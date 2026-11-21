"""Stage 5: at the layout's radial depth (inner face at R + wall), wall thickness against off-axis angle for four
magnet sizes, in the reference edge and corner, both azimuth options; and the gap between the 2 (edge) or 3 (corner)
magnets of one piece against the angle. Then the angle range where both hold (wall >= 0.4 mm, mutual gap >= 0.5 mm).
Also, at the layout's own angles: the longest magnet of 4 mm and of 3 mm diameter that keeps a 0.4 mm wall.
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
RR = {k: v * 1e3 for k, v in pos["REAL_RADIUS"].items()}
WALL = pos["mp"]["wall"] * 1e3
SIZES = {"4x3": (2.0, 3.0), "4x2": (2.0, 2.0), "3x3": (1.5, 3.0), "3x2": (1.5, 2.0)}
TUBE = 3.6


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def directions(home, opt):
    h = np.asarray(home, float)
    u = unit(h)
    if opt[1] == 0:
        return [u]
    g = np.radians(opt[1])
    nz = np.nonzero(h)[0]
    if opt[0] == "split":
        if opt[2] == "centre":
            targets = [np.eye(3)[k] * h[k] for k in nz]
        else:
            z = [k for k in range(3) if h[k] == 0][0]
            targets = [unit(h + s * np.eye(3)[z]) for s in (1.0, -1.0)]
    else:
        if opt[2] == "edge":
            targets = [unit(h * (1 - np.eye(3)[k])) for k in range(3)]
        else:
            targets = [np.eye(3)[k] * h[k] for k in range(3)]
    return [unit(np.cos(g) * u + np.sin(g) * unit(t - (t @ u) * u)) for t in targets]


parts = L.load_parts()
by_home = {p["home"]: p for p in parts if p["kind"] in ("edge", "corner")}
res = {"wall_param_mm": WALL, "real_radius_mm": RR, "rows": []}
CASES = [("edge", (1, 1, 0), "split", "centre"), ("edge", (1, 1, 0), "split", "corner"),
         ("corner", (1, 1, 1), "tri", "centre"), ("corner", (1, 1, 1), "tri", "edge")]
samples = {}
for kind, home, mode, tgt in CASES:
    p = by_home[home]
    if home not in samples:
        samples[home] = L.sample_tris_rows(p["V"], p["F"], 0.08)   # the whole piece
    S = samples[home]
    face = RR[kind] + WALL
    for g in np.arange(0, 35.01, 0.5):
        dirs = directions(home, (mode, float(g), tgt))
        row = {"kind": kind, "home": home, "toward": tgt, "gamma_deg": float(g)}
        per_dir = []
        for v in dirs:
            hits = L.ray_hits(p["V"], p["F"], np.zeros(3), v)
            iv = [(hits[i], hits[i + 1]) for i in range(0, len(hits) - 1, 2)]
            t, rho = L.cyl_coords(S, np.zeros(3), v)
            m = (rho < TUBE) & (t > 15) & (t < 34)
            per_dir.append((iv, t[m], rho[m]))
        for sname, (a, Lm) in SIZES.items():
            walls = []
            for iv, t, rho in per_dir:
                c = face + Lm / 2
                if not any(lo < c < hi for lo, hi in iv):
                    walls.append(None)
                else:
                    walls.append(min(TUBE - a, float(L.cyl_sdf(t - c, rho, a, Lm / 2).min())) if len(t) else TUBE - a)
            w = None if any(x is None for x in walls) else min(walls)
            gap = None
            if len(dirs) > 1:
                cs = [v * (face + Lm / 2) for v in dirs]
                gap = min(L.cyl_cyl_gap(cs[i], dirs[i], a, Lm / 2, cs[j], dirs[j], a, Lm / 2, h=0.1)
                          for i in range(len(dirs)) for j in range(i + 1, len(dirs)))
            row[sname] = {"wall_mm": None if w is None else round(w, 3), "mutual_gap_mm": None if gap is None else round(gap, 3)}
        res["rows"].append(row)
    print(kind, home, tgt, "done", round(time.time() - t0, 1), "s", flush=True)

# feasible ranges
summary = {}
for kind, home, mode, tgt in CASES:
    R = [r for r in res["rows"] if r["kind"] == kind and r["toward"] == tgt]
    for sname in SIZES:
        def rng(pred):
            gs = [r["gamma_deg"] for r in R if pred(r[sname])]
            if not gs:
                return None
            segs = [[gs[0], gs[0]]]
            for g in gs[1:]:
                if g - segs[-1][1] <= 0.5 + 1e-9:
                    segs[-1][1] = g
                else:
                    segs.append([g, g])
            return segs
        summary[f"{kind} toward {tgt} {sname}"] = {
            "gamma_wall>=0.4": rng(lambda d: d["wall_mm"] is not None and d["wall_mm"] >= 0.4 - 0.005),
            "gamma_wall>=0.2": rng(lambda d: d["wall_mm"] is not None and d["wall_mm"] >= 0.2),
            "gamma_wall>0": rng(lambda d: d["wall_mm"] is not None and d["wall_mm"] > 0),
            "gamma_mutual_gap>=0.5": rng(lambda d: d["mutual_gap_mm"] is not None and d["mutual_gap_mm"] >= 0.5),
            "gamma_both(wall>=0.4,gap>=0.5)": rng(lambda d: d["wall_mm"] is not None and d["wall_mm"] >= 0.4 - 0.005 and d["mutual_gap_mm"] is not None and d["mutual_gap_mm"] >= 0.5),
            "gamma_both(wall>=0.2,gap>=0.5)": rng(lambda d: d["wall_mm"] is not None and d["wall_mm"] >= 0.2 and d["mutual_gap_mm"] is not None and d["mutual_gap_mm"] >= 0.5),
            "wall_at_layout_angle": next((r[sname]["wall_mm"] for r in R if abs(r["gamma_deg"] - (20 if kind == "edge" else 16)) < 1e-9), None)}
res["summary"] = summary
for k, v in summary.items():
    print(k, json.dumps(v))

# at the layout's own angles: longest magnet (inner face at the layout's radius) keeping a 0.4 mm wall
longest = {}
for kind, home, mode, tgt, g in (("edge", (1, 1, 0), "split", "centre", 20.0), ("corner", (1, 1, 1), "tri", "centre", 16.0),
                                 ("corner", (1, 1, 1), "tri", "edge", 16.0)):
    p, S = by_home[home], samples[home]
    face = RR[kind] + WALL
    v = directions(home, (mode, g, tgt))[0]
    hits = L.ray_hits(p["V"], p["F"], np.zeros(3), v)
    iv = [(hits[i], hits[i + 1]) for i in range(0, len(hits) - 1, 2)]
    t, rho = L.cyl_coords(S, np.zeros(3), v)
    m = (rho < TUBE) & (t > 15) & (t < 34)
    t, rho = t[m], rho[m]
    for dia in (4.0, 3.0):
        best = 0.0
        for Lm in np.arange(0.5, 6.01, 0.05):
            c = face + Lm / 2
            if any(lo < c < hi for lo, hi in iv) and L.cyl_sdf(t - c, rho, dia / 2, Lm / 2).min() >= 0.4 - 0.005:
                best = float(Lm)
            else:
                break
        longest[f"{kind} toward {tgt} at {g:g} deg, diameter {dia:g}"] = round(best, 2)
res["longest_magnet_with_0.4_wall_at_layout_angle_mm"] = longest
print(json.dumps(longest, indent=1))
(HERE / "stage5_results.json").write_text(json.dumps(res, indent=1))
print("done", round(time.time() - t0, 1), "s")
