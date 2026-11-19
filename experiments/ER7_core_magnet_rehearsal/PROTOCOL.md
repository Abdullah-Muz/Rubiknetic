# ER7 — Dynamic rehearsal of the core-magnet layout against M5 (PROTOCOL, fixed before any run)

**Status:** approved in P-61 (user: "1", 2026-11-18, approving this protocol as written; the optional derated C52 arm was not added and stays a follow-up). Written by the main session; this protocol, `er7_run.py` and `er7_analyze.py` are committed **before** the first ER7 run. Unscored and exploratory. It changes no record, cannot change M5's verdict (NOT PASSED, P-51) and selects no mechanism. A candidate would need the user's approval and a new pre-registration with new seeds.

## Question (fixed)
> On new seeds and an identical trial list, does replacing M5's 48 corner–edge magnets with the 20 core magnets (4×3 mm
> N52, c = 0.2 mm; P-59, P-60) remove the rest slips, while keeping M5's sequence, forgiveness and abuse results?

## Arms (paired: same trial list, same seeds)
- **L0 (control):** frozen M5. 48 × 4×2 mm N35 corner–edge magnets, piece gap 0.05 mm, M5's validated tables, every
  M5 setting.
- **C52:** identical to L0 except for the magnets. `core_layout(MagnetParams(4 mm, 3 mm, "N52"), clearance=0.2 mm)`
  with M6's N52 table, whose SHA-256 is recorded in `experiments/M6_core_magnets/results/m6_checks.json`. Cube model,
  gap, contacts, integrator (implicitfast, 0.5 ms), turner and setup draw are unchanged.

## Trial list
- M5's Option A scored list, unchanged in content: E1-1 (20), E1-2 (24), E1-3 (22), E1-4 (40), E1-5 (42), E1-5s (20),
  E1-6a (6), E1-6b (6), E1-6c (8) and E1-6t (16). That is 204 trials per arm.
- E1-6n (the no-magnet arm) and E1-7 (sensitivity) are left out.
- **Seeds:** M5 scored seed + 6000, i.e. 16000–16655, including the hard-coded E1-5s and E1-6t bases. E1-4's
  scrambles are drawn from the new seeds, as in M5.
  - A repository search found no use of 16000–16999 as seeds.
  - After ER7, these seeds count as used for diagnostics.
- **E1-1 rest:** 60 s with D10's instrumented loop, as in ER2's O2. The frozen metric (peak rotation in the first 10 s)
  is unchanged; the extra 50 s and the time series are descriptive.

## Measured (each per trial and arm)
- Every M5 metric, computed by M5's frozen functions:
  - rest rotation;
  - oracle match;
  - per-move drift and the E1-4 growth slope;
  - E1-5 and E1-5s completion and legality;
  - the E1-6 abuse quantities;
  - turner peak torque per move, with the count of moves at the clip.
- For E1-1: slip events by D11's fixed definition, and their time and pieces.
- **Force-law regime (P-60):** `MagnetSystem.stats` per trial (clamped z, near perpendicular, max near tilt). A C52
  trial is **flagged "outside the validated regime"** if it has near_perpendicular > 0 or max near tilt > 20°. ER5's
  validated real-placement trajectories reached 18–20°.
- Energy and impulse disclosure as in M5 (E1-6m accounting), plus wall time and steps/s.

## Feasibility signals (pre-declared; for deciding the next step, not G1 thresholds)
For C52, all of the following:
1. 0 / 20 E1-1 slip events, and every E1-1 rest rotation ≤ 0.5° (M1's criterion).
2. Every other experiment passes M1's thresholds as M5's `analyze.py` applies them (E1-2/3/4 oracle match and
   drift ≤ 1°, E1-4 growth slope < 0.005°/move, E1-5, E1-5s and E1-6a/b/c/t).
3. No flagged trials. Flagged trials are reported with and without inclusion; any flag means the signal is not met.

If C52 meets all three, I would propose a scored pre-registration for it as a G1 candidate, for your approval, with
new seeds and an independent review, as for M5. If it does not, the failures are reported against L0 trial by trial,
and the next step goes back to you.

## Analysis (fixed)
- Per experiment: pass counts for both arms, as M5's `analyze.py` reports them.
- Paired differences on the same seeds: rest rotation, maximum drift and turner peak torque, with medians and the
  count of seeds where C52 is lower.
- Slip rate per arm, with 95 % Clopper–Pearson intervals.
- L0 is also compared with M5's scored record (seeds 10000–) as a check of the harness, descriptive only. L0 is not
  expected to reproduce M5 trial by trial, because the seeds differ.

## Self-checks (all must pass, otherwise the results are not used)
- **S1:** before the run, one M5 scored trial per experiment, re-run in the L0 arm with its original M5 seed,
  reproduces its scored record exactly (rest rotation, per-move drift and oracle state). This checks that the harness
  is unchanged.
- **S2:** the C52 arm's installed MagnetSystem has 40 magnets, the M6 table hash, and reproduces M6's S2 layer
  stiffness within 1e-9 in the trial model.
- **S3:** the C52 trial models' body ids match the magnet layout. This is M4's existing assertion.

## Limits (fixed)
- Rehearsal only. Twenty rest seeds give wide intervals: 0 / 20 has a 95 % upper bound of 17 %.
- The magnets have no collision geometry. The positions inside the B1 piece volumes are an abstraction (P-58).
- implicitfast at 0.5 ms has a bounded energy oscillation of about 10 % on a rigid-layer release (M6), as did D8's
  layout. No timestep change is made; the same setting is used in both arms.
- The ideal-magnet caveat (up to 1.5× overstatement) carries over. A derated C52 arm is not included; it could be a
  follow-up.
- Deviations after the first run are recorded in the ER7 summary.

## Cost
About 400 trials, which on M5's record (11,944 s for 440 records) suggests **3–4 h** of wall time.
