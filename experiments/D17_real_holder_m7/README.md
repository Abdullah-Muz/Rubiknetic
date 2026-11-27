# D17: the real G2 holder for the free-core M7 cube (UNSCORED, 2026-11-26)

**Why:** D16 showed the free-core result depends on the stand-in holding fixture (P-101). The user chose "Model the
real holder next".
- **Stage A:** the xArm7 + Gripper G2 model holds the cube.
- **Stage B (next):** add a turning side that follows the cube.

**Model (`hold.py`):**
- **Robot:** `experiments/P2_robot_model/build_model.py`: revision 1305+, gravity compensation, G2 four-bar and tendon
  drive, force limit calibrated at 57 mm. The arm is at P2's `HOME_ARM`, gripper pointing down.
- **Cube:** M7 as scored in G1 (B1, gap 0.05 mm, rounded R 2.5 mm, NoSlip 10, dt 0.5 ms), with L0 magnets through the
  unchanged `MagnetSystem`, `rig=False`, and a free core (1.7 g, as D6/D16).
- **Fingertip, P-97 stabiliser:** **one box per finger**, 30 wide × 30 deep × 4 mm. It replaces the stock G2 pads,
  which stay as visuals only.
  - Contact: μ 0.8, condim 4, rig-pad solimp.
  - `--tip-solref` sets the contact time constant: 0.001 s = rig pads, "rigid"; 0.01 s = "soft".
- **Setup (before t0, logged, as P2):** gravity off while the gripper ramps closed at 0.5 rad/s, then gravity on and
  a 5 s hold.

## Findings (`FACT` unless marked)
1. **The stock G2 pads are two boxes per finger, and only one touches** (`FACT`, this model).
   - Their faces differ by about 0.06 mm.
   - In P2's placement only `finger_pad_1` touched, and only the middle layer: in effect a one-layer grip.
   - The P-97 fingertip is a single flat pad, so it is modelled as one box (`robot_spec`).
2. **P2's cube placement is not the P-04 grasp.**
   - P2 (`integration_hold_m2.py`) passes the fingers alongside the U layer and holds D+E from the U end. The G2
     inner knuckles then pressed on the U layer at about 16 N per side.
   - Under P-04, arm A grips from the **D end**: the D face at the fingertip's proximal end, and the U layer projecting
     27 mm past the fingertips for arm B (`--orient p04`, the default). No knuckle contact arises there.
3. **The fingertips splay 0.25–0.9° under 10–50 N.**
   - Stiffening the four-bar equality constraints did not remove it: 0.005 / 0.002 / 0.001 s gave 0.45 / 0.88 / 0.13°.
     It is not simply constraint compliance; the cause is not identified.
4. **The two held layers do not share the load equally, and pad compliance decides the split.**
   - In B1, the D-layer side cubies sit on ball joints and roll about 0.04 mm under a side squeeze. The middle layer's
     centre is radially rigid.
   - Combined with the splay, one layer carries most of the load unless the pad is compliant.
   - A real 4 mm compliant pad would spread the load (`INFERENCE`).

### Stage A results, P-04 orientation (5 s hold; `results/hold_p04_*`)
| Fingertip contact | Grip | Core slip mm | Core rot ° | Jitter (median max-cubie \|ω\|) °/s | Load D / E (N) | Pad pen. mm | Cubie pen. mm | Non-pad contacts |
|---|---|---|---|---|---|---|---|---|
| rigid (0.001 s) | 10 N | 0.021 | 0.008 | 0.00 | 10.1 / 10.8 | 0.015 | 0.016 | 0 |
| rigid | 20 N | 0.054 | 0.010 | 0.01 | 33.2 / 7.7 | 0.039 | 0.063 | 0 |
| rigid | 30 N | 0.050 | 0.020 | 0.02 | 56.8 / 3.9 | 0.056 | 0.083 | 0 |
| rigid | 50 N | 0.020 | 0.050 | 0.03 | 99.0 / 1.8 | 0.085 | 0.137 | 0 |
| soft (0.01 s) | 10 N | 0.103 | 0.016 | 0.01 | 7.6 / 13.4 | 0.309 | 0.012 | 0 |
| soft | 20 N | 0.182 | 0.038 | 0.01 | 19.0 / 21.9 | 0.372 | 0.018 | 0 |
| soft | 30 N | 0.076 | 0.030 | 0.01 | 33.1 / 27.8 | 0.433 | 0.032 | 0 |
| soft | 50 N | 0.020 | 0.097 | 0.05 | 60.0 / 40.8 | 0.576 | 0.045 | 0 |

No audit violations or numerical failures. The P2-placement runs (`results/hold_p2_*`, rigid) put all the load on the
middle layer (E).

**Stage A conclusion (`INFERENCE`):**
- **The real-gripper model holds the free-core M7 cube** with the P-97 fingertip in the P-04 orientation at 10–50 N:
  - slip ≤ 0.18 mm over 5 s;
  - no jitter, unlike D16's stand-in (45°/s);
  - no non-pad contact.
- **The D16 problems were properties of the stand-in fixture,** not of the free cube.
- **Open:**
  - the load split depends on the pad's compliance, which is unmeasured (`ASSUMPTION`);
  - the fingertip splay is unexplained;
  - pad penetration in the "soft" model is 0.3–0.6 mm. That is pad deformation, not a cube overlap.

## Limits
- One arm pose with the gripper pointing down.
- No turning yet (Stage B).
- One run per setting.
- Pad compliance is represented by contact softness, not a deformable pad.
- The G2 model's inertials and linkage constraints come from P2 (not identified).

## Stage B: turning the U layer with a second G2 (`turn.py`; UNSCORED)
**Setup:**
- **Arm A** as in stage A: P-04 orientation, P-97 stabiliser fingertips on D+E.
- **Turner:** a **second G2 gripper model** (`B_`, attached with its four-bar, tendon and drive) on a **compliant
  mount**, a `PROPOSAL` stand-in for arm B:
  - x/y/z slides with springs of 2000 N/m and dampers of 60 N·s/m, gravity-compensated;
  - a roll hinge on the cube axis with a position servo, as the G1 turner: kp 5, kv 0.2, ±1 N·m.
- **Turner fingertips (C1):** one box per finger, 25 wide × 14 deep × 4 mm, inserted 14 mm into the U layer.
- **Per move:**
  1. Wait for rest.
  2. Ramp the turner closed.
  3. Roll on a cosine ramp, 1 s per quarter turn.
  4. Open, roll back.
- **Checks:** as G1's, in the core frame: observed move against the logical oracle, turn error ≤ 2°, drift ≤ 1°,
  cubie-cubie penetration ≤ 0.5 mm, causality with the layer speed relative to the core. Plus edit audit and numerical
  failures.

**Results:** sequence U U′ U2 U′ U, the same grip on both grippers (`results/turn_*`):

| Grip | Pad contact | Pass | Moves correct | Max turn err ° | Max drift ° | Max cubie pen. mm | Max pad pen. mm | Max roll torque N·m | Mount excursion mm | Core slip / rot per move |
|---|---|---|---|---|---|---|---|---|---|---|
| 10 N | rigid | **yes** | 5/5 | 0.18 | 0.20 | 0.08 | 0.08 | 0.113 | 1.7 | 0.03 mm / 0.21° |
| 10 N | soft | **yes** | 5/5 | 0.08 | 0.17 | 0.07 | 0.69 | 0.099 | 1.3 | 0.06 mm / 0.39° |
| 20 N | rigid | **yes** | 5/5 | 0.21 | 0.19 | 0.12 | 0.12 | 0.117 | 2.8 | 0.02 mm / 0.17° |
| 20 N | soft | **yes** | 5/5 | 0.11 | 0.13 | 0.10 | 1.00 | 0.092 | 2.7 | 0.08 mm / 0.26° |
| 30 N | rigid | **yes** | 5/5 | 0.28 | 0.23 | 0.13 | 0.11 | 0.162 | 2.8 | 0.03 mm / 0.13° |
| 30 N | soft | **yes** | 5/5 | 0.10 | 0.14 | 0.12 | 1.03 | 0.091 | 2.8 | 0.06 mm / 0.27° |
| 50 N | rigid | **yes** | 5/5 | 0.12 | 0.33 | 0.14 | 0.13 | 0.254 | 2.9 | 0.02 mm / 0.28° |
| 50 N | soft | **yes** | 5/5 | 0.05 | 0.12 | 0.14 | 1.21 | 0.088 | 2.9 | 0.14 mm / 0.36° |

- **40/40 moves are correct on every check, causality included.**
- No rest wait was needed: the cube was always at rest.
- No audit violations or numerical failures.
- About 400–500 s wall time per run (WSL, 8 runs in parallel).

**Stage B conclusion (`INFERENCE`):**
- **Contact-driven turns of the free-core M7 cube work with real G2 grippers on both sides.** This holds for both pad
  models across 10–50 N, at the P-97 fingertip sizes, in the P-04 orientation.
- **The D16 causality failures, creep and ejection came from the stand-in fixture,** not the cube.
- **Turning torque ≤ 0.25 N·m,** close to G1's 0.19 N·m maximum. Rigid pads at 50 N need the most.

**Limits (stage B):**
- U-face moves only: one stabiliser grasp, no regrasp.
- One sequence and one run per setting.
- Arm B is a compliant mount with assumed stiffness, damping and roll gains, not an xArm7 with its controller.
- Arm A is fixed at one pose.
- Pad compliance is contact softness: soft-pad "penetration" up to 1.2 mm is pad deformation.
- The causality check uses the instantaneous speed relative to the core.
- Not pre-registered; no criterion is claimed.

## P-1 pilot: C1 vs C2 turner fingertip (G2 pre-registration §7, P-105; UNSCORED)
`pilot_c1c2.sh`, `results/pilot_*`.

**Setup:**
- Sequence U U′ U2 U′ U, grip 20 N, soft pads (0.01 s), μ 0.8.
- The turner mount is now **actuated**: position actuators kp 2000 N/m, kv 60 N·s/m, the same dynamics as stage B's
  springs. So the controller can command grasp offsets.
- Deliberate grasp errors: **axial −2 / 0 / +2 mm** × **lateral 0 / 1 mm**.

**Procedures:**
- **C1:** insertion set by command (nominal 14 mm).
- **C2:**
  1. Pre-close to a 58 mm gap.
  2. Push axially (command +2 mm deeper than nominal) so the shoulder seats on the U face.
  3. Close.

  Closing first fails: the 20 N grip's pad friction (about 32 N) blocks the 6 N axial push, so the shoulder never
  seated (smoke test, `FACT`).
- **Causality:** the tool contact counted is pads plus shoulder. The pads-only result is reported too.

| Turner | Runs pass | Moves correct | Insertion (all offsets) mm | Shoulder force N | Max roll torque N·m | Max drift ° | Max core slip mm | Pads-only causal |
|---|---|---|---|---|---|---|---|---|
| **C1** | 6/6 | 30/30 | 12.2–16.4 (follows the error) | – | **0.094** | 0.27 | 0.09 | 30/30 |
| **C2, 3 mm shoulder** | 6/6 | 30/30 | **13.7–14.2** | 1.5–17.3 | 0.274 | 0.42 | 0.28 | 17/30 |
| **C2, 5 mm shoulder** | 6/6 | 30/30 | **13.9–14.2** | 2.7–18.7 | 0.266 | 0.21 | 0.22 | 18/30 |

**Findings (`FACT` for these runs; interpretation `INFERENCE`):**
1. **Both candidates pass everything** at ±2 mm axial and 1 mm lateral error.
2. **C2's shoulder does its job:** insertion stays at 14 ± 0.3 mm whatever the axial error.
   - **The cost is an axial load on the U layer** (up to about 19 N with the +2 mm error). It roughly **triples the
     turning torque**, 0.09 → 0.27 N·m, presumably by pressing U against E.
   - **Seating nudges the U layer before the side pads grip** (pads-only causality 17–18/30). This is tool contact,
     but it is an extra disturbance.
3. **C1's insertion follows the arm's axial error.** At +2 mm it reaches 16.35 mm, 0.15 mm short of the end of the
   flat band (16.5 mm) and 2.7 mm short of the U/E boundary.
   - A larger error would put the pad on the rounded edge, then across the boundary. That is negative test G2-7a's
     territory.
4. **A 5 mm shoulder sits more precisely than 3 mm** (13.9–14.2 vs 13.7–14.2): 3 mm barely clears the 2.5 mm edge
   rounding. Otherwise they are similar.

**Recommendation (`PROPOSAL`, for the user's choice):**
- **C1 as the G2 turner fingertip:** simplest, lowest torque, no seating disturbance.
- **Condition:** arm B's axial grasp error stays within about ±2 mm. G2-6 and G2-7a must test it.
- **Contingency:** C2 with a 5 mm shoulder, if the real arm B's axial error proves larger.
