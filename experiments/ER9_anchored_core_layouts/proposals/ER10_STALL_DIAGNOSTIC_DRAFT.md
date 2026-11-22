> **DRAFT — not approved; not a committed protocol.** Drafted by a subagent on 2026-11-21 without running anything.
> Before any run it needs the user's approval, a DECISION_LOG row, and a commit as a protocol. It is diagnosis only:
> it does not propose changing the frozen B1 model, M5 or the rig.
>
> Main-session checks:
> - CUBE_MECHANISM_FINDINGS §3 gives 0.033–0.038 mm neighbour clearance for the same CAD at rest.
> - D8's README reports the no-magnet B1 cube reaching the 1.00 N·m limit.
>
> The other tallies it quotes from E5 records are its own and are marked for re-checking.

> **DRAFT — not approved; not a committed protocol.** Drafted by a subagent on 2026-11-21. No simulation or other
> process was run. Small JSON records were read. Nothing here is fixed until the user approves a version. It would
> then be committed as `experiments/ER10_turning_stall/PROTOCOL.md` before any ER10 computation, with a
> DECISION_LOG row.

# DRAFT for review — ER10: turning-stall diagnostic (exploratory, unscored)

**Status: DRAFT, 2026-11-21. Not fixed, not committed, not approved, nothing run.**
- **Exploratory and unscored.** It uses only ER7's rehearsal seeds (16000–16999) and touches no scored seed
  (17000–17999).
- **Diagnosis, not a model change.** It changes no record and no frozen parameter, and it selects no mechanism. The
  B1 geometry (piece gap 0.05 mm, chamfer 1.4 mm), the cubie contact parameters, the timestep and the M1/M5 turner
  rig all stay frozen.
- **What a change would need.** A different gap, chamfer or contact setting would be a mechanical or modelling
  decision for the user. It would need its own proposal, approval, pre-registration and full re-validation.
- **Status of the mechanisms.** M5 stays NOT PASSED and no mechanism has passed G1.

Labels: `FACT` (with file and section), `INFERENCE`, `PROPOSAL`, `TODO` (a number this draft could not get without
running something). Nothing here is a result.

**Sources read:**
- `CLAUDE.md`
- `docs/DECISION_LOG.md`, rows P-23, P-24, P-25, P-26, P-27, P-30, P-31, P-32, P-58, P-60, P-63
- `docs/research/CUBE_MECHANISM_FINDINGS.md` §1–4 and `docs/research/MUJOCO_CONTACT_CREEP_FINDINGS.md` §0–2
- `src/rubiknetic/cube_physics/m1_model.py` (`M1Params`, `build_m1_xml`) and `magnets.py` (`MagnetParams.wall`,
  `layout`)
- ER9: `SUMMARY.md`, `PROTOCOL.md` (structure, Parts A–B), `er9_turn_diag.py`, `er9_catch_diag.py`,
  `results/probe/diag/turn_*.json` (all 13, summary fields; samples for W3, L0 and X0.003),
  `catch_W3_s16100.json`, `catch_L0_s16100.json`, `side_checks/README.md`, `side_checks/realfit/stage4_m5_positions.log`
  (first lines), `proposals/PART_F_DRAFT.md` (format only)
- `experiments/ER7_core_magnet_rehearsal/er7_run.py` (how the gap reaches the model)
- `experiments/E5_scored_m5/RESULTS.md` and `SUMMARY.md` (E1-7), `results/E1-7/*.json` (per-move turner torque and
  drift, read during drafting)
- `experiments/D8_alignment/results/diag_m4_2026-11-15/SUMMARY.md` §5 (gap study)

---

## Decisions for the user (the draft uses the default in every case)

| # | Choice | Default | Alternatives and trade-off |
|---|---|---|---|
| D1 | Run ER10 at all, and when | Approve as a diagnostic. Run only after ER9 Part E's probe has finished or been stopped, on an idle machine, one process at a time | Defer until Part E and Part F are settled. The stall stays unexplained, and Part F's anchored-only family keeps an unexplained cost |
| D2 | Piece-gap levels | {0.05, 0.10, 0.25} mm | Add 0.20 mm. It links to P-24/P-26 and D8 §5, which have drift and torque data at 0.2 mm. Adds 9 replays |
| D3 | Chamfer levels | {1.0, 1.4, 2.0} mm, which is E5's E1-7 band, so earlier data exist at the same values | {1.0, 1.4, 2.5} mm, to push further if 2.0 mm already shows a trend |
| D4 | Layouts | (a) **no magnets** (M5's `magnet=none` configuration, E1-6n's arm); (b) **W3**; (c) **L0**. Also X0.003 at the nominal point only, as the link to ER9's replay | Use X0.003 instead of a true no-magnet arm. It is closer to ER9's harness, but it is not magnet-free and it is slower (96 magnets) |
| D5 | L0's corner–edge face gap when the piece gap changes | Keep the 0.4 mm wall, so face gap = piece gap + 0.8 mm (what `magnets.layout` does already; 1.05 mm at 0.25 mm) | Hold the face gap at 0.85 mm by thinning the wall. This isolates the geometry effect from magnet strength, but it is a different magnet design |
| D6 | "Catch present" thresholds | As in §5 (clip, stall, sub-limit catch; window 3–15° of turner angle) | Clip only. Simpler, but it misses L0's sub-limit catch (§2, item 4) |
| D7 | Worst-point checks | Timestep 0.25 ms; 0.25 ms with cubie solref 0.5 ms; flat cubie solimp (0.99, 0.99, 0.5 mm); cubie friction 0.1 and 0.5; setup misalignment 0; grip 10 and 50 N | Add geom margin/gap (0.1/0.1 mm) and `multiccd`. These test contact detection rather than mechanics; low prior value |
| D8 | Guard rails for any setting with no catch | E1-7's `6move` and `sexy6` sequences, 2 × E1-1 rest (10 s), 2 × E1-5s snap-back (±8°), each paired with the frozen nominal on the same seeds | A full 106-trial probe for the best setting. Much stronger, about 10× the cost; better left to a follow-up the user approves separately |
| D9 | Seeds | Grid on 16100 (first U of E1-2, as ER9). Seeds 16101 (U) and 16102 (U′) are added at the nominal point and at every catch-free setting | Three seeds over the whole grid. About 3× the cost; useful if single-seed results look erratic (§2, item 5) |
| D10 | Faces | U only | Add one R and one F move at catch-free settings. Gravity breaks the symmetry between faces, and W3's 771 clipped moves were not all U |
| D11 | Whether 0.25 mm is "the real gap" | **No.** It is one CAD model's flat-face separation, and the same CAD's smallest neighbour clearance is 0.033–0.038 mm (§2, item 6). 0.25 mm is a grid level, not a target | Treat 0.25 mm as the reference. Not supported by the sources. A real-cube measurement (R1, caliper) is the user's item |
| D12 | Radial retention (M1's 1 N preload slide, removed in B1) | Out of scope for ER10 | Add one replay at the nominal gap with M1's preload. P-26 found M1 with preload drifted 0.013° at 0.2 mm, against 0.83° for B1. It is a different mechanism model, so it is the user's mechanical decision |

---

## 1. Question and scope
**Question.** Does the catch about 7° into a quarter turn depend on any of these?
- piece gap;
- chamfer size;
- cubie contact parameters (solref, solimp, friction);
- timestep;
- the grip force and setup misalignment of the frozen rig.

Is there a model setting at which the catch disappears without breaking what G1 needs: drift ≤ 1° per move, rest
≤ 0.5°, snap-back ≤ 0.5°?

**The inference under test (INFERENCE, from the brief and §2).** The catch may be an artefact of the model's very
small clearance or its chamfer geometry, rather than mechanics a real cube would show.

**Out of scope:**
- changing the frozen B1 model, M5, ER9 records or any criterion;
- scoring anything;
- claiming anything about a real cube;
- new magnet layouts.

## 2. What is known going in

1. **The stall** (FACT, ER9 `SUMMARY.md` "Diagnostics"; `turn_W3_s16100.json`, `catch_W3_s16100.json`):
   - Seed 16100, first U of E1-2, W3. The layer stops at about 6.7–6.9° while the turner winds up to 1 N·m.
     It breaks through at t ≈ 1.17 s (layer error −6.83° → −11.42° in one 10 ms sample). Peak 1.0 N·m; 4.3 % of the
     turn's steps at the clip.
   - At the step with the largest summed cubie–cubie normal force (148 N, turner −7.96°), the top contacts are
     U-corner against side-centre, at about 10 N each:
     - `cubie_0n0`–`cubie_pnp`, normal (0.706, −0.081, 0.704);
     - `cubie_npp`–`cubie_0p0`, normal (0.696, 0, −0.718).
   - Both contacts sit at z ≈ 9.55 mm, the layer boundary, and |y| ≈ 27.07 mm, about one chamfer in from the outer
     face.
   - U pieces lag the turner by 0.60–1.55° and are tilted 0.14–0.39°.
2. **Penetration at the catch is larger than the gap** (FACT, `catch_W3_s16100.json`, field `dist`):
   - 0.077–0.078 mm at the corner–centre contacts;
   - 0.114–0.117 mm at in-layer contacts with near-y normals (for example `cubie_pnp`–`cubie_p0p`);
   - the piece gap is 0.05 mm.

   INFERENCE: the contact model's softness is on the same scale as the clearance, so contact parameters are a
   plausible factor in their own right.
3. **During the stall, pad contacts drop and the turner keeps going** (FACT, `turn_W3_s16100.json` samples
   t = 1.06–1.16 s):
   - pad contacts fall from 10 to 4;
   - the turner advances 0.5° (−7.47° → −7.96°) while the layer error stays at −6.80 to −6.93°.

   INFERENCE: the pads slip on the layer or comply while the layer is held, so pad slip should be recorded.
4. **L0 shows a smaller catch at the same place** (FACT, `turn_L0_s16100.json` samples t = 0.99–1.02 s):
   - The turner torque rises from 0.10 to 0.446 N·m between turner −5.6° and −6.3°, then drops to 0.09 N·m by −7.3°.
   - The catching pairs are again corner against side centre (`cubie_nnp`–`cubie_n00`, `cubie_p00`–`cubie_ppp`,
     normals about 45°), penetration 0.029–0.036 mm (`catch_L0_s16100.json`).

   INFERENCE: M5's in-layer magnets **attenuate** the catch rather than remove it. ER9's summary says they
   "suppress it". Its numbers (peak 0.46 N·m) agree, but the word overstates.
5. **Single replays are erratic** (FACT, `turn_*.json` summary fields):
   - The ad hoc strength sweep is not monotone: X0.1 peak 1.0 N·m, X0.03 0.782, X0.003 1.0 (9.8 % of steps at the
     clip; final layer error 0.318°).
   - C52's replay on this seed peaks at 0.419 N·m with no clip, yet C52 had 69 clipped moves in its 204-trial
     rehearsal (SUMMARY Part D).

   INFERENCE: one seed and one face cannot characterise the catch, hence D9.
6. **Clearance in the real-mechanism CAD:**
   - FACT (`side_checks/README.md`, realfit; `stage4_m5_positions.log`): along the M5 magnet lines, the GrabCAD
     model's corner material starts at 9.75 mm where the edge ends at 9.5 mm. The README reports this as "the CAD's
     piece gap is 0.25 mm".
   - FACT (`CUBE_MECHANISM_FINDINGS.md` §3, same CAD, FCL queries): "Neighbour clearance is 0.033–0.038 mm" at rest,
     and layer sweeps keep at least 0.033 mm. Corner twist is blocked by 2°, and radial capture is within 0.1 mm.
   - The CAD's licence is unconfirmed (§3), and it is one design, not a measured cube.

   INFERENCE (not verified): the two numbers measure different things. 0.25 mm is a flat face-to-face separation.
   0.033–0.038 mm is the smallest clearance anywhere, probably at the feet and tracks. B1 has no feet, so its single
   piece gap sets both the face clearance and the pieces' freedom to tilt. No single B1 gap reproduces both.
7. **Earlier gap data** (FACT):
   - P-24/P-25: drift above M1's 1° limit in 9 of 18 moves at 0.2 mm (M4 probe). At 0.1 mm the full rehearsal failed
     10 trials on drift (12 of 1,376 moves, max 1.14°).
   - P-26: at 0.2 mm the drift belongs to the B1 base (rigid radius, angular play), with or without magnets. M1 with
     its 1 N radial preload drifted 0.013°.
   - D8 §5: without magnets, the turner reached the 1 N·m limit at 0.2 mm (median 0.34, max 1.00 N·m) and at
     0.05 mm (median 0.41, max 1.00; one jam with 0.76 mm penetration). With magnets the medians were 0.095–0.12 N·m.
   - P-30: M5's median turner torque at 0.05 mm was about 2× that at 0.1 mm.

   INFERENCE: the 1 N·m limit is reached without magnets at a 0.2 mm gap as well. That is existing evidence against
   "the stall is only a small-gap artefact", although D8 did not identify the contacts responsible.
8. **E5's E1-7 sensitivity records** (FACT for pass/fail, `E5_scored_m5/RESULTS.md` "E1-7"; turner torque and drift
   were tallied from `results/E1-7/*.json` during drafting and should be rechecked; the arm is L0 at 0.05 mm unless
   named):

   | Setting | `6move` pass / max torque / max drift | `sexy6` pass / max torque / clipped moves / max drift |
   |---|---|---|
   | nominal | pass / 0.465 / 0.474° | pass / 0.640 / 0 / 0.517° |
   | gap 0.025 mm | pass / 0.373 / 0.331° | pass / 0.491 / 0 / 0.381° |
   | gap 0.1 mm | pass / 0.456 / 0.805° | pass / 0.464 / 0 / 0.894° |
   | chamfer 1.0 mm | FAIL (tilt 11.97°) / 0.813 / 0.280° | pass / 0.568 / 0 / 0.510° |
   | chamfer 2.0 mm | pass / 0.447 / 0.467° | pass / 0.502 / 0 / 0.593° |
   | misalignment 0 | pass / 0.110 / 0.476° | pass / 0.477 / 0 / 0.381° |
   | timestep 0.25 ms | pass / 0.632 / 0.512° | pass / 0.597 / 0 / 0.566° |
   | timestep 0.75 ms | FAIL / 0.129 / 0.536° | FAIL / 0.389 / 0 / 0.571° |
   | magnets none | FAIL (2 moves) / 1.0 / 0.578° | pass / 1.0 / 5 / 0.843° |

   INFERENCE:
   - Drift rises with the gap even with M5's magnets: 0.894° at 0.1 mm against 0.517°. This is the P-24 trade-off
     ER10 must watch.
   - Zero setup misalignment cut the `6move` peak from 0.465 to 0.110 N·m, which makes misalignment a candidate
     cause (H5).
   - All of these are single sequences.
9. **Contact and timestep context** (FACT, `m1_model.py` `M1Params`; `MUJOCO_CONTACT_CREEP_FINDINGS.md` §1–2):
   - Cubie contacts: condim 3, μ = 0.2, solref (1 ms, 1), solimp (0.95, 0.99, 0.5 mm); timestep 0.5 ms; elliptic
     cone, impratio 10, Newton.
   - MuJoCo's refsafe floor is τ ≥ 2·dt, so at 0.5 ms the cubie solref already sits at the floor and cannot be made
     stiffer without a smaller timestep.
   - INFERENCE: at 0.75 ms the floor (1.5 ms) silently softens every cubie contact, which may be why E1-7's 0.75 ms
     arm failed.
   - MuJoCo is pinned at 4.0.1 (`pyproject.toml`).
10. **Turning torque of a real cube** (FACT, P-63): 0.09 N·m appears on an archived product page (Superclick). It is
    one vendor figure, not a measurement. O-09 remains open. It is not evidence for or against the model's
    1 N·m peaks.

## 3. Hypotheses and what each predicts (INFERENCE)

| | Hypothesis | Prediction if true |
|---|---|---|
| H1 | **Clearance.** A tilt of 0.3–0.4° at a 20–40 mm lever moves a piece's lower edge by about 0.10–0.28 mm, more than the 0.05 mm gap, so the corner's lower chamfer drops to the level of the centre's upper chamfer | The catch measure falls steadily as the gap grows at a fixed chamfer. Counter-risk: B1 pieces are located only by contact, so a larger gap may allow proportionally larger tilts and leave the catch in place |
| H2 | **Chamfer ramp.** A longer 45° lead-in lifts the corner over the centre instead of wedging it | The catch is smaller at 2.0 mm and larger at 1.0 mm. (E5's chamfer 1.0 mm arm already failed one sequence on tilt) |
| H3 | **Contact softness.** Penetration (0.08–0.12 mm) larger than the gap lets pieces sink into each other and sets the catch geometry | Stiffer contacts (flat solimp 0.99; 0.25 ms with solref 0.5 ms) reduce penetration and the catch measure. Friction changes the catch only through the wedge |
| H4 | **Grip forces set the tilt.** The pads (grip drawn per seed, 13.36 N on 16100, at z ≈ 14–24 mm) act on ball-jointed pieces that can only rotate | Tilt and catch change with grip force (10 against 50 N). The sign of the effect has not been worked out |
| H5 | **Setup misalignment of the side faces.** A side centre turned 0.25° about its normal raises one end of its upper chamfer by up to about 9.5 mm × sin 0.25° ≈ 0.04 mm, close to the 0.05 mm gap | The catch weakens or disappears with misalignment 0 (E1-7: `6move` peak 0.465 → 0.110 N·m) |
| H6 | **Numerical.** Timestep or detection artefact | Results differ between 0.5 and 0.25 ms at the same physical parameters |

These are not exclusive. The design varies one family at a time around the nominal and the worst grid point.

## 4. Design (PROPOSAL)

### Stage 0 — read existing records (no simulation)
Tabulate, for every record that already holds per-move turner torque, the per-move peak, the number of clipped moves
and the drift. The sources:
- E5's E1-7 arms (§2, item 8, rechecked by script);
- E5's no-magnet arm (`results_nomag/`);
- D8's gap study (0.2 / 0.1 / 0.05 mm, with and without magnets);
- ER9's 13 `turn_*.json`.

Output: one table, so that Stage 1 can be read against what is already known. Records whose turner torque was not
stored are listed as such.

### Stage 1 — single-turn grid
- **Replay.** Seed 16100, first U of an E1-2 trial, exactly as `er9_turn_diag.py`: setup, grip, `rig.turn(U)`. Rig,
  timing (0.889 s per quarter), grip draw and misalignment draw are unchanged.
- **Grid.** Gap {0.05, 0.10, 0.25} mm × chamfer {1.0, 1.4, 2.0} mm × layout {none, W3, L0} = **27 replays**, plus
  X0.003 at (0.05, 1.4).
- **Instrumentation.** One process runs both diagnostics in one replay: the `er9_turn_diag` time series and the
  `er9_catch_diag` contact snapshot (§5). ER9 ran two separate scripts; one replay per point halves the cost and
  keeps the two consistent.
- **How the gap and chamfer reach the model.** Through `M4.BASE_OVERRIDES` (`gap`, `chamfer`) and the magnet layout's
  `gap` argument (`M4.use_magnets(..., gap)`), as ER7's `use_core` and D8's `rehearsal_gap.py` do. Each record must
  carry the compiled model's `gap` and `chamfer` and the magnet layout's gap (self-check S2).
- **Worst point.** The grid point with the largest catch impulse (§5) in the no-magnet layout. Also the nominal
  point (0.05, 1.4) for W3.

### Stage 2 — one-factor checks at the worst point and at W3's nominal point
Each check changes one setting from that point:
- (a) timestep 0.25 ms;
- (b) timestep 0.25 ms with cubie solref (0.5 ms, 1), so the contact is stiffer than refsafe allows at 0.5 ms;
- (c) flat cubie solimp (0.99, 0.99, 0.5 mm);
- (d) cubie friction 0.1 and (e) 0.5;
- (f) setup misalignment 0;
- (g) grip force 10 N and (h) 50 N.

That is 9 replays per point, **18 in all**.

Timestep 0.75 ms is excluded: refsafe would clamp the contact (§2, item 9), and E1-7 already shows it fails.

Contact and timestep settings go through `M1Params` fields. The global `o_solref`/`o_solimp` override is not used,
because it also changes pad contacts (`MUJOCO_CONTACT_CREEP_FINDINGS.md` §2.8).

### Stage 3 — robustness of any catch-free setting
For every Stage 1 or 2 setting classed "absent" (§5), and for the nominal:
- replay seeds 16101 (U) and 16102 (U′);
- with D10's alternative, also one R and one F move.

A setting counts as catch-free only if all of its replays are "absent".

### Stage 4 — guard rails for catch-free settings (G1's needs)
Run only for settings that pass Stage 3, each paired with the frozen nominal on the same seeds and the same layout:
- **Drift:** E1-7's `6move` and `sexy6` sequences (30 moves), with M1's non-target drift per move (limit 1°).
  Flag a setting whose maximum exceeds 0.8°. That is the level E1-7's 0.1 mm arm already reached with magnets.
- **Rest:** 2 × E1-1 (10 s), including one of L0's two slip seeds (SUMMARY Part D, signal 1); rest ≤ 0.5°.
- **Snap-back:** 2 × E1-5s from ±8° (seed 16568, as ER9's snap replay); error ≤ 0.5° after 1 s.

**Reading.** A setting that removes the catch but exceeds 1° drift, 0.5° rest or 0.5° snap-back in any of these
trades the stall for a G1 failure, and is reported as such. Passing the guard rails is a screening signal only, on a
handful of trials. It is not G1 evidence (P-25 shows that 3 of 3 sequences passed at 0.1 mm while the full rehearsal
failed on drift).

## 5. What is recorded, and what counts as a catch

**Per replay (time series every step in the window, every 20 steps outside it):**
- `t`, turner angle, U layer error, turner torque;
- per U piece: lag about z relative to the turner, tilt magnitude and axis (ER9's `catch_diag` method);
- number of cubie–cubie and pad contacts and their summed normal force;
- minimum contact `dist` (largest penetration), cubie–cubie and pad separately;
- pad slip, defined as turner angle minus layer angle;
- solver iterations used and any MuJoCo warning counters;
- magnet stats where magnets are present (`MagnetSystem.stats`).

**Per replay (scalars):**
- peak |torque| and the turner angle at the peak;
- fraction of turn steps at the clip (|τ| ≥ 0.999 N·m);
- the catch measures below;
- final layer error;
- largest lag and tilt at the catch step;
- largest penetration over the turn;
- wall time;
- the compiled `gap`, `chamfer`, timestep, solref, solimp, friction, grip force and misalignment draws;
- MuJoCo version, commit and machine load at start.

**Contact snapshot.** Taken at the first clipped step, or, if there is none, at the step of peak torque inside the
window. A second snapshot is taken at the step of largest summed cubie–cubie normal force (ER9's choice).

Each snapshot lists the top 8 cubie–cubie contacts by normal force, with:
- body names;
- position (mm);
- normal;
- `dist` (mm);
- whether the pair is corner–side-centre with a normal within 10° of 45° to the turn axis. This is the ER9
  signature.

**Catch classes (PROPOSAL; window = turner angle 3–15° from the start of the turn):**
- **Baseline** = median |τ| over turner angle 20–70°.
- **Catch impulse** (continuous primary measure) = ∫ max(0, |τ| − baseline) dt over the window, in N·m·s.
- **Clip catch:** any step in the window with |τ| ≥ 0.999 N·m.
- **Stall:** the layer advances < 0.05° over ≥ 30 ms in the window while the turner advances.
- **Sub-limit catch:** peak |τ| in the window ≥ 0.25 N·m and ≥ 3 × baseline. On ER9's samples, L0 at 16100 would
  qualify: 0.446 N·m against about 0.04 N·m.
- **Catch present** = clip catch or stall. **Attenuated** = sub-limit only. **Absent** = none of the three.

The class and the catch impulse are both reported, so that a trend shows even where the class does not change.

## 6. Self-checks (before any grid replay)
- **S1, reproduction.** The combined script at the frozen settings reproduces `turn_W3_s16100.json`,
  `turn_L0_s16100.json` and `turn_X0.003_s16100.json` (peak torque, clip fraction, final layer error, every
  20-step sample). It also reproduces `catch_W3_s16100.json` and `catch_L0_s16100.json` exactly.
- **S2, parameter propagation.** For one non-nominal point (0.25 mm, 2.0 mm, L0), the compiled model's cubie
  half-size equals (pitch − gap)/2 and its mesh vertices equal `_chamfered_box_vertices(h, chamfer)`. The magnet
  layout's corner–edge face gap equals gap + 2 × wall (D5).
- **S3, isolation.** Each replay runs in a fresh process, so no magnet neighbour list or table cache crosses replays
  (P-26's defect).

## 7. Resources and scheduling
- **Wall time: TODO.** ER9's `turn_*.json` files store no wall time, and its logs time whole trials across parallel
  workers.

  INFERENCE for scale only:
  - A replay covers about 2.6 s of simulated time (setup and grip to t ≈ 0.51 s; turn and settle to t ≈ 2.58 s),
    which is about 5,200 steps at 0.5 ms.
  - At P-60's measured throughputs (3,854 steps/s without magnets; 606 steps/s with the 40-magnet core layout), that
    is about 1.5 s to about 10 s of stepping. W3 (96 magnets) is probably slower, and recording contacts every step
    adds more.
  - Model build and table loading come on top.
  - Estimate: under a minute per replay, so Stages 1–3 (about 50–70 replays) in about 1 h serial, and 0.25 ms
    replays at about 2×.
  - Stage 4 trials are full trials: TODO, of the order of minutes each (ER9's summed wall time was 10.5 h for 204 L0
    trials).
- **Measure first.** Time the three S1 replays and update this estimate before the grid.
- **Memory.** One process, `--jobs 1`. Run only when the machine is idle. The Part E probe stopped three times on
  low memory while other jobs ran (SUMMARY Part E). ER10 must not run beside it.
- **Restartable.** One JSON per replay, written to a temporary file and then renamed. Existing files are skipped
  (ER9's practice, plus the atomic write the code review asked for).

## 8. What the result would and would not license

**Would license (each only as a proposal to the user):**
- **The catch disappears at a geometry setting** (gap and/or chamfer) on all Stage 3 replays, and the setting stays
  within the Stage 4 guard rails. Then a written **model-change proposal** may be put to the user: a "B1′" with that
  geometry, stating what is lost and what would have to be re-run (M5's battery, ER7, ER9, E1-7). A real-cube
  clearance measurement (R1) would be recommended before choosing a value. Nothing changes until the user approves,
  and a changed model starts its validation from the beginning.
- **The catch disappears only with contact or timestep settings.** Then a report that the catch is at least partly
  numerical (H3/H6), with a recommendation for an engineering review of the cubie contact parameters. These are
  frozen across every scored and rehearsal record, so the review would also cover what a change would invalidate.
- **The catch disappears only with zero misalignment or a different grip.** The frozen rig's draws are then implicated
  (H4/H5). A report to the user; no rig change.
- **The catch persists at every setting.** Then the evidence weighs against "artefact of the small gap" (INFERENCE),
  consistent with D8's 0.2 mm data (§2, item 7). That points to B1's abstractions (ball joints, no feet, rigid
  radius). The recommendation would be to raise CUBE_MECHANISM_FINDINGS §4's "M3" direction, or the M1 radial
  preload (D12), with the user, not to adopt either.

**Would not license:**
- any automatic change to B1, M5, the rig, contact parameters or the timestep;
- re-reading or re-scoring past records under a new setting;
- treating W3's turner saturation as resolved;
- any statement about a real cube's turning behaviour;
- using any ER10 replay as G1 evidence;
- choosing 0.25 mm as "the real gap" (D11).

## 9. Limits
- **Small sample.** Single seeds in Stages 1–2. Stage 3 adds two seeds at the points that matter, which is still a
  small sample.
- **Changing the gap changes more than the clearance.** It also changes piece size, outer cube size, pad first-contact
  position and (with D5's default) L0's face gap.
- **Changing the chamfer changes more than the ramp.** It also changes the pad contact patch and corner-cutting
  geometry. The factors are not physically separable in B1.
- **Stage 2 checks one factor at a time.** It will not find interactions.
- **One CAD for clearance.** The only real-mechanism clearance data come from one CAD with an unconfirmed licence and
  two different clearance numbers (§2, item 6).
- **The catch definition is chosen after seeing ER9's replays** (as were H1–H6), and is disclosed as such.

## 10. Inconsistencies and open points found while drafting
1. **"The real cube's gap is 0.25 mm"** is a CAD number: one GrabCAD model, one flat-face separation. The same CAD
   gives 0.033–0.038 mm minimum neighbour clearance in `CUBE_MECHANISM_FINDINGS.md` §3. The two are not reconciled
   anywhere.
2. **Existing data already show the 1 N·m limit without magnets at 0.2 mm** (D8 §5). The brief's inference should be
   framed as "partly an artefact", not "an artefact".
3. **ER9's SUMMARY says M5's magnets "suppress" the stall.** Its own L0 replay shows a 0.446 N·m catch at the same
   angle and on the same contact type. "Attenuate" is the accurate word.
4. **Older `turn_*.json` files have no `n_magnets` value** (only the G arms show 144), and none stores wall time.
5. **Order of work.** ER10 competes for memory with Part E's unfinished probe. D1's default puts it after.
