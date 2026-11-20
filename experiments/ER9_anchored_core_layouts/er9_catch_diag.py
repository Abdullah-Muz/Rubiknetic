"""ER9 diagnostic (exploratory, unscored): what catches at about 7 degrees into a quarter turn of U?
Replays the first move of an E1-2 trial for one arm and, at the step with the largest piece-to-piece contact force,
lists the contacts that carry it and each U-layer piece's rotation relative to a rigid rotation of the layer.
Usage: python er9_catch_diag.py ARM SEED
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
    if arm.startswith("H"):                                  # hybrid: M5's 48 magnets + anchors, clearance in mm
        spec = importlib.util.spec_from_file_location("er9_hybrid", HERE / "er9_hybrid.py")
        HY = importlib.util.module_from_spec(spec); sys.modules["er9_hybrid"] = HY; spec.loader.exec_module(HY)
        HY.configure(HY.cfg_for(float(arm[1:])))
    elif arm.startswith("X"):                                  # ad hoc: S1 geometry, N35, strength scale after the X
        cfg = {**P.arms()["W1"], "scale": float(arm[1:]), "variant": f"N35 x {arm[1:]} (ad hoc)"}
    else:
        cfg = P.C52_CFG if arm == "C52" else P.arms()[arm]
    if not arm.startswith("H"):
        P.configure(cfg)
    E7.setup_arm("C52")
ms = M4.use_magnets(R.magnet_params_for({}), R.GAP)
ms.reset_neighbour_list(); ms.reset_stats()
setup = scored.draw_setup(seed)
tr = scored.Trial(scored.params_for(setup), setup)
m, d, ro = tr.model, tr.sim.d, tr.ro
names = {mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, cubie_name(h)): (cubie_name(h), h) for h in HOME_POSITIONS}
best = {"normal": -1.0}


def hook(dd):
    w, tot, rows = np.zeros(6), 0.0, []
    for i in range(dd.ncon):
        c = dd.contact[i]
        b1, b2 = m.geom_bodyid[c.geom1], m.geom_bodyid[c.geom2]
        if b1 in names and b2 in names:
            mujoco.mj_contactForce(m, dd, i, w)
            tot += float(w[0])
            rows.append((float(w[0]), names[b1][0], names[b2][0], [float(x) * 1e3 for x in c.pos],
                         [float(x) for x in c.frame[:3]], float(c.dist) * 1e3))
    if tot > best["normal"]:
        turner = float(np.degrees(dd.qpos[tr.rig.hinge_qadr["U"]]))
        pieces = {}
        for b, (nm, h) in names.items():
            if h[2] != 1:
                continue
            qw, qx, qy, qz = dd.xquat[b]
            rel = Rotation.from_euler("z", -turner, degrees=True) * Rotation.from_quat([qx, qy, qz, qw])
            rv = np.degrees(rel.as_rotvec())
            pieces[nm] = {"lag_about_z_deg": float(rv[2]), "tilt_deg": float(np.hypot(rv[0], rv[1])),
                          "tilt_axis_xy": [float(rv[0]), float(rv[1])]}
        best.update(normal=tot, t=float(dd.time), turner_deg=turner,
                    torque=float(dd.actuator_force[tr.rig.act["U"][2]]),
                    top=sorted(rows, reverse=True)[:8], n=len(rows), pieces=pieces)


tr.sim.hooks.append(hook)
tr.rig.turn(parse("U")[0], tr.timing)
print(json.dumps({"arm": arm, "seed": seed, **best}, default=float))
