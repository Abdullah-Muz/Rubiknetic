"""ER7 analysis (PROTOCOL.md "Analysis" and "Feasibility signals"). Reads results/; prints a markdown report and writes
results/analysis.json.

Per arm, M5's Option A rule as its analyze.py applies it (verdict(): every stored per-trial `pass` flag of the 204
trials, by sub-experiment, and E1-6m <P> for every move of E1-2..E1-4). Slip events by D11's definition (any piece
changing by >= 0.2 deg within 200 ms in the 60 s instrumented rest). Paired differences on the same seeds.
Usage (WSL):  ~/.venvs/rubiknetic/bin/python experiments/ER7_core_magnet_rehearsal/er7_analyze.py
"""
from __future__ import annotations

import gzip
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RES = HERE / "results"
ARMS = ("L0", "C52")
EXPECTED = {"E1-1": 20, "E1-2": 24, "E1-3": 22, "E1-4": 40, "E1-5": 42, "E1-5s": 20, "E1-6a": 6, "E1-6b": 6,
            "E1-6c": 8, "E1-6t": 16}
M5_EXPECTED_PASSED = {"E1-1": 19}   # M5 scored record (P-51): every other row passed in full


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


D11 = _load("d11_analyze", "experiments/D11_rest_slip_count/d11_analyze.py")   # events() and cp() only


def load(arm: str) -> dict:
    out = {}
    for f in sorted((RES / arm).glob("*/*.json.gz")):
        r = json.loads(gzip.decompress(f.read_bytes()))
        out[(r["experiment"], r["trial_id"])] = r
    return out


def option_a(recs: dict) -> dict:
    by = defaultdict(list)
    for r in recs.values():
        by[r["sub_experiment"]].append(r)
    rows = {e: {"n": len(by[e]), "expected": EXPECTED[e], "passed": sum(bool(r["pass"]) for r in by[e]),
                "failed": sorted(r["trial_id"] for r in by[e] if not r["pass"])} for e in EXPECTED}
    p_ok = [m.get("e16m_P_ok") for e in ("E1-2", "E1-3", "E1-4") for r in by[e] for m in r.get("per_move", [])]
    e16m = {"moves": len(p_ok), "ok": sum(x is True for x in p_ok)}
    e16m["pass"] = bool(p_ok) and e16m["ok"] == e16m["moves"]
    complete = all(rows[e]["n"] == rows[e]["expected"] for e in EXPECTED)
    passes = complete and all(rows[e]["passed"] == rows[e]["n"] for e in EXPECTED) and e16m["pass"]
    return {"rows": rows, "e16m": e16m, "complete": complete, "option_a": passes, "by": by}


def slips(rec: dict) -> list[dict]:
    r60 = rec.get("rest60")
    if not r60:
        return []
    t = np.array(r60["timeseries"]["t"]) - r60["timeseries"]["t"][0] + 0.025
    return D11.events(r60, t)


def seq_stats(r: dict) -> dict:
    mv = r.get("per_move", [])
    dr = [abs(x["nontarget_drift_deg"]) for x in mv if x.get("nontarget_drift_deg") is not None]
    tq = [x.get("max_turner_torque_Nm") for x in mv if x.get("max_turner_torque_Nm") is not None]
    return {"max_drift_deg": max(dr) if dr else None, "max_turner_Nm": max(tq) if tq else None,
            "clip_moves": sum(t >= 0.999 for t in tq)}


def paired(a: dict, b: dict, key) -> dict:
    """b - a over common trial keys where both values exist; median and count of b < a."""
    vals = [(key(a[k]), key(b[k])) for k in sorted(set(a) & set(b))]
    vals = [(x, y) for x, y in vals if x is not None and y is not None]
    if not vals:
        return {"n": 0}
    d = np.array([y - x for x, y in vals])
    return {"n": len(vals), "median_diff": float(np.median(d)), "n_C52_lower": int(np.sum(d < 0)),
            "n_equal": int(np.sum(d == 0)), "max_L0": float(max(x for x, _ in vals)),
            "max_C52": float(max(y for _, y in vals))}


def main() -> None:
    data = {arm: load(arm) for arm in ARMS}
    res = {"arms": {}}
    for arm in ARMS:
        recs = data[arm]
        oa = option_a(recs)
        rest = [r for r in recs.values() if r["sub_experiment"] == "E1-1"]
        ev = {r["trial_id"]: slips(r) for r in rest}
        n_slip60 = sum(bool(v) for v in ev.values())
        n_slip10 = sum(any(e["t_start_s"] <= 10.0 for e in v) for v in ev.values())
        flags = sorted(f"{e}/{t}" for (e, t), r in recs.items() if r.get("er7_flag_outside_regime"))
        s4 = [r.get("s4_rest60_matches_scored") for r in rest]
        res["arms"][arm] = {
            "n_records": len(recs), "option_a": oa["option_a"], "complete": oa["complete"], "rows": oa["rows"],
            "e16m": oa["e16m"],
            "rest_rotation_deg": {r["trial_id"]: r["rest_rotation_deg"] for r in rest},
            "rest_max_deg": max((r["rest_rotation_deg"] for r in rest), default=None),
            "slip_seeds_0_60s": n_slip60, "slip_seeds_0_10s": n_slip10, "n_rest": len(rest),
            "slip_ci95_0_60s": D11.cp(n_slip60, len(rest)) if rest else None,
            "slip_events": {k: v for k, v in ev.items() if v},
            "s4_all_true": bool(s4) and all(x is True for x in s4),
            "flagged_trials": flags,
            "max_near_tilt_deg": max((r["magnet_stats"]["max_near_tilt_deg"] for r in recs.values()
                                      if r.get("magnet_stats")), default=None),
            "near_perpendicular_total": sum(r["magnet_stats"].get("near_perpendicular", 0)
                                            for r in recs.values() if r.get("magnet_stats")),
            "clamped_z_total": sum(r["magnet_stats"].get("clamped_z", 0) for r in recs.values() if r.get("magnet_stats")),
        }
    a, b = data["L0"], data["C52"]
    rest_a = {k: r for k, r in a.items() if r["sub_experiment"] == "E1-1"}
    rest_b = {k: r for k, r in b.items() if r["sub_experiment"] == "E1-1"}
    seq_a = {k: r for k, r in a.items() if r["sub_experiment"] in ("E1-2", "E1-3", "E1-4")}
    seq_b = {k: r for k, r in b.items() if r["sub_experiment"] in ("E1-2", "E1-3", "E1-4")}
    res["paired"] = {
        "rest_rotation_deg": paired(rest_a, rest_b, lambda r: r["rest_rotation_deg"]),
        "seq_max_drift_deg": paired(seq_a, seq_b, lambda r: seq_stats(r)["max_drift_deg"]),
        "seq_max_turner_Nm": paired(seq_a, seq_b, lambda r: seq_stats(r)["max_turner_Nm"]),
    }
    res["clip_moves"] = {arm: sum(seq_stats(r)["clip_moves"] for r in data[arm].values()
                                  if r["sub_experiment"] in ("E1-2", "E1-3", "E1-4")) for arm in ARMS}
    c = res["arms"]["C52"]
    res["signals"] = {
        "1_no_slips_and_rest_le_0.5": bool(c["n_rest"] == 20 and c["slip_seeds_0_60s"] == 0
                                           and c["rest_max_deg"] is not None and c["rest_max_deg"] <= 0.5),
        "2_option_a_rule": bool(c["option_a"]),
        "3_no_flagged_trials": not c["flagged_trials"],
    }
    res["signals"]["all_met"] = all(res["signals"].values())
    (RES / "analysis.json").write_text(json.dumps(res, indent=1, default=float))

    L = ["# ER7 report (auto-generated by er7_analyze.py)", "", "| Experiment | L0 passed / n | C52 passed / n |",
         "|---|---|---|"]
    for e in EXPECTED:
        ra, rb = res["arms"]["L0"]["rows"][e], res["arms"]["C52"]["rows"][e]
        L.append(f"| {e} | {ra['passed']} / {ra['n']} | {rb['passed']} / {rb['n']} |")
    for arm in ARMS:
        m = res["arms"][arm]["e16m"]
        L.append(f"| E1-6m ⟨P⟩ moves ({arm}) | {m['ok']} / {m['moves']} | |")
    L.append("")
    for arm in ARMS:
        x = res["arms"][arm]
        lo, hi = x["slip_ci95_0_60s"] or (None, None)
        L += [f"**{arm}:** Option A rule {'met' if x['option_a'] else 'NOT met'} (complete: {x['complete']}); "
              f"rest max {x['rest_max_deg']}; slip seeds 0–60 s {x['slip_seeds_0_60s']} / {x['n_rest']} "
              f"(95 % CI {lo:.3f}–{hi:.3f}), 0–10 s {x['slip_seeds_0_10s']}; S4 {x['s4_all_true']}; "
              f"flagged {len(x['flagged_trials'])}; max near tilt {x['max_near_tilt_deg']}; "
              f"near perpendicular {x['near_perpendicular_total']}; clamped z {x['clamped_z_total']}.",
              f"Failed trials: { {e: r['failed'] for e, r in x['rows'].items() if r['failed']} }", ""]
    L += ["Paired (C52 − L0): " + json.dumps(res["paired"]), "", f"Clip moves: {res['clip_moves']}", "",
          f"Feasibility signals (C52): {res['signals']}"]
    print("\n".join(L))


if __name__ == "__main__":
    main()
