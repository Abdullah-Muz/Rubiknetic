"""Diagnostic: rounded-edge geometry checks (extents, facet angles, home-pose contacts)."""
import sys, os, gzip, json
from pathlib import Path
D = str(Path(__file__).resolve().parent); sys.path.insert(0, D); sys.path.insert(0, str(Path(D).parents[2] / "src"))
import numpy as np, mujoco
import edge_patch
from rubiknetic.cube_physics import m1_model
from scipy.spatial import ConvexHull
orig = m1_model._chamfered_box_vertices
p0 = m1_model.M1Params(gap=5e-05)
h = (p0.pitch - p0.gap) / 2
for R in (None, 1.4, 2.5):
    v = orig(h, p0.chamfer) if R is None else edge_patch.rounded_box_vertices(h, R / 1000)
    hull = ConvexHull(v)
    n = hull.equations[:, :3]
    # angles of hull facets relative to the +z face, among facets adjacent to the top face (normal z>0, not flat)
    tilt = sorted(set(round(float(np.degrees(np.arccos(abs(x[2])))), 1) for x in n if x[2] > 0.01 and abs(x[2]) < 0.9999))
    print("R", R, "verts", len(v), "extent mm", np.round(v.max(axis=0) * 1000, 4), "facet angles vs face (deg):", tilt[:6])
    m1_model._chamfered_box_vertices = (lambda hh, c, R=R: orig(hh, c) if R is None else edge_patch.rounded_box_vertices(hh, R / 1000))
    m = mujoco.MjModel.from_xml_string(m1_model.build_m1_xml(p0)); d = mujoco.MjData(m)
    mujoco.mj_fwdPosition(m, d)
    cub = [i for i in range(d.ncon) if m.geom(d.contact[i].geom1).name.startswith("cubie") and m.geom(d.contact[i].geom2).name.startswith("cubie")]
    print("   home pose: cubie-cubie contacts", len(cub), "min dist mm", round(min([d.contact[i].dist for i in cub], default=0) * 1000, 4))
m1_model._chamfered_box_vertices = orig
