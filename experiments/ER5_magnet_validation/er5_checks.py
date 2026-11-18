"""ER5: force-law validation for core-positioning magnet sizes (PROTOCOL.md). Unscored.
Usage (WSL):  ~/.venvs/rubiknetic/bin/python experiments/ER5_magnet_validation/er5_checks.py [4x3_N35|5x2_N35 ...]
Writes results/er5_<size>.json. Tables are built into experiments/ER5_magnet_validation/tables/ (never D8's folder).
"""
from __future__ import annotations

import json
import multiprocessing as mp_
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
D8DIR = REPO / "experiments" / "D8_alignment"
sys.path.insert(0, str(D8DIR))
import d8_1b_checks as D8  # noqa: E402
import magnet_force as MF  # noqa: E402

from rubiknetic.cube_logic import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_physics.magnets import MagnetParams, near_field_tables, pair_forces  # noqa: E402

TABLES = HERE / "tables"
OUT = HERE / "results"
SIZES = {"4x3_N35": (0.004, 0.003, "N35"), "5x2_N35": (0.005, 0.002, "N35")}
PITCH, GAP_B1, CLEAR_REAL = 0.019, 5e-5, 2e-4
R_REAL = {"edge": 22.04e-3, "corner": 21.95e-3}
FAR_QUAD = (6, 16)
COS45 = np.cos(np.radians(45))


def core_layout(mp: MagnetParams, placement: str):
    """20 core magnets and 20 piece magnets (home positions), each (pos, dir) in the core frame."""
    core, piece = {}, {}
    for h in HOME_POSITIONS:
        c = np.array(h, float)
        nz = int(np.count_nonzero(c))
        if nz < 2:
            continue
        u = c / np.linalg.norm(c)
        kind = "edge" if nz == 2 else "corner"
        if placement == "B1":
            r_piece = np.linalg.norm(c) * (PITCH + GAP_B1) / 2
            r_core = r_piece - GAP_B1
        else:
            r_piece = R_REAL[kind]
            r_core = r_piece - CLEAR_REAL
        piece[tuple(h)] = (u * (r_piece + mp.wall + mp.length / 2), u.copy(), kind)
        core[tuple(h)] = (u * (r_core - mp.wall - mp.length / 2), u.copy(), kind)
    return core, piece


def rz(deg: float) -> np.ndarray:
    t = np.radians(deg)
    return np.array([[np.cos(t), -np.sin(t), 0], [np.sin(t), np.cos(t), 0], [0, 0, 1.0]])


def v1(mp: MagnetParams) -> dict:
    a, L, br = mp.diameter / 2, mp.length, mp.br
    rows = []
    for z in (0.0005, 0.001, 0.002, 0.004):
        bc, bq = MF.onaxis_field_closed(a, L, br, z), MF.onaxis_field_charges(a, L, br, z)
        rows.append({"z_mm": z * 1e3, "closed_T": bc, "charges_T": bq, "rel_err": abs(bq - bc) / bc})
    return {"rows": rows, "worst_rel_err": max(r["rel_err"] for r in rows),
            "pass": bool(max(r["rel_err"] for r in rows) <= 1e-3)}


def v3_turn(mp: MagnetParams, spline, fn_nom: float, placement: str, home: tuple) -> dict:
    core, piece = core_layout(mp, placement)
    cp = np.array([v[0] for v in core.values()]); cn = np.array([v[1] for v in core.values()])
    p0, n0, kind = piece[home]
    rows = []
    for deg in range(0, 91):
        R = rz(deg)
        pm, nm = R @ p0, R @ n0
        p = np.vstack([cp, pm]); n = np.vstack([cn, nm])
        k = len(cp)
        ii = np.arange(k); jj = np.full(k, k)
        F, T, _ = pair_forces(mp, spline, ii, jj, p, n)
        fh, th = F[k], T[k]
        ff, tf = np.zeros(3), np.zeros(3)
        near_tilts, near_perp = [], 0
        for i in range(k):
            d = np.linalg.norm(pm - cp[i])
            near = d < mp.r2
            f, t, _ = D8.fine_pair(mp, cp[i], cn[i], pm, nm, *(D8.REF_QUAD if near else FAR_QUAD))
            ff += f; tf += t
            if near:
                c = float(abs(cn[i] @ nm))
                near_tilts.append(float(np.degrees(np.arccos(min(1.0, c)))))
                near_perp += int(c <= COS45)
        rows.append({"deg": deg, "F_err_rel_Fn": float(np.linalg.norm(fh - ff) / fn_nom),
                     "T_err_Nm": float(np.linalg.norm(th - tf)), "fine_T_Nm": float(np.linalg.norm(tf)),
                     "fine_F_N": float(np.linalg.norm(ff)), "max_near_tilt_deg": max(near_tilts, default=None),
                     "n_near": len(near_tilts), "near_perpendicular": near_perp})
    t_tol = max(0.05 * max(r["fine_T_Nm"] for r in rows), 2e-5)
    for r in rows:
        r["pass"] = bool(r["F_err_rel_Fn"] <= 0.05 and r["T_err_Nm"] <= t_tol)
    passing = [r["deg"] for r in rows if r["pass"]]
    first_fail = next((r["deg"] for r in rows if not r["pass"]), None)
    return {"placement": placement, "piece": home, "kind": kind, "T_tol_Nm": t_tol, "rows": rows,
            "worst_F_err_rel_Fn": max(r["F_err_rel_Fn"] for r in rows), "worst_T_err_Nm": max(r["T_err_Nm"] for r in rows),
            "first_failing_deg": first_fail, "n_passing": len(passing),
            "near_perpendicular_total": sum(r["near_perpendicular"] for r in rows),
            "max_near_tilt_deg": max((r["max_near_tilt_deg"] or 0) for r in rows),
            "pass": bool(len(passing) == len(rows))}


def v4(mp: MagnetParams, spline, n_states: int = 20, seed: int = 0) -> dict:
    from scipy.spatial.transform import Rotation
    rng = np.random.default_rng(seed)
    core, piece = core_layout(mp, "B1")
    rows = []
    for _ in range(n_states):
        ps, ns, bodies = [], [], []
        for h, (pc, nc, _) in core.items():
            ps.append(pc); ns.append(nc); bodies.append(-1)
        turn = rz(rng.uniform(0, 90))
        for b, (h, (pp, npc, _)) in enumerate(piece.items()):
            ax = rng.normal(size=3); ax /= np.linalg.norm(ax)
            R = Rotation.from_rotvec(ax * np.radians(rng.uniform(0, 5))).as_matrix()
            if h[2] == 1:
                R = turn @ R
            ps.append(R @ pp); ns.append(R @ npc); bodies.append(b)
        p, n, bodies = np.array(ps), np.array(ns), np.array(bodies)
        ii, jj = np.triu_indices(len(p), 1)
        keep = ~((bodies[ii] == -1) & (bodies[jj] == -1))
        F, T, _ = pair_forces(mp, spline, ii[keep], jj[keep], p, n)
        L = T + np.cross(p, F)
        rows.append({"sumF_rel": float(np.linalg.norm(F.sum(0)) / np.abs(F).max()),
                     "sumL_rel": float(np.linalg.norm(L.sum(0)) / np.abs(L).max())})
    worst = max(max(r["sumF_rel"], r["sumL_rel"]) for r in rows)
    return {"rows": rows, "worst_rel": worst, "pass": bool(worst <= 1e-9)}


def run_size(tag: str) -> dict:
    t0 = time.perf_counter()
    dia, length, grade = SIZES[tag]
    mp = MagnetParams(diameter=dia, length=length, grade=grade)
    D8.MP, D8.CACHE = mp, TABLES                      # D8's checks read these module globals
    TABLES.mkdir(parents=True, exist_ok=True)
    spline = near_field_tables(mp, TABLES)
    import hashlib
    res = {"size": tag, "moment_Am2": mp.moment, "moment_ratio_to_4x2_N35": mp.moment / MagnetParams().moment,
           "table_s": round(time.perf_counter() - t0, 1),
           "tables_sha256": {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                             for f in sorted(TABLES.glob(f"*_{dia * 1e3:g}x{length * 1e3:g}_*.npz"))}}
    res["V1"] = v1(mp)
    v3 = D8.v3(spline)
    res["V3_D8"] = {k: v for k, v in v3.items() if k not in ("pair", "tilt")}
    res["V3a_pass"] = bool(v3["pair_worst_err"] <= 0.05 and v3["pair_worst_T_err_Nm"] <= v3["pair_T_tol_Nm"])
    res["V3b_validated_tilt_deg"] = v3["validated_tilt_deg"]
    res["V3b_pass"] = bool(v3["validated_tilt_deg"] >= 5.0)
    fn_nom = v3["Fn_nominal_N"]
    res["V3_turn"] = [v3_turn(mp, spline, fn_nom, pl, h) for pl in ("B1", "real") for h in ((-1, 0, 1), (-1, -1, 1))]
    res["V3_turn_pass"] = all(t["pass"] for t in res["V3_turn"])
    res["V4"] = v4(mp, spline)
    res["validated_for_core_layout"] = bool(res["V1"]["pass"] and res["V3a_pass"] and res["V3b_pass"]
                                            and res["V3_turn_pass"] and res["V4"]["pass"])
    res["wall_s"] = round(time.perf_counter() - t0, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"er5_{tag}.json").write_text(json.dumps(res, indent=1, default=float))
    return res


def summary(r: dict) -> str:
    s = [f"== {r['size']} (moment x{r['moment_ratio_to_4x2_N35']:.3f} of 4x2 N35; wall {r['wall_s']} s)",
         f"  V1 worst rel err {r['V1']['worst_rel_err']:.1e}  pass {r['V1']['pass']}",
         f"  V3a pair worst F {r['V3_D8']['pair_worst_err']:.4f}, T {r['V3_D8']['pair_worst_T_err_Nm']:.2e}"
         f"/{r['V3_D8']['pair_T_tol_Nm']:.2e}  pass {r['V3a_pass']}",
         f"  V3b validated tilt {r['V3b_validated_tilt_deg']} deg  pass {r['V3b_pass']}  "
         f"(by angle: {{{', '.join(k + ': ' + str(v['pass']) for k, v in r['V3_D8']['tilt_by_angle'].items())}}})",
         f"  V3c whole cube (L0 layout, reported only): {[(c['R_turn_deg'], round(c['max_force_err_rel_Fn'], 4)) for c in r['V3_D8']['cube']]}"]
    for t in r["V3_turn"]:
        s.append(f"  V3-turn {t['placement']:4s} {t['kind']:6s}: worst F {t['worst_F_err_rel_Fn']:.4f}, T {t['worst_T_err_Nm']:.2e}"
                 f"/{t['T_tol_Nm']:.2e}; passes {t['n_passing']}/91 deg, first fail {t['first_failing_deg']}; "
                 f"max near tilt {t['max_near_tilt_deg']:.1f} deg; near-perpendicular {t['near_perpendicular_total']}  pass {t['pass']}")
    s.append(f"  V4 worst {r['V4']['worst_rel']:.1e}  pass {r['V4']['pass']}")
    s.append(f"  VALIDATED FOR CORE LAYOUT: {r['validated_for_core_layout']}")
    return "\n".join(s)


if __name__ == "__main__":
    tags = [a for a in sys.argv[1:] if a in SIZES] or list(SIZES)
    with mp_.get_context("fork").Pool(len(tags)) as pool:
        for r in pool.imap_unordered(run_size, tags):
            print(summary(r), flush=True)
