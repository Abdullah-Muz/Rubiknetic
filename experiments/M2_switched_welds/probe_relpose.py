"""Probe: weld eq_data layout and the relpose convention that gives ZERO violation at activation."""
import sys

import mujoco
import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from m2_model import build_m2_xml  # noqa: E402

m = mujoco.MjModel.from_xml_string(build_m2_xml())
d = mujoco.MjData(m)
print("neq", m.neq, "eq_data width", m.eq_data.shape)
eid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_EQUALITY, "w_cubie_ppp_cubie_00p")
print("default eq_data", np.round(m.eq_data[eid], 4))
# rotate the U centre hinge and the corner ppp ball joint by the same rotation about z, then
# activate the cubie->centre weld with a computed relpose and check the residual.
from scipy.spatial.transform import Rotation as Rr  # noqa: E402
ang = np.radians(37.0)
jc = m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "cubie_00p_j")]
jb = m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "cubie_ppp_j")]
d.qpos[jc] = ang * 0.5  # centre rotated 18.5 deg
x, y, z, w = Rr.from_rotvec([0, 0, ang]).as_quat()
d.qpos[jb:jb + 4] = [w, x, y, z]  # corner rotated 37 deg
d.eq_active[:] = 0
d.eq_active[eid] = 1
mujoco.mj_forward(m, d)
b1 = m.eq_obj1id[eid]
b2 = m.eq_obj2id[eid]


def residual():
    mujoco.mj_forward(m, d)
    rows = [i for i in range(d.nefc) if d.efc_type[i] == mujoco.mjtConstraint.mjCNSTR_EQUALITY and d.efc_id[i] == eid]
    return np.linalg.norm(d.efc_pos[rows])


def rel(b1, b2):
    p1, R1 = d.xpos[b1], d.xmat[b1].reshape(3, 3)
    p2, R2 = d.xpos[b2], d.xmat[b2].reshape(3, 3)
    return R1, p1, R2, p2


R1, p1, R2, p2 = rel(b1, b2)
q12 = Rr.from_matrix(R1.T @ R2).as_quat()  # body2 relative to body1
q21 = Rr.from_matrix(R2.T @ R1).as_quat()
for label, q in (("q(body2 rel body1)", q12), ("q(body1 rel body2)", q21)):
    ed = m.eq_data[eid].copy()
    ed[0:3] = 0.0                       # anchor in body2 frame
    ed[3:6] = R1.T @ (p2 - p1)          # anchor (body2 origin) in body1 frame
    ed[6:10] = [q[3], q[0], q[1], q[2]]
    m.eq_data[eid] = ed
    print(f"{label}: residual {residual():.3e}")
