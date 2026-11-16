import json, glob, numpy as np
base = "/mnt/c/Users/abdul/OneDrive/Desktop/Rubiknetic/experiments"
def load(pat):
    rows = []
    for f in glob.glob(pat):
        r = json.load(open(f))
        prev = r.get("misalignment_t0")
        for i, m in enumerate(r.get("per_move", [])):
            rows.append(dict(f=f.split("/")[-1], i=i, move=m["move"], half="2" in m["move"],
                             drift=m["nontarget_drift_deg"], te=abs(m["turn_error_deg"]),
                             spread=m["turn_error_spread_deg"],
                             tq=m.get("layer_magnet_axis_torque_peak_Nm"), turner=m["max_turner_torque_Nm"],
                             pre_err=(prev or {}).get("max_err_deg"), pre_res=(prev or {}).get("max_residual_deg"),
                             post_err=m.get("misalignment", {}).get("max_err_deg"),
                             grip=r["setup"]["grip_force"], speed=r["setup"]["turn_s_per_quarter"],
                             lag=None if m["t_pad_force_s"] is None or m["t_layer_motion_s"] is None
                             else m["t_pad_force_s"] - m["t_layer_motion_s"]))
            prev = m.get("misalignment")
    return rows
def summ(name, rows):
    d = np.array([r["drift"] for r in rows])
    print(f"{name}: n={len(d)} median {np.median(d):.3f} p90 {np.percentile(d,90):.3f} p99 {np.percentile(d,99):.3f} max {d.max():.3f} >1: {(d>1).sum()} >0.8: {(d>0.8).sum()}")
reh = load(base + "/D8_alignment/results/rehearsal_gap0.1mm/E1-[234]/*.json")
m1 = load(base + "/E1_scored/results/E1-[234]/*.json")
summ("M4 0.1mm rehearsal (magnets)", reh); summ("M1 scored (no magnets, 0.2mm)", m1)
for nm, sel in [("quarter", lambda r: not r["half"]), ("half", lambda r: r["half"])]:
    summ("  rehearsal " + nm, [r for r in reh if sel(r)]); summ("  M1 " + nm, [r for r in m1 if sel(r)])
R = [r for r in reh if r["pre_err"] is not None]
D = np.array([r["drift"] for r in R])
for k in ["pre_err", "pre_res", "post_err", "tq", "turner", "grip", "speed", "te", "spread", "i"]:
    x = np.array([r[k] for r in R], float)
    print(f"corr(drift, {k:8s}) = {np.corrcoef(D, x)[0,1]:+.2f}   mean in drift>1: {x[D>1].mean():.4g}  overall: {x.mean():.4g}")
print("drift>1 moves:", [(r["f"], r["i"], r["move"], round(r["drift"],2), round(r["pre_err"],2), round(r["post_err"],2)) for r in R if r["drift"] > 1])
lags = np.array([r["lag"] for r in reh if r["lag"] is not None])
print("pad-minus-motion lag (s): n", len(lags), "positive (motion first):", (lags > 0).sum(), "max", lags.max().round(3), "p95", np.percentile(lags,95).round(3))
lm = np.array([r["lag"] for r in m1 if r["lag"] is not None]); print("M1 lag: positive", (lm>0).sum(), "of", len(lm), "max", lm.max().round(3))
