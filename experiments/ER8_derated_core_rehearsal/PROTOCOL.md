# ER8 — Robustness arms for the core-magnet layout: derated strength and half timestep (PROTOCOL, fixed before any run)

**LAPSED on 2026-11-19 (P-65). ER8 was never run.** ER7's C52 arm met signals 1 and 3 but failed signal 2 (E1-5s
snap-back 10 / 20), so the condition below is not met and the runner refuses to start. No self-check and no trial
was run. The text below is kept unchanged as the record of what was fixed.

**Status when written: fixed on 2026-11-19, before any ER8 run and before ER7 finished.**
- **Approval.** The user's instruction "work autonomously to fix them all" (2026-11-19) was a reply to a list that
  named "the ER8 derated arm, if you want it" and "the integrator's … effect on rest slips hasn't been measured". The
  main session treats that as approval to run ER8 under this protocol, and records it as such in the DECISION_LOG
  (P-63). The user may reverse it.
- **History.** A draft of this file (`1ce3b24`) had the derated arm only. This version adds the half-timestep arm
  C52h, the condition check in the runner, and the self-checks as implemented.
- **What the author had seen of ER7 when this was fixed** (ER7 was at about 200 of 408 trials; no analysis had been
  run):
  - progress lines up to trial 198, with three failures, all in L0 (rest rotation 0.568° on seed 16003 and 0.559° on
    seed 16005, and one E1-4 sequence, seed 16405) and none in C52;
  - the fields of one C52 record, `E1-1/rest_s16000` (rest rotation about 2e-10°), read to learn the record layout.

  Nothing in this protocol was chosen using those values. The signals are ER7's, unchanged.
- **Condition.** ER8 runs only if ER7's C52 arm meets all three of its feasibility signals. The runner checks this in
  ER7's `results/analysis.json` and refuses otherwise. If C52 does not meet them, ER8 lapses: robustness arms of a
  failing layout would add nothing.
- **Scope.** Unscored and exploratory. It changes no record, selects no mechanism, and cannot change M5's verdict
  (NOT PASSED) or ER7's.

## Questions (fixed)
> 1. If every magnet force and torque of the C52 layout is 1.5× weaker than the ideal-magnet model predicts, does C52
>    still meet ER7's feasibility signals on the same seeds and trials?
> 2. Does C52's rest result (E1-1) hold when the timestep is halved?

**Why they matter (`INFERENCE`).**
- **Strength.** The force law models ideal, uniformly magnetised discs. D8's V2 found that it may overstate real
  magnet strength by up to about 1.5×. ER6's static screen found C52's layer stiffness stays ≥ 1 N m/rad when derated
  by 1.5, but that was statics only. If C52 needs the full ideal strength to pass dynamically, a scored test at that
  strength could pass in simulation while a real build fails.
- **Timestep.** With this layout, implicitfast at 0.5 ms shows a bounded energy oscillation of about 10 % on a
  rigid-layer release, and about 5 % at 0.25 ms (M6 V5). M5's rest slips were sensitive to the timestep in D10, in no
  consistent direction. A rest result that changed with the timestep would be a numerical artefact, not a property
  of the layout.

## Arms
Both arms run through ER7's runner, loaded unchanged. Each trial runs in a fresh worker process.

- **C52d (derated strength), all 204 trials.** Identical to ER7's C52 except `MagnetParams.scale = 1/1.5`.
  - **What the scale does.** It multiplies every pair energy by 1/1.5: in the dipole term through `|m|²`
    (`MagnetParams.moment` applies `sqrt(scale)`), and in the near-field correction through the table.
  - **Table.** M6's N52 table multiplied by 1/1.5, saved as
    `tables/tilt_4x3_1.455T_s0.666667_r8_h1.5_q16x48.npz` (git-ignored; its SHA-256 is in `results/selfcheck.json`
    and is checked in every worker, together with the source table's recorded hash). M6's S1 showed the tables are
    linear in strength to 8e-16, so the 640 s rebuild is not done.
  - **Note (`FACT`, arithmetic).** The derated strength is (1.455 T)²/1.5 = (1.188 T)², within 0.4 % in force of the
    N35 value used in this model (1.19 T). So C52d is also, very nearly, a 4×3 mm **N35** core layout at c = 0.2 mm:
    the configuration ER5 validated directly, whose ER6 layer stiffness is 1.72 N m/rad.
- **C52h (half timestep), E1-1 only, 20 trials.** Identical to ER7's C52 except timestep 0.25 ms instead of 0.5 ms,
  applied as D10's A1 arm applied it (`scored.params_for` wrapped). It covers the scored 10 s rest and the
  instrumented 60 s rest. Nothing else changes; the sampling interval of the time series stays 25 ms.
- **Controls: none newly run.** ER7's L0 and C52 records are the paired controls, on the same seeds. Self-check S1
  makes sure ER8 runs the same code.

## Trial list and seeds
- ER7's trial list and seeds (16000–16655), unchanged, so that each ER8 trial is paired with the same seed in L0 and
  C52. These seeds are already used for diagnostics; ER8 adds no new seed use.
- E1-1 trials also run D10's instrumented 60 s rest, as in ER7.
- Rest trials are run first.

## Measured
Everything ER7 measures, by the same functions, including `MagnetSystem.stats` and the outside-regime flag (near pair
perpendicular, or near tilt > 20°; scaling and the timestep do not change the geometry of the validated regime).

## Feasibility signals (pre-declared)
**C52d**, the same three as ER7:
1. 0 / 20 E1-1 slip events, and every rest rotation ≤ 0.5°;
2. M5's Option A rule;
3. no flagged trials.

**C52h** is reported only, against the E1-1 parts of the same signals: 0 / 20 slip events, every rest rotation
≤ 0.5°, no flagged trials.

**How the outcomes would be read** (`INFERENCE`, fixed now):
- **C52d meets all three.** C52's ER7 result does not depend on the ideal-magnet strength, within the 1.5× caveat.
- **C52d fails any signal.** The result is reported trial by trial against C52 and L0. A scored pre-registration
  would then have to disclose that its pass depends on magnet strength the model may overstate, and the options
  (a stronger magnet if one fits; an R1 bench measurement of real magnet force) go to the user.
- **C52h differs from C52** in slips, or in any rest trial's pass/fail. The rest result is then timestep-sensitive
  and is reported as a numerical fragility that a scored pre-registration must disclose.

## Analysis (fixed; `er8_analyze.py`)
- Pass counts by sub-experiment for C52d, with C52 and L0 alongside, all three computed by ER7's functions.
- Paired differences on the same seeds, C52d − C52 and C52d − L0: rest rotation, max sequence drift and turner peak
  torque. For each: the median and the count of seeds where C52d is lower. For C52h − C52: rest rotation.
- Slip seeds with 95 % Clopper–Pearson intervals; the number of moves at the torque clip.

## Self-checks (all must pass, otherwise nothing is run; `er8_run.py selfcheck`)
- **S1, harness unchanged since ER7.** `git diff 0cc9ff6 HEAD` is empty, and nothing is uncommitted, for:
  `experiments/ER7_core_magnet_rehearsal/er7_run.py`, `experiments/E5_scored_m5/run.py`,
  `experiments/E4_scored_m4/run.py`, `experiments/D10_m5_rest_diagnostic/d10_rest.py` and
  `src/rubiknetic/cube_physics/`. The check is repeated at the start of the run.
- **Table.** The derived table equals M6's table × (1/1.5) to ≤ 1e-12 relative, with the grid arrays identical.
- **S2, scaled system.** In the trial model, the installed MagnetSystem has 40 magnets and scale 1/1.5, and its layer
  stiffness on every face equals M6's S2 value × (1/1.5) within 1e-9 relative.
- **S3, body ids.** As ER7, by M4's assertion, in every trial and in S2.
- **S4, reproduction.** One C52 trial per sub-experiment (the first of each, 10 trials), run through the ER8 runner
  with nothing changed, reproduces its ER7 record exactly, including the 60 s rest time series. Only run-metadata
  keys are skipped: `wall_s`, `wall_time_s`, `er7_wall_s`, `loadavg_start`, `environment` and `source_commit`. This
  checks that the ER8 wrapper changes nothing but what an arm asks for.
- **Per trial.** Each ER8 record must show the arm's timestep in its parameters and the arm's scale in its magnet
  description; the worker asserts both.

## Limits
- As ER7: rehearsal only; magnets without collision geometry (P-58); 20 rest seeds give wide intervals (0 / 20 has a
  95 % upper bound of 17 %).
- **A uniform 1/1.5 scale is a crude model of a real strength shortfall.** A real magnet may differ in its near-field
  shape, not only in total strength. ER8 tests only the strength.
- **Seeds are shared with ER7.** This makes the comparison paired, but ER8's results are not independent of the
  seeds C52 saw.
- **C52h covers rest only.** It says nothing about the timestep's effect on turning. One halving is not a
  convergence study.
- Deviations after the first run are recorded in the ER8 summary.

## Cost
About 224 trials. At ER7's rate with 8 workers, about 2–3 h of wall time when the machine is shared. Memory about
1 GB.
