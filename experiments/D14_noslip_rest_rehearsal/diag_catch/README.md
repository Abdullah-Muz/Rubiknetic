# D14 diagnostic — the `scr20inv_s16400` jam and the ~6° turn catch (UNSCORED, diagnostic only)

**Status.** Requested by the user on 2026-11-24 ("Look into the s16400 U2 jam first, before spending the ~8 hours";
"approved" for this write-up and a sensitivity check). Not part of any protocol. It does not change any record, verdict or
signal of D14 Stage 3. Stage 3b stays stopped at 26 / 294 trials until the user decides (`../results/stage3_run_log.txt`).

**Code and environment (`FACT`).**
- All runs go through the committed Stage 3b worker (`d14s3_run.worker`, NoSlip 10) unchanged, at repo commit `0b63a56`.
  The only addition is extra read-only step hooks stacked on Stage 2's `LoggedTrial`.
- Environment: WSL2 Ubuntu 24.04, MuJoCo 4.0.1, Python 3.12.3.
- **Reproduction checks.** The instrumented rerun of `scr20inv_s16400` matches the committed Stage 3b record exactly:
  every `per_move` entry, plus pass, fail reasons, sim time and growth slope. So does the smoke test on
  E1-2 `U_s16100` (PG20). The hooks do not change the trajectory.
- **Nothing was written under `../results/`.**
- **Files.**
  - Raw outputs are in `raw/` (git-ignored, 65 MB, regenerable).
  - Extracted numbers are in `catch_summary.json` (from `extract.py`) and `static_sweep.json`.

| Script | What it does |
|---|---|
| `diag_s16400.py` | Rerun of one trial. Logs the turner, layer and contact torques on every U move: every 10 ms, and every 2 ms on moves 10 and 29. |
| `diag2_catch.py` | Single-turn trials (E1-2 job with the move and seed changed). Logs per step: magnet torque and axial force on the turning layer, every contact on the layer (normal split into axial, radial and tangential), piece offsets and tilts, centre angles. `DIAG_GRAV=0` turns gravity off. It also saves `qpos` at the turn's ramp start. |
| `static_sweep.py` | No dynamics. Takes the saved ramp-start `qpos`, rotates the turning layer rigidly through 0–12° and records cubie–cubie overlaps. Variant "ideal" removes every layer piece's tilt first. |

## 1. What happened in `scr20inv_s16400` (`FACT`)

The trial is 40 moves: a 20-move scramble and its inverse.
- Moves 0–28 are clean: turn error within ±0.05°, non-target drift ≤ 0.45°.
- **Move 29 (U2) jammed.**
  - The first quarter caught at 6.3° (0.91 N·m) and broke through.
  - The second quarter caught at **96.6°**. The turner sat at the 1 N·m clip for about 1.1 s, with the turner at 97.9°,
    so the pads did not slip.
  - The resisting torque came from contacts between U-layer pieces and the R centre (`cubie_p00`), about +0.76 N·m.
  - The rest, about 0.24 N·m, is consistent with the magnets' peak axis torque on that move (0.25 N·m). It was not logged
    per step in this rerun.
- **The record's "45° short" is a release artefact.**
  - The commanded target kept ramping to 180° during the stall. `TurnRig.rotate` has no stall handling.
  - When the pads opened at 2.6 s, the turner swung towards 180° and dragged the layer from 96.6° to 134.8° before
    contact ended.
  - The scored turn error (45.16°) is computed correctly from the final pose; the jam angle itself was 96.6°.
- Both fail reasons ("M1 criteria", growth slope 0.286°/move) come from this one move.

## 2. The catch is a step, not friction (`FACT` unless marked)

**Same angle every time.** Every turn measured peaks at **6.2–6.8°**. That covers 27 single turns (all six faces, three
designs, four seeds, gravity on and off) and every U move of `s16400`.

**Two causes overlap at that angle.**
- **The magnets.** Their axis torque rises smoothly to a peak just before the catch window. This is always present.

  | Design | Magnet axis torque peak | Angle of the peak | Magnets' pull along the turn axis |
  |---|---|---|---|
  | PG20 | 0.25 N·m | 5.7–5.9° | 8.0–8.7 N |
  | PG8 | about 0.16 N·m | | 3.5–4.2 N |
  | L0 | 0.08 N·m | 4.3° | about 0.5 N |

- **A contact catch.** This is a narrow spike, about 6.0–6.6° wide.
  - On PG20 U `s16100` the turner torque goes 0.27 → 0.86 → 0.29 N·m between 5.0° and 7.0°.
  - It is a corner of the turning layer against the adjacent slice's face-centre piece, at the layer boundary
    (height 0.0–0.1 mm), radius 28.2 mm, overlap 0.03–0.065 mm.
  - **The contact normal is at 45°** (axial 0.71, tangential 0.65). That is the corner's 1.4 mm bevel riding on the
    centre's edge.
  - One such contact carries about 8–9 N normal force and 0.18–0.19 N·m axis torque. Friction (μ 0.2) at that load and
    radius could give only about 0.05 N·m, so the torque comes from the normal force's tangential component.
  - When no catch occurs, contacts add about 0 N·m at the peak.

**Contact torque at the peak in the 16 default turns (gravity on):**

| Turn | Contact torque at the peak (N·m) |
|---|---|
| PG20 U, seeds 16100–16103 | 0.71, 0.25, 0.37, 0.15 |
| PG20 R, seeds 16100–16103 | 0.00, 0.22, 0.02, 0.31 |
| PG20 F, D, L, B (seed 16100) | ≤ 0.03 |
| L0 R | 0.68 |
| L0 U | 0.26 |
| PG8 R | 0.36 |
| PG8 U | 0.02 |

**Gravity off (PG20 U, seeds 16100–16103):**
- Peak turner torque goes 0.97 / 0.66 / 0.63 / 0.41 → 0.63 / 0.27 / 0.27 / 0.32 N·m.
- The catch disappears in 3 of 4. In `s16100` it halves (0.71 → 0.37 N·m), on the same pair.
- L0 R: 0.68 → 0.40 N·m, although gravity is not along R's axis.
- So gravity enlarges the catch on U, but is not its only cause.

**Static sweep (no dynamics).** The layer is rotated rigidly from the ramp-start state, each piece keeping its own tilt.
- In the turns that caught, the worst layer-to-rest overlap jumps at **5.5–6.25°** from about 0.01 mm to 0.05–0.17 mm,
  on the same corner ↔ centre pairs as the dynamic contact.
- With every layer piece's tilt removed ("ideal"), no jump appears in any case.
- Step size and catch torque move roughly together, but not tightly:

  | Static step (mm) | Catch torque (N·m) |
  |---|---|
  | L0 R: 0.153 (gravity on), 0.172 (gravity off) | 0.68, 0.40 |
  | PG20 U `s16100`: 0.126 (gravity on), 0.086 (gravity off) | 0.71, 0.37 |
  | Several steps ≤ 0.05 | 0 |
  | PG20 U `s16103`: no step at the ramp-start pose | 0.15 |

**Reading (`INFERENCE`).**
- Pieces sit on ball joints about the cube centre and can tilt within soft-contact compliance. Some turning-layer
  corners sit 0.05–0.17 mm below the top of the adjacent centre, against a 0.05 mm piece gap.
- For the first ~6° the corner passes over the V between the two bevels. At ~6° its flat face meets the centre's edge
  and must climb the 45° bevel.
- Gravity adds to the tilt on U, the top layer.
- PG20's magnets resist with about 0.25 N·m just before the window, which leaves about 0.75 N·m for the catch. That is
  why PG20 U moves reach the clip first: 34 of 281 PG20 U moves ≥ 0.95 N·m and 6 at the clip, against 0 of 453 moves on
  other faces in the Stage 2 + 3b records.
- L0 and PG8 show the same catch, with more margin.

## 3. Limits
- These are diagnostic runs on rehearsal seeds. They are not pre-registered and not scored.
- Coverage is small: 27 single turns and one sequence.
- Magnet torque was not logged per step in the `s16400` rerun.
- The static sweep uses the ramp-start pose, not the pose at the catch.
- **Physical credibility is unverified.** A real cube retains pieces with interlocking feet in the core, not ball joints.
  Whether the tilt (angular piece play, P-26's "B1 base") and the resulting step are real, or an artefact of the
  abstraction combined with the 0.05 mm gap (P-30/P-31), is open. That calls for an engineering review, not a
  parameter change.
