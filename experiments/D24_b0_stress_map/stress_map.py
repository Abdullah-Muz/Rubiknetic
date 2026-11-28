"""D24: B0 stress map (UNSCORED; G3 step 2 per P-146 D1; pilot seeds 29700-29779).

B0 is G2's frozen classical controller, unchanged. Each trial runs "U U' U2" from a G2-style start with ONE stress
factor changed. G2's runner, trial code and checks are used read-only (`experiments/E8_scored_g2/run.py`,
`trials.py`); nothing frozen is edited. The records keep G2's full pass/fail; `analyze.py` also separates the turn
outcome from G2's start-sequence limits (e.g. the 3 mm t0 offset), which a deliberate offset is expected to trip.

Factors (one at a time; everything else as G2):
  offset    extra cube offset of r mm in a seeded random direction, r in {1, 2, 3, 4, 5}       (5 x 4 seeds)
  misalign  every face's start misalignment drawn uniformly in +-m deg, m in {2, 3, 4, 5}      (4 x 4 seeds)
  mu        fingertip friction (both arms) in {0.4, 0.5, 0.6, 1.0}                               (4 x 3 seeds)
  grip      grip force (both arms) in {10, 15, 30, 50} N                                          (4 x 3 seeds)
  depth     turner insertion depth error in {-3, -1.5, +1.5, +3} mm (G2: 14 mm)                  (4 x 3 seeds)
  base      G2's own start draw                                                                    (8 seeds)

Usage (WSL, repo root): ~/.venvs/rubiknetic/bin/python experiments/D24_b0_stress_map/stress_map.py \
    --out /home/fwdev/g3stress [--jobs 8] [--dry-run]     (resume: the same command)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
E8 = HERE.parents[0] / "E8_scored_g2"
sys.path.insert(0, str(E8))
import run as R  # noqa: E402  (G2's runner, read-only)

SEED0 = 29700
MOVES = "U U' U2"


def _unit(seed: int) -> list[float]:
    v = np.random.default_rng(seed + 700_000).normal(size=3)
    return (v / np.linalg.norm(v)).tolist()


def build_jobs() -> list[dict]:
    J, s = [], SEED0

    def add(exp, tid, ov):
        nonlocal s
        J.append(R.job(exp, f"{tid}_s{s}", "seq", {"seed": s, "moves": MOVES, "overrides": ov}))
        s += 1
    for _ in range(8):
        add("S-base", "base", {})
    for r_mm in (1, 2, 3, 4, 5):
        for _ in range(4):
            u = _unit(s)
            add("S-offset", f"off{r_mm}mm", {"extra_offset_m": [r_mm * 1e-3 * x for x in u]})
    for m in (2, 3, 4, 5):
        for _ in range(4):
            rng = np.random.default_rng(s + 800_000)
            add("S-misalign", f"mis{m}deg", {"misalign_override": {f: float(rng.uniform(-m, m))
                                                                    for f in ("U", "D", "F", "B", "L", "R")}})
    for mu in (0.4, 0.5, 0.6, 1.0):
        for _ in range(3):
            add("S-mu", f"mu{mu:g}", {"pad_mu": mu})
    for g in (10.0, 15.0, 30.0, 50.0):
        for _ in range(3):
            add("S-grip", f"grip{g:g}", {"grip": g})
    for dz in (-3.0, -1.5, 1.5, 3.0):
        for _ in range(3):
            add("S-depth", f"depth{dz:+g}mm", {"insertion_u": 0.014 + dz * 1e-3})
    assert len({R.key_of(j) for j in J}) == len(J) and all(29700 <= j["kw"]["seed"] <= 29799 for j in J)
    return J


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    jobs = build_jobs()
    if a.dry_run:
        by = {}
        for j in jobs:
            by[j["exp"]] = by.get(j["exp"], 0) + 1
        print(by, len(jobs), "trials; seeds", jobs[0]["kw"]["seed"], "-", jobs[-1]["kw"]["seed"])
        return
    out = a.out.resolve() / "results"
    if out == R.OUT.resolve() or out.is_relative_to(R.OUT.resolve()):
        raise SystemExit("refusing: would write into the G2 scored folder")
    head = R._git("rev-parse", "HEAD")
    for j in jobs:
        j["smoke"], j["scored"] = True, False
    t0 = time.perf_counter()
    try:
        n = R.execute(out, jobs, head + "+D24", R.environment(), head, a.jobs, log=lambda s: print(s, flush=True),
                      arts=R.artifacts())
    except R.Interrupted as e:
        print(f"INTERRUPTED after {time.perf_counter() - t0:.0f} s: {e}. Resume with the same command.", flush=True)
        sys.exit(3)
    print(f"complete: {n} records written this start in {time.perf_counter() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
