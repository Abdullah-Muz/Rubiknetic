# ER9 — Core layouts that anchor every piece in all three rotations (PROTOCOL, fixed before any run)

**Status: fixed on 2026-11-19, before any ER9 computation.** Exploratory and unscored. Part A is a static screen (no
dynamics). Part B is a small dynamic probe of at most two candidates Part A selects.
- **Approval.** The user's instruction "please find a solution to these problems, be creative" (2026-11-19) followed
  the ER7 report, whose recommended option was a static screen of core layouts that also restore spin and twist. The
  main session treats it as approval for this protocol, under the delegation recorded in P-63, and records it in the
  DECISION_LOG. The user may reverse it.
- **Scope.** It changes no record and selects no mechanism. A candidate that does well here would still need the
  user's approval, a force-law validation for its placement, a full rehearsal and a new pre-registration.

## Idea
ER7 showed that one coaxial magnet pair per piece leaves the piece free to spin about that pair's axis, and that the
whole cube then has a contact-free motion nothing restores (`../ER7_core_magnet_rehearsal/SUMMARY.md`).

**Principle.** Give every edge and corner two or three magnet pairs to the core, set off the piece's own axis, each
pair with its axis along the radial line through it.
- **No new unstable direction.** A coaxial attracting pair is stable sideways and unstable along its axis. With every
  axis radial, the unstable direction is radial for every pair, and a B1 piece cannot move radially. This is why the
  core layout had no slide/cross trade-off (ER3), and it stays true off the piece's axis.
- **Spin and twist become restoring.** A pair set a distance d off the piece's axis is pushed sideways when the
  piece spins, so two pairs give a spin stiffness of about 2·k·d², where k is one pair's sideways stiffness.
- **Every piece is tied to the fixed core in all three rotations,** so no collective motion is left free.
- **The cost** is more magnets and more turning torque, because the tangential stiffness grows with the number of
  pairs. The screen measures both.

**Why a stiffness target and not just "positive"** (`INFERENCE` from ER7's records). The joints have a friction loss
of 0.5 mN·m per axis (M1's frozen value). In ER7 every C52 piece stopped where the magnet torque equalled that
friction: 0.066° for edges and 0.093° for corners, against 0.072° and 0.090° predicted from the tangential stiffness.
The same rule for spin gives the leftover a layer would show after a snap-back:

| Spin or twist stiffness | Predicted layer error from edges | from corners |
|---|---|---|
| 50 mN·m/rad | 0.57° | 0.57° |
| 100 mN·m/rad | 0.29° | 0.29° |
| 150 mN·m/rad | 0.19° | 0.19° |

M4's criterion is 0.5°. L0 (M5's layout) has 122 and 118 mN·m/rad (ER3).

## Part A — static screen (`er9_screen.py`)
**Candidates.** Magnets 4×3 mm, core clearance 0.2 mm and real-mechanism radii, as C52. The piece magnet and its
core magnet sit on one radial line, tilted by an angle γ from the piece's axis.
- **Grade:** N35, N42, N52 (exact rescaling of ER5's validated N35 table, as ER6).
- **Edges:** one pair on the axis (as C52), or two pairs at ±γ with γ = 14°, 16°, 18° or 20°, set either toward the
  two neighbouring centres or toward the two neighbouring corners.
- **Corners:** one pair on the axis, or three pairs at γ = 10°, 12°, 14° or 16°, set either toward the three
  neighbouring edges or toward the three neighbouring centres.
- **Centres:** no magnets. (A centre has one rotation, about its own axis; whether it needs anchoring is read from
  the probe.)

That is 3 × 9 × 9 = 243 layouts, including C52 itself as the reference.

**Measured** for each layout:
- ER3's quantities by ER3's function: every single-piece stiffness (edge spin, slide and cross; corner twist and
  tangential), the stiffness of each rigid layer, and the U-turn torque profile and its peak.
- **The full stiffness matrix of the cube** (66 rotations: three per edge and corner, one per centre) by finite
  differences, and its eigenvalues. This is new, and it sees collective motions.
- **The stiffness of the collective twist** ER7 found (every piece turned about its own radial axis in proportion).
- **Geometry over every face turn** (−90° to +90° in 1° steps, six faces): the smallest clearance between any two
  magnets (ER6's sweep), and the smallest centre distance between magnets on two different pieces.
- **Near-pair survey** over the same poses in 2° steps: perpendicular near pairs, largest near tilt, and near pairs
  between two pieces.

**Screen criteria (fixed now).** A layout passes if all hold:
1. ER3's criteria: no single-piece stiffness below −1 mN·m/rad, layer stiffness ≥ 1.0 N·m/rad, U-turn peak
   ≤ 0.5 N·m.
2. **Edge spin ≥ 100 and corner twist ≥ 100 mN·m/rad.**
3. **Full matrix:** exactly six eigenvalues below 1 mN·m/rad in magnitude (the six centres, which carry no magnets),
   and every other eigenvalue ≥ 50 mN·m/rad.
4. **Geometry:** no two magnets intersect in any face turn, and no two magnets on different pieces come within 8 mm
   centre to centre. 8 mm is the force law's near-field range: inside it, a pair of magnets side by side on two
   pieces would be evaluated outside the tabulated region.
5. **Survey:** no perpendicular near pair, largest near tilt ≤ 20° (P-60's validated regime), no piece-to-piece near
   pair.

**Self-checks.** (S1) The C52 row reproduces ER6's N52, c = 0.2 mm row (single-piece stiffnesses, layer stiffness,
peak) to 1e-9. (S2) For C52 the full matrix has 26 eigenvalues below 1 mN·m/rad in magnitude (20 spins and twists and
six centres) and a collective-twist stiffness below 1 mN·m/rad. (S3) ER6's table hash check.

**Selection (fixed now).** Among passing layouts, take the one with the lowest U-turn peak; break ties by fewer
magnets, then by the lower grade. If none passes, report the layouts that fail only criterion 1's torque limit or
only criterion 2, ordered by how far they miss, and stop.

## Part B — dynamic probe (`er9_probe.py`; only if Part A selects a layout)
- **Arms:** the selected layout. A second arm may be added only if it is the runner-up by the rule above and differs
  in grade or in which pieces are split.
- **Runner:** ER7's, loaded unchanged, with its layout function and magnet parameters replaced in each fresh worker,
  as ER8's wrapper did. The table is M6's N52 table times the exact strength factor for the grade.
- **Trials:** from ER7's list and seeds (16000–16655, already diagnostic): E1-1 rest (20, scored 10 s rest only),
  E1-2 quarter turns (24), E1-5s snap-back (20) and E1-5 forgiveness (42). 106 trials per arm.
- **Self-check:** with C52's own layout the wrapper reproduces ER7's C52 records for the first E1-2 and E1-5s trials
  exactly (run-metadata keys skipped).
- **Probe signals (fixed now), all on ER7's criteria:**
  1. E1-5s: every scored trial passes (|error| ≤ 0.5° after 1 s from 3° or more);
  2. E1-1: every rest rotation ≤ 0.5°;
  3. E1-2 and E1-5: every trial passes;
  4. no trial outside the validated regime (tilt > 20° or a perpendicular near pair), and no piece-to-piece near pair.
- **Reported:** peak turner torque against L0 and C52 on the same seeds, moves at the 1 N·m clip, each piece's
  leftover rotation after the +8° snap-back (ER7's `posthoc/snap_diag.py` method), and steps per second.
- **Reading.** Meeting all four signals makes the layout worth a full 204-trial rehearsal, which would be proposed to
  the user with a force-law validation for the new placement. Failing any is reported trial by trial.

## Limits
- **The force law is not validated for the new placement.** ER5's V3-turn compared the force law with the fine model
  for on-axis magnets at these radii. Off-axis pairs meet the same kind of pair (two radial magnets at these two
  radii), but in different combinations. Criterion 5 and signal 4 keep the probe inside the regime ER5 covered pair
  by pair; they do not replace a V3-turn check of the new layout.
- **Fit in a real piece is not checked.** The magnets have no collision geometry (P-58). An off-axis magnet at these
  radii sits under a neighbouring piece's volume in the B1 model; a real ball-core cube would carry it in the
  piece's foot. ER4 checked the fit only for on-axis magnets.
- The stiffness target rests on one seed's diagnostic and M1's joint friction value.
- Static stiffness screens have now failed to predict a dynamic result twice (ER3's criteria passed C52). The probe
  is the test; the screen only narrows the field.

## Deviations (recorded before the probe run)
1. **Probe self-check, 2026-11-19.** The first self-check failed on one bookkeeping field in both trials: the wrapper
   stored the near-field table's folder in `magnet_table.table_file`, where ER7 stores the file. No other field
   differed. The wrapper now stores the file, and the rerun shows 0 differences in both trials. The first output is
   kept as `results/probe/selfcheck_run1.json`.

## Part C — weaker magnets in the selected geometry (addendum, fixed 2026-11-19 after Part B, before any Part C run)
**What Part B showed** (`results/probe/report.json`; details go in the summary).
- Both arms met all four probe signals, 106 / 106 trials each: S1 (N42) and S2 (N52), with two pairs per edge at 20°
  and three per corner at 16°, set toward the centres. Every snap-back error was below 0.001°.
- **Turning is too stiff.** In E1-2 the turner reached its 1 N·m limit in 20 of 24 quarter turns in both arms
  (median peak 1.0 N·m; L0 0.144; C52 0.70, with 4 at the limit). Every turn still completed and passed.
- **The stiffness target of Part A was not needed, and its rationale was wrong.** One replay per arm
  (`results/probe/diag/`) showed every edge and corner with zero leftover spin after the release, where the
  joint-friction rule predicted up to 0.27°. The small leftovers in ER7 that the rule seemed to match (0.066° and
  0.093°) are gravity sag: the piece's weight times its horizontal lever, divided by the tangential stiffness, gives
  0.0656° and 0.0932° for C52 and 0.0408° and 0.0402° for S1, the values observed. Joint friction does not hold a
  piece off its magnetic equilibrium in this model.

**Question.** How weak can the magnets be in this geometry and still meet the probe signals, and how much does the
turning torque fall?

**Arms.** The S1 geometry (edges split at 20° toward the centres; corners with three pairs at 16° toward the centres;
96 magnets), 4×3 mm, clearance 0.2 mm, at three strengths set by `MagnetParams.scale` on grade N35:

| Arm | Strength (pair energy against N35) | Static layer stiffness | Static U-turn peak |
|---|---|---|---|
| W1 | 1.0 (N35) | 4.41 N·m/rad | 0.283 N·m |
| W2 | 0.5 | 2.21 N·m/rad | 0.142 N·m |
| W3 | 0.3 | 1.32 N·m/rad | 0.085 N·m |

The W2 and W3 values are the W1 row of the screen times the scale (the stiffnesses are linear in strength). W3 is the
weakest of the three that keeps ER3's layer stiffness of at least 1.0 N·m/rad.
- **What a scale below 1 stands for.** A magnet of the same size with a lower remanence (0.5 → 0.84 T, 0.3 → 0.65 T,
  the range of bonded NdFeB), or a smaller sintered magnet of the same dipole moment. Neither has been fitted or
  validated; it is a strength knob for this exploration.
- **Tables.** M6's N52 table times the exact strength factor, written once and checked on every use, as in Part B.
- **Geometry and survey** do not depend on strength, so Part A's result for this geometry stands (criteria 4 and 5
  passed).

**Trials, self-check and signals:** as Part B (106 trials per arm, the same four signals).

**Selection (fixed now).** Among the five arms of Parts B and C that meet all four signals, the one with the lowest
median E1-2 turner torque is the candidate for a full 204-trial rehearsal. If W3 is selected, weaker strengths are
not explored here: W3 is already at ER3's layer-stiffness limit.

**Reported:** as Part B, plus each arm's gravity sag (largest tangential leftover at rest).

## Part D — full rehearsal of the selected arm (addendum, fixed 2026-11-19 while Part C was running, before any Part C result was read)
- **Arm:** the one Part C's selection rule names. If no arm of Parts B and C meets all four signals, Part D lapses.
- **Trials:** ER7's full list and seeds, unchanged: 204 trials (E1-1 to E1-6, E1-5s, E1-6t), seeds 16000–16655, with
  D10's instrumented 60 s rest in E1-1. The 106 probe trials are run again inside it; they must reproduce the probe's
  records (same pass flags and the same rest and snap-back values), which is reported as a check.
- **Runner:** `er9_full.py`, the Part B wrapper around ER7's runner with the trial filter and the rest shortening
  removed. Records in `results/full/<arm>/`.
- **Signals (ER7's three, unchanged):**
  1. 0 / 20 E1-1 slip events (D11's definition) and every rest rotation ≤ 0.5°;
  2. M5's Option A rule over the 204 trials, with E1-6m ⟨P⟩;
  3. no trial outside the validated regime (near tilt > 20° or a perpendicular near pair).
- **Analysis:** `er9_full_analyze.py`, which applies ER7's functions (`er7_analyze.py`) to the arm and prints it beside
  ER7's L0 and C52: pass counts by sub-experiment, slip seeds with intervals, paired rest rotation, sequence drift and
  turner peak torque, and moves at the 1 N·m limit.
- **Reading (fixed now).**
  - **All three met:** the layout is a candidate for a scored pre-registration. That would be proposed to the user
    together with what it still lacks: a force-law validation for the off-axis placement (an ER5-style V3-turn), a fit
    check in a real piece (as ER4), and the meaning of the strength used.
  - **Any signal missed:** reported trial by trial against L0 and C52; the next step goes to the user.
- **Limits:** those of ER7 and of Part B. In particular the seeds are ER7's, already used for diagnostics and for
  selecting this arm, so the rehearsal is not independent of the selection.

## Part E — hybrid: M5's corner–edge magnets plus weak anchors (addendum, fixed 2026-11-20 after Part D, before any Part E trial)
**Why.** Part D's arm W3 met all three signals but its turner reached the 1 N·m limit in 771 of 1,376 moves. Single-turn
replays (exploratory, seed 16100, first U of an E1-2 trial; `er9_turn_diag.py`, outputs in `results/probe/diag/`)
were read before this addendum was written, and they chose its arms:

| Replay | Layout | Peak turner torque | Steps at the limit |
|---|---|---|---|
| L0 | M5's 48 magnets | 0.461 N·m | 0 |
| W3 | anchors, N35 × 0.3 | 1.000 | 4.3 % |
| X0.1 / X0.03 / X0.003 | anchors, N35 × 0.1 / 0.03 / 0.003 | 1.000 / 0.782 / 1.000 | 0.1 % / 0 / 9.8 % |
| H0.2 / H1 / H2 | M5's 48 + anchors (4×2 N35) at clearance 0.2 / 1 / 2 mm | 0.734 / 0.653 / 0.278 | 0 / 0 / 0 |

- INFERENCE: the stall at about 7° is not caused by the anchors. It is there, and worse, with almost no magnets
  (X0.003). M5's corner–edge magnets, which tie the pieces of a turning layer to each other, suppress it.
- PROPOSAL (tested here): keep M5's 48 magnets for turning and add weak anchors to hold the pieces at rest, which is
  where M5's layout fails (E1-1 slips).

**Layout.** M5's `layout()` unchanged (48 magnets) plus the S1 anchor geometry (edges 2 pairs at 20° toward the
centres, corners 3 pairs at 16° toward the centres; 96 magnets), 144 magnets in all. One magnet type throughout,
M5's 4 × 2 mm N35 at scale 1 with M5's validated table (a MagnetSystem has one magnet type). Anchor strength is set by
a real dimension, the piece-to-core clearance c along each pair's axis (face gap = c + 0.8 mm), not by a strength scale.
Code: `er9_hybrid.py`.

**Arms:** HB1, HB2, HB3 with c = 1, 2, 3 mm.

**Runner:** `er9_hybrid_run.py`, the Part B wrapper mechanism with `er9_hybrid.configure`. Records in
`results/hybrid/probe/<arm>/` and `results/hybrid/full/<arm>/`.

**Self-check (before any arm):** the hybrid path with the anchors switched off (48 magnets installed through ER7's
core-arm path) must reproduce ER7's L0 records for the first E1-2 and the first E1-5s trial in every field except run
metadata and the fields that name the arm and the table (`er7_arm`, `mechanism`, `magnet_table`, `er9_arm`, `er9`).

**Validated regime.** The table is M5's, so the tilt limit is M5's V3 validated tilt for the 4 × 2 magnet (not P-60's
20°, which belongs to the 4 × 3 table). A trial is flagged if a near pair exceeds it or a perpendicular near pair occurs.
V3 validated this table for corner–edge pairs; its use for coaxial piece-to-core pairs at these gaps is an extension
that a scored run would need to validate (an ER5-style V3-turn at this placement).

**Probe (as Part B):** the 106 trials (E1-1, E1-2, E1-5, E1-5s) on ER7's seeds, the same four signals.

**Selection (fixed now):** among the arms that meet all four probe signals, the one with the lowest median E1-2 turner
torque; ties go to the larger clearance. That arm gets the full 204-trial rehearsal with Part D's three signals
(tilt limit as above) and Part D's analysis (`er9_full_analyze.py ARM --root results/hybrid`). If no arm meets the four
signals, Part E ends there and is reported.

**Reading (fixed now).** As Part D, with one addition: the hybrid is reported against L0 on turner torque (median,
maximum, moves at the limit). All three signals met and no move at the limit: the hybrid replaces W3 as the candidate.
All three met but with moves at the limit: both are reported and the choice goes to the user.

**Limits.** Those of Parts B–D. In addition: the arms were chosen after single-seed replays on an ER7 seed; 144
magnets (edges carry 4, corners 6, the core 48) have not been checked for fit in a real piece; M5's magnets and the
anchor magnets act on each other, which is inside the force law but outside what V3 covered.

### Part E amendment 1 (fixed 2026-11-20, before any Part E arm trial)
**What happened.** The self-check of the Part E runner passed (anchors off: ER7's L0 records reproduced with 0
differences; kept as `results/hybrid/selfcheck_run1_4x2.json`). It also printed M5's validated tilt for the 4 × 2
table: **5°**. Anchor pairs stay within near-field range of their core partner for the first 14–16° of a turn, so
under M5's rule 2 every turning trial of HB1–HB3 as first specified would fail for leaving the validated range. I
should have checked that limit before writing Part E; the single-turn replays H0.2, H1 and H2 used the 4 × 2 table
beyond its validated tilt and are kept only as the observation that prompted this part.

**Change.** The three arms keep their layout and clearances but use the magnet type whose table is validated to 20°
(P-60), the one Parts B–D used:
- every magnet is 4 × 3 mm N35 at strength scale **0.756**, with M6's N52 table times the exact strength factor;
- 0.756 is the scale at which a corner–edge pair across the 0.85 mm face gap pulls as hard as M5's 4 × 2 mm N35
  pair (1.644 N; `er9_hybrid_scale.py`, `results/hybrid/scale.json`, computed before any arm trial). It stands in
  for M5's magnet at the corner–edge positions; it is not a catalogue magnet, and the meaning of the scale is the
  same open point as for W3;
- anchor pairs at c = 1, 2, 3 mm then pull 0.80, 0.39 and 0.23 N (W3's pairs: 0.3 × N35 at c = 0.2 mm);
- tilt limit 20° (P-60), as in Parts B–D.

**Self-check (replaces the one above for these arms):** the hybrid path with the corner–edge magnets left out,
scale 0.3 and c = 0.2 mm is arm W3; it must reproduce W3's Part C probe records for the first E1-2 and the first
E1-5s trial in every field except run metadata and the fields that name the arm (`er9_arm`, `er9`, `mechanism`).

**Replays before the probe.** One single-turn replay per arm (seed 16100, `er9_turn_diag.py G1 | G2 | G3`) is run
first as a smoke test and reported; it does not change the arms, the signals or the selection rule.

Everything else in Part E stands (probe trials, four signals, selection, full rehearsal, reading, limits). The limit
about V3 changes to: P-60 validated the 4 × 3 table for coaxial piece-to-core pairs up to 20° of tilt; corner–edge
pairs of 4 × 3 magnets and the cross-interaction of the two groups were not part of that validation.

### Part E amendment 2 (fixed 2026-11-20, after the self-check and the three smoke replays, before any probe trial)
**Self-check:** passed (W3's two probe records reproduced with 0 differences; `results/hybrid/selfcheck.json`).

**Smoke replays (seed 16100, first U of an E1-2 trial):**

| Replay | Anchor clearance | Peak turner torque | Steps at the limit | Max near tilt | Perpendicular near-pair evaluations |
|---|---|---|---|---|---|
| L0 (reference) | — | 0.461 N·m | 0 | — | — |
| G1 | 1 mm | 0.525 | 0 | 17.4° | 4,429 |
| G2 | 2 mm | 0.432 | 0 | 15.5° | 4,553 |
| G3 | 3 mm | 0.118 | 0 | 12.4° | 4,624 |

**Known before the probe: signal 4 cannot be met.** The force law corrects a near pair (closer than 8 mm) only if it
is within 45° of parallel; any other near pair gets the point-dipole formula alone, and M5 required that none
occurs. In a hybrid, anchor magnets of the turning layer pass corner–edge magnets of the layer below at 5.8–6.2 mm
and about 64° (`er9_hybrid_pairs.py`: 12 pairs per quarter turn, none at home, the same at every clearance). The rule
is not changed here. Signal 4 is reported as not met for every arm.

**Reported item (computed before the probe):** `er9_hybrid_perp.py` compares, for those 12 pairs along a rigid
quarter turn, the dipole energy the simulation uses with the charge-model energy the tables were built from. Torque
about the turn axis, summed over the pairs: dipole 10.9 mN·m peak, charge model 11.3 mN·m, largest difference
0.39 mN·m (3.5 %); per pair at most 0.10 mN·m (`results/hybrid/perp_c2.json`). INFERENCE: the flagged pairs are a
small modelling error, not a large one; that is not a validation, and accepting the dipole formula for them would be
an amendment of the kind P-60 was, which is the user's decision.

**Changes to selection and reading (the probe's trials, signals 1–3 and the full rehearsal's trials are unchanged):**
- An arm is *eligible* if it meets probe signals 1–3, is complete, and stays within the 20° tilt limit, so that its
  only flag is the perpendicular near pairs. Among eligible arms the one with the lowest median E1-2 turner torque
  gets the full rehearsal (ties to the larger clearance), as before.
- No hybrid arm can be named a candidate for a scored pre-registration under the rules as they stand. The result is
  reported as "meets or misses signals 1 and 2 of the full rehearsal; signal 3 not met (perpendicular near pairs)",
  beside L0, C52 and W3, and the choice goes to the user.

### Part E amendment 3 (fixed 2026-11-22, after the probe, before any Part E full-rehearsal trial): Part E recorded as probe-only
**Decision (P-69: the user's "Can you just begin", 2026-11-22, read as accepting decision U7's recommended default in
`proposals/PART_G_FINAL.md`; P-67 item 7).** The hybrid is not in contention. Part E ends with its 318-trial probe. The
full 204-trial rehearsal in Part E's selection rule is not run.

**Reason (independent of the probe's outcome; every item existed before the probe finished):**
- P-67 item 1 chose Part G (M5's 48 plus on-axis core pairs) as the direction, and W3 is not taken forward.
- P-67 item 3 made real-mechanism fit a criterion for any new candidate.
- Part E's anchors use W3's geometry, which does not fit the real-mechanism CAD (`side_checks/realfit/`).
- Amendment 2 already rules out naming a hybrid arm a candidate under the rules as they stand.

**Order of events, disclosed.** The decision was taken after the probe results were reported (SUMMARY.md, Part E,
`ad29442`). U7's recommended default, with the reasons above, was written on 2026-11-21, before the probe finished.

**What stays as fixed.** The probe's trials, signals 1–4, the eligibility rule, the self-check and the records are all
unchanged. The probe is reported in full, per arm, beside L0, C52 and W3 (SUMMARY.md, Part E), including the arm the
rule would have selected (HB3, reported only) and its turner torque against L0.

**What is not claimed.** There is no result on Part D's three signals for any hybrid arm. Sequences, drift, abuse trials
and the 60 s rest slip count are unmeasured. Part E's addendum "Reading" does not apply, because no full rehearsal
exists. The probe records are under `results/hybrid/probe/` (`6e722e1`); `results/hybrid/full/` stays empty. If the user
reopens Part E, the full rehearsal runs under Part E's selection rule as fixed and is reported as run after this
amendment.

## Part G — commercial pattern: M5's 48 corner–edge magnets plus attracting on-axis core pairs (addendum fixed 2026-11-22, before any Part G computation)

**Status: fixed on 2026-11-22, before any Part G computation, static or dynamic.** P-67 (2026-11-21) approved the
direction (Part G, static pre-checks first) and the magnet type (b). The user's "Can you just begin" (2026-11-22), in
reply to "reply 'defaults' to accept my recommendations for U1–U8", is read by the main session as accepting every
recommended default below; recorded as P-69, and the user may reverse any of them before the computation it affects is
read. It is committed before its code is run, as Parts A–E were. It is exploratory and unscored: it changes no record and
selects no mechanism. M5 stays NOT PASSED, and no mechanism has passed gate G1. Seeds come only from ER7's rehearsal
range 16000–16999. **Seeds 17000–17999 are never used.**

Labels: `FACT` (file and section given), `INFERENCE` (reasoning or hand arithmetic, not computed by code), `PROPOSAL`,
`TODO` (a number not yet computed, with the script that computes it). Nothing in this part is a result.

> **Decisions taken (P-69: the recommended default in every row; the text below uses them)**
>
> | # | Decision | Taken (the recommended default) | Alternatives not taken (consequences in the section named) |
> |---|---|---|---|
> | **U1** | **Fit policy for Part G (P-67 item 3).** At L0's exact positions the corner magnets have a 0.175 mm wall against 0.4 mm. With C52's core geometry the core cover is 0.20 / 0.29 mm against 0.4 mm (G.6, P3). | **F-A:** keep L0's exact positions and C52's core geometry, report both misses, and require fit only of the configuration taken to a scored pre-registration. An arm that meets every signal is then reported as "meets the rehearsal signals; fit not met", not as a candidate. In parallel (no simulation), source what wall and cover real moulded pieces use. | **F-B:** fit-corrected positions now, with their own validation (no longer L0, outside P-60). **F-C:** thresholds argued from real manufacturing (sources needed; post hoc unless fixed before P3 is read). Consequences: G.6, P3. |
> | U2 | How off-path piece-to-core pairs are judged (review G1) | **Validated deviation:** pre-check P4.d measures how far off a face-turn path the force law stays accurate (D_val). Pairs within D_val are judged at 20° with clamped z allowed; pairs beyond it at 7.5° with no clamped z. | **Strict:** D_val = 0.5° with no P4.d. INFERENCE: E1-5 trials that complete from a misalignment of more than a few degrees would probably fail. **Proxy:** 20° for every piece-to-core pair, as ER7 and C52 had. Validity is then read only as a proxy (P-67 item 8). See G.4. |
> | U3 | Core magnet grade (4×3 mm) | **N52 in both arms.** PG20's core is then exactly C52's, which GS2 checks directly. P2 reports N35 and N42 statically before any dynamics; the user may switch grade then, disclosed. | N35 (lower turner torque; corner+edge cluster stiffness about +14 instead of +230 mN·m/rad, INFERENCE G.2), or both grades (doubles the dynamic cost) |
> | U4 | Repelling-edge variant PG20r (review G5) | **No dynamics.** PG20r appears in P2's static rows only. Reason: B1 has no radial freedom, so in B1 repulsion only adds negative tangential stiffness (G.3). | Add PG20r as a third probe arm (about +50 % probe cost) |
> | U5 | Rest-only extension for statistical power (review G9) | **Include it:** 40 extra 60 s rests on seeds 16700–16739 for L0, PG8 and PG20 (120 trials). Reported only, not a signal. | Leave it out: 20 rest seeds, with which 0/20 against 2/20 cannot be told apart (p ≈ 0.49, INFERENCE) |
> | U6 | ER3 criterion 1 (no single-piece stiffness below −1 mN·m/rad) | **Report only, not a stop** (review GD7). L0 itself fails it and passes 201/204 in rehearsal. Disclosed as a relaxation for this family. | Apply it. INFERENCE: it would stop every arm before any dynamics (G.2). |
> | U7 | Part E (P-67 item 7), as this text reads it | Part E's anchors use W3's geometry, which does not fit the CAD, and fit is now a criterion. So Part E's hybrid is not in contention: **Part E finishes its probe and is recorded as probe-only, by amendment.** Part G does not wait for a Part E rehearsal. | The user keeps Part E in contention, and its rehearsal runs before Part G's dynamics |
> | U8 | Cross-type (4×2 with 4×3) pairs near r2 | **Measure first, then keep P1's rule and treat near cross-type evaluations as out of regime.** Measured (`side_checks/u8_cross_type/`, `be250b7`; FACT): in rigid turns no piece-to-piece cross pair comes closer than 9.335 mm (meets r2 + 1.0 mm), and the rigid-turn cross minimum is 8.176 mm, an edge 4×2 against a **core** `core_edge` 4×3 (PG20 only; hard bound 8.117 mm). The earlier note attributing 8.178 mm to a piece pair was wrong. Point-dipole error for these pairs: vector force 3.4–6.5 % at 8.18 mm, up to 7.4 % at 7.3–7.9 mm. P1's rule is unchanged; `cross_near > 0` stays out of regime (G.4). | Lower P1's margin (not needed on these numbers); accept near cross pairs at the measured error (an amendment of the P-60 kind, not made); move the on-axis piece magnets inward |
>
> **Seed search (G.8, U5), recorded before fixing:** `git grep -E "167[0-3][0-9]"` over `experiments/`, `src/` and
> `tests/` finds no use of seeds 16700–16739 (the only hits are digits inside floats and hashes, and this part's own
> text). D12 reserves 16900–16999 (P-68), so the blocks do not overlap.

### G.0 Prerequisites and order
1. **Composite magnet system (P-67 item 2; built and reviewed separately, not part of this text).**
   - Same-type pairs use their own table, unchanged: M5's 4×2 N35 table and M6's 4×3 N52 table.
   - Cross-type pairs (4×2 with 4×3) use the dipole term only, with the same far taper.
   - A per-trial stat `cross_near` counts every cross-type pair evaluation closer than r2 = 8 mm.
   - It must pass its own review and V4 (momentum), V5 (energy) and V6 (pose-only) before GS1. **Part G adds no
     force-law code.**
2. **Self-checks GS1–GS6 (G.5)**, then **static pre-checks P1–P4 (G.6)**. Statics take minutes, except P4 (TODO).
   They may run whenever the machine is idle.
3. **Dynamic trials** (smoke replays, then the probe, then the full rehearsal) start only when all of these hold:
   - Part E's probe is finished;
   - D12 (P-67 item 5) is not running;
   - no other heavy job is running (FACT: low-memory stops in ER7 deviation 2 and in Part E's probe).
4. Order inside Part G: GS → P1 → P2 → P3 → P4 → smoke and cost check (G.7) → probe (G.8) → full rehearsal of the
   selected arm (G.9). Any stop rule ends that arm, and a stop affecting every arm ends Part G. Each stop is reported
   with its margin.

### G.1 Purpose and question
**Why (FACT unless labelled).**
- L0 (M5's 48 corner–edge magnets, 4×2 mm N35) fails at rest in rehearsal (ER7 SUMMARY):
  - 2 of 20 slip seeds (16003 at 0.568°, 16005 at 0.559°);
  - median turner torque 0.203 N·m with 0 moves at the 1 N·m clip.
- C52 (20 attracting on-axis core pairs, 4×3 mm N52, c = 0.2 mm) holds at rest (3.4e-6°) but fails snap-back in
  10 of 20 trials. Single coaxial pairs leave spin and twist with zero stiffness: 26 zero modes (ER7 post hoc; ER9 Part
  A S2).
- L0's magnets give spin +122 and twist +118 mN·m/rad (ER3).
- Commercial cubes put one core magnet on each corner's own axis, optionally one per edge, always alongside the
  piece-to-piece magnets (`docs/research/CORE_MAGNET_PRACTICE_FINDINGS.md`, Summary and table (a); [S4]).
- On-axis 4×3 piece-to-core paths at c = 0.2 mm are the only core placement whose force-law check passed at every
  turn angle (ER5 V3-turn, real placement; P-58, P-60).
- Under magnet type (b), the 48 magnets are exactly L0 and the 20 core pairs at N52 are exactly C52 (P-67 item 2).
  PG20 is then the union of two configurations that each have 204 ER7 records on the same seeds.

**Question (fixed).**
> On ER7's paired rehearsal seeds, does adding **attracting** on-axis core pairs (4×3 mm, c = 0.2 mm; 8 corner pairs
> or all 20) to M5's own 48 corner–edge magnets:
> - (a) remove L0's rest slips (0/20 D11 slip events and every rest rotation ≤ 0.5°);
> - (b) keep snap-back within 0.5°, which C52 alone failed; and
> - (c) keep every other probe and rehearsal trial passing,
>
> while every magnet pair stays inside the validated regime of its class (G.4)?

Turner torque is reported against the realism reference of about 0.2 N·m, with a warning level at about 0.45–0.5
N·m (P-67 item 4; `docs/research/TURNING_TORQUE_FINDINGS.md`, headline). It is not part of the question and not a
gate G1 criterion. Repelling core pairs are not part of the question (U4).

### G.2 Known in advance (read before the probe)
- **ER3 rejected "M5 + core" statically, in the unbuildable B1 placement.**
  - FACT (ER3 SUMMARY F3, Interpretation 2): edge slide −1441 mN·m/rad at σ = 2, against −1971 for L0 alone.
  - FACT (P-58): that placement is not buildable. The real-placement value is unknown until P2.
- **Stiffness about the face axis (INFERENCE, hand arithmetic; corrected per review G2).**
  - FACT (ER1 REVIEW F4, probe 5, rotation about the face axis): L0's single-piece stiffnesses are −0.93 N·m/rad
    (edge), −0.42 (corner) and −0.42 (corner+edge pair). Under (b) these are the exact L0 values.
  - FACT (ER6 SUMMARY): a real-placement core pair, 4×3 N35 at c = 0.2 mm, gives edge slide +377, cross +370 and
    corner tangential +369 mN·m/rad. These are linear in Br², so ×1.495 for N52.
  - A coaxial pair contributes nothing about its own axis. About the face axis it contributes k·sin²(angle between
    the piece axis and the face axis): 0.5 for an edge (45°) and 2/3 for a corner (54.7°).

  | Arm (superposition; cross-group terms left out) | Edge | Corner | Corner+edge pair |
  |---|---|---|---|
  | PG20, N52 | about −650 | about −50 | **about +230** |
  | PG20, N35 | about −740 | about −175 | about +15 |
  | PG8, N52 | −930 (unchanged) | about −50 | about −50 |
  | PG8, N35 | −930 | about −175 | about −175 |

  - So each single piece probably stays contact-supported, as in L0. Only PG20's corner+edge cluster, which is the
    unit that slips in D11 ("each slip moves a corner and its neighbouring edge … together"), may turn positive, and
    only at N52.
  - ER3's B1 edge slide (−1971) and ER1's −0.93 use different definitions, which are not reconciled here. P2
    computes both.
  - Statics have mispredicted dynamics twice (ER3 passed C52; Part A's peak missed W3's stall). P2 guides; the probe
    decides.
- **Snap-back (INFERENCE).** Core pairs add zero to spin and twist (FACT, ER3/ER6). L0's +122 / +118 should remove
  C52's 20 spin and twist zero modes, leaving 6 (the centres). P2 checks this.
- **Turner torque (INFERENCE).** C52 alone had median 0.645 N·m and 69 moves at the clip (ER7). PG20 at N52 is
  likely to exceed the 0.45–0.5 N·m warning level. PG8 is likely closer to L0.
- **Part E** finished its probe and is recorded as probe-only (amendment 3). Its numbers are not used by any Part G rule.

### G.3 Magnet system and arms
**Common to all arms (FACT, ER7 PROTOCOL; unchanged).**
- B1 cube, implicitfast at 0.5 ms, piece gap 0.05 mm, contacts, turner (1 N·m limit), and setup draw.
- Composite magnet system (G.0):
  - 48 × 4×2 mm N35 at M5's positions (`magnets.layout(pitch 19 mm, gap 0.05 mm)`) with M5's validated table;
  - core pairs from `magnets.core_layout(MagnetParams(4 mm, 3 mm, grade), clearance = 2e-4)`, with M6's N52 table
    (or the exact Br² rescaling for another grade, U3);
  - real radii 22.04 / 21.95 mm. Magnets have no collision geometry (P-58 abstraction).

| Arm | Magnets | Composition | Code needed (none in `src/` beyond the composite) |
|---|---|---|---|
| **PG8** | 64 | L0's 48 + the 16 corner entries of `core_layout()` (8 corner pairs) | Layout wrapper: filter the corner entries |
| **PG20** | 88 | L0's 48 + all 40 entries of `core_layout()` = L0 ∪ C52 at N52 | Layout wrapper (list concatenation) |
| *PG20r* (U4; static rows only by default) | 88 | as PG20, with the 12 edge **piece** magnets' moments reversed, so each edge repels its own core magnet | Layout wrapper |

- **No 4×3 stand-in control.** The draft's H0 is dropped: under (b) the 48 magnets are L0, and GS1 shows that ER7's
  L0 records are reproduced exactly. L0 and C52 are the controls, on the same seeds.
- **Arm names (review G7).** `PG8`, `PG20` and `PG20r` collide with no prefix in `er9_turn_diag.py`, which maps
  `H…` to the old 4×2 hybrid builder and `G…` to Part E (FACT, l.29–36).
  - The Part G runner and the replay tool keep an explicit arm registry and refuse any other name.
  - The committed `er9_turn_diag.py` is not used for Part G arms.
- **Why repelling edges are not run by default (U4).**
  - FACT (findings (a), [S3], [S5], [S7]): some commercial designs repel edge feet from core magnets.
  - INFERENCE: in a real cube that can give a radial preload. B1 pieces have no radial freedom (ER7 correction), so a
    repelling coaxial pair can only add negative tangential stiffness. That works against Part G's purpose (G.2).
  - P-60's wording ("grades by exact scaling") does not explicitly cover reversed polarity. The force law is exactly
    odd in one moment (`magnets.py`, `s = sign(n1·n2)`), so accuracy should transfer (INFERENCE). GS6 checks the
    oddness to machine precision.
  - The GAN 13 pattern (edge feet repelling the corner core magnets) is not modelled: no source gives its geometry.

### G.4 Validated regime by pair class (review G1)
**Classes.** Fixed by static labels: magnet type, and whether a magnet sits on `core` or on a piece. Same-body pairs
are skipped by `MagnetSystem`. "Near" means centre distance r < r2 = 8 mm.

| Class | Members | Validated basis (FACT) | Limit in regime |
|---|---|---|---|
| **CE** | 4×2–4×2 on different pieces (L0's pairs) | M5's V3 record: validated tilt 5° (D8; M5 prereg §1; the 7.5° extension failed, P-24). V3a covers face gaps 0.5–1.5 mm and lateral offsets 0–6 mm | tilt ≤ 5°; no clamped z (\|z\| < 2.1 mm); no perpendicular near pair |
| **PC-on** | 4×3 piece magnet with any 4×3 core magnet, piece magnet on a face-turn path (path deviation d ≤ D_val, below) | P-60: real placement, c = 0.2 mm, 4×3, grades by exact scaling; ER5 V3-turn against all 20 core magnets at θ = 0–90°, tilts within r2 18–20°. **PG8 only if P4.0 passes** | tilt ≤ 20°; clamped z allowed; no perpendicular near pair |
| **PC-off** | as PC-on, with d > D_val | P-60: "poses far from a single-face-turn trajectory still fail"; generic tilted-pair validation 7.5° (ER5 V3b) | tilt ≤ 7.5°; no clamped z (\|z\| < 3.1 mm); no perpendicular near pair |
| **PP3** | 4×3–4×3 on two different pieces | ER5 V3b, 7.5° | tilt ≤ 7.5°; no clamped z; no perpendicular. INFERENCE: never near in rigid face turns (closest about 14.5 mm) |
| **X** | 4×2 with 4×3 (cross-type) | none: dipole term only (G.0) | **no near evaluation at all** (`cross_near` = 0) |

**Path deviation d (computable from one magnet's pose; review G1's "cannot be computed").**
- The core is fixed, and a piece magnet lies on its piece's radial line in every pose. So a piece-to-core pair
  depends only on the piece magnet's unit direction n, and the turn history does not matter.
- ER5's V3-turn swept n over the circle {n · e_k = cos β0}: β0 = 45° for edges, arccos(1/√3) = 54.74° for corners.
- The 20-magnet and 8-magnet cores are invariant under the cube's symmetry group. INFERENCE: every arc of every circle
  \|n · e_k\| = cos β0, k ∈ {x, y, z}, is then equivalent to the validated arc.
- **Definition:** d(n) = min over k of \|arccos(\|n · e_k\|) − β0\|, in degrees, for the piece magnet of the pair.
  - d = 0 exactly in any rigid face turn of any piece in any slot.
  - Slice moves would give d = 45° (edges); the rig makes none.
- **D_val** is fixed before any dynamic trial (U2):
  - default: P4.d's result;
  - "strict": 0.5°;
  - "proxy": D_val = ∞, so PC-off is empty. Signal 4 and rehearsal signal 3 are then labelled "proxy, not P-60
    compliance".

**Rules by experiment (M4 prereg §2, rules 2–3, unchanged; FACT, `E4_scored_m4/run.py` l.89–90).**
- **Operational trials** (E1-1, E1-2, E1-3, E1-4, E1-5, E1-5s, E1-6a): a trial with any out-of-regime evaluation in
  any class **fails**. It is not excluded and not rerun.
  - E1-5 starts are on-path: a layer offset about its own axis keeps d = 0.
  - Off-path poses arise only while the second turn pushes the offset layer back. INFERENCE (rigid approximation):
    up to about 8.6° for a corner and about 1.2° for an edge at an 11.6° offset. P1 computes this.
- **Abuse trials** (E1-6b, E1-6c, E1-6t): an out-of-regime evaluation is logged, and the trial is labelled "magnet
  model outside validated range". It does not fail the trial by itself.

**Per-trial rule (one function, used by the probe, the full rehearsal and the report).**
`out_of_regime` is true if any of the following holds:
- `CE_max_near_tilt_deg > 5`, or `CE_clamped_z > 0`, or `CE_near_perpendicular > 0`;
- `PCon_max_near_tilt_deg > 20`, or `PCon_near_perpendicular > 0`;
- `PCoff_max_near_tilt_deg > 7.5`, or `PCoff_clamped_z > 0`, or `PCoff_near_perpendicular > 0`;
- `PP3_max_near_tilt_deg > 7.5`, or `PP3_clamped_z > 0`, or `PP3_near_perpendicular > 0`;
- `cross_near > 0`.

**New stats the runner must log per trial** (diagnostic `er9g_stats.py`; reads only p and n inside the callback, after
the unchanged force evaluation; GS4 shows that it changes no physics field).
- For each class K in {CE, PCon, PCoff, PP3, X}:
  - `K_near_evals`;
  - `K_near_perpendicular`;
  - `K_max_near_tilt_deg`;
  - `K_clamped_z` (z_min = L + 0.1 mm of the class's magnet type);
  - `K_min_centre_distance_mm`.
- `PC_max_path_dev_deg`: the largest d over PC near evaluations.
- `PC_max_path_dev_deg_clamped`: the largest d over clamped PC evaluations.
- `D_val_deg`: the value in force.
- The composite's own `cross_near`.
- The legacy aggregate `MagnetSystem.stats` (`max_near_tilt_deg`, `near_perpendicular`, `clamped_z`), so that ER7's
  20° proxy flag can also be reported for comparison with ER7 and Part E (review X1).
- One shared diagnostic serves every new dynamic run that needs per-class flags (review X1). D12 should reuse it.

### G.5 Self-checks (before any Part G static result is read or any arm trial is run)
Each check must show 0 differences outside run metadata and the arm-naming and table-naming fields (`er7_arm`,
`mechanism`, `magnet_table`, `er9_arm`, `er9`, `wall_s`, `er7_wall_s`, `loadavg_start`). A failure stops Part G
until it is explained and recorded as a deviation.
- **GS1, L0 exactly (P-67 item 2).**
  - Setup: the Part G runner with the composite system, only the 48 4×2 magnets installed.
  - Check: it reproduces ER7's L0 records for the first trial of each of the ten sub-experiments (E1-1 (60 s
    instrumented rest), E1-2, E1-3, E1-4, E1-5, E1-5s, E1-6a, E1-6b, E1-6c, E1-6t).
- **GS2, C52 exactly (P-67 item 2).** The same, with only C52's 40 4×3 N52 magnets installed, against ER7's C52
  records.
- **GS3, layout lists (static).**
  - PG20 = `layout()` + `core_layout()`, PG8 = `layout()` + the corner entries, and PG20r = PG20 with the 12 edge piece
    moments negated.
  - Bodies, positions and directions are exactly equal to the direct lists.
  - Magnet counts are 88 / 64 / 88; pair counts are as in G.11.
- **GS4, diagnostic is stats-only.** One PG20 E1-2 trial (seed 16120) run with and without `er9g_stats.py` gives
  identical records in every physics field.
- **GS5, static path.** `er9g_static.py` through the composite energy:
  - 48-only reproduces ER3's L0 row to 1e-9 (the ER3 function, 4×2 table) and ER1's probe-5 values (−0.93 / −0.42 /
    −0.42 N·m/rad) to their reported precision;
  - 40-only reproduces Part A's S1 (ER6's N52, c = 0.2 mm row, 1e-9) and S2 (26 zero modes; collective twist below
    1 mN·m/rad).
  - `er9_screen.full_matrix` hard-codes the 4×3 parameters and spline (review G12), so the 66 × 66 path for mixed
    types is new code. That is why it is self-checked here.
- **GS6, polarity and path deviation.**
  - The pair energy with one moment reversed equals minus the original to 1e-12 relative (all classes).
  - d(n) evaluates below 1e-9° for every piece magnet in rigid face turns of all six faces at 1° steps.

### G.6 Static pre-checks, each with its stop rule (any listed failure stops that arm)
**P1, kinematic scan** (`er9g_scan.py`, new; reuses `er9_hybrid_pairs.scan` geometry; TODO).
- Coverage: per arm, rigid turns of each of the 6 faces from −90° to +90° in 0.5° steps.
- Measured per class:
  - near evaluations and perpendicular near pairs;
  - largest near tilt;
  - clamped-z count;
  - smallest centre distance;
  - smallest surface clearance between real cylinders (ER6's sweep method);
  - largest d.
- **E1-5-like rigid poses (reported only).** U offset by ±α, α = 1°…20° in 1° steps, then a rigid R turn from 0° to
  90°. Same measures, including the largest d for PC near pairs and any cross-type near pair. These poses ignore
  contacts, so they bound what E1-5 could reach and do not predict it.
- **Stop an arm if, in any rigid face turn:**
  - a perpendicular near pair occurs in any class;
  - a CE tilt exceeds 5°, or a CE pair is clamped;
  - a PP3 pair is near;
  - a PC tilt exceeds 20°;
  - a cross-type pair comes within r2, or the cross-type piece-to-piece minimum is below r2 + 1.0 mm;
  - or two magnets intersect.
  - Margin reason (INFERENCE): pieces tilt by at most about 0.7° (ER7 rest diagnostic: worst piece 0.71°). At a
    29 mm radius that moves a magnet by about 0.35 mm, or about 0.7 mm for two pieces.
- **Core-to-4×2 bound (review G3, restated under (b); INFERENCE, hand arithmetic).**
  - B1 pieces rotate only about the centre and the core is fixed, so every magnet's radius is invariant.
  - 4×2 magnets sit at r ≥ 28.057 mm (edges; corners 29.006). Core magnets sit at r ≤ 19.94 mm.
  - So every core-to-4×2 pair stays ≥ 8.117 mm apart in **any** pose: a hard bound, 0.117 mm outside r2.
  - P1 recomputes it from the layout radii and stops the arm if it is below r2.
  - The draft's HC20 case (8.02 mm in rigid motion, 7.98 mm bound) does not exist under (b).
- **Expected (INFERENCE, hand arithmetic; P1 decides):**
  - closest cross-type piece-to-piece pair: a corner's axis magnet to a middle edge's 4×2 face magnet, 9.34 mm at 0°
    and 90° of a U turn;
  - the own piece-to-core pair is clamped from about 15.8° to 18.3° of separation, largest near tilt about 18.3°
    (ER7 C52: 18.42°, FACT);
  - CE facing pairs keep tilt 0 in rigid turns;
  - expected outcome: both arms pass P1.

**P2, stiffness** (`er9g_static.py`, new; ER3's and ER1's functions through the composite energy; TODO).
- Rows: PG8 and PG20 at N52 and at N35 / N42 (U3), PG20r at N52, and reference rows L0 and C52 (GS5).
- Measured:
  - ER3's single-piece stiffnesses (edge spin, slide and cross; corner twist and tangential);
  - layer stiffness, and the U-turn profile and peak;
  - the 66 × 66 eigenvalues and the collective-twist stiffness;
  - ER1's probe 5 (edge, corner, corner+edge pair about the face axis).
- **Stop an arm if** more than 6 eigenvalues have |λ| < 1 mN·m/rad, or if the collective twist is ≤ 1 mN·m/rad.
  - INFERENCE (review G12): with L0's spin and twist of about +120, this can trigger only through an error. **P2 is
    in effect report-only**, and a trigger is investigated as a possible bug before anything else runs.
- **Reported, not a stop (U6):** negative eigenvalues, and negative single-piece or cluster stiffnesses (ER3
  criterion 1 waived for this family; disclosed).

**P3, fit** (numbers only, from committed side-check results and the TODO reruns below. The CAD mesh licence is
unconfirmed, so no geometry is committed. P-67 item 3: measured CAD numbers only).

| Item | Value | Source |
|---|---|---|
| On-axis piece magnet, 4×3 (both arms) | fits: wall ≥ 0.4 mm at γ = 0 for edges (feasible 0–16.5°) and corners (0–5.5°) | FACT, `realfit/stage5_sizes_and_gaps.log` "gamma_wall>=0.4" rows; ER4 REPORT §2 |
| L0's 48 at their simulated positions, measured as 4×3 | fully inside every piece; outer-face wall **0.425 mm (edges), 0.175 mm (corners)**; 0.4 mm only after a 0.354 / 0.419 mm shift (mapping B) | FACT, `realfit/stage4_m5_positions.log` summary lines |
| Same for M5's own 4×2 | INFERENCE: the same outer-face walls, because `layout()` puts the outer face `wall` behind the piece face whatever the length. The lateral and inner walls are larger | `magnets.layout` l.107, l.114; **TODO** rerun `stage4_m5_positions.py` with a 4×2 position set (`dump_positions.py`) |
| Why the corner wall is thin | INFERENCE: 0.175 + 0.425 + 0.25 (CAD piece gap) = 0.85 mm = 0.05 + 2 × 0.4, the simulated face gap. At identical magnet positions, the CAD's wider piece gap is taken entirely from the corner's wall. The magnetic geometry is the same in both | `stage4`; side_checks README ("CAD's piece gap is 0.25 mm") |
| Core cover at c = 0.2 mm, measured at the cylinder rim | **0.202 (edge), 0.292 (corner) mm** for a single ball of radius 21.735 mm; 0.307 / 0.397 at 21.84; 0.367 / 0.457 at 21.9 | FACT, `realfit/stage2b_core_gaps.log` (the anchored set; INFERENCE: on-axis is the same, because the rim radius depends only on R, c and the magnet size) |
| What 0.4 mm is | the simulation's own `MagnetParams.wall` default ("face gap = piece gap + 2 × wall"), not a manufacturing figure | FACT, `magnets.py` l.72 |
| On-axis piece magnet to the same piece's 4×2 magnets | centres about 7.92 mm (corner) and 8.59 mm (edge) apart (INFERENCE, hand) | **TODO** `realfit/fitlib.cyl_cyl_gap` |
| Core-to-core spacing, on-axis | centres 12.05 mm (corner–edge at 35.3°; review "checked and correct") | **TODO** surface gap, `fitlib.cyl_cyl_gap` |
| Commercial reference | no teardown gives pocket wall, gap or core-magnet size; GAN 17's ball core is 17.5 mm | FACT, CORE_MAGNET_PRACTICE_FINDINGS (b) |

- **Hard stop (all options):** a magnet protrudes from its piece or core volume, or any two magnets have a surface gap
  below 0.5 mm, or two magnets overlap.
- **The two known misses (corner wall 0.175 mm; core cover 0.20 / 0.29 mm) under U1:**
  - **F-A (default).**
    - What happens: reported and not a stop. An arm that meets every signal is reported "fit not met". Before any
      scored pre-registration the user chooses F-B or F-C for the configuration taken forward.
    - Gains: L0's and C52's exact reproduction (GS1, GS2), P-60's validated geometry, and the paired comparison with
      ER7 are kept. The mechanism question is answered first, inside the validated regime.
    - Costs: fit is deferred. If F-B is chosen later, Part G's dynamics do not transfer, and a new validation and
      rehearsal follow (about one probe plus one rehearsal; INFERENCE G.11). P-67 item 3's "candidate" is read as
      "the configuration taken to a scored pre-registration". That reading is the user's.
  - **F-B (fit-corrected positions now).**
    - What changes: the corner–edge magnets move to the CAD's face-relative positions (mapping B). INFERENCE: axial
      face gap about 0.25 + 2 × 0.4 = 1.05 mm, plus lateral changes (TODO from stage4 mapping B). Core magnets are
      recessed until the rim cover is ≥ 0.4 mm with a single ball.
    - Consequences:
      - not L0, so a new L0-fit control arm is needed and ER7's records cannot be reused;
      - weaker corner–edge pairs (TODO pull at the new gap);
      - M5's table only within V3a's 0.5–1.5 mm / 0–6 mm (TODO);
      - a core face gap above 1.0 mm, outside ER5's V3-turn and therefore outside P-60;
      - before any dynamics are read beyond a proxy: an ER10-type V3-turn at the new gap, and P1–P4 rerun on new
        positions. This is effectively a new Part.
  - **F-C (thresholds argued from real manufacturing).**
    - What changes: 0.4 mm is replaced by a sourced minimum wall and cover for moulded magnet pockets (or flush or
      exposed magnets, if sources show that is common).
    - Consequences: needs a sourced literature or teardown search first (not found in the repository). A threshold
      chosen after these misses were seen is post hoc and must be disclosed, unless it is fixed before P3 is read. If
      the sourced value is ≤ 0.175 mm, both misses pass without moving any magnet.

**P4, force-law checks modelled on ER5's V3-turn** (`ER5_magnet_validation/er5_checks.py` V3-turn function with a
reduced core set and displaced trajectories; new wrapper `er9g_v3turn.py`; TODO).
- Settings: 4×3 N35 table. By exact Br² scaling the relative pass is grade-invariant (M6 S1; INFERENCE).
- Comparison: the hybrid law against the fine charge model, 32 × 96 for pairs within r2 and 6 × 16 beyond.
- Pass rule (ER5's, unchanged), at every θ:
  - force error ≤ 5 % of the 4×3 N35 facing-pair normal force at 1.0 mm (1.92 N);
  - torque error ≤ max(5 % of the largest fine torque along that trajectory, 2e-5 N·m).
- **P4.0, the 8-pair subset (P-67 item 8; required for PG8).**
  - Setup: real placement, c = 0.2 mm, core set = the 8 corner core magnets. One U-layer corner piece magnet rotated
    about U at θ = 0°, 1°, …, 90°. PG8 has no edge piece magnets.
  - Reported beyond ER5: the error of each pair within r2 separately (own core magnet; others), the largest tilt
    within r2, and pairs beyond 45°.
  - **Stop PG8 if it fails at any θ.**
  - ER5's 20-magnet V3-turn covers PG20's core (P-67 item 8). It is not repeated.
- **P4.d, off-path accuracy (U2 default; both arms; their own core sets).**
  - Setup: for each piece kind in the arm (PG20: edge and corner; PG8: corner), the piece magnet direction is
    displaced from its validated circle by d ∈ {0.5, 1, 2, 4, 8, 12}°, toward and away from the turn axis, then swept
    θ = 0–90° about that face axis.
  - Why this family: displacement then a sweep about the face axis is exactly the rigid E1-5 family (an offset about
    one axis, then a turn about another keeps n · e_k constant). The 12° upper value covers E1-5's completion bound of
    11.6° (FACT, M1 prereg E1-5 "completes at ≤ 11.6°").
  - Order: increasing d, halting at the first failing d.
  - **D_val** = the largest d at which every grid point with displacement ≤ d passes, for that arm.
  - **Stop the arm if D_val < 0.5°.** Ordinary turns would then be off-path.
  - Budget: 8 h of summed run time. If the budget is reached, D_val is the largest d already completed and passed.
  - Under U2 "strict" or "proxy", P4.d is not run.
- Cost: TODO from ER5's `run_log.txt`. Exclude the 530 s table build if `ER5_magnet_validation/tables/` is still
  present (review G12).

**If both arms stop in P1–P4,** Part G ends with each arm's failing check and margin, and no dynamics.

### G.7 Smoke replays and the cost stop rule (reported; they change no arm, signal or selection rule)
- **Replay tool.** One replay tool with an explicit arm registry (review X3; shared with D12 if D12 has built it).
  Before use it reproduces the committed `turn_L0_s16100.json` and `turn_C52_s16100.json` through the composite, with
  48-only and 40-only respectively.
- **Per arm:**
  - one single-turn replay (seed 16100, the first U of an E1-2 trial);
  - one snap-back replay (seed 16568, +8°, ER7's `posthoc/snap_diag.py` method).
- **Reported:**
  - peak turner torque and the fraction of steps at the 1 N·m clip;
  - per-class stats, and the largest d;
  - U error after 1 s, and each piece's leftover rotation about its own radial axis (C52: 1.40–1.74°, FACT);
  - steps/s;
  - peak resident memory per process (`/usr/bin/time -v`, in WSL; review G6).
- References (FACT, ER9 PROTOCOL Part E table and amendment 2):
  - L0: 0.461 N·m, 0 steps at the clip;
  - C52: `turn_C52_s16100.json` (TODO, read the peak);
  - W3: 1.000 N·m, 4.3 % of steps at the clip.
- **Cost stop rule (review G6), fixed now.** From the measured steps/s, project the summed per-trial wall time of the
  probe (with U5's extension if chosen) and of each full rehearsal. **Stop and return to the user if:**
  - the projected probe exceeds **24 h**; or
  - either full rehearsal exceeds **35 h**; or
  - peak memory × workers would leave less than 2 GB free.
- **During the probe:** after 25 % of its trials, the projection is repeated with measured `wall_s`. If it exceeds the
  same limits, the probe pauses after the trials in flight, and the user decides.
- "CPU-h" in this part means summed per-trial wall time (`wall_s`), as in the gap analysis.

### G.8 Probe (Part B design)
- **Trials:** ER7's list and seeds, 106 per arm (212 for PG8 and PG20):
  - E1-1 rest (20), now with **D10's instrumented 60 s rest** (review G9); the scored 10 s metric is unchanged;
  - E1-2 quarter turns (24);
  - E1-5s snap-back (20);
  - E1-5 forgiveness (42).
- **U5 extension (default included).** Rest-only trials (E1-1 configuration, 60 s instrumented) on seeds
  **16700–16739** for L0, PG8 and PG20: 120 trials.
  - The seeds are unused by ER7 (16000–16655). A repository search for 16700–16739 must be recorded before this text
    is fixed (TODO; `git grep`). D12 must avoid this block.
- **Runner:** `er9g_run.py` (new), built like `er9_hybrid_run.py`, with the Part G arm registry.
  - It refuses to start unless GS1–GS6 and the arm's P1–P4 passed, and unless D_val is recorded.
  - Records are created exclusively, so the run resumes after an interruption. Each trial runs in a fresh worker.
  - Records go to `results/hybrid_g/probe/<arm>/` and `results/hybrid_g/rest40/<arm>/`.
- **Probe signals (fixed now; ER7's criteria):**
  1. E1-5s: every scored trial passes (|error| ≤ 0.5° after 1 s, from release offsets of 3° or more).
  2. E1-1: every rest rotation ≤ 0.5° **and** 0/20 D11 slip events over 60 s.
  3. E1-2 and E1-5: every trial passes.
  4. No operational trial out of regime under G.4's per-trial rule, with the D_val in force. All probe trials are
     operational.
- **Reported (pre-declared, not signals):**
  - **Turner torque, against the realism reference (review G10):** median, p99 and max per move; moves above
    0.45 N·m, above 0.5 N·m, and at the 1 N·m clip. Shown beside L0 (full-run median 0.203), C52 (0.645), W3 and
    Part E's arms on the same seeds.
  - **Paired rest rotation** against L0 on the 20 seeds: the count of seeds where the arm is lower, with a sign test.
  - **Slip seeds over 60 seeds** (20 probe + 40 extension), each arm against L0: counts with 95 % Clopper–Pearson
    intervals and a one-sided Fisher exact test.
    - Pre-declared reading: p ≤ 0.05 and fewer slip seeds than L0 = "fewer slips than L0 in rehearsal"; otherwise
      "not distinguishable".
  - Rest on L0's slip seeds 16003 and 16005.
  - Snap-back errors, gravity sag (largest tangential leftover), per-class stats, the largest d, steps/s.
  - The legacy 20° proxy flag (comparability with ER7 and Part E).
- **Selection (fixed now).** Among PG8 and PG20 (and PG20r if added), take the arm that meets all four signals with
  the lowest median E1-2 turner torque. Ties go to fewer magnets. If none meets all four, Part G ends with the probe
  report and the next step goes to the user. Fit does not enter selection: both arms share the same misses.

### G.9 Full rehearsal of the selected arm, and reading
- **Trials:** ER7's full list and seeds: 204 trials (E1-1 to E1-6, E1-5s, E1-6t), seeds 16000–16655, D10's
  instrumented 60 s rest in E1-1.
  - The 106 probe trials are rerun inside it. They must reproduce the probe's pass flags, rest and snap-back values
    (reported as a check).
  - Records go to `results/hybrid_g/full/<arm>/`.
- **Signals (ER7's three, with G.4's per-class validity):**
  1. 0/20 E1-1 slip events (D11) and every rest ≤ 0.5°.
  2. M5's Option A rule over the 204 trials, with E1-6m ⟨P⟩.
  3. No operational trial out of regime (G.4). Abuse trials are labelled, not failed (rule 3).
- **Analysis:** `er9_full_analyze.py ARM --root results/hybrid_g`, beside L0 and C52 (and W3). For PG20 the
  attribution is direct: PG20 is L0 ∪ C52 on the same seeds. Turner torque is reported as in G.8.
- **Reading (fixed now).**
  - **All three met, no move at the clip:** reported as "meets the rehearsal signals", **not as a candidate.** It is
    put to the user with what it still lacks for a gate G1 path:
    - fit (U1; under F-A, the F-B or F-C choice);
    - turner torque against the realism reference;
    - independence from selection (fresh seeds, a scored pre-registration and reviews);
    - E1-7 coverage, including the 1.5× ideal-magnet arm (gap analysis A6);
    - the composite system's review status;
    - the lateral-offset disclosure (G.10).
  - **All three met, with moves at the clip:** reported beside W3; the choice goes to the user.
  - **Signal 1 missed:** INFERENCE, the static warning of G.2 holds. Reported against L0 trial by trial, with the
    60-seed slip comparison.
  - **Signal 2 missed in E1-5s:** reported with each piece's leftover spin, against L0 and C52.
  - **Signal 3 missed:** reported by class and by d.
    - If only PC-off or X evaluations caused it, accepting them would be an amendment of the P-60 kind, which is the
      user's decision. It is not made here.
  - **Any miss:** the negative result is kept and reported (CLAUDE.md).

### G.10 Limits
- **Rehearsal only.** ER7's seeds have been used for diagnostics and for earlier selections, and this part reuses
  them again (gap analysis C2; review X4). Twenty rest seeds give wide intervals: 0/20 has a 95 % upper bound of
  17 % (FACT, ER7 PROTOCOL).
- **P-58 abstraction:** magnets have no collision geometry and sit at real radii inside B1 pieces. B1 has no radial
  freedom, so magnetic preload, and with it the commercial use of repelling magnets, has no counterpart.
- **Force-law coverage.**
  - CE: M5's 5°.
  - PC on-path: P-60, plus P4.0 for PG8.
  - PC off-path: D_val from P4.d, otherwise 7.5°.
  - X pairs: dipole only.
    - INFERENCE: beyond r2, same-type pairs get no near-field correction either, so X pairs beyond 8 mm are treated
      as every pair is.
    - Near X pairs are counted as out of regime and were never validated.
- **Lateral offsets (review G11).** Corner–edge pairs crossing a turning boundary pass lateral offsets of 6–8 mm.
  V3a covers 0–6 mm. M5 had the same gap at the same positions. Disclosed, not a new rule.
- **L0's own largest near tilt in ER7 was 12.59°** (FACT, ER7 SUMMARY), above CE's 5°.
  - INFERENCE: it came from abuse trials (rule 3), because no L0 operational trial failed rule 2 in ER7 (its three
    failures are named there).
  - TODO: confirm from ER7's L0 records (`magnet_outside_validated_range` and `rule3_label` by sub-experiment) before
    the probe is read. PG arms are expected to carry the same labels.
- **Numerics.** implicitfast at 0.5 ms has a bounded energy oscillation of about 10 % with core magnets (FACT, M6
  SUMMARY). The ideal-magnet caveat (up to 1.5×) carries over, and no derated arm is included.
- **Fit (U1).** Under F-A, Part G's geometry is L0's and C52's, not the CAD's. Commercial dimensions are unknown
  (findings (b)).
- **Statics guide; the probe decides** (G.2).

### G.11 Resources (machine shared and memory-limited)
**FACT (recorded).**
- ER7, 204 trials, summed trial wall time: L0 10.5 h (48 magnets), C52 9.5 h (40). Run: 408 records in 9,593 s at
  8 workers.
- W3: 22.8 h summed (7,117 s wall).
- One E1-2 trial (`B_s16120`): L0 24 s, C52 21 s, W3 42–66 s, and Part E's HB1–HB3 547–675 s (not explained; machine
  load likely, not checked). The Part E figures are operational timing read from the log of the probe while it was
  still running, used only for the cost estimate; they are not a Part E result.

**Pair counts on different bodies (INFERENCE, hand count; GS3 checks them).**

| Arm | 4×2–4×2 | 4×3–4×3 | Cross-type (dipole only) | Total |
|---|---|---|---|---|
| L0 | 1,092 | — | — | 1,092 |
| C52 | — | 590 | — | 590 |
| PG8 | 1,092 | 92 | 744 | 1,928 |
| PG20 | 1,092 | 590 | 1,872 | 3,554 |

**Estimates (INFERENCE; the smoke replays replace them).**
- PG20 ≈ L0 + C52 + cross-pair overhead: full rehearsal **20–35 h**.
- PG8: **12–18 h**.
- Probe (106 trials with 60 s rests): about 0.2–0.3 of a full rehearsal (TODO: per-experiment sums of `wall_s` over
  `results/full/W3`). That gives PG20 about 4–10 h and PG8 about 2.5–5 h.
- U5 extension: about 2–5 h.
- Probe total with the extension: about 9–20 h, or about 3–5 h wall at 4 workers.
- P1–P3: minutes (Part A screened 243 layouts in 29 min, FACT by git log; geometry was run for 4 rows only).
- P4: TODO, with an 8 h cap for P4.d.
- Self-checks: 20 trials (about 1 h summed, INFERENCE from ER7 means). Smoke replays: under 1 h.

**Proposal.**
- 4 workers by default (at most 6), and fewer if peak memory × workers would leave less than 2 GB free.
- Only when Part E, D12 and other heavy jobs are not running (review X7).
- The runner resumes from existing records, so a low-memory stop loses at most the trials in flight (FACT: ER7
  deviation 2; Part E's stops lost no records).

### G.12 Code to write
All of it lives in `experiments/ER9_anchored_core_layouts/`. It is committed with this part before any Part G run. It
changes nothing in `src/` beyond the separately reviewed composite system, and touches no frozen path.

| Script | Purpose | Kind |
|---|---|---|
| `er9g_layouts.py` | PG8, PG20 and PG20r lists; arm registry; GS3 | Wrapper (lists only) |
| `er9g_stats.py` | Per-class stats and path deviation d from p and n after the unchanged force call; GS4, GS6 (d part) | Diagnostic (forces untouched) |
| `er9g_scan.py` | P1 (6 faces, ±90°, classes, clearances, d, E1-5-like poses, core-to-4×2 bound) | Static |
| `er9g_static.py` | P2 and GS5 through the composite energy; ER3's and ER1's functions; grade rows; GS6 (polarity) | Static |
| `er9g_v3turn.py` | P4.0 and P4.d around `er5_checks.py`'s V3-turn (reduced core, displaced circles) | Static (force-law check) |
| `er9g_run.py` | `selfcheck`, `probe`, `rest40`, `report`, `full`; registry; refusals; the per-trial rule of G.4 | Wrapper |
| Replay tool | Arm registry; self-checked on the committed L0 and C52 turn files (shared with D12) | Diagnostic |

### G.13 TODO: numbers this text does not compute (no process was run)

| Number | What computes it |
|---|---|
| P1 per arm: classes, perpendicular pairs, tilts, clamped counts, distances, clearances, d; E1-5-like poses; the 9.34 mm and 8.117 mm figures | `er9g_scan.py` |
| P2 rows (PG8, PG20 at N35 / N42 / N52; PG20r; L0; C52) | `er9g_static.py` |
| 4×2 walls at L0's positions; on-axis-to-4×2 and core-to-core surface gaps | `realfit/stage4_m5_positions.py` (4×2 set via `dump_positions.py`); `realfit/fitlib.cyl_cyl_gap` |
| P4.0 and P4.d (D_val per arm); their cost | `er9g_v3turn.py`; ER5 `run_log.txt` timings |
| C52's smoke peak at seed 16100 | read `results/probe/diag/turn_C52_s16100.json` |
| Probe-to-full cost ratio | per-experiment sums of `wall_s`, `results/full/W3` |
| Steps/s and peak memory per arm | smoke replays (G.7) |
| L0's 12.59° by sub-experiment | ER7 L0 records (`magnet_outside_validated_range`, `rule3_label`) |
| Seed search for 16700–16739 | `git grep` over `experiments/**` (recorded in the commit message) |
