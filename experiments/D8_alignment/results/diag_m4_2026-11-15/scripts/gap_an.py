import json, glob, numpy as np
B = "/mnt/c/Users/abdul/OneDrive/Desktop/Rubiknetic/experiments/D8_alignment/results/diag_m4_2026-11-15/"
arms = [("0.2 mm 4x2", B + "size_gap0.2mm/4x2_N35"), ("0.2 mm none", B + "size_gap0.2mm/none"),
        ("0.1 mm 4x2", B + "gap_study/g0.1_4x2"), ("0.05 mm 4x2", B + "gap_study/g0.05_4x2"), ("0.05 mm none", B + "gap_study/g0.05_none")]
for name, d in arms:
    seq = [json.load(open(f)) for f in sorted(glob.glob(d + "/scr20inv_*.json"))]
    mv = [m for r in seq for m in r["per_move"]]
    dr = np.array([m["nontarget_drift_deg"] for m in mv]); te = np.array([abs(m["turn_error_deg"]) for m in mv])
    tq = np.array([m["max_turner_torque_Nm"] for m in mv]); pen = max(m["penetration_mm"] for m in mv)
    post = [m.get("misalignment", {}).get("max_err_deg") for m in mv if m.get("misalignment")]
    tilt = max((r["magnet_stats"] or {}).get("max_near_tilt_deg", 0) for r in seq) if seq else 0
    print(f"{name:13s} seq pass {sum(r['pass'] for r in seq)}/{len(seq)} moves {len(mv)} oracle {sum(m['ok_oracle'] for m in mv)} | drift med {np.median(dr):.3f} p99 {np.percentile(dr,99):.3f} max {dr.max():.3f} | turn err max {te.max():.2f} | turner torque med {np.median(tq):.3f} max {tq.max():.3f} N m | pen max {pen:.3f} | post-move worst err med {np.median(post) if post else float('nan'):.2f} max {max(post) if post else float('nan'):.2f} | tilt {tilt:.2f}")
    rest = [json.load(open(f)) for f in sorted(glob.glob(d + "/rest_*.json"))]
    if rest: print(f"{'':13s} rest rotation {[round(r['rest_rotation_deg'],3) for r in rest]} pen {max(r['penetration_mm'] for r in rest):.3f}")
    for f in sorted(glob.glob(d + "/[otsf]*.json")):
        r = json.load(open(f)); k = r["kind"]
        if k == "snap": continue
        keys = {kk: (round(v, 3) if isinstance(v, float) else v) for kk, v in r.items()
                if any(s in kk for s in ("twist", "radial_change", "penetration", "forgiv", "completed", "blocked", "final_", "max_rot", "outcome"))
                and not isinstance(v, (dict, list))}
        print(f"{'':13s} {r['trial_id']:22s} pass {r['pass']} {json.dumps(keys)[:330]}")
    for f in sorted(glob.glob(d + "/snap*.json")):
        r = json.load(open(f)); print(f"{'':13s} {r['trial_id']} pass {r['pass']} " + json.dumps({k: round(v,3) for k, v in r.items() if isinstance(v, float) and ('err' in k or 'resid' in k)})[:200])
