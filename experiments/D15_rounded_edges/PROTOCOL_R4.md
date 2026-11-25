# D15 R4 — fresh-seed rehearsal of M7's Option A battery (PROTOCOL, fixed before any computation)

**Status.** Approved by the user on 2026-11-25 (P-86 Q3: "Yes, ~2 h run", a fresh-seed unscored rehearsal of
Option A on 19000–19655 before the M7 pre-registration is fixed). This file is committed with `r4_run.py`,
`r4_analyze.py`, their tests and the smoke records before any R4 trial.

**Scope (`FACT`).** UNSCORED, reported only.
- Nothing is selected for G1, and nothing here is M7's verdict. M5 stays NOT PASSED.
- R4 writes only under `results/r4/` (run) and `results/r4_smoke/` (smoke).
- **Seeds: 19000–19655** (M5's scored seeds + 9000). They have never been simulated (the M7 draft §6.4 scan covered
  `experiments/`). The gate uses the rehearsal seeds 16000–16655, and the smoke test uses 16950–16959.
- The runner refuses 10000–10999 and 17000–17999 in every mode.
- **Purpose:** M7's configuration on seeds that informed no choice, to see the tails before the one-shot scored run
  (M5 rehearsed 204/204, then failed its scored run on one trial). Its result is reported in the M7 text before that
  text is fixed.
- **No R4 result may be used to change M7's configuration or thresholds.** If R4 misses a signal, the negative result
  is kept and the user decides what follows.

## 1. What runs
**Configuration:** M7 as drafted (`PHASE_1_M7_PREREGISTRATION.md` §1):
- L0: M5's 48 × 4×2 mm N35 magnets;
- rounded edges at R 2.5 mm;
- NoSlip 10;
- piece gap 0.05 mm, face gap 0.85 mm;
- M1's rig.

**Trials:** M5's 204-trial Option A list, built by M5's builder (`build_m5_jobs`) with every seed + 9000. ER7 used
+6000 the same way.
- E1-4's 20 scramble+inverse sequences are drawn from the new seeds, so they are new (test).
- E1-7 and E1-6n are not run.

| Sub-exp. | Trials | How it runs |
|---|---|---|
| E1-1 | 20 (seeds 19000–19019) | R2/R3's 60 s instrumented rest: a 10 s warm-up E1-1 through ER7's L0 path, a magnet-system reset, then `d13_rest` (D13 V2, NoSlip 10) (`r3_run.rest_worker`) |
| E1-2 … E1-6t | 184 | R3's sequence worker: ER7's L0 path (`er7_run.run_one` → M5 `run_job`) with the edge and NoSlip installs (`r3_run.seq_worker`) |

**Gate (before any 19xxx trial; a failure stops R4).**
- The first trial of each of the 10 sub-experiments, built with the rehearsal mapping (+6000), must reproduce R1's
  or R2's committed L0 R25 record exactly:
  - E1-2, E1-5 and E1-5s from R1;
  - E1-1 (60 s), E1-3, E1-4, E1-6a/b/c and E1-6t from R2.
- The comparison is `gs_diff` after stripping the logging blocks. For rests, it compares the record block plus seed,
  rest length, variant and capture.
- This extends R3's gates, which covered only E1-2 and the rest, to every trial kind.

**Proof checks (every record; a failure stops the run).** R3's checks:
- edge profile and radius;
- timestep, iterations, cubie friction, joint frictionloss and gap;
- the compiled NoSlip count;
- M5's nominal magnet parameters and the layout gap;
- seed;
- rest length.

The misalignment check applies to E1-2 to E1-4 only, since E1-5 sets its own offset.

**Pause, workers, stops.**
- Only a harness exception pauses the run.
- An abort, numerical failure or failed criterion is a result.
- 6 workers. If fewer are possible at the start, R4 does not start.
- WSL is free of other jobs.
- No new trial starts more than 6 h after the start.
- The run is resumable.

## 2. Signals and reading (fixed; mirrors what M7's scored verdict would judge)
**Complete:** 20 rests on 19000–19019, plus the expected counts of every sub-experiment (E1-2 24, E1-3 22, E1-4 40,
E1-5 42, E1-5s 20, E1-6a 6, E1-6b 6, E1-6c 8, E1-6t 16).

**Signal 1 (rests):**
- all 20 present;
- 0 D11 slip events over the full 60 s (P-86 Q4);
- every 0–10 s rest ≤ 0.5°;
- integrity;
- rest length 60 s.

These are R2's signal-1 rules (`r2_analyze.signal1`).

**Signal 2 (Option A with the slip rule):**
- every sub-experiment is complete and every trial passes:
  - E1-1: D14's `e11_pass` and 0 slip events;
  - every other sub-experiment: L0's M4 flag `rec["pass"]`, as in R2;
- E1-6m ⟨P⟩ (`e16m_P_ok`) holds on every move of E1-2, E1-3 and E1-4.

**Reading:**
- both signals met: "meets the rehearsal signals on fresh seeds (not a candidate)";
- not complete: "incomplete: result to the user";
- otherwise: "signal(s) missed: negative result kept; the user decides".

**Reported only:**
- turner torque per move for E1-2 to E1-4 (median, max, moves at the clip);
- margins (largest 0–10 s rest rotation, non-target drift, penetration, |turn error|) beside R1 + R2's L0 rehearsal
  maxima;
- the trouble list;
- rest wall times.

**Predictions (`INFERENCE`, written before any 19xxx trial):**
- The gate passes.
- Both signals are met, with no move at the clip.
- The largest drift and penetration stay below the limits, but may exceed the rehearsal maxima (0.73°, 0.29 mm),
  because tails grow with new seeds, as M5's rest did (0.290° in rehearsal, 0.560° scored).
- If a trial fails, the most likely criterion is non-target drift (closest margin: 0.73° against 1.0°).

## 3. Smoke test (before this file was committed; unscored; proof checks only)
- One trial of each of the 10 sub-experiments, on seeds 16950–16959. Turn trials ran one move, and the rest ran 2 s.
- **10 / 10 ran, with 0 proof errors and 0 harness exceptions** (`results/r4_smoke/r4_run_log.txt`).
- It is not analysed.

## 4. Limits
- These are not the scored seeds: R4 is evidence about the tails, not M7's verdict.
- Its result is disclosed in the M7 text before that text is fixed. It may inform the stop rules and the disclosure,
  never the configuration or thresholds.
- Changes after the first R4 computation are recorded as deviations.
