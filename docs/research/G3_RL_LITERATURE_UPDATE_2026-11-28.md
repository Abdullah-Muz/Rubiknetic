# G3 literature update: residual RL budgets, surrogate simulators, CPU throughput, evaluation statistics

**Date:** 2026-11-28 · **Status:** literature review only. Nothing here is a `VALIDATED_RESULT`. No simulation was run,
no specification or decision was changed, and every `PROPOSAL` needs the user's approval. It builds on
[`CONTACT_AND_RL_FINDINGS.md`](CONTACT_AND_RL_FINDINGS.md) (2026-11-19, with its 2026-11-28 addendum) and does not
repeat its sources (S50, S51, L01–L34, C01–C21). It answers four questions raised by
[`PHASE_3_READINESS_2026-11-28.md`](PHASE_3_READINESS_2026-11-28.md) and the D19 speed study
([`../../experiments/D19_speed_study/README.md`](../../experiments/D19_speed_study/README.md)).

**How it was made.** One session, no subagents. Every source below was opened by this session (web search, then a
fetch of the arXiv abstract page, the HTML full text, or the official documentation page). The fetch tool returns a
model-written summary of the page, so "full text" means the HTML full text was read **through a summarising fetch**,
and short quotations are as that tool returned them. Pages longer than about 100,000 characters were read only in part
(marked "partial"). Access date for all sources: 2026-11-28 (UTC; the machine clock read 2026-11-27 19:45 PST).

**Tags:** `FACT` (stated in the source, at the verification level in §7), `INFERENCE` (this review's reasoning),
`PROPOSAL` (a suggestion for the user). **Nothing is generalised to cube turning without an `INFERENCE` tag.** Source
IDs U01–U33 are new and listed in §7.

**Project numbers used below** (`FACT`, from D19 and the readiness check, not from the literature): full two-arm M7
control step ≈ 159 physics steps/s in one quiet process (0.08× real time, 0.5 ms timestep); about 1.6 policy steps/s at
20 Hz; pilot 4 ran 8 workers at a median of 0.043× real time each; NoSlip ≈ 80 % of `mj_step`, the Python magnet
callback ≈ 16–20 % of the full step, the judged checks ≈ 10 %; NoSlip 0 makes bare `mj_step` 5.3× faster; NoSlip 5
or solver iterations 50 change almost nothing.

## Summary
1. **Off-policy residual RL on a frozen base now reaches high success in 10⁴–10⁵ steps in simulation, when the critic
   is stabilised.** ResFiT (U02) reports convergence on a simulated task in about 75k steps and 200k versus 40M steps
   for PPO on another; critic LayerNorm was "crucial". DAWN (U01) attributes slow residual learning to value
   learning, fixes it with base-policy warm-up data plus critic normalisation, and reports about 5× faster convergence
   than prior methods that "require over a million online interactions" (`FACT`).
2. **Recent residual-over-classical-controller results confirm the pattern of the earlier review: the gain is where the
   nominal controller fails, and a residual can make a near-perfect base worse.** Book insertion on an xArm7 (U06):
   nominal 37.89 % → residual 98.50 % in simulation, 26.7 % → 63.3 % on hardware, but with PPO and 30M transitions.
   Tight insertion (U07): a plain residual dropped one object class from 97.55 % to 82.37 % at zero noise (`FACT`).
3. **No study was found that trains with a cheaper MuJoCo solver setting (NoSlip, iterations) and measures the policy
   under the reference setting.** The closest evidence is cautionary: agents exploited simulated wall-sliding and the
   sim-to-real correlation was 0.18 until sliding was removed (U14); MuJoCo slip artefacts and "traction tuning"
   changed measured tracking quality (U18); source-domain performance "is not a reliable indicator" of target-domain
   performance (U13) (`FACT`).
4. **MuJoCo 4.0.1 has a native closed-loop batch API (`mujoco.batch.Batch`, added in 3.17.0) as well as
   `mujoco.rollout`, but both need physics callbacks written in C.** A Python callback "holds the Global Interpreter
   Lock while it runs, which serializes the batch's threads" (U21). The project's magnet force is a Python
   `mjcb_passive` callback, so it blocks these APIs until it is ported (`FACT` + `INFERENCE`).
5. **No published measurement of MuJoCo thread or process scaling on 8–16 cores for a scene like M7 was found.** The
   only 16-thread number found (U24) is for small standard models at saturation, with no scaling curve. Q5 of the
   earlier review (measure scaling here) remains the only reliable source.
6. **Evaluation statistics: with 3–10 training seeds, interval estimates are needed but bootstrap intervals over seeds
   are not trustworthy** (U31: "at least 100" seeds per algorithm–environment pair for benchmark aggregates). Paired
   per-condition comparisons on a fixed bank of held-out start conditions, with an exact McNemar test (as in U06) and
   reporting every seed, fit G3 better than IQM over seeds (`INFERENCE`).
7. **Implication for G3 (`INFERENCE`):** if the pilot-4 aggregate rate (≈ 6.9 policy steps/s on 8 workers) holds, a
   200k-step SAC run takes about 8 h on full M7, so **an off-policy budget of 10⁵–2×10⁵ steps per seed does not need
   a NoSlip-off surrogate.** A surrogate becomes necessary only for PPO-scale budgets, and by Amdahl's law it would give
   about 2.3–2.6× on the full control step (about 3× with the judged checks sampled), not 5.3×, unless the magnet
   callback is also compiled.

## 1. Q1: residual RL for contact-rich manipulation, 2024–2026
### 1.1 Residual RL on frozen base policies (`FACT`)
| ID | Task, base and method | Budget and result |
|---|---|---|
| U01 DAWN (2026) | ManiSkill (PegInsertionSide, TurnFaucet, PushChair) and Adroit; frozen Diffusion Policy or BeT base; SAC residual, bounded by a scale λ ≈ 0.1 | Prior methods "require over a million online interactions". DAWN converges "approximately 5× faster" (aggregate); PegInsertionSide reaches 90 % "approximately 6× faster than Policy Decorator". Default warm-up of 20K base-policy transitions; PegInsertionSide "failed entirely" without warm-up. Critic LayerNorm default; distributional critics (C51, QR, TQC) gave no gain; actor normalisation did not help. 8 seeds, 95 % CIs |
| U02 ResFiT (2025, ICLR 2026) | Robomimic Can, Square; DexMimicGen BoxCleanup, CanSort, Coffee; 20 Hz control; frozen BC base; TD3-style off-policy residual with ensembled double Q, n-step 3, UTD > 1, 50/50 demo/online sampling | Can: ≈ 75k steps (baselines ≈ 150k). Square: > 90 % within 150k. BoxCleanup: "200k steps versus 40M steps" for PPO. UTD 4 captures "most of the benefit". Critic LayerNorm "crucial". Real humanoid: 14 % → 64 % (≈ 15 min), 23 % → 64 % (≈ 76 min). Seed count not reported |
| U03 Res-HIL (2026) | Five contact-rich real tasks; frozen imitation base, zero-initialised residual, human interventions | Beats baselines "after ten minutes of online training" (abstract only; no success numbers seen) |
| U08 HIL-SERL (2024) | Real precision assembly and dexterous tasks; human-in-the-loop off-policy RL (not residual) | Near-perfect success "within just 1 to 2.5 hours of training" (abstract) |

### 1.2 Residual RL on classical or model-based controllers (`FACT`)
| ID | Task, base and method | Budget and result |
|---|---|---|
| U06 Book insertion (2026) | Isaac Lab, Franka in sim, **real xArm7**; nominal task-space controller + bounded residual PPO (SB3 2.8.0), 256 envs; 60 Hz control in sim, 20 Hz policy on the xArm via its "Servo/velocity layer" | Final checkpoint at 30M transitions. Sim: 98.50 ± 0.23 % (3 training runs, 512 fixed conditions) vs nominal 37.89 %. Real: 26.7 % → 63.3 %, 30 matched conditions, 60 trials, exact McNemar p = 0.0074. Per-step residual: 1–2 mm, 0.30–0.35° |
| U07 Tight insertion (2025) | IsaacGym; potential-field controller + PPO residual, asymmetric actor–critic | "2–3 hours using a single GPU". Base vs base+residual (5 seeds): left objects at 5 mm/5° noise 3.28 % → 97.66 %; middle objects at 0 noise **97.55 % → 82.37 %** (residual worse), at 5 mm/5° 46.51 % → 61.09 ± 45.18 % |
| U05 CG-RL (2026) | Simulated oblique insertion; RL outputs residual motion, rate and a gain that the controller clamps | 85.8 ± 7.7 % vs fixed-gain 50.1 % (5 training seeds). Training budget not stated in the abstract |
| U04 SHaRe-RL (2025, ICRA 2026) | Real connector insertion, 0.2–0.4 mm clearance; manipulation primitives + human-in-the-loop off-policy RL + per-axis compliance bounding forces | "within practical time budgets" (abstract; no numbers seen) |

### 1.3 Sample-efficient off-policy learners (`FACT`; all on standard benchmarks, none on contact-rich residuals)
- **U09 CrossQ (ICLR 2024):** batch normalisation in the critic, no target networks, UTD 1; matches or beats REDQ and
  DroQ (UTD 20) with much less computation (abstract).
- **U10 BRO (NeurIPS 2024):** a larger, strongly regularised critic plus optimistic exploration; 1M environment steps,
  10 seeds, replay ratio 10 (BRO) or 2 (BRO Fast); IQM with 95 % CIs from rliable; timing on one A100 GPU plus 8 CPU
  cores.
- **U11 SimbaV2 (ICML 2025):** SAC with hyperspherical normalisation and distributional critic; 57 tasks, 1M steps,
  UTD 2 by default (sweeps 1–8); 95 % CIs and Welch's t-test.

### 1.4 Reading (`INFERENCE`)
- **Budgets.** Off-policy residual methods on frozen bases report useful learning at 7.5×10⁴–2×10⁵ steps (U02) and
  claim about 5× fewer than the >10⁶ of earlier residual work (U01). On-policy residual PPO in the classical-controller
  papers uses GPU simulators and 10⁷-scale budgets (U06: 3×10⁷). This agrees with the earlier review's L02 and L11: SAC
  is not uniformly better, but PPO needs far more samples.
- **Design choices with converging evidence:** critic normalisation (LayerNorm in U01, U02; batch normalisation in U09;
  weight-norm projection in U11), base-policy warm-up transitions in the replay buffer (U01), a zero-initialised,
  bounded residual (U03, U06; earlier S51, L06), and UTD above 1 (U02, U10). None of this is shown for a torque-level
  impedance base or a cube.
- **Headroom.** U07's 97.55 % → 82.37 % drop is a direct example of the risk the readiness check raised (issue 5): on
  a distribution where the base is near-perfect, a residual can only lose. G2 pilot 4 (144/144) is such a
  distribution.
- **Relevance of U06.** It is the closest published analogue: an xArm7, a nominal task-space controller, a bounded
  residual, a fixed bank of conditions and a paired hardware test. Its sim and policy stack (GPU, PPO, 30M) is not
  available here.

## 2. Q2: training on a cheaper simulator, evaluating on a higher-fidelity one
### 2.1 What was found (`FACT`)
- **U14 Sim2Real Predictivity (RA-L 2020).** A Sim-vs-Real Correlation Coefficient (SRCC) over 9 models. SRCC for
  success was 0.18 because agents learned to exploit simulator imperfections, "abusing collision dynamics to 'slide'
  along walls". Tuning simulation parameters raised it to 0.844. Older than the 2024 window but the protocol is the
  relevant part.
- **U18 Quadruped loco-manipulation (2025).** Sim-to-sim: Isaac Gym vs MuJoCo default vs MuJoCo with impratio 100.
  Velocity-tracking RMSE (vx/vyaw, mid pose): Isaac 0.144/0.118, MuJoCo default 0.123/0.118, impratio 100
  0.109/0.110. MuJoCo default showed foot sliding and drift; the lower error at impratio 100 "reflects unrealistic
  traction rather than true policy robustness".
- **U13 ODRL benchmark (NeurIPS 2024 D&B).** Friction and gravity shifts of 0.1–5× in MuJoCo locomotion, 5 seeds,
  0.1M target-domain steps. Observation 11: "There is no definitive correlation between the policy's performance in
  the source domain and the target domain"; source performance "is not a reliable indicator". Observation 5: training
  SAC on source plus target data "can incur good performance on numerous kinds of dynamics shifts". "No method has
  universal advantages."
- **U12 Multi-fidelity policy gradients (2025, TMLR 2026 per search; arXiv lists no venue).** Low fidelity = original
  MuJoCo dynamics; high fidelity = friction or gravity scaled 0.5–5×. 100 high-fidelity samples per update plus up to
  100× low-fidelity samples; 20 seeds; two-sided 95 % bootstrap CIs (10,000 resamples). Abstract: helps when the gap is
  "mild to moderate", more robust than off-dynamics baselines when low-fidelity data hurt. On-policy REINFORCE only.
- **U19 MuJoCo Playground (adds to C13).** Several training XMLs were cut to 1–4 solver iterations and 4–8 line-search
  iterations "for performance"; sim-to-sim checks used Gazebo. No MJX-to-MuJoCo-C or reduced-vs-full solver comparison
  was found in the part read.
- **U23 MJX documentation (adds to L22).** Solver iterations should be "brought down to just low enough that the
  simulation remains stable"; "Accurate solver forces are not so important in reinforcement learning" where domain
  randomisation adds noise. MJX-Warp supports "All except PGS, noslip".
- **U20 DiffMJX (ICLR 2026).** Hard contact needs stiff solver settings; non-stiff settings "strongly increase" the
  sim-to-real gap (abstract).
- **U16 PolySim (2025), U17 Humanoid-Gym (2024).** Sim-to-sim checking (Isaac to MuJoCo) is standard practice in
  humanoid locomotion; PolySim trains across several engines at once and reports improved MuJoCo execution success
  ("52.8", unit not stated in the abstract). Humanoid-Gym's abstract gives no sim-to-sim numbers.
- **U15 Lower fidelity, better transfer (2022).** For visual navigation, more physics fidelity did not help: slow
  simulation limited learning, and agents overfitted to simulator physics errors (abstract).

### 2.2 Reading (`INFERENCE`)
- **No reported number transfers to the NoSlip question.** The gaps above are between engines, gravity or friction
  scales, or simulation and reality. None removes a friction post-solver from a contact-rich manipulation scene.
- **The specific danger is exploitation, not average degradation.** U14 is the same failure in another domain: a
  surrogate that permits sliding taught agents to use it. NoSlip off allows creep at rest and softer stick (D13, the
  NoSlip findings), so a residual trained on it could learn to rely on pad slip or layer creep that full M7 does not
  allow. The full-M7 oracle would catch this at evaluation, but the training budget would be lost.
- **Speed-up of the surrogate on the full control step is smaller than 5.3×.** From D19: full step ≈ 6.3 ms, of which
  magnets ≈ 1.0–1.3 ms and judged checks ≈ 0.6 ms are unaffected by NoSlip. The remaining ≈ 4.4–4.7 ms of `mj_step`
  shrinks by 5.3× to ≈ 0.85 ms, so the step becomes ≈ 2.5–2.8 ms: about **2.3–2.6×** (about 3× if the judged checks
  are only sampled in training). The 5–6× of D19 needs the magnet force compiled as well.
- **Off-policy learning can mix fidelities cheaply.** U13 Observation 5 and U12 suggest that surrogate and full-M7
  transitions in one replay buffer is a plausible, simple scheme. Neither is shown for contact mechanics.

## 3. Q3: CPU-only throughput
### 3.1 What was found (`FACT`)
- **`mujoco.rollout` (U21, documentation for 4.0.1).** Rolls out `mj_step` "given an initial state and sequence of
  controls"; releases the GIL; `model` may be a sequence of "homogeneous" models (same sizes, different floating-point
  values); a persistent pool via `Rollout(nthread=...)`; "an `MjData` with a mju_threadpool installed is rejected".
  Controls are open-loop arrays. No performance numbers in the text.
- **`mujoco.batch.Batch` (U21, U22).** Added in 3.17.0: "Added a mujoco.batch module over the batch API". "Runs many
  simulations of one model on a thread pool", on `nthread` threads "with the Global Interpreter Lock released";
  results "are bit-identical to a loop over one `MjData` per simulation, at any thread count". Closed-loop control:
  write `ctrl` rows, then `step()`. Physics callbacks "must be C functions, installed through `ctypes`"; a Python
  function raises `ValueError`; a ctypes wrapper around Python "holds the Global Interpreter Lock while it runs, which
  serializes the batch's threads". No performance figures.
- **Python callbacks in general (U21).** The bindings acquire the GIL on every callback entry; "This is likely to incur
  a severe performance impact ... and is unlikely to be suitable for 'production' use case."
- **MuJoCo 3 announcement (U26, 2023).** "the Python bindings are subject to the Global Interpreter Lock (GIL)", so pure
  Python threads do not scale across cores.
- **MuJoCoUni (U24, 2026).** A downstream C++ batched executor with per-environment model copies. On an i9-14900HX with
  16 simulation threads, saturation at 256–512 environments: Allegro ≈ 1.8M, Go1 ≈ 1.2M, Franka ≈ 410k, Humanoid ≈ 290k
  steps/s. No scaling curve over 1–16 threads in the text; no callback support described.
- **Stable-Baselines3 (U27).** SAC supports multiple environments; `SubprocVecEnv` gives "significant speed up when
  the environment is computationally complex"; "the number of environments should not exceed the number of logical
  cores"; only "forkserver" and "spawn" are thread-safe start methods.
- **Lyceum (U25, 2020).** "5-30x faster" than Gym and dm_control (abstract; no core-scaling numbers on the page).

### 3.2 Reading (`INFERENCE`)
- **The project's fastest route to parallelism today is one environment per process** (already required by the
  process-global magnet callback, readiness issue 4), e.g. `SubprocVecEnv` with `forkserver`/`spawn`, up to the measured
  knee of Q5.
- **Pilot 4 gives a first aggregate figure:** 8 workers × 0.043× real time ≈ 0.34× real time ≈ **6.9 policy steps/s
  at 20 Hz ≈ 25k per hour ≈ 0.6M per day.** This was measured on G2 trials, possibly with other jobs running, and is not
  the Q5 scaling measurement.
- **`Batch` or `rollout` would need two ports:** the magnet force as a C callback (ctypes or a plugin), and the
  impedance plus J7 torque laws either as C (`mjcb_control`) or evaluated in NumPy over all rows between `step()`
  calls. A C port of the magnet force can be checked against the current Python callback, force by force, on recorded
  states; and `Batch` is documented as bit-identical to a per-simulation loop (U21), so the threaded path adds no
  further numerical change. This is engineering, not research, and it changes no physics if that check passes.
- **Because the simulator is the bottleneck,** learner updates are almost free: at ≈ 7 environment steps/s, even UTD
  10–20 adds little wall time on spare cores. This favours high-UTD or normalised-critic SAC variants (U02, U09–U11).

## 4. Q4: evaluation methodology for RL versus a classical controller
### 4.1 What was found (`FACT`)
- **U28 Agarwal et al. (NeurIPS 2021).** In the "few run" regime, report interval estimates of aggregate performance,
  performance profiles and robust aggregates such as the interquartile mean; library rliable (stratified bootstrap,
  probability of improvement).
- **U31 Jordan et al. (ICML 2024).** For benchmark aggregates over many environments, "the minimum number of seeds per
  algorithm-environment pair needs to be at least 100, otherwise ... we cannot trust the confidence intervals";
  bootstrap intervals "tend to be too narrow"; it is "unwise to blindly trust bootstrap ... for a small number of
  samples".
- **U32 Patterson et al. (JMLR 2024).** A guide to empirical design: assumptions behind performance measures,
  variation and stability, hypothesis testing, comparing multiple agents, baselines, hyperparameters and experimenter
  bias (abstract).
- **U33 Colas et al. (2018).** How the number of seeds sets error rates for t-tests and bootstrap tests (abstract).
- **U29 Kress-Gazit et al. (2024).** For robot policy evaluation: report initial conditions, number of runs and success
  criteria; use metrics beyond success rate; do statistical analysis; describe failure modes (abstract).
- **U30 STEP (RSS 2025).** A sequential test for comparing two policies with small samples ("e.g., 10 or 50"); "reduces
  the number of evaluation trials by up to 32%" while keeping correctness and power (abstract).
- **Practice in the residual papers:** U06 used 3 training runs, a fixed bank of 512 (and 2,000) conditions, and an
  exact McNemar test on matched hardware conditions; U07 used 5 seeds (mean ± SD); U05 5 seeds; U01 8 seeds with 95 %
  CIs; U10 10 seeds with IQM; U12 20 seeds with bootstrap CIs.

### 4.2 Reading (`INFERENCE`)
- **B0 has no training seed; B2 does.** The variability that matters differs: B0 varies only over start conditions,
  B2 over conditions and training seeds. A paired design on the same pre-registered condition bank isolates the effect
  of the residual (U06's approach).
- **IQM over 3–5 training seeds is nearly meaningless** (it drops one seed or less from each end), and U31 says
  bootstrap CIs over so few seeds under-cover. Per-seed results, all reported, are more honest.
- **Sample size for a binary endpoint.** For an unpaired comparison of 70 % vs 85 % success (α = 0.05, power 0.8) the
  standard two-proportion formula gives about 120 conditions per arm. A paired McNemar design needs fewer if outcomes
  are correlated, but depends on the discordant fraction, which only a pilot can estimate.

## 5. Implications for G3 (all `INFERENCE` or `PROPOSAL`; none needed before G2 closes)
1. `PROPOSAL` **Budget.** SAC residual, 2×10⁵ policy steps per training seed, with checkpoints at 25k, 50k, 100k and
   200k evaluated on validation conditions; 3 seeds minimum, 5 if Q5 allows. At the pilot-4 aggregate rate that is
   about 8 h per seed and 1–1.7 days for 3–5 seeds on full M7 (`INFERENCE`; episode resets and start sequences are not
   yet costed). Before committing, one 50k-step pilot on one seed to check that the critic learns.
2. `PROPOSAL` **Learner configuration to pre-register:** zero-initialised bounded residual (bounds from Q9); critic
   LayerNorm; UTD 4–10; replay buffer warm-started with about 20k B0 transitions (residual = 0), which are also B0
   stress-map data. All are literature defaults (U01, U02, U10), not tuned values.
3. `INFERENCE` **PPO at a matched 2×10⁵ budget is expected to underperform** (U02: 200k vs 40M; earlier L02, L11). The
   RL spec asks for a matched-budget PPO comparison; it can be run as specified and reported as such, or the user may
   drop B3 (`DECISION`, later).
4. `INFERENCE` **A NoSlip-off training surrogate is not needed for the off-policy budget above** if Q5 confirms ≈ 7
   policy steps/s on 8 processes. It would help only for PPO-scale budgets, and gives about 2.3–3× unless the magnet
   callback is compiled.
5. `PROPOSAL` **If a surrogate is used anyway, validate it before training, in this order:**
   - (a) **B0 agreement:** run B0 on both models over the same seeded stress-map conditions; pre-register a tolerance
     on the paired success difference (e.g. 95 % CI within ±5 percentage points) and on per-condition rank agreement
     (an SRCC-style correlation of per-cell failure rates, U14), plus core slip, turn time and peak wrench;
   - (b) **B1 agreement:** the same for the random bounded residual, because a residual can find slip that B0 never
     uses;
   - (c) **exploitation audit:** during surrogate training, re-run the current policy on full M7 at every checkpoint
     and log the surrogate–full gap; a widening gap is the U14 signature;
   - (d) **control arm:** at least one seed trained on full M7 at the same budget;
   - (e) **every reported result on full M7**, as the readiness check already requires.
   A cheaper variant is mixed replay (some surrogate, some full-M7 transitions; U12, U13), still with (c)–(e).
6. `PROPOSAL` **Throughput work before G3 design:** Q5 (1, 2, 4, 8, 12, 16 processes, 60 s each, quiet machine). Then,
   if it is worth it, port the magnet force to a C callback and bit-check it against the Python path; that also opens
   `mujoco.batch` (U21).
7. `PROPOSAL` **Evaluation protocol:**
   - three disjoint seed ranges for start conditions: training, validation (checkpoint selection) and test (used
     once);
   - the primary endpoint is oracle-judged success on the test bank, paired with B0 condition by condition; per training
     seed, an exact McNemar test and Wilson 95 % intervals for each rate;
   - every seed reported, including the worst; an aggregate probability of improvement (rliable) only as a secondary,
     labelled approximate (U31);
   - a **no-harm set** on G2's nominal distribution (where B0 is 144/144), because U07 shows a residual can lose there;
   - a wider out-of-distribution set reported separately;
   - secondary metrics and failure narratives as in U29; B1 as the negative control;
   - the test-bank size fixed after the stress map and a pilot of the discordant rate (≈ 120 conditions per arm as a
     first estimate for 70 % vs 85 %); a sequential test (U30) only if pre-registered.

## 6. Searches that came up empty
- Residual or any RL for nut tightening, screwing or other twist tasks with a parallel gripper, 2024–2026 (found only a
  2025 classical hybrid controller, 2511.21366, and a 2023 admittance-residual paper, 2310.10509, abstract only, not
  relied on).
- A study that trains with reduced MuJoCo solver settings (NoSlip off, fewer iterations) and measures the policy under
  the reference settings.
- A quantified sim-to-sim success drop for a contact-rich **manipulation** policy between two contact settings.
- Published thread or process scaling curves for `mujoco.rollout` or `mujoco.batch` on 8–16 cores (one gist,
  emiwar/fadab101…, contains a benchmark script but no results).
- Residual RL whose base is a torque-level Cartesian impedance controller with a separate roll-torque law.

Seen in search results but **not opened, not relied on (UNVERIFIED):** HIL-ResRL (arXiv 2606.22860), PACT
(2606.03949), SPARR (2602.23253), SLAC (2506.04147), SGFT (2502.02705), SimLauncher (2507.04452), Tabero (2605.27886),
HandoverSim engine swap (2303.17592), "Robot Policy Evaluation for Sim-to-Real Transfer" (2508.11117), a potential-field
plug-insertion paper on par.nsf.gov (PDF not readable by the tool), and EnvPool's 256-core figure beyond the earlier
L20 entry.

## 7. Sources (all accessed 2026-11-28)
Levels: **full** = HTML full text read through a summarising fetch; **partial** = first ~100,000 characters of the full
text; **abstract** = arXiv abstract page or documentation summary only; **docs** = official documentation page.

| ID | Citation | Reference | Level |
|---|---|---|---|
| U01 | G. Ma, L. Li, H. Wang, Z. Liu, P.-L. Bacon, D. Tao, "What Makes Value Learning Efficient in Residual Reinforcement Learning?", 2026 | arXiv:2602.10539 | partial (≈ 2/3) |
| U02 | L. Ankile, Z. Jiang, R. Duan, G. Shi, P. Abbeel, A. Nagabandi, "Residual Off-Policy RL for Finetuning Behavior Cloning Policies", 2025 (ICLR 2026 listing seen in search) | arXiv:2509.19301 | full |
| U03 | M. Iavorskaia, C. Dietz, S. Albrecht, M. Khadiv, "Res-HIL: Human-Guided Residual Reinforcement Learning for Sample-Efficient Dexterous Manipulation", 2026 | arXiv:2609.30023 | abstract |
| U04 | J. Stranghöner, P. Hartmann, M. Braun, S. Wrede, K. Neumann, "SHaRe-RL: Structured, Interactive Reinforcement Learning for Contact-Rich Industrial Assembly Tasks", ICRA 2026 | arXiv:2509.13949 | abstract |
| U05 | L. He, M. Deng, "Constraint-Grounded Reinforcement Learning for Variable Impedance Control in Contact-Rich Robotic Insertion", 2026 | arXiv:2609.13516 | abstract |
| U06 | T. Liu, R. A. Patamia, B. Champion, A. Cosgun, R. Dazeley, "Hybrid Residual Reinforcement Learning for Contact-Rich Robotic Book Insertion", 2026 | arXiv:2609.19962 | full |
| U07 | I. Marougkas, D. M. Ramesh, J. H. Doerr, E. Granados, A. Sivaramakrishnan, A. Boularias, K. E. Bekris, "Integrating Model-based Control and RL for Sim2Real Transfer of Tight Insertion Policies", 2025 | arXiv:2505.11858 | full |
| U08 | J. Luo, C. Xu, J. Wu, S. Levine, "Precise and Dexterous Robotic Manipulation via Human-in-the-Loop Reinforcement Learning", 2024 | arXiv:2410.21845 | abstract |
| U09 | A. Bhatt, D. Palenicek, B. Belousov, M. Argus, A. Amiranashvili, T. Brox, J. Peters, "CrossQ: Batch Normalization in Deep Reinforcement Learning for Greater Sample Efficiency and Simplicity", ICLR 2024 | arXiv:1902.05605 | abstract |
| U10 | M. Nauman, M. Ostaszewski, K. Jankowski, P. Miłoś, M. Cygan, "Bigger, Regularized, Optimistic: scaling for compute and sample-efficient continuous control", NeurIPS 2024 | arXiv:2405.16158 | partial (most) |
| U11 | H. Lee, Y. Lee, T. Seno, D. Kim, P. Stone, J. Choo, "Hyperspherical Normalization for Scalable Deep Reinforcement Learning" (SimbaV2), ICML 2025 | arXiv:2502.15280 | partial |
| U12 | X. Liu, C. Neary, K. Gupta, W. A. Suttle, C. Ellis, U. Topcu, D. Fridovich-Keil, "A Multi-Fidelity Control Variate Approach for Policy Gradient Estimation", 2025 | arXiv:2503.05696 | partial |
| U13 | J. Lyu, K. Xu, J. Xu, M. Yan, J. Yang, Z. Zhang, C. Bai, Z. Lu, X. Li, "ODRL: A Benchmark for Off-Dynamics Reinforcement Learning", NeurIPS 2024 D&B | arXiv:2410.20750 | partial |
| U14 | A. Kadian, J. Truong, A. Gokaslan, A. Clegg, E. Wijmans, S. Lee, M. Savva, S. Chernova, D. Batra, "Sim2Real Predictivity: Does Evaluation in Simulation Predict Real-World Performance?", RA-L 2020 | arXiv:1912.06321 | abstract |
| U15 | J. Truong, M. Rudolph, N. Yokoyama, S. Chernova, D. Batra, A. Rai, "Rethinking Sim2Real: Lower Fidelity Simulation Leads to Higher Sim2Real Transfer in Navigation", 2022 | arXiv:2207.10821 | abstract |
| U16 | Z. Lei et al., "PolySim: Bridging the Sim-to-Real Gap for Humanoid Control via Multi-Simulator Dynamics Randomization", 2025 | arXiv:2510.01708 | abstract |
| U17 | X. Gu, Y.-J. Wang, J. Chen, "Humanoid-Gym: Reinforcement Learning for Humanoid Robot with Zero-Shot Sim2Real Transfer", ICRA 2024 workshop | arXiv:2404.05695 | abstract |
| U18 | Y. Liu, J. Liu, H. Liang, D. Kanoulas, "A Framework for Deploying Learning-based Quadruped Loco-Manipulation", 2025 | arXiv:2512.18938 | full |
| U19 | K. Zakka et al., "MuJoCo Playground", 2025 (same paper as C13; new detail: Appendix A.1 Table III) | arXiv:2502.08844 | partial |
| U20 | A. Paulus, A. R. Geist, P. Schumacher, V. Musil, S. Rappenecker, G. Martius, "Differentiable Simulation of Hard Contacts with Soft Gradients for Learning and Control", ICLR 2026 | arXiv:2506.14186 | abstract |
| U21 | MuJoCo documentation, Python bindings (rollout, batch, callbacks); "stable" = 4.0.1 per the changelog | https://mujoco.readthedocs.io/en/stable/python.html | docs |
| U22 | MuJoCo changelog (latest 4.0.1, 2026-11-11; `mujoco.batch` in 3.17.0) | https://mujoco.readthedocs.io/en/stable/changelog.html | docs, partial |
| U23 | MuJoCo documentation, MJX (adds to L22) | https://mujoco.readthedocs.io/en/stable/mjx.html | docs |
| U24 | Y. Jia, J. Wu, "MuJoCoUni: Persistent Batched Runtime Primitives for MuJoCo", 2026 | arXiv:2605.24922 | partial |
| U25 | C. Summers, K. Lowrey, A. Rajeswaran, S. Srinivasa, E. Todorov, "Lyceum: An efficient and scalable ecosystem for robot learning", 2020 | arXiv:2001.07343 | abstract |
| U26 | MuJoCo GitHub Discussion #1101, "MuJoCo 3" (saran-t, 2023-10-18) | https://github.com/google-deepmind/mujoco/discussions/1101 | read |
| U27 | Stable-Baselines3 documentation (master): SAC; Vectorized Environments | https://stable-baselines3.readthedocs.io/en/master/modules/sac.html ; https://stable-baselines3.readthedocs.io/en/master/guide/vec_envs.html | docs |
| U28 | R. Agarwal, M. Schwarzer, P. S. Castro, A. Courville, M. G. Bellemare, "Deep Reinforcement Learning at the Edge of the Statistical Precipice", NeurIPS 2021 | arXiv:2108.13264 | abstract |
| U29 | H. Kress-Gazit, K. Hashimoto, N. Kuppuswamy, P. Shah, P. Horgan, G. Richardson, S. Feng, B. Burchfiel, "Robot Learning as an Empirical Science: Best Practices for Policy Evaluation", 2024 | arXiv:2409.09491 | abstract |
| U30 | D. Snyder, A. J. Hancock, A. Badithela, E. Dixon, P. Miller, R. A. Ambrus, A. Majumdar, M. Itkina, H. Nishimura, "Is Your Imitation Learning Policy Better than Mine? Policy Comparison with Near-Optimal Stopping", RSS 2025 | arXiv:2503.10966 | abstract |
| U31 | S. M. Jordan, A. White, B. Castro da Silva, M. White, P. S. Thomas, "Position: Benchmarking is Limited in Reinforcement Learning Research", ICML 2024 | arXiv:2406.16241 | partial (§2–3) |
| U32 | A. Patterson, S. Neumann, M. White, A. White, "Empirical Design in Reinforcement Learning", JMLR 25(318):1–63, 2024 | https://jmlr.org/papers/v25/23-0183.html | abstract |
| U33 | C. Colas, O. Sigaud, P.-Y. Oudeyer, "How Many Random Seeds? Statistical Power Analysis in Deep Reinforcement Learning Experiments", 2018 | arXiv:1806.08295 | abstract |

No DOIs were checked; arXiv identifiers and URLs are given. Venues are as stated on the arXiv page unless marked
"seen in search".

## 8. Limits
- One session on one day. Search coverage is limited; the "empty" list in §6 is absence in this session's searches,
  not evidence of absence.
- "Full" and "partial" levels were read through a summarising fetch tool, not as raw text; numbers were taken as the
  tool returned them and not cross-checked against PDFs. Figures (where several papers keep their main numbers) were
  not read.
- Every quantitative result is for its own task, simulator and hardware. None involves a cube, a torque-level impedance
  base, or MuJoCo's NoSlip.
- The throughput arithmetic in §2.2, §3.2 and §5 uses D19 and pilot-4 figures measured under load; Q5 has not been run.
- Per-contact or per-geom NoSlip (the D19 idea of NoSlip only on cubie–cubie contacts) was not researched.
- The sample-size estimate in §4.2 is a textbook two-proportion calculation, not a pre-registration.
