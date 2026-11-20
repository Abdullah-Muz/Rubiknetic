"""ER9 part E, static check: which magnet pairs of a hybrid layout come within near-field range (r < r2) at an
orientation the force law treats as perpendicular (|cos| <= cos 45 deg), at home and through a rigid quarter turn of U.
Kinematic only (no dynamics). Usage (WSL, repo root):
    ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9_hybrid_pairs.py CLEAR_MM [key=value ...]
keys: scale, base (0/1), edge_gamma, corner_gamma, radius_shift_mm (anchors moved inward along their axes).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("er9_hybrid", HERE / "er9_hybrid.py")
HY = importlib.util.module_from_spec(spec); sys.modules["er9_hybrid"] = HY; spec.loader.exec_module(HY)


def scan(mp, mags, step_deg: float = 1.0) -> dict:
    body = [g["body"] for g in mags]
    p0 = np.array([g["pos"] for g in mags]); n0 = np.array([g["dir"] for g in mags])
    in_u = np.array([b != "core" and b.startswith("cubie_") and b[-1] == "p" for b in body])
    ii, jj = np.triu_indices(len(mags), 1)
    keep = np.array([body[i] != body[j] for i, j in zip(ii, jj)])
    ii, jj = ii[keep], jj[keep]
    out = {"n_magnets": len(mags), "home_near_perp": 0, "pairs": {}, "min_r_mm_perp": None}
    for ang in np.arange(0.0, 90.0 + 1e-9, step_deg):
        rot = Rotation.from_euler("z", -ang, degrees=True).as_matrix()
        p, n = p0.copy(), n0.copy()
        p[in_u], n[in_u] = p0[in_u] @ rot.T, n0[in_u] @ rot.T
        r = np.linalg.norm(p[jj] - p[ii], axis=1)
        cosn = np.abs(np.einsum("ij,ij->i", n[ii], n[jj]))
        bad = (r < mp.r2) & (cosn <= np.cos(np.radians(45)))
        if ang == 0.0:
            out["home_near_perp"] = int(bad.sum())
        for k in np.nonzero(bad)[0]:
            key = f"{mags[ii[k]]['kind']}@{body[ii[k]]} - {mags[jj[k]]['kind']}@{body[jj[k]]}"
            e = out["pairs"].setdefault(key, {"min_r_mm": 1e9, "angles": []})
            e["min_r_mm"] = min(e["min_r_mm"], float(r[k]) * 1e3)
            e["angles"].append(float(ang))
    for e in out["pairs"].values():
        e["angles"] = [min(e["angles"]), max(e["angles"])]
    out["n_pairs"] = len(out["pairs"])
    if out["pairs"]:
        out["min_r_mm_perp"] = min(e["min_r_mm"] for e in out["pairs"].values())
    return out


def main() -> None:
    kv = dict(a.split("=") for a in sys.argv[2:])
    cfg = HY.cfg_for(float(sys.argv[1]), scale=float(kv.get("scale", HY.SCALE_M5)), base=bool(int(kv.get("base", 1))),
                     edge_opt=("split", float(kv.get("edge_gamma", 20)), "centre"),
                     corner_opt=("tri", float(kv.get("corner_gamma", 16)), "centre"))
    mp, mags = HY.hybrid_mags(cfg)
    res = scan(mp, mags)
    kinds = {}
    for k, e in res["pairs"].items():
        a, b = (s.split("@")[0] for s in k.split(" - "))
        t = kinds.setdefault(f"{a} - {b}", {"n": 0, "min_r_mm": 1e9, "angles": [90.0, 0.0]})
        t["n"] += 1; t["min_r_mm"] = min(t["min_r_mm"], e["min_r_mm"])
        t["angles"] = [min(t["angles"][0], e["angles"][0]), max(t["angles"][1], e["angles"][1])]
    print(json.dumps({"config": cfg, "n_magnets": res["n_magnets"], "home_near_perp": res["home_near_perp"],
                      "n_pairs": res["n_pairs"], "min_r_mm_perp": res["min_r_mm_perp"], "by_kind": kinds}, indent=1))


if __name__ == "__main__":
    main()
