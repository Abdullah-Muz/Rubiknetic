"""Prints a short table from the snap-back diagnostic outputs (posthoc/snap_<arm>_s<seed>_<delta>.json)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for f in sorted(HERE.glob("snap_*.json")) if len(sys.argv) < 2 else [Path(x) for x in sys.argv[1:]]:
    o = json.loads(f.read_text())
    s = o["states"][-1]
    print(f"{o['arm']} seed {o['seed']} delta {o['delta_deg']:+g}: U error {s['U_err_deg']:+.4f} deg, "
          f"piece-piece contacts {s['cubie_cubie']['n']} ({s['cubie_cubie']['normal_N']:.2f} N), "
          f"magnet torque about U {s['magnet_Nm']:.2e} N m")
    for in_u in (True, False):
        for kind in ("edge", "corner", "centre"):
            v = [p for p in s["pieces"].values() if p["in_U_layer"] == in_u and p["kind"] == kind]
            if not v:
                continue
            sp = [p["spin_about_own_axis_deg"] for p in v]
            tg = [p["tangential_deg"] for p in v]
            print(f"   {'U layer' if in_u else 'others ':8s} {kind:6s} n={len(v):2d}  spin {min(sp):+.3f} .. {max(sp):+.3f} deg"
                  f"   tangential max {max(tg):.3f} deg")
