"""D5 stage-2 dynamics checks (UNSCORED): rest, corner-twist staircase, centre-driven turns,
dynamic forgiveness, and throughput.

* Turns are driven by a position actuator on the centre hinge. The cap's side faces push the
  layer through contact; this is not the pad rig.
* The forgiveness test misaligns U through its own actuator (contact-driven), then zeroes that
  actuator's gains (a model-parameter change in this diagnostic, not a state write) so U is free,
  then turns R.
Usage (WSL2, repo root): uv run python experiments/D5_follower_cube/dyn_check.py <rest|twist|turn|forgive|all> [k=v ...]
"""
from __future__ import annotations

import sys
import time

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from cube_d5 import D5Params, build_xml  # noqa: E402

from rubiknetic.cube_logic import CubieCube, parse  # noqa: E402
from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_logic.notation import FACE_NORMAL  # noqa: E402
from rubiknetic.cube_physics.m1_model import cubie_name  # noqa: E402
from rubiknetic.cube_physics.readout import CubeReadout  # noqa: E402
from rubiknetic.cube_physics.rig import AuditedSim, EditAuditError, NumericalFailure  # noqa: E402

PITCH = 0.019


def make(p: D5Params):
    xml, info = build_xml(p, actuated_centres=True)
    m = mujoco.MjModel.from_xml_string(xml)
    sim = AuditedSim(m, allow_test_wrench=True)
    mujoco.mj_forward(m, sim.d)
    return m, sim, CubeReadout(m, PITCH)


def rot_deg(rot, rot0, i, axis=None):
    rv = Rotation.from_matrix(rot[i] @ rot0[i].T).as_rotvec()
    return float(np.degrees(rv @ axis)) if axis is not None else float(np.degrees(np.linalg.norm(rv)))


def max_pen(d):
    return max(0.0, -float(d.contact.dist[:d.ncon].min())) * 1000 if d.ncon else 0.0


def mode_rest(p, secs=3.0):
    m, sim, ro = make(p)
    d = sim.d
    pos0, rot0 = ro.poses(d)
    t = time.perf_counter()
    try:
        sim.step(int(secs / m.opt.timestep))
    except NumericalFailure as e:
        print("REST numerical failure:", e)
        return
    el = time.perf_counter() - t
    pos, rot = ro.poses(d)
    drift = max(rot_deg(rot, rot0, i) for i in range(26))
    obs = ro.observe(d)
    print(f"REST {secs}s: observed valid {obs.valid} solved {obs.valid and obs.state == CubieCube()} | max piece rotation "
          f"{drift:.3f} deg, max displacement {np.abs(pos - pos0).max() * PITCH * 1000:.3f} mm, contacts {d.ncon}, "
          f"penetration {max_pen(d):.3f} mm | {secs / m.opt.timestep / el:.0f} steps/s (RTF {secs / el:.2f})")


def mode_twist(p):
    m, sim, ro = make(p)
    d = sim.d
    dt = m.opt.timestep
    sim.step(int(0.5 / dt))
    idx = HOME_POSITIONS.index((1, 1, 1))
    body = int(ro.body_ids[idx])
    axis = np.ones(3) / np.sqrt(3)
    pos0, rot0 = ro.poses(d)
    prev = 0.0
    print("TWIST staircase on corner ppp (M1 reference: 11 deg at 0.05 N.m, 35 deg at 0.5 N.m, diverged by 1 N.m)")
    try:
        for lvl in [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]:
            pen = 0.0
            for k in range(int(0.05 / dt) + int(0.25 / dt)):
                tau = prev + (lvl - prev) * min(1.0, (k + 1) / int(0.05 / dt))
                sim.set_test_wrench(body, np.concatenate([np.zeros(3), tau * axis]))
                sim.step()
                pen = max(pen, max_pen(d))
            pos, rot = ro.poses(d)
            nbr = max(rot_deg(rot, rot0, i) for i in range(26) if i != idx)
            print(f"  {lvl:6.3f} N.m: twist {rot_deg(rot, rot0, idx, axis):7.2f} deg | corner moved "
                  f"{np.linalg.norm(pos[idx] - pos0[idx]) * PITCH * 1000:6.3f} mm | max neighbour rot {nbr:5.2f} deg | pen {pen:.3f} mm")
            prev = lvl
        sim.set_test_wrench(body, np.zeros(6))
        sim.step(int(0.5 / dt))
        _, rot = ro.poses(d)
        obs = ro.observe(d)
        print(f"  released: twist {rot_deg(rot, rot0, idx, axis):.2f} deg; observed valid {obs.valid}, solved "
              f"{obs.valid and obs.state == CubieCube()}")
    except (NumericalFailure, EditAuditError) as e:
        print("  ABORT", e)


def _turn(m, sim, ro, face, quarter_s=1.0, settle_s=0.5, sign=1):
    d = sim.d
    dt = m.opt.timestep
    h = tuple(int(x) for x in FACE_NORMAL[face])
    aid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, f"turn_{cubie_name(h)}")
    q0 = float(d.ctrl[aid])
    n = int(quarter_s / dt)
    for k in range(n):
        d.ctrl[aid] = q0 - sign * np.pi / 2 * (k + 1) / n  # CW about the outward normal
        sim.step()
    sim.step(int(settle_s / dt))


def mode_turn(p, seq="U R U' R' F F' D2 L B'"):
    m, sim, ro = make(p)
    d = sim.d
    sim.step(int(0.3 / m.opt.timestep))
    cube = CubieCube()
    t = time.perf_counter()
    nst = 0
    print(f"TURN sequence (centre-driven): {seq}")
    for mv in parse(seq):
        _, rot0 = ro.poses(d)
        members = ro.layer_members(d, mv.face)
        try:
            for _ in range(mv.quarter_turns if mv.quarter_turns != 3 else 1):
                _turn(m, sim, ro, mv.face, sign=1 if mv.quarter_turns != 3 else -1)
                nst += int(1.5 / m.opt.timestep)
        except (NumericalFailure, EditAuditError) as e:
            print("  ABORT", e)
            return
        _, rot = ro.poses(d)
        ang = CubeReadout.rotation_about_deg(rot0, rot, members, mv.face)
        others = [i for i in range(26) if i not in members]
        drift = np.max(np.abs(CubeReadout.rotation_about_deg(rot0, rot, others, mv.face)))
        cube = cube.apply(mv) if hasattr(cube, "apply") else cube.multiply(CubieCube.from_moves([mv]))
        obs = ro.observe(d)
        nominal = -90.0 * {1: 1, 2: 2, 3: -1}[mv.quarter_turns]
        err = np.mean(ang) - nominal
        print(f"  {str(mv):3s}: layer {np.mean(ang):+8.2f} deg (error {err:+.2f}, spread {np.ptp(ang):.2f}) | non-layer drift "
              f"{drift:.2f} | pen {max_pen(d):.3f} mm | observed valid {obs.valid}, matches oracle "
              f"{obs.valid and obs.state == cube}")
    print(f"  throughput {nst / (time.perf_counter() - t):.0f} steps/s")


def mode_forgive(p, degs=(0, 3, 6, 9, 12, 15, 20)):
    print("FORGIVENESS (dynamic): U turned to d deg by its actuator, then U freed, then R turned")
    for deg in degs:
        m, sim, ro = make(p)
        d = sim.d
        dt = m.opt.timestep
        sim.step(int(0.3 / dt))
        aU = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, "turn_cubie_00p")
        try:
            for k in range(int(0.3 / dt)):
                d.ctrl[aU] = -np.radians(deg) * (k + 1) / int(0.3 / dt)
                sim.step()
            sim.step(int(0.2 / dt))
            m.actuator_gainprm[aU, 0] = 0.0
            m.actuator_biasprm[aU, 1:3] = 0.0
            _, rot0 = ro.poses(d)
            membersR = ro.layer_members(d, "R")
            membersU = ro.layer_members(d, "U")
            _turn(m, sim, ro, "R")
        except (NumericalFailure, EditAuditError) as e:
            print(f"  U {deg:2d} deg: ABORT {e}")
            continue
        _, rot = ro.poses(d)
        angR = np.mean(CubeReadout.rotation_about_deg(rot0, rot, membersR, "R"))
        obs = ro.observe(d)
        uz = [i for i in membersU if i not in membersR]
        angU = np.mean(CubeReadout.rotation_about_deg(rot0, rot, uz, "U"))
        exp = CubieCube().apply(parse("R")[0]) if hasattr(CubieCube(), "apply") else None
        print(f"  U {deg:2d} deg: R turned {angR:+7.2f} deg | U (non-R) moved {angU:+6.2f} deg during the R turn | "
              f"observed valid {obs.valid}{', state = R' if obs.valid and exp is not None and obs.state == exp else ''} | "
              f"pen {max_pen(d):.3f} mm")


if __name__ == "__main__":
    mode = sys.argv[1]
    p = D5Params(bevel_body=1.0, bevel_foot=0.5)
    for kv in sys.argv[2:]:
        k, v = kv.split("=")
        cur = getattr(p, k)
        setattr(p, k, type(cur)(v) if not isinstance(cur, tuple) else tuple(float(x) for x in v.split(",")))
    for mname in (["rest", "twist", "turn", "forgive"] if mode == "all" else [mode]):
        {"rest": mode_rest, "twist": mode_twist, "turn": mode_turn, "forgive": mode_forgive}[mname](p)
