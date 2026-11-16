import json, sys, numpy as np
D = "/mnt/c/Users/abdul/AppData/Local/Temp/claude/b6672f8dce1e00f4/3140f1d7-6e9e-4f5a-9e6c-c7e61a5f6350/scratchpad/diag/"
for name in sys.argv[1:]:
    j = json.load(open(D + name + ".json")); rows = j["rows"]; m = j["meta"]
    print("==", name, "drift", round(j["per_move"]["nontarget_drift_deg"], 3), "pad t", j["per_move"]["t_pad_force_s"], "motion t", j["per_move"]["t_layer_motion_s"])
    t = np.array([r["t"] for r in rows]); rot = np.array([r["nt_rot_deg"] for r in rows]); err = np.array([r["nt_err_deg"] for r in rows])
    mag = np.array([r["nt_mag_Nm"] for r in rows]); lay = np.array([r["layer_rot_deg"] for r in rows]); pad = np.array([r["pad_N"] for r in rows])
    final = rot[-1]; k = np.argsort(-np.abs(final))
    print(" piece class  final_rot  err_before err_after  peak|rot| t_peak  mag_peak_Nm")
    for i in k[:6]:
        ip = np.argmax(np.abs(rot[:, i]))
        print(f"  {m['nontarget'][i]:3d} {m['class'][i]:8s} {final[i]:+.3f}   {err[0,i]:+.3f}   {err[-1,i]:+.3f}   {rot[ip,i]:+.3f}  {t[ip]:.3f}  {np.abs(mag[:,i]).max():.4f}")
    sl = [i for i, c in enumerate(m["class"]) if c == "slice"]; op = [i for i, c in enumerate(m["class"]) if c == "opposite"]
    print(f" mean final rot: slice {final[sl].mean():+.3f} (spread {np.ptp(final[sl]):.3f})  opposite {final[op].mean():+.3f} (spread {np.ptp(final[op]):.3f})")
    print(f" |err| mean before {np.abs(err[0]).mean():.3f} after {np.abs(err[-1]).mean():.3f};  max before {np.abs(err[0]).max():.3f} after {np.abs(err[-1]).max():.3f}")
    # phase timeline every ~0.1 s
    for q in range(0, len(t), max(1, len(t)//22)):
        print(f"  t {t[q]:.3f} pad {pad[q]:5.2f}N layer {lay[q]:+7.2f}  slice-mean {rot[q,sl].mean():+.3f} opp-mean {rot[q,op].mean():+.3f} worst {rot[q,k[0]]:+.3f} magτ_worst {mag[q,k[0]]:+.4f}")
