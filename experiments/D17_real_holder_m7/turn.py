"""D17 stage B (UNSCORED): arm A (xArm7 + G2, P-97 stabiliser fingertips, P-04 orientation, as hold.py) holds the
free-core M7 cube; a second G2 gripper ("B_", the turner, C1 fingertips) turns the U layer coaxially from the other
end. No arm B yet: the turner gripper sits on a compliant mount that follows the cube.

Turner mount (PROPOSAL, a stand-in for arm B's Cartesian impedance and its wrist roll J7):
  * three slides x, y, z with springs (K_LIN) and dampers (C_LIN) to the commanded pose, gravity-compensated, so the
    turner can follow the cube by millimetres instead of being world-fixed (D16's G1 rig);
  * a hinge "turner_roll" about the cube axis, driven by a position servo as the G1 turner (kp 5 N.m/rad, kv 0.2,
    torque limit 1 N.m).
Turner fingertip (C1, P-97): one box per finger, 25 wide x 14 deep x 4 mm, its distal end 14 mm into the U layer
(insertion 14 mm, within the flat band of the 19 mm layer).
Per move (controller; all states evolve only through actuators):
  1. wait until the cube is at rest (all cubies and the core |w| < 1 deg/s, at most 2 s; D16b);
  2. ramp the turner gripper closed (0.5 rad/s, as arm A), hold 0.3 s;
  3. roll by the move angle on a smooth (cosine) ramp, 1.0 s per quarter turn; hold 0.3 s;
  4. open the turner, wait 0.3 s, roll back to zero (open, 1.0 s), wait 0.3 s.
Checks per move (as G1's, in the core frame): observed move (logical oracle from the readout), turn error (<= 2 deg),
non-target drift (<= 1 deg), cubie-cubie penetration (<= 0.5 mm; pad penetration reported separately), causality
(turner fingertip force > 0.5 N before the U layer's speed relative to the core exceeds 5 deg/s), plus core slip
relative to arm A's gripper, the mount's excursion, edit audit, numerical failures.
Usage (WSL): python turn.py [--seq "U U' U2 U' U"] [--grip 20] [--tip-solref 0.01] [--k-lin 2000]
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
import hold as H  # noqa: E402

bm, D13, E7 = H.bm, H.D13, H.E7
scored = E7.scored
from rubiknetic.cube_logic import SOLVED, InconsistentTransition, infer_move, parse  # noqa: E402
from rubiknetic.cube_logic.notation import FACE_NORMAL, to_string  # noqa: E402
from rubiknetic.cube_physics.magnets import MagnetSystem  # noqa: E402
from rubiknetic.cube_physics.readout import CubeReadout  # noqa: E402
from rubiknetic.cube_physics.rig import AuditedSim, EditAuditError, NumericalFailure  # noqa: E402

TURNER_TIP_HALF = (0.0125, 0.002, 0.007)    # C1 turner fingertip, 25 x 4 x 14 mm (half sizes)
SHOULDER_PROT, SHOULDER_Z = 0.003, 0.003    # C2 shoulder: protrudes 3 mm (P-97) inward beyond the pad face, 3 mm thick
C2_PRE_GAP = 0.058                          # C2: pre-close to a 58 mm pad gap (0.5 mm clear per side), seat, then grip
C2_PRESEAT, C2_PRELOAD = -0.001, 0.002      # C2 axial commands vs nominal 14 mm: close 1 mm short, then push 2 mm deep
INSERTION_U = 0.014
K_LIN, C_LIN, MOUNT_MASS = 2000.0, 60.0, 0.5
ROLL_KP, ROLL_KV, ROLL_TAU = 5.0, 0.2, 1.0
REST_W, MAX_WAIT = 1.0, 2.0
T = scored.THRESHOLDS
OUT = H.OUT


def add_shoulders(sp: mujoco.MjSpec, robot_path) -> None:
    """C2 (P-03/P-97): a shoulder on each turner finger, at the fingertip's proximal end, protruding SHOULDER_PROT
    inward beyond the pad face, so it abuts the U end face and sets the insertion at 14 mm mechanically. The inward
    direction (finger body frame) is found from the compiled gripper geometry."""
    m0 = sp.copy().compile() if hasattr(sp, "copy") else None
    for side in ("left", "right"):
        ft = sp.geom(f"{side}_fingertip_c1")
        th = TURNER_TIP_HALF
        if m0 is not None:
            d0 = mujoco.MjData(m0)
            mujoco.mj_kinematics(m0, d0)
            g = m0.geom(f"{side}_fingertip_c1").id
            base = m0.body("xarm_gripper_base_link").id
            zb = d0.xmat[base].reshape(3, 3)[:, 2]
            v = d0.xpos[base] - d0.geom_xpos[g]
            v -= (v @ zb) * zb
            inward = d0.xmat[m0.geom_bodyid[g]].reshape(3, 3).T @ (v / np.linalg.norm(v))
        else:
            inward = np.array([0.0, 1.0 if ft.pos[1] < 0 else -1.0, 0.0])
        assert abs(inward[1]) > 0.99, inward
        iy = float(np.sign(inward[1]))
        sh = ft.parent.add_geom()
        sh.name = f"{side}_shoulder_c2"
        sh.type = mujoco.mjtGeom.mjGEOM_BOX
        sh.size = [th[0], SHOULDER_PROT / 2, SHOULDER_Z / 2]
        sh.pos = [float(ft.pos[0]), float(ft.pos[1]) + iy * (th[1] + SHOULDER_PROT / 2),
                  float(ft.pos[2]) - th[2] - SHOULDER_Z / 2]
        sh.quat = list(ft.quat)
        for k in ("contype", "conaffinity", "condim", "priority", "friction", "solref", "solimp", "rgba"):
            setattr(sh, k, getattr(ft, k))
        sh.mass = 0.002


def build(robot_path, calib, mu: float, k_lin: float, turner: str = "c1"):
    p = H.m7_params()
    half = 1.5 * p.pitch - p.gap / 2
    centre, quat, info = H.grasp_frame(robot_path, calib, half)
    xml = D13.with_noslip(H.build_m1_xml(p), E7.NOSLIP)
    tag = '<body name="core" pos="0 0 0">'
    xml = xml.replace(tag, f'<body name="core" pos="{" ".join(f"{v:.9g}" for v in centre)}" '
                           f'quat="{" ".join(f"{v:.9g}" for v in quat)}">\n      <freejoint name="core_free"/>\n'
                           '      <inertial pos="0 0 0" mass="0.0017" diaginertia="2e-8 2e-8 2e-8"/>', 1)
    cube = mujoco.MjSpec.from_string(xml)
    parent = H.robot_spec(robot_path, mu)
    for k in ("timestep", "integrator", "cone", "impratio", "solver", "iterations", "tolerance", "gravity",
              "noslip_iterations"):
        setattr(parent.option, k, getattr(cube.option, k))
    for key in list(parent.keys):
        parent.delete(key)
    parent.worldbody.add_frame().attach_body(cube.body("core"), "", "")
    # turner: tip 14 mm into the U layer; arm A's gripper axis is world -z within 0.0004 (P2), cube +z along it
    Rg = np.array(info.pop("_Rg"))
    zA = Rg[:, 2]
    tip_dist = info["pad_tip_gripper_z_mm"] / 1e3     # base-frame origin -> fingertip distal end (same G2 model)
    tipB = centre + (half - INSERTION_U) * zA
    mount_pos = tipB + tip_dist * zA                   # the turner points along -zA (world +z)
    bspec = H.robot_spec(robot_path, mu, tip_half=TURNER_TIP_HALF, tag="c1")
    if turner == "c2":
        add_shoulders(bspec, robot_path)
    mount = parent.worldbody.add_body(name="turner_mount", pos=mount_pos.tolist())
    for ax, v in (("x", [1, 0, 0]), ("y", [0, 1, 0]), ("z", [0, 0, 1])):
        mount.add_joint(name=f"turner_slide_{ax}", type=mujoco.mjtJoint.mjJNT_SLIDE, axis=v)
        # the impedance as a position actuator (kp = stiffness, kv = damping): ctrl = commanded offset (m), so the
        # controller can command lateral and axial offsets (C1/C2 pilot); same dynamics as D17 stage B's springs
        pa = parent.add_actuator(name=f"turner_pos_{ax}", target=f"turner_slide_{ax}",
                                 trntype=mujoco.mjtTrn.mjTRN_JOINT)
        pa.set_to_position(kp=k_lin, kv=C_LIN)
    roll = mount.add_body(name="turner_roll_body")
    roll.add_joint(name="turner_roll", type=mujoco.mjtJoint.mjJNT_HINGE, axis=[0, 0, 1], damping=0.001,
                   armature=1e-5)
    mount.mass, mount.inertia, mount.explicitinertial = MOUNT_MASS, [1e-3, 1e-3, 1e-3], True
    roll.add_frame().attach_body(bspec.body("xarm_gripper_base_link"), "B_", "")
    a = parent.add_actuator(name="turner_roll", target="turner_roll", trntype=mujoco.mjtTrn.mjTRN_JOINT)
    a.set_to_position(kp=ROLL_KP, kv=ROLL_KV)
    a.forcelimited, a.forcerange = mujoco.mjtLimited.mjLIMITED_TRUE, [-ROLL_TAU, ROLL_TAU]
    m = parent.compile()
    for b in range(m.nbody):                           # turner side gravity-compensated (like arm A)
        nm = m.body(b).name
        if nm.startswith("B_") or nm.startswith("turner_"):
            m.body_gravcomp[b] = 1.0
    info.update({"turner_mount_world_m": np.round(mount_pos, 5).tolist(), "turner_tip_world_m": tipB.round(5).tolist(),
                 "k_lin": k_lin, "c_lin": C_LIN, "turner": turner, "roll": [ROLL_KP, ROLL_KV, ROLL_TAU], "pad_mu": mu,
                 "nq": m.nq, "nv": m.nv, "nu": m.nu})
    return m, p, info


def set_grip(m, calib, name: str, F: float) -> None:
    f = max(F * calib["tendon_force_per_grip_N"] - calib["spring_tau_at_calib_Nm"], 0.0)
    m.actuator_forcerange[m.actuator(name).id] = [-f, f]


class Run:
    def __init__(self, robot_path, calib, grip: float, mu: float, k_lin: float, turner: str = "c1",
                 ax_off: float = 0.0, lat_off: float = 0.0):
        self.turner, self.ax_off, self.lat_off, self.calib = turner, ax_off, lat_off, calib
        _orig = H.grasp_frame

        def gf(rp, cal, half):                         # also return arm A's gripper rotation
            c, q, inf = _orig(rp, cal, half)
            m0 = H.robot_spec(rp).compile()
            d0 = mujoco.MjData(m0)
            d0.qpos[[m0.jnt_qposadr[m0.joint(j).id] for j in bm.ARM_JOINTS]] = H.HOME_ARM
            mujoco.mj_kinematics(m0, d0)
            inf["_Rg"] = d0.xmat[m0.body("xarm_gripper_base_link").id].reshape(3, 3).tolist()
            return c, q, inf
        H.grasp_frame = gf
        try:
            self.m, self.p, self.info = build(robot_path, calib, mu, k_lin, turner)
        finally:
            H.grasp_frame = _orig
        m = self.m
        set_grip(m, calib, "gripper", grip)
        set_grip(m, calib, "B_gripper", grip)
        self.ms = H.install_magnets(m, self.p)
        self.sim = AuditedSim(m)
        self.d = d = self.sim.d
        self.ro = CubeReadout(m, self.p.pitch)
        aid = lambda n: m.actuator(n).id  # noqa: E731
        self.gA, self.gB, self.roll = aid("gripper"), aid("B_gripper"), aid("turner_roll")
        self.th_open = float(m.actuator_ctrlrange[self.gA, 0])
        qa = [m.jnt_qposadr[m.joint(j).id] for j in bm.ARM_JOINTS]
        gq = [m.jnt_qposadr[m.joint(j).id] for j in bm.GRIPPER_JOINTS]
        gqB = [m.jnt_qposadr[m.joint("B_" + j).id] for j in bm.GRIPPER_JOINTS]
        d.qpos[qa] = H.HOME_ARM
        d.qpos[gq] = self.th_open
        d.qpos[gqB] = self.th_open
        self.sim.log_setup({"kind": "initial poses", "arm": H.HOME_ARM, "grippers_theta": self.th_open})
        d.ctrl[[aid(f"act{i}") for i in range(1, 8)]] = H.HOME_ARM
        d.ctrl[self.gA] = d.ctrl[self.gB] = self.th_open
        self.pos_act = [aid(f"turner_pos_{a}") for a in "xyz"]
        slides = [m.jnt_qposadr[m.joint(f"turner_slide_{a}").id] for a in "xyz"]
        z0 = ax_off + (C2_PRESEAT if turner == "c2" else 0.0)
        d.qpos[slides] = d.ctrl[self.pos_act] = [lat_off, 0.0, z0]       # commanded grasp offsets (setup)
        self.sim.log_setup({"kind": "turner offsets", "lateral_m": lat_off, "axial_m": z0, "turner": turner})
        mujoco.mj_forward(m, d)
        self.baseA, self.core = m.body("xarm_gripper_base_link").id, m.body("core").id
        g = m.opt.gravity.copy()
        m.opt.gravity[:] = 0.0
        dt = m.opt.timestep
        for k in range(int(H.SETUP_S / dt)):          # setup (as hold.py): arm A closes, gravity off
            d.ctrl[self.gA] = min(bm.DRIVE_RANGE[1], self.th_open + H.CLOSE_RATE * k * dt)
            self.sim.step(1)
        m.opt.gravity[:] = g
        self.sim.step(int(round(0.5 / dt)))
        self.tipsA = [m.geom(n).id for n in H.FINGERTIPS]
        self.tipsB = [m.geom("B_" + n.replace("p97", "c1")).id for n in H.FINGERTIPS]
        self.pads = np.array(self.tipsA + self.tipsB)
        self.cubie = np.array(self.ro.geom_ids)
        self.mount_q = slides
        self.shoulders = [m.geom(f"B_{s}_shoulder_c2").id for s in ("left", "right")] if turner == "c2" else []
        self.f6 = np.zeros(6)

    def rel(self):
        d = self.d
        Rb, pb = d.xmat[self.baseA].reshape(3, 3), d.xpos[self.baseA]
        return Rb.T @ (d.xpos[self.core] - pb), Rb.T @ d.xmat[self.core].reshape(3, 3)

    def tipB_force(self) -> float:
        d, tot = self.d, 0.0
        for i in range(d.ncon):
            c = d.contact[i]
            if (c.geom1 in self.tipsB) or (c.geom2 in self.tipsB):
                mujoco.mj_contactForce(self.m, d, i, self.f6)
                tot += self.f6[0]
        return tot

    def pen(self) -> tuple[float, float]:
        d = self.d
        n = d.ncon
        if not n:
            return 0.0, 0.0
        g1, g2, dist = d.contact.geom1[:n], d.contact.geom2[:n], d.contact.dist[:n]
        padc = np.isin(g1, self.pads) | np.isin(g2, self.pads)
        cc = np.isin(g1, self.cubie) & np.isin(g2, self.cubie)
        pp = max(0.0, float(-dist[padc].min()) * 1e3) if padc.any() else 0.0
        pc = max(0.0, float(-dist[cc].min()) * 1e3) if cc.any() else 0.0
        return pp, pc

    def step(self, n: int, mv=None) -> None:
        for _ in range(n):
            self.sim.step(1)
            pp, pc = self.pen()
            self.acc["pen_pad"] = max(self.acc["pen_pad"], pp)
            self.acc["pen_cubie"] = max(self.acc["pen_cubie"], pc)
            ms = float(np.linalg.norm(self.d.qpos[self.mount_q] - self.d.ctrl[self.pos_act]) * 1e3)
            self.acc["mount_mm"] = max(self.acc["mount_mm"], ms)
            if self.acc["t_force"] is None and self.tipB_force() > T["causal_force_N"]:
                self.acc["t_force"] = float(self.d.time)
            if self.acc["t_tool"] is None and self.tipB_force() + self.shoulder_force() > T["causal_force_N"]:
                self.acc["t_tool"] = float(self.d.time)
            if self.acc["t_motion"] is None and self.acc.get("bodies") is not None:
                ax = self.acc["axis_world"]
                w = float(np.mean(self.d.cvel[self.acc["bodies"], :3] @ ax) - self.d.cvel[self.core, :3] @ ax)
                if abs(np.degrees(w)) > T["causal_speed_dps"]:
                    self.acc["t_motion"] = float(self.d.time)
            self.acc["tau_max"] = max(self.acc["tau_max"], abs(float(self.d.actuator_force[self.roll])))

    def ramp_grip(self, target: float) -> None:
        start = float(self.d.ctrl[self.gB])
        n = self.secs(abs(target - start) / H.CLOSE_RATE)
        for k in range(1, n + 1):
            self.d.ctrl[self.gB] = start + (target - start) * k / n
            self.step(1)

    def ramp_axial(self, target: float, s: float = 0.3) -> None:
        a = self.pos_act[2]
        start = float(self.d.ctrl[a])
        n = self.secs(s)
        for k in range(1, n + 1):
            self.d.ctrl[a] = start + (target - start) * k / n
            self.step(1)

    def insertion_mm(self) -> float:
        """Depth of the turner fingertips' distal ends below the U face, in the cube frame (mean of the two)."""
        d, m = self.d, self.m
        Rc, pc = d.xmat[self.core].reshape(3, 3), d.xpos[self.core]
        half = 1.5 * self.p.pitch - self.p.gap / 2
        out = []
        for g in self.tipsB:
            Rg = d.geom_xmat[g].reshape(3, 3)
            tip = d.geom_xpos[g] + Rg[:, 2] * m.geom_size[g, 2]          # distal end (local +z = towards the tip)
            out.append(half - float((Rc.T @ (tip - pc))[2]))
        return float(np.mean(out)) * 1e3

    def shoulder_force(self) -> float:
        d, tot = self.d, 0.0
        for i in range(d.ncon):
            c = d.contact[i]
            if c.geom1 in self.shoulders or c.geom2 in self.shoulders:
                mujoco.mj_contactForce(self.m, d, i, self.f6)
                tot += self.f6[0]
        return tot

    def secs(self, s: float) -> int:
        return max(1, int(round(s / self.m.opt.timestep)))

    def move(self, mv, timing: float = 1.0) -> dict:
        m, d, ro = self.m, self.d, self.ro
        self.acc = {"pen_pad": 0.0, "pen_cubie": 0.0, "mount_mm": 0.0, "t_force": None, "t_tool": None, "t_motion": None,
                    "tau_max": 0.0, "bodies": None}
        t0, rested = float(d.time), False                     # 1. rest
        ids = np.append(ro.body_ids, self.core)
        while d.time - t0 < MAX_WAIT:
            if np.degrees(np.linalg.norm(d.cvel[ids, :3], axis=1)).max() < REST_W:
                rested = True
                break
            self.step(1)
        wait = float(d.time) - t0
        _, r0 = ro.poses(d)
        members = ro.layer_members(d, mv.face)
        Rc = d.xmat[self.core].reshape(3, 3)
        self.acc["bodies"] = ro.body_ids[members]
        self.acc["axis_world"] = Rc @ np.array(FACE_NORMAL[mv.face], float)
        p0, R0 = self.rel()
        if self.turner == "c2":                           # C2: pre-close short of the cube, seat the shoulder
            th_pre = self.calib["theta_at_calib_width_rad"] + (C2_PRE_GAP - self.calib["calib_width_m"])                 / self.calib["d_opening_d_theta_m_per_rad"]
            self.ramp_grip(th_pre)
            self.step(self.secs(0.2))
            self.ramp_axial(self.ax_off + C2_PRELOAD)
            self.step(self.secs(0.2))
        self.ramp_grip(bm.DRIVE_RANGE[1])                 # 2. close the turner (ramp)
        self.step(self.secs(0.3))
        insertion = self.insertion_mm()
        shoulder_N = self.shoulder_force()
        # 3. roll: right-hand about U's outward normal = -(turner axis), so the roll target moves by -delta
        delta = -np.pi / 2 * {1: 1, 2: 2, 3: -1}[mv.quarter_turns]
        axis_sign = float(np.sign(self.acc["axis_world"] @ np.array([0, 0, 1.0])))   # U normal vs turner +z
        start = float(d.ctrl[self.roll])
        n = self.secs(timing * abs(delta) / (np.pi / 2))
        for k in range(1, n + 1):
            s = 0.5 - 0.5 * np.cos(np.pi * k / n)
            d.ctrl[self.roll] = start + axis_sign * delta * s
            self.step(1)
        self.step(self.secs(0.3))
        d.ctrl[self.gB] = self.th_open                         # 4. open, roll back
        self.step(self.secs(0.3))
        if self.turner == "c2":
            self.ramp_axial(self.ax_off + C2_PRESEAT)
        _, r1 = ro.poses(d)
        obs = ro.observe(d)
        hold_end = dict(self.acc)
        end = float(d.ctrl[self.roll])
        n = self.secs(1.0)
        for k in range(1, n + 1):
            d.ctrl[self.roll] = end * (1 - (0.5 - 0.5 * np.cos(np.pi * k / n)))
            self.step(1)
        self.step(self.secs(0.3))
        nominal = -90.0 * {1: 1, 2: 2, 3: -1}[mv.quarter_turns]
        rot = ro.rotation_about_deg(r0, r1, members, mv.face)
        err = (rot - nominal + 180.0) % 360.0 - 180.0
        non = [i for i in range(26) if sum(map(abs, scored.HOME_POSITIONS[i])) >= 2 and i not in members]
        drift = np.abs(ro.rotation_about_deg(r0, r1, non, mv.face))
        p1, R1 = self.rel()
        tf, tm, tt = hold_end["t_force"], hold_end["t_motion"], hold_end["t_tool"]
        return {"move": str(mv), "obs": obs, "rest_wait_s": wait, "rested": rested,
                "insertion_mm": insertion, "shoulder_N": shoulder_N,
                "turn_error_deg": float(np.mean(err)), "nontarget_drift_deg": float(drift.max()),
                "pen_cubie_mm": hold_end["pen_cubie"], "pen_pad_mm": hold_end["pen_pad"],
                "mount_excursion_mm": hold_end["mount_mm"], "max_roll_torque_Nm": hold_end["tau_max"],
                "t_tip_force_s": tf, "t_tool_force_s": tt, "t_layer_motion_rel_core_s": tm,
                # tool = turner fingertip pads + (C2) shoulders; the pads-only result is reported alongside
                "ok_causal": bool(tm is None or (tt is not None and tt <= tm)),
                "causal_pads_only": bool(tm is None or (tf is not None and tf <= tm)),
                "core_slip_mm": float(np.linalg.norm(p1 - p0) * 1e3),
                "core_rot_deg": float(np.degrees(np.linalg.norm(Rotation.from_matrix(R1 @ R0.T).as_rotvec())))}


def run(robot_path, calib, seq: str, grip: float, mu: float, k_lin: float, turner: str = "c1",
        ax_off: float = 0.0, lat_off: float = 0.0) -> dict:
    t_wall = time.perf_counter()
    r = Run(robot_path, calib, grip, mu, k_lin, turner, ax_off, lat_off)
    prev = r.ro.observe(r.d)
    rec = {"study": "D17 stage B", "scored": False, "sequence": seq, "grip_N": grip, "scene": r.info,
           "turner": turner, "axial_offset_mm": ax_off * 1e3, "lateral_offset_mm": lat_off * 1e3,
           "shoulder_mm": SHOULDER_PROT * 1e3 if turner == "c2" else None,
           "t0_valid": prev.valid, "t0_solved": bool(prev.valid and prev.state == SOLVED), "per_move": []}
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
    ap.add_argument("--mu", type=float, default=0.8)
    ap.add_argument("--tip-solref", type=float, default=None)
    ap.add_argument("--k-lin", type=float, default=K_LIN)
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--turner", default="c1", choices=("c1", "c2"))
    ap.add_argument("--ax-mm", type=float, default=0.0, help="axial grasp offset (+ = deeper)")
    ap.add_argument("--lat-mm", type=float, default=0.0, help="lateral grasp offset (world x)")
    ap.add_argument("--pilot", action="store_true", help="name the record as a pilot run")
    ap.add_argument("--shoulder-mm", type=float, default=3.0, help="C2 shoulder protrusion")
    a = ap.parse_args()
    H.TIP_SOLREF = None if a.tip_solref is None else (a.tip_solref, 1.0)
    global SHOULDER_PROT
    SHOULDER_PROT = a.shoulder_mm / 1e3
    if a.no_build:                                     # parallel runs: reuse the generated model (no file race)
        robot_path = bm.OUT_DIR / "xarm7_g2_1305+.xml"
        calib = json.loads((bm.OUT_DIR / "xarm7_g2_1305+_gripper_calibration.json").read_text())
    else:
        robot_path, calib = bm.build("1305+", True)
    rec = run(robot_path, calib, a.seq, a.grip, a.mu, a.k_lin, a.turner, a.ax_mm / 1e3, a.lat_mm / 1e3)
    OUT.mkdir(exist_ok=True)
    name = f"turn_F{a.grip:g}_sr{a.tip_solref or 0.001:g}_k{a.k_lin:g}_{a.seq.replace(' ', '_').replace(chr(39), 'p')}"
    if a.pilot or a.turner != "c1" or a.ax_mm or a.lat_mm:   # --pilot: never overwrite a stage-B record
        name = (f"pilot_{a.turner}{'' if a.turner == 'c1' else f'sh{a.shoulder_mm:g}'}_ax{a.ax_mm:+g}_lat{a.lat_mm:g}"
                f"_F{a.grip:g}_sr{a.tip_solref or 0.001:g}")
    (OUT / f"{name}.json").write_text(json.dumps(rec, indent=1, default=float))
    print(json.dumps({k: v for k, v in rec.items() if k not in ("per_move", "scene")}, default=float))


if __name__ == "__main__":
    main()
