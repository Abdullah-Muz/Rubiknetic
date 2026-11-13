# Mechanical Feasibility Assessment — Two xArm7 Arms Manipulating a Dynamically Constrained Cube

**Date:** 2026-11-12 · **Phase:** 0 · **Gate:** G0 · **Verdict:** `CONDITIONAL` (§10)
**Nature of this document:** preliminary, closed-form engineering estimates from sourced facts and **explicitly labeled assumptions**. **No simulation has been run.** Every number below is either cited (S-ID, see [`PHASE_0_SOURCE_REGISTER.md`](PHASE_0_SOURCE_REGISTER.md)), derived (`INFERENCE`), or assumed (`ASSUMPTION`).

---

## 1. Assumptions and sourced parameters

| Symbol | Quantity | Value / range | Status | Source |
|---|---|---|---|---|
| a | Cube edge | 57 mm (keep parametric 55–58 mm) | `ASSUMPTION` anchored by sources | S01 (ADR mean 0.057 m; mesh pitch 19.05 mm), S03 (5.6 cm) |
| h | Layer height | a/3 ≈ 19.0 mm | `INFERENCE` | — |
| m | Cube mass | ≈0.09 kg (0.036–0.158 kg sweep) | `ASSUMPTION` | S01 ADR range (randomization, not measurement) |
| F | Per-jaw squeeze force | 10–50 N (G2); ≤30 N (original gripper) | `FACT` | S22, S21 |
| μ | Pad–cube sliding friction | 0.3–1.0 | `ASSUMPTION` (no plastic-on-silicone measurement sourced) | — |
| b | Pad width | 10–30 mm (stock pad 30 mm) | design variable; stock `FACT` | S19 |
| τ_req | Face-turn resistance | **0.03–0.6 N·m** working bracket | `ASSUMPTION` (no measurement found) | — |
| e_rob | Arm repeatability | ±0.1 mm | `FACT` | S21 |
| Δ_G2 | G2 tip axial shift, 67 → 57 mm aperture | ≈2.2 mm | `INFERENCE` from the official L(d) relation | S22 |
| δ_play | Cubie radial elastic play (model) | −1.0 … +0.2 mm (robogym spring range) | `FACT` (as a sim choice, not a measurement) | S02 |
| J7 | Wrist roll range | ±360° | `FACT` | S21 |

**How the τ_req bracket was formed (`ASSUMPTION`):** a fingertip force f applied tangentially at the layer edge (lever a/2 = 28.5 mm) gives τ = f·a/2. For f = 1, 3, 5, 10 and 20 N this is 0.029, 0.086, 0.143, 0.285 and 0.570 N·m. The low end represents a well-lubricated speedcube; the high end represents a stiff or partially misaligned cube (S07 reports qualitatively that resistance rises with adjacent-face misalignment). **This bracket must be replaced by measured data before any threshold is registered.**

## 2. Geometry of the coaxial layer grasp

The turner's jaws squeeze two opposite side faces of the target layer, and the turning axis is the face normal. That axis lies in both pad planes and coincides with the wrist-roll axis (J7) when aligned. The stabilizer grasps the other two layers the same way from the opposite end (see the sketch in [`GRIPPER_DESIGN_TRADEOFFS.md`](GRIPPER_DESIGN_TRADEOFFS.md) §2).

## 3. Torque-transmission capacity (`INFERENCE`, rigid-body statics)

Two mechanisms transmit torque about the turning axis from jaws to layer:

1. **Tangential friction** at both pads, each at lever a/2: τ_f = 2 · μF · (a/2) = **μ F a**.
2. **Normal-force couple.** Rigid parallel pads pressed on flat faces resist relative rotation because rotating the slab would force the jaws apart. By virtual work, rotating by δθ against pads of width b (b ≤ a) separates them by ≈ b·δθ, so τ_N ≈ **F b** before the gripper is back-driven. This assumes the G2 linkage resists back-driving at the commanded force, which is **unverified** for the real gripper and depends on the sim actuator model.

Upper estimate τ_cap ≈ F (b + μ a); lower bound (compliant pads, back-drivable jaws) τ_cap ≈ μ F a.

| F [N] | μ | friction-only μFa [N·m] | b = 10 mm | b = 20 mm | b = 30 mm |
|---|---|---|---|---|---|
| 10 | 0.3 | **0.171** | 0.271 | 0.371 | 0.471 |
| 10 | 0.6 | 0.342 | 0.442 | 0.542 | 0.642 |
| 10 | 1.0 | 0.570 | 0.670 | 0.770 | 0.870 |
| 30 | 0.3 | 0.513 | 0.813 | 1.113 | 1.413 |
| 30 | 0.6 | 1.026 | 1.326 | 1.626 | 1.926 |
| 50 | 0.6 | 1.710 | 2.210 | 2.710 | 3.210 |
| 50 | 1.0 | 2.850 | 3.350 | 3.850 | **4.350** |

**Margin (`INFERENCE`):**
- Against the *central* resistance assumption (~0.1 N·m), even the weakest case (10 N, μ = 0.3, friction only) gives ≈1.7×.
- Against the *pessimistic* 0.57 N·m, the weakest case fails and **≥ 30 N with μ ≥ 0.6 or a rigid pad couple** is needed.
- **Conclusion:** torque is feasible within the G2 range unless real resistance exceeds ~1 N·m. Grip force should not simply be maximized, because squeeze also loads the cube internally, which matters for the M1 contact model (§8).

**Stabilizer:** it reacts the same torque on a two-layer (38 mm) slab with the same formulas, so it has an equal or larger margin. It must also react the turner's off-axis forces (§5).

**Wrist torque:** τ_req ≤ 0.6 N·m. The J7 joint torque rating is not published (S21). The MJCF actuator limit (±20 N·m class) is a model value. `ASSUMPTION`: J7 capacity ≫ 1 N·m, to be confirmed from UFACTORY documentation before any hardware claim.

## 4. Layer-selectivity error budget (`INFERENCE`)

**Coaxial turner.** The fingertip must stop short of the layer boundary: d_max = h − c − e_axial.

| clearance c | e = 0.5 mm | e = 1 mm | e = 2 mm | e = 3 mm |
|---|---|---|---|---|
| 0.5 mm | 18.0 | 17.5 | 16.5 | 15.5 |
| 1.0 mm | 17.5 | 17.0 | 16.0 | 15.0 |
| 2.0 mm | 16.5 | 16.0 | 15.0 | 14.0 |

**Side-approach turner.** The pad height must fit inside the layer on both sides: t_max = h − 2c − 2e.

| clearance c | e = 0.5 | e = 1 | e = 2 | e = 3 |
|---|---|---|---|---|
| 0.5 mm | 17.0 | 16.0 | 14.0 | 12.0 |
| 1.0 mm | 16.0 | 15.0 | 13.0 | 11.0 |

**Axial error contributors (`INFERENCE`):**

| Contributor | Magnitude | Note |
|---|---|---|
| Arm repeatability | ±0.1 mm | `FACT` S21; negligible |
| G2 axial tip shift with aperture | ≈2.2 mm (deterministic) | Compensable by modeling L(d) (S22); an error only if ignored |
| Cube pose estimate (privileged sim) | ≈0 | Phase 2 debug mode |
| Cube pose estimate (vision, Phase 5) | **unknown**, plausibly mm-scale | `ASSUMPTION`; drives the C1-vs-C2 choice |
| Cubie elastic play | up to ~1 mm in S02's model | Model-dependent |
| Cube held by stabilizer: slip along axis | unknown | Must be measured in E2 experiments |

**Stock fingers fail:** the Menagerie pad span is ≈37 mm (`FACT` S19) and even a single stock pad is 19.0 mm tall, so the margin is zero. **Custom fingertips are required** (consistent with D-04).

**Corner sweep:** the turning layer's corners sweep a radius of a/√2 ≈ 40.3 mm about the axis. Stabilizer finger bodies must stay outside this cylinder within the turning layer's axial band. In the coaxial configuration they do, because they occupy the opposite end.

## 5. Bimanual coaxial alignment and internal forces (`INFERENCE`)

If the turner's roll axis is laterally offset from the cube's layer axis by δ, a turn by θ forces the layer center along a circle of radius δ relative to the gripper. The two grasps then fight through the cube with an internal force F_int ≈ K_lat · δ · |2 sin(θ/2)| (peak ≈ 2 K_lat δ at θ = 180°), where K_lat is the effective lateral stiffness of the turner–cube–stabilizer loop.

Peak internal force 2·K_lat·δ:

| K_lat (N/m) | δ = 0.5 mm | δ = 1 mm | δ = 2 mm |
|---|---|---|---|
| 500 (soft impedance, `ASSUMPTION`) | 0.5 N | 1.0 N | 2.0 N |
| 5,000 | 5 N | 10 N | 20 N |
| 50,000 (stiff position control, `ASSUMPTION`) | 50 N | 100 N | 200 N |

Compare these with the *friction* capacity holding the cube in each grasp (2μF ≈ 6–100 N). With stiff position control, a 1 mm misalignment can produce internal forces comparable to or larger than the grasp friction. That would cause slip, cube distortion, or (in the M1 model) jamming. **This is the quantitative justification for the approved force/impedance-aware low-level control (D-08)** and a natural place for residual corrections (D-07). It is a falsifiable prediction for experiment E2-5.

## 6. Workspace and kinematics (`INFERENCE`, to be verified in Phase 2)

- **Payload:** ≈0.82 kg G2 + ~0.09 kg cube + fingertips ≪ 3.5 kg (S21, S22).
- **Wrist range:** a 180° turn in one grasp fits J7 ±360°. Repeated same-direction turns accumulate J7 angle, so the planner must include release-and-unwind steps. This is a Phase 4 cost term.
- **Arm placement:** a cube held between two facing arms (e.g., bases 0.6–1.0 m apart) lies well within the 700 mm-class reach (S21 Cartesian range ±700 mm). Elbow and wrist self-collision, J4/J6 limits (−6…225°, −97…180°) and inter-arm collision **must be checked in simulation**. No reachability claim is made here.
- **Stroke:** 57 mm grasp plus ~5 mm approach clearance per side ≈ 67 mm < 84 mm stroke. The diagonal (80.6 mm) grasp is marginal (C5 rejected).

## 7. Handoffs and reorientation (`INFERENCE`)

- A cube has three face pairs. A coaxial turner occupies one pair with its finger contacts and one axis with its palm. A full handoff frees one pair for the receiving gripper. Finger width and thickness must leave that pair fully accessible (S37 "good clearance" condition).
- Turning a face on a different axis requires that one gripper ends coaxial with the new axis, i.e. at least one regrasp per axis change. The expected regrasp count per solve depends on the move sequence. It is an important manipulation-aware planning cost (master spec §9.1) and is **not estimated here**, because doing so needs the Phase 4 planner.
- Camera coverage: coaxial grasps occlude the end faces, so complete facelet observation needs at least one reorientation (risk R5).

## 8. Interaction with the cube model (`INFERENCE`)

- **M1 (contact-emergent):** gripper squeeze (10–50 N) presses cubies toward the center. With ball joints anchoring every cubie at the center, the radial load is carried by the joints. If S02-style radial springs are added (stiffness 500 N/m, range −1.0 … +0.2 mm), a ~0.5 N inward load already reaches the −1 mm limit. Under 10–50 N squeeze the play is therefore set by the **joint-limit constraint**, not the spring, and limit softness (`solreflimit`) becomes a hidden compliance parameter that must be recorded and swept. Squeeze across a layer boundary also creates normal load between layers, which *raises* turn friction. Grasp force therefore couples into cube dynamics, and this must be measured (E1-7, E2-6).
- **M2 (switched welds):** squeeze loads welds. Deactivating a loaded weld at turn start releases stored constraint force, so it must be checked for impulses (E1-5).
- S01's model was tuned for a dexterous hand, so forces from a 10–50 N parallel gripper are **outside its calibration envelope** (`INFERENCE`).

## 9. Control and learning feasibility on CPU (summary; detail deferred to Phase 3)

- **Residual RL premise:** supported in principle by S50 (residual on top of conventional feedback for contact/friction problems; superposed control signals) and S51 (improvements over imperfect controllers in six MuJoCo tasks). These are the authors' results on their tasks; **no transfer to cube turning is implied.**
- **Compute:** S01 needed 64 V100 GPUs plus 29,440 CPU cores for months. Rubiknetic's single bounded residual skill on a CPU laptop is a different problem class, so the training budget **must be derived from measured steps/s** (E1-8, E2-8). No promise of feasible training time is made.
- **Low-level control:** §5 shows why impedance or force-aware control is necessary even for the classical baseline. Hogan's impedance framework (S54) is the canonical reference. Gains are `ASSUMPTION`s to be tuned in Phase 2.
- **Sensing honesty:** the G2 reports position only (S22). Contact-wrench observations used by the RL policy should be estimated from joint torques or labeled privileged sim data, per the master spec's data-channel rules.

## 10. Verdict — `CONDITIONAL`

**Feasible in principle**, conditional on:

1. **Turning resistance** of the modeled cube is ≲ 1 N·m (unmeasured; it is in the 0.17–4.4 N·m capacity band only if μ and F are adequate).
2. **Custom fingertips** keep the turner inside one layer: insertion ≲ 14–17 mm coaxial, or a mechanical depth datum (C2).
3. **Compliant (impedance) control** limits internal forces under ~1 mm bimanual misalignment.
4. The **cube model** (M1 or M2) remains legal and stable under 10–50 N squeeze, which is unverified and is the most likely technical blocker.
5. **CPU throughput** is adequate for Phase 2 baselines, measured before Phase 3 budgeting.

No condition is shown to be infeasible by available evidence. Conditions 1 and 4 are the highest-risk unknowns.
