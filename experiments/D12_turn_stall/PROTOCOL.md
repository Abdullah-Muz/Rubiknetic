# D12 — Turning-stall diagnostic (PROTOCOL, to be fixed before any run)

**Status.** Approved in principle in P-67 item 5 (user: "all approvd", 2026-11-21): "approved with the review's
blocking fixes: a jam rule, an uncensored torque measure, and rehearsal seeds for its sequences. It is renamed D12
(ER10 stays free for a force-law validation), runs one process on an idle machine, and its protocol is committed
before any run."
- This text turns the draft `experiments/ER9_anchored_core_layouts/proposals/ER10_STALL_DIAGNOSTIC_DRAFT.md` into the
  protocol. It applies the review `REVIEW_F_G_ER10_2026-11-21.md` (T1–T11, X1–X7).
- It is fixed only once committed as `experiments/D12_turn_stall/PROTOCOL.md`, together with `d12_run.py`,
  `d12_stage0.py` and `d12_analyze.py`, before the first D12 computation. The main session records that commit in
  `docs/DECISION_LOG.md` (TODO: commit hash).
- §15 lists the choices made here that go beyond the approved draft. The user may reverse any of them before the
  commit.
- **Nothing has been run.** Every number below is either copied from a committed record (FACT, with file) or marked
  TODO with the script that computes it.

**What D12 is, and is not:**
- **Unscored, exploratory and diagnostic only.** It uses rehearsal seeds 16000–16999 only (§6). It never uses
  17000–17999, and never the scored seeds 10000–10999 (E5's E1-7 ran at seed 10000).
- **No change follows automatically.** D12 changes no record and no frozen parameter, and it selects no mechanism.
  The B1 geometry (piece gap 0.05 mm, chamfer 1.4 mm), the cubie contact parameters, the timestep and the M1/M5 turner
  rig (1 N·m limit) all stay frozen.
- **Any geometry change is the user's mechanical decision.** So is any change to contact parameters, the rig or the
  turner-torque policy. Each would need its own proposal, approval, pre-registration and full re-validation.
- **No verdict changes.** M5 stays NOT PASSED, and no mechanism has passed G1.
- **The diagnostic rig is not the frozen rig.** The clip-raised turner "R5" (§4) exists only inside D12. Every record
  made with it carries that label.

Labels: `FACT` (file and section given), `INFERENCE`, `PROPOSAL`, `TODO` (a number that needs a script run). Nothing
here is a `VALIDATED_RESULT`.

---

## 1. Question (fixed)

> Does the catch about 7° into a quarter turn depend on any of these: piece gap, chamfer size, cubie contact
> parameters (solref, solimp, friction), timestep, or the frozen rig's grip force and setup misalignment? Measure it
> with a torque that the 1 N·m clip does not censor.
>
> Is there a model setting at which the catch is absent on every replay, without breaking what G1 needs (drift
> ≤ 1° per move, rest ≤ 0.5°, snap-back ≤ 0.5°) on a small guard-rail set?

**The inference under test (INFERENCE).** The catch may be *partly* an artefact of the model's small clearance,
chamfer geometry or contact softness, rather than mechanics a real cube would show. Existing data already weigh
against "only a small-gap artefact" (§2, item 7).

**Out of scope:**
- changing B1, M5, ER9 records or any criterion;
- scoring anything;
- any statement about a real cube;
- new magnet layouts;
- M1's radial preload (draft decision "D12, radial retention"; renamed here to avoid a clash with this diagnostic's
  name). It is a different mechanism model and the user's mechanical decision.

## 2. What is known going in

1. **The stall** (FACT, ER9 `SUMMARY.md` "Diagnostics"; `results/probe/diag/turn_W3_s16100.json`,
   `catch_W3_s16100.json`; figures checked by the review):
   - Seed 16100, first U of an E1-2 trial, W3. The layer stops at about 6.7–6.9° while the turner torque reaches
     1 N·m. It breaks through at t ≈ 1.17 s. Peak 1.0 N·m; 4.3 % of the turn's steps are at the clip.
   - At the step with the largest summed cubie–cubie normal force (148 N, turner −7.96°), the top contacts are
     U-corner against side-centre, about 10 N each, with normals near 45° to the turn axis: (0.706, −0.081, 0.704) and
     (0.696, 0, −0.718). Both sit at z ≈ 9.55 mm (the layer boundary) and |y| ≈ 27.07 mm.
   - U pieces lag the turner by 0.60–1.55° and are tilted 0.14–0.39°.
2. **Penetration at the catch exceeds the gap** (FACT, `catch_W3_s16100.json`, field `dist`): 0.077–0.078 mm at the
   corner–centre contacts and 0.114–0.117 mm at in-layer contacts, against a 0.05 mm piece gap. INFERENCE: contact
   softness is on the scale of the clearance, so contact parameters are a plausible factor in their own right.
3. **During the stall the pad contacts drop** (FACT, `turn_W3_s16100.json`, t = 1.06–1.16 s): from 10 to 4. The
   turner advances 0.5° while the layer error stays at −6.80 to −6.93°. INFERENCE: pads slip or comply, so pad slip
   must be recorded. It is also a second ceiling on the torque the turner can deliver (§4).
4. **L0 shows a smaller catch at the same place** (FACT, `turn_L0_s16100.json`, `catch_L0_s16100.json`): peak
   0.461 N·m at turner −6.34°, on corner–side-centre pairs, penetration 0.029–0.036 mm. INFERENCE: M5's magnets
   *attenuate* the catch. ER9's summary says "suppress", which overstates it.
5. **Single replays are erratic** (FACT, `turn_*.json` summary fields): the ad hoc strength sweep is not monotone
   (X0.1 1.0, X0.03 0.782, X0.003 1.0 N·m). C52's replay on 16100 peaks at 0.419 N·m with no clip, yet C52 had 69
   clipped moves in its 204-trial rehearsal (ER9 SUMMARY Part D). INFERENCE: one seed cannot separate a trend from
   trajectory sensitivity (T4; §6, §11).
6. **Clearance in the real-mechanism CAD** (one GrabCAD model, licence unconfirmed):
   - FACT (ER9 `side_checks/README.md`, realfit): along M5's magnet lines the CAD has a 0.25 mm flat face separation.
   - FACT (`docs/research/CUBE_MECHANISM_FINDINGS.md` §3): "Neighbour clearance is 0.033–0.038 mm" at rest.
   - INFERENCE: the two numbers measure different things. B1 has one piece gap, so no single B1 gap reproduces both.
     0.25 mm is a grid level, not "the real gap".
7. **Earlier gap data** (FACT):
   - P-24/P-25: at 0.2 mm, drift exceeded 1° in 9 of 18 moves. At 0.1 mm, the 204-trial rehearsal failed 10 trials on
     drift (12 moves, max 1.14°; P-28 count).
   - P-26: at 0.2 mm the drift belongs to the B1 base, with or without magnets.
   - D8 `results/diag_m4_2026-11-15/SUMMARY.md` §5:
     - Without magnets the turner reached the 1 N·m limit at 0.2 mm (median 0.34, max 1.00 N·m) and at 0.05 mm
       (median 0.41, max 1.00).
     - At 0.05 mm with no magnets, the first move of one sequence **jammed**: the layer ended 86° short, penetration
       reached 0.76 mm, and the state was unreadable.
     - With magnets the medians were 0.095–0.12 N·m.
   - INFERENCE: the limit is reached without magnets at 0.2 mm too, which is evidence against a pure small-gap
     artefact.
8. **E5's E1-7 arms already cover L0's one-factor sensitivities** (FACT for pass/fail: `E5_scored_m5/RESULTS.md`
   "E1-7"). Turner and drift values were tallied from `results/E1-7/*.json` with grep and awk during drafting
   (2026-11-21); `d12_stage0.py` recomputes them. All are seed 10000, the frozen 1 N·m rig, layout L0, gap 0.05 mm
   unless named. See the Stage 0 table (§7.0).
9. **Contact and timestep context** (FACT, `m1_model.py` `M1Params`; `MUJOCO_CONTACT_CREEP_FINDINGS.md` §1–2, §2.8):
   - Cubie contacts: condim 3, μ 0.2, solref (1 ms, 1), solimp (0.95, 0.99, 0.5 mm); timestep 0.5 ms; elliptic cone,
     impratio 10, Newton, implicitfast. MuJoCo 4.0.1.
   - The refsafe floor is τ ≥ 2·dt. At 0.5 ms the cubie solref already sits at that floor.
   - The global `o_solref`/`o_solimp` override is global, so it would also change the pad contacts. D12 does not use
     it.
10. **Real-cube turning torque** (FACT, `docs/research/TURNING_TORQUE_FINDINGS.md` table row 1; P-62, P-63):
    - 0.09 N·m for "a traditional Rubiks Cube".
    - Source: Oskar van Deventer's TwistyPuzzles museum entry for the Superclick Cube (archived 2022-05-16, verified
      2026-11-19). It is a museum figure, not a vendor figure. P-62 calls it an undated hand measurement.
    - The same entry gives 2.7 N·m for the Superclick itself, a deliberately clicky magnetic novelty puzzle.
    - O-09 stays open.
    - P-67 item 4 adopts about 0.2 N·m as a realism reference, with a warning level at about 0.45–0.5 N·m. Turner
      torque is not a G1 criterion.
11. **How the turner works** (FACT, `m1_model.py` l.187–188; `rig.py` l.133–175):
    - The turner is a MuJoCo position actuator (kp 5 N·m/rad, kv 0.2) with `forcerange` ±`turn_torque_limit`, so the
      1 N·m limit is a pure clip on the PD force.
    - The target follows a cosine ramp over `turn_s_per_quarter` seconds (0.889 s on seed 16100), then hold, open and
      settle (0.3 s each).
    - All durations are converted to steps as round(seconds / timestep).
12. **The ER9 layer error cannot see a jam** (FACT, `D8_alignment/d8_1b_stage1.py` l.126–132). `layer_error` measures
    against the *nearest* lattice rotation, so a layer that ends 86° short of a quarter turn reads about 4°. A jam rule
    must use the layer's unwrapped rotation from the turn's start (`CubeReadout.rotation_about_deg`, `readout.py`
    l.48–59).

## 3. Hypotheses and predictions (INFERENCE)

| | Hypothesis | Prediction if true |
|---|---|---|
| H1 | **Clearance.** A tilt of 0.3–0.4° at a 20–40 mm lever moves a piece's lower edge by about 0.10–0.28 mm, more than the 0.05 mm gap | The R5 catch impulse falls steadily as the gap grows, at a fixed chamfer. Counter-risk: a larger gap may allow proportionally larger tilts |
| H2 | **Chamfer ramp.** A longer 45° lead-in lifts the corner over the centre instead of wedging it | Smaller catch at 2.0 mm, larger at 1.0 mm |
| H3 | **Contact softness.** Penetration larger than the gap sets the catch geometry | Stiffer contacts (flat solimp 0.99; 0.25 ms with solref 0.5 ms) reduce penetration and the catch. Friction acts only through the wedge |
| H4 | **Grip force sets the tilt** | Catch changes with grip 10 against 50 N; the sign is not predicted |
| H5 | **Setup misalignment.** A side centre turned 0.25° raises one end of its upper chamfer by up to about 9.5 mm × sin 0.25° ≈ 0.04 mm, close to the gap | Catch weaker or absent with misalignment 0 |
| H6 | **Numerical** | Results differ between 0.5 and 0.25 ms at the same physical parameters |

These hypotheses are not exclusive. The design varies one family at a time around fixed points (§7).

## 4. Torque measures: the frozen rig R1 and the diagnostic rig R5 (resolves T2)

**Two rigs (PROPOSAL, fixed).**
- **R1 = the frozen rig:** `turn_torque_limit` 1.0 N·m. Everything else is frozen.
- **R5 = the diagnostic rig:** `turn_torque_limit` 5.0 N·m. Nothing else changes: kp, kv, timing, pads and grip are
  the same. **R5 is not the frozen rig.** It is used only inside D12, to measure torque demand, and every R5 record
  carries `"rig": "R5-diagnostic (turn_torque_limit 5.0 N·m; NOT the frozen rig)"`.

**Why a raised clip, and not another measure.**
- **(a) Clip raised (chosen).**
  - FACT (§2, item 11): below the limit, the actuator force is the PD law, and `forcerange` only clips it.
  - INFERENCE: an R5 replay is therefore bit-identical to the R1 replay up to the first step at which R1's force
    reaches the limit. The catch onset is the same physical event, checked by self-check S4.
  - After that step, R5 keeps winding up until the contacts give way. Its peak is the torque at which the layer
    actually breaks through.
- **(b) The unclipped PD command, kp(target − θ) − kv·ω (rejected as the primary measure; recorded).** During a stall
  this command rises with time at the target's rate. It measures how long the layer is held, not how much torque the
  layer needs.
- **(c) A resisting torque derived from the contacts on the turning layer (rejected as primary; recorded as a
  cross-check).** During a stall it balances the torque delivered, so the same clip censors it.
- **(d) A quasi-static torque ramp on a free layer (out of scope).** It uses a different load path, without the rig's
  trajectory, and would need a new harness. It could be a later, separate proposal.

**The level, 5 N·m.**
- FACT: kp is 5 N·m/rad, so the force reaches 5 N·m only when the target leads the turner by 1 rad (57°).
- INFERENCE: reaching 5 N·m therefore means the layer has been held for most of the turn, which is jam-like behaviour,
  not a catch. A catch released below 5 N·m is measured uncensored.
- 5 N·m is above every figure in `TURNING_TORQUE_FINDINGS.md`, including the Superclick's 2.7 N·m.
- The gap analysis (A10) gave 3 N·m as an example. 5 N·m is chosen so that hitting the ceiling is rare (§15, item 1).

**Remaining censoring, which is flagged rather than hidden.**
- **At the 5 N·m ceiling:** any step with |τ| ≥ 4.995 N·m flags the record `censored_R5`, and its peak is a lower
  bound.
- **At the pads:** the torque reaching the layer is also limited by pad slip (§2, item 3). Pad slip is turner angle
  minus layer angle (unwrapped, §2 item 12). If pad slip grows by more than 1.0° inside the catch window while the
  layer is stalled, the record is flagged `pad_limited`, and its R5 peak is a lower bound on the demand.
- Both flags are reported beside every R5 number.

**What R5 numbers mean (INFERENCE).**
- An R5 peak is a breakthrough torque at the rig's wind-up rate. It depends on that rate, and it is neither a
  quasi-static breakaway torque nor a real-cube torque.
- After the breakthrough, R5 carries more stored energy than R1, so its post-catch trajectory differs. **R5's final
  layer error, drift and settling are not read.** Only R1 replays and Stage 4 (R1 only) speak to G1-type behaviour.
- R5 peaks are also reported against P-67's realism reference (0.2 N·m) and warning level (0.45–0.5 N·m), for
  information only.

**Where each rig runs.**
- Stages 1–3 use R5 as the primary measure.
- R1 is repeated at the nominal point on all five nominal seeds, and at every catch-free candidate (§7).
- Stage 4 uses R1 only.

## 5. Classes: jam, catch, absent (resolves T1, T10, T11)

**Catch window:** turner angle 3–15° from the turn's start. **Baseline:** median |τ| over turner angle 20–70°.

**Jam (checked first; it excludes every other class).** A replay is a JAM if any of these holds:
- **J1, the layer did not follow.** At the end of the hold phase, before the pads open, the turning layer's achieved
  rotation differs from the commanded quarter turn by more than 20°.
  - The rotation is the median over the 8 non-centre pieces that were in the layer at the turn's start, using
    `CubeReadout.rotation_about_deg` from the turn-start snapshot. `layer_error` cannot see this (§2, item 12).
- **J2, penetration.** The largest cubie–cubie penetration at any step of the move exceeds 0.5 mm. That is the
  project's penetration limit (P-24 A2, E1-6t). D8's jam reached 0.76 mm.
- **J3, illegal or unreadable state.** After settle, `CubeReadout.observe` does not return the oracle state after the
  commanded move, or cannot read a state.

**Recorded for every jam:** which of J1–J3 fired, the time each first held, the layer's shortfall in degrees, the
largest penetration, and the R5 flags.

**Jam is distinct from a catch.** A catch is a transient hold that ends with the layer within 20° of the commanded
turn by the end of the hold, with a legal state and penetration ≤ 0.5 mm. A jam is a failure to complete.

**How the analysis treats jams:**
- Jam replays keep their torque measures in the records. Those measures are excluded from medians, trends and the
  worst-point choice, because a jam maximises the catch impulse without being the catch under study (T1).
- A point with any jam can never count as catch-free.
- Jams get their own table: per layout, point and rig, k of n seeds.
- "Jam under R1, completes under R5" is reported as its own outcome: the resistance lies between 1 and 5 N·m.
- A jam is a finding, not an error. It is never re-run.

**Catch classes (for non-jam replays):**
- **Catch impulse** (the continuous primary measure): ∫ max(0, |τ| − baseline) dt over the window, in N·m·s.
- **High catch:** under R5, peak |τ| in the window ≥ 1.0 N·m, meaning the frozen rig would have clipped. Under R1,
  the same rule with the clip threshold (any window step ≥ 0.999 N·m) is called a "clip catch".
- **Stall:** in the window, the layer advances less than 0.05° over at least 30 ms while the commanded turner target
  advances.
- **Sub-limit catch:** peak |τ| in the window ≥ **0.2 N·m** (P-67 item 4's realism reference) and ≥ 3 × baseline,
  without being a high catch.
  - The draft used 0.25 N·m. The level is tied to the approved reference (T10).
  - FACT: on ER9's samples L0 at 16100 would qualify (0.446 N·m against a baseline of about 0.04 N·m).
- **Catch present** = high (or clip) catch, or stall. **Attenuated** = sub-limit only. **Absent** = none of these and
  not a jam.
- A window peak ≥ 0.45 N·m is also flagged "above warning level". This is information only.

**Freeze (T11).**
- The window, baseline, thresholds (1.0, 0.999, 0.2, 3×, 0.05° / 30 ms, 20°, 0.5 mm, 4.995 N·m, 1.0° pad slip) and
  the class rules **cannot change after Stage 1 starts**.
- They were chosen after seeing ER9's replays, and L0's catch was used to set the sub-limit rule. That is disclosed in
  §14.

## 6. Seeds (resolves T3, T4; X4)

**Every seed is fixed here.** The runner refuses any seed outside this list (self-check S5).

| Use | Seeds | Move | Source of the seed |
|---|---|---|---|
| Grid, all layouts and points | **16100, 16101, 16900** | U | 16100 and 16101 are ER7's two E1-2 U seeds (FACT: `E1_scored/run.py` l.43–50, seed 1100 + k over faces U R F D L B, two of each of q = 1 and q = 3; ER7 shift +15000). 16100 is ER9's stall replay. 16900 is a fresh draw |
| Nominal replication (5 seeds) | grid seeds + **16901, 16902** | U | fresh draws |
| Stage 3 robustness | **16102** (U′), **16104** (R), **16108** (F), **16903**, **16904** (U) | as listed | 16102, 16104 and 16108 are ER7's E1-2 seeds for those moves; the last two are fresh draws |
| Stage 4 sequences | **16910, 16911** | E1-7's `6move` "U U' R R' F F'" and `sexy6` "R U R' U'" × 6 | fresh draws |
| Stage 4 rest (E1-1, 10 s) | **16000, 16003** | — | ER7's E1-1 seeds; 16003 is one of L0's two slip seeds (FACT, ER7 `SUMMARY.md` l.36) |
| Stage 4 snap-back (E1-5s) | **16568**, +8° and −8° | — | ER7's E1-5s range; the seed of ER9's snap replay |

**Reserved block.**
- D12 reserves **16900–16999** for its fresh draws.
- A repository search on 2026-11-21 found no use of 16656–16999. Part G's draft names 16656–16999 only as an
  alternative.
- 16656–16899 stay free for other work. The reservation should be noted in the decision-log row.

**The E1-7 sequences are reseeded (T3).**
- E5 ran them at scored seed 10000 (FACT: `E4_scored_m4/run.py` l.145–157, `shift_seed(1000)`; record
  `nominal__6move.json`, `setup.seed` 10000).
- D12 uses the same move strings, but their setups are drawn by `draw_setup` from 16910 and 16911.
- **Pairing with E5's E1-7 records is not wanted.** It would need seed 10000 and would breach the status line. Stage 0
  compares with E1-7 descriptively only.

**Never used:** 17000–17999 (held out), and 10000–10999 (E5's scored range, including E1-7's 10000).

**The post hoc chain (X4).** ER7, ER8, ER9 and now D12 all draw on 16000–16655. Any later pre-registration must
disclose that chain (gap analysis C2). D12's reuse is diagnostic, and it adds the reserved block to the chain.

## 7. Design

### 7.0 Stage 0 — existing records and written predictions (no simulation; resolves T7)

`d12_stage0.py` (TODO, read-only JSON parsing) tabulates per-move turner peak, clipped-move count and drift for:
- E5's E1-7 (all arms);
- E5's no-magnet battery (`results_nomag/`, its E1-2 single moves);
- D8's gap study (`diag_m4_2026-11-15/gap_study/`);
- ER9's 13 `turn_*.json`.

Its output is committed before Stage 1.

**E1-7 tallies quoted as the starting point** (FACT from `E5_scored_m5/results/E1-7/*.json`, keys
`max_turner_torque_Nm` and `nontarget_drift_deg`; tallied with grep and awk on 2026-11-21. If `d12_stage0.py`
disagrees, its value governs and the mismatch is reported.) Seed 10000, R1, L0, gap 0.05 mm unless named. "U peak" is
the first move of `6move`, which is a U turn like D12's grid replays.

| Arm | `6move` U peak / max / clipped / max drift | `sexy6` max / clipped / max drift | Pass (6move, sexy6) |
|---|---|---|---|
| nominal | 0.465 / 0.465 / 0 / 0.474° | 0.640 / 0 / 0.517° | pass, pass |
| gap 0.025 mm | 0.373 / 0.373 / 0 / 0.331° | 0.491 / 0 / 0.381° | pass, pass |
| gap 0.1 mm | 0.456 / 0.456 / 0 / 0.805° | 0.464 / 0 / 0.894° | pass, pass |
| chamfer 1.0 mm | 0.813 / 0.813 / 0 / 0.280° (5 moves recorded) | 0.568 / 0 / 0.510° | **FAIL**, pass |
| chamfer 2.0 mm | 0.447 / 0.447 / 0 / 0.467° | 0.502 / 0 / 0.593° | pass, pass |
| friction 0.1 | 0.309 / 0.400 / 0 / 0.350° | 0.388 / 0 / 0.376° | pass, pass |
| friction 0.5 | 0.504 / 0.504 / 0 / 0.466° | **1.000 / 5** / 0.586° | pass, pass |
| friction 1.0 | 0.743 / 0.743 / 0 / 0.473° | **1.000 / 3** / 0.586° | pass, pass |
| grip 10 N | 0.557 / 0.557 / 0 / 0.477° | 0.570 / 0 / 0.379° | pass, pass |
| grip 30 N | 0.460 / 0.460 / 0 / 0.493° | 0.471 / 0 / 0.355° | pass, pass |
| grip 50 N | 0.445 / 0.925 / 0 / 0.496° | 0.489 / 0 / 0.505° | pass, pass |
| misalignment max 0° | 0.095 / 0.110 / 0 / 0.476° | 0.477 / 0 / 0.381° | pass, pass |
| misalignment max 2° | 0.252 / 0.252 / 0 / 0.528° | 0.492 / 0 / 0.583° | pass, pass |
| misalignment max 5° | 0.463 / 0.463 / 0 / 0.496° | 0.474 / 0 / 0.468° | pass, pass |
| timestep 0.25 ms | 0.632 / 0.632 / 0 / 0.512° | 0.597 / 0 / 0.566° | pass, pass |
| timestep 0.75 ms | 0.106 / 0.129 / 0 / 0.536° | 0.389 / 0 / 0.571° | **FAIL**, **FAIL** |
| magnets none | **1.000 / 1.000 / 2** / 0.578° (2 moves recorded) | **1.000 / 5** / 0.843° | **FAIL**, pass |

**Predictions, written before Stage 1** (INFERENCE from the table and §2). They are stated so that the reading is not
post hoc. Each rests on one seed or on a small sample.
- **Pr1, no magnets at nominal.** The R5 window peak is ≥ 1 N·m on at least 2 of 3 grid seeds, or the replay jams
  (E1-7 `magnet=none`; D8's jam).
- **Pr2, gap.** In L0, the catch impulse is not monotone in gap beyond the nominal seed spread (E1-7: 0.373 / 0.465 /
  0.456). In the no-magnet layout, the catch persists at 0.25 mm on at least one seed (D8: 1.00 N·m at 0.2 mm).
  Drift rises with gap (E1-7: 0.38 → 0.52 → 0.89° in `sexy6`).
- **Pr3, chamfer.** 1.0 mm raises L0's catch (U peak 0.813 against 0.465) and may trip L0's 5° tilt flag (E1-7's
  1.0 mm failure was a magnet tilt of 11.97°). 2.0 mm changes it little.
- **Pr4, friction.** Higher cubie friction raises the catch in every layout (L0 clipped at μ 0.5 and 1.0 in `sexy6`).
- **Pr5, misalignment 0.** It lowers the catch on some seeds but not on all (E1-7 is not monotone: 0.095 / 0.465 /
  0.252 / 0.463 at maxima 0 / 1 / 2 / 5°).
- **Pr6, timestep 0.25 ms.** It does not remove the catch (E1-7: 0.632 against 0.465).
- **Pr7, guard rail.** Any catch-free setting with gap ≥ 0.10 mm flags (≥ 0.8°) or fails (> 1°) the Stage 4 drift
  guard rail (§7.4).

**What Stages 1–2 add beyond E1-7 (T7).**
- An uncensored torque measure (R5) where the clip binds.
- The no-magnet cube and W3 at one-factor settings. E1-7 tested only L0 one factor at a time, except the single
  `magnet=none` arm at the nominal point.
- The crossed gap × chamfer grid, and the 0.25 mm level.
- Three seeds instead of one, the jam and catch classes, and a contact snapshot of each catch.
- **Stage 2 does not re-run L0's one-factor checks.** E1-7 already covers grip, friction, misalignment, gap, chamfer
  and timestep for L0 (§7.2).

### 7.1 Stage 1 — gap × chamfer grid

- **Replay.** One E1-2 single-move trial: setup (`draw_setup(seed)`), settle 0.5 s, grip, `rig.turn(move)`, hold, open,
  settle. This is exactly the frozen trial that `er9_turn_diag.py` replays, with the per-seed timing, grip and
  misalignment draws unchanged.
- **Layouts:**
  - **none**: no magnet system, as in E5's `magnet=none` arm;
  - **L0**: M5's 48 4×2 mm N35 magnets, wall 0.4 mm, so face gap = piece gap + 0.8 mm (draft decision D5, approved);
  - **W3**: ER9's anchored layout. It is diagnostic only and can never yield a candidate (§8.2).
- **Grid:** gap {0.05, 0.10, 0.25} mm × chamfer {1.0, 1.4, 2.0} mm × layout {none, L0, W3} × grid seeds
  {16100, 16101, 16900}, all under R5. That is **81 replays**.
  - 0.25 mm is kept explicitly as a demonstration of the clearance-against-drift trade-off. It is not a candidate
    value (T8; Pr7).
- **Nominal point (0.05, 1.4) for each layout:**
  - R5 on 16901 and 16902 as well: **6 replays**. With the grid seeds that makes 5 R5 seeds per layout.
  - R1 on all five nominal seeds: **15 replays**. The R1 replays of L0 and W3 on 16100 double as self-check S1.
- **Link to ER9:** X0.003 at the nominal point on 16100 under R1, only as part of S1.
- **How gap and chamfer reach the model:** through `BASE_OVERRIDES` (`gap`, `chamfer`) and the magnet layout's `gap`
  argument (`use_magnets(mp, gap)`), as ER7's `use_core` and D8's `rehearsal_gap.py` do. Every record carries the
  compiled values (S2).

### 7.2 Stage 2 — one-factor checks (no-magnet cube and W3 only)

**Two points:**
- **P-none: the worst no-magnet point.** Among the no-magnet grid points with no jam on any of the 3 grid seeds, take
  the one with the largest median R5 catch impulse. If no no-magnet point qualifies, Stage 2 runs at P-W3 only, and
  the reason is reported (T1).
- **P-W3:** W3 at the nominal point (0.05, 1.4).

**Checks, each changing one setting from the point:**
- (a) timestep 0.25 ms;
- (b) timestep 0.25 ms with cubie solref (0.5 ms, 1). This is stiffer than refsafe allows at 0.5 ms;
- (c) flat cubie solimp (0.99, 0.99, 0.5 mm);
- (d) cubie friction 0.1;
- (e) cubie friction 0.5;
- (f) setup misalignment 0;
- (g) grip 10 N;
- (h) grip 50 N.

**Count:** 8 checks × 3 grid seeds × 2 points = **48 R5 replays**, of which 12 are at 0.25 ms and cost about double.
The point's own Stage 1 replays serve as the reference.

**Not run:**
- Timestep 0.75 ms, because refsafe would clamp the contact and E1-7 already fails there.
- L0's one-factor checks, because E1-7 covers them (Stage 0; T7).

Contact and timestep settings go through `M1Params` fields only (cubie_solref, cubie_solimp, cubie_friction,
timestep), never through the global override.

### 7.3 Stage 3 — robustness of catch-free candidates

**Candidate.** A Stage 1 or Stage 2 setting in layout none or L0 that is:
- "absent" on all 3 grid seeds under R5;
- jam-free;
- not validity-flagged (§8.2).

A W3 setting is never a candidate (§8.2).

**For each candidate:**
- R5 on the Stage 3 seeds: 16102 (U′), 16104 (R), 16108 (F), 16903 and 16904 (U). That is 5 replays.
- R1 on the 3 grid seeds. S4 predicts that these are identical to R5 wherever R5 never reached 1 N·m.

**Catch-free** means all 8 R5 replays and all 3 R1 replays are "absent", jam-free and not flagged.

**Cap.** If there are more than 6 candidates, Stage 3 runs on the 6 with the lowest median R5 catch impulse, and the
rest are listed. Count: at most 6 × 8 = **48 replays**.

### 7.4 Stage 4 — guard rails (R1 only, in L0; resolves T8)

**What runs.** Every setting that passes Stage 3 is run **in L0**, whichever layout it was found in, under R1. Each run
is paired with L0 at the frozen nominal setting on the same seeds.
- Reason: the no-magnet cube already fails E1-7 at the nominal point (FACT, §7.0), so guard rails in that layout say
  nothing about G1's needs. L0 is M5's layout.
- **Cap:** at most 3 settings, those with the lowest median R5 catch impulse in L0. Beyond that the run returns to the
  user.

**Guard rails (§6 seeds):**
- **Drift:** `6move` and `sexy6` on 16910 and 16911 (4 trials, 60 moves), with M1's non-target drift per move.
  - Fail above 1°. Flag at ≥ 0.8°, the level E1-7's 0.1 mm arm reached (0.805° and 0.894°).
- **Rest:** E1-1 for 10 s on 16000 and 16003. Rest rotation must be ≤ 0.5°.
- **Snap-back:** E1-5s from +8° and −8° on 16568. The error must be ≤ 0.5° after 1 s.

**Count:** 8 trials per setting, plus 8 for the paired nominal. At most 32 trials.

**Expected outcome, stated in advance (T8; Pr7; INFERENCE).**
- A catch-free setting reached by raising the gap is expected to fail or flag the drift guard rail. That is what
  P-24, P-25, P-26, D8 §5 and E1-7's 0.1 mm arm show.
- That outcome would be reported as "trades the stall for drift". It is a demonstration of the trade-off, not a
  surprise.

**What passing means.** Passing the guard rails is a screening signal on 8 trials only, not G1 evidence. P-25: 3 of 3
sequences passed at 0.1 mm, but the full rehearsal then failed on drift.

## 8. Overrides and validity (resolves T5, T6)

### 8.1 Overrides never shift the seeded draws (T5)
- **Draw first, then replace.** Every replay first calls `draw_setup(seed, misalign_max_deg=1.0)` exactly as the
  frozen trial does: six misalignments, then grip, then turn time. Only then does it replace the field under test:
  - grip → 10 or 50 N;
  - every face misalignment → 0;
  - gap, chamfer, contact or timestep fields → the `M1Params` value.
- Self-check S6 confirms that every field not under test equals the nominal record's value for that seed.
- **Timestep.** All rig and trial durations are in seconds and converted to steps by round(s / dt) (FACT, §2 item 11),
  so the turn lasts the same 0.889 s on seed 16100 at 0.25 ms. Self-check S7 confirms this to within one step.

### 8.2 Validity of magnet layouts at non-nominal settings (T6; X1)
- **L0.**
  - Every replay records `MagnetSystem.stats`: `max_near_tilt_deg`, `near_perpendicular`, `clamped_z`, `max_force_N`.
  - A replay is **flagged out of regime** if `max_near_tilt_deg` > 5° (M5's validated tilt for 4×2 mm, P-24) or
    `near_perpendicular` > 0. It is also flagged if the face gap leaves V3's validated 0.5–1.5 mm. At the grid's
    levels the face gap is 0.85, 0.90 and 1.05 mm, all inside.
  - L0 has one magnet class, so the pooled stats are per class.
  - M5's known gap is disclosed, not flagged: corner–edge pairs that cross a turning boundary pass lateral offsets of
    6–8 mm, while V3a covers 0–6 mm (review G11).
- **W3.**
  - Its off-axis anchor-to-core pairs lie outside P-60's validated set at every pose (ER9 SUMMARY, Limits; review F1),
    so every W3 replay is **proxy-flagged** by construction.
  - **W3 results are mechanism diagnosis only.** They can never make a setting catch-free or a candidate.
  - When Part G's per-class stats tool exists and has been reviewed (X1), its output is added to the W3 records. D12
    does not wait for it.
- **none:** no magnet validity question arises.
- **A flagged replay keeps its measures in the tables, marked.** It cannot count toward "catch-free".

## 9. What is recorded

**Time series** (every step inside the catch window and around any catch, every 20 steps elsewhere):
- `t`, turner angle, commanded target, turner torque, unclipped PD command (§4 b), the layer's unwrapped rotation and
  `layer_error`, pad slip;
- per turning-layer piece: lag about the face axis relative to the turner, and tilt magnitude and axis (ER9
  `catch_diag` method, generalised from U to the turned face);
- counts and summed normal force of cubie–cubie and pad contacts;
- the contact-derived resisting torque on the turning layer about the face axis (§4 c);
- the largest cubie–cubie penetration and the largest pad penetration;
- solver iterations and MuJoCo warning counters;
- `MagnetSystem.stats` where magnets are present.

**Scalars per replay:**
- rig label; peak |τ| and turner angle at the peak; window peak; baseline; catch impulse;
- fraction of turn steps at R1's clip (|τ| ≥ 0.999); flags `censored_R5` and `pad_limited`;
- class (jam / present / attenuated / absent), with the jam fields of §5;
- final layer error (read for R1 only); largest lag and tilt at the catch; largest penetration;
- the validity flag;
- the compiled gap, chamfer, timestep, solref, solimp, friction, grip and all setup draws;
- MuJoCo version, repository commit, wall time, peak RSS, and machine load and free memory at start.

**Contact snapshots:**
- At the first step with |τ| ≥ 0.999 N·m (or the window peak if there is none), and at the step of largest summed
  cubie–cubie normal force (ER9's choice).
- Each lists the top 8 cubie–cubie contacts with body names, position (mm), normal and `dist` (mm).
- Each contact is marked if it has **the ER9 signature**: a corner–side-centre pair with its normal within 10° of 45°
  to the turn axis.
- The analysis reports, per point, the fraction of snapshots carrying the signature. A setting where the catch
  persists on a different contact type is then distinguished from one where it disappears.

## 10. Self-checks (before the grid; a failure stops the run)

- **S1, reproduction.** At the frozen settings under R1, the D12 runner reproduces `turn_W3_s16100.json`,
  `turn_L0_s16100.json` and `turn_X0.003_s16100.json` exactly: peak, clip fraction, final layer error and every
  20-step sample. It also reproduces `catch_W3_s16100.json` and `catch_L0_s16100.json` exactly.
  - If the shared replay tool recommended in X3 exists and has been reviewed, D12 uses it and its check against all
    13 `turn_*.json` files.
  - Otherwise D12's runner has its own arm registry {none, L0, W3, X0.003, W1, C52} and refuses every other name
    (review G7). W1 and C52 are registered only so that the runner also reproduces `turn_W1_s16100.json` and
    `turn_C52_s16100.json`; they are not used in any stage.
- **S1b, no-magnet build.** No earlier no-magnet replay exists on a rehearsal seed, so the build is checked
  structurally:
  - no magnet callback is installed;
  - the compiled `M1Params` equal those in E5's `magnet=none__6move.json`, except the seed-drawn fields.
- **S2, parameter propagation.** At (0.25 mm, 2.0 mm, L0):
  - the compiled cubie half-size equals (pitch − gap) / 2;
  - the mesh vertices equal `_chamfered_box_vertices(h, chamfer)`;
  - L0's corner–edge face gap equals gap + 2 × wall.
  - For W3, the record states whether its magnet positions change with the piece gap.
- **S3, isolation.** Every replay runs in a fresh process, so no neighbour list or table cache crosses replays (the
  defect fixed in P-26).
- **S4, R5 equals R1 before the clip.** For each layout at the nominal point on 16100, the R5 and R1 time series are
  bit-identical up to the first step at which R1's |actuator force| reaches 0.999 N·m. If R1 never reaches it, they
  are identical throughout.
- **S5, seeds.** The runner asserts that every seed is in §6's list, prints and stores the full job list before the
  first replay, and refuses 10000–10999 and 17000–17999.
- **S6, draws preserved.** For every override replay, all setup fields not under test equal the nominal replay's
  fields for the same seed.
- **S7, timestep.** At 0.25 ms, the turn, hold, open and settle durations in seconds equal the 0.5 ms values to within
  one step.
- **S8, read-only instrumentation.** The hooks only read `mjData`. S1 shows this, because the instrumented replays
  reproduce the records bit for bit.

## 11. Analysis rules (fixed before Stage 1)

**Noise yardstick.** Per layout, the range of the R5 catch impulse across the 5 nominal seeds.

**Trend (T4).** A factor shows a trend in a layout only if both hold:
- the R5 catch impulse is monotone across the factor's three levels in at least 2 of the 3 grid seeds; and
- the difference between the medians at the extreme levels exceeds that layout's nominal range.

Otherwise the result reads "no trend distinguishable from seed spread". Jam replays are excluded and counted (§5).

**One-factor effect (Stage 2).** An effect is reported only if the median over 3 seeds moves by more than the nominal
range, and in the same direction on at least 2 of 3 seeds.

**Classes.** Report, per point, the class on each seed, the median catch impulse, the median window peak (with flags),
the jam count, the share of snapshots with the signature, and the validity flags.

**Worst point.** Chosen by §7.2's rule. Jams are excluded.

**Catch-free.** As defined in §7.3. Guard rails as in §7.4. The prediction checks Pr1–Pr7 are each reported as held,
not held or not testable.

**Negative and null results are kept and reported.**

## 12. Resources, scheduling and stop rules (X5, X7)

**When it runs.**
- D12 runs only on an idle machine, with **one simulation process at a time**: a driver launches one fresh replay
  process after another (S3).
- It never runs beside Part E's probe, Part G or any other simulation (X7).
- It runs after Part E's probe is finished or stopped (P-67 item 7). Per the review, it can use an idle gap while
  Part G's code is being reviewed.
- The Part E probe stopped three times on low memory while other jobs ran (ER9 SUMMARY Part E).

**Timing test first (before Stage 1).**
- Time the S1 replays (W3, L0 and X0.003 under R1), plus one no-magnet replay under R1, one under R5, and one L0
  replay at 0.25 ms under R5.
- Record the wall time and peak RSS of each, then project Stages 1–3 from the counts below.
- Wall time depends on machine load (review G6: the same W3 trial took 42 s and 66 s), so load is recorded at each
  start.

**Scale (INFERENCE, to be replaced by the measurements).**
- A replay is about 2.59 s of simulated time, about 5,200 steps at 0.5 ms.
- At P-60's 3,854 steps/s without magnets and 606 steps/s with 40 magnets, stepping takes about 1.5–10 s. W3 has 96
  magnets and is slower. Per-step logging, model build, table loading and process start come on top.
- Probably under a minute per replay. TODO: measured, `d12_run.py --timing`.

| Stage | Replays or trials |
|---|---|
| Self-checks and timing | about 10 |
| 1 | 81 + 6 + 15 = 102 |
| 2 | 48 (12 at 0.25 ms) |
| 3 | ≤ 48 |
| 4 | ≤ 32 full trials (sequences of up to 24 moves, 10 s rests, snaps) |

**Stop rules (fixed). Stop and return to the user if:**
- the timing test projects Stages 1–3 above **6 h** of serial wall time;
- any single replay takes more than **3 ×** the timing-test wall time of its class (layout × timestep) or more than
  **15 min**. Part E's E1-2 trials ran about 10 × slower than W3's (review G6);
- a replay's peak RSS exceeds **2 ×** its class's timing-test value, or free memory at a replay's start is below the
  floor set from the timing test (TODO: the floor, recorded before Stage 1);
- Stage 4 is projected above **4 h**, measured on its first sequence trial.

**Restartable.**
- One JSON per replay, written to a temporary file and then renamed. Existing records are skipped.
- A crashed replay is recorded with its traceback and is not retried silently. A jam is not a crash.

**Outputs.** Only under `experiments/D12_turn_stall/results/` (`selfcheck/`, `timing/`, `stage0/` … `stage4/`). The
runner refuses to run from uncommitted code, and every record carries the commit.

## 13. What the result would and would not license

**Would license, each only as a written proposal to the user:**
- **The catch is absent at a geometry setting** on every Stage 3 replay, and that setting passes Stage 4 in L0.
  - A "B1′" model-change proposal may then be put to the user. It would state what is lost and what must be re-run
    (M5's battery, ER7, ER9, E1-7).
  - A real-cube clearance measurement (R1 bench) would be recommended first.
  - Nothing changes until the user approves, and a changed model restarts validation.
- **The catch is absent only with contact or timestep settings.** That would be reported as a catch that is at least
  partly numerical (H3/H6), with a recommendation for an engineering review of the cubie contact parameters. These
  are frozen across every scored and rehearsal record, so the review would also cover what a change would invalidate.
- **The catch is absent only with misalignment 0 or another grip.** The rig's draws are then implicated (H4/H5). That
  is reported to the user; the rig does not change.
- **The catch persists at every setting.** The evidence then weighs against a small-gap artefact (INFERENCE),
  consistent with D8 at 0.2 mm, and points to B1's abstractions (ball joints, no feet, rigid radius). Raising
  CUBE_MECHANISM_FINDINGS §4's "M3" direction or M1's radial preload with the user would be recommended, not adopted.
- **R5 torque demand.** R5 numbers inform the user's turner-torque policy (gap analysis A10 options a–c; P-67 item 4).
  They do not change the rig.

**Would not license:**
- any automatic change to B1, M5, the rig, contact parameters or the timestep;
- treating R5 as a rig, or R5's post-catch behaviour as frozen-rig behaviour;
- re-reading or re-scoring past records under a new setting;
- treating W3's saturation as resolved;
- any W3 setting as a candidate;
- any statement about a real cube's turning behaviour or torque;
- using any D12 replay as G1 evidence;
- treating 0.25 mm as "the real gap".

## 14. Limits

- **Small samples.** There are 3 seeds per grid point, 5 at the nominal point, and at most 8 at a candidate. These are
  screening numbers.
- **Mostly U turns.** R, F and U′ appear only in Stage 3. Gravity breaks the symmetry between faces.
- **R5 is rate-dependent** and is not the frozen rig. Pad transmission can still censor it (flagged).
- **Changing the gap changes more than the clearance:** piece size, outer size, pad first-contact position and L0's
  face gap all change too. **Changing the chamfer changes more than the ramp:** the pad patch and corner geometry
  change too. In B1 these factors cannot be separated physically.
- **Stage 2 tests one factor at a time** and will not find interactions.
- **W3 is proxy-flagged throughout,** so it is diagnosis only.
- **The Stage 0 predictions rest on E1-7's single seed** (10000).
- **One CAD with an unconfirmed licence** is the only source of clearance data, and it gives two different numbers.
- **The thresholds and windows were chosen after seeing ER9's replays,** and the sub-limit rule was set so that L0
  qualifies. They are frozen from Stage 1 (§5).

## 15. Choices made here beyond the approved draft (the user may reverse any before the commit)

1. **R5 at 5 N·m** as the uncensored measure. The alternative is 3 N·m (the gap analysis's example), which would be
   censored more often.
2. **Jam thresholds:** 20° shortfall at the end of the hold, penetration 0.5 mm, or an illegal or unreadable state.
3. **Seeds:** three grid seeds for the whole grid (the draft's alternative, now the default under T4), five at the
   nominal point, and a D12 reservation of 16900–16999.
4. **Sub-limit catch threshold** 0.2 N·m, tied to P-67 item 4 (the draft had 0.25 N·m).
5. **W3 is diagnosis only,** so candidates come from none and L0, and Stage 4 runs in L0 only.
6. **0.25 mm is kept** as a labelled demonstration level. The alternative is to drop it (T8).
7. **Caps:** at most 6 Stage 3 candidates and 3 Stage 4 settings.
8. **Stop-rule numbers:** 6 h, 3 ×, 15 min, 2 × RSS, 4 h.
9. **Pairing with E5's E1-7 records is declined,** to keep the seed rule.

## 16. Sources read

- `CLAUDE.md`; `docs/DECISION_LOG.md` P-24, P-58, P-62, P-63, P-67 (plus P-25, P-26, P-28, P-60 as cited in the
  draft and review).
- ER9: the draft, the review, `DECISIONS_2026-11-21.md`, `G1_GAP_ANALYSIS.md` A10, `er9_turn_diag.py`,
  `er9_catch_diag.py`, `er9_probe.py` (arms, `configure`), and the `results/probe/diag/` listing.
- `D8_alignment/README.md`, `results/diag_m4_2026-11-15/SUMMARY.md` §5, and `d8_1b_stage1.py` (`layer_error`).
- E5: `RESULTS.md` E1-7, `run.py` (seed scheme), the `results/E1-7/*.json` keys tallied, and
  `E4_scored_m4/run.py` `e17_trials`.
- `E1_scored/run.py` (E1-2 seed list).
- ER7: `PROTOCOL.md` (seeds), `er7_run.py` (globals), `SUMMARY.md` (slip seeds).
- `src/rubiknetic/cube_physics/m1_model.py`, `rig.py`, `scored.py` (`draw_setup`, `Trial`), `readout.py`, and
  `magnets.py` (stats).
- `docs/research/TURNING_TORQUE_FINDINGS.md`, `CUBE_MECHANISM_FINDINGS.md` §3, and
  `MUJOCO_CONTACT_CREEP_FINDINGS.md` §2.8.
- `experiments/D11_rest_slip_count/PROTOCOL.md` (house style).

---

# Changes from the draft, mapped to review findings

| Finding | Severity | Change in this protocol |
|---|---|---|
| **T1** no jam rule | blocking | §5 defines a JAM class (J1: unwrapped layer rotation short by more than 20° at the end of the hold; J2: penetration > 0.5 mm; J3: illegal or unreadable state). It is checked before the catch classes, recorded with its own fields, excluded from medians, trends and the worst-point choice, never catch-free, and reported in its own table. §2 item 12 notes that `layer_error` cannot detect a jam. The worst point (§7.2) is the worst *non-jam* no-magnet point, falling back to W3 |
| **T2** torque censored by the clip | blocking | §4: the diagnostic rig R5 (limit 5 N·m, nothing else changed) is the primary measure for Stages 1–3. R1 is repeated at the nominal point (5 seeds) and at every candidate, and Stage 4 is R1 only. The alternatives (unclipped PD command, contact-derived torque, quasi-static ramp) are argued and the first two recorded. The remaining censoring (5 N·m ceiling, pad slip) is flagged. R5's post-catch behaviour is not read. Self-check S4 shows R5 equals R1 before the clip |
| **T3** Stage 4 seeds unspecified | blocking | §6 lists every seed. The E1-7 move strings are reseeded from scored seed 10000 to 16910 and 16911. Rest uses 16000 and 16003, snap-back 16568. Pairing with E5's E1-7 records is declined. S5 enforces the list and refuses 10000–10999 and 17000–17999 |
| **T4** one seed for the grid | should fix | Three seeds for the whole grid; five at the nominal point as the noise yardstick; the trend and effect rules in §11 are fixed in advance |
| **T5** overrides shift seeded draws | should fix | §8.1 "draw first, then replace"; S6 checks the other draws; S7 checks that durations stay fixed in seconds at 0.25 ms (FACT: `rig.py` converts seconds to steps) |
| **T6** no validity rule for magnets | should fix | §8.2: L0 is flagged at tilt > 5°, any perpendicular near pair, or a face gap outside 0.5–1.5 mm. W3 is proxy-flagged by construction and is diagnosis only. Flagged replays cannot be catch-free |
| **T7** Stage 2 overlaps E1-7 | should fix | §7.0 writes E1-7's tallies (verified from the records, including friction rows the draft did not list) and predictions Pr1–Pr7 into the protocol before Stage 1. Stage 2 runs only on the no-magnet cube and W3; L0's one-factor data are cited from E1-7 |
| **T8** gap route's guard-rail outcome predictable | should fix | §7.4 and Pr7 state in advance that a catch-free gap setting is expected to fail or flag drift. 0.25 mm is kept only as a labelled demonstration (§15 item 6) |
| **T9** name collision | should fix | Renamed **D12** throughout (folder `experiments/D12_turn_stall/`). ER10 stays free for the force-law validation. The draft's decision "D12" (radial preload) is renamed in the text to avoid a clash |
| **T10** 0.09 N·m mischaracterised | should fix | §2 item 10: Oskar van Deventer's TwistyPuzzles museum Superclick entry, not a vendor page, cited via `TURNING_TORQUE_FINDINGS.md`. The sub-limit threshold is tied to P-67's 0.2 N·m reference, and the 0.45 N·m warning is flagged |
| **T11** definition set after seeing replays | minor | §5 "Freeze": no threshold or window may change after Stage 1 starts. The post hoc origin is disclosed in §14 |
| **X1** inconsistent regime standards | conflict | §8.2: W3 is reported as proxy-flagged. Part G's per-class tool is added to W3 records when it has been reviewed; D12 does not depend on it. L0 uses M5's own 5° flag |
| **X3** two forks of the replay scripts | conflict | §10 S1: use the shared reviewed tool if it exists; otherwise D12's own registry refuses unknown names (G7) and reproduces 5 committed `turn_*` files and 2 `catch_*` files |
| **X4** seed reuse chain | conflict | §6: the chain is disclosed, and D12 reserves 16900–16999 for its fresh draws |
| **X5** order and records | conflict | Header and §12: approval is P-67 item 5. The protocol and code are committed before any run, and the commit is recorded in the decision log. D12 runs after Part E's probe |
| **X6** clip-raised slot taken without its purpose | conflict | Resolved by T2: R5 is the gap analysis's clip-raised diagnostic (A10), at 5 N·m rather than the example 3 N·m |
| **X7** machine | conflict | §12: one simulation process at a time, never beside Part E, Part G or other jobs. A timing test comes first, with stop rules on projected time, per-replay time and memory |
| X2 | not applicable | Part F/G hybrid overlap; not in this draft |
| Review: decisions with defaults (D2/D3 levels, D5 face gap, D9 seeds, D12 preload, implicit clip choice) | — | Levels and the face gap are kept as approved in P-67. Seeds were changed under T4. Preload stays out of scope. The clip is now an explicit choice (R5; §15 item 1) |
| Other corrections | — | "Suppress" → "attenuate" (§2 item 4). Stage 4 now runs in L0 only, because the no-magnet cube already fails E1-7. Per-replay records add peak RSS, free memory, the unclipped command, contact-derived torque, pad slip and the signature flag. The E1-7 seed (10000) and move strings are now cited to source |
