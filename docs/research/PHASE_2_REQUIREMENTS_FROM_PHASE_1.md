# Phase 2 requirements derived from Phase 1 findings — PROPOSAL

**Date:** 2026-11-13 · **Status:** `PROPOSAL` for user review. Nothing in this file is approved, and nothing here is
a `VALIDATED_RESULT`. It does **not** edit `phases/PHASE_2_ROBOT_INTEGRATION.md`,
`docs/research/PHASE_1_2_VALIDATION_EXPERIMENTS.md` (E2-x), `docs/VALIDATION_PLAN.md` (G2) or the master spec. Each
requirement adopted by the user must be applied to those documents and logged in `docs/DECISION_LOG.md`.
**G1 is not passed** (the M2 scored run is in progress). Every number below comes from unscored prototypes,
smoke checks or pre-registration amendments, and must be re-checked once G1 is signed off.

**Tags:** `FACT` = measured in a cited run or stated in a cited project file · `INFERENCE` = derived from facts ·
`ASSUMPTION` · `PROPOSAL`. Numeric acceptance values marked ⟨P⟩ are proposals. They should be set from the E2-0
calibration pilot and pre-registered before any scored Phase 2 trial, and never loosened after a failure.

**Sources read:** `RUBIKNETIC_MASTER_SPEC.md`; `phases/PHASE_2_ROBOT_INTEGRATION.md` (cited below as "Plan Task n",
"Plan Neg", "Plan Exit"); `docs/research/PHASE_1_2_VALIDATION_EXPERIMENTS.md` §2 (E2-0…E2-9); `docs/VALIDATION_PLAN.md`
G2; `docs/DECISION_LOG.md` P-09…P-17; `experiments/PHASE_1_M2_PREREGISTRATION.md` §1 and §9–11 (Amendments 1–3);
`experiments/D6_free_core/README.md`; `experiments/P2_robot_model/README.md` (cited as "P2 §n");
`experiments/D5_follower_cube/README.md`; `docs/research/PHASE_2_ROBOT_MODEL_FINDINGS.md`;
`docs/research/CUBE_MECHANISM_FINDINGS.md`; and `src/rubiknetic/cube_physics/switching.py` (to check how robot
contacts enter the M2 switch rule).

---

## 1. Summary

| ID | Requirement (short) | Group |
|---|---|---|
| R2-01 | Stabiliser grasp spans exactly two adjacent layers (outer non-target + middle) | Grasp |
| R2-02 | Stabiliser clearance to the target-layer boundary, under sag, L(d) and creep | Grasp |
| R2-03 | Reaction-torque split gives a shear-dominance margin | Switching |
| R2-04 | Robot fingertips registered in the M2 switch manager, with a defined face-grip rule | Switching |
| R2-05 | Turn completion within 0.5° (hinge and every layer cubie) | Turning |
| R2-06 | End-of-turn unloading so M2 can relock | Turning |
| R2-07 | Declared layer-angle feedback source for the turning controller | Turning |
| R2-08 | Ramped (speed-limited) gripper closing, settle before load | Gripper |
| R2-09 | Scored trials grasp with gravity on, from a modelled support | Grasp |
| R2-10 | Soft-contact creep (~0.02 mm/s) measured, separated from slip, and bounded | Contact |
| R2-11 | Gripper calibration regression (stroke 83.1 mm, spring offset removed) and per-width recalibration | Gripper |
| R2-12 | Tool frame from the simulated four-bar pose, not a fixed 0.172 m TCP | Gripper |
| R2-13 | Fingertip mount interface (provisional 2 × M3 at 12 mm) | Fingertip |
| R2-14 | Fingertip contact model includes torsional friction, or justifies its absence | Fingertip |
| R2-15 | Conservative joint envelope until the xArm7 hardware revision is confirmed | Robot |
| R2-16 | URDF peak torques as saturation limits; sustained-load flag | Robot |
| R2-17 | Controller enforces joint and gripper speed limits | Robot |
| R2-18 | Gravity compensation on; sag budget and mass-error sensitivity | Robot |
| R2-19 | Throughput measured for two arms + M2 (one arm + M2 was 400–840 steps/s) | Compute |
| R2-20 | D5 used as the forgiveness reference, never for scoring | Cube model |
| R2-21 | Initial cube alignment within the M2 envelope, and not disturbed by the grasp | Cube model |
| R2-22 | Controller and supervisor never read M2 lock state | Integrity |
| R2-23 | Asset provenance and vendoring as approved in P-17 | Provenance |

**23 requirements.** The top five by impact are R2-04, R2-05, R2-01/R2-02 (grouped), R2-10 and R2-08 (section 4).

---

## 2. Requirements

### R2-01 — Two-layer stabiliser grasp

* **Requirement.** Arm A (stabiliser) must grip the cube across **two adjacent layers**: the outer layer opposite
  the target face and the middle layer (for a U turn, D + E). It must not touch the target layer. A one-layer hold
  is not an allowed stabiliser grasp.
* **Evidence.**
  * `FACT` D6 `run_stab.py shear stab_hold=DE` (two-layer stabiliser, 30 N pads): 5/5 U U′ U2 U′ U correct, error
    ≤ 0.30°, drift 0.00°, core slip ≤ 0.28 mm, switch ΔKE ≤ 1e-8 J.
  * `FACT` D6 one-layer hold: with the original rule, commanding U unlocked D (cube rotated 89.8° inside the held D
    layer; the following R slipped 7.8 mm). With shear-dominance it was refused correctly, but the cube slid 13 mm
    in the grip.
  * `INFERENCE` (D6 finding 1): with a one-layer hold, "turn U" and "turn D plus rotate the cube" satisfy equal and
    opposite loads equally well, so the outcome is physically ambiguous.
  * `FACT` the P2 integration hold already placed the G2 pads on D and E only (P2 §4).
* **Affected Phase 2 plan sections.** Plan Task 5 (stabilisation); Plan Neg "Tool touches two layers by mistake"
  (needs scoping, see contradiction X-3); E2-2 ("two layers, stabilizer finger": consistent); G2 "Stable classical
  stabilization".
* **Acceptance test.** In every E2-2 and E2-3 trial, log the layer membership (by measured cubie position in the
  core frame) of every Arm A contact at every step. Pass: Arm A contacts lie only on the two declared layers, with
  zero target-layer contacts. **Negative control** (add to E2-9): a deliberate one-layer hold must be refused, or
  end in UNKNOWN or a legal oracle-consistent state; never an illegal state or a wrong-layer turn counted as success.

### R2-02 — Stabiliser clearance to the target-layer boundary

* **Requirement.** The stabiliser fingertip's edge nearest the target layer must stay at least ⟨P⟩ 1.5 mm from the
  target-layer boundary, in the worst case. The budget must include gravity-compensation sag, the axial shift of the
  G2 fingertip with opening (L(d)), soft-contact creep over the hold, grasp placement error and the cube-size range
  of E2-7. The stabiliser fingertip length along the face axis must be designed for this, not inherited from the
  40 mm G2 pad.
* **Evidence.**
  * `FACT` P2 §4: pads covered cube z −30.9…+9.1 mm; the U layer starts at +9.5 mm. **The margin was 0.4 mm.**
  * `INFERENCE` P2 §2 T2: the residual sag with gravcomp is ≈ 0.4 mm at the TCP, the same size as that margin.
  * `INFERENCE` (geometry, this report): with a 40 mm pad overhanging the D face by 2.5 mm, the pad top sits at
    −s/2 + 37.5 mm and the U boundary at +s/6, so the pad touches U for any cube side s < 56.25 mm. E2-7 sweeps
    55–58 mm, so the stock-length pad would breach the target layer at the small end of the sweep.
  * `FACT` the G2 fingertip moves ≈ 11 mm axially over the stroke (L(d), PHASE_2_ROBOT_MODEL_FINDINGS §4).
* **Affected sections.** Plan Task 2 (fingertips, clearance), Task 3 (grasp approach), Task 7 (fingertip benchmark);
  E2-4 (axial offsets 0, ±1, ±2, ±3 mm); E2-7 (cube size).
* **Acceptance test.** (a) Static budget table (sag + L(d) + creep × hold time + placement + cube size) showing a
  worst-case margin ≥ ⟨P⟩ 1.5 mm. (b) Dynamic: minimum stabiliser-to-boundary distance logged in every E2-2, E2-3
  and E2-7 trial; pass if never below ⟨P⟩ 1.0 mm and zero target-layer contacts.

### R2-03 — Shear-dominance margin from the reaction split

* **Requirement.** During a turn, the stabiliser must take enough of the reaction torque through the **middle**
  layer that the outer non-target face's boundary shear stays well below the target face's. Proposed design margin:
  target shear ≥ ⟨P⟩ 2.0 × the next face's shear, above the rule's 1.5×.
* **Evidence.**
  * `FACT` M2 pre-registration Amendment 1 (A2): a face requests unlock only if |shear| ≥ 0.05 N·m **and**
    ≥ 1.5 × the next face's |shear|; otherwise the cube refuses.
  * `FACT` `switching.py`: shear is computed per **face** layer. The middle layer E is not a face, so stabiliser
    torque applied to E cubies counts towards no face.
  * `INFERENCE`: with a D + E hold, the D shear equals the share of the reaction that passes through D. For U to
    dominate by 1.5×, at least about one third of the reaction must pass through E (half for a 2× margin). A grip
    that loads mainly the D layer approaches the ambiguous one-layer case of R2-01.
* **Affected sections.** Plan Task 5, Task 6; E2-2 (counter-torque capacity); E2-6 (contact-force map).
* **Acceptance test.** Log, at every unlock request and refusal, the shear of all six faces and the ratio of the
  largest to the second largest. Report the distribution. Pass (⟨P⟩): every intended turn unlocks with ratio
  ≥ 2.0. A refusal on an intended turn counts as a failed trial, never as an excluded one.

### R2-04 — Robot fingertips in the switch manager, with a face-grip rule

* **Requirement.** Before any robot-driven turn is scored, the M2 switch manager must (a) register both arms'
  fingertip geoms as gripper geoms, and (b) have a pre-registered, physical-state-only rule for when robot fingertips
  count as gripping face F. Proposal: the summed normal force of fingertip contacts on cubies **currently in F's
  layer** (membership by measured position) exceeds `grip_min_n` (2 N). It must never use the commanded move, the
  arm role or the oracle.
* **Evidence.**
  * `FACT` `src/rubiknetic/cube_physics/switching.py` (docstring and `shears()`): the unlock condition "F's own pads
    grip … above `grip_min_n`" only counts geoms named `pad_{F}a_g`/`pad_{F}b_g` (the Phase 1 rig pads).
    "Gripper geoms without a face (stabilisers, later fingertips) add shear but never grant a face's grip."
  * `FACT` P2 `integration_hold_m2.py` did not call `register_gripper_geoms` for the G2 pads. No turn was requested,
    so this had no effect on that hold test.
  * `INFERENCE`: under the frozen rule, a turn driven only by robot fingertips can never satisfy the grip condition,
    so M2 can never unlock and no robot turn can complete. D6 succeeded only because the turner was still the
    Phase 1 rig (face-named pads).
* **Affected sections.** Plan Task 6 (arm B target-layer engagement and turns); Plan Exit ("repeatable physical face
  turns"); E2-3; E2-9 ("forced relink impulse (M2)").
* **Acceptance test.** Unit tests before E2-3: (1) the fingertip geoms of both arms are registered; (2) an Arm B
  grasp on the U layer with ≥ 2 N grants U grip; (3) an Arm A D + E grasp never grants U grip; (4) a grasp spanning
  two face layers grants both, and the shear-dominance rule then decides; (5) the existing audit tests (illegal
  `eq_active` write, `qpos` write) still fail as before. **Decision needed:** this changes a frozen M2 rule input,
  so it needs an amendment and user approval (see open question Q-1).

### R2-05 — Turn completion within 0.5°

* **Requirement.** The classical turning controller must end every turn with the centre hinge within **0.5°** of a
  multiple of 90° and every layer cubie within **0.5°** of the lattice (the M2 relock tolerances in force).
* **Evidence.**
  * `FACT` Amendment 2 → 3: B1 (1.0° per-cubie relock) failed its smoke check; the fallback (setup ±0.25°/face,
    hinge and per-cubie relock both 0.5°) is in force.
  * `FACT` Amendment 3: the default turner (turn_kp 5) left layers 0.8–1.4° from square, so layers stayed unlocked
    and later turns were refused (7/9 and 4/9). With turn_kp 20, kv 0.8: 9/9 on 3 seeds, worst error 0.16–0.31°.
  * `FACT` Amendment 3 disclosed limitation: "the robot's turning controller must finish turns within about 0.5°" is
    a Phase 2 requirement.
* **Affected sections.** Plan Task 4 (impedance control), Task 6; E2-3 (currently ±2°, see contradiction X-1);
  Plan Exit ("registered tolerances").
* **Acceptance test.** In E2-3: per trial, record the final hinge error, the worst layer-cubie error, and whether a
  relock event occurred within ⟨P⟩ 1 s of the controller declaring the turn complete. Pass: all three hold in every
  trial (or the pre-registered success rate). Report the error distribution against both 0.5° (M2) and the D5 band
  (R2-20).

### R2-06 — End-of-turn unloading for relock

* **Requirement.** After reaching the target angle, the turning controller must bring the target layer's boundary
  shear below `tau_relock` (0.02 N·m) and the hinge speed below `omega_relock` (0.05 rad/s) while staying within
  0.5°, before releasing or starting another move. No perpendicular turn may start until the cube is relocked.
* **Evidence.** `FACT` M2 pre-registration §1 relock rule (and `switching.py` docstring): hinge ≤ 0.5°, every layer
  cubie ≤ 0.5°, pad torque (now boundary shear) < 0.02 N·m, hinge speed < 0.05 rad/s, and turned > 45° or > 1 s.
  `FACT` §1 refusals: a request while another layer is unlocked is refused. `INFERENCE`: an impedance controller
  holding a residual torque above 0.02 N·m, or the stabiliser's own shear on the target layer, would keep the layer
  unlocked indefinitely.
* **Affected sections.** Plan Task 6 ("release and stable stop"); Plan Neg "Gripper opens mid-turn".
* **Acceptance test.** Log relock latency (turn-complete declared → relock event) in every E2-3 trial; pass if
  ≤ ⟨P⟩ 1 s in all trials, with zero "still unlocked at next move" events. Report the boundary shear at release.

### R2-07 — Declared layer-angle feedback source

* **Requirement.** The Phase 2 classical controller must declare which signal it uses to finish turns within 0.5°:
  J7 encoder only, or privileged simulator layer angle (allowed in early development under D-10 and spec §9.2, but
  logged). The J7-to-layer angle discrepancy must be measured.
* **Evidence.** `INFERENCE`: grip compliance and slip mean that the J7 angle is not the layer angle; the 0.5°
  requirement (R2-05) is tight compared with soft-contact penetration of 0.07–0.29 mm (P2 §4, `FACT`) on a ~28 mm
  lever arm. `FACT` D-10: final evaluation uses camera-derived state.
* **Affected sections.** Plan Task 4; spec §8 observations; Phase 5 (later camera accuracy requirement).
* **Acceptance test.** E2-3 reports, per trial, |J7 rotation − layer rotation| at turn end. If a J7-only controller
  meets R2-05, record it as the baseline. If privileged feedback is needed, record the angular accuracy that Phase 5
  perception must then supply.

### R2-08 — Ramped gripper closing

* **Requirement.** The gripper close command must be speed-limited (ramped position target, within the G2's
  15–225 mm/s), and the grasp must settle before any external load or turn. A step close is not allowed in scored
  trials.
* **Evidence.** `FACT` P2 §4 preserved negative result (step close, 0.5 s setup): at 10 N a 75 N impact spike and the
  cube dropped; at 30 N the impact bounced the free cube out of the grip; at 50 N it held but shifted ≈ 5 mm, with 6
  non-pad robot contacts and 1.38 mm penetration. `FACT` with a 0.5 rad/s ramp (≈ 26 mm/s per pad) all three forces
  held: slip ≤ 0.093 mm, no non-pad contacts, penetration ≤ 0.29 mm.
* **Affected sections.** Plan Task 2 (gripper limits), Task 4; E2-0 (force calibration); E2-2.
* **Acceptance test.** E2-0 sweep of closing speed (e.g. 15, 26, 50, 100, 225 mm/s per pad) at 10/30/50 N. Report the
  bounce boundary. Pass for the chosen default: peak normal force ≤ ⟨P⟩ 1.2 × set-point, cube displacement during
  closing ≤ ⟨P⟩ 0.5 mm, zero non-pad robot–cube contacts.

### R2-09 — Gravity-on grasp from a modelled support

* **Requirement.** Scored Phase 2 trials must start with gravity on and the cube resting on a modelled support (table,
  fixture or the other arm), with the approach motion simulated. The gravity-off setup used in D6 and P2 is a
  diagnostic only.
* **Evidence.** `FACT` D6: "gravity is off for 0.3 s while the holder closes" (diagnostic). `FACT` P2 §4: gravity off
  for 2.0 s during closing; listed as a limit ("no approach motion is simulated").
* **Affected sections.** Plan Task 3 (grasp approach configurations); E2-2; Plan Neg "Robot collides with table".
* **Acceptance test.** Trial logs show constant gravity from t = 0. The edit audit covers the whole episode; the only
  pre-step write is the registered initial cube placement. Report lift-off slip and penetration.

### R2-10 — Soft-contact creep during holds

* **Requirement.** (a) The slip metric must separate steady soft-contact creep from Coulomb slip events. (b) Before
  holds longer than ⟨P⟩ 10 s are relied on, run an unscored study of pad `solref`/`impratio` (and fingertip contact
  parameters) against creep rate. (c) Every protocol must declare its maximum hold duration and show that
  accumulated creep stays within its slip threshold, or include a feedback re-centre or regrasp. (d) Disclose creep
  as a simulator artefact.
* **Evidence.** `FACT` P2 §4: core slip creeps steadily at ≈ 0.02 mm/s at every grip force (10/30/50 N), while
  friction use is only 1.3–7.3 % of μ. `INFERENCE`: MuJoCo soft-friction creep under sustained tangential load, not
  Coulomb slip; ≈ 1.2 mm/min. `INFERENCE`: E2-2's 0.5 mm slip limit is reached after ≈ 25 s of hold.
* **Affected sections.** Plan Task 5; E2-2 (slip ≤ 0.5 mm); E2-5 (no grasp slip > 1 mm); E2-6 (slip velocity);
  later Phase 4/6 multi-move holds.
* **Acceptance test.** 60 s holds at 10/30/50 N, baseline and with each mitigation; report the creep rate (mm/s, fit
  over the last 50 s) and the Coulomb-slip events. Pass (⟨P⟩): the selected configuration has creep ≤ 0.005 mm/s, or
  every protocol's declared hold time × measured rate ≤ half its slip threshold.

### R2-11 — Gripper calibration regression and per-width recalibration

* **Requirement.** Keep the P2 calibration as regression tests (85 mm open limit, stroke, spring-offset-free force),
  and recalibrate the force map at the **actual contact width** of each custom fingertip, since thicker fingertips
  change the gap at contact and hence k and the spring term.
* **Evidence.** `FACT` P2 §2 T3: open 84.73 mm, closed 1.64 mm, stroke **83.1 mm** (spec 84 ± 1 mm; within the band
  by 0.1 mm). `FACT` T4 at 57 mm, after removing the linkage-spring offset (0.2282 N·m ≙ 2.22 N): errors +0.32 /
  −0.03 / −0.16 N at 10/30/50 N (before: +2.05…+2.44 N). `FACT` P2 §5: calibrated at 57 mm only. `ASSUMPTION` 57 mm
  contact width.
* **Affected sections.** Plan Task 2; E2-0 (force calibration map); E2-6 (10–50 N sweep).
* **Acceptance test.** Regression: stroke within 84 ± 1 mm; open gap 85 ± 0.5 mm. Calibration: at each fingertip's
  contact gap (and at ±2 mm), |measured normal force − set-point| ≤ ⟨P⟩ 0.5 N at 10, 30, 50 N. The calibration
  table becomes an E2-0 output.

### R2-12 — Tool frame from the simulated four-bar pose

* **Requirement.** Layer targeting and grasp planning must use the fingertip pose from forward kinematics of the
  simulated four-bar at the current opening, not the fixed 0.172 m TCP.
* **Evidence.** `FACT` G2 manual formula L = 121.606 + √(55.000² − (0.5d − 8.997)²) mm: 175.9 mm at d = 0, 165.2 mm at
  85 mm (≈ 11 mm axial travel). `INFERENCE` (formula): L(57 mm) ≈ 173.0 mm against 176.3 mm at the STEP pose
  (29.16 mm), a 3.3 mm difference, which is larger than the R2-02 margin. `FACT` P2 T3 matched the STEP fingertip
  span at the STEP pose.
* **Affected sections.** Plan Task 2 (tool frames); E2-0 ("verify the G2 L(d) axial-offset model"); E2-1 (tool-frame
  FK error < 0.1 mm).
* **Acceptance test.** E2-0: simulated pad-centre position along the gripper axis against L(d) at ≥ 5 openings;
  pass if |error| ≤ ⟨P⟩ 0.3 mm. E2-1: the tool frame used by the planner is a function of opening.

### R2-13 — Fingertip mount interface (provisional)

* **Requirement.** Fingertip models C1, C2 (and contingencies) are parameterised on the measured mount interface:
  2 × M3 (provisional), 12.0 mm pitch on the finger centreline, ≈ 3 mm engagement in a 5 mm plate, 32 × 40 mm
  envelope, mount face at |x| = 21.58 mm. Fingertip mass and plate thickness are modelled. **No detailed CAD release
  or manufacture until the caliper check is recorded.**
* **Evidence.** `FACT` P2 §3 STEP measurement (shank Ø3.0 mm, head Ø5.5 mm, 12.0 mm pitch at 146.3 and 158.3 mm from
  the flange face). `INFERENCE` M3 thread. `FACT` P-17: "fingertip mount 2×M3 at 12 mm provisionally (caliper check
  before manufacture)". `FACT` P-03: simulation primitives only, no CAD.
* **Affected sections.** Plan Task 2 ("attach research-approved custom passive fingertip geometry"); G2 "Approved
  passive fingertip candidate accurately mounted"; Deliverables.
* **Acceptance test.** (a) Caliper record (thread, pitch, hole depth, mount flatness, locating features) logged in
  the decision log. (b) In simulation, each fingertip's gripping face is within 0.1 mm of mount face + designed
  thickness, checked by script.

### R2-14 — Fingertip contact model (torsional friction)

* **Requirement.** Fingertip–cubie contacts must use `condim` ≥ 4 (torsional friction), or the report must justify
  `condim` 3 with a comparison.
* **Evidence.** `FACT` P2 §4 limits: the G2 pads are Menagerie boxes with `condim` 3 and no torsional friction.
  `FACT` E2-6 plans a torsional-coefficient sweep, which needs `condim` ≥ 4 to have any effect. `INFERENCE`: in the
  coaxial grasp (P-04) part of the turning torque is carried by torsional friction at the pad patch.
* **Affected sections.** Plan Task 2, Task 7; E2-6.
* **Acceptance test.** E2-6 includes a `condim` 3 vs 4 (vs 6) comparison at nominal μ; report the change in success
  rate and in the minimum grip force for success.

### R2-15 — Conservative joint envelope until the hardware revision is confirmed

* **Requirement.** Until the user confirms the xArm7 revision, plan and score with the **intersection** of both
  builds: joint ranges per `--clip-1305-spec-limits` (J2 −117…116°, J4 −6…225°, J6 −97…180°) and, per joint, the
  smaller of the two torque tables (163.2, 163.2, 81.6, 81.6, 81.558, 30.6, 30.6 N·m). Rerun E2-1 and the headline
  E2-3 on the confirmed revision once known.
* **Evidence.** `FACT` P-17: revision pending, model default 1305+, clip flag off by default. `FACT` torque tables
  (pre-1305 163.2/163.2/81.6/81.6/81.6/30.6/30.6; 1305+ 179.44/179.44/92/92/81.558/30.6/30.6). `FACT` URDF ranges
  (J2 −118…120°, J4 −11…225°) are wider than the 1305 spec. `INFERENCE` the intersection is valid for either
  revision. The pre-1305 spec-sheet ranges were not found; only the URDF ranges are known for that revision.
* **Affected sections.** Plan Task 1 ("verify … original kinematics, joint limits"), Task 3 (workspace); E2-1.
* **Acceptance test.** E2-1 builds and checks both revisions; the workspace overlap and grasp configurations are
  reported for both. Any trial whose commanded or measured joint state leaves the intersection is flagged.

### R2-16 — URDF peak torques as working limits

* **Requirement.** Actuator saturation equals the URDF peak efforts (approved as working limits). Because these are
  peak/overload values, every trial must log the per-joint max |τ|/limit and the time spent above a derived
  non-overload value (peak ÷ documented overload factor), flagged but not failed.
* **Evidence.** `FACT` P-17 approval. `FACT` RM-03: "max torque = torque constant × 100 × 2.55 (overload limit)"
  (pre-1305); 1305 overload factors 1.879/2/1.773/2.04. `FACT` P2 T2: peak hold torque 0.12–0.19 of the limit.
  `INFERENCE` J7 (30.6 N·m) exceeds the 0.03–0.6 N·m cube-turn bracket by > 30×, so wrist torque is not limiting.
* **Affected sections.** Plan Task 4 (actuator saturation and limits); Plan Exit ("reasonable … force
  characteristics"); E2-5, E2-6.
* **Acceptance test.** Torque log present in every trial; a summary table per experiment. Flag (⟨P⟩) any joint above
  its derived non-overload value for > 1 s.

### R2-17 — Joint and gripper speed limits in the controller

* **Requirement.** The controller enforces arm joint speed ≤ 3.14 rad/s and gripper finger speed within 15–225 mm/s,
  because MuJoCo does not enforce velocity limits.
* **Evidence.** `FACT` PHASE_2_ROBOT_MODEL_FINDINGS §2.1/§3: no velocity limits in the MJCF; URDF and spec 3.14 rad/s
  (180°/s); G2 15–225 mm/s. `FACT` P2 §5 gap 3.
* **Affected sections.** Plan Task 4.
* **Acceptance test.** Per trial, max |q̇| ≤ 3.14 rad/s and finger speed ≤ 225 mm/s; any violation fails the trial.

### R2-18 — Gravity compensation and sag

* **Requirement.** Actuator-routed gravity compensation stays on (no `xfrc_applied`/`qfrc_applied` writes). The
  static TCP error from sag enters the R2-02 budget. Because compensation is ideal (it uses the model's own masses),
  E2-7 must test a gravcomp mass error.
* **Evidence.** `FACT` P2 T2: servo-only sag 0.0154 rad (J4, home) and 0.0140 rad (J2, reach); with gravcomp 0.00086
  and 0.00050 rad; arm `qfrc_passive` 0; external force arrays stayed 0. `INFERENCE` residual ≈ 0.4 mm at the TCP
  from the uncompensated finger bodies (0.21 kg). `FACT` model mass 12.07 kg vs 14.3 kg (1305 manual), gripper
  0.751 kg vs 0.80–0.82 kg.
* **Affected sections.** Plan Task 1 (mass), Task 4; E2-1; E2-7.
* **Acceptance test.** E2-1: static TCP error at ≥ 3 grasp poses ≤ ⟨P⟩ 0.5 mm. E2-7: gravcomp masses scaled by
  ±20 % (covers the 12.07 vs 14.3 kg mismatch); pass if layer selectivity and turn outcomes are unchanged.

### R2-19 — Throughput

* **Requirement.** E2-8 measures the full two-arm + M2 + controller model headless on an otherwise idle machine,
  with ≥ 3 repeats, and records machine load, timestep and solver settings. It also reports whether a 1 ms timestep
  keeps the M2 switch criteria (E1-5) clean.
* **Evidence.** `FACT` one arm + G2 + M2 at dt 0.5 ms: 786–840 steps/s (first run), 408–593 (machine loaded),
  ≈ 0.2–0.4× real time (P2 §4). `FACT` M2 alone 1,350–2,030 steps/s (pre-registration header); robot alone 3,500–
  19,100 steps/s at dt 2 ms, noisy (P2 T5). `FACT` the merged model inherits the cube's 0.5 ms timestep.
  `INFERENCE` the two-arm model will be slower than 400–840 steps/s.
* **Affected sections.** Plan Task 8; E2-8; R4 (spec §4); Phase 3 go/no-go.
* **Acceptance test.** Published table: median and spread of steps/s and real-time factor for (a) one arm + M2,
  (b) two arms + M2, (c) (b) plus controllers, each with rendering off. A throughput floor for Phase 3 is proposed
  from it, together with the estimated RL sample budget.

### R2-20 — D5 as the forgiveness reference

* **Requirement.** Phase 2 reports must state that M2's 0.5° completion requirement is a property of the model, and
  compare the classical controller's end-of-turn errors with the frozen D5 reference band. D5 is never used for
  scoring.
* **Evidence.** `FACT` D5 frozen design B: completes R at +3.2° misalignment, jams at −2.5° (one-sided forgiveness
  ≈ 3–4°); penetration ≤ 1.51 mm (above the 0.5 mm limit); 62 steps/s. `FACT` P-17: D5 is the unscored high-fidelity
  reference. `INFERENCE` (Amendment 3): M2 is far less forgiving than D5 or, per vendor claims, a speedcube.
* **Affected sections.** Plan Exit ("registered tolerances"); E2-3 reporting; Deliverables.
* **Acceptance test.** An E2-3 annex table: fraction of turns ending within 0.5° (M2) and within D5's band
  (−2.5…+3.2°). Optional, unscored: replay the controller's end-error distribution as setup misalignments on the D5
  rig (`forgive_rig.py`).

### R2-21 — Initial alignment within the M2 envelope

* **Requirement.** Every scored Phase 2 trial starts with the cube within ±0.25° per face (the M2 setup envelope
  in force), and the stabiliser grasp must not move any cubie more than ⟨P⟩ 0.25° from the lattice.
* **Evidence.** `FACT` Amendment 3: setup ±0.25° per face is in force. `FACT` Amendment 1: ±1° per face compounds to
  1.22° median worst piece, above the 1.0° unlock tolerance. `FACT` P2 §4: grasp lattice deviation ≤ 0.012°.
* **Affected sections.** Plan Task 5; E2-2; E2-5 (misalignment injection concerns the robot, not the cube).
* **Acceptance test.** Log per-cubie lattice deviation at t = 0 and after grasp settle in every trial. Trials that
  violate the setup envelope are invalid by construction (and counted), never silently excluded.

### R2-22 — Controller and supervisor never read M2 lock state

* **Requirement.** The classical controller and supervisor decide turn completion from physical observations only
  (poses, encoders, later cameras). They never read `eq_active`, `eq_data` or switch-manager state. Only the
  evaluator and logs may.
* **Evidence.** `FACT` M2 pre-registration §1: rule inputs are physical state only. `FACT` spec D-06 and §5.2.
  `INFERENCE`: lock state has no real-cube counterpart, and reading it would leak the model's internals into control.
* **Affected sections.** Plan Task 4, Task 6; spec §7 `CubePhysics` contract.
* **Acceptance test.** A static test (import or attribute check) that controller and supervisor modules do not
  access `eq_active`, `eq_data` or `SwitchManager`; plus a run-time audit hook.

### R2-23 — Asset provenance

* **Requirement.** Vendor the BSD-3 Menagerie and `xarm_ros2` assets (licences preserved) when Phase 2 starts.
  STEP-derived files stay in git-ignored `third_party_cad/` unless the user decides to publish them. Every generated
  model records its source commits and hashes.
* **Evidence.** `FACT` P-17 approvals; `FACT` RM-01/RM-03 BSD-3-Clause; `FACT` UFACTORY STEP licence unverified
  (findings §2.4), use permitted locally by the user.
* **Affected sections.** Plan Task 1 ("confirm asset licenses"); E2-1 ("Model provenance"); Deliverables.
* **Acceptance test.** E2-1 check: every vendored file has a licence notice and a source commit; no STEP-derived
  file is tracked by git.

---

## 3. Contradictions between the Phase 2 plan (and E2-x) and these findings

| ID | Plan text | Finding | Proposed resolution |
|---|---|---|---|
| X-1 | E2-3: "Turn within ⟨P⟩ ±2°" | M2 relocks only within 0.5° (Amendment 3, `FACT`). A turn ending at 1–2° stays unlocked, and the next move is refused | Tighten E2-3 to R2-05 when the cube model is M2, or add relock as a separate pass criterion |
| X-2 | Plan Task 6 and Exit assume a robot can drive a physical turn | The frozen switch rule grants face grip only to Phase 1 rig pads (`switching.py`, `FACT`); robot fingertips cannot unlock any face | R2-04 amendment, approved before any robot turn is scored |
| X-3 | Plan Neg "Tool touches two layers by mistake: reject face turn"; E2-9 "Two-layer contact by design (oversized tip)" | The stabiliser **must** touch two layers (R2-01) | Scope both to the **turning** arm (Arm B) and to the target layer's neighbours |
| X-4 | E2-2: "The E1 contact probe applies a torque ramp" | The Phase 1 rig is fixed at the world origin and sits inside the robot base, so P2 removed it (`rig=False`, P2 §4) | Relocate the rig in the Phase 2 world, or use Arm B as the probe (then E2-2 and E2-3 merge) |
| X-5 | Plan Task 1 "Import two distinct xArm7 MJCF instances, verify … original kinematics … mass"; Task 2 "Load compatible parallel-jaw gripper models"; E2-1 "Load 2 × Menagerie xArm7 (pinned commit)" | No G2 MJCF exists; the model is generated from Menagerie + URDF torques + converted G2 meshes + gravcomp + an 85 mm limit + a 3 mm pad extension. The model mass (12.07 kg) does not match the manual (14.3 kg) | Reword E2-1 to "the generated model from pinned sources, with documented deviations"; record the mass mismatch as a known gap |
| X-6 | E2-2 slip ≤ 0.5 mm; E2-5 slip ≤ 1 mm | Soft-contact creep alone reaches 0.5 mm in ≈ 25 s (`INFERENCE` from 0.02 mm/s) | R2-10: declare hold durations, separate creep from slip |
| X-7 | Plan Task 4 "force-aware contact control"; Task 7 "Record actual contact forces" | G2 has position-only feedback; the xArm torque register is "for reference only" (`FACT`). Simulated contact forces are privileged | State which force signals the classical controller may use (Q-3) |
| X-8 | E2-6 sweeps a torsional coefficient | Pads are `condim` 3, so a torsional sweep has no effect (`FACT` P2 §4) | R2-14 |
| X-9 | E2-7 cube size 55–58 mm | With 40 mm pads and 2.5 mm overhang, the stabiliser touches U for s < 56.25 mm (`INFERENCE`) | R2-02: design the stabiliser fingertip length to the layer, or vary overhang with size |
| X-10 | Plan prerequisite "G1 physics gate passed" | P2 robot-model work and the integration hold ran before G1 (labelled exploratory and unscored) | Consistent with D-12 (independent work allowed); scored Phase 2 work still waits for G1 |

---

## 4. Top five (by consequence if ignored)

1. **R2-04** — without a fingertip face-grip rule, no robot-driven M2 turn can complete at all.
2. **R2-05** (with R2-06) — turns must end within 0.5° and unload below 0.02 N·m, or M2 refuses every later move.
3. **R2-01 + R2-02** — a two-layer stabiliser is required, and the measured margin to the target layer was only
   0.4 mm.
4. **R2-10** — creep of ≈ 0.02 mm/s sets a hold-time budget of ≈ 25 s against E2-2's 0.5 mm slip limit.
5. **R2-08** — a step close bounced the free cube out; a ramped close is required.

---

## 5. Open questions for the user

| ID | Question |
|---|---|
| Q-1 | Is the R2-04 face-grip change an M2 **model** change (requiring a Phase 1 amendment and re-check of affected E1 criteria), or a Phase 2 interface addition that leaves the rig behaviour unchanged? |
| Q-2 | May the Phase 2 classical controller use the privileged layer angle (logged, per D-10) to reach 0.5°, or must it use J7 encoders only (R2-07)? |
| Q-3 | Which force signals may the classical "force-aware" controller use: simulated contact forces (privileged), a joint-torque estimate, or none (X-7)? |
| Q-4 | What supports the cube before the first grasp: a table, a fixture or a handoff (R2-09)? |
| Q-5 | Should the ramped close become the default gripper command (P2 §6), and at what speed (R2-08)? |
| Q-6 | Investigate creep mitigation now (pad `solref`/`impratio`) or accept a hold-time budget (R2-10)? |
| Q-7 | xArm7 hardware revision (R2-15), and the caliper check of the fingertip mount (R2-13). |
| Q-8 | Should E2-3 adopt 0.5° as its turn tolerance, or keep ±2° for "turn achieved" and add relock as a separate criterion (X-1)? |
| Q-9 | Can the merged model run at a 1 ms timestep without breaking E1-5 (R2-19), given the robot was built for 2 ms and the cube for 0.5 ms? |
| Q-10 | Which overload factor applies to which joint for the 1305 torque table (R2-16)? The project files list four factors for three torque constants without a mapping. |
| Q-11 | In a slow 180° turn, could M2 relock at the 90° crossing (turned > 45°, hinge within 0.5°, speed below 0.05 rad/s)? E1-3 covers this in the rig; Phase 2 should confirm with the robot's speed profile. |
| Q-12 | Should the E2-3 18/20 success rate stand, given that M2's G1 scoring uses Option A (100 %)? |
