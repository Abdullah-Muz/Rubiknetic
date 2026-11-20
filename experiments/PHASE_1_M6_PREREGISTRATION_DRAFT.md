# Phase 1 (G1) Pre-registration: M6, core-magnet contact cube (DRAFT, revision 0)

**Status: DRAFT. Not approved, not reviewed, not in force. No M6 scored trial exists.**
- **When it was written.** On 2026-11-19, during ER7, so that a draft exists if ER7 meets its signals. The author had
  not run or read ER7's analysis. The author had seen ER7 progress lines; the last ones read were PASS lines for E1-3
  and E1-4 trials in both arms.
- **When it lapses.**
  - If ER7's C52 arm fails any feasibility signal (P-61), this draft lapses unused.
  - If ER8 (the derated arm, itself a draft) is approved and run, its outcome is disclosed in §0 before any review.
- **Path to force.** As for M5:
  - the user approves the text;
  - one or more independent reviews require no changes;
  - the §6.1 items are committed;
  - the runner checks for a clean commit.

  Thresholds may never be loosened after a failure.
- **Name.** "M6" is the label already used for the core-layout implementation checks
  (`experiments/M6_core_magnets/`, P-59, P-60). It names the same configuration.

**Basis.**
- The M5 pre-registration, revision 8 ([`PHASE_1_M5_PREREGISTRATION.md`](PHASE_1_M5_PREREGISTRATION.md)), and through
  it M4 (with Amendment 1 item A2) and M1.
- **M6 is M5 with one design change: the magnet layout.** Every rule, criterion, threshold and run-procedure item is
  M5's unless this file says otherwise. That includes M5 §2's manifest, start log, ledger, atomic records, resume,
  exception and integrity rules and the location check.
- **This file's changes are confined to:**
  - the magnets and their validated regime (§1);
  - the seeds (§2);
  - the E1-6n and E1-7 definitions (§4);
  - the folder names and `mechanism` label (§5, §6).

  None of them loosens an M1, M4 or M5 criterion.

## 0. Disclosure (read first)
1. **The layout was chosen after M5's scored failure, using unscored data** (`FACT`):
   - **M5 failed.** M5 failed G1 on one E1-1 rest trial: 0.560° against ≤ 0.5° (P-51).
   - **Diagnosis.** D10, D11 and ER1 traced the failure to fast corner–edge slip events with negative single-piece
     stiffness (P-53, P-54).
   - **Design.** ER2–ER6 screened layouts. The core layout was chosen statically (P-55 to P-59).
   - **M6 checks.** M6 checked the implementation. **Its near-pair survey failed, and its criterion was amended after
     that failure (P-60).** The amendment allows clamped near pairs that lie on trajectories ER5's V3-turn validated.
     The original verdict NOT ALL PASS is on record.
   - **ER7 rehearsal.** ER7 rehearsed the full Option A list on seeds 16000–16655.
2. **How independent the scored test is.** As in M5 §0 item 2:
   - **Held out.** The E1-4 scrambles are drawn from the new M6 seeds (§3).
   - **Not held out.** Every other move string is fixed by M1's registration and was seen by M5's scored run and by
     ER7. Only the setup draws are new.
3. **Abstraction** (`ASSUMPTION`, P-58).
   - The core magnets sit at real-mechanism radii (22.04 mm edge, 21.95 mm corner) on the `core` body, with no
     collision geometry. Their positions lie inside the B1 piece volumes, which no real cube could have.
   - What is modelled is the magnetic force between pieces and core. The contact geometry stays B1's.
4. **Magnet strength.**
   - The ideal-magnet force law may overstate real strength by up to about 1.5× (D8 V2).
   - If ER8 has run by then, its outcome is stated here. If not, the 1/1.5 scale arm of E1-7 (§4) is the only test of
     this.
5. **Integrator.** implicitfast at 0.5 ms shows a bounded energy oscillation of about 10 % on a rigid-layer release
   with this layout (M6 V5). The setting is unchanged from M5, and both arms of ER7 used it.
6. **Throughput.** M6 measured 606 steps/s (rig model, idle, one process) against 3,854 without magnets. E1-8 is
   judged as in M5 §6.2.

## 1. Frozen configuration (proposed)
| Group | Value |
|---|---|
| Cubies, rig, solver | M5 §1 unchanged: B1 (`radial_preload = 0`), piece gap 0.05 mm |
| Magnets | **Replaces M5's 48 corner–edge magnets.** 40 axial discs: 20 on the pieces (one per edge and corner) and 20 on the `core` body, in coaxial attracting pairs. `core_layout(MagnetParams(4 mm, 3 mm, "N52"), clearance = 0.2 mm)` (`src/rubiknetic/cube_physics/magnets.py`, `911e45b`) |
| Force law, table | `magnets.py` force law unchanged (dipole far field plus the tilt-aware near-field table). N52 table `tilt_4x3_1.455T_s1_r8_h1.5_q16x48.npz`, with the SHA-256 recorded in `experiments/M6_core_magnets/results/m6_checks.json` and checked at every start |
| Validated regime | **Validated tilt 20°** for this configuration (ER5 V3-turn in the real placement; P-60). A trial is **outside the validated regime** if any near pair is perpendicular, or its maximum near tilt exceeds 20°. Clamped \|z\| on piece-to-core pairs is inside the regime (P-60). Rules 2 and 3 of M4 apply with this definition: outside the regime, an operational trial fails and an abuse trial is labelled. Every record stores `MagnetSystem.stats` |
| Turner, runner, software | M5 §1 unchanged. Runner `experiments/E6_scored_m6/run.py` = M5's runner with the magnet installation replaced (§6.1) |

## 2. Run-integrity rules
- **M5 §2 applies unchanged**, with the folders under `experiments/E6_scored_m6/` and `mechanism` = "M6".
- **Rule 4 (M6), seeds: M6 seed = M5 scored seed + 7000 = M4 scored seed + 11000**, for every trial, including the
  hard-coded E1-5s and E1-6t bases.
  - That gives 17000–17655; `SCORED_SEED_RANGE` = 17000–17999.
  - A repository search on 2026-11-19 found no use of the 17000s in code or documents.
  - The range is disjoint from M5's scored seeds (10000–10999), D11/ER1 (on M5's seeds), ER2 (14000–14019), ER7
    (16000–16655) and every earlier range listed in M5 §2.
  - The search is repeated and recorded before approval.
- **No simulation on M6 seeds before the scored run.** ER8, if run, uses ER7's seeds.

## 3. What varies between trials
As M5 §3. The E1-4 scrambles are drawn with `random_scramble(20, s)` from the M6 seed s (17400–17419).

## 4. Experiments and thresholds
**All of M5 §4 applies unchanged** (E1-1 to E1-6, Option A, magnet validity, E1-4 growth slope, E1-5s, E1-6c, E1-6t,
E1-6m, the turner-torque report, E1-8), except:

| ID | Change |
|---|---|
| **E1-6n** | Unchanged in form and never part of Option A. It is the same no-magnet arm as M5's, because M5 and M6 differ only in magnets. Disclosed: at 0.05 mm without magnets, it is expected to jam (P-27) |
| **E1-1 instrumented rest (NEW, reported)** | Every E1-1 trial also runs D10's 60 s instrumented rest, and D11's slip events are counted. Reported only: the M1 criterion (peak rotation ≤ 0.5° in the first 10 s) is unchanged and is the only judged quantity |
| **E1-7 sensitivity, M6 factors** | **OPEN; see §8.** Proposed factors: piece gap 0.025 / 0.05 / 0.1 mm (M5's band); **core clearance 0.1 / 0.2 / 0.3 mm** (ER6 screened all three; replaces M5's face-gap factor, which has no meaning in the core layout); grade N35 / N42 / N52 (exact Br² rescaling, M6 S1); **strength scale 1/1.5** on N52 (= ER8's arm); no-magnet arm. **Magnet size: no factor.** 4×3 mm is the only size ER5 validated in the real placement, and 5×2 mm failed. **V3 coverage:** every grade and scale arm is a rescaling of the ER5-validated 4×3 mm table, so it shares that record by the M6 S1 linearity check. The 0.1 and 0.3 mm clearance arms were not in ER5's V3-turn (0.2 mm only); they need a V3-turn record each before the first start, or are "not run: outside V3". Flips are reported as fragilities, not G1 failures, as in M4 and M5 |

## 5. Pass logic and verdict script
- As M5 §5: Option A over E1-1 to E1-6, including E1-5s, E1-6t and E1-6m; 204 trials.
- Verdict script `experiments/E6_scored_m6/analyze.py`: M5's, with the M6 label, the M6 seed range, the regime
  definition of §1, and the expected counts unchanged.

## 6. Work required
### 6.1 Gates the scored run
1. **Runner `experiments/E6_scored_m6/run.py`**: M5's runner with only these changes:
   - the magnet installation (as ER7's `use_core`);
   - the table provider with its SHA-256 check;
   - validated tilt 20° with the perpendicular-pair rule;
   - the seeds;
   - the folders and label;
   - the E1-1 instrumented rest;
   - the E1-7 factors as approved.

   The clean-commit check covers M5's frozen paths plus `magnets.py`, `m6_checks.json`, this file, the runner and
   `analyze.py`.
2. **Verdict script** (§5), with failure tests.
3. **Unit tests**, none stepping the simulation on an M6 seed:
   - the seed list;
   - 40 magnets with the core layout installed in every magnet job;
   - the table SHA-256 refusal;
   - the regime rule: perpendicular pair → outside, tilt 20.01° → outside, clamped z → inside;
   - M5's run-procedure tests, ported;
   - the E1-7 arm classification.
4. **Smoke test** on seeds outside every range, unscored, through the full run procedure, as M5 §6.1 item 4.
5. **E1-7 V3-turn records** for the 0.1 and 0.3 mm clearance arms, if those arms are approved.
6. **Independent review(s)** of the text and the code, as for M5.

### 6.2 Gates the G1 sign-off only
E1-8 on a quiet machine, as M5 §6.2.

## 7. Known issues carried into scoring (`INFERENCE`)
- **The P-58 abstraction** (§0 item 3). A G1 pass would establish the simulated mechanism, not a buildable cube.
- **Ideal-magnet strength** (§0 item 4).
- **The integrator's energy oscillation** (§0 item 5). Its effect on rest slips is not separately measured.
- **M5's known margins** (drift 0.786° of 1°; torque headroom; abuse penetration) apply until ER7 shows otherwise for
  C52. They are restated with ER7's numbers before review.

## 8. Decisions requested (when, and only if, ER7 meets its signals)
1. Whether to proceed to a scored M6 run at all, or to run ER8 first.
2. The E1-7 factors (§4). In particular: the clearance band, whether to build V3-turn records for 0.1 and 0.3 mm,
   and whether the 1/1.5 scale arm stays in E1-7 if ER8 has already run.
3. The seed rule (+7000 on M5).
4. The number and scope of independent reviews.
