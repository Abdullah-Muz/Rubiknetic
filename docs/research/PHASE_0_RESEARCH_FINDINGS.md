# Phase 0 Research Findings — Consolidated Engineering Report

**Date:** 2026-11-12 · **Phase:** 0 · **Gate G0 status proposed:** `CONDITIONAL` — **not passed**; G0 requires your explicit approval of mechanism and gripper directions (see §9).
**Scope honesty:** literature and documentation research plus closed-form estimates only. **No simulation, CAD, code or training has been produced. No experimental result is claimed.**

## Report set

| Report | Purpose |
|---|---|
| [`PHASE_0_SOURCE_REGISTER.md`](PHASE_0_SOURCE_REGISTER.md) | 42 registered sources with access level (26 inspected at abstract level or deeper) |
| [`CUBE_MECHANICS_LITERATURE_REVIEW.md`](CUBE_MECHANICS_LITERATURE_REVIEW.md) | Cube mechanism, MuJoCo capabilities, candidate models M1–M4 |
| [`GRIPPER_LITERATURE_REVIEW.md`](GRIPPER_LITERATURE_REVIEW.md) | Grippers, fingertips, contact mechanics, bimanual regrasp |
| [`GRIPPER_DESIGN_TRADEOFFS.md`](GRIPPER_DESIGN_TRADEOFFS.md) | Seven concepts, weighted matrix, sensitivity |
| [`MECHANICAL_FEASIBILITY_ASSESSMENT.md`](MECHANICAL_FEASIBILITY_ASSESSMENT.md) | Quantitative torque, clearance, alignment and workspace estimates |
| [`PHASE_1_2_VALIDATION_EXPERIMENTS.md`](PHASE_1_2_VALIDATION_EXPERIMENTS.md) | Proposed Phase 1/2 experiments with pass/fail criteria (not run) |

---

## 1. Most important discoveries

1. **A switch-free, contact-driven MuJoCo cube already exists in the literature and in open code.** OpenAI's model (S01 §4.2; MIT-licensed robogym code, S02) uses center-anchored joints and convex bevelled cubelets: "no custom physics", with turns driven by contact and friction. This directly addresses risk R1 and is the strongest single piece of evidence found.
2. **Runtime equality switching in MuJoCo has documented failure modes.** Activating welds without a correct relative pose has produced sudden motion (S15) and divergence (S16). Re-anchoring needs `eq_data` writes, which the docs mark "safe with `mj_setConst`", with state-workspace caveats (S10). The `eq_active` API is real, but as the spec already warns, it is not proof of credible topology switching.
3. **The literal switched-weld reading of D-05 has a structural problem.** Some rule other than physics must choose which layer unlocks at an aligned state. A contact-emergent model lets physics make that choice.
4. **Stock MuJoCo xArm fingertips cannot grip a single layer.** Their contact span is ≈37 mm against a 19 mm layer (S19). Custom fingertips are necessary, which confirms D-04 on evidence.
5. **Torque is not the bottleneck; layer selectivity and bimanual alignment are.** A coaxial parallel-jaw layer grasp transmits ≈0.17–4.4 N·m across the G2's official 10–50 N range (S22) and assumed friction. Under stiff position control, a 1 mm coaxial misalignment between the two arms can produce internal forces of 10–100 N, comparable to or larger than the grasp friction. This **quantitatively justifies the approved impedance-aware control (D-08)**.
6. **The biggest numerical unknown is real cube turning resistance.** No published instrumented measurement was found. All gripper margins currently rest on an assumed 0.03–0.6 N·m bracket.
7. **Platform facts that change implementation details:**
   - The G2 gripper reports **position only** (no force feedback).
   - Its fingertip shifts ≈2.2 mm axially between pre-grasp and grasp aperture.
   - xArm7 J7 is ±360°, so 180° turns fit in one grasp.
   - MuJoCo **4.0.x** (released 2026-11-06/11) drops Python 3.10 and restructures the pip packages.
8. **Citation-integrity catches made during the review:**
   - US4378116 is an 18-element (2×2×2-type) patent, not the 3×3 mechanism.
   - An IROS 2018 author name differs between indexes (Higo/Rigo).
   - OpenAI's 20 % full-scramble rate used a *sensorized* cube; vision-only face angles gave 0 %.
   - robogym's released XML includes radial springs that the paper says were unnecessary.

## 2. Strongest supported mechanical approaches

| Area | Lead | Alternative | Rationale |
|---|---|---|---|
| Cube model | **M1** contact-emergent topology, ball-joint cubies anchored at the center, bevelled convex cubies, calibrated joint friction | **M2** switched welds (zero-violation activation, torque-gated unlock), as a matched comparison | Precedent S01/S02; no switching artifacts; physics decides legality (§1.1–1.3) |
| Grasp geometry | **Coaxial** opposed grasps; turn by J7 roll | Side approach with stepped jaws (C3) | Single-joint turn; selectivity reduces to a depth limit |
| Fingertips | **C2** asymmetric datum tooling (short shouldered turner + long-pad stabilizer) and **C1** identical flat compliant pads, piloted together | C6 adaptive gripper (contingency); C4 grooved | Matrix: C2 first in 99.5 % of weight perturbations; C1 wins if role symmetry is weighted ≥ ~25 % |
| Low-level control | Cartesian impedance with force limits | — | Internal-force analysis (feasibility §5) |

## 3. Remaining technical uncertainties (ranked)

1. Real cube turning torque and forgiveness angle (no data).
2. Whether M1 stays legal and non-jamming under 10–50 N gripper squeeze (its precedent was tuned for a dexterous hand).
3. Pose and seating accuracy achievable at the turner tip (decides C1 vs C2).
4. CPU throughput of cube + two arms (not measured).
5. G2 back-drivability and effective jaw stiffness (affects the normal-force torque couple).
6. xArm7 joint torque ratings (not published on the spec page).
7. UFACTORY G2 CAD license terms (not inspected).
8. MuJoCo 4.0 ecosystem compatibility (Gymnasium/SB3/Menagerie).

## 4. Potential implementation blockers

- **B1 (high):** M1 jams or allows illegal twists under gripper loads, *and* M2 shows switching impulses or brittle unlock logic. This would trigger G1 `BLOCKED` and a scope review. A scripted fallback is never acceptable.
- **B2 (medium):** CPU throughput too low for Phase 3 RL at meaningful sample counts. Mitigations: M2 or simplified collision geometry, shorter episodes, M4 surrogate for early RL. Each mitigation must be disclosed.
- **B3 (medium):** coaxial bimanual alignment cannot be held within selectivity margins without force sensing (G2 has none). Mitigations: C2 datum shoulder, joint-torque-based wrench estimation.
- **B4 (low–medium):** handoff clearance on a 57 mm cube is too tight for the chosen finger widths (S37). This would be found in Phase 4 planning.

## 5. Candidate design directions (for approval, not yet selected)

- **Cube:** pilot M1 and M2 with an identical contact probe and oracle (E1-0…E1-8). Use M4 only for controller bring-up.
- **Gripper:** G2-class parallel jaw (stays within D-04). Fingertip pilot C1 + C2. Parameter sweeps per the tradeoff report §5 (pad width 10–30 mm, turner depth 12–17 mm, stabilizer depth 22–35 mm, μ 0.3–1.0, 10–50 N).
- **Control:** impedance-controlled coaxial turning; residual RL later bounded to Cartesian corrections (unchanged D-07/D-08).

## 6. Recommended feasibility experiments

See [`PHASE_1_2_VALIDATION_EXPERIMENTS.md`](PHASE_1_2_VALIDATION_EXPERIMENTS.md). The three highest-information experiments are:

1. **E1-4 + E1-6 on M1 and M2:** `(R U R' U')×6`, scramble+inverse, and the negative controls. This decides the cube model.
2. **E2-4 layer-selectivity sweep:** a falsification test of C2's datum advantage over C1.
3. **E1-8/E2-8 CPU benchmarks:** these decide whether Phase 3 is affordable.

**Optional, outside simulation scope (your choice):** a simple bench measurement of a physical cube's breakaway and running torque (lever plus scale), at 0°, 5° and 10° adjacent-face misalignment. This would replace the largest assumption with data.

## 7. Are MuJoCo and the xArm7 still justified?

- **MuJoCo — yes, with stronger justification than before.**
  - It has the only verified precedent for a contact-driven 3×3 cube (S01/S02).
  - It provides torsional/rolling friction, soft-contact tuning and runtime equality toggling (S10–S13).
  - It runs on CPU.
  - Caveats: mesh convexification (non-convex cubie internals cannot be modeled directly); MuJoCo 4.0 is brand new, so pin a version.
- **xArm7 — yes.**
  - The 3.5 kg payload, ±360° J7 and ISO flange suit coaxial turning.
  - A BSD-3 MJCF exists (S19).
  - The G2 gripper offers replaceable fingers and 10–50 N (S22).
  - Caveats: no force feedback in the gripper; joint torque ratings unpublished; the Menagerie model integrates the *original* gripper, not the G2.
- **Nothing found argues for changing simulator or arm.** Some evidence suggests the *gripper variant* may matter (C6 contingency), which D-04 already leaves open.

## 8. Documentation audit — inconsistencies found

| # | Issue | Location | Proposed resolution (needs approval) |
|---|---|---|---|
| A1 | Deliverable names and paths conflict: the repo docs require `research/CUBE_MECHANICS_FINDINGS.md`, `GRIPPER_FINDINGS.md`, `CONTACT_AND_RL_FINDINGS.md`, `PHASE_0_DECISION_MATRIX.md`, `PHASE_0_SOURCE_REGISTER.md`; the Phase 0 instruction required five differently named files under `docs/research/` | `docs/RESEARCH_PLAN.md`, `phases/PHASE_0_RESEARCH.md`, briefs, master spec §13 | Adopt `docs/research/` (done for this run). Mapping: CUBE_MECHANICS_FINDINGS → `CUBE_MECHANICS_LITERATURE_REVIEW.md`; GRIPPER_FINDINGS → `GRIPPER_LITERATURE_REVIEW.md` + `GRIPPER_DESIGN_TRADEOFFS.md`; PHASE_0_DECISION_MATRIX → `GRIPPER_DESIGN_TRADEOFFS.md` §4 + cube comparison in the cube review §6; PHASE_0_SOURCE_REGISTER → same name; **CONTACT_AND_RL_FINDINGS → only partially covered** (feasibility §9), and a full RL/contact review is deferred unless you want it now. Update the doc references after approval. |
| A2 | Master spec §13 says findings go in `research/`, experiments in `experiments/` | `RUBIKNETIC_MASTER_SPEC.md` | Amend the path to `docs/research/` only with approval (spec is locked) |
| A3 | "Lock a Python version during Phase 0" has no owner, and MuJoCo 4.0 removed Python 3.10 | Master spec §11 | Proposal: decide at Phase 1 environment setup (Python ≥ 3.11; exact pin after dependency check) |
| A4 | R1 wording "26 external movable cubies, centers/core" is ambiguous | Master spec §4 | Clarify to 8 corners + 12 edges (movable) + 6 centers (rotate in place) + core |
| A5 | D-05's text ("constraint relationships that adapt after face turns") does not say whether *contact* constraints count | Master spec §2, decision log | Your decision (§9, decision 1) |
| A6 | `VALIDATION_PLAN.md` G1 lists no explicit negative controls for corner twist or perpendicular jam | `docs/VALIDATION_PLAN.md` | Add E1-6 controls when thresholds are pre-registered |
| A7 | The `GRIPPER_DESIGN_RESEARCH.md` seed link refers to "gripper G2"; the Menagerie model contains the original gripper geometry | Brief vs S19 | Record O-01 sub-question: G2 model source |

## 9. Decisions requiring your approval

1. **D-05 interpretation (architecture).** May "dynamic cubie constraints" be satisfied by **contact-emergent topology (M1)**, with switched welds (M2) as a comparison? Or must the lead model use switched equality constraints? *Recommendation: allow M1 as lead; pilot both.* This would be recorded as a clarification of D-05, not a reversal.
2. **Cube pilot set.** Approve M1 + M2 (+ M4 bring-up fixture) for Phase 1 pilots.
3. **Fingertip pilot set.** Approve C1 + C2 for Phase 2 (C6 as contingency, C4 third). This does **not** approve CAD. Simulation primitives only, until E2-4/E2-6 results exist.
4. **Grasp strategy.** Approve coaxial opposed grasps as the primary turning strategy.
5. **Deliverable location.** Approve `docs/research/` as the canonical findings path and the doc-reference updates in A1/A2.
6. **CONTACT_AND_RL_FINDINGS.** Defer to before Phase 3 (recommended), or produce now?
7. **Optional physical cube torque measurement.** Yes or no.
8. **G0 status.** Record G0 as `CONDITIONAL` (directions approved, pending G1 evidence on cube-model legality under gripper loads). Approving decisions 1–4 is what would let G0 be marked passed or conditional. Phase 1 must not start before that.
