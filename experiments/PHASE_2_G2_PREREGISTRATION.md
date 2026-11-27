# Phase 2 (G2) Pre-registration: two-arm, contact-driven layer turns of the free-core M7 cube

**Status: DRAFT revision 2, NOT IN FORCE (2026-11-27).**
- Revision 2 answers review 1 (`G2_PREREGISTRATION_REVIEW1_2026-11-27.md`, P-122): all 7 required items, and every
  suggestion except per-trial F/T noise seeding (P-123). §9 maps each item to its change.
- The text states what the code does at the commit that introduces this revision.
- Before it is in force: review rounds until "ACCEPTABLE AS IS" (one reviewer subagent per round, P-121), then the
  user's approval recorded in `docs/DECISION_LOG.md`.
- **Freeze procedure:** the freeze commit changes exactly two things: `FROZEN = True` in `run.py`, and this status
  line ("IN FORCE", with the DECISION_LOG entry). No other change to a frozen path. The scored run refuses to start
  while `FROZEN = False` or with uncommitted changes in the frozen paths (§6).
- Gate: `docs/VALIDATION_PLAN.md` G2. **Pass** = repeatable physical turns with prescribed classical controllers; no
  RL. Mapping in §5.
- **Labels:** `FACT`, `INFERENCE`, `ASSUMPTION`, `PROPOSAL`.

## 0. Disclosure (read first)
1. **Everything below was designed after unscored results on rehearsal and pilot seeds** (29000–29999 and earlier
   ranges). Only the scored seeds 30000–30999 are independent of the design.
   - **D16** (P-98 … P-101): a stand-in holder failed for fixture reasons.
   - **D17** (P-102, P-103): the real G2 holder and a compliant-mount turner, 40/40 moves.
   - **C1/C2 pilot** (P-106): 90/90 moves; C1 chosen (P-107).
   - **D18** (P-108, P-110): two xArm7 arms and the drop-away stand.
   - **Jam protection** (P-111, P-113, P-114): the lag guard failed; the torque budget is infeasible at ±20 % model
     error; the wrist F/T guard was adopted.
   - **Arm B gain tuning** (P-115).
   - **Pilot P-5** (P-118): 56/56 pass. The F/T stop and the limits were set from it (P-119).
   - **Revision-2 pilot** (§7, P-124).
2. **Move strings:** U, U′, U2 and U U′ U2 U′ U were run many times in rehearsals. The 20 random 10-move sequences are
   drawn from the scored seeds and are new.
3. **First-turn torque tail (`FACT`).** With the ±1° start misalignment, the first turn's F/T τ_z reached 0.47 N·m once
   (smoke) and at most 0.35 in 30 U pilot turns. The revision-2 pilot adds U′ and U2 first turns (§7). The stop is
   0.8 N·m.
   - `INFERENCE`: the tail is estimated from about 75 first turns. A false stop in a scored trial is a failure.
4. **The G1 rig's grip was capped at about 11.5 N** (G1 report §3 item 12). G2 is the first squeeze test above that.
5. **`ASSUMPTION`s:**
   - M7's clearance (0.05 mm), rounded edge (R 2.5 mm), uncalibrated turning torque, and core mass and inertia
     (1.7 g, 2e-8);
   - pad friction μ 0.8; pad compliance as a contact time constant (0.01 s);
   - the F/T sensor's size (75 × 35 mm, 0.6 kg) and noise (0.01 N·m, one stream `default_rng(29000)` shared by every
     trial; see §8);
   - the Menagerie xArm7 joint friction, damping and armature;
   - the G2 linkage is closed by soft constraints, and the fingertips splay 0.25–0.9° under load;
   - **only collision geometry can touch the cube:** the G2 finger and knuckle meshes are visual-only, the stock pads
     are disabled, and the four fingertip boxes are the collision geometry of the fingers. A finger body cannot register
     a cube contact.
6. **Simulation only.** Nothing here establishes sim-to-real transfer.

## 1. System under test (frozen; `experiments/D18_two_arm_m7/two_arm.py`, `layout.py`)
| Part | Configuration | Source |
|---|---|---|
| Cube | **M7** as G1-scored: B1, L0 magnets (unchanged `MagnetSystem`), rounded R 2.5 mm, gap 0.05 mm, NoSlip 10, dt 0.5 ms. **Free core** (free joint, 1.7 g) | P-95, P-97 |
| Arms | Two xArm7 1305+ (`P2_robot_model/build_model.py`; the generated model and meshes are fingerprinted, §6), actuator gravity compensation. Arm A at the origin; arm B at (1.0, 0, 0) m, yawed 180°; table z = 0 | P-96, P-108 |
| Cube pose | Centre (0.5, 0, 0.30) m nominal; cube +z (U) = world +x | P-108 |
| Grippers | Two Gripper G2 models (four-bar, tendon drive). `set_grip_force` calibrated at 57 mm; **20 N on both arms** | P-97 |
| Arm A fingertip | **One flat box per finger**, 30 × 30 × 4 mm, from the D end over D and 11 mm of E | P-97, D17 |
| Arm B fingertip | **C1**: one box per finger, 25 × 14 × 4 mm, distal end 14 mm inside the U face | P-107 |
| Fingertip contact | Both arms: μ 0.8, condim 4, rig-pad solimp, **time constant 0.01 s** | P-105 |
| Arm B wrist | **UFACTORY 6-axis F/T sensor** (modelled) between the flange and the gripper; MuJoCo force/torque sensors at the interface; sampled at 200 Hz, + N(0, 0.01 N·m) | P-114 |
| Stand | Actuated stand under D and E only (33 × 40 mm), stiff slide servo; drops 30 mm after arm A's grasp | P-109, P-110 |
| Visuals | Stickers and the room are off in scored runs (physics-identical, P-110, P-112) | |

## 2. Procedure and controllers (classical; `two_arm.py`)
**Inputs allowed:**
- Controllers read only robot joint states, the kinematics derived from them, the F/T sample, commanded targets and
  time. **Never cube or cubie state.**
- **Targets** come from the nominal cube pose (layout IK).
- **The roll direction** comes from the nominal layout (`roll_sign`, review 1 item 1). The measured sign is logged per
  move (`axis_sign_measured`), never used.
- **Tests:**
  - `test_controllers_ignore_cube_state`: scrambling every cube joint state leaves arm B's control outputs
    **bit-identical** (`np.array_equal`), with a positive control;
  - `test_roll_commands_ignore_cube_state`: the J7 and gripper command sequence of a whole move is identical with the
    cube state scrambled.

**Setup (before t0, logged setup writes):**
1. Arm A at its IK grasp pose, gripper open; arm B at its pre-grasp pose (gripper base 40 mm outside the grasp along
   the axis), gripper open.
2. The cube rests on the stand at the seeded start offset and misalignment (§3).

**Start sequence (gravity on throughout; monitored, §4.1):**
1. Settle 0.3 s.
2. Arm A ramps closed at 0.5 rad/s (2 s), then 0.3 s.
3. The stand lowers 30 mm over 0.5 s, then 0.5 s.

**t0** is the end of the start sequence: the trial-level reference pose and every cubie's misalignment are recorded
here.

**Approach (monitored):** arm B moves 40 mm along the axis over 1 s, then 1 s.

**Arm A:** joint position servos hold the IK pose; the gripper stays closed.

**Arm B, joints 1–6:** torque control, a Cartesian impedance at the gripper base.
- Position: K_P 4000 N/m, D_P 60 N·s/m. Axis direction: K_R 50 N·m/rad, D_R 2 N·m·s/rad. Weak posture (2 N·m/rad)
  and joint damping (1 N·m·s/rad).
- Integral term: KI_P 8000, KI_R 200, clamped at 25 N / 3 N·m. It **integrates only while the fingers are open and is
  held, not zeroed, while gripping.**
- Torques are clamped to the URDF peak efforts.

**Arm B, J7 (roll):** torque control.
- τ = clip(ff + 800·(q_c − q) + 80·(q̇_c − q̇), ff ± B).
- ff = 2·q̇ (measured) + 1·tanh(q̇_c / 0.02).
- B = 2 + 0.2·(|2·q̇| + 1) N·m.

**Per move** (one move = from the end of the previous move through its own roll-back):
1. Settle 0.3 s (fixed; no cube-state rest check).
2. Integral off; ramp arm B closed (0.5 rad/s), then 0.3 s.
3. Roll on a cosine ramp, 1 s per quarter turn. Commanded rotation about U's outward normal: U −90°, U′ +90°,
   U2 −180° (one direction).
4. Hold 0.3 s; open; 0.3 s; integral on.
5. Roll back to the start angle (1 s, open).

**Guards during a roll:**
- **F/T stop:** |τ_z| > **0.8 N·m** on two consecutive 200 Hz samples.
- **Stall rule:** J7 following error > 2° for 20 ms.
- Either freezes the roll at the current angle; the move then opens and rolls back as usual.

## 3. Trials (`experiments/E8_scored_g2/run.py`, `build_jobs`; 138 trials, 128 scored)
**Start draw (`trials.start_draw(seed)`):**
- Cube offset uniform ±1 mm per axis.
- Per-face setup misalignment uniform ±1° (6 faces, as G1), from `default_rng(seed)`.
- The cube starts solved.

| ID | Trials | Seeds | Kind | Scored |
|---|---|---|---|---|
| G2-1 | 20 × 60 s hold after the start sequence (arm B open at pre-grasp; no approach) | 30000–30019 | hold | yes |
| G2-2 | 20 × U, 20 × U′ | 30100–30119, 30120–30139 | seq | yes |
| G2-3 | 20 × U2 | 30200–30219 | seq | yes |
| G2-4 | 20 × U U′ U2 U′ U; 20 × 10 random moves from {U, U′, U2} (`default_rng(seed + 500000)`) | 30300–30319, 30320–30339 | seq | yes |
| G2-5 | C1 vs C2 (done, P-106) | – | – | no (decided P-107) |
| G2-6 | U U′ U2 U′ U with one change: K_P 2000; K_P 6000; pad μ 0.5 (both arms); grip 10 N (both); grip 30 N (both); grip 50 N (both; stress); rigid pads (0.001 s); extra cube offset (0, 2, 2) mm | 30600–30607 | sens | **reported only** |
| G2-7 | 2 each of two_layer, collision, open_midturn, jam (scored: 8); 2 × offcentre (**reported only**) | 30700–30709 | neg | 8 yes, 2 reported |
| G2-8 | throughput: real-time factor `sim_time_s / wall_s` of every trial record (holds included; harness-exception records have none) | – | – | reported only |

- Scope: U-family turns from one stabiliser grasp. No regrasp or other faces (G4; P-105).
- One trial per spawned process.

## 4. Criteria (stated before any scored data)
### 4.1 Turn trials (G2-2, G2-3, G2-4)
The worker (`trials._seq_reasons`) and the verdict script (`analyze.recompute_seq`, independent code with its own copy
of the limits; a test checks the copies agree) both apply the following. A trial passes only if **all** hold.

**Integrity:**
- no abort, edit-audit violation, numerical failure or harness exception;
- the model audit finds no actuator and no equality constraint acting on a cube body;
- the cube is solved at t0;
- every move is recorded;
- the final state matches the oracle.

**Start sequence and approach** (no judged contact may occur):
- non-fingertip robot–cube, arm–arm, robot–table, robot–stand or robot–jam-block contact;
- cubie–cubie penetration > 0.5 mm;
- in the approach, also cube–stand contact.

**Every move** (its window runs from the previous move's end through its own roll-back):

| Check | Limit |
|---|---|
| Observed move (readout → oracle) | = commanded move |
| Turn error (mean layer rotation − nominal, core frame) | ≤ **2°** |
| Drift (non-target cubies about the face axis) | ≤ **1°** |
| Cubie–cubie penetration | ≤ **0.5 mm** (fingertip–cubie penetration is reported) |
| Causality: arm B **fingertip–cubie** normal force > 0.5 N before the U layer's speed relative to the core exceeds 5°/s | as stated |
| **Drive:** the fingertip torque on the layer about its axis, integrated over the roll, has the commanded sign (> 0) | as stated |
| **Roll-back:** every cubie's rotation about the face axis during the roll-back | ≤ **1°**, and the logical state is unchanged |
| Contacts: non-fingertip robot–cube, arm–arm, robot–table, robot–stand, robot–block, cube–stand | none |
| Core slip relative to arm A's gripper | ≤ **1 mm** |
| Core rotation relative to arm A's gripper | ≤ **2°** |
| Guard stop | none |

**Trial level (from t0 to the end):**
- total core slip ≤ **2 mm** and rotation ≤ **2°**, relative to arm A's gripper;
- every cubie's misalignment (angle to the nearest cube rotation, core frame) at the end ≤ its t0 value + **1°**.

**Reported, not judged:**
- J7 actuator torque; fingertip torque on the layer; F/T peak; pad penetration;
- actuator saturation count (actuators are clamped to their limits by construction);
- grasp and tracking errors; the measured roll sign.

### 4.2 Holds (G2-1)
Pass if all hold:
- integrity as §4.1, and the start-sequence contacts as §4.1;
- the cube is solved at t0 and at the end;
- over 60 s, relative to arm A's gripper: core slip ≤ **1.0 mm** and rotation ≤ **1.0°**;
- during the hold: none of the §4.1 contacts (cube–stand included), cubie penetration ≤ 0.5 mm;
- misalignment growth ≤ **1°** per cubie.

### 4.3 Negative cases (G2-7; `trials.neg_outcome`, `analyze.recompute_neg`)
Any abort, edit-audit violation, numerical failure, harness exception or model-audit finding **fails** a negative
trial. Otherwise:

| Case | Fault | Pass when (the detection it accepts) | What it tests |
|---|---|---|---|
| `two_layer` | Turner inserted 25 mm (6 mm across the U/E boundary) | a guard stop, or a failure of the observed-move, turn-error or drift check | the offline checks detect a two-layer grip |
| `open_midturn` | Arm B opens halfway through the roll | a failure of the observed-move or turn-error check | the checks detect an incomplete turn |
| `collision` | Turner driven 34 mm deep, into arm A's fingertips | arm–arm or non-fingertip robot–cube contact recorded (approach or move) | the contact monitor detects a collision |
| `jam` | A world-fixed block above the top face beside the U layer | a guard stop after **20–50°** of roll, core slip ≤ **0.5 mm**, cubie penetration ≤ 0.5 mm | the **online** guard stops a blocked turn safely |
| `offcentre` | Cube 5 mm sideways | **reported only**: "clean" or "detected" | robustness to a larger placement error |

- `two_layer`, `open_midturn` and `collision` test the offline checks; only `jam` tests the controller online.
- With n = 2 per case, a pass shows that detection works on two instances, not a detection rate.

### 4.4 Verdict (`analyze.py`)
**INVALID** if any of the following:
- no manifest;
- a record that does not parse;
- a ledger SHA-256 mismatch;
- a record without a ledger line, or a ledger key with more than one line or without a record;
- any file or directory the run procedure does not produce, including any orphan temporary file;
- the manifest's trial list differs from the registered `build_jobs()`;
- the manifest's frozen paths differ from `run.FROZEN_PATHS`;
- an artifact SHA-256 (robot model, calibration, meshes, magnet table, V3 records) differs from the manifest;
- a record's metadata (experiment, trial ID, spec, commit, scored / smoke) differs from its manifest entry;
- a record's stored `pass` differs from the independent recomputation.

**INCOMPLETE:** a manifest trial without a record.

**PASS:** every one of the 128 scored trials passes (**zero tolerance**, P-105).

**NOT PASSED:** otherwise.

**Reported:**
- a Clopper–Pearson 95 % upper bound on the per-trial failure rate of the 100 turn trials;
- per-move and trial-level maxima; the hold, negative and G2-6 tables; G2-8.

## 5. Mapping to VALIDATION_PLAN G2
| G2 checklist item | Evidence |
|---|---|
| Distinct xArm7 instances with validated tool frames, limits, collision geometry | layout IK (P-108, ≥ 25.8° joint margin); contact checks in the start sequence, the approach and every move; G2-7 `collision` |
| Approved passive fingertip candidate accurately mounted | P-97 / P-107 fingertips; non-fingertip contact checks |
| Stable classical stabilisation against a physical rotating layer | G2-1 holds; per-move and trial-level core slip and rotation; roll-back and misalignment checks |
| Contact-driven 90° and 180° turns across multiple starts, no unintentional adjacent-layer rotation | G2-2 … G2-4: observed move, turn error, drift, causality, drive |
| Collision/force/clearance logs and sensitivity to alignment and friction | per-move logs; G2-6; G2-7 |

## 6. Run integrity (`run.py`)
**Scored command (WSL, repo root, after the freeze):**
`~/.venvs/rubiknetic/bin/python experiments/E8_scored_g2/run.py all --jobs 8`, then
`~/.venvs/rubiknetic/bin/python experiments/E8_scored_g2/analyze.py`.

**First start:**
- `results/` must be empty.
- `MANIFEST.json` is linked atomically. It holds the trial list, environment, frozen paths, commit, and **artifact
  SHA-256s**: the generated robot model, its gripper calibration, every mesh it references, the magnet near-field table
  in use, and the V3 check records.

**Logs and records:**
- `STARTS.txt` logs each start, with its resume plan logged before it is applied.
- `LEDGER.txt` holds one line per record, with its SHA-256.
- Records are written by the parent only: temporary file, fsync, `os.link` (never overwritten), ledger line.
- Each record stores the manifest commit and the start's HEAD.

**Resume refuses if:**
- the trial list, an environment field (MuJoCo, NumPy, SciPy, Python, CPU), an artifact SHA-256 or a frozen path differs
  from the manifest;
- foreign files or directories exist;
- a ledger key has more than one line or no record.

On a resume, orphan temporary files are moved to `_interrupted/` and records without a ledger line are reconciled.

**Errors and interruptions:**
- A harness exception becomes a failing record.
- MemoryError, OSError, the magnet-availability refusal or a broken worker pool are interruptions (exit 3).
- **Every trial runs in its own spawned process** (`max_tasks_per_child = 1`, whatever `--jobs` is). Settings never
  carry over, and `trials.configure` takes its defaults from fixed constants.

**Frozen paths (`run.FROZEN_PATHS`):**
- this file; `experiments/E8_scored_g2/{run,trials,analyze,selfcheck}.py`; `tests/test_scored_g2.py`;
- `experiments/D18_two_arm_m7/{two_arm,layout}.py`; `experiments/D17_real_holder_m7/{hold,turn}.py`;
  `experiments/D16_free_core_m7/grip_probe.py`; `experiments/P2_robot_model/build_model.py`;
- `experiments/E{4,5,7}_scored_*/run.py`; `experiments/D8_alignment/{magnets,d8_1b_stage1}.py` and
  `results/d8_1b_checks*.json`;
- `experiments/D10…/d10_rest.py`, `D11…/d11_analyze.py`, `D13…/{d13_run,d13_analyze}.py`;
- `src/rubiknetic/__init__.py`, `src/rubiknetic/cube_physics/`, `src/rubiknetic/cube_logic/`.

`test_frozen_paths_cover_every_loaded_module` checks that every repository module a trial loads is frozen.

**Procedure (as G1 §2):**
- Before a resume, leftover worker processes of the stopped start are found and stopped.
- No other WSL jobs during the run; each record stores its load average.
- The runner refuses to start with less than 2 GB free.

**Environment:** WSL Ubuntu-24.04, `~/.venvs/rubiknetic` (Python 3.12.3, MuJoCo 4.0.1, NumPy 2.5.4, SciPy 1.18.1).
About 0.09× real time per trial process; 138 trials take about 1.5–2.5 h on 8 workers.

**Seed search (review 1 suggestion 14):**
- Tracked files contain no record using 30000–30999. The only uses are synthetic test calls.
- The search is repeated and recorded at the freeze.

## 7. Evidence before the freeze
- **Tests:** `tests/test_scored_g2.py`, 33 tests pass.
- **Self-check:** `selfcheck.py` re-runs three pilot trials and requires the **physics identity** (final qpos SHA-256,
  the start sequence, observed moves, guard stops, F/T peaks) to equal the committed pilot records. Result: P-124.
- **Smoke:** a smoke run killed after a record link and resumed gives PASS, with the ledger reconciled (P-120).
- **Revision-2 pilot** (`run.py pilot2`, seeds 29300–29353; P-124): 20 U′ and 20 U2 first turns with the stop
  disabled; 4 × U U′ U2 U′ U and 2 holds at the fixed settings; 2 each of jam, two_layer, collision and open_midturn.
  Results in `pilot2_rev2/`.

| # | Prerequisite | Status |
|---|---|---|
| P-1 … P-6 | fingertips, layout, controller, runner, pilots and limits, self-check and smoke | done (P-106 … P-120) |
| P-6b | revision-2 code, tests, self-check and pilot | P-123, P-124 |
| P-7 | independent reviews until "ACCEPTABLE AS IS" | **open** (review 1: P-122) |
| P-8 | the user's approval; freeze commit; DECISION_LOG | **open** |

## 8. Limitations (to be stated with any G2 result)
1. **Simulation only;** every `ASSUMPTION` of §0.5 applies.
2. **Scope:** U-family turns from one grasp. No regrasp, no other faces, no camera state (G4, G5).
3. **Controllers:** the controllers are first designs, tuned on two pilot seeds. K_P 4000 is at the edge of the tuning
   grid.
4. **F/T sensor:** the sensor model is assumed (size, noise; no offset drift, temperature or bandwidth limit). **The F/T
   noise is one seeded stream shared by every trial,** so false-stop risk is correlated across trials, not independent.
5. **Joint model:** the J7 and arm joint friction values are Menagerie's.
6. **Starting conditions:** the start pose is drawn within ±1 mm / ±1°. Larger placement errors are untested except
   G2-6 (n = 1 per condition) and `offcentre` (reported only).
7. **Seeds:** one seed per scored trial; the negative cases have 2 each.
8. **What the limits mean.**
   - The limits are set from what the task needs, not tightened to the pilot:
     - 2° turn error and 1° drift (G1);
     - 1 mm per-move and 2 mm total core slip: within the C1 turner's verified ±2 mm axial tolerance (P-106), so arm
       B's nominal grasp stays valid over a sequence;
     - 2° core rotation: about 1 mm at the cube's corner radius;
     - 1° hold and misalignment growth.
   - **A PASS therefore shows that the turns succeed and the cube stays within these task tolerances.** It does not
     establish tight stabilisation (the pilot values are 5–10× below the limits), robustness beyond ±1 mm / ±1°, or
     anything on hardware.

## 9. Response to review 1 (P-122)
| Item | Change in revision 2 |
|---|---|
| R1 roll sign from cube state | `roll_sign` from the nominal layout; measured sign logged only; new test of the move-level command sequence |
| R2 unjudged phases | the start sequence and the approach are monitored and judged; move windows are gapless and include the roll-back (rotation ≤ 1°, state unchanged); trial-level core slip, rotation and misalignment growth |
| R3 negative rules | integrity failures fail every case; each case names its accepted detection; `offcentre` reported only (128 scored) |
| R4 integrity gaps | orphan temporary files anywhere, duplicate ledger keys, ledger keys without a record and unknown directories are INVALID (and refused on resume); the manifest list must equal `build_jobs()`; record metadata is checked; 8 tamper tests |
| R5 frozen coverage | `FROZEN_PATHS` covers every loaded module (tested); artifact SHA-256s in the manifest, compared at every resume and in the verdict |
| R6 in-process trials | real trials always run in spawned processes; fixed defaults in `configure`; `--jobs 8` default and in §6 |
| R7 text vs code | G2-8 includes holds; "bit-identical" is `np.array_equal`; the integral wording; both arms in G2-6; fingertip–cubie force for causality; the collision-geometry assumption; the FROZEN test monkeypatched; docstrings corrected; the freeze procedure |
| S8 causality | fingertip–cubie force only; the new judged drive check; a model audit for actuators or equalities on cube bodies |
| S9 U′/U2 tail | revision-2 pilot, 20 + 20 single turns (§7) |
| S10 core rotation | judged per move (≤ 2°) and per trial |
| S11 jam | roll window 20–50°, cubie penetration judged |
| S12 shared noise | **not adopted** (user, P-123): disclosed in §8 item 4 |
| S13 stand and block contacts | monitored and judged |
| S14 procedure | disk check, load recorded, HEAD stored per record, worker clean-up and seed search stated (§6) |
| S15 wording | §4.3 "what it tests" column |
| S16 independent verdict | `analyze.recompute_*`; a disagreement makes the run INVALID |
| S17 limits | justified from the task (§8 item 8) |
