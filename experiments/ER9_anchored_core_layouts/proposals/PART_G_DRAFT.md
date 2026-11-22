> **DRAFT — not approved; not a committed protocol.** Drafted by a subagent on 2026-11-21 without running anything.
> Its estimates are hand arithmetic marked INFERENCE.
>
> **Main-session check (FACT, ER3 SUMMARY and DECISION_LOG P-56): this premise was screened before.** In ER3,
> "core σ=2 + L0 (M5 + core)" failed the static screen on edge slide (−1441 mN·m/rad). The B1 placement used there is
> not buildable (ER5). Edge slide is negative for L0 alone too, and L0 still passes most dynamic trials on contacts.
> So the static failure does not decide the question, but any reading of Part G must start from it.

> **DRAFT: not approved, not a committed protocol.** A subagent drafted this on 2026-11-21 without running anything:
> no Python, no simulation, no git change. Numbers marked INFERENCE come from hand arithmetic on formulas in the code
> and on recorded values. Nothing here is fixed until the user approves a version. That version would then be appended
> to `experiments/ER9_anchored_core_layouts/PROTOCOL.md` and committed before any Part G computation, as Parts A–E
> were.

# DRAFT for review: ER9 Part G, commercial-pattern hybrid (piece-to-piece plus on-axis core pairs)

**Status: DRAFT, 2026-11-21. Exploratory and unscored.** It changes no record and selects no mechanism. It uses
ER7's rehearsal seeds only (16000–16655). It never uses seeds 17000–17999. M5 stays NOT PASSED, and no mechanism has
passed G1.

**Labels:**
- `FACT` (file and section given);
- `INFERENCE` (reasoning or hand arithmetic, not computed by code);
- `PROPOSAL`;
- `TODO` (a number this draft could not compute, with the script that would compute it).

Nothing here is a result or a validation.

**Sources read:**
- `CLAUDE.md`;
- `docs/DECISION_LOG.md` (P-56 to P-66, G1 row);
- `docs/research/CORE_MAGNET_PRACTICE_FINDINGS.md`;
- ER3 `SUMMARY.md`;
- ER4 `REPORT.md` §2;
- ER5 `PROTOCOL.md` (V3-turn) and `SUMMARY.md`;
- ER6 `SUMMARY.md`;
- ER7 `PROTOCOL.md` and `SUMMARY.md`;
- ER1 `REVIEW.md` (F1, F4);
- D11 `SUMMARY.md` (grep);
- ER9:
  - `PROTOCOL.md` (Parts A–E with amendments 1–2) and `SUMMARY.md`;
  - `proposals/PART_F_DRAFT.md` and `proposals/G1_GAP_ANALYSIS.md`;
  - `side_checks/README.md`;
  - `side_checks/realfit/stage2b_core_gaps.log`, `stage4_m5_positions.log` and `stage5_sizes_and_gaps.log`;
  - `results/hybrid/scale.json`;
  - `er9_hybrid.py`, `er9_hybrid_run.py`, `er9_hybrid_pairs.py`, `er9_layout.py`, `er9_turn_diag.py` and
    `er9_hybrid_scale.py`;
- `src/rubiknetic/cube_physics/magnets.py`;
- `src/rubiknetic/cube_physics/m1_model.py` (pitch, gap);
- `experiments/PHASE_1_M4_PREREGISTRATION.md` (rules 2–3) and `PHASE_1_M5_PREREGISTRATION.md` (§1 tilt row);
- the `wall_s` field of one E1-2 record (`B_s16120`) per arm.

---

## Summary
1. **Question.** Does adding on-axis core pairs to M5's 48 corner–edge positions keep L0's snap-back and low turning
   torque, and does it remove L0's rest slips, on ER7's paired rehearsal seeds? This combination is the commercial
   pattern. Its two halves fail separately: C52 fails snap-back and L0 slips at rest.
2. **Arms (default 3).** `H0` is M5's 48 positions alone with Part E's 4×3 magnet. It is a control for the magnet
   stand-in. `HC8` is H0 plus 8 on-axis corner–core pairs. `HC20` is H0 plus 20 on-axis core pairs. All are 4×3 N35
   at scale 0.756 with c = 0.2 mm. An optional fourth arm, `HC8r`, adds edge-foot magnets that repel the corner core
   magnets.
3. **No force-law code is needed for the default arms.**
   - Layouts are lists (`layout()` + `core_layout()`).
   - The only new code is wrappers: a corner-only filter, a Part G arm table, a scan script, and a stats-only
     per-pair-class diagnostic.
4. **Strict tilt limits by pair class.**
   - Corner–edge 4×3 pairs: 7.5° (ER5 V3b).
   - On-axis piece-to-core pairs on face-turn paths: 20°, with clamped z allowed (P-60, c = 0.2 mm only).
   - The single 20° flag that ER7 and Part E used cannot tell the classes apart. Hence the diagnostic.
5. **Known in advance (INFERENCE).** At matched strength, the core pairs add only about +285 (edge) and +279 (corner)
   mN·m/rad of tangential stiffness. That is ER6's N35 value × 0.756. L0's single-piece stiffnesses are negative:
   ER1 measured −930 and −420; ER3 measured an edge slide of −1971. **So in statics the hybrid probably stays
   contact-supported, as L0 is.** Only ER1's corner+edge cluster in HC20 might turn positive (−420 + 564). Whether the
   slips stop is a dynamic question.
6. **Geometry (INFERENCE, hand arithmetic; the scan decides).**
   - HC8 can never form a near pair between a core magnet and an M5 magnet. Their radii differ by at least 8.07 mm,
     which is more than r2 = 8 mm.
   - HC20 has one passage per edge-core magnet at 8.02 mm and 74.8°, 0.02 mm outside r2. Perpendicular near-pair
     counts of near-zero weight are therefore likely in its dynamics. That would be a bookkeeping flag of Part E's
     kind, but much weaker.
7. **Pre-checks that stop an arm:**
   - a perpendicular near pair, an over-limit tilt or a clamped piece–piece pair in a rigid face turn;
   - remaining zero modes (more than 6);
   - a hard fit failure;
   - (optional) a failed V3-turn subset check for HC8.
8. **Sequence.**
   - Self-checks first: L0, W3 and C52 records reproduced exactly.
   - Then smoke replays (seed 16100).
   - Then a 318-trial probe (106 per arm, ER7's seeds) with four fixed signals.
   - The selected HC arm then gets a full 204-trial rehearsal.
9. **Cost (INFERENCE, scaled from ER7/ER9 by pair count).**
   - Probe about 6–7 CPU-h.
   - Full rehearsal of HC20 about 20–35 CPU-h, or of HC8 about 15 CPU-h.
   - 4 workers by default, started only after Part E's probe finishes.
10. **Blockers.**
    - ER9 has no decision-log row.
    - Part E's probe is unfinished and uncommitted.
    - The 0.756 scale has no catalogue meaning (Br ≈ 1.03 T).

---

## Decisions for the user (the draft uses the defaults)

| # | Choice | Recommended default | Alternative(s) and trade-off |
|---|---|---|---|
| GD1 | When to fix and run Part G | **After Part E's probe is finished, reported and committed.** Part E is the closest analogue: M5's 48 plus core magnets at 1–3 mm. Its result bears on this part's premise (G1 gap analysis §5 risk 5). Both parts need the same memory-limited machine. | (a) Fix the text now and run after Part E. (b) Run Part G instead of finishing Part E: not recommended, since 43 Part E trials remain and the comparison set would stay incomplete. |
| GD2 | Magnet type (`MagnetSystem` takes one `MagnetParams`, so every magnet in a layout has the same type) | **(a) All 4×3 N35 at scale 0.756, as in Part E amendment 1.** No force-law code. Directly comparable with HB1–HB3. Core pairs at c = 0.2 mm stay in P-60's set, reading "grades by exact scaling" as covering an exact Br² scale. Costs: core strength is tied to corner–edge strength; the corner–edge magnet is a stand-in, hence the H0 control; 0.756 has no catalogue meaning (Br ≈ 1.03 T; gap analysis A5). | (b) **Two types.** M5's own 4×2 N35 (its table, 5°) for the 48, and 4×3 N35–N52 for the core pairs. Needs a composite magnet system in experiment code, with cross pairs dipole-only and flagged if they come within r2. Reproduces ER7's L0 exactly with the core off, so H0 is not needed. Uses catalogue magnets only, and core grade is free at c = 0.2 inside P-60. INFERENCE: with 4×2 the M5 magnets sit at r ≥ 28.06 mm, so no core magnet can ever be near one. It needs code and a review first. **This is what a G1 candidate would need anyway.** (c) Per-magnet σ in one 4×3 system: a smaller code change; core strength becomes free, but the corner–edge stand-in stays. |
| GD3 | Arms | **H0, HC8, HC20** (3 arms; 318-trial probe, the size of Part E's) | Add **HC8r** (GAN 13 pattern: 12 edge-foot magnets repelling the 8 corner core magnets; 76 magnets), or drop H0 (saves about 1.4 CPU-h but loses attribution of any change to the core pairs) |
| GD4 | Core clearance / strength levels | **c = 0.2 mm only.** It is the only clearance whose on-axis paths ER5's V3-turn checked (P-60). Pull per pair 1.454 N (FACT, `results/hybrid/scale.json`, "0.2"), about 0.51 × C52's pull (INFERENCE). | Add c = 1 mm (0.799 N; scale.json). It is outside P-60, so its on-axis pairs fall under V3b's 7.5° and would be flagged in every turn, unless an ER5-style V3-turn at c = 1 mm is run first (about 1 h, TODO `er5_checks.py`). Under GD2 (b) or (c), strength levels can instead be grades at c = 0.2 mm. |
| GD5 | Edge polarity | **Attracting only** (HC20), or no edge core pairs (HC8). Edge pairs that repel their own coaxial core magnet are excluded. In B1 a repelling coaxial pair only destabilises the edge sideways. Any radial preload it might give a real cube has no counterpart in B1, which has no radial freedom (ER7 correction, FACT). | Include an HC20 variant with repelling edges. The force law supports it exactly (see "Polarity"); the physics argues against it. |
| GD6 | Tilt and clamped-z limits per pair class | **Strict:** piece–piece pairs ≤ 7.5° (ER5 V3b, 4×3) with no clamped z; piece-to-core on-axis pairs ≤ 20° with clamped z allowed (P-60; c = 0.2; face-turn paths); no perpendicular near pair. Needs a stats-only diagnostic (new code; forces untouched; self-checked, GS5). | ER7's single flag (any near pair > 20° or perpendicular), as Part E used. No new code, but it does not apply the 7.5° limit to corner–edge pairs (ER9 SUMMARY, "What signal 3 shows"). |
| GD7 | Stop rule on static stiffness | **Stop an arm only if zero modes remain** (more than 6 eigenvalues with \|λ\| < 1 mN·m/rad, or collective twist ≤ 1 mN·m/rad). Negative single-piece and cluster stiffnesses are reported. They are expected: L0 has them and passes 201/204 in rehearsal. | Apply ER3's criterion 1 (no single-piece stiffness below −1 mN·m/rad). INFERENCE: that would stop every matched-strength arm before any dynamics. |
| GD8 | Known fit misses | **Keep M5's simulated positions and C52's core geometry, and report the misses.** Corner wall 0.175 mm (stage4); core cover 0.20 / 0.29 mm (stage2b). This keeps P-60's geometry and comparability with L0, C52 and Part E. | Shift the 48 to the CAD's face-relative positions (0.354 / 0.419 mm) and recess the core magnets (face gap about 1.1–1.2 mm; Part F D3). Fits the CAD, but leaves P-60's c = 0.2 geometry and changes every comparison. |
| GD9 | V3-turn coverage of HC8's 8-magnet core | **Run the subset check P4 before dynamics** (static; `er5_checks.py` V3-turn with 8 core magnets). ER5 compared the force *summed over 20 core magnets*; per-pair accuracy was not shown. | Accept ER5's 20-magnet V3-turn as covering a subset. Saves about 1 CPU-h, but is not strict. |
| GD10 | Seeds | **ER7's 16000–16655**, paired with L0, C52, W3 and HB1–HB3 | Unused rehearsal seeds 16656–16999: not paired, and too few for the full list, which spans offsets 0–655. **Never 17000–17999.** |
| GD11 | Full-rehearsal scope | **Only the selected HC arm** | Also H0 (about 10.5 CPU-h), for paired 60 s slip events and sequences against the stand-in |
| GD12 | Workers | **4** (at most 6), only when no other heavy job runs | 8 (ER7's restart setting), on a free machine only |
| GD13 | Approval route | **Explicit user approval of Part G.** ER9's earlier parts ran under P-63's delegation, and no ER9 decision-log row exists yet. | Treat it as covered by P-63 (the user may reverse). Not recommended: this is a new direction from the user's own research. |

---

## Part G: commercial-pattern hybrid (addendum, DRAFT; to be fixed before any Part G computation)

### G.1 Purpose and question
**Why (FACT unless labelled).**
- L0, M5's 48 corner–edge magnets, fails rest in rehearsal: 2 of 20 seeds, 0.568° and 0.559° against 0.5° (ER7
  SUMMARY). Its turner torque is low: median 0.203 N·m, 0 moves at the 1 N·m limit (ER7).
- C52, 20 on-axis core pairs (4×3 N52, c = 0.2 mm), holds at rest (3.4e-6°) but fails snap-back in 10 of 20 trials.
  Its 26 zero modes come from single coaxial pairs, which have no stiffness against spin (ER7 post hoc; ER9 Part A S2).
- Commercial cubes put one core magnet on each corner's own axis, optionally one per edge, and always alongside the
  piece-to-piece magnets (`CORE_MAGNET_PRACTICE_FINDINGS.md`, Summary; [S4] "usually used alongside standard
  magnetization"). No source shows off-axis core magnets.
- On-axis 4×3 piece-to-core paths at c = 0.2 mm are the one placement whose V3-turn passed, at every θ from 0° to 90°
  (ER5 SUMMARY; P-58, P-60).
- In the real-mechanism CAD:
  - on-axis piece magnets fit (ER4 REPORT §2: feet take coaxial magnets of 5 mm on edges and 6 mm on corners);
  - M5's positions lie inside the pieces, with a corner wall of 0.175 mm (side_checks `stage4`).
- Part E tests M5's 48 plus *off-axis* anchors. That combination has perpendicular piece-to-piece near pairs (Part E
  amendment 2) and does not fit the CAD (side checks). Its probe is unfinished.

**Question (fixed).**
> On ER7's paired seeds, does adding on-axis core pairs (4×3, c = 0.2 mm) to M5's 48 corner–edge positions (a) keep
> snap-back within 0.5°, (b) keep every rest rotation within 0.5°, and (c) keep turner torque near L0's, while every
> magnet pair stays within the force law's validated regime for its class?

### G.2 Known in advance (read before choosing GD7)
- **ER3 already rejected this combination statically, in the unbuildable B1 placement.**
  - FACT (ER3 SUMMARY F3 and Interpretation 2): "core σ=2 + L0 (M5 + core)", edge slide −1441 mN·m/rad, fails.
  - "Keeping M5's corner–edge magnets and adding core magnets does not work at σ ≤ 3. The corner–edge slide
    instability, −1971 mN m/rad, is too strong."
  - FACT (P-58): the B1 placement is not buildable. The real-placement value is unknown (Part F draft, Hybrid family).
- **Real-placement numbers (INFERENCE, hand arithmetic on FACTs).**
  - Core pairs, 4×3 N35 at c = 0.2 mm, give edge slide +377, cross +370 and corner tangential +369 mN·m/rad (FACT,
    ER6 SUMMARY table). These are linear in strength (FACT, ER9 Part C), so at scale 0.756 they are about **+285 /
    +280 / +279**.
  - Cross-check: one pair's lateral stiffness at 0.756 is 583.8 N/m (FACT, scale.json). Times a lever of about 22 mm
    squared, that gives 283 mN·m/rad.
  - L0's destabilising single-piece stiffnesses inside the play:
    - **−0.93 N·m/rad (edge), −0.42 (corner), −0.42 (corner+edge pair)** (FACT, ER1 REVIEW F4);
    - ER3's edge slide is **−1971** (FACT). The two definitions differ; this draft does not reconcile them.
  - Sums, if superposition holds (the energy is a sum over pairs, but cross-group terms are left out):
    - HC20: edge about −645, corner about −141, corner+edge pair about **+144**;
    - HC8: corner about −141, edge unchanged.
  - **So at matched strength the hybrid probably stays contact-supported per piece, as L0 is** (ER1 F1/F4: slips are
    clusters crossing a consolidated gap, driven by this negative stiffness). The exception is HC20's corner+edge
    cluster, which D11 says is the unit that slips: "each slip moves a corner and its neighbouring edge … together".
  - All of these numbers are hand estimates on a 4×2 L0. Pre-check P2 replaces them with computed values for the 4×3
    stand-in.
- **Partial dynamic evidence (FACT as quoted, uncommitted and uninterpreted).** G1_GAP_ANALYSIS §5 risk 5: "HB2 had
  rest 0.516° on L0's slip seed 16005". HB2's anchors pull 0.386 N each (scale.json "2"); Part G's core pairs pull
  1.454 N.
- **Snap-back is expected to be restored (INFERENCE).**
  - L0's corner–edge magnets give spin +122 and twist +118 mN·m/rad (FACT, ER3; ER7 Interpretation 2). Core pairs add
    zero to either (FACT, ER3/ER6).
  - So the 26 zero modes should drop to 6, the centres. P2 checks this.

### G.3 Arms
**Common to all.**
- B1 cube model and every M5/ER7 setting unchanged (implicitfast, 0.5 ms, piece gap 0.05 mm, turner, setup draw).
- Magnets: 4×3 mm N35 at `MagnetParams.scale` = 0.756 (`er9_hybrid.SCALE_M5`). Table: M6's N52 table times the exact
  strength factor (`er9_probe.table_for`), as in Part E amendment 1.
- M5's 48 positions from `magnets.layout(pitch, gap, mp)` (pitch 19 mm, gap 0.05 mm). Core pairs from
  `magnets.core_layout(mp, clearance=2e-4)`, real radii 22.04 / 21.95 mm (P-58 abstraction: no collision geometry).

| Arm | Magnets | Composition | Core pull per pair | Code needed (none in `src/`) |
|---|---|---|---|---|
| **H0** (control) | 48 | `layout()` only. The stand-in for M5's 4×2 magnet; no core pairs | n/a | None: `er9_hybrid.cfg_for(0.2, anchors=False)` already builds it (its docstring says "4x2_M5 only", but the code path works for 4×3) |
| **HC8** | 64 | `layout()` + the 16 corner entries of `core_layout()` | 1.454 N | Wrapper: filter the corner entries (or add an edge option `('none',)` in a Part G helper; `er9_layout.pair_directions` has no such option) |
| **HC20** | 88 | `layout()` + all 40 entries of `core_layout()` | 1.454 N | None for the layout: `cfg_for(0.2, edge_opt=('axis',), corner_opt=('axis',))` |
| *HC8r* (optional, GD3) | 76 | HC8 + 12 edge-foot magnets on each edge's axis at the piece-magnet radius (`u·(R + wall + L/2)`), moment along −u, with no edge core magnet | n/a for the edges | Wrapper: list entries with flipped `dir` |

**Why one core strength (GD4).**
- P-60 accepts clamped piece-to-core pairs only for "real placement, c = 0.2 mm, 4×3 mm, with grades by exact
  scaling" (FACT, P-60).
- With one magnet type, the core strength at c = 0.2 mm is fixed by the scale that matches M5's corner–edge pull
  (FACT, Part E amendment 1: 0.756 ⇒ 1.644 N across 0.85 mm).
- Other strengths need either another clearance (outside P-60) or a code change (GD2 b/c).
- INFERENCE (hand, from the `core_layout` formula):
  - At c = 1 mm, an on-axis pair never clamps: z < 3.1 mm needs φ > 21.8°, where the pair is already 9.4 mm apart.
  - Its largest near tilt would be about 17.3°.
  - But that path has no V3-turn of its own.

**Polarity (FACT from `magnets.py`; INFERENCE on accuracy).**
- The force law handles opposite moments through `s = sign(n1·n2)`. The near-field term is `s·w·C(ρ, |z|, v, μ)` with
  `u = s·n2`. Reversing n2 flips s and leaves u, and therefore C, unchanged. The dipole term is bilinear.
- So the model energy is exactly odd in one moment, and so is the charge-model reference.
- INFERENCE: a repelling pair's error has the same magnitude as the attracting pair's at the same pose, so V3 and
  V3-turn accuracy transfers exactly.
- TODO: a machine-precision check (pair energy with one moment reversed equals minus the original), in the Part G
  static script.

**Which tilt limit applies to which pair (GD6; strict).**

| Pair class | Example | Limit | Basis |
|---|---|---|---|
| Piece–piece, 4×3 (M5's facing corner–edge pairs; any other piece–piece near pair) | U corner's z-face magnet to middle edge's | **7.5°**, no clamped z | FACT: ER5 V3b validated tilt 7.5° for 4×3 (generic tilted pair); V3a covers lateral offsets 0–6 mm |
| Piece-to-core, on-axis, on a single-face-turn path (own core magnet and neighbouring core magnets) | U corner's piece magnet to the U edge's core magnet at 45° | **20°**, clamped z allowed | FACT: P-60 (c = 0.2 mm, 4×3, exact grade scaling); ER5 V3-turn real placement, every θ 0–90°, tilts within r2 reached 18–20° |
| Piece-to-core, off any single-face-turn path (E1-5 offset starts, E1-6 abuse) | — | 7.5° strictly; reported at 20° as ER7 did | FACT: P-60 "poses far from a single-face-turn trajectory still fail". ER7 applied 20° everywhere; this draft reports both |
| Any pair with \|n1·n2\| ≤ cos 45° inside r2 | — | **none allowed** | FACT: force-law design (`magnets.py` docstring; M5 required `near_perpendicular` = 0) |

Rules 2–3 of M4's pre-registration carry over unchanged:
- operational experiments (E1-1 to E1-5, E1-6a): an over-limit trial fails;
- abuse experiments (E1-6b, E1-6c): an over-limit trial is logged and labelled.

### G.4 Static pre-checks (before any dynamic trial; any listed failure stops that arm)

**P1, kinematic scan** (new script `er9g_scan.py`, reusing `er9_hybrid_pairs.scan`; TODO).
- `er9_hybrid_pairs.py` as committed reports only perpendicular pairs, for U only, from 0° to 90°. That is not
  enough here.
- For each arm, rigid turns of each of the 6 faces from −90° to +90° in 0.5° steps. Per magnet-pair class:
  - perpendicular near pairs (r < 8 mm, \|cos\| ≤ cos 45°);
  - largest near tilt;
  - clamped-z count (\|z\| < L + 0.1 mm = 3.1 mm);
  - smallest centre distance;
  - smallest surface clearance between magnet cylinders with real dimensions (ER6's sweep method).
- Also, for E1-5-like poses: U offset by ±5°, ±10° and ±20°, then a rigid R turn from 0° to 90° of the pieces in R.
  This is an approximation of E1-5 and is reported only.
- **Stop an arm if, in any rigid face turn:**
  - a perpendicular near pair occurs;
  - a piece–piece near tilt exceeds 7.5°, or any piece–piece pair is clamped;
  - a piece-to-core near tilt exceeds 20°;
  - or two magnets intersect.
- **Expected (INFERENCE, hand arithmetic; pieces rotate about the cube centre, so each magnet keeps its radius):**

  | Quantity | Value |
  |---|---|
  | Magnet-centre radii (`layout`, `core_layout`) | piece on-axis 23.94 (edge) / 23.85 (corner); core 19.94 / 19.85; M5 4×3 edge 27.92, corner 29.21 mm |
  | Core to M5 magnet, lower bound (radius difference) | corner core: ≥ 8.07 mm, so **never near**. Edge core to M5 edge magnet: ≥ 7.98 mm |
  | HC20, closest core-to-M5 passage in a rigid U turn | U edge's x-face magnet at (±7.575, 19, 19) passes the edge core magnet at (0, 14.10, 14.10): **8.02 mm at 74.8°, about 21.7° into the turn**. Outside r2 by 0.02 mm in rigid motion, so dynamics may bring it inside, at a near-field weight of about 0 |
  | Piece on-axis magnet to another piece's M5 magnet | closest in a rigid U turn: U corner's axis magnet to the middle edge's upper z-face magnet, **9.65 mm at 0° and 90°** |
  | Piece-to-core | own pair: clamped from about 15.8° to 18.4°, largest near tilt 18.4° (matches ER7's C52: 18.42°, FACT); corner piece magnet to edge core magnet at 45°: 5.4 mm, 9.7° (findings (e)3) |
  | M5's facing corner–edge pairs | tilt 0 in rigid turns: all facing pairs across a layer boundary are along the turn axis. Centre distance 3.85 mm > 3.1 mm, so not clamped |

  So H0 and HC8 are expected to pass P1 cleanly. HC20 is expected to pass in rigid motion with a 0.02 mm margin. In
  the probe, HC20 may record perpendicular near-pair evaluations at a weight of about 0. Under the rules as written
  they would fail signal 4. **This is decided now, not after the probe:** they count. Accepting weight-zero pairs
  would be a rule change of the P-60 kind, which is the user's decision. GD2 (b) removes the case (INFERENCE: 4×2
  edge magnets sit at r = 28.06 mm, at least 8.12 mm from any core magnet).

**P2, stiffness** (new script `er9g_static.py`, importing `er9_screen.py`'s functions unchanged, plus ER1's probe-5
function from `ER1_rest_slip_review/er1_probe_magnet_stiffness.py`; TODO).
- For each arm:
  - ER3's single-piece stiffnesses (edge spin, slide and cross; corner twist and tangential);
  - layer stiffness and the U-turn profile and peak;
  - the full 66 × 66 stiffness matrix and its eigenvalues;
  - the collective-twist stiffness;
  - ER1's probe 5 (one edge, one corner, a corner+edge pair, each rotated inside its play about the face axis).
- Per-magnet σ exists in `er9_screen` (static only). The script also reports the core σ at which each negative mode
  reaches 0. It is reported only, and informs GD2 (c).
- **Stop an arm if:**
  - more than 6 eigenvalues have \|λ\| < 1 mN·m/rad (a spin or twist mode left free);
  - or the collective twist is ≤ 1 mN·m/rad.
- **Reported, not a stop under GD7's default:** negative eigenvalues and negative single-piece or cluster stiffnesses.
  A negative diagonal entry implies a negative eigenvalue (Rayleigh quotient), so L0-like modes will show up here.
- Reference rows: L0 (4×2, ER3 function) and C52 (Part A S2: 26 zero modes).

**P3, fit** (numbers only, from committed side-check results; no mesh is opened; CAD licence unconfirmed).

| Item | Value | Source |
|---|---|---|
| On-axis piece magnet, 4×3 | fits: wall ≥ 0.4 mm at γ = 0 for edges (range 0–16.5°) and corners (0–5.5°) | FACT, `stage5` "gamma_wall>=0.4" rows; ER4 REPORT §2 (5 / 6 mm magnets fit the feet) |
| M5's 48 at simulated positions, 4×3 | inside every piece; walls 0.425 mm (edges), **0.175 mm (corners)**; 0.4 mm only if shifted 0.354 / 0.419 mm | FACT, `stage4` summary lines |
| Same for M5's own 4×2 | INFERENCE: same outer-face wall. `layout()` puts the outer face `wall` behind the face whatever the length | `magnets.layout` |
| Core cover, single ball of radius 21.735 mm at c = 0.2 | **0.20 mm (edge), 0.29 mm (corner)** against the 0.4 mm assumed | FACT, `stage2b` "anchored_c0.2". INFERENCE: applies on-axis, since the rim radius depends only on R and c |
| Core-magnet spacing, on-axis | INFERENCE: closest core magnets, corner to edge at 35.3°, are about 12.0 mm apart centre to centre | TODO `realfit/fitlib.cyl_cyl_gap` |
| On-axis piece magnet to the M5 magnets of the same piece | not measured (`stage4`'s ≥ 3.99 mm is for the S1 anchors). INFERENCE: centres 7.76 mm (corner) and 8.12 mm (edge) apart | TODO `fitlib.cyl_cyl_gap` |

- **Stop an arm if:** any measured surface gap is < 0.5 mm, or two magnets overlap.
- The two known misses (0.175 mm corner wall; 0.20 / 0.29 mm core cover) are reported per GD8 and do not stop.

**P4, V3-turn subset for HC8 and HC8r** (GD9; `ER5_magnet_validation/er5_checks.py`'s V3-turn with only the 8 corner
core magnets; TODO).
- Same pass rule as ER5: at every θ, force error ≤ 5 % of the facing-pair normal force at 1.0 mm, and torque error
  ≤ max(5 % of the largest fine torque, 2e-5 N·m).
- Cases: edge and corner trajectories of the real placement, at c = 0.2 mm.
- For HC8r: the edge trajectory with reversed edge moments.
- **Stop HC8 or HC8r if it fails.**
- Cost INFERENCE: ER5 took 4,523 s for all its checks, including a 530 s table build. This subset is roughly a
  quarter of that.

**If every HC arm stops in P1–P4,** Part G ends. It reports each arm's failing check and margin, with no dynamics.

### G.5 Self-checks (before any arm trial; each must show 0 differences outside run metadata and arm-naming fields)
- **GS1, L0.** The hybrid path with M5's 4×2 magnet and anchors off reproduces ER7's L0 records for the first E1-2 and
  first E1-5s trials. This is Part E's first self-check, repeated (`results/hybrid/selfcheck_run1_4x2.json`).
- **GS2, W3.** The hybrid path with base off, scale 0.3, c = 0.2 and S1 anchors reproduces W3's Part C probe records
  for the same two trials. This is Part E amendment 1's self-check, repeated (`results/hybrid/selfcheck.json`).
- **GS3, C52.** The Part B wrapper (`er9_probe`) with C52's layout reproduces ER7's C52 records for the same two
  trials, as Part B did.
- **GS4, layout lists (static).**
  - H0 = `layout()`.
  - HC20 = `layout()` + `core_layout(mp, 2e-4)`.
  - HC8 = `layout()` + the corner entries of `core_layout()`.
  - Bodies, positions and directions are exactly equal.
  - Also: HC20 built through `cfg_for(0.2, edge_opt=('axis',), corner_opt=('axis',))` equals the direct list.
- **GS5, stats diagnostic.** One HC20 E1-2 trial run with and without the per-class diagnostic gives identical
  records in every physics field. This shows the diagnostic does not touch forces.
- **GS6, static path.**
  - Part A's S1 (C52 row = ER6's N52 c = 0.2 row, to 1e-9) and S2 (26 zero modes; collective twist < 1 mN·m/rad),
    rerun through `er9g_static.py`.
  - The polarity check under G.3.

A failure stops Part G until it is explained and recorded as a deviation.

### G.6 Smoke replays (reported; they change no arm, signal or selection rule)
- One single-turn replay per arm: seed 16100, the first U of an E1-2 trial, `er9_turn_diag.py` method (TODO: a Part G
  arm option; its arm parser knows only L0, C52, H, G, X and Part A/C names).
  - Reported: peak turner torque, fraction of steps at the 1 N·m limit, per-class near-pair stats, and steps/s.
  - Also peak memory per process, as input to G.10 (TODO: `/usr/bin/time -v`).
- One snap-back replay per HC arm: seed 16568, +8°, ER7's `posthoc/snap_diag.py` method. Reported: U error after 1 s
  and each piece's leftover rotation about its own radial axis. C52 left 1.40–1.74° on the U-layer pieces (FACT, ER7).
- References: L0 0.461 N·m, 0 steps at the limit; W3 1.000, 4.3 %; G1 / G2 / G3 (Part E) 0.525 / 0.432 / 0.118 N·m
  (FACT, ER9 PROTOCOL Part E table and amendment 2).

### G.7 Probe (Part B design)
- **Trials:** ER7's list and seeds. E1-1 rest (20; scored 10 s rest only), E1-2 quarter turns (24), E1-5s snap-back
  (20), E1-5 forgiveness (42). That is 106 per arm, 318 in all for the 3 default arms (424 with HC8r).
- **Runner:** a Part G runner (`er9g_run.py`, TODO) built like `er9_hybrid_run.py`:
  - Part G arm table;
  - refuses to start unless GS1–GS5 passed;
  - exclusive-create records, so it resumes after interruption;
  - fresh worker per trial.
- Records go in `results/hybrid_g/probe/<arm>/`.
- **Probe signals (fixed now; ER7's criteria):**
  1. E1-5s: every scored trial passes (\|error\| ≤ 0.5° after 1 s from 3° or more).
  2. E1-1: every rest rotation ≤ 0.5°.
  3. E1-2 and E1-5: every trial passes.
  4. Validity per G.3, by pair class:
     - no perpendicular near pair;
     - piece–piece tilt ≤ 7.5° and no clamped piece–piece pair;
     - piece-to-core tilt ≤ 20°;
     - in operational trials, an over-limit trial fails (M4 rule 2).
- **Reported (pre-declared, not signals):**
  - Turner torque: median, max and moves at the limit, against L0, C52, W3 and HB1–HB3 on the same seeds.
  - **Paired rest rotation against L0 and against H0 on the 20 seeds** (count of seeds where the arm is lower; sign
    test). Rest rotation is continuous, so it has more power than the 0/20 versus 2/20 pass count. Fisher's exact test
    on 0/20 against 2/20 gives p of about 0.49 (INFERENCE).
  - Rest on L0's slip seeds 16003 and 16005.
  - Snap-back errors, gravity sag, per-class stats, and steps/s.
- **Selection (fixed now).** H0 is a control and is not selectable. Among the HC arms that meet all four signals, take
  the one with the lowest median E1-2 turner torque; ties go to fewer magnets (HC8). If none meets all four, Part G
  ends here and is reported.

### G.8 Full rehearsal of the selected arm, and reading
- **Trials:** ER7's full list and seeds, 204 trials, with D10's instrumented 60 s rest in E1-1. The 106 probe trials
  are rerun inside it and must reproduce the probe's pass flags and rest and snap-back values (reported as a check).
- **Signals:**
  1. 0/20 E1-1 slip events (D11's definition) and every rest ≤ 0.5°.
  2. M5's Option A rule over the 204 trials, with E1-6m ⟨P⟩.
  3. Validity per G.3 by pair class: operational trials fail when over the limit; abuse trials are logged and
     labelled.
- **Analysis:** `er9_full_analyze.py ARM --root results/hybrid_g`, beside L0, C52, W3 and (if run) the Part E arm.
- **Reading (fixed now).**
  - **All three met and no move at the 1 N·m limit:** the arm is reported as worth a G1 path. That path is proposed to
    the user together with what it still lacks:
    - the GD2 (b) catalogue-magnet version (the 0.756 scale has no catalogue meaning);
    - corner–edge 4×3 validation beyond 7.5°, if any operational trial came near it;
    - the fit misses (GD8);
    - independence from selection (fresh seeds, a scored pre-registration and a review).
  - **All three met but with moves at the limit:** reported beside W3; the choice goes to the user.
  - **Signal 1 missed:** INFERENCE, the static warning in G.2 holds. Reported against L0 and H0 trial by trial.
  - **Signal 2 missed in E1-5s:** M5's magnets did not supply enough spin stiffness against the core pairs. Reported.
  - **H0 meets signals 1–3 in the probe:** the 4×3 stand-in alone explains any improvement over L0, and the core
    pairs' role is unshown. Reported as such.

### G.9 Limits
- Rehearsal only. ER7's seeds have been used for diagnostics and for earlier selections. Twenty rest seeds give wide
  intervals: 0/20 has a 95 % upper bound of 17 % (FACT, ER7 PROTOCOL).
- **P-58 abstraction:** magnets have no collision geometry and sit at real radii inside B1 pieces.
- B1 has no radial freedom. Magnets cannot preload pieces radially, so the commercial uses of repelling magnets have
  no counterpart here. Commercial cubes hold pieces with feet, not magnets (findings (e)5); B1 holds them with a ball
  joint at the centre, which matches that.
- The 4×3 at scale 0.756 stands in for M5's magnet (pull matched; other properties not). Br ≈ 1.03 T is below sintered
  N35 (G1 gap analysis A5).
- **Validation coverage:**
  - on-axis piece-to-core paths: P-60;
  - corner–edge 4×3: 7.5°;
  - cross-group pairs: dipole far field only (> 8 mm by P1);
  - HC8's subset: only if P4 passes;
  - off-path poses (E1-5, E1-6) are judged at 7.5° strictly and also reported at 20°.
- implicitfast at 0.5 ms has a bounded energy oscillation of about 10 % with core magnets (FACT, M6). The
  ideal-magnet caveat (up to 1.5× overstatement) carries over. No derated arm is included.
- Statics have mispredicted dynamics twice (ER3 passed C52; Part A's peak did not predict W3's stall). P2's numbers
  guide; the probe decides.

### G.10 Resources (machine shared and memory-limited)
**FACT (recorded runs):**
- ER7, 204 trials per arm, summed trial wall: L0 (48 magnets) 10.5 h, C52 (40) 9.5 h (ER9 SUMMARY Part D table;
  ER7: 408 records in 9,593 s at 8 workers).
- W3 (96), 204 trials: 22.8 h summed, in 7,117 s wall (`full_W3_log.txt`).
- ER9 Part C probe: 318 trials (W1–W3) in 2,756 s wall (`probe_partC_log.txt`). Its worker count was not checked.
- **One E1-2 trial (`B_s16120`), `wall_s`:** L0 24 s, C52 21 s, W3 42 s (full) / 66 s (probe), S1 73 s, HB1–HB3
  547–675 s.
  - The Part E figures are about 10× W3's. That is not explained: machine load during Part E is likely but was not
    checked.

**INFERENCE (estimates; the smoke replays measure steps/s first).**
- Pairs on different bodies:
  - L0 / H0 1,092;
  - HC8 1,928;
  - HC20 3,554;
  - HC8r about 2,700;
  - W3 3,396;
  - C52 590.
- A straight line through L0 (1,092 → 10.5 h) and W3 (3,396 → 22.8 h) gives, for a full 204-trial rehearsal:

  | Arm | Full rehearsal (CPU-h) |
  |---|---|
  | H0 | about 10.5 |
  | HC8 | about 15 |
  | HC20 | about 24 |

  - The fit is poor for C52 (predicts 7.8 h against 9.5 h).
  - The Part E per-trial times suggest the real cost could be higher. The G1 gap analysis estimated 25–35 CPU-h for
    the 144-magnet hybrid.
  - Band: HC20 20–35 CPU-h.
- Probe: ER9's probe-to-full ratio is about 0.13–0.14 for W3, if Part C ran on about 12 workers (TODO: exact, from the
  summed `wall_s` of `results/probe/W3`).

  | Item | CPU-h | Wall at 4 workers |
  |---|---|---|
  | H0 probe | about 1.4 | |
  | HC8 probe | about 2.0 | |
  | HC20 probe | about 3.2 | |
  | Probe total (3 arms) | about 6.6 | about 1.7–2.5 h, with tail effects |
  | Full rehearsal, HC20 | about 24 (20–35) | about 6–9 h |
  | Full rehearsal, HC8 | about 15 | about 4 h |
- Statics (P1–P3): minutes. Part A screened 243 layouts in about half an hour (FACT, Part F draft, git history).
- P4: about 1 CPU-h.
- Self-checks: 6 trials. Smoke: 3–4 single turns and 2–3 snap-backs, under 1 CPU-h.

**Proposal.**
- Start only after Part E's probe has finished and nothing else heavy is running.
- 4 workers (at most 6).
- The runner resumes from existing records, so a low-memory stop loses at most the trials in flight (FACT: ER7
  deviation 2; Part E's three stops lost no records).
- Memory per worker is not recorded anywhere I read (TODO, from the smoke replays). If it exceeds roughly 1/6 of the
  free memory, use 3 workers.

### G.11 Code to write (all in `experiments/ER9_anchored_core_layouts/`, committed with the protocol before any run; no change to `src/` or to any frozen path)

| Script | Purpose | Kind |
|---|---|---|
| `er9g_layouts.py` | H0, HC8, HC20 (and HC8r) lists from `layout()` + `core_layout()`, plus GS4 | Wrapper (lists only) |
| `er9g_scan.py` | P1, reusing `er9_hybrid_pairs.scan` geometry and extending it to classes, tilt, clamped z, 6 faces, clearances, and E1-5-like poses | Static |
| `er9g_static.py` | P2 and GS6, through `er9_screen.py` functions and ER1's probe-5 function; per-magnet σ only as a static report | Static |
| `er9g_stats.py` | Per-class near-pair diagnostic: a `MagnetSystem` subclass whose `forces()` adds stats from `p, n` after calling the unchanged `pair_forces`; GS5 | Diagnostic (forces untouched) |
| `er9g_run.py` | Part G runner: `selfcheck`, `probe`, `report`, `full`, as `er9_hybrid_run.py` | Wrapper |
| Smoke | An arm option for `er9_turn_diag.py`'s method (new file, so the committed script stays unchanged), and ER7's `snap_diag.py` method | Diagnostic |

GD2 (b) or (c) would add force-law-level code: a composite system or per-magnet σ. That needs its own self-checks
(V4 momentum, V5 energy, V6 pose-only) and an independent review before any use.

---

## Inconsistencies and blockers found while drafting
1. **No decision-log row for ER9** (FACT: grep finds no "ER9" in `docs/DECISION_LOG.md`).
   - ER9 PROTOCOL's status says the main session "records it in the DECISION_LOG", and ER9 SUMMARY says a row "will
     be proposed when Part E is complete".
   - Parts A–E therefore rest on an unlogged reading of P-63. Part G's approval should not stack on that (GD13).
2. **The task's premise is weaker than stated.** ER3 already screened "M5 + core" statically and rejected it, though
   in the unbuildable B1 placement (P-56; ER3 Interpretation 2). Hand arithmetic (G.2) says matched-strength on-axis
   pairs add only +280–285 mN·m/rad, against L0's −420 to −1971. And the one partial dynamic data point (HB2, seed
   16005, 0.516°; gap analysis §5) is a rest failure. "Nobody has simulated the two together" is true only for
   on-axis dynamics.
3. **Two L0 stiffness figures differ:** ER1 F4's −0.93 N·m/rad (edge) against ER3's edge slide −1971 mN·m/rad. These
   are probably different definitions; not reconciled here. P2 computes both for every arm.
4. **Part E's probe is unfinished and uncommitted.** `hybrid_probe_log.txt` shows restarts at 318, 243 and 95
   remaining, and stops at 275/318. Git status lists it and `results/hybrid/probe/` as untracked. Part G competes for
   the same machine and shares its comparison set.
5. **Per-trial wall time in Part E is about 10× W3's on the same trial** (547–675 s against 42–66 s, `B_s16120`).
   This is not explained, and it makes every resource estimate above uncertain.
6. **Part E's tilt flag was not strict.** It used 20° for 4×3 corner–edge pairs, for which only V3b's 7.5° applies.
   ER9 SUMMARY already says so; Part G needs the new per-class diagnostic to do better. The runner's single
   `max_near_tilt_deg` cannot separate classes.
7. **`er9_hybrid_pairs.py`** scans only perpendicular pairs, only U, from 0° to 90°. It is not enough as Part G's P1
   and needs a new script.
8. **`er9_hybrid.py`'s docstring** says `anchors=False` is for "4x2_M5 only". The code path also builds 4×3 H0. The
   docstring is misleading, not wrong in behaviour (INFERENCE from reading the code; not run).
9. **The scale 0.756 has no catalogue meaning** (Br ≈ 1.03 T; gap analysis A5). P-60's wording is "grades by exact
   scaling". Whether a non-grade Br² scale is covered is a reading that Part E applied without a recorded decision.
10. **The HC20 geometry margin is 0.02 mm** (G.4 P1, hand arithmetic). This is a likely source of weight-zero
    perpendicular flags. Rather than invite a post hoc amendment, this draft fixes now that such flags count.
11. **Minor.** The findings report ((e)1) cites ER4 as "room … for magnets of at least 9.8 mm diameter" (the corner's
    largest coaxial cylinder). It omits the edge's 6.3 mm and the with-wall figures, 5 / 6 mm, that P-57 records.
    These are consistent but easy to misread.
12. **Not checked.** ER7's L0 largest near tilt was 12.59° (ER7 SUMMARY), above 4×2's 5°. Presumably it came from
    abuse trials, where M4 rule 3 only logs. Not verified. If an operational L0 trial exceeded 5°, M5's rule 2
    handling would need a look.

---

## TODO: numbers this draft could not compute (no process was run)

| Number | What computes it |
|---|---|
| P1 scan per arm: perpendicular pairs, per-class largest tilt, clamped counts, closest distances and clearances (6 faces, ±90°), E1-5-like poses; confirm the 8.02 mm / 74.8° HC20 passage and the 9.65 mm minimum | `er9g_scan.py` (new; reuses `er9_hybrid_pairs.scan`) |
| ER3 single-piece stiffnesses, layer stiffness, U-turn peak, 66 × 66 eigenvalues and collective twist per arm; core σ at which each negative mode reaches 0 | `er9g_static.py` (new; `er9_screen.py` functions) |
| ER1 probe 5 (edge, corner, corner+edge pair) per arm, and for the 4×3 H0 against L0's 4×2 | `ER1_rest_slip_review/er1_probe_magnet_stiffness.py`, called with each arm's list |
| Machine-precision polarity check (energy odd in one moment) | `er9g_static.py` |
| V3-turn for the 8-magnet core (HC8; HC8r with reversed edge moments) | `ER5_magnet_validation/er5_checks.py` V3-turn with a reduced core set |
| Surface gaps: on-axis piece magnet to the same piece's M5 magnets; core-to-core | `side_checks/realfit/fitlib.cyl_cyl_gap` on our own cylinders (no CAD) |
| Probe-to-full CPU ratio for W3 | sum of `wall_s` over `results/probe/W3` and `results/full/W3` records |
| Steps/s and peak memory per worker for each arm | smoke replays (G.6) under `/usr/bin/time -v` |
| Cause of Part E's 10× per-trial time | `loadavg_start` and `wall_s` fields across `results/hybrid/probe/*` records |
