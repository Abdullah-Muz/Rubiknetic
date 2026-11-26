# G1 report: M7, a contact-driven Rubik's cube in MuJoCo

**Status.** The scored battery returned PASS (P-93). This report is the "mechanism abstraction and limitations
published" item of G1 (VALIDATION_PLAN G1 "Pass"), with E1-8 and the evidence map. **G1 is passed only when the user
signs off (§7).**

**Labels:**
- `FACT`: from a committed record or file.
- `INFERENCE`: the main session's reading.
- `ASSUMPTION`, `UNVERIFIED`: as defined in the pre-registration.

## 1. What was validated (`FACT`)
**M7**, the configuration under test:
- B1 contact cube: 26 cubies on fixed-radius ball joints about a fixed core;
- piece gap 0.05 mm;
- rounded piece edges, R 2.5 mm;
- M5's 48 corner–edge magnets, 4×2 mm N35, with an ideal-dipole near-field force law;
- MuJoCo `noslip_iterations = 10`;
- implicitfast integration at 0.5 ms.

Layers are turned only by a test rig: two pads clamp a layer, and a torque-limited actuator (clip 1 N·m) rotates
them. Nothing sets a layer angle.

**Scored result** (pre-registration [`../PHASE_1_M7_PREREGISTRATION.md`](../PHASE_1_M7_PREREGISTRATION.md), revision
4; report [`RESULTS.md`](RESULTS.md); DECISION_LOG P-93):
- **Run:** one start at commit `2708ba4`, 2026-11-26, seeds 17000–17739, never simulated before.
- **Option A, 204 / 204 trials passing:**

  | E1-1 | E1-2 | E1-3 | E1-4 | E1-5 | E1-5s | E1-6a | E1-6b | E1-6c | E1-6t |
  |---|---|---|---|---|---|---|---|---|---|
  | 20 / 20 | 24 / 24 | 22 / 22 | 40 / 40 | 42 / 42 | 20 / 20 | 6 / 6 | 6 / 6 | 8 / 8 | 16 / 16 |

  E1-1 used 60 s rests with **0 slip events**.
- **E1-6m:** energy and impulse accounting held on all 1,376 / 1,376 moves.
- **Integrity:** 0 violations, 0 missing records.
- **Margins** (scored / limit):

  | Quantity | Scored | Limit |
  |---|---|---|
  | drift | 0.761° | 1.0° |
  | penetration | 0.293 mm | 0.5 mm |
  | turn error | 0.372° | 2.0° |
  | 0–10 s rest | 0.0035° | 0.5° |
  | turner torque | 0.191 N·m | clip 1.0 N·m |

  No move exceeded 0.2 N·m.

## 2. Mechanism abstraction (what the model is, and is not)
- **Contact-emergent.**
  - Each cubie is a convex rigid body on a ball joint at the cube centre, at fixed radius (B1).
  - Layers rotate only through contact forces between cubies and with the rig pads.
  - There are no switched constraints, no welds, and no pose writes. `m1_model.py` says so, and every trial's edit
    audit (M1 rule 2) checks it.
  - So VALIDATION_PLAN's "switch timing" item does not apply (`INFERENCE`).
- **Geometry.** Cubies at 19 mm pitch with a 0.05 mm piece gap. Edges are rounded at R 2.5 mm instead of M5's 45°
  1.4 mm chamfer. The chamfer caused a ~6° catch and one jam (P-76–P-80).
- **Magnets.**
  - 48 point-dipole-equivalent 4×2 mm N35 magnets at M5's positions.
  - The near field comes from precomputed tables validated against reference quadrature (V3).
  - The force law is applied as a passive callback.
  - The validated regime is near-pair tilt ≤ 5°.
  - Magnets have no collision geometry.
- **Solver.**
  - MuJoCo implicitfast, 0.5 ms, M1's contact settings.
  - **NoSlip 10:** a post-process that removes residual contact slip velocity. It is a numerical choice, not a
    physical law.
- **Rig.** The pads and turning actuator are a test fixture, not a robot.
- **State oracle.** Every observed cube state is checked against an independent cube-logic model: two independent
  implementations, 59 tests (`tests/test_cube_logic.py`).

## 3. Limitations (to be stated wherever the G1 result is cited)
1. **The rest result depends on NoSlip.**
   - Each 60 s rest is preceded by an unjudged 10 s warm-up with no NoSlip. These warm-ups exceeded M1's 0.5° limit
     in 3/20 rehearsal seeds, 1/20 fresh seeds, and **1/40 REST-X seeds in the scored run** (0.541°).
   - With NoSlip, the largest rest was 0.0035°.
   - Rounded edges fixed the turning catch; NoSlip fixed the rest slip.
2. **Clearance is an `ASSUMPTION`.**
   - The 0.05 mm piece gap is not measured, and the project's CAD figures conflict (0.25 mm against 0.033–0.038 mm,
     `UNVERIFIED`).
   - E1-7 shows drift fragility at 0.1 mm. In the scored run the 0.1 mm sexy6 failed and the 0.1 mm 6-move passed.
   - The claim holds for piece gaps up to about 0.05 mm.
3. **Turning torque is uncalibrated.**
   - Scored median 0.103 N·m, max 0.191.
   - The only verified real-cube figure is 0.09 N·m. No torque profile exists in the literature (P-83; research
     addendum 2026-11-25).
4. **The rounded edge is a modelling choice.** R 2.5 mm was chosen because it removed the chamfer catch, not from a
   measured profile; real-cube edge geometry is `UNVERIFIED`. The result holds over R 1.8–3.6 mm (E1-7).
5. **Magnet model limits.**
   - The ideal-dipole law may overstate force by up to 1.5×. The 0.67-scale E1-7 arm passes.
   - In all 8 E1-6c corner-twist abuse trials, near-pair tilt reached 13.8–15.2°, outside the 5° validated range. As
     pre-registered (rule 3) these are labelled, not failed; their no-magnet twins pass.
   - Corner–edge pairs crossing a turning boundary pass lateral offsets of 6–8 mm, while V3a validates 0–6 mm (carried
     from M5).
6. **No radial freedom (B1).** No magnetic preload or radial play is modelled.
7. **Numerical fragility.** At a 0.75 ms timestep, both E1-7 sequences fail (penetration). **The model must run at
   ≤ 0.5 ms.**
8. **Post-hoc choices.**
   - NoSlip 10, rounded edges and the arm L0 were chosen after results on the rehearsal seeds.
   - Only the scored seeds, and the R4 fresh-seed rehearsal, are independent of them.
   - Move strings other than the 20 E1-4 scrambles were seen during development.
9. **Sensitivity is one seed per setting.** E1-7 is a screen, not a statistical estimate.
10. **Simulation only.** Turns come from a rig, not xArm7 grippers (G2). Nothing here establishes sim-to-real
    transfer.
11. **Throughput (E1-8, §4).** About 0.3× real time per CPU core. The magnet force law is the main cost.

**Reported findings beyond Option A** (`FACT`, RESULTS.md):
- **No magnets (E1-6n):** the long sequences fail (E1-3 11/22, E1-4 22/40, E1-5s 8/20). The magnets are needed.
- **E1-7 fragilities:**
  - gap 0.1 mm, sexy6;
  - timestep 0.75 ms, both sequences.

  Every other setting passes, including μ 1.0, NoSlip 0 and no magnets on the short sequences.

## 4. E1-8: CPU throughput (`FACT`; [`results_E1-8/bench.json`](results_E1-8/bench.json), commit `c91b153`, 16 logical CPUs, WSL)
| Scenario (0.5 ms unless noted) | Raw steps/s | Real-time factor |
|---|---|---|
| M7 at rest, cube only | 852 | 0.43 |
| M7 at rest, idle rig | 858 | 0.43 |
| **M7 turning** | **645** | **0.32** |
| M7 turning, 0.25 / 1.0 ms | 660 / 560 | 0.17 / 0.56 |
| Turning **without magnets** | 1,090 | 0.55 |
| Turning **with NoSlip off** | 703 | 0.35 |
| Idle rig without magnets | 3,037 | 1.52 |
| **Parallel turning, 1 / 4 / 8 / 16 processes** | **588 / 2,094 / 3,817 / 6,010** (aggregate) | **0.29 / 1.05 / 1.91 / 3.01** |

- Mean contacts: 36 at rest and 56 while turning.
- The load average was 4.5 at the start, decaying from a preceding unscored check run (recorded).
- `INFERENCE`: the magnet force law costs about 40 % while turning and dominates at rest; NoSlip costs about 8 %.
  Speeding up the magnet evaluation is the obvious lever before G3 (RL).

## 5. Evidence map: VALIDATION_PLAN G1 tests
| G1 test | Evidence | Status |
|---|---|---|
| Logic: inverse identity, 4× quarter turns, valid scrambles, parity and orientation invariants | `tests/test_cube_logic.py`: 59 tests, two independent models (PH1-02); passing | met |
| Physically actuated quarter turn, both signs; state agrees with oracle | E1-2 24/24 | met |
| Half turns and reverse turns | E1-3 22/22; E1-2 counter-clockwise | met |
| Consecutive nonparallel-axis turns, `R U R' U'` and inverse sequences | E1-4 40/40 (sexy6 ×20; 20-move scramble + inverse ×20) | met |
| No target-angle setter, teleportation or hidden actuator | M1 rule 2 edit audit on every trial; observed-move oracle; causality; E1-6a | met |
| Switch timing, force/torque, angular velocity, penetration, continuity, solver sensitivity | No switches (§2); torque per move; penetration criteria; E1-6m; E1-7 timestep, iterations and NoSlip | met, with the §3 fragilities |
| CPU benchmark in several contact/topology configurations | E1-8 (§4) | met |
| **Pass:** categorical invariants; calibrated tolerances met in pre-registered trials; abstraction and limitations published; not a one-turn demo | Option A PASS (P-93); §2–§3 here | met, **pending sign-off** |

## 6. What a G1 pass does and does not establish
- **Does:** M7 is a physically credible contact-driven simulated cube. Under the frozen, pre-registered criteria, on
  held-out seeds, it turns accurately, holds at rest, survives abuse, and stays logically consistent. It is the
  foundation for G2.
- **Does not:**
  - establish fidelity to a specific real cube (torque, clearance and edge are uncalibrated);
  - establish anything about robot grasping (G2), learning (G3) or sim-to-real transfer.

## 7. Sign-off (VALIDATION_PLAN sign-off protocol; filled in when the user signs off)
| Field | Value |
|---|---|
| `gate_id` | G1 (mechanism M7) |
| `date` | — |
| `approver` | — (the user) |
| `test_evidence_paths` | `experiments/E7_scored_m7/RESULTS.md`, `results/`, `results_nomag/`; `results_E1-8/bench.json`; `tests/test_cube_logic.py`; this report; reviews `experiments/M7_PREREGISTRATION_REVIEW{1..4}_*.md` |
| `tolerances_and_trial_counts_pre_registered` | `experiments/PHASE_1_M7_PREREGISTRATION.md` revision 4 (in force at `2708ba4`): M1/M4/M5 criteria plus the 60 s slip rule; 204 Option A trials |
| `PASS/CONDITIONAL/BLOCKED` | — (proposed: PASS, with the §3 limitations) |
| `unresolved_risks` | §3 items 1–11; open items O-09 (real-cube torque), O-10 (gripper squeeze), O-12, O-13 |
| `next_authorized_phase` | — (proposed: G2, robot and gripper, beginning with its Phase 0-style design work) |
