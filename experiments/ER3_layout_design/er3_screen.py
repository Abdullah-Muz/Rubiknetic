"""ER3: static magnet-layout design screen (PROTOCOL.md). No dynamics.
Usage (WSL):  ~/.venvs/rubiknetic/bin/python experiments/ER3_layout_design/er3_screen.py
Writes results/screen.json and prints a markdown report.
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
spec = importlib.util.spec_from_file_location("er2_static", REPO / "experiments/ER2_layout_probe/er2_static.py")
E = importlib.util.module_from_spec(spec); sys.modules["er2_static"] = E; spec.loader.exec_module(E)
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES  # noqa: E402

MG, MP, SPLINE = E.MG, E.MP, E.SPLINE
DLT = np.radians(E.DELTA_DEG)
GAP = E.M5.GAP


# ---- layouts -------------------------------------------------------------------------------------------------------
def face_pair(a, b, pitch, gap, sigma, offset_mm=0.0):
    """ER2's pair (polarity corner->edge, edge->centre); sigma < 0 = repel with |sigma|; optional in-plane offset
    (edge-centre pairs: perpendicular to the edge axis, positive toward the cube's outer surface)."""
    H = E.HOMES
    if np.count_nonzero(H[a]) < np.count_nonzero(H[b]):
        a, b = b, a
    ca, cb = H[a].astype(float), H[b].astype(float)
    e = cb - ca
    h = (pitch - gap) / 2
    depth = h - MP.wall - MP.length / 2
    off = np.zeros(3)
    if offset_mm:
        edge = ca if np.count_nonzero(H[a]) == 2 else cb
        k = [i for i in range(3) if e[i] == 0 and edge[i] != 0][0]
        off[k] = np.sign(edge[k]) * offset_mm * 1e-3
    s = abs(sigma)
    return [{"body": E.NAMES[a], "pos": ca * pitch + e * depth + off, "dir": e.copy(), "sigma": s},
            {"body": E.NAMES[b], "pos": cb * pitch - e * depth + off, "dir": -e if sigma < 0 else e.copy(), "sigma": s}]


def core_pairs(pitch, gap, sigma, kinds=("edge", "corner")):
    out = []
    for n, c in zip(E.NAMES, E.HOMES):
        if E.KIND[n] not in kinds:
            continue
        u = c / np.linalg.norm(c)
        rp = np.linalg.norm(c) * (pitch + gap) / 2
        out.append({"body": n, "pos": u * (rp + MP.wall + MP.length / 2), "dir": u.copy(), "sigma": sigma})
        out.append({"body": "core", "pos": u * (rp - gap - MP.wall - MP.length / 2), "dir": u.copy(), "sigma": sigma})
    return out


def layout(spec_: dict, pitch: float, gap: float) -> list[dict]:
    mags = []
    if spec_.get("ce", 0):
        mags += [m for a, b in E.adjacent(("corner", "edge")) for m in face_pair(a, b, pitch, gap, spec_["ce"])]
    if spec_.get("ec", 0):
        mags += [m for a, b in E.adjacent(("edge", "centre"))
                 for m in face_pair(a, b, pitch, gap, spec_["ec"], spec_.get("ec_offset_mm", 0.0))]
    if spec_.get("core", 0):
        mags += core_pairs(pitch, gap, spec_["core"], tuple(spec_.get("core_kinds", ("edge", "corner"))))
    return mags


# ---- torques with per-magnet strength ------------------------------------------------------------------------------
def torques(rig, mags, mp=MP, spline=SPLINE):
    import mujoco  # noqa: F401
    bid = dict(rig.bid); bid["core"] = mujoco_body(rig, "core")
    b = np.array([bid[g["body"]] for g in mags])
    R = rig.d.xmat[b].reshape(-1, 3, 3)
    p = rig.d.xpos[b] + np.einsum("nij,nj->ni", R, np.array([g["pos"] for g in mags]))
    n = np.einsum("nij,nj->ni", R, np.array([g["dir"] for g in mags]))
    sig = np.array([g["sigma"] for g in mags])
    ii, jj = np.triu_indices(len(mags), 1)
    keep = b[ii] != b[jj]
    ii, jj = ii[keep], jj[keep]
    fac = np.round(sig[ii] * sig[jj], 12)
    F = np.zeros((len(mags), 3)); T = np.zeros((len(mags), 3))
    for f in np.unique(fac):
        k = fac == f
        Fk, Tk, _ = MG.pair_forces(mp, spline, ii[k], jj[k], p, n, None, MG.scatter_matrices(len(mags), ii[k], jj[k]))
        F += f * Fk; T += f * Tk
    tc = T + np.cross(p, F)
    out: dict[str, np.ndarray] = {}
    for k, g in enumerate(mags):
        out[g["body"]] = out.get(g["body"], np.zeros(3)) + tc[k]
    return out


def mujoco_body(rig, name):
    import mujoco
    return mujoco.mj_name2id(rig.m, mujoco.mjtObj.mjOBJ_BODY, name)


def measure(rig, mags, mp=MP, spline=SPLINE, turn_profile=True) -> dict:
    T = lambda: torques(rig, mags, mp, spline)  # noqa: E731
    rig.pose({}); t0 = T()
    res = {"n_magnets": len(mags), "max_aligned_torque_mNm": max(float(np.linalg.norm(v)) * 1e3 for k, v in t0.items()
                                                                 if k != "core"),
           "pieces": {}, "centres": {}, "layers": {}, "modes": {}}
    for nm, c in zip(E.NAMES, E.HOMES):
        if E.KIND[nm] == "centre":
            ax = c.astype(float); tq = []
            for s in (1, -1):
                rig.pose({nm: s * DLT * ax}); tq.append(float(T().get(nm, np.zeros(3)) @ ax))
            res["centres"][nm] = -(tq[0] - tq[1]) / (2 * DLT) * 1e3
            continue
        K = np.zeros((3, 3))
        for a in range(3):
            e = np.eye(3)[a]
            rig.pose({nm: DLT * e}); tp = T().get(nm, np.zeros(3))
            rig.pose({nm: -DLT * e}); tm = T().get(nm, np.zeros(3))
            K[:, a] = -(tp - tm) / (2 * DLT)
        Ks = (K + K.T) / 2 * 1e3
        res["pieces"][nm] = {"kind": E.KIND[nm], "eig": np.linalg.eigvalsh(Ks).tolist(), "K": Ks.tolist()}
        rad = c / np.linalg.norm(c); q = lambda u: float(u @ Ks @ u)  # noqa: E731
        if E.KIND[nm] == "edge":
            along = np.eye(3)[np.nonzero(c == 0)[0][0]]
            sl = np.cross(rad, along); sl /= np.linalg.norm(sl)
            res["modes"][nm] = {"spin": q(rad), "slide": q(sl), "cross": q(along)}
        else:
            t1 = np.cross(rad, [1.0, 0, 0]); t1 /= np.linalg.norm(t1); t2 = np.cross(rad, t1)
            Bm = np.column_stack([t1, t2])
            res["modes"][nm] = {"twist": q(rad), "tangential": np.linalg.eigvalsh(Bm.T @ Ks @ Bm).tolist()}
    for f in FACES:
        nrm = np.array(FACE_NORMAL[f], float)
        mem = [x for x, h in zip(E.NAMES, E.HOMES) if h @ nrm == 1]
        tq = []
        for s in (1, -1):
            rig.pose({x: s * DLT * nrm for x in mem}); Tt = T()
            tq.append(float(sum(Tt.get(x, np.zeros(3)) @ nrm for x in mem)))
        res["layers"][f] = -(tq[0] - tq[1]) / (2 * DLT)
    if turn_profile:
        nrm = np.array(FACE_NORMAL["U"], float)
        mem = [x for x, h in zip(E.NAMES, E.HOMES) if h @ nrm == 1]
        prof = []
        for deg in range(0, 91):
            rig.pose({x: np.radians(deg) * nrm for x in mem}); Tt = T()
            prof.append(float(sum(Tt.get(x, np.zeros(3)) @ nrm for x in mem)))
        res["turn_profile_Nm"] = prof
        res["turn_peak_Nm"] = float(np.max(np.abs(prof)))
    mins = {k: min(min(v["eig"]) for v in res["pieces"].values() if v["kind"] == k) for k in ("edge", "corner")}
    res["min_eig"] = min(mins.values()); res["min_eig_by_kind"] = mins
    res["min_centre"] = min(res["centres"].values())
    res["min_layer"] = min(res["layers"].values())
    mm = lambda key: min(v[key] for v in res["modes"].values() if key in v)  # noqa: E731
    res["mode_min"] = {"edge_spin": mm("spin"), "edge_slide": mm("slide"), "edge_cross": mm("cross"),
                       "corner_twist": mm("twist"),
                       "corner_tangential": min(min(v["tangential"]) for v in res["modes"].values() if "tangential" in v)}
    margins = [(res["min_eig"] + 1) / 100, (res["min_centre"] + 1) / 100, res["min_layer"] - 1.0]
    if turn_profile:
        margins.append((0.5 - res["turn_peak_Nm"]) / 0.5)
    res["passes"] = bool(all(m >= 0 for m in margins))
    res["margin"] = float(min(margins))
    return res


# ---- self-checks ----------------------------------------------------------------------------------------------------
def self_checks(rig) -> dict:
    out = {}
    E.check_l0(); out["V-a"] = "OK"
    mags = layout({"ce": 1}, rig.p.pitch, GAP)
    a = measure(rig, [dict(g, sigma=np.sqrt(0.67)) for g in mags], turn_profile=False)
    mp67 = replace(MP, scale=0.67)
    b = measure(rig, mags, mp67, E.M4._tables_for(mp67), turn_profile=False)
    va = np.array([x for v in a["pieces"].values() for x in v["eig"]] + list(a["layers"].values()))
    vb = np.array([x for v in b["pieces"].values() for x in v["eig"]] + list(b["layers"].values()))
    rel = float(np.max(np.abs(va - vb)) / np.max(np.abs(vb)))
    out["V-b_rel_diff"] = rel
    assert rel <= 0.01, f"V-b failed: {rel}"
    er2 = {r["layout"]: r for r in json.loads((REPO / "experiments/ER2_layout_probe/results/static_screen.json").read_text())["rows"]}
    worst = 0.0
    for lid, sp in (("L0", {"ce": 1}), ("L1", {"ec": 1})):
        m = measure(rig, layout(sp, rig.p.pitch, GAP), turn_profile=False)
        x = np.array([y for k in E.NAMES if k in m["pieces"] for y in m["pieces"][k]["eig"]] + [m["layers"][f] for f in FACES])
        y = np.array([z for k in E.NAMES if k in er2[lid]["pieces"] for z in er2[lid]["pieces"][k]["eig_mNm_per_rad"]]
                     + [er2[lid]["layers"][f] for f in FACES])
        worst = max(worst, float(np.max(np.abs(x - y)) / np.max(np.abs(y))))
    out["V-c_rel_diff"] = worst
    assert worst <= 1e-6, f"V-c failed: {worst}"
    return out


def variants() -> list[tuple[str, dict]]:
    v = []
    grid = [-1, -0.5, 0, 0.5, 1]
    for a, b in itertools.product(grid, grid):
        if a == 0 and b == 0:
            continue
        v.append((f"F1 ce={a:+g} ec={b:+g}", {"ce": a, "ec": b}))
    for off in (-4, -2, 0, 2, 4):
        v.append((f"F2 L1 offset={off:+d}mm", {"ec": 1, "ec_offset_mm": float(off)}))
    for s in (1, 2, 3):
        v.append((f"F3 core={s} alone", {"core": s}))
        v.append((f"F3 core={s} + L0", {"core": s, "ce": 1}))
        v.append((f"F3 core={s} + L1", {"core": s, "ec": 1}))
        v.append((f"F3e core(edges)={s} + L1", {"core": s, "ec": 1, "core_kinds": ["edge"]}))
    return v


if __name__ == "__main__":
    rig = E.Rig(GAP)
    checks = self_checks(rig)
    print("self-checks:", checks)
    rows = []
    for name, sp in variants():
        r = measure(rig, layout(sp, rig.p.pitch, GAP))
        r.update({"variant": name, "spec": sp})
        rows.append(r)
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "screen.json").write_text(json.dumps({"env": E.D10.environment(), "self_checks": checks,
                                                               "rows": rows}, indent=1))
    print("| variant | magnets | edge spin / slide / cross | corner twist / tangential | min eig | min centre | "
          "layer N m/rad | U-turn peak N m | screen | margin |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        m = r["mode_min"]
        print(f"| {r['variant']} | {r['n_magnets']} | {m['edge_spin']:+.0f} / {m['edge_slide']:+.0f} / {m['edge_cross']:+.0f} | "
              f"{m['corner_twist']:+.0f} / {m['corner_tangential']:+.0f} | {r['min_eig']:+.0f} | {r['min_centre']:+.0f} | "
              f"{r['min_layer']:+.3f} | {r['turn_peak_Nm']:.3f} | {'PASS' if r['passes'] else 'fail'} | {r['margin']:+.3f} |")
