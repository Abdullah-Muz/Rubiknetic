# Independent review 6 (narrow): changes for revision 6 of PHASE_1_M5_PREREGISTRATION.md (2026-11-16)

**Reviewer:** independent reviewer (Claude agent), read-only. I created, edited or deleted no repository file and ran no git command that writes. `git status --porcelain` was empty before and after. My only scratch file is outside the repository: `C:\Users\abdul\AppData\Local\Temp\claude\b6672f8dce1e00f4\3140f1d7-6e9e-4f5a-9e6c-c7e61a5f6350\scratchpad\rev6_checks.py`.

**Read:**
- `git diff 44f9150 HEAD` for:
  - `experiments/PHASE_1_M5_PREREGISTRATION.md`
  - `experiments/E5_scored_m5/run.py`
  - `experiments/E5_scored_m5/analyze.py`
  - `tests/test_scored_m5.py`
  - `docs/DECISION_LOG.md` (P-44 and P-45 only)
- `experiments/M5_PREREGISTRATION_REVIEW5_2026-11-16.md`, in full.
- Current `run.py` lines 40–700 and current `analyze.py`, in full.
- `experiments/E4_scored_m4/run.py`: lines 74–102, 210–265 and 625–640.
- `src/rubiknetic/cube_physics/scored.py`: lines 49–75.
- `.gitignore`, searched for results, tables and temporary files.
- The rev-6 smoke test: `smoke_rev6_2026-11-16.log`, `STARTS.txt`, the file list, and the manifest's environment fields.

**Not read:**
- I did **not** read, list, grep or `git show` anything under `experiments/E4_scored_m4/results/`. My one recursive grep excluded `results` folders.
- I did not read DECISION_LOG P-37 or any session transcript.

**Ran:**
- `pytest tests/test_scored_m5.py`: **71 passed**.
- `run.py all --dry-run`: **440 runnable, 2 registered not run, 0 refused**. Seeds per experiment are as registered.
- `analyze.py --smoke-dir experiments/E5_scored_m5/smoke_rev6_2026-11-16`: 0 violations, 0 missing, 19 records, 3 starts.
- A scratch script, which does no stepping and no writes. It:
  - calls `resume_problems` on the real frozen paths and the real results paths;
  - calls the real `onedrive_running()`, and `tasklist.exe` with a filter that cannot match;
  - runs `R.prepare` as `analyze.main` does, once with the near-field tables present and once with `M4.TABLES` pointed at a folder that does not exist (only the in-memory value changed; nothing on disk was touched).

**No simulation was run on M5 seeds 10000–10999.** `prepare`/`classify`, the dry run and `resume_problems` do not step MuJoCo. I did not run `run.py smoke` or `run.py all` without `--dry-run`.

## Verdict: ACCEPTABLE WITH CHANGES

V1 is met. All twelve optional items are implemented, and the new run-procedure code is sound in every crash window I traced. One new defect matters: the re-derived "not run" check (O3) makes the verdict depend on git-ignored files present when the analysis runs. A correct run can therefore come out **INVALID**, which the text calls final, and the code does not do what §5 says.

## Required changes

**W1. The re-derived "not run" set depends on the git-ignored near-field tables, so a correct run can be declared INVALID.** (`FACT`)

- **What the text registers.** §5 (`PHASE_1_M5_PREREGISTRATION.md:308`) says the manifest's "not run" set must equal "the one re-derived **from the committed V3 records**".
- **What the code does.**
  - `analyze.main` re-derives the set with `R.prepare` (`analyze.py:383`).
  - `prepare` → `classify` → `M4.magnet_availability` (`E4 run.py:246–262`) needs every near-field table to exist on disk with the default grid.
  - It also puts every refused trial into the derived set as `"refused: …"` (`analyze.py:385`).
  - Any difference from the manifest is a violation (`analyze.py:169–170`), and any violation gives INVALID (`analyze.py:259–260`).
- **The tables are git-ignored** (`.gitignore:74`). Before revision 6 the analyzer did not read them; it compared table SHA-256s only against the manifest.
- **What I measured.**
  - With the tables present: 440 / 2 / 0, so the derived set equals the manifest's.
  - With the tables absent: 186 runnable, 2 not run, **254 refused**, giving a derived set of 256 keys against the manifest's 2. Example message: "near-field table … does not exist".
- **Consequence.** A correct, complete run gives INVALID whenever the verdict script runs without the tables. That covers:
  - a fresh clone;
  - an independent re-analysis;
  - any later clean-up or rebuild of `D8_alignment/results/tables/` on another grid.

  The violation message ("differs from the one re-derived from the V3 records") would also point at the wrong cause. On the run machine, right after the run, the risk is low. But the registered verdict then depends on local, untracked state, and the code diverges from the registered wording.
- **Fix (any of these):**
  - re-derive using the V3 rule only, without `magnet_availability`. For example, run `classify` with availability stubbed, or drop only refusals raised by `magnet_availability`. Keep refusals from the V3 matching rule, which do come from committed files.
  - or, if tables are missing at analysis time, stop with "cannot re-derive; restore the tables" and give no verdict, and say so in §5.

  Add a test: a complete, valid set analysed with the tables absent must not give INVALID.

## Optional changes

**X1. Two tests could start a real run if the check they cover regresses.** (`FACT`)
- `test_scored_start_refused_while_onedrive_runs` (`tests/test_scored_m5.py:689–692`) calls `R.main(["all"])` with only `onedrive_running` patched. If the check at `run.py:604` were removed or moved later, then on a clean tree this test would:
  - pass `require_m5_clean_commit`;
  - run the start-up check;
  - call `execute` on the real `OUT`/`OUT_NOMAG`.

  That is a scored first start on M5 seeds from the test suite, which would break P5 and use up the one first start.
- `test_smoke_dir_may_not_be_the_scored_folders` (`:683–686`) has the same exposure: it would write a smoke run into the scored folders.
- The code is correct today. Still, also patch `R.execute` and `R.startup_check` to raise, or point `R.OUT`/`R.OUT_NOMAG` at `tmp_path`, in both tests.

**X2. The "allowed" half of V1 never runs git.** (`FACT`)
- `test_resume_allowed_from_the_manifest_commit` (`:521–531`) uses head = manifest commit, so `run.py:403` skips the diff entirely. That is what review 5 asked for.
- The realistic resume is HEAD ≠ manifest commit with the frozen paths unchanged. No automated test covers it.
- I checked it by hand: manifest commit `ccc6330` against HEAD `769eab2`, with the real frozen paths and the real results paths, gives `[]`.
- Consider adding a test case with that pair.

**X3. §2 says more than `foreign_files` checks.** (`FACT`)
- `PHASE_1_M5_PREREGISTRATION.md:199` says a resume refuses if any file "would make the run INVALID (§5)". `foreign_files` (`run.py:414–434`) checks names only.
- It accepts any `*.json` in an experiment folder. That includes a OneDrive-style conflict copy `x-PC.json` or a key that is not in the manifest, which the analyzer would flag ("record not in the manifest").
- It is never stricter than the analyzer, so it cannot block a correct run. Either narrow the wording ("files of a kind the verdict script rejects") or also check that each `.json` stem is a manifest key.

**X4. The OneDrive check's failure modes.**
- **Checked here** (`FACT`):
  - `onedrive_running()` returned True while OneDrive runs.
  - `tasklist.exe` with a filter that cannot match returns rc 0 and prints "INFO: No tasks are running…", so an exited OneDrive gives False and the run is not blocked.
  - A missing `tasklist.exe` or broken WSL interop raises `OSError`, which is a refusal. This is fail-safe.
- **Not caught** (`INFERENCE`): a `UnicodeDecodeError` from a non-English tasklist message is not caught (`run.py:543–550`). It would crash, which is still fail-safe.
- **Operational** (`INFERENCE`, not verified): with OneDrive exited, any repository file that is an online-only placeholder cannot be read. Make sure the repository folder, the tables included, is "always kept on this device" before exiting OneDrive.

**X5. Wording leftovers.** (`FACT`)
- §6.1 item 3 (`:377`) still says "the cubie gap passed to `params_for`" right after the new `scored.Trial` stub wording.
- The `analyze.py:1–4` docstring does not mention "INCOMPLETE (and NOT PASSED)".
- After a kill between the start-log line and `apply_resume`, the STARTS line and the report column "orphans moved" (`analyze.py:303–305`) count *planned* moves. The text (`:202–204`) says this correctly, but the column could be called "orphans planned".
- `run.py:404` has a long run of spaces where a line continuation seems to have been lost. It is cosmetic and parses correctly.

**X6. Operational, not code.** (`FACT` from `run.py:399–411` and §2)
- The pre-registration file is a frozen path. The commit that records this review's outcome (the Status line) must therefore come **before** the first start. Otherwise every resume is refused.
- Any commit during the run, including an automatic one, must not touch `experiments/E5_scored_m5/results*`. The resume now enforces this.
- `git diff` compares trees, so a commit followed by its revert makes the resume pass again.

## Checks that passed

**V1** (`FACT`)
- `test_resume_refused_on_a_different_frozen_path_commit` (`tests/test_scored_m5.py:508–518`):
  - makes a first start with manifest commit `cdfc76e`, then resumes through `execute` with `check_git` at its default (True) and HEAD = HEAD;
  - it reaches the `git diff` at `run.py:404` and is refused with "frozen paths differ".
- The allowed case (`:521–531`) completes the resume (2 records).
- By hand:
  - `44f9150` → refused on `analyze.py`, `run.py` and the pre-registration;
  - `ffd6d93` → the same;
  - `ccc6330` → allowed.

**O1** (`FACT`)
- `onedrive_running` runs at every non-dry scored start, before the clean-commit check (`run.py:604–606`). The test is at `:689`.
- `foreign_files` runs on every resume (`run.py:493–494`) and is never stricter than `analyze.load` (`analyze.py:117–145`):
  - top-level files: same rule;
  - `_interrupted/`: needs logging only, while the analyzer also needs the SHA;
  - experiment folders: a subset of the analyzer's rejections.
- The test is at `:549`.

**O2** (`FACT`)
- **(a)** The temporary manifest sits at `results/../.results.MANIFEST.json.tmp` (`run.py:380`) and is opened `wb`.
  - A kill before the link leaves `results/` empty, so the first start can be repeated.
  - The path is outside the folders the analyzer reads, and it does not match any frozen path, so it cannot dirty the clean check.
  - The test is at `:593`.
- **(b)** Ordering: `plan_resume` changes nothing (`run.py:437–458`); the STARTS line is appended (`:500`); then `apply_resume` runs (`:502`).
  - A kill in between leaves the files in place, and the next start plans them again.
  - A kill part-way through `apply_resume` is also safe. After a link without its unlink, the source is re-planned under the next k, and the earlier copy is already logged. Ledger lines already reconciled are not planned again.
  - The analyzer only checks files that exist against logged entries, so stale planned entries cause no violation. The test is at `:556`.
- **(c)** Moved names are `k{start}__{exp}__{name}` (`run.py:450`), created with `os.link`, which never overwrites.
  - Names are unique: k is unique per start, and a trial has one temporary path per arm.
  - The test is at `:579`. The smoke test shows `k2__` and `k3__` files, both logged, with 0 violations.

**O3** (`FACT`)
- The table-file check (`analyze.py:222–227`) computes the same `_rel(table_path(magnet_params_for(overrides)))` that `run_trial` stores through `magnet_availability` (`E4 run.py:262`, `635`). It works on real records: the smoke folder gives 0 violations.
- Every new INVALID case listed in §5 (`:326–331`) has a test (`:610–649`).
- Only W1 is defective.

**O4** (`FACT`)
- `json.dumps(rec, default=list)` sits inside the worker's `try` (`run.py:287`), with the same `default` as `write_record`.
- The test is at `:674`.

**O5** (`FACT`): the text (`:226–227`) now matches the existing handling of `Refused` as an interruption.

**O6** (`FACT`)
- `present_fail` (`analyze.py:258–263`) matches the text (`:311–314`).
- Nothing reads the verdict string except `report()` and the tests, so the new word breaks nothing.
- Tests: `:288` (plain INCOMPLETE) and `:663–671` (both words).

**O7** (`FACT`)
- The results-folder diff is at `run.py:407–410`.
- `execute` derives `('experiments/E5_scored_m5/results', 'experiments/E5_scored_m5/results_nomag')` for the real folders. This was checked by hand.
- The pathspec does not match the committed `smoke_rev6…/results` folders: the diff `44f9150..HEAD` over those paths is empty.
- The guard for an empty path list (`run.py:404`) fixes the whole-tree diff. The test is at `:533`.

**O8** (`FACT`)
- The E1-6n wording and its reference `run.py:101` (`NOMAG_EXPS`) are correct.
- The `MagnetSystem` wording is fixed.
- The gap-test wording is fixed apart from X5.

**O9** (`FACT`)
- `ENV_COMPARED` includes scipy (`run.py:73`), and `environment()` adds it (`:561`).
- Records take `environment` from the job (`_metadata`), so the per-record comparison holds.
- The smoke manifest has `environment_compared` with scipy and `scipy = 1.18.1`.

**O10** (`FACT`): the disclosure is in §4, and its reference `run.py:89–90` (RULE2/RULE3 in M4's runner) is correct.

**O11** (`FACT`): the guard at `run.py:600–602` covers `HERE`, `OUT`, `OUT_NOMAG` and anything inside them. These are the only smoke folders that map onto a scored folder. The test is at `:683`.

**O12** (`FACT`): the test at `:695` passes, and the dry run agrees.

**Text against code** (`FACT`)
- §2, §4, §5, §6.1 and §9 match the code, apart from W1, X3 and X5.
- The reference `table_path, run.py:215–218` is correct.
- No criterion, threshold, factor value or seed changed. The seed ranges in the dry run are unchanged from review 5.

**Smoke test** (`FACT`)
- It was run at `ccc6330`. `run.py`, `analyze.py`, the tests and the pre-registration are unchanged from `ccc6330` to HEAD.
- Smoke seeds are 11000–11007 and 11051 onwards, outside 10000–10999 (P5).
- The smoke test covered an after-link kill, which gave an orphan plus a reconciled ledger line, and an after-temporary-file kill.
