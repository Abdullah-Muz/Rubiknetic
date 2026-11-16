# Phase 1 (G1) Pre-registration: M5, magnetic contact cube at a 0.05 mm piece gap

**Status: NOT APPROVED. The condition failed (P-33).** The draft was approved on 2026-11-16 on condition that the
independent review require no changes (P-32). The review
([`M5_PREREGISTRATION_REVIEW1_2026-11-16.md`](M5_PREREGISTRATION_REVIEW1_2026-11-16.md)) returned ACCEPTABLE WITH
CHANGES, with five required changes, so the draft returns to the user. The text below is unchanged from the reviewed
draft.
- Drafted 2026-11-15 under the condition the user approved in
  [`D8_alignment/results/rehearsal_gap0.05mm/CONDITION.md`](D8_alignment/results/rehearsal_gap0.05mm/CONDITION.md). That
  condition was met (P-30); the user then said "approved" to drafting.
- No scored M5 trial exists. Scored runs may start only after:
  - this text is approved;
  - the §6 work is committed;
  - the runner checks for a clean commit.
- Thresholds may never be loosened after a failure.

**Name.** "M5" is the next free mechanism label. It is not the "M5" measurement in
`R1_real_cube_bench/PROTOCOL.md`, which is a corner-twist bench test.

**Basis:**
- The approved M4 pre-registration ([`PHASE_1_M4_PREREGISTRATION.md`](PHASE_1_M4_PREREGISTRATION.md)) including
  Amendment 1 item A2, and through it the M1 pre-registration. **M5 is M4 with one change: the piece gap.** Every
  rule, criterion and threshold is M4's unless this file says otherwise.
- **The play-criteria proposal is not used.** Revision 3 is not in force (P-28). M5 is judged on M1's and M4's
  per-piece criteria exactly as registered.

## 0. Disclosure (read first)
1. **The gap was chosen after seeing unscored data** (`FACT`):
   - at the registered 0.2 mm, an unscored probe showed drift over 1° (P-24);
   - a 0.1 mm rehearsal failed 16 / 204 trials (P-25);
   - the diagnostic attributed the drift to B1's per-piece play (P-26);
   - a 21-trial study at 0.05 mm passed (P-27);
   - a full 204-trial rehearsal at 0.05 mm passed every M1 and M4 criterion (P-30).

   The scored seeds below have never been used, but the design choice itself is post hoc.
2. **Whether a 0.05 mm clearance is realistic is an `ASSUMPTION`.**
   - The only numeric source found is a 2×2×2 puzzle patent, US 6,217,023 B1, which says "the clearance between
     pieces being of the order of 0.05 mm and being a matter for trial and error by the puzzle designer".
   - No measurement of a real 3×3 was found.
   - Generic ABS moulding tolerances place 0.05 mm at the tight end of what is achievable. That figure comes from a
     manufacturer's guide the main session has not checked.
   - R1 bench data would settle it, after G1, as for E1-6t.
3. **Without magnets, 0.05 mm jams** (P-27: turner torque at its 1 N·m clip, a layer 86° short, forgiveness blocked).
   M5's turning depends on the magnets keeping the layers square (`INFERENCE`).
4. **Turner torque headroom is smaller** (`FACT`, rehearsal):
   - median turning torque 0.21 N·m, about 2× the 0.1 mm run;
   - 1 of 1,376 moves touched the 1 N·m clip, and that move still turned correctly.

   It is reported (§4), not a criterion: M1 and M4 have none, and adding one after seeing this value would be a
   post-hoc choice in either direction.
5. **M1's per-piece drift criterion is kept at 1°.** In the rehearsal the largest value was 0.74°, a margin of 0.26°.

## 1. Frozen configuration (proposed)
| Group | Value |
|---|---|
| Cubies, rig, solver | M4 §1 unchanged: M1 as frozen, with `radial_preload = 0` (B1, rigid radius), **except piece gap 0.2 → 0.05 mm** (`M1Params.gap = 0.00005`; box size = pitch − gap) |
| Magnets | M4 §1 unchanged: 48 axial discs, 4 × 2 mm N35, 0.4 mm wall, classic layout. Because the wall is unchanged, **the face gap is 0.85 mm** (M4: 1.0 mm) |
| Force law, validated range | M4 §1 unchanged: `src/rubiknetic/cube_physics/magnets.py`; validated near-pair tilt 5° (the V3 extension to 7.5° failed, Amendment 1) |
| Turner | Default M1 rig (turn_kp 5, kv 0.2, torque clip 1 N·m), unchanged |
| Runner | M4 logic (`experiments/E4_scored_m4/run.py`), including the P-26 neighbour-list reset |
| Software | MuJoCo 4.0.1, Python 3.12, NumPy and SciPy from `uv.lock` |

## 2. Run-integrity rules
- M1 rules 1–5 and M4 rules 1–3 apply unchanged:
  - clean commit;
  - edit audit;
  - numerical failure;
  - observed-move oracle;
  - no exclusions;
  - magnet callback check;
  - rule 2: magnet validity fails operational trials;
  - rule 3: magnet validity labels abuse trials.
- **Rule 4 (M5): scored seeds 10000–10999.** These are M1's experiment offsets shifted by +9000.
  - They are disjoint from M1 (1000–1999), M2 (2000–3999), the diagnostics (4302, 4401) and stage 1 (5100–5299).
  - They are also disjoint from M4's unused scored range (6000–6999), the rehearsals (7000–8999) and the M4 diagnostics
    (9000–9999).
  - A repository search found no use of seeds of 10000 or more.
  - The trial slots and move strings are M4's, with only the seeds shifted.

## 3. What varies between trials
As M4: misalignment ±1° per face applied before t = 0 and logged, grip 10–20 N, 0.8–1.2 s per quarter turn, and
scrambles for E1-4.

## 4. Experiments and thresholds
- **All of M4 §4 and Amendment 1 item A2 apply unchanged:**
  - E1-1 to E1-6, with M1's thresholds;
  - Option A;
  - magnet validity;
  - the E1-4 growth slope < 0.005°/move;
  - E1-5s;
  - E1-6c, M1's categorical criterion, with twist, penetration and the torque at 15° reported;
  - E1-6t (0.45 N·m; solved after release; penetration ≤ 0.5 mm);
  - E1-6m;
  - E1-6n;
  - E1-8.
- The only changes are additions that are reported, never criteria, and E1-7's band, re-centred on the new nominal:

| ID | Change |
|---|---|
| **E1-6n** | Unchanged in form (no-magnet rerun, same seeds, reported only). **Disclosed:** at 0.05 mm the no-magnet arm is expected to jam (P-27), so it shows that the magnets are necessary, not a like-for-like comparison |
| **Turner torque (NEW, reported)** | For every move of E1-2 to E1-4, report the peak turner torque, its median / p99 / max, and the number of moves at the 1 N·m clip. No threshold (§0 item 4) |
| **E1-7 sensitivity, M5 factors** | M4's factors, with the two gap factors re-centred by rule:
  - **Piece gap 0.025 / 0.05 / 0.075 mm.** This is M1's relative band (0.1 / 0.2 / 0.3 mm = 0.5× / 1× / 1.5× nominal) applied to the new nominal.
  - **Face gap 0.35 / 0.85 / 1.35 mm** (wall 0.15 / 0.4 / 0.65 mm), M4's ±0.5 mm band.
  - The magnet size, grade and strength-scale factors are as M4.

  **Disclosed:** 0.1 mm lies outside this band and is known to fail M1's drift criterion (P-25). The band was set by M1's rule, not to exclude it. 0.075 mm has never been run. 4×1.5 N35 failed V3 (P-26) and cannot be used unless it passes V3; 4×2 N52 must pass V3 before use, as M4 §6 required |

## 5. Pass logic
- Option A, as for M1 and M4: every categorical and quantitative criterion holds in 100 % of scored trials of E1-1
  to E1-6, including E1-5s and E1-6t.
- E1-7 and E1-8 must be completed and published. G1 also needs the user's sign-off.
- **At the G1 gate, the verdict must restate §0 items 1 and 2**: the gap was chosen post hoc, and the clearance is an
  assumption.
- If M5 fails, the failure is documented in full and G1 stays not passed. No rerun, no exclusion, and a scripted
  rotation is never a fallback.

## 6. Work required before freezing
1. **Scored runner `experiments/E5_scored_m5/run.py`.** It reuses M4's `run.py` logic unchanged, as
   `rehearsal_gap.py` does, with:
   - gap 0.05 mm;
   - seed shift +9000, with a range assertion of 10000–10999;
   - the turner-torque report;
   - the re-centred E1-7 gap factors. M4's face-gap factor computes the wall from M1's nominal 0.2 mm gap
     (`run.py:211`), so M5 must compute it from 0.05 mm;
   - a clean-commit check that also covers the new runner.

   It gets unit tests for the seed range, the gap override and the wall computation.
2. **A smoke test** of one trial per experiment on seeds outside every range. It is unscored and only checks the
   plumbing.
3. **E1-8 on a quiet machine**, with load average and CPU model recorded. This needs the user's other workload paused.
4. **The V3 check for any E1-7 magnet size not yet validated.**

## 7. Known issues carried into scoring (`INFERENCE`)
- **Drift margin:** 0.26° below the 1° criterion in the rehearsal. Across 1,376 new moves with new misalignments, a
  move above 1° is possible.
- **Torque headroom:** §0 item 4. A seed with higher friction or misalignment could clip the turner longer; whether
  that would show up as a turn error is not known.
- **Magnet force may be overstated by about 1.5×** (V2). E1-7's 0.67 strength scale tests this. Since the magnets
  prevent jamming at 0.05 mm, weaker magnets may jam: a likely fragility.
- **Abuse penetration** reached 0.61 mm (E1-6b) and 0.65 mm (E1-6c) in the rehearsal. Both are categorical
  experiments, so these values are reported and not judged against 0.5 mm, as for M4.

## 8. Decisions requested
1. **Approve this draft** (configuration, seeds 10000–10999, reported additions, E1-7 factors, §6 work), or modify it.
2. **M4's status.** M4 was approved but never scored.
   - **(a) Recommended:** close M4 as "superseded by M5 before any scored trial". Its unscored evidence (P-24 to
     P-27) stays on record as the negative result. INFERENCE: M4 at 0.2 mm would fail drift.
   - **(b)** Run M4's scored battery at 0.2 mm first, to record the failure formally (about 2–2.5 h).
3. **An independent review of this draft before approval** (P-20 subagent). Recommended because of §0 item 1; it is
   the user's choice.
