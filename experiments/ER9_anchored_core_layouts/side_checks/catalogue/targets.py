"""Target numbers per simulated ER9 arm: pull, axial and lateral stiffness of ONE coaxial anchor pair at home.

Two evaluations per arm:
  (A) "sim": the repo force law (magnets.pair_forces with the arm's near-field table), as er9_hybrid_scale.py does.
      This is what the simulation applied.
  (B) "charge": the ideal charge model for the same magnet with Br_eff = Br * sqrt(scale) (cyl_pair.py, independent).
Checks: scale.json reproduced; (A) = (B) below r1 = 5 mm; repo quadrature (_exact_energy_tilted) vs cyl_pair;
how MagnetParams.scale enters.
Reads the repo (src and one JSON); writes only next to this file. Run with python -B.
Usage: ~/.venvs/rubiknetic/bin/python -B targets.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = Path("/mnt/c/dev/Rubiknetic")
sys.path.insert(0, str(HERE))

from rubiknetic.cube_physics import magnets as MG  # noqa: E402
from rubiknetic.cube_physics.magnets import MagnetParams, near_field_tables, pair_forces  # noqa: E402

import cyl_pair as CP  # noqa: E402

TABLES = HERE / "tables_copy"       # copies of the repo's tables (the repo folders are not touched)
WALL = 0.0004
ARMS = {  # name: (scale, clearance mm)
    "W1": (1.0, 0.2), "W2": (0.5, 0.2), "W3": (0.3, 0.2),
    "HB1": (0.756, 1.0), "HB2": (0.756, 2.0), "HB3": (0.756, 3.0),
}


def splines(mp: MagnetParams):
    name = f"tilt_{mp.diameter*1e3:g}x{mp.length*1e3:g}_{mp.br:g}T_s{mp.scale:g}_r{mp.r2*1e3:g}_h1.5_q16x48.npz"
    path = TABLES / name
    assert path.exists(), f"no table copy {name}: refusing to build one (minutes of CPU)"
    with np.load(path) as f:
        assert np.array_equal(f["rho"], np.linspace(0.0, mp.r2 + 0.001, 37))
        assert np.array_equal(f["z"], np.linspace(mp.length + 0.0001, mp.r2 + 0.001, 31))
    return near_field_tables(mp, TABLES)


def force(mp, spl, D: float, lateral: float = 0.0) -> np.ndarray:
    p = np.array([[0.0, 0.0, 0.0], [lateral, 0.0, D]])
    n = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]])
    return np.asarray(pair_forces(mp, spl, np.array([0]), np.array([1]), p, n)[0])[1]


def sim_pair(mp, spl, D: float, h: float = 1e-5) -> dict:
    f0 = force(mp, spl, D)
    kz = (force(mp, spl, D + h)[2] - force(mp, spl, D - h)[2]) / (2 * h)
    kx = (force(mp, spl, D, h)[0] - force(mp, spl, D, -h)[0]) / (2 * h)
    return {"pull_N": float(-f0[2]), "kz_N_per_m": float(kz), "klat_N_per_m": float(-kx)}


def main() -> None:
    t0 = time.time()
    out: dict = {"conventions": "pull > 0 attraction; kz = dFz/dD > 0 (attraction falls as the gap opens: axially "
                                "unstable); klat = -dFx/dx > 0 (restoring). Charge model: klat = kz / 2 exactly."}

    # ---- (a) how scale enters
    m1, m03 = MagnetParams(0.004, 0.003, "N35", scale=1.0), MagnetParams(0.004, 0.003, "N35", scale=0.3)
    s1, s03 = splines(m1), splines(m03)
    f1, f03 = force(m1, s1, 0.004)[2], force(m03, s03, 0.004)[2]
    with np.load(TABLES / "tilt_4x3_1.19T_s1_r8_h1.5_q16x48.npz") as a, \
            np.load(TABLES / "tilt_4x3_1.19T_s0.3_r8_h1.5_q16x48.npz") as b:
        tab_ratio = float(np.max(np.abs(b["C0"] / a["C0"] - 0.3)))
    out["scale_check"] = {"moment_ratio_s0.3_over_s1": m03.moment / m1.moment, "sqrt_0.3": float(np.sqrt(0.3)),
                          "pair_force_ratio_s0.3_over_s1": float(f03 / f1),
                          "table_C0_ratio_minus_0.3_max_abs": tab_ratio,
                          "Br_eff_T": {str(s): MG.GRADES_BR["N35"] * float(np.sqrt(s)) for s in (1.0, 0.756, 0.5, 0.3)}}

    # ---- (f) scale.json reproduced (its method: scale-1 table times the fitted scale 0.75615...)
    ref = json.loads((REPO / "experiments/ER9_anchored_core_layouts/results/hybrid/scale.json").read_text())
    sc = ref["matching_scale"]
    rep = {}
    for c_mm, r in ref["anchor_pair_4x3_N35_at_matching_scale"].items():
        D = float(c_mm) * 1e-3 + 2 * WALL + 0.003
        g = sim_pair(m1, s1, D)
        rep[c_mm] = {"pull_here": -g["pull_N"] * sc, "pull_json": r["pull_N"],
                     "klat_here": -g["klat_N_per_m"] * sc, "klat_json": r["lateral_stiffness_N_per_m"],
                     "rel_diff_pull": g["pull_N"] * sc / -r["pull_N"] - 1,
                     "rel_diff_klat": g["klat_N_per_m"] * sc / -r["lateral_stiffness_N_per_m"] - 1}
    out["scale_json_check"] = rep
    m42 = MagnetParams(0.004, 0.002, "N35")
    f5 = force(m42, splines(m42), 0.00085 + 0.002)[2]
    f43 = force(m1, s1, 0.00085 + 0.003)[2]
    out["scale_json_check"]["m5_4x2_pull"] = {"here": float(f5), "json": ref["m5_4x2_N35_pull_N"]}
    out["scale_json_check"]["4x3_pull"] = {"here": float(f43), "json": ref["4x3_N35_pull_N"]}
    out["scale_json_check"]["matching_scale"] = {"here": float(f5 / f43), "json": sc}

    # ---- (b) targets per arm
    out["arms"] = {}
    for arm, (scale, c_mm) in ARMS.items():
        mp = MagnetParams(0.004, 0.003, "N35", scale=scale)
        spl = splines(mp)
        gap = c_mm * 1e-3 + 2 * WALL
        D = gap + mp.length
        sim = sim_pair(mp, spl, D)
        br_eff = mp.br * float(np.sqrt(scale))
        ch = CP.pair(0.004, 0.003, br_eff, gap)
        w = float(MG._cutoff(np.array([D]), mp.r1, mp.r2)[0][0])
        out["arms"][arm] = {"scale": scale, "clearance_mm": c_mm, "face_gap_mm": gap * 1e3,
                            "centre_distance_mm": D * 1e3, "Br_eff_T": br_eff, "near_field_weight_w": w,
                            "sim": sim, "charge": {k: ch[k] for k in ("pull_N", "kz_N_per_m", "klat_N_per_m",
                                                                      "energy_mJ")},
                            "sim_over_charge": {k: sim[k] / ch[k] for k in sim},
                            "sim_klat_over_kz": sim["klat_N_per_m"] / sim["kz_N_per_m"]}

    # ---- cross-check of cyl_pair against the repo's own charge-model quadrature (finer than the tables' 16 x 48)
    chk = []
    for (dia, L, br, gap) in ((0.004, 0.003, 1.19, 0.001), (0.004, 0.003, 1.19, 0.0028), (0.003, 0.002, 1.30, 0.0015)):
        a, D, h = dia / 2, gap + L, 5e-5
        m = (br / MG.MU0) * np.pi * a * a * L
        E = lambda rho, z: MG._exact_energy_tilted(a, L, m, rho, z, np.eye(3), 24, 64)  # noqa: E731
        e0, ep, em, ex = E(0.0, D), E(0.0, D + h), E(0.0, D - h), E(h, D)
        quad = {"pull_N": (ep - em) / (2 * h), "kz_N_per_m": -(ep - 2 * e0 + em) / h ** 2,
                "klat_N_per_m": 2 * (ex - e0) / h ** 2, "energy_mJ": e0 * 1e3}
        mine = CP.pair(dia, L, br, gap)
        chk.append({"magnet": f"{dia*1e3:g}x{L*1e3:g} Br {br} gap {gap*1e3:g} mm", "repo_quadrature_fd": quad,
                    "cyl_pair": {k: mine[k] for k in quad},
                    "rel_diff": {k: quad[k] / mine[k] - 1 for k in quad}})
    out["charge_model_cross_check"] = chk
    # Laplace check inside cyl_pair: klat from the lateral force slope against kz / 2
    r = 1e-5
    fx = CP.lateral_force(0.004, 0.003, 1.19, 0.001, np.array([r]))[0]
    out["laplace_check"] = {"klat_from_lateral_force": fx / r, "kz_over_2": CP.pair(0.004, 0.003, 1.19, 0.001)["klat_N_per_m"]}
    out["dipole_far_check"] = {"gap_30mm_charge_pull": CP.pair(0.004, 0.003, 1.19, 0.030)["pull_N"],
                               "gap_30mm_dipole_pull": CP.dipole_pull(0.004, 0.003, 1.19, 0.030)}
    out["wall_s"] = time.time() - t0
    (HERE / "targets.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
