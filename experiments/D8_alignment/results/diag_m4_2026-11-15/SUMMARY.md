# Why M4 fails the M1 criteria: unscored diagnostic, 2026-11-15

**UNSCORED. Diagnostic only.** Approved by the user ("approved, lets do it") after the 0.1 mm rehearsal failed
(P-25). Seeds: rehearsal seeds (7000–7999, re-simulated) and new diagnostic seeds 9000–9599, which are outside every
registered range. Scripts are in `scripts/`. They were run from the session scratchpad, so their absolute paths point
there.

## 1. Drift comes from the B1 base's per-piece play, not from the magnets (FACT)
| 0.2 mm piece gap (registered); 3 × 40-move scramble+inverse; seeds 9400–9402 | Drift median | p90 | max | Moves > 1° | Rest rotation, 4 trials (limit 0.5°) |
|---|---|---|---|---|---|
| B1 + 4×2 mm N35 (M4 nominal) | 0.88° | 1.49° | 1.69° | 46 / 120 | 0.20, 0.38, 0.98, 0.53° |
| B1 + 3×1.5 mm N35 (weaker) | 0.93° | 1.48° | 1.73° | 56 / 120 | 0.41, 0.71, 0.44, 0.44° |
| B1, no magnets | 0.83° | 1.40° | 1.98° | 39 / 120 | 1.03, 1.02, 1.30, 1.30° |
| *M1 scored (radial preload 1 N, no magnets; 1,376 moves)* | *0.013°* | *0.033°* | *0.71°* | *0* | *≤ 0.04°* |
| *B1 + 4×2 mm at 0.1 mm gap (rehearsal; 1,376 moves)* | *0.46°* | *0.83°* | *1.14°* | *12* | *0.05–0.90°* |

- **Correction (disclosed).** A first comparison in this session set the M4 rehearsal against M1 and read the 35× rise
  in drift as a magnet effect. That comparison confounded two changes: the magnets were added and M1's 1 N radial
  preload was removed (B1). On the same B1 base the magnets barely change drift, and weaker magnets do not reduce it.
- Drift scales with the piece gap. At 0.2 mm the B1 + magnet median is 0.88°; at 0.1 mm it is 0.46°.
- The D8 README already records this play: "Pieces in B1 sit 1–2° off square" (stage-1 r2).
- At rest, the magnets do help B1 (0.2–0.98° against 1.0–1.3° without), but not enough to meet 0.5°.
- Every move in every arm agreed with the oracle (360 / 360). Turn error was at most 0.57° with magnets and 2.6° without.

## 2. What "drift" is, move by move (time-resolved re-simulations, 5 ms resolution)
- **During moves, the drifting pieces are in the opposite layer and move *toward* square.** In D_s7113 move 0
  (drift 1.057°), piece 25 went from −1.031° to +0.027°. The worst non-target error fell from 1.03° to 0.05°. The
  same happened in D_s7112 (0.82° → 0.12°) and in scr20inv_s7402 move 26 (1.10° → 0.18°). Their pre-move errors
  alternate in sign around the layer. INFERENCE: neighbouring pieces were held in twisted states within their play,
  and the move released them.
- **At rest, pieces move *away* from square.** In rest_s7000 a collective event at t = 2.45 s moved piece 9 from
  1.17° to 1.44° off square and piece 2 from 1.05° to 1.31°. All six layers shifted at the same moment. The worst
  error rose from 0.97° to 1.48° over the trial. Between events there is a slow creep of about 0.01°/s, which M1
  without magnets does not show.
- INFERENCE: with play and no preload, pieces have several resting states within their play, and they jump between
  them. M1's per-piece criteria (drift 1°, rest 0.5°) count any such jump, in either direction.

## 3. Results depend on process history: a runner reproducibility defect (FACT)
| sexy6_s7312 (rehearsal seed) | Move-12 drift | Layer-motion time | Causal |
|---|---|---|---|
| Original rehearsal worker | 0.745° | 27.033 s | **no** |
| Fresh process, run twice | 0.37033° (bit-identical) | 27.1285 s | yes |
| Fresh process, after rest_s7004 | 0.39097° | 27.376 s | yes |

- In a fresh process the runner is deterministic. D_s7113, D_s7112, scr20inv_s7402 and rest_s7000 all reproduce
  their records bit for bit.
- A worker reuses its magnet system across trials. When the previous trial ended near the solved pose, the next trial
  starts with the inherited neighbour list rather than a fresh one. The force law is the same, but the floating-point
  summation order differs, and the dynamics amplify that.
- **Consequence 1:** the four causality failures are chance events at a rate, not properties of their seeds. With the
  list reset before each trial, 0 of 360 moves at 0.2 mm were non-causal, in every arm.
- **Consequence 2:** before any scored magnet run, the runner must reset the neighbour list at the start of every trial
  (`MagnetSystem`: `ii, jj = ii_all, jj_all; p_ref = None`), so that a result does not depend on worker scheduling.
  This changes no physics. **Approved and applied (P-26):** `MagnetSystem.reset_neighbour_list()` is called in
  `experiments/E4_scored_m4/run.py:run_trial`. The test is `tests/test_magnets.py::test_reset_neighbour_list_makes_a_reused_system_match_a_fresh_one`.
  The end-to-end check result is in `history_test_after_fix.jsonl`.
- The 0.1 mm rehearsal (P-25) ran before this fix. Its per-trial values depend on worker scheduling, but its
  conclusion does not: drift over 1° appeared in 11 trials and does not depend on the history effect (see §1).

## 4. Magnet size checks (E1-7)
- **3×1.5 mm N35:** all pass; validated tilt 7.5°.
- **4×1.5 mm N35:** **FAIL**. The V3 pair force error is 5.65% against a 5% tolerance (complete rerun). The size is
  not validated, and the tolerance is unchanged. See `../checks_history/README.md`.
- **Snap at 0.2 mm** (E1-5s form, seeds 9500–9503): 4×2 mm passed 3 of 4 trials (+3° left 0.60°). 3×1.5 mm passed
  2 of 4 (−3° → 0.56° and −5° → 0.66°). So the weaker size also snaps less reliably.

## What this does not establish
- These are unscored seeds with small samples (3 sequences and 4 rest trials per arm).
- **Where B1's play comes from (FACT, from the model code).** B1 has no radial joint at all: `build_m1_xml` creates the
  radial slide only when `radial_preload > 0` (`src/rubiknetic/cube_physics/m1_model.py:146`). So B1 pieces are ball
  joints at a fixed radius, and their play is angular clearance between neighbouring pieces. The D8-1b design proposal
  (§2) records about 12° of twist play at 0.02 N·m for that construction (D1 config J). M1's 1 N preload removes the
  play by wedging pieces together, at the cost of a higher turning torque and the radial change under opposed torque
  that ruled out B2/B2E. A first follow-up proposed in this session ("lock the radial travel") was based on a wrong
  premise. B1's radius is already rigid, so that test was not run.
