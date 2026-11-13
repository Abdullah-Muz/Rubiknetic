"""E1-0 pilot of E1-6 negative controls and the E1-5 M1 forgiveness angle (UNSCORED).

Usage: uv run python experiments/E1-0_calibration/negative_controls.py <case> [key=value ...]
cases: open_pads | opposed_UR | misalign_U:<deg>
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import mujoco
import numpy as np

from rubiknetic.cube_logic import HOME_POSITIONS, SOLVED, Move
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml
from rubiknetic.cube_physics.readout import CubeReadout
from rubiknetic.cube_physics.rig import AuditedSim, NumericalFailure, TurnRig
from rubiknetic.cube_physics.trials import environment

sys.path.insert(0, str(Path(__file__).parent))
from run import _coerce  # noqa: E402

QT = np.pi / 2


def radial_dev_mm(ro: CubeReadout, d) -> float:
    pos, _ = ro.poses(d)
    home_r = np.linalg.norm(np.array(HOME_POSITIONS, float), axis=1)
    return float(np.max(np.abs(np.linalg.norm(pos, axis=1) - home_r)) * ro.pitch * 1000)


def main() -> None:
    case, overrides = sys.argv[1], sys.argv[2:]
    overrides_raw = [tuple(o.split("=", 1)) for o in overrides]
    kw = {k: _coerce(k, v) for k, v in overrides_raw}
    p = M1Params(**kw)
    m = mujoco.MjModel.from_xml_string(build_m1_xml(p))
    sim = AuditedSim(m)
    ro = CubeReadout(m, p.pitch)
    rig = TurnRig(sim, pad_close_target=-(p.pad_open_clearance + p.grip_overshoot))
    sim.step(500)
    d = sim.d
    rec: dict = {"experiment": "E1-0 (pilot of E1-6 / E1-5)", "scored": False, "case": case,
                 "overrides": kw, "params": {k: v for k, v in asdict(p).items() if k != "extra"},
                 "environment": environment()}

    def rot(face, r0, mem):
        _, r1 = ro.poses(d)
        return float(np.mean(ro.rotation_about_deg(r0, r1, mem, face)))

    _, r0 = ro.poses(d)
    mem = {f: ro.layer_members(d, f) for f in "URFDLB"}

    try:
        _run_case(case, rec, rig, ro, d, r0, mem, rot)
    except NumericalFailure as e:
        rec["numerical_failure"] = str(e)
        rec["note"] = "trial VOID: simulation diverged; any later readings would reflect MuJoCo's auto-reset"
    rec["numerical_failures"] = sim.numerical_failures
    rec["edit_audit_violations"] = sim.violations
    suffix = "".join(f"__{k}={v}" for k, v in sorted(overrides_raw)) if overrides_raw else "__nominal"
    out = Path(__file__).parent / "results" / f"neg_{case.replace(':', '_')}{suffix}.json".replace(",", "-")
    out.write_text(json.dumps(rec, indent=1, default=list))
    print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rec.items()
                      if k not in ("environment",)}))


def _run_case(case, rec, rig, ro, d, r0, mem, rot) -> None:
    if case == "open_pads":
        log = rig.rotate({"U": -QT}, grip=False)
        o = ro.observe(d)
        rec.update(U_layer_rotation_deg=rot("U", r0, mem["U"]), turner_final_deg=log.turner_angle_deg[-1],
                   observed_valid=o.valid, solved=bool(o.valid and o.state == SOLVED),
                   expectation="no layer motion; state stays solved")
    elif case == "opposed_UR":
        log = rig.rotate({"U": -QT, "R": -QT}, grip=True)
        o = ro.observe(d)
        rec.update(U_layer_rotation_deg=rot("U", r0, mem["U"]), R_layer_rotation_deg=rot("R", r0, mem["R"]),
                   max_turner_torque_Nm=float(np.max(np.abs(log.turner_torque))),
                   max_radial_deviation_mm=radial_dev_mm(ro, d),
                   max_penetration_mm=float(max(0.0, -min(log.min_contact_dist_mm))),
                   observed_valid=o.valid, observe_problems=o.problems,
                   expectation="jam: not both layers rotate; no separation (radial dev small)")
    elif case.startswith("misalign_U:"):
        deg = float(case.split(":")[1])
        rig.rotate({"U": -np.radians(deg)}, grip=True)
        u_mis = rot("U", r0, mem["U"])
        _, r1 = ro.poses(d)
        mem1 = {f: ro.layer_members(d, f) for f in "URFDLB"}
        log = rig.rotate({"R": -QT}, grip=True)
        r_rot = rot("R", r1, mem1["R"])
        u_change = rot("U", r1, [i for i in mem1["U"] if i not in mem1["R"]])  # U cubies not shared with R
        o_mid = ro.observe(d)
        # Oracle check uses the OBSERVED move: a completed R (|rot| > 45) or none.
        observed = [Move("R", 1)] if r_rot < -45 else []
        oracle_ok = bool(o_mid.valid and o_mid.state == SOLVED.apply_all(observed)) if o_mid.valid else None
        # Recovery by MEASURED amounts (not commanded): undo R, then remove remaining U offset.
        rig.rotate({"R": -np.radians(r_rot)}, grip=True)
        _, r2 = ro.poses(d)
        u_now = u_mis + u_change
        rig.rotate({"U": -np.radians(u_now)}, grip=True)
        o_end = ro.observe(d)
        rec.update(U_misalignment_deg=u_mis, R_layer_rotation_deg=r_rot, U_change_during_R_deg=u_change,
                   R_max_turner_torque_Nm=float(np.max(np.abs(log.turner_torque))),
                   observed_valid_after_R_attempt=o_mid.valid, observe_problems=o_mid.problems,
                   oracle_match_after_R_attempt=oracle_ok,
                   max_radial_deviation_mm=radial_dev_mm(ro, d),
                   max_penetration_mm_R_attempt=float(max(0.0, -min(log.min_contact_dist_mm))),
                   recovered_solved=bool(o_end.valid and o_end.state == SOLVED),
                   expectation=("either R completes and the observed state matches the oracle "
                                "(U pushed back = corner cutting), or R is blocked and the state reads "
                                "UNKNOWN; never an illegal or mismatched state"))
    else:
        raise SystemExit(f"unknown case {case}")


if __name__ == "__main__":
    main()
