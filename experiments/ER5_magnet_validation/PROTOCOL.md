# ER5 — Force-law validation for core-positioning magnet sizes (PROTOCOL, fixed before any run)

**Status:** approved in P-57 (user: "b", 2026-11-17). Written by the main session and committed **before** the first
ER5 run. Unscored. It changes no record and selects no mechanism. M5 stays NOT PASSED.

## Question (fixed)
> Is the project's magnet force law (`rubiknetic.cube_physics.magnets.pair_forces`, with its near-field tables)
> accurate for 4×3 mm and 5×2 mm N35 magnets, both in D8's facing-pair checks and along the trajectories that
> core-to-piece pairs follow during layer turns?

## Background (`FACT`)
- D8 validated the force law for 4×2 mm N35 face pairs. Validated tilt: 5° (`d8_1b_checks.json`).
- The near-field correction is a second-order expansion in tilt. It applies only to pairs within r2 = 8 mm whose
  axes are within 45° of parallel (`magnets.py`).
- Face pairs stay parallel during turns. **Core pairs do not:** as a layer turns by θ, a piece magnet tilts by θ
  relative to its core magnet while it is still near it. For example, at B1's edge radius of 13.5 mm, the magnet is
  still within 8 mm of its core magnet at θ of about 30°. This is the reason for V3-turn.

## Sizes
- S1: 4×3 mm N35 (D8 Br 1.19 T).
- S2: 5×2 mm N35.

Wall 0.4 mm and the default table grid, as in D8. Tables are built into `experiments/ER5_magnet_validation/tables/`.
Nothing is written under `experiments/D8_alignment/`.

## Checks per size
- **V1, on-axis field.** The discretised charge model against the closed-form on-axis field of the cylinder
  (`magnet_force.py` functions), at z = 0.5, 1, 2 and 4 mm. Pass: relative error ≤ 1e-3.
- **V3a, facing pair** (D8's `v3` part (a), unchanged). Hybrid law against the fine charge model at 32 × 96, over
  gaps 0.5–1.5 mm and lateral offsets 0–6 mm. Pass, as D8:
  - force error ≤ 5 % of the aligned facing-pair normal force at 1.0 mm;
  - torque error ≤ max(5 % of the largest reference torque in the set, 2e-5 N m).
- **V3b, tilted pairs** (D8's part (b), unchanged): tilts of 2, 5, 7.5 and 10°. Pass: validated tilt ≥ 5°.
  - D8's whole-cube part (c) uses the corner–edge layout. It runs as part of D8's function and is **reported only**.
- **V3-turn, new (layout-specific).**
  - **Setup:** the 20 core magnets of the candidate (one per edge and corner direction). One moving piece magnet,
    rotated about the U axis with its piece by θ = 0°, 1°, …, 90°, for one U-layer edge and one U-layer corner.
  - **Two placements:**
    - (i) **B1:** ER3's geometry. The piece's innermost point is at |c|(pitch + gap)/2, with a 0.05 mm gap.
    - (ii) **Real:** ER4's geometry. The piece's inner surface is at 22.04 mm (edge) or 21.95 mm (corner), with a
      0.2 mm core clearance.

    In both, the piece magnet sits at wall + L/2 outward of the piece surface, and the core magnet at wall + L/2
    inward of the core surface.
  - **Comparison:** at every θ, the total force and torque on the moving magnet from all 20 core magnets, hybrid
    against fine. The fine model uses 32 × 96 for pairs within r2 and 6 × 16 beyond.
  - **Pass:** at every θ, force error ≤ 5 % of S's facing-pair normal force at 1.0 mm, and torque error ≤ max(5 % of
    the largest fine torque along that trajectory, 2e-5 N m).
  - **Also reported:**
    - the θ range that passes;
    - the largest tilt within r2;
    - the number of pairs within r2 whose axes are more than 45° from parallel, where the force law switches branch.
- **V4, Newton and angular momentum, core layout.** 20 random states: each of the 20 pieces rotated randomly about
  the centre by up to 5°, then a random U-layer turn of 0–90°. Pass: |ΣF| and |Σ(T + p × F)| ≤ 1e-9 relative to the
  largest per-magnet force and torque in that state.

## Verdict per size (fixed)
"**Validated for the core layout**" only if V1, V3a, V3b (≥ 5°), V3-turn (all θ, both kinds, both placements) and V4
all pass. Otherwise the failing parts and the failing θ ranges are reported.

ER5 does not revise the force law. A revision, for example a tilt treatment valid to large angles, would be a separate
step needing approval.

## Not in scope
V5 (energy in MuJoCo), V6 (pose-only callback) and the near-pair survey test a MuJoCo implementation of the core
layout. That implementation does not exist yet; those checks belong to it. V2 (supplier force) is not repeated. D8's
finding that the ideal model may overstate real force by up to 1.5× carries over (`ASSUMPTION`).

## Limits (fixed)
- Ideal rigid magnetisation (μ_r = 1).
- Two placements and one turn axis (U). Other faces are equivalent by symmetry.
- Deviations after the first run are recorded in the ER5 summary.
