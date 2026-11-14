"""D5 stage-1 geometry-only checks on the exact MuJoCo collision geometry (no dynamics).

Poses are set directly for geometry queries only (this is not an evaluation run).
  1. rest: min distance between neighbouring pieces (expect ~gap at planes, ~clearance at pads)
  2. sweeps: each of the 6 faces turned 0..90 deg in 1-deg steps; min distance moving vs fixed
  3. capture: each piece type moved outward / twisted / tilted with everything else fixed
  4. forgiveness (kinematic): U pre-rotated by d deg, then R swept; first d that blocks R
Usage (WSL2, repo root): uv run python experiments/D5_follower_cube/kin_check.py [key=value ...]
"""
from __future__ import annotations

import sys
import time

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from cube_d5 import D5Params, build_xml  # noqa: E402

from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES  # noqa: E402
from rubiknetic.cube_physics.m1_model import cubie_name  # noqa: E402

MARGIN = 0.003  # 3 mm detection margin so separated pairs report distances


def make(p: D5Params):
    p.margin = MARGIN
    xml, info = build_xml(p, actuated_centres=False)
    m = mujoco.MjModel.from_xml_string(xml)
    return m, mujoco.MjData(m), info


class Poser:
    def __init__(self, m, d, p):
        self.m, self.d, self.p = m, d, p
        self.bid = {cubie_name(h): mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, cubie_name(h)) for h in HOME_POSITIONS}
        self.home = {cubie_name(h): np.array(h, float) for h in HOME_POSITIONS}

    def reset(self):
        self.d.qpos[:] = self.m.qpos0

    def rotate(self, names, R: np.ndarray):
        for n in names:
            h = self.home[n]
            b = self.bid[n]
            jid = self.m.body_jntadr[b]
            adr = self.m.jnt_qposadr[jid]
            if np.count_nonzero(h) == 1:  # centre: hinge angle about its own axis
                ang = Rotation.from_matrix(R).as_rotvec() @ h
                self.d.qpos[adr] = ang
            else:
                pos0 = self.m.qpos0[adr:adr + 3]
                self.d.qpos[adr:adr + 3] = R @ pos0
                x, y, z, w = Rotation.from_matrix(R).as_quat()
                self.d.qpos[adr + 3:adr + 7] = [w, x, y, z]

    def translate(self, name, dv):
        b = self.bid[name]
        adr = self.m.jnt_qposadr[self.m.body_jntadr[b]]
        self.d.qpos[adr:adr + 3] = self.m.qpos0[adr:adr + 3] + dv

    def set_rot_about_own(self, name, R):
        b = self.bid[name]
        adr = self.m.jnt_qposadr[self.m.body_jntadr[b]]
        x, y, z, w = Rotation.from_matrix(R).as_quat()
        self.d.qpos[adr + 3:adr + 7] = [w, x, y, z]


def min_dist(m, d, set_a, set_b=None):
    """min contact distance (mm) between bodies in set_a and bodies in set_b (default: all others)."""
    mujoco.mj_kinematics(m, d)
    mujoco.mj_collision(m, d)
    best, pair = np.inf, None
    for i in range(d.ncon):
        c = d.contact[i]
        b1, b2 = m.geom_bodyid[c.geom1], m.geom_bodyid[c.geom2]
        n1 = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b1)
        n2 = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b2)
        in1, in2 = n1 in set_a, n2 in set_a
        if set_b is None:
            ok = in1 != in2
        else:
            ok = (in1 and n2 in set_b) or (in2 and n1 in set_b)
        if ok and c.dist < best:
            best, pair = c.dist, (n1, n2)
    return best * 1000, pair


def layer(face):
    n = np.array(FACE_NORMAL[face])
    return [cubie_name(h) for h in HOME_POSITIONS if np.dot(h, n) == 1]


def main():
    p = D5Params()
    for kv in sys.argv[1:]:
        k, v = kv.split("=")
        setattr(p, k, type(getattr(p, k))(v))
    t = time.perf_counter()
    m, d, info = make(p)
    print(f"built in {time.perf_counter() - t:.1f}s: ngeom {m.ngeom}; geoms per piece: "
          f"corner {info['cubie_ppp']['n_geoms']}, edge {info['cubie_pp0']['n_geoms']}, centre {info['cubie_00p']['n_geoms']}")
    P = Poser(m, d, p)
    allp = list(P.bid)

    # 1. rest
    P.reset()
    mujoco.mj_kinematics(m, d)
    mujoco.mj_collision(m, d)
    rows = {}
    for i in range(d.ncon):
        c = d.contact[i]
        n1 = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, m.geom_bodyid[c.geom1])
        n2 = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, m.geom_bodyid[c.geom2])
        k1 = {1: "centre", 2: "edge", 3: "corner"}[sum(ch != "0" for ch in n1[6:])]
        k2 = {1: "centre", 2: "edge", 3: "corner"}[sum(ch != "0" for ch in n2[6:])]
        key = "-".join(sorted([k1, k2]))
        rows[key] = min(rows.get(key, np.inf), c.dist * 1000)
    print("1. REST min distance by pair type (mm):", {k: round(v, 3) for k, v in sorted(rows.items())})

    # 2. sweeps
    print("2. SWEEPS (min clearance moving vs fixed over 0..90 deg, 1-deg steps):")
    for face in FACES:
        mv = layer(face)
        n = np.array(FACE_NORMAL[face], float)
        worst = (np.inf, None, None)
        for ang in range(0, 91):
            P.reset()
            P.rotate(mv, Rotation.from_rotvec(-np.radians(ang) * n).as_matrix())
            dd, pr = min_dist(m, d, set(mv))
            if dd < worst[0]:
                worst = (dd, ang, pr)
        print(f"   {face}: min {worst[0]:+.3f} mm at {worst[1]} deg {worst[2]}")

    # 3. capture
    print("3. CAPTURE (others fixed): first contact distance when moving the piece")
    for name in ("cubie_ppp", "cubie_pp0"):
        h = P.home[name]
        u = h / np.linalg.norm(h)
        for label, dv in (("outward", u), ("inward", -u)):
            res = []
            for s in (0.02, 0.05, 0.1, 0.2, 0.5):
                P.reset()
                P.translate(name, dv * s / 1000)
                res.append(f"{s}:{min_dist(m, d, {name})[0]:+.3f}")
            print(f"   {name} {label}: " + "  ".join(res))
        for label, ax in (("twist about own axis", u), ("tilt", np.cross(u, [0, 0, 1]) if abs(u[2]) < 0.99 else [1, 0, 0])):
            ax = np.array(ax, float) / np.linalg.norm(ax)
            res = []
            for a in (0.25, 0.5, 1.0, 2.0, 4.0):
                P.reset()
                P.set_rot_about_own(name, Rotation.from_rotvec(np.radians(a) * ax).as_matrix())
                res.append(f"{a}:{min_dist(m, d, {name})[0]:+.3f}")
            print(f"   {name} {label} (deg:mm): " + "  ".join(res))

    # 4. forgiveness
    print("4. FORGIVENESS (kinematic): U pre-rotated by d, then R swept 0..90; min clearance")
    U, R_ = layer("U"), layer("R")
    for dpre in (0, 2, 5, 10, 15, 20):
        worst = np.inf
        for ang in range(0, 91, 2):
            P.reset()
            Ru = Rotation.from_rotvec(-np.radians(dpre) * np.array([0, 0, 1.0])).as_matrix()
            Rr = Rotation.from_rotvec(-np.radians(ang) * np.array([1.0, 0, 0])).as_matrix()
            P.rotate([n for n in U if n not in R_], Ru)
            P.rotate([n for n in R_ if n not in U], Rr)
            P.rotate([n for n in R_ if n in U], Rr @ Ru)
            worst = min(worst, min_dist(m, d, set(R_))[0])
        print(f"   U misaligned {dpre:2d} deg: R sweep min clearance {worst:+.3f} mm")


if __name__ == "__main__":
    main()
