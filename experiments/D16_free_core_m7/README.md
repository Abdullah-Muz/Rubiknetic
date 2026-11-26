# D16: free-core M7 rehearsal (UNSCORED, 2026-11-26)

**Why:** P-97 item 3, the first G2 experiment. It carries out P-09's free-core condition for M7. In G1 the core was fixed
to the world. In G2 the cube is free, and arm A holds it with a two-layer stabiliser.

**Model:**
- M7 as scored in G1: L0 magnets, rounded edges R 2.5 mm, NoSlip 10, gap 0.05 mm, timestep 0.5 ms. It is built
  through `E7_scored_m7/run.py`'s `run_trial`, so every G1 per-move check is applied unchanged.
- Plus:
  - **a free core:** a free joint, 1.7 g, diaginertia 2e-8 (as D6; `ASSUMPTION`). The baseline keeps the fixed core;
  - **a stand-in stabiliser** with P-97's sizes: pads 30 wide × 30 deep × 4 mm; μ 0.8; condim 4; on world-fixed
    slides; covering the two layers opposite the turned face.
- The layer is turned by the unchanged G1 rig.
- Setup, before t = 0 and logged:
  - gravity off for 0.3 s while the stabiliser closes, then 0.3 s with gravity;
  - then the harness's 0.5 s settle.
- Each trial is 5 moves: X X′ X2 X′ X, for X = U, R or F.
- Seeds 21000–21003.

**Code and outputs:**
- `run.py`: the runner;
- `analyze.py`, which writes `results/summary.md` and `results/summary.json`;
- `grip_probe.py`, which writes `results/grip_probe.json`;
- `run_log.txt`.

## D16-0: the G1 rig's grip is capped at about 11.5 N (`FACT`, `grip_probe.py`)
The rig pad is a position servo: kp 2000 N/m, target 6 mm beyond contact, force limited to ±`grip_force`. Its squeeze
is therefore at most about kp × 6 mm = 12 N. Measured with the U pads closed on M7:

| Requested `grip_force` (N) | 10 | 16.5 | 20 | 30 | 50 | 50, with 30 mm overshoot |
|---|---|---|---|---|---|---|
| Actuator force (N) | 10.0 | 11.5 | 11.6 | 11.5 | 11.6 | 50.0 |

- **G1's scored trials** drew 10–20 N and actually applied about 10–11.6 N.
- **E1-7's grip levels** of 30 and 50 N actually applied about 11.5 N.
- The G1 report does not claim squeeze coverage; O-10 is listed as unresolved. But
  [`../../docs/research/G2_STEP2_GRIPPER_FINGERTIP_PROPOSAL.md`](../../docs/research/G2_STEP2_GRIPPER_FINGERTIP_PROPOSAL.md)
  §2.1 wrongly called E1-7 partial evidence for O-10 (corrected there).
- D16's stabiliser targets 30 mm beyond contact, so it applies the requested force. The measured median squeeze is
  within 1 N of it.

## Results (`FACT`; `results/summary.md`)
| Configuration | Trials | G1 pass | Observed move correct | Max drift ° | Max pen. mm | Max τ N·m | Max core slip mm |
|---|---|---|---|---|---|---|---|
| Fixed core, stabiliser 20 N (U, R, F) | 12 | **12** | 60/60 | 0.53 | 0.29 | 0.157 | 0 |
| **Free core, 20 N (U, R, F)** | 12 | **5** | **60/60** | 0.44 | 0.43 | 0.208 | 2.07 |
| Fixed core, 10 / 30 / 50 N (U) | 2 / 2 / 2 | 2 / 2 / **0** | 30/30 | 0.25 | **0.64** at 50 N | 0.157 | 0 |
| Free core, 10 / 30 / 50 N (U) | 2 / 2 / 2 | 0 / 0 / 0 | 29/30 (**one jam at 50 N**) | 0.45 | **0.94** at 50 N | **1.00** (jam) | **10.5** |

**Failed checks:**
- **Free core at 20 N:** every failure is G1's causality check (`ok_causal`) alone.
  - The checked layer is already turning, at more than 5°/s, about 80–120 ms before the turning pads' force reaches
    0.5 N.
  - This also holds with the layer speed measured relative to the core (`d16_ok_causal_rel_core`, a supplementary
    check).
  - The first move of some trials starts at t0 = 1.10 s, and the layer is flagged as moving at 1.10 s.
- **Higher squeeze:** penetration exceeds 0.5 mm at 50 N even with the fixed core, and at 30 N and above with the free
  core. The jammed free-core 50 N trial (`U_free_F50_s21001`, its fourth move) stalled at the 1 N·m torque limit with
  an 82° error.
- **Stabiliser contact:** the free core loses all contact on one stabiliser pad for up to 141 of about 1,200 10-ms
  samples. The fixed core loses it for at most 7.

## Interpretation (`INFERENCE` unless marked)
1. **Contact alone turns the correct layer with a free core.** At the P-97 default of 20 N, all 60 observed moves are
   the commanded ones: drift ≤ 0.44°, penetration ≤ 0.43 mm, turning torque ≤ 0.21 N·m (G1 max 0.19). That is the
   question D6 could not answer for a cube without a switch rule.
2. **The causality failures probably come from residual motion at move start, not a hidden actuator.**
   - The layer moves at the start of a move: the turning pads are still closing and have not yet loaded it.
   - The free cube in the compliant stand-in grip is probably still moving after the previous move or the setup.
   - G1's check assumes the cube is at rest when a move starts, which a fixed core guarantees.
   - Untested. Next test: wait until the cube is at rest before each move, or require it to be.
3. **The cube creeps downward in the stabiliser grip:** about 1–2 mm over 5 moves at 20 N, about 5 mm at 10 N, mostly
   along gravity (−z). Each rig-pad engagement seems to knock the free cube, and it slips while a stabiliser pad is
   briefly unloaded. G2 needs a creep limit (R2-10) and a gentler engagement (ramped closing, R2-08). The G1 rig closes
   in a step.
4. **More squeeze is not safer.** At 50 N, penetration exceeds G1's 0.5 mm even with the fixed core. With the free core
   it reaches 0.94 mm, and one turn jammed.
   - Part of the penetration figure may be pad-into-cubie rather than cubie-into-cubie: G1's metric takes the deepest
     of all contacts, pads included. Not separated yet.
   - This is the first real exercise of O-10 for M7, because G1's rig never squeezed above about 11.6 N.
   - It argues for a G2 grip band of about 10–30 N rather than 10–50 N (`PROPOSAL`, for the user).

## Limits
- Two to four seeds per configuration, 5-move sequences, one stabiliser placement per axis.
- The stabiliser is idealised: rigid pads on world-fixed slides, not an xArm7 with the G2 gripper.
- The turning side is the G1 rig: world-fixed and step-closing. It does not follow the cube when the cube slides.
- The core's mass and inertia are assumed.
- Nothing here is scored or pre-registered.
