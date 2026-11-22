# ER9 — anchored core-magnet layouts: summary

**Status:** exploratory and unscored. Every trial used ER7's rehearsal seeds (16000–16999). Nothing here is a
VALIDATED_RESULT for gate G1, and no scored seed (17000–17999) was touched. Protocol: `PROTOCOL.md` (Parts A–E, each
part and amendment committed before its runs). Parts A–D are complete; Part E is in progress. The decision-log row
for ER9 will be proposed when Part E is complete.

## Outcome in brief
- **The problem.** No cube mechanism passes G1. M5's 48 corner–edge magnets (L0) fail on small slips at rest. The
  single core pairs of ER7 (C52) hold at rest but do not snap a displaced layer back.
- **Why C52 failed (FACT, ER7 post hoc and Part A's self-check S2).** One magnet pair on a piece's own axis gives no
  stiffness against that piece spinning about the axis. All 26 pieces can spin together with no contact and no
  restoring torque (26 zero modes in the stiffness matrix).
- **The idea tested here.** Hold each edge with two pairs and each corner with three, set off the piece's axis, each
  pair pointing radially. That anchors every piece in all three rotations.
- **Result 1 (Parts A–D).** The anchored layout removes both known failures. Arm W3 (N35 at strength 0.3) passed
  **204 of 204** rehearsal trials and met all three of ER7's signals; L0 passed 201 and C52 194 on the same seeds.
- **The catch.** With W3 the turner reached its 1 N·m limit in 771 of 1,376 moves (L0: 0). The layer stalls briefly at
  about 7° into a turn, then breaks through.
- **Result 2 (diagnostics, Part E).** The stall is not caused by the anchors: it is there, and worse, with almost no
  magnets. INFERENCE from single-turn replays: M5's corner–edge magnets suppress it (L0's pieces lag at most 0.21°).
  Part E therefore tests both together.
- **Part E status:** probe interrupted and incomplete; no result yet (see the Part E section below).

## Part A — static screen (243 layouts)
- Layouts: edges on their axis or split into 2 pairs at 14–20° toward the centres or the corners; corners on their
  axis or split into 3 pairs at 10–16° toward the edges or the centres; grades N35, N42, N52; 4 × 3 mm magnets at
  0.2 mm clearance.
- Criteria fixed beforehand: spin and twist stiffness ≥ 100 mN·m/rad; smallest non-centre eigenvalue of the full
  66 × 66 stiffness matrix ≥ 50; magnetic U-turn peak ≤ 0.5 N·m; layer stiffness ≥ 1 N·m/rad; magnets of different
  pieces ≥ 8 mm apart; near-pair tilt ≤ 20°.
- Self-checks passed: S1 reproduces ER6's numbers exactly; S2 finds C52's 26 zero modes and a collective twist
  stiffness of about 0; S3 passes.
- **3 of 243 pass.** Selected (lowest U-turn peak): N42, edges 2 pairs at 20° toward the centres, corners 3 pairs at
  16° toward the centres, 96 magnets.

| Quantity (selected layout) | Value |
|---|---|
| Edge: spin / slide / cross stiffness | +106 / +803 / +884 mN·m/rad |
| Corner: twist / tangential stiffness | +100 / +1,277 mN·m/rad |
| Layer stiffness | 5.27 N·m/rad |
| Magnetic U-turn peak | 0.338 N·m |
| Zero modes | 6 (the centres, which carry no magnets) |
| Smallest other eigenvalue; collective twist | 99; 4,881 mN·m/rad |
| Closest magnets of different pieces; clearance | 10.36 mm; 0.82 mm |
| Largest near-pair tilt | 18.2° |

## Parts B and C — 106-trial probes (E1-1, E1-2, E1-5, E1-5s)
Wrapper self-check: ER7's C52 records reproduced exactly (after deviation 1, a bookkeeping field).

| Arm | Layout | Trials passed | Snap-back max error | Rest max | E1-2 turner median | Moves at the 1 N·m limit (of 24) |
|---|---|---|---|---|---|---|
| L0 (ER7) | M5's 48 magnets | 104 (E1-1 18/20) | 0.27° | 0.568° | 0.144 N·m | 0 |
| C52 (ER7) | single core pairs, N52 | 96 (E1-5s 10/20) | 1.01° | 3.4e-6° | 0.70 | 4 |
| S1 | anchored, N42 | 106 | < 0.001° | 1.1e-6° | 1.0 | 20 |
| S2 | anchored, N52 | 106 | < 0.001° | 7.6e-12° | 1.0 | 20 |
| W1 | anchored, N35 × 1.0 | 106 | < 0.001° | 1.5e-5° | 1.0 | 20 |
| W2 | anchored, N35 × 0.5 | 106 | < 0.001° | 0.0027° | 1.0 | 16 |
| W3 | anchored, N35 × 0.3 | 106 | 0.028° | 0.011° | 0.947 | 9 |

- "Snap-back max error" in this table is over all 20 snap-back trials, including the unscored ±1° and ±2° starts;
  the Part D table below uses only the scored starts (|Δ| ≥ 3°). L0 is 0.269° by the first definition and 0.118° by
  the second; C52 (1.013°) and W3 (0.028°) are the same under both.
- All five anchored arms met the four probe signals. None was flagged (largest near tilt 18.42°, no perpendicular
  near pair). The runner checks signal 4 through ER7's regime flag only; its other clause, "no piece-to-piece near
  pair", holds for these arms by geometry (magnets of different pieces stay ≥ 10.36 mm apart in every face turn).
- By the selection rule fixed beforehand (lowest median E1-2 turner torque), W3 went to the full rehearsal.

## Part D — full 204-trial rehearsal of W3

| Experiment | L0 | C52 | W3 |
|---|---|---|---|
| E1-1 rest | 18 / 20 | 20 / 20 | 20 / 20 |
| E1-2 single moves | 24 / 24 | 24 / 24 | 24 / 24 |
| E1-3 half turns | 22 / 22 | 22 / 22 | 22 / 22 |
| E1-4 long sequences | 39 / 40 | 40 / 40 | 40 / 40 |
| E1-5 misaligned starts | 42 / 42 | 42 / 42 | 42 / 42 |
| E1-5s snap-back | 20 / 20 | 10 / 20 | 20 / 20 |
| E1-6a / b / c / t abuse | 6, 6, 8, 16 | 6, 6, 8, 16 | 6, 6, 8, 16 (all passed) |
| **Total** | **201 / 204** | **194 / 204** | **204 / 204** |
| E1-6m moves oracle-correct | 1,376 / 1,376 | 1,376 / 1,376 | 1,376 / 1,376 |

| Signal (ER7's three) | L0 | C52 | W3 |
|---|---|---|---|
| 1. No slip seed in E1-1 and rest ≤ 0.5° | no (2 seeds, 0.568°) | yes (3.4e-6°) | **yes** (0 seeds, 0.011°) |
| 2. M5's Option A rule over 204 trials | no | no | **yes** |
| 3. No trial outside the validated regime | — | yes | **yes** (max tilt 18.42°) |

| Reported | L0 | C52 | W3 |
|---|---|---|---|
| Turner torque: median / 99th percentile / max (N·m) | 0.203 / 0.563 / 0.870 | 0.645 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 |
| Moves at the 1 N·m limit | 0 | 69 (37 trials) | **771 (68 trials)** |
| Non-target drift per move: median / max | 0.231° / 0.776° | 0.191° / 0.831° | 0.045° / 0.119° |
| Snap-back max error | 0.118° | 1.013° | 0.028° |
| Summed trial wall time | 10.5 h | 9.5 h | 22.8 h |

- The 106 probe trials were reproduced inside the full run (same pass flags, same rest and snap-back values).
- Paired with L0 on the same seeds, W3 has lower rest rotation in 20 of 20 trials and lower sequence drift in 85 of
  86, and higher peak turner torque in 86 of 86.

**Reading (as fixed in Part D).** All three signals are met, so the anchored layout is a candidate for a scored
pre-registration, with what it still lacks listed under Limits. The turner saturation is the reason I did not stop
there.

## Part E — hybrid: M5's 48 positions plus weak anchors (in progress; no result)
- **Arms.** HB1, HB2, HB3: M5's 48 corner–edge positions plus the 96 anchor magnets (144 in all), anchors at 1, 2 and
  3 mm clearance. One magnet type throughout: 4 × 3 mm N35 at strength 0.756, which matches the pull of M5's 4 × 2 mm
  pair (amendment 1; the table used is the one validated to 20° of tilt).
- **Self-check:** passed (W3's probe records reproduced with 0 differences).
- **Smoke replays (seed 16100, first U of an E1-2 trial), before any probe trial:** peak turner torque 0.525, 0.432
  and 0.118 N·m at 1, 2 and 3 mm, no step at the 1 N·m limit (L0: 0.461; W3: 1.0 with 4.3 % of steps at the limit).
- **Known before the probe (amendment 2).** No hybrid arm can meet the validity signal. Anchor magnets of the turning
  layer pass corner–edge magnets of the layer below at 5.8–6.2 mm and about 64°, and the force law corrects near pairs
  only within 45° of parallel. For those 12 pairs the dipole formula the simulation uses is within 3.5 % of the charge
  model in torque about the turn axis (0.39 mN·m of 11.3 mN·m). That is a measured size of the error, not a
  validation. Accepting it would be an amendment of the kind P-60 was, which is the user's decision.
- **Probe status (2026-11-21).** The 318-trial probe has been stopped three times by low-memory stops (other jobs
  were running on the machine): at 75, 223 and 275 of 318 trials. These are not failures of the run. Every record
  present was checked to decompress; the runner skips existing records, so each restart continues where it stopped.
  The partial records are not committed and are not interpreted here.
- **Still to do:** finish the probe; report the signals per arm; run the full 204-trial rehearsal on the eligible arm
  with the lowest median E1-2 turner torque; analysis beside L0, C52 and W3.

## Diagnostics (exploratory; single seeds; `results/probe/diag/`)
- **Snap-back replay (seed 16568, +8°).** S1, S2, W1, W2: no leftover spin on any piece. W3: U error 0.028°, largest
  spin 0.097°.
- **Rest leftovers are gravity sag (FACT).** They match piece weight × lever / tangential stiffness to three digits
  (C52 0.066° and 0.093°; S1 0.041° and 0.040°). Sag grows as the anchors weaken: S1 0.065°, W1 0.078°, W2 0.155°,
  W3 0.229° (largest tangential leftover).
- **The stall (seed 16100, first U of an E1-2 trial).** The layer stops at about 6.7° for about 0.1 s while the
  position-controlled turner winds up to 1 N·m, then jumps forward. Two contacts carry most of the torque: the
  U-layer corners' lower chamfers against the side centres' chamfers (45° normals). The U pieces are tilted 0.3–0.4°
  and lag the turner by 0.6–1.55°, each by a different amount. L0's pieces lag at most 0.21° and its peak is
  0.46 N·m.
- **Strength sweep of the same replay.** Anchors at N35 × 0.1, 0.03, 0.003: peak 1.0, 0.78, 1.0 N·m, and 9.8 % of
  steps at the limit at 0.003. INFERENCE: the stall belongs to the B1 cube without in-layer magnets, not to the
  anchors.

## Corrections to my own reasoning, kept on record
1. **Stiffness target.** I set "spin and twist ≥ 100 mN·m/rad" from a joint-friction argument that seemed to match
   ER7's rest leftovers. Those leftovers are gravity sag. The target was stricter than needed, which narrowed the
   screen to 3 layouts; it did not invalidate the layouts that passed.
2. **Cause of the stall.** In the Part C commit I described the stall as "independent of strength" and suspected the
   anchors' tilting pull. The strength sweep shows it is independent of the anchors altogether.
3. **Part E's first specification** used M5's 4 × 2 table past its validated tilt (5°). Caught by the self-check
   output before any arm trial; see amendment 1.

## Limits
- Rehearsal only: ER7's seeds were used for diagnostics, for choosing the arms and for the rehearsal, so the 204
  trials are not independent of the selection.
- P-58 abstraction: the magnets have no collision geometry and sit at ER4's real-mechanism radii inside the B1 model.
- The force law was validated for coaxial piece-to-core pairs up to 20° of tilt (P-60, ER5). Off-axis anchor pairs
  stay within that tilt range but their placement has not had its own V3-turn check.
- A strength scale (0.3 for W3) is not a catalogue magnet. It stands for a weaker grade, a smaller magnet or a larger
  gap; which one has not been chosen or checked for fit.
- **Fit in a real mechanism: the anchored layout as screened does not fit the real-mechanism CAD (FACT about that
  CAD; `side_checks/realfit/`, measured 2026-11-20).**
  - Corner anchors at 16° lie mostly in air: the corner's material along their line starts at 25.0 mm, while the
    magnet spans 22.35–25.35 mm.
  - Edge anchors at 20° break out of the foot by up to 0.58 mm.
  - In that CAD, three magnets per corner fit toward the centres only as 3 × 2 mm at 5.5–7° or 3 × 3 mm at 5.5–6.5°,
    which is outside Part A's screened range. Edges take 4 × 3 up to 16.5° and 4 × 2 or 3 × 2 at 20°.
  - Whether a feasible placement still holds the pieces has not been computed. A cube designed for these magnets
    could have deeper corner feet; that has not been checked either.
- **Real-magnet equivalents (`side_checks/catalogue/`).**
  - A strength scale multiplies Br², so pair forces go with the scale itself.
  - W3's scale 0.3 at 1.0 mm face gap corresponds to a stocked 3 × 3 N45/N42 at about 1.8–1.9 mm. That magnet has
    no validated force table.
  - The gap is uncertain by about 0.5 mm until pull against gap is measured on real magnets.
- The turner rig is a position servo with a 1 N·m limit; "moves at the limit" is a property of cube and rig together.
- In a turn, each anchor pair of W3 briefly passes through the force law's clamped-z region as it leaves (15.7–18.3°
  of relative rotation, 7.2–8 mm apart, where the near-field weight is ≤ 0.13). ER9 does not report the count.
  **Correction (2026-11-21, from the G1 gap analysis):** an earlier version of this line said P-60 covers it. It does
  not: P-60 accepts clamped pairs only on face-turn trajectories that ER5's V3-turn validated, which were on-axis
  placements at c = 0.2 mm. W3's off-axis anchor paths have had no V3-turn check.
- **What signal 3 shows.** "No trial outside the validated regime" was computed with a 20° tilt limit and the
  perpendicular-pair rule (PROTOCOL.md, Part B criterion 5 and signal 4). The 20° figure comes from ER5's
  V3-turn on the on-axis trajectories; ER5's generic tilted-pair check (V3b) validates the 4 × 3 table to 7.5° only.
  Signal 3 is therefore the protocol's proxy, as Part B's limits say. It is not a validation of the off-axis paths,
  and it is not compliance with P-60. The same applies to Part E: there the hybrid's 4 × 3 corner–edge pairs were
  flagged at 20°, although for that pair type only V3b's 7.5° applies.

## Independent code review (2026-11-20)
A reviewer given the code and protocol, not these results, found nothing that changes a verdict. It confirmed:
- anchor geometry and attraction for all 20 pieces at 0.2–3 mm;
- the configuration reaching every worker, with no leak between arms;
- record bookkeeping and the analysis (L0 and C52 values recomputed from ER7's records);
- the force law's handling of these layouts.

The report's points are dealt with above, under Parts B and C and under Limits. One further point: records are
written without a temporary file. All 112 hybrid probe records present on 2026-11-20 were checked to decompress and
to carry their arm's configuration (144 magnets, scale 0.756).
