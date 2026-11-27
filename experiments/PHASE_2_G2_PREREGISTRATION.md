# Phase 2 (G2) Pre-registration: two-arm, contact-driven layer turns of the free-core M7 cube

**Status: DRAFT revision 1, NOT IN FORCE (2026-11-27).**
- Revision 0 (P-104) was a plan. Revision 1 states what the code does (`experiments/E8_scored_g2/` at the commit that
  introduces this revision), with every limit fixed from the pilots (P-118, P-119).
- Before it is in force: independent reviews (one reviewer subagent per round, P-121) until "ACCEPTABLE AS IS", then
  the user's approval recorded in `docs/DECISION_LOG.md`.
- **Freeze procedure:** the freeze commit sets `FROZEN = True` in `run.py`; it contains no other code change. The
  scored run refuses to start otherwise, and refuses uncommitted changes in the frozen paths (§6).
- Gate: `docs/VALIDATION_PLAN.md` G2. **Pass** = repeatable physical turns with prescribed classical controllers; no
  RL. Mapping in §5.
- **Labels:** `FACT`, `INFERENCE`, `ASSUMPTION`, `PROPOSAL`.

## 0. Disclosure (read first)
1. **Everything below was designed after unscored results on rehearsal and pilot seeds.** Only the scored seeds
   (30000–30999) are independent of the design.
   - **D16** (P-98 … P-101): a stand-in holder failed for fixture reasons.
   - **D17** (P-102, P-103): the real G2 holder and a turner on a compliant mount, 40/40 moves.
   - **C1/C2 pilot** (P-106): 90/90 moves; C1 chosen (P-107).
   - **D18** (P-108, P-110): two xArm7 arms; the drop-away stand.
   - **Jam work:** the lag guard failed (P-111); the torque budget is infeasible at ±20 % model error (P-113); the
     **wrist F/T sensor guard** was adopted (P-114).
   - **Arm B gain tuning** (P-115): K_P 4000.
   - **Pilot P-5** (P-118): 56/56. The F/T stop was set at 0.8 N·m from it (P-119).
2. **Move strings:** U, U′, U2 and U U′ U2 U′ U were run many times in rehearsals. The 20 random 10-move sequences are
   drawn from the scored seeds and are new.
3. **First-turn torque tail (`FACT`, P-117, P-118).** With the ±1° start misalignment, the first turn's F/T τ_z
   reached 0.47 N·m once (smoke) and at most 0.35 in 30 pilot turns. The stop is 0.8 N·m.
   - `INFERENCE`: the tail is estimated from about 35 first turns. A false stop in a scored trial is a failure, not an
     excuse.
4. **The G1 rig's grip was capped at about 11.5 N** (G1 report §3 item 12). G2 is the first squeeze test above that.
5. **Inherited and new `ASSUMPTION`s:**
   - M7's clearance (0.05 mm), rounded edge (R 2.5 mm), uncalibrated turning torque, and core mass and inertia
     (1.7 g, 2e-8);
   - pad friction μ 0.8; pad compliance as a contact time constant (0.01 s);
   - the F/T sensor's size (75 × 35 mm, 0.6 kg) and noise (0.01 N·m);
   - the Menagerie xArm7 joint friction, damping and armature;
   - the G2 linkage is closed by soft constraints, and the fingertips splay 0.25–0.9° under load.
6. **Simulation only.** Nothing here establishes sim-to-real transfer.

## 1. System under test (frozen; `experiments/D18_two_arm_m7/two_arm.py`, `layout.py`)
| Part | Configuration | Source |
|---|---|---|
| Cube | **M7** as G1-scored: B1, L0 magnets (unchanged `MagnetSystem`), rounded R 2.5 mm, gap 0.05 mm, NoSlip 10, dt 0.5 ms. **Free core** (free joint, 1.7 g) | P-95, P-97 |
| Arms | Two xArm7 1305+ (`P2_robot_model/build_model.py`), actuator gravity compensation. Arm A at the origin; arm B at (1.0, 0, 0) m, yawed 180°; table z = 0 | P-96, P-108 |
| Cube pose | Centre (0.5, 0, 0.30) m nominal; cube +z (U) = world +x | P-108 |
| Grippers | Two Gripper G2 models (four-bar, tendon drive). `set_grip_force` calibrated at 57 mm; **20 N** on both | P-97 |
| Arm A fingertip | **One flat box per finger**, 30 × 30 × 4 mm, from the D end over D and 11 mm of E | P-97, D17 |
| Arm B fingertip | **C1**: one box per finger, 25 × 14 × 4 mm, distal end 14 mm inside the U face | P-107 |
| Fingertip contact | μ 0.8, condim 4, rig-pad solimp, **time constant 0.01 s** | P-105 |
| Arm B wrist | **UFACTORY 6-axis F/T sensor** (modelled), between the flange and the gripper; MuJoCo force/torque sensors at the interface; sampled at 200 Hz, + N(0, 0.01 N·m) noise from `default_rng(29000)` | P-114 |
| Stand | Actuated stand under D and E only (33 × 40 mm), stiff slide servo; drops 30 mm after arm A's grasp | P-109, P-110 |
| Visuals | Stickers and the room are off in scored runs (physics-identical, P-110, P-112) | |

## 2. Procedure and controllers (classical; `two_arm.py`)
**Inputs allowed:**
- Controllers read only robot joint states, the kinematics derived from them, the F/T sample, commanded targets and
  time. **Never cube or cubie state.**
- The targets come from the nominal cube pose (layout IK).
- Test: perturbing every cube joint state leaves arm B's control outputs bit-identical
  (`test_controllers_ignore_cube_state`, with a positive control).

**Setup (before t0, logged setup writes):**
1. Arm A at its IK grasp pose, gripper open; arm B at its pre-grasp pose (gripper base 40 mm outside the grasp along
   the axis), gripper open.
2. The cube rests on the stand at the seeded start offset and misalignment (§3).

**Start sequence (gravity on throughout; part of the trial):**
1. Settle 0.3 s.
2. Arm A ramps closed at 0.5 rad/s (2 s), then 0.3 s.
3. The stand lowers 30 mm over 0.5 s, then 0.5 s.
4. Arm B approaches 40 mm along the axis over 1 s, then 1 s.

**Arm A:** joint position servos hold the IK pose; the gripper stays closed.

**Arm B, joints 1–6:** torque control, a Cartesian impedance at the gripper base.
- Position: K_P 4000 N/m, D_P 60 N·s/m. Axis direction: K_R 50 N·m/rad, D_R 2 N·m·s/rad. Weak posture (2 N·m/rad)
  and joint damping (1 N·m·s/rad).
- An integral term (KI_P 8000, KI_R 200, clamped at 25 N / 3 N·m) is **active only while the fingers are open**.
- Torques are clamped to the URDF peak efforts.

**Arm B, J7 (roll):** torque control.
- τ = clip(ff + 800·(q_c − q) + 80·(q̇_c − q̇), ff ± B).
- ff = 2·q̇ (measured) + 1·tanh(q̇_c / 0.02).
- B = 2 + 0.2·(|2·q̇| + 1) N·m.

**Per move:**
1. Settle 0.3 s (fixed; no cube-state rest check).
2. Integral off; ramp arm B closed (0.5 rad/s), then 0.3 s.
3. Roll on a cosine ramp, 1 s per quarter turn. U2 is always −180° about U's normal; U′ is +90°.
4. Hold 0.3 s; open; 0.3 s; integral on.
5. Roll back to the start angle (1 s, open).

**Guards during a roll:**
- **F/T stop:** |τ_z| > **0.8 N·m** on two consecutive 200 Hz samples.
- **Stall rule:** J7 following error > 2° for 20 ms.
- Either freezes the roll at the current angle; the move then opens as usual.
- A guard stop is a failure of that move in turn trials (§4), and the intended outcome in G2-7 jam trials.

## 3. Trials (`experiments/E8_scored_g2/run.py`, `build_jobs`; 138 trials)
**Start draw (`trials.start_draw(seed)`):**
- Cube offset uniform ±1 mm per axis.
- Per-face setup misalignment uniform ±1° (6 faces, as G1), from `default_rng(seed)`.
- The cube starts solved.

| ID | Trials | Seeds | Kind | Scored |
|---|---|---|---|---|
| G2-1 | 20 × hold 60 s (after the start sequence, arm B open at pre-grasp) | 30000–30019 | hold | yes |
| G2-2 | 20 × U, 20 × U′ | 30100–30119, 30120–30139 | seq | yes |
| G2-3 | 20 × U2 | 30200–30219 | seq | yes |
| G2-4 | 20 × U U′ U2 U′ U; 20 × 10 random moves from {U, U′, U2} (`default_rng(seed + 500000)`) | 30300–30319, 30320–30339 | seq | yes |
| G2-5 | C1 vs C2 (done, P-106) | – | – | no (decided P-107) |
| G2-6 | U U′ U2 U′ U with one change: K_P 2000; K_P 6000; pad μ 0.5; grip 10 N; grip 30 N; grip 50 N (stress); rigid pads (0.001 s); extra cube offset (0, 2, 2) mm | 30600–30607 | sens | **reported only** |
| G2-7 | 2 each of 5 negative cases (§4.3) | 30700–30709 | neg | yes |
| G2-8 | throughput: real-time factor from every record (`sim_time_s / wall_s`) | – | – | reported only |

- Scope: U-family turns from one stabiliser grasp. No regrasp or other faces (G4; P-105).
- One trial per spawned process.

## 4. Criteria (stated before any scored data)
### 4.1 Turn trials (G2-2, G2-3, G2-4; `trials._seq_reasons`)
A trial passes only if **all** of the following hold:
- **Run integrity:** the cube is solved at t0; no abort (no numerical failure or edit-audit violation); every move is
  recorded; the final state matches the oracle.
- **Every move:**
  - `ok_oracle`: the observed move (readout → logical oracle) equals the commanded move.
  - `ok_turn_error`: |mean layer rotation − nominal| ≤ **2°**, in the core frame.
  - `ok_drift`: rotation of the non-target cubies about the face axis ≤ **1°**.
  - `ok_penetration_cubie`: deepest cubie–cubie contact ≤ **0.5 mm** (fingertip–cubie penetration is reported, not
    judged).
  - `ok_causal`: the turner fingertips' contact force exceeds 0.5 N before the U layer's angular speed relative to
    the core exceeds 5°/s.
  - `ok_no_nonpad_cube_contact`: no robot geometry other than the four fingertips touches a cubie.
  - `ok_no_arm_arm`: no contact between arm A and arm B geometry.
  - `ok_no_table`: no robot–table contact (bases excluded).
  - **No guard stop.**
  - Core slip relative to arm A's gripper ≤ **1 mm**.
- **Reported, not judged:** J7 actuator torque; fingertip torque on the layer; F/T peak; pad penetration; actuator
  saturation count (actuators are clamped to their limits by construction); grasp and tracking errors; core rotation.

### 4.2 Holds (G2-1; `trials.run_hold`)
Pass if all hold: no abort; the cube is solved at t0 and at the end; core slip ≤ **1.0 mm** and rotation ≤ **1.0°**
relative to arm A's gripper over 60 s; no non-fingertip, arm-arm or table contact.

### 4.3 Negative cases (G2-7; `trials.neg_outcome`)
A negative trial passes when the fault is handled:

| Case | Fault | Pass when |
|---|---|---|
| `two_layer` | Turner inserted 25 mm (6 mm across the U/E boundary) | the turn trial does **not** pass cleanly (guard stop or a failed check) |
| `offcentre` | Cube 5 mm sideways | always (reported: a clean turn or a detection are both acceptable) |
| `collision` | Turner driven 34 mm deep, into arm A's fingertips | robot contact is detected (arm-arm or non-fingertip cube contact) |
| `open_midturn` | Arm B opens halfway through the roll | the turn trial does not pass cleanly |
| `jam` | A world-fixed block above the top face beside the U layer | an F/T or stall stop, with core slip ≤ **0.5 mm** |

A solver failure is never a pass: an aborted trial fails §4.1 (unit test `test_seq_reasons`).

### 4.4 Verdict (`analyze.py`)
- **INVALID:** no manifest; a record that does not parse; a ledger SHA-256 mismatch; a record without a ledger
  line; a ledger line or file the run procedure does not produce (`foreign_files`); an orphan temporary file at
  verdict time.
- **INCOMPLETE:** a manifest trial without a record.
- **PASS:** every scored trial (G2-1, -2, -3, -4, -7: 130 trials) passes (**zero tolerance**, P-105).
- **NOT PASSED:** otherwise.
- **Reported:**
  - an exact Clopper–Pearson 95 % upper bound on the per-trial failure rate of the 100 turn trials;
  - per-move maxima; the hold, negative and G2-6 tables; G2-8.

## 5. Mapping to VALIDATION_PLAN G2
| G2 checklist item | Evidence |
|---|---|
| Distinct xArm7 instances with validated tool frames, limits, collision geometry | layout IK (P-108, ≥ 25.8° joint margin); arm-arm and table contact checks in every trial; G2-7 `collision` |
| Approved passive fingertip candidate accurately mounted | P-97 / P-107 fingertips; `ok_no_nonpad_cube_contact` |
| Stable classical stabilisation against a physical rotating layer | G2-1 holds; per-move core slip and drift in G2-2 … G2-4 |
| Contact-driven 90° and 180° turns across multiple starts, no unintentional adjacent-layer rotation | G2-2 … G2-4 (`ok_oracle`, `ok_turn_error`, `ok_drift`, `ok_causal`) |
| Collision/force/clearance logs and sensitivity to alignment and friction | per-move logs; G2-6; G2-7 |

## 6. Run integrity (`run.py`; as the G1 runners)
**Results and first start:**
- Results go to `experiments/E8_scored_g2/results/`.
- The first start requires an empty folder and writes `MANIFEST.json` (trial list, environment, frozen paths,
  commit) by atomic link.
- Every later start is a resume.

**Logs and records:**
- `STARTS.txt`: each start, with its resume plan logged before it is applied.
- `LEDGER.txt`: one line per record, with its SHA-256.
- Records are written by the parent only: temporary file, fsync, `os.link` (never overwritten), ledger line.

**Resume:**
- Refuses if the trial list, an environment field (MuJoCo, NumPy, SciPy, Python, CPU) or a frozen path differs from
  the manifest, or if foreign files exist.
- Moves orphan temporary files to `_interrupted/`.
- Reconciles records without a ledger line.

**Errors and interruptions:**
- A harness exception becomes a failing record.
- MemoryError, OSError, the magnet-availability refusal or a broken worker pool are interruptions (exit 3); resume
  with the same command.
  - The P-115 incident (a transient refusal under 8 parallel processes) is handled this way.
- One trial per spawned process (`max_tasks_per_child = 1`).

**Location and freeze:**
- Location check: no path in a OneDrive folder; the `rubiknetic` package from this repository.
- **Frozen paths:** this file; `experiments/E8_scored_g2/{run,trials,analyze}.py`;
  `experiments/D18_two_arm_m7/{two_arm,layout}.py`; `experiments/D17_real_holder_m7/{hold,turn}.py`;
  `experiments/P2_robot_model/build_model.py`; `experiments/E7_scored_m7/run.py`;
  `src/rubiknetic/cube_physics/{m1_model,magnets,rig,readout}.py`; `src/rubiknetic/cube_logic`.
- Scored starts are refused while `FROZEN = False` or with uncommitted changes in these paths.

**Environment:** WSL Ubuntu-24.04, `~/.venvs/rubiknetic` (Python 3.12.3, MuJoCo 4.0.1, NumPy 2.5.4, SciPy 1.18.1).
**8 workers** (G2-8: about 0.09× real time per trial process; the 138 trials take about 1.5–2.5 h).

**Evidence before the freeze (P-6):**
- 21 unit tests pass (`tests/test_scored_g2.py`).
- `selfcheck.py` reproduces three pilot records exactly (P-120).
- A smoke run killed after a record link and resumed gives PASS, with the ledger reconciled
  (`smoke_2_kill_resume/`, P-120).

## 7. Prerequisites
| # | Item | Status |
|---|---|---|
| P-1 | C1 vs C2 pilot and choice | done (P-106, P-107) |
| P-2 | Two-arm layout; gravity-on grasp from a support | done (P-108, P-110) |
| P-3 | Arm B controller; jam protection; gains | done (P-108, P-114, P-115) |
| P-4 | Runner, trials, verdict, tests | done (P-116, P-117) |
| P-5 | Pilots; limits | done (P-118, P-119) |
| P-6 | Self-check; smoke with kill and resume | done (P-120) |
| P-7 | Independent reviews until "ACCEPTABLE AS IS" | **open** |
| P-8 | The user's approval; freeze commit (`FROZEN = True`); DECISION_LOG | **open** |

## 8. Limitations (to be stated with any G2 result)
1. **Simulation only;** every `ASSUMPTION` of §0.5 applies.
2. **Scope:** U-family turns from one grasp. No regrasp, no other faces, no camera state (G4, G5).
3. **Controllers:** the controllers are first designs, tuned on two pilot seeds. K_P 4000 is at the edge of the tuning
   grid.
4. **F/T sensor:** the sensor model is assumed (size, noise; no offset drift, temperature or bandwidth limit).
5. **Joint model:** the J7 and arm joint friction values are Menagerie's.
6. **Starting conditions:** the start sequence lowers the stand by command, and the cube's start pose is drawn within
   ±1 mm / ±1°. Larger placement errors are untested (except G2-6 and `offcentre`).
7. **Seeds:** one seed per scored trial. The negative cases have 2 trials each.
