# Phase 2 — xArm7, Grippers & Classical Manipulation

**Status:** NOT STARTED  
**Gate:** G2 in `../docs/VALIDATION_PLAN.md`  
**Prerequisites:** G1 physics gate passed; gripper mechanism approved from Phase 0 research.

## Objective

Demonstrate a legal **contact-driven** cube-face rotation by one arm while a second arm stabilizes the rest of the cube, using classical controllers **without RL**. Validate selected custom fingertip geometry with repeatable tests.

## Tasks

1. Import two distinct xArm7 MJCF instances, verify actuator names, original kinematics, joint limits, mass and transforms; confirm asset licenses.
2. Load compatible parallel-jaw gripper models. Attach research-approved custom passive fingertip geometry; model tool frames, inertias, jaw limits and clearance.
3. Establish base frame separation, overlap workspace and collision-aware grasp approach configurations.
4. Implement joint control and basic Cartesian motion tracking; add stable impedance/force-aware contact control, actuator saturation and limits.
5. Verify stable cube stabilization through externally driven contact torque before performing a face turn with another arm.
6. Implement physically controlled arm B target-layer engagement, 90° and 180° turns, release and stable stop.
7. Benchmark narrow/stepped/other approved fingertip candidates under matched pose/force/friction conditions. Record actual contact forces, wrong-layer movement and slips.
8. Profile headless simulation with two robot arms, cube constraints and dynamic contacts on CPU.

## Required negative tests

- Tool touches two layers by mistake: reject face turn.
- Deliberate off-center grasp: test torque/slip and safe-stop.
- Robot collides with table or the other arm: reject execution.
- Gripper opens mid-turn: monitor slippage and discontinuity.
- Contact solver divergence or constraint relink impulse: reject the claimed pass.

## Deliverables

Versioned robot world and gripper assets, coordinate-frame tests, controllers, classical baseline trajectories, simulation throughput report, contact verification logs and gripper-design selection evidence.

## Exit criteria

Repeatable physical face turns at registered tolerances with two xArm7s, no invisible face actuation, no illegal cubie motion, reasonable collision/force characteristics, and explicitly approved gripper mechanism. Only then start contact-rich RL training.
