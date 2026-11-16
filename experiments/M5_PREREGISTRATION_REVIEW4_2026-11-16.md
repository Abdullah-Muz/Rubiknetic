# Independent review 4: PHASE_1_M5_PREREGISTRATION.md revision 4 (2026-11-16)

Reviewer: independent subagent, read-only. I modified no repository file, ran no simulation and ran no git command that writes. I ran only these commands, all read-only:
- `git log`, `git diff c5cd5d6 6df84fd`, `git ls-files`, `git check-ignore`;
- Python that reads the three V3 JSON files;
- one WSL Python call that imports the M4 runner and calls `build_jobs("all", ...)`. It builds a list only, with no stepping and with `PYTHONDONTWRITEBYTECODE=1` set.

**`experiments/E4_scored_m4/results/` was NOT read, listed, grepped or `git show`n.** No session transcripts were read. I read DECISION_LOG P-37 only up to its first sentence. Its full row did appear as unchanged context in the required `git diff c5cd5d6 6df84fd` output. I used none of that row's content, and I did not check the "123 / 204" quoted in the provenance statement (line 16) for that reason.

Read:
- M5 pre-registration revision 4 (all) and the rev 3 → rev 4 diff;
- reviews 2 and 3 (all);
- M4 pre-registration §4 E1-7, §5 and Amendment 1 (the parts cited);
- M1 pre-registration §2 (line 52);
- `E4_scored_m4/run.py` (all) and `E4_scored_m4/analyze.py` lines 1–80;
- `E1_scored/run.py` lines 1–110;
- `rehearsal_gap.py` lines 38–46;
- `magnets.py`: `MagnetParams`, `layout`, `MagnetSystem`, `describe`;
- `scored.py`: `FROZEN_PATHS`, `require_clean_commit`, `base_record`, `params_for`, `run_sequence_trial` head, exception handling;
- `d8_1b_stage1.run_snap` (record construction);
- `d8_1b_checks.py` (`v3`, `main`, `SIZES`);
- `cube_logic/scramble.py`;
- all three `d8_1b_checks*.json` (`magnet_params` and V3 block);
- listing of `D8_alignment/results/` and `tables/`;
- `.gitignore`;
- DECISION_LOG P-39.

## Verdict: ACCEPTABLE WITH CHANGES

T1 is substantively fixed:
- the commit, the trial list and the E1-7 "not run" set are fixed at first start;
- existing records cannot be rewritten;
- §6.1 item 5 is gated before the first start;
- `results_nomag/` is covered.

The twelve optional items are implemented correctly, and every V3 requirement can be met with the files and tools that exist. Nothing from reviews 1–3 has regressed, and no M1 or M4 threshold is weakened.

Two required changes remain. Both are internal contradictions in the new §2 and §5 text. Followed literally, each would turn a correct or properly resumed run into INVALID, or leave the analyst with an unregistered choice after seeing scored data. Both are small wording fixes.

## Required changes

### U1. The resume rule and the integrity rule conflict in three cases, so some interruptions and exceptions have no registered outcome

**FACT (text):**
- §2 promises that an interrupted run "is resumed under the rule above" (lines 164–166).
- The same section and §5 give INVALID for "a leftover temporary file", "a record without a ledger line" (lines 167–169, 227–229), and for any record whose `params.gap` / `magnets.layout_gap` is not the registered value (lines 220–223).
- The record procedure is: write a temporary file, link it to the final name, then append the ledger line (lines 158–161).
- Resume "runs only trial IDs that have no record" and "never deletes, rewrites or reruns an existing record" (lines 155–156).

**(a) Leftover temporary file (INFERENCE).**
- A process killed (OOM, WSL restart) after the temporary file is created leaves it on disk. The same happens if the kill falls between the link and the removal of the temporary name; the text does not say the temporary name is removed at all.
- On resume, that trial has no record, so it is rerun and gets its own record. The orphan stays, so the run is INVALID under line 167.

**(b) Record with no ledger line (INFERENCE).**
- A kill between the link and the ledger append leaves a complete record with no ledger line.
- Resume skips that trial because a record exists, so the missing ledger line can never be supplied. The run is permanently INVALID.

**(c) Records written for harness exceptions (INFERENCE, based on FACT).**
- An exception record "with the exception text" (lines 162–163) is not built through `Trial.base_record()`. That is where `params` comes from (`scored.py:214–216`).
- So, unless the text says otherwise, such a record has no `params.gap` and no `magnets.layout_gap`, and line 220 makes it INVALID, not "a failed trial" as line 163 says.
- This can happen in E1-6n or E1-7, which are reported-only arms. The scored harness catches only `NumericalFailure`/`EditAuditError` (`scored.py:302`, `333`, `393`, `418`, `454`, `507`); any other exception escapes to the runner.

**Why this is required.** These are the T1 failure class again, in small time windows.
- The probability is low (the write and link windows are short), but not zero.
- When it happens, the text gives two contradictory outcomes: "resume" and "INVALID".
- The author would then decide, after seeing scored records, whether to hand-delete the orphan or hand-append the ledger line, or accept INVALID. The freeze rule forbids repairing the text after the first scored trial.

**Change.** State the rules explicitly. One sufficient form:
- **(i) Orphans at resume.** Before running anything, a resume moves every orphan temporary file to `results/_interrupted/` and logs its name and SHA-256 in the start log. The verdict script treats only unlogged temporary files as violations.
- **(ii) Missing ledger lines at resume.** For a complete, parseable record that is in the manifest but has no ledger line, the resume appends the line, marked "reconciled at start k". The verdict script accepts reconciled lines and reports them.
- **(iii) Exception records.** They carry the job metadata (experiment, sub-experiment, trial ID, seed, arm, commit, mechanism, `scored`, `spec`). They also carry the configured `params.gap` and, for magnet jobs, the `magnets.layout_gap`, both taken from the job's overrides. All §5 integrity checks apply to them unchanged.
- **Tests.** Add a §6.1 item 3 test for each of (i)–(iii).

### U2. The ledger and resume rules are keyed by trial ID alone, but E1-6n reuses every magnet-arm trial ID

**FACT:**
- E1-6n jobs are built from the same `trials(e2)` lists, with the same `tid`, and differ only in output folder (`run.py:689–692`).
- I ran `build_jobs("all", ...)` on the M4 runner (read-only, no stepping). It gives 442 jobs and 184 duplicated trial IDs, for example `U_s6100`. There are no duplicates within the magnet arm, and none once the key is (folder, experiment, tid).
- M5 has the same structure, with seeds + 4000.
- §2 says the runner appends "its trial ID" for each record to the single `results/LEDGER.txt` (lines 159–161). It says "a trial ID that appears twice in the ledger" gives INVALID (line 168), and resume "runs only trial IDs that have no record" (line 155).

**INFERENCE:**
- Implemented literally, every complete, correct run is INVALID: 184 duplicate ledger IDs.
- A tid-keyed resume would also never run an E1-6n trial whose magnet twin already has a record.
- None of the §5 tests (lines 230–235) is a positive control that would expose this before the run. If it is first noticed afterwards, the choice of how to read the rule is made after seeing the results.

**Change:**
- Define the record key everywhere in §2 and §5 (manifest, ledger, resume, duplicate check, "not in the manifest") as (arm or output folder, experiment, trial ID).
- Add a §6.1 item 3 / §5 test: a complete, valid synthetic record set, including E1-6n and E1-7 with its registered "not run" arms, must give PASS and not INVALID.

## Optional changes

1. **Inputs outside git are not fixed across starts.**
   - The near-field tables are git-ignored (`.gitignore:74`, `experiments/D8_alignment/results/tables/`), so the clean-commit check does not cover them. `magnet_availability` refuses on a missing table but does not check its content (`run.py:249–262`).
   - The Python environment is also outside the commit.
   - Suggestion: record each configuration's `table_sha256` and `scored.environment()` in `MANIFEST.json`. A resume should refuse on any mismatch and also require the same "not run" set. The verdict script should check every record's `magnet_table.table_sha256` and `environment` against the manifest. Each record already stores the table SHA (`run.py:262`, `635`).
2. **Ledger writer and filesystem.**
   - `_execute` runs in pool workers (`run.py:759–760`). Concurrent appends from several processes to one file on `/mnt/c` (drvfs, inside OneDrive) may not be atomic, and I could not check, read-only, that hard links (`os.link`) work there (unverified INFERENCE).
   - Suggestion: let the parent process write the ledger (one writer).
   - Run the run-procedure tests with `--jobs` > 1 on the real results folder.
   - Consider pausing OneDrive sync during the run: a sync conflict copy inside `results/` would be "a record not in the manifest".
3. **Start log.**
   - "The number of trials it ran" (line 156) cannot be written for a start that is killed, which is the case that matters for the G1 restatement (line 243).
   - Suggestion: put a start index in each ledger line and derive the per-start counts from it.
   - Keep `MANIFEST.json` immutable after first start, with the start log in a separate append-only file, and write the manifest atomically.
4. **Finality of INCOMPLETE / INVALID.** Line 170 says results are committed "only after the run is complete", so an INCOMPLETE run is never committed. Suggested wording:
   - `MANIFEST.json`, once written, is never deleted;
   - M5 has only one first start;
   - INCOMPLETE and INVALID are final, like a failure (line 244);
   - the partial records are committed and reported.
5. **Commits during the run.** Resume requires HEAD = the manifest's commit (line 154). `require_clean_commit` checks only the frozen paths, and uses whatever HEAD is (`scored.py:59–64`). State that a resume may be run from a checkout of the manifest's commit (detached HEAD), and that commits made during the run touch neither frozen paths nor the results folders. Otherwise a routine DECISION_LOG commit would look like an "impossible resume".
6. **Define the 0.35 mm pair check exactly.**
   - Today `d8_1b_checks.py` hard-codes pair gaps 0.5–1.5 mm (`d8_1b_checks.py:133`), so a script change is needed.
   - `pair_T_tol_Nm` depends on which rows are in the set (`d8_1b_checks.py:136–139`), so "unchanged settings" needs to say how it is computed.
   - Also name the magnet configuration (presumably 4×2 N35, scale 1) and the record file. A file outside the `d8_1b_checks*.json` glob would fall outside the clean-commit check named in §6.1 item 1.
   - Require that exactly one V3 record matches each (size, grade, scale) and that the matcher ignores `wall`. If it compared `wall`, every face-gap arm would be refused.
7. **More integrity tests and checks.**
   - Tests that should each give INVALID: a leftover (unlogged) temporary file, a duplicate ledger key, a ledger line without a record, a record not in the manifest, a `layout_gap` that equals `params.gap` but not the registered value of a piece-gap arm.
   - Checks: add `startup_checks.gap` = 5e-5 to the §5 integrity list, so the line 112–114 claim is checked rather than only auditable. Consider checking `magnets.params.wall` against 0.15 / 0.4 / 0.65 mm per face-gap arm, which catches the `run.py:211` bug class after the run.
8. **Exception classes.**
   - A `MemoryError` becomes a permanent failed trial, while an OOM kill is resumable (lines 162–166). That is pre-registered, so it is not a post-hoc choice, but it is inconsistent.
   - Consider treating `MemoryError`/`OSError` as an interruption (no record; the process exits).
9. **Gap test wording** (lines 274–279). "For every job" should leave out the no-magnet jobs from the `p_loc` comparison, as §5 already does (lines 222–223).
10. **Provenance and wording.**
    - Line 17 says "every revision-4 change comes from review 3's text". The ledger, SHA-256, start log, trial-list identity check and harness-exception rule are the author's elaborations of option (a), not review 3's text. Say so; the "not informed by M4's results" statement still covers them.
    - "No configuration … is changed" (line 18): the 0.67-scale arm is newly gated on its own V3 record, which could change whether it runs. It is stricter, not looser, and it traces to review 3 item 8.
    - Line 56 ("That proposal's revision 3") is an untraced but harmless clarification.
    - Line 142 says the CLI "runs one experiment per call"; it also accepts `all` (`run.py:683–684`).
11. **Smoke test** (line 287). Let it exercise the full run procedure on a scratch folder (manifest, ledger, atomic link, a forced interruption and a resume), plus at least one E1-6n job and one E1-7 job per magnet configuration.

## Checks that passed

**T1 is fixed in substance (FACT unless marked):**
- The first start requires both `results/` and `results_nomag/` to be empty (lines 149–152). `OUT_NOMAG` is the second folder `_execute` writes into (`run.py:72`, `692`).
- A resume needs the manifest's commit, the clean-commit check and an identical trial list. It runs only missing trials and never rewrites (lines 153–157).
- §6.1 item 5 must be committed before the first start, and the runner refuses if any trial outside the registered E1-7 "not run" reasons would be refused (lines 146–148, 203, 289–291). This closes review 3's case of an N52 or 0.35 mm arm refused and impossible to run later.
- "Link to final name, fails if it exists" (line 159) is a correct no-clobber primitive, and it replaces the non-atomic `open(path, "x")` write (`run.py:639–642`).
- Changing the commit, the trial list or the "not run" set after seeing partial results is refused. The V3 records are under the clean-commit glob, and new untracked `d8_1b_checks*.json` files are not git-ignored (`git check-ignore`: only `tables/` matches), so they would show as dirty.
- Deleting a record and resuming: the record's ledger line is left with no record, which gives INVALID. Even with the ledger also edited by hand, a rerun from the same seed and commit should give the same result, because the setup is drawn from the seed and P-26 removed the dependence on trial order (`magnets.py` `reset_neighbour_list`; `run.py:604`). Selective rerunning would gain nothing (INFERENCE). Tamper evidence beyond that relies on honest operation (optional items 1 and 4).
- A run that cannot be resumed is INCOMPLETE and G1 is not passed (line 166), so the outcome is fixed in advance.

**The twelve optional items are correct (FACT):**
- **Item 1.**
  - `MagnetSystem` stores neither `p` nor the gap (`magnets.py:418–438`), and `describe()` omits the gap (`magnets.py:502–504`).
  - `p_loc` comes from `layout(pitch, gap, mp)` (`magnets.py:92`, `421`, `424`), so comparing it with `layout(pitch, expected_gap, mp)` is exact and needs no stepping.
  - It catches both N1 (the rehearsal overwrite, `rehearsal_gap.py:42`) and O3 (gap missing from the per-trial overrides: `use_magnets` would get 2e-4 through `run.py:602`).
  - Storing `layout_gap` inside `rec["magnets"]` fits records without magnets, where that field is `None` (`run.py:633`).
- **Item 2.** The face-gap arms keep piece gap 5e-5. Only the two piece-gap arms differ.
- **Item 3.** The listed INVALID tests are specified (lines 231–235).
- **Item 4.** E1-6t is added at line 242.
- **Item 5.** The `d8_1b_checks*.json` glob is in the clean-commit list (line 269).
- **Item 6.** The Basis list (lines 43–53) and the §4 preamble (lines 194–196) are complete.
- **Item 7.** `SCORED_SEED_RANGE` (`run.py:81`, asserted at `699`), `OUT` and `OUT_NOMAG` are named, plus "unchanged except".
- **Item 8.**
  - Grade and scale both act only through the magnet strength: `br` from `GRADES_BR`, and moment ∝ Br·√scale (`magnets.py:62`, `83–85`).
  - Every V3 record carries `grade` and `scale` in `magnet_params`: `d8_1b_checks.json` = 4×2 N35 scale 1; `_3x1.5_N35_s1` = 3×1.5 N35 scale 1; `_4x1.5_N35_s1` = 4×1.5 N35 scale 1 with V3 `pass: false`. Matching by size, grade and scale is therefore satisfiable for the nominal configuration and the 3×1.5 arm.
  - `d8_1b_checks.py --size 4x2_N52` and `--scale 0.67` write `d8_1b_checks_4x2_N52_s1.json` and `d8_1b_checks_4x2_N35_s0.67.json` (`d8_1b_checks.py:364–372`). Both names fall inside the glob.
  - Both tables exist: `tilt_4x2_1.455T_s1_…npz` and `tilt_4x2_1.19T_s0.67_…npz`. Their names match `table_path` (`run.py:217`).
- **Item 9.** The 3×1.5 N35 record has V3 `validated_tilt_deg` 7.5 and `pass: true`. `run.py:654` uses each configuration's own tilt.
- **Item 10.** `startup_checks` already takes `gap` (`run.py:522`, `527`); recording it is a small addition.
- **Item 11.**
  - `random_scramble(20, s)` is deterministic in `s` (`scramble.py:16–30`).
  - M1 builds each sequence as `sc + invert(sc)` (`E1_scored/run.py:58–61`), and the stored `sequence` is at `scored.py:246`, so re-deriving it is feasible.
- **Item 12.** Line 203 is consistent with "E1-7 … must be completed" (line 236).

**No regression of N1 or R1–R5 (FACT):**
- **N1:** precedence and the rehearsal-overwrite prohibition (lines 253–254); E1-7 nominal of 0.05 / 0.85 mm (line 202); the test must fail under the overwrite (line 279).
- **R1:** the seed table and unit test are unchanged (lines 115–140).
- **R2:** the counts (sum 204), E1-6t through `pass` (`run.py:503–517`), E1-6m through `e16m_P_ok`, and the tests are kept and extended.
- **R3:** unchanged.
- **R4:** the band and the disclosures are unchanged.
- **R5:** the stale "in progress" text is updated (lines 34, 136), §8 lists only open decisions, and the freeze rule (lines 30–35) is intact. It allows user-approved amendments before any scored trial and requires the "not informed by M4" statement, which is given at lines 16–19.

**No threshold weakened (FACT):**
- The diff touches no criterion, threshold, factor value or seed.
- §4's list (lines 182–192) and Option A (lines 206–207) are unchanged.
- Every new rule is stricter (V3 per grade and scale; more INVALID conditions) or procedural.

**Line references and numbers new in revision 4, all matching (FACT):**
- `run.py`: `645–648` (`_execute` skips existing records), `654` (per-configuration tilt), `81`/`699`, `232–243`, `602`, `658`, `211`, `527`/`746`, `87`/`99`, `505`.
- Other files: `magnets.py:92` (`layout`), `magnets.py:418–438` (`MagnetSystem.__init__`), `analyze.py:16–18`, `PHASE_1_PREREGISTRATION.md:52`, `rehearsal_gap.py:42`.
- Values: 7.5° (3×1.5 N35); V3 pair gaps 0.5–1.5 mm (`d8_1b_checks.py:133`); 2.5e-5 / 1e-4 / 5e-5; 10000–10999.
- The nominal record's 7.5° tilt fails (`worst_T_err` 3.92e-5 > `tilt_T_tol` 3.52e-5), which supports line 97. M4 Amendment 1 (M4 pre-registration line 174) quotes a 2.4e-5 tolerance, which differs from the current record. That is an M4 text issue; the outcome is the same.
- Not checked: "123 / 204" (line 16), because of the P-37 exclusion.
