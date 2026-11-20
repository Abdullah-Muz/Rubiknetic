"""ER9 diagnostic (exploratory, unscored): the turner torque through one quarter turn of U, for one arm.
Replays the first move of an E1-2 trial (setup, grip, turn) and prints the turner torque, the turner angle and the
U layer's actual angle through the turn.   Usage: python er9_turn_diag.py ARM SEED   (ARM = L0 | C52 | S1 | W1 ...)
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("er9_probe", HERE / "er9_probe.py")
P = importlib.util.module_from_spec(spec); sys.modules["er9_probe"] = P; spec.loader.exec_module(P)
E7, M4, R = P.E7, P.M4, P.R
scored, ST = E7.scored, M4.ST
from rubiknetic.cube_logic import parse  # noqa: E402
from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_physics.m1_model import cubie_name  # noqa: E402

arm, seed = sys.argv[1], int(sys.argv[2])
E7.set_seeds(E7.ER7_GLOBALS)
if arm == "L0":
    E7.setup_arm("L0")
else:
    P.configure(P.C52_CFG if arm == "C52" else P.arms()[arm])
    E7.setup_arm("C52")
ms = M4.use_magnets(R.magnet_params_for({}), R.GAP)
ms.reset_neighbour_list(); ms.reset_stats()
setup = scored.draw_setup(seed)
tr = scored.Trial(scored.params_for(setup), setup)
m, d, ro = tr.model, tr.sim.d, tr.ro
cubies = {mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, cubie_name(h)) for h in HOME_POSITIONS}
samples = []


def hook(dd):
    if tr.sim.steps % 20:
        return
    n_cc, n_pad, normal_cc, normal_pad, w = 0, 0, 0.0, 0.0, np.zeros(6)
    for i in range(dd.ncon):
        c = dd.contact[i]
        mujoco.mj_contactForce(m, dd, i, w)
        if m.geom_bodyid[c.geom1] in cubies and m.geom_bodyid[c.geom2] in cubies:
            n_cc += 1; normal_cc += float(w[0])
        else:
            n_pad += 1; normal_pad += float(w[0])
    samples.append({"t": float(dd.time), "torque": float(dd.actuator_force[tr.rig.act["U"][2]]),
                    "turner_deg": float(np.degrees(dd.qpos[tr.rig.hinge_qadr["U"]])),
                    "layer_err_deg": float(ST.layer_error(ro, dd, "U")), "n_cc": n_cc, "normal_cc_N": normal_cc,
                    "n_pad": n_pad, "normal_pad_N": normal_pad})


tr.sim.hooks.append(hook)
t_start = d.time
log = tr.rig.turn(parse("U")[0], tr.timing)
tq = np.abs(np.array(log.turner_torque))
k = int(np.argmax(tq))
out = {"arm": arm, "seed": seed, "grip_force_N": getattr(setup, "grip_force", None),
       "turn_s_per_quarter": tr.timing.turn_s_per_quarter, "peak_torque_Nm": float(tq.max()),
       "t_peak_from_start_s": float(log.t[k] - t_start), "turner_deg_at_peak": float(log.turner_angle_deg[k]),
       "fraction_of_steps_at_clip": float(np.mean(tq >= 0.999)),
       "final_layer_err_deg": float(ST.layer_error(ro, d, "U")), "samples": samples}
print(json.dumps(out, default=float))
