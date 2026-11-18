# ER3 — Static magnet-layout design screen (route B): summary (2026-11-17)

Static, exploratory and unscored (PROTOCOL.md; approved in P-55). No mechanism is selected. M5 stays NOT PASSED.

## Provenance (`FACT`)
- The protocol and script were committed in `acf0125`, before the run. Same software as M5. Runtime 2 min 41 s.
- No deviations from the protocol.
- **Self-checks:** all passed (`results/screen.json`).
  - V-a: the L0 rebuild equals `magnets.layout`.
  - V-b: σ-scaling against the real s0.67 table, relative difference 1.5e-13.
  - V-c: ER2's L0 and L1 values reproduced exactly (difference 0).

## Results (`FACT`; full table in `report.md`)
- **F1, signed strength mixes of corner–edge and edge–centre pairs: 24 / 24 fail.** No mix has the edge slide, the
  edge cross and the layer stiffness all non-negative. The stated superposition argument holds.
- **F2, offset edge–centre pairs (−4 to +4 mm): 5 / 5 fail.** An outward offset raises the layer stiffness (to 1.46)
  and the slide stiffness but makes the cross mode worse (to −1414). An inward offset does the reverse.
- **F3, core-to-piece pairs:**
  - Every tangential mode becomes restoring: edge slide and cross, and corner tangential, all scale with σ².
  - Edge spin and corner twist get exactly 0, because the pairs are axisymmetric.
  - Layer stiffness rises, and so does the static detent torque over a turn.

| Variant | Magnets | Edge spin / slide / cross (mN m/rad) | Corner twist / tangential | Layer (N m/rad) | U-turn peak (N m) | Screen |
|---|---|---|---|---|---|---|
| core σ=1 alone | 40 | 0 / +130 / +123 | 0 / +186 | +0.75 | 0.071 | fail (layer) |
| **core σ=2 alone** | 40 | 0 / +522 / +490 | 0 / +743 | **+3.01** | **0.285** | **PASS** |
| core σ=3 alone | 40 | 0 / +1174 / +1104 | 0 / +1672 | +6.77 | 0.642 | fail (turn torque) |
| core σ=2 + L0 (M5 + core) | 88 | +122 / **−1441** / +1486 | +118 / +46 | +5.01 | 0.325 | fail (slide) |
| core σ=3 + L0 | 88 | +122 / **−785** / +2100 | +118 / +977 | +8.77 | 0.669 | fail |
| core σ=2 + L1 | 88 | +59 / +1085 / **−430** | 0 / +740 | +4.00 | 0.332 | fail (cross) |
| core σ=3 + L1 | 88 | +59 / +1739 / +186 | 0 / +1667 | +7.77 | **0.688** | fail (turn torque) |
| **core σ=3 on edges + L1** | 72 | +58 / +1693 / +195 | 0 / 0 (no corner magnets) | **+3.25** | **0.305** | **PASS** |

- **Both passing variants have margin +0.010.** In both, the limiting term is the screen's −1 mN m/rad tolerance
  applied to a mode with exactly zero stiffness: spin and twist, and every corner direction in the edges-only variant.

## Interpretation (`INFERENCE`)
1. **Core-to-piece magnets are the only tested family that removes the negative piece stiffness behind the M5 rest
   slip.** With the core fixed, a piece is held relative to the core rather than to its moving neighbours, and the
   ball joint absorbs the radial pull. The face-pair families cannot do this (F1 and F2).
2. **Keeping M5's corner–edge magnets and adding core magnets does not work** at σ ≤ 3. The corner–edge slide
   instability, −1971 mN m/rad, is too strong.
3. **The candidates differ:**
   - **core σ=2 alone** is simpler: 40 magnets, no face magnets. It is restoring in every piece direction except
     spin and twist, has the higher layer stiffness, and the lower detent.
   - **core σ=3 on edges + L1** leaves corners with no magnets at all. They would be held only by contact and
     friction, as in the no-magnet arm, which drifted slowly (D10 A4).
4. **What the screen does not show:**
   - turning behaviour: whether the extra detent of about 0.3 N m fits within the turner's 1 N m alongside friction
     (M5 turner torque p99 was 0.62 N m);
   - drift during sequences;
   - whether a magnet of σ = 2 (about twice the volume of a 4×2 mm N35, at the same grade) physically fits
     between a piece and the core;
   - validity of the near-field model for that size.

## Proposed next steps (`PROPOSAL`; each needs the user's approval)
- (a) A **physical-fit and literature check** of core-positioning magnets: CAD of a piece–core magnet seat, and a
  search for documented real-cube core-magnet designs. The B1 cube geometry cannot show fit.
- (b) **V-checks for the σ=2 magnet size**, as D8 did for 4×2 mm: near-field table and V3 tilt validation for the
  chosen real magnet.
- (c) An **unscored dynamic rehearsal** of the chosen variant on new seeds:
  - rest slip count, as D11;
  - the move-sequence battery, against M5's criteria, to check turns and drift.
- (d) Only then a **new pre-registration (M6)** with new seeds. It must disclose that the design was chosen after
  M5 failed.
