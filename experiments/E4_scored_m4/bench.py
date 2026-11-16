"""E1-8 CPU throughput benchmark for M4 (measurement only, no pass threshold; PHASE_1_M4_PREREGISTRATION.md §4).

Same scenarios as M1's experiments/E1_scored/bench.py (cube only, cube + idle rig, continuous U turn; timesteps 0.25,
0.5 and 1 ms; 1, 4, 8 and 16 parallel processes), each WITH and WITHOUT the M4 magnets, on the frozen M4 base
configuration (run.py BASE_OVERRIDES). The load average is recorded before and after each block, so a measurement
taken on a busy machine is visible as such.
Run alone from the repo root in WSL2:  uv run python experiments/E4_scored_m4/bench.py [--allow-dirty]
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import mujoco
import numpy as np

from rubiknetic.cube_physics import scored
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml
from rubiknetic.cube_physics.magnets import MagnetParams, MagnetSystem, near_field_tables
from rubiknetic.cube_physics.rig import AuditedSim

HERE = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("e4run", HERE / "run.py")
R = importlib.util.module_from_spec(_spec)
sys.modules["e4run"] = R
_spec.loader.exec_module(R)

OUT = HERE / "results" / "E1-8"
STEPS = 4000


def _measure(args: tuple[str, float, bool]) -> dict:
    scenario, dt, magnets = args
    p = M1Params(**{**R.BASE_OVERRIDES, "timestep": dt, "rig": scenario != "cube_only"})
    MagnetSystem.uninstall()
    m = mujoco.MjModel.from_xml_string(build_m1_xml(p))          # compiled with no callback installed
    d = mujoco.MjData(m)
    if magnets:
        MagnetSystem(m, p.pitch, p.gap, MagnetParams(), tables=near_field_tables(MagnetParams(), R.TABLES)).install()
    try:
        for _ in range(int(0.3 / dt)):                           # settle (not timed)
            mujoco.mj_step(m, d)
        if scenario == "turning":
            aid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, "turn_U")
            for g in ("grip_Ua", "grip_Ub"):
                d.ctrl[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, g)] = -(p.pad_open_clearance
                                                                                    + p.grip_overshoot)
            for _ in range(int(0.3 / dt)):
                mujoco.mj_step(m, d)
        ncon = []
        t = time.perf_counter()
        for k in range(STEPS):
            if scenario == "turning":
                d.ctrl[aid] = -0.5 * np.pi * (k + 1) / STEPS           # slow continuous turn (actuator command)
            mujoco.mj_step(m, d)
            if k % 100 == 0:
                ncon.append(d.ncon)
        raw = STEPS / (time.perf_counter() - t)
        sim = AuditedSim(m, d)
        t = time.perf_counter()
        sim.step(1000)
        audited = 1000 / (time.perf_counter() - t)
    finally:
        MagnetSystem.uninstall()
    return {"scenario": scenario, "timestep_s": dt, "magnets": magnets, "raw_steps_per_s": raw,
            "raw_realtime_factor": raw * dt, "audited_steps_per_s": audited, "audited_realtime_factor": audited * dt,
            "mean_contacts": float(np.mean(ncon)), "nv": m.nv}


def main() -> None:
    commit = "DIRTY (not a scored record)" if "--allow-dirty" in sys.argv else R.require_m4_clean_commit()
    env = scored.environment()
    load = {"start": os.getloadavg()}
    single = [_measure((s, dt, mag)) for mag in (True, False) for s in ("cube_only", "rig_idle", "turning")
              for dt in (0.00025, 0.0005, 0.001)]
    load["after_single"] = os.getloadavg()
    parallel = []
    for mag in (True, False):
        for n in (1, 4, 8, 16):
            t = time.perf_counter()
            with Pool(n) as pool:
                res = pool.map(_measure, [("turning", 0.0005, mag)] * n)
            parallel.append({"magnets": mag, "processes": n,
                             "per_process_raw_steps_per_s": [r["raw_steps_per_s"] for r in res],
                             "aggregate_raw_steps_per_s": sum(r["raw_steps_per_s"] for r in res),
                             "aggregate_realtime_factor": sum(r["raw_realtime_factor"] for r in res),
                             "wall_s": time.perf_counter() - t})
    load["end"] = os.getloadavg()
    rec = {"experiment": "E1-8", "mechanism": "M4", "scored": "--allow-dirty" not in sys.argv, "source_commit": commit,
           "environment": env, "logical_cpus": os.cpu_count(), "loadavg": load,
           "base_overrides": R.BASE_OVERRIDES, "single_process": single, "parallel_turning_dt0.5ms": parallel}
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / ("bench.json" if rec["scored"] else "bench_unscored.json")
    if path.exists():
        raise SystemExit(f"{path.name} exists; not overwriting")
    path.write_text(json.dumps(rec, indent=1))
    for r in single:
        print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items()})
    for r in parallel:
        print(r["magnets"], r["processes"], round(r["aggregate_raw_steps_per_s"]), round(r["aggregate_realtime_factor"], 2))


if __name__ == "__main__":
    main()
