# Phase 3 (G3) design: residual RL on the G2 controller (DRAFT for the user's decisions)

**Status: DESIGN, decisions D1–D5 taken by the user 2026-11-28 (P-146).** No RL code exists and no training has run. This document lists the
design choices G3 needs, with a recommendation for each. The user approves them before any implementation. Then come
a B0 stress map (unscored), the environment, pilots, and a G3 pre-registration with reviews and a freeze, as for G2.

**Gate (`docs/VALIDATION_PLAN.md` G3):**
- action/observation/frame specification and reward unit tests;
- B0 and no-op/random residual controls on matched starts;
- a SAC residual policy, trained with seed, configuration, checkpoint and logging, and evaluated on held-out starts;
- every physics validity check active during evaluation;
- training steps, wall time, CPU, uncertainty and negative cases reported.

**Pass = a scientifically honest, reproducible comparison, not necessarily an RL win.**

**Inputs:**
- `docs/RL_EXPERIMENT_SPEC.md`;
- `phases/PHASE_3_REINFORCEMENT_LEARNING.md`;
- `docs/research/PHASE_3_READINESS_2026-11-28.md` (R);
- `docs/research/G3_RL_LITERATURE_UPDATE_2026-11-28.md` (L);
- `experiments/D19_speed_study/README.md`;
- the G2 report.

Labels: `FACT`, `INFERENCE`, `PROPOSAL`, `DECISION` (the user's).

## 1. Already decided
- **B0 = G2's validated controller** (torque-level Cartesian impedance + J7 torque law), disclosed as an abstraction
  the real xArm cannot run (P-134).
- **Full M7 physics for every result.** A NoSlip-off training surrogate is not pursued for now (L: about 2.3–2.6×
  end-to-end, and no published validation of reduced-solver training).
- **Validity checks are G2's, unchanged:** the magnets every step, the edit and model audits, contacts, causality,
  drive, the oracle. An RL success means exactly a G2 success.

## 2. Choices (decided, P-146)
**Decisions:**
- D1 approved.
- D2 approved.
- **D3: asymmetric actor-critic.** The privileged layer angle goes to the critic only; the actor never sees it.
- D4 approved.
- **D5: B0, B1 and B2, plus B3 = PPO at a matched budget.**

The proposals below are kept as written.
### D1. Task and headroom: start with a B0 stress map (`PROPOSAL`)
- `FACT`: under G2's start draw (±1 mm, ±1°), B0 passed 128/128. A residual cannot show a success gain there.
- **Proposal:** an unscored **B0 stress map** on pilot seeds as G3's first experiment. B0 alone, no learning; about 80
  short trials, about 1 h on 8 workers. It sweeps one factor at a time:
  - cube offset ±1, 2, 3, 4, 5 mm;
  - layer misalignment ±1, 2, 3, 5°;
  - pad friction 0.4–1.0;
  - grip 10–50 N;
  - arm B approach error ±1–3 mm.
- Outcome: the conditions where B0's failure rate is roughly 10–50 %. Those define G3's training and held-out
  distributions, and the metrics where a residual has room: success, peak force, core slip, time.
- G3 stays **U-family** (U, U′, U2) from G2's grasp (R issue 6). The other faces need G4's regrasps.

### D2. Action space (`PROPOSAL`, R issue 3)
- A bounded residual on the **setpoints**, never on torques (L: a residual on the controller's output is resisted by
  it):
  - (a) arm B's gripper-base position target, ±3 mm per axis;
  - (b) its axis direction, ±2°;
  - (c) the J7 roll target, ±3°.
- Gripper force and timing are not learned.
- Policy rate **20 Hz** (100 physics steps), action held between updates.
- Bounds are to be tuned in a residual-bound pilot (findings Q9): the largest bound at which a random residual (B1)
  does not degrade B0.

### D3. Observations and privileged state (`PROPOSAL`, R issue 7)
- **Available without privileged state:** arm joint state, the gripper-base pose error, the wrist F/T reading, the
  gripper aperture, the commanded move, the phase and elapsed fraction.
- **The layer's turn angle has no camera source before G5.**
- Proposal:
  - train with the simulator's layer angle as a **privileged** observation;
  - evaluate two policies, one with it and one without (J7 angle as a proxy), so the dependence on privileged state is
    measured, not hidden (CLAUDE.md).

### D4. RL software and budget (`PROPOSAL`, L)
- **Stable-Baselines3 SAC on CPU PyTorch, with Gymnasium.** These are new dependencies, pinned when introduced
  (CLAUDE.md), CPU-only.
- Critic LayerNorm (L: "crucial" for sample-efficient residual RL) added through a custom policy. The residual output
  starts at zero.
- The replay buffer is seeded with about 20k B0 transitions (residual = 0).
- **Budget:** 2×10⁵ control steps per seed, 3 seeds (5 if affordable), checkpoints at 25k/50k/100k/200k.
  - `INFERENCE` from D19/pilot 4: about 8 h per seed on 8 parallel environments.
  - A **50k-step pilot on one seed** comes first.
- PPO is optional, at a matched budget. It is expected to underperform (L).

### D5. Evaluation design (`PROPOSAL`, L Q4)
- A fixed bank of held-out start conditions from the stress-map region, on seeds never used in training.
- B0, B1 (random residual) and B2 (SAC) are each run on the same starts.
- Paired comparison per condition: exact McNemar per seed, Wilson intervals, every seed reported. A **no-harm check**
  on G2's own start distribution (B2 must not fall below B0 there).
- Reward hacking audit: G2's checks plus the RL spec's §6 tests.

## 3. Proposed order of work (each step reviewed by the user)
1. **This design** (D1–D5): the user's decisions.
2. **B0 stress map** (unscored), then the user picks the training and held-out distributions.
3. **Environment** (Gymnasium wrapper around G2's scene; one process per environment, P-130's per-step magnet counter
   kept). Unit tests:
   - action/observation/frame contracts;
   - reward terms;
   - B0 reproduction (residual = 0 gives the G2 trajectory bit-identically);
   - the anti-hacking tests.
4. **Throughput measurement** with 1, 4 and 8 environments (findings Q5), then the compute cap.
5. **Pilots:** the residual-bound pilot (B1), then a 50k-step SAC pilot.
6. **G3 pre-registration**, then reviews until "ACCEPTABLE AS IS", the user's freeze, and the scored training and
   evaluation.
