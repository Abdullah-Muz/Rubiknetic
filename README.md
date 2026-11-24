<div align="center">

# Rubiknetic

[![CI](https://github.com/Abdullah-Muz/Rubiknetic/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Abdullah-Muz/Rubiknetic/actions/workflows/ci.yml)

### Learning-Enabled Bimanual Robotic Manipulation for Physically Solving a Rubik's Cube

**Research and architecture stage · No validated physical solves claimed**

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

## Proposed system

| Layer | Initial approach |
| --- | --- |
| Physics engine | MuJoCo / MJCF, CPU-first headless operation |
| Arms | 2 × UFACTORY xArm7 (14 arm joints total) |
| End effectors | Parallel-jaw grippers with passive custom fingertips; final geometry research-gated |
| Cube | 3×3 cubie model with dynamically changing, mechanically motivated constraints |
| Low-level control | Cartesian target tracking with impedance/force-aware safeguards |
| Learning | Hierarchical task execution + bounded residual RL (SAC candidate; PPO comparison) |
| Coordination | Initially one classical stabilizer and one RL-assisted turning arm; later handoffs and role switching |
| Planning | Independent symbolic cube state, two-phase solver, task/motion planning |
| Perception | Simulator state for early debugging; final RGB camera-based observation and verification |
| Evaluation | Classical-vs-RL comparisons, randomized legal scrambles, held-out seeds and disturbances |

## Development phases

| Phase | Purpose | Exit artifact |
| --- | --- | --- |
| **0 — Research** | Literature, cube mechanism and fingertip feasibility | Verified reports, comparative design decision, documented open risks |
| **1 — Cube physics** | Dynamically constrained cubie simulation | Verified one-turn and cross-axis consecutive turns driven by external physical torque |
| **2 — Robot integration** | Two xArm7s, grippers, classical controllers | Contact-driven face turn with one arm stabilizing and the other turning |
| **3 — Reinforcement learning** | Residual Cartesian RL for manipulation | Reproducible learned-vs-classical benchmark; negative results accepted |
| **4 — Bimanual autonomy** | Task/motion planning, regrasp and handoff | Legal, coordinated multi-turn sequences and state continuity |
| **5 — Perception and recovery** | Cameras, cube-state estimation, feedback | Vision-derived pose/state and independently tested error detection |
| **6 — Complete solving** | Integrated cube solver and physical actions | Documented complete solves on valid unseen scrambles |
| **7 — Evaluation and release** | Robustness studies, ablations, reproducibility | Technical report, benchmarks, failures, runnable documented release |

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

## Current status

**Documentation ready for Phase 0.** No literature review has been completed within this repository package, and no mechanical mechanism, training result, or autonomous cube solve is claimed. The biggest unknowns are the physically meaningful cubie constraint system, end-effector access to individual layers, and realistic simulation stability/performance on CPU-only hardware.

## License

Licensed under the [Apache License, Version 2.0](LICENSE). Third-party material keeps its own licence and attribution; see [NOTICE](NOTICE) (for example, the OpenAI robogym cube files under `experiments/D9_openai_baseline/robogym/` are MIT-licensed). Third-party CAD used during development is not included in this repository.

## Credits and naming

An independent educational/research project, not affiliated with or endorsed by the owners of the Rubik's Cube brand, UFACTORY, or Google DeepMind. “Rubik's Cube” is used descriptively. Original work and third-party assets must retain their respective licenses and attribution.
