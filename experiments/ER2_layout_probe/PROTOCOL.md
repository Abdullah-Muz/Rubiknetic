# ER2 — Magnet-layout stiffness screen (O1) and 0.025 mm rest rehearsal (O2): PROTOCOL, fixed before any run

**Status:** approved in P-54 (user: "all aproved", 2026-11-17; the interpretation is recorded there). Written by the
main session and committed **before** the first ER2 run. Exploratory and unscored. It cannot change M5's verdict
(NOT PASSED, P-51) and selects no mechanism. Any candidate needs the user's approval and a new pre-registration with
new seeds.

## Background (`FACT`, ER1)
At the aligned pose, the M5 layout (48 × 4×2 mm N35 on the corner–edge faces) gives:
- layer stiffness +2.03 N m/rad (restoring);
- single-piece stiffness −0.42 to −0.93 N m/rad (destabilising).

ER1 identified this as the cause of the rest slips.

## Part O1 — static stiffness screen (no dynamics)

### Questions (fixed)
> Is there a magnet layout, using the same magnets, that keeps every piece non-destabilised while keeping each layer
> restoring? How large are its piece and layer stiffnesses compared with M5's layout?

### Candidate layouts
All candidates use 4×2 mm N35 magnets with M5's wall and depth, and the same placement rule as `magnets.layout`: on
a face centre, at depth wall + length/2. For a magnet pair across the interface from piece A to piece B (unit vector
e from A to B), "attract" means both moments point along e, and "repel" means B's moment is reversed.

| ID | Layout | Magnets |
|---|---|---|
| L0 | corner–edge, attract (M5 as built) | 48 |
| L1 | edge–centre, attract (each edge to its 2 centres; each centre to its 4 edges); corners have no magnets | 48 |
| L2 | L0 + L1 | 96 |
| L3 | corner–edge, repel | 48 |
| L4 | L1 + corner–edge repel | 96 |
| L0-g025 | L0 at piece gap 0.025 mm (part of O2) | 48 |

### Model and measurements
- Aligned M5 model (B1, rigid radius), piece gap 0.05 mm, except L0-g025.
- The magnet force law is `rubiknetic.cube_physics.magnets.pair_forces` with M5's near-field tables.
  - `ASSUMPTION`: its near-field correction was validated (V3) for D8's attracting corner–edge pairs. For repelling
    pairs (L3, L4) and edge–centre pairs it is used as is; those results are flagged accordingly.
- Measurements, at the aligned pose:
  - (i) net magnet torque about the cube centre on every body;
  - (ii) for each of the 20 corner and edge pieces, its 3 × 3 rotational stiffness matrix K = −∂τ/∂θ. τ is the magnet
    torque about the cube centre on that piece and θ its small rotation vector, with all other pieces aligned.
    Central differences of ±0.02° (inside the ±0.106° free play), symmetrised. Its smallest eigenvalue is reported;
  - (iii) for each of the 6 centres, the spin stiffness about its own axis;
  - (iv) for each of the 6 face layers, the whole-layer stiffness about the face axis.

### Screen (fixed; descriptive, not a G1 criterion)
A layout **passes the static screen** if all three hold:
1. every piece's smallest eigenvalue is ≥ −1 mN m/rad (tolerance for finite-difference noise);
2. every centre's spin stiffness is ≥ −1 mN m/rad;
3. every layer's stiffness is ≥ 1.0 N m/rad, about half of L0's +2.03 N m/rad, to keep a comparable self-alignment.

A passing layout is reported as a **candidate** only. Its next steps (V-checks, an unscored dynamic rehearsal, a
pre-registration) each need the user's approval.

## Part O2 — rest rehearsal at 0.025 mm on new seeds (dynamics, unscored)

### Question (fixed)
> With M5's layout (L0), does halving the piece gap to 0.025 mm reduce the size or frequency of rest slips, compared
> on the same new seeds at 0.05 mm?

### Runs
- **Seeds:** 14000–14019. A repository search found no use of these seeds. After ER2 they count as used for
  diagnostics and must not be reused for scoring.
- **Two arms**, each with every seed:
  - **G050:** frozen M5 settings, 0.05 mm gap;
  - **G025:** identical except the piece gap is 0.025 mm, for both the cube model and the magnet layout.
- Rest is 60 s, using D10's instrumented loop with D10's logging. Setup is drawn from the seed, as in M5.

### Reported (fixed; no decision rule)
Per arm:
- the slip-event count using D11's definition (≥ 0.2° change within 200 ms, merged per cubie), in 0–10 s and in
  0–60 s, with Clopper–Pearson 95 % intervals;
- event sizes;
- the 0–10 s peak per seed (the M5 rest metric), and the number of seeds above 0.5°;
- the per-seed paired difference between G025 and G050 peaks.

## Limits (fixed)
- O1 is static, local (±0.02°) and evaluated at the aligned pose only. It screens; it validates nothing.
- O2 uses 20 seeds per arm, so frequencies have wide intervals. It is a rehearsal, not a scored test.
- Neighbour gaps at t0 are not measured in O2 (that would need ER1's probe 1).
- Changes after the first run are recorded as deviations in the ER2 summary.
