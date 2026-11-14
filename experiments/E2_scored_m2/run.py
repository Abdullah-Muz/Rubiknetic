"""Scored G1 runner for M2 (experiments/PHASE_1_M2_PREREGISTRATION.md).

Usage (WSL2, repo root):
    uv run python experiments/E2_scored_m2/run.py <E1-1|E1-2|E1-3|E1-4|E1-5b|E1-6|E1-7|all> [--jobs N]

It refuses to run from uncommitted code (frozen paths include the M2 src files and these scripts) and never
overwrites an existing trial record: there are no reruns of failed trials. E1-5 (switch transitions) is computed by
analyze.py from the switch logs of E1-2 to E1-4. E1-8 is bench.py.

Seeds are B + offset, with B = 3000 since Amendment 4 (D2) (run 1 used 2000):

| Experiment | Seeds |
|---|---|
| E1-1 | B+0 to B+19 |
| E1-2 | B+100 onward |
| E1-3 | B+200 onward |
| E1-4 | B+300 to B+319 (R U R′ U′ ×6), B+400 to B+419 (scrambles) |
| E1-5b | B+500 to B+541 |
| E1-6 | B+600 (open pads), B+610 (opposed), B+620 (twist), B+630 (forced switch, E1-6e), each onward |
| E1-7 | B+0 |
"""

from __future__ import annotations

import argparse
import json
import sys
from multiprocessing import Pool
from pathlib import Path

from rubiknetic.cube_logic import Move, invert, parse, random_scramble
from rubiknetic.cube_logic.notation import FACES
from rubiknetic.cube_physics import scored_m2 as S
from rubiknetic.cube_physics.m2_model import WeldParams
from rubiknetic.cube_physics.switching import SwitchRule

OUT = Path(__file__).parent / "results"
B = S.SCORED_SEED_RANGE[0]  # Amendment 4 (D2): every seed below is B + a fixed offset
SEXY6 = "R U R' U' " * 6
HALVES = "F2 B2 L2 R2 U2 D2"

# E1-7: M1's friction, timestep and iteration factors, plus the M2 factors (pre-registration section 4).
E17_FACTORS = [
    ("timestep", [0.00025, 0.0005, 0.00075]),
    ("iterations", [50, 100, 200]),
    ("cubie_friction", [(0.1, 0.0025, 0.0005), (0.2, 0.0025, 0.0005), (0.5, 0.0025, 0.0005), (1.0, 0.0025, 0.0005)]),
    ("grip_force", [10.0, 30.0, 50.0]),
    ("turn_kp", [5.0, 20.0]),
    ("rule.tol_unlock_deg", [0.5, 1.0, 2.0]),
    ("rule.tau_unlock", [0.02, 0.05, 0.1]),
    ("weld.solref", [(0.0005, 1.0), (0.001, 1.0), (0.002, 1.0)]),
]
NOMINAL = {("timestep", 0.0005), ("iterations", 100), ("cubie_friction", (0.2, 0.0025, 0.0005)), ("turn_kp", 20.0),  # C1: scored turner kp 20 is nominal; kp 5 is the sensitivity case
           ("rule.tol_unlock_deg", 1.0), ("rule.tau_unlock", 0.05), ("weld.solref", (0.001, 1.0))}
# grip has no nominal: it is randomised 10–20 N per trial.

_PERP_ORDER = list(FACES)


def trials(exp: str) -> list[tuple[str, str, dict]]:
    """(trial_id, kind, kwargs) for one experiment, exactly as pre-registered."""
    t: list[tuple[str, str, dict]] = []
    if exp == "E1-1":
        t = [(f"rest_s{s}", "rest", {"seed": s}) for s in range((B + 0), (B + 20))]
    elif exp == "E1-2":
        k = 0
        for f in FACES:
            for q in (1, 3):
                for _ in range(2):
                    s = (B + 100) + k
                    t.append((f"{Move(f, q)}_s{s}".replace("'", "p"), "seq", {"moves": str(Move(f, q)), "seed": s}))
                    k += 1
    elif exp == "E1-3":
        k = 0
        for f in FACES:
            for _ in range(2):
                s = (B + 200) + k
                t.append((f"{f}2_s{s}", "seq", {"moves": f"{f}2", "seed": s}))
                k += 1
        t += [(f"halves_s{s}", "seq", {"moves": HALVES, "seed": s}) for s in range((B + 230), (B + 240))]
    elif exp == "E1-4":
        t = [(f"sexy6_s{s}", "seq", {"moves": SEXY6.strip(), "seed": s}) for s in range((B + 300), (B + 320))]
        for s in range((B + 400), (B + 420)):
            sc = random_scramble(20, s)
            t.append((f"scr20inv_s{s}", "seq", {"moves": " ".join(str(m) for m in sc + invert(sc)), "seed": s}))
    elif exp == "E1-5b":
        k = 0
        for sign in (1, -1):
            for deg in range(0, 21):
                s = (B + 500) + k
                t.append((f"misturn_{sign * deg:+d}_s{s}", "misturn", {"misalign_deg": float(sign * deg), "seed": s}))
                k += 1
    elif exp == "E1-6":
        t = [(f"openpad_{f}_s{(B + 600) + i}", "openpad", {"face": f, "seed": (B + 600) + i}) for i, f in enumerate(FACES)]
        k = 0
        for pair in (("U", "R"), ("U", "F"), ("R", "F")):
            for tau in (1.0, 2.0):
                s = (B + 610) + k
                t.append((f"opposed_{''.join(pair)}_{tau:g}Nm_s{s}", "opposed",
                          {"faces": pair, "torque_limit": tau, "seed": s}))
                k += 1
        corners = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        t += [(f"twist_{''.join('p' if v > 0 else 'n' for v in c)}_s{(B + 620) + i}", "twist",
               {"corner": c, "seed": (B + 620) + i}) for i, c in enumerate(corners)]
        t += [(f"forcedswitch_{f}_s{(B + 630) + i}", "forced", {"face": f, "seed": (B + 630) + i}) for i, f in enumerate(FACES)]
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
                    t.append((f"{tag}__{sname}", "seq", {"moves": seq, "seed": (B + 0), "overrides": ov}))
    else:
        raise SystemExit(f"unknown experiment {exp}")
    return t


def _split_overrides(ov: dict) -> tuple[dict, SwitchRule | None, WeldParams | None]:
    m1, rule, weld = {}, {}, {}
    for k, v in ov.items():
        if k.startswith("rule."):
            rule[k[5:]] = v
        elif k.startswith("weld."):
            weld[k[5:]] = tuple(v) if isinstance(v, list) else v
        elif k == "turn_kp":
            m1["turn_kp"], m1["turn_kv"] = v, 0.04 * v  # damping scaled with stiffness (prototype: kp 20 -> kv 0.8)
        else:
            m1[k] = tuple(v) if isinstance(v, list) else v
    return m1, (SwitchRule(**rule) if rule else None), (WeldParams(**weld) if weld else None)


def _execute(job: tuple[str, str, str, dict, str, dict]) -> str:
    exp, tid, kind, kw, commit, env = job
    path = OUT / exp / f"{tid}.json"
    if path.exists():
        return f"skip {exp}/{tid} (exists)"
    if kind == "seq":
        m1, rule, weld = _split_overrides(dict(kw.get("overrides", {})))
        rec = S.run_sequence_trial_m2(parse(kw["moves"]), kw["seed"], rule=rule, weld=weld, **m1)
    elif kind == "rest":
        rec = S.run_rest_trial_m2(kw["seed"])
    elif kind == "misturn":
        rec = S.run_misaligned_turn_trial_m2(kw["misalign_deg"], kw["seed"])
    elif kind == "openpad":
        rec = S.run_open_pad_trial_m2(kw["face"], kw["seed"])
    elif kind == "opposed":
        rec = S.run_opposed_trial_m2(tuple(kw["faces"]), kw["torque_limit"], kw["seed"])
    elif kind == "twist":
        rec = S.run_corner_twist_trial_m2(tuple(kw["corner"]), kw["seed"])
    elif kind == "forced":
        rec = S.run_forced_misaligned_switch_trial_m2(kw["face"], kw["seed"])
    else:
        raise ValueError(kind)
    lo, hi = S.SCORED_SEED_RANGE
    assert lo <= kw["seed"] <= hi, "scored seed outside the pre-registered range"
    rec.update({"experiment": exp, "trial_id": tid, "kind": kind, "spec": kw, "source_commit": commit,
                "environment": env, "scored": True})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1, default=list))
    return f"{'PASS' if rec['pass'] else 'FAIL'} {exp}/{tid}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("experiment")
    ap.add_argument("--jobs", type=int, default=2)
    a = ap.parse_args()
    commit = S.require_clean_commit_m2()
    env = S.environment()
    exps = ["E1-1", "E1-2", "E1-3", "E1-4", "E1-5b", "E1-6", "E1-7"] if a.experiment == "all" else [a.experiment]
    jobs = [(e, tid, kind, kw, commit, env) for e in exps for tid, kind, kw in trials(e)]
    jobs.sort(key=lambda j: -len(j[3].get("moves", "").split()))
    print(f"commit {commit}: {len(jobs)} trials", flush=True)
    with Pool(a.jobs) as pool:
        for line in pool.imap_unordered(_execute, jobs):
            print(line, flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
