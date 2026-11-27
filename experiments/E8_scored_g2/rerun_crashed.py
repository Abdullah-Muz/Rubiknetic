"""Re-run named pilot trials whose records were harness crashes (UNSCORED; P-127). Writes to --out.
Usage (WSL, repo root): python experiments/E8_scored_g2/rerun_crashed.py pilot3 P3-conf/rand10_s29448 ... --out DIR"""
import argparse
import json
import multiprocessing
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as R  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pilot", choices=("pilot", "pilot2", "pilot3", "pilot4"))
    ap.add_argument("keys", nargs="+")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    jobs = {R.key_of(j): j for j in {"pilot": R.pilot_jobs, "pilot2": R.pilot2_jobs, "pilot3": R.pilot3_jobs,
                                         "pilot4": R.pilot4_jobs}[a.pilot]()}
    todo = [jobs[tuple(k.split("/"))] for k in a.keys]
    for j in todo:
        j["smoke"] = True
    with ProcessPoolExecutor(len(todo), mp_context=multiprocessing.get_context("spawn"), max_tasks_per_child=1) as ex:
        res = list(ex.map(R.run_job, todo))
    a.out.mkdir(parents=True, exist_ok=True)
    for k, r in res:
        (a.out / f"{k[1]}.json").write_text(json.dumps(r, indent=1, default=list))
        t = r.get("trial") or {}
        print(k, r["pass"], r["fail_reasons"][:2], "retries", r.get("load_retries"),
              "end misalignment %.2f slip %.3f rot %.3f" % (max(t.get("residual_end_deg", [0])),
                                                           t.get("core_slip_total_mm", 0), t.get("core_rot_total_deg", 0)))
