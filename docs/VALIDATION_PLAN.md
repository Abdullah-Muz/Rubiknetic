# Rubiknetic — Validation & Acceptance Plan

**Status:** Validation protocol defined, not executed. All tests below start **NOT RUN**.  
**Authority:** `../RUBIKNETIC_MASTER_SPEC.md`.

## General standard

**Evidence over appearance:** A GIF or visually plausible move never substitutes for independently checked physical/logical state, contact trace, and reproducible run. Physical simulations may use simplifications, but report them. No fabricated runs, no invisible resets, no hidden cube-state injection.

Each milestone produces: (1) run command; (2) versioned code/assets/dependencies; (3) machine/OS and CPU baseline; (4) random seeds / scramble; (5) config, timestep and solver parameters; (6) raw machine-readable metrics; (7) outcome + failure reasons; (8) representative video only as supporting evidence; (9) limitations; (10) decision approval and sign-off.

**Threshold policy:** Hard constraints below are categorical (e.g., no teleportation). Numerical tolerances for angle error, force, penetration, energy discontinuity, throughput, success fraction and trial count are **TBD after sourced physical tolerances and Phase 0/1 pilot data**; they must be registered in a versioned experimental protocol *before* evaluating the final test set. Do not retroactively lower thresholds to pass a failed test.

## Cross-cutting invariants — required on all relevant trials

- **Legal puzzle state:** exactly the same labeled cubies exist; no unintended swaps, detachments or parity/orientation invalidity; independent logical state agrees with observed physically completed turn.
- **Nonteleportation:** no direct edits to cubie pose/velocity, no face-angle setter or injected solver move during claimed physical action. For permissible initial reset/training states, distinguish episode setup from execution and audit for prohibited updates.
- **Contact causality:** face turn trace shows tool contact and physically applied wrench/torque responsible for motion; no hidden torque actuator on the layer.
- **Constraint consistency:** activated topology matches the current physical configuration; no unvalidated forced corrections, unintended large impulses, sustained penetration, or numerical divergence.
- **Joint/force validity:** motor, workspace and contact constraints respected or flagged as failures; never silently cap/hide force events after scoring.
- **Data provenance:** final camera-based cube state must not be contaminated by privileged simulator cube truth; audit and training paths separate.

## Phase gates

### G0 — Literature and feasibility (Phase 0)

**Evidence:** source register, relevant primary bibliography; cube mechanisms study; >=6 candidate fingertip concepts, 2–3 deep comparisons; uncertainty/torque and clearance estimates; simulator risk register; design decision matrices and candidate selections.

**Pass:** All claims traceable; top candidates and their falsification tests identified; user explicitly approves mechanism/gripper direction. If impossible to substantiate, mark conditional/blocked.

### G1 — Mechanically credible cube physics (Phase 1)

**Tests:**

- [x] Logic: move + inverse identity, 4× quarter-turn identity, valid generated scrambles, parity and orientation invariants. *(`tests/test_cube_logic.py`, 59 tests, PH1-02)*
- [x] Physically actuated one quarter-turn from both direction signs; state agrees with logical oracle. *(M7 E1-2 24/24)*
- [x] Physically actuated half-turn and reverse-turn trials. *(M7 E1-3 22/22, E1-2 counter-clockwise)*
- [x] Consecutive nonparallel-axis turns, including `R U R' U'` and repetition/inverse sequences. *(M7 E1-4 40/40)*
- [x] No target-angle setter, teleportation, hidden layer actuator or programmatic forced turn during scored trials. *(M1 rule 2 edit audit on every trial; observed-move oracle; E1-6a)*
- [x] Trace switch timing, force/torque, angular velocity, penetration, continuity and solver tolerance sensitivity. *(No switches in M7; torque, penetration and E1-6m per move; E1-7 sensitivity, with fragilities at 0.75 ms and a 0.1 mm gap)*
- [x] CPU benchmark in several contact/topology configurations. *(M7 E1-8, `experiments/E7_scored_m7/results_E1-8/bench.json`)*

**Pass:** all categorical invariants hold; calibrated quantitative tolerances met in pre-registered trials; mechanism abstraction and limitations published. A one-turn-only demo is insufficient.

**G1 sign-off (2026-11-26, DECISION_LOG P-95):** **PASS for mechanism M7**, approved by the user, with the
limitations of [`../experiments/E7_scored_m7/G1_REPORT_M7.md`](../experiments/E7_scored_m7/G1_REPORT_M7.md) §3 as its
stated scope. Evidence: the scored battery under
[`../experiments/PHASE_1_M7_PREREGISTRATION.md`](../experiments/PHASE_1_M7_PREREGISTRATION.md) revision 4 (204/204,
P-93), E1-8, the logic tests, and the published abstraction and limitations. Next authorised phase: **G2, starting with
design**.

### G2 — Two-arm manipulation (Phase 2)

- [x] Distinct xArm7 instances with validated tool frames, limits, collision geometry. *(layout IK, joint margins B ≥ 19.1°, A 28.9°; no judged contact in 128 scored trials; G2-7 collision 2/2; P-143)*
- [x] Approved passive fingertip candidate accurately mounted to selected grippers. *(P-97 stabiliser pads, C1 turner P-107; no non-fingertip robot–cube contact)*
- [x] Stable classical stabilization against a physical rotating layer. *(G2-1 holds 20/20; per-move core slip ≤ 0.26 mm, rotation ≤ 1.24°)*
- [x] Contact-driven 90° and 180° turns across multiple starts, no unintentional adjacent-layer rotation. *(G2-2…G2-4 100/100, 360 moves; turn error ≤ 0.41°, drift ≤ 0.31°)*
- [x] Collision/force/clearance logs and sensitivity to alignment and friction. *(per-move logs; G2-6 screen; G2-7 8/8)*

**Pass:** repeatable physical turns with prescribed classical controllers; no RL needed to pass.

**G2 PASSED for M7 (2026-11-28, user sign-off, P-144)** with the limitations of [`../experiments/E8_scored_g2/G2_REPORT.md`](../experiments/E8_scored_g2/G2_REPORT.md) §6.

### G3 — RL experimental validity (Phase 3)

- [ ] Action/observation/frame specification and reward unit tests.
- [ ] Classical B0 and no-op/random residual controls evaluated on matched starts.
- [ ] SAC residual policy trained with seed/config/checkpoint/logging and held-out evaluation; PPO optional.
- [ ] All physics validity checks remain active during RL evaluation.
- [ ] Report training steps, wall time, CPU resources, uncertainty and negative cases.

**Pass:** scientifically honest reproducible comparison, not necessarily an RL win.

### G4 — Multi-move bimanual autonomy (Phase 4)

- [ ] Unique cube/orientation/arm frames validated; no ambiguous move notation.
- [ ] Planner generates only kinematically feasible, collision-checked candidate actions.
- [ ] Regrasp, support transfer and role swap performed without cube teleportation.
- [ ] Physical/logical state continuity across multiple nonparallel moves verified.
- [ ] Failed manipulations trigger bounded retry/replan/stop, not a hidden reset.

**Pass:** independent multi-move autonomous demonstrations with reproducible state traces.

### G5 — Camera-derived estimation and recovery (Phase 5)

- [ ] Calibrated RGB camera extrinsics and image reproduction.
- [ ] Sticker color/face pose estimation; explicit confidence/unknown output.
- [ ] Multi-view reconstruction of all necessary facelets and independent legality validation.
- [ ] No simulator cubie truth supplied to final perception-based planner.
- [ ] Injected failures (missed rotation, slip, pose ambiguity) detected or appropriately safe-stopped.

**Pass:** correctly classifies tested states and selects recovery/stop behavior under held-out camera/lighting/pose variations.

### G6 — Integrated full-cube solves (Phase 6)

- [ ] Legal scrambles generated from independent symbolic oracle.
- [ ] System observes, plans and executes through robot contacts only.
- [ ] All face rotations, gripper releases, handoffs and state verifications traced.
- [ ] At least one uninterrupted, independently verified full solve on a nontrivial legal scramble.
- [ ] Evaluation expanded to a pre-registered distribution of randomized unseen scrambles (target: 100 trials if compute allows, not an implied completed result).

**Pass:** independently verified solved states and transparent success denominator/failure taxonomy; must not require hidden mid-episode reset.

### G7 — Reproducible release (Phase 7)

- [ ] Locked dependencies and documented environment/hardware requirements.
- [ ] Runnable demonstration and benchmark commands tested from clean environment.
- [ ] Classical/RL ablations with equal evaluation conditions, seeds and confidence estimates.
- [ ] GPU optional, CPU throughput limitations reported.
- [ ] Code/CAD/robot assets and puzzle name licenses/permissions checked.
- [ ] Technical report includes negative and uncertain outcomes; no false novelty or sim-to-real claims.

**Pass:** a reader can reproduce claims without privileged information omitted from docs.

## Failure taxonomy

`ILLEGAL_CUBE_STATE`, `WRONG_LAYER_TURN`, `INCOMPLETE_FACE_TURN`, `CUBIE_DETACHED`, `CUBIE_PENETRATION`, `CONSTRAINT_IMPULSE`, `CONTACT_SLIP`, `EXCESS_FORCE`, `ROBOT_COLLISION`, `UNREACHABLE_GRASP`, `HANDOFF_FAILURE`, `CAMERA_AMBIGUOUS`, `STATE_ESTIMATION_ERROR`, `PLANNER_FAILURE`, `POLICY_FAILURE`, `SIM_NUMERICAL_ERROR`, `CPU_TIMEOUT`, `OTHER`.

## Trial record template

```yaml
experiment_id: TBD
phase_gate: G1
status: NOT_RUN
source_commit: TBD
model_asset_revision: TBD
python_mujoco_versions: TBD
os_cpu_ram: TBD
sim_timestep_s: TBD
solver_settings: TBD
seed: TBD
scramble: TBD
initial_poses: TBD
controller_mode: TBD
privileged_state_used_for_decisions: TBD
trial_outcome: TBD
observed_logical_state: TBD
contact_wrench_trace: TBD
constraint_switch_events: TBD
illegal_pose_edits_detected: TBD
fail_reason: TBD
metrics_path: TBD
video_path: TBD
```

## Sign-off protocol

`gate_id`, `date`, `approver`, `test_evidence_paths`, `tolerances_and_trial_counts_pre_registered`, `PASS/CONDITIONAL/BLOCKED`, `unresolved_risks`, `next_authorized_phase`. Record the approval in `docs/DECISION_LOG.md`. Never auto-check a task as complete based only on code presence.
