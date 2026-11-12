# Phase 3 — Residual Reinforcement Learning for Contact-Rich Turns

**Status:** NOT STARTED  
**Gate:** G3 in `../docs/VALIDATION_PLAN.md`  
**Prerequisites:** Mechanically valid cube and reproducible classical-control baseline (G1/G2).

## Objective

Train and independently evaluate a **bounded Cartesian residual RL policy** for one cube-face turn, while arm A maintains a conventionally controlled stabilizing grasp. Learning should improve or characterize contact behavior—not learn a hidden shortcut to logical cube moves.

## Tasks

1. Translate `../docs/RL_EXPERIMENT_SPEC.md` into tested Gymnasium observation/action/reward/terminal contracts.
2. Define tool/cube frames, reward observables, physical completion checks and bounds before training.
3. Benchmark SAC vs no-residual classical and random-residual negative control; optionally PPO under explicit compute budget.
4. Implement curriculum: fixed grasp → small pose variations → friction/offset variations → bounded disturbances.
5. Separate train/validation/test distributions; log seeds, policy checkpoints, environment versions, compute and wall time.
6. Run held-out physical face-turn success tests with independent oracle, force/angle/slip diagnostics and confidence intervals where sample size supports them.
7. Audit for reward hacking, simulator state overwrites, unrealistic contact impulses and unauthorized privileged information.

## Deliverables

Reusable RL environment; trained checkpoint if successful; classical/B0 and SAC/B2 comparisons; reproducible training/evaluation commands; negative results and failure analysis; CPU profiling report.

## Exit criteria

The residual-learning result is **reproducible and valid** regardless of whether RL improves on classical control. A policy that wins only by physics exploitation fails the gate. Record signed-off decision before integrating into bimanual hierarchy.

**Parallel opportunity:** Basic planning grammar and camera placement study can proceed, but not replace contact validation.
