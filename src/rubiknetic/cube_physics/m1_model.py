"""M1 cube model: contact-emergent topology (approved interpretation of D-05, P-01).

Abstraction (documented; see docs/research/CUBE_MECHANICS_LITERATURE_REVIEW.md §6):

* 26 visible cubies. Every corner/edge cubie is a body whose frame sits at the
  cube centre and carries a **ball joint** there; centre cubies carry one
  **hinge** about their face normal. This represents the real core/retention
  mechanism as "each cubie is retained at fixed radius and may only rotate
  about the cube centre" (precedent: OpenAI 2019 §4.2 used 3 hinges per
  cubie; a ball joint is the singularity-free equivalent).
* Which cubies move together is **not** declared anywhere. It emerges from
  convex bevelled cubie geometry in contact with its neighbours. No
  constraint is switched at runtime and nothing writes cubie state.
* Test rig v0 (Phase 1 only): the core is fixed to the world (a cube mounted on a
  fixed axle). Six "turners" -- one per face, each a hinge about the face
  normal plus two opposed sliding pads -- are the only external actuators.
  They act on cubies purely through contact, with force- and torque-limited
  position servos (physical actuator limits, not state edits).

All numeric values are ASSUMPTIONS / calibration parameters, not measured
properties of a real cube. Defaults are the E1-0 nominal candidate (config
c21, experiments/E1-0_calibration/README.md); the original pre-calibration
values are recorded there.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
from scipy.spatial.transform import Rotation

from rubiknetic.cube_logic.geometric import HOME_POSITIONS
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES

# Pad closing direction t1 for each face's turner (pads sit on +-t1 sides of the layer).
PAD_AXIS: dict[str, tuple[int, int, int]] = {
    "U": (0, 1, 0), "D": (0, 1, 0),
    "R": (0, 0, 1), "L": (0, 0, 1),
    "F": (1, 0, 0), "B": (1, 0, 0),
}


@dataclass
class M1Params:
    # --- geometry (ASSUMPTION: 57 mm cube, 19 mm pitch; Phase 0 OpenAI reference) ---
    pitch: float = 0.019
    gap: float = 0.0002          # clearance between neighbouring cubie faces
    chamfer: float = 0.0014      # edge bevel (OpenAI used 1.425 mm on 19 mm cubies)
    cubie_mass: float = 0.0034   # 26 x 3.4 g ~= 88 g (ASSUMPTION)
    # --- cubie-cubie contact ---
    cubie_friction: tuple[float, float, float] = (0.2, 0.0025, 0.0005)
    cubie_condim: int = 3
    cubie_solref: tuple[float, float] = (0.001, 1.0)
    cubie_solimp: tuple[float, float, float] = (0.95, 0.99, 0.0005)
    # --- retention-joint dissipation (turn resistance source #2) ---
    joint_damping: float = 0.0005
    joint_frictionloss: float = 0.0005
    joint_armature: float = 1e-6
    # --- radial retention preload (OpenAI robogym precedent: spring-loaded radial
    # slide per cubelet). 0 disables the slide joint entirely (rigid-radius M1).
    radial_preload: float = 1.0       # N pulling each corner/edge cubie toward the core
    radial_stiffness: float = 500.0   # N/m
    radial_range: tuple[float, float] = (-0.001, 0.0002)  # m, inward negative
    radial_damping: float = 0.05      # N s/m
    radial_solreflimit: tuple[float, float] = (0.001, 1.0)  # retention stop as stiff as contacts
    radial_solimplimit: tuple[float, float, float] = (0.95, 0.99, 0.0005)
    # --- test rig ---
    rig: bool = True
    pad_thickness: float = 0.005
    pad_width: float = 0.045     # along t2 (tangent to the face, perpendicular to pad axis)
    pad_height: float = 0.010    # along the face normal; layer is 19 mm thick
    pad_open_clearance: float = 0.014  # idle pads clear the 40 mm corner sweep radius
    grip_overshoot: float = 0.006   # closing target beyond first contact (force saturates)
    pad_slide_damping: float = 100.0  # N s/m; limits closing speed
    pad_friction: tuple[float, float, float] = (0.8, 0.005, 0.0001)
    pad_condim: int = 4
    pad_solref: tuple[float, float] = (0.001, 1.0)
    pad_solimp: tuple[float, float, float] = (0.95, 0.99, 0.0005)
    grip_force: float = 10.0     # N per pad (G2 range 10-50 N)
    grip_kp: float = 2000.0
    turn_torque_limit: float = 1.0  # N m
    turn_kp: float = 5.0
    turn_kv: float = 0.2
    rig_mass: float = 0.05
    # --- solver ---
    timestep: float = 0.0005
    gravity_z: float = -9.81
    integrator: str = "implicitfast"
    cone: str = "elliptic"
    impratio: float = 10.0
    solver: str = "Newton"
    iterations: int = 100
    tolerance: float = 1e-10
    # --- piece edge shape (P-79, 2026-11-24). "chamfer": 45 deg bevel of `chamfer` on every edge (the original B1
    # geometry; default). "rounded": edges and corners rounded at `edge_radius` (m) as a faceted fillet with 30 deg
    # facet steps, so the first facet meets each face at 15 deg; half-size and gap unchanged. Both fields are left out
    # of record params while they hold their defaults, so chamfer records stay byte-identical (params_record).
    edge_profile: str = "chamfer"
    edge_radius: float = 0.0
    extra: dict = field(default_factory=dict)


EDGE_DEFAULTS = {"edge_profile": "chamfer", "edge_radius": 0.0}


def params_record(p: "M1Params") -> dict:
    """Params as written into trial records: every field except `extra`, and the edge fields only when they differ
    from their defaults (so records of the original chamfer geometry are unchanged by P-79)."""
    return {k: v for k, v in asdict(p).items()
            if k != "extra" and not (k in EDGE_DEFAULTS and v == EDGE_DEFAULTS[k])}


def _fmt(v) -> str:
    return " ".join(f"{float(x):.9g}" for x in np.ravel(v))


def _chamfered_box_vertices(h: float, c: float) -> np.ndarray:
    pts = []
    for axis in range(3):
        for s0 in (-1, 1):
            for s1 in (-1, 1):
                for s2 in (-1, 1):
                    p = np.array([s1 * (h - c), s2 * (h - c), 0.0])
                    p = np.insert(p[:2], axis, s0 * h)
                    pts.append(p)
    return np.array(pts)


ROUNDED_FACET_STEPS_DEG = (0.0, 30.0, 60.0, 90.0)


def _rounded_box_vertices(h: float, r: float) -> np.ndarray:
    """Faceted rounded box: half-size h, edge/corner radius r. Points s*(h-r) + r*s*u for every octant s and every
    direction u on a 30 deg polar/azimuth grid; the convex hull's first fillet facet meets each face at 15 deg.
    Identical to the D14 diagnostic geometry (experiments/D14_noslip_rest_rehearsal/diag_catch/edge_patch.py)."""
    if not 0.0 < r < h:
        raise ValueError(f"edge_radius must be in (0, half-size {h}); got {r}")
    dirs = set()
    for th in np.radians(ROUNDED_FACET_STEPS_DEG):
        for ph in np.radians(ROUNDED_FACET_STEPS_DEG):
            u = (np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th))
            dirs.add(tuple(round(x, 12) for x in u))
    pts = set()
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                s = np.array([sx, sy, sz], float)
                for u in dirs:
                    pts.add(tuple(round(x, 12) for x in s * (h - r) + r * s * np.array(u)))
    return np.array(sorted(pts))


def piece_vertices(p: "M1Params") -> np.ndarray:
    h = (p.pitch - p.gap) / 2
    if p.edge_profile == "chamfer":
        return _chamfered_box_vertices(h, p.chamfer)
    if p.edge_profile == "rounded":
        return _rounded_box_vertices(h, p.edge_radius)
    raise ValueError(f"unknown edge_profile {p.edge_profile!r}")


def cubie_name(home: tuple[int, int, int]) -> str:
    def c(v):
        return {-1: "n", 0: "0", 1: "p"}[v]
    return "cubie_" + "".join(c(v) for v in home)


def _face_frame_quat(face: str) -> np.ndarray:
    n = np.array(FACE_NORMAL[face], float)
    t1 = np.array(PAD_AXIS[face], float)
    t2 = np.cross(n, t1)
    m = np.column_stack([t1, t2, n])
    x, y, z, w = Rotation.from_matrix(m).as_quat()
    return np.array([w, x, y, z])


def build_m1_xml(p: M1Params | None = None) -> str:
    p = p or M1Params()
    h = (p.pitch - p.gap) / 2
    half_cube = 1.5 * p.pitch - p.gap / 2
    verts = piece_vertices(p)

    cubies = []
    for home in HOME_POSITIONS:
        name = cubie_name(home)
        nz = int(np.count_nonzero(home))
        if nz == 1:
            joint = (f'<joint name="{name}_j" type="hinge" axis="{_fmt(home)}" '
                     f'damping="{p.joint_damping}" frictionloss="{p.joint_frictionloss}" '
                     f'armature="{p.joint_armature}"/>')
        else:
            joint = (f'<joint name="{name}_j" type="ball" damping="{p.joint_damping}" '
                     f'frictionloss="{p.joint_frictionloss}" armature="{p.joint_armature}"/>')
            if p.radial_preload > 0:
                u = np.array(home, float) / np.linalg.norm(home)
                joint += (f'\n        <joint name="{name}_r" type="slide" axis="{_fmt(u)}" '
                          f'range="{_fmt(p.radial_range)}" stiffness="{p.radial_stiffness}" '
                          f'springref="{-p.radial_preload / p.radial_stiffness:.9g}" '
                          f'damping="{p.radial_damping}" armature="{p.joint_armature}" '
                          f'solreflimit="{_fmt(p.radial_solreflimit)}" solimplimit="{_fmt(p.radial_solimplimit)}"/>')
        cubies.append(
            f'      <body name="{name}" pos="0 0 0">\n'
            f"        {joint}\n"
            f'        <geom name="{name}_g" class="cubie" pos="{_fmt(np.array(home) * p.pitch)}"/>\n'
            f"      </body>"
        )

    rigs = []
    actuators = []
    if p.rig:
        open_off = half_cube + p.pad_open_clearance + p.pad_thickness / 2
        for f in FACES:
            q = _face_frame_quat(f)
            pads = []
            for side, s in (("a", -1), ("b", 1)):
                pads.append(
                    f'        <body name="pad_{f}{side}" pos="{_fmt([s * open_off, 0, p.pitch])}">\n'
                    f'          <joint name="pad_{f}{side}_slide" type="slide" axis="{s} 0 0" '
                    f'range="-0.05 0.001" damping="{p.pad_slide_damping}"/>\n'
                    f'          <geom name="pad_{f}{side}_g" class="pad"/>\n'
                    f"        </body>"
                )
                actuators.append(
                    f'    <position name="grip_{f}{side}" joint="pad_{f}{side}_slide" kp="{p.grip_kp}" '
                    f'forcerange="{-p.grip_force} {p.grip_force}" ctrlrange="-0.05 0.001"/>'
                )
            rigs.append(
                f'    <body name="turner_{f}" pos="0 0 0" quat="{_fmt(q)}" gravcomp="1">\n'
                f'      <joint name="turner_{f}_hinge" type="hinge" axis="0 0 1" damping="0.01"/>\n'
                f'      <inertial pos="0 0 {p.pitch}" mass="{p.rig_mass}" diaginertia="1e-5 1e-5 1e-5"/>\n'
                + "\n".join(pads) + "\n"
                f"    </body>"
            )
            actuators.append(
                f'    <position name="turn_{f}" joint="turner_{f}_hinge" kp="{p.turn_kp}" '
                f'kv="{p.turn_kv}" forcerange="{-p.turn_torque_limit} {p.turn_torque_limit}"/>'
            )

    pad_half = [p.pad_thickness / 2, p.pad_width / 2, p.pad_height / 2]
    return f"""<mujoco model="rubiknetic_m1">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="{p.timestep}" integrator="{p.integrator}" cone="{p.cone}"
          impratio="{p.impratio}" solver="{p.solver}" iterations="{p.iterations}"
          tolerance="{p.tolerance}" gravity="0 0 {p.gravity_z}"/>
  <asset>
    <mesh name="cubelet" vertex="{_fmt(verts)}"/>
  </asset>
  <default>
    <default class="cubie">
      <geom type="mesh" mesh="cubelet" mass="{p.cubie_mass}" contype="1" conaffinity="3"
            condim="{p.cubie_condim}" friction="{_fmt(p.cubie_friction)}"
            solref="{_fmt(p.cubie_solref)}" solimp="{_fmt(p.cubie_solimp)}" rgba="0.15 0.15 0.15 1"/>
    </default>
    <default class="pad">
      <geom type="box" size="{_fmt(pad_half)}" contype="2" conaffinity="0" condim="{p.pad_condim}"
            friction="{_fmt(p.pad_friction)}" solref="{_fmt(p.pad_solref)}" solimp="{_fmt(p.pad_solimp)}"
            mass="0.005" rgba="0.9 0.5 0.1 1"/>
    </default>
  </default>
  <worldbody>
    <body name="core" pos="0 0 0">
{chr(10).join(cubies)}
    </body>
{chr(10).join(rigs)}
  </worldbody>
  <actuator>
{chr(10).join(actuators)}
  </actuator>
</mujoco>
"""
