# M5 scored battery — summary (2026-11-17)

**Verdict (Option A, pre-registration revision 8, §5): NOT PASSED — 203 / 204 magnet-arm trials pass.** The single
failure is E1-1 `rest_s10001`, rest rotation 0.560° against the registered limit ≤ 0.5°. Under the pre-registration
this verdict is final: no rerun, no exclusion, no change of threshold (`PHASE_1_M5_PREREGISTRATION.md` §5). G1 is not
passed by M5. (`VALIDATED_RESULT`: frozen `analyze.py`, `RESULTS.md`.)

## Provenance and integrity (`FACT`)
- Pre-registration revision 8 in force (P-50); manifest commit `ee730d9`, which is HEAD at analysis; the tree had no
  tracked changes when `analyze.py` ran (review 7, Y5, checked by hand).
- Working copy `C:\dev\Rubiknetic` (revision 8 location check passed at start; OneDrive was running and outside every
  path the run used).
- One start, no interruption, no resume: 440 records written, 0 orphans, 0 reconciled ledger lines; `STARTS.txt` has
  one line. 2 registered "not run" trials (E1-7, 4×1.5 N35, failed V3).
- `analyze.py` found **0 integrity violations** and 0 missing records.
- Start 2026-11-16 15:57 PST; end 2026-11-17 10:38 PST. The laptop slept overnight, which paused WSL; the runner's
  own timer (`perf_counter`, which does not advance in suspend) measured 11,944 s of run time. Per-trial `wall_s` uses
  the same clock; the largest is 1,199 s (an E1-4 trial), so no record's time includes the sleep. Other heavy jobs
  shared the machine; each M5 worker had about one core. Timing is not a criterion.
- Files: `RESULTS.md` (frozen verdict script), `report.txt` (read-only `rehearsal_report.py`, second reading, with a
  side-by-side against the 0.05 mm rehearsal), `report_m4format.md` (M4's `report()` imported read-only; its "M4"
  header and verdict lines do not apply), `run_log.txt`, `results/`, `results_nomag/`. Neither supplementary report
  is registered; both only read the records.

## Option A, magnet arm (`VALIDATED_RESULT`)

| Experiment | Passed / registered | Note |
|---|---|---|
| E1-1 rest | **19 / 20** | `rest_s10001` rest rotation 0.560° (> 0.5°); all its other checks pass |
| E1-2 | 24 / 24 | |
| E1-3 | 22 / 22 | |
| E1-4 | 40 / 40 | all growth slopes within ±0.003 deg/move (criterion < 0.005) |
| E1-5 forgiveness | 42 / 42 | completes from −13° to +13°; blocked beyond (categorical) |
| E1-5s snap-back | 20 / 20 | worst |U error after 1 s| 0.112° where judged (|δ| ≥ 3°, criterion ≤ 0.5°); 0.163° over all 20 |
| E1-6a / b / c | 6/6, 6/6, 8/8 | E1-6c: 8 trials labelled "magnet model outside validated range" (rule 3, tilt up to 12.55°) |
| E1-6t | 16 / 16 | |
| E1-6m ⟨P⟩ | 1376 / 1376 moves | |

**Move quality, E1-2…E1-4 (1376 moves):**
- Non-target drift: median 0.232°, p90 0.510°, p99 0.652°, max 0.786°.
  - 0 moves above 1°; the margin to the criterion is 0.214°.
- Turn error: max 0.309° (limit 2°).
- Penetration: max 0.310 mm (limit 0.5 mm).
- Causality failures: 0. Oracle agreement: 1376 / 1376 moves, and 86 / 86 sequence finals.
- Turner torque: median 0.218, p99 0.622, max 0.901 N m; 0 moves at the 1 N m clip.
- Rule-2 magnet tilt: max 2.06°, inside the validated 5°.

## The failing trial (`FACT`, with one `INFERENCE`)
- E1-1 rest rotation per trial (n = 20): median 0.163°, p90 0.359°, max 0.560°. Two trials are above 0.4°:
  - 0.560° (`rest_s10001`, fails);
  - 0.498° (`rest_s10000`, passes by 0.002°).

  For comparison, the 0.05 mm rehearsal's 20 rest trials reached at most 0.290° (`report.txt`), and M4 reached 1.03°.
- `rest_s10001` otherwise:
  - solved and valid at t0 and at the end;
  - penetration 0.014 mm, radial change ≈ 0;
  - magnet tilt within range;
  - no numerical failures, no wrench-log entries.
- `INFERENCE`: the rest rotation is **not** explained by the size of the random setup misalignment. Across the 20
  trials, rest rotation and the largest setup misalignment are negatively correlated (Pearson r = −0.51; `rest_s10001`
  had a maximum setup misalignment of 0.45°). So "magnets pulling a misaligned layer into line" is not supported by
  this data as the cause. The cause is not established. Finding it would need an unscored diagnostic with its
  question fixed in advance.
- The rest criterion is inherited unchanged from M1 (`PHASE_1_PREREGISTRATION.md:74`). It must not be relaxed after
  this result (CLAUDE.md; VALIDATION_PLAN).

## Comparison with M4 and the rehearsal (`FACT`; M4 from `E4_scored_m4/results/SUMMARY.md`)

| | M4 (0.2 mm) | 0.05 mm rehearsal (unscored) | **M5 (0.05 mm, scored)** |
|---|---|---|---|
| Option A trials passed | 123 / 204 | 204 / 204 | **203 / 204** |
| E1-1 rest | 14 / 20 (max 1.03°) | 20 / 20 (max 0.290°) | 19 / 20 (max 0.560°) |
| E1-2 / E1-3 / E1-4 | 9/24, 4/22, 0/40 | all pass | all pass |
| Drift median / max | 0.86° / 1.96° | 0.227° / 0.742° | 0.232° / 0.786° |
| Moves with drift > 1° | 440 (in 73 trials) | 0 | 0 |
| E1-5 | 40 / 42 | 42 / 42 | 42 / 42 |
| Oracle | 1376 / 1376 | 1376 / 1376 | 1376 / 1376 |

Reducing the gap from 0.2 to 0.05 mm removed the drift failure that sank M4. The rehearsal predicted this, and the
scored seeds confirm it (`VALIDATED_RESULT`). M5 fails instead on one rest trial.

## Reported-only experiments
- **E1-6n, no-magnet arm (same trial IDs):**

  | | E1-2 | E1-3 | E1-4 | E1-5 | E1-5s | E1-6a | E1-6b | E1-6c | E1-6t |
  |---|---|---|---|---|---|---|---|---|---|
  | passed | 23/24 | 4/22 | 18/40 | 42/42 | 8/20 | 6/6 | 6/6 | 8/8 | 16/16 |

  - Without magnets, E1-5s does not snap back: the error stays near the commanded offset.
  - Long sequences mostly fail.
  - The magnets carry the 0.05 mm result (`INFERENCE`, consistent with the gap study).
- **E1-7 sensitivity:** 52 trials run, 2 not run (4×1.5 N35, failed V3). Three settings flip to FAIL; these are
  fragilities:
  - `timestep=0.00075`: both sequences fail. The result depends on the timestep: 0.25 and 0.5 ms pass, 0.75 ms
    fails.
  - `chamfer=0.001`: the 6-move sequence fails (max tilt 11.97°).
  - `magnet=none`: the 6-move sequence fails.

  All other settings pass both sequences:
  - piece gap 0.025 and 0.1 mm;
  - face gap 0.35 and 1.35 mm;
  - cubie friction ×3 settings;
  - grip 10–50 N;
  - solver iterations 50 and 200;
  - joint friction ×2 settings;
  - 3×1.5 N35 and 4×2 N52 magnets;
  - 0.67 magnet strength scale;
  - misalignment 0–5°.
- **E1-6b/c abuse penetration (reported):** up to 0.80 mm (E1-6b, `opposed_UF_2Nm`, which also ends with
  `observed_valid=False` and F at −50°, a categorical pass) and 0.66 mm (E1-6c). Both are above 0.5 mm, as in the
  rehearsal; they are reported only.
- **Turner torque at 15° twist (E1-6c):** 2.68–2.78 N m.

## What this means
- `VALIDATED_RESULT`: M5 does not pass G1's Option A. The negative result stands and is preserved with all records.
- `INFERENCE`: the M4 failure mode, drift from per-piece play, is resolved at 0.05 mm with magnets.
  - The remaining failure is a rest rotation 12% above the limit in 1 of 20 trials.
  - Two of the 20 rest trials are near the limit (0.498° and 0.560°), so this is not a single outlier far from the
    rest of the distribution.
- Next steps are the user's decision. Options already on record (T12 briefing; nothing here is applied):
  - an unscored diagnostic of rest behaviour with its question fixed in advance;
  - an engineering review;
  - a new mechanism or variant under a new pre-registration with new seeds.

  Thresholds are not loosened.
- E1-8 was not run (it gates sign-off only).
