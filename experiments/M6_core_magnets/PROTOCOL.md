# M6 — Core-magnet implementation checks (PROTOCOL, fixed before any run)

**Status:** approved in P-59 (user: "i approve recommendations", 2026-11-18). Written by the main session and
committed **before** the first M6 run. Unscored model checks. They change no record and select no mechanism. M5 stays
NOT PASSED. The dynamic rehearsal is not part of M6 and needs separate approval.

## Question (fixed)
> Does the MuJoCo implementation of the real-radius core layout (`core_layout()` passed to `MagnetSystem`) with 4×3 mm
> N52 magnets at c = 0.2 mm reproduce ER6's statics, conserve momentum and energy inside MuJoCo, depend only on body
> poses, and stay inside the force law's validated near-field regime during every face turn?

## Implementation under test (`FACT`, from the code)
- `src/rubiknetic/cube_physics/magnets.py`:
  - `core_layout(mp, clearance=2e-4)` emits 20 coaxial attracting pairs, one per edge and corner, at ER5's real radii
    (22.04 mm edge, 21.95 mm corner). The piece magnet sits at u·(R + wall + L/2) on the piece body; the core magnet
    sits at u·(R − c − wall − L/2) on `core`. Both moments point along +u.
  - `MagnetSystem(..., mags=...)` accepts any magnet list. The default (the 48-magnet corner–edge `layout()`) is
    unchanged.
- **Magnet:** `MagnetParams(diameter=4 mm, length=3 mm, grade="N52")`, wall 0.4 mm, default table grid and
  quadrature. The N52 table is built into `experiments/M6_core_magnets/tables/` (not tracked).
- **Model:** the M1 cube with `radial_preload=0`, at M5's piece gap of 0.05 mm. The magnets have no collision geometry,
  and their positions lie inside the B1 piece volumes (P-58 abstraction).

## Self-checks (all must pass, otherwise the results are not used)
- **S1, table scaling.** The SHA-256 of ER5's 4×3 N35 table must equal the hash recorded in `er5_4x3_N35.json`. The
  N52 table's four raw arrays (C0, Cp, Cm, Ct) must equal the N35 arrays × (1.455/1.19)², with max |difference| ≤ 1e-9
  of the array's max |value|. This carries ER5's validation (V1, V3a, V3b, V3-turn) to N52 by the exact grade scaling
  of the ideal model.
- **S2, ER6 reproduction.** Through `MagnetSystem` in the MuJoCo model, with layer poses set on the joints, the
  following must match ER6's row `N52 c=0.2mm` (`experiments/ER6_real_placement_screen/results/screen.json`) within
  1e-6 relative:
  - the layer stiffness on all six faces. Method as ER3's `measure`: −(τ(+δ) − τ(−δ)) / 2δ, with δ = ER3's DLT and τ the
    magnet torque on the layer's bodies about the face normal, taken about the cube centre;
  - the U-turn torque profile at 0°, 1°, …, 90°. The tolerance is 1e-6 of the profile's peak.

## Checks (pass criteria fixed)
- **V4, Newton and angular momentum.** 20 random states (seed 81). Each ball-jointed piece is rotated by a normal
  random rotation vector of 2° per component, and each centre by a normal 2°. Then a random face is turned by a uniform
  0–90°. Pass: |ΣF| / Σ|F| < 1e-9 and |Σ(T + p × F)| / (Σ|F| × 0.03 m) < 1e-9 (D8's V4 normalisation).
- **V5, energy inside MuJoCo** (D8's design). The R layer turns as one rigid body on the R centre's hinge, and every
  other piece is fixed to the core (D8's `build_r_hinge_model`). Contacts, gravity, damping and friction are off. The
  R layer is released 3° off square.
  - Primary: RK4, 0.5 ms, 0.5 s. Pass: max |E(t) − E0| ≤ 1 % of the magnet energy exchanged, with E the kinetic plus
    potential energy from MuJoCo plus the magnet energy.
  - Reported only: implicitfast at 0.5 ms for 0.5 s, and implicitfast for 5 s at 0.5 ms and 0.25 ms (D8's drift
    diagnostic).
- **V6, pose-only callback** (D8's design). With the U layer posed at 2°, changing ctrl, time, qvel and act leaves the
  magnet generalised forces bit-identical. The installed callback's contribution to `qfrc_passive` matches the direct
  call within 1e-12. The magnet force must be non-zero.
- **Near-pair survey.** Each of the six faces is turned by θ = −90°, −89°, …, +90°, with the rest of the cube at home.
  For every magnet pair on different bodies within r2 = 8 mm:
  - **pass** requires all three:
    - no pair whose axes are more than 45° from parallel, which would switch the force-law branch;
    - no clamped |z|: |z| ≥ L + 0.1 mm for every near parallel pair;
    - no near pair between two pieces. ER5's V3-turn validated only piece-to-core pairs.
  - **reported:** the number of near pairs per pose, and the largest tilt within r2. ER5's real-placement trajectories
    reached 18–20°.

## Reported only
- Idle throughput (steps/s) of the M1 rig model with no magnets and with the core layout installed, single process.
- `MagnetSystem.stats` from V5 (calls, clamped z, near perpendicular, max near tilt).
- Environment: commit, tracked changes, MuJoCo, NumPy, SciPy and Python versions, platform.

## Verdict (fixed)
"**M6 implementation checks pass**" only if S1, S2, V4, V5 (RK4), V6 and the survey all pass. Otherwise the failing
parts are reported and nothing is used dynamically.

## Limits (fixed)
- Accuracy against the fine charge model is not re-run. It rests on ER5 (N35) and on S1's exact grade scaling, which
  assumes ideal rigid magnetisation, as all project magnet models do.
- D8's caveat stands: the ideal model may overstate real force by up to 1.5× (`ASSUMPTION`).
- V5 tests a rigid-layer turn only, because free pieces held only by attracting magnets have no stable equilibrium
  without contacts (Earnshaw; D8 V5 note).
- The magnets have no collision geometry. Whether the stiffness suffices in dynamics (rest slip and sequence drift) is
  the dynamic rehearsal's question, not M6's.
- Deviations after the first run are recorded in the M6 summary.
