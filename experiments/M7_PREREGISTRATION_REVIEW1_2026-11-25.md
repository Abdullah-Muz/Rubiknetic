# M7 pre-registration — independent review 1 (2026-11-25)

Two reviewer subagents (P-86 Q8, widened by the user to two for this round). Part A (code, procedure, validity) is
reproduced below as returned. Part B (facts and tests) is appended when it returns. The main session's verification of
each required change, and its response, are recorded in revision 2 and in DECISION_LOG.

---

## Part A — verdict: ACCEPTABLE WITH CHANGES

Scope: `experiments/PHASE_1_M7_PREREGISTRATION.md` (rev. 1), `experiments/E7_scored_m7/run.py`, `analyze.py`,
`tests/test_scored_m7.py`, `results_selfcheck/selfcheck.json`, `smoke_2026-11-25/` and its log. Checked against M5
rev. 8 (`E5_scored_m5/run.py`, `analyze.py`), M4's runner, E6's runner and tests, D13/D14/D15 code, D15 records and
DECISION_LOG P-51, P-73, P-82, P-85, P-87 and P-88. Read-only: no repository change (`git status` clean). No
simulation run; only fast, non-simulating commands (listed at the end).

### REQUIRED changes

**R1. A harness-exception record makes the whole run INVALID, but M5 §2 makes it a failing trial.**
- **Evidence.**
  - `E7_scored_m7/analyze.py:82-88`: `m7_record_problems` adds the edge violation (l.82-83) and the m7-block
    violation (l.84-86) *before* the early return for `harness_exception` (l.87-88).
  - The comment on l.88 says the opposite.
  - M5's `exception_record` (`E5_scored_m5/run.py:287-301`) writes `params = {"gap": gap}` and no `m7` block.
    `run_job` (`run.py:319-320`) produces that record for any harness exception.
- **Reproduced without simulation.** For records built by `R.exception_record(job, ValueError("boom"))`,
  `m7_record_problems` returns 2 violations each for E1-2 `U_s17100`, E1-1 `rest_s17000`, REST-X `rest_s17700` and
  E1-7 `timestep=0.00025__6move`:
  - `edge None None != rounded 0.0025`;
  - `m7 block None / None != 0.0025 / 10`.
- **Why it matters.**
  - The text (§2, "harness exceptions become failing records", M5 U1 (iii)) and the M6 precedent
    (`tests/test_scored_m6.py:544`) treat such a record as a valid failing trial. M7's code makes it INVALID.
  - This holds for any trial, including the reported-only E1-7, E1-6n and REST-X ones. One exception in a fragile E1-7
    setting would turn an Option A PASS into INVALID.
  - It is realistic: a `NumericalFailure` during `scored.Trial`'s 0.5 s settle is raised outside the trials' try
    blocks, as is the "cannot be serialised" path of `run.py:316`.
  - No test covers it.
- **Fix.**
  - Move `if rec.get("harness_exception"): return []` to the top. M5's integrity checks still apply.
  - Optionally require `rec.get("pass") is False`.
  - Add a test mirroring M6's (exception record from `R.run_job` with a stand-in `M4.run_trial` that raises → 0
    violations, NOT PASSED), including a REST-X or E1-7 case with no effect on Option A.

**R2. Disclosure: without NoSlip, the M7 configuration fails M1's E1-1 on rehearsal and fresh seeds, and the text's
wording implies otherwise.**
- **Evidence.**
  - Every 60 s rest is preceded by a 10 s warm-up. The warm-up is exactly M5's E1-1 with rounded edges R 2.5 mm and
    **no NoSlip** (`run.py:204-205`; D15 `r1_run.rest_worker:110,120`, `r3_run.rest_worker:248,254`).
  - Its outcome is stored as `warmup_10s` and never judged. The D15 records show these warm-ups fail M1's ≤ 0.5°:
    - R2 L0 (rehearsal seeds), 3/20: `rest_s16003` 0.709°, `rest_s16005` 0.549°, `rest_s16018` 0.694°;
    - R4 L0 (fresh seeds), 1/20: `rest_s19008` 0.577°.
  - The judged 60 s NoSlip-10 rests of the same seeds give 0.0004–0.0012°.
  - §0 item 6 (l.77-78) says R3 shows the outcome holds "over NoSlip 5–20 and, for sequences, with NoSlip off". That
    is literally true but omits that the rest outcome with NoSlip off fails.
  - §1 (l.120-121) says NoSlip's effect "is bounded by R3's NoSlip 5 / 20 / 0 arms", but R3's NoSlip-0 arm is
    sequences only.
  - Nothing in DECISION_LOG or the D15 README reports the warm-up outcomes.
- **Why it matters.**
  - The headline E1-1 result depends on a post-hoc solver post-process. Without it, the configuration would fail
    E1-1 at a rate similar to M5's.
  - The scored run will produce 75 more such warm-ups, which would sit silently inside a PASS.
  - CLAUDE.md requires abstractions and their consequences to be documented.
- **Fix.**
  - §0 item 6 and §1: state the warm-up numbers and that E1-1 passes only with NoSlip on. Limit the NoSlip-0 bound to
    sequences.
  - §4.2 and §6.1: state that each rest60 trial first runs M5's 10 s E1-1 (rounded edges, NoSlip 0) as a recorded,
    unjudged warm-up.
  - §4.3 and `analyze.py`: report the warm-ups (count above 0.5°, max) as "NoSlip-off E1-1 (reported)".

**R3. §3 marks a seed-search claim as `FACT` beyond the scope of the search that supports it.**
- l.141 says "no record anywhere uses 17000–17999", but §6.4 covered only `.json`, `.json.gz` and `.jsonl` files
  under `experiments/`.
- `git grep` found only test stand-in keys, none simulating.
- **Fix:** limit the claim to §6.4's scope, or mark it `TODO`.

**R4. §2 says "The start log records the load at start", but it does not.**
- M5's start-log line (`E5_scored_m5/run.py:532`) has only `k, time, head, orphans, reconciled`. The load is stored
  per record as `loadavg_start`.
- **Fix:** correct the text. Adding it to the start log would change M5's frozen runner.

**R5. The Clopper–Pearson bound is misstated.**
- §5 and Q7 say 0/60 gives "about 5 %", but the code computes the two-sided 95 % upper bound, 0.0596, and the test
  asserts it.
- **Fix:** say "about 6 % (two-sided 95 %)", or register a one-sided bound (0.049) and change the code and test.

### OPTIONAL changes
- **O1. Stub test for all 501 jobs.** `noslip=0` and 13 rest settings are exercised only by a fake-trial unit test.
  Add a stub test as E6's `test_core_layout_and_gap_in_every_job`: replace `scored.Trial` with a stub that records
  params and raises before stepping, then assert edge, NoSlip wrapper count and `d13_rest` cfg per job.
- **O2. Provenance.** `selfcheck.json` records `head 5e74b69`, but the 16-trial list was committed only in `090fc8f`
  (the tree was dirty), and the smoke ran at `e795a2c+smoke`. Record `git status --porcelain` in the self-check, and
  re-run the self-check and smoke at the final committed code.
- **O3. Reuse determinism.** E1-7 `nominal__rest60` and E1-1 `rest_s17000` should give identical `d13_rest` records
  under `ProcessPoolExecutor` worker reuse. Report that equality.
- **O4. Rest checks.** Check the 60 s length from `sim_time_s` or the sample count, and re-derive the 0–10 s rotation
  from `timeseries.rot_deg`.
- **O5. `e11_pass` test.** Use all 20 R4 records and perturb each criterion; take thresholds from
  `scored.THRESHOLDS`.
- **O6. Fail reasons.** A slip failure shows only "M1 criteria" (`apply_m4_criteria` overwrites the list). Print
  `e11_fail_reasons` in the report.
- **O7. Registered reporting not implemented.** Torque beside R2's L0 values; margins against every threshold beside
  §0 item 8; E1-7 flips against R3 (R3's `noslip_ref=0` is M7's `noslip=0`). Implement them, or state they are
  written by hand.
- **O8.** Assert that the REST-X and E1-7 rest seeds lie in `M4.SCORED_SEED_RANGE`.
- **O9.** Assert that each `M5_RESTATED` line is present before it is replaced in the report.
- **O10. Storage.** A 60 s rest record is about 11.4 MB, so 75 rests come to about 0.85 GB. Check free disk at start
  and plan how the results will be committed.
- **O11.** §4.1 radial pop can also cite R4's 1376 moves: largest `radial_above_nominal_mm_so_far` 8.3e-14 mm.
- **O12.** `test_run_trial_installs_and_consumes` should restore the patched globals in a `finally` or via
  monkeypatch.

### Checked and found correct (summary)
- **`FACT`s:** M5 (P-51); R2 (P-82); R3 (P-85, including the `noslip_ref=0` records); R4 (P-87); `m1_model.py`
  line 13; turner settings; validated tilt and magnet size; M5 E1-1 `radial_above_nominal_mm` 7.63e-14 mm in all 20;
  the software versions; D12's seed guard.
- **Code against text:**
  - the seed map, the counts (501 + 2), the E1-7 factors and rest tags;
  - rest60 against `r3_run.rest_worker`; `e11_pass` byte-equivalent to D14's; D11's `events`;
  - **no criterion loosened relative to M5** (penetration, integrity and final-solved are judged over 60 s, stricter;
    only pop is omitted, and it is inert in B1);
  - per-trial installs rebuilt every trial; snap trials get the edge; the magnet model has no NoSlip;
  - isolation and the reused M5 procedure, including the clean-commit refusal, manifest, resume and OneDrive check
    using M7's lists;
  - `check_records` replaced in the module namespace; the mechanism filter removes only M5's exact "M7" message;
  - verdict and Option A unchanged; REST-X and E1-7 outside `ROWS`; INCOMPLETE and INVALID behave as in M5;
  - M5's integrity checks on E1-7 and REST-X rests; frozen paths;
  - the self-check (16 / 16) and the smoke (kill, resume, 19 records).
- **Commands:**
  - `run.py all --dry-run` → 501 / 2 / 0;
  - `pytest tests/test_scored_m7.py` → 14 passed;
  - `pytest tests/test_scored_m5.py` → 83 passed;
  - `analyze.py --smoke-dir` → 0 violations, 0 missing;
  - a scratchpad script confirming R1;
  - record reads (M5 E1-1, D15 `warmup_10s`, R4 pop, R3 NoSlip, smoke fields, `selfcheck.json`);
  - `git log`, `git diff 5e74b69 090fc8f`, `git grep`.
- **UNVERIFIED:**
  - the full repository suite;
  - commit identity of the smoke and self-check code (O2);
  - reuse determinism (O3);
  - DECISION_LOG figures not re-derived: R3's 0.011°, R2's 0.293 mm, the §6.6 costs.

---

## Part B — facts and tests: required changes

Scope: fact-check of the text (rev 1, `090fc8f`) and test coverage of `tests/test_scored_m7.py` against `run.py` and
`analyze.py`. No repository file changed, no simulation run.

### REQUIRED
- **B-R1. The 0/60 Clopper–Pearson bound is about 6 %, not 5 %** (§5, §8 Q7).
  - The code computes the two-sided 95 % bound: 1−0.025^(1/60) = 0.0596. "About 5 %" is the one-sided value
    (0.0487).
  - Duplicates Part A R5.
- **B-R2. The start log does not record the load** (§2).
  - STARTS.txt holds only `k, time, head, orphans, reconciled`. The load is stored per record as `loadavg_start`.
  - Duplicates Part A R4.
- **B-R3. A harness exception makes the run INVALID; it should give a failing record.**
  - `analyze.py:82-86` checks before the l.87-88 early return.
  - Verified for `U_s17100`, `rest_s17000` and `noslip=0__6move`.
  - Add tests for a seq job, a rest60 job and `noslip=0`. Duplicates Part A R1.
- **B-R4. "CAD piece gap 0.25 mm" is miscited and contested** (§0 item 3, cited to P-77).
  - P-77 does not state it; the figure is from `ER9_anchored_core_layouts/side_checks/README.md:56`.
  - `docs/research/MAGNET_POCKET_WALL_FINDINGS.md:99-102` records it as an unresolved conflict with
    `CUBE_MECHANISM_FINDINGS.md:71`, which gives 0.033–0.038 mm.
  - Cite both figures and mark the question unresolved.
- **B-R5. Unlabelled claim:** "Real speedcube pieces are rounded or bevelled at their edges (corner cutting)" (§0 item
  5).
  - The project records say real-cube edge geometry is unverified (P-78, P-82).
  - The only corner-cutting source is UNVERIFIED (`D14…/diag_catch/README.md:212-223`).
  - Corner cutting is a turning tolerance, not an edge profile.
  - Label it UNVERIFIED/ASSUMPTION, or remove it.
- **B-R6. The rest60 path (the Q4 criterion) has no unit test.**
  - No self-check rest uses a non-nominal `edge_radius` or `noslip`.
  - Add a test that monkeypatches `_m4_run_trial` and `d13_rest`, and asserts for the warm-up and the rest:
    - the M7Trial radius;
    - the unwrapped XML;
    - `cfg` (NoSlip, params without edge/noslip/magnet keys);
    - `duration_s == 60`;
    - `rec["m7"]`.
  - Repeat with a slip in `rot_deg`: pass False, `ok_no_slip` False, events ≥ 1, and the fail reason.
- **B-R7. No positive control or full-verdict test for M7's analyze.** Adapt M5's complete-set fixture to M7's list:
  - complete set → PASS;
  - an E1-1 slip → NOT PASSED;
  - a failing REST-X or E1-7 rest → PASS;
  - a missing REST-X or E1-7 rest → INCOMPLETE;
  - an extra record → INVALID;
  - a harness exception → NOT PASSED.
- **B-R8. The self-check and smoke results are not tied to the commits the text names.**
  - The smoke ran at `e795a2c+smoke`, before the E7 code was committed.
  - `selfcheck.json` records `5e74b69`, but the 16-trial list was committed in `090fc8f`.
  - Disclose this, or re-run both at the freeze commit and record the SHA-256 of `run.py` and `analyze.py`.

### OPTIONAL
- **B-O1.** The file count is now 5,814 (rescan: 0 matches). "No record anywhere" should read "under `experiments/`".
  `git grep` will hit synthetic `_s17xxx` keys in the M6/M7 tests.
- **B-O2.** E1-5s is "2 repetitions over 10 seeds" (seed = base + 10·rep + |δ|), not "2 seeds".
- **B-O3.** GS1 is ER9 Part G's gate, not ER7's.
- **B-O4.** The records give only a platform string (`glibc2.39`); the venv is Ubuntu 24.04.5. The versions match all
  357 R2, 74 R3 and 214 R4 records.
- **B-O5.** "Switch timing does not apply (FACT)" is an inference from a docstring spanning `m1_model.py:11-13`.
  Relabel it, or cite per-record `edit_audit_violations`.
- **B-O6.** The label legend lacks ASSUMPTION and UNVERIFIED.
- **B-O7.** R3's `noslip_ref=0` is M7's `noslip=0`. Otherwise M7's E1-7 list equals R3's 73 plus the 2 not run.
- **B-O8.** `m7_sections` lacks "beside R2's L0 values", "beside the §0 item 8 maxima" and "E1-7 flips against R3".
- **B-O9.** Strengthen tests:
  - compare with M5's `MANIFEST.json` (verified: all 438 non-chamfer keys map with seed + 7000);
  - check `e11_pass` on all 20 R4 records, perturbing each of the 7 conditions;
  - record-check cases: `noslip=0` wrapper calls, a rest with wrong NoSlip, mismatched `n_slip_events`, a chamfer
    profile;
  - check the measured rest length (`timeseries.t`);
  - check that M7Trial passes the profile and radius, and that the wrapped XML has `noslip_iterations`, using
    monkeypatch;
  - test the report title and restated lines;
  - check `v3_not_run` on M7's list;
  - check that M5's own runner instance is unchanged.

### Checked and correct
- **Tests and runs:** pytest 14 passed; dry run 501 / 2 / 0 with the §3 seed ranges; smoke integrity 0 / 0 / 19 / 2.
- **Records and log:**
  - DECISION_LOG P-24–P-30, P-51, P-66, P-73, P-76–P-88;
  - commits `01938af`, `5e74b69`, `090fc8f`;
  - `r2_analysis.json`, `r4_analysis.json`, the R4 log (1 h 38 min), `r3_analysis.json`, `r3_static.json`;
  - M5 E1-1 pop 7.63e-14 mm;
  - the software versions in all R2/R3/R4 records.
- **Code constants and references:**
  - `scored.THRESHOLDS`; SNAP 3° / 0.5°; slope 0.005; clip 0.999; D11's WIN 8 × 25 ms and THR 0.2°;
  - `d14s3_analyze.py:105-110` (identical by diff), `install_edge`, `with_noslip`;
  - the D12 and ER9 seed guards.
- **Evidence:**
  - the self-check, 16 / 16 with 0 differences;
  - the smoke (5 + 14 records, 1 orphan, 1 reconciled, 332 s);
  - 25 frozen paths in the manifest;
  - the §6.6 costs (9.58 CPU-h, E1-4 6.24, R3 3.78, REST-X 3.46).

### UNVERIFIED
- M5's tests and the full suite in the same session.
- The E1-6n cost.
- "The magnet model has no NoSlip."
- That `run.py` at smoke time equalled `5e74b69`.
