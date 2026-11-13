# Rubiknetic — Architecture Decision & Approval Log

**Status:** User approvals from architecture-planning conversation on **2026-11-12**. Technical selections are **design decisions**, not evidence of implementation feasibility. Future entries must record rationale, alternatives, evidence and explicit approval.

| ID | Decision / status | Rationale / limitations |
| --- | --- | --- |
| D-01 | **Approved:** Name `Rubiknetic` | Rubik-related project identity; trademark/name availability requires separate check |
| D-02 | **Approved:** MuJoCo | CPU-first contact simulation; topology feasibility not yet proven |
| D-03 | **Approved:** Two UFACTORY xArm7 arms | Seven-axis bimanual configuration; model, mount and workspace still to validate |
| D-04 | **Approved direction:** Parallel grippers with research-informed custom fingertips | Final gripper variant, fingertip geometry, dimensions, material, compliance and tooling **open** |
| D-05 | **Approved:** Dynamic cubie constraints | Must preserve legal physical connectivity; runtime toggles alone do not establish feasibility |
| D-06 | **Approved:** Level C contact-driven physical turns | No scripted face rotations or solver-to-pose overwrite during evaluation |
| D-07 | **Approved:** Reinforcement learning required as a substantive project component | No requirement to outperform classical controller for honest scientific result |
| D-08 | **Approved:** Hierarchical/residual RL + Cartesian commands + impedance/force-aware low-level control (E+C+D) | Initial action bounds and controller dynamics TBD |
| D-09 | **Approved:** Initially one classical stabilizing arm, one learned turning arm | Later role exchange and cooperative handoff |
| D-10 | **Approved:** Eventual camera-based cube perception | Early privileged sim state for debug; final scored autonomy via cameras |
| D-11 | **Approved:** CPU-only target on Ryzen 7-class 32GB WSL2 | No NVIDIA CUDA assumption, benchmark performance empirically |
| D-12 | **Approved:** Eight phases 0–7 with milestones and acceptance gates | Non-sequential independent tasks allowed, no bypass of dependent gates |
| D-13 | **Approved:** Extensive research of gripper/fingertip design before CAD | Literature, mechanical analysis, at least six concepts, comparative report |
| D-14 | **Proposed working scope:** Single 3×3 cube, legal scrambles, independent cube oracle | Initial benchmark, not proof of hardware fidelity |
| D-15 | **Proposed working method:** Claude Code single interactive session, no subagents; user retains change/push approval | Supports auditability and preferred development workflow |

## Open decisions — intentionally deferred

| Open ID | Question | Evidence / approval needed |
| --- | --- | --- |
| O-01 | Which exact xArm7-compatible gripper model? | Official CAD, actuator geometry, MuJoCo assets, license, physical feasibility |
| O-02 | Which fingertip geometry/compliance and identical vs asymmetric setup? | Literature, torque/clearance matrix, simulation pilot, explicit user selection |
| O-03 | Which mechanism realizes legal dynamic cubie topology in MuJoCo? | Phase 0 investigation and Phase 1 validated transition tests |
| O-04 | What cube dimension, mass, friction and turn resistance? | Sourced measurements, uncertainty ranges, sensitivity study |
| O-05 | RL residual bounds, update frequencies, impedance values, reward coefficients? | Measured controller stability, pilot tests, audit and reproducibility |
| O-06 | Camera layout and illumination? | Visibility/occlusion analysis and calibration experiments |
| O-07 | Benchmark numerical tolerances and minimum statistical samples? | Pilot variance, sourced mechanical tolerance and pre-registered protocol |
| O-08 | Final asset licensing and public project branding? | Verify third-party CAD licenses and naming implications before release |

## Phase 0 research log — 2026-11-12

Reports: [`research/PHASE_0_RESEARCH_FINDINGS.md`](research/PHASE_0_RESEARCH_FINDINGS.md) (consolidated), with the source register, cube and gripper reviews, tradeoffs, feasibility assessment and proposed Phase 1/2 experiments in `docs/research/`. **No decision above (D-01…D-15) has been changed.**

### Evidence recorded against existing decisions

| Ref | Decision | Evidence (source IDs from `research/PHASE_0_SOURCE_REGISTER.md`) | Effect |
|---|---|---|---|
| EV-01 | D-02 MuJoCo | Open, contact-driven, switch-free 3×3 cube model precedent (S01 §4.2, S02, MIT); torsional/rolling friction and runtime equality toggling documented (S10–S13) | Supports D-02 |
| EV-02 | D-05 dynamic constraints | `eq_active` exists (S10). Weld activation artifacts reported (S15, S16). `eq_data` re-anchoring "safe with mj_setConst" with state caveats (S10) | Supports the spec's warning that the API ≠ validity; raises P-01 |
| EV-03 | D-04 custom fingertips | Menagerie xArm pads span ≈37 mm vs 19 mm layer (S19) | Custom fingertips are **necessary**: supports D-04 |
| EV-04 | D-08 impedance control | Closed-form internal-force estimate under bimanual misalignment (feasibility §5) | Supports D-08 (estimate, not a result) |
| EV-05 | D-03 xArm7 | J7 ±360°, 3.5 kg payload, ISO flange (S21); G2 10–50 N, replaceable fingers, position-only feedback (S22) | Supports D-03; flags the lack of force feedback |
| EV-06 | D-11 CPU-only | No throughput measured yet. Dactyl reference compute was 64 V100 GPUs + 29,440 CPU cores (S01) for a far larger learning problem | Neutral; throughput must be measured (E1-8, E2-8) |

### Pending decision requests (awaiting explicit user approval)

| ID | Request | Recommendation |
|---|---|---|
| P-01 | Interpretation of D-05: may contact-emergent topology (M1) satisfy "dynamic cubie constraints", with switched welds (M2) as a comparison? | Yes; pilot both |
| P-02 | Phase 1 cube pilot set M1 + M2 (+ M4 bring-up fixture) | Approve |
| P-03 | Phase 2 fingertip pilot set C1 + C2 (C6 contingency, C4 third); simulation primitives only, **no CAD** | Approve |
| P-04 | Coaxial opposed grasp as the primary turning strategy | Approve |
| P-05 | Canonical findings path `docs/research/` and doc-reference updates (spec §13, RESEARCH_PLAN, PHASE_0, briefs) | Approve (spec edit needs approval) |
| P-06 | `CONTACT_AND_RL_FINDINGS` full review: now, or deferred to before Phase 3 | Defer |
| P-07 | Optional bench measurement of real cube turning torque | User's choice |
| P-08 | Record G0 as `CONDITIONAL` once P-01…P-04 are approved | — |

### New open questions

| Open ID | Question | Evidence / approval needed |
|---|---|---|
| O-09 | Real 3×3 face-turn breakaway/running torque and forgiveness angle | No published measurement found; bench test or sourced data |
| O-10 | Does M1 remain legal and non-jamming under 10–50 N gripper squeeze? | Phase 1 E1-4/E1-6 under probe loads; Phase 2 E2-6 |
| O-11 | MuJoCo version pin (4.0.x vs 3.x) and Python version | Dependency compatibility check at Phase 1 setup |
| O-12 | Which G2 model source (Menagerie has the original xArm gripper geometry) and G2 CAD license | UFACTORY downloads/license review |
| O-13 | xArm7 joint torque ratings (not on the official spec page) | Official UFACTORY documentation |

## Phase gate status

| Gate | Status |
| --- | --- |
| G0 Research | **IN REVIEW** — Phase 0 findings submitted 2026-11-12; proposed `CONDITIONAL`; **not passed** until user approves P-01…P-04 |
| G1 Cube physics | **NOT STARTED** |
| G2 Robot / gripper | **NOT STARTED** |
| G3 RL | **NOT STARTED** |
| G4 Bimanual autonomy | **NOT STARTED** |
| G5 Perception / recovery | **NOT STARTED** |
| G6 Full solve | **NOT STARTED** |
| G7 Release | **NOT STARTED** |

## Change request template

```text
Date / author:
Affected decision ID(s):
Current requirement:
Proposed alternative:
Reason and evidence (sources or trial IDs):
Scientific / safety / compute / scope implications:
Alternatives rejected and why:
User approval (explicit):
Master-spec revision + affected docs:
Validation gates that need rerun:
```
