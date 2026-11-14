"""E1-8 CPU throughput benchmark for M2 (measurement only, no pass threshold).

Run it ALONE (no other simulation jobs) from repo root in WSL2:
    uv run python experiments/E2_scored_m2/bench.py

It fixes the flaw in the M1 benchmark: raw and audited stepping are timed from the SAME state. The audited
simulator is first advanced to the scenario state, then its MjData is copied (mj_copyData) into a raw MjData. Raw
mj_step on the copy and audited stepping on the original are each timed for STEPS steps, starting from that
identical state. The audited path includes the edit audit, the switch manager and the monitor hooks.

Scenarios:
* cube_only: no rig;
* rig_idle;
* turning: U turned by its rig; measured mid-turn with the layer unlocked.

Timesteps 0.25, 0.5 and 1 ms. Processes 1, 4, 8 and 16 for "turning" at 0.5 ms.
"""

from __future__ import annotations

import json
import os
import time
from multiprocessing import Pool
from pathlib import Path

import mujoco
import numpy as np

from rubiknetic.cube_physics import scored_m2 as S
from rubiknetic.cube_physics.m2_model import build_m2_xml, m2_params
from rubiknetic.cube_physics.switching import SwitchAuditedSim, SwitchManager

OUT = Path(__file__).parent / "results" / "E1-8"
STEPS = 2000


def _env(scenario: str, dt: float):
    p = m2_params(timestep=dt, rig=scenario != "cube_only")
    m = mujoco.MjModel.from_xml_string(build_m2_xml(p))
    sim = SwitchAuditedSim(m)
    mujoco.mj_forward(m, sim.d)
    mgr = SwitchManager(sim, p.pitch)
    mgr.setup_reanchor(sim.d)
    return p, m, sim, mgr


def _measure(args: tuple[str, float]) -> dict:
    scenario, dt = args
    p, m, sim, mgr = _env(scenario, dt)
    d = sim.d
    sim.step(int(0.3 / dt))  # settle (not timed)
    if scenario == "turning":
        aid = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, n)  # noqa: E731
        for g in ("grip_Ua", "grip_Ub"):
            d.ctrl[aid(g)] = -(p.pad_open_clearance + p.grip_overshoot)
        sim.step(int(0.3 / dt))
        d.ctrl[aid("turn_U")] = -0.5 * np.pi  # turner driven toward a quarter turn
        for _ in range(int(2.0 / dt)):        # advance until the manager has unlocked U and the layer moves
            sim.step()
            if mgr.unlocked == "U" and abs(np.degrees(d.qpos[mgr.hinge["U"]])) > 15.0:
                break
    d_raw = mujoco.MjData(m)
    mujoco.mj_copyData(d_raw, m, d)  # identical starting state (eq_active included; eq_data lives in the model)
    ncon_raw = []
    t = time.perf_counter()
    for k in range(STEPS):
        mujoco.mj_step(m, d_raw)
        if k % 100 == 0:
            ncon_raw.append(d_raw.ncon)
    raw = STEPS / (time.perf_counter() - t)
    t = time.perf_counter()
    sim.step(STEPS)
    audited = STEPS / (time.perf_counter() - t)
    return {"scenario": scenario, "timestep_s": dt, "raw_steps_per_s": raw, "raw_realtime_factor": raw * dt,
            "audited_steps_per_s": audited, "audited_realtime_factor": audited * dt,
            "mean_contacts_raw": float(np.mean(ncon_raw)), "nv": m.nv, "neq": m.neq,
            "unlocked_at_start": mgr.unlocked if scenario == "turning" else None}


def main() -> None:
    commit = S.require_clean_commit_m2()
    env = S.environment()
    single = [_measure((s, dt)) for s in ("cube_only", "rig_idle", "turning") for dt in (0.00025, 0.0005, 0.001)]
    parallel = []
    for n in (1, 4, 8, 16):
        t = time.perf_counter()
        with Pool(n) as pool:
            res = pool.map(_measure, [("turning", 0.0005)] * n)
        parallel.append({"processes": n, "per_process_raw_steps_per_s": [r["raw_steps_per_s"] for r in res],
                         "aggregate_raw_steps_per_s": sum(r["raw_steps_per_s"] for r in res),
                         "aggregate_audited_steps_per_s": sum(r["audited_steps_per_s"] for r in res),
                         "aggregate_raw_realtime_factor": sum(r["raw_realtime_factor"] for r in res),
                         "wall_s": time.perf_counter() - t})
    rec = {"experiment": "E1-8", "model": "M2", "scored": True, "source_commit": commit, "environment": env,
           "logical_cpus": os.cpu_count(), "steps_timed": STEPS, "single_process": single,
           "parallel_turning_dt0.5ms": parallel}
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "bench.json"
    if path.exists():
        raise SystemExit("bench.json exists; not overwriting")
    path.write_text(json.dumps(rec, indent=1))
    for r in single:
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    for r in parallel:
        print(r["processes"], round(r["aggregate_raw_steps_per_s"]), round(r["aggregate_raw_realtime_factor"], 2))


if __name__ == "__main__":
    main()
