"""Verdict script for M7 (experiments/PHASE_1_M7_PREREGISTRATION.md, sections 4-5). Reads only; never re-runs a trial.

It is M5's verdict script (experiments/E5_scored_m5/analyze.py), loaded UNCHANGED on M7's runner (so its manifest,
ledger, record, seed, gap, wall, table and environment checks and its Option A rule apply as they did to M5), with
these M7 additions only:
  * the mechanism label "M7" (M5's script checks for "M5"; that one message is replaced by the M7 check);
  * per record: rounded edges with the registered radius (2.5 mm, or the E1-7 edge setting), and the registered NoSlip
    count in the compiled trial options (10, or the E1-7 NoSlip setting); for turn trials exactly one trial model
    built, with the NoSlip wrapper called once when NoSlip > 0;
  * every 60 s rest record (E1-1, the E1-7 rests, REST-X): length 60 s, and its pass flag re-derived from the record
    with D14's e11_pass and D11's slip-event detector (P-86 Q4) must equal the flag the worker stored;
  * the report's M7 title and restated disclosures, and the reported M7 sections (E1-7 rests, slips over E1-1 + REST-X
    with a 95 % Clopper-Pearson bound, margins, turner torque at 0.2 / 0.45 / 0.5 N m).
Verdict order (M5 section 5): INVALID > INCOMPLETE > NOT PASSED > PASS. PASS is the quantitative/categorical verdict
only: G1 also needs E1-8, the published abstraction and limitations, and the user's sign-off.

Usage (WSL, repo root):
    ~/.venvs/rubiknetic/bin/python experiments/E7_scored_m7/analyze.py            # writes RESULTS.md
    ~/.venvs/rubiknetic/bin/python experiments/E7_scored_m7/analyze.py --print
    ~/.venvs/rubiknetic/bin/python experiments/E7_scored_m7/analyze.py --smoke-dir DIR   # integrity only
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_E7_NAME = "e7_scored_m7_run"
_A_NAME = "e5_scored_m5_analyze_for_m7"
_R_NAME_IN_A = "e5_scored_m5_run"            # the name M5's analyze.py looks its runner up under


def _exec(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


E7 = _exec(_E7_NAME, HERE / "run.py")
R = E7.R


def _load_m5_analyze():
    if _A_NAME in sys.modules:
        return sys.modules[_A_NAME]
    missing = object()
    prev = sys.modules.get(_R_NAME_IN_A, missing)
    sys.modules[_R_NAME_IN_A] = R
    try:
        a = _exec(_A_NAME, REPO / "experiments" / "E5_scored_m5" / "analyze.py")
    finally:
        if prev is missing:
            del sys.modules[_R_NAME_IN_A]
        else:
            sys.modules[_R_NAME_IN_A] = prev
    assert a.R is R
    return a


A = _load_m5_analyze()
REST_EXPS = ("E1-1", "E1-7", "REST-X")
TORQUE_LEVELS = (0.2, 0.45, 0.5)


E11_KEYS = ("t0_solved", "final_solved", "rest_rotation_deg", "penetration_mm", "radial_offset_mm_t0")


def rest_samples(dt) -> int | None:
    """Samples d13_rest takes over REST_S at timestep dt: one every round(SAMPLE_S/dt) steps of round(REST_S/dt)
    (d13_run.py:190-193, 214). 2,400 at 0.5 and 0.25 ms; 2,425 at 0.75 ms (review 2, R1)."""
    if not dt:
        return None
    return len(range(0, int(round(E7.REST_S / dt)), int(round(E7.D13.SAMPLE_S / dt))))


def _overrides(rec: dict) -> dict:
    return (rec.get("spec") or {}).get("overrides") or {}


def m7_record_problems(key: tuple, rec: dict) -> list[str]:
    """M7's per-record checks (section 6.1); empty = fine."""
    tag, probs = "/".join(key), []
    if rec.get("harness_exception"):                     # M5 section 2 (U1 iii): a failing record, not a violation
        return [] if rec.get("pass") is False else [f"{tag}: harness-exception record is not failing"]
    ov = _overrides(rec)
    r_want, n_want = float(ov.get("edge_radius", E7.EDGE_R)), int(ov.get("noslip", E7.NOSLIP))
    p = rec.get("params") or {}
    if p.get("edge_profile") != "rounded" or not A._close(p.get("edge_radius"), r_want):
        probs.append(f"{tag}: edge {p.get('edge_profile')!r} {p.get('edge_radius')!r} != rounded {r_want}")
    m7 = rec.get("m7") or {}
    if not A._close(m7.get("edge_radius"), r_want) or m7.get("noslip") != n_want:
        probs.append(f"{tag}: m7 block {m7.get('edge_radius')!r} / {m7.get('noslip')!r} != {r_want} / {n_want}")
    if m7.get("kind") == "rest60":
        opts = rec.get("compiled_options") or {}
        n_got = opts.get("noslip_iterations")
        n_samples = len((rec.get("timeseries") or {}).get("t") or [])
        want_samples = rest_samples(opts.get("timestep"))
        aborted = bool(rec.get("aborted"))                 # an aborted rest stops sampling: a failing trial (M1)
        length_ok = (rec.get("rest_s") == E7.REST_S and want_samples is not None
                     and (n_samples <= want_samples if aborted else n_samples == want_samples))
        if not length_ok:
            probs.append(f"{tag}: rest length {rec.get('rest_s')} s, {n_samples} samples "
                         f"(registered {E7.REST_S} s, {want_samples} samples at timestep {opts.get('timestep')}"
                         f"{', aborted' if aborted else ''})")
        if rec.get("integrity_ok") and not aborted:
            lacking = [k for k in E11_KEYS if k not in rec]
            if lacking:                                   # review 2, O4: a malformed record is a violation, not a crash
                probs.append(f"{tag}: rest record lacks {lacking}")
                return probs
        ev = E7._plain(E7.D13A.events(rec))
        ok = E7.e11_pass(rec) and not ev
        if bool(rec.get("pass_m1_criteria")) != ok or rec.get("n_slip_events") != len(ev):
            probs.append(f"{tag}: stored rest verdict {rec.get('pass_m1_criteria')} / {rec.get('n_slip_events')} events "
                         f"differs from the re-derived {ok} / {len(ev)}")
    else:
        n_got = (m7.get("options") or {}).get("noslip_iterations")
        if m7.get("n_trials") != 1:
            probs.append(f"{tag}: {m7.get('n_trials')} trial models built (1 expected)")
        if m7.get("noslip_wrapper_calls") != (1 if n_want else 0):
            probs.append(f"{tag}: NoSlip wrapper called {m7.get('noslip_wrapper_calls')} times")
    if n_got != n_want:
        probs.append(f"{tag}: compiled noslip_iterations {n_got} != {n_want}")
    return probs


_m5_check_records = A.check_records


def check_records(st: dict, registered, expect_scored: bool, derived_not_run=None) -> None:
    """M5's checks, with the mechanism check made M7's, then M7's per-record checks."""
    _m5_check_records(st, registered, expect_scored, derived_not_run)
    m5_msgs = {f"{'/'.join(k)}: mechanism {r.get('mechanism')!r}" for k, r in st["records"].items()
               if r.get("mechanism") == E7.MECHANISM}
    st["violations"] = [x for x in st["violations"] if x not in m5_msgs]
    for k, r in st["records"].items():
        if r.get("mechanism") != E7.MECHANISM:
            st["violations"].append(f"{'/'.join(k)}: mechanism {r.get('mechanism')!r} (M7 expected)")
        st["violations"] += m7_record_problems(k, r)


A.check_records = check_records


# ---- report -------------------------------------------------------------------------------------------------------
M5_TITLE = "# G1 scored results — M5 (auto-generated by analyze.py)"
M5_RESTATED = [
    "* The 0.05 mm gap was chosen after unscored data at 0.2, 0.1 and 0.05 mm (P-24 to P-30).",
    "* Move strings other than the 20 E1-4 scrambles are the ones the rehearsals used; the E1-4 scrambles were "
    "drawn from the M5 seeds.",
    "* Whether a 0.05 mm clearance is realistic is an ASSUMPTION (one 2x2x2 patent; no 3x3 measurement).",
]
M7_RESTATED = [
    "* Post hoc (section 0 item 1): NoSlip 10 (P-73), rounded edges R 2.5 mm (P-79, P-80) and the arm L0 (P-83) were "
    "chosen on the rehearsal seeds 16000-16999; the 0.05 mm gap after unscored data (P-24 to P-30).",
    "* Move strings other than the 20 E1-4 scrambles are the ones the rehearsals used; the E1-4 scrambles were drawn "
    "from the M7 seeds. R4 rehearsed the same list on 19000-19655 (P-87).",
    "* Whether a 0.05 mm clearance is realistic is an ASSUMPTION; R3 shows drift fragility at 0.1 mm (P-85). Turning "
    "torque is uncalibrated (P-83).",
]


def clopper_pearson_upper(k: int, n: int, conf: float = 0.95) -> float:
    """Upper end of the two-sided 95 % Clopper-Pearson interval for k events in n trials."""
    from scipy.stats import beta
    return 1.0 if k >= n else float(beta.ppf(1 - (1 - conf) / 2, k + 1, n - k))


# Rehearsal maxima the margins are shown beside (section 0 item 8). FACT: D15 R1 + R2 L0 R25 on 16000-16655 and R4 on
# 19000-19655, from r4_analysis.json (margins_rehearsal_R1_R2, margins_fresh, turner_Nm_E12_E13_E14), except the
# rehearsal turner maximum 0.185, which is r2/r2_analysis.json arms/L0/turner_Nm_E12_E13_E14 (review 2, O3)
REHEARSAL_MAX = {"max_nontarget_drift_deg": (0.7281, 0.7810), "max_penetration_mm": (0.2932, 0.2916),
                 "max_abs_turn_error_deg": (0.3682, 0.3848), "max_rest_deg_0_10s": (0.0051, 0.0055),
                 "max_turner_Nm": (0.185, 0.193)}
LIMITS = {"max_nontarget_drift_deg": 1.0, "max_penetration_mm": 0.5, "max_abs_turn_error_deg": 2.0,
          "max_rest_deg_0_10s": 0.5, "max_turner_Nm": 1.0}
R3_E17 = REPO / "experiments/D15_rounded_edges/results/r3"
R3_TAG = {"noslip=0": "noslip_ref=0"}               # R3's tag for M7's NoSlip-0 reference arm


def _mx(xs):
    xs = [x for x in xs if x is not None]
    return max(xs) if xs else None


def margins(by: dict, rests: dict) -> dict:
    mv = [x for e in ("E1-2", "E1-3", "E1-4") for r in by.get(e, []) for x in r.get("per_move", [])]
    return {"max_nontarget_drift_deg": _mx(abs(x["nontarget_drift_deg"]) for x in mv
                                           if x.get("nontarget_drift_deg") is not None),
            "max_penetration_mm": _mx(x.get("penetration_mm") for x in mv),
            "max_abs_turn_error_deg": _mx(abs(x["turn_error_deg"]) for x in mv if x.get("turn_error_deg") is not None),
            "max_rest_deg_0_10s": _mx(r.get("rest_rotation_deg") for r in rests.values()),
            "max_turner_Nm": _mx(x.get("max_turner_torque_Nm") for x in mv)}


def _r3_pass(tid: str):
    """R3's pass flag for the same E1-7 sequence trial (None for rests, whose R3 records carry no flag, or if absent)."""
    import gzip
    import json
    tag, tail = tid.split("__")
    p = R3_E17 / "E1-7" / f"{R3_TAG.get(tag, tag)}__{tail}.json.gz"
    if tail == "rest60" or not p.exists():
        return None
    return bool(json.loads(gzip.decompress(p.read_bytes())).get("pass"))


def is_rest(k: tuple) -> bool:
    """A 60 s rest key, whether its record ran or is a harness-exception record (review 2, O2)."""
    return k[1] in ("E1-1", "REST-X") or (k[1] == "E1-7" and k[2].endswith("__rest60"))


def m7_sections(st: dict, vd: dict) -> list[str]:
    recs = st["records"]
    rest60 = {k: r for k, r in recs.items() if k[0] == "magnets" and is_rest(k)}
    rests = {k: r for k, r in rest60.items() if k[1] in ("E1-1", "REST-X")}
    e11 = {k: r for k, r in rest60.items() if k[1] == "E1-1"}
    n_slip = sum(1 for r in rests.values() if r.get("n_slip_events"))
    n_exc = sum(1 for r in rests.values() if r.get("harness_exception"))
    L = ["", "## Slip events over 60 s (E1-1 is a criterion; REST-X reported)", "",
         f"Rests with at least one D11 slip event: {n_slip} / {len(rests)} E1-1 + REST-X records "
         f"({n_exc} of them harness-exception records, counted without slips); two-sided 95 % Clopper-Pearson upper "
         f"bound on the per-rest rate {clopper_pearson_upper(n_slip, len(rests)) if rests else float('nan'):.3f}."]
    failed = [(k, r) for k, r in sorted(rest60.items()) if not r.get("pass")]
    if failed:
        L += ["", "Failed 60 s rests with their reasons (`e11_fail_reasons`, else `fail_reasons`; M4 lists E1-1 reasons "
              "as 'M1 criteria'):", ""]
        L += [f"* {'/'.join(k)}: {'; '.join(r.get('e11_fail_reasons') or r.get('fail_reasons') or [])}"
              for k, r in failed]
    warm = {k: (r.get("warmup_10s") or {}).get("rest_rotation_deg") for k, r in rest60.items()}
    L += ["", "## NoSlip-off E1-1 (reported; section 0 item 6)", "",
          "Each 60 s rest is preceded by M5's 10 s E1-1 with rounded edges and **no NoSlip**, recorded and not judged. "
          "M1's E1-1 limit is 0.5 deg.", "", "| rests | warm-ups | above 0.5 deg | largest (deg) |", "|---|---|---|---|"]
    for label, exp in (("E1-1", "E1-1"), ("REST-X", "REST-X"), ("E1-7 rests", "E1-7")):
        vals = [warm[k] for k in warm if k[1] == exp and warm[k] is not None]
        L.append(f"| {label} | {len(vals)} | {sum(v > 0.5 for v in vals)} | "
                 f"{'–' if not vals else f'{max(vals):.4f}'} |")
    m = margins(vd.get("by", {}), e11)
    L += ["", "## Margins beside the rehearsals (reported; section 0 item 8)", "",
          "| quantity | M7 scored | R1 + R2 rehearsal | R4 fresh seeds | limit |", "|---|---|---|---|---|"]
    for q, lim in LIMITS.items():
        v = m.get(q)
        a, b = REHEARSAL_MAX[q]
        L.append(f"| {q} | {'–' if v is None else f'{v:.4f}'} | {a} | {b} | {lim} |")
    by = vd.get("by", {})
    tq = [x.get("max_turner_torque_Nm") for e in ("E1-2", "E1-3", "E1-4") for r in by.get(e, [])
          for x in r.get("per_move", []) if x.get("max_turner_torque_Nm") is not None]
    L += ["", "* Moves with peak turner torque above " + ", ".join(f"{t} N m: {sum(x > t for x in tq)}"
                                                                  for t in TORQUE_LEVELS) + f" (of {len(tq)})."]
    L += ["", "## E1-7 against R3 (reported; R3's `noslip_ref=0` is M7's `noslip=0`)", "",
          "| trial | M7 | R3 |", "|---|---|---|"]
    for k, r in sorted(recs.items()):
        if k[0] == "magnets" and k[1] == "E1-7":
            r3 = _r3_pass(k[2])
            L.append(f"| {k[2]} | {'pass' if r.get('pass') else 'FAIL'} | {'–' if r3 is None else ('pass' if r3 else 'FAIL')} |")
    L += ["", "## E1-7 rests (reported)", "", "| setting | pass | 0-10 s rotation (deg) | slip events |", "|---|---|---|---|"]
    for k, r in sorted(recs.items()):
        if k[1] == "E1-7" and k[2].endswith("__rest60"):
            L.append(f"| {k[2][:-len('__rest60')]} | {r.get('pass')} | {r.get('rest_rotation_deg')} | "
                     f"{r.get('n_slip_events')} |")
    return L


def report(st: dict, vd: dict) -> str:
    text = A.report(st, vd)
    assert text.startswith(M5_TITLE)
    text = "# G1 scored results — M7 (auto-generated by analyze.py)" + text[len(M5_TITLE):]
    if st["manifest"] is not None:
        missing = [a for a in M5_RESTATED if a not in text]
        if missing:                                  # M5's template drifted: say so rather than print M5's wording
            text += "\n**Report template mismatch:** M5 restated line(s) not found: " + " | ".join(missing) + "\n"
    for a, b in zip(M5_RESTATED, M7_RESTATED):
        text = text.replace(a, b)
    if st["manifest"] is None:
        return text
    return text + "\n".join(m7_sections(st, vd)) + "\n"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--smoke-dir", type=Path)
    a = ap.parse_args(argv)
    if a.smoke_dir:
        dirs = {"magnets": a.smoke_dir / "results", "no_magnets": a.smoke_dir / "results_nomag"}
        st, vd = A.analyse(dirs, None, expect_scored=False)
        print(f"smoke integrity: {len(st['violations'])} violations, {len(st['missing'])} missing, "
              f"{len(st['records'])} records, {len(st['starts'])} starts")
        for x in st["violations"]:
            print("  ", x)
        sys.exit(1 if st["violations"] or st["missing"] else 0)
    env = R.environment()
    registered = R.build_m5_jobs("analyze", env, R.M4.nominal_validated_tilt())
    derived = R.v3_not_run(registered)
    st, vd = A.analyse({"magnets": R.OUT, "no_magnets": R.OUT_NOMAG}, registered, derived_not_run=derived)
    text = report(st, vd)
    if not a.print and st["manifest"] is not None:
        (HERE / "RESULTS.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
