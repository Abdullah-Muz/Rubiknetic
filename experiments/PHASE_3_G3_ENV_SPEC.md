# Phase 3 (G3) environment contract: residual RL on the G2 controller (DRAFT for the user's review)

**Status: DRAFT specification. Documents only.** No environment, policy, reward or test code exists. No simulation was
run to write it. It specifies the environment that `experiments/PHASE_3_G3_DESIGN.md` §3 step 3 calls for, under the
user's decisions D1–D5 (P-146). Every `PROPOSAL` needs the user's approval before implementation. Nothing here changes a
frozen G2 file, the master specification, `docs/RL_EXPERIMENT_SPEC.md` or a decision.

**Labels:** `FACT` (code or committed record, cited `file:line`), `INFERENCE` (reasoning from facts), `ASSUMPTION`,
`PROPOSAL` (for the user), `DECISION` (the user's, cited).

**Inputs read:** `experiments/PHASE_3_G3_DESIGN.md`; `docs/DECISION_LOG.md` P-134 (line 213), P-145 (line 224), P-146
(line 225); `docs/RL_EXPERIMENT_SPEC.md`; `phases/PHASE_3_REINFORCEMENT_LEARNING.md`; `docs/VALIDATION_PLAN.md` G3
(lines 64–72); `docs/research/PHASE_3_READINESS_2026-11-28.md`; `docs/research/G3_RL_LITERATURE_UPDATE_2026-11-28.md`;
`experiments/PHASE_2_G2_PREREGISTRATION.md` §0–§4; `experiments/D18_two_arm_m7/two_arm.py`;
`experiments/E8_scored_g2/trials.py`; `src/rubiknetic/cube_physics/rig.py`; `src/rubiknetic/cube_physics/readout.py`;
`experiments/D24_b0_stress_map/stress_map.py`, `analyze.py`; the scored G2 records in `experiments/E8_scored_g2/results/`.

**Path abbreviations:** `TA` = `experiments/D18_two_arm_m7/two_arm.py`; `TR` = `experiments/E8_scored_g2/trials.py`;
`PR` = `experiments/PHASE_2_G2_PREREGISTRATION.md`; `DS` = `experiments/PHASE_3_G3_DESIGN.md`; `RS` =
`docs/RL_EXPERIMENT_SPEC.md`; `RIG` = `src/rubiknetic/cube_physics/rig.py`; `RO` =
`src/rubiknetic/cube_physics/readout.py`.

---

## 0. Decisions this spec implements, and the constraints it must keep

**Decisions (`DECISION`, P-146, `docs/DECISION_LOG.md:225`; `DS:34-41`):**
- D1: a B0 stress map first. Its results define the training and held-out distributions. D24 has scripts at
  `b5deb88`; no D24 result is committed yet (`FACT`: `experiments/D24_b0_stress_map/` holds only `stress_map.py` and
  `analyze.py`).
- D2: a bounded residual on arm B's **setpoints**: gripper-base position ±3 mm per axis, axis direction ±2°, J7 roll
  target ±3°. Never torques. The gripper is not learned. Policy rate 20 Hz (100 physics steps), action held between
  updates (`DS:56-65`).
- D3: **asymmetric actor-critic.** The simulator's layer angle goes to the critic only. The actor, which is the
  evaluated policy, sees only signals a real robot has.
- D4: Stable-Baselines3 SAC, CPU PyTorch, Gymnasium, pinned when introduced. Critic LayerNorm. Residual initialised at
  zero. About 20k B0 transitions pre-filled. A 50k-step pilot, then 2×10⁵ steps × 3 seeds.
- D5: B0, B1 (random residual), B2 (SAC) and B3 (PPO at a matched budget) on one held-out bank of starts. Exact
  McNemar per seed, Wilson intervals, every seed reported, and a no-harm check on G2's starts.
- B0 = G2's validated torque-level controller, disclosed as an abstraction the real xArm cannot run (P-134,
  `docs/DECISION_LOG.md:213`).

**Constraints carried over (`FACT` unless marked):**
- C1. Controllers read only robot joint states, kinematics derived from them, the F/T sample, commanded targets and
  time. They never read cube or cubie state (`PR:112-114`; `TA:6-7`; CLAUDE.md). G2 tests this with
  `test_controllers_ignore_cube_state` and `test_roll_commands_ignore_cube_state` (`tests/test_scored_g2.py:665`,
  `:697`).
- C2. Privileged simulator state may be used in training (critic, reward) but never in the evaluated actor
  (CLAUDE.md; D3).
- C3. Every G2 validity check stays active in evaluation: the magnets at every step, the edit and model audits,
  contacts, causality, drive, the oracle (`DS:31-32`; `VALIDATION_PLAN.md:69`).
- C4. The magnet force is a process-global MuJoCo callback, so there is **one environment per process**
  (`PHASE_3_READINESS:68-72`). Each environment keeps P-130's per-step magnet counter (`TA:402-410`, `TA:596-600`).
- C5. No file in G2's frozen set (`experiments/E8_scored_g2/run.py:50-62`, which includes `TA`, `TR`, `layout.py`,
  `hold.py`, `turn.py`) is edited. Everything in this spec lives in new files.
- C6. "An RL success means exactly a G2 success" (`DS:31-32`; `PHASE_3_READINESS:100-105`).

---

## 1. Frames, units, signs and rates

### 1.1 Rates (`FACT`)
| Quantity | Value | Source |
|---|---|---|
| Physics timestep | 0.5 ms (2 kHz) | `TR:38` (`SIM_DT`), `PR:100` |
| Arm B impedance and J7 law | every physics step | `TA:589-600` (`ctrl_step`) |
| Wrist F/T sample | 200 Hz = every 10 physics steps | `TA:92` (`FT_RATE`), `TA:458` (`ft_every`) |
| G2 F/T guard noise | N(0, 0.01 N·m) on τ_z, one stream `default_rng(29000)` restarted in every trial | `TA:92`, `TA:457`, `TA:787-788`; `PR:88-89`, `PR:477-478` |
| Policy (G3) | 20 Hz = every 100 physics steps (`DECISION` D2) | `DS:63` |

### 1.2 Frames (`FACT` unless marked)
- **World W:** table plane z = 0. Arm A base at the origin; arm B base at (1.0, 0, 0) m, yawed 180°. Nominal cube centre
  (0.5, 0, 0.30) m. Cube +z (the U face's outward normal) = world +x (`TA:4-5`; `PR:101-102`).
- **Core frame C:** the core body's frame. Its axes in W at the nominal pose: cube x = world y, cube y = world z, cube
  z = world x (`TA:286`). Every layer angle is measured in C (`RO:30-36`).
- **Nominal task frame T (`PROPOSAL`):** a world-fixed frame computed once per episode from arm B's **nominal** grasp
  rotation `RBt = RB @ (ROLL180 if roll180 else I)` (`TA:436`), the same matrix whose third column is G2's axis
  setpoint `a_d` (`TA:474`). Its axes: `e1 = RBt[:,0]`, `e2 = RBt[:,1]`, `e3 = RBt[:,2] = a_d`. Its origin is the
  nominal grasp position `pB_grasp` (`TA:434`). T comes from the nominal layout only, never from cube state (as
  `roll_sign`, `TA:452-453`). It does **not** rotate with J7.
- **F/T sensor frame S:** the `ft_site` on arm B's gripper base (`TA:237-241`). It rotates with J7. Its z axis is the
  tool axis. MuJoCo's force/torque sensors give what link7 transmits to the gripper subtree (`TA:221-223`).
- **Arm A gripper frame A:** the frame of `xarm_gripper_base_link` on arm A. G2 measures core slip and rotation in it
  (`TA:737-740`, `rel()`).

### 1.3 Signs and angle conventions (`FACT`)
- A layer angle is the signed rotation, right-handed about the face's outward normal, between two snapshots, per cubie,
  in C (`RO:47-50`). The turn angle is the mean over the layer's members fixed at the move start (`TA:755`, `TA:827`).
- Commanded rotation about U's outward normal: **U −90°, U′ +90°, U2 −180°** (`TA:826`; `PR:157-158`).
- The J7 command displacement for a move is `A = roll_sign · delta`, with `delta = −π/2·{U:1, U2:2, U′:−1}`
  (`TA:764`, `TA:778`). `roll_sign` comes from the nominal layout (`TA:453`).
- `INFERENCE`: `rotation_about_deg` returns per-snapshot angles, so a U2 turn passes through ±180°. G2 wraps the
  turn error at the end (`TA:828`). The G3 reward must unwrap by summing per-control-step increments, each well under
  180° (§4.2).

### 1.4 Units
SI internally (m, rad, N, N·m, s). Reports use mm and degrees, as G2 does. Every normalisation constant below is
stated in the units it divides.

---

## 2. Episode

### 2.1 Start state (`PROPOSAL`; the stress distribution is TBD by D24)
- **Base draw:** G2's own `TR.start_draw(seed)` (`TR:53-58`): cube offset uniform ±1 mm per axis, per-face setup
  misalignment uniform ±1°, the cube solved. It is used unchanged, so the no-harm bank (§7) is exactly G2's start
  distribution.
- **Stress overrides:** drawn from a distribution **S** that the user picks after D24. It uses only override keys G2's
  `TR.configure` and `TR.run_trial` already accept (`TR:77-90`, `TR:310-311`), the same ones D24 sweeps
  (`stress_map.py:43-65`):
  - `extra_offset_m` (3-vector);
  - `misalign_override` (per face, deg);
  - `pad_mu` (both arms);
  - `grip` (both arms, N);
  - `insertion_u` (turner insertion depth, m).
- **Random streams (`PROPOSAL`):**
  - G2's draw uses `default_rng(seed)`, unchanged.
  - Every G3 stream uses list entropy, which cannot collide with an integer seed or with G2's and D24's offset streams
    (+500000, +700000, +800000; `TR:62`, `stress_map.py:36`, `:52`):
    - stress overrides: `default_rng([3, seed, 0])`;
    - observation F/T noise: `default_rng([3, seed, 1])`;
    - B1's random residual: `default_rng([3, seed, 2])`;
    - the commanded move in training: `default_rng([3, seed, 3])`.
  - The leading 3 tags G3.
- **Commanded move:** one of {U, U′, U2}.
  - Training: drawn uniformly per episode.
  - Held-out and no-harm banks: balanced, with each start condition crossed with all three moves.

### 2.2 Phases of one episode
Taken from G2's procedure, which runs unchanged (`PR:125-165`; `TA:494-541`, `TA:723-735`, `TA:750-849`). The physics
step counts are `INFERENCE` from the code's durations, checked against the scored records: one-move U and U′ trials
end at `sim_time_s` = 10.4085 s, U2 at 11.4085 s (`FACT`: every G2-2 and G2-3 record in
`experiments/E8_scored_g2/results/`).

| # | Phase (G2 code) | Duration | Physics steps | Residual |
|---|---|---|---|---|
| P0 | Start sequence: settle, arm A closes, the stand drops (`TA:494-541`) | 3.6 s | 7,200 | **off** |
| P1 | Approach: arm B moves 40 mm along the axis, then waits (`TA:723-730`) | 2.0 s | 4,000 | **off** |
| P2 | Move settle, gripper open, integral on (`TA:759`) | 0.3 s | 600 | **off** |
| P3 | Close: integral held (`TA:761`); arm B ramps closed (`TA:762`, `TA:742-748`) | ≈ 1.61 s | ≈ 3,217 | **on** |
| P4 | Dwell after closing (`TA:763`) | 0.3 s | 600 | **on** |
| P5 | Roll: cosine ramp, 1 s per quarter turn, F/T and stall guards active (`TA:779-803`) | 1 s (U, U′) / 2 s (U2) | 2,000 / 4,000 | **on** |
| P6 | Hold (`TA:805-807`) | 0.3 s | 600 | **on** |
| P7 | Open, then wait (`TA:808-809`) | 0.3 s | 600 | held, not updated (§3.5) |
| P8 | Integral on (`TA:810`); roll back to the start angle, gripper open (`TA:814-821`) | 1.0 s | 2,000 | ramped to 0 (§3.5) |
| — | End-of-move checks (`TA:822-849`) and G2's classification (`TR:163-194`) | — | — | — |

- `INFERENCE`: the close duration (P3) = (0.85 − θ_open) / 0.5 rad/s (`TA:742-748`; `build_model.py:75`;
  `hold.py:46`). θ_open ≈ 0.046 rad reproduces the records' 10.4085 s. Test E5 (§8) measures the exact count.

**The learning window is P3–P6:** from the first physics step of `ramp_grip` (the gripper starts closing) to the
physics step after the open command (`TA:808`).

**Why the residual acts only in P3–P6 (`PROPOSAL`):**
1. **Information.** While arm B is open (P0–P2, P7–P8), no robot-side signal carries anything about the cube. Its F/T
   sees only the gripper's own weight. A residual there could only be open-loop.
2. **Leverage.** The layer is turned only while arm B grips it (P3–P6). This is where the stress-map failures are
   expected (grasp under offset or misalignment, roll under friction or grip variation).
3. **The integral term.** It integrates only while the fingers are open (`TA:555-558`, `PR:145-146`). A residual in an
   open phase would wind it up and carry the residual into later phases through the integrator. In P3–P6 the integral
   is held, so the residual enters the impedance directly.
4. **Judged contacts.** In P1 and P2 any non-fingertip robot–cube, arm–arm or cube–stand contact fails the trial
   (`PR:215-218`). An open-loop residual there adds risk with no possible gain.
5. **Attribution.** The state at the start of P3 is bit-identical across B0, B1, B2 and B3 (test E2). Every difference
   between the arms then arises inside the window.

### 2.3 Episode length (`INFERENCE` from §2.2)
- The window has about 6,417 physics steps for U and U′ and about 8,417 for U2.
- That gives **65 policy decisions (U, U′) and 85 (U2)**, at window steps 0, 100, 200, … The last interval is short
  (about 17 steps). Test E5 checks the exact counts.
- The last `step()` call also runs P7, P8 and G2's end-of-move checks (2,600 physics steps). It returns the terminal
  reward.
- `PROPOSAL`: discount γ = 0.99 (an effective horizon of about 100 decisions, longer than the episode).
- **One U-family move per episode** (as instructed).

### 2.4 Cost of one move per episode (`INFERENCE`, important for the budget)
- Only 6,417 of 20,817 physics steps (31 %) of a U episode are inside the window (37 % for U2). P0–P2 and P7–P8 must be
  simulated every episode.
- `FACT`: median wall time of the scored single-move trials under 8 workers: **233 s for U/U′ (G2-2, n = 40) and
  267 s for U2 (G2-3, n = 20)** (`wall_s` in `experiments/E8_scored_g2/results/G2-2`, `G2-3`).
- `INFERENCE`: with moves drawn uniformly, the mean is about 72 transitions and 244 s per episode. So 2×10⁵
  transitions take about 2,800 episodes, or **about 24 h per training seed on 8 workers**, before learner overhead.
  `DS:83` estimated about 8 h, counting window steps only.
- At that rate, 3 SAC seeds + 3 PPO seeds + the 20k prefill + the 50k pilot take roughly 6–7 days of machine time.
- Throughput step 4 (`DS:103`) must measure this. Open question Q5 offers an alternative (several moves per episode).

---

## 3. Action

### 3.1 Parametrisation (`PROPOSAL`): **6-D**, `a ∈ [−1, 1]⁶`
| Index | Name | Physical residual | Bound (`DECISION` D2) | Frame and sign |
|---|---|---|---|---|
| 0–2 | Δp | position setpoint offset | ±3 mm per axis | components along e1, e2, e3 of T; Δp_W = 0.003 · RBt @ a[0:3] (m) |
| 3–4 | Δθ | axis-direction setpoint tilt | ±2° per component | rotation vector v = (2° in rad)·(a[3]·e1 + a[4]·e2), right-handed |
| 5 | Δψ | J7 roll target offset | ±3° | positive = further in the move's commanded roll direction: Δq7 = s · (3° in rad) · a[5], with s = sign(A) = roll_sign · sign(delta) |

**Why 6-D and not 5-D:**
- The position residual is 3-D.
- The axis direction is a unit vector, so it has 2 degrees of freedom. G2's orientation impedance acts only on
  `er = a × a_d` (`TA:554`), which has no component along the axis. A rotation about the axis is J7's roll, which D2
  gives its own dimension.
- So 3 + 2 + 1 = 6. A third orientation component would be either unobservable to the impedance or a duplicate of Δψ.

**Why a rotation vector in e1/e2 (`PROPOSAL`):**
- It is linear near zero, symmetric, and exactly the identity at a = 0 (§3.3).
- Its components have fixed physical meanings in a frame that does not move with the cube or with J7.
- The alternative of two Euler angles has the same first-order behaviour but an order-dependent second-order term.

**Box or disk for the tilt (open question Q3):**
- The box above allows a combined tilt of up to 2√2·2° ≈ 2.83°.
- A disk (clip ‖v‖ ≤ 2°) matches "±2°" literally.
- The box is proposed for consistency with the per-axis ±3 mm box: ‖Δp‖ can likewise reach 5.2 mm.

**Why Δψ is signed by the move direction (`PROPOSAL`):** one policy serves U, U′ and U2. A positive Δψ means
"overshoot the commanded roll" and a negative one "lag it", for every move. s comes from the nominal `roll_sign`
(`TA:453`) and the commanded move only (C1).

### 3.2 Normalisation and clipping
- `action_space = Box(-1, 1, (6,), float32)`.
- The environment clips to [−1, 1] before scaling. A non-finite action raises an error and voids the episode.
- SAC's tanh-squashed output lies in (−1, 1) by construction. PPO's Gaussian output is clipped by the environment, and
  the clip count is logged.
- The bounds (3 mm, 2°, 3°) are stored in one constant block, logged in every record, and tuned only by the
  residual-bound pilot (`DS:64-65`).

### 3.3 How the residual enters G2's setpoints without editing G2 (`PROPOSAL`)
A subclass `G3TwoArm(TA.TwoArm)`, in a new file, overrides three methods. Nothing frozen is edited (C5).

1. **`impedance()`** saves `p_d` and `a_d` (`TA:473-474`). It sets
   `p_d ← p_d + Δp_W` and `a_d ← cos(θ)·a_d + sinc(θ)·(v × a_d)`, with θ = ‖v‖ and sinc(0) = 1, and no renormalisation.
   It calls `super().impedance()` (`TA:544-565`), then restores both in a `finally`.
   - At a = 0 this gives `p_d + 0.0` and `1.0·a_d + 1.0·0`: the same floats, so B0 is reproduced bit-identically (test
     E1).
   - The term k(k·a_d) of Rodrigues' formula vanishes because v ⟂ a_d. e1, e2 and e3 are orthonormal columns of RBt.
2. **`j7_control()`** saves `self.j7` (`TA:456`). It sets `self.j7[0] ← self.j7[0] + Δq7`, leaving the rate and
   acceleration feedforward nominal. It calls `super().j7_control()` (`TA:567-578`), then restores `self.j7`.
   - **Every G2 procedure variable stays nominal:** `roll_cmd()` (`TA:586-587`), the roll start (`TA:769`), the stall
     rule's lag (`TA:796`), the hold (`TA:806`), and the roll-back's start (`TA:813`).
   - This avoids the double-counting that an override of `set_roll` would cause at `TA:806`, where
     `set_roll(roll_cmd())` re-reads the command.
3. **`set_roll(q, qd, qdd)`** calls `super().set_roll(...)` unchanged. If it is called while a roll is in progress
   with qd = qdd = 0, it sets a **guard latch**.
   - In the roll loop qd ∝ sin(πk/n), which is never exactly 0 for k = 1…n (`TA:780-783`). A call with qd = qdd = 0
     inside the roll is therefore exactly G2's F/T freeze (`TA:794`) or stall freeze (`TA:802`).
   - The latch only reads `acc["rolling"]` (`TA:768`, `TA:804`), a controller flag.

**Consequences, stated before any data:**
- **The J7 residual and G2's stall rule (`INFERENCE`; open question Q2).**
  - The stall rule trips when |nominal command − J7 angle| > 2° for 20 ms during a roll (`TA:85`, `TA:796-803`).
    Under the scheme above, J7 tracks nominal + Δq7.
  - `FACT`: the largest J7 lag in the scored G2 moves without a guard stop is 0.070° (n = 404 moves, `j7_lag_max_deg`,
    `experiments/E8_scored_g2/results/`).
  - So during P5, a |Δψ| above about 1.9° held for 20 ms (40 physics steps, under half a policy interval) **trips G2's
    stall guard**. That is a guard stop and a move failure (`TR:175-176`). In effect the J7 bound is about ±1.9°
    during the roll and ±3° in P3, P4 and P6, where the stall rule is inactive.
  - This keeps G2's guard **at least as strict as in B0**: J7 cannot leave its nominal trajectory by more than 2°
    during a roll without a stop.
- **After a guard stop:**
  - Δq7 is forced to 0 from the freeze step to the episode's end. The policy can never push J7 past a freeze.
  - Δp and Δθ follow the P7–P8 schedule (§3.5). Zeroing them at once would step the setpoint by up to 3 mm, about
    12 N at K_P 4000 N/m (`TA:52`), on a closed gripper.
  - In training the episode terminates at once anyway (§5).
- **What reads the effective setpoint:** only the impedance and the J7 law. `TA.step`'s `track_err_mm` (`TA:711-712`)
  reads `self.p_d` outside `impedance()`, so it reports tracking error **relative to the nominal setpoint**. It is
  reported only, never judged (`PR:251-254`).

### 3.4 Action hold (`DECISION` D2; `PROPOSAL` for the mechanism)
- The policy is queried at window steps 0, 100, 200, …
- The action is a zero-order hold until the next query.
- The action computed from the observation at boundary k acts from the next physics step on. No computation delay is
  modelled; this is a stated limitation, and an optional one-interval delay ablation is listed.

### 3.5 Outside the window (`PROPOSAL`)
- **P0–P2:** the residual is exactly 0 and the policy is not called.
- **P7 (open + 0.3 s):** the last action is held.
- **P8 (roll-back, 1 s):** all components fall to 0 on a cosine ramp (Δq7 is already 0 after a guard stop). The
  gripper is open and the integral is active again. A smooth ramp avoids a setpoint step while the fingers are near the
  layer, so G2's roll-back check (≤ 1°, `PR:230`) stays meaningful.
- **After P8:** 0.

### 3.6 Zero residual = B0
- With a ≡ 0 the `G3TwoArm` trajectory is bit-identical to `TA.TwoArm`'s (test E1).
- **B1** (`PROPOSAL`): a ~ U[−1, 1]⁶ i.i.d. at every decision, from stream `[3, seed, 2]`. It is a negative control at
  the full bounds and the instrument of the bound pilot (`DS:64-65`).

### 3.7 Running G2's code path with the subclass (`PROPOSAL`; open question Q12)
- `TA.run` builds the arm through the module-level name `TwoArm` (`TA:854`), and `TR.run_seq` calls `TA.run`
  (`TR:187-194`).
- In the G3 worker process, which runs one environment per process (C4), the module attribute `TA.TwoArm` is bound to
  `G3TwoArm` at run time. The file is not edited.
- **Training and evaluation then both run G2's own `TR.run_seq`**, from configuration through `_seq_reasons`. The G2
  record, its `pass` and its `fail_reasons` come from G2's code (§6).
- **Gymnasium inversion of control (training):**
  - `TR.run_seq` runs in a worker thread of the environment process.
  - A read-only hook in `AuditedSim.hooks` (called after every physics step, `RIG:91-93`) hands control to the
    environment thread at each decision boundary. It sends the observation and blocks until the action arrives.
  - Exactly one thread runs at any time, so the run is deterministic.
  - Early termination raises a G3 exception in the simulation thread at the hook. `TA.run` catches only
    `NumericalFailure` and `EditAuditError` (`TA:898`), so the G3 exception propagates. The thread wrapper then calls
    `MagnetSystem.uninstall()`, which `TA.run` would otherwise skip (`TA:913`).
- **Evaluation:** the hook calls the policy synchronously; no thread is needed. The same hook code runs in both modes
  (test E19).

---

## 4. Observation

### 4.1 Actor observation (non-privileged only; `PROPOSAL`)
**Allowed sources (C1):**
- arm A and arm B joint `qpos` and `qvel` at their own addresses (`TA:417-419`);
- arm B gripper driver joint position;
- `d.sensordata` at the two F/T sensor addresses (`TA:239-241`, `TA:460-461`);
- the controller's own commands (`d.ctrl` of the arm actuators, `self.j7`, `p_d`, `a_d`, the commanded move, the
  schedule);
- the guard latch;
- time.

**Forbidden:** any cube joint, cube body pose or velocity, contact array, readout, or anything in `self.acc` except the
controller flag `rolling`. The phase comes from the schedule and the latch, so the actor does not even read that flag.

All normalisations are **fixed constants**; no running statistics. Every field is clipped to [−10, 10] after
normalisation and stored as float32.

| Field | Dim | Source and computation | Frame / units | Normalisation |
|---|---|---|---|---|
| Arm B joint position, J1–J6 | 6 | q − q at window start | rad | ÷ 0.05 rad |
| Arm B J7 angle | 1 | q7 − roll0 (`TA:455`), multiplied by s | rad | ÷ π/2 |
| Arm B joint velocity, J1–J7 | 7 | `qvel` | rad/s | ÷ 1 rad/s |
| Arm B commanded torque, J1–J7 | 7 | `d.ctrl[aB]`, the controller's own output | N·m | ÷ actuator ctrlrange limit |
| Gripper-base position error vs the **nominal** setpoint | 3 | p_d − x_B (forward kinematics), in T | mm | ÷ 3 mm |
| Axis error vs nominal | 2 | er = a × a_d (`TA:554`), components on e1 and e2 | deg | ÷ 2° |
| J7 following error vs nominal | 1 | s·(roll_cmd() − q7) | deg | ÷ 2° |
| Wrist F/T, mean of the 10 samples in the last interval, tared | 6 | (F_S, τ_S) + observation noise − tare | S; N, N·m | F ÷ 10 N, τ ÷ 0.5 N·m |
| Wrist peak \|τ_z\| in the last interval | 1 | max over the 10 noisy samples | N·m | ÷ 1.0 N·m (the stop, `TR:44`) |
| Arm B gripper aperture | 1 | driver joint angle | rad | ÷ 0.85 rad |
| Arm A joint position error, J1–J7 | 7 | ctrl − q (position servos, `PR:140`) | rad | ÷ 0.01 rad |
| Commanded move, one-hot | 3 | U, U′, U2 | — | — |
| Phase, one-hot | 4 | P3 close / P4 dwell / P5 roll / P6 hold, from the schedule and the guard latch | — | — |
| Elapsed fraction | 1 | window step ÷ window length (6,417 or 8,417) | — | [0, 1] |
| Nominal roll fraction | 1 | the cosine-ramp value (`TA:782`) of the nominal command, 0 before P5, 1 after | — | [0, 1] |
| Previous action | 6 | a_{k−1}; 0 at k = 0 | — | [−1, 1] |
| **Total** | **57** | | | |

**F/T sampling at 20 Hz (`PROPOSAL`):**
- At window steps that are multiples of 10 (200 Hz), the hook reads the 6-axis sensor and adds noise from the
  environment's own stream `[3, seed, 1]`:
  - torques: N(0, 0.01 N·m) per axis, as G2 models τ_z (`PR:88`);
  - forces: N(0, σ_F) per axis, with σ_F = 0.1 N as an `ASSUMPTION` (G2 modelled no force noise; open question Q7).
- The observation gives the **mean** of the 10 samples in the interval (a box anti-aliasing filter that a real 200 Hz
  sensor stream allows) and the **peak** |τ_z|.
- **Tare:** the mean of the last 10 samples of P2, before contact.
- No gravity compensation: the actor has the J7 angle, so it can learn the gripper's weight term (open question Q7).
- **The environment never draws from `TwoArm.ft_rng`** (`TA:457`). G2's guard noise sequence, and with it B0, stays
  bit-identical (test E1). The guard keeps its own samples and stop rule, unchanged.

**Disclosed abstractions:**
- Commanded joint torques are the torque-level B0 abstraction (P-134). A real xArm reports estimated joint torques
  instead.
- No sensor delay, bias drift or bandwidth limit (as `PR:477-478`).

### 4.2 Critic-only (privileged) observation (`PROPOSAL`; training only)
The critic receives the actor fields **plus** the fields below. They come from the simulator, through the same
functions G2's checks use (`RO.poses`, `RO.rotation_about_deg`, `TA.rel`, `TA.tips_cubie_force`, `TA.tool_torque`,
`self.acc`).

| Field | Dim | Source | Units | Normalisation |
|---|---|---|---|---|
| Layer angle φ, U members fixed at the move start, relative to the core, **unwrapped** by summing per-interval increments | 1 | mean of `rotation_about_deg(r0, r, members, U)` (`TA:753-755`, `TA:827`) | deg | ÷ \|φ*\| (90 or 180) |
| Remaining turn φ* − φ | 1 | φ* from `TA:826` | deg | ÷ \|φ*\| |
| Layer rate relative to the core about U | 1 | mean member `cvel` minus core, as in `TA:697-698` | deg/s | ÷ 90°/s |
| Largest non-target drift about U | 1 | as `TA:829-830` | deg | ÷ 1° |
| Core slip relative to arm A since the move start | 3 | `rel()` difference (`TA:737-740`, `TA:848`) | mm, in A | ÷ 1 mm |
| Core rotation relative to arm A since the move start (rotation vector) | 3 | `TA:849` | deg, in A | ÷ 2° |
| Fingertip–cubie normal force of arm B | 1 | `tips_cubie_force` (`TA:643-654`) | N | ÷ 20 N |
| Fingertip torque on the layer about its axis | 1 | `tool_torque` (`TA:665-683`) | N·m | ÷ 0.5 N·m |
| Largest cubie and pad penetration so far | 2 | `acc` (`TA:688-691`) | mm | ÷ 0.5 mm |
| Latched judged-contact flags | 6 | `acc` keys of `CONTACT_KEYS` (`TA:106`) | 0/1 | — |
| Core offset from nominal at t0 | 3 | `start` (`TA:528`); the vector, from `info["cube_centre"]` | mm | ÷ 3 mm |
| Stress parameters | 5 | pad μ, grip, \|extra offset\|, U-face misalignment, insertion error | various | fixed ranges to [−1, 1] |
| Largest magnet near-pair tilt | 1 | `MagnetSystem.stats` (`TA:606-610`) | deg | ÷ 5° |
| **Total extra** | **29** | | | |

**Wiring (`PROPOSAL`):**
- The observation space is `Dict({"actor": Box(57), "critic": Box(29)})`.
- The actor network takes only `"actor"`. The critic, the Q-networks for SAC and the value network for PPO, take the
  concatenation.
- SAC needs separate actor and critic feature extractors (`share_features_extractor=False`) and a custom extractor that
  selects keys.
- `INFERENCE`, not verified in this session: Stable-Baselines3's SAC policy supports separate extractors. This must be
  checked against the pinned version when SB3 is introduced.

---

## 5. Reward

### 5.1 Terms (`PROPOSAL`; weights to be fixed by the B0/B1 pilot before the pre-registration)
At each decision k, after its physics interval:

r_k = w_prog·(P_{k+1} − P_k) − w_slip·(S_{k+1} − S_k) − w_rot·(Θ_{k+1} − Θ_k) − w_drift·(D_{k+1} − D_k)
      − w_ft·max(0, (τ̂_peak,k − 0.5)/0.5) − w_a·‖a_k‖²/6 − w_Δa·‖a_k − a_{k−1}‖²/24 + 1[terminal]·R_end

| Term | Observable (source) | Definition | Proposed weight | Why it cannot be gamed (RS §6, `RS:52-60`) |
|---|---|---|---|---|
| Progress P | Physical layer angle relative to the **core**, members fixed at the move start (critic field; `TA:827`) | P = 1 − min(\|φ* − φ\|/\|φ*\|, 2) ∈ [−1, 1]; 0 at the start, 1 at the target | 1.0 | Reads cubie poses, not J7 or a command, so a J7 roll that slips on the pads earns nothing (RS §6.1). Turning the whole cube changes nothing relative to the core (§6.4). Overshoot lowers P. Rotation of another layer earns nothing and is caught by drift and the oracle (§6.2) |
| Slip S | Core position relative to arm A's gripper since the move start (`TA:848`) | S = \|Δp_core\| / 1 mm (`TR:36`) | 0.5 | A potential difference, so it sums to the move's final slip, which is exactly what G2 judges. It cannot be cancelled by other terms |
| Rotation Θ | Core rotation relative to arm A's gripper (`TA:849`) | Θ = angle / 2° (`TA:105`) | 0.5 | As S; the arm cannot rotate the cube and claim progress (§6.4) |
| Drift D | Largest rotation of non-target cubies about U (`TA:829-830`) | D = drift / 1° | 0.5 | Penalises adjacent-layer motion (§6.2) |
| F/T peak | The **measured** peak \|τ_z\| (actor field) | zero below 0.5 N·m; linear up to the 1.0 N·m stop | 0.05 | A robot-side measurement of the real wrist load; it cannot be lowered without lowering the load |
| Action size | a | ‖a‖²/6 | 0.01 | Keeps the residual at 0 unless it helps (the no-harm concern, U07 in the literature update, `G3_RL_LITERATURE_UPDATE:71`) |
| Smoothness | a_k − a_{k−1} | ‖Δa‖²/24 | 0.01 | Limits 20 Hz setpoint chatter, up to about 12 N steps at K_P 4000 |
| **R_end** (terminal) | **G2's classification** of the episode's one-move record (§6) | +5 if `pass`; −5 otherwise, including early termination (§5.2) | 5 | The bonus comes only from G2's oracle, turn error, drift, roll-back, causality, drive, contacts, integrity and magnet checks, after the roll-back (RS §6.1, §6.3, §6.5) |

**Notes:**
- **No time or energy term.** Timing is not learned (D2): the schedule is fixed, so time is not a lever. Arm B's
  ∫‖τ‖²dt is **reported** as a metric, not rewarded (open question Q8).
- The final step evaluates P, S, Θ and D at the move's end, after the roll-back. G2 measures turn error and drift
  before the roll-back (`TA:811`, `TA:827-830`) and slip and rotation after it (`TA:831`). The shaping terms are
  guidance only; **success is G2's classification**.
- **The potentials telescope.** A mid-move excursion of slip that returns costs nothing, exactly as G2 judges only
  end-of-move values. The mid-move peaks are reported (open question Q8).
- **U2 unwrap.** φ is accumulated from per-interval increments, each wrapped to (−180°, 180°], so P is continuous
  through ±180° (test R4).
- `INFERENCE`: a typical B0 return is ≈ 1 + 5 − 0.5·(0.10 + 0.15 + 0.15) − small ≈ 5.8, from the pilot-4 and scored
  values (`PR:69-82`). A failed episode returns ≤ about −4.
- **Credit.** The reward does not subtract B0's progress. Residual RL credits the composite controller, and the
  comparison with B0 is made at evaluation on matched starts (D5). Arm A, the "opponent arm" of RS §6.4, is
  position-servoed (`PR:140`) and cannot roll the layer. Any whole-cube rotation is penalised by Θ and earns no P.

### 5.2 Anti-hacking map (RS §6) → tests in §8
| RS §6 item | How the contract handles it | Test |
|---|---|---|
| Command issued, face does not turn: no completion reward | R_end needs G2's oracle and turn error ≤ 2°; P reads cubie poses | R2, H1 (jam) |
| Adjacent layer turns illegally: failure | Drift ≤ 1°, oracle, two-layer detection; D penalty | H2 (two_layer) |
| Teleport or constraint snap: failure | `AuditedSim` edit audit (`RIG:75-83`) and model audit (`TA:134-192`) → `aborted` → failure; the environment has no state setter | H5, H6, E16 |
| Opponent arm does the turn: no spurious credit | P is relative to the core; Θ penalty; arm A is a position servo | R3 |
| Solver or simulator state set to solved: no success | No API writes cube state; success comes from physical poses → oracle; static scan for writes to audited arrays (`RIG:20`) | H6 |
| Collision or unrealistic friction exploited | Every G2 contact check is terminal (§5.3); pad penetration and fingertip impulses reported; μ fixed per condition; evaluation is in full M7 only (`DS:29-30`) | H4, the evaluation audit |
| Every reward term has a measured observable, scale and test | The table above | R1–R7 |

### 5.3 Termination and truncation (`PROPOSAL`)
The environment checks the conditions below at every decision boundary, from latched G2 accumulators.

**Rule:**
- **Training** terminates on any condition that makes G2's failure **certain**.
- **Evaluation** never stops early. It runs the move to its end with the policy acting (Δq7 latched to 0 after a guard
  stop, §3.3), so G2's full record and classification exist for every held-out start.

| ID | Condition | Source | Certain G2 failure? | Gymnasium flags (training) |
|---|---|---|---|---|
| T1 | Edit-audit violation | `EditAuditError` (`RIG:76-83`), caught by `TA.run` → `aborted` (`TA:898-899`) | yes (`TR:104-107`) | terminated, R_end = −5, `invalid` flag |
| T2 | Numerical failure | `NumericalFailure` (`RIG:85-90`) | yes (`TR:108-109`) | terminated, −5, `invalid` flag |
| T3 | A step without the magnet force, or an uncounted step | `mag_missing > 0`, or `mag_steps ≠ sim.steps` (`TA:596-600`, `TA:607-608`) | yes (`TR:116-120`) | terminated, −5, `harness_fault` flag (the run is investigated) |
| T4 | A judged contact: non-fingertip robot–cube, arm–arm, robot–table, robot–stand, robot–block; cube–stand after the drop | latched `acc` maxima (`TA:688-693`) | yes (`TR:93-99`, `TA:884-888`) | terminated, −5 |
| T5 | Cubie–cubie penetration > 0.5 mm | `acc["pen_cubie"]` (`TA:690-691`) | yes (`TR:41`, `TA:883`) | terminated, −5 |
| T6 | Guard stop (F/T or stall) | the guard latch (§3.3) | yes (`TR:175-176`) | terminated, −5 |
| T7 | The magnet force law outside its validated range: tilt > 5° or a near-perpendicular pair | `MagnetSystem.stats` (`TA:606-610`) | yes (`TR:124-134`) | terminated, −5 |
| T8 | Harness exception, including the magnet-availability `Refused` (`TR:50`) | thread exception | **not a trial result** (G2 treats `Refused` as an interruption) | truncated, episode void, logged |
| T9 | Wall-clock watchdog (> 5× the measured median episode time) | environment | — | truncated, void, logged |
| — | **Natural end:** after the roll-back, `TR.run_seq` returns the record | §6 | pass or fail | **terminated** (the task ends; no bootstrap), R_end = ±5 |
| — | Pre-window failure: start contacts, pre-t0 limits, approach contacts (`TR:168-170`), known at the window start | `start`, `approach` | yes, and independent of the policy | training: no transitions; the start is logged as void and the next seed is drawn. Evaluation: a failure for **every** arm (a concordant pair) |

**Not terminal:**
- Per-move slip > 1 mm or rotation > 2° part-way through a move. G2 judges these at the move's end (`TA:848-849`), so
  a mid-move excursion does not make failure certain. They are penalised through S and Θ.
- No time-limit truncation is needed: the schedule fixes the episode length (§2.3).

---

## 6. Success classification at evaluation (unchanged G2)
- A G3 episode **succeeds** iff the record from `TR.run_seq(move, overrides, start)` (`TR:187-194`), run with
  `TA.TwoArm` bound to `G3TwoArm` (§3.7), has `pass = True`.
- `pass` is `not TR._seq_reasons(rec, 1)` (`TR:163-184`), which requires all of the following:
  - **integrity:** no abort, edit-audit violation, numerical failure or harness exception; a clean model audit; the
    magnets at every step, with `steps = sim_steps = round(sim_time/dt)` (`TR:102-121`);
  - **magnet validity:** tilt ≤ 5°, no near-perpendicular pair (`TR:124-134`);
  - the cube solved at t0;
  - start-sequence contacts, the pre-t0 limits (stand-drop shift ≤ 1 mm, t0 offset ≤ 3 mm) and approach contacts
    (`TR:137-146`, `TR:168-170`);
  - the move recorded;
  - every per-move `ok_*` (oracle, turn error ≤ 2°, drift ≤ 1°, cubie penetration ≤ 0.5 mm, contacts, drive,
    roll-back, core rotation ≤ 2°, causality; `TA:880-892`), no guard stop, core slip ≤ 1 mm;
  - the final state equal to the oracle;
  - the trial-level checks: total slip ≤ 2 mm, rotation ≤ 2°, every cubie's end misalignment ≤ 4° (`TR:149-160`).
- The verdict code must also recompute `pass` independently from the stored record, as G2's `analyze.py` does
  (`PR:189-190`). The G3 pre-registration will specify this.
- **Open question Q6:** offsets in S that push the t0 offset past 3 mm fail G2's pre-t0 limit **whatever the policy
  does**. D24's `analyze.py` reports a separate `turn_ok` that ignores those limits (`D24 analyze.py:1-5`). Exact G2
  success (C6) needs S to keep the t0 offset ≤ 3 mm. Otherwise the user must approve a G3-specific classification that
  excludes the pre-t0 limits, and it must be named as such.

---

## 7. Seeds and splits (`PROPOSAL`)
**Used ranges (`FACT`, from a search of every tracked `.md` and `.py` for 5-digit ranges):**
- start seeds 10000–21003 (G1 era);
- 29000–29999 (pilot space; the specific blocks used run 29001–29779, and D24 uses 29700–29779, `stress_map.py:33`,
  `:66`);
- 30000–30999 (G2 scored, P-141).
- Derived offset streams: +500000 (`TR:62`), +700000 and +800000 (D24).
- Nothing at 40000 or above is used as a start seed.
- `INFERENCE`: a search of text is not a search of every record. The G3 pre-registration must repeat P-141's
  scored-seed search over records and results before its freeze.

| Block | Seeds | Use | Rule |
|---|---|---|---|
| G3 development | **29800–29999** | unit tests (§8), the residual-bound pilot (B1), throughput (`DS:103-104`), pilot debugging | the last unused part of the pilot space; never in a reported comparison |
| Training starts | **100000–199999** | every training episode: environment i ∈ {0…7}, its j-th episode uses seed 100000 + 8j + i; the **same start sequence** for every training run (SAC and PPO, all learner seeds), so the training distribution is matched | far from every used range; about 3,000 episodes per run leaves room for 30 runs |
| B0 replay prefill | **190000–190999** | the ≈ 20k B0 transitions (≈ 280 episodes) of D4 | a fixed, disjoint sub-block, so the prefill is identical for every SAC run |
| Validation | **40000–40999** | learning-curve monitoring at checkpoints (25k, 50k, 100k, 200k; `DS:82`) | **no checkpoint selection on it**: the evaluated policy is the pre-registered final checkpoint (200k), so validation cannot leak into the result |
| **Held-out evaluation bank** (stress region from D24) | **41000–41999** | B0, B1, B2 and B3 on identical starts (D5) | untouched until the scored evaluation, as 30000–30999 was for G2 |
| **No-harm bank** (G2's start distribution, no stress) | **42000–42999** | B2 and B3 must not fall below B0 (D5) | G2's start distribution on **new** seeds; G2's scored seeds 30000–30999 are **not reused** |
| Reserve | 43000–49999 | future G3 re-evaluations or G4 | unassigned |

**Why 40000 or above for evaluation:**
- It sits clear of every used start seed: the highest is 30999.
- The prefix is visually distinct, so a held-out seed in a training log is easy to spot.
- It leaves G2's scored seeds independent.

**Seed guards (`PROPOSAL`, as `TA:954`):** the training environment refuses seeds in 40000–49999. The evaluator refuses
seeds outside 41000–42999.

**Learner seeds** (the RNG of SB3, PyTorch and NumPy) are separate integers: 0, 1, 2, and 3, 4 if affordable. They are
logged with every checkpoint (`RS:84`).

---

## 8. Unit tests required before any training (`PROPOSAL`)
**Run rules:**
- Every test runs on development seeds 29800–29999.
- The scene tests require the robot model, as G2's do, and run with `G2_REQUIRE_SCENE=1` so a skip fails (P-138).
- No test edits a frozen file. Test X1 checks this.

### Environment and action
| ID | Test | Property checked |
|---|---|---|
| E1 | **B0 bit-identity.** For U, U′ and U2 on a development seed: G2's unmodified `TR.run_seq` vs the G3 path with a ≡ 0 (both the Gymnasium thread path and the evaluation path), with every observation hook active | every record field identical except `wall_s`, including `final_qpos_sha256` (`TA:909`), every per-move value and the magnet counts. Positive control: a ≡ 0 except one component at 1e-6 at one decision changes the hash |
| E2 | Pre-window identity | for random actions, the state hash at the first window step equals B0's: the residual cannot act before P3 |
| E3 | Bounds and clipping | a = ±1 gives exactly ±3 mm, ±2° per component and ±3°; values beyond [−1, 1] are clipped; NaN or inf raises and voids the episode |
| E4 | Frames and signs | +1 on a[0], a[1] or a[2] moves the effective `p_d` by +3 mm along e1, e2 or e3 in W. +1 on a[3] rotates `a_d` right-handed about e1. +1 on a[5] moves the effective J7 target further in the commanded roll direction for U **and** U′ |
| E5 | Hold and decision count | the policy is called exactly at window steps 0, 100, …; 65 (U, U′) and 85 (U2) calls, or the exact counts measured and recorded; the residual is constant between calls |
| E6 | Outside the window | the residual is 0 in P0–P2; held in P7; cosine to 0 over P8; 0 after |
| E7 | Guard latch | jam configuration (`JAM_BLOCK`, `TA:102`) with a ≡ +1: the latch fires on the same physics step as G2's freeze (`TA:794`); from then on Δq7 = 0. In a normal roll the latch never fires |
| E8 | Stall interaction (Q2) | a constant Δψ of 2.5° in P5 trips G2's stall guard; 1.5° does not. This measures the effective bound |
| E9 | Determinism | the same seed and action sequence give identical records twice in one process and across two processes |
| E10 | One environment per process | building a second scene in the process is refused (C4; P-130) |

### Observation
| ID | Test | Property checked |
|---|---|---|
| O1 | **Actor output is independent of privileged input** | with the critic fields replaced by random values (and by NaN), the actor's deterministic action is bit-identical. Positive control: the Q-value changes |
| O2 | **The actor observation contains no cube state** | the actor builder runs on a recording proxy of `MjData` and `TwoArm`. It touches only the whitelisted arrays and indices (§4.1): no cube joint address, cube body pose, `contact`, readout or `acc` key |
| O3 | **Cube scramble** (as `test_controllers_ignore_cube_state`, `tests/test_scored_g2.py:665`) | scrambling every cube joint state in a copy of the data leaves the actor observation bit-identical. Positive control: the critic observation changes |
| O4 | Shapes and ranges | `Dict` shapes (57, 29), float32, finite, inside the clip range over B0 rollouts on 3 development seeds × 3 moves |
| O5 | Pose-error frame | a known arm displacement gives the expected sign and size of the T-frame error |
| O6 | F/T stream | the 20 Hz mean equals the mean of the 10 samples of that interval; the tare equals the P2 mean; the noise σ is 0.01 N·m (χ² check); `TwoArm.ft_rng`'s state is unchanged by the environment (also covered by E1) |
| O7 | Phase and fraction | the phase one-hot follows §2.2 on the nominal schedule and moves to hold after a guard latch |

### Reward
| ID | Test | Property checked |
|---|---|---|
| R1 | Progress telescopes | ΣΔP over an episode = P_end − 0 for synthetic angle sequences |
| R2 | **No turn, no reward** | a layer held still while J7 rolls (synthetic, and the jam scene) gives ΣΔP ≈ 0 and no bonus |
| R3 | **Whole-cube rotation earns nothing** | synthetic poses with core and every cubie rotated together give ΔP = 0, and Θ grows |
| R4 | U2 unwrap | a synthetic −170° → −190° step gives ΔP > 0 and continuity |
| R5 | Slip, rotation and drift potentials | their sums equal the final values ÷ limits |
| R6 | F/T penalty | 0 at ≤ 0.5 N·m; linear to 1 at 1.0 N·m |
| R7 | **The bonus only from G2** | a passing G2 record → +5. Records that each fail **exactly one** `ok_*` check, the guard stop, the core slip, the oracle, an integrity item, the magnet counter or the magnet validity → −5 each |

### Anti-hacking and termination (RS §6)
| ID | Test | Property checked |
|---|---|---|
| H1 | Jam scene | guard stop → T6, −5, no bonus |
| H2 | Two-layer scene (`TR:248`) | failure, no bonus |
| H3 | Open mid-turn scene (`TA:95`) | no bonus |
| H4 | Collision scene (`TR:250`) | T4 terminal |
| H5 | Edit audit | a test hook that writes `qpos` mid-episode → `EditAuditError` → T1, `invalid`, no bonus |
| H6 | No state setter | an AST scan of every G3 module finds no write to the audited arrays (`RIG:20`: qpos, qvel, act, eq_active, xfrc_applied, qfrc_applied, mocap_pos, mocap_quat) and no `mj_resetData`, `mj_setState` or `mj_forward` call on the simulation's data |
| T-all | Each of T1–T9 | the right `terminated` / `truncated` flags, R_end and `info["end_reason"]`; evaluation mode runs to the move's end in every case |

### Integrity and wiring
| ID | Test | Property checked |
|---|---|---|
| M1 | **Magnet counter still enforced** | normal episodes have `steps_without_magnet_force = 0` and `steps = sim_steps = round(t/dt)`. Positive control: uninstalling the callback mid-episode (the P-130 failure) → T3 and a failed classification |
| E16 | Model audit | the G3 scene's `model_audit` is clean and identical to G2's; the subclass adds no model element |
| E17 | Classification identity | the environment's success equals `TR._seq_reasons(rec, 1) == []` on the same record; G2's tests still pass at HEAD |
| E18 | Seed guards | training refuses 40000–49999; the evaluator refuses everything outside 41000–42999 |
| E19 | Same hook, both modes | for a fixed action sequence, the Gymnasium path and the evaluation path give identical records |
| P1 | Zero-initialised residual | a freshly built SAC (and PPO) policy's deterministic action is exactly 0, so its first evaluation equals B0 (E1) |
| P2 | Asymmetric gradients | the actor loss's gradient with respect to the critic-only inputs is exactly 0 |
| P3 | Prefill | the prefill transitions have a = 0 and match E1's B0 trajectories at the decision points |
| X1 | Frozen files untouched | `git status --porcelain` over `run.FROZEN_PATHS` is empty |

---

## 9. Open questions for the user
1. **Q1 Window.** The residual acts from the start of closing to the open command (P3–P6), is held in P7 and ramped out
   in P8. Approve, or include P2 (settle) and P1 (approach)?
2. **Q2 J7 residual and the stall rule.** The proposal keeps G2's stall rule on the nominal command. The effective J7
   bound is then about ±1.9° during the roll (more trips the guard) and ±3° outside it. Accept this? The alternative is
   to reduce the J7 bound to ±1.5–2°. Measuring lag against the effective command would need a change to frozen code,
   so it is not proposed.
3. **Q3 Axis bound.** A per-component box ±2° (combined tilt up to 2.83°) or a disk ‖tilt‖ ≤ 2°?
4. **Q4 Action hold.** Pure zero-order hold (D2), or linear interpolation within each 50 ms interval to avoid
   setpoint steps of up to about 12 N? The smoothness penalty is proposed either way.
5. **Q5 Episode length and budget.** One move per episode spends 69 % of the physics outside the window. A training seed
   then takes about 24 h on 8 workers, not about 8 h (§2.4). Keep one move per episode, or run k moves per episode
   (random U-family, the policy acting in each window, as G2-4 runs sequences)? Or decide after the throughput
   measurement?
6. **Q6 Start distribution vs exact G2 success.** Must S keep the t0 offset ≤ 3 mm so that G3 success is exactly G2
   success? Or should G3 use D24's `turn_ok` (without the pre-t0 limits), named as a G3-specific criterion?
7. **Q7 F/T model.** Force noise σ_F = 0.1 N (`ASSUMPTION`; G2 modelled τ_z noise only). Tare only, or also the
   gripper payload's gravity compensation?
8. **Q8 Reward.** Approve the weights as starting values to be set by the B0/B1 pilot: progress 1, terminal ±5, slip,
   rotation and drift 0.5, F/T 0.05, action and smoothness 0.01. Should there also be a non-telescoping penalty on
   mid-move peak slip? Energy reported only?
9. **Q9 Arm A in the actor.** Include arm A's joint position errors? They are real-robot signals that carry the cube's
   load.
10. **Q10 Checks in training.** Keep every G2 check on in training (about 10 % of the step, `PHASE_3_READINESS:71-73`),
    so training and evaluation share the same semantics? (Proposed: yes.)
11. **Q11 Seeds.** Approve the blocks in §7, including the matched training start sequence and the rule "evaluate the
    final 200k checkpoint, no selection on validation".
12. **Q12 Run-time substitution.** Bind `TA.TwoArm` to the subclass inside the worker process, so both training and
    evaluation run G2's own `run_seq` and classification? No file is edited. The alternative, a copy of `TA.run` in G3
    code, duplicates G2's per-move checks and is not proposed.
13. **Q13 B1.** i.i.d. uniform at every decision (proposed), or one random constant residual per episode?
14. **Q14 Termination asymmetry.** Training stops early on certain failure; evaluation runs every move to its end.
    Approve?

## 10. Limitations of this contract (to carry into the G3 pre-registration)
- Simulation only. B0's torque-level control and the commanded-torque observation are abstractions the real xArm
  cannot run (P-134).
- No sensor latency, bias drift or bandwidth limit. No policy computation delay.
- G2's guard noise is one stream restarted in every episode (`TA:457`; `PR:477-478`). It is kept for B0 bit-identity,
  so false-stop risk is correlated across episodes.
- The layer angle has no camera source before G5. The actor is evaluated without it, and its J7 angle is the only proxy
  (D3).
- The stress distribution, the bounds and the reward weights are not yet set. They depend on D24, the bound pilot and
  the B0/B1 pilot.
