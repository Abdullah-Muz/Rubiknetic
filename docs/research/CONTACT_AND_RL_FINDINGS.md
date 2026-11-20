# Contact Modelling, Classical Controller and Residual RL: Findings

**Date:** 2026-11-19 · **Status:** literature review only. Nothing here is a `VALIDATED_RESULT`, and no experiment was
run. It closes the deliverable that P-06 had deferred to before Phase 3; it was done early, under the user's
delegation of 2026-11-19 (P-63, P-64). It should be re-checked for newer work when Phase 3 starts.

**How it was made.** Two web searches ran as subagents under P-20, one on contact modelling and the classical
controller and one on residual RL and CPU feasibility. The main session then checked four sources on their primary
pages: the MuJoCo 4.0.1 modelling guide (S13), UFACTORY's servo-mode guide (C01), and the abstracts of L04 and L11.
All four matched the reports. **Every other entry is as the subagents reported it**, with the verification level they
gave (§7). Quotations from sources marked "via summary" should be re-opened before being quoted elsewhere.

**Scope.** What each source establishes is stated for its own task and hardware. **Nothing is generalised to cube
turning.** Tags: `FACT` (in a source, at the stated verification level), `INFERENCE`, `PROPOSAL`.

Source IDs: S-numbers are in [`PHASE_0_SOURCE_REGISTER.md`](PHASE_0_SOURCE_REGISTER.md); C- and L-numbers are new and
listed in §7.

## 1. What matters most for this project
1. **The real xArm has no torque command mode** (`FACT`, C01–C03; C01 checked by the main session). It accepts
   position or velocity setpoints at up to 250 Hz, unbuffered. So a real "impedance" baseline is an admittance loop
   around the position servo, not a torque-level impedance law (`INFERENCE`). §3.
2. **The residual should act on the setpoint, upstream of the compliance loop.** One paper found that a residual
   added to an impedance controller's *output* is resisted by that controller (`FACT`, L04). The project's contract
   (a bounded Cartesian correction to the command) is the setpoint-level variant (`INFERENCE`). §4.
3. **The simulator, not the learner, limits training on this machine** (`INFERENCE` from the project's own
   throughput). At 600 physics steps/s with magnets and 20 Hz control, one process gives 6 control steps/s: 250,000
   steps take about 12 hours, and 1 million take about 2 days. Budgets in the tens of millions are out of reach. §5.
4. **No measured friction coefficient for silicone or rubber on ABS was found,** and pad friction depends strongly on
   load (`FACT`, C16, C17). A single constant pad μ is not supported across the G2's 10–50 N range (`INFERENCE`). §2.
5. **Published evidence does not pick SAC or PPO.** The ordering flips by task (`FACT`, L11, L02). §4.

## 2. Contact and friction modelling in MuJoCo
Slip and creep mechanics are already in [`MUJOCO_CONTACT_CREEP_FINDINGS.md`](MUJOCO_CONTACT_CREEP_FINDINGS.md); these
are additions.

### 2.1 Official guidance (`FACT`, S13 "Model tuning", read at git tag 4.0.1; checked by the main session)
| Setting | Guidance (quoted) |
|---|---|
| Integrator | "Use implicitfast for most models". `discrete` is being trialled as a candidate to replace it |
| Friction cone | "set cone="elliptic" and raise impratio (10 for manipulation, 10–100 for legged locomotion)" |
| Contact stiffness | "Rigid contacts usually prefer lowering it to 0.004–0.01", keeping `solref[0] >= 2 * timestep` |
| Contact dimension | "Set "4" (torsional) or "6" (torsional + rolling) on fingertips, grasp pads, and curved objects" |
| Timestep | "2 ms is usually reasonable, or slightly high, for contact-rich manipulation"; "stiff grippers, high gains, or thin objects often prefer 0.5–2 ms" |
| Mass ratios | "Mass or inertia ratios > 1000:1 across contacts or joints" degrade solver conditioning and accuracy |
| Friction units | "friction[1] and friction[2] have units of length (contact-patch radii)" |
| Deformable pads | Flex elasticity "raises a runtime error" under `implicit` and `implicitfast` |

`INFERENCE`:
- **The project's settings sit inside this guidance.** The cube uses implicitfast at 0.5 ms.
- **Pad contact dimension.** The creep findings record the G2 pads as condim 3; the guide recommends 4 or 6 on grasp
  pads. Multi-point box pads already resist torsion through pairs of tangential forces, so adding condim 4 could count
  it twice. Experiment Q3 (§6) would settle it.
- **Deformable (flex) pads are not compatible with the validated setup.** They would force a change of integrator.
  Rigid pads with soft-contact parameters remain the compatible representation.
- **Mass ratio.** The arm's links are kilograms and a cubie is 3.4 g, a ratio over 1000:1 across the grasp. This is a
  conditioning risk to check when the arm holds the contact cube in Phase 2.

### 2.2 Changes between MuJoCo 3.x and 4.0 (`FACT`, S14 changelog, as reported by the subagent)
| Version | Change |
|---|---|
| 3.3.0 | `nativeccd` became the default |
| 3.8.0 | `multiccd` enabled by default |
| 3.11.0 | `implicitfast` uses gyroscopic derivatives in place of midpoint integration |
| 3.13.0 | `discrete` integrator added |
| 4.0.0 | Stability work on nativeccd/multiccd "can slightly change contacts for models with convex or mesh collisions" |
| 4.0.0 | Actuators saturated by `actuatorfrcrange` "no longer contribute implicit actuator derivatives… models with light links and no armature may need joint armature or a smaller timestep" |

`INFERENCE`: contact settings published for MuJoCo 3.7 or earlier, including the Menagerie gripper pads, were tuned
under different collision defaults and are not guaranteed equivalent at 4.0.1. The P2 robot model limits arm torque
with `actuatorfrcrange`, so the last row applies to it.

### 2.3 Compliant fingertips and measured friction (`FACT`, as reported)
- **How published simulation work represents soft pads.**
  - C19 (a two-finger variable-friction hand) hardens MuJoCo's contact with solref and solimp, an elliptic cone, the
    Newton solver, a high impratio, optional noslip and multiccd. It gives no numbers.
  - C18 (a position-controlled parallel gripper) uses the solimp width, 0.003–0.01, to model objects of different
    stiffness, tuned against real grasps. Domain randomisation was "crucial" for transfer.
- **Measured friction.**
  - C17: a urethane pad on flat 3D-printed ABS, static μ = 0.688; bare ABS on ABS, 0.125. Normal force 1–2.5 N.
  - C16: silicone on acrylic. Static μ falls with load: for a flat pad, 6.10 at 1 N, 1.71 at 12.5 N and 1.17 at 25 N.
    Kinetic friction was 60 % of static at 1 N and 94 % at 25 N.
  - **No silicone-on-ABS or rubber-on-ABS measurement was found.**

`INFERENCE`: the feasibility assessment's friction range should be treated as an identified or randomised parameter,
not a constant. The bench protocol could add a pad pull test (Q1).

### 2.4 Sim-to-real evidence (`FACT`, as reported; each on its own task)
- **C12** (MuJoCo, Fetch arm, puck pushing): randomised link mass, joint damping, puck mass and friction, controller
  gains, action delay and observation noise. Real success 0.89 ± 0.06 over 28 trials, with "little calibration".
- **C08** (PyBullet, KUKA iiwa, peg-in-hole, torque control): system identification without dynamics randomisation
  gave mostly 20/20 insertions. The authors state that friction and snap-in events "are difficult or even impossible
  to simulate with tools like PyBullet or MuJoCo".
- **C13** (MuJoCo Playground): cube reorientation with a multi-finger hand randomised friction, cube mass, joint
  offsets, motor friction and PD gains. The most frequent real failure was the cube becoming wedged.
- **C14, C15** (abstracts): simulators capture inelastic impacts better than elastic ones, and some common contact
  relaxations "can severely widen the reality gap".

## 3. Classical controller baseline
### 3.1 What the real arm offers (`FACT`)
- **Modes** (C01, checked by the main session; C02, C03): 0 position, 1 servo, 2 joint teaching, 4 joint velocity,
  5 Cartesian velocity, 6 and 7 online trajectory planning. Mode 3 is "Not Used". **No joint-torque or current command
  mode is documented.**
- **Servo mode** (C01): the controller "can communicate at a maximum frequency of 250Hz"; "the recommended control
  frequency is 50-200Hz". Commands "do not set buffers and only execute the latest received target point". The
  example limits a step to 10 mm.
- **Readable signals** (C03): joint currents and an estimated joint torque. Its rate and accuracy are undocumented.
- **Optional six-axis force/torque sensor** (C03, C04): the SDK offers an admittance mode and a force mode, with
  stiffness 0–2000 N/m, rotational stiffness 0–20 N·m/rad and virtual mass 0.02–1 kg. The project has not decided to
  use this sensor.
- **Joint torque capacity:** see [`PHASE_2_ROBOT_MODEL_FINDINGS.md`](PHASE_2_ROBOT_MODEL_FINDINGS.md) §8 (continuous
  42 / 19 / 7 N·m by a forum reply; URDF peaks about 4× higher).

### 3.2 Impedance against admittance (`FACT`, C06, a one-joint analysis and experiment)
"Impedance Control provides very good performance when the environment is stiff but results in poor accuracy when the
environment is soft. In contrast, Admittance Control provides very good performance for soft environments but results
in contact instability for stiff environments."

`INFERENCE`:
- Because the arm takes only position or velocity setpoints, any compliance on the real robot is admittance-type: an
  outer loop that turns a measured or estimated wrench into setpoint changes, at 250 Hz or less, with a one-sample
  hold.
- A cube held by compliant pads is a moderately soft environment, which is the favourable case for admittance. A
  jammed cube is stiff, which is the unfavourable case.
- Without the force/torque sensor, the wrench must come from estimated joint torques, whose quality is unknown (Q4).

`PROPOSAL` (needs the user's approval; it does not change the master specification):
- Build the simulated baseline with the same structure the hardware allows: position-servo arm actuators, an outer
  admittance loop at 250 Hz or less, and a one-sample hold with one to three samples of delay.
- Read the specification's "stable lower-level impedance controller" as this structure. If a torque-level impedance
  controller is used in simulation instead, record it as an abstraction that the real arm cannot run.

### 3.3 Reference values in public code (`FACT`; defaults, not validated for any task here)
- libfranka's Cartesian impedance example (C10): 150 N/m and 10 N·m/rad, critically damped.
- robosuite's operational-space controller (C11): stiffness 150 with limits 0–300, damping ratio 1, steps of at most
  0.05 m.
- Both are for torque-controlled arms. They are starting points for a sweep, not settings.

### 3.4 Closest classical analogues (`FACT`, as reported)
- **Valve turning** (C21, six-axis arm, 6 N·m valve): radial misalignment gave radial forces of about 60 N with
  passive compliance only, and about 9 N once force control was added.
- **Valve turning** (C20): reaction-torque feedback corrected an axial misalignment of ±15° to a median of 2.46°.
- **Jamming and wedging** (C07, Whitney 1982) is the standard analysis. It was not read here.
- No paper on a parallel-gripper twist controller, or on cap unscrewing, was found.

`INFERENCE`: these support the feasibility assessment's point that misalignment becomes a large side force unless
compliance or force feedback absorbs it. They say nothing quantitative about a cube.

## 4. Residual RL
### 4.1 Published variants (`FACT`, as reported; L04 and L11 abstracts checked by the main session)
| Source | Task and robot | Base controller and residual | Reported result |
|---|---|---|---|
| S50 | Block insertion between two blocks, Sawyer, real | Residual (TD3) added to a hand-made Cartesian P-controller | About 8,000 real samples (3 h). Misaligned blocks: 15/20 with the residual, 2/20 without. Aligned: 20/20 both |
| S51 | Five Fetch tasks and a pusher, MuJoCo | Residual on hand-made policies; last layer initialised to zero | Push converges after about 2 million steps. A randomly initialised residual can make a good base policy worse |
| L01 | Connector insertion, Sawyer, real | Residual on a Cartesian P-controller; SAC and TD3 | A few thousand real steps. Only the residual method solved the hardest connector in the time allowed |
| L02 | Peg insertion, Franka, simulation | Residual on a motion primitive, 10 Hz policy over a 500 Hz impedance loop | Base 24 % / 8 % (easy / hard). SAC residual 94.8 % / 55.0 % after 700 episodes. PPO residual 87.6 % / 69.0 % after 25,500 episodes |
| L04 | Peg-in-hole with pose uncertainty, Franka | Compares a residual on the controller's output with a residual on its feedback signal | "internal feedback signals of the controller limit an RL algorithm". The output-level residual is resisted by the impedance controller |
| L06 | ManiSkill and Adroit tasks | Bounded residual (tanh times a scale) on a learned base policy | "Bounded residual action is essential" |
| L05 | Assembly, simulation with 1,024 parallel environments | PPO residual, scale 0.1, on a diffusion policy | 12 % → 94 % on one task; budget up to 500 million steps |
| L08 | Assembly, UR5e with a parallel gripper, MuJoCo | SAC Cartesian residual on a hybrid force–motion controller | 250,000 steps at about 13 Hz. One task; improvement shown in a figure; no seed count found |

`INFERENCE`:
- **The gain appears where the base controller fails.** In S50 the residual helped only in the misaligned case. If
  the classical controller already succeeds across the task distribution, there is nothing for a residual to add.
  The specification's order (classical controller first) lets this be measured before any training (Q7).
- **Bounding and initialisation matter.** A zero-initialised, bounded residual starts as the base controller (S51,
  L06). This matches the specification's bounded residual contract.
- **Where the residual enters matters** (L04). §1 item 2.

### 4.2 SAC, PPO and sample-efficient off-policy methods (`FACT`, as reported)
- **L11** (simulated KUKA, MuJoCo; PPO and SAC; peg insertion, hammering and pushing). Millions of steps to reach an
  80 % criterion with a task-space impedance action space: hammering PPO 0.11, SAC 0.012; insertion PPO 0.14,
  SAC 0.39; pushing PPO 0.21, SAC 0.18. **SAC was not uniformly more sample-efficient.**
- **L02:** SAC needed far fewer episodes; PPO did better on the harder task.
- **L15** (real Franka, with demonstrations): contact tasks learned in 25–50 minutes with a sample-efficient
  off-policy method.
- **L16–L18** (REDQ, DroQ, TQC): their gains are on locomotion benchmarks, not manipulation.

`INFERENCE`: the specification's matched-budget comparison of SAC and PPO is the right design. No source justifies
choosing one in advance.

### 4.3 Action space (`FACT`, as reported)
- **L11:** "learning references for a task-space impedance controller significantly reduces the number of samples
  needed" (abstract, checked). It learned fastest in all six task–algorithm cells.
- **L10** (simulated Panda, 20 Hz policy over a 500 Hz controller): joint-torque and low fixed-impedance policies
  failed path following; variable impedance in end-effector space did best on wiping. Real transfer 8/10.
- **L12** (13 action spaces, reaching and pushing): Cartesian velocity was best in simulation, and joint-torque
  pushing policies were never safe to deploy.

`INFERENCE`: these support the specification's bounded Cartesian residual over a compliant low-level controller, as a
reasonable choice. They are for torque-controlled arms on other tasks.

### 4.4 From privileged state to camera state (`FACT`, as reported)
- **S01** (Rubik's cube, real images, best model): orientation error 7.48°, position 6.24 mm, top-face angle 13.83°.
  Face angles from vision were hard enough that most experiments used an instrumented cube (5.90° mean error).
- **L26** (block pose from three cameras): 5.01° ± 2.47 and 9.27 mm ± 4.02 on real images.
- **L25, L27, L05:** asymmetric actor–critic and teacher–student distillation are the two established routes.
- **L29** (FINGR, 2026): a 2×2×2 cube with a dexterous hand, imitation learning, and cubie poses from coded markers.
- **No paper after 2019 reporting markerless face-angle accuracy was found.**

`INFERENCE`: face-angle error of the order of 10° from vision should be expected unless markers or an instrumented
cube are used. The classical controller's tolerance to face-angle noise should be measured before the vision work
(Q8). The cube model's forgiveness angle sets how much of this error is harmless.

### 4.5 Reward hacking and safety (`FACT`, as reported)
- **L30:** an agent flipped a brick to collect a mis-specified grasp reward.
- **L01:** pure RL "hacked" an image-distance reward by moving down beside the socket; the base controller in the
  residual setup prevented it.
- **L15:** learned success classifiers can be exploited. Its safety mechanism clips the reference error in the
  low-level loop instead of shrinking the policy's actions.
- **L14** (position-controlled arm): a force-limit violation ended the episode with a penalty. Removing the penalty
  lowered performance "considerably".

`INFERENCE`: the specification's reward-safety tests and its independent oracle address the first three. A force or
torque limit enforced below the policy (as in L15) is safer than a penalty alone.

## 5. CPU-only training feasibility
`FACT` (as reported):
- **L20:** on a 12-thread laptop, vectorising a MuJoCo locomotion environment gave 12,861 steps/s in a loop, 36,586
  with Python subprocesses and 105,126 with an asynchronous C++ pool.
- **L19:** a SAC run on a manipulation suite took "about two days" on 2 CPUs and no GPU.
- **L22:** MuJoCo's JAX port "can be 10x slower than MuJoCo" for single scenes on CPU, and has no noslip solver.
- **L32:** MuJoCo's Python bindings release the interpreter lock and offer a native multi-threaded rollout.

`INFERENCE` from the project's measured speeds (M6: 606 steps/s with the core magnets, 3,854 without; one idle
process; 0.5 ms timestep):

| Quantity | With magnets | Without magnets |
|---|---|---|
| Speed against real time | 0.30× | 1.93× |
| Control steps/s at 20 Hz (100 physics steps each) | 6 | 38.5 |
| 50,000 control steps | 2.3 h | 0.4 h |
| 250,000 control steps (the scale of L08) | 11.6 h | 1.8 h |
| 1 million control steps | 46 h | 7.2 h |
| 5 million control steps | 9.6 days | 1.5 days |

These are physics-only times for one process, without resets, policy inference, learning, or the arm model, which
will slow each step further.
- **Budgets like those of the PPO papers (tens to hundreds of millions of steps) are out of reach on this machine.**
- **Budgets of 10,000 to 300,000 steps** (S50, L01, L08) are reachable. Multi-process scaling would help but is
  unmeasured here (Q5), and ER7 showed that memory and shared CPU limit it in practice.
- **Because the simulator is the bottleneck,** methods that take many learning updates per environment step cost
  little extra wall time. They do compete with the simulator for cores.
- **The magnet force callback is the main cost** (a 6× slowdown). Speeding it up would be the largest single gain for
  Phase 3, but it must not change the force law's results; that would need its own validation.

## 6. Open questions and the small experiment for each
| # | Question | Smallest experiment | Phase |
|---|---|---|---|
| Q1 | Pad-on-cube friction and its load dependence | Pull or incline test with the real pad material on a cube face at 10, 30 and 50 N. Until then, sweep μ in simulation | Bench / 2 |
| Q2 | Stable admittance stiffness at 250 Hz on soft pads | In simulation, wrap the position servo in an admittance loop with 1–3 samples of delay; sweep stiffness 200–2000 N/m; log chatter and internal force | 2 |
| Q3 | Does condim 4 double-count pad torsion? | Press one pad on a fixed cube and ramp the torque about the pad normal; compare condim 3 multi-contact with condim 4 | 2 |
| Q4 | Wrench estimation without a force/torque sensor | A hardware log of the SDK's estimated joint torque, or a question to UFACTORY (the user has declined contact so far, P-17) | 2 |
| Q5 | Does throughput scale across processes on this machine? | Run 1, 2, 4 and 8 independent headless processes for 60 s each on a quiet machine; record total steps/s (E1-8, E2-8) | 1 / 2 |
| Q6 | Is 20 Hz the right control rate? | Sweep the action hold over 10, 20 and 50 Hz on the classical controller alone | 2 |
| Q7 | Is there headroom for a residual? | Measure the classical controller's failure rate under the planned randomisation before any training | 2 → 3 |
| Q8 | How much face-angle noise can the task tolerate? | Inject face-angle noise of 5°, 10° and 15° into the classical controller's observation | 2 → 3 |
| Q9 | What residual bound? | Run a random bounded residual at three or four bounds; take the largest that does not degrade the base controller | 3 |
| Q10 | Does the compliance loop resist a setpoint residual? | Apply a step in the residual during contact; log transmitted displacement and force against hold length | 3 |

## 7. Sources added by this review (accessed 2026-11-19)
Verification levels are the subagents' unless marked **main**: "read" = primary page, PDF or file text read;
"via summary" = read through a summarising fetch tool; "abstract" = abstract only; "snippet" = search result only.

### Contact modelling and controller
| ID | Citation | Reference | Level |
|---|---|---|---|
| C01 | UFACTORY, "UFACTORY Robot Arm Servo Mode Usage Guide" | https://docs.supportarticle.ufactory.cc/support_articles/developer/ufactory-servo-mode-guide.html | **main**, via summary |
| C02 | UFACTORY Studio manual, "10. Robotic Arm Motion Mode and State" | https://docs.ufactory.cc/user_manual/ufactoryStudio/10.motion_mode_and_state.html | via summary |
| C03 | xArm-Python-SDK, `doc/api/xarm_api.md`, commit `dcb9079` | https://github.com/xArm-Developer/xArm-Python-SDK | read |
| C04 | UFACTORY docs, "7. Force Torque Sensor" | https://docs.api.ufactory.cc/xarm_python_sdk_docs/7.-Force-Torque-Sensor.html | via summary |
| C06 | C. Ott, R. Mukherjee, Y. Nakamura, "Unified Impedance and Admittance Control", ICRA 2010 | DOI 10.1109/ROBOT.2010.5509861 | read |
| C07 | D. E. Whitney, "Quasi-Static Assembly of Compliantly Supported Rigid Parts", J. Dyn. Sys. Meas. Control 104(1), 1982 | DOI 10.1115/1.3149634 | snippet (lead only) |
| C08 | M. Kaspar, J. D. Muñoz Osorio, J. Bock, "Sim2Real Transfer for Reinforcement Learning without Dynamics Randomization", IROS 2020 | arXiv:2002.11635 | read |
| C10 | Franka Robotics, libfranka `examples/cartesian_impedance_control.cpp` (Apache-2.0) | https://github.com/frankaemika/libfranka | read |
| C11 | robosuite, `controllers/config/default/parts/osc_pose.json` | https://github.com/ARISE-Initiative/robosuite | read |
| C12 | X. B. Peng, M. Andrychowicz, W. Zaremba, P. Abbeel, "Sim-to-Real Transfer of Robotic Control with Dynamics Randomization", ICRA 2018 | arXiv:1710.06537 | read |
| C13 | K. Zakka et al., "MuJoCo Playground", 2025 | arXiv:2502.08844 | via summary, partial |
| C14 | B. Acosta, W. Yang, M. Posa, "Validating Robotics Simulators on Real-World Impacts", RA-L 2022 | arXiv:2110.00541 | abstract |
| C15 | Q. Le Lidec et al., "Contact Models in Robotics: A Comparative Analysis", T-RO 2024 | arXiv:2304.06372 | abstract |
| C16 | M. T. Leddy, A. M. Dollar, "Examining the Frictional Behavior of Primitive Contact Geometries for use as Robotic Finger Pads", RA-L 2020 | DOI 10.1109/LRA.2020.2974683 | read |
| C17 | A. J. Spiers, B. Calli, A. M. Dollar, "Variable-Friction Finger Surfaces to Enable Within-Hand Manipulation via Gripping and Sliding", RA-L 2018 | https://www.eng.yale.edu/grablab/pubs/Spiers_RAL2018.pdf | read |
| C18 | L. Lach et al., "Towards Transferring Tactile-based Continuous Force Control Policies from Simulation to Robot", 2023 | arXiv:2311.07245 | read |
| C19 | Q. Yan, Z. Ding, X. Zhou, A. J. Spiers, "Variable-Friction In-Hand Manipulation for Arbitrary Objects via Diffusion-Based Imitation Learning", 2025 | arXiv:2503.02738 | read |
| C20 | A. Kumar et al., "Robotic Valve Turning: Axial Misalignment Correction Using Reaction Torque Feedback", 2026 | arXiv:2609.24413 | abstract |
| C21 | H. Xing et al., "Robotic Valve Turning with a Wheeled Mobile Manipulator via Hybrid Passive/Active Compliance", Sensors 24(17):5559, 2024 | DOI 10.3390/s24175559 | via summary |

Not used as evidence: C05 (reseller listing of the force/torque sensor), C09 (same paper as L10), C22 and C23
(leads, snippet only).

### Residual RL and CPU feasibility
| ID | Citation | Reference | Level |
|---|---|---|---|
| L01 | G. Schoettler et al., "Deep Reinforcement Learning for Industrial Insertion Tasks with Visual Inputs and Natural Rewards", 2019 | arXiv:1906.05841 | read (tables garbled) |
| L02 | T. Davchev et al., "Residual Learning from Demonstration: Adapting DMPs for Contact-rich Manipulation", 2020 | arXiv:2008.07682 | read |
| L04 | A. Ranjbar, N. A. Vien, H. Ziesche, J. Boedecker, G. Neumann, "Residual Feedback Learning for Contact-Rich Manipulation Tasks with Uncertainty", 2021 | arXiv:2106.04306 | read; abstract **main** |
| L05 | L. Ankile et al., "From Imitation to Refinement – Residual RL for Precise Assembly", 2024 | arXiv:2407.16677 | read |
| L06 | X. Yuan et al., "Policy Decorator", 2024 | arXiv:2412.13630 | read |
| L08 | Abuibaid, Sidorenko, Wagner, Ruskowski, "Learning-Based Strategy for Composite Robot Assembly Skill Adaptation", 2026 | arXiv:2604.06949 | read |
| L10 | R. Martín-Martín et al., "Variable Impedance Control in End-Effector Space: An Action Space for Reinforcement Learning in Contact-Rich Tasks", IROS 2019 | arXiv:1906.08880 | read |
| L11 | P. Varin, L. Grossman, S. Kuindersma, "A Comparison of Action Spaces for Learning Manipulation Tasks", IROS 2019 | arXiv:1908.08659 | read; abstract **main** |
| L12 | E. Aljalbout et al., "On the Role of the Action Space in Robot Manipulation Learning and Sim-to-Real Transfer", 2024 | arXiv:2312.03673 | read |
| L14 | C. Beltran-Hernandez et al., "Learning Force Control for Contact-rich Manipulation Tasks with Rigid Position-controlled Robots", 2020 | arXiv:2003.00628 | read (table garbled) |
| L15 | J. Luo et al., "SERL: A Software Suite for Sample-Efficient Robotic Reinforcement Learning", 2024 | arXiv:2401.16013 | read |
| L16 | T. Hiraoka et al., "Dropout Q-Functions for Doubly Efficient Reinforcement Learning", 2021 | arXiv:2110.02034 | read |
| L17 | X. Chen et al., "Randomized Ensembled Double Q-Learning", 2021 | arXiv:2101.05982 | read |
| L18 | A. Kuznetsov et al., "Controlling Overestimation Bias with Truncated Mixture of Continuous Distributional Quantile Critics", 2020 | arXiv:2005.04269 | abstract |
| L19 | Y. Zhu et al., "robosuite: A Modular Simulation Framework and Benchmark for Robot Learning" | arXiv:2009.12293 | read |
| L20 | J. Weng et al., "EnvPool", 2022 | arXiv:2206.10558 | read |
| L22 | MuJoCo documentation, MJX | https://mujoco.readthedocs.io/en/stable/mjx.html | via summary |
| L25 | L. Pinto et al., "Asymmetric Actor Critic for Image-Based Robot Learning", 2017 | arXiv:1710.06542 | abstract |
| L26 | OpenAI, "Learning Dexterous In-Hand Manipulation", 2018 | arXiv:1808.00177 | read (Table 6) |
| L27 | T. Chen et al., "Visual Dexterity", 2023 | arXiv:2211.11744 | read, partial |
| L29 | Y. Liang, Q. Peng, M. Kim, X. Wang, "FINGR: Learning Dexterous Hand Control for Real-World Rubik's Cube Solving", 2026 | arXiv:2609.33973 | read, partial; abstract **main** (2×2×2) |
| L30 | I. Popov et al., "Data-efficient Deep Reinforcement Learning for Dexterous Manipulation", 2017 | arXiv:1704.03073 | read |
| L32 | MuJoCo documentation, Python bindings (rollout) | https://mujoco.readthedocs.io/en/stable/python.html | via summary |

The subagents also reported L03, L07, L09, L13, L21, L23, L24, L28, L31, L33 and L34; they are not relied on above.
No DOIs were checked for the L-sources, so only arXiv numbers are given.

## 8. Searches that came up empty
- Residual RL, or any RL, for cube face turning with a parallel gripper and an arm.
- A measured friction coefficient for silicone or rubber on ABS.
- Any xArm joint-torque or current command mode.
- Published MuJoCo work using flex elements for parallel-gripper pads.
- A classical cap-unscrewing or parallel-gripper twist controller.
- Markerless face-angle estimation accuracy for cubes after 2019.
- Per-core throughput figures for common MuJoCo manipulation suites.

## 9. Limits
- Two searches on one day, by subagents; most entries were not re-opened by the main session.
- Constrained-RL methods and several follow-up leads were not examined.
- The CPU table uses idle single-process speeds for the cube alone; the arm, the gripper and the controller will add
  cost that is not yet measured.
