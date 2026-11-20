"""ER8 analysis (PROTOCOL.md "Analysis" and "Feasibility signals"). Reads ER8's results/ and ER7's results/; prints a
markdown report and writes results/analysis.json.

The per-arm functions are ER7's (er7_analyze.py: option_a, slips, seq_stats), so C52d is judged exactly as C52 was.
Usage (WSL):  ~/.venvs/rubiknetic/bin/python experiments/ER8_derated_core_rehearsal/er8_analyze.py
"""
from __future__ import annotations

import gzip
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RES = HERE / "results"
ER7_RES = REPO / "experiments/ER7_core_magnet_rehearsal/results"
SEQ = ("E1-2", "E1-3", "E1-4")


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


A7 = _load("er7_analyze", "experiments/ER7_core_magnet_rehearsal/er7_analyze.py")
D11 = A7.D11


def load(folder: Path) -> dict:
    out = {}
    for f in sorted(folder.glob("*/*.json.gz")):
        r = json.loads(gzip.decompress(f.read_bytes()))
        out[(r["experiment"], r["trial_id"])] = r
    return out


def paired(a: dict, b: dict, key) -> dict:
    """b - a over common trial keys where both values exist."""
    vals = [(key(a[k]), key(b[k])) for k in sorted(set(a) & set(b))]
    vals = [(x, y) for x, y in vals if x is not None and y is not None]
    if not vals:
        return {"n": 0}
    d = np.array([y - x for x, y in vals])
    return {"n": len(vals), "median_diff": float(np.median(d)), "n_b_lower": int(np.sum(d < 0)),
            "n_equal": int(np.sum(d == 0)), "max_a": float(max(x for x, _ in vals)),
            "max_b": float(max(y for _, y in vals))}


def rest_block(recs: dict) -> dict:
    rest = [r for r in recs.values() if r["sub_experiment"] == "E1-1"]
    ev = {r["trial_id"]: A7.slips(r) for r in rest}
    n60 = sum(bool(v) for v in ev.values())
    n10 = sum(any(e["t_start_s"] <= 10.0 for e in v) for v in ev.values())
    s4 = [r.get("s4_rest60_matches_scored") for r in rest]
    return {"n_rest": len(rest), "rest_passed": sum(bool(r["pass"]) for r in rest),
            "rest_rotation_deg": {r["trial_id"]: r["rest_rotation_deg"] for r in rest},
            "rest_max_deg": max((r["rest_rotation_deg"] for r in rest), default=None),
            "slip_seeds_0_60s": n60, "slip_seeds_0_10s": n10,
            "slip_ci95_0_60s": D11.cp(n60, len(rest)) if rest else None,
            "slip_events": {k: v for k, v in ev.items() if v}, "s4_all_true": bool(s4) and all(x is True for x in s4)}


def regime_block(recs: dict) -> dict:
    st = [r["magnet_stats"] for r in recs.values() if r.get("magnet_stats")]
    return {"flagged_trials": sorted(f"{e}/{t}" for (e, t), r in recs.items() if r.get("er7_flag_outside_regime")),
            "max_near_tilt_deg": max((s["max_near_tilt_deg"] for s in st), default=None),
            "near_perpendicular_total": sum(s.get("near_perpendicular", 0) for s in st),
            "clamped_z_total": sum(s.get("clamped_z", 0) for s in st)}


def main() -> None:
    data = {"L0": load(ER7_RES / "L0"), "C52": load(ER7_RES / "C52"), "C52d": load(RES / "C52d"),
            "C52h": load(RES / "C52h")}
    res = {"arms": {}}
    for arm in ("L0", "C52", "C52d"):
        oa = A7.option_a(data[arm])
        res["arms"][arm] = {"n_records": len(data[arm]), "option_a": oa["option_a"], "complete": oa["complete"],
                            "rows": oa["rows"], "e16m": oa["e16m"], **rest_block(data[arm]),
                            **regime_block(data[arm]),
                            "clip_moves": sum(A7.seq_stats(r)["clip_moves"] for r in data[arm].values()
                                              if r["sub_experiment"] in SEQ)}
    h = data["C52h"]
    res["arms"]["C52h"] = {"n_records": len(h), "complete": len(h) == 20, **rest_block(h), **regime_block(h),
                           "timesteps": sorted({r["params"]["timestep"] for r in h.values()})}

    def sub(d, subs):
        return {k: r for k, r in d.items() if r["sub_experiment"] in subs}

    res["paired"] = {}
    for a, b in (("C52", "C52d"), ("L0", "C52d"), ("C52", "C52h")):
        blk = {"rest_rotation_deg": paired(sub(data[a], ("E1-1",)), sub(data[b], ("E1-1",)),
                                           lambda r: r["rest_rotation_deg"])}
        if b != "C52h":
            blk["seq_max_drift_deg"] = paired(sub(data[a], SEQ), sub(data[b], SEQ),
                                              lambda r: A7.seq_stats(r)["max_drift_deg"])
            blk["seq_max_turner_Nm"] = paired(sub(data[a], SEQ), sub(data[b], SEQ),
                                              lambda r: A7.seq_stats(r)["max_turner_Nm"])
        res["paired"][f"{b}_minus_{a}"] = blk
    d = res["arms"]["C52d"]
    res["signals_C52d"] = {
        "1_no_slips_and_rest_le_0.5": bool(d["n_rest"] == 20 and d["slip_seeds_0_60s"] == 0
                                           and d["rest_max_deg"] is not None and d["rest_max_deg"] <= 0.5),
        "2_option_a_rule": bool(d["option_a"]),
        "3_no_flagged_trials": not d["flagged_trials"],
    }
    res["signals_C52d"]["all_met"] = all(res["signals_C52d"].values())
    hh = res["arms"]["C52h"]
    res["C52h_reported"] = {"complete": hh["complete"], "no_slips": hh["slip_seeds_0_60s"] == 0,
                            "rest_le_0.5": hh["rest_max_deg"] is not None and hh["rest_max_deg"] <= 0.5,
                            "no_flagged_trials": not hh["flagged_trials"]}
    (RES / "analysis.json").write_text(json.dumps(res, indent=1, default=float))

    L = ["# ER8 report (auto-generated by er8_analyze.py)", "", "| Experiment | L0 (ER7) | C52 (ER7) | C52d |",
         "|---|---|---|---|"]
    for e in A7.EXPECTED:
        row = [res["arms"][a]["rows"][e] for a in ("L0", "C52", "C52d")]
        L.append(f"| {e} | " + " | ".join(f"{x['passed']} / {x['n']}" for x in row) + " |")
    L.append("| E1-6m ⟨P⟩ moves | " + " | ".join(
        f"{res['arms'][a]['e16m']['ok']} / {res['arms'][a]['e16m']['moves']}" for a in ("L0", "C52", "C52d")) + " |")
    L.append("")
    for arm in ("L0", "C52", "C52d", "C52h"):
        x = res["arms"][arm]
        lo, hi = x["slip_ci95_0_60s"] or (float("nan"), float("nan"))
        head = (f"Option A rule {'met' if x['option_a'] else 'NOT met'} (complete: {x['complete']}); "
                if "option_a" in x else f"E1-1 only, {x['rest_passed']} / {x['n_rest']} pass (complete: {x['complete']}); ")
        L += [f"**{arm}:** {head}rest max {x['rest_max_deg']}; slip seeds 0–60 s {x['slip_seeds_0_60s']} / "
              f"{x['n_rest']} (95 % CI {lo:.3f}–{hi:.3f}), 0–10 s {x['slip_seeds_0_10s']}; S4 {x['s4_all_true']}; "
              f"flagged {len(x['flagged_trials'])}; max near tilt {x['max_near_tilt_deg']}; near perpendicular "
              f"{x['near_perpendicular_total']}; clamped z {x['clamped_z_total']}"
              + (f"; clip moves {x['clip_moves']}." if "clip_moves" in x else "."), ""]
        if "rows" in x:
            L += [f"Failed trials: { {e: r['failed'] for e, r in x['rows'].items() if r['failed']} }", ""]
    L += ["Paired: " + json.dumps(res["paired"]), "", f"Feasibility signals (C52d): {res['signals_C52d']}", "",
          f"C52h (reported only): {res['C52h_reported']}"]
    print("\n".join(L))


if __name__ == "__main__":
    main()
