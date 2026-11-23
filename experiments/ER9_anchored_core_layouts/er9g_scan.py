"""ER9 Part G, P1: kinematic scan of an arm (PROTOCOL.md G.6 P1). Static; no dynamics, no force evaluation.

Poses are set kinematically on the B1 trial model (qpos, then mj_kinematics), the way ER2's Rig.pose sets them (ER3,
ER6 and Part A use it): a rotation vector per piece about the cube centre, hinge centres by their axis component.
Magnet centres and directions come from the body poses exactly as MagnetSystem.world computes them (and as
er9_hybrid_pairs.scan rotates them; the cubie body frames sit at the cube centre).

Measured per class (er9g_stats.ClassStats: CE, PCon, PCoff, PP3, X, definitions of magnets.py):
  near evaluations, perpendicular near pairs, largest near tilt, clamped-z count, smallest centre distance, the largest
  path deviation d of PC pairs, and the smallest surface clearance between the real cylinders by ER6's sweep method
  (er6_screen.surface_samples / frame / signed_dist; sample spacing 0.05 mm; checked for every pair whose centres are
  within the sum of the two bounding-sphere radii + 0.5 mm, ER6's cutoff generalised to two magnet types; a pair
  outside it has clearance > 0.5 mm, and its sphere bound is reported).
Coverage: rigid turns of each of the 6 faces, -90 to +90 deg in 0.5 deg steps (361 poses per face).
E1-5-like rigid poses (reported only): the U layer offset by +-alpha, alpha = 1..20 deg in 1 deg steps, then a rigid
R turn from 0 to 90 deg in 0.5 deg steps (R-layer pieces by home position; the two U-and-R pieces get R(theta) U(alpha)).
Core-to-4x2 bound: smallest 4x2 centre radius minus largest core-magnet centre radius (radii are invariant in B1).
PC evaluations are pooled at D_val = inf here (D_val comes from P4.d, after P1); d is reported per class.

Stop rules (G.6 P1; any one stops the arm; each reported with its margin), in any rigid face turn:
  S1 a perpendicular near pair in any class            S2 a CE tilt > 5 deg, or a CE pair clamped
  S3 a PP3 pair near                                   S4 a PC tilt > 20 deg
  S5 a cross-type pair within r2, or the cross-type piece-to-piece minimum < r2 + 1.0 mm
  S6 two magnets intersect (smallest surface clearance < 0; same-body pairs included, checked once at home)
  S7 the core-to-4x2 bound < r2
Usage (WSL, repo root):
  ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9g_scan.py ARM [--grade N52] [--out DIR]
Writes DIR/P1_<ARM>.json (default DIR = results/hybrid_g/static; exclusive create, never overwritten).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

from rubiknetic.cube_logic.geometric import HOME_POSITIONS
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml, cubie_name

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "results" / "hybrid_g" / "static"


def _load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


LY = _load("er9g_layouts", HERE / "er9g_layouts.py")
ST = _load("er9g_stats", HERE / "er9g_stats.py")

STEP_DEG = 0.5
E15_ALPHAS = tuple(range(1, 21))
H_SAMPLE = 5e-5                                         # ER6's H_SAMPLE
CE_TILT, PC_TILT, X_MARGIN_MM = 5.0, 20.0, 1.0
NAMES = [cubie_name(h) for h in HOME_POSITIONS]
HOMES = {cubie_name(h): np.array(h, float) for h in HOME_POSITIONS}


# ---- ER6's sweep method (er6_screen.py l.74-108), generalised to two magnet types ------------------------------------
def surface_samples(a: float, L: float, h: float = H_SAMPLE) -> np.ndarray:
    """er6_screen.surface_samples, unchanged: points on a cylinder's surface (axis z, centred), spacing <= h."""
    nt = int(np.ceil(2 * np.pi * a / h)); nz = int(np.ceil(L / h)) + 1
    t = np.linspace(0, 2 * np.pi, nt, endpoint=False); z = np.linspace(-L / 2, L / 2, nz)
    T, Z = np.meshgrid(t, z)
    pts = [np.column_stack([a * np.cos(T.ravel()), a * np.sin(T.ravel()), Z.ravel()])]
    for r in np.linspace(0, a, int(np.ceil(a / h)) + 1):
        k = max(1, int(np.ceil(2 * np.pi * r / h)))
        tt = np.linspace(0, 2 * np.pi, k, endpoint=False)
        for zc in (-L / 2, L / 2):
            pts.append(np.column_stack([r * np.cos(tt), r * np.sin(tt), np.full(k, zc)]))
    return np.vstack(pts)


def frame(axis: np.ndarray) -> np.ndarray:
    """er6_screen.frame, unchanged."""
    z = axis / np.linalg.norm(axis)
    x = np.cross(z, [1.0, 0, 0] if abs(z[0]) < 0.9 else [0, 1.0, 0]); x /= np.linalg.norm(x)
    return np.column_stack([x, np.cross(z, x), z])


def signed_dist(pts: np.ndarray, c: np.ndarray, axis: np.ndarray, a: float, L: float) -> np.ndarray:
    """er6_screen.signed_dist, unchanged: signed distance of points to a solid cylinder."""
    d = pts - c
    z = d @ axis
    r = np.linalg.norm(d - np.outer(z, axis), axis=1)
    dz, dr = np.abs(z) - L / 2, r - a
    out = np.hypot(np.maximum(dz, 0), np.maximum(dr, 0))
    inside = (dz <= 0) & (dr <= 0)
    out[inside] = np.maximum(dz, dr)[inside]
    return out


def clearance2(c1, n1, cyl1, c2, n2, cyl2) -> float:
    """er6_screen.clearance for two cylinders that may differ: cyl = (a, L, samples). Same-type pairs give exactly
    ER6's value."""
    a1, L1, S1 = cyl1
    a2, L2, S2 = cyl2
    p1 = c1 + S1 @ frame(n1).T
    p2 = c2 + S2 @ frame(n2).T
    return float(min(signed_dist(p1, c2, n2, a2, L2).min(), signed_dist(p2, c1, n1, a1, L1).min()))


# ---- kinematic poses -------------------------------------------------------------------------------------------------
class Kin:
    """The B1 trial model (M1Params with M4's BASE_OVERRIDES, gap 0.05 mm) posed kinematically, as ER2's Rig."""

    def __init__(self, gap: float = LY.GAP):
        self.p = M1Params(**{**LY.BASE_OVERRIDES, "gap": gap})
        self.m = mujoco.MjModel.from_xml_string(build_m1_xml(self.p))
        self.d = mujoco.MjData(self.m)
        self.bid = {n: mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_BODY, n) for n in NAMES + ["core"]}
        self.jid = {n: mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_JOINT, n + "_j") for n in NAMES}

    def pose(self, moves: dict) -> None:
        """moves: piece name -> rotation vector (rad) about the cube centre (er2_static.Rig.pose, same steps)."""
        mujoco.mj_resetData(self.m, self.d)
        for n, rv in moves.items():
            j = self.jid[n]; adr = self.m.jnt_qposadr[j]
            rv = np.asarray(rv, float)
            ang = float(np.linalg.norm(rv))
            if ang == 0.0:
                continue
            if self.m.jnt_type[j] == mujoco.mjtJoint.mjJNT_BALL:
                q = np.zeros(4); mujoco.mju_axisAngle2Quat(q, rv / ang, ang)
                qn = np.zeros(4); mujoco.mju_mulQuat(qn, q, self.d.qpos[adr:adr + 4].copy())
                self.d.qpos[adr:adr + 4] = qn
            else:
                self.d.qpos[adr] += float(np.dot(self.m.jnt_axis[j], rv))
        mujoco.mj_kinematics(self.m, self.d)

    def world(self, mags: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Magnet centres and directions as MagnetSystem.world computes them, plus body ids."""
        b = np.array([self.bid[g["body"]] for g in mags])
        R = self.d.xmat[b].reshape(-1, 3, 3)
        p = self.d.xpos[b] + np.einsum("nij,nj->ni", R, np.array([g["pos"] for g in mags]))
        n = np.einsum("nij,nj->ni", R, np.array([g["dir"] for g in mags]))
        return p, n, b


def face_members(face: str) -> list[str]:
    nrm = np.array(FACE_NORMAL[face], float)
    return [x for x in NAMES if HOMES[x] @ nrm == 1]


def face_turn_moves(face: str, deg: float) -> dict:
    nrm = np.array(FACE_NORMAL[face], float)
    return {x: np.radians(deg) * nrm for x in face_members(face)}


def e15_moves(alpha_deg: float, theta_deg: float) -> dict:
    """U offset by alpha, then a rigid R turn by theta (rotation vectors about the cube centre)."""
    u, r = np.array(FACE_NORMAL["U"], float), np.array(FACE_NORMAL["R"], float)
    RU, RR = Rotation.from_rotvec(np.radians(alpha_deg) * u), Rotation.from_rotvec(np.radians(theta_deg) * r)
    mem_u, mem_r = set(face_members("U")), set(face_members("R"))
    out = {}
    for x in NAMES:
        rot = (RR if x in mem_r else Rotation.identity()) * (RU if x in mem_u else Rotation.identity())
        out[x] = rot.as_rotvec()
    return out


def degs(lo: float = -90.0, hi: float = 90.0, step: float = STEP_DEG) -> np.ndarray:
    return np.linspace(lo, hi, int(round((hi - lo) / step)) + 1)


# ---- the scan ---------------------------------------------------------------------------------------------------------
class Clearances:
    """Smallest surface clearance per class over a pose family, with ER6's sampled-surface method. A pair whose
    bodies share one rigid motion within a family keeps its clearance, so it is computed once per family."""

    def __init__(self, mags: list[dict], stats: ST.ClassStats):
        self.mags = mags
        self.cyl = {}
        self.cyl_of = []
        for g in mags:
            key = (g["mp"].diameter / 2, g["mp"].length)
            if key not in self.cyl:
                self.cyl[key] = (key[0], key[1], surface_samples(*key))
            self.cyl_of.append(key)
        self.rb = np.array([math.hypot(k[0], k[1] / 2) for k in self.cyl_of])   # bounding-sphere radius
        self.ii, self.jj, self.code = stats.ii, stats.jj, stats.code
        self.cut = self.rb[self.ii] + self.rb[self.jj] + 5e-4
        self.cls_name = {0: "CE", 1: "PC", 3: "PP3", 4: "X"}
        self.reset()

    def reset(self) -> None:
        self.best = {k: {"min_surface_clearance_mm": None, "at": None, "pairs_checked": 0,
                         "sphere_bound_min_mm": None} for k in ("CE", "PC", "PP3", "X")}

    def family(self) -> None:
        self.cache: dict = {}

    def update(self, p, n, group: np.ndarray, where) -> None:
        """group: per-magnet rigid-motion label in this pose family (same label = same rigid motion)."""
        r = np.linalg.norm(p[self.jj] - p[self.ii], axis=1)
        for c, name in self.cls_name.items():
            msk = self.code == c
            if msk.any():
                v = float((r[msk] - self.rb[self.ii[msk]] - self.rb[self.jj[msk]]).min()) * 1e3
                b = self.best[name]
                b["sphere_bound_min_mm"] = v if b["sphere_bound_min_mm"] is None else min(b["sphere_bound_min_mm"], v)
        for k in np.nonzero(r < self.cut)[0]:
            i, j = int(self.ii[k]), int(self.jj[k])
            rigid = group[i] == group[j]
            if rigid and (i, j) in self.cache:
                continue
            cl = clearance2(p[i], n[i], self.cyl[self.cyl_of[i]], p[j], n[j], self.cyl[self.cyl_of[j]]) * 1e3
            if rigid:
                self.cache[(i, j)] = cl
            b = self.best[self.cls_name[int(self.code[k])]]
            b["pairs_checked"] += 1
            if b["min_surface_clearance_mm"] is None or cl < b["min_surface_clearance_mm"]:
                b["min_surface_clearance_mm"] = cl
                b["at"] = {**where, "pair": [self.label(i), self.label(j)]}

    def label(self, k: int) -> str:
        g = self.mags[k]
        return f"{'4x3' if LY.is_43(g) else '4x2'} {g['kind']}@{g['body']}"


def same_body_clearance(mags: list[dict], p: np.ndarray, n: np.ndarray) -> dict:
    """Same-body pairs (rigid; not evaluated by the force law) at home, for the intersection rule only."""
    cyl, best = {}, {"min_surface_clearance_mm": None, "pair": None, "pairs_checked": 0}
    for i in range(len(mags)):
        for j in range(i + 1, len(mags)):
            if mags[i]["body"] != mags[j]["body"]:
                continue
            ki = (mags[i]["mp"].diameter / 2, mags[i]["mp"].length)
            kj = (mags[j]["mp"].diameter / 2, mags[j]["mp"].length)
            rb = math.hypot(ki[0], ki[1] / 2) + math.hypot(kj[0], kj[1] / 2) + 5e-4
            if np.linalg.norm(p[i] - p[j]) >= rb:
                continue
            for k in (ki, kj):
                if k not in cyl:
                    cyl[k] = (k[0], k[1], surface_samples(*k))
            cl = clearance2(p[i], n[i], cyl[ki], p[j], n[j], cyl[kj]) * 1e3
            best["pairs_checked"] += 1
            if best["min_surface_clearance_mm"] is None or cl < best["min_surface_clearance_mm"]:
                best["min_surface_clearance_mm"], best["pair"] = cl, [mags[i]["kind"], mags[j]["kind"], mags[i]["body"]]
    return best


def core_bound(mags: list[dict], r2: float) -> dict:
    """Every magnet's centre radius is invariant in B1 (pieces rotate about the centre; the core is fixed), so a core
    magnet and a 4x2 magnet are never closer than (smallest 4x2 radius) - (largest core radius)."""
    r42 = [float(np.linalg.norm(g["pos"])) for g in mags if not LY.is_43(g)]
    rc = [float(np.linalg.norm(g["pos"])) for g in mags if g["body"] == "core"]
    if not r42 or not rc:
        return {"applicable": False}
    b = min(r42) - max(rc)
    return {"applicable": True, "min_r_4x2_mm": min(r42) * 1e3, "max_r_core_mm": max(rc) * 1e3,
            "bound_mm": b * 1e3, "r2_mm": r2 * 1e3, "margin_mm": (b - r2) * 1e3}


def _family(kin, mags, mp, pose_list, group_of) -> dict:
    """Runs one pose family: stats per class (D_val = inf, pooled PC) and clearances."""
    stats = ST.ClassStats(mags, mp, ST.PROXY_D_VAL)
    cl = Clearances(mags, stats)
    cl.family()
    for where, moves in pose_list:
        kin.pose(moves)
        p, n, b = kin.world(mags)
        stats.update(p, n)
        cl.update(p, n, group_of(where, b), where)
    return {"stats": stats.as_dict(), "clearance": cl.best, "poses": stats.calls}


def scan(arm: str, grade: str = "N52", step_deg: float = STEP_DEG, alphas=E15_ALPHAS, e15: bool = True,
         faces=FACES) -> dict:
    """P1 for one arm. Returns the record (no file written)."""
    LY.check_arm(arm, grade)
    t0 = time.perf_counter()
    kin = Kin()
    mags = LY.arm_mags(arm, grade, kin.p.pitch, kin.p.gap)
    mp = LY.system_mp(arm, grade)
    r2 = mp.r2
    bid = kin.bid
    out = {"arm": arm, "grade": grade, "protocol": "ER9 PROTOCOL.md Part G, G.6 P1", "n_magnets": len(mags),
           "pair_counts": LY.pair_counts(mags), "step_deg": step_deg, "faces": list(faces),
           "D_val_deg_used_for_split": "inf (pooled PC; D_val is fixed later by P4.d)",
           "clearance_method": {"source": "experiments/ER6_real_placement_screen/er6_screen.py sweep / clearance",
                                "sample_spacing_mm": H_SAMPLE * 1e3,
                                "cutoff": "bounding-sphere radii sum + 0.5 mm"}}
    per_face = {}
    for f in faces:
        mem = {bid[x] for x in face_members(f)}
        poses = [({"face": f, "deg": float(a)}, face_turn_moves(f, a)) for a in degs(-90, 90, step_deg)]
        per_face[f] = _family(kin, mags, mp, poses, lambda w, b, mem=mem: np.isin(b, list(mem)).astype(int))
    out["face_turns"] = {"per_face": per_face, "combined": combine(per_face.values())}
    if e15:
        fam = {}
        uid = {bid[x] for x in face_members("U")}
        rid = {bid[x] for x in face_members("R")}
        for s in (1, -1):
            for a in alphas:
                poses = [({"alpha_deg": s * a, "R_deg": float(t)}, e15_moves(s * a, t)) for t in degs(0, 90, step_deg)]
                fam[f"{s * a:+d}"] = _family(kin, mags, mp, poses, lambda w, b: np.isin(b, list(uid)).astype(int)
                                             + 2 * np.isin(b, list(rid)).astype(int))
        out["e15_like"] = {"note": "reported only (G.6): rigid, contacts ignored; bounds what E1-5 could reach",
                           "per_alpha": fam, "combined": combine(fam.values())}
    kin.pose({})
    p, n, _ = kin.world(mags)
    out["same_body_home"] = same_body_clearance(mags, p, n)
    out["core_to_4x2_bound"] = core_bound(mags, r2)
    out["stops"] = stop_rules(out, r2)
    out["stopped"] = any(s["stop"] for s in out["stops"])
    out["wall_s"] = time.perf_counter() - t0
    return out


def combine(families) -> dict:
    """Worst case over pose families: counts summed, maxima maxed, minima minned."""
    fams = list(families)
    st = {}
    for k in fams[0]["stats"]:
        vals = [f["stats"][k] for f in fams]
        if k == "D_val_deg" or k == "legacy":
            st[k] = vals[0]
        elif k.endswith("_mm"):
            v = [x for x in vals if x is not None]
            st[k] = min(v) if v else None
        elif k.startswith("PC_max") or k.endswith("_deg"):
            st[k] = max(vals)
        else:
            st[k] = sum(vals)
    cl = {}
    for c in fams[0]["clearance"]:
        rows = [f["clearance"][c] for f in fams]
        have = [r for r in rows if r["min_surface_clearance_mm"] is not None]
        best = min(have, key=lambda r: r["min_surface_clearance_mm"]) if have else None
        sb = [r["sphere_bound_min_mm"] for r in rows if r["sphere_bound_min_mm"] is not None]
        cl[c] = {"min_surface_clearance_mm": best["min_surface_clearance_mm"] if best else None,
                 "at": best["at"] if best else None, "pairs_checked": sum(r["pairs_checked"] for r in rows),
                 "sphere_bound_min_mm": min(sb) if sb else None}
    return {"stats": st, "clearance": cl}


def stop_rules(rec: dict, r2: float) -> list[dict]:
    """G.6 P1 stop rules on the rigid face turns (not on the E1-5-like poses, which are reported only)."""
    s = rec["face_turns"]["combined"]["stats"]
    cl = rec["face_turns"]["combined"]["clearance"]
    perp = sum(s[f"{k}_near_perpendicular"] for k in ST.CLASSES)
    pc_tilt = max(s["PCon_max_near_tilt_deg"], s["PCoff_max_near_tilt_deg"])
    xpp = s["X_piece_piece_min_centre_distance_mm"]
    mins = [c["min_surface_clearance_mm"] for c in cl.values() if c["min_surface_clearance_mm"] is not None]
    sb = rec["same_body_home"]["min_surface_clearance_mm"]
    if sb is not None:
        mins.append(sb)
    cb = rec["core_to_4x2_bound"]
    r2mm = r2 * 1e3
    rows = [
        {"rule": "S1 perpendicular near pair (any class)", "value": perp, "limit": "0", "stop": perp > 0},
        {"rule": "S2a CE tilt > 5 deg", "value": s["CE_max_near_tilt_deg"], "limit": CE_TILT,
         "margin": CE_TILT - s["CE_max_near_tilt_deg"], "stop": s["CE_max_near_tilt_deg"] > CE_TILT},
        {"rule": "S2b CE pair clamped", "value": s["CE_clamped_z"], "limit": "0", "stop": s["CE_clamped_z"] > 0},
        {"rule": "S3 PP3 pair near", "value": s["PP3_near_evals"], "limit": "0",
         "min_centre_distance_mm": s["PP3_min_centre_distance_mm"], "stop": s["PP3_near_evals"] > 0},
        {"rule": "S4 PC tilt > 20 deg", "value": pc_tilt, "limit": PC_TILT, "margin": PC_TILT - pc_tilt,
         "stop": pc_tilt > PC_TILT},
        {"rule": "S5a cross-type pair within r2", "value": s["X_near_evals"], "limit": "0",
         "min_centre_distance_mm": s["X_min_centre_distance_mm"], "stop": s["X_near_evals"] > 0},
        {"rule": "S5b cross-type piece-to-piece minimum < r2 + 1.0 mm", "value": xpp, "limit": r2mm + X_MARGIN_MM,
         "margin": None if xpp is None else xpp - (r2mm + X_MARGIN_MM),
         "stop": xpp is not None and xpp < r2mm + X_MARGIN_MM},
        {"rule": "S6 two magnets intersect", "value": min(mins) if mins else None, "limit": 0.0,
         "margin": min(mins) if mins else None, "stop": bool(mins) and min(mins) < 0},
        {"rule": "S7 core-to-4x2 bound < r2", "value": cb.get("bound_mm"), "limit": r2mm,
         "margin": cb.get("margin_mm"), "stop": bool(cb.get("applicable")) and cb["bound_mm"] < r2mm},
    ]
    for r in rows:
        r["stop"] = bool(r["stop"])
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("arm")
    ap.add_argument("--grade", default="N52")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    LY.check_arm(a.arm, a.grade)
    path = Path(a.out) / f"P1_{a.arm}.json"
    if path.exists():
        raise SystemExit(f"refusing to overwrite {path}")
    rec = scan(a.arm, a.grade)
    D10 = _load("d10_rest", REPO / "experiments/D10_m5_rest_diagnostic/d10_rest.py")
    rec["env"] = D10.environment()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x") as f:
        f.write(json.dumps(rec, indent=1, default=float))
    print(json.dumps({"arm": a.arm, "stopped": rec["stopped"], "stops": rec["stops"]}, indent=1, default=float))


if __name__ == "__main__":
    main()
