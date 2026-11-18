"""ER1 probe 4 (static geometry, no dynamics): free rotation allowed by the M5 piece play.
Aligned M5 cube (B1, gap 0.05 mm). A group of pieces is rotated rigidly about an axis through the cube centre while
every other piece stays aligned; the free angle is the largest angle (each sign) before any cubie-cubie signed distance
(mj_geomDistance) between a moved and an unmoved piece falls below 0. Writes results/probe_play.json."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
spec = importlib.util.spec_from_file_location("d10_rest", REPO / "experiments/D10_m5_rest_diagnostic/d10_rest.py")
D10 = importlib.util.module_from_spec(spec); sys.modules["d10_rest"] = D10; spec.loader.exec_module(D10)
from rubiknetic.cube_logic import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml, cubie_name  # noqa: E402

M5 = D10._load_m5()
p = M1Params(**{**M5.M4.BASE_OVERRIDES, "gap": M5.GAP})
m = mujoco.MjModel.from_xml_string(build_m1_xml(p))
d = mujoco.MjData(m)
NAMES = [cubie_name(h) for h in HOME_POSITIONS]
GEOM = {n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, n + "_g") for n in NAMES}
JNT = {n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n + "_j") for n in NAMES}
HOME = {n: np.array(h) for n, h in zip(NAMES, HOME_POSITIONS)}


def set_group(group, axis, deg):
    mujoco.mj_resetData(m, d)
    q = np.zeros(4); mujoco.mju_axisAngle2Quat(q, np.asarray(axis, float) / np.linalg.norm(axis), np.radians(deg))
    for n in group:
        j = JNT[n]; adr = m.jnt_qposadr[j]
        if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_BALL:
            qn = np.zeros(4); mujoco.mju_mulQuat(qn, q, d.qpos[adr:adr + 4].copy()); d.qpos[adr:adr + 4] = qn
        else:   # centre hinge: only rotation about its own axis is representable
            d.qpos[adr] += np.radians(deg) * float(np.dot(m.jnt_axis[j], axis) / np.linalg.norm(axis))
    mujoco.mj_kinematics(m, d)


def min_dist(group):
    others = [n for n in NAMES if n not in group]
    best = (np.inf, None)
    ft = np.zeros(6)
    for a in group:
        for b in others:
            if np.abs(HOME[a] - HOME[b]).sum() > 2:   # only face- or edge-adjacent pairs can touch
                continue
            dist = mujoco.mj_geomDistance(m, d, GEOM[a], GEOM[b], 0.002, ft)
            if dist < best[0]:
                best = (dist, (a, b))
    return best


def free_angle(group, axis, sign):
    lo, hi = 0.0, 5.0
    set_group(group, axis, sign * hi)
    if min_dist(group)[0] >= 0:
        return hi, None
    for _ in range(40):
        mid = (lo + hi) / 2
        set_group(group, axis, sign * mid)
        (lo, hi) = (mid, hi) if min_dist(group)[0] >= 0 else (lo, mid)
    set_group(group, axis, sign * hi)
    return lo, min_dist(group)[1]


CASES = [
    ("corner nnp alone, about U (z)", ["cubie_nnp"], (0, 0, 1)),
    ("edge n0p alone, about U (z)", ["cubie_n0p"], (0, 0, 1)),
    ("pair nnp + n0p, about U (z)", ["cubie_nnp", "cubie_n0p"], (0, 0, 1)),
    ("row nnp + n0p + npp, about U (z)", ["cubie_nnp", "cubie_n0p", "cubie_npp"], (0, 0, 1)),
    ("corner nnp alone, twist about its diagonal", ["cubie_nnp"], (-1, -1, 1)),
    ("corner nnp alone, about L (x)", ["cubie_nnp"], (1, 0, 0)),
    ("whole U layer, about U (z)", [n for n in NAMES if HOME[n][2] == 1], (0, 0, 1)),
]
if __name__ == "__main__":
    mujoco.mj_resetData(m, d); mujoco.mj_kinematics(m, d)
    res = []
    for label, grp, ax in CASES:
        r = {"case": label, "group": grp, "axis": ax}
        for s in (+1, -1):
            a, pair = free_angle(grp, ax, s)
            r["free_deg_" + ("pos" if s > 0 else "neg")] = a
            r["blocking_pair_" + ("pos" if s > 0 else "neg")] = pair
        res.append(r)
        print(f"{label:45s} +{r['free_deg_pos']:.3f} / -{r['free_deg_neg']:.3f} deg   blocked by {r['blocking_pair_pos']} / {r['blocking_pair_neg']}")
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "probe_play.json").write_text(json.dumps({"env": D10.environment(), "gap_m": p.gap,
                                                                    "chamfer_m": p.chamfer, "cases": res}, indent=1))
