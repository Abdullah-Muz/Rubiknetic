"""D8-1b (UNSCORED): passive piece-to-piece magnets for M1-geometry cubes (P-16; design approved 2026-11-14).

Layout (D8_1b_DESIGN_PROPOSAL.md §3): the classic 48-magnet corner–edge system. Each corner carries 3 axial disc
magnets, one on each face toward its 3 edge neighbours; each edge carries 2, one on each face toward its 2 corner
neighbours. Centres and core carry none. Magnets sit on the face centre, recessed by a wall w. Polarity: corner
moments point out of the corner's face, edge moments point into the edge's face, so every facing corner-edge pair
is head-to-tail and attracts.

Force law (D8_1b_DESIGN_PROPOSAL.md §5), a fixed function of the poses of the bodies the magnets are fixed in:
  U = sum over magnet pairs on different bodies of
        U_dipole(r, m1, m2) + w(|r|) * s * [U_exact(rho, |z|) - U_dipole_par(rho, |z|)]   if |n1 . n2| > cos 45 deg
        U_dipole(r, m1, m2)                                                               otherwise
  * U_dipole: point dipoles, m = (Br / mu0) * pi a^2 L (exact far field). Every pair term is multiplied by a C2
    taper that goes from 1 at far_r1 (20 mm) to 0 at far_r2 (25 mm), where the dipole force is ~0.06 % of the
    facing-pair force; a Verlet neighbour list (skin 4 mm, rebuilt before any magnet moves skin/2) makes this exact.
  * U_exact: the charge-model pair energy of two parallel coaxially-oriented cylinders at lateral offset rho and
    axial offset z (bicubic spline of a table precomputed with magnet_force.disc_points quadrature).
  * s = sign(n1 . n2); w = smooth cutoff (1 below R1, 0 above R2, C2 quintic in between).
  * Only facing pairs come within R2 in legal motion, and their axes stay parallel during turns, so the parallel /
    perpendicular branch never switches inside R2 (counted at run time: stats['near_perpendicular'] must stay 0).
  Forces are -grad U. Torques: dipole m x B for far pairs; for near parallel pairs the exact charge-model torque on
  the upper magnet (a second table), blended by w, with the partner's torque set by exact angular-momentum balance
  (T_i + T_j = -rv x F_j). Rotation about the common axis (the turning motion) is exactly conservative (V5).
  ASSUMPTION: for slightly TILTED pairs the parallel-pair tables stand in for the true tilted-pair energy and torque
  (tilts are small in legal motion), so energy is conserved only to first order in tilt.
Injection: mujoco.set_mjcb_passive adds the generalized forces to qfrc_passive inside mj_step (D5 detent.py
precedent), so the AuditedSim edit audit is unaffected. The callback reads ONLY body poses (xpos, xmat). It never
reads controls, time, commands, oracle state or switch state.
One magnet model per process (the MuJoCo passive callback is global).
"""
from __future__ import annotations

import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import mujoco
import numpy as np
from scipy.interpolate import RectBivariateSpline

sys.path.insert(0, str(Path(__file__).parent))
from magnet_force import MU0, disc_points  # noqa: E402

from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_physics.m1_model import cubie_name  # noqa: E402

GRADES_BR = {"N35": 1.19, "N42": 1.30, "N45": 1.35, "N52": 1.455}  # mid-range Br (T), first4magnets grade table


@dataclass(frozen=True)
class MagnetParams:
    diameter: float = 0.004      # m
    length: float = 0.002        # m (axial thickness)
    grade: str = "N35"
    wall: float = 0.0004         # plastic wall in front of each magnet; face gap = piece gap + 2 * wall
    scale: float = 1.0           # strength scale on Br^2 (0.67 = possible overestimate of the ideal model, V2)
    r1: float = 0.005            # near-field correction fully on below this centre distance (m)
    r2: float = 0.008            # ... and fully off above this one
    far_r1: float = 0.020        # every pair interaction tapers smoothly to zero between far_r1 and far_r2
    far_r2: float = 0.025        # (dipole force at 25 mm is ~0.06 % of the facing-pair force; keeps U smooth)
    skin: float = 0.004          # neighbour-list margin; the list is rebuilt before any magnet moves skin/2

    @property
    def br(self) -> float:
        return GRADES_BR[self.grade]

    @property
    def moment(self) -> float:
        """|m| in A m^2, with the strength scale applied to |m|^2 (all forces scale with |m|^2)."""
        return (self.br / MU0) * np.pi * (self.diameter / 2) ** 2 * self.length * np.sqrt(self.scale)

    @property
    def magnet_mass(self) -> float:
        return 7500.0 * np.pi * (self.diameter / 2) ** 2 * self.length  # NdFeB ~7.5 g/cm^3 (ASSUMPTION)


def layout(pitch: float, gap: float, mp: MagnetParams) -> list[dict]:
    """48 magnets: body name, position and moment direction in the body frame (= core frame at home)."""
    h = (pitch - gap) / 2
    mags = []
    for home in HOME_POSITIONS:
        nz = np.count_nonzero(home)
        if nz == 1:
            continue
        c = np.array(home, float)
        for k in range(3):
            if nz == 3:                        # corner: face toward the edge obtained by zeroing component k
                sgn = c[k]
                pos = c * pitch
                pos[k] = sgn * (pitch - h + mp.wall + mp.length / 2)
                direction = np.zeros(3)
                direction[k] = -sgn            # out of the corner face, toward the edge
                mags.append({"body": cubie_name(home), "pos": pos, "dir": direction, "kind": "corner"})
            elif c[k] == 0:                    # edge: both faces along its zero axis, toward the two corners
                for sgn in (-1.0, 1.0):
                    pos = c * pitch
                    pos[k] = sgn * (h - mp.wall - mp.length / 2)
                    direction = np.zeros(3)
                    direction[k] = -sgn        # into the edge face (the face points toward +sgn)
                    mags.append({"body": cubie_name(home), "pos": pos, "dir": direction, "kind": "edge"})
    assert len(mags) == 48, len(mags)
    return mags


# ------------------------------------------------------------------ exact near-field table
def _exact_parallel_energy(a: float, L: float, m_abs: float, rho: np.ndarray, z: np.ndarray,
                           n_r: int = 16, n_phi: int = 48) -> np.ndarray:
    """Charge-model energy (J) of two identical parallel coaxially-oriented cylinders, centre offset (rho, z)."""
    sigma = m_abs / (np.pi * a * a * L)            # |M| = m / V
    pts, w = disc_points(a, n_r, n_phi)
    out = np.zeros(rho.shape)
    faces = [(+L / 2, +1.0), (-L / 2, -1.0)]       # north face at +L/2 (moment along +z)
    for idx in np.ndindex(rho.shape):
        u = 0.0
        for za, qa in faces:
            for zb, qb in faces:
                dx = pts[None, :, 0] + rho[idx] - pts[:, None, 0]
                dy = pts[None, :, 1] - pts[:, None, 1]
                dz = (z[idx] + zb) - za
                u += qa * qb * np.einsum("i,j,ij->", w, w, 1.0 / np.sqrt(dx * dx + dy * dy + dz * dz))
        out[idx] = MU0 / (4 * np.pi) * sigma * sigma * u
    return out


def _exact_parallel_torque(a: float, L: float, m_abs: float, rho: np.ndarray, z: np.ndarray,
                           n_r: int = 16, n_phi: int = 48) -> np.ndarray:
    """Charge-model torque (N m) on the UPPER magnet B about its own centre, for B at (rho, 0, z > 0) above A at the
    origin, both moments +z. By symmetry it points along y = z_hat x x_hat (= axis x lateral direction A -> B)."""
    sigma = m_abs / (np.pi * a * a * L)
    pts, w = disc_points(a, n_r, n_phi)
    out = np.zeros(rho.shape)
    faces = [(+L / 2, +1.0), (-L / 2, -1.0)]
    ww = w[:, None] * w[None, :]
    for idx in np.ndindex(rho.shape):
        ty = 0.0
        for za, qa in faces:
            for zb, qb in faces:
                dx = pts[None, :, 0] + rho[idx] - pts[:, None, 0]
                dy = pts[None, :, 1] - pts[:, None, 1]
                dz = (z[idx] + zb) - za
                r3 = (dx * dx + dy * dy + dz * dz) ** 1.5
                fx = qa * qb * ww * dx / r3                 # force on B's charge j from A's charge i (x, z parts)
                fz = qa * qb * ww * dz / r3
                # lever arm of B's charge about B's centre: (pts_j_x, pts_j_y, zb); y-component of r x f
                ty += float(np.sum(zb * fx - pts[None, :, 0] * fz))
        out[idx] = MU0 / (4 * np.pi) * sigma * sigma * ty
    return out


def _dipole_parallel_energy(m_abs: float, rho, z):
    r2 = rho * rho + z * z
    return MU0 / (4 * np.pi) * m_abs ** 2 * (r2 - 3 * z * z) / r2 ** 2.5


_TABLE_CACHE: dict = {}


def correction_spline(mp: MagnetParams, cache_dir: Path | None = None) -> tuple:
    """Splines on rho in [0, R2], |z| in [L + 0.1 mm, R2] for parallel moments:
    dU(rho, |z|) = U_exact - U_dipole (J), and tau(rho, |z|) = exact torque on the upper magnet about its centre (N m)."""
    key = (mp.diameter, mp.length, mp.br, mp.scale, mp.r2)
    if key in _TABLE_CACHE:
        return _TABLE_CACHE[key]
    rho = np.linspace(0.0, mp.r2 + 0.001, 37)
    zz = np.linspace(mp.length + 0.0001, mp.r2 + 0.001, 31)
    path = None
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = cache_dir / f"dU_{mp.diameter*1e3:g}x{mp.length*1e3:g}_{mp.br:g}T_s{mp.scale:g}_r{mp.r2*1e3:g}.npz"
    if path is not None and path.exists() and "tau" in np.load(path):
        f = np.load(path)
        tab, tau = f["dU"], f["tau"]
    else:
        R, Z = np.meshgrid(rho, zz, indexing="ij")
        a = mp.diameter / 2
        tab = _exact_parallel_energy(a, mp.length, mp.moment, R, Z) - _dipole_parallel_energy(mp.moment, R, Z)
        tau = _exact_parallel_torque(a, mp.length, mp.moment, R, Z)
        if path is not None:
            np.savez(path, dU=tab, tau=tau, rho=rho, z=zz)
    spl = (RectBivariateSpline(rho, zz, tab, kx=3, ky=3), RectBivariateSpline(rho, zz, tau, kx=3, ky=3))
    _TABLE_CACHE[key] = spl
    return spl


def _cutoff(r: np.ndarray, r1: float, r2: float) -> tuple[np.ndarray, np.ndarray]:
    """C2 quintic smoothstep: w = 1 (r <= r1) ... 0 (r >= r2) and dw/dr."""
    t = np.clip((r - r1) / (r2 - r1), 0.0, 1.0)
    w = 1 - (10 * t ** 3 - 15 * t ** 4 + 6 * t ** 5)
    dw = -(30 * t ** 2 - 60 * t ** 3 + 30 * t ** 4) / (r2 - r1)
    dw = np.where((r > r1) & (r < r2), dw, 0.0)
    return w, dw


def _cross(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Row-wise cross product of (k, 3) arrays (much faster than np.cross for small arrays)."""
    return np.column_stack([a[:, 1] * b[:, 2] - a[:, 2] * b[:, 1],
                            a[:, 2] * b[:, 0] - a[:, 0] * b[:, 2],
                            a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]])


def scatter_matrices(n_mag: int, ii: np.ndarray, jj: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(n_mag, n_pairs) one-hot matrices so that per-magnet sums are matrix products (replaces np.add.at)."""
    Si = np.zeros((n_mag, len(ii)))
    Sj = np.zeros((n_mag, len(jj)))
    Si[ii, np.arange(len(ii))] = 1.0
    Sj[jj, np.arange(len(jj))] = 1.0
    return Si, Sj


def pair_forces(mp: MagnetParams, spline, ii: np.ndarray, jj: np.ndarray, p: np.ndarray, n: np.ndarray,
                stats: dict | None = None, scatter: tuple | None = None) -> tuple[np.ndarray, np.ndarray, float]:
    """Per-magnet force (N) and torque about its own centre (N m), and the total energy (J)."""
    mabs, c = mp.moment, MU0 / (4 * np.pi)
    i, j = ii, jj
    zmin = mp.length + 0.0001
    rv = p[j] - p[i]
    r = np.linalg.norm(rv, axis=1)
    rh = rv / r[:, None]
    m1, m2 = mabs * n[i], mabs * n[j]
    a1 = np.einsum("ij,ij->i", m1, rh)
    a2 = np.einsum("ij,ij->i", m2, rh)
    mm = np.einsum("ij,ij->i", m1, m2)
    wf, dwf = _cutoff(r, mp.far_r1, mp.far_r2)                      # smooth far taper of the whole interaction
    Ud = c / r ** 3 * (mm - 3 * a1 * a2)
    U = float(np.sum(wf * Ud))
    F2 = (3 * c / r ** 4)[:, None] * (a1[:, None] * m2 + a2[:, None] * m1 + mm[:, None] * rh
                                     - 5 * (a1 * a2)[:, None] * rh)
    F2 = wf[:, None] * F2 - (dwf * Ud)[:, None] * rh
    B1 = (c / r ** 3)[:, None] * (3 * a1[:, None] * rh - m1)        # field of 1 at 2
    B2 = (c / r ** 3)[:, None] * (3 * a2[:, None] * rh - m2)        # field of 2 at 1 (r -> -r leaves it unchanged)
    T2 = wf[:, None] * _cross(m2, B1)
    T1 = wf[:, None] * _cross(m1, B2)
    # near-field correction for (nearly) parallel pairs within R2
    cosn = np.einsum("ij,ij->i", n[i], n[j])
    near = r < mp.r2
    par = near & (np.abs(cosn) > np.cos(np.radians(45)))
    if stats is not None:
        stats["near_perpendicular"] += int(np.sum(near & ~par))
    if par.any():
        k = np.nonzero(par)[0]
        ax = n[i[k]]
        z = np.einsum("ij,ij->i", rv[k], ax)
        lat = rv[k] - z[:, None] * ax
        rho = np.linalg.norm(lat, axis=1)
        az = np.abs(z)
        if stats is not None:
            stats["clamped_z"] += int(np.sum(az < zmin))
        azc = np.maximum(az, zmin)
        s = np.sign(cosn[k])
        sU, sT = spline
        dU = s * sU.ev(rho, azc)
        dUr = s * sU.ev(rho, azc, dx=1)
        dUz = s * sU.ev(rho, azc, dy=1) * (az >= zmin)
        w, dw = _cutoff(r[k], mp.r1, mp.r2)
        U += float(np.sum(w * dU))
        lat_hat = np.where(rho[:, None] > 1e-12, lat / np.maximum(rho, 1e-12)[:, None], 0.0)
        # grad wrt p_j of w(r) dU(rho, |z|); force on j is minus that, on i plus that
        grad = (w * dUr)[:, None] * lat_hat + (w * dUz * np.sign(z))[:, None] * ax + (dw * dU)[:, None] * rh[k]
        F2[k] -= grad
        # Torques of near parallel pairs: the exact torque on the upper magnet (table), blended with the dipole torque
        # by w; the partner gets the remainder so that T_i + T_j = -rv x F_j (exact angular-momentum balance).
        e_t = _cross(ax, lat_hat)                      # ax x lateral direction (lower -> upper when j is upper)
        tau = s * sT.ev(rho, azc)
        up_j = (z >= 0)[:, None]
        T_up = np.where(up_j, 1.0, -1.0) * tau[:, None] * e_t
        tot = -_cross(rv[k], F2[k])
        Tj_exact = np.where(up_j, T_up, tot - T_up)
        T2[k] = (1 - w)[:, None] * T2[k] + w[:, None] * Tj_exact
        T1[k] = tot - T2[k]
    Si, Sj = scatter if scatter is not None else scatter_matrices(len(p), i, j)
    F = Sj @ F2 - Si @ F2
    T = Sj @ T2 + Si @ T1
    if stats is not None:
        stats["max_force_N"] = max(stats["max_force_N"], float(np.abs(F).max()))
    return F, T, U


# ------------------------------------------------------------------ the magnet system
class MagnetSystem:
    def __init__(self, model: mujoco.MjModel, pitch: float, gap: float, mp: MagnetParams,
                 cache_dir: Path | None = None):
        self.m, self.mp = model, mp
        self.mags = layout(pitch, gap, mp)
        self.body = np.array([mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, g["body"]) for g in self.mags])
        assert (self.body >= 0).all()
        self.p_loc = np.array([g["pos"] for g in self.mags])
        self.d_loc = np.array([g["dir"] for g in self.mags])
        ii, jj = np.triu_indices(48, 1)
        keep = self.body[ii] != self.body[jj]            # same-body pairs are rigid: no effect, skipped
        self.ii_all, self.jj_all = ii[keep], jj[keep]
        self.ii, self.jj = self.ii_all, self.jj_all      # active neighbour list (all pairs until first rebuild)
        self.p_ref = None
        self.bodies = np.unique(self.body)
        self.scatter = scatter_matrices(48, self.ii, self.jj)
        self.body_sum = (self.body[None, :] == self.bodies[:, None]).astype(float)   # (n_bodies, 48)
        self.spline = correction_spline(mp, cache_dir)
        self.zmin = mp.length + 0.0001
        self.stats = {"calls": 0, "clamped_z": 0, "near_perpendicular": 0, "max_force_N": 0.0, "list_rebuilds": 0,
                      "list_pairs": len(self.ii_all)}
        self._buf = np.zeros(model.nv)

    # pure function of body poses -------------------------------------------------------------
    def world(self, xpos: np.ndarray, xmat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        R = xmat[self.body].reshape(-1, 3, 3)
        p = xpos[self.body] + np.einsum("nij,nj->ni", R, self.p_loc)
        n = np.einsum("nij,nj->ni", R, self.d_loc)
        return p, n

    def _update_list(self, p: np.ndarray) -> None:
        """Verlet neighbour list: keep pairs within far_r2 + skin; rebuild before any magnet moves skin/2."""
        if self.p_ref is not None and np.max(np.sum((p - self.p_ref) ** 2, axis=1)) < (self.mp.skin / 2) ** 2:
            return
        r = np.linalg.norm(p[self.jj_all] - p[self.ii_all], axis=1)
        sel = r < self.mp.far_r2 + self.mp.skin
        self.ii, self.jj = self.ii_all[sel], self.jj_all[sel]
        self.scatter = scatter_matrices(48, self.ii, self.jj)
        self.p_ref = p.copy()
        self.stats["list_rebuilds"] += 1
        self.stats["list_pairs"] = int(sel.sum())

    def forces(self, p: np.ndarray, n: np.ndarray, stats: bool = False) -> tuple[np.ndarray, np.ndarray, float]:
        """Per-magnet force (N) and torque about its own centre (N m), and the total energy (J)."""
        self._update_list(p)
        return pair_forces(self.mp, self.spline, self.ii, self.jj, p, n, self.stats if stats else None, self.scatter)

    def energy(self, d: mujoco.MjData) -> float:
        return self.forces(*self.world(d.xpos, d.xmat))[2]

    # MuJoCo injection ------------------------------------------------------------------------
    def apply(self, model: mujoco.MjModel, d: mujoco.MjData) -> None:
        p, n = self.world(d.xpos, d.xmat)
        F, T, _ = self.forces(p, n, stats=True)
        self.stats["calls"] += 1
        Fb = self.body_sum @ F
        Tb = self.body_sum @ (T + _cross(p - d.xpos[self.body], F))
        self._buf[:] = 0.0
        for k, b in enumerate(self.bodies):
            mujoco.mj_applyFT(model, d, Fb[k], Tb[k], d.xpos[b], int(b), self._buf)  # accumulates into _buf
        d.qfrc_passive[:] += self._buf

    def install(self) -> None:
        mujoco.set_mjcb_passive(lambda model, data: self.apply(model, data))

    @staticmethod
    def uninstall() -> None:
        mujoco.set_mjcb_passive(None)

    def describe(self) -> dict:
        return {"params": asdict(self.mp), "Br_T": self.mp.br, "moment_Am2": self.mp.moment,
                "magnet_mass_g": self.mp.magnet_mass * 1e3, "n_magnets": 48, "n_pairs": int(len(self.ii))}
