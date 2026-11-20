"""Post-hoc diagnostic (exploratory, unscored): what balances the magnets' restoring torque on a layer at rest?

For each arm (L0 = M5 magnets, C52 = core layout), on one ER7 rest seed: build the trial exactly as the rest trial
does, step briefly, then split the generalized constraint force into joint friction-loss rows and contact rows and
project each, with the magnet force, onto a rigid rotation of each face layer about its axis.
Usage: python er7_stick_diag.py ARM SEED
"""
import importlib.util
import json
import sys
from pathlib import Path

import mujoco
import numpy as np

REPO = Path("/mnt/c/dev/Rubiknetic")
arm, seed = sys.argv[1], int(sys.argv[2])
spec = importlib.util.spec_from_file_location("er7_run", REPO / "experiments/ER7_core_magnet_rehearsal/er7_run.py")
E7 = importlib.util.module_from_spec(spec); sys.modules["er7_run"] = E7; spec.loader.exec_module(E7)
M4, R, scored = E7.M4, E7.R, E7.scored
from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES  # noqa: E402
from rubiknetic.cube_physics.m1_model import cubie_name  # noqa: E402

E7.set_seeds(E7.ER7_GLOBALS)
E7.setup_arm(arm)
ms = M4.use_magnets(R.magnet_params_for({}), R.GAP)
ms.reset_neighbour_list(); ms.reset_stats()
setup = scored.draw_setup(seed)
tr = scored.Trial(scored.params_for(setup), setup)
m, d = tr.model, tr.sim.d
m.opt.jacobian = mujoco.mjtJacobian.mjJAC_DENSE
out = {"arm": arm, "seed": seed, "misalign_deg": {k: round(v, 3) for k, v in setup.misalign_deg.items()}}


def layer_dofs(face):
    """Generalized velocity of a rigid unit-rate rotation of the face layer about its outward normal."""
    nrm = np.array(FACE_NORMAL[face], float)
    v = np.zeros(m.nv)
    for h in HOME_POSITIONS:
        if int(np.dot(h, nrm)) != 1:
            continue
        j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, cubie_name(h) + "_j")
        a = m.jnt_dofadr[j]
        if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_BALL:
            b = m.jnt_bodyid[j]
            v[a:a + 3] = d.xmat[b].reshape(3, 3).T @ nrm        # ball dofs are in the body frame
        else:
            v[a] = float(np.dot(np.array(h, float) / np.linalg.norm(h), nrm))
    return v


def snapshot(tag):
    mujoco.mj_forward(m, d)
    J = d.efc_J.reshape(d.nefc, m.nv) if d.nefc else np.zeros((0, m.nv))
    f = d.efc_force[:d.nefc]
    typ = d.efc_type[:d.nefc]
    fric = typ == mujoco.mjtConstraint.mjCNSTR_FRICTION_DOF
    con = np.isin(typ, [mujoco.mjtConstraint.mjCNSTR_CONTACT_FRICTIONLESS, mujoco.mjtConstraint.mjCNSTR_CONTACT_PYRAMIDAL,
                        mujoco.mjtConstraint.mjCNSTR_CONTACT_ELLIPTIC])
    q_fric, q_con = J[fric].T @ f[fric], J[con].T @ f[con]
    q_mag = np.zeros(m.nv)
    keep = d.qfrc_passive.copy()
    d.qfrc_passive[:] = 0.0
    ms.apply(m, d)
    q_mag = d.qfrc_passive.copy()
    d.qfrc_passive[:] = keep
    normal, wrench = 0.0, np.zeros(6)
    for i in range(d.ncon):
        mujoco.mj_contactForce(m, d, i, wrench)
        normal += wrench[0]
    rows = {}
    for face in FACES:
        v = layer_dofs(face)
        rows[face] = {"magnet_Nm": float(v @ q_mag), "joint_friction_Nm": float(v @ q_fric),
                      "contact_Nm": float(v @ q_con), "other_passive_Nm": float(v @ (d.qfrc_passive - q_mag))}
    _, rot = tr.ro.poses(d)
    out[tag] = {"t": d.time, "ncon": int(d.ncon), "sum_contact_normal_N": normal,
                "n_friction_rows": int(fric.sum()), "n_contact_rows": int(con.sum()),
                "max_abs_qvel": float(np.abs(d.qvel).max()), "layers": rows}


snapshot("t0")
tr.sim.step(1000)                                             # 0.5 s
snapshot("t0.5s")
tr.sim.step(3000)                                             # to 2.0 s
snapshot("t2s")
print(json.dumps(out, indent=1))
