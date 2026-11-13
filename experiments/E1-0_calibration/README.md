# E1-0 — M1 calibration pilot (UNSCORED)

**Status:** `CALIBRATION` — not a G1 result. Nothing here passes or fails a gate. Its purpose (per
[`PHASE_1_2_VALIDATION_EXPERIMENTS.md`](../../docs/research/PHASE_1_2_VALIDATION_EXPERIMENTS.md) §1)
is to find a parameter set in which a contact-driven turn is possible, publish **every** setting tried,
and supply evidence for pre-registering the ⟨P⟩ thresholds of E1-1…E1-8.
**Model:** M1 contact-emergent topology (P-01/P-02, approved 2026-11-12), implemented in
`src/rubiknetic/cube_physics/m1_model.py`. **Rig v0:** core fixed to the world ("cube on a fixed axle"),
six face turners (hinge + two force-limited sliding pads) acting only through contact.
**Environment:** MuJoCo 4.0.1, Python 3.12.3, NumPy 2.5.4, WSL2 Ubuntu 24.04, AMD Ryzen 7 250
(16 threads). Code: uncommitted working tree at the time of each run (full parameter sets are stored
in every JSON record; the code changes between batches are listed below).

Raw records: `results/*.json`. Table: `results/SUMMARY.md` (regenerate with `summarize.py`).

## What was learned (tags refer to `results/`)

| # | Finding | Evidence | Tag |
|---|---|---|---|
| 1 | **FACT (sim):** with narrow 15 mm pads that touch only the edge cubie, the edge pushes the neighbouring corner, whose push line tilts it down onto the side centre: jam at ≈7°. | contact trace: corner–side-centre force 22 N at layer −8.8° | c01, diag |
| 2 | **FACT (sim):** idle turner pads intruded into the corner sweep radius (≈40 mm) of perpendicular layers, a rig error: stall at ≈−62°. Fixed by `pad_open_clearance` 6 → 14 mm. | contacts `pad_Ba`/`pad_Fb` with U corners | c03–c08 |
| 3 | **FACT (sim):** without a radial preload, gravity sag of ball-jointed cubies (≤1.2°) relative to the hinged centres creates steps that jam turns. Success flips with tiny rig changes (c09 passes, c10 fails); 20 N grip makes it worse (c15). | c09–c16 vs c11 (gravity off: 6/6) | c09–c16 |
| 4 | **FACT (sim):** a spring-loaded radial retention slide per corner/edge cubie (precedent: OpenAI robogym cube XML, source S02) removes the gravity jam: all preloaded configs pass 6/6, incl. 15 mm pads and 20 N grip. | c17–c23 | c17–c23 |
| 5 | **FACT (sim):** contact softness must scale with the 3.4 g cubie mass. With `solref` 2 ms at 1 ms step, penetrations were 0.6–2 mm; with 1 ms at 0.5 ms step, ≈0.2–0.3 mm. | c20–c22 vs c17–c19 | |
| 6 | **FACT (sim):** long multi-axis sequences on the candidate config: `R U R' U'`×6 (24/24), two 20-move scrambles + inverse (40/40 each), `F2 B2 L2 R2 U2 D2` (6/6); every intermediate observed state matched the oracle; edit audit clean. | c25, c26, c29, c30 | |
| 7 | **FACT (harness):** under a forced jam MuJoCo diverged (`mjWARN_BADQACC`) and **auto-reset the state to the solved initial pose**, which can masquerade as success. The audit now treats any such warning as a void trial (`NumericalFailure`). Earlier jam readings showing exact 0.0° rotations were reset artefacts and are discarded. | console output of the first negative-control batch | legacy |
| 8 | **FACT (sim):** root cause of the divergence: a pad dragged a misaligned cubie outward through MuJoCo's *soft default* joint limit on the radial slide (0.2 mm stop crept to 4.6 mm), then the solver blew up. Making the retention stop as stiff as the contacts (`radial_solreflimit` 1 ms) fixed it at 1–2 N·m and 10–30 N grip. Pyramidal cones avoided divergence but allowed 9 mm penetrations, so they were rejected. | `blow.py` trace; neg batches E–M | |
| 9 | **FACT (sim):** forgiveness angle of M1 (E1-5 pilot, nominal): with U misaligned 4.7°, 9.6° and 11.6°, R completes **and pushes U back into line** (U change ≈ +misalignment: emergent corner cutting); the observed state matches the oracle for the observed move R. At 14.6°, 19.6° and 29.6° R is blocked (≤5.5°) and the state reads UNKNOWN; reversing by measured amounts restores solved. Forgiveness angle ≈12–15°. With 15 mm pads at 19.6°, R reached −74.5° (UNKNOWN), so the boundary depends on the rig. Jam (U+R opposed, 1–2 N·m, 10–30 N): U 16–21°, R ≈4–5°, no separation (radial offset ≤0.37 mm), penetration 0.37–0.64 mm. No numerical failures, edit audit clean in all 12 runs. | `neg_*.json` (final batch) | neg_* |
| 10 | **FACT (sim):** final nominal config (with stiff retention stop, divergence monitoring on): `U U' R R' F F'` 6/6; `R U R' U'`×6 24/24; 20-move scramble + inverse, seeds 1 and 3, 40/40 each; half turns 6/6; grip 30 N and 50 N 6/6. Max turn error 0.68°, max opposite-layer drift 0.07°, max turner torque 0.63 N·m, max penetration 0.34 mm, zero numerical failures, edit audit clean. | c31–c37 | c31–c37 |
| 11 | **ASSUMPTION / limitation:** turning torque (0.16–0.68 N·m here) is set by the chosen preload and friction values, **not** by real-cube data (O-09). | | |

## Candidate nominal configuration (proposed for pre-registration, `PROPOSAL`)

The `M1Params` defaults now equal this set (c21 plus the stiff retention stop):
`pitch` 19 mm, `gap` 0.2 mm, `chamfer` 1.4 mm, cubie mass 3.4 g, cubie friction (0.2, 0.0025, 0.0005)
condim 3, contact `solref` (1 ms, 1), `solimp` (0.95, 0.99, 0.5 mm), radial preload 1 N, radial stiffness
500 N/m, radial range (−1, +0.2) mm, radial limit `solref` 1 ms; pads 45 × 10 × 5 mm, μ 0.8, condim 4,
grip 10 N, open clearance 14 mm, slide damping 100 N·s/m; turner torque limit 1 N·m;
timestep 0.5 ms, implicitfast, elliptic cone, impratio 10, Newton, 100 iterations, tol 1e-10.
Original pre-calibration defaults: pads 15 mm wide, clearance 6 mm, slide damping 2, no radial preload,
`solref` 2 ms, timestep 1 ms (see c01).

## Deviations from the proposed E1 protocol (need your approval)

1. **Rig v0 fixes the core to the world** instead of holding non-turning layers by a contact fixture.
   Holding the core is equivalent to holding the six centres; slice moves (M, E, S) are therefore
   impossible in this rig, which is acceptable because the project uses outer-face turns only.
   A free-core, contact-held variant is still required before Phase 2.
2. **M1 now includes a radial retention slide + preload** (20 extra DOF), following the OpenAI precedent.
   This is a refinement inside the approved M1 interpretation, not a new mechanism, but it is a modelling
   choice you should see explicitly.
3. **E1-6(c) corner-twist control not yet run:** it needs either a physical twist probe or an approved,
   logged external-wrench mechanism (`xfrc_applied`), which the audit currently forbids.
4. **E1-6(d) expectation needs revision:** a real speed cube can "corner-cut" (a perpendicular turn pushes a
   misaligned layer back into line). The categorical requirement should be "no illegal or oracle-mismatched
   state", not "always blocked at 20°".

## Process issues found and corrected (recorded for honesty)

* The first sweep launcher dropped each config's tag, so 4 runs were written under wrong names with the
  wrong (default) settings. Those files were deleted and the sweep re-run correctly (c01–c08).
* Early negative-control records were named by case only, so parallel and later runs overwrote each other,
  and they did not store the full parameter set. Survivors are quarantined in
  `results/legacy_negative_controls/` (code version ambiguous; do not use) and the controls were re-run
  with unique names and full parameters.
* c01–c30 were run before the stiff retention limit (finding 8) and before the half-turn angle-wrap fix
  in the turn-error metric (affected one c26 `R2` reading of "135°"; the oracle check was unaffected).

## Throughput note (not E1-8)

Single process ≈5,100 steps/s for the bare cube at rest (no rig, 40 contacts, 1 ms). With the full rig and
preload at 0.5 ms the long sequences ran at ≈0.3× real time per process while 6–8 processes shared the
CPU. A proper E1-8 benchmark (isolated, single vs multi process) has not been run.
