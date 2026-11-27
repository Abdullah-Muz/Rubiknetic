# G2 jam detection: root cause analysis and industry practice (research note, 2026-11-26)

**Why:** P-111. The P-109 (2) J7 lag guard false-triggered, and an obstacle produced a push-through, not a stall. The
user asked for "a round of research, root cause analysis, and an idea of how industry players deal with issues like
this".

**Scope:**
- Web search only, access date 2026-11-26; snippet-level reading of the sources below. No full-text review is claimed.
- Simulation facts are from `experiments/D18_two_arm_m7/` (logs `jam_guard.txt`, `jam_noguard.txt`,
  `guard_normal.txt`).
- **Labels:** `FACT`, `INFERENCE`, `PROPOSAL`.

## 1. Root cause analysis (our simulation)
### RC-1: the lag rule measures the servo's design, not a jam
- **`FACT` (model):** J7 uses the Menagerie position servo: force = kp·(q_cmd − q) − kv·q̇, with kp 800 and kv 80.
- **`FACT` (model):** at steady velocity ω it therefore trails by about (kv/kp)·ω = 0.1 s × ω. A 1 s cosine quarter
  turn peaks at about 2.5 rad/s, so the lag is up to about 14°. Measured in `jam_noguard`: 13.9°.
- **`INFERENCE`:** real servo drives follow trajectories with **velocity feedforward**, so their following error comes
  mostly from friction and load, not from speed. Our controller sends position only.
- **Root cause:** the missing feedforward in our controller, plus a guard that took raw lag as a jam signal.

### RC-2: a blocked layer becomes a push-through, because the weakest link is arm A's grip
- **`FACT` (`jam_noguard`):**
  - When a U corner met the obstacle, the fingertip torque on the layer rose to 1.67 N·m.
  - The cube moved 2.2 mm and 2.5° in arm A's pads; the turn still reached −87° (error 3.07°).
- **`INFERENCE`:**
  - The torque the system can deliver is J7's servo, up to 30.6 N·m. That far exceeds the torque arm A's friction grip
    can resist (μ·F·a ≈ 0.8 × 20 N × 0.057 m ≈ 0.9 N·m).
  - So under obstruction the grip slips before J7 stalls.
  - **A jam guard that waits for a stall can never fire here:** the cube is harmed first.

### RC-3: the cube's torque is small next to J7's own losses
- **`FACT`:** normal fingertip torque is ≤ 0.28 N·m. J7 needs about 5.9 N·m, mostly its 1 N·m friction and its
  damping (2 N·m·s/rad × 2.5 rad/s ≈ 5 N·m).
- **`INFERENCE`:**
  - Any guard reading J7's motor torque must subtract a model of those losses.
  - Its error must be small next to about 1 N·m, which is a hard requirement (§2.3).

## 2. How industry handles it (sources in §5)
1. **UFACTORY xArm (our arm).**
   - The controller offers **collision sensitivity 0–5**. It stops when a joint's torque deviation exceeds a normal
     range (manual).
   - Sensitivity > 0 monitors **motor currents to estimate joint torque** and can give **false estimates because joint
     friction and temperature are not modelled accurately**. Error C31 is "collision caused abnormal joint current".
   - A support reply suggests **lowering the sensitivity during impedance control** (xarm_ros2 issue 55).
   - `FACT` (as sourced; secondary, GitHub thread): this is coarse protection, not a fine-contact jam sensor.
2. **Universal Robots.**
   - A TCP/elbow **force limit** stops the robot and backs off to the pre-limit position (official safety table).
   - A forum reply says the force is **estimated from motor current and calibrated joint parameters**
     (informal source).
3. **ABB (IRC5/OmniCore) Motion Supervision.**
   - Compares actual axis behaviour with what the commanded motion and **payload model** predict.
   - Tunable sensitivity 0–300 %; more sensitive at low speed.
   - Load-data errors invalidate it (ABB community, manual).
4. **Franka (FR3/Panda).**
   - **Joint torque sensors.** `setCollisionBehavior` sets per-joint contact and collision thresholds, separately for
     acceleration and constant-velocity phases, using the robot's external force estimate.
5. **The research standard** (Haddadin, De Luca, Albu-Schäffer, *IEEE T-RO* 33(6), 2017, DOI
   10.1109/TRO.2017.2723903).
   - Model-based collision detection, isolation and identification from proprioceptive sensors only.
   - The **generalized momentum observer** gives an external-torque residual without needing acceleration.
6. **Sensorless practice and its limits** (papers and patents in §5).
   - **Friction-model error is the main source of false alarms.** Remedies: LuGre or Coulomb-viscous friction
     identified offline; time-varying thresholds that include model error; raising the threshold until identification
     is done.
   - One study reports current-based estimation errors growing under acceleration, **up to about 20 N·m** on an
     industrial arm.
7. **Fine contact and jamming in assembly** (peg-in-hole literature).
   - Jamming and wedging are handled with **wrist force/torque sensing plus compliance**.
   - Wrist force spikes signal contact with a jammed part.
8. **Available hardware.**
   - UFACTORY sells a **6-axis F/T sensor for xArm 5/6/7 (serial ≥ XI1305) and 850** (retailer and reseller data;
     official sheet not checked):
     - 400 N and 20 N·m range;
     - 200 Hz;
     - about 600 g;
     - Python and C++ SDK.

**Synthesis (`INFERENCE`):** industry uses **two layers**.
- **(a) Coarse protection:** current- or torque-based collision detection against a dynamics and friction model,
  tuned conservatively because the model error is large.
- **(b) Fine-contact tasks:** a **wrist F/T sensor** (or joint torque sensors, as on Franka) together with
  **compliance and force or torque limits**, so that a jam cannot build large forces in the first place.

Our task is a fine-contact task: about 0.3 N·m on the layer against about 6 N·m of joint losses. Current-based
sensing alone would sit at the edge of its accuracy.

## 3. Options for the G2 controller (`PROPOSAL`; for the user's choice)
| # | Option | Detects | Realism | Effort | Risk |
|---|---|---|---|---|---|
| A | **Velocity feedforward + torque budget on J7.** Add feedforward (removes RC-1). Cap J7's torque at its modelled losses + about 0.6 N·m, so it **cannot push the layer harder than arm A's grip holds**. Plus a stall rule on feedforward-corrected lag | true stalls; prevents push-through by design | high (power and force limiting is standard cobot practice) | low | the cap depends on the J7 friction model; a model error shifts it |
| B | **Model-based external-torque residual on J7**, xArm/ABB style. Motor torque minus modelled friction, damping and inertia, with **deliberate model error** in simulation (e.g. ±20 % friction and damping, per §2.6). Threshold from a pilot | push-through and jam when the residual exceeds about 1 N·m | high for xArm (C31 is this) | medium | at our scale the margin is thin; false alarms likely unless the turn is slow |
| C | **Wrist F/T sensor on arm B** (UFACTORY 6-axis): the tool torque about the axis is measured directly. Threshold about 0.6–0.8 N·m | everything, clearly | high (standard for fine assembly) | medium: a **hardware decision** (+600 g, longer tool, a new model part, cost) | sensor noise and resolution need checking against the official sheet |
| D | **A + B together:** a torque budget as the primary safety, the residual as a secondary flag | both | high | medium | as A and B |

**Recommendation:**
- **A now**, because it removes the root causes and needs no new hardware. Add **B as a reported secondary signal**
  (D) if wanted.
- Keep **C** as the documented path if the real-hardware phase needs fine jam detection.
- **Decision for the user:** C changes the robot's hardware and so is a strategic choice (CLAUDE.md).

## 4. What would be tested (G2-7, unscored first)
1. **Normal sequence:** no trigger, and turns unchanged. With feedforward the lag should drop to the friction level.
2. **Obstacle:** with A, the layer stops at the obstacle with **no cube shift in arm A's grip** beyond a pilot limit;
   the guard opens the turner.
3. **Model error:** the same tests with ±20 % J7 friction and damping in the simulator but not in the controller's
   model, so the result does not rely on a perfect model.

## 5. Sources (accessed 2026-11-26)
| Topic | Source |
|---|---|
| xArm collision sensitivity (manual) | https://www.manualslib.com/manual/3211390/Ufactory-Xarm.html?page=86 |
| xArm current-based estimate, false estimates, C31 | https://github.com/xArm-Developer/xarm_ros2/issues/55 |
| UR force limit and stop behaviour | https://www.universal-robots.com/manuals/EN/HTML/SW5_25_1/Content/prod-usr-man/complianceUR20/safetyFunctionsAndinterfaces/safety_functions_table1.htm |
| UR protective stops | https://www.universal-robots.com/articles/ur/robot-care-maintenance/understanding-protective-stops/ |
| UR force from current (informal) | https://forum.universal-robots.com/t/recommended-safety-setting-limitations/1261 |
| ABB Motion Supervision | https://library.e.abb.com/public/d4708d0240be2966c125772f00528ca9/Collision%20det%20PR10044EN_R2.pdf ; https://tech-community.robotics.abb.com/t/motion-supervision-tune-values/6519 |
| Franka collision behaviour | https://docs.rs/crate/libfranka-rs/0.8.0-alpha-1/source/src/robot.rs |
| Collision survey (Haddadin, De Luca, Albu-Schäffer 2017) | https://iris.uniroma1.it/bitstream/11573/1071580/5/Haddadin_Postprint_Robot-Collisions_2017.pdf |
| Current-based detection, error under acceleration | https://tdl-ir.tdl.org/handle/2152/21585 |
| Friction models, thresholds, false alarms | https://pmc.ncbi.nlm.nih.gov/articles/PMC7435754 ; https://elib.dlr.de/195141/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC5470894 |
| Jamming and wedging, wrist force sensing | https://arxiv.org/pdf/2404.03943 ; https://arxiv.org/pdf/2002.02580 |
| UFACTORY 6-axis F/T sensor | https://www.robotshop.com/products/ufactory-6-axis-force-torque-sensor-xarm-850-400n ; https://www.ufactory.cc/wp-content/uploads/2023/05/6-Axis-Force-Torque-Sensor-V2.0.04.pdf |
