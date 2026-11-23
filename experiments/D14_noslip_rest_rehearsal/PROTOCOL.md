# D14 — Stage 1: 60 s rest rehearsal at `noslip_iterations` 10 (PROTOCOL, fixed before any run)

**Status:** approved by the user 2026-11-23 (P-73: "all approved"). P-73 approves the staged plan: Stage 1 (this file),
Stage 2 (the rest of the Part G probe at this setting, for arms that pass Stage 1) and Stage 3 (model re-validation and
a G1 pre-registration). Stages 2 and 3 each need the user's go after the previous stage's report. This file is
committed with `d14_run.py` and `d14_analyze.py` **before** the first D14 run.

**Scope (`FACT`):** UNSCORED, reported only.
- M5 stays NOT PASSED, and Part G's outcome stays as reported (no arm selected).
- D14 changes one simulation setting, `noslip_iterations` from 0 to 10, in the 60 s rest only. The setting was chosen
  after M5, Part G and D13, and this is disclosed. Nothing here adopts it for G1. Adoption needs Stage 3 and a new
  pre-registration with new seeds.
- D14 writes only under `experiments/D14_noslip_rest_rehearsal/`. It edits nothing under `src/`, the scored runners,
  ER7, ER9 or D13.
- Seeds 16000–16019 only (the Part G probe's E1-1 rehearsal seeds). 17000–17999 and 10000–10999 are untouched.

## 1. Background
`FACT`, from `experiments/D13_rest_slip_mechanism/SUMMARY.md` (`45a92f2`).
- With `noslip_iterations` 10 (D13 variant V2), none of the six committed slip cases had a fast slip event in 60 s.
  The 0–10 s rest rotation was 0.0014–0.0029°, and wall time was 1.14–1.26 × the frozen setting.
- `impratio` 100 delayed two of six events rather than removing them.
- Gravity contributes to the events, and their place.

**Why this setting** (`INFERENCE`, with its source): MuJoCo's documentation ("Slow slippage", `doc/modeling.rst` at
tag 4.0.1) describes slow slip under a persistent tangential load as an artifact of its regularized friction, and names
the NoSlip solver as the stronger remedy. A physical contact held inside its friction cone sticks.

**Open after D14:** D14 tests only rest. Turning, forgiveness and snap-back at this setting are Stage 2.

## 2. Question (fixed)
> At `noslip_iterations` 10, does each arm (L0, PG8, PG20) meet Part G's rest signal (signal 2) on all 20 E1-1
> rehearsal seeds?

## 3. Runs
- **Arms:**
  - **L0:** frozen M5's 48 4×2 N35 magnets, through ER7's own path.
  - **PG8 and PG20:** the Part G arms, grade N52, installed with `er9g_layouts.install_er7` and the class-stats
    system, as in the Part G probe.
- **Seeds:** 16000–16019 for every arm, which is 60 runs.
- **Trial:** D13's run path unchanged (`d13_run.d13_rest`, imported from the committed `d13_run.py`):
  1. the arm installation;
  2. ER7's 10 s scored-format rest trial at the frozen settings (a warm-up; recorded, not analysed);
  3. ER7's 60 s rest set-up;
  4. the instrumented 60 s rest with `noslip_iterations="10"` added to the trial model's `<option>` element, with
     D13's per-piece contact logging and event capture.

  This is exactly D13's variant V2, so the D14 runs that repeat a D13 V2 case can be compared exactly (the gate below).
- **Cost** (`ASSUMPTION`, from D13's V2 wall times with six workers: L0 about 470 s, PG8 about 820–870 s, PG20 about
  950–970 s per run): 20 × (466 + 845 + 960) s / 4 workers, about 3.2 hours.
- **Cost stop:** 6 hours projected, checked after the gate batch.
- **Memory:** four workers by default, because another job shares the machine. Workers are reduced if less than 2 GB
  would remain free. Runs killed for low memory are not restarted without the user's instruction.

## 4. Gate (fixed)
The runs that repeat a D13 V2 case run first:

| Arm | Seeds | D13 case |
|---|---|---|
| PG8 | 16000, 16003, 16011, 16016 | Q1, C1, C2, C3 |
| PG20 | 16000, 16013 | Q2, C4 |
| L0 | 16003, 16005 | C5, C6 |

Each must equal its D13 V2 record exactly: every `rot_deg` sample identical (maximum absolute difference 0.0°) and the
same 0–10 s rest rotation. If not, D14 stops and reports that alone.

## 5. Measures and signal (fixed)
Per run:
- **0–10 s rest rotation:** the frozen E1-1 metric applied to the first 10 s of the 60 s rest. Its largest absolute
  per-piece rotation about any face normal, at 25 ms samples, is the same metric as the scored 10 s rest trial; ER7's
  S4 showed the two are equal at the frozen settings.
- **Fast slip event:** D11's definition (≥ 0.2° within 200 ms), over 60 s, any piece (`d11_analyze.events`).
- **Validity (PG8, PG20):** Part G's per-class rule (G.4) on the 60 s rest's class stats, through
  `er9g_run.verdict("E1-1", [], class_stats, D_val)` with the arm's D_val (12°). The run is out of regime if
  `out_of_regime` is true. L0 is reported with M4's legacy magnet statistics only, as in Part G.
- **Integrity:** no aborted run and no numerical failure.

**Stage 1 signal, per arm** (Part G signal 2, unchanged, plus integrity and validity): all 20 runs complete, every
0–10 s rest rotation ≤ 0.5°, no seed with a fast slip event over 60 s, no aborted run or numerical failure, and (for
PG8 and PG20) no run out of regime.

**Reading** (fixed):
- An arm that meets the signal is a **candidate for Stage 2**. Stage 2 runs only on the user's go after this report.
- An arm that misses it is reported with its events and is not taken further at this setting without a new decision.
- Nothing here is a G1 result.

**Reported only:**
- the paired comparison with the committed frozen-setting records of the same seeds (Part G probe for PG8 and PG20,
  ER7 for L0): rest rotation, largest 200 ms change, and largest net drift;
- the largest solver iteration count;
- wall time;
- D13's per-piece creep and sliding distances.

**Predictions, written before any run (`INFERENCE`):**
- All three arms meet the signal, with 0–10 s rest rotations below 0.01°.
- The largest risk is an event in a seed not tested in D13. Under the frozen setting, the largest 200 ms change
  outside the D13 cases was 0.115° (L0, seed 16015).

## 6. Limits (fixed)
- Rest only. Turning effort, stalls, forgiveness and snap-back at this setting are not tested here (Stage 2).
- The setting was chosen after the failures it addresses. D14 can show that the setting removes the slips on these
  seeds. It cannot show that the setting is physically right: whether a physical cube creeps under these loads stays
  unverified.
- MuJoCo documents that NoSlip makes inverse dynamics ill-defined and can occasionally destabilize systems with many
  contacts. Integrity failures are reported, not excluded.
- Changes after the first run are recorded as deviations in the D14 summary.
