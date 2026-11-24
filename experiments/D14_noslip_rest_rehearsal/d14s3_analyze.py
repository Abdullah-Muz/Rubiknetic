"""D14 Stage 3a/3b analysis (PROTOCOL_STAGE3.md sections 1-3): 3a checks, the 3b gate, and Part G's G.9 signals over
the full 204 trials per arm at noslip_iterations 10 (Stage 1 E1-1 + Stage 2 + Stage 3b). Writes report_stage3.md and
analysis_stage3.json. Exploratory and unscored.

Usage (WSL, repo root): ~/.venvs/rubiknetic/bin/python experiments/D14_noslip_rest_rehearsal/d14s3_analyze.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


RUN3 = _load("d14s3_run", HERE / "d14s3_run.py")
RUN2 = RUN3.RUN2
S2AN = _load("d14s2_analyze", HERE / "d14s2_analyze.py")
STAGE1 = _load("d14_run", HERE / "d14_run.py")
THRESH = {"rest_rotation_deg": 0.5, "penetration_mm": 0.5, "radial_offset_mm": 0.5}   # scored.THRESHOLDS values


def strip(rec: dict) -> dict:
    return {k: v for k, v in rec.items() if k not in ("d14s2", "d14s3")}


# ---- 3a ----------------------------------------------------------------------------------------------------------------
def stage3a(comp: list[dict]) -> dict:
    ER9 = RUN2.er9()
    frozen_cc = json.loads((RUN2.E9 / "results/hybrid_g/static/composite_checks.json").read_text())
    comp_rows = {}
    for c in comp:
        a = c["arm"]
        comp_rows[a] = {k: c[k] for k in ("V4", "V5", "V6")}
        comp_rows[a]["pass"] = all(c[k]["pass"] for k in ("V4", "V5", "V6"))
        if a in frozen_cc:
            comp_rows[a]["frozen"] = {"V4_max_rel_net_force": frozen_cc[a]["V4"]["max_rel_net_force"],
                                      "V5_drift_rel": frozen_cc[a]["V5"]["drift_rel"], "V6_pass": frozen_cc[a]["V6"]["pass"]}
    repro, conv = [], []
    for arm in RUN3.ARMS:
        exp, tid = RUN3.CHECK_TRIAL
        r10 = RUN2.load_rec(RUN2.record_path(RUN3.S3A_DIR / f"n{RUN3.NOSLIP}", arm, exp, tid))
        r20 = RUN2.load_rec(RUN2.record_path(RUN3.S3A_DIR / f"n{RUN3.NOSLIP_CONV}", arm, exp, tid))
        s2 = RUN2.load_rec(RUN2.record_path(RUN2.S2, arm, exp, tid))
        d = ER9.gs_diff(strip(s2), strip(r10))
        errs = RUN3.proof_errors(r10) + RUN3.proof_errors(r20)
        repro.append({"arm": arm, "trial": f"{exp}/{tid}", "n_diffs": len(d), "diffs": d[:10], "proof_errors": errs,
                      "pass": not d and not errs})
        mv10, mv20 = r10.get("per_move", []), r20.get("per_move", [])
        conv.append({"arm": arm, "pass_10": r10["pass"], "pass_20": r20["pass"],
                     "moves": [{k: (a.get(k), b.get(k)) for k in ("turn_error_deg", "nontarget_drift_deg",
                                                                  "max_turner_torque_Nm")} for a, b in zip(mv10, mv20)]})
    out = {"composite": comp_rows, "composite_pass": all(r["pass"] for r in comp_rows.values()),
           "reproduction": repro, "reproduction_pass": all(r["pass"] for r in repro), "convergence_reported": conv}
    out["pass"] = bool(out["composite_pass"] and out["reproduction_pass"])
    return out


# ---- 3b gate ---------------------------------------------------------------------------------------------------------
def gate3() -> dict:
    ER9 = RUN2.er9()
    out = {"trials": [], "pass": True}
    for p in sorted((RUN3.GATE3 / "L0").glob("*/*.json.gz")):
        rec = RUN2.load_rec(p)
        ref = RUN2.load_rec(RUN2.frozen_path("L0", rec["experiment"], rec["trial_id"]))
        d = ER9.gs_diff(ref, strip(rec))
        errs = RUN3.proof_errors(rec)
        ok = not d and not errs
        out["trials"].append({"trial": f"{rec['experiment']}/{rec['trial_id']}", "sub": rec["sub_experiment"],
                              "n_diffs": len(d), "diffs": d[:10],
                              "proof_errors": errs, "pass": ok})
        out["pass"] &= ok
    out["pass"] = bool(out["pass"] and sorted(t["sub"] for t in out["trials"]) == sorted(RUN3.EXPS3))
    return out


def arm_wall_ratios() -> dict:
    """Per arm: median over Stage 2 trials of (Stage 2 NoSlip wall / ER7 L0 frozen wall, same trial)."""
    out = {}
    for arm in RUN3.ARMS:
        r = []
        for p in sorted((RUN2.S2 / arm).glob("*/*.json.gz")):
            rec = RUN2.load_rec(p)
            f = RUN2.load_rec(RUN2.frozen_path("L0", rec["experiment"], rec["trial_id"]))
            r.append(rec["er7_wall_s"] / f["er7_wall_s"])
        out[arm] = float(np.median(r))
    return out


# ---- the 204 trials per arm --------------------------------------------------------------------------------------------
def e11_pass(rec: dict) -> bool:
    """Scored E1-1 criteria applied to a Stage 1 record (B1: no radial joint, so radial pop does not apply)."""
    return bool(rec.get("integrity_ok") and not rec.get("aborted") and rec.get("t0_solved") and rec.get("final_solved")
                and rec["rest_rotation_deg"] <= THRESH["rest_rotation_deg"]
                and rec["penetration_mm"] <= THRESH["penetration_mm"]
                and rec["radial_offset_mm_t0"] <= THRESH["radial_offset_mm"])


def assemble(arm: str) -> dict:
    """{(exp, tid): {"pass", "sub", "rec"}} for the 204 trials (E1-1 from Stage 1, the rest from Stages 2 and 3b)."""
    ER9 = RUN2.er9()
    dv = RUN2.d_val(arm)
    out = {}
    for s in STAGE1.SEEDS:
        p = STAGE1.result_path(arm, s)
        if p.exists():
            rec = STAGE1.D13.load_json(p)["record"]
            out[("E1-1", f"rest_s{s}")] = {"sub": "E1-1", "pass": e11_pass(rec), "rec": None}
    for root in (RUN2.S2, RUN3.S3):
        for p in sorted((root / arm).glob("*/*.json.gz")):
            rec = RUN2.load_rec(p)
            ok = bool(rec["pass"]) if arm == "L0" else bool(ER9.pass_g(rec, dv))
            out[(rec["experiment"], rec["trial_id"])] = {"sub": rec["sub_experiment"], "pass": ok, "rec": rec}
    return out


def arm_report(arm: str, stage1_signal: dict) -> dict:
    ER9 = RUN2.er9()
    A7 = _load("er7_analyze", REPO / "experiments/ER7_core_magnet_rehearsal/er7_analyze.py")
    dv = RUN2.d_val(arm)
    t = assemble(arm)
    rows = {e: {"n": sum(v["sub"] == e for v in t.values()), "expected": n,
                "passed": sum(v["sub"] == e and v["pass"] for v in t.values()),
                "failed": sorted(k[1] for k, v in t.items() if v["sub"] == e and not v["pass"])}
            for e, n in A7.EXPECTED.items()}
    complete = all(r["n"] == r["expected"] for r in rows.values())
    p_ok = [m.get("e16m_P_ok") for v in t.values() if v["rec"] is not None and v["sub"] in ("E1-2", "E1-3", "E1-4")
            for m in v["rec"].get("per_move", [])]
    e16m = {"moves": len(p_ok), "ok": sum(x is True for x in p_ok)}
    e16m["pass"] = bool(p_ok) and e16m["ok"] == e16m["moves"]
    option_a = bool(complete and all(r["passed"] == r["n"] for r in rows.values()) and e16m["pass"])
    recs = {k: v["rec"] for k, v in t.items() if v["rec"] is not None}
    oor_op = sorted(f"{e}/{i}" for (e, i), r in recs.items()
                    if arm != "L0" and r["sub_experiment"] in ER9.OPERATIONAL and ER9.oor_g(r, dv) is not False)
    abuse = sorted(f"{e}/{i}" for (e, i), r in recs.items()
                   if arm != "L0" and r["sub_experiment"] in ER9.ABUSE and ER9.oor_g(r, dv))
    seqs = [r for r in recs.values() if r["sub_experiment"] in ("E1-2", "E1-3", "E1-4")]
    tq = ER9.turner_stats(seqs)
    sig = {"1_rest_and_no_slips_stage1": bool(stage1_signal.get("signal_met")), "2_option_a_rule": option_a,
           "3_no_operational_trial_out_of_regime": (not oor_op) if arm != "L0" else None}
    sig["all_met"] = all(v for v in sig.values() if v is not None)
    clip = (tq or {}).get("at_clip", 0)
    reading = ("meets the rehearsal signals (not a candidate)" if sig["all_met"] and clip == 0 else
               "meets the rehearsal signals with moves at the clip: the user decides" if sig["all_met"] else
               "signal(s) missed: negative result kept and reported")
    flips = []
    if arm == "L0":
        for (e, i), r in recs.items():
            if r["sub_experiment"] in RUN3.EXPS3:
                f = RUN2.load_rec(RUN2.frozen_path("L0", e, i))
                if bool(f["pass"]) != bool(r["pass"]):
                    flips.append({"trial": f"{e}/{i}", "frozen": f["pass"], "noslip": r["pass"],
                                  "reasons": r.get("fail_reasons")})
    s3 = [r for r in recs.values() if r["sub_experiment"] in RUN3.EXPS3]
    drift = [abs(m["nontarget_drift_deg"]) for r in s3 for m in r.get("per_move", [])
             if m.get("nontarget_drift_deg") is not None]
    return {"arm": arm, "n": len(t), "rows": rows, "e16m": e16m, "complete": complete, "signals": sig,
            "reading": reading, "operational_out_of_regime": oor_op, "abuse_labelled_out_of_regime": abuse,
            "turner_Nm_E12_E13_E14": tq, "l0_flips_vs_frozen_3b": flips,
            "stage3b_trouble": sorted(f"{r['experiment']}/{r['trial_id']}" for r in s3 if RUN2.trouble(r)),
            "stage3b_max_nontarget_drift_deg": max(drift) if drift else None,
            "stage3b_max_solver_niter": max((r["d14s3"]["solver"]["max_solver_niter"] for r in s3), default=None),
            "stage3b_steps_at_iteration_limit": sum(r["d14s3"]["solver"]["steps_at_iteration_limit"] for r in s3)}


def main() -> None:
    s3a = json.loads(RUN3.S3A_FILE.read_text()) if RUN3.S3A_FILE.exists() else None
    g = gate3()
    stage1 = json.loads((HERE / "analysis.json").read_text())["signal"]
    arms = {a: arm_report(a, stage1.get(a, {})) for a in RUN3.ARMS}
    fmt = S2AN.fmt
    L = ["# D14 Stage 3a/3b report (generated by d14s3_analyze.py)", ""]
    if s3a:
        L += [f"## 3a: **{'PASS' if s3a['pass'] else 'FAIL'}**", "",
              "| Arm | V4 max rel force | V5 drift / exchanged | V6 | pass | frozen V5 drift |", "|---|---|---|---|---|---|"]
        for a, c in s3a["composite"].items():
            L.append(f"| {a} | {c['V4']['max_rel_net_force']:.1e} | {fmt(c['V5']['drift_rel'], 4)} | {c['V6']['pass']} | "
                     f"{c['pass']} | {fmt((c.get('frozen') or {}).get('V5_drift_rel'), 4)} |")
        L += ["", "Stage 2 reproduction (E1-2 U_s16100 at NoSlip 10): " +
              ", ".join(f"{r['arm']} {r['n_diffs']} diffs" for r in s3a["reproduction"]), "",
              "Convergence (NoSlip 10 vs 20, reported): " +
              "; ".join(f"{c['arm']}: pass {c['pass_10']}/{c['pass_20']}, moves {c['moves']}" for c in s3a["convergence_reported"])]
    L += ["", f"## 3b gate (L0 frozen, 6 trials): **{'PASS' if g['pass'] else 'FAIL'}**", ""]
    L += [f"- {x['trial']}: {x['n_diffs']} diffs" for x in g["trials"]]
    L += ["", "## G.9 signals over 204 trials per arm (NoSlip 10)", "",
          "| Arm | trials | 1 rest / slips (Stage 1) | 2 Option A (+ E1-6m ⟨P⟩) | 3 validity | all | reading |",
          "|---|---|---|---|---|---|---|"]
    for a, s in arms.items():
        sg = s["signals"]
        L.append(f"| {a} | {s['n']} / 204 | {sg['1_rest_and_no_slips_stage1']} | {sg['2_option_a_rule']} "
                 f"({s['e16m']['ok']}/{s['e16m']['moves']} moves ⟨P⟩) | "
                 f"{sg['3_no_operational_trial_out_of_regime'] if a != 'L0' else 'legacy (reported)'} | **{sg['all_met']}** | "
                 f"{s['reading']} |")
    L += ["", "## Rows (passed / n)", "", "| Arm | " + " | ".join(arms["L0"]["rows"]) + " |",
          "|---|" + "---|" * len(arms["L0"]["rows"])]
    for a, s in arms.items():
        L.append(f"| {a} | " + " | ".join(f"{r['passed']}/{r['n']}" + (f" (failed {r['failed']})" if r["failed"] else "")
                                         for r in s["rows"].values()) + " |")
    L += ["", "## Reported", "",
          "| Arm | turner median / p99 / max (E1-2–E1-4, N·m) | moves > 0.5 | at clip | abuse labelled OOR | 3b max non-target drift (°) | 3b max solver iter | L0 flips vs frozen |",
          "|---|---|---|---|---|---|---|---|"]
    for a, s in arms.items():
        t = s["turner_Nm_E12_E13_E14"] or {}
        L.append(f"| {a} | {fmt(t.get('median'))} / {fmt(t.get('p99'))} / {fmt(t.get('max'))} | {t.get('above_0.5')} | "
                 f"{t.get('at_clip')} | {len(s['abuse_labelled_out_of_regime'])} | {fmt(s['stage3b_max_nontarget_drift_deg'])} | "
                 f"{s['stage3b_max_solver_niter']} | {len(s['l0_flips_vs_frozen_3b']) if a == 'L0' else '–'} |")
    (HERE / "report_stage3.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    json.dump({"stage3a": s3a, "gate3": g, "arms": arms}, open(HERE / "analysis_stage3.json", "w"), indent=1, default=float)
    print("\n".join(L))


if __name__ == "__main__":
    main()
