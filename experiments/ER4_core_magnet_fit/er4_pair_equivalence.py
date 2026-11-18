"""ER4 part 3 (static): tangential stiffness of ONE core-to-piece magnet pair placed in the real-cube geometry
(piece inner point 22.04 mm for edges and 21.95 mm for corners, from er4_fit_geometry part 2; ball-core surface at
r_in - c), for the validated 4x2 mm tables (N35, 1.19 T; N52, 1.455 T) and core clearances c in {0.1, 0.2, 0.3} mm.
Compared with the B1 candidate "core sigma=2 alone" (ER3): edge slide +522 / cross +490, corner tangential +743
mN m/rad (one core pair per piece there as well). Writes results/pair_equivalence.json."""
import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("d10_rest", REPO / "experiments/D10_m5_rest_diagnostic/d10_rest.py")
D10 = importlib.util.module_from_spec(spec); sys.modules["d10_rest"] = D10; spec.loader.exec_module(D10)
M5 = D10._load_m5(); M4 = M5.M4
from rubiknetic.cube_physics import magnets as MG  # noqa: E402

DLT = np.radians(0.02)
TARGET = {"edge": 522.0, "corner": 743.0}       # B1 core sigma=2 (ER3): edge slide, corner tangential minimum
R_IN = {"edge": 22.04e-3, "corner": 21.95e-3}


def stiffness(mp, spline, r_in, c):
    u = np.array([0.0, 0.0, 1.0])               # radial direction (any; the pair is axisymmetric)
    pc = u * (r_in - c - mp.wall - mp.length / 2)
    pp0 = u * (r_in + mp.wall + mp.length / 2)
    ax = np.array([1.0, 0, 0])                  # tangential rotation axis through the cube centre
    tq = []
    for s in (1, -1):
        th = s * DLT
        Rm = np.array([[1, 0, 0], [0, np.cos(th), -np.sin(th)], [0, np.sin(th), np.cos(th)]])
        p = np.array([pc, Rm @ pp0]); n = np.array([u, Rm @ u])
        F, T, _ = MG.pair_forces(mp, spline, np.array([0]), np.array([1]), p, n, None,
                                 MG.scatter_matrices(2, np.array([0]), np.array([1])))
        tq.append(float((T[1] + np.cross(p[1], F[1])) @ ax))
    return -(tq[0] - tq[1]) / (2 * DLT) * 1e3     # mN m / rad


rows = []
for grade, br in (("N35", None), ("N52", "N52")):
    mp = M5.magnet_params_for({}) if grade == "N35" else M5.magnet_params_for({"magnet": "4x2_N52"})
    spline = M4._tables_for(mp)
    for kind in ("edge", "corner"):
        for c in (0.1e-3, 0.2e-3, 0.3e-3):
            k = stiffness(mp, spline, R_IN[kind], c)
            rows.append({"magnet": f"4x2 {grade} (Br {mp.br} T)", "kind": kind, "clearance_mm": c * 1e3,
                         "face_separation_mm": (c + 2 * mp.wall) * 1e3, "stiffness_mNm_per_rad": k,
                         "target_mNm_per_rad": TARGET[kind], "ratio_to_target": k / TARGET[kind]})
            print(f"{grade} {kind:6s} c={c*1e3:.1f} mm  k={k:+8.1f} mN m/rad  target {TARGET[kind]:.0f}  ratio {k/TARGET[kind]:.2f}")
(REPO / "experiments/ER4_core_magnet_fit/results/pair_equivalence.json").write_text(json.dumps(rows, indent=1))
