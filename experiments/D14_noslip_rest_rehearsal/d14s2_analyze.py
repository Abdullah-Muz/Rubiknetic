"""D14 Stage 2 analysis (PROTOCOL_STAGE2.md sections 2-5). Reads results/stage2_decay.json, results/stage2_gate/,
results/stage2/, D14 Stage 1's analysis.json and the committed frozen-setting records; writes report_stage2.md and
analysis_stage2.json. Exploratory and unscored.

Usage (WSL, repo root): ~/.venvs/rubiknetic/bin/python experiments/D14_noslip_rest_rehearsal/d14s2_analyze.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


RUN = _load("d14s2_run", HERE / "d14s2_run.py")
STALL_WINDOW_SAMPLES = 6            # 30 ms at the 5 ms series spacing
STALL_ADVANCE_DEG = 0.05
MOVE_START_DEG, MOVE_END_DEG = 1.0, 85.0


def frozen(arm: str, exp: str, tid: str) -> dict:
    return RUN.load_rec(RUN.frozen_path(arm, exp, tid))


def records(root: Path, arm: str) -> dict:
    out = {}
    for p in sorted((root / arm).glob("*/*.json.gz")):
        r = RUN.load_rec(p)
        out[(r["experiment"], r["trial_id"])] = r
    return out


def strip(rec: dict) -> dict:
    return {k: v for k, v in rec.items() if k != "d14s2"}


# ---- gate ----------------------------------------------------------------------------------------------------------
def gate() -> dict:
    ER9 = RUN.er9()
    out = {"trials": [], "pass": True, "wall_ratio_by_arm": {}}
    ratios: dict = {}
    for arm in RUN.ARMS:
        recs = records(RUN.GATE_DIR, arm)
        if len(recs) != len(RUN.EXPS):
            out["pass"] = False
        for (exp, tid), rec in sorted(recs.items()):
            ref = frozen(arm, exp, tid)
            d = ER9.gs_diff(ref, strip(rec))
            errs = RUN.proof_errors(rec)
            ok = not d and not errs
            out["trials"].append({"arm": arm, "exp": exp, "tid": tid, "n_diffs": len(d), "diffs": d[:10],
                                  "proof_errors": errs, "pass": ok})
            out["pass"] &= ok
            ratios.setdefault(arm, []).append(rec["er7_wall_s"] / ref["er7_wall_s"])
    out["wall_ratio_by_arm"] = {a: float(np.mean(v)) for a, v in ratios.items()}
    out["pass"] = bool(out["pass"] and len(out["trials"]) == len(RUN.ARMS) * len(RUN.EXPS))
    return out


# ---- per-trial helpers -------------------------------------------------------------------------------------------
def arm_pass(arm: str, rec: dict, d_val: float) -> bool:
    if arm == "L0":
        return bool(rec["pass"])
    return bool(RUN.er9().pass_g(rec, d_val))


def arm_oor(arm: str, rec: dict, d_val: float):
    if arm == "L0":
        return None
    return RUN.er9().oor_g(rec, d_val)


def peak_torque(rec: dict) -> float | None:
    tq = [m.get("max_turner_torque_Nm") for m in rec.get("per_move", []) if m.get("max_turner_torque_Nm") is not None]
    return max(tq) if tq else None


def stall_descriptors(rec: dict) -> dict | None:
    s = (rec.get("d14s2") or {}).get("series")
    if not s or not s["t"]:
        return None
    face = rec["trial_id"][0]
    k = RUN.FACES.index(face)
    tt = np.abs(np.array(s["turner_deg"])[:, k])
    ll = np.array(s["layer_deg"])[:, k]
    la = np.abs(ll)
    t = np.array(s["t"])
    start = int(np.argmax(tt > MOVE_START_DEG)) if (tt > MOVE_START_DEG).any() else None
    if start is None:
        return {"face": face, "move_found": False}
    reach = np.nonzero(la[start:] >= MOVE_END_DEG)[0]
    end = start + int(reach[0]) if reach.size else len(t) - 1
    w = STALL_WINDOW_SAMPLES
    stalled = [abs(ll[i + w] - ll[i]) < STALL_ADVANCE_DEG for i in range(start, max(start, end - w))]
    episodes, cur = [], 0
    for x in stalled:
        if x:
            cur += 1
        elif cur:
            episodes.append(cur)
            cur = 0
    if cur:
        episodes.append(cur)
    dt = float(np.median(np.diff(t))) if len(t) > 1 else 0.0
    slip = np.abs(np.array(s["turner_deg"])[start:end + 1, k] - ll[start:end + 1])
    return {"face": face, "move_found": True, "reached_85": bool(reach.size), "n_stall_episodes": len(episodes),
            "longest_stall_s": (max(episodes) - 1) * dt + w * dt if episodes else 0.0,
            "max_pad_slip_deg": float(slip.max()) if slip.size else None,
            "min_pad_contacts": int(min(s["pad_contacts"][start:end + 1])) if s["pad_contacts"] else None}


def sign_counts(pairs: list) -> dict:
    d = [b - a for a, b in pairs if a is not None and b is not None]
    return {"n": len(d), "noslip_higher": int(sum(x > 0 for x in d)), "noslip_lower": int(sum(x < 0 for x in d)),
            "equal": int(sum(x == 0 for x in d))}


# ---- per arm -----------------------------------------------------------------------------------------------------------
def arm_summary(arm: str, stage1: dict) -> dict:
    ER9 = RUN.er9()
    dv = RUN.d_val(arm)
    recs = records(RUN.S2, arm)
    by = {e: [r for (x, _), r in recs.items() if x == e] for e in RUN.EXPS}
    complete = {e: len(v) for e, v in by.items()} == RUN.COUNTS
    snap_scored = [r for r in by["E1-5s"] if r.get("snap_is_criterion")]
    failed = sorted(f"{e}/{t}" for (e, t), r in recs.items() if not arm_pass(arm, r, dv))
    oor = sorted(f"{e}/{t}" for (e, t), r in recs.items() if arm != "L0" and arm_oor(arm, r, dv) is not False)
    trouble = sorted(f"{e}/{t}" for (e, t), r in recs.items() if RUN.trouble(r))
    s1 = (stage1.get("signal") or {}).get(arm, {}).get("signal_met")
    sig = {"complete": complete,
           "1_snap_scored_all_pass": complete and all(arm_pass(arm, r, dv) for r in snap_scored),
           "2_rest_from_stage1": bool(s1),
           "3_e12_e15_all_pass": complete and all(arm_pass(arm, r, dv) for e in ("E1-2", "E1-5") for r in by[e]),
           "4_no_trial_out_of_regime": complete and (not oor if arm != "L0" else None)}
    met = [v for k, v in sig.items() if v is not None]
    sig["all_met"] = bool(all(met))
    flips, torque_pairs, snap_pairs, wall = [], [], [], []
    for (e, t), r in recs.items():
        f = frozen(arm, e, t)
        pf, pn = arm_pass(arm, f, dv), arm_pass(arm, r, dv)
        if pf != pn:
            flips.append({"trial": f"{e}/{t}", "frozen": pf, "noslip": pn, "noslip_reasons": r.get("fail_reasons")})
        if e == "E1-2":
            torque_pairs.append((peak_torque(f), peak_torque(r)))
        if e == "E1-5s":
            snap_pairs.append((abs(f["U_err_after_1s_deg"]) if f.get("U_err_after_1s_deg") is not None else None,
                               abs(r["U_err_after_1s_deg"]) if r.get("U_err_after_1s_deg") is not None else None))
        wall.append(r["er7_wall_s"] / f["er7_wall_s"])
    fz = [frozen(arm, "E1-2", t) for (e, t) in recs if e == "E1-2"]
    stalls = {t: stall_descriptors(r) for (e, t), r in recs.items() if e == "E1-2"}
    st_ok = [x for x in stalls.values() if x and x.get("move_found")]
    outcomes = {}
    for r in by["E1-5"]:
        outcomes[r.get("outcome")] = outcomes.get(r.get("outcome"), 0) + 1
    fo = {}
    for (e, t) in recs:
        if e == "E1-5":
            o = frozen(arm, e, t).get("outcome")
            fo[o] = fo.get(o, 0) + 1
    snaps = [abs(r["U_err_after_1s_deg"]) for r in snap_scored if r.get("U_err_after_1s_deg") is not None]
    return {"arm": arm, "d_val": dv if arm != "L0" else None, "n": len(recs), "signals": sig, "failed": failed,
            "out_of_regime": oor, "trouble": trouble, "flipped_vs_frozen": flips,
            "turner_noslip": ER9.turner_stats(by["E1-2"]), "turner_frozen": ER9.turner_stats(fz),
            "paired_peak_torque": sign_counts(torque_pairs), "paired_snap_abs_err_1s": sign_counts(snap_pairs),
            "snap_scored_max_abs_err_deg": max(snaps) if snaps else None,
            "e15_outcomes_noslip": outcomes, "e15_outcomes_frozen": fo,
            "wall_ratio_median": float(np.median(wall)) if wall else None,
            "max_solver_niter": max((r["d14s2"]["solver"]["max_solver_niter"] for r in recs.values()), default=None),
            "steps_at_iteration_limit": sum(r["d14s2"]["solver"]["steps_at_iteration_limit"] for r in recs.values()),
            "stall": {"n_trials": len(st_ok), "trials_with_stall": sum(x["n_stall_episodes"] > 0 for x in st_ok),
                      "longest_stall_s": max((x["longest_stall_s"] for x in st_ok), default=None),
                      "max_pad_slip_deg": max((x["max_pad_slip_deg"] for x in st_ok if x["max_pad_slip_deg"] is not None),
                                              default=None),
                      "all_reached_85": all(x["reached_85"] for x in st_ok), "per_trial": stalls}}


def fmt(x, nd=3):
    return "–" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def main() -> None:
    dec = json.loads(RUN.DECAY_FILE.read_text()) if RUN.DECAY_FILE.exists() else None
    g = gate()
    stage1 = json.loads((HERE / "analysis.json").read_text())
    arms = {a: arm_summary(a, stage1) for a in RUN.ARMS}
    L = ["# D14 Stage 2 report (generated by d14s2_analyze.py)", ""]
    if dec:
        L += ["## Free-decay check (PROTOCOL_STAGE2 section 3)", "", f"Overall: **{'PASS' if dec['pass'] else 'FAIL'}**", "",
              "| Case | decay time, NoSlip 0 (s) | NoSlip 10 (s) | time ratio | angle ratio | pass |", "|---|---|---|---|---|---|"]
        for k, c in dec["cases"].items():
            L.append(f"| {k} | {fmt(c['noslip0']['decay_time_s'], 4)} | {fmt(c['noslip10']['decay_time_s'], 4)} | "
                     f"{fmt(c['time_ratio'])} | {fmt(c['angle_ratio'])} | {c['pass']} |")
    L += ["", f"## Gate (frozen setting, with Stage 2 logging): **{'PASS' if g['pass'] else 'FAIL'}**", "",
          "| Arm | Trial | differences | proof errors | wall ratio |", "|---|---|---|---|---|"]
    for x in g["trials"]:
        L.append(f"| {x['arm']} | {x['exp']}/{x['tid']} | {x['n_diffs']} | {x['proof_errors'] or 'none'} | |")
    L += ["", "## Signals at NoSlip (G.8; signal 2 from Stage 1)", "",
          "| Arm | trials | 1 snap-back | 2 rest (Stage 1) | 3 E1-2 and E1-5 | 4 validity | all | failed trials | trouble |",
          "|---|---|---|---|---|---|---|---|---|"]
    for a, s in arms.items():
        sg = s["signals"]
        L.append(f"| {a} | {s['n']} / 86 | {sg['1_snap_scored_all_pass']} | {sg['2_rest_from_stage1']} | "
                 f"{sg['3_e12_e15_all_pass']} | {sg['4_no_trial_out_of_regime'] if a != 'L0' else 'legacy (reported)'} | "
                 f"**{sg['all_met']}** | {s['failed'] or 'none'} | {s['trouble'] or 'none'} |")
    L += ["", "## Reported items (frozen → NoSlip)", "",
          "| Arm | E1-2 turner median | p99 | max | > 0.45 N·m | > 0.5 N·m | at clip | peak torque higher / lower (paired) | "
          "snap max \\|err\\| scored | snap \\|err\\| higher / lower | flipped pass flags | wall ratio | max solver iter |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a, s in arms.items():
        f, n = s["turner_frozen"] or {}, s["turner_noslip"] or {}
        pt, ps = s["paired_peak_torque"], s["paired_snap_abs_err_1s"]
        L.append(f"| {a} | {fmt(f.get('median'))} → {fmt(n.get('median'))} | {fmt(f.get('p99'))} → {fmt(n.get('p99'))} | "
                 f"{fmt(f.get('max'))} → {fmt(n.get('max'))} | {f.get('above_0.45')} → {n.get('above_0.45')} | "
                 f"{f.get('above_0.5')} → {n.get('above_0.5')} | {f.get('at_clip')} → {n.get('at_clip')} | "
                 f"{pt['noslip_higher']} / {pt['noslip_lower']} | {fmt(s['snap_scored_max_abs_err_deg'])} | "
                 f"{ps['noslip_higher']} / {ps['noslip_lower']} | {len(s['flipped_vs_frozen'])} | "
                 f"{fmt(s['wall_ratio_median'], 2)} | {s['max_solver_niter']} |")
    L += ["", "E1-5 outcomes (frozen → NoSlip): " + "; ".join(f"{a}: {s['e15_outcomes_frozen']} → {s['e15_outcomes_noslip']}"
                                                         for a, s in arms.items()), "",
          "## E1-2 stall descriptors (NoSlip; reported only)", "",
          "| Arm | trials | with a stall window | longest (s) | max pad slip (°) | all reached 85° |", "|---|---|---|---|---|---|"]
    for a, s in arms.items():
        x = s["stall"]
        L.append(f"| {a} | {x['n_trials']} | {x['trials_with_stall']} | {fmt(x['longest_stall_s'])} | "
                 f"{fmt(x['max_pad_slip_deg'])} | {x['all_reached_85']} |")
    (HERE / "report_stage2.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    json.dump({"decay": dec, "gate": g, "arms": arms}, open(HERE / "analysis_stage2.json", "w"), indent=1, default=float)
    print("\n".join(L))


if __name__ == "__main__":
    main()
