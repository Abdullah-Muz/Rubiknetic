"""V3 pair check extended to a 0.35 mm face gap (UNSCORED; M5 pre-registration §4 and §6.1 item 5).

M5's E1-7 face-gap arm at 0.35 mm (wall 0.15 mm, piece gap 0.05 mm) puts facing magnets 0.35 mm apart, below the
0.5-1.5 mm face gaps at which V3 part (a) tested magnet pairs (d8_1b_checks.py:133). This script reruns V3 part (a)
with 0.35 mm added to the gap list and NOTHING ELSE CHANGED:
  * magnet: nominal 4 x 2 mm N35, scale 1 (d8_1b_checks.MP), the configuration of the face-gap arm;
  * the same offsets (0 to 6 mm in 0.37 mm steps), reference quadrature REF_QUAD, fine_pair and hybrid_pair;
  * the same normaliser: the aligned facing-pair normal force at the nominal 1.0 mm gap (Fn_nominal_N);
  * the same criteria: force error <= 5 % of Fn_nominal_N; torque error <= max(5 % of the largest reference torque
    in the set, 2e-5 N m), where the set is the whole extended set (0.35 mm plus V3's five gaps).
Pass = every row of the extended set passes. The record has no "V3" key, so the M5 runner's V3 lookup ignores it.
Usage (WSL): ~/.venvs/rubiknetic/bin/python experiments/D8_alignment/v3_pair_extension.py
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import d8_1b_checks as C  # noqa: E402  (V3 functions and settings, imported unchanged)
from magnets import near_field_tables  # noqa: E402

GAPS_M = (0.00035, 0.0005, 0.00075, 0.001, 0.00125, 0.0015)   # V3 part (a) gaps plus 0.35 mm
OUT_NAME = "d8_1b_checks_pair0.35mm_4x2_N35_s1.json"


def pair_extension(spline) -> dict:
    mp = C.MP
    L = mp.length
    fn_nom = abs(C.fine_pair(mp, [0, 0, 0], [0, 0, 1], [0, 0, L + 0.001], [0, 0, 1], *C.REF_QUAD)[0][2])
    rows = []
    z_axis = [0.0, 0.0, 1.0]
    for g in GAPS_M:
        for s in np.arange(0.0, 0.0061, 0.00037):
            p2 = [s, 0, L + g]
            ff, tf, _ = C.fine_pair(mp, [0, 0, 0], z_axis, p2, z_axis, *C.REF_QUAD)
            fh, th, _ = C.hybrid_pair(mp, spline, [0, 0, 0], z_axis, p2, z_axis)
            rows.append({"gap_mm": g * 1e3, "offset_mm": s * 1e3, "fine_N": ff.tolist(), "hybrid_N": fh.tolist(),
                         "err_rel_Fn": float(np.linalg.norm(fh - ff) / fn_nom), "fine_T_Nm": tf.tolist(),
                         "hybrid_T_Nm": th.tolist(), "T_err_Nm": float(np.linalg.norm(th - tf))})
    t_tol = max(0.05 * max(np.linalg.norm(r["fine_T_Nm"]) for r in rows), 2e-5)
    by_gap = {}
    for g in GAPS_M:
        rg = [r for r in rows if np.isclose(r["gap_mm"], g * 1e3)]
        by_gap[f"{g * 1e3:g}"] = {"worst_err_rel_Fn": max(r["err_rel_Fn"] for r in rg),
                                  "worst_T_err_Nm": max(r["T_err_Nm"] for r in rg)}
    worst_f = max(r["err_rel_Fn"] for r in rows)
    worst_t = max(r["T_err_Nm"] for r in rows)
    return {"gaps_mm": [g * 1e3 for g in GAPS_M], "ref_quad": C.REF_QUAD, "Fn_nominal_N": fn_nom,
            "pair_T_tol_Nm": t_tol, "worst_err_rel_Fn": worst_f, "worst_T_err_Nm": worst_t, "by_gap": by_gap,
            "rows": rows, "pass": bool(worst_f <= 0.05 and worst_t <= t_tol)}


def main() -> None:
    t0 = time.perf_counter()
    spline = near_field_tables(C.MP, C.CACHE)
    res = {"kind": "V3 part (a) pair check extended to 0.35 mm (M5 pre-registration §4)",
           "magnet_params": asdict(C.MP), "Br_T": C.MP.br, "mujoco": mujoco.__version__}
    res["V3_pair_extension"] = pair_extension(spline)
    res["wall_s"] = round(time.perf_counter() - t0, 1)
    v = res["V3_pair_extension"]
    print("by gap:", v["by_gap"], f"T tol {v['pair_T_tol_Nm']:.2e}", "pass", v["pass"], f"wall {res['wall_s']} s")
    (C.OUT / OUT_NAME).write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
