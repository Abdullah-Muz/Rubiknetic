# D8-1b design proposal — piece-to-piece magnets on a contact cube (PROPOSAL, awaiting user approval)

**Date:** 2026-11-14 · **Decision:** P-18 approved ("Yes begin D8-1b"). This document is the magnet layout and
strength proposal that was promised before any model is built. **Nothing below is built or validated** except the
force calculator `magnet_force.py` and its checks (§4.1).
**Tags:** `FACT` · `INFERENCE` · `ASSUMPTION` · `PROPOSAL`. Sources were accessed 2026-11-14.

## 1. What D8-1b can and cannot fix (read this first)

| Problem | Seen in | Can magnets fix it? |
|---|---|---|
| Misalignment builds up until turns are refused | M2 (D7, D8-0) | **Not on M2** (D8-0). On a contact cube, **possibly**: each piece is pulled into register with its neighbours |
| Layers finish a turn slightly off-square, and forgiveness is one-sided | M1 (E1-5), D5 | **Possibly.** Magnets pull a layer back if it is within about 3–4° of square and its resistance is below the magnet torque (§4.3) |
| Corner twist with almost no resistance (about 12° at 0.02–0.05 N·m) | M1 (D1, E1-6c) | **No** (`INFERENCE` from §4.3): magnets add only 0.001–0.005 N·m per degree. A real cube resists twist with interlocking geometry (feet), not magnets |
| Contact-solver overload above about 1 N·m | M1 (D1) | No. A separate fix already exists (solimp dmax 0.999, D1 config E) |

**Consequence (`INFERENCE`):** M1 plus magnets can at best become a cube that **aligns itself**. It will **not**
meet the current corner-twist negative control (the M2 pre-registration asks for ≤ 2° up to 5 N·m). A contact
cube that resists twist needs interlocking geometry, like D5, which costs speed (62 steps/s).

There is also no measured real-cube twist torque (O-09). That is why we can't yet say what a fair twist threshold
for a contact cube would be.

## 2. Base model (decision needed)

| Option | What it is | For | Against |
|---|---|---|---|
| **B1** | M1 geometry, **rigid radius** (no radial slide), no welds, + magnets | Same cubies as M2. A radial pop is impossible by construction. Each corner's net magnet pull points inward and is absorbed by its ball joint, so it adds no contact friction | D1 config J jammed in a turning check (57° error) and had ~12° of twist play at 0.02 N·m. Magnets may or may not cure the jam |
| **B2** | M1 as scored: 1 N radial preload slide, plus the D1-E overload fix and magnets | Already turns long sequences: 86/86 oracle matches in E1-2…E1-4 | The corners' magnet pull (1.1–5.9 N, §4.3) presses on the slide stop like a higher preload. D1 config K (3 N preload) turned worse. M1's turning torque (0.16–0.68 N·m, E1-0) is larger than every magnet snap torque in §4.3, so the magnets might never pull a layer square |
| **B3** | D5 real-mechanism geometry + magnets | Real twist resistance (1.1° at 0.2 N·m) | 62 steps/s; 1–1.5 mm penetration under grip |

**Recommendation (`PROPOSAL`):** stage 1 tests **B1 and B2 side by side**, with the same magnet code, and **with
and without magnets** (the no-magnet comparison P-16 requires). This is cheap, because both use M1's geometry.
**B3** comes only if stage 1 shows that magnets give self-alignment, and only with your separate approval.

## 3. Magnet layout (`FACT` from sources, then `PROPOSAL`)

**Real speedcubes** (`FACT`):
- "On a standard 3×3, this normally uses 48 magnets." That is 3 per corner and 2 per edge.
- "The magnets inside the corners attract the corresponding magnets inside the edges as a layer approaches
  alignment" (speedcubing.org).
- Newer cubes add corner-core or centre-edge magnets (same source).
- A retailer recommends "strong magnets, ie 4x2mm" for a 3×3, or 4×1.5 mm for slightly weaker magnets (cuboss.com).
  Its table lists 50 per 3×3, which is probably a pack size; the layout count is 48.

**Proposed layout** (`PROPOSAL`), the classic 48-magnet corner–edge system:
- Each **edge** has 2 magnets, one on each face toward its two corners.
- Each **corner** has 3 magnets, one on each face toward its three edges.
- Centres and core have none.
- Each magnet is an axial disc on the face centre, with its axis along the face normal, recessed behind a plastic
  wall w.
- **Polarity:** every corner magnet points north outward and every edge magnet south outward. Corners only ever
  face edges across a layer boundary, in any legal state, so every facing pair attracts.

**Geometry check** (`INFERENCE`, from M1's lattice): across any face boundary, 4 corner–edge pairs face each other
(the R boundary, for example, has M-slice edges UF, UB, DF and DB against the 4 R corners). They sit 26.9 mm from
the turning axis.
- When a layer turns, facing pairs keep parallel axes and slide across each other, so the magnets act as a 4-fold
  detent at every square position.
- At square, each edge's two pulls cancel, and each corner's three pulls add up to a force pointing straight at the
  cube centre, so there is no net torque.

**What the magnets know** (P-16 compliance): only the positions and orientations of the bodies they are fixed in.
They know nothing about commands, targets, the oracle or the switch state. They pull a piece toward its
neighbours, not a layer toward 90°.

## 4. Strength

### 4.1 Force model (`FACT`, `magnet_force.py`, `results/magnet_force.json`)

The model is the magnetic-charge model of uniformly magnetised cylinders, using Br values from public grade tables
(N35 1170–1220 mT, N52 1430–1480 mT; first4magnets.com). Checks:

| Check | Result |
|---|---|
| V1: on-axis field vs the closed-form cylinder formula | agrees to ≤ 4e-15 (relative) |
| Quadrature convergence (24×64 vs 40×96 points, 0.5 mm gap) | 5e-8 |
| V2: two 4×2 mm N45 discs at contact, vs supplier "adhesive force approx. 4,12 N" (supermagnete S-04-02-N, on steel) | model 5.8–6.3 N |

V2 shows the ideal model may **overstate real force by up to about 1.5×**: real steel, coatings and test conditions
lose force. A strength-scale factor is therefore part of the sweep.

Shear (sideways) force peaks at about half the normal force, at an offset of about half a diameter.

### 4.2 Gap between magnet faces (`ASSUMPTION`)

The gap between facing magnets = M1's 0.2 mm piece gap + 2 × wall. Real wall thickness is not measured.

| Wall | Gap |
|---|---|
| 0.15 mm | 0.5 mm |
| **0.4 mm (nominal)** | **1.0 mm** |
| 0.65 mm | 1.5 mm |

### 4.3 Resulting cube-level numbers (`INFERENCE`, small-angle, ideal model)

| Magnets, 1.0 mm gap | Pull per pair (aligned) | Layer snap torque, peak (at angle) | Layer stiffness | Corner-twist stiffness / peak | Corner inward pull |
|---|---|---|---|---|---|
| 3×1.5 mm N35 (weak) | 0.62 N | 0.032 N·m (3.2°) | 0.016 N·m/° | 0.0010 N·m/° / 0.007 N·m | 1.1 N |
| 4×1.5 mm N35 | 1.11 N | 0.056 N·m (4.3°) | 0.025 N·m/° | 0.0016 / 0.012 | 1.9 N |
| **4×2 mm N35 (nominal)** | **1.44 N** | **0.074 N·m (4.3°)** | **0.031 N·m/°** | **0.0019 / 0.016** | **2.5 N** |
| 4×2 mm N52 (strong) | 2.14 N | 0.109 N·m (4.3°) | 0.046 N·m/° | 0.0029 / 0.024 | 3.7 N |

The full table, with 0.5–2.0 mm gaps, is in `results/magnet_force.json`. At a 0.5 mm gap the values rise by about
1.5×.

The magnets add 48 × ≈0.19 g ≈ 9 g to the cube (NdFeB ≈ 7.5 g/cm³, `ASSUMPTION`). That is added to the cubie
masses.

**Prediction to falsify:** a layer snaps square only if its static resistance is below about 0.03–0.11 N·m and it is
within about 3–4° of square. M1 as scored (B2) needs 0.16–0.68 N·m to turn, so B2 may not snap at all. B1 has no
preload wedging, so its resistance should be lower.

### 4.4 Proposed sweep

- Magnets: **none** / 3×1.5 N35 / 4×1.5 N35 / **4×2 N35** / 4×2 N52.
- Gap: 0.5 / **1.0** / 1.5 mm.
- Strength scale: **1.0** / 0.67.

To keep the run count small, the gap and scale variations are run on the nominal magnet only.

## 5. Force law inside the simulation (`PROPOSAL`)

The fine model in §4.1 is too slow to run at every step, and coarse point charges are inaccurate at 1 mm (about
20 % error with 12 points per face; measured). The runtime force law is therefore a hybrid:

1. **All 48 magnets interact pairwise** as point dipoles. That gives exact far-field force and torque, and it is
   conservative.
2. **Near-field correction** for facing pairs with parallel axes. Facing pairs keep parallel axes during any legal
   turn, and the 4-fold layout means near pairs are always parallel or perpendicular. The correction adds
   (U_exact − U_dipole) × w(r):
   - U_exact is a precomputed table of the exact pair energy U(ρ, z), interpolated with a smooth spline;
   - w(r) is a smooth cutoff, so the total energy is a single smooth function and no energy is created by
     switching.
3. It is applied in `mjcb_passive` and added to `qfrc_passive` as equal and opposite force/torque pairs. This
   follows the D5 `detent.py` precedent, so the edit audit (which checks `qfrc_applied` and `xfrc_applied`) stays
   intact.
4. **Validation before any trial:**
   - **V3:** the hybrid matches the fine model within 5 % over the operating range.
   - **V4:** Newton's third law (the sum of all magnet forces and torques is ≈ 0) at every logged step.
   - **V5:** energy conservation. Release a misaligned layer with friction and damping off: kinetic energy plus
     magnet energy stays constant within 1 % (time-step error only).
   - **V6:** the callback reads no command, oracle or switch state (code review plus a unit test).

## 6. Stage-1 test plan (unscored; diagnostic seeds only, never 3000–3999)

| Test | What | Recorded |
|---|---|---|
| T1 snap | Misalign U by ±1…±10° through the logged setup, then release | Return to square: yes/no, residual angle, time |
| T2 forgiveness | E1-5-style: R turn after a ±U misalignment | Completion and legality, both signs |
| T3 sequences | The five D7/D8-0 sequences + `U U' R R' F F'` | Oracle match; max per-piece misalignment after every move and its growth per move (D8-0 metric) |
| T4 effort | Peak turner torque and settle time per turn | vs no magnets |
| T5 abuse | D1-style corner-twist staircase; E1-6b-style opposed torque | Twist vs torque; penetration; stability. Expected to stay weak (§1) |
| T6 energy and impulse | V4/V5 during real trials; magnet power and work per turn | Disclosure required by P-16 |
| T7 throughput | Steps/s with and without magnets | Python callback cost |

Each test runs on B1 and B2, with and without magnets.

**Pre-declared feasibility signals** (for deciding the next step, not G1 thresholds):
- all T3 sequences match the oracle;
- max per-piece misalignment stays bounded (growth < 0.005°/move over 40 moves);
- T1 snaps back from ≥ 3° in both directions;
- V4/V5 pass;
- throughput ≥ 300 steps/s single-process.

If B1 or B2 meets all of these, I would write a pre-registration for it as a G1 candidate, for your approval. The
corner-twist question (§1) would be raised with you before that.

## 7. Cost and risks

- **Compute:** the Python callback for 1,128 dipole pairs plus about 100 near-pair table lookups. My estimate,
  unmeasured, is 0.2–0.5 ms per step, against about 1.6 ms per step for M1 during turns. If it is too slow, it
  could become a MuJoCo C plugin later.
- **Model risk:** the magnets can't be stronger than real ones (P-16 "realistic strengths"). If self-alignment needs
  more than 4×2 N52, that is a finding, not a reason to scale up.
- **Fidelity limit:** B1 cannot represent popping; the spec must disclose this.

## 8. Decisions requested

1. **Base:** B1 + B2 in stage 1 (recommended), or only one of them?
2. **Layout:** the 48-magnet corner–edge layout, without corner-core or centre magnets for now?
3. **Strength:** nominal 4×2 mm N35 at a 1.0 mm gap, with the §4.4 sweep?
4. **Force law:** the dipole plus exact-near-field hybrid in `mjcb_passive`, with V3–V6 before any trial?

## Sources (accessed 2026-11-14)

- speedcubing.org, "The Evolution of Magnets in Speedcubes": <https://speedcubing.org/blogs/news/the-evolution-of-magnets-in-speedcubes> (author and date not shown)
- cuboss.com, "Magnets for Speedcubes": <https://cuboss.com/shop/magnets-for-speedcubes/> (retailer recommendation)
- first4magnets, "Grades of Neodymium Magnets": <https://www.first4magnets.com/neodymium-magnet-information/grades-of-neodymium-magnets> (Br ranges; the page does not say whether they are minimum or typical)
- supermagnete, disc magnet S-04-02-N: <https://www.supermagnete.de/eng/disc-magnets-neodymium/disc-magnet-4mm-2mm_S-04-02-N> (N45, 4×2 mm, adhesive force approx. 4.12 N; conditions not stated)
- A SpeedSolving forum post with a magnet-force formula was found but returned HTTP 403, so it was not read and is not used.
- Project evidence: D1 (`../D1_corner_twist_diagnostic/README.md`), E1 (`../E1_scored/README.md`), E1-0, D5, D8-0.
