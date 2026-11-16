# Phase 1 (G1) Pre-registration — M4 magnetic contact cube (B1 + 48 magnets)

**Status:** `APPROVED 2026-11-15` (user: "fully approved", covering the whole draft, including the recommended option
(c) for §8 decision 1). **Not yet frozen for scoring.**
- Scored runs may start only after:
  - the §6 work is committed;
  - the E1-6c threshold has been set from R1 real-cube data and approved as an amendment;
  - the runner checks for a clean commit.
- No scored M4 trial exists.
- Thresholds may never be loosened after a failure.

**Basis:**
- P-16 (passive piece-to-piece forces), P-18 (D8-1b), P-22 (magnet model revision 2).
- The approved M1 pre-registration ([`PHASE_1_PREREGISTRATION.md`](PHASE_1_PREREGISTRATION.md)). Its structure,
  thresholds and integrity rules are reused unless stated.
- D8-1b stage 1 revision 2 ([`D8_alignment/README.md`](D8_alignment/README.md)).

**Unscored evidence** (`FACT`, stage 1 revision 2, seeds 5140–5145, 5160–5161, 5170–5171, 5201–5232):
- All five pre-declared feasibility signals met.
- 140/140 sequence moves matched the oracle.
- No error build-up (−0.002 to −0.003°/move).
- Snap from ≥ 3° to ≤ 0.48°.
- Turn error 0.23–0.43°; penetration ≤ 0.29 mm.
- Forgiveness completes to ±12°.
- Opposed torque and corner twist pass categorically, with twist about 40° at 5 N·m.
- 0 edit-audit violations; 0 numerical failures.

**Name.** "M4" is the next free mechanism label: M3 was the D3 prototype. M4 is M1's contact-only cube at rigid
radius (B1) plus the D8-1b magnets.

---

## 1. Frozen configuration (proposed)

| Group | Value |
|---|---|
| Cubies, rig, solver | M1 as frozen in M1 §1, with **`radial_preload = 0`**: rigid radius, no radial slide (B1, as also frozen for M2) |
| Magnets | 48 axial discs, **4 × 2 mm N35** (Br 1.19 T), 0.4 mm wall, face gap 1.0 mm. Classic layout: 3 per corner, 2 per edge, corner–edge head-to-tail. Magnet mass not added (disclosed, as in stage 1) |
| Force law | `experiments/D8_alignment/magnets.py` revision 2, moved into `src/` (§6): dipoles everywhere, with a tilt-aware exact near-field correction within 8 mm and a C2 far taper at 20–25 mm. It reads body poses only (P-16) and is injected through `mjcb_passive` |
| Validated range | Near-pair tilt ≤ the V3-validated tilt: 5° now, 7.5° if the V3 extension in §6 passes. Magnet forces are not validated beyond it |
| Turner | Default M1 rig (turn_kp 5, kv 0.2), as for M1 and as in stage 1 |
| Software | MuJoCo 4.0.1, Python 3.12, NumPy and SciPy from `uv.lock` |

## 2. Run-integrity rules

M1 rules 1–5 apply unchanged: clean commit, edit audit, numerical failure, observed-move oracle, no exclusions.

**NEW:**
1. The magnet callback is installed once per process and checked to read only `xpos` and `xmat` (a V6-style check
   at runner start). Its contribution goes only into `qfrc_passive`.
2. **Magnet validity, operational experiments** (E1-1 to E1-5, E1-6a): if the largest near-pair tilt in a trial
   exceeds the validated range, **the trial fails**. It is not excluded or rerun.
3. **Magnet validity, abuse experiments** (E1-6b, E1-6c): exceeding the validated range is logged and reported. It
   doesn't fail the trial by itself, but the magnet arm's result is labelled "magnet model outside validated range",
   and the no-magnet arm (§4) is the bound.
4. Scored seeds **6000–6999**: M1's experiment offsets shifted by +5000. They are disjoint from M1 (1000–1999), M2
   (2000–3999), the diagnostics (4302, 4401) and stage 1 (5100–5299).

## 3. What varies between trials

The same draws as M1: misalignment ±1° per face applied before t = 0 and logged, grip 10–20 N, 0.8–1.2 s per quarter
turn, and scrambles for E1-4.

## 4. Experiments and thresholds

M1's approved thresholds are kept:
- turn error ≤ 2°;
- non-target drift ≤ 1°;
- penetration ≤ 0.5 mm;
- radial offset ≤ 0.5 mm;
- pop check ≤ 0.3 mm;
- rest rotation ≤ 0.5°;
- open-pad rotation ≤ 0.5°;
- causality;
- Option A: every criterion in 100 % of trials.

The E1-2 to E1-4 turn-error metric uses the unwrapped layer angle, as M2 introduced. Changes are marked **NEW**; all
are additions or tightenings, except where §8 decision 1 says otherwise.

| ID | Trials | Pass criteria |
|---|---|---|
| E1-1 Rest, 10 s | 20 | As M1. **NEW:** magnet validity (rule 2) |
| E1-2 Quarter turns | 24 | As M1, plus magnet validity |
| E1-3 Half turns | 22 | As M1, plus magnet validity |
| E1-4 Sequences | 20 × `R U R' U'`×6, and 20 × scramble(20) + inverse | As M1 (every observed state agrees with the oracle; final state solved), plus magnet validity. **NEW:** per-piece misalignment (D8-0 metric) after every move; growth slope over each 40-move run **< 0.005°/move**, the stage-1 S2 signal promoted to a criterion |
| E1-5 Forgiveness | U misaligned 0…20° in 1° steps, both signs, then R (42) | As M1: categorical, never illegal or oracle-mismatched. Magnet validity applies. The forgiveness boundary is reported |
| **E1-5s Snap-back (NEW)** | U offset by the rig by ±1, ±2, ±3, ±5, ±8°, released (10 × 2 seeds = 20) | **From ≥ 3°: \|U error\| ≤ 0.5° after 1 s.** Residuals from ±1/±2° are reported (stage 1: ≤ 0.59°) with no threshold. **Disclosed:** the 0.5° line was chosen when the stage-1 analysis was written, not pre-declared, and is proposed here for approval before any scored trial |
| E1-6a Command without contact | 6 | As M1, plus magnet validity |
| E1-6b Opposed torques | 6 | As M1 (categorical; radial change ≤ 0.5 mm). Rule 3 applies |
| E1-6c Corner twist | 8 corners | **See §8 decision 1.** M1's categorical criterion, reported quantities and rule 3 apply in every option |
| **E1-6m Magnet energy and impulse (NEW, P-16)** | All moves of E1-2 to E1-4 | Per move, these are reported: the magnet energy change ΔU_mag; the magnet work W_mag = Σ qfrc_mag·qvel·dt, from the generalized forces the callback applied; and the peak magnet force and impulse on the turning layer. **⟨P⟩ conservativeness:** \|W_mag + ΔU_mag\| ≤ 10 % of the magnet energy exchanged during the move + 0.05 mJ. Basis: the V5 implicitfast bound of 7.6 % plus margin |
| **E1-6n No-magnet comparison (NEW, P-16)** | E1-2 to E1-6 rerun without magnets, same seeds | Reported only, no threshold. Shows what the magnets change |
| E1-7 Sensitivity | M1's factors, plus the M4 factors below | Outcome unchanged within the band; any flip is reported as a fragility |
| E1-8 Throughput | As M1, with and without magnets | Measurement only. Includes 1, 4, 8 and 16 parallel processes |

**E1-7, M4 factors** (the approved P-18 sweep):

| Factor | Values |
|---|---|
| Magnet size and grade | none; 3×1.5 N35; 4×1.5 N35; **4×2 N35**; 4×2 N52 |
| Face gap | 0.5, **1.0**, 1.5 mm |
| Strength scale (V2: the model may overstate force by about 1.5×) | 0.67, **1.0** |
| Radial preload | **Dropped**: M4 has a rigid radius, and B2/B2E (with preload) failed stage 1. Disclosed |

Each new magnet size needs its own tables (about 20 minutes each) and must pass V3 at that size before use.

## 5. Pass logic

Option A, as for M1: every categorical and quantitative criterion holds in 100 % of scored trials of E1-1 to E1-6.
E1-7 and E1-8 must be completed and published. G1 also needs your sign-off.

If M4 fails, the failure is documented in full and G1 stays not passed. A scripted rotation is never a fallback.

## 6. Work required before freezing

1. **Move the magnet model into `src/`** (`rubiknetic/cube_physics/magnets.py`), with unit tests:
   - V4 and V6 as tests;
   - the force/energy-gradient check;
   - a test that the callback ignores ctrl, time and qvel;
   - an injected state write is still caught by the edit audit with magnets installed.

   The near-field tables become a reproducible build step with a recorded hash; they are not committed.
2. **Extend V3 to 7.5° tilt.** The operational peak in stage 1 was 4.80° against the 5° limit. If 7.5° passes on
   the unchanged criterion, the validated range becomes 7.5°. If not, it stays 5° and rule 2 applies at 5°.
3. **Scored runner** (`experiments/E4_scored_m4/`). Reuse the M1 runner with:
   - magnet installation;
   - per-trial magnet stats and tilt;
   - the rule-2 failure;
   - E1-5s;
   - E1-6m and E1-6n;
   - the D8-0 misalignment metric;
   - the clean-commit check.
4. **E1-8 on a quiet machine.** Record load average and CPU model.
5. **R1 bench data**, if §8 decision 1 chooses option (c).

## 7. Known issues carried into scoring (`INFERENCE`)

- **Per-piece play.** B1 pieces sit 1.1–2.3° off square without building up. Non-target drift (≤ 1°) was not
  measured in stage 1 and is the main unknown among M1's thresholds.
- **Corner twist about 40° at 5 N·m** with no real-cube anchor (§8).
- **Tilt margin.** 4.80° operational against a 5° validated limit (§6 item 2).
- **Magnet force may be overstated** by about 1.5× (V2). E1-7 covers this with the 0.67 scale.

## 8. Decisions requested from you

1. **E1-6c corner-twist criterion.** Every option keeps M1's categorical criterion: after release the observer never
   reports a valid non-solved state.
   - **(a) M1's approved E1-6c unchanged:** categorical only; twist, penetration and the load at 15° reported.
     **Disclosure:** M2's stricter credibility criteria were "twist ≤ 2° at 5 N·m" and "penetration ≤ 0.5 mm". M4 is
     known from unscored stage 1 to fail both (about 40° and about 1.0 mm). Choosing (a) with that knowledge has to
     be recorded as such.
   - **(b) M2's stricter criteria.** M4 is expected to fail G1 on E1-6c.
   - **(c) Recommended:** set a quantitative E1-6c threshold from R1 real-cube measurements
     ([`R1_real_cube_bench/PROTOCOL.md`](R1_real_cube_bench/PROTOCOL.md), M5) **before** scoring. For example: "twist at
     5 N·m does not exceed the measured real-cube twist at the same torque", or, if real cubes pop, "torque to reach
     15° ≥ the measured real-cube value". The number is set from the measurement, not from M4's result.
2. **Approve the NEW criteria:** magnet validity; E1-4 growth slope; E1-5s snap with its disclosed 0.5° line; E1-6m;
   E1-6n.
3. **Approve the configuration** (§1), the seed range 6000–6999, and the E1-7 M4 factors, including dropping radial
   preload.
4. **Approve the §6 work** before any scored run.

## 9. Amendment 1 (2026-11-15, before any scored M4 trial)

**Approved by the user:** "i approve your recommenndations" (2026-11-15), covering items A1 and A2 below. A1 is
conditional, as stated. Logged as P-24.

**Triggers (`FACT`, unscored):**
- **Drift.** The runner smoke test (seed 95) gave non-target drift of 1.59° on one move, against M1's approved 1°
  limit. A probe on seeds 95–97 (6-move sequence, 18 moves per arm) found drift > 1° in **9/18** moves with magnets
  (max 1.61°) and 1/18 without (max 1.30°), at the 0.2 mm piece gap.
- **Gap probe.** The same probe at a **0.1 mm piece gap** gave 0/18 moves over 1° (max 0.91°), and the largest magnet
  tilt fell from 4.64° to 2.53°. Friction μ 0.5 instead gave 1/18 over (max 1.34°).
- **§6 item 2.** The V3 extension to 7.5° failed on torque (3.9e-5 N·m against a 2.4e-5 tolerance). The validated
  tilt stays 5°.
- **Corner twist.** Two literature searches (`R1_real_cube_bench/LITERATURE.md`) found no real-cube corner-twist data.
  The only primary anchor is the toy-safety torque test of 16 CFR §1500.53(e): 4 in·lb, 0.45 N·m.

| # | Change |
|---|---|
| A1 | **Nominal piece gap 0.2 → 0.1 mm** (§1); the face gap becomes 0.9 mm; the E1-7 gap factor becomes 0.05 / **0.1** / 0.2 mm. **Conditional:** adopted only if an unscored dress rehearsal of every pre-registered experiment (E1-1…E1-6, E1-5s and E1-6t; seeds = scored seeds + 1000, i.e. 7000–7999; `D8_alignment/rehearsal_gap.py`) passes **every M4 criterion in every trial**, under the same verdict logic as the scored run (Option A). The condition was fixed before any rehearsal result was seen. If it fails, A1 is not adopted, and the options go back to the user. **Disclosed:** this design change was chosen after seeing the drift problem in unscored data. The scored seeds (6000–6999) stay unused, and no threshold changes |
| A2 | **Corner twist (§8 decision 1 changes from (c)):** **E1-6c** uses M1's approved categorical criterion only, with twist, penetration and the torque at 15° reported. **NEW E1-6t, toy-standard torque test** (16 trials, seeds 6640–6655): 0.45 N·m about each corner's diagonal, applied over 5 s, held 10 s, released, in both directions (the form of 16 CFR §1500.53(e)). **Pass:** after release the observed state is valid and solved, and penetration ≤ 0.5 mm throughout (M1's integrity limit). Rule 3 applies. **Disclosed:** a standards-anchored engineering assumption, **not real-cube parity**. M4 has a rigid radius, so popping can't happen in the model; this is a known abstraction. M4's behaviour at 0.45 N·m was not known when the criterion was set. R1 bench data becomes post-G1 validation, not a gate |

**Unchanged:** every threshold, Option A, the seed ranges, rules 1–4, and the other NEW criteria.
