"""D11 — runs the 20 E1-1 seeds for 60 s at the frozen M5 settings (PROTOCOL.md), using D10's instrumented rest loop
(imported read-only). Writes only to experiments/D11_rest_slip_count/results/.

Usage (WSL):  ~/.venvs/rubiknetic/bin/python experiments/D11_rest_slip_count/d11_slip.py [--jobs N]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import multiprocessing as mp_
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "results"
SEEDS = list(range(10000, 10020))

_spec = importlib.util.spec_from_file_location("d10_rest", REPO / "experiments/D10_m5_rest_diagnostic/d10_rest.py")
D10 = importlib.util.module_from_spec(_spec)
sys.modules["d10_rest"] = D10
_spec.loader.exec_module(D10)
D10.ARMS["D11"] = {"duration_s": 60.0}


def job(seed: int) -> dict:
    return D10.run_job(("D11", seed))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=7)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    env = D10.environment()
    (OUT / "environment.json").write_text(json.dumps(env, indent=1))
    with mp_.get_context("fork").Pool(a.jobs, maxtasksperchild=1) as pool:
        for res in pool.imap_unordered(job, SEEDS):
            res["environment"] = env
            (OUT / f"rest60_s{res['seed']}.json").write_text(
                json.dumps(res, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x)))
            print(f"s{res['seed']}  peak0-10 {res['rest_rotation_deg']:.6f} deg  wall {res['wall_s']:.0f} s", flush=True)


if __name__ == "__main__":
    main()
