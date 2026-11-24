"""P-79 R0 check: do the piece magnets of each arm (L0, PG8, PG20) still fit inside the piece with rounded edges?

For each magnet on a cubie body: a cylinder (its type's diameter and length) centred at its body-frame position along its
direction. It fits if every sampled point of the cylinder (both end discs and the side) lies at least `wall` (0.4 mm, the
magnets' MagnetParams.wall) inside the piece solid: the convex hull of the piece vertices, centred at the piece's home
position (pieces are bodies at the core origin; geom offset = home * pitch). Core magnets are skipped (the core is not
reshaped). Reported for the original chamfer and for rounded R 1.4 / 2.5 mm. Writes r0_magnet_fit.json next to this file.
The layout is read from the live magnet system after one E1-2 trial per arm through the committed Stage 3b worker."""
import json, sys, importlib.util
import multiprocessing as mp
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
EXP = HERE.parent / "D14_noslip_rest_rehearsal"
sys.path.insert(0, str(EXP)); sys.path.insert(0, str(HERE.parents[1] / "src"))
GEOMS = {"chamfer": ("chamfer", 0.0), "R1.4": ("rounded", 0.0014), "R2.5": ("rounded", 0.0025)}


def load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


def layout(arm):
    S3 = load("d14s3_run", EXP / "d14s3_run.py")
    env = S3.D13.environment()
    job = [j for j in S3.check_jobs(env, S3.NOSLIP) if j["er9g_arm"] == arm][0]
    S3.worker(job)
    _, _, M4, _ = S3.RUN2.er9().mods()
    ms = M4._MS
    out = []
    for g in ms.mags:
        t = g.get("mp", ms.mp)
        out.append({"body": g["body"], "pos": [float(x) for x in g["pos"]], "dir": [float(x) for x in g["dir"]],
                    "diameter": float(t.diameter), "length": float(t.length), "wall": float(t.wall)})
    return arm, out


def cylinder_points(c, u, dia, length, n=48):
    u = np.asarray(u, float) / np.linalg.norm(u)
    a = np.cross(u, [1.0, 0, 0]) if abs(u[0]) < 0.9 else np.cross(u, [0, 1.0, 0])
    a /= np.linalg.norm(a); b = np.cross(u, a)
    pts = []
    for z in np.linspace(-length / 2, length / 2, 5):
        for rr in (dia / 2,) if abs(z) < length / 2 else (0.0, dia / 4, dia / 2):
            for k in range(n):
                th = 2 * np.pi * k / n
                pts.append(c + z * u + rr * (np.cos(th) * a + np.sin(th) * b))
    return np.array(pts)


def main():
    from scipy.spatial import ConvexHull
    from rubiknetic.cube_physics.m1_model import M1Params, piece_vertices, cubie_name, HOME_POSITIONS
    home = {cubie_name(h): np.array(h, float) for h in HOME_POSITIONS}
    with mp.get_context("fork").Pool(3, maxtasksperchild=1) as pool:
        lays = dict(pool.map(layout, ["L0", "PG8", "PG20"]))
    res = {"note": "UNSCORED R0 check (P-79)", "geometries": {}, "layouts": {a: len(v) for a, v in lays.items()}}
    for gname, (prof, r) in GEOMS.items():
        p = M1Params(gap=5e-05, radial_preload=0.0, edge_profile=prof, edge_radius=r)
        hull = ConvexHull(piece_vertices(p))
        A, b = hull.equations[:, :3], hull.equations[:, 3]
        per_arm = {}
        for arm, mags in lays.items():
            worst, bad, n = np.inf, [], 0
            for i, g in enumerate(mags):
                if g["body"] not in home or np.count_nonzero(home[g["body"]]) == 0 and g["body"] == "core":
                    continue
                n += 1
                c_local = np.array(g["pos"]) - home[g["body"]] * p.pitch      # piece-centred frame
                pts = cylinder_points(c_local, g["dir"], g["diameter"], g["length"])
                depth = -(pts @ A.T + b).max()                              # min distance inside the hull (m)
                worst = min(worst, depth)
                if depth < g["wall"] - 1e-12:
                    bad.append({"i": i, "body": g["body"], "depth_mm": depth * 1000})
            per_arm[arm] = {"piece_magnets": n, "min_depth_mm": worst * 1000, "wall_mm": mags[0]["wall"] * 1000,
                            "n_violating": len(bad), "violating": bad[:12]}
        res["geometries"][gname] = per_arm
    (HERE / "r0_magnet_fit.json").write_text(json.dumps(res, indent=1))
    for gname, pa in res["geometries"].items():
        print(gname, {a: (v["piece_magnets"], round(v["min_depth_mm"], 3), v["n_violating"]) for a, v in pa.items()})


if __name__ == "__main__":
    main()
