# Unscored dress rehearsal: 0.1 mm piece gap (Amendment 1, A1 condition), 2026-11-15

**UNSCORED. Diagnostic only; never counts toward G1.** Seeds 7000–7999, which are the scored list shifted by +1000.
Runner: `experiments/D8_alignment/rehearsal_gap.py`, which uses the unmodified M4 logic
(`experiments/E4_scored_m4/run.py`: `run_trial` and `apply_m4_criteria`). Configuration: B1 (radial_preload = 0),
48 magnets (4×2 mm N35), piece gap overridden 0.2 → 0.1 mm. Log: `log.txt`. One JSON file per trial.

## Outcome (FACT)
**188 / 204 trials pass. A1's pre-fixed condition was "every M4 criterion in every trial", so it has FAILED, and the
0.1 mm gap is not adopted.**

| Experiment | Pass | Failures |
|---|---|---|
| E1-1 rest (20) | 16 | s7000–7003: rest rotation 0.90 / 0.68 / 0.56 / 0.80° (limit 0.5°) |
| E1-2 quarter turns (24) | 23 | D_s7113: non-target drift 1.06° (limit 1°) |
| E1-3 half turns (22) | 21 | D2_s7207: drift 1.02° |
| E1-4 sequences (40) | 30 | 9 of the 20-move scramble+inverse trials and sexy6_s7312: 10 drift moves (1.00–1.14°) and 4 causality failures |
| E1-5 (42), E1-5s (20), E1-6 (20), E1-6t (16) | all | — |

Over 1,376 moves:
- **Oracle:** 1,376 / 1,376 moves agree with the oracle.
- **Drift:** 12 moves (0.9%) go over 1°; the worst is 1.14°.
- **Causality:** 4 moves fail. In each, layer motion begins 45–85 ms *before* the pad force reaches its threshold.
- **Errors:** turn error is at most 0.43°; penetration is at most 0.31 mm.
- **E1-6m:** the energy/impulse bound holds on every move.

**Magnet validity:**
- Operational trials reached a tilt of at most 3.48° (E1-6b). That is within the validated 5°.
- 24 abuse trials went outside the validated range: E1-6c reached 15.5° and E1-6t 5.26°. Rule 3 labels these; it does
  not fail them.
- The E1-6t passes therefore rest on the magnet model at slightly above its validated tilt.

## Diagnostics
- **The rest failures are seed-specific, not a run-order artefact (FACT).** The four failing rest trials were the
  only rest trials that rebuilt the magnet pair list. Each was the first rest trial in its worker, run after a
  sequence trial.
  - Rerun alone in a fresh process, rest_s7000 gave 0.904° again, identical to the original. rest_s7004 gave 0.122°
    and passed, even though it also rebuilt the list.
  - For comparison, M1 without magnets had rest rotation 0.006–0.037° (seeds 1000–1019).
  - INFERENCE: with magnets, the layers move toward square from the ±1° setup misalignment while at rest, and E1-1
    counts that motion as rest rotation.
- **Causality (INFERENCE, not confirmed):** the layer starts moving before the pads load. A magnet snap pulling a
  nearly square layer is the likely cause.

## What this does not establish
- These are unscored seeds. They say nothing scored about M4 at the registered 0.2 mm gap.
- E1-1 was not rehearsed at 0.2 mm. The earlier gap probe (seeds 95–97) covered sequences only.
