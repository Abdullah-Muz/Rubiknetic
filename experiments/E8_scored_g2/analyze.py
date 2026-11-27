"""G2 verdict and report (experiments/PHASE_2_G2_PREREGISTRATION.md §4-§5; DRAFT, not in force).

Integrity first (as the G1 verdict scripts):
  INVALID     no manifest; a record that does not parse; a ledger line whose SHA-256 differs from its record; a record
              without a ledger line; a file the run procedure does not produce; a record whose key is not in the
              manifest;
  INCOMPLETE  a manifest trial has no record.
Otherwise:
  PASS        every scored trial (not reported-only) passes (zero tolerance, P-105 (4));
  NOT PASSED  at least one scored trial fails.
Report: counts per experiment, failure reasons, per-move maxima, G2-1 holds, G2-7 negative outcomes, the G2-6 screen
(reported only), and an exact (Clopper-Pearson) 95 % upper bound on the per-trial failure rate of the scored turns.
Usage: python analyze.py [RESULTS_DIR]   (default: experiments/E8_scored_g2/results)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run as R  # noqa: E402


def cp_upper(k: int, n: int, conf: float = 0.95) -> float:
    """Exact one-sided upper bound on a binomial proportion."""
    from scipy.stats import beta
    return 1.0 if k >= n else float(beta.ppf(conf, k + 1, n - k))


def integrity(out: Path) -> tuple[str | None, list[str], dict, dict]:
    probs: list[str] = []
    man_p = out / R.MANIFEST
    if not man_p.exists():
        return "INVALID", ["no manifest"], {}, {}
    manifest = json.loads(man_p.read_text())
    starts = R.read_lines(out / R.STARTS)
    ledger = {(x["exp"], x["tid"]): x["sha256"] for x in R.read_lines(out / R.LEDGER)}
    keys = {(t["exp"], t["tid"]) for t in manifest["trials"]}
    probs += [f"foreign file {f}" for f in R.foreign_files(out, starts, manifest)
              if not f.endswith(".json.tmp")]
    probs += [f"orphan temporary file {f}" for f in R.foreign_files(out, starts, manifest) if f.endswith(".json.tmp")]
    recs, missing = {}, []
    for k in sorted(keys):
        p = R.record_path(out, k)
        if not p.exists():
            missing.append(f"{k[0]}/{k[1]}")
            continue
        data = p.read_bytes()
        try:
            recs[k] = json.loads(data)
        except ValueError:
            probs.append(f"record {k} does not parse")
            continue
        if k not in ledger:
            probs.append(f"record {k} has no ledger line")
        elif ledger[k] != R._sha(data):
            probs.append(f"record {k}: ledger SHA-256 differs")
    probs += [f"ledger line {k} is not a manifest trial" for k in ledger if k not in keys]
    if probs:
        return "INVALID", probs, manifest, recs
    if missing:
        return "INCOMPLETE", [f"{len(missing)} trials without a record: {missing[:10]}"], manifest, recs
    return None, [], manifest, recs


def verdict(out: Path) -> dict:
    status, probs, manifest, recs = integrity(out)
    res = {"status": status, "problems": probs}
    if status is not None:
        return res
    ro = {(t["exp"], t["tid"]): t["reported_only"] for t in manifest["trials"]}
    scored = {k: r for k, r in recs.items() if not ro[k]}
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
                                              "core_rot_deg", "grasp_err_mm", "armB_track_err_mm")}
    holds = [r for k, r in scored.items() if k[0] == "G2-1"]
    res["holds"] = {"n": len(holds), "pass": sum(r["pass"] for r in holds),
                    "slip_max_mm": max((r.get("core_slip_mm", 0) for r in holds), default=None),
                    "rot_max_deg": max((r.get("core_rot_deg", 0) for r in holds), default=None)}
    res["negatives"] = {f"{k[1]}": {"pass": r["pass"], "outcome": r.get("negative_outcome")}
                        for k, r in scored.items() if k[0] == "G2-7"}
    res["screen"] = {k[1]: {"pass_as_turns": r["pass"], "fail_reasons": r["fail_reasons"]}
                     for k, r in recs.items() if ro[k]}
    return res


def report(res: dict) -> str:
    lines = [f"# G2 verdict: **{res['status']}**", ""]
    if res.get("problems"):
        lines += ["Problems:"] + [f"- {p}" for p in res["problems"]]
        return "\n".join(lines)
    lines += [f"- scored trials: {res['n_scored']} (reported only: {res['n_reported_only']})",
              f"- turn trials: {res['turn_trials']}, failures {res['turn_failures']}, exact 95 % upper bound on the "
              f"per-trial failure rate {res['turn_failure_rate_upper95']:.3f}", f"- moves: {res['moves']}",
              f"- G2-1 holds: {res['holds']['pass']}/{res['holds']['n']} pass; max slip "
              f"{res['holds']['slip_max_mm']} mm, max rotation {res['holds']['rot_max_deg']} deg", "",
              "| per-move maximum | value |", "|---|---|"]
    lines += [f"| {k} | {v:.3f} |" if v is not None else f"| {k} | - |" for k, v in res["per_move_max"].items()]
    lines += ["", "| G2-7 negative case | pass | outcome |", "|---|---|---|"]
    lines += [f"| {k} | {v['pass']} | {v['outcome']} |" for k, v in sorted(res["negatives"].items())]
    lines += ["", "| G2-6 screen (reported only) | turns pass | reasons |", "|---|---|---|"]
    lines += [f"| {k} | {v['pass_as_turns']} | {'; '.join(v['fail_reasons']) or '-'} |"
              for k, v in sorted(res["screen"].items())]
    if res.get("failed"):
        lines += ["", "Failed scored trials:"] + [f"- {k}: {'; '.join(v)}" for k, v in sorted(res["failed"].items())]
    return "\n".join(lines)


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else R.OUT
    res = verdict(out)
    text = report(res)
    print(text)
    (out.parent / "VERDICT.md").write_text(text + "\n", encoding="utf-8")
    (out.parent / "verdict.json").write_text(json.dumps(res, indent=1, default=list))


if __name__ == "__main__":
    main()
