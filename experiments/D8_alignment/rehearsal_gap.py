"""UNSCORED dress rehearsal of the M4 G1 battery with a modified piece gap (2026-11-15).

Why: the M4 runner's smoke test showed non-target drift above M1's approved 1 deg limit (1.59 deg). An unscored
probe (seeds 95-97) found drift > 1 deg in 9/18 moves at the 0.2 mm piece gap and 0/18 at 0.1 mm. Before proposing a
configuration amendment, this runs every pre-registered experiment E1-1...E1-6 and E1-5s through the unmodified M4
runner logic (experiments/E4_scored_m4/run.py: run_trial + apply_m4_criteria) with the piece gap overridden.

Seeds: the scored list shifted by +1000 (7000-7999; 0.1 mm) or by --shift 2000 (8000-8999; 0.05 mm), disjoint from every
scored range. Results are diagnostic only
and never count toward G1. The E1-6c threshold is not set, so E1-6c is reported against M1's categorical criterion.
Usage (WSL, repo root): rehearsal_gap.py <gap_m> [--jobs N] [--shift S]
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("e4run", ROOT / "experiments" / "E4_scored_m4" / "run.py")
R = importlib.util.module_from_spec(spec)
sys.modules["e4run"] = R
spec.loader.exec_module(R)

SHIFT = int(sys.argv[sys.argv.index("--shift") + 1]) if "--shift" in sys.argv else 1000   # 2026-11-16: 0.05 mm uses 2000
EXPS = ["E1-1", "E1-2", "E1-3", "E1-4", "E1-5", "E1-6", "E1-5s", "E1-6t"]   # E1-6t added 2026-11-15 (P-24)


def jobs(gap: float, out: Path) -> list[dict]:
    validated = R.nominal_validated_tilt()
    js = []
    for exp in EXPS:
        for tid, kind, kw in R.trials(exp):
            kw = copy.deepcopy(kw)
            s = kw["seed"]
            kw["seed"] = s + SHIFT
            kw.setdefault("overrides", {})["gap"] = gap
            js.append({"exp": exp, "sub": R.sub_experiment(exp, kind), "tid": tid.replace(f"_s{s}", f"_s{s + SHIFT}"),
                       "kind": kind, "kw": kw, "gap": gap, "validated": validated, "out": str(out)})
    js.sort(key=lambda j: -len(j["kw"].get("moves", "").split()))
    return js


def execute(job: dict) -> str:
    path = Path(job["out"]) / job["exp"] / f"{job['tid']}.json"
    if path.exists():
        return f"skip {job['tid']}"
    R.BASE_OVERRIDES = {"radial_preload": 0.0, "gap": job["gap"]}   # every harness trial in this process
    load0 = os.getloadavg()[0]
    rec, ms, _ = R.run_trial(job["kind"], copy.deepcopy(job["kw"]), True)
    rec.update({"experiment": job["exp"], "sub_experiment": job["sub"], "trial_id": job["tid"], "kind": job["kind"],
                "spec": job["kw"], "scored": False, "rehearsal": True, "base_overrides": R.BASE_OVERRIDES,
                "loadavg_start": load0})
    R.apply_m4_criteria(rec, job["sub"], job["validated"], ms is not None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1, default=list))
    return f"{'PASS' if rec['pass'] else 'FAIL'} {job['exp']}/{job['tid']} {'; '.join(rec['fail_reasons'])}"


def main() -> None:
    gap = float(sys.argv[1])
    n = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 8
    out = Path(__file__).parent / "results" / f"rehearsal_gap{gap * 1e3:g}mm"
    js = jobs(gap, out)
    print(f"{len(js)} trials, gap {gap * 1e3:g} mm, out {out}", flush=True)
    t0 = time.perf_counter()
    with Pool(n) as pool:
        for line in pool.imap_unordered(execute, js):
            print(line, flush=True)
    print(f"done in {time.perf_counter() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
