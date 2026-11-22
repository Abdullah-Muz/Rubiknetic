"""D12 analysis (PROTOCOL.md section 11, fixed before Stage 1). Reads the replay and Stage 4 records; never simulates.

Rules implemented here (pure functions on record dicts, unit-tested on synthetic records):
  * noise yardstick: per layout, range of the R5 catch impulse over the 5 nominal seeds (non-jam, non-crash);
  * trend (Stage 1, per slice of the grid): monotone across the three levels on >= 2 of 3 grid seeds in the direction
    of the median difference, and |median(extreme) - median(extreme)| > the layout's nominal range;
  * one-factor effect (Stage 2): the median over 3 seeds moves by more than the nominal range, in the same direction on
    >= 2 of 3 seeds (seed-paired against the point's own Stage 1 replays);
  * classes per point; jam table; "jam under R1, completes under R5"; worst no-magnet point (section 7.2);
    candidates (section 7.3, cap 6); catch-free; Stage 4 settings (cap 3) and guard rails (section 7.4);
  * prediction checks Pr1-Pr7 (held / not held / not testable);
  * S6 / S7 on the records and the threshold freeze (one THRESHOLDS hash across all records).
Jam replays keep their measures in the records but are excluded from medians, trends and the worst-point choice.
Crashed replays are listed and never counted as a class.

Usage (WSL, repo root):  ~/.venvs/rubiknetic/bin/python experiments/D12_turn_stall/d12_analyze.py
Writes results/analysis/report.json and report.md.
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import d12_common as C  # noqa: E402

OUT = HERE / "results"
RECORD_FOLDERS = ("selfcheck", "timing", "stage1", "stage2", "stage3", "stage4")


# ---- loading --------------------------------------------------------------------------------------------------------
def load_records(root: Path = OUT) -> list[dict]:
    out = []
    for folder in RECORD_FOLDERS:
        for f in sorted((root / folder).glob("*.json.gz")):
            r = json.loads(gzip.decompress(f.read_bytes()))
            r["_path"] = str(f)
            out.append(r)
    return out


def key_of(rec: dict) -> tuple:
    j = rec["job"]
    return (j["layout"], C.setting_tag(j["setting"]), j["rig"], j["seed"])


def index(records: list[dict]) -> dict:
    """{(layout, setting tag, rig, seed): record} for replay records (first record wins; job ids are unique). Timing
    re-runs (job purpose 'timing') duplicate self-check replays and stay out of the stage analysis."""
    out = {}
    for r in records:
        if r.get("job", {}).get("kind") == "replay" and not r["job"].get("purpose"):
            out.setdefault(key_of(r), r)
    return out


def usable(rec: dict | None) -> bool:
    return rec is not None and not rec.get("crash", False)


def is_jam(rec: dict) -> bool:
    return rec.get("class") == "jam"


def _med(xs):
    xs = [x for x in xs if x is not None]
    return float(np.median(xs)) if xs else None


# ---- points ---------------------------------------------------------------------------------------------------------
def point_records(idx: dict, layout: str, st: dict, rig: str, seeds) -> dict:
    tag = C.setting_tag(st)
    return {s: idx.get((layout, tag, rig, s)) for s in seeds}


def point_summary(idx: dict, layout: str, st: dict, rig: str, seeds=C.GRID_SEEDS) -> dict:
    recs = point_records(idx, layout, st, rig, seeds)
    rows, imp, wpk, snaps, sig = {}, [], [], 0, 0
    n_jam = n_crash = n_missing = 0
    flags = {"censored_R5": 0, "pad_limited": 0, "above_warning": 0, "validity_flagged": 0}
    for s, r in recs.items():
        if r is None:
            n_missing += 1
            rows[s] = {"class": "missing"}
            continue
        if r.get("crash"):
            n_crash += 1
            rows[s] = {"class": "crash", "error": r.get("error")}
            continue
        rows[s] = {"class": r["class"], "catch_impulse_Nms": r["catch_impulse_Nms"], "window_peak_Nm": r["window_peak_Nm"],
                   "baseline_Nm": r["baseline_Nm"], "flags": r["flags"], "validity_flagged": r["validity"]["flagged"],
                   "jam": r["jam"] if is_jam(r) else None}
        flags["validity_flagged"] += int(bool(r["validity"]["flagged"]))
        for f in ("censored_R5", "pad_limited", "above_warning"):
            flags[f] += int(bool(r["flags"].get(f)))
        if is_jam(r):
            n_jam += 1
            continue
        imp.append(r["catch_impulse_Nms"])
        wpk.append(r["window_peak_Nm"])
        for sn in (r.get("snapshot_catch"), r.get("snapshot_max_normal")):
            if sn is not None:
                snaps += 1
                sig += int(bool(sn.get("signature")))
    return {"layout": layout, "setting": st, "tag": C.setting_tag(st), "rig": rig, "seeds": rows,
            "median_catch_impulse_Nms": _med(imp), "median_window_peak_Nm": _med(wpk), "n_jam": n_jam,
            "n_crash": n_crash, "n_missing": n_missing, "signature_share": (sig / snaps) if snaps else None,
            "flag_counts": flags}


def nominal_range(idx: dict, layout: str) -> float | None:
    vals = [r["catch_impulse_Nms"] for r in point_records(idx, layout, C.NOMINAL, "R5", C.NOMINAL_SEEDS).values()
            if usable(r) and not is_jam(r)]
    return float(max(vals) - min(vals)) if len(vals) >= 2 else None


def _impulse(r):
    return r["catch_impulse_Nms"] if usable(r) and not is_jam(r) else None


def trend(idx: dict, layout: str, factor: str, fixed: float) -> dict:
    """Section 11 'Trend' for one slice: factor 'gap' at a fixed chamfer, or 'chamfer' at a fixed gap."""
    levels = C.GAPS if factor == "gap" else C.CHAMFERS
    sts = [C.setting(v, fixed) if factor == "gap" else C.setting(fixed, v) for v in levels]
    per_seed, excluded = {}, 0
    for s in C.GRID_SEEDS:
        vals = [_impulse(idx.get((layout, C.setting_tag(st), "R5", s))) for st in sts]
        excluded += sum(v is None for v in vals)
        per_seed[s] = vals
    meds = [_med([per_seed[s][i] for s in C.GRID_SEEDS]) for i in range(3)]
    rng = nominal_range(idx, layout)
    diff = None if meds[0] is None or meds[2] is None else meds[2] - meds[0]
    direction = 0 if not diff else int(np.sign(diff))
    mono = {}
    for s, v in per_seed.items():
        if any(x is None for x in v):
            mono[s] = None
        elif v[0] < v[1] < v[2]:
            mono[s] = 1
        elif v[0] > v[1] > v[2]:
            mono[s] = -1
        else:
            mono[s] = 0
    n_mono = sum(1 for d in mono.values() if d is not None and d != 0 and d == direction)
    ok = bool(rng is not None and diff is not None and abs(diff) > rng and n_mono >= 2)
    return {"layout": layout, "factor": factor, "fixed": fixed, "levels": list(levels), "per_seed": per_seed,
            "medians": meds, "median_diff_extremes": diff, "nominal_range": rng, "monotone_by_seed": mono,
            "n_monotone_in_direction": n_mono, "excluded_jam_or_crash": excluded, "trend": ok,
            "reading": ("trend " + ("rising" if direction > 0 else "falling")) if ok else
            "no trend distinguishable from seed spread"}


def effect(idx: dict, layout: str, point: dict, check: str) -> dict:
    """Section 11 'One-factor effect' (Stage 2)."""
    ref = point_records(idx, layout, point, "R5", C.GRID_SEEDS)
    chk = point_records(idx, layout, C.setting(point["gap"], point["chamfer"], check), "R5", C.GRID_SEEDS)
    r_imp = {s: _impulse(r) for s, r in ref.items()}
    c_imp = {s: _impulse(r) for s, r in chk.items()}
    mr, mc = _med(r_imp.values()), _med(c_imp.values())
    rng = nominal_range(idx, layout)
    delta = None if mr is None or mc is None else mc - mr
    d = 0 if not delta else int(np.sign(delta))
    same = sum(1 for s in C.GRID_SEEDS if r_imp[s] is not None and c_imp[s] is not None
               and d != 0 and int(np.sign(c_imp[s] - r_imp[s])) == d)
    ok = bool(rng is not None and delta is not None and abs(delta) > rng and same >= 2)
    return {"layout": layout, "point": point, "check": check, "label": C.CHECKS[check]["label"], "ref": r_imp,
            "check_values": c_imp, "median_ref": mr, "median_check": mc, "delta": delta, "nominal_range": rng,
            "n_same_direction": same, "effect": ok,
            "classes": {s: (None if not usable(r) else r["class"]) for s, r in chk.items()},
            "reading": (("raises" if d > 0 else "lowers") + " the catch impulse") if ok else "no effect beyond seed spread"}


def grid_points() -> list[dict]:
    return [C.setting(g, c) for g in C.GAPS for c in C.CHAMFERS]


def worst_none_point(idx: dict) -> tuple[dict | None, list]:
    """Section 7.2 P-none: among the no-magnet grid points with no jam on any of the 3 grid seeds, the largest median
    R5 catch impulse. A point with a crashed or missing replay does not qualify (reported)."""
    table, best = [], None
    for st in grid_points():
        ps = point_summary(idx, "none", st, "R5")
        q = ps["n_jam"] == 0 and ps["n_crash"] == 0 and ps["n_missing"] == 0
        table.append({"tag": ps["tag"], "qualifies": q, "median_catch_impulse_Nms": ps["median_catch_impulse_Nms"],
                      "n_jam": ps["n_jam"], "n_crash": ps["n_crash"], "n_missing": ps["n_missing"]})
        if q and (best is None or ps["median_catch_impulse_Nms"] > best[1]):
            best = (st, ps["median_catch_impulse_Nms"])
    return (best[0] if best else None), table


def _absent_unflagged(r) -> bool:
    return usable(r) and r["class"] == "absent" and not r["validity"]["flagged"]


def candidate_settings(idx: dict, p_none: dict | None) -> list[tuple[str, dict]]:
    out = [(lay, st) for lay in C.CANDIDATE_LAYOUTS for st in grid_points()]
    if p_none is not None:
        out += [("none", C.setting(p_none["gap"], p_none["chamfer"], chk)) for chk in C.CHECKS]
    return out


def candidates(idx: dict, p_none: dict | None) -> dict:
    """Section 7.3: none/L0 settings 'absent' on all 3 grid seeds under R5, jam-free, not validity-flagged; at most 6
    (lowest median R5 catch impulse), the rest listed."""
    found = []
    for lay, st in candidate_settings(idx, p_none):
        recs = point_records(idx, lay, st, "R5", C.GRID_SEEDS)
        if all(_absent_unflagged(r) for r in recs.values()):
            found.append((lay, st, _med([r["catch_impulse_Nms"] for r in recs.values()])))
    found.sort(key=lambda x: (x[2], x[0], C.setting_tag(x[1])))
    return {"selected": [(lay, st) for lay, st, _ in found[:6]], "listed_beyond_cap": [(lay, st) for lay, st, _ in found[6:]],
            "medians": {f"{lay}:{C.setting_tag(st)}": m for lay, st, m in found}}


def catch_free(idx: dict, layout: str, st: dict) -> dict:
    """Section 7.3: all 8 R5 replays (3 grid + 5 Stage 3) and all 3 R1 replays absent, jam-free, not flagged."""
    r5 = point_records(idx, layout, st, "R5", C.GRID_SEEDS + tuple(s for s, _ in C.STAGE3_R5))
    r1 = point_records(idx, layout, st, "R1", C.GRID_SEEDS)
    ok = all(_absent_unflagged(r) for r in list(r5.values()) + list(r1.values()))
    return {"layout": layout, "setting": st, "catch_free": bool(ok),
            "R5": {s: (None if r is None else ("crash" if r.get("crash") else r["class"])) for s, r in r5.items()},
            "R1": {s: (None if r is None else ("crash" if r.get("crash") else r["class"])) for s, r in r1.items()},
            "median_R5_impulse": _med([_impulse(r) for r in r5.values()])}


def stage4_settings(idx: dict, passing: list[tuple[str, dict]]) -> dict:
    """Section 7.4: settings passing Stage 3 run in L0; at most 3, by the lowest median R5 catch impulse in L0 (grid
    seeds). A setting with no L0 R5 data (a Stage 2 check found in 'none') is ranked by its own layout's median."""
    seen, rows = set(), []
    for lay, st in passing:
        tag = C.setting_tag(st)
        if tag in seen:
            continue
        seen.add(tag)
        m_l0 = _med([_impulse(r) for r in point_records(idx, "L0", st, "R5", C.GRID_SEEDS).values()])
        m_own = _med([_impulse(r) for r in point_records(idx, lay, st, "R5", C.GRID_SEEDS).values()])
        rows.append({"setting": st, "found_in": lay, "median_R5_L0": m_l0, "median_R5_own": m_own,
                     "rank_value": m_l0 if m_l0 is not None else m_own,
                     "ranked_by": "L0" if m_l0 is not None else f"{lay} (no L0 R5 data)"})
    rows.sort(key=lambda r: (r["rank_value"] if r["rank_value"] is not None else np.inf, C.setting_tag(r["setting"])))
    return {"selected": [r["setting"] for r in rows[:3]], "returned_to_user": [r["setting"] for r in rows[3:]],
            "rows": rows}


def stage4_verdicts(records: list[dict]) -> dict:
    out: dict = {}
    for r in records:
        if r.get("job", {}).get("kind") != "stage4":
            continue
        tag = C.setting_tag(r["job"]["setting"])
        o = out.setdefault(tag, {"setting": r["job"]["setting"], "drift": [], "rest": [], "snap": [], "crash": [],
                                 "validity_flagged": 0})
        if r.get("crash"):
            o["crash"].append(r["job_id"])
            continue
        g = r["guard_rail"]
        o["validity_flagged"] += int(bool(r["validity"]["flagged"]))
        kind = r["job"]["trial_kind"]
        o["drift" if kind == "seq" else kind].append({"job_id": r["job_id"], **g})
    for tag, o in out.items():
        # drift is read on complete sequences only; an incomplete one (oracle mismatch / abort) fails the guard rail
        # for that reason, never as a drift failure
        done = [x for x in o["drift"] if not x.get("incomplete", not x.get("complete", True))]
        incomplete = [x["job_id"] for x in o["drift"] if x not in done]
        drift_fail = any(x["drift_fail"] for x in done)
        drift_flag = any(x["drift_flag"] for x in done)
        complete = len(o["drift"]) == 4 and len(o["rest"]) == 2 and len(o["snap"]) == 2 and not o["crash"]
        o["summary"] = {"complete": complete, "drift_fail": drift_fail, "drift_flag": drift_flag,
                        "incomplete_sequences": incomplete, "n_sequences_complete": len(done),
                        "max_drift_deg": max((x["max_drift_deg"] or 0.0) for x in done) if done else None,
                        "rest_pass": bool(o["rest"]) and all(x["pass"] for x in o["rest"]),
                        "snap_pass": bool(o["snap"]) and all(x["pass"] for x in o["snap"])}
        s = o["summary"]
        s["passes_guard_rails"] = bool(complete and not incomplete and not drift_fail and s["rest_pass"]
                                       and s["snap_pass"])
        if s["passes_guard_rails"]:
            reading = "passes (screening signal on 8 trials only, not G1 evidence)"
        elif drift_fail:
            reading = "trades the stall for drift"
        elif incomplete:
            reading = "fails a guard rail (sequence incomplete: oracle/abort)"
        else:
            reading = "fails a guard rail"
        s["reading"] = reading + (" (drift flag >= 0.8 deg)" if drift_flag and not drift_fail else "")
    return out


def jam_table(idx: dict) -> list[dict]:
    groups: dict = {}
    for (lay, tag, rig, s), r in idx.items():
        g = groups.setdefault((lay, tag, rig), {"layout": lay, "tag": tag, "rig": rig, "n": 0, "k_jam": 0, "jams": []})
        if not usable(r):
            continue
        g["n"] += 1
        if is_jam(r):
            g["k_jam"] += 1
            g["jams"].append({"seed": s, "J1": r["jam"]["J1"]["fired"], "J2": r["jam"]["J2"]["fired"],
                              "J3": r["jam"]["J3"]["fired"], "shortfall_deg": r["jam"]["J1"]["shortfall_deg"],
                              "max_penetration_mm": r["jam"]["J2"]["max_penetration_mm"], "flags": r["flags"]})
    return [g for g in sorted(groups.values(), key=lambda g: (g["layout"], g["tag"], g["rig"])) if g["k_jam"]]


def r1_jam_r5_completes(idx: dict) -> list[dict]:
    """Section 5: 'jam under R1, completes under R5' (the resistance lies between 1 and 5 N m)."""
    out = []
    for (lay, tag, rig, s), r in idx.items():
        if rig != "R1" or not usable(r) or not is_jam(r):
            continue
        r5 = idx.get((lay, tag, "R5", s))
        if usable(r5) and not is_jam(r5):
            out.append({"layout": lay, "tag": tag, "seed": s, "R5_class": r5["class"],
                        "R5_window_peak_Nm": r5["window_peak_Nm"], "R5_peak_Nm": r5["peak_abs_torque_Nm"]})
    return out


# ---- predictions (section 7.0) --------------------------------------------------------------------------------------
def _held(x):
    return "not testable" if x is None else ("held" if x else "not held")


def predictions(idx: dict, s4: dict, p_none: dict | None, passing: list[tuple[str, dict]]) -> dict:
    out = {}
    # Pr1: none at nominal, R5 window peak >= 1 N m on >= 2 of 3 grid seeds, or a replay jams
    recs = [r for r in point_records(idx, "none", C.NOMINAL, "R5", C.GRID_SEEDS).values() if usable(r)]
    if len(recs) < 3:
        out["Pr1"] = {"result": "not testable", "why": "missing or crashed replays"}
    else:
        n_hi = sum(1 for r in recs if not is_jam(r) and r["window_peak_Nm"] >= 1.0)
        n_jam = sum(1 for r in recs if is_jam(r))
        out["Pr1"] = {"result": _held(n_hi >= 2 or n_jam >= 1), "n_peak_ge_1": n_hi, "n_jam": n_jam}
    # Pr2: (a) L0 no gap trend at chamfer 1.4; (b) none present at (0.25, 1.4) on >= 1 seed; (c) drift rises with gap
    t = trend(idx, "L0", "gap", C.NOMINAL_CHAMFER)
    a = None if t["nominal_range"] is None or t["median_diff_extremes"] is None else (not t["trend"])
    nr = [r for r in point_records(idx, "none", C.setting(2.5e-4, C.NOMINAL_CHAMFER), "R5", C.GRID_SEEDS).values()
          if usable(r)]
    b = None if not nr else any(r["class"] == "present" for r in nr)
    ok4 = [v for v in s4.values() if v["summary"]["n_sequences_complete"] > 0]
    gaps4 = sorted({v["setting"]["gap"] for v in ok4})
    c = None
    if len(gaps4) >= 2:
        md = {g: max(v["summary"]["max_drift_deg"] for v in ok4 if v["setting"]["gap"] == g) for g in gaps4}
        c = all(md[gaps4[i]] < md[gaps4[i + 1]] for i in range(len(gaps4) - 1))
    parts = [a, b, c]
    tested = [x for x in parts if x is not None]
    out["Pr2"] = {"result": "not testable" if not tested else _held(all(tested)),
                  "a_L0_no_gap_trend": _held(a), "b_none_catch_at_0.25mm": _held(b), "c_drift_rises_with_gap": _held(c)}
    # Pr3: chamfer 1.0 raises L0's catch beyond seed spread; 2.0 changes it little (tilt flag reported)
    rng = nominal_range(idx, "L0")
    m = {c_: _med([_impulse(r) for r in point_records(idx, "L0", C.setting(C.NOMINAL_GAP, c_), "R5",
                                                        C.GRID_SEEDS).values()]) for c_ in C.CHAMFERS}
    if rng is None or any(v is None for v in m.values()):
        out["Pr3"] = {"result": "not testable", "medians": m, "nominal_range": rng}
    else:
        r10 = point_records(idx, "L0", C.setting(C.NOMINAL_GAP, 0.0010), "R5", C.GRID_SEEDS)
        r14 = point_records(idx, "L0", C.NOMINAL, "R5", C.GRID_SEEDS)
        same = sum(1 for s in C.GRID_SEEDS if _impulse(r10[s]) is not None and _impulse(r14[s]) is not None
                   and _impulse(r10[s]) > _impulse(r14[s]))
        raises = (m[0.0010] - m[0.0014]) > rng and same >= 2
        little = abs(m[0.0020] - m[0.0014]) <= rng
        tilt = sum(1 for r in r10.values() if usable(r) and r["validity"]["flagged"])
        out["Pr3"] = {"result": _held(raises and little), "raises_at_1.0": raises, "little_change_at_2.0": little,
                      "medians": {str(k): v for k, v in m.items()}, "nominal_range": rng,
                      "L0_flagged_at_1.0mm": tilt}
    # Pr4: higher friction raises the catch at every Stage 2 point (L0 not testable in D12: E1-7 only)
    pts = ([("none", p_none)] if p_none is not None else []) + [("W3", C.NOMINAL)]
    res4 = {}
    for lay, p in pts:
        e, dlo = effect(idx, lay, p, "e"), effect(idx, lay, p, "d")
        if e["median_check"] is None or dlo["median_check"] is None or e["nominal_range"] is None:
            res4[lay] = None
        else:
            res4[lay] = bool(e["effect"] and e["delta"] > 0 and not (dlo["effect"] and dlo["delta"] > 0))
    t4 = [v for v in res4.values() if v is not None]
    out["Pr4"] = {"result": "not testable" if not t4 else _held(all(t4)), "by_point": {k: _held(v) for k, v in res4.items()},
                  "note": "L0 friction is covered by E1-7 only (Stage 0)"}
    # Pr5: misalignment 0 lowers the catch on some seeds but not all (per Stage 2 point)
    res5 = {}
    for lay, p in pts:
        e = effect(idx, lay, p, "f")
        pairs = [(e["ref"][s], e["check_values"][s]) for s in C.GRID_SEEDS
                 if e["ref"][s] is not None and e["check_values"][s] is not None]
        res5[lay] = None if len(pairs) < 3 else (1 <= sum(1 for r, c_ in pairs if c_ < r) <= 2)
    t5 = [v for v in res5.values() if v is not None]
    out["Pr5"] = {"result": "not testable" if not t5 else _held(all(t5)), "by_point": {k: _held(v) for k, v in res5.items()}}
    # Pr6: timestep 0.25 ms does not remove the catch (not absent on all 3 seeds), per Stage 2 point
    res6 = {}
    for lay, p in pts:
        recs = [r for r in point_records(idx, lay, C.setting(p["gap"], p["chamfer"], "a"), "R5", C.GRID_SEEDS).values()
                if usable(r)]
        res6[lay] = None if len(recs) < 3 else (not all(r["class"] == "absent" for r in recs))
    t6 = [v for v in res6.values() if v is not None]
    out["Pr6"] = {"result": "not testable" if not t6 else _held(all(t6)), "by_point": {k: _held(v) for k, v in res6.items()}}
    # Pr7: any catch-free setting with gap >= 0.10 mm flags (>= 0.8) or fails (> 1) the Stage 4 drift guard rail
    big = [C.setting_tag(st) for _, st in passing if st["gap"] >= 1e-4]
    # drift test on complete sequences only (an incomplete sequence is not a drift result)
    res7 = [s4[t]["summary"]["drift_fail"] or s4[t]["summary"]["drift_flag"] for t in big
            if t in s4 and s4[t]["summary"]["n_sequences_complete"] > 0]
    out["Pr7"] = {"result": "not testable" if not res7 else _held(all(res7)), "settings": big}
    return out


# ---- record-level self-checks ----------------------------------------------------------------------------------------
def s6_records(records: list[dict]) -> dict:
    """S6 on the records: for every override replay, setup fields and compiled M1Params fields not under test equal
    those of the nominal R1 replay on the same seed (any layout; the draws do not depend on the layout)."""
    reps = [r for r in records if r.get("job", {}).get("kind") == "replay" and usable(r)]
    nominal = {}
    for r in reps:
        j = r["job"]
        if C.is_nominal(j["setting"]) and j["rig"] == "R1":
            nominal.setdefault(j["seed"], r)
    out, n = [], 0
    for r in reps:
        j = r["job"]
        if C.is_nominal(j["setting"]) and j["rig"] == "R1":
            continue
        ref = nominal.get(j["seed"])
        if ref is None:
            out.append({"job_id": j["job_id"], "diffs": ["no nominal R1 replay on this seed yet"], "untestable": True})
            continue
        n += 1
        ut = C.fields_under_test(j["setting"], j["rig"])
        d = C.s6_diffs(ref["setup_used"], r["setup_used"], ut["setup"])
        d += C.s6_diffs(ref["setup_drawn"], r["setup_drawn"], set())
        d += C.params_diffs(ref["params"], r["params"], ut["m1"] | ({"grip_force"} if "grip_force" in ut["setup"] else set()),
                            ignore=())
        if d:
            out.append({"job_id": j["job_id"], "diffs": d})
    fails = [x for x in out if not x.get("untestable")]
    return {"n_compared": n, "problems": out, "pass": not fails}


def s7_records(records: list[dict]) -> dict:
    reps = {(r["job"]["seed"], r["job"]["move"], C.job_timestep(r["job"])): r for r in records
            if r.get("job", {}).get("kind") == "replay" and usable(r)}
    rows = []
    for (seed, mv, ts), r in reps.items():
        if ts != 0.00025:
            continue
        ref = reps.get((seed, mv, 0.0005))
        if ref is None:
            continue
        diffs = {k: abs(r["phases_s"][k] - ref["phases_s"][k]) for k in ref["phases_s"]}
        rows.append({"job_id": r["job_id"], "ref": ref["job_id"], "diff_s": diffs,
                     "pass": all(v <= 0.0005 + 1e-15 for v in diffs.values())})
    return {"rows": rows, "pass": all(x["pass"] for x in rows)}


def thresholds_frozen(records: list[dict]) -> dict:
    shas = {r.get("thresholds_sha256") for r in records if r.get("job", {}).get("kind") in ("replay", "stage4")}
    return {"shas": sorted(s for s in shas if s), "current": C.THRESHOLDS_SHA,
            "pass": shas <= {C.THRESHOLDS_SHA}}


# ---- report ---------------------------------------------------------------------------------------------------------
def report(records: list[dict]) -> dict:
    idx = index(records)
    crashes = [r["job_id"] for r in records if r.get("crash")]
    points = []
    for lay in C.STAGE_LAYOUTS:
        for st in grid_points():
            points.append(point_summary(idx, lay, st, "R5"))
        points.append(point_summary(idx, lay, C.NOMINAL, "R5", C.NOMINAL_SEEDS))
        points.append(point_summary(idx, lay, C.NOMINAL, "R1", C.NOMINAL_SEEDS))
    trends = [trend(idx, lay, "gap", c) for lay in C.STAGE_LAYOUTS for c in C.CHAMFERS] + \
             [trend(idx, lay, "chamfer", g) for lay in C.STAGE_LAYOUTS for g in C.GAPS]
    p_none, worst_table = worst_none_point(idx)
    s2pts = ([("none", p_none)] if p_none is not None else []) + [("W3", C.NOMINAL)]
    effects = [effect(idx, lay, p, chk) for lay, p in s2pts for chk in C.CHECKS]
    s2_points = [point_summary(idx, lay, C.setting(p["gap"], p["chamfer"], chk), "R5")
                 for lay, p in s2pts for chk in C.CHECKS]
    cand = candidates(idx, p_none)
    cf = [catch_free(idx, lay, st) for lay, st in cand["selected"]]
    passing = [(x["layout"], x["setting"]) for x in cf if x["catch_free"]]
    s4set = stage4_settings(idx, passing)
    s4 = stage4_verdicts(records)
    return {
        "status": "D12 is unscored, exploratory and diagnostic only; nothing here is a VALIDATED_RESULT",
        "n_records": len(records), "crashes": crashes,
        "noise_yardstick": {lay: nominal_range(idx, lay) for lay in C.STAGE_LAYOUTS},
        "points": points, "trends": trends, "worst_none_point": {"P_none": p_none, "table": worst_table},
        "stage2_effects": effects, "stage2_points": s2_points, "candidates": cand, "catch_free": cf,
        "stage4_settings": s4set, "stage4": s4, "jam_table": jam_table(idx),
        "jam_R1_completes_R5": r1_jam_r5_completes(idx),
        "predictions": predictions(idx, s4, p_none, passing),
        "S6_records": s6_records(records), "S7_records": s7_records(records),
        "thresholds_frozen": thresholds_frozen(records),
    }


def _fmt(x, nd=3):
    return "-" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def markdown(rep: dict) -> str:
    L = ["# D12 analysis report (generated by d12_analyze.py)", "",
         "Unscored, exploratory, diagnostic only. R5 is the diagnostic rig (turn_torque_limit 5 N·m), not the frozen "
         "rig; R5's final error, drift and settling are not read. Nothing here is a VALIDATED_RESULT.", "",
         f"Records: {rep['n_records']}; crashed: {len(rep['crashes'])}.", "",
         "## Noise yardstick (range of R5 catch impulse over 5 nominal seeds, N·m·s)", ""]
    for k, v in rep["noise_yardstick"].items():
        L.append(f"- {k}: {_fmt(v, 5)}")
    L += ["", "## Points", "", "| layout | point | rig | classes by seed | median impulse | median window peak | jams |"
          " signature share | flags (censored/pad/warn/validity) |", "|---|---|---|---|---|---|---|---|---|"]
    for p in rep["points"] + rep["stage2_points"]:
        cls = ", ".join(f"{s}:{v['class']}" for s, v in p["seeds"].items())
        fc = p["flag_counts"]
        L.append(f"| {p['layout']} | {p['tag']} | {p['rig']} | {cls} | {_fmt(p['median_catch_impulse_Nms'], 5)} | "
                 f"{_fmt(p['median_window_peak_Nm'])} | {p['n_jam']} | {_fmt(p['signature_share'], 2)} | "
                 f"{fc['censored_R5']}/{fc['pad_limited']}/{fc['above_warning']}/{fc['validity_flagged']} |")
    L += ["", "## Trends (section 11)", ""]
    for t in rep["trends"]:
        L.append(f"- {t['layout']} {t['factor']} at {t['fixed'] * 1e3:g} mm: {t['reading']} (medians "
                 f"{[_fmt(x, 5) for x in t['medians']]}, range {_fmt(t['nominal_range'], 5)}, "
                 f"monotone seeds {t['n_monotone_in_direction']}, excluded {t['excluded_jam_or_crash']})")
    L += ["", f"## Worst no-magnet point: {rep['worst_none_point']['P_none']}", "", "## Stage 2 effects", ""]
    for e in rep["stage2_effects"]:
        L.append(f"- {e['layout']} ({e['label']}): {e['reading']} (delta {_fmt(e['delta'], 5)}, same direction "
                 f"{e['n_same_direction']}/3)")
    L += ["", "## Candidates and catch-free", "", f"- selected: {rep['candidates']['selected']}",
          f"- beyond cap: {rep['candidates']['listed_beyond_cap']}"]
    for c in rep["catch_free"]:
        L.append(f"- {c['layout']} {C.setting_tag(c['setting'])}: catch-free {c['catch_free']}")
    L += ["", "## Stage 4", ""]
    for tag, o in rep["stage4"].items():
        L.append(f"- {tag}: {o['summary']['reading']} (max drift {_fmt(o['summary']['max_drift_deg'])} deg)")
    L += ["", "## Jams", ""]
    for g in rep["jam_table"]:
        L.append(f"- {g['layout']} {g['tag']} {g['rig']}: {g['k_jam']} of {g['n']}")
    for x in rep["jam_R1_completes_R5"]:
        L.append(f"- jam under R1, completes under R5: {x}")
    L += ["", "## Predictions", ""]
    for k, v in rep["predictions"].items():
        L.append(f"- {k}: {v['result']}")
    L += ["", f"S6 on records: {rep['S6_records']['pass']}; S7 on records: {rep['S7_records']['pass']}; "
          f"thresholds frozen: {rep['thresholds_frozen']['pass']}", ""]
    return "\n".join(L)


def main() -> None:
    recs = load_records()
    rep = report(recs)
    d = OUT / "analysis"
    d.mkdir(parents=True, exist_ok=True)
    (d / "report.json").write_text(json.dumps(rep, indent=1, default=C.jsonable))
    (d / "report.md").write_text(markdown(rep))
    print(markdown(rep))


if __name__ == "__main__":
    main()
