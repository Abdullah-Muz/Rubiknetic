"""Passive piece-to-piece magnets for M1-geometry cubes (P-16): the M4 force law (P-23).

Moved here from experiments/D8_alignment/magnets.py (revision 2, 2026-11-14) for the M4 pre-registration (section 6
item 1). The force law is unchanged; the only additions are the quadrature and grid arguments of near_field_tables
(fast coarse tables for unit tests) and the in-module charge-model quadrature (formerly magnet_force.py).

Layout (D8_1b_DESIGN_PROPOSAL.md §3): the classic 48-magnet corner–edge system. Each corner carries 3 axial disc
magnets, one on each face toward its 3 edge neighbours; each edge carries 2, one on each face toward its 2 corner
neighbours. Centres and core carry none. Magnets sit on the face centre, recessed by a wall w. Polarity: corner
moments point out of the corner's face, edge moments point into the edge's face, so every facing corner-edge pair
is head-to-tail and attracts.
M6 alternative (P-58, 2026-11-18): core_layout(), 20 coaxial core-to-piece pairs at the real-mechanism radius, passed
to MagnetSystem(mags=...). The default layout and every default code path are unchanged.

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
Composite systems (P-67 item 2, 2026-11-21): a magnet dict may carry its own type, g["mp"] (a MagnetParams; default
the system's mp; see typed()). Types are compared on the force-law fields (diameter, length, grade, scale), so a
different wall alone does not make a new type. r1, r2, far_r1, far_r2 and skin must be equal across types (checked).
  * One type (every existing caller): the original single pair_forces call, unchanged, so forces, torques, energy,
    stats and neighbour-list rebuilds are bit-for-bit those of the single-type code.
  * Same-type pairs of a composite: pair_forces with that type's params and table, on the subset of the active
    neighbour list (each pair term is computed exactly as in a single-type system of that type).
  * Cross-type pairs: point dipoles with each magnet's own moment and the same far taper (cross_pair_forces); no
    near-field correction exists for unlike cylinders, so none is applied. A cross pair closer than r2 is counted in
    stats['near_cross_type'], which must stay 0 for the dipole term to be the model (the closest cross distance is
    stats['min_cross_type_r_m']). Per-type near-pair stats are reported as e.g. stats['max_near_tilt_deg[4x2_N35_s1]'].
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


# Fields that define a magnet TYPE for the force law (wall only places magnets in a layout), and fields that every type
# of one composite system must share (near-field range, far taper and neighbour-list skin are system-wide).
TYPE_FIELDS = ("diameter", "length", "grade", "scale")
SHARED_FIELDS = ("r1", "r2", "far_r1", "far_r2", "skin")


def type_key(mp: MagnetParams) -> tuple:
    return tuple(getattr(mp, f) for f in TYPE_FIELDS)


def type_label(mp: MagnetParams) -> str:
    """e.g. '4x2_N35_s1' (diameter x length in mm, grade, strength scale)."""
    return f"{mp.diameter*1e3:g}x{mp.length*1e3:g}_{mp.grade}_s{mp.scale:g}"


def typed(mags: list[dict], mp: MagnetParams) -> list[dict]:
    """Copies of the magnet dicts tagged with their own magnet type (for a composite MagnetSystem)."""
    return [{**g, "mp": mp} for g in mags]


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


# Real-mechanism radii of the pieces' innermost points along their radial lines (m): ER4 (GrabCAD real-mechanism cube,
# experiments/ER4_core_magnet_fit/REPORT.md) as used by ER5/ER6. Placing core-to-piece magnets here inside the B1 cube
# model is a documented abstraction (P-58): the magnets carry no collision geometry.
REAL_RADIUS = {"edge": 22.04e-3, "corner": 21.95e-3}


def core_layout(mp: MagnetParams, clearance: float = 2e-4, radius: dict | None = None) -> list[dict]:
    """M6 core-positioning layout (P-58, ER6): 20 attracting coaxial pairs, one per edge and corner, on the piece's
    radial line u. Piece magnet on the piece at u (R + wall + L/2); core magnet on the fixed `core` body at
    u (R - clearance - wall - L/2); both moments along +u. Centres carry none. Body frames are at the cube centre."""
    radius = REAL_RADIUS if radius is None else radius
    mags = []
    for home in HOME_POSITIONS:
        nz = np.count_nonzero(home)
        if nz == 1:
            continue
        kind = "edge" if nz == 2 else "corner"
        u = np.array(home, float) / np.sqrt(nz)
        R = radius[kind]
        mags.append({"body": cubie_name(home), "pos": u * (R + mp.wall + mp.length / 2), "dir": u.copy(),
                     "kind": kind})
        mags.append({"body": "core", "pos": u * (R - clearance - mp.wall - mp.length / 2), "dir": u.copy(),
                     "kind": "core_" + kind})
    assert len(mags) == 40, len(mags)
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


def cross_pair_forces(moment: np.ndarray, far_r1: float, far_r2: float, ii: np.ndarray, jj: np.ndarray,
                      p: np.ndarray, n: np.ndarray, scatter: tuple | None = None
                      ) -> tuple[np.ndarray, np.ndarray, float, np.ndarray]:
    """Pairs of unlike magnets (composite systems, P-67): point dipoles with per-magnet moments moment[k] (A m^2),
    with the far taper of pair_forces and no near-field correction. The same formulas as pair_forces' dipole part,
    with mabs * n replaced by moment[k] * n[k]. Returns per-magnet force (N), torque about its own centre (N m), the
    energy (J) and the pair centre distances r (m) so the caller can count pairs inside the near-field range."""
    c = MU0 / (4 * np.pi)
    i, j = ii, jj
    rv = p[j] - p[i]
    r = np.linalg.norm(rv, axis=1)
    rh = rv / r[:, None]
    m1, m2 = moment[i][:, None] * n[i], moment[j][:, None] * n[j]
    a1 = np.einsum("ij,ij->i", m1, rh)
    a2 = np.einsum("ij,ij->i", m2, rh)
    mm = np.einsum("ij,ij->i", m1, m2)
    wf, dwf = _cutoff(r, far_r1, far_r2)
    Ud = c / r ** 3 * (mm - 3 * a1 * a2)
    U = float(np.sum(wf * Ud))
    F2 = (3 * c / r ** 4)[:, None] * (a1[:, None] * m2 + a2[:, None] * m1 + mm[:, None] * rh
                                     - 5 * (a1 * a2)[:, None] * rh)
    F2 = wf[:, None] * F2 - (dwf * Ud)[:, None] * rh
    B1 = (c / r ** 3)[:, None] * (3 * a1[:, None] * rh - m1)
    B2 = (c / r ** 3)[:, None] * (3 * a2[:, None] * rh - m2)
    T2 = wf[:, None] * _cross(m2, B1)
    T1 = wf[:, None] * _cross(m1, B2)
    Si, Sj = scatter if scatter is not None else scatter_matrices(len(p), i, j)
    return Sj @ F2 - Si @ F2, Sj @ T2 + Si @ T1, U, r


def _pair_stats() -> dict:
    """The stats keys pair_forces updates (a scratch dict per same-type group of a composite system)."""
    return {"clamped_z": 0, "near_perpendicular": 0, "max_near_tilt_deg": 0.0, "max_force_N": 0.0}


# ------------------------------------------------------------------ the magnet system
class MagnetSystem:
    def __init__(self, model: mujoco.MjModel, pitch: float, gap: float, mp: MagnetParams,
                 cache_dir: Path | None = None, tables: tuple | None = None, mags: list[dict] | None = None,
                 type_tables: dict | None = None):
        """mags: the magnet list (body, pos, dir in the body frame, optional "mp"); default the corner-edge layout().
        mp is the system's (primary) magnet type: magnets without "mp" have it, and tables are its near-field tables.
        A magnet with an "mp" of another type makes the system composite (P-67); type_tables maps such a MagnetParams
        to its near-field tables (looked up by type; a missing one is built by near_field_tables(mp_k, cache_dir))."""
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
        self._setup_types(cache_dir, type_tables)
        self.zmin = mp.length + 0.0001
        self.stats: dict = {}
        self.reset_stats()
        self._buf = np.zeros(model.nv)

    # magnet types (composite systems, P-67) --------------------------------------------------------------------
    def _setup_types(self, cache_dir: Path | None, type_tables: dict | None) -> None:
        """types[0] is the system mp; type_of[k] indexes magnet k's type. One type: composite False, and nothing below
        is used by the force path."""
        keys, self.types = [type_key(self.mp)], [self.mp]
        type_of = []
        for g in self.mags:
            t = g.get("mp", self.mp)
            k = type_key(t)
            if k not in keys:
                keys.append(k)
                self.types.append(t)
            type_of.append(keys.index(k))
        self.type_of = np.array(type_of, dtype=int)
        if 0 not in type_of and self.n > 0:
            raise ValueError("the system MagnetParams must be the type of at least one magnet "
                             f"(system {type_label(self.mp)}, magnets {sorted({type_label(t) for t in self.types[1:]})})")
        for t in [g["mp"] for g in self.mags if "mp" in g] + list((type_tables or {}).keys()):   # every tagged magnet
            bad = [f for f in SHARED_FIELDS if getattr(t, f) != getattr(self.mp, f)]
            if bad:
                raise ValueError(f"magnet type {type_label(t)} differs from the system type in {bad}; near-field range, "
                                 "far taper and neighbour-list skin must be the same for every type and table")
        self.composite = len(self.types) > 1
        self.type_labels = [type_label(t) for t in self.types]
        if len(set(self.type_labels)) != len(self.type_labels):
            raise ValueError(f"distinct magnet types share a label: {self.type_labels}")
        if not self.composite:
            return
        by_key = {type_key(k): v for k, v in (type_tables or {}).items()}
        self.type_splines = [self.spline]
        for t in self.types[1:]:
            self.type_splines.append(by_key[type_key(t)] if type_key(t) in by_key else near_field_tables(t, cache_dir))
        self.moments = np.array([self.types[t].moment for t in self.type_of])
        self._build_groups()

    def _build_groups(self) -> None:
        """Split the active neighbour list into same-type groups and one cross-type group (pair order preserved)."""
        ti, tj = self.type_of[self.ii], self.type_of[self.jj]
        self._groups = []
        for t in range(len(self.types)):
            sel = (ti == t) & (tj == t)
            gi, gj = self.ii[sel], self.jj[sel]
            self._groups.append((t, gi, gj, scatter_matrices(self.n, gi, gj)))
        sel = ti != tj
        gi, gj = self.ii[sel], self.jj[sel]
        self._cross = (gi, gj, scatter_matrices(self.n, gi, gj))

    def reset_stats(self) -> None:
        """Diagnostics only (no effect on forces). Reset at the start of every trial so stats are per trial."""
        self.stats = {"calls": 0, "clamped_z": 0, "near_perpendicular": 0, "max_force_N": 0.0,
                      "max_near_tilt_deg": 0.0, "list_rebuilds": 0, "list_pairs": len(self.ii)}
        if self.composite:                  # extra keys only for composite systems (single-type stats are unchanged)
            self.stats.update({"near_cross_type": 0, "min_cross_type_r_m": None})
            for lab in self.type_labels:
                self.stats.update({f"clamped_z[{lab}]": 0, f"near_perpendicular[{lab}]": 0,
                                   f"max_near_tilt_deg[{lab}]": 0.0})

    def reset_neighbour_list(self) -> None:
        """Return the Verlet list to its just-constructed state (all pairs; rebuilt on the next call).

        Call at the start of every trial when one MagnetSystem is reused across trials: the force law does not depend
        on the list, but the floating-point summation order does, and magnet-coupled trajectories amplify that
        difference. Without the reset, a trial's result depends on which trial ran before it in the same process
        (found 2026-11-15, experiments/D8_alignment/results/diag_m4_2026-11-15/SUMMARY.md §3)."""
        self.ii, self.jj = self.ii_all, self.jj_all
        self.p_ref = None
        self.scatter = scatter_matrices(self.n, self.ii, self.jj)
        if self.composite:
            self._build_groups()

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
        if self.composite:
            self._build_groups()
        self.p_ref = p.copy()
        self.stats["list_rebuilds"] += 1
        self.stats["list_pairs"] = int(sel.sum())

    def forces(self, p: np.ndarray, n: np.ndarray, stats: bool = False) -> tuple[np.ndarray, np.ndarray, float]:
        """Per-magnet force (N) and torque about its own centre (N m), and the total energy (J)."""
        self._update_list(p)
        if not self.composite:              # the single-type path, unchanged
            return pair_forces(self.mp, self.spline, self.ii, self.jj, p, n, self.stats if stats else None,
                               self.scatter)
        F, T, U = np.zeros((self.n, 3)), np.zeros((self.n, 3)), 0.0
        for _, Fg, Tg, Ug in self.contributions(p, n, self.stats if stats else None):
            F += Fg
            T += Tg
            U += Ug
        if stats:
            self.stats["max_force_N"] = max(self.stats["max_force_N"], float(np.abs(F).max()))
        return F, T, U

    def contributions(self, p: np.ndarray, n: np.ndarray, stats: dict | None = None) -> list[tuple]:
        """Composite systems: (name, F, T, U) of each same-type group ("same:<type label>", pair_forces with that
        type's params and table) and of the cross-type group ("cross", cross_pair_forces), on the CURRENT neighbour
        list (forces() updates it first). Groups with no active pair are left out. With stats, pair_forces' near-pair
        stats are added per type and in total, and cross pairs inside r2 are counted in near_cross_type; max_force_N
        is left to forces(), which sees the total force. A single-type system returns its one pair_forces term."""
        if not self.composite:
            return [(f"same:{self.type_labels[0]}",
                     *pair_forces(self.mp, self.spline, self.ii, self.jj, p, n, stats, self.scatter))]
        out = []
        for t, gi, gj, sc in self._groups:
            if len(gi) == 0:
                continue
            st = _pair_stats() if stats is not None else None
            out.append((f"same:{self.type_labels[t]}",
                        *pair_forces(self.types[t], self.type_splines[t], gi, gj, p, n, st, sc)))
            if st is not None:
                lab = self.type_labels[t]
                for k in ("clamped_z", "near_perpendicular"):
                    stats[k] += st[k]
                    stats[f"{k}[{lab}]"] += st[k]
                stats["max_near_tilt_deg"] = max(stats["max_near_tilt_deg"], st["max_near_tilt_deg"])
                stats[f"max_near_tilt_deg[{lab}]"] = max(stats[f"max_near_tilt_deg[{lab}]"], st["max_near_tilt_deg"])
        gi, gj, sc = self._cross
        if len(gi):
            Fc, Tc, Uc, r = cross_pair_forces(self.moments, self.mp.far_r1, self.mp.far_r2, gi, gj, p, n, sc)
            out.append(("cross", Fc, Tc, Uc))
            if stats is not None:
                stats["near_cross_type"] += int(np.sum(r < self.mp.r2))
                rmin = float(r.min())
                old = stats["min_cross_type_r_m"]
                stats["min_cross_type_r_m"] = rmin if old is None else min(old, rmin)
        return out

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
        out = {"params": asdict(self.mp), "Br_T": self.mp.br, "moment_Am2": self.mp.moment,
               "magnet_mass_g": self.mp.magnet_mass * 1e3, "n_magnets": self.n, "n_pairs": int(len(self.ii))}
        if self.composite:                  # single-type output unchanged
            out["types"] = [{"label": lab, "params": asdict(t), "Br_T": t.br, "moment_Am2": t.moment,
                             "magnet_mass_g": t.magnet_mass * 1e3, "n_magnets": int(np.sum(self.type_of == k))}
                            for k, (lab, t) in enumerate(zip(self.type_labels, self.types))]
        return out
