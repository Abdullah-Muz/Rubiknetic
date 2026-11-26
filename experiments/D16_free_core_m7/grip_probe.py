"""D16-0: UNSCORED probe of the force the M1/M7 rig pads actually apply.

The rig's pad actuator is a position servo (kp = grip_kp) whose target is pad_overshoot beyond first contact, with
forcerange = +-grip_force. Its steady squeeze is therefore at most min(grip_force, grip_kp * overshoot) = 12 N with the
defaults (2000 N/m x 6 mm). This probe measures it: M7 model (rounded R 2.5 mm, NoSlip 10, gap 0.05 mm, no magnets,
fixed core), the U pads closed for 0.5 s, then the summed contact normal force of each U pad on the cubies.
Reads only; nothing is scored. Usage (WSL): python experiments/D16_free_core_m7/grip_probe.py
"""
from __future__ import annotations

import dataclasses
import importlib.util
import json
import sys
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def load_e7():
    name = "e7_scored_m7_run_for_d16"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / "experiments/E7_scored_m7/run.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def pad_forces(m, d, pad_geoms) -> dict:
    f6 = np.zeros(6)
    out = {g: 0.0 for g in pad_geoms}
    for i in range(d.ncon):
        c = d.contact[i]
        for g in pad_geoms:
            if g in (c.geom1, c.geom2):
                mujoco.mj_contactForce(m, d, i, f6)
                out[g] += f6[0]
    return out


def probe(grip_force: float, overshoot: float | None = None) -> dict:
    E7 = load_e7()
    scored = E7.scored
    E7.install(E7.EDGE_R, E7.NOSLIP)
    E7.M4.use_magnets(None, 5e-5)
    kw = {"radial_preload": 0.0, "gap": 5e-5, "grip_force": grip_force}
    if overshoot is not None:
        kw["grip_overshoot"] = overshoot
    p = scored.M1Params(**kw)
    tr = scored.Trial(p, None)
    m, d = tr.model, tr.sim.d
    a, b, _ = tr.rig.act["U"]
    d.ctrl[a] = d.ctrl[b] = tr.rig.close_target
    tr.sim.step(int(round(0.5 / m.opt.timestep)))
    gid = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, n)  # noqa: E731
    pads = [gid("pad_Ua_g"), gid("pad_Ub_g")]
    f = pad_forces(m, d, pads)
    return {"grip_force_requested_N": grip_force, "grip_overshoot_m": p.grip_overshoot, "grip_kp": p.grip_kp,
            "actuator_force_N": [float(d.actuator_force[a]), float(d.actuator_force[b])],
            "pad_normal_force_N": [float(f[g]) for g in pads],
            "kp_x_overshoot_N": p.grip_kp * p.grip_overshoot}


if __name__ == "__main__":
    rows = [probe(F) for F in (10.0, 16.5, 20.0, 30.0, 50.0)] + [probe(50.0, overshoot=0.03)]
    for r in rows:
        print(json.dumps(r))
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "grip_probe.json").write_text(json.dumps(rows, indent=1))
