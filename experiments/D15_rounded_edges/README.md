# D15 — rounded piece edges (P-79)

**Approval.** The user approved this on 2026-11-24 ("fully approved"; DECISION_LOG P-79). The plan is
`../D14_noslip_rest_rehearsal/proposals/ROUNDED_EDGES_PROPOSAL_DRAFT.md`.

| Step | Status |
|---|---|
| R0 | done (below) |
| R1 | done 2026-11-24: both radii meet the screen; **R 2.5 mm selected** (below) |
| R2 | done 2026-11-25 (P-81, P-82): all three arms **meet the rehearsal signals**, no move at the clip; unscored (below) |
| R3 | done 2026-11-25 (P-84, P-85): E1-7 rehearsal of L0; nominal and all 15 rests pass; 4 / 58 sequence fragilities (gap 0.1 mm drift ×2, μ 1.0 jam, 0.75 ms penetration); unscored (below) |
| R4 | done 2026-11-25 (P-86, P-87): M7's Option A on fresh seeds 19000–19655: **204 / 204, both signals met**, 0 slip events, no move at the clip; unscored (below) |

## R0 — implementation and static checks (`FACT`; all checks done 2026-11-24)

**Code.**
- `src/rubiknetic/cube_physics/m1_model.py` adds:
  - `M1Params.edge_profile` (`"chamfer"` default, or `"rounded"`) and `edge_radius`;
  - `_rounded_box_vertices` and `piece_vertices`;
  - `params_record`.
- The record writers in `scored.py`, `scored_m2.py` and `trials.py` use `params_record`. It leaves the edge fields out
  while they hold their defaults, so chamfer records are unchanged.
- The rounded geometry is the one the P-78 diagnostic tested (asserted by a test).

**Checks.**

| Check | Where | Result |
|---|---|---|
| Default (chamfer) model XML is byte-identical to before the change, for three parameter sets | `tests/test_edge_profile.py` (sha256 recorded at `07054f1`) | pass |
| Default record `params` keys are unchanged | same | pass |
| Rounded geometry: 104 vertices, extents = half-size, first facet at 15°, no cubie–cubie contact in the solved pose; bad settings raise | same | pass (13 tests) |
| One committed record per arm reproduces exactly: D14 Stage 2 E1-2 `U_s16100` at NoSlip 10, gates' comparison with the logging blocks stripped on both sides | `r0_repro.py` → `r0_repro.json` | L0, PG8, PG20: 0 differences, no proof errors |
| Composite checks V4 / V5 / V6 on the rounded geometry, NoSlip 10, R 1.4 and 2.5 mm, three arms | `r0_composite.py` → `r0_composite.json` | 6 / 6 pass. V4 rel. net force ≤ 4.1e-17; V5 energy drift 0.07–0.41 % (limit 1 %); V6 pass |
| Magnet fit: every piece magnet cylinder at least the 0.4 mm wall inside the piece solid | `r0_magnet_fit.py` → `r0_magnet_fit.json` | L0 48, PG8 56, PG20 68 piece magnets: all fit for the chamfer, R 1.4 and R 2.5. Minimum depth 0.40 mm in every case (the outer face), so rounding does not reach any magnet. Core magnets not reshaped, not checked. |
| Full test suite (`tests/` and D14's tests, WSL, MuJoCo 4.0.1) | — | all pass after one stale D14 test was updated (below) |

**The stale test.** `test_d14s3.py::test_assemble_counts_before_3b` asserted that every assembled trial passes. It was
written before Stage 3b had records. It failed only on the committed Stage 3b record `PG20 E1-4/scr20inv_s16400`, the
P-76 jam, and not because of R0. It now checks:
- that the Stage 1 + 2 trials (106 per arm) all pass;
- that Stage 3b holds exactly its 26 PG20 E1-4 records, with that one failure.

## R1 — screen (`FACT`; UNSCORED; protocol `PROTOCOL_R1.md`, fixed at `fbbacfa` before any computation)

**Run.**
- 636 / 636 trials, 2026-11-24 14:42–16:29, 6 workers, WSL2, MuJoCo 4.0.1.
- Code at commit `fbbacfa` for every record.
- Records: `results/r1/<R25|R14>/<arm>/<exp>/`. Log: `results/r1/r1_run_log.txt`. Analysis:
  `results/r1/r1_analysis.json` (`r1_analyze.py`).
- One deviation: an earlier start at 13:54 was stopped by the main session before any trial ran. Another project's
  training was using most of WSL's memory, and the runner had fallen to 1 worker. No record was written, and the log
  keeps its start line.
- No abort, numerical failure, harness exception, proof error, rest slip event, out-of-regime trial, or move at the
  1 N·m clip.

**Screen (PROTOCOL_R1 §2).** Every arm at both radii is complete (20 rests + 86 trials), with 0 rest failures, 0 trial
failures and 0 E1-2 moves at the clip.

| Radius | L0 | PG8 | PG20 | Meets the screen |
|---|---|---|---|---|
| R 2.5 mm (R25) | pass | pass | pass | **yes** |
| R 1.4 mm (R14) | pass | pass | pass | yes |

**Selection (P-79's rule): R 2.5 mm.**

**Reported only.** Chamfer values are D14 Stage 2, the same trials at NoSlip 10.

| | L0 | PG8 | PG20 |
|---|---|---|---|
| E1-2 turner median / max (N·m), R25 | 0.099 / 0.108 | 0.191 / 0.200 | 0.271 / 0.306 |
| R14 | 0.103 / 0.152 | 0.204 / 0.262 | 0.280 / 0.364 |
| chamfer | 0.193 / 0.596 | 0.424 / 0.678 | 0.328 / 0.967 |
| Largest 0–10 s rest rotation, R25 / R14 | 0.0051° / 0.0034° | 0.0040° / 0.0063° | 0.0114° / 0.0069° |
| Largest non-target drift, R25 / R14 | 0.64° / 0.55° | 0.51° / 0.50° | 0.54° / 0.42° |
| E1-5 completed / blocked, R25 | 26 / 16 | 41 / 1 | 41 / 1 |
| R14 | 26 / 15 (+1 no net move) | 37 / 5 | 37 / 5 |
| chamfer | 29 / 12 (+1 no net move) | 37 / 5 | 37 / 5 |
| Largest solver iteration count, R25 / R14 | 32 / 33 | 33 / 35 | 35 / 35 |

**Against the predictions written before the run.**
- "Both radii meet the screen": met.
- "E1-2 peaks fall to about the magnets' resistance plus the rig, about 0.3 N·m PG20, 0.2 L0":
  - PG20: met (0.31).
  - L0: lower than predicted (0.11).
- "E1-5 completes more of the large-misalignment starts":
  - PG8 and PG20 at R25: met (41 against 37).
  - PG8 and PG20 at R14: unchanged from the chamfer.
  - **L0 at both radii: missed.** L0 blocks slightly more (16 / 15 against 12). Blocking is an allowed outcome; this
    is not explained by these runs.
- "Rest rotation far inside 0.5°": met.

**Reading (`INFERENCE`).**
- With rounded edges, no turn in the screen comes near the clip.
- PG20's worst E1-2 turn is a third of the chamfer's, and rest holding is unaffected.
- **Turning effort is now low.** L0's median (0.10 N·m) is about half P-67's realism reference (about 0.2 N·m).
  PG8's median (0.19) is at it, and PG20's (0.27) is between the reference and the warning level. The catch was
  artificial, but the model also has no tension-spring friction. Whether the remaining turn resistance is realistic
  is an open question to settle before any scored run.

**Not covered by R1.** E1-3, E1-4 (the long sequences, where the chamfer jam happened), E1-6, E1-7, 60 s rests, and
fresh seeds. These are the R2 / Stage 3c questions. R2 needs the user's approval.

## Turning-torque realism (desk check, P-81 item 4; 2026-11-24)

**No new web search was needed.** The question is covered by `docs/research/TURNING_TORQUE_FINDINGS.md`
(2026-11-21), the basis of P-67's realism reference, which is three days old.

**What the evidence is, from that report (`FACT` / `UNVERIFIED` as labelled there).**
- The only verified figure for a standard 3x3 is **0.09 N·m** (TwistyPuzzles museum, method not stated).
- A snippet-only bench report implies about **0.10–0.20 N·m** breakaway.
- Speedcube figures of 0.02–0.05 N·m are unverified.
- No source quantifies the magnets' effect or separates breakaway from running torque.
- The report's reading: about 0.14 N·m realistic, 0.4 N·m high, 1.0 N·m far too high.
- **P-67's 0.2 N·m is a reference level chosen by the user, not a measurement.**

**Reading (`INFERENCE`).**
- The R1 medians at R 2.5 mm (L0 0.10, PG8 0.19, PG20 0.27 N·m) lie in or near the plausibly realistic range. The
  chamfer's peaks of up to 0.97 N·m did not.
- §R1's earlier note, that L0's torque is "about half the realism reference", is literally true. But it should not be
  read as "too low": L0's median is next to the only verified real figure.
- Whether the model needs tension-spring friction cannot be settled from published data. No such data exists, so no
  model change is proposed.
- The only route is open item **O-09**: a real-cube bench measurement (`docs/research/REAL_CUBE_MEASUREMENT_GUIDE.md`,
  `experiments/R1_real_cube_bench/PROTOCOL.md`; about 30–45 min with a luggage scale). It needs the user and the cube
  the robot will use.

## R2 — full rehearsal at R 2.5 mm (`FACT`; UNSCORED; protocol `PROTOCOL_R2.md`, fixed at `8ed47ed` before any computation)

**Run.**
- 357 / 357 trials: 3 gate trials and 354 main trials (L0, PG8, PG20; NoSlip 10; gap 0.05 mm; 6 workers).
- The run was done in WSL (Ubuntu 24.04, `~/.venvs/rubiknetic`: Python 3.12.3, MuJoCo 4.0.1, numpy 2.5.4, scipy
  1.18.1), as every record's environment block states.
- It was paused three times at the user's request (laptop sleep) and resumed with `--resume`. Trials in flight at a
  pause were discarded, never partly written, and rerun.
  - Session 1: 16:39–17:54 at `8ed47ed`.
  - Sessions 2–4: 17:59–18:46, 19:22–19:48 and 20:54 to 01:33 on 2026-11-25, at `2a919c2`. The commit changed
    only this README.
- The gate (E1-2 `U_s16100` equal to R1's record) passed with 0 differences at every start.
- 0 FAIL lines, 0 aborts, 0 proof errors, 0 pauses for trouble.
- Records: `results/r2/R25/<arm>/<experiment>/`. Log: `results/r2/r2_run_log.txt`. Analysis:
  `results/r2/r2_analysis.json`.

**Deviation: the analysis read was fixed after computation (P-82).**
- The runner files records by experiment: E1-6a, E1-6b and E1-6c all go under `E1-6/`, as in D14 Stage 3b.
- The first `r2_analyze.py` globbed `<sub_experiment>/`, so it missed those 20 records per arm. It reported 184 of
  204 trials and Option A as unmet.
- The fix reads `*/*.json.gz` and filters on `sub_experiment`, as `d14s3_analyze.py` does. It asserts no duplicate
  trial key, and a test covers the layout.
- Nothing else changed: records, signals, thresholds and reading are untouched.
- The first output is kept as `results/r2/r2_analysis_before_P82_fix.json`.

**Signals (G.9, over 204 trials per arm: 20 R2 rests + 86 reused R1 R 2.5 records + 98 R2 trials).**

| | L0 | PG8 | PG20 |
|---|---|---|---|
| Trials passed (every ER7 row complete) | 204 / 204 | 204 / 204 | 204 / 204 |
| 1: 60 s rests, 0 slip events, ≤ 0.5° (largest 0–10 s rest) | met (0.0051°) | met (0.0040°) | met (0.0114°) |
| 2: Option A, incl. E1-6m ⟨P⟩ on 1376 / 1376 moves | met | met | met |
| 3: no operational trial out of regime | n/a (legacy) | met | met |
| E1-2/3/4 turner median / max (N·m) | 0.103 / 0.185 | 0.196 / 0.234 | 0.275 / 0.315 |
| Moves at the 1 N·m clip | 0 | 0 | 0 |
| Largest non-target drift | 0.73° | 0.57° | 0.74° |
| Largest solver iteration count; steps at the limit | 36; 0 | 35; 0 | 35; 0 |
| Abuse trials labelled out of regime (not failures, G.4 rule 3) | n/a | E1-6t: 8 twist trials | E1-6t: 8 twist trials |

**Reading (G.9, fixed).** All three arms **meet the rehearsal signals, with no move at the clip. This is not a
candidate.** M5 stays NOT PASSED, and nothing is selected for G1.

**Against the chamfer (reported only).**
- L0 has 98 comparisons with ER7's frozen records. PG20 has 26 with D14 Stage 3b's E1-4 records. PG8 has no chamfer
  record for these trials.
- Two trials that failed with the chamfer pass with rounded edges: L0 E1-4 `scr20inv_s16405` and PG20 E1-4
  `scr20inv_s16400`. The second is the Stage 3b jam.
- No trial passes with the chamfer and fails with rounded edges.

**Predictions written before the run (`PROTOCOL_R2.md` §2).**
- Gate passes: held.
- All three arms meet the signals with no move at the clip: held.
- PG20 `scr20inv_s16400` passes: held.
- Largest E1-3 / E1-4 turner torque below 0.5 N·m: held, at 0.315 N·m (PG20).
- "If something fails, most likely E1-6 or a 60 s rest slip": nothing failed.

**Still lacking (`PROTOCOL_R2.md` §2 reading; user decision).**
- Fresh seeds (Stage 3c): R2 used the rehearsal seeds, which informed every earlier choice.
- Turning torque against a real-cube measurement (O-09).
- E1-7.
- The composite review.
- The lateral-offset disclosure.
- The physical credibility of the rounded edge.
- Rounded edges and NoSlip 10 are post-hoc settings chosen after earlier failures.

## R3 — E1-7 sensitivity rehearsal of L0 at R 2.5 mm (`FACT`; UNSCORED; protocol `PROTOCOL_R3.md`, fixed at `741a36f` before any computation)

**Run.**
- 2026-11-25, 11:03–11:49, one start, 6 workers. WSL was free of other jobs: the user paused another project for
  the run.
- 73 / 73 trials: 58 sequence trials on seed 16000 and 15 rests of 60 s. 2 were "not run" by M5's V3 rule
  (4×1.5 N35), as in M5.
- 0 proof errors, 0 harness exceptions, 0 pauses.
- **Gate 1** (R3's ER7 path against R1's ER9-path E1-2 `U_s16100`): 0 differences.
- **Gate 2** (nominal 60 s rest against R2's `rest_s16000`): 0 differences.
- Records: `results/r3/`. Analysis: `results/r3/r3_analysis.json`.

**Signals.**
- **Complete.**
- **A met:** nominal passes 6-move and sexy6 (turner max 0.16 / 0.12 N·m, drift 0.46° / 0.56°), and the nominal rest
  is ok.
- **B not met:** 4 of the 58 sequence trials flip against nominal. **Reading: "fragilities reported: the user
  decides".**
- **Rests: 15 / 15 ok, no flips.** Every rest had 0 slip events over 60 s. The largest 0–10 s rest rotation is
  0.011° (gap 0.1 mm); the limit is 0.5°.

**Fragilities (the four flips).**

| Setting | Sequence | What failed | Detail |
|---|---|---|---|
| piece gap 0.1 mm (2× nominal) | 6-move | non-target drift | 1.005° against ≤ 1.0° on move 5 (F). Turn error 0.07°; final state correct |
| piece gap 0.1 mm | sexy6 | non-target drift | 1.019° (move 1, R) and 1.095° (move 8, U′). Turn errors ≤ 0.16°; final state correct |
| cubie friction μ 1.0 | sexy6 | **jam** | Move 7 (R′) stalled at the 1 N·m clip, 60° short. Penetration 0.64 mm; oracle check failed. The 6-move at μ 1.0 passed (max 0.17 N·m) |
| timestep 0.75 ms | 6-move | penetration | 0.504 mm against ≤ 0.5 mm on move 2 (U′). Turn error 0.22°; final state correct |

**Everything else passed both sequences:**
- timestep 0.25 ms;
- iterations 50 / 200;
- μ 0.1 / 0.5 (μ 0.5 max torque 0.37 N·m);
- joint frictionloss ±10×;
- edge radius 1.8 / 3.6 mm;
- piece gap 0.025 mm;
- face gap 0.35 / 1.35 mm;
- grip 10 / 30 / 50 N;
- misalignment 0 / 2 / 5°;
- magnets none / 3×1.5 N35 / 4×2 N52, and magnet scale 0.67;
- NoSlip 5 / 20.

The NoSlip 0 reference (outside the band) also passed both.

**Largest values among the 54 passing trials:** turner torque 0.37 N·m, drift 0.85°, penetration 0.499 mm. There was
1 move at the clip over the whole run: the μ 1.0 jam.

**Against M5's E1-7 (same factors and seed mapping; chamfer and default NoSlip; reported only).**
- M5 failed and R3 passes:
  - "no magnets" 6-move;
  - timestep 0.75 ms sexy6.
- M5 passed and R3 fails:
  - gap 0.1 mm (both sequences);
  - μ 1.0 sexy6.
- M5's chamfer-1.0 mm fragility has no counterpart: the edge-radius settings that replace it both pass.

**Predictions (`PROTOCOL_R3.md` §3).**
- Gates pass: held.
- Nominal passes: held.
- Timestep 0.75 ms fails at least one sequence: held (6-move, by 0.004 mm).
- Edge radius 1.8 mm passes: held.
- "No magnets" fails at least one sequence: **did not hold** (both pass).
- μ 1.0 passes: **did not hold** (sexy6 jams).
- "If a rest flips, most likely 0.75 ms or NoSlip 5": no rest flipped.

**Reading (`INFERENCE`).**
- **Robust:** the mechanism holds across solver settings, NoSlip 5–20, edge radius 1.8–3.6 mm, grip, misalignment,
  magnet type and strength, face gap and moderate friction. Rest holding is insensitive to every rest factor
  tested.
- **Two of the four flips are marginal threshold crossings with correct turns.** The gap 0.1 mm drift is 1.005–1.095°
  against 1.0°, and the 0.75 ms penetration is 0.504 against 0.5 mm. Both sit on the M1 limits rather than showing a
  mechanism failure.
- The 0.75 ms one is a step-size limit, as in M5: the model needs ≤ 0.5 ms.
- **The gap 0.1 mm drift is the most consequential.**
  - Real cube clearances are unverified (P-77). The claim may need to be bounded to piece gaps up to about 0.05 mm,
    or the drift's cause understood.
  - With the chamfer, M5 passed at 0.1 mm. Nominal L0 drift at 0.05 mm is 0.46–0.56°, so doubling the gap roughly
    doubles the drift.
- **The μ 1.0 jam is a real jam, but at an extreme friction value** for lubricated ABS. μ 0.5 passes with 0.37 N·m
  peak torque.
- E1-7 is reported, not pass/fail, for G1 (M5 pre-registration §5). These fragilities are disclosed limits unless
  the user chooses to investigate.

## R4 — fresh-seed rehearsal of M7's Option A battery (`FACT`; UNSCORED; protocol `PROTOCOL_R4.md`, fixed at `b6df25c` before any computation)

**Run.**
- 2026-11-25, 15:11–16:49, one start, 6 workers.
- **Deviation, approved by the user before any computation:** another project's job ran in WSL ("can we go ahead
  even with polypanda running?"), against §1's "WSL free of other jobs". It affects wall time only. It is logged at
  the head of `results/r4/r4_run_log.txt`.
- **Gate:** the first trial of all 10 sub-experiments, at rehearsal seeds, reproduces R1/R2's committed L0 R25 records
  with **0 differences each**.
- 204 / 204 trials on seeds 19000–19655 (M5's scored seeds + 9000), never simulated before. E1-4's scrambles were
  drawn from them.
- 0 proof errors, 0 harness exceptions, 0 trouble records.

**Signals (both met; reading: "meets the rehearsal signals on fresh seeds (not a candidate)").**

| Sub-exp. | E1-1 | E1-2 | E1-3 | E1-4 | E1-5 | E1-5s | E1-6a | E1-6b | E1-6c | E1-6t |
|---|---|---|---|---|---|---|---|---|---|---|
| passed | 20 / 20 | 24 / 24 | 22 / 22 | 40 / 40 | 42 / 42 | 20 / 20 | 6 / 6 | 6 / 6 | 8 / 8 | 16 / 16 |

- **Signal 1:** all 20 rests ran 60 s with **0 D11 slip events**. The largest 0–10 s rotation was 0.0055°.
- **Signal 2:** Option A with the slip rule. E1-6m ⟨P⟩ holds on 1376 / 1376 moves.
- **Turner torque** (E1-2 to E1-4): median 0.103, p99 0.170, max 0.193 N·m. 0 moves above 0.45 N·m, 0 at the clip.

**Margins: fresh seeds against the rehearsal (R1 + R2 L0, same 204-trial list on 16000–16655).**

| Quantity | R4 (fresh) | Rehearsal | Limit |
|---|---|---|---|
| largest 0–10 s rest rotation | 0.0055° | 0.0051° | 0.5° |
| largest non-target drift | **0.781°** | 0.728° | 1.0° |
| largest penetration | 0.292 mm | 0.293 mm | 0.5 mm |
| largest \|turn error\| | 0.385° | 0.368° | 2.0° |
| turner torque max | 0.193 N·m | 0.185 N·m | clip 1.0 |

**Predictions (`PROTOCOL_R4.md` §2).**
- Gate passes: held.
- Both signals met, with no move at the clip: held.
- Drift and penetration below the limits, possibly above the rehearsal maxima: held. Drift rose to 0.781°;
  penetration did not rise.
- "If a trial fails, most likely drift": no trial failed. Drift is still the closest margin.

**Reading (`INFERENCE`).**
- On seeds that informed no choice, M7 behaves as rehearsed. Every quantity except drift is within a few per cent of
  its rehearsal maximum.
- Drift's tail grew by 0.05°, leaving 0.22° (22 %) of margin. It stays the most likely route to a scored failure.
- Rest holding is about 100× inside its limit, with no slip events in 20 fresh 60 s rests.
- This is evidence about the tails, not M7's verdict. Per `PROTOCOL_R4.md` §4, it informs the M7 disclosure and stop
  rules only.
