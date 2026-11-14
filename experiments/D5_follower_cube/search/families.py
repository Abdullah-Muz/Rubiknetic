"""Best stage-1 config per (bevel_body, pad_spacing) family, for a diverse stage-2 list."""
import json
from pathlib import Path
R = Path(__file__).resolve().parent / "results"
rows = json.loads((R / "stage1_ranked.json").read_text())
best = {}
for r in rows:
    k = (r["cfg"]["bevel_body"], r["cfg"]["pad_spacing_deg"])
    if k not in best or r["ranked"] < best[k]["ranked"]:
        best[k] = r
for k in sorted(best):
    r = best[k]
    h = r["hard"]
    print(k, f"ranked {r['ranked']:.3f} minvol {r['min_rel_vol']:.3f}",
          " ".join(f"{h[str(d)]:.2f}" for d in (-5, -3, -2, -1, 1, 2, 3, 5)), r["cfg"])
