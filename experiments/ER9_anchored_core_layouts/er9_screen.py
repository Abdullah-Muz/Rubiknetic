"""ER9 part A: static screen of core layouts with off-axis magnet pairs (PROTOCOL.md). No dynamics.

Reuses ER3's measure() (single-piece stiffnesses, layer stiffness, U-turn profile), ER6's table loader and magnet
intersection sweep, and adds the cube's full 66 x 66 magnet stiffness matrix, the collective-twist stiffness, the
piece-to-piece magnet distance over every face turn, and a near-pair survey.
Usage (WSL, repo root):  ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9_screen.py [--jobs N]
Writes results/screen.json and prints a table.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import multiprocessing as mp_
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def _load(name, rel):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


E6 = _load("er6_screen", "experiments/ER6_real_placement_screen/er6_screen.py")
E3, E, E5 = E6.E3, E6.E, E6.E5
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES  # noqa: E402
from rubiknetic.cube_physics import magnets as MG  # noqa: E402
from rubiknetic.cube_physics.magnets import GRADES_BR  # noqa: E402

MP43 = E6.MP43
GAP = E6.GAP
CLEAR = 2e-4
DLT = E3.DLT
GRADES = ("N35", "N42", "N52")
EDGE_OPTS = [("axis",)] + [("split", g, t) for t in ("centre", "corner") for g in (14, 16, 18, 20)]
CORNER_OPTS = [("axis",)] + [("tri", g, t) for t in ("edge", "centre") for g in (10, 12, 14, 16)]
JOINT_FRICTION = 0.0005          # N m per axis (M1Params.joint_frictionloss)
SPIN_MIN, EIG_MIN, PEAK_MAX, LAYER_MIN, PP_MIN_MM, TILT_MAX = 100.0, 50.0, 0.5, 1.0, 8.0, 20.0


# ---- layouts --------------------------------------------------------------------------------------------------------
def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _toward(u: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Unit tangent at u pointing toward the unit vector target."""
    return _unit(target - (target @ u) * u)


def pair_directions(home: np.ndarray, opt: tuple) -> list[np.ndarray]:
    """Unit directions of a piece's magnet pairs. opt: ('axis',) | ('split', gamma_deg, 'centre' | 'corner') for an
    edge | ('tri', gamma_deg, 'edge' | 'centre') for a corner."""
    h = np.asarray(home, float)
    u = _unit(h)
    if opt[0] == "axis":
        return [u]
    g = np.radians(opt[1])
    nz = np.nonzero(h)[0]
    if opt[0] == "split":
        assert len(nz) == 2
        if opt[2] == "centre":                    # toward the two neighbouring face centres
            targets = [np.eye(3)[k] * h[k] for k in nz]
        else:                                     # toward the two neighbouring corners (along the edge's long axis)
            z = [k for k in range(3) if h[k] == 0][0]
            targets = [_unit(h + s * np.eye(3)[z]) for s in (1.0, -1.0)]
    elif opt[0] == "tri":
        assert len(nz) == 3
        if opt[2] == "edge":                      # toward the three neighbouring edges
            targets = [_unit(h * (1 - np.eye(3)[k])) for k in range(3)]
        else:                                     # toward the three neighbouring face centres
            targets = [np.eye(3)[k] * h[k] for k in range(3)]
    else:
        raise ValueError(opt)
    return [_unit(np.cos(g) * u + np.sin(g) * _toward(u, t)) for t in targets]


def anchored_layout(mp, clear: float, edge_opt: tuple, corner_opt: tuple, sigma: float = 1.0) -> list[dict]:
    """Core layout with one or more radial pairs per edge and corner. Each pair: piece magnet at v (R + wall + L/2),
    core magnet at v (R - clear - wall - L/2), both moments along +v (v = the pair's radial direction)."""
    out = []
    for n, c in zip(E.NAMES, E.HOMES):
        kind = E.KIND[n]
        if kind == "centre":
            continue
        R = E5.R_REAL[kind]
        for v in pair_directions(c, edge_opt if kind == "edge" else corner_opt):
            out.append({"body": n, "pos": v * (R + mp.wall + mp.length / 2), "dir": v.copy(), "sigma": sigma})
            out.append({"body": "core", "pos": v * (R - clear - mp.wall - mp.length / 2), "dir": v.copy(),
                        "sigma": sigma})
    return out


# ---- full stiffness matrix -----------------------------------------------------------------------------------------
def dofs() -> list[tuple[str, np.ndarray]]:
    out = []
    for n, c in zip(E.NAMES, E.HOMES):
        if E.KIND[n] == "centre":
            out.append((n, c.astype(float)))
        else:
            out += [(n, np.eye(3)[a]) for a in range(3)]
    return out


def full_matrix(rig, mags, spline) -> dict:
    D = dofs()
    T = lambda: E3.torques(rig, mags, MP43, spline)  # noqa: E731
    K = np.zeros((len(D), len(D)))
    for j, (nm, ax) in enumerate(D):
        rig.pose({nm: DLT * ax}); tp = T()
        rig.pose({nm: -DLT * ax}); tm = T()
        for i, (ni, ai) in enumerate(D):
            K[i, j] = -float((tp.get(ni, np.zeros(3)) - tm.get(ni, np.zeros(3))) @ ai) / (2 * DLT)
    Ks = (K + K.T) / 2 * 1e3                                        # mN m/rad
    w, V = np.linalg.eigh(Ks)
    centre = np.array([E.KIND[n] == "centre" for n, _ in D])
    twist = np.array([float(c.astype(float) @ ax) for (n, ax), c in
                      zip(D, [E.HOMES[E.NAMES.index(n)] for n, _ in D])])   # every piece about its own radial axis
    zero = np.abs(w) < 1.0
    zero_centre_weight = [float(np.sum(V[centre, k] ** 2)) for k in np.nonzero(zero)[0]]
    return {"n_dof": len(D), "asym_max": float(np.abs(K - K.T).max() * 1e3), "eig_min": float(w.min()),
            "n_zero": int(zero.sum()), "zero_modes_centre_weight_min": min(zero_centre_weight, default=None),
            "eig_min_nonzero": float(w[~zero].min()) if (~zero).any() else None,
            "collective_twist_mNm_per_rad": float(twist @ Ks @ twist),
            "collective_twist_norm2": float(twist @ twist)}


# ---- geometry and survey -------------------------------------------------------------------------------------------
def geometry_and_survey(rig, mags, mp, spline, step_dist: int = 1, step_survey: int = 2) -> dict:
    core_id = E3.mujoco_body(rig, "core")
    ii, jj = np.triu_indices(len(mags), 1)
    pp_min, pp_at = np.inf, None
    sv = {"near_perpendicular": 0, "near_piece_piece": 0, "max_near_tilt_deg": 0.0, "clamped_z": 0,
          "near_pairs_max": 0}
    for f in FACES:
        nrm = np.array(FACE_NORMAL[f], float)
        mem = [x for x, h in zip(E.NAMES, E.HOMES) if h @ nrm == 1]
        for deg in range(-90, 91, step_dist):
            rig.pose({x: np.radians(deg) * nrm for x in mem})
            p, n, b = E6.world(rig, mags, core_id)
            diff = b[ii] != b[jj]
            r = np.linalg.norm(p[ii] - p[jj], axis=1)
            pp = diff & (b[ii] != core_id) & (b[jj] != core_id)
            if pp.any() and r[pp].min() < pp_min:
                k = np.nonzero(pp)[0][np.argmin(r[pp])]
                pp_min, pp_at = float(r[k]), {"face": f, "deg": deg, "pair": [mags[ii[k]]["body"], mags[jj[k]]["body"]]}
            if deg % step_survey == 0:
                near = diff & (r < mp.r2)
                sv["near_pairs_max"] = max(sv["near_pairs_max"], int(near.sum()))
                sv["near_piece_piece"] += int((near & pp).sum())
                st = {"near_perpendicular": 0, "clamped_z": 0, "max_near_tilt_deg": 0.0, "max_force_N": 0.0}
                k = np.nonzero(near)[0]
                if len(k):
                    MG.pair_forces(mp, spline, ii[k], jj[k], p, n, st, MG.scatter_matrices(len(mags), ii[k], jj[k]))
                sv["near_perpendicular"] += st["near_perpendicular"]
                sv["clamped_z"] += st["clamped_z"]
                sv["max_near_tilt_deg"] = max(sv["max_near_tilt_deg"], st["max_near_tilt_deg"])
    rig.pose({})
    p, n, b = E6.world(rig, mags, core_id)
    cc = (b[ii] == core_id) & (b[jj] == core_id)
    core_min = float(np.linalg.norm(p[ii] - p[jj], axis=1)[cc].min())
    return {"piece_piece_min_mm": pp_min * 1e3, "piece_piece_min_at": pp_at, "core_core_min_mm": core_min * 1e3,
            "survey": sv}


# ---- one candidate -------------------------------------------------------------------------------------------------
_CTX: dict = {}


def _ctx():
    if not _CTX:
        _CTX["rig"] = E.Rig(GAP)
        _CTX["spline"], _CTX["s2"] = E6.load_tables()
    return _CTX["rig"], _CTX["spline"]


def name_of(grade, eo, co) -> str:
    e = "E1" if eo[0] == "axis" else f"E2@{eo[1]}>{eo[2]}"
    c = "C1" if co[0] == "axis" else f"C3@{co[1]}>{co[2]}"
    return f"{grade} {e} {c}"


def evaluate(job: tuple) -> dict:
    grade, eo, co = job
    rig, spline = _ctx()
    sig = GRADES_BR[grade] / GRADES_BR["N35"]
    mags = anchored_layout(MP43, CLEAR, eo, co, sig)
    r = E3.measure(rig, mags, MP43, spline)
    m = r["mode_min"]
    row = {"variant": name_of(grade, eo, co), "grade": grade, "edge_opt": list(eo), "corner_opt": list(co),
           "n_magnets": len(mags), "mode_min": m, "min_eig": r["min_eig"], "min_layer": r["min_layer"],
           "turn_peak_Nm": r["turn_peak_Nm"], "er3_passes": r["passes"],
           "max_aligned_torque_mNm": r["max_aligned_torque_mNm"]}
    row["full"] = full_matrix(rig, mags, spline)
    row["predicted_layer_error_deg"] = {
        "edge": float(np.degrees(JOINT_FRICTION / (m["edge_spin"] * 1e-3))) if m["edge_spin"] > 1 else None,
        "corner": float(np.degrees(JOINT_FRICTION / (m["corner_twist"] * 1e-3))) if m["corner_twist"] > 1 else None}
    c1 = bool(r["min_eig"] >= -1.0 and r["min_layer"] >= LAYER_MIN and r["turn_peak_Nm"] <= PEAK_MAX)
    c2 = bool(m["edge_spin"] >= SPIN_MIN and m["corner_twist"] >= SPIN_MIN)
    f = row["full"]
    c3 = bool(f["n_zero"] == 6 and f["eig_min_nonzero"] is not None and f["eig_min_nonzero"] >= EIG_MIN
              and (f["zero_modes_centre_weight_min"] or 0) > 0.999)
    row["criteria"] = {"1_er3": c1, "2_spin_twist": c2, "3_full_matrix": c3}
    if c1 and c2 and c3 or (eo[0] == "axis" and co[0] == "axis"):      # geometry only where it can matter (and C52)
        g = geometry_and_survey(rig, mags, MP43, spline)
        sw = E6.sweep(rig, mags, MP43)
        row["geometry"] = {**g, "min_clearance_mm": sw["min_clearance_mm"], "clearance_worst": sw["worst"]}
        s = g["survey"]
        row["criteria"]["4_geometry"] = bool(sw["min_clearance_mm"] > 0 and g["piece_piece_min_mm"] >= PP_MIN_MM
                                             and g["core_core_min_mm"] > MP43.diameter * 1e3)
        row["criteria"]["5_survey"] = bool(s["near_perpendicular"] == 0 and s["max_near_tilt_deg"] <= TILT_MAX
                                           and s["near_piece_piece"] == 0)
    row["passes"] = bool(len(row["criteria"]) == 5 and all(row["criteria"].values()))
    return row


def self_checks(rows: list[dict]) -> dict:
    ref = [r for r in json.loads((REPO / "experiments/ER6_real_placement_screen/results/screen.json").read_text())["rows"]
           if r["variant"] == "N52 c=0.2mm"][0]
    c52 = [r for r in rows if r["variant"] == "N52 E1 C1"][0]
    a = np.array([c52["min_eig"], c52["min_layer"], c52["turn_peak_Nm"], *c52["mode_min"].values()])
    b = np.array([ref["min_eig"], ref["min_layer"], ref["turn_peak_Nm"], *ref["mode_min"].values()])
    s1 = float(np.max(np.abs(a - b)) / np.max(np.abs(b)))
    f = c52["full"]
    return {"S1": {"rel_diff_vs_er6": s1, "pass": s1 <= 1e-9},
            "S2": {"n_zero": f["n_zero"], "collective_twist_mNm_per_rad": f["collective_twist_mNm_per_rad"],
                   "pass": bool(f["n_zero"] == 26 and abs(f["collective_twist_mNm_per_rad"]) < 1.0)},
            "S3": _CTX.get("s2")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=12)
    a = ap.parse_args()
    _ctx()
    jobs = [(g, eo, co) for g in GRADES for eo in EDGE_OPTS for co in CORNER_OPTS]
    with mp_.get_context("fork").Pool(a.jobs) as pool:
        rows = []
        for k, r in enumerate(pool.imap(evaluate, jobs), 1):
            rows.append(r)
            print(f"[{k}/{len(jobs)}] {r['variant']}: {r['criteria']}", flush=True)
    checks = self_checks(rows)
    out = HERE / "results"; out.mkdir(exist_ok=True)
    passing = sorted([r for r in rows if r["passes"]],
                     key=lambda r: (round(r["turn_peak_Nm"], 4), r["n_magnets"], GRADES.index(r["grade"])))
    (out / "screen.json").write_text(json.dumps(
        {"env": E.D10.environment(), "self_checks": checks, "thresholds": {
            "spin_twist_min": SPIN_MIN, "eig_min": EIG_MIN, "peak_max": PEAK_MAX, "layer_min": LAYER_MIN,
            "piece_piece_min_mm": PP_MIN_MM, "tilt_max_deg": TILT_MAX},
         "selected": passing[0]["variant"] if passing else None,
         "runner_up": passing[1]["variant"] if len(passing) > 1 else None, "rows": rows}, indent=1, default=float))
    print("\nself-checks:", json.dumps(checks, default=float))

    def line(r):
        m, f, g = r["mode_min"], r["full"], r.get("geometry")
        geo = (f"{g['piece_piece_min_mm']:.2f} / {g['min_clearance_mm']:.2f} / {g['survey']['max_near_tilt_deg']:.1f}"
               if g else "–")
        pe = r["predicted_layer_error_deg"]
        return (f"| {r['variant']} | {r['n_magnets']} | {m['edge_spin']:+.0f} / {m['edge_slide']:+.0f} / "
                f"{m['edge_cross']:+.0f} | {m['corner_twist']:+.0f} / {m['corner_tangential']:+.0f} | "
                f"{r['min_layer']:.2f} | {r['turn_peak_Nm']:.3f} | {f['n_zero']} / {f['eig_min_nonzero']:.0f} / "
                f"{f['collective_twist_mNm_per_rad']:.0f} | "
                f"{'–' if pe['edge'] is None else format(pe['edge'], '.2f')} / "
                f"{'–' if pe['corner'] is None else format(pe['corner'], '.2f')} | {geo} | "
                f"{''.join('Y' if v else 'n' for v in r['criteria'].values())} | {'PASS' if r['passes'] else 'fail'} |")

    head = ("| layout | magnets | edge spin / slide / cross | corner twist / tangential | layer N m/rad | U-turn peak "
            "N m | zero modes / min other eig / collective twist | predicted layer error edge / corner (deg) | "
            "piece-piece min mm / min clearance mm / max tilt | criteria 1-5 | screen |\n" + "|---" * 11 + "|")
    print(f"\n{len(passing)} of {len(rows)} layouts pass.\n\n## Passing layouts, by U-turn peak\n" + head)
    for r in passing[:25]:
        print(line(r))
    print("\n## Reference and near misses (fail only criterion 1 or only criterion 2)\n" + head)
    print(line([r for r in rows if r["variant"] == "N52 E1 C1"][0]))
    miss = [r for r in rows if not r["passes"] and sum(not v for v in list(r["criteria"].values())[:3]) == 1
            and r["criteria"]["3_full_matrix"]]
    for r in sorted(miss, key=lambda r: r["turn_peak_Nm"])[:20]:
        print(line(r))


if __name__ == "__main__":
    main()
