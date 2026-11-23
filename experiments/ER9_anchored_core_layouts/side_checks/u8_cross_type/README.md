# U8 side check: point-dipole error for cross-type (4 × 2 with 4 × 3) magnet pairs

Date: 2026-11-22. This is an exploratory side measurement for open issue U8 in
`../../proposals/PART_G_FINAL.md` (option 2: measure first). It is unscored. It runs no MuJoCo simulation, builds no
MuJoCo model, changes no record and decides nothing about P1. All numbers come from `u8_dipole_error.py`, and the
full output is in `results.json` and `run_log.txt`.

Labels: **FACT** = computed by `u8_dipole_error.py` in this folder. **INFERENCE** = reasoning from those numbers.
**ASSUMPTION** = an input taken as given.

## 1. What was compared

- **Simulated term (what Part G would use).** `magnets.cross_pair_forces` from the repo, called directly. It treats
  the two magnets as point dipoles, gives each its own moment, and applies the far taper (1 below 20 mm).
- **Reference.** The magnetic surface-charge model of two uniformly magnetised cylinders with μr = 1, summed with
  the repo's own disc quadrature (`magnets.disc_points`, 16 × 48, the `TABLE_QUAD` of the near-field tables).
  - This is the model `magnets._exact_energy_tilted` uses to build the same-type tables, generalised to two
    different cylinders.
  - Force and torques are summed directly from the charge-to-charge forces, not taken by finite differences.
- **Magnet types (ASSUMPTION: Part G defaults, as in `tests/test_magnets_composite.py`).**
  - 4 × 2 mm N35, scale 1: m = 0.02380 A·m².
  - 4 × 3 mm N52, scale 1 (U3 default): m = 0.04365 A·m².
  - Layout: pitch 19 mm, gap 0.05 mm, core clearance 0.2 mm.
  - Both models are linear in each moment, so every **relative** error below holds for any 4 × 3 grade. Absolute
    values scale with the grade's Br/1.455.
- **Error measures, per pair.**
  - Relative error in |F|.
  - Vector error |F_dip − F_ref| / |F_ref|.
  - F along r̂, in both models.
  - Angle between F_dip and F_ref.
  - Each magnet's torque about its own centre, as a relative error and normalised by |m||B_dip|. The normalised
    form is needed because the 4 × 2 magnet's own torque is small: its moment lies close to the partner's field, so
    its plain relative error is large even where the absolute error is tiny.
  - Torque about the cube centre on each magnet's body (T_own + p × F), which is what turns a piece. It is reported
    only for actual poses: in the r-sweeps the lever arm changes with r, so that number has no physical meaning there.

## 2. Reference-model checks (FACT)

| Check | Result |
|---|---|
| Identical cylinders: our charge sum against the repo's `_exact_energy_tilted` (4 × 2 N35; 4 × 3 N52) | 4.4e-16, −3.3e-16 relative |
| Force against −∇U by central differences (oblique cross pair at about 7.4 mm) | 3.3e-10 relative |
| Torque against −dU/dθ by central differences | 7.5e-10 relative |
| Angular-momentum balance, T1 + T2 + r × F2 = 0 | 3.8e-15 relative |
| Quadrature ladder (8×24, 12×36, 16×48, 24×72, 32×96) at the closest geometries (7.3 mm on the home orientation; 8.176 mm core pair; 5.91 mm tilted case) | 16 × 48 differs from 32 × 96 by ≤ 7.7e-14 in F, T1 and T2. Coarsest (8 × 24) ≤ 1.4e-7 |
| Quadrature pattern rotated about each magnet's axis | ≤ 2.3e-14 change in F |
| Independent model: each cylinder cut into 192 / 576 / 1280 volume cells, one point dipole per cell | Coaxial 4 × 2 pair at 8 mm: F differs from the reference by 0.34 / 0.09 / 0.03 %. Home-closest cross pair: F 0.37 / 0.22 / 0.14 %, T1 0.63 / 0.07 / 0.04 %, T2 0.26 / 0.13 / 0.08 %. Both converge toward the reference |
| Point-dipole limit, F, at 30 mm / 60 mm (untapered dipole against the reference) | 0.43 / 0.11 % (piece orientation), 0.34 / 0.09 % (core orientation), 0.40 / 0.10 % (2° tilted). Under 1 % |
| Same limit for the 4 × 3 magnet's own torque, and for energy | T2 ≤ 0.33 % at 30 mm. U ≤ 0.36 % at 30 mm |
| Same limit for the 4 × 2 magnet's own torque (small, see §1) | Normalised by \|m\|\|B\|: 1.1 % at 30 mm, 0.28 % at 60 mm (falls as 1/r², a finite-size effect). Plain relative error 9.9 % / 2.7 % for the piece orientation, because the reference torque is near zero |

The reference is converged to machine precision in its quadrature. The physical model is the ideal one and is
confirmed by an independent discretisation. Its limits are listed in §6.

## 3. Which pairs and poses (FACT, with one correction to Part G's text)

Positions come from `magnets.layout()` + `magnets.core_layout()` (PG20). In B1 each piece body frame sits at the cube
centre (ball joint at the origin, `m1_model.py`), so a pose is a rotation of each piece about the origin. These are
pure kinematics, with the same pose form as `test_magnets_composite._set_pose`.

- **Home.** The closest piece-to-piece cross pair is an edge's 4 × 2 face magnet against the neighbouring corner's
  on-axis 4 × 3 piece magnet (e.g. `cubie_nn0` edge with `cubie_nnn` corner), at **9.335 mm**. 24 such pairs lie
  within 10 mm.
  - Axes are 125.3° apart (cos −0.577). r̂ makes 127.6° with the 4 × 2 axis and 107.1° with the 4 × 3 axis.
- **Rigid single-face turns** (6 faces, −90° to 90°, 0.5° steps).
  - **No piece-to-piece cross pair comes closer than its home value of 9.335 mm.**
  - The overall cross-type minimum, **8.176 mm**, is a different class: a 4 × 2 edge magnet against a **core**
    4 × 3 magnet (`cubie_n0p` edge to `core_edge`, U face at −66.97°, refined at 0.01°). Axes are 106.1° apart
    (cos −0.276).
  - The diagnostic Part G cites, `diag_cross.py`, printed exactly this pair (`cubie_n0p/edge - core/core_edge
    cos=-0.276`, 8.176 mm at −67°). **Part G's known-issue box gives 8.178 mm as the edge-to-corner piece pair. That
    looks like a misattribution.**
  - Core-to-4 × 2 pairs are hard-bounded at 8.117 mm, because every magnet's radius is invariant in B1
    (recomputed here: 8.117 mm).
  - PG8 has no `core_edge` magnets, so this 8.176 mm pair exists only in PG20 (INFERENCE from Part G's arm
    definitions; PG8's own minima were not computed).
- **Tilts.**
  - **Deterministic worst case.** Starting from home, rotate the edge, the corner, or both (split ±θ/2) by a relative
    angle θ about the worst of 400 axes. The minimum piece-to-piece cross distance is:

    | θ | r_min |
    |---|---|
    | 0.71° | 9.054 mm |
    | 1.0° | 8.940 mm |
    | 1.5° | 8.744 mm |
    | 2° | 8.549 mm |
    | 3° | 8.164 mm |
    | 5° | 7.413 mm |

    The pair crosses r2 = 8 mm at about **3.4° relative tilt** (interpolated, INFERENCE).
  - **Monte Carlo.** Random per-piece rotation vectors with N(0, σ) per component (the form used by the test), on top
    of rigid turns (half at the worst angle, half uniform), 240 poses per σ, seed 8808. Minimum piece-to-piece cross
    distance:

    | σ | Minimum distance | Poses with a pair below 8 mm |
    |---|---|---|
    | 0.5° | 8.167 mm | none |
    | 1° | 7.115 mm | 11 % |
    | 2° | 5.910 mm | 91 % |

  - The reference was evaluated on 109 of the 1438 candidate pairs below 8.5 mm: per σ, the 20 closest plus 30 at
    random.
  - Their relative tilts reach 11.7°: σ is per component and per piece, so "1–2° tilts" in this form are relative
    tilts of several degrees.
  - 108 of the 109 are the edge-4 × 2 / corner-4 × 3 class.
  - INFERENCE: Part G's 7.3–7.9 mm values came from σ = 1–2° test poses, which correspond to relative tilts of
    roughly 3.5–9°. ER7's worst rest tilt (0.71°, cited in Part G) is far smaller.

## 4. Results

### 4a. Separation sweeps at fixed realistic orientation (FACT)

In each sweep the orientation (both axes and r̂) is held fixed and only |r| is scaled. Columns:

- **|F| err:** relative error in |F|.
- **F vec err:** vector error, |F_dip − F_ref| / |F_ref|.
- **F·r̂ dip / ref:** force on the 4 × 3 magnet along r̂ (from the 4 × 2 to the 4 × 3), dipole / reference.
- **F angle:** angle between F_dip and F_ref.
- **T4x2/mB, T4x3/mB:** each magnet's own-torque error divided by |m||B_dip|.
- **T4x3 rel:** relative own-torque error of the 4 × 3 magnet.

**(i) Piece pair, home orientation** (edge 4 × 2 with corner on-axis 4 × 3; actual r 9.335 mm; it is also the
rigid-turn piece-pair minimum)

| r (mm) | \|F\| ref (mN) | \|F\| err | F vec err | F·r̂ dip / ref (mN) | F angle (°) | T4x2/mB | T4x3/mB | T4x3 rel |
|---|---|---|---|---|---|---|---|---|
| 7.300 | 131.2 | −2.1 % | 8.5 % | −122.6 / −121.5 | 4.75 | 20.3 % | 5.1 % | 7.4 % |
| 7.600 | 111.5 | −2.0 % | 7.7 % | −104.3 / −103.6 | 4.32 | 18.6 % | 4.5 % | 6.6 % |
| 7.900 | 95.4 | −1.8 % | 7.1 % | −89.4 / −88.9 | 3.95 | 17.2 % | 4.1 % | 6.0 % |
| 8.178 | 83.0 | −1.7 % | 6.5 % | −77.8 / −77.5 | 3.65 | 16.0 % | 3.7 % | 5.5 % |
| 8.500 | 71.0 | −1.6 % | 6.0 % | −66.7 / −66.4 | 3.34 | 14.7 % | 3.3 % | 5.0 % |
| 9.000 | 56.4 | −1.5 % | 5.3 % | −53.0 / −52.9 | 2.93 | 13.1 % | 2.9 % | 4.3 % |
| 9.335 | 48.7 | −1.4 % | 4.9 % | −45.8 / −45.7 | 2.70 | 12.1 % | 2.6 % | 3.9 % |
| 10.000 | 36.9 | −1.2 % | 4.2 % | −34.8 / −34.8 | 2.32 | 10.5 % | 2.2 % | 3.3 % |
| 12.000 | 17.7 | −0.8 % | 2.8 % | −16.8 / −16.8 | 1.56 | 7.2 % | 1.4 % | 2.1 % |

**(ii) Core pair, rigid-turn minimum orientation** (edge 4 × 2 with `core_edge` 4 × 3; actual r 8.176 mm; PG20 only)

| r (mm) | \|F\| ref (mN) | \|F\| err | F vec err | F·r̂ dip / ref (mN) | F angle (°) | T4x2/mB | T4x3/mB | T4x3 rel |
|---|---|---|---|---|---|---|---|---|
| 7.300 | 125.9 | −0.9 % | 4.0 % | 71.6 / 76.2 | 2.23 | 1.8 % | 7.6 % | 10.3 % |
| 7.600 | 107.3 | −1.1 % | 3.8 % | 61.0 / 64.8 | 2.09 | 1.7 % | 6.8 % | 9.1 % |
| 7.900 | 92.0 | −1.1 % | 3.6 % | 52.2 / 55.4 | 1.97 | 1.6 % | 6.1 % | 8.1 % |
| 8.178 | 80.1 | −1.2 % | 3.4 % | 45.5 / 48.1 | 1.86 | 1.6 % | 5.6 % | 7.3 % |
| 8.500 | 68.7 | −1.2 % | 3.3 % | 39.0 / 41.1 | 1.75 | 1.5 % | 5.0 % | 6.5 % |
| 9.000 | 54.6 | −1.2 % | 3.0 % | 31.0 / 32.6 | 1.59 | 1.4 % | 4.3 % | 5.5 % |
| 9.335 | 47.2 | −1.2 % | 2.8 % | 26.8 / 28.1 | 1.49 | 1.3 % | 3.9 % | 5.0 % |
| 10.000 | 35.8 | −1.1 % | 2.6 % | 20.3 / 21.2 | 1.32 | 1.2 % | 3.3 % | 4.2 % |
| 12.000 | 17.2 | −0.9 % | 1.9 % | 9.8 / 10.1 | 0.95 | 0.9 % | 2.1 % | 2.6 % |

**(iii) Piece pair, worst 2° relative tilt orientation** (actual r 8.549 mm): vector F error 8.0 / 6.7 / 6.2 / 4.6 %
at 7.3 / 7.9 / 8.178 / 9.335 mm; |F| error −2.9 to −1.8 %; T4x2/mB 19.5 to 11.5 %; T4x3/mB 4.7 to 2.2 % (`results.json`,
`sweep_realistic_orientation`).

The vector error is mostly a direction error of 2–5°; |F| itself is within 3 %.

### 4b. Actual poses (FACT; maxima over the evaluated cases, piece-to-piece class)

| Separation band | n | Rel. tilt | max F vec err | \|F\| err range | max F angle | max T4x2/mB | max T4x3/mB | max body torque about centre: rel / abs |
|---|---|---|---|---|---|---|---|---|
| home, 9.335 mm | 1 | 0 | 4.9 % | −1.4 % | 2.7° | 12.1 % | 2.6 % | 1.5 % / 0.019 mN·m (of 1.28) |
| 8.5–9.5 mm | 7 | ≤ 2° | 5.6 % | −2.1 to −1.4 % | 3.0° | 13.9 % | 2.8 % | 2.9 % / 0.054 mN·m |
| 8.0–8.5 mm, tilt ≤ 3° | 23 | ≤ 3° | 6.0 % | −2.7 to −2.2 % | 3.1° | 14.7 % | 2.9 % | 3.9 % / 0.086 mN·m |
| 8.0–8.5 mm, any tilt | 55 | ≤ 10.3° | 7.9 % | −6.1 to +7.0 % | 3.2° | 15.0 % | 2.9 % | 7.2 % / 0.150 mN·m |
| 7.9–8.0 mm | 6 | ≤ 5.1° | 6.5 % | −3.8 to −3.2 % | 3.2° | 15.2 % | 2.9 % | 5.5 % / 0.131 mN·m |
| **7.3–7.9 mm** | 27 | ≤ 9.3° | **7.4 %** | **−5.1 to −3.3 %** | 3.4° | 15.8 % | 2.9 % | **7.3 % / 0.22 mN·m** |
| below 7.3 mm (5.91–7.12 mm) | 23 | 5.9–11.7° | 12.8 % | −12.4 to −5.3 % | 3.4° | 15.9 % | 8.8 % | 14.5 % / 0.76 mN·m |

- The core pair at its rigid-turn minimum of 8.176 mm: vector F error 3.4 %, |F| −1.2 %, F·r̂ 45.5 vs 48.1 mN
  (−5.5 %), F angle 1.9°, T4x2/mB 1.6 %, T4x3/mB 5.6 %. The body torque about the centre has a relative error of
  2.0 % (0.028 of 1.42 mN·m).
- The core class was not tilt-sampled. Its distance cannot fall below 8.117 mm (§3), where the core-orientation sweep
  gives about 3.4–3.5 %.
- Plain relative errors of the 4 × 2 magnet's own torque reach 54–66 % on the sweeps, and up to 15× in MC cases.
  There the reference torque is near zero; the absolute error is ≤ 0.077 mN·m.
- Context (FACT): a facing corner-edge 4 × 2 pair at home (coaxial, 2.85 mm) pulls with 1.65 N in the reference model.

### 4c. Comparison with the same-type error the repo already handles (FACT)

**Parallel same-type pairs: the branch the near-field table corrects.** The correction has weight w = 1 below 5 mm,
falls to 0 at 8 mm, and is off beyond. The pure-dipole force error is:

| Pair | Offset | 5 mm (w = 1) | 7 mm (w = 0.21) | 8 mm (w = 0) | 9 mm (w = 0) |
|---|---|---|---|---|---|
| 4 × 2 N35 | coaxial | 62 % | 30 % | **22 %** | 17 % |
| 4 × 2 N35 | side by side | 33 % | 19 % | **15 %** | 12 % |
| 4 × 2 N35 | 45° | 39 % | 20 % | **15 %** | 12 % |
| 4 × 3 N52 | coaxial | 33 % | 14 % | **10 %** | 7.8 % |
| 4 × 3 N52 | side by side | 4.9 % | 4.6 % | **4.1 %** | 3.5 % |
| 4 × 3 N52 | 45° | 25 % | 9.0 % | **6.5 %** | 5.0 % |

The independent volume-dipole model confirms the 22 % coaxial figure (§2).

**The same realistic geometries with both magnets of one type.** Vector F error at 8.176 mm:

| Orientation | 4 × 2 + 4 × 2 | 4 × 3 + 4 × 3 | Cross (4 × 2 + 4 × 3) |
|---|---|---|---|
| Piece orientation | 7.0 % | 3.1 % | 6.5 % |
| Core orientation | 5.4 % | 2.9 % | 3.4 % |

At 7.3 mm the piece-orientation values are 9.0 / 4.2 / 8.5 %.

- FACT: the cross-type dipole error lies between the two same-type errors at the same geometry, and is set mainly by
  the flatter 4 × 2 magnet.
- FACT: across 7.3–8.2 mm in rigid and moderately tilted poses, the cross-type error (3.4–8.5 % vector, ≤ 5.1 % in
  |F|) is **smaller** than the dipole error the force law already accepts for parallel same-type 4 × 2 pairs just
  outside r2 (15–22 % at 8 mm).
- It is similar to or smaller than the 4 × 3 values (4–10 %).
- Whether such same-type parallel pairs near 8 mm actually occur in L0/PG motion was **not** checked here.

## 5. What error level each choice would be consistent with (INFERENCE, not a recommendation)

- **Accept the level the force law already accepts at r2 for same-type parallel pairs (≥ 10–22 %).** Every
  cross-type case evaluated down to 5.9 mm (max 12.8 %) is at or below that level. P1's extra 1.0 mm margin would then
  not be needed for accuracy, and `near_cross_type` would serve as a report-only flag.
- **Require ≤ 5 % vector force error.**
  - Core-class pairs meet this everywhere they can go (≥ 8.117 mm gives about 3.5 %).
  - Piece pairs meet it only at r ≳ 9.3 mm (4.9 % at home), i.e. with essentially no tilt. That would argue for a flag
    on piece cross pairs below about 9.3 mm, or a cross-type near-field correction.
  - |F| alone (without direction) stays within about 5 % (max 5.1 %) down to 7.3 mm in the evaluated cases.
- **Require ≤ 10 %.** Every evaluated case at r ≥ 6.5 mm meets it (max 7.9 % at r ≥ 7.3 mm). Cases below about
  6.4 mm, all with relative tilts of 8–12°, exceed it (up to 12.8 %).
  - A runtime flag at r2 = 8 mm (`near_cross_type`) marks the region where the rigid and small-tilt errors exceed
    about 6.5 %.
  - It does not catch everything: strongly tilted poses (7–9° relative) already reach 7.1–7.9 % at 8.2–8.3 mm.
- **P1 as written.**
  - By §3, P1's cross-type rule may already be met: piece-to-piece minimum 9.335 mm ≥ 9.0 mm, and the 8.176 mm
    minimum is a core pair outside r2.
  - That depends on how P1's "piece-to-piece" is read and on P1's own scan code, which does not exist yet.
  - The main session should check this before deciding U8.

## 6. What this does NOT establish

- **No dynamics.** No MuJoCo trial or step was run, so nothing here says how a 3–8 % force error changes any
  rehearsal signal (slip, snap-back, turner torque, drift).
- **No P1 result.** P1 was not run and is not validated. The geometry scan here is this script's own kinematics, not
  `er9g_scan.py`. Middle-slice turns and E1-5-like offset poses were not scanned.
- **Reference is ideal.** Uniform magnetisation and μr = 1: no demagnetisation or induced magnetisation; NdFeB μr is
  about 1.05. Nominal dimensions and mid-range Br are used. Real magnet tolerance (±0.1 mm, Br spread), chamfers and
  vendor pull ratios (0.61–0.87 of ideal, side_checks README) are not modelled, and could be comparable to or larger
  than the dipole errors above.
- **Sampling is not exhaustive.** The tilt sampling is Monte Carlo (seed 8808, 720 poses, 109 reference evaluations)
  plus a one-pair deterministic worst-axis scan. The core class was not tilt-sampled; only its radius bound and the
  fixed-orientation sweep cover it. The "corner 4 × 2 / edge 4 × 3" class appeared once.
- **No grade-specific absolutes beyond N52.** Relative errors are grade-independent; absolute forces and torques are
  for N52.
- **Not a decision.** It does not decide U8, pick a margin, or change any protocol, record or force-law code.

## 7. Reproduce

From the repo root, in WSL. Single-threaded, about 70 s on a loaded machine:

```
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/side_checks/u8_cross_type/u8_dipole_error.py
```

Inputs, versions and the seed are recorded in `results.json["inputs"]`. Reruns are deterministic.
