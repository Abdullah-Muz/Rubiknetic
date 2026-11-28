"""D21 camera placement study (UNSCORED; G5 preparation; pilot seed 29001; rendering only).

Runs the G2 scene (magnets on, stickers on; stickers are physics-invariant, P-110) through the start sequence, arm B's
approach and one U move, keeping state snapshots. For each snapshot and each candidate free camera (looking at the cube
centre), it renders a segmentation image twice:
  - as is (the arms and grippers can occlude the cube);
  - with every robot geom moved to a hidden geom group (no occlusion),
and reports, per cube face (by its current outward direction in the core frame), the fraction of sticker pixels still
visible. A greedy search then picks the smallest camera sets that see every face. Nothing here feeds a controller or a
result; it changes no frozen file.

Usage (WSL, repo root): MUJOCO_GL=egl ~/.venvs/rubiknetic/bin/python experiments/D21_camera_placement/camera_study.py
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
from pathlib import Path

import mujoco
import numpy as np

os.environ.setdefault("MUJOCO_GL", "egl")
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("trials", HERE.parents[0] / "E8_scored_g2" / "trials.py")
T = importlib.util.module_from_spec(spec)
sys.modules["trials"] = T
spec.loader.exec_module(T)
from rubiknetic.cube_logic import parse  # noqa: E402

W, H = 160, 120
DIST = 0.6                                      # m from the cube centre
AZ = list(range(0, 360, 30))
EL = [-90, -75, -60, -45, -30, -15, 0, 15, 30]  # MuJoCo: negative = from above; positive = from below the cube centre
                                                # (+30 at 0.6 m puts the camera at table height; the table can occlude)
FACES = ["+x", "-x", "+y", "-y", "+z", "-z"]    # core frame; cube U = core +z (= world +x at t0)
# At t0 (P-108 layout): core +z (U) = world +x, toward arm B; -z (D) toward arm A; core +-x = world +-y, the faces both
# arms' fingertips press on; core +y = world up; core -y = world down (toward the table and the stand).
FACE_NAME = {"+z": "U (toward arm B)", "-z": "D (toward arm A)", "+x": "side +y (gripped)", "-x": "side -y (gripped)",
             "+y": "top (world up)", "-y": "bottom (world down)"}


def main() -> None:
    T.configure({}, T.start_draw(29001))
    T.TA.STICKERS = True
    r = T.TA.TwoArm(T.L, T.HC, T.DEFAULTS["grip"])
    m, d = r.m, r.d
    snaps = [("t0 (arm A holds, B open)", d.qpos.copy())]
    r.approach()
    snaps.append(("after approach (B open at grasp)", d.qpos.copy()))
    seq, step0 = [], r.step

    def step(n):
        step0(n)
        seq.append(d.qpos.copy())
    r.step = step
    r.move(parse("U")[0])
    r.step = step0
    k = len(seq)
    for frac, label in ((0.30, "move 30 % (B closed, early roll)"), (0.45, "move 45 % (mid-roll)"),
                        (0.60, "move 60 % (late roll)"), (0.99, "move end (B open, rolled back)")):
        snaps.append((label, seq[min(k - 1, int(frac * k))]))
    T.MagnetSystem.uninstall()

    sticker = {m.geom(i).name: i for i in range(m.ngeom) if "_st" in m.geom(i).name}
    st_ids = np.array(sorted(sticker.values()))
    root = lambda g: m.body_rootid[m.geom_bodyid[g]]  # noqa: E731
    robot_roots = {m.body("link_base").id, m.body("B_link_base").id}
    robot_geoms = [g for g in range(m.ngeom) if root(g) in robot_roots]
    m_hidden = copy.copy(m)
    for g in robot_geoms:
        m_hidden.geom_group[g] = 5
    opt = mujoco.MjvOption()
    for gi in range(6):
        opt.geomgroup[gi] = 1 if gi < 5 else 0
    ren = mujoco.Renderer(m, H, W)
    ren_h = mujoco.Renderer(m_hidden, H, W)
    ren.enable_segmentation_rendering()
    ren_h.enable_segmentation_rendering()
    dd = mujoco.MjData(m)
    core = m.body("core").id
    centre = np.array([0.5, 0.0, 0.30])

    def face_of(qpos):
        """Sticker geom id -> current face label (direction of the sticker's offset from the core, core frame)."""
        dd.qpos[:] = qpos
        mujoco.mj_forward(m, dd)
        Rc = dd.xmat[core].reshape(3, 3)
        out = {}
        for g in st_ids:
            v = Rc.T @ (dd.geom_xpos[g] - dd.xpos[core])
            a = int(np.argmax(np.abs(v)))
            out[int(g)] = ("+" if v[a] > 0 else "-") + "xyz"[a]
        return out

    def counts(renderer, qpos, cam, fmap):
        dd.qpos[:] = qpos
        mujoco.mj_forward(m, dd)
        renderer.update_scene(dd, camera=cam, scene_option=opt)
        seg = renderer.render()
        ids = seg[..., 0][seg[..., 1] == int(mujoco.mjtObj.mjOBJ_GEOM)]
        c = {f: 0 for f in FACES}
        vals, n = np.unique(ids[np.isin(ids, st_ids)], return_counts=True)
        for g, nn in zip(vals, n):
            c[fmap[int(g)]] += int(nn)
        return c

    cams = []
    for el in EL:
        for az in ([0] if el == -90 else AZ):
            cam = mujoco.MjvCamera()
            cam.type = mujoco.mjtCamera.mjCAMERA_FREE
            cam.lookat[:] = centre
            cam.distance, cam.azimuth, cam.elevation = DIST, az, el
            cams.append(((az, el), cam))
    table = {}                                   # (cam, snap) -> {face: visible fraction or None}
    for si, (label, q) in enumerate(snaps):
        fmap = face_of(q)
        for key, cam in cams:
            occ, free = counts(ren, q, cam, fmap), counts(ren_h, q, cam, fmap)
            table[(key, si)] = {f: (occ[f] / free[f] if free[f] >= 20 else None) for f in FACES}
    # per camera: for each face, the WORST visible fraction over the snapshots (None if the face is edge-on or behind)
    MIN_PIX_FRAC = 0.5

    def worst(key):
        out = {}
        for f in FACES:
            v = [table[(key, si)][f] for si in range(len(snaps))]
            out[f] = None if any(x is None for x in v) else min(v)
        return out
    per_cam = {key: worst(key) for key, _ in cams}
    sees = {key: {f for f, v in w.items() if v is not None and v >= MIN_PIX_FRAC} for key, w in per_cam.items()}
    # greedy set cover of the 6 faces
    chosen, covered = [], set()
    while covered != set(FACES):
        best = max(sees, key=lambda k: (len(sees[k] - covered), sum(per_cam[k][f] or 0 for f in sees[k])))
        gain = sees[best] - covered
        if not gain:
            break
        chosen.append((best, sorted(gain)))
        covered |= gain
    face_best = {f: max(((per_cam[k][f] or 0.0), k) for k in per_cam) for f in FACES}
    res = {"face_names": FACE_NAME, "snapshots": [s[0] for s in snaps], "n_cameras": len(cams), "distance_m": DIST, "image": [W, H],
           "visible_threshold": MIN_PIX_FRAC,
           "best_camera_per_face": {f: {"worst_visible_fraction": round(v, 3), "azimuth_elevation": k}
                                    for f, (v, k) in face_best.items()},
           "greedy_cover": [{"azimuth_elevation": k, "adds_faces": g} for k, g in chosen],
           "uncovered_faces": sorted(set(FACES) - covered),
           "per_camera_worst": {f"{k[0]},{k[1]}": {f: (None if v is None else round(v, 3)) for f, v in w.items()}
                                for k, w in per_cam.items()}}
    (HERE / "results.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("face_names", "snapshots", "best_camera_per_face", "greedy_cover",
                                          "uncovered_faces")},
                     indent=1))


if __name__ == "__main__":
    main()
