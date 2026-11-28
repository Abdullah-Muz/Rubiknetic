"""G2 trial kinds (experiments/PHASE_2_G2_PREREGISTRATION.md revision 5 §3-§4; DRAFT, not in force).

Every trial builds the D18 two-arm scene (`experiments/D18_two_arm_m7/two_arm.py`) in its own spawned process, configured
from the job's overrides and the fixed defaults below, and returns a record with `pass` and `fail_reasons`. The limits
were fixed from the P-5 pilot (P-118, P-119), review 1 (P-122, revision 2), pilot 2 (P-125: F/T stop 1.0 N.m,
absolute end misalignment 4 deg), review 2 (P-126, revision 3) and review 3 (P-128, revision 4) and review 4 (P-130, magnets restored: revision 5).

Kinds:
  seq   G2-2/G2-3/G2-4: a U-family move sequence from a seeded start (cube offset, layer misalignment).
  hold  G2-1: arm A holds the cube for hold_s seconds after the start sequence; arm B open at its pre-grasp pose.
  neg   G2-7 negative cases: two_layer, offcentre (reported only), collision, open_midturn, jam.
  sens  G2-6 sensitivity screen (reported only): a seq trial with one setting changed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "experiments" / "D18_two_arm_m7"))
import two_arm as TA  # noqa: E402

from rubiknetic.cube_logic import SOLVED, parse  # noqa: E402
from rubiknetic.cube_physics.magnets import MagnetSystem  # noqa: E402
from rubiknetic.cube_physics.rig import EditAuditError, NumericalFailure  # noqa: E402

L, HC = 1.0, 0.30                       # D18 layout (P-108)
DEFAULTS = {"grip": 20.0, "kp": 4000.0, "dp": 60.0, "ki": 8000.0, "pad_mu": 0.8, "tip_solref": 0.01,
            "insertion_u": 0.014, "j7_err": 0.0}         # fixed (review 1 item 6): never the current module value
CUBE_TOL = 0.001                        # start offset, uniform +-1 mm per axis (P-119)
MISALIGN_DEG = 1.0                      # setup misalignment per face, uniform +-1 deg (as G1; P-119)
HOLD_SLIP_MM, HOLD_ROT_DEG = 1.0, 1.0   # G2-1 limits (P-119)
MOVE_SLIP_MM = 1.0                      # per-move core slip relative to arm A (P-119)
TOTAL_SLIP_MM, TOTAL_ROT_DEG = 2.0, 2.0 # from t0 to the end of a trial (revision 2)
RESIDUAL_END_MAX_DEG = 4.0              # every cubie's end misalignment (absolute) <= 4 deg (P-125; replaces growth)
PEN_MM = 0.5                            # cubie-cubie penetration (G1)
JAM_SLIP_MM = 0.5                       # G2-7 jam: cube shift allowed before the guard stops (P-119)
JAM_ROLL_DEG = (20.0, 50.0)             # G2-7 jam: the stop must happen in this roll window (pilot 26-44 deg; rev. 2)
FT_STOP = 1.0                           # F/T stop on |tau_z| (P-125; was 0.8, P-119; U' first turns reach 0.67)
DROP_SHIFT_MM = 1.0                     # cube shift while the stand drops, in arm A's grip (review 2 S6)
T0_OFFSET_MM = 3.0                      # cube centre vs nominal at t0 (review 2 S6; start draw <= 1.7 mm)
NEG_CASES = ("two_layer", "offcentre", "collision", "open_midturn", "jam")
NEG_REPORTED_ONLY = ("offcentre",)      # review 1 item 3: it cannot fail, so it is reported, not scored
CONTACT_ZERO = ("robot_cube_nonpad", "arm_arm", "robot_table", "robot_stand", "robot_block")
Refused = TA.H.M4.Refused               # magnet-availability refusal: an interruption, never a trial result


def start_draw(seed: int) -> dict:
    """The seeded start of a trial: cube offset (m) and per-face misalignment (deg)."""
    rng = np.random.default_rng(seed)
    off = rng.uniform(-CUBE_TOL, CUBE_TOL, 3)
    mis = {f: float(rng.uniform(-MISALIGN_DEG, MISALIGN_DEG)) for f in ("U", "D", "F", "B", "L", "R")}
    return {"cube_offset_m": off.tolist(), "misalign_deg": mis}


def random_u_sequence(seed: int, n: int = 10) -> str:
    rng = np.random.default_rng(seed + 500_000)
    return " ".join(rng.choice(["U", "U'", "U2"], size=n).tolist())


def reset_phase() -> None:
    """Review 3 item 1: marks the trial as not yet simulating. The runner calls this before every attempt; the first
    control step (`TwoArm.ctrl_step`) sets the flag."""
    TA.SIM_STARTED = False


def simulation_started() -> bool:
    """True once the trial has taken its first control step: an exception before it is a model-load error."""
    return bool(TA.SIM_STARTED)


def configure(ov: dict, start: dict) -> None:
    """Sets the two_arm module for this trial (one trial per process). Physics-neutral visuals are off."""
    v = {**DEFAULTS, **ov}
    TA.STICKERS, TA.ENV, TA.STAND, TA.FT, TA.ROLL_MODE = False, False, True, True, "ffb"
    TA.H.TIP_SOLREF = (v["tip_solref"], 1.0)
    TA.K_P, TA.D_P, TA.KI_P = v["kp"], v["dp"], v["ki"]
    TA.FT_STOP = v.get("ft_stop", FT_STOP)
    TA.CUBE_OFF = np.array(start["cube_offset_m"]) + np.array(v.get("extra_offset_m", [0.0, 0.0, 0.0]))
    TA.SETUP_MISALIGN = start["misalign_deg"]
    TA.JAM_BLOCK = bool(v.get("jam_block", False))
    TA.OPEN_MIDTURN = bool(v.get("open_midturn", False))
    TA.TU.INSERTION_U = v["insertion_u"]
    TA.J7_ERR = v["j7_err"]
    TA.PAD_MU = v["pad_mu"]


def _contact_reasons(where: str, c: dict, cube_stand: bool) -> list[str]:
    out = [f"{where}: {k} = {c[k]}" for k in CONTACT_ZERO if c.get(k)]
    if cube_stand and c.get("cube_stand"):
        out.append(f"{where}: cube_stand = {c['cube_stand']}")
    if c.get("pen_cubie", 0.0) > PEN_MM:
        out.append(f"{where}: cubie penetration {c['pen_cubie']:.3f} mm")
    return out


def _integrity_reasons(rec: dict) -> list[str]:
    out = []
    if "aborted" in rec:
        out.append(f"aborted: {rec['aborted']}")
    if rec.get("audit_violations"):
        out.append("edit-audit violation")
    if rec.get("numerical_failures"):
        out.append("numerical failure")
    if rec.get("harness_exception"):
        out.append("harness exception")
    audit = rec.get("trial", {}).get("model_audit") or rec.get("model_audit")
    if audit is None or any(audit.get(k) for k in ("actuators_on_cube", "equalities_on_cube", "tendons_on_cube",
                                                   "gravcomp_on_cube")):
        out.append(f"model audit: {audit}")
    mag = rec.get("trial", {}).get("magnets") or rec.get("magnets")      # P-130: the L0 magnets act at every step
    if not mag or mag.get("steps", 0) <= 0 or mag.get("steps_without_magnet_force", 1) != 0:
        out.append(f"magnets not active at every step: {mag}")
    return out


def _pre_t0_reasons(start: dict) -> list[str]:
    """Review 2 S6: arm A's stabilisation before t0 (the stand drop) and the cube's position at t0."""
    out = []
    if start.get("stand_drop_shift_mm", 0.0) > DROP_SHIFT_MM:
        out.append(f"stand drop shift {start['stand_drop_shift_mm']:.2f} mm")
    if start.get("core_offset_from_nominal_mm", 0.0) > T0_OFFSET_MM:
        out.append(f"cube {start['core_offset_from_nominal_mm']:.2f} mm from nominal at t0")
    if "stand_drop_shift_mm" not in start:
        out.append("no stand-drop measurement")
    return out


def _trial_reasons(rec: dict) -> list[str]:
    t = rec.get("trial")
    if t is None:
        return ["no trial-level measurements"]
    out = []
    if t["core_slip_total_mm"] > TOTAL_SLIP_MM:
        out.append(f"total core slip {t['core_slip_total_mm']:.2f} mm")
    if t["core_rot_total_deg"] > TOTAL_ROT_DEG:
        out.append(f"total core rotation {t['core_rot_total_deg']:.2f} deg")
    if max(t["residual_end_deg"]) > RESIDUAL_END_MAX_DEG:
        out.append(f"a cubie is misaligned by {max(t['residual_end_deg']):.2f} deg at the end")
    return out


def _seq_reasons(rec: dict, n_moves: int) -> list[str]:
    out = _integrity_reasons(rec)
    if not rec.get("t0_solved"):
        out.append("cube not solved at t0")
    out += _contact_reasons("start", rec.get("start", {}).get("contacts", {}), cube_stand=False)
    out += _pre_t0_reasons(rec.get("start", {}))
    out += _contact_reasons("approach", rec.get("approach", {}), cube_stand=True)
    if len(rec.get("per_move", [])) != n_moves:
        out.append(f"{len(rec.get('per_move', []))}/{n_moves} moves recorded")
    for i, pm in enumerate(rec.get("per_move", [])):
        bad = [k for k, v in pm.items() if k.startswith("ok_") and k != "ok_all" and not v]
        if pm.get("jam_stop") is not None:
            bad.append("guard stop")
        if pm.get("core_slip_mm", 0.0) > MOVE_SLIP_MM:
            bad.append(f"core slip {pm['core_slip_mm']:.2f} mm")
        if bad:
            out.append(f"move {i + 1} {pm['move']}: {', '.join(bad)}")
    if not rec.get("final_matches_oracle"):
        out.append("final state does not match the oracle")
    out += _trial_reasons(rec)
    return out


def run_seq(moves: str, ov: dict, start: dict) -> dict:
    configure(ov, start)
    rec = TA.run(moves, {**DEFAULTS, **ov}["grip"], L, HC)
    rec["start_draw"] = start
    reasons = _seq_reasons(rec, len(parse(moves)))
    rec["fail_reasons"] = reasons
    rec["pass"] = not reasons
    return rec


def run_hold(hold_s: float, ov: dict, start: dict) -> dict:
    """G2-1: arm A alone holds the cube after the start sequence; arm B stays open at its pre-grasp pose."""
    configure(ov, start)
    rec = {"kind": "hold", "hold_s": hold_s, "start_draw": start}
    try:
        r = TA.TwoArm(L, HC, {**DEFAULTS, **ov}["grip"])
        rec["start"] = r.start
        rec["model_audit"] = r.model_audit
        obs0 = r.ro.observe(r.d)
        rec["t0_solved"] = bool(obs0.valid and obs0.state == SOLVED)
        p0, R0 = r.rel()
        r.new_acc()
        slip = rot = 0.0
        n = r.secs(hold_s)
        every = r.secs(0.1)
        for k in range(0, n, every):
            r.step(min(every, n - k))
            p, R = r.rel()
            slip = max(slip, float(np.linalg.norm(p - p0) * 1e3))
            ang = np.degrees(np.arccos(np.clip((np.trace(R @ R0.T) - 1) / 2, -1, 1)))
            rot = max(rot, float(ang))
        obs = r.ro.observe(r.d)
        rec["magnets"] = r.magnet_stats()
        rec.update({"core_slip_mm": slip, "core_rot_deg": rot, "final_solved": bool(obs.valid and obs.state == SOLVED),
                    "contacts": {k: v for k, v in r.acc.items() if k in TA.CONTACT_KEYS},
                    "residual_t0_deg": r.residual_t0, "residual_end_deg": TA.lattice_residual_deg(r.ro.poses(r.d)[1]),
                    "audit_violations": r.sim.violations, "numerical_failures": r.sim.numerical_failures,
                    "sim_time_s": float(r.d.time)})
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    finally:
        MagnetSystem.uninstall()
    reasons = _integrity_reasons(rec)
    if "aborted" not in rec:
        if not rec["t0_solved"] or not rec["final_solved"]:
            reasons.append("cube not solved at t0 or at the end")
        if rec["core_slip_mm"] > HOLD_SLIP_MM:
            reasons.append(f"core slip {rec['core_slip_mm']:.2f} mm > {HOLD_SLIP_MM}")
        if rec["core_rot_deg"] > HOLD_ROT_DEG:
            reasons.append(f"core rotation {rec['core_rot_deg']:.2f} deg > {HOLD_ROT_DEG}")
        reasons += _contact_reasons("start", rec["start"].get("contacts", {}), cube_stand=False)
        reasons += _pre_t0_reasons(rec["start"])
        reasons += _contact_reasons("hold", rec["contacts"], cube_stand=True)
        if max(rec["residual_end_deg"]) > RESIDUAL_END_MAX_DEG:
            reasons.append(f"a cubie is misaligned by {max(rec['residual_end_deg']):.2f} deg at the end")
    rec["fail_reasons"], rec["pass"] = reasons, not reasons
    return rec


NEG_SETUP = {                       # case -> (overrides, sequence); acceptance in neg_outcome
    "two_layer": ({"insertion_u": 0.025}, "U"),          # turner pads cross the U/E boundary by 6 mm
    "offcentre": ({"extra_offset_m": [0.0, 0.005, 0.0]}, "U"),   # cube 5 mm sideways (pad normal)
    "collision": ({"insertion_u": 0.034}, "U"),          # turner driven into arm A's fingertips
    "open_midturn": ({"open_midturn": True}, "U"),
    "jam": ({"jam_block": True}, "U"),
}


def neg_outcome(case: str, rec: dict) -> tuple[bool, str]:
    """Revision 2 (review 1 item 3): an abort, edit-audit violation, numerical failure, harness exception or
    model-audit finding fails a negative trial. Each case names the detection it accepts:
      two_layer     a guard stop, or a failure of ok_oracle, ok_turn_error or ok_drift;
      open_midturn  a failure of ok_oracle or ok_turn_error;
      collision     arm-arm or non-fingertip robot-cube contact recorded (approach or move);
      jam           a guard stop within JAM_ROLL_DEG of roll, core slip <= JAM_SLIP_MM, cubie penetration <= PEN_MM;
      offcentre     reported only: 'clean' (all turn checks pass) or 'detected' (a guard stop or a failed check)."""
    if _integrity_reasons(rec):
        return False, "integrity failure: " + "; ".join(_integrity_reasons(rec))
    pms = rec.get("per_move", [])
    if not pms:
        return False, "no move recorded"
    pm = pms[0]
    stop = pm.get("jam_stop")
    failed = {k for k, v in pm.items() if k.startswith("ok_") and k != "ok_all" and not v}
    if case == "two_layer":
        ok = stop is not None or bool(failed & {"ok_oracle", "ok_turn_error", "ok_drift"})
        return ok, "detected" if ok else "NOT detected"
    if case == "open_midturn":
        ok = bool(failed & {"ok_oracle", "ok_turn_error"})
        return ok, "detected" if ok else "NOT detected"
    if case == "collision":
        app = rec.get("approach", {})
        ok = bool(pm.get("arm_arm_max") or pm.get("robot_cube_nonpad_max") or app.get("arm_arm")
                  or app.get("robot_cube_nonpad"))
        return ok, "robot contact detected" if ok else "no robot contact detected"
    if case == "jam":
        if stop is None:
            return False, "no guard stop"
        rd = abs(stop.get("roll_done_deg", 0.0))
        ok = (JAM_ROLL_DEG[0] <= rd <= JAM_ROLL_DEG[1] and pm.get("core_slip_mm", 9.9) <= JAM_SLIP_MM
              and pm.get("pen_cubie_mm", 9.9) <= PEN_MM)
        return ok, f"guard stop at {rd:.1f} deg" + ("" if ok else " outside the window or cube shift/penetration")
    if case == "offcentre":
        return True, "clean" if (stop is None and not failed) else "detected"
    raise ValueError(case)


def run_neg(case: str, start: dict, extra: dict | None = None) -> dict:
    ov, moves = NEG_SETUP[case]
    rec = run_seq(moves, {**ov, **(extra or {})}, start)
    ok, why = neg_outcome(case, rec)
    rec.update({"negative_case": case, "trial_pass_as_turn": rec["pass"], "turn_fail_reasons": rec["fail_reasons"],
                "detected_ok": ok, "negative_outcome": why})
    rec["pass"] = ok
    rec["fail_reasons"] = [] if ok else [f"negative case {case}: {why}"]
    return rec


def run_trial(kind: str, kw: dict) -> dict:
    start = start_draw(kw["seed"])
    ov = kw.get("overrides", {})
    if "misalign_override" in ov:                     # pilots only (review 2 item 1): force a face's start misalignment
        start["misalign_deg"] = {**start["misalign_deg"], **ov["misalign_override"]}
    if kind in ("seq", "sens"):
        return run_seq(kw["moves"], ov, start)
    if kind == "hold":
        return run_hold(kw["hold_s"], ov, start)
    if kind == "neg":
        return run_neg(kw["case"], start, ov)
    raise ValueError(kind)
