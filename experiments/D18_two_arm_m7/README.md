# D18: two xArm7 + G2, facing each other, turning the free-core M7 cube (UNSCORED, 2026-11-26)

> **Magnet-free until P-131 (P-130, found 2026-11-27):** every D18 run recorded below, and the P-115 tuning, ran **without the M7
> L0 magnets** (`TwoArm.__init__` installed the magnet callback, then building arm B's IK model uninstalled it). Fixed
> in P-131; the magnets-on evidence is [`../E8_scored_g2/pilot4_magnets/`](../E8_scored_g2/pilot4_magnets/README.md).

**Why:** G2 pre-registration §7 P-2 (layout) and P-3 (arm B controller). The user chose ("proceed with the next part",
P-105):
- both arms on one table facing each other;
- cube axis horizontal;
- C1 turner (P-107);
- soft pads.

## Step 1: layout (`layout.py`, `results/layout_ik.json`)
**Frames:**
- Table top z = 0. Arm A's base is at the origin; arm B's (`B_`) is at (L, 0, 0), yawed 180°.
- Cube centre (L/2, 0, H). Cube +z (U) = world +x; the pad normal = world y.
- Grasp poses:
  - arm A's gripper axis is +x, with the D face at the stabiliser fingertip's proximal end;
  - arm B's is −x, with the fingertip's distal end 14 mm inside the U face.

**IK:**
- Damped least squares on the full gripper-base pose, with joint limits enforced.
- 6 seeds. The 180° roll about the gripper axis is accepted, since the fingers are symmetric.
- **Fix:** the first version's orientation error had a false zero at 180° (it reported 180° errors); it now uses the
  rotation-vector error.

**Results:**
- **All 20 layouts on the grid L 0.8–1.1 m × H 0.25–0.45 m are reachable by both arms,** with residuals < 0.001 mm and
  0.001°.
- Minimum joint-limit margin: 10–45°, larger with L.
- **Chosen: L = 1.0 m, H = 0.30 m.** Margins are A 28.9° and B 25.8°, without stretching the arms.

## Steps 2-3: two-arm scene and arm B controller (`two_arm.py`)
**Scene:**
- Both robots from P2's `build_model.py` (1305+, actuator gravity compensation).
- P-97 stabiliser fingertips on arm A; C1 turner fingertips on arm B.
- The free-core M7 cube (as G1: L0 magnets, R 2.5 mm, NoSlip 10, gap 0.05 mm), soft pads (0.01 s), μ 0.8.
- A table plane, with base-table contacts excluded.

**Controllers** (classical). They read only robot joint states, the kinematics derived from them, the targets and the
time, **never cube state**.
- **Arm A:** its joint position servos hold the IK pose. The gripper closes in the setup phase (gravity off, before
  t0, logged, as D17).
- **Arm B, joints 1–6:** torque control. A Cartesian impedance at the gripper base:
  - position: 2000 N/m, 60 N·s/m;
  - axis direction: 50 N·m/rad, 2 N·m·s/rad;
  - weak posture and joint damping;
  - an **integral term active only while the fingers are open** (approach, between moves), frozen while gripping;
  - clamped to the URDF peak efforts.
- **Arm B, J7:** the roll, using the model's own servo (kp 800, kv 80, ±30.6 N·m).
- **Per move:**
  1. Fixed 0.3 s settle. D16b's cube-state rest check is not allowed here.
  2. Ramp closed.
  3. Roll on a cosine ramp, 1 s per quarter turn.
  4. Open, roll back.
- **Approach:** from 40 mm outside, over 1 s.

**Two findings while building it (`FACT`, this model):**
1. **Joint friction:** the Menagerie xArm7 joints have 1 N·m friction (frictionloss). Under a pure impedance it left
   arm B 4.1 mm short and 1.9 mm off-axis at the grasp, statically, with no contacts. The integral term brings that to
   0.4–1.3 mm.
2. **J7 friction:** J7 has 1 N·m friction, 2 N·m·s/rad damping and 0.1 kg·m² armature. The 1 N·m roll limit carried
   over from the G1 rig and D17 cannot even overcome that: the first two-arm turn stalled at 1 N·m with the layer at
   0°.
   - J7's own servo turns it, using about 5.9 N·m, mostly the joint's own friction and damping.
   - **The torque the fingertips put on the layer is measured from the contacts:** 0.17–0.28 N·m.

## Results: U U′ U2 U′ U, two real arms (`results/two_arm_*`, `logs/`)
| Grip | Pass | Moves correct | Max turn err ° | Max drift ° | Max cubie pen. mm | Max pad pen. mm | Fingertip torque on layer N·m | J7 torque N·m | Grasp err mm | Core slip / rot per move | Non-pad cube, arm-arm, table contacts | Saturation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 N | **yes** | 5/5 | 0.58 | 0.22 | 0.11 | 0.71 | 0.21 | 5.9 | 1.15 | 0.11 mm / 0.43° | 0 / 0 / 0 | 0 |
| 20 N | **yes** | 5/5 | 0.53 | 0.24 | 0.15 | 1.01 | 0.28 | 5.9 | 1.26 | 0.06 mm / 0.46° | 0 / 0 / 0 | 0 |
| 30 N | **yes** | 5/5 | 0.57 | 0.22 | 0.18 | 1.04 | 0.17 | 6.0 | 1.31 | 0.09 mm / 0.45° | 0 / 0 / 0 | 0 |
| 50 N | **yes** | 5/5 | 0.50 | 0.19 | 0.18 | 1.11 | 0.18 | 6.0 | 1.28 | 0.14 mm / 0.49° | 0 / 0 / 0 | 0 |

- No audit violations or numerical failures.
- About 6 min wall time per run (4 in parallel, WSL).

**Conclusion (`INFERENCE`):** **two xArm7 arms with G2 grippers turn the free-core M7 cube's U layer by contact alone**,
with classical controllers that never read cube state:
- 20/20 moves correct on all G1-style checks;
- no collisions;
- no non-fingertip contact.

Compared with D17's compliant mount, the turn error is larger (0.5–0.6° vs ≤ 0.3°) but well inside 2°.

## Limits
- One layout, one approach, U-family moves only.
- One run per grip.
- Arm A's grasp happens in a gravity-off setup phase (R2-09, a gravity-on grasp from a support, is still open).
- The impedance gains are first choices, not tuned or identified.
- The joint friction, damping and armature are Menagerie's.
- Arm B's grasp error is 0.4–1.3 mm. The C1 tolerance is about ±2 mm (P-106).
- Not pre-registered.

## Drop-away stand (P-109 (1), R2-09) and visual stickers (UNSCORED)
### The stand
**Design:**
- An actuated stand under **D and E only**: world x from 2.5 mm inside the D face to 2.5 mm before the E/U boundary,
  40 mm wide, top 0.1 mm below the cube.
- A stiff vertical slide servo (20000 N/m, 300 N·s/m), gravity-compensated.

**Sequence (gravity on from the first step; no gravity-off setup):**
1. The cube settles 0.3 s.
2. Arm A ramps closed (2 s), then holds 0.3 s.
3. The stand lowers 30 mm (0.5 s).
4. Settle 0.5 s, then arm B approaches.

**Result** (`results/two_arm_F20_L1_H0.3_U_stand.json`, one U turn):

| Measure | Value |
|---|---|
| Stand load at rest | 0.884 N (= cube weight) |
| Stand load after the grasp | 1.298 N |
| Settle on stand | 0.19 mm, 0.11° |
| Shift during arm A's grasp | 0.51 mm, 0.09° |
| Shift as the stand drops | 0.11 mm, 0.03° |
| Stand contact after the drop | 0 N (clear) |
| Cube centre vs nominal at t0 | 0.59 mm |

The U turn passes every check: error −0.16°, drift 0.19°, fingertip torque 0.24 N·m.

### Visual stickers
- One 13 × 13 × 0.2 mm tile per outward cubie face, in the standard colour scheme.
- `contype = conaffinity = 0` and density 0, added in the G2 scene builder. The frozen G1 model is not changed.
- **Physics invariance (`FACT`):** the same U turn without and with stickers (gravity-off setup) gives **identical
  final `qpos` SHA-256** (`e83b4955…`) and identical per-move numbers (`results/*_nostk.json`, `results/*_stk.json`).

## J7 jam guard, first attempt (P-109 (2); UNSCORED; logs `logs/jam_guard.txt`, `jam_noguard.txt`, `guard_normal.txt`)
**Rule tested:** stop the roll and open if J7's lag (command − angle) exceeds 3° for 5 ms. **It does not work (`FACT`):**
1. **False trigger on a normal turn** (no obstacle): lag 3.16° at the first move, then stop.
   - J7 keeps the model's servo (kp 800, kv 80), whose velocity term makes it trail by about (kv/kp)·ω ≈ 0.1 s of
     motion: **up to about 14° at normal turning speed**.
   - A fixed lag threshold cannot separate a jam from normal motion.
2. **The obstacle test produced a push-through, not a stall.**
   - A world-fixed block above the top face beside the U layer, guard off: the U corner hit it and **pushed the whole
     cube about 2.2 mm (2.5°) in arm A's grip**.
   - The turn still mostly completed (error 3.07°, failing ≤ 2°), and the final state did not match the oracle.
   - Fingertip torque on the layer was 1.67 N·m, against ≤ 0.28 normally. The J7 motor torque was 6.86 N·m, against
     about 5.9 normally: the cube's share is hidden under J7's own friction and damping.

**PROPOSAL (for the user):** guard on the **estimated external torque at J7**: the motor torque minus J7's modelled
friction, damping and inertia (robot state only; a real xArm reports current-based joint torque). Normal ≤ 0.3 N·m;
push-through about 1.7 N·m; threshold [pilot], about 0.8–1 N·m. The lag guard is off by default (`--guard` enables it).

## Visual environment (user, 2026-11-26: the all-black room was "very depressing")
`add_environment` in `two_arm.py`, on by default (`--plain-env` turns it off):
- a light sky-gradient skybox;
- a wood-tone checker material on the table plane;
- a grey checker floor 0.75 m below the table (`contype = conaffinity = 0`);
- two directional lights and a brighter headlight.

**Visual only (`FACT`):** the same U turn gives the identical final `qpos` SHA-256 (`e83b4955…`) with and without the
environment, and the same hash as the sticker check.

## Option A: velocity feedforward + J7 torque budget (P-113; UNSCORED; `logs/ffb_rev1/`, `logs/ffb_rev2/`)
**The test matrix (both revisions):**
- normal U U′ U2 U′ U, and the jam block with one U;
- the simulator's J7 damping, friction and armature at **0 / +20 % / −20 %** relative to the controller's model.

**Revision 1:** feedforward from the commanded rate and acceleration, fixed budget 0.6 N·m.
- Normal, exact model: 5/5, lag 0.07° (was about 14°).
- Normal, ±20 %: **false stall stop** about 28° into the first turn.
- Jam, exact model: stopped at 59°, after pushing (1.49 N·m, 0.9 mm).
- Jam, +20 %: stopped at 26°.
- Jam, −20 %: **no stop**, push-through (1.7 N·m, 1.7 mm).

**Revision 2:** damping feedforward from the *measured* rate, friction along the commanded direction, no inertia
feedforward, budget B = 0.6 + 0.2·(|D·q̇| + F).
- Normal, exact model: 5/5.
- Normal, +20 %: **false stop** at 4° (static friction + inertia exceed ff + B).
- Normal, −20 %: 4th move **over-pushes** (error −7.9°, drift 1.27°, no stop).
- Jam, exact model and −20 %: **no stop**, push-through (1.71 N·m, cube 1.9 mm, 2.5°).

**Root cause (`INFERENCE`, a feasibility limit, not a tuning issue):**
- J7's modelled losses peak at about 6 N·m during a 1 s quarter turn; the cube needs about 0.3 N·m.
- Robustness to a fraction U of model error needs an allowance of about U × 6 N·m: about 1.2 N·m at U = 20 %.
- Arm A's 20 N grip resists only μ·F·a ≈ 0.9 N·m. So **no budget is both wide enough to avoid false stops and narrow
  enough to prevent push-through.**
- Feasibility requires B0 + U·L_peak < τ_grip(A) − τ_turn. That means a J7 model better than about 10 %, slower turns
  (L_peak falls with speed), or a stronger arm A grip, or a sensor that does not see J7's losses at all (a wrist F/T
  sensor, option C of the research note).

## Option C: wrist F/T sensor guard on arm B (P-114; UNSCORED; `logs/ft_*.txt`, `results/*_ft0.6*`)
**Sensor:**
- The official UFACTORY 6-axis F/T sensor for xArm, serial ≥ XI1305. `FACT` from listings: about 600 g, 400 N /
  20 N·m, 200 Hz.
- **Modelled by us:**
  - a welded 0.6 kg disc, 75 × 35 mm (`ASSUMPTION`, no official dimensions found), between link7 and the gripper;
  - the gripper moves out 35 mm;
  - MuJoCo force/torque sensors at the interface site;
  - sampled at 200 Hz with 0.01 N·m Gaussian noise (`ASSUMPTION`).
- Arm B's grasp IK is redone for the longer tool.
- The sensor's τ_z agrees with the torque computed from the contacts: 0.129 vs 0.136 N·m on the first U.

**Guard:**
- Stop (freeze the roll, open) when the measured torque about the tool axis exceeds **0.6 N·m on two consecutive
  samples (10 ms)**.
- J7 runs the revision-2 feedforward controller with a generous budget (2 N·m + 20 % of the losses), so it cannot
  stall falsely.

| Test | J7 plant error 0 | +20 % | −20 % |
|---|---|---|---|
| Normal U U′ U2 U′ U | **5/5 pass**, no stop, F/T max 0.26 N·m | **5/5**, no stop, max 0.24 | **5/5**, no stop, max 0.25 |
| Jam block (U) | **stopped by F/T** at 29.8°, τ_z 0.64, cube shift **0.09 mm** | **stopped** at 29.0°, 0.61, 0.09 mm | **stopped** at 29.9°, 0.65, 0.08 mm |

- All runs had cubie penetration ≤ 0.14 mm, no audit violations or numerical failures, and no collisions.
- Without a guard, the same obstacle shoved the cube about 2 mm (P-111).
- Normal turn error was ≤ 0.87° and drift ≤ 0.22°.

**Conclusion (`INFERENCE`):**
- The wrist F/T guard separates normal turning (≤ 0.26 N·m) from obstruction (stopped at about 0.6 N·m), with about
  2.3× margin.
- It is **insensitive to J7 model error,** because the sensor does not see J7's own losses.
- **Open:** the threshold's margin against real-cube torques (O-09, uncalibrated) and real sensor noise and offset
  drift. Set by a pilot and the real sensor's datasheet.

## Arm B gain tuning study (P-109 (3); UNSCORED; pilot seeds 29001–29002 only; `tune.sh`, `tune_analyze.py`, `results/tune/`)
**Design:**
- 11 configurations: K_P {1000, 2000, 4000} N/m × D_P {30, 60, 120} N·s/m at KI_P 8000, plus KI_P {4000, 16000} at
  (2000, 60).
- Each from 2 pilot seeds, which offset the cube start uniformly by ±1 mm per axis; arm targets stay nominal.
- Sequence U U′ U2 U′ U, F/T guard on, soft pads, 20 N.

**Selection rule** (in `tune_analyze.py`, written before the results):
1. Eligible = all moves of both seeds pass and no guard stop.
2. Rank by worst-case F/T torque, then core slip, then turn error.
3. Keep the nominal if it is within 10 % of the best.

`results/tune/summary.md`:
- **8/11 eligible.** All three K_P 1000 configurations fail one move each (seed 29002, first U, `ok_causal` only;
  turns accurate). `INFERENCE`: with the softer arm, the grasp lands less accurately and one turner pad touches the
  layer first.
- **Selected: K_P 4000, D_P 60, KI_P 8000.**
  - Worst F/T 0.154 N·m, against nominal 0.242 (−36 %).
  - Core slip 0.088 mm (0.121), grasp error 0.71 mm (1.29).
  - Turn error 0.87° (0.76), drift 0.17° (0.22).
- **Adopted as `K_P = 4000` in `two_arm.py`.** D_P, KI_P, K_R and D_R are unchanged.

**Limits:**
- K_P 4000 is the **edge of the grid**; the optimum may be stiffer.
- Two seeds per configuration; one sequence.

**Harness incident (`FACT`):** one run (`kp2000_dp30_ki8000_s29002`) crashed at start-up. M4's
`magnet_availability` refused, "no passing V3 record for 4x2 mm", although the record exists and every other run read
it.
- `INFERENCE`: a transient file-read failure on `/mnt/c` with 8 parallel processes.
- The log is kept as `logs/tune/..._CRASHED_startup.txt`. The configuration was rerun alone and passed.
- The G2 runner must treat this as a harness error (a failing record and a resume), never a silent pass.
