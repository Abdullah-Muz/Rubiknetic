# ER9 — anchored core-magnet layouts: summary

**Status:** exploratory and unscored. Every trial used ER7's rehearsal seeds (16000–16999). Nothing here is a
VALIDATED_RESULT for gate G1, and no scored seed (17000–17999) was touched. Protocol: `PROTOCOL.md` (Parts A–E and G, each
part and amendment committed before its runs). Parts A–D are complete; Part E's probe is complete (`6e722e1`); Part G's probe is complete (`b0698ba`). The decision-log row
for ER9 will be proposed once Part E's probe is reported (P-67 item 6); a draft is in
`proposals/ER9_RECORD_DRAFT.md`.

## Outcome in brief
- **The problem.** No cube mechanism passes G1. M5's 48 corner–edge magnets (L0) fail on small slips at rest. The
  single core pairs of ER7 (C52) hold at rest but do not snap a displaced layer back.
- **Why C52 failed (FACT, ER7 post hoc and Part A's self-check S2).** One magnet pair on a piece's own axis gives no
  stiffness against that piece spinning about the axis. All 26 pieces can spin together with no contact and no
  restoring torque (26 zero modes in the stiffness matrix).
- **The idea tested here.** Hold each edge with two pairs and each corner with three, set off the piece's axis, each
  pair pointing radially. That anchors every piece in all three rotations.
- **Result 1 (Parts A–D).** The anchored layout removes both known failures. Arm W3 (N35 at strength 0.3) passed
  **204 of 204** rehearsal trials and met all three of ER7's signals; L0 passed 201 and C52 194 on the same seeds.
- **The catch.** With W3 the turner reached its 1 N·m limit in 771 of 1,376 moves (L0: 0). The layer stalls briefly at
  about 7° into a turn, then breaks through.
- **Result 2 (diagnostics after Part D; they motivated Part E).** The stall is not caused by the anchors: it is there, and worse, with almost no
  magnets. INFERENCE from single-turn replays: M5's corner–edge magnets attenuate it to a sub-limit peak (L0: 0.461 N·m; pieces lag at most 0.21°).
  Part E therefore tests both together.
- **Part E probe (complete, 318 / 318).** HB1 and HB3 meet probe signals 1–3 and HB2 misses signal 2 (one rest at
  0.516° > 0.5°); no arm can meet signal 4 (known before the probe). The hybrids' E1-2 turner medians, 0.37–0.46 N·m,
  are 2.6–3.2× L0's 0.144 N·m on the same seeds. Whether the selected arm (HB3) gets the full rehearsal is the
  user's decision (P-67 item 7, U7).
- **Part G probe (complete, 212 / 212).** PG8 and PG20 (M5's 48 magnets plus 8 or 20 core pairs) meet probe signals
  1, 3 and 4 and miss signal 2 through fast slip events on 3 / 20 and 1 / 20 seeds (L0: 2 / 20); no arm is selected
  (P-72). D13 links the slips largely to the simulator's friction model (INFERENCE there); D14 follows (P-73).

## Part A — static screen (243 layouts)
- Layouts: edges on their axis or split into 2 pairs at 14–20° toward the centres or the corners; corners on their
  axis or split into 3 pairs at 10–16° toward the edges or the centres; grades N35, N42, N52; 4 × 3 mm magnets at
  0.2 mm clearance.
- Criteria fixed beforehand: spin and twist stiffness ≥ 100 mN·m/rad; smallest non-centre eigenvalue of the full
  66 × 66 stiffness matrix ≥ 50; magnetic U-turn peak ≤ 0.5 N·m; layer stiffness ≥ 1 N·m/rad; magnets of different
  pieces ≥ 8 mm apart; near-pair tilt ≤ 20°.
- Self-checks passed: S1 reproduces ER6's numbers exactly; S2 finds C52's 26 zero modes and a collective twist
  stiffness of about 0; S3 passes.
- **3 of 243 pass.** Selected (lowest U-turn peak): N42, edges 2 pairs at 20° toward the centres, corners 3 pairs at
  16° toward the centres, 96 magnets.

| Quantity (selected layout) | Value |
|---|---|
| Edge: spin / slide / cross stiffness | +106 / +803 / +884 mN·m/rad |
| Corner: twist / tangential stiffness | +100 / +1,277 mN·m/rad |
| Layer stiffness | 5.27 N·m/rad |
| Magnetic U-turn peak | 0.338 N·m |
| Zero modes | 6 (the centres, which carry no magnets) |
| Smallest other eigenvalue; collective twist | 99; 4,881 mN·m/rad |
| Closest magnets of different pieces; clearance | 10.36 mm; 0.82 mm |
| Largest near-pair tilt | 18.2° |

## Parts B and C — 106-trial probes (E1-1, E1-2, E1-5, E1-5s)
Wrapper self-check: ER7's C52 records reproduced exactly (after deviation 1, a bookkeeping field).

| Arm | Layout | Trials passed | Snap-back max error | Rest max | E1-2 turner median | Moves at the 1 N·m limit (of 24) |
|---|---|---|---|---|---|---|
| L0 (ER7) | M5's 48 magnets | 104 (E1-1 18/20) | 0.27° | 0.568° | 0.144 N·m | 0 |
| C52 (ER7) | single core pairs, N52 | 96 (E1-5s 10/20) | 1.01° | 3.4e-6° | 0.70 | 4 |
| S1 | anchored, N42 | 106 | < 0.001° | 1.1e-6° | 1.0 | 20 |
| S2 | anchored, N52 | 106 | < 0.001° | 7.6e-12° | 1.0 | 20 |
| W1 | anchored, N35 × 1.0 | 106 | < 0.001° | 1.5e-5° | 1.0 | 20 |
| W2 | anchored, N35 × 0.5 | 106 | < 0.001° | 0.0027° | 1.0 | 16 |
| W3 | anchored, N35 × 0.3 | 106 | 0.028° | 0.011° | 0.947 | 9 |

- "Snap-back max error" in this table is over all 20 snap-back trials, including the unscored ±1° and ±2° starts;
  the Part D table below uses only the scored starts (|Δ| ≥ 3°). L0 is 0.269° by the first definition and 0.118° by
  the second; C52 (1.013°) and W3 (0.028°) are the same under both.
- All five anchored arms met the four probe signals. None was flagged (largest near tilt 18.42°, no perpendicular
  near pair). The runner checks signal 4 through ER7's regime flag only; its other clause, "no piece-to-piece near
  pair", holds for these arms by geometry (magnets of different pieces stay ≥ 10.36 mm apart in every face turn).
- By the selection rule fixed beforehand (lowest median E1-2 turner torque), W3 went to the full rehearsal.

## Part D — full 204-trial rehearsal of W3

| Experiment | L0 | C52 | W3 |
|---|---|---|---|
| E1-1 rest | 18 / 20 | 20 / 20 | 20 / 20 |
| E1-2 single moves | 24 / 24 | 24 / 24 | 24 / 24 |
| E1-3 half turns | 22 / 22 | 22 / 22 | 22 / 22 |
| E1-4 long sequences | 39 / 40 | 40 / 40 | 40 / 40 |
| E1-5 misaligned starts | 42 / 42 | 42 / 42 | 42 / 42 |
| E1-5s snap-back | 20 / 20 | 10 / 20 | 20 / 20 |
| E1-6a / b / c / t abuse | 6, 6, 8, 16 | 6, 6, 8, 16 | 6, 6, 8, 16 (all passed) |
| **Total** | **201 / 204** | **194 / 204** | **204 / 204** |
| E1-6m moves oracle-correct | 1,376 / 1,376 | 1,376 / 1,376 | 1,376 / 1,376 |

| Signal (ER7's three) | L0 | C52 | W3 |
|---|---|---|---|
| 1. No slip seed in E1-1 and rest ≤ 0.5° | no (2 seeds, 0.568°) | yes (3.4e-6°) | **yes** (0 seeds, 0.011°) |
| 2. M5's Option A rule over 204 trials | no | no | **yes** |
| 3. No trial outside the validated regime | — | yes | **yes** (max tilt 18.42°) |

| Reported | L0 | C52 | W3 |
|---|---|---|---|
| Turner torque: median / 99th percentile / max (N·m) | 0.203 / 0.563 / 0.870 | 0.645 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 |
| Moves at the 1 N·m limit | 0 | 69 (37 trials) | **771 (68 trials)** |
| Non-target drift per move: median / max | 0.231° / 0.776° | 0.191° / 0.831° | 0.045° / 0.119° |
| Snap-back max error | 0.118° | 1.013° | 0.028° |
| Summed trial wall time | 10.5 h | 9.5 h | 22.8 h |

- The 106 probe trials were reproduced inside the full run (same pass flags, same rest and snap-back values).
- Paired with L0 on the same seeds, W3 has lower rest rotation in 20 of 20 trials and lower sequence drift in 85 of
  86, and higher peak turner torque in 86 of 86.

**Reading (as fixed in Part D).** All three signals are met, so the anchored layout is a candidate for a scored
pre-registration, with what it still lacks listed under Limits. The turner saturation is the reason I did not stop
there.

**Superseded (2026-11-22; the paragraph above is kept as fixed in Part D).** W3 is no longer a candidate: it does
not fit the real-mechanism CAD (Limits, fit), signal 3 is a 20° proxy rather than a validation (Limits, "What signal
3 shows"), and P-67 item 1 does not take W3 forward.

## Part E — hybrid: M5's 48 positions plus weak anchors (probe complete; full rehearsal not run)
- **Arms.** HB1, HB2, HB3: M5's 48 corner–edge positions plus the 96 anchor magnets (144 in all), anchors at 1, 2 and
  3 mm clearance. One magnet type throughout: 4 × 3 mm N35 at strength 0.756, which matches the pull of M5's 4 × 2 mm
  pair (amendment 1; the 4 × 3 table, which is validated to 7.5° for a generic tilted pair (V3b) and to 20° only on ER5's
  on-axis face-turn paths at c = 0.2 mm; corrected 2026-11-22, see Limits).
- **Validity limit (added 2026-11-22).** The anchors are off-axis at c = 1–3 mm; P-60 accepts c = 0.2 mm on ER5's
  on-axis paths only, so it does not cover them.
- **Self-check:** passed (W3's probe records reproduced with 0 differences).
- **Smoke replays (seed 16100, first U of an E1-2 trial), before any probe trial:** peak turner torque 0.525, 0.432
  and 0.118 N·m at 1, 2 and 3 mm, no step at the 1 N·m limit (L0: 0.461; W3: 1.0 with 4.3 % of steps at the limit).
- **Known before the probe (amendment 2).** No hybrid arm can meet the validity signal. Anchor magnets of the turning
  layer pass corner–edge magnets of the layer below at 5.8–6.2 mm and about 64°, and the force law corrects near pairs
  only within 45° of parallel. For those 12 pairs the dipole formula the simulation uses is within 3.5 % of the charge
  model in torque about the turn axis (0.39 mN·m of 11.3 mN·m). That is a measured size of the error, not a
  validation. Accepting it would be an amendment of the kind P-60 was, which is the user's decision.
- **Probe run.** 318 / 318 trials, finished 2026-11-22 (`6e722e1`, `results/hybrid/probe/report.json`). The run was
  stopped three times by low-memory stops (at 75, 223 and 275 trials) and once paused at the user's request (296);
  the runner skips existing records, so each restart continued where it stopped. All 318 records decompress. Worker
  count changed between restarts (12, 14, 4, 6); each trial runs in its own process, so it does not enter a result.
- **Probe signals (FACT, from the report; signals as in Part B, eligibility as in amendment 2).**

  | Arm | Passed (of 106) | 1 snap-back | 2 rest ≤ 0.5° | 3 E1-2 and E1-5 | 4 regime | Max near tilt | Eligible |
  |---|---|---|---|---|---|---|---|
  | HB1 (1 mm) | 106 | met | met (0.169°) | met | not met | 17.4° | yes |
  | HB2 (2 mm) | 105 (E1-1 19 / 20) | met | **missed (0.516°)** | met | not met | 15.5° | no |
  | HB3 (3 mm) | 106 | met | met (0.463°) | met | not met | 12.4° | yes |

  Flagged trials (a near pair over the tilt limit or a perpendicular near pair): HB1 70, HB2 73, HB3 74 of 106.
- **Beside the Parts B–D arms on the same 106 seeds (FACT).**

  | Arm | Rest max | Snap-back max error | E1-2 turner median / max | Moves at the 1 N·m limit (of 24) | Summed trial wall time |
  |---|---|---|---|---|---|
  | L0 | 0.568° | 0.269° | 0.144 / 0.461 N·m | 0 | 2.5 h |
  | C52 | 3.4e-6° | 1.01° | 0.700 / 1.0 N·m | 4 | 2.1 h |
  | W3 | 0.011° | 0.028° | 0.947 / 1.0 N·m | 9 | 3.0 h |
  | HB1 | 0.169° | 0.080° | 0.461 / 0.901 N·m | 0 | 26.2 h |
  | HB2 | 0.516° | 0.185° | 0.370 / 0.611 N·m | 0 | 27.1 h |
  | HB3 | 0.463° | 0.191° | 0.388 / 0.989 N·m | 0 | 27.5 h |

  The hybrids' wall times were measured with other jobs on the machine and are not comparable with the others'.
- **Selection rule (amendment 2), applied as reporting only.** Eligible: HB1 and HB3. Lowest median E1-2 turner torque:
  **HB3** (0.388 N·m). It is the arm a full rehearsal would use.
- **Reading (as fixed by amendment 2; no more).** HB1 and HB3 meet probe signals 1–3 on these 106 rehearsal trials;
  HB2 misses signal 2 by 0.016°. No hybrid arm can be named a candidate for a scored pre-registration (signal 4).
  Against P-67 item 4's realism reference (about 0.2 N·m) and warning level (0.45–0.5 N·m): the hybrid medians are
  above the reference, and HB1's median is at the warning level; HB3's maximum, 0.989 N·m, is just under the clip.
  INFERENCE: the anchors buy rest stiffness (rest max 0.17–0.52° against L0's 0.57°) at 2.6–3.2× L0's median turner
  torque, and the hybrid does not fit the real CAD (the anchors are W3's geometry).
- **Full rehearsal: not run.** P-67 item 7 runs it only if the hybrid stays in contention; Part G's decision U7
  recommends probe-only, recorded by amendment 3 (draft in `proposals/ER9_RECORD_DRAFT.md`). Awaiting the user.

## Part G — commercial pattern: M5's 48 corner–edge magnets plus attracting on-axis core pairs (probe complete; no arm selected; full rehearsal not run)
- **Status.** Exploratory and unscored (PROTOCOL.md Part G, fixed 2026-11-22 before any Part G computation; decisions
  U1–U8 by P-69; pre-commitments by P-70; cost decision by P-71; probe recorded by P-72). Seeds only from ER7's
  rehearsal range 16000–16999. The U5 rest-only block 16700–16739 is reserved but was **not run** (deferred, P-71,
  P-72). Seeds 17000–17999 were not used. Part G changes no record and selects no mechanism. M5 stays NOT PASSED, and
  no mechanism has passed gate G1. Nothing here is a VALIDATED_RESULT.
- **Question (fixed, G.1).** On ER7's paired rehearsal seeds, does adding **attracting** on-axis core pairs (4×3 mm,
  c = 0.2 mm; 8 corner pairs or all 20) to M5's own 48 corner–edge magnets: (a) remove L0's rest slips (0/20 D11
  slip events and every rest rotation ≤ 0.5°); (b) keep snap-back within 0.5°, which C52 alone failed; and (c) keep
  every other probe and rehearsal trial passing, while every magnet pair stays inside the validated regime of its
  class (G.4)? Turner torque is reported against the realism reference (about 0.2 N·m; warning level about
  0.45–0.5 N·m) and is not part of the question.
- **Why (FACT, G.1).** L0 fails at rest in rehearsal (2 of 20 slip seeds: 16003 at 0.568°, 16005 at 0.559°; median
  turner torque 0.203 N·m, 0 moves at the clip). C52 holds at rest (3.4e-6°) but fails snap-back in 10 of 20 trials
  (26 zero modes). Under magnet type (b), PG20 is exactly L0 ∪ C52 at N52.

| Arm | Magnets | Composition (G.3) |
|---|---|---|
| **PG8** | 64 | L0's 48 (4 × 2 mm N35) + the 16 corner entries of `core_layout()` (8 corner pairs, 4 × 3 mm N52, c = 0.2 mm) |
| **PG20** | 88 | L0's 48 + all 40 entries of `core_layout()` = L0 ∪ C52 at N52 |
| *PG20r* | 88 | as PG20, edge piece moments reversed; static P2 row only (U4: no dynamics) |

- Controls: L0 and C52 (ER7's records on the same seeds; GS1 and GS2 reproduce them through the composite system).
- Fit (U1, F-A): L0's and C52's exact positions are kept; the two known misses (corner wall 0.175 mm; core cover
  0.202 / 0.292 mm, against the simulation's 0.4 mm default) are reported, not a stop.
- Off-path pairs (U2): D_val from P4.d per arm; PC pairs within D_val judged at 20° with clamped z allowed, beyond it
  at 7.5° with no clamped z. Cross-type (X) pairs: no near evaluation allowed (`cross_near` = 0).

### Self-checks and static pre-checks (G.0, G.5, G.6; FACT, committed files named per table)
All gates passed for both arms; no arm was stopped by P1–P4.

| Check | Result | Source |
|---|---|---|
| Composite V4 (momentum), V5 (energy), V6 (pose-only), run late per deviation 3 | pass for PG8 and PG20. V4 net force and torque ≤ 3.0e-17 relative; V5 (RK4, 0.5 s) drift 0.23 % (PG8) and 0.41 % (PG20) of the energy exchanged; V6 exact | `results/hybrid_g/static/composite_checks.json` |
| GS1 (L0 through the composite, first trial of each of the 10 sub-experiments) | pass, 0 differences in 10 / 10 | `results/hybrid_g/selfcheck.json` |
| GS2 (C52 likewise) | pass, 0 differences in 10 / 10 | same |
| GS4 (stats diagnostic changes no physics field; PG20, E1-2 `B_s16120`) | pass, 0 differences | same |
| GS3 (layout lists), GS3b (composite = 4×2 + 4×3 + cross dipole, 20 poses) | pass; GS3b largest relative difference about 1e-16 | `results/hybrid_g/selfcheck_static.json` |
| GS6 (polarity oddness; path deviation d in rigid turns) | pass; polarity relative difference 0.0; largest d 1.4e-14° | same |
| GS5 (read per Part G deviation 1) | 40-only pass (S1 relative difference 3.8e-13; S2 26 zero modes, collective twist 2.7e-5 mN·m/rad); 48-only with ER3's magnet order pass (2.2e-17); probe 5 pass; `layout()`-order ER3 row **not met** (0.0053; reported, not required). The file's own top-level `pass` is `false` because of this last item; the runner's gate reads it per deviation 1 | same |
| Replay tool (G.7) | pass: turn L0 and C52 at seed 16100 and both snap replays reproduce the committed files with 0 differences | `results/hybrid_g/replay_selfcheck.json` |

- The dynamic self-checks were rerun after PROTOCOL.md changed in `85a0164` (deviation 3); they passed again, and the
  earlier files are kept under `results/hybrid_g/superseded/` (`20cdcfe`).

**P1, kinematic scan (rigid face turns ±90°, 0.5° steps)** — FACT — `results/hybrid_g/static/P1_PG8.json`,
`P1_PG20.json` (`stops`, `stopped`, `e15_like.combined.stats`).

| Stop rule | PG8 | PG20 |
|---|---|---|
| S1 perpendicular near pair (any class) | 0 (limit 0) | 0 (limit 0) |
| S2a CE tilt > 5° | 1.5e-06° | 1.5e-06° |
| S2b CE pair clamped | 0 | 0 |
| S3 PP3 pair near | 0 (min centre 27.540 mm) | 0 (min centre 14.476 mm) |
| S4 PC tilt > 20° | 17.926° (margin 2.074°) | 18.371° (margin 1.629°) |
| S5a cross-type pair within r2 | 0 (min centre 8.748 mm) | 0 (min centre 8.176 mm) |
| S5b cross-type piece-to-piece minimum < r2 + 1.0 mm | 9.335 mm (margin 0.335 mm) | 9.335 mm (margin 0.335 mm) |
| S6 two magnets intersect | min clearance 0.850 mm | 0.850 mm |
| S7 core-to-4×2 bound < r2 | 8.207 mm (margin 0.207 mm) | 8.117 mm (margin 0.117 mm) |
| **Arm stopped by P1** | no | no |

E1-5-like rigid poses (U offset ±1…20°, then R 0…90°; reported only, contacts ignored): `cross_near` 1,288 (PG8) and
2,059 (PG20); X min centre distance 4.250 mm; PC largest path deviation d 10.397°; CE largest near tilt 27.991°, with
2,801 perpendicular and 1,374 clamped CE evaluations in both arms. These poses bound what E1-5 could reach; the probe
below shows what it did reach.

**P2, stiffness** — FACT — `results/hybrid_g/static/P2_<arm>_<grade>.json`. Stiffness in mN·m/rad, layer in N·m/rad.
L0 and C52 are reference rows (the stop rule applies to arms only).

| Row | Stopped | Zero modes | Collective twist | Negative eigenvalues | Edge spin / slide / cross (min) | Corner twist / tangential (min) | Layer | U-turn peak (N·m) | Probe 5: edge / corner / corner+edge cluster | Probe 5: U layer |
|---|---|---|---|---|---|---|---|---|---|---|
| PG8 N35 | no | 6 | 10,481 | 23 | 121 / -1,993 / 1,002 | 118 / -350 | 3.00 | 0.144 | -937 / -177 / **-177** | 3,046 |
| PG8 N42 | no | 6 | 10,487 | 23 | 121 / -1,995 / 1,003 | 118 / -279 | 3.19 | 0.156 | -938 / -130 / **-130** | 3,238 |
| PG8 N52 | no | 6 | 10,495 | 20 | 121 / -1,997 / 1,004 | 118 / -169 | 3.49 | 0.174 | -939 / -56 / **-56** | 3,538 |
| PG20 N35 | no | 6 | 10,448 | 20 | 121 / -1,602 / 1,365 | 116 / -342 | 3.75 | 0.194 | -741 / -172 / **17** | 3,795 |
| PG20 N42 | no | 6 | 10,451 | 20 | 121 / -1,529 / 1,437 | 116 / -270 | 4.09 | 0.216 | -705 / -125 / **102** | 4,132 |
| PG20 N52 | no | 6 | 10,454 | 20 | 121 / -1,416 / 1,549 | 116 / -159 | 4.61 | 0.252 | -648 / -50 / **233** | 4,657 |
| PG20r N52 | no | 6 | 10,502 | 30 | 121 / -2,559 / 452 | 118 / -176 | 2.41 | 0.103 | -1,220 / -61 / **-335** | 2,452 |
| L0 N35 | (ref.) | 9 | 10,421 | 23 | 118 / -1,974 / 994 | 118 / -714 | 1.99 | 0.083 | -929 / -420 / **-421** | 2,032 |
| C52 N52 | (ref.) | 26 | 2.7e-05 | 0 | -3.0e-07 / 563 / 554 | 1.4e-06 / 551 | 2.57 | 0.181 | 282 / 368 / **648** | 2,578 |

- Both arms leave exactly the 6 centre zero modes, so L0's magnets remove C52's 20 spin and twist zero modes, as G.2
  expected. Negative eigenvalues and negative single-piece stiffnesses are reported, not a stop (U6).
- Only PG20's corner+edge cluster turns positive (+233 at N52), as G.2's hand estimate (about +230) expected; PG8's
  stays negative (-56). The probe below shows that this static difference did not remove the slips (signal 2).

**P3, fit (hard stop per deviation 2)** — FACT — `results/hybrid_g/static/P3_PG8.json`, `P3_PG20.json`
(`hard_stop`, `protrusion`, `surface_gaps`, `items`). Items column condensed; identical for both arms.

| Arm | Hard stop | Protrusion | Min surface gap at home (mm) |
|---|---|---|---|
| PG8 | no | no | 0.850 (cubie_nnn / cubie_0nn; 32 of 2,016 pairs sampled, rest bounded by spheres) |
| PG20 | no | no | 0.850 (cubie_nnn / cubie_0nn; 44 of 3,828 pairs sampled, rest bounded by spheres) |

Items (committed side checks, both arms): M5's 48 magnets fully inside every piece, outer-face wall 0.425 mm (edges)
and **0.175 mm (corners)**; on-axis 4×3 piece magnets fit with wall ≥ 0.4 mm at γ = 0; core cover at c = 0.2 mm
**0.202 (edge) and 0.292 (corner) mm** at the rim. The two bold values are U1's known misses: reported under F-A, not a
stop.

**P4, force-law checks (ER5 V3-turn pass rule; both pair orders must pass)** — FACT —
`results/hybrid_g/static/P4_0.json`, `P4d_PG8.json`, `P4d_PG20.json` (`label`, `verdict`).

| Check | Label | Result | Detail | Summed run (h) |
|---|---|---|---|---|
| P4.0 (PG8, 8 corner core magnets) | PROTOCOL SETTINGS | pass | worst force error 1.18 % of Fn (limit 5 %); worst torque error 3.63e-5 N·m (tolerance 5.34e-5); max near tilt 17.93°; pairs beyond 45°: 0 | 0.06 |
| P4.d PG8 | PROTOCOL SETTINGS | no stop | **D_val = 12.0°** (largest tested); complete; budget not reached | 0.82 |
| P4.d PG20 | PROTOCOL SETTINGS | no stop | **D_val = 12.0°** (largest tested); complete; budget not reached | 2.66 |

### Smoke replays and the cost stop (G.7; reported, change no arm, signal or selection rule)
FACT — `results/hybrid_g/smoke/smoke.json` (`rows.<arm>.turn`, `.snap`, `largest_d_deg`, `steps_per_s`,
`peak_rss_kb`; `references`; `projection`; `memory`; `cost_stop`). Turn: seed 16100, first U of an E1-2 trial. Snap:
seed 16568, +8°.

| Arm | Turn: peak turner torque (N·m) | Turn: steps at the 1 N·m clip | Snap: U error after 1 s | Snap: largest \|leftover spin\| of any piece | Snap: largest tangential leftover (gravity sag) | Largest d | Steps/s | Peak RSS (MB) |
|---|---|---|---|---|---|---|---|---|
| L0 (speed reference) | 0.461 | 0 % | -0.013° | 0.301° | 0.727° | 0.0° | 165 | 110 |
| PG8 | 0.382 | 0 % | -0.017° | 0.300° | 0.466° | 0.45° | 93 | 114 |
| PG20 | 0.785 | 0 % | +0.013° | 0.305° | 0.430° | 0.51° | 94 | 125 |

- References (`references`): L0 0.461 N·m, 0 % at the clip; C52 0.419 N·m, 0 % at the clip (from
  `results/probe/diag/turn_C52_s16100.json`; this fills G.13's TODO); W3 1.000 N·m, 4.3 % of steps at the clip. C52's
  leftover spin in the same snap replay: 1.40–1.74° (G.7). No smoke replay was out of regime.
- **Cost stop: yes** (`cost_stop`: "projected probe 63.67 h > 24 h"). Projection from the smoke steps/s: probe 10.2 h
  (PG8) + 10.1 h (PG20); U5 rest40 extension 9.6 (L0) + 17.0 (PG8) + 16.8 h (PG20); 63.7 h in all. Full rehearsal
  32.1 h (PG8) and 31.8 h (PG20), under 35 h. Memory: at 4 workers 2.99 GB would stay free (limit 2 GB).
- **Decision (P-71; user: "1", 2026-11-22).** The probe (212 trials) runs alone with `--accept-cost-overrun`; its own
  projection (20.3 h) is within 24 h. The rest40 extension is deferred to a later free machine window, not dropped.

### Probe run
- **212 / 212 trials** (PG8 and PG20 × 106: E1-1 20, E1-2 24, E1-5 42, E1-5s 20), all at code commit `20cdcfe`
  (`er9.commit` in every record; `probe/<arm>/environment.json`), D_val 12.0° in force for both arms. Committed
  2026-11-23 at `b0698ba`. All 212 records decompress (checked while drafting). There is no `not_run.jsonl`.
- **Workers.** A 1-worker start (memory rule while other jobs ran), then a restart with 6 workers (`b0698ba` commit
  message). The console run log was lost: the `/tmp` logs were cleared before they were copied, and the empty
  `run_log.txt` was removed (`f595ae5`). Start and end times of the run: [NOT FOUND: no run log; only the commit times
  of `20cdcfe` (2026-11-22 23:40 -0800) and `b0698ba` (2026-11-23 03:12 -0800) bound it].
- **25 % cost checks** (`probe/cost_check_25_PG8.json`, `cost_check_25_PG20.json`; at 27 of 106 trials per arm, 6
  workers). Measured ratio to ER7's L0 wall time: 2.52 (PG8), 3.11–3.15 (PG20). Both files have `stop: true` with
  "projected probe 46.44 h > 24 h" and "46.72 h > 24 h", and `accepted_by_user_flag: true`, so the runner did not
  pause (`er9g_run.write_cost_check` returns "stop and not accepted"). INFERENCE (hand sum): the probe's own share is
  6.38 + 7.88 = 14.3 h (and 6.38 + 7.98 = 14.4 h), within 24 h; the overrun comes from the projected rest40 extension
  (32.2 h and 32.4 h), which P-71 had deferred. Full-rehearsal projections stayed under 35 h (26.3 and 32.5–32.9 h).
  Memory: 13.1 GB would stay free.
- **Summed trial wall time** (`report.json` → `arms.<arm>.wall_h`): 5.2 h (PG8) and 6.2 h (PG20), 11.4 h in all,
  about half the smoke projection (INFERENCE: probe median steps/s 188 and 160 against 93 and 94 in the smoke
  replays; the machine load during the smoke was not recorded).

### Probe signals (G.8; ER7's criteria, G.4 per-class rule at D_val = 12°; FACT, `results/hybrid_g/probe/report.json`)

| Arm | Trials passed (of 106) | 1 snap-back (scored, \|Δ\| ≥ 3°) | 2 rest ≤ 0.5° and 0/20 D11 slips over 60 s | 3 E1-2 and E1-5 all pass | 4 no operational trial out of regime | All four |
|---|---|---|---|---|---|---|
| PG8 | 106 | met (max \|err\| 0.105°) | **not met**: rest max 0.327° (≤ 0.5°), but D11 slip events on 3 seeds (16003, 16011, 16016) | met | met (0 of 106) | **no** |
| PG20 | 106 | met (max \|err\| 0.032°) | **not met**: rest max 0.151° (≤ 0.5°), but a D11 slip event on 1 seed (16013) | met | met (0 of 106) | **no** |

- Signal 2 is missed only through the 60 s slip events (D11: a piece turning ≥ 0.2° within 200 ms). Every 10 s rest
  rotation is ≤ 0.5°, so every trial passes its own criteria (`failed` is empty for both arms). L0 had 2 slip seeds
  of 20 on the same seeds.
- Slip sizes (largest 200 ms change per seed; `side_checks/slip_anatomy/slip_anatomy_out.txt`, read-only side check
  at `15b4e88`): PG8 0.242° (16003), 0.205° (16011), 0.232° (16016); PG20 0.240° (16013). L0's two in ER7: 0.400° and
  0.390°. Each is a slow drift of 1–15 s followed by the jump, and the leading piece is in the U∩F row in all six
  events (that side check). D11 counts events per piece, so PG8's seed 16003 has 2 events (`rest_on_L0_slip_seeds`).
- Signal 4 in detail (`arms.<arm>.class_stats_max`, probe maxima / minima / sums): CE largest near tilt 1.299° (PG8)
  and 1.297° (PG20) against 5°, no clamped or perpendicular CE pair; PC-on largest near tilt 18.322° and 18.416°
  against 20°, with 6,598 and 54,560 clamped evaluations (allowed on-path); no PC-off, PP3 or X near evaluation;
  `cross_near` 0; X minimum centre distance 8.713 mm and 8.163 mm (r2 = 8 mm); largest d 0.86° and 0.80° against
  D_val 12°; ER7's 20° proxy flag in 0 trials.

### Reported items beside L0, C52, W3 and HB1–HB3 on the same 106 seeds (G.8; not signals)
FACT — PG arms: `results/hybrid_g/probe/report.json`; references' turner columns: the same report →
`turner_references_E1-2`; references' rest max, snap-back and wall time as in Parts B–E (`results/probe/report.json`,
`results/hybrid/probe/report.json`), via `probe/writeup.md` table (c).

| Arm | Rest max (10 s) | Snap-back max \|err\|, scored | … all 20 starts | E1-2 turner median / p99 / max (N·m) | Moves > 0.45 N·m | > 0.5 N·m | At the 1 N·m clip (of 24) | Summed trial wall time |
|---|---|---|---|---|---|---|---|---|
| **PG8** | 0.327° | 0.105° | 0.124° | 0.378 / 0.672 / 0.681 | 9 | 4 | 0 | 5.2 h |
| **PG20** | 0.151° | 0.032° | 0.038° | 0.576 / 0.863 / 0.886 | 19 | 19 | 0 | 6.2 h |
| L0 | 0.568° | 0.118° | 0.269° | 0.144 / 0.460 / 0.461 | 2 | 0 | 0 | 2.5 h |
| C52 | 3.4e-6° | 1.013° | 1.013° | 0.700 / 1.000 / 1.000 | 21 | 20 | 4 | 2.1 h |
| W3 | 0.011° | 0.028° | 0.028° | 0.947 / 1.000 / 1.000 | 23 | 23 | 9 | 3.0 h |
| HB1 | 0.169° | 0.054° | 0.080° | 0.461 / 0.860 / 0.901 | 13 | 9 | 0 | 26.2 h |
| HB2 | 0.516° | 0.050° | 0.185° | 0.370 / 0.608 / 0.611 | 8 | 4 | 0 | 27.1 h |
| HB3 | 0.463° | 0.063° | 0.191° | 0.388 / 0.911 / 0.989 | 7 | 5 | 0 | 27.5 h |

- Full-run references (ER7, 204 trials; `turner_references_full_run`): L0 median 0.203 N·m, 0 of 1,376 moves at the
  clip; C52 0.645 N·m, 69 of 1,376 at the clip.
- Against P-67 item 4: both medians are above the realism reference (about 0.2 N·m). PG20's median (0.576 N·m) is
  above the warning level (0.45–0.5 N·m), and 19 of its 24 moves exceed 0.5 N·m; PG8's median (0.378 N·m) is below
  it. INFERENCE (hand ratio): 2.6 × (PG8) and 4.0 × (PG20) L0's median on the same seeds. No move reached the clip.
- HB1–HB3 wall times were measured with other jobs on the machine and are not comparable (Part E).
- Other (`largest_d_deg`, `steps_per_s_median`, `gravity_sag_from_smoke`): steps/s median 188 (PG8) and 160 (PG20);
  gravity sag in the single smoke replay 0.466° and 0.430° (L0 0.727°), not measured on probe trials.

**Rest against L0 (G.8; reported, not signals).** FACT — `report.json` → `arms.<arm>.paired_rest_vs_L0`,
`.slip_seeds_60`, `.slip_seeds_60_complete`, `.rest_on_L0_slip_seeds`.
- Paired 10 s rest rotation on the 20 E1-1 seeds (exact sign test, no ties): PG8 lower than L0 on 16 of 20 (one-sided
  p = 0.0059); PG20 on 17 of 20 (p = 0.0013).
- Slip seeds: PG8 3 / 20 (95 % CP 0.032–0.379), PG20 1 / 20 (0.001–0.249), L0 2 / 20 (0.012–0.317); one-sided Fisher
  p = 0.83 (PG8) and 0.50 (PG20). Reading: "not distinguishable". **Incomplete**: G.8 pre-declared this comparison
  over 60 seeds (20 + rest40's 40); with rest40 deferred it covers 20 (`slip_seeds_60_complete: false`).
- On L0's slip seeds (10 s rest; D11 events over 60 s): PG8 16003 0.105° (2 events), 16005 0.047° (0); PG20 16003
  0.071° (0), 16005 0.095° (0). PG8 slips on 16003 as L0 did; PG20 does not, but slips on 16013, where L0 did not.

### Reading (as fixed by G.8 and P-70; no more)
- **Selection (G.8): none.** Neither arm meets all four signals (`selection.selected` is null; note: "no arm meets
  all four signals: Part G ends with the probe report; the next step goes to the user"). Part G therefore ends with
  this probe report. No full rehearsal (G.9) is run, and G.9's reading does not apply.
- **What the probe shows (FACT, rehearsal seeds, unscored).** Both arms meet signals 1, 3 and 4: the core pairs plus
  L0's magnets snap back (worst 0.105° and 0.032°, against C52's 1.013°) and no trial leaves the validated regime of
  its class. Both miss signal 2, through fast slip events on 3 / 20 (PG8) and 1 / 20 (PG20) seeds, against L0's
  2 / 20. Question (a) is answered "no" for both arms on these seeds; (b) and (c) are met within the probe.
- **INFERENCE.** The core pairs lower the 10 s rest rotation against L0 (16 / 20 and 17 / 20 seeds lower), but on 20
  seeds they cannot be shown to reduce slip seeds. G.2's static warning holds in part: PG20's positive cluster
  stiffness (+233 mN·m/rad) did not remove the slips. Statics guided; the probe decided.
- **P-70 pre-commitments.** Item 1 applies (no arm meets all four): the only permitted follow-up probe is PG20 at N42
  and N35, after one PG20 snap-back diagnostic. Item 2 does not apply (signal 4 met by both arms). Item 3 does not
  apply (no arm selected).
- **Decision (P-72; user, 2026-11-23).** P-70 item 1 is **deferred, not run and not cancelled**; it stays the only
  permitted follow-up probe of a new arm unless the user decides otherwise after D13. D13, an unscored diagnostic of
  the slip events, runs first. The rest40 extension stays deferred. Disclosed in P-72: this was decided after the probe
  result was known, and after the assistant stated its expectation (INFERENCE) that weaker core magnets would lower
  turning torque but not reduce the slips.

### Follow-up: D13 slip diagnostic (separate experiment; does not change Part G's outcome)
`experiments/D13_rest_slip_mechanism/SUMMARY.md` (complete, 50 / 50 runs, 2026-11-23; protocol fixed before any run at
`ffa9189`, P-72; unscored). Its outcome under its fixed rules (FACT there): the reproduction gate passed (all 8 replays
equal the committed 60 s rest records exactly); for Q1 and Q2, **outcome 1, "drift mostly numerical, events depend on
it"**: the NoSlip solver (10 iterations) suppressed the event in 6 / 6 slip cases, and `impratio` 100 slowed the drift
(ρ = 0.009–0.154) but still produced 2 events, about 11–12 × later; for Q3, the label is **gravity-linked** (gravity
off: no event in 6 / 6). Its interpretation (INFERENCE there) is that the 0.2° slips that failed signal 2 come largely
from the simulator's friction model rather than from the magnet layouts; it notes that snap-back, turning and
forgiveness have not been rerun at any other friction setting. **Part G's outcome is unchanged by D13:** signal 2 is
missed by both arms, no arm is selected, M5 stays NOT PASSED, and no simulation setting has been adopted. Under P-73 (user, 2026-11-23) a staged follow-up was approved: Stage 1, D14
(`experiments/D14_noslip_rest_rehearsal/`), a 60 s rest rehearsal of L0, PG8 and PG20 at `noslip_iterations` 10;
Stages 2 and 3 only on the user's go. The setting was chosen after these failures and is disclosed as such.

### Deviations and run notes
1. **Part G deviation 1 (GS5's 48-only half).** Read as passed on ER3's magnet order (2.2e-17); the `layout()`-order
   miss (5.3e-3) is reported. `selfcheck_static.json` therefore carries top-level `pass: false`, and the runner's gate
   applies the deviation explicitly (`report.json` → `gates.<arm>.notes`).
2. **Part G deviation 2 (P3's hard stop).** Evaluated by `er9g_p3.py`, written after the other static results were read
   and before P3 was computed. Protrusion is taken from committed side-check numbers; the CAD-mesh reruns of G.13 were
   not done.
3. **Part G deviation 3 (composite V4/V5/V6 run late).** Required by G.0 before GS1; run after GS1, GS2 and GS4 had
   passed and before any probe trial. All passed. GS1/GS2/GS4 and the replay self-check were rerun afterwards
   (`20cdcfe`).
4. **Accepted code change before any dynamic run.** `65866d6` (`install_er7` cache key only); the static gate files
   predate it and carry the runner's acceptance note.
5. **Cost stop overridden by the user (P-71)**, with `--accept-cost-overrun`; rest40 deferred. The 25 % cost checks
   flagged the same overrun again (driven by the projected rest40 share) and the run did not pause, because the flag
   was set. G.7 says the probe pauses at a 25 % overrun and the user decides; P-71 recorded the user's acceptance of
   the overrun at the smoke check only. INFERENCE: the runner's projection included the deferred rest40 share; the probe's own share was
   14.3–14.4 h, within 24 h, so the probe itself did not exceed G.7's limit. The 25 % flags are disclosed here and
   not separately recorded.
6. **Run log lost** (`f595ae5`); records, cost checks and `report.json` are intact.

### Limits (G.10, plus what the probe adds)
- **Rehearsal only.** ER7's seeds have been used for diagnostics and earlier selections, and this part reuses them.
  Twenty rest seeds give wide intervals (0 / 20 has a 95 % upper bound of 17 %), and the 60-seed slip comparison is
  incomplete because rest40 was not run.
- **P-58 abstraction.** Magnets have no collision geometry and sit at real radii inside B1 pieces. B1 has no radial
  freedom, so magnetic preload, and with it the commercial use of repelling magnets, has no counterpart.
- **Force-law coverage.** CE: M5's 5°. PC on-path: P-60, plus P4.0 for PG8. PC off-path: D_val = 12° from P4.d (none
  occurred; largest d 0.86°). X pairs: dipole only; no near X evaluation occurred in the probe.
- **Lateral offsets.** Corner–edge pairs crossing a turning boundary pass lateral offsets of 6–8 mm; V3a covers
  0–6 mm. M5 had the same gap at the same positions. Disclosed, not a new rule.
- **L0's own largest near tilt in ER7 was 12.59°**, above CE's 5°. INFERENCE: from abuse trials. G.10's TODO, to
  confirm this from ER7's L0 records by sub-experiment, is open [NOT FOUND: no committed result].
- **Numerics.** implicitfast at 0.5 ms has a bounded energy oscillation of about 10 % with core magnets (M6 SUMMARY).
  The ideal-magnet caveat (up to 1.5 ×) carries over, and no derated arm is included. D13 adds that the slip events
  depend on MuJoCo's soft friction constraint at the frozen settings (INFERENCE there).
- **Fit (U1).** Under F-A, Part G's geometry is L0's and C52's, not the CAD's (corner wall 0.175 mm, core cover
  0.202 / 0.292 mm against 0.4 mm). Commercial dimensions are unknown.
- **Write-up limits.** Rest maxima per arm are derived from the records' `rest_rotation_deg` (10 s metric), because
  `report.json` does not carry them. Signal-4 reasons come from the aggregated `class_stats_max`, not per trial (none
  were needed: 0 out-of-regime trials). Gravity sag is from the single smoke replay. Turner statistics cover E1-2
  moves only. Slip sizes come from a read-only side check (`slip_anatomy`), not from `report.json`.
7. **`probe/writeup.md` table (c).** Its wall-time column shows "+ rest40 8.2" (PG8) and "9.8" (PG20). These are
   projections (`report.json` → `cost.rest40_h`), not measured times: rest40 did not run.

Number sources for this section: [`PART_G_NUMBER_SOURCES.md`](PART_G_NUMBER_SOURCES.md).

## Diagnostics (exploratory; single seeds; `results/probe/diag/`)
- **Snap-back replay (seed 16568, +8°).** S1, S2, W1, W2: no leftover spin on any piece. W3: U error 0.028°, largest
  spin 0.097°.
- **Rest leftovers are gravity sag (FACT).** They match piece weight × lever / tangential stiffness to three digits
  (C52 0.066° and 0.093°; S1 0.041° and 0.040°). Sag grows as the anchors weaken: S1 0.065°, W1 0.078°, W2 0.155°,
  W3 0.229° (largest tangential leftover).
- **The stall (seed 16100, first U of an E1-2 trial).** The layer stops at about 6.7° for about 0.1 s while the
  position-controlled turner winds up to 1 N·m, then jumps forward. Two contacts carry most of the torque: the
  U-layer corners' lower chamfers against the side centres' chamfers (45° normals). The U pieces are tilted 0.3–0.4°
  and lag the turner by 0.6–1.55°, each by a different amount. L0's pieces lag at most 0.21° and its peak is
  0.46 N·m.
- **Strength sweep of the same replay.** Anchors at N35 × 0.1, 0.03, 0.003: peak 1.0, 0.78, 1.0 N·m, and 9.8 % of
  steps at the limit at 0.003. INFERENCE: the stall belongs to the B1 cube without in-layer magnets, not to the
  anchors.

## Corrections to my own reasoning, kept on record
1. **Stiffness target.** I set "spin and twist ≥ 100 mN·m/rad" from a joint-friction argument that seemed to match
   ER7's rest leftovers. Those leftovers are gravity sag. The target was stricter than needed, which narrowed the
   screen to 3 layouts; it did not invalidate the layouts that passed.
2. **Cause of the stall.** In the Part C commit I described the stall as "independent of strength" and suspected the
   anchors' tilting pull. The strength sweep shows it is independent of the anchors altogether.
3. **Part E's first specification** used M5's 4 × 2 table past its validated tilt (5°). Caught by the self-check
   output before any arm trial; see amendment 1.

## Limits
- Rehearsal only: ER7's seeds were used for diagnostics, for choosing the arms and for the rehearsal, so the 204
  trials are not independent of the selection.
- P-58 abstraction: the magnets have no collision geometry and sit at ER4's real-mechanism radii inside the B1 model.
- The force law was validated for coaxial piece-to-core pairs to 20° of tilt only on ER5's on-axis face-turn paths at
  c = 0.2 mm (P-60), and to 7.5° for a generic tilted 4 × 3 pair (V3b). Off-axis anchor pairs (W3, and Part E's at
  c = 1–3 mm) have had no V3-turn check, so P-60 does not cover them. (Corrected 2026-11-22: this line used to say
  "validated … up to 20° of tilt" without the path and clearance limits; see "What signal 3 shows".)
- A strength scale (0.3 for W3) is not a catalogue magnet. It stands for a weaker grade, a smaller magnet or a larger
  gap; which one has not been chosen or checked for fit.
- **Fit in a real mechanism: the anchored layout as screened does not fit the real-mechanism CAD (FACT about that
  CAD; `side_checks/realfit/`, measured 2026-11-20).**
  - Corner anchors at 16° lie mostly in air: the corner's material along their line starts at 25.0 mm, while the
    magnet spans 22.35–25.35 mm.
  - Edge anchors at 20° break out of the foot by up to 0.58 mm.
  - In that CAD, three magnets per corner fit toward the centres only as 3 × 2 mm at 5.5–7° or 3 × 3 mm at 5.5–6.5°,
    which is outside Part A's screened range. Edges take 4 × 3 up to 16.5° and 4 × 2 or 3 × 2 at 20°.
  - Whether a feasible placement still holds the pieces has not been computed. A cube designed for these magnets
    could have deeper corner feet; that has not been checked either.
- **Real-magnet equivalents (`side_checks/catalogue/`).**
  - A strength scale multiplies Br², so pair forces go with the scale itself.
  - W3's scale 0.3 at 1.0 mm face gap corresponds to a stocked 3 × 3 N45/N42 at about 1.8–1.9 mm. That magnet has
    no validated force table.
  - The gap is uncertain by about 0.5 mm until pull against gap is measured on real magnets.
- The turner rig is a position servo with a 1 N·m limit; "moves at the limit" is a property of cube and rig together.
- In a turn, each anchor pair of W3 briefly passes through the force law's clamped-z region as it leaves (15.7–18.3°
  of relative rotation, 7.2–8 mm apart, where the near-field weight is ≤ 0.13). ER9 does not report the count.
  **Correction (2026-11-21, from the G1 gap analysis):** an earlier version of this line said P-60 covers it. It does
  not: P-60 accepts clamped pairs only on face-turn trajectories that ER5's V3-turn validated, which were on-axis
  placements at c = 0.2 mm. W3's off-axis anchor paths have had no V3-turn check.
- **What signal 3 shows.** "No trial outside the validated regime" was computed with a 20° tilt limit and the
  perpendicular-pair rule (PROTOCOL.md, Part B criterion 5 and signal 4). The 20° figure comes from ER5's
  V3-turn on the on-axis trajectories; ER5's generic tilted-pair check (V3b) validates the 4 × 3 table to 7.5° only.
  Signal 3 is therefore the protocol's proxy, as Part B's limits say. It is not a validation of the off-axis paths,
  and it is not compliance with P-60. The same applies to Part E: there the hybrid's 4 × 3 corner–edge pairs were
  flagged at 20°, although for that pair type only V3b's 7.5° applies.

## Independent code review (2026-11-20)
A reviewer given the code and protocol, not these results, found nothing that changes a verdict. It confirmed:
- anchor geometry and attraction for all 20 pieces at 0.2–3 mm;
- the configuration reaching every worker, with no leak between arms;
- record bookkeeping and the analysis (L0 and C52 values recomputed from ER7's records);
- the force law's handling of these layouts.

The report's points are dealt with above, under Parts B and C and under Limits. One further point: records are
written without a temporary file. All 112 hybrid probe records present on 2026-11-20 were checked to decompress and
to carry their arm's configuration (144 magnets, scale 0.756).
