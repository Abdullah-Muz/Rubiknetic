# Phase 6 — End-to-End Autonomous Cube Solving

**Status:** NOT STARTED  
**Gate:** G6 in `../docs/VALIDATION_PLAN.md`  
**Prerequisites:** G1–G5 gates passed at their respective scopes.

## Objective

Demonstrate complete bimanual Rubik's Cube solving from valid unseen scrambles, with camera-derived state, symbolic planning, verified robot-contact execution and active failure detection. No hidden manual interventions or resets within scored runs.

## Tasks

1. Generate legal scrambles using independent puzzle oracle; freeze scramble seed lists and distribution before scored evaluation.
2. Integrate vision observation of all required cube faces, frame transforms, solver, manipulation plan, classical and RL-assisted controllers and task supervisor.
3. Execute complete sequences with physical turns, regrasp, arm-role swap and verification after relevant steps.
4. Ensure failure cases stop safely or replan from *observed* state; never overwrite the cube to match symbolic expectation.
5. Record at least one uninterrupted, independently verified nontrivial full solve; expand to pre-registered held-out cases.
6. Target eventual 100 randomized valid test scrambles **if CPU/runtime feasibility permits**; report actual trial count and failures, not an assumed achievement.

## Deliverables

End-to-end reproducible simulation commands, full episode logs, independent scramble and solved-state proof, failure taxonomy, demo footage and compute budget report.

## Exit criteria

At least one legitimate complete solve with independently verified state and no prohibited physical shortcuts; substantive held-out evaluation (sample size declared, not improvised) with transparent denominator and limits. A hardcoded trajectory for a single known scramble is insufficient.
