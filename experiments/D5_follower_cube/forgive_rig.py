"""D5 dynamic forgiveness with the M1 pad rig (UNSCORED): U is turned by -d deg with the rig
(grip, rotate, release; contact-driven), then R is turned with the rig. Reports whether R completes
and how much U moved back during the R turn (cam action).
Usage: uv run python experiments/D5_follower_cube/forgive_rig.py degs=0,1,2,3,5,8 [d5 k=v ...]"""
from __future__ import annotations

import sys

import mujoco
import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from cube_d5 import D5Params, build_xml_with_rig  # noqa: E402

from rubiknetic.cube_logic import parse  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params  # noqa: E402
from rubiknetic.cube_physics.readout import CubeReadout  # noqa: E402
from rubiknetic.cube_physics.rig import AuditedSim, EditAuditError, NumericalFailure, TurnRig  # noqa: E402


def run(p: D5Params, deg: float, m1o: dict) -> str:
    xml, _ = build_xml_with_rig(p, m1o)
    m = mujoco.MjModel.from_xml_string(xml)
    import os
    import detent  # P-16 core-centre detent (0 = off)
    detent.install(m, float(os.environ.get("D5_DETENT", "0")))
    sim = AuditedSim(m)
    mujoco.mj_forward(m, sim.d)
    ro = CubeReadout(m, 0.019)
    mp = M1Params(**m1o)
    rig = TurnRig(sim, pad_close_target=-(mp.pad_open_clearance + mp.grip_overshoot))
    d = sim.d
    sim.step(int(0.3 / m.opt.timestep))
    _, r0 = ro.poses(d)
    U = ro.layer_members(d, "U")
    try:
        if deg:
            rig.rotate({"U": -np.radians(deg)}, record=False)
        _, r1 = ro.poses(d)
        u_mis = float(np.mean(CubeReadout.rotation_about_deg(r0, r1, U, "U")))
        R = ro.layer_members(d, "R")
        Uonly = [i for i in U if i not in R]
        log = rig.turn(parse("R")[0])
    except (NumericalFailure, EditAuditError) as e:
        return f"ABORT {e}"
    _, r2 = ro.poses(d)
    angR = float(np.mean(CubeReadout.rotation_about_deg(r1, r2, R, "R")))
    u_back = float(np.mean(CubeReadout.rotation_about_deg(r1, r2, Uonly, "U")))
    obs = ro.observe(d)
    return (f"U misaligned {u_mis:+6.2f} deg -> R turned {angR:+7.2f} deg | U moved {u_back:+6.2f} deg during R | "
            f"peak R torque {np.max(np.abs(log.turner_torque)):.2f} N.m | observed valid {obs.valid}")


if __name__ == "__main__":
    degs = [0, 1, 2, 3, 5, 8]
    p = D5Params(bevel_body=1.0, bevel_foot=0.5, gap=0.05, clearance=0.02, spring_preload=10.0, spring_k=2000.0,
                 slide_range=(-0.001, 0.0003), pad_spacing_deg=20.0, sphere_spacing_mm=2.0)
    m1o = {}
    for kv in sys.argv[1:]:
        k, v = kv.split("=", 1)
        if k == "degs":
            degs = [float(x) for x in v.split(",")]
        elif k.startswith("m1."):
            m1o[k[3:]] = type(getattr(M1Params(), k[3:]))(v)
        else:
            cur = getattr(p, k)
            setattr(p, k, type(cur)(v) if not isinstance(cur, tuple) else tuple(float(x) for x in v.split(",")))
    print(f"bevel body {p.bevel_body} foot {p.bevel_foot}, friction {p.friction}, spring {p.spring_preload} N, m1 {m1o}")
    for dg in degs:
        print(f"  d={dg:4.1f}: {run(p, dg, m1o)}", flush=True)
