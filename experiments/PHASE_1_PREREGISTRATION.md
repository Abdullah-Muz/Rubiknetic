# Phase 1 (G1) Pre-registration — M1 contact-emergent cube

**Status:** `APPROVED 2026-11-12` (user: "Fully approved": section 4 thresholds, 0.5 mm penetration, Option A, section 2
trial counts and ranges), with **Amendment 1** below. Frozen by the git commit that adds this line; thresholds may never be
loosened after a failure (VALIDATION_PLAN threshold policy).
**Date:** 2026-11-12 · **Model:** M1 with radial preload (P-10) · **Rig:** v0, core fixed (P-09) ·
**Order:** M1 scored first; M2 built afterwards as comparison (P-14).
**Basis:** E1-0 calibration ([`E1-0_calibration/README.md`](E1-0_calibration/README.md)) and the protocol in
[`../docs/research/PHASE_1_2_VALIDATION_EXPERIMENTS.md`](../docs/research/PHASE_1_2_VALIDATION_EXPERIMENTS.md).

---

## 1. Frozen configuration

The scored runs use the `M1Params` defaults at the commit that freezes this document (E1-0 nominal "v2", run as
c31–c37). The key values are:

| Group | Value |
|---|---|
| Geometry | 19 mm pitch, 0.2 mm gap, 1.4 mm chamfer, 3.4 g per cubie |
| Cubie contact | μ (0.2, 0.0025, 0.0005), condim 3, solref (1 ms, 1), solimp (0.95, 0.99, 0.5 mm) |
| Retention | Ball joint at centre; radial slide with 1 N preload, 500 N/m, range −1…+0.2 mm, limit solref 1 ms |
| Pads / turner | 45 × 10 × 5 mm pads, μ 0.8, condim 4, grip 10 N, open clearance 14 mm; turner torque limit 1 N·m |
| Solver | 0.5 ms timestep, implicitfast, elliptic cone, impratio 10, Newton, 100 iterations, tol 1e-10 |
| Software | MuJoCo 4.0.1, Python 3.12, NumPy 2.5.4 (from `uv.lock`) |

**Run-integrity rules (categorical, apply to every scored trial):**

1. **Clean commit:** scored runs execute only from a clean, committed working tree. The commit hash is stored in
   every record, and the runner refuses to start otherwise.
2. **Edit audit:** zero writes to `qpos`, `qvel`, `act`, `eq_active`, `xfrc_applied`, `qfrc_applied` or mocap
   between steps. The only exceptions are (a) the logged episode setup before t = 0 and (b) the E1-6(c) test
   wrench approved under P-12.
3. **Numerical failure:** any `mjWARN_BADQACC`, `BADQPOS`, `BADQVEL` or `BADCTRL` fails the trial. It is never
   excluded or rerun.
4. **Oracle agreement uses observed moves:** the move applied to the oracle is inferred from the **measured** layer
   rotation (nearest multiple of 90° about the measured axis), never from the command. If no layer rotated by
   more than 45°, the observed move is "none".
5. **No exclusions:** every scored trial is reported. Failed trials are archived with their full configuration.

## 2. What varies between trials

The simulator is deterministic, so identical trials would be repeats rather than evidence. Each scored trial
draws, from seed `s` (scored seeds **1000–1999**, disjoint from calibration seeds 1–3), the following episode-setup
values. All are logged.

| Variable | Distribution | Why |
|---|---|---|
| Initial misalignment of every layer, applied at setup before t = 0 | Uniform ±1° per face | Tests sensitivity to imperfect starting alignment |
| Grip force | Uniform 10–20 N | Inside the G2 range (10–50 N) |
| Turn duration per quarter turn | Uniform 0.8–1.2 s | Speed robustness |
| Scramble (E1-4 only) | 20 legal moves from `random_scramble(20, s)` | Topology coverage |

## 3. Metric definitions

| Metric | Definition |
|---|---|
| Turn error | Mean over the target layer's non-centre cubies of wrap(measured rotation − nominal), measured between the pre-move snapshot and the snapshot after release and settle |
| Non-target drift | Max absolute rotation about the turn axis of **all** non-centre cubies not in the target layer, over the same interval |
| Penetration | Max over all contacts and all steps of −dist |
| Radial offset | Per corner/edge, \|r − r_nominal\|, after setup settle |
| Radial change (travel) | Max over the trial of \|r(t) − r(trial start)\| per corner/edge. **Reported**; used as a criterion only in E1-6b |
| Radial pop check (Amendment 1) | Max over the trial of r(t) − r_nominal over corner/edge cubies; must stay ≤ 0.3 mm (outward retention stop at +0.2 mm, plus 0.1 mm tolerance) |
| Causality | For each turn, the first time target-layer angular speed exceeds 5°/s must come **after** the turner-pad contact force first exceeds 0.5 N |
| Rest rotation (E1-1) | Max absolute rotation of any layer over 10 s with no actuation |

## 4. Experiments and thresholds

⟨P⟩ marks quantitative thresholds proposed from E1-0 data. "Observed" gives the worst E1-0 value on the nominal
configuration, for comparison.

| ID | Trials | Pass criteria | Observed in E1-0 |
|---|---|---|---|
| **E1-1** Static rest, 10 s | 20 seeds | Observed state solved and valid. Rest rotation ⟨P⟩ ≤ 0.5°. Radial offset ⟨P⟩ ≤ 0.5 mm. Radial pop check ≤ 0.3 mm (Amendment 1). Penetration ⟨P⟩ ≤ 0.5 mm. | Radial offset 0.35–0.37 mm (preload seating) |
| **E1-2** Quarter turns | 6 faces × CW/CCW × 2 seeds = 24 | Oracle agrees. Turn error ⟨P⟩ ≤ 2°. Non-target drift ⟨P⟩ ≤ 1°. Penetration ⟨P⟩ ≤ 0.5 mm. Radial pop check ≤ 0.3 mm (Amendment 1). Causality holds. | Turn error 0.68°, drift 0.07°, penetration 0.34 mm |
| **E1-3** Half turns | 6 faces × 2 seeds = 12, plus 10 × `F2 B2 L2 R2 U2 D2` | As E1-2 | Turn error 0.37° |
| **E1-4** Multi-axis sequences | 20 × `R U R' U'`×6; 20 × scramble(20, s) + inverse | Every intermediate observed state agrees with the oracle. Final state solved. Per-move criteria as E1-2. Cumulative misalignment reported. | 24/24 and 40/40 matched |
| **E1-5** Forgiveness (M1) | U misaligned 0…20° in 1° steps, both signs; then R attempted (42 trials) | **Categorical:** never an illegal or oracle-mismatched state (P-11). The forgiveness angle is measured and reported, with no threshold until real-cube data exists. | Completes at ≤11.6°, blocked at ≥14.6° |
| **E1-6a** Command without contact | 6 faces, pads open | Layer rotation ⟨P⟩ ≤ 0.5°. State stays solved. | 0.0° |
| **E1-6b** Opposed torques | Pairs U+R, U+F, R+F at 1 and 2 N·m (6 trials) | **Categorical:** not both layers ≥ 45°, and the state is UNKNOWN or legal and oracle-consistent with the observed moves. Radial change ⟨P⟩ ≤ 0.5 mm (no separation; not amended). Penetration is reported only (overload case). | Penetration 0.37–0.64 mm; radial ≤ 0.37 mm |
| **E1-6c** Corner twist (logged test wrench, P-12) | 8 corners | Torque about the corner's diagonal ramped 0 → 5 N·m (≈10× running torque) over 2 s, held 0.5 s, then released. **Categorical:** after release, the observer never reports a *valid* state other than solved. Twist angle, penetration and the load at which twist exceeds 15° (if it does) are reported. | Not yet run |
| **E1-6d** Misaligned perpendicular turn | Covered by E1-5 | As E1-5 | — |
| **E1-7** Sensitivity, one factor at a time | Each value below × (U U' R R' F F' and `R U R' U'`×6), seed 1000 | Outcome unchanged inside the declared band. Any flip is reported as a fragility, not hidden. | Partial (E1-0) |
| **E1-8** CPU throughput | Isolated machine load | Measurement only (steps/s and real-time factor) for: cube at rest; cube + idle rig; during a turn; timesteps 0.25, 0.5 and 1 ms; 1, 4, 8 and 16 parallel processes. Sets the Phase 2 throughput floor. | Not yet run |

**E1-7 declared nominal band:**

| Factor | Values |
|---|---|
| Timestep | 0.25, 0.5, 0.75 ms |
| Solver iterations | 50, 100, 200 |
| Cubie μ | 0.1, 0.2, 0.5, 1.0 |
| Joint frictionloss | ×0.1, ×1, ×10 |
| Chamfer | 1.0, 1.4, 2.0 mm |
| Gap | 0.1, 0.2, 0.3 mm |
| Radial preload | 0.5, 1, 2, 3 N |
| Grip | 10, 30, 50 N |
| Initial misalignment | 0, 1, 2, 5° |

**Penetration change from the original proposal:** the original ⟨P⟩ was 0.2 mm. E1-0 never reached it at a 0.5 ms
timestep (worst 0.34 mm on long sequences). This draft therefore proposes 0.5 mm. The alternative keeps 0.2 mm,
which requires recalibrating at a smaller timestep (about 2× slower).

## 5. Pass logic for M1 (choose one)

* **Option A (recommended, strict):** every categorical **and** every ⟨P⟩ criterion holds in 100 % of scored trials
  of E1-1 to E1-6. A deterministic simulator should not need a tolerance for occasional failure.
* **Option B:** categorical criteria hold in 100 % of trials; ⟨P⟩ criteria hold in at least 95 % of trials per
  experiment, with every miss reported.

Under either option, E1-7 and E1-8 must be completed and published. G1 also requires your sign-off.
**Mechanism decision rule (from the protocol):** if M1 passes, M2 is still built and run as the comparison
(P-14). If M1 fails E1-4 or E1-6, M2 becomes the candidate. A scripted rotation is never a fallback.

## 6. Harness work required before scoring (not yet implemented)

1. Observed-move inference from measured rotation (rule 4). The calibration harness compared against the
   *commanded* move.
2. Non-target drift over all non-target cubies. The calibration harness measured only the opposite face.
3. Radial travel, radial pop check, causality and rest-rotation metrics.
4. Per-trial setup randomisation with logging (section 2), applied before t = 0 only.
5. Logged test-wrench mechanism for E1-6c, permitted by the audit only in that experiment.
6. Clean-commit check and commit hash in every record.
7. Unit tests for the new metrics, including injected-fault tests (e.g. a scripted state write must be
   caught, and a fake twisted corner must be rejected).

## 7. Amendment 1 (2026-11-12, before any scored trial)

**Trigger:** the first harness self-test (seeds 998/999, outside the scored range, not a scored trial) gave
0.51–0.56 mm radial travel in a single U turn against the approved 0.2 mm "radial change" limit.
**Cause:** the 1 N preload seats each corner/edge cubie ≈0.35 mm inside nominal. During a turn the cubie lifts to
its outward retention stop at +0.2 mm, giving ≈0.55 mm of designed play. This is not a pop.
**Decision (user, 2026-11-12):** replace the E1-1…E1-4 "radial change ≤ 0.2 mm" criterion with a pop check:
radial position ≤ nominal + 0.3 mm. Travel is still reported.
**Unchanged:** E1-6b keeps its approved "radial change ≤ 0.5 mm" no-separation criterion.

## 8. Decisions (resolved)

1. Approve the thresholds in section 4, or change any value.
2. Penetration limit: 0.5 mm (as drafted) or keep 0.2 mm with recalibration.
3. Pass logic: Option A or Option B.
4. Trial counts and the randomisation ranges in section 2.
