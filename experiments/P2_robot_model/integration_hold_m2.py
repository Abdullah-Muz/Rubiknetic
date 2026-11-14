"""EXPLORATORY, UNSCORED integration test (not Phase 2 work; G1 is not signed off):
one xArm7 + Gripper G2 holding the M2 switched-weld cube with a free core.

* Cube: experiments/M2_switched_welds/m2_model.build_m2_xml, imported unchanged, with
  M1Params(radial_preload=0.0, rig=False). The free core is added exactly as in
  experiments/D6_free_core/run_stab.py (freejoint + 1.7 g core inertial); the core body is placed at
  the grasp point by its pos/quat attributes (initial condition, before any step).
  rig=False: the Phase-1 turning rig (fixed at the world origin) is not needed — turning is out of
  scope — and would otherwise sit inside the robot base.
* Robot: build_model.build("1305+") (gravity compensation on), merged with MjSpec attach (the cube
  is the attached child, names unchanged; the cube's solver options are copied to the parent).
* Grip: G2 pads across the D and E layers (pad tip 2.5 mm beyond the D face, pad top at cube
  z = +9.0 mm, below the U layer at +9.5 mm), pads on the R/L faces, gripper pointing down.
* Run: setup (t < 0, documented, diagnostic as in run_stab): gravity off for 0.5 s while the gripper
  closes; then gravity on and 3 s hold. Simulation via SwitchAuditedSim + SwitchManager (unchanged):
  any qpos/qvel/eq/xfrc/qfrc write or unexpected switch is caught/logged.
Measured: core slip relative to the gripper, penetration, pad contact forces and friction use,
which layers the pads touch, cubie deviation from the lattice, switch log, steps/s.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "experiments" / "M2_switched_welds"))
import build_model as bm  # noqa: E402
from m2_model import build_m2_xml  # noqa: E402
from switching import SwitchAuditedSim, SwitchManager, _rot_err_deg  # noqa: E402

from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params  # noqa: E402
from rubiknetic.cube_physics.readout import CubeReadout  # noqa: E402

HOME_ARM = [0.0, -0.247, 0.0, 0.909, 0.0, 1.15644, 0.0]
SETUP_S, HOLD_S = 2.0, 3.0
# Grasp procedure (PROPOSAL, controller side): ramp the gripper position target instead of a step.
# 0.5 rad/s of driver angle ~= 51 mm/s gap closing (~26 mm/s per pad), inside the G2 15-225 mm/s range.
# A step command (first attempt) hit the floating cube at speed, bounced, and lost it.
CLOSE_RATE = 0.5
TIP_BEYOND_D = 0.0025  # m, pad tip beyond the D face
PADS = {"left": ("left_finger_pad_1", "left_finger_pad_2"), "right": ("right_finger_pad_1", "right_finger_pad_2")}
# PROPOSAL (unscored) hold criterion
SLIP_MM_MAX, ROT_DEG_MAX = 1.0, 1.0


def grasp_frame(robot_path: Path, calib: dict, half: float):
    """Gripper base pose at HOME_ARM (gripper open) and the cube pose for the D+E grip."""
    m = mujoco.MjModel.from_xml_path(str(robot_path))
    d = mujoco.MjData(m)
    gq = [m.jnt_qposadr[m.joint(j).id] for j in bm.GRIPPER_JOINTS]
    d.qpos[[m.jnt_qposadr[m.joint(j).id] for j in bm.ARM_JOINTS]] = HOME_ARM
    d.qpos[gq] = calib["theta_at_calib_width_rad"]
    mujoco.mj_kinematics(m, d)
    b = m.body("xarm_gripper_base_link").id
    R, p0 = d.xmat[b].reshape(3, 3).copy(), d.xpos[b].copy()
    g2 = m.geom("left_finger_pad_2").id
    tip = float((R.T @ (d.geom_xpos[g2] - p0))[2] + m.geom_size[g2, 2])  # pad tip along gripper z
    zc = tip - TIP_BEYOND_D - half  # cube centre along gripper z
    centre = p0 + R @ np.array([0.0, 0.0, zc])
    # cube axes: +z (U) = -gripper z (towards the flange), +x (R) = gripper y (pad normal)
    Rc = np.column_stack([R[:, 1], np.cross(-R[:, 2], R[:, 1]), -R[:, 2]])
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, Rc.flatten())
    pad_cube_z = (-(tip - zc), -(tip - 0.040 - zc))  # pad z-span in cube coordinates (40 mm pads)
    return centre, q, R, {"pad_tip_gripper_z_mm": tip * 1e3, "cube_centre_gripper_z_mm": zc * 1e3,
                          "pad_span_cube_z_mm": [round(v * 1e3, 2) for v in pad_cube_z],
                          "gripper_z_world": np.round(R[:, 2], 4).tolist()}


def build_scene(robot_path: Path, calib: dict):
    mp = M1Params(radial_preload=0.0, rig=False)
    half = 1.5 * mp.pitch - mp.gap / 2
    centre, quat, _, info = grasp_frame(robot_path, calib, half)
    xml = build_m2_xml(mp)
    pos = " ".join(f"{v:.9g}" for v in centre)
    qs = " ".join(f"{v:.9g}" for v in quat)
    # identical to run_stab.build (freejoint + 1.7 g core inertial); pos/quat = grasp point
    xml = xml.replace('<body name="core" pos="0 0 0">',
                      f'<body name="core" pos="{pos}" quat="{qs}">\n      <freejoint name="core_free"/>\n'
                      '      <inertial pos="0 0 0" mass="0.0017" diaginertia="2e-8 2e-8 2e-8"/>', 1)
    cube = mujoco.MjSpec.from_string(xml)
    parent = mujoco.MjSpec.from_file(str(robot_path))
    for k in ("timestep", "integrator", "cone", "impratio", "solver", "iterations", "tolerance", "gravity"):
        setattr(parent.option, k, getattr(cube.option, k))
    for key in list(parent.keys):  # robot keyframe would not cover the cube DOFs
        parent.delete(key)
    parent.worldbody.add_frame().attach_body(cube.body("core"), "", "")
    m = parent.compile()
    info.update({"cube_centre_world_m": np.round(centre, 5).tolist(), "half_cube_mm": half * 1e3,
                 "timestep": m.opt.timestep, "nbody": m.nbody, "nq": m.nq, "nv": m.nv, "neq": m.neq,
                 "cube_mass_kg": round(float(m.body_subtreemass[m.body("core").id]), 4)})
    return m, mp, info


def run(m, mp, calib, F):
    bm.set_grip_force(m, calib, F)
    sim = SwitchAuditedSim(m)
    d = sim.d
    mgr = SwitchManager(sim, mp.pitch)
    ro = CubeReadout(m, mp.pitch)
    qa = [m.jnt_qposadr[m.joint(j).id] for j in bm.ARM_JOINTS]
    gq = [m.jnt_qposadr[m.joint(j).id] for j in bm.GRIPPER_JOINTS]
    gid = m.actuator("gripper").id
    th_open = float(m.actuator_ctrlrange[gid, 0])
    # setup writes before the first step (logged): robot joints to the home pose, gripper open
    d.qpos[qa] = HOME_ARM
    d.qpos[gq] = th_open
    sim.log_setup({"kind": "initial robot pose", "arm": HOME_ARM, "gripper_theta": th_open})
    d.ctrl[[m.actuator(f"act{i}").id for i in range(1, 8)]] = HOME_ARM
    d.ctrl[gid] = th_open
    mujoco.mj_forward(m, d)
    dt = m.opt.timestep
    base, core = m.body("xarm_gripper_base_link").id, m.body("core").id
    Rb, pb = d.xmat[base].reshape(3, 3), d.xpos[base]
    z_start = float((Rb.T @ (d.xpos[core] - pb))[2])
    g = m.opt.gravity.copy()
    m.opt.gravity[:] = 0.0
    for k in range(int(SETUP_S / dt)):
        d.ctrl[gid] = min(bm.DRIVE_RANGE[1], th_open + CLOSE_RATE * k * dt)  # ramped close
        sim.step(1)
    m.opt.gravity[:] = g
    Rb, pb = d.xmat[base].reshape(3, 3), d.xpos[base]
    setup_shift_mm = (float((Rb.T @ (d.xpos[core] - pb))[2]) - z_start) * 1e3
    pad_ids = {s: {m.geom(n).id for n in names} for s, names in PADS.items()}
    allpad = pad_ids["left"] | pad_ids["right"]
    cubie_geoms = set(int(x) for x in ro.geom_ids)
    robot_bodies = {b for b in range(1, m.nbody) if m.body_rootid[b] == m.body("link_base").id}

    def rel(dd):
        Rb, pb = dd.xmat[base].reshape(3, 3), dd.xpos[base]
        return Rb.T @ (dd.xpos[core] - pb), Rb.T @ dd.xmat[core].reshape(3, 3)

    p0, R0 = rel(d)
    f6 = np.zeros(6)
    rows = []
    other_names: set[str] = set()
    n = int(HOLD_S / dt)
    every = int(0.01 / dt)
    t0 = time.perf_counter()
    for k in range(n):
        sim.step(1)
        if k % every and k != n - 1:
            continue
        p, R = rel(d)
        fn = {"left": 0.0, "right": 0.0}
        ft = {"left": 0.0, "right": 0.0}
        layers, other = set(), 0
        pos, rot = ro.poses(d)
        gid2idx = {int(gg): i for i, gg in enumerate(ro.geom_ids)}
        for i in range(d.ncon):
            c = d.contact[i]
            g1, g2 = int(c.geom1), int(c.geom2)
            if (g1 in allpad and g2 in cubie_geoms) or (g2 in allpad and g1 in cubie_geoms):
                pg, cg = (g1, g2) if g1 in allpad else (g2, g1)
                mujoco.mj_contactForce(m, d, i, f6)
                s = "left" if pg in pad_ids["left"] else "right"
                fn[s] += f6[0]
                ft[s] += float(np.hypot(f6[1], f6[2]))
                layers.add(int(np.rint(pos[gid2idx[cg]][2])))
            elif (g1 in cubie_geoms and int(m.geom_bodyid[g2]) in robot_bodies) or \
                 (g2 in cubie_geoms and int(m.geom_bodyid[g1]) in robot_bodies):
                other += 1
                rg = g1 if g2 in cubie_geoms else g2
                other_names.add(m.geom(rg).name or f"{m.body(int(m.geom_bodyid[rg])).name} (mesh geom)")
        movable = [i for i in range(26) if sum(map(abs, HOME_POSITIONS[i])) >= 2]
        rows.append({
            "t": (k + 1) * dt,
            "slip_mm": float(np.linalg.norm(p - p0) * 1e3),
            "rot_deg": float(np.degrees(np.linalg.norm(Rotation.from_matrix(R @ R0.T).as_rotvec()))),
            "fn_left": fn["left"], "fn_right": fn["right"], "ft_left": ft["left"], "ft_right": ft["right"],
            "layers": sorted(layers), "other_robot_contacts": other,
            "pen_mm": ro.max_penetration_mm(d),
            "lattice_pos_mm": float(np.abs(pos[movable] - np.rint(pos[movable])).max() * mp.pitch * 1e3),
            "lattice_rot_deg": float(max(_rot_err_deg(rot[i]) for i in movable)),
        })
    wall = time.perf_counter() - t0
    a = {k2: np.array([r[k2] for r in rows]) for k2 in ("slip_mm", "rot_deg", "fn_left", "fn_right",
                                                         "ft_left", "ft_right", "pen_mm", "lattice_pos_mm",
                                                         "lattice_rot_deg", "other_robot_contacts")}
    last = slice(-50, None)
    mu = 0.7  # pad friction (Menagerie pad_box1 0.7, pad_box2 0.6; priority 1)
    fn_tot = a["fn_left"] + a["fn_right"]
    res = {
        "grip_setting_N": F,
        "setup_contact_N_at_t0": [round(rows[0]["fn_left"], 2), round(rows[0]["fn_right"], 2)],
        "core_slip_mm_final": round(float(a["slip_mm"][-1]), 4),
        "core_slip_mm_max": round(float(a["slip_mm"].max()), 4),
        "core_rot_deg_max": round(float(a["rot_deg"].max()), 4),
        "core_slip_mm_at_t_s": {f"{t:g}": round(float(np.interp(t, [r["t"] for r in rows], a["slip_mm"])), 4)
                                for t in (0.05, 0.25, 0.5, 1.0, 2.0, 3.0)},
        "pad_normal_N_mean_last0.5s": [round(float(a["fn_left"][last].mean()), 2), round(float(a["fn_right"][last].mean()), 2)],
        "pad_tangential_N_mean_last0.5s": [round(float(a["ft_left"][last].mean()), 3), round(float(a["ft_right"][last].mean()), 3)],
        "friction_use_max": round(float(((a["ft_left"] + a["ft_right"]) / np.maximum(fn_tot, 1e-9)).max() / mu), 4),
        "layers_touched_by_pads": sorted({ly for r in rows for ly in r["layers"]}),
        "non_pad_robot_cube_contacts_max": int(a["other_robot_contacts"].max()),
        "non_pad_robot_geoms_touching": sorted(other_names),
        "setup_cube_shift_toward_tip_mm": round(setup_shift_mm, 3),
        "max_penetration_mm": round(float(a["pen_mm"].max()), 4),
        "cubie_lattice_dev_max_mm": round(float(a["lattice_pos_mm"].max()), 4),
        "cubie_lattice_dev_max_deg": round(float(a["lattice_rot_deg"].max()), 4),
        "switch_events": [{k2: v for k2, v in e.items() if k2 in ("t", "kind", "face", "reason")} for e in sim.switch_log],
        "audit_violations": sim.violations, "numerical_failures": sim.numerical_failures,
        "steps_per_s": round(n / wall, 1),
        "weight_N": round(float(m.body_subtreemass[core] * np.linalg.norm(g)), 3),
    }
    res["holds"] = bool(res["core_slip_mm_max"] < SLIP_MM_MAX and res["core_rot_deg_max"] < ROT_DEG_MAX
                        and not res["audit_violations"] and not res["numerical_failures"]
                        and res["layers_touched_by_pads"] and max(res["layers_touched_by_pads"]) <= 0)
    return res


def main() -> int:
    robot_path, calib = bm.build("1305+", True)
    m, mp, info = build_scene(robot_path, calib)
    out = {"study": "P2 integration (exploratory, UNSCORED)", "date": time.strftime("%Y-%m-%d %H:%M:%S %z"),
           "mujoco": mujoco.__version__, "scene": info,
           "criterion": f"PROPOSAL: core slip < {SLIP_MM_MAX} mm and rotation < {ROT_DEG_MAX} deg relative to the "
                        "gripper over 3 s, pads only on D/E layers, no audit violation or numerical failure",
           "runs": []}
    print(json.dumps(info, indent=1))
    for F in (10.0, 30.0, 50.0):
        r = run(m, mp, calib, F)
        out["runs"].append(r)
        print(json.dumps(r, indent=1), flush=True)
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "integration_hold_m2.json").write_text(json.dumps(out, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
