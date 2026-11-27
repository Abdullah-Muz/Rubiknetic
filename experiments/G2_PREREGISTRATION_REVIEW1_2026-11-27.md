# G2 pre-registration review 1 (2026-11-27)

VERDICT: REQUIRES CHANGES

*(Independent reviewer subagent, one per round (P-121). It was given the pre-registration and the code, not the
assistant's conclusions. The report is saved as returned.)*

Scope: revision 1 of `experiments/PHASE_2_G2_PREREGISTRATION.md` at HEAD `0e45a13`, read against `E8_scored_g2/{run,trials,analyze,selfcheck}.py`, `D18_two_arm_m7/{two_arm,layout}.py`, `D17_real_holder_m7/{hold,turn}.py`, `tests/test_scored_g2.py`, the pilot records and DECISION_LOG P-115 to P-121. The review was read-only. No simulation was run and no scored seed was touched. What I ran:
- the unit tests: 21 passed;
- a list of the repository modules a trial imports;
- synthetic-runner checks of `run.execute` and `analyze.verdict`, done in a temporary folder;
- checks of `trials.neg_outcome`;
- scans of the committed pilot and smoke records.

---

## REQUIRED

### 1. Arm B's roll direction is computed from the cube's state. The claim "Never cube or cubie state" (§2) is false.
- Evidence:
  - In `two_arm.py:599-601`, `move()` reads `Rc = d.xmat[self.core]` and sets `axis_world = Rc @ FACE_NORMAL[face]`.
  - At `:608-609` it computes `axis_sign = sign(axis_world @ zB)`.
  - At `:619` the commanded J7 trajectory uses `A = axis_sign * delta`.
  - So the sign of every roll command depends on the core's orientation, which is simulator truth about the cube. In practice it is probably constant, but it is still a cube-state input to the controller.
- `test_controllers_ignore_cube_state` (`tests/test_scored_g2.py:244-247`) calls only `impedance()` and `j7_control()`. It does not exercise `move()`, `approach()`, `ramp_grip()` or the guards, so it cannot detect this read. Its scope is narrower than §2 states.
- Fix:
  - Compute the roll sign once from the nominal layout: nominal U axis (world +x) · nominal arm B tool z (`RBt[:, 2]`). The measured value may be logged for monitoring only.
  - Extend the test so the commanded J7 trajectory (`self.j7` and `d.ctrl[aB]` over the first steps of a roll) is shown to be unchanged when the cube state is perturbed.
  - Re-run `selfcheck.py`. It should stay 3/3 identical if the sign was constant.

### 2. Parts of every trial are not judged.
- **Roll-back.**
  - `two_arm.py:651-653` takes `r1` and snapshots `a = dict(self.acc)` before the 1 s roll-back with the gripper open (`:654-662`).
  - So contacts during the roll-back are never judged: non-fingertip cube contact, arm-arm contact, table contact and cubie penetration.
  - Layer rotation caused by the open fingertips dragging the layer is also never judged.
  - The next move's `r0` is taken after its settle (`:597`), so the rotation between `r1` of move i and `r0` of move i+1 falls outside every turn-error and drift measurement.
- **Approach.**
  - `rec["approach"]` records `robot_cube_nonpad`, `arm_arm`, `robot_table` and `pen_cubie` (`:566-578`).
  - `trials._seq_reasons` (`trials.py:71-93`) never reads them. Only the `collision` negative case does (`trials.py:171-172`).
- **Start sequence** (arm A grasp and stand drop).
  - `TwoArm.__init__` steps with `ctrl_step` (`:393-406`), not `step`, so no contacts are recorded at all.
- **Accumulated error.**
  - Core slip is measured per move from after the settle to after the open (`:602`, `:668`).
  - Slip during the roll-backs and settles, and the total over a 10-move sequence, are not bounded.
  - No layer's absolute alignment at the end is checked. Turn error is relative to `r0`, and the readout snaps at 45°, so a layer left 20° off passes `final_matches_oracle`.
- UNVERIFIED: whether drag during the roll-back happens. The pilot records do not contain the data needed to tell.
- Fix:
  - Snapshot the per-move accumulators after the roll-back, or add a judged "between moves" block.
  - Judge the approach and start-sequence contacts with the same contact criteria.
  - Add trial-level checks from t0 to the end: total core slip and rotation relative to arm A, and the absolute residual angle of every layer at the end (e.g. ≤ 2°).

### 3. The negative-case acceptance rules can accept solver failures, and `offcentre` cannot fail.
- Quick check (`trials.neg_outcome` on a record with `aborted: NumericalFailure`):
  - `two_layer` → (True, "detected");
  - `open_midturn` → (True, "detected");
  - `offcentre` → (True, "flagged");
  - an edit-audit violation in `offcentre` → True.
- This contradicts §4.3, "A solver failure is never a pass". The cause is that `flagged = bool(rec["fail_reasons"])` (`trials.py:169`) counts "aborted" as a detection.
- `offcentre` returns True unconditionally (`trials.py:177-178`), yet it is counted among the "130 scored" trials.
- Fix:
  - Any abort, numerical failure, edit-audit violation or harness exception fails a negative trial.
  - Name the detection signal each case accepts. For example, `two_layer` accepts a guard stop or a failure of `ok_drift` or `ok_oracle`; `open_midturn` accepts a failure of `ok_oracle` or `ok_turn_error`.
  - For `offcentre`, either move it to reported-only (128 scored), or pass it only if it is a clean turn, or a guard stop with no safety violation (no non-fingertip or arm-arm contact, cubie penetration within the limit).

### 4. Integrity gaps in `run.py` and `analyze.py` let a bad run reach PASS. Each of these was shown with the synthetic runner.
- (a) **An orphan temporary file inside an experiment folder gives PASS.**
  - `foreign_files` accepts `.*.json.tmp` files in subfolders (`run.py:256`).
  - `analyze.py:41-43` only flags temporary files that `foreign_files` reports, which here are only root-level ones.
  - This contradicts §4.4 ("an orphan temporary file at verdict time" is INVALID).
- (b) **Deleting a failing record and resuming gives PASS.**
  - Sequence: first verdict NOT PASSED; the record was deleted; the resume re-ran it; the verdict became PASS with 4 ledger lines for 3 trials.
  - Neither `plan_resume`/`foreign_files` nor `integrity()` flags a ledger line whose record is missing, or a key with two ledger lines (`analyze.py:39` keeps the last one in a dict).
  - Combined with item 5, the re-run could use changed code.
- (c) **The manifest's trial list is never compared with the pre-registered `build_jobs()`.** A 3-trial run gives PASS with `n_scored` = 3. `analyze.py` also does not check:
  - the manifest's `frozen_paths`;
  - the record metadata (`trial_id`, `spec` against the manifest `kw`, `scored` true, `smoke` false, `source_commit`).
- (d) An empty extra directory under `results/` is not flagged. This is minor.
- Fix:
  - Make all of (a) to (c) INVALID: a ledger key with more than one line, or with a missing record.
  - Make the resume refuse the same cases.
  - Make `analyze` require that `manifest["trials"]` equals the normalised `build_jobs()` (138 trials, 130 scored) and that the record metadata matches the manifest.
  - Add unit tests for each case.

### 5. The frozen paths and the manifest do not cover the code and data that set the physics and the limits.
- Importing `trials` loads these repository modules that are **not** frozen:
  - `src/rubiknetic/cube_physics/scored.py`, which holds `THRESHOLDS` (the 2° turn error, 1° drift, 0.5 mm penetration and 0.5 N / 5°/s causality limits) and `apply_setup_misalignment`;
  - `experiments/E4_scored_m4/run.py` (magnet tables, `Refused`);
  - `experiments/E5_scored_m5/run.py`;
  - `experiments/D8_alignment/{magnets,d8_1b_stage1}.py`;
  - `experiments/D13_rest_slip_mechanism/{d13_run,d13_analyze}.py` (`with_noslip`);
  - `experiments/D16_free_core_m7/grip_probe.py` (`load_e7`);
  - `experiments/D10_m5_rest_diagnostic/d10_rest.py`;
  - `experiments/D11_rest_slip_count/d11_analyze.py`;
  - `src/rubiknetic/__init__.py` and `cube_physics/__init__.py`.
- Some physics-defining files are gitignored, so git checks cannot see them, and the manifest stores no SHA-256 for them:
  - `third_party_cad/robot/generated/xarm7_g2_1305+.xml`;
  - its `_gripper_calibration.json` and the meshes;
  - `experiments/D8_alignment/results/tables/*.npz`.
- `experiments/D8_alignment/results/d8_1b_checks.json` is also not in the frozen list. G1's frozen list included it, and G1's manifest also stored the table SHA-256s (G1 pre-registration §2).
- Fix:
  - Freeze every repository module that `trials` loads, and add a unit test that compares `sys.modules` after `import trials` with `FROZEN_PATHS`.
  - Store SHA-256s of the robot XML, the calibration JSON, the meshes, the magnet tables and `d8_1b_checks.json` in `MANIFEST.json`. Compare them at every resume and in `analyze`.

### 6. `--jobs 1` runs every trial in the parent process, and settings leak between trials.
- `execute()` runs the trials in-process when `n_workers <= 1` (`run.py:328-335`). §6 says "One trial per spawned process".
- `configure()` uses `TA.K_P = ov.get("kp", TA.K_P)`, and the same pattern for `dp` and `ki` (`trials.py:58-60`). The default is the current module value, not 4000.
- The run order sorts longest-first (`run.py:314`), so the 5-move G2-6 `kp_x0.5` / `kp_x1.5` trials run before the G2-2 and G2-3 trials. Those trials would then run at K_P 2000 or 6000 without any warning.
- The default is `--jobs 4` (`run.py:394`), while §6 says 8 workers.
- Fix:
  - Always use the spawn pool (including for one worker), or refuse `--jobs < 2` for scored runs.
  - Take the `configure` defaults from fixed constants.
  - Write the exact scored command, including `--jobs 8`, in §6.

### 7. Places where the text and the code disagree (rewrite the text, or change the code).
- §3 G2-8, "from every record": hold records have no `sim_time_s` (`trials.py:109-130`), so G2-8 leaves out the 20 holds and any exception records (`analyze.py:100-101`).
- §2, "bit-identical": the test uses `np.allclose(..., atol=1e-9)` (`test_scored_g2.py:265`).
- §2, "integral term active only while the fingers are open": the accumulated `Ip`/`Ir` stops integrating but is still applied while gripping (`two_arm.py:437-441`, `:604`). Say "integrates only while open; held, not zeroed, while gripping".
- §3 G2-6: grip 10/30/50 N applies to both arms (`two_arm.py:303-304`), and so does pad μ 0.5 (`:203`, `:210`). Say so.
- §4.1 `ok_causal`: the force counted is any contact force on arm B's fingertips (`force_on(self.tipsB)`, `:503-510`, `:541`), including contact with the other fingertip or with arm A. It is not only fingertip–cubie force.
- §4.1 `ok_no_nonpad_cube_contact`: only collision geometry counts.
  - The finger link meshes are class `visual` (contype 0) in the generated model.
  - The stock pads are disabled (`hold.py:69-71`).
  - So a finger body cannot register contact. Disclose this as a modelling `ASSUMPTION`.
- §6, "21 unit tests pass": true now. But `test_scored_start_refused_until_frozen` asserts `R.FROZEN is False` (`test_scored_g2.py:189-192`), so the suite fails at the freeze commit. Make the test independent of the flag, for example by monkeypatching `FROZEN`.
- Some docstrings and comments in frozen files contradict the pre-registration:
  - `two_arm.py:9-15`: K_P 2000, J7 as a kp 5 / ±1 N·m position servo, gravity-off setup;
  - `:92`: the `PAD_MU` comment describes `OPEN_MIDTURN`;
  - `:271-273`: the J7 servo comment.
  Fix these before the freeze, because the frozen files are part of the record.
- Freeze procedure: §0 says the freeze commit "contains no other code change", but the pre-registration's own status line (a frozen path) must also change. State this explicitly.

---

## SUGGESTED

### 8. `ok_causal` is decided when arm B's gripper closes, not during the roll, and its margin is small.
- Over the 80 pilot moves where both times exist, the layer's speed relative to the core exceeds 5°/s only 1.5–25 ms after the fingertip force exceeds 0.5 N. The smallest gap, 1.5 ms (3 steps), occurs in `U_s29200`, `U_s29222` and `rand10_s29263`.
- The roll starts at least 0.3 s later. So the check shows that the fingertips touch first; it does not show that the fingertip torque drives the turn.
- A 3-step margin is also a source of failures unrelated to the claim.
- Suggestion:
  - count only fingertip–cubie force;
  - time the motion onset from the start of the roll;
  - add a judged check that, while the layer moves, the fingertip torque on the layer has the commanded sign;
  - add a model-level assertion that no actuator, `xfrc_applied` or equality acts on cube bodies; the magnets act through `MagnetSystem`, which P-16 permits.

### 9. The first-turn F/T torque tail for U′ and U2 has hardly been piloted.
- The stop-disabled first turns are almost all U:
  - P-U: 30 U turns;
  - P-rand: one U′ first turn (0.244 N·m, `rand10_s29262`) and one U2 first turn (0.188 N·m, `rand10_s29263`);
  - smoke (stop active): U2 0.252 N·m.
- The scored run has 20 U′ and 20 U2 first turns at zero tolerance, and a false stop is a failure.
- Suggestion: before freezing, pilot about 20 U′ and 20 U2 single turns on pilot seeds with the stop disabled.

### 10. Judge per-move core rotation relative to arm A.
- It is currently reported only; the pilot maximum is 0.71°. Stable stabilisation is a G2 checklist item.
- For example, the whole cube could turn 5° in arm A's grip during a turn and still pass every judged check.

### 11. Tighten the `jam` acceptance.
- Require the stop's `roll_done_deg` to fall in the range expected from contact with the block (pilot: 32–35° at 0.8 N·m), so that a spurious stop is not counted as a detection.
- Also judge `pen_cubie` and the cubie–block penetration.

### 12. Arm B's guard noise is shared by every trial.
- The F/T noise comes from `default_rng(29000)` for every trial (`two_arm.py:346`), so false-stop risk is correlated across trials.
- Seed it per trial (for example, trial seed + 1,000,000), or disclose this in §8.

### 13. Robot contact with the stand and the jam block is not monitored.
- `contacts()` only classifies cubie, arm and table contacts (`two_arm.py:479-501`). Add the stand and the jam block.

### 14. Procedural items from G1 are missing.
- G1 §2 had these; G2 does not:
  - stop any leftover worker processes before a resume;
  - refuse to start below a free-disk threshold;
  - no other WSL load during the run;
  - a recorded search showing the scored seeds were never used before.
- My search of tracked files found no record using 30000–30999. The only uses are synthetic test calls (30100–30103, start draws 30000–30049, sequences 30320–30321). Untracked files were not searched (UNVERIFIED).
- On a resume, records get `source_commit` = the manifest commit (`run.py:305`) even if HEAD differs outside the frozen paths. Store HEAD in each record as well.

### 15. Describe G2-7 accurately.
- `two_layer`, `open_midturn`, `offcentre` and `collision` test whether the offline checks are sensitive to a fault. Only `jam` tests how the controller handles a fault online.
- "A negative trial passes when the fault is handled" overstates this. Reword, and note that n = 2 per case only shows that detection works on two instances.

### 16. Recompute the verdict independently.
- `analyze.py` trusts each record's own `pass` field, which the worker computes with `trials.py`.
- Recompute pass or fail from the raw per-move fields and the frozen limits in `analyze`, and flag any disagreement.

### 17. Justify the limits from what the task requires, not from the pilot.
- Per-move slip is limited to 1 mm against a pilot maximum of 0.19 mm. Hold slip is limited to 1 mm against 0.09 mm, and hold rotation to 1° against 0.27°.
- Limits set this loose after seeing the data are unlikely to fail.
- Say what a PASS at these limits does not establish: tight stabilisation, robustness beyond ±1 mm / ±1°, independence of the guard noise across trials, or any result on hardware.

---

## What a PASS would establish, once the items above are fixed
- With the nominal arm targets, the fixed classical controllers and a start drawn from ±1 mm / ±1°, 100 U-family turn trials and 20 holds of the modelled M7 cube succeed in simulation. The per-trial failure rate would be ≤ about 3 % (one-sided 95 % bound, 0 failures in 100).
- It would not establish sim-to-real transfer, robustness to larger placement errors (G2-6 is n = 1 per condition and reported only), or anything about turns of faces other than U.
