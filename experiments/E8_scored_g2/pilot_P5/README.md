# G2 pilot P-5 (UNSCORED, pilot seeds 29200–29263; 2026-11-26)

> **Magnet-free (P-130, found 2026-11-27):** this pilot ran **without the M7 L0 magnets**, through a bug in the two-arm scene
> (`two_arm.py` installed the magnet callback, then building arm B's IK model uninstalled it). The records below are kept
> as recorded and are not evidence for the system under test. The magnets-on repeat is [`../pilot4_magnets/`](../pilot4_magnets/README.md) (P-131, P-132).

**Scope:** the G2 pre-registration §7 P-5 (user: "Full pilot set"). Run with
`run.py pilot --smoke-dir /home/fwdev/g2pilot --jobs 8`; the records are copied here (`results/`, `run_log.txt`).
- 56 trials, **56/56 pass**, 2208 s wall (8 workers, with other WSL load).
- Code at commit `0ab31b5`.
- The smoke run (`../smoke_1/`, seeds 29100–29104) is kept beside it.

## Data (`FACT`)
| Pilot | n | Result |
|---|---|---|
| P-U: single U turns, F/T stop disabled (5 N·m) | 30 | all pass. **First-turn F/T τ_z: median 0.190, mean 0.201, sd 0.070, p95 0.325, max 0.351 N·m.** Fingertip torque max 0.376. Turn error ≤ 1.16°, drift ≤ 0.25°, cubie penetration ≤ 0.143 mm, core slip ≤ 0.156 mm, core rotation ≤ 0.71° |
| Smoke (for comparison) | 3 turn trials | first-turn F/T max **0.471** N·m (seed 29101; the highest seen) |
| P-rand: 10-move random U sequences, stop disabled | 4 (40 moves) | all pass. F/T max 0.304 (first moves ≤ 0.244); core slip ≤ 0.194 mm |
| P-hold: 60 s holds | 4 | all pass. Core slip 0.045–0.088 mm, rotation 0.18–0.27° |
| P-jam: stop at 0.6 N·m | 3 | all stopped at 0.62–0.65 N·m after 26–30° of roll; cube shift ≤ **0.094 mm** |
| P-jam: stop at 0.8 N·m | 4 | all stopped at 0.81–0.84 N·m after 32–35°; cube shift ≤ **0.138 mm** |
| P-jam: stop at 1.0 N·m | 3 | all stopped at 1.04–1.09 N·m after 41–44°; cube shift ≤ **0.271 mm** |
| two_layer (turner 25 mm deep) | 2 | detected: guard stop + oracle / turn-error failure |
| collision (turner 34 mm deep) | 2 | detected: arm-arm contact during the move + guard stop |
| open_midturn | 2 | detected: incomplete turn (oracle, turn error, final state) |
| offcentre (cube 5 mm sideways) | 2 | completed cleanly (correct turn); reported, as designed |

## Proposed limits (`PROPOSAL`, for the user's approval before the freeze)
| Limit | Provisional | Proposed | Basis |
|---|---|---|---|
| F/T stop (τ_z, 2 samples) | 0.6 N·m | **0.8 N·m** | normal max 0.47 (smoke) / 0.35 (pilot): margin 1.7× / 2.3×. Jam still stopped with cube shift ≤ 0.14 mm |
| Jam: cube shift at stop | 0.5 mm | 0.5 mm | observed ≤ 0.14 mm at 0.8 N·m |
| Per-move core slip vs arm A | 1.0 mm | 1.0 mm | observed ≤ 0.19 mm |
| G2-1 hold (60 s): slip / rotation | 1.0 mm / 1.0° | 1.0 mm / 1.0° | observed ≤ 0.09 mm / 0.27° |
| Start draw: cube offset / misalignment | ±1 mm / ±1° | unchanged | as G1; drives the first-turn torque |
| Negative-test acceptance (`trials.neg_outcome`) | provisional | as coded | every case behaved as specified |
| Trial counts | 138 | 138 | P-109 (4) |

**Note (`INFERENCE`):**
- The first turn's torque tail is set by the ±1° layer misalignment, so one smoke seed reached 0.47 N·m.
- The scored run has 140 first turns. A turn above 0.8 N·m would be a false stop, which counts as a failure under
  zero tolerance.
- The pilot gives no case above 0.47, but the tail is not well estimated from 35 values.
