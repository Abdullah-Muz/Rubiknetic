"""D17 stage A (UNSCORED; user, 2026-11-26: "Model the real holder next"): one xArm7 + the Gripper G2 model holding
the free-core M7 cube by two layers, no turning.

Replaces D16's world-fixed slide-pad stand-in by the real gripper model of experiments/P2_robot_model (build_model.py,
revision 1305+, gravity compensation; G2 four-bar, tendon drive, force limit calibrated at 57 mm). Procedure as
P2's integration_hold_m2.py: arm at HOME_ARM (gripper pointing down), gravity off while the gripper ramps closed at
0.5 rad/s (setup, t < 0, logged), then gravity on and a hold.

Cube: M7 exactly as scored in G1 (B1 rigid radius, gap 0.05 mm, rounded edges R 2.5 mm, NoSlip 10, timestep 0.5 ms,
L0 magnets through the unchanged MagnetSystem), rig=False, free core (1.7 g, I 2e-8, as D6/D16), placed at the grasp
point (initial condition).
Fingertips (P-97 stabiliser): one box per finger, 30 wide x 30 deep x 4 mm, replacing the stock pads (robot_spec);
contact mu 0.8, condim 4, rig-pad solref/solimp; flush with the D face, so it covers the D and E layers up to cube
z = +1.5 mm (8 mm below the U/E boundary). --ext-mm moves the fingertip beyond the stock pad tip (design screen).
Measured over the hold: core slip and rotation relative to the gripper; max-cubie |w| per step (D16's jitter
measure); pad-cubie and cubie-cubie penetration; pad forces; layers touched; non-pad robot contacts; audit.
Usage (WSL): python experiments/D17_real_holder_m7/hold.py [--hold 5] [--forces 10,20,30,50]
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
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "experiments" / "P2_robot_model"))
sys.path.insert(0, str(REPO / "experiments" / "D16_free_core_m7"))
import build_model as bm  # noqa: E402
from grip_probe import load_e7  # noqa: E402

E7 = load_e7()
M4, R, D13 = E7.M4, E7.R, E7.D13
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml  # noqa: E402
from rubiknetic.cube_physics.magnets import MagnetSystem  # noqa: E402
from rubiknetic.cube_physics.readout import CubeReadout  # noqa: E402
from rubiknetic.cube_physics.rig import AuditedSim  # noqa: E402

HOME_ARM = [0.0, -0.247, 0.0, 0.909, 0.0, 1.15644, 0.0]   # P2 integration pose (gripper axis = world -z)
SETUP_S, CLOSE_RATE = 2.0, 0.5                             # P2: ramped close, gravity off
TIP_BEYOND_D = 0.0                                         # P-97 fingertip (30 mm deep) flush with the D face
OUT = HERE / "results"
ORIENT = "p04"     # cube placement: "p04" (coaxial grasp from the D end, P-04) or "p2" (P2's M2 test placement)
EXT = 0.0          # fingertip extension beyond the stock G2 pad tip (m), design screen
TIP_SOLREF = None  # fingertip contact solref (timeconst, dampratio); None = rig pads (0.001, 1)
EQ_SOLREF = None   # gripper four-bar equality solref timeconst (s); None = the P2 model's 0.005 (screen)
TIP_HALF = (0.015, 0.002, 0.015)   # P-97 stabiliser fingertip: 30 wide x 4 thick x 30 deep (half sizes, m)
FINGERTIPS = ("left_fingertip_p97", "right_fingertip_p97")


def robot_spec(robot_path: Path, mu: float = 0.8, tip_half=None, tag: str = "p97") -> mujoco.MjSpec:
    """The P2 robot spec with the stock G2 pad boxes replaced by one P-97 fingertip box per finger.

    The stock model has two pad boxes per finger whose faces differ by ~0.06 mm, so only one box touches a flat
    cube (D17 finding); the P-97 fingertip is a single flat pad. The new box is in the stock pads' finger body, at the
    stock pad_2 face plane (same y), its distal end EXT beyond the stock pad tip, contact as the G1 rig pads with
    mu (P-97). The stock pads are kept as visuals only (contype = conaffinity = 0)."""
    p = M1Params()
    MagnetSystem.uninstall()          # a previous scene's passive callback must not run on a model being compiled
    sp = mujoco.MjSpec.from_file(str(robot_path))
    for side in ("left", "right"):
        p2 = sp.geom(f"{side}_finger_pad_2")
        for n in (f"{side}_finger_pad_1", f"{side}_finger_pad_2"):
            g = sp.geom(n)
            g.contype, g.conaffinity = 0, 0
        tip_z = float(p2.pos[2] + p2.size[2]) + EXT
        ft = p2.parent.add_geom()
        th = tip_half or TIP_HALF
        ft.name = f"{side}_fingertip_{tag}"
        ft.type = mujoco.mjtGeom.mjGEOM_BOX
        ft.size = list(th)
        ft.pos = [float(p2.pos[0]), float(p2.pos[1]), tip_z - th[2]]
        ft.quat = list(p2.quat)
        ft.contype, ft.conaffinity, ft.condim, ft.priority = 1, 1, p.pad_condim, 1
        ft.friction = [mu, p.pad_friction[1], p.pad_friction[2]]
        ft.solref = list(TIP_SOLREF or p.pad_solref)
        ft.solimp = list(p.pad_solimp) + [0.5, 2.0]
        ft.mass = 0.005
        ft.rgba = [0.2, 0.6, 0.9, 1]
    if EQ_SOLREF is not None:
        for e in sp.equalities:
            e.solref = [EQ_SOLREF, 1.0]
    return sp


def m7_params() -> M1Params:
    return M1Params(radial_preload=0.0, gap=R.GAP, edge_profile="rounded", edge_radius=E7.EDGE_R, rig=False)


def grasp_frame(robot_path: Path, calib: dict, half: float):
    """As P2 integration_hold_m2.grasp_frame, with the tip offset TIP_BEYOND_D."""
    m = robot_spec(robot_path).compile()
    d = mujoco.MjData(m)
    d.qpos[[m.jnt_qposadr[m.joint(j).id] for j in bm.ARM_JOINTS]] = HOME_ARM
    d.qpos[[m.jnt_qposadr[m.joint(j).id] for j in bm.GRIPPER_JOINTS]] = calib["theta_at_calib_width_rad"]
    mujoco.mj_kinematics(m, d)
    b = m.body("xarm_gripper_base_link").id
    Rg, p0 = d.xmat[b].reshape(3, 3).copy(), d.xpos[b].copy()
    g2 = m.geom("left_fingertip_p97").id
    tip = float((Rg.T @ (d.geom_xpos[g2] - p0))[2] + m.geom_size[g2, 2])
    if ORIENT == "p04":
        # P-04 coaxial grasp: arm A grips from the D end. D face at the fingertip's proximal end, the fingertip covers
        # D and E (30 mm), and the U layer projects 27 mm beyond the fingertips for arm B.
        zc = tip - 2 * TIP_HALF[2] + half
        Rc = np.column_stack([Rg[:, 1], np.cross(Rg[:, 2], Rg[:, 1]), Rg[:, 2]])  # cube +z = gripper +z (to the tip)
    else:
        # "p2": P2 integration_hold_m2's placement (fingers pass alongside U from the U end; pads at D+E). Not P-04.
        zc = tip - TIP_BEYOND_D - half
        Rc = np.column_stack([Rg[:, 1], np.cross(-Rg[:, 2], Rg[:, 1]), -Rg[:, 2]])  # cube +z = towards the flange
    centre = p0 + Rg @ np.array([0.0, 0.0, zc])
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, Rc.flatten())
    s_ = 1.0 if ORIENT == "p04" else -1.0
    span = sorted([s_ * (tip - zc) * 1e3, s_ * (tip - 2 * TIP_HALF[2] - zc) * 1e3])
    return centre, q, {"orientation": ORIENT, "pad_tip_gripper_z_mm": tip * 1e3, "cube_centre_gripper_z_mm": zc * 1e3,
                       "pad_span_cube_z_mm": [round(v, 2) for v in span]}


def build_scene(robot_path: Path, calib: dict, mu: float):
    p = m7_params()
    half = 1.5 * p.pitch - p.gap / 2
    centre, quat, info = grasp_frame(robot_path, calib, half)
    xml = D13.with_noslip(build_m1_xml(p), E7.NOSLIP)
    tag = '<body name="core" pos="0 0 0">'
    assert xml.count(tag) == 1
    xml = xml.replace(tag, f'<body name="core" pos="{" ".join(f"{v:.9g}" for v in centre)}" '
                           f'quat="{" ".join(f"{v:.9g}" for v in quat)}">\n      <freejoint name="core_free"/>\n'
                           '      <inertial pos="0 0 0" mass="0.0017" diaginertia="2e-8 2e-8 2e-8"/>', 1)
    cube = mujoco.MjSpec.from_string(xml)
    parent = robot_spec(robot_path, mu)
    for k in ("timestep", "integrator", "cone", "impratio", "solver", "iterations", "tolerance", "gravity",
              "noslip_iterations"):
        setattr(parent.option, k, getattr(cube.option, k))
    for key in list(parent.keys):
        parent.delete(key)
    parent.worldbody.add_frame().attach_body(cube.body("core"), "", "")
    m = parent.compile()
    info.update({"cube_centre_world_m": np.round(centre, 5).tolist(), "timestep": m.opt.timestep,
                 "noslip_iterations": int(m.opt.noslip_iterations), "nq": m.nq, "nv": m.nv,
                 "cube_mass_kg": round(float(m.body_subtreemass[m.body("core").id]), 4), "pad_mu": mu,
                 "fingertip_extension_mm": EXT * 1e3})
    return m, p, info


def install_magnets(m, p) -> MagnetSystem:
    mp = R.magnet_params_for({})
    ms = MagnetSystem(m, p.pitch, p.gap, mp, tables=M4._tables_for(mp))
    ms.install()
    return ms


class Scene:
    """The robot + cube model with its sim, readout and the gripper set-up phase (gravity off, ramped close)."""

    def __init__(self, robot_path, calib, F: float, mu: float = 0.8):
        self.m, self.p, self.info = build_scene(robot_path, calib, mu)
        m = self.m
        bm.set_grip_force(m, calib, F)
        self.ms = install_magnets(m, self.p)
        self.sim = AuditedSim(m)
        self.d = d = self.sim.d
        self.ro = CubeReadout(m, self.p.pitch)
        qa = [m.jnt_qposadr[m.joint(j).id] for j in bm.ARM_JOINTS]
        gq = [m.jnt_qposadr[m.joint(j).id] for j in bm.GRIPPER_JOINTS]
        self.gid = m.actuator("gripper").id
        th_open = float(m.actuator_ctrlrange[self.gid, 0])
        d.qpos[qa] = HOME_ARM
        d.qpos[gq] = th_open
        self.sim.log_setup({"kind": "initial robot pose", "arm": HOME_ARM, "gripper_theta": th_open})
        d.ctrl[[m.actuator(f"act{i}").id for i in range(1, 8)]] = HOME_ARM
        d.ctrl[self.gid] = th_open
        mujoco.mj_forward(m, d)
        self.base, self.core = m.body("xarm_gripper_base_link").id, m.body("core").id
        g = m.opt.gravity.copy()
        m.opt.gravity[:] = 0.0
        dt = m.opt.timestep
        for k in range(int(SETUP_S / dt)):
            d.ctrl[self.gid] = min(bm.DRIVE_RANGE[1], th_open + CLOSE_RATE * k * dt)
            self.sim.step(1)
        m.opt.gravity[:] = g
        names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, i) or "" for i in range(m.ngeom)]
        self.pad_ids = np.array([m.geom(n).id for n in FINGERTIPS])
        self.left = {m.geom(FINGERTIPS[0]).id}
        self.cubie = np.array(self.ro.geom_ids)
        robot_root = m.body("link_base").id
        self.robot_geoms = np.array([i for i in range(m.ngeom) if m.body_rootid[m.geom_bodyid[i]] == robot_root
                                     and i not in set(self.pad_ids.tolist())])
        self.names = names

    def rel(self):
        d = self.d
        Rb, pb = d.xmat[self.base].reshape(3, 3), d.xpos[self.base]
        return Rb.T @ (d.xpos[self.core] - pb), Rb.T @ d.xmat[self.core].reshape(3, 3)

    def contacts(self) -> dict:
        """Penetration split, pad normal forces, layers the pads touch, non-pad robot contacts (this step)."""
        m, d = self.m, self.d
        n = d.ncon
        out = {"pen_pad_mm": 0.0, "pen_cubie_mm": 0.0, "fn_left": 0.0, "fn_right": 0.0, "layers": set(),
               "other_robot": 0, "layer_N": {}}
        if not n:
            return out
        g1, g2, dist = d.contact.geom1[:n], d.contact.geom2[:n], d.contact.dist[:n]
        padc = np.isin(g1, self.pad_ids) | np.isin(g2, self.pad_ids)
        cub1, cub2 = np.isin(g1, self.cubie), np.isin(g2, self.cubie)
        cc = cub1 & cub2
        if (padc & (cub1 | cub2)).any():
            out["pen_pad_mm"] = max(0.0, float(-dist[padc & (cub1 | cub2)].min()) * 1e3)
        if cc.any():
            out["pen_cubie_mm"] = max(0.0, float(-dist[cc].min()) * 1e3)
        rob = (np.isin(g1, self.robot_geoms) & cub2) | (np.isin(g2, self.robot_geoms) & cub1)
        out["other_robot"] = int(rob.sum())
        pos, _ = self.ro.poses(d)
        gi = {int(x): i for i, x in enumerate(self.cubie)}
        f6 = np.zeros(6)
        for i in np.nonzero(padc & (cub1 | cub2))[0]:
            mujoco.mj_contactForce(m, d, int(i), f6)
            pg, cg = (int(g1[i]), int(g2[i])) if g1[i] in self.pad_ids else (int(g2[i]), int(g1[i]))
            out["fn_left" if pg in self.left else "fn_right"] += float(f6[0])
            ly = int(np.rint(pos[gi[cg]][2]))
            out["layers"].add(ly)
            out["layer_N"][ly] = out["layer_N"].get(ly, 0.0) + float(f6[0])
        return out

    def tilts(self) -> list[float]:
        """Angle between each fingertip's long axis and the cube's z axis (deg); 0 = flat on the side face."""
        Rc = self.d.xmat[self.core].reshape(3, 3)
        return [float(np.degrees(np.arccos(min(1.0, abs((Rc.T @ self.d.geom_xmat[g].reshape(3, 3))[2, 2])))))
                for g in self.pad_ids]

    def w_max(self) -> float:
        return float(np.degrees(np.linalg.norm(self.d.cvel[self.ro.body_ids, :3], axis=1)).max())


def hold(robot_path, calib, F: float, hold_s: float) -> dict:
    sc = Scene(robot_path, calib, F)
    p0, R0 = sc.rel()
    dt = sc.m.opt.timestep
    rows, w = [], []
    every = int(round(0.01 / dt))
    t0 = time.perf_counter()
    n = int(round(hold_s / dt))
    for k in range(n):
        sc.sim.step(1)
        w.append(sc.w_max())
        if k % every:
            continue
        p, Rr = sc.rel()
        c = sc.contacts()
        rows.append({"t": round(float(sc.d.time), 3), "slip_mm": float(np.linalg.norm(p - p0) * 1e3),
                     "rot_deg": float(np.degrees(np.linalg.norm(Rotation.from_matrix(Rr @ R0.T).as_rotvec()))),
                     **{k2: v for k2, v in c.items() if k2 != "layers"}, "layers": sorted(c["layers"])})
    wall = time.perf_counter() - t0
    a = lambda k2: np.array([r[k2] for r in rows])  # noqa: E731
    res = {"grip_setting_N": F, "hold_s": hold_s, "scene": sc.info,
           "core_slip_mm_max": float(a("slip_mm").max()), "core_slip_mm_final": float(a("slip_mm")[-1]),
           "core_rot_deg_max": float(a("rot_deg").max()),
           "slip_mm_at_s": {f"{t:g}": float(np.interp(t, a("t") - a("t")[0], a("slip_mm"))) for t in (0.5, 1, 2, 3, 5)
                            if t <= hold_s},
           "jitter_w_max_median_dps": float(np.median(w)), "jitter_w_max_p95_dps": float(np.percentile(w, 95)),
           "pen_pad_mm_max": float(a("pen_pad_mm").max()), "pen_cubie_mm_max": float(a("pen_cubie_mm").max()),
           "pad_normal_N_median": [float(np.median(a("fn_left"))), float(np.median(a("fn_right")))],
           "pad_normal_N_min": [float(a("fn_left").min()), float(a("fn_right").min())],
           "fingertip_tilt_deg_end": sc.tilts(),
           "layers_touched": sorted({ly for r in rows for ly in r["layers"]}),
           "layer_N_median": {str(ly): float(np.median([r["layer_N"].get(ly, 0.0) for r in rows]))
                              for ly in (-1, 0, 1)},
           "non_pad_robot_contacts_max": int(a("other_robot").max()),
           "audit_violations": sc.sim.violations, "numerical_failures": sc.sim.numerical_failures,
           "steps_per_s": n / wall, "series": rows[::10]}
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hold", type=float, default=5.0)
    ap.add_argument("--forces", default="10,20,30,50")
    ap.add_argument("--ext-mm", type=float, default=0.0)
    ap.add_argument("--tip-solref", type=float, default=None, help="fingertip contact timeconst (s)")
    ap.add_argument("--orient", default="p04", choices=("p04", "p2"))
    ap.add_argument("--eq-solref", type=float, default=None, help="gripper four-bar equality timeconst (s)")
    a = ap.parse_args()
    global EXT, TIP_SOLREF, EQ_SOLREF, ORIENT
    ORIENT = a.orient
    EQ_SOLREF = a.eq_solref
    EXT = a.ext_mm / 1000
    TIP_SOLREF = None if a.tip_solref is None else (a.tip_solref, 1.0)
    robot_path, calib = bm.build("1305+", True)
    OUT.mkdir(exist_ok=True)
    for F in [float(x) for x in a.forces.split(",")]:
        r = hold(robot_path, calib, F, a.hold)
        (OUT / f"hold_{a.orient}_F{F:g}_ext{a.ext_mm:g}_sr{a.tip_solref or 0.001:g}_eq{a.eq_solref or 0.005:g}.json").write_text(json.dumps(r, indent=1, default=float))
        print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()
                          if k not in ("series", "scene")}), flush=True)


if __name__ == "__main__":
    main()
