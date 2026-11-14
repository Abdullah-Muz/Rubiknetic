"""Scored G1 trial harness for M2 (experiments/PHASE_1_M2_PREREGISTRATION.md).

* Reuses the M1 harness by import: setup draws, setup misalignment, Monitor and provenance.
* M1's thresholds are kept unchanged. The M2 additions (NEW in the pre-registration) live in ``THRESHOLDS_M2``.
* Every record carries params, switch rule, weld parameters, setup and setup log, the full switch log, integrity
  fields, source_commit and environment (the last two are added by the runner).
"""

from __future__ import annotations

import time
from dataclasses import asdict

import mujoco
import numpy as np

from rubiknetic.cube_logic import HOME_POSITIONS, SOLVED, InconsistentTransition, Move, infer_move
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES, to_string

from . import scored
from .m2_model import WeldParams, build_m2_xml, m2_params
from .readout import CubeReadout
from .rig import EditAuditError, NumericalFailure, TurnRig, TurnTiming
from .switching import SwitchAuditedSim, SwitchManager, SwitchRule

# ---- frozen thresholds (pre-registration section 4) --------------------------------------
THRESHOLDS_M2 = {
    **scored.THRESHOLDS,                 # M1's approved thresholds, unchanged
    "switch_dke_rel": 0.01,              # E1-5: |dKE| <= max(1 % of cube KE, 1 mJ)
    "switch_dke_abs_J": 1e-3,
    "switch_post_pos_err_mm": 0.01,      # E1-5 NEW: post-activation pose error
    "twist_max_deg": 2.0,                # E1-6c NEW: twist <= 2 deg up to 5 N m
    "twist_penetration_mm": 0.5,         # E1-6c NEW: penetration <= 0.5 mm throughout
    "e16e_misalignment_deg": 5.0,        # E1-6e setup misalignment
}
SCORED_SEED_RANGE = (3000, 3999)  # Amendment 4 (D2): new range; 2000-2999 belongs to the invalid run 1
FROZEN_PATHS_M2 = ["src", "pyproject.toml", "uv.lock", "experiments/PHASE_1_M2_PREREGISTRATION.md",
                   "experiments/E2_scored_m2/run.py", "experiments/E2_scored_m2/analyze.py",
                   "experiments/E2_scored_m2/bench.py"]
_NONCENTRE = [i for i, h in enumerate(HOME_POSITIONS) if np.count_nonzero(h) >= 2]
environment = scored.environment
SETUP_MISALIGN_MAX_DEG = 0.25  # Amendment 2 fallback (B1 conditional failed): +/-0.25 deg per face (A1 was 0.5)
AMENDMENTS = ("A1 setup +/-0.5 deg per face", "A2 shear-dominance unlock (dominance 1.5)", "A3 E1-7 kv = 0.04*kp",
              "A4 E1-6e perpendicular-face map _PERPENDICULAR", "A5 E1-5 pose error from translational rows (mm)",
              "B1 FALLBACK in force: setup +/-0.25 deg per face, per-cubie and hinge relock 0.5 deg",
              "B2 E1-6b: M1 categorical criterion + never two layers unlocked",
              "C1 scored turner turn_kp 20, turn_kv 0.8; E1-7 turner factor {5, 20}, kv = 0.04*kp")
SCORED_TURNER = {"turn_kp": 20.0, "turn_kv": 0.8}  # Amendment 3 (C1): frozen turner for every scored M2 trial


def draw_setup(seed: int, misalign_max_deg: float = SETUP_MISALIGN_MAX_DEG) -> scored.TrialSetup:
    """M1's seeded setup draw with the M2 misalignment range (Amendment 1, A1)."""
    return scored.draw_setup(seed, misalign_max_deg)


def require_clean_commit_m2() -> str:
    """Rule 1: refuse to score from uncommitted code (covers the M2 src files and E2 scripts)."""
    dirty = scored._git("status", "--porcelain", "--", *FROZEN_PATHS_M2)
    if dirty:
        raise SystemExit("refusing to run scored M2 trials: uncommitted changes in frozen paths:\n" + dirty)
    return scored._git("rev-parse", "HEAD")


# ---- unwrapped layer angle ---------------------------------------------------------------
class LayerAngleTracker:
    """Read-only hook: integrates the mean signed rotation of a layer's members about the face axis in small
    increments, so half turns are measured without the ±180° wrap artefact."""

    def __init__(self, ro: CubeReadout, every: int = 20):
        self.ro, self.every, self.k = ro, every, 0
        self.face = None
        self.members: list[int] = []
        self.prev = None
        self.total = 0.0

    def begin(self, d, face: str, members: list[int]) -> None:
        self.face, self.members, self.total, self.k = face, list(members), 0.0, 0
        self.prev = self.ro.poses(d)[1]

    def _accumulate(self, d) -> None:
        _, rot = self.ro.poses(d)
        self.total += float(np.mean(CubeReadout.rotation_about_deg(self.prev, rot, self.members, self.face)))
        self.prev = rot

    def end(self, d) -> float:
        if self.face is not None and self.members:
            self._accumulate(d)
        self.face = None
        return self.total

    def __call__(self, d) -> None:
        if self.face is None or not self.members:
            return
        self.k += 1
        if self.k % self.every == 0:
            self._accumulate(d)


# ---- environment for one trial ------------------------------------------------------------
class TrialM2:
    def __init__(self, params, setup: scored.TrialSetup | None, rule: SwitchRule | None = None,
                 weld: WeldParams | None = None, allow_test_wrench: bool = False, settle_s: float = 0.5,
                 misalign_override: dict | None = None):
        self.params, self.rule, self.weld = params, rule or SwitchRule(), weld or WeldParams()
        self.model = mujoco.MjModel.from_xml_string(build_m2_xml(params, self.weld))
        self.sim = SwitchAuditedSim(self.model, allow_test_wrench=allow_test_wrench)
        mujoco.mj_forward(self.model, self.sim.d)
        self.ro = CubeReadout(self.model, params.pitch)
        self.mon = scored.Monitor(self.model, self.ro)
        self.sim.hooks.append(self.mon)
        self.mgr = SwitchManager(self.sim, params.pitch, self.rule)
        self.tracker = LayerAngleTracker(self.ro)
        self.sim.hooks.append(self.tracker)
        self.rig = TurnRig(self.sim, pad_close_target=-(params.pad_open_clearance + params.grip_overshoot))
        self.setup = setup
        mis = misalign_override if misalign_override is not None else (setup.misalign_deg if setup else None)
        self.misalign = mis
        if mis:
            scored.apply_setup_misalignment(self.sim, mis)
        self.mgr.setup_reanchor(self.sim.d)  # logged setup: welds hold the setup pose
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
            "model": "M2",
            "preregistration_amendments": list(AMENDMENTS),
            "scored_turner": dict(SCORED_TURNER),
            "params": {k: v for k, v in asdict(self.params).items() if k != "extra"},
            "switch_rule": asdict(self.rule),
            "weld": asdict(self.weld),
            "setup": asdict(self.setup) if self.setup else None,
            "applied_misalignment_deg": self.misalign,
            "setup_log": self.sim.setup_log,
            "t0_observed_valid": self.t0_obs.valid,
            "t0_solved": bool(self.t0_obs.valid and self.t0_obs.state == SOLVED),
            "radial_offset_mm_t0": self.radial_offset_mm(),
        }

    def finish(self, rec: dict) -> dict:
        rec["switch_log"] = [{k: v for k, v in e.items()} for e in self.sim.switch_log]
        rec["switch_counts"] = {k: sum(e["kind"] == k for e in self.sim.switch_log) for k in ("unlock", "relock", "refuse")}
        rec["refusal_episodes"] = rec["switch_counts"]["refuse"]  # refusals are logged once per episode (A2)
        rec["refusal_episodes_ambiguous"] = sum(bool(e.get("ambiguous_loads")) for e in self.sim.switch_log
                                                if e["kind"] == "refuse")
        rec["e1_5"] = e15_switch_checks(self.sim.switch_log, self.rule)
        rec["edit_audit_violations"] = self.sim.violations
        rec["numerical_failures"] = self.sim.numerical_failures
        rec["wrench_log_entries"] = len(self.sim.wrench_log)
        rec["sim_time_s"] = float(self.sim.d.time)
        rec["integrity_ok"] = not self.sim.violations and not self.sim.numerical_failures
        return rec


def params_for_m2(setup: scored.TrialSetup | None, **overrides):
    """M2 params for a trial: the frozen scored turner (C1) unless explicitly overridden (E1-7 only)."""
    kw = {**SCORED_TURNER, **overrides}
    if setup is not None and "grip_force" not in kw:
        kw["grip_force"] = setup.grip_force
    return m2_params(**kw)


def e15_switch_checks(log: list[dict], rule: SwitchRule) -> dict:
    """E1-5 per-switch criteria on unlock and relock events. Events whose post-switch measurement did not complete
    (the trial ended within one step) are counted as 'incomplete' and fail."""
    t = THRESHOLDS_M2
    checks = []
    for e in log:
        if e["kind"] not in ("unlock", "relock"):
            continue
        if "dke" not in e:
            checks.append({"t": e["t"], "kind": e["kind"], "complete": False, "ok": False})
            continue
        dke_lim = max(t["switch_dke_rel"] * max(e["ke_before"], 0.0), t["switch_dke_abs_J"])
        within = (e.get("max_misalignment_deg", 0.0) <= rule.tol_unlock_deg if e["kind"] == "unlock"
                  else (e.get("hinge_off_square_deg", 0.0) <= rule.tol_lock_deg
                        and e.get("max_misalignment_deg", 0.0) <= rule.tol_lock_cubie_deg))
        c = {"t": e["t"], "kind": e["kind"], "complete": True, "abs_dke_J": abs(e["dke"]), "dke_limit_J": dke_lim,
             "pos_err_post_mm": e.get("pos_err_post_mm", 0.0),
             "ok_dke": abs(e["dke"]) <= dke_lim, "ok_within_tolerance": bool(within),
             "ok_pos_err": e.get("pos_err_post_mm", 0.0) <= t["switch_post_pos_err_mm"]}
        c["ok"] = c["ok_dke"] and c["ok_within_tolerance"] and c["ok_pos_err"]
        checks.append(c)
    return {"n": len(checks), "n_fail": sum(not c["ok"] for c in checks), "checks": checks}


def _rot_deg(ro, r0, r1, members, face):
    return ro.rotation_about_deg(r0, r1, members, face)


# ---- E1-2 / E1-3 / E1-4 / E1-7 ------------------------------------------------------------
def run_sequence_trial_m2(moves: list[Move], seed: int, misalign_max_deg: float = SETUP_MISALIGN_MAX_DEG,
                          rule: SwitchRule | None = None,
                          weld: WeldParams | None = None, **overrides) -> dict:
    setup = draw_setup(seed, misalign_max_deg)
    tr = TrialM2(params_for_m2(setup, **overrides), setup, rule, weld)
    ro, d, mon = tr.ro, tr.sim.d, tr.mon
    th = THRESHOLDS_M2
    rec = tr.base_record()
    rec.update({"sequence": to_string(moves), "seed": seed, "per_move": []})
    expect, prev = SOLVED, tr.t0_obs
    wall = time.perf_counter()
    try:
        for mv in moves:
            _, r0 = ro.poses(d)
            members = {f: ro.layer_members(d, f) for f in FACES}
            mon.new_window()
            mon.begin_turn(mv.face, members[mv.face])
            tr.tracker.begin(d, mv.face, members[mv.face])
            n_sw = len(tr.sim.switch_log)
            log = tr.rig.turn(mv, tr.timing)
            causal = mon.end_turn()
            cum = tr.tracker.end(d)
            _, r1 = ro.poses(d)
            obs = ro.observe(d)
            nominal = -90.0 * {1: 1, 2: 2, 3: -1}[mv.quarter_turns]
            err = cum - nominal  # UNWRAPPED cumulative layer angle (pre-registration E1-2)
            nontarget = [i for i in _NONCENTRE if i not in members[mv.face]]
            drift = np.abs(_rot_deg(ro, r0, r1, nontarget, mv.face))
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
                "move": str(mv), "observed_move": str(observed) if observed else None,
                "inference_error": inference_error, "observed_valid": obs.valid,
                "layer_angle_unwrapped_deg": float(cum), "turn_error_deg": float(err),
                "nontarget_drift_deg": float(drift.max()) if len(drift) else 0.0, "penetration_mm": pen,
                "radial_change_mm_so_far": mon.max_radial_change * 1000,
                "radial_above_nominal_mm_so_far": mon.max_above_nominal * 1000,
                "max_turner_torque_Nm": float(np.max(np.abs(log.turner_torque))),
                "switch_events": [e["kind"] + ":" + str(e.get("face", e.get("faces"))) for e in tr.sim.switch_log[n_sw:]],
                **causal,
                "ok_oracle": oracle_ok,
                "ok_turn_error": bool(abs(err) <= th["turn_error_deg"]),
                "ok_drift": bool((drift.max() if len(drift) else 0.0) <= th["nontarget_drift_deg"]),
                "ok_penetration": bool(pen <= th["penetration_mm"]),
                "ok_radial_pop": bool(mon.max_above_nominal * 1000 <= th["radial_above_nominal_mm"]),
                "ok_causal": causal["causal"],
            }
            r["ok_all"] = all(v for k, v in r.items() if k.startswith("ok_") and k != "ok_all")
            rec["per_move"].append(r)
            prev = obs
            if not oracle_ok:
                break
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    rec["wall_time_s"] = time.perf_counter() - wall
    final = ro.observe(d) if "aborted" not in rec else None
    rec["final_matches_oracle"] = bool(final is not None and final.valid and final.state == expect)
    rec["moves_completed_ok"] = sum(1 for r in rec["per_move"] if r["ok_all"])
    tr.finish(rec)
    rec["pass"] = bool(rec["integrity_ok"] and "aborted" not in rec and rec["t0_solved"]
                       and len(rec["per_move"]) == len(moves) and all(r["ok_all"] for r in rec["per_move"])
                       and rec["final_matches_oracle"])
    return rec


# ---- E1-1 rest ------------------------------------------------------------------------------
def run_rest_trial_m2(seed: int, duration_s: float = 10.0) -> dict:
    setup = draw_setup(seed)
    tr = TrialM2(params_for_m2(setup), setup)
    ro, d, mon = tr.ro, tr.sim.d, tr.mon
    th = THRESHOLDS_M2
    rec = tr.base_record()
    rec["seed"] = seed
    _, r0 = ro.poses(d)
    members = {f: ro.layer_members(d, f) for f in FACES}
    worst, topo_ok, topo_problems = 0.0, True, []
    steps = int(round(duration_s / tr.model.opt.timestep))
    try:
        for k in range(0, steps, 50):
            tr.sim.step(min(50, steps - k))
            _, r = ro.poses(d)
            for f in FACES:
                worst = max(worst, float(np.abs(ro.rotation_about_deg(r0, r, members[f], f)).max()))
            ok, probs = tr.mgr.weld_topology_consistent(d)
            if not ok and topo_ok:
                topo_ok, topo_problems = False, probs
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    obs = ro.observe(d)
    pen = max(0.0, -mon.window_min_dist) * 1000
    rec.update({
        "rest_rotation_deg": worst, "radial_change_mm": mon.max_radial_change * 1000,
        "radial_above_nominal_mm": mon.max_above_nominal * 1000, "penetration_mm": pen,
        "weld_topology_problems": topo_problems,
        "final_solved": bool(obs.valid and obs.state == SOLVED),
        "ok_solved": bool(obs.valid and obs.state == SOLVED and rec["t0_solved"]),
        "ok_rest_rotation": worst <= th["rest_rotation_deg"],
        "ok_radial_offset": rec["radial_offset_mm_t0"] <= th["radial_offset_mm"],
        "ok_radial_pop": mon.max_above_nominal * 1000 <= th["radial_above_nominal_mm"],
        "ok_penetration": pen <= th["penetration_mm"],
        "ok_weld_topology": topo_ok,  # NEW (E1-1, M2 row)
    })
    tr.finish(rec)
    rec["pass"] = bool(rec["integrity_ok"] and "aborted" not in rec and all(v for k, v in rec.items() if k.startswith("ok_")))
    return rec


# ---- E1-5b misaligned perpendicular turn ------------------------------------------------------
def run_misaligned_turn_trial_m2(misalign_deg: float, seed: int) -> dict:
    """U is turned by ``misalign_deg`` with the rig (signed, right-hand about +z), then R is attempted.
    Categorical: R is refused (logged, no motion) or completes legally after U realigns. Never an illegal or
    oracle-mismatched valid state; never a snap (an activation outside tolerance)."""
    setup = draw_setup(seed)
    tr = TrialM2(params_for_m2(setup), setup)
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
        rec["U_left_unlocked"] = tr.mgr.unlocked
        mem1 = {f: ro.layer_members(d, f) for f in FACES}
        n_sw = len(tr.sim.switch_log)
        tr.rig.turn(Move("R", 1), tr.timing)
        _, r2 = ro.poses(d)
        rec["R_rotation_deg"] = float(np.mean(ro.rotation_about_deg(r1, r2, mem1["R"], "R")))
        rec["R_phase_switch_events"] = [{k: v for k, v in e.items() if k != "activated_ids"} for e in tr.sim.switch_log[n_sw:]]
        refused = any(e["kind"] == "refuse" for e in tr.sim.switch_log[n_sw:])
        obs = ro.observe(d)
        rec["observed_valid"] = obs.valid
        ok = True
        if obs.valid:
            try:
                mv = infer_move(tr.t0_obs.cube, obs.cube)
                rec["observed_move"] = str(mv) if mv else None
                ok = obs.state == SOLVED.apply_all([mv] if mv else [])
                rec["outcome"] = ("completed" if mv else ("refused" if refused else "no_net_move"))
            except InconsistentTransition as e:
                rec["inference_error"] = str(e)
                ok, rec["outcome"] = False, "illegal_transition"
        else:
            rec["outcome"] = "refused_unknown" if refused else "blocked_unknown"
        rec["ok_categorical"] = bool(ok)
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
        rec["ok_categorical"] = False
    tr.finish(rec)
    rec["ok_no_snap"] = all(c.get("ok_within_tolerance", False) for c in rec["e1_5"]["checks"] if c["complete"])
    rec["pass"] = bool(rec["integrity_ok"] and "aborted" not in rec and rec["ok_categorical"] and rec["ok_no_snap"]
                       and rec["t0_solved"])
    return rec


# ---- E1-6a / E1-6b / E1-6c / E1-6e ----------------------------------------------------------
def run_open_pad_trial_m2(face: str, seed: int) -> dict:
    setup = draw_setup(seed)
    tr = TrialM2(params_for_m2(setup), setup)
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
        rec.update({"layer_rotation_deg": rot, "ok_no_motion": rot <= THRESHOLDS_M2["open_pad_rotation_deg"],
                    "ok_solved": bool(obs.valid and obs.state == SOLVED)})
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    tr.finish(rec)
    rec["pass"] = bool(rec["integrity_ok"] and "aborted" not in rec and rec.get("ok_no_motion")
                       and rec.get("ok_solved") and rec["t0_solved"])
    return rec


def _max_concurrent_unlocked(events: list[dict]) -> int:
    """Largest number of layers unlocked at the same time, reconstructed from unlock/relock events."""
    open_faces, peak = set(), 0
    for e in events:
        if e["kind"] == "unlock":
            open_faces.add(e["face"])
            peak = max(peak, len(open_faces))
        elif e["kind"] == "relock":
            open_faces.discard(e["face"])
    return peak


def run_opposed_trial_m2(faces: tuple[str, str], torque_limit: float, seed: int) -> dict:
    setup = draw_setup(seed)
    tr = TrialM2(params_for_m2(setup, turn_torque_limit=torque_limit), setup)
    ro, d, mon = tr.ro, tr.sim.d, tr.mon
    rec = tr.base_record()
    rec.update({"seed": seed, "faces": list(faces), "torque_limit_Nm": torque_limit})
    try:
        _, r0 = ro.poses(d)
        mem = {f: ro.layer_members(d, f) for f in faces}
        mon.new_window()
        n_sw = len(tr.sim.switch_log)
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
        ev = tr.sim.switch_log[n_sw:]
        both = all(abs(v) >= 45.0 for v in rots.values())
        rec.update({"layer_rotations_deg": rots, "observed_valid": obs.valid,
                    "penetration_mm_reported_only": max(0.0, -mon.window_min_dist) * 1000,
                    "radial_change_mm": mon.max_radial_change * 1000,
                    "ok_not_both_rotated": not both, "ok_state_consistent": bool(consistent),
                    "ok_no_separation": mon.max_radial_change * 1000 <= THRESHOLDS_M2["opposed_radial_change_mm"],
                    # Amendment 2 (B2): M1's categorical criterion plus "never two layers unlocked at the same time"
                    # (checked from the switch log); "opposed requests must be refused" is withdrawn.
                    "max_concurrently_unlocked": _max_concurrent_unlocked(ev),
                    "ok_never_two_unlocked": _max_concurrent_unlocked(ev) <= 1})
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    tr.finish(rec)
    rec["pass"] = bool(rec["integrity_ok"] and "aborted" not in rec and rec["t0_solved"]
                       and all(v for k, v in rec.items() if k.startswith("ok_")))
    return rec


def run_corner_twist_trial_m2(corner: tuple[int, int, int], seed: int, peak_Nm: float = 5.0,
                              ramp_s: float = 2.0, hold_s: float = 0.5, settle_s: float = 0.5) -> dict:
    """E1-6c with the logged test wrench (P-12), plus the NEW credibility criteria."""
    setup = draw_setup(seed)
    tr = TrialM2(params_for_m2(setup), setup, allow_test_wrench=True)
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
        return float(np.degrees(np.arccos(np.clip((np.trace(rel) - 1) / 2, -1, 1))))

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
        twist_max = max(twist_max, twist_deg())
        pen = max(0.0, -mon.window_min_dist) * 1000
        sim.set_test_wrench(body, np.zeros(6))
        sim.step(int(settle_s / dt))
        obs = ro.observe(d)
        rec.update({
            "max_twist_deg": twist_max, "torque_at_twist_15deg_Nm": load_at_15, "penetration_mm": pen,
            "radial_change_mm": mon.max_radial_change * 1000, "final_observed_valid": obs.valid,
            "final_solved": bool(obs.valid and obs.state == SOLVED),
            "ok_no_false_valid_state": bool((not obs.valid) or obs.state == SOLVED),
            "ok_twist_credible": twist_max <= THRESHOLDS_M2["twist_max_deg"],               # NEW
            "ok_penetration_credible": pen <= THRESHOLDS_M2["twist_penetration_mm"],         # NEW
        })
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    tr.finish(rec)
    rec["pass"] = bool(rec["integrity_ok"] and "aborted" not in rec and rec["t0_solved"]
                       and rec.get("ok_no_false_valid_state") and rec.get("ok_twist_credible")
                       and rec.get("ok_penetration_credible"))
    return rec


_PERPENDICULAR = {"U": "R", "D": "R", "R": "U", "L": "U", "F": "U", "B": "U"}


def run_forced_misaligned_switch_trial_m2(face: str, seed: int) -> dict:
    """E1-6e: a face perpendicular to ``face`` is misaligned by 5° at setup (logged); the welds hold that pose.
    A gripped turn of ``face`` is requested and must be REFUSED (logged), with no layer motion and no snap."""
    setup = draw_setup(seed, misalign_max_deg=0.0)
    mis = {f: 0.0 for f in FACES}
    mis[_PERPENDICULAR[face]] = THRESHOLDS_M2["e16e_misalignment_deg"]
    tr = TrialM2(params_for_m2(setup), setup, misalign_override=mis)
    ro, d = tr.ro, tr.sim.d
    rec = tr.base_record()
    rec.update({"seed": seed, "face": face, "misaligned_face": _PERPENDICULAR[face],
                "perpendicular_map_A4": dict(_PERPENDICULAR)})
    try:
        _, r0 = ro.poses(d)
        mem = ro.layer_members(d, face)
        n_sw = len(tr.sim.switch_log)
        tr.rig.turn(Move(face, 1), tr.timing)
        _, r1 = ro.poses(d)
        ev = tr.sim.switch_log[n_sw:]
        rot = float(np.abs(ro.rotation_about_deg(r0, r1, mem, face)).max())
        obs = ro.observe(d)
        rec.update({"layer_rotation_deg": rot, "events": [{k: v for k, v in e.items() if k != "activated_ids"} for e in ev],
                    "ok_refused": any(e["kind"] == "refuse" for e in ev) and not any(e["kind"] == "unlock" for e in ev),
                    "ok_no_motion": rot <= THRESHOLDS_M2["open_pad_rotation_deg"],
                    "ok_state_unchanged": bool(obs.valid and obs.state == SOLVED)})
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    tr.finish(rec)
    rec["pass"] = bool(rec["integrity_ok"] and "aborted" not in rec and rec["t0_solved"]
                       and all(v for k, v in rec.items() if k.startswith("ok_")))
    return rec
