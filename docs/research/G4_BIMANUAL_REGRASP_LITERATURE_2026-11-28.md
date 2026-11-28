# G4 literature review: bimanual regrasp, handoff and face access for a two-gripper cube

**Status:** research findings for Phase 4 (gate G4). Not a design decision, and nothing here has been run.
**Access date for every source:** 2026-11-28.
**Labels:** `FACT` (stated by a source, at the verification level given), `INFERENCE` (this report's reasoning),
`PROPOSAL` (a suggestion for the user to accept or reject). No locked decision (xArm7, G2 gripper, MuJoCo, dynamic cubie
constraints, Level C, E+C+D) is changed or questioned here.
**Context read first:** `phases/PHASE_4_BIMANUAL_AUTONOMY.md`, `docs/SYSTEM_ARCHITECTURE.md`,
`docs/REFERENCES_SEED.md`, `experiments/PHASE_2_G2_PREREGISTRATION.md` §0–§2, `docs/VALIDATION_PLAN.md` G4, and the
existing register `docs/research/PHASE_0_SOURCE_REGISTER.md` (S01, S30, S31, S37–S39 are cross-referenced, not
repeated).

**Verification levels used:**
- **FULL**: the full text (or the full web page) was opened and the relevant sections read. For PDFs this was by
  local text extraction (`pdftotext`) of the downloaded file.
- **ABSTRACT**: only the abstract (via Semantic Scholar, Crossref or arXiv) was read.
- **META**: only title/authors/venue metadata was confirmed. Nothing about the content is claimed beyond that.
- **SNIPPET**: only a search-engine snippet was seen. Used only where marked, never for numbers in the table.

## 1. Summary

1. **The closest published precedent for Rubiknetic's grasp split is the PR2 cube solver** (Yang, Lancaster, Smith;
   G4-01–G4-03). One unmodified parallel-jaw gripper holds two layers; the other grips the third layer and turns it by
   a wrist rotation. Faces are reached by **transferring the cube between grippers and shifting grasps**. Each face is
   only turnable while a given arm holds. 20 face turns needed about 34 motions and 7–8 min (`FACT`, FULL).
2. **Regrasp, not the face turn, is where the only quantitative two-parallel-gripper cube study failed.** With
   position-only dead reckoning the PR2 solved 0/10 scrambles (mean 9.6 rotations completed). With fingertip proximity
   sensing before each regrasp it solved 8/10. **All failed rotations happened at a regrasp** (handoff or grasp for a
   turn). The acceptable cube pose error was about half a cubie (`FACT`, G4-02, FULL).
3. **Two-arm cube systems use force or compliance during the closed-chain phases.** The Warsaw IRp-6 system turned
   faces under position-force control. It says pure position control would build up force from small misalignments in
   the closed chain, and force sensing kept faces from jamming. The arm receiving the cube was force-controlled while
   the holding arm was position-controlled (`FACT`, G4-04 FULL, G4-05 ABSTRACT).
4. **Planning formulations are mature but kinematic.** The standard formulations all check pairwise gripper collisions
   at the handover pose (Wan & Harada, G4-10, FULL; Vahrenkamp et al., G4-12, FULL; Beretta, G4-14, FULL summary):
   - regrasp graphs with transit/transfer edges;
   - a handling configuration bridging two per-arm sub-graphs;
   - offline tables of collision-free grasp pairs, searched with Dijkstra.

   None models contact dynamics during the handoff.
   Dual-arm regrasp is worse when the two hands' grasps overlap (G4-10).
5. **Handover force transfer has been controlled explicitly for parallel grippers under torsional load.** The giver
   releases at 0.3 N/s, monitors predicted slip, and aborts the release and asks the receiver to regrasp if slip is
   predicted (Costanzo et al., G4-16, FULL). This is the only robot-to-robot parallel-gripper handover with force
   traces found. It is one demonstrated run, with no success rate.
6. **Misalignment before a turn is treated as a precondition everywhere it is discussed.**
   - OpenAI aligns all faces to within 0.1 rad before a turn (S01).
   - Li et al. give their simulated cube a ~5° tolerance through chamfers (G4-20).
   - The quadruped cube work requires layers within ±5° after a flip (G4-21).
   - Hobby builds report that non-90° turns jam the next move (G4-27) and that whole-cube moves separate layers (G4-25).
   - The UIUC two-gripper rig says "a few millimetres of misalignment can turn the wrong layer" (G4-24).
7. **No source was found that simulates contact-driven layer turns plus handoffs between two parallel grippers.**
   - The public MuJoCo 3×3×3 model (G4-22) drives each face with an actuator on the centre hinge, which Rubiknetic
     forbids.
   - Published RL cube work uses dexterous hands or legs (S01, G4-19–G4-21).

   `INFERENCE`: G4 has no external simulation baseline for handoff success. Its numbers must come from its own
   pre-registered trials.
8. **Usable numbers are few and come from very different hardware** (§6). Examples:
   - about 1.7 manipulation motions per face turn for the PR2;
   - a median of 23 whole-cube rolls per solve (30 quarter turns) for a fixed two-gripper rig;
   - about 30 s per table-assisted regrasp for a dexterous hand;
   - about 21–23 s per rotation for the PR2 benchmark baselines;
   - 86 % solve success for a dual-arm humanoid (abstract only).

   None is a handoff success rate per handoff, and none comes from simulation with contact-driven turns.

## 2. Question 1: how two-arm/two-gripper cube robots access all six faces

### 2.1 Research systems with two arms
- **PR2, Yang, Lancaster, Smith (G4-01 FULL, G4-02 FULL, G4-03 FULL)**:
  - **Grasp split (`FACT`, G4-01):** "one of the grippers holds two rows of the cube stationary and the other rotates
    one face". "The cube holding gripper always constrains two layers of the cube and the manipulating gripper rotates
    only one layer." The rotating gripper has one allowed grasp point, "the mid-point of the face, which allows the
    face to rotate with a very simple wrist rotation". Each finger of the holding gripper has three feasible grasp
    points.
  - **Face access (`FACT`, G4-01):** "The front, back, and right faces can only be rotated when the left gripper is
    holding the cube. The up, down, and left faces can only be rotated when the right gripper is holding the cube."
    The cube "must be transferred from one gripper to another in order to rotate a certain face", and re-grasping can
    also be needed "to shift the grip position". After each rotation both grippers return to a home pose. The cube's
    orientation is kept consistent relative to the holding gripper. This "can be handled by a finite state machine".
  - **Cost (`FACT`, G4-01):** "Executing 20 cube rotations requires approximately 34 motions over a time period of 7
    to 8 minutes."
  - **Grasp space (`FACT`, G4-01):**
    - up to 120 single-hand grasps (6 headings × 2 wrist rolls × 10 grasp points);
    - at most 100 for the second hand;
    - so at most 12,000 two-handed grasps, fewer after kinematic and hand-collision constraints.
  - **Proposed future work (`FACT`, G4-01):** search the product of cube state and gripper state (heading, roll,
    grasp point, open/closed) to remove slow regrasps. The paper says "solving the Rubik's cube is the most complex,
    sequential task to which pre-touch sensing has ever been applied" (G4-02). The joint planner was proposed, not
    reported as built.
  - **Results (`FACT`, G4-02 Table I and §V-A):**
    - Ten scrambles needing 20–23 rotations.
    - Baseline (no pose re-estimation): 0/10 solved; maximum 17, minimum 3, mean 9.6 rotations completed.
    - With optical time-of-flight pre-touch scans before each re-grasp: 8/10 solved. The two failures stopped at
      14/21 and 19/20.
    - "All of the unsuccessful rotations occurred when the robot failed to re-grasp the cube; either as it tried to
      transfer the cube from one gripper to the other, or as it attempted to grasp the cube in order to rotate a face."
  - **Error margin (`FACT`, G4-02):** the finger width is about one cubie, so the margin "is approximately half the
    width of a sub-cube". More error can "unintentionally constrain one of the faces" or miss the grasp.
  - **Benchmark (G4-03, `FACT`):** later published as a benchmark protocol. Tiers Rubiks-M-N: M consecutive trials
    of N rotations, scored by time from first contact, with no human intervention.
    - Fingertip-aided baseline: Rubiks-1-100 in 2207.97 s; Rubiks-5-20 in 416.61 ± 23.10 s.
    - Dead reckoning: completed nothing above Rubiks-1-20 (463.45 s).
    - Under-constraint (a held layer turns) and over-constraint (the intended layer is blocked) are named as the two
      grasp failure classes.
- **Warsaw University of Technology two-arm system** (G4-04 FULL, G4-05 ABSTRACT):
  - **Hardware (`FACT`, G4-04 §4.3):** two modified 6-DOF IRp-6 arms. Each has a parallel-jaw gripper with tactile
    sensors in the jaws, a six-axis wrist F/T sensor and an eye-in-hand camera.
  - **Specialised jaws (`FACT`, G4-04 §4.1):** "The shape of each of the jaws of the gripper matches the form of the
    corner of the cube. The cube is being grasped diagonally in such a way that either one or two layers are
    immobilized". G4-02 describes these grippers as trough-shaped, grasping at the corners.
  - **Skills (`FACT`, G4-04):** Localize, Reach, Grasp, Turn, Release. Solving is "Grasp → Turn → Release performed
    n times", plus regrasps to inspect the initial state. Grasp feasibility is reduced to "the proper positioning of
    the grippers".
  - **Control (`FACT`, G4-04):** in the closed chain, "the two robot arms cannot be position controlled while
    executing the turns. This would cause excessive build-up of force in a rigid closed kinematic chain due to small
    misalignments". Turns use position-force control. While one arm catches the cube held by the other, the holder is
    position controlled and the catcher force-controlled. F/T plots show "a rapid change in torque … because initially
    the rotated face was jammed".
  - **Result (`FACT`, G4-05 abstract):** force sensing meant "jamming of the faces has always been avoided", but
    visual servoing "could only cope with slow handing over of the cube".
  - **Not available:** solve times and success rates were not found (closed access).
- **Dual-arm humanoid "Baymax"** (S30 / G4-07, ABSTRACT): HSV vision, Kociemba, "eighteen actions" executed with
  RRT-Connect, success rate 86 % (`FACT`, abstract). Grasp, regrasp and reorientation are not described in the
  abstract.
- **Song 2022, "Dual Arm Rubik's Cube Solver Robot"** (G4-08, ABSTRACT): reports solving "within 7 seconds" (`FACT`,
  abstract, paraphrased by the retrieval tool). The mechanism is not described.
  `INFERENCE`: a 7 s solve suggests a dedicated rig rather than general-purpose arms; not verified.
- **Gan et al. 2025, "A two-armed Rubik's Cube solver robot design and mechanical step optimization method"**
  (G4-09, META): only the title, authors and venue were confirmed. The title suggests the paper optimises mechanical
  steps for a two-arm rig. Content not read.

### 2.2 Documented hobby and student builds
- **UIUC ECE 445 dual-arm solver, spring 2026** (G4-24, FULL page; Huang, Xu, Wang, Shen):
  - **Mechanism (`FACT`):** two grippers fixed to a frame, each with a wrist stepper and a clamp stepper. The cube is
    held "corner-down", and each gripper "clamps the middle piece of one lower edge". The grippers "can reach only two
    of the cube's six layers".
  - **Face access (`FACT`):** whole-cube rolls, in which "one gripper holds and turns; the other opens, then
    re-clamps". The planner picks the arm needing fewer rolls.
  - **Counts and time (`FACT`):** median 23 rolls per solve, with a median of 21 Kociemba face turns and 30 quarter
    turns. About 2 min per real solve including scanning. 1000/1000 scrambles in a MuJoCo playback. The page does not
    say whether the simulated turns are contact-driven. The simulation "assumes each jaw lands on the centre of an
    edge piece".
  - **Real-rig limits (`FACT`):**
    - "a few millimetres of misalignment can turn the wrong layer";
    - "Stepper clamps slowly lose grip under load", so a re-clamp follows each return to dual hold;
    - no real-robot success rate is reported.
- **"The Mad Wrapper" two-gripper solver** (G4-25, FULL page; after a design by "KAS"; posted 2021, updated 2023)
  (`FACT`):
  - It can turn only the down and back faces directly. Other faces are reached by whole-cube rotations, e.g. "Y2, B,
    Y2" for a front turn.
  - About 60 moves per solve versus about 20 for a six-gripper design; 4–5 min per solve.
  - Failure: with loose speed cubes "the top of the cube will separate from the bottom" during whole-cube moves and
    jam the grippers.
- **Cornell ECE 5725, four claw arms** (G4-27, FULL page) (`FACT`):
  - No full solve was achieved.
  - Main cause: "mechanical slop (backlash)". Turns that are not exact multiples of 90° make the next move fail.
  - The open-loop steppers gave "no way of knowing the true position" of a face.

### 2.3 Other face-access strategies, for contrast
- **Dedicated face drives, excluded by Rubiknetic's no-hidden-face-motor rule.**
  - MIT (Katz/Di Carlo, 2018, G4-28, FULL page): six servo motors coupled to the centre caps, 0.38 s solve.
    The cube had to be tightened "well past what felt intuitive" so outer faces would not cam outward.
  - Mitsubishi Electric (2024, G4-29, FULL page): 0.305 s; the first official attempt failed when the cube jammed.
- **One hand plus the environment.**
  - Higo/Rigo et al. 2018 (S31, ABSTRACT): two regrasp primitives and one face-turn primitive on a plane, 30
    turn-and-regrasp operations in 10 s at 70 % success.
  - FINGR 2026 (G4-19, FULL): one dexterous hand on an xArm7, 2×2×2 cube. Nine of ten solves needed one
    table-assisted regrasp, at 29.98 ± 5.86 s each. 181/185 planned turns succeeded.
- **One hand, reorienting the cube in hand.**
  - OpenAI 2019 (S01, FULL on record): face rotations plus cube flips.
  - Li et al. 2019 (G4-20, FULL): rotate the whole cube so the target layer is on top, then apply only U′.
- **Legs** (Amiet et al. 2026, G4-21, FULL): flips, and "one foot pinning the cube as the other pushes".

`INFERENCE` (from §2): every system that uses general-purpose two-finger grippers reaches the six faces in one of two
ways:
- (a) handoffs between arms, with grasp shifts (PR2, Warsaw);
- (b) whole-cube rolls by one gripper while the other is open (UIUC, Mad Wrapper).

Specialised jaws (Warsaw corner troughs) reduce pose uncertainty but are still parallel jaws. No two-arm system was
found that avoids regrasping.

## 3. Question 2: regrasp and handoff planning for bimanual parallel-jaw manipulation

### 3.1 Formulations
- **Manipulation graph with transit and transfer motions** (Siméon et al. 2004, G4-17, ABSTRACT): `FACT`, a
  probabilistic-roadmap manipulation planner over continuous grasp and placement sets. It is the formal background of
  the transit/transfer vocabulary used below.
- **Wan & Harada 2016, single- vs dual-arm regrasp** (S37 upgraded to FULL here as G4-10):
  - **Graph (`FACT`):** nodes are grasps grouped by object state. Transit edges change grasp without moving the
    object. Transfer edges move the object with a fixed grasp.
  - **Dual arm (`FACT`):** two sub-graphs (master, slave) are bridged at a "handling configuration". Its position is
    chosen by manipulability and "approachability", and its rotation is sampled evenly. Hand–hand collisions and
    "hand directions that induce crossing arms" are removed. "Collision between master and slave arms need to be
    further checked before merging the two sub-graphs".
  - **Timing (`FACT`, kinematic simulation on HiroNX in Choreonoid):** IK and collision checking at the initial and
    goal placements took up to 10.02 s. A worst-case search over 352 rotations was estimated at 6 min, but no search
    exceeded 3 min.
  - **Conclusion (`FACT`):** dual-arm regrasp "has good performance in most cases" but is bad when "the grasps of the
    master hand at the initial placement overlap with the grasps of the slave hand at the goal placement, and the
    master hand and the slave hand collide during handling".
- **Wan & Harada 2017, regrasp with 10,000s of grasps** (G4-11, FULL via ar5iv):
  - **Method (`FACT`):** grasp databases plus regrasp roadmaps; single-arm experiments only. Collision checking is
    two-level: finger-pad swept volumes modelled as two cylinders, then the full hand.
  - **Results (`FACT`):** graph connection and search took 0.14–30.91 s per object. Regrasps needed: 0–3 per
    reorientation task.
- **Wan & Harada 2016, dual-arm handover success** (*Advanced Robotics* 30(17–18):1111–1125, G4-13, META): the title
  promises a "high success rate in dual-arm handover using large number of candidate grasps, handover heuristics, and
  hierarchical search".
  - The abstract was elided in the indexes reached. The full text was blocked (HTTP 403).
  - A search snippet says it handles "thousands of grasps within a few seconds" with simulation and real tests. That
    is SNIPPET only, and **no success-rate number is reported here**.
- **Vahrenkamp et al. 2009, humanoid dual-arm re-grasping** (G4-12, FULL):
  - **Validity (`FACT`):** a handoff configuration "is only valid if there are no collisions between the arms, the
    environment, the object and the robot". A collision-free trajectory must also exist to reach it.
  - **Planners (`FACT`):** IK-RRT, which samples dual-arm IK solutions while planning, and J+-RRT, which moves both
    end effectors towards each other by Jacobian steps.
  - **Mean planning times over 100 runs (`FACT`):** IK-RRT 278 ms without obstacles and 469 ms with them; J+-RRT
    1,662 ms and 5,192 ms.
  - **Kitchen task (`FACT`):** the re-grasp took 760.7 ms of IK solving plus 4,702 ms of motion planning.
- **Beretta 2023, polyhedral objects, YuMi with parallel jaws** (G4-14; FULL read of the executive summary only, not
  the thesis):
  - **Offline (`FACT`):** pairs of collision-free grasps are associated to handover states: "a collision check between
    the hands is conducted to assess whether the two grasps can be paired and executed simultaneously". Grasp quality
    is "determined with reference to the friction force".
  - **Online (`FACT`):** a directed weighted graph whose nodes are grasps and whose edges are regrasps, with weight
    max quality minus end-node quality. Dijkstra gives "a trade-off between grasp stability and number of regrasp".
    The handover pose is then chosen by maximising manipulability over translations and rotations between the arms.
  - **Execution (`FACT`):** as a finite state machine in RAPID or a ROS node.
- **Cruciani et al. 2019, Dexterous Manipulation Graph** (S38 upgraded to FULL here as G4-15):
  - **Method (`FACT`):** the second gripper acts as support while the first regrasps. Its grasp maximises distance
    from the first gripper's grasp lines. "Since large rotations could lead to collisions between the two grippers,
    they should be penalized."
  - **Results (`FACT`):** YuMi, three objects including a 50 × 50 × 40 mm block. Results are qualitative. The final
    orientation was "slightly rotated" from the target because the arm hid the object from the camera. No trial
    counts or success rates are given.
- **Nagahama, Wan, Hu, Harada 2025, bimanual regrasp to reduce pose uncertainty** (G4-18, FULL via arXiv HTML v4):
  - **Principle (`FACT`):** flat finger pads on a parallel gripper remove uncertainty along the closing direction.
    Three orthogonal grasps can constrain the object's pose uniquely.
  - **Method (`FACT`):** two UR3e arms with Robotiq Hand-E grippers and wrist F/T sensors. A handover-style regrasp
    sequence is executed with admittance control, target external force "essentially zero".
  - **Results (`FACT`):** six runs on two L-shaped objects. Position spread was below 2 mm SD relative to optical
    tracking, with systematic offsets. No success rate is given.
- **Integrated TAMP survey** (Garrett et al. 2021, G4-23, ABSTRACT): `FACT`, a taxonomy of how TAMP methods handle
  continuous subproblems and how they combine the discrete and continuous parts of the search. Background only.
- **Bimanual taxonomy** (Krebs & Asfour 2022, S39, ABSTRACT on record): vocabulary for symmetric and asymmetric
  roles.

### 3.2 Grasp stability and drop risk during handoff
- **Costanzo, De Maria, Natale 2021** (G4-16, FULL apart from the last 11.6k characters of the page):
  - **Setup (`FACT`):** human-to-robot, robot-to-human and robot-to-robot handovers with parallel grippers and
    fingertip 6-D wrench sensors. A KUKA iiwa with a WSG-50 gripper and a Yaskawa SIA5F with a WSG-32.
  - **Release logic (`FACT`):**
    - The giver ramps its grip-force setpoint to zero "with a rate of 0.3 N/s".
    - It watches a "virtual" slip from an observer with a reduced friction coefficient, so slip is predicted before
      it happens.
    - On predicted slip it "aborts the opening" and returns to slipping-avoidance grip. It then cues the receiver,
      which regrasps 2.5 cm closer to the centre of gravity.
  - **Robot-to-robot run (`FACT`):** an 82 g box, giver at 11 N during lift, receiver up to 12.5 N. The transfer,
    including one aborted release and the regrasp, spanned about t = 18–58 s.
  - **Limits stated (`FACT`):** with parallel grippers, a grasp "too far from the center of gravity" may need more
    grip force than the gripper can give. The authors claim novelty for "handover of objects subject to torsional
    load".
  - **Missing (`FACT`):** no success rate or trial count.
- **Wan & Harada 2016** (G4-10): failure from overlapping grasps and hand collision during handling (§3.1).
- **Yang et al. 2017** (G4-02): every failure was at a regrasp (§2.1).
- **UIUC rig** (G4-24): clamps lose grip under load; re-clamp after each return to dual hold.

### 3.3 Which methods suit a small cube held by two parallel grippers (`INFERENCE`)
- **The cube's grasp set is small and discrete.** G4-01 counts at most 120 × 100 two-hand grasps on a PR2 grid.
  This favours **precomputed tables plus graph search** (G4-01's proposal, G4-14's grasp-pair table, G4-10's
  handling-configuration bridge). Sampling-based TAMP over continuous grasps (G4-17, G4-23) is more than the problem
  needs.
- **The planning state must include gripper state.** Cube moves alone are not enough (G4-01). The state is
  (cube orientation in the world, which arm holds which layers, grasp point, wrist roll, open/closed).
- **Collision checking needs two levels.** First the finger-pad swept volumes, then the full gripper and arm (G4-11),
  with explicit arm–arm checks at the handoff pose (G4-10, G4-12).
- **The kinematic planners do not answer whether the cube stays aligned and held during the handoff.** For that, the
  force-aware literature applies:
  - force or compliance on the receiving arm while the holder stays fixed (G4-04);
  - a controlled release by the giver with slip monitoring (G4-16);
  - pose re-estimation before each regrasp (G4-02);
  - flat-pad closure as a passive way to re-centre the cube (G4-18).

## 4. Question 3: physically simulated, contact-driven cube manipulation

- **OpenAI 2019** (S01, FULL on record; not re-read today):
  - **Model (`FACT`):** a MuJoCo cube of 26 cubelets with hinges and no custom physics. Turns come from contact and
    friction.
  - **Alignment (`FACT`):** a turn is attempted only when all faces are within 0.1 rad of a straight angle;
    otherwise the goal is to align first. On the real robot it "first aligns faces after performing a flip".
- **Li et al. 2019** (G4-20, FULL):
  - **Model (`FACT`):** a MuJoCo 2×2×2 cube with a simulated Shadow hand. Eight 2.5 cm cubelets "connected by a ball
    joint located at the cube center". Circular chamfers give "an angle tolerance around 5°".
  - **Primitives (`FACT`):** whole-cube rotation, 95.2 % success over 1,000 tests; the single primitive U′, 92.3 %.
    The full task reached 90.3 %, using a "rollback mechanism".
  - **Rollback (`FACT`):** if cubelets are not aligned after a layer move, "we first restore it into a good state by
    applying randomization". The paper does not say clearly whether this is a physical action or a state reset.
    `INFERENCE`: it should not be read as a precedent for recovery without a reset.
- **Amiet et al. 2026, quadruped and giant cube** (G4-21, FULL):
  - **Model (`FACT`):** Isaac Lab, physics at 200 Hz. A "simplified" cube of three layers "connected by two passive
    revolute joints" about one axis. Static and dynamic friction torques of 6.0 and 4.0 N·m were measured with a
    spring scale.
  - **Failure and recovery (`FACT`):**
    - Flips must land with "all layers aligned within ±5°".
    - Residual misalignment "was usually corrected when the cube landed from the next flip".
    - Failures were mostly over-rotation (hardware: rotate CCW 13/15, CW 10/15).
    - A blocked flip gets two to three more attempts.
- **Zakka's `mujoco_cube` 3×3×3 model** (G4-22, FULL: README and model XML; Apache-2.0) (`FACT`):
  - Centre bodies have hinge joints, each driven by a `general` actuator ("red" … "yellow").
  - The default cubelet joint is `type="ball"`.
  - Cubelets are 1.9 cm with 1.425 mm chamfers.

  `INFERENCE`: the face actuators are hidden face motors under CLAUDE.md, so this model is not usable for Rubiknetic
  as is. It is listed because it is the obvious public candidate.
- **FINGR 2026** (G4-19, FULL) (`FACT`):
  - All evaluation is on real hardware; no simulator was used for experiments.
  - Misalignment is handled by re-observing and an explicit "alignment motion", with four corrections over ten
    solves taking 0.70–3.20 s.
  - Failures were state mismatches, resolved by re-observation and replanning.
- **Real two-arm systems** (§2):
  - jamming was avoided by force control (G4-04, G4-05);
  - under- and over-constraint come from pose error of more than about half a cubie (G4-02, G4-03);
  - misalignment "can turn the wrong layer" (G4-24);
  - non-90° turns jam the next move (G4-27).
- **Not found:** a physically simulated (non-kinematic) 3×3×3 cube manipulated by two parallel-jaw grippers, with or
  without handoffs (§8).

`INFERENCE`: the literature treats alignment as a precondition checked before each turn, with a tolerance of about
5–6°. Recovery is either an explicit alignment action or a retry. Rubiknetic's G2 already measures per-cubie
misalignment at t0 and per move. G4 adds handoffs and reorientations, which none of these sources measured for their
effect on layer alignment.

## 5. Cube-solving robots found

| ID | System | Mechanism | How faces are reached | Regrasps / reorientations | Reported performance | Verification |
|---|---|---|---|---|---|---|
| G4-01/02/03 | PR2 (Yang, Lancaster, Smith; Srinivasa) 2016/17/20 | Two 7-DOF arms, stock parallel jaws plus optical proximity fingertips | One holds 2 layers; other grips face mid-point and rolls wrist; handoff between arms plus grasp shifts; F/B/R only while left holds, U/D/L only while right holds | ~34 motions per 20 rotations | 8/10 solves (20–23 rotations) with pre-touch, 0/10 without (mean 9.6 rotations); 7–8 min per 20 rotations; benchmark ~21–23 s per rotation (derived) | FULL |
| G4-04/05 | Warsaw IRp-6 pair (Zieliński, Szynkiewicz et al.) 2007/2012 | Two 6-DOF arms; parallel jaws shaped to cube corners; wrist F/T, tactile, eye-in-hand | Diagonal grasp immobilising 1 or 2 layers; Grasp→Turn→Release; handing over between arms | Not stated | Jamming "always" avoided by force control; handovers slow (vision-limited); no rates found | FULL (2012) / ABSTRACT (2007) |
| S30 / G4-07 | "Baymax" dual-arm humanoid (Chen et al.) 2023 | Dual-arm humanoid; grippers not described | 18 predefined actions via RRT-Connect | Not stated | 86 % success | ABSTRACT |
| G4-08 | Song 2022 | Dual arm; not described | Not described | Not stated | Solve within 7 s | ABSTRACT |
| G4-09 | Gan et al. 2025 | Two-armed; not read | Not read | Title mentions "mechanical step optimization" | Not read | META |
| G4-24 | UIUC ECE 445 dual-arm rig, 2026 | Two frame-fixed grippers, wrist and clamp steppers | Cube corner-down; each jaw on a lower edge piece; whole-cube rolls (one holds and turns, other re-clamps) | Median 23 rolls per solve (30 quarter turns) | ~2 min per real solve; 1000/1000 in MuJoCo playback (physics of turns unstated); no real success rate | FULL (page) |
| G4-25 | Mad Wrapper / KAS two-gripper design, 2021–23 | Two servo grippers | Only D and B turnable; whole-cube Y/Z rotations | ~60 moves vs ~20 face turns | 4–5 min; no rate | FULL (page) |
| G4-27 | Cornell ECE 5725 | Four claw arms (stepper plus solenoid) | Claw per face | None | 0 full solves (backlash, off-90° jams) | FULL (page) |
| S31 | Higo/Rigo et al. 2018 | High-speed 3-finger hand, cube on a plane | 2 regrasp types plus 1 turn type | 1 regrasp per turn cycle | 30 turn+regrasp in 10 s, 70 % | ABSTRACT |
| G4-19 | FINGR 2026 (2×2×2) | Dexterous hand on xArm7 | U/L turns in grasp; table-assisted regrasp | 1 regrasp in 9/10 solves; 29.98 ± 5.86 s each | 10/10 solves; 181/185 turns | FULL |
| S01 | OpenAI 2019 | Shadow hand | Flips plus face turns | Flips per Kociemba sequence | 60 % half / 20 % full scramble (N = 10) | FULL (on record) |
| G4-20 | Li et al. 2019 (2×2×2, simulation) | Simulated Shadow hand | Whole-cube rotation to bring layer on top, then U′ | 1 rotation per move | 90.3 % (simulation) | FULL |
| G4-21 | Amiet et al. 2026 (giant cube) | Quadruped legs | Flips, repositioning, pin-and-push turns | ~30 steps per solve | 3 hardware solves, 8–9 min | FULL |
| G4-28/29 | MIT 2018; Mitsubishi 2024 | Six motors on centre caps | Direct face drive | None | 0.38 s; 0.305 s | FULL (pages) |

## 6. Question 4: quantitative values usable for G4 (all `FACT` as reported; each comes from different hardware)

| Quantity | Value | Source | Caveat |
|---|---|---|---|
| Manipulation motions per face turn, two-arm parallel jaws | ~34 motions / 20 rotations ≈ 1.7 | G4-01 | FSM with home pose after every turn |
| Whole-cube rolls per solve, two fixed grippers | median 23 (30 quarter turns, 21 face turns) | G4-24 | Rolling, not handoff |
| Moves per solve with two grippers vs six | ~60 vs ~20 | G4-25 | Hobby estimate |
| Time per rotation incl. regrasps | ~21–23 s (derived from Table I) | G4-03 | PR2, not optimised |
| Time per regrasp (table-assisted, dexterous hand) | 29.98 ± 5.86 s | G4-19 | Includes placing on the table |
| Regrasp success: solves with pose re-estimation vs none | 8/10 vs 0/10; all failures at regrasp | G4-02 | N = 10 each |
| Pose-error tolerance for a turn grasp | ≈ half a cubie (~9.5 mm for a 19 mm cubie) | G4-02, G4-03 | Finger width ≈ one cubie |
| Layer-angle precondition before a turn | 0.1 rad (S01); ~5° (G4-20); ±5° after a flip (G4-21) | | Different cubes |
| Handoff planning time (dual-arm IK-RRT) | 278 ms / 469 ms (without / with obstacles) | G4-12 | 2009 hardware |
| Giver release rate in a robot-to-robot handover | 0.3 N/s, with slip-predicted abort | G4-16 | One run, 82 g box |
| Hold force in a robot-to-robot handover | giver 11 N, receiver up to 12.5 N | G4-16 | Different grippers |
| Turn + regrasp cycle, high-speed hand | 30 in 10 s at 70 % | S31 | Cube on a plane |
| Solve success, dual-arm humanoid | 86 % | S30 | Abstract only |

**Not found:** a per-handoff success rate for a cube, a typical gripper-to-gripper clearance at the handoff in mm, or
any handoff number from simulation with contact-driven turns.

## 7. Implications for Rubiknetic G4 (`INFERENCE` and `PROPOSAL`, clearly labelled)

1. **`INFERENCE`:** the G2 setup is functionally the PR2 and Warsaw split. In G2, arm A holds D and E from the side
   and arm B grips U and rolls J7. There is therefore direct precedent that two parallel grippers can reach all six
   faces through handoffs and grasp shifts, with a fixed rule set per holding arm. The precedent is real-robot and
   kinematically planned, not a physics-simulation result.
2. **`PROPOSAL`: start G4 with a finite-state, table-driven planner, as G4-01 did, before a general graph search.**
   - State: (cube orientation in the world; which arm holds which two layers; which arm grips which face; wrist roll;
     open/closed).
   - Transitions: turn, handoff, and grasp shift, each a precomputed, collision-checked and IK-checked entry (G4-14
     pairing, G4-10 handling configuration, G4-11 two-level collision).
   - This gives the "manipulation-aware plan graph" of Phase 4 task 3 with checkable preconditions. Phase 4 task 7
     (naive vs cost-aware) can then be a Dijkstra search over the same table with handoff cost weights (G4-14), against
     a fixed-rule baseline.
3. **`PROPOSAL`: score each handoff as a separate pre-registered event, not only whole solves.**
   - G4-02's only failure mode was the regrasp.
   - Per-handoff metrics, measured on the audit channel: cube pose change in the receiving gripper frame; per-face
     misalignment before and after; core and layer rotation during the handoff; contact loss (both grasps released at
     once = unsupported, which Phase 4 task 5 forbids unless deliberately tested).
4. **`INFERENCE`:** Rubiknetic needs its own pose tolerance; G4-02's half-cubie margin should not be imported. That
   margin follows from PR2 finger width ≈ one cubie. Rubiknetic's margins follow from its pads:
   - arm A: 30 mm pads over D and 11 mm of E;
   - arm B: C1 pads 25 × 14 mm, distal end 14 mm inside U;
   - 19 mm layers.

   **`PROPOSAL`:** derive the axial over- and under-constraint margins for each grasp from that geometry, with a small
   falsifiable test (offset sweep) before the handoff design is frozen.
5. **`PROPOSAL`: a handoff protocol with an always-supported overlap** (Phase 4 task 5):
   - (i) the receiver approaches under Cartesian impedance (as arm B already does) while the giver holds a position
     (G4-04 pattern);
   - (ii) the receiver closes to full grip;
   - (iii) a dwell, with both grasps closed and the F/T reading steady;
   - (iv) the giver opens with a ramped force (G4-16 uses 0.3 N/s);
   - (v) an abort rule: if the receiver's wrist F/T or J7 error shows slip or torque above a bound during (iv), the
     giver re-closes.

   Caveat: the F/T sensor exists only on arm B (P-114). Whether arm A needs one for symmetric role swaps is a user
   decision, flagged here and not assumed.
6. **`INFERENCE`: handoffs and whole-cube reorientations can disturb layer alignment** (G4-25 separation in
   whole-cube moves; G4-24 misalignment turning the wrong layer). A parallel-jaw closure across a layer boundary may
   push a misaligned layer flat or may wedge it. Which happens in the M7 model is **unknown and must be measured**.
   **`PROPOSAL`:** a small feasibility experiment.
   - Do: one handoff at several seeded start misalignments (as in G2's ±1°), with no turn.
   - Record: per-face misalignment and core rotation before and after.
   - Purpose: decide whether G4 needs an explicit `verify_alignment` or "re-squeeze" precondition (as S01 and G4-19
     use) before each turn.
7. **`INFERENCE`: pose re-centring.** Flat pads re-centre the cube along their closing axis (G4-18). Successive
   orthogonal grasps by the two arms may therefore bound cube-in-gripper drift without perception, which G4-02 needed
   pre-touch sensing to achieve.

   **`PROPOSAL`:** measure drift over many handoffs on the audit channel before adding any runtime estimator. Runtime
   control must still not read cube state (G2 §2 rule; architecture data channels).
8. **`INFERENCE`: a planning cost needs an estimate.** Two-gripper systems need roughly 1–2 extra manipulation actions
   per face turn (G4-01: ~1.7; G4-24: 23 rolls / 30 quarter turns). A 20-move solve might therefore take on the order
   of 20–40 handoffs or grasp shifts. With a zero-tolerance gate, even a small per-handoff failure rate compounds.
   Example: 99 % per handoff gives about 0.99^30 ≈ 74 % for 30 handoffs (arithmetic). G4 should report per-event
   rates with confidence intervals, not only whole-sequence pass/fail.
9. **`INFERENCE`: there is no external simulation baseline.** No source simulated contact-driven turns with two
   parallel grippers and handoffs, and the public MuJoCo cube uses face actuators (G4-22). Claims of novelty for this
   specific combination would need a broader search than this one (see §9).

## 8. Searches that came up empty or were blocked
- A paper on a 2023–2026 **bimanual** (two-hand or two-arm) **physically simulated** 3×3×3 cube with contact-driven
  turns: none found (several queries, standard and extended).
- **Per-handoff success rates** for robot-to-robot cube handovers: none found. The closest are Costanzo et al. (one run)
  and G4-13 (title only).
- **ABB YuMi Rubik's cube demo**: a search result described an ABB downloads-page listing for a RobotStudio demo kit.
  The page was **not opened**; not cited.
- **RLE-Bench**: a search snippet mentioned two Panda grippers exchanging a 2×2×2 cube. The arXiv abstract page
  (opened: https://arxiv.org/abs/2609.34210) does not mention it. **UNVERIFIED**; not used.
- **Speedsolving forum thread and robot list wiki**: HTTP 403 on
  https://www.speedsolving.com/threads/robot-solving-the-cube-with-two-hands.96823/ and
  https://www.speedsolving.com/wiki/index.php/List_of_cube_solving_robots; not used.
- **Saut et al. IROS 2010** (two-hand regrasping): https://hal.laas.fr/hal-01986173 failed DNS resolution, so only
  search snippets were seen. **SNIPPET only**; not used for any claim.
- **Wan & Harada, *Advanced Robotics* 2016**: publisher page https://www.tandfonline.com/doi/abs/10.1080/01691864.2016.1202138
  returned HTTP 403; abstract elided in Semantic Scholar (G4-13, META).
- **Gan et al. SPIE 2025** and **Song IAECST 2022**: the publisher pages
  (https://www.spiedigitallibrary.org/conference-proceedings-of-spie/13735/3082082/A-two-armed-Rubiks-Cube-solver-robot-design-and-mechanical/10.1117/12.3082082.full,
  https://ieeexplore.ieee.org/document/10062245/) returned no content; metadata or abstract only (G4-08, G4-09).
- **`pr2_rubiks_solver`** (Riano 2011, cited by G4-02 as a PR2 system that solved a six-rotation puzzle): the GitHub
  page https://github.com/uu-isrc-robotics/pr2_rubiks_solver has no README text; not used beyond G4-02's description.
- **`CuBiC`** (https://github.com/EightEggs/CuBiC, GPL-3.0, "two mechanical arms"): the README has no mechanism or
  performance details; not used.
- **Warsaw technical report** ("MRROC++ based controller of a dual arm robot system manipulating a Rubik's cube",
  2007): seen only as a search result and as reference [20] in G4-02; not opened, not cited.
- **Otvinta four-arm build**: search results only, no page opened; no performance numbers found.

## 9. Limits
- **Mostly real-robot sources.** Most sources are real-robot systems with kinematic planning. Their numbers come from
  different grippers, cubes, sensors and controllers, and none is a prediction for the MuJoCo M7 scene.
- **Single-sample PDF reads.** PDFs were read by local text extraction. Tables and figures (e.g. Wan & Harada Fig. 10
  success rates per placement, Yang 2017 Fig. 4 box plots) could not be read as numbers, so only values stated in the
  text are used.
- **Tool-summarised pages.** Several web pages and arXiv HTML pages were read through a summarising fetch tool. Exact
  quotes are given where the tool returned them. Numbers were cross-checked against a second fetch where they drive a
  conclusion (G4-24, G4-16).
- **Abstract-only sources.** Abstract-only items (S30, S31, G4-05, G4-07, G4-08, G4-17, G4-23) are used only for what
  their abstracts say. G4-09 and G4-13 are metadata only.
- **Single search engine.** The search used one web search engine, with no Google Scholar, IEEE Xplore full text or
  CNKI access. Chinese- and Japanese-language cube-robot literature is under-represented.
- **Derived values.** "Per rotation" times for G4-03 and the 0.99^30 example are arithmetic by this report, not
  values from the sources.

## 10. Source register (all accessed 2026-11-28)

"Opened" lists the exact URLs fetched for this report. A DOI is given only where it was confirmed in an opened record
(Crossref, Semantic Scholar or the full text). PDFs fetched from an "Opened" URL were read by local `pdftotext`.

| ID | Citation | Opened (exact URLs) / DOI | Level | What it establishes |
|---|---|---|---|---|
| G4-01 | B. Yang, P. Lancaster, J. R. Smith, "Prospects for Combining Task and Motion Planning for Bi-Manual Solution of the Rubik's Cube", RSS 2016 workshop abstract | https://kavrakilab.org/2016-rss-workshop/abstracts/yang.pdf | FULL | PR2 holder-2-layers / turner-1-layer split; per-arm face rules; FSM; 20 rotations ≈ 34 motions, 7–8 min; ≤12,000 two-hand grasps; proposed joint cube-gripper state search |
| G4-02 | B. Yang, P. Lancaster, J. R. Smith, "Pre-touch Sensing for Sequential Manipulation", ICRA 2017, pp. 5088–5095 | https://sensorfiles.cs.washington.edu/pubs/robotics/pre-touch-seq_manip.pdf | FULL | 8/10 vs 0/10 solves; all failures at regrasp; half-cubie margin; Warsaw grippers trough-shaped |
| G4-03 | B. Yang, P. E. Lancaster, S. S. Srinivasa, J. R. Smith, "Benchmarking Robot Manipulation with the Rubik's Cube", IEEE RA-L 5(2):2094–2099, 2020 | https://arxiv.org/abs/2202.07074 ; https://ar5iv.labs.arxiv.org/html/2202.07074 | FULL | Rubiks-M-N protocol; PR2 tier times; under/over-constraint failure classes |
| G4-04 | W. Szynkiewicz, "Skill-Based Bimanual Manipulation Planning", J. Telecommun. Inf. Technol. 2012(4):54–62 | https://jtit.pl/jtit/article/view/1292/1278 (PDF) ; DOI 10.26636/jtit.2012.4.1292 confirmed in https://api.crossref.org/works?query.bibliographic=Skill-Based+Bimanual+Manipulation+Planning+Szynkiewicz&rows=3&select=DOI,title,author,container-title,published,volume,issue,page | FULL | IRp-6 pair, corner-shaped jaws, 1- or 2-layer grasps; skills; position-force control in the closed chain; jammed-face torque spike |
| G4-05 | C. Zieliński, W. Szynkiewicz, T. Winiarski, M. Staniak, W. Czajewski, T. Kornuta, "Rubik's cube as a benchmark validating MRROC++…", Industrial Robot 34(5):368–375, 2007 | DOI 10.1108/01439910710774377 ; https://api.crossref.org/works/10.1108%2F01439910710774377 (abstract) ; https://api.semanticscholar.org/graph/v1/paper/5c8055b44c7dd2b7e725e7f11143bafed5b20ca4?fields=title,authors,year,abstract,venue,externalIds,openAccessPdf (metadata) | ABSTRACT (Crossref) | Two arms with force control and visual servoing; jamming always avoided; slow vision-limited handovers |
| G4-07 (=S30) | Z. Chen, X. Yuan, Q. Gu, D. He, "Design and Implementation of Dual-Arm Robot Rubik's Cube Solving System", CCDC 2023 | DOI 10.1109/CCDC58219.2023.10326999 ; https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/CCDC58219.2023.10326999?fields=title,authors,year,abstract,venue (abstract) ; https://api.crossref.org/works?query.bibliographic=Dual+Arm+Rubik%27s+Cube+Solver+Robot&rows=5&select=DOI,title,author,container-title,published (metadata) ; see also register entry S30 in `PHASE_0_SOURCE_REGISTER.md` | ABSTRACT | 18 actions via RRT-Connect; 86 % |
| G4-08 | C. Song, "Dual Arm Rubik's Cube Solver Robot", IAECST 2022, pp. 1545–1549 | DOI 10.1109/IAECST57965.2022.10062245 ; https://api.crossref.org/works/10.1109/iaecst57965.2022.10062245 (metadata) ; https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/IAECST57965.2022.10062245?fields=title,authors,year,abstract,venue,tldr (abstract) | ABSTRACT | Solve within 7 s; mechanism not described |
| G4-09 | W. Gan, B. Ma, Y. Yang, C. Li, L. Fang, "A two-armed Rubik's Cube solver robot design and mechanical step optimization method", ISCER 2025 (SPIE) | DOI 10.1117/12.3082082 ; https://api.crossref.org/works/10.1117/12.3082082 (metadata) | META | Existence only |
| G4-10 (=S37) | W. Wan, K. Harada, "Developing and Comparing Single-arm and Dual-arm Regrasp", IEEE RA-L 1(1):243–250, 2016 | https://arxiv.org/pdf/1509.02302 (arXiv v1 full text) ; journal DOI per register entry S37 in `PHASE_0_SOURCE_REGISTER.md` (not re-opened) | FULL | Regrasp graph; handling configuration; arm–arm checks; overlap makes dual-arm regrasp bad; planning times |
| G4-11 | W. Wan, K. Harada, "Regrasp Planning using 10,000s of Grasps", IROS 2017 | https://ar5iv.labs.arxiv.org/html/1705.09400 | FULL | Grasp DB plus roadmap; two-level swept-volume collision check; 0–3 regrasps; search times |
| G4-12 | N. Vahrenkamp, D. Berenson, T. Asfour, J. Kuffner, R. Dillmann, "Humanoid Motion Planning for Dual-Arm Manipulation and Re-Grasping Tasks", IROS 2009, pp. 2464–2470 | https://simox.sourceforge.net/articles/iros09_vahrenkamp.pdf (DOI not opened) | FULL | Handoff validity conditions; IK-RRT / J+-RRT; planning times |
| G4-13 | W. Wan, K. Harada, "Achieving high success rate in dual-arm handover using large number of candidate grasps, handover heuristics, and hierarchical search", Advanced Robotics 30(17–18):1111–1125, 2016 | DOI 10.1080/01691864.2016.1202138 ; https://api.semanticscholar.org/graph/v1/paper/DOI:10.1080/01691864.2016.1202138?fields=title,authors,year,abstract,venue (metadata; abstract elided) ; publisher page HTTP 403 | META | Existence only; no rate available |
| G4-14 | L. Beretta, "Object grasp and manipulation planning with a dual arm robot", MSc executive summary, Politecnico di Milano, 2023 | https://www.politesi.polimi.it/retrieve/725b0524-cce6-4b0a-8819-f7131bbfc38f/2023_12_Beretta_Executive_Summary_02.pdf | FULL (summary only) | Offline collision-free grasp-pair table; Dijkstra quality-vs-regrasp trade-off; manipulability handover pose; FSM execution on YuMi |
| G4-15 (=S38) | S. Cruciani, K. Hang, C. Smith, D. Kragic, "Dual-Arm In-Hand Manipulation and Regrasping Using Dexterous Manipulation Graphs", 2019 | https://arxiv.org/html/1904.11382v2 (read in two parts) | FULL | Support-gripper regrasp; gripper-collision penalty; qualitative YuMi results |
| G4-16 | M. Costanzo, G. De Maria, C. Natale, "Handover Control for Human-Robot and Robot-Robot Collaboration", Front. Robot. AI 8:672995, 2021 | https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2021.672995/full ; DOI 10.3389/frobt.2021.672995 (stated on that page) | FULL (last 11.6k chars unread) | Parallel-gripper R2R handover; 0.3 N/s release; virtual-slip abort and regrasp; 11 / 12.5 N; torsional load |
| G4-17 | T. Siméon, J.-P. Laumond, J. Cortés, A. Sahbani, "Manipulation Planning with Probabilistic Roadmaps", IJRR 23(7–8):729–746, 2004 | DOI 10.1177/0278364904045471 ; https://api.crossref.org/works?query.bibliographic=Manipulation+planning+with+probabilistic+roadmaps+Simeon+Laumond&rows=2&select=DOI,title,author,container-title,published,volume,issue,page,abstract | ABSTRACT (Crossref) | Manipulation-graph planning over continuous grasps |
| G4-18 | R. Nagahama, W. Wan, Z. Hu, K. Harada, "Bimanual Regrasp Planning and Control for Active Reduction of Object Pose Uncertainty", 2025 | https://arxiv.org/abs/2503.22240 ; https://arxiv.org/html/2503.22240v4 | FULL | Flat pads constrain pose along closing axis; three orthogonal grasps; admittance-controlled bimanual regrasp; UR3e + Hand-E |
| G4-19 | Y. Liang, Q. Peng, M. Kim, X. Wang, "FINGR: Learning Dexterous Hand Control for Real-World Rubik's Cube Solving", 2026 | https://arxiv.org/abs/2609.33973 ; https://arxiv.org/html/2609.33973 | FULL | Table-assisted regrasp 29.98 s; alignment corrections; 181/185 turns; real hardware only |
| G4-20 | T. Li, W. Xi, M. Fang, J. Xu, M. Q.-H. Meng, "Learning to Solve a Rubik's Cube with a Dexterous Hand", 2019 | https://arxiv.org/abs/1907.11388 ; https://ar5iv.labs.arxiv.org/html/1907.11388 ; https://arxiv.org/pdf/1907.11388 | FULL | MuJoCo 2×2×2 with ball joint; ~5° chamfer tolerance; rotate-then-U′; 90.3 %; rollback "by applying randomization" |
| G4-21 | L. Amiet, G. Sánchez-Blanco Repgen, M. Mittal, V. Klemm, A. Cramariuc, M. Hutter, C. Cadena, "Solving a Giant Rubik's Cube with a Quadruped Robot", 2026 | https://arxiv.org/abs/2610.24610 ; https://arxiv.org/html/2610.24610 | FULL | Isaac Lab 2-revolute-joint cube; ±5° flip criterion; misalignment corrected by later flips; skill success rates |
| G4-22 | K. Zakka, `mujoco_cube` (GitHub, Apache-2.0) | https://github.com/kevinzakka/mujoco_cube ; https://raw.githubusercontent.com/kevinzakka/mujoco_cube/main/cube_3x3x3.xml (read in two parts) | FULL (README + XML) | Centre hinges driven by six `general` actuators; ball-jointed cubelets |
| G4-23 | C. R. Garrett et al., "Integrated Task and Motion Planning", Annu. Rev. Control Robot. Auton. Syst. 4, 2021 | https://arxiv.org/abs/2010.01083 | ABSTRACT | TAMP taxonomy (background) |
| G4-24 | Q. Huang, Y. Xu, R. Wang, Z. Shen, "Dual-Arm Robotic Rubik's Cube Solver" (UIUC ECE 445, spring 2026) | https://dualarm-cube.github.io/ (opened twice) | FULL (page) | Rolls; median 23 per solve; ~2 min; misalignment and grip-loss notes; licence not stated |
| G4-25 | "The Mad Wrapper", Rubik's cube robot (2021, updated 2023) | https://madwrapper.com/rubiks-cube/ | FULL (page) | Two grippers turn D and B only; ~60 moves; 4–5 min; layer separation jams |
| G4-27 | E. Berg, Y. Hao, "Robotic Rubik's Cube Solver", Cornell ECE 5725 | https://courses.ece.cornell.edu/ece5990/ECE5725_Fall2018_Projects/eb645_yh326_final/index.html | FULL (page) | 0 solves; backlash; off-90° jams |
| G4-28 | B. Katz, "The Rubik's Contraption" (blog, 2018-03-07) | https://build-its-inprogress.blogspot.com/2018/03/the-rubiks-contraption.html | FULL (page) | Six centre-cap motors; 0.38 s; cube camming when loose |
| G4-29 | Guinness World Records, "Japanese company's robot solves a puzzle cube in 0.305 seconds" (2024-05-23) | https://www.guinnessworldrecords.com/news/commercial/2024/5/japanese-companys-robot-solves-a-puzzle-cube-in-0-305-seconds-to-break-record | FULL (page) | 0.305 s; first attempt jammed |
| S01 | OpenAI et al., "Solving Rubik's Cube with a Robot Hand", 2019 | Not re-read today; see register entry S01 in `docs/research/PHASE_0_SOURCE_REGISTER.md` (arXiv:1910.07113, https://arxiv.org/abs/1910.07113) | as recorded there | Alignment precondition; flips plus face turns |
| S31 | R. Higo (Crossref) / Rigo (Semantic Scholar), Y. Yamakawa, T. Senoo, M. Ishikawa, IROS 2018 | DOI 10.1109/IROS.2018.8593538 ; abstract re-read today at https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/IROS.2018.8593538?fields=title,authors,year,abstract,venue ; see register entry S31 | ABSTRACT | 2 regrasp + 1 turn primitive; 30 in 10 s at 70 % |
| S39 | F. Krebs, T. Asfour, "A Bimanual Manipulation Taxonomy", IEEE RA-L 2022 | Not re-read today; see register entry S39 in `docs/research/PHASE_0_SOURCE_REGISTER.md` | as recorded there | Role vocabulary |

(G4-06 and G4-26 are unused. G4-06 was removed because its page was never opened; see §8.)
