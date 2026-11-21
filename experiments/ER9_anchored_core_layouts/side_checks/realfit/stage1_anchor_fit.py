"""Stage 1: tool self-test, frame and identity checks, and the fit of every anchor piece magnet (4 x 3 mm at the
layout's position and direction) in its real CAD piece. Numbers only; no geometry is written."""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

import fitlib as L  # noqa: E402

t0 = time.time()
res = {}

# ---------------------------------------------------------------- self-test of the tools on a known solid
box = trimesh.creation.box(extents=[10, 10, 10])
Vb, Fb = np.asarray(box.vertices, float), np.asarray(box.faces, int)
Sb = L.sample_tris(Vb, Fb, 0.05)
v = np.array([0.0, 0.6, 0.8])
c = np.array([1.0, 0.5, -0.5])
r = L.fit_cylinder(Vb, Fb, Sb, c, v, 2.0, 1.5)
# exact wall: support of the cylinder along +x: c.x + a*sqrt(1-vx^2) + hl*|vx| etc.
exact = min(5 - abs(c[k]) - (2.0 * np.sqrt(1 - v[k] ** 2) + 1.5 * abs(v[k])) for k in range(3))
c2 = np.array([3.5, 0.0, 0.0])
r2 = L.fit_cylinder(Vb, Fb, Sb, c2, v, 2.0, 1.5)
exact2 = c2[0] + 2.0 * np.sqrt(1 - v[0] ** 2) + 1.5 * abs(v[0]) - 5
g_par = L.cyl_cyl_gap(np.zeros(3), np.array([0, 0, 1.0]), 2, 1.5, np.array([4.7, 0, 0.0]), np.array([0, 0, 1.0]), 2, 1.5)
g_ax = L.cyl_cyl_gap(np.zeros(3), np.array([0, 0, 1.0]), 2, 1.5, np.array([0, 0, 3.3]), np.array([0, 0, 1.0]), 2, 1.5)
res["selftest"] = {"box_wall_measured": r["wall_mm"], "box_wall_exact": exact,
                   "box_protrusion_measured": r2.get("protrusion_mm"), "box_protrusion_exact": exact2,
                   "box_outside_fraction": r2.get("outside_fraction"),
                   "cyl_gap_parallel_measured": g_par, "cyl_gap_parallel_exact": 0.7,
                   "cyl_gap_coaxial_measured": g_ax, "cyl_gap_coaxial_exact": 0.3}
print("selftest", json.dumps(res["selftest"]))

# ---------------------------------------------------------------- CAD parts, frame and identity
parts = L.load_parts()
print("loaded", len(parts), "parts", round(time.time() - t0, 1), "s")
by_home = {}
frame = []
for p in parts:
    V, F = p["V"], p["F"]
    e = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    ue, cnt = np.unique(e, axis=0, return_counts=True)
    bad = ue[cnt != 2]
    blen = np.linalg.norm(V[bad[:, 0]] - V[bad[:, 1]], axis=1) if len(bad) else np.zeros(0)
    brad = np.linalg.norm((V[bad[:, 0]] + V[bad[:, 1]]) / 2, axis=1) if len(bad) else np.zeros(0)
    Sn = L.sample_tris(V, F, 0.1, centre=np.zeros(3), radius=23.5)
    row = {"name": p["name"], "kind": p["kind"], "home": p["home"],
           "bounds_min": np.round(V.min(0), 3).tolist(), "bounds_max": np.round(V.max(0), 3).tolist(),
           "closest_to_origin_mm": float(np.linalg.norm(Sn, axis=1).min()) if len(Sn) else None,
           "edges_not_shared_by_2_faces": int(len(bad)), "open_edge_total_len_mm": float(blen.sum()),
           "open_edge_max_len_mm": float(blen.max()) if len(bad) else 0.0,
           "open_edge_radius_range_mm": [float(brad.min()), float(brad.max())] if len(bad) else None}
    frame.append(row)
    if p["kind"] in ("edge", "corner", "centre"):
        assert p["home"] not in by_home, p["home"]
        by_home[p["home"]] = p
res["frame"] = frame
for k in ("edge", "corner", "centre", "core"):
    R = [r for r in frame if r["kind"] == k]
    print(f"{k}: n={len(R)} closest_to_origin min/max "
          f"{min(r['closest_to_origin_mm'] for r in R):.3f}/{max(r['closest_to_origin_mm'] for r in R):.3f} "
          f"open edges {sorted({r['edges_not_shared_by_2_faces'] for r in R})} "
          f"open len total {max(r['open_edge_total_len_mm'] for r in R):.2f} max single "
          f"{max(r['open_edge_max_len_mm'] for r in R):.3f} radius range {R[0]['open_edge_radius_range_mm']}")
assert sum(1 for h in by_home if np.count_nonzero(h) == 2) == 12
assert sum(1 for h in by_home if np.count_nonzero(h) == 3) == 8
assert sum(1 for h in by_home if np.count_nonzero(h) == 1) == 6

# symmetry check: every edge (corner) is the image of the first one under a signed axis permutation of the frame
def canon(p):
    """Sorted radii and absolute sorted coordinates of the vertices: invariant under signed axis permutations."""
    A = np.sort(np.abs(p["V"]), axis=1)
    A = A[np.lexsort(A.T[::-1])]
    return A


sym = {}
for kind in ("edge", "corner"):
    ps = [p for p in parts if p["kind"] == kind]
    ref = canon(ps[0])
    dev = []
    for p in ps[1:]:
        A = canon(p)
        dev.append(float(np.abs(A - ref).max()) if A.shape == ref.shape else None)
    sym[kind] = dev
res["symmetry_max_vertex_deviation_mm"] = sym
print("symmetry deviation (mm) vs first piece:", {k: (max(x for x in v if x is not None), sum(x is None for x in v)) for k, v in sym.items()})

# ---------------------------------------------------------------- anchor magnets
pos = json.loads((HERE / "positions.json").read_text())
mp = pos["mp"]
a, hl = mp["diameter"] * 1e3 / 2, mp["length"] * 1e3 / 2
name2home = lambda b: tuple({"n": -1, "0": 0, "p": 1}[ch] for ch in b.split("_")[1])  # noqa: E731
rows = []
others_cache = {}
for m in pos["anchored_c0.2"]:
    if m["body"] == "core":
        continue
    home = name2home(m["body"])
    p = by_home[home]
    c = np.array(m["pos"]) * 1e3
    v = np.array(m["dir"])
    u = np.array(home, float) / np.linalg.norm(home)
    S = L.sample_tris(p["V"], p["F"], 0.05, centre=c, radius=6.0)
    fit = L.fit_cylinder(p["V"], p["F"], S, c, v, a, hl)
    hits = L.ray_hits(p["V"], p["F"], np.zeros(3), v)
    hits_axis = L.ray_hits(p["V"], p["F"], np.zeros(3), u)
    # which other parts does the cylinder reach into?
    Pv = np.concatenate([L.cyl_volume_points(c, v, a, hl, 0.25), L.cyl_surface_points(c, v, a, hl, 0.2)])
    other = {}
    for q in parts:
        if q is p or q["kind"] == "core":
            continue
        if np.any(Pv.max(0) < q["V"].min(0)) or np.any(Pv.min(0) > q["V"].max(0)):
            continue
        ins, _ = L.inside(q["V"], q["F"], Pv, ndir=5)
        if ins.any():
            other[q["name"] + str(q["home"])] = float(ins.mean())
    row = {"body": m["body"], "kind": m["kind"], "home": home, "cad_part": p["name"],
           "off_axis_deg": float(np.degrees(np.arccos(np.clip(v @ u, -1, 1)))),
           "centre_radius_mm": float(np.linalg.norm(c)), "dir": [round(float(x), 5) for x in v],
           "piece_material_along_pair_axis_mm": [round(x, 3) for x in hits],
           "piece_material_along_piece_axis_mm": [round(x, 3) for x in hits_axis],
           "n_local_samples": int(len(S)), "share_of_cylinder_inside_other_parts": other, **fit}
    rows.append(row)
    print(row["body"], row["kind"], f"off {row['off_axis_deg']:.2f}", "inside" if fit["fully_inside"] else "NOT inside",
          {k: (round(x, 3) if isinstance(x, float) else x) for k, x in fit.items()}, "axis hits", row["piece_material_along_pair_axis_mm"],
          "others", {k: round(x, 3) for k, x in other.items()}, flush=True)
res["anchor_piece_magnets_4x3"] = rows
(HERE / "stage1_results.json").write_text(json.dumps(res, indent=1))
print("done", round(time.time() - t0, 1), "s")
