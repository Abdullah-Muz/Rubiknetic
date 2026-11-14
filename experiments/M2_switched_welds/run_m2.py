"""M2 prototype tests (UNSCORED). Modes: rest | seq | twist | forgive.
Usage (WSL2, repo root): uv run python experiments/M2_switched_welds/run_m2.py <mode> [m1.key=val ...] [degs=...]
Writes a JSON record to experiments/M2_switched_welds/results/<mode>[_tag].json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from m2_model import build_m2_xml  # noqa: E402
from switching import SwitchAuditedSim, SwitchManager  # noqa: E402

from rubiknetic.cube_logic import parse  # noqa: E402
from rubiknetic.cube_logic.cubie import SOLVED  # noqa: E402
from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_logic.transitions import infer_move  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params  # noqa: E402
from rubiknetic.cube_physics.readout import CubeReadout  # noqa: E402
from rubiknetic.cube_physics.rig import EditAuditError, NumericalFailure, TurnRig  # noqa: E402

OUT = Path(__file__).parent / "results"


def make(m1o: dict, wrench=False):
    mp = M1Params(**{"radial_preload": 0.0, **m1o})
    m = mujoco.MjModel.from_xml_string(build_m2_xml(mp))
    sim = SwitchAuditedSim(m, allow_test_wrench=wrench)
    mujoco.mj_forward(m, sim.d)
    mgr = SwitchManager(sim, mp.pitch)
    rig = TurnRig(sim, pad_close_target=-(mp.pad_open_clearance + mp.grip_overshoot))
    return m, sim, mgr, rig, CubeReadout(m, mp.pitch), mp


def pen_hook(state):
    def h(d):
        if d.ncon:
            state["pen"] = max(state["pen"], -float(d.contact.dist[:d.ncon].min()) * 1000)
    return h


def switch_summary(log):
    sw = [e for e in log if e["kind"] in ("unlock", "relock")]
    dke = [abs(e.get("dke", 0.0)) for e in sw]
    return {"n_unlock": sum(e["kind"] == "unlock" for e in log), "n_relock": sum(e["kind"] == "relock" for e in log),
            "n_refuse": sum(e["kind"] == "refuse" for e in log),
            "max_abs_dKE_J": max(dke, default=0.0), "max_impulse_proxy_Ns": max((e.get("impulse_proxy_Ns", 0) for e in sw), default=0.0),
            "max_post_pos_err_mm": max((e.get("pos_err_post_mm", 0) for e in sw), default=0.0),
            "max_relock_off_square_deg": max((e.get("hinge_off_square_deg", 0) for e in sw if e["kind"] == "relock"), default=0.0),
            "max_rel_speed_at_switch": max((abs(e.get("rel_speed_rad_s", 0)) for e in sw), default=0.0)}


def mode_rest(m1o):
    m, sim, mgr, rig, ro, mp = make(m1o)
    st = {"pen": 0.0}
    sim.hooks.append(pen_hook(st))
    _, r0 = ro.poses(sim.d)
    t = time.perf_counter()
    sim.step(int(3.0 / m.opt.timestep))
    el = time.perf_counter() - t
    _, r = ro.poses(sim.d)
    obs = ro.observe(sim.d)
    drift = max(np.degrees(np.linalg.norm(Rotation.from_matrix(r[i] @ r0[i].T).as_rotvec())) for i in range(26))
    return {"valid": obs.valid, "solved": bool(obs.valid and obs.state == SOLVED), "max_rotation_deg": drift,
            "penetration_mm": st["pen"], "steps_per_s": 3.0 / m.opt.timestep / el, "switches": switch_summary(sim.switch_log)}


def mode_seq(m1o, seq="U R U' R' F F' D2 L B'"):
    m, sim, mgr, rig, ro, mp = make(m1o)
    st = {"pen": 0.0}
    sim.hooks.append(pen_hook(st))
    sim.step(int(0.3 / m.opt.timestep))
    prev = ro.observe(sim.d).cube
    rows, t0, s0 = [], time.perf_counter(), sim.steps
    for mv in parse(seq):
        _, r0 = ro.poses(sim.d)
        members = ro.layer_members(sim.d, mv.face)
        others = [i for i in range(26) if sum(map(abs, HOME_POSITIONS[i])) >= 2 and i not in members]
        st["pen"] = 0.0
        nlog = len(sim.switch_log)
        try:
            log = rig.turn(mv)
        except (NumericalFailure, EditAuditError) as e:
            rows.append({"move": str(mv), "aborted": str(e)})
            break
        _, r = ro.poses(sim.d)
        ang = CubeReadout.rotation_about_deg(r0, r, members, mv.face)
        drift = float(np.max(np.abs(CubeReadout.rotation_about_deg(r0, r, others, mv.face))))
        nominal = -90.0 * {1: 1, 2: 2, 3: -1}[mv.quarter_turns]
        obs = ro.observe(sim.d)
        try:
            om = infer_move(prev, obs.cube) if obs.valid else None
        except Exception as e:  # noqa: BLE001
            om = f"inconsistent: {e}"
        if obs.valid:
            prev = obs.cube
        rows.append({"move": str(mv), "observed": str(om), "ok": str(om) == str(mv), "layer_deg": float(np.mean(ang)),
                     "error_deg": float(np.mean(ang) - nominal), "drift_deg": drift, "penetration_mm": st["pen"],
                     "peak_turner_torque_Nm": float(np.max(np.abs(log.turner_torque))),
                     "switches": [{k: v for k, v in e.items() if k != "activated_ids"} for e in sim.switch_log[nlog:]]})
    el = time.perf_counter() - t0
    return {"moves": rows, "all_ok": all(r.get("ok") for r in rows), "steps_per_s": (sim.steps - s0) / el,
            "switches": switch_summary(sim.switch_log)}


def mode_twist(m1o):
    m, sim, mgr, rig, ro, mp = make(m1o, wrench=True)
    d, dt = sim.d, m.opt.timestep
    st = {"pen": 0.0}
    sim.hooks.append(pen_hook(st))
    sim.step(int(0.5 / dt))
    idx = HOME_POSITIONS.index((1, 1, 1))
    body = int(ro.body_ids[idx])
    axis = np.ones(3) / np.sqrt(3)
    _, r0 = ro.poses(d)
    prev, levels = 0.0, []
    try:
        for lvl in [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]:
            st["pen"] = 0.0
            for k in range(int(0.05 / dt) + int(0.25 / dt)):
                tau = prev + (lvl - prev) * min(1.0, (k + 1) / int(0.05 / dt))
                sim.set_test_wrench(body, np.concatenate([np.zeros(3), tau * axis]))
                sim.step()
            _, r = ro.poses(d)
            rv = Rotation.from_matrix(r[idx] @ r0[idx].T).as_rotvec()
            levels.append({"torque_Nm": lvl, "twist_deg": float(np.degrees(rv @ axis)), "penetration_mm": st["pen"]})
            prev = lvl
        sim.set_test_wrench(body, np.zeros(6))
        sim.step(int(0.5 / dt))
        _, r = ro.poses(d)
        obs = ro.observe(d)
        rel = float(np.degrees(Rotation.from_matrix(r[idx] @ r0[idx].T).as_rotvec() @ axis))
        return {"levels": levels, "released_twist_deg": rel, "valid": obs.valid,
                "solved": bool(obs.valid and obs.state == SOLVED), "switches": switch_summary(sim.switch_log)}
    except (NumericalFailure, EditAuditError) as e:
        return {"levels": levels, "aborted": str(e)}


def mode_forgive(m1o, degs=(1.0, 3.0, 6.0, -3.0, -6.0)):
    out = []
    for deg in degs:
        m, sim, mgr, rig, ro, mp = make(m1o)
        d = sim.d
        sim.step(int(0.3 / m.opt.timestep))
        _, r0 = ro.poses(d)
        U = ro.layer_members(d, "U")
        try:
            rig.rotate({"U": -np.radians(deg)}, record=False)
            _, r1 = ro.poses(d)
            mis = float(np.mean(CubeReadout.rotation_about_deg(r0, r1, U, "U")))
            state_after_U = mgr.unlocked
            R = ro.layer_members(d, "R")
            n0 = len(sim.switch_log)
            log = rig.turn(parse("R")[0])
            _, r2 = ro.poses(d)
            angR = float(np.mean(CubeReadout.rotation_about_deg(r1, r2, R, "R")))
            obs = ro.observe(d)
            out.append({"commanded_deg": deg, "U_misaligned_deg": mis, "U_left_unlocked": state_after_U,
                        "R_turned_deg": angR, "observed_valid": obs.valid, "obs_problems": obs.problems[:3],
                        "obs_max_angle_err_deg": obs.max_angle_error_deg, "obs_max_pos_err": obs.max_position_error,
                        "U_after_R_deg": float(np.mean(CubeReadout.rotation_about_deg(r0, r2, U, "U"))),
                        "R_switch_events": [{k: v for k, v in e.items() if k != "activated_ids"} for e in sim.switch_log[n0:]],
                        "peak_R_torque_Nm": float(np.max(np.abs(log.turner_torque)))})
        except (NumericalFailure, EditAuditError) as e:
            out.append({"commanded_deg": deg, "aborted": str(e)})
    return {"trials": out}


if __name__ == "__main__":
    mode = sys.argv[1]
    m1o, kw, tag = {}, {}, ""
    for a in sys.argv[2:]:
        k, v = a.split("=", 1)
        if k.startswith("m1."):
            m1o[k[3:]] = type(getattr(M1Params(), k[3:]))(v)
            tag += f"_{k[3:]}{v}"
        elif k == "degs":
            kw["degs"] = tuple(float(x) for x in v.split(","))
        elif k == "seq":
            kw["seq"] = v
    t = time.perf_counter()
    rec = {"rest": mode_rest, "seq": mode_seq, "twist": mode_twist, "forgive": mode_forgive}[mode](m1o, **kw)
    rec.update({"mode": mode, "m1_overrides": m1o, "wall_s": time.perf_counter() - t, "scored": False})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{mode}{tag}.json").write_text(json.dumps(rec, indent=1, default=str))
    print(json.dumps({k: v for k, v in rec.items() if k not in ("moves", "trials", "levels")}, default=str)[:1500])
    for key in ("moves", "trials", "levels"):
        for r in rec.get(key, []):
            print(" ", json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()
                                   if k not in ("switches", "R_switch_events")}, default=str))
