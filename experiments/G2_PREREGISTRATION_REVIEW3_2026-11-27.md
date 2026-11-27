# G2 pre-registration review 3 (2026-11-27)

VERDICT: REQUIRES CHANGES

*(Independent reviewer subagent, round 3 (P-121). It was given the pre-registration, the code and reviews 1–2, not
the assistant's conclusions. The report is saved as returned.)*

Scope: revision 3 at HEAD `14e6ac0`. I checked it against `E8_scored_g2/{run,trials,analyze,selfcheck,rerun_crashed}.py`, `D18/{two_arm,layout}.py`, `D17/{hold,turn}.py`, `tests/test_scored_g2.py`, the P5, pilot-2 and pilot-3 records and READMEs, the self-check log, and DECISION_LOG P-115 to P-127.

What I ran (no files changed, nothing committed):
- the unit tests: **41 passed**;
- the model build and start sequence once (seed 29001) under a Python `open` audit hook;
- error-message checks for empty input files against `run.is_load_error`;
- a positive control for `model_audit` on a synthetic model;
- statistics from the committed pilot records;
- `start_draw` on scored seeds. It gives the design's start parameters, not outcomes.

No scored trial was simulated.

## Review 2 required items

| # | Status | Evidence |
|---|---|---|
| 1 U′ torque at untested misalignment | **FIXED** | Pilot 3: 34 forced-extreme first turns, max 0.47 N·m. A linear fit of the first-turn F/T peak on the 9 start-draw variables (n = 38–46 per move, R² 0.76–0.86, residual sd ≈ 0.05) predicts a scored maximum of 0.48 N·m for U′ (Up_s30136), 0.64 at +3 sd. The 1.0 N·m stop has margin (`INFERENCE`). |
| 2 Limits unexercised | **FIXED** | Records confirm: two_layer 4/4 detected by an F/T stop at 1.05–1.11 N·m after 3.7–4.0° of roll (the torque is still rising at the stop); jam stops at 38.0° and 40.8°, slip ≤ 0.19 mm; 8/8 10-move sequences pass, end misalignment 2.00–2.83°, total ≤ 0.38 mm / 1.24°. |
| 3 Weak roll-command test | **FIXED** (one residual gap, finding 3) | `test_scored_g2.py:516-577`: the cube is turned 180° about world z, J7 follows its command (the roll exceeds 1.5 rad), and the positive control `buggy_move` gives different commands. The test passes. |
| 4 Stray temporary files | **FIXED** | `run.py:365-390` (`is_inflight_tmp`, `foreign_files`), `run.py:435-436`, `analyze.py:266-269`. Tests cover a root `.x.json.tmp`, `foo.json.tmp`, an unknown tid and an unlogged `_interrupted/` file. |

Review 2 suggestions 5–10 are implemented as §10 claims:
- S5: `analyze.code_problems` and `starts_problems`; `present` logged at `run.py:443-444`.
- S6: `trials.py:106-115`, `analyze.py:54-60`.
- S7: the causality note is disclosed (its numbers are now stale, finding 4).
- S8: `two_arm.py:132-190`. My synthetic model with a joint, tendon and site actuator, connect/joint/tendon equalities, two tendons and gravcomp on a cube body flagged all of them; a robot-only weld was not flagged.
- S9: `FT_STOP` 1.0 at `two_arm.py:92` and in the CLI default at `:907`.
- S10: pilot-2 README, hold sampling, jam basis, freeze scope, and the penetration check in the agreement test (`test:78`).

Leftover stale docstrings (no effect on behaviour): `trials.py:1`, `analyze.py:1` and the test file docstring still say "revision 2".

## New findings

### 1. REQUIRED: the load-error retry matches on message text, and common empty-file errors do not match. A transient read fault can still produce a failing record, so a false NOT PASSED is plausible.
- `run.py:199-205` retries only exceptions whose text contains `stl_decoder`, `is empty`, `error opening file`, `could not open`, `no such file` or `no passing v3 record` (plus `Refused`). Every other exception becomes a harness-exception record (`run.py:231`), which fails the trial.
- Quick check (MuJoCo 4.0.1, NumPy 2.5.4). With an empty file:
  - robot XML via `MjSpec.from_file` (read 4 times per trial in `hold.robot_spec`) gives `ValueError: "ParseXML: empty file …"`. Not matched ("empty file" is not "is empty").
  - gripper calibration (`layout.calib`) gives `JSONDecodeError`. Not matched.
  - magnet table (`np.load`) gives `EOFError: No data left in file`. Not matched.
  - a V3 record (`E4 run.py:236`) gives `JSONDecodeError`. Not matched.
- Evidence of the fault rate:
  - 3 transient empty-read incidents in about 200 pilot and tuning trials;
  - 2/48 in pilot 3 under 8 workers;
  - one of the three (P-115) hit a non-mesh file.
- A trial reads roughly 12 non-mesh files and some tens to about 120 mesh files. `INFERENCE`: about 2–6 transient faults are expected in 138 trials, and roughly 10–20 % of them would land on an unmatched file. The chance of at least one false failure from this alone is roughly 15–50 %, under zero tolerance.
- The text (§6, lines 302-306) says these errors "can only happen while the model is built, before any simulation step". The code does not check this; it only matches message text. (Retrying a trial that had already stepped cannot turn a failure into a pass, because trials are deterministic. But the rule should be enforced, not assumed.)
- Fix:
  - Classify by phase, not by message. Treat any non-interruption exception raised before the first `AuditedSim` step as a load error: retry, then interrupt. For example, set a flag in `TwoArm.ctrl_step`, or check `r.d.time == 0`, or wrap `build`/`TwoArm.__init__` up to the first `self.step` in a `LoadError` wrapper. Any exception after the first step stays a failing record.
  - Add tests for each of the empty-file messages above.
  - Optional: remove the cause by running from a clone on the WSL native filesystem at the frozen commit.

### 2. REQUIRED (text vs code): a trial executes an unfrozen repository module, and the coverage test cannot see it.
- `experiments/E4_scored_m4/run.py:61-68` runs `experiments/E1_scored/run.py` at import, through `spec_from_file_location`/`exec_module`. It is not registered in `sys.modules`.
- `E1_scored/run.py` is not in `run.FROZEN_PATHS` (`run.py:50-64`).
- `test_frozen_paths_cover_every_loaded_module` (`test:86-96`) scans only `sys.modules`, so it passes.
- My audit hook over import plus build plus start sequence listed exactly one opened repository file that is neither frozen nor an artifact: `experiments/E1_scored/run.py`. `T.TA.H.M4.E1.__file__` points to it, and `'e1_scored_run' in sys.modules` is False.
- Practical impact today is low: the file is unchanged since the Phase-1 freeze (`cfbc5c6`), and at import it only defines lists and imports `scored` without changing it. But §6 line 320 ("checks that every repository module a trial loads is frozen") is false, and neither `code_problems` nor the resume check would see an edit to this code.
- Fix:
  - add `experiments/E1_scored/run.py` to `FROZEN_PATHS`;
  - make the test record file opens with `sys.addaudithook` (`open` events, mapping `__pycache__/*.pyc` back to `.py`) while it imports `trials` and builds a model, or also walk `M4.E1`-style module attributes.

### 3. SUGGESTED: remaining gaps in the controller-input tests.
- `reset()` in `test_roll_commands_ignore_cube_state` (`test:542`) recomputes `r.roll_sign` from `r.a_d` on every reset. A regression that derived `roll_sign` from cube state in `TwoArm.__init__` would be overwritten and missed.
  - Fix: save `r.roll_sign` right after construction, restore that value, and assert it equals `sign([1,0,0] @ RBt[:,2])`.
- The move-level test stubs `step`, so it proves only that the commands issued inside `move()` ignore the cube pose. Impedance outputs are covered by the single-state test. This is adequate, but the §2 wording "with the cube state scrambled" (lines 85-86) overstates it. Say "with the cube turned 180° about world z, physics stubbed".
- No unit test exercises `model_audit` on a model with a forbidden element; the tests use synthetic audit dicts only. My synthetic positive control (above) passes. Add it as a test.

### 4. SUGGESTED: some evidence statements in the text are stale or wrong; correct them before the freeze.
- **§4.1 lines 166-167** ("the pilots saw 0.06–0.09 mm and 0.8–1.14 mm"). Across 161 non-offcentre pilot records:
  - stand-drop shift ≤ 0.12 mm;
  - **t0 offset up to 2.08 mm** (pilot3 `U2_m1.00_4_s29419`; P5 `U_s29203` 1.96). The margin to 3 mm is 1.44×.
- **§4.1 note, line 199** ("over 140 pilot moves … at least 3 steps"). Over 254 moves the minimum force-to-motion gap is **2 steps (1.0 ms)**, twice, both in pilot-3 re-run `rand10_s29448`. Counts: 2 steps 2, 3 steps 13, 4 steps 16, 5 steps 8. Update the numbers.
- **§8 item 8** ("the pilot values are 5–10× below the limits"). True for the slips. Not true for:
  - turn error, pilot max **1.75° vs 2°** (1.14×; U2 `U2_m0.95_8_s29423`, and U′ 1.60° at U = −0.48°);
  - end misalignment 2.83 vs 4°;
  - total rotation 1.24 vs 2°;
  - t0 offset 2.08 vs 3 mm;
  - per-move core rotation 0.93 vs 2°.
- **§0.3** ("about 110 first turns"): I count 123 distinct first turns with an F/T record.
- Disclose in §0 that the **tightest margin is the first-move turn error**, not the F/T stop.
  - First-move error ≈ 0.6–0.8° bias minus 0.2–0.4 × the U misalignment. U′ residual sd is 0.36°, so a U′ start at −1° (scored Up_s30131 is at −0.97°) needs a +2.7 sd residual to exceed 2°.
  - `INFERENCE`: a few percent chance of a turn-error failure over about 100 scored first moves. It is not required to change the 2° G1 limit, but it should be stated.

### 5. SUGGESTED: state what happens when an interruption repeats, and whether the verdict may be re-run.
- A trial whose load error persists, or an error matching a marker deterministically, interrupts every resume. The run then stays INCOMPLETE with no stated end. State a maximum number of resumes and that the gate is then not passed; a code fix requires a new freeze.
- `analyze.integrity` re-hashes the artifacts from `/mnt/c`. A transient empty read at verdict time would give INVALID. State that the verdict is read-only and may be re-run, and that an artifact-hash INVALID must reproduce to stand.

### 6. SUGGESTED: evidence at the final code.
- §7 cites the self-check at P-124, which is revision-2 code. Revision 3 changed `two_arm.py` and `trials.py`. Pilot 3 shows they work, but not bit-identity. Re-run `selfcheck.py` (3 trials) at the freeze candidate and record it.
- The pilot-3 re-run records have `source_commit` and `head` = null (`rerun_crashed.py` sets neither). Put the commit in `pilot3_rev3/README.md`.

### 7. SUGGESTED: editing the frozen text after the run.
- `code_problems` (`analyze.py:226-240`) makes any later edit to a frozen path, including the pre-registration's status line, turn a re-run of the verdict into INVALID. Say explicitly that after the freeze, results go in a separate report and frozen files are not edited.

## Checked with no problem found
- **Text vs code:**
  - 138 / 128 trials and 100 turn trials; every seed range; the start draw; `random_u_sequence`;
  - start-sequence, approach and per-move timings; impedance and integral gains and clamps; the J7 law and budget;
  - the F/T rule (2 samples at 200 Hz, > 1.0 N·m) and the stall rule (2° for 20 ms);
  - G2-6 overrides on both arms; negative setups and acceptance (trials and analyze agree);
  - the hold criteria and 0.1 s sampling; the pre-t0 limits; the end-misalignment rule;
  - verdict rules, INVALID causes and the Clopper–Pearson bound.
- **Controllers read only robot state:** `impedance`, `j7_control`, `approach`, `ramp_grip`, the roll command and both guards read only arm joint state and kinematics, the F/T sensor, targets and time. In `move()`, `members`, `Rc` and `axis_world` feed only the monitors. `test_controllers_ignore_cube_state` is sound, with a positive control.
- **Integrity:**
  - move windows are gapless, including the start sequence, the approach and the hold;
  - a crash between link and unlink, or during `apply_resume`, is recovered correctly;
  - deleting a record together with its ledger line after a later start is caught by `present`. Doing so in the final start is not caught, but trials are deterministic, so a re-run cannot change the outcome;
  - WSL `git status` on the frozen paths is clean with `core.filemode=false`, so `require_clean_commit` will not refuse spuriously.
- **Fragility:**
  - first-turn F/T (see item 1 of the table);
  - J7 lag ≈ 0.07° vs 2°; drift ≤ 0.57° vs 1°; penetration ≤ 0.15 mm vs 0.5;
  - per-move slip ≤ 0.20 mm vs 1; roll-back ≤ 0.05° vs 1°; drive impulse min 0.012 N·m·s > 0;
  - hold slip ≤ 0.09 mm and rotation ≤ 0.27° vs 1.0;
  - jam stops at 1.0 N·m: 38.0–44.3° inside the 20–50° window.
