# D15 — rounded piece edges (P-79)

**Approval.** The user approved this on 2026-11-24 ("fully approved"; DECISION_LOG P-79). The plan is
`../D14_noslip_rest_rehearsal/proposals/ROUNDED_EDGES_PROPOSAL_DRAFT.md`.

| Step | Status |
|---|---|
| R0 | done (below) |
| R1 | done 2026-11-24: both radii meet the screen; **R 2.5 mm selected** (below) |
| R2 | needs a separate approval |

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
