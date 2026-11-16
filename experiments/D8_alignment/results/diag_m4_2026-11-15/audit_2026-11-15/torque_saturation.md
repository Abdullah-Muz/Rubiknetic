# Turner torque saturation: read-only analysis (2026-11-15)

Scripts: `scratchpad/t1_torque.py`, `scratchpad/t1b_torque.py` (outputs `t1_out.txt`, `t1b_out.txt`). Only stored JSON
was read; nothing was simulated. Field: `per_move[*].max_turner_torque_Nm`.

## 1. The saturating move (FACT, `rehearsal_gap0.05mm/E1-4/scr20inv_s8416.json`)
Move 22 of 40 (`per_move[21]`), **U2**, observed `U2`, `ok_oracle` True, `ok_all` True. Trial `pass` True,
`final_matches_oracle` True, `moves_completed_ok` 40.

| Quantity | Move 22 (U2) | Trial median (abs, 40 moves) | Trial max |
|---|---|---|---|
| `max_turner_torque_Nm` | **1.0** (stored exactly 1.0) | 0.232 | 1.0 |
| `turn_error_deg` | +0.084 | 0.079 | 0.261 |
| `turn_error_spread_deg` | 0.008 (lowest in trial) | 0.609 | 1.015 |
| `nontarget_drift_deg` | 0.053 (lowest in trial) | 0.358 | 0.670 |
| `penetration_mm` | 0.3004 (trial max; also run max over 1,088 moves) | 0.275 | 0.3004 |
| `layer_magnet_axis_torque_peak_Nm` | 0.072 | 0.074 | 0.082 |
| `misalignment.max_err_deg` after move | 0.479 | — | — |
| `t_layer_motion_s − t_pad_force_s` | 2 ms (causal) | — | — |
| Duration | `magnet_steps` 6434 (= every half turn in the trial); gap to next move's `t_pad_force_s` 3.215 s (other half turns 3.216–3.219 s) | | |

- FACT: per-move duration is **not an outcome**: `rig.py:TurnRig.rotate` runs a fixed number of steps
  (close 0.3 s, turn `turn_s_per_quarter`×quarters, hold, open, settle 0.3 s each). So a stall cannot show up as a
  longer move; it can only show up as turn error, oracle failure or penetration.
- FACT: the turn completed correctly (oracle, turn error 0.084°, all `ok_*` True). Penetration 0.3004 mm is the
  largest in the run so far but within `THRESHOLDS["penetration_mm"]` (move passed `ok_penetration`).
- FACT: next-highest value in the 0.05 mm run: `scr20inv_s8405` move 2 (D) 0.985 N·m (below the 0.99 cut).

## 2. Frequency table (FACT; ≥ 0.99 N·m = within 1 % of `turn_torque_limit` = 1.0)
| Run (stored params: gap, magnets, radial_preload) | Trials read | Moves | ≥ 0.99 | median | p95 | p99 | max |
|---|---|---|---|---|---|---|---|
| 0.05 mm rehearsal, 4×2 N35, preload 0 (in progress; E1-4 only) | 32 | 1,088 | **1** (0.09 %) | 0.196 | 0.474 | 0.549 | 1.000 |
| 0.1 mm rehearsal, 4×2 N35, preload 0 | 204 (86 with moves) | 1,376 | 0 | 0.104 | 0.533 | 0.652 | 0.876 |
| Gap study g0.05_4x2 | 21 (3 seq) | 120 | 0 | 0.123 | 0.475 | 0.634 | 0.694 |
| Gap study g0.05_none | 17 (3 seq) | 81 | **11** (13.6 %) | 0.411 | 1.000 | 1.000 | 1.000 |
| Gap study g0.1_4x2 | 11 (3 seq) | 120 | 0 | 0.098 | 0.575 | 0.681 | 0.701 |
| Size study 0.2 mm 4×2 N35 | 11 (3 seq) | 120 | 0 | 0.095 | 0.524 | 0.601 | 0.676 |
| Size study 0.2 mm 3×1.5 N35 | 11 (3 seq) | 120 | 2 (1.7 %) | 0.056 | 0.606 | 0.949 | 1.000 |
| Size study 0.2 mm, no magnets | 7 (3 seq) | 120 | **18** (15 %; 17 exactly 1.0) | 0.338 | 1.000 | 1.000 | 1.000 |
| M1 scored (`E1_scored/results/E1-2..E1-4`, gap 0.2 mm, preload 1 N) | 86 | 1,376 | 0 | 0.358 | 0.613 | 0.719 | 0.875 |

- (0.05 mm run counts at first read: 30 trials / 1,040 moves, also 1 saturation; p95 0.473, p99 0.546.)
- FACT: all runs above have stored `turn_torque_limit` 1.0, `turn_kp` 5.0, `turn_kv` 0.2 for move trials
  (the 2.0 entries are E1-6b opposed-torque trials, which store no per-move torque).
- FACT: saturations concentrate on the U face: g0.05_none 8 of 11 on U; 0.2 mm none 17 of 18 on U; 3×1.5 2 of 2 on U;
  the 0.05 mm rehearsal's one is U2. U-face median torque is the highest face median in every magnet-free or weak arm.
- FACT: in g0.05_none, 10 of the 11 saturating moves were oracle-correct; only `scr20inv_s9400` move 1 (U2) jammed
  (`turn_error_deg` 85.6, `penetration_mm` 0.758, `observed_valid` False). In 0.2 mm none, 18/18 saturating moves were
  oracle-correct. In M1-scored outside E1-2..4, the two 1.0 values are in the E1-7/E1-8 friction sweep
  (`cubie_friction=1.0…__6move.json` moves 4 and 5; move 5 failed the oracle).

## 3. What the stored value is (FACT from code)
- `rig.py:TurnRig._run` appends `d.actuator_force[self.act[face][2]]` every 0.5 ms step, where `act[face][2]` is the
  `turn_<face>` actuator of the **moving face** (`faces[0]`). Logging covers the whole move window (close, turn, hold,
  open, settle).
- `scored.py:run_sequence_trial` (used unchanged by `E4_scored_m4/run.py:run_trial`, line ~610) stores
  `max_turner_torque_Nm = max(|log.turner_torque|)`: the **peak absolute** actuator force over the window, not a mean.
- `m1_model.py:188`: `<position name="turn_f" … kp=5 kv=0.2 forcerange="-1 1">` with `<compiler autolimits="true">`.
  FACT (MuJoCo semantics): a specified `forcerange` with autolimits makes the actuator force-limited, and
  `actuator_force` is the clamped value. So **1.0 is a hard clip**, and an exact stored 1.0 means the position servo's
  demand `kp·(ctrl−q) − kv·q̇` exceeded 1 N·m for **at least one 0.5 ms step** in the window.
- Not stored: how long it was clipped, in which phase (turn vs hold vs settle), or the sign. A single-step transient
  and a sustained stall both store 1.0.
- INFERENCE: 1 N·m at kp = 5 N·m/rad corresponds to about 0.2 rad (11°) of servo error with zero velocity, or less
  when the −kv·q̇ term adds; so 1.0 means the turner lagged its ramp substantially at some instant, or was resisted.

## 4. Is it a sign of near-jamming at the tight gap? (INFERENCE)
- INFERENCE: **weak evidence only.** The one event (1/1,088 moves, 0.09 %; exact 95 % upper bound about 0.5 % by the
  Poisson approximation for 1 event) completed with normal turn error and the lowest drift and spread in the trial; its
  only abnormal value is penetration 0.300 mm, which is the run maximum but essentially at the run's p99 (≈0.29 mm).
- INFERENCE: saturation is **not specific to the tight gap**: it is frequent without magnets at 0.2 mm (15 %) and also
  occurs with the weaker 3×1.5 magnets at 0.2 mm (1.7 %), while 4×2 at 0.05 mm in the gap study had 0/120. Its strongest
  stored correlate is absence/weakness of magnets and the U face, not the gap.
- INFERENCE: saturation ≠ jam: 28 of 29 saturating moves across the magnet-free arms still completed oracle-correct; a
  jam is a saturation in which the layer then fails to complete (one case, g0.05_none s9400 move 1).
- Counter-indicator worth tracking (FACT): the 0.05 mm rehearsal's median turner torque (0.196) is about 1.9× the
  0.1 mm rehearsal (0.104) and 1.6× the gap-study g0.05_4x2 arm (0.123), while its p99 is lower (0.549 vs 0.652).
  INFERENCE: higher baseline torque at 0.05 mm suggests more friction, which narrows the margin to the 1 N·m clip; the
  rest of the run (E1-5 forgiveness, E1-6) will show whether saturations increase. Not established by current data.
- Untested: the stored data cannot say whether the clip occurred during the turn or in hold/settle; a time-resolved
  re-simulation of s8416 move 22 would decide it (not run here: workers busy, and out of scope).
