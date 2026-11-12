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

## Phase gate status

| Gate | Status |
| --- | --- |
| G0 Research | **NOT STARTED** |
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
