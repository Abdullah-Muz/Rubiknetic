# Phase 2 (G2) Pre-registration: two-arm, contact-driven layer turns of the free-core M7 cube

**Status: DRAFT revision 0, NOT IN FORCE (2026-11-26); §8 answered (P-105).**
- This is G2 step 3 (user: "1 2 than 3"; P-95, P-97). Nothing here is fixed.
- Before it can be fixed: the open items of §7 must be built or piloted, the questions of §8 answered, reviews run
  until "ACCEPTABLE AS IS" (as M5 and M7), and the user's approval recorded in `docs/DECISION_LOG.md`.
- Gate: `docs/VALIDATION_PLAN.md` G2.
  - **Pass** = repeatable physical turns with prescribed classical controllers; no RL.
  - The five G2 checklist items map to §3 (table in §5).
- **Labels:** `FACT`, `INFERENCE`, `ASSUMPTION`, `PROPOSAL`. Every number marked **[pilot]** is set from pilot data
  before the text is fixed (VALIDATION_PLAN threshold policy), never after scored data.

## 0. Disclosure (read first)
1. **What is already known (`FACT`; all UNSCORED rehearsals, 2026-11-26).** Their seeds and sequences are not
   independent of this plan.
   - **D16** (P-98 … P-101): free-core M7 held by a world-fixed slide-pad stand-in. It failed for fixture reasons:
     jitter of light pads, and axial ejection with damped pads.
   - **D17 stage A** (P-102): xArm7 + G2 model, P-97 stabiliser fingertip, P-04 orientation. It holds the free cube at
     10–50 N with slip ≤ 0.18 mm over 5 s.
   - **D17 stage B** (P-103): a second G2 on a compliant mount turns U. Sequence U U′ U2 U′ U, 8/8 runs and 40/40 moves
     pass G1-style checks. Max turn error 0.28°, drift 0.33°, cubie penetration 0.14 mm, roll torque ≤ 0.25 N·m.
   - The design choices below (single fingertip box, grip from the D end, rest-wait, ramped closing, 14 mm turner
     insertion) were made **after** those results.
2. **The G1 rig's grip was capped at about 11.5 N** (D16-0; G1 report §3 item 12). G2 is the first test of squeeze
   above that.
3. **Inherited `ASSUMPTION`s:**
   - the M7 clearance (0.05 mm);
   - the rounded edge (R 2.5 mm);
   - the uncalibrated turning torque;
   - the core mass and inertia (1.7 g, 2e-8; D6);
   - pad friction (μ 0.8);
   - **pad compliance:** a contact time constant standing in for a 4 mm compliant layer. It decides the D/E load split
     (P-102).
4. **Model fidelity (`FACT`, P2 README):**
   - the G2 fingers and knuckles are the original gripper's geometry;
   - the inertials are not revision-specific;
   - the four-bar is closed by soft equality constraints. The fingertips splay 0.25–0.9° under 10–50 N, cause not
     identified.
5. **Simulation only.** Nothing here establishes sim-to-real transfer.

## 1. System under test (frozen configuration; PROPOSAL)
| Part | Configuration | Source |
|---|---|---|
| Cube | **M7** exactly as G1-scored: B1, L0 magnets, rounded R 2.5 mm, gap 0.05 mm, NoSlip 10, dt 0.5 ms. **Free core** (free joint, 1.7 g) | P-95, P-97, D17 |
| Arms | Two xArm7, revision 1305+, `experiments/P2_robot_model/build_model.py`. URDF peak efforts as limits (P-17, O-13 closed). Actuator gravity compensation | P-96 |
| Grippers | Two Gripper G2 models (four-bar, tendon drive). Force setting by `set_grip_force` (calibrated at 57 mm). Ramped closing at 0.5 rad/s | P2, R2-08 |
| Stabiliser fingertip (arm A) | **One flat box per finger**, 30 wide × 30 deep × 4 mm. **Gripped from the D end** (P-04): covers D and 11 mm of E; the U layer projects 27 mm beyond | P-97, D17 |
| Turner fingertip (arm B) | **C1** (P-107): one box per finger, 25 wide × 14 deep × 4 mm, insertion 14 mm by control. Contingency: C2 with a 5 mm shoulder (pre-close → seat → grip), if arm B's axial error exceeds about ±2 mm | P-03, P-97, P-106, P-107 |
| Fingertip contact | μ 0.8, condim 4, rig-pad solimp; contact time constant **0.01 s ("soft")** for scoring (§8 Q3, P-105); rigid 0.001 s in the G2-6 screen | P-97, D17, P-105 |
| Grip | 20 N on both grippers (scored); 10 / 30 N sensitivity; 50 N stress (reported only) | P-97, P-99 |
| Layout | **Both arms on one table facing each other, cube axis horizontal** (§8 Q2, P-105). Arm A grips from the D end, arm B from the U end, coaxially; base positions and poses designed in §7 P-2 | VALIDATION_PLAN G2 item 1, P-105 |

## 2. Controllers (classical; PROPOSAL)
**Inputs allowed:**
- Controllers read only robot joint states, gripper drive angles, commanded targets and time.
- **They never read cube or cubie state** (privileged truth). The cube state is used only by the checks.
- Cube pose for planning comes from the fixed nominal placement, not from the simulator.

**Arm A (stabiliser):**
1. Joint-space approach to the pre-grasp pose (speed-limited, R2-17).
2. Ramped gripper closing (0.5 rad/s).
3. Hold (joint position servo + gravity compensation).

**Arm B (turner):**
1. Joint-space approach to the coaxial pre-grasp pose.
2. A Cartesian impedance hold during grasp and turn; gains **[pilot]**, starting from D17's mount (2000 N/m,
   60 N·s/m).
3. Ramped closing.
4. **J7 roll** on a cosine ramp, 1 s per quarter turn, through J7's position servo with a torque limit **[pilot]**
   (D17: ±1 N·m).
5. Open, retract, roll back.
6. Turn completion is judged from **J7's angle** (R2-07), not from cube state.

**Rest rule:** before each turn, wait until arm B's joint velocities and gripper drive are at rest, at most 2 s.
D16b's cube-velocity rest check reads cube state, so it is not allowed in the scored controller. It is replaced by a
fixed settle time **[pilot]**.

**Mounting:** the arm bases are placed by the scene file. There is no simulated table approach or handoff (Phase 4).

## 3. Trials (PROPOSAL; counts [pilot] from cost)
| ID | Test | Starts | Scored |
|---|---|---|---|
| G2-1 | **Stabilisation under load:** arm A holds while arm B turns (inside every turn trial), plus a 60 s hold without turning | in every trial + 20 holds | yes |
| G2-2 | **Quarter turns**, both directions (U, U′) | 20 + 20 | yes |
| G2-3 | **Half turns** (U2), both roll directions | 20 | yes |
| G2-4 | **Sequences:** U U′ U2 U′ U, and 10-move random U-family sequences | 20 + 20 | yes |
| G2-5 | **Turner fingertip comparison** C1 vs C2 under matched poses, grip, friction and solver | pilot (§7 P-1) | reported, decides P-1 |
| G2-6 | **Sensitivity:** grasp offset (±1 mm lateral, ±1 mm axial, ±1° about the axis), pad μ 0.5 / 1.0, grip 10 / 30 N, 50 N stress, pad contact time constant | 1–2 per setting | reported (E1-7 style screen) |
| G2-7 | **Negative tests** (phase plan): (a) turner inserted across the U/E boundary (two layers) must fail or be detected; (b) off-centre grasp (5 mm) → torque, slip and safe stop; (c) arm-arm or arm-cube non-pad collision → rejected; (d) turner opens mid-turn → slip and discontinuity detected; (e) a solver failure is rejected, never a pass | 2 each | yes (correct detection) |
| G2-8 | **Throughput:** two arms + M7 on CPU, steps/s and real-time factor | benchmark | reported |

**Starts:**
- **Seeds:** scored 30000–30999; pilot and rehearsal 29000–29999. Both ranges are unused so far: G1 used 17000–17739,
  the smoke 18000, D16 21000–21003.
- **Per seed:** a legal scramble state of the cube (colours only; same physics), a setup misalignment ±1° per layer
  (as G1), and a grasp offset within the controller's nominal tolerance **[pilot]**.
- Only U-family moves: one stabiliser grasp, no regrasp or role swap (that is Phase 4, G4; §8 Q5, P-105).

## 4. Criteria (stated before any data; G1 values unless marked)
**Categorical (all trials; VALIDATION_PLAN cross-cutting):**
- no edit-audit violation;
- no numerical failure;
- legal state;
- observed move = commanded move (oracle on the readout);
- no hidden actuator on the layer;
- controllers never read cube state (code audit and a test);
- **no robot geometry other than the fingertips touches the cube**;
- **no arm-arm, arm-base or self collision**;
- joint torques within URDF peak limits (flagged, never capped silently).

**Per move:**

| Criterion | Limit | D17 pilot max |
|---|---|---|
| Turn error | ≤ 2° | 0.28° |
| Non-target drift (D, E relative to the core) | ≤ 1° | 0.33° |
| Cubie-cubie penetration | ≤ 0.5 mm | 0.14 mm |
| Causality: turner fingertip force > 0.5 N before the U layer exceeds 5°/s relative to the core | as G1, relative to the core | passed |
| Core slip relative to arm A's gripper, per move | ≤ 1 mm **[pilot]** | 0.14 mm |
| Turning torque (J7) | reported, never judged (uncalibrated) | 0.25 N·m |

**Pad penetration** (fingertip into cubie) is reported, not judged: it is the stand-in for pad compliance.

**60 s hold (G2-1):**
- core slip ≤ **[pilot]** mm;
- rotation ≤ **[pilot]**°;
- the pads stay on D and E only.

**Pass logic (§8 Q4, P-105):**
- **Zero tolerance** on the scored trials (as G1's Option A). Every scored trial passes every criterion.
- G2-7 passes when every negative case is detected or safely stopped.
- G2-5, G2-6 and G2-8 are reported only.

## 5. Mapping to VALIDATION_PLAN G2
| G2 checklist item | Evidence |
|---|---|
| Distinct xArm7 instances with validated tool frames, limits, collision geometry | §7 P-2 layout; R2-12 tool frame; a frame/limit test suite; G2-7c |
| Approved passive fingertip candidate accurately mounted | §7 P-1 (C1/C2 choice), R2-13 mount, R2-24 single flat pad |
| Stable classical stabilisation against a physical rotating layer | G2-1 |
| Contact-driven 90° and 180° turns across multiple starts, no unintentional adjacent-layer rotation | G2-2 … G2-4 (drift criterion) |
| Collision/force/clearance logs and sensitivity to alignment and friction | per-move logs, G2-6, G2-7 |

## 6. Requirements carried into G2 (from P-97 §4, updated by D16/D17)
- **Kept:** R2-01, 02, 03, 05, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 23.
  - R2-05 (0.5° completion) is now judged on J7 only. The layer criterion is §4's 2°.
- **Dropped:** R2-04, 06, 20, 21, 22 (M2-specific).
- **Added by P-97:**
  - free-core M7;
  - M7 numerical bounds (dt ≤ 0.5 ms, NoSlip 10, gap ≤ 0.05 mm);
  - magnet-model validity reported;
  - drift ≤ 1°.
- **Added by D16/D17:**
  - **R2-24: one flat fingertip pad per finger** (the stock G2 pads mis-touch);
  - **R2-25: the stabiliser grips from the D end (P-04)**, with the U layer clear of arm A's fingers and knuckles;
  - **R2-26: pad compliance stated and swept** (it sets the D/E load split);
  - **R2-27: the rig grip cap is not inherited:** the actual squeeze is measured in every trial.

## 7. Prerequisites before this text can be fixed (open)
| # | Item | Kind |
|---|---|---|
| P-1 | ~~C1 vs C2 turner pilot (G2-5), then the user's choice~~ **Done:** P-106 pilot, C1 chosen (P-107) | pilot + decision |
| P-2 | **Two-arm layout:** base positions, cube pose, IK for both grasps, collision clearance. Arm B as an xArm7, replacing D17's compliant mount | design + build |
| P-3 | **Arm B controller:** Cartesian impedance + J7 roll, with gains and torque limit from pilots. The settle time replaces the cube-state rest check | build + pilot |
| P-4 | **Runner and analysis** in the M5/M7 style: manifest, ledger, resume, environment check, audit. Tests including the controller-reads-no-cube-state test | build |
| P-5 | **Pilots** fixing every **[pilot]** number: slip limits, 60 s hold limits, grasp-offset tolerance, trial counts from cost | pilot |
| P-6 | Self-checks reproducing pilot records; a smoke run with a forced kill and resume | build |
| P-7 | **Independent reviews** (one reviewer subagent per round, as P-86 Q8) until "ACCEPTABLE AS IS" | review |
| P-8 | The user's approval; DECISION_LOG entry; code and text frozen | decision |

## 8. Questions for the user (recommended option first; **all answered 2026-11-26, P-105: the recommended option each time**)
1. **Order of the remaining work:** P-1 (C1/C2 pilot) → P-2/P-3 (real arm B and layout) → P-4 … P-8?
2. **Layout:** both arms on one table facing each other, cube axis horizontal (the natural P-04 pose), or arm A
   pointing down as in D17 with arm B below?
3. **Fingertip contact model for scoring:** "soft" (0.01 s; more even D/E load, closer to a compliant pad), "rigid"
   (0.001 s), or both as separate scored arms?
4. **Pass logic:** zero tolerance (every scored trial passes), or a pre-registered success fraction with a confidence
   bound?
5. **Scope:** U-family turns only (one grasp) for G2, leaving regrasp and other faces to G4 (Phase 4)?
