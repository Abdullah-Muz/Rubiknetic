# Proposal DRAFT — rounded piece edges instead of the 45° chamfer (NOT APPROVED)

**Status.** This is a draft for the user's decision; nothing here is adopted.
- No model code changes until it is approved.
- When approved, the approval is recorded as a new DECISION_LOG entry.
- Each compute step below is fixed in its own protocol before it runs, as D14's stages were.

## Change request (DECISION_LOG template)

```text
Date / author:     2026-11-24 / drafted in the main session at the user's request ("yes" to "Shall I draft the proposal?")
Affected decision ID(s):
                   the B1 contact-cube base used by M4, M5 (L0) and ER9 Part G (PG8, PG20): P-23, P-31, P-67, P-73–P-75 (D14),
                   and the diagnostics P-76–P-78
Current requirement:
                   every piece is a box (half-size (pitch - gap)/2 = 9.475 mm) with a 45° chamfer of 1.4 mm on every edge
                   (M1Params.chamfer, default 0.0014, chosen to match OpenAI's 1.425 mm on 19 mm cubies)
Proposed alternative:
                   the same box with edges and corners rounded at radius R, built as a faceted fillet (30° facet steps;
                   the first facet meets each face at 15°). Half-size and the 0.05 mm gap are unchanged.
                   R chosen by the rule in §3 (R 2.5 mm preferred, R 1.4 mm fallback).
Reason and evidence:
                   P-76 to P-78 (experiments/D14_noslip_rest_rehearsal/diag_catch/README.md)
Scientific / safety / compute / scope implications:   §2
Alternatives rejected and why:                        §4
User approval (explicit):                             PENDING
Master-spec revision + affected docs:
                   no master-spec change is needed: the spec does not fix the edge shape. Affected documents are
                   DECISION_LOG, the mechanism abstraction write-up, the D14 records' "applies to" notes, and any
                   pre-registration drafted after this
Validation gates that need rerun:
                   G1 rehearsal evidence on the new geometry (§3); M5's final verdict (P-51) is unaffected
```

## 1. Evidence (`FACT`, from P-76 to P-78; unscored diagnostics on rehearsal seeds)

**The failure.**
- The D14 Stage 3b failure (`scr20inv_s16400`) is a jam on a contact catch about 6° past each quarter-turn position: a
  turning-layer corner climbs the adjacent face centre's 45° bevel.
- The catch is caused by the pieces' tilt on their ball joints, against a 0.05 mm gap. Gravity enlarges it on U.
- It adds up to about 0.76 N·m on top of PG20's 0.25 N·m magnet resistance, against a 1 N·m turner limit.
- It occurs in all three designs: L0 R reached 0.74 N·m in one single turn.

**Gap and contact settings do not fix it (P-77).**
- A gap of 0.10 / 0.20 mm makes catches rarer, but the worst stays about 0.7 N·m, and the M4-type drift returns
  (0.20 mm: 24 / 40 moves fail drift > 1°).
- Stiffer small-overlap contacts jam earlier.

**Rounded edges remove it at the 0.05 mm gap (P-78).** R 1.4 mm and R 2.5 mm, against the current chamfer:

| | chamfer | R 1.4 mm | R 2.5 mm |
|---|---|---|---|
| Largest contact torque at the peak, 8 catching single turns | 0.71 N·m | 0.07 N·m | 0.07 N·m |
| `scr20inv_s16400` | jams at move 29 | 40 / 40 pass | 40 / 40 pass |
| Sequence max turner torque | 1.00 N·m | 0.38 N·m | 0.31 N·m |
| Sequence max drift | 0.45° | 0.53° | 0.51° |
| L0 R peak | 0.74 N·m | 0.19 N·m | 0.15 N·m |

- The rounded L0 R peak is close to P-67's realism reference of about 0.2 N·m.

**Real cubes (`UNVERIFIED`).** Secondary sources only, not read in full: about 2–3 mm fillets to stop misaligned parts
jamming, and "corner cutting" of about 45° on a 3x3 (README §4).

## 2. Implications

**What it changes.**
- The geometry of every piece, in all three designs.
- Collision cost: hull vertices go from 24 to 104. This was not measured cleanly. Under similar parallel load, the
  rounded sequences took 1233–1235 s against 1532–1549 s for the gap variants, so there is no sign of a slowdown yet;
  it will be measured in step R1.

**What it does not change.**
- Piece tilt freedom: the ball-joint abstraction is unchanged.
- The contact parameters, the magnets, NoSlip, the rig, or any scoring threshold.
- It adds no force, so P-16 is unaffected.

**Risks to check (`INFERENCE`).**
- A rounded lead-in forgives misalignment. That could change:
  - E1-5: snap-back and forgiveness. PG8 and PG20 currently block +16° to +20° starts, and rounded edges may let more
    turns through.
  - E1-6: abuse and blocking cases.
  - E1-1: rest holding. The flat faces get smaller: R 2.5 mm leaves a 13.95 mm flat square, against 16.15 mm.
- **Magnet fit.** Face-centred magnets (4 mm diameter) sit about 7.5 mm from a piece edge, so R 2.5 mm does not reach
  them. Some layouts in ER9's realfit positions (`anchored_c0.2` in `side_checks/realfit/positions.json`) place magnets
  about 1 mm inside inner faces, near an inner edge. A fit check against each arm's actual layout is required (step R0).

**Records.**
- Every earlier D14 / ER9 rehearsal result applies to the chamfer geometry only. Each keeps a note saying so.
- The 26 Stage 3b records stay as they are.
- Stage 3b on the chamfer geometry would be closed as superseded, not resumed.

**Seeds.** Steps R1–R2 reuse rehearsal seeds 16000–16655, as every earlier choice did; this is disclosed. 19000–19655
(Stage 3c's fresh seeds) and 17000–17999 / 10000–10999 stay untouched.

## 3. Plan, each step behind its own fixed protocol and approval

| Step | What | Cost |
|---|---|---|
| R0 | **Implementation and static checks** (detail below) | no long compute |
| R1 | **Screen**: at NoSlip 10, for L0, PG8 and PG20 at both R 1.4 and R 2.5: E1-1 rest (20 seeds, as Stage 1), E1-5 and E1-5s (as Stage 2), and E1-2 (24 turns). Wall times measured. | about 1–1.5 h on 4 workers |
| R2 | **Full rehearsal** on the selected R: all 204 trials per arm (E1-1 … E1-6t) at NoSlip 10, three arms, with Part G's G.9 signals and reading unchanged. Replaces the chamfer Stage 3b. | about 10 h |
| then | Stage 3c (fresh seeds), 3d (G1 pre-registration) and 3e (scored run), as already planned, on the new geometry | — |

**R0 in detail.**
- Add `M1Params.edge_profile` (`"chamfer"` default, or `"rounded"`) and `edge_radius`.
- With the default, `build_m1_xml` output must be byte-identical. One committed frozen record per arm must reproduce
  exactly.
- Tests:
  - rounded hull extents equal the half-size;
  - the first facet is at 15°;
  - no cubie–cubie contact in the solved pose;
  - composite checks V4–V6 still pass on the rounded geometry.
- The magnet-fit check per arm layout.

**R1 selection rule (fixed here).**
- A radius **meets the screen** if, for all three arms:
  - every E1-1 rest is ≤ 0.5° with no slip event;
  - every E1-5 / E1-5s / E1-2 trial passes;
  - no trial is out of regime;
  - no move reaches the 1 N·m clip.
- Choose R 2.5 mm if it meets the screen; otherwise R 1.4 mm if it does; otherwise stop and report.
- R 2.5 mm is preferred in advance for its larger lead-in and lower torque, and because it is nearer the 2–3 mm the
  secondary sources mention.

## 4. Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Tune the gap | No safe point: 0.10 mm leaves 0.98° drift and 0.99 N·m in one sequence; 0.20 mm fails drift (P-77) |
| Stiffer contacts | Worse (P-77) |
| Raise the 1 N·m torque limit | Hides a contact that is unphysical at 3–5× the realism reference |
| A spring resisting piece tilt | Needs the lattice orientation, close to P-16's forbidden alignment forces |
| Structural retention (feet in a core track) | The proper long-term fix for tilt, but MuJoCo's convex collision cannot represent the curved bearing surfaces (P-15; Drake exploration) |
| Rig stall handling (back off and retry) | Worth doing later, but it is a protocol and scoring change that does not fix the cube |

## 5. Decisions for the user
1. Approve rounded edges as the proposed geometry: yes / no / changes.
2. Approve the R selection rule (R 2.5 preferred, R 1.4 fallback), or fix one radius now.
3. Close the chamfer-geometry Stage 3b as superseded (26 records kept), rather than resuming it.
4. Keep NoSlip 10 and all three arms (L0, PG8, PG20) for R1 and R2.
