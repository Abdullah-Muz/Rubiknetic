# Phase 4 — Bimanual Task & Motion Planning

**Status:** NOT STARTED  
**Gate:** G4 in `../docs/VALIDATION_PLAN.md`  
**Prerequisites:** G2 physical manipulation passed; G3 RL experiment evaluated (RL can be neutral or negative; hierarchy may choose classical skill where better).

## Objective

Convert legal symbolic cube moves into physically executable grasps, stabilizations, face turns, releases, reorientations, handoffs and role swaps. Preserve puzzle state across multiple different axes without privileged state repair.

## Tasks

1. Integrate vetted Kociemba two-phase solver and independent logical cube model; test move notation and cube orientation transforms.
2. Define task-level skills and preconditions/postconditions: `approach`, `grasp`, `hold`, `turn_layer`, `verify_turn`, `release`, `handoff`, `reorient`, `safe_stop`.
3. Develop manipulation-aware plan graph with valid wrist reachability, grip clearance, collision and arm-role constraints.
4. Implement collision-aware motion planning (consider OMPL or a simpler verified planner based on measured need).
5. Implement bimanual handoff with both arms supporting cube appropriately; avoid a brief unsupported drop unless deliberately tested.
6. Include limited retry/replan behavior on failed or incomplete turn, rather than silently resetting physics.
7. Compare naive solver move execution vs manipulation-cost-aware feasible planning when both are well-defined.

## Deliverables

Symbolic-to-physical plan trace, action state machine, regrasp/handoff control, collision-safe motion planner, independent state checker, multi-move robot videos and machine-readable traces.

## Exit criteria

Multiple varied face turns and role transitions occur autonomously by physically plausible contacts; independent oracle agrees with physical state; no direct state update and no hidden reorientation. Move-optimality claims require comparative evidence.
