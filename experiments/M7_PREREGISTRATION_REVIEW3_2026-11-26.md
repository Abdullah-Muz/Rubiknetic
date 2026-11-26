# M7 pre-registration — independent review 3 (2026-11-26)

One reviewer subagent (P-86 Q8). Revision 3 at `dfae488`; code last changed at `1b5c758`. Reproduced as returned,
lightly condensed. The main session's response is in revision 4 (§11) and DECISION_LOG.

---

**Verdict: ACCEPTABLE WITH CHANGES**

**Reviewed:**
- revision 3 at `dfae488`; the code last changed at `1b5c758`, and `git diff 1b5c758 dfae488` shows no change to
  `run.py`, `analyze.py`, the tests, `src/`, E4, E5 or the D-code;
- comparison base `e807def`.

Read-only: `git status` clean, no simulation, no seed in 17000–17999 touched.

**Summary:** review 2's R1 is fully and correctly resolved. No new code defect changes a verdict. Two factual errors
in the text must be fixed before freezing (R1); everything else is optional.

## Status of review 2's items
| Item | Status | Evidence |
|---|---|---|
| R1: rest-length check | **RESOLVED** | See the four points below the table |
| O1: smoke provenance | **RESOLVED** | Provenance file committed: clean tree, same SHA-256s as `selfcheck.json`. `MANIFEST.json`, `STARTS.txt` and the log carry `1b5c758(+smoke)`. The code did not change between `1b5c758` and `dfae488` |
| O2: exception rests in the report | **RESOLVED** | `is_rest`; reasons fall back to `fail_reasons`; the denominator and exception count are printed. A synthetic run with exception records for an E1-1 rest, a REST-X rest and the 0.75 ms E1-7 rest gave NOT PASSED with 0 violations, the report listed all three, and nothing crashed. No test covers this report path (O4) |
| O3: turner figure source | **RESOLVED** | 0.185 confirmed in `r2_analysis.json` |
| O4: malformed rest crash | **RESOLVED for missing keys; PARTLY otherwise** (O2) | `E11_KEYS` covers every field `e11_pass` reads; removing any one gives a "lacks" violation |
| O5: full-verdict gaps | **RESOLVED** | Aborted E1-1 → NOT PASSED with 0 violations; failing 0.75 ms E1-7 rest → PASS; missing REST-X → INCOMPLETE; `run_job` exception test patches the instance `run_job` uses |
| O6: labels and evidence | **RESOLVED** | — |
| O7: table header | **RESOLVED** | — |
| O8: E1-7 rest before scoring | **RESOLVED** | The self-check reproduces the 0.75 ms rest, and the R3-rest test shows that record passes `m7_record_problems` |

**R1 in detail:**
- **The count matches D13's loop exactly.** `rest_samples` equals D13's `range(0, steps, chunk)` with the same
  constants: 2,400 at 0.25 and 0.5 ms, 2,425 at 0.75 ms.
- **All 15 committed R3 rests** (14 with 2,400 samples, one with 2,425) give `[]` dressed as M7 records.
- **A non-aborted rest that is truncated, has the wrong timestep or has a bad label is caught.** Each of these gives a
  violation: a 0.75 ms record truncated to 2,400; 2,425 samples labelled 0.5 ms; `rest_s` 59.9; no compiled timestep;
  `aborted: ""` with 2,400 samples.
- **An aborted rest is a failing trial, never a passing one.**
  - Aborted and truncated (to 1,000 or 5 samples), stored as failing: `[]`.
  - The same records stored as passing: a violation.
  - An abort with 0 samples would crash `times()`. The worker would raise first, though, so the stored record would
    be an exception record, which is exempt.

## REQUIRED
**R1. Two factual errors in the text to be frozen.**
- **(a)** l.428 cites `run.py` as `576e221c…9b1b9a0a`. The SHA-256 ends `…82b1b9a0a`, so the last 8 hex digits are
  `2b1b9a0a`. `analyze.py` is correct.
- **(b)** l.8, the revision-3 status bullet, says "Response in §9". The response to review 2 is §10.

No other required change.

## OPTIONAL
- **O1. Line endings.** The working-copy `run.py` and `analyze.py` are CRLF (`git ls-files --eol`: `i/lf w/crlf`), and
  the recorded SHA-256s are of those bytes. The committed LF blobs hash to `1636a3e1…cb5d4c6f` and
  `095f71f9…77163444265`. State this in §6.8 and add the LF values, or renormalize and re-take the provenance.
- **O2. Malformed-record coverage is narrower than §5 says.** These still crash rather than give a violation:
  - a field present but `None` (TypeError in `e11_pass`);
  - a missing `timeseries` (KeyError in `events`);
  - a missing `members`.

  None of these can come from the code: the worker evaluates the same functions, so an exception there becomes an
  exception record. They would stop the analysis, never give a false PASS. The early return also skips the NoSlip
  check for that record (diagnostics only). Wrap the calls in `try/except`, or narrow the §5 wording.
- **O3. Stale text.**
  - The §6 heading omits `1b5c758`.
  - The §6.2 SC rows still say 16 / 16 and do not list the 0.75 ms rest.
  - l.377 still says the revision-2 re-run replaces these results.
  - §6.8 precedes §6.7.
- **O4.** No test of `report()` on exception rests (a probe shows it works).
- **O5.** The self-check could record `m7_record_problems` for its own records.
- **O6.** M7 compares only `pass_m1_criteria` with the re-derived rest verdict. `apply_m4_criteria` ensures `pass`
  implies `pass_m1_criteria`, but nothing checks it. This is not reachable from the code. Add a one-line check.
- **O7.** Nothing compares the compiled timestep with the registered timestep (the override, or 0.5 ms). The
  self-check's 0-diff reproduction of the R3 0.75 ms rest shows the override is applied.

## Re-confirmations
- **Nothing loosened since the M7 code began.** `git diff --stat 5e74b69^ dfae488` over `src/`, E4, E5, D10, D11, D13,
  D14, the D15 code and results, ER9, the master spec, VALIDATION_PLAN and `test_scored_m5.py` is empty.
- M5's runner and verdict script are still loaded unchanged.
- The physics configuration and the criteria are unchanged; revision 3 changes only `SC_E17` in `run.py`.
- The review-1 resolutions still hold.

## Fact-checks
- **§6.8:**
  - the self-check claims are true (HEAD `1b5c758`, clean, 17 / 17, 0 differences, including the 0.75 ms rest);
  - the smoke claims match the log, `STARTS.txt`, `LEDGER.txt`, `MANIFEST.json` and `_interrupted/`;
  - `analyze.py`'s SHA-256 is correct; `run.py`'s is wrong (R1a);
  - 384 tests are collected; whether they pass is UNVERIFIED.
- **§2 resume note:** consistent with the code. `--stop-after` is refused outside smoke, `os._exit(3)` is used, only
  the parent writes records, and stray workers cannot write.
- **§10 and P-90:** accurate, apart from the scope of O2.

## Commands
- `git diff` as above;
- `run.py all --dry-run` → 501 / 2 / 0;
- `run.py provenance` → clean, SHA-256s equal to `sha256sum` and `selfcheck.json`;
- `git ls-files --eol` and the blob hashes;
- `analyze.py --smoke-dir smoke_rev3_2026-11-26` → 0 / 0 / 19 / 2;
- `pytest tests/test_scored_m7.py` → 35 passed;
- `pytest --collect-only` → 384 (M5 83, M6 45, M7 35);
- scratchpad probes as described;
- the tests checked for vacuity: under revision 2's fixed 2,400, the full-verdict runs, the R3-rest test and the
  aborted test would all have failed.

## UNVERIFIED
- That the 384-test suite passes.
- The six stray workers.
- The self-check's worker count.
- Whether any scored rest will abort; the §6.6 costs.
- §1's version counts and R4's pop value.
