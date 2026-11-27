"""G2 verdict and report (experiments/PHASE_2_G2_PREREGISTRATION.md revision 2 §4.4; DRAFT, not in force).

INVALID     no manifest; a record that does not parse; a ledger SHA-256 mismatch; a record without a ledger line; a
            ledger key with more than one line or without a record; any file or directory the run procedure does not
            produce, including an orphan temporary file anywhere; the manifest's trial list differs from the registered
            list (`build_jobs`, or `smoke_jobs` / `pilot_jobs` with --mode); for a scored run, the manifest's frozen
            paths differ from `run.FROZEN_PATHS`; an artifact SHA-256 differs from the manifest; a record's metadata
            differs from its manifest entry; a record's stored `pass` disagrees with the independent recomputation.
INCOMPLETE  a manifest trial has no record.
PASS        every scored trial passes (zero tolerance, P-105); NOT PASSED otherwise.

The recomputation below is deliberately independent of `trials.py`: it re-derives pass/fail from the raw fields with
its own copy of the limits (a unit test checks the two copies agree).
Usage: python analyze.py [RESULTS_DIR] [--mode scored|smoke|pilot]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run as R  # noqa: E402

LIMITS = {"turn_error_deg": 2.0, "drift_deg": 1.0, "pen_mm": 0.5, "move_slip_mm": 1.0, "move_rot_deg": 2.0,
          "rollback_deg": 1.0, "total_slip_mm": 2.0, "total_rot_deg": 2.0, "residual_end_deg": 4.0,
          "hold_slip_mm": 1.0, "hold_rot_deg": 1.0, "jam_slip_mm": 0.5, "jam_roll_deg": (20.0, 50.0),
          "drop_shift_mm": 1.0, "t0_offset_mm": 3.0}
ZERO = ("robot_cube_nonpad", "arm_arm", "robot_table", "robot_stand", "robot_block")


def cp_upper(k: int, n: int, conf: float = 0.95) -> float:
    from scipy.stats import beta
    return 1.0 if k >= n else float(beta.ppf(conf, k + 1, n - k))


# ---- independent recomputation --------------------------------------------------------------------------------------
def _n_moves(seq: str) -> int:
    return len(seq.split())


def _integrity(rec: dict) -> list[str]:
    out = [k for k in ("aborted", "harness_exception") if rec.get(k)]
    out += [k for k in ("audit_violations", "numerical_failures") if rec.get(k)]
    audit = (rec.get("trial") or {}).get("model_audit") or rec.get("model_audit")
    if not audit or any(audit.get(k) for k in ("actuators_on_cube", "equalities_on_cube", "tendons_on_cube",
                                               "gravcomp_on_cube")) or "tendons_on_cube" not in audit:
        out.append("model audit")
    return out


def _pre_t0(start: dict) -> list[str]:
    out = []
    if "stand_drop_shift_mm" not in start or start["stand_drop_shift_mm"] > LIMITS["drop_shift_mm"]:
        out.append("stand drop shift")
    if start.get("core_offset_from_nominal_mm", 99.0) > LIMITS["t0_offset_mm"]:
        out.append("t0 offset")
    return out


def _contacts(c: dict, cube_stand: bool) -> list[str]:
    out = [k for k in ZERO if c.get(k)]
    if cube_stand and c.get("cube_stand"):
        out.append("cube_stand")
    if c.get("pen_cubie", 0.0) > LIMITS["pen_mm"]:
        out.append("pen_cubie")
    return out


def _move(pm: dict) -> list[str]:
    bad = []
    if pm.get("observed_move") != pm.get("move"):
        bad.append("observed move")
    if abs(pm["turn_error_deg"]) > LIMITS["turn_error_deg"]:
        bad.append("turn error")
    if pm["nontarget_drift_deg"] > LIMITS["drift_deg"]:
        bad.append("drift")
    if pm["pen_cubie_mm"] > LIMITS["pen_mm"]:
        bad.append("penetration")
    tf, tm = pm.get("t_tip_force_s"), pm.get("t_layer_motion_rel_core_s")
    if not (tm is None or (tf is not None and tf <= tm)):
        bad.append("causality")
    for k in ("robot_cube_nonpad_max", "arm_arm_max", "robot_table_max", "robot_stand_max", "robot_block_max",
              "cube_stand_max"):
        if pm.get(k):
            bad.append(k)
    if not (pm["drive_impulse_Nms"] > 0.0 or pm.get("jam_stop") is not None):
        bad.append("drive")
    if pm["rollback_rot_deg"] > LIMITS["rollback_deg"] or not pm["rollback_state_unchanged"]:
        bad.append("roll-back")
    if pm["core_rot_deg"] > LIMITS["move_rot_deg"]:
        bad.append("core rotation")
    if pm["core_slip_mm"] > LIMITS["move_slip_mm"]:
        bad.append("core slip")
    if pm.get("jam_stop") is not None:
        bad.append("guard stop")
    return bad


def _growth(t0: list, end: list) -> float:
    return max(e - s for s, e in zip(t0, end))


def recompute_seq(rec: dict, moves: str) -> list[str]:
    out = _integrity(rec)
    if not rec.get("t0_solved"):
        out.append("t0")
    out += ["start " + x for x in _contacts(rec.get("start", {}).get("contacts", {}), False)]
    out += _pre_t0(rec.get("start", {}))
    out += ["approach " + x for x in _contacts(rec.get("approach", {}), True)]
    pms = rec.get("per_move", [])
    if len(pms) != _n_moves(moves):
        out.append("moves recorded")
    for i, pm in enumerate(pms):
        out += [f"move {i + 1} {x}" for x in _move(pm)]
    if not rec.get("final_matches_oracle"):
        out.append("final state")
    t = rec.get("trial")
    if not t:
        out.append("trial block")
    else:
        if t["core_slip_total_mm"] > LIMITS["total_slip_mm"]:
            out.append("total slip")
        if t["core_rot_total_deg"] > LIMITS["total_rot_deg"]:
            out.append("total rotation")
        if max(t["residual_end_deg"]) > LIMITS["residual_end_deg"]:
            out.append("end misalignment")
    return out


def recompute_hold(rec: dict) -> list[str]:
    out = _integrity(rec)
    if out:
        return out
    if not (rec.get("t0_solved") and rec.get("final_solved")):
        out.append("solved")
    if rec["core_slip_mm"] > LIMITS["hold_slip_mm"]:
        out.append("slip")
    if rec["core_rot_deg"] > LIMITS["hold_rot_deg"]:
        out.append("rotation")
    out += ["start " + x for x in _contacts(rec["start"].get("contacts", {}), False)]
    out += _pre_t0(rec["start"])
    out += ["hold " + x for x in _contacts(rec["contacts"], True)]
    if max(rec["residual_end_deg"]) > LIMITS["residual_end_deg"]:
        out.append("end misalignment")
    return out


def recompute_neg(rec: dict, case: str) -> bool:
    if _integrity(rec) or not rec.get("per_move"):
        return False
    pm = rec["per_move"][0]
    stop = pm.get("jam_stop")
    bad = set(_move(pm))
    if case == "two_layer":
        return stop is not None or bool(bad & {"observed move", "turn error", "drift"})
    if case == "open_midturn":
        return bool(bad & {"observed move", "turn error"})
    if case == "collision":
        app = rec.get("approach", {})
        return bool(pm.get("arm_arm_max") or pm.get("robot_cube_nonpad_max") or app.get("arm_arm")
                    or app.get("robot_cube_nonpad"))
    if case == "jam":
        if stop is None:
            return False
        rd = abs(stop.get("roll_done_deg", 0.0))
        lo, hi = LIMITS["jam_roll_deg"]
        return lo <= rd <= hi and pm["core_slip_mm"] <= LIMITS["jam_slip_mm"] and pm["pen_cubie_mm"] <= LIMITS["pen_mm"]
    if case == "offcentre":
        return True
    raise ValueError(case)


def recompute(rec: dict, t: dict) -> bool:
    kind, kw = t["kind"], t["kw"]
    if rec.get("harness_exception"):
        return False
    if kind in ("seq", "sens"):
        return not recompute_seq(rec, kw["moves"])
    if kind == "hold":
        return not recompute_hold(rec)
    if kind == "neg":
        return recompute_neg(rec, kw["case"])
    raise ValueError(kind)


# ---- integrity and verdict -------------------------------------------------------------------------------------------
def expected_jobs(mode: str) -> list[dict]:
    return {"scored": R.build_jobs, "smoke": R.smoke_jobs, "pilot": R.pilot_jobs, "pilot2": R.pilot2_jobs,
            "pilot3": R.pilot3_jobs}[mode]()


def starts_problems(out: Path, manifest: dict, starts: list[dict]) -> list[str]:
    """Review 2 S5: the start log must be consistent with the ledger and the folder.
    - every start is numbered 1..K in order;
    - every ledger line's start is in 1..K, and reconciled lines match the plans logged in STARTS.txt;
    - every record listed as present at a start still exists with the SHA-256 the ledger gives it (a record deleted
      together with its ledger line is caught)."""
    probs = []
    ks = [s.get("k") for s in starts]
    if ks != list(range(1, len(starts) + 1)):
        probs.append(f"STARTS.txt numbering {ks}")
    lines = R.read_lines(out / R.LEDGER)
    if lines and not starts:
        probs.append("ledger lines but no start logged")
    planned = {(s["k"], tuple(r["key"])) for s in starts for r in s.get("reconciled", [])}
    for x in lines:
        if not 1 <= x.get("start", 0) <= len(starts):
            probs.append(f"ledger line {x['exp']}/{x['tid']} has start {x.get('start')}")
        if x.get("reconciled") and (x["start"], (x["exp"], x["tid"])) not in planned:
            probs.append(f"reconciled ledger line {x['exp']}/{x['tid']} not in the logged plan")
    ledger = {(x["exp"], x["tid"]): x["sha256"] for x in lines}
    for s in starts:
        for k in s.get("present", []):
            k = tuple(k)
            p = R.record_path(out, k)
            if not p.exists():
                probs.append(f"record {k} present at start {s['k']} is missing")
            elif k in ledger and ledger[k] != R._sha(p.read_bytes()):
                probs.append(f"record {k} changed since start {s['k']}")
    return probs


def code_problems(manifest: dict) -> list[str]:
    """Review 2 S5: the verdict must run the frozen code: no frozen path differs between the manifest commit and HEAD,
    and none has uncommitted changes."""
    base = manifest["commit"].split("+")[0]
    probs = []
    try:
        diff = R._git("diff", "--name-only", base, "HEAD", "--", *manifest["frozen_paths"])
        dirty = R._git("status", "--porcelain", "--", *manifest["frozen_paths"])
    except Exception as e:  # noqa: BLE001
        return [f"cannot verify the frozen code: {e}"]
    if diff:
        probs.append(f"frozen paths differ between the manifest commit and HEAD: {diff}")
    if dirty:
        probs.append(f"frozen paths have uncommitted changes: {dirty}")
    return probs


def integrity(out: Path, mode: str = "scored", check_artifacts: bool = True, expected: list | None = None,
              recompute_fn=None, check_code: bool = True):
    """expected / recompute_fn are for unit tests only (synthetic runs); a real verdict uses the registered list and
    the independent recomputation."""
    recompute_fn = recompute_fn or recompute
    probs: list[str] = []
    man_p = out / R.MANIFEST
    if not man_p.exists():
        return "INVALID", ["no manifest"], {}, {}
    manifest = json.loads(man_p.read_text())
    starts = R.read_lines(out / R.STARTS)
    exp = [{"exp": j["exp"], "tid": j["tid"], "kind": j["kind"], "kw": j["kw"], "reported_only": j["reported_only"]}
           for j in (expected if expected is not None else expected_jobs(mode))]
    if R._norm(manifest.get("trials")) != R._norm(exp):
        probs.append(f"manifest trial list differs from the registered {mode} list")
    if mode == "scored" and manifest.get("frozen_paths") != R.FROZEN_PATHS:
        probs.append("manifest frozen paths differ from run.FROZEN_PATHS")
    if check_artifacts:
        now = R.artifacts()
        diff = sorted(k for k in set(now) | set(manifest.get("artifacts", {}))
                      if now.get(k) != manifest.get("artifacts", {}).get(k))
        if diff:
            probs.append(f"artifact SHA-256 differs from the manifest: {diff[:5]}")
    probs += [f"foreign or orphan file: {f}" for f in R.foreign_files(out, starts, manifest)
              if not R.is_inflight_tmp(out, f, manifest)]
    probs += [f"orphan temporary file at verdict time: {f.relative_to(out)}"     # review 1 item 4 a, review 2 item 4
              for f in sorted(out.rglob("*.json.tmp")) if f.parent.name != R.INTERRUPTED]
    probs += starts_problems(out, manifest, starts)
    if check_code and mode == "scored":
        probs += code_problems(manifest)
    probs += R.ledger_problems(out, manifest)
    ledger = {(x["exp"], x["tid"]): x["sha256"] for x in R.read_lines(out / R.LEDGER)}
    recs, missing = {}, []
    for t in manifest["trials"]:
        k = (t["exp"], t["tid"])
        p = R.record_path(out, k)
        if not p.exists():
            missing.append(f"{k[0]}/{k[1]}")
            continue
        data = p.read_bytes()
        try:
            rec = json.loads(data)
        except ValueError:
            probs.append(f"record {k} does not parse")
            continue
        if k not in ledger:
            probs.append(f"record {k} has no ledger line")
        elif ledger[k] != R._sha(data):
            probs.append(f"record {k}: ledger SHA-256 differs")
        meta_ok = (rec.get("experiment") == t["exp"] and rec.get("trial_id") == t["tid"]
                   and R._norm(rec.get("spec")) == R._norm(t["kw"]) and rec.get("source_commit") == manifest["commit"]
                   and rec.get("scored") == (mode == "scored") and rec.get("smoke") == (mode != "scored"))
        if not meta_ok:
            probs.append(f"record {k}: metadata differs from the manifest")
        rp = recompute_fn(rec, t)
        if bool(rec.get("pass")) != rp:
            probs.append(f"record {k}: stored pass {rec.get('pass')} != recomputed {rp}")
        recs[k] = rec
    if probs:
        return "INVALID", probs, manifest, recs
    if missing:
        return "INCOMPLETE", [f"{len(missing)} trials without a record: {missing[:10]}"], manifest, recs
    return None, [], manifest, recs


def verdict(out: Path, mode: str = "scored", check_artifacts: bool = True, **test_kw) -> dict:
    """test_kw: expected, recompute_fn, check_code (unit tests only)."""
    status, probs, manifest, recs = integrity(out, mode, check_artifacts, **test_kw)
    res = {"status": status, "problems": probs, "mode": mode}
    if status is not None:
        return res
    tinfo = {(t["exp"], t["tid"]): t for t in manifest["trials"]}
    scored = {k: r for k, r in recs.items() if not tinfo[k]["reported_only"]}
    failed = {f"{k[0]}/{k[1]}": r["fail_reasons"] for k, r in scored.items() if not r["pass"]}
    res["status"] = "PASS" if not failed else "NOT PASSED"
    res["failed"] = failed
    res["n_scored"], res["n_reported_only"] = len(scored), len(recs) - len(scored)
    turns = [r for k, r in scored.items() if k[0] in ("G2-2", "G2-3", "G2-4")]
    k_fail = sum(not r["pass"] for r in turns)
    res["turn_trials"], res["turn_failures"] = len(turns), k_fail
    res["turn_failure_rate_upper95"] = cp_upper(k_fail, len(turns)) if turns else None
    pms = [pm for r in turns for pm in r.get("per_move", [])]

    def mx(key):
        v = [abs(pm[key]) for pm in pms if pm.get(key) is not None]
        return max(v) if v else None
    res["moves"] = len(pms)
    res["per_move_max"] = {k: mx(k) for k in ("turn_error_deg", "nontarget_drift_deg", "pen_cubie_mm", "pen_pad_mm",
                                              "ft_tau_z_max_Nm", "max_tool_torque_on_layer_Nm", "core_slip_mm",
                                              "core_rot_deg", "rollback_rot_deg", "grasp_err_mm", "armB_track_err_mm")}
    tr = [r["trial"] for r in turns if r.get("trial")]
    res["trial_max"] = {"core_slip_total_mm": max((t["core_slip_total_mm"] for t in tr), default=None),
                        "core_rot_total_deg": max((t["core_rot_total_deg"] for t in tr), default=None),
                        "residual_end_deg": max((max(t["residual_end_deg"]) for t in tr), default=None),
                        "residual_growth_deg (reported)": max((_growth(t["residual_t0_deg"], t["residual_end_deg"])
                                                               for t in tr), default=None)}
    holds = [r for k, r in scored.items() if k[0] == "G2-1"]
    res["holds"] = {"n": len(holds), "pass": sum(r["pass"] for r in holds),
                    "slip_max_mm": max((r.get("core_slip_mm", 0) for r in holds), default=None),
                    "rot_max_deg": max((r.get("core_rot_deg", 0) for r in holds), default=None)}
    res["negatives"] = {k[1]: {"pass": r["pass"], "outcome": r.get("negative_outcome"),
                               "reported_only": tinfo[k]["reported_only"]}
                        for k, r in recs.items() if tinfo[k]["kind"] == "neg"}
    res["screen"] = {k[1]: {"pass_as_turns": r["pass"], "fail_reasons": r["fail_reasons"]}
                     for k, r in recs.items() if k[0] == "G2-6"}
    rtf = sorted(r["sim_time_s"] / r["wall_s"] for r in recs.values() if r.get("sim_time_s") and r.get("wall_s"))
    res["throughput"] = {"n": len(rtf), "rtf_median": rtf[len(rtf) // 2] if rtf else None,
                         "rtf_min": rtf[0] if rtf else None, "rtf_max": rtf[-1] if rtf else None,
                         "note": "simulated s per wall s per trial process (holds included); other trials in parallel"}
    return res


def report(res: dict) -> str:
    lines = [f"# G2 verdict ({res['mode']}): **{res['status']}**", ""]
    if res.get("problems"):
        lines += ["Problems:"] + [f"- {p}" for p in res["problems"]]
        return "\n".join(lines)
    ub = res["turn_failure_rate_upper95"]
    lines += [f"- scored trials: {res['n_scored']} (reported only: {res['n_reported_only']})",
              f"- turn trials: {res['turn_trials']}, failures {res['turn_failures']}, exact 95 % upper bound on the "
              f"per-trial failure rate {'-' if ub is None else f'{ub:.3f}'}", f"- moves: {res['moves']}",
              f"- G2-1 holds: {res['holds']['pass']}/{res['holds']['n']} pass; max slip {res['holds']['slip_max_mm']}"
              f" mm, max rotation {res['holds']['rot_max_deg']} deg",
              f"- G2-8 throughput (reported): real-time factor median {res['throughput']['rtf_median']} "
              f"({res['throughput']['n']} trials)", "", "| per-move maximum | value |", "|---|---|"]
    lines += [f"| {k} | {'-' if v is None else f'{v:.3f}'} |" for k, v in res["per_move_max"].items()]
    lines += [f"| {k} (trial) | {'-' if v is None else f'{v:.3f}'} |" for k, v in res["trial_max"].items()]
    lines += ["", "| negative case | pass | outcome | reported only |", "|---|---|---|---|"]
    lines += [f"| {k} | {v['pass']} | {v['outcome']} | {v['reported_only']} |" for k, v in sorted(res["negatives"].items())]
    lines += ["", "| G2-6 screen (reported only) | turns pass | reasons |", "|---|---|---|"]
    lines += [f"| {k} | {v['pass_as_turns']} | {'; '.join(v['fail_reasons']) or '-'} |"
              for k, v in sorted(res["screen"].items())]
    if res.get("failed"):
        lines += ["", "Failed scored trials:"] + [f"- {k}: {'; '.join(v)}" for k, v in sorted(res["failed"].items())]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="?", type=Path, default=R.OUT)
    ap.add_argument("--mode", choices=("scored", "smoke", "pilot", "pilot2", "pilot3"), default="scored")
    a = ap.parse_args()
    res = verdict(a.results, a.mode)
    text = report(res)
    print(text)
    (a.results.parent / "VERDICT.md").write_text(text + "\n", encoding="utf-8")
    (a.results.parent / "verdict.json").write_text(json.dumps(res, indent=1, default=list))


if __name__ == "__main__":
    main()
