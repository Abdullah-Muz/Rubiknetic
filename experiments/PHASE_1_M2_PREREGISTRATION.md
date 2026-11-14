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

## 9. Amendment 1 (2026-11-13, before any scored M2 trial)

**Approved by the user:** "fully approved".

**Trigger** (harness review, FACT, verified independently over seeds 2000–2999): the ±1° per-face setup
misalignment compounds on corners and edges. The median worst piece is 1.22°, and 83 % of seeds exceed the 1.0°
unlock tolerance. M2 would refuse most turns and fail E1-2 to E1-4 by construction.

| # | Change |
|---|---|
| A1 | **Setup misalignment ±0.5° per face** for every M2 trial that draws a setup. The compound worst piece is ≤ 0.83°, inside the 1.0° unlock tolerance. **Disclosed as easier than M1's ±1° setup.** It is M2's design envelope: M2 needs a near-square cube. Misalignment tolerance is tested separately by E1-5b and E1-6e, which are unchanged |
| A2 | **The unlock request rule becomes shear-dominance** (study D6, `experiments/D6_free_core/`). For each face F, the shear is the torque about F's axis, in the core frame, that all gripper contacts apply to the cubies currently in F's layer. F requests only if \|shear\| ≥ 0.05 N·m **and** ≥ 1.5× the next face's \|shear\|. Otherwise every face above threshold requests, and the cube refuses (ambiguous loads). All other unlock, relock and refusal conditions in section 1 are unchanged. Reason: in the fixed-core rig it behaves as the original rule; with a hand-held cube (Phase 2) the original rule unlocked the wrong layer. Equal opposed torques (E1-6b) are refused by construction |
| A3 | **E1-7 turner stiffness factor** uses damping kv = 0.04 × kp (0.2 at kp 5, 0.8 at kp 20) |
| A4 | **E1-6e** uses the harness's fixed map of which perpendicular face is requested for each misaligned face (`scored_m2._PERPENDICULAR`) |
| A5 | **The E1-5 post-activation pose error** uses only the translational constraint rows, in mm, with rotation reported separately in degrees. This fixes a units mix-up in the prototype |

**Unchanged:** every threshold, the pass logic (Option A), the trial counts and the seed range.

## 10. Amendment 2 (2026-11-13, before any scored M2 trial)

**Approved by the user:** "I agree with your recommendations".

**Trigger** (harness smoke checks, unscored seeds 96–97, FACT):

* **Setup against relock.** With the ±0.5° setup (A1), a 9-move sequence got 1/9. U unlocked, but its cubies carry
  compound setup misalignment above the 0.5° per-cubie relock tolerance, so U never relocked and later turns were
  refused. With a perfectly square start the same sequence passed 9/9.
* **E1-6b.** With perpendicular opposed faces, the other face's pads also touch the first layer, so the shears are
  not equal. One layer dominates, unlocks and completes one legal turn, while the other face is refused.
  **Correction:** Amendment 1 (A2) wrongly stated that equal opposed torques are "refused by construction". That holds
  only when the shears are equal.

| # | Change |
|---|---|
| B1 | **The per-cubie relock tolerance becomes 1.0°**, equal to the unlock tolerance. The centre-hinge relock tolerance stays 0.5°. Reason: symmetric, so any cube allowed to unlock can relock. It is a model-rule parameter, not a pass threshold. **Conditional:** it is adopted only if an unscored smoke check of the 9-move sequence with the ±0.5° setup passes 9/9 with E1-5 clean. Otherwise the fallback is setup ±0.25° per face, with relock unchanged |
| B2 | **E1-6b uses M1's categorical criterion:** not both layers ≥ 45°; the state is UNKNOWN, or legal and oracle-consistent with the observed moves; radial change ≤ 0.5 mm. It adds: **never two layers unlocked at the same time.** "Opposed requests must be refused" is withdrawn. **This is a loosening of the approved wording, made before any scored trial and disclosed here.** Reason: one legal turn by the dominant layer is physical and is what M1 was allowed |

**Unchanged:** every other threshold, the pass logic, the trial counts and the seed range.

## 11. Amendment 3 (2026-11-13, before any scored M2 trial)

**Approved by the user:** "approved".

**Amendment 2 outcome.** B1's condition was not met. In unscored smoke checks with the ±0.5° setup and 1.0° per-cubie
relock, the 9-move sequence got 1/9 and 1/9 with the default turner, and 4/9, 9/9 and 4/9 with the stiffer one.
**Amendment 2's pre-approved fallback is therefore in force:** setup **±0.25° per face**, with the per-cubie and
hinge relock tolerances both **0.5°**.

**Trigger for this amendment** (FACT). The default turner (turn_kp 5) leaves layers 0.8–1.4° from square. That is
above the 0.5° hinge relock tolerance, so the layer stays unlocked and later turns are refused: the fallback got 7/9
and 4/9 with it. With **turn_kp 20 and turn_kv 0.8**, the fallback passed **9/9 on all 3 smoke seeds** (95–97), with
worst error 0.16–0.31°, no E1-5 failures and peak turner torque ≤ 0.18 N·m. E1-6b also passed.

| # | Change |
|---|---|
| C1 | **Every scored M2 trial uses the turner at turn_kp 20, turn_kv 0.8.** In E1-7 the turner factor becomes {5, 20}, so the default turner is reported as a sensitivity result. Reason: the turner is the test probe's controller, not the cube model. **Disclosed:** this reduces direct comparability with M1, which was scored with turn_kp 5 |

**Disclosed limitation** (INFERENCE). M2 is unforgiving: it needs every layer within about 0.5° of square, both at
setup and at the end of each turn. This is reported as a property of M2, and it becomes a **Phase 2 requirement**:
the robot's turning controller must finish turns within about 0.5°. D5, the frozen reference, characterises how a
forgiving cube behaves by comparison.

**Unchanged:** every threshold, the pass logic, the trial counts and the seed range.
