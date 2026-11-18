"""ER4: physical-fit measurements for core-to-piece magnets in the GrabCAD real-mechanism cube.
Reads the git-ignored local mesh third_party_cad/Assembled_Rubiks_Cube.glb (licence unconfirmed: the CAD and any
mesh derived from it stay out of the repo; only measured numbers are reported). For every edge and corner, along the
radial line from the cube centre through the piece: where the core material ends, where the piece material begins,
the gap between them, and the room available to embed a cylindrical magnet coaxially in each part (depth along the
line, and the largest coaxial cylinder radius that stays inside the part over that depth).
Usage (WSL):  ~/.venvs/cadtools/bin/python -I experiments/ER4_core_magnet_fit/er4_fit_geometry.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

REPO = Path(__file__).resolve().parents[2]
GLB = REPO / "third_party_cad" / "Assembled_Rubiks_Cube.glb"


def parts():
    s = trimesh.load(GLB)
    out = {}
    for g in s.dump(concatenate=False):
        out.setdefault(g.metadata.get("name", "?"), []).append(g)
    return out


def hits(mesh, u, r_max=0.05):
    """Distances along ray origin->u where the ray crosses mesh, sorted."""
    loc, _, _ = mesh.ray.intersects_location([np.zeros(3)], [u])
    return sorted(set(np.round(np.linalg.norm(loc, axis=1), 7))) if len(loc) else []


def inside_radius(mesh, u, r0, r1, n=9):
    """Largest radius of a cylinder coaxial with u, spanning r0..r1, inside mesh: min over samples of the distance
    from axis points to the mesh surface (points must be inside)."""
    pts = np.outer(np.linspace(r0, r1, n), u)
    sd = trimesh.proximity.signed_distance(mesh, pts)   # positive inside
    return float(sd.min())


def main():
    P = parts()
    core = P["Center Part"][0]
    pieces = [(n, g) for n, gs in P.items() for g in gs if n.startswith(("Edge Square", "Corner Square"))]
    print("core watertight", core.is_watertight, "piece watertight", all(g.is_watertight for _, g in pieces))
    rows = []
    for name, g in pieces:
        c = g.bounds.mean(0)
        kind = "corner" if name.startswith("Corner") else "edge"
        cs = np.sign(np.round(c / 0.019))
        u = cs / np.linalg.norm(cs)
        hc, hp = hits(core, u), hits(g, u)
        core_out = max([h for h in hc if h < (hp[0] if hp else 1)], default=None)
        piece_in = hp[0] if hp else None
        piece_exit = hp[1] if len(hp) > 1 else None
        core_in = max([h for h in hc if core_out is not None and h < core_out], default=0.0) if hc else None
        row = {"piece": name, "kind": kind, "dir": cs.tolist(), "core_hits_mm": [h * 1e3 for h in hc],
               "piece_hits_mm": [h * 1e3 for h in hp],
               "core_outer_mm": None if core_out is None else core_out * 1e3,
               "piece_inner_mm": None if piece_in is None else piece_in * 1e3,
               "gap_mm": None if (core_out is None or piece_in is None) else (piece_in - core_out) * 1e3,
               "piece_depth_mm": None if piece_exit is None else (piece_exit - piece_in) * 1e3,
               "core_depth_mm": None if core_out is None else (core_out - core_in) * 1e3}
        if piece_in is not None and piece_exit is not None:
            for d in (1.0, 2.0, 3.0):
                if (piece_exit - piece_in) * 1e3 >= d:
                    row[f"piece_radius_over_{d:g}mm"] = inside_radius(g, u, piece_in + 1e-5, piece_in + d * 1e-3) * 1e3
        if core_out is not None:
            for d in (1.0, 2.0, 3.0):
                if row["core_depth_mm"] >= d:
                    row[f"core_radius_over_{d:g}mm"] = inside_radius(core, u, core_out - d * 1e-3, core_out - 1e-5) * 1e3
        rows.append(row)
    out = REPO / "experiments" / "ER4_core_magnet_fit" / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "fit_geometry.json").write_text(json.dumps(rows, indent=1))
    for k in ("edge", "corner"):
        R = [r for r in rows if r["kind"] == k]
        f = lambda key: [round(r[key], 2) if r.get(key) is not None else None for r in R]  # noqa: E731
        print(f"== {k} (n={len(R)})")
        for key in ("core_outer_mm", "piece_inner_mm", "gap_mm", "piece_depth_mm", "core_depth_mm",
                    "piece_radius_over_1mm", "piece_radius_over_2mm", "piece_radius_over_3mm",
                    "core_radius_over_1mm", "core_radius_over_2mm", "core_radius_over_3mm"):
            v = [x for x in f(key) if x is not None]
            print(f"  {key:24s} " + (f"min {min(v):.2f} max {max(v):.2f}" if v else "n/a"))
        print("  example hits core", [round(x, 2) for x in R[0]["core_hits_mm"]], "piece", [round(x, 2) for x in R[0]["piece_hits_mm"]])


if __name__ == "__main__":
    main()


# ---- part 2 (ray casting; the meshes are not watertight, so signed distance is not used) ---------------------------
def perp_basis(u):
    a = np.cross(u, [1.0, 0, 0]) if abs(u[0]) < 0.9 else np.cross(u, [0, 1.0, 0])
    a /= np.linalg.norm(a)
    return a, np.cross(u, a)


def inscribed_radius(mesh, point, u, n_dir=36):
    """Smallest distance from point to mesh along n_dir directions perpendicular to u (point assumed inside)."""
    a, b = perp_basis(u)
    dirs = [np.cos(t) * a + np.sin(t) * b for t in np.linspace(0, 2 * np.pi, n_dir, endpoint=False)]
    loc, idx, _ = mesh.ray.intersects_location([point] * n_dir, dirs)
    if not len(loc):
        return float("inf")
    d = np.linalg.norm(loc - point, axis=1)
    best = np.full(n_dir, np.inf)
    for k, ray in enumerate(idx):
        best[ray] = min(best[ray], d[k])
    return float(best.min())


def closest_to_origin(mesh):
    p, dist, _ = trimesh.proximity.closest_point(mesh, [np.zeros(3)])
    return float(dist[0])


def part2():
    P = parts()
    res = {"closest_to_origin_mm": {}, "pieces": []}
    for name, gs in P.items():
        if name.endswith("Surface"):
            continue
        res["closest_to_origin_mm"][name] = min(closest_to_origin(g) for g in gs) * 1e3
    for name, gs in P.items():
        if not name.startswith(("Edge Square", "Corner Square")):
            continue
        for g in gs:
            c = g.bounds.mean(0)
            cs = np.sign(np.round(c / 0.019)); u = cs / np.linalg.norm(cs)
            hp = hits(g, u)
            row = {"piece": name, "kind": "corner" if name.startswith("Corner") else "edge", "piece_inner_mm": hp[0] * 1e3}
            for dmm in (0.5, 1.0, 2.0, 3.0, 4.0):
                row[f"inscribed_radius_at_{dmm:g}mm_mm"] = inscribed_radius(g, u * (hp[0] + dmm * 1e-3), u) * 1e3
            res["pieces"].append(row)
    out = REPO / "experiments" / "ER4_core_magnet_fit" / "results"
    (out / "fit_geometry_part2.json").write_text(json.dumps(res, indent=1))
    print("closest approach to the cube centre (mm):", {k: round(v, 2) for k, v in res["closest_to_origin_mm"].items()})
    for k in ("edge", "corner"):
        R = [r for r in res["pieces"] if r["kind"] == k]
        print(f"== {k}: inner point {min(r['piece_inner_mm'] for r in R):.2f} mm; inscribed radius of a coaxial cylinder at depth:")
        for dmm in (0.5, 1.0, 2.0, 3.0, 4.0):
            v = [r[f"inscribed_radius_at_{dmm:g}mm_mm"] for r in R]
            print(f"   {dmm:g} mm: min {min(v):.2f} max {max(v):.2f} mm")


if __name__ == "__main__" and "--part2" in sys.argv:
    part2()
