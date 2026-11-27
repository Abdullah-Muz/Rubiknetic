"""G2 trial kinds (experiments/PHASE_2_G2_PREREGISTRATION.md §3; DRAFT, not in force).

Every trial builds the D18 two-arm scene (`experiments/D18_two_arm_m7/two_arm.py`) in its own process, configured from
the job's overrides, and returns a record with `pass` and `fail_reasons`. Limits marked [pilot] are provisional and
are fixed by the pilots before the pre-registration is frozen (VALIDATION_PLAN threshold policy).

Kinds:
  seq   G2-2/G2-3/G2-4: a U-family move sequence from a seeded start (cube start offset, layer misalignment).
  hold  G2-1: arm A holds the cube for hold_s seconds after the stand drops, arm B open at its pre-grasp pose.
  neg   G2-7 negative tests: two_layer, offcentre, collision, open_midturn, jam.
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
GRIP = 20.0                             # P-97
CUBE_TOL = 0.001                        # start offset, uniform +-1 mm per axis [pilot]
MISALIGN_DEG = 1.0                      # setup misalignment per face, uniform +-1 deg (as G1) [pilot]
HOLD_SLIP_MM, HOLD_ROT_DEG = 1.0, 1.0   # G2-1 limits [pilot]
MOVE_SLIP_MM = 1.0                      # per-move core slip limit relative to arm A [pilot]
JAM_SLIP_MM = 0.5                       # G2-7e: cube shift allowed before the guard stops [pilot]
NEG_CASES = ("two_layer", "offcentre", "collision", "open_midturn", "jam")
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


def configure(ov: dict, start: dict) -> None:
    """Sets the two_arm module for this trial (one trial per process). Physics-neutral visuals are off."""
    TA.STICKERS, TA.ENV, TA.STAND, TA.FT, TA.ROLL_MODE = False, False, True, True, "ffb"
    TA.H.TIP_SOLREF = (ov.get("tip_solref", 0.01), 1.0)
    TA.K_P = ov.get("kp", TA.K_P)
    TA.D_P = ov.get("dp", TA.D_P)
    TA.KI_P = ov.get("ki", TA.KI_P)
    TA.FT_STOP = ov.get("ft_stop", TA.FT_STOP)
    TA.CUBE_OFF = np.array(start["cube_offset_m"]) + np.array(ov.get("extra_offset_m", [0.0, 0.0, 0.0]))
    TA.SETUP_MISALIGN = start["misalign_deg"]
    TA.JAM_BLOCK = bool(ov.get("jam_block", False))
    TA.OPEN_MIDTURN = bool(ov.get("open_midturn", False))
    TA.TU.INSERTION_U = ov.get("insertion_u", 0.014)
    TA.J7_ERR = ov.get("j7_err", 0.0)
    TA.PAD_MU = ov.get("pad_mu", 0.8)


def _seq_reasons(rec: dict, n_moves: int) -> list[str]:
    out = []
    if not rec.get("t0_solved"):
        out.append("cube not solved at t0")
    if "aborted" in rec:
        out.append(f"aborted: {rec['aborted']}")
    if rec.get("audit_violations"):
        out.append("edit-audit violation")
    if rec.get("numerical_failures"):
        out.append("numerical failure")
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
    return out


def run_seq(moves: str, ov: dict, start: dict) -> dict:
    configure(ov, start)
    rec = TA.run(moves, ov.get("grip", GRIP), L, HC)
    rec["start_draw"] = start
    reasons = _seq_reasons(rec, len(parse(moves)))
    rec["fail_reasons"] = reasons
    rec["pass"] = not reasons
    return rec


def run_hold(hold_s: float, ov: dict, start: dict) -> dict:
    """G2-1: arm A alone holds the cube after the stand drops; arm B stays open at its pre-grasp pose."""
    configure(ov, start)
    rec = {"kind": "hold", "hold_s": hold_s, "start_draw": start}
    try:
        r = TA.TwoArm(L, HC, ov.get("grip", GRIP))
        rec["start"] = r.start
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
        rec.update({"core_slip_mm": slip, "core_rot_deg": rot, "final_solved": bool(obs.valid and obs.state == SOLVED),
                    "robot_cube_nonpad_max": r.acc["robot_cube_nonpad"], "arm_arm_max": r.acc["arm_arm"],
                    "robot_table_max": r.acc["robot_table"], "pen_cubie_mm": r.acc["pen_cubie"],
                    "audit_violations": r.sim.violations, "numerical_failures": r.sim.numerical_failures})
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    finally:
        MagnetSystem.uninstall()
    reasons = []
    if "aborted" in rec:
        reasons.append(f"aborted: {rec['aborted']}")
    else:
        if not rec["t0_solved"] or not rec["final_solved"]:
            reasons.append("cube not solved at t0 or at the end")
        if rec["core_slip_mm"] > HOLD_SLIP_MM:
            reasons.append(f"core slip {rec['core_slip_mm']:.2f} mm > {HOLD_SLIP_MM}")
        if rec["core_rot_deg"] > HOLD_ROT_DEG:
            reasons.append(f"core rotation {rec['core_rot_deg']:.2f} deg > {HOLD_ROT_DEG}")
        for k in ("robot_cube_nonpad_max", "arm_arm_max", "robot_table_max"):
            if rec[k]:
                reasons.append(f"{k} = {rec[k]}")
        if rec["audit_violations"] or rec["numerical_failures"]:
            reasons.append("audit violation or numerical failure")
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
    """Provisional acceptance [pilot]: the negative case must be detected (guard stop or a failed check), never
    reported as a clean pass. 'collision' must be detected as robot contact; 'jam' as a guard stop with the cube shift
    within JAM_SLIP_MM. 'offcentre' is reported: accepted if it completes cleanly or is detected."""
    pms = rec.get("per_move", [])
    stopped = any(pm.get("jam_stop") for pm in pms)
    flagged = bool(rec.get("fail_reasons"))
    if case == "collision":
        hit = any(pm.get("arm_arm_max", 0) or pm.get("robot_cube_nonpad_max", 0) for pm in pms) or \
            rec.get("approach", {}).get("arm_arm", 0) > 0
        return hit, "robot contact detected" if hit else "no robot contact detected"
    if case == "jam":
        ok = stopped and all(pm.get("core_slip_mm", 0) <= JAM_SLIP_MM for pm in pms)
        return ok, "guard stop" if ok else "no guard stop or cube shifted too far"
    if case == "offcentre":
        return True, "stopped" if stopped else ("flagged" if flagged else "completed cleanly")
    return (stopped or flagged), ("detected" if (stopped or flagged) else "NOT detected (clean pass reported)")


def run_neg(case: str, start: dict) -> dict:
    ov, moves = NEG_SETUP[case]
    rec = run_seq(moves, ov, start)
    ok, why = neg_outcome(case, rec)
    rec.update({"negative_case": case, "trial_pass_as_turn": rec["pass"], "turn_fail_reasons": rec["fail_reasons"],
                "detected_ok": ok, "negative_outcome": why})
    rec["pass"] = ok                                    # a negative trial passes when the fault is handled
    rec["fail_reasons"] = [] if ok else [f"negative case {case}: {why}"]
    return rec


def run_trial(kind: str, kw: dict) -> dict:
    start = start_draw(kw["seed"])
    ov = kw.get("overrides", {})
    if kind in ("seq", "sens"):
        return run_seq(kw["moves"], ov, start)
    if kind == "hold":
        return run_hold(kw["hold_s"], ov, start)
    if kind == "neg":
        return run_neg(kw["case"], start)
    raise ValueError(kind)
