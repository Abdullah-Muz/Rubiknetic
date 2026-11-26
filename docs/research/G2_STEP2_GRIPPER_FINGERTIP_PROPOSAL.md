# G2 step 2: gripper and fingertip choice for the M7 cube (PROPOSAL, 2026-11-26)

**Status.** `PROPOSAL` for the user's approval (P-95: "G2, starting with design"). Nothing here is decided. It
re-derives the Phase 0 gripper recommendation ([`GRIPPER_DESIGN_TRADEOFFS.md`](GRIPPER_DESIGN_TRADEOFFS.md);
approved as a pilot set in P-03 and P-04) for **M7**, the cube that passed G1. The Phase-1-derived requirements
([`PHASE_2_REQUIREMENTS_FROM_PHASE_1.md`](PHASE_2_REQUIREMENTS_FROM_PHASE_1.md), 2026-11-13) were written for
**M2**, the switched-weld cube; §4 says which still apply.

The work is simulation only. Fingertips are MuJoCo primitives, with **no CAD** (P-03).

**Labels:** `FACT`, `INFERENCE`, `ASSUMPTION`, `PROPOSAL`.

## 1. Already decided (`FACT`, DECISION_LOG)
- **Arms:** two xArm7, revision 1305+ (P-96).
- **Gripper:** UFACTORY Gripper G2: 10–50 N, 84 mm stroke, position feedback only (P-17). The model is built and
  smoke-tested in `experiments/P2_robot_model/`.
- **Grasp strategy:** **coaxial opposed** (P-04).
  - Arm A (stabiliser) grips two layers.
  - Arm B (turner) grips the target layer's two opposite side faces and turns it with wrist roll J7. J7's ±360°
    allows 180° in one grasp.
- **Fingertip pilot set** (P-03):
  - **C1:** identical flat compliant pads, insertion depth set by control;
  - **C2:** asymmetric: the turner has a depth shoulder that abuts the cube end face; the stabiliser has C1's long
    pads;
  - **C6:** a contingency (adaptive gripper; would change the gripper decision);
  - **C4:** third option (grooved jaws), only if C1/C2 fail lateral centring.

## 2. What M7 and G1 add (`FACT` unless labelled)
1. **G1's rig already used a C1-like coaxial layer grasp.**
   - Two pads 45 mm wide, 10 mm high and 5 mm thick, friction 0.8, condim 4, clamp the target layer's opposite side
     faces at a randomised grip (e.g. 14.0 N in `D15 r2 R25/L0/E1-3/U2_s16200`).
   - A torque-limited actuator then rotates the pads.
   - **E1-7 passed at grip 10, 30 and 50 N.** The cube stays legal and non-jamming under these squeezes with rig pads.
     This is partial evidence for **O-10**: the G2 gripper's real fingers still have to be checked.
2. **Turning torque needed (M7):** median 0.103 N·m, max 0.191 N·m over 1,376 scored moves. In E1-7, cubie friction
   μ 0.5 gave up to 0.37 N·m.
3. **Torque capacity of a coaxial friction grasp:** τ ≈ μ·F·a with a = 57 mm (`INFERENCE`, as in the feasibility
   study).

   | Grip F | μ 0.3 | μ 0.5 | μ 0.8 |
   |---|---|---|---|
   | 10 N | 0.17 | **0.29** | 0.46 |
   | 20 N | 0.34 | **0.57** | 0.91 |
   | 30 N | 0.51 | 0.86 | 1.37 |

   - At 10 N the margin over the 0.19 N·m maximum is thin (1.5× at μ 0.5).
   - At 20 N it is about 3×.
   - **Pad friction on ABS is unmeasured.** No measured silicone or rubber value was found (CONTACT_AND_RL_FINDINGS).
     It is an `ASSUMPTION`, to be swept.
4. **Geometry.**
   - Pitch and layer height h = 19 mm (cube 57 mm); piece gap 0.05 mm.
   - **Edges rounded at R 2.5 mm**, so each cubie side face is flat over about 19 − 2 × 2.5 = **14 mm** of the layer
     height (`INFERENCE`). A pad contacts flat face only within that band.
   - **Turner insertion depth** (along the turning axis, from the end face) must stay inside the target layer:
     ≤ about 16.5 mm before reaching the rounded boundary. About 14 mm is the full flat band.
   - **Stabiliser** must cover both remaining layers: insertion about 22–35 mm.
5. **The cube's core was fixed to the world in G1** (rig v0, P-09). P-09 approved "a free-core contact-held variant
   before Phase 2". **In G2 the cube is free and held only by arm A**, which G1 did not test.
   - `INFERENCE`: this is the largest physics risk G2 inherits.
   - It needs its own check: an unscored free-core M7 rehearsal, then scored inside G2.

## 3. Proposal
**P1. Keep the P-03 pilot set: C1 and C2**, compared under matched poses, grip, friction and solver settings. They
share the stabiliser finger, so the only extra artefact is C2's turner tip. C6 and C4 stay contingencies.

**P2. Starting primitive dimensions** (MuJoCo boxes, simulation only; to be swept, not fixed):

| Part | C1 | C2 |
|---|---|---|
| Turner pad (per finger) | flat, 25 mm wide × 14 mm deep (insertion by control, target 12–14 mm) × 4 mm compliant layer | flat, 25 mm wide × 14 mm deep, ending at a **shoulder** 3 mm tall that abuts the end face (sets 14 mm insertion mechanically) |
| Stabiliser pad (shared) | flat, 30 mm wide × 30 mm deep (covers both non-target layers; insertion 24–30 mm, leaving ≥ 8 mm to the target-layer boundary at 38 mm) × 4 mm compliant layer | same |
| Pad contact | condim 4 (sliding + torsional friction, R2-14; the G1 rig pads also use condim 4); μ swept 0.5 / 0.8 / 1.0 (rig: 0.8); soft contact tuned like the rig pads | same |

- Mount: the G2 fingertip interface, provisional 2 × M3 at 12 mm (R2-13). G2's own pad span is 40 mm (P2 prototype),
  so these pads replace it.
- `INFERENCE`: 14 mm keeps the turner within the flat band with about 2.5 mm to spare before the rounded boundary.

**P3. Default grip force 20 N** for both arms, swept 10 / 20 / 30 / 50 N. That is about 3× torque margin at μ 0.5
(§2.3). 50 N is the upper O-10 check.

**P4. G2 adds a free-core requirement (new).**
- Before any arm work, an unscored rehearsal of **free-core M7**: the core as a free body, cubies on their ball joints
  to it, everything else as M7.
- Held by fixed stand-in pads in place of arm A, with the G1 rig turning a layer.
- It shows whether G1's behaviour survives without the fixed core. If it does not, the result goes to the user before
  anything else in G2.

**P5. Re-derive the requirements list for M7** (§4), to be fixed in the G2 pre-registration (step 3).

## 4. The Phase-1 requirements (R2-01…R2-23), re-read for M7 (`INFERENCE`)
| Keep (adapted) | Drop (M2-specific) | Add |
|---|---|---|
| R2-01 two-layer stabiliser grasp · R2-02 clearance to the target boundary (now with the 2.5 mm rounding) · R2-03 shear-dominance margin · R2-05 turn completion within 0.5° · R2-07 declared layer-angle feedback source · R2-08 ramped closing · R2-09 gravity-on grasp from a support · R2-10 contact creep bounded · R2-11 gripper calibration regression · R2-12 tool frame from the four-bar pose · R2-13 mount interface · R2-14 torsional friction · R2-15 joint envelope (now 1305+) · R2-16 URDF peak torques as saturation (O-13 closed) · R2-17 speed limits · R2-18 gravity compensation · R2-19 throughput for two arms + M7 · R2-23 asset provenance | R2-04 switch manager and face-grip rule · R2-06 end-of-turn unloading for relock · R2-20 D5 as forgiveness reference · R2-21 initial alignment within the M2 envelope (replaced by M7's E1-5 forgiveness behaviour) · R2-22 no reading of M2 lock state | **Free-core M7 (P4)** · **M7 numerical bounds carried from G1: timestep ≤ 0.5 ms, NoSlip 10, piece gap ≤ 0.05 mm** · **magnet-model validity reported** (G1's rule-3 labels) · **no wrong-layer drag**: non-target layers ≤ 1° (G1's drift criterion) |

## 5. Decisions for the user
1. Keep C1 + C2 as the pilot pair (P1)?
2. Accept the starting primitive dimensions and the friction sweep (P2)?
3. Default grip 20 N, swept 10 / 20 / 30 / 50 N (P3)?
4. Add the free-core M7 rehearsal as G2's first experiment (P4)?
5. Accept the requirement re-derivation (§4) as the basis of the G2 pre-registration (step 3)?
