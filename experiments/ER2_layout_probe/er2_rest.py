"""ER2 part O2: unscored 60 s rest rehearsal on new seeds 14000-14019 at piece gap 0.05 mm (G050, frozen M5) and
0.025 mm (G025), M5 magnet layout, D10's instrumented loop (PROTOCOL.md). Writes results/rest_<arm>_s<seed>.json.gz.
Usage (WSL):  ~/.venvs/rubiknetic/bin/python experiments/ER2_layout_probe/er2_rest.py [--jobs N]
"""
from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import multiprocessing as mp_
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "results"
SEEDS = list(range(14000, 14020))
ARMS = {"G050": 5e-5, "G025": 2.5e-5}
spec = importlib.util.spec_from_file_location("d10_rest", REPO / "experiments/D10_m5_rest_diagnostic/d10_rest.py")
D10 = importlib.util.module_from_spec(spec); sys.modules["d10_rest"] = D10; spec.loader.exec_module(D10)


def job(j: tuple[str, int]) -> dict:
    arm, seed = j
    gap = ARMS[arm]
    M5 = D10._load_m5(); M4 = M5.M4
    from rubiknetic.cube_physics import scored
    t0 = time.perf_counter()
    ms = M4.use_magnets(M5.magnet_params_for({}), gap)
    ms.reset_neighbour_list(); ms.reset_stats()
    M4.MagnetMonitor.last = None
    pf = scored.params_for
    scored.params_for = lambda setup, **kw: pf(setup, **{"gap": gap, **kw})
    try:
        rec = D10.instrumented_rest(scored, M4, seed, 60.0, ms)
    finally:
        scored.params_for = pf
    rec["magnet_stats"] = dict(ms.stats)
    return {"arm": arm, "seed": seed, "gap": gap, "rest_rotation_deg": rec["rest_rotation_deg"],
            "attribution": D10.attribute(rec), "record": rec, "wall_s": time.perf_counter() - t0}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=10)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    env = D10.environment()
    (OUT / "rest_environment.json").write_text(json.dumps(env, indent=1))
    jobs = [(arm, s) for s in SEEDS for arm in ARMS]
    with mp_.get_context("fork").Pool(a.jobs, maxtasksperchild=1) as pool:
        for res in pool.imap_unordered(job, jobs):
            res["environment"] = env
            raw = json.dumps(res, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x)).encode()
            (OUT / f"rest_{res['arm']}_s{res['seed']}.json.gz").write_bytes(gzip.compress(raw, 9, mtime=0))
            print(f"{res['arm']} s{res['seed']}  peak0-10 {res['rest_rotation_deg']:.4f} deg  "
                  f"aborted={res['record'].get('aborted')}  wall {res['wall_s']:.0f} s", flush=True)


if __name__ == "__main__":
    main()
