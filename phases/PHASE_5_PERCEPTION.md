# Phase 5 — Vision, State Estimation & Recovery

**Status:** NOT STARTED  
**Gate:** G5 in `../docs/VALIDATION_PLAN.md`  
**Prerequisites:** G4 multi-move autonomy and documented camera/robot coordinate conventions.

## Objective

Replace privileged cube-state inputs in the **deployed decision-making pathway** with calibrated simulated-camera estimates. Detect failed manipulation and recover or safe-stop with transparent reasoning.

## Tasks

1. Choose simulated RGB camera arrangement, lighting/background variation and extrinsic calibration; test WSL2 headless rendering feasibility.
2. Implement OpenCV face detection, sticker segmentation/color classification, cube pose inference and multiple-view reconstruction to observe all relevant faces.
3. Validate color-consistent legal cube state with an independent oracle; represent ambiguous/unknown stickers, orientation confusion and insufficient views explicitly.
4. Integrate camera-derived state into plan selection and post-turn verification while keeping simulator cube truth in **audit-only** channels.
5. Inject slips, underrotation, overrotation, incorrect grasp, occlusion and partial ambiguity; implement bounded `REOBSERVE`, `REPLAN`, `RETRY`, `SAFE_STOP` transitions.
6. Evaluate vision estimates under held-out initial poses, lighting, cube rotations and temporary occlusions. Record confidence and false corrective actions.

## Deliverables

Camera model/config and calibration tests, vision pipeline, legal-state reconstruction, error detection/recovery tests, privileged-state access audit and video examples with synchronized logs.

## Exit criteria

Robot actions and cube-solving decisions use vision-derived puzzle-state information; known failure modes are either detected and corrected physically or lead to safe stop. No simulator truth leakage to final perception-mode planner.
