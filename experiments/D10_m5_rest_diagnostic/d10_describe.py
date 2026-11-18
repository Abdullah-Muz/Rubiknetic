"""D10 descriptive extraction (reads results/*.json only). Not part of the decision rule; source of SUMMARY's
descriptive numbers."""
import json
from pathlib import Path

import numpy as np

RES = Path(__file__).resolve().parent / "results"
for arm in ["A0i", "A1", "A2", "A3", "A4", "A5"]:
    for s in (10001, 10000):
        r = json.loads((RES / f"{arm}_s{s}.json").read_text())
        rec, at = r["record"], r["attribution"]
        ts = rec["timeseries"]
        t = np.array(ts["t"]) - ts["t"][0] + 0.025
        f, pc = at["peak_face"], at["peak_cubie"]
        sg = np.array(ts["rot_deg"][f])[:, rec["members"][f].index(pc)]
        dif = np.diff(sg)
        big = np.nonzero(np.abs(dif) > 0.01)[0]
        print(f"{arm} s{s}: peak {at['peak_deg']:.3f} deg, face {f}, {pc}, t {at['peak_time_s']:.3f} s, "
              f"layer mean {at['layer_mean_deg_at_peak']:+.3f}, label {at['label']}")
        if len(big):
            print(f"   fast event: {len(big)} x 25 ms samples with |step| > 0.01 deg, {t[big[0]]:.3f}-{t[big[-1]+1]:.3f} s, "
                  f"largest step {dif[np.argmax(np.abs(dif))]:+.3f} deg; KE peak {max(ts['ke_J']):.2e} J")
        else:
            print(f"   no fast event (no 25 ms step > 0.01 deg); KE peak {max(ts['ke_J']):.2e} J")
        idx = [min(np.searchsorted(t, x), len(t) - 1) for x in (1, 2, 4, 6, 8, 10, 30, 60) if x <= t[-1] + 1e-9]
        print("   signed rotation at 1,2,4,6,8,10[,30,60] s:", [round(float(sg[i]), 3) for i in idx])
        print(f"   KE first/last {ts['ke_J'][0]:.2e} / {ts['ke_J'][-1]:.2e} J; solver max iter {max(ts['solver_max_iter'])}"
              f" (limit hits {sum(ts['solver_limit_hits'])})")
        if ts["mag_force_N"]:
            names = rec["magnet_bodies"]
            F, T = np.array(ts["mag_force_N"]), np.array(ts["mag_torque_Nm"])
            corners = [i for i, n in enumerate(names) if all(c != "0" for c in n.split("_")[1])]
            print(f"   magnet net |F| t0: corners {F[0, corners].min():.2f}-{F[0, corners].max():.2f} N, "
                  f"all-body median {np.median(F[0]):.2f} N; peak cubie |torque| {T[0, names.index(pc)]*1e3:.1f} mN m "
                  f"(rank {int((T[0] > T[0, names.index(pc)]).sum()) + 1} of {len(names)}; median {np.median(T[0])*1e3:.1f})")
