# ER5 — Force-law validation for core-positioning magnet sizes: summary (2026-11-17)

Unscored (PROTOCOL.md; approved in P-57). It changes no record and selects no mechanism. M5 stays NOT PASSED.
Labels: `FACT`, `INFERENCE`, `PROPOSAL`.

## Provenance (`FACT`)
- The protocol and script were committed in `eb00add`, before the run. Same software as M5 (MuJoCo 4.0.1,
  NumPy 2.5.4, SciPy 1.18.1, Python 3.12.3, WSL).
- One run, both sizes in parallel. Each size's table build took about 530 s; wall time 4523 s (4×3) and 4694 s (5×2).
  Output: `results/er5_<size>.json` and `run_log.txt`. The tables (`tables/`, git-ignored) can be regenerated, and
  their SHA-256 hashes are recorded in the JSONs.
- **No deviations from the protocol.** Two side activities, neither of which touched the run:
  - While the run was in progress I ran short timing probes in separate processes; they may have slowed it.
  - One probe would have built a MagnetSystem against D8's table folder. I stopped it before it wrote anything; no
    file under `experiments/D8_alignment/` is newer than the ER5 protocol.
- **Limitation:** the result JSONs keep D8's summary fields for V3a and V3b but not the per-case rows, so the
  offset at which 5×2 fails V3a is not recorded.

## Results (`FACT`)
Verdict per size (fixed rule): **neither size is "validated for the core layout"**.

| Check | 4×3 mm N35 (moment 1.50× of 4×2) | 5×2 mm N35 (1.56×) |
|---|---|---|
| V1, on-axis field | 3.6e-15 — pass | 1.9e-13 — pass |
| V3a, facing pair | F 0.008, T 3.0e-5 / 7.9e-5 — pass | F 0.035, **T 1.8e-4 / 7.8e-5 — FAIL** |
| V3b, validated tilt | 7.5° — pass | 5° — pass (7.5° fails) |
| V3c, whole L0 cube (reported only) | max F error 0.003 | max F error 0.005 |
| V3-turn, B1, edge | **FAIL**: 22–28°, 31–59°, 62–68° | **FAIL**: 18–72° |
| V3-turn, B1, corner | **FAIL** (torque only): 10–13°, 16–19°, 35–37°, 53–55°, 71–74°, 77–80° | **FAIL**: 7–83° |
| V3-turn, real, edge | **pass, 91/91°**; worst torque error 4.1 % of the largest fine torque (limit 5 %) | **FAIL** (torque): from 12° |
| V3-turn, real, corner | **pass, 91/91°**; worst torque error 3.9 % | **FAIL** (torque): from 10° |
| V4, Newton and angular momentum | 2.7e-15 — pass | 3.7e-15 — pass |

- Force errors are relative to each size's facing-pair normal force at 1.0 mm (1.92 N for 4×3, 2.22 N for 5×2).
- No pair within r2 was beyond 45° from parallel in any trajectory, so the force law's branch switch was never
  reached. The largest tilts within r2 were 30–32° (B1 edge) and 18–20° (real placement).

## Why B1 fails: the placement is not physically possible (`FACT` from geometry, `er5_checks.core_layout`)
- In B1 the pieces sit at different radii: edges at 13.5 mm and corners at 16.5 mm from the centre. A corner's core
  magnet therefore reaches 16.05 mm, which is outside the 13.87 mm inner radius of the edge-piece magnets.
- As the U layer turns, the edge piece magnet passes the corner's core magnet. At 45° their centres are 2.67 mm apart
  (4×3), only 0.60 mm along the core magnet's axis and 2.60 mm sideways. That is less than the magnet length (3 mm) and
  less than the diameter (4 mm), so **the two magnets would intersect** (tilt ignored). It is the same for 5×2
  (2.54 mm, −0.39 mm axial, 2.51 mm lateral).
- The worst B1 edge errors (F up to 1.86 × Fn for 4×3, 3.36 × Fn for 5×2, at θ = 45°) occur in exactly that
  configuration.
- The B1 corner failures for 4×3 are torque only (worst 9 % of the largest fine torque, limit 5 %), at tilts of 8–15°
  to its own core magnet, beyond the 7.5° validated tilt.

## Interpretation (`INFERENCE`)
1. **4×3 mm N35 in the real (ball-core) placement is accurate along the whole turn**, at 0–90° for both edge and
   corner. It also passes V1, V3a, V3b and V4. The fixed verdict is still "not validated", because the protocol
   required both placements. The real-placement margin is modest (4.1 % against 5 %).
2. **The B1 placement of ER3's candidate is not a buildable geometry.** A core holding magnets at corner radius sweeps
   through the edges' magnets. This is a flaw in ER3's static screen setup, not in the force law: ER3 evaluated only
   static poses near home, where the clash does not appear. Fixing the force law there would model something that
   cannot exist.
3. **5×2 mm N35 is not usable with the current table grid.** It fails the plain facing pair (V3a, torque) and the real
   trajectory from 10–12°. A wider magnet at the same gap probably needs a finer or wider near-field grid; that was not
   tested.
4. **No force-law revision is indicated by these results** for the 4×3 real-placement case. A revision would matter
   only for B1 (not physical) or for 5×2 (where the facing-pair table already fails, so a tilt treatment alone would
   not fix it).
5. **Carried over from ER4:** 4×3 has 1.50× the moment of a 4×2. ER4's moment-scaling estimate needed 1.36× (edges)
   and 1.64× (corners) to match the B1 σ=2 stiffness at 0.2 mm clearance. So corners may fall short, by about
   (1.50/1.64)² ≈ 0.84 of target (moment scaling, not computed with the 4×3 tables).

## Proposed next steps (`PROPOSAL`; each needs the user's approval)
- (i) Record ER5 (P-58). No force-law revision.
- (ii) Settle ER4 open question 1 in favour of the **real-radius placement**: core magnets in a ball core at about
  21.4 mm and piece magnets at about 22.4 mm, as an abstraction inside the B1 cube model (the magnets have no collision
  geometry). Then:
  - re-run ER3's static screen for that placement with the validated 4×3 tables (layer and piece stiffness, detent);
  - add a sweep check that no magnet passes through another during turns.
- (iii) Then the M6 implementation in MagnetSystem, with V5, V6 and the near-pair survey, before the unscored dynamic
  rehearsal (c).
