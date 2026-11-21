# ER9 side checks (2026-11-20): real-magnet equivalents and fit in a real mechanism

These are exploratory measurements made while the Part E probe ran. They are unscored, involve no simulation, and are
not part of any committed protocol. Two subagents did the work, writing only to the session scratchpad. The main
session spot-checked the key claims (files `main_session_spotcheck.py`) and copied scripts and numeric results here.

Paths inside the scripts point to the scratchpad they ran from. To rerun one, point its input and output paths at
this folder.

## `catalogue/`: which real magnets match the simulated strength scales
- **`scale`.** It multiplies Br², so pair forces, stiffnesses and energies go with `scale` to the first power
  (`magnets.py`, `MagnetParams.moment`). Checked: moment ratio = sqrt(0.756).
- **Targets.** Coaxial pull, axial and lateral stiffness of one pair, per arm (`targets.json`). `scale.json`'s values
  are reproduced exactly.
- **Shortlist.**
  - W3: 3 × 3 N45/N42 at a face gap of about 1.8–1.9 mm.
  - Hybrid at 1 and 2 mm clearance: 4 × 2 N35/N45, which is M5's magnet type.
  - The same 4 × 3 N35 at a larger gap matches pull but is 5–23 % softer.
  - Data: `scan.json`, `extras.json`.
- **Availability.** Vendor pages were read on 2026-11-20 (supermagnete, first4magnets). Stated tolerance is ±0.1 mm
  on dimensions, which is about ±9–13 % in pull. No pull or Br tolerance is stated beyond the grade range.
- **Largest open uncertainty.** Vendor pull is 0.61–0.87 of the ideal model. If that ratio holds across an air gap,
  the matching gaps shift by about 0.5 mm. A bench measurement would settle it.
- **Force-law note (checked).** At 2 and 3 mm anchor clearance the pairs sit in the 5–8 mm near/far blend. There the
  simulated pull is 7.1 % below the charge model at 2 mm (0.386 vs 0.416 N), and within 1 % at 3 mm. Reported in the
  agent's run, not rechecked: the 3 mm arm's axial stiffness is 27 % low.
- **Validity.** Of the shortlist, only 4 × 3 magnets (any grade, by Br scaling) have a table validated to 20° of
  tilt. Using 4 × 2 for anchors would need its table validated beyond 5°. 3 × 3 has no table.

## `realfit/`: do the anchor magnets fit the real-mechanism CAD pieces?
Measured on the git-ignored GrabCAD mesh used by ER4. Its licence is unconfirmed, so only numbers are kept: no
geometry and no derived mesh. The simulation and CAD frames were checked to coincide (`stage0*`). ER4's on-axis radii
are reproduced (22.037 / 21.947 mm).

- **Corner anchors (3 per corner at 16° toward the centres): do not fit.**
  - Along each pair's line the corner has no material until 25.0 mm. The 4 × 3 magnet spans 22.35–25.35 mm, so 83 %
    of it is in air.
  - Spot-checked in the main session: material from 24.99 to 36.86 mm along the line.
  - In this CAD, three magnets per corner fit only as 3 × 2 at 5.5–7° (toward the centres) or 5.5–14° (toward the
    edges). That is outside Part A's screened range (10–16°).
- **Edge anchors (2 per edge at 20°): do not fit as 4 × 3.**
  - Along the line, material runs from 21.94 to 31.72 mm (spot-checked). The cylinder's side breaks out of the foot
    by up to 0.58 mm (3.5 % of its volume), into space the centre piece occupies.
  - 4 × 3 fits from 6° to 16.5°. 4 × 2 and 3 × 2 fit at 20° with a 0.42 / 0.45 mm wall.
- **Magnet spacing: no overlaps.** Magnets in the same piece and in the core never come within 0.5 mm. The closest
  core magnets are 4.58 mm apart at 0.2 mm clearance and 3.29 mm at 3 mm.
- **Core cover at 0.2 mm clearance: thin.** A single ball core has 0.20–0.29 mm of material over the core magnets,
  against the 0.4 mm assumed. The layout's core radius also differs between edges and corners (21.84 vs 21.75 mm).
- **Hybrid: M5's corner–edge magnets fit.** Every 4 × 3 at M5's positions lies inside the CAD piece, with no clash
  with the anchors (at least 3.99 mm away). The CAD's piece gap is 0.25 mm, against 0.05 mm in the simulation.
- **Not determined:**
  - whether any feasible placement still holds the pieces (no forces were computed);
  - real moulded pieces, which are hollow;
  - other cube designs;
  - how a 48-seat ball core would be manufactured.
