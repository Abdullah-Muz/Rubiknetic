"""D25 prototype (UNSCORED): a faster pure-NumPy drop-in for MagnetSystem.apply (option (a)).

It is a separate implementation; src/rubiknetic/cube_physics/magnets.py is not touched. FastApply(ms) wraps an existing
single-type MagnetSystem and evaluates the same force law. Default ("tuned": spline direct, scatter blas, body blas):
the same floating-point operations in the same order with fewer Python-level calls, intended to be bit-identical.
"perturbed" (scatter bincount, body bincount): per-magnet / per-body sums in sequential pair order instead of OpenBLAS's
order, a rounding-level stand-in for what a compiled (C) port would change. Components:
  * norm_rows / np.add.reduce / c_einsum: numpy's own computation without the Python wrappers.

  * spline "fused": the 12 RectBivariateSpline.ev calls (4 tables x value, d/drho, d/dz) are replaced by one
    vectorised re-implementation of FITPACK's evaluation (fpbisp / fpbspl / parder, as wrapped by bispeu / pardeu):
    the B-spline basis is computed once per point and coordinate by the de Boor-Cox recursion in FITPACK's operation
    order; the degree-2 basis of the derivative (parder evaluates on the knots t[1:-1] with degree k-1) is exactly the
    intermediate level of the degree-3 recursion; the derivative coefficients ((c[i+1]-c[i]) * k / (t[i+k+1]-t[i+1]),
    parder's formula) are computed once at construction instead of once per point per call; the double sum is done in
    FITPACK's order (i1 outer, j1 inner, left to right). spline "direct" calls scipy's compiled bispeu / pardeu
    without the Python wrapper (identical by construction). spline "scipy" is the original .ev calls.
  * cutoff: the C2 taper with each power t**k computed once and reused (the original computes t**3 and t**4 twice).
  * spline "fused" is measured 3x SLOWER than scipy (741 vs 239 us) and is kept only for the FITPACK bit-identity
    test (it is what a C port of the spline would do).
  * scatter "bincount": per-magnet sums by np.bincount (sequential in pair order) instead of the one-hot matrix
    product; "blas" keeps the original matrix product. body "bincount" likewise for the per-body sums.
  * The Verlet neighbour list, stats, the RecordingMagnetSystem `last` record and the mj_applyFT accumulation are the
    original object's own (ms._update_list, ms.stats, ms.last, ms._buf), so shared state (e.g. MagnetMonitor's
    energy() calls between steps) evolves exactly as with the original callback.
Whether any of this is bit-identical is an empirical question: equivalence.py tests it."""
from __future__ import annotations

import mujoco
import numpy as np
from numpy._core.multiarray import c_einsum
from scipy.interpolate import _fitpack

from rubiknetic.cube_physics import magnets as MG

cross = MG._cross            # the original row-wise cross product (an index-array variant measured slower: 25 vs 21 us)


def norm_rows(x: np.ndarray) -> np.ndarray:
    """np.linalg.norm(x, axis=1) for a real 2-D array as numpy implements it (sqrt of add.reduce of x*x), without the
    Python wrapper (16 us -> about 4 us)."""
    return np.sqrt(np.add.reduce(x * x, axis=1))


def cutoff(r: np.ndarray, r1: float, r2: float) -> tuple[np.ndarray, np.ndarray]:
    """magnets._cutoff with the same operations; t**3 and t**4 computed once."""
    t = np.minimum(np.maximum((r - r1) / (r2 - r1), 0.0), 1.0)
    t3, t4 = t ** 3, t ** 4
    w = 1 - (10 * t3 - 15 * t4 + 6 * t ** 5)
    dw = -(30 * t ** 2 - 60 * t3 + 30 * t4) / (r2 - r1)
    dw = np.where((r > r1) & (r < r2), dw, 0.0)
    return w, dw


# ---------------------------------------------------------------- FITPACK evaluation, vectorised
class FusedSplines:
    """Evaluates value, d/dx and d/dy of several cubic RectBivariateSplines at the same points, as FITPACK does.
    Splines are grouped by their x knots (the y knots must be common)."""

    def __init__(self, splines):
        self.n = len(splines)
        ty = splines[0].tck[1]
        for s in splines:
            assert tuple(s.degrees) == (3, 3)
            assert np.array_equal(s.tck[1], ty)
        groups: dict = {}
        for idx, s in enumerate(splines):
            key = s.tck[0].tobytes()
            groups.setdefault(key, []).append(idx)
        self.groups = []
        knots = []
        off = 0
        for key, members in groups.items():
            tx = splines[members[0]].tck[0]
            knots.append(tx)
            self.groups.append({"members": members, "tx": tx, "off": off})
            off += len(tx)
        self.ty, self.ty_off = ty, off
        knots.append(ty)
        self.TT = np.concatenate(knots)
        ny = len(ty)
        nky1 = ny - 4
        for g in self.groups:
            tx = g["tx"]
            nx = len(tx)
            nkx1 = nx - 4
            C = np.stack([splines[m].tck[2].reshape(nkx1, nky1) for m in g["members"]])   # (ng, nkx1, nky1)
            # parder, nux = 1: wrk(m0) = (wrk(m1) - wrk(m0)) * ak / fac, fac = tx(l1 + k) - tx(l1), row by row
            fac_x = tx[4:4 + nkx1 - 1] - tx[1:1 + nkx1 - 1]
            assert (fac_x > 0).all()
            CDX = (C[:, 1:, :] - C[:, :-1, :]) * 3.0 / fac_x[None, :, None]
            fac_y = ty[4:4 + nky1 - 1] - ty[1:1 + nky1 - 1]
            assert (fac_y > 0).all()
            CDY = (C[:, :, 1:] - C[:, :, :-1]) * 3.0 / fac_y[None, None, :]
            g.update(C=C, CDX=CDX, CDY=CDY, nkx1=nkx1)
        self.nky1 = nky1

    @staticmethod
    def _interval(t: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """fpbisp: clamp to [t(k+1), t(n-k)] and find l (1-based) with t(l) <= x < t(l+1), k+1 <= l <= n-k-1."""
        n = len(t)
        nk1 = n - 4
        xc = np.minimum(np.maximum(x, t[3]), t[nk1])
        l = np.searchsorted(t, xc, side="right")            # = (0-based last index with t <= x) + 1 = 1-based l
        l = np.minimum(np.maximum(l, 4), nk1)
        return xc, l

    def basis(self, X: np.ndarray, Lg: np.ndarray):
        """fpbspl (k = 3) for all points at once. X: arguments; Lg: 0-based index into TT of t(l) for each point.
        Returns the degree-2 and degree-3 bases, shapes (npts, 3) and (npts, 4)."""
        TT = self.TT
        W = TT[Lg[:, None] + np.arange(-2, 4)]              # t(l-2) ... t(l+3)
        h = np.ones((len(X), 1))
        Xc = X[:, None]
        h2 = None
        for j in (1, 2, 3):
            tli = W[:, 3:3 + j]                             # t(l+i), i = 1..j
            tlj = W[:, 3 - j:3]                             # t(l+i-j)
            f = h / (tli - tlj)
            A = f * (tli - Xc)
            B = f * (Xc - tlj)
            hn = np.empty((len(X), j + 1))
            hn[:, 0] = 0.0 + A[:, 0]
            hn[:, 1:j] = B[:, :j - 1] + A[:, 1:j]
            hn[:, j] = B[:, j - 1]
            h = hn
            if j == 2:
                h2 = h
        return h2, h

    def ev(self, x: np.ndarray, y: np.ndarray):
        """Returns (value, d/dx, d/dy), each of shape (n_splines, npts), in the splines' original order."""
        k = len(x)
        G = len(self.groups)
        xs, ls = [], []
        for g in self.groups:
            xc, l = self._interval(g["tx"], x)
            xs.append(xc)
            ls.append(l - 1 + g["off"])
        yc, ly = self._interval(self.ty, y)
        X = np.concatenate(xs + [yc])
        L = np.concatenate(ls + [ly - 1 + self.ty_off])
        h2, h3 = self.basis(X, L)
        hy2, hy3 = h2[G * k:], h3[G * k:]
        lyo = ly - 4                                        # first basis index in y (0-based)
        out = [np.empty((self.n, k)) for _ in range(3)]
        for gi, g in enumerate(self.groups):
            hx2, hx3 = h2[gi * k:(gi + 1) * k], h3[gi * k:(gi + 1) * k]
            lxo = ls[gi] - g["off"] - 3                     # = l - 4 (l 1-based)
            for which, (CC, hx, hy, ax, ay) in enumerate(((g["C"], hx3, hy3, 4, 4), (g["CDX"], hx2, hy3, 3, 4),
                                                          (g["CDY"], hx3, hy2, 4, 3))):
                ia = lxo[:, None, None] + np.arange(ax)[None, :, None]
                ib = lyo[:, None, None] + np.arange(ay)[None, None, :]
                Wc = CC[:, ia, ib]                           # (ng, k, ax, ay)
                terms = (Wc * hx[None, :, :, None]) * hy[None, :, None, :]
                terms = np.ascontiguousarray(terms.reshape(len(g["members"]), k, ax * ay).transpose(2, 0, 1))
                sp = np.add.accumulate(terms, axis=0)[-1]   # strictly left to right, i1 outer, j1 inner
                for mi, m in enumerate(g["members"]):
                    out[which][m] = sp[mi]
        return out


class FastApply:
    def __init__(self, ms: MG.MagnetSystem, spline: str = "direct", scatter: str = "blas", body: str = "blas"):
        assert not ms.composite, "composite magnet systems are not supported by the prototype"
        self.ms, self.mp = ms, ms.mp
        self.spline_mode, self.scatter_mode, self.body_mode = spline, scatter, body
        self.mabs, self.c = ms.mp.moment, MG.MU0 / (4 * np.pi)
        self.zmin = ms.mp.length + 0.0001
        self.cos45 = np.cos(np.radians(45))
        self.recording = hasattr(type(ms), "last")
        self.fused = FusedSplines(list(ms.spline)) if spline == "fused" else None
        self.body_idx = np.searchsorted(ms.bodies, ms.body)
        self.nb = len(ms.bodies)
        self.bodies_int = [int(b) for b in ms.bodies]

    # ------------------------------------------------------------------ splines
    def splines(self, rho, azc):
        S = self.ms.spline
        if self.spline_mode == "scipy":
            return [[s.ev(rho, azc), s.ev(rho, azc, dx=1), s.ev(rho, azc, dy=1)] for s in S]
        if self.spline_mode == "direct":
            out = []
            for s in S:
                tx, ty, c = s.tck
                out.append([_fitpack.bispeu(tx, ty, c, 3, 3, rho, azc)[0],
                            _fitpack.pardeu(tx, ty, c, 3, 3, 1, 0, rho, azc)[0],
                            _fitpack.pardeu(tx, ty, c, 3, 3, 0, 1, rho, azc)[0]])
            return out
        v, dx, dy = self.fused.ev(rho, azc)
        return [[v[q], dx[q], dy[q]] for q in range(4)]

    # ------------------------------------------------------------------ the force law (magnets.pair_forces)
    def pair_forces(self, ii, jj, p, n, stats, scatter):
        mp = self.mp
        mabs, c = self.mabs, self.c
        i, j = ii, jj
        zmin = self.zmin
        rv = p[j] - p[i]
        r = norm_rows(rv)
        rh = rv / r[:, None]
        ni, nj = n[i], n[j]
        m1, m2 = mabs * ni, mabs * nj
        a1 = c_einsum("ij,ij->i", m1, rh)
        a2 = c_einsum("ij,ij->i", m2, rh)
        mm = c_einsum("ij,ij->i", m1, m2)
        wf, dwf = cutoff(r, mp.far_r1, mp.far_r2)
        cr3 = c / r ** 3
        Ud = cr3 * (mm - 3 * a1 * a2)
        U = float(np.add.reduce(wf * Ud))
        F2 = (3 * c / r ** 4)[:, None] * (a1[:, None] * m2 + a2[:, None] * m1 + mm[:, None] * rh
                                         - 5 * (a1 * a2)[:, None] * rh)
        F2 = wf[:, None] * F2 - (dwf * Ud)[:, None] * rh
        cr3c = cr3[:, None]
        B1 = cr3c * (3 * a1[:, None] * rh - m1)
        B2 = cr3c * (3 * a2[:, None] * rh - m2)
        wfc = wf[:, None]
        T2 = wfc * cross(m2, B1)
        T1 = wfc * cross(m1, B2)
        cosn = c_einsum("ij,ij->i", ni, nj)
        near = r < mp.r2
        par = near & (np.abs(cosn) > self.cos45)
        if stats is not None:
            stats["near_perpendicular"] += int(np.count_nonzero(near & ~par))
        k = np.flatnonzero(par)
        if len(k):
            ax = ni[k]
            s = np.sign(cosn[k])
            u = s[:, None] * nj[k]
            rk = rv[k]
            z = c_einsum("ij,ij->i", rk, ax)
            lat = rk - z[:, None] * ax
            rho = norm_rows(lat)
            az = np.abs(z)
            if stats is not None:
                stats["clamped_z"] += int(np.count_nonzero(az < zmin))
                tilt = float(np.degrees(np.arccos(min(1.0, float(np.abs(cosn[k]).min())))))
                stats["max_near_tilt_deg"] = max(stats["max_near_tilt_deg"], tilt)
            azc = np.maximum(az, zmin)
            zon = (az >= zmin).astype(float)
            sig = np.where(z >= 0, 1.0, -1.0)
            mu = c_einsum("ij,ij->i", u, ax)
            v = c_einsum("ij,ij->i", u, lat)
            (C0, C0r, C0z), (A, Ar, Az), (B, Br, Bz), (D, Dr, Dz) = self.splines(rho, azc)
            q = 1.0 - mu * mu                           # the original expressions, verbatim (operation order matters)
            C = C0 + sig * A * v + 0.5 * B * q + 0.5 * D * v * v
            C_r = C0r + sig * v * Ar + 0.5 * q * Br + 0.5 * v * v * Dr
            C_z = (C0z + sig * v * Az + 0.5 * q * Bz + 0.5 * v * v * Dz) * zon
            C_v = sig * A + D * v
            C_mu = -B * mu
            w, dw = cutoff(r[k], mp.r1, mp.r2)
            U += float(np.add.reduce(s * w * C))
            lat_hat = np.where(rho[:, None] > 1e-12, lat / np.maximum(rho, 1e-12)[:, None], 0.0)
            grad = s[:, None] * ((dw * C)[:, None] * rh[k]
                                 + w[:, None] * (C_r[:, None] * lat_hat + (C_z * sig)[:, None] * ax
                                                 + C_v[:, None] * (u - mu[:, None] * ax)))
            F2k = F2[k] - grad
            F2[k] = F2k
            g_u = (s * w)[:, None] * (C_v[:, None] * lat + C_mu[:, None] * ax)
            T2k = T2[k] - cross(u, g_u)
            T2[k] = T2k
            T1[k] = -cross(rk, F2k) - T2k
        nm = len(p)
        if self.scatter_mode == "blas":
            Si, Sj = scatter
            F = Sj @ F2 - Si @ F2
            T = Sj @ T2 + Si @ T1
        else:
            F, T = self._scatter(i, j, F2, T1, T2, nm)
        if stats is not None:
            stats["max_force_N"] = max(stats["max_force_N"], float(np.abs(F).max()))
        return F, T, U

    def _scatter(self, i, j, F2, T1, T2, nm):
        ix = (i[:, None] * 3 + np.arange(3)).ravel()
        jx = (j[:, None] * 3 + np.arange(3)).ravel()
        Fj = np.bincount(jx, F2.ravel(), minlength=3 * nm)
        Fi = np.bincount(ix, F2.ravel(), minlength=3 * nm)
        Tj = np.bincount(jx, T2.ravel(), minlength=3 * nm)
        Ti = np.bincount(ix, T1.ravel(), minlength=3 * nm)
        return (Fj - Fi).reshape(nm, 3), (Tj + Ti).reshape(nm, 3)

    # ------------------------------------------------------------------ the callback (magnets.MagnetSystem.apply)
    def forces(self, p, n, stats: bool = False):
        ms = self.ms
        ms._update_list(p)
        F, T, U = self.pair_forces(ms.ii, ms.jj, p, n, ms.stats if stats else None, ms.scatter)
        if stats and self.recording:
            ms.last = (p.copy(), F.copy(), T.copy(), U)
        return F, T, U

    def apply(self, model: mujoco.MjModel, d: mujoco.MjData) -> None:
        ms = self.ms
        xpos = d.xpos
        R = d.xmat[ms.body].reshape(-1, 3, 3)                       # MagnetSystem.world without the einsum wrapper
        p = xpos[ms.body] + c_einsum("nij,nj->ni", R, ms.p_loc)
        n = c_einsum("nij,nj->ni", R, ms.d_loc)
        F, T, _ = self.forces(p, n, stats=True)
        ms.stats["calls"] += 1
        Tt = T + cross(p - xpos[ms.body], F)
        if self.body_mode == "blas":
            Fb = ms.body_sum @ F
            Tb = ms.body_sum @ Tt
        else:
            bx = (self.body_idx[:, None] * 3 + np.arange(3)).ravel()
            Fb = np.bincount(bx, F.ravel(), minlength=3 * self.nb).reshape(self.nb, 3)
            Tb = np.bincount(bx, Tt.ravel(), minlength=3 * self.nb).reshape(self.nb, 3)
        buf = ms._buf
        buf[:] = 0.0
        applyFT = mujoco.mj_applyFT
        for kk, b in enumerate(self.bodies_int):
            applyFT(model, d, Fb[kk], Tb[kk], xpos[b], b, buf)
        d.qfrc_passive[:] += buf


def patch(ms: MG.MagnetSystem, **kw) -> FastApply:
    """Route ms's installed callback (install() looks up ms.apply at call time) to a FastApply."""
    fa = FastApply(ms, **kw)
    ms.apply = fa.apply
    return fa
