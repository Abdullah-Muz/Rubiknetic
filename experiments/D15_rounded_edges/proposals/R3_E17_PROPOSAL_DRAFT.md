# D15 R3: E1-7 sensitivity rehearsal of L0 at R 2.5 mm (PROPOSAL DRAFT, not approved)

**Status.** DRAFT, written 2026-11-25 under P-83 ("approved": L0 as working candidate, PG8 backup; draft the E1-7
rehearsal). Nothing here is fixed. No code is written and nothing is computed until the user approves this draft and
settles D1–D4. The protocol and its code are then committed before any computation, as for R1 and R2.

## 1. Why (`INFERENCE`)
- E1-7 is part of every G1 battery. G1 needs it "completed and published" (M5 pre-registration §5), but it is
  **reported, not pass/fail**: a setting whose small change flips a sequence's outcome is recorded as a fragility
  (`docs/research/PHASE_1_2_VALIDATION_EXPERIMENTS.md`, E1-7).
- **It has never been run on the current mechanism or harness.** M5's E1-7 ran through M5's own runner, with the
  chamfer and the default NoSlip. Everything since (ER7 → ER9 Part G → D14 → D15) ran only the 204-trial Option A
  list.
- A rehearsal therefore does two things before the scored run:
  1. It proves the E1-7 path works through the D15 harness, so the one-shot scored run doesn't fail on plumbing.
  2. It shows the fragilities early. M5 had three: a 0.75 ms timestep (both sequences), a 1.0 mm chamfer (6-move)
     and no magnets (6-move). We would see whether rounded edges and NoSlip 10 remove or move them.

## 2. What would run
- **Mechanism (the P-83 working candidate):**
  - L0: M5's 48 corner–edge magnets, 4×2 mm N35;
  - rounded edges at R 2.5 mm (`r1_run.install_edge`);
  - piece gap 0.05 mm, face gap 0.85 mm;
  - NoSlip 10, applied as in D14 Stage 3 and D15 R2.
- **Sequences:** M5's two E1-7 sequences, `6move` (U U′ R R′ F F′) and `sexy6`.
- **Seed:** **16000** for every trial. This is M5's E1-7 seed (10000) under the rehearsal mapping (+6000) used by
  ER7, D14 and D15. Seeds 17000–17999 stay untouched for the scored run.
- **Pass flag:** M4's flag (`rec["pass"]`), as L0 was judged in R2.

**Factors.** These are M5's E1-7 factors and bands, with the changes in bold:

| Factor | Values (nominal in *italics*) | Change from M5 |
|---|---|---|
| timestep | 0.25 / *0.5* / 0.75 ms | — |
| solver iterations | 50 / *100* / 200 | — |
| cubie friction μ | 0.1 / *0.2* / 0.5 / 1.0 | — |
| joint frictionloss | 5e-5 / *5e-4* / 5e-3 | — |
| **edge radius** | **D1: 1.8 / *2.5* / 3.6 mm** | **replaces M5's chamfer factor (1.0 / 1.4 / 2.0 mm)**; the chamfer is not used with rounded edges |
| piece gap | 0.025 / *0.05* / 0.1 mm | — |
| face gap | 0.35 / *0.85* / 1.35 mm | — |
| grip force | 10 / 30 / 50 N (no nominal; randomised 10–20 N) | — |
| initial misalignment max | 0 / *1* / 2 / 5° | — |
| magnet configuration | none / 3×1.5 N35 / 4×1.5 N35 / *4×2 N35* / 4×2 N52 | — (4×1.5 N35 failed V3 for M5; it stays "not run" for the same reason unless its V3 record has changed) |
| magnet strength scale | 0.67 / *1.0* | — |
| **NoSlip iterations** | **D2: 5 / *10* / 20** (+ 0 as a reference arm, reported separately) | **new**: NoSlip 10 is a post-hoc setting (P-73), so its band must be shown |

- **Size:** 29 settings × 2 sequences = 58 trials, plus 2 for the NoSlip 0 reference arm. 2 trials are expected not
  to run (4×1.5 N35, V3).
- **D3 (rests):** E1-7 by definition repeats only sequences. But M5's one scored failure was a rest, and NoSlip acts
  mainly at rest. **Proposed:** add one 60 s rest (seed 16000, D14 Stage 1's steps) for every non-nominal setting of
  timestep, iterations, cubie friction, edge radius, piece gap, magnet scale and NoSlip, plus nominal. That is 15
  rests, reported only, judged by D14's `e11_pass` and D11's slip detector.
- **Cost (`INFERENCE`, from R2's L0 wall times):** sexy6 about 350 s, 6-move about 120 s, rests about 310 s.
  - Sequences: about 4 CPU-hours.
  - Rests: about 1.3 CPU-hours.
  - Wall time: **about 1 h on 6 workers**.
  - Cost stop: 3 h wall time. The run starts only with 6 workers, and WSL is kept free of other jobs (lesson from
    P-82 (b)).

## 3. Before any computation (code and static checks, committed with the protocol)
1. **Static checks for the two new radii** (only if D1 adds radii other than 1.4 / 2.5): `r0_magnet_fit.py`, where
   every piece magnet must keep the 0.4 mm wall, and `r0_composite.py` V4–V6. A radius that fails is reported and its
   arm is "not run", with the reason.
2. **Runner `r3_run.py`:**
   - It builds the list from M4's `e17_trials` with M5's re-centred bands. The chamfer factor is replaced by an
     `edge_radius` factor that sets the job's radius, and a `noslip_iterations` factor is added through D14 Stage
     3's config.
   - It reuses R2's structure: resumable; pause on the first abort or harness error; proof errors stop the run.
3. **Proof checks on every record.** Each factor value must appear in the record: params, compiled options or
   magnet params. These cover timestep, iterations, friction, frictionloss, `edge_profile` / `edge_radius`, piece
   gap (cubies and magnet layout), face gap and wall, grip, misalignment, magnet configuration and scale, and
   `noslip_iterations`. A missing or wrong value is a proof error. This guards against a factor that silently does
   nothing in the newer harness.
4. **Gate:** E1-2 `U_s16100` at R 2.5 mm must equal R1's record exactly (as R2's gate).
5. **Smoke test (unscored, seeds 11100–11199, outside every range):** one short trial per factor value, checked by
   the proof checks only. Its records are kept apart and not analysed.
6. **Tests:** the job list (size, unique IDs, seed 16000, nominal and bands), the proof-check rule (positive and
   negative), and the analysis on synthetic records.

## 4. Signals and reading (fixed in the protocol before computation)
- **Signal A:** nominal passes both sequences (and its rest, if D3 is adopted).
- **Signal B:** within the declared bands, no setting flips a sequence (or a rest, if D3) from the nominal outcome.
- Every flip is listed as a **fragility**, with its first failing move, error, tilt, penetration and turner torque.
- Side-by-side with M5's E1-7 table (`experiments/E5_scored_m5/RESULTS.md`). Same factors, different mechanism;
  reported only.
- **Reading:**
  - A and B met: "E1-7 rehearsal clean". The scored battery can include E1-7 as M5 did.
  - A met, B not: the fragilities are reported. The user decides whether to pre-register with them disclosed, as M5
    did with its three, or to investigate first.
  - A not met: the run stops at the first trouble (pause rule), and the result goes to the user.
- **Reported only:** turner torque per move and moves at the 1 N·m clip; largest drift, penetration and solver
  iterations; the NoSlip 0 reference arm; wall times.
- **Predictions (to be written into the protocol before computation; `INFERENCE`):**
  - nominal passes;
  - the 0.75 ms timestep may still fail (it is a step-size effect that rounded edges need not change);
  - the small-radius arm (1.8 mm) passes, since the catch came from the chamfer bevel;
  - "no magnets" still fails at least one sequence (M5, ER7).

## 5. Decisions for the user
| # | Question | Recommendation | Alternative |
|---|---|---|---|
| **D1** | Edge-radius band | **1.8 / 2.5 / 3.6 mm**: M1's relative chamfer rule (1.0 / 1.4 / 2.0 = 0.71× / 1× / 1.43×) applied to 2.5 mm, as M5 re-centred the gap band by a relative rule (P-34). Needs the two static checks in §3.1. | 1.4 / 2.5 / 3.5 mm. 1.4 already has R0 checks and R1 screen records; 3.5 needs the checks. |
| **D2** | NoSlip band | **5 / 10 / 20**, plus 0 as a reference arm reported separately. 0 shows whether NoSlip is load-bearing in sequences, not only at rest. | 5 / 10 / 20 only. |
| **D3** | Add rests | **Yes:** 15 one-seed 60 s rests (about +1.3 CPU-h), reported only. | Sequences only, as M5's E1-7. |
| **D4** | PG8 (backup arm) | **Not now.** Run PG8's E1-7 only if L0 is dropped. Its magnet factors would also need defining for the core pairs. | Run PG8 in the same batch (about double the cost). |

## 6. Limits
- These are rehearsal seeds (one seed per setting). It is a sensitivity screen, not a statistical estimate.
- Rounded edges and NoSlip 10 remain post-hoc settings. Turning-torque realism is uncalibrated (P-83 (2)).
- Nothing here is scored or selects for G1. M5 stays NOT PASSED.
