# Proposal: drift and rest criteria for a cube with per-piece play

**Status: revision 3, approved 2026-11-15 (user: "all approved") on condition of a third independent review (P-28).
It is not in force until that review requires no changes.**
- Revision 2 was approved on 2026-11-16 (user: "all approved"), on condition that a second independent review passed.
  That review (§7) required changes, so per the condition revision 2 is **not in force**. Revision 3 makes those
  changes and goes back to the user.
- It would take effect only inside a **new** pre-registration for a future mechanism, approved before that
  mechanism's first scored trial. **It never applies to M4.** M4 is judged on M1's criteria as registered (P-23 to
  P-26).

## 1. Why (FACT; P-26, `D8_alignment/results/diag_m4_2026-11-15/SUMMARY.md`)
- **M1's two criteria measure single pieces.** Non-target drift is the largest rotation, over a move, of *any*
  non-target piece about the turn axis ("**all** non-centre cubies", M1 pre-registration line 59; `scored.py:263–292`).
  Rest rotation is implemented as the largest rotation of any piece within a face layer (`scored.py:331`).
- **M1 was a wedged cube.** Its 1 N radial preload gave a drift median of 0.013°.
- **A rigid-radius cube has play.** Its pieces rock in their clearance: B1 drift median 0.83° without magnets and
  0.88° with them, at 0.2 mm. M1's metric counts pieces settling *toward* square as drift.
- **Text/code mismatch in M1 (disclosed).** M1's registered text defines rest rotation as "rotation of any **layer**"
  (line 65), while the code measures any **piece**. The code also measures only the 6 face layers.

## 2. Principle
Keep M1's per-piece limits. Grant **one bounded allowance**: a piece may additionally move toward square by at most
half of the criterion's threshold. Every other kind of motion is limited exactly as in M1:
- motion away from square;
- motion across square;
- coherent layer motion;
- shear between pieces;
- chatter at rest.

## 3. Definitions

### 3.1 Measurement (common to all criteria)
- **Snapshots.** *Pre* is the pose sampled immediately before the pads close, as M1's `r0`. *Post* is after the pads
  have opened and settled, as M1's `r1` (`scored.py:252, 258`).
- **Δᵢ** is piece *i*'s signed twist about the turn axis from pre to post, computed by M1's own
  `rotation_about_deg` (unwrapped relative rotation; no lattice reference).
- **a₀,ᵢ** is piece *i*'s signed twist about the same axis of its world-frame lattice error
  (`R·Lᵀ`, `d8_1b_stage1.py:105`) at *pre*.
- **a₁,ᵢ = a₀,ᵢ + Δᵢ.** It is never re-derived from the lattice at *post*, so the 45° wrap cannot occur.
- **Away-motion.** It is `max(0, |a₁| − |a₀|)` when a₀ and a₁ have the same sign. It is `|a₁|` when they have
  opposite signs (crossing square).
- **Rest uses the rotation-vector norm.** For rest the same quantities are computed per piece as the norm of the
  relative rotation from t = 0, which covers all three axes (review change 7). The lattice errors are taken at
  t = 0.
- **Sampling.** Rest is sampled every 10 physics steps (5 ms at the 0.5 ms timestep), fixed in the pre-registration.

### 3.2 Criteria (moves: E1-2 to E1-4, every non-target non-centre piece)
| ID | Definition | Threshold |
|---|---|---|
| **D-T: Total piece motion** (replaces M1 drift as the pass criterion) | \|Δᵢ\| | **≤ 1° + min(\|a₀,ᵢ\|, 0.5°)** |
| **D-A: Directional drift** | away-motion of piece *i* | **≤ 1°** |
| **D-L: Layer drift** | For each non-target layer (middle slice: 4 edges; opposite layer: 8 pieces), \|mean Δ\| | **≤ 1°** |
| **D-S: Shear** | For each non-target layer, max \|Δᵢ − mean Δ\| | **≤ 1.5°**, absolute; does not depend on θ_play |

### 3.3 Criteria (rest: E1-1; every non-centre piece; all 9 layers, including the 3 middle slices)
| ID | Definition | Threshold |
|---|---|---|
| **R-T: Total piece motion** (replaces M1 rest rotation) | max over the 10 s of the rotation-vector norm of piece *i*'s rotation since t = 0 | **≤ 0.5° + min(\|e₀,ᵢ\|, 0.25°)**, where e₀ is the norm of its lattice error at t = 0 |
| **R-A: Directional rest motion** | max over the 10 s of max(0, \|eₜ\| − \|e₀\|), with eₜ the lattice-error norm (wrap-safe at these angles) | **≤ 0.5°** |
| **R-L: Layer rotation** | For each of the 9 layers, max over the 10 s of \|mean twist of its non-centre pieces about the layer axis\| | **≤ 0.5°** |
| **R-S: Settling** | Per piece, the sum of the rotation-vector norms of the 5 ms increments over the **last 5 s** (path length) | **≤ 0.5°**. The first 5 s are covered by R-T and R-A |

**Reported with equal prominence:** M1's per-piece drift and rest rotation, computed exactly as M1 does, for every
trial.

### 3.4 Applicability (objective, measured before any scored run)
- **Configuration:** the scored configuration (rig, magnets on if the mechanism has them), pads open, after a 0.5 s
  settle.
- **Test:** one corner and one edge, each about each of the 3 axes and in both directions. A 0.02 N·m torque (the D1
  test torque) is applied by a logged test wrench, ramped over 1 s and held for 1 s.
- **Reported:** the one-sided rotation in each direction and the total range.
- **Qualifies as a play mechanism** if the total range is > 0.5° (M1's rest limit) for some piece class and axis.
- **Upper limit:** no one-sided rotation may exceed **1.5°**, the largest total motion D-T allows. A mechanism with
  more free play than the criteria permit as motion cannot qualify.

### 3.5 Unchanged
Every other M1, M4 and P-24 criterion is unchanged: turn error, penetration, the radial and pop checks, causality,
open-pad rotation, the E1-4 growth slope < 0.005°/move, E1-5s, E1-6m, E1-6t, magnet validity, Option A and the
integrity rules.

### 3.6 New numbers, listed honestly
- **The allowance** c = half of the criterion's threshold: 0.5° for moves, 0.25° for rest. One rule.
- **D-S at 1.5°**, equal to D-T's maximum.
- **R-S:** the 5 s window and the 5 ms sampling interval.
- **Applicability:** the 0.02 N·m test torque, the 0.5° entry line and the 1.5° upper limit.
- **Measurement changes:** rest measured with the 3-axis norm, and over 9 layers.

All other thresholds are M1 values.

## 4. Integrity safeguards
1. **Post hoc, disclosed.** These definitions were written after M4 failed M1's per-piece criteria.
2. **M1's result is reported with equal prominence** for every mechanism scored under these definitions. Near-copies
   of M4 (B1 + magnets at another gap) count as M4-derived.
3. **G1 sign-off rule.** A mechanism that passes these criteria but fails M1's needs the user's explicit sign-off at
   the G1 gate, recorded with that fact stated (review change 8).
4. **Fault-injection unit tests.** Each scripted fault must **fail** the criterion named:

| Scripted fault | Must fail |
|---|---|
| Single piece dragged 1.5° away from square | D-A |
| Slice edges counter-rotating ±1.5° from square | D-T |
| Coherent slice rotation 1.1° | D-L |
| One piece −0.9° → +0.9° (crossing) | D-T (1.8 > 1.5) |
| Carried-over error: one piece −2.5° → +0.9° | D-T |
| Subset drag: 3 of 8 pieces −0.9° → +0.9° | D-T |
| Rest: piece −0.9° → +0.45° within the first 5 s | R-T (1.35 > 0.75) |
| Rest: oscillation ±0.4° in the last 5 s | R-S |
| A 90° turn plus 0.3° as a non-target motion (wrap check) | D-T |
| A fault just above each threshold, and one just below | fails above, passes below |

5. **Controls on unscored seeds.** M1's configuration must pass (positive control). The candidate geometry with a
   scripted marginal drag of 1.2–2° (a logged test wrench on one non-target piece during a move) must fail (marginal
   negative control on the candidate itself).

## 5. Work required before any pre-registration uses this
- **W1:** the free-play measurement script (§3.4).
- **W2:** the metric implementation, with M1's metrics kept beside it.
- **W3:** the fault-injection tests (§4 item 4).
- **W4:** the controls (§4 item 5).

## 6. What is already known (disclosure)
- **Four moves examined** at 5 ms resolution (0.1 mm gap, B1 + magnets):
  - the largest |Δ| was 1.13°, by a piece that started 1.10° off square, so its limit is 1.5° and it passes D-T;
  - the drifting pieces moved toward square, so D-A passes;
  - non-target layer means changed by ≤ 0.19°.
  - INFERENCE: those moves would pass. This is not known for whole trials.
- **Rest.** In rest_s7000 (0.1 mm), one piece's error norm grew 0.82° → 1.46°, and the largest piece rotation
  was 0.90°. INFERENCE: it would fail R-A and R-T.
- D-S, R-S and the applicability test have not been evaluated on any data. B1's free play under §3.4 is not known
  (D1's 12° figure came from a different test, corner twist).

## 7. Independent reviews (P-20 subagents; neither was given the disclosure section)
- **Review 1, of revision 1: ACCEPTABLE WITH CHANGES.**
  - The layer mean plus a 2° per-piece cap passed single-piece drags of 1.5–3° and shear.
  - 2° was a new number: it is M1's layer-mean tolerance.
  - Revision 2 adopted the six required changes.
- **Review 2, of revision 2: ACCEPTABLE WITH CHANGES.**
  - **Counterexamples that passed revision 2 but fail M1:**
    - a crossing drag −0.9° → +0.9°;
    - a carried-over error −2.5° → +0.9°;
    - a subset drag;
    - an early rest crossing.
  - **Defects:**
    - lattice wrap at 45°;
    - frame and measure ambiguity;
    - D-S was gameable through a declared θ_play;
    - R-S was sampling-dependent and blind to the first 5 s;
    - the applicability test had no upper limit and no defined configuration.
  - **Required changes, all adopted in revision 3:**
    1. a total-motion bound → D-T and R-T;
    2. unwrapped a₁ in the world frame with named snapshots → §3.1;
    3. an absolute D-S → 1.5°;
    4. R-S fixed in sampling and measure, with early rest motion covered → §3.1 and R-T;
    5. an applicability configuration with an upper limit → §3.4;
    6. fault tests for every counterexample, plus a marginal negative control → §4 items 4–5.
  - **Optional changes, both adopted:** the 3-axis norm for rest, and G1 sign-off.
- **Revision 3 has not been reviewed.**

## 8. Decisions requested
1. Approve revision 3 (yes / no / modify).
2. A third independent review before it is used (recommended, since revision 3 adds new numbers).
3. W1–W4 are needed only once a candidate mechanism is chosen.
