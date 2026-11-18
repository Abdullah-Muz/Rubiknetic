"""ER6: static screen of real-radius core magnets plus a no-intersection sweep (PROTOCOL.md). Unscored.
Usage (WSL):  ~/.venvs/rubiknetic/bin/python experiments/ER6_real_placement_screen/er6_screen.py
Writes results/screen.json and results/sweep.json and prints a markdown report.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


E3 = _load("er3_screen", "experiments/ER3_layout_design/er3_screen.py")
E5 = _load("er5_checks", "experiments/ER5_magnet_validation/er5_checks.py")
E = E3.E                                                     # ER2 machinery (Rig, NAMES, HOMES, KIND, D10)
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES  # noqa: E402
from rubiknetic.cube_physics.magnets import GRADES_BR, MagnetParams, near_field_tables  # noqa: E402

MP43 = MagnetParams(diameter=0.004, length=0.003, grade="N35")
GAP = E3.GAP
GRADES = ("N35", "N42", "N52")
CLEARS = (1e-4, 2e-4, 3e-4)
H_SAMPLE = 5e-5
DERATE = 1.5
B1_REF = {"edge_slide": 522, "edge_cross": 490, "corner_tangential": 743, "layer": 3.01, "peak": 0.285}


# ---- layouts --------------------------------------------------------------------------------------------------------
def core_layout(mp: MagnetParams, placement: str, clear: float, sigma: float = 1.0) -> list[dict]:
    """placement 'real': R from ER5 (22.04 / 21.95 mm), core clearance `clear`; 'B1': ER5's B1 placement."""
    out = []
    for n, c in zip(E.NAMES, E.HOMES):
        kind = E.KIND[n]
        if kind == "centre":
            continue
        u = c / np.linalg.norm(c)
        if placement == "real":
            r_piece, r_core = E5.R_REAL[kind], E5.R_REAL[kind] - clear
        else:
            r_piece = np.linalg.norm(c) * (E5.PITCH + E5.GAP_B1) / 2
            r_core = r_piece - E5.GAP_B1
        out.append({"body": n, "pos": u * (r_piece + mp.wall + mp.length / 2), "dir": u.copy(), "sigma": sigma})
        out.append({"body": "core", "pos": u * (r_core - mp.wall - mp.length / 2), "dir": u.copy(), "sigma": sigma})
    return out


# ---- tables ---------------------------------------------------------------------------------------------------------
def load_tables() -> tuple:
    tdir = REPO / "experiments/ER5_magnet_validation/tables"
    rec = json.loads((REPO / "experiments/ER5_magnet_validation/results/er5_4x3_N35.json").read_text())["tables_sha256"]
    assert len(rec) == 1, rec
    (fname, sha), = rec.items()
    f = tdir / fname
    assert f.exists(), f"missing ER5 table {f} (regenerate with er5_checks.py 4x3_N35)"
    got = hashlib.sha256(f.read_bytes()).hexdigest()
    s2 = {"file": fname, "sha256": got, "recorded": sha, "pass": got == sha}
    assert s2["pass"], f"S2 failed: {s2}"
    return near_field_tables(MP43, tdir), s2


# ---- geometry sweep -------------------------------------------------------------------------------------------------
def surface_samples(a: float, L: float, h: float = H_SAMPLE) -> np.ndarray:
    """Points on a cylinder's surface (axis z, centred), spacing <= h."""
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
    z = axis / np.linalg.norm(axis)
    x = np.cross(z, [1.0, 0, 0] if abs(z[0]) < 0.9 else [0, 1.0, 0]); x /= np.linalg.norm(x)
    return np.column_stack([x, np.cross(z, x), z])


def signed_dist(pts: np.ndarray, c: np.ndarray, axis: np.ndarray, a: float, L: float) -> np.ndarray:
    d = pts - c
    z = d @ axis
    r = np.linalg.norm(d - np.outer(z, axis), axis=1)
    dz, dr = np.abs(z) - L / 2, r - a
    out = np.hypot(np.maximum(dz, 0), np.maximum(dr, 0))
    inside = (dz <= 0) & (dr <= 0)
    out[inside] = np.maximum(dz, dr)[inside]
    return out


def clearance(c1, n1, c2, n2, a, L, S) -> float:
    p1 = c1 + S @ frame(n1).T
    p2 = c2 + S @ frame(n2).T
    return float(min(signed_dist(p1, c2, n2, a, L).min(), signed_dist(p2, c1, n1, a, L).min()))


def world(rig, mags, core_id):
    b = np.array([core_id if g["body"] == "core" else rig.bid[g["body"]] for g in mags])
    R = rig.d.xmat[b].reshape(-1, 3, 3)
    p = rig.d.xpos[b] + np.einsum("nij,nj->ni", R, np.array([g["pos"] for g in mags]))
    n = np.einsum("nij,nj->ni", R, np.array([g["dir"] for g in mags]))
    return p, n, b


def sweep(rig, mags, mp, faces=FACES, degs=range(-90, 91)) -> dict:
    a, L = mp.diameter / 2, mp.length
    S = surface_samples(a, L)
    cutoff = 2 * np.hypot(a, L / 2) + 5e-4
    core_id = E3.mujoco_body(rig, "core")
    worst = {"clearance_mm": np.inf}
    n_checked = 0
    per_face = {}
    for f in faces:
        nrm = np.array(FACE_NORMAL[f], float)
        mem = [x for x, h in zip(E.NAMES, E.HOMES) if h @ nrm == 1]
        fmin = np.inf
        for deg in degs:
            rig.pose({x: np.radians(deg) * nrm for x in mem})
            p, n, b = world(rig, mags, core_id)
            ii, jj = np.triu_indices(len(mags), 1)
            k = (b[ii] != b[jj]) & (np.linalg.norm(p[ii] - p[jj], axis=1) < cutoff)
            for i, j in zip(ii[k], jj[k]):
                cl = clearance(p[i], n[i], p[j], n[j], a, L, S)
                n_checked += 1
                fmin = min(fmin, cl)
                if cl < worst["clearance_mm"] / 1e3:
                    worst = {"clearance_mm": cl * 1e3, "face": f, "deg": deg,
                             "pair": [mags[i]["body"], mags[j]["body"]]}
        per_face[f] = fmin * 1e3
    worst["clearance_mm"] = float(worst["clearance_mm"])
    return {"min_clearance_mm": worst["clearance_mm"], "worst": worst, "per_face_min_mm": per_face,
            "pairs_checked": n_checked, "pass": bool(worst["clearance_mm"] > 0)}


# ---- self-checks ----------------------------------------------------------------------------------------------------
def s1(rig) -> dict:
    ref = [r for r in json.loads((REPO / "experiments/ER3_layout_design/results/screen.json").read_text())["rows"]
           if r["variant"] == "F3 core=2 alone"][0]
    m = E3.measure(rig, E3.layout({"core": 2}, rig.p.pitch, GAP))
    a = np.array([m["min_eig"], m["min_layer"], m["turn_peak_Nm"], *m["mode_min"].values()])
    b = np.array([ref["min_eig"], ref["min_layer"], ref["turn_peak_Nm"], *ref["mode_min"].values()])
    rel = float(np.max(np.abs(a - b)) / np.max(np.abs(b)))
    assert rel <= 1e-9, f"S1 failed: {rel}"
    return {"rel_diff": rel, "pass": True}


def s3(rig) -> dict:
    r = sweep(rig, core_layout(MP43, "B1", 0.0), MP43, faces=("U",))
    assert r["min_clearance_mm"] < 0, f"S3 failed: positive control found no intersection: {r}"
    return {**r, "pass": True}


def s4() -> dict:
    a, L = MP43.diameter / 2, MP43.length
    S = surface_samples(a, L)
    z = np.array([0, 0, 1.0])
    coax = clearance(np.zeros(3), z, np.array([0, 0, L + 1e-3]), z, a, L, S) * 1e3
    side = clearance(np.zeros(3), z, np.array([2 * a + 5e-4, 0, 0]), z, a, L, S) * 1e3
    ok = abs(coax - 1.0) <= 0.02 and abs(side - 0.5) <= 0.02
    assert ok, f"S4 failed: coaxial {coax}, side {side}"
    return {"coaxial_mm": coax, "side_mm": side, "n_samples": len(S), "pass": True}


# ---- main -----------------------------------------------------------------------------------------------------------
def main():
    rig = E.Rig(GAP)
    spline, s2 = load_tables()
    checks = {"S1": s1(rig), "S2": s2, "S3": s3(rig), "S4": s4()}
    print("self-checks:", json.dumps({k: {kk: v[kk] for kk in v if kk in ("pass", "rel_diff", "min_clearance_mm",
                                                                        "coaxial_mm", "side_mm", "worst")}
                                      for k, v in checks.items()}), flush=True)
    rows = []
    for g in GRADES:
        sig = GRADES_BR[g] / GRADES_BR["N35"]
        for c in CLEARS:
            r = E3.measure(rig, core_layout(MP43, "real", c, sig), MP43, spline)
            der = {"min_layer": r["min_layer"] / DERATE, "turn_peak_Nm": r["turn_peak_Nm"] / DERATE,
                   "mode_min": {k: v / DERATE for k, v in r["mode_min"].items()}}
            der["layer_ok"] = bool(der["min_layer"] >= 1.0)
            r.update({"variant": f"{g} c={c * 1e3:.1f}mm", "grade": g, "sigma": sig, "clear_mm": c * 1e3,
                      "derated_1_5": der})
            rows.append(r)
            print(f"  screened {r['variant']}", flush=True)
    sweeps = {f"{c * 1e3:.1f}": sweep(rig, core_layout(MP43, "real", c), MP43) for c in CLEARS}
    out = HERE / "results"; out.mkdir(exist_ok=True)
    env = E.D10.environment()
    (out / "screen.json").write_text(json.dumps({"env": env, "self_checks": checks, "rows": rows}, indent=1,
                                                default=float))
    (out / "sweep.json").write_text(json.dumps({"env": env, "sample_spacing_mm": H_SAMPLE * 1e3, "sweeps": sweeps},
                                               indent=1, default=float))
    print("\n| variant | edge spin / slide / cross (mN m/rad) | corner twist / tangential | min eig | layer N m/rad | "
          "U-turn peak N m | screen | margin | derated /1.5: slide / cross / tang, layer, layer >= 1 |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        m, d = r["mode_min"], r["derated_1_5"]
        dm = d["mode_min"]
        print(f"| {r['variant']} | {m['edge_spin']:+.0f} / {m['edge_slide']:+.0f} / {m['edge_cross']:+.0f} | "
              f"{m['corner_twist']:+.0f} / {m['corner_tangential']:+.0f} | {r['min_eig']:+.0f} | {r['min_layer']:+.3f} | "
              f"{r['turn_peak_Nm']:.3f} | {'PASS' if r['passes'] else 'fail'} | {r['margin']:+.3f} | "
              f"{dm['edge_slide']:+.0f} / {dm['edge_cross']:+.0f} / {dm['corner_tangential']:+.0f}, "
              f"{d['min_layer']:.3f}, {d['layer_ok']} |")
    print(f"| B1 core sigma=2 (ER3, reference) | 0 / +{B1_REF['edge_slide']} / +{B1_REF['edge_cross']} | "
          f"0 / +{B1_REF['corner_tangential']} | | +{B1_REF['layer']} | {B1_REF['peak']} | | | |")
    print("\n| clearance c | min magnet clearance over all face turns (mm) | worst pair, pose | pairs checked | sweep |")
    print("|---|---|---|---|---|")
    for c, s in sweeps.items():
        w = s["worst"]
        print(f"| {c} mm | {s['min_clearance_mm']:.3f} | {w.get('pair')} at {w.get('face')} {w.get('deg')} deg | "
              f"{s['pairs_checked']} | {'PASS' if s['pass'] else 'FAIL'} |")


if __name__ == "__main__":
    main()
