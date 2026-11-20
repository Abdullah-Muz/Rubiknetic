"""ER9 part E: the strength scale at which a 4 x 3 mm N35 corner-edge pair pulls as hard as M5's 4 x 2 mm N35 pair.

Both pairs are coaxial and face each other across the same face gap (piece gap + 2 walls); the 4 x 3 magnets sit
0.5 mm deeper each. The pull is taken from each magnet's own table through magnets.pair_forces. Also prints the pull
and the lateral stiffness of one anchor pair at several clearances, for the 4 x 3 magnet at that scale.
Usage (WSL, repo root):  ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9_hybrid_scale.py
Writes results/hybrid/scale.json.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("er9_probe", HERE / "er9_probe.py")
P = importlib.util.module_from_spec(spec); sys.modules["er9_probe"] = P; spec.loader.exec_module(P)
E7, M4, R = P.E7, P.M4, P.R

from rubiknetic.cube_physics.magnets import near_field_tables, pair_forces  # noqa: E402


def pull(mp, spline, centre_dist: float, lateral: float = 0.0) -> np.ndarray:
    """Force on magnet 1 of a parallel pair: magnet 0 at the origin, magnet 1 at (lateral, 0, centre_dist)."""
    p = np.array([[0.0, 0.0, 0.0], [lateral, 0.0, centre_dist]])
    n = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]])
    out = pair_forces(mp, spline, np.array([0]), np.array([1]), p, n)
    return np.asarray(out[0])[1]


def main() -> None:
    m5 = R.magnet_params_for({})
    s5 = near_field_tables(m5, M4.TABLES)
    m43, table, _ = P.table_for("N35", 1.0)
    s43 = near_field_tables(m43, table.parent)
    face_gap = R.GAP + 2 * m5.wall
    f5 = pull(m5, s5, face_gap + m5.length)
    f43 = pull(m43, s43, face_gap + m43.length)
    scale = float(f5[2] / f43[2])
    res = {"face_gap_mm": face_gap * 1e3, "m5_4x2_N35_pull_N": float(f5[2]), "4x3_N35_pull_N": float(f43[2]),
           "matching_scale": scale, "anchor_pair_4x3_N35_at_matching_scale": {}}
    for c_mm in (0.2, 1.0, 2.0, 3.0):
        d = c_mm * 1e-3 + 2 * m43.wall + m43.length
        f0 = pull(m43, s43, d) * scale
        h = 1e-5
        k = (pull(m43, s43, d, h)[0] - pull(m43, s43, d, -h)[0]) / (2 * h) * scale
        res["anchor_pair_4x3_N35_at_matching_scale"][f"{c_mm:g}"] = {
            "centre_distance_mm": d * 1e3, "pull_N": float(f0[2]), "lateral_stiffness_N_per_m": float(k)}
    (HERE / "results" / "hybrid").mkdir(parents=True, exist_ok=True)
    (HERE / "results" / "hybrid" / "scale.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
