"""Is the reference edge (corner) unchanged, as a shape, by the mirror / rotation symmetries that exchange its anchor
pairs? stage0 showed the vertex sets are not (only the identity maps vertices onto vertices), which may be only the
triangulation. Here: two-sided surface distance between the piece and its image, from dense surface samples."""
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

import fitlib as L  # noqa: E402

parts = L.load_parts()
MATS = []
for perm in itertools.permutations(range(3)):
    for sg in itertools.product((1, -1), repeat=3):
        M = np.zeros((3, 3))
        for i in range(3):
            M[i, perm[i]] = sg[i]
        MATS.append(M)
res = {}
for kind, home in (("edge", (1, 1, 0)), ("corner", (1, 1, 1))):
    p = [q for q in parts if q["home"] == home][0]
    fine = L.sample_tris(p["V"], p["F"], 0.08)
    coarse = L.sample_tris(p["V"], p["F"], 0.3)
    tree = cKDTree(fine)
    rows = []
    for M in MATS:
        if not np.allclose(M @ np.array(home, float), home) or np.allclose(M, np.eye(3)):
            continue
        d = tree.query(coarse @ M.T)[0]
        rr = np.linalg.norm(coarse, axis=1)
        foot = rr < 27.0                                   # the region near the core, where the anchors sit
        rows.append({"det": int(round(np.linalg.det(M))), "matrix": M.astype(int).tolist(),
                     "max_surface_distance_mm": float(d.max()), "max_surface_distance_within_27mm_of_centre_mm": float(d[foot].max()),
                     "share_of_samples_further_than_0.1mm": float((d > 0.1).mean())})
    res[kind] = rows
    print(kind, "non-identity symmetries of the home position:", len(rows))
    for r in rows:
        print("   det", r["det"], "max surface distance", round(r["max_surface_distance_mm"], 3), "mm; within 27 mm of the centre",
              round(r["max_surface_distance_within_27mm_of_centre_mm"], 3), "mm; share > 0.1 mm", round(r["share_of_samples_further_than_0.1mm"], 4))
(HERE / "stage0b_results.json").write_text(json.dumps(res, indent=1))
