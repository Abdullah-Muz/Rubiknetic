# M7 pre-registration — independent review 2 (2026-11-25)

One reviewer subagent (P-86 Q8). Revision 2 at `e807def`; code last changed at `d5ba4cd`. Reproduced below as
returned. The main session's verification and response are in revision 3 (§9) and DECISION_LOG.

---

**Verdict: ACCEPTABLE WITH CHANGES**

**Reviewed:**
- `experiments/PHASE_1_M7_PREREGISTRATION.md`, revision 2, at `e807def`;
- `experiments/E7_scored_m7/run.py`, `analyze.py` and `tests/test_scored_m7.py` (code unchanged between `d5ba4cd`
  and `e807def`);
- the evidence: `results_selfcheck/selfcheck.json`, `smoke_rev2_2026-11-25/` and its log.

Comparison base `090fc8f`. Read-only: no repository file changed, `git status` clean, no simulation run.

**Summary:** every review-1 required item is resolved. Revision 2 adds one new defect that would certainly make the
scored run INVALID (R1).

## Review-1 required items
| Item | Status | Evidence |
|---|---|---|
| A-R1 / B-R3: harness exception made the run INVALID | **RESOLVED** | The exemption is first (`analyze.py:79-80`) and requires `pass is False`. M5's integrity checks and M7's mechanism check still run (`analyze.py:117-124`). Only `E5 run.py:287-301` writes `harness_exception`, always with `pass` False, so the exemption cannot hide a misconfigured passing record. Tests cover seq, rest60, `noslip=0`, REST-X, an E1-7 rest and the `pass True` case, plus full-verdict PASS and NOT PASSED |
| A-R2: NoSlip dependence undisclosed | **RESOLVED** | Disclosed in §0 item 6, §1, §4.2, §4.3 and §6.1, and reported by `analyze.py:204-214`. Warm-up numbers re-derived and matching: R2 3/20 (0.7093, 0.5490, 0.6938), R4 1/20 (0.5768); judged maxima 0.005133° and 0.005526° |
| A-R3: seed FACT scope | **RESOLVED** | Limited to §6.4's scope. Rescan: 5,834 files, 0 matches |
| A-R4 / B-R2: start-log load claim | **RESOLVED** | — |
| A-R5 / B-R1: "about 5 %" | **RESOLVED** | "Two-sided 95 %", "about 6 % (0.0596)" |
| B-R4: CAD gap | **RESOLVED** | All three line references correct; `UNVERIFIED` |
| B-R5: speedcube-edge claim | **RESOLVED** | — |
| B-R6: rest60 path untested | **RESOLVED** | `test_rest60_path`, `test_rest60_slip_fails`, and the test over all 501 jobs |
| B-R7: no full-verdict tests | **RESOLVED**, with gaps (O5) | The stand-in rest always has 2,400 samples, which hides R1 |
| B-R8: evidence provenance | **RESOLVED** for the self-check (head `d5ba4cd`, clean, 16/16, SHA-256s match); **PARTLY** for the smoke (only `d5ba4cd+smoke`, no SHA-256s or clean flag committed; O1). R1 changes the code, so both must be re-run anyway | — |

## REQUIRED changes
### R1. The new measured rest-length check makes the scored run INVALID with certainty
**Where:** `analyze.py:91-95` and §5 l.272 ("by its 2,400 samples").

**The timestep case.** `want_samples = round(REST_S / D13.SAMPLE_S)` is 2,400 for every rest. But `d13_rest`
samples every `chunk = round(SAMPLE_S/dt)` steps over `steps = round(60/dt)` steps (`d13_run.py:190-193, 211-245`).
- At dt = 0.75 ms that is ceil(80000/33) = **2,425** samples.
- M7's list contains this setting: the E1-7 rest `timestep=0.00075__rest60` (`run.py:265`).
- Verified on R3's committed record, which M7's rest path reproduces:
  - `results/r3/rests/timestep=0.00075__rest60.json.gz` has 2,425 samples; the other 14 R3 rests have 2,400.
  - All 15 R3 rests, dressed as M7 records and passed through `m7_record_problems`: 14 give `[]`, and
    `timestep=0.00075` gives a violation.
- The verdict would be INVALID, which is final.

**The abort case.** `d13_rest` catches `NumericalFailure` and `EditAuditError`, sets `aborted` and stops sampling
(`d13_run.py:297-298`).
- An aborted rest is a failing trial under M1, but the new check turns it into INVALID.
- Confirmed with a truncated, aborted R4 record. This repeats review-1 R1's mistake.

**Why it was not caught:** `_fake_rest_record` always has 2,400 samples. The smoke list has no E1-7 rest, and the
self-check does not run `analyze`.

**Fix:**
- Derive the expected count from the compiled timestep:
  `want = ceil(round(REST_S/dt) / round(D13.SAMPLE_S/dt))`.
- For aborted records, require only `n_samples <= want` and a failing stored verdict.
- Tests: all 15 committed R3 rests dressed as M7 records give `[]`; an aborted, truncated record gives `[]` and fails
  Option A when it is an E1-1 record.
- Correct §5.
- Re-run the self-check and smoke at the new code commit, and update §6.7.

No other required change.

## OPTIONAL changes
- **O1. Smoke provenance.** Commit the `run.py provenance` output with the smoke.
- **O2. Exception rests in the report.** Rests are selected by `m7.kind == "rest60"`, so an exception rest (no `m7`
  block) is left out of the failed-rests list and silently shrinks the slip-rate denominator.
  - Select rests by experiment and tag instead.
  - Print `fail_reasons` when `e11_fail_reasons` is absent.
  - State the denominator.
- **O3.** The rehearsal turner maximum 0.185 N·m comes from `r2/r2_analysis.json`, not `r4_analysis.json`. The other
  eight values match `r4_analysis.json`.
- **O4.** A malformed rest record (missing keys while `integrity_ok` is true) would crash `e11_pass` with `KeyError`
  instead of giving INVALID. This predates revision 2.
- **O5.** Full-verdict gaps:
  - a failing E1-7 rest should give PASS;
  - an explicitly missing REST-X or E1-7 rest key should give INCOMPLETE;
  - the exception record should be built through `R.run_job` with a raising stand-in.
- **O6. Labels.**
  - "At a rate like M5's" is an `INFERENCE` (M5 scored 1/20, rehearsed 0/20).
  - §6.1's "full repository suite" claim has no evidence in §6.7.
- **O7.** The NoSlip-off table header prints only when E1-1 warm-ups exist (cosmetic).
- **O8.** No E1-7 rest or REST-X job goes through the full procedure before the scored run. Consider adding one
  non-nominal-timestep rest to an unscored check.

## Checked, and commands run
- **Diffs:** `git diff 090fc8f e807def` and `d5ba4cd e807def`.
  - Only text changed after `d5ba4cd`.
  - No diff in `src/`, E4, E5, D10, D13 or D11.
  - No physics setting, criterion or M5 procedure changed.
  - M5's `run.py` and `analyze.py` are still loaded unchanged in isolated instances.
- **`run.py all --dry-run`:** 501 / 2 / 0.
- **`run.py provenance`:** clean; the SHA-256s equal `sha256sum` and `selfcheck.json`.
- **Tests:** `pytest tests/test_scored_m7.py` 31 dots, no failures; `tests/test_scored_m5.py` 83 dots, no failures.
- **Smoke:** `analyze.py --smoke-dir smoke_rev2_2026-11-25` gives 0 violations, 0 missing, 19 records, 2 starts. The
  smoke log, `STARTS.txt` and manifest match §6.7.
- **Scratchpad scripts:**
  - the R1 reproduction;
  - the warm-up maxima;
  - `REHEARSAL_MAX` against `r2` and `r4_analysis.json`;
  - R3 E1-7 tags against M7's (58 files, 54 pass and 4 fail; all resolve);
  - the seed scan.
- **Crash and abuse paths of the new code:** no crash found except O4.
- **Stand-in tests:** not vacuous, apart from the rest length (R1).
- **Text fact-checks:** §0 items 3, 6 and 8, §1, §2, §3, §5, §6.1, §6.4 and §6.7, and P-89.

## UNVERIFIED
- The full repository suite.
- That the smoke ran on a clean tree (O1).
- §1's version counts and R4's 8.3e-14 mm pop (taken from review 1).
- The §6.6 costs.
- Whether any rest will actually abort in the scored run.
