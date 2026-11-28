# D19: where the simulation time goes (UNSCORED; pilot seed 29001; 2026-11-28)

**Why:** planning G3 (reinforcement learning) needs a realistic simulation budget. With the magnets on, a G2 trial
runs at about 0.04× real time under 8 workers (pilot 4). The user asked for a speed study while G2 waits on its review.

**Scope:** measurement only. It changes no frozen file and no model used for any result. The what-if variants run on
an in-memory copy of the model and are **candidates, not adopted settings**.

**Scripts:**
- `speed_profile.py`: cProfile of the scene build and start sequence, then 2,000 control steps with the magnets on
  and off.
- `speed_timers.py`: MuJoCo's internal timers per pipeline stage, with what-if copies (NoSlip 0 / 5, solver
  iterations 50).

Run them from the repo root in WSL with `~/.venvs/rubiknetic/bin/python`.

## Results (`FACT`; WSL, 16 logical CPUs, with review and probe jobs running at the same time, so absolute rates are
## approximate and ratios are the reliable part)
**Scene:** nv 99, 87 geoms (65 meshes), dt 0.5 ms, Newton solver (100 iterations, 50 line-search), NoSlip 10, elliptic
cones, implicitfast, sparse Jacobian. After the start sequence: about 90 contacts (49 cubie–cubie, 48
fingertip–cubie) and about 410 constraint rows.

| Measurement | Rate |
|---|---|
| Full control step (controllers + audit + magnets + mj_step) | 159 steps/s (0.080× real time, one process) |
| Same with the magnet callback removed | 191 steps/s: **the magnets are about 16–20 % of the step** |
| Controllers alone (impedance + J7 law) | about 5,200 evaluations/s (not a bottleneck) |
| Bare `mj_step`, magnets off | 197–245 steps/s |

**Per stage of `mj_step`** (ms per step, magnets off):

| Variant (what-if) | Steps/s | STEP | POS_PROJECT | CONSTRAINT | COLLISION |
|---|---|---|---|---|---|
| As built (NoSlip 10) | 197 | 5.05 | **2.52** | 1.86 | 0.39 |
| NoSlip 5 | 211 | 4.73 | 2.41 | 1.66 | 0.37 |
| **NoSlip 0** | **1,052** | **0.94** | 0.00 | 0.37 | 0.33 |
| Solver iterations 50 | 203 | 4.90 | 2.43 | 1.80 | 0.37 |

## Reading
- `FACT`: switching NoSlip off makes the bare step **5.3× faster**. Halving NoSlip or the solver iterations changes
  almost nothing.
- `INFERENCE`: the cost of NoSlip is mostly fixed per step, not per iteration: with NoSlip on, MuJoCo computes the
  constraint projection (POS_PROJECT) over all ~410 rows, and the constraint stage also grows. Not checked against
  MuJoCo's source.
- `INFERENCE`: rewriting the Python magnet callback would gain at most about 1.2×. NoSlip off plus a faster magnet
  callback could give roughly 5–6×.
- **NoSlip 10 is part of the G1-passed M7 mechanism** (P-82, P-95): it is what stops layers creeping at rest. Dropping
  it changes the validated physics, so it is **not** an option for G2 or any scored evaluation as things stand.

## Open (for the user, before G3 planning)
- `PROPOSAL`: a cheaper **training** model (e.g. NoSlip 0, or NoSlip only on cubie–cubie contacts if MuJoCo allows
  it), validated against full M7 by a pre-registered comparison, with every final evaluation on full M7.
- Other levers not yet measured: fewer contact rows (condim, contact pruning between arm A's pads and the held
  layers), a vectorised or compiled magnet force, and parallel environments across the 16 CPUs.
