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
