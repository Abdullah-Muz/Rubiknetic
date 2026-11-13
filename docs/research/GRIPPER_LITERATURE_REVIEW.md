# Robotic Grippers and Fingertips for Cube Manipulation — Literature Review

**Date:** 2026-11-12 · **Phase:** 0 · **Gate:** G0 · **Brief answered:** [`../GRIPPER_DESIGN_RESEARCH.md`](../GRIPPER_DESIGN_RESEARCH.md)
**Sources:** IDs refer to [`PHASE_0_SOURCE_REGISTER.md`](PHASE_0_SOURCE_REGISTER.md). Tags: `FACT` / `INFERENCE` / `ASSUMPTION` / `PROPOSAL` (no `VALIDATED_RESULT`s exist).
**Companion reports:** concept comparison in [`GRIPPER_DESIGN_TRADEOFFS.md`](GRIPPER_DESIGN_TRADEOFFS.md); numbers in [`MECHANICAL_FEASIBILITY_ASSESSMENT.md`](MECHANICAL_FEASIBILITY_ASSESSMENT.md).

---

## 1. Summary

1. **The binding constraint is layer selectivity, not torque.** A parallel-jaw grasp on one layer can transmit roughly 0.17–4.4 N·m over the official G2 force range (feasibility report §3), which is well above any plausible turning resistance. The danger is touching the *adjacent* layer.
2. **The stock MuJoCo xArm gripper pads cannot grip a single layer.** `FACT` (S19): each finger carries two 30 × 4 × 19 mm pad boxes centered 18 mm apart, so the contact span is about **37 mm**, roughly two cube layers (a layer is 19 mm). Custom fingertips are therefore *necessary*, not optional. This independently confirms decision D-04.
3. **The approach direction determines how hard the fingertip problem is.** If the turning gripper approaches **along the face's rotation axis** and turns with wrist joint 7 (±360°, S21), plain flat fingers work, provided their **insertion depth** stays within one layer. If it approaches **perpendicular** to the rotation axis, the pad height itself must fit inside 19 mm minus tolerances, which requires narrow or stepped jaws (`INFERENCE`; geometry in the tradeoff report).
4. **Fingertip surface material matters more than shape for torque about the grasp axis.** `FACT` (S32): on an ABB YuMi, designed A30 silicone tips raised grasp success from 28.7 % (factory rigid tips) to 93.7 %. The authors explicitly note that torques about the principal grasp axis "are difficult to resist with two fingers". Directional gecko adhesives failed by *rotational slip*.
5. **Published cube-manipulating robots fall into four families:** specialized center-driven machines, dual-arm humanoids (S30), high-speed multi-fingered hands using environmental constraints (S31), and dexterous in-hand RL (S01). **No peer-reviewed study of parallel-jaw fingertip geometry for layer-selective cube turning was found.** Rubiknetic's fingertip design must therefore be derived from first principles and validated in simulation, not copied.

## 2. Platform facts (verified)

### 2.1 xArm7 arm — `FACT` (S21 official; S19 model)

| Property | Value | Rubiknetic relevance |
|---|---|---|
| Payload | 3.5 kg | Gripper (≈0.8 kg) + cube (≈0.09 kg, `ASSUMPTION`) leave a large margin |
| Repeatability | ±0.1 mm | Small next to the cube's 19 mm layer; pose *estimation* error will dominate |
| Joint 7 range | ±360° (official); ±6.28319 rad in the MJCF | A 180° face turn fits within one grasp; cumulative turns need wrist "unwinding" |
| Max joint speed | 180°/s | A 90° turn ≥ 0.5 s at J7 limit (not a constraint for Phase 2) |
| Flange | ISO 9409-1-A50 | Standard mounting; custom adapters are possible |
| Joint torque ratings | **Not published on the spec page** | MJCF actuator limits (±20 N·m for J5–J7 class) are model values, not ratings (`ASSUMPTION` until sourced) |

### 2.2 Gripper options

| Gripper | Stroke | Grip force | Feedback | Fingers | Sim model | Source |
|---|---|---|---|---|---|---|
| xArm Gripper (original) | 84 mm | max 30 N | position only | — | Menagerie `ufactory_xarm7` (BSD-3), 2 pads/finger | S21, S19 |
| **xArm Gripper G2 (AG1200)** | 84 ± 1 mm | **10–50 N**, programmable torque | position only | **replaceable** | none found in Menagerie; reuse or adapt the S19 linkage | S22 |
| Robotiq 2F-85 (adaptive) | 85 mm | 20–235 N | (per Robotiq docs) | adaptive 4-bar | Menagerie `robotiq_2f85` (BSD-2), `impratio=10` | S23 (unopened), S20 |

`INFERENCE`: neither UFACTORY gripper reports contact force, so grasp force in a future real system would be *commanded*, not *measured*. In simulation, contact forces are available but should be labeled privileged for the final camera/sensor-honest evaluation.
`FACT` (S22): the G2 fingertip moves along the approach axis as the jaws open. Reconstructed from the official example values, L ≈ 175.9 mm at d = 0 and ≈165.2 mm at d = 85 mm. Between a 67 mm pre-grasp and a 57 mm grasp the tip shifts ≈2.2 mm axially (feasibility report §4), which is a direct contributor to layer-boundary error.

## 3. Existing robotic Rubik's Cube systems

| System | Mechanism | What was demonstrated | Relevance | Source / access |
|---|---|---|---|---|
| Specialized solvers | Motors coupled directly to cube faces/centers | Fast solves | **Excluded**: equivalent to hidden face actuation (violates D-06's spirit). Noted only as the approach Rubiknetic is *not* taking | S30 abstract states existing robots use "specialized hardware structures"; no specific machine was verified |
| Dual-arm humanoid "Baymax" | Two arms, HSV vision, Kociemba, 18 predefined actions via RRT-Connect | 86 % success (abstract) | Closest system-level analogue. Shows dual-arm cube solving is achievable with conventional planning | S30 (abstract) |
| High-speed multi-fingered hand | Two regrasp primitives plus one face-turn primitive; cube on a plane; environmental constraints | 30 turn+regrasp cycles in 10 s at 70 % success | Shows that **environmental constraints** (a table) can substitute for a second hand | S31 (abstract) |
| Shadow Dexterous Hand + RL (Dactyl) | Five-finger in-hand manipulation, ADR, massive compute | Per S01 Table 6 (10 trials): full 26-rotation fair scramble completed **20 %** of the time when face angles came from the sensorized Giiker cube, and **0 %** with vision-only face angles (20 % for half the scramble). | The cube model is the relevant part. The hand approach is a **non-goal** (master spec §3). The vision-only gap is a caution for Phase 5 | S01 (partial) |

## 4. Bimanual manipulation and regrasping

- **Clearance governs dual-arm regrasp success.** `FACT` (S37): dual-arm regrasp beats single-arm when "the two hands can grasp the object with good clearance". With overlapping grasps it is "bad". `INFERENCE`: on a 57 mm cube, two grippers and their fingers compete for the same few faces. **Finger thickness and lateral width are therefore first-order design variables**, because they determine which face pairs remain free for the other hand during handoffs.
- **Parallel grippers can do in-hand regrasping with a second arm.** `FACT` (S38, YuMi): a manipulation-graph planner sequences pushes and regrasps using both hands interchangeably. This supports the role-swap requirement with identical tools.
- **Role vocabulary.** `FACT` (S39): the taxonomy distinguishes symmetric and asymmetric coordination and hand roles. Rubiknetic's Phase 2 split (Arm A stabilizer, Arm B turner) is an *asymmetric, coordinated* pattern. Handoffs are a separate sequential pattern.
- **Single-gripper alternatives.** S41 (extrinsic dexterity) and S42 (gravity and controlled slip) are *leads* for reorienting the cube against the table or gripper instead of handing it off. They were not read beyond metadata.

## 5. Gripper architectures compared (literature view)

| Architecture | Strength for cube turning | Weakness | Evidence |
|---|---|---|---|
| Rigid parallel jaw (xArm/G2) | Simple, stiff, symmetric; wrist roll gives a clean turning axis; fingers replaceable (G2) | Two contacts resist grasp-axis torque poorly without good pads (S32); no force sensing | S21, S22, S32 |
| Adaptive parallel (Robotiq 2F-85) | Higher force range; widely modeled; pinch mode behaves like a parallel jaw | Changes the D-04 hardware assumption; heavier; fingertip is the same selectivity problem | S20, S23 |
| Three-finger / high-speed hand | Can grip and flick a face within one hand (S31) | Custom hardware; not xArm-standard; out of the approved architecture | S31 |
| Five-finger dexterous hand | Proven full in-hand cube manipulation | Explicit non-goal; extreme compute (S01) | S01 |

`INFERENCE`: nothing found argues that the approved parallel-jaw architecture is mechanically insufficient for cube turning. The weak points it does show (grasp-axis torque, selectivity) are addressable with fingertip surface and geometry.

## 6. Fingertip contact mechanics

### 6.1 How torque reaches the layer

`INFERENCE` (derivation in the feasibility report §3):

- **Coaxial grasp** (jaws squeeze two opposite side faces of the layer; rotation about the face normal, which lies *in* the pad planes). Torque is carried by:
  - (i) tangential friction at both pads, lever arm a/2 each: τ_f = μ F a;
  - (ii) a **normal-force couple**: rigid parallel pads resist rotation of a flat face geometrically, up to τ_N ≈ F b for pad width b, before the jaws are back-driven open.
  This is favorable: the main mode is *not* friction-limited.
- **Pad-normal torque** (rotation about the jaw-closing axis, as when a parallel gripper pinches an object and something tries to spin it between the fingers). This is the case S32 calls hard for two fingers. It is resisted only by **torsional friction** over the contact patch. In MuJoCo this is controlled by `condim ≥ 4` and a torsional coefficient with units of length (≈ patch diameter, S11/S12). This mode matters for the **stabilizer** whenever the reaction torque is about its jaw axis, and for the cube during handoffs.

### 6.2 Surface, compliance and slip

- `FACT` (S32): compliant, patterned silicone (A30) greatly outperformed rigid and taped tips in a grasp benchmark.
- `FACT` (S11/S13): in MuJoCo, soft-contact slip is reduced with elliptic cones and higher `impratio`; noslip is a last resort with stability caveats. Menagerie's Robotiq model uses `impratio=10` (S20). The xArm model uses pad `priority=1`, friction 0.6–0.7 and stiff `solref` (S19).
- Leads not read (S34–S36): soft-finger contact radius versus normal force, and limit surfaces for combined sliding and spinning. **No equations from these are used.** The feasibility report uses only standard rigid-body statics and explicitly assumed friction ranges.

### 6.3 Mechanical interference and layer selectivity

- `FACT` (S19): stock pads span ≈37 mm along the finger.
- `INFERENCE`:
  - **Coaxial approach:** the fingertip must stop at least (clearance + axial error) short of the layer boundary. That allows about 14–17.5 mm insertion for 0.5–3 mm axial error.
  - **Perpendicular approach:** the pad height must fit within the layer with clearance on *both* sides, giving 11–17 mm.
  - Finger *bodies* above the pad must not intrude into the adjacent layer's swept volume during the turn (a corner of a rotating 57 mm layer sweeps a radius of ≈40.3 mm).

## 7. CAD, models and licenses

| Asset | License | Status | Source |
|---|---|---|---|
| Menagerie xArm7 + integrated xArm gripper MJCF and meshes | BSD-3-Clause (© 2018 UFACTORY) | Inspected | S19 |
| Menagerie Robotiq 2F-85 MJCF | BSD-2-Clause (© 2013 ROS-Industrial) | README/LICENSE inspected | S20 |
| robogym Rubik's cube MJCF + `rounded_cubelet.stl` | MIT (repository) | Inspected | S02 |
| UFACTORY G2 CAD (STEP) | **Unknown**; UFACTORY downloads page not inspected this session | Lead | seed link in `GRIPPER_DESIGN_RESEARCH.md` |
| Open-source parallel-jaw cube fingertip CAD | **None found** | Gap | — |

`PROPOSAL`: confirm the UFACTORY CAD terms before using G2 geometry in a public repository (open decision O-08).

## 8. MuJoCo gripper-model requirements

`PROPOSAL`, derived from S11–S13 and S19–S20:

1. Represent fingertip contact surfaces as **primitive boxes or capsules** (cheap and stable). Use convex decomposition (S43) only if a stepped or grooved tip cannot be expressed as a few primitives.
2. Use `condim=4` (or 6) on pads so torsional friction exists, and record the torsional coefficient as an explicit, swept parameter, since it is effectively a patch diameter.
3. Use elliptic friction cones with `impratio` raised and swept, and record solver type, tolerance and iterations with every trial.
4. Command grip **force**, not just position. Map the G2's 10–50 N range onto the tendon actuator `forcerange` and verify by measuring simulated contact normal force (the S19 actuator uses `forcerange ±50` with an affine bias, which is not a calibrated N-to-command map).
5. Define a tool frame at the pad center with documented insertion depth. Because the G2 tip moves ≈2 mm axially over the relevant aperture range (S22), compute that offset as a function of aperture.

## 9. Feasibility across cube orientations

`INFERENCE`:

- A coaxial turn needs the target face's axis aligned with the turning gripper's wrist axis. There are 6 faces and 3 axes, and two arms can each hold one axis, so **every change of turning axis requires a regrasp or handoff** unless the stabilizer's orientation already offers the new axis. Planning cost therefore depends on axis changes in the solver sequence, which matches the master spec's "manipulation-aware cost" (Phase 4).
- During a handoff, the receiving gripper must grasp a *different* face pair than the releasing gripper. On a cube that leaves exactly one free pair per configuration, so **finger width and thickness must leave the third face pair unobstructed** (S37 clearance finding).
- Camera visibility: the coaxial configuration occludes the two end faces (finger contact faces are side faces of the layer, and the palms cover the ends). Facelet observation will need reorientation or regrasp. This feeds Phase 5 (risk R5).

## 10. Gaps and limitations of this review

- No paywalled full texts were read. IEEE cube papers (S30, S31) are known only from abstracts, so their gripper geometry is **unknown**.
- No measured cube turning torque exists in the sources found.
- No peer-reviewed parallel-jaw fingertip study specific to puzzle layers was found. The literature on general finger design automation (S33) and soft-finger mechanics (S34–S36) was identified but not read.
- Robotiq specifications were obtained from search-result extraction (S23) and must be re-verified before any selection.
