"""ER9 Part G, G.0 item 1: the composite magnet system's model checks V4 (momentum), V5 (energy) and V6 (pose-only)
for the Part G arms, using D8-1b's own check models and criteria (experiments/D8_alignment/d8_1b_checks.py) with the
arm's composite MagnetSystem (er9g_layouts.build_system) in place of M1's single-type system. Exploratory, unscored.

V4  at 12 poses (each face turned by 1-44 deg, plus small random piece rotations, seed 404), the arm's per-magnet forces
    sum to zero and the torques about the cube centre sum to zero (relative 1e-9), i.e. Newton's third law and
    angular-momentum balance of the whole composite.
V5  D8-1b's V5 model: the R layer turns as one rigid body on the R centre's hinge, contacts, gravity, damping and
    friction off, started 3 deg from home; RK4 at 0.5 ms for 0.5 s; total energy (kinetic + potential + magnet energy)
    drifts by at most 1 % of the magnet energy exchanged (D8's criterion).
V6  D8-1b's V6: magnet qfrc_passive is identical after changing ctrl, time, qvel and act; the installed callback adds
    exactly the direct contribution.
Writes results/hybrid_g/static/composite_checks.json (exclusive create).
Usage (WSL, repo root): ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9g_composite_checks.py
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "results" / "hybrid_g" / "static" / "composite_checks.json"


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


LY = _load("er9g_layouts", HERE / "er9g_layouts.py")
D8 = _load("d8_1b_checks", REPO / "experiments" / "D8_alignment" / "d8_1b_checks.py")
from rubiknetic.cube_physics.m1_model import M1Params  # noqa: E402
from rubiknetic.cube_physics.magnets import MagnetSystem  # noqa: E402

ARMS = ("PG8", "PG20")


def v4(arm: str) -> dict:
    m, d = D8.build(M1Params(radial_preload=0.0, rig=True, gap=LY.GAP))
    ms = LY.build_system(m, arm)
    rng = np.random.default_rng(404)
    worst_f, worst_t, n_near_cross = 0.0, 0.0, 0
    for k in range(12):
        mujoco.mj_resetData(m, d)
        D8.turn_layer(m, d, k % 3, 1 if k % 2 else -1, float(1 + (k * 43) % 44))
        mujoco.mj_kinematics(m, d)
        pp, n = ms.world(d.xpos, d.xmat)
        tilt = rng.normal(0, np.radians(0.5), (len(n), 3))          # small independent piece rotations of n
        n = n + np.cross(tilt, n)
        n /= np.linalg.norm(n, axis=1, keepdims=True)
        F, T, _ = ms.forces(pp, n, stats=True)
        scale = float(np.abs(F).sum())
        worst_f = max(worst_f, float(np.linalg.norm(F.sum(axis=0))) / scale)
        worst_t = max(worst_t, float(np.linalg.norm((T + np.cross(pp, F)).sum(axis=0))) / (scale * 0.03))
    return {"poses": 12, "max_rel_net_force": worst_f, "max_rel_net_torque": worst_t,
            "pass": bool(worst_f < 1e-9 and worst_t < 1e-9)}


def v5(arm: str, duration: float = 0.5, timestep: float = 0.0005) -> dict:
    mp1 = M1Params(radial_preload=0.0, rig=False, gap=LY.GAP, gravity_z=0.0, joint_damping=0.0, joint_frictionloss=0.0,
                   integrator="RK4", timestep=timestep)
    m, d = D8.build_r_hinge_model(mp1)
    m.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_CONTACT
    m.opt.enableflags |= mujoco.mjtEnableBit.mjENBL_ENERGY
    ms = LY.build_system(m, arm, gap=mp1.gap)
    ms.install()
    try:
        D8.turn_layer(m, d, 0, 1, 3.0)
        mujoco.mj_forward(m, d)
        E, U = [], []
        for _ in range(int(duration / m.opt.timestep)):
            mujoco.mj_step(m, d)
            u = ms.energy(d)
            U.append(u)
            E.append(d.energy[1] + d.energy[0] + u)
        E, U = np.array(E), np.array(U)
        exch = float(U.max() - U.min())
        drift = float(np.abs(E - E[0]).max())
        return {"integrator": "RK4", "duration_s": duration, "timestep_s": timestep, "energy_exchanged_J": exch,
                "max_drift_J": drift, "drift_rel": drift / exch if exch > 0 else None, "stats": dict(ms.stats),
                "pass": bool(exch > 0 and drift <= 0.01 * exch)}
    finally:
        MagnetSystem.uninstall()


def v6(arm: str) -> dict:
    m, d = D8.build(M1Params(radial_preload=0.0, rig=True, gap=LY.GAP))
    ms = LY.build_system(m, arm)
    D8.turn_layer(m, d, 0, 1, 2.0)
    mujoco.mj_forward(m, d)

    def contrib():
        d.qfrc_passive[:] = 0.0
        ms.apply(m, d)
        return d.qfrc_passive.copy()

    base = contrib()
    rng = np.random.default_rng(6)
    d.ctrl[:] = rng.uniform(-1, 1, m.nu)
    d.time = 123.4
    d.qvel[:] = rng.normal(0, 1, m.nv)
    if m.na:
        d.act[:] = rng.uniform(-1, 1, m.na)
    after = contrib()
    mujoco.mj_forward(m, d)
    without = d.qfrc_passive.copy()
    ms.install()
    try:
        mujoco.mj_forward(m, d)
        with_cb = d.qfrc_passive.copy()
    finally:
        MagnetSystem.uninstall()
    return {"max_abs_magnet_qfrc": float(np.abs(base).max()),
            "max_change_from_ctrl_time_qvel_act": float(np.abs(after - base).max()),
            "installed_matches_direct": float(np.abs((with_cb - without) - base).max()),
            "pass": bool(np.abs(base).max() > 0 and np.array_equal(after, base)
                         and np.allclose(with_cb - without, base, rtol=0, atol=1e-12))}


def main() -> None:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", str(Path(__file__).relative_to(REPO))], cwd=REPO,
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit("refusing: commit er9g_composite_checks.py first")
    res = {"commit": commit, "protocol": "Part G G.0 item 1 (V4, V5, V6 of the composite system); deviation 3"}
    for arm in ARMS:
        res[arm] = {"V4": v4(arm), "V6": v6(arm), "V5": v5(arm)}
        print(arm, {k: v["pass"] for k, v in res[arm].items()},
              {"V5_drift_rel": res[arm]["V5"]["drift_rel"]}, flush=True)
    res["pass"] = all(res[a][c]["pass"] for a in ARMS for c in ("V4", "V5", "V6"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "x") as f:
        json.dump(res, f, indent=1, default=float)
    print("pass", res["pass"])


if __name__ == "__main__":
    main()
