"""ER9 Part G, P3 hard stop (fit), from committed side-check numbers plus a surface-gap computation (exploratory).

G.6 P3 hard stop (all fit options): a magnet protrudes from its piece or core volume, any two magnets have a surface
gap below 0.5 mm, or two magnets overlap. The CAD mesh is not in the repository (licence unconfirmed), so protrusion is
taken from the committed side-check results (cited per item), and the surface gaps are computed here for every pair of
magnets of the arm at home (same piece, different pieces, piece-core and core-core) with realfit's cyl_cyl_gap.
Pairs whose centres are farther apart than the sum of the two bounding-sphere radii + 0.5 mm cannot have a gap below
0.5 mm and are counted, not sampled. Gaps are invariant in rigid face turns for pairs on one body; pairs on different
bodies in turns are P1's (min_surface_clearance_mm).

Two steps (two venvs):
  ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9g_p3.py dump ARM OUT.json
  ~/.venvs/cadtools/bin/python -I experiments/ER9_anchored_core_layouts/er9g_p3.py gaps ARM OUT.json
The second writes results/hybrid_g/static/P3_<ARM>.json (exclusive create).
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "results" / "hybrid_g" / "static"

PROTRUSION_ITEMS = [
    {"item": "M5's 48 corner-edge magnets at L0's positions",
     "value": "fully inside every piece; outer-face wall 0.425 mm (edges), 0.175 mm (corners)",
     "protrudes": False, "source": "side_checks/realfit/stage4_m5_positions.log (summary lines; measured as 4x3, "
     "INFERENCE: the 4x2 lies inside the 4x3 envelope at the same outer face, G.6 P3 table)"},
    {"item": "On-axis 4x3 piece magnets of the core pairs",
     "value": "fit with wall >= 0.4 mm at gamma = 0 (edges and corners)", "protrudes": False,
     "source": "side_checks/realfit/stage5_sizes_and_gaps.log 'gamma_wall>=0.4' rows; ER4 REPORT section 2"},
    {"item": "Core-side 4x3 magnets at c = 0.2 mm", "value": "core cover 0.202 (edge), 0.292 (corner) mm at the rim",
     "protrudes": False, "source": "side_checks/realfit/stage2b_core_gaps.log (single ball R = 21.735 mm)"},
]


def _git_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()


def dump(arm: str, out: str) -> None:
    spec = importlib.util.spec_from_file_location("er9g_layouts", HERE / "er9g_layouts.py")
    LY = importlib.util.module_from_spec(spec); spec.loader.exec_module(LY)
    mags = LY.arm_mags(arm)
    rows = []
    for g in mags:
        mp = g["mp"]
        rows.append({"body": g["body"], "kind": g.get("kind"), "pos": [float(x) for x in np.asarray(g["pos"])],
                     "dir": [float(x) for x in np.asarray(g["dir"])], "radius": mp.diameter / 2, "length": mp.length})
    Path(out).write_text(json.dumps({"arm": arm, "commit": _git_commit(), "mags": rows}))
    print(f"dumped {len(rows)} magnets")


def gaps(arm: str, src: str) -> None:
    spec = importlib.util.spec_from_file_location("fitlib", HERE / "side_checks" / "realfit" / "fitlib.py")
    FL = importlib.util.module_from_spec(spec); spec.loader.exec_module(FL)
    d = json.loads(Path(src).read_text())
    assert d["arm"] == arm
    m = d["mags"]
    n = len(m)
    rows, n_bounded, best = [], 0, (np.inf, None)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = m[i], m[j]
            ca, cb = np.array(a["pos"]) * 1e3, np.array(b["pos"]) * 1e3           # mm
            ra = np.hypot(a["radius"], a["length"] / 2) * 1e3
            rb = np.hypot(b["radius"], b["length"] / 2) * 1e3
            dist = float(np.linalg.norm(ca - cb))
            if dist > ra + rb + 0.5:
                n_bounded += 1
                continue
            gap = FL.cyl_cyl_gap(ca, np.array(a["dir"]), a["radius"] * 1e3, a["length"] / 2 * 1e3,
                                 cb, np.array(b["dir"]), b["radius"] * 1e3, b["length"] / 2 * 1e3)
            same = a["body"] == b["body"]
            rows.append({"i": i, "j": j, "bodies": [a["body"], b["body"]], "same_body": same,
                         "centre_mm": dist, "surface_gap_mm": gap})
            if gap < best[0]:
                best = (gap, rows[-1])
    gap_min = best[0] if rows else None
    gap_stop = gap_min is not None and gap_min < 0.5
    rec = {"arm": arm, "check": "P3 hard stop (G.6)", "positions_commit": d["commit"], "commit": _git_commit(),
           "items": PROTRUSION_ITEMS,
           "surface_gaps": {"pairs_total": n * (n - 1) // 2, "pairs_bounded_by_spheres": n_bounded,
                            "pairs_sampled": len(rows), "min_surface_gap_mm": gap_min, "min_pair": best[1],
                            "method": "realfit fitlib.cyl_cyl_gap, h = 0.05 mm sampling, at home",
                            "sampled": rows},
           "protrusion": any(it["protrudes"] for it in PROTRUSION_ITEMS),
           "hard_stop": bool(gap_stop or any(it["protrudes"] for it in PROTRUSION_ITEMS)),
           "note": "Protrusion items are committed side-check numbers (the CAD mesh is outside the repository); the "
                   "TODO reruns of G.13 that need the CAD were not done. Recorded as Part G deviation 2."}
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"P3_{arm}.json"
    with open(path, "x") as f:
        json.dump(rec, f, indent=1)
    print(json.dumps({"arm": arm, "min_surface_gap_mm": gap_min, "sampled": len(rows), "hard_stop": rec["hard_stop"]}))


if __name__ == "__main__":
    mode, arm, path = sys.argv[1:4]
    assert arm in ("PG8", "PG20", "PG20r"), arm
    dump(arm, path) if mode == "dump" else gaps(arm, path)
