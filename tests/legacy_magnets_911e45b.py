"""Frozen reference for tests/test_magnets_composite.py: the single-type MagnetSystem and pair_forces exactly as they
were before the composite (two-type) magnet system was added (P-67 item 2).

Lines 338-535 of src/rubiknetic/cube_physics/magnets.py at commit 911e45b (the last commit that changed that file
before P-67; the file is identical at 350be9c, sha256 54801b19...ed40383cb), copied verbatim. Only this header and
the import block are new. Do not edit the copied code: the equivalence tests compare the current module against it
bit for bit. Not a test module (no test_ prefix); the test loads it by path.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import mujoco
import numpy as np

from rubiknetic.cube_physics.magnets import MU0, MagnetParams, layout, near_field_tables


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
        # Tilt-aware near-field correction (revision 2): U_c = s w(r) C(rho, |z|, v, mu), see near_field_tables.
        # It is a function of the rotation invariants z = rv.a, rho, v = u.lat, mu = u.a only, so forces are its exact
        # gradient, the torque on j is -u x dU_c/du, and the torque on i follows from exact angular-momentum balance.
        k = np.nonzero(par)[0]
        ax = n[i[k]]
        s = np.sign(cosn[k])
        u = s[:, None] * n[j[k]]
        rk = rv[k]
        z = np.einsum("ij,ij->i", rk, ax)
        lat = rk - z[:, None] * ax
        rho = np.linalg.norm(lat, axis=1)
        az = np.abs(z)
        if stats is not None:
            stats["clamped_z"] += int(np.sum(az < zmin))
            # tilt of the pair away from parallel (V3 sets the validated range)
            tilt = float(np.degrees(np.arccos(min(1.0, float(np.abs(cosn[k]).min())))))
            stats["max_near_tilt_deg"] = max(stats["max_near_tilt_deg"], tilt)
        azc = np.maximum(az, zmin)
        zon = (az >= zmin).astype(float)
        sig = np.where(z >= 0, 1.0, -1.0)
        mu = np.einsum("ij,ij->i", u, ax)
        v = np.einsum("ij,ij->i", u, lat)
        S0, SA, SB, SD = spline
        C0, C0r, C0z = S0.ev(rho, azc), S0.ev(rho, azc, dx=1), S0.ev(rho, azc, dy=1)
        A, Ar, Az = SA.ev(rho, azc), SA.ev(rho, azc, dx=1), SA.ev(rho, azc, dy=1)
        B, Br, Bz = SB.ev(rho, azc), SB.ev(rho, azc, dx=1), SB.ev(rho, azc, dy=1)
        D, Dr, Dz = SD.ev(rho, azc), SD.ev(rho, azc, dx=1), SD.ev(rho, azc, dy=1)
        q = 1.0 - mu * mu
        C = C0 + sig * A * v + 0.5 * B * q + 0.5 * D * v * v
        C_r = C0r + sig * v * Ar + 0.5 * q * Br + 0.5 * v * v * Dr
        C_z = (C0z + sig * v * Az + 0.5 * q * Bz + 0.5 * v * v * Dz) * zon
        C_v = sig * A + D * v
        C_mu = -B * mu
        w, dw = _cutoff(r[k], mp.r1, mp.r2)
        U += float(np.sum(s * w * C))
        lat_hat = np.where(rho[:, None] > 1e-12, lat / np.maximum(rho, 1e-12)[:, None], 0.0)
        # d/d rv of s w C: d rho = lat_hat, d|z| = sign(z) a, d v = u - mu a, d r = rh
        grad = s[:, None] * ((dw * C)[:, None] * rh[k]
                             + w[:, None] * (C_r[:, None] * lat_hat + (C_z * sig)[:, None] * ax
                                             + C_v[:, None] * (u - mu[:, None] * ax)))
        F2[k] -= grad
        g_u = (s * w)[:, None] * (C_v[:, None] * lat + C_mu[:, None] * ax)     # d(s w C)/du
        T2[k] = T2[k] - _cross(u, g_u)
        T1[k] = -_cross(rk, F2[k]) - T2[k]
    Si, Sj = scatter if scatter is not None else scatter_matrices(len(p), i, j)
    F = Sj @ F2 - Si @ F2
    T = Sj @ T2 + Si @ T1
    if stats is not None:
        stats["max_force_N"] = max(stats["max_force_N"], float(np.abs(F).max()))
    return F, T, U


# ------------------------------------------------------------------ the magnet system
class MagnetSystem:
    def __init__(self, model: mujoco.MjModel, pitch: float, gap: float, mp: MagnetParams,
                 cache_dir: Path | None = None, tables: tuple | None = None, mags: list[dict] | None = None):
        """mags: the magnet list (body, pos, dir in the body frame); default the corner-edge layout()."""
        self.m, self.mp = model, mp
        self.mags = layout(pitch, gap, mp) if mags is None else mags
        self.n = len(self.mags)
        self.body = np.array([mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, g["body"]) for g in self.mags])
        assert (self.body >= 0).all()
        self.p_loc = np.array([g["pos"] for g in self.mags])
        self.d_loc = np.array([g["dir"] for g in self.mags])
        ii, jj = np.triu_indices(self.n, 1)
        keep = self.body[ii] != self.body[jj]            # same-body pairs are rigid: no effect, skipped
        self.ii_all, self.jj_all = ii[keep], jj[keep]
        self.ii, self.jj = self.ii_all, self.jj_all      # active neighbour list (all pairs until first rebuild)
        self.p_ref = None
        self.bodies = np.unique(self.body)
        self.scatter = scatter_matrices(self.n, self.ii, self.jj)
        self.body_sum = (self.body[None, :] == self.bodies[:, None]).astype(float)   # (n_bodies, n)
        self.spline = tables if tables is not None else near_field_tables(mp, cache_dir)
        self.zmin = mp.length + 0.0001
        self.stats: dict = {}
        self.reset_stats()
        self._buf = np.zeros(model.nv)

    def reset_stats(self) -> None:
        """Diagnostics only (no effect on forces). Reset at the start of every trial so stats are per trial."""
        self.stats = {"calls": 0, "clamped_z": 0, "near_perpendicular": 0, "max_force_N": 0.0,
                      "max_near_tilt_deg": 0.0, "list_rebuilds": 0, "list_pairs": len(self.ii)}

    def reset_neighbour_list(self) -> None:
        """Return the Verlet list to its just-constructed state (all pairs; rebuilt on the next call).

        Call at the start of every trial when one MagnetSystem is reused across trials: the force law does not depend
        on the list, but the floating-point summation order does, and magnet-coupled trajectories amplify that
        difference. Without the reset, a trial's result depends on which trial ran before it in the same process
        (found 2026-11-15, experiments/D8_alignment/results/diag_m4_2026-11-15/SUMMARY.md §3)."""
        self.ii, self.jj = self.ii_all, self.jj_all
        self.p_ref = None
        self.scatter = scatter_matrices(self.n, self.ii, self.jj)

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
        self.scatter = scatter_matrices(self.n, self.ii, self.jj)
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
                "magnet_mass_g": self.mp.magnet_mass * 1e3, "n_magnets": self.n, "n_pairs": int(len(self.ii))}
