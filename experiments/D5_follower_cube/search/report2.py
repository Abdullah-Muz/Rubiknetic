"""Summarise stage-2/3 JSONL results."""
import json, sys
from pathlib import Path
R = Path(__file__).resolve().parent / "results"
files = sys.argv[1:] or ["stage2.jsonl", "stage2_b.jsonl"]
for fn in files:
    for l in (R / fn).read_text().splitlines():
        r = json.loads(l)
        c = r["cfg"]; g = r["geometry"]
        tag = f"bb{c['bevel_body']} bf{c['bevel_foot']} bi{c['bevel_inner']} t{c['taper']}@{c['taper_start']} ps{c['pad_spacing_deg']}" + (" BASE" if c.get("is_baseline") else "")
        gate = f"gate {'GREEN' if g['green'] else 'FAIL'} sweepmin {min(g['sweep_min_mm'].values()):.3f} out0.05 {g['outward_0.05mm']:+.3f} tw2 {g['twist_2deg']:+.3f}"
        if "rig" not in r:
            print(f"{tag:45s} {gate} | no dynamic test"); continue
        rg = r["rig"]
        mv = " ".join(f"{m['move']}:{'ok' if m['ok'] else 'X'}{m['error']:+.1f}/sp{m['spread']:.1f}/dr{m['drift']:.1f}/tq{m['torque']:.2f}" for m in rg["moves"])
        pen = max((m["pen_piece"] for m in rg["moves"]), default=0)
        print(f"{tag:45s} {rg['n_ok']}/{rg['n']} pen {pen:.2f} {rg['steps_per_s']} st/s | {mv}")
        if "forgive" in r:
            print("     forgive: " + " ".join(f"{q['mis']:+.1f}->{'OK' if q['completed'] else 'X'}(R{q['R']:.0f})" for q in r["forgive"]["points"]))
        if "twist" in r:
            tw = r["twist"]
            print("     twist: " + " ".join(f"{L['torque']}:{L['twist']:.1f}" for L in tw["levels"]) + f" | released {tw['released_twist']} solved {tw['recovered_solved']}")
