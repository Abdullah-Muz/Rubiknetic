"""D18 steps 2-3 (UNSCORED; G2 pre-registration §7 P-2/P-3): two xArm7 + G2 on one table facing each other, the free-core
M7 cube held horizontally by arm A (P-97 stabiliser, from the D end), U turned by arm B (C1 turner, P-107).

Scene: table plane z = 0; arm A base at the origin; arm B ("B_") base at (L, 0, 0) yawed 180 deg; cube centre
(L/2, 0, H); layout.py's IK for the grasp poses. Cube +z (U) = world +x.
Controllers (classical; they read only robot joint states, robot kinematics derived from them, commanded targets and
time; never the cube or cubie state):
  * arm A: its joint position servos hold the IK grasp pose (actuator gravity compensation); gripper ramps closed in
    the setup phase (gravity off, before t0, logged, as D17);
  * arm B: joints 1-6 under Cartesian impedance at the gripper base (position K_P 2000 N/m, D_P 60 N.s/m; gripper
    axis direction K_R 50 N.m/rad, D_R 2 N.m.s/rad; weak joint posture and damping), as torque (motor) actuators
    clamped to the URDF peak efforts, with the model's actuator gravity compensation; J7 is the roll: a position servo
    kp 5, kv 0.2, +-1 N.m (as the G1 turner). Approach: from 40 mm outside along the axis to the grasp pose in 1 s.
Per move: (rest: fixed 0.3 s settle; the cube-state rest check of D16b/D17 is not allowed here) -> ramp B closed ->
roll on a cosine ramp, 1 s per quarter -> hold 0.3 s -> open -> roll back.
Checks per move: as D17 stage B (oracle, turn error, drift, cubie penetration, causality relative to the core, core
slip relative to arm A) plus: robot contacts with the cube other than fingertips, arm-arm contacts, robot-table
contacts (bases excluded), actuator saturation flags.
Usage (WSL): python two_arm.py [--seq "U U' U2 U' U"] [--grip 20] [--L 1.0] [--H 0.30] [--view]
  --view opens the MuJoCo viewer (needs a display, e.g. WSLg) and does not write a result file.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import layout as LY  # noqa: E402

H, TU, bm = LY.H, LY.TU, LY.bm
D13, E7 = H.D13, H.E7
scored = E7.scored
from rubiknetic.cube_logic import SOLVED, InconsistentTransition, infer_move, parse  # noqa: E402
from rubiknetic.cube_logic.notation import FACE_NORMAL  # noqa: E402
from rubiknetic.cube_physics.magnets import MagnetSystem  # noqa: E402
from rubiknetic.cube_physics.readout import CubeReadout  # noqa: E402
from rubiknetic.cube_physics.rig import AuditedSim, EditAuditError, NumericalFailure  # noqa: E402

K_P, D_P, K_R, D_R, K_Q, D_Q = 2000.0, 60.0, 50.0, 2.0, 2.0, 1.0
# integral action against joint friction (the model's arm joints have ~1 N.m frictionloss, which leaves a 2-5 mm
# static error under pure impedance; D18 finding). Active only while arm B's fingers are open; frozen while gripping.
KI_P, KI_R, I_P_MAX, I_R_MAX = 8000.0, 200.0, 25.0, 3.0
ROLL_KP, ROLL_KV, ROLL_TAU = 5.0, 0.2, 1.0
APPROACH = 0.040
SETTLE_S = 0.3
T = scored.THRESHOLDS
OUT = HERE / "results"
YAW180 = np.array([[-1.0, 0, 0], [0, -1.0, 0], [0, 0, 1.0]])


def build(L: float, Hc: float, mu: float):
    C, half, (pA, RA), (pB, RB), tips = LY.targets(L, Hc)
    sol = LY.solve(L, Hc)
    rp = LY.robot_path()
    p = H.m7_params()
    Rc = np.column_stack([[0, 1.0, 0], [0, 0, 1.0], [1.0, 0, 0]])
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, Rc.flatten())
    xml = D13.with_noslip(H.build_m1_xml(p), E7.NOSLIP)
    tag = '<body name="core" pos="0 0 0">'
    xml = xml.replace(tag, f'<body name="core" pos="{" ".join(f"{v:.9g}" for v in C)}" '
                           f'quat="{" ".join(f"{v:.9g}" for v in q)}">\n      <freejoint name="core_free"/>\n'
                           '      <inertial pos="0 0 0" mass="0.0017" diaginertia="2e-8 2e-8 2e-8"/>', 1)
    cube = mujoco.MjSpec.from_string(xml)
    parent = H.robot_spec(rp, mu)                                  # arm A, P-97 stabiliser fingertips
    for k in ("timestep", "integrator", "cone", "impratio", "solver", "iterations", "tolerance", "gravity",
              "noslip_iterations"):
        setattr(parent.option, k, getattr(cube.option, k))
    for key in list(parent.keys):
        parent.delete(key)
    parent.worldbody.add_frame().attach_body(cube.body("core"), "", "")
    bspec = H.robot_spec(rp, mu, tip_half=TU.TURNER_TIP_HALF, tag="c1")
    for key in list(bspec.keys):
        bspec.delete(key)
    fr = parent.worldbody.add_frame(pos=[L, 0, 0], quat=[0, 0, 0, 1.0])
    fr.attach_body(bspec.body("link_base"), "B_", "")
    tbl = parent.worldbody.add_geom()
    tbl.name, tbl.type, tbl.size, tbl.pos = "table", mujoco.mjtGeom.mjGEOM_PLANE, [1.5, 1.0, 0.01], [L / 2, 0, 0]
    tbl.rgba = [0.6, 0.55, 0.5, 1]
    for b in ("link_base", "B_link_base"):
        ex = parent.add_exclude()
        ex.bodyname1, ex.bodyname2 = "world", b
    m = parent.compile()
    # arm B joints 1-6 -> torque (motor) actuators, ctrl = torque, range = URDF peak effort; J7 -> roll servo
    for i in range(1, 7):
        a = m.actuator(f"B_act{i}").id
        lim = float(m.actuator_forcerange[a, 1])
        m.actuator_gainprm[a, :] = 0
        m.actuator_gainprm[a, 0] = 1.0
        m.actuator_biasprm[a, :] = 0
        m.actuator_ctrlrange[a] = [-lim, lim]
    # J7 (roll) keeps the model's own position servo (kp 800, kv 80) and URDF peak limit (30.6 N.m): the joint has
    # 1 N.m friction, 2 N.m.s/rad damping and 0.1 kg.m2 armature (Menagerie), so D17's 1 N.m roll limit cannot even
    # overcome it (D18 finding). The cube-relevant torque is measured from the fingertip contacts instead.
    a7 = m.actuator("B_act7").id
    m.actuator_ctrlrange[a7] = m.jnt_range[m.joint("B_joint7").id]
    info = {"L": L, "H": Hc, "cube_centre": C.tolist(), "ik": sol, "impedance": [K_P, D_P, K_R, D_R, K_Q, D_Q],
            "roll": "B_act7 model servo (kp 800, kv 80, +-30.6 N.m)", "pad_mu": mu, "nq": m.nq, "nv": m.nv, "nu": m.nu}
    return m, p, info, (pA, RA), (pB, RB), half


class TwoArm:
    def __init__(self, L: float, Hc: float, grip: float, mu: float = 0.8):
        self.m, self.p, self.info, (pA, RA), (pB, RB), self.half = build(L, Hc, mu)
        m = self.m
        cal = LY.calib()
        TU.set_grip(m, cal, "gripper", grip)
        TU.set_grip(m, cal, "B_gripper", grip)
        self.ms = H.install_magnets(m, self.p)
        self.sim = AuditedSim(m)
        self.d = d = self.sim.d
        self.ro = CubeReadout(m, self.p.pitch)
        J = lambda pre: [m.joint(pre + j).id for j in bm.ARM_JOINTS]  # noqa: E731
        self.qA = np.array([m.jnt_qposadr[j] for j in J("")])
        self.qB = np.array([m.jnt_qposadr[j] for j in J("B_")])
        self.vB = np.array([m.jnt_dofadr[j] for j in J("B_")])
        self.aA = [m.actuator(f"act{i}").id for i in range(1, 8)]
        self.aB = [m.actuator(f"B_act{i}").id for i in range(1, 8)]
        self.gA, self.gB = m.actuator("gripper").id, m.actuator("B_gripper").id
        self.th_open = float(m.actuator_ctrlrange[self.gA, 0])
        self.bodyB = m.body("B_xarm_gripper_base_link").id
        self.baseA, self.core = m.body("xarm_gripper_base_link").id, m.body("core").id
        sol = self.info["ik"]
        qA = np.array(sol["A"]["q"])
        # arm B starts 40 mm outside the grasp pose along its axis (+x world), IK in its own base frame
        m0 = H.robot_spec(LY.robot_path()).compile()
        d0 = mujoco.MjData(m0)
        self.pB_grasp, self.RB = pB, RB
        self.pB_pre = pB + APPROACH * np.array([1.0, 0, 0])
        RBt = RB @ (LY.ROLL180 if sol["B"]["roll180"] else np.eye(3))
        qBpre, e, _ = LY.ik(m0, d0, "xarm_gripper_base_link", YAW180.T @ (self.pB_pre - np.array([L, 0, 0])),
                            YAW180.T @ RBt, [np.array(sol["B"]["q"])])
        assert e < 1e-5, e
        d.qpos[self.qA] = qA
        d.qpos[self.qB] = qBpre
        gq = [m.jnt_qposadr[m.joint(j).id] for j in bm.GRIPPER_JOINTS]
        gqB = [m.jnt_qposadr[m.joint("B_" + j).id] for j in bm.GRIPPER_JOINTS]
        d.qpos[gq] = d.qpos[gqB] = self.th_open
        self.sim.log_setup({"kind": "initial poses", "armA": qA.tolist(), "armB_pregrasp": qBpre.tolist()})
        d.ctrl[self.aA] = qA
        d.ctrl[self.gA] = d.ctrl[self.gB] = self.th_open
        self.q0B = qBpre.copy()                       # posture reference for the impedance null space
        self.roll0 = float(qBpre[6])
        d.ctrl[self.aB[6]] = self.roll0
        mujoco.mj_forward(m, d)
        self.p_d = self.pB_pre.copy()
        self.a_d = RBt[:, 2].copy()
        self.jp, self.jr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
        self.Ip, self.Ir, self.integ = np.zeros(3), np.zeros(3), True
        self.sim.hooks.insert(0, lambda _d: None)
        # classification sets for contact checks
        root = lambda b: m.body_rootid[m.geom_bodyid[b]]  # noqa: E731
        ridA, ridB = m.body("link_base").id, m.body("B_link_base").id
        self.gA_all = np.array([g for g in range(m.ngeom) if root(g) == ridA])
        self.gB_all = np.array([g for g in range(m.ngeom) if root(g) == ridB])
        self.tipsA = [m.geom(n).id for n in H.FINGERTIPS]
        self.tipsB = [m.geom("B_" + n.replace("p97", "c1")).id for n in H.FINGERTIPS]
        self.pads = np.array(self.tipsA + self.tipsB)
        self.cubie = np.array(self.ro.geom_ids)
        self.table = m.geom("table").id
        self.f6 = np.zeros(6)
        # setup (before t0): gravity off while arm A closes, as D17 (R2-09 gravity-on grasp is for the prereg)
        g = m.opt.gravity.copy()
        m.opt.gravity[:] = 0.0
        dt = m.opt.timestep
        for k in range(int(H.SETUP_S / dt)):
            d.ctrl[self.gA] = min(bm.DRIVE_RANGE[1], self.th_open + H.CLOSE_RATE * k * dt)
            self.ctrl_step()
        m.opt.gravity[:] = g
        for _ in range(int(round(0.5 / dt))):
            self.ctrl_step()

    # ---- arm B impedance (robot state only) -------------------------------------------------------------------
    def impedance(self) -> None:
        m, d = self.m, self.d
        b = self.bodyB
        mujoco.mj_jacBody(m, d, self.jp, self.jr, b)
        v6 = self.vB[:6]
        Jp, Jr = self.jp[:, v6], self.jr[:, v6]
        qd = d.qvel[v6]
        v, w = Jp @ qd, Jr @ qd
        R = d.xmat[b].reshape(3, 3)
        a = R[:, 2]
        ep, er = self.p_d - d.xpos[b], np.cross(a, self.a_d)
        if self.integ:
            dt = m.opt.timestep
            self.Ip = np.clip(self.Ip + KI_P * ep * dt, -I_P_MAX, I_P_MAX)
            self.Ir = np.clip(self.Ir + KI_R * er * dt, -I_R_MAX, I_R_MAX)
        F = K_P * ep - D_P * v + self.Ip
        w_perp = w - (w @ a) * a
        M = K_R * er - D_R * w_perp + self.Ir
        tau = Jp.T @ F + Jr.T @ M + K_Q * (self.q0B[:6] - d.qpos[self.qB[:6]]) - D_Q * qd
        lo = m.actuator_ctrlrange[self.aB[:6], 0]
        hi = m.actuator_ctrlrange[self.aB[:6], 1]
        d.ctrl[self.aB[:6]] = np.clip(tau, lo, hi)

    def ctrl_step(self, n: int = 1) -> None:
        for _ in range(n):
            self.impedance()
            self.sim.step(1)

    # ---- per-step monitoring ------------------------------------------------------------------------------------
    def contacts(self) -> dict:
        d = self.d
        n = d.ncon
        out = {"pen_pad": 0.0, "pen_cubie": 0.0, "robot_cube_nonpad": 0, "arm_arm": 0, "robot_table": 0}
        if not n:
            return out
        g1, g2, dist = d.contact.geom1[:n], d.contact.geom2[:n], d.contact.dist[:n]
        cub1, cub2 = np.isin(g1, self.cubie), np.isin(g2, self.cubie)
        pad1, pad2 = np.isin(g1, self.pads), np.isin(g2, self.pads)
        rob1 = np.isin(g1, self.gA_all) | np.isin(g1, self.gB_all)
        rob2 = np.isin(g2, self.gA_all) | np.isin(g2, self.gB_all)
        pc = (pad1 & cub2) | (pad2 & cub1)
        if pc.any():
            out["pen_pad"] = max(0.0, float(-dist[pc].min()) * 1e3)
        cc = cub1 & cub2
        if cc.any():
            out["pen_cubie"] = max(0.0, float(-dist[cc].min()) * 1e3)
        out["robot_cube_nonpad"] = int((((rob1 & ~pad1) & cub2) | ((rob2 & ~pad2) & cub1)).sum())
        aA1, aB1 = np.isin(g1, self.gA_all), np.isin(g1, self.gB_all)
        aA2, aB2 = np.isin(g2, self.gA_all), np.isin(g2, self.gB_all)
        out["arm_arm"] = int(((aA1 & aB2) | (aB1 & aA2)).sum())
        out["robot_table"] = int((((g1 == self.table) & rob2) | ((g2 == self.table) & rob1)).sum())
        return out

    def force_on(self, geoms) -> float:
        d, tot = self.d, 0.0
        for i in range(d.ncon):
            c = d.contact[i]
            if c.geom1 in geoms or c.geom2 in geoms:
                mujoco.mj_contactForce(self.m, d, i, self.f6)
                tot += self.f6[0]
        return tot

    def tool_torque(self, axis) -> float:
        """Torque about the cube axis (through the core) that arm B's fingertips apply to the cubies (N.m)."""
        d, tot = self.d, 0.0
        c0 = d.xpos[self.core]
        cub = set(self.cubie.tolist())
        tips = set(self.tipsB)
        for i in range(d.ncon):
            c = d.contact[i]
            g1, g2 = int(c.geom1), int(c.geom2)
            if g1 in tips and g2 in cub:
                sign = 1.0                                   # contact force acts on geom2 (the cubie)
            elif g2 in tips and g1 in cub:
                sign = -1.0
            else:
                continue
            mujoco.mj_contactForce(self.m, d, i, self.f6)
            f = sign * (c.frame.reshape(3, 3).T @ self.f6[:3])
            tot += float(np.cross(c.pos - c0, f) @ axis)
        return tot

    def step(self, n: int) -> None:
        for _ in range(n):
            self.ctrl_step()
            c = self.contacts()
            a = self.acc
            for k in ("pen_pad", "pen_cubie"):
                a[k] = max(a[k], c[k])
            for k in ("robot_cube_nonpad", "arm_arm", "robot_table"):
                a[k] = max(a[k], c[k])
            if a["t_force"] is None and self.force_on(self.tipsB) > T["causal_force_N"]:
                a["t_force"] = float(self.d.time)
            if a["t_motion"] is None and a.get("bodies") is not None:
                ax = a["axis_world"]
                w = float(np.mean(self.d.cvel[a["bodies"], :3] @ ax) - self.d.cvel[self.core, :3] @ ax)
                if abs(np.degrees(w)) > T["causal_speed_dps"]:
                    a["t_motion"] = float(self.d.time)
            a["tau_roll"] = max(a["tau_roll"], abs(float(self.d.actuator_force[self.aB[6]])))
            if a.get("axis_world") is not None:
                a["tau_tool"] = max(a["tau_tool"], abs(self.tool_torque(a["axis_world"])))
            fr = self.m.actuator_forcerange
            satA = np.abs(self.d.actuator_force[self.aA]) >= 0.99 * fr[self.aA, 1]
            satB = np.abs(self.d.ctrl[self.aB[:6]]) >= 0.99 * self.m.actuator_ctrlrange[self.aB[:6], 1]
            a["saturated_steps"] += int(satA.any() or satB.any())
            a["track_err_mm"] = max(a["track_err_mm"],
                                    float(np.linalg.norm(self.p_d - self.d.xpos[self.bodyB]) * 1e3))

    def secs(self, s: float) -> int:
        return max(1, int(round(s / self.m.opt.timestep)))

    def new_acc(self) -> None:
        self.acc = {"pen_pad": 0.0, "pen_cubie": 0.0, "robot_cube_nonpad": 0, "arm_arm": 0, "robot_table": 0,
                    "t_force": None, "t_motion": None, "tau_roll": 0.0, "tau_tool": 0.0, "saturated_steps": 0, "track_err_mm": 0.0,
                    "bodies": None}

    def approach(self) -> dict:
        self.new_acc()
        n = self.secs(1.0)
        for k in range(1, n + 1):
            s = 0.5 - 0.5 * np.cos(np.pi * k / n)
            self.p_d = self.pB_pre + s * (self.pB_grasp - self.pB_pre)
            self.step(1)
        self.step(self.secs(1.0))
        out = {k: v for k, v in self.acc.items() if k != "bodies"}
        out["final_err_mm"] = float(np.linalg.norm(self.p_d - self.d.xpos[self.bodyB]) * 1e3)
        a = self.d.xmat[self.bodyB].reshape(3, 3)[:, 2]
        out["final_axis_err_deg"] = float(np.degrees(np.arccos(np.clip(a @ self.a_d, -1, 1))))
        return out

    def rel(self):
        d = self.d
        Rb, pb = d.xmat[self.baseA].reshape(3, 3), d.xpos[self.baseA]
        return Rb.T @ (d.xpos[self.core] - pb), Rb.T @ d.xmat[self.core].reshape(3, 3)

    def ramp_grip(self, target: float) -> None:
        d = self.d
        start = float(d.ctrl[self.gB])
        n = self.secs(abs(target - start) / H.CLOSE_RATE)
        for k in range(1, n + 1):
            d.ctrl[self.gB] = start + (target - start) * k / n
            self.step(1)

    def move(self, mv) -> dict:
        m, d, ro = self.m, self.d, self.ro
        self.new_acc()
        self.step(self.secs(SETTLE_S))                     # fixed settle (no cube-state rest check)
        _, r0 = ro.poses(d)
        members = ro.layer_members(d, mv.face)
        Rc = d.xmat[self.core].reshape(3, 3)
        self.acc["bodies"] = ro.body_ids[members]
        self.acc["axis_world"] = Rc @ np.array(FACE_NORMAL[mv.face], float)
        p0, R0 = self.rel()
        grasp_err = float(np.linalg.norm(self.p_d - d.xpos[self.bodyB]) * 1e3)
        self.integ = False                                  # gripping: pure impedance (compliant)
        self.ramp_grip(bm.DRIVE_RANGE[1])
        self.step(self.secs(0.3))
        delta = -np.pi / 2 * {1: 1, 2: 2, 3: -1}[mv.quarter_turns]
        zB = d.xmat[self.bodyB].reshape(3, 3)[:, 2]        # J7 axis ~ gripper axis
        axis_sign = float(np.sign(self.acc["axis_world"] @ zB))
        start = float(d.ctrl[self.aB[6]])
        n = self.secs(abs(delta) / (np.pi / 2))
        for k in range(1, n + 1):
            d.ctrl[self.aB[6]] = start + axis_sign * delta * (0.5 - 0.5 * np.cos(np.pi * k / n))
            self.step(1)
        self.step(self.secs(0.3))
        d.ctrl[self.gB] = self.th_open
        self.step(self.secs(0.3))
        self.integ = True
        _, r1 = ro.poses(d)
        obs = ro.observe(d)
        a = dict(self.acc)
        end = float(d.ctrl[self.aB[6]])
        n = self.secs(1.0)
        for k in range(1, n + 1):
            d.ctrl[self.aB[6]] = end + (self.roll0 - end) * (0.5 - 0.5 * np.cos(np.pi * k / n))
            self.step(1)
        nominal = -90.0 * {1: 1, 2: 2, 3: -1}[mv.quarter_turns]
        rot = ro.rotation_about_deg(r0, r1, members, mv.face)
        err = (rot - nominal + 180.0) % 360.0 - 180.0
        non = [i for i in range(26) if sum(map(abs, scored.HOME_POSITIONS[i])) >= 2 and i not in members]
        drift = np.abs(ro.rotation_about_deg(r0, r1, non, mv.face))
        p1, R1 = self.rel()
        tf, tm = a["t_force"], a["t_motion"]
        return {"move": str(mv), "obs": obs, "turn_error_deg": float(np.mean(err)), "grasp_err_mm": grasp_err,
                "nontarget_drift_deg": float(drift.max()), "pen_cubie_mm": a["pen_cubie"], "pen_pad_mm": a["pen_pad"],
                "max_roll_torque_Nm": a["tau_roll"], "max_tool_torque_on_layer_Nm": a["tau_tool"], "t_tip_force_s": tf, "t_layer_motion_rel_core_s": tm,
                "ok_causal": bool(tm is None or (tf is not None and tf <= tm)),
                "robot_cube_nonpad_max": a["robot_cube_nonpad"], "arm_arm_max": a["arm_arm"],
                "robot_table_max": a["robot_table"], "saturated_steps": a["saturated_steps"],
                "armB_track_err_mm": a["track_err_mm"],
                "core_slip_mm": float(np.linalg.norm(p1 - p0) * 1e3),
                "core_rot_deg": float(np.degrees(np.linalg.norm(Rotation.from_matrix(R1 @ R0.T).as_rotvec())))}


def run(seq: str, grip: float, L: float, Hc: float, viewer=None) -> dict:
    t_wall = time.perf_counter()
    r = TwoArm(L, Hc, grip)
    if viewer is not None:
        viewer(r)
    prev = r.ro.observe(r.d)
    rec = {"study": "D18 two-arm", "scored": False, "sequence": seq, "grip_N": grip, "scene": r.info,
           "t0_solved": bool(prev.valid and prev.state == SOLVED), "per_move": []}
    rec["approach"] = r.approach()
    print("approach", json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rec["approach"].items()}),
          flush=True)
    expect = SOLVED
    moves = parse(seq)
    try:
        for mv in moves:
            pm = r.move(mv)
            obs = pm.pop("obs")
            observed = None
            if prev.valid and obs.valid:
                try:
                    observed = infer_move(prev.cube, obs.cube)
                except InconsistentTransition as e:
                    pm["inference_error"] = str(e)
            if observed is not None:
                expect = expect.apply(observed)
            pm["observed_move"] = str(observed) if observed else None
            pm["ok_oracle"] = bool(obs.valid and observed == mv and obs.state == expect)
            pm["ok_turn_error"] = abs(pm["turn_error_deg"]) <= T["turn_error_deg"]
            pm["ok_drift"] = pm["nontarget_drift_deg"] <= T["nontarget_drift_deg"]
            pm["ok_penetration_cubie"] = pm["pen_cubie_mm"] <= T["penetration_mm"]
            pm["ok_no_nonpad_cube_contact"] = pm["robot_cube_nonpad_max"] == 0
            pm["ok_no_arm_arm"] = pm["arm_arm_max"] == 0
            pm["ok_no_table"] = pm["robot_table_max"] == 0
            pm["ok_all"] = all(v for k, v in pm.items() if k.startswith("ok_"))
            rec["per_move"].append(pm)
            print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in pm.items()}), flush=True)
            prev = obs
            if not pm["ok_oracle"]:
                break
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    final = r.ro.observe(r.d)
    rec.update({"final_matches_oracle": bool(final.valid and final.state == expect),
                "audit_violations": r.sim.violations, "numerical_failures": r.sim.numerical_failures,
                "sim_time_s": float(r.d.time), "wall_s": time.perf_counter() - t_wall})
    rec["pass"] = bool(rec["t0_solved"] and "aborted" not in rec and not rec["audit_violations"]
                       and not rec["numerical_failures"] and len(rec["per_move"]) == len(moves)
                       and all(pm["ok_all"] for pm in rec["per_move"]) and rec["final_matches_oracle"])
    MagnetSystem.uninstall()
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq", default="U U' U2 U' U")
    ap.add_argument("--grip", type=float, default=20.0)
    ap.add_argument("--L", type=float, default=1.0)
    ap.add_argument("--H", type=float, default=0.30)
    ap.add_argument("--view", action="store_true")
    a = ap.parse_args()
    H.TIP_SOLREF = (0.01, 1.0)                         # soft pads, as scored (P-105)
    viewer, holder = None, {}
    if a.view:
        import mujoco.viewer

        def viewer(r):
            v = mujoco.viewer.launch_passive(r.m, r.d)
            holder["v"] = v
            v.cam.lookat[:] = r.d.xpos[r.core]
            v.cam.distance, v.cam.azimuth, v.cam.elevation = 1.4, 90, -20
            every = max(1, int(round(1 / 60 / r.m.opt.timestep)))
            k = [0]

            def hook(_d):
                k[0] += 1
                if k[0] % every == 0 and v.is_running():
                    v.sync()
            r.sim.hooks.append(hook)
    rec = run(a.seq, a.grip, a.L, a.H, viewer)
    if a.view:                                        # viewing only: never overwrite a recorded result
        print(json.dumps({k: v for k, v in rec.items() if k not in ("per_move", "scene", "approach")}, default=float))
        v = holder.get("v")
        if v is not None:
            print("sequence done; close the viewer window to exit", flush=True)
            while v.is_running():
                time.sleep(0.1)
        return
    OUT.mkdir(parents=True, exist_ok=True)
    name = f"two_arm_F{a.grip:g}_L{a.L:g}_H{a.H:g}_{a.seq.replace(' ', '_').replace(chr(39), 'p')}"
    (OUT / f"{name}.json").write_text(json.dumps(rec, indent=1, default=float))
    print(json.dumps({k: v for k, v in rec.items() if k not in ("per_move", "scene", "approach")}, default=float))


if __name__ == "__main__":
    main()
