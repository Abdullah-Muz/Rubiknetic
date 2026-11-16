# Unscored dress rehearsal: 0.05 mm piece gap, 2026-11-15

**UNSCORED. Diagnostic only; never counts toward G1.**
- **Pass condition:** fixed before the run, in `CONDITION.md` (committed in `248720f` while the run was in progress,
  before any summary).
- **Seeds:** 8000–8655, the scored list shifted by +2000. The range had not been used before.
- **Runner:** `experiments/D8_alignment/rehearsal_gap.py 0.00005 --jobs 4 --shift 2000`, using the unmodified M4 logic
  (`experiments/E4_scored_m4/run.py`: `run_trial` and `apply_m4_criteria`). It includes the P-26 runner fix.
- **Configuration:**
  - B1 (radial_preload = 0) with 48 magnets, 4×2 mm N35;
  - piece gap overridden 0.2 → 0.05 mm;
  - the magnet wall stays 0.4 mm, so the face gap is 0.85 mm.

  All three were verified in every trial file: `params.gap` = 5e-05, `radial_preload` = 0 and `n_magnets` = 48 in
  204 / 204.
- **Run:** wall time 7,812 s, 4 workers. Log in `log.txt`, one JSON file per trial.
- **Analysis:** `report.txt` was produced by `rehearsal_report.py`, which reads the stored verdicts and does not
  re-judge them. On the 0.1 mm run it reproduced that run's summary; its one mismatch was the trial count corrected in
  P-28. The main session cross-checked the pass counts, the configuration and the false flags independently.

## Outcome (FACT)
**204 / 204 trials pass every M1 and M4 criterion. CONDITION.md's condition is MET.** Every stored `pass` and
`pass_m1_criteria` flag is true. No `ok_*` flag is false anywhere, in any trial or move.

| Experiment | Pass | Notes |
|---|---|---|
| E1-1 rest (20) | 20 | Rest rotation median 0.10°, max 0.29° (limit 0.5°). Penetration ≤ 0.008 mm |
| E1-2 quarter turns (24) | 24 | |
| E1-3 half turns (22) | 22 | |
| E1-4 sequences (40) | 40 | Final state matches the oracle in 86 / 86 sequence trials (E1-2 to E1-4) |
| E1-5 forgiveness (42) | 42 | |
| E1-5s snap (20) | 20 | Offsets up to ±8°; U error after 1 s is −0.19 to +0.13° |
| E1-6 abuse (20) | 20 | E1-6a open-pad rotation 0.02–0.09°. E1-6b opposed torque: radial change 0, penetration 0.38–0.61 mm (reported only). E1-6c corner twist at 5 N·m: 23.6–24.5°, 2.63–2.78 N·m at 15°, penetration 0.64–0.65 mm (reported only) |
| E1-6t toy-standard (16) | 16 | 10.4–10.9° twist at ±0.45 N·m; final state solved; penetration 0.18–0.19 mm against the E1-6t limit of 0.5 mm (`run.py:505`). The stored field is named `penetration_mm_reported_only`, but for E1-6t it is a criterion |

Over 1,376 moves:

| Quantity | 0.05 mm (this run) | 0.1 mm rehearsal (P-25) |
|---|---|---|
| Trials passing | **204 / 204** | 188 / 204 |
| Oracle agreement | 1,376 / 1,376 | 1,376 / 1,376 |
| Non-target drift, median / p90 / p99 / max | **0.23 / 0.49 / 0.65 / 0.74°** | 0.46 / 0.83 / 0.99 / 1.14° |
| Moves with drift > 1° (trials) | **0 (0)** | 12 (10) |
| Causality failures | **0** | 4 |
| Turn error max | 0.32° | 0.43° |
| Move penetration max | 0.30 mm | 0.31 mm |
| E1-1 rest rotation max | **0.29°** | 0.90° |
| Turner torque, median / p99 / max | 0.21 / 0.56 / **1.00** N·m | 0.10 / 0.65 / 0.88 N·m |
| Magnet tilt, operational trials (rule 2), max | **2.08°** (E1-5) | 3.09° (E1-5) |
| Magnet tilt, abuse trials (rule 3), max | 12.56° (E1-6c) | 15.54° (E1-6c) |
| Rule-3 "outside validated range" labels | 8 (all E1-6c) | 24 |

- Both runs use the same pre-registered trial slots and move strings, and every slot is paired. The seeds differ, so
  the random setup misalignments differ.
- **E1-6t stays inside the validated magnet range at 0.05 mm** (max tilt 3.54°, below 5°). At 0.1 mm it went above it
  (5.26°).
- Only E1-6c leaves the validated range. As at every gap, rule 3 labels those trials and does not fail them.

## Observations that are not criteria (reported)
- **Turner torque.** The median turning torque is about 2× that of the 0.1 mm rehearsal (0.21 against 0.10 N·m). One
  move reached the turner's 1.0 N·m clip: scr20inv_s8416, move 22, U2.
  - That move completed correctly: oracle-correct, every flag true, drift 0.05°.
  - The stored value is the peak over the whole move, so the clip may have lasted a single 0.5 ms step. Its duration
    is not stored.
  - Without magnets, 0.05 mm jams with the torque at the clip (gap study, P-27). See
    `../diag_m4_2026-11-15/audit_2026-11-15/torque_saturation.md`.
  - INFERENCE: torque headroom is smaller at 0.05 mm. Any pre-registration should report it.
- **Abuse penetration** reaches 0.61 mm (E1-6b) and 0.65 mm (E1-6c). M4 registers these as reported only.

## What this does not establish
- **These are unscored seeds.** The result is evidence for drafting a new pre-registration, not a G1 result.
- **The gap was chosen after the unscored diagnostics at 0.2, 0.1 and 0.05 mm** (P-25 to P-27). A scored run on fresh
  seeds is needed.
- **Whether a 0.05 mm clearance is realistic is ASSUMPTION.**
  - The only numeric source found is a 2×2×2 puzzle patent, US 6,217,023 B1, which says "the clearance between
    pieces being of the order of 0.05 mm and being a matter for trial and error by the puzzle designer".
  - No measurement of a real 3×3 was found. Generic ABS moulding tolerances of 0.05–0.1 mm (fine) to 0.1–0.325 mm
    (commercial) make 0.05 mm the tight end of what is achievable. These figures come from a manufacturer's guide
    that the main session has not checked.
  - A physical measurement (R1 bench) would settle it.
- Nothing here bears on M4 at its registered 0.2 mm gap.
