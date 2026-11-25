# D15 R3 — E1-7 sensitivity rehearsal of L0 at R 2.5 mm (PROTOCOL, fixed before any computation)

**Status.** Approved by the user on 2026-11-25 (P-84: the recommended D1–D4 of
`proposals/R3_E17_PROPOSAL_DRAFT.md`). This file is committed with `r3_run.py`, `r3_analyze.py`, their tests, the
static pre-check (`r3_static.json`) and the smoke-test records before any R3 trial.

**Scope (`FACT`).** UNSCORED, reported only.
- Nothing is selected for G1. M5 stays NOT PASSED.
- R3 writes only under `results/r3/` (run) and `results/r3_smoke/` (smoke).
- The run uses seed **16000** only, which is M5's E1-7 seed 10000 under ER7's +6000 mapping. The smoke test uses
  16901–16945 and 16999, from the unused block 16900–16999 of ER7's rehearsal range.
- 10000–10999, 17000–17999 and 19000–19655 stay untouched.

## 1. What runs
**Mechanism (P-83 working candidate).**
- L0: M5's 48 corner–edge magnets, 4×2 mm N35.
- Rounded edges at R 2.5 mm (`r1_run.install_edge`).
- Piece gap 0.05 mm, face gap 0.85 mm.
- NoSlip 10, applied by wrapping `scored.build_m1_xml` (D14 Stage 3's method).

**Sequences: M5's E1-7 list.**
- Each setting runs two sequences, `6move` (U U′ R R′ F F′) and `sexy6`.
- The list is built by M5's own builder (`E5_scored_m5/run.py: build_m5_jobs`) under ER7's seed mapping. It gives
  54 jobs, all on seed 16000, with these changes:
  - M5's two chamfer settings (1.0 and 2.0 mm) are dropped. **Edge radius 1.8 and 3.6 mm** (P-84 D1) replace them.
    The static pre-check (`r3_static.json`, `d77d0ab`) shows both radii keep the 0.4 mm magnet wall and pass V4–V6.
  - **NoSlip 5 and 20** are added (P-84 D2).
  - **NoSlip 0** is added as a reference arm. It is outside the band and reported separately.
- That gives 60 jobs.
- **M5's V3 rule** (`R.classify`) leaves 4×1.5 N35 "not run: failed V3" (2 jobs), as in M5.
- **58 sequence trials run.**

**Path (`FACT`, found while writing the code).**
- The sequences run through ER7's L0 path: `er7_run.run_one` → M5 `run_job` → M4 `run_trial`. This is the path M5's
  own E1-7 used, and it applies every E1-7 setting natively.
- They do **not** use ER9 Part G's path (`er9g_run.run_one`), which R1 and R2 used. Its L0 installer
  (`er9g_layouts.install_er7`) ignores the job's magnet parameters, always building 4×2 N35, and refuses
  "no magnets". Through it, the magnet-type, strength-scale and face-gap settings would have no effect.
- Gate 1 and the smoke test's path-equivalence check show the two paths give identical records for the nominal
  mechanism.

**Rests (P-84 D3).**
- 15 rests of 60 s on seed 16000, one each for:
  - nominal;
  - timestep 0.25 and 0.75 ms;
  - iterations 50 and 200;
  - cubie friction μ 0.1, 0.5 and 1.0;
  - edge radius 1.8 and 3.6 mm;
  - piece gap 0.025 and 0.1 mm;
  - magnet scale 0.67;
  - NoSlip 5 and 20.
- Each follows R1/R2's rest steps: a 10 s warm-up E1-1 through ER7's L0 path, a magnet-system reset, then `d13_rest`
  with D13 variant V2. The setting's overrides go to both, and the NoSlip count to `d13_rest`.

**Gates (in order; a failed gate stops R3).**
1. **Gate 1:** E1-2 `U_s16100` (L0, R 2.5 mm, NoSlip 10) through R3's sequence path must equal R1's committed record
   (ER9 path) exactly. The comparison uses `er9g_run.gs_diff` after stripping the logging blocks, as R2's gate did.
2. **Gate 2:** R3's nominal 60 s rest must equal R2's committed L0 `rest_s16000` (record block, `gs_diff`; seed, rest
   length, variant and capture equal).

**Proof checks (every record; a failure stops the run).** The record must show the job's value for each of these:
- edge profile and radius;
- timestep, iterations, cubie friction, joint frictionloss and piece gap (`params`);
- the compiled NoSlip count, timestep and iterations;
- the magnet parameters: diameter, length, grade, scale and wall, which carries the face-gap setting. "No magnets"
  must have none;
- the magnet layout gap;
- grip force (grip settings);
- misalignment within the setting's maximum (exactly 0 for 0°);
- seed;
- rest length (rests).

**Pause rule.**
- Only a harness exception pauses the run (no new trial starts, and trials in flight finish).
- An abort, numerical failure or failed criterion under a setting is an E1-7 outcome, a possible fragility, not a
  pause. M1's E1-7 included a `BADQVEL` at μ 1.0.

**Workers and stops.**
- 6 workers. If fewer than 6 are possible at the start, R3 does not start and reports.
- WSL is kept free of other jobs (P-82 (b)).
- No new trial starts more than 3 h after the start.
- The run is resumable: a trial with a record is not rerun.

**Order.** Gate 1, gate 2 (the nominal rest), the sexy6 sequences, the 6move sequences, then the other rests.

## 2. Smoke test (before this protocol was committed; unscored)
- One short trial (move U) per sequence setting on seeds 16901–16930, one seed per setting. 4×1.5 N35's seed is
  assigned, but the V3 rule leaves that trial "not run".
- One 2 s rest per rest setting on 16931–16945. Each warm-up runs on its own smoke seed.
- The path-equivalence pair: E1-2 "U" on seed 16999 through R1's ER9 path and through R3's path. It must give
  `gs_diff` = 0.
- **Proof checks only.** The smoke records (`results/r3_smoke/`) are not analysed and carry no result. Their outcome
  is recorded in §5 below.

## 3. Signals and reading (fixed)
- **Complete:** 58 sequence records, 15 rest records, and the "not run" set equal to the two 4×1.5 N35 jobs.
- **Signal A:**
  - nominal `6move` and `sexy6` pass (M4's flag `rec["pass"]`, as L0 in R2);
  - the nominal rest is "ok": D14's `e11_pass` (0–10 s rest ≤ 0.5°, integrity, penetration and radial offset) and 0
    slip events over 60 s (D11's detector).
- **Signal B:**
  - no in-band setting flips a sequence's outcome against nominal for the same sequence;
  - no rest setting flips the rest outcome against the nominal rest.
  - NoSlip 0 is outside the band.
- **Fragilities:** every flip is listed with its first failing move, largest turn error, drift, penetration and
  turner torque, and its fail reasons.
- **Reading:**
  - complete, A and B: "E1-7 rehearsal clean";
  - A but not B: "fragilities reported: the user decides";
  - not A: "nominal failed: result to the user";
  - not complete: "incomplete: result to the user".
- **Reported only:**
  - turner torque per trial and moves at the 1 N·m clip;
  - largest drift, penetration and solver iteration count, and steps at the iteration limit;
  - the NoSlip 0 reference;
  - M5's E1-7 pass flags side by side (same seed mapping, different mechanism);
  - wall times.

**Predictions (written before any R3 trial; `INFERENCE`):**
- Both gates pass.
- Nominal passes both sequences and its rest.
- The 0.75 ms timestep may still fail at least one sequence (M5 failed both). It is a step-size effect that rounded
  edges need not change.
- Edge radius 1.8 mm passes both sequences. The catch came from the chamfer's bevel, and R1 already passed at 1.4 mm.
- "No magnets" fails at least one sequence (M5, ER7).
- μ 1.0 passes. Rounded edges reduce the catch that friction amplified.
- If a rest flips, the most likely settings are the 0.75 ms timestep and NoSlip 5.

## 4. Limits
- One seed per setting: a sensitivity screen, not a statistical estimate.
- These are rehearsal seeds.
- Rounded edges and NoSlip 10 are post-hoc settings. Turning-torque realism is uncalibrated (P-83 (2)).
- Changes after the first R3 computation are recorded as deviations.

## 5. Smoke-test outcome (`FACT`, 2026-11-25, before this file was committed)
- **Trials:** 44 / 44 ran (29 sequence settings, 15 rests). 4×1.5 N35 was "not run" by the V3 rule. 0 proof
  errors, 0 harness exceptions. Every setting's value appeared in its record. Log: `results/r3_smoke/r3_run_log.txt`.
- **Path equivalence (seed 16999):**
  - The first attempt reported 9 differences, all tuple against list in `params`. One record was compared straight
    from memory and the other after a JSON round trip. That is a check artifact, not a physics difference.
  - The check was corrected to compare both records as saved on disk (`_as_saved`), as gate 1 and gate 2 do.
  - Rerun: **0 differences** (`results/r3_smoke/equivalence.json`).
- No smoke record is analysed. A WSL job of another project (about 3 cores) was running during the smoke test. It
  affects wall time only.
