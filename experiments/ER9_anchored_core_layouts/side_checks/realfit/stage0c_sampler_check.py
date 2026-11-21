"""Check of the row sampler used by stages 3, 5 (sample_tris_rows): coverage on a synthetic mesh with thin triangles,
and on one CAD piece against the older grid sampler (two-sided distance between the two point sets). Numbers only."""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

import fitlib as L  # noqa: E402

h = 0.08
cyl = trimesh.creation.cylinder(radius=3.0, height=19.0, sections=96)     # long thin side triangles
V, F = np.asarray(cyl.vertices, float), np.asarray(cyl.faces, int)
S = L.sample_tris_rows(V, F, h)
rnd, _ = trimesh.sample.sample_surface(cyl, 200000, seed=1)
d = cKDTree(S).query(np.asarray(rnd))[0]
print("synthetic cylinder: samples", len(S), "area/h^2", round(cyl.area / h ** 2), "max distance of a random surface point to a sample (mm)",
      round(float(d.max()), 4), "bound 0.71 h =", round(0.71 * h, 4))
t0 = time.time()
parts = L.load_parts()
p = [q for q in parts if q["home"] == (1, 1, 0)][0]
c = np.array([1, 1, 0]) / np.sqrt(2) * 24.0
Sr = L.sample_tris_rows(p["V"], p["F"], h, centre=c, radius=6.0)
So = L.sample_tris(p["V"], p["F"], h, centre=c, radius=6.0)
inner = np.linalg.norm(So - c, axis=1) < 5.8
inner_r = np.linalg.norm(Sr - c, axis=1) < 5.8
print("CAD edge, 6 mm ball: row sampler", len(Sr), "points; grid sampler", len(So), "points;",
      "max distance grid->row", round(float(cKDTree(Sr).query(So[inner])[0].max()), 4),
      "row->grid", round(float(cKDTree(So).query(Sr[inner_r])[0].max()), 4), "mm")
t1 = time.time()
Sw = L.sample_tris_rows(p["V"], p["F"], h)
print("whole edge piece: row sampler", len(Sw), "points in", round(time.time() - t1, 1), "s")
