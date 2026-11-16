# Independent review 5: PHASE_1_M5_PREREGISTRATION.md revision 5 and the §6.1 code (2026-11-16)

**Reviewer:** independent reviewer (Claude agent), read-only. No repository file was created, edited or deleted, and no git command that writes was run. `git status` was clean before and after.

**Read:**
- `experiments/PHASE_1_M5_PREREGISTRATION.md`, all of it. I read it at `9bfb3e0`. During the review HEAD moved to `44f9150` (P-43), which changes only the Status line. `git diff 6d9399d HEAD` was used for rev 4 → rev 5.
- `experiments/E5_scored_m5/run.py`, `experiments/E5_scored_m5/analyze.py` and `tests/test_scored_m5.py`, in full.
- `experiments/E4_scored_m4/run.py` in full, and `experiments/E4_scored_m4/analyze.py` lines 14–19 and 60–72.
- `experiments/D8_alignment/v3_pair_extension.py`, `d8_1b_checks.py` (header, lines 100–215, and CLI), `d8_1b_stage1.py` lines 36–175, `rehearsal_gap.py` lines 38–46 and `magnets.py` (the D8 shim).
- `src/rubiknetic/cube_physics/scored.py` (provenance, `environment`, `run_sequence_trial` head), `src/rubiknetic/cube_physics/magnets.py` lines 174–195 and 416–440, and `describe()`.
- `experiments/E1_scored/run.py` lines 55–66 and `.gitignore`.
- The six `d8_1b_checks*.json` records (summarised by script) and the four `checks_log_*.txt` files.
- `experiments/E5_scored_m5/smoke_2026-11-16.log`, plus the smoke folder's MANIFEST, STARTS, LEDGER and two records.
- Review 4's headings and optional-item list.

**Not read, and disclosures:**
- I did **not** read, list or grep anything under `experiments/E4_scored_m4/results/`. One recursive grep that would have included that folder was blocked by the permission system before it ran.
- **Disclosure:** a grep of `docs/DECISION_LOG.md` for durations accidentally printed the full P-37 row. Nothing in this review uses or depends on it. Item O7 follows from §2 of the text and review 4 item 5.
- I did not read session transcripts.

**Ran:**
- `run.py all --dry-run`.
- The unit tests: `pytest tests/test_scored_m5.py`, **44 passed**.
- `analyze.py --smoke-dir experiments/E5_scored_m5/smoke_2026-11-16`: 0 violations, 0 missing, 19 records, 3 starts. In this mode it only prints.
- Scratch scripts in my scratchpad that:
  - listed the E1-7 jobs with `classify()`;
  - summarised the V3 records;
  - checked that `to_string(parse(...))` round-trips the 20 M5 scrambles;
  - called `resume_problems()` against three earlier commits. It uses `git diff` only.

**No simulation was run on M5 seeds 10000–10999.** Scramble generation, the dry run and `resume_problems` do not step MuJoCo. The unit tests' only `mj_step` is the start-up check, which uses RNG seed 6. The smoke test and `run.py all` without `--dry-run` were not run.

## Verdict: ACCEPTABLE WITH CHANGES

The code does what the text registers in every section I checked. M4's trial logic is reused unchanged apart from the listed items. The verdict script is sound for a correct run, and the V3 and pair-check records support the registered decisions. One registered gating test is missing (V1). The code that test would cover works when I ran it by hand, so V1 is small.

## Required changes

**V1. The registered resume-refusal test for "a different frozen-path commit" does not exist.** (`FACT`)
- **What the text registers.** §6.1 item 3 (`PHASE_1_M5_PREREGISTRATION.md:354–355`) lists "resume refused on a different frozen-path commit, a different trial list, a different 'not run' set or a different table SHA-256" among the tests that gate the scored run.
- **What exists.**
  - `test_resume_refused_when_the_configuration_changed` (`tests/test_scored_m5.py:414–433`) covers only `trials`, `not_run`, `tables` and `env`.
  - Every test calls `execute` with `check_git=False` (`test_scored_m5.py:235`, `433`, `469`, `488`), so the git branch of `resume_problems` (`run.py:392–396`) is never run by the suite.
  - The smoke test never runs it either. Its manifest commit equals HEAD (`run.py:536`, `392–393`).
- **Why it matters.** This is the resume path most likely to be used. §2 allows commits during the run as long as they do not touch frozen paths, so a resume from a HEAD that differs from the manifest commit is expected. It is the only resume condition that has never been run automatically, and the §6.1 gate is not met as written.
- **The code itself works** (`FACT`, checked by hand). `resume_problems` refuses with:
  - base `14aa2a6` → "experiments/PHASE_1_M5_PREREGISTRATION.md";
  - base `9ecf5a9` → the two new V3 records plus the pre-registration;
  - base `cdfc76e` → the V3 records, `run.py`, `analyze.py` and the pre-registration.
- **Fix:** add a test case with `check_git=True`. A manifest commit whose frozen paths differ from HEAD (e.g. `cdfc76e`) must be refused, and a manifest commit equal to HEAD must give no problem. Alternatively, amend §6.1 item 3 to remove the words, but the test is the better fix.

## Optional changes

**O1. OneDrive "pause" resumes on its own.** (`INFERENCE`: product behaviour as I know it; I did not verify it here.)
- §2 (`:163–164`) relies on pausing sync, because any extra file in a results folder is INVALID.
- OneDrive's pause offers 2, 8 or 24 hours and then resumes by itself. A long run, or a run resumed the next day, can outlast the pause.
- Suggested wording: "OneDrive is exited (not paused) for the whole run, including every resume". Also check the results folders for foreign files before each resume.

**O2. Three narrow crash windows can make a correct run INVALID or blocked.** (`FACT` from the code; the probability is low.)
- (a) **Manifest write.** `write_manifest` (`run.py:374–380`) creates `results/.MANIFEST.json.tmp`.
  - A kill before `os.link` leaves no manifest and a non-empty `results/`, so every later start is refused as a first start (`run.py:436–439`). The run can never start.
  - A kill after the link but before the unlink leaves the temp file at the top of `results/`. `prepare_resume` does not move it, because its glob is `*/.*.json.tmp` (`run.py:407`), so `analyze.py:121–123` reports "unexpected file", which is INVALID.
- (b) **Orphans moved but not logged.** `prepare_resume` moves orphans (`run.py:407–413`) before the STARTS line that logs them is appended (`run.py:450`). A kill in between leaves moved orphans that are never logged, which `analyze.py:125–130` reports as INVALID. The next resume does not log them again.
- (c) **Orphan name collision.** Moved orphans are named `<exp>__<tmp name>` (`run.py:409`). A second orphan of the same trial overwrites the first through `os.replace`. That loses a file, contradicting "never deletes".
- **Fix:**
  - log the planned moves (or append the STARTS line) before moving;
  - have `prepare_resume` also log any unlogged file already in `_interrupted/`;
  - treat a top-level `.MANIFEST.json.tmp` explicitly;
  - put the start index in the moved name.

**O3. Weak spots in the verdict script and its tests.** (`FACT`)
- **Missing table record passes.** `analyze.py:216–218` passes when a magnet record has no `magnet_table`, because `man["tables"].get(None) != None` is False. Also, `table_file` is not checked against the record's configuration (`M4.table_path(magnet_params_for(overrides))`). This cannot happen in a scored run (`E4 run.py:601` always sets `info`), but the check is weaker than §5 states.
- **The "not run" set is not re-derived.** The analyzer checks only that each manifest "not run" entry is E1-7 with one of the two reasons (`analyze.py:166–168`). It could re-run `R.prepare` on the frozen V3 records and compare the sets.
- **No test fails if these checks are removed:**
  - manifest keys vs the registered list (`analyze.py:169–177`). The "trial ID outside the list" case (`test_scored_m5.py:332–333`) is caught by the manifest check instead;
  - spec vs the registered trial (`191–192`);
  - record metadata vs key (`187–188`);
  - seed vs manifest (`189–190`);
  - orphan not logged or with a different SHA-256 (`125–130`);
  - unexpected file (`122–123`, `143`);
  - magnet record without magnets, or no-magnet record with magnets (`207–220`);
  - an unregistered "not run" reason (`166–168`).

**O4. Records are serialised in the parent, outside the exception rule.** (`FACT`)
- `json.dumps(rec, default=list)` runs in `write_record` (`run.py:319`), outside `run_job`'s `try` (`run.py:275–288`).
- A record that cannot be serialised would therefore crash the parent with no record. It would hit the same error on every resume, and the run would stay INCOMPLETE. §2 says such a trial should give a failing record.
- The risk is low (`INFERENCE`): M4 used the same serialisation (`E4 run.py:642`), and the smoke records serialised.
- Fix: serialise, or test-serialise, inside the worker's `try`.

**O5. The text does not say what a mid-trial refusal does.** (`FACT`)
- §2 (`:204`) excludes "a refusal" from failing records but does not list it among the interruptions (`:209`).
- The code treats `Refused` as an interruption (`run.py:285`, `473–474`, `483–484`).
- Add "a refusal" to the interruption bullet.

**O6. The order of INCOMPLETE and NOT PASSED is not registered.** (`FACT`)
- `analyze.py:249–252` reports INCOMPLETE ahead of NOT PASSED. A run with a failed Option A trial and a missing E1-7 or E1-6n record would therefore read INCOMPLETE.
- Both outcomes are final and G1 is not passed either way, so there is no post-hoc freedom. Still, register the order, or report both words.

**O7. Commits during the run.**
- §2 (`:181–182`) forbids commits that touch the results folders, but nothing checks this. `resume_problems` diffs only the frozen paths (`run.py:394`). The results folders could be added to that diff.
- Operationally: the pre-registration file is a frozen path. The commit that records review 5's outcome must therefore come before the first start, and the file must not be edited until the run is complete. Otherwise every resume is refused and the run stays INCOMPLETE.

**O8. Wording.** (`FACT`)
- "E1-6n reuses every magnet-arm trial ID" (`:156`) is not exact. E1-6n covers E1-2 to E1-6t only (`E4 run.py:101`), so it does not reuse the E1-1 or E1-7 IDs. The dry run shows no no-magnet E1-1.
- "`MagnetSystem` stores neither the parameters nor the gap" (`:324`): it stores `mp` (`magnets.py:420`). It does not store `M1Params` or the gap.
- §6.1 item 3 says `params_for` is intercepted. The test intercepts `scored.Trial` and reads `M4._MS_KEY` (`test_scored_m5.py:96–107`). This is equivalent; only the description differs.

**O9. SciPy is not compared.** §1 names SciPy, but `ENV_COMPARED` has no SciPy version (`run.py:71`), even though SciPy is on the runtime path (`d8_1b_stage1.py:46`). Consider adding it to the manifest and the comparison.

**O10. The 0.35 mm pair check covers V3 part (a) only.** Parts (b) (tilt) and (c) (whole cube) were not extended to 0.35 mm, so that arm reuses the nominal record's 5° (`FACT`, `v3_pair_extension.py:28`). The verdict is unaffected, because E1-7 is in neither RULE2 nor RULE3 (`E4 run.py:89–90`). A one-line disclosure would help.

**O11. Smoke-folder guard.** `--smoke-dir` is not checked against `experiments/E5_scored_m5`. Pointing it there before the first start would write a smoke manifest into the scored folder, and the scored first start would then be refused for good (`run.py:561`). A guard is cheap.

**O12. Pin the committed classification in a test.** Add a unit test that the committed V3 records classify the full list as 440 runnable, 2 not run (4×1.5 N35, "failed V3") and 0 refused. Today only the dry run shows this.

## Checks that passed

**§1 configuration** (`FACT`)
- `BASE_OVERRIDES` = {radial_preload 0, gap 5e-5} (`run.py:93`).
- Every job gets `overrides.gap` through `setdefault` (`run.py:174`). The dry-run job list gives gap 5e-5 everywhere except the two E1-7 piece-gap arms (2.5e-5 and 1e-4).
- `M4.configure_process` reads `BASE_OVERRIDES` when it is called (`E4 run.py:310`), and `run_snap` uses `SC.params_for` (`d8_1b_stage1.py:142`), so non-sequence trials also get 0.05 mm.
- Walls are 0.15, 0.4 and 0.65 mm. The smoke 0.35 mm record shows wall 0.00015 and `layout_gap` 5e-5.
- Validated tilt per configuration: nominal, N52 and 0.67 → 5.0; 3×1.5 → 7.5 (from `classify` and the smoke records).

**§2 seeds** (`FACT`)
- Dry run: E1-1 10000–10019; E1-2 10100–10123; E1-3 10200–10239; E1-4 10300–10419; E1-5 10500–10541; E1-5s 10551–10568; E1-6 10600–10627; E1-6t 10640–10655; E1-7 10000.
- These match the table at `:130–140`.
- `test_seed_list_is_m4_plus_4000_and_in_range` compares against an unpatched M4 module (`test_scored_m5.py:34`, `49–61`).

**§2 run procedure** (`FACT`)
- Record key (arm, exp, tid): `run.py:164–166`. 442 keys are unique and trial IDs repeat (test at `:64–68`).
- First start requires both folders empty (`run.py:436–440`).
- The manifest holds the commit, `created`, trials (key, kind, seed, overrides), not-run entries with reasons, table SHA-256s, the environment and the frozen paths (`run.py:348–363`). It is written once with `os.link` (`run.py:379`; test `:494–498`).
- STARTS has one line per start, with k, time, HEAD, orphans and reconciled lines (`run.py:450`).
- Resume compares trials, not-run set, tables and the four environment fields, and diffs the frozen paths between the manifest commit and HEAD (`run.py:383–397`).
- The clean-commit check runs on every non-dry start (`run.py:540`, `491–496`).
- Records carry the manifest's commit (`run.py:447`, `451–452`).
- Atomic write order: tmp, fsync, link, unlink, ledger line (`run.py:313–335`). Only the parent writes; workers return `(key, rec)` (`run.py:273–289`, `477–485`).
- Exception records carry all the registered fields and pass every integrity check (test `:462–476`).
- `MemoryError` and `OSError` are interruptions with no record (test `:479–491`).
- The smoke run exercised after-link and after-tmp kills, orphan moves, ledger reconciliation and a final resume, with 0 violations.

**§3** (`FACT`)
- E1-4 scrambles use `random_scramble(20, M5 seed)` (`run.py:101–109`) and differ from M4's strings (test `:71–78`).
- The harness stores `to_string(moves)` (`scored.py:246`), which round-trips all 20 strings exactly, so the analyzer check at `analyze.py:221–225` will not flag a correct run.

**§4** (`FACT`)
- E1-7 factors and nominal values are re-centred (`run.py:94–97`). Tags `gap=5e-05`, `gap=0.0002`, `face_gap_mm=0.85` and `face_gap_mm=1.0` are absent. 27 configurations × 2 = 54 jobs: 52 run, 2 not run.
- The V3 matching rule (`run.py:126–151`) needs a V3 block, matches diameter, length, grade and scale, ignores wall, and requires exactly one match.
- Real records give exactly one match per configuration. The pair-check record has no `V3` key.
- 4×1.5 N35 is "failed V3", so it is not run. N52 and 0.67 pass V3 with validated tilt 5.0.
- **Pair check:**
  - `v3_pair_extension.py` reuses `C.fine_pair`, `C.hybrid_pair`, `REF_QUAD` (32×96), the offsets and the normaliser, and recomputes the torque tolerance over all six gaps.
  - It reproduces the nominal V3's 85 rows exactly (largest |Δ| = 0.0).
  - At 0.35 mm the worst force error is 2.15 % of Fn and the worst torque error is 3.57e-5 N·m, against a tolerance of 5.38e-5. It would also pass against V3's original tolerance of 4.79e-5.

**§5 analyzer** (`FACT`)
- Expected counts total 204 including E1-6t 16 (`analyze.py:45–46`).
- Per-trial `pass` flags and per-move `e16m_P_ok` are used (`analyze.py:238–246`).
- All §5 integrity checks are implemented (`analyze.py:102–228`).
- The INVALID tests listed in §5, the positive control (PASS with E1-6n and the not-run arm) and the accepted cases (a reconciled line and a logged orphan) all exist and pass.
- The per-move keys `max_turner_torque_Nm` and `nontarget_drift_deg` exist in harness records (`scored.py:282`, `288`), so the torque and clip report is not silently empty.
- `RESULTS.md` is written to `experiments/E5_scored_m5/`, outside the results folders (`analyze.py:372`).

**B: M4 reuse** (`FACT`)
- The patched globals are `OUT`, `OUT_NOMAG`, `SEED_SHIFT`, `SCORED_SEED_RANGE`, `SNAP_SEED_BASE`, `E16T_SEED_BASE`, `BASE_OVERRIDES`, `E17_FACTORS`, `NOMINAL`, `trials`, `magnet_params_for` and `v3_record_for` (`run.py:88–98`, `154–156`). M4 looks each of these up at call time.
- Every remaining unpatched read is overridden explicitly:
  - `M1Params().gap` at `E4 run.py:602`: `ov` always has a gap;
  - `E4 run.py:527`: called with `gap=GAP`;
  - `E4 run.py:211`: replaced;
  - the mechanism label at `E4 run.py:658`: `_execute` is not used.
- `M4.main` and `_execute` are not used. `run_job` repeats `_execute`'s steps in the same order, adding only `layout_gap` and the exception rule.

**Frozen paths and V3 files** (`FACT`)
- `M5_FROZEN_PATHS` (`run.py:73–79`) plus `scored.FROZEN_PATHS` (`scored.py:49–50`) cover everything §6.1 item 1 lists.
- Near-field tables are git-ignored (`.gitignore:74`) and covered by the SHA-256 in the manifest.
- Only `tilt_*.npz` tables are loaded at runtime. `correction_spline` and the `dU_*` tables are not called by the runner.

**E: line references new in revision 5** (`FACT`)
- All checked and correct: `run.py:211`, `232–243`, `645–648`, `689–692`, `654`, `527`, `746`, `87`, `99`, `81`, `699`, `505`, `602`, `658`; `.gitignore:74`; `d8_1b_checks.py:133`; `magnets.py:92`; `scored.py:49–50`; M4 `analyze.py:16–18`; `rehearsal_gap.py:42`; `PHASE_1_PREREGISTRATION.md:52`.
- "Eleven optional changes" matches review 4's items 1–11, and §9's mapping matches them.
- The provenance claim holds: rev 4 → rev 5 changes no criterion, threshold, factor value or seed.

**P5** (`FACT`): no test or smoke trial simulates on seeds 10000–10999. The smoke test used seeds 11000–11007 and 11051–11059.
