# Phase 1 (G1) Pre-registration — M2 switched-weld cube

**Status:** `APPROVED 2026-11-13` (user: "approved", covering sections 1–8). Scored runs may start only after the section-6 harness work is committed and
the runner checks for a clean commit. Thresholds may never be loosened after a failure.
**Date:** 2026-11-13 · **Basis:** P-14 and P-17 ([`../docs/DECISION_LOG.md`](../docs/DECISION_LOG.md)), the M2
prototype ([`M2_switched_welds/README.md`](M2_switched_welds/README.md)), the validation protocol
([`../docs/research/PHASE_1_2_VALIDATION_EXPERIMENTS.md`](../docs/research/PHASE_1_2_VALIDATION_EXPERIMENTS.md)),
and the approved M1 pre-registration ([`PHASE_1_PREREGISTRATION.md`](PHASE_1_PREREGISTRATION.md)), whose
structure, thresholds and integrity rules are reused unless stated.
**Prototype evidence (unscored, FACT):** 9/9 oracle matches with both turner stiffnesses; turn error ≤ 1.0°
(soft turner); corner twist 0.48° at 5 N·m; switch |ΔKE| ≤ 2e-7 J; 1,350–2,030 steps/s.

---

## 1. Frozen configuration (proposed)

| Group | Value |
|---|---|
| Cubies, rig, solver | M1 geometry and pad rig exactly as frozen for M1 (section 1 of the M1 pre-registration), with `radial_preload = 0` (rigid radius, no radial slide) |
| Welds | 146 equality welds: each non-centre cubie → core, cubie → each of the 6 centres (normally inactive), and each centre → core. solref (1 ms, 1), solimp (0.99, 0.999, 0.1 mm) |
| Unlock rule | All of: no layer unlocked; every non-centre cubie within **1.0°** and **0.15 pitch** of the lattice; the face's pads grip with more than **2 N**; pad contact torque about the face axis above **0.05 N·m**. The layer's welds then move from the core to the layer's centre |
| Relock rule | Centre hinge within **0.5°** of a multiple of 90°; every layer cubie within **0.5°**; pad torque below **0.02 N·m**; hinge speed below **0.05 rad/s**; and the layer has turned more than 45° or more than 1 s has passed |
| Refusals | Simultaneous requests, a misaligned cube, or another layer still unlocked: logged, and nothing switches |
| Re-anchoring | Every activation sets the weld relpose to the **current** relative pose. It never snaps to the lattice |
| Inputs to the rule | Physical state only: poses, speeds, pad contact forces and torques. Never the commanded move or the oracle |
| Turner | **Default M1 rig (turn_kp 5, kv 0.2)**, matching M1 for comparability. Stiffness 20 is tested only in E1-7 |

## 2. Run-integrity rules

These are M1's rules 1–5 (clean commit, edit audit, numerical failure, observed-move oracle, no exclusions), with one
**declared exception**:

* `eq_active` and `eq_data` may change **only** through the registered switch manager. Every change is logged with
  time, face, member count, pad torque, relative speed, pre- and post-activation pose error, ΔKE, impulse proxy
  and penetration.
* Any other write to `eq_*`, `qpos`, `qvel`, `act`, `xfrc_applied`, `qfrc_applied` or mocap fails the trial.
* Scored seeds are **2000–2999**, disjoint from M1 (1000–1999) and from the prototypes.

## 3. What varies between trials

The same draws as M1: misalignment ±1° per face (applied before t = 0 and logged), grip 10–20 N, 0.8–1.2 s per
quarter turn, and scrambles for E1-4.

## 4. Experiments and thresholds

M1's approved thresholds are kept: turn error ≤ 2°, non-target drift ≤ 1°, penetration ≤ 0.5 mm, radial offset ≤
0.5 mm, pop check ≤ 0.3 mm, rest rotation ≤ 0.5°, open-pad rotation ≤ 0.5°, causality, and Option A (100 % of
trials). Changes are marked **NEW**; all of them are additions or tightenings, never loosenings.

| ID | Trials | Pass criteria |
|---|---|---|
| E1-1 Rest, 10 s | 20 | As for M1, plus **NEW:** the active weld set matches the topology implied by the measured poses (protocol E1-1, M2 row) |
| E1-2 Quarter turns | 24 | As for M1. The turn error metric uses the **unwrapped** cumulative layer angle (the prototype showed a ±180° display artefact on D2) |
| E1-3 Half turns | 22 | As for E1-2 |
| E1-4 Sequences | 40 | As for M1: every observed state agrees with the oracle and the final state is solved |
| E1-5 **Switch transitions** (protocol E1-5, M2 row) | All switches in E1-2 to E1-4 | Per switch: \|ΔKE\| ≤ max(1 % of cube KE, 1 mJ); no activation outside the alignment tolerance; post-activation pose error ≤ 0.01 mm (**NEW:** numeric form of "zero relpose-error activation") |
| E1-5b Misaligned perpendicular turn | U misaligned 0–20° in 1° steps, both signs, then R attempted (42) | **Categorical:** the R request is either refused (logged, R does not move) or completes legally after U realigns. Never an illegal or oracle-mismatched valid state; never a snap. The refusal and completion boundary is reported |
| E1-6a Command without contact | 6 | As for M1 |
| E1-6b Opposed torques | 6 | As for M1, including radial change ≤ 0.5 mm. Opposed requests must be refused |
| E1-6c Corner twist (logged test wrench, P-12) | 8 | As for M1, plus **NEW credibility criteria:** penetration ≤ 0.5 mm throughout, and twist ≤ 2° at 5 N·m |
| E1-6e **Forced switch at a misaligned pose** | 6 (one per face, 5° misalignment) | The request is **refused** and logged; no snapping (protocol E1-6e) |
| E1-7 Sensitivity | As for M1, plus the M2 factors below | Outcome unchanged within the band; any flip is reported as a fragility |
| E1-8 Throughput | As for M1 | Measurement only. The prototype's E1-8 measurement flaw (audited figure taken on a different state) is fixed first |

**E1-7, M2 factors:**

| Factor | Values |
|---|---|
| Unlock tolerance | 0.5, 1, 2° |
| Unlock torque | 0.02, 0.05, 0.1 N·m |
| Weld solref | 0.5, 1, 2 ms |
| Turner stiffness | 5, 20 |
| Grip | 10, 30, 50 N |
| Friction, timestep, iterations | As for M1 |

## 5. Pass logic

**Option A** (approved for M1): every categorical and quantitative criterion holds in 100 % of scored trials of E1-1
to E1-6. E1-7 and E1-8 must be completed and published. G1 also needs user sign-off.

**If M2 fails:** the failure is documented in full, and G1 stays not passed. The options then go back to the user;
a scripted rotation is never a fallback.

## 6. Harness work required before freezing (not yet done)

1. **Move M2 into the frozen code paths.** Put the model builder and switch manager into
   `src/rubiknetic/cube_physics/` (for example `m2_model.py` and `switching.py`) with unit tests:
   * weld re-anchor residual;
   * a refused misaligned switch;
   * an injected illegal `eq_active` write is caught;
   * an injected `qpos` write is still caught.
2. **Scored runner and analyser.** `experiments/E2_scored_m2/` (or similar), reusing the M1 runner and analyser and
   adding the E1-5, E1-5b and E1-6e logic.
3. **Unwrapped turn-angle metric** for half turns.
4. **Fix E1-8:** time the audited and raw runs on the same state.
5. **Report extra switch pairs** (pad-release transients) as counted events, not failures, unless they violate
   E1-5.

## 7. Known issues carried into scoring (INFERENCE, from the prototype)

* **No corner cutting by design.** Perpendicular turns are refused until the cube is within 1° of square. This is
  the main realism gap; D5 (frozen reference) is used to characterise it.
* **A refused face's pads can drag the free unlocked layer** further out of line. In the prototype the observer
  reported "unknown", never a false valid state. E1-5b and E1-6e judge this categorically.

## 8. Decisions requested from the user

1. Approve the configuration in section 1, or change the thresholds or tolerances.
2. Approve the NEW criteria in section 4 (all tighten or add, none loosen).
3. Approve the trial counts and seed range.
4. Approve the harness work in section 6 before any scored run.
