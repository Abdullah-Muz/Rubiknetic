# ER8 — Derated core-magnet arm (PROTOCOL, DRAFT; not approved, not run)

**Status: DRAFT for the user's review.** It is the follow-up that P-61 left optional: "a 1.5×-derated C52 arm".
- **When it was written.** On 2026-11-19, while ER7 was still running and before any ER7 analysis had been run or
  read. The author had seen only ER7 progress lines; the last ones read were PASS lines for trials of E1-3 and E1-4 in
  both arms. Nothing in this draft depends on ER7's results.
- **Condition.** ER8 is proposed only if ER7's C52 arm meets all three of its feasibility signals. If C52 does not
  meet them, this draft lapses: a derated arm of a failing layout would add nothing.
- **What is needed before any ER8 run:**
  - the user's approval, recorded as a DECISION_LOG row;
  - this file, the runner and the analysis committed.
- **Scope.** Unscored and exploratory. It changes no record, selects no mechanism, and cannot change M5's verdict
  (NOT PASSED) or ER7's.

## Question (fixed)
> If every magnet force and torque of the C52 layout is 1.5× weaker than the ideal-magnet model predicts, does C52 still
> meet ER7's feasibility signals on the same seeds and trials?

**Why it matters (`INFERENCE`).**
- The force law models ideal, uniformly magnetised discs. D8's V2 found that it may overstate real magnet strength by
  up to about 1.5×. This is the "ideal-magnet caveat" that M5 §7, ER6 and ER7 carry.
- ER6's static screen found that C52's layer stiffness stays ≥ 1 N m/rad when derated by 1.5. That was statics only.
- If C52 needs the full ideal strength to pass dynamically, a scored test at that strength could pass in simulation
  while a real build fails.

## Arm
- **C52d:** identical to ER7's C52 in every respect except `MagnetParams.scale = 1/1.5`:
  - `core_layout(MagnetParams(4 mm, 3 mm, "N52", scale=1/1.5), clearance=0.2 mm)`;
  - the same cube model, piece gap (0.05 mm), contacts, integrator (implicitfast, 0.5 ms), turner and setup draws.
- **What the scale does.** It multiplies every pair energy by 1/1.5:
  - in the dipole term, through `|m|²` (`MagnetParams.moment` applies `sqrt(scale)`);
  - in the near-field correction, through the table.
- **Table.** M6's N52 table multiplied by 1/1.5 exactly.
  - M6's S1 showed the tables are linear in strength: N52 = N35 × (1.455/1.19)², to 8e-16.
  - A rebuild (about 640 s) is therefore not needed, and is not done.
  - The derived table is saved under its own name with its SHA-256, and its source table's SHA-256 is checked
    against `experiments/M6_core_magnets/results/m6_checks.json`.
- **Note (`FACT`, arithmetic).** The derated strength is (1.455 T)²/1.5 = (1.188 T)². That is within 0.2 % of the N35
  value used in this model (1.19 T). So C52d is also, to within 0.4 % in force, a 4×3 mm **N35** core layout at
  c = 0.2 mm.
  - That configuration is the one ER5 validated directly (V3-turn in the real placement).
  - Its ER6 static screen passed, with layer stiffness about 1.7 N m/rad.
  - This is reported as an observation; ER8 still uses the scaled N52 table, not the N35 file.
- **Controls: none newly run.**
  - ER7's L0 and C52 records serve as the paired controls, on the same seeds (16000–16655).
  - This reuse needs C52d to run on the commit that ER7 ran on, or on a later commit whose diff against `0cc9ff6`
    leaves ER7's runner, M4/M5's runners and `magnets.py` unchanged. S1 below checks this.

## Trial list and seeds
- ER7's trial list, unchanged: M5's Option A list without E1-6n and E1-7, 204 trials.
- Seeds 16000–16655: the same as ER7, deliberately, so that each C52d trial is paired with the same seed in L0 and
  C52.
  - These seeds are already used for diagnostics (ER7).
  - ER8 adds no new seed use.
- E1-1 also runs D10's instrumented 60 s rest, as in ER7.

## Measured
Everything ER7 measures, by the same functions, including `MagnetStats` and the outside-regime flag:
- near pair perpendicular, or near tilt > 20°;
- the validated tilt stays 20°, since scaling does not change geometry.

## Feasibility signals (pre-declared; same as ER7)
For C52d, all of:
1. 0 / 20 E1-1 slip events, and every rest rotation ≤ 0.5°;
2. M5's Option A rule;
3. no flagged trials.

**How the outcome would be read** (`INFERENCE`, fixed now):
- **C52d meets all three.** C52's ER7 result does not depend on the ideal-magnet strength, within the 1.5× caveat. A
  scored pre-registration could then use nominal N52 with the derated arm as a registered sensitivity factor.
- **C52d fails any signal.** The result is reported trial by trial against C52 and L0. A scored pre-registration
  would then have to disclose that its pass depends on magnet strength the model may overstate. Options:
  - a stronger magnet, if one fits;
  - an R1 bench measurement of real magnet force;
  - leaving it to the user.

## Analysis (fixed)
- Pass counts by sub-experiment for C52d, with C52 and L0 alongside, from ER7's `analysis.json`.
- Paired differences, C52d − C52 and C52d − L0, on the same seeds: rest rotation, max sequence drift and turner peak
  torque. For each: the median and the count of seeds where C52d is lower.
- Slip seeds with 95 % Clopper–Pearson intervals; the number of moves at the torque clip.

## Self-checks (all must pass, otherwise the results are not used)
- **S1, harness unchanged since ER7.** `git diff 0cc9ff6 HEAD` is empty for:
  - `experiments/ER7_core_magnet_rehearsal/er7_run.py`;
  - `experiments/E5_scored_m5/run.py` and `experiments/E4_scored_m4/run.py`;
  - `src/rubiknetic/cube_physics/`.
- **S2, scaled system.**
  - The installed MagnetSystem has 40 magnets.
  - The derived table equals M6's table × (1/1.5), to ≤ 1e-12 relative.
  - In the trial model, the layer stiffness on every face equals M6's S2 value × (1/1.5), within 1e-9 relative.
- **S3, body ids.** As ER7, by M4's assertion.
- **S4, reproduction.** One C52 trial per sub-experiment, rerun with scale 1 through the ER8 runner, reproduces its ER7
  record exactly. The comparison is the same as ER7's S1 (JSON form, run-metadata keys skipped). This checks that the
  ER8 wrapper changes nothing but the scale.

## Implementation (to be committed with this file after approval)
- `er8_run.py` imports `er7_run.py` as a module and replaces only:
  - its `MP52`, with the scaled parameters;
  - its table provider, with the scaled table;
  - its output folder (`results/C52d/`);
  - the arm label "C52d".
- Everything else is ER7's code path. It keeps ER7's records (`.json.gz`, exclusive create), resume rule,
  `maxtasksperchild=1` and refusal to start before the self-check passes.
- `er8_analyze.py` reads ER8's records and ER7's records.

## Limits
- As ER7: rehearsal only; magnets without collision geometry (P-58); implicitfast energy oscillation; 20 rest seeds.
- **A uniform 1/1.5 scale is a crude model of a real strength shortfall.** A real magnet may differ in its near-field
  shape, not only in total strength. ER8 tests only the strength.
- **Seeds are shared with ER7.** This makes the comparison paired, but C52d's result is not independent of the seeds
  that C52 saw.

## Cost
- About 204 trials. On ER7's rate with 8 workers, that is about 2–3 h of wall time.
- Memory: about 1 GB for 8 workers.
