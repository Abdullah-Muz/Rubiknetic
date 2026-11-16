# Scored M4 battery at the registered 0.2 mm piece gap, 2026-11-16

**SCORED. G1 result for M4: NOT PASSED** (Option A, `PHASE_1_M4_PREREGISTRATION.md` §5). Approved in P-32;
outcome recorded in P-37.

- **Scope (P-32):** the operational experiments E1-1 to E1-6, E1-5s and E1-6t; 204 trials; seeds 6000–6655.
  E1-6n (no magnets) and E1-7 (sensitivity) were not run; G1 needs them only for a pass. E1-8 (throughput) is still
  outstanding.
- **Runner:** unmodified `experiments/E4_scored_m4/run.py` with the P-26 fix, `--jobs 4`, experiments run one after
  another (E1-4, E1-2, E1-3, E1-5, E1-5s, E1-6, E1-6t, E1-1). Start-up checks passed. Wall time 09:26–11:04
  (about 5,900 s). Log in `log.txt`.
- **Configuration, checked in every trial file (FACT):** `params.gap` = 2e-4 (0.2 mm), `radial_preload` = 0,
  `magnets.n_magnets` = 48, `mechanism` = "M4" in 204 / 204. The seeds span 6000–6655; the only repeated seeds are
  the 10 E1-5s ±delta pairs, by design (the 0.05 mm rehearsal has the same pattern).
- **Source commits (FACT, disclosed).** Each experiment records the HEAD at its start, and three commits appear:
  `1dc578c` (E1-4), `abe4d64` (E1-2 to E1-6t) and `0956704` (E1-1). The later two were committed during the run.
  `git diff --stat 1dc578c 0956704` shows changes only to `docs/DECISION_LOG.md`, the M5 pre-registration, the two M5
  review files and `R1_real_cube_bench/LITERATURE.md`. No code, lock file or M4 frozen path changed, and every
  experiment passed the clean-commit check at its start.

## Verdict (FACT)

Two independent readings of the stored records agree.

| Experiment | Pass / trials | Failing criterion |
|---|---|---|
| E1-1 rest (20) | **14 / 20** | rest rotation 0.50–1.03° (limit 0.5°) in 6 trials |
| E1-2 quarter turns (24) | **9 / 24** | non-target drift 1.09–1.96° (limit 1°) |
| E1-3 half turns (22) | **4 / 22** | drift |
| E1-4 sequences (40) | **0 / 40** | drift in every trial; causality in 5 moves; growth slope 0.0051 and 0.0080°/move in 2 trials (limit < 0.005) |
| E1-5 forgiveness (42) | **40 / 42** | M4 rule 2: magnet near-pair tilt 5.19° and 5.18° (validated range 5°), forgive_+15 and forgive_+16 |
| E1-5s snap (20) | 20 / 20 | |
| E1-6a / b / c (6 / 6 / 8) | 20 / 20 | |
| E1-6t toy-standard (16) | 16 / 16 | |
| E1-6m ⟨P⟩ (1,376 moves) | 1,376 / 1,376 | |
| **Total** | **123 / 204** | |

- **`analyze.py`** (frozen; run unmodified) wrote `RESULTS.md` with "**NOT PASSED**". As recorded in P-33 and in review 1
  of M5 (R2), its expected counts omit E1-6t, so its verdict line ignores E1-6t. The per-trial `pass` flags include
  E1-6t (16 / 16 pass), so the omission does not change the verdict.
- **`report.txt`** was produced by `../../D8_alignment/rehearsal_report.py`, which reads the stored verdicts without
  re-judging them and compares them with the 0.05 mm rehearsal. It reproduces the same counts, and its
  `analyze._mx` cross-check matches `RESULTS.md` (drift max 1.960°, turn error max 0.665°, penetration max 0.311 mm).

## Quantities (FACT, over 1,376 moves)

| Quantity | M4 scored, 0.2 mm | 0.05 mm rehearsal (P-30, unscored) |
|---|---|---|
| Trials passing | **123 / 204** | 204 / 204 |
| Oracle agreement | 1,376 / 1,376; final state correct in 86 / 86 sequence trials | 1,376 / 1,376 |
| Non-target drift, median / p90 / p99 / max | **0.86 / 1.32 / 1.68 / 1.96°** | 0.23 / 0.49 / 0.65 / 0.74° |
| Moves with drift > 1° (trials) | **440 (73)** | 0 (0) |
| Causality failures | 5 | 0 |
| Turn error max | 0.67° | 0.32° |
| Move penetration max | 0.31 mm | 0.30 mm |
| Radial position above nominal, max | ≈ 0 (7.6e-14 mm) | |
| E1-1 rest rotation, median / max | 0.34 / **1.03°** | 0.10 / 0.29° |
| Turner torque, median / p99 / max | 0.10 / 0.68 / 0.86 N·m | 0.21 / 0.56 / 1.00 N·m |
| Magnet tilt, operational trials (rule 2), max | **5.19°** (E1-5) | 2.08° |
| Magnet tilt, abuse trials (rule 3), max | 23.57° (E1-6c) | 12.56° |
| Rule-3 "outside validated range" labels | 25 (16 E1-6t, 8 E1-6c, 1 E1-6b) | 8 |

Abuse trials (reported values; rule 3 labels them, it does not fail them):
- E1-6a open-pad rotation 0.04–0.45°.
- E1-6b radial change ≈ 0; penetration 0.43–0.70 mm (reported only).
- E1-6c corner twist 38.7–41.2° at 5 N·m; 0.75–0.93 N·m at 15°; penetration 0.96–1.01 mm (reported only).
- E1-6t twist 17.8–18.6° at ±0.45 N·m; final state solved in 16 / 16; penetration 0.20–0.21 mm against its 0.5 mm
  criterion. Its magnet tilt (8.6–8.8°) is outside the validated 5°, so all 16 carry the rule-3 label.

## Interpretation

- **FACT:** M4 fails G1 at its registered gap on three criteria: non-target drift (73 trials), rest rotation
  (6 trials) and, in 2 E1-5 trials, rule 2 (magnet tilt beyond the validated range). The E1-4 growth slope also fails
  in 2 trials that already fail on drift.
- **INFERENCE:** the failure mode matches the expectation recorded before the run (P-32: "failure on drift") and the
  unscored 0.2 mm diagnostic (`../../D8_alignment/results/diag_m4_2026-11-15/SUMMARY.md`: drift median 0.88°,
  max 1.69°; rest 0.20–0.98°). The scored run also failed rest rotation and, narrowly, rule 2, which P-32 did not
  name.
- **INFERENCE:** the physical-to-logical layer is sound at 0.2 mm (oracle agreement in every move); the failures are in
  how square the non-turning pieces stay, which the diagnostics attribute to piece clearance (P-27).
- Under P-32, M4 is closed as superseded by M5 (0.05 mm gap). This result is M4's formal record. M5's pre-registration
  was frozen against this run (its freeze rule), and its third review was instructed not to read this folder.

## Files
- `E1-*/` one JSON record per trial (204).
- `log.txt` runner log; `RESULTS.md` frozen-analyzer output; `report.txt` independent read-only report.
