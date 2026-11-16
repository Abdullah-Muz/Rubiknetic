"""Task 1: turner torque saturation. Read-only; reads per-trial JSON only."""
import json, glob, os
import numpy as np

E = "experiments"
LIM = 1.0
THR = 0.99


def load_dir(pattern):
    recs, bad = [], []
    for f in sorted(glob.glob(pattern)):
        try:
            r = json.load(open(f))
        except Exception as e:
            bad.append(f)
            continue
        if not isinstance(r, dict) or "pass" not in r:
            bad.append(f)
            continue
        r["_f"] = f
        recs.append(r)
    return recs, bad


def stats(name, recs, bad):
    mv = [(r, i, m) for r in recs for i, m in enumerate(r.get("per_move", []))]
    tq = np.array([abs(m["max_turner_torque_Nm"]) for _, _, m in mv if m.get("max_turner_torque_Nm") is not None])
    if len(tq) == 0:
        print(f"{name}: trials {len(recs)} (bad {len(bad)}), moves {len(mv)}, torque stored: 0")
        return
    sat = [(r, i, m) for r, i, m in mv if m.get("max_turner_torque_Nm") is not None and abs(m["max_turner_torque_Nm"]) >= THR]
    print(f"{name}: trials {len(recs)} (unreadable {len(bad)}), seq trials with moves {sum(1 for r in recs if r.get('per_move'))}, "
          f"moves {len(mv)}, torque n {len(tq)} | >=0.99: {len(sat)} | ==1.0 exactly: {(tq >= 1.0).sum()} | "
          f"median {np.median(tq):.3f} p95 {np.percentile(tq,95):.3f} p99 {np.percentile(tq,99):.3f} max {tq.max():.6f} | >=0.9: {(tq>=0.9).sum()} >=0.8: {(tq>=0.8).sum()}")
    for r, i, m in sat:
        print(f"    SAT {os.path.basename(r['_f'])} move#{i+1} {m['move']} tq {m['max_turner_torque_Nm']!r} te {m['turn_error_deg']:.3f} "
              f"drift {m['nontarget_drift_deg']:.3f} pen {m['penetration_mm']:.3f} oracle {m.get('ok_oracle')} obs {m.get('observed_move')}")
    # top 5
    top = sorted(mv, key=lambda x: -abs(x[2].get("max_turner_torque_Nm") or 0))[:5]
    print("    top5: " + "; ".join(f"{os.path.basename(r['_f'])}#{i+1} {m['move']} {m['max_turner_torque_Nm']:.4f}" for r, i, m in top))


arms = [
    ("0.05mm rehearsal (so far)", E + "/D8_alignment/results/rehearsal_gap0.05mm/E1-*/*.json"),
    ("0.1mm rehearsal", E + "/D8_alignment/results/rehearsal_gap0.1mm/E1-*/*.json"),
    ("gap g0.05_4x2", E + "/D8_alignment/results/diag_m4_2026-11-15/gap_study/g0.05_4x2/*.json"),
    ("gap g0.05_none", E + "/D8_alignment/results/diag_m4_2026-11-15/gap_study/g0.05_none/*.json"),
    ("gap g0.1_4x2", E + "/D8_alignment/results/diag_m4_2026-11-15/gap_study/g0.1_4x2/*.json"),
    ("size0.2 4x2_N35", E + "/D8_alignment/results/diag_m4_2026-11-15/size_gap0.2mm/4x2_N35/*.json"),
    ("size0.2 3x1.5_N35", E + "/D8_alignment/results/diag_m4_2026-11-15/size_gap0.2mm/3x1.5_N35/*.json"),
    ("size0.2 none", E + "/D8_alignment/results/diag_m4_2026-11-15/size_gap0.2mm/none/*.json"),
    ("M1 scored E1_scored (all)", E + "/E1_scored/results/E1-*/*.json"),
    ("M2 scored E2_scored_m2 (all)", E + "/E2_scored_m2/results/E1-*/*.json"),
]
for name, pat in arms:
    recs, bad = load_dir(pat)
    stats(name, recs, bad)

# Detail of the saturating trial
f = E + "/D8_alignment/results/rehearsal_gap0.05mm/E1-4/scr20inv_s8416.json"
r = json.load(open(f))
pm = r["per_move"]
print("\n=== scr20inv_s8416 detail ===")
print("setup:", {k: v for k, v in r["setup"].items() if k != "misalign_deg"})
print("pass", r["pass"], "fail_reasons", r["fail_reasons"], "final_matches_oracle", r["final_matches_oracle"],
      "moves_completed_ok", r["moves_completed_ok"], "sim_time_s", r["sim_time_s"], "wall_time_s", r.get("wall_time_s"))
keys = ["max_turner_torque_Nm", "turn_error_deg", "turn_error_spread_deg", "nontarget_drift_deg", "penetration_mm",
        "layer_magnet_axis_torque_peak_Nm", "layer_magnet_force_peak_N", "magnet_steps", "magnet_W_J", "magnet_dU_J"]
med = {k: float(np.median([abs(m[k]) for m in pm])) for k in keys}
mx = {k: float(np.max([abs(m[k]) for m in pm])) for k in keys}
print("trial medians |x|:", {k: round(v, 4) for k, v in med.items()})
print("trial max |x|:", {k: round(v, 4) for k, v in mx.items()})
prev_t = None
for i, m in enumerate(pm):
    dt = None if prev_t is None or m["t_pad_force_s"] is None else m["t_pad_force_s"] - prev_t
    prev_t = m["t_pad_force_s"]
    flag = " <==" if abs(m["max_turner_torque_Nm"]) >= THR else ""
    print(f"  #{i+1:2d} {m['move']:3s} tq {m['max_turner_torque_Nm']:.6f} te {m['turn_error_deg']:+.3f} spr {m['turn_error_spread_deg']:.3f} "
          f"drift {m['nontarget_drift_deg']:.3f} pen {m['penetration_mm']:.3f} tpad {m['t_pad_force_s']:.4f} tmot {m['t_layer_motion_s']:.4f} "
          f"steps {m['magnet_steps']} dt_prev {dt if dt is None else round(dt,4)} magTpk {m['layer_magnet_axis_torque_peak_Nm']:.4f} "
          f"post_err {m['misalignment']['max_err_deg']:.3f} obs {m['observed_move']} ok_all {m['ok_all']}{flag}")
# exact repr of the saturating value
for i, m in enumerate(pm):
    if abs(m["max_turner_torque_Nm"]) >= THR:
        print("saturating move full record:", json.dumps(m, indent=None)[:3000])
