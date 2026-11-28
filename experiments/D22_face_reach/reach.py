"""D22 step 1 (UNSCORED, kinematics only): which world-frame grasps on the cube can each xArm7 reach at the G2 layout,
and which grasp pairs (stabilise + turn, hold + receive) are collision-free at static poses.

No dynamics. IK (D18 layout.ik, rotation-vector error) on the gripper-base pose, then MuJoCo collision detection at the
static pose (mj_kinematics + mj_collision with a contact margin, so near misses report a clearance).

Layout (as G2, D18): arm A base at the origin, arm B base at (L, 0, 0) yawed 180 deg (with the modelled wrist F/T
sensor, as G2), table plane z = 0, cube centre C = (L/2, 0, H). The cube is a 56.95 mm box; it is invariant under the
24 cube rotations, so every grasp and every check below is a WORLD-frame pose. graph.py maps cube faces to world
directions for each of the 24 cube orientations.

Grasp families (gripper base frame: z = approach axis into the cube, y = pad normal (closing direction), x = pad width):
  COAX  entry face normal n: z = -n; pads on the two faces +-y; fingertip distal end `depth` inside the entry face.
        tip p97 (P-97 stabiliser, 30 x 30 mm pad, depth 30 mm): holds the entry layer + 11 mm of the middle layer, so it
        stabilises a turn of the OPPOSITE face (G2 arm A: entry -x = D face).
        tip c1 (C1 turner, 25 x 14 mm pad, depth 14 mm): grips the entry layer only; J7 roll turns that layer (G2 arm B).
  SIDE  entry face normal n: z = -n; pad width (x) along a perpendicular axis, pad pushed flush to the end face
        fe = +-x; pads on the faces +-y. p97: holds layer fe + 11 mm of the middle, stabilises a turn of the face -fe.
        c1: holds layer fe + 6 mm of the middle (a weak hold; used only as arm B's holding grasp in the FIXED tooling
        scenario).

Checks:
  solo     one arm at the grasp (fingers closed at the calibrated 57 mm), the other arm parked at q = 0 (upright).
  turn     holder (p97 stabiliser) + turner (c1 COAX on the face the holder stabilises): turner at its approach pose
           (40 mm out, open), at the grasp, and with J7 rolled -180..+180 deg in 30 deg steps; the turned layer is a
           separate box rotated with the turner's gripper; the holder is checked against it.
  handoff  holder at its grasp + receiver at its approach pose (open) and at its grasp (closed); pad footprints on
           the cube faces must not overlap (1 mm clearance).
Collision geometry: the model's collision meshes (links, gripper base, knuckles), the fingertip boxes, plus the G2
finger meshes (visual-only in the G2 model; enabled here as a CONSERVATIVE convex hull, reported separately).
A check passes if no robot-robot, robot-table, self (non-adjacent links) or non-expected robot-cube pair is closer
than 0 mm; pads of a grasping arm may touch the cube.

Usage (WSL): python reach.py [--L 1.0] [--H 0.30] [--seeds 18] [--out results]
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "experiments" / "D18_two_arm_m7"))
import layout as LY  # noqa: E402  (read-only import; frozen code)
import two_arm as TA  # noqa: E402  (read-only import: add_ft_sensor, YAW180)

H, TU, bm = LY.H, LY.TU, LY.bm

MARGIN = 0.010          # contact margin (m): pairs closer than this are reported with their distance
TIGHT = 0.005           # clearance below this is "tight" (m)
PAD_SANITY = -0.001     # a grasping pad deeper than 1 mm into the cube is a geometry error
APPROACH = TA.APPROACH  # 40 mm, as G2
SWEEP_DEG = [a for a in range(-180, 181, 30) if a != 0]
IK_POS, IK_ROT = 1e-4, 0.01      # acceptance (m, deg)
TIP = {"p97": {"half": tuple(H.TIP_HALF), "depth": 2 * H.TIP_HALF[2]},
       "c1": {"half": tuple(TU.TURNER_TIP_HALF), "depth": TU.INSERTION_U}}
AXES = {"+x": np.array([1.0, 0, 0]), "-x": np.array([-1.0, 0, 0]), "+y": np.array([0, 1.0, 0]),
        "-y": np.array([0, -1.0, 0]), "+z": np.array([0, 0, 1.0]), "-z": np.array([0, 0, -1.0])}


def dname(v) -> str:
    for k, a in AXES.items():
        if np.allclose(v, a, atol=1e-9):
            return k
    raise ValueError(v)


def perp(n):
    return [k for k, a in AXES.items() if abs(a @ n) < 0.5]


def geometry(L: float, Hc: float) -> dict:
    p = H.m7_params()
    half = 1.5 * p.pitch - p.gap / 2
    tipdist = LY.gripper_frames()["c1"]           # distal fingertip end in the gripper-base frame (same for p97, c1)
    return {"C": np.array([L / 2, 0.0, Hc]), "half": half, "pitch": p.pitch, "gap": p.gap, "tipdist": tipdist, "L": L,
            "H": Hc}


def world_grasps(G: dict) -> list[dict]:
    """Every axis-aligned COAX / SIDE grasp, for both tips, as a world gripper-base pose."""
    C, half, td = G["C"], G["half"], G["tipdist"]
    out = []
    for tip, tp in TIP.items():
        depth, hw, padlen = tp["depth"], tp["half"][0], 2 * tp["half"][2]
        for nk, n in AXES.items():
            z = -n
            for yk in perp(n):                                   # COAX: 4 signed pad normals
                y = AXES[yk]
                x = np.cross(y, z)
                R = np.column_stack([x, y, z])
                base = C + n * (half - depth) + td * n
                stab = dname(-n) if tip == "p97" else None
                out.append({"id": f"COAX-{tip}:n{nk}:y{yk}", "kind": "COAX", "tip": tip, "n": nk, "y": yk,
                            "x": dname(x), "fe": None, "R": R, "p": base, "stab": stab,
                            "turn": nk if tip == "c1" else None, "hold": "strong" if tip == "p97" else "weak",
                            "pads": pads(n, x, y, 0.0, half, depth, padlen, hw)})
            for xk in perp(n):                                   # SIDE: pad width along x, flush with the end fe
                x = AXES[xk]
                y = np.cross(z, x)
                R = np.column_stack([x, y, z])
                for fs in (1.0, -1.0):
                    fe = fs * x
                    off = fs * (half - hw)
                    base = C + n * (half - depth) + fe * (half - hw) + td * n
                    out.append({"id": f"SIDE-{tip}:n{nk}:x{xk}:e{dname(fe)}", "kind": "SIDE", "tip": tip, "n": nk,
                                "y": dname(y), "x": xk, "fe": dname(fe), "R": R, "p": base,
                                "stab": dname(-fe) if tip == "p97" else None, "turn": None,
                                "hold": "strong" if tip == "p97" else "weak",
                                "pads": pads(n, x, y, off, half, depth, padlen, hw)})
    return out


def pads(n, x, y, xoff, half, depth, padlen, hw) -> list:
    """Pad footprints on the cube faces +-y: per world axis an interval (cube-centred coordinates, m)."""
    out = []
    a_n, a_x = int(np.argmax(np.abs(n))), int(np.argmax(np.abs(x)))
    s_n, s_x = float(n[a_n]), float(x[a_x])
    lo_n, hi_n = half - depth, half - depth + padlen                    # along n, measured from the centre
    iv_n = sorted([s_n * lo_n, s_n * hi_n])
    iv_x = sorted([s_x * (xoff - hw), s_x * (xoff + hw)])
    for s in (1.0, -1.0):
        face = dname(s * y)
        out.append({"face": face, a_n: iv_n, a_x: iv_x})
    return out


def pads_overlap(pa: list, pb: list, clr: float = 0.001) -> bool:
    for a in pa:
        for b in pb:
            if a["face"] != b["face"]:
                continue
            ax = [k for k in a if k != "face"]
            if all(max(a[k][0], b[k][0]) < min(a[k][1], b[k][1]) + clr for k in ax):
                return True
    return False


# ---------------------------------------------------------------- IK ------------------------------------------------
def arm_model(arm: str):
    sp = H.robot_spec(LY.robot_path())
    if arm == "B":
        TA.add_ft_sensor(sp)
    for key in list(sp.keys):
        sp.delete(key)
    m = sp.compile()
    return m, mujoco.MjData(m)


BASE = {"A": (np.zeros(3), np.eye(3)), "B": None}


def to_base(arm, p, R, L):
    if arm == "A":
        return p, R
    Y = TA.YAW180
    return Y.T @ (p - np.array([L, 0, 0])), Y.T @ R


def wrap(q):
    q = q.copy()
    for i in (0, 2, 4, 6):                                     # +-2 pi joints: same pose, largest margin
        q[i] = (q[i] + np.pi) % (2 * np.pi) - np.pi
    return q


def margin_deg(m, q) -> float:
    return LY.margin_of(m, q)


def solve_all(m, d, p, R, seeds, keep: int = 3) -> list[dict]:
    sols = []
    for s in seeds:
        q, ep, er = LY.ik(m, d, "xarm_gripper_base_link", p, R, [s])
        if q is None or ep > IK_POS or er > IK_ROT:
            continue
        q = wrap(q)
        sols.append({"q": q, "pos_err_m": ep, "rot_err_deg": er, "margin_deg": margin_deg(m, q)})
    sols.sort(key=lambda s: -s["margin_deg"])
    out = []
    for s in sols:                                            # distinct postures only
        if all(np.max(np.abs(s["q"] - o["q"])) > 0.3 for o in out):
            out.append(s)
        if len(out) >= keep:
            break
    return out


def approach_ik(m, d, p, R, q0) -> dict | None:
    pa = p - APPROACH * R[:, 2]
    q, ep, er = LY.ik(m, d, "xarm_gripper_base_link", pa, R, [q0])
    if q is None or ep > IK_POS or er > IK_ROT:
        return None
    q = wrap(q)
    return {"q": q, "pos_err_m": ep, "rot_err_deg": er, "margin_deg": margin_deg(m, q),
            "jump_rad": float(np.max(np.abs(q - q0)))}


# ---------------------------------------------------------- collision scene ----------------------------------------
def quat_of(R):
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, np.asarray(R, float).flatten())
    return q


def frame_z(n):
    n = np.asarray(n, float)
    a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    x = np.cross(a, n)
    x /= np.linalg.norm(x)
    return np.column_stack([x, np.cross(n, x), n])


class Scene:
    """Both arms (A: tipA, B: tipB + F/T), the cube proxies (full cube; held two layers; turned layer) as mocap boxes,
    the table plane."""
    FAR = np.array([0, 0, 50.0])

    def __init__(self, G: dict, tipA: str, tipB: str):
        self.G = G
        half, pitch, gap = G["half"], G["pitch"], G["gap"]
        rp = LY.robot_path()
        parent = H.robot_spec(rp, tip_half=TIP[tipA]["half"], tag=tipA)
        bsp = H.robot_spec(rp, tip_half=TIP[tipB]["half"], tag=tipB)
        TA.add_ft_sensor(bsp)
        for sp in (parent, bsp):
            for key in list(sp.keys):
                sp.delete(key)
            for side in ("left", "right"):                       # finger meshes: conservative collision hulls
                for g in sp.body(f"{side}_finger").geoms:
                    if g.type == mujoco.mjtGeom.mjGEOM_MESH:
                        g.contype, g.conaffinity = 1, 1
        fr = parent.worldbody.add_frame(pos=[G["L"], 0, 0], quat=[0, 0, 0, 1.0])
        fr.attach_body(bsp.body("link_base"), "B_", "")
        tbl = parent.worldbody.add_geom()
        tbl.name, tbl.type, tbl.size, tbl.pos = "table", mujoco.mjtGeom.mjGEOM_PLANE, [3, 3, 0.01], [G["L"] / 2, 0, 0]
        lt = pitch - gap
        for nm, size in (("cube_full", [half, half, half]), ("cube_held", [half, half, (2 * half - pitch) / 2]),
                         ("cube_layer", [half, half, lt / 2])):
            b = parent.worldbody.add_body(name=nm, pos=self.FAR.tolist(), mocap=True)
            g = b.add_geom()
            g.name, g.type, g.size = nm, mujoco.mjtGeom.mjGEOM_BOX, size
        for b in ("link_base", "B_link_base"):
            ex = parent.add_exclude()
            ex.bodyname1, ex.bodyname2 = "world", b
        m = parent.compile()
        m.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_GRAVITY
        coll = (m.geom_contype != 0) | (m.geom_conaffinity != 0)
        m.geom_margin[coll] = MARGIN
        m.geom_gap[:] = 0.0
        self.m, self.d = m, mujoco.MjData(m)
        self.tips = {"A": tipA, "B": tipB}
        rid = {"A": m.body("link_base").id, "B": m.body("B_link_base").id}
        self.owner = np.array([("A" if m.body_rootid[m.geom_bodyid[g]] == rid["A"] else
                                "B" if m.body_rootid[m.geom_bodyid[g]] == rid["B"] else
                                m.geom(g).name) for g in range(m.ngeom)], dtype=object)
        self.pad = np.zeros(m.ngeom, bool)
        for pre in ("", "B_"):
            tag = tipA if pre == "" else tipB
            for s in ("left", "right"):
                self.pad[m.geom(f"{pre}{s}_fingertip_{tag}").id] = True
        self.finger = np.zeros(m.ngeom, bool)
        for pre in ("", "B_"):
            for s in ("left", "right"):
                b = m.body(f"{pre}{s}_finger").id
                self.finger[(m.geom_bodyid == b) & (m.geom_type == mujoco.mjtGeom.mjGEOM_MESH)] = True
        chain = {"link_base": 0, **{f"link{i}": i for i in range(1, 8)}}
        self.link = np.array([chain.get(m.body(m.geom_bodyid[g]).name.removeprefix("B_"), 8) for g in range(m.ngeom)])
        J = lambda pre, js: [m.jnt_qposadr[m.joint(pre + j).id] for j in js]  # noqa: E731
        self.qa = {"A": J("", bm.ARM_JOINTS), "B": J("B_", bm.ARM_JOINTS)}
        self.qg = {"A": J("", bm.GRIPPER_JOINTS), "B": J("B_", bm.GRIPPER_JOINTS)}
        cal = LY.calib()
        self.th_closed, self.th_open = cal["theta_at_calib_width_rad"], cal["theta_open_rad"]
        self.gb = {"A": m.body("xarm_gripper_base_link").id, "B": m.body("B_xarm_gripper_base_link").id}
        self.mocap = {nm: m.body_mocapid[m.body(nm).id] for nm in ("cube_full", "cube_held", "cube_layer")}

    def set_cube(self, mode: str, n=None, layer_R=None):
        """mode 'full' or 'split' (held two layers + the turned layer on the face with outward normal n)."""
        d, G = self.d, self.G
        for nm in self.mocap:
            d.mocap_pos[self.mocap[nm]] = self.FAR
            d.mocap_quat[self.mocap[nm]] = [1, 0, 0, 0]
        if mode == "full":
            d.mocap_pos[self.mocap["cube_full"]] = G["C"]
            return
        n = np.asarray(n, float)
        Rz = frame_z(n)
        lt = G["pitch"] - G["gap"]
        d.mocap_pos[self.mocap["cube_held"]] = G["C"] - n * G["pitch"] / 2
        d.mocap_quat[self.mocap["cube_held"]] = quat_of(Rz)
        d.mocap_pos[self.mocap["cube_layer"]] = G["C"] + n * (G["half"] - lt / 2)
        d.mocap_quat[self.mocap["cube_layer"]] = quat_of((layer_R if layer_R is not None else np.eye(3)) @ Rz)

    def set_arm(self, arm: str, q, grip: str):
        self.d.qpos[self.qa[arm]] = q
        self.d.qpos[self.qg[arm]] = self.th_closed if grip == "closed" else self.th_open

    def check(self, roles: dict, corotating: str | None = None) -> dict:
        """roles: arm -> 'grasp' (pads may touch the cube) | 'free' (nothing may touch). corotating: an arm whose
        contacts with 'cube_layer' are ignored (the turner rolls with the layer). Returns per-class min distances (m;
        MARGIN means 'no pair within the margin')."""
        m, d = self.m, self.d
        mujoco.mj_kinematics(m, d)
        mujoco.mj_collision(m, d)
        res = {k: MARGIN for k in ("arm_arm", "robot_table", "self_A", "self_B", "robot_cube", "finger_hull_cube")}
        res["pad_cube_min"] = MARGIN
        for i in range(d.ncon):
            c = d.contact[i]
            g1, g2, dist = int(c.geom1), int(c.geom2), float(c.dist)
            o1, o2 = self.owner[g1], self.owner[g2]
            arms = {"A", "B"}
            if o1 in arms and o2 in arms:
                if o1 != o2:
                    k = "arm_arm"
                elif self.link[g1] == 8 and self.link[g2] == 8 or abs(self.link[g1] - self.link[g2]) < 2:
                    continue
                else:
                    k = f"self_{o1}"
            elif (o1 in arms) != (o2 in arms):
                arm, g, other = (o1, g1, o2) if o1 in arms else (o2, g2, o1)
                if other == "table":
                    k = "robot_table"
                elif other.startswith("cube"):
                    if other == "cube_layer" and arm == corotating:
                        continue
                    if self.pad[g] and roles.get(arm) == "grasp":
                        res["pad_cube_min"] = min(res["pad_cube_min"], dist)
                        if dist >= PAD_SANITY:
                            continue
                        k = "robot_cube"
                    elif self.finger[g] and roles.get(arm) == "grasp":
                        k = "finger_hull_cube"
                    else:
                        k = "robot_cube"
                else:
                    continue
            else:
                continue
            res[k] = min(res[k], dist)
        return res


def verdict(res: dict, hull_blocks: bool) -> tuple[bool, float]:
    keys = ["arm_arm", "robot_table", "self_A", "self_B", "robot_cube"] + (["finger_hull_cube"] if hull_blocks else [])
    clr = min(res[k] for k in keys)
    return clr >= 0.0, clr


# -------------------------------------------------------------- main ------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=float, default=1.0)
    ap.add_argument("--H", type=float, default=0.30)
    ap.add_argument("--seeds", type=int, default=18, help="random IK seeds added to D18's 6")
    ap.add_argument("--keep", type=int, default=3, help="distinct IK postures kept per pose")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    t0 = time.time()
    G = geometry(a.L, a.H)
    grasps = world_grasps(G)
    rng = np.random.default_rng(22)
    lo, hi = np.array([-np.pi, -2.059, -np.pi, -0.19, -np.pi, -1.69, -np.pi]), np.array(
        [np.pi, 2.09, np.pi, 3.9, np.pi, 3.14, np.pi])
    seeds = LY.SEEDS + [rng.uniform(lo, hi) for _ in range(a.seeds)]
    models = {arm: arm_model(arm) for arm in ("A", "B")}

    # --- IK for every grasp, both arms (grasp + approach pose) ---
    ik = {}
    for arm in ("A", "B"):
        m, d = models[arm]
        for g in grasps:
            pb, Rb = to_base(arm, g["p"], g["R"], a.L)
            sols = solve_all(m, d, pb, Rb, seeds, a.keep)
            for s in sols:
                s["approach"] = approach_ik(m, d, pb, Rb, s["q"])
            ik[(arm, g["id"])] = sols
        print(f"IK arm {arm}: {sum(bool(ik[(arm, g['id'])]) for g in grasps)}/{len(grasps)} poses reachable "
              f"({time.time() - t0:.0f} s)", flush=True)

    scenes = {}

    def scene(tA, tB):
        if (tA, tB) not in scenes:
            scenes[(tA, tB)] = Scene(G, tA, tB)
        return scenes[(tA, tB)]

    gid = {g["id"]: g for g in grasps}
    other = {"A": "B", "B": "A"}
    PARK = np.zeros(7)

    # --- solo: one arm at its grasp, the other parked; also the approach pose ---
    solo = {}
    for arm in ("A", "B"):
        for g in grasps:
            res_list = []
            for k, s in enumerate(ik[(arm, g["id"])]):
                tags = {arm: g["tip"], other[arm]: g["tip"]}
                S = scene(tags["A"], tags["B"])
                S.set_cube("full")
                S.set_arm(other[arm], PARK, "open")
                S.set_arm(arm, s["q"], "closed")
                r = S.check({arm: "grasp"})
                ok, clr = verdict(r, False)
                okh, clrh = verdict(r, True)
                app = None
                if s["approach"] is not None:
                    S.set_arm(arm, s["approach"]["q"], "open")
                    ra = S.check({})
                    app = verdict(ra, True)
                res_list.append({"sol": k, "ok": ok, "clear_mm": clr * 1e3, "ok_with_hull": okh,
                                 "clear_hull_mm": clrh * 1e3, "detail_mm": {kk: v * 1e3 for kk, v in r.items()},
                                 "approach_ok": bool(app and app[0]), "approach_clear_mm": app[1] * 1e3 if app else None})
            solo[(arm, g["id"])] = res_list
    print(f"solo checks done ({time.time() - t0:.0f} s)", flush=True)

    def solo_ok(arm, g_id):
        return [r["sol"] for r in solo[(arm, g_id)] if r["ok"]]

    # --- turn: holder (p97 stabiliser) + turner (c1 COAX on the stabilised face) ---
    turns = []
    for holder in ("A", "B"):
        turner = other[holder]
        for gh in grasps:
            if gh["stab"] is None or not solo_ok(holder, gh["id"]):
                continue
            f = gh["stab"]
            nf = AXES[f]
            for gt in grasps:
                if gt["turn"] != f or not solo_ok(turner, gt["id"]):
                    continue
                tags = {holder: "p97", turner: "c1"}
                S = scene(tags["A"], tags["B"])
                best = None
                for ih in solo_ok(holder, gh["id"]):
                    for it in solo_ok(turner, gt["id"]):
                        qh = ik[(holder, gh["id"])][ih]["q"]
                        st = ik[(turner, gt["id"])][it]
                        rec = {"holder_sol": ih, "turner_sol": it, "fail": None}
                        S.set_arm(holder, qh, "closed")
                        # approach (turner open, 40 mm out), full cube
                        S.set_cube("full")
                        if st["approach"] is None:
                            rec["fail"] = "approach_ik"
                        else:
                            S.set_arm(turner, st["approach"]["q"], "open")
                            r = S.check({holder: "grasp"})
                            ok, c_app = verdict(r, False)
                            rec["approach_clear_mm"] = c_app * 1e3
                            if not ok:
                                rec["fail"] = f"approach ({min(r, key=lambda k: r[k] if k != 'pad_cube_min' else 1)})"
                        if rec["fail"] is None:
                            S.set_arm(turner, st["q"], "closed")
                            S.set_cube("split", nf)
                            r = S.check({holder: "grasp", turner: "grasp"}, corotating=turner)
                            ok, c0 = verdict(r, False)
                            rec["grasp_clear_mm"] = c0 * 1e3
                            if not ok:
                                rec["fail"] = "grasp"
                        if rec["fail"] is None:
                            mujoco.mj_kinematics(S.m, S.d)
                            R0 = S.d.xmat[S.gb[turner]].reshape(3, 3).copy()
                            sweep = {}
                            for ang in SWEEP_DEG:
                                q = st["q"].copy()
                                q[6] += np.radians(ang)
                                S.set_arm(turner, q, "closed")
                                mujoco.mj_kinematics(S.m, S.d)
                                R1 = S.d.xmat[S.gb[turner]].reshape(3, 3)
                                S.set_cube("split", nf, R1 @ R0.T)
                                r = S.check({holder: "grasp", turner: "grasp"}, corotating=turner)
                                sweep[ang] = verdict(r, False)[1] * 1e3
                            rec["sweep_clear_mm"] = sweep
                            q90 = [sweep[x] for x in (-90, -60, -30, 30, 60, 90)]
                            rec["quarter_ok"] = min(q90) >= 0
                            rec["half_ok"] = min(sweep.values()) >= 0
                            rec["quarter_clear_mm"] = min(q90 + [rec["grasp_clear_mm"]])
                            rec["half_clear_mm"] = min(list(sweep.values()) + [rec["grasp_clear_mm"]])
                            rec["j7_margin_half_turn_deg"] = float(180.0 - np.degrees(abs(st["q"][6])))
                            if not rec["quarter_ok"]:
                                rec["fail"] = "sweep"
                        rec["margin_holder_deg"] = ik[(holder, gh["id"])][ih]["margin_deg"]
                        rec["margin_turner_deg"] = st["margin_deg"]
                        score = (rec["fail"] is None, rec.get("half_ok", False),
                                 min(rec.get("quarter_clear_mm", -1e9), 10.0),
                                 min(rec["margin_holder_deg"], rec["margin_turner_deg"]))
                        if best is None or score > best[0]:
                            best = (score, rec)
                if best is not None:
                    turns.append({"holder": holder, "turner": turner, "hold_grasp": gh["id"], "turn_grasp": gt["id"],
                                  "face_dir": f, "ok": best[1]["fail"] is None, **best[1]})
    print(f"turn checks: {sum(t['ok'] for t in turns)}/{len(turns)} ok ({time.time() - t0:.0f} s)", flush=True)

    # --- handoff: holder at its grasp, receiver approaches (open) and closes ---
    hand = []
    for scen, tipmap in (("FIXED", {"A": "p97", "B": "c1"}), ("SYM", {"A": "p97", "B": "p97"})):
        S = scene(tipmap["A"], tipmap["B"])
        S.set_cube("full")
        for holder in ("A", "B"):
            recv = other[holder]
            for gh in grasps:
                if gh["tip"] != tipmap[holder] or not solo_ok(holder, gh["id"]):
                    continue
                for gr in grasps:
                    if gr["tip"] != tipmap[recv] or not solo_ok(recv, gr["id"]):
                        continue
                    if pads_overlap(gh["pads"], gr["pads"]):
                        continue
                    best = None
                    for ih in solo_ok(holder, gh["id"]):
                        for ir in solo_ok(recv, gr["id"]):
                            sr = ik[(recv, gr["id"])][ir]
                            S.set_arm(holder, ik[(holder, gh["id"])][ih]["q"], "closed")
                            rec = {"holder_sol": ih, "recv_sol": ir, "fail": None}
                            if sr["approach"] is None:
                                rec["fail"] = "approach_ik"
                            else:
                                S.set_arm(recv, sr["approach"]["q"], "open")
                                ok, ca = verdict(S.check({holder: "grasp"}), False)
                                rec["approach_clear_mm"] = ca * 1e3
                                if not ok:
                                    rec["fail"] = "approach"
                            if rec["fail"] is None:
                                S.set_arm(recv, sr["q"], "closed")
                                ok, cg = verdict(S.check({holder: "grasp", recv: "grasp"}), False)
                                rec["grasp_clear_mm"] = cg * 1e3
                                if not ok:
                                    rec["fail"] = "both_closed"
                            rec["margin_holder_deg"] = ik[(holder, gh["id"])][ih]["margin_deg"]
                            rec["margin_recv_deg"] = sr["margin_deg"]
                            clr = min(rec.get("approach_clear_mm", -1e9), rec.get("grasp_clear_mm", -1e9))
                            score = (rec["fail"] is None, min(clr, 10.0),
                                     min(rec["margin_holder_deg"], rec["margin_recv_deg"]))
                            if best is None or score > best[0]:
                                best = (score, rec)
                            if best[0][0] and best[0][1] >= 10.0:
                                break
                    hand.append({"scenario": scen, "holder": holder, "receiver": recv, "hold_grasp": gh["id"],
                                 "recv_grasp": gr["id"], "ok": best[1]["fail"] is None, **best[1]})
        print(f"handoff {scen}: {sum(h['ok'] for h in hand if h['scenario'] == scen)}/"
              f"{sum(1 for h in hand if h['scenario'] == scen)} ok ({time.time() - t0:.0f} s)", flush=True)

    # --- G2 baseline (checker sanity): A COAX-p97 from -x (D), B COAX-c1 from +x (U) ---
    out_dir = HERE / a.out
    out_dir.mkdir(parents=True, exist_ok=True)

    def js(v):
        if isinstance(v, np.ndarray):
            return v.tolist()
        if isinstance(v, (np.floating, np.integer)):
            return v.item()
        if isinstance(v, dict):
            return {str(k): js(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [js(x) for x in v]
        return v
    gout = []
    for g in grasps:
        e = {k: js(v) for k, v in g.items()}
        for arm in ("A", "B"):
            e[f"ik_{arm}"] = js(ik[(arm, g["id"])])
            e[f"solo_{arm}"] = js(solo[(arm, g["id"])])
        gout.append(e)
    meta = {"L": a.L, "H": a.H, "cube_centre": G["C"].tolist(), "half_mm": G["half"] * 1e3,
            "tipdist_mm": G["tipdist"] * 1e3, "margin_mm": MARGIN * 1e3, "tight_mm": TIGHT * 1e3,
            "sweep_deg": SWEEP_DEG, "ik_tol": [IK_POS, IK_ROT], "seeds": len(seeds), "keep": a.keep,
            "park": PARK.tolist(), "runtime_s": time.time() - t0, "mujoco": mujoco.__version__}
    (out_dir / "reach.json").write_text(json.dumps({"meta": meta, "grasps": gout, "turns": js(turns),
                                                    "handoffs": js(hand)}, indent=0))
    print(f"wrote {out_dir / 'reach.json'} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
