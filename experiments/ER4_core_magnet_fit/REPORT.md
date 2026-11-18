# ER4 — Physical fit and literature check of core-positioning magnets (2026-11-17)

**Status:** step (a) of P-56. The candidate under review is ER3's "core σ=2 alone": 20 core-to-piece magnet pairs,
one per edge and corner, each with twice the moment of a 4×2 mm N35 magnet in the B1 model. Research report;
unscored. Labels: `FACT`, `INFERENCE`, `ASSUMPTION`, `PROPOSAL`. Sources accessed 2026-11-17.

## Summary
- **(1) Real cubes use the concept (`FACT`, product level).** Commercial speedcubes put magnets in a ball-shaped core
  that interact with the corner pieces, and in some designs with the edges. No source gives magnet sizes, forces or
  geometry.
- **(2) It fits a real mechanism (`FACT`, from the GrabCAD real-mechanism cube).**
  - A ball core of radius up to about 21.9 mm clears every edge, corner and centre cap in every orientation. Each
    piece's innermost point is then 0.1–0.3 mm from the core.
  - The piece feet have room for coaxial magnets of at least 6.3 mm (edges) and 9.8 mm (corners) diameter.
- **(3) Strength (`INFERENCE`, static).** Matching the B1 candidate's stiffness in the real geometry needs a magnet
  of about 1.4× (edges) to 1.6× (corners) the moment of a 4×2 mm N35, at 0.2 mm clearance. Examples are 4×3 mm or
  5×2 mm N35; that size fits.
  - This rests on moment scaling. The near-field model is validated only for 4×2 mm, so the claim needs V-checks
    (step b).

## 1. Literature (what each source establishes)
| ID | Source | Type | What it establishes (`FACT` about the source's statements) | Limits |
|---|---|---|---|---|
| S1 | GANCUBE, "GANCUBE Core Technology Evolution: Cube Stability Improvements", <https://www.gancube.com/blogs/gans-technology/gancube-core-ctech-st> | Manufacturer blog; no author or date shown | 2020: the GAN 11 M Pro has a core with "eight omnidirectional magnetic components" and "an innovative omnidirectional core positioning technique". 2021: "Magnetic Core 2.0", "a record 30° automatic alignment", with corner magnets that "produced repulsion". | No counts beyond 8, no sizes, no polarity per pair, no geometry. Marketing text. The URL `.../gancube-s-magnetic-system-evolution` returned the same article. Only the first 100,000 of 106,639 characters were read. |
| S2 | L. Terzich, "What is a Ball-Core?", KewbzUK, 2025-02-03, <https://kewbz.co.uk/blogs/cubing-blogs/what-is-a-ball-core> | Retailer blog | A "rounded, ball-shaped core" adds "an additional track of magnets between the corners and the core". Some designs put magnets in the edge bases that repel the core magnets, "auto-aligning" past 45°. | No numbers. Products are not named. |
| S3 | J. J. Lee, US10583351B2 (published as US20200023266A1), "Puzzle cube and a method for making same", priority 2018-07-17, <https://patents.google.com/patent/US20200023266A1/en> | Patent (individual applicant) | Attracting magnets between the corner bases (3 per corner) and the edge plate lips (2 per edge). The feet form a spherical inner surface; **the core is not magnetic**. Stated purposes: alignment, stability, resisting over-rotation. | A corner–edge (M5-like) design at the feet, **not** core magnets. Only the first 100,000 of 125,291 characters were read. |

- **Not read (HTTP 403):**
  - <https://makerworld.com/en/models/1065200-speedcube-maglev-adjustable-core>, a 3D-printable cube. A search
    snippet says it uses "16x Ø4x1.5" core magnets. **Unverified.**
  - The Justia copy of S3.
- **Search-snippet claims, unverified:** "MoYu WeiLong WR M V9 ball core" with edge-to-core repulsion; "20-magnet"
  cores (MoYu Weilong V11 SE manual).
- **Not found (blocked):** engineering data on commercial core magnets (sizes, grades, separations, forces), or a
  core-magnet patent by GAN or MoYu.
- `INFERENCE`: S1 and S2 show that core-to-corner magnets are realisable and in commercial use. The layout used in
  commerce (8 core magnets aimed at corners, with edges repelled by them) differs from ER3's candidate (20 dedicated
  attracting pairs). It was not screened in ER3 and could be a further static-screen variant.

## 2. Physical fit in a real mechanism (`FACT`; `er4_fit_geometry.py`, `results/fit_geometry*.json`)
- **Source geometry:** the GrabCAD "Rotatable Rubik's Cube 3 x 3 x 3", a local git-ignored mesh
  (`third_party_cad/Assembled_Rubiks_Cube.glb`).
  - Licence unconfirmed (`docs/research/CUBE_MECHANISM_FINDINGS.md` §3). Only measured numbers are reported; no
    geometry is committed.
  - Its core is a spider: a hub of radius 7.48 mm plus arms to the caps.
- **Closest approach to the cube centre:**
  - every edge and corner: 21.93 mm;
  - every centre cap: 22.04 mm;
  - the stickers lie further out.

  Pieces keep their distance from the centre as layers turn. So a ball core of radius R < 21.93 mm clears every
  moving part in every orientation.
- **With the existing hub, a core magnet would face its piece across about 14.5 mm** (hub 7.49 mm, piece at
  21.95–22.04 mm). That is far too weak. The concept requires a **ball core** (cf. S1, S2), not the spider hub.
- **Room in the piece feet** (largest coaxial cylinder inside the part, measured by ray casting along the piece's
  radial line):

  | Depth from the inner surface | Edge | Corner |
  |---|---|---|
  | 0.5 mm | radius 3.17 mm | radius 4.91 mm |
  | 2 mm | radius 3.38 mm | radius 4.91 mm |
  | 3 mm | radius 9.50 mm | radius 5.70 mm |

  - A 5 mm diameter magnet fits in an edge foot, leaving at least 0.67 mm of wall.
  - A 6 mm magnet fits in a corner foot.
  - The CAD pieces are solid. Real moulded pieces are hollow shells, so the room needs checking on real parts
    (`ASSUMPTION`).
- The meshes are not watertight, so the signed-distance values in part 1 were discarded and ray casting was used.

## 3. Strength needed in the real geometry (`INFERENCE`; `er4_pair_equivalence.py`, `results/pair_equivalence.json`)
- **Setup:** one core-to-piece pair, coaxial on the piece's radial line, piece magnet in the foot, core magnet in a
  ball core with clearance c. Static tangential stiffness about the cube centre, using `magnets.pair_forces` with the
  validated 4×2 tables:

  | Magnet | Edge (r = 22.04 mm), c = 0.1 / 0.2 / 0.3 mm | Corner (r = 21.95 mm), c = 0.1 / 0.2 / 0.3 mm |
  |---|---|---|
  | 4×2 N35 | 311 / 280 / 253 mN m/rad | 308 / 278 / 251 |
  | 4×2 N52 | 464 / 419 / 379 | 461 / 416 / 376 |
  | B1 candidate target (core σ=2) | 522 | 743 |

- **What it implies:**
  - Stiffness scales with the square of the magnet moment. At c = 0.2 mm the target needs about 1.36× (edges) and
    1.64× (corners) the moment of a 4×2 N35: for example 4×3 mm (1.5×) or 5×2 mm (1.56×) N35, or 5×2.5 mm (1.95×).
    All of these fit the room in §2.
  - This assumes the stiffness of a finite magnet scales with its moment at about 1 mm separation. **Not validated:**
    the near-field tables exist only for 4×2 mm. That is step (b).
- **Comparison with B1:** B1's candidate places the pairs at 13.5–16.5 mm radius. The real geometry places them at
  about 22 mm, which gives a longer lever arm. The B1 σ=2 candidate therefore corresponds to a smaller real magnet
  than "2× moment".

## 4. Open questions and risks
1. **The model's geometry differs from the real cube's.** B1's pieces and core are not the real mechanism's. A
   decision is needed on whether an M6 model would:
   - keep B1 with core pairs at B1 radius, scaled to match the real-geometry stiffness (as above);
   - or move the pairs to the real radius.

   Both are abstractions to document.
2. **Detent and turning.** The static detent of the B1 candidate is 0.285 N m. Commercial cubes report "auto
   alignment" (S1: 30°), which suggests a similar detent. Its effect on the turner's 1 N m budget is untested
   (step c).
3. **Commercial layouts differ.** Repelling edge-to-core pairs (S1, S2) were not screened. They could reach the same
   piece stability with fewer core magnets.
4. **Hollow real parts and core manufacturing (a ball core with 20 seats)** are unverified.

## 5. Proposed next steps (`PROPOSAL`; each needs the user's approval)
- **(b) V-checks for the real magnet size**, as D8 did for 4×2 mm: build the near-field table for the chosen size
  (for example 4×3 or 5×2 mm N35) and run the V1–V3 validations.
- **(a′) Optional:** a static screen of the commercial-style layout (8 core-to-corner pairs plus edge repulsion),
  using ER3's machinery.
- **(c) An unscored dynamic rehearsal** of the chosen variant on new seeds: rest slip count plus the sequence battery.
