# D23: hardware-style admittance controller for arm B (findings Q2; P-134 optional side work)

**UNSCORED feasibility experiment.** It does not count toward any gate, changes no G2/G3 decision, and uses pilot seeds
29001 and 29002 only. Nothing outside this folder was modified. Run 2026-11-27, MuJoCo 4.0.1, WSL Ubuntu-24.04,
`~/.venvs/rubiknetic` (no new dependencies).

## Question

The real xArm accepts only position or velocity setpoints, at up to 250 Hz. G2's arm-B controller is a torque-level
Cartesian impedance, which the real arm cannot run. Is a hardware-style structure stable in this scene? The structure
tested is: stiff joint position servos, wrapped in an outer **admittance** loop on the wrist F/T force, updated at
250 Hz with a one-sample hold and 1–3 samples of delay.

## Method

* **Scene.** The G2 scene comes unchanged from `experiments/E8_scored_g2/trials.py`: `configure({}, start_draw(seed))`,
  then `TA.TwoArm`. It has the D18 layout, the stand drop, arm A holding, the L0 magnets on, and the F/T sensor
  (P-114). The frozen files are imported and never edited. The arm-B model change is made in memory, in this process
  only (`admittance.py::_build_position_servos`, which wraps `TA.build`). That change converts arm B's J1–J7 back
  from torque motors into MuJoCo position servos with arm A's Menagerie gains (kp 1500/1500/1000/1000/1000/800/800
  N·m/rad, kv = kp/10, implicit under `implicitfast`). Servo gains are ×1 unless marked `sg4`.
* **Controller.** Arm B's `impedance()` is overridden. Every 8 physics steps (250 Hz, dt 0.5 ms), it does the
  following:
  1. Reads the F/T force in the world frame and adds Gaussian noise of 0.1 N per axis (ASSUMPTION).
  2. Subtracts a tare taken while the arm is free, giving F_ext = −(f − f_tare). The sign was checked in
     `probe_ft_sign.py`.
  3. Takes the sample `delay` ticks old (1 or 3).
  4. Integrates M·δ̈ + D·δ̇ + K·δ = F_ext (semi-implicit Euler, per axis, translation only).
  5. Commands x_cmd = x_ref + δ with the nominal gripper axis, through a 3-iteration damped-least-squares IK on a
     standalone arm-B model. The IK is seeded with the previous **commanded** joint vector.
  6. Writes the joint setpoints, which are held until the next tick. J7 receives the roll setpoint at the same ticks.

  The controller reads only F/T samples, its own commanded joints, targets and time. It **never reads cube state**.
  Cube state is read offline for metrics only.
* **Sequence** (simulated seconds after the 3.6 s start sequence): tare 0.2 s → approach 1 s (cosine, 40 mm along the
  axis) → settle 0.5 s → close arm B's gripper at G2's rate (1.6 s) → **task 1: hold 1.5 s** → **task 2: roll J7 a
  quarter turn (U) on a 1.5 s cosine** → hold 0.3 s → open 0.3 s. That is 10.5 s of simulation in all. A run aborts as
  UNSTABLE if |δ| exceeds 30 mm.
* **Controls.** `stiff` uses the same position servos with δ ≡ 0, i.e. no compliance. `g2` uses G2's own torque
  impedance plus the J7 torque law, unmodified.
* **Sweep.** The main set is K ∈ {200, 500, 1000, 2000} N/m × M ∈ {1, 0.1} kg × delay ∈ {1, 3} samples, with
  D = 2ζ√(KM) and ζ = 0.8. The extra set was chosen **after** the first 8 main runs, as stated here:
  * K 500, M 1, with D set explicitly to 150 or 300 N·s/m, at delays 1 and 3;
  * a 20 Hz first-order F/T low-pass;
  * servo gains ×4;
  * a second seed (29002) for the best and the baseline settings.
* **Metrics** (`analyze.py`, offline). F_ext is the true, noise-free net force arm B applies to the cube, which is
  the inter-arm "internal squeeze" that arm A must resist. "Grip" is arm B's fingertip normal force, summed over
  contacts.
  * Chatter is measured with a 5 Hz high-pass (zero-phase Butterworth) at 2 kHz: the RMS of the gripper-base position
    and of the F_ext 3-vector, and the dominant frequency.
  * Windows: hold = the last 1.0 s of task 1; roll = task 2.
  * Core slip and rotation are measured relative to arm A's gripper. The turn is the readout's observed move plus the
    layer rotation.
  * Classification is post hoc: CHATTER if the high-passed F_ext RMS exceeds 1.0 N or the position RMS exceeds
    0.05 mm. The controls sit at 0.04 N (hold) and 0.15–0.38 N (roll).

## Results (seed 29001 unless marked; full table in `results/summary_table.md`, numbers in `results/summary.json`)

The F_hp and mean/peak F_ext columns are N; F_hp is the high-passed RMS, with its dominant frequency in brackets.

| setting | class | hold F_hp (Hz) | hold F_ext mean / peak | roll F_hp (Hz) | roll F_ext mean / peak | max δ mm | core slip max mm | turn |
|---|---|---|---|---|---|---|---|---|
| **stiff** servo, no admittance | STABLE | 0.04 | 2.49 / 3.38 | 0.15 | 5.24 / 7.50 | 0 | 0.13 | U (−90.0°) |
| stiff, servo ×4 | STABLE | 0.06 | 3.08 / 3.67 | 0.38 | 4.24 / 7.01 | 0 | 0.18 | U |
| **G2** torque impedance (reference) | STABLE | 0.04 | 1.56 / 2.03 | 0.31 | 3.33 / 5.14 | – | 0.10 | U (−90.1°) |
| K200 M1 d1 (D 22.6) | CHATTER | 2.71 (12) | 2.71 / 4.99 | 2.53 (12) | 2.51 / 4.64 | 3.6 | 0.13 | U |
| K500 M1 d1 (D 35.8) | CHATTER | 2.38 (12) | 2.35 / 3.99 | 2.10 (12) | 2.26 / 3.69 | 3.1 | 0.12 | U |
| K1000 M1 d1 (D 50.6) | CHATTER | 2.06 (12) | 2.09 / 3.37 | 1.86 (12) | 2.36 / 3.94 | 2.6 | 0.10 | U |
| K2000 M1 d1 (D 71.6) | CHATTER | 1.66 (14) | 1.83 / 3.44 | 1.39 (14) | 2.70 / 4.11 | 2.0 | 0.13 | U |
| K200 M1 d3 | CHATTER (large) | 19.9 (8) | 21.9 / 35.1 | 21.2 (8) | 23.0 / 37.0 | 24.3 | **5.11** | U (−91.4°) |
| K500 M1 d3 | CHATTER | 4.62 (10) | 4.69 / 8.20 | 4.74 (10) | 4.84 / 9.24 | 4.2 | 0.16 | U |
| K500 M1 d3, seed 29002 | CHATTER | 4.53 (10) | 4.55 / 7.60 | 4.49 (10) | 4.55 / 7.90 | 4.0 | 0.17 | U |
| K1000 M1 d3 | CHATTER | 2.76 (10) | 2.83 / 4.62 | 2.64 (10) | 3.01 / 4.94 | 3.3 | 0.10 | U |
| K2000 M1 d3 | CHATTER | 2.14 (12) | 2.28 / 3.60 | 1.96 (12) | 2.90 / 4.83 | 2.4 | 0.10 | U |
| K200 M0.1 d1 | **UNSTABLE** (\|δ\| > 30 mm at 9.60 s, in the roll) | 33.1 (29) | 29.2 / 57.5 | – | – | >30 | 1.09 | – |
| K500 M0.1 d1 | CHATTER (large) | 25.8 (33) | 23.0 / 48.7 | 27.9 (35) | 25.3 / 50.6 | 15.0 | 1.32 | U (−92.2°) |
| K1000 M0.1 d1 | CHATTER (large) | 19.4 (37) | 16.1 / 31.6 | 20.7 (39) | 18.4 / 37.7 | 8.6 | 0.48 | U (−92.5°) |
| K2000 M0.1 d1 | CHATTER | 2.29 (39) | 2.32 / 3.89 | 2.04 (39) | 2.96 / 6.04 | 2.9 | 0.09 | U |
| K200 M0.1 d3 | **UNSTABLE** (at 5.97 s, during the close) | – | – | – | – | >30 | 0.09 | – |
| K500 M0.1 d3 | **UNSTABLE** (at 5.99 s, during the close) | – | – | – | – | >30 | 0.39 | – |
| K1000 M0.1 d3 | CHATTER (large) | 34.5 (23) | 31.8 / 65.1 | 30.7 (23) | 27.1 / 63.2 | 27.5 | **6.13** | **no move** (−78.7°) |
| K2000 M0.1 d3 | CHATTER (large) | 22.8 (25) | 20.3 / 39.2 | 25.4 (25) | 23.4 / 47.4 | 12.0 | 0.68 | U (−92.3°) |
| K500 M1 d1, 20 Hz F/T low-pass | CHATTER | 2.88 (10) | 2.91 / 4.76 | 2.73 (10) | 2.88 / 4.65 | 3.5 | 0.11 | U |
| **K500 M1 d1 D150** | STABLE | 0.48 | 0.61 / 3.09 | 0.26 | 1.14 / 2.06 | 3.1 | 0.11 | U (−90.0°) |
| K500 M1 d3 D150 | CHATTER (mild) | 1.33 (10) | 1.54 / 3.72 | 1.19 (10) | 1.71 / 3.04 | 3.0 | 0.15 | U |
| **K500 M1 d1 D300** | STABLE | 0.31 | 0.61 / 2.94 | 0.22 | 1.40 / 2.49 | 3.1 | 0.13 | U (−90.1°) |
| **K500 M1 d3 D300** | STABLE | 0.39 | 0.71 / 3.22 | 0.23 | 1.42 / 2.36 | 3.1 | 0.13 | U (−90.1°) |
| **K500 M1 d3 D300, seed 29002** | STABLE | 0.47 | 0.95 / 3.07 | 0.51 | 1.53 / 3.13 | 3.0 | 0.15 | U (−90.1°) |
| **K500 M1 d3 D300, servo ×4** | STABLE | 0.90 | 1.06 / 3.47 | 0.56 | 0.81 / 2.89 | 1.5 | 0.13 | U (−89.9°) |

Integrity, all 27 runs:
* the magnets acted at every step;
* 0 edit-audit violations and 0 numerical failures;
* no actuator, equality, tendon or gravcomp on the cube;
* no robot non-pad–cube, arm–arm, robot–table or robot–stand contacts;
* cubie penetration ≤ 0.20 mm;
* the largest near-pair magnet tilt was 2.28°.

Arm B's fingertip grip was 38–40 N in every run.

## Findings

**FACT** (as measured in these runs):
1. **Free-space admittance is quiet** in every setting. Through the tare, approach and settle phases, the high-passed
   F_ext stays at or below 0.2 N, the same as the stiff control. The oscillation **starts when arm B's gripper closes on
   the U layer** and dies within about 0.1 s of opening (`diag_phases.py`). It is a contact-coupled oscillation, and it
   lies mainly along the cube/gripper axis (world x).
2. **With the textbook damping D = 2·0.8·√(KM), no setting is stable.**
   * Every M = 1 kg run holds a sustained limit cycle at 8–14 Hz. With 1-sample delay it is 1.7–2.7 N RMS
     (δ 2–3.6 mm). With 3-sample delay it is 2.1–4.7 N, and 20 N at K = 200 (1 mm, 8 Hz).
   * Every M = 0.1 kg run oscillates at 23–39 Hz with 16–35 N RMS and 30–65 N peaks, except K2000 d1 (2.3 N).
     K200 d1, K200 d3 and K500 d3 diverged (|δ| > 30 mm).
   * Chatter falls monotonically as D rises (K200 → K2000 at fixed M), not with K as such.
3. **A turn still worked in 23 of the 25 runs that reached the roll.** U was observed by the readout, with layer
   rotation −89.9° to −92.5°.
   * K1000 M0.1 d3 failed: no move was detected, the layer turned −78.7°, the core slipped 6.1 mm in arm A's grip, the
     core rotated 18.8°, and one cubie ended 14° off the lattice.
   * K200 M0.1 d1 diverged 1.2 s into the roll, with core rotation 10.4°.
   * K200 M1 d3 turned the layer but slipped the core 5.1 mm (rotation 5.3°). That is beyond G2's 1 mm / 2° limits.
   * The two runs that diverged during the close (K200 and K500, M0.1, d3) never reached a turn.
4. **Damping sized to the contact, not to K/M, makes it stable.** At K 500 and M 1:
   * D = 300 N·s/m is STABLE at delay 1 and at delay 3, on both seeds, and with 4× stiffer servos. Hold ripple is
     0.3–0.9 N, decaying to ≤ 0.06 N RMS by the end of the hold in the seed-29001 d3 run.
   * D = 150 is stable at delay 1 and chatters mildly at delay 3 (1.3 N, 10 Hz).
5. **When stable, the admittance loop cuts the inter-arm force below both controls.**

   | | hold mean F_ext (N) | roll mean F_ext (N) | roll peak F_ext (N) |
   |---|---|---|---|
   | stiff servo | 2.49 | 5.24 | 7.50 |
   | G2 impedance | 1.56 | 3.33 | 5.14 |
   | admittance, D 300 | 0.61–1.06 | 0.81–1.53 | 2.4–3.1 |

   Core slip is the same (0.10–0.15 mm).
6. **The 20 Hz F/T low-pass made chatter worse** (2.88 vs 2.38 N RMS), consistent with the extra lag.
7. **The stiff position servo alone (no admittance) turns the layer cleanly** at this seed, with a higher internal
   force (roll mean 5.2 N, peak 7.5 N).

**INFERENCE:**
* The limit-cycle frequencies fit f ≈ √((K + k_e)/M)/2π with an effective contact stiffness of k_e ≈ 5–6 kN/m.
  k_e lumps arm B's servo compliance, the soft fingertip pads (solref 0.01) and arm A's grip. The fit is 12 Hz at
  M 1 and 33–39 Hz at M 0.1 for delay 1.
* The sampled loop delay of 1–3 ticks plus the hold (6–14 ms) turns that stiffness into negative damping of roughly
  k_e·τ_eff ≈ 30–80 N·s/m. Admittance damping below that is destabilised, which explains why D, not K, sets the
  outcome.
* The one-spring linear model (`linear_model.py`, `results/linear_model_table.md`) at k_e = 5.5 kN/m reproduces the
  pattern: spectral radius > 1 for all M = 0.1 cases, marginal (0.94–1.08) for M = 1 with ζ = 0.8, and < 1 for D 150
  and D 300. Its frequencies are close for M = 1 but low for M = 0.1. It predicts D150 d3 is stable, whereas the
  simulation shows mild chatter. It is a sanity check, not a validated model.
* A hardware-style admittance loop at 250 Hz therefore looks **feasible in this simulation** with M ≈ 1 kg,
  K ≈ 500 N/m and D ≈ 300 N·s/m (heavily overdamped relative to K/M; ζ_KM ≈ 6.7). It also reduces internal force.
  Light virtual mass (0.1 kg) at 250 Hz with this contact stiffness should be avoided.

**ASSUMPTION / LIMITATIONS:**
* The xArm's real joint-servo dynamics, internal IK, bandwidth and latency are not modelled. Here they are an ideal
  MuJoCo position servo with Menagerie gains (×1, plus one ×4 check) and a damped-least-squares IK. The real
  controller's setpoint filtering and interpolation would add lag, which per the inference above needs more damping.
* The F/T noise of 0.1 N per axis with no bias drift is an ASSUMPTION; G2's sensor model has torque noise only. The
  sensor rate is taken as 250 Hz; the UFACTORY sensor is listed at 200 Hz (P-114).
* The contact stiffness depends on the soft pad model (solref 0.01) and on arm A's servo. A stiffer real contact would
  raise k_e and the damping required.
* The admittance is on translation only. Orientation is held by the servo, and J7 is position-commanded with no
  torque budget and no F/T jam guard. G2's jam guard (P-114) was not ported.
* Two seeds were used, on the best and baseline settings only. Each setting is one run of 10.5 s simulated, with one
  slow (1.5 s) quarter turn U and no sequence. Throughput was about 140 steps/s per process (135–200 s wall per run).
* The chatter thresholds and the extra-set choice are post hoc. Nothing here is a validated result or a G2/G3 gate
  item.

## Files

| file | purpose |
|---|---|
| `admittance.py` | one trial (`--mode adm/stiff/g2`, `--K --M --zeta/--D --delay --servo-gain --ft-lp --seed`) |
| `sweep.py` | runs the main and extra sets, ≤ 2 processes, skips finished runs |
| `analyze.py` | metrics → `results/summary.json`, Markdown table (`results/summary_table.md`) |
| `diag_phases.py` | high-passed force and position RMS per phase (free space vs grasped) |
| `linear_model.py` | discrete one-spring stability cross-check → `results/linear_model.json`, `_table.md` |
| `probe.py`, `probe_ft_sign.py` | model facts (gains, integrator) and the F/T sign convention |
| `results/*.json`, `results/*_trace.npz` | per-run records; 2 kHz traces (t, gripper-base xyz, raw F/T force world, x_cmd) and 250 Hz ticks (t, core slip, core rotation, grip, F used, δ); about 21 MB in total |
| `logs/` | per-run stdout of the sweep |

## Reproduce (WSL)

```bash
cd /mnt/c/dev/Rubiknetic
PY=~/.venvs/rubiknetic/bin/python
$PY experiments/D23_admittance_q2/probe_ft_sign.py
$PY experiments/D23_admittance_q2/admittance.py --mode stiff
$PY experiments/D23_admittance_q2/admittance.py --mode g2
$PY experiments/D23_admittance_q2/sweep.py --jobs 2 --set main     # 16 runs, ~25 min
$PY experiments/D23_admittance_q2/sweep.py --jobs 2 --set extra    # 9 runs, ~15 min
$PY experiments/D23_admittance_q2/analyze.py > experiments/D23_admittance_q2/results/summary_table.md
$PY experiments/D23_admittance_q2/linear_model.py
$PY experiments/D23_admittance_q2/diag_phases.py adm_K500_M1_d3_D300_sg1_s29001
```

## Repository note (main session, 2026-11-28)
The 27 per-run time traces (`results/*_trace.npz`, about 21 MB) are not committed (`.gitignore` in this folder). They are
deterministic per seed and are regenerated by `sweep.py`. The per-run JSON metrics, `summary.json` and the tables are
committed.
