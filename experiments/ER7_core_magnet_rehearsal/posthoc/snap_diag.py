"""Post-hoc diagnostic (exploratory, unscored): in the E1-5s snap-back trial, what holds the U layer where it stops?
Replays d8_1b_stage1.run_snap's steps for one ER7 seed and arm, then splits the torque about the U axis into
magnets, joint friction, cubie-cubie contacts and rig (pad) contacts.  Usage: python er7_snap_diag.py ARM SEED DELTA
"""
import importlib.util
import json
import sys
from pathlib import Path

import mujoco
import numpy as np

REPO = Path("/mnt/c/dev/Rubiknetic")
arm, seed, delta = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
spec = importlib.util.spec_from_file_location("er7_run", REPO / "experiments/ER7_core_magnet_rehearsal/er7_run.py")
E7 = importlib.util.module_from_spec(spec); sys.modules["er7_run"] = E7; spec.loader.exec_module(E7)
M4, R, scored = E7.M4, E7.R, E7.scored
ST = M4.ST
from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_logic.notation import FACE_NORMAL  # noqa: E402
from rubiknetic.cube_physics.m1_model import cubie_name  # noqa: E402

E7.set_seeds(E7.ER7_GLOBALS)
E7.setup_arm(arm)
ms = M4.use_magnets(R.magnet_params_for({}), R.GAP)
ms.reset_neighbour_list(); ms.reset_stats()
setup = scored.draw_setup(seed, ST.SETUP_MISALIGN)
tr = scored.Trial(scored.params_for(setup), setup)
m, d, ro = tr.model, tr.sim.d, tr.ro
m.opt.jacobian = mujoco.mjtJacobian.mjJAC_DENSE
cubie_bodies = {mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, cubie_name(h)) for h in HOME_POSITIONS}
nrm = np.array(FACE_NORMAL["U"], float)


def v_layer():
    v = np.zeros(m.nv)
    for h in HOME_POSITIONS:
        if int(np.dot(h, nrm)) != 1:
            continue
        j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, cubie_name(h) + "_j")
        a = m.jnt_dofadr[j]
        if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_BALL:
            v[a:a + 3] = d.xmat[m.jnt_bodyid[j]].reshape(3, 3).T @ nrm
        else:
            v[a] = float(np.dot(np.array(h, float) / np.linalg.norm(h), nrm))
    return v


def pieces():
    """Each U-layer piece: its rotation from home (deg), split into spin about its own radial axis (the axis of its
    magnet pair in the core layout) and the tangential rest; and the rotation about the U axis."""
    from scipy.spatial.transform import Rotation
    out = {}
    for h in HOME_POSITIONS:
        if int(np.dot(h, nrm)) != 1:
            continue
        b = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, cubie_name(h))
        w, x, y, z = d.xquat[b]
        rv = np.degrees(Rotation.from_quat([x, y, z, w]).as_rotvec())
        u = np.array(h, float) / np.linalg.norm(h)
        spin = float(rv @ u)
        out[cubie_name(h)] = {"kind": {1: "centre", 2: "edge", 3: "corner"}[int(np.count_nonzero(h))],
                              "about_U_deg": float(rv @ nrm), "spin_about_own_axis_deg": spin,
                              "tangential_deg": float(np.linalg.norm(rv - spin * u))}
    return out


def snap(tag):
    mujoco.mj_forward(m, d)
    J = d.efc_J.reshape(d.nefc, m.nv) if d.nefc else np.zeros((0, m.nv))
    f, typ = d.efc_force[:d.nefc], d.efc_type[:d.nefc]
    v = v_layer()
    fric = typ == mujoco.mjtConstraint.mjCNSTR_FRICTION_DOF
    keep = d.qfrc_passive.copy()
    d.qfrc_passive[:] = 0.0
    ms.apply(m, d)
    q_mag = d.qfrc_passive.copy()
    d.qfrc_passive[:] = keep
    cc = {"n": 0, "normal_N": 0.0, "torque_Nm": 0.0}
    rig = {"n": 0, "normal_N": 0.0, "torque_Nm": 0.0}
    w = np.zeros(6)
    for i in range(d.ncon):
        c = d.contact[i]
        if c.efc_address < 0:
            continue
        b1, b2 = m.geom_bodyid[c.geom1], m.geom_bodyid[c.geom2]
        rows = slice(c.efc_address, c.efc_address + (c.dim if m.opt.cone == mujoco.mjtCone.mjCONE_ELLIPTIC
                                                      else 2 * (c.dim - 1)))
        mujoco.mj_contactForce(m, d, i, w)
        tgt = cc if (b1 in cubie_bodies and b2 in cubie_bodies) else rig
        tgt["n"] += 1
        tgt["normal_N"] += float(w[0])
        tgt["torque_Nm"] += float(v @ (J[rows].T @ f[rows]))
    con_all = np.isin(typ, [mujoco.mjtConstraint.mjCNSTR_CONTACT_FRICTIONLESS,
                            mujoco.mjtConstraint.mjCNSTR_CONTACT_PYRAMIDAL, mujoco.mjtConstraint.mjCNSTR_CONTACT_ELLIPTIC])
    return {"tag": tag, "t": round(d.time, 3), "U_err_deg": ST.layer_error(ro, d, "U"),
            "magnet_Nm": float(v @ q_mag), "joint_friction_Nm": float(v @ (J[fric].T @ f[fric])),
            "all_contacts_Nm": float(v @ (J[con_all].T @ f[con_all])), "cubie_cubie": cc, "rig_or_core": rig,
            "actuator_Nm": float(v @ d.qfrc_actuator), "max_abs_qvel": float(np.abs(d.qvel).max()),
            "misalignment": ST.misalignment(ro, d), "pieces": pieces()}


out = {"arm": arm, "seed": seed, "delta_deg": delta, "states": [snap("t0")]}
tr.rig.rotate({"U": np.radians(delta)}, grip=True, timing=tr.timing)
out["states"].append(snap("after_release"))
tr.sim.step(int(round(1.0 / m.opt.timestep)))
out["states"].append(snap("after_1s"))
tr.sim.step(int(round(4.0 / m.opt.timestep)))
out["states"].append(snap("after_5s"))
print(json.dumps(out, indent=1, default=float))
