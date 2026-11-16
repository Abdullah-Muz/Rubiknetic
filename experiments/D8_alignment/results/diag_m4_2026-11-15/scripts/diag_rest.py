import json, numpy as np
D = "/mnt/c/Users/abdul/AppData/Local/Temp/claude/b6672f8dce1e00f4/3140f1d7-6e9e-4f5a-9e6c-c7e61a5f6350/scratchpad/diag/"
for s in ("7000", "7004"):
    j = json.load(open(D + f"rest_s{s}_rest_gap0.1.json")); rows = j["rows"]
    t = np.array([r["t"] for r in rows]); F = "URFDLB"
    E = np.array([[r[f] for f in F] for r in rows])
    i0 = np.argmin(np.abs(t - 0.5))
    print(f"== rest_s{s} rest_rotation {j['rest_rotation_deg']:.3f}")
    for q in list(range(0, len(t), max(1, len(t)//16))) + [len(t)-1]:
        print(f"  t {t[q]:6.2f}  " + "  ".join(f"{f} {E[q,k]:+.3f}" for k, f in enumerate(F)))
    print("  change t0->end per layer:", {f: round(float(E[-1,k]-E[i0,k]),3) for k, f in enumerate(F)})
    print("  t of largest step (per face):", {f: round(float(t[1:][np.argmax(np.abs(np.diff(E[:,k])))]),2) for k, f in enumerate(F)})
