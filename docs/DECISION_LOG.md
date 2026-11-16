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
| P-01 | Interpretation of D-05: may contact-emergent topology (M1) satisfy "dynamic cubie constraints", with switched welds (M2) as a comparison? | **APPROVED 2026-11-12** (user: "approved") |
| P-02 | Phase 1 cube pilot set M1 + M2 (+ M4 bring-up fixture) | **APPROVED 2026-11-12** |
| P-03 | Phase 2 fingertip pilot set C1 + C2 (C6 contingency, C4 third); simulation primitives only, **no CAD** | **APPROVED 2026-11-12** |
| P-04 | Coaxial opposed grasp as the primary turning strategy | **APPROVED 2026-11-12** |
| P-05 | Canonical findings path `docs/research/` and doc-reference updates (spec §13, RESEARCH_PLAN, PHASE_0, briefs) | Approve (spec edit needs approval) |
| P-06 | `CONTACT_AND_RL_FINDINGS` full review: now, or deferred to before Phase 3 | Defer |
| P-07 | Optional bench measurement of real cube turning torque | User's choice |
| P-08 | Record G0 as `CONDITIONAL` once P-01…P-04 are approved | **DONE 2026-11-12** (G0 recorded `CONDITIONAL`) |

### New open questions

| Open ID | Question | Evidence / approval needed |
|---|---|---|
| O-09 | Real 3×3 face-turn breakaway/running torque and forgiveness angle | No published measurement found; bench test or sourced data |
| O-10 | Does M1 remain legal and non-jamming under 10–50 N gripper squeeze? | Phase 1 E1-4/E1-6 under probe loads; Phase 2 E2-6 |
| O-11 | MuJoCo version pin (4.0.x vs 3.x) and Python version | Dependency compatibility check at Phase 1 setup |
| O-12 | Which G2 model source (Menagerie has the original xArm gripper geometry) and G2 CAD license | UFACTORY downloads/license review |
| O-13 | xArm7 joint torque ratings (not on the official spec page) | Official UFACTORY documentation |

## Phase 1 log — 2026-11-12

Work: environment pin, independent cube oracle, M1 MJCF + contact rig + edit/divergence audit, E1-0 calibration
pilot ([`../experiments/E1-0_calibration/README.md`](../experiments/E1-0_calibration/README.md)). **Unscored: no G1 criterion has been verified.**

| Ref | Item | Status |
|---|---|---|
| PH1-01 | Dependency pin: Python 3.12, MuJoCo 4.0.1, NumPy 2.5.4, SciPy 1.18.1, pytest 9.2.0 (`pyproject.toml`, `uv.lock`), WSL2 venv outside OneDrive | Proposed resolution of O-11; awaiting user acceptance |
| PH1-02 | Cube oracle: two independent models (geometry vs Kociemba tables), 57 tests pass | Done (G1 "Logic" row evidence, not yet signed off) |
| PH1-03 | E1-0 found a nominal M1 config: all long sequences match the oracle (see E1-0 findings 6, 10) | Calibration result, unscored |

### Pending decision requests (Phase 1)

| ID | Request | Recommendation |
|---|---|---|
| P-09 | Accept rig v0 (core fixed to world) for E1 scoring; free-core contact-held variant before Phase 2 | **APPROVED 2026-11-12** |
| P-10 | Accept radial retention slide + 1 N preload inside M1 (OpenAI robogym precedent) | **APPROVED 2026-11-12** |
| P-11 | Revise E1-6(d) expectation: "no illegal or oracle-mismatched state" (corner cutting allowed) instead of "blocked at 20°" | **APPROVED 2026-11-12** |
| P-12 | E1-6(c) corner twist: allow a logged `xfrc_applied` test wrench in negative controls only, or require a physical twist probe | **APPROVED 2026-11-12: logged test wrench**, negative controls only |
| P-13 | Pre-register E1 thresholds from E1-0 data | **APPROVED 2026-11-12** ("Fully approved": thresholds as drafted, penetration 0.5 mm, Option A strict 100 %). **Amendment 1** (user-approved, same day, before any scored trial): E1-1…E1-4 radial criterion becomes a pop check (≤ nominal + 0.3 mm). See [`../experiments/PHASE_1_PREREGISTRATION.md`](../experiments/PHASE_1_PREREGISTRATION.md) |
| P-14 | Build M2 (switched welds) as the approved comparison before scored E1 runs, or score M1 first | **APPROVED 2026-11-12: score M1 first**, then build M2 |
| P-17 | **Cube-model direction after D5 and M2 prototypes.** The D5 convex real-mechanism cube is frozen at design B as an unscored high-fidelity reference, because of one-sided forgiveness (~3–4°), 1–1.5 mm penetration under grip and ~60 steps/s. M2 (switched welds) becomes the primary candidate for G1: prototype 9/9, error ≤ 1°, ~1,400 steps/s. Its scored pre-registration is drafted for approval | **APPROVED 2026-11-13** (user: "I approve your recommendation"). See [`../experiments/D5_follower_cube/README.md`](../experiments/D5_follower_cube/README.md), [`../experiments/M2_switched_welds/README.md`](../experiments/M2_switched_welds/README.md) and [`../experiments/PHASE_1_M2_PREREGISTRATION.md`](../experiments/PHASE_1_M2_PREREGISTRATION.md) (APPROVED 2026-11-13; **Amendment 1 approved 2026-11-13**, user "fully approved": setup misalignment ±0.5° per face, shear-dominance unlock rule, E1-7 kv, E1-6e map, E1-5 units fix. **Amendment 2 approved 2026-11-13** (user: "I agree with your recommendations"): E1-6b uses the M1 categorical criterion plus no two layers unlocked at once; the 1.0° relock condition FAILED its smoke check, so the fallback (setup ±0.25°/face, relock 0.5°) is in force. **Amendment 3 approved 2026-11-13** (user: "approved"): scored turner turn_kp 20, turn_kv 0.8; M2 needs layers within ~0.5° (disclosed; a Phase 2 controller requirement). **Scored run 1 (commit 1b0a5e4, seeds 2000–2999) INVALID as a test of the pre-registration** (harness relock deviated from A2; deadlock in 38/40 E1-4 trials; archived, not deleted). **Amendment 4 approved 2026-11-13** (user: "go with A"): relock conformity fix, fresh-grip rule against spurious re-unlock, new scored seeds 3000–3999. Phase 2: Gripper G2 confirmed; xArm7 URDF peak efforts accepted as working torque limits; xArm7 hardware revision pending (model default 1305+). Robot model choices approved: limit G2 opening to 85 mm and extend the pads by 3 mm; calibrate out the ~2 N linkage-spring grip offset; narrow J2/J4 to the 1305 spec if the arms are 1305+; fingertip mount 2×M3 at 12 mm provisionally (caliper check before manufacture); vendor the BSD-3 assets when Phase 2 starts (STEP-derived files excluded). UFACTORY will NOT be contacted (user: "its not needed"). The G2 STEP CAD MAY be used (user: "its fine to use them"); STEP-derived files stay in git-ignored `third_party_cad/` unless the user decides to publish them) |
| P-16 | **Rule change: allow modelled non-contact physical forces (magnets, detents) between pieces.** Context: the convex-only real-mechanism cube (D5) jams on small layer misalignments; real speedcubes use magnets and alignment features | **APPROVED IN PRINCIPLE 2026-11-13** (user: "we are allowed to alter the projects rules for this ... It seems like we simply need to adapt"). **Allowed:** forces between specific pieces (for example embedded magnet pairs, or a core detent), computed by a fixed, documented force law inside the physics model (passive-force callback or plugin), with realistic strengths. **Still banned:** writes to state or forces from outside the model during a run (the edit audit stays); any force that knows the target or acts on a layer as a whole ("pull the layer to the nearest 90°"); scripted rotations. **Required:** disclosure in the model description; energy and impulse analysis; a no-magnet comparison. **Wording APPROVED 2026-11-13** (user: "approved") and applied to `RUBIKNETIC_MASTER_SPEC.md` D-06 and `CLAUDE.md` (physics constraints) |
| P-18 | **Self-alignment direction after D8-0** (2026-11-14, unscored). M2's misalignment is mostly piece-specific: even an ideal correction of all six layers leaves a residual that passes the 0.5° relock tolerance within 4–16 moves (D8-0, [`../experiments/D8_alignment/README.md`](../experiments/D8_alignment/README.md)). So magnets acting on M2 layers (D8-1a) cannot fix the stall. Proposed: D8-1b, an unscored feasibility test of a bevelled contact cube (S01/M1 style) with P-16 piece-to-piece magnet pairs, against a no-magnet comparison, with energy and impulse analysis. Scored use would need a new pre-registration. Also: S01 re-read 2026-11-14 (source register updated) | **APPROVED 2026-11-14** (user: "Yes begin D8-1b"). Magnet layout and strength go to the user for approval before the model is built. **Design APPROVED 2026-11-14** (user selected every recommended option in [`../experiments/D8_alignment/D8_1b_DESIGN_PROPOSAL.md`](../experiments/D8_alignment/D8_1b_DESIGN_PROPOSAL.md) §8): stage 1 on B1 (rigid radius) + B2 (M1 as scored), each with and without magnets; 48-magnet corner-edge layout; nominal 4×2 mm N35 at 1.0 mm gap with the §4.4 sweep; dipole + exact near-field hybrid in `mjcb_passive`, V3–V6 before any trial. Known limit, accepted: magnets do not fix M1's corner-twist weakness |
| P-19 | **Exception to D-15 (no subagents): CI on GitHub Actions** (2026-11-14). One subagent, in an isolated git worktree, prepares a CI workflow (tests on a pinned Python 3.12 / uv / `uv.lock` environment, CPU-only). It does not push; the main session reviews, merges and pushes. CD: nothing is deployed (no release artifact exists yet) | **APPROVED 2026-11-14** (user: "we should have CI/CD on the github as well as github actions, please have a sub agent take care of this"). Scope: this task only; D-15 otherwise unchanged |
| P-20 | **Standing exception to D-15 (no subagents)** (2026-11-14). The main session may use subagents where it judges them useful. Constraints it applies: subagents do not commit or push; their findings come back to the main session, which checks them before anything is recorded as `FACT`; CPU-heavy work is not delegated while trials are running; the CLAUDE.md research-integrity and credit rules apply to them unchanged. First uses: (1) a literature search for real-cube measurements (turning torque, corner-twist resistance, forgiveness, snap-back, speedcube magnets); (2) an independent code review of the D8-1b magnet model and the stage-1 harness | **APPROVED 2026-11-14** (user: "i give permission to use the subagent wherever you find best"). Supersedes P-19's scope limit; the rest of D-15 is unchanged |
| P-21 | **D9: OpenAI's released cube (robogym, MIT, commit 9ff1111) through the D8-1b stage-1 battery** (2026-11-14, unscored diagnostic). Their physics is unchanged; core fixed like ours; rules in `experiments/D9_openai_baseline/PROTOCOL.md`, written before any result. Result (variant A, our solver settings): 63/140 sequence moves vs 103/140 for B1 without magnets; fails opposed torque; numerical failure in corner twist; 2.5–2.9 mm penetration; best forgiveness (±12°); gimbal lock confirmed after y turns. INFERENCE: not a better base for this task; see [`../experiments/D9_openai_baseline/README.md`](../experiments/D9_openai_baseline/README.md) | **APPROVED 2026-11-14** (user: "sure", in reply to the proposal to run it). No locked decision changed |
| P-22 | **D8-1b magnet model revision 2** (2026-11-14). An independent review (P-20) found a spurious alignment-point force (one-sided spline fit), weak V3 checks, cumulative stats, unpaired seeds and an undisclosed T1 deviation. The strengthened V3 then **failed** for tilted pairs (4.7 / 11 / 23 % force error at 2 / 5 / 10°). The near-field correction was replaced by a tilt-aware second-order expansion derived from one rotation-invariant potential. All checks pass, with a validated tilt range of 5° (10° fails on torque). Stage-1 B1 is re-run as revision 2 (`results/stage1_r2/`); revision-1 results and the failing check record are kept. Details: D8 README, "revision 2" | Approved in session 2026-11-14 (user: "approved", after the fix was proposed). No pre-declared signal or criterion was loosened |
| P-23 | **G1 pre-registration for M4** (B1 rigid-radius contact cube + 48 D8-1b magnets), [`../experiments/PHASE_1_M4_PREREGISTRATION.md`](../experiments/PHASE_1_M4_PREREGISTRATION.md). Contents: M1's approved thresholds and Option A; NEW criteria: magnet validity (trials beyond the validated tilt fail), E1-4 growth slope < 0.005°/move, E1-5s snap (0.5° line, disclosed as chosen after stage 1), E1-6m magnet energy/impulse, E1-6n no-magnet comparison; seeds 6000–6999; E1-7 magnet sweep; radial-preload factor dropped (disclosed). **E1-6c option (c):** the corner-twist threshold is set from R1 real-cube bench data before scoring ([`../experiments/R1_real_cube_bench/PROTOCOL.md`](../experiments/R1_real_cube_bench/PROTOCOL.md)) | **APPROVED 2026-11-15** (user: "fully approved"; option (c) was the draft's recommended option, and this reading is recorded as an interpretation). Not frozen until the §6 work, R1 data and the E1-6c amendment are in place |
| P-24 | **M4 pre-registration Amendment 1** (§9). **A1:** nominal piece gap 0.2 → 0.1 mm. Trigger: unscored drift above M1's 1° limit in 9/18 moves at 0.2 mm, 0/18 at 0.1 mm. Conditional on an unscored dress rehearsal (seeds 7000–7999) passing every M4 criterion in every trial, a condition fixed before any rehearsal result. **A2:** E1-6c uses M1's categorical criterion only; NEW E1-6t toy-standard torque test (0.45 N·m, 16 CFR §1500.53(e) form; pass = valid and solved after release, penetration ≤ 0.5 mm); real-cube parity is not claimed; R1 becomes post-G1 validation. The validated magnet tilt stays 5° (the 7.5° V3 extension failed on torque) | **APPROVED 2026-11-15** (user: "i approve your recommenndations"). A1 is conditional as stated. Disclosed: A1 was chosen after seeing unscored drift data; no threshold is changed |
| P-25 | **Outcome of the A1 condition (P-24): FAILED.** The unscored 0.1 mm dress rehearsal (seeds 7000–7999, unmodified M4 runner logic) passed 188 / 204 trials. Failures: non-target drift > 1° in 10 trials [corrected 2026-11-15 from "11", a counting error: the per-trial files show 12 failing moves in 10 trials; pass/fail unchanged; correction approved by the user, P-28] (12 / 1,376 moves, max 1.14°); 4 causality failures (layer motion 45–85 ms before pad force); E1-1 rest rotation 0.56–0.90° in 4 / 20 trials (limit 0.5°; M1 without magnets ≤ 0.04°), reproduced in isolation (seed-specific, not run order). All 1,376 moves oracle-correct; operational tilt ≤ 3.48°, inside the validated 5°. Record: `experiments/D8_alignment/results/rehearsal_gap0.1mm/SUMMARY.md`. **The 0.1 mm gap is not adopted; the registered 0.2 mm configuration stands; no threshold is changed.** INFERENCE: the scored M4 battery at 0.2 mm would fail G1 on drift (the 0.2 mm probe had 9/18 moves over 1°). Side record: E1-7 size checks, 3×1.5 N35 ALL PASS (validated tilt 7.5°); the 4×1.5 N35 run was stopped by memory pressure during V3 (log incomplete; rerun needed) | **RECORDED 2026-11-15** (user approved recording it). Next step (record M4's expected failure and select the next mechanism, a diagnostic first, or a scored run) is open for the user |
| P-26 | **Unscored diagnostic of M4's failures** (2026-11-15; [`../experiments/D8_alignment/results/diag_m4_2026-11-15/SUMMARY.md`](../experiments/D8_alignment/results/diag_m4_2026-11-15/SUMMARY.md); seeds 9000–9599 plus re-simulated rehearsal seeds). FACT: at the registered 0.2 mm gap, drift is a property of the **B1 base** (rigid radius, angular piece play), not of the magnets. Drift median 0.88° with 4×2 mm magnets, 0.93° with 3×1.5 mm and 0.83° without magnets, against 0.013° for M1 with its 1 N preload. A first in-session reading that magnets caused the drift confounded the two changes and is corrected in the record. Drifting pieces move toward square during moves and away from it at rest; M1's per-piece criteria count both. **Runner reproducibility defect:** a reused magnet neighbour list made trial results depend on the previous trial in the worker (same trial: causal in a fresh process, non-causal in the rehearsal worker). Fix: `MagnetSystem.reset_neighbour_list()` at the start of every M4 trial; no physics change; with a test. 4×1.5 mm N35 fails V3 (pair force 5.65 % > 5 %); 3×1.5 mm passes (validated to 7.5°) but snaps less reliably | **APPROVED 2026-11-15** (user: "approved, lets do it" for the diagnostic; "1-3 approved" for the runner fix and for committing the records). No threshold changed. The follow-up test proposed alongside (lock B1's radial travel) rested on a wrong premise, since B1 has no radial joint; it was not run |
| P-27 | **(a) 0.05 mm gap study** (unscored, 2026-11-16; diagnostic SUMMARY §5). B1 + 4×2 mm magnets at a 0.05 mm piece gap passed all 21 trials on every M1 and M4 criterion. Drift max 0.70°, rest ≤ 0.28°, snap ≤ 0.11°, magnet tilt ≤ 1.40°, turning torque near the 0.2 mm level, corner twist 23.7° at 5 N·m. Without magnets, 0.05 mm jams. Small sample; realism of a 0.05 mm clearance unknown. **(b) Play-criteria proposal** ([`../experiments/PLAY_CRITERIA_PROPOSAL.md`](../experiments/PLAY_CRITERIA_PROPOSAL.md)). Revision 1: independent review judged it a weakening. Revision 2 was approved by the user on condition of a second review; that review required changes (counterexamples, a crossing drag of −0.9° → +0.9° among them), so revision 2 is **not in force**. Revision 3 adopts every required and optional change | (a) Run as approved (user: "do both"). (b) Revision 3 **awaits the user's approval**. Never applies to M4 |
| P-28 | **(a) Play-criteria proposal, revision 3** ([`../experiments/PLAY_CRITERIA_PROPOSAL.md`](../experiments/PLAY_CRITERIA_PROPOSAL.md)), with a third independent review before any use. **(b) Correction of P-25** and of the diagnostic SUMMARY (lines 58 and 106): drift > 1° occurred in 10 trials of the 0.1 mm rehearsal, not 11. The error was found by an independent recount of the per-trial files; pass/fail is unchanged | **APPROVED 2026-11-15** (user: "all approved"). (a) is **conditional**, as for revision 2: revision 3 comes into force only if the third independent review (P-20 subagent) requires no changes. If the review requires changes, revision 3 is not in force and the proposal returns to the user. It applies only inside a new pre-registration approved before that mechanism's first scored trial, and **never applies to M4**. The running 0.05 mm rehearsal does not use it: its CONDITION.md fixes M1 and M4 criteria. (b) applied |
| P-15 | Drake (hydroelastic contact) feasibility for a real-mechanism cube. D3 showed that MuJoCo convex collision cannot represent the CAD's concave spherical bearings: either the chunks overlap and must be loosened, after which the corner pops at 0.05–0.1 N·m, or about 34k chunks are needed | **Exploration APPROVED 2026-11-13** (user: "okay lets try Drake"). The scope is an unscored feasibility test in a separate environment. **MuJoCo remains the locked simulator**; any platform change needs a separate explicit approval and a master-spec revision |

## Phase gate status

| Gate | Status |
| --- | --- |
| G0 Research | **CONDITIONAL PASS** — 2026-11-12, user approved P-01…P-04. Conditions: O-09…O-13 remain open; P-05…P-07 still pending |
| G1 Cube physics | **IN PROGRESS — M1 NOT PASSED** (2026-11-12, frozen Option A, commit `cfbc5c6`). E1-1/2/3/5 pass. E1-4 fails 38/40, on the radial pop check only (0.304 and 0.331 mm vs 0.3). E1-6 fails 7/20: E1-6b radial change 0.82–0.89 mm vs 0.5; E1-6c 7/8 numerical failures, and 1/8 non-credible (12.9 mm penetration). E1-7 shows 3 fragility flips. E1-8 measured. See [`../experiments/E1_scored/README.md`](../experiments/E1_scored/README.md). Under the pre-registered mechanism rule, M2 becomes the candidate. **2026-11-13:** the unscored diagnostics D1–D5 explain the failure; D5 is frozen as the high-fidelity reference; M2 prototype 9/9; M2 is the primary candidate (P-17) and its pre-registration is APPROVED (2026-11-13). Scored run 1 was INVALID (harness deviation, archived); Amendment 4 applied; a fresh scored run on seeds 3000–3999 is pending. No G1 criterion verified for M2 yet |
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
