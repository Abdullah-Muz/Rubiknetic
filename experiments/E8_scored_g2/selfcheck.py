"""G2 self-check (pre-registration §7 P-6; UNSCORED): re-run pilot trials with the current code and compare them with the
committed pilot records (pilot_P5/results). Volatile fields (wall time, load, commit, environment, smoke/scored flags)
are ignored; every physics field must be identical, including each record's final qpos SHA-256.
Usage (WSL, repo root): python experiments/E8_scored_g2/selfcheck.py [--jobs 3]
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run as R  # noqa: E402

CHECK = [("P-U", "U_s29200"), ("P-jam", "jam0.8_s29233"), ("P-rand", "rand10_s29260")]
VOLATILE = {"wall_s", "loadavg_start", "source_commit", "environment", "smoke", "scored"}


def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if k not in VOLATILE}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x


def diff(a, b, path=""):
    if type(a) is not type(b):
        return [f"{path}: type {type(a).__name__} != {type(b).__name__}"]
    if isinstance(a, dict):
        out = [f"{path}/{k}: missing" for k in set(a) ^ set(b)]
        for k in set(a) & set(b):
            out += diff(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in diff(x, y, f"{path}[{i}]")]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=3)
    a = ap.parse_args()
    jobs = {R.key_of(j): j for j in R.pilot_jobs()}
    todo = [jobs[k] for k in CHECK]
    for j in todo:
        j["smoke"] = True
    with ProcessPoolExecutor(a.jobs, mp_context=multiprocessing.get_context("spawn"), max_tasks_per_child=1) as ex:
        results = list(ex.map(R.run_job, todo))
    bad = 0
    for key, rec in results:
        ref = json.loads((HERE / "pilot_P5" / "results" / key[0] / f"{key[1]}.json").read_text())
        new = json.loads(json.dumps(rec, default=list))
        d = diff(strip(ref), strip(new))
        bad += bool(d)
        print(f"{'IDENTICAL' if not d else 'DIFFERS'} {key[0]}/{key[1]}  qpos sha {new.get('final_qpos_sha256', '')[:12]}"
              + ("" if not d else "\n  " + "\n  ".join(d[:10])), flush=True)
    print(f"self-check: {len(results) - bad}/{len(results)} identical")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
