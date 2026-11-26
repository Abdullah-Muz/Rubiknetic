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
