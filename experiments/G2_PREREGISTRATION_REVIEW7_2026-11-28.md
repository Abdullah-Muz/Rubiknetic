# G2 pre-registration review 7 (2026-11-28; short round limited to the revision-7 changes)

VERDICT: ACCEPTABLE AS IS

*(Independent reviewer subagent, round 7 (P-121), limited by the user's choice to the changes of revision 7. The report
is saved as returned.)*

**Scope and what I ran** (read-only; no repository file changed; no scored seed simulated)
- `git diff 2ddea9b 3368783` over `experiments/E8_scored_g2`, `tests` and the pre-registration, plus `git diff 3368783 HEAD -- PHASE_2_G2_PREREGISTRATION.md` (the evidence commit `bf0b1c9`).
- `git diff --stat 2ddea9b HEAD` over all 26 `run.FROZEN_PATHS` entries, glob included.
- Read the evidence log, review 6 (S-a…S-g), DECISION_LOG P-120 and P-138, `E4_scored_m4/run.py:464-483`, and the pilot-4 `scene.ik` across all 138 pilot-4 records. Ran `git ls-files` with the glob pathspec.
- Ran `G2_REQUIRE_SCENE=1 ~/.venvs/rubiknetic/bin/python -m pytest -q -rs -p no:cacheprovider tests/test_scored_g2.py` in WSL.
  - Result: 63 dots, no `s`/`F`/`E`, and only 3 UserWarnings (two_arm.py:356, an empty spec prefix). So the 4 scene tests ran: 63 passed, 0 skipped.
  - My captured output lacked pytest's final summary line (tail/pipe artifact), so the count comes from the progress line.
  - `git status --porcelain` was empty afterwards.

**Review-6 items**

| Item | Status | Evidence |
|---|---|---|
| S-a joint margin | FIXED | Prereg §5 line 314. FACT: pilot-4 `scene.ik` has A `limit_margin_deg` 28.912 in all 138 records. B is 19.084 in 130 records, 21.20 in 6 and 22.93 in 2. The higher values are only P4-neg `two_layer_*` and `collision_*`, so 19.1° is B's minimum. Exact figures: `U_s29500.json:50,70`, `with_ft_sensor: true`. |
| S-b G1 attribution | FIXED | Prereg §4.1 lines 202-205. FACT: G1 rule 2 judges tilt only (`E4_scored_m4/run.py:476-483`); the text now credits `near_perpendicular` to the force law and calls it stricter than G1. |
| S-c self-check flag | FIXED | `selfcheck.py:66-69`. Checks `git status --porcelain -- *R.FROZEN_PATHS` with `cwd=R.REPO`, the same call as `run.require_clean_commit` (`run.py:564`). FACT: the glob pathspec matches the 6 tracked `d8_1b_checks*.json` files (`git ls-files`). It prints a flag and does not refuse, as the text says. |
| S-d verdict-run names | FIXED | `analyze.py:416-422`: `%Y%m%dT%H%M%S.%fZ`, mode `"x"`, both files named `VERDICT_<ts>`. Text in §6 line 395 and §14 matches. INFERENCE: a `FileExistsError` needs a same-microsecond repeat. It would come after the verdict is printed and only stop `VERDICT.md` being refreshed, so it cannot change a verdict. The log shows two runs with separate files. |
| S-e "0 skipped" | FIXED | `tests/test_scored_g2.py:38-47`. With the variable set and the model present, the 4 `@NEEDS_SCENE` tests run (my run). With the model absent: `skipif` is False, so the scene tests run and fail, and the new test fails on `assert ROBOT_XML.exists()`. Unset on a clean clone, they skip and the new test passes trivially. No other skip, xfail or importorskip in the file, and no conftest. |
| S-f coverage | FIXED | `tests/test_scored_g2.py:128`. Asserts a `src/rubiknetic/` path is among the repository-resolved modules. An installed copy (outside REPO or under site-packages) now fails. |
| S-g smoke wording | PARTIAL | Prereg §7 lines 429-431. "One uninterrupted start" is correct. The added justification is false; see N1. |

**New findings**

- **N1 (SUGGESTED, fix before the freeze): §7 lines 430-431 state something false.**
  - The text says "`run.py` has not changed since the P-120 kill-and-resume smoke".
  - FACT: P-120's smoke ran at `6d7777b` (recorded in `d58bf35`; `smoke_2_kill_resume/results/STARTS.txt` head `6d7777b`).
  - FACT: `run.py` has changed in 5 commits since (`eded7ef`, `63f2ae2`, `6e4a0de`, `bb58342`, `eb90291`), +225/−40 lines per `git diff --stat d58bf35 3368783`. The changes include resume logic: artifact SHAs checked on resume, the stray-temp-file refusal, `MAX_STARTS`, and `present` logged in STARTS.
  - Why only SUGGESTED: it is evidence wording, not a judged rule, and it cannot produce a false PASS.
  - FACT: the current resume path is covered by synthetic tests at the current code: `test_interrupt_then_resume_completes`, `test_resume_moves_orphans_and_reconciles`, `test_resume_refusals`, `test_resume_refuses_stray_temporary_files` and `test_resumes_are_limited_then_not_passed`.
  - Fix, either of:
    - Reword to "P-120's kill-and-resume smoke predates the later run.py changes; resume at the current code is covered by the synthetic resume tests".
    - Re-run a kill-and-resume smoke (`--stop-after … --stop-point after_link`) at the freeze commit.
- **N2 (SUGGESTED, minor): §7's self-check line does not name the commit it ran at.**
  - It reads "3/3 physics-identical, frozen paths clean (P-138)". The log shows HEAD `a377b23`, which differs from `3368783` only in D23, outside the frozen paths.
  - Earlier rounds named the code commit. Add "at `a377b23`, G2 code of `3368783`".
- **N3 (SUGGESTED, cosmetic): §5 could say "arm B ≥ 19.1°".**
  - 8 negative-case records have B at 21.2° and 22.9°. 19.1° is the minimum.

**Checked, no problem found**
- Frozen paths:
  - FACT: `git diff --stat 2ddea9b HEAD` over all FROZEN_PATHS shows only analyze.py, selfcheck.py, trials.py (docstring), the pre-registration and test_scored_g2.py.
  - The D22 and D23 commits touch no frozen path.
  - The evidence commit changes only §7 placeholders (now filled), DECISION_LOG and the log.
- Evidence log vs §7 and P-138: frozen paths clean, 63 passed, two verdict runs with distinct microsecond `VERDICT_*.md/.json` files, self-check 3/3 IDENTICAL. Magnets: 0 steps without force, `steps == sim_steps`, tilt 1.21–1.72°, `near_perpendicular` 0. All agree with the text.
  - INFERENCE: the older `VERDICT_…Z.md` / lowercase `verdict_…Z.json` in that listing are revision-6 leftovers and harmless.
  - The verdict-run directory is outside the repo, so I could not check those files directly.
- My independent pytest run reproduced 63 passed, 0 skipped with `G2_REQUIRE_SCENE=1`.
- §14 maps all 7 items. The header and P-7/P-6g rows are updated. No leftover "62 tests" or stale lowercase `verdict_<…>` naming in code, text or tests.
- No CI workflow sets `G2_REQUIRE_SCENE`, so CI still skips as intended.
