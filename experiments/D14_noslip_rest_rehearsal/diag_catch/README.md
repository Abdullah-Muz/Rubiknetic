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
| `extract.py` | Writes `catch_summary.json` from `raw/`. Both rerun scripts accept `DIAG_OVR` (JSON M1Params overrides) and `DIAG_TAG`. |
| `edge_patch.py`, `edge_check.py`, `edge_sweep.py` | Rounded-edge swap (`DIAG_EDGE_R_MM`), its geometry checks, and the static sweep with rounded edges (§3b). |
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

## 3. Sensitivity check (`FACT`; diagnostic only, nothing adopted)

**Variants.** Each was applied as an extra M1Params override, through the same worker:

| Variant | Override |
|---|---|
| G10 | `gap` 0.10 mm |
| G20 | `gap` 0.20 mm (M4's registered gap) |
| SI | `cubie_solimp` width 0.5 → 0.1 mm, so contacts are stiffer at small overlaps; gap 0.05 mm |

`cubie_solref`'s time constant (1 ms) is already 2 × the timestep, so it was not lowered.

**Runs.**
- The 8 single turns that caught at baseline.
- The 40-move `scr20inv_s16400` sequence, a new trajectory under each override.
- Raw outputs: `raw/sens_*`, `raw/diag_scr20inv_s16400_{G10,G20,SI}.json.gz`. Extracted numbers: `catch_summary.json`.

**Single turns.** Contact torque at the peak, in N·m:

| Turn | baseline | G10 | G20 | SI |
|---|---|---|---|---|
| PG20 U 16100 | 0.71 | 0.04 | 0.00 | 0.75 (turner at the 1 N·m clip) |
| PG20 U 16101 | 0.25 | 0.71 | 0.71 | 0.35 |
| PG20 U 16102 | 0.37 | 0.00 | 0.00 | 0.00 |
| PG20 U 16103 | 0.15 | 0.00 | 0.00 | 0.00 |
| PG20 R 16101 | 0.22 | 0.00 | 0.00 | 0.07 |
| PG20 R 16103 | 0.31 | 0.00 | 0.09 | 0.33 |
| L0 R 16100 | 0.68 | 0.40 | 0.31 | 0.39 |
| PG8 R 16100 | 0.36 | 0.45 | 0.03 | 0.35 |

- Catches of ≥ 0.15 N·m: 8 / 8 at baseline, 3 / 8 with G10, 2 / 8 with G20, 5 / 8 with SI.
- Every peak stays at 6.0–7.1°.
- Largest single-turn non-target drift: 0.82° with G10, **1.74°** and 1.53° with G20, 0.39° with SI. The baseline single
  turns did not save drift.

**Sequence.**

| Variant | Outcome | Max drift | Max turner torque |
|---|---|---|---|
| baseline | jam at move 29 | 0.45° | 1.00 |
| G10 | all 40 moves pass | **0.98°** (limit 1°) | **0.99** (2 moves ≥ 0.95) |
| G20 | no jam, but **24 / 40 moves fail drift > 1°** | 1.80° | 1.00 (one move, completed) |
| SI | **jam at move 9** (B2, at the clip) | 0.61° | 1.00 |

**Reading (`INFERENCE`).**
- Within what can be varied without changing the model's structure, no setting removes the catch.
- A larger gap makes catches rarer but not smaller (PG20 U 16101 rose to 0.71 N·m with both G10 and G20), and it brings
  back the non-target drift that failed M4 (P-26, P-37).
- At 0.10 mm both margins are nearly gone in the one sequence tried.
- Stiffer small-overlap contacts do not help.
- So the catch and the drift look like two faces of the same angular piece play in the B1 ball-joint abstraction:
  narrowing the gap trades one for the other. The abstraction itself, free tilt about the cube centre, was not varied.

## 3b. Rounded piece edges (`FACT`; diagnostic only, nothing adopted)

**Geometry.** Requested by the user on 2026-11-24 ("Rounded-edge test first").
- `edge_patch.py` swaps `m1_model._chamfered_box_vertices` in the worker process for a faceted rounded box. The repo's
  model code is not edited.
- The half-size stays the same (9.475 mm), so the gap stays 0.05 mm.
- Edges and corners are rounded at radius R, with fillet facets every 30°. The first facet meets each face at 15°,
  against 45° for the current chamfer.
- The rounded box has 104 hull vertices.
- Variants: E14 (R 1.4 mm, the current chamfer size) and E25 (R 2.5 mm).
- `edge_check.py`: extents unchanged, no cubie–cubie contact in the solved pose.

**Static sweep** of the saved baseline catch poses (`edge_sweep.py`).
- The step the corner must climb keeps its height (0.12–0.17 mm), but it is spread over more angle:

  | Edge | Step angle | Step width |
  |---|---|---|
  | chamfer | 5.5–6.0° | about 0.5° |
  | E14 | 5.0–6.0° | about 1° |
  | E25 | moves out to about 10–12° | about 2° |

**Dynamic runs.** The same 8 single turns and the 40-move `scr20inv_s16400` sequence.

| | baseline chamfer | G10 (gap 0.10 mm) | **E14** | **E25** |
|---|---|---|---|---|
| Single turns: largest contact torque at the peak | 0.71 N·m | 0.71 N·m | **0.07 N·m** | **0.07 N·m** |
| Single turns: largest peak turner torque | 0.97 N·m | 0.98 N·m | **0.36 N·m** | **0.31 N·m** |
| Single turns: largest non-target drift | (not saved) | 0.82° | 0.44° | 0.50° |
| Sequence outcome | jam at move 29 | 40 / 40 pass | **40 / 40 pass** | **40 / 40 pass** |
| Sequence: max turner torque | 1.00 N·m | 0.99 N·m | **0.38 N·m** | **0.31 N·m** |
| Sequence: max drift | 0.45° | 0.98° | **0.53°** | **0.51°** |
| Sequence: moves ≥ 0.95 N·m | 2 (to move 29) | 2 | **0** | **0** |

- With rounded edges, every PG20 peak is close to the magnets' own resistance (about 0.25 N·m) plus the rig.
- L0 R's peak falls 0.74 → 0.19 (E14) / 0.15 N·m (E25), close to P-67's realism reference of about 0.2 N·m.
- No solver iteration limit is hit (max 33).

**Reading (`INFERENCE`).**
- The catch is caused by the 45° chamfer's steep lead-in meeting the pieces' tilt.
- A rounded lead-in removes it at the 0.05 mm gap, keeping drift well inside the 1° limit in these runs.
- This removes the gap-versus-drift trade-off seen in §3.

**Not shown.**
- Rest holding (E1-1), snap-back and forgiveness (E1-5), abuse cases (E1-6), long sequences beyond one seed, and E1-7 with
  rounded edges.
- Whether a rounded edge is what a real cube has: secondary sources point to 2–3 mm fillets (§4, unverified).
- Adopting it would be a model change needing the user's approval and a re-run of the earlier rehearsal stages.

## 4. Real-cube clearances (`UNVERIFIED`; search summaries only, pages not read)

A web search on 2026-11-24 found no primary or manufacturer data on speedcube internal clearances. Secondary sources, as
summarised by the search tool:
- A 3D-printing service's design blog reportedly suggests about 0.2 mm clearance for sliding parts and 2–3 mm fillets so
  misaligned parts do not jam.
  [Sculpteo, 2016](https://cdn2.sculpteo.com/blog/2016/04/06/3d-printing-and-twisty-puzzles/)
- A retailer's blog reportedly says a 3x3 can turn while a layer is about 45° out of alignment ("corner cutting").
  [SpeedCubeShop](https://speedcubeshop.com/a/blog/corner-cutting)

The pages were not opened in this session: no fetch tool without a subagent, and CLAUDE.md rules out subagents. These
are pointers for an engineering review, not evidence.

## 5. Limits
- These are diagnostic runs on rehearsal seeds. They are not pre-registered and not scored.
- Coverage is small: 27 single turns and one sequence.
- Magnet torque was not logged per step in the `s16400` rerun.
- The static sweep uses the ramp-start pose, not the pose at the catch.
- **Physical credibility is unverified.** A real cube retains pieces with interlocking feet in the core, not ball joints.
  Whether the tilt (angular piece play, P-26's "B1 base") and the resulting step are real, or an artefact of the
  abstraction combined with the 0.05 mm gap (P-30/P-31), is open. That calls for an engineering review, not a
  parameter change.
