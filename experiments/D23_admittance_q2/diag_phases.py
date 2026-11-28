"""D23 diagnostic: high-passed force / position RMS per phase (free space vs grasped), and amplitude growth."""
import json, sys
from pathlib import Path
import numpy as np
from scipy.signal import butter, sosfiltfilt
HERE = Path(__file__).resolve().parent
SOS = butter(2, 5.0, "highpass", fs=2000.0, output="sos")
for name in sys.argv[1:]:
    rec = json.loads((HERE / "results" / f"{name}.json").read_text())
    s = np.load(HERE / "results" / f"{name}_trace.npz")["step"]
    t, x, fr = s[:, 0], s[:, 1:4], s[:, 4:7]
    ph = rec["phases"]
    f = -(fr - fr[(t >= ph["tare"][0]) & (t <= ph["tare"][1])].mean(0))
    fh, xh = sosfiltfilt(SOS, f, axis=0), sosfiltfilt(SOS, x, axis=0) * 1e3
    print(name, rec.get("aborted"))
    for p, (a, b) in ph.items():
        sel = (t >= a) & (t <= b)
        # RMS in 4 equal sub-windows to see growth/decay
        idx = np.array_split(np.where(sel)[0], 4)
        fr_ = [float(np.sqrt((fh[i] ** 2).sum(1).mean())) for i in idx if len(i)]
        xr_ = [float(np.sqrt((xh[i] ** 2).sum(1).mean())) for i in idx if len(i)]
        print(f"  {p:9s} {a:6.2f}-{b:6.2f}s  F_hp rms by quarter {np.round(fr_, 2)}  x_hp rms mm {np.round(xr_, 3)}  "
              f"F axis rms {np.round(np.sqrt((fh[sel]**2).mean(0)), 2)}")
