# D14 Stage 3a and 3b — model re-checks and the full-rehearsal remainder at `noslip_iterations` 10 (PROTOCOL, fixed before any computation)

**Status:** approved by the user on 2026-11-23 (P-75: "yes", in reply to "go ahead with 3a, and 3b on all three
designs", from `proposals/STAGE3_PLAN_DRAFT.md`). This file is committed with `d14s3_run.py` and `d14s3_analyze.py`
before any Stage 3 computation. Steps 3c (fresh-seed rehearsal), 3d (G1 pre-registration) and 3e (scored run) are not
approved here.

**Scope (`FACT`):** UNSCORED, reported only.
- M5 stays NOT PASSED. Nothing is selected, and the setting is not adopted for G1.
- Stage 3 writes only under `experiments/D14_noslip_rest_rehearsal/`.
- Seeds come from ER7's committed Option A list (16000–16655); 17000–17999 and 10000–10999 stay untouched.
- Harness: the Stage 2 harness unchanged (`d14s2_run.install_logged_trial`, `er9g_run.run_one`, `d13_run.with_noslip`),
  with the NoSlip iteration count as a parameter.

## 1. Step 3a — model re-checks (fixed)
1. **Composite checks with NoSlip.** `er9g_composite_checks.v4`, `v5` and `v6` for L0, PG8 and PG20, with every model
   they build given `noslip_iterations` 10 (a wrapper around `d8_1b_checks.build` and `build_r_hinge_model`).
   - Pass criteria are the committed ones: V4 relative net force and torque < 1e-9; V5 energy drift ≤ 1 % of the
     energy exchanged; V6 exact.
   - The committed frozen values for PG8 and PG20 (`ER9 .../static/composite_checks.json`) are reported beside them.
2. **Reproduction of Stage 2.** E1-2 `U_s16100` is rerun at NoSlip 10 for each arm. Each must equal its committed
   Stage 2 record exactly, outside run metadata and the logging block. This also shows determinism at NoSlip.
3. **Convergence (reported only).** The same three trials at `noslip_iterations` 20. Reported: per-move turn error,
   non-target drift, peak turner torque and pass flag, against NoSlip 10.

**3a passes** if items 1 and 2 pass. If 3a fails, Stage 3 stops and reports to the user.

## 2. Step 3b — the full-rehearsal remainder (fixed)
- **Trials:** E1-3 (22), E1-4 (40), E1-6a (6), E1-6b (6), E1-6c (8) and E1-6t (16) from ER7's list, which is 98 per
  arm. Arms: L0, PG8 and PG20 (294 trials), at `noslip_iterations` 10, through the Stage 2 path. Per-step solver
  logging is on for all trials; the E1-2 series logging is not used.
- **Gate:** the first trial of each of the six sub-experiments for **L0** at the frozen setting, with the logging
  installed (6 trials). Each must equal ER7's committed L0 record exactly (GS1's comparison). PG8 and PG20 have no
  committed frozen records for these sub-experiments, so their harness rests on GS1/GS2 and the Stage 2 gate.
  If the gate fails, Stage 3b stops.
- **Cost stop:** 20 h projected, checked after the gate. Each arm's ratio is the median, over its Stage 2 trials, of
  (Stage 2 NoSlip wall / ER7 L0 frozen wall, same trial ID), applied to ER7 L0's frozen wall times.
- **Pause rule:** as Stage 2. The first abort, numerical failure or harness exception starts nothing new. Trials in
  flight finish, and the run pauses for the user. A harness-proof error stops at once.
- **Workers:** 4, or fewer if less than 2 GB of memory would remain free.

## 3. Signals: Part G's G.9, over the full 204 trials per arm at NoSlip (fixed)
The 204 trials are assembled from:
- E1-1: D14 Stage 1 (20 rests);
- E1-2, E1-5 and E1-5s: Stage 2 (86);
- the rest: Stage 3b (98).

**E1-1's pass flag** is computed from the Stage 1 record with the scored E1-1 criteria (`scored.THRESHOLDS`):
- integrity, not aborted, `t0_solved` and `final_solved`;
- the 0–10 s rest rotation ≤ 0.5°;
- penetration ≤ 0.5 mm;
- `radial_offset_mm_t0` ≤ 0.5 mm.

The radial-pop criterion does not apply under B1, which has no radial joint (`radial_preload` 0); this is disclosed.

**The signals (G.9, unchanged):**
1. 0 / 20 E1-1 slip events (D11) and every rest ≤ 0.5°. This is Stage 1's result.
2. M5's Option A rule over the 204 trials (`er7_analyze.option_a`): every row complete and every trial passing, plus
   E1-6m ⟨P⟩ (`e16m_P_ok` on every move of E1-2, E1-3 and E1-4).
   - Pass flags for PG8 and PG20 are the Part G verdict at D_val 12° (`pass_g`).
   - L0 uses M4's flag.
   - Abuse trials (E1-6b, E1-6c, E1-6t) are labelled when out of regime, not failed (G.4 rule 3).
3. No operational trial out of regime (G.4) for PG8 and PG20. L0 is reported with legacy statistics.

**Reading (G.9's, fixed):**
- **All three signals met, no move at the 1 N·m clip:** "meets the rehearsal signals", not a candidate. It goes to
  the user with what it still lacks: fit, torque against the realism reference, fresh seeds, E1-7, the composite
  review and the lateral-offset disclosure.
- **Met, with moves at the clip:** reported, and the user decides.
- **Missed:** the negative result is kept and reported.

**Reported only:**
- E1-2, E1-3 and E1-4 turner torque per move (`er9g_run.turner_stats`);
- moves at the clip;
- abuse trials labelled out of regime;
- the largest solver iteration count;
- for L0, the pass flags of the 98 trials against ER7's frozen records (flips).

**Predictions, written before any run (`INFERENCE`):**
- 3a passes.
- All three arms meet the G.9 signals.
- E1-4, the long sequences, is the most likely place for a failure. If one appears, the most likely kind is
  non-target drift accumulating over moves, for L0.

## 4. Limits (fixed)
As Stage 2:
- rehearsal seeds, used for every earlier choice;
- a post-hoc setting;
- NoSlip is an ad-hoc pass;
- physical credibility is unverified.

PG8 and PG20 have no frozen-setting records for E1-3, E1-4 and E1-6, so no paired comparison is possible for them.
Changes after the first computation are recorded as deviations.
