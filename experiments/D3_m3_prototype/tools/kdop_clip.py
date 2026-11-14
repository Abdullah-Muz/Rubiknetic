"""Trim CoACD hulls to the real geometry they represent (D3 tool; separate CAD venv).

For each hull H of a part, take the dense surface samples P of the ORIGINAL part that lie
inside H, and intersect H with the 26-plane k-DOP of P (3 axes, 6 face diagonals, 4 body
diagonals). Since conv(P) is inside both H and the k-DOP, the trimmed hull still covers the
real geometry it was built from, but no longer bulges past it in those 13 directions,
for example across the planar cuts between layers.

Usage: python -I kdop_clip.py <Assembled_Rubiks_Cube.glb> <in_hulls.json> <out_hulls.json>
"""
import json
import sys

import numpy as np
import trimesh
from scipy.spatial import ConvexHull, HalfspaceIntersection

glb, src, dst = sys.argv[1:4]
REF = {"core": 3296e-9, "centre": 742e-9, "edge": 5434e-9, "corner": 6823e-9}
sc = trimesh.load(glb)
rep = {}
for node in sc.graph.nodes_geometry:
    T, g = sc.graph[node]
    local = sc.geometry[g].copy()
    local.merge_vertices(merge_tex=True, merge_norm=True, digits_vertex=7)
    w = local.copy()
    w.apply_transform(T)
    k = min(REF, key=lambda kk: abs(REF[kk] - abs(w.volume)))
    if abs(REF[k] - abs(w.volume)) < 0.05 * REF[k] and k not in rep:
        rep[k] = local

dirs = [np.eye(3)[i] for i in range(3)]
dirs += [np.array(v, float) / np.sqrt(2) for v in ((1, 1, 0), (1, -1, 0), (1, 0, 1), (1, 0, -1), (0, 1, 1), (0, 1, -1))]
dirs += [np.array(v, float) / np.sqrt(3) for v in ((1, 1, 1), (1, 1, -1), (1, -1, 1), (-1, 1, 1))]
D = np.array(dirs)

data = json.load(open(src))
for kind, hulls in data["hulls"].items():
    mesh = rep[kind]
    pts = np.vstack([mesh.sample(300000, seed=0), mesh.vertices])
    out, vol0, vol1, n_clipped = [], 0.0, 0.0, 0
    for h in hulls:
        v = np.array(h["v"])
        hull = ConvexHull(v)
        vol0 += hull.volume
        inside = np.all(pts @ hull.equations[:, :3].T + hull.equations[:, 3] <= 2e-6, axis=1)
        P = pts[inside]
        if len(P) < 8:
            out.append(h)
            vol1 += hull.volume
            continue
        proj = P @ D.T
        lo, hi = proj.min(0), proj.max(0)
        hs = np.vstack([hull.equations,
                        np.hstack([D, -hi[:, None]]),     # d.x - hi <= 0
                        np.hstack([-D, lo[:, None]])])    # -d.x + lo <= 0
        c = P.mean(0)
        # interior point must be strictly inside every halfspace; nudge toward the hull centroid if needed
        for alpha in (0.0, 0.25, 0.5, 0.75):
            ip = (1 - alpha) * c + alpha * v.mean(0)
            if np.all(hs[:, :3] @ ip + hs[:, 3] < -1e-9):
                break
        else:
            out.append(h)
            vol1 += hull.volume
            continue
        nv = HalfspaceIntersection(hs, ip).intersections
        nh = ConvexHull(nv)
        out.append({"v": nv[nh.vertices].tolist(), "f": nh.simplices.tolist()})
        vol1 += nh.volume
        n_clipped += int(nh.volume < hull.volume * 0.999)
    data["hulls"][kind] = out
    print(f"{kind}: {len(hulls)} hulls, {n_clipped} trimmed, volume {vol1 / vol0:.3f} of before, "
          f"{vol1 / abs(mesh.volume):.3f} of the real part")
data["kdop_clip"] = "26-plane k-DOP of original surface samples inside each hull"
json.dump(data, open(dst, "w"))
