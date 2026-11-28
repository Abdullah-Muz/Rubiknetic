"""D24 analysis: per stress condition, G2's full pass rate and the TURN outcome separately.

turn_ok: every move observed as commanded with all per-move checks passing, no guard stop, final state = oracle,
         integrity clean (G2's per-move and integrity rules), IGNORING G2's start-sequence limits (t0 offset, stand-drop
         shift) and trial totals, which a deliberate stress may trip.
Usage: ~/.venvs/rubiknetic/bin/python experiments/D24_b0_stress_map/analyze.py /home/fwdev/g3stress/results
"""
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

root = Path(sys.argv[1])
rows = defaultdict(list)
for f in sorted(glob.glob(str(root / "S-*" / "*.json"))):
    r = json.load(open(f))
    cond = Path(f).stem.rsplit("_s", 1)[0]
    pms = r.get("per_move", [])
    integ = not (r.get("aborted") or r.get("harness_exception") or r.get("audit_violations")
                 or r.get("numerical_failures"))
    moves_ok = len(pms) == 3 and all(pm.get("ok_all") and pm.get("jam_stop") is None
                                     and pm.get("core_slip_mm", 9) <= 1.0 for pm in pms)
    turn_ok = bool(integ and moves_ok and r.get("final_matches_oracle"))
    fails = sorted({k for pm in pms for k, v in pm.items() if k.startswith("ok_") and k != "ok_all" and not v}
                   | ({"guard_stop"} if any(pm.get("jam_stop") for pm in pms) else set())
                   | ({"incomplete"} if len(pms) < 3 else set()))
    rows[cond].append({
        "g2_pass": bool(r.get("pass")), "turn_ok": turn_ok, "fails": fails,
        "reasons": r.get("fail_reasons", [])[:3],
        "t0_offset_mm": r.get("start", {}).get("core_offset_from_nominal_mm"),
        "max_turn_err": max((abs(pm.get("turn_error_deg", 0)) for pm in pms), default=None),
        "max_ft": max((pm.get("ft_tau_z_max_Nm", 0) for pm in pms), default=None),
        "max_slip": max((pm.get("core_slip_mm", 0) for pm in pms), default=None),
        "max_rot": max((pm.get("core_rot_deg", 0) for pm in pms), default=None)})


def order(c):
    import re
    m = re.match(r"([a-z]+)([-+]?[0-9.]+)?", c)
    return (m.group(1), float(m.group(2)) if m.group(2) else 0.0)


out = []
print(f"{'condition':16s} {'n':>2s} {'G2 pass':>8s} {'turn ok':>8s}  max turn err  max F/T  max slip  max rot  failures")
for c in sorted(rows, key=order):
    v = rows[c]
    n = len(v)
    g2 = sum(x["g2_pass"] for x in v)
    tk = sum(x["turn_ok"] for x in v)

    def mx(k):
        return max((x[k] for x in v if x[k] is not None), default=float("nan"))
    fl = sorted({f for x in v for f in x["fails"]})
    print(f"{c:16s} {n:2d} {g2:4d}/{n:<3d} {tk:4d}/{n:<3d}  {mx('max_turn_err'):11.2f}  {mx('max_ft'):7.3f}  "
          f"{mx('max_slip'):8.3f}  {mx('max_rot'):7.2f}  {','.join(fl)}")
    out.append({"condition": c, "n": n, "g2_pass": g2, "turn_ok": tk, "failures": fl,
                "max": {k: mx(k) for k in ("max_turn_err", "max_ft", "max_slip", "max_rot", "t0_offset_mm")},
                "trials": v})
json.dump(out, open(Path(__file__).resolve().parent / "summary.json", "w"), indent=1, default=float)
