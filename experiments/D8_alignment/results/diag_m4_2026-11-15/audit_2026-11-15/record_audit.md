# Audit of written records against stored data (read-only, 2026-11-15)

Scripts: `scratchpad/t2_audit.py`, `scratchpad/t2b_audit.py` (outputs `t2_out.txt`, `t2b_out.txt`), plus
`report_0.1mm.txt` (rehearsal_report.py). All values below are recomputed from per-trial JSON unless stated.
Abbreviations: REH = `experiments/D8_alignment/results/rehearsal_gap0.1mm/`; DG = `…/diag_m4_2026-11-15/`;
DL = `docs/DECISION_LOG.md`. Verdicts: **M** match, **X** mismatch, **C** cannot be checked (data not stored).

## A. REH/SUMMARY.md
| # | Claim | Line | Recomputed (how) | Verdict |
|---|---|---|---|---|
| A1 | Seeds 7000–7999 | 3 | stored seeds 7000–7655 (all `seed`/`setup.seed`) | M |
| A2 | B1 (radial_preload 0), 48 magnets 4×2 mm N35, gap 0.1 mm | 5–6 | `params.radial_preload` 0.0 ×204; `magnets.n_magnets` 48; diameter 0.004, length 0.002, N35; `params.gap` 1e-4 ×204 | M |
| A3 | 188/204 pass | 9 | 188 `pass` True | M |
| A4 | E1-1 16/20; s7000–7003 0.90/0.68/0.56/0.80° | 14 | 16/20; 0.9041/0.6849/0.5617/0.7982 | M |
| A5 | E1-2 23/24; D_s7113 drift 1.06° | 15 | 23/24; 1.0567 | M |
| A6 | E1-3 21/22; D2_s7207 1.02° | 16 | 21/22; 1.0209 | M |
| A7 | E1-4 30/40; 9 scr20inv + sexy6_s7312; 10 drift moves 1.00–1.14°; 4 causality failures | 17 | 30/40; failing scr20inv: 7402,7403,7404,7407,7408,7412,7413,7414,7418 (9) + sexy6_s7312; E1-4 drift moves 10 (1.0007–1.1445); `ok_causal` False 4 | M |
| A8 | E1-5 42, E1-5s 20, E1-6 20, E1-6t 16 all pass | 18 | 42/42, 20/20, 20/20, 16/16 | M |
| A9 | 1,376 moves | 20 | 1,376 `per_move` entries | M |
| A10 | Oracle 1,376/1,376 | 21 | `ok_oracle` True 1,376 | M |
| A11 | Drift: 12 moves (0.9 %) > 1°, worst 1.14° | 22 | 12 (`nontarget_drift_deg`>1 and `ok_drift` False both 12) = 0.87 %; max 1.1445 | M |
| A12 | Causality: 4 moves, motion 45–85 ms before pad force | 23 | `t_pad_force_s − t_layer_motion_s` = 84.5, 57.0, 44.5, 78.5 ms | M (44.5→"45", 84.5→"85" by rounding up) |
| A13 | Turn error ≤ 0.43°; penetration ≤ 0.31 mm | 24 | 0.4274°; 0.3078 mm | M |
| A14 | E1-6m bound holds on every move | 25 | `e16m_P_ok` True 1,376/1,376 | M |
| A15 | "Operational trials reached a tilt of at most 3.48° (E1-6b)" | 28 | `run.py` RULE2 (operational) = E1-1..E1-5s, E1-6a; RULE3 = E1-6b, E1-6c, E1-6t. Rule-2 max `magnet_stats.max_near_tilt_deg` = **3.088° (E1-5)**; 3.480° is E1-6b, a **rule-3** sub-experiment | **X** (value is right for E1-6b, but E1-6b is not operational per run.py; operational max 3.09°). Does not change pass/fail (both < 5°) |
| A16 | 24 abuse trials outside validated range; E1-6c 15.5°, E1-6t 5.26° | 29 | `magnet_outside_validated_range` True: E1-6c 8 + E1-6t 16 = 24; `rule3_label` 24; maxima 15.538, 5.262 | M |
| A17 | The four failing rest trials were the only rest trials that rebuilt the pair list | 34–35 | `magnet_stats.list_rebuilds` = 1 for s7000–7003, 0 for s7004–7019 | M |
| A18 | Each was the first rest trial in its worker, after a sequence trial | 35–36 | no worker id / order stored (log.txt is completion order only) | C |
| A19 | rest_s7000 rerun alone gave 0.904° again, identical | 37 | DG/timeseries/rest_s7000…json `rest_rotation_deg` 0.9041107575845045 == REH record (bit-identical) | M |
| A20 | rest_s7004 gave 0.122° and passed, "even though it also rebuilt the list" | 37–38 | DG/timeseries rest_s7004 0.12178, pass True; DG/history_test.jsonl rest_s7004 `rebuilds` 1 (rerun). In REH the original rest_s7004 had `list_rebuilds` 0 | M (for the rerun) |
| A21 | M1 without magnets rest 0.006–0.037° (seeds 1000–1019) | 39 | E1_scored/results/E1-1: 20 trials, seeds 1000–1019, 0.0059–0.0367 | M |
| A22 | Earlier gap probe (seeds 95–97) covered sequences only | 47 | probe data not stored (only `E4_scored_m4/smoke/smoke_seq_s95.json`, `smoke_snap_+5_s96.json`) | C |

## B. DG/SUMMARY.md
| # | Claim | Line | Recomputed (how) | Verdict |
|---|---|---|---|---|
| B1 | New diagnostic seeds 9000–9599 | 4 | stored seeds in gap_study include **9610, 9611, 9626, 9627, 9654, 9655, 9800–9803** | **X** (range understated; no effect on pass/fail) |
| B2 | §1 4×2: drift median 0.88 / p90 1.49 / max 1.69, 46/120 > 1°, rest 0.20, 0.38, 0.98, 0.53 | 11 | size_gap0.2mm/4x2_N35 seq: 0.879/1.487/1.692, 46/120; rest s9000–9003 0.201/0.384/0.975/0.528 | M |
| B3 | §1 3×1.5: 0.93/1.48/1.73, 56/120, rest 0.41, 0.71, 0.44, 0.44 | 12 | 0.927/1.480/1.729, 56/120; rest 0.411/0.714/0.443/0.440 (s9001 = 0.714, fail per log) | M |
| B4 | §1 none: 0.83/1.40/1.98, 39/120, rest 1.03, 1.02, 1.30, 1.30 | 13 | 0.828/1.396/1.978, 39/120; rest s9000–9003 1.027/1.017/1.299/1.303 | M |
| B5 | M1 scored: 0.013/0.033/0.71, 0, rest ≤ 0.04 (1,376 moves) | 14 | E1_scored E1-2..4: 1,376 moves, 0.0127/0.0326/0.7049, 0 > 1°; rest max 0.0367 | M |
| B6 | 0.1 mm rehearsal: 0.46/0.83/1.14, 12, rest 0.05–0.90 | 15 | 0.4604/0.8314/1.1445, 12; rest 0.0541–0.9041 | M |
| B7 | "35× rise in drift" | 17 | median ratio 0.4604/0.0127 = **36.3×** (35.4× from the rounded table values) | M (approx.; rounding) |
| B8 | 0.2 mm B1+magnet median 0.88°, 0.1 mm 0.46° | 20 | 0.879; 0.460 | M |
| B9 | README: "Pieces in B1 sit 1–2° off square" | 21 | `experiments/D8_alignment/README.md:172` contains the sentence | M (text) |
| B10 | Rest: magnets 0.2–0.98° vs 1.0–1.3° without | 22 | 4×2 0.201–0.975 (3×1.5 0.411–0.714); none 1.017–1.303 | M |
| B11 | Every move in every arm oracle-correct (360/360) | 23 | 3 arms × 120 = 360, `ok_oracle` 360 | M |
| B12 | Turn error at most 0.57° with magnets, 2.6° without | 23 | 4×2 max 0.568; **3×1.5 max 0.690**; none 2.625 | **X** (with-magnets max is 0.69° if the 3×1.5 arm is included; 0.57° holds for 4×2 only). No pass/fail effect (limit 2.0°) |
| B13 | §2 "5 ms resolution" | 25 | move timeseries rows dt 5.0 ms; **rest timeseries dt 25 ms** | X (minor: rest_s7000 claims rest on 25 ms data) |
| B14 | D_s7113 move 0 drift 1.057°; piece 25 −1.031° → +0.027°; worst non-target 1.03 → 0.05° | 26–27 | per_move drift 1.0567; `nt_err_deg` piece 25 −1.031 → 0.027; worst 1.031 → 0.051 | M |
| B15 | D_s7112 0.82 → 0.12°; scr20inv_s7402 move 26 1.10 → 0.18° | 28 | 0.816 → 0.123; 1.096 → 0.184 | M |
| B16 | Pre-move errors alternate in sign around the layer | 28–29 | D_s7113 first-row signs [+,+,−,−,−,+,−,+,+,+,−,−] in `meta.nontarget` order; angular order of pieces not stored | C |
| B17 | rest_s7000 event t = 2.45 s; piece 9 1.17 → 1.44°, piece 2 1.05 → 1.31° | 31–32 | `piece_err` vector norm: largest step between t = 2.425 and 2.450 s; piece 9 1.172 → 1.438, piece 2 1.046 → 1.307 | M |
| B18 | All six layers shifted at the same moment | 32 | face columns at the largest face step (2.450→2.475 s): L −0.17°, F/D/B +0.02–0.03°, U/R ≤ 0.002° | C (not confirmed by the obvious metric; method not stated) |
| B19 | Worst error rose 0.97° → 1.48° over the trial | 32–33 | norm: first 0.966, max 1.482, last 1.456 | M (1.48 = trial peak, not final) |
| B20 | Slow creep ≈ 0.01°/s between events | 33 | worst-piece norm: median abs slope 0.0035°/s; linear trend t > 3 s −0.0037°/s | C (not reproduced; metric not stated) |
| B21 | §3 sexy6_s7312 original: move-12 drift 0.745°, motion 27.033 s, non-causal | 41 | REH per_move[12] drift 0.74517, `t_layer_motion_s` 27.0330, `ok_causal` False | M |
| B22 | Fresh process ×2: 0.37033° bit-identical, 27.1285 s, causal | 42 | history_test.jsonl (list null) 0.37032574766889476 / 27.1285 / True; timeseries sexy6 file same drift | M |
| B23 | After rest_s7004: 0.39097°, 27.376 s, causal | 43 | history_test.jsonl (list "kept") 0.3909746722 / 27.376 / True | M |
| B24 | D_s7113, D_s7112, scr20inv_s7402, rest_s7000 reproduce bit for bit | 45–46 | timeseries `per_move` drift, turn error, t_pad, t_motion == REH records exactly; rest_s7000 rotation identical | M |
| B25 | With list reset, 0/360 moves non-causal at 0.2 mm | 50–51 | `ok_causal` False 0 of 360 | M |
| B26 | After-fix check result in history_test_after_fix.jsonl | 56 | file has 3 rows; sexy6 "kept" now 0.37033 = fresh | M |
| B27 | "drift over 1° appeared in **11** trials" (0.1 mm rehearsal) | 58 | 10 trials (12 moves) | **X** (known). Does not change the A1 FAILED verdict |
| B28 | 3×1.5: all pass, validated tilt 7.5° | 61 | `d8_1b_checks_3x1.5_N35_s1.json` `all_pass` True, `validated_tilt_deg` 7.5 | M |
| B29 | 4×1.5: V3 pair force error 5.65 % vs 5 % | 62 | `d8_1b_checks_4x1.5_N35_s1.json` max `err_rel_Fn` 0.05648; `all_pass` False | M |
| B30 | Snap 0.2 mm: 4×2 3/4 (+3° left 0.60°); 3×1.5 2/4 (−3 → 0.56, −5 → 0.66) | 64–65 | 4×2 fails snap_+3 `U_err_after_1s_deg` 0.6003; 3×1.5 fails −0.5643, −0.6561 | M |
| B31 | Radial slide only when radial_preload > 0 at m1_model.py:146 | 70 | line 146 `if p.radial_preload > 0:` | M |
| B32 | ~12° twist play at 0.02 N·m (D1 config J), design proposal §2 | 72–73 | `D8_1b_DESIGN_PROPOSAL.md:28` "~12° of twist play at 0.02 N·m" (line 14 says 0.02–0.05) | M (text; underlying D1 data not re-checked) |
| B33 | §5 dated 2026-11-16 | 77 | gap_study file mtimes 2026-11-15 20:10–20:34 (WSL clock, PST); timezone of the record unknown | C |
| B34 | Face gap 0.85 mm (wall 0.4 mm) | 79 | `magnets.params.wall` 0.0004, `params.gap` 5e-5 → 2×0.4+0.05 = 0.85 (formula assumed) | M (ASSUMPTION on formula) |
| B35 | §5 row 0.2 mm magnets: 0/3; 0.88/1.68/1.69; 1.45/2.01; 0.095/0.68; 0.29; 0.20–0.98; 4.96 | 83 | 0/3; 0.879/1.680/1.692; 1.445/2.005; 0.0953/0.676; 0.292; 0.201–0.975; 4.959 | M |
| B36 | §5 row 0.2 mm none: 0/3; 0.83/1.90/1.98; 2.44/5.25; 0.34/1.00; 0.35; 1.02–1.30 | 84 | 0/3; 0.828/1.902/1.978; 2.435/5.254; 0.338/1.000; 0.353; 1.017–1.303 | M |
| B37 | §5 row 0.1 mm magnets: 3/3; 0.55/0.95/0.97; 0.97/1.50; 0.098/0.70; 0.31; 0.10–0.77 (1 fail); 2.66 | 85 | 3/3; 0.552/0.947/0.966; 0.974/1.497; 0.0977/0.7006; 0.305; 0.095–0.771, 1 fail (s9001); tilt 2.662 over sequences, **2.672 over all 11 trials** (snap_+3) | M (tilt column = sequences only, per gap_an.py) |
| B38 | §5 row 0.05 mm magnets: 3/3; 0.30/0.63/0.70; 0.68/0.92; 0.12/0.69; 0.29; 0.10–0.28; 1.40 | 86 | 3/3; 0.296/0.628/0.699; 0.676/0.919; 0.1235/0.694; 0.288; 0.101–0.279; 1.395 over sequences; **12.58 over all 21 trials** (corner twist, rule-3 labelled), 3.45 (E1-6t), 2.00 (opposed) | M for sequences; column label omits "sequences only" |
| B39 | §5 row 0.05 mm none: 0/3, jam on first move (86° short, pen 0.76 mm, unreadable); 0.72/1.33/1.35; 1.01/5.50; 0.41/1.00; 0.76; 0.22–0.30 | 87 | 0/3; s9400 move 1 `turn_error_deg` 85.60, pen 0.758, `observed_valid` False; drift 0.717/1.325/1.351 (81 moves); 1.006/5.496; 0.411/1.000; 0.758; 0.221–0.304 | M |
| B40 | 0.05 mm magnets passed all 21 trials; 120 moves oracle-correct | 89–90 | 21/21 `pass`; 120/120 `ok_oracle` | M |
| B41 | 4 snaps from ±3/±5° to ≤ 0.11° | 92 | max \|`U_err_after_1s_deg`\| 0.1111 | M |
| B42 | Forgiveness ±10 completes, ±20 blocked | 93 | ±10 `outcome` completed; ±20 blocked_unknown; all pass | M |
| B43 | Opposed 1 and 2 N·m pass | 94 | both `pass` True | M |
| B44 | Corner twist 23.7° at 5 N·m (≈40° at 0.2 mm); 2.7–2.8 N·m at 15° | 95 | `max_twist_deg` 23.65/23.77; 0.2 mm: stage1_r2 B1_nom 39.1/41.5; `torque_at_twist_15deg_Nm` 2.726/2.801 | M |
| B45 | Toy test 10.4–10.6° at 0.45 N·m, solved after release | 96 | 10.42/10.56; `final_solved` True | M |
| B46 | Without magnets: torque saturates at 1.0; every forgiveness trial blocked, even ±10° | 98–99 | 11/81 moves at 1.0; all 4 forgive `outcome` blocked_unknown | M |
| B47 | With magnets median torque close to 0.2 mm | 100 | 0.1235 vs 0.0953 N·m | M (qualitative) |
| B48 | Abuse penetration 0.53 mm (2 N·m opposed), 0.64 mm (corner twist) | 102 | 0.5263; 0.6373/0.6450 | M |
| B49 | "204-trial rehearsal found drift failures in **11** trials" | 106 | 10 | **X** (same error as B27). No pass/fail change |
| B50 | 3 sequences and 4 rest trials per arm | 105–106 | 3 seq + 4 rest in every arm | M |

## C. DL entries P-25, P-26, P-27 (lines 104–106)
| # | Claim | Recomputed | Verdict |
|---|---|---|---|
| C1 | P-25: seeds 7000–7999; 188/204 | 7000–7655; 188 | M |
| C2 | P-25: drift > 1° in **11** trials | 10 trials | **X** (known). A1 still FAILED |
| C3 | P-25: 12/1,376 moves, max 1.14° | 12; 1.1445 | M |
| C4 | P-25: 4 causality failures, 45–85 ms | 4; 44.5–84.5 ms | M |
| C5 | P-25: rest 0.56–0.90° in 4/20; M1 ≤ 0.04° | 0.5617–0.9041 in 4/20; M1 max 0.0367 | M |
| C6 | P-25: reproduced in isolation (seed-specific, not run order) | rest_s7000 rerun bit-identical (A19) | M |
| C7 | P-25: all 1,376 moves oracle-correct | 1,376 | M |
| C8 | P-25: operational tilt ≤ 3.48°, inside 5° | rule-2 max 3.088° (E1-5); 3.48 is E1-6b (rule 3) | **X** (same as A15; no pass/fail change) |
| C9 | P-25: 0.2 mm probe had 9/18 moves over 1° | probe records not stored | C |
| C10 | P-25: 3×1.5 all pass, validated 7.5° | `all_pass` True, 7.5 | M |
| C11 | P-25: 4×1.5 run stopped by memory pressure, log incomplete | current `d8_1b_checks_4x1.5_N35_s1.json` is a complete run (`all_pass` False, V3 5.65 %); the stopped run's log is not separately identifiable | C (historical; superseded by P-26/DG §4, not contradicted) |
| C12 | P-26: drift medians 0.88 / 0.93 / 0.83° vs 0.013° | 0.879 / 0.927 / 0.828 vs 0.0127 | M |
| C13 | P-26: non-causal in rehearsal worker, causal in fresh process | B21–B23 | M |
| C14 | P-26: 4×1.5 V3 5.65 % > 5 %; 3×1.5 validated to 7.5° | 0.05648; 7.5 | M |
| C15 | P-26: 3×1.5 snaps less reliably | 2/4 vs 3/4 (B30) | M |
| C16 | P-27: 0.05 mm + 4×2 passed all 21 trials | 21/21 | M |
| C17 | P-27: drift max 0.70°, rest ≤ 0.28°, snap ≤ 0.11° | 0.699; 0.279; 0.111 | M |
| C18 | P-27: magnet tilt ≤ 1.40° | 1.395 over sequences; over the 21 trials it reports: twist 12.07/12.58° (rule-3 labelled "outside validated range"), E1-6t 3.45°, opposed 2.00° | **X** as written (true only for sequence/rule-2 trials). Pass/fail unchanged (rule 3 labels, does not fail) |
| C19 | P-27: turning torque near 0.2 mm level | median 0.1235 vs 0.0953 | M (qualitative) |
| C20 | P-27: corner twist 23.7° at 5 N·m | 23.65/23.77 | M |
| C21 | P-27: without magnets 0.05 mm jams | s9400 move 1 (B39) | M |

## Totals
- Claims checked: 93 (A 22, B 50, C 21).
- Matches: 76. Mismatches: 9 rows (A15, B1, B12, B13, B27, B49, C2, C8, C18), of which B27/B49/C2 are the same
  known "11 vs 10" error and A15/C8 the same tilt-classification error, so 6 distinct errors.
  Cannot check: 8 rows (A18, A22, B16, B18, B20, B33, C9, C11).
- None of the mismatches changes a pass/fail conclusion.
