"""Rank stage-1 results with a support penalty and write the stage-2 candidate list.
Penalty: 5 * max(0, 0.92 - min_rel_volume), where min_rel_volume is the smallest piece-type convex
volume relative to the baseline (big bevels/tapers remove support; see the D5 disintegration run).
Usage: python select.py [top_n]"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE / "results"
rows = [json.loads(l) for f in sorted(R.glob("stage1_*.jsonl")) for l in f.read_text().splitlines() if l.strip()]
base = next(r for r in rows if r["cfg"] == {"bevel_body": 1.0, "bevel_foot": 0.5, "bevel_inner": 0.0, "taper": 0.0,
                                             "taper_start": 19.0, "pad_spacing_deg": 10.0})
for r in rows:
    rel = min(r["support"][f"{k}_vol"] / base["support"][f"{k}_vol"] for k in ("corner", "edge", "centre"))
    r["min_rel_vol"] = rel
    r["ranked"] = r["score"] + 5 * max(0.0, 0.92 - rel)
rows.sort(key=lambda r: r["ranked"])
n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
print(f"{len(rows)} configs screened; baseline score {base['score']:.3f}")
print("rank  ranked  score  minvol  HARD(-5,-3,-2,-1,+1,+2,+3,+5)  cfg")
for i, r in enumerate(rows[:25]):
    h = r["hard"]
    hs = " ".join(f"{h[str(d)] if str(d) in h else h[d]:.2f}" for d in (-5, -3, -2, -1, 1, 2, 3, 5))
    print(f"{i + 1:4d} {r['ranked']:7.3f} {r['score']:6.3f} {r['min_rel_vol']:6.3f}  {hs}  {r['cfg']}")
top = [r["cfg"] for r in rows[:n]]
bcfg = dict(base["cfg"], sphere_spacing_mm=1.0, is_baseline=True)
(R / "stage2_candidates.json").write_text(json.dumps([bcfg] + top, indent=1))
(R / "stage1_ranked.json").write_text(json.dumps(rows, indent=1))
print(f"wrote {R / 'stage2_candidates.json'} ({n} + baseline)")
