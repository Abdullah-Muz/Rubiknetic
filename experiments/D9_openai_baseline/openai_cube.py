"""D9 adapter: OpenAI robogym's simulated Rubik's cube inside Rubiknetic's stage-1 harness.

The cube model is OpenAI's ``rubik_perpendicular.xml`` + ``roundcube.msh`` (robogym, MIT, (c) 2020 OpenAI; see
robogym/SOURCE.md). Its physics is NOT changed: geometry, mesh scale, joints, joint defaults (damping, armature,
frictionloss, the radial "spring" slides), geom density/condim/friction and contact parameters are copied verbatim.

What this adapter changes, and why (all disclosed in PROTOCOL.md):
  * Textures/materials are stripped (render only; the PNGs are not vendored).
  * The cube body "middle" loses its 3 free slides + ball joint and is renamed "core": the core is fixed to the
    world exactly like Rubiknetic's M1 rig v0 (like-for-like; the hand-held free cube of robogym is NOT tested).
  * Names only: each inner body "cubelet:<name>" is renamed ``cubie_name(home)`` and its geom ``cubie_name(home)+"_g"``
    so that CubeReadout / Monitor / scored.Trial find the 26 pieces. The inner body carries the geom and has the
    same orientation as the outer jointed body "body:<name>" (it is a fixed child), so the readout's body xmat is
    the piece orientation. Joint names are left as in the source (they contain upstream typos; we map by body).
  * Rubiknetic's rig (6 turners, 12 pads, actuators) is taken from build_m1_xml(rig=True) with pitch 19.05 mm and
    gap 0.05 mm (19.0 mm cubelets). The only rig change: pad contype 2 -> 1 so the pads collide with OpenAI's
    cubelets (contype=conaffinity=1 by default) without editing OpenAI's geoms. Pads still do not touch each other.
  * Solver <option>: variant A = Rubiknetic M1Params options; variant B = robogym's (see VARIANT_B below).

Usage: ``install("A")`` patches, in-process only, ``scored.build_m1_xml``, ``scored.apply_setup_misalignment`` and
``scored.params_for`` so every unmodified harness function (scored.Trial, run_sequence_trial, run_forgiveness_trial,
run_opposed_trial, run_corner_twist_trial, d8_1b_stage1.run_seq/run_snap) builds this model instead of M1.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

from rubiknetic.cube_logic.geometric import HOME_POSITIONS
from rubiknetic.cube_logic.notation import FACE_NORMAL
from rubiknetic.cube_physics import m1_model
from rubiknetic.cube_physics import scored as SC
from rubiknetic.cube_physics.m1_model import M1Params, cubie_name

HERE = Path(__file__).resolve().parent
SRC_XML = HERE / "robogym" / "rubik_perpendicular.xml"
SRC_MSH = HERE / "robogym" / "roundcube.msh"

PITCH = 0.01905      # FACT: cubelet pos in rubik_perpendicular.xml
CUBELET = 0.019      # FACT (load_test.py): roundcube.msh x 0.095 spans 19.0 mm; re-checked in smoke.py
GEOM = {"pitch": PITCH, "gap": PITCH - CUBELET}

# Variant B: robogym's simulator options for the Dactyl cube envs (cited in PROTOCOL.md).
#   timestep 0.008, iterations 20: robogym/assets/xmls/robot/shadowhand/assets.xml lines 14-17 (<option>), merged
#   into the cube env by robogym/envs/dactyl/common/cube_env.py (HAND_XML = "robot/shadowhand/main.xml").
#   No other <option> attribute is set there, so integrator/cone/solver/impratio/tolerance are MuJoCo defaults
#   (Euler, pyramidal, Newton, 1, 1e-8). n_substeps=10 (cube_env.py line 174; full_perpendicular.py line 60) only sets
#   the env control period (80 ms); it does not change the physics step.
VARIANT_B = {"timestep": 0.008, "iterations": 20, "integrator": "Euler", "cone": "pyramidal", "impratio": 1.0,
             "solver": "Newton", "tolerance": 1e-8}
VARIANTS = {"A": {}, "B": VARIANT_B}

_NAME_TOKEN = {"neg": -1, "pos": 1}


def _home_from_name(name: str) -> tuple[int, int, int]:
    v = [0, 0, 0]
    for m in re.finditer(r"(neg|pos)_([xyz])", name):
        v["xyz".index(m.group(2))] = _NAME_TOKEN[m.group(1)]
    return tuple(v)


def _openai_root() -> ET.Element:
    src = SRC_XML.read_text()
    for pat in (r"\s*<texture[^>]*/>", r"\s*<material[^>]*/>", r'\s*material="[^"]*"'):
        src = re.sub(pat, "", src)
    return ET.fromstring(src)


# Filled by build_xml: home -> (outer body name, [joint names in body order]); used by the setup misalignment.
PIECE_JOINTS: dict[tuple[int, int, int], tuple[str, list[str]]] = {}


def build_xml(p: M1Params) -> str:
    """OpenAI cube (physics unchanged, core fixed, names mapped) + Rubiknetic M1 rig and solver options from ``p``."""
    ours = ET.fromstring(m1_model.build_m1_xml(replace(p, rig=True)))
    theirs = _openai_root()
    root = ET.Element("mujoco", {"model": "d9_openai_cube_m1_rig"})
    root.append(ours.find("compiler"))
    root.append(ours.find("option"))
    asset = ET.SubElement(root, "asset")
    for mesh in theirs.find("asset").findall("mesh"):
        mesh.set("file", str(SRC_MSH))           # absolute path: no asset dict needed by scored.Trial
        asset.append(mesh)
    default = ET.SubElement(root, "default")
    for cls in theirs.find("default").findall("default"):
        default.append(cls)
    for cls in ours.find("default").findall("default"):
        if cls.get("class") == "pad":
            cls.find("geom").set("contype", "1")  # rig-side filter change (see module docstring)
            default.append(cls)
    world = ET.SubElement(root, "worldbody")
    middle = theirs.find("worldbody").find("body")
    assert middle.get("name") == "middle"
    for j in middle.findall("joint"):           # cube:tx/ty/tz (slide) + cube:rot (ball): core fixed to world
        middle.remove(j)
    middle.set("name", "core")
    PIECE_JOINTS.clear()
    for outer in middle.findall("body"):
        inner = outer.find("body")
        home = _home_from_name(inner.get("name").split(":", 1)[1])
        assert np.allclose(np.array(inner.get("pos").split(), float), np.array(home) * PITCH), inner.get("name")
        inner.set("name", cubie_name(home))
        inner.find("geom").set("name", cubie_name(home) + "_g")
        PIECE_JOINTS[home] = (outer.get("name"), [j.get("name") for j in outer.findall("joint")])
    assert sorted(PIECE_JOINTS) == sorted(HOME_POSITIONS)
    world.append(middle)
    for b in ours.find("worldbody").findall("body"):
        if b.get("name", "").startswith("turner_"):
            world.append(b)
    root.append(ours.find("actuator"))
    return ET.tostring(root, encoding="unicode")


def apply_setup_misalignment(sim, misalign_deg: dict) -> None:
    """Same draw and same composition as scored.apply_setup_misalignment (each face layer rotated about its normal,
    premultiplied in dict order), realised through OpenAI's joints: the driver hinge for centres; for the 20 other
    pieces the rotx-roty-rotz hinge angles are the exact intrinsic XYZ Euler decomposition of the target rotation
    (no gimbal issue at +-1 deg). Episode setup before t=0, logged; verified against mj_forward body orientations."""
    m, d = sim.m, sim.d
    target = {h: np.eye(3) for h in HOME_POSITIONS}
    for face, deg in misalign_deg.items():
        if deg == 0.0:
            continue
        n = np.array(FACE_NORMAL[face], float)
        r = Rotation.from_rotvec(np.radians(deg) * n).as_matrix()
        for h in HOME_POSITIONS:
            if np.dot(h, n) == 1:
                target[h] = r @ target[h]
        sim.log_setup({"type": "layer_misalignment", "face": face, "deg": deg, "joints": "openai_hinges"})
    for h, (_, joints) in PIECE_JOINTS.items():
        hinges = [mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, j) for j in joints
                  if m.jnt_type[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, j)] == mujoco.mjtJoint.mjJNT_HINGE]
        if len(hinges) == 1:                     # centre: driver hinge about its face normal
            j = hinges[0]
            rv = Rotation.from_matrix(target[h]).as_rotvec()
            d.qpos[m.jnt_qposadr[j]] += float(rv @ m.jnt_axis[j])
        else:
            assert [tuple(m.jnt_axis[j]) for j in hinges] == [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
            ang = Rotation.from_matrix(target[h]).as_euler("XYZ")
            for j, a in zip(hinges, ang):
                d.qpos[m.jnt_qposadr[j]] = a
    mujoco.mj_forward(m, d)
    ids = [mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, cubie_name(h)) for h in HOME_POSITIONS]
    err = max(np.abs(d.xmat[b].reshape(3, 3) - target[h]).max() for b, h in zip(ids, HOME_POSITIONS))
    assert err < 1e-9, f"setup misalignment mapping error {err}"


def hinge_conditioning(m, d) -> dict:
    """Read-only: smallest singular value of each 3-hinge chain's angular Jacobian (1 = well conditioned, 0 = gimbal
    lock: the piece has lost a rotational DOF)."""
    out = {}
    for h, (outer, joints) in PIECE_JOINTS.items():
        jid = [mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, j) for j in joints]
        dofs = [m.jnt_dofadr[j] for j in jid if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE]
        if len(dofs) < 3:
            continue
        jr = np.zeros((3, m.nv))
        mujoco.mj_jacBody(m, d, None, jr, mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, cubie_name(h)))
        out[cubie_name(h)] = float(np.linalg.svd(jr[:, dofs], compute_uv=False).min())
    return out


_ORIG = {}


def install(variant: str = "A") -> None:
    """Point the unmodified scored harness at this model (in-process monkeypatch; reversible with uninstall())."""
    if not _ORIG:
        _ORIG.update(build=SC.build_m1_xml, setup=SC.apply_setup_misalignment, params=SC.params_for)
    over = {**GEOM, **VARIANTS[variant]}
    orig_params = _ORIG["params"]
    SC.build_m1_xml = build_xml
    SC.apply_setup_misalignment = apply_setup_misalignment
    SC.params_for = lambda setup, **kw: orig_params(setup, **{**over, **kw})


def uninstall() -> None:
    if _ORIG:
        SC.build_m1_xml, SC.apply_setup_misalignment, SC.params_for = _ORIG["build"], _ORIG["setup"], _ORIG["params"]
