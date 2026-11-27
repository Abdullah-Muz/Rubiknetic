"""P-109 (3) tuning study summary (UNSCORED). One row per gain configuration (2 pilot seeds each).

Selection rule (stated before reading the results, in README "Tuning study"):
  1. eligible = every move of both seeds passes every check, and no guard stop;
  2. among eligible, rank by the worst-case F/T torque during normal turning, then the worst-case core slip per
     move, then the worst-case turn error;
  3. if the nominal configuration (2000, 60, 8000) is within 10 % of the best on the first key, keep the nominal
     (no change without a clear gain).
Usage: python tune_analyze.py
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOMINAL = (2000.0, 60.0, 8000.0)


def main() -> None:
    groups = defaultdict(list)
    for p in sorted((HERE / "results" / "tune").glob("*.json")):
        m = re.search(r"_kp([\d.]+)_dp([\d.]+)_ki([\d.]+)_s(\d+)", p.name)
        if m is None:                                     # summary.json and other non-run files
            continue
        groups[(float(m[1]), float(m[2]), float(m[3]))].append(json.loads(p.read_text()))
    rows = []
    for cfg, recs in sorted(groups.items()):
        pms = [pm for r in recs for pm in r["per_move"]]
        mx = lambda k: max((abs(pm[k]) for pm in pms if pm.get(k) is not None), default=None)  # noqa: E731
        rows.append({
            "kp": cfg[0], "dp": cfg[1], "ki": cfg[2], "runs": len(recs),
            "runs_pass": sum(bool(r["pass"]) for r in recs),
            "moves_ok": sum(bool(pm["ok_all"]) for pm in pms), "moves": len(pms),
            "stops": sum(pm["jam_stop"] is not None for pm in pms),
            "ft_max": mx("ft_tau_z_max_Nm"), "slip_max": mx("core_slip_mm"), "err_max": mx("turn_error_deg"),
            "drift_max": mx("nontarget_drift_deg"), "grasp_err_max": mx("grasp_err_mm"),
            "track_max": mx("armB_track_err_mm"), "tool_max": mx("max_tool_torque_on_layer_Nm"),
            "approach_final_err_max": max((r["approach"].get("final_err_mm", 0) for r in recs), default=None),
            "cube_offsets_mm": [r["scene"]["cube_offset_mm"] for r in recs]})
    elig = [r for r in rows if r["runs"] == 2 and r["runs_pass"] == 2 and r["stops"] == 0]
    elig.sort(key=lambda r: (r["ft_max"], r["slip_max"], r["err_max"]))
    nom = next((r for r in elig if (r["kp"], r["dp"], r["ki"]) == NOMINAL), None)
    choice = None
    if elig:
        best = elig[0]
        choice = nom if (nom is not None and nom["ft_max"] <= 1.10 * best["ft_max"]) else best
    f = lambda v, n=2: "-" if v is None else f"{v:.{n}f}"  # noqa: E731
    lines = ["| K_P | D_P | KI_P | runs pass | moves ok | stops | max F/T N·m | max slip mm | max err ° | max drift ° | "
             "max grasp err mm | max tool τ N·m |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['kp']:g} | {r['dp']:g} | {r['ki']:g} | {r['runs_pass']}/{r['runs']} | {r['moves_ok']}/{r['moves']} "
                     f"| {r['stops']} | {f(r['ft_max'], 3)} | {f(r['slip_max'], 3)} | {f(r['err_max'])} | "
                     f"{f(r['drift_max'])} | {f(r['grasp_err_max'])} | {f(r['tool_max'], 3)} |")
    lines.append("")
    lines.append(f"Eligible: {len(elig)}/{len(rows)}. Selected: "
                 + ("none" if choice is None else f"K_P {choice['kp']:g}, D_P {choice['dp']:g}, KI_P {choice['ki']:g}"
                    + (" (nominal kept: within 10 % of the best)" if choice is nom else "")))
    out = "\n".join(lines)
    print(out)
    (HERE / "results" / "tune" / "summary.md").write_text(out + "\n", encoding="utf-8")
    (HERE / "results" / "tune" / "summary.json").write_text(json.dumps({"rows": rows, "choice": choice}, indent=1))


if __name__ == "__main__":
    main()
