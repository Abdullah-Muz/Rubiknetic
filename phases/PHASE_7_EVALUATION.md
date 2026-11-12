# Phase 7 — Scientific Evaluation, Ablations & Release

**Status:** NOT STARTED  
**Gate:** G7 in `../docs/VALIDATION_PLAN.md`  
**Prerequisites:** G6 integrated solver evaluated and all earlier results reproducibly recorded.

## Objective

Produce an evidence-grounded technical report and usable public research repository that make the achievements, limitations and unreliability modes transparent.

## Tasks

1. Freeze release revision, dependency lock, robot/gripper licenses, cube modeling choices, evaluation distributions and configuration.
2. Evaluate classical-only, residual RL and any task-planning alternatives on matched valid scrambles and physics conditions; measure success, solve time, regrasp/handoff counts, contact force/angle errors, constraint artifacts and CPU throughput.
3. Run ablations for camera vs simulator state, contact feedback, curriculum, fingertip geometry, planning cost function and recovery where supported by compute.
4. Report uncertainty, test-set sample counts, genuine failures and negative findings; disclose any manual tuning or incomplete objectives.
5. Verify independent cube oracle, contact causality and benchmark reproducibility from a clean environment.
6. Produce technical figures, plots, documentation and a concise demo showing both normal execution and failure recovery.
7. Audit marketing: no unsupported 'research first', 'novel', 'perfect solve', 'real-world ready', or 'fully physical' claims where abstraction remains.
8. Review third-party CAD / MJCF / gripper assets and puzzle-brand naming; package license notices appropriately.

## Deliverables

Research report, released source and instructions, benchmark harness and provenance, archived experiment configurations, clean demo and known-limitations document.

## Exit criteria

Another developer can reproduce stated results on documented CPU-compatible hardware with specified inputs and versions; all headline claims trace to output evidence. An impressive video with undocumented hidden assumptions does not pass.
