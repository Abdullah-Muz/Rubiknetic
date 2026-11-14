"""D3 — UNSCORED prototype of "M3": real-cube retention built from the user-supplied CAD.

Model (see docs/research/CUBE_MECHANISM_FINDINGS.md section 4):
  * core fixed to the world (as P-09);
  * 6 centres: hinge about the face axis plus a spring-loaded radial slide (the real
    screw and spring); centre-core contact excluded (the cap is mounted on the arm);
  * 12 edges and 8 corners: FREE bodies (6 DOF each), held only by contact with the
    interlocking feet. There is no joint and no per-cubie spring.
Geometry: CoACD convex hulls of the CAD (third_party_cad/, git-ignored, GrabCAD terms).
Masses (ASSUMPTION, from the Paulus 2023 teardown BOM): corner 3.9 g, edge 2.6 g, centre 2.3 g.
Centre spring (ASSUMPTION, no published data): preload 3 N, 500 N/m.

Modes:
  check   static interference at the CAD pose (contacts with dist<0 between pieces)
  rest    3 s settle under gravity: observe, drift, penetration, contacts, steps/s
  twist   D1/D2 torque staircase on corner ppp (logged test wrench)
  turn    90-degree turns of U and R, driven by a position actuator on the centre hinge
          (contact-driven via the centre cap, not by the M1 pad rig)
Usage (WSL2, repo root): uv run python experiments/D3_m3_prototype/run.py <mode> [key=value ...]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation

from rubiknetic.cube_logic import Move
from rubiknetic.cube_logic.geometric import HOME_POSITIONS
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES
from rubiknetic.cube_physics.m1_model import cubie_name
from rubiknetic.cube_physics.readout import CubeReadout
from rubiknetic.cube_physics.rig import AuditedSim, EditAuditError, NumericalFailure

REPO = Path(__file__).resolve().parents[2]
HULLS = REPO / "third_party_cad" / "m3_hulls_t0.03.json"
OUT = Path(__file__).parent / "results"
PITCH = 0.019

CFG = {
    "hulls": str(HULLS), "shrink_mm": 0.0, "radial_in_mm": 0.0, "maxhullvert": 0, "timestep": 0.0005, "iterations": 100,
    "friction": 0.2, "solref": 0.001, "solimp": (0.99, 0.999, 0.0005),
    "mass_corner": 0.0039, "mass_edge": 0.0026, "mass_centre": 0.0023,
    "spring_preload": 3.0, "spring_k": 500.0, "slide_range": (-0.001, 0.003),
    "hinge_damping": 0.0005, "hinge_frictionloss": 0.0005, "turn_kp": 5.0, "turn_kv": 0.2, "turn_torque": 1.0,
}


def _fmt(v) -> str:
    return " ".join(f"{float(x):.9g}" for x in np.ravel(v))


def _shrink(v: np.ndarray, mm: float, radial_in_mm: float = 0.0, centre: np.ndarray | None = None) -> np.ndarray:
    """Exact inward offset of a convex hull: every face plane moves inward by `mm`. In addition,
    faces that face the cube centre (outward normal within ~45 deg of pointing at `centre`) move
    inward by `radial_in_mm`. This removes the sagitta bulge of flat hull faces over the concave
    spherical bearing surfaces. Hulls too thin to survive are scaled to 50 % about their centroid."""
    if mm <= 0 and radial_in_mm <= 0:
        return v
    from scipy.spatial import HalfspaceIntersection
    hull = ConvexHull(v)
    eq = hull.equations.copy()  # n.x + c <= 0 inside
    eq[:, 3] += mm / 1000
    if radial_in_mm > 0 and centre is not None:
        u = v.mean(0) - centre
        u /= np.linalg.norm(u)
        eq[eq[:, :3] @ u < -0.7, 3] += radial_in_mm / 1000
    c = v.mean(0)
    if np.all(eq[:, :3] @ c + eq[:, 3] < -1e-9):
        try:
            return HalfspaceIntersection(eq, c).intersections
        except Exception:
            pass
    return c + (v - c) * 0.5


def build_xml(cfg: dict) -> str:
    data = json.loads(Path(cfg["hulls"]).read_text())
    assets, bodies, excludes, actuators = [], [], [], []
    vol = {}
    for kind, hl in data["hulls"].items():
        vol[kind] = 0.0
        T0 = np.array(next(i for i in data["instances"] if i["kind"] == kind)["T"])
        centre_local = -T0[:3, :3].T @ T0[:3, 3]  # cube centre in this part's local frame
        rin = cfg["radial_in_mm"] if kind in ("edge", "corner", "centre") else 0.0
        for i, h in enumerate(hl):
            v = _shrink(np.array(h["v"]), cfg["shrink_mm"], rin, centre_local)
            vol[kind] += ConvexHull(v).volume
            mhv = f' maxhullvert="{cfg["maxhullvert"]}"' if cfg["maxhullvert"] else ""
            assets.append(f'    <mesh name="{kind}_{i}"{mhv} vertex="{_fmt(v)}"/>')
    dens = {"corner": cfg["mass_corner"] / vol["corner"], "edge": cfg["mass_edge"] / vol["edge"],
            "centre": cfg["mass_centre"] / vol["centre"], "core": 1000.0}

    def geoms(kind: str, T: np.ndarray, origin: np.ndarray) -> list[str]:
        q = Rotation.from_matrix(T[:3, :3]).as_quat()  # x y z w
        return [f'        <geom class="piece" mesh="{kind}_{i}" density="{dens[kind]:.6g}" '
                f'pos="{_fmt(T[:3, 3] - origin)}" quat="{_fmt([q[3], q[0], q[1], q[2]])}"/>'
                for i in range(len(data["hulls"][kind]))]

    by_home = {tuple(i["home"]): i for i in data["instances"] if i["kind"] != "core"}
    core = next(i for i in data["instances"] if i["kind"] == "core")
    bodies.append('    <body name="core">\n' + "\n".join(geoms("core", np.array(core["T"]), np.zeros(3))) + "\n    </body>")
    for h in HOME_POSITIONS:
        inst = by_home[tuple(h)]
        T = np.array(inst["T"])
        name = cubie_name(h)
        home = np.array(h, float) * PITCH
        marker = f'        <geom name="{name}_g" type="sphere" size="0.001" contype="0" conaffinity="0" group="5" mass="0" pos="{_fmt(home if inst["kind"] == "centre" else np.zeros(3))}"/>'
        if inst["kind"] == "centre":
            ax = np.array(h, float)
            joints = (f'        <joint name="{name}_j" type="hinge" axis="{_fmt(ax)}" damping="{cfg["hinge_damping"]}" '
                      f'frictionloss="{cfg["hinge_frictionloss"]}" armature="1e-6"/>\n'
                      f'        <joint name="{name}_r" type="slide" axis="{_fmt(ax)}" range="{_fmt(cfg["slide_range"])}" '
                      f'stiffness="{cfg["spring_k"]}" springref="{-cfg["spring_preload"] / cfg["spring_k"]:.9g}" '
                      f'damping="0.05" armature="1e-6" solreflimit="0.001 1" solimplimit="0.99 0.999 0.0005"/>')
            bodies.append(f'    <body name="{name}" pos="0 0 0">\n{joints}\n{marker}\n'
                          + "\n".join(geoms("centre", T, np.zeros(3))) + "\n    </body>")
            excludes.append(f'    <exclude body1="core" body2="{name}"/>')
            actuators.append(f'    <position name="turn_{name}" joint="{name}_j" kp="{cfg["turn_kp"]}" kv="{cfg["turn_kv"]}" '
                             f'forcerange="{-cfg["turn_torque"]} {cfg["turn_torque"]}"/>')
        else:
            bodies.append(f'    <body name="{name}" pos="{_fmt(home)}">\n        <freejoint name="{name}_free"/>\n{marker}\n'
                          + "\n".join(geoms(inst["kind"], T, home)) + "\n    </body>")
    si = _fmt(cfg["solimp"])
    return f"""<mujoco model="rubiknetic_m3_prototype">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="{cfg['timestep']}" integrator="implicitfast" cone="elliptic" impratio="10"
          solver="Newton" iterations="{cfg['iterations']}" tolerance="1e-10" gravity="0 0 -9.81"/>
  <size memory="200M"/>
  <default>
    <default class="piece">
      <geom type="mesh" condim="3" friction="{cfg['friction']} 0.0025 0.0005" solref="{cfg['solref']} 1" solimp="{si}"/>
    </default>
  </default>
  <asset>
{chr(10).join(assets)}
  </asset>
  <worldbody>
{chr(10).join(bodies)}
  </worldbody>
  <contact>
{chr(10).join(excludes)}
  </contact>
  <actuator>
{chr(10).join(actuators)}
  </actuator>
</mujoco>
"""


def make(cfg: dict):
    m = mujoco.MjModel.from_xml_string(build_xml(cfg))
    sim = AuditedSim(m, allow_test_wrench=True)
    mujoco.mj_forward(m, sim.d)  # kinematics only (no state change), so poses are valid before step 1
    return m, sim, CubeReadout(m, PITCH)


def piece_contacts(m, d):
    """(dist, body1, body2) for contacts between different pieces."""
    out = []
    for i in range(d.ncon):
        c = d.contact[i]
        b1, b2 = m.geom_bodyid[c.geom1], m.geom_bodyid[c.geom2]
        out.append((c.dist, mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b1),
                    mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b2)))
    return out


def mode_check(cfg):
    m, sim, ro = make(cfg)
    d = sim.d
    mujoco.mj_forward(m, d)
    pc = piece_contacts(m, d)
    pen = sorted(pc)[:8]
    print(f"geoms {m.ngeom}  bodies {m.nbody}  nv {m.nv}  contacts at CAD pose {d.ncon}")
    print(f"interfering (dist<0): {sum(x[0] < 0 for x in pc)}, worst {[(round(-a * 1000, 3), b, c) for a, b, c in pen[:5]]} (mm)")
    print("observe at CAD pose:", ro.observe(d).valid, "masses", np.round(m.body_mass * 1000, 2)[1:6], "g")
    return {"ncon": d.ncon, "worst_pen_mm": -min(x[0] for x in pc) * 1000 if pc else 0}


def mode_rest(cfg, secs=3.0):
    m, sim, ro = make(cfg)
    d = sim.d
    pos0, rot0 = ro.poses(d)
    t = time.perf_counter()
    try:
        sim.step(int(secs / m.opt.timestep))
    except NumericalFailure as e:
        print("NUMERICAL FAILURE", e)
        return
    el = time.perf_counter() - t
    pos, rot = ro.poses(d)
    obs = ro.observe(d)
    drift = max(np.degrees(np.linalg.norm(Rotation.from_matrix(rot[i] @ rot0[i].T).as_rotvec())) for i in range(26))
    pc = piece_contacts(m, d)
    print(f"rest {secs}s: observed valid {obs.valid} solved-pose drift max {drift:.3f} deg, max pos change "
          f"{np.abs(pos - pos0).max() * PITCH * 1000:.3f} mm, contacts {d.ncon}, max pen "
          f"{-min(x[0] for x in pc) * 1000 if pc else 0:.3f} mm, {secs / m.opt.timestep / el:.0f} steps/s "
          f"(RTF {secs / el:.2f})")
    slides = {cubie_name(h): round(float(d.qpos[m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, cubie_name(h) + '_r')]]) * 1000, 3)
              for h in HOME_POSITIONS if np.count_nonzero(h) == 1}
    print("centre slide positions (mm, + = outward):", slides)


def mode_twist(cfg):
    m, sim, ro = make(cfg)
    d = sim.d
    sim.step(int(0.5 / m.opt.timestep))
    idx = HOME_POSITIONS.index((1, 1, 1))
    body = int(ro.body_ids[idx])
    axis = np.ones(3) / np.sqrt(3)
    _, rot0 = ro.poses(d)
    pos0, _ = ro.poses(d)
    dt = m.opt.timestep
    prev = 0.0
    try:
        for lvl in [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]:
            n_r, n_h = int(0.05 / dt), int(0.25 / dt)
            minpen = 0.0
            for k in range(n_r + n_h):
                tau = prev + (lvl - prev) * min(1.0, (k + 1) / n_r)
                sim.set_test_wrench(body, np.concatenate([np.zeros(3), tau * axis]))
                sim.step()
                if d.ncon:
                    minpen = min(minpen, float(d.contact.dist[:d.ncon].min()))
            pos, rot = ro.poses(d)
            rv = Rotation.from_matrix(rot[idx] @ rot0[idx].T).as_rotvec()
            nbr = max(np.degrees(np.linalg.norm(Rotation.from_matrix(rot[i] @ rot0[i].T).as_rotvec()))
                      for i in range(26) if i != idx)
            print(f"  {lvl:6.3f} N.m twist {np.degrees(rv @ axis):7.2f} deg  corner moved {np.linalg.norm(pos[idx] - pos0[idx]) * PITCH * 1000:.3f} mm"
                  f"  max neighbour rot {nbr:.2f} deg  pen {-minpen * 1000:.3f} mm")
            prev = lvl
        sim.set_test_wrench(body, np.zeros(6))
        sim.step(int(0.5 / dt))
        _, rot = ro.poses(d)
        print(f"  released: twist {np.degrees(Rotation.from_matrix(rot[idx] @ rot0[idx].T).as_rotvec() @ axis):.2f} deg, observed valid {ro.observe(d).valid}")
    except (NumericalFailure, EditAuditError) as e:
        print("ABORT", e)


def mode_turn(cfg):
    m, sim, ro = make(cfg)
    d = sim.d
    dt = m.opt.timestep
    sim.step(int(0.3 / dt))
    t = time.perf_counter()
    nsteps = 0
    for face in ("U", "R"):
        h = tuple(int(x) for x in FACE_NORMAL[face])
        name = cubie_name(h)
        aid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, f"turn_{name}")
        q0 = float(d.ctrl[aid])
        _, rot0 = ro.poses(d)
        members = ro.layer_members(d, face)
        try:
            for k in range(int(1.0 / dt)):  # CW quarter turn = -90 deg about the outward normal
                d.ctrl[aid] = q0 - np.pi / 2 * (k + 1) / int(1.0 / dt)
                sim.step()
            sim.step(int(0.5 / dt))
            nsteps += int(1.5 / dt)
        except (NumericalFailure, EditAuditError) as e:
            print(face, "ABORT", e)
            return
        _, rot = ro.poses(d)
        ang = CubeReadout.rotation_about_deg(rot0, rot, members, face)
        others = [i for i in range(26) if i not in members]
        other_ang = CubeReadout.rotation_about_deg(rot0, rot, others, face)
        obs = ro.observe(d)
        print(f"{face}: layer rotation mean {np.mean(ang):+.2f} (min {np.min(ang):+.2f}, max {np.max(ang):+.2f}) deg; "
              f"non-layer max {np.max(np.abs(other_ang)):.2f} deg; observed valid {obs.valid}"
              f"{'' if not obs.valid else ''}; contacts {d.ncon}")
    el = time.perf_counter() - t
    print(f"turn throughput {nsteps / el:.0f} steps/s")
    from rubiknetic.cube_logic import CubieCube, parse  # oracle check
    obs = ro.observe(d)
    if obs.valid:
        exp = CubieCube.from_moves(parse("U R")) if hasattr(CubieCube, "from_moves") else None
        print("final observed state matches oracle 'U R':", None if exp is None else obs.state == exp)


if __name__ == "__main__":
    mode = sys.argv[1]
    cfg = dict(CFG)
    for kv in sys.argv[2:]:
        k, v = kv.split("=")
        cfg[k] = type(CFG[k])(v) if not isinstance(CFG[k], tuple) else tuple(float(x) for x in v.split(","))
    {"check": mode_check, "rest": mode_rest, "twist": mode_twist, "turn": mode_turn}[mode](cfg)
