# Cube Mechanics — Literature Review and Simulation-Strategy Analysis

**Date:** 2026-11-12 · **Phase:** 0 · **Gate:** G0 · **Brief answered:** [`../CUBE_MECHANICS_RESEARCH.md`](../CUBE_MECHANICS_RESEARCH.md)
**Sources:** IDs refer to [`PHASE_0_SOURCE_REGISTER.md`](PHASE_0_SOURCE_REGISTER.md).
**Claim tags (per `CLAUDE.md`):** `FACT` (directly supported by a cited source) · `INFERENCE` (reasoned from facts) · `ASSUMPTION` (unverified working value) · `PROPOSAL` (recommended action) · `VALIDATED_RESULT` (none exist in this report; no simulations have been run).

---

## 1. Summary

1. **There is a published, open-source precedent for a contact-driven 3×3 cube in MuJoCo that uses *no* constraint switching.** `FACT` (S01 §4.2, S02): OpenAI modeled 26 convex cubelets. Each center has one hinge, and each of the 20 edges and corners has three hinges whose axes pass through the cube center. Turns "rely on the cubelet shapes, contact forces and friction"; there is "no custom physics". This model was used to train policies that were later run on a physical cube, which is task-level evidence of plausible dynamics, though not a validation of mechanical fidelity.
2. **The approved direction D-05 ("dynamic cubie constraints") can be realized in two fundamentally different ways**, and they carry very different risks:
   - **(M1) Contact-emergent topology:** fixed joints anchored at the cube center; *contacts* (which MuJoCo re-detects every step) decide which layer can move. No equality switching.
   - **(M2) Switched equality topology:** cubies are welded to the core or to a rotating center via `eq_active` toggling at aligned states.
   This review finds M1 better supported by evidence and less exposed to switching artifacts. M2 is feasible in principle but has a structural problem: **something other than physics must decide which face is unlocked** (§6.2).
3. **Switching artifacts are real and documented** in MuJoCo user reports. Activating a weld with an unsuitable relative pose caused sudden motion (S15) and, in one case, divergence (S16). Runtime re-anchoring requires writing `eq_data`, which the docs list as "safe with `mj_setConst`" with state-workspace caveats (S10).
4. **No published, instrumented measurement of 3×3 face-turning torque was found.** This is the largest numerical gap for both cube calibration and gripper sizing (§8).
5. **Recommendation (`PROPOSAL`, requires approval):** run a Phase 1 pilot with **M1 (ball-joint variant)** as the lead candidate and **M2** as a matched comparison, plus a single-axis fixture surrogate (**M4**) for controller bring-up. Because M1 satisfies D-05 through *contact* constraints rather than switched equalities, the interpretation of D-05 needs your explicit decision (see [`PHASE_0_RESEARCH_FINDINGS.md`](PHASE_0_RESEARCH_FINDINGS.md) §7).

## 2. Physical mechanism of a conventional 3×3 cube

| Element | Description | Tag / source |
|---|---|---|
| Visible pieces | 26 cubies: 8 corners, 12 edges, 6 centers | `FACT` S01, S03 |
| Core | Three intersecting axes ("axles") to which the 6 centers attach; centers rotate in place with 1 DOF | `FACT` S01, S03 |
| Retention | Edges and corners have inward tabs/extensions held by neighbors, which are ultimately retained by the centers | `FACT` S01 ("little plastic tabs that extend towards the core") |
| Preload | Spring-tensioned center fasteners (screws in older official cubes, rivets in newer ones; clones may use clips) | `FACT` (tertiary) S03 — treat as indicative only |
| Torque propagation | "It is enough to apply force to a single cubelet to rotate a face, as it will be propagated between the neighboring elements via contact forces" | `FACT` S01 |
| Base friction | "The components of the cube constantly exert pressure on each other which results in a certain base level of friction" | `FACT` S01 (qualitative) |
| Blocking / forgiveness | When one face is rotated by a sufficient angle, perpendicular faces are locked. If that angle is small, the face often "snaps" back to alignment, a property called "forgiveness" that varies strongly between cube models | `FACT` S01 |
| Detents | Competition cubes may contain magnets that stabilize alignment | `FACT` S06 (Reg. 3h+) |
| Nominal size | ~56–57 mm (Wikipedia "5.6 cm"; OpenAI ADR average 0.057 m; OpenAI mesh spacing 19.05 mm ⇒ 57.15 mm) | `FACT` S01, S02, S03; the exact value is **cube-specific**, so keep it parametric |
| Mass | ~0.09 kg is plausible (OpenAI ADR average 0.0902 kg, range 0.036–0.158) | `ASSUMPTION` — ADR ranges are not measurements |

**INFERENCE — the mechanical fact that matters most for simulation:** every legal cubie motion is a rotation about an axis through the cube center. A corner or edge never translates independently of a rotation about the center. Its radial distance is fixed (up to elastic play), and *which* rotations are admissible is decided by contact with neighboring layers. This is exactly the kinematic structure that S01/S02 encode with center-anchored joints.

## 3. Requirements a credible simulation must reproduce

`INFERENCE` from the brief, the master spec §5, and §2 above:

1. **Retention:** no cubie detaches; radial distance stays within elastic play.
2. **Legal kinematics:** only whole-layer rotations about the three face axes, including middle layers if the model allows them (decide explicitly; spec move set is `U D L R F B`).
3. **Exclusion:** perpendicular layers cannot rotate simultaneously beyond the forgiveness angle, so the model must *jam* rather than tear.
4. **Orientation invariants:** no in-place corner twist or edge flip. Total corner twist ≡ 0 (mod 3), total edge flip ≡ 0 (mod 2), permutation parity consistent.
5. **Causality:** layer motion is caused by external contact wrench, with no hidden actuators on layers or centers.
6. **Resistance:** a calibratable turn-resistance torque (Coulomb-like plus damping) and optional detents.
7. **Observability:** cubie poses must be extractable for an *independent* discrete-state verifier.

## 4. Relevant MuJoCo capabilities and caveats (verified against docs)

| Capability | What the docs say | Implication | Source |
|---|---|---|---|
| Runtime equality toggling | `mjData.eq_active` toggles equalities; initial value from `eq_active0` | API exists; says nothing about physical validity | S10 |
| Changing weld anchors at runtime | `eq_data` is "Safe with `mj_setConst`"; `mj_setConst` uses `mjData` as workspace and "wakes all sleeping trees, so call `mj_resetData` or restore the state before continuing" | Mid-episode re-anchoring needs save/restore of state around `mj_setConst`, or careful direct writes that must be verified | S10, S12 |
| Weld default pose | If `relpose` is unspecified, the weld enforces the pose from `qpos0` | A weld activated far from its reference pose will *pull* bodies together, an energy injection | S12; observed in S15, S16 |
| Collision filtering | Excluded: same body; parent–child (disableable); bodies welded with no joint. **Siblings are checked**; `contype/conaffinity` bitmask | Center-anchored sibling cubies under one core body collide with each other by default, as M1 requires | S11 |
| Mesh collision | Meshes are replaced by their **convex hulls** | Interlocking internal tabs (non-convex) cannot be modeled with a single mesh. Use convex pieces (S43) or convex external shells only | S11, S13 |
| Contact softness | Soft contacts allow penetration; `margin`, `gap`, `solref`, `solimp` tune it; `timeconst` ≥ 2× timestep | Layer interfaces need small gaps or bevels to avoid catching (S01's bevel finding) | S11, S13 |
| Joint friction | `frictionloss` models dry friction and applies to *all* DOFs of a joint (including ball) | Gives a direct, physically interpretable turn-resistance parameter on center hinges or cubie joints | S12 |
| Torsional/rolling friction | `condim` 4/6; torsional coefficient has units of length (≈ contact-patch diameter) | Relevant to inter-layer sliding and to fingertip torque transfer | S11, S12 |
| Slip suppression | Elliptic cones plus large `impratio`; noslip solver optional with stability caveats | Relevant for gripper–cube contact, not for inter-layer sliding (where slip *is* the motion) | S13 |

## 5. Existing simulators and mechanical models

### 5.1 OpenAI Dactyl cube (S01) and the robogym code (S02) — primary precedent

- **Structure (`FACT`, S02 XML):** a root body `middle` (free via 3 slides + ball) with a small core sphere. There are 6 driver bodies with one hinge each (the centers), and 20 cubelet bodies, each with **three hinges** (x, y, z, axes through the cube center) plus one **radial slide "spring"** (stiffness 500, range −1.0 to +0.2 mm). Geometry is a `rounded_cube` mesh. Defaults: `condim=6`, friction `0.2 0.0025 0.0005`, joint damping 0.0005, frictionloss 0.0005, armature 0.0001.
- **Reported behaviour (`FACT`, S01):** perfectly cubic cubelets were "highly unforgiving", so edges were bevelled 1.425 mm. Springs were tried and found unnecessary in the paper. The *released* XML still contains radial springs (discrepancy noted in S02).
- **Kinematic edits (`FACT`, S02 code):** helper functions `rotate_face`, `soft_align_faces` and `align_angles` write `qpos` directly. By call-site inspection they are used on the *physical* cube only during **reset** (scrambling, random face angles) and on a separate *goal* model for visualization. Code comments name **Euler-angle gimbal lock** as a motivation for alignment helpers.
- **Relevance:** strong. It shows a contact-only cube is tractable in MuJoCo and was good enough to train policies used on hardware.
- **Limitations:** calibration was "very rudimentary"; there is no published torque or forgiveness measurement. The three-hinge Euler parametrization has singularities. Fidelity was never validated against a mechanical benchmark.

### 5.2 Other cube robots (context)

- Dual-arm humanoid solving with Kociemba and RRT-Connect, 86 % success (S30, abstract only).
- High-speed multi-fingered hand: regrasp and face turn on a plane using environmental constraints, 70 % success over 30 cycles (S31, abstract only).
- Neither publication describes a physics *simulation* of cube internals. **No other peer-reviewed simulator of cube internals was found** in this session (an evidence gap; see §10).

## 6. Candidate simulation strategies

### M1 — Contact-emergent topology with center-anchored joints (lead candidate)

- **Model:** core body (free joint) → 6 center bodies (1 hinge each, axis = face normal) plus 20 cubie bodies, each with a **ball joint at the cube center** (`PROPOSAL`: a ball joint rather than S02's 3 Euler hinges, to remove gimbal-lock singularities). Optionally add a radial slide with a stiff spring for elastic play, as in S02. Cubie collision shapes are convex bevelled boxes (S01's 1.425 mm bevel is a starting point, not a requirement).
- **How legality arises (`INFERENCE`):** a cubie can only rotate about the center. Rotating it alone would push neighbors in its ring, so motion propagates around the ring as a layer (S01's "propagated … via contact forces"). Perpendicular rotations collide with the other layer and jam. Corner twist or edge flip in place requires deep penetration of neighbors, which soft contacts resist but do not make impossible. **The independent oracle must therefore check orientation invariants** (§9).
- **Constraint count:** no equality constraints. DOF = 6 + 6 + 20×3 = **72** (92 with radial slides). There are **48** face-adjacent cubie pairs (computed), each producing 1 or more contacts per step.
- **Satisfies non-teleportation by construction:** nothing is ever switched. Layer membership changes only because cubies physically move.
- **Risks:**
  - (a) Edge catching or jamming at layer boundaries under soft-contact penetration (S01 needed bevels).
  - (b) Cumulative misalignment and drift with no detent, so later perpendicular turns may jam; S01 calls this "forgiveness".
  - (c) Turn resistance must come from joint `frictionloss`, damping or contact friction under preload. With rigid center anchoring there is little normal preload between layers unless radial springs are preloaded.
  - (d) The contact count dominates CPU cost.
  - (e) Ball-joint plus contact interactions under large grasp forces are unvalidated.
- **Relation to D-05:** constraints *do* change dynamically (MuJoCo's contact set *is* a set of constraints), but there is no `eq_active` switching. **This is an interpretation question for you, not a silent change.**

### M2 — Switched equality topology (the literal D-05 reading)

- **Model:** core plus 6 hinged centers, as in M1. Each of the 20 non-center cubies has a free joint and predeclared welds: cubie↔core (20) and cubie↔each center (20 × 6 = 120), so **≈140 predeclared welds**, with about 20 active at any time. At an aligned state all cubies are welded to the core. To turn face X, the 8 cubies currently in layer X are re-welded to center X, whose hinge then carries the layer.
- **Switching rules (`PROPOSAL` if pursued):**
  - Switch only when all 6 face angles are within an alignment tolerance and relative velocities are below a threshold.
  - Set each newly activated weld's `relpose` to the **current** measured relative pose, so the constraint violation is zero at activation and no energy is injected (S15, S16 show the failure when this is not done).
  - Log every switch.
- **Structural problem — the unlock decision (`INFERENCE`):** at an aligned state a real cube lets *any* face start turning, and the physics decides which one. Under M2 a **rule** must choose which layer to release *before* it moves. A rule based on the controller's intended move would violate the spirit of D-06 (hidden actuation by intent). A rule based on *measured* external torque about each face axis (unlock the face whose net contact torque exceeds a breakaway threshold and dominates the others) is defensible as a model of static friction. But it is an algorithmic event detector whose thresholds and tie-breaks become hidden mechanism parameters. Simultaneous torques on two faces must *jam*, not pick a winner.
- **Advantages:** cheap. Intra-cube contacts can be disabled (collisions excluded), so DOF and contacts are small, and the layer kinematics are exact while welded.
- **Risks:**
  - (a) Activation impulses or relpose errors (S15, S16).
  - (b) `eq_data` re-anchoring plus `mj_setConst` state handling (S10).
  - (c) Legality is enforced by code, not by physics, so the validator risks validating the model against itself (forbidden by `CLAUDE.md`).
  - (d) Misaligned locking can freeze small errors into the state.
  - (e) "Forgiveness" and jamming behavior must be hand-coded.

### M3 — M1 plus physically motivated detents (variant, only if pilots show need)

- Adds a passive, potential-derived detent torque on center hinges (periodic with π/2) to emulate magnets (S06 confirms magnets exist in real cubes). It is implemented as a documented passive force that depends only on state, never on the commanded move. **Must be disclosed** as a modeling element.
- Purpose: counter drift and misalignment in M1 and model the "snap back" forgiveness S01 describes.

### M4 — Single-axis fixture surrogate (test infrastructure, not a cube model)

- A core plus one hinged layer with calibrated `frictionloss`, held by a fixture. It is used only to bring up grasp/turn controllers and torque logging before the full cube is trusted. It does not satisfy D-05 and must never be reported as a cube result.

### Comparison

| Criterion | M1 contact-emergent | M2 switched welds | M3 = M1 + detents | M4 surrogate |
|---|---|---|---|---|
| Non-teleportation by construction | **Yes** | Conditional (switch audit) | Yes (detent disclosed) | Yes |
| Who decides the active layer | Physics (contacts) | **Rule / event detector** | Physics | Fixed |
| Jamming of perpendicular turns | Emergent | Must be coded | Emergent | N/A |
| Orientation-invariant risk | Soft-contact penetration under extreme load | Low while welded | As M1 | N/A |
| Switching-artifact risk | None | **High** (S15, S16) | None | None |
| Implementation complexity | Moderate (geometry tuning) | High (state machine, re-anchoring) | Moderate+ | Low |
| CPU cost (`INFERENCE`) | Higher (≥48 contact pairs) | Lower (contacts excludable) | As M1 | Lowest |
| Published precedent | **S01/S02** | None found | Partial (magnets: S06) | — |
| D-05 interpretation | Needs approval | Literal | Needs approval | Not a cube model |

## 7. Numerical instability from constraint switching (M2) — analysis

`INFERENCE`, grounded in S10–S16:

- MuJoCo equalities are **soft constraints**. On activation, any existing violation is resolved over the constraint's time constant, which produces an impulse proportional to the violation. Zero-violation activation (relpose = current relative pose) removes the position-error impulse. It does **not** remove velocity mismatch: if the two bodies are moving relative to each other, the weld absorbs that relative momentum, which is a dissipative but discontinuous event.
- Deactivation releases stored constraint force instantly. If a weld was carrying load (e.g., a gripper squeezing a layer), the layer can jump.
- **Required audit (`PROPOSAL`):** for every switch, log the pre/post relative pose, relative velocity, total kinetic energy, constraint force norm and penetration. Flag any switch whose kinetic-energy change or constraint impulse exceeds a pre-registered threshold. Run the same sequence at ≥3 timesteps and solver settings, and report sensitivity.

## 8. Physically meaningful rotation torque and resistance

- **Sources of resistance in a real cube (`FACT`, qualitative, S01):** inter-piece friction under internal pressure, joint friction, elasticity.
- **Model parameters that represent it:** center or cubie joint `frictionloss` (Coulomb breakaway, units N·m for rotational DOFs), joint damping (viscous), contact friction with radial preload, and detents (M3).
- **Measured values:** **none found.** S02's frictionloss 0.0005 N·m and S01's ADR randomization are *simulation tuning values*, not measurements. S07 only confirms qualitatively that resistance rises with misalignment of the adjacent face.
- **Consequence:** turning resistance must be treated as an **uncertain parameter swept over a wide range**. The working bracket in [`MECHANICAL_FEASIBILITY_ASSESSMENT.md`](MECHANICAL_FEASIBILITY_ASSESSMENT.md) is 0.03–0.6 N·m (`ASSUMPTION`).
- **`PROPOSAL` (optional, low cost, your choice):** a bench measurement on one or two physical cubes, e.g. a lever arm and a digital luggage or kitchen scale. Record breakaway and running torque at 0°, 5° and 10° misalignment of the adjacent face. This would turn the largest unknown into data. It is outside simulation scope, so it is offered, not assumed.

## 9. Independent cube-state and constraint validation

`PROPOSAL`, consistent with the master spec §5.1 and `CLAUDE.md`:

1. **Discrete oracle** (`cube_logic`): a cubie-level permutation/orientation model with legal moves, inverses, `M^4 = I`, parity and twist/flip invariants. It is independent of MuJoCo.
2. **Physical-state extractor:** from cubie body poses, round each cubie to the nearest legal slot and orientation, and **reject** the state if any cubie exceeds a pose tolerance (no silent rounding). Then derive the discrete state.
3. **Agreement test:** after a *physically observed* completed turn, the extracted state must equal `oracle.apply(observed_move)`, where `observed_move` is inferred from which layer actually rotated, **not** from the command.
4. **Model-independent invariants** checked every N steps: radial distances, layer coplanarity, interpenetration depth, twist/flip sums, energy and velocity anomalies.
5. **Negative controls:** a corner-twist torque attack; perpendicular simultaneous torques (must jam); a turn attempted at 20° misalignment (must block); a command without contact (must not turn).

## 10. CPU-only computational considerations

- **No throughput numbers are claimed.** No benchmark has been run.
- `INFERENCE`: M1 cost is dominated by narrow-phase collision across ≥48 cubie pairs plus the constraint solve. M2 can exclude intra-cube contacts. Both add the two-arm model (≈26 robot DOF in Menagerie xArm7 with gripper ×2).
- **Scale caution (`FACT`, S01):** the Dactyl Rubik's policy used 64 V100 GPUs and 29,440 CPU cores for months. Rubiknetic's scope (one residual skill on a CPU laptop) is deliberately far narrower, and throughput must be **measured** before any RL budget is set.
- **Version caution (`FACT`, S14):** MuJoCo 4.0.x was released one week before this review and drops Python 3.10. Pin a version during Phase 1 setup and record it. Ecosystem compatibility is unverified.

## 11. Findings, unresolved questions and the recommended pilot

**Strongest-supported approach:** M1 (ball-joint variant), based on S01/S02 precedent and switch-free causality.
**Credible alternative:** M2, as a matched comparison and fallback if M1 cannot be made forgiving or CPU-tractable.
**Unresolved (ordered by impact):**

1. Real turning torque and forgiveness angle (no data).
2. Whether M1 jams or drifts under gripper-scale squeeze forces (10–50 N) that are far larger than human finger forces.
3. Bevel and gap geometry needed for reliable 90° and 180° turns.
4. CPU throughput.
5. Whether middle-layer (slice) motion must be excluded or allowed.

**Minimal falsifiable pilot (Phase 1, not executed):** detailed in [`PHASE_1_2_VALIDATION_EXPERIMENTS.md`](PHASE_1_2_VALIDATION_EXPERIMENTS.md), experiments P1-1 to P1-8. Each mechanism candidate is driven by an external *contact probe* (no robot): quarter turn, half turn, `R U R' U'`, and the negative controls listed in §9.
