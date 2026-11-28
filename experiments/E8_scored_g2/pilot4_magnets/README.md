# G2 pilot 4: magnets-on re-pilot (UNSCORED; seeds 29500–29671; 2026-11-27/28)

**Why:** review 4 (P-130) found that the M7 L0 magnets were **off** in every earlier D18/G2 trial. `TwoArm.__init__`
installed the magnet callback, then `b_robot_spec()` → `hold.robot_spec` uninstalled it, and nothing installed it
again. Every earlier pilot (P5, `pilot2_rev2/`, `pilot3_rev3/`), the P-115 tuning and both self-checks were therefore
magnet-free. P-131 (user: "Full re-pilot"; limits "keep unless data says no") restored the magnets and added a judged
check that the magnet force is evaluated at every simulation step. This pilot repeats every earlier pilot with the
magnets on, on new seeds.

**Run:** `run.py pilot4 --smoke-dir /home/fwdev/g2pilot4 --jobs 8` at commit `eb90291`. It was paused by the user
after 70 trials and resumed (start 2; no orphans, nothing reconciled). The records are copied here (`results/`,
`run_log.txt` without MuJoCo's spec-attach warnings). `analyze.py --mode pilot4` gives **PASS, 144/144**, with
integrity clean (`verdict_pilot4.md`).

## Magnets (`FACT`)
- Every one of the 144 records has `steps_without_magnet_force` = 0. A turn trial has at least 20,817 steps.

## First turns, F/T stop disabled (5 N·m)
| Group | n | F/T τ_z median / p95 / max (N·m) | Turn error max | Core rotation max |
|---|---|---|---|---|
| U | 30 | 0.149 / 0.225 / 0.243 | 0.13° | 0.68° |
| U′ | 20 | 0.238 / 0.305 / **0.373** | 0.16° | 0.86° |
| U2 | 20 | 0.215 / 0.271 / 0.279 | 0.17° | 1.06° |
| Forced extreme (U face ±0.80 … ±1.00°; U′, U2, U) | 34 | 0.222 / 0.286 / 0.334 | 0.19° | 0.90° |

- The worst first turn over all 120 first moves is 0.373 N·m, a **2.7× margin** to the 1.0 N·m stop. Magnet-free, it
  was 0.674 N·m.
- The worst first-move turn error is 0.196°; magnet-free, it was 1.75°. The detents re-centre the layer.

## At the configuration to be frozen (F/T stop 1.0 N·m)
| Case | n | Result |
|---|---|---|
| `jam` | 6 | all stopped after **37.3–44.3°** of roll (window 20–50°) at 1.02–1.05 N·m; core slip ≤ 0.22 mm (limit 0.5) |
| `two_layer` | 6 | all detected: F/T stop at 1.10–1.15 N·m after 3.4–3.7° of roll; core slip ≤ 0.36 mm |
| `collision` | 2 | detected (robot contact) |
| `open_midturn` | 2 | detected |
| `offcentre` (5 mm) | 2 | clean (both turned U correctly) |
| 60 s holds | 6 | all pass: core slip ≤ 0.13 mm, rotation ≤ 0.31° |
| U U′ U2 U′ U | 4 | all pass |
| 10-move random sequences | 12 | all pass; end misalignment 0.61–**1.05°** (limit 4°); F/T ≤ 0.48 N·m |

## All 244 turn moves (120 turn trials)
| Quantity | Max | Limit | Magnet-free pilots |
|---|---|---|---|
| Turn error | 0.31° | 2° | 1.75° |
| Drift | 0.30° | 1° | 0.57° |
| Cubie penetration | 0.145 mm | 0.5 mm | 0.15 |
| Core slip per move | 0.26 mm | 1 mm | 0.20 |
| **Core rotation per move** | **1.21°** | 2° | 0.93° |
| Roll-back rotation | 0.083° | 1° | 0.05 |
| F/T peak, any move | 0.48 N·m | 1.0 (stop) | – |
| Total core slip / rotation | 0.63 mm / 1.12° | 2 mm / 2° | 0.38 / 1.24 |
| End misalignment | 1.05° | 4° | 2.83° |
| **t0 offset** (142 records, offcentre excluded) | **2.25 mm** (mean 1.01, sd 0.49) | 3 mm | 2.08 |
| Stand-drop shift | 0.12 mm | 1 mm | 0.12 |
| Causality gap (force before motion) | min 3 steps (1.5 ms), median 27 | > 0 | min 2 |
| Drive impulse | min 0.0106 N·m·s | > 0 | 0.012 |

- **Margins with magnets on:** the t0 offset is now the tightest (1.33×), then per-move core rotation (1.65×) and total
  core rotation (1.8×). The core moves a little more with magnets on (the detents add resistance). Turn error,
  end misalignment and the F/T margin are much better.
- The limits are unchanged (P-131: "keep unless data says no"); every one fits this data.

## Load retries (`FACT`)
- 3 trials (`rand10_s29660`, `s29663`, `s29665`) hit `OSError: [Errno 12] Cannot allocate memory` before their first
  control step. The runner retried them (the phase rule, P-129); all 3 then ran and passed.
- Another project's processes were running in WSL at the time. The scored procedure forbids other WSL jobs (§6).

## Timing
- Median real-time factor 0.043 per trial process (8 workers, with the other load). The magnet callback runs in Python
  at every step.

## Re-analysing with later code (revision 6, P-136)
- Revision 6 (review 5) added `sim_steps` and the magnet-validity fields (`max_near_tilt_deg`, `near_perpendicular`,
  `clamped_z`) to the record and judges them. These pilot-4 records predate them, so `analyze.py --mode pilot4` at
  revision 6 or later reports INVALID ("stored pass ≠ recomputed"). This is expected; the records are kept as recorded
  (as for `pilot2_rev2/`).
- The verdict stored here (`verdict_pilot4.md`, PASS) was produced at revision 5 (`114489e`'s code).
- Review 5 confirmed for all 144 records that `steps` = `sim_time_s` / dt, and measured a near-pair tilt of at most 1.82°
  in six magnets-on probes at revision 5.
