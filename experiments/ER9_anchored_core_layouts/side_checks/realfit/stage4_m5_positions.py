"""Stage 4 (hybrid): do M5's 48 corner-edge magnet positions have a counterpart in the real CAD pieces, and do they
clash with the anchor magnets of the same piece? Two mappings are measured:
  A  identity: the simulation's coordinates used directly in the CAD frame (same origin and axes);
  B  face-relative: same place on the piece's corner-edge face (the cubie's face centre), same depth under the CAD
     piece's actual face (wall + L/2), same direction.
Numbers only."""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np  # noqa: E402

import fitlib as L  # noqa: E402

t0 = time.time()
pos = json.loads((HERE / "positions.json").read_text())
a, Lm, wall = pos["mp"]["diameter"] * 1e3 / 2, pos["mp"]["length"] * 1e3, pos["mp"]["wall"] * 1e3
hl = Lm / 2
name2home = lambda b: tuple({"n": -1, "0": 0, "p": 1}[ch] for ch in b.split("_")[1])  # noqa: E731
parts = L.load_parts()
by_home = {p["home"]: p for p in parts if p["kind"] in ("edge", "corner", "centre")}
mags = pos["hybrid_c1"]
is_m5 = [m["body"] != "core" and abs(abs(np.array(m["dir"])).max() - 1.0) < 1e-9 for m in mags]
m5 = [m for m, f in zip(mags, is_m5) if f]
anch = [m for m, f in zip(mags, is_m5) if not f and m["body"] != "core"]
assert len(m5) == 48 and len(anch) == 48
res = {"magnet_mm": [2 * a, Lm], "wall_mm": wall, "sim": pos["m1"]}

# CAD cubie body: the outer cube part of each piece (bounds along the axes where home != 0 end at the cube face)
rows = []
for m in m5:
    home = name2home(m["body"])
    p = by_home[home]
    kind = "edge" if np.count_nonzero(home) == 2 else "corner"
    d = np.array(m["dir"])
    k = int(np.argmax(np.abs(d)))
    n_out = d if kind == "corner" else -d                # outward normal of the face the magnet sits under
    cA = np.array(m["pos"]) * 1e3
    # CAD face: ray from outside the face, through the CAD cubie's face centre, going into the piece
    vmax = np.abs(p["V"]).max(0)                         # cube face coordinate (28.75) on the axes where home != 0
    lat = np.array([0.0 if home[i] == 0 else home[i] * (vmax[i] - 9.5) for i in range(3)])   # CAD cubie centre
    lat[k] = 0.0
    start = lat + n_out * 40.0
    # the piece's material along that line, measured from the cube's mid-plane coordinate
    hits = L.ray_hits(p["V"], p["F"], start, -n_out)
    coord = [float((start - n_out * t)[k]) for t in hits]       # coordinate along axis k of each crossing
    face_k = coord[0] if coord else None                 # first crossing coming from outside = the contact face
    row = {"body": m["body"], "kind": kind, "home": home, "axis": k, "sim_pos_mm": np.round(cA, 3).tolist(),
           "cad_cubie_centre_lateral_mm": np.round(lat, 3).tolist(),
           "cad_crossings_along_magnet_axis_coord_mm": [round(x, 3) for x in coord]}
    S = L.sample_tris(p["V"], p["F"], 0.05, centre=cA, radius=6.5)
    fa = L.fit_cylinder(p["V"], p["F"], S, cA, d, a, hl)
    row["A_identity"] = fa
    if face_k is not None:
        cB = lat.copy()
        cB[k] = face_k
        cB = cB - n_out * (wall + hl)
        fb = L.fit_cylinder(p["V"], p["F"], S, cB, d, a, hl)
        row["B_face_relative"] = {"pos_mm": np.round(cB, 3).tolist(), "shift_from_sim_mm": float(np.linalg.norm(cB - cA)), **fb}
        row["cB"] = cB.tolist()
        # largest cylinder under that face on that axis (inner face of the magnet `wall` under the contact face)
        tS, rhoS = L.cyl_coords(S, cB + n_out * hl, -n_out)      # t = depth under the magnet's front face
        for Lx in (1.0, 2.0, 3.0):
            mm = (tS >= 0) & (tS <= Lx)
            row[f"B_max_diameter_len{Lx:g}_wall0_mm"] = round(2 * float(rhoS[mm].min()), 3) if mm.any() else None
    rows.append(row)
    print(m["body"], kind, "axis", k, "crossings", row["cad_crossings_along_magnet_axis_coord_mm"], "| A:",
          {kk: (round(x, 3) if isinstance(x, float) else x) for kk, x in fa.items()}, "| B:",
          {kk: (round(x, 3) if isinstance(x, float) else x) for kk, x in row.get("B_face_relative", {}).items() if kk != "pos_mm"}, flush=True)

# clash with the anchors of the same piece, both mappings
clash = {}
for mapping in ("A_identity", "B_face_relative"):
    out = {"edge": [], "corner": []}
    for m, r in zip(m5, rows):
        c = np.array(m["pos"]) * 1e3 if mapping == "A_identity" else (np.array(r["cB"]) if "cB" in r else None)
        if c is None:
            continue
        for q in anch:
            if q["body"] != m["body"]:
                continue
            g = L.cyl_cyl_gap(c, np.array(m["dir"]), a, hl, np.array(q["pos"]) * 1e3, np.array(q["dir"]), a, hl)
            out[r["kind"]].append((float(np.linalg.norm(c - np.array(q["pos"]) * 1e3)), g))
    clash[mapping] = {k: {"n_pairs": len(v), "centre_distance_mm_min": min(x[0] for x in v), "surface_gap_mm_min": min(x[1] for x in v),
                          "n_gap_below_0.5mm": sum(x[1] < 0.5 for x in v)} for k, v in out.items() if v}
for r in rows:
    r.pop("cB", None)
res["m5_magnets"] = rows
res["m5_vs_anchor_same_piece"] = clash
print(json.dumps(clash, indent=1))
for kind in ("edge", "corner"):
    R = [r for r in rows if r["kind"] == kind]
    for mp_ in ("A_identity", "B_face_relative"):
        F = [r[mp_] for r in R if mp_ in r]
        ins = [f for f in F if f["fully_inside"]]
        print(f"{kind} {mp_}: n={len(F)} fully inside {len(ins)}",
              "wall min/max", (round(min(f['wall_mm'] for f in ins), 3), round(max(f['wall_mm'] for f in ins), 3)) if ins else None,
              "protrusion max", max((f.get('protrusion_mm') or 0) for f in F), "outside fraction max", max((f.get('outside_fraction') or 0) for f in F))
(HERE / "stage4_results.json").write_text(json.dumps(res, indent=1))
print("done", round(time.time() - t0, 1), "s")
