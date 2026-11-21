"""Follow-up tables from scan.json / targets.json (ideal charge model, cyl_pair.py; no repo import).

1. Stocked items only (size and grade as read on vendor pages, 2026-11-20): gap g* matching each arm's pull, stiffness
   mismatch there, and the same with the pull derated to 0.67 of ideal (the repo's V2 figure).
2. Vendor "adhesive force on steel" against the ideal contact pull (mirror image, zero gap): how far real is from ideal.
3. M5's real magnet (4x2 N35) at the hybrid arms' own gaps, and the corner-edge pair at its 0.85 mm face gap.
4. Tolerance summary at the shortlisted combinations.
Usage: ~/.venvs/rubiknetic/bin/python -B extras.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from scipy.optimize import brentq

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cyl_pair as CP  # noqa: E402

SC = json.loads((HERE / "scan.json").read_text())
GR = SC["grades_Br_T_min_nom_max"]
T = SC["targets"]

# (vendor, article, d mm, l mm, grade, stated pull on steel N)  -- as read on the product pages
STOCK = [("supermagnete", "S-02-01-N", 2, 1, "N48", 1.08), ("supermagnete", "S-02-02-N", 2, 2, "N48", 1.47),
         ("supermagnete", "S-03-01-N", 3, 1, "N48", 1.86), ("supermagnete", "S-03-02-N", 3, 2, "N48", 2.94),
         ("supermagnete", "S-03-03-N", 3, 3, "N45", 3.24), ("supermagnete", "S-04-01-N", 4, 1, "N45", 2.45),
         ("supermagnete", "S-04-1.5-N", 4, 1.5, "N45", 3.43), ("supermagnete", "S-04-02-N", 4, 2, "N45", 4.12),
         ("supermagnete", "S-04-03-N", 4, 3, "N45", 5.2),
         ("first4magnets", "F413", 3, 3, "N42", 0.29 * 9.80665), ("first4magnets", "F343", 4, 1, "N42", 0.21 * 9.80665),
         ("first4magnets", "F415", 4, 1.5, "N42", 0.36 * 9.80665),
         ("first4magnets", "F042-N35", 4, 2, "N35", 0.38 * 9.80665),
         ("first4magnets", "F334", 4, 3, "N42", 0.53 * 9.80665)]


def gap_for(d, l, br, pull, derate=1.0):
    f = lambda g: derate * CP.pull(d * 1e-3, l * 1e-3, br, g) - pull  # noqa: E731
    if f(0.5e-3) < 0 or f(8e-3) > 0:
        return None
    return brentq(f, 0.5e-3, 8e-3, xtol=1e-9)


def main() -> None:
    out = {"stocked": [], "adhesive_check": [], "m5_magnet_at_hybrid_gaps": [], "corner_edge_pair": {}}

    print("1. STOCKED ITEMS: gap g* (mm) where pull = target; klat mismatch %; [same with real pull = 0.67 x ideal]")
    for arm, t in T.items():
        print(f"\n {arm}: pull {t['pull_N']:.3f} N, kz {t['kz_N_per_m']:.0f}, klat {t['klat_N_per_m']:.0f} N/m "
              f"(sim gap {t['gap_mm']:.1f} mm)")
        rows = []
        for (v, art, d, l, g, _) in STOCK:
            br = GR[g][1]
            r = {"arm": arm, "vendor": v, "article": art, "size": f"{d:g}x{l:g}", "grade": g}
            for tag, der in (("ideal", 1.0), ("derated_0.67", 0.67)):
                gs = gap_for(d, l, br, t["pull_N"], der)
                if gs is None:
                    r[tag] = None
                    continue
                p = CP.pair(d * 1e-3, l * 1e-3, br, gs)
                lo, hi = gap_for(d, l, br, 1.1 * t["pull_N"], der), gap_for(d, l, br, 0.9 * t["pull_N"], der)
                r[tag] = {"g_star_mm": gs * 1e3, "pull_N": der * p["pull_N"], "kz": der * p["kz_N_per_m"],
                          "klat": der * p["klat_N_per_m"],
                          "d_klat_pct": 100 * (der * p["klat_N_per_m"] / t["klat_N_per_m"] - 1),
                          "d_kz_pct": 100 * (der * p["kz_N_per_m"] / t["kz_N_per_m"] - 1),
                          "window_mm": [lo and lo * 1e3, hi and hi * 1e3]}
            rows.append(r)
            out["stocked"].append(r)
        rows = [r for r in rows if r["ideal"] and 1.0 <= r["ideal"]["g_star_mm"] <= 4.0]
        rows.sort(key=lambda r: abs(r["ideal"]["d_klat_pct"]))
        for r in rows:
            i, dd = r["ideal"], r["derated_0.67"]
            ds = (f"[{dd['g_star_mm']:.2f} mm, klat {dd['d_klat_pct']:+.1f} %]" if dd else "[no gap >= 0.5 mm]")
            print(f"  {r['size']:6s} {r['grade']} {r['vendor']:13s} {r['article']:10s} g* {i['g_star_mm']:.2f} "
                  f"({i['window_mm'][0]:.2f}-{i['window_mm'][1]:.2f})  pull {i['pull_N']:.3f}  kz {i['kz']:.0f} "
                  f"({i['d_kz_pct']:+.1f} %)  klat {i['klat']:.0f} ({i['d_klat_pct']:+.1f} %)   {ds}")

    print("\n2. VENDOR ADHESIVE FORCE ON STEEL vs IDEAL CONTACT PULL (Br min-max of the grade)")
    for (v, art, d, l, g, stated) in STOCK:
        lo = CP.pull(d * 1e-3, l * 1e-3, GR[g][0], 0.0)
        hi = CP.pull(d * 1e-3, l * 1e-3, GR[g][2], 0.0)
        # the same with a 2 x 0.02 mm non-magnetic layer is not computed (needs d/a >= 0.2); contact only
        out["adhesive_check"].append({"vendor": v, "article": art, "size": f"{d:g}x{l:g}", "grade": g,
                                      "stated_N": stated, "ideal_N": [lo, hi], "stated_over_ideal": [stated / hi, stated / lo]})
        print(f"  {v:13s} {art:10s} {d:g}x{l:g} {g}: stated {stated:.2f} N, ideal {lo:.2f}-{hi:.2f} N, "
              f"ratio {stated/hi:.2f}-{stated/lo:.2f}")

    print("\n3. M5's REAL MAGNET (4x2 N35, Br 1.19) AT THE HYBRID ARMS' OWN GAPS")
    for arm in ("HB1", "HB2", "HB3"):
        t = T[arm]
        p = CP.pair(0.004, 0.002, 1.19, t["gap_mm"] * 1e-3)
        row = {"arm": arm, "gap_mm": t["gap_mm"], "pull_N": p["pull_N"], "kz": p["kz_N_per_m"], "klat": p["klat_N_per_m"],
               "d_pull_pct": 100 * (p["pull_N"] / t["pull_N"] - 1), "d_kz_pct": 100 * (p["kz_N_per_m"] / t["kz_N_per_m"] - 1),
               "d_klat_pct": 100 * (p["klat_N_per_m"] / t["klat_N_per_m"] - 1)}
        out["m5_magnet_at_hybrid_gaps"].append(row)
        print(f"  {arm} gap {t['gap_mm']:.1f}: pull {p['pull_N']:.3f} ({row['d_pull_pct']:+.1f} %), kz {p['kz_N_per_m']:.0f} "
              f"({row['d_kz_pct']:+.1f} %), klat {p['klat_N_per_m']:.0f} ({row['d_klat_pct']:+.1f} %)   [vs sim target]")
    a = CP.pair(0.004, 0.002, 1.19, 0.85e-3)
    b = CP.pair(0.004, 0.003, 1.19 * 0.756 ** 0.5, 0.85e-3)
    out["corner_edge_pair"] = {"real_4x2_N35_gap0.85": a, "sim_4x3_scale0.756_gap0.85": b,
                               "sim_over_real": {k: b[k] / a[k] for k in ("pull_N", "kz_N_per_m", "klat_N_per_m", "energy_mJ")}}
    print(f"  corner-edge pair at 0.85 mm face gap: real 4x2 N35 pull {a['pull_N']:.3f} N, klat {a['klat_N_per_m']:.0f}; "
          f"simulated 4x3 x 0.756 pull {b['pull_N']:.3f} N, klat {b['klat_N_per_m']:.0f} "
          f"(sim/real: pull {b['pull_N']/a['pull_N']:.3f}, klat {b['klat_N_per_m']/a['klat_N_per_m']:.3f}, "
          f"energy {b['energy_mJ']/a['energy_mJ']:.3f})")

    print("\n4. TOLERANCES at shortlisted combinations (pull change, %): +0.1 mm gap | Br min/max of grade | "
          "D and L of both magnets -0.1/+0.1 mm at fixed gap | same with centres fixed (gap +-0.1)")
    want = [("W2", "4x1.5", "N45"), ("W2", "4x2", "N35"), ("W3", "3x3", "N45"), ("W3", "3x3", "N42"),
            ("W3", "4x1.5", "N35"), ("W3", "4x1", "N45"), ("W3", "4x3", "N35"), ("HB1", "4x2", "N45"),
            ("HB1", "4x2", "N35"), ("HB1", "4x3", "N35"), ("HB2", "4x2", "N35"), ("HB3", "4x2", "N35")]
    out["tolerance"] = []
    for (arm, size, grade) in want:
        r = next(x for x in SC["rows"] if x["arm"] == arm and x["size"] == size and x["grade"] == grade)
        out["tolerance"].append(r)
        print(f"  {arm:4s} {size:6s} {grade} at {r['g_star_mm']:.2f} mm: {r['pull_pct_per_plus0p1mm_gap']:+.1f} | "
              f"{r['pull_pct_Br_min_max'][0]:+.1f}/{r['pull_pct_Br_min_max'][1]:+.1f} | "
              f"{r['pull_pct_dims_pm0p1mm_gap_fixed'][0]:+.1f}/{r['pull_pct_dims_pm0p1mm_gap_fixed'][1]:+.1f} | "
              f"{r['pull_pct_dims_pm0p1mm_centres_fixed'][0]:+.1f}/{r['pull_pct_dims_pm0p1mm_centres_fixed'][1]:+.1f}")
    print("\n  arm-to-arm pull ratios (sim): W2/W3 = %.2f, W1/W2 = %.2f, HB1/HB2 = %.2f, HB2/HB3 = %.2f, HB1/W3 = %.2f"
          % (T["W2"]["pull_N"] / T["W3"]["pull_N"], T["W1"]["pull_N"] / T["W2"]["pull_N"],
             T["HB1"]["pull_N"] / T["HB2"]["pull_N"], T["HB2"]["pull_N"] / T["HB3"]["pull_N"],
             T["HB1"]["pull_N"] / T["W3"]["pull_N"]))
    (HERE / "extras.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
