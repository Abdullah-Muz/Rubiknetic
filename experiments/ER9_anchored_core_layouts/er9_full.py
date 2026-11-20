"""ER9 part D: full 204-trial rehearsal of one probe arm (PROTOCOL.md, Part D). Unscored.

The Part B wrapper (er9_probe.py) around ER7's runner, with ER7's full trial list and the instrumented 60 s rest.
Usage (WSL, repo root):
    ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9_full.py run ARM [--jobs N]
Records: results/full/<arm>/<exp>/<tid>.json.gz (exclusive create; an existing record is skipped).
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import multiprocessing as mp_
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "full"
spec = importlib.util.spec_from_file_location("er9_probe", HERE / "er9_probe.py")
P = importlib.util.module_from_spec(spec); sys.modules["er9_probe"] = P; spec.loader.exec_module(P)
E7 = P.E7


def run_one(job: dict) -> dict:
    return P.run_one(job)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("run",))
    ap.add_argument("arm")
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    cfg = P.arms()[a.arm]
    sc = json.loads((P.OUT / "selfcheck.json").read_text())
    if not sc["pass"]:
        raise SystemExit("refusing to run: the probe self-check has not passed")
    rep = json.loads((P.OUT / "report.json").read_text())
    if not rep[a.arm]["signals"]["all_met"]:
        raise SystemExit(f"refusing to run: arm {a.arm} did not meet the probe signals")
    env = E7.D10.environment()
    P.table_for(cfg["grade"], cfg.get("scale", 1.0))
    jobs = [{**copy.deepcopy(j), "er7_arm": "C52", "er9_arm": a.arm, "er9_cfg": cfg, "env": env,
             "commit": env["commit"], "scored": False, "reported_only": True} for j in E7.er7_jobs()]
    path = lambda j: OUT / a.arm / j["exp"] / f"{j['tid']}.json.gz"  # noqa: E731
    todo = [j for j in jobs if not path(j).exists()]
    todo.sort(key=lambda j: -len(j["kw"].get("moves", "").split()))            # longest sequences first
    (OUT / a.arm).mkdir(parents=True, exist_ok=True)
    (OUT / a.arm / "environment.json").write_text(json.dumps({**env, "config": cfg}, indent=1))
    print(f"{len(todo)} trials to run ({len(jobs)} in total); arm {a.arm}: {cfg}", flush=True)
    t0 = time.perf_counter()
    with mp_.get_context("fork").Pool(a.jobs, maxtasksperchild=1) as pool:
        for k, rec in enumerate(pool.imap_unordered(run_one, todo), 1):
            p = OUT / a.arm / rec["experiment"] / f"{rec['trial_id']}.json.gz"
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "xb") as f:
                f.write(E7._dump(rec))
            extra = f" rest {rec['rest_rotation_deg']:.3f}" if rec.get("kind") == "rest" else ""
            print(f"[{k}/{len(todo)} {time.perf_counter() - t0:.0f} s] {a.arm} {'PASS' if rec['pass'] else 'FAIL'} "
                  f"{rec['experiment']}/{rec['trial_id']}{extra}{' FLAG' if rec['er7_flag_outside_regime'] else ''} "
                  f"{'; '.join(rec['fail_reasons'])}", flush=True)


if __name__ == "__main__":
    main()
