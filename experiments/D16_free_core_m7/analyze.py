"""D16 summary (UNSCORED): one row per trial and per configuration group. Usage: python analyze.py"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def row(r: dict) -> dict:
    d = r["d16"]
    pm = r.get("per_move", [])
    S = np.array(d.get("series") or [[0] * 8])
    sq = S[:, 1:3].min(axis=1)
    return {
        "name": d["name"], "group": d["name"].rsplit("_s", 1)[0],
        "pass_g1": bool(r.get("pass")), "pass_rel_core": bool(d.get("pass_rel_core")),
        "harness_error": r.get("harness_error"),
        "moves_ok_g1": sum(1 for m in pm if m.get("ok_all")),
        "moves_ok_rel": sum(1 for m in pm if m.get("d16_ok_all_rel_core")),
        "observed_ok": sum(1 for m in pm if m.get("ok_oracle")), "n_moves": len(pm),
        "failed_checks": sorted({k for m in pm for k, v in m.items() if k.startswith("ok_") and k != "ok_all" and not v}),
        "max_turn_err_deg": max((abs(m["turn_error_deg"]) for m in pm), default=None),
        "max_drift_deg": max((m["nontarget_drift_deg"] for m in pm), default=None),
        "max_pen_mm": max((m["penetration_mm"] for m in pm), default=None),
        "max_torque_Nm": max((m["max_turner_torque_Nm"] for m in pm), default=None),
        "core_slip_mm": d.get("core_slip_mm"), "core_rot_deg": d.get("core_rot_deg"),
        "squeeze_median_N": d.get("stab_squeeze_N_median"),
        "squeeze_lt1N_samples": int((sq < 1.0).sum()), "n_samples": len(S),
        "core_w_max_dps": float(S[:, 7].max()) if S.shape[1] > 7 else None,
    }


def main() -> None:
    rows = [row(json.loads(p.read_text())) for p in sorted((HERE / "results").glob("*_s*.json"))]
    groups = defaultdict(list)
    for x in rows:
        groups[x["group"]].append(x)
    f = lambda v, n=2: "-" if v is None else f"{v:.{n}f}"  # noqa: E731
    lines = ["| Trial | G1 pass | pass (rel. core) | observed ok | failed checks | max err ° | max drift ° | max pen mm "
             "| max τ N·m | core slip mm | core rot ° | squeeze N (median) | samples < 1 N |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for x in rows:
        lines.append(f"| {x['name']} | {x['pass_g1']} | {x['pass_rel_core']} | {x['observed_ok']}/{x['n_moves']} | "
                     f"{', '.join(x['failed_checks']) or '-'}{' ' + x['harness_error'] if x['harness_error'] else ''} | "
                     f"{f(x['max_turn_err_deg'])} | {f(x['max_drift_deg'])} | {f(x['max_pen_mm'])} | "
                     f"{f(x['max_torque_Nm'], 3)} | {f(x['core_slip_mm'])} | {f(x['core_rot_deg'])} | "
                     f"{f(x['squeeze_median_N'], 1)} | {x['squeeze_lt1N_samples']}/{x['n_samples']} |")
    lines += ["", "| Group | trials | G1 pass | pass (rel. core) | observed-move ok | max core slip mm | max core rot ° |",
              "|---|---|---|---|---|---|---|"]
    for g, xs in groups.items():
        lines.append(f"| {g} | {len(xs)} | {sum(x['pass_g1'] for x in xs)} | {sum(x['pass_rel_core'] for x in xs)} | "
                     f"{sum(x['observed_ok'] for x in xs)}/{sum(x['n_moves'] for x in xs)} | "
                     f"{f(max((x['core_slip_mm'] or 0) for x in xs))} | {f(max((x['core_rot_deg'] or 0) for x in xs))} |")
    out = "\n".join(lines)
    print(out)
    (HERE / "results" / "summary.md").write_text(out + "\n", encoding="utf-8")
    (HERE / "results" / "summary.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
