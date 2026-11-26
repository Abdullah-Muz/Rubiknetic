"""E1-8 CPU throughput benchmark for M7 (measurement only, no pass threshold; PHASE_1_M7_PREREGISTRATION.md §3, "E1-8:
throughput on a quiet machine, after the verdict"; it gates the G1 sign-off only).

Same scenarios as M1's experiments/E1_scored/bench.py and M4's experiments/E4_scored_m4/bench.py: cube only, cube + idle
rig, and a continuous U turn; timesteps 0.25, 0.5 and 1 ms; 1, 4, 8 and 16 parallel processes. The configuration is
M7's: M5's base overrides (B1, 0.05 mm piece gap), rounded edges R 2.5 mm, NoSlip 10 on the trial model, and M5's 48
magnets (4x2 mm N35, M5's table) installed on the timed model. Two comparisons, for the cost of each M7 ingredient:
without magnets, and with NoSlip off. The load average is recorded before and after each block, so a measurement
taken on a busy machine is visible as such.
Run alone from the repo root in WSL:  ~/.venvs/rubiknetic/bin/python experiments/E7_scored_m7/bench.py [--allow-dirty]
"""
from __future__ import annotations

import dataclasses
import importlib.util
import json
import os
import sys
import time
from multiprocessing import get_context
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("e7_scored_m7_run", HERE / "run.py")
E7 = importlib.util.module_from_spec(_spec)
sys.modules["e7_scored_m7_run"] = E7
_spec.loader.exec_module(E7)
R, M4 = E7.R, E7.M4

from rubiknetic.cube_physics import scored  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params  # noqa: E402
from rubiknetic.cube_physics.magnets import MagnetParams, MagnetSystem  # noqa: E402
from rubiknetic.cube_physics.rig import AuditedSim  # noqa: E402

OUT = HERE / "results_E1-8"
STEPS = 4000


def _measure(args: tuple[str, float, bool, int]) -> dict:
    scenario, dt, magnets, noslip = args
    p = dataclasses.replace(M1Params(**{**M4.BASE_OVERRIDES, "timestep": dt, "rig": scenario != "cube_only"}),
                            edge_profile="rounded", edge_radius=E7.EDGE_R)
    xml = scored.build_m1_xml(p)                                  # nothing is installed in this process
    if noslip:
        xml = E7.D13.with_noslip(xml, noslip)
    MagnetSystem.uninstall()
    m = mujoco.MjModel.from_xml_string(xml)                       # compiled with no callback installed
    d = mujoco.MjData(m)
    if magnets:
        mp = MagnetParams()
        MagnetSystem(m, p.pitch, p.gap, mp, tables=M4._tables_for(mp)).install()
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
    return {"scenario": scenario, "timestep_s": dt, "magnets": magnets, "noslip_iterations": int(m.opt.noslip_iterations),
            "edge_radius": p.edge_radius, "raw_steps_per_s": raw, "raw_realtime_factor": raw * dt,
            "audited_steps_per_s": audited, "audited_realtime_factor": audited * dt,
            "mean_contacts": float(np.mean(ncon)), "nv": m.nv}


def main() -> None:
    dirty = "--allow-dirty" in sys.argv
    commit = "DIRTY (not a scored record)" if dirty else R.require_m5_clean_commit()
    env = R.environment()
    load = {"start": os.getloadavg()}
    m7 = [(s, dt, True, E7.NOSLIP) for s in ("cube_only", "rig_idle", "turning") for dt in (0.00025, 0.0005, 0.001)]
    cmp_ = [("turning", 0.0005, False, E7.NOSLIP), ("turning", 0.0005, True, 0), ("rig_idle", 0.0005, False, E7.NOSLIP),
            ("rig_idle", 0.0005, True, 0)]
    single = [_measure(a) for a in m7 + cmp_]
    load["after_single"] = os.getloadavg()
    parallel = []
    ctx = get_context("fork")
    for n in (1, 4, 8, 16):
        t = time.perf_counter()
        with ctx.Pool(n) as pool:
            res = pool.map(_measure, [("turning", 0.0005, True, E7.NOSLIP)] * n)
        parallel.append({"processes": n, "per_process_raw_steps_per_s": [r["raw_steps_per_s"] for r in res],
                         "aggregate_raw_steps_per_s": sum(r["raw_steps_per_s"] for r in res),
                         "aggregate_realtime_factor": sum(r["raw_realtime_factor"] for r in res),
                         "wall_s": time.perf_counter() - t})
    load["end"] = os.getloadavg()
    rec = {"experiment": "E1-8", "mechanism": "M7", "scored": not dirty, "source_commit": commit, "environment": env,
           "logical_cpus": os.cpu_count(), "loadavg": load, "base_overrides": M4.BASE_OVERRIDES,
           "edge_radius": E7.EDGE_R, "noslip_iterations": E7.NOSLIP, "single_process": single,
           "parallel_turning_dt0.5ms_M7": parallel}
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / ("bench.json" if rec["scored"] else "bench_unscored.json")
    if path.exists():
        raise SystemExit(f"{path.name} exists; not overwriting")
    path.write_text(json.dumps(rec, indent=1))
    for r in single:
        print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items()})
    for r in parallel:
        print(r["processes"], round(r["aggregate_raw_steps_per_s"]), round(r["aggregate_realtime_factor"], 2))


if __name__ == "__main__":
    main()
