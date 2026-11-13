# Phase 1 and Phase 2 Validation Experiments — Proposed Protocol

**Date:** 2026-11-12 · **Status:** `PROPOSAL` — **NOT RUN**. Defined during Phase 0; nothing here is implemented.
**Relationship to [`../VALIDATION_PLAN.md`](../VALIDATION_PLAN.md):** these experiments instantiate gates **G1** and **G2**. Per its threshold policy, **categorical** criteria (no teleportation, no hidden actuation, legal state) are fixed now. **Numeric** thresholds below are *provisional proposals*, marked ⟨P⟩. They must be confirmed or revised after the calibration pilots (E1-0, E2-0) and pre-registered **before** any scored run. They may never be lowered after a failure.
**Cube-model candidates under test:** M1 (contact-emergent, ball-joint), M2 (switched welds), M4 (fixture surrogate, bring-up only). See [`CUBE_MECHANICS_LITERATURE_REVIEW.md`](CUBE_MECHANICS_LITERATURE_REVIEW.md) §6.
**Fingertip candidates:** C1, C2 (C4/C6 contingency). See [`GRIPPER_DESIGN_TRADEOFFS.md`](GRIPPER_DESIGN_TRADEOFFS.md).

---

## 0. Common rules for every experiment

1. **Recording:** each run records the [`VALIDATION_PLAN.md`](../VALIDATION_PLAN.md) trial template, plus MuJoCo version, timestep, integrator, solver (type, iterations, tolerance), cone type, `impratio`, and all contact `solref`/`solimp`/`margin`/`gap`.
2. **No privileged edits during execution:** any write to `qpos`, `qvel`, `eq_data`, `eq_active` or `xfrc_applied` outside an approved, logged mechanism (episode setup; M2 switching rule) automatically fails the run. An **edit audit** (diffing state writes against the logged allowance) runs on every trial.
3. **Oracle agreement:** the extracted discrete state must equal `oracle.apply(observed_move)`. The *observed* move is inferred from measured layer rotation, never from the command.
4. **Determinism:** repeated runs with identical seed and config must reproduce trajectories to a stated tolerance on the same machine. Report any nondeterminism.
5. **Negative results are deliverables:** failed parameter sets are archived with their configs.

## 1. Phase 1 — cube physics (no robot arms)

The external actuator is a **contact probe**: a kinematic or position-servoed body (e.g., a mocap-driven box or capsule) that pushes on cubies through ordinary contacts. A separate fixture holds the non-turning layers *by contact*. The probe's applied wrench is logged from contact forces.

| ID | Experiment | Procedure | Pass criteria (categorical / ⟨P⟩ provisional) | Credibility evidence produced |
|---|---|---|---|---|
| **E1-0** | Calibration pilot (unscored) | Tune bevel, gap, contact and joint-friction parameters until a probe-driven 90° turn is possible. Record the breakaway and running torque achieved. | None (calibration). Its output fixes the ⟨P⟩ values below and is published with all tried settings. | Parameter-to-behaviour map; honest record of tuning |
| **E1-1** | Geometry and constraint consistency | Load the model; compute cubie positions, orientations and radial distances; run 10 s at rest under gravity and with the fixture. | 26 cubies in legal slots. Extracted state = solved. Radial drift ⟨P⟩ ≤ 0.2 mm. No spontaneous layer rotation ⟨P⟩ > 0.5°. Max penetration ⟨P⟩ ≤ 0.2 mm. **M2:** active weld set exactly matches the topology implied by poses. | Static legality; contact steady state |
| **E1-2** | Physically driven 90° turn (both directions) | Probe pushes one edge cubie tangentially on U (CW, then CCW) while the fixture holds D+E. Repeat on all 6 faces. | Turn completes to within ⟨P⟩ ±2° of 90°. Non-target layer rotation ⟨P⟩ ≤ 1°. Oracle agrees. Edit audit clean. Contact trace shows probe force **preceding** layer motion. | Contact causality; torque-angle curve |
| **E1-3** | Physically driven 180° turn | As E1-2, continuous 180° (both directions). | As E1-2. No stall at 90°: either a continuous turn, or a stall that is reported along with the torque needed to overcome it. | Detent/forgiveness behavior at 90° |
| **E1-4** | Consecutive turns on different axes | Probe sequence `R U R' U'` ×6 (this sequence has order 6, so the solved state should return); plus `F2 B2 L2 R2 U2 D2`; plus a 20-move scramble and its inverse. Realign between moves only via probe contact. | Every intermediate state agrees with the oracle. Final state = expected (solved for ×6 and scramble+inverse). No cubie lost or twisted. Cumulative misalignment reported. | Topology correctness across axis changes; drift accumulation |
| **E1-5** | Constraint transitions | **M2:** log every switch (pre/post relative pose and velocity, ΔKE, constraint impulse, penetration) over E1-2…E1-4. **M1:** measure the forgiveness angle, i.e. the largest misalignment of face X that still allows a perpendicular turn of face Y. | **M2:** no switch with ⟨P⟩ \|ΔKE\| > 1 % of cube KE or > 1 mJ, whichever is larger; no switch outside the alignment tolerance; zero relpose-error activation. **M1:** forgiveness angle measured (no pass threshold until real-cube data exist). | Switching artifacts (R2), or emergent jamming |
| **E1-6** | Negative controls | (a) Command a "turn" with the probe out of contact. (b) Apply opposing torques to U and R simultaneously. (c) Apply twisting torque to a single corner about its diagonal (up to 10× running torque). (d) Attempt a turn at 20° misalignment of a perpendicular face. (e) **M2 only:** force a switch request at a misaligned pose. | (a) No motion and no success. (b) **Jams**: no simultaneous legal rotation, no separation. (c) No corner twist; the oracle invariant holds; if it fails, record the load at which it fails. (d) Blocked. (e) Request **refused**, no snapping. | Shows the model cannot "succeed" without physics |
| **E1-7** | Sensitivity | Sweep timestep (≥3 values), solver iterations or tolerance, friction (μ 0.1–1.0), joint `frictionloss` (decade sweep), bevel, gap, initial misalignment (0–5°). Repeat E1-2 and E1-4. | Outcome (pass/fail of E1-2/E1-4) is unchanged across the declared "nominal band". Any parameter whose small change flips the outcome is reported as a fragility. | Robustness, not single-point tuning |
| **E1-8** | CPU performance (headless) | Measure steps/s and simulated-s per wall-s for: M1, M2, M4 alone; with probe; at ≥2 timesteps; single-thread and N-process. Record CPU model, RAM, OS, WSL2 status. | No pass threshold for the measurement itself. Publish results and set ⟨P⟩ a Phase 2 throughput floor from them. | Compute budget evidence (R4) |

**G1 pass logic:** all categorical criteria hold in all scored trials; ⟨P⟩ thresholds are confirmed or pre-registered after E1-0 and met in ≥ ⟨P⟩ 20 trials per experiment; E1-6 negative controls behave as specified. **One-turn-only success is insufficient** (VALIDATION_PLAN G1).

**Mechanism decision rule (`PROPOSAL`):** choose M1 if it passes E1-2…E1-6 within the CPU floor. Choose M2 if M1 fails E1-4/E1-6 and M2 passes E1-5 cleanly. If neither passes, mark G1 **BLOCKED** and request a scope review. A scripted rotation is never an acceptable fallback.

## 2. Phase 2 — two xArm7s, grippers, classical control (no RL)

| ID | Experiment | Procedure | Pass criteria | Credibility evidence |
|---|---|---|---|---|
| **E2-0** | Calibration pilot (unscored) | Map grip-actuator command to simulated normal force; verify the G2 L(d) axial-offset model; tune impedance gains on free motion. | None (calibration); outputs registered. | Force calibration map |
| **E2-1** | Robot model integrity | Load 2 × Menagerie xArm7 (pinned commit), rename all elements uniquely, attach candidate fingertips; check frames, joint limits vs S21, masses, collision groups. | All joint limits match the official spec or deviations are documented. Unique names. Tool-frame FK error ⟨P⟩ < 0.1 mm against an independent computation. No self-collision at home pose. License notices preserved. | Model provenance |
| **E2-2** | Stable grasp and stabilization | Arm A grasps the cube (two layers, stabilizer finger). The E1 contact probe applies a torque ramp on the free layer up to ⟨P⟩ 2 × the E1-0 running torque. | Held layers' rotation ⟨P⟩ ≤ 1°. Cube slip in grasp ⟨P⟩ ≤ 0.5 mm. No cubie illegal state. | Counter-torque capacity, measured not assumed |
| **E2-3** | Bimanual face turn, 90° and 180° | Arm A stabilizes; Arm B (C1 and C2 tips) seats on the target layer and turns via J7 under impedance control; release; retreat. All 6 faces (via test-setup poses; no planner yet). | Turn within ⟨P⟩ ±2°. Non-target rotation ⟨P⟩ ≤ 1°. Oracle agrees. Edit audit clean. No robot collisions. Success in ≥ ⟨P⟩ 18/20 trials per face and direction. | The Phase 2 headline result |
| **E2-4** | Layer-selectivity sweep (falsifies C1 vs C2) | Repeat E2-3 for U with axial seating offsets 0, ±1, ±2, ±3 mm and lateral offsets 0, ±1, ±2 mm. | Report wrong-layer angle and middle-layer contact force against offset for each tip. **Prediction to test:** C2 holds selectivity at axial offsets where C1 fails. If not, the datum rationale is falsified. | Quantitative tip comparison |
| **E2-5** | Alignment and internal force | Inject coaxial misalignment δ ∈ {0, 0.5, 1, 2} mm and tilt ∈ {0, 0.5, 1}°; run impedance stiffness at ≥3 levels. | Measured internal force compared with the §5 feasibility prediction. Success-vs-stiffness curve reported. ⟨P⟩ no grasp slip > 1 mm at the selected stiffness. | Justifies the D-08 controller choice with data |
| **E2-6** | Slippage and contact-force analysis | Grip-force sweep (10–50 N) × μ sweep (0.3–1.0) × torsional coefficient sweep; log normal and tangential forces, slip velocity, contact count. | Map of the success region. The minimum force for ⟨P⟩ ≥95 % success at nominal μ is identified. Excess-force events flagged. | Grounds the torque estimates in sim data |
| **E2-7** | Sensitivity | Friction, cube size (55–58 mm), cubie play, solver settings, timestep. | As E1-7: report the fragility boundary. | Robustness |
| **E2-8** | CPU performance | Steps/s for two arms + cube (M-selected) + controllers, headless, rendering off/on. | Measurement published. ⟨P⟩ Phase 3 go/no-go needs ≥ a throughput floor derived here, plus the estimated RL sample budget. | R4 evidence |
| **E2-9** | Required negative tests (from `PHASE_2_ROBOT_INTEGRATION.md`) | Two-layer contact by design (oversized tip); deliberate off-center grasp; collision course with table or other arm; gripper opens mid-turn; forced relink impulse (M2). | Each must be **detected and rejected**, never counted as success. | Validator sensitivity |

**G2 pass logic:** E2-1…E2-3 and E2-9 pass; E2-4…E2-8 are completed and published. A gripper concept is selected *by you* on E2-4/E2-6 evidence. No RL is used in Phase 2.

## 3. What would demonstrate physical credibility

1. **Causality traces:** contact force from the probe or fingertip rises *before* layer angular velocity, and the integrated contact torque accounts for the layer's angular momentum change (impulse–momentum check within ⟨P⟩ 10 %).
2. **Edit audit:** zero unlogged state writes during scored execution.
3. **Independent oracle agreement** on every observed turn, including long sequences (E1-4).
4. **Negative controls behave physically** (E1-6, E2-9): the system *fails* when it should.
5. **Insensitivity within a declared band** (E1-7, E2-7), with fragility edges reported.
6. **Energy audit:** no unexplained kinetic-energy gains at switches or contacts (E1-5).
7. **Calibration provenance:** turning resistance tied to a measured real-cube value if one becomes available (CUBE review §8); otherwise reported explicitly as uncalibrated.
