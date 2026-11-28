# Phase 3 readiness check (2026-11-28; documents only)

**What this is:** an issue list comparing the Phase 3 plan (`phases/PHASE_3_REINFORCEMENT_LEARNING.md`), the RL
specification (`docs/RL_EXPERIMENT_SPEC.md`) and the earlier findings (`CONTACT_AND_RL_FINDINGS.md`, P-64) against what
G1 and G2 have since established. The user asked for it while G2 is in review. It starts nothing in Phase 3, changes no
specification, and every `PROPOSAL` needs the user's approval. G3 cannot start before G2 is signed off.

**Labels:** `FACT` (from a committed record or measurement), `INFERENCE`, `PROPOSAL`, `DECISION` (for the user).

## Summary
1. **Simulation speed is about 4× worse than the earlier estimate**, and the cause is different: NoSlip, not the magnets
   (issue 1). At the planned 20 Hz control rate, one process gives about 1.6 control steps per second. That makes the
   simulator, not the learner, the limit on everything in Phase 3.
2. **The G2 baseline is a torque-level impedance controller that the real xArm cannot run** (issue 2). Whether G3's
   baseline keeps it or moves to the hardware's admittance structure is the user's decision (P-64 proposal).
3. **Under G2's start distribution the classical controller has almost nothing left to fix** (issue 5): pilot 4 passed
   144/144. A residual-RL comparison needs a harder, pre-registered task distribution on which the baseline fails
   measurably.
4. **The magnet force is a process-global MuJoCo callback** (issue 4). This caused the P-130 bug, and it rules out
   several environments in one process.

## Issues
### 1. Throughput (`FACT`: D19, pilot 4; `INFERENCE`: budget)
- **Measured:**
  - two-arm M7 scene, one process, quiet: about 159 control steps/s with magnets, controllers and monitoring (0.08×
    real time);
  - under 8 workers in pilot 4: a median of 0.043× real time;
  - bare `mj_step` without magnets: about 200–245 steps/s;
  - with NoSlip off: 1,052 steps/s.
- **The earlier estimate is outdated.** `CONTACT_AND_RL_FINDINGS` §5 assumed 606 steps/s (an M6 cube-only scene) and
  named the magnet callback as the main cost. In the two-arm M7 scene, **NoSlip is about 80 % of the step** and the
  magnets about 16–20 % (D19).
- **Budget at 20 Hz** (100 physics steps per control step): about 1.6 control steps/s per process. 100,000 control
  steps would take about 17 h on one process; 1 million about 7 days. Multi-process scaling is still unmeasured (Q5).
- `PROPOSAL`: before any G3 design, measure parallel scaling on a quiet machine (D19 part 2, pending) and fix a compute
  cap from it (RL spec §9 asks for this).
- `DECISION` (later): a cheaper **training** model (NoSlip off, about 5×), validated against full M7 by a pre-registered
  comparison, with every final evaluation on full M7. It changes the physics that G1 validated, so it must not be used
  for any reported result.

### 2. Classical baseline structure (the pending P-64 decision)
- `FACT`: the real xArm takes only position or velocity setpoints, up to 250 Hz (C01–C03). The G2 controller drives arm B
  with joint torques: a Cartesian impedance, and a torque-controlled J7 with feedforward.
- The RL spec says B0 is "the same controller without residuals". So B0 is whatever G2 validated, unless the user
  decides otherwise.
- **Options:**

| | A: keep G2's torque-level impedance as B0 | B: build B0 with the hardware's structure (position servo + outer admittance loop at ≤ 250 Hz, 1–3 samples of delay) |
|---|---|---|
| Cost now | none: B0 is G2's validated controller | a new controller, tuning, and its own classical validation (a G2-style pilot) before any RL |
| Validity | sound in simulation; recorded as an abstraction the real arm cannot run | closer to what a real xArm could execute; supports any later sim-to-real claim |
| Risk | the RL result may not transfer to hardware at all | admittance on a stiff (jammed) cube can chatter (C06); a delay makes it harder |
| Residual placement | on the impedance setpoint (correct per L04) | on the admittance setpoint (also correct) |
| Fits the project's scope | yes: the spec claims simulation only | yes, and keeps a hardware path open |

- `INFERENCE`: if Phase 3 is meant to stay simulation-only (as the master specification states), A is cheaper and
  scientifically fine, provided the abstraction is disclosed. B is the better choice if a hardware follow-up is a real
  goal.

### 3. The action space and the roll
- The spec's action is a bounded 6D Cartesian residual. In G2 the turn itself is J7's roll, driven by its own torque law
  with a nominal ramp, while the impedance holds the gripper-base pose.
- `PROPOSAL`: define the residual as (a) a 3D position and 2D axis-direction correction to the impedance setpoint, plus
  (b) a bounded correction to the J7 roll setpoint (angle or rate). Then the roll is the residual's lever and
  "hidden shortcut" questions are easy to audit. Leave the gripper command non-learned at first (the spec allows it
  only "if verified safe").

### 4. Environment engineering constraints (`FACT`)
- `mujoco.set_mjcb_passive` is **process-global**. The magnet force is installed per process, and any other model built
  in the same process can disable it (exactly P-130). So: **one environment per process**, and every environment
  carries P-131's per-step magnet counter.
- The judged checks in G2 (edit audit, model audit, contacts, oracle) cost about 10 % of the step (`two_arm.contacts`,
  D19 profile). They must stay on in evaluation (G3 checklist) but could be sampled in training. `DECISION` later.
- Gymnasium, PyTorch and Stable-Baselines3 are not installed. Pin them when introduced (CLAUDE.md); CPU-only.

### 5. Headroom for a residual (Q7 of the findings)
- `FACT`: under G2's start draw (±1 mm, ±1°), pilot 4 passed 144/144. The turn error was ≤ 0.31° and no move failed.
- `INFERENCE`: on that distribution, B0's failure rate is near zero, so "RL improves success" cannot be shown there.
  Room for a residual exists only where B0 degrades: larger cube offsets and misalignment, pad friction variation,
  grip-force variation, disturbances, or cost terms (time, peak force, core slip).
- `PROPOSAL`: a pre-registered **B0 stress map** first, on pilot seeds: sweep offset (±1 … ±5 mm), misalignment
  (±1 … ±5°), μ (0.4–1.0) and grip (10–50 N). Find where B0's failure rate is 10–50 %. G2-6 and `offcentre` (5 mm:
  clean in pilot 4) are the starting points. This is also the spec's curriculum stages 2–3.

### 6. Task scope
- The spec's stage 2 says "randomized target-face axis". G2 is U-family from one grasp; other faces need regrasps (G4).
- `PROPOSAL`: G3 stays U-family (U, U′, U2) from G2's grasp. The "face" is randomised only in direction and size of the
  turn.

### 7. Observations and privileged state
- **Available without privileged state:** arm joint states, the modelled wrist F/T (P-114), gripper aperture, commanded
  targets, time.
- **"Current face angle estimate"** has no non-privileged source before G5 (camera).
- `PROPOSAL`:
  - training may use the simulator's face angle (privileged) in the observation and reward;
  - final evaluation runs both a privileged-observation policy and, as a separate arm, a policy without the face angle
    (J7 angle as a proxy), so the dependence on privileged state is measured, not hidden (CLAUDE.md);
  - every success is judged by the independent oracle, as in G2.

### 8. Reward and anti-hacking
- G2 already provides the observables the spec's reward needs: turn progress in the core frame, drift, core slip and
  rotation, penetration, contact classes, F/T, and the oracle. The anti-hacking tests in spec §6 map onto G2's judged
  checks.
- `PROPOSAL`: reuse G2's per-move checks as the episode's termination and success classifier, unchanged, so that "RL
  success" and "G2 success" mean the same thing.

### 9. Documents to update before G3 (`PROPOSAL`, after approval)
- `CONTACT_AND_RL_FINDINGS.md` §1 item 3 and §5: add an addendum with D19's numbers. The magnets are not the main cost
  in the two-arm scene.
- `RL_EXPERIMENT_SPEC.md` §3: the control rate and action definition (issue 3), and the task scope (issue 6), once
  decided.
- A G3 pre-registration, the same process as G2: pilots, reviews and a freeze, with sample sizes set after the stress
  map.

## Decisions for the user (none needed before G2 closes)
1. ~~The baseline structure~~ **Decided: A, keep G2's impedance as B0, disclosed as an abstraction; Q2 admittance check optional (P-134, 2026-11-28).**
2. Whether to pursue a NoSlip-off training model, validated against full M7 (issue 1).
3. Approval of the B0 stress map as G3's first experiment (issue 5).
