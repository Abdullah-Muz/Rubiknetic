# G2 pre-registration review 6 (2026-11-28)

VERDICT: ACCEPTABLE AS IS

*(Independent reviewer subagent, round 6 (P-121). It was given the pre-registration, the code, the evidence and
reviews 1–5, not the assistant's conclusions. During the review the main session passed it one fact for
classification: the stale joint margin in §5, found by the D22 study; it is item S-a. The report is saved as
returned.)*

## Scope and what I ran
- I reviewed `experiments/PHASE_2_G2_PREREGISTRATION.md` (revision 6) against the code at `662d9fa` and the evidence commit `2ddea9b`. HEAD has since moved to `5a4c5d0` (D22, G4 docs). No G2 code, test, CI or pre-registration file differs between `2ddea9b` and `5a4c5d0` (FACT, `git diff --stat`).
- Diffs read: revision 6 (`662d9fa`) for `trials.py`, `analyze.py`, `selfcheck.py`, `two_arm.py`, `tests/test_scored_g2.py`, `ci.yml` and the pilot-4 README; the evidence commit `2ddea9b`.
- Code read: `MagnetSystem` stats code (`src/rubiknetic/cube_physics/magnets.py:394-473, 589-702`), `TwoArm.__init__` / `ctrl_step` / `step` / `move` / `run` (`two_arm.py:393-914`), `run.py` (frozen paths, `artifacts`, `foreign_files`, `main`), G1's rule-2 code (`E4_scored_m4/run.py:464-488`).
- Ran (WSL venv, read-only, `-B`, no cache): `pytest -q -rs tests/test_scored_g2.py` gave **62 passed, 0 skipped, exit 0** (FACT).
- Three probes on pilot seeds (no scored seeds), from a scratch script outside the repository:

| Probe | Result | steps = sim_steps = round(t/dt) | Largest tilt | Perpendicular pairs | Label |
|---|---|---|---|---|---|
| neg open_midturn s29901 | detected | 20817 | 1.50° | 0 | false |
| neg collision s29902 | detected | 18837 | 1.52° | 0 | false |
| seq U′ s29903 | pass | 20817 | 1.34° | 0 | – |

- The open_midturn probe left a cubie 32.5° off, and the tilt was still 1.5°.
- CI status (`gh run list`): `662d9fa` success; `4b64f0c` and earlier failure (FACT).

## Review-5 items and the CI change
| Item | Status | Evidence |
|---|---|---|
| S1 magnet-validity rule | FIXED | `two_arm.py:602-610` records tilt, perpendicular pairs and z clamps from `ms.stats`. That dict is never reset during a trial, so it covers the whole trial including the start sequence (FACT: no `reset_stats` call in D16, D17, D18). Judged for seq trials at `trials.py:165` and `analyze.py:125`, and for holds at `trials.py:230` and `analyze.py:152`. Negative cases are labelled only (`trials.py:299`); `neg_outcome` and `recompute_neg` use integrity only. Tilt limit 5.0 = `M4.nominal_validated_tilt()` (tested); M7 uses the nominal 4×2 N35 magnets. Tilt and the perpendicular check together cover every pair within r2, because tilt counts pairs with \|cos\| > cos 45° and the perpendicular check counts the rest. No bypass found: a NaN cannot enter the running max, and a missing or None value fails in both files. |
| S2 jam headroom | FIXED | Prereg §0.4 and §8 item 8. |
| S3 §4.3 text | FIXED | Prereg line 264. |
| S4 step count | FIXED | `trials.py:116-120`, `analyze.py:52-57`. All stepping goes through `ctrl_step` → `sim.step(1)` (`two_arm.py:597` is the only call), so the equality holds by construction (FACT). It held in every smoke record, self-check record and probe, including the jam and collision negatives and the 5 s hold. Aborted holds and seq trials fail through `aborted` anyway. |
| S5 self-check prints HEAD | FIXED (see S-c below) | `selfcheck.py:64-67`. |
| S6 verdict runs kept | FIXED (see S-d below) | `analyze.py:414-422`. |
| CI | FIXED | Skip marker at `tests/test_scored_g2.py:37` on 4 tests (lines 142, 396, 653, 685). Fresh-process coverage test at lines 101-119. CI green at `662d9fa`. |

## New findings (none REQUIRED)

**S-a. SUGGESTED: §5 states a stale joint margin.**
- Prereg line 311 cites "layout IK (P-108, ≥ 25.8° joint margin)". The coordinator's figure checks out (FACT): `pilot4_magnets/results/P4-U/U_s29500.json` gives `scene.ik.B.limit_margin_deg` 19.08° and A 28.91°, with the wrist F/T sensor (P-114) as in the scored configuration.
- Classification: an evidence citation in the §5 mapping table, not a judged rule (`limit_margin_deg` is reported only, `layout.py:138-140`). It cannot change a verdict.
- Fix: replace it with "arm B 19.1°, arm A 28.9° at the grasp IK with the F/T sensor (pilot-4 `scene.ik`)".

**S-b. SUGGESTED: the perpendicular-pair check is attributed to G1, but G1 did not judge it.**
- Prereg line 200 says "(review 5 S1; G1's M4 rule 2) … tilt ≤ 5° … and no near perpendicular pair". G1's rule 2 judges tilt only (`E4_scored_m4/run.py:476-483`, FACT).
- The `near_perpendicular` = 0 requirement comes from the force law's docstring (`magnets.py:26`). It is a zero-tolerance count, so G2 is stricter than G1 here.
- False NOT PASSED risk: low (INFERENCE; 0 in every one of about 17 probes and smoke/self-check records, including a 32° misaligned open_midturn).
- Fix: say "tilt as G1's rule 2; plus near_perpendicular = 0, the force law's stated precondition, which G1 did not judge".

**S-c. SUGGESTED: the self-check's "uncommitted changes" flag is repo-wide.**
- `selfcheck.py:66` runs `git status --porcelain` with no path filter. Any untracked side-work folder therefore sets the flag, as the evidence log shows (D21/D22/D23 folders). The S5 signal becomes noise.
- Fix: limit it to `R.FROZEN_PATHS`, as `run.require_clean_commit` does.

**S-d. SUGGESTED: verdict-run file naming and overwrite.**
- `analyze.py:416` uses one-second timestamps. Two verdict runs in the same second overwrite each other, against "never overwriting one" (prereg line 392).
- The JSON is written as `verdict_<ts>.json` (lowercase), while the text says `VERDICT_<UTC time>…json` (lines 392, 543).
- Fix: open with mode `"x"` or add microseconds, and align the name in the text.
- No interaction with the INVALID foreign-file rules (FACT): `foreign_files` and the orphan-tmp scan cover only `results/`, `verdict_runs/` sits in its parent, and no frozen path is a directory containing it. `code_problems`' `git status -- frozen_paths` does not see it.

**S-e. SUGGESTED: "0 skipped" is stated, not enforced.**
- No mechanism turns a skip into a failure, and the evidence log shows the progress dots but not the pytest summary line.
- Mitigation (FACT): `run.artifacts()` reads the same robot XML, so the scored run cannot start on a machine where these tests would skip. A skip can only hide a failure if the freeze evidence comes from a different machine.
- Fix: an environment variable (e.g. `G2_REQUIRE_SCENE=1`) that makes `NEEDS_SCENE` fail instead of skip, used for the freeze run; and record the `-rs` summary line.

**S-f. SUGGESTED (minor): the fresh-process coverage test does not check that `src/rubiknetic` files are covered.**
- It asserts only `two_arm.py` is present. If `rubiknetic` were installed non-editable, its files would fall outside REPO and be silently skipped.
- Locally it resolves to `/mnt/c/dev/Rubiknetic/src` (FACT), and `run.location_problems` guards the scored run.
- Fix: also assert one `src/rubiknetic/` path appears.

**S-g. SUGGESTED (minor): the §7 smoke line does not say how the revision-6 smoke ran.**
- The revision-6 smoke was a single uninterrupted start ("orphans moved 0; ledger lines reconciled 0"). §7's general sentence still describes a killed-and-resumed smoke.
- `run.py` did not change in revision 6, so the P-120 interruption evidence still applies (INFERENCE).
- Fix: say it was one uninterrupted start.

## Checked with no problem found
- `trials` and `analyze` apply the same magnet-integrity and validity logic. Holds take their magnets block and `sim_time_s` from the top level (`trials.py:207-212`). `analyze` looks in `trial` first, then the top level.
- `recompute_hold` judges validity but returns early on integrity failures, matching `run_hold`.
- Float `d.time` accumulation cannot shift `round(t/dt)` over about 1.3e5 steps (INFERENCE). Equality was observed in every record.
- `force_evaluations` = steps + 3, from the setup `mj_forward` calls (`two_arm.py:467, 472`). These are also included in the stats; that is harmless and conservative.
- `selfcheck.physics()` compares only the pilot-4 magnet keys, so the new fields do not break identity.
- G2 code is identical between `662d9fa` and `036bd5f`, where the smoke run and self-check ran (FACT, empty diff over every frozen path).
- The pilot-4 README discloses that re-analysis at revision 6 reports INVALID. The revision-5 verdict is kept.
- CI: the venv outside the checkout; the G2 file runs in its own process (`if: success() || failure()`). `test_counts` is deselected only on CI and disclosed.
- §0.1a cites D20 (P-133) correctly. The §13 mapping matches the code. P-136 matches the commits.
- Seed safety: no scored seeds were used.
