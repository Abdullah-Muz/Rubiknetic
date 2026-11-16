"""Passive piece-to-piece magnets for M1-geometry cubes (P-16): the M4 force law (P-23).

Moved here from experiments/D8_alignment/magnets.py (revision 2, 2026-11-14) for the M4 pre-registration (section 6
item 1). The force law is unchanged; the only additions are the quadrature and grid arguments of near_field_tables
(fast coarse tables for unit tests) and the in-module charge-model quadrature (formerly magnet_force.py).

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
  Forces are -grad U. Torques: dipole m x B for far pairs; for near pairs, minus the orientation gradient of U on
  magnet j, with the partner's torque set by exact angular-momentum balance (T_i + T_j = -rv x F_j).
  REVISION 2 (2026-11-14): revision 1 used parallel-pair tables for tilted pairs as well (energy and a separate exact
  torque table). The strengthened V3 showed this fails for tilted pairs (force error 4.7 % / 11 % / 23 % at
  2 / 5 / 10 deg). The correction is now a second-order expansion in the tilt (near_field_tables), built from exact
  charge-model energies, and every force and torque derives from that single rotation-invariant potential, so energy
  and angular momentum are conserved for any tilt; its accuracy at a given tilt is what V3 tests.
Injection: mujoco.set_mjcb_passive adds the generalized forces to qfrc_passive inside mj_step (D5 detent.py
precedent), so the AuditedSim edit audit is unaffected. The callback reads ONLY body poses (xpos, xmat). It never
reads controls, time, commands, oracle state or switch state.
One magnet model per process (the MuJoCo passive callback is global).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import mujoco
import numpy as np
from scipy.interpolate import RectBivariateSpline

from rubiknetic.cube_logic.geometric import HOME_POSITIONS

MU0 = 4e-7 * np.pi


def disc_points(a: float, n_r: int = 24, n_phi: int = 64) -> tuple[np.ndarray, np.ndarray]:
    """Quadrature points (x, y) and weights (area) on a disc of radius a: Gauss-Legendre in r, uniform in phi."""
    xr, wr = np.polynomial.legendre.leggauss(n_r)
    r = 0.5 * a * (xr + 1)
    wr = 0.5 * a * wr * r
    phi = (np.arange(n_phi) + 0.5) * 2 * np.pi / n_phi
    R, P = np.meshgrid(r, phi, indexing="ij")
    W = np.repeat(wr[:, None], n_phi, axis=1) * (2 * np.pi / n_phi)
    return np.column_stack([(R * np.cos(P)).ravel(), (R * np.sin(P)).ravel()]), W.ravel()
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
TABLE_QUAD = (16, 48)      # disc quadrature (radial, angular) used to build the near-field tables


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
    tab = tau = None
    if path is not None and path.exists():
        with np.load(path) as f:
            # Reuse only a table on the same grid and quadrature (files written before "quad" was stored all used
            # the 16 x 48 default, the only quadrature this module has ever used for tables).
            quad = tuple(f["quad"]) if "quad" in f else (16, 48)
            if ("tau" in f and quad == TABLE_QUAD and np.array_equal(f["rho"], rho)
                    and np.array_equal(f["z"], zz)):
                tab, tau = f["dU"], f["tau"]
    if tab is None:
        R, Z = np.meshgrid(rho, zz, indexing="ij")
        a = mp.diameter / 2
        tab = (_exact_parallel_energy(a, mp.length, mp.moment, R, Z, *TABLE_QUAD)
               - _dipole_parallel_energy(mp.moment, R, Z))
        tau = _exact_parallel_torque(a, mp.length, mp.moment, R, Z, *TABLE_QUAD)
        if path is not None:
            np.savez(path, dU=tab, tau=tau, rho=rho, z=zz, quad=np.array(TABLE_QUAD))
    # Fit on the grid mirrored to negative rho (energy even, scalar torque odd in signed rho), so the fitted energy
    # has zero slope at rho = 0. A one-sided fit leaves a nonzero slope there (measured 15 mN for 4x2 mm at 3 mm),
    # which is a spurious cusp force toward exact alignment (review finding, 2026-11-14).
    rho_m = np.concatenate([-rho[:0:-1], rho])
    tab_m = np.concatenate([tab[:0:-1], tab])
    tau_m = np.concatenate([-tau[:0:-1], tau])
    spl = (RectBivariateSpline(rho_m, zz, tab_m, kx=3, ky=3), RectBivariateSpline(rho_m, zz, tau_m, kx=3, ky=3))
    _TABLE_CACHE[key] = spl
    return spl


# ------------------------------------------------------------------ tilt-aware near-field tables (revision 2)
TILT_H_DEG = 1.5           # finite-difference tilt used to build the second-order tilt expansion


def _exact_energy_tilted(a: float, L: float, m_abs: float, rho: float, z: float, R2: np.ndarray,
                         n_r: int, n_phi: int) -> float:
    """Charge-model energy (J): magnet 1 centred at the origin with axis +z; magnet 2 centred at (rho, 0, z) with its
    body frame rotated by R2 (axis R2 @ z_hat). Magnet 2's quadrature pattern is magnet 1's pattern rotated by R2, so
    the discretisation is identical for every tilt (no spurious anisotropy)."""
    sigma = m_abs / (np.pi * a * a * L)
    pts, w = disc_points(a, n_r, n_phi)
    P = np.column_stack([pts, np.zeros(len(pts))])
    ww = w[:, None] * w[None, :]
    c2 = np.array([rho, 0.0, z])
    u = 0.0
    for za, qa in ((+L / 2, 1.0), (-L / 2, -1.0)):
        x1 = P + np.array([0.0, 0.0, za])
        for zb, qb in ((+L / 2, 1.0), (-L / 2, -1.0)):
            x2 = c2 + (P + np.array([0.0, 0.0, zb])) @ R2.T
            d = x2[None, :, :] - x1[:, None, :]
            u += qa * qb * float(np.sum(ww / np.sqrt(np.einsum("ijk,ijk->ij", d, d))))
    return MU0 / (4 * np.pi) * sigma * sigma * u


def _dipole_energy(m_abs: float, rv: np.ndarray, n1: np.ndarray, n2: np.ndarray) -> float:
    r = float(np.linalg.norm(rv))
    rh = rv / r
    return MU0 / (4 * np.pi) * m_abs ** 2 * (float(n1 @ n2) - 3 * float(n1 @ rh) * float(n2 @ rh)) / r ** 3


def _rot(axis: int, ang: float) -> np.ndarray:
    c, s = np.cos(ang), np.sin(ang)
    if axis == 0:
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])      # axis == 1 (y)


def near_field_tables(mp: MagnetParams, cache_dir: Path | None = None, quad: tuple[int, int] = TABLE_QUAD,
                      n_rho: int = 37, n_z: int = 31) -> tuple:
    """Tilt-aware near-field correction C = U_exact - U_dipole for nearly parallel pairs (revision 2, 2026-11-14).

    Frame: magnet 1 axis a, magnet 2 axis u = s n2 (s = sign(n1.n2)), offset rv = p2 - p1, z = rv.a,
    lat = rv - z a, rho = |lat|, v = u.lat, mu = u.a. Second-order expansion in the tilt of u away from a:
        C = C0(rho, |z|) + sign(z) A(rho, |z|) v + B(rho, |z|) (1 - mu^2) / 2 + D(rho, |z|) v^2 / 2
    (C is even in the tilt component normal to the (a, lat) plane by mirror symmetry; the z -> -z reflection flips
    the in-plane tilt, hence sign(z)). Coefficients from central differences of the exact charge-model energy at
    +-TILT_H_DEG: A = C_l / rho, B = C_tt, D = (C_ll - C_tt) / rho^2. All four are even in rho and fitted on the
    mirrored grid, so the potential is smooth through rho = 0. Returns splines (C0, A, B, D) and diagnostics."""
    key = ("tilt", mp.diameter, mp.length, mp.br, mp.scale, mp.r2, TILT_H_DEG, tuple(quad), n_rho, n_z)
    if key in _TABLE_CACHE:
        return _TABLE_CACHE[key]
    rho = np.linspace(0.0, mp.r2 + 0.001, n_rho)
    zz = np.linspace(mp.length + 0.0001, mp.r2 + 0.001, n_z)
    path, data = None, None
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = cache_dir / (f"tilt_{mp.diameter*1e3:g}x{mp.length*1e3:g}_{mp.br:g}T_s{mp.scale:g}_r{mp.r2*1e3:g}"
                            f"_h{TILT_H_DEG:g}_q{quad[0]}x{quad[1]}.npz")
        if path.exists():
            with np.load(path) as f:
                if np.array_equal(f["rho"], rho) and np.array_equal(f["z"], zz):
                    data = {k: f[k] for k in ("C0", "Cp", "Cm", "Ct")}
    if data is None:
        a, L, m = mp.diameter / 2, mp.length, mp.moment
        h = np.radians(TILT_H_DEG)
        rots = {"C0": np.eye(3), "Cp": _rot(1, h), "Cm": _rot(1, -h), "Ct": _rot(0, h)}
        data = {k: np.zeros((len(rho), len(zz))) for k in rots}
        e1 = np.array([0.0, 0.0, 1.0])
        for ir, rr in enumerate(rho):
            for iz, z in enumerate(zz):
                rv = np.array([rr, 0.0, z])
                for k, R in rots.items():
                    data[k][ir, iz] = (_exact_energy_tilted(a, L, m, rr, z, R, *quad)
                                       - _dipole_energy(m, rv, e1, R @ e1))
        if path is not None:
            np.savez(path, rho=rho, z=zz, h_deg=TILT_H_DEG, quad=np.array(quad), **data)
    sh = np.sin(np.radians(TILT_H_DEG))
    C0, Cp, Cm, Ct = data["C0"], data["Cp"], data["Cm"], data["Ct"]
    Cl = (Cp - Cm) / (2 * sh)
    Cll = (Cp + Cm - 2 * C0) / sh ** 2
    Ctt = 2 * (Ct - C0) / sh ** 2
    pos = rho[1:]
    A = Cl[1:] / pos[:, None]
    D = (Cll[1:] - Ctt[1:]) / pos[:, None] ** 2

    def even(x, t, with_zero=True):
        if with_zero:
            return RectBivariateSpline(np.concatenate([-x[:0:-1], x]), zz, np.concatenate([t[:0:-1], t]), kx=3, ky=3)
        return RectBivariateSpline(np.concatenate([-x[::-1], x]), zz, np.concatenate([t[::-1], t]), kx=3, ky=3)

    spl = (even(rho, C0), even(pos, A, False), even(rho, Ctt), even(pos, D, False))
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
                 cache_dir: Path | None = None, tables: tuple | None = None):
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
        self.spline = tables if tables is not None else near_field_tables(mp, cache_dir)
        self.zmin = mp.length + 0.0001
        self.stats: dict = {}
        self.reset_stats()
        self._buf = np.zeros(model.nv)

    def reset_stats(self) -> None:
        """Diagnostics only (no effect on forces). Reset at the start of every trial so stats are per trial."""
        self.stats = {"calls": 0, "clamped_z": 0, "near_perpendicular": 0, "max_force_N": 0.0,
                      "max_near_tilt_deg": 0.0, "list_rebuilds": 0, "list_pairs": len(self.ii)}

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
