"""Spot check: do the second edge and corner give the same sweep numbers as the reference pieces (stage3_results.json)?"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
r = json.loads((HERE / "stage3_results.json").read_text())
ref = {"edge": [1, 1, 0], "corner": [1, 1, 1]}
worst = {}
n = 0
for x in r["sweep"]:
    if x["home"] == ref[x["kind"]]:
        continue
    y = [z for z in r["sweep"] if z["home"] == ref[x["kind"]] and z["toward"] == x["toward"] and z["gamma_deg"] == x["gamma_deg"]]
    # pair order may differ between pieces: compare sorted values over the pairs at this gamma
    xs = [z for z in r["sweep"] if z["home"] == x["home"] and z["toward"] == x["toward"] and z["gamma_deg"] == x["gamma_deg"]]
    for s in ("4x3", "3x2"):
        for key in ("wall_at_layout_depth_mm", "best_wall_mm"):
            a = sorted([-99 if q[s].get(key) is None else q[s][key] for q in xs])
            b = sorted([-99 if q[s].get(key) is None else q[s][key] for q in y])
            d = max(abs(p - q) for p, q in zip(a, b))
            k = f"{x['kind']} {s} {key}"
            worst[k] = max(worst.get(k, 0.0), d)
    n += 1
print("rows compared", n)
for k, v in worst.items():
    print(f"  {k}: largest difference from the reference piece {v:.4f} mm")
la = [x for x in r["largest_cylinder_at_layout_pairs"]]
for kind in ("edge", "corner"):
    R = [x for x in la if x["kind"] == kind]
    keys = [k for k in R[0] if k.startswith("max_")]
    print(kind, "largest-cylinder rows", len(R), {k: sorted({x[k] for x in R}, key=lambda v: (v is None, v)) for k in keys})
