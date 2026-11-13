"""E1-8 CPU throughput benchmark (measurement only, no pass threshold).

Run ALONE (no other simulation jobs) from repo root in WSL2:
    uv run python experiments/E1_scored/bench.py
Measures raw mj_step throughput (no Python audit/monitor overhead) and the
full audited harness, for: cube at rest without rig, cube + idle rig, and a
continuous U turn; timesteps 0.25/0.5/1 ms; 1/4/8/16 parallel processes.
"""

from __future__ import annotations

import json
import os
import time
from multiprocessing import Pool
from pathlib import Path

import mujoco
import numpy as np

from rubiknetic.cube_physics import scored
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml
from rubiknetic.cube_physics.rig import AuditedSim, TurnRig

OUT = Path(__file__).parent / "results" / "E1-8"
STEPS = 4000


def _measure(args: tuple[str, float]) -> dict:
    scenario, dt = args
    p = M1Params(timestep=dt, rig=scenario != "cube_only")
    m = mujoco.MjModel.from_xml_string(build_m1_xml(p))
    d = mujoco.MjData(m)
    for _ in range(int(0.3 / dt)):  # settle (not timed)
        mujoco.mj_step(m, d)
    if scenario == "turning":
        aid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, "turn_U")
        for g in ("grip_Ua", "grip_Ub"):
            d.ctrl[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, g)] = -(p.pad_open_clearance + p.grip_overshoot)
        for _ in range(int(0.3 / dt)):
            mujoco.mj_step(m, d)
    ncon = []
    t = time.perf_counter()
    for k in range(STEPS):
        if scenario == "turning":
            d.ctrl[aid] = -0.5 * np.pi * (k + 1) / STEPS  # slow continuous turn (actuator command)
        mujoco.mj_step(m, d)
        if k % 100 == 0:
            ncon.append(d.ncon)
    el = time.perf_counter() - t
    raw = STEPS / el
    # audited harness overhead (same scenario, idle actuators)
    sim = AuditedSim(m, d)
    t = time.perf_counter()
    sim.step(1000)
    audited = 1000 / (time.perf_counter() - t)
    return {"scenario": scenario, "timestep_s": dt, "raw_steps_per_s": raw,
            "raw_realtime_factor": raw * dt, "audited_steps_per_s": audited,
            "audited_realtime_factor": audited * dt, "mean_contacts": float(np.mean(ncon)), "nv": m.nv}


def main() -> None:
    commit = scored.require_clean_commit()
    env = scored.environment()
    single = [_measure((s, dt)) for s in ("cube_only", "rig_idle", "turning") for dt in (0.00025, 0.0005, 0.001)]
    parallel = []
    for n in (1, 4, 8, 16):
        jobs = [("turning", 0.0005)] * n
        t = time.perf_counter()
        with Pool(n) as pool:
            res = pool.map(_measure, jobs)
        parallel.append({"processes": n, "per_process_raw_steps_per_s": [r["raw_steps_per_s"] for r in res],
                         "aggregate_raw_steps_per_s": sum(r["raw_steps_per_s"] for r in res),
                         "aggregate_realtime_factor": sum(r["raw_realtime_factor"] for r in res),
                         "wall_s": time.perf_counter() - t})
    rec = {"experiment": "E1-8", "scored": True, "source_commit": commit, "environment": env,
           "logical_cpus": os.cpu_count(), "single_process": single, "parallel_turning_dt0.5ms": parallel}
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "bench.json"
    if path.exists():
        raise SystemExit("bench.json exists; not overwriting")
    path.write_text(json.dumps(rec, indent=1))
    for r in single:
        print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items()})
    for r in parallel:
        print(r["processes"], round(r["aggregate_raw_steps_per_s"]), round(r["aggregate_realtime_factor"], 2))


if __name__ == "__main__":
    main()
