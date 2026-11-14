"""Generate an xArm7 + UFACTORY Gripper G2 MJCF from third-party assets (UNSCORED Phase 2 prototype).

Inputs (third-party, BSD-3-Clause, Copyright (c) 2018 UFACTORY Inc.; NOT in the repo,
see third_party_cad/robot/SOURCES.md):
  * MuJoCo Menagerie ufactory_xarm7/xarm7.xml + assets/*.stl   (arm + original-gripper MJCF)
  * UFACTORY xarm_ros2 xarm_description (joint_limits*.yaml, xarm7_1305 meshes, G2 .dae meshes)
  * third_party_cad/robot/g2_meshes/*_g2.stl  (made by convert_g2_meshes.py from the G2 .dae)

Output (git-ignored, derived from BSD-3 material):
  third_party_cad/robot/generated/xarm7_g2_<revision>[_nogc].xml
  third_party_cad/robot/generated/xarm7_g2_<revision>[_nogc]_gripper_calibration.json

Usage (project venv):
  python experiments/P2_robot_model/build_model.py [--revision 1305+|pre-1305] [--no-gravcomp]
                                                    [--grip-force 50]

The generator never runs code from the downloads; it only parses XML/YAML text and
loads meshes through MuJoCo.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
TP = ROOT / "third_party_cad" / "robot"
MEN = TP / "src" / "menagerie" / "ufactory_xarm7"
XDESC = TP / "src" / "xarm_ros2" / "xarm_description"
G2_MESHES = TP / "g2_meshes"
OUT_DIR = TP / "generated"

ARM_JOINTS = [f"joint{i}" for i in range(1, 8)]
ARM_LINKS = [f"link{i}" for i in range(1, 8)]
GRIPPER_JOINTS = [
    "left_driver_joint", "left_finger_joint", "left_inner_knuckle_joint",
    "right_driver_joint", "right_finger_joint", "right_inner_knuckle_joint",
]
GRIPPER_PARTS = [
    "base_link", "left_outer_knuckle", "left_finger", "left_inner_knuckle",
    "right_outer_knuckle", "right_finger", "right_inner_knuckle",
]

# FACT: xarm_ros2 humble @ ac736c92, config/xarm7/joint_limits.yaml and joint_limits_1305.yaml
# ("max torque = torque constant x 100 (gear ratio) x overload limit"). Peak/overload values,
# accepted by the user as working torque limits (DECISION_LOG P-17). Verified against the
# YAML text at build time by _check_efforts_against_yaml().
REVISIONS = {
    "pre-1305": {
        "efforts_Nm": [163.2, 163.2, 81.6, 81.6, 81.6, 30.6, 30.6],
        "yaml": "config/xarm7/joint_limits.yaml",
        "arm_meshes": "menagerie",  # = xarm_ros2 meshes/xarm7/visual/*.stl, visual used as collision
    },
    "1305+": {
        "efforts_Nm": [179.4445, 179.4445, 92.0, 92.0, 81.558, 30.6, 30.6],
        "yaml": "config/xarm7/joint_limits_1305.yaml",
        "arm_meshes": "xarm7_1305",  # visual/*.stl + separate collision/*.obj (URDF, model_num >= 1305)
    },
}
DEFAULT_REVISION = "1305+"

# Gripper G2 (FACT, G2 User Manual v2.7.1, RM-06): grip force 10-50 N, stroke 84 +/- 1 mm.
G2_FORCE_MIN_N = 10.0
G2_FORCE_MAX_N = 50.0
# Width at which the force calibration is evaluated (ASSUMPTION: ~57 mm cube).
CALIB_WIDTH_M = 0.057
# FACT: URDF drive_joint limit 0..0.85 rad, velocity 2 rad/s (xarm_gripper.urdf.xacro).
DRIVE_RANGE = (0.0, 0.85)
DRIVE_VEL_LIMIT = 2.0
# PROPOSAL: servo saturates once the position error exceeds this (rad).
GRIP_SAT_ERR_RAD = 0.05
PAD_HALF_THICK = 0.002  # Menagerie pad_box size y (m)
# (a) user-approved 2026-11-13: open gap limited to the G2 drawing's 85 mm (FACT, UM v2.7.1 §6.2)
# by raising the drive-joint lower limit; distal pad extended 3 mm toward the fingertip
# (FACT, STEP measurement: MJCF pads ended 3 mm short of the G2 fingertip).
OPEN_GAP_M = 0.085
PAD_EXT_M = 0.003
PAD2_Z, PAD2_HALF_H = 0.050, 0.0095  # Menagerie pad_box2 centre z (finger frame) and half height
# (c) 1305 spec joint ranges (FACT, RM-05 spec page / RM-07 HW manual v2.7.1), opt-in flag,
# 1305+ only, off until the user confirms the hardware revision.
SPEC_1305_RANGES_DEG = {"joint2": (-117.0, 116.0), "joint4": (-6.0, 225.0)}
INNER_KNUCKLES = ["left_inner_knuckle_joint", "right_inner_knuckle_joint"]


# --------------------------------------------------------------------------- helpers
def _check_efforts_against_yaml(rev: str) -> None:
    text = (XDESC / REVISIONS[rev]["yaml"]).read_text()
    vals = [float(v) for v in re.findall(r"max_effort:\s*([0-9.]+)", text)]
    if len(vals) != 7 or not np.allclose(vals, REVISIONS[rev]["efforts_Nm"], atol=1e-6):
        raise RuntimeError(f"{rev}: YAML efforts {vals} != table {REVISIONS[rev]['efforts_Nm']}")


def _rel(p: Path) -> str:
    """Mesh path relative to compiler meshdir (= third_party_cad/robot)."""
    return p.relative_to(TP).as_posix()


def _fmt(v) -> str:
    return " ".join(f"{x:.6g}" for x in np.atleast_1d(v))


def _find(root: ET.Element, tag: str, name: str) -> ET.Element:
    el = root.find(f".//{tag}[@name='{name}']")
    if el is None:
        raise KeyError(f"<{tag} name='{name}'> not found")
    return el


# --------------------------------------------------------------------------- MJCF build
def _build_tree(rev: str, gravcomp: bool, grip: dict | None, clip_1305: bool = False) -> ET.ElementTree:
    tree = ET.parse(MEN / "xarm7.xml")
    root = tree.getroot()
    root.set("model", f"xarm7_g2_{rev}" + ("" if gravcomp else "_nogc") + ("_clip" if clip_1305 else ""))
    root.find("compiler").set("meshdir", "..")  # file is written to third_party_cad/robot/generated/

    # --- mesh assets: re-point Menagerie meshes; G2 meshes replace the gripper meshes
    asset = root.find("asset")
    gripper_mesh_names = set(GRIPPER_PARTS)
    for mesh in asset.findall("mesh"):
        fname = mesh.get("file")
        stem = Path(fname).stem
        mesh.set("name", stem)
        if stem in gripper_mesh_names:
            mesh.set("file", _rel(G2_MESHES / f"{stem}_g2.stl"))
        else:
            mesh.set("file", _rel(MEN / "assets" / fname))

    # --- arm meshes for the 1305 hardware (URDF: separate visual STL + collision OBJ)
    if REVISIONS[rev]["arm_meshes"] == "xarm7_1305":
        for link in ["link_base"] + ARM_LINKS:
            ET.SubElement(asset, "mesh", name=f"{link}_1305_vis",
                          file=_rel(XDESC / "meshes/xarm7_1305/visual" / f"{link}.stl"))
            ET.SubElement(asset, "mesh", name=f"{link}_1305_col",
                          file=_rel(XDESC / "meshes/xarm7_1305/collision" / f"{link}.obj"))
            body = _find(root, "body", link)
            old = [g for g in body.findall("geom")]
            assert len(old) == 1, link  # Menagerie: one mesh geom per arm link (visual = collision)
            mat = old[0].get("material")
            body.remove(old[0])
            idx = 1 if body.find("inertial") is not None else 0
            if body.find("joint") is not None:
                idx += 1
            vis = ET.Element("geom", {"class": "visual", "mesh": f"{link}_1305_vis"})
            if mat:
                vis.set("material", mat)
            col = ET.Element("geom", {"class": "collision", "mesh": f"{link}_1305_col"})
            body.insert(idx, col)
            body.insert(idx, vis)

    # --- arm torque limits (actuator forcerange + joint actuatorfrcrange), gravity compensation
    eff = REVISIONS[rev]["efforts_Nm"]
    for i, jname in enumerate(ARM_JOINTS):
        j = _find(root, "joint", jname)
        j.set("actuatorfrcrange", f"{-eff[i]:.10g} {eff[i]:.10g}")
        if gravcomp:
            j.set("actuatorgravcomp", "true")
        a = _find(root, "general", f"act{i + 1}")
        a.set("forcerange", f"{-eff[i]:.10g} {eff[i]:.10g}")
    if gravcomp:
        # Arm links plus the rigidly attached gripper base (no own DOF, so its compensation
        # maps only onto arm joints). Finger/knuckle bodies (~0.21 kg) are NOT compensated:
        # their compensation would leak into passive forces on the gripper joints.
        for b in ARM_LINKS + ["xarm_gripper_base_link"]:
            _find(root, "body", b).set("gravcomp", "1")
    # (c) optional 1305 spec joint ranges (J2, J4) on joint range and actuator ctrlrange
    if clip_1305:
        if rev != "1305+":
            raise ValueError("clip_1305 applies to the 1305+ revision only")
        for jname, (lo, hi) in SPEC_1305_RANGES_DEG.items():
            rng = f"{math.radians(lo):.6f} {math.radians(hi):.6f}"
            _find(root, "joint", jname).set("range", rng)
            _find(root, "general", f"act{jname[-1]}").set("ctrlrange", rng)

    # --- gripper: URDF attach pose (identity on link_eef = link7); Menagerie used quat 0 0 0 1
    _find(root, "body", "xarm_gripper_base_link").set("quat", "1 0 0 0")
    # Gripper joints have no <dynamics> in the URDF; Menagerie's class default gives them the arm's
    # frictionloss=1 N m, which would distort a 10-50 N force calibration. Set to 0 (documented).
    for jname in GRIPPER_JOINTS:
        _find(root, "joint", jname).set("frictionloss", "0")

    # measurement sites at the centre of each pad pair (between pad_1 and pad_2)
    for side, sgn in (("left", -1.0), ("right", 1.0)):
        fb = _find(root, "body", f"{side}_finger")
        ET.SubElement(fb, "site", name=f"{side}_pad_center", pos=f"0 {sgn * 0.024003:.6f} 0.041")
        # (a) distal pad extended PAD_EXT_M toward the fingertip (+z of the finger frame)
        p2 = _find(root, "geom", f"{side}_finger_pad_2")
        p2.set("pos", f"0 {sgn * 0.024003:.6f} {PAD2_Z + PAD_EXT_M / 2:.6f}")
        p2.set("size", f"0.015 {PAD_HALF_THICK} {PAD2_HALF_H + PAD_EXT_M / 2:.6f}")

    # --- gripper actuator: force-limited position servo on the 'split' tendon (= driver angle)
    act = _find(root, "general", "gripper")
    g = grip or {"kp": 100.0, "kv": 10.0, "f_max": 50.0, "theta_open_rad": DRIVE_RANGE[0]}
    th_open = g["theta_open_rad"]
    act.set("ctrlrange", f"{th_open:.6f} {DRIVE_RANGE[1]}")
    act.set("gainprm", f"{g['kp']:.6g}")
    act.set("biasprm", f"0 {-g['kp']:.6g} {-g['kv']:.6g}")
    act.set("forcerange", f"{-g['f_max']:.6g} {g['f_max']:.6g}")
    # (a) drive-joint lower limit = angle at which the pad gap is OPEN_GAP_M
    for side in ("left", "right"):
        _find(root, "joint", f"{side}_driver_joint").set("range", f"{th_open:.6f} {DRIVE_RANGE[1]}")

    # keyframe 'home': gripper joints start at the (new) open angle, gripper ctrl = open
    key = root.find("keyframe/key[@name='home']")
    q = key.get("qpos").split()
    q[7:13] = [f"{th_open:.6f}"] * 6
    key.set("qpos", " ".join(q))
    c = key.get("ctrl").split()
    c[7] = f"{th_open:.6f}"
    key.set("ctrl", " ".join(c))
    return tree


def _write(tree: ET.ElementTree, path: Path, header: str) -> None:
    ET.indent(tree, space="  ")
    body = ET.tostring(tree.getroot(), encoding="unicode")
    path.write_text(f"<!--\n{header}\n-->\n{body}\n")


# --------------------------------------------------------------------------- gripper calibration
def gripper_kinematics(model: mujoco.MjModel, n: int = 171) -> dict:
    """Pad-face opening d(theta) from forward kinematics, all six gripper joints = theta
    (URDF mimic multiplier 1 => parallelogram), expressed in the gripper base frame."""
    data = mujoco.MjData(model)
    qadr = [model.jnt_qposadr[model.joint(j).id] for j in GRIPPER_JOINTS]
    base = model.body("xarm_gripper_base_link").id
    sl, sr = model.site("left_pad_center").id, model.site("right_pad_center").id
    th = np.linspace(DRIVE_RANGE[0], DRIVE_RANGE[1], n)
    d, z = [], []
    for t in th:
        data.qpos[:] = 0
        data.qpos[qadr] = t
        mujoco.mj_kinematics(model, data)
        R, p0 = data.xmat[base].reshape(3, 3), data.xpos[base]
        pl = R.T @ (data.site_xpos[sl] - p0)
        pr = R.T @ (data.site_xpos[sr] - p0)
        d.append((pl[1] - PAD_HALF_THICK) - (pr[1] + PAD_HALF_THICK))
        z.append(0.5 * (pl[2] + pr[2]))
    d, z = np.array(d), np.array(z)
    return {"theta": th, "opening": d, "pad_z": z}


def calibrate_gripper(model: mujoco.MjModel, grip_force_N: float = G2_FORCE_MAX_N) -> dict:
    kin = gripper_kinematics(model)
    th, d = kin["theta"], kin["opening"]
    if not np.all(np.diff(d) < 0):
        raise RuntimeError("opening is not monotonic in theta")
    t57 = float(np.interp(CALIB_WIDTH_M, d[::-1], th[::-1]))
    dd = float(np.interp(t57, th, np.gradient(d, th)))  # m/rad (negative: closing)
    # Virtual work (rigid, frictionless linkage, springs ignored): tendon force f [N m per rad of
    # tendon length = driver angle] and per-pad squeeze force F satisfy f*dtheta = F*|dd|.
    k = abs(dd)  # N m of tendon force per N of grip force
    f_max50 = G2_FORCE_MAX_N * k
    # (b) linkage springs (Menagerie inner-knuckle joints: stiffness, springref) push toward closing;
    # their generalized force along theta at the calibration width is subtracted from the tendon
    # force so that the set-point equals the pad force at 57 mm. Read from the compiled model.
    tau_spring = 0.0
    for jn in INNER_KNUCKLES:
        jid = model.joint(jn).id
        tau_spring += float(model.jnt_stiffness[jid] * (model.qpos_spring[model.jnt_qposadr[jid]] - t57))
    th_open = float(np.interp(OPEN_GAP_M, d[::-1], th[::-1]))
    F = float(min(max(grip_force_N, G2_FORCE_MIN_N), G2_FORCE_MAX_N))
    return {
        "calib_width_m": CALIB_WIDTH_M,
        "theta_at_calib_width_rad": t57,
        "d_opening_d_theta_m_per_rad": dd,
        "tendon_force_per_grip_N": k,
        "spring_tau_at_calib_Nm": tau_spring,
        "spring_offset_N": tau_spring / k,
        "theta_open_rad": th_open,
        "opening_at_theta_open_m": OPEN_GAP_M,
        "opening_at_theta0_m": float(d[0]),
        "opening_at_theta_max_m": float(d[-1]),
        "model_stroke_m": float(OPEN_GAP_M - d[-1]),
        "pad_axial_travel_m": float(np.ptp(kin["pad_z"][th >= th_open])),
        "kp": f_max50 / GRIP_SAT_ERR_RAD,
        "kv": f_max50 / DRIVE_VEL_LIMIT,  # saturated free closing speed ~= URDF 2 rad/s at 50 N
        "f_max": max(F * k - tau_spring, 0.0),
        "grip_force_setting_N": F,
    }


def set_grip_force(model: mujoco.MjModel, calib: dict, grip_force_N: float) -> float:
    """Equivalent of the G2 force setting (1-100 % -> 10-50 N): a model parameter set between
    episodes, not a state edit. Spring offset (b) compensated. Returns the clamped setting in N."""
    F = float(min(max(grip_force_N, G2_FORCE_MIN_N), G2_FORCE_MAX_N))
    f = max(F * calib["tendon_force_per_grip_N"] - calib["spring_tau_at_calib_Nm"], 0.0)
    model.actuator_forcerange[model.actuator("gripper").id] = [-f, f]
    return F


# --------------------------------------------------------------------------- entry point
HEADER = """Generated by experiments/P2_robot_model/build_model.py (Rubiknetic, UNSCORED Phase 2 prototype).
Derived from MuJoCo Menagerie ufactory_xarm7/xarm7.xml and UFACTORY xarm_ros2 xarm_description
(both BSD-3-Clause, Copyright (c) 2018 UFACTORY Inc.; licences in third_party_cad/robot/).
Revision: {rev}; gravity compensation via actuators: {gc}; grip-force setting: {F} N.
Deviations from Menagerie: arm forcerange/actuatorfrcrange = URDF max_effort ({yaml});
{meshnote}G2 meshes (converted .dae); gripper attach quat = URDF identity; gripper joint
frictionloss 0; gripper actuator re-sized to the G2 10-50 N spec (linkage-spring offset compensated);
open gap limited to 85 mm (drive lower limit); distal pads +3 mm toward the fingertip; pad-centre sites
added. J2/J4 1305-spec ranges: {clip}."""


def build(revision: str = DEFAULT_REVISION, gravcomp: bool = True,
          grip_force_N: float = G2_FORCE_MAX_N, clip_1305: bool = False) -> tuple[Path, dict]:
    if revision not in REVISIONS:
        raise ValueError(f"revision must be one of {list(REVISIONS)}")
    if clip_1305 and revision != "1305+":
        raise ValueError("--clip-1305-spec-limits applies to the 1305+ revision only")
    _check_efforts_against_yaml(revision)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"xarm7_g2_{revision}" + ("" if gravcomp else "_nogc") + ("_clip" if clip_1305 else "")
    path = OUT_DIR / f"{stem}.xml"
    hdr = HEADER.format(
        rev=revision, gc=gravcomp, F=grip_force_N, yaml=REVISIONS[revision]["yaml"],
        meshnote=("arm meshes = xarm7_1305 visual STL + collision OBJ; "
                  if REVISIONS[revision]["arm_meshes"] == "xarm7_1305" else ""),
        clip="ON" if clip_1305 else "off (URDF ranges)",
    )
    # pass 1: placeholder gripper gains -> kinematic calibration; pass 2: final model
    _write(_build_tree(revision, gravcomp, None, clip_1305), path, hdr)
    calib = calibrate_gripper(mujoco.MjModel.from_xml_path(str(path)), grip_force_N)
    _write(_build_tree(revision, gravcomp, calib, clip_1305), path, hdr)
    mujoco.MjModel.from_xml_path(str(path))  # must compile
    (OUT_DIR / f"{stem}_gripper_calibration.json").write_text(json.dumps(calib, indent=2))
    return path, calib


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--revision", default=DEFAULT_REVISION, choices=list(REVISIONS))
    ap.add_argument("--no-gravcomp", action="store_true")
    ap.add_argument("--grip-force", type=float, default=G2_FORCE_MAX_N)
    ap.add_argument("--clip-1305-spec-limits", action="store_true",
                    help="1305+ only: J2 -117..116 deg, J4 -6..225 deg (off until the revision is confirmed)")
    a = ap.parse_args()
    path, calib = build(a.revision, not a.no_gravcomp, a.grip_force, a.clip_1305_spec_limits)
    print(f"wrote {path}")
    for k, v in calib.items():
        print(f"  {k}: {v:.6g}" if isinstance(v, float) else f"  {k}: {v}")
    print(f"  (pad axial travel {calib['pad_axial_travel_m']*1e3:.1f} mm; "
          f"theta@57mm {math.degrees(calib['theta_at_calib_width_rad']):.1f} deg)")


if __name__ == "__main__":
    main()
