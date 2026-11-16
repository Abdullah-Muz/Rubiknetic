import json, numpy as np
j = json.load(open("/mnt/c/Users/abdul/AppData/Local/Temp/claude/b6672f8dce1e00f4/3140f1d7-6e9e-4f5a-9e6c-c7e61a5f6350/scratchpad/diag/rest_s7000_rest_gap0.1.json"))
rows = [r for r in j["rows"] if "piece_err" in r]
t = np.array([r["t"] for r in rows]); P = np.array([r["piece_err"] for r in rows])   # (T, 20, 3) rotvec error deg
mag = np.linalg.norm(P, axis=2)
print("rest_rotation", j["rest_rotation_deg"])
for q in [0, 5, 9, 10, 20, 40, 45, 48, 49, 50, 52, 60, 100, 150, 200, len(t)-1]:
    if q < len(t): print(f" t {t[q]:6.2f}  max|err| {mag[q].max():.3f}  mean|err| {mag[q].mean():.3f}")
i0 = np.argmin(np.abs(t - 0.5)); k = np.argmax(np.abs(np.diff(mag, axis=0)).max(axis=1))
print(" biggest single-interval change at t", round(t[k+1],3), "pieces with |d err|>0.2:")
dd = mag[k+1] - mag[k]
for i in np.argsort(-np.abs(dd))[:6]: print(f"   piece {i:2d}  |err| {mag[k,i]:.3f} -> {mag[k+1,i]:.3f}   (t0 {mag[i0,i]:.3f}, end {mag[-1,i]:.3f})")
