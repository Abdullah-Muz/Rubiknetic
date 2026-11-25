"""D15 R3 static pre-checks (proposal §3.1; P-84 D1): for L0, do the piece magnets still fit (0.4 mm wall) and do the
composite checks V4 / V5 / V6 pass at the two new edge radii of the E1-7 band, R 1.8 and 3.6 mm? Same code as R0
(r0_magnet_fit.layout / cylinder_points; r0_composite.one), only the radii and the arm differ. R 2.5 mm is
included as a control and must reproduce R0's committed L0 values. Writes r3_static.json next to this file.
UNSCORED; static apart from V5's 0.5 s energy check; no trial records."""
import json
import sys
import importlib.util
import multiprocessing as mp
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
RADII = (0.0018, 0.0025, 0.0036)
ARM = "L0"


def load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


FIT = load("r0_magnet_fit", HERE / "r0_magnet_fit.py")
COMP = load("r0_composite", HERE / "r0_composite.py")


def fit(mags: list, r: float) -> dict:
    from scipy.spatial import ConvexHull
    from rubiknetic.cube_physics.m1_model import M1Params, piece_vertices, cubie_name, HOME_POSITIONS
    home = {cubie_name(h): np.array(h, float) for h in HOME_POSITIONS}
    p = M1Params(gap=5e-05, radial_preload=0.0, edge_profile="rounded", edge_radius=r)
    hull = ConvexHull(piece_vertices(p))
    A, b = hull.equations[:, :3], hull.equations[:, 3]
    worst, bad, n = np.inf, [], 0
    for i, g in enumerate(mags):
        if g["body"] not in home:
            continue
        n += 1
        pts = FIT.cylinder_points(np.array(g["pos"]) - home[g["body"]] * p.pitch, g["dir"], g["diameter"], g["length"])
        depth = -(pts @ A.T + b).max()
        worst = min(worst, depth)
        if depth < g["wall"] - 1e-12:
            bad.append({"i": i, "body": g["body"], "depth_mm": depth * 1000})
    return {"piece_magnets": n, "min_depth_mm": worst * 1000, "wall_mm": mags[0]["wall"] * 1000,
            "n_violating": len(bad), "violating": bad[:12], "fits": not bad}


def main() -> None:
    ctx = mp.get_context("fork")
    with ctx.Pool(1, maxtasksperchild=1) as pool:
        _, mags = pool.apply(FIT.layout, (ARM,))
    fits = {f"R{r * 1000:.1f}": fit(mags, r) for r in RADII}
    with ctx.Pool(len(RADII), maxtasksperchild=1) as pool:
        comp = pool.map(COMP.one, [(ARM, r) for r in RADII])
    r0 = json.loads((HERE / "r0_magnet_fit.json").read_text())["geometries"]["R2.5"][ARM]
    r0c = [x for x in json.loads((HERE / "r0_composite.json").read_text())["results"]
           if x["arm"] == ARM and x["edge_radius"] == 0.0025][0]
    c25 = [x for x in comp if x["edge_radius"] == 0.0025][0]
    control = {"fit_R2.5_equals_R0": fits["R2.5"]["min_depth_mm"] == r0["min_depth_mm"]
               and fits["R2.5"]["n_violating"] == r0["n_violating"],
               "composite_R2.5_equals_R0": all(c25[k] == r0c[k] for k in ("V4", "V5", "V6"))}
    out = {"note": "UNSCORED D15 R3 static pre-check (proposal section 3.1, P-84)", "arm": ARM,
           "control": control, "fit": fits, "composite": comp,
           "runnable": {f"R{r * 1000:.1f}": fits[f"R{r * 1000:.1f}"]["fits"] and c["pass"]
                        for r, c in zip(RADII, comp)}}
    (HERE / "r3_static.json").write_text(json.dumps(out, indent=1, default=float))
    print("control", control)
    for k, v in fits.items():
        print(k, "fit", v["fits"], "min depth mm %.3f" % v["min_depth_mm"], "violations", v["n_violating"])
    for c in comp:
        print("R%.1f" % (c["edge_radius"] * 1000), "composite", c["pass"], {k: c[k]["pass"] for k in ("V4", "V5", "V6")},
              "V5 drift_rel", c["V5"].get("drift_rel"))
    print("runnable", out["runnable"])


if __name__ == "__main__":
    main()
