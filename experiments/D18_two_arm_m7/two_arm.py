"""D18 steps 2-3 (UNSCORED; G2 pre-registration §7 P-2/P-3): two xArm7 + G2 on one table facing each other, the free-core
M7 cube held horizontally by arm A (P-97 stabiliser, from the D end), U turned by arm B (C1 turner, P-107).

Scene: table plane z = 0; arm A base at the origin; arm B ("B_") base at (L, 0, 0) yawed 180 deg; cube centre
(L/2, 0, H); layout.py's IK for the grasp poses. Cube +z (U) = world +x.
Controllers (classical; they read only robot joint states, robot kinematics derived from them, the F/T sample,
commanded targets and time; never the cube or cubie state; the roll direction comes from the nominal layout):
  * arm A: its joint position servos hold the IK grasp pose (actuator gravity compensation); with STAND (default) the
    cube starts on a stand, arm A ramps closed with gravity on and the stand drops away (P-109, P-110);
  * arm B: joints 1-6 under Cartesian impedance at the gripper base (position K_P 4000 N/m (P-115), D_P 60 N.s/m;
    axis direction K_R 50 N.m/rad, D_R 2 N.m.s/rad; weak posture and damping; integral term that integrates only while
    the fingers are open and is held, not zeroed, while gripping), as torque actuators clamped to the URDF peak
    efforts, with actuator gravity compensation; J7 (roll) under torque control with velocity feedforward and a torque
    budget (P-113, P-114); the wrist F/T sensor (P-114) stops a roll at |tau_z| > FT_STOP on two samples; a stall rule
    (lag > 2 deg for 20 ms) as backup. Approach: from 40 mm outside along the axis to the grasp pose in 1 s.
Per move: fixed 0.3 s settle -> ramp B closed -> roll on a cosine ramp, 1 s per quarter -> hold 0.3 s -> open ->
roll back (1 s). Each move is measured from its start (the previous move's end) through its roll-back.
Checks (G2 pre-registration revision 2 §4): oracle, turn error, drift, cubie penetration, causality (fingertip-cubie
force before layer motion), drive (fingertip torque impulse in the commanded direction during the roll), roll-back
rotation and state, contacts (non-fingertip robot-cube, arm-arm, robot-table, robot-stand, robot-block, cube-stand
after the drop) over the start sequence, the approach and every move, core slip and rotation relative to arm A per
move and from t0, the cube's shift during the stand drop and its offset from nominal at t0, and every cubie's
misalignment at the end (absolute; P-125).
Usage (WSL): python two_arm.py [--seq "U U' U2 U' U"] [--grip 20] [--L 1.0] [--H 0.30] [--view]
  --view opens the MuJoCo viewer (needs a display, e.g. WSLg) and does not write a result file.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import layout as LY  # noqa: E402

H, TU, bm = LY.H, LY.TU, LY.bm
D13, E7 = H.D13, H.E7
scored = E7.scored
from rubiknetic.cube_logic import SOLVED, InconsistentTransition, infer_move, parse  # noqa: E402
from rubiknetic.cube_logic.notation import FACE_NORMAL  # noqa: E402
from rubiknetic.cube_physics.magnets import MagnetSystem  # noqa: E402
from rubiknetic.cube_physics.readout import CubeReadout  # noqa: E402
from rubiknetic.cube_physics.rig import AuditedSim, EditAuditError, NumericalFailure  # noqa: E402

K_P, D_P, K_R, D_R, K_Q, D_Q = 4000.0, 60.0, 50.0, 2.0, 2.0, 1.0   # K_P 4000 from the P-109 (3) tuning study (P-115)
# integral action against joint friction (the model's arm joints have ~1 N.m frictionloss, which leaves a 2-5 mm
# static error under pure impedance; D18 finding). Active only while arm B's fingers are open; frozen while gripping.
KI_P, KI_R, I_P_MAX, I_R_MAX = 8000.0, 200.0, 25.0, 3.0
APPROACH = 0.040
SETTLE_S = 0.3
T = scored.THRESHOLDS
OUT = HERE / "results"
YAW180 = np.array([[-1.0, 0, 0], [0, -1.0, 0], [0, 0, 1.0]])
STICKERS = True        # visual-only stickers (no mass, no collision; user 2026-11-26); --no-stickers to omit
STAND = True           # P-109 (1): actuated stand under D+E, gravity-on grasp, then it drops away; --no-stand = D18 v1
STICKER_HALF, STICKER_T = 0.0065, 0.0002
FACE_RGBA = {"U": [1, 1, 1, 1], "D": [1, 0.85, 0, 1], "R": [0.8, 0.05, 0.05, 1], "L": [1, 0.45, 0, 1],
             "F": [0, 0.6, 0.15, 1], "B": [0, 0.25, 0.8, 1]}         # standard scheme; cube-frame faces
STAND_KP, STAND_KV, STAND_DROP, STAND_GAP = 20000.0, 300.0, 0.030, 0.0001
# P-109 (2): J7 stall guard (robot state only). If |J7 command - J7 angle| exceeds GUARD_LAG_DEG for GUARD_HOLD_S
# during a roll, arm B freezes the roll at the current angle and opens. Threshold [pilot].
GUARD = False         # off by default: the lag rule false-triggers (D18 guard test, P-111); --guard to enable
GUARD_LAG_DEG, GUARD_HOLD_S = 3.0, 0.005
ENV = True             # visual-only room (sky gradient, wood table, grey floor, lights; user 2026-11-26); --plain-env
# P-113 (user: option A, docs/research/G2_JAM_DETECTION_RESEARCH_2026-11-26.md): J7 under torque control with
# velocity/acceleration feedforward and a TORQUE BUDGET. tau = clip(tau_ff + PD, tau_ff - BUDGET, tau_ff + BUDGET),
# tau_ff = the controller's MODEL of J7's own losses (damping, friction, inertia) along the commanded motion, so J7
# can push the layer by at most about BUDGET beyond its own losses (arm A's grip holds ~0.9 N.m). Stall rule: if the
# J7 following error exceeds STALL_LAG_DEG for STALL_HOLD_S during a roll, freeze and open. Robot state only.
ROLL_MODE = "ffb"      # "ffb" (P-113) or "servo" (D18 v1: the model's position servo)
J7_D_M, J7_F_M, J7_ARM_M = 2.0, 1.0, 0.1                      # controller model = Menagerie nominal values
J7_KP, J7_KV, BUDGET = 800.0, 80.0, 0.6
# P-113 revision 2 (after the first matrix): the loss model uses the MEASURED J7 rate for damping (at a stall it
# vanishes, so no feedforward torque is pushed into a blocked layer), friction along the commanded direction (needed
# to break away), no inertia feedforward (the PD covers it, ~0.06 deg), and a budget that grows with the modelled loss:
# B = BUDGET + U_MODEL * (|D q_dot| + F), the time-varying threshold idea of the collision literature.
U_MODEL = 0.2
STALL_LAG_DEG, STALL_HOLD_S = 2.0, 0.02
# P-114 (user: "Add the wrist F/T sensor"): UFACTORY 6-axis F/T sensor between arm B's flange and gripper.
# FACT (retail listings): ~600 g, 400 N / 20 N.m, 200 Hz, for xArm serial >= XI1305. ASSUMPTION: a 75 mm (flange)
# x 35 mm disc; noise 0.01 N.m (1 sigma). The guard reads the torque about the tool axis at 200 Hz and freezes the
# roll and opens when |tau_z| > FT_STOP on two consecutive samples. J7 then uses a generous budget (no false stalls).
FT = True
FT_T, FT_R, FT_M = 0.035, 0.0375, 0.6
FT_STOP, FT_NOISE, FT_RATE, FT_N = 1.0, 0.01, 200.0, 2       # FT_STOP: scored value P-125 (trials.configure sets it)
FT_BUDGET = 2.0
SETUP_MISALIGN = None  # {face: deg}: setup misalignment of layers before t0 (as G1's draw_setup), via scored's
OPEN_MIDTURN = False   # G2-7d negative test: arm B's gripper opens halfway through the roll
PAD_MU = 0.8           # fingertip friction (P-97, both arms); the G2-6 screen varies it
SIM_STARTED = False    # set by the first control step; the G2 runner treats an exception before it as a model-load
                       # error (review 3 item 1; trials.reset_phase / simulation_started)
CUBE_OFF = np.zeros(3) # P-109 (3) tuning study: cube start offset (m) from a pilot seed; arm targets stay nominal
OUT_DIR = None
J7_ERR = 0.0           # plant error test: the SIMULATOR's J7 damping, friction, armature scaled by (1 + J7_ERR)
JAM_BLOCK = False      # G2-7 negative test: a world-fixed block above the cube's top face beside the U layer


CORE_ROT_MOVE_DEG = 2.0       # per-move core rotation in arm A's grip (revision 2; justified in the pre-registration)
CONTACT_KEYS = ("pen_cubie", "robot_cube_nonpad", "arm_arm", "robot_table", "robot_stand", "robot_block", "cube_stand")


def _cube_rotations() -> list[np.ndarray]:
    import itertools
    out = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((-1.0, 1.0), repeat=3):
            M = np.zeros((3, 3))
            for i, (j, sgn) in enumerate(zip(perm, signs)):
                M[i, j] = sgn
            if np.linalg.det(M) > 0:
                out.append(M)
    return out


CUBE_ROTS = _cube_rotations()                       # the 24 proper rotations of the cube


def lattice_residual_deg(rots: np.ndarray) -> list[float]:
    """Per cubie: angle (deg) from its rotation in the core frame to the nearest of the 24 cube rotations."""
    out = []
    for R in rots:
        best = min(np.degrees(np.arccos(np.clip((np.trace(Q.T @ R) - 1) / 2, -1.0, 1.0))) for Q in CUBE_ROTS)
        out.append(float(best))
    return out


def model_audit(m) -> dict:
    """No actuator, tendon, equality constraint or gravity compensation may act on a cube body (CLAUDE.md, P-16; the
    magnets act through MagnetSystem's passive callback, P-16). Review 2 S8: every actuator transmission type (joint,
    joint-in-parent, tendon, site, slider-crank, body), every tendon's joints and sites, every equality's objects by
    their object type, and body_gravcomp."""
    core = m.body("core").id
    cube = {b for b in range(m.nbody) if m.body_rootid[b] == core}
    T, O = mujoco.mjtTrn, mujoco.mjtObj

    def body_of(objtype, objid) -> set:
        if objid < 0:
            return set()
        if objtype in (O.mjOBJ_JOINT,):
            return {int(m.jnt_bodyid[objid])}
        if objtype == O.mjOBJ_SITE:
            return {int(m.site_bodyid[objid])}
        if objtype == O.mjOBJ_GEOM:
            return {int(m.geom_bodyid[objid])}
        if objtype == O.mjOBJ_BODY:
            return {int(objid)}
        if objtype == O.mjOBJ_TENDON:
            return tendon_bodies(objid)
        return {-1}                                    # unknown object type: reported as a finding

    def tendon_bodies(t) -> set:
        out = set()
        for w in range(m.tendon_adr[t], m.tendon_adr[t] + m.tendon_num[t]):
            wt, wid = int(m.wrap_type[w]), int(m.wrap_objid[w])
            if wt == mujoco.mjtWrap.mjWRAP_JOINT:
                out.add(int(m.jnt_bodyid[wid]))
            elif wt in (mujoco.mjtWrap.mjWRAP_SITE, mujoco.mjtWrap.mjWRAP_PULLEY) and wid >= 0:
                if wt == mujoco.mjtWrap.mjWRAP_SITE:
                    out.add(int(m.site_bodyid[wid]))
            elif wid >= 0:
                out.add(int(m.geom_bodyid[wid]))
        return out
    trn_obj = {T.mjTRN_JOINT: O.mjOBJ_JOINT, T.mjTRN_JOINTINPARENT: O.mjOBJ_JOINT, T.mjTRN_TENDON: O.mjOBJ_TENDON,
               T.mjTRN_SITE: O.mjOBJ_SITE, T.mjTRN_SLIDERCRANK: O.mjOBJ_SITE, T.mjTRN_BODY: O.mjOBJ_BODY}
    acts = []
    for i in range(m.nu):
        ot = trn_obj.get(int(m.actuator_trntype[i]))
        bodies = body_of(ot, int(m.actuator_trnid[i, 0])) if ot is not None else {-1}
        if int(m.actuator_trntype[i]) in (T.mjTRN_SITE, T.mjTRN_SLIDERCRANK):
            bodies |= body_of(O.mjOBJ_SITE, int(m.actuator_trnid[i, 1]))
        if bodies & cube or -1 in bodies:
            acts.append(m.actuator(i).name)
    tendons = [t for t in range(m.ntendon) if tendon_bodies(t) & cube]
    eqs = []
    for i in range(m.neq):
        et = int(m.eq_type[i])
        # joint and tendon equalities carry objtype UNKNOWN in MuJoCo 4: their objects follow from the type
        ot = (O.mjOBJ_JOINT if et == mujoco.mjtEq.mjEQ_JOINT else O.mjOBJ_TENDON if et == mujoco.mjtEq.mjEQ_TENDON
              else int(m.eq_objtype[i]))
        bodies = body_of(ot, int(m.eq_obj1id[i])) | body_of(ot, int(m.eq_obj2id[i]))
        if bodies & cube or -1 in bodies:
            eqs.append(i)
    gc = [int(b) for b in cube if m.body_gravcomp[b] != 0.0]
    return {"actuators_on_cube": acts, "equalities_on_cube": eqs, "tendons_on_cube": tendons,
            "gravcomp_on_cube": gc, "n_cube_bodies": len(cube)}


def add_stickers(cube, p) -> None:
    """One thin coloured tile per outward cubie face: visual only (contype = conaffinity = 0, density 0), in the
    cubie body (body origin = core centre, the cubie geom at home * pitch). Physics unchanged (checked: identical
    qpos with and without)."""
    from rubiknetic.cube_logic.geometric import HOME_POSITIONS
    from rubiknetic.cube_logic.notation import FACES
    from rubiknetic.cube_physics.m1_model import cubie_name
    h = (p.pitch - p.gap) / 2
    for home in HOME_POSITIONS:
        body = cube.body(cubie_name(home))
        for f in FACES:
            n = np.array(FACE_NORMAL[f], float)
            if np.dot(home, n) != 1:
                continue
            g = body.add_geom()
            g.name = f"{cubie_name(home)}_st{f}"
            g.type = mujoco.mjtGeom.mjGEOM_BOX
            size = np.full(3, STICKER_HALF)
            size[int(np.argmax(np.abs(n)))] = STICKER_T / 2
            g.size = size.tolist()
            g.pos = (np.array(home, float) * p.pitch + n * (h + STICKER_T / 2)).tolist()
            g.contype, g.conaffinity, g.density, g.group = 0, 0, 0.0, 1
            g.rgba = FACE_RGBA[f]


def add_ft_sensor(sp) -> None:
    """The F/T sensor between link7 and the gripper (in an un-prefixed robot spec): the gripper base moves FT_T out
    along its own axis; a welded 'ft_sensor' body (FT_M kg, disc geom) sits in the gap on link7; a site at the gripper
    base origin carries MuJoCo force/torque sensors, which measure what link7 transmits to the gripper subtree."""
    g = sp.body("xarm_gripper_base_link")
    q = np.array(g.quat, float)
    R = np.zeros(9)
    mujoco.mju_quat2Mat(R, q / np.linalg.norm(q))
    R = R.reshape(3, 3)
    p0 = np.array(g.pos, float)
    g.pos = (p0 + R[:, 2] * FT_T).tolist()
    link7 = sp.body("link7")
    fb = link7.add_body(name="ft_sensor", pos=(p0 + R[:, 2] * FT_T / 2).tolist(), quat=q.tolist())
    fb.mass, fb.inertia, fb.explicitinertial = FT_M, [FT_M * (3 * FT_R ** 2 + FT_T ** 2) / 12] * 2 + [FT_M * FT_R ** 2 / 2], True
    fg = fb.add_geom()
    fg.name, fg.type, fg.size = "ft_disc", mujoco.mjtGeom.mjGEOM_CYLINDER, [FT_R, FT_T / 2, 0]
    fg.rgba, fg.density = [0.75, 0.75, 0.78, 1], 0.0
    st = g.add_site()
    st.name = "ft_site"
    for nm, ty in (("ft_force", mujoco.mjtSensor.mjSENS_FORCE), ("ft_torque", mujoco.mjtSensor.mjSENS_TORQUE)):
        se = sp.add_sensor()
        se.name, se.type, se.objtype, se.objname = nm, ty, mujoco.mjtObj.mjOBJ_SITE, "ft_site"


def b_robot_spec(mu: float = 0.8):
    sp = H.robot_spec(LY.robot_path(), mu, tip_half=TU.TURNER_TIP_HALF, tag="c1")
    if FT:
        add_ft_sensor(sp)
    return sp


def add_environment(sp, L: float) -> None:
    """Visual-only surroundings: a light sky-gradient skybox, a wood-tone checker material on the table plane, a grey
    floor 0.75 m below the table (contype = conaffinity = 0), two directional lights and a brighter headlight. No
    physics change (checked: identical final qpos with and without)."""
    sky = sp.add_texture()
    sky.name, sky.type, sky.builtin = "sky", mujoco.mjtTexture.mjTEXTURE_SKYBOX, mujoco.mjtBuiltin.mjBUILTIN_GRADIENT
    sky.rgb1, sky.rgb2, sky.width, sky.height = [0.75, 0.85, 0.95], [0.97, 0.97, 1.0], 512, 3072
    wood = sp.add_texture()
    wood.name, wood.type, wood.builtin = "wood", mujoco.mjtTexture.mjTEXTURE_2D, mujoco.mjtBuiltin.mjBUILTIN_CHECKER
    wood.rgb1, wood.rgb2, wood.width, wood.height = [0.72, 0.55, 0.38], [0.66, 0.50, 0.34], 512, 512
    floor = sp.add_texture()
    floor.name, floor.type, floor.builtin = "floor", mujoco.mjtTexture.mjTEXTURE_2D, mujoco.mjtBuiltin.mjBUILTIN_CHECKER
    floor.rgb1, floor.rgb2, floor.width, floor.height = [0.80, 0.80, 0.80], [0.70, 0.70, 0.72], 512, 512
    for name, tex, rep_ in (("table_mat", "wood", [4, 3]), ("floor_mat", "floor", [10, 10])):
        mt = sp.add_material()
        mt.name, mt.texrepeat, mt.reflectance = name, rep_, 0.05
        tx = [""] * 10
        tx[int(mujoco.mjtTextureRole.mjTEXROLE_RGB)] = tex
        mt.textures = tx
    fl = sp.worldbody.add_geom()
    fl.name, fl.type, fl.size, fl.pos = "floor_vis", mujoco.mjtGeom.mjGEOM_PLANE, [4.0, 4.0, 0.05], [L / 2, 0, -0.75]
    fl.contype, fl.conaffinity, fl.material = 0, 0, "floor_mat"
    for pos, dr in (([L / 2, -1.0, 2.0], [0, 0.45, -1.0]), ([L / 2, 1.2, 2.5], [0, -0.45, -1.0])):
        lt = sp.worldbody.add_light()
        lt.pos, lt.dir, lt.diffuse, lt.specular = pos, dr, [0.55, 0.55, 0.55], [0.15, 0.15, 0.15]
        lt.type = mujoco.mjtLightType.mjLIGHT_DIRECTIONAL
    sp.visual.headlight.ambient = [0.35, 0.35, 0.35]
    sp.visual.headlight.diffuse = [0.45, 0.45, 0.45]


def build(L: float, Hc: float, mu: float):
    C, half, (pA, RA), (pB, RB), tips = LY.targets(L, Hc)
    sol = LY.solve(L, Hc)
    rp = LY.robot_path()
    p = H.m7_params()
    Rc = np.column_stack([[0, 1.0, 0], [0, 0, 1.0], [1.0, 0, 0]])
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, Rc.flatten())
    xml = D13.with_noslip(H.build_m1_xml(p), E7.NOSLIP)
    tag = '<body name="core" pos="0 0 0">'
    Cn = C.copy()
    C = C + CUBE_OFF                                    # actual cube start (setup); arm targets use the nominal Cn
    xml = xml.replace(tag, f'<body name="core" pos="{" ".join(f"{v:.9g}" for v in C)}" '
                           f'quat="{" ".join(f"{v:.9g}" for v in q)}">\n      <freejoint name="core_free"/>\n'
                           '      <inertial pos="0 0 0" mass="0.0017" diaginertia="2e-8 2e-8 2e-8"/>', 1)
    cube = mujoco.MjSpec.from_string(xml)
    if STICKERS:
        add_stickers(cube, p)
    parent = H.robot_spec(rp, mu)                                  # arm A, P-97 stabiliser fingertips
    for k in ("timestep", "integrator", "cone", "impratio", "solver", "iterations", "tolerance", "gravity",
              "noslip_iterations"):
        setattr(parent.option, k, getattr(cube.option, k))
    for key in list(parent.keys):
        parent.delete(key)
    parent.worldbody.add_frame().attach_body(cube.body("core"), "", "")
    bspec = b_robot_spec(mu)
    if FT:                                               # arm B's grasp IK with the longer tool (same gripper pose)
        mB = b_robot_spec(mu)
        for key in list(mB.keys):
            mB.delete(key)
        mB = mB.compile()
        dB = mujoco.MjData(mB)
        RBt = RB @ (LY.ROLL180 if sol["B"]["roll180"] else np.eye(3))
        qB, eB, rB = LY.ik(mB, dB, "xarm_gripper_base_link", YAW180.T @ (pB - np.array([L, 0, 0])), YAW180.T @ RBt,
                           [np.array(sol["B"]["q"])] + LY.SEEDS)
        lo, hi = mB.jnt_range[[mB.joint(j).id for j in bm.ARM_JOINTS]].T
        sol["B"].update({"q": qB.tolist(), "pos_err_mm": eB * 1e3, "rot_err_deg": rB, "with_ft_sensor": True,
                         "limit_margin_deg": float(np.degrees(np.min(np.minimum(qB - lo, hi - qB))))})
    for key in list(bspec.keys):
        bspec.delete(key)
    fr = parent.worldbody.add_frame(pos=[L, 0, 0], quat=[0, 0, 0, 1.0])
    fr.attach_body(bspec.body("link_base"), "B_", "")
    tbl = parent.worldbody.add_geom()
    tbl.name, tbl.type, tbl.size, tbl.pos = "table", mujoco.mjtGeom.mjGEOM_PLANE, [1.5, 1.0, 0.01], [L / 2, 0, 0]
    tbl.rgba = [0.6, 0.55, 0.5, 1]
    if ENV:
        add_environment(parent, L)
        tbl.material, tbl.rgba = "table_mat", [1, 1, 1, 1]
    if JAM_BLOCK:
        # above the top face (world +z = cube +y), over the U layer (world x from C+12 to C+26 mm), |y| <= 5 mm,
        # 1.5 mm clear of the face: a U-layer corner reaches it about 38-40 deg into a turn
        jb = parent.worldbody.add_geom()
        jb.name, jb.type = "jam_block", mujoco.mjtGeom.mjGEOM_BOX
        jb.size = [0.007, 0.005, 0.005]
        jb.pos = [C[0] + 0.019, 0.0, C[2] + half + 0.0015 + 0.005]
        jb.rgba = [0.9, 0.1, 0.1, 1]
    excl = ["link_base", "B_link_base"]
    if STAND:
        # under D and E only (world x from 2.5 mm inside the D face to 2.5 mm before the E/U boundary), 40 mm wide,
        # top 0.1 mm below the cube's lower face; a stiff vertical slide servo lowers it by STAND_DROP after the grasp
        x0, x1 = C[0] - half + 0.0025, C[0] + 0.5 * p.pitch - 0.0025
        top = C[2] - half - STAND_GAP
        hz = (top - 0.010) / 2
        st = parent.worldbody.add_body(name="stand", pos=[(x0 + x1) / 2, 0.0, top - hz])
        st.add_joint(name="stand_z", type=mujoco.mjtJoint.mjJNT_SLIDE, axis=[0, 0, 1], range=[-0.05, 0.001])
        sg = st.add_geom()
        sg.name, sg.type, sg.size = "stand_g", mujoco.mjtGeom.mjGEOM_BOX, [(x1 - x0) / 2, 0.020, hz]
        sg.friction, sg.condim, sg.rgba = [0.5, 0.005, 0.0001], 3, [0.35, 0.35, 0.4, 1]
        sa = parent.add_actuator(name="stand_z", target="stand_z", trntype=mujoco.mjtTrn.mjTRN_JOINT)
        sa.set_to_position(kp=STAND_KP, kv=STAND_KV)
        sa.forcelimited, sa.forcerange = mujoco.mjtLimited.mjLIMITED_TRUE, [-200.0, 200.0]
        excl.append("stand")
    for b in excl:
        ex = parent.add_exclude()
        ex.bodyname1, ex.bodyname2 = "world", b
    m = parent.compile()
    if STAND:
        m.body_gravcomp[m.body("stand").id] = 1.0
    # arm B joints 1-6 -> torque (motor) actuators, ctrl = torque, range = URDF peak effort; J7 -> roll servo
    for i in range(1, 7):
        a = m.actuator(f"B_act{i}").id
        lim = float(m.actuator_forcerange[a, 1])
        m.actuator_gainprm[a, :] = 0
        m.actuator_gainprm[a, 0] = 1.0
        m.actuator_biasprm[a, :] = 0
        m.actuator_ctrlrange[a] = [-lim, lim]
    # J7 (roll): ROLL_MODE "ffb" (default) turns it into a torque actuator driven by j7_control (P-113, P-114);
    # "servo" keeps the model's position servo (kp 800, kv 80). The joint has 1 N.m friction, 2 N.m.s/rad damping and
    # 0.1 kg.m2 armature (Menagerie).
    a7 = m.actuator("B_act7").id
    j7 = m.joint("B_joint7").id
    if ROLL_MODE == "ffb":
        lim = float(m.actuator_forcerange[a7, 1])
        m.actuator_gainprm[a7, :] = 0
        m.actuator_gainprm[a7, 0] = 1.0
        m.actuator_biasprm[a7, :] = 0
        m.actuator_ctrlrange[a7] = [-lim, lim]
    else:
        m.actuator_ctrlrange[a7] = m.jnt_range[j7]
    v7 = m.jnt_dofadr[j7]
    if J7_ERR:
        m.dof_damping[v7] *= 1 + J7_ERR
        m.dof_frictionloss[v7] *= 1 + J7_ERR
        m.dof_armature[v7] *= 1 + J7_ERR
    info = {"L": L, "H": Hc, "cube_centre": Cn.tolist(), "cube_start": C.tolist(),
            "cube_offset_mm": (CUBE_OFF * 1e3).tolist(), "ik": sol, "impedance": [K_P, D_P, K_R, D_R, K_Q, D_Q],
            "roll": (f"ffb: kp {J7_KP}, kv {J7_KV}, budget {BUDGET} N.m, model D {J7_D_M} F {J7_F_M} arm {J7_ARM_M}; "
                     f"plant error {J7_ERR:+.0%}" if ROLL_MODE == "ffb" else "B_act7 model servo (kp 800, kv 80)"),
            "pad_mu": mu, "nq": m.nq, "nv": m.nv, "nu": m.nu}
    return m, p, info, (pA, RA), (pB, RB), half


class TwoArm:
    def __init__(self, L: float, Hc: float, grip: float, mu: float | None = None):
        mu = PAD_MU if mu is None else mu
        self.m, self.p, self.info, (pA, RA), (pB, RB), self.half = build(L, Hc, mu)
        m = self.m
        cal = LY.calib()
        TU.set_grip(m, cal, "gripper", grip)
        TU.set_grip(m, cal, "B_gripper", grip)
        self.ms = H.install_magnets(m, self.p)
        self.sim = AuditedSim(m)
        self.d = d = self.sim.d
        self.ro = CubeReadout(m, self.p.pitch)
        if SETUP_MISALIGN:                                  # setup writes before the first step (logged)
            scored.apply_setup_misalignment(self.sim, SETUP_MISALIGN)
        J = lambda pre: [m.joint(pre + j).id for j in bm.ARM_JOINTS]  # noqa: E731
        self.qA = np.array([m.jnt_qposadr[j] for j in J("")])
        self.qB = np.array([m.jnt_qposadr[j] for j in J("B_")])
        self.vB = np.array([m.jnt_dofadr[j] for j in J("B_")])
        self.aA = [m.actuator(f"act{i}").id for i in range(1, 8)]
        self.aB = [m.actuator(f"B_act{i}").id for i in range(1, 8)]
        self.gA, self.gB = m.actuator("gripper").id, m.actuator("B_gripper").id
        self.th_open = float(m.actuator_ctrlrange[self.gA, 0])
        self.bodyB = m.body("B_xarm_gripper_base_link").id
        self.baseA, self.core = m.body("xarm_gripper_base_link").id, m.body("core").id
        sol = self.info["ik"]
        qA = np.array(sol["A"]["q"])
        # arm B starts 40 mm outside the grasp pose along its axis (+x world), IK in its own base frame
        m0 = b_robot_spec()
        for key in list(m0.keys):
            m0.delete(key)
        m0 = m0.compile()
        d0 = mujoco.MjData(m0)
        self.pB_grasp, self.RB = pB, RB
        self.pB_pre = pB + APPROACH * np.array([1.0, 0, 0])
        RBt = RB @ (LY.ROLL180 if sol["B"]["roll180"] else np.eye(3))
        qBpre, e, _ = LY.ik(m0, d0, "xarm_gripper_base_link", YAW180.T @ (self.pB_pre - np.array([L, 0, 0])),
                            YAW180.T @ RBt, [np.array(sol["B"]["q"])])
        assert e < 1e-5, e
        d.qpos[self.qA] = qA
        d.qpos[self.qB] = qBpre
        gq = [m.jnt_qposadr[m.joint(j).id] for j in bm.GRIPPER_JOINTS]
        gqB = [m.jnt_qposadr[m.joint("B_" + j).id] for j in bm.GRIPPER_JOINTS]
        d.qpos[gq] = d.qpos[gqB] = self.th_open
        self.sim.log_setup({"kind": "initial poses", "armA": qA.tolist(), "armB_pregrasp": qBpre.tolist()})
        d.ctrl[self.aA] = qA
        d.ctrl[self.gA] = d.ctrl[self.gB] = self.th_open
        self.q0B = qBpre.copy()                       # posture reference for the impedance null space
        # review 1 item 1: the roll direction from the NOMINAL layout (cube U = world +x), never from the cube state
        self.roll_sign = float(np.sign(np.array([1.0, 0.0, 0.0]) @ RBt[:, 2]))
        self.model_audit = model_audit(m)
        self.roll0 = float(qBpre[6])
        self.j7 = [self.roll0, 0.0, 0.0]                  # commanded J7 angle, rate, acceleration
        self.ft_rng = np.random.default_rng(29000)        # F/T noise (pilot seed range)
        self.ft_every = max(1, int(round(1.0 / FT_RATE / m.opt.timestep)))
        if FT:
            sid = m.sensor("B_ft_torque").id
            self.ft_adr = int(m.sensor_adr[sid])
        self.j7_budget_used = 0.0
        if ROLL_MODE == "servo":
            d.ctrl[self.aB[6]] = self.roll0
        else:
            # link inertia about J7 from the robot's own model (mass matrix), with the controller's nominal armature
            mujoco.mj_forward(m, d)
            M = np.zeros((m.nv, m.nv))
            mujoco.mj_fullM(m, d, M)                      # MuJoCo 4 signature (m, d, dst)
            v7 = self.vB[6]
            self.j7_inertia = float(M[v7, v7] - m.dof_armature[v7] + J7_ARM_M)
        mujoco.mj_forward(m, d)
        self.p_d = self.pB_pre.copy()
        self.a_d = RBt[:, 2].copy()
        self.jp, self.jr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
        self.Ip, self.Ir, self.integ = np.zeros(3), np.zeros(3), True
        self.sim.hooks.insert(0, lambda _d: None)
        # classification sets for contact checks
        root = lambda b: m.body_rootid[m.geom_bodyid[b]]  # noqa: E731
        ridA, ridB = m.body("link_base").id, m.body("B_link_base").id
        self.gA_all = np.array([g for g in range(m.ngeom) if root(g) == ridA])
        self.gB_all = np.array([g for g in range(m.ngeom) if root(g) == ridB])
        self.tipsA = [m.geom(n).id for n in H.FINGERTIPS]
        self.tipsB = [m.geom("B_" + n.replace("p97", "c1")).id for n in H.FINGERTIPS]
        self.pads = np.array(self.tipsA + self.tipsB)
        self.cubie = np.array(self.ro.geom_ids)
        self.table = m.geom("table").id
        self.stand_g = m.geom("stand_g").id if STAND else -1
        self.block_g = m.geom("jam_block").id if JAM_BLOCK else -1
        self.f6 = np.zeros(6)
        self.new_acc()                                    # the start sequence is monitored too (review 1 item 2)
        dt = m.opt.timestep
        self.start = {"stand": STAND, "stickers": STICKERS}
        if STAND:
            # P-109 (1): gravity on from the first step. The cube settles on the stand; arm A ramps closed; the stand
            # lowers STAND_DROP clear; settle. Recorded: core shifts and rotation in each phase, stand load.
            sa = m.actuator("stand_z").id
            sg = m.geom("stand_g").id
            d.ctrl[sa] = 0.0

            def pose():
                return d.xpos[self.core].copy(), d.xmat[self.core].reshape(3, 3).copy()

            def rot(Ra, Rb):
                return float(np.degrees(np.linalg.norm(Rotation.from_matrix(Rb @ Ra.T).as_rotvec())))
            c0, R0 = pose()
            self.step(int(round(0.3 / dt)))
            c1, R1 = pose()
            self.start["stand_load_N"] = self.force_on([sg])
            for k in range(int(H.SETUP_S / dt)):
                d.ctrl[self.gA] = min(bm.DRIVE_RANGE[1], self.th_open + H.CLOSE_RATE * k * dt)
                self.step(1)
            self.step(int(round(0.3 / dt)))
            c2, R2 = pose()
            self.start["stand_load_after_grasp_N"] = self.force_on([sg])
            n = int(round(0.5 / dt))
            for k in range(1, n + 1):
                d.ctrl[sa] = -STAND_DROP * k / n
                self.step(1)
            self.stand_dropped = True
            self.step(int(round(0.5 / dt)))
            c3, R3 = pose()
            self.start.update({
                "settle_on_stand_mm": float(np.linalg.norm(c1 - c0) * 1e3), "settle_rot_deg": rot(R0, R1),
                "grasp_shift_mm": float(np.linalg.norm(c2 - c1) * 1e3), "grasp_rot_deg": rot(R1, R2),
                "stand_drop_shift_mm": float(np.linalg.norm(c3 - c2) * 1e3), "stand_drop_rot_deg": rot(R2, R3),
                "stand_contact_after_drop_N": self.force_on([sg]),
                "core_offset_from_nominal_mm": float(np.linalg.norm(c3 - np.array(self.info["cube_centre"])) * 1e3)})
        else:
            # D18 v1 setup (before t0): gravity off while arm A closes, as D17
            g = m.opt.gravity.copy()
            m.opt.gravity[:] = 0.0
            for k in range(int(H.SETUP_S / dt)):
                d.ctrl[self.gA] = min(bm.DRIVE_RANGE[1], self.th_open + H.CLOSE_RATE * k * dt)
                self.ctrl_step()
            m.opt.gravity[:] = g
            for _ in range(int(round(0.5 / dt))):
                self.ctrl_step()
        self.start["contacts"] = {k: v for k, v in self.acc.items() if k in CONTACT_KEYS}
        self.p_t0, self.R_t0 = self.rel()                 # t0: end of the start sequence
        self.residual_t0 = lattice_residual_deg(self.ro.poses(d)[1])

    # ---- arm B impedance (robot state only) -------------------------------------------------------------------
    def impedance(self) -> None:
        m, d = self.m, self.d
        b = self.bodyB
        mujoco.mj_jacBody(m, d, self.jp, self.jr, b)
        v6 = self.vB[:6]
        Jp, Jr = self.jp[:, v6], self.jr[:, v6]
        qd = d.qvel[v6]
        v, w = Jp @ qd, Jr @ qd
        R = d.xmat[b].reshape(3, 3)
        a = R[:, 2]
        ep, er = self.p_d - d.xpos[b], np.cross(a, self.a_d)
        if self.integ:
            dt = m.opt.timestep
            self.Ip = np.clip(self.Ip + KI_P * ep * dt, -I_P_MAX, I_P_MAX)
            self.Ir = np.clip(self.Ir + KI_R * er * dt, -I_R_MAX, I_R_MAX)
        F = K_P * ep - D_P * v + self.Ip
        w_perp = w - (w @ a) * a
        M = K_R * er - D_R * w_perp + self.Ir
        tau = Jp.T @ F + Jr.T @ M + K_Q * (self.q0B[:6] - d.qpos[self.qB[:6]]) - D_Q * qd
        lo = m.actuator_ctrlrange[self.aB[:6], 0]
        hi = m.actuator_ctrlrange[self.aB[:6], 1]
        d.ctrl[self.aB[:6]] = np.clip(tau, lo, hi)

    def j7_control(self) -> None:
        d = self.d
        q, qd = float(d.qpos[self.qB[6]]), float(d.qvel[self.vB[6]])
        qc, qdc, qddc = self.j7
        loss_d, loss_f = J7_D_M * qd, J7_F_M * np.tanh(qdc / 0.02)
        ff = loss_d + loss_f
        B = (FT_BUDGET if FT else BUDGET) + U_MODEL * (abs(loss_d) + J7_F_M)
        tau = ff + J7_KP * (qc - q) + J7_KV * (qdc - qd)
        tau = float(np.clip(tau, ff - B, ff + B))
        self.j7_budget_used = max(self.j7_budget_used, abs(tau - ff))
        lim = self.m.actuator_ctrlrange[self.aB[6], 1]
        d.ctrl[self.aB[6]] = float(np.clip(tau, -lim, lim))

    def set_roll(self, q: float, qd: float = 0.0, qdd: float = 0.0) -> None:
        if ROLL_MODE == "servo":
            self.d.ctrl[self.aB[6]] = q
        else:
            self.j7 = [q, qd, qdd]

    def roll_cmd(self) -> float:
        return float(self.d.ctrl[self.aB[6]]) if ROLL_MODE == "servo" else self.j7[0]

    def ctrl_step(self, n: int = 1) -> None:
        global SIM_STARTED
        for _ in range(n):
            SIM_STARTED = True
            self.impedance()
            if ROLL_MODE == "ffb":
                self.j7_control()
            self.sim.step(1)

    # ---- per-step monitoring ------------------------------------------------------------------------------------
    def contacts(self) -> dict:
        d = self.d
        n = d.ncon
        out = {"pen_pad": 0.0, "pen_cubie": 0.0, "robot_cube_nonpad": 0, "arm_arm": 0, "robot_table": 0,
               "robot_stand": 0, "robot_block": 0, "cube_stand": 0}
        if not n:
            return out
        g1, g2, dist = d.contact.geom1[:n], d.contact.geom2[:n], d.contact.dist[:n]
        cub1, cub2 = np.isin(g1, self.cubie), np.isin(g2, self.cubie)
        pad1, pad2 = np.isin(g1, self.pads), np.isin(g2, self.pads)
        rob1 = np.isin(g1, self.gA_all) | np.isin(g1, self.gB_all)
        rob2 = np.isin(g2, self.gA_all) | np.isin(g2, self.gB_all)
        pc = (pad1 & cub2) | (pad2 & cub1)
        if pc.any():
            out["pen_pad"] = max(0.0, float(-dist[pc].min()) * 1e3)
        cc = cub1 & cub2
        if cc.any():
            out["pen_cubie"] = max(0.0, float(-dist[cc].min()) * 1e3)
        out["robot_cube_nonpad"] = int((((rob1 & ~pad1) & cub2) | ((rob2 & ~pad2) & cub1)).sum())
        aA1, aB1 = np.isin(g1, self.gA_all), np.isin(g1, self.gB_all)
        aA2, aB2 = np.isin(g2, self.gA_all), np.isin(g2, self.gB_all)
        out["arm_arm"] = int(((aA1 & aB2) | (aB1 & aA2)).sum())
        out["robot_table"] = int((((g1 == self.table) & rob2) | ((g2 == self.table) & rob1)).sum())
        for key, g in (("robot_stand", self.stand_g), ("robot_block", self.block_g)):
            if g >= 0:
                out[key] = int((((g1 == g) & rob2) | ((g2 == g) & rob1)).sum())
        if self.stand_g >= 0 and getattr(self, "stand_dropped", False):
            out["cube_stand"] = int((((g1 == self.stand_g) & cub2) | ((g2 == self.stand_g) & cub1)).sum())
        return out

    def tips_cubie_force(self) -> float:
        """Normal force between arm B's fingertips and cubies only (review 1 item 7 / suggestion 8)."""
        d, tot = self.d, 0.0
        cub = set(self.cubie.tolist())
        tips = set(self.tipsB)
        for i in range(d.ncon):
            c = d.contact[i]
            g1, g2 = int(c.geom1), int(c.geom2)
            if (g1 in tips and g2 in cub) or (g2 in tips and g1 in cub):
                mujoco.mj_contactForce(self.m, d, i, self.f6)
                tot += self.f6[0]
        return tot

    def force_on(self, geoms) -> float:
        d, tot = self.d, 0.0
        for i in range(d.ncon):
            c = d.contact[i]
            if c.geom1 in geoms or c.geom2 in geoms:
                mujoco.mj_contactForce(self.m, d, i, self.f6)
                tot += self.f6[0]
        return tot

    def tool_torque(self, axis) -> float:
        """Torque about the cube axis (through the core) that arm B's fingertips apply to the cubies (N.m)."""
        d, tot = self.d, 0.0
        c0 = d.xpos[self.core]
        cub = set(self.cubie.tolist())
        tips = set(self.tipsB)
        for i in range(d.ncon):
            c = d.contact[i]
            g1, g2 = int(c.geom1), int(c.geom2)
            if g1 in tips and g2 in cub:
                sign = 1.0                                   # contact force acts on geom2 (the cubie)
            elif g2 in tips and g1 in cub:
                sign = -1.0
            else:
                continue
            mujoco.mj_contactForce(self.m, d, i, self.f6)
            f = sign * (c.frame.reshape(3, 3).T @ self.f6[:3])
            tot += float(np.cross(c.pos - c0, f) @ axis)
        return tot

    def step(self, n: int) -> None:
        for _ in range(n):
            self.ctrl_step()
            c = self.contacts()
            a = self.acc
            for k in ("pen_pad", "pen_cubie"):
                a[k] = max(a[k], c[k])
            for k in ("robot_cube_nonpad", "arm_arm", "robot_table", "robot_stand", "robot_block", "cube_stand"):
                a[k] = max(a[k], c[k])
            if a["t_force"] is None and a.get("bodies") is not None and self.tips_cubie_force() > T["causal_force_N"]:
                a["t_force"] = float(self.d.time)
            if a["t_motion"] is None and a.get("bodies") is not None:
                ax = a["axis_world"]
                w = float(np.mean(self.d.cvel[a["bodies"], :3] @ ax) - self.d.cvel[self.core, :3] @ ax)
                if abs(np.degrees(w)) > T["causal_speed_dps"]:
                    a["t_motion"] = float(self.d.time)
            a["tau_roll"] = max(a["tau_roll"], abs(float(self.d.actuator_force[self.aB[6]])))
            if a.get("axis_world") is not None:
                tt = self.tool_torque(a["axis_world"])
                a["tau_tool"] = max(a["tau_tool"], abs(tt))
                if a.get("rolling"):
                    a["drive_impulse"] += tt * a["roll_dir"] * self.m.opt.timestep
            fr = self.m.actuator_forcerange
            satA = np.abs(self.d.actuator_force[self.aA]) >= 0.99 * fr[self.aA, 1]
            satB = np.abs(self.d.ctrl[self.aB[:6]]) >= 0.99 * self.m.actuator_ctrlrange[self.aB[:6], 1]
            a["saturated_steps"] += int(satA.any() or satB.any())
            a["track_err_mm"] = max(a["track_err_mm"],
                                    float(np.linalg.norm(self.p_d - self.d.xpos[self.bodyB]) * 1e3))

    def secs(self, s: float) -> int:
        return max(1, int(round(s / self.m.opt.timestep)))

    def new_acc(self) -> None:
        self.acc = {"pen_pad": 0.0, "pen_cubie": 0.0, "robot_cube_nonpad": 0, "arm_arm": 0, "robot_table": 0,
                    "robot_stand": 0, "robot_block": 0, "cube_stand": 0,
                    "t_force": None, "t_motion": None, "tau_roll": 0.0, "tau_tool": 0.0, "saturated_steps": 0,
                    "track_err_mm": 0.0, "bodies": None, "rolling": False, "roll_dir": 0.0, "drive_impulse": 0.0}

    def approach(self) -> dict:
        self.new_acc()
        n = self.secs(1.0)
        for k in range(1, n + 1):
            s = 0.5 - 0.5 * np.cos(np.pi * k / n)
            self.p_d = self.pB_pre + s * (self.pB_grasp - self.pB_pre)
            self.step(1)
        self.step(self.secs(1.0))
        out = {k: v for k, v in self.acc.items() if k not in ("bodies", "rolling", "roll_dir", "drive_impulse")}
        out["final_err_mm"] = float(np.linalg.norm(self.p_d - self.d.xpos[self.bodyB]) * 1e3)
        a = self.d.xmat[self.bodyB].reshape(3, 3)[:, 2]
        out["final_axis_err_deg"] = float(np.degrees(np.arccos(np.clip(a @ self.a_d, -1, 1))))
        return out

    def rel(self):
        d = self.d
        Rb, pb = d.xmat[self.baseA].reshape(3, 3), d.xpos[self.baseA]
        return Rb.T @ (d.xpos[self.core] - pb), Rb.T @ d.xmat[self.core].reshape(3, 3)

    def ramp_grip(self, target: float) -> None:
        d = self.d
        start = float(d.ctrl[self.gB])
        n = self.secs(abs(target - start) / H.CLOSE_RATE)
        for k in range(1, n + 1):
            d.ctrl[self.gB] = start + (target - start) * k / n
            self.step(1)

    def move(self, mv) -> dict:
        m, d, ro = self.m, self.d, self.ro
        self.new_acc()
        _, r0 = ro.poses(d)                                # move start = the previous move's end (gapless)
        p0, R0 = self.rel()
        members = ro.layer_members(d, mv.face)
        Rc = d.xmat[self.core].reshape(3, 3)               # checks only (never used by a controller)
        self.acc["bodies"] = ro.body_ids[members]
        self.acc["axis_world"] = Rc @ np.array(FACE_NORMAL[mv.face], float)
        self.step(self.secs(SETTLE_S))                     # fixed settle (no cube-state rest check)
        grasp_err = float(np.linalg.norm(self.p_d - d.xpos[self.bodyB]) * 1e3)
        self.integ = False                                  # gripping: pure impedance (compliant)
        self.ramp_grip(bm.DRIVE_RANGE[1])
        self.step(self.secs(0.3))
        delta = -np.pi / 2 * {1: 1, 2: 2, 3: -1}[mv.quarter_turns]
        zB = d.xmat[self.bodyB].reshape(3, 3)[:, 2]        # J7 axis ~ gripper axis
        axis_sign_measured = float(np.sign(self.acc["axis_world"] @ zB))     # logged only
        axis_sign = self.roll_sign                         # controller: nominal layout (review 1 item 1)
        self.acc["rolling"], self.acc["roll_dir"] = True, float(np.sign(delta))
        start = self.roll_cmd()
        n = self.secs(abs(delta) / (np.pi / 2))
        q7 = self.qB[6]
        lag_max, over, jam = 0.0, 0, None
        self.j7_budget_used = 0.0
        if ROLL_MODE == "servo":
            lag_lim, hold_n, guard_on = GUARD_LAG_DEG, max(1, self.secs(GUARD_HOLD_S)), GUARD
        else:
            lag_lim, hold_n, guard_on = STALL_LAG_DEG, max(1, self.secs(STALL_HOLD_S)), True
        A, Tn = axis_sign * delta, n * m.opt.timestep
        ft_over, ft_max = 0, 0.0
        for k in range(1, n + 1):
            ph = np.pi * k / n
            self.set_roll(start + A * (0.5 - 0.5 * np.cos(ph)), A * np.pi / (2 * Tn) * np.sin(ph),
                          A * np.pi ** 2 / (2 * Tn ** 2) * np.cos(ph))
            self.step(1)
            if OPEN_MIDTURN and k == n // 2:
                d.ctrl[self.gB] = self.th_open             # G2-7d: the turner lets go mid-turn
            if FT and k % self.ft_every == 0:              # 200 Hz sample, with noise (robot-side sensor)
                tz = float(d.sensordata[self.ft_adr + 2]) + float(self.ft_rng.normal(0.0, FT_NOISE))
                ft_max = max(ft_max, abs(tz))
                ft_over = ft_over + 1 if abs(tz) > FT_STOP else 0
                if ft_over >= FT_N:
                    jam = {"t": float(d.time), "by": "ft", "tau_z_Nm": tz,
                           "roll_done_deg": float(np.degrees(axis_sign * (float(d.qpos[q7]) - start)))}
                    self.set_roll(float(d.qpos[q7]))
                    break
            lag = abs(np.degrees(self.roll_cmd() - float(d.qpos[q7])))
            lag_max = max(lag_max, lag)
            over = over + 1 if lag > lag_lim else 0
            if guard_on and over >= hold_n:
                jam = {"t": float(d.time), "lag_deg": lag,
                       "roll_done_deg": float(np.degrees(axis_sign * (float(d.qpos[q7]) - start)))}
                self.set_roll(float(d.qpos[q7]))           # freeze the roll where it is
                break
        self.acc["rolling"] = False
        if ROLL_MODE == "ffb":
            self.set_roll(self.roll_cmd())                 # hold: no rate or acceleration feedforward
        self.step(self.secs(0.3))
        d.ctrl[self.gB] = self.th_open
        self.step(self.secs(0.3))
        self.integ = True
        _, r1 = ro.poses(d)
        obs = ro.observe(d)
        end = self.roll_cmd()
        n = self.secs(1.0)
        A, Tn = self.roll0 - end, n * m.opt.timestep
        for k in range(1, n + 1):
            ph = np.pi * k / n
            self.set_roll(end + A * (0.5 - 0.5 * np.cos(ph)), A * np.pi / (2 * Tn) * np.sin(ph),
                          A * np.pi ** 2 / (2 * Tn ** 2) * np.cos(ph))
            self.step(1)
        self.set_roll(self.roll0)
        _, r2 = ro.poses(d)                                # after the roll-back (review 1 item 2)
        obs2 = ro.observe(d)
        a = dict(self.acc)                                 # accumulators cover settle, grasp, roll, open, roll-back
        rb = np.abs(ro.rotation_about_deg(r1, r2, list(range(26)), mv.face))
        nominal = -90.0 * {1: 1, 2: 2, 3: -1}[mv.quarter_turns]
        rot = ro.rotation_about_deg(r0, r1, members, mv.face)
        err = (rot - nominal + 180.0) % 360.0 - 180.0
        non = [i for i in range(26) if sum(map(abs, scored.HOME_POSITIONS[i])) >= 2 and i not in members]
        drift = np.abs(ro.rotation_about_deg(r0, r1, non, mv.face))
        p1, R1 = self.rel()
        tf, tm = a["t_force"], a["t_motion"]
        return {"move": str(mv), "obs": obs, "turn_error_deg": float(np.mean(err)), "grasp_err_mm": grasp_err,
                "axis_sign_measured": axis_sign_measured, "roll_sign_used": axis_sign,
                "rollback_rot_deg": float(rb.max()),
                "rollback_state_unchanged": bool(obs.valid and obs2.valid and obs.state == obs2.state),
                "drive_impulse_Nms": a["drive_impulse"],
                "robot_stand_max": a["robot_stand"], "robot_block_max": a["robot_block"],
                "cube_stand_max": a["cube_stand"],
                "j7_lag_max_deg": lag_max, "jam_stop": jam, "j7_budget_used_Nm": self.j7_budget_used,
                "ft_tau_z_max_Nm": ft_max if FT else None,
                "nontarget_drift_deg": float(drift.max()), "pen_cubie_mm": a["pen_cubie"], "pen_pad_mm": a["pen_pad"],
                "max_roll_torque_Nm": a["tau_roll"], "max_tool_torque_on_layer_Nm": a["tau_tool"], "t_tip_force_s": tf, "t_layer_motion_rel_core_s": tm,
                "ok_causal": bool(tm is None or (tf is not None and tf <= tm)),
                "robot_cube_nonpad_max": a["robot_cube_nonpad"], "arm_arm_max": a["arm_arm"],
                "robot_table_max": a["robot_table"], "saturated_steps": a["saturated_steps"],
                "armB_track_err_mm": a["track_err_mm"],
                "core_slip_mm": float(np.linalg.norm(p1 - p0) * 1e3),
                "core_rot_deg": float(np.degrees(np.linalg.norm(Rotation.from_matrix(R1 @ R0.T).as_rotvec())))}


def run(seq: str, grip: float, L: float, Hc: float, viewer=None) -> dict:
    t_wall = time.perf_counter()
    r = TwoArm(L, Hc, grip)
    if viewer is not None:
        viewer(r)
    prev = r.ro.observe(r.d)
    rec = {"study": "D18 two-arm", "scored": False, "sequence": seq, "grip_N": grip, "scene": r.info,
           "t0_solved": bool(prev.valid and prev.state == SOLVED), "per_move": []}
    rec["start"] = r.start
    print("start", json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.start.items()}), flush=True)
    rec["approach"] = r.approach()
    print("approach", json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rec["approach"].items()}),
          flush=True)
    expect = SOLVED
    moves = parse(seq)
    try:
        for mv in moves:
            pm = r.move(mv)
            obs = pm.pop("obs")
            observed = None
            if prev.valid and obs.valid:
                try:
                    observed = infer_move(prev.cube, obs.cube)
                except InconsistentTransition as e:
                    pm["inference_error"] = str(e)
            if observed is not None:
                expect = expect.apply(observed)
            pm["observed_move"] = str(observed) if observed else None
            pm["ok_oracle"] = bool(obs.valid and observed == mv and obs.state == expect)
            pm["ok_turn_error"] = abs(pm["turn_error_deg"]) <= T["turn_error_deg"]
            pm["ok_drift"] = pm["nontarget_drift_deg"] <= T["nontarget_drift_deg"]
            pm["ok_penetration_cubie"] = pm["pen_cubie_mm"] <= T["penetration_mm"]
            pm["ok_no_nonpad_cube_contact"] = pm["robot_cube_nonpad_max"] == 0
            pm["ok_no_arm_arm"] = pm["arm_arm_max"] == 0
            pm["ok_no_table"] = pm["robot_table_max"] == 0
            pm["ok_no_stand_block"] = (pm["robot_stand_max"] == 0 and pm["robot_block_max"] == 0
                                       and pm["cube_stand_max"] == 0)
            pm["ok_drive"] = pm["drive_impulse_Nms"] > 0.0 or pm["jam_stop"] is not None
            pm["ok_rollback"] = pm["rollback_rot_deg"] <= T["nontarget_drift_deg"] and pm["rollback_state_unchanged"]
            pm["ok_core_rot"] = pm["core_rot_deg"] <= CORE_ROT_MOVE_DEG
            pm["ok_all"] = all(v for k, v in pm.items() if k.startswith("ok_"))
            rec["per_move"].append(pm)
            print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in pm.items()}), flush=True)
            prev = obs
            if not pm["ok_oracle"]:
                break
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    final = r.ro.observe(r.d)
    pT, RT = r.rel()
    rec["trial"] = {"core_slip_total_mm": float(np.linalg.norm(pT - r.p_t0) * 1e3),
                    "core_rot_total_deg": float(np.degrees(np.linalg.norm(Rotation.from_matrix(RT @ r.R_t0.T).as_rotvec()))),
                    "residual_t0_deg": r.residual_t0, "residual_end_deg": lattice_residual_deg(r.ro.poses(r.d)[1]),
                    "model_audit": r.model_audit}
    rec.update({"final_matches_oracle": bool(final.valid and final.state == expect),
                "audit_violations": r.sim.violations, "numerical_failures": r.sim.numerical_failures,
                "sim_time_s": float(r.d.time), "wall_s": time.perf_counter() - t_wall,
                "final_qpos_sha256": __import__("hashlib").sha256(r.d.qpos.tobytes()).hexdigest()})
    rec["pass"] = bool(rec["t0_solved"] and "aborted" not in rec and not rec["audit_violations"]
                       and not rec["numerical_failures"] and len(rec["per_move"]) == len(moves)
                       and all(pm["ok_all"] for pm in rec["per_move"]) and rec["final_matches_oracle"])
    MagnetSystem.uninstall()
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq", default="U U' U2 U' U")
    ap.add_argument("--grip", type=float, default=20.0)
    ap.add_argument("--L", type=float, default=1.0)
    ap.add_argument("--H", type=float, default=0.30)
    ap.add_argument("--view", action="store_true")
    ap.add_argument("--no-stickers", action="store_true")
    ap.add_argument("--no-stand", action="store_true", help="D18 v1 gravity-off setup instead of the stand")
    ap.add_argument("--tag", default="")
    ap.add_argument("--plain-env", action="store_true", help="no sky, floor, textures or extra lights")
    ap.add_argument("--roll", default="ffb", choices=("ffb", "servo"))
    ap.add_argument("--j7-err", type=float, default=0.0, help="plant error on J7 damping/friction/armature")
    ap.add_argument("--budget", type=float, default=0.6)
    ap.add_argument("--no-ft", action="store_true", help="no wrist F/T sensor (D18 v1 tool)")
    ap.add_argument("--kp", type=float, default=None)
    ap.add_argument("--dp", type=float, default=None)
    ap.add_argument("--ki", type=float, default=None)
    ap.add_argument("--seed", type=int, default=None, help="pilot seed: cube start offset uniform +-1 mm per axis")
    ap.add_argument("--out", default=None)
    ap.add_argument("--ft-stop", type=float, default=1.0)
    ap.add_argument("--guard", action="store_true", help="enable the J7 lag guard (false-triggers; P-111)")
    ap.add_argument("--jam-block", action="store_true")
    ap.add_argument("--guard-lag", type=float, default=3.0)
    a = ap.parse_args()
    global STICKERS, STAND, GUARD, JAM_BLOCK, GUARD_LAG_DEG, ENV, ROLL_MODE, J7_ERR, BUDGET
    ENV = not a.plain_env
    ROLL_MODE, J7_ERR, BUDGET = a.roll, a.j7_err, a.budget
    global FT, FT_STOP, K_P, D_P, KI_P, CUBE_OFF
    FT, FT_STOP = not a.no_ft, a.ft_stop
    if a.kp is not None:
        K_P = a.kp
    if a.dp is not None:
        D_P = a.dp
    if a.ki is not None:
        KI_P = a.ki
    if a.seed is not None:
        assert 29000 <= a.seed <= 29999, "tuning uses pilot seeds only (29000-29999)"
        CUBE_OFF = np.random.default_rng(a.seed).uniform(-0.001, 0.001, 3)
    STICKERS, STAND = not a.no_stickers, not a.no_stand
    GUARD, JAM_BLOCK, GUARD_LAG_DEG = a.guard, a.jam_block, a.guard_lag
    H.TIP_SOLREF = (0.01, 1.0)                         # soft pads, as scored (P-105)
    viewer, holder = None, {}
    if a.view:
        import mujoco.viewer

        def viewer(r):
            v = mujoco.viewer.launch_passive(r.m, r.d)
            holder["v"] = v
            v.cam.lookat[:] = r.d.xpos[r.core]
            v.cam.distance, v.cam.azimuth, v.cam.elevation = 1.4, 90, -20
            every = max(1, int(round(1 / 60 / r.m.opt.timestep)))
            k = [0]

            def hook(_d):
                k[0] += 1
                if k[0] % every == 0 and v.is_running():
                    v.sync()
            r.sim.hooks.append(hook)
    rec = run(a.seq, a.grip, a.L, a.H, viewer)
    if a.view:                                        # viewing only: never overwrite a recorded result
        print(json.dumps({k: v for k, v in rec.items() if k not in ("per_move", "scene", "approach")}, default=float))
        v = holder.get("v")
        if v is not None:
            print("sequence done; close the viewer window to exit", flush=True)
            while v.is_running():
                time.sleep(0.1)
        return
    out = OUT if a.out is None else Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    name = f"two_arm_F{a.grip:g}_L{a.L:g}_H{a.H:g}_{a.seq.replace(' ', '_').replace(chr(39), 'p')}"
    if STAND:
        name += "_stand"
    if FT:
        name += f"_ft{FT_STOP:g}" + (f"_err{J7_ERR:+g}" if J7_ERR else "")
    elif ROLL_MODE == "ffb":
        name += f"_ffb{BUDGET:g}" + (f"_err{J7_ERR:+g}" if J7_ERR else "")
    if JAM_BLOCK:
        name += "_jam" + ("" if ROLL_MODE == "ffb" else ("_guard" if GUARD else "_noguard"))
    name += a.tag
    if a.seed is not None:
        name += f"_kp{K_P:g}_dp{D_P:g}_ki{KI_P:g}_s{a.seed}"
    (out / f"{name}.json").write_text(json.dumps(rec, indent=1, default=float))
    print(json.dumps({k: v for k, v in rec.items() if k not in ("per_move", "scene", "approach")}, default=float))


if __name__ == "__main__":
    main()
