# D15 R1 — screen of rounded piece edges (PROTOCOL, fixed before any computation)

**Status.** R1 was approved by the user on 2026-11-24 (P-79, "fully approved").
- The rest length is 10 s: the user chose "10 s rests (Recommended)" on 2026-11-24.
- This file is committed with `r1_run.py`, `r1_analyze.py` and their tests before any R1 computation.
- **R2 is not approved here.**

**Scope (`FACT`).** UNSCORED, reported only.
- Nothing is adopted beyond P-79's decision. M5 stays NOT PASSED.
- R1 writes only under `experiments/D15_rounded_edges/results/r1/`.
- Seeds come from ER7's Option A list, as D14 Stage 1 and 2 used them. 19000–19655, 17000–17999 and 10000–10999 stay
  untouched.

## 1. What runs
- **Geometry.** `M1Params.edge_profile = "rounded"`, at `edge_radius` 2.5 mm (tag R25) and 1.4 mm (tag R14). It is
  applied in each worker by a subclass of `scored.Trial` that replaces the trial's params with the edge fields set, so
  every trial kind builds the rounded model and records it in `params`.
- **Gap and NoSlip.** Gap 0.05 mm, as every trial sets it. NoSlip iterations 10, as D14.
- **Arms.** L0, PG8 and PG20, with D_val 12° for PG8 and PG20 (as D14).

| Experiment | Trials per arm per radius | How |
|---|---|---|
| E1-1 | 20 rests, seeds 16000–16019 | D14 Stage 1's worker steps (`d14_run.run_job`: warm-up, magnet-system reset, `d13_rest`), with `duration_s` **10 s** instead of 60 s. D13 variant V2 applies NoSlip 10 to the rest. The event capture's summary is recorded; the capture arrays are not written. |
| E1-2 | 24 | D14 Stage 3's worker (`d14s3_run.worker`, NoSlip 10, Stage 2 logging), with the Stage 2 job list |
| E1-5 | 42 | same |
| E1-5s | 20 | same |

- **Total:** 106 trials × 3 arms × 2 radii = **636 trials**. R25 runs first; rests run first within a radius.
- **Workers:** 6, or fewer if less than 2 GB of memory would remain free.
- **Pause rule (as D14).**
  - The first abort, numerical failure or harness exception starts nothing new. Trials in flight finish, and the run
    pauses for the user.
  - A proof error stops the run at once. Proof errors are D14's checks plus: params must state
    `edge_profile = "rounded"` and the radius under test.
- **Cost stop: 6 h projected.**
  - The projection is checked once 6 trials of each kind (rest, other) have finished.
  - It is the mean wall time per kind × the trials remaining of that kind / workers, plus the time elapsed.
- **Resumable.** A trial with a record is not rerun.

## 2. The screen and the selection (P-79's rule, fixed)

**A radius meets the screen if, for each of L0, PG8 and PG20, all of the following hold.**
1. All 106 trials are present.
2. **E1-1, every rest:** D14's `e11_pass` holds. That is: integrity, not aborted, solved at start and end, 0–10 s rest
   rotation ≤ 0.5°, penetration ≤ 0.5 mm, radial offset ≤ 0.5 mm. In addition, D11's slip-event detector finds no
   event, and for PG8 / PG20 the rest is not out of regime (Part G G.4).
3. **E1-2, E1-5 and E1-5s, every trial passes.** L0 uses M4's flag; PG8 and PG20 use Part G's `pass_g` at D_val 12°.
   For PG8 and PG20 no trial is out of regime (`oor_g` is False).
4. **No move reaches the 1 N·m clip** (`max_turner_torque_Nm` ≥ ER9's `CLIP_NM`). E1-5 and E1-5s records do not
   record turner torque, so this applies to the 72 E1-2 moves per arm. This is the same set D14 reported "at the clip"
   for. It is a clarification of P-79's wording, not a change.

**Selection.** Choose R 2.5 mm if it meets the screen; otherwise R 1.4 mm if it does; otherwise neither, and stop and
report.

**Reported only, no reading fixed in advance:**
- E1-2 turner torque statistics (`turner_stats`);
- E1-5 outcomes (completed / blocked / no net move), against D14 Stage 2's chamfer records;
- largest rest rotation and non-target drift;
- the largest solver iteration count;
- wall time per kind, against the chamfer records.

**Predictions, written before any run (`INFERENCE`).**
- Both radii meet the screen.
- E1-2 turner peaks fall to about the magnets' resistance plus the rig: about 0.3 N·m PG20, 0.2 L0.
- E1-5 completes more of the large-misalignment starts than the chamfer did. Blocking stays allowed.
- Rest rotation stays far inside 0.5°.

## 3. Limits
- These are rehearsal seeds, used for every earlier choice. The rests are 10 s; the 60 s rests are left to R2, for the
  chosen radius only.
- E1-3, E1-4, E1-6 and E1-7 are not in R1.
- NoSlip is an ad-hoc pass. Physical credibility of the rounded edge is unverified.
- Changes after the first computation are recorded as deviations.
