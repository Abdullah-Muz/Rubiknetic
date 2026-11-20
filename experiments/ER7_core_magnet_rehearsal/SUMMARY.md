# ER7 — Dynamic rehearsal of the core-magnet layout against M5 (SUMMARY)

**Status:** unscored, exploratory rehearsal under [`PROTOCOL.md`](PROTOCOL.md) (P-61). Protocol, runner and analysis:
`43094ca`, with deviation 1 in `0cc9ff6`; pre-run self-check `22b6306`. Every record carries commit `0cc9ff6`.
One run, 2026-11-19, WSL2, MuJoCo 4.0.1, 8 workers: 408 records (204 per arm) in 9,593 s. Raw records:
`results/<arm>/<experiment>/<trial>.json.gz`, `results/analysis.json` and `run_log.txt`.
Nothing here selects a mechanism or changes M5, which stays NOT PASSED.

## Fixed verdict
**C52 DOES NOT MEET THE FEASIBILITY SIGNALS.** It meets signals 1 and 3 and fails signal 2: 10 of 20 snap-back
trials (E1-5s) fail. Under the protocol, no scored pre-registration is proposed for C52, and the next step goes back
to the user.

## Feasibility signals (C52 arm; pre-declared, not G1 thresholds)
| Signal | Criterion | Result | Met |
|---|---|---|---|
| 1 | 0 / 20 slip seeds over 0–60 s (D11 events) and every rest rotation ≤ 0.5° | 0 / 20 slip seeds (95 % CI 0–0.17); largest rest rotation 3.4e-6° | **yes** |
| 2 | M5's Option A rule (every per-trial pass flag of the 204 trials, plus E1-6m ⟨P⟩) | 194 / 204 trials pass; E1-5s 10 / 20; E1-6m 1,376 / 1,376 moves | **no** |
| 3 | No flagged trial (near pair perpendicular, or near tilt > 20°) | 0 flagged; largest near tilt 18.42°; 0 perpendicular pairs | **yes** |

## Results by sub-experiment (`VALIDATED_RESULT` for this rehearsal as defined; passed / n)
| Experiment | L0 (frozen M5) | C52 (core layout) |
|---|---|---|
| E1-1 rest | **18 / 20** | 20 / 20 |
| E1-2 quarter turns | 24 / 24 | 24 / 24 |
| E1-3 half turns | 22 / 22 | 22 / 22 |
| E1-4 sequences | **39 / 40** | 40 / 40 |
| E1-5 forgiveness | 42 / 42 | 42 / 42 |
| E1-5s snap-back | 20 / 20 | **10 / 20** |
| E1-6a / b / c abuse | 6 / 6, 6 / 6, 8 / 8 | 6 / 6, 6 / 6, 8 / 8 |
| E1-6t corner twist | 16 / 16 | 16 / 16 |
| E1-6m ⟨P⟩ (moves) | 1,376 / 1,376 | 1,376 / 1,376 |
| **Option A rule** | **not met** (201 / 204) | **not met** (194 / 204) |

**L0's failures** (`FACT`):
- **Rest:** seeds 16003 (0.568°) and 16005 (0.559°), each with fast slip events (at 5.3 s and 7.3 s). That is 2 / 20
  slip seeds (95 % CI 0.01–0.32), the same count as D11 found on M5's scored seeds.
- **E1-4:** `scr20inv_s16405`, one move (move 9, F′) flagged non-causal; its drift was 0.32°.
- L0 is frozen M5 on new seeds, so this is a second, unscored sample of M5: it again fails on rest rotation.

**C52's failures** (`FACT`): all ten are E1-5s trials with a release offset of 3° or more.

| Release offset | Scored | L0 error after 1 s | C52 error after 1 s | C52 pass |
|---|---|---|---|---|
| ±1° | no | 0.03–0.27° | 0.05–0.33° | n/a |
| ±2° | no | 0.01–0.14° | 0.37–0.43° | n/a |
| ±3° | yes | 0.01–0.12° | 0.42–0.54° | 2 of 4 |
| ±5° | yes | 0.01–0.10° | 0.67–0.73° | 0 of 4 |
| ±8° | yes | 0.01–0.04° | 0.87–1.01° | 0 of 4 |

The criterion is |error| ≤ 0.5° after 1 s. In C52 the layer returns most of the way and then stops: in the one
record inspected (`snap_+8_s16568`), the error right after release and the error 1 s later are equal to 11 digits
(0.9963°).

## Paired comparison (C52 − L0, same seeds; `FACT`)
| Quantity | L0 | C52 | Paired |
|---|---|---|---|
| Rest rotation, 20 seeds | median 0.105°, max 0.568° | median 1.7e-10°, max 3.4e-6° | C52 lower in 20 / 20 |
| Max non-target drift per sequence, 86 trials | max 0.776° | max 0.831° | median difference −0.080°; C52 lower in 53 / 86 |
| Peak turner torque per move, 1,376 moves | median 0.203, p99 0.563, max 0.870 N·m | median 0.645, p99 1.000, max 1.000 N·m | per-sequence peak: median difference +0.462 N·m; C52 lower in 4 / 86 |
| Moves at the 1 N·m torque clip | 0 | **69**, in 37 of 86 sequence trials | |
| Largest turn error | 0.304° | 0.645° | |
| E1-4 growth slope, largest | 0.0024°/move | 0.0027°/move (limit 0.005) | |

Every one of C52's 1,376 moves matched the oracle, including the 69 at the clip.

**Force-law regime (P-60):** C52 had 1,403,737 clamped-z pair evaluations, which the P-60 amendment allows for
piece-to-core pairs, and none outside the validated regime. L0 had none clamped and a largest near tilt of 12.59°.

## Self-checks
| Check | Result |
|---|---|
| S1, L0 reproduces one M5 scored trial per sub-experiment | Pass after deviation 1: 0 differences in all 10 trials (`results/selfcheck.json`; first run kept as `selfcheck_run1.json`) |
| S2, C52 system reproduces M6's layer stiffness | Pass (difference 0) |
| S3, body ids match the magnet layout | No assertion failure in any trial |
| S4, E1-1 instrumented rest matches the scored rest | True for all 20 trials in both arms |

## Interpretation (`INFERENCE`; post hoc, from these records and ER6's statics)
1. **The core layout removes the rest slips by clamping the cube, not only by restoring it.** C52's rest rotation is
   at least five orders of magnitude smaller than L0's, which is what static friction holding every piece would give. Each
   piece-to-core pair pulls its piece toward the core with about 2 N (largest pair force 2.18 N), so the 20 pairs act
   as a radial preload of the order of 40 N in total. That preload was not part of the static screen (ER3, ER6), which
   looked at stiffness only.
2. **The same friction stops the snap-back short.** The layer stops where the magnets' restoring torque falls below
   the friction torque. With ER6's layer stiffness of 2.58 N·m/rad, a stop at 0.5–1.0° corresponds to a friction
   torque of about 0.02–0.05 N·m on the layer.
3. **It also raises the turning torque about threefold** (median 0.645 against 0.203 N·m) and puts 5 % of moves at
   the turner's 1 N·m limit. ER6's static detent peak for this variant was 0.18 N·m, so most of the increase is
   friction, not the detent.
4. **Weaker magnets alone may not fix the snap-back.** Friction torque and restoring stiffness both scale with
   magnet strength, so their ratio, which sets where the layer stops, would stay about the same. This is a scaling
   argument, not a measurement; the joint friction and the contact model could change it. ER8's derated arm would
   have tested it, but ER8 was conditional on C52 meeting these signals, so it lapses.
5. **What ER7 does and does not show.** It shows that C52 as specified fails M4's snap-back criterion in rehearsal,
   and that radial magnetic preload suppresses M5's rest slips. It does not show that every core-magnet layout
   fails: the ratio of radial pull to tangential stiffness depends on the magnet geometry, which was not varied.

## Deviations after the first run
2. **Restart after a memory-pressure kill, 2026-11-19.** `FACT`:
   - **What happened.** The first attempt of the main run started on 2026-11-18 with `--jobs 12`. The user paused
     it with SIGSTOP about 3.5 min in. While it was paused, Claude Code stopped the background task because the
     system was critically low on memory, and the paused processes were lost.
   - **Data affected.** None: the first attempt had written 0 of 408 records.
   - **Restart.** At 2026-11-19T16:16:31-08:00 the run restarted with `--jobs 8`, from the same commit (`0cc9ff6`;
     `results/environment.json`, rewritten at the restart). `run_log.txt` keeps the first attempt's start line and a
     restart marker.
   - **Other load.** For about the first 2 h 20 min of the restarted run, another project's job (about 35 Python
     worker processes) shared the same WSL2 machine, leaving about 1 GB of memory free.

   **Why this does not change the results** (`INFERENCE`, from the runner's design):
   - Each trial has a fixed seed and runs in a fresh worker process (`maxtasksperchild=1`).
   - Records are written once per trial, and the physics does not depend on wall-clock time.
   - So the worker count and the other load can change only the wall-time fields (`wall_s`, `er7_wall_s`,
     `loadavg_start`).
3. **Post hoc additions to the report, 2026-11-19.** The snap-back table by release offset, the turner-torque
   quantiles, the largest turn error and the growth slope were read from the records after the fixed analysis
   (`er7_analyze.py`) had run. They are descriptive and change no signal.

## Consequences (fixed by the protocols)
- **No scored pre-registration is proposed for C52.** The draft `experiments/PHASE_1_M6_PREREGISTRATION.md` lapses
  unused, as its status section says.
- **ER8 lapses.** Its runner refuses to start unless these signals are all met.
- Seeds 16000–16655 now count as used for diagnostics.

## Options for the next step (`PROPOSAL`; the choice is the user's)
- **(a) A static screen of preload against stiffness.** Extend ER6's screen with one more quantity: the radial pull
  per piece, and from it the expected stop angle (friction torque ÷ layer stiffness). Screen core-layout geometries
  (clearance, magnet size, offset or angled pairs) for ones that keep the tangential stiffness but pull less. This
  is cheap, static, and tests interpretation 4 before any new dynamic run.
- **(b) A small dynamic probe of the scaling argument.** Run E1-5s and E1-1 only (40 trials) for the derated layout
  (ER8's C52d arm, already built), as a new protocol with its own approval. If the stop angle is unchanged at lower
  strength, interpretation 4 holds and option (a) is the only route within this layout family.
- **(c) Revisit the snap-back criterion.** The 0.5° line is M4's own registered criterion and was disclosed as chosen
  from stage-1 data. Changing it after this result would be a post hoc change; it would need the user's explicit
  decision and a disclosure, and it would not address the turner-torque clip.
- **(d) Return to M5 and target the slip differently,** for example a small radial preload from another source, now
  that ER7 shows preload suppresses the slips. M1 had a 1 N preload spring per piece, which B1 removed (M4, P-23).

## Limits
As in `PROTOCOL.md`:
- Rehearsal only.
- The magnets have no collision geometry (P-58 abstraction).
- implicitfast has a bounded energy oscillation.
- The ideal-magnet caveat applies.
- 20 rest seeds give wide intervals.
