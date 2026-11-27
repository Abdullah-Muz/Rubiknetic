# G2 pre-registration review 2 (2026-11-27)

VERDICT: REQUIRES CHANGES

*(Independent reviewer subagent, round 2 (P-121). It was given the pre-registration, the code and review 1, not the
assistant's conclusions. The report is saved as returned.)*

Scope: revision 2 (amended P-125) at HEAD `14a5072`, checked against `E8_scored_g2/{run,trials,analyze,selfcheck}.py`, `D18/{two_arm,layout}.py`, `D17/{hold,turn}.py`, `tests/test_scored_g2.py`, the pilot, pilot-2 and smoke records, and DECISION_LOG P-115 to P-125. I changed no files. What I ran:
- the unit tests: **33 passed**;
- a synthetic runner (in a temporary folder) against `run.execute` and `analyze.verdict`;
- one full pilot-seed trial (seed 29001, "U") under a Python audit hook, to record every file it opened;
- one model build to list equalities and actuators;
- a sensitivity check of `test_roll_commands_ignore_cube_state`;
- statistics from the committed pilot records;
- `analyze.verdict` on `pilot2_rev2`.

No scored trial was simulated. I did call `start_draw()` on scored seeds. It returns start parameters fixed by the design, not outcomes.

## Review 1 required items

| # | Status | Evidence |
|---|---|---|
| 1 Roll sign from cube state | **FIXED in code; the test cannot detect a regression** | `two_arm.py:395` takes `roll_sign` from the nominal `RBt`, and `:692-693` only logs the measured sign. In every pilot-2 move the measured sign equals the sign used (−1). The test is weak (new finding 3). |
| 2 Unjudged phases | **FIXED** | Each move window opens at `:678` (`new_acc`) and is snapshotted after the roll-back (`:750`). The roll-back is judged (`:816`; `analyze.py:80`). The start sequence is monitored through `self.step` (`:433`, `:449-463`) and judged (`trials.py:120`, `analyze.py:99`). The approach is judged (`trials.py:121`, `analyze.py:100`). Trial-level slip, rotation and residual are judged (`two_arm.py:827-831`; `trials.py:102-113`; `analyze.py:108-117`). Remaining gap: new finding 6. |
| 3 Negative rules | **FIXED** | Integrity failures fail every negative case (`trials.py:212-213`, `analyze.py:139`). `offcentre` is reported only (`trials.py:43`, `run.py:95-96`), giving 128 scored trials (`test:55`). |
| 4 Integrity gaps | **PARTLY** | (a) orphans in subfolders, (b) duplicate or missing ledger keys, (c) list, frozen paths and metadata, (d) unknown directories: all now INVALID, confirmed by the tests and by my synthetic runner. But root-level `*.json.tmp` files and unlogged `*.json.tmp` files in `_interrupted/` still give **PASS** and are accepted on resume (new finding 4). |
| 5 Frozen coverage and artifacts | **FIXED** | Under the audit hook, the full U trial loaded no repository module outside `FROZEN_PATHS`. It opened no data file that is neither frozen nor in `artifacts()`. The files it read were the robot XML, the calibration, 31 meshes, the magnet table and 6 V3 records. |
| 6 In-process trials | **FIXED** | Real trials always use the spawn pool with `max_tasks_per_child=1` (`run.py:400-409`). `DEFAULTS` are fixed (`trials.py:30`, `:63`). `--jobs` defaults to 8 (`run.py:466`). |
| 7 Text vs code | **FIXED, with stale leftovers in frozen files** | Every item listed in review 1 is addressed. Stale defaults and docstrings remain (new finding 9). |

Suggestion 12 (shared F/T noise) is **adequately disclosed** (§0.5, §8 item 4). σ = 0.01 N·m is about 33σ below the gap between 1.0 and 0.674 N·m, so the noise cannot drive a false stop. Optionally add that, because every trial uses the same noise draws at the same sample indices, the Clopper–Pearson bound says nothing about variability from sensor noise.

## New findings

### 1. REQUIRED: the scored U′ first turns start beyond any piloted misalignment, where F/T torque rises steeply. False F/T stops are likely.
- The U′ first-turn F/T peak correlates strongly with the U-face start misalignment: r = −0.82 over 21 pilot turns.
- The pilot points at the most negative misalignment are:

  | U misalignment | F/T peak |
  |---|---|
  | −0.53° | 0.36 N·m |
  | −0.57° | 0.28 N·m |
  | −0.59° | 0.46 N·m |
  | −0.68° | 0.47 N·m |
  | −0.69° | 0.51 N·m |
  | **−0.78°** | **0.674 N·m (the pilot maximum)** |

- No pilot U′ first turn started below −0.78°.
- `start_draw` for the registered scored jobs puts three U′-first trials at U = **−0.88°, −0.94° and −0.97°**. Five U2-first trials and four U-first trials also fall below −0.78°.
- The local slope from −0.69° to −0.78° is about 1.8 N·m/deg. Continued to −0.97°, it gives about 1.0 N·m, which is the stop level. (`INFERENCE`: a two-point extrapolation, but the tail is steep and has never been sampled.)
- U2 has a similar outlier: 0.488 N·m at −0.84°.
- §0.3 estimates the tail "from about 75 first turns" without looking at this covariate. A single false stop fails the run at zero tolerance (32 U′ first moves are scored).
- Fix:
  - Before the freeze, pilot about 10 U′ and about 10 U2 first turns with the stop disabled. Use pilot seeds selected for, or an override forcing, U misalignment in [−1.0°, −0.8°]. Also cover the matching positive extreme.
  - Then set the stop with a stated margin over that worst case, and re-check the jam window and slip at the new stop (at 1.0 N·m, P-5 jams stopped at 40.8–44.3° with slip ≤ 0.27 mm).
  - Alternatively, narrow the start draw and disclose the change.

### 2. REQUIRED: the P-125 limits were never exercised where they matter (two_layer at 1.0 N·m; 10-move sequences under the revision-2 measures).
- **two_layer:**
  - All four pilot two_layer detections came from an F/T stop. P-5 stopped at 0.66 and 0.70 N·m (`INFERENCE`: at the then-current 0.6 stop). Pilot 2 stopped at 0.91 and 0.92 N·m (0.8 stop), after 1.8–3.4° of roll.
  - At 1.0 N·m, the 0.91–0.92 N·m readings would not trigger the stop. Whether a turn error, drift or oracle failure would detect it instead is untested.
  - Every pilot-2 negative record ran before P-125.
- **End misalignment ≤ 4°:**
  - The §4.1 derivation (√3·1° + 2°) covers one move only.
  - Turn errors carry a positive bias, so they accumulate. My estimate from the cumulative signed turn error is 1.1–2.6° over the P-5 10-move sequences and 1.7–1.9° over the pilot-2 5-move sequences. Pilot-2 5-move sequences ended at up to 2.07°.
  - No 10-move sequence has ever been run with `residual_end_deg` or the trial-level totals. The scored run has 20 of them, the longest trials (the 2 mm / 2° totals are likewise unpiloted beyond 5 moves; pilot-2 totals ≤ 0.27 mm / 0.87°).
- Fix:
  - Run a short confirmation pilot on pilot seeds at exactly the frozen configuration: at least 4 two_layer, 2 jam, and at least 8 10-move random sequences.
  - Rewrite the 4° justification to account for accumulation, or show from that pilot that the margin holds.

### 3. REQUIRED: `test_roll_commands_ignore_cube_state` cannot detect review 1 item 1.
- I re-introduced the old bug: a `TwoArm` subclass whose `roll_sign` is computed from `d.xmat[core]`. **The test's assertion still passes** (`first == second`).
- Two reasons:
  - the 0.05 perturbation cannot flip the sign;
  - with `step` stubbed, J7 never moves. The stall rule (`two_arm.py:722-729`) freezes the roll after about 45 steps, so most of the "whole move" roll commands are never exercised.
- §2 cites this test as evidence.
- Fix:
  - Perturb the core orientation by a large rotation (for example 180° about world z) in the scrambled run.
  - Make the stubbed step track the command (set `d.qpos[q7] = r.j7[0]`) so the full roll runs.
  - Add a positive control: the cube-reading subclass must fail.

### 4. REQUIRED (text vs code): some orphan temporary files are not INVALID.
- §4.4 says any file the procedure does not produce, "including any orphan temporary file", makes the run INVALID. The code disagrees:
  - `analyze.py:204-207` drops every `foreign_files` entry ending in `.json.tmp`, and only globs `*/.*.json.tmp`;
  - `run.py:372-373` and `plan_resume` (`run.py:332`) behave the same way.
- Synthetic results:
  - `results/.x.json.tmp` → **PASS**, resume accepted;
  - `results/foo.json.tmp` → **PASS**, resume accepted;
  - an unlogged `_interrupted/k9__G2-2__.U_s30100.json.tmp` → **PASS**, resume accepted.
- Fix: treat as INVALID (and refuse on resume) any `.json.tmp` that is not `<exp>/.<tid>.json.tmp` for a manifest key. Or narrow the text.

### 5. SUGGESTED: the verdict does not check that it runs the frozen code, or that `STARTS.txt` is consistent.
- `analyze.integrity` never compares HEAD or the working tree with `manifest["commit"]` on `FROZEN_PATHS`. A modified `analyze.py` could report PASS. Fix: refuse, or report INVALID, unless `git diff <manifest commit> HEAD -- FROZEN_PATHS` is empty and those paths are clean.
- Synthetic results:
  - emptying `STARTS.txt` → PASS;
  - deleting a record together with its ledger line → INCOMPLETE, and the resume re-runs it unnoticed.
- Fix:
  - hash-chain the ledger, or log in `STARTS.txt` the set of records present at each start;
  - cross-check that each ledger line's `start` is at most the number of starts, and that reconciled lines and orphan moves match the plans in `STARTS.txt`.

### 6. SUGGESTED: arm A's stabilisation before t0 is not judged.
- `grasp_shift_mm`, `stand_drop_shift_mm` and `core_offset_from_nominal_mm` are recorded (`two_arm.py:465-470`) but not judged.
- All slip limits are measured from t0, so a cube that slips in arm A's grip while the stand drops is invisible to every judged check.
- Pilot values: drop shift 0.06–0.09 mm; offset from nominal 0.8–1.14 mm.
- Fix: add, for example, `stand_drop_shift_mm` ≤ 1 mm and an offset from nominal at t0 ≤ 3 mm, to both `trials.py` and `analyze.py`.

### 7. SUGGESTED: causality is decided at grasp time with a 3-step minimum margin, and the remaining part of review 1 suggestion 8 is not disclosed.
- `t_force` and `t_motion` are latched in the settle/grasp phase (`two_arm.py:620-626`).
- Over 140 normal pilot moves, the gap from force onset to motion onset was 3 steps (1.5 ms) five times and ≤ 5 steps 16 times; the median is 19 steps. The scored run has 360 turn moves.
- §9 row S8 and P-123 ("suggestions 8–11 … implemented") omit that review 1's "time the onset from the roll start" was not adopted.
- Fix: disclose this. Or define the failure as layer motion before any fingertip–cubie contact force, or time the check from the roll start (the drive check already covers the roll).

### 8. SUGGESTED: the model audit is narrower than "no actuator or equality acting on a cube body".
- `model_audit` (`two_arm.py:132-146`) checks only joint-transmission actuators.
- It ignores tendon, site and body transmissions, and `body_gravcomp` on cube bodies.
- It assumes equalities are body-based. In the built model all four CONNECT equalities have objtype body and all are on robot bodies, so the current result (0 / 0, 27 cube bodies) is valid.
- Generalise it, or state its scope in §4.1.

### 9. SUGGESTED: stale text in frozen files (fix before the freeze).
- `two_arm.py`:
  - `:92` has the module default `FT_STOP = 0.6`, and `:863` the CLI `--ft-stop` default 0.6 (configure overrides both);
  - `:22` says the residual is judged "relative to t0" (it is now absolute);
  - `:55` has unused `ROLL_KP/KV/TAU`.
- `run.py:5-6` and `:11-12`: the docstring omits artifacts from the manifest and from the resume checks.
- `trials.py:4-5` omits P-125.

### 10. SUGGESTED: disclosures and procedure.
- §7 / `pilot2_rev2`:
  - state that the stored pass/fail values used the pre-P-125 rules (stop 0.8 N·m, the growth rule);
  - `analyze.py --mode pilot2` now returns **INVALID**, with 11 "stored pass False != recomputed True" (verified);
  - add a README to `pilot2_rev2/`.
- §4.3: the 20–50° jam window rests on three P-5 trials at 1.0 N·m. They ran on pre-revision-2 code; the self-check shows the physics is identical.
- §4.2: hold slip and rotation are sampled every 0.1 s, not every step (`trials.py:162-168`). State this.
- Freeze procedure: only the status line may change, so the frozen §7 table will still show P-7 and P-8 as "open". Allow the freeze commit to update that table too, or say so.
- `test_limits_agree_between_trials_and_analyze` does not compare `analyze.LIMITS["pen_mm"]` with `TA.T["penetration_mm"]`, which `ok_penetration_cubie` uses. Both are 0.5 now.

### Checked with no problem found
- Every criterion, limit, seed range, count and step that I did not raise above matches between the text and the code. That includes the 138 / 128 trials, 100 turn trials, all seed ranges, the start draw, the random-sequence seed, the procedure timings, the controller gains, J7 budget, F/T and stall rules, and the G2-6 overrides.
- No controller path (`impedance`, `j7_control`, `approach`, `ramp_grip`, the roll command, the F/T and stall guards) reads cube state; the guards read only the F/T sample and J7's angle. `test_controllers_ignore_cube_state` is sound, with a positive control.
- The drive sign convention is consistent: the impulse is > 0 in all 60 measured normal moves (min 0.012 N·m·s), and a reversed drive would fail. The roll-back check is not vacuous (max 0.043°).
- The self-check (3/3 physics-identical) does not exercise the scored `FT_STOP`. Its pilot jobs override the stop. This is acceptable for a physics-identity check.
- A tracked-file search found no record using seeds 30000–30999.
