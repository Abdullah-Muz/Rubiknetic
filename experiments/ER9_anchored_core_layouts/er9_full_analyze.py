"""ER9 part D analysis (PROTOCOL.md, Part D): ER7's functions applied to one ER9 arm, beside ER7's L0 and C52.
Usage (WSL, repo root):  ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9_full_analyze.py ARM
Writes results/full/<ARM>/analysis.json and prints a report.
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
ER7_RES = REPO / "experiments/ER7_core_magnet_rehearsal/results"
SEQ = ("E1-2", "E1-3", "E1-4")
ARM = sys.argv[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


A7 = _load("er7_analyze", "experiments/ER7_core_magnet_rehearsal/er7_analyze.py")


def load(folder: Path) -> dict:
    out = {}
    for f in sorted(folder.glob("*/*.json.gz")):
        r = json.loads(gzip.decompress(f.read_bytes()))
        out[(r["experiment"], r["trial_id"])] = r
    return out


def block(recs: dict) -> dict:
    oa = A7.option_a(recs)
    rest = [r for r in recs.values() if r["sub_experiment"] == "E1-1"]
    ev = {r["trial_id"]: A7.slips(r) for r in rest}
    n60 = sum(bool(v) for v in ev.values())
    mv = [m for r in recs.values() if r["sub_experiment"] in SEQ for m in r["per_move"]]
    tq = [m["max_turner_torque_Nm"] for m in mv]
    dr = [abs(m["nontarget_drift_deg"]) for m in mv if m.get("nontarget_drift_deg") is not None]
    st = [r["magnet_stats"] for r in recs.values() if r.get("magnet_stats")]
    snap = [r for r in recs.values() if r["sub_experiment"] == "E1-5s" and r.get("snap_is_criterion")]
    return {"n_records": len(recs), "option_a": oa["option_a"], "complete": oa["complete"], "rows": oa["rows"],
            "e16m": oa["e16m"], "n_rest": len(rest),
            "rest_max_deg": max((r["rest_rotation_deg"] for r in rest), default=None),
            "slip_seeds_0_60s": n60, "slip_ci95_0_60s": A7.D11.cp(n60, len(rest)) if rest else None,
            "s4_all_true": bool(rest) and all(r.get("s4_rest60_matches_scored") is True for r in rest),
            "flagged_trials": sorted(f"{e}/{t}" for (e, t), r in recs.items() if r.get("er7_flag_outside_regime")),
            "max_near_tilt_deg": max((s["max_near_tilt_deg"] for s in st), default=None),
            "near_perpendicular_total": sum(s.get("near_perpendicular", 0) for s in st),
            "turner_Nm": {"median": float(np.median(tq)), "p99": float(np.percentile(tq, 99)), "max": float(max(tq))}
            if tq else None,
            "clip_moves": int(sum(t >= 0.999 for t in tq)), "n_moves": len(tq),
            "clip_trials": sum(any(m["max_turner_torque_Nm"] >= 0.999 for m in r["per_move"]) for r in recs.values()
                               if r["sub_experiment"] in SEQ),
            "drift_deg": {"median": float(np.median(dr)), "max": float(max(dr))} if dr else None,
            "snap_abs_err_max_deg": max((abs(r["U_err_after_1s_deg"]) for r in snap), default=None),
            "wall_h": sum(r.get("er7_wall_s", 0.0) for r in recs.values()) / 3600}


def paired(a: dict, b: dict, subs, key) -> dict:
    ks = [k for k in sorted(set(a) & set(b)) if a[k]["sub_experiment"] in subs]
    v = [(key(a[k]), key(b[k])) for k in ks]
    v = [(x, y) for x, y in v if x is not None and y is not None]
    d = np.array([y - x for x, y in v])
    return {"n": len(v), "median_diff": float(np.median(d)), "n_arm_lower": int(np.sum(d < 0))} if v else {"n": 0}


def main() -> None:
    data = {"L0": load(ER7_RES / "L0"), "C52": load(ER7_RES / "C52"), ARM: load(HERE / "results" / "full" / ARM)}
    res = {"arms": {a: block(r) for a, r in data.items()}, "paired": {}}
    for ref in ("L0", "C52"):
        res["paired"][f"{ARM}_minus_{ref}"] = {
            "rest_rotation_deg": paired(data[ref], data[ARM], ("E1-1",), lambda r: r["rest_rotation_deg"]),
            "seq_max_drift_deg": paired(data[ref], data[ARM], SEQ, lambda r: A7.seq_stats(r)["max_drift_deg"]),
            "seq_max_turner_Nm": paired(data[ref], data[ARM], SEQ, lambda r: A7.seq_stats(r)["max_turner_Nm"])}
    probe = load(HERE / "results" / "probe" / ARM)
    same = [k for k in probe if k in data[ARM]]
    res["probe_reproduced"] = {
        "n_common": len(same),
        "pass_flags_equal": all(probe[k]["pass"] == data[ARM][k]["pass"] for k in same),
        "values_equal": all(probe[k].get(f) == data[ARM][k].get(f) for k in same
                            for f in ("rest_rotation_deg", "U_err_after_1s_deg"))}
    x = res["arms"][ARM]
    res["signals"] = {
        "1_no_slips_and_rest_le_0.5": bool(x["n_rest"] == 20 and x["slip_seeds_0_60s"] == 0
                                           and x["rest_max_deg"] is not None and x["rest_max_deg"] <= 0.5),
        "2_option_a_rule": bool(x["option_a"]), "3_no_flagged_trials": not x["flagged_trials"]}
    res["signals"]["all_met"] = all(res["signals"].values())
    (HERE / "results" / "full" / ARM / "analysis.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"| Experiment | L0 | C52 | {ARM} |\n|---|---|---|---|")
    for e in A7.EXPECTED:
        print(f"| {e} | " + " | ".join(f"{res['arms'][a]['rows'][e]['passed']} / {res['arms'][a]['rows'][e]['n']}"
                                         for a in data) + " |")
    print("| E1-6m moves | " + " | ".join(f"{res['arms'][a]['e16m']['ok']} / {res['arms'][a]['e16m']['moves']}"
                                           for a in data) + " |")
    for a in data:
        b = res["arms"][a]
        print(f"\n{a}: Option A {'met' if b['option_a'] else 'NOT met'} (complete {b['complete']}); rest max "
              f"{b['rest_max_deg']:.3g}; slip seeds {b['slip_seeds_0_60s']} / {b['n_rest']}; S4 {b['s4_all_true']}; "
              f"flagged {len(b['flagged_trials'])}; max tilt {b['max_near_tilt_deg']:.2f}; turner {b['turner_Nm']}; "
              f"clip moves {b['clip_moves']} / {b['n_moves']} in {b['clip_trials']} trials; drift {b['drift_deg']}; "
              f"snap max {b['snap_abs_err_max_deg']}; wall {b['wall_h']:.2f} h")
        print("   failed:", {e: r["failed"] for e, r in b["rows"].items() if r["failed"]})
    print("\npaired:", json.dumps(res["paired"]))
    print("probe reproduced:", res["probe_reproduced"])
    print("signals:", res["signals"])


if __name__ == "__main__":
    main()
