# D14 Stage 2 — the rest of the Part G probe at `noslip_iterations` 10 (PROTOCOL, fixed before any run)

**Status:** approved by the user on 2026-11-23 (P-74: "yes", in reply to the recommended answers to OPEN-1 to OPEN-12
of `proposals/STAGE2_DRAFT.md`). This file is committed with `d14s2_run.py` and `d14s2_analyze.py` **before** the
first Stage 2 computation (free-decay check, gate or trial). It follows the draft (sections 1–3, verified by the main
session) with the user's answers fixed below.

**Scope (`FACT`):** UNSCORED, reported only.
- M5 stays NOT PASSED, and Part G's outcome stays as reported. Nothing is selected (OPEN-6).
- Stage 2 changes one setting, `noslip_iterations` from 0 to 10, in every trial model it compiles. The setting was
  chosen after M5, Part G and D13, and this is disclosed. Nothing here adopts it for G1.
- Stage 2 writes only under `experiments/D14_noslip_rest_rehearsal/`. It edits no committed code.
- Seeds come only from the committed probe trial lists (16100–16123, 16500–16541, 16551–16568). 17000–17999,
  10000–10999, 16700–16739 and 16900–16999 are untouched. The U5 rest extension and the P-70 follow-up probe stay
  deferred (OPEN-10).

## 1. Trials and arms (`FACT`, draft section 1)
- **Experiments.** E1-2 (24), E1-5 (42) and E1-5s (20, of which 12 are scored). The trial IDs and seeds are exactly the
  committed Part G probe and ER7 lists, which gives **86 trials per arm**.
- **E1-1 is not rerun.** Signal 2 comes from Stage 1 (D14 `SUMMARY.md`: met by all three arms).
- **Arms (OPEN-1): L0, PG8 and PG20.** All three met Stage 1.
- **One path for all three:** `er9g_run.run_one` with `install_er7(arm, "N52")` and the class-stats system. For L0
  this is the composite path that GS1 showed reproduces ER7's L0 records exactly. D_val is 12.0° for PG8 and PG20
  (their `P4d` files), and the proxy for L0 (`er9g_stats.PROXY_D_VAL`), as in GS1. That is 258 trials.

## 2. Order of work and stops (fixed)
1. **Free-decay check (OPEN-11).** Section 3. If it fails, Stage 2 stops and reports to the user before any trial.
2. **Reproduction gate (OPEN-2).** At the **frozen** setting, with Stage 2's read-only logging installed, run the
   first trial (in committed list order) of E1-2, E1-5 and E1-5s for each arm: 9 trials.
   - Each must equal its committed record exactly on every field except `er9g_run.GS_SKIP` (run metadata and naming)
     and Stage 2's own `d14s2` block. PG records get `apply_verdict` first, as in the probe.
   - Committed records: PG8 and PG20 from `ER9 .../results/hybrid_g/probe/<arm>/<exp>/`; L0 from ER7
     `results/L0/<exp>/`, compared as GS1 did.
   - If any differs, Stage 2 stops and reports that alone.
3. **Cost check (OPEN-3).** Projected total = elapsed time + Σ over the remaining trials of (the committed frozen
   wall time × the measured gate ratio (Stage 2 gate wall / committed wall, per arm) × 1.26) / workers. If it exceeds
   **4 hours**, Stage 2 stops.
4. **The 258 NoSlip trials,** on 4 workers, with fewer if less than 2 GB of memory would remain free.
   - **Pause rule (OPEN-8).** At the first trial with an abort, a numerical failure or a harness exception, no new
     trial starts. Trials in flight finish and are recorded. The run then pauses for the user.
   - Such a trial counts as failed. It is not excluded and not rerun (G.4).
   - Runs killed for low memory are not restarted without the user's instruction.

## 3. Free-decay check (fixed; for MuJoCo issue #2423)
**Purpose.** Issue #2423 (open) reports that joint `frictionloss` + `damping` + NoSlip makes a spinning joint
decelerate far too slowly. Every cube piece joint has both (damping 0.0005, frictionloss 0.0005, armature 1e-6;
`M1Params`).

**Cases.** All use the trial models' options: implicitfast, 0.5 ms, elliptic, `impratio` 10, Newton, 100 iterations,
tolerance 1e-10. Each runs at `noslip_iterations` 0 and 10.
- **A, hinge (centre-like).** One body on a hinge about z through the origin, with a cubie-sized box (mass 3.4 g,
  half-size (pitch − gap)/2) centred at (0, 0, pitch). The joint parameters are `M1Params`'. No contacts, gravity 0.
  Initial ω = 20 rad/s.
- **B, ball (corner-like).** As A, but a ball joint at the origin, with the box at (pitch, pitch, pitch). Initial ω =
  20 rad/s about z.
- **C, U layer in the cube.** The trial model (`build_m1_xml(M1Params(radial_preload=0, gap=5e-5, rig=True))`, rig
  open, no magnets), settled 0.5 s from home. Then the 9 U-layer pieces are given a common angular velocity of 5 rad/s
  about +z (ball joints: R_bodyᵀ ω; centre hinge: ω along its axis). This is a write to `qvel`, allowed here because
  this is a diagnostic model, not a trial.

**Measures.** The decay time (from the initial spin until |ω| ≤ 1 % of the initial value; for C, the U layer's mean
angular rate about z) and the angle turned in that time. Cap: 3 s.

**Pass.** For every case, the ratio (NoSlip 10 / NoSlip 0) of the decay time and of the angle turned is within
[0.8, 1.25]. A case that does not decay within 3 s fails. If any case fails, Stage 2 stops and reports to the user.

## 4. Injection and proof (fixed; draft section 3.4)
- **The NoSlip wrapper.** In each NoSlip worker (fresh process, one trial), `scored.build_m1_xml` is replaced by
  `d13_run.with_noslip(orig(p), 10)` for the whole trial. It is never installed in the parent or in gate workers.
- **Logging.** `scored.Trial` is replaced in every Stage 2 worker (gate and NoSlip) by a subclass. Its `__init__` calls
  the original unchanged and then appends a read-only step hook, and it records the compiled options. The gate shows
  the logging is read-only.
- **Proof per record**, in `rec["d14s2"]`:
  - the wrapper's call count (must be 1 in NoSlip trials, 0 in gate trials);
  - the trial model's `timestep`, `impratio`, `noslip_iterations`, `cone`, `solver`, `iterations` and `tolerance`;
  - the magnet system model's `noslip_iterations` (expected 0) and `nv` (must equal the trial model's).

  A NoSlip record whose trial model does not have `noslip_iterations` 10, or whose call count is not 1, is a harness
  error, and Stage 2 stops.
- **Per-step logging (OPEN-4, OPEN-5; read-only, reported only).**
  - All trials: the largest `solver_niter` and the count of steps at the iteration limit.
  - E1-2 additionally, every 10 steps (5 ms): time, all six turner angles and actuator torques, the six layers' mean
    rotation from t0, and the pad contact count.

## 5. Measures, signals and reading (fixed)
**Signals at NoSlip, per arm (G.8, unchanged; draft section 2.1):**
1. E1-5s: every scored trial passes (`er9g_run.pass_g`).
2. E1-1: from Stage 1 (met by all three).
3. E1-2 and E1-5: every trial passes (`pass_g`).
4. No trial out of regime (`oor_g`, D_val 12°).

Signals 1, 3 and 4 use Part G's functions for PG8 and PG20. L0 is reported against the same items, with its M4 pass
flag and its legacy statistics, as in Part G and Stage 1. No new threshold is introduced.

**Reported only (OPEN-7: counts, no reading set in advance):**
- every pass flag that flipped against the committed frozen record, with its reasons;
- E1-2 turner torque per move (`er9g_run.turner_stats`: median, p99, max, above 0.45 N·m, above 0.5 N·m, at the clip),
  frozen against NoSlip;
- paired direction counts for the per-trial peak torque (E1-2) and |error after 1 s| (E1-5s);
- E1-5 outcomes;
- E1-5s errors;
- the wall-time ratio;
- the largest solver iteration count;
- **E1-2 stall descriptors:**
  - the longest window, from the first sample with turner |angle| > 1° until the turning layer reaches 85°, in which
    the layer advances < 0.05° over ≥ 30 ms;
  - the number of such windows;
  - the largest turner-minus-layer angle (pad slip).

**Reading.**
- An arm that meets signals 1–4 at NoSlip is a **candidate for Stage 3** (model re-validation and a G1
  pre-registration). Stage 3 runs only on the user's go.
- An arm that misses a signal is reported with the failing trials.
- No arm is selected here.

**Predictions, written before any run (`INFERENCE`):**
- The decay check passes for A and B only if issue #2423 does not affect implicitfast with these parameters. This is
  uncertain.
- All three arms meet signals 1, 3 and 4.
- E1-2 median torque within ±20 % of frozen.

## 6. Limits (fixed)
- Rehearsal seeds only: they were used for every earlier choice.
- The setting was chosen after the failures.
- NoSlip is an ad-hoc post-pass (MuJoCo documentation).
- The decay check tests isolated joints and one layer spin, not every motion in a turn.
- Physical credibility stays unverified, and the contact friction of 0.2 is an assumption.
- Changes after the first computation are recorded as deviations in the Stage 2 summary.
