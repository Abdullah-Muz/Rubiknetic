"""Stage 3: (a) the largest cylinder that fits at each anchor pair's position and direction; (b) a sweep of the
off-axis angle and of the radial depth, for 4 x 3 mm and 3 x 2 mm magnets, in a representative edge and corner and
one other piece of each type. Numbers only."""
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
SIZES = {"4x3": (2.0, 3.0), "3x2": (1.5, 2.0)}
H = 0.08


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def toward(u, target):
    return unit(target - (target @ u) * u)


def directions(home, opt):
    """Same construction as er9_layout.pair_directions (checked below against the dumped positions)."""
    h = np.asarray(home, float)
    u = unit(h)
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
    return [unit(np.cos(g) * u + np.sin(g) * toward(u, t)) for t in targets]


# check the re-implementation against the dumped layout
name2home = lambda b: tuple({"n": -1, "0": 0, "p": 1}[ch] for ch in b.split("_")[1])  # noqa: E731
dumped = {}
for m in pos["anchored_c0.2"]:
    if m["body"] != "core":
        dumped.setdefault(name2home(m["body"]), []).append(np.array(m["dir"]))
worst = 0.0
for home, ds in dumped.items():
    opt = ("split", 20, "centre") if np.count_nonzero(home) == 2 else ("tri", 16, "centre")
    mine = directions(home, opt)
    for d in ds:
        worst = max(worst, min(float(np.linalg.norm(d - x)) for x in mine))
assert worst < 1e-12, worst
print("direction re-implementation matches the dumped layout, max difference", worst)

parts = L.load_parts()
by_home = {p["home"]: p for p in parts if p["kind"] in ("edge", "corner")}
res = {"sample_spacing_mm": H, "wall_param_mm": WALL, "real_radius_mm": RR}


def intervals(hits):
    return [(hits[i], hits[i + 1]) for i in range(0, len(hits) - 1, 2)]


def in_material(iv, t):
    return any(lo < t < hi for lo, hi in iv)


TUBE = 3.6


def axis_data(p, S, v, tube=TUBE, t_lo=14.0, t_hi=40.0):
    """Material intervals along the radial line v, and the surface samples within `tube` of that line."""
    hits = L.ray_hits(p["V"], p["F"], np.zeros(3), v)
    t, rho = L.cyl_coords(S, np.zeros(3), v)
    m = (rho < tube) & (t > t_lo) & (t < t_hi)
    return hits, t[m], rho[m]


def wall_at(t, rho, iv, face, a, Lm):
    """Wall of the cylinder (radius a, length Lm, inner face at radius `face` on the line): smallest distance from
    the surface to the cylinder, or a negative number if the surface cuts it, or None if its centre is in air."""
    if not in_material(iv, face + Lm / 2):
        return None
    if not len(t):
        return TUBE - a
    return min(TUBE - a, float(L.cyl_sdf(t - (face + Lm / 2), rho, a, Lm / 2).min()))   # walls above TUBE - a are not resolved


def max_radius(t, rho, iv, face, Lm, w):
    if not (in_material(iv, face + 1e-3) and in_material(iv, face + Lm - 1e-3) and in_material(iv, face + Lm / 2)):
        return None
    dz = np.maximum(np.maximum(face - t, t - face - Lm), 0.0)
    m = dz < w if w > 0 else dz <= 0
    if not m.any():
        return 9.9
    return float((rho[m] - np.sqrt(np.maximum(w * w - dz[m] ** 2, 0.0))).min())


# ---------------------------------------------------------------- (a) largest cylinder at the layout's pairs, all pieces
largest = []
samples = {}
SWEEP_PIECES = {"edge": [(1, 1, 0), (0, -1, 1)], "corner": [(1, 1, 1), (-1, 1, -1)]}
for home, p in by_home.items():
    if home not in SWEEP_PIECES["edge"] + SWEEP_PIECES["corner"]:
        continue                                         # stage 1 already shows all pieces of a type measure alike
    kind = "edge" if np.count_nonzero(home) == 2 else "corner"
    S = L.sample_tris_rows(p["V"], p["F"], H)                # the whole piece (run 1 sampled only a 13 mm ball: incomplete beyond about 20 deg)
    samples[home] = S
    opt = ("split", 20, "centre") if kind == "edge" else ("tri", 16, "centre")
    for v in directions(home, opt):
        hits, t, rho = axis_data(p, S, v, tube=6.0)
        iv = intervals(hits)
        face = RR[kind] + WALL
        row = {"home": home, "kind": kind, "cad_part": p["name"], "material_intervals_along_pair_axis_mm": [[round(a_, 3), round(b_, 3)] for a_, b_ in iv],
               "layout_inner_face_radius_mm": face}
        for Lm in (1.0, 1.5, 2.0, 3.0):
            for w in (0.0, 0.4):
                r = max_radius(t, rho, iv, face, Lm, w)
                row[f"max_diameter_len{Lm:g}_wall{w:g}_innerface_at_layout_mm"] = None if r is None else round(2 * r, 3)
        # same centre, same 4:3 proportions: largest scale that stays inside (wall 0 and wall 0.4)
        c = face + 1.5
        if in_material(iv, c):
            tt = np.abs(t - c)
            row["max_scale_same_centre_wall0"] = round(float(np.maximum(rho / 2.0, tt / 1.5).min()), 3)
            lo, hi = 0.0, 3.0
            for _ in range(40):
                mid = (lo + hi) / 2
                if mid > 0 and L.cyl_sdf(t - c, rho, 2.0 * mid, 1.5 * mid).min() >= 0.4:
                    lo = mid
                else:
                    hi = mid
            row["max_scale_same_centre_wall0.4"] = round(lo, 3)
        else:
            row["max_scale_same_centre_wall0"] = None
        largest.append(row)
res["largest_cylinder_at_layout_pairs"] = largest
for kind in ("edge", "corner"):
    R = [r for r in largest if r["kind"] == kind]
    print(f"== largest cylinder, {kind} pairs (n={len(R)})")
    for key in [k for k in R[0] if k.startswith("max_")]:
        vals = [r[key] for r in R]
        nn = [x for x in vals if x is not None]
        print(f"   {key:52s} min {min(nn) if nn else None} max {max(nn) if nn else None} none {len(vals) - len(nn)}")
    print("   intervals example", R[0]["material_intervals_along_pair_axis_mm"], "all equal within 0.01:",
          all(np.allclose(np.ravel(r["material_intervals_along_pair_axis_mm"]), np.ravel(R[0]["material_intervals_along_pair_axis_mm"]), atol=0.01)
              if np.shape(r["material_intervals_along_pair_axis_mm"]) == np.shape(R[0]["material_intervals_along_pair_axis_mm"]) else False for r in R))
print("part (a)", round(time.time() - t0, 1), "s", flush=True)

# ---------------------------------------------------------------- (b) angle and depth sweep
SWEEP_PIECES = {"edge": [(1, 1, 0), (0, -1, 1)], "corner": [(1, 1, 1), (-1, 1, -1)]}
AZ = {"edge": [("split", "centre"), ("split", "corner")], "corner": [("tri", "centre"), ("tri", "edge")]}
FACES = np.arange(21.5, 30.0001, 0.1)
sweep = []
for kind in ("edge", "corner"):
    for home in SWEEP_PIECES[kind]:
        p, S = by_home[home], samples[home]
        gammas = list(range(0, 41)) if home == SWEEP_PIECES[kind][0] else sorted(set(range(0, 41, 4)) | {16, 20})
        for (mode, tgt) in AZ[kind]:
            for g in gammas:
                dirs = directions(home, (mode, g, tgt)) if g > 0 else [unit(home)]
                for idir, v in enumerate(dirs):
                    hits, t, rho = axis_data(p, S, v)
                    iv = intervals(hits)
                    row = {"kind": kind, "home": home, "toward": tgt, "gamma_deg": g, "pair_index": idir,
                           "material_intervals_mm": [[round(a_, 3), round(b_, 3)] for a_, b_ in iv],
                           "odd_hit_count": len(hits) % 2 == 1}
                    for sname, (a, Lm) in SIZES.items():
                        wl = wall_at(t, rho, iv, RR[kind] + WALL, a, Lm)
                        W = np.array([np.nan if (x := wall_at(t, rho, iv, f, a, Lm)) is None else x for f in FACES])
                        ok = ~np.isnan(W)
                        d = {"wall_at_layout_depth_mm": None if wl is None else round(wl, 3)}
                        if ok.any():
                            k = int(np.nanargmax(W))
                            d["best_wall_mm"] = round(float(W[k]), 3)
                            d["best_wall_inner_face_radius_mm"] = round(float(FACES[k]), 2)
                            for thr in (0.4, 0.2, 0.0):
                                idx = np.nonzero(ok & (W >= thr))[0]
                                segs = []
                                for i in idx:                      # contiguous runs of inner-face radii
                                    if segs and i == segs[-1][1] + 1:
                                        segs[-1][1] = i
                                    else:
                                        segs.append([i, i])
                                d[f"inner_face_radius_range_wall>={thr:g}_mm"] = [[round(float(FACES[i0]), 2), round(float(FACES[i1]), 2)] for i0, i1 in segs] or None
                        else:
                            d["best_wall_mm"] = None
                        row[sname] = d
                    sweep.append(row)
            print(kind, home, tgt, "swept", round(time.time() - t0, 1), "s", flush=True)
res["sweep"] = sweep
(HERE / "stage3_results.json").write_text(json.dumps(res, indent=1))

# ---------------------------------------------------------------- printed summary of the sweep
for kind in ("edge", "corner"):
    for home in SWEEP_PIECES[kind]:
        for (mode, tgt) in AZ[kind]:
            print(f"== {kind} {home} toward {tgt}: gamma | first material interval | per size: wall at layout depth, best wall @ inner-face radius, face range wall>=0.4")
            for g in range(0, 41):
                R = [r for r in sweep if r["kind"] == kind and r["home"] == home and r["toward"] == tgt and r["gamma_deg"] == g]
                if not R:
                    continue
                line = f"  {g:2d} | {R[0]['material_intervals_mm'][:2]} |"
                for sname in SIZES:
                    wl = [r[sname]["wall_at_layout_depth_mm"] for r in R]
                    bw = [r[sname].get("best_wall_mm") for r in R]
                    bf = [r[sname].get("best_wall_inner_face_radius_mm") for r in R]
                    rg = [r[sname].get("inner_face_radius_range_wall>=0.4_mm") for r in R]
                    line += f" {sname}: {wl} best {bw} @ {bf} rng {rg} |"
                print(line)
print("done", round(time.time() - t0, 1), "s")
