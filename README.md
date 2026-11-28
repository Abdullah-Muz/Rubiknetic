<div align="center">

# Rubiknetic

[![CI](https://github.com/Abdullah-Muz/Rubiknetic/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Abdullah-Muz/Rubiknetic/actions/workflows/ci.yml)

### Learning-Enabled Bimanual Robotic Manipulation for Physically Solving a Rubik's Cube

**Simulation research in progress · G1 cube physics passed · G2 two-arm contact turning passed (simulation) · No cube solve claimed**

<img src="docs/media/g2_two_arm_u_turn.gif" alt="Two simulated xArm7 arms: arm A holds the cube's lower layers, arm B grips the top layer and turns it a quarter turn by contact" width="480">

<sub>MuJoCo simulation, 2× speed: arm A holds the free-core cube, arm B turns the U layer by fingertip contact (magnets
on, pilot seed 29001). Close-up: <a href="docs/media/g2_u_turn_closeup.gif">g2_u_turn_closeup.gif</a>.</sub>

</div>

## Overview

**Rubiknetic** is an independent, simulation-first robotics project studying how two robotic manipulators can cooperatively perceive, grasp, reorient, and **physically turn** a 3×3 Rubik's Cube. The puzzle is a demanding test case for contact-rich manipulation, hierarchical autonomy, and long-horizon task-and-motion planning—not merely a software cube solver or a preanimated demonstration.

The proposed platform uses **two UFACTORY xArm7 seven-axis manipulators**, parallel-jaw grippers with **research-informed custom fingertips**, and **MuJoCo** physics. A mathematical cube solver determines legal moves; a manipulation planner chooses feasible arm roles, grasps, transfers, and trajectories. **Residual reinforcement learning** improves selected contact-intensive skills on top of classical Cartesian and impedance-aware control.

The final system aims to infer cube state from **simulated cameras**, execute its solution by simulated **contact forces**, verify each result, and recover from selected failures. All capabilities are *targets*, not results, until tested and documented.

## Research questions

1. Can a dynamically constrained cubie model support successive, mechanically valid, contact-driven rotations across different cube axes without scripted pose updates?
2. Which custom fingertip geometries let two parallel grippers stabilize separate portions of the cube, rotate one layer, and perform handoffs?
3. Does bounded residual RL improve contact-rich face turning compared with a matched classical-controller baseline?
4. How do grasp choice, reorientation, and handoff cost affect the best physically executable cube-solving sequence?
5. Can camera-derived state and closed-loop monitoring support repeatable complete solves across unseen valid scrambles?

## System (built so far, and planned)

| Layer | Approach |
| --- | --- |
| Physics engine | MuJoCo 4 / MJCF, CPU-first headless operation (WSL2 Ubuntu) |
| Arms | 2 × UFACTORY xArm7, revision 1305+ (MuJoCo Menagerie model + UFACTORY xarm_ros2 limits and meshes) |
| End effectors | UFACTORY Gripper G2 with passive custom fingertips: a 30 × 30 mm flat stabiliser pad and a 25 × 14 mm flat turner pad (C1); a shouldered turner (C2) is the contingency |
| Cube | **M7**: 26 cubies on fixed-radius ball joints with 48 modelled N35 magnets, 2.5 mm rounded piece edges, 0.05 mm clearance; layers turn only through contact forces (no switched constraints, no hidden actuator) |
| Low-level control | Cartesian target tracking with impedance/force-aware safeguards |
| Learning | Hierarchical task execution + bounded residual RL (SAC candidate; PPO comparison) |
| Coordination | Initially one classical stabilizer and one RL-assisted turning arm; later handoffs and role switching |
| Planning | Independent symbolic cube state, two-phase solver, task/motion planning |
| Perception | Simulator state for early debugging; final RGB camera-based observation and verification |
| Evaluation | Classical-vs-RL comparisons, randomized legal scrambles, held-out seeds and disturbances |

## Development phases

| Phase | Purpose | Exit artifact | Status |
| --- | --- | --- | --- |
| **0 — Research** | Literature, cube mechanism and fingertip feasibility | Verified reports, comparative design decision, documented open risks | Conditional pass (2026-11-12) |
| **1 — Cube physics** | Mechanically credible cubie simulation | Verified one-turn and cross-axis consecutive turns driven by external physical torque | **Passed for M7** (2026-11-26), with stated limitations |
| **2 — Robot integration** | Two xArm7s, grippers, classical controllers | Contact-driven face turn with one arm stabilizing and the other turning | **Passed for M7** (2026-11-28): 128/128 scored trials, with stated limitations |
| **3 — Reinforcement learning** | Residual Cartesian RL for manipulation | Reproducible learned-vs-classical benchmark; negative results accepted | Not started |
| **4 — Bimanual autonomy** | Task/motion planning, regrasp and handoff | Legal, coordinated multi-turn sequences and state continuity | Not started |
| **5 — Perception and recovery** | Cameras, cube-state estimation, feedback | Vision-derived pose/state and independently tested error detection | Not started |
| **6 — Complete solving** | Integrated cube solver and physical actions | Documented complete solves on valid unseen scrambles | Not started |
| **7 — Evaluation and release** | Robustness studies, ablations, reproducibility | Technical report, benchmarks, failures, runnable documented release | Not started |

> Phase completion is evidence-based. A smooth video alone does not prove physical validity or autonomy. The phases may contain independent parallel tasks but cannot bypass prerequisites.

## Technology candidates

**Initially:** Python, MuJoCo, MJCF, MuJoCo Menagerie, NumPy, SciPy, pytest, Git, `uv`, Ubuntu / WSL2.

**Added when justified:** CAD (Fusion 360 or FreeCAD), PyTorch, Gymnasium, Stable-Baselines3, TensorBoard, OpenCV, Pinocchio, OMPL, pandas, Matplotlib, Ruff. ROS 2, MoveIt 2, CasADi, GPU-centric tooling and multi-agent RL are **not required** for v1.

## What counts as a physical cube solve?

A valid solve requires robot-actuated grippers to generate the contact forces/torques responsible for face rotations; independently checked cube-state legality; no commanded teleportation, direct rotation setting, or solver-to-physics state overwrite during execution; and accurate documentation of any mechanical abstractions such as reconfigured constraints. Camera-derived state is required for the final vision milestone, while privileged simulator state is allowed only for early baselines, training or independent verification as specified.

## Documentation

- [Master engineering specification](RUBIKNETIC_MASTER_SPEC.md) — authoritative scope, invariants, interfaces and approval gates.
- [Claude Code operating instructions](CLAUDE.md) — single-session, research-first workflow.
- [Research plan](docs/RESEARCH_PLAN.md) and [seed references](docs/REFERENCES_SEED.md).
- [Cube mechanics research brief](docs/CUBE_MECHANICS_RESEARCH.md).
- [Gripper and fingertip research brief](docs/GRIPPER_DESIGN_RESEARCH.md).
- [System architecture](docs/SYSTEM_ARCHITECTURE.md).
- [RL experiment specification](docs/RL_EXPERIMENT_SPEC.md).
- [Validation and acceptance plan](docs/VALIDATION_PLAN.md).
- [Decision log](docs/DECISION_LOG.md).
- [Phase-by-phase plans](phases/PHASE_0_RESEARCH.md).

## Current status (2026-11-28)

Everything below is **simulation only**. Nothing here establishes sim-to-real transfer.

**Phase 1 — cube physics: passed for mechanism M7** ([G1 report](experiments/E7_scored_m7/G1_REPORT_M7.md)).
- A pre-registered, independently reviewed battery of **204/204 scored trials** passed with zero tolerance
  ([pre-registration](experiments/PHASE_1_M7_PREREGISTRATION.md), [results](experiments/E7_scored_m7/RESULTS.md)).
- It covers quarter, half and reverse turns, cross-axis sequences, 60 s rests, negative controls and a sensitivity
  screen.
- Every turn is checked against an independent logical cube-state oracle; any direct state edit is audited and fails
  the trial.
- The report lists 12 limitations. Among them: assumed clearance, uncalibrated turning torque, a solver setting
  (NoSlip) chosen after rehearsals, and a test-rig grip that never exceeded about 11.5 N.

**Phase 2 — two-arm turning: passed for M7** ([G2 report](experiments/E8_scored_g2/G2_REPORT.md)).
- **Two full xArm7 arms** facing each other (bases 1.0 m apart): arm A holds the free-floating cube's lower two layers,
  arm B grips the top layer and turns it with its wrist. Only fingertip contact turns the layer; the controllers never
  read the cube's state.
- A pre-registered, seven-times independently reviewed battery of **128/128 scored trials** passed with zero tolerance
  ([pre-registration](experiments/PHASE_2_G2_PREREGISTRATION.md), [verdict](experiments/E8_scored_g2/VERDICT.md)):
  - 100 turn trials (U, U′, U2, 5-move and 10-move random sequences), 360 moves: turn error ≤ 0.41°, other layers
    ≤ 0.31°; 95 % upper bound on the per-trial failure rate 3 %;
  - 20 one-minute holds: the cube moves ≤ 0.16 mm;
  - negative cases detected: blocked turns are stopped by a wrist force/torque guard, and wrong grips, collisions and
    a gripper opening mid-turn are caught.
- **A bug found by review:** the cube's magnets had been switched off in every earlier two-arm run. They were restored,
  every trial now proves they acted at every step, and all pilots were repeated before the scored run.
- Limitations include: simulation only; U-family turns from one grasp (no regrasps, no other faces yet); modelled
  friction, turning torque and force sensor.
- **Stickers:** the cube carries coloured stickers in the viewer. They are visual only (no mass, no collision), and the
  physics is bit-identical with and without them.

**Watch it** (WSL with a display, e.g. WSLg on Windows 11):
```bash
~/.venvs/rubiknetic/bin/python experiments/D18_two_arm_m7/two_arm.py --view
```

**Not yet done:** reinforcement learning (Phase 3), regrasps and other faces (Phase 4), camera perception (Phase 5)
and complete solves (Phase 6). No autonomous cube solve is claimed.

## License

Licensed under the [Apache License, Version 2.0](LICENSE). Third-party material keeps its own licence and attribution; see [NOTICE](NOTICE) (for example, the OpenAI robogym cube files under `experiments/D9_openai_baseline/robogym/` are MIT-licensed). Third-party CAD used during development is not included in this repository.

## Credits and naming

An independent educational/research project, not affiliated with or endorsed by the owners of the Rubik's Cube brand, UFACTORY, or Google DeepMind. “Rubik's Cube” is used descriptively. Original work and third-party assets must retain their respective licenses and attribution.
