"""ER9 part E, reported item: how wrong is the force law for the hybrid's perpendicular near pairs?

The force law gives pairs within near-field range a correction only if they are within 45 deg of parallel; other
pairs get the point-dipole formula alone, and M5 required that none occurs. In a hybrid, anchor magnets of the turning
layer pass corner-edge magnets of the layer below at about 6 mm and about 64 deg (er9_hybrid_pairs.py). For each such
pair this script compares, along a rigid quarter turn of U, the dipole energy the simulation uses with the
charge-model energy (magnets._exact_energy_tilted, the reference the tables were built from), and the torque about
the U axis that each gives (minus the derivative of the energy with respect to the turn angle).
Kinematic only. Usage (WSL, repo root):
    ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9_hybrid_perp.py CLEAR_MM
Writes results/hybrid/perp_c<CLEAR_MM>.json.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("er9_hybrid", HERE / "er9_hybrid.py")
HY = importlib.util.module_from_spec(spec); sys.modules["er9_hybrid"] = HY; spec.loader.exec_module(HY)

from rubiknetic.cube_physics.magnets import TABLE_QUAD, _dipole_energy, _exact_energy_tilted  # noqa: E402

STEP = 1.0


def exact(mp, p1, n1, p2, n2) -> float:
    rv = p2 - p1
    z = float(rv @ n1)
    lat = rv - z * n1
    rho = float(np.linalg.norm(lat))
    ex = lat / rho if rho > 1e-12 else np.cross(n1, [1.0, 0.0, 0.0]) / np.linalg.norm(np.cross(n1, [1.0, 0.0, 0.0]))
    ey = np.cross(n1, ex)
    u = np.array([n2 @ ex, n2 @ ey, n2 @ n1])                       # magnet 2's axis in magnet 1's frame
    R2 = Rotation.align_vectors([u], [[0.0, 0.0, 1.0]])[0].as_matrix()
    return _exact_energy_tilted(mp.diameter / 2, mp.length, mp.moment, rho, z, R2, *TABLE_QUAD)


def main() -> None:
    cfg = HY.cfg_for(float(sys.argv[1]))
    mp, mags = HY.hybrid_mags(cfg)
    body = [g["body"] for g in mags]
    p0 = np.array([g["pos"] for g in mags]); n0 = np.array([g["dir"] for g in mags])
    in_u = np.array([b != "core" and b[-1] == "p" for b in body])
    ii, jj = np.triu_indices(len(mags), 1)
    keep = np.array([body[i] != body[j] for i, j in zip(ii, jj)])
    ii, jj = ii[keep], jj[keep]
    angs = np.arange(0.0, 90.0 + 1e-9, STEP)
    P, N = [], []
    for ang in angs:
        rot = Rotation.from_euler("z", -ang, degrees=True).as_matrix()
        p, n = p0.copy(), n0.copy()
        p[in_u], n[in_u] = p0[in_u] @ rot.T, n0[in_u] @ rot.T
        P.append(p); N.append(n)
    P, N = np.array(P), np.array(N)
    r = np.linalg.norm(P[:, jj] - P[:, ii], axis=2)
    cosn = np.abs(np.einsum("tki,tki->tk", N[:, ii], N[:, jj]))
    bad = (r < mp.r2) & (cosn <= np.cos(np.radians(45)))
    pairs = np.nonzero(bad.any(axis=0))[0]
    ue, ud = np.zeros((len(pairs), len(angs))), np.zeros((len(pairs), len(angs)))
    rows = []
    for q, k in enumerate(pairs):
        i, j = ii[k], jj[k]
        for t in range(len(angs)):
            ud[q, t] = _dipole_energy(mp.moment, P[t, j] - P[t, i], N[t, i], N[t, j])
            ue[q, t] = exact(mp, P[t, i], N[t, i], P[t, j], N[t, j]) if r[t, k] < mp.far_r1 else ud[q, t]
        te, td = -np.gradient(ue[q], np.radians(angs)), -np.gradient(ud[q], np.radians(angs))
        near = bad[:, k]
        rows.append({"pair": f"{mags[i]['kind']}@{body[i]} - {mags[j]['kind']}@{body[j]}",
                     "min_r_mm": float(r[:, k].min() * 1e3), "near_perp_deg": [float(angs[near].min()),
                                                                               float(angs[near].max())],
                     "peak_torque_dipole_mNm": float(np.abs(td[near]).max() * 1e3),
                     "peak_torque_exact_mNm": float(np.abs(te[near]).max() * 1e3),
                     "max_torque_error_mNm": float(np.abs(te - td)[near].max() * 1e3)})
    tot_e, tot_d = -np.gradient(ue.sum(axis=0), np.radians(angs)), -np.gradient(ud.sum(axis=0), np.radians(angs))
    res = {"config": cfg, "n_pairs": len(pairs), "strength_note": "energies scale with cfg scale (moment^2)",
           "sum_over_pairs": {"peak_torque_dipole_mNm": float(np.abs(tot_d).max() * 1e3),
                              "peak_torque_exact_mNm": float(np.abs(tot_e).max() * 1e3),
                              "max_torque_error_mNm": float(np.abs(tot_e - tot_d).max() * 1e3),
                              "angle_of_max_error_deg": float(angs[int(np.argmax(np.abs(tot_e - tot_d)))])},
           "pairs": rows}
    out = HERE / "results" / "hybrid" / f"perp_c{float(sys.argv[1]):g}.json"
    out.write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "pairs"}, indent=1))
    for x in rows:
        print(x)


if __name__ == "__main__":
    main()
