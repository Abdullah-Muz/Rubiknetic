# Rubiknetic — Proposed System Architecture

**Status:** Interface design, not implemented. Source of truth: `../RUBIKNETIC_MASTER_SPEC.md`.

## Architecture overview

```text
             ┌──────────────────────────┐
 RGB cameras │  Perception & estimation │─────┐
     ───────▶│  cube facelets / pose    │     │
             └──────────────────────────┘     ▼
                                       ┌───────────────┐
 Independent logical cube oracle ◀────▶│ Symbolic cube │
                                       │ solver        │
                                       └───────┬───────┘
                                               ▼
                                       ┌───────────────┐
                                       │ TAMP planner  │
                                       │ grasp/regrasp │
                                       │ role & path   │
                                       └───────┬───────┘
                                               ▼
                                       ┌───────────────┐
                                       │ Task          │
                                       │ supervisor    │◀────── verify / recover
                                       └───────┬───────┘
                                          ┌────┴────┐
                                          ▼         ▼
                                     ┌────────┐ ┌─────────────┐
                                     │ Arm A  │ │ Arm B       │
                                     │ nominal│ │ nominal +   │
                                     │ control│ │ residual RL │
                                     └────┬───┘ └────┬────────┘
                                          └────┬─────┘
                                               ▼
                                   ┌────────────────────────┐
                                   │ MuJoCo: two xArm7 +    │
                                   │ grippers + dynamic     │
                                   │ cubie constraints      │
                                   └───────────┬────────────┘
                                               ▼
                                     measured contacts,
                                     poses, joint state
```

The **logical cube oracle** and independent physical verifier may inspect simulator truth during validation; final runtime decision-making must not have access to privileged cube-state variables except explicit training/diagnostic mode.

## Coordinate frames

Define and test transformations among:

- `world`: MuJoCo table, environment, camera extrinsics.
- `arm_a_base`, `arm_b_base`: two xArm7 base poses.
- `arm_a_tool`, `arm_b_tool`: fitted custom fingertip grasp/contact frame.
- `cube_body`: chosen stable object reference, not automatically one face's moving coordinates.
- `face_F`, `face_U`, etc.: logical face references attached to cube orientation, not arbitrary world axes.
- `target_layer_axis`: physical axis and sign corresponding to one requested move.
- `camera_i`: optical frame, calibrated to world.

Declare transform direction and representation (e.g., `T_world_from_tool`), quaternion convention, right-hand angle sign and reference layer. Write frame-consistency tests before motion planning.

## Component ownership

| Component | Responsibilities | Forbidden shortcut |
| --- | --- | --- |
| `cube_logic` | Legal reachable states, scramble generator, moves, validity | Copy simulator's intended state blindly |
| `cube_physics` | Geometry, contacts, constraint activation, dynamics logs | Direct face angle assignment on eval |
| `robot_models` | Unique model names, base/tool frames, actuator and gripper limits | Suppressed collision for convenience without evidence |
| `controllers` | IK, Cartesian target tracking, impedance, limits | Infinitely strong friction, nonphysical actuation |
| `skills_rl` | Bounded residual commands in selected skill contexts | Hidden solve sequence, noncausal data |
| `planning` | Cube moves, reachability, collision-free grasps and TAMP | Assuming every cube move is mechanically executable |
| `perception` | Calibrated cube pose, sticker observation, uncertainty | Reading `qpos` for final camera-only cube-state inference |
| `supervisor` | Mode transitions, operation verification, retry/replan/stop | Silently resetting failures |
| `evaluation` | Independent checks, metrics, replay, reports | Reporting visually plausible moves as successful physical turns |

## Three data channels

1. **Runtime observation:** robot joints and tool pose sensors; perception outputs; allowed wrench estimates; previous action outcome. The final vision mode cannot receive simulator cubie truth through this channel.
2. **Training privileged channel:** optionally precise cube poses/contact metadata for efficient state-based curriculum, *tagged and never mixed with the final camera-only evaluation result*.
3. **Evaluation audit channel:** simulator ground truth, collision/contact traces and independent combinatorial oracle used only for scoring, not for choosing actions.

## Core execution state machine

`INIT → OBSERVE → VALIDATE_CUBE_STATE → SOLVE_SYMBOLICALLY → PLAN_MANIPULATION → GRASP → STABILIZE → TURN → VERIFY → RELEASE/REGRASP → (next move / SOLVED)`.

Fault transitions to `RETRY`, `REOBSERVE`, `REPLAN`, or `SAFE_STOP` must have bounded attempts and logged rationale. Do not auto-correct physical state during recovery. A cube state can become `UNKNOWN` after an incomplete turn; recover from observation or stop without guesswork.

## Deployment boundaries

- **Phase 1:** simulator and independent oracle, no arms required for every test.
- **Phase 2:** bimanual physical control, privileged cube-state for debug.
- **Phase 3:** residual policy for one turn; other arm classical.
- **Phase 4:** multi-step TAMP and handoffs; handoff policies may remain classical initially.
- **Phase 5:** perception-derived state and failure recovery.
- **Phase 6:** full closed-loop solves without action-state overwrite.

## Reproducibility contract

Every run stores: software and source revision, platform versions, MuJoCo model and asset revisions, random seeds, cube scramble, controller mode, train/test flag, physics timestep and solver settings, contact parameters, camera calibration, action logs, constraint switches, score and failure reason. Keep lightweight logs first and raw video opt-in for CPU usage.
