# Phase 4 (G4) design: cube handoff between the two xArm7 arms (DRAFT for the user's decisions)

**Status: DESIGN DRAFT, 2026-11-28. Documents only.** Nothing here has been simulated, implemented or validated. No
code exists for any handoff, abort rule or experiment described below. Every number marked `PROPOSAL` is a starting
value to be checked by pilots, not a result.

**Labels:**
- `FACT`: read from a committed file (cited) or plain arithmetic on cited values.
- `INFERENCE`: this document's reasoning from facts.
- `ASSUMPTION`: taken without evidence.
- `PROPOSAL`: a suggestion for the user to accept or reject.
- `DECISION`: a choice the user has already made (with its DECISION_LOG id). `DECISION NEEDED` marks open choices.

**Inputs read:**
- `experiments/D22_face_reach/README.md`, `results/tour_clearance.json` (D22);
- `docs/research/G4_BIMANUAL_REGRASP_LITERATURE_2026-11-28.md` (L; source ids G4-xx, S01);
- `experiments/PHASE_2_G2_PREREGISTRATION.md` §0–§5 (G2-PR), `experiments/E8_scored_g2/G2_REPORT.md` (G2-R), the
  scored G2-7 `two_layer` records in `experiments/E8_scored_g2/results/G2-7/`;
- `experiments/D23_admittance_q2/README.md` (D23);
- `experiments/E7_scored_m7/G1_REPORT_M7.md` and `experiments/PHASE_1_M7_PREREGISTRATION.md` (G1, E1-5/E1-5s);
- `phases/PHASE_4_BIMANUAL_AUTONOMY.md`, `docs/VALIDATION_PLAN.md` G4, `docs/SYSTEM_ARCHITECTURE.md`, `CLAUDE.md`;
- `experiments/P2_robot_model/build_model.py` (`set_grip_force`), `experiments/D18_two_arm_m7/two_arm.py`.

**Constraints carried over (`DECISION` / `FACT`):**
- Two xArm7 arms in the G2 layout, MuJoCo, M7 cube with dynamic cubie contacts (locked, CLAUDE.md).
- G2 tooling: arm A P-97 stabiliser pads 30 × 30 × 4 mm (P-97); arm B C1 turner 25 × 14 × 4 mm (P-107); wrist F/T on
  arm B only (P-114); 20 N grip on both arms (P-97).
- Regrasp and other faces were deferred from G2 to G4 (P-105).
- Controllers read robot signals, targets and time only, never cube or cubie state (G2-PR §2; architecture data
  channels). Cube state is read only offline on the audit channel for judged checks.
- No state edits, hidden reorientation or resets; failures go to bounded retry, replan or stop (VALIDATION_PLAN G4;
  SYSTEM_ARCHITECTURE state machine).
- Mechanical choices are the user's (CLAUDE.md). This document proposes; it does not change tooling.

---

## 1. Starting facts

### 1.1 Why handoffs are needed (D22)
- `FACT` (D22 §2): from G2's grasp only **U** can be turned. Arm A's P-97 pads clamp D, R, L and the D-layer corners.
- `FACT` (D22 §3): fewest handoffs for a tour that makes all six faces turnable:
  - **FIXED** (G2 tooling; A only holds/stabilises, B only turns): **10 handoffs + 1 reorientation**. B holds the cube
    during each handoff by a one-layer C1 grip.
  - **SYM** (either arm can turn or stabilise): **5 handoffs + 1 reorientation**. Needs a tool change or a
    dual-purpose fingertip, which is not designed.
- `FACT` (D22 §3, `matrix.py`): face-to-face cost is always exactly 2 handoffs in FIXED and exactly 1 in SYM-coax.
- `FACT` (D22 §4, `tour_clearance.json`):
  - Arm B's joint-limit margin at the +x pose is 19.7° (19.08° in the committed G2 record with the F/T sensor). In
    FIXED this pose recurs at every handoff where B holds.
  - Both-closed arm–arm clearance on the coax tours: FIXED 23.4 mm or 60 mm (the check's cap); SYM 18.2–19.5 mm.
    SIDE grasps fall to 1.1 mm.
  - The reorientation (180° FIXED, 120° SYM) was checked at its end poses only, not along a path.
  - SIDE grasps, B's one-layer hold and the SYM tooling are mechanically unassessed.

### 1.2 What G2 validated and did not (G2-R)
- `FACT`: 128/128 scored trials; 100/100 turn trials, 360 moves; holds 20/20 over 60 s with core slip ≤ 0.16 mm and
  rotation ≤ 0.34° relative to arm A's gripper (G2-R §5).
- `FACT`: during the G2-1 holds, arm A alone held D + E and **U hung through the mechanism** (G2-PR §3: arm B open at
  pre-grasp). That is the only validated "layer hangs from a grip" condition.
- `FACT`: G2 scope excluded regrasp, other faces and camera state (G2-R §6 item 2). Starts were within ±1 mm and ±1°
  per face (G2-R §6 item 5).
- `FACT`: G2-7 `two_layer` (arm B's C1 inserted 25 mm, 6 mm across the U/E boundary, while arm A held): in both scored
  records, 0 arm–arm contacts, 0 non-fingertip robot–cube contacts, cubie penetration ≤ 0.07 mm; the F/T stop fired at
  1.10–1.13 N·m after 3.4–3.7° of roll (`results/G2-7/two_layer_s30700.json`, `_s30701.json`).

### 1.3 Signals a robot controller may use
| Signal | Arm | In simulation | On hardware | Use here |
|---|---|---|---|---|
| Joint positions, velocities; tool pose by FK | A, B | yes | yes | tracking errors, retreat checks |
| 6-axis wrist F/T, 200 Hz | **B only** | MuJoCo force/torque sensors + N(0, 0.01 N·m) on torque (G2-PR §1); D23 added 0.1 N per force axis (`ASSUMPTION`) | official UFACTORY sensor (P-114) | contact witness, internal force, load transfer, slip |
| Gripper aperture (finger joint position) | A, B | yes | **position feedback only** (S22, `PHASE_0_SOURCE_REGISTER.md`) | grasp presence, wedge/miss detection |
| Commanded targets, time | A, B | yes | yes | phase sequencing |
| Joint torque estimates | A, B | actuator forces | current-based estimates, accuracy undocumented (`CONTACT_AND_RL_FINDINGS.md` C03, Q4) | **gross collision only** |

- `FACT`: joint-torque estimates are too coarse for fine contact on this task. About 0.3 N·m on the layer sits against
  about 6 N·m of joint losses (`G2_JAM_DETECTION_RESEARCH_2026-11-26.md`). The J7 lag guard (P-111) and the torque
  budget (P-113) both failed; the F/T guard was adopted (P-114).
- `INFERENCE`: when arm A holds the cube alone, the only robot signal about that grip is A's aperture. Arm B's F/T is
  the only force witness, and it witnesses every handoff, because every handoff involves both arms.
- Contact lists, cube and cubie poses, the oracle readout and magnet statistics are **audit-channel only**: they judge
  trials offline and never feed a controller or an abort rule.

### 1.4 Load estimates (`FACT` parameters, `INFERENCE` arithmetic, static)
- Cube mass ≈ 26 × 3.4 g + 1.7 g core ≈ 90 g, weight ≈ 0.88 N (`m1_model.py` `cubie_mass` 3.4 g, itself an
  `ASSUMPTION`; core 1.7 g, G2-PR §0.6). One layer of 9 cubies ≈ 0.30 N; D + E (17 cubies + core) ≈ 0.58 N.
- **G2's validated hang** (U from A's grip): shear 0.30 N across the U/E interface, moment ≈ 0.30 N × 9.5 mm ≈
  0.003 N·m.
- **FIXED one-layer hold** (whole cube from B's C1 on U, axis horizontal): shear 0.58 N across U/E, moment ≈ 0.58 N ×
  19.6 mm ≈ **0.011 N·m**. That is about 2× the shear and 4× the moment of the validated hang, carried through the
  cubie–core interlock.
- **B's C1 grip on the whole cube:** friction capacity 2 × 0.8 × 20 N = 32 N against 0.88 N (36×). The weight moment
  about the pad patch is ≈ 0.88 N × 21.5 mm ≈ 0.019 N·m. Its margin depends on the pad's torsional and distributed
  friction in the model (condim 4), which is **not checked** here.
- **Push during a position-controlled closure:** if A closes on a cube that B holds under impedance (K_P 4000 N/m,
  G2-PR §2), a lateral offset e gives ≈ 4 N per mm until B yields. With a one-layer hold this force reaches D + E
  through the mechanism: 2 mm of offset is about 14× the gravity shear.
- **Turning resistance for comparison:** G1 turner torque median 0.103 N·m, max 0.191 (G1 report); G2 first-turn F/T
  ≤ 0.373 N·m (G2-PR §0.3).

---

## 2. Handoff protocol (`PROPOSAL`)

### 2.1 Principles
1. **Never unsupported** (Phase 4 task 5). The giver does not start opening until the receiver's grip is confirmed by
   robot signals (§3, interlock I1).
2. **One compliant arm in every closed chain.** Arm B is always compliant (G2's Cartesian impedance); arm A is always a
   joint-position servo, as validated in G2.
   - When A gives and B receives, this is the Warsaw pattern: the holder is stiff and the catcher compliant (L §2.1,
     G4-04).
   - When B gives and A receives, the catcher is stiff and B's compliance absorbs A's placement error.
   - `INFERENCE`: in FIXED, A never needs force control, so no second F/T sensor is required for handoffs.
3. **Targets are nominal.** Every grasp target comes from the layout IK at the nominal cube pose (as G2). The only
   correction allowed is one estimated from robot signals: an offset estimated from B's F/T, or a guarded touch (§6 R3).
4. **Release by ramp, with abort** (G4-16: ramped release, slip-triggered abort and regrasp).
5. **Every phase has a time-out**, and every abort leads to a bounded retry or SAFE_STOP. Nothing is reset.

### 2.2 Phases
G = giver (holds at the start), R = receiver. Timings follow G2's where a counterpart exists (G2-PR §2: approach 40 mm
in 1 s + 1 s; close at 0.5 rad/s then 0.3 s; settle 0.3 s).

| Phase | Duration (`PROPOSAL`) | Giver controller | Receiver controller | Online abort checks (robot signals, §3) | Judged offline (audit channel) |
|---|---|---|---|---|---|
| **H0 Pre-check** | 0.5 s | holds (A: position servo; B: impedance, integral held while gripping) | parked at pre-grasp, 40 mm out along the grasp axis, open | B's F/T steady (std < 0.05 N over 0.3 s); if B is the receiver, F/T tare taken (free, open; as D23); giver aperture in band | cube solved and logical state recorded; per-cubie misalignment recorded (start of handoff) |
| **H1 Approach** | 1.0 s cosine + 1.0 s settle | holds | B: G2 impedance, integral on while open. A: position servo along an interpolated IK path | B receiver: \|ΔF\| < 2 N (no contact with the fingers open). B giver: \|ΔF\| < 1 N (A's open fingers must not touch the cube). Tracking error < 3 mm | no non-fingertip robot–cube, arm–arm, robot–table, robot–stand contact; cube motion relative to the giver ≤ 0.5 mm / 1° |
| **H2 Close** | close at 0.5 rad/s (≈ 1.6–2 s) + 0.3 s | holds; **if B is the giver, B lowers its translational stiffness normal to its own axis** (`PROPOSAL`: K_P 1000 N/m) so that A's first pad pushes the cube at ≈ 1 N/mm, not 4 | B receiver: integral off at the close (G2). A receiver: position servo, gripper force-closes at 20 N | receiver aperture at the end within the band (I1); B giver: a force pulse when A's pads land (contact witness), and its size gives an offset estimate e ≈ ΔF / K | cube displacement relative to the giver ≤ 1 mm / 2° (G2 per-move limits); logical state unchanged; cubie penetration ≤ 0.5 mm |
| **H3 Both-grip dwell and internal-force nulling** | 0.5 s dwell + ≤ 0.5 s nulling | A: position servo. B: impedance setpoint shifted, rate-limited (≤ 2 mm/s, total ≤ 2 mm, translation only), toward the pose where the horizontal F/T force (internal squeeze) is zero | same | horizontal internal force \|F_int\| ≤ 3 N after nulling (`PROPOSAL`; D23: G2 impedance hold mean 1.56 N, peak 2.03 N); if > 8 N at any time, abort (A3) | true inter-arm force reported (D23 metric); cube motion relative to each gripper ≤ 1 mm / 2° |
| **H4 Load transfer (ramped release)** | ≈ 1.0 s ramp + 0.5 s open + 0.3 s | **releases**: gripper target moves toward open at a slow rate through the contact zone, so the grip force decays over ≈ 1 s (§2.3); then opens to aperture ≥ 62 mm | holds at 20 N; B keeps its impedance | slip and load-transfer rules A4–A6 (§3) | **support continuity** (at least one gripper with both pads above 0.5 N normal force at every step); no drop; cube pose relative to the receiver ≤ 1 mm / 2°; logical state unchanged |
| **H5 Giver retreat** | 40 mm along its axis in 1.0 s + 0.3 s | B: impedance. A: position servo | holds | load-transfer check A7: B receiver, the F/T vertical force rises by the cube weight, 0.88 ± 0.3 N; B giver, it returns to the pre-handoff tare ± 0.3 N; receiver aperture still in band | no giver–cube contact after its pads leave; non-fingertip contacts none |
| **H6 Post-handoff settle** | 1.0 s | parked | holds | F/T steady; aperture in band | per-cubie misalignment at the end; growth from H0; magnets valid over the whole handoff |

- `INFERENCE`: about 9–10 s of simulated time per handoff, excluding transit to the next grasp. A FIXED tour has
  10 handoffs, about 95 s.
- The 1.0 s settle in H6 is chosen from G1 E1-5s: a free M7 layer started 3–8° off snaps back to within 0.5° within 1 s
  (`FACT`, G1 report; PHASE_1_M7_PREREGISTRATION E1-5s criterion; 20/20 scored).

### 2.3 How the ramped release is realised (`FACT` model facts, `PROPOSAL` method)
- `FACT` (`build_model.py`): the G2 gripper actuator is a position servo whose force is clamped by `forcerange`.
  `set_grip_force` sets that clamp (10–50 N) and is documented as "a model parameter set between episodes, not a state
  edit". The servo gain gives full force at 0.05 rad error (`GRIP_SAT_ERR_RAD`), so 20 N corresponds to 0.02 rad.
- `PROPOSAL`: release by moving the position target toward open at about 0.02 rad/s through the contact zone. The force
  then falls from 20 N to 0 over about 1 s, without changing any model parameter mid-trial. Afterwards the gripper opens
  at the normal rate. This matches the real G2's interface (position plus force-limited closing).
  - Lowering the force setting mid-trial (20 → 10 N, the G2's minimum) would be a mid-trial actuator-parameter change.
    It acts on the robot, not the cube, but it departs from the code's documented use. It is not proposed unless the
    user approves it and it is audited.
- Costanzo's 0.3 N/s (G4-16) would take 67 s from 20 N. It was used for an 82 g box held at 11 N with fingertip wrench
  sensors that Rubiknetic does not have. The rate here is a pilot parameter.

### 2.4 Checks reused from G2, and the new ones
Reused unchanged by import (frozen G2 files are never edited; the pilot builds its additions in memory, as D23 did):
- integrity: edit audit, model audit (nothing acts on a cube body), numerical failures (`trials._integrity_reasons`);
- magnets at every step and within the validated range (`_magnet_validity_reasons`);
- contact classes (`_contact_reasons`, `two_arm.CONTACT_KEYS`), cubie penetration;
- oracle readout, per-cubie misalignment, core pose.

New handoff checks (`PROPOSAL`; each needs code and unit tests before any pilot):
- **Support continuity:** the minimum number of supporting grippers at any step, from fingertip–cubie normal forces.
- **Cube pose relative to each gripper frame** (core and the clamped cubies), per phase. G2's `rel()` is relative to
  arm A's base, which was enough only while A never moved.
- **No drop:** core height change, plus no cube–table or cube–stand contact.
- **Logical continuity:** the oracle readout is unchanged across the handoff (no layer turned).
- **Hanging-layer behaviour:** the rotation of the hanging layer(s) relative to the held layer about the face axis, and
  layer separation (axial and tilt displacement of the held layer's cubies relative to the core). The reference values
  are G1's "pop ≤ 0.3 mm" and "radial change ≤ 0.5 mm" (PHASE_1_M7_PREREGISTRATION E1-2, E1-6b); these are reported,
  not judged, until pilots set limits.
- **Signal-versus-truth log:** each online signal (F/T load step, internal force, apertures) next to its audit-channel
  truth, so the abort thresholds can be calibrated and their false-alarm and miss rates reported.
- **Controller blindness tests**, as G2's `test_controllers_ignore_cube_state`: scrambling cube joint state leaves the
  handoff controller's and the abort logic's outputs bit-identical at a given robot state, with a positive control.

---

## 3. Abort and recovery rules (`PROPOSAL`; robot signals only)

Thresholds are starting values. They are calibrated on pilot seeds against the signal-versus-truth log before any
pre-registration.

| ID | Phase | Signal | Condition | Action |
|---|---|---|---|---|
| **I1** (interlock) | before H4 | receiver aperture; B's F/T contact witness | aperture within [56.5, 58.0] mm (nominal closure 57 mm, calibrated, G2-PR §1), **and** (B receiver) F/T shows a grip offset, or (B giver) the A-contact force pulse was seen in H2 | **the giver may not start H4 unless I1 holds**. Otherwise go to A2 |
| A1 | H1 | B's F/T; tracking error | unexpected contact (§2.2 H1 limits) or tracking error > 3 mm | stop; receiver back to pre-grasp; retry once |
| A2 | H2 | receiver aperture | below band (missed or partial grasp) or above band (pad on an edge, wedged or misaligned layer). `INFERENCE`: a rounded 56.95 mm layer turned by θ is wider by about 51.95 mm × θ (0.9 mm at 1°, 2.6 mm at 3°, 4.3 mm at 5°), so a wedged layer shows in the aperture | receiver opens, retreats 40 mm, retries once from H1; a second failure → SAFE_STOP |
| A3 | H2–H3 | B's horizontal F/T force | > 8 N (`PROPOSAL`; D23 stiff-servo roll peak 7.5 N) at any time, or > 3 N after nulling | B relaxes (lower K_P); if not below 3 N within 0.5 s, the receiver opens → A2 retry path |
| A4 | H4 | receiver aperture | changes by > 0.3 mm during the giver's release (the cube is moving between the receiver's pads) | **stop the release; the giver re-closes to 20 N** (G4-16 pattern); then the receiver opens, re-seats (H1–H3) and the release is retried once |
| A5 | H4, B receiver | B's F/T | step or rate anomaly: \|dF/dt\| > 20 N/s, or torque about B's axis \|τ_z\| > 0.1 N·m (hanging layers twisting) | as A4 |
| A6 | H4, B giver | B's F/T and aperture | B's aperture > 59 mm but B's F/T still carries the weight (> 0.5 N above tare): A is not holding | B re-closes; abort the handoff; A opens, retreats, retries once |
| A7 | H5 | B's F/T | load transfer outside 0.88 ± 0.3 N (B receiver), or not back to tare ± 0.3 N (B giver) | stop the retreat. If the weight is missing from both grips: **drop suspected → SAFE_STOP, no retry** |
| A8 | any | joint-torque estimate; arm tracking error | xArm-level collision detection or tracking error > 10 mm | SAFE_STOP |
| A9 | any | time | a phase exceeds 2× its nominal duration | as the phase's own abort |

**Recovery limits (`PROPOSAL`):**
- At most one retry per failure class per handoff, and at most 3 retries per tour.
- **SAFE_STOP:** whichever arm holds keeps holding; the other retreats to its pre-grasp pose; the logical state is
  marked `UNKNOWN` if any of A4, A5 or A7 fired (a layer may have moved); everything is logged.
- No recovery may read cube state or reset physics. In Phase 4 an `UNKNOWN` state ends the trial. Re-observation is a
  G5 capability (SYSTEM_ARCHITECTURE state machine).

**Limits of these signals (`INFERENCE`):**
- Arm A holding alone has no force witness. A slow loss of A's grip is visible only once its aperture leaves the band.
- With 0.1 N force noise (`ASSUMPTION`, D23) the 0.88 N load step has an SNR of about 9 per sample, and more after
  averaging. The 0.019 N·m weight moment is only about 2σ of the 0.01 N·m torque noise, so slip detection by torque is
  marginal. Force and aperture carry the rules; torque is a secondary signal.
- These rules detect gross events. Small slips (≤ 1 mm) are found only by the offline judged checks. Whether such
  slips accumulate over a tour has to be measured (§6 R3).

---

## 4. Layer alignment before handoffs and turns

**Evidence:**
- `FACT` (L §1 item 6, §4): every source treats alignment as a precondition. OpenAI aligns to 0.1 rad before a turn
  (S01); simulated tolerances are about 5° (G4-20, G4-21); hobby builds report that non-90° turns jam the next move
  (G4-27) and that misalignment "can turn the wrong layer" (G4-24).
- `FACT` (G1): a free M7 layer started 3–8° off snaps back to ≤ 0.5° within 1 s through the L0 magnets (E1-5s, 20/20).
  U offsets of 0–20° followed by an R turn never produced an illegal or mismatched state; blocking was allowed (E1-5,
  42/42).
- `FACT` (G2-R §5): scored turn errors ≤ 0.414°, end misalignment ≤ 1.064°. **G2 turns are validated only from starts
  within ±1° per face.**
- `INFERENCE` (geometry): flat pads squeezing a layer rotate it toward the pad plane, about every axis perpendicular to
  the pad normal (the flat-pad re-centring of G4-18). Each closure therefore aligns the layers it clamps to the
  gripper's nominal orientation. Rotation about the pad normal is not corrected.
- `INFERENCE` (the real mechanism of risk): a misalignment survives only where two grips disagree. Examples: the cube
  is rotated by δ in the giver's grip and the receiver closes at its nominal orientation, or a turn ends short while
  both grips hold. In FIXED-C1, when A releases, D + E become free relative to the U layer B holds, so the magnets should
  snap them back. This is the E1-5s mechanism, but now with the whole cube hanging; it is untested.

**Answer (`PROPOSAL`):**
1. **No separate runtime alignment step for now.** Runtime cannot read layer angles before G5 (cameras). The protocol
   instead relies on:
   - the H6 settle of 1 s for magnet snap-back;
   - the aperture band (A2), which catches a wedged layer at ≳ 1° (see the widths in A2);
   - G2's jam guard (1.0 N·m) as the backstop on the next turn.
2. **An offline judged check before every turn and at the end of every handoff:** every cubie's misalignment ≤ the
   envelope from which turns have been validated. Today that envelope is G2's (±1° starts, end ≤ 4°).
3. **The first experiment (§5) decides whether more is needed.**
   - If handoffs leave every cubie within about 1°, nothing is added.
   - If they leave 1–3°, G2-style turn trials from those starts are run before G4 relies on them.
   - If they leave more, or the aperture misses wedges that the audit sees, an explicit `align` primitive is proposed:
     a re-grip at nominal orientation by the stabiliser and then the turner, with no roll, and only nominal targets.
4. **No alignment check may read cube state at runtime.** A camera-based check belongs to G5.

---

## 5. Tooling decision: FIXED vs SYM

### 5.1 Options
- **FIXED-C1 (D22's FIXED):** G2 tooling unchanged. During handoffs B holds the whole cube by its C1 grip on one layer
  (14 mm deep); two layers hang.
- **FIXED-ST (`PROPOSAL`, new here):** G2 tooling unchanged. For handoff holds only, B inserts its C1 pads to G2-7's
  `two_layer` depth (distal end 25 mm inside the face; 8 mm on the held face's layer and 6 mm on the middle layer). The
  grip straddles the boundary and clamps two layers, so one layer hangs, as in G2's validated hold.
  - For turns, B keeps the G2 14 mm C1 grasp unchanged.
  - `FACT`: this insertion ran in 2 scored and 6 pilot G2-7 trials with A holding, without arm–arm or non-fingertip
    contact (§1.2).
  - `INFERENCE`: at the A→B handoff the pads are 2 mm apart along x: A's pads reach x = +1.5 mm and B's distal end is at
    x = +3.5 mm. That satisfies D22's 1 mm footprint rule. Clearances against A's *next* grasp (from ±y) are unchecked.
- **SYM-P97 (`PROPOSAL`, the simplest SYM candidate found):**
  - Both arms carry P-97 pads (B's C1 is replaced).
  - The role is selected by insertion depth: 30 mm to stabilise (as A in G2); 14 mm to turn, so that only the distal
    14 mm of the pad touches one layer, a 30 × 14 mm patch against C1's 25 × 14.
  - A second wrist F/T sensor on A, and A's controller made compliant like B's.
  - Pros: no tool changer, and the holder always grips 1.5 layers.
- **SYM by tool changer:** listed for completeness and not recommended. It adds mass, length and change time, none of
  it modelled, and a mechanism outside the cube's contact model.
- **Stand-assisted regrasp:** park the cube on a fixture between grips. D22 did not consider it (D22 Limitations). The
  G2 stand supports only D + E at the G2 orientation. Not evaluated.

### 5.2 Decision matrix
Success-rate rows are arithmetic (`p^n`), with **p = per-handoff success**, which is unknown. "Est. per 20-move solve"
uses `INFERENCE`: a solver never turns the same face twice in a row, so each move after the first is a face change.
That gives about 2 × 19 = 38 handoffs for FIXED and 19 for SYM, reorientations excluded.

| Criterion | FIXED-C1 | FIXED-ST | SYM-P97 |
|---|---|---|---|
| Handoffs per six-face tour | **10** + 1 reorientation (`FACT`, D22) | 10 + 1 (`INFERENCE`: same topology; kinematics to recheck) | **5** + 1 (`FACT` for D22's SYM grasp set; `ASSUMPTION` that it transfers to 30 mm-wide turner pads and A's sensor) |
| Handoffs per face change | 2 | 2 | 1 |
| Est. handoffs per 20-move solve | ≈ 38 | ≈ 38 | ≈ 19 |
| Tour success at p = 0.99 / 0.98 / 0.95 | 0.904 / 0.817 / 0.599 | same | 0.951 / 0.904 / 0.774 |
| 20-move solve at p = 0.999 / 0.99 / 0.98 | 0.963 / 0.683 / 0.464 | same | 0.981 / 0.826 / 0.681 |
| Holder's grip during a handoff | one layer (14 mm); two layers hang; U/E shear 0.58 N and moment ≈ 0.011 N·m (2× / 4× G2's validated hang) | two layers (8 + 6 mm); one layer hangs; shear 0.30 N, moment ≈ 0.003 N·m (as G2's hang) | 1.5 layers (19 + 11 mm); one layer hangs (= G2-1's validated hold) |
| Hardware change | none | none (a new grasp pose) | P-97 pads on B; second F/T sensor on A (≈ 0.6 kg, +35 mm tool, P-114 figures); compliant controller on A |
| G2-validated parts kept | every turn, guard and controller | same; the straddle insertion exercised in G2-7 (as a turn fault, not as a hold) | stabiliser P-97 (on A only). **Not validated:** P-97 as a turner, A as a turner, A's guard |
| Worst static joint margin on the tour | B 19.7° at +x, recurring at every B hold (`FACT`, D22) | unknown (D22 rerun) | 25.9° without A's sensor (`FACT`, D22); with it, unknown. Adding B's sensor cut B's margin from 25.8° to 19.1° (G2-PR §5) |
| Worst both-closed arm–arm clearance (coax tour) | 23.4 mm | unknown (B's fingers 11 mm deeper) | 18.2 mm (D22, without A's sensor) |
| Online guard coverage | F/T on the only turner; B's F/T witnesses every handoff | same | F/T on both turners; two witnesses per handoff |
| Needed before the first handoff pilot | nothing | D22 recheck of the straddle grasp against A's next grasps (≈ 20 min, D22 Reproduce) | sensor model on A; D22 rerun; a P-106-style turner pilot (P-97 shallow vs C1); A's controller and guard; G2-like turn re-validation |
| Main unknowns | one-layer hold mechanics; A's closure pushing D + E through the mechanism (§1.4) | the straddle hold under load and A's push; clearance with A's next grasps | turn quality with the wider pad; A's margins and clearances with the sensor; real-arm compliance on A (D23: admittance stable only with contact-sized damping, D ≈ 300 N·s/m) |
| Simulated handoff time per tour (≈ 9.5 s each) | ≈ 95 s | ≈ 95 s | ≈ 48 s |

**What would have to be validated (`INFERENCE`):**
- **Any option:** per-handoff success with a confidence bound. With zero failures, a 95 % upper bound of 1 % on the
  per-handoff failure rate needs ≥ 299 handoffs (1 − 0.05^(1/299) ≈ 0.997 %, the one-sided exact bound G2-R used for
  its 3.0 % at 0/100). That is about 30 FIXED tours or 60 SYM tours.
- **FIXED-C1:** the one-layer hold, statically and under A's closure push.
- **FIXED-ST:** the same for the straddle hold, plus kinematics against A's next grasps.
- **SYM-P97:** turner equivalence (a new C1/C2-style pilot), A's sensor model and margins, and A's guard. That is close
  to a partial G2 re-run for arm A.

### 5.3 Recommendation (`PROPOSAL`, clearly a recommendation, not a decision)
**Recommended: FIXED tooling for G4.** B's handoff-hold grasp should be chosen by the first experiment between C1
one-layer (FIXED-C1) and C1 straddle (FIXED-ST). SYM-P97 should be kept in reserve, with an explicit trigger.

Reasons:
1. FIXED keeps every G2-validated component: turner, stabiliser, controllers, F/T guard and limits. G4 starts from a
   passed gate, not from a re-validation.
2. FIXED's specific mechanical risk, the one-layer hold, can be tested in about 1–2 h of compute (§5.4 and §6). Its
   fallback, FIXED-ST, needs no hardware change and puts the holding condition back to G2's validated one-layer hang.
3. G4's pass criterion is "multiple varied face turns and role transitions" with reproducible traces (VALIDATION_PLAN
   G4; PHASE_4 exit criteria), not a handoff count. Ten handoffs per tour is slower but not disqualifying.
4. SYM's halving of handoffs matters most for G6 full solves: at p = 0.99, 0.68 vs 0.83 per 20-move solve. That is the
   right time to revisit it, with measured p in hand.

**Trigger to move to SYM (`PROPOSAL`):**
- both FIXED hold variants fail the §5.4 pass signals for a mechanical reason (drop, layer separation, a hanging layer
  turned by A's push); or
- chained-handoff pilots show per-handoff failures that FIXED's 2-per-face-change topology makes untenable for the G4/G6
  targets the user sets; or
- the user rules that G4's "role swap" means swapping turner and stabiliser (§7 D-6), which FIXED cannot do.

**Second wrist F/T on arm A:**
- Not needed for FIXED handoffs: B witnesses every handoff, and A is never compliant or a turner.
- **Needed for SYM** (`INFERENCE`): the only working jam guard is the F/T guard (P-111, P-113, P-114). A compliant A on
  real hardware also needs a force measurement (D23).

### 5.4 Decision signal from the first experiment
- If FIXED-C1 meets every pass signal (§6.4) with margins similar to FIXED-ST, keep the G2 C1 grasp for holds (simpler:
  one grasp depth).
- If FIXED-C1 shows any failure, or hanging-layer separation or rotation clearly above FIXED-ST's, use FIXED-ST.
- If both fail, go to SYM-P97 or a stand-assisted regrasp (user decision).

---

## 6. First experiment: handoff-only pilot (`PROPOSAL`; UNSCORED)

**Working name:** `experiments/D26_handoff_pilot/` (number to be confirmed; `D25_magnet_speedup/` already exists).
**Seeds:** pilot range 29800–29899, never used elsewhere afterwards.
**Gate status:** it is a feasibility study like D22 and D23. It counts toward no gate and changes no frozen file.

### 6.1 Question
At the G2 grasp pair, can arm A hand the cube to arm B (B holding by C1 one-layer or by C1 straddle) without a drop,
an unsupported interval, a turned layer, judged contacts or alignment loss? Are the robot-signal abort rules informative,
meaning they detect the injected faults and do not fire on normal trials?

### 6.2 Trial sequence (no turn)
1. **G2 start sequence, unchanged** (G2-PR §2), up to t0 (≈ 3.6 s), with the seeded start draw.
2. **H0–H3:** B approaches and closes. For C1 this is the G2 move grasp; for ST it is the G2-7 `two_layer` insertion.
   Then dwell and nulling.
3. **Optional seeded inter-layer offset (block A3 only):** B rolls J7 by δ with the G2 roll controller, then holds.
   This produces a contact-made misalignment between U and D + E, like a turn that ended short. It is a few degrees,
   not a move.
4. **H4–H6:** A ramps its release, opens and retreats 40 mm along −x; settle.
5. **Solo hold:** B holds the whole cube alone for 5 s (the FIXED condition while A moves to its next grasp).
6. **Return stage (`PROPOSAL`, D-5):** A re-approaches the same G2 grasp and closes (position servo), with B as the
   compliant giver (lowered K_P), then B releases and retreats. It is judged as a separate handoff. It tests A's
   closure on a B-held cube without transit planning. The user may drop it to keep strictly one handoff.

Every phase runs under the online abort rules of §3 (logged), plus the audit-channel checks of §2.4.

### 6.3 Conditions and seeds
| Block | Hold | Start / fault | Seeds | n |
|---|---|---|---|---|
| A1 | C1 one-layer | G2 start draw (±1 mm per axis, ±1° per face) | 29800–29814 | 15 |
| A2 | C1 one-layer | extended: cube offset ±2 mm per axis and whole-cube rotation ±2° about each axis at setup | 29815–29824 | 10 |
| A3 | C1 one-layer | G2 draw + contact-made offset δ ∈ {+2, −2, +4, −4, +6}° before A's release | 29825–29829 | 5 |
| B1 | C1 straddle | G2 start draw | 29830–29844 | 15 |
| B2 | C1 straddle | extended (as A2) | 29845–29854 | 10 |
| F1 | C1 | **receiver miss:** B's gripper target stops at 70 mm aperture (expect I1/A2 to block A's release) | 29855–29856 | 2 |
| F2 | C1 | B's axial target 8 mm short, pads on 6 mm of U (report) | 29857–29858 | 2 |
| F3 | C1 | B's grip at 10 N, the G2 minimum (report hold margins) | 29859–29860 | 2 |
| F4 | C1 | cube offset 3 mm along B's closing direction (does the F/T offset estimate see it?) | 29861–29862 | 2 |
| F5 | C1 | **deliberate unsupported release:** A opens before B closes, a positive control for the support-continuity check and A7 (Phase 4 task 5 allows it when deliberately tested) | 29863–29864 | 2 |
| — | — | reserve for reruns and diagnostics | 29865–29899 | (35) |

**Total: 65 trials.** Block A2/B2 setup writes are logged setup writes before t0, as G2's start draw.

### 6.4 Metrics and pass signals (stated before running; pilot signals, not gate criteria)
**Metrics per handoff (audit channel), each reported per block as max / median:**
- support continuity (minimum supporting grippers, longest both-grip interval);
- core and clamped-cubie pose change relative to the receiver from both-closed to the end, and relative to the giver
  during H1–H3;
- core height change; drop flag;
- oracle readout before and after;
- per-cubie misalignment at H0 and at the end of H6, and growth;
- hanging-layer rotation about the face axis, and layer separation (axial and tilt) during H4–H6 and the solo hold;
- cubie and fingertip penetration;
- contact classes;
- magnets (steps without force = 0; near-pair tilt ≤ 5°; no perpendicular pair);
- true inter-arm force (mean and peak);
- the online signals next to their truths (F/T load step, internal force, apertures);
- every abort fired, with its reason;
- sim time, wall time, real-time factor.

**Pass signals (`PROPOSAL`):**
1. **A1 and B1 (30 trials):**
   - 0 drops and 0 unsupported steps;
   - logical state unchanged;
   - no judged contact;
   - magnets valid;
   - cube pose change relative to the receiver ≤ 1 mm and ≤ 2° per handoff (G2 per-move limits), ≤ 1 mm / 1° over the
     5 s solo hold (G2-1's hold limits);
   - every cubie ≤ 4° at the end (G2's end limit), with growth reported against G2's 1.064°;
   - **0 aborts fired (no false alarms).**
2. **A2 and B2:** the same checks, **reported** per condition. Failures here set tolerances; they do not stop the work.
3. **A3:** after A's release, D + E realign with U to ≤ 0.5° within the 1 s settle (as E1-5s), or the result is reported
   as a finding.
4. **Faults:**
   - F1: 2/2 blocked by I1/A2 before A's gripper starts H4;
   - F5: 2/2 flagged by the support-continuity check offline **and** by A7 (or A4/A5) online, within 0.2 s of the loss;
   - F2–F4: reported.
5. **Signals:** in every A/B trial, the F/T load step lies within 0.88 ± 0.3 N of its truth. This checks the A7
   threshold.
6. **Tooling signal:** as §5.4.

### 6.5 Expected compute (`INFERENCE`)
- Simulated time per trial: about 3.6 s start + 9.5 s handoff + 5 s hold ≈ 18 s; about 28 s with the return stage.
- Wall time: G2-8's median real-time factor was 0.043 per process with 8 workers (G2-R §5), about 23 s of wall per
  simulated second. The G2 scored run averaged about 670 s of wall per trial-process (11,519 s × 8 / 138).
  - So about 7–11 min per trial.
  - 65 trials: about **1.0–1.5 h with 8 workers**, or 2–3 h with 4.
- Preparatory D22 recheck of the straddle grasp against A's next grasps: about 20 min, single process (D22 Reproduce).
- Code before the run: the handoff sequencer, the abort rules, the new audit metrics and their unit tests, and the
  controller-blindness tests. All CPU-only, no new dependencies, run in WSL (`~/.venvs/rubiknetic`).

### 6.6 What comes after (not part of this pilot)
1. The B→A handoff at FIXED's next grasp (A from ±y), with a joint-space transit of A, collision-checked offline.
2. A chained-handoff pilot: the FIXED tour without turns (10 handoffs + reorientation), to measure axial drift and
   alignment growth.
3. Then turns inserted: a FIXED tour with one turn per face.
4. Then a G4 pre-registration with reviews and a freeze, as for G2.

---

## 7. Risks, open questions and decisions needed

### 7.1 Risks (`INFERENCE` unless marked)
- **R1 One-layer hold (FIXED-C1).** The cube hangs through the cubie–core interlock at about 2× the shear and 4× the
  moment of G2's validated hang (§1.4). Layer separation in whole-cube moves is reported for real cubes (G4-25).
- **R2 Push through the mechanism.** A position-controlled A closing on a B-held cube pushes at about 4 N/mm of offset
  with G2's K_P. With a one-layer hold, that push reaches D + E through the mechanism and could tilt or turn them.
  Mitigation: B yields during A's closure (H2).
- **R3 Axial drift.** Pad closures re-centre the cube along their closing direction only (G4-18). Nothing re-centres
  it along the approach axis, and no robot signal measures that axis. C1's axial tolerance is about ±2 mm (P-107).
  - Mitigation `PROPOSAL`: a guarded touch, in which B touches the face axially with closed fingers and detects contact
    on its F/T before a C1 grasp. This is a robot-signal analogue of the PR2's pre-touch re-estimation, which raised
    the PR2 from 0/10 to 8/10 solves (G4-02).
- **R4 Reorientation:** the 180° carry by A is unchecked along its path, and gravity on the hanging layer changes
  direction during it (D22 §4).
- **R5 Transit:** A's moves between grasps around a B-held cube are not planned or collision-checked (Phase 4 task 4).
- **R6 Joint margin:** B's 19.1–19.7° margin recurs at every FIXED handoff (D22; G2-R §8 unresolved risk).
- **R7 Controller abstraction:** G2's torque-level impedance cannot run on the real xArm (P-134). The hardware-style
  admittance is stable only with contact-sized damping (D23), and it is untested in handoff transients.
- **R8 Release mechanism:** a mid-trial force-setting change departs from `set_grip_force`'s documented use. A position
  ramp avoids it (§2.3).
- **R9 Turn envelope:** turns are validated only from ±1° starts (G2). If handoffs leave more, turns need new
  validation (§4).
- **R10 Statistics:** a zero-tolerance gate over about 38 handoffs per solve needs hundreds of failure-free handoffs to
  bound p (§5.2).
- **R11 SIDE grasps:** mechanically unassessed and as tight as 1.1 mm (D22). The recommended coax tours avoid them.

### 7.2 Decisions needed from the user
| ID | Question | Options | Recommendation |
|---|---|---|---|
| **D-1** | Tooling for G4 | FIXED (G2 tooling) / SYM-P97 / SYM by tool changer | **FIXED**, with SYM-P97 in reserve under the §5.3 trigger |
| **D-2** | B's grasp while holding the whole cube during handoffs | C1 one-layer (D22) / C1 straddle (G2-7 depth) | test both in the pilot; choose by §5.4 |
| **D-3** | Second wrist F/T on arm A | not now / add now | **not now** (needed only for SYM) |
| **D-4** | How the giver releases | position-target ramp / mid-trial force-setting change | **position ramp** (§2.3) |
| **D-5** | First pilot scope | A→B only / A→B plus the B→A return at the same grasps | **include the return**, judged separately |
| **D-6** | Does FIXED's holder swap satisfy G4's "role swap", or must turner and stabiliser swap? | user's interpretation of VALIDATION_PLAN G4 | needs the user's ruling; a turner/stabiliser swap would force SYM |
| **D-7** | Phase order: `PHASE_4` lists "G3 RL experiment evaluated" as a prerequisite, and G3 is still in design (P-145, P-146) | run the G4 pilot in parallel as unscored feasibility (as D22) / wait for G3 | user's call; CLAUDE.md forbids phase advancement without sign-off, and an unscored pilot is not an advancement |
| **D-8** | Runtime alignment check | none beyond the H6 settle, aperture band and jam guard, unless the pilot shows > 1° / explicit `align` primitive now | **none for now**, decided by the pilot (§4) |
| **D-9** | Numbering and seeds | `D26_handoff_pilot`, seeds 29800–29899 (check that no other work uses the range) | as proposed |

### 7.3 Open questions not answered here
- The torsional friction of the pad contacts in the model (condim 4 parameters) and therefore the true moment margin of
  B's C1 grip on the whole cube (§1.4).
- Whether the M7 interlock carries the hanging load without separation at 0.011 N·m (R1). Only the pilot can say.
- The G2 gripper's real aperture accuracy (position feedback only; command resolution 0.1 mm per
  `PHASE_2_ROBOT_MODEL_FINDINGS.md`, accuracy unknown), which sets the real A2 band.
- Whether one held layer's alignment, and the cube's orientation in the holder's grip, stay within the turn envelope
  over 10 chained handoffs (R3, §6.6 step 2).
- The real F/T sensor's force noise and bias drift (D23 used an `ASSUMPTION` of 0.1 N; G2 modelled torque noise only).

---

## 8. Mapping to VALIDATION_PLAN G4 (what this design addresses)
| G4 item | Where addressed |
|---|---|
| Unique cube/orientation/arm frames; no ambiguous notation | not addressed here (Phase 4 task 1; frame tests before motion planning, SYSTEM_ARCHITECTURE) |
| Planner generates only feasible, collision-checked actions | D22's static checks; transit and reorientation paths open (R4, R5) |
| Regrasp, support transfer and role swap without teleportation | §2 protocol (support continuity judged); role-swap interpretation D-6 |
| Physical/logical continuity across nonparallel moves | §2.4 logical-continuity check per handoff; tours in §6.6 |
| Failed manipulations → bounded retry/replan/stop, no hidden reset | §3 abort and recovery rules (robot signals only) |
