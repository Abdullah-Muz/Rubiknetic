"""Read-only report on an M4 dress-rehearsal results folder (optionally compared with a second folder).

Usage (repo root):  python rehearsal_report.py <results_dir> [<compare_dir>]

Principles
* Verdicts are NOT re-judged. Pass/fail comes from each record's stored "pass", "fail_reasons" and "ok_*" flags, which
  were written by scored.py (M1 criteria) and E4_scored_m4/run.py:apply_m4_criteria (M4 criteria).
* Thresholds printed next to failing values are read (not executed) from the frozen sources:
  src/rubiknetic/cube_physics/scored.py:THRESHOLDS and experiments/E4_scored_m4/run.py module constants (via ast).
  They are only printed for context; they never decide a verdict here.
* Expected trial counts come from experiments/E4_scored_m4/analyze.py:EXPECTED (imported; numpy only) plus E1-6t = 16
  (run.py:e16t_trials, 8 corners x 2 directions).
* Only <dir>/E1-*/*.json are read (the layout written by rehearsal_gap.py). Files that do not parse as JSON, or lack
  "pass"/"fail_reasons", are listed as unreadable/partial and skipped. log.txt is ignored.
* A value that a record does not store is reported as "missing", never inferred.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path.cwd()
SCORED = REPO / "src" / "rubiknetic" / "cube_physics" / "scored.py"
RUN = REPO / "experiments" / "E4_scored_m4" / "run.py"
ANALYZE = REPO / "experiments" / "E4_scored_m4" / "analyze.py"


# ---- frozen constants and helpers reused from the project (read, not re-derived) ----------------------------------
def _module_constants(path: Path, names: set[str]) -> dict:
    tree = ast.parse(path.read_text())
    out = {}
    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        for t in targets:
            if isinstance(t, ast.Name) and t.id in names:
                out[t.id] = ast.literal_eval(value)
            elif isinstance(t, ast.Tuple):       # e.g. P_REL, P_ABS_J = 0.10, 0.05e-3
                ids = [e.id for e in t.elts if isinstance(e, ast.Name)]
                if any(i in names for i in ids):
                    vals = ast.literal_eval(value)
                    out.update({i: v for i, v in zip(ids, vals) if i in names})
    return out


TH = _module_constants(SCORED, {"THRESHOLDS"})["THRESHOLDS"]
M4C = _module_constants(RUN, {"SLOPE_LIMIT_DEG_PER_MOVE", "SNAP_LIMIT_DEG", "SNAP_MIN_SCORED_DEG", "RULE2", "RULE3",
                              "E16T_PEN_LIMIT_MM"})
_spec = importlib.util.spec_from_file_location("m4_analyze", ANALYZE)
AN = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(AN)
EXPECTED_SUB = dict(AN.EXPECTED, **{"E1-6t": 16})
# Folder-level grouping used by rehearsal_gap.py (E1-6 folder holds E1-6a/b/c).
FOLDERS = ["E1-1", "E1-2", "E1-3", "E1-4", "E1-5", "E1-5s", "E1-6", "E1-6t"]
EXPECTED_FOLDER = {"E1-1": 20, "E1-2": 24, "E1-3": 22, "E1-4": 40, "E1-5": 42, "E1-5s": 20,
                   "E1-6": EXPECTED_SUB["E1-6a"] + EXPECTED_SUB["E1-6b"] + EXPECTED_SUB["E1-6c"], "E1-6t": 16}

# ok_* flag -> (stored value key, threshold text). Only used to PRINT the value that the stored flag judged.
TRIAL_FLAG_VALUE = {
    "ok_rest_rotation": ("rest_rotation_deg", f"<= {TH['rest_rotation_deg']} deg"),
    "ok_radial_offset": ("radial_offset_mm_t0", f"<= {TH['radial_offset_mm']} mm"),
    "ok_radial_pop": ("radial_above_nominal_mm", f"<= {TH['radial_above_nominal_mm']} mm"),
    "ok_penetration": ("penetration_mm", f"<= {TH['penetration_mm']} mm"),
    "ok_solved": ("final_solved", "True"),
    "ok_no_motion": ("layer_rotation_deg", f"<= {TH['open_pad_rotation_deg']} deg"),
    "ok_no_separation": ("radial_change_mm", f"<= {TH['opposed_radial_change_mm']} mm"),
    "ok_categorical": ("outcome", "categorical (completed / no_net_move / blocked_unknown legal)"),
    "ok_snap_state": ("final_solved", "valid and solved"),
    "ok_snap": ("U_err_after_1s_deg", f"|x| <= {M4C['SNAP_LIMIT_DEG']} deg"),
    "ok_growth_slope": ("misalignment_growth_slope_deg_per_move", f"< {M4C['SLOPE_LIMIT_DEG_PER_MOVE']} deg/move"),
    "ok_e16t": ("penetration_mm_reported_only", f"solved and <= {M4C['E16T_PEN_LIMIT_MM']} mm"),
    "ok_magnet_validity": (None, "near-pair tilt <= validated tilt"),
}
MOVE_FLAG_VALUE = {
    "ok_turn_error": ("turn_error_deg", f"|x| <= {TH['turn_error_deg']} deg"),
    "ok_drift": ("nontarget_drift_deg", f"<= {TH['nontarget_drift_deg']} deg"),
    "ok_penetration": ("penetration_mm", f"<= {TH['penetration_mm']} mm"),
    "ok_radial_pop": ("radial_above_nominal_mm_so_far", f"<= {TH['radial_above_nominal_mm']} mm"),
    "ok_oracle": ("observed_move", "observed move == commanded and state == oracle"),
    "ok_causal": (None, "pad force threshold reached no later than layer motion"),
}
DRIFT_LIMIT = TH["nontarget_drift_deg"]


# ---- loading ------------------------------------------------------------------------------------------------------
def load(root: Path) -> tuple[dict, list[str], list[str]]:
    """{folder: [record]} plus lists of skipped files and ignored top-level json files."""
    by, skipped = defaultdict(list), []
    for f in sorted(root.glob("E1-*/*.json")):
        try:
            r = json.loads(f.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
            skipped.append(f"{f.parent.name}/{f.name}: unreadable ({type(e).__name__})")
            continue
        if not isinstance(r, dict) or "pass" not in r or "fail_reasons" not in r:
            skipped.append(f"{f.parent.name}/{f.name}: no stored verdict (pass/fail_reasons missing)")
            continue
        r["_file"] = f"{f.parent.name}/{f.name}"
        by[f.parent.name].append(r)
    ignored = sorted(p.name for p in root.glob("*.json"))
    return by, skipped, ignored


def moves(by: dict) -> list[tuple[str, dict, dict]]:
    return [(e, r, m) for e in FOLDERS for r in by.get(e, []) for m in r.get("per_move", [])]


# ---- statistics ---------------------------------------------------------------------------------------------------
def dist(vals) -> dict:
    v = np.asarray([abs(x) for x in vals if x is not None], float)
    if not len(v):
        return {"n": 0}
    return {"n": len(v), "median": float(np.median(v)), "p90": float(np.percentile(v, 90)),
            "p99": float(np.percentile(v, 99)), "max": float(v.max())}


def fmt_dist(d: dict, unit: str) -> str:
    if d["n"] == 0:
        return "missing (not stored in any record)"
    return (f"n={d['n']:5d}  median {d['median']:.3f}  p90 {d['p90']:.3f}  p99 {d['p99']:.3f}  "
            f"max {d['max']:.3f} {unit}")


def metrics(by: dict) -> dict:
    mv = moves(by)
    all_recs = [r for e in FOLDERS for r in by.get(e, [])]
    rule2, rule3 = set(M4C["RULE2"]), set(M4C["RULE3"])

    def tilt(rs):
        return [(r.get("magnet_stats") or {}).get("max_near_tilt_deg") for r in rs]

    return {
        "per-move non-target drift (deg)": (dist(m.get("nontarget_drift_deg") for _, _, m in mv), "deg"),
        "per-move turn error |mean| (deg)": (dist(m.get("turn_error_deg") for _, _, m in mv), "deg"),
        "per-move penetration (mm)": (dist(m.get("penetration_mm") for _, _, m in mv), "mm"),
        "per-move max turner torque (N m)": (dist(m.get("max_turner_torque_Nm") for _, _, m in mv), "N m"),
        "E1-1 rest rotation, per trial (deg)": (dist(r.get("rest_rotation_deg") for r in by.get("E1-1", [])), "deg"),
        "E1-1 penetration, per trial (mm)": (dist(r.get("penetration_mm") for r in by.get("E1-1", [])), "mm"),
        "E1-6t penetration (reported), per trial (mm)": (
            dist(r.get("penetration_mm_reported_only") for r in by.get("E1-6t", [])), "mm"),
        "magnet near-pair tilt, rule-2 (operational) trials (deg)": (
            dist(tilt([r for r in all_recs if r.get("sub_experiment") in rule2])), "deg"),
        "magnet near-pair tilt, rule-3 (abuse) trials (deg)": (
            dist(tilt([r for r in all_recs if r.get("sub_experiment") in rule3])), "deg"),
    }


def counts(by: dict) -> dict:
    mv = moves(by)
    drift_flag = [(e, r, m) for e, r, m in mv if m.get("ok_drift") is False]
    drift_val = [(e, r, m) for e, r, m in mv if (m.get("nontarget_drift_deg") or 0) > DRIFT_LIMIT]
    recs = [r for e in FOLDERS for r in by.get(e, [])]
    return {
        "trials": len(recs),
        "passed": sum(bool(r["pass"]) for r in recs),
        "moves": len(mv),
        "drift_moves_flag": len(drift_flag),
        "drift_moves_value": len(drift_val),
        "drift_trials": len({r["_file"] for _, r, _ in drift_flag}),
        "drift_max": max((m.get("nontarget_drift_deg") for _, _, m in mv if m.get("nontarget_drift_deg") is not None),
                         default=None),
        "causal_fail": sum(m.get("ok_causal") is False for _, _, m in mv),
        "causal_missing": sum("ok_causal" not in m for _, _, m in mv),
        "oracle_ok": sum(m.get("ok_oracle") is True for _, _, m in mv),
        "oracle_missing": sum("ok_oracle" not in m for _, _, m in mv),
        "final_oracle": (sum(r.get("final_matches_oracle") is True for r in recs if "final_matches_oracle" in r),
                         sum("final_matches_oracle" in r for r in recs)),
        "e16m": (sum(m.get("e16m_P_ok") is True for _, _, m in mv), sum("e16m_P_ok" in m for _, _, m in mv)),
        "rule3_labelled": sum(bool(r.get("rule3_label")) for r in recs),
    }


# ---- failure description (stored flags only) ----------------------------------------------------------------------
def _v(x):
    if isinstance(x, float):
        return f"{x:.4g}"
    return repr(x)


def describe_failure(r: dict) -> list[str]:
    out = [f"stored fail_reasons: {r['fail_reasons']}"]
    for k, (vk, thr) in TRIAL_FLAG_VALUE.items():
        if r.get(k) is False:
            if k == "ok_magnet_validity":
                val = (r.get("magnet_stats") or {}).get("max_near_tilt_deg")
                thr = f"<= validated {r.get('validated_tilt_deg')} deg"
            else:
                val = r.get(vk, "missing") if vk else "n/a"
            out.append(f"{k}: {vk or 'tilt'} = {_v(val)} (criterion {thr})")
    for k in ("integrity_ok", "t0_solved"):
        if r.get(k) is False:
            out.append(f"{k} = False")
    if r.get("aborted"):
        out.append(f"aborted: {r['aborted']}")
    if "per_move" in r and "sequence" in r:
        n_seq = len(r["sequence"].split())
        if len(r["per_move"]) != n_seq:
            out.append(f"moves recorded {len(r['per_move'])} of {n_seq} (run stops after an oracle failure)")
    if r.get("final_matches_oracle") is False:
        out.append("final_matches_oracle = False")
    for i, m in enumerate(r.get("per_move", [])):
        for k, (vk, thr) in MOVE_FLAG_VALUE.items():
            if m.get(k) is False:
                if k == "ok_causal":
                    t_f, t_s = m.get("t_pad_force_s"), m.get("t_layer_motion_s")
                    lead = (f"; layer motion leads pad force by {(t_f - t_s) * 1e3:.0f} ms"
                            if t_f is not None and t_s is not None else "")
                    val = f"t_pad_force_s={_v(t_f)}, t_layer_motion_s={_v(t_s)}{lead}"
                elif k == "ok_oracle":
                    val = f"observed {m.get('observed_move')!r} vs commanded {m.get('move')!r}, " \
                          f"valid={m.get('observed_valid')}, inference_error={m.get('inference_error')!r}"
                else:
                    val = f"{vk} = {_v(m.get(vk, 'missing'))}"
                out.append(f"move {i + 1} {m.get('move')}: {k}: {val} (criterion {thr})")
    return out


# ---- report -------------------------------------------------------------------------------------------------------
def report(root: Path, other: Path | None) -> None:
    by, skipped, ignored = load(root)
    print(f"# Rehearsal report: {root}")
    print("Verdicts are the stored ones; nothing is re-judged. Thresholds shown for context are read from "
          "scored.py:THRESHOLDS and run.py constants.")
    if ignored:
        print(f"Ignored top-level JSON (not in an E1-* subfolder): {len(ignored)} files ({', '.join(ignored[:4])}"
              f"{', ...' if len(ignored) > 4 else ''})")
    print(f"Skipped (partial / unreadable): {len(skipped)}")
    for s in skipped:
        print(f"  - {s}")

    print("\n## Pass/fail per experiment")
    print(f"| {'experiment':10} | found / expected | passed | failed | status |")
    for e in FOLDERS:
        rs = by.get(e, [])
        n, p = len(rs), sum(bool(r["pass"]) for r in rs)
        exp = EXPECTED_FOLDER[e]
        status = "missing" if n == 0 else ("complete" if n == exp else f"INCOMPLETE ({exp - n} not present)")
        subs = defaultdict(lambda: [0, 0])
        for r in rs:
            subs[r.get("sub_experiment")][0] += 1
            subs[r.get("sub_experiment")][1] += bool(r["pass"])
        sub_txt = (" [" + ", ".join(f"{s} {v[1]}/{v[0]} of {EXPECTED_SUB.get(s, '?')}" for s, v in sorted(subs.items()))
                   + "]") if e == "E1-6" and rs else ""
        print(f"| {e:10} | {n:3d} / {exp:3d}        | {p:6d} | {n - p:6d} | {status}{sub_txt} |")
    c = counts(by)
    print(f"| {'total':10} | {c['trials']:3d} / {sum(EXPECTED_FOLDER.values()):3d}        | {c['passed']:6d} | "
          f"{c['trials'] - c['passed']:6d} | |")

    print("\n## Failing trials (stored flags; value vs criterion)")
    nfail = 0
    for e in FOLDERS:
        for r in sorted(by.get(e, []), key=lambda r: r.get("trial_id", "")):
            if r["pass"]:
                continue
            nfail += 1
            print(f"* {e}/{r.get('trial_id')} ({r.get('sub_experiment')})")
            for line in describe_failure(r):
                print(f"    {line}")
    if not nfail:
        print("* none")

    print("\n## Distributions (absolute values; median / p90 / p99 / max)")
    for name, (d, unit) in metrics(by).items():
        print(f"* {name:58} {fmt_dist(d, unit)}")
    tilt_sub = defaultdict(list)
    for e in FOLDERS:
        for r in by.get(e, []):
            t = (r.get("magnet_stats") or {}).get("max_near_tilt_deg")
            if t is not None:
                tilt_sub[r.get("sub_experiment")].append(t)
    print("* max near-pair tilt per sub-experiment (deg): " + ", ".join(
        f"{s} {max(v):.2f}" for s, v in sorted(tilt_sub.items())) + f"; rule 2 = {sorted(M4C['RULE2'])}, "
        f"rule 3 = {sorted(M4C['RULE3'])} (run.py)")
    print("* rest rotation outside E1-1, magnet tilt per move, turner torque outside move trials: not stored "
          "(magnet tilt is stored once per trial in magnet_stats)")

    print("\n## Drift, causality and oracle")
    print(f"* moves: {c['moves']}; moves with stored ok_drift = False: {c['drift_moves_flag']} "
          f"(cross-check, value > {DRIFT_LIMIT} deg: {c['drift_moves_value']}); trials with such a move: "
          f"{c['drift_trials']}; max drift {_v(c['drift_max'])} deg")
    miss = f"; ok_causal missing in {c['causal_missing']} moves" if c["causal_missing"] else ""
    print(f"* causality failures (ok_causal = False): {c['causal_fail']} moves{miss}")
    print(f"* oracle agreement (ok_oracle = True): {c['oracle_ok']} / {c['moves']} moves"
          f"{'; ok_oracle missing in ' + str(c['oracle_missing']) + ' moves' if c['oracle_missing'] else ''}; "
          f"final_matches_oracle True in {c['final_oracle'][0]} / {c['final_oracle'][1]} sequence trials")
    print(f"* E1-6m <P> energy bound (e16m_P_ok): {c['e16m'][0]} / {c['e16m'][1]} moves")
    print(f"* rule-3 'outside validated range' labels: {c['rule3_labelled']} trials")
    drift_trials = sorted({(e, r.get("trial_id")) for e, r, m in moves(by) if m.get("ok_drift") is False})
    if drift_trials:
        print("* trials with a drift move: " + ", ".join(f"{e}/{t}" for e, t in drift_trials))

    if other is None:
        return
    ob, oskipped, _ = load(other)
    oc = counts(ob)
    print(f"\n## Side by side: A = {root.name}  vs  B = {other.name}")
    print("NOTE: seeds differ between folders (rehearsal_gap.py --shift); an incomplete A is compared with complete B.")
    print(f"| {'experiment':10} | A pass/found | B pass/found |")
    for e in FOLDERS:
        a, b = by.get(e, []), ob.get(e, [])
        print(f"| {e:10} | {sum(bool(r['pass']) for r in a):4d} / {len(a):3d}   | "
              f"{sum(bool(r['pass']) for r in b):4d} / {len(b):3d}   |")
    rows = [("trials passed / found", f"{c['passed']}/{c['trials']}", f"{oc['passed']}/{oc['trials']}"),
            ("moves", c["moves"], oc["moves"]),
            ("moves with drift > limit", c["drift_moves_flag"], oc["drift_moves_flag"]),
            ("trials with a drift move", c["drift_trials"], oc["drift_trials"]),
            ("max drift (deg)", _v(c["drift_max"]), _v(oc["drift_max"])),
            ("causality failures (moves)", c["causal_fail"], oc["causal_fail"]),
            ("oracle agreement (moves)", f"{c['oracle_ok']}/{c['moves']}", f"{oc['oracle_ok']}/{oc['moves']}"),
            ("skipped files", len(skipped), len(oskipped))]
    print(f"\n| {'quantity':58} | {'A':>22} | {'B':>22} |")
    for q, a, b in rows:
        print(f"| {q:58} | {str(a):>22} | {str(b):>22} |")
    ma, mb = metrics(by), metrics(ob)
    for name in ma:
        da, db = ma[name][0], mb[name][0]
        f = (lambda d: "missing" if d["n"] == 0 else f"n={d['n']} med {d['median']:.3f} p99 {d['p99']:.3f} "
                                                      f"max {d['max']:.3f}")
        print(f"| {name:58} | {f(da):>22} | {f(db):>22} |")

    # Matched comparison: same trial type and same seed offset within the shifted range (seed % 1000).
    def key(r):
        tid = r.get("trial_id", "")
        m = re.match(r"(.*)_s(\d+)$", tid)
        return (r.get("experiment"), m.group(1), int(m.group(2)) % 1000) if m else None
    bidx = {key(r): r for e in FOLDERS for r in ob.get(e, [])}
    pairs = [(r, bidx.get(key(r))) for e in FOLDERS for r in by.get(e, [])]
    matched = [(a, b) for a, b in pairs if b is not None]
    print(f"\n## Matched subset: trials of A paired with B by experiment, trial type and seed offset (seed % 1000)")
    print(f"pairs: {len(matched)} of {len(pairs)} A trials (same pre-registered slot; the seeds differ, so the random "
          f"setup misalignments differ: not the same initial condition)")
    same_seq = sum(a.get("sequence") == b.get("sequence") for a, b in matched)
    print(f"pairs with an identical move sequence: {same_seq} / {len(matched)}")
    if matched:
        sa = {e: {"by": defaultdict(list)} for e in ("A", "B")}
        for a, b in matched:
            sa["A"]["by"][a["experiment"]].append(a)
            sa["B"]["by"][b["experiment"]].append(b)
        ca, cb = counts(sa["A"]["by"]), counts(sa["B"]["by"])
        for q, k in [("trials passed", "passed"), ("moves", "moves"), ("drift moves", "drift_moves_flag"),
                     ("drift trials", "drift_trials"), ("max drift (deg)", "drift_max"),
                     ("causality failures", "causal_fail"), ("oracle ok moves", "oracle_ok")]:
            print(f"| {q:20} | A {_v(ca[k]):>8} | B {_v(cb[k]):>8} |")
        da = metrics(sa["A"]["by"])["per-move non-target drift (deg)"][0]
        db = metrics(sa["B"]["by"])["per-move non-target drift (deg)"][0]
        print(f"| drift distribution   | A {fmt_dist(da, 'deg')} |")
        print(f"|                      | B {fmt_dist(db, 'deg')} |")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    root = Path(args[0])
    other = Path(args[1]) if len(args) > 1 else None
    for p in (root, other):
        if p is not None and not p.is_dir():
            raise SystemExit(f"not a directory: {p}")
    report(root, other)
    # Cross-check with the project's own aggregation helper (analyze._mx), sequence trials only.
    by, _, _ = load(root)
    seq = by.get("E1-2", []) + by.get("E1-3", []) + by.get("E1-4", [])
    print(f"\ncross-check analyze._mx over E1-2..E1-4: drift max {AN._mx(seq, 'nontarget_drift_deg', 'per_move')}, "
          f"turn error max {AN._mx(seq, 'turn_error_deg', 'per_move')}, penetration max "
          f"{AN._mx(seq, 'penetration_mm', 'per_move')}")


if __name__ == "__main__":
    main()
