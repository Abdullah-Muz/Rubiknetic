# Phase 0 — Research & Engineering Foundations

**Status:** NOT STARTED  
**Gate:** G0 in `../docs/VALIDATION_PLAN.md`  
**Purpose:** Understand feasibility, not merely collect citations. No detailed fingertip CAD, cube mechanism implementation or RL training authorized in this phase.

## Entry conditions

- Master specification, selected platform, study questions and research integrity rules reviewed.
- Approved scope: 2× xArm7, MuJoCo, custom fingertip research, changing cubie constraints, physically driven turns, E+C+D residual RL, CPU-only.

## Work packages

**A. Cube mechanics and simulator research**

- Review 3×3 cube internal mechanics, corner/edge/center retention and layer transitions.
- Review runtime equality activation (`mjData.eq_active`), solver contact parameters and loop-constraint behavior; calculate candidate constraint graph size and possible impulse artifacts.
- Compare predefined switched equalities, core/cubie assembly and mechanical surrogate models without hiding the simplifications.
- Outline minimal falsifiable one-turn plus nonparallel consecutive-turn experiments and independent logical oracle.

**B. Gripper and fingertip research**

- Review xArm7 model, real gripper variants and CAD/mount/license details.
- Review 15–20 credible sources across combined study; examine at least six fingertip concepts and develop a deep comparison of two or three.
- Analyze grip force, torsional resistance, wrong-layer interference, reach, tool geometry, handoff and pose uncertainty with sourced assumptions.

**C. Control / RL / perception research**

- Establish classical Cartesian/impedance controller reference with realistic limits.
- Review bounded residual RL and compare SAC vs PPO without claiming one will work.
- Draft CPU-throughput and camera-viewability feasibility test plans.

## Deliverables

- `research/PHASE_0_SOURCE_REGISTER.md`
- `research/CUBE_MECHANICS_FINDINGS.md`
- `research/GRIPPER_FINDINGS.md`
- `research/CONTACT_AND_RL_FINDINGS.md`
- `research/PHASE_0_DECISION_MATRIX.md`
- User-facing recommendation: 2–3 alternative concepts, quantified constraints, uncertainty, smallest viable test, and explicit approval request.

These reports do **not** exist yet. Produce them only from verified research.

## Exit criteria

- Citation metadata and access status verified; no hallucinated experiments.
- Physical validity risks and design assumptions documented.
- Competing gripper/cube concepts ranked on stated criteria.
- Clear pilot test and evidence expectations agreed.
- User explicitly approves concept directions and records decision in log.

**If results show infeasibility:** mark G0 `BLOCKED`, propose evidence-based scope alternatives and obtain approval; do not work around physics with hidden state updates.

**Parallel opportunities:** Independent logical cube solver and test-oracle specification can be drafted without committing to mechanics, but no Phase 1 completion may be claimed.
