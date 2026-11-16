import json, glob, os, time
import numpy as np

E = "experiments"
DG = E + "/D8_alignment/results/diag_m4_2026-11-15/"
TS = DG + "timeseries/"
REH = E + "/D8_alignment/results/rehearsal_gap0.1mm/"


def J(p):
    return json.load(open(p))


# ---- bit-for-bit reproduction claims (diag §3 L45) ----
pairs = [("D_s7113_0_gap0.1.json", "E1-2/D_s7113.json", 0), ("D_s7112_0_gap0.1.json", "E1-2/D_s7112.json", 0),
         ("scr20inv_s7402_26_gap0.1.json", "E1-4/scr20inv_s7402.json", 26)]
for ts, rec, i in pairs:
    t, r = J(TS + ts), J(REH + rec)
    a, b = t["per_move"], r["per_move"][i]
    same = {k: a[k] == b[k] for k in ("nontarget_drift_deg", "turn_error_deg", "t_layer_motion_s", "t_pad_force_s")}
    print(ts, "ts drift", repr(a["nontarget_drift_deg"]), "rec drift", repr(b["nontarget_drift_deg"]), same)
print("rest_s7000 ts", repr(J(TS + "rest_s7000_rest_gap0.1.json")["rest_rotation_deg"]), "rec", repr(J(REH + "E1-1/rest_s7000.json")["rest_rotation_deg"]))

# ---- §2 time series ----
for ts in ("D_s7113_0_gap0.1.json", "D_s7112_0_gap0.1.json", "scr20inv_s7402_26_gap0.1.json"):
    t = J(TS + ts)
    rows, nt = t["rows"], t["meta"]["nontarget"]
    dt = np.diff([x["t"] for x in rows])
    e0, e1 = np.array(rows[0]["nt_err_deg"]), np.array(rows[-1]["nt_err_deg"])
    print(f"{ts}: rows {len(rows)} dt median {np.median(dt)*1000:.2f} ms | worst nt err first {np.abs(e0).max():.3f} last {np.abs(e1).max():.3f}")
    if "s7113" in ts:
        k = nt.index(25)
        print("   piece 25 err first", round(e0[k], 3), "last", round(e1[k], 3), "| signs first", np.sign(e0).astype(int).tolist())
    if "tl_err_deg" in rows[0]:
        pass
# rest_s7000
t = J(TS + "rest_s7000_rest_gap0.1.json")
rows = t["rows"]
dt = np.diff([x["t"] for x in rows])
pe = np.array([np.abs(np.array(x["piece_err"])).max(axis=1) for x in rows])  # per piece, max |component|
pn = np.array([np.linalg.norm(np.array(x["piece_err"]), axis=1) for x in rows])
T = np.array([x["t"] for x in rows])
print(f"rest_s7000: rows {len(rows)} dt median {np.median(dt)*1000:.1f} ms, t range {T[0]:.3f}-{T[-1]:.3f}")
for lab, arr in (("max|comp|", pe), ("norm", pn)):
    worst = arr.max(axis=1)
    jump = np.abs(np.diff(arr, axis=0)).max(axis=1)
    j = int(np.argmax(jump))
    print(f"  [{lab}] worst first {worst[0]:.3f} last {worst[-1]:.3f} max {worst.max():.3f}; biggest step between t={T[j]:.3f} and {T[j+1]:.3f}")
    for p in (9, 2):
        print(f"     piece {p}: before {arr[j, p]:.3f} after {arr[j+1, p]:.3f}")
    # number of pieces changing > 0.1 deg at that step
    print(f"     pieces with change > 0.1 deg at that step: {int((np.abs(arr[j+1]-arr[j])>0.1).sum())}")
    # creep: median slope outside jumps, of worst error
    sl = np.diff(worst) / np.diff(T)
    print(f"     median |d worst/dt| {np.median(np.abs(sl)):.4f} deg/s, mean slope over t>3s {np.polyfit(T[T>3], worst[T>3], 1)[0]:.4f} deg/s")
fl = {f: [x[f] for x in rows] for f in "URFDLB"}
k = int(np.argmax(np.abs(np.diff(np.array([fl[f] for f in "URFDLB"]).T, axis=0)).sum(axis=1)))
print("  face-level biggest collective step at t", T[k], "->", T[k+1], {f: round(fl[f][k+1]-fl[f][k], 3) for f in "URFDLB"})

# ---- magnet checks files ----
for f in ("d8_1b_checks_3x1.5_N35_s1.json", "d8_1b_checks_4x1.5_N35_s1.json"):
    c = J(E + "/D8_alignment/results/" + f)
    s = json.dumps(c)
    print(f, "top keys", list(c.keys())[:15])
    for k, v in c.items():
        if isinstance(v, dict) and any(x in k.upper() for x in ("V3", "SUMMARY", "VALID", "RESULT")):
            print("   ", k, json.dumps(v)[:500])
        elif not isinstance(v, (dict, list)):
            print("   ", k, repr(v)[:200])

# ---- per-trial tilt in 0.05 4x2 arm ----
for f in sorted(glob.glob(DG + "gap_study/g0.05_4x2/*.json")):
    r = J(f)
    print("  tilt", os.path.basename(f), round((r.get("magnet_stats") or {}).get("max_near_tilt_deg") or -1, 3), r.get("rule3_label"))
for arm in ("g0.1_4x2",):
    for f in sorted(glob.glob(DG + f"gap_study/{arm}/*.json")):
        r = J(f)
        print("  ", arm, os.path.basename(f), "tilt", round((r.get("magnet_stats") or {}).get("max_near_tilt_deg") or -1, 3), "rest", r.get("rest_rotation_deg"), r["pass"])
for f in sorted(glob.glob(DG + "size_gap0.2mm/none/rest*.json")):
    print("  0.2 none", os.path.basename(f), round(J(f)["rest_rotation_deg"], 4))

# ---- stage1 twist at 0.2 mm ----
for f in sorted(glob.glob(E + "/D8_alignment/results/stage1*/B1_*/twist*.json")):
    r = J(f)
    print("  stage1", f.split("results/")[1], "max_twist", r.get("max_twist_deg"), "gap", (r.get("params") or {}).get("gap"))

# ---- 0.05 rehearsal: penetration rank of the saturating move ----
mv = [(r["trial_id"], i + 1, m) for f in sorted(glob.glob(E + "/D8_alignment/results/rehearsal_gap0.05mm/E1-*/*.json"))
      for r in [J(f)] for i, m in enumerate(r["per_move"])]
pen = sorted(((m["penetration_mm"], t, i) for t, i, m in mv), reverse=True)
print("0.05 rehearsal moves", len(mv), "top penetration", [(round(a, 4), t, i) for a, t, i in pen[:4]], "median", round(float(np.median([a for a, _, _ in pen])), 4))
sp = sorted(((m["turn_error_spread_deg"], t, i) for t, i, m in mv))
print("lowest turn_error_spread", [(round(a, 4), t, i) for a, t, i in sp[:3]])
# mtimes of gap study
ms = [os.path.getmtime(f) for f in glob.glob(DG + "gap_study/*/*.json")]
print("gap study mtimes", time.strftime("%Y-%m-%d %H:%M", time.localtime(min(ms))), time.strftime("%Y-%m-%d %H:%M", time.localtime(max(ms))), time.tzname)
