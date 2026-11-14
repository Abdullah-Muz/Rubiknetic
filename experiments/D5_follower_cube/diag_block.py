"""D5 diagnostic (UNSCORED): which contacts block a perpendicular turn after a misalignment?
U is turned by `deg` with the rig and released, then R is turned with the rig. Whenever the R
turner torque is near its limit, the highest-force piece contacts are recorded and summarised by
(piece pair, geom roles).
Usage: uv run python experiments/D5_follower_cube/diag_block.py deg=6 [d5 k=v ...]"""
from __future__ import annotations

import sys
from collections import Counter

import mujoco
import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from cube_d5 import D5Params, build_xml_with_rig  # noqa: E402

from rubiknetic.cube_logic import parse  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params  # noqa: E402
from rubiknetic.cube_physics.readout import CubeReadout  # noqa: E402
from rubiknetic.cube_physics.rig import AuditedSim, TurnRig  # noqa: E402

deg = 6.0
p = D5Params(bevel_body=1.0, bevel_foot=0.5, gap=0.05, clearance=0.02, spring_preload=10.0, spring_k=2000.0,
             slide_range=(-0.001, 0.0003))
for kv in sys.argv[1:]:
    k, v = kv.split("=", 1)
    if k == "deg":
        deg = float(v)
    else:
        cur = getattr(p, k)
        setattr(p, k, type(cur)(v) if not isinstance(cur, tuple) else tuple(float(x) for x in v.split(",")))
xml, _ = build_xml_with_rig(p)
m = mujoco.MjModel.from_xml_string(xml)
sim = AuditedSim(m)
mujoco.mj_forward(m, sim.d)
ro = CubeReadout(m, 0.019)
mp = M1Params()
rig = TurnRig(sim, pad_close_target=-(mp.pad_open_clearance + mp.grip_overshoot))
d = sim.d
pad = {g for g in range(m.ngeom) if (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, g) or "").startswith("pad_")}
aR = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, "turn_R")


def role(g):
    if g in pad:
        return "RIGPAD"
    mesh = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_MESH, m.geom_dataid[g]) or ""
    b = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, m.geom_bodyid[g])
    v = m.mesh_vertnum[m.geom_dataid[g]]
    return f"{b[6:]}.{'foot' if mesh.endswith('_m0') else ('body' if v <= 16 and not mesh.endswith('_m0') else 'pad/body')}"


agg, samples = Counter(), {}
f6 = np.zeros(6)
watch = {"on": False}


def hook(dd):
    if not watch["on"] or abs(dd.actuator_force[aR]) < 0.9 * mp.turn_torque_limit:
        return
    for i in range(dd.ncon):
        c = dd.contact[i]
        mujoco.mj_contactForce(m, dd, i, f6)
        if f6[0] < 5.0:
            continue
        key = " vs ".join(sorted([role(c.geom1), role(c.geom2)]))
        agg[key] += f6[0]
        samples[key] = (np.round(c.pos * 1000, 1), np.round(c.frame[:3], 2), round(f6[0], 1))


sim.hooks.append(hook)
sim.step(int(0.3 / m.opt.timestep))
_, r0 = ro.poses(d)
U = ro.layer_members(d, "U")
rig.rotate({"U": -np.radians(deg)}, record=False)
_, r1 = ro.poses(d)
print(f"U misaligned {np.mean(CubeReadout.rotation_about_deg(r0, r1, U, 'U')):+.2f} deg (commanded {-deg:+.1f})")
R = ro.layer_members(d, "R")
watch["on"] = True
log = rig.turn(parse("R")[0])
_, r2 = ro.poses(d)
print(f"R turned {np.mean(CubeReadout.rotation_about_deg(r1, r2, R, 'R')):+.2f} deg; peak torque {np.max(np.abs(log.turner_torque)):.2f}")
print("contacts carrying load while the R turner is saturated (summed normal force over samples):")
for key, f in agg.most_common(10):
    pos, nrm, f1 = samples[key]
    print(f"  {f:10.0f}  {key:40s} e.g. at {pos} mm, normal {nrm}, {f1} N")

# --- centre hinge angles and slide positions at the end (stall) -------------------------------
from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_physics.m1_model import cubie_name  # noqa: E402
print("centre state at the end (hinge deg relative to nearest 90-deg multiple, slide mm):")
for h in HOME_POSITIONS:
    if np.count_nonzero(h) != 1:
        continue
    n = cubie_name(h)
    a = np.degrees(d.qpos[m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n + "_j")]])
    s = d.qpos[m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n + "_r")]] * 1000
    print(f"  {n[6:]}: hinge {a:+8.2f} (off-square {a - 90 * round(a / 90):+6.2f} deg), slide {s:+.3f} mm")
