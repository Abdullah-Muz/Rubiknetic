"""D5 — our own convex-only cube mechanism ("two-grid + tangent pads"), UNSCORED design study.

Geometry principle (derived from the reference CAD's layout; no CAD geometry is used):
  * Outside the bearing sphere (r >= RS) pieces are bounded by the outer cut planes |x|,|y|,|z| = A.
  * Inside it, the feet are bounded by inner planes |x|,|y|,|z| = S (S < A).
  * Each piece = its outer cell (outside the sphere) + its inner cell (inside the sphere). Where the
    two grids disagree, one piece's foot lies under another piece's body, across the sphere. That
    is the capture.
  * Every interface is a plane except the sphere. The foot side of the sphere is convex (exact). The
    concave body side is replaced by flat pads TANGENT to the sphere: each pad touches a foot at one
    fixed point, which stays fixed as the foot slides around the sphere during a turn.
All geoms are convex: feet = box ∩ ball, bodies = boxes, pads = box ∩ cone ∩ halfspace.
Units: metres in the MJCF; parameters in mm.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
from scipy.optimize import linprog
from scipy.spatial import HalfspaceIntersection

from rubiknetic.cube_logic.geometric import HOME_POSITIONS
from rubiknetic.cube_physics.m1_model import cubie_name


@dataclass
class D5Params:
    pitch: float = 19.0      # mm
    H: float = 28.4          # outer half-size (1.5*pitch - gap/2)
    A: float = 9.5           # outer cut planes
    S: float = 4.8           # inner (feet) planes (reference CAD: feet stop ~12 deg from face axes at r~23)
    RS: float = 25.0         # bearing sphere radius (reference CAD: interface at r ~ 24.94/24.99)
    gap: float = 0.2         # gap across every cut plane
    clearance: float = 0.05  # radial clearance pad-to-foot at the tangent points
    pad_spacing_deg: float = 10.0
    sphere_spacing_mm: float = 1.0
    bevel_body: float = 0.0  # 45-deg bevel leg on outer-body edges (mm)
    bevel_foot: float = 0.0  # 45-deg bevel leg on foot edges (mm)
    # dynamics (for later stages)
    mass_corner: float = 0.0039
    mass_edge: float = 0.0026
    mass_centre: float = 0.0023
    friction: float = 0.2
    solref: tuple = (0.001, 1.0)
    solimp: tuple = (0.99, 0.999, 0.0005)
    timestep: float = 0.0005
    spring_preload: float = 3.0
    spring_k: float = 500.0
    slide_range: tuple = (-0.001, 0.003)  # m; centre radial travel (inward, outward)
    turn_kp: float = 5.0
    bevel_inner: float = 0.0       # bevel on inner-grid (+/-S) faces of own-beneath body boxes, inside the sphere
    inner_split_centre: float = 24.0
    inner_split_edge: float = 22.0
    taper: float = 0.0        # slope of cone-like ramps on inner-plane faces near the sphere (0 = off)
    taper_start: float = 19.0  # distance along the piece axis where the taper begins (mm)
    turn_torque: float = 1.0
    margin: float = 0.0      # geom margin (m); >0 only for kinematic distance queries
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------- convex helpers
def _polytope(hs: np.ndarray) -> np.ndarray | None:
    """Vertices of {x : hs[:, :3] @ x + hs[:, 3] <= 0}, or None if empty or degenerate."""
    A, b = hs[:, :3], -hs[:, 3]
    norm = np.linalg.norm(A, axis=1)
    res = linprog(c=[0, 0, 0, -1], A_ub=np.hstack([A, norm[:, None]]), b_ub=b,
                  bounds=[(None, None)] * 3 + [(0, None)], method="highs")
    if not res.success or res.x[3] < 1e-4:
        return None
    return HalfspaceIntersection(hs, res.x[:3]).intersections


def _box_hs(lo, hi) -> list:
    hs = []
    for i in range(3):
        e = np.zeros(3)
        e[i] = 1
        hs.append([*e, -hi[i]])
        hs.append([*(-e), lo[i]])
    return hs


def _fib_dirs(n: int) -> np.ndarray:
    k = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * k / n)
    th = np.pi * (1 + 5 ** 0.5) * k
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)


def _ball_box_points(lo, hi, R: float, spacing: float) -> np.ndarray:
    """Points whose convex hull is box ∩ ball(R), approximated from inside: box vertices inside
    the ball, sphere points inside the box, and box-edge/sphere intersections."""
    pts = []
    for c in np.array(np.meshgrid(*zip(lo, hi))).T.reshape(-1, 3):
        if np.linalg.norm(c) <= R:
            pts.append(c)
    n = int(4 * np.pi * R ** 2 / spacing ** 2)
    sp = _fib_dirs(n) * R
    inside = np.all((sp >= np.array(lo) - 1e-9) & (sp <= np.array(hi) + 1e-9), axis=1)
    pts += list(sp[inside])
    # box faces ∩ sphere (circle arcs) and box edges ∩ sphere
    for i in range(3):
        for val in (lo[i], hi[i]):
            rr = R ** 2 - val ** 2
            if rr <= 0:
                continue
            rho = np.sqrt(rr)
            j, k = [a for a in range(3) if a != i]
            for t in np.linspace(0, 2 * np.pi, int(2 * np.pi * rho / spacing) + 8, endpoint=False):
                p = np.zeros(3)
                p[i], p[j], p[k] = val, rho * np.cos(t), rho * np.sin(t)
                if lo[j] - 1e-9 <= p[j] <= hi[j] + 1e-9 and lo[k] - 1e-9 <= p[k] <= hi[k] + 1e-9:
                    pts.append(p)
    return np.array(pts)


# ---------------------------------------------------------------------------- cell extents
def _range(sign: int, half: float, gap: float, outer: float) -> tuple[float, float]:
    if sign > 0:
        return half + gap / 2, outer
    if sign < 0:
        return -outer, -(half + gap / 2)
    return -(half - gap / 2), half - gap / 2


def _bevel_hs(lo, hi, c: float, real_faces) -> list:
    """45-degree bevels of leg c on box edges where BOTH adjacent faces are real faces.
    real_faces[i] = (lo_is_real, hi_is_real) for axis i."""
    hs = []
    if c <= 0:
        return hs
    for i in range(3):
        for j in range(i + 1, 3):
            for si, bi, ri in ((-1, lo[i], real_faces[i][0]), (1, hi[i], real_faces[i][1])):
                for sj, bj, rj in ((-1, lo[j], real_faces[j][0]), (1, hi[j], real_faces[j][1])):
                    if ri and rj:
                        n = np.zeros(3)
                        n[i], n[j] = si, sj
                        hs.append([*n, -(si * bi + sj * bj - c)])
    return hs


def _convex_points(hs: list, R: float | None, spacing: float) -> np.ndarray | None:
    """Vertex set whose hull is {hs} (optionally ∩ ball(R), approximated from inside the ball)."""
    hs = np.array(hs, float)
    V = _polytope(hs)
    if V is None:
        return None
    if R is None or np.all(np.linalg.norm(V, axis=1) <= R):
        return V
    pts = [v for v in V if np.linalg.norm(v) <= R]
    ok = lambda P: np.all(P @ hs[:, :3].T + hs[:, 3] <= 1e-7, axis=1)  # noqa: E731
    sp = _fib_dirs(int(4 * np.pi * R ** 2 / spacing ** 2)) * R
    pts += list(sp[ok(sp)])
    for n, dd in zip(hs[:, :3], hs[:, 3]):  # plane ∩ sphere circles
        nn = np.linalg.norm(n)
        n, dd = n / nn, dd / nn
        dist = -dd  # plane: n.x = dist
        if abs(dist) >= R:
            continue
        rho = np.sqrt(R ** 2 - dist ** 2)
        u = np.cross(n, [1, 0, 0] if abs(n[0]) < 0.9 else [0, 1, 0])
        u /= np.linalg.norm(u)
        w = np.cross(n, u)
        t = np.linspace(0, 2 * np.pi, int(2 * np.pi * rho / spacing) + 16, endpoint=False)
        C = dist * n + rho * (np.outer(np.cos(t), u) + np.outer(np.sin(t), w))
        pts += list(C[ok(C)])
    P = np.array(pts)
    return P if len(P) >= 4 else None


def _taper_hs(lo, hi, faces, u, t: float, w0: float) -> list:
    """Cone-like ramps (Doose 1984, US 4,427,197: inclined surfaces from the outside toward the
    bearing race), approximated by planes: each listed inner-plane face n.x <= c is tilted inward
    near the sphere, giving n.x <= c - t*(u.x - w0). As a halfspace: (n + t*u).x <= c + t*w0, which is
    inactive below w0. faces[i] = (lo_face, hi_face) booleans."""
    # LATERAL version: a misalignment delta about axis j shifts a face on axis i by ~ (coordinate along the
    # third axis) * delta, so each inner-plane face retreats linearly with |coordinate| along every OTHER
    # axis beyond w0 (planar, convex): n.x + t*s*x_j <= c + t*w0, with s the sign(s) the piece extends to.
    hs = []
    if t <= 0:
        return hs
    home_sign = np.sign(u)
    for i in range(3):
        e = np.zeros(3)
        e[i] = 1.0
        for is_face, n, c in ((faces[i][0], -e, -lo[i]), (faces[i][1], e, hi[i])):
            if not is_face:
                continue
            for j in range(3):
                if j == i:
                    continue
                for s in ([home_sign[j]] if home_sign[j] != 0 else [1.0, -1.0]):
                    ej = np.zeros(3)
                    ej[j] = s
                    hs.append([*(n + t * ej), -(c + t * w0)])
    return hs


def piece_geometry(home: tuple[int, int, int], p: D5Params) -> list[np.ndarray]:
    """List of convex vertex sets (mm, world frame at the home pose) for one piece."""
    h = np.array(home)
    geoms = []
    Ri = p.RS - p.clearance / 2
    Ro = p.RS + p.clearance / 2
    u_axis = h / np.linalg.norm(h)
    # inner cell (foot / boss) ∩ ball(Ri); every box face of the inner cell is a real cut face
    lo, hi = zip(*[_range(int(s), p.S, p.gap, Ri) for s in h])
    # real cut faces: both faces on a 0-axis; only the inner (+/-S) face on a signed axis (the other bound is the ball)
    real = [((int(s) > 0) or s == 0, (int(s) < 0) or s == 0) for s in h]
    foot_hs = _box_hs(lo, hi) + _bevel_hs(lo, hi, p.bevel_foot, real) + _taper_hs(lo, hi, real, u_axis, p.taper, p.taper_start)
    foot = _convex_points(foot_hs, Ri, p.sphere_spacing_mm)
    if foot is not None:
        geoms.append(foot)
    # outer cell, split by what lies beneath it inside the ball
    olo, ohi = zip(*[_range(int(s), p.A, p.gap, p.H) for s in h])
    s_in = p.S - p.gap / 2
    splits = []
    for i in range(3):
        if h[i] == 0:
            # (lo, hi, foreign_beneath, lo_is_real_face, hi_is_real_face)
            splits.append([(olo[i], -s_in, True, True, False), (-s_in, s_in, False, False, False),
                           (s_in, ohi[i], True, False, True)])
        else:
            splits.append([(olo[i], ohi[i], False, True, True)])
    dirs = _fib_dirs(int(4 * np.pi / np.radians(p.pad_spacing_deg) ** 2))
    for bx in splits[0]:
        for by in splits[1]:
            for bz in splits[2]:
                blo = np.array([bx[0], by[0], bz[0]])
                bhi = np.array([bx[1], by[1], bz[1]])
                realf = [(b[3], b[4]) for b in (bx, by, bz)]
                base = _box_hs(blo, bhi) + _bevel_hs(blo, bhi, p.bevel_body, realf)
                if not (bx[2] or by[2] or bz[2]):
                    internal = any(not f for b, f2 in zip((bx, by, bz), realf) for f in f2 if b[0] != b[1]) and \
                        any(hh == 0 for hh in h)
                    if internal and p.bevel_inner > 0:
                        # Split faces (+/-S) are internal only OUTSIDE the bearing sphere. Inside it they face
                        # other pieces' feet, so bevel them there: lower part (inside the ball) gets bevels on
                        # every face; upper part keeps the split faces unbevelled (no grooves on the outer surface).
                        u = h / np.linalg.norm(h)
                        dcut = p.inner_split_centre if np.count_nonzero(h) == 1 else p.inner_split_edge
                        split_faces = [(hh == 0, hh == 0) for hh in h]  # the +/-S faces of the central sub-box
                        lower = (_box_hs(blo, bhi) + _bevel_hs(blo, bhi, p.bevel_inner, [(True, True)] * 3)
                                 + _taper_hs(blo, bhi, split_faces, u, p.taper, p.taper_start) + [[*u, -dcut]])
                        upper = base + [[*(-u), dcut]]
                        for hs in (lower, upper):
                            v = _convex_points(hs, None, p.sphere_spacing_mm)
                            if v is not None:
                                geoms.append(v)
                        continue
                    v = _convex_points(base, None, p.sphere_spacing_mm)
                    if v is not None:
                        geoms.append(v)
                    continue
                # pads: sub-box ∩ Voronoi cone(n_k) ∩ {n_k . x >= Ro}
                cand = dirs[np.all((dirs * Ro >= blo - 2) & (dirs * Ro <= bhi + 2), axis=1)]
                cand = cand[[_box_reaches_out(blo, bhi, d, Ro) for d in cand]]
                for k, nk in enumerate(cand):
                    hs = base + [[*(-nk), Ro]]
                    for j, nj in enumerate(cand):
                        if j != k:
                            hs.append([*(nj - nk), 0.0])  # (nk - nj) . x >= 0
                    v = _polytope(np.array(hs, float))
                    if v is not None and len(v) >= 4:
                        geoms.append(v)
    return geoms


def _box_reaches_out(blo, bhi, d, Ro) -> bool:
    corners = np.array(np.meshgrid(*zip(blo, bhi))).T.reshape(-1, 3)
    return (corners @ d).max() > Ro + 0.05


# ---------------------------------------------------------------------------- MJCF
def _fmt(v) -> str:
    return " ".join(f"{float(x):.9g}" for x in np.ravel(v))


def build_xml(p: D5Params | None = None, actuated_centres: bool = True) -> tuple[str, dict]:
    p = p or D5Params()
    assets, bodies, actuators, info = [], [], [], {}
    for home in HOME_POSITIONS:
        name = cubie_name(home)
        kind = {1: "centre", 2: "edge", 3: "corner"}[int(np.count_nonzero(home))]
        gs = piece_geometry(home, p)
        info[name] = {"kind": kind, "n_geoms": len(gs)}
        origin = np.zeros(3) if kind == "centre" else np.array(home, float) * p.pitch
        mass = {"corner": p.mass_corner, "edge": p.mass_edge, "centre": p.mass_centre}[kind] / len(gs)
        geo = []
        for i, v in enumerate(gs):
            assets.append(f'    <mesh name="{name}_m{i}" vertex="{_fmt((v - origin) / 1000)}"/>')
            geo.append(f'        <geom class="piece" mesh="{name}_m{i}" mass="{mass:.6g}"/>')
        marker = (f'        <geom name="{name}_g" type="sphere" size="0.001" contype="0" conaffinity="0" '
                  f'group="5" mass="0" pos="{_fmt((np.array(home, float) * p.pitch - origin) / 1000)}"/>')
        if kind == "centre":
            ax = np.array(home, float)
            joints = (f'        <joint name="{name}_j" type="hinge" axis="{_fmt(ax)}" damping="0.0005" '
                      f'frictionloss="0.0005" armature="1e-6"/>\n'
                      f'        <joint name="{name}_r" type="slide" axis="{_fmt(ax)}" range="{_fmt(p.slide_range)}" '
                      f'stiffness="{p.spring_k}" springref="{-p.spring_preload / p.spring_k:.9g}" damping="0.05" '
                      f'armature="1e-6" solreflimit="0.001 1" solimplimit="0.99 0.999 0.0005"/>')
            bodies.append(f'    <body name="{name}" pos="0 0 0">\n{joints}\n{marker}\n' + "\n".join(geo) + "\n    </body>")
            if actuated_centres:
                actuators.append(f'    <position name="turn_{name}" joint="{name}_j" kp="{p.turn_kp}" kv="{0.04 * p.turn_kp}" forcerange="{-p.turn_torque} {p.turn_torque}"/>')
        else:
            bodies.append(f'    <body name="{name}" pos="{_fmt(origin / 1000)}">\n        <freejoint name="{name}_free"/>\n'
                          f'{marker}\n' + "\n".join(geo) + "\n    </body>")
    si = _fmt(p.solimp)
    xml = f"""<mujoco model="rubiknetic_d5">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="{p.timestep}" integrator="implicitfast" cone="elliptic" impratio="10"
          solver="Newton" iterations="100" tolerance="1e-10" gravity="0 0 -9.81"/>
  <default>
    <default class="piece">
      <geom type="mesh" condim="3" friction="{p.friction} 0.0025 0.0005" solref="{_fmt(p.solref)}"
            solimp="{si}" margin="{p.margin}"/>
    </default>
  </default>
  <asset>
{chr(10).join(assets)}
  </asset>
  <worldbody>
    <body name="core"/>
{chr(10).join(bodies)}
  </worldbody>
  <actuator>
{chr(10).join(actuators)}
  </actuator>
</mujoco>
"""
    return xml, info


# ---------------------------------------------------------------------------- M1 pad rig, spliced
def build_xml_with_rig(p: D5Params | None = None, m1_overrides: dict | None = None) -> tuple[str, dict]:
    """D5 cube (passive centre hinges) plus the unchanged M1 pad rig: six turners with two
    gripper pads each and actuators grip_{F}a/b and turn_{F}, taken verbatim from build_m1_xml."""
    import re

    from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml

    p = p or D5Params()
    xml, info = build_xml(p, actuated_centres=False)
    m1 = build_m1_xml(M1Params(**(m1_overrides or {})))
    pad_default = re.search(r'    <default class="pad">.*?</default>\n', m1, re.S).group(0)
    rig_bodies = m1[m1.index('    <body name="turner_'):m1.index("  </worldbody>")]
    rig_acts = "\n".join(l for l in m1.splitlines() if l.strip().startswith(('<position name="grip_', '<position name="turn_')))
    xml = xml.replace('    <default class="piece">', pad_default + '    <default class="piece">', 1)
    xml = xml.replace('<geom type="mesh" condim="3"', '<geom type="mesh" conaffinity="3" condim="3"', 1)
    xml = xml.replace("  </worldbody>", rig_bodies + "  </worldbody>", 1)
    xml = xml.replace("  <actuator>\n", "  <actuator>\n" + rig_acts + "\n", 1)
    return xml, info
