"""Stage 2: magnet-to-magnet gaps (same piece; the 48 core magnets) and the core-side envelope (ball radius needed,
distance to the centre axles), for the anchored layout (clearance 0.2 mm) and the hybrids (1, 2, 3 mm).
Positions are the simulation's (positions.json). The CAD is used only for the spider core's arm radius (a number)."""
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np  # noqa: E402

import fitlib as L  # noqa: E402

t0 = time.time()
pos = json.loads((HERE / "positions.json").read_text())
a, hl = pos["mp"]["diameter"] * 1e3 / 2, pos["mp"]["length"] * 1e3 / 2
res = {"magnet_mm": [2 * a, 2 * hl]}


def gaps(mags, limit=9.0):
    """All pairs with centre distance < limit: (i, j, centre distance, surface gap)."""
    C = np.array([m["pos"] for m in mags]) * 1e3
    D = np.array([m["dir"] for m in mags])
    out = []
    for i in range(len(mags)):
        for j in range(i + 1, len(mags)):
            d = float(np.linalg.norm(C[i] - C[j]))
            if d < limit:
                out.append((i, j, d, L.cyl_cyl_gap(C[i], D[i], a, hl, C[j], D[j], a, hl)))
    return out


for key in ("anchored_c0.2", "hybrid_c1", "hybrid_c2", "hybrid_c3"):
    mags = pos[key]
    r = {}
    # ---- magnets of one piece
    by_body = defaultdict(list)
    for m in mags:
        by_body[m["body"]].append(m)
    per_kind = {}
    for body, ms in by_body.items():
        if body == "core":
            continue
        kind = "edge" if body.count("0") == 1 else "corner"     # cubie_pp0 etc.
        is_anchor = [abs(abs(np.array(m["dir"])).max() - 1.0) > 1e-9 for m in ms]   # M5 magnets are axis-aligned
        for (i, j, d, g) in gaps(ms, limit=1e9):
            lab = "anchor-anchor" if (is_anchor[i] and is_anchor[j]) else "M5-M5" if not (is_anchor[i] or is_anchor[j]) else "anchor-M5"
            per_kind.setdefault(f"{kind} {lab}", []).append((d, g))
    r["same_piece"] = {k: {"n_pairs": len(v), "centre_distance_mm_min_max": [min(x[0] for x in v), max(x[0] for x in v)],
                           "surface_gap_mm_min_max": [min(x[1] for x in v), max(x[1] for x in v)]}
                       for k, v in per_kind.items()}
    # ---- core magnets
    core = by_body["core"]
    G = gaps(core)
    cls = defaultdict(list)
    for (i, j, d, g) in G:
        cls[" / ".join(sorted([core[i]["kind"], core[j]["kind"]]))].append((d, g))
    r["core_pairs_within_9mm"] = {k: {"n_pairs": len(v), "centre_distance_mm_min": min(x[0] for x in v),
                                      "surface_gap_mm_min": min(x[1] for x in v),
                                      "n_gap_below_0.5mm": sum(x[1] < 0.5 for x in v),
                                      "n_overlapping": sum(x[1] <= 0 for x in v)} for k, v in cls.items()}
    r["core_min_gap_mm"] = min(x[3] for x in G) if G else None
    env = {}
    for kind in ("core_edge", "core_corner"):
        ms = [m for m in core if m["kind"] == kind]
        rc = np.array([np.linalg.norm(m["pos"]) * 1e3 for m in ms])
        ax = []
        for m in ms:
            c, v = np.array(m["pos"]) * 1e3, np.array(m["dir"])
            P = L.cyl_surface_points(c, v, a, hl, 0.1)
            ax.append(min(float(np.sqrt((P ** 2).sum(1) - P[:, k] ** 2).min()) for k in range(3)))
        env[kind] = {"n": len(ms), "centre_radius_mm": [float(rc.min()), float(rc.max())],
                     "outer_face_centre_radius_mm": float(rc.max() + hl),
                     "outermost_point_radius_mm": float(np.sqrt((rc.max() + hl) ** 2 + a ** 2)),
                     "innermost_point_radius_mm": float(rc.min() - hl),
                     "min_distance_to_a_centre_axis_mm": [min(ax), max(ax)]}
    r["core_envelope"] = env
    res[key] = r
    print(key, json.dumps(r, indent=1))

# ---- CAD spider core: hub and arm radius (numbers only), as the stand-in for the centre-axle keep-out
parts = L.load_parts()
core = [p for p in parts if p["kind"] == "core"][0]
S = L.sample_tris(core["V"], core["F"], 0.1)
prof = {}
for k in range(3):
    x = np.abs(S[:, k])
    perp = np.sqrt((S ** 2).sum(1) - S[:, k] ** 2)
    m = (x > perp)                                            # points in the double cone about axis k
    for lo in range(8, 28, 2):
        mm = m & (x >= lo) & (x < lo + 2)
        if mm.any():
            prof.setdefault(f"{lo}-{lo + 2}", []).append(float(perp[mm].max()))
res["cad_spider_core"] = {"hub_closest_and_farthest_radius_mm": [float(np.linalg.norm(S, axis=1).min()), float(np.linalg.norm(S, axis=1).max())],
                          "arm_max_perp_radius_by_axial_bin_mm": {k: [round(min(v), 3), round(max(v), 3)] for k, v in prof.items()}}
cen = [p for p in parts if p["kind"] == "centre"]
cr = []
for p in cen:
    Sc = L.sample_tris(p["V"], p["F"], 0.1)
    k = int(np.argmax(np.abs(p["home"])))
    x = np.abs(Sc[:, k]); perp = np.sqrt((Sc ** 2).sum(1) - Sc[:, k] ** 2)
    rr = np.linalg.norm(Sc, axis=1)
    cr.append({"closest_to_origin_mm": float(rr.min()), "inner_end_axial_mm": float(x.min()),
               "max_perp_radius_within_1mm_of_inner_end_mm": float(perp[x < x.min() + 1.0].max()),
               "min_perp_radius_mm": float(perp.min())})
res["cad_centre_pieces"] = cr
print(json.dumps(res["cad_spider_core"], indent=1)); print(json.dumps(cr[:2], indent=1))
(HERE / "stage2_results.json").write_text(json.dumps(res, indent=1))
print("done", round(time.time() - t0, 1), "s")
