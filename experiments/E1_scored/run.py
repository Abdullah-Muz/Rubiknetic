"""Scored G1 runner for M1 (experiments/PHASE_1_PREREGISTRATION.md).

Usage (WSL2, from repo root):
    uv run python experiments/E1_scored/run.py <E1-1|E1-2|E1-3|E1-4|E1-5|E1-6|E1-7|all> [--jobs N]

Refuses to run from uncommitted code. Never overwrites an existing trial
record (no reruns of failed trials); every trial is kept.
"""

from __future__ import annotations

import argparse
import json
import sys
from multiprocessing import Pool
from pathlib import Path

from rubiknetic.cube_logic import Move, invert, parse, random_scramble
from rubiknetic.cube_logic.notation import FACES
from rubiknetic.cube_physics import scored

OUT = Path(__file__).parent / "results"
SEXY6 = "R U R' U' " * 6
HALVES = "F2 B2 L2 R2 U2 D2"
E17_FACTORS = [
    ("timestep", [0.00025, 0.0005, 0.00075]),
    ("iterations", [50, 100, 200]),
    ("cubie_friction", [(0.1, 0.0025, 0.0005), (0.2, 0.0025, 0.0005), (0.5, 0.0025, 0.0005), (1.0, 0.0025, 0.0005)]),
    ("joint_frictionloss", [0.00005, 0.0005, 0.005]),
    ("chamfer", [0.0010, 0.0014, 0.0020]),
    ("gap", [0.0001, 0.0002, 0.0003]),
    ("radial_preload", [0.5, 1.0, 2.0, 3.0]),
    ("grip_force", [10.0, 30.0, 50.0]),
    ("misalign_max_deg", [0.0, 1.0, 2.0, 5.0]),
]


def trials(exp: str) -> list[tuple[str, str, dict]]:
    """(trial_id, kind, kwargs) for one experiment, exactly as pre-registered."""
    t: list[tuple[str, str, dict]] = []
    if exp == "E1-1":
        t = [(f"rest_s{s}", "rest", {"seed": s}) for s in range(1000, 1020)]
    elif exp == "E1-2":
        k = 0
        for f in FACES:
            for q in (1, 3):
                for _ in range(2):
                    s = 1100 + k
                    t.append((f"{Move(f, q)}_s{s}".replace("'", "p"), "seq", {"moves": str(Move(f, q)), "seed": s}))
                    k += 1
    elif exp == "E1-3":
        k = 0
        for f in FACES:
            for _ in range(2):
                s = 1200 + k
                t.append((f"{f}2_s{s}", "seq", {"moves": f"{f}2", "seed": s}))
                k += 1
        t += [(f"halves_s{s}", "seq", {"moves": HALVES, "seed": s}) for s in range(1230, 1240)]
    elif exp == "E1-4":
        t = [(f"sexy6_s{s}", "seq", {"moves": SEXY6.strip(), "seed": s}) for s in range(1300, 1320)]
        for s in range(1400, 1420):
            sc = random_scramble(20, s)
            seq = " ".join(str(m) for m in sc + invert(sc))
            t.append((f"scr20inv_s{s}", "seq", {"moves": seq, "seed": s}))
    elif exp == "E1-5":
        k = 0
        for sign in (1, -1):
            for deg in range(0, 21):
                s = 1500 + k
                t.append((f"forgive_{sign * deg:+d}_s{s}", "forgive", {"misalign_deg": float(sign * deg), "seed": s}))
                k += 1
    elif exp == "E1-6":
        t = [(f"openpad_{f}_s{1600 + i}", "openpad", {"face": f, "seed": 1600 + i}) for i, f in enumerate(FACES)]
        k = 0
        for pair in (("U", "R"), ("U", "F"), ("R", "F")):
            for tau in (1.0, 2.0):
                s = 1610 + k
                t.append((f"opposed_{''.join(pair)}_{tau:g}Nm_s{s}", "opposed",
                          {"faces": pair, "torque_limit": tau, "seed": s}))
                k += 1
        corners = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        t += [(f"twist_{''.join('p' if v > 0 else 'n' for v in c)}_s{1620 + i}", "twist",
               {"corner": c, "seed": 1620 + i}) for i, c in enumerate(corners)]
    elif exp == "E1-7":
        seen = set()
        for name, values in E17_FACTORS:
            for v in values:
                ov = {} if (name, v) in NOMINAL else {name: v}
                key = json.dumps(ov, sort_keys=True, default=list)
                if key in seen:
                    continue
                seen.add(key)
                tag = "nominal" if not ov else f"{name}={v}".replace(" ", "").replace("(", "").replace(")", "").replace(",", "-")
                for sname, seq in (("6move", "U U' R R' F F'"), ("sexy6", SEXY6.strip())):
                    t.append((f"{tag}__{sname}", "seq", {"moves": seq, "seed": 1000, "overrides": ov}))
    else:
        raise SystemExit(f"unknown experiment {exp}")
    return t


NOMINAL = {("timestep", 0.0005), ("iterations", 100), ("cubie_friction", (0.2, 0.0025, 0.0005)),
           ("joint_frictionloss", 0.0005), ("chamfer", 0.0014), ("gap", 0.0002), ("radial_preload", 1.0),
           ("misalign_max_deg", 1.0)}  # grip has no nominal: it is randomised 10-20 N per trial


def _execute(job: tuple[str, str, str, dict, str, dict]) -> str:
    exp, tid, kind, kw, commit, env = job
    path = OUT / exp / f"{tid}.json"
    if path.exists():
        return f"skip {exp}/{tid} (exists)"
    if kind == "seq":
        ov = dict(kw.get("overrides", {}))
        mis = ov.pop("misalign_max_deg", 1.0)
        rec = scored.run_sequence_trial(parse(kw["moves"]), kw["seed"], misalign_max_deg=mis, **ov)
    elif kind == "rest":
        rec = scored.run_rest_trial(kw["seed"])
    elif kind == "forgive":
        rec = scored.run_forgiveness_trial(kw["misalign_deg"], kw["seed"])
    elif kind == "openpad":
        rec = scored.run_open_pad_trial(kw["face"], kw["seed"])
    elif kind == "opposed":
        rec = scored.run_opposed_trial(tuple(kw["faces"]), kw["torque_limit"], kw["seed"])
    elif kind == "twist":
        rec = scored.run_corner_twist_trial(tuple(kw["corner"]), kw["seed"])
    else:
        raise ValueError(kind)
    rec.update({"experiment": exp, "trial_id": tid, "kind": kind, "spec": kw, "source_commit": commit,
                "environment": env, "scored": True})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1, default=list))
    return f"{'PASS' if rec['pass'] else 'FAIL'} {exp}/{tid}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("experiment")
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    commit = scored.require_clean_commit()
    env = scored.environment()
    exps = ["E1-1", "E1-2", "E1-3", "E1-4", "E1-5", "E1-6", "E1-7"] if a.experiment == "all" else [a.experiment]
    jobs = [(e, tid, kind, kw, commit, env) for e in exps for tid, kind, kw in trials(e)]
    # longest first for better load balance
    jobs.sort(key=lambda j: -len(j[3].get("moves", "").split()))
    print(f"commit {commit}: {len(jobs)} trials", flush=True)
    with Pool(a.jobs) as pool:
        for line in pool.imap_unordered(_execute, jobs):
            print(line, flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
