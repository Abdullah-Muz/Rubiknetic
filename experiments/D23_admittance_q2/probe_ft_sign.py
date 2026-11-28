"""D23 probe: sign convention of the modelled wrist F/T force sensor (standalone arm B, no cube)."""
import sys
from pathlib import Path
import numpy as np, mujoco
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "experiments" / "E8_scored_g2"))
import trials as TR
TA = TR.TA
sp = TA.b_robot_spec()
for k in list(sp.keys):
    sp.delete(k)
m = sp.compile()
d = mujoco.MjData(m)
q0 = np.array([0, -0.247, 0, 0.909, 0, 1.15644, 0])
qa = [m.jnt_qposadr[m.joint(f"joint{i}").id] for i in range(1, 8)]
d.qpos[qa] = q0
d.ctrl[:7] = q0
b = m.body("xarm_gripper_base_link").id
s = m.site("ft_site").id
fa = m.sensor_adr[m.sensor("ft_force").id]
def run(n, F):
    d.xfrc_applied[b, :3] = F
    for _ in range(n):
        mujoco.mj_step(m, d)
    return d.site_xmat[s].reshape(3, 3) @ d.sensordata[fa:fa + 3]
f0 = run(4000, [0, 0, 0])
f1 = run(4000, [10.0, 0, 0])
f2 = run(4000, [0, 0, 10.0])
sub = m.body_subtreemass[b]
print("subtree mass", sub, "m*g", sub * 9.81)
print("free (world):", f0.round(3))
print("+10 N x applied, delta:", (f1 - f0).round(3))
print("+10 N z applied, delta:", (f2 - f0).round(3))
