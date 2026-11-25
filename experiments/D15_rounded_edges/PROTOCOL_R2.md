# D15 R2 — full rehearsal of rounded edges at R 2.5 mm (PROTOCOL, fixed before any computation)

**Status.** Approved by the user on 2026-11-24 (P-81, "i approve your recommendations"). This file is committed with
`r2_run.py`, `r2_analyze.py` and their tests before any R2 computation.

**Scope (`FACT`).** UNSCORED, reported only.
- Nothing is selected for G1. M5 stays NOT PASSED.
- R2 writes only under `experiments/D15_rounded_edges/results/r2/`.
- Seeds come from ER7's Option A list (16000–16655), as D14 used them. 19000–19655, 17000–17999 and 10000–10999 stay
  untouched.

## 1. What runs
- **Geometry:** `edge_profile = "rounded"`, `edge_radius` 2.5 mm (R1's selection, P-80), applied as in R1
  (`r1_run.install_edge`). Gap 0.05 mm; NoSlip iterations 10.
- **Arms:** L0, PG8, PG20; D_val 12° for PG8 and PG20.

| Experiment | Trials per arm | How |
|---|---|---|
| **Gate** | 1 (3 in all) | E1-2 `U_s16100` at R 2.5 mm through R1's worker. It must equal R1's committed record exactly (`er9g_run.gs_diff` after stripping the logging blocks). If any arm differs, R2 stops. |
| E1-1 | 20 rests of **60 s**, seeds 16000–16019 | R1's rest worker with the rest length set to 60 s: D14 Stage 1's steps (warm-up, magnet-system reset, `d13_rest`, D13 variant V2). |
| E1-3, E1-4, E1-6a, E1-6b, E1-6c, E1-6t | 22, 40, 6, 6, 8, 16 = 98 | D14 Stage 3b's job list (`d14s3_run.stage3b_jobs`) through R1's sequence worker. |
| E1-2, E1-5, E1-5s | 86 | **Reused** from R1's R 2.5 records (`results/r1/R25/<arm>/`), identical configuration, listed with sha256 in the analysis. Not rerun. |

- **Total run:** 3 gate trials + 3 × (20 + 98) = 357 trials.
- **Order:** gate first; then longest first (E1-4, then rests, E1-3, E1-6t, E1-6c, E1-6b, E1-6a), PG20 before PG8 before
  L0.
- **Workers:** 6, or fewer if less than 2 GB of memory would remain free. If the start finds fewer than 6 workers
  possible, R2 does not start and reports. Other jobs are to be kept off WSL (P-81).
- **Pause rule (as D14):**
  - The first abort, numerical failure or harness exception starts nothing new. Trials in flight finish, and the run
    pauses for the user.
  - A proof error stops the run at once. Proof errors are R1's: D14's checks plus `edge_profile` and `edge_radius` in
    params, and NoSlip 10 on rests.
- **Wall-clock stop:** no new trial starts more than 12 h after the start.
- **Resumable:** a trial with a record is not rerun.

## 2. Signals: Part G's G.9 over the 204 trials per arm (fixed, as D14 Stage 3 §3)

**Assembly of the 204 trials:**
- E1-1: R2's 20 rests (60 s).
- E1-2, E1-5, E1-5s: R1's R 2.5 records (86).
- The rest: R2 (98).

**E1-1's pass flag** is D14's `e11_pass` on the rest record: integrity, not aborted, solved at start and end,
0–10 s rest rotation ≤ 0.5°, penetration ≤ 0.5 mm, radial offset ≤ 0.5 mm.

**The signals:**
1. All 20 rests are present, with **0 slip events over the full 60 s** (D11's detector), every 0–10 s rest ≤ 0.5°,
   integrity, and for PG8 / PG20 no rest out of regime. This is D14 Stage 1's signal.
2. M5's Option A rule over the 204 trials: every ER7 row complete and every trial passing, plus E1-6m ⟨P⟩
   (`e16m_P_ok` on every move of E1-2, E1-3 and E1-4).
   - PG8 and PG20 use Part G's `pass_g` at D_val 12°; L0 uses M4's flag.
   - Abuse trials (E1-6b, E1-6c, E1-6t) are labelled when out of regime, not failed (G.4 rule 3).
3. No operational trial out of regime (G.4) for PG8 and PG20. L0 is reported with legacy statistics.

**Reading (G.9's, fixed):**
- **All three signals met, and no move at the 1 N·m clip:** "meets the rehearsal signals", not a candidate. It goes to
  the user with what it still lacks: fresh seeds (Stage 3c), turning torque against the realism reference, E1-7, the
  composite review, the lateral-offset disclosure, and the physical credibility of the rounded edge.
- **Met, with moves at the clip:** reported, and the user decides.
- **Missed:** the negative result is kept and reported.

**Reported only:**
- turner torque per move for E1-2, E1-3 and E1-4 (`turner_stats`), and moves at the clip;
- abuse trials labelled out of regime;
- the largest non-target drift and solver iteration count, and steps at the iteration limit;
- for each arm, E1-3 / E1-4 / E1-6 pass flags against the chamfer where chamfer records exist (D14 Stage 3b: PG20
  E1-4, 26 trials; ER7's L0 frozen records);
- wall times.

**Predictions, written before any run (`INFERENCE`):**
- The gate passes.
- All three arms meet the G.9 signals with no move at the clip.
- PG20 E1-4 `scr20inv_s16400`, which jammed on the chamfer, passes.
- The largest E1-3 / E1-4 turner torque stays below 0.5 N·m in every arm.
- If something fails, the most likely place is E1-6 (abuse) or a 60 s rest slip event.

## 3. Limits
- These are rehearsal seeds, used for every earlier choice.
- Rounded edges were chosen after the chamfer failed, so this is a post-hoc setting, as NoSlip 10 is.
- Physical credibility of the rounded edge and of the turning torque is unverified.
- E1-7 is not run.
- Changes after the first computation are recorded as deviations.
