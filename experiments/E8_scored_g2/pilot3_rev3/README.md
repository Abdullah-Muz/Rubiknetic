# G2 pilot 3 (revision 3; UNSCORED; seeds 29400–29453; 2026-11-27)

> **Magnet-free (P-130, found 2026-11-27):** this pilot ran **without the M7 L0 magnets**, through a bug in the two-arm scene
> (`two_arm.py` installed the magnet callback, then building arm B's IK model uninstalled it). The records below are kept
> as recorded and are not evidence for the system under test. The magnets-on repeat is [`../pilot4_magnets/`](../pilot4_magnets/README.md) (P-131, P-132).

**Why:** review 2, required items 1 and 2 (P-126). Run with `run.py pilot3 --smoke-dir /home/fwdev/g2pilot3 --jobs 8`
at commit `63f2ae2` (the revision-3 code, without the load-retry change). The records are copied here (`results/`,
`run_log.txt`). 48 trials in 1841 s.

## Extreme start misalignment (stop disabled; the U face forced, the other faces drawn)
| Group | n | F/T τ_z first turn | Result |
|---|---|---|---|
| U′, U at −0.80 … −1.00° | 10 | 0.21–**0.47** N·m | all pass |
| U2, U at −0.80 … −1.00° | 10 | ≤ 0.47 | all pass |
| U′ and U2, U at +0.80 … +1.00° | 10 | ≤ 0.47 | all pass |
| U, U at ±1.00° | 4 | ≤ 0.47 | all pass |

- **The steep rise extrapolated in review 2 (to about 1.0 N·m at −0.97°) did not occur** (`FACT`): the maximum over the
  34 forced extremes is 0.47 N·m.
- The worst first turn seen anywhere is still 0.674 N·m (pilot 2, U′). `INFERENCE`: a combination of several faces'
  misalignment, not U alone.
- **The 1.0 N·m stop has a 1.49× margin over every first turn piloted** (about 110 of them).

## Confirmation at the frozen configuration (F/T stop 1.0 N·m)
| Case | n | Result |
|---|---|---|
| `two_layer` | 4 | all detected: F/T stop at 1.05–1.11 N·m after 3.7–4.0° of roll; core slip ≤ 0.27 mm |
| `jam` | 2 | stop at 38.0° and 40.8° (window 20–50°); core slip 0.12 / 0.19 mm |
| 10-move random sequences | 8 | 6 ran and **all pass**; 2 were **harness crashes** ("STL file … is empty" while loading the model; see below) |

The 10-move sequences that ran:
- end misalignment 2.00–**2.83°** (limit 4°);
- total core slip ≤ 0.37 mm; total rotation ≤ 0.88°;
- F/T ≤ 0.40 N·m; turn error ≤ 1.23°.

## Harness crashes (`FACT`, P-127)
- 2 of 48 trials crashed while MuJoCo read mesh files from `/mnt/c` under 8-process load: the file read returned empty.
- This is the same class as the P-115 magnet-record refusal.
- The runner now retries model-load errors up to 3 times, then interrupts the run, so they are never recorded as a
  failed trial. Revision 3 matched them by message; revision 4 (review 3 item 1) classifies by phase: any exception
  before the first control step.
- The 2 trials were re-run (`rerun/`, `rerun_crashed.py`) at commit `6e4a0de` (the revision-3 code with the
  message-based retry). `rerun_crashed.py` does not write `source_commit` or `head`, so those fields are null in
  the two re-run records (review 3 S6).
