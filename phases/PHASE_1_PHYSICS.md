# Phase 1 — Dynamic Cube Physics & Logical Correctness

**Status:** NOT STARTED  
**Gate:** G1 in `../docs/VALIDATION_PLAN.md`  
**Prerequisite:** G0 approved mechanical representation, documented known simplifications and test protocol.

## Objective

Develop a 3×3 cube simulation with **physically driven** legal layer rotation, dynamic cubie connectivity and an independent symbolic puzzle-state oracle. First test the mechanism **without complex robot arms** so mechanism failures remain diagnosable.

## Implementation tasks

1. Implement standalone legal Rubik's Cube representation with corner/edge identity, orientation, parity checks, valid scramble generator and inverse/identity tests.
2. Construct selected minimal MJCF cube prototype with explicit cubie identifiers, mass/inertia estimates, contact meshes and core/retention abstractions.
3. Implement finite-state constraint transitions driven by measured pose/angle/velocity/contact conditions, not a command to rotate face or solve puzzle.
4. Create a physical test actuator (fixture, contact pad/probe) applying contact forces to the rotating layer; do **not** directly set layer angle or manipulate cubie poses during scored trials.
5. Log constraint activations, impulses, velocity continuity, relative angle, torque, penetration, collision and illegal state events.
6. Demonstrate clockwise/counterclockwise quarter-turn, half turn, inversion and consecutive cross-axis moves.
7. Test timestep, solver, friction, initial alignment and geometry sensitivity; measure headless CPU throughput.

## Tests and negative controls

- Puzzle oracle: `M M' = identity`; `M^4 = identity`; verify independent legal scramble generator.
- Physics agrees with expected moves inferred from **observed** cube states.
- Artificial commands without applied contact cause no turn or success reward.
- Turn without valid physical alignment cannot spuriously relink cubies.
- Force unintended adjacent-layer motion and show the validator rejects it.
- Force constraint switch under wrong geometry and verify it fails safely rather than snapping into place.
- Repeat `R U R' U'` to expose topology/axis errors.

## Deliverables

Prototype MJCF + documented modeling abstraction, independent logical cube model, falsifiable constraint state machine, benchmark commands, trace logs and Phase 1 technical memo. Preserve failed attempts and parameters.

## Exit criteria

All hard invariants and registered numerical tolerances in G1 pass on repeatable trials. User approval required to integrate robot arms. A preanimated or programmatically driven face turn **does not pass**.
