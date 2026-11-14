"""Measure the real mechanism's layout from the reference CAD (dimensions only; D5 design input).

For each piece type in the assembly frame: occupancy in (r, angle-from-own-axis) bands, and which
neighbour each piece's inner regions sit under (radially overlapping pairs = bearing interfaces).
Runs in the CAD tool venv. Prints numbers only; no CAD geometry is written out.
"""
import sys

import numpy as np
import trimesh

sc = trimesh.load(sys.argv[1])
REF = {"core": 3296e-9, "centre": 742e-9, "edge": 5434e-9, "corner": 6823e-9}
pieces = []
for node in sc.graph.nodes_geometry:
    T, g = sc.graph[node]
    m = sc.geometry[g].copy()
    m.apply_transform(T)
    m.apply_scale(1000)
    v = abs(m.volume) / 1e9
    k = min(REF, key=lambda kk: abs(REF[kk] - v))
    if abs(REF[k] - v) > 0.05 * REF[k]:
        continue
    c = (m.bounds[0] + m.bounds[1]) / 2
    home = np.array([int(np.sign(x)) if abs(x) > 8 else 0 for x in c])
    pieces.append((k, home, m))


def bands(kind):
    k, home, m = next(p for p in pieces if p[0] == kind)
    u = home / np.linalg.norm(home)
    pts = m.sample(200000, seed=1)
    pts = np.vstack([pts, trimesh.sample.volume_mesh(m, 200000)]) if m.is_watertight else pts
    r = np.linalg.norm(pts, axis=1)
    ang = np.degrees(np.arccos(np.clip(pts @ u / r, -1, 1)))
    print(f"\n== {kind} {home}: r {r.min():.2f}..{r.max():.2f} mm")
    for lo in np.arange(np.floor(r.min()), np.ceil(r.max()), 1.0):
        sel = (r >= lo) & (r < lo + 1)
        if sel.sum() > 50:
            print(f"   r {lo:4.0f}-{lo + 1:<3.0f}: angle from own axis {ang[sel].min():5.1f}..{ang[sel].max():5.1f} deg  (n={sel.sum()})")


for kind in ("centre", "edge", "corner", "core"):
    bands(kind)

# radial-overlap partners: for sample directions, which pieces occupy which radius ranges along that ray
print("\n== stacking along sample rays (piece: r-interval mm)")
rays = {"centre axis +z": [0, 0, 1], "27deg from z toward edge (1,0,1)": None, "edge dir (1,1,0)": [1, 1, 0],
        "17deg from edge (1,1,0) toward corner": None, "corner dir (1,1,1)": [1, 1, 1],
        "20deg from corner toward edge (1,1,0)": None}


def slerp(a, b, deg):
    a, b = np.array(a, float) / np.linalg.norm(a), np.array(b, float) / np.linalg.norm(b)
    om = np.arccos(a @ b)
    t = np.radians(deg) / om
    return (np.sin((1 - t) * om) * a + np.sin(t * om) * b) / np.sin(om)


rays["27deg from z toward edge (1,0,1)"] = slerp([0, 0, 1], [1, 0, 1], 27)
rays["17deg from edge (1,1,0) toward corner"] = slerp([1, 1, 0], [1, 1, 1], 17)
rays["20deg from corner toward edge (1,1,0)"] = slerp([1, 1, 1], [1, 1, 0], 20)
for name, d in rays.items():
    d = np.array(d, float) / np.linalg.norm(d)
    hits = []
    for k, home, m in pieces:
        loc, _, _ = m.ray.intersects_location([np.zeros(3)], [d])
        if len(loc):
            rr = np.sort(np.linalg.norm(loc, axis=1))
            hits.append((rr[0], f"{k}{tuple(home)}: " + ", ".join(f"{x:.2f}" for x in rr)))
    print(f"  {name}:")
    for _, h in sorted(hits):
        print("     ", h)
