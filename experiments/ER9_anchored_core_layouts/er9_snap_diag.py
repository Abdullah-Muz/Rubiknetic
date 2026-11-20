"""ER9 probe, reported item: each piece's leftover rotation after a snap-back, for a probe arm. The method is ER7's
posthoc/snap_diag.py (one replay of d8_1b_stage1.run_snap's steps, read-only), with the arm's layout installed.
Usage (WSL, repo root):  python er9_snap_diag.py ARM SEED DELTA    (ARM = S1 | S2 | C52)
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
spec = importlib.util.spec_from_file_location("er9_probe", HERE / "er9_probe.py")
P = importlib.util.module_from_spec(spec); sys.modules["er9_probe"] = P; spec.loader.exec_module(P)
E7, M4, R = P.E7, P.M4, P.R
scored, ST = E7.scored, M4.ST
from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_logic.notation import FACE_NORMAL  # noqa: E402
from rubiknetic.cube_physics.m1_model import cubie_name  # noqa: E402

arm, seed, delta = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
cfg = P.C52_CFG if arm == "C52" else P.arms()[arm]
E7.set_seeds(E7.ER7_GLOBALS)
P.configure(cfg)
E7.setup_arm("C52")
ms = M4.use_magnets(R.magnet_params_for({}), R.GAP)
ms.reset_neighbour_list(); ms.reset_stats()
setup = scored.draw_setup(seed, ST.SETUP_MISALIGN)
tr = scored.Trial(scored.params_for(setup), setup)
m, d, ro = tr.model, tr.sim.d, tr.ro
nrm = np.array(FACE_NORMAL["U"], float)
cubies = {mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, cubie_name(h)) for h in HOME_POSITIONS}


def state(tag):
    mujoco.mj_forward(m, d)
    n_cc, normal, w = 0, 0.0, np.zeros(6)
    for i in range(d.ncon):
        c = d.contact[i]
        if m.geom_bodyid[c.geom1] in cubies and m.geom_bodyid[c.geom2] in cubies:
            mujoco.mj_contactForce(m, d, i, w)
            n_cc += 1
            normal += float(w[0])
    pieces = {}
    for h in HOME_POSITIONS:
        b = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, cubie_name(h))
        qw, qx, qy, qz = d.xquat[b]
        rv = np.degrees(Rotation.from_quat([qx, qy, qz, qw]).as_rotvec())
        u = np.array(h, float) / np.linalg.norm(h)
        spin = float(rv @ u)
        pieces[cubie_name(h)] = {"kind": {1: "centre", 2: "edge", 3: "corner"}[int(np.count_nonzero(h))],
                                 "in_U_layer": bool(int(np.dot(h, nrm)) == 1), "about_U_deg": float(rv @ nrm),
                                 "spin_about_own_axis_deg": spin,
                                 "tangential_deg": float(np.linalg.norm(rv - spin * u))}
    return {"tag": tag, "t": round(d.time, 3), "U_err_deg": ST.layer_error(ro, d, "U"),
            "cubie_cubie": {"n": n_cc, "normal_N": normal}, "max_abs_qvel": float(np.abs(d.qvel).max()),
            "pieces": pieces}


out = {"arm": arm, "config": cfg, "n_magnets": ms.n, "seed": seed, "delta_deg": delta, "states": [state("t0")]}
tr.rig.rotate({"U": np.radians(delta)}, grip=True, timing=tr.timing)
out["states"].append(state("after_release"))
tr.sim.step(int(round(1.0 / m.opt.timestep)))
out["states"].append(state("after_1s"))
out["magnet_stats"] = dict(ms.stats)
print(json.dumps(out, indent=1, default=float))
