"""Frame and identity check: every CAD edge (corner) is the image of a reference edge (corner) under a signed axis
permutation about the origin, and the reference piece is unchanged by the symmetries that exchange its anchor pairs.
This is what makes 'the simulation's cubie at home h' = 'the CAD piece whose centre has the signs of h' unambiguous
up to a symmetry of the whole layout. Numbers only."""
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
for kind, ref_home in (("edge", (1, 1, 0)), ("corner", (1, 1, 1)), ("centre", (1, 0, 0))):
    ps = [p for p in parts if p["kind"] == kind]
    ref = [p for p in ps if p["home"] == ref_home][0]
    tree = cKDTree(ref["V"])
    rows = []
    for p in ps:
        best = None
        n_ok = 0
        for M in MATS:
            if not np.allclose(M @ np.array(p["home"], float), ref_home):
                continue
            d1 = tree.query(p["V"] @ M.T)[0].max()
            d2 = cKDTree(p["V"] @ M.T).query(ref["V"])[0].max()
            d = float(max(d1, d2))
            best = d if best is None else min(best, d)
            n_ok += d < 1e-3
        rows.append({"home": p["home"], "n_vertices": int(len(p["V"])), "best_max_vertex_mismatch_mm": best,
                     "maps_matching_within_1um": int(n_ok)})
    res[kind] = rows
    print(kind, "pieces", len(rows), "worst best-mismatch (mm)", max(r["best_max_vertex_mismatch_mm"] for r in rows),
          "matching maps per piece (stabiliser size if all match)", sorted({r["maps_matching_within_1um"] for r in rows}))
# cube size and pitch from the CAD, against the simulation's
pos = json.loads((HERE / "positions.json").read_text())
e = [p for p in parts if p["home"] == (1, 1, 0)][0]
c = [p for p in parts if p["home"] == (1, 1, 1)][0]
res["cad_edge_bounds_mm"] = [np.round(e["V"].min(0), 3).tolist(), np.round(e["V"].max(0), 3).tolist()]
res["cad_corner_bounds_mm"] = [np.round(c["V"].min(0), 3).tolist(), np.round(c["V"].max(0), 3).tolist()]
res["sim_pitch_mm"] = pos["m1"]["pitch"] * 1e3
res["sim_half_size_mm"] = (pos["m1"]["pitch"] - pos["m1"]["gap"]) * 1e3 / 2
print(json.dumps({k: v for k, v in res.items() if k.startswith(("cad", "sim"))}))
(HERE / "stage0_results.json").write_text(json.dumps(res, indent=1))
