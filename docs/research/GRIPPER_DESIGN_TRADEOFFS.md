# Gripper and Fingertip Design Tradeoffs — Comparative Engineering Analysis

**Date:** 2026-11-12 · **Phase:** 0 · **Gate:** G0 · **Status:** `CONDITIONAL` recommendation; **no geometry is selected** until you approve it (D-04 / O-02).
**Inputs:** [`GRIPPER_LITERATURE_REVIEW.md`](GRIPPER_LITERATURE_REVIEW.md), [`MECHANICAL_FEASIBILITY_ASSESSMENT.md`](MECHANICAL_FEASIBILITY_ASSESSMENT.md), sources in [`PHASE_0_SOURCE_REGISTER.md`](PHASE_0_SOURCE_REGISTER.md).
**Important:** the scores below are **engineering judgments** informed by the cited facts and the closed-form estimates. They are not measurements. Sensitivity results show which conclusions survive reasonable disagreement about weights.

---

## 1. Design drivers (from evidence)

| Driver | Value / fact | Source / tag |
|---|---|---|
| Layer height | h = a/3 ≈ 19.0 mm for a = 57 mm | `ASSUMPTION` (cube-specific; parametric) |
| Stock pad span | ≈37 mm (2 × 19 mm pads, 18 mm apart): **fails** single-layer selectivity | `FACT` S19 |
| Grip force | G2: 10–50 N programmable; original gripper: ≤30 N; position feedback only | `FACT` S21, S22 |
| Stroke vs cube | 84 mm stroke vs 57 mm face and 80.6 mm diagonal | `FACT` S22; arithmetic |
| G2 axial tip shift | ≈2.2 mm between 67 mm and 57 mm aperture | `INFERENCE` from S22 formula |
| Torque capacity, coaxial layer grasp | 0.17–4.4 N·m over the 10–50 N, μ = 0.3–1.0 range | `INFERENCE` (feasibility §3) |
| Required turning torque | **unknown**; working bracket 0.03–0.6 N·m | `ASSUMPTION` |
| Wrist roll | J7 ±360° allows a coaxial 180° turn in one grasp | `FACT` S21 |
| Two-finger grasp-axis torque is hard; compliant silicone pads help | 28.7 % → 93.7 % grasp success | `FACT` S32 |
| Dual-arm regrasp needs clearance | "When the grasps overlap, dual-arm regrasp is bad" | `FACT` S37 |

## 2. Two grasp geometries underlie all concepts

```
 COAXIAL (turning axis = wrist roll axis)          PERPENDICULAR / SIDE (turning axis ⟂ approach)

        Arm B (turner) approach  ↓                       Arm B approach →
          ┌──┐          ┌──┐                                 ┌──────── finger (pad height ≤ h-2c-2e)
          │  │ finger   │  │                         ┌───────┼─┐
       ┌──┼──┼──────────┼──┼──┐  U layer  (h=19)    │ U     ═ │  ← pad must stay inside one layer,
       │  └──┘ insertion└──┘  │  ← tip depth ≤ h-c-e│ E       │     relief above/below
       ├──────────────────────┤                     │ D       │
       │      E layer         │  Arm A (stabilizer)  └─────────┘
       │      D layer         │  grips E+D from the  turn = arc motion of whole hand about
       └──┬──┬──────────┬──┬──┘  opposite end        the cube axis (multi-joint), not J7 roll
          │  │          │  │  ↑ Arm A approach
```

`INFERENCE`: in the coaxial geometry the turn is a single-joint (J7) rotation and the fingertip needs only a **depth limit**. In the side geometry the hand must follow an arc about an axis it does not own, and the pad *height* must fit inside the layer. The coaxial geometry is mechanically simpler. Its costs are that both cube end faces are occluded and that changing turning axis requires a regrasp.

## 3. Candidate concepts (seven compared, one excluded)

Each concept is a *complete configuration*: geometry, approach, and arm roles.

### C1 — Coaxial, identical flat compliant pads, depth set by control

- **Geometry:** both arms carry the same fingers. Each has a flat pad roughly 20–30 mm wide and ~33 mm long (usable), faced with a compliant high-friction layer (silicone class per S32; properties to be swept in sim).
- **Turner** inserts ≤ (h − c − e) ≈ 14–16 mm. **Stabilizer** inserts ≥ h + c + e and ≤ 2h − c − e, i.e. ≈ 22–35 mm, so it covers *both* remaining layers. Gripping only the far layer would let the middle layer be dragged.
- **Strengths:** role-symmetric (handoffs and role swaps with no tool change); simplest geometry; trivial MuJoCo primitives.
- **Failure modes:** an axial depth error makes the turner touch the middle layer (wrong-layer drag). Insertion depth depends on cube-pose estimate plus G2 axial shift (~2.2 mm). Pad compliance reduces the normal-force couple, so torque relies more on friction.

### C2 — Coaxial, asymmetric datum tooling (turner with a depth shoulder; long-pad stabilizer)

- **Geometry:** turner fingers have a pad of length ≈ h − c (e.g. 15–16 mm) ending at a **shoulder** that abuts the cube's end face. The cube itself then sets the insertion depth mechanically, which removes axial pose error from the selectivity budget. Stabilizer fingers are C1's long pads.
- **Strengths:** layer selectivity is guaranteed by geometry; robust to depth estimation error; the shoulder also gives a contact cue for "seated" detection.
- **Failure modes:** roles are fixed, so swaps need a handoff that also swaps *which arm turns*, or a tool change (excluded by design simplicity). The shoulder covers part of the end face, worsening camera occlusion. A misaligned approach can wedge the shoulder on a cube edge.
- **Note:** C1 and C2 share the stabilizer finger, so both can be piloted at the cost of one extra turner-tip variant.

### C3 — Side approach with stepped/offset jaws

- **Geometry:** the pad confined to one layer has height ≤ h − 2c − 2e ≈ 11–16 mm, with relief (recess) above and below so the finger body clears the adjacent layers. The stabilizer variant has a two-layer pad.
- **Strengths:** lets either arm turn any face pair reachable from the side without coaxial alignment; leaves both end faces visible.
- **Failure modes:** the turn is an arc that needs coordinated multi-joint motion about an external axis (larger tracking error and internal forces). Pad height errors act on both sides of the band. More finger volume near the cube makes handoffs harder (S37 clearance).

### C4 — Grooved / edge-conforming coaxial jaws

- **Geometry:** shallow V-grooves or edge-conforming profiles that center on the layer's vertical edges (or on two opposite corners of the layer).
- **Strengths:** lateral self-centering; strong form-closure torque.
- **Failure modes:** cube edges are rounded and bevelled (S01 bevel; real cubes have rounded corners), so grooves may seat poorly or **wedge**. Non-convex profiles need convex decomposition in MuJoCo (S11, S43), which costs CPU and contact-stability tuning. Jamming during release.

### C5 — Diagonal corner-cradle jaws

- **Geometry:** L-shaped jaws gripping the layer across its diagonal (corner to corner).
- **Strengths:** pure form closure about the turn axis.
- **Failure modes:** the 80.6 mm diagonal leaves only ~3.4 mm of the 84 mm stroke for approach clearance (`FACT` arithmetic + S22). Corner pieces are the most rounded. Large finger volume blocks handoffs. **Negative finding: not recommended.**

### C6 — Adaptive gripper (Robotiq 2F-85) with custom pads

- **Strengths:** 20–235 N force range (S23, to re-verify); well-modeled in Menagerie (S20, BSD-2); parallel-pinch mode behaves like C1/C2.
- **Failure modes:** changes the D-04 *gripper variant*, and xArm mounting/control is unverified. The fingertip selectivity problem is unchanged. More complex linkage model (CPU). **A contingency, not a lead.**

### C7 — Single arm plus environmental constraint (table)

- Inspired by S31 (environmental constraints) and S41/S42 (extrinsic dexterity, controlled slip). The cube rests on the table and one gripper turns the top layer while table friction stabilizes the rest.
- **Strengths:** frees the second arm; compact; good for recovery fallback.
- **Failure modes:** table friction (μN_gravity ≈ 0.5 × 0.09 kg × 9.81 ≈ 0.44 N) yields only ~0.01–0.02 N·m of counter-torque at cube-scale levers (`INFERENCE`), which is far below the resistance bracket. It would need pressing down or a fixture. It also departs from the bimanual objective. **Recovery fallback only.**

### C8 — Dexterous multi-finger hand — excluded

- Explicit non-goal (master spec §3). S01 shows feasibility only at extreme compute. Listed for completeness and not scored.

## 4. Weighted decision matrix

**Weights (sum 100) and rationale:**

| Criterion | Weight | Why this weight |
|---|---|---|
| Layer selectivity | 20 | The binding constraint (§1). A wrong-layer turn invalidates the core claim |
| Robustness to pose/axis error | 15 | Bimanual coaxial alignment and perception error are the dominant real uncertainties |
| Turning torque transmission | 10 | Required, but every coaxial concept shows large margins |
| Stabilization counter-torque | 10 | Required for Arm A's role in Phase 2 |
| Role swap / handoff compatibility | 10 | Needed by Phase 4 (D-09 "eventual role swapping") |
| Reach and inter-gripper clearance | 10 | Two grippers on a 57 mm cube; S37 clearance finding |
| Simulation complexity / CPU | 10 | D-11 CPU-only constraint |
| Camera visibility | 5 | A Phase 5 concern; mitigable by regrasping |
| Integration (mount, D-04, license) | 5 | Hardware assumption consistency |
| Evidence base | 5 | How directly the literature supports the concept |

**Scores (1 = poor … 5 = strong; judgment):**

| Concept | Sel. | Robust | Torque | Stab. | Swap | Reach | Sim | Cam | Integ. | Evid. | **Total /100** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **C2** asymmetric datum tooling | 5 | 4 | 5 | 5 | 2 | 4 | 5 | 3 | 5 | 3 | **85.0** |
| **C1** identical flat pads, depth by control | 3 | 3 | 5 | 4 | 5 | 4 | 5 | 3 | 5 | 3 | **78.0** |
| C6 adaptive gripper + custom pads | 3 | 3 | 5 | 5 | 5 | 3 | 3 | 3 | 2 | 3 | 71.0 |
| C4 grooved / edge-conforming | 3 | 3 | 5 | 4 | 4 | 4 | 3 | 3 | 3 | 2 | 69.0 |
| C3 side-approach stepped jaws | 4 | 2 | 4 | 3 | 4 | 2 | 4 | 3 | 4 | 2 | 65.0 |
| C7 single arm + table | 3 | 2 | 3 | 2 | 3 | 4 | 4 | 4 | 4 | 3 | 61.0 |
| C5 diagonal corner cradle | 3 | 2 | 5 | 4 | 3 | 2 | 3 | 2 | 2 | 1 | 57.0 |

**Sensitivity (computed):**

- One-at-a-time weight changes (×0, ×0.5, ×2 on every criterion): C2 stays first in every case except *Layer selectivity ×0*, where C1 leads. The top three stay C2/C1 with C6 or C4.
- Monte Carlo (every weight independently ×U[0.5, 1.5], 20,000 draws): **C2 first in 99.5 %**, C1 first in 0.5 %. C1 and C2 are in the top three in 100 %, C6 in 96.8 %, C4 in 2.9 %.
- Role-swap emphasis (weight 25 instead of 10): **C1 (80.9) overtakes C2 (79.1)**. The C1-vs-C2 choice is therefore really a decision about **how much you value tool symmetry versus a mechanical selectivity guarantee**.

## 5. Recommendation — `CONDITIONAL`

**Pilot set for Phase 2 (after G1):** C2 and C1 together. They share the stabilizer finger, so the only extra artifact is the turner tip variant. A matched comparison under the same poses, friction and solver settings gives direct evidence on the symmetry-versus-selectivity tradeoff.

**Contingency:** C6, if simulated G2-class force or fit proves inadequate. This requires a D-04 variant decision.

**Third geometric alternative:** C4, only if C1/C2 show lateral centering failures.

**Negative findings:** C5 (stroke margin, finger volume) and C7 as primary (insufficient counter-torque without pressing or a fixture).

**Minimum falsifiable simulation experiment:** E2-3 / E2-4 in [`PHASE_1_2_VALIDATION_EXPERIMENTS.md`](PHASE_1_2_VALIDATION_EXPERIMENTS.md). Run a coaxial 90° turn with the C1 and C2 turner tips at axial offset errors of 0, ±1, ±2, ±3 mm, and record the wrong-layer rotation angle and contact force on the middle layer. C2 should hold selectivity across the sweep; C1 is expected to fail beyond its margin. If C2 does *not* show this advantage, the datum rationale is falsified.

**Parameter ranges to carry into CAD-free simulation (`PROPOSAL`, not dimensions for manufacture):**

| Parameter | Range to sweep | Basis |
|---|---|---|
| Pad width b | 10–30 mm | Torque couple vs handoff clearance |
| Turner insertion depth / shoulder depth | 12–17 mm | h − c − e, with c = 0.5–2 mm, e = 0.5–3 mm |
| Stabilizer insertion | 22–35 mm | covers both non-turning layers |
| Pad compliance (`solref`/`solimp`) | stiff ↔ silicone-like | S32 motivates compliance; sim values have no physical calibration yet |
| Sliding μ | 0.3–1.0 | `ASSUMPTION` range |
| Torsional coefficient | 0–patch diameter (≈ 0–0.02 m) | S11 semantics |
| Grip force | 10–50 N | S22 |
