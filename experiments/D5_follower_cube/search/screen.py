"""Stage 1 of the D5 geometry search (UNSCORED, geometry only): cam-analyser screening.

Samples configurations from the declared grid (seeded), runs cam_analyser.analyse on each, and
records HARD penetration per misalignment, a score, and a support proxy (convex volume of each
piece type relative to the baseline, and pad-geom counts).
Usage: python screen.py <chunk_index> <n_chunks>   (resumable; appends JSON lines)
"""
from __future__ import annotations

import itertools
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import cam_analyser  # noqa: E402
from cube_d5 import D5Params, piece_geometry  # noqa: E402

FIXED = dict(gap=0.05, clearance=0.02, spring_preload=10.0, spring_k=2000.0, slide_range=(-0.001, 0.0003),
             friction=0.2, sphere_spacing_mm=2.0)
BASELINE = dict(bevel_body=1.0, bevel_foot=0.5, bevel_inner=0.0, taper=0.0, taper_start=19.0, pad_spacing_deg=10.0)
SCORE_D = [-3, -2, -1, 1, 2, 3]
OUT = HERE / "results"


def grid() -> list[dict]:
    cfgs = []
    tapers = [(0.0, 19.0)] + [(t, s) for t in (0.1, 0.2, 0.3) for s in (14.0, 17.0, 20.0)]
    for bb, bf, bi, (t, ts), ps in itertools.product((1.0, 1.5, 2.0, 3.0, 4.0), (0.5, 1.0, 1.5), (0.0, 1.0, 2.0),
                                                     tapers, (10.0, 14.0)):
        cfgs.append(dict(bevel_body=bb, bevel_foot=bf, bevel_inner=bi, taper=t, taper_start=ts, pad_spacing_deg=ps))
    random.Random(20261113).shuffle(cfgs)
    return [BASELINE] + cfgs[:179]


def params(cfg: dict, sphere=None) -> D5Params:
    kw = dict(FIXED)
    kw.update({k: v for k, v in cfg.items() if k != "is_baseline"})
    if cfg.get("taper", 0) > 0:
        kw.update(inner_split_centre=26.0, inner_split_edge=24.0)
    if sphere is not None:
        kw["sphere_spacing_mm"] = sphere
    return D5Params(**kw)


def support(p: D5Params) -> dict:
    out = {}
    for kind, h in (("corner", (1, 1, 1)), ("edge", (1, 1, 0)), ("centre", (0, 0, 1))):
        gs = piece_geometry(h, p)
        out[f"{kind}_vol"] = float(sum(ConvexHull(g).volume for g in gs))
        out[f"{kind}_ngeom"] = len(gs)
    return out


def key(cfg: dict) -> str:
    return json.dumps(cfg, sort_keys=True)


def main():
    k, n = int(sys.argv[1]), int(sys.argv[2])
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"stage1_{k}.jsonl"
    done = set()
    if path.exists():
        done = {key(json.loads(l)["cfg"]) for l in path.read_text().splitlines() if l.strip()}
    cam_analyser.DELTAS = [-5, -3, -2, -1, 1, 2, 3, 5]
    cfgs = grid()[k::n]
    for cfg in cfgs:
        if key(cfg) in done:
            continue
        t0 = time.perf_counter()
        p = params(cfg)
        res = cam_analyser.analyse(p)
        hard = {int(dl): float(r["hard"]) for dl, r in res.items()}
        score = sum(hard[d] for d in SCORE_D) + 0.3 * (hard[-5] + hard[5])
        rec = {"cfg": cfg, "hard": hard, "score": score, "support": support(p), "wall_s": time.perf_counter() - t0}
        with path.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"{score:7.3f} {cfg} ({rec['wall_s']:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
