"""ER9 Part G static self-checks GS3, GS3b, GS5 and GS6 (PROTOCOL.md G.5). GS1, GS2 (dynamic records) and GS4 (one
dynamic trial with and without the diagnostic) belong to the runner (er9g_run.py), not to this script.
GS3b (added by the coordinator's review, not in G.5): at 20 kinematic poses (seed 2611; face turns plus small random
tilts), the composite PG20 (PG20r, PG8) system's per-magnet forces, torques and energy equal the sum of the single-type
4x2 system, the single-type 4x3 system and cross_pair_forces over every cross pair, to 1e-12 relative. It exercises
the composite path, which GS1 (48-only) and GS2 (40-only) do not.

Usage (WSL, repo root):
  ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9g_selfcheck_static.py [--out FILE]
Writes FILE (default results/hybrid_g/selfcheck_static.json; exclusive create).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from rubiknetic.cube_physics import magnets as M

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "results" / "hybrid_g" / "selfcheck_static.json"


def _load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


LY = _load("er9g_layouts", HERE / "er9g_layouts.py")
ST = _load("er9g_stats", HERE / "er9g_stats.py")
SS = _load("er9g_static", HERE / "er9g_static.py")


GS3B_SEED = 2611
GS3B_POSES = 20


def gs3b(arm: str = "PG20", grade: str = "N52", tables: dict | None = None, n_poses: int = GS3B_POSES) -> dict:
    """Composite = 4x2 system + 4x3 system + cross dipole pairs, per magnet, at random kinematic poses."""
    SC = SS.SC
    LY.check_arm(arm, grade)
    if arm not in LY.PART_G_ARMS:
        raise ValueError("GS3b applies to composite arms only")
    kin = SC.Kin()
    tables = LY.load_tables(arm, grade) if tables is None else tables
    pitch, gap = kin.p.pitch, kin.p.gap
    comp = LY.build_system(kin.m, arm, grade, tables, pitch=pitch, gap=gap)
    mags = comp.mags
    k42 = np.array([not LY.is_43(g) for g in mags])
    mp43 = LY.mp43(grade)
    s42 = M.MagnetSystem(kin.m, pitch, gap, LY.MP42, tables=tables[LY.MP42], mags=[g for g in mags if not LY.is_43(g)])
    s43 = M.MagnetSystem(kin.m, pitch, gap, mp43, tables=tables[mp43], mags=[g for g in mags if LY.is_43(g)])
    assert k42[:48].all() and not k42[48:].any()          # 4x2 first, then 4x3 (arm_mags order)
    ii, jj = comp.ii_all, comp.jj_all
    cross = k42[ii] != k42[jj]
    ci, cj = ii[cross], jj[cross]
    rng = np.random.default_rng(GS3B_SEED)
    faces = list(SC.FACES)
    worst = {"F": 0.0, "T": 0.0, "U": 0.0}
    for k in range(n_poses):
        face = faces[k % 6]
        base = SC.face_turn_moves(face, float(rng.uniform(-90, 90))) if k % 4 else {}
        moves = {x: (Rotation.from_rotvec(np.radians(rng.normal(0, 1.0, 3)))
                     * Rotation.from_rotvec(base.get(x, np.zeros(3)))).as_rotvec() for x in SC.NAMES}
        kin.pose(moves)
        p, n = comp.world(kin.d.xpos, kin.d.xmat)
        for s in (comp, s42, s43):
            s.reset_neighbour_list()
        F, T, U = comp.forces(p, n)
        F42, T42, U42 = s42.forces(p[:48], n[:48])
        F43, T43, U43 = s43.forces(p[48:], n[48:])
        Fc, Tc, Uc, _ = M.cross_pair_forces(comp.moments, comp.mp.far_r1, comp.mp.far_r2, ci, cj, p, n)
        Fr = np.vstack([F42, F43]) + Fc
        Tr = np.vstack([T42, T43]) + Tc
        Ur = U42 + U43 + Uc
        worst["F"] = max(worst["F"], float(np.abs(F - Fr).max() / np.abs(Fr).max()))
        worst["T"] = max(worst["T"], float(np.abs(T - Tr).max() / np.abs(Tr).max()))
        worst["U"] = max(worst["U"], abs(U - Ur) / abs(Ur))
    return {"arm": arm, "grade": grade, "poses": n_poses, "seed": GS3B_SEED, "n_cross_pairs": int(cross.sum()),
            "max_rel_diff": worst, "pass": bool(max(worst.values()) <= 1e-12)}


def run() -> dict:
    t0 = time.perf_counter()
    gs3 = {g: LY.gs3(g) for g in LY.GRADES}
    g3b = {a: gs3b(a, "N52") for a in ("PG20", "PG20r", "PG8")}
    gs5 = SS.gs5()
    pol = {a: SS.gs6_polarity(a, "N52") for a in ("PG20", "PG20r", "PG8")}
    dev = {a: ST.gs6_path_deviation(a, "N52") for a in ("PG20", "PG8")}
    res = {"GS3": {"grades": gs3, "pass": all(v["pass"] for v in gs3.values())},
           "GS3b": {"arms": g3b, "pass": all(v["pass"] for v in g3b.values())},
           "GS5": gs5,
           "GS6": {"polarity": pol, "path_deviation": dev,
                   "pass": all(v["pass"] for v in pol.values()) and all(v["pass"] for v in dev.values())}}
    res["pass"] = bool(res["GS3"]["pass"] and res["GS3b"]["pass"] and res["GS5"]["pass"] and res["GS6"]["pass"])
    res["wall_s"] = time.perf_counter() - t0
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    D10 = _load("d10_rest", REPO / "experiments/D10_m5_rest_diagnostic/d10_rest.py")
    res = {**run(), "env": D10.environment()}
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "x") as f:
        f.write(json.dumps(res, indent=1, default=float))
    print(json.dumps({"GS3": res["GS3"]["pass"], "GS3b": res["GS3b"]["pass"], "GS5": res["GS5"]["pass"], "GS6": res["GS6"]["pass"],
                      "pass": res["pass"]}, indent=1))


if __name__ == "__main__":
    main()
