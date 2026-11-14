"""Sanity tests for the xArm7 + Gripper G2 MJCF (UNSCORED Phase 2 prototype; smoke tests, not validation).

Run (WSL, project venv):
  UV_PROJECT_ENVIRONMENT=$HOME/.venvs/rubiknetic $HOME/.local/bin/uv run \
      python experiments/P2_robot_model/test_model.py

Tests
  T1 load      : both hardware revisions compile in MuJoCo; size, mass, limits.
  T2 hold      : hold two arm poses under gravity with the position servos, with and without
                 gravity compensation routed through the actuators (joint actuatorgravcomp);
                 report sag, actuator torque vs limit. No xfrc_applied / qfrc_applied writes
                 (checked to stay exactly zero).
  T3 stroke    : open/close the gripper in free space; pad-face opening vs the 84 mm spec.
  T4 squeeze   : close on a fixed (static) 57 mm box at grip settings 10/30/50 N; measured pad
                 normal force vs setting; other box contacts; penetration.
  T5 throughput: steps/s (single thread) for the hold and squeeze loops.
Results are written to experiments/P2_robot_model/results/test_results.json.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import time
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_model as bm  # noqa: E402

HERE = Path(__file__).resolve().parent
BOX_HALF = 0.0285  # 57 mm test box
POSES = {
    # Menagerie keyframe 'home' (arm part)
    "home": [0.0, -0.247, 0.0, 0.909, 0.0, 1.15644, 0.0],
    # PROPOSAL: a reaching pose with larger gravity load on J2/J4 (forearm near horizontal)
    "reach": [0.0, 0.7, 0.0, 0.6, 0.0, -0.2, 0.0],
}
HOLD_S = 4.0


def audit_zero(d: mujoco.MjData) -> bool:
    return not (np.any(d.xfrc_applied) or np.any(d.qfrc_applied))


def arm_qadr(m):
    return np.array([m.jnt_qposadr[m.joint(j).id] for j in bm.ARM_JOINTS])


def arm_dadr(m):
    return np.array([m.jnt_dofadr[m.joint(j).id] for j in bm.ARM_JOINTS])


def opening(m, d) -> float:
    """Pad-face opening (m) from the current state, in the gripper base frame."""
    b = m.body("xarm_gripper_base_link").id
    R, p0 = d.xmat[b].reshape(3, 3), d.xpos[b]
    pl = R.T @ (d.site_xpos[m.site("left_pad_center").id] - p0)
    pr = R.T @ (d.site_xpos[m.site("right_pad_center").id] - p0)
    return float((pl[1] - bm.PAD_HALF_THICK) - (pr[1] + bm.PAD_HALF_THICK))


def reset_pose(m, d, q_arm, grip_ctrl=None):
    mujoco.mj_resetDataKeyframe(m, d, m.key("home").id)
    d.qpos[arm_qadr(m)] = q_arm
    d.ctrl[:7] = q_arm
    gid = m.actuator("gripper").id
    d.ctrl[gid] = m.actuator_ctrlrange[gid, 0] if grip_ctrl is None else grip_ctrl  # default: open
    mujoco.mj_forward(m, d)


# --------------------------------------------------------------------------- T1
def t1_load(path: Path) -> dict:
    t0 = time.perf_counter()
    m = mujoco.MjModel.from_xml_path(str(path))
    dt = time.perf_counter() - t0
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    gb = [m.body(n).id for n in ["xarm_gripper_base_link", "left_outer_knuckle", "left_finger",
                                 "left_inner_knuckle", "right_outer_knuckle", "right_finger",
                                 "right_inner_knuckle"]]
    return {
        "load_s": round(dt, 3),
        "nbody": m.nbody, "nq": m.nq, "nv": m.nv, "nu": m.nu, "ngeom": m.ngeom,
        "nmesh": m.nmesh, "neq": m.neq, "ntendon": m.ntendon, "timestep": m.opt.timestep,
        "total_mass_kg": round(float(m.body_subtreemass[0]), 4),
        "gripper_mass_kg": round(float(sum(m.body_mass[i] for i in gb)), 5),
        "arm_forcerange_Nm": [float(m.actuator_forcerange[i, 1]) for i in range(7)],
        "gripper_forcerange": float(m.actuator_forcerange[m.actuator("gripper").id, 1]),
        "contacts_at_home": int(d.ncon),
    }


# --------------------------------------------------------------------------- T2
def t2_hold(path: Path) -> dict:
    m = mujoco.MjModel.from_xml_path(str(path))
    d = mujoco.MjData(m)
    qa, da = arm_qadr(m), arm_dadr(m)
    lim = m.jnt_actfrcrange[[m.joint(j).id for j in bm.ARM_JOINTS], 1]
    out = {}
    nsteps = int(HOLD_S / m.opt.timestep)
    for name, q in POSES.items():
        reset_pose(m, d, q)
        q0 = np.array(q)
        maxdev = np.zeros(7)
        maxtau = np.zeros(7)
        audit = True
        t0 = time.perf_counter()
        for _ in range(nsteps):
            mujoco.mj_step(m, d)
            maxdev = np.maximum(maxdev, np.abs(d.qpos[qa] - q0))
            maxtau = np.maximum(maxtau, np.abs(d.qfrc_actuator[da]))
            audit &= audit_zero(d)
        wall = time.perf_counter() - t0
        gc = getattr(d, "qfrc_gravcomp", None)
        out[name] = {
            "final_dev_rad": np.round(np.abs(d.qpos[qa] - q0), 6).tolist(),
            "max_dev_rad": float(maxdev.max()),
            "max_dev_joint": int(np.argmax(maxdev)) + 1,
            "max_total_joint_torque_Nm": np.round(maxtau, 3).tolist(),
            "max_torque_fraction_of_limit": float((maxtau / lim).max()),
            "gravcomp_Nm_final": None if gc is None else np.round(gc[da], 3).tolist(),
            "passive_Nm_final": np.round(d.qfrc_passive[da], 3).tolist(),
            "finite": bool(np.all(np.isfinite(d.qpos))),
            "no_xfrc_qfrc_applied": bool(audit),
            "steps_per_s": round(nsteps / wall, 1),
        }
    return out


# --------------------------------------------------------------------------- T3
def t3_stroke(path: Path) -> dict:
    m = mujoco.MjModel.from_xml_path(str(path))
    d = mujoco.MjData(m)
    reset_pose(m, d, POSES["home"])
    for _ in range(500):
        mujoco.mj_step(m, d)
    d_open = opening(m, d)
    gid = m.actuator("gripper").id
    d.ctrl[gid] = bm.DRIVE_RANGE[1]
    trace = []
    for k in range(int(2.0 / m.opt.timestep)):
        mujoco.mj_step(m, d)
        trace.append((k * m.opt.timestep, opening(m, d)))
    d_closed = opening(m, d)
    t = np.array(trace)
    span = d_open - d_closed
    t10 = t[np.argmax(t[:, 1] <= d_open - 0.1 * span), 0]
    t90 = t[np.argmax(t[:, 1] <= d_open - 0.9 * span), 0]
    jl = [m.jnt_qposadr[m.joint(j).id] for j in bm.GRIPPER_JOINTS]
    q = d.qpos[jl]
    return {
        "opening_open_mm": round(d_open * 1e3, 2),
        "opening_closed_mm": round(d_closed * 1e3, 2),
        "stroke_mm": round(span * 1e3, 2),
        "spec_stroke_mm": "84 +/- 1 (G2 UM v2.7.1)",
        "close_10_90_s": round(float(t90 - t10), 3),
        "gripper_joint_q_closed_rad": np.round(q, 4).tolist(),
        "parallelogram_mismatch_rad": float(np.ptp(q)),
    }


def pad_span_check(path: Path, gap: float = 0.02916) -> dict:
    """Pad z-span (from the gripper flange face) at the STEP pose gap; STEP fingertip 136.3-176.3 mm."""
    m = mujoco.MjModel.from_xml_path(str(path))
    d = mujoco.MjData(m)
    kin = bm.gripper_kinematics(m)
    th = float(np.interp(gap, kin["opening"][::-1], kin["theta"][::-1]))
    d.qpos[[m.jnt_qposadr[m.joint(j).id] for j in bm.GRIPPER_JOINTS]] = th
    mujoco.mj_kinematics(m, d)
    b = m.body("xarm_gripper_base_link").id
    R, p0 = d.xmat[b].reshape(3, 3), d.xpos[b]
    zs = []
    for g in ("left_finger_pad_1", "left_finger_pad_2"):
        gid = m.geom(g).id
        c = R.T @ (d.geom_xpos[gid] - p0)
        zs += [c[2] - m.geom_size[gid, 2], c[2] + m.geom_size[gid, 2]]
        face_y = abs(c[1]) - m.geom_size[gid, 1]
    return {"gap_mm": gap * 1e3, "pad_z_span_mm": [round(min(zs) * 1e3, 2), round(max(zs) * 1e3, 2)],
            "pad_face_abs_y_mm": round(face_y * 1e3, 2), "STEP_fingertip_z_mm": [136.3, 176.3],
            "STEP_face_abs_y_mm": 14.58}


# --------------------------------------------------------------------------- T4
def build_box_model(path: Path) -> tuple[mujoco.MjModel, dict]:
    """Add a static 57 mm box centred between the open pads at 'home'."""
    m0 = mujoco.MjModel.from_xml_path(str(path))
    d0 = mujoco.MjData(m0)
    reset_pose(m0, d0, POSES["home"])
    for _ in range(500):  # let the arm settle with the gripper open
        mujoco.mj_step(m0, d0)
    c = 0.5 * (d0.site_xpos[m0.site("left_pad_center").id] + d0.site_xpos[m0.site("right_pad_center").id])
    quat = d0.xquat[m0.body("xarm_gripper_base_link").id].copy()
    spec = mujoco.MjSpec.from_file(str(path))
    b = spec.worldbody.add_body(name="test_box_body", pos=c.tolist(), quat=quat.tolist())
    b.add_geom(name="test_box", type=mujoco.mjtGeom.mjGEOM_BOX, size=[BOX_HALF] * 3,
               rgba=[0.9, 0.5, 0.1, 1])
    return spec.compile(), {"box_center_m": np.round(c, 5).tolist()}


def box_contacts(m, d, box_id):
    pads = {"left": {m.geom(f"left_finger_pad_{i}").id for i in (1, 2)},
            "right": {m.geom(f"right_finger_pad_{i}").id for i in (1, 2)}}
    f6 = np.zeros(6)
    res = {"left": 0.0, "right": 0.0, "other": {}, "min_dist_mm": 0.0}
    for i in range(d.ncon):
        con = d.contact[i]
        if box_id not in (con.geom1, con.geom2):
            continue
        other = con.geom2 if con.geom1 == box_id else con.geom1
        mujoco.mj_contactForce(m, d, i, f6)
        res["min_dist_mm"] = min(res["min_dist_mm"], con.dist * 1e3)
        if other in pads["left"]:
            res["left"] += f6[0]
        elif other in pads["right"]:
            res["right"] += f6[0]
        else:
            nm = m.geom(other).name or f"geom{other}(body {m.body(m.geom_bodyid[other]).name})"
            res["other"][nm] = res["other"].get(nm, 0.0) + f6[0]
    return res


def t4_squeeze(path: Path, calib: dict) -> dict:
    m, info = build_box_model(path)
    d = mujoco.MjData(m)
    box = m.geom("test_box").id
    gid = m.actuator("gripper").id
    out = {"setup": info, "settings": {}}
    for F in (10.0, 30.0, 50.0):
        bm.set_grip_force(m, calib, F)
        reset_pose(m, d, POSES["home"])
        out["setup"]["contacts_with_box_at_start"] = box_contacts(m, d, box)["other"] or "none"
        d.ctrl[gid] = bm.DRIVE_RANGE[1]
        n = int(2.0 / m.opt.timestep)
        acc, k, audit, mind = [], 0, True, 0.0
        t0 = time.perf_counter()
        for k in range(n):
            mujoco.mj_step(m, d)
            audit &= audit_zero(d)
            if k >= n - int(0.5 / m.opt.timestep):
                r = box_contacts(m, d, box)
                acc.append((r["left"], r["right"], sum(r["other"].values()), d.actuator_force[gid]))
                mind = min(mind, r["min_dist_mm"])
        wall = time.perf_counter() - t0
        a = np.array(acc)
        r = box_contacts(m, d, box)
        out["settings"][f"{F:.0f}N"] = {
            "left_pad_normal_N_mean": round(float(a[:, 0].mean()), 2),
            "right_pad_normal_N_mean": round(float(a[:, 1].mean()), 2),
            "left_pad_normal_N_std": round(float(a[:, 0].std()), 3),
            "other_box_contacts_N_mean": round(float(a[:, 2].mean()), 3),
            "other_contacts_final": {k2: round(v, 3) for k2, v in r["other"].items()},
            "tendon_force_mean": round(float(a[:, 3].mean()), 4),
            "tendon_forcerange": round(float(m.actuator_forcerange[gid, 1]), 4),
            "opening_final_mm": round(opening(m, d) * 1e3, 2),
            "max_penetration_mm": round(-mind, 3),
            "no_xfrc_qfrc_applied": bool(audit),
            "steps_per_s": round(n / wall, 1),
        }
    return out


# --------------------------------------------------------------------------- main
def main() -> int:
    results = {
        "status": "UNSCORED Phase 2 prototype smoke test; not validation",
        "date": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "env": {"mujoco": mujoco.__version__, "numpy": np.__version__,
                "python": sys.version.split()[0], "platform": platform.platform(),
                "cpu_count": os.cpu_count(), "threads": 1},
    }
    builds = {}
    for rev, gc in (("1305+", True), ("1305+", False), ("pre-1305", True), ("pre-1305", False)):
        path, calib = bm.build(rev, gc)
        builds[(rev, gc)] = (path, calib)
    results["gripper_calibration"] = builds[("1305+", True)][1]

    results["T1_load"] = {f"{rev}{'' if gc else '_nogc'}": t1_load(p) for (rev, gc), (p, _) in builds.items()}
    results["T2_hold"] = {f"{rev}{'' if gc else '_nogc'}": t2_hold(p) for (rev, gc), (p, _) in builds.items()}
    p, calib = builds[("1305+", True)]
    results["T3_stroke"] = t3_stroke(p)
    results["T3_stroke"]["pad_span_vs_STEP"] = pad_span_check(p)
    results["T4_squeeze"] = t4_squeeze(p, calib)
    for k, v in results["T4_squeeze"]["settings"].items():
        F = float(k[:-1])
        v["error_vs_setpoint_N"] = round(0.5 * (v["left_pad_normal_N_mean"] + v["right_pad_normal_N_mean"]) - F, 2)

    # (c) optional 1305 spec ranges: build + load check only (flag off by default)
    pc, _ = bm.build("1305+", True, clip_1305=True)
    mc = mujoco.MjModel.from_xml_path(str(pc))
    results["T1_load"]["1305+_clip"] = {
        "J2_range_deg": np.round(np.degrees(mc.jnt_range[mc.joint("joint2").id]), 3).tolist(),
        "J4_range_deg": np.round(np.degrees(mc.jnt_range[mc.joint("joint4").id]), 3).tolist(),
        "act2_ctrlrange_deg": np.round(np.degrees(mc.actuator_ctrlrange[mc.actuator("act2").id]), 3).tolist(),
        "act4_ctrlrange_deg": np.round(np.degrees(mc.actuator_ctrlrange[mc.actuator("act4").id]), 3).tolist(),
    }
    del mc

    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / "test_results.json").write_text(json.dumps(results, indent=2, default=float))
    print(json.dumps(results, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
