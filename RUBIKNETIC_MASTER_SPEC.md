# Rubiknetic — Master Engineering & Research Specification

**Version:** 1.0 (planning baseline)  
**Date:** 2026-11-12  
**Status:** Architecture decisions approved; research and physics feasibility **not yet validated**  
**Scope authority:** This document; approved changes are recorded in `docs/DECISION_LOG.md`.

## 1. Mission and engineering thesis

Build a reproducible, CPU-first, simulation-based bimanual robotic manipulation system that can autonomously solve **legal 3×3 Rubik's Cube scrambles** through real simulated robot-object interactions. Two seven-axis robot arms must grasp, stabilize, rotate one cube layer relative to another, regrasp, hand off, and verify the results. The project must distinguish a symbolic cube solution from the complex physical manipulation required to execute it.

**Research hypothesis, not an established finding:** A hybrid, hierarchical system combining a symbolic cube solver, manipulation-aware task/motion planning, classical impedance-aware controllers and **bounded residual RL** can yield more robust contact-based cube turns than the classical baseline under matched conditions. Outcomes may be negative.

**Research value:** Contact mechanics, dynamically changing object constraints, bimanual robotics, task-and-motion planning (TAMP), reinforcement learning, vision-based feedback, controlled evaluation.

## 2. Approved decisions (locked unless reviewed)

| ID | Decision | Technical interpretation |
| --- | --- | --- |
| D-01 | Project name: **Rubiknetic** | Public working name, branding rights still to be checked |
| D-02 | **MuJoCo** primary simulator | MJCF, measured CPU throughput; no alternative simulator necessary unless feasibility results require reconsideration |
| D-03 | **2 × UFACTORY xArm7** | 7-DOF per arm, two separate robot control interfaces; verify imported model kinematics and licenses |
| D-04 | Parallel-jaw end effectors with **research-led custom fingertips** | Exact gripper variant and geometry **not selected**; full literature/design review before detailed CAD |
| D-05 | **Dynamic cubie constraints** | A legal 3×3 model with constraint relationships that adapt after face turns; switching is not permitted to supply rotation energy or teleportation |
| D-06 | **Level C physical manipulation** | Face rotation is driven by modeled robot contacts/torques; no scripted cube angles in evaluated runs. Passive internal cube mechanisms (springs, documented magnet pairs or detents acting between specific pieces, with realistic strengths) may contribute alignment forces, but turns must be initiated and driven by robot contact (P-16, approved 2026-11-13) |
| D-07 | **Reinforcement learning is in scope** | Hierarchical/residual RL used for selected contact tasks; classical control remains a necessary baseline |
| D-08 | **E + C + D control** | High-level task hierarchy + bounded residual Cartesian motion corrections + force/impedance-aware low-level control |
| D-09 | **One learned arm first** | Initial stabilizer classical, turning arm RL-assisted; eventual role swapping and bimanual coordination |
| D-10 | **Camera perception is the final goal** | Simulator privileged state permitted only in designated debug/training/baselines; final independent vision test |
| D-11 | **CPU-only target** | Ryzen 7-class CPU, 32 GB RAM, integrated Radeon/WSL2; no CUDA requirement |
| D-12 | **Eight phases (0–7)** | Entry/exit criteria and evidence gates; dependent phases cannot be marked passed early |
| D-13 | **Research first** | Cube mechanics and gripper/fingertip study must be approved before detailed design and RL training |

## 3. Non-goals and guardrails

- Not a mathematical solver alone, animation, joint-teleportation demo, or guaranteed real-hardware deployment.
- Not end-to-end RL from pixels to motor torque as the initial solution, nor a five-finger humanoid hand project.
- No claim of novel physics, manipulation research novelty, real-world fidelity, successful solves, verified mechanical properties, or trained results without evidence.
- No renderer-dependent training requirement; no CUDA dependence; no large GPU-based image-based policy as v1.
- Do not merge handoff, turning, and cube-state changes into a single invisible kinematic macro during reported physical evaluation.

## 4. Major risks and feasibility gates

**R1 — Valid cube connectivity:** The 3×3 cube has 26 external movable cubies, centers/core and varying layer memberships. Static per-layer joints do not automatically reproduce all legal sequential moves. Runtime-switchable constraints such as `mjData.eq_active` are an API capability, **not proof** that a 3×3 cube topology can be made credible. Predeclared constraints are finite; plan the candidate constraint graph, possible overconstraints, and alternative mechanical abstractions. Gate in Phase 0/1.

**R2 — Constraint transition artifacts:** Enabling/disabling constraints might cause impulses, position corrections, penetrations, energy drift or discontinuities. Only switch when measured poses/angles, velocities and contact geometry satisfy mechanical criteria; audit physical consistency and compare multiple timesteps/solver settings.

**R3 — Fingertip access and torque:** Two compact parallel grippers must contact one layer and the remaining cube body without interference. Exact contact envelope, grip force, cube size, face torque and friction remain unknown. Validate them and avoid assuming larger grippers are more dexterous.

**R4 — Contact-rich RL on CPU:** Learning can be slow and reward-sensitive. Benchmark pure simulator throughput, controller overhead, contact stiffness/sensitivities, and resource use before selecting training steps or deadlines.

**R5 — State observability:** All six faces generally require multiple viewpoints or reorientation. A solver-ready cube state cannot be inferred from one arbitrary RGB frame without additional assumptions. Track sticker orientation, color mapping, ambiguity and perception confidence; no hidden simulator state in final vision-gated evaluation.

**R6 — Full-solve integration:** Multi-turn success depends on regrasp transitions, collision-free reachability, role swapping, and reliable state recovery; one successful face turn is not a full-solve claim.

## 5. Physical and logical modeling contract

### 5.1 Independent logical puzzle model

- Implement a discrete cubie/facelet model independent from MuJoCo physics; represent corner/edge permutations and orientations, fixed centers (relative to cube frame), and legal move notation `U D L R F B` with primes and `2` turns.
- Generate **reachable** cube scrambles from legal moves, not arbitrary random sticker permutations. Implement invariants, move inverse, four quarter-turn identity, parity/orientation checks, and canonical solved-state tests.
- After an *observed completed physical turn*, infer resulting discrete state from cubie poses; compare to independent logical expectation. Any disagreement is a failure, not silently resolved by snapping simulation state.

### 5.2 Candidate dynamic cubie mechanics

- Research physical cube mechanism (core, center attachments, corner/edge retainers and contact surfaces), representation fidelity and performance.
- Model all visible cubies and a credible retention/rotation mechanism. Explore mechanically meaningful contact constraints and selective connectivity changes; never assume constraint toggles alone enforce legal turns automatically.
- Constraint switches may occur at justified geometric alignments to restore valid assembly relationships. They must **not** rotate a layer, reset velocities to hide defects, relocate pieces, or enforce the goal state.
- Prohibit interpenetration, unintended non-target layer rotation, detached cubies, unsupported collision exemptions, and unreported numerical repairs in validated trials.
- Record per-step observed torque, layer angle, contact force, penetration, constraint transition events, energy/velocity anomalies and solver statistics when possible.

### 5.3 Geometric assumptions to research

Nominal cube size (often near 57 mm), individual layer width (~one-third nominal), mass, inertia, internal clearances, turn resistance, friction and target gripper force are **unverified starting assumptions** until measured/sourced. Keep all adjustable and test sensitivities; do not state universal values.

## 6. Robotic hardware abstraction

- Two xArm7 models in one collision-aware world with independent base frames, correctly composed names/actuators and observable transforms.
- Select compatible actual gripper model and mount from verified manufacturer/MuJoCo assets; **custom passive fingertips** may attach to jaws with well-defined tool-frame and inertial properties.
- Early tests: reachability, joint limits, workspace overlap, tool clearance, gripper opening/closing, stable cube grasp, one-face torque, forbidden-layer contact, collision and self-collision checks.
- Distinct arm roles initially: **Arm A classical stabilizer**, **Arm B RL-assisted turner**. Later both arms must be able to stabilize/turn or an approved different strategy must make handoff feasible.
- Conduct gripper design study under `docs/GRIPPER_DESIGN_RESEARCH.md`; geometry is deliberately unselected.

## 7. Software architecture and interfaces

Use modular packages (no code pre-created by this documentation package):

`cube_logic` ↔ `cube_physics` ↔ `robot_models` / `controllers` ↔ `planning` ↔ `skills_rl` ↔ `perception` ↔ `evaluation`.

**Minimal contracts (to specify and test before coding):**

| Interface | Inputs | Outputs / invariants |
| --- | --- | --- |
| `PuzzleState` | legal scramble / observed cubie transforms | immutable valid cubie state; `apply(move)`, `is_solved`, invariants |
| `CubePhysics` | robot-applied forces, simulation step | measured pose, face angle, contacts, constraint events; no high-level move setter in evaluation |
| `RobotState` | world frame + calibrated robot/tool frames | joint states, end-effector poses, contact wrench estimates |
| `MovePlanner` | legal puzzle state, target move, robot reachability | candidate grasp/turn/handoff action plan + feasibility cost |
| `LowLevelController` | nominal Cartesian target, bounded residual, limits | physically applied actuator commands, saturation and stop flags |
| `RLSkill` | training obs / task target | bounded residual command with deterministic evaluation option |
| `Perception` | RGB/depth images, camera calibration | estimated pose/facelets/confidence; missing/ambiguous state explicit |
| `Supervisor` | plan, beliefs, completion events, safety | execution state, verify/replan/stop decision |
| `Evaluator` | independent recorded episode outputs | metrics, validity checks, configs, seeds and diagnostics |

`docs/SYSTEM_ARCHITECTURE.md` expands on coordinate frames, privileged-state separation and failure pathways.

## 8. Control and learning

**Architecture:** discrete symbolic planner → task/motion planner → nominal Cartesian trajectories → residual RL (for selected skills) → impedance/force-aware controller → robot joint actuation / MuJoCo contacts → observation and task supervisor.

- Start one RL-assisted **90° face turn**, while the stabilizer uses classical control.
- Proposed policy action: small normalized Cartesian translation and orientation increments (6D) with configurable bounds. Optional bounded impedance parameters only after base controller stability is demonstrated. Do not mix frame conventions.
- Candidate measured observation: gripper/cube relative transforms, target/current layer angle, joint positions/velocities, gripper opening, estimated contact wrench, nominal trajectory error, relevant constraint mode. No direct target-state teleportation.
- Reward actual **measured** target-layer progress and verified completion; penalize slip, wrong-layer movement, excessive force, collision, time and numerical instability; no shortcut reward for issuing a move command.
- SAC as first candidate, PPO comparison. Algorithm and hyperparameters are research decisions, not promises of performance.
- Use curriculum (fixed pose → pose variation → friction/geometry variation → contact disturbances), bounded reset states, independent evaluation seeds, and classical/no-residual ablation. See `docs/RL_EXPERIMENT_SPEC.md`.

## 9. Planning, perception and recovery

### 9.1 Symbolic and manipulation planning

- Choose a vetted 3×3 cube solver (e.g., two-phase Kociemba). Verify cube-state encoding and solutions independently.
- Manipulation-aware cost is a stated investigation: cube move count, regrasp count, handoff count, estimated duration, joint travel, collision risk and estimated failure probability. Do not assert improvement without baseline.
- Generate executable motion/role plans with guards, feasibility and collision checks, joint and contact limits. Optional Pinocchio and OMPL are dependency-gated until needed.

### 9.2 Perception

- Early development: privileged MuJoCo state is allowed to isolate physics/controller bugs, but log exactly when used.
- Final: calibrated simulated cameras + OpenCV baseline for multiple-view facelet observation and pose. Require full puzzle-state reconstruction with ambiguity detection and independent consistency checks. Depth is optional, not assumed.
- Controller state may still use physical joint encoders as on a real robot; puzzle state/pose must come from the specified perception channel for camera-gated experiments.

### 9.3 Recovery

State machine with guarded transitions, e.g. `OBSERVE → PLAN → GRASP → STABILIZE → TURN → VERIFY → RELEASE/REGRASP → ... → SOLVED`, plus `RETRY`, `REPLAN`, and `SAFE_STOP`.

For detected slip, wrong-layer movement, missed 90° turn, unexpectedly high force, ambiguous camera state or failed transfer: cease unsafe action, observe anew, choose evidence-backed corrective action, or stop. No silent reset or correction during benchmark episodes.

## 10. Validation and experimental methodology

- **Phase-gated** progression in `docs/VALIDATION_PLAN.md`, with predefined quantitative metrics and thresholds determined from reference measurements and pilot results (not invented now).
- Independent logical cube tests; dynamics/constraint switch tests; tool/contact feasibility; classical manipulation baselines; RL held-out seeded trials; camera-derived state; integrated random legal scramble solves; full-benchmark ablations.
- For each benchmark report sample size, seed list, hardware, software version, simulation timestep, solver iterations, real-time factor, wall-clock runtime, success denominator, failure taxonomy and uncertainty intervals.
- Define fully successful *physical solve* as an unbroken episode starting from a reachable scramble, robot-actuated legal layer turns, independently verified solved state, no prohibited kinematic edits, and no unreported resets.
- Compare classical vs RL under identical cube states, initial poses, friction/disturbance distributions and execution budgets. Keep training and evaluation distributions distinct.

## 11. Technology and performance policy

**Initial:** Python 3.11+ (choose and lock a mutually compatible version during Phase 0), MuJoCo, MJCF, NumPy, SciPy, pytest, `uv`, Git, WSL2 Ubuntu.  
**On demand:** official xArm7/Menagerie assets, CAD Fusion 360/FreeCAD, Pinocchio, OMPL, PyTorch, Gymnasium, Stable-Baselines3, OpenCV, pandas, Matplotlib, TensorBoard, Ruff.  
**Deferred:** ROS 2/MoveIt 2, CasADi, GPU/CUDA training, humanoid models, real-world deployment.

Measure headless steps/second and simulated-seconds/wall-seconds; profile cube contacts, constraint transitions, two arms, grippers, RL inference and rendering independently. Record WSL2 graphics limitations. No assumption of 1× real time or fixed training duration without measurements.

## 12. Documentation deliverables and phase order

- `README.md` public status and roadmap.
- `CLAUDE.md` single-session execution instructions.
- `docs/RESEARCH_PLAN.md`, `docs/CUBE_MECHANICS_RESEARCH.md`, `docs/GRIPPER_DESIGN_RESEARCH.md` — mandated literature and design reviews.
- `docs/SYSTEM_ARCHITECTURE.md`, `docs/RL_EXPERIMENT_SPEC.md`, `docs/VALIDATION_PLAN.md` — implementation contracts and tests.
- `docs/REFERENCES_SEED.md` — source leads, not completion evidence.
- `docs/DECISION_LOG.md` — frozen decisions, approvals and open risks.
- `phases/PHASE_0_RESEARCH.md` through `phases/PHASE_7_EVALUATION.md` — objective, tasks, gate and deliverable of each phase.

The sequence is **0 research → 1 cube physics → 2 robot/gripper → 3 RL → 4 bimanual autonomy → 5 vision/recovery → 6 full solve → 7 evaluation**. Independent work may proceed in parallel, but no result may bypass its acceptance gate. Detailed mechanical CAD and RL training explicitly require prior phase approval.

## 13. Evidence, provenance and change control

Research findings belong in dated `docs/research/` reports created *after* literature review; benchmark results belong in versioned `experiments/` records created after running tests. Do **not** create synthetic results as a substitute. Cite exact DOI/URL/asset license, record used versions and preserve third-party copyright notices. Approve changes to locked decisions before editing this specification; note them in `docs/DECISION_LOG.md`.

## 14. Definition of done — v1

Rubiknetic v1 is done **only if** it has: (a) documented mechanically credible legal cube dynamics; (b) demonstrably contact-driven turns using two xArm7 manipulators; (c) a tested residual RL component with an honest classical comparison; (d) autonomous arm coordination, handoffs and multi-face planning; (e) camera-derived puzzle state and verification; (f) complete valid scrambled-cube solves and independently reproducible benchmarks; and (g) transparent limitations and release instructions.

**This document defines intended acceptance criteria. As of 2026-11-12, none of the implementation results are claimed complete.**
