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

## Post hoc diagnostic: what leaves the layer short (`FACT`; `posthoc/`, exploratory)
Two read-only replays on ER7 seeds, run after the fixed analysis (scripts and outputs in `posthoc/`). Each splits the
torque about a layer's axis into magnets, joint friction and contacts.

- **Snap-back, seed 16568, +8°** (`snap_diag.py`). After the release, and unchanged 5 s later:

  | Quantity | C52 | L0 |
  |---|---|---|
  | U-layer error | +0.996° | −0.014° |
  | Magnet torque about the U axis | 0 (below 1e-14 N·m) | 4.6e-4 N·m, balanced by contacts |
  | Contacts between pieces | **none** | 56, total normal force 6.0 N |
  | Largest joint velocity | 3e-13 | 3e-4 |
  | U-layer edges and corners: rotation about their own radial axis | **+1.40 to +1.74°** | −0.27 to +0.27° |
  | The other 12 edges and corners: rotation about their own radial axis | **+1.00 to +1.39°** | −0.20 to +0.20° |
  | The six centres: rotation about their axis | +0.62 to +1.02° | −0.11 to +0.10° |
  | Edges and corners: rotation in the other two directions, largest | 0.09° | 0.70° |

  In C52 every piece is at its home position and is left **rotated about its own radial axis**, the axis of its
  magnet pair. **All 26 pieces are rotated in the same sense**, including the 17 that the rig never turned. Seen
  along the U axis, the U-layer pieces' leftover is 0.87–1.08° each, which is the 1.0° layer error. Nothing pushes or
  holds the pieces: there is no contact, no magnet torque and no motion. In L0 the pieces' rotations have both signs
  and stay within 0.3°.
- **Rest, seed 16000** (`rest_diag.py`). In C52, after the 0.5 s settle that precedes every trial, the cube has no
  contacts at all and the magnet torque on every layer is zero (below 1e-13 N·m). L0 has 61 contacts carrying 7.2 N,
  with the magnets' torque on each layer balanced by contact forces.

## Interpretation (`INFERENCE`, post hoc; item 1 rests on the diagnostic above and on ER3 and ER6)
1. **The layer stops short because the core layout has no stiffness against a piece spinning about its own radial
   axis.** A coaxial magnet pair is symmetric about its axis. ER3 and ER6 recorded this as "edge spin 0, corner twist
   0", and both screens passed only inside the tolerance on those two modes (margin +0.010). A layer turned by an
   angle and released carries a spin of 71 % of that angle on its edges and 58 % on its corners. The magnets pull the
   pieces back to their positions but leave the spin.
   - **The leftover is a collective motion of the whole cube.** One piece alone could not stay spun by 1.5°: that
     moves the edges of its faces by about 0.14 mm, more than the 0.05 mm gap. But with every piece spun the same
     way, neighbouring faces tilt together and nothing touches. The magnets resist this motion not at all, and
     contacts do not resist it either, so the cube has a free internal motion that nothing brings back to square.
   - The static screens looked at one piece, or one rigid layer, at a time. They could not see a collective motion.
2. **M5's corner–edge magnets do restore that mode** (ER3: spin +122 and twist +118 mN·m/rad for L0), which is why
   L0 snaps back to within 0.1°.
3. **C52's rest result is not friction.** The setup offsets each layer by up to 1°, as a rigid rotation written
   before t = 0. In C52 the magnets bring every piece back within the settle time and the cube then sits with no
   contacts, so nothing can slip. L0 rests on contact forces between pieces that its magnets pull together, and its
   slips happen there (D11, ER1).
   - **The pieces are not square while they rest** (`FACT`, one-off check on seed 16000). After the settle, C52's
     layers are 0.13–0.19° off and its worst piece 0.39° off; L0's layers are within 0.09° and its worst piece
     0.71° off. The rest criterion measures motion during the rest, not the error from square, so C52 passes it
     while sitting slightly spun.
4. **Weaker or stronger magnets would not change this.** A mode with zero stiffness stays at zero under any strength
   scale. ER8's derated arm would have failed the same way.
5. **The higher turning torque is probably the same defect seen during a turn:** pieces left spun inside the gap play
   meet the turning layer. This was not measured.
6. **What ER7 does and does not show.** A layout of single coaxial pairs fails M4's snap-back criterion in rehearsal.
   It does not show that core magnets fail: a layout that also restores spin and twist was not tested.

**Correction (2026-11-19).** The first version of this section, committed in `21b3470`, attributed the short
snap-back, the rest result and the turning torque to friction from a radial magnetic preload of about 40 N. That was
wrong. B1's pieces have no radial freedom (`radial_preload = 0` removes the slide joint), so a radial pull loads the
joint and cannot press pieces together, and the diagnostic found no contacts at all in the stopped state. The
"options" that followed from it (a screen of radial pull against stiffness; a preload from another source) are
withdrawn.

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
4. **Post hoc diagnostic, 2026-11-19.** `posthoc/snap_diag.py` and `posthoc/rest_diag.py` replay one snap-back trial
   (seed 16568, +8°) and one rest trial (seed 16000) per arm and read the constraint forces and every piece's rotation (`posthoc/summarize.py` prints the table). They are exploratory, use
   ER7's seeds (already diagnostic) and change no record or signal. One seed per case: the per-piece numbers are an
   example, not a distribution.

## Consequences (fixed by the protocols)
- **No scored pre-registration is proposed for C52.** The draft `experiments/PHASE_1_M6_PREREGISTRATION.md` lapses
  unused, as its status section says.
- **ER8 lapses.** Its runner refuses to start unless these signals are all met.
- Seeds 16000–16655 now count as used for diagnostics.

## Options for the next step (`PROPOSAL`; the choice is the user's)
- **(a) Recommended: a static screen of core layouts that also restore spin and twist.** Break the symmetry about the
  piece's radial axis, for example with two magnet pairs per piece, or one pair set off the axis. Screen them with
  ER6's code against ER3's criteria, with the tolerance on spin and twist replaced by a required positive stiffness.
  It is static and cheap, and the fit of any candidate inside a real piece would have to be checked as ER4 did.
  ER3's one mixed variant that passed (core magnets on edges plus edge–centre magnets) restores edge spin (+58) but
  has no corner magnets, so it is not an answer as it stands.
- **(b) Add a spin and twist requirement to the screen's criteria** for any future layout, whatever option is taken.
  ER7 shows the zero-stiffness tolerance let through a layout that fails dynamically.
- **(c) Revisit the snap-back criterion.** The 0.5° line is M4's own registered criterion. Changing it after this
  result would be post hoc; it would need the user's explicit decision and a disclosure, and it would leave pieces
  free to sit spun by 1–2°.
- **(d) Return to M5's layout and target its slip mode directly,** keeping the corner–edge magnets that give spin and
  twist stiffness. ER2 and ER3 found no static fix there (a slide/cross sign trade-off).

## Limits
As in `PROTOCOL.md`:
- Rehearsal only.
- The magnets have no collision geometry (P-58 abstraction).
- implicitfast has a bounded energy oscillation.
- The ideal-magnet caveat applies.
- 20 rest seeds give wide intervals.
