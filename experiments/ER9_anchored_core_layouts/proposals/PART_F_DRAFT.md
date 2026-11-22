> **DRAFT — not approved; not a committed protocol.** Drafted by a subagent on 2026-11-21 without running anything.
> Estimates marked INFERENCE are hand arithmetic. Nothing here is fixed until the user approves a version, and it is
> then added to `PROTOCOL.md`.
>
> Main-session checks: the four source inconsistencies it found in the side-check notes were confirmed against the
> stage4 and stage5 logs and corrected (commit following this draft).
>
> Written before the core-magnet practice report (`docs/research/CORE_MAGNET_PRACTICE_FINDINGS.md`) existed. That
> report finds commercial cubes use on-axis corner–core pairs added to the usual piece-to-piece magnets. Of this
> draft's families, the closest match is the all-on-axis hybrid, which a revision should consider first.

# DRAFT for review — ER9 Part F: fit-constrained static re-screen

**Status: DRAFT, 2026-11-21. Not fixed, not committed, not approved, nothing run.** If approved, this text (with the
user's choices filled in) would be appended to `experiments/ER9_anchored_core_layouts/PROTOCOL.md` and committed
before any Part F computation, as for Parts A–E. Exploratory and unscored. It changes no record, selects no
mechanism, and touches no scored seed (17000–17999). M5 stays NOT PASSED; no mechanism has passed G1.

Labels: `FACT` (from a named file), `INFERENCE`, `PROPOSAL`, `TODO` (a number this draft could not compute; no
process was run while it was written). Nothing here is a result.

Sources read: ER9 `SUMMARY.md`, `PROTOCOL.md` (Parts A–E), `er9_screen.py`, `er9_layout.py`, `er9_hybrid.py`,
`screen_log.txt`; `side_checks/README.md`, `side_checks/realfit/` (stage0–6 scripts and logs, `summarize3.log`,
`compare_spot.log`), `side_checks/catalogue/` (`targets_out.txt`, `scan_out.txt`, `extras_out.txt`); ER5 `PROTOCOL.md`
and `SUMMARY.md`; `docs/DECISION_LOG.md` P-56 to P-66 and the G1 row; `docs/VALIDATION_PLAN.md`;
`experiments/D8_alignment/results/checks_history/README.md`; `src/rubiknetic/cube_physics/magnets.py`
(`MagnetParams`, `GRADES_BR`, `REAL_RADIUS`); the list of table files on disk.

---

## Decisions for the user (each is a mechanical or strategic choice; the draft uses the default)

| # | Choice | Recommended default | Alternative(s) and trade-off |
|---|---|---|---|
| D1 | Fit reference | The GrabCAD real-mechanism CAD's **measured numbers only** (`side_checks/realfit/`), as a hard criterion | A purpose-designed cube with deeper corner feet: no data exists, so it can only be a design lever, not a screen input |
| D2 | Fit thresholds | Wall ≥ 0.4 mm (the `MagnetParams.wall` the model already assumes); magnet-to-magnet gap ≥ 0.5 mm (the side checks' value) | Wall ≥ 0.2 mm, for which `stage5` also has ranges. Wider candidate set, but thin moulded walls are unverified. Default reports the 0.2 mm result as a sensitivity column only |
| D3 | Core placement | **Fit-true single ball**: radius 21.935 − c mm, core magnets recessed so 0.4 mm of ball covers each magnet's rim | Part A's per-kind core radius (21.84 / 21.75 mm at c = 0.2, rim cover 0.20–0.29 mm), kept for comparison with Parts A–D. It fails the 0.4 mm cover (FACT, `stage2b`) |
| D4 | Magnet sizes | 4×3, 4×2, 3×3, 3×2 (all measured for fit) plus 3×1.5 (fit follows from 3×2 by containment; its table exists) | 4×3 only: every corner option then has to be on-axis or deep, which is weak (see "Expected outcome") |
| D5 | Sizes with no validated core-pair table | **Screen them statically with a 4×3 stand-in** (stated equivalence below), ranked below 4×3. No dynamic use until that size passes an ER5-style validation | (a) Exclude them: the screen is clean, but corners lose almost every fit-feasible option. (b) Validate first: about 1.3 h of compute per size at ER5's timings, with failure possible (5×2 and 4×1.5 failed before). Takes the machine's memory while Part E is unfinished |
| D6 | Spin/twist criterion 2 (Part A's 100 mN·m/rad, set from an argument now known to be wrong) | **Option 2-B**: spin, twist and the smallest eigenvalue each ≥ W3's own value (computed by the screen), with 100 kept as a reported column | 2-A: keep 100 (comparable with Part A; expected to reject every anchored-only fit-feasible layout). 2-C: positive only (> 1 mN·m/rad); widest set, and leaves the probe to decide |
| D7 | Eigenvalue criterion 3 (≥ 50, no rationale stated in Part A) | Same option as D6 (W3's own value) | Keep 50, or positivity only |
| D8 | Strength allowed for selection | Sintered grades N35–N52 of the real size: strength factor 1.0–1.495 on Br² (`GRADES_BR`) | Down to 0.3 (W3's level), which stands for bonded NdFeB or another unconfirmed material. Both are reported; only the allowed range selects |
| D9 | Clearance | Anchored family: c = 0.2 mm (Part A, ER6, and the scope of P-60's clamped-pair acceptance). Hybrid family: c = 1, 2, 3 mm (Part E's arms) | Add c = 0.3 mm as a tolerance case: one more evaluation per geometry |
| D10 | Families | Anchored-only **and** hybrid (M5's 48 corner–edge positions plus fit-feasible anchors), selected separately | Anchored-only. INFERENCE: it probably inherits W3's turner stall, which the diagnostics tie to the absence of in-layer magnets |
| D11 | Hybrid corner–edge fit miss | Screen at Part E's positions and report the miss (corner wall 0.175 mm at the simulated positions, FACT `stage4`) | Shift them to the CAD's face-relative positions (wall 0.4 mm; face gap about 1.05 mm instead of 0.85 mm). Fits, but departs from Part E's arms |
| D12 | What a selected layout gets | Tier 1 (4×3 anchors): a Part B-style probe and, if it meets all four signals, a Part D-style rehearsal, as Parts B–D. Tiers 2–3: stop and report; validation needs the user's go | Stop after the screen in every case and bring the result to the user |
| D13 | Seeds for any probe | ER7's rehearsal seeds 16000–16655, for pairing with L0, C52 and W3 | Fresh unscored seeds outside 16000–17999: independent of earlier selection, but not paired with L0, C52 and W3 |
| D14 | Clamped near pairs outside P-60's accepted set (off-axis anchors; c ≠ 0.2 mm) | Report the count per candidate; not a pass/fail criterion of the screen | Make it a criterion: it would reject every off-axis candidate, including W3 |

---

## Part F — fit-constrained static re-screen (addendum, DRAFT; to be fixed before any Part F computation)

### Why
- **FACT (`side_checks/README.md`, `realfit/stage1_anchor_fit.log`, `stage5_sizes_and_gaps.log`).** Part A's selected
  geometry does not fit the real-mechanism CAD.
  - Corner anchors at 16° toward the centres: 83 % of each 4×3 magnet is in air. Along the line, material starts at
    24.99–25.0 mm; the magnet spans 22.35–25.35 mm.
  - Edge anchors at 20°: the 4×3 cylinder breaks out of the foot by 0.58 mm (wall −0.543 mm), into the centre piece.
- **FACT (`stage5`).** Feasible angle ranges at the layout's depth (wall ≥ 0.4 mm and piece-side gap ≥ 0.5 mm):

  | Piece, direction | 4×3 | 4×2 | 3×3 | 3×2 |
  |---|---|---|---|---|
  | Edge, toward centres | 6–16.5° | 6–26.5° | 4.5–17.5° | 4.5–28° |
  | Edge, toward corners | none | none | none | none |
  | Corner, toward centres | none | none | 5.5–6.5° | 5.5–7.0° |
  | Corner, toward edges | none (7.0° only at wall ≥ 0.2) | 7–11.5° | 5.5–7.5° | 5.5–14° |

  Note: `SUMMARY.md` and the side-check README say corners take three magnets "only as 3 × 2 at 5.5–7° toward the
  centres". `stage5` also gives 3×3 at 5.5–6.5° toward the centres.
- **FACT (`stage3_sweep.log` via `summarize3.log`).** Deeper placements of the piece magnet exist. Examples: corner
  4×3 toward the centres fits with its inner face at ≥ 25.4 mm (8°, 12°), ≥ 27.0 mm (16°) or ≥ 29.8 mm (20°); toward
  the edges at ≥ 26.1 mm (8°) or ≥ 28.1 mm (10°). The core magnet cannot follow (the ball's radius is limited by the
  pieces), so the face gap grows to about 4–7 mm (INFERENCE, arithmetic below).
- **FACT (`SUMMARY.md` Limits).** Whether any feasible placement still holds the pieces has not been computed. Part F
  computes it.

### Question (fixed)
> Is there an anchored or hybrid core-magnet layout whose magnets all fit the real-mechanism pieces, by the measured
> fit data, and which meets Part A's static criteria (as amended by D6/D7)? If none does, which criteria does each
> near candidate miss, and by how much?

### Candidates
**Common to all.** Piece magnet and core magnet on one radial line (Part A's principle). Piece magnet inner face at
the layout depth R_kind + 0.4 mm (R_edge = 22.04, R_corner = 21.95 mm; `REAL_RADIUS`), or at a measured deep radius
where stated. Core magnets per D3. Angles and depths only where the fit data has a grid point (no interpolation):
`stage5` has 0.5° steps at the layout depth; `stage3` has 1° steps and 0.1 mm inner-face steps for 4×3 and 3×2.

**Edge options (15).**

| ID | Magnets per edge | Fit (FACT, `stage5`/`stage3`) | Core-side gap ≥ 0.5 mm (INFERENCE, hand estimate) | Table status |
|---|---|---|---|---|
| E0 | 1 × 4×3 on the axis (C52's edge; reference) | wall 0.40 | — | T1 |
| E43-8, -12, -16 | 2 × 4×3 toward the centres at 8°, 12°, 16° | walls 0.49 / 0.49 / 0.50 | needs γ ≳ 7.0° | T1 (off-axis trajectory not V3-turn checked, as W3) |
| E42-12, -16, -20, -24 | 2 × 4×2 toward the centres | in range 6–26.5°; **20°: 0.417, marginal** | ≳ 6.7° | T2 |
| E32-12, -20, -26 | 2 × 3×2 toward the centres | in range 4.5–28°; 20°: 0.454 | ≳ 5.2° | T3 |
| E33-16 | 2 × 3×3 toward the centres | in range 4.5–17.5° | ≳ 5.5° | T3 |
| E315-20, -26 | 2 × 3×1.5 toward the centres | contained in the 3×2 cylinder at the same axis and inner face (INFERENCE: a subset of a cylinder with wall ≥ 0.4 mm has wall ≥ 0.4 mm) | ≳ 5.2° | T2 |
| EM-16 | 1 × 4×3 on the axis + 2 × 4×3 at 16° toward the centres | walls 0.40 and 0.50 per direction; on-axis to off-axis gap **not measured** | ≳ 11.5° piece side, ≳ 14.0° core side | T1 |

Toward the corners: excluded. FACT (`stage5`): no angle meets both the wall and the spacing for any size.

**Corner options (19).**

| ID | Magnets per corner | Fit (FACT) | Core-side gap (INFERENCE) | Table status |
|---|---|---|---|---|
| C0 | 1 × 4×3 on the axis (C52's corner; reference; twist 0) | wall 0.40 | — | T1 |
| CC32-6.0, -7.0 | 3 × 3×2 toward the centres | range 5.5–7.0° | ≳ 6.0°: **6.0° marginal** | T3 |
| CC33-6.5 | 3 × 3×3 toward the centres | range 5.5–6.5° | ≳ 6.3°: marginal | T3 |
| CE32-6, -10, -12, -14 | 3 × 3×2 toward the edges | range 5.5–14° | ≳ 6.0° | T3 |
| CE33-7.5 | 3 × 3×3 toward the edges | range 5.5–7.5° | ≳ 6.3° | T3 |
| CE42-8, -11.5 | 3 × 4×2 toward the edges | range 7–11.5° | ≳ 7.7° | T2 |
| CE315-10, -14 | 3 × 3×1.5 toward the edges | contained in the 3×2 (as E315) | ≳ 6.0° | T2 |
| CD-c8, -c12, -c16 | 3 × 4×3 toward the centres, **deep** (inner face 25.4 / 25.4 / 27.0 mm) | `stage3`, smallest inner face with wall ≥ 0.4 | wide at these radii | T1 for the table; face gap 4.2–5.8 mm (INFERENCE) |
| CD-e8, -e10 | 3 × 4×3 toward the edges, deep (26.1 / 28.1 mm) | `stage3` | wide | T1; face gap 4.9–6.9 mm |
| CM-e14 | 1 × 4×3 on the axis + 3 × 3×2 at 14° toward the edges | walls per direction from `stage5`; on-axis to off-axis gap not measured | ≳ 10.3° piece side, ≳ 11.9° core side | T3 |

**Anchored family:** 15 × 19 = **285 geometries**, plus three reference rows that do not fit (Part A's selected
layout, W3, C52), for the self-checks and for comparison. Part A screened 243.

**Hybrid family (18).** M5's 48 corner–edge positions with Part E's magnet (4×3 N35 at scale 0.756, amendment 1),
plus anchors E0, E43-12 or E43-16 on the edges × C0 or CE32-14 on the corners × c = 1, 2, 3 mm. Anchors of 4×3 at
scale 0.756 as in Part E; the CE32-14 anchors as a stand-in (below), at the strength of a 3×2 N35 × 0.756.
- INFERENCE: E0 + C0 + M5's 48 is the one hybrid that uses only placements whose core-pair trajectories ER5 checked
  (on-axis, 4×3). Its corner–edge pairs carry Part E's validation status.
- FACT (P-56): ER3 found "M5's layout plus core magnets" failing (edge slide −1441 mN·m/rad at σ = 2). That was in
  the B1 placement, which ER5 showed is not buildable (P-58). The real-placement value is unknown.

**Known in advance (INFERENCE, hand arithmetic from Part A's rows; not computed).**
- Edge spin and corner twist scale with sin²γ. Part A's N35 rows give 761–764 × sin²γ (edges toward the centres, 16–20°)
  and 1105–1111 × sin²γ (corners toward the edges, 14–16°) mN·m/rad for 4×3 at c = 0.2.
- A size factor converts to other sizes: the pair's lateral stiffness relative to 4×3 at the same face gap. Hand
  estimates from catalogue rows: about 0.75 for 4×2, 0.55 for 3×3, 0.5 for 3×2, 0.35–0.45 for 3×1.5. TODO: compute with
  `side_checks/catalogue/cyl_pair.py`.
- Corner twist at N35 on these estimates: 3×2 toward the edges about 17 (10°) and 33 (14°); 4×2 about 33 (11.5°);
  3×2 toward the centres about 8 (7°); deep 4×3 in single digits. N52 multiplies by 1.495.
- W3's values are Part A's N35 row × 0.3: spin ≈ 26.7, twist ≈ 25.2, smallest eigenvalue ≈ 24.9 mN·m/rad. TODO:
  exact values from `results/screen.json`. W3 would fail Part A's criteria 2 and 3 itself.
- **So, before running:**
  - Under option 2-A (100 mN·m/rad), no anchored-only fit-feasible layout is expected to pass. The corner maximum is
    about 50 mN·m/rad at N52.
  - Under option 2-B, the corners that plausibly pass are 3×2, 3×1.5 or 4×2 toward the edges near the top of their
    ranges (tiers 2–3).
  - Under every option, a tier-1 anchored-only layout can only pass with deep or on-axis corners, which means
    positivity only (2-C).
  - The hybrid family may pass 2-A: FACT (PROTOCOL.md, Idea), L0's spin and twist are 122 and 118 mN·m/rad (ER3).
  - The screen replaces all of these estimates.

### Force tables and stand-ins
**Status per size.**

| Size | Table on disk | Validation | Tier |
|---|---|---|---|
| 4×3 | `ER5_magnet_validation/tables/`, `M6_core_magnets/tables/` | V1, V3a, V3b (7.5°), V4; V3-turn passed for on-axis core pairs in the real placement, tilts within r2 to 18–20° (FACT, ER5, P-58, P-60) | T1 |
| 4×2 N35 / N52 | `D8_alignment/results/tables/` | V3b validated tilt 5° (FACT, D8 checks history); never checked for core pairs | T2 |
| 3×1.5 N35 | `D8_alignment/results/tables/tilt_3x1.5_…` | V3 passed, validated tilt 7.5° (FACT, D8 checks history); never checked for core pairs | T2 |
| 3×2, 3×3 | none (FACT, file list) | none | T3 |

FACT (Part E amendment 1; Part D): anchor pairs stay within 8 mm of their core partner for the first 14–16° of a
turn, with near tilts up to 18.4°. INFERENCE: so no T2 size is validated at the tilts involved; each would need at
least a V3-turn.

**Stand-in (PROPOSAL, D5 default).**
- A non-4×3 magnet is represented in the force computation by a 4×3 magnet with the same inner face (piece side) or
  outer face (core side), on the same axis.
- Its moment multiplier σ (the existing per-magnet `sigma` of `er9_screen.anchored_layout`; pair factor σᵢσⱼ) is set
  so that the coaxial pair's **lateral stiffness** at the candidate's face gap equals the real size's charge-model
  value, computed with `cyl_pair.py`.
- Reported for each stand-in: pull mismatch, axial-stiffness mismatch, and the centre shift (0.5 mm for 3×2, 0.75 mm
  for 3×1.5), which changes the lever arms by about 4 % (INFERENCE).
- **Why lateral stiffness.** Criteria 1–3 and layer stiffness are tangential stiffnesses. The cost is the detent
  (U-turn peak). From the catalogue rows (INFERENCE), at equal pull a 3×2 or 3×3 is 12–38 % stiffer laterally than a
  4×3, so a pull-matched stand-in would understate the stiffness, and a lateral-stiffness-matched one probably
  overstates the pull.
- **Why the 4×3 geometry and not the real centre.** A 3×2 at its real centre sits 3.0 mm from its partner at a 1.0 mm
  gap. The 4×3 table is clamped below |z| = 3.1 mm (FACT, P-60), so it would be evaluated clamped even at rest.
- **Measured size of the stand-in error.** For single-size layouts of 4×2 and 3×1.5, whose own tables exist, the
  screen also evaluates the layout with that table at home poses. The difference is reported as the stand-in error
  for those sizes. It is not a validation, and it says nothing direct about 3×2 or 3×3.
- **Fit, spacing and intersection** always use the real size's dimensions and positions.
- Stand-in numbers are labelled "stand-in" in every output and cannot be presented as a validated result.

**Engineering constraint (FACT, `er9_hybrid.py` docstring).** A MagnetSystem has one magnet type. A mixed-size
layout (edges 4×3, corners 3×2, or CM/EM mixes) therefore cannot be run dynamically without a code change. A
single-size layout can run with its own table once that table is validated.

### Fit as a hard criterion (new)
The screen opens no mesh. It reads only committed numeric results: `stage5_results.json` (wall and piece-side gap per
size, angle and direction at the layout depth), `stage3_results.json` (inner-face ranges per angle for 4×3 and 3×2),
and the constants below. It records their SHA-256 hashes in its output.

**FACT (`side_checks/README.md`).** The CAD's licence is unconfirmed. Only numbers may be kept: no geometry, no
derived mesh, no piece outline in any committed file or figure. A new measurement would need the same rule and the
user's approval; this draft proposes none.

- **F1, piece wall.** Every piece magnet's wall to the CAD surface ≥ 0.4 mm (−0.005 mm, `stage5`'s tolerance), at a
  measured grid point (size, angle, direction, depth).
  - A size contained in a measured cylinder (same axis, same inner face, no larger diameter or length) inherits that
    cylinder's wall as a lower bound. This covers 3×1.5 in 3×2.
  - Walls within 0.07 mm of the threshold are flagged "marginal". FACT (`stage0c`): the surface sampler's largest
    point spacing is 0.068 mm.
  - The data is for one reference piece per type.
    - FACT (`stage0_symmetry.log`): the pieces of a type are congruent to 1e-14 mm.
    - FACT (`stage0b`): each piece's own symmetries hold to 0.045 mm.
    - FACT (`compare_spot.log`): a second piece gave identical walls.
- **F2, spacing.** Every two magnets of one piece, and every two core magnets, ≥ 0.5 mm apart, surface to surface,
  with real dimensions.
  - Piece-side gaps for symmetric sets are read from `stage5`.
  - Mixes, and all core-side gaps, are computed by the screen from the layout's own cylinders (geometry of our
    magnets only; no CAD), for example with `realfit/fitlib.cyl_cyl_gap`.
  - INFERENCE: `stage5`'s lower angle bounds come from the piece magnets only. Core magnets of one piece sit 3–4 mm
    nearer the centre, so they are closer together. By hand, the core side needs about 7.0° (4×3 edges), 7.7° (4×2
    corners), 6.0° (3×2 corners) and 6.3° (3×3 corners).
- **F3, core cover.** At least 0.4 mm of ball material over every core magnet's rim, for one ball of radius
  21.935 − c mm.
  - FACT (`stage1`): the CAD pieces come no closer than 21.935 mm to the centre.
  - Rim radius = √((outer-face radius)² + (d/2)²).
  - Self-check: the formula reproduces `stage2b` (Part A placement, c = 0.2, ball 21.735 mm: edge 0.202, corner
    0.292 mm).
- **F4, intrusion into other pieces.** Implied by F1 (INFERENCE: a magnet with ≥ 0.4 mm of its own piece around it
  cannot occupy another piece, and the CAD's pieces do not overlap). Not computed separately. FACT (`stage6`): it was
  measured only for Part A's positions.
- **F5, hybrid corner–edge magnets.** FACT (`stage4`): at the simulated positions every 4×3 lies inside its piece, but
  the corner walls are 0.175 mm. Walls reach 0.4 mm only at the CAD's face-relative positions (shifted 0.354 mm on
  edges and 0.419 mm on corners; the CAD's piece gap is 0.25 mm against 0.05 mm in the simulation). Handled per D11.
  The anchor-to-corner–edge clash distance (≥ 3.99 mm, `stage2`) was measured for the S1 anchors only; for new
  anchors F2 covers it.

**Fit-true core placement (D3 default).** Core magnet outer face at (21.935 − c) − 0.4 − (d/2)²/(2·(21.935 − c)).
At c = 0.2 the face gap then becomes about 1.19 mm on edges and 1.10 mm on corners for d = 4 mm, against Part A's
1.0 mm (INFERENCE, arithmetic). That is about 7–14 % less pull, at the catalogue's −7.4 %/0.1 mm (FACT, `scan_out.txt`).

### Measured (per geometry)
- Everything Part A measures, by Part A's functions unchanged: ER3's single-piece stiffnesses, layer stiffness,
  U-turn profile and peak; the full 66 × 66 matrix and its eigenvalues; collective twist; the face-turn sweep (closest
  magnets, piece-to-piece distance); the near-pair survey.
- New:
  - F1–F5, each with its margin.
  - Clamped-z count over the survey (already recorded in `geometry_and_survey`, not used by Part A).
  - Stand-in mismatches.
  - Predicted gravity sag: piece weight × lever / tangential stiffness, the relation that matched the rest leftovers
    to three digits (FACT, SUMMARY Diagnostics). TODO: B1 piece masses from the model.
- **Strength window (PROPOSAL).**
  - With one strength factor s applied to every magnet, all stiffnesses, eigenvalues and the peak are linear in s.
    FACT (Part C): "the stiffnesses are linear in strength"; Part A's N42 row = N35 row × (1.30/1.19)².
  - Each anchored geometry is evaluated once, at s = 1 (N35 of the real size, through its stand-in σ), plus at N42
    for the self-check. Its feasible window is s_min = max(1.0 / layer, T₂ / spin, T₂ / twist, T₃ / eig_min) to
    s_max = 0.5 / peak.
  - Reported against the allowed range (D8).
  - The hybrid family is not linear in one factor (fixed corner–edge strength), so each of its 18 rows is one
    evaluation.

### Criteria
Part A's criteria are kept except where marked. A candidate passes if all hold at some allowed strength:
1. **Unchanged.** ER3's: no single-piece stiffness below −1 mN·m/rad; layer stiffness ≥ 1.0 N·m/rad; U-turn peak
   ≤ 0.5 N·m. INFERENCE (noted, not changed): the static peak did not predict the turner saturation (W3: static
   0.085 N·m, dynamic 1 N·m in 771 moves). The selection rule still uses it.
2. **Changed per D6 (user's choice).** Part A's 100 mN·m/rad came from the joint-friction argument that SUMMARY
   correction 1 and Part C withdrew: rest leftovers are gravity sag, and no leftover spin was found after release.
   Options:
   - **2-A:** keep 100. Comparable with Part A. Expected to reject every anchored-only fit-feasible layout.
   - **2-B (default):** spin and twist ≥ W3's values from the same code. Rationale: W3 is the weakest anchored arm that
     has met all three rehearsal signals (204 / 204). Limits: post hoc, and on ER7's seeds, which were used to select W3.
   - **2-C:** > 1 mN·m/rad. This removes the zero modes that failed C52 and nothing more.
   - Whatever the choice, 100 and W3's values are both printed for every row. The option chosen must be recorded
     before the run; changing it afterwards is not allowed (VALIDATION_PLAN threshold policy).
3. **Changed per D7.** Exactly six eigenvalues below 1 mN·m/rad (the centres), and every other eigenvalue ≥ T₃.
   T₃ = W3's smallest eigenvalue (default), 50 (Part A), or 1 (2-C).
4. **Amended.**
   - As Part A: no intersection in any face turn, now with real dimensions; magnets of different pieces ≥ 8 mm apart.
   - Core–core spacing moves from "centre distance > diameter" (`er9_screen.py` line 219) to F2's 0.5 mm surface gap.
   - Hybrid family: M5's designed corner–edge pairs are exempt from the 8 mm rule (they are near pairs by design).
     Every other piece-to-piece pair is held to it.
5. **Survey.** As Part A for the anchored family: no perpendicular near pair, largest near tilt ≤ 20°, no
   piece-to-piece near pair.
   - Hybrid family: anchor-to-corner–edge near pairs are counted and reported, as Part E amendment 2 did (12 per
     quarter turn for the S1 anchors). A hybrid whose only failure is that count is "eligible", as in amendment 2.
   - Clamped-z count is reported (D14).
6. **New: fit F1–F3** (F5 for hybrids per D11), at the D2 thresholds.

### Self-checks (all before any new candidate; any failure stops Part F)
- **FS1.** Part A's S1 (C52 row against ER6's N52 c = 0.2 row, ≤ 1e-9), S2 (26 zero modes, collective twist
  < 1 mN·m/rad) and S3 (table hash) rerun and pass.
- **FS2.** Part A's selected layout (N42, E2@20 > centre, C3@16 > centre, Part A placement, c = 0.2, 4×3, σ by grade),
  computed through Part F's code path, reproduces its row in `results/screen.json` to 1e-9 relative in every field.
  The fields are: single-piece stiffnesses (+106 / +803 / +884; +100 / +1277), layer 5.27, peak 0.338, zero modes 6,
  smallest other eigenvalue 99, collective twist 4881, piece-to-piece 10.36 mm, clearance 0.82 mm, tilt 18.2°.
  TODO: full-precision values from `screen.json`.
- **FS3.** Linearity: the same geometry at N35 × 0.3 (W3) equals the N35 row × 0.3 to 1e-9, and gives Part C's
  1.32 N·m/rad and 0.085 N·m. Its spin, twist and smallest eigenvalue become T₂ and T₃ under option 2-B.
- **FS4.** Fit lookup:
  - (a) Part A's selected layout fails F1, with edge wall −0.543 mm and the corner magnet centre in air (`stage5`
    `wall_at_layout_angle`; `stage1`).
  - (b) Each of `stage5`'s 16 "gamma_both" ranges is reproduced exactly from `stage5_results.json` rows.
  - (c) F3's formula reproduces `stage2b`'s covers to 1e-3 mm.
- **FS5.** Stand-in: the charge-model function reproduces the catalogue's 4×3 N35 at 1.0 mm (`targets_out.txt`:
  pull 1.9231 N, lateral stiffness 776.53 N/m) and 3×2 Br 1.3 at 1.5 mm (lateral stiffness 261.34 N/m) to 1e-6
  relative. σ for 4×3 is exactly 1.
- **FS6.** Hybrid path: with S1 anchors at c = 1 mm it builds the same magnet list as `er9_hybrid.hybrid_mags` (Part E,
  HB1) exactly.

### Running
- **PROPOSAL.** New script `er9_fitscreen.py`, importing `er9_screen.py`'s functions unchanged. It adds:
  - per-direction size, depth and σ;
  - the fit lookup and F2/F3 geometry;
  - the strength window;
  - the hybrid family.

  Output: `results/fitscreen.json` and `fitscreen_log.txt`.
- Runs only when no other job is running (the machine ran out of memory during Part E's probe), with at most 4
  workers. Part A used 12; TODO: memory per worker.
- **Smoke test first.** Time 3 geometries (one per family plus FS2) and print the projected total. Part A's 243
  layouts ran within about half an hour, protocol to results commit (FACT, git history, 21:54 → 22:23). TODO: actual
  per-geometry time.

### Selection (fixed in advance; per family)
1. Candidates that pass every criterion (1–6) at some allowed strength (D8).
2. Order by tier, lowest first:
   - T1: every anchor magnet 4×3.
   - T2: a size whose table exists and passed V3 (4×2, 3×1.5).
   - T3: 3×2 or 3×3.
3. Within a tier: single-size layouts before mixed (runnable with the present MagnetSystem); then the lowest U-turn
   peak at the weakest passing allowed strength; ties go to fewer magnets, then the larger smallest fit margin, then
   the lower strength.
4. A runner-up only as Part B allows (it differs in which pieces are split, or in size).

### What happens next
- **Anchored T1 selected.** A Part B-style probe: 106 trials on ER7's seeds (D13), the four probe signals, 20° tilt
  (P-60), reported beside L0, C52 and W3. If it meets all four, a Part D-style 204-trial rehearsal with ER7's three
  signals, under D12.
- **Hybrid selected.** Probed only if Part E's probe finds an eligible hybrid arm (signals 1–3 met, complete, within
  20°). Otherwise reported only. Reading as Part E amendment 2: no hybrid can be named a pre-registration candidate
  under the present rules.
- **T2 or T3 selected.** No dynamics.
  - Reported with what it would take: for T3, building the size's table; for T2 and T3, an ER5-style validation (V1,
    V3a, V3b ≥ 5°, V3-turn in the real placement for on-axis and for the selected off-axis directions, V4).
  - For a mixed-size layout, also a per-magnet-type MagnetSystem.
  - Each step is a separate proposal for the user.
- **In every case:**
  - The strength window is mapped to stocked magnets (catalogue method) with the stated ±0.5 mm gap uncertainty (FACT,
    catalogue README).
  - A V3-turn of the off-axis placement is still owed before any scored pre-registration (open since Part A).

### If nothing passes
Report, per family:
- the candidates failing exactly one criterion, ordered by the size of the miss (fit margin in mm, stiffness short of
  T₂/T₃ in %, required strength above N52 as a factor);
- what Part A's three passing layouts would need, in mm of wall and degrees of angle, to fit.

Then list the design levers for the user, none of which Part F tests:
- A purpose-designed cube with corner feet that carry material from about 22 mm along off-axis lines. In this CAD it
  starts at 25.0 mm along 16° toward the centres.
- Two pairs per corner instead of three: twist is still restored and the spacing is easier. Needs a new option type
  and its own fit check.
- Thinner walls (0.2 mm), where `stage5` shows wider ranges. Moulding feasibility is unverified.
- Hybrid with on-axis anchors only, if it did not already pass.
- Corner–edge-only layouts (L0 / M5) with another remedy for the rest slips.
- Validating a smaller size's table first (3×1.5 is closest: table and V3 exist).
- Revisiting criterion 2 or 3 (D6/D7), if not already done.

### Limits
- **Static only.** Static screens have mispredicted dynamics twice (ER3 passed C52; Part A's peak did not predict
  W3's stall).
- **Fit data.** One CAD of unconfirmed licence; solid pieces (real moulded pieces are hollow); a 0.25 mm piece gap
  against the simulation's 0.05 mm; grid points only.
- **P-58 abstraction.** The magnets have no collision geometry and sit at real radii inside the B1 model.
- **Stand-ins** are not the real magnet; their numbers rank candidates, they do not describe a magnet.
- **Off-axis trajectories** have no V3-turn of their own (as W3).
- **Clamped pairs** outside P-60's set are reported, not judged (D14).
- **Option 2-B** rests on a rehearsal that used the same seeds that selected it.

---

## TODO list: numbers this draft could not compute (no process was run)

| Number | What computes it |
|---|---|
| Size factors (lateral stiffness of 4×2, 3×3, 3×2, 3×1.5 relative to 4×3, at each face gap) and the stand-in σ | `side_checks/catalogue/cyl_pair.py` (charge model; single pairs; light) |
| Core-side spacing for every option (hand estimates above) | `realfit/fitlib.cyl_cyl_gap` on the layout's own cylinders |
| W3's exact spin, twist and smallest eigenvalue; FS2's full-precision row | `results/screen.json` (N35 E2@20 > centre C3@16 > centre) × 0.3; the N42 row |
| Face gaps and pair distances of the deep options; whether the 4×3 table's z range covers 7–10 mm pairs | Arithmetic from F3 plus the table's npz metadata |
| B1 piece masses and levers for the sag column | The trial model (`M1Params`) |
| Per-geometry runtime and memory per worker | Smoke test of 3 geometries |
| Anchor-to-corner–edge perpendicular near pairs for the new anchor angles | The survey (as `er9_hybrid_pairs.py`) |
