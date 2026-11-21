"""Catalogue scan: which real cylinder magnet (size, grade) at which face gap reproduces one anchor pair of each arm.

Ideal charge model (cyl_pair.py). Targets from targets.json: the simulated force-law values ("sim") and, where the
force law differs from the charge model (HB2, HB3: pair inside the near-field taper), the charge-model values too.
For every arm x size x grade:
  g_star  face gap in [1.0, 4.0] mm at which the pull equals the target; stiffness differences there;
  window  the gap range over which the pull stays within +-10 % of the target.
For every arm x size: the (gap, Br) at which pull AND lateral stiffness both match ("double match").
Usage: ~/.venvs/rubiknetic/bin/python -B scan.py        (numpy / scipy only; no repo import)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cyl_pair as CP  # noqa: E402

# Br (T): (min, nominal, max). Ranges: supermagnete "Physical magnet data" table (read 2026-11-20). Nominal: the
# repo's GRADES_BR where it has the grade (N35, N42, N45, N52), else the middle of the range.
GRADES = {"N35": (1.17, 1.19, 1.21), "N38": (1.22, 1.24, 1.26), "N40": (1.26, 1.275, 1.29), "N42": (1.29, 1.30, 1.32),
          "N45": (1.32, 1.35, 1.37), "N48": (1.37, 1.395, 1.42), "N50": (1.40, 1.43, 1.46), "N52": (1.42, 1.455, 1.47)}
SIZES = [(2, 1), (2, 2), (3, 1), (3, 1.5), (3, 2), (3, 3), (4, 1), (4, 1.5), (4, 2), (4, 3)]
G_LO, G_HI = 1.0e-3, 4.0e-3


def q(d_mm, l_mm, br, gap):
    return CP.pair(d_mm * 1e-3, l_mm * 1e-3, br, gap)


def qp(d_mm, l_mm, br, gap):
    return {"pull_N": CP.pull(d_mm * 1e-3, l_mm * 1e-3, br, gap)}


def gap_for_pull(d_mm, l_mm, br, pull):
    f = lambda g: CP.pull(d_mm * 1e-3, l_mm * 1e-3, br, g) - pull  # noqa: E731
    lo, hi = 0.6e-3, 8e-3                                 # search wider than the reported range; flag if outside
    if f(lo) < 0 or f(hi) > 0:
        return None
    return brentq(f, lo, hi, xtol=1e-9)


def peak_lateral(d_mm, l_mm, br, gap):
    rho = np.linspace(0.6e-3, 4.2e-3, 10)             # 0.4 mm steps, then a parabola through the top three
    f = CP.lateral_force(d_mm * 1e-3, l_mm * 1e-3, br, gap, rho)
    i = int(np.clip(np.argmax(f), 1, len(rho) - 2))
    c2, c1, c0 = np.polyfit(rho[i - 1:i + 2], f[i - 1:i + 2], 2)
    x = -c1 / (2 * c2)
    return float(c0 - c1 * c1 / (4 * c2)), float(x * 1e3)


def main() -> None:
    tg = json.loads((HERE / "targets.json").read_text())["arms"]
    targets = {}
    for arm, a in tg.items():
        targets[arm] = dict(a["sim"], gap_mm=a["face_gap_mm"], Br_eff=a["Br_eff_T"], kind="sim")
        if abs(a["sim_over_charge"]["pull_N"] - 1) > 0.02 or abs(a["sim_over_charge"]["klat_N_per_m"] - 1) > 0.02:
            targets[arm + "_charge"] = dict({k: a["charge"][k] for k in ("pull_N", "kz_N_per_m", "klat_N_per_m")},
                                            gap_mm=a["face_gap_mm"], Br_eff=a["Br_eff_T"], kind="charge")
    out = {"grades_Br_T_min_nom_max": GRADES, "targets": {}, "rows": [], "double_match": [], "grid": []}

    # reference: peak lateral force and energy of each target pair (charge model of the scaled 4x3 magnet)
    for arm, t in targets.items():
        pk, at = peak_lateral(4, 3, t["Br_eff"], t["gap_mm"] * 1e-3)
        ref = q(4, 3, t["Br_eff"], t["gap_mm"] * 1e-3)
        t.update(peak_lateral_N=pk, peak_at_mm=at, energy_mJ=ref["energy_mJ"])
        out["targets"][arm] = t

    for arm, t in targets.items():
        for (d, l) in SIZES:
            for grade, (bmin, bnom, bmax) in GRADES.items():
                g = gap_for_pull(d, l, bnom, t["pull_N"])
                row = {"arm": arm, "size": f"{d:g}x{l:g}", "grade": grade, "Br": bnom}
                if g is None:
                    row["g_star_mm"] = None
                    out["rows"].append(row)
                    continue
                r = q(d, l, bnom, g)
                glo = gap_for_pull(d, l, bnom, 1.1 * t["pull_N"])
                ghi = gap_for_pull(d, l, bnom, 0.9 * t["pull_N"])
                pk, at = peak_lateral(d, l, bnom, g)
                # sensitivities of the pull at g_star
                s_gap = qp(d, l, bnom, g + 1e-4)["pull_N"] / r["pull_N"] - 1            # +0.1 mm gap
                s_br = (qp(d, l, bmin, g)["pull_N"] / r["pull_N"] - 1, qp(d, l, bmax, g)["pull_N"] / r["pull_N"] - 1)
                s_dim = (qp(d - 0.1, l - 0.1, bnom, g + 1e-4)["pull_N"] / r["pull_N"] - 1,   # all dims -0.1 mm
                         qp(d + 0.1, l + 0.1, bnom, g - 1e-4)["pull_N"] / r["pull_N"] - 1)   # (faces fixed in pockets)
                s_dim_only = (qp(d - 0.1, l - 0.1, bnom, g)["pull_N"] / r["pull_N"] - 1,
                              qp(d + 0.1, l + 0.1, bnom, g)["pull_N"] / r["pull_N"] - 1)
                row.update(g_star_mm=g * 1e3, in_range=bool(G_LO - 1e-9 <= g <= G_HI + 1e-9),
                           pull_N=r["pull_N"], kz=r["kz_N_per_m"], klat=r["klat_N_per_m"],
                           d_kz_pct=100 * (r["kz_N_per_m"] / t["kz_N_per_m"] - 1),
                           d_klat_pct=100 * (r["klat_N_per_m"] / t["klat_N_per_m"] - 1),
                           d_energy_pct=100 * (r["energy_mJ"] / t["energy_mJ"] - 1),
                           peak_lateral_N=pk, peak_at_mm=at, d_peak_pct=100 * (pk / t["peak_lateral_N"] - 1),
                           window_mm=[None if glo is None else glo * 1e3, None if ghi is None else ghi * 1e3],
                           pull_pct_per_plus0p1mm_gap=100 * s_gap,
                           pull_pct_Br_min_max=[100 * s_br[0], 100 * s_br[1]],
                           pull_pct_dims_pm0p1mm_centres_fixed=[100 * s_dim[0], 100 * s_dim[1]],
                           pull_pct_dims_pm0p1mm_gap_fixed=[100 * s_dim_only[0], 100 * s_dim_only[1]])
                out["rows"].append(row)
            # double match: gap where klat / pull equals the target's, then the Br that gives the pull
            ratio = t["klat_N_per_m"] / t["pull_N"]
            f = lambda g: (lambda r: r["klat_N_per_m"] / r["pull_N"])(q(d, l, 1.0, g)) - ratio  # noqa: E731
            dm = {"arm": arm, "size": f"{d:g}x{l:g}"}
            if f(0.6e-3) > 0 > f(8e-3):
                g = brentq(f, 0.6e-3, 8e-3, xtol=1e-9)
                br = float(np.sqrt(t["pull_N"] / q(d, l, 1.0, g)["pull_N"]))
                grades = [k for k, (lo, _, hi) in GRADES.items() if lo <= br <= hi]
                dm.update(gap_mm=g * 1e3, Br_needed_T=br, grades_whose_range_contains_it=grades)
            else:
                dm.update(gap_mm=None)
            out["double_match"].append(dm)

    # discrete grid (0.1 mm steps), for anyone who wants to look up a combination directly
    for (d, l) in SIZES:
        for gi in range(10, 41):
            r = q(d, l, 1.0, gi * 1e-4)
            out["grid"].append({"size": f"{d:g}x{l:g}", "gap_mm": gi / 10, "pull_N_at_Br_1T": r["pull_N"],
                                "kz_at_Br_1T": r["kz_N_per_m"], "klat_at_Br_1T": r["klat_N_per_m"],
                                "energy_mJ_at_Br_1T": r["energy_mJ"]})
    (HERE / "scan.json").write_text(json.dumps(out, indent=1))

    # ---- printed tables
    for arm, t in targets.items():
        print(f"\n=== {arm} ({t['kind']}): 4x3 Br_eff {t['Br_eff']:.3f} T at gap {t['gap_mm']:.1f} mm -> pull "
              f"{t['pull_N']:.3f} N, kz {t['kz_N_per_m']:.0f}, klat {t['klat_N_per_m']:.0f} N/m, peak lateral "
              f"{t['peak_lateral_N']:.3f} N at {t['peak_at_mm']:.1f} mm, energy {t['energy_mJ']:.3f} mJ")
        rows = [r for r in out["rows"] if r["arm"] == arm and r.get("g_star_mm") is not None and r["in_range"]]
        rows.sort(key=lambda r: abs(r["d_klat_pct"]))
        print(" size   grade  g*mm  window(+-10% pull)  kz    klat  dkz%   dklat%  dpeak%  dE%   | pull% per +0.1mm gap,"
              " Br min/max, dims-0.1/+0.1(centres fixed)")
        for r in rows:
            w = r["window_mm"]
            ws = f"{w[0]:.2f}-{w[1]:.2f}" if None not in w else str(w)
            print(f" {r['size']:6s} {r['grade']:5s} {r['g_star_mm']:5.2f}  {ws:12s}      {r['kz']:6.0f} {r['klat']:5.0f}"
                  f" {r['d_kz_pct']:+6.1f} {r['d_klat_pct']:+6.1f}  {r['d_peak_pct']:+6.1f} {r['d_energy_pct']:+6.1f}"
                  f" | {r['pull_pct_per_plus0p1mm_gap']:+5.1f}, {r['pull_pct_Br_min_max'][0]:+.1f}/"
                  f"{r['pull_pct_Br_min_max'][1]:+.1f}, {r['pull_pct_dims_pm0p1mm_centres_fixed'][0]:+.1f}/"
                  f"{r['pull_pct_dims_pm0p1mm_centres_fixed'][1]:+.1f}")
        print(" double match (pull and klat both exact):")
        for dm in out["double_match"]:
            if dm["arm"] == arm:
                if dm["gap_mm"] is None:
                    print(f"   {dm['size']:6s} none in 0.6-8 mm")
                else:
                    print(f"   {dm['size']:6s} gap {dm['gap_mm']:.2f} mm, Br {dm['Br_needed_T']:.3f} T "
                          f"{dm['grades_whose_range_contains_it']}")


if __name__ == "__main__":
    main()
