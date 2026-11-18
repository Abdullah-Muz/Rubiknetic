"""ER2 part O1: static magnet-stiffness screen of candidate layouts (PROTOCOL.md). No dynamics.

For each layout: net magnet torque about the cube centre at the aligned pose; per-piece 3x3 rotational stiffness
(smallest eigenvalue); centre spin stiffness; whole-layer stiffness. Uses magnets.pair_forces with M5's near-field
tables. Writes results/static_screen.json and prints a table.
Usage (WSL):  ~/.venvs/rubiknetic/bin/python experiments/ER2_layout_probe/er2_static.py
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import sys
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
spec = importlib.util.spec_from_file_location("d10_rest", REPO / "experiments/D10_m5_rest_diagnostic/d10_rest.py")
D10 = importlib.util.module_from_spec(spec); sys.modules["d10_rest"] = D10; spec.loader.exec_module(D10)
M5 = D10._load_m5(); M4 = M5.M4
from rubiknetic.cube_logic import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES  # noqa: E402
from rubiknetic.cube_physics import magnets as MG  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml, cubie_name  # noqa: E402

DELTA_DEG = 0.02
MP = M5.magnet_params_for({})
SPLINE = M4._tables_for(MP)
HOMES = [np.array(h) for h in HOME_POSITIONS]
NAMES = [cubie_name(h) for h in HOME_POSITIONS]
KIND = {n: {1: "centre", 2: "edge", 3: "corner"}[int(np.count_nonzero(h))] for n, h in zip(NAMES, HOMES)}


def pair_magnets(a: int, b: int, pitch: float, gap: float, repel: bool) -> list[dict]:
    """One magnet in each of two face-adjacent pieces, on the shared face centres (magnets.layout's placement)."""
    h = (pitch - gap) / 2
    ca, cb = HOMES[a].astype(float), HOMES[b].astype(float)
    e = cb - ca
    depth = h - MP.wall - MP.length / 2
    return [{"body": NAMES[a], "pos": ca * pitch + e * depth, "dir": e.copy()},
            {"body": NAMES[b], "pos": cb * pitch - e * depth, "dir": -e if repel else e.copy()}]


def adjacent(kinds: tuple[str, str]) -> list[tuple[int, int]]:
    out = []
    for a, b in itertools.combinations(range(26), 2):
        if np.abs(HOMES[a] - HOMES[b]).sum() == 1 and {KIND[NAMES[a]], KIND[NAMES[b]]} == set(kinds):
            out.append((a, b))
    return out


def build_layout(lid: str, pitch: float, gap: float) -> list[dict]:
    ce, ec = adjacent(("corner", "edge")), adjacent(("edge", "centre"))
    if lid in ("L0", "L0-g025"):
        return [m for a, b in ce for m in pair_magnets(a, b, pitch, gap, False)]
    if lid == "L1":
        return [m for a, b in ec for m in pair_magnets(a, b, pitch, gap, False)]
    if lid == "L2":
        return build_layout("L0", pitch, gap) + build_layout("L1", pitch, gap)
    if lid == "L3":
        return [m for a, b in ce for m in pair_magnets(a, b, pitch, gap, True)]
    if lid == "L4":
        return build_layout("L1", pitch, gap) + build_layout("L3", pitch, gap)
    raise ValueError(lid)


class Rig:
    """Aligned M5 model at a given piece gap; magnet torques about the cube centre for a magnet list."""

    def __init__(self, gap: float):
        self.p = M1Params(**{**M4.BASE_OVERRIDES, "gap": gap})
        self.m = mujoco.MjModel.from_xml_string(build_m1_xml(self.p))
        self.d = mujoco.MjData(self.m)
        self.bid = {n: mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_BODY, n) for n in NAMES}
        self.jid = {n: mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_JOINT, n + "_j") for n in NAMES}

    def pose(self, moves: dict[str, np.ndarray]) -> None:
        """moves: piece name -> rotation vector (rad) applied about the cube centre (hinge: axis component only)."""
        mujoco.mj_resetData(self.m, self.d)
        for n, rv in moves.items():
            j = self.jid[n]; adr = self.m.jnt_qposadr[j]
            ang = float(np.linalg.norm(rv))
            if ang == 0.0:
                continue
            if self.m.jnt_type[j] == mujoco.mjtJoint.mjJNT_BALL:
                q = np.zeros(4); mujoco.mju_axisAngle2Quat(q, rv / ang, ang)
                qn = np.zeros(4); mujoco.mju_mulQuat(qn, q, self.d.qpos[adr:adr + 4].copy()); self.d.qpos[adr:adr + 4] = qn
            else:
                self.d.qpos[adr] += float(np.dot(self.m.jnt_axis[j], rv))
        mujoco.mj_kinematics(self.m, self.d)

    def torques(self, mags: list[dict]) -> dict[str, np.ndarray]:
        b = np.array([self.bid[g["body"]] for g in mags])
        R = self.d.xmat[b].reshape(-1, 3, 3)
        p = self.d.xpos[b] + np.einsum("nij,nj->ni", R, np.array([g["pos"] for g in mags]))
        n = np.einsum("nij,nj->ni", R, np.array([g["dir"] for g in mags]))
        ii, jj = np.triu_indices(len(mags), 1)
        keep = b[ii] != b[jj]
        ii, jj = ii[keep], jj[keep]
        F, T, _ = MG.pair_forces(MP, SPLINE, ii, jj, p, n, None, MG.scatter_matrices(len(mags), ii, jj))
        tc = T + np.cross(p - self.d.xpos[b], F) + np.cross(self.d.xpos[b], F)   # about the cube centre
        out: dict[str, np.ndarray] = {}
        for k, g in enumerate(mags):
            out[g["body"]] = out.get(g["body"], np.zeros(3)) + tc[k]
        return out


def screen(lid: str, gap: float) -> dict:
    rig = Rig(gap)
    mags = build_layout(lid, rig.p.pitch, gap)
    dlt = np.radians(DELTA_DEG)
    rig.pose({})
    t0 = rig.torques(mags)
    res = {"layout": lid, "gap_mm": gap * 1e3, "n_magnets": len(mags),
           "max_aligned_torque_mNm": max((float(np.linalg.norm(v)) * 1e3 for v in t0.values()), default=0.0),
           "pieces": {}, "centres": {}, "layers": {}}
    for n in NAMES:
        if KIND[n] == "centre":
            ax = np.array(HOMES[NAMES.index(n)], float)
            tq = []
            for s in (1, -1):
                rig.pose({n: s * dlt * ax}); tq.append(float(rig.torques(mags).get(n, np.zeros(3)) @ ax))
            res["centres"][n] = -(tq[0] - tq[1]) / (2 * dlt) * 1e3
            continue
        K = np.zeros((3, 3))
        for a in range(3):
            e = np.eye(3)[a]
            tp, tm = [], []
            rig.pose({n: dlt * e}); tp = rig.torques(mags).get(n, np.zeros(3))
            rig.pose({n: -dlt * e}); tm = rig.torques(mags).get(n, np.zeros(3))
            K[:, a] = -(tp - tm) / (2 * dlt)
        Ks = (K + K.T) / 2 * 1e3
        res["pieces"][n] = {"kind": KIND[n], "eig_mNm_per_rad": np.linalg.eigvalsh(Ks).tolist(), "K": Ks.tolist()}
    for f in FACES:
        nrm = np.array(FACE_NORMAL[f], float)
        members = [nm for nm, h in zip(NAMES, HOMES) if h @ nrm == 1]
        tq = []
        for s in (1, -1):
            rig.pose({nm: s * dlt * nrm for nm in members})
            T = rig.torques(mags)
            tq.append(float(sum(T.get(nm, np.zeros(3)) @ nrm for nm in members)))
        res["layers"][f] = -(tq[0] - tq[1]) / (2 * dlt)        # N m / rad
    mins = [min(v["eig_mNm_per_rad"]) for v in res["pieces"].values()]
    res["min_piece_eig_mNm_per_rad"] = min(mins)
    res["min_piece_eig_by_kind"] = {k: min(min(v["eig_mNm_per_rad"]) for v in res["pieces"].values() if v["kind"] == k)
                                    for k in ("edge", "corner")}
    res["min_centre_mNm_per_rad"] = min(res["centres"].values())
    res["min_layer_Nm_per_rad"] = min(res["layers"].values())
    res["passes_screen"] = bool(res["min_piece_eig_mNm_per_rad"] >= -1.0 and res["min_centre_mNm_per_rad"] >= -1.0
                                and res["min_layer_Nm_per_rad"] >= 1.0)
    return res


def check_l0() -> float:
    """L0 rebuilt here must equal magnets.layout (same bodies, positions, directions)."""
    p = M1Params(**{**M4.BASE_OVERRIDES, "gap": M5.GAP})
    ref = MG.layout(p.pitch, p.gap, MP)
    mine = build_layout("L0", p.pitch, p.gap)
    key = lambda g: (g["body"], tuple(np.round(g["pos"], 9)), tuple(np.round(g["dir"], 9)))  # noqa: E731
    assert sorted(map(key, ref)) == sorted(map(key, mine)), "L0 differs from magnets.layout"
    return 0.0


if __name__ == "__main__":
    check_l0()
    print("L0 rebuilt here == magnets.layout: OK")
    rows = [screen(l, M5.GAP) for l in ("L0", "L1", "L2", "L3", "L4")] + [screen("L0-g025", 2.5e-5)]
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "static_screen.json").write_text(json.dumps({"env": D10.environment(), "delta_deg": DELTA_DEG,
                                                                      "rows": rows}, indent=1))
    print("| layout | gap mm | magnets | max aligned torque mN m | min piece eig (edge / corner) mN m/rad | "
          "min centre mN m/rad | layer N m/rad (min..max) | screen |")
    print("|---|---|---|---|---|---|---|---|")
    for r in rows:
        lay = list(r["layers"].values())
        print(f"| {r['layout']} | {r['gap_mm']:.3f} | {r['n_magnets']} | {r['max_aligned_torque_mNm']:.2e} | "
              f"{r['min_piece_eig_by_kind']['edge']:+.1f} / {r['min_piece_eig_by_kind']['corner']:+.1f} | "
              f"{r['min_centre_mNm_per_rad']:+.1f} | {min(lay):+.3f}..{max(lay):+.3f} | "
              f"{'PASS' if r['passes_screen'] else 'fail'} |")
