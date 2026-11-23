"""ER9 Part G, P2 (stiffness) and the static self-checks GS5 and GS6 (polarity) (PROTOCOL.md G.5, G.6, G.12). Static;
no dynamics. P3 is a stub that lists its inputs (G.6 P3: numbers from committed side checks and TODO reruns that need
the licensed CAD outside the repository); nothing of P3 is computed here.

Composite energy path. Every torque below comes from the arm's MagnetSystem (er9g_layouts.build_system: same-type
pairs with their own table, cross-type pairs dipole-only; magnets.py, unchanged), evaluated at kinematic poses of ER2's
Rig (the B1 model, gap 0.05 mm): per-body torque about the cube centre = sum over the body's magnets of T + p x F, the
sum ER3's torques() forms (er3_screen.py l.70-87). The neighbour list is reset before every evaluation (as ER1 probe 5
does), so each pose is evaluated from the full pair list.
  * ER3's single-piece stiffnesses, layer stiffness and U-turn profile: ER3's own measure() (er3_screen.py l.94-153),
    called unchanged with its module-level torques() replaced, for the duration of the call, by the composite torque
    function above (restored afterwards). measure() passes mp and spline only to torques(), so nothing else changes.
  * The 66 x 66 matrix: full_matrix66 below, a copy of er9_screen.full_matrix (l.107-128) that takes the torque
    function instead of the hard-coded 4 x 3 parameters and spline (review G12), and also returns every eigenvalue.
  * ER1's probe 5 (er1_probe_magnet_stiffness.py): edge n0p, corner nnp, corner+edge pair nnp+n0p and the whole U
    layer rotated about the face axis z by -0.1..+0.1 deg; restoring stiffness = -slope x 180 / pi (mN m/rad).
GS5 checks this path against the recorded rows (48-only: ER3's L0 row, ER1's probe-5 values; 40-only: Part A's S1
against ER6's N52 c = 0.2 mm row, and S2).

Usage (WSL, repo root):
  ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9g_static.py p2 ARM [--grade G] [--out DIR]
  ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9g_static.py gs5 [--out DIR]
  ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9g_static.py p3
p2 writes DIR/P2_<ARM>_<GRADE>.json (default DIR = results/hybrid_g/static; exclusive create). L0's row is named
with its own magnets' grade (N35); the core grade does not apply to it.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

from rubiknetic.cube_physics import magnets as M

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "results" / "hybrid_g" / "static"


def _load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


LY = _load("er9g_layouts", HERE / "er9g_layouts.py")
ST = _load("er9g_stats", HERE / "er9g_stats.py")
SC = _load("er9g_scan", HERE / "er9g_scan.py")
S9 = _load("er9_screen", HERE / "er9_screen.py")       # loads ER6, ER5, ER3 and ER2 (Rig) as Part A does
E3, E = S9.E3, S9.E

P2_ROWS = {("PG8", "N52"), ("PG8", "N35"), ("PG8", "N42"), ("PG20", "N52"), ("PG20", "N35"), ("PG20", "N42"),
           ("PG20r", "N52"), ("L0", "N35"), ("C52", "N52")}
EIG_SMALL = 1.0                     # mN m/rad: |lambda| below this counts as a zero mode (er9_screen.full_matrix)
MAX_ZERO_MODES = 6                  # P2 stop: more than 6 eigenvalues with |lambda| < 1 mN m/rad
TWIST_MIN = 1.0                     # P2 stop: collective twist <= 1 mN m/rad
P5_DEGS = (-0.1, -0.05, -0.02, 0.0, 0.02, 0.05, 0.1)
P5_CASES = (("edge n0p", ["cubie_n0p"]), ("corner nnp", ["cubie_nnp"]), ("pair nnp + n0p", ["cubie_nnp", "cubie_n0p"]),
            ("whole U layer", [n for n, h in zip(E.NAMES, E.HOMES) if h[2] == 1]))
ER3_L0_VARIANT = "F1 ce=+1 ec=+0"
ER6_C52_VARIANT = "N52 c=0.2mm"
ER1_REPORTED_N_m = {"edge n0p": -0.93, "corner nnp": -0.42, "pair nnp + n0p": -0.42}   # ER1 REVIEW F4, 2 decimals


# ---- the composite torque function -----------------------------------------------------------------------------------
def composite_torques(ms):
    """torques(rig, mags=None, mp=None, spline=None) -> {body name: torque about the cube centre (N m)} from ms."""
    names = [g["body"] for g in ms.mags]

    def torques(rig, mags=None, mp=None, spline=None):
        ms.reset_neighbour_list()
        p, n = ms.world(rig.d.xpos, rig.d.xmat)
        F, T, _ = ms.forces(p, n)
        tc = T + np.cross(p, F)
        out: dict = {}
        for k, b in enumerate(names):
            out[b] = out.get(b, np.zeros(3)) + tc[k]
        return out

    return torques


@contextlib.contextmanager
def er3_through(torque_fn):
    """ER3's measure() with its torques() replaced by torque_fn for the duration of the block."""
    orig = E3.torques
    E3.torques = torque_fn
    try:
        yield
    finally:
        E3.torques = orig


def full_matrix66(rig, torque_fn) -> dict:
    """er9_screen.full_matrix with a torque function (mixed types) and the full eigenvalue list."""
    D = S9.dofs()
    dlt = S9.DLT
    K = np.zeros((len(D), len(D)))
    for j, (nm, ax) in enumerate(D):
        rig.pose({nm: dlt * ax}); tp = torque_fn(rig)
        rig.pose({nm: -dlt * ax}); tm = torque_fn(rig)
        for i, (ni, ai) in enumerate(D):
            K[i, j] = -float((tp.get(ni, np.zeros(3)) - tm.get(ni, np.zeros(3))) @ ai) / (2 * dlt)
    Ks = (K + K.T) / 2 * 1e3                                        # mN m/rad
    w, V = np.linalg.eigh(Ks)
    centre = np.array([E.KIND[n] == "centre" for n, _ in D])
    twist = np.array([float(c.astype(float) @ ax) for (n, ax), c in
                      zip(D, [E.HOMES[E.NAMES.index(n)] for n, _ in D])])
    zero = np.abs(w) < EIG_SMALL
    zero_centre_weight = [float(np.sum(V[centre, k] ** 2)) for k in np.nonzero(zero)[0]]
    return {"n_dof": len(D), "asym_max": float(np.abs(K - K.T).max() * 1e3), "eig_min": float(w.min()),
            "n_zero": int(zero.sum()), "zero_modes_centre_weight_min": min(zero_centre_weight, default=None),
            "eig_min_nonzero": float(w[~zero].min()) if (~zero).any() else None,
            "collective_twist_mNm_per_rad": float(twist @ Ks @ twist),
            "collective_twist_norm2": float(twist @ twist),
            "n_negative": int(np.sum(w <= -EIG_SMALL)), "eigenvalues_mNm_per_rad": w.tolist()}


def probe5(rig, torque_fn) -> dict:
    """ER1 probe 5 through torque_fn: group torque about z at small rotations of the group about z."""
    z = np.array([0.0, 0.0, 1.0])
    out = {}
    for label, grp in P5_CASES:
        tq = []
        for deg in P5_DEGS:
            rig.pose({x: math.radians(deg) * z for x in grp})
            T = torque_fn(rig)
            tq.append(float(sum(T[x][2] for x in grp if x in T)) * 1e3)
        k = np.polyfit(P5_DEGS, tq, 1)[0]
        out[label] = {"group": grp, "group_torque_z_mNm": tq, "restoring_stiffness_mNm_per_rad": float(-k * 180 / np.pi)}
    rig.pose({})
    return out


_RIG: dict = {}


def rig():
    if "rig" not in _RIG:
        _RIG["rig"] = E.Rig(LY.GAP)
    return _RIG["rig"]


def measure(arm: str, grade: str = "N52", tables: dict | None = None, the_rig=None) -> dict:
    """ER3's measure(), the 66 x 66 matrix and ER1's probe 5 for one arm through the composite energy."""
    LY.check_arm(arm, grade)
    r = the_rig or rig()
    ms = LY.build_system(r.m, arm, grade, tables, pitch=r.p.pitch, gap=r.p.gap)
    T = composite_torques(ms)
    with er3_through(T):
        er3 = E3.measure(r, ms.mags, None, None)
    full = full_matrix66(r, T)
    p5 = probe5(r, T)
    r.pose({})
    return {"arm": arm, "grade": grade, "n_magnets": ms.n, "composite": bool(ms.composite),
            "types": ms.type_labels, "er3": er3, "full": full, "probe5": p5}


def er6_metric(row: dict, ref: dict) -> float:
    """er6_screen.s1 / er9_screen.self_checks S1: max |a - b| / max |b| over min_eig, min_layer, turn_peak_Nm and
    mode_min."""
    a = np.array([row["min_eig"], row["min_layer"], row["turn_peak_Nm"], *row["mode_min"].values()])
    b = np.array([ref["min_eig"], ref["min_layer"], ref["turn_peak_Nm"], *ref["mode_min"].values()])
    return float(np.max(np.abs(a - b)) / np.max(np.abs(b)))


def extended_metric(row: dict, ref: dict) -> float:
    """The same metric over every piece eigenvalue, centre, layer and the U-turn profile (both rows from measure())."""
    def vec(r):
        names = sorted(r["pieces"])
        return np.array([x for k in names for x in r["pieces"][k]["eig"]] + [r["centres"][k] for k in sorted(r["centres"])]
                        + [r["layers"][k] for k in sorted(r["layers"])] + list(r.get("turn_profile_Nm", [])))
    a, b = vec(row), vec(ref)
    return float(np.max(np.abs(a - b)) / np.max(np.abs(b)))


def p2_stops(full: dict) -> list[dict]:
    return [{"rule": "more than 6 eigenvalues with |lambda| < 1 mN m/rad", "value": full["n_zero"],
             "limit": MAX_ZERO_MODES, "stop": bool(full["n_zero"] > MAX_ZERO_MODES)},
            {"rule": "collective twist <= 1 mN m/rad", "value": full["collective_twist_mNm_per_rad"],
             "limit": TWIST_MIN, "margin": full["collective_twist_mNm_per_rad"] - TWIST_MIN,
             "stop": bool(full["collective_twist_mNm_per_rad"] <= TWIST_MIN)}]


def p2(arm: str, grade: str) -> dict:
    """One P2 row. Stops as G.6 P2 (a trigger is to be investigated as a possible bug first); negative eigenvalues and
    negative single-piece / cluster stiffnesses are reported, not stops (U6)."""
    if (arm, grade) not in P2_ROWS:
        raise ValueError(f"({arm}, {grade}) is not a P2 row of G.6: {sorted(P2_ROWS)}")
    t0 = time.perf_counter()
    res = measure(arm, grade)
    res["stops"] = p2_stops(res["full"])
    res["stopped"] = any(s["stop"] for s in res["stops"])
    res["reported_not_stops"] = {
        "n_negative_eigenvalues": res["full"]["n_negative"],
        "negative_threshold_mNm_per_rad": -EIG_SMALL,      # ER3 criterion 1's level; smaller values are noise
        "negative_single_piece_modes": {k: v for k, v in res["er3"]["mode_min"].items()
                                        if (min(v) if isinstance(v, list) else v) < -EIG_SMALL},
        "negative_probe5": {k: v["restoring_stiffness_mNm_per_rad"] for k, v in res["probe5"].items()
                            if v["restoring_stiffness_mNm_per_rad"] < -EIG_SMALL},
        "er3_criterion_1_waived": "U6: ER3 criterion 1 is report-only for this family"}
    res["tables"] = LY.table_files(arm, grade)
    res["protocol"] = "ER9 PROTOCOL.md Part G, G.6 P2"
    res["wall_s"] = time.perf_counter() - t0
    return res


# ---- GS5 -------------------------------------------------------------------------------------------------------------
def er3_order_check(er3_row: dict) -> dict:
    """Diagnostic for GS5 48-only: the same composite path on ER3's own L0 list (er3_screen.layout({'ce': 1}), ER3's
    magnet order) instead of magnets.layout's order. The positions and directions are the same set (ER2's check_l0);
    only the order, and so which magnet of each pair is 'i', differs. pair_forces expands the near-field term about
    magnet i's axis (ax = n[i], magnets.py l.428), so at a nonzero relative tilt the pair energy depends on the order.
    This separates a path error from that order dependence."""
    r = rig()
    tabs = LY.load_tables("L0")
    mags = [{"body": g["body"], "pos": g["pos"], "dir": g["dir"], "kind": "er3"}
            for g in E3.layout({"ce": 1}, r.p.pitch, E3.GAP)]
    ms = M.MagnetSystem(r.m, r.p.pitch, r.p.gap, LY.MP42, tables=tabs[LY.MP42], mags=M.typed(mags, LY.MP42))
    with er3_through(composite_torques(ms)):
        row = E3.measure(r, ms.mags, None, None)
    r.pose({})
    key = lambda g: (g["body"], tuple(np.round(g["pos"], 9)), tuple(np.round(g["dir"], 9)))  # noqa: E731
    same_set = sorted(map(key, mags)) == sorted(map(key, LY.arm_mags("L0")))
    rel = er6_metric(row, er3_row)
    return {"same_magnet_set_as_layout": bool(same_set), "rel_diff_vs_er3": rel, "pass": bool(same_set and rel <= 1e-9),
            "explanation": "Diagnostic, not the protocol's check. ER3's L0 row was computed with ER3's magnet order. "
                           "pair_forces expands the near-field term about the first magnet's axis (ax = n[i], "
                           "magnets.py l.428), so at a nonzero relative tilt a pair's energy depends on which magnet is "
                           "i. The same magnets in layout() order (the order ER7's L0, M5 and the Part G arms use) "
                           "therefore give different single-piece stiffnesses; with ER3's order this path reproduces "
                           "ER3's row. The protocol's check (rel_diff_vs_er3, layout() order) is kept as the pass flag."}


def gs5() -> dict:
    """GS5 (G.5): 48-only reproduces ER3's L0 row to 1e-9 and ER1's probe-5 values to their reported precision;
    40-only reproduces Part A's S1 (ER6's N52 c = 0.2 mm row, 1e-9) and S2 (26 zero modes; collective twist below
    1 mN m/rad)."""
    er3 = [r for r in json.loads((REPO / "experiments/ER3_layout_design/results/screen.json").read_text())["rows"]
           if r["variant"] == ER3_L0_VARIANT][0]
    er6 = [r for r in json.loads((REPO / "experiments/ER6_real_placement_screen/results/screen.json").read_text())["rows"]
           if r["variant"] == ER6_C52_VARIANT][0]
    er1 = {c["case"]: c["restoring_stiffness_mNm_per_rad"] for c in json.loads(
        (REPO / "experiments/ER1_rest_slip_review/results/probe_magnet_stiffness.json").read_text())["cases"]}
    l0 = measure("L0", "N35")
    rel3 = er6_metric(l0["er3"], er3)
    p5 = {k: v["restoring_stiffness_mNm_per_rad"] for k, v in l0["probe5"].items()}
    p5_rounded = {k: round(p5[k] / 1e3, 2) for k in ER1_REPORTED_N_m}
    p5_rel = {k: abs(p5[k] - er1[k]) / abs(er1[k]) for k in er1}
    order = er3_order_check(er3)
    a = {"er3_row": ER3_L0_VARIANT, "rel_diff_vs_er3": rel3, "extended_rel_diff_vs_er3": extended_metric(l0["er3"], er3),
         "er3_row_pass": bool(rel3 <= 1e-9), "magnet_order": "magnets.layout() (protocol's check)",
         "with_er3_magnet_order": order,
         "probe5_mNm_per_rad": p5, "probe5_N_m_per_rad_2dp": p5_rounded, "er1_reported_N_m_per_rad": ER1_REPORTED_N_m,
         "probe5_rel_diff_vs_er1_json": p5_rel, "probe5_pass": bool(p5_rounded == ER1_REPORTED_N_m),
         "pass": bool(rel3 <= 1e-9 and p5_rounded == ER1_REPORTED_N_m)}
    c52 = measure("C52", "N52")
    rel6 = er6_metric(c52["er3"], er6)
    f = c52["full"]
    b = {"S1": {"er6_row": ER6_C52_VARIANT, "rel_diff_vs_er6": rel6, "pass": bool(rel6 <= 1e-9)},
         "S2": {"n_zero": f["n_zero"], "collective_twist_mNm_per_rad": f["collective_twist_mNm_per_rad"],
                "pass": bool(f["n_zero"] == 26 and abs(f["collective_twist_mNm_per_rad"]) < 1.0)}}
    b["pass"] = bool(b["S1"]["pass"] and b["S2"]["pass"])
    return {"48_only": a, "40_only": b, "tables": {"L0": LY.table_files("L0"), "C52": LY.table_files("C52", "N52")},
            "pass": bool(a["pass"] and b["pass"])}


# ---- GS6, polarity ---------------------------------------------------------------------------------------------------
def pair_energy(ms, i: int, j: int, p: np.ndarray, n: np.ndarray) -> float:
    """Energy (J) of the single pair (i, j) by the system's own law: pair_forces with the pair's type and table for
    same-type pairs, cross_pair_forces for cross-type pairs (magnets.py MagnetSystem.contributions)."""
    ii, jj = np.array([i]), np.array([j])
    if not ms.composite:
        return M.pair_forces(ms.mp, ms.spline, ii, jj, p, n)[2]
    ti, tj = int(ms.type_of[i]), int(ms.type_of[j])
    if ti == tj:
        return M.pair_forces(ms.types[ti], ms.type_splines[ti], ii, jj, p, n)[2]
    return M.cross_pair_forces(ms.moments, ms.mp.far_r1, ms.mp.far_r2, ii, jj, p, n)[2]


GS6_POSES = (("home", {}), ("U +30", SC.face_turn_moves("U", 30.0)), ("R -45", SC.face_turn_moves("R", -45.0)),
             ("F +12.5", SC.face_turn_moves("F", 12.5)), ("E1-5-like a=+5 R=40", SC.e15_moves(5.0, 40.0)))


def gs6_polarity(arm: str = "PG20", grade: str = "N52", tables: dict | None = None, far_every: int = 23) -> dict:
    """The pair energy with one moment reversed (either magnet) equals minus the original, to 1e-12 relative, for every
    near pair and every far_every-th far pair of each class, at the GS6_POSES. Reports pass and the largest relative
    deviation per class (machine-precision check; not a physics result)."""
    kin = SC.Kin()
    ms = LY.build_system(kin.m, arm, grade, tables, pitch=kin.p.pitch, gap=kin.p.gap)
    cs = ST.ClassStats(ms.mags, ms.mp, ST.PROXY_D_VAL)
    names = {0: "CE", 1: "PC", 3: "PP3", 4: "X"}
    worst = {names[c]: {"pairs": 0, "max_rel": 0.0} for c in names if np.any(cs.code == c)}
    for _, moves in GS6_POSES:
        kin.pose(moves)
        p, n = ms.world(kin.d.xpos, kin.d.xmat)
        r = np.linalg.norm(p[cs.jj] - p[cs.ii], axis=1)
        sel = np.nonzero((r < ms.mp.r2) | (np.arange(len(r)) % far_every == 0))[0]
        for k in sel:
            i, j = int(cs.ii[k]), int(cs.jj[k])
            u0 = pair_energy(ms, i, j, p, n)
            for flip in (i, j):
                n2 = n.copy(); n2[flip] = -n2[flip]
                u1 = pair_energy(ms, i, j, p, n2)
                rel = abs(u1 + u0) / abs(u0) if u0 != 0 else abs(u1)
                w = worst[names[int(cs.code[k])]]
                w["max_rel"] = max(w["max_rel"], rel)
            worst[names[int(cs.code[k])]]["pairs"] += 1
    return {"arm": arm, "grade": grade, "classes": worst,
            "pass": bool(all(w["max_rel"] <= 1e-12 and w["pairs"] > 0 for w in worst.values()))}


# ---- P3 (stub) -------------------------------------------------------------------------------------------------------
P3_INPUTS = [
    {"item": "On-axis 4x3 piece magnet wall (both arms)", "source": "side_checks/realfit/stage5_sizes_and_gaps.log",
     "status": "committed (FACT in G.6 P3)"},
    {"item": "L0's 48 at simulated positions measured as 4x3: outer-face walls", "status": "committed (FACT)",
     "source": "side_checks/realfit/stage4_m5_positions.log"},
    {"item": "Same for M5's own 4x2", "status": "TODO",
     "source": "rerun realfit/stage4_m5_positions.py with a 4x2 position set (realfit/dump_positions.py); needs CAD"},
    {"item": "Core cover at c = 0.2 mm", "source": "side_checks/realfit/stage2b_core_gaps.log", "status": "committed"},
    {"item": "On-axis piece magnet to the same piece's 4x2 magnets: surface gap", "status": "TODO",
     "source": "realfit/fitlib.cyl_cyl_gap"},
    {"item": "Core-to-core spacing, on-axis: surface gap", "status": "TODO", "source": "realfit/fitlib.cyl_cyl_gap"},
    {"item": "Hard stop: protrusion, surface gap < 0.5 mm, overlap", "status": "evaluated from the rows above"},
]


def p3_inputs() -> dict:
    """P3 is not computed by code in this repository (CAD licence unconfirmed; G.6 P3). This lists its inputs."""
    return {"protocol": "ER9 PROTOCOL.md Part G, G.6 P3", "computed": False, "inputs": P3_INPUTS,
            "note": "stub: the TODO rows need the git-ignored CAD mesh outside the repository"}


def _write_new(path: Path, rec: dict) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x") as f:
        f.write(json.dumps(rec, indent=1, default=float))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("p2", "gs5", "p3"))
    ap.add_argument("arm", nargs="?")
    ap.add_argument("--grade", default=None)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    D10 = _load("d10_rest", REPO / "experiments/D10_m5_rest_diagnostic/d10_rest.py")
    if a.mode == "p3":
        print(json.dumps(p3_inputs(), indent=1))
        return
    if a.mode == "gs5":
        rec = {**gs5(), "env": D10.environment()}
        _write_new(Path(a.out) / "GS5.json", rec)
        print(json.dumps({k: rec[k] for k in ("48_only", "40_only", "pass")}, indent=1, default=float))
        return
    if a.arm is None:
        raise SystemExit("p2 needs an arm")
    grade = a.grade or ("N35" if a.arm == "L0" else "N52")
    LY.check_arm(a.arm, grade)
    rec = {**p2(a.arm, grade), "env": D10.environment()}
    _write_new(Path(a.out) / f"P2_{a.arm}_{grade}.json", rec)
    print(json.dumps({"arm": a.arm, "grade": grade, "stopped": rec["stopped"], "stops": rec["stops"]}, indent=1,
                     default=float))


if __name__ == "__main__":
    main()
