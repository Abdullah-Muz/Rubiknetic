"""Convex-decompose the supplied cube CAD for MuJoCo (D3, unscored prototype).

Runs in a SEPARATE tool venv (not the project's pinned env): cascadio 0.1.1, trimesh 5.2.1,
coacd, python-fcl, networkx. Input and output live in the git-ignored third_party_cad/
directory: the CAD is under GrabCAD terms and must not be committed.

Usage: python -I decompose_cad.py <Assembled_Rubiks_Cube.glb> <out.json> [threshold]
"""
import json
import sys
import time

import coacd
import numpy as np
import trimesh

glb, out = sys.argv[1], sys.argv[2]
thr = float(sys.argv[3]) if len(sys.argv) > 3 else 0.03
REF = {"core": 3296e-9, "centre": 742e-9, "edge": 5434e-9, "corner": 6823e-9}  # m^3
sc = trimesh.load(glb)
inst, rep = [], {}
for node in sc.graph.nodes_geometry:
    T, g = sc.graph[node]
    local = sc.geometry[g].copy()
    local.merge_vertices(merge_tex=True, merge_norm=True, digits_vertex=7)
    world = local.copy()
    world.apply_transform(T)
    v = abs(world.volume)
    kind = min(REF, key=lambda k: abs(REF[k] - v))
    if abs(REF[kind] - v) > 0.05 * REF[kind]:
        continue  # stickers
    c = (world.bounds[0] + world.bounds[1]) / 2
    home = [int(np.sign(x)) if abs(x) > 0.008 else 0 for x in c]
    key = np.round(np.sort(local.vertices, axis=0), 7)
    if kind in rep:
        same = rep[kind]["key"].shape == key.shape and np.allclose(rep[kind]["key"], key, atol=1e-6)
    else:
        rep[kind] = {"mesh": local, "key": key}
        same = True
    inst.append({"kind": kind, "home": home, "T": np.asarray(T).tolist(), "same_local_geometry": bool(same)})
print({k: sum(i["kind"] == k for i in inst) for k in REF}, "all same local geometry:",
      all(i["same_local_geometry"] for i in inst))

hulls = {}
for kind, r in rep.items():
    m = r["mesh"]
    t0 = time.time()
    parts = coacd.run_coacd(coacd.Mesh(m.vertices, m.faces), threshold=thr, preprocess_mode="auto",
                            max_convex_hull=-1, seed=0)
    hulls[kind] = [{"v": np.asarray(v).tolist(), "f": np.asarray(f).tolist()} for v, f in parts]
    hv = sum(trimesh.Trimesh(v, f).convex_hull.volume for v, f in parts)
    print(f"{kind}: {len(parts)} hulls, hull volume / part volume = {hv / abs(m.volume):.3f}, {time.time() - t0:.0f}s")
json.dump({"source": "GrabCAD 'Rotatable Rubik's Cube 3 x 3 x 3' (user-supplied; not redistributable)",
           "units": "m", "coacd_threshold": thr, "instances": inst, "hulls": hulls}, open(out, "w"))
