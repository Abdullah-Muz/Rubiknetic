"""D23 (UNSCORED feasibility, findings Q2, P-134 optional side work): is a hardware-style controller stable for arm B?

Arm B's joints 1-7 are driven by stiff joint POSITION servos (MuJoCo position actuators with arm A's Menagerie gains
times SERVO_GAIN; implicit damping under implicitfast), the way the real xArm accepts only position setpoints. An outer
ADMITTANCE loop at 250 Hz (every 8 physics steps at dt 0.5 ms; zero-order hold between ticks) turns the measured wrist
force (the modelled F/T sensor, P-114; tared in the world frame before the approach; Gaussian noise) into a Cartesian
setpoint offset of the gripper base:

    M * dd(delta) + D * d(delta) + K * delta = F_ext(t - delay),   x_cmd = x_ref + delta,

integrated per tick (semi-implicit Euler), using the F/T sample `delay` ticks old (1-3). x_cmd and the nominal gripper
axis go through a damped-least-squares IK on a standalone copy of arm B's model (seeded by the previous COMMANDED
joint vector, as the controller's own internal state) to joint setpoints for J1-J6; J7 receives the roll setpoint.

The controller reads only: the F/T samples, its own commanded joint vector, targets and time. It never reads the cube
or cubie state (CLAUDE.md, P-16). Cube state is read OFFLINE for metrics only (core slip relative to arm A, layer
rotation, readout), after the control decision of each tick.

Modes: adm (admittance as above), stiff (position servo only, delta = 0: no compliance), g2 (G2's own torque-level
impedance + J7 torque law, unmodified, as the reference).

Sequence (after the G2 start sequence with arm A holding, magnets on; seeded start draw):
  tare 0.2 s -> approach 1 s (cosine, 40 mm along the axis) -> settle 0.5 s -> close arm B's gripper (G2 rate) ->
  hold HOLD_S [task 1] -> roll J7 a quarter turn (U) on a cosine over ROLL_S [task 2] -> hold 0.3 s -> open 0.3 s.
Usage (WSL): python admittance.py --mode adm --K 500 --M 1 --delay 1 [--zeta 0.8] [--servo-gain 1] [--seed 29001]
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
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "experiments" / "E8_scored_g2"))
import trials as TR  # noqa: E402  (read-only import of the frozen G2 harness)

TA = TR.TA
H, bm = TA.H, TA.bm
from rubiknetic.cube_logic import SOLVED, InconsistentTransition, infer_move  # noqa: E402
from rubiknetic.cube_physics.magnets import MagnetSystem  # noqa: E402
from rubiknetic.cube_physics.readout import CubeReadout  # noqa: E402
from rubiknetic.cube_physics.rig import EditAuditError, NumericalFailure  # noqa: E402

TICK = 8                 # physics steps per controller tick (250 Hz at dt 0.5 ms)
FT_FORCE_NOISE = 0.1     # N, 1 sigma per axis (ASSUMPTION; not a UFACTORY figure)
DIVERGE_MM = 30.0        # |delta| beyond this aborts the run as UNSTABLE (safety stop)
TARE_S, SETTLE_S, HOLD_S, ROLL_S = 0.2, 0.5, 1.5, 1.5
IK_ITERS, IK_DAMP = 3, 1e-4
CFG: dict = {}


# ---- model edit (in memory, on this process's copy only) ----------------------------------------------------------
_orig_build = TA.build


def _build_position_servos(L, Hc, mu):
    """TA.build, then arm B's J1-J6 torque motors are turned back into position servos with arm A's gains x SERVO_GAIN
    (J7 is already a servo when TA.ROLL_MODE == 'servo'; its gains are scaled too)."""
    m, p, info, A, B, half = _orig_build(L, Hc, mu)
    g = CFG.get("servo_gain", 1.0)
    for i in range(1, 8):
        a, aB = m.actuator(f"act{i}").id, m.actuator(f"B_act{i}").id
        m.actuator_gainprm[aB, :] = m.actuator_gainprm[a, :]
        m.actuator_biasprm[aB, :] = m.actuator_biasprm[a, :]
        m.actuator_gainprm[aB, 0] *= g
        m.actuator_biasprm[aB, 1:3] *= g
        m.actuator_ctrlrange[aB] = m.actuator_ctrlrange[a] if i < 7 else m.jnt_range[m.joint("B_joint7").id]
    info["armB_control"] = f"position servos (arm A gains x {g}), admittance mode {CFG.get('mode')}"
    return m, p, info, A, B, half


class AdmArm(TA.TwoArm):
    def __init__(self, cfg: dict, L: float, Hc: float, grip: float):
        self.cfg = cfg
        self.mode = cfg["mode"]
        # standalone arm-B model for the controller's IK: built BEFORE the scene (b_robot_spec uninstalls the magnet
        # callback; TwoArm re-installs it after its own standalone model)
        sp = TA.b_robot_spec()
        for k in list(sp.keys):
            sp.delete(k)
        self.mk = sp.compile()
        self.dk = mujoco.MjData(self.mk)
        self.k_qa = np.array([self.mk.jnt_qposadr[self.mk.joint(j).id] for j in bm.ARM_JOINTS])
        self.k_va = np.array([self.mk.jnt_dofadr[self.mk.joint(j).id] for j in bm.ARM_JOINTS])
        self.k_b = self.mk.body("xarm_gripper_base_link").id
        self.k_lo, self.k_hi = self.mk.jnt_range[[self.mk.joint(j).id for j in bm.ARM_JOINTS]].T
        self.k_jp, self.k_jr = np.zeros((3, self.mk.nv)), np.zeros((3, self.mk.nv))
        self.nstep = 0
        self.adm_on = False           # off during the start sequence: arm B holds its pre-grasp joint vector
        self.delta = np.zeros(3)
        self.ddelta = np.zeros(3)
        self.f_tare = None
        self.ft_buf: list[np.ndarray] = []
        self.ft_rng2 = np.random.default_rng(cfg["seed"])
        self.roll_target = None
        self.q_cmd = None
        self.log_step: list = []      # per physics step (metrics only)
        self.log_tick: list = []      # per tick (metrics only)
        self.logging = False
        self.diverged = None
        super().__init__(L, Hc, grip)

    # ---- the controller (robot-side signals only) ------------------------------------------------------------
    def ft_world_raw(self) -> np.ndarray:
        """F/T force sample in the world frame (the sensor's own orientation from arm kinematics)."""
        m, d = self.m, self.d
        if not hasattr(self, "_ft_ids"):
            self._ft_ids = (m.site("B_ft_site").id, int(m.sensor_adr[m.sensor("B_ft_force").id]))
        s, adr = self._ft_ids
        return d.site_xmat[s].reshape(3, 3) @ d.sensordata[adr:adr + 3]

    def ik(self, x_cmd_w: np.ndarray, a_d_w: np.ndarray, q7: float) -> None:
        L = TR.L
        p_t = TA.YAW180.T @ (x_cmd_w - np.array([L, 0, 0]))
        a_t = TA.YAW180.T @ a_d_w
        m, d = self.mk, self.dk
        q = self.q_cmd.copy()
        q[6] = q7
        for _ in range(IK_ITERS):
            d.qpos[self.k_qa] = q
            mujoco.mj_kinematics(m, d)
            mujoco.mj_comPos(m, d)
            R = d.xmat[self.k_b].reshape(3, 3)
            ep = p_t - d.xpos[self.k_b]
            er = np.cross(R[:, 2], a_t)
            mujoco.mj_jacBody(m, d, self.k_jp, self.k_jr, self.k_b)
            J = np.vstack([self.k_jp[:, self.k_va[:6]], self.k_jr[:, self.k_va[:6]]])
            dq = J.T @ np.linalg.solve(J @ J.T + IK_DAMP * np.eye(6), np.concatenate([ep, er]))
            q[:6] = np.clip(q[:6] + dq, self.k_lo[:6], self.k_hi[:6])
        self.q_cmd = q

    def tick(self) -> None:
        d = self.d
        f_raw = self.ft_world_raw()
        f_meas = f_raw + self.ft_rng2.normal(0.0, FT_FORCE_NOISE, 3)
        if self.q_cmd is None:
            self.q_cmd = self.q0B.copy()
            self.roll_target = float(self.q0B[6])
        if not self.adm_on or self.mode == "stiff":
            fext = np.zeros(3)
        else:
            fe = -(f_meas - self.f_tare)                          # F_ext = -(f - f_tare) (probe_ft_sign.py)
            lp = self.cfg.get("ft_lp_hz", 0.0)
            if lp:                                                # optional first-order low-pass at the tick rate
                al = 1.0 - np.exp(-2 * np.pi * lp * TICK * self.m.opt.timestep)
                self._f_lp = fe if not hasattr(self, "_f_lp") else self._f_lp + al * (fe - self._f_lp)
                fe = self._f_lp.copy()
            self.ft_buf.append(fe)
            k = len(self.ft_buf) - 1 - self.cfg["delay"]
            fext = self.ft_buf[k] if k >= 0 else np.zeros(3)
            if len(self.ft_buf) > 16:
                del self.ft_buf[0]
            K, M, D, T = self.cfg["K"], self.cfg["M"], self.cfg["D"], TICK * self.m.opt.timestep
            acc = (fext - D * self.ddelta - K * self.delta) / M
            self.ddelta += T * acc
            self.delta += T * self.ddelta
            if np.linalg.norm(self.delta) * 1e3 > DIVERGE_MM and self.diverged is None:
                self.diverged = float(d.time)
        x_cmd = self.p_d + self.delta
        self.ik(x_cmd, self.a_d, self.roll_target)
        d.ctrl[self.aB] = self.q_cmd
        self._last_fext_used = fext
        self._last_xcmd = x_cmd

    def impedance(self) -> None:          # called by ctrl_step before every physics step
        if self.mode == "g2":
            TA.TwoArm.impedance(self)
        elif self.nstep % TICK == 0:
            self.tick()
        self.nstep += 1
        if self.logging:
            d = self.d
            self.log_step.append(np.concatenate([[d.time], d.xpos[self.bodyB], self.ft_world_raw(),
                                                 getattr(self, "_last_xcmd", self.p_d)]))

    def set_roll(self, q: float, qd: float = 0.0, qdd: float = 0.0) -> None:
        if self.mode == "g2":
            TA.TwoArm.set_roll(self, q, qd, qdd)
        else:
            self.roll_target = q          # applied at the next tick (one-sample hold)

    def roll_cmd(self) -> float:
        return TA.TwoArm.roll_cmd(self) if self.mode == "g2" else float(self.roll_target)


# ---- the trial ------------------------------------------------------------------------------------------------------
def run(cfg: dict) -> dict:
    global CFG
    CFG = cfg
    t_wall = time.perf_counter()
    start = TR.start_draw(cfg["seed"])
    TR.configure({}, start)
    if cfg["mode"] != "g2":
        TA.ROLL_MODE = "servo"
        TA.build = _build_position_servos
    rec = {"study": "D23 admittance Q2", "scored": False, "cfg": cfg, "start_draw": start}
    try:
        r = AdmArm(cfg, TR.L, TR.HC, TR.DEFAULTS["grip"])
        m, d = r.m, r.d
        rec["start"] = r.start
        rec["model_audit"] = r.model_audit
        rec["scene_armB"] = r.info.get("armB_control", "G2 torque impedance")
        obs0 = r.ro.observe(d)
        rec["t0_solved"] = bool(obs0.valid and obs0.state == SOLVED)
        p0, R0 = r.rel()
        r.new_acc()
        r.logging = True
        phases = {}
        slip_tick = []

        def advance(n: int, phase: str, per_step=None):
            t_a = float(d.time)
            k = 0
            while k < n:
                if per_step is not None:
                    per_step(k)
                r.step(1)
                k += 1
                if r.nstep % TICK == 0:
                    p, R = r.rel()                                   # METRICS ONLY (cube state)
                    rot = float(np.degrees(np.linalg.norm(Rotation.from_matrix(R @ R0.T).as_rotvec())))
                    slip_tick.append([float(d.time), float(np.linalg.norm(p - p0) * 1e3), rot,
                                      r.tips_cubie_force(), *getattr(r, "_last_fext_used", np.zeros(3)),
                                      *r.delta])
                if r.diverged is not None:
                    raise RuntimeError(f"admittance diverged (|delta| > {DIVERGE_MM} mm) at t = {r.diverged:.3f} s")
            phases[phase] = [t_a, float(d.time)]

        # tare (controller-side, from noisy F/T samples while arm B is free)
        tare = []
        advance(r.secs(TARE_S), "tare", per_step=lambda k: tare.append(r.ft_world_raw()) if k % TICK == 0 else None)
        r.f_tare = np.mean(tare, axis=0) + r.ft_rng2.normal(0.0, FT_FORCE_NOISE / np.sqrt(len(tare)), 3)
        rec["f_tare_N"] = r.f_tare.tolist()
        r.adm_on = True
        n = r.secs(1.0)
        pre, grasp = r.pB_pre.copy(), r.pB_grasp.copy()

        def appr(k):
            s = 0.5 - 0.5 * np.cos(np.pi * (k + 1) / n)
            r.p_d = pre + s * (grasp - pre)
        advance(n, "approach", appr)
        advance(r.secs(SETTLE_S), "settle")
        r.integ = False                                           # (G2 mode: integral frozen while gripping)
        g0 = float(d.ctrl[r.gB])
        ng = r.secs(abs(bm.DRIVE_RANGE[1] - g0) / H.CLOSE_RATE)
        advance(ng, "close", lambda k: d.ctrl.__setitem__(r.gB, g0 + (bm.DRIVE_RANGE[1] - g0) * (k + 1) / ng))
        advance(r.secs(HOLD_S), "hold")
        # task 2: quarter turn U, slow cosine roll (direction from the nominal layout, as G2)
        ro: CubeReadout = r.ro
        _, rots0 = ro.poses(d)
        members = ro.layer_members(d, "U")                        # METRICS ONLY
        prev = ro.observe(d)
        delta_roll = -np.pi / 2
        A = r.roll_sign * delta_roll
        q_start = r.roll_cmd()
        nr = r.secs(ROLL_S)
        Tn = nr * m.opt.timestep

        def roll(k):
            ph = np.pi * (k + 1) / nr
            r.set_roll(q_start + A * (0.5 - 0.5 * np.cos(ph)), A * np.pi / (2 * Tn) * np.sin(ph),
                       A * np.pi ** 2 / (2 * Tn ** 2) * np.cos(ph))
        advance(nr, "roll", roll)
        r.set_roll(r.roll_cmd())
        advance(r.secs(0.3), "roll_hold")
        d.ctrl[r.gB] = r.th_open
        advance(r.secs(0.3), "open")
        _, rots1 = ro.poses(d)
        obs = ro.observe(d)
        observed = None
        if prev.valid and obs.valid:
            try:
                observed = infer_move(prev.cube, obs.cube)
            except InconsistentTransition as e:
                rec["inference_error"] = str(e)
        layer_rot = ro.rotation_about_deg(rots0, rots1, members, "U")
        rec["turn"] = {"observed_move": str(observed) if observed else None,
                       "layer_rot_mean_deg": float(np.mean(layer_rot)),
                       "turn_error_deg": float(((np.mean(layer_rot) - (-90.0)) + 180) % 360 - 180),
                       "final_valid": bool(obs.valid),
                       "j7_roll_done_deg": float(np.degrees(r.roll_sign * (d.qpos[r.qB[6]] - q_start)))}
        rec["phases"] = phases
        rec["contacts"] = {k: v for k, v in r.acc.items() if k in TA.CONTACT_KEYS}
        rec["residual_end_deg_max"] = max(TA.lattice_residual_deg(ro.poses(d)[1]))
    except (NumericalFailure, EditAuditError, RuntimeError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
        rec["phases"] = locals().get("phases", {})
        if "r" in locals():
            rec["contacts"] = {k: v for k, v in r.acc.items() if k in TA.CONTACT_KEYS}
    finally:
        MagnetSystem.uninstall()
    if "r" in locals():
        rec["magnets"] = r.magnet_stats()
        rec["audit_violations"] = r.sim.violations
        rec["numerical_failures"] = r.sim.numerical_failures
        rec["sim_time_s"] = float(r.d.time)
        rec["_log_step"] = np.array(r.log_step)
        rec["_log_tick"] = np.array(locals().get("slip_tick", []))
    rec["wall_s"] = time.perf_counter() - t_wall
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="adm", choices=("adm", "stiff", "g2"))
    ap.add_argument("--K", type=float, default=500.0)
    ap.add_argument("--M", type=float, default=1.0)
    ap.add_argument("--zeta", type=float, default=0.8)
    ap.add_argument("--delay", type=int, default=1)
    ap.add_argument("--servo-gain", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=29001)
    ap.add_argument("--D", type=float, default=None, help="explicit admittance damping (N.s/m); overrides zeta")
    ap.add_argument("--ft-lp", type=float, default=0.0, help="first-order low-pass on the F/T force (Hz); 0 = off")
    ap.add_argument("--out", default=str(HERE / "results"))
    a = ap.parse_args()
    assert 29000 <= a.seed <= 29999, "pilot seeds only"
    cfg = {"mode": a.mode, "K": a.K, "M": a.M, "zeta": a.zeta, "D": a.D if a.D is not None else 2 * a.zeta * np.sqrt(a.K * a.M), "ft_lp_hz": a.ft_lp,
           "delay": a.delay, "servo_gain": a.servo_gain, "seed": a.seed, "tick_hz": 1.0 / (TICK * 0.0005),
           "ft_force_noise_N": FT_FORCE_NOISE}
    damp = f"z{a.zeta:g}" if a.D is None else f"D{a.D:g}"
    name = (f"{a.mode}_K{a.K:g}_M{a.M:g}_d{a.delay}_{damp}_sg{a.servo_gain:g}_s{a.seed}" if a.mode == "adm"
            else f"{a.mode}_sg{a.servo_gain:g}_s{a.seed}")
    if a.ft_lp:
        name += f"_lp{a.ft_lp:g}"
    rec = run(cfg)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / f"{name}_trace.npz", step=rec.pop("_log_step", np.zeros(0)),
                        tick=rec.pop("_log_tick", np.zeros(0)))
    rec["name"] = name
    (out / f"{name}.json").write_text(json.dumps(rec, indent=1, default=float))
    print(json.dumps({k: rec.get(k) for k in ("name", "aborted", "turn", "contacts", "wall_s", "sim_time_s")},
                     default=float), flush=True)


if __name__ == "__main__":
    main()
