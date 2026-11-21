"""Stage 2b: closest core-magnet pairs for every clearance with a wider search (stage 2 looked only within 9 mm
centre distance, which found no pair at clearance 0.2 mm), and the plastic cover over a core magnet for a given
ball radius. Simulation positions only; no CAD."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np  # noqa: E402

import fitlib as L  # noqa: E402

pos = json.loads((HERE / "positions.json").read_text())
a, hl = pos["mp"]["diameter"] * 1e3 / 2, pos["mp"]["length"] * 1e3 / 2
res = {}
for key in ("anchored_c0.2", "hybrid_c1", "hybrid_c2", "hybrid_c3"):
    core = [m for m in pos[key] if m["body"] == "core"]
    C = np.array([m["pos"] for m in core]) * 1e3
    D = np.array([m["dir"] for m in core])
    best = {}
    for i in range(len(core)):
        for j in range(i + 1, len(core)):
            d = float(np.linalg.norm(C[i] - C[j]))
            if d < 14.0:
                lab = " / ".join(sorted([core[i]["kind"], core[j]["kind"]]))
                g = L.cyl_cyl_gap(C[i], D[i], a, hl, C[j], D[j], a, hl, h=0.1)
                if lab not in best or g < best[lab][1]:
                    best[lab] = (d, g)
    rim = {k: float(np.sqrt((np.linalg.norm(C[[m["kind"] == k for m in core]], axis=1).max() + hl) ** 2 + a ** 2)) for k in ("core_edge", "core_corner")}
    res[key] = {"closest_pairs": {k: {"centre_distance_mm": v[0], "surface_gap_mm": v[1]} for k, v in best.items()},
                "min_surface_gap_mm": min(v[1] for v in best.values()), "outer_rim_radius_mm": rim,
                "cover_over_rim_mm_for_ball_radius": {f"{rb}": {k: rb - v for k, v in rim.items()} for rb in (21.9, 21.84, 21.75, 21.735)}}
    print(key, json.dumps(res[key]))
(HERE / "stage2b_results.json").write_text(json.dumps(res, indent=1))
