# ER6 — Static screen of real-radius core magnets, with a no-intersection sweep (PROTOCOL, fixed before any run)

**Status:** approved in P-58 (user: "all approved", 2026-11-17). Written by the main session and committed **before**
the first ER6 run. Static and unscored. It changes no record and selects no mechanism. M5 stays NOT PASSED.

## Question (fixed)
> With core-to-piece magnets in the real-radius (ball-core) placement, using the ER5-validated 4×3 mm magnet, does
> the core layout pass ER3's static screen? And do any two magnets intersect during any face turn?

## Background (`FACT`)
- ER3's candidate "core σ=2 alone" used the B1 placement. ER5 showed that placement is not buildable: at a 45° U turn
  an edge magnet would pass through a corner's core magnet (ER5 SUMMARY).
- ER5: 4×3 mm N35 passes V1, V3a, V3b (7.5°), V4 and V3-turn (0–90°, edge and corner) in the real placement at
  0.2 mm clearance.
- ER4: in the GrabCAD real mechanism the innermost points of the pieces lie at about 22 mm from the centre, and a ball
  core of R < 21.93 mm clears every part.

## Layout (fixed)
- **20 pairs**, one per edge and corner, coaxial on the piece's radial line u, attracting (same direction u).
  - **Piece magnet** on the piece body at u·(R + wall + L/2).
  - **Core magnet** on the `core` body at u·(R − c − wall − L/2).
  - R is ER5's real radius: 22.04 mm for edges and 21.95 mm for corners. Wall is 0.4 mm and L is 3 mm.
- **Abstraction (documented):** these positions are inside the B1 model's piece volumes. The magnets have no
  collision geometry. The B1 pieces' own inner geometry is not the real mechanism's.
- **Magnet:** 4×3 mm, using ER5's 4×3 N35 near-field table (`experiments/ER5_magnet_validation/tables/`, SHA-256
  checked against `er5_4x3_N35.json`; nothing is written there).
- **Grades by exact scaling:** in the ideal rigid-magnet model the field scales with Br, so every pair interaction
  scales with Br₁·Br₂. N42 and N52 are therefore ER3's per-magnet σ = Br/Br(N35), using the project's grade table:
  1.0924 and 1.2227. ER3's V-b check showed this identity to 1.5e-13.

## Variants (fixed)
Grades N35, N42 and N52, each at clearance c = 0.1, 0.2 and 0.3 mm: **9 variants**, 40 magnets each, M5's piece gap
(0.05 mm).

## Static screen (ER3's `measure`, unchanged; ER3's fixed criteria)
- **Measured:**
  - per-piece stiffness, including mode values (edge spin, slide, cross; corner twist, tangential);
  - centre stiffness;
  - layer stiffness on all six faces;
  - the static U-turn torque profile, 0–90°, and its peak.
- **Pass:** all four must hold:
  - minimum piece eigenvalue ≥ −1 mN m/rad;
  - minimum centre stiffness ≥ −1 mN m/rad;
  - minimum layer stiffness ≥ 1.0 N m/rad;
  - U-turn peak ≤ 0.5 N m.
- **Reported only:**
  - ER3's B1 σ=2 values for comparison: slide 522, cross 490, corner tangential 743 mN m/rad, layer 3.01 N m/rad,
    peak 0.285 N m;
  - every stiffness and torque divided by 1.5. This is D8's caveat that the ideal model may overstate real force by
    up to 1.5×; all these quantities are linear in pair strength. Whether the derated layer stiffness is still
    ≥ 1.0 is also reported.

## No-intersection sweep (new)
- **Poses:** each of the six faces turned by θ = −90°, −89°, …, +90°, with the rest of the cube at home and the core
  fixed.
- **Pairs checked:** every pair of magnets on different bodies whose centres are closer than the sum of their
  bounding-sphere radii plus 0.5 mm.
- **Clearance:** each magnet's surface is sampled at a spacing of at most 0.05 mm. The clearance is the minimum
  signed distance from one magnet's samples to the other solid cylinder, taken both ways; negative means
  intersection.
- Run at c = 0.1, 0.2 and 0.3 mm. The grade does not affect geometry.
- **Pass:** clearance > 0 for every pair at every pose. Reported: the minimum clearance, with the pair and pose.

## Self-checks (all must pass, otherwise the results are not used)
- **S1:** ER3's "core σ=2 alone" row reproduced with ER3's own functions: minimum eigenvalue, mode minima, minimum
  layer stiffness and turn peak, relative difference ≤ 1e-9.
- **S2:** the SHA-256 of ER5's 4×3 N35 table equals the hash recorded in `er5_4x3_N35.json`.
- **S3, positive control:** the sweep run on ER5's B1 placement with the same magnet must report an intersection
  (clearance < 0) on the U turn.
- **S4, accuracy:** the sampled clearance matches the exact value within 0.02 mm for:
  - two coaxial magnets 1.000 mm apart, end to end;
  - two parallel magnets side by side with a 0.500 mm surface gap.

## Limits (fixed)
- Static and local (±0.02°) about the aligned pose, plus the static turn profile. No dynamics.
- ER5's V3-turn validated the force law at c = 0.2 mm only. The 0.1 and 0.3 mm variants (facing gaps of 0.9 and
  1.1 mm) lie inside V3a's validated gap range of 0.5–1.5 mm, but their turn trajectories were not separately
  validated.
- Grade scaling assumes ideal rigid magnetisation, as all project magnet models do.
- A passing variant is a design candidate. The variant to implement in M6 goes to the user first (P-58).
- Deviations after the first run are recorded in the ER6 summary.
