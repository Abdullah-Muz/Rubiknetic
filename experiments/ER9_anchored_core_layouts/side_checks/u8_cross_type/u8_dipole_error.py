"""U8 side check (Part G, option 2): how wrong is the point-dipole force law for CROSS-TYPE magnet pairs?

Part G's arms put M5's 48 corner-edge magnets (4 x 2 mm N35, scale 1, magnets.layout) and C52's on-axis core pairs
(4 x 3 mm N52 by default (U3), scale 1, magnets.core_layout, clearance 0.2 mm) in one composite MagnetSystem. Cross-type
pairs (one 4x2, one 4x3) get only the point-dipole term (magnets.cross_pair_forces), with no near-field correction.
This script measures, for the cross-type pair geometries that actually occur in B1 kinematics, the dipole force and
torques against a finite-size reference: the magnetic surface-charge model of two uniformly magnetised cylinders
(mu_r = 1), i.e. the same model and the same disc quadrature (magnets.disc_points) that magnets.py uses to build its
same-type near-field tables (magnets._exact_energy_tilted), generalised to two different cylinders. Forces and torques
are summed directly from the charge-charge forces (no finite differences).

Geometry (no MuJoCo is run; no model is built): magnet positions/directions come from magnets.layout(pitch, gap, MP42)
and magnets.core_layout(MP43, 0.2 mm) exactly as tests/test_magnets_composite.py builds the PG20 composite. In B1 every
piece body frame sits at the cube centre and pieces rotate about it (ball joint at the origin, m1_model.py), so a pose
is one rotation per piece body about the origin; the core is fixed. Poses: home; rigid turns of each of the 6 faces,
-90..90 deg in 0.5 deg steps; and random independent piece rotations (rotation-vector components N(0, sigma), the
perturbation form of test_magnets_composite._set_pose) on top of rigid turns.

Usage (WSL, repo root; single-threaded):
    OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH=src \
        ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/side_checks/u8_cross_type/u8_dipole_error.py
Writes results.json next to this file. Kinematic/static only.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import json  # noqa: E402
import platform  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from dataclasses import asdict, replace  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
from scipy.spatial.transform import Rotation  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))

from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_physics import magnets as M  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params, cubie_name  # noqa: E402

# ---------------------------------------------------------------- inputs (as tests/test_magnets_composite.py)
PITCH = M1Params().pitch                      # 19 mm
GAP = 5e-5                                    # M5 / ER7 piece gap
CLEAR = 2e-4                                  # C52 core clearance
MP42 = M.MagnetParams()                       # M5: 4 x 2 mm N35, scale 1
MP43 = M.MagnetParams(diameter=0.004, length=0.003, grade="N52")   # C52 / Part G default (U3): 4 x 3 mm N52, scale 1
QUAD = (16, 48)                               # = magnets.TABLE_QUAD, the quadrature of the repo's near-field tables
QUAD_LADDER = [(8, 24), (12, 36), (16, 48), (24, 72), (32, 96)]
SEED = 8808                                   # tilt Monte Carlo
SIGMAS_DEG = (0.5, 1.0, 2.0)
N_MC_PER_FACE = 40
MC_EVAL_BELOW = 0.0085                        # MC pairs closer than this (m) are candidates for the reference model
MC_N_CLOSEST, MC_N_RANDOM = 20, 30            # per sigma: the closest candidates plus a random sample of the rest
SWEEP_MM = [7.3, 7.6, 7.9, 8.178, 8.5, 9.0, 9.335, 10.0, 12.0, 15.0, 20.0]
C = M.MU0 / (4 * np.pi)


# ---------------------------------------------------------------- reference model: surface charges of two cylinders
def frame(n: np.ndarray) -> np.ndarray:
    """Right-handed orthonormal frame with third column n."""
    n = n / np.linalg.norm(n)
    h = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = np.cross(h, n)
    e1 /= np.linalg.norm(e1)
    return np.column_stack([e1, np.cross(n, e1), n])


def charges(c: np.ndarray, R: np.ndarray, mp: M.MagnetParams, quad) -> tuple[np.ndarray, np.ndarray]:
    """Charge points and charges (A m) of a uniformly magnetised cylinder centred at c with body frame R (axis R[:,2]):
    sigma = +-|M| on the north (+L/2) / south (-L/2) faces, |M| = m / V (as magnets._exact_energy_tilted)."""
    a, L = mp.diameter / 2, mp.length
    sigma = mp.moment / (np.pi * a * a * L)
    pts, w = M.disc_points(a, *quad)
    P = np.column_stack([pts, np.zeros(len(pts))])
    X = np.vstack([c + (P + [0, 0, +L / 2]) @ R.T, c + (P + [0, 0, -L / 2]) @ R.T])
    Q = np.concatenate([sigma * w, -sigma * w])
    return X, Q


def ref_pair(c1, R1, mp1, c2, R2, mp2, quad=QUAD, chunk=512) -> dict:
    """Charge-model energy (J), force on magnet 2 (N; force on 1 is its negative), torques on 1 and 2 about their own
    centres (N m)."""
    X1, Q1 = charges(c1, R1, mp1, quad)
    X2, Q2 = charges(c2, R2, mp2, quad)
    U = 0.0
    f2 = np.zeros_like(X2)
    T1 = np.zeros(3)
    for s in range(0, len(X1), chunk):
        x1, q1 = X1[s:s + chunk], Q1[s:s + chunk]
        d = X2[None, :, :] - x1[:, None, :]
        inv = 1.0 / np.sqrt(np.einsum("ijk,ijk->ij", d, d))
        qq = q1[:, None] * Q2[None, :]
        U += float(np.sum(qq * inv))
        f = (qq * inv ** 3)[:, :, None] * d                  # force on charge j of 2 from charge i of 1
        f2 += f.sum(axis=0)
        T1 += np.cross(x1 - c1, -f.sum(axis=1)).sum(axis=0)
    F2 = C * f2.sum(axis=0)
    T2 = C * np.cross(X2 - c2, f2).sum(axis=0)
    return {"U": C * U, "F2": F2, "T1": C * T1, "T2": T2}


def volume_dipoles(c, n, mp, nr, nphi, nz):
    """Independent check model: the cylinder cut into nr x nphi x nz equal-volume cells, one point dipole per cell."""
    a, L = mp.diameter / 2, mp.length
    Mag = mp.moment / (np.pi * a * a * L)
    edges = a * np.sqrt(np.arange(nr + 1) / nr)                     # equal-area rings
    rc = 0.5 * (edges[1:] + edges[:-1])
    ph = (np.arange(nphi) + 0.5) * 2 * np.pi / nphi
    zc = (np.arange(nz) + 0.5) * L / nz - L / 2
    Rr, Pp, Zz = np.meshgrid(rc, ph, zc, indexing="ij")
    R = frame(n)
    loc = np.column_stack([(Rr * np.cos(Pp)).ravel(), (Rr * np.sin(Pp)).ravel(), Zz.ravel()])
    dv = np.pi * a * a * L / loc.shape[0]
    return c + loc @ R.T, Mag * dv * n


def volume_dipole_pair(c1, n1, mp1, c2, n2, mp2, res=(8, 32, 6)) -> dict:
    X1, m1 = volume_dipoles(c1, n1, mp1, *res)
    X2, m2 = volume_dipoles(c2, n2, mp2, *res)
    d = X2[None, :, :] - X1[:, None, :]
    r = np.sqrt(np.einsum("ijk,ijk->ij", d, d))
    rh = d / r[:, :, None]
    a1, a2, mm = rh @ m1, rh @ m2, float(m1 @ m2)
    f = (3 * C / r ** 4)[:, :, None] * (a1[:, :, None] * m2 + a2[:, :, None] * m1 + mm * rh
                                        - 5 * (a1 * a2)[:, :, None] * rh)      # force on dipole j of 2
    B1 = (C / r ** 3)[:, :, None] * (3 * a1[:, :, None] * rh - m1)            # field of i at j
    B2 = (C / r ** 3)[:, :, None] * (3 * a2[:, :, None] * rh - m2)            # field of j at i
    fj = f.sum(axis=0)
    T2 = np.cross(m2, B1.sum(axis=0)).sum(axis=0) + np.cross(X2 - c2, fj).sum(axis=0)
    T1 = np.cross(m1, B2.sum(axis=1)).sum(axis=0) + np.cross(X1 - c1, -f.sum(axis=1)).sum(axis=0)
    return {"F2": fj.sum(axis=0), "T1": T1, "T2": T2}


def dip_pair(c1, n1, mp1, c2, n2, mp2, taper=True) -> dict:
    """The simulation's own cross-type term: magnets.cross_pair_forces (point dipoles, far taper; taper=False
    disables the taper for the far-field limit check)."""
    p, n = np.array([c1, c2]), np.array([n1, n2])
    mom = np.array([mp1.moment, mp2.moment])
    r1, r2 = (mp1.far_r1, mp1.far_r2) if taper else (1.0, 2.0)
    F, T, U, _ = M.cross_pair_forces(mom, r1, r2, np.array([0]), np.array([1]), p, n)
    return {"U": U, "F2": F[1], "F1": F[0], "T1": T[0], "T2": T[1]}


def compare(c1, n1, mp1, c2, n2, mp2, quad=QUAD, R1=None, R2=None) -> dict:
    """Point-dipole vs reference for one pair (magnet 1 = mp1 at c1 with axis n1, etc.)."""
    R1 = frame(n1) if R1 is None else R1
    R2 = frame(n2) if R2 is None else R2
    ref = ref_pair(c1, R1, mp1, c2, R2, mp2, quad)
    dip = dip_pair(c1, n1, mp1, c2, n2, mp2)
    rv = c2 - c1
    r = float(np.linalg.norm(rv))
    rh = rv / r
    Fr, Fd = ref["F2"], dip["F2"]
    ang = lambda a, b: float(np.degrees(np.arccos(np.clip(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)), -1, 1))))  # noqa: E731
    out = {
        "r_mm": r * 1e3,
        "angle_between_axes_deg": ang(n1, n2),
        "angle_r_to_axis1_deg": ang(rh, n1), "angle_r_to_axis2_deg": ang(rh, n2),
        "U_dip_J": dip["U"], "U_ref_J": ref["U"],
        "F_on_2_dip_N": Fd.tolist(), "F_on_2_ref_N": Fr.tolist(),
        "absF_dip_N": float(np.linalg.norm(Fd)), "absF_ref_N": float(np.linalg.norm(Fr)),
        "absF_rel_err": float(np.linalg.norm(Fd) / np.linalg.norm(Fr) - 1),
        "F_vec_rel_err": float(np.linalg.norm(Fd - Fr) / np.linalg.norm(Fr)),
        "F_along_r_dip_N": float(Fd @ rh), "F_along_r_ref_N": float(Fr @ rh),
        "F_angle_err_deg": ang(Fd, Fr),
        "absF_err_N": float(np.linalg.norm(Fd - Fr)),
    }
    for k, cc, mk, other in (("1", c1, mp1.moment, mp2.moment * n2), ("2", c2, mp2.moment, mp1.moment * n1)):
        Td, Tr = dip["T" + k], ref["T" + k]
        sF = 1.0 if k == "2" else -1.0
        # |m_k| |B_dip at k|: the largest torque the (dipole) field could exert on magnet k; normalising by it keeps
        # the own-torque error meaningful when the actual torque is small because m_k is nearly along B
        Bk = C / r ** 3 * (3 * float(other @ rh) * rh - other)
        out[f"T{k}_own_err_over_mB"] = float(np.linalg.norm(Td - Tr) / (mk * np.linalg.norm(Bk)))
        out[f"T{k}_own_ref_over_mB"] = float(np.linalg.norm(Tr) / (mk * np.linalg.norm(Bk)))
        # torque about the cube centre on this magnet's body (what moves a piece): T_own + p x F
        Bd, Br = Td + np.cross(cc, sF * Fd), Tr + np.cross(cc, sF * Fr)
        out.update({
            f"T{k}_own_dip_Nm": Td.tolist(), f"T{k}_own_ref_Nm": Tr.tolist(),
            f"T{k}_own_abs_err_mNm": float(np.linalg.norm(Td - Tr) * 1e3),
            f"T{k}_own_rel_err": float(np.linalg.norm(Td - Tr) / max(np.linalg.norm(Tr), 1e-300)),
            f"T{k}_about_centre_dip_Nm": Bd.tolist(), f"T{k}_about_centre_ref_Nm": Br.tolist(),
            f"T{k}_about_centre_abs_err_mNm": float(np.linalg.norm(Bd - Br) * 1e3),
            f"T{k}_about_centre_rel_err": float(np.linalg.norm(Bd - Br) / max(np.linalg.norm(Br), 1e-300)),
        })
    return out


# ---------------------------------------------------------------- geometry: PG20 composite, B1 kinematics
def build_mags(mp43=MP43):
    mags = M.typed(M.layout(PITCH, GAP, MP42), MP42) + M.typed(M.core_layout(mp43, CLEAR), mp43)
    home = {cubie_name(h): np.array(h, float) for h in HOME_POSITIONS}
    return mags, home


def pose(mags, home, face=None, angle_deg=0.0, rng=None, sigma_deg=0.0):
    """World positions/directions. Rigid turn of the layer with outward normal `face`, then (rng) an independent
    small rotation of every piece body in its own frame (cur * dq, as _set_pose). Returns p, n, body rotations."""
    rots = {}
    for b in home:
        R = Rotation.identity()
        if face is not None and int(np.dot(home[b], face)) == 1:
            R = Rotation.from_rotvec(np.radians(angle_deg) * np.asarray(face, float))
        if rng is not None:
            R = R * Rotation.from_rotvec(np.radians(rng.normal(0, sigma_deg, 3)))
        rots[b] = R.as_matrix()
    p = np.array([rots[g["body"]] @ g["pos"] if g["body"] != "core" else g["pos"] for g in mags])
    n = np.array([rots[g["body"]] @ g["dir"] if g["body"] != "core" else g["dir"] for g in mags])
    return p, n, rots


def cross_pairs(mags):
    """(i, j, class) for every 4x2 / 4x3 pair on different bodies; i is the 4x2 magnet."""
    out = []
    for i, gi in enumerate(mags):
        if gi["mp"] is not MP42:
            continue
        for j, gj in enumerate(mags):
            if gj["mp"] is MP42 or gi["body"] == gj["body"]:
                continue
            out.append((i, j, "core4x3" if gj["body"] == "core" else "piece4x3"))
    return out


def label(mags, i, j):
    return f"{mags[i]['kind']}4x2@{mags[i]['body']} - {mags[j]['kind']}4x3@{mags[j]['body']}"


FACES = [(0, 0, 1), (0, 0, -1), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)]


def main() -> None:
    t0 = time.time()
    mags, home = build_mags()
    cp = cross_pairs(mags)
    I = np.array([x[0] for x in cp]); J = np.array([x[1] for x in cp])
    is_piece = np.array([x[2] == "piece4x3" for x in cp])
    res: dict = {"inputs": {"pitch_m": PITCH, "gap_m": GAP, "core_clearance_m": CLEAR, "MP42": asdict(MP42),
                            "MP43": asdict(MP43), "moment_4x2_Am2": MP42.moment, "moment_4x3_Am2": MP43.moment,
                            "quad": QUAD, "seed": SEED, "sigmas_deg": SIGMAS_DEG, "n_mc_per_face": N_MC_PER_FACE,
                            "python": sys.version, "numpy": np.__version__, "platform": platform.platform(),
                            "repo_src": str(REPO / "src")}}

    # ---- 0. model self-checks -------------------------------------------------------------------------------
    # (a) identical cylinders: our charges() reproduces the repo's _exact_energy_tilted exactly
    chk = {}
    R2 = Rotation.from_rotvec([0.03, -0.02, 0.01]).as_matrix()
    c2 = np.array([0.003, 0.0, 0.005])
    for mp in (MP42, MP43):
        u_repo = M._exact_energy_tilted(mp.diameter / 2, mp.length, mp.moment, 0.003, 0.005, R2, *QUAD)
        u_here = ref_pair(np.zeros(3), np.eye(3), mp, c2, R2, mp)["U"]
        chk[f"identical_{M.type_label(mp)}_energy_rel_diff_vs_repo"] = float(u_here / u_repo - 1)
    # (b) force and torque vs finite differences of the reference energy (cross pair, close, oblique)
    c1, n1 = np.zeros(3), np.array([0.0, 0.0, 1.0])
    c2 = np.array([0.0045, 0.002, 0.0055]); n2 = np.array([0.4, 0.3, 0.866]); n2 /= np.linalg.norm(n2)
    R1, R2 = frame(n1), frame(n2)
    base = ref_pair(c1, R1, MP42, c2, R2, MP43)
    h = 1e-7
    fd = np.array([-(ref_pair(c1, R1, MP42, c2 + h * e, R2, MP43)["U"] - ref_pair(c1, R1, MP42, c2 - h * e, R2, MP43)["U"])
                   / (2 * h) for e in np.eye(3)])
    ha = 1e-6
    tq = np.array([-(ref_pair(c1, R1, MP42, c2, Rotation.from_rotvec(ha * e).as_matrix() @ R2, MP43)["U"]
                     - ref_pair(c1, R1, MP42, c2, Rotation.from_rotvec(-ha * e).as_matrix() @ R2, MP43)["U"])
                   / (2 * ha) for e in np.eye(3)])
    chk["force_vs_minus_grad_U_rel_diff"] = float(np.linalg.norm(fd - base["F2"]) / np.linalg.norm(base["F2"]))
    chk["torque2_vs_minus_dU_dtheta_rel_diff"] = float(np.linalg.norm(tq - base["T2"]) / np.linalg.norm(base["T2"]))
    # (c) angular-momentum balance of the reference: T1 + T2 + (c2 - c1) x F2 = 0
    chk["ang_mom_balance_rel"] = float(np.linalg.norm(base["T1"] + base["T2"] + np.cross(c2 - c1, base["F2"]))
                                       / np.linalg.norm(base["T2"]))
    # (d) independent model: volume cells as point dipoles, refined, against the surface-charge reference, for a
    #     coaxial 4x2 pair at 8 mm (the largest same-type error found) and the home-closest cross pair's geometry
    #     (edge 4x2 at the origin, axis -x; corner 4x3 at its home offset; values from layout()/core_layout())
    vd_cases = {"coaxial_4x2_4x2_8mm": (np.zeros(3), np.array([0, 0, 1.0]), MP42,
                                        np.array([0, 0, 0.008]), np.array([0, 0, 1.0]), MP42)}
    _m, _ = build_mags()
    ge = [g for g in _m if g["body"] == "cubie_nn0" and g["mp"] is MP42]
    gc = [g for g in _m if g["body"] == "cubie_nnn" and g["mp"] is MP43][0]
    ge = min(ge, key=lambda g: np.linalg.norm(g["pos"] - gc["pos"]))
    vd_cases["home_closest_cross"] = (ge["pos"], ge["dir"], MP42, gc["pos"], gc["dir"], MP43)
    vd = {}
    for nm, (a1, b1, t1, a2, b2, t2) in vd_cases.items():
        rr = ref_pair(a1, frame(b1), t1, a2, frame(b2), t2)
        dd = dip_pair(a1, b1, t1, a2, b2, t2)
        rows = []
        for resn in ((4, 16, 3), (6, 24, 4), (8, 32, 5)):
            vv = volume_dipole_pair(a1, b1, t1, a2, b2, t2, resn)
            rows.append({"cells": resn, "F_rel_diff_vs_ref": float(np.linalg.norm(vv["F2"] - rr["F2"]) / np.linalg.norm(rr["F2"])),
                         "T1_rel_diff_vs_ref": float(np.linalg.norm(vv["T1"] - rr["T1"]) / np.linalg.norm(rr["T1"]) if np.linalg.norm(rr["T1"]) > 1e-12 else np.linalg.norm(vv["T1"])),
                         "T2_rel_diff_vs_ref": float(np.linalg.norm(vv["T2"] - rr["T2"]) / np.linalg.norm(rr["T2"]) if np.linalg.norm(rr["T2"]) > 1e-12 else np.linalg.norm(vv["T2"]))})
        vd[nm] = {"r_mm": float(np.linalg.norm(a2 - a1) * 1e3),
                  "point_dipole_F_rel_err_vs_ref": float(np.linalg.norm(dd["F2"] - rr["F2"]) / np.linalg.norm(rr["F2"])),
                  "volume_dipole_ladder": rows}
    chk["volume_dipole_cross_check"] = vd
    res["self_checks"] = chk
    print("self-checks", json.dumps(chk, indent=1), flush=True)

    # ---- 1. geometry scan ------------------------------------------------------------------------------------
    def dists(p):
        return np.linalg.norm(p[J] - p[I], axis=1)

    p0, n0, _ = pose(mags, home)
    r0 = dists(p0)
    k_home = int(np.argmin(np.where(is_piece, r0, np.inf)))
    geo = {"home_min_piece_cross_mm": float(r0[is_piece].min() * 1e3), "home_min_pair": label(mags, I[k_home], J[k_home]),
           "home_n_piece_cross_within_10mm": int(np.sum(is_piece & (r0 < 0.010))),
           "home_min_core_cross_mm": float(r0[~is_piece].min() * 1e3)}
    turn = {"min_mm": np.inf}
    core = {"min_mm": np.inf}
    worst_ang = {}                    # worst angle per face (piece cross pairs), also used by the tilt Monte Carlo
    for face in FACES:
        best = (np.inf, 0.0)
        for ang in np.arange(-90.0, 90.0 + 1e-9, 0.5):
            p, n, _ = pose(mags, home, face, ang)
            r = dists(p)
            rc = np.where(is_piece, np.inf, r)
            kc = int(np.argmin(rc))
            if rc[kc] < core["min_mm"] / 1e3 - 1e-12:
                core = {"min_mm": float(rc[kc] * 1e3), "face": face, "angle_deg": float(ang), "k": kc,
                        "pair": label(mags, I[kc], J[kc])}
            rp = np.where(is_piece, r, np.inf)
            k = int(np.argmin(rp))
            best = min(best, (float(rp[k]), float(ang)))
            if rp[k] < turn["min_mm"] / 1e3 - 1e-12:
                turn = {"min_mm": float(rp[k] * 1e3), "face": face, "angle_deg": float(ang), "k": k,
                        "pair": label(mags, I[k], J[k])}
        worst_ang[face] = best
    # refine the core-class minimum to 0.01 deg around its 0.5 deg grid point
    for ang in np.arange(core["angle_deg"] - 0.5, core["angle_deg"] + 0.5 + 1e-9, 0.01):
        r = dists(pose(mags, home, core["face"], ang)[0])
        rc = np.where(is_piece, np.inf, r)
        kc = int(np.argmin(rc))
        if rc[kc] < core["min_mm"] / 1e3 - 1e-12:
            core.update({"min_mm": float(rc[kc] * 1e3), "angle_deg": float(ang), "k": kc,
                         "pair": label(mags, I[kc], J[kc])})
    geo["rigid_turn_min_piece_cross"] = {x: turn[x] for x in ("min_mm", "face", "angle_deg", "pair")}
    geo["rigid_turn_min_core_cross"] = {x: core[x] for x in ("min_mm", "face", "angle_deg", "pair")}
    geo["core_cross_radius_bound_mm"] = float((min(np.linalg.norm(g["pos"]) for g in mags if g["mp"] is MP42)
                                               - max(np.linalg.norm(g["pos"]) for g in mags if g["body"] == "core"))
                                              * 1e3)
    geo["worst_angle_per_face"] = {str(f): {"min_mm": v[0] * 1e3, "angle_deg": v[1]} for f, v in worst_ang.items()}
    print("geometry", json.dumps(geo, indent=1), flush=True)
    res["geometry"] = geo

    # ---- 1b. deterministic worst-case tilt: rotate the home-closest pair's pieces by theta about the worst axis ----
    def pair_geom(face, ang, k):
        p, n, _ = pose(mags, home, face, ang)
        return p[I[k]], n[I[k]], p[J[k]], n[J[k]]

    b_edge, b_corner = mags[I[k_home]]["body"], mags[J[k_home]]["body"]
    nax = 400
    gold = np.pi * (3 - np.sqrt(5))
    zz_ = 1 - 2 * (np.arange(nax) + 0.5) / nax
    axes = np.column_stack([np.sqrt(1 - zz_ ** 2) * np.cos(gold * np.arange(nax)),
                            np.sqrt(1 - zz_ ** 2) * np.sin(gold * np.arange(nax)), zz_])
    is_e = np.array([g["body"] == b_edge for g in mags])
    is_c = np.array([g["body"] == b_corner for g in mags])
    det_tilt = []
    for th in (0.25, 0.5, 0.71, 1.0, 1.5, 2.0, 3.0, 5.0):
        best = (np.inf, None)
        for mode in ("corner_only", "edge_only", "split"):
            for ax in axes:
                p, n = p0.copy(), n0.copy()
                for sel, s in ((is_c, {"corner_only": 1.0, "edge_only": 0.0, "split": -0.5}[mode]),
                               (is_e, {"corner_only": 0.0, "edge_only": 1.0, "split": 0.5}[mode])):
                    if s:
                        Rm = Rotation.from_rotvec(np.radians(th * s) * ax).as_matrix()
                        p[sel], n[sel] = p0[sel] @ Rm.T, n0[sel] @ Rm.T
                rp = np.where(is_piece, dists(p), np.inf)
                k = int(np.argmin(rp))
                if rp[k] < best[0]:
                    best = (float(rp[k]), (mode, ax.tolist(), k, p[I[k]], n[I[k]], p[J[k]], n[J[k]]))
        mode, ax, k, c1, n1, c2, n2 = best[1]
        row = {"rel_tilt_deg": th, "mode": mode, "axis": ax, "pair": label(mags, I[k], J[k]),
               "geom": [c1.tolist(), n1.tolist(), c2.tolist(), n2.tolist()], **compare(c1, n1, MP42, c2, n2, MP43)}
        det_tilt.append(row)
        print("det tilt %.2f deg: min r %.3f mm (%s, %s) |F|err=%+.4f Fvec=%.4f T1/mB=%.4f T2/mB=%.4f Tc=%.4f"
              % (th, row["r_mm"], mode, row["pair"], row["absF_rel_err"], row["F_vec_rel_err"],
                 row["T1_own_err_over_mB"], row["T2_own_err_over_mB"], row["T1_about_centre_rel_err"]), flush=True)
    res["deterministic_worst_tilt"] = det_tilt

    # ---- 2. realistic geometries swept in r (orientation fixed, separation scaled) -----------------------------
    templates = {"piece_home_closest": (None, 0.0, k_home),
                 "core_rigid_turn_closest": (core["face"], core["angle_deg"], core["k"])}
    tgeo = {name: (pair_geom(face, ang, k), label(mags, I[k], J[k]), f"face {face} at {ang} deg")
            for name, (face, ang, k) in templates.items()}
    d2 = [d for d in det_tilt if d["rel_tilt_deg"] == 2.0][0]
    tgeo["piece_worst_2deg_relative_tilt"] = (tuple(np.array(x) for x in d2["geom"]), d2["pair"],
                                              f"home, {d2['mode']} tilt 2 deg about {np.round(d2['axis'], 3).tolist()}")
    sweep = {}
    for name, ((c1, n1, c2, n2), plabel, where) in tgeo.items():
        rh = (c2 - c1) / np.linalg.norm(c2 - c1)
        rows = []
        for rmm in SWEEP_MM:
            row = compare(c1, n1, MP42, c1 + rh * rmm * 1e-3, n2, MP43)
            rows.append(row)
        sweep[name] = {"pair": plabel, "pose": where,
                       "actual_r_mm": float(np.linalg.norm(c2 - c1) * 1e3), "rows": rows}
        print(name, plabel, where, "actual r %.3f" % sweep[name]["actual_r_mm"], flush=True)
        for row in rows:
            print("  r=%6.3f axes %.1f r-ax1 %.1f r-ax2 %.1f |F|err=%+.4f Fvec=%.4f ang=%.2f  T1/mB=%.4f T2/mB=%.4f "
                  "T1rel=%.3f T2rel=%.4f Tc=%.4f"
                  % (row["r_mm"], row["angle_between_axes_deg"], row["angle_r_to_axis1_deg"],
                     row["angle_r_to_axis2_deg"], row["absF_rel_err"], row["F_vec_rel_err"], row["F_angle_err_deg"],
                     row["T1_own_err_over_mB"], row["T2_own_err_over_mB"], row["T1_own_rel_err"],
                     row["T2_own_rel_err"], row["T1_about_centre_rel_err"]), flush=True)
    res["sweep_realistic_orientation"] = sweep

    # ---- 3. actual poses: home, rigid-turn minimum, and tilt Monte Carlo ---------------------------------------
    rng = np.random.default_rng(SEED)
    cases = []
    c1, n1, c2, n2 = pair_geom(None, 0.0, k_home)
    cases.append({"source": "home", "class": "piece", "pair": label(mags, I[k_home], J[k_home]), "sigma_deg": 0.0,
                  "rel_tilt_deg": 0.0, "geom": [c1.tolist(), n1.tolist(), c2.tolist(), n2.tolist()],
                  **compare(c1, n1, MP42, c2, n2, MP43)})
    c1, n1, c2, n2 = pair_geom(core["face"], core["angle_deg"], core["k"])
    cases.append({"source": "rigid_turn_min_core", "class": "core", "pair": core["pair"], "sigma_deg": 0.0,
                  "rel_tilt_deg": 0.0, "face": core["face"], "angle_deg": core["angle_deg"],
                  "geom": [c1.tolist(), n1.tolist(), c2.tolist(), n2.tolist()], **compare(c1, n1, MP42, c2, n2, MP43)})
    mc_minr = {}
    n_eval = 0
    for sig in SIGMAS_DEG:
        allr, cand = [], []
        for face in FACES:
            for t in range(N_MC_PER_FACE):
                ang = worst_ang[face][1] if t % 2 == 0 else float(rng.uniform(-90, 90))
                p, n, rots = pose(mags, home, face, ang, rng, sig)
                r = dists(p)
                allr.append(float(np.where(is_piece, r, np.inf).min()))
                sel = np.nonzero(is_piece & (r < MC_EVAL_BELOW))[0]
                rig = pose(mags, home, face, ang)[2]
                for k in sel:
                    bi, bj = mags[I[k]]["body"], mags[J[k]]["body"]
                    # relative tilt: rotation of body j relative to body i, beyond the rigid-turn relative rotation
                    rel = (rots[bi].T @ rots[bj]) @ (rig[bi].T @ rig[bj]).T
                    tilt = float(np.degrees(Rotation.from_matrix(rel).magnitude()))
                    cand.append({"source": "tilt_mc", "class": "piece", "pair": label(mags, I[k], J[k]), "sigma_deg": sig,
                                 "rel_tilt_deg": tilt, "face": face, "angle_deg": ang, "r_cand": float(r[k]),
                                 "geom": [p[I[k]].tolist(), n[I[k]].tolist(), p[J[k]].tolist(), n[J[k]].tolist()]})
        # evaluate the MC_N_CLOSEST closest candidates and a random sample of MC_N_RANDOM others (cost bound)
        order = sorted(range(len(cand)), key=lambda q: cand[q]["r_cand"])
        pick = order[:MC_N_CLOSEST]
        rest = order[MC_N_CLOSEST:]
        if rest:
            pick += sorted(rng.choice(rest, size=min(MC_N_RANDOM, len(rest)), replace=False).tolist())
        for q in pick:
            c = cand[q]
            g = [np.array(x) for x in c["geom"]]
            cases.append({**{x: c[x] for x in c if x != "r_cand"}, **compare(g[0], g[1], MP42, g[2], g[3], MP43)})
            n_eval += 1
        mc_minr[str(sig)] = {"min_piece_cross_mm": min(allr) * 1e3, "n_poses": len(allr),
                             "frac_poses_with_piece_cross_below_r2": float(np.mean(np.array(allr) < 0.008)),
                             "n_candidate_pairs_below_eval_cut": len(cand), "n_evaluated": len(pick)}
        print("sigma", sig, mc_minr[str(sig)], "evaluated so far", n_eval, "t=%.0fs" % (time.time() - t0), flush=True)
    res["tilt_mc_summary"] = mc_minr
    cases += [{"source": "det_tilt", "class": "piece", "sigma_deg": None, **d} for d in det_tilt]
    res["cases"] = cases
    # maxima over the evaluated actual-pose cases, by separation band and relative-tilt band
    keys = ["F_vec_rel_err", "absF_rel_err", "F_angle_err_deg", "T1_own_rel_err", "T2_own_rel_err",
            "T1_own_err_over_mB", "T2_own_err_over_mB",
            "T1_own_abs_err_mNm", "T2_own_abs_err_mNm", "T1_about_centre_rel_err", "T2_about_centre_rel_err",
            "T1_about_centre_abs_err_mNm", "T2_about_centre_abs_err_mNm", "absF_err_N", "absF_ref_N"]
    bands = {"r<7.3": (0, 7.3), "7.3<=r<7.9": (7.3, 7.9), "7.9<=r<8.0": (7.9, 8.0), "8.0<=r<8.5": (8.0, 8.5),
             "8.5<=r<9.5": (8.5, 9.5)}
    tilts = {"rel_tilt<=1.5": 1.5, "rel_tilt<=3": 3.0, "any_tilt": 1e9}
    summ = {}
    for bn, (lo, hi) in bands.items():
        for tn, tmax in tilts.items():
            sel = [c for c in cases if lo <= c["r_mm"] < hi and c["rel_tilt_deg"] <= tmax and c["class"] == "piece"]
            if not sel:
                continue
            ent = {"n": len(sel), "r_range_mm": [min(c["r_mm"] for c in sel), max(c["r_mm"] for c in sel)],
                   "rel_tilt_max_deg": max(c["rel_tilt_deg"] for c in sel)}
            for kk in keys:
                vals = [c[kk] for c in sel]
                ent["max_abs_" + kk] = float(max(abs(v) for v in vals))
                if kk == "absF_rel_err":
                    ent["min_absF_rel_err"], ent["max_absF_rel_err"] = float(min(vals)), float(max(vals))
            summ[f"{bn} & {tn}"] = ent
    res["actual_pose_summary"] = summ
    for k_, v_ in summ.items():
        print("summary", k_, {x: (round(y, 4) if isinstance(y, float) else y) for x, y in v_.items()}, flush=True)

    # ---- 4. convergence of the reference model ---------------------------------------------------------------
    conv = []
    c1, n1, c2, n2 = tgeo["piece_home_closest"][0]
    rh = (c2 - c1) / np.linalg.norm(c2 - c1)
    tilt_min = min((c for c in cases if c["source"] == "tilt_mc"), key=lambda c: c["r_mm"], default=None)
    geoms = {"piece_home_orientation_at_7.3mm": (c1, n1, c1 + rh * 7.3e-3, n2),
             "core_rigid_turn_closest": tgeo["core_rigid_turn_closest"][0]}
    if tilt_min is not None:
        geoms["closest_tilt_mc_case"] = tuple(np.array(x) for x in tilt_min["geom"])
    for name, g in geoms.items():
        ca, na, cb, nb = g
        R1, R2 = frame(na), frame(nb)
        rows = []
        for q in QUAD_LADDER:
            rr = ref_pair(ca, R1, MP42, cb, R2, MP43, q)
            rows.append({"quad": q, "U_J": rr["U"], "F2_N": rr["F2"].tolist(), "T1_Nm": rr["T1"].tolist(),
                         "T2_Nm": rr["T2"].tolist()})
        top = rows[-1]
        for row in rows:
            row["F_rel_change_vs_finest"] = float(np.linalg.norm(np.array(row["F2_N"]) - top["F2_N"])
                                                  / np.linalg.norm(top["F2_N"]))
            row["T1_rel_change_vs_finest"] = float(np.linalg.norm(np.array(row["T1_Nm"]) - top["T1_Nm"])
                                                   / np.linalg.norm(top["T1_Nm"]))
            row["T2_rel_change_vs_finest"] = float(np.linalg.norm(np.array(row["T2_Nm"]) - top["T2_Nm"])
                                                   / np.linalg.norm(top["T2_Nm"]))
        # pattern-azimuth invariance: rotate both quadrature patterns about their own axes
        Rz = lambda t: np.array([[np.cos(t), -np.sin(t), 0], [np.sin(t), np.cos(t), 0], [0, 0, 1]])  # noqa: E731
        rr = ref_pair(ca, R1 @ Rz(0.37), MP42, cb, R2 @ Rz(1.1), MP43, QUAD)
        conv.append({"geometry": name, "ladder": rows,
                     "azimuth_rotated_F_rel_change": float(np.linalg.norm(rr["F2"] - np.array(rows[2]["F2_N"]))
                                                           / np.linalg.norm(rows[2]["F2_N"]))})
        print("convergence", name, [(r_["quad"], "%.2e" % r_["F_rel_change_vs_finest"],
                                     "%.2e" % r_["T1_rel_change_vs_finest"], "%.2e" % r_["T2_rel_change_vs_finest"])
                                    for r_ in rows], flush=True)
    # far-field limit: reference vs untapered dipole at 30 and 60 mm, both template orientations
    far = []
    for name, ((c1, n1, c2, n2), _, _) in tgeo.items():
        rh = (c2 - c1) / np.linalg.norm(c2 - c1)
        for rmm in (30.0, 60.0):
            cb = c1 + rh * rmm * 1e-3
            rr = ref_pair(c1, frame(n1), MP42, cb, frame(n2), MP43)
            dd = dip_pair(c1, n1, MP42, cb, n2, MP43, taper=False)
            far.append({"orientation": name, "r_mm": rmm,
                        "F_vec_rel_err": float(np.linalg.norm(dd["F2"] - rr["F2"]) / np.linalg.norm(rr["F2"])),
                        "T2_rel_err": float(np.linalg.norm(dd["T2"] - rr["T2"]) / np.linalg.norm(rr["T2"])),
                        "T1_rel_err": float(np.linalg.norm(dd["T1"] - rr["T1"]) / np.linalg.norm(rr["T1"])),
                        "T1_err_over_mB": float(np.linalg.norm(dd["T1"] - rr["T1"]) / (MP42.moment * np.linalg.norm(
                            C / (rmm * 1e-3) ** 3 * (3 * MP43.moment * float(n2 @ rh) * rh - MP43.moment * n2)))),
                        "U_rel_err": float(dd["U"] / rr["U"] - 1)})
    print("far field", json.dumps(far, indent=1), flush=True)
    res["convergence"] = conv
    res["far_field_limit"] = far

    # ---- 5. same-type comparison ------------------------------------------------------------------------------
    # (a) the same realistic geometries with both magnets of one type (what the dipole error would be if the pair
    #     were same-type at that geometry; perpendicular-ish, so the repo's table would not apply either)
    # (b) parallel same-type pairs (the branch the repo corrects) at r = 5..9 mm, coaxial and side by side: the
    #     dipole error that the near-field correction removes with weight w(r) (1 below 5 mm, 0 above 8 mm)
    same = {"realistic_geometry": [], "parallel_pairs": []}
    for tname in ("piece_home_closest", "core_rigid_turn_closest"):
      c1, n1, c2, n2 = tgeo[tname][0]
      rh = (c2 - c1) / np.linalg.norm(c2 - c1)
      for rmm in (7.3, 8.0, 8.176, 9.335):
        for t1, t2, nm in ((MP42, MP42, "4x2-4x2"), (MP43, MP43, "4x3-4x3"), (MP42, MP43, "4x2-4x3 (cross)")):
            row = compare(c1, n1, t1, c1 + rh * rmm * 1e-3, n2, t2)
            same["realistic_geometry"].append({"orientation": tname, "types": nm, "r_mm": rmm, "F_vec_rel_err": row["F_vec_rel_err"],
                                               "absF_rel_err": row["absF_rel_err"],
                                               "T1_own_rel_err": row["T1_own_rel_err"],
                                               "T2_own_rel_err": row["T2_own_rel_err"],
                                               "T1_own_err_over_mB": row["T1_own_err_over_mB"],
                                               "T2_own_err_over_mB": row["T2_own_err_over_mB"],
                                               "T_about_centre_rel_err": row["T1_about_centre_rel_err"]})
    z = np.array([0.0, 0.0, 1.0])
    for mp in (MP42, MP43):
        for nm, dvec in (("coaxial", np.array([0.0, 0.0, 1.0])), ("side_by_side", np.array([1.0, 0.0, 0.0])),
                         ("45deg", np.array([1.0, 0.0, 1.0]) / np.sqrt(2))):
            for rmm in (5.0, 6.0, 7.0, 8.0, 9.0):
                row = compare(np.zeros(3), z, mp, dvec * rmm * 1e-3, z, mp)
                w = float(M._cutoff(np.array([rmm * 1e-3]), mp.r1, mp.r2)[0][0])
                same["parallel_pairs"].append({"type": M.type_label(mp), "offset": nm, "r_mm": rmm,
                                               "near_weight_w": w, "F_vec_rel_err": row["F_vec_rel_err"],
                                               "absF_rel_err": row["absF_rel_err"],
                                               "T2_own_abs_err_mNm": row["T2_own_abs_err_mNm"],
                                               "T2_own_err_over_mB": row["T2_own_err_over_mB"],
                                               "absF_ref_N": row["absF_ref_N"]})
    res["same_type_comparison"] = same
    for x in same["realistic_geometry"]:
        print("same-type realistic", x, flush=True)
    for x in same["parallel_pairs"]:
        print("same-type parallel", x, flush=True)

    # context: a facing corner-edge 4x2 pair at home (coaxial, the strongest same-type pair), reference model
    i42 = [k for k, g in enumerate(mags) if g["mp"] is MP42]
    k0 = min(((a, b) for a in i42 for b in i42 if mags[a]["body"] != mags[b]["body"]),
             key=lambda ab: np.linalg.norm(p0[ab[0]] - p0[ab[1]]))
    rr = ref_pair(p0[k0[0]], frame(n0[k0[0]]), MP42, p0[k0[1]], frame(n0[k0[1]]), MP42)
    res["context"] = {"facing_CE_4x2_pair_home_r_mm": float(np.linalg.norm(p0[k0[1]] - p0[k0[0]]) * 1e3),
                      "facing_CE_4x2_pair_home_absF_ref_N": float(np.linalg.norm(rr["F2"]))}
    print("context", res["context"], flush=True)
    res["runtime_s"] = time.time() - t0
    out = HERE / "results.json"
    out.write_text(json.dumps(res, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))
    print("wrote", out, "runtime %.0f s" % res["runtime_s"], "cases", len(cases))


if __name__ == "__main__":
    main()
