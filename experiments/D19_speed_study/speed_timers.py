"""Speed study part 2 (UNSCORED, pilot seed 29001; read-only): MuJoCo's internal timers for the G2 scene after the
start sequence (arm A holding, arm B at pre-grasp), magnets off so only the C step is timed. Then what-if variants on a
COPY of the model (never used for any result): NoSlip iterations, solver iterations, and robot-cube collision filtering
are reported as candidates only."""
import importlib.util
import sys
from pathlib import Path
import copy
import time

import mujoco
import numpy as np

spec = importlib.util.spec_from_file_location("trials", Path(__file__).resolve().parents[1] / "E8_scored_g2" / "trials.py")
T = importlib.util.module_from_spec(spec)
sys.modules["trials"] = T
spec.loader.exec_module(T)
T.configure({}, T.start_draw(29001))
r = T.TA.TwoArm(T.L, T.HC, T.DEFAULTS["grip"])
T.MagnetSystem.uninstall()
mujoco.set_mjcb_time(time.perf_counter)
m, d = r.m, r.d
print(f"nq {m.nq} nv {m.nv} nbody {m.nbody} ngeom {m.ngeom} nmesh {m.nmesh} ncon now {d.ncon} nefc {d.nefc}")
print(f"opt: timestep {m.opt.timestep} solver {m.opt.solver} iterations {m.opt.iterations} ls_iter "
      f"{m.opt.ls_iterations} noslip {m.opt.noslip_iterations} cone {m.opt.cone} integrator {m.opt.integrator} "
      f"jacobian {m.opt.jacobian}")
d0 = mujoco.MjData(m)
snap = (d.qpos.copy(), d.qvel.copy(), d.act.copy(), d.ctrl.copy(), d.qacc_warmstart.copy(), d.time)


def restore(dd):
    dd.qpos[:], dd.qvel[:], dd.act[:], dd.ctrl[:], dd.qacc_warmstart[:] = snap[:5]
    dd.time = snap[5]
    mujoco.mj_forward(m, dd)


def bench(mm, n=1500, label=""):
    dd = mujoco.MjData(mm)
    dd.qpos[:], dd.qvel[:], dd.act[:], dd.ctrl[:] = snap[0], snap[1], snap[2], snap[3]
    mujoco.mj_forward(mm, dd)
    for t in dd.timer:
        t.duration, t.number = 0.0, 0
    t0 = time.perf_counter()
    for _ in range(n):
        mujoco.mj_step(mm, dd)
    rate = n / (time.perf_counter() - t0)
    tm = {mujoco.mjtTimer(i).name[8:]: dd.timer[i].duration / max(1, n) * 1e3 for i in range(len(dd.timer))}
    keep = ("STEP", "FORWARD", "POSITION", "VELOCITY", "ACTUATION", "CONSTRAINT", "POS_KINEMATICS",
            "POS_INERTIA", "POS_COLLISION", "POS_MAKE", "POS_PROJECT", "COL_BROAD", "COL_NARROW")
    print(f"{label:34s} {rate:6.0f} steps/s  ncon {dd.ncon:3d} nefc {dd.nefc:4d}  ms/step: "
          + " ".join(f"{k}={tm[k]:.2f}" for k in keep if k in tm))
    return rate


base = bench(m, label="as built")
for ns in (0, 5):
    mm = copy.copy(m)
    mm.opt.noslip_iterations = ns
    bench(mm, label=f"noslip {ns} (what-if)")
mm = copy.copy(m)
mm.opt.iterations = max(1, m.opt.iterations // 2)
bench(mm, label=f"solver iterations {mm.opt.iterations} (what-if)")
# contact count by pair class at this state
mujoco.mj_forward(m, d)
cube = set(int(g) for g in r.cubie)
cls = {"cubie-cubie": 0, "robot-robot": 0, "pad-cubie": 0, "other": 0}
for i in range(d.ncon):
    g1, g2 = int(d.contact.geom1[i]), int(d.contact.geom2[i])
    if g1 in cube and g2 in cube:
        cls["cubie-cubie"] += 1
    elif (g1 in cube) != (g2 in cube):
        cls["pad-cubie" if (g1 in set(int(x) for x in r.pads) or g2 in set(int(x) for x in r.pads)) else "other"] += 1
    else:
        cls["robot-robot"] += 1
print("contacts by class:", cls)
