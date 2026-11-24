"""Scored G1 trial harness implementing experiments/PHASE_1_PREREGISTRATION.md.

Every function here returns a JSON-serialisable record with raw metrics and
per-criterion booleans. Thresholds live in ``THRESHOLDS`` and must match the
frozen pre-registration (checked by tests/test_scored_harness.py).
"""

from __future__ import annotations

import platform
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import mujoco
import numpy as np

from rubiknetic.cube_logic import (
    HOME_POSITIONS,
    SOLVED,
    InconsistentTransition,
    Move,
    infer_move,
)
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES, to_string

from .m1_model import M1Params, build_m1_xml, cubie_name, params_record
from .readout import CubeReadout
from .rig import AuditedSim, EditAuditError, NumericalFailure, TurnRig, TurnTiming

# ---- frozen thresholds (pre-registration section 4) --------------------------------------
THRESHOLDS = {
    "turn_error_deg": 2.0,
    "nontarget_drift_deg": 1.0,
    "penetration_mm": 0.5,
    "radial_offset_mm": 0.5,
    "radial_above_nominal_mm": 0.3,  # amended 2026-11-12 (pop check vs retention stop), user-approved
    "rest_rotation_deg": 0.5,
    "open_pad_rotation_deg": 0.5,
    "opposed_radial_change_mm": 0.5,
    "causal_force_N": 0.5,
    "causal_speed_dps": 5.0,
    "observed_move_min_deg": 45.0,
}
SCORED_SEED_RANGE = (1000, 1999)
_NONCENTRE = [i for i, h in enumerate(HOME_POSITIONS) if np.count_nonzero(h) >= 2]
REPO = Path(__file__).resolve().parents[3]
FROZEN_PATHS = ["src", "pyproject.toml", "uv.lock", "experiments/PHASE_1_PREREGISTRATION.md",
                "experiments/E1_scored/run.py", "experiments/E1_scored/analyze.py"]


# ---- provenance ---------------------------------------------------------------------------
def _git(*args: str) -> str:
    cmd = ["git", "-c", "core.filemode=false", "-c", "safe.directory=*", "-C", str(REPO), *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()


def require_clean_commit() -> str:
    """Pre-registration rule 1: refuse to score from uncommitted code."""
    dirty = _git("status", "--porcelain", "--", *FROZEN_PATHS)
    if dirty:
        raise SystemExit("refusing to run scored trials: uncommitted changes in frozen paths:\n" + dirty)
    return _git("rev-parse", "HEAD")


def environment() -> dict:
    cpu = platform.processor()
    try:
        with open("/proc/cpuinfo") as f:
            cpu = next(line.split(":", 1)[1].strip() for line in f if line.startswith("model name"))
    except (OSError, StopIteration):
        pass
    return {"mujoco": mujoco.__version__, "numpy": np.__version__, "python": platform.python_version(),
            "platform": platform.platform(), "cpu": cpu}


# ---- per-trial randomisation (pre-registration section 2) ---------------------------------
@dataclass
class TrialSetup:
    seed: int
    misalign_deg: dict
    grip_force: float
    turn_s_per_quarter: float


def draw_setup(seed: int, misalign_max_deg: float = 1.0) -> TrialSetup:
    rng = np.random.default_rng(seed)
    mis = {f: float(rng.uniform(-misalign_max_deg, misalign_max_deg)) for f in FACES}
    return TrialSetup(seed, mis, float(rng.uniform(10.0, 20.0)), float(rng.uniform(0.8, 1.2)))


def apply_setup_misalignment(sim: AuditedSim, misalign_deg: dict) -> None:
    """Episode setup before t=0 (allowed, logged): rotate each face layer's cubies
    about the face axis by a small angle by writing joint positions."""
    m, d = sim.m, sim.d
    for face, deg in misalign_deg.items():
        if deg == 0.0:
            continue
        n = np.array(FACE_NORMAL[face], float)
        q_axis = np.zeros(4)
        mujoco.mju_axisAngle2Quat(q_axis, n, np.radians(deg))
        for h in HOME_POSITIONS:
            if np.dot(h, n) != 1:
                continue
            j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, cubie_name(h) + "_j")
            adr = m.jnt_qposadr[j]
            if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_BALL:
                q_old = d.qpos[adr:adr + 4].copy()
                q_new = np.zeros(4)
                mujoco.mju_mulQuat(q_new, q_axis, q_old)
                d.qpos[adr:adr + 4] = q_new
            elif np.array_equal(np.abs(h), np.abs(n).astype(int)):  # centre of this face
                d.qpos[adr] += np.radians(deg) * float(np.dot(m.jnt_axis[j], n))
        sim.log_setup({"type": "layer_misalignment", "face": face, "deg": deg})
    mujoco.mj_forward(m, d)


# ---- read-only per-step monitor -----------------------------------------------------------
class Monitor:
    def __init__(self, m: mujoco.MjModel, ro: CubeReadout):
        self.m, self.ro = m, ro
        self.r_nominal = np.linalg.norm(np.array(HOME_POSITIONS, float), axis=1) * ro.pitch
        self.pad_geoms = {
            f: np.array([mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, f"pad_{f}{s}_g") for s in "ab"])
            for f in FACES
        }
        self._f6 = np.zeros(6)
        self.r_start: np.ndarray | None = None
        self.window_min_dist = np.inf
        self.max_radial_change = 0.0
        self.max_radial_out = 0.0  # outward excursion (toward popping)
        self.max_radial_in = 0.0   # inward compression of the retention spring
        self.max_above_nominal = -np.inf  # radial position beyond nominal (pop check)
        self.turn = None

    def radii(self, d) -> np.ndarray:
        return np.linalg.norm(d.geom_xpos[self.ro.geom_ids] - d.xpos[self.ro.core], axis=1)

    def start_trial(self, d) -> None:
        self.r_start = self.radii(d)
        self.max_radial_change = 0.0
        self.max_radial_out = 0.0
        self.max_radial_in = 0.0
        self.max_above_nominal = -np.inf

    def new_window(self) -> None:
        self.window_min_dist = np.inf

    def begin_turn(self, face: str, members: list[int]) -> None:
        axis = np.array(FACE_NORMAL[face], float)
        self.turn = {"face": face, "bodies": self.ro.body_ids[members], "axis": axis, "t_force": None,
                     "t_speed": None}

    def end_turn(self) -> dict:
        t, self.turn = self.turn, None
        causal = t["t_speed"] is None or (t["t_force"] is not None and t["t_force"] <= t["t_speed"])
        return {"t_pad_force_s": t["t_force"], "t_layer_motion_s": t["t_speed"], "causal": bool(causal)}

    def __call__(self, d) -> None:
        n = d.ncon
        if n:
            self.window_min_dist = min(self.window_min_dist, float(d.contact.dist[:n].min()))
        if self.r_start is not None:
            r = self.radii(d)
            dr = r - self.r_start
            self.max_above_nominal = max(self.max_above_nominal, float((r - self.r_nominal).max()))
            self.max_radial_change = max(self.max_radial_change, float(np.abs(dr).max()))
            self.max_radial_out = max(self.max_radial_out, float(dr.max()))
            self.max_radial_in = max(self.max_radial_in, float(-dr.min()))
        t = self.turn
        if t is None:
            return
        if t["t_force"] is None and n:
            g1, g2 = d.contact.geom1[:n], d.contact.geom2[:n]
            pads = self.pad_geoms[t["face"]]
            idx = np.nonzero(np.isin(g1, pads) | np.isin(g2, pads))[0]
            total = 0.0
            for i in idx:
                mujoco.mj_contactForce(self.m, d, int(i), self._f6)
                total += self._f6[0]
            if total > THRESHOLDS["causal_force_N"]:
                t["t_force"] = float(d.time)
        if t["t_speed"] is None:
            w = d.cvel[t["bodies"], :3] @ t["axis"]
            if abs(np.degrees(np.mean(w))) > THRESHOLDS["causal_speed_dps"]:
                t["t_speed"] = float(d.time)


# ---- environment for one trial ------------------------------------------------------------
class Trial:
    def __init__(self, params: M1Params, setup: TrialSetup | None, allow_test_wrench: bool = False,
                 settle_s: float = 0.5):
        self.params = params
        self.model = mujoco.MjModel.from_xml_string(build_m1_xml(params))
        self.sim = AuditedSim(self.model, allow_test_wrench=allow_test_wrench)
        self.ro = CubeReadout(self.model, params.pitch)
        self.rig = TurnRig(self.sim, pad_close_target=-(params.pad_open_clearance + params.grip_overshoot))
        self.mon = Monitor(self.model, self.ro)
        self.sim.hooks.append(self.mon)
        self.setup = setup
        if setup is not None:
            apply_setup_misalignment(self.sim, setup.misalign_deg)
        self.sim.step(int(round(settle_s / self.model.opt.timestep)))
        self.mon.start_trial(self.sim.d)
        self.mon.new_window()
        self.timing = TurnTiming(turn_s_per_quarter=setup.turn_s_per_quarter) if setup else TurnTiming()
        self.t0_obs = self.ro.observe(self.sim.d)

    def radial_offset_mm(self) -> float:
        r = self.mon.radii(self.sim.d)[_NONCENTRE]
        return float(np.abs(r - self.mon.r_nominal[_NONCENTRE]).max() * 1000)

    def base_record(self) -> dict:
        return {
            "params": params_record(self.params),
            "setup": asdict(self.setup) if self.setup else None,
            "setup_log": self.sim.setup_log,
            "t0_observed_valid": self.t0_obs.valid,
            "t0_solved": bool(self.t0_obs.valid and self.t0_obs.state == SOLVED),
            "radial_offset_mm_t0": self.radial_offset_mm(),
        }

    def finish(self, rec: dict) -> dict:
        rec["edit_audit_violations"] = self.sim.violations
        rec["numerical_failures"] = self.sim.numerical_failures
        rec["wrench_log_entries"] = len(self.sim.wrench_log)
        rec["sim_time_s"] = float(self.sim.d.time)
        rec["integrity_ok"] = not self.sim.violations and not self.sim.numerical_failures
        return rec


def params_for(setup: TrialSetup | None, **overrides) -> M1Params:
    kw = dict(overrides)
    if setup is not None and "grip_force" not in kw:
        kw["grip_force"] = setup.grip_force
    return M1Params(**kw)


# ---- scored move sequence (E1-2, E1-3, E1-4, E1-7) ---------------------------------------
def run_sequence_trial(moves: list[Move], seed: int, misalign_max_deg: float = 1.0, **overrides) -> dict:
    setup = draw_setup(seed, misalign_max_deg)
    tr = Trial(params_for(setup, **overrides), setup)
    ro, d, mon = tr.ro, tr.sim.d, tr.mon
    rec = tr.base_record()
    rec.update({"sequence": to_string(moves), "seed": seed, "per_move": []})
    expect = SOLVED
    prev = tr.t0_obs
    wall = time.perf_counter()
    try:
        for mv in moves:
            _, r0 = ro.poses(d)
            members = {f: ro.layer_members(d, f) for f in FACES}
            mon.new_window()
            mon.begin_turn(mv.face, members[mv.face])
            log = tr.rig.turn(mv, tr.timing)
            causal = mon.end_turn()
            _, r1 = ro.poses(d)
            obs = ro.observe(d)
            nominal = -90.0 * {1: 1, 2: 2, 3: -1}[mv.quarter_turns]
            rot = ro.rotation_about_deg(r0, r1, members[mv.face], mv.face)
            err = (rot - nominal + 180.0) % 360.0 - 180.0
            nontarget = [i for i in _NONCENTRE if i not in members[mv.face]]
            drift = np.abs(ro.rotation_about_deg(r0, r1, nontarget, mv.face))
            observed, inference_error = None, None
            if prev.valid and obs.valid:
                try:
                    observed = infer_move(prev.cube, obs.cube)
                except InconsistentTransition as e:
                    inference_error = str(e)
            if observed is not None:
                expect = expect.apply(observed)  # oracle driven by the OBSERVED move
            oracle_ok = bool(obs.valid and observed == mv and obs.state == expect)
            pen = max(0.0, -mon.window_min_dist) * 1000
            r = {
                "move": str(mv),
                "observed_move": str(observed) if observed else None,
                "inference_error": inference_error,
                "observed_valid": obs.valid,
                "turn_error_deg": float(np.mean(err)),
                "turn_error_spread_deg": float(np.ptp(err)),
                "nontarget_drift_deg": float(drift.max()),
                "penetration_mm": pen,
                "radial_change_mm_so_far": mon.max_radial_change * 1000,
                "radial_outward_mm_so_far": mon.max_radial_out * 1000,
                "radial_inward_mm_so_far": mon.max_radial_in * 1000,
                "radial_above_nominal_mm_so_far": mon.max_above_nominal * 1000,
                "max_turner_torque_Nm": float(np.max(np.abs(log.turner_torque))),
                **causal,
                "ok_oracle": oracle_ok,
                "ok_turn_error": bool(abs(np.mean(err)) <= THRESHOLDS["turn_error_deg"]),
                "ok_drift": bool(drift.max() <= THRESHOLDS["nontarget_drift_deg"]),
                "ok_penetration": bool(pen <= THRESHOLDS["penetration_mm"]),
                "ok_radial_pop": bool(mon.max_above_nominal * 1000 <= THRESHOLDS["radial_above_nominal_mm"]),
                "ok_causal": causal["causal"],
            }
            r["ok_all"] = all(v for k, v in r.items() if k.startswith("ok_") and k != "ok_all")
            rec["per_move"].append(r)
            prev = obs
            if not oracle_ok:
                break  # state no longer tracked; trial already failed
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    rec["wall_time_s"] = time.perf_counter() - wall
    final = ro.observe(d) if "aborted" not in rec else None
    rec["final_matches_oracle"] = bool(final is not None and final.valid and final.state == expect)
    rec["expected_final_solved"] = SOLVED.apply_all(moves).is_solved()
    rec["moves_completed_ok"] = sum(1 for r in rec["per_move"] if r["ok_all"])
    tr.finish(rec)
    rec["pass"] = bool(rec["integrity_ok"] and "aborted" not in rec and rec["t0_solved"]
                       and len(rec["per_move"]) == len(moves) and all(r["ok_all"] for r in rec["per_move"])
                       and rec["final_matches_oracle"])
    return rec


# ---- E1-1 static rest ---------------------------------------------------------------------
def run_rest_trial(seed: int, duration_s: float = 10.0) -> dict:
    setup = draw_setup(seed)
    tr = Trial(params_for(setup), setup)
    ro, d, mon = tr.ro, tr.sim.d, tr.mon
    rec = tr.base_record()
    rec["seed"] = seed
    _, r0 = ro.poses(d)
    members = {f: ro.layer_members(d, f) for f in FACES}
    worst = 0.0
    steps = int(round(duration_s / tr.model.opt.timestep))
    try:
        for k in range(0, steps, 50):
            tr.sim.step(min(50, steps - k))
            _, r = ro.poses(d)
            for f in FACES:
                worst = max(worst, float(np.abs(ro.rotation_about_deg(r0, r, members[f], f)).max()))
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    obs = ro.observe(d)
    pen = max(0.0, -mon.window_min_dist) * 1000
    rec.update({
        "rest_rotation_deg": worst,
        "radial_change_mm": mon.max_radial_change * 1000,
        "radial_above_nominal_mm": mon.max_above_nominal * 1000,
        "penetration_mm": pen,
        "final_solved": bool(obs.valid and obs.state == SOLVED),
        "ok_solved": bool(obs.valid and obs.state == SOLVED and rec["t0_solved"]),
        "ok_rest_rotation": worst <= THRESHOLDS["rest_rotation_deg"],
        "ok_radial_offset": rec["radial_offset_mm_t0"] <= THRESHOLDS["radial_offset_mm"],
        "ok_radial_pop": mon.max_above_nominal * 1000 <= THRESHOLDS["radial_above_nominal_mm"],
        "ok_penetration": pen <= THRESHOLDS["penetration_mm"],
    })
    tr.finish(rec)
    rec["pass"] = bool(rec["integrity_ok"] and "aborted" not in rec
                       and all(v for k, v in rec.items() if k.startswith("ok_")))
    return rec


# ---- E1-5 forgiveness / E1-6d -------------------------------------------------------------
def run_forgiveness_trial(misalign_deg: float, seed: int) -> dict:
    """Physically misalign U by ``misalign_deg`` (signed, right-hand about +z), then
    attempt R. Categorical: never an illegal or oracle-mismatched state."""
    setup = draw_setup(seed)
    tr = Trial(params_for(setup), setup)
    ro, d = tr.ro, tr.sim.d
    rec = tr.base_record()
    rec.update({"seed": seed, "commanded_U_misalignment_deg": misalign_deg})
    try:
        _, r0 = ro.poses(d)
        mem0 = {f: ro.layer_members(d, f) for f in FACES}
        if misalign_deg:
            tr.rig.rotate({"U": np.radians(misalign_deg)}, grip=True, timing=tr.timing)
        _, r1 = ro.poses(d)
        rec["U_misalignment_deg"] = float(np.mean(ro.rotation_about_deg(r0, r1, mem0["U"], "U")))
        mem1 = {f: ro.layer_members(d, f) for f in FACES}
        tr.rig.turn(Move("R", 1), tr.timing)
        _, r2 = ro.poses(d)
        rec["R_rotation_deg"] = float(np.mean(ro.rotation_about_deg(r1, r2, mem1["R"], "R")))
        u_only = [i for i in mem1["U"] if i not in mem1["R"]]
        rec["U_change_during_R_deg"] = float(np.mean(ro.rotation_about_deg(r1, r2, u_only, "U")))
        obs = ro.observe(d)
        rec["observed_valid"] = obs.valid
        if obs.valid:
            try:
                mv = infer_move(tr.t0_obs.cube, obs.cube)
                rec["observed_move"] = str(mv) if mv else None
                ok = obs.state == SOLVED.apply_all([mv] if mv else [])
                rec["outcome"] = "completed" if mv else "no_net_move"
            except InconsistentTransition as e:
                rec["inference_error"] = str(e)
                ok = False
                rec["outcome"] = "illegal_transition"
        else:
            ok = True  # UNKNOWN is an allowed outcome; the reader refused to guess
            rec["outcome"] = "blocked_unknown"
        rec["ok_categorical"] = bool(ok)
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
        rec["ok_categorical"] = False
    tr.finish(rec)
    rec["pass"] = bool(rec["integrity_ok"] and "aborted" not in rec and rec["ok_categorical"] and rec["t0_solved"])
    return rec


# ---- E1-6a/b/c ----------------------------------------------------------------------------
def run_open_pad_trial(face: str, seed: int) -> dict:
    setup = draw_setup(seed)
    tr = Trial(params_for(setup), setup)
    ro, d = tr.ro, tr.sim.d
    rec = tr.base_record()
    rec.update({"seed": seed, "face": face})
    try:
        _, r0 = ro.poses(d)
        mem = ro.layer_members(d, face)
        tr.rig.rotate({face: -np.pi / 2}, grip=False, timing=tr.timing)
        _, r1 = ro.poses(d)
        rot = float(np.abs(ro.rotation_about_deg(r0, r1, mem, face)).max())
        obs = ro.observe(d)
        rec.update({"layer_rotation_deg": rot,
                    "ok_no_motion": rot <= THRESHOLDS["open_pad_rotation_deg"],
                    "ok_solved": bool(obs.valid and obs.state == SOLVED)})
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    tr.finish(rec)
    rec["pass"] = bool(rec["integrity_ok"] and "aborted" not in rec and rec.get("ok_no_motion")
                       and rec.get("ok_solved") and rec["t0_solved"])
    return rec


def run_opposed_trial(faces: tuple[str, str], torque_limit: float, seed: int) -> dict:
    setup = draw_setup(seed)
    tr = Trial(params_for(setup, turn_torque_limit=torque_limit), setup)
    ro, d, mon = tr.ro, tr.sim.d, tr.mon
    rec = tr.base_record()
    rec.update({"seed": seed, "faces": list(faces), "torque_limit_Nm": torque_limit})
    try:
        _, r0 = ro.poses(d)
        mem = {f: ro.layer_members(d, f) for f in faces}
        mon.new_window()
        tr.rig.rotate({f: -np.pi / 2 for f in faces}, grip=True, timing=tr.timing)
        _, r1 = ro.poses(d)
        rots = {f: float(np.mean(ro.rotation_about_deg(r0, r1, mem[f], f))) for f in faces}
        obs = ro.observe(d)
        consistent = True
        if obs.valid:
            try:
                mv = infer_move(tr.t0_obs.cube, obs.cube)
                consistent = obs.state == SOLVED.apply_all([mv] if mv else [])
                rec["observed_move"] = str(mv) if mv else None
            except InconsistentTransition as e:
                consistent, rec["inference_error"] = False, str(e)
        both = all(abs(v) >= 45.0 for v in rots.values())
        rec.update({"layer_rotations_deg": rots, "observed_valid": obs.valid,
                    "penetration_mm_reported_only": max(0.0, -mon.window_min_dist) * 1000,
                    "radial_change_mm": mon.max_radial_change * 1000,
                    "ok_not_both_rotated": not both, "ok_state_consistent": bool(consistent),
                    "ok_no_separation": mon.max_radial_change * 1000 <= THRESHOLDS["opposed_radial_change_mm"]})
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    tr.finish(rec)
    rec["pass"] = bool(rec["integrity_ok"] and "aborted" not in rec and rec["t0_solved"]
                       and all(v for k, v in rec.items() if k.startswith("ok_")))
    return rec


def run_corner_twist_trial(corner: tuple[int, int, int], seed: int, peak_Nm: float = 5.0,
                           ramp_s: float = 2.0, hold_s: float = 0.5, settle_s: float = 0.5) -> dict:
    """E1-6c with the logged test wrench (P-12): torque about the corner's own
    diagonal, ramped, held, released."""
    setup = draw_setup(seed)
    tr = Trial(params_for(setup), setup, allow_test_wrench=True)
    ro, d, mon, sim = tr.ro, tr.sim.d, tr.mon, tr.sim
    rec = tr.base_record()
    rec.update({"seed": seed, "corner": list(corner), "peak_torque_Nm": peak_Nm})
    idx = HOME_POSITIONS.index(tuple(corner))
    body = int(ro.body_ids[idx])
    axis = np.array(corner, float) / np.sqrt(3)
    _, rot0 = ro.poses(d)
    dt = tr.model.opt.timestep
    twist_max, load_at_15 = 0.0, None

    def twist_deg() -> float:
        _, rot = ro.poses(d)
        rel = rot[idx] @ rot0[idx].T
        ang = np.degrees(np.arccos(np.clip((np.trace(rel) - 1) / 2, -1, 1)))
        return float(ang)

    try:
        mon.new_window()
        n_ramp, n_hold = int(ramp_s / dt), int(hold_s / dt)
        for k in range(n_ramp + n_hold):
            tau = peak_Nm * min(1.0, (k + 1) / n_ramp)
            sim.set_test_wrench(body, np.concatenate([np.zeros(3), tau * axis]))
            sim.step()
            if k % 20 == 0:
                tw = twist_deg()
                twist_max = max(twist_max, tw)
                if load_at_15 is None and tw > 15.0:
                    load_at_15 = tau
        sim.set_test_wrench(body, np.zeros(6))
        sim.step(int(settle_s / dt))
        obs = ro.observe(d)
        rec.update({
            "max_twist_deg": twist_max, "torque_at_twist_15deg_Nm": load_at_15,
            "penetration_mm_reported_only": max(0.0, -mon.window_min_dist) * 1000,
            "radial_change_mm": mon.max_radial_change * 1000,
            "final_observed_valid": obs.valid,
            "final_solved": bool(obs.valid and obs.state == SOLVED),
            "ok_no_false_valid_state": bool((not obs.valid) or obs.state == SOLVED),
        })
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    tr.finish(rec)
    rec["pass"] = bool(rec["integrity_ok"] and "aborted" not in rec and rec["t0_solved"]
                       and rec.get("ok_no_false_valid_state"))
    return rec
