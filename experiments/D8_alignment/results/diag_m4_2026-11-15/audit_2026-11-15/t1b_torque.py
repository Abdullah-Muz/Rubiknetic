"""Task 1b: per-face breakdown, stored actuator params, M1 restricted to E1-2..E1-4."""
import json, glob, os
from collections import Counter, defaultdict
import numpy as np

E = "experiments"
arms = [
    ("0.05mm rehearsal (so far)", E + "/D8_alignment/results/rehearsal_gap0.05mm/E1-*/*.json"),
    ("0.1mm rehearsal", E + "/D8_alignment/results/rehearsal_gap0.1mm/E1-*/*.json"),
    ("gap g0.05_4x2", E + "/D8_alignment/results/diag_m4_2026-11-15/gap_study/g0.05_4x2/*.json"),
    ("gap g0.05_none", E + "/D8_alignment/results/diag_m4_2026-11-15/gap_study/g0.05_none/*.json"),
    ("gap g0.1_4x2", E + "/D8_alignment/results/diag_m4_2026-11-15/gap_study/g0.1_4x2/*.json"),
    ("size0.2 4x2_N35", E + "/D8_alignment/results/diag_m4_2026-11-15/size_gap0.2mm/4x2_N35/*.json"),
    ("size0.2 3x1.5_N35", E + "/D8_alignment/results/diag_m4_2026-11-15/size_gap0.2mm/3x1.5_N35/*.json"),
    ("size0.2 none", E + "/D8_alignment/results/diag_m4_2026-11-15/size_gap0.2mm/none/*.json"),
    ("M1 scored E1-2..E1-4", E + "/E1_scored/results/E1-[234]/*.json"),
]
for name, pat in arms:
    recs, bad = [], []
    for f in sorted(glob.glob(pat)):
        try:
            r = json.load(open(f))
            recs.append(r)
        except Exception:
            bad.append(f)
    prm = Counter((r.get("params", {}).get("turn_torque_limit"), r.get("params", {}).get("turn_kp"),
                   r.get("params", {}).get("turn_kv"), r.get("params", {}).get("gap"),
                   r.get("params", {}).get("radial_preload")) for r in recs)
    mv = [m for r in recs for m in r.get("per_move", [])]
    tq = np.array([abs(m["max_turner_torque_Nm"]) for m in mv])
    face = defaultdict(list)
    half = defaultdict(list)
    for m in mv:
        face[m["move"][0]].append(abs(m["max_turner_torque_Nm"]))
        half["half" if "2" in m["move"] else "quarter"].append(abs(m["max_turner_torque_Nm"]))
    print(f"== {name}: trials {len(recs)} unreadable {[os.path.basename(b) for b in bad]} moves {len(mv)}")
    print("   (turn_torque_limit, turn_kp, turn_kv, gap, radial_preload):", dict(prm))
    if len(tq):
        print(f"   n {len(tq)} >=0.99 {(tq>=0.99).sum()} p95 {np.percentile(tq,95):.3f} p99 {np.percentile(tq,99):.3f} median {np.median(tq):.3f} max {tq.max():.4f}")
        print("   per face (n, median, n>=0.99): " + ", ".join(f"{k}:{len(v)},{np.median(v):.3f},{sum(x>=0.99 for x in v)}" for k, v in sorted(face.items())))
        print("   quarter/half (n, median, p99, n>=0.99): " + ", ".join(f"{k}:{len(v)},{np.median(v):.3f},{np.percentile(v,99):.3f},{sum(x>=0.99 for x in v)}" for k, v in sorted(half.items())))
# which M1 file was unreadable in the full glob
for f in sorted(glob.glob(E + "/E1_scored/results/E1-*/*.json")):
    try:
        json.load(open(f))
    except Exception as e:
        print("M1 unreadable:", f, type(e).__name__)
# 0.05 rehearsal: U-face moves sorted
recs = [json.load(open(f)) for f in sorted(glob.glob(E + "/D8_alignment/results/rehearsal_gap0.05mm/E1-*/*.json"))]
u2 = sorted([(m["max_turner_torque_Nm"], r["trial_id"], i + 1) for r in recs for i, m in enumerate(r["per_move"]) if m["move"] == "U2"], reverse=True)
print("0.05 rehearsal U2 moves: n", len(u2), "top 6", [(round(a, 3), b, c) for a, b, c in u2[:6]], "median", round(float(np.median([a for a, _, _ in u2])), 3))
