"""Shared trial runner for Phase 1 experiments (E1-x).

A trial physically performs a move sequence with the M1 rig and, after every
move, compares the *observed* discrete state (read from cubie poses) with the
independent oracle. It never writes cubie state.
"""

from __future__ import annotations

import platform
import time
from dataclasses import asdict

import mujoco
import numpy as np

from rubiknetic.cube_logic import SOLVED, Move
from rubiknetic.cube_logic.notation import OPPOSITE, to_string

from .m1_model import M1Params, build_m1_xml, params_record
from .readout import CubeReadout
from .rig import AuditedSim, EditAuditError, NumericalFailure, TurnRig, TurnTiming


def environment() -> dict:
    return {
        "mujoco": mujoco.__version__,
        "numpy": np.__version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": _cpu_name(),
    }


def _cpu_name() -> str:
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor()


def run_sequence(
    params: M1Params,
    moves: list[Move],
    timing: TurnTiming | None = None,
    settle_steps: int = 500,
    stop_on_failure: bool = True,
) -> dict:
    m = mujoco.MjModel.from_xml_string(build_m1_xml(params))
    sim = AuditedSim(m)
    ro = CubeReadout(m, params.pitch)
    rig = TurnRig(sim, pad_close_target=-(params.pad_open_clearance + params.grip_overshoot))
    sim.step(settle_steps)

    expect = SOLVED
    obs0 = ro.observe(sim.d)
    per_move: list[dict] = []
    ok = obs0.valid and obs0.state == expect
    t_wall = time.perf_counter()
    try:
        for mv in moves:
            if not ok and stop_on_failure:
                break
            _, r0 = ro.poses(sim.d)
            members = {f: ro.layer_members(sim.d, f) for f in "URFDLB"}
            log = rig.turn(mv, timing)
            _, r1 = ro.poses(sim.d)
            expect = expect.apply(mv)
            obs = ro.observe(sim.d)
            target_rot = ro.rotation_about_deg(r0, r1, members[mv.face], mv.face)
            opp = OPPOSITE[mv.face]
            opp_rot = ro.rotation_about_deg(r0, r1, members[opp], opp)
            nominal = -90.0 * {1: 1, 2: 2, 3: -1}[mv.quarter_turns]
            # error per cubie wrapped to (-180, 180] so half turns near +-180 average correctly
            err = (target_rot - nominal + 180.0) % 360.0 - 180.0
            match = bool(obs.valid and obs.state == expect)
            per_move.append(
                {
                    "move": str(mv),
                    "target_layer_rotation_deg_mean": float(nominal + np.mean(err)),
                    "target_layer_rotation_deg_spread": float(np.ptp(err)),
                    "turn_error_deg": float(np.mean(err)),
                    "opposite_layer_rotation_deg_max": float(np.max(np.abs(opp_rot))),
                    "observed_valid": bool(obs.valid),
                    "oracle_match": match,
                    "observe_problems": obs.problems,
                    "max_angle_error_deg": obs.max_angle_error_deg,
                    "max_position_error_pitch": obs.max_position_error,
                    "max_turner_torque_Nm": float(np.max(np.abs(log.turner_torque))),
                    "turner_final_deg": log.turner_angle_deg[-1],
                    "max_penetration_mm": float(max(0.0, -min(log.min_contact_dist_mm))),
                }
            )
            ok = match
    except EditAuditError as e:  # pragma: no cover - would indicate a harness bug
        per_move.append({"edit_audit_violation": str(e)})
        ok = False
    except NumericalFailure as e:
        per_move.append({"numerical_failure": str(e)})
        ok = False
    wall = time.perf_counter() - t_wall
    return {
        "sequence": to_string(moves),
        "params": params_record(params),
        "timing": asdict(timing or TurnTiming()),
        "initial_valid_solved": bool(obs0.valid and obs0.state == SOLVED),
        "moves_completed": sum(1 for r in per_move if r.get("oracle_match")),
        "all_match": ok and len(per_move) == len(moves),
        "edit_audit_violations": sim.violations,
        "numerical_failures": sim.numerical_failures,
        "sim_time_s": float(sim.d.time),
        "wall_time_s": wall,
        "per_move": per_move,
    }
