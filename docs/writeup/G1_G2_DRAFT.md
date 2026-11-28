# Contact-driven layer turns of a simulated Rubik's cube by two robot arms: a pre-registered validation of the cube model (G1) and the two-arm turn (G2)

> **DRAFT generated from project records. Not for publication or circulation without the project owner's approval.**
> Every number below is copied from a committed file in this repository, and the file is cited inline. Nothing here
> goes beyond those records. This is a simulation study only; it makes no claim about real hardware or sim-to-real
> transfer. The authors are a placeholder. Written 2026-11-28 from the repository at commit `fbca90c`.

**Authors:** [AUTHOR LIST TO BE DECIDED BY THE PROJECT OWNER]

**Labels used** (as in the project reports): `FACT` (from a committed record or file), `INFERENCE` (a reading of the
records), `ASSUMPTION` (a modelling assumption stated in a pre-registration). Where a sentence summarises a report,
the report is cited and its label applies.

---

## Abstract

We describe a MuJoCo model of a 3×3 Rubik's cube in which layers turn only through contact forces, with no hidden
actuators, welds or pose writes, and the use of that model by two simulated UFACTORY xArm7 arms with parallel-jaw
grippers. Both steps were tested in pre-registered batteries. Criteria, trial counts and code were frozen before
scoring, trials ran on held-out seeds, any single failure counted against the gate, and independent reviews continued
until a reviewer found the plan acceptable. The cube mechanism (M7: contact cubies, 48 modelled magnets, rounded
edges, MuJoCo NoSlip post-processing) passed 204 of 204 trials of turns, rests and abuse cases
(`experiments/E7_scored_m7/G1_REPORT_M7.md`). In the two-arm battery, one arm holds the cube and the other turns the U
layer by rolling its wrist under a classical impedance controller with a wrist force/torque guard. It passed 128 of 128
scored trials: 100 turn trials with 360 moves, 20 holds and 8 negative cases (`experiments/E8_scored_g2/G2_REPORT.md`).
A review before the freeze found that the cube's magnets had been silently disabled in every earlier two-arm trial. We
describe how this was found and fixed. The results are limited to simulation, to U-family turns from one grasp, and to
the uncalibrated parameters listed in both reports.

## 1. Introduction

**Problem.** Solving a physical Rubik's cube with robot arms needs more than a symbolic solver. A layer has to be
gripped, turned against the friction and detents of the mechanism, and released without disturbing the other layers.
Simulating this credibly is harder than it looks. A cube can easily be made to "turn" in simulation by a motor in its
own core, a joint whose angle is set, or a constraint that snaps a layer into place. Any of these would let a robot
appear to turn the cube without doing the physical work. The project's specification therefore requires that face
rotation be "driven by modeled robot contacts/torques; no scripted cube angles in evaluated runs" (decision D-06,
`RUBIKNETIC_MASTER_SPEC.md` §2). Passive internal mechanisms such as magnet pairs may contribute alignment forces through
a fixed force law, "but turns must be initiated and driven by robot contact" (D-06, P-16).

**This work.** This draft reports the first two validation gates of the project (`docs/VALIDATION_PLAN.md`):
- **G1 (cube physics):** a simulated cube in which layers turn only through contact, checked against an independent
  combinatorial cube model. It passed for mechanism **M7**, after earlier mechanisms M1, M4 and M5 did not pass and M2
  had no valid scored run (`docs/DECISION_LOG.md`, G1 gate row).
- **G2 (robot and gripper):** two xArm7 arms with grippers and custom fingertips. One holds the cube; the other turns
  the U layer by contact, using prescribed classical controllers. There is no learning.

**Contributions** (`INFERENCE`, framed as in `docs/research/M7_NOVELTY_LITERATURE_SEARCH_2026-11-26.md`):
1. A validated configuration of a contact-driven simulated cube, with its abstractions and failure modes documented
   (`G1_REPORT_M7.md` §2–§3).
2. A two-arm, contact-driven U-layer turn on that cube, with controllers that never read cube state, a modelled wrist
   force/torque guard, and pre-registered negative tests (`G2_REPORT.md` §2, §5).
3. An evaluation procedure that applies established practice to a simulated manipulable object: pre-registration,
   frozen code, one-shot zero-tolerance scoring on held-out seeds, bit-identical self-checks, and independent review
   rounds. We do not claim this method is new. Each element has precedent (§2).

The project's long-term goal is full scramble solves with residual reinforcement learning and camera-based state
(`RUBIKNETIC_MASTER_SPEC.md` §1). None of that is reported here.

## 2. Related work

This section uses only sources listed in the project's research reports, at the verification level those reports
record. **These sources were not re-checked for this draft.** Before any publication, each must be re-read in full and
re-cited. A systematic literature search has not been done
(`docs/research/M7_NOVELTY_LITERATURE_SEARCH_2026-11-26.md`, conclusion item 4).

**Simulated cubes.**
- OpenAI, *Solving Rubik's Cube with a Robot Hand* (arXiv 1910.07113, 2019). Their simulated cube used bevels of
  1.425 mm on 1.9 cm cubelets, with "very rudimentary dynamics calibration". This is recorded as read in
  `docs/research/TURNING_TORQUE_FINDINGS.md`, according to the novelty note. The note marks as `UNVERIFIED` that the
  model has 26 convex cubelets and that face rotation is driven by contact and friction
  (`M7_NOVELTY_LITERATURE_SEARCH_2026-11-26.md` §1).
- Li et al., arXiv 1907.11388 (2019): a simulated 2×2×2 cube manipulated by a simulated Shadow hand, with 90.3 %
  success in simulation and a ~5° tolerance provided by chamfers. Verification level FULL according to
  `docs/research/G4_BIMANUAL_REGRASP_LITERATURE_2026-11-28.md` (G4-20).
- K. Zakka, `mujoco_cube` (GitHub, Apache-2.0): a public MuJoCo 3×3×3 model whose centre hinges are driven by six
  actuators. Rubiknetic's contract forbids this form of actuation. Level FULL (README and XML), G4 report, G4-22.
- `INFERENCE` (novelty note §1): a contact-driven cube in MuJoCo is not new in kind. M7's distinguishing feature is
  what has been validated about it.

**Robot cube manipulation with two arms or parallel grippers** (G4 report, table in §5 and source list):
- PR2 (Yang, Lancaster, Smith; ICRA 2017; RA-L 2020). One parallel-jaw gripper holds two layers while the other turns
  the third with a wrist rotation. They report 8/10 solves with pre-touch sensing against 0/10 without, and all
  failures occurred at a regrasp. FULL (G4-01–G4-03).
- Warsaw IRp-6 pair (Szynkiewicz 2012, FULL; Zieliński et al. 2007, ABSTRACT): two arms with position-force control
  while the chain is closed. Force sensing is reported to prevent face jams (G4-04, G4-05).
- A dual-arm humanoid with 86 % success (Chen et al., CCDC 2023; ABSTRACT; S30). A high-speed multi-fingered hand with
  70 % success over 30 turn-and-regrasp cycles in 10 s (Higo et al., IROS 2018; ABSTRACT; S31).
- `INFERENCE` (G4 report §1 item 7): no source found simulates contact-driven layer turns together with handoffs
  between two parallel grippers.

**Simulator validation and evaluation practice** (novelty note §2–§4):
- Zhou et al., *When the Simulator Fails, Not the Policy* (SimuGuard; arXiv 2610.41857). It records every physics
  step, flags contact artefacts, and replays episodes bit for bit with one solver parameter changed. Abstract read
  (`FACT` at abstract level).
- Credibility frameworks for computational models: ASME V&V 40 and NASA-STD-7009 / NASA-HDBK-7009. These are
  `UNVERIFIED`, search summaries only.
- Pre-registration is common in human-robot interaction studies. These are `UNVERIFIED`, except one small robot-learning
  repository whose README was read.

**Tools and assets.**
- MuJoCo: Todorov, Erez, Tassa, IROS 2012 (DOI 10.1109/IROS.2012.6386109; level META,
  `docs/research/PHASE_0_SOURCE_REGISTER.md` S17).
- The MuJoCo documentation on NoSlip (S13, PARTIAL).
- The xArm7 model: MuJoCo Menagerie `ufactory_xarm7`, BSD-3-Clause © UFACTORY (S19, FULL file listing). Joint limits and
  1305+ meshes come from `xArm-Developer/xarm_ros2`, also BSD-3 (`docs/research/G2_STEP1_MODEL_SOURCE_STATUS_2026-11-26.md`).

## 3. Methods

### 3.1 The cube mechanism M7 and its abstraction (G1)
From `G1_REPORT_M7.md` §1–§2 and `experiments/PHASE_1_M7_PREREGISTRATION.md` §1:
- **Contact cube (B1).**
  - 26 convex rigid cubies at 19 mm pitch, each on a ball joint at the cube centre at fixed radius.
  - Piece gap 0.05 mm.
  - Layers rotate only through contact forces between cubies and with whatever touches them.
  - No constraint is switched at runtime, no weld is used, and nothing writes cubie state. An edit audit on every trial
    checks the last point.
- **Rounded edges, R 2.5 mm.** These replaced an earlier 45° 1.4 mm chamfer, which caused a ~6° catch and one jam.
- **Magnets.**
  - 48 point-dipole-equivalent 4×2 mm N35 corner–edge magnets.
  - Their near field comes from precomputed tables validated against reference quadrature.
  - They are applied as a passive force callback with a validated regime of near-pair tilt ≤ 5°.
  - They have no collision geometry.
- **Solver.**
  - MuJoCo implicitfast at 0.5 ms.
  - `noslip_iterations = 10`. NoSlip is a solver post-process that removes residual contact slip velocity. **It is a
    numerical choice, not a physical law** (G1 report §2).
- **Turning in G1** used a test rig: two pads clamp a layer and a torque-limited actuator (clip 1 N·m) rotates them. It
  is a fixture, not a robot.
- **State oracle.** Every observed cube state is checked against an independent cube-logic model: two independent
  implementations, 59 tests (`tests/test_cube_logic.py`).

### 3.2 The two-arm system (G2)
From `G2_REPORT.md` §2 and `experiments/PHASE_2_G2_PREREGISTRATION.md` §1–§2:
- **Cube.** M7 as validated in G1, with a free core (free joint, 1.7 g). Only the cubies hold the core.
- **Arms.**
  - Two xArm7 1305+ models, facing each other on one table.
  - Arm A at the origin; arm B at (1.0, 0, 0) m, yawed 180°.
  - Cube centre nominally at (0.5, 0, 0.30) m, with its U face pointing at arm B.
- **Grippers and fingertips.** Two Gripper G2 models at 20 N.
  - Arm A holds the D and E layers with one flat 30 × 30 × 4 mm pad per finger (P-97).
  - Arm B grips the U layer with the C1 fingertip, 25 × 14 × 4 mm per finger (P-107).
  - Pad friction μ 0.8; pad compliance is a 0.01 s contact time constant (both `ASSUMPTION`s, pre-registration §0
    item 6).
- **Classical controllers.** They read only robot joint states, derived kinematics, the F/T sample, commanded targets
  and time, **never cube or cubie state**. Two tests check this, one of them by showing that arm B's control outputs are
  bit-identical when every cube joint state is scrambled (pre-registration §2).
  - Arm A holds its IK pose with joint position servos.
  - Arm B, joints 1–6: Cartesian impedance at the gripper base (K_P 4000 N/m, D_P 60 N·s/m), with an integral term only
    while the gripper is open.
  - Arm B, J7: a torque law with feedforward and a torque budget. It rolls 1 s per quarter turn on a cosine ramp.
  - The roll direction comes from the nominal layout, never from the measured cube state.
- **Start sequence.**
  - The cube rests on an actuated stand under D and E, with gravity on.
  - Arm A closes on the cube (2 s ramp).
  - The stand drops 30 mm clear.
  - The end of this sequence is t0.
- **One move.**
  1. Arm B settles at the grasp pose and closes.
  2. It rolls J7 by −90° (U), +90° (U′) or −180° (U2).
  3. It holds, opens, and rolls back with the gripper open (pre-registration §2).
- **Wrist F/T guard** (P-114, P-125).
  - A modelled UFACTORY 6-axis F/T sensor sits between arm B's flange and gripper, sampled at 200 Hz with
    N(0, 0.01 N·m) noise. Its size, mass and noise are `ASSUMPTION`s.
  - The roll stops if |τ_z| exceeds 1.0 N·m on two consecutive samples.
  - A J7 stall rule (following error > 2° for 20 ms) also stops the roll.
  - The F/T sensor was adopted after a J7 lag guard false-triggered (P-111). A torque-budget guard was also shown to be
    infeasible at ±20 % J7 model error (P-113).
- **Visual-only parts.** Stickers and the room are off in scored runs. Their physics invariance was shown by an
  identical final-state hash with and without them (P-110, P-112).

### 3.3 Pre-registration, independent review and run integrity
- **Pre-registration.**
  - For G1: `experiments/PHASE_1_M7_PREREGISTRATION.md`, revision 4.
  - For G2: `experiments/PHASE_2_G2_PREREGISTRATION.md`, revision 7.
  - Each document states the configuration, trials, seeds, criteria and verdict logic before any scored data. It also
    discloses which choices were made after unscored rehearsal and pilot results (G1 report §3 item 8; G2
    pre-registration §0 item 1).
  - The scored seed ranges (G1: 17000–17739; G2: 30000–30999) were searched for prior use and never used before the
    scored run (P-93, P-141).
- **Zero tolerance.** A single failing scored trial means the gate is NOT PASSED (P-105). For example, M5 did not pass
  at 203/204 because one rest rotated 0.560° against a 0.5° limit. Under its pre-registration that verdict was final
  (`docs/DECISION_LOG.md`, G1 gate row).
- **Independent review.**
  - Each pre-registration was reviewed by one independent reviewer sub-agent per round, given the plan and the code but
    not the main session's conclusions.
  - Rounds continued until a reviewer returned "ACCEPTABLE AS IS" (P-86, P-121).
  - G1 had 4 review rounds (G1 report §7). G2 had 7 (`G2_REPORT.md` §3).
  - G1's revision 4 came into force under the user's conditional approval of P-91 (P-92). The user approved G2's
    freeze explicitly (P-141).
- **Freeze and integrity machinery** (G2 pre-registration §6; G1 pre-registration §2):
  - The scored runner refuses to start unless the code is frozen and the frozen paths are clean.
  - An immutable manifest records the trial list, the environment, the commit and the SHA-256s of the generated robot
    model, meshes and magnet tables.
  - An append-only start log and an append-only ledger record the SHA-256 of every record.
  - Records are written atomically by the parent process and never overwritten.
  - A resume procedure refuses on any mismatch.
  - A separate `analyze.py` recomputes every pass/fail independently of the trial code.
- **Self-checks.** Before each run, pilot trials were re-run and compared with committed records for physics identity:
  final generalized-position hash, start sequence and observed moves. For G2: 3/3 physics-identical at the freeze
  commit, and 63 tests passed with 0 skipped (`experiments/E8_scored_g2/freeze_check_2026-11-28.log`, P-142).
- **Magnet activity check (added after the defect in §5).** Every G2 record counts the simulation steps without a
  magnet-force evaluation. A trial fails unless that count is 0 and the step count equals simulated time / dt (P-131,
  P-136).

## 4. Results

### 4.1 G1: the cube mechanism M7
**Run** (`FACT`; `G1_REPORT_M7.md` §1, `experiments/E7_scored_m7/RESULTS.md`, P-93):
- one start at commit `2708ba4`, 2026-11-26, 6 workers, 9,789 s;
- seeds 17000–17739, never simulated before;
- 501 records plus 2 registered "not run".

**Verdict: PASS, 204/204 Option A trials.**

| E1-1 rest 60 s | E1-2 quarter turns | E1-3 half turns | E1-4 sequences | E1-5 offsets | E1-5s snap-back | E1-6a open pad | E1-6b opposed torques | E1-6c corner twist | E1-6t toy torque |
|---|---|---|---|---|---|---|---|---|---|
| 20/20 | 24/24 | 22/22 | 40/40 | 42/42 | 20/20 | 6/6 | 6/6 | 8/8 | 16/16 |

- Energy and impulse accounting held on 1,376/1,376 moves (E1-6m).
- The 60 s rests had 0 slip events.
- Integrity: 0 violations, 0 missing records.

| Quantity (G1 scored) | Maximum | Limit |
|---|---|---|
| Non-target drift | 0.761° | 1.0° |
| Penetration | 0.293 mm | 0.5 mm |
| Turn error | 0.372° | 2.0° |
| Rest rotation, 0–10 s | 0.0035° | 0.5° |
| Turner torque | 0.191 N·m | clip 1.0 N·m |

Source: `G1_REPORT_M7.md` §1.

**Reported beyond the verdict** (`G1_REPORT_M7.md` §3):
- **Without magnets the long sequences fail** (E1-6n): E1-3 11/22, E1-4 22/40, E1-5s 8/20.
- **E1-7 fragilities:**
  - at a 0.1 mm piece gap, the sexy6 sequence failed;
  - at a 0.75 ms timestep, both sequences failed on penetration.

**Throughput (E1-8)** (`G1_REPORT_M7.md` §4; `experiments/E7_scored_m7/results_E1-8/bench.json`):
- M7 turning ran at 645 raw steps/s (real-time factor 0.32).
- 16 parallel processes reached 6,010 aggregate steps/s (3.01).
- `INFERENCE` (G1 report): the magnet force law costs about 40 % while turning.

### 4.2 G2: two arms turn the U layer
**Run** (`FACT`; `G2_REPORT.md` §5, `experiments/E8_scored_g2/VERDICT.md`, P-143):
- `run.py all --jobs 8` at manifest commit `a3e4c98`, frozen code of `5aab69d`;
- one uninterrupted start, 138 records in 11,519 s;
- the user paused another project's processes for the whole run.

**Verdict: PASS, 128/128 scored trials.**

| Battery | Result |
|---|---|
| G2-1: 20 × 60 s holds (arm A alone) | 20/20; core slip ≤ 0.16 mm, rotation ≤ 0.34° (limits 1 mm, 1°) |
| G2-2/3: 20 U, 20 U′, 20 U2 | all pass (within the 100/100 below) |
| G2-4: 20 × U U′ U2 U′ U, 20 × 10 random U-family moves | all pass (within the 100/100 below) |
| Turn trials G2-2 … G2-4 together | **100/100, 360 moves, 0 guard stops**; exact 95 % upper bound on the per-trial failure rate **3.0 %** (Clopper–Pearson, 0/100) |
| G2-7 negative cases (scored) | 8/8: two_layer 2/2 detected, collision 2/2 robot contact detected, open_midturn 2/2 detected, jam 2/2 stopped at 43.6° and 40.8° (window 20–50°) |

| Quantity (scored turn trials) | Maximum | Limit |
|---|---|---|
| Turn error | 0.414° | 2° |
| Drift of other layers | 0.307° | 1° |
| Cubie penetration | 0.144 mm | 0.5 mm |
| F/T τ_z, any move | 0.503 N·m | 1.0 N·m stop |
| F/T τ_z, first turn (100) | 0.371 N·m (U′) | 1.0 N·m stop |
| Core slip per move / total | 0.260 / 0.656 mm | 1 / 2 mm |
| Core rotation per move / total | 1.237° / 1.188° | 2° / 2° |
| Roll-back rotation | 0.092° | 1° |
| End misalignment | 1.064° | 4° |
| t0 offset / stand-drop shift | 2.09 / 0.14 mm | 3 / 1 mm |
| Causality gap (force before motion) | min 2 steps (1.0 ms), median 24 | > 0 |
| Drive impulse | min 0.0090 N·m·s | > 0 |
| Magnets | 0 steps without force; near-pair tilt ≤ 2.32°; 0 perpendicular pairs | 0; ≤ 5°; 0 |

Source: `G2_REPORT.md` §5, `VERDICT.md`.

**Reported only** (`G2_REPORT.md` §5):
- **G2-6 sensitivity screen (n = 1 each).** The turn checks passed for K_P ×0.5 and ×1.5, μ 0.5, grip 10, 30 and 50 N,
  and rigid pads.
  - The extra (0, 2, 2) mm offset trial failed the pre-t0 offset check (3.23 mm > 3 mm), as that condition was
    expected to. Its moves passed.
- **offcentre (5 mm):** 2/2 clean.
- **G2-8 throughput:** median real-time factor 0.043 per trial process, with 8 workers.

**Margins** (`INFERENCE`, `G2_REPORT.md` §5):
- Every judged quantity stayed at or below 75 % of its limit.
- The closest were the t0 offset (2.09 of 3 mm) and the per-move core rotation (1.24 of 2°), as the pilots predicted.

**Where the time goes** (`experiments/D19_speed_study/README.md`, unscored, approximate rates):
- In the two-arm scene, a full control step ran at 159 steps/s on one process.
- NoSlip accounts for about 80 % of the step: a bare step is 5.3× faster without it.
- The magnets account for about 16–20 %.
- NoSlip is part of the validated M7 mechanism, so dropping it is not an option for scored evaluation.

## 5. The magnet defect, and how review caught it

This section is included as a lesson, not as a result. All of it is `FACT` from `G2_REPORT.md` §3, the G2
pre-registration §0 item 1a, and P-130 to P-133.

**What happened.**
- The two-arm scene installed the cube's magnet force callback.
- The code then built a separate kinematic model for arm B's pre-grasp inverse kinematics. A helper used there
  (`hold.robot_spec`) uninstalls the passive callback, so that it cannot run on that model.
- The callback was never installed again.
- From the first commit of the two-arm study to pilot 3, **every two-arm trial therefore ran on a cube without
  magnets.** This included the two-arm rehearsal (D18), the arm B gain tuning, pilots P5, 2 and 3, and two
  self-checks.
- The controller gains and several limits were chosen on this magnet-free cube: the F/T stop of 1.0 N·m, the jam
  window, two_layer detection, and the end misalignment.
- Nothing failed loudly. With no magnets, turns still succeeded, so no check flagged the problem.

**How it was found.**
- The fourth independent review of the G2 pre-registration reported it as a required change (N1). The main session
  confirmed it with its own probe: the passive callback was `None` after construction, and the magnet force was
  evaluated once in 3.6 s of simulation (P-130).
- The reviewer's magnets-on probes showed the defect had changed the evidence, for example:
  - turn error on one pilot seed fell from 0.80° to −0.05°;
  - on a forced-misalignment seed, turn error fell from 1.56° to −0.22° and F/T torque from 0.41 to 0.18 N·m (P-130).
- Review rounds 1–3 had each required other changes, and none of them found this defect (`G2_REPORT.md` §3).

**What was done** (P-131, P-132, P-135, P-136):
- The callback is re-installed after the inverse-kinematics model is built.
- Every record now counts the simulation steps without a magnet-force evaluation. A trial fails unless that count is 0
  and the step count equals simulated time / dt. This is checked in the trial code and, independently, in `analyze.py`.
- Every pilot was repeated with the magnets on, on new seeds (pilot 4): 144/144 pass.
- Every limit was rechecked against pilot 4 and kept.
- The pre-registration was rewritten from pilot-4 evidence, with an explicit disclosure (revision 5).
- Review 5 independently confirmed that the magnets act at every step. It found no other difference between the
  two-arm cube and G1's M7.
- **G1 is not affected.** D20 ran G1's scored runner on rehearsal seeds for three trial kinds. The magnet force was
  evaluated at every one of 5,179 / 103,120 / 142,000 steps, and the committed records were reproduced exactly
  (`experiments/D20_g1_magnet_check/README.md`, P-133).
- `G2_REPORT.md` §6 item 3 states the remaining limitation: the controllers were tuned without the magnets and were not
  re-tuned.

**Lessons** (`INFERENCE`):
1. A passive force that only *helps* a task can disappear without any task-level check failing. Such a force needs a
   positive, per-step check that it acts.
2. Self-checks that compare a run with earlier records only show that the code did not change. If the earlier records
   share the defect, the self-check confirms the defect.
3. A reviewer given the code, not the author's conclusions, found what three earlier rounds and the author had
   missed. Continuing review rounds until a reviewer accepted the plan was worth its cost here.
4. The same review process also caught an author error later. In revision 7 the main session wrote a false statement
   that `run.py` had not changed since an earlier smoke test. Review 7 flagged it. The text was corrected, and a new
   kill-and-resume smoke test was run at the current code (P-139, P-140).

## 6. Limitations (verbatim from the two reports)

### 6.1 G1 (`experiments/E7_scored_m7/G1_REPORT_M7.md` §3, verbatim)
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
12. **Addendum 2026-11-26 (after sign-off; user-approved, DECISION_LOG P-99): the rig's grip is capped at about 11.5 N.**
    - The rig pad servo (kp 2000 N/m, target 6 mm beyond contact) saturates at about 11.5 N, whatever `grip_force` is
      set (D16-0, [`../D16_free_core_m7/grip_probe.py`](../D16_free_core_m7/README.md)).
    - The scored trials, drawn at 10–20 N, therefore squeezed at about 10–11.6 N.
    - E1-7's 30 and 50 N grip levels ran at about 11.5 N.
    - G1 gives no evidence on squeeze above about 11.6 N. O-10 stays open, as already listed in §7.
    - The verdict is unchanged: no pre-registered criterion depends on the squeeze level.

*(The relative link in item 12 is quoted as written in the G1 report; from this file it resolves to
`experiments/D16_free_core_m7/README.md`.)*

### 6.2 G2 (`experiments/E8_scored_g2/G2_REPORT.md` §6, verbatim)
1. Simulation only; every assumption of §0.6 applies (clearance, turning torque, pad friction and compliance, the F/T
   sensor model, Menagerie joint friction).
2. U-family turns from one grasp only: no regrasp, no other faces, no camera state (G4, G5).
3. The controllers were tuned without the magnets (P-115, P-130) and not re-tuned; pilot 4 shows they work with them.
4. The F/T noise is one seeded stream shared by every trial.
5. Starts within ±1 mm / ±1°. Larger errors were tested only in G2-6 (n = 1 each) and offcentre (reported only).
6. One seed per scored trial; negative cases n = 2 each (detection shown, not a rate).
7. The limits are task tolerances, not tight stabilisation bounds (§8 item 8).
8. The scored run adds no new limitation. Its 3.0 % bound is a per-trial failure rate under the tested start
   distribution only; it says nothing about larger placement errors, other faces or hardware.

*(Here "§0.6" and "§8 item 8" refer to the G2 pre-registration, `experiments/PHASE_2_G2_PREREGISTRATION.md`.)*

### 6.3 Further caveats for this draft (`INFERENCE`)
- **Abstractions of the controller.** G3's baseline B0 is the G2 controller, which is a torque-level Cartesian
  impedance plus a J7 torque law. The real xArm accepts only position or velocity setpoints, so this is an abstraction
  the real arm cannot run (P-134). The same is true of the G2 controller.
- **Open items carried by both sign-offs** (P-95, P-144):
  - O-09: real turning torque;
  - O-10: squeeze legality, screened to 50 N in G2;
  - O-12: G2 CAD licence;
  - O-13 (G1 only): closed in P-96;
  - the arm B joint-limit margin of 19.1°, the tightest kinematic margin (`G2_REPORT.md` §8).

## 7. Reproducibility

**Environment** (`experiments/PHASE_1_M7_PREREGISTRATION.md` §1; `pyproject.toml`):
- MuJoCo 4.0.1, Python 3.12.3, NumPy 2.5.4, SciPy 1.18.1;
- WSL Ubuntu 24.04, virtual environment `~/.venvs/rubiknetic`;
- E1-8 was measured on 16 logical CPUs (`G1_REPORT_M7.md` §4);
- every record stores its environment, and the runners refuse to resume on a mismatch.

**Robot model.**
- The xArm7 + Gripper G2 MJCF is generated from third-party BSD-3 sources by
  `experiments/P2_robot_model/build_model.py` into the git-ignored `third_party_cad/robot/`
  (`experiments/P2_robot_model/README.md`).
- The generated model and meshes are fingerprinted in the G2 manifest (G2 pre-registration §6).
- Without the generated model, the G2 scene tests skip. `G2_REQUIRE_SCENE=1` turns such skips into failures (P-136,
  P-138).

**Commands** (WSL, repository root):
```bash
# G1 (frozen at 2708ba4; seeds 17000-17739)
~/.venvs/rubiknetic/bin/python experiments/E7_scored_m7/run.py all --jobs 6
~/.venvs/rubiknetic/bin/python experiments/E7_scored_m7/analyze.py
# G2 (frozen at 5aab69d, manifest commit a3e4c98; seeds 30000-30999)
G2_REQUIRE_SCENE=1 ~/.venvs/rubiknetic/bin/python -m pytest -rs tests/test_scored_g2.py   # log runs `pytest -rs`
~/.venvs/rubiknetic/bin/python experiments/E8_scored_g2/selfcheck.py --jobs 3
~/.venvs/rubiknetic/bin/python experiments/E8_scored_g2/run.py all --jobs 8
~/.venvs/rubiknetic/bin/python experiments/E8_scored_g2/analyze.py
```
Sources for these commands:
- G1 run usage: `experiments/E7_scored_m7/run.py` docstring; `--jobs 6` from P-93.
- G2: pre-registration §6; the freeze-check log `experiments/E8_scored_g2/freeze_check_2026-11-28.log`; P-142.

A scored runner refuses to start into a non-empty `results/` folder. A reproduction should therefore use a fresh
checkout, or re-run only the verdict scripts on the committed records.

**Seeds.**
- G1 scored: 17000–17739.
- G2 scored: 30000–30999. Of these, 30000–30019, 30100–30139, 30200–30219, 30300–30339, 30600–30607 and
  30700–30709 are used (G2 pre-registration §3).
- G2 pilots: 29000–29999. The F/T noise uses `default_rng(29000)`.

**Commits and records.**

| Item | Commit / path |
|---|---|
| G1 pre-registration in force | revision 4, `2708ba4` (P-92, P-93) |
| G1 scored records | `experiments/E7_scored_m7/results/`, `RESULTS.md`, `run_log.txt`; committed at `4938686` (P-94) |
| G1 sign-off | P-95, 2026-11-26 |
| G2 pre-registration frozen | revision 7, `5aab69d` (P-141) |
| G2 scored run | manifest commit `a3e4c98`; `experiments/E8_scored_g2/results/`, `VERDICT.md`, `verdict.json`, `verdict_runs/`, `scored_run_log.txt` (P-143) |
| G2 sign-off | P-144, 2026-11-28 |

## 8. Future work (gates G3–G7; `docs/VALIDATION_PLAN.md`, `docs/DECISION_LOG.md` gate rows)
- **G3, RL experimental validity.** Authorised, design first (P-145).
  - The baseline B0 is G2's controller (P-134).
  - A bounded residual policy (SAC first, PPO optional) is to be compared with B0, and with no-op and random residuals,
    on matched starts, with all physics validity checks active.
  - The pass criterion is "scientifically honest reproducible comparison, not necessarily an RL win".
  - Simulation cost is the main constraint: about 0.04× real time per trial process (G2-8). D19 proposes a cheaper
    training model validated against full M7, with all final evaluation on full M7. This is a `PROPOSAL` only.
- **G4, multi-move bimanual autonomy.** Not started. It covers regrasp, support transfer and role swaps without
  teleportation, and turns of faces other than U.
- **G5, camera-derived state and recovery.** Not started. It covers calibrated cameras, sticker-based state
  estimation with explicit uncertainty, and detection of injected failures. A camera-placement study exists as
  preparation (`experiments/D21_camera_placement/README.md`, unscored).
- **G6, full solves.** Not started. It requires at least one uninterrupted, independently verified full solve, then a
  pre-registered distribution of unseen scrambles.
- **G7, reproducible release.** Not started. It covers locked dependencies, commands tested from a clean environment,
  licence checks, and a technical report that includes negative outcomes and makes no sim-to-real claim.

---
*End of draft. Before any use outside the project:*
- *re-verify every related-work source;*
- *re-check every number against the cited files at the commit used;*
- *obtain the project owner's approval of content and authorship.*
