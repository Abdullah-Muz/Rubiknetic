"""Compact table of stage3_results.json (numbers only)."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
r = json.loads((HERE / "stage3_results.json").read_text())
def fmt(x):
    return "  -   " if x is None else f"{x:6.2f}"
for kind, home, tgt in (("edge", [1, 1, 0], "centre"), ("edge", [1, 1, 0], "corner"), ("corner", [1, 1, 1], "centre"), ("corner", [1, 1, 1], "edge")):
    print(f"== {kind} {home} toward {tgt}:  gamma | material intervals | 4x3: wall@layout, best wall, face ranges wall>=0.4 | 3x2: same")
    for g in range(41):
        R = [x for x in r["sweep"] if x["kind"] == kind and x["home"] == home and x["toward"] == tgt and x["gamma_deg"] == g]
        if not R:
            continue
        line = f"{g:3d} | {R[0]['material_intervals_mm']} |"
        for s in ("4x3", "3x2"):
            wl = [x[s]["wall_at_layout_depth_mm"] for x in R]
            bw = [x[s].get("best_wall_mm") for x in R]
            wl_min = None if any(v is None for v in wl) else min(wl)
            spread = 0 if any(v is None for v in wl) else max(wl) - min(wl)
            line += f" {s}: {fmt(wl_min)} (spread {spread:.3f}) best {fmt(None if any(v is None for v in bw) else min(bw))} rng0.4 {R[0][s].get('inner_face_radius_range_wall>=0.4_mm')} rng0 {R[0][s].get('inner_face_radius_range_wall>=0_mm')} |"
        print(line)
