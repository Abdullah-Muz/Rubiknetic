# D18: two xArm7 + G2, facing each other, turning the free-core M7 cube (UNSCORED, 2026-11-26)

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
