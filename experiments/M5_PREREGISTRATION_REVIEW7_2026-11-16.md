# Independent review 7 (very narrow): the revision-7 changes to PHASE_1_M5_PREREGISTRATION.md (commit `acf570e` against `74b30a3`), 2026-11-16

## Verdict: ACCEPTABLE AS IS

I found no defect that would make a correct scored run INVALID, INCOMPLETE or refused, or that would let an incorrect run pass. W1 is met, and X1–X6 are implemented correctly. The optional items below are wording and test-strength points only.

**Scope and constraints kept.**
- I read the diff, the affected code, review 6's "Required changes" and "Optional changes", and the changed prereg sections.
- I did not read `experiments/E4_scored_m4/results/`. Both scratch extractions excluded it.
- I read no DECISION_LOG row beyond P-44 to P-47, and no transcripts.
- I ran no simulation on M5 seeds. The only `run.py` invocation was `all --dry-run`.
- I changed no repository file; `git status --porcelain` is empty afterwards. All scratch work is in `C:\Users\abdul\AppData\Local\Temp\claude\b6672f8dce1e00f4\3140f1d7-6e9e-4f5a-9e6c-c7e61a5f6350\scratchpad`.

## Required changes

None.

## Optional changes

**Y1. The X4 operational step is stated only in §9, not in §2.** (`FACT`)
- §9's X4 row (`PHASE_1_M5_PREREGISTRATION.md:534`) says "operationally, the repository is kept on the device before OneDrive is exited".
- §2's OneDrive bullet (`:175–178`) does not contain this. A grep for "on this device", "online-only" or "kept on the device" finds only line 534.
- If this step were missed, the run would fail safe (`INFERENCE`): an unreadable file raises `OSError`, which is a refusal at start-up or an interruption during a trial, never a record.
- Suggest one sentence in §2: make sure the repository folder, tables included, is "always kept on this device" before exiting OneDrive.

**Y2. The provenance bullet is not extended to revision 7.** (`FACT`)
- `:32` now says "Revisions 4 to 7 were written after M4's scored battery finished".
- The sub-bullet at `:34–36` still lists only "every revision-6 change an item in review 5" and "None of these reviews used M4's results". It does not cover revision 7 and review 6.
- Suggest adding "every revision-7 change an item in review 6" and extending the statement to review 6. This review did not use M4's results either.

**Y3. No test covers the "refused: …" branch of `v3_not_run`.** (`FACT`)
- `run.py:248–258`. The existing `test_not_run_set_must_equal_the_rederived_one` (`tests/test_scored_m5.py:645`) passes a hand-written dict.
- I checked the branch by hand in a tree with no tables:
  - with `PAIR_CHECK` pointed at a missing file, the derived set gains `face_gap_mm=0.35__{6move,sexy6}` as "refused: 0.35 mm pair check … missing";
  - with no N52 V3 match, it gains "refused: 0 V3 records match 4x2 mm N52 scale 1 (exactly one required)".
- A short test would pin the §5 sentence "Refusals of the §4 rule are part of the re-derived set".

**Y4. A weak assertion in the end-to-end W1 test.** (`FACT`)
- `tests/test_scored_m5.py:756` asserts `"INVALID" not in out and "PASS" in out`. "NOT PASSED" also satisfies `"PASS" in out`.
- The INVALID half is the part that matters for W1. Asserting the exact verdict line would also pin PASS.

**Y5. What "committed files only" means.** (`INFERENCE`)
- `v3_rule` reads the `d8_1b_checks*.json` files in the working tree (`run.py:128–140`), not `git show <manifest commit>:…`.
- On a fresh clone these are the committed files. At the first start, the runner's clean-commit check covers them (the glob is a frozen path).
- The verdict script does not check that they are clean when it runs. A local edit to a V3 record at analysis time could therefore change the derived set.
- This is low risk and was not introduced by this commit. Optionally, §5 could say "as committed at the manifest commit (the analysis tree must be clean for these paths)".

## Checks that passed

**W1: the verdict script no longer depends on the tables.**
- `analyze.main` now calls `R.v3_not_run(registered)` (`analyze.py:386`). That calls `v3_rule` (`run.py:221–245`), which reads only the V3 records and `PAIR_CHECK`. Nothing in it reaches `M4.magnet_availability`.
- Every other table reference in `analyze.py` only builds a file name and compares SHA-256s with the manifest: `M4.table_path` at `analyze.py:225` computes a path; it does not open it.
- `build_m5_jobs` and `nominal_validated_tilt` read only committed files (`d8_1b_checks.json`).
- `git status --ignored` shows `experiments/D8_alignment/results/tables/` as the only ignored path there. All `d8_1b_checks*.json` files and the pair-check record are tracked.

**W1 in a real fresh tree.**
- I extracted `git archive acf570e` (no tables directory at all) and ran the W1, X3, X4 and resume tests there.
- These all pass:
  - `test_rederived_not_run_set_reads_no_tables`
  - `test_complete_valid_set_without_tables_is_not_invalid`
  - `test_verdict_script_main_never_reads_tables`
  - both X3 cases
  - X4
  - every resume and foreign-file test that does not need git
- As expected without `.git` or tables, these fail:
  - the four git-based resume tests, X2 included;
  - the 440 / 2 / 0 pin, because the runner refuses without tables.
- `v3_not_run` on the full list in that tree gives exactly `{('magnets','E1-7','magnet=4x1.5_N35__6move'): 'failed V3', ('magnets','E1-7','magnet=4x1.5_N35__sexy6'): 'failed V3'}`.

**W1 tests against revision-6 code.**
- I copied the revision-7 test file into an extraction of `74b30a3`. All six new W1, X3 and X4 tests fail there:
  - W1 tests 1 and 2 fail with `AttributeError` (`v3_not_run` does not exist);
  - W1 test 3 fails behaviourally ("the verdict script called the runner's availability check"), which is the real regression guard;
  - both X3 cases fail with "DID NOT RAISE SystemExit";
  - X4 fails because `errors` is not set.

**Runner behaviour unchanged.**
- I loaded the revision-6 runner (extraction, its `M4.TABLES` pointed at the real tables) next to the revision-7 runner, and classified all 442 jobs with each.
- `(status, message)` is identical for every job. Revision 7 gives `{'run': 440, 'not_run': 2}`, with 0 refused.
- `table_sha256`, `v3_source_sha256` and `validated_tilt_deg` in `magnet_info` are identical. `table_file` differs only because of my cross-tree path redirection.
- `v3_not_run` does not mutate the job dicts.

**Dry run.** `run.py all --dry-run` in the repository gives "440 runnable, 2 registered not run, 0 refused". The NOT RUN lines are the two 4×1.5 N35 E1-7 keys ("failed V3"). The tree is clean afterwards.

**Test suite.** `tests/test_scored_m5.py`: 78 tests, all pass (exit 0).

**X1.**
- `_no_real_start` (`tests/test_scored_m5.py:682`) replaces `R.execute` and `R.startup_check` with functions that raise, and points `R.OUT` and `R.OUT_NOMAG` at `tmp_path`.
- `main` looks up all four as module globals, so they are patched.
- If a guard regressed, any earlier `SystemExit` (unclean commit, E1-6c threshold) would fail the `match=`. No path reaches a real start.

**X2.**
- `base != head`, so `scored._git diff` really runs. In the fresh extraction without `.git` it raises `CalledProcessError`, which confirms git is called.
- The second half (frozen path = the revision-6 smoke folder added between `ccc6330` and `769eab2`) is refused. So the test would detect a broken or skipped diff.
- The results pathspec `experiments/E5_scored_m5/results` does not match `results_nomag` or the smoke folder.

**X3.**
- `records` (`run.py:447`) and the paths `iterdir` yields (`:462`) are both built as `dirs[arm] / <exp> / <tid>.json` from the same `dirs` object. PosixPath equality is component-wise, so relative or absolute `--smoke-dir` and `./` prefixes compare equal.
- E1-6n records are keyed `("no_magnets", exp, tid)` and are found under `dirs["no_magnets"]`. `test_resume_runs_only_missing_keys_including_e16n_twins_and_never_overwrites` passes with the new check.
- Records of the "not run" set and non-manifest `.json` files are refused. The verdict script would flag them as "record not in the manifest" (`analyze.py:188–189`), so the check is never stricter than the verdict script.
- A record plus its leftover `.json.tmp` (kill between link and unlink) is still accepted.

**X4.** `errors="replace"` keeps the ASCII image name intact. A missing `tasklist.exe` still raises `OSError`, which is a refusal.

**X5.**
- The docstring now mentions "INCOMPLETE (and NOT PASSED)", matching `analyze.py:265`.
- The report column is "orphans planned (moved)".
- The line continuation at `run.py:431–432` is restored.
- The §6.1 item 3 wording now refers to the parameters the stub receives.

**X6.**
- `resume_problems` (`run.py:416–439`) diffs the frozen paths, which include this pre-registration, and the results folders between the manifest commit and HEAD.
- So the Status-line commit must come before the first start, as §8 says. A later edit would make every resume refuse.
- `docs/DECISION_LOG.md` and review documents are not frozen paths, so recording them during the run is safe, provided no commit touches `experiments/E5_scored_m5/results*`. These folders are not git-ignored, so an automatic `git add -A`-style commit during the run would make every resume refuse. That outcome is fail-safe, and §9's X6 row covers it.

**Text.**
- §2 (`:204–207`), §5 (`:315–318`), §6.1 item 3 (`:413–417`), §8, §9's revision-7 table, the Status line and P-47 match the code, apart from Y1 and Y2.
- §5's claim that a manifest made despite a §4 refusal is INVALID holds: the refused key enters the derived set, the dicts differ, and `analyze.py:169–170` records a violation.
