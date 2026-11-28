"""D23 probe: model facts needed for the admittance experiment (no simulation beyond build)."""
import sys, time
from pathlib import Path
import numpy as np, mujoco
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "experiments" / "E8_scored_g2"))
import trials as TR
TA = TR.TA
TR.configure({}, TR.start_draw(29001))
m, p, info, A, B, half = TA.build(TR.L, TR.HC, 0.8)
print("integrator", m.opt.integrator, "dt", m.opt.timestep, "cone", m.opt.cone, "noslip", m.opt.noslip_iterations)
for i in range(1, 8):
    a = m.actuator(f"act{i}").id
    print(f"act{i}", m.actuator_gainprm[a, :3], m.actuator_biasprm[a, :3], m.actuator_forcerange[a], m.actuator_ctrlrange[a],
          "dyntype", m.actuator_dyntype[a], "gaintype", m.actuator_gaintype[a], "biastype", m.actuator_biastype[a])
    j = m.joint(f"joint{i}").id
    v = m.jnt_dofadr[j]
    print("   joint damping", m.dof_damping[v], "fric", m.dof_frictionloss[v], "arm", m.dof_armature[v], "actgravcomp", m.jnt_actgravcomp[j])
print("B gripper body", m.body("B_xarm_gripper_base_link").id, "ft sensors", [m.sensor(i).name for i in range(m.nsensor)])
sub = [b for b in range(m.nbody) if m.body_rootid[b] == m.body("B_link_base").id]
print("ngeom", m.ngeom, "nv", m.nv)
