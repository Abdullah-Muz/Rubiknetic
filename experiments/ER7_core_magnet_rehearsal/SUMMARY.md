# ER7 — Dynamic rehearsal of the core-magnet layout against M5 (SUMMARY)

**Status: RUN IN PROGRESS. No results are recorded here yet.** This file was started during the main run so that
deviations are recorded as they happen, as `PROTOCOL.md` ("Limits") requires. The results sections are filled from
`er7_analyze.py` only after all 408 records exist. Protocol, runner and analysis: `43094ca` (P-61), with deviation 1
in `0cc9ff6`. Pre-run self-check: `22b6306`.

## Fixed verdict
_Pending: the run has not finished._

## Feasibility signals (C52 arm; pre-declared, not G1 thresholds)
| Signal | Criterion | Result | Met |
|---|---|---|---|
| 1 | 0 / 20 slip seeds over 0–60 s (D11 events) and rest rotation ≤ 0.5° | _pending_ | _pending_ |
| 2 | M5's Option A rule (every per-trial pass flag of the 204 trials, plus E1-6m ⟨P⟩) | _pending_ | _pending_ |
| 3 | No flagged trial (near pair perpendicular, or near tilt > 20°) | _pending_ | _pending_ |

## Results by sub-experiment
_Pending: table from `er7_analyze.py` (L0 and C52, passed / n)._

## Paired comparison (C52 − L0, same seeds)
_Pending: rest rotation, sequence max non-target drift, turner peak torque, moves at the torque clip._

## Self-checks
| Check | Result | Record |
|---|---|---|
| S1, L0 reproduces one M5 scored trial per sub-experiment | Pass after deviation 1: 0 differences in all 10 trials | `results/selfcheck.json` (`22b6306`); first run kept as `results/selfcheck_run1.json` |
| S2, C52 system reproduces M6's layer stiffness | Pass (difference 0 in both self-check runs) | `results/selfcheck.json` |
| S3, body ids match the magnet layout | Asserted in every C52 trial by M4's existing check; a failure would stop the trial | per-trial records |
| S4, E1-1 instrumented rest matches the scored rest | _pending_ | per-trial records |

## Deviations after the first run
2. **Restart after a memory-pressure kill, 2026-11-19.** `FACT`:
   - **What happened.** The first attempt of the main run started on 2026-11-18 with `--jobs 12`. The user paused
     it with SIGSTOP about 3.5 min in. While it was paused, Claude Code stopped the background task because the
     system was critically low on memory, and the paused processes were lost.
   - **Data affected.** None: the first attempt had written 0 of 408 records.
   - **Restart.** At 2026-11-19T16:16:31-08:00 the run restarted with `--jobs 8`, from the same commit (`0cc9ff6`;
     `results/environment.json`, rewritten at the restart). `run_log.txt` keeps the first attempt's start line and a
     restart marker.
   - **Other load.** During the restarted run, another project's job (about 35 Python worker processes) shared the
     same WSL2 machine, leaving about 1 GB of memory free.

   **Why this does not change the results** (`INFERENCE`, from the runner's design):
   - Each trial has a fixed seed and runs in a fresh worker process (`maxtasksperchild=1`).
   - Records are written once per trial, and the physics does not depend on wall-clock time.
   - So the worker count and the other load can change only the wall-time fields (`wall_s`, `er7_wall_s`,
     `loadavg_start`).

## Limits
As in `PROTOCOL.md`:
- Rehearsal only.
- The magnets have no collision geometry (P-58 abstraction).
- implicitfast has a bounded energy oscillation.
- The ideal-magnet caveat applies.
- 20 rest seeds give wide intervals.
