# ER3 — Static magnet-layout design screen, route B (PROTOCOL, fixed before any run)

**Status:** approved in P-55 (user: "1b, 2", 2026-11-17; the interpretation is recorded there). Written by the main
session and committed **before** the first ER3 run. Static only (no dynamics), exploratory and unscored. It selects
no mechanism. Any layout that passes goes to the user before any V-check, dynamic rehearsal or pre-registration.
M5 stays NOT PASSED (P-51).

## Why these families (`INFERENCE` from ER2's numbers; stated before running)
- **Superposition rules out a plain mix.** ER2's stiffnesses add almost linearly: L2 ≈ L0 + L1, within 2 mN m/rad.
  Write a for the signed strength of the corner–edge pairs and b for the edge–centre pairs. Then:
  - edge slide ≈ 559 b − 1971 a;
  - edge cross ≈ −926 b + 994 a;
  - layer ≈ 1.99 a + 0.99 b (N m/rad).

  No (a, b) satisfies all three with slide ≥ 0, cross ≥ 0 and layer ≥ 1. Family F1 checks this numerically.
- **A new degree of freedom is needed.** Two are tested:
  - F2: moving the edge–centre pairs off the face centre;
  - F3: core-to-piece pairs. These are radial pairs between the fixed core and each edge and corner. Any tangential
    motion of a piece shears such a pair, which restores it, and the radial pull is taken by the ball joint. P-16 lists
    "a core detent" among the allowed passive forces.

## Variants (all 4×2 mm N35 tables; σ = moment multiplier of a magnet group)
Each pair contributes σ_i σ_j times its unit-strength value, because magnet interaction energy is bilinear in the two
magnetisations. "Attract" and "repel" follow ER2's polarity rule: moments point corner → edge, and edge → centre. For
core pairs, moments point radially outward on both magnets (attract).

| Family | Variants |
|---|---|
| F1: signed mix σ_CE·L0 + σ_EC·L1 | σ_CE, σ_EC ∈ {−1, −0.5, 0, 0.5, 1}, not both 0. A negative σ means that pair class is repelling with \|σ\|. |
| F2: L1 with the edge–centre pairs offset in their interface plane, perpendicular to the edge axis (positive = toward the cube's outer surface) | offset ∈ {−4, −2, 0, +2, +4} mm; L1 strength σ_EC ∈ {1} |
| F3: core pairs (CORE) on all 20 edges and corners, with or without the face layouts | σ_CORE ∈ {1, 2, 3}; base ∈ {none, L0 (σ_CE = 1), L1 (σ_EC = 1)} |
| F3e: core pairs on edges only | σ_CORE ∈ {1, 2, 3}; base ∈ {L1} (L1 leaves corners with no magnets) |

- **Core-pair placement** (`ASSUMPTION`; idealised, fit not checked):
  - The piece magnet sits on the piece's innermost point along its radial line: r_p = |c| · (pitch + gap)/2 (13.47 mm
    for an edge, 16.50 mm for a corner), pushed outward by wall + length/2.
  - The core magnet sits coaxially, inward by the same amount. The face-to-face separation equals that of a face pair
    (2 × wall + gap).
  - The chamfer and the real core shape are ignored. Whether a magnet physically fits there must be checked in CAD
    before any use.
- **Strength:** σ_CORE = 2 or 3 would need larger magnets than 4×2 mm, for example about 2× or 3× the volume. Whether
  the 4×2 near-field correction holds for them is an `ASSUMPTION`.

## Measurements (as ER2, plus a turn-torque guard)
At the aligned M5 pose (B1, gap 0.05 mm):
- (i) net magnet torque on every body;
- (ii) each piece's 3 × 3 rotational stiffness matrix (±0.02° central differences, symmetrised), its smallest
  eigenvalue, and ER2's mode split (edge spin, slide, cross; corner twist and tangential);
- (iii) centre spin stiffness;
- (iv) layer stiffness for all 6 layers.

Plus:
- (v) the static magnet torque on the U layer as it turns rigidly from 0° to 90° in 1° steps, with the rest of the cube
  aligned and fixed. The peak |torque| is reported. L0's profile is the reference.

## Screen (fixed; descriptive, not a G1 criterion)
A variant passes if all four hold:
1. every piece's smallest eigenvalue is ≥ −1 mN m/rad;
2. every centre spin stiffness is ≥ −1 mN m/rad;
3. every layer stiffness is ≥ 1.0 N m/rad (ER2's rule);
4. the peak |U-layer magnet torque| over 0–90° is ≤ 0.5 N m. This keeps turns within half the M5 turner limit of
   1 N m.

Passing variants are ranked by their smallest margin, each margin taken relative to its threshold scale:
- rules 1 and 2 against 100 mN m/rad;
- rule 3 against 1 N m/rad;
- rule 4 against 0.5 N m.

## Self-checks (fixed; a failed check stops ER3 and is reported)
- **V-a:** L0 rebuilt here equals `magnets.layout` exactly (as ER2).
- **V-b:** L0 with σ = √0.67 on every magnet agrees with L0 computed from the s0.67 table. Every piece eigenvalue and
  layer stiffness must agree within 1 % (relative to the largest |value|). This validates the σ scaling.
- **V-c:** L0 and L1 at σ = 1 reproduce ER2's `static_screen.json` values within 1e-6 relative.

## Limits (fixed)
- Static, local (±0.02°), aligned pose only, idealised placement. A passing variant is a design candidate, not a
  validated mechanism.
- The far-field taper of the force law (`far_r1`/`far_r2` = 20/25 mm) is used as is.
- Changes after the first run are recorded as deviations in the ER3 summary.
