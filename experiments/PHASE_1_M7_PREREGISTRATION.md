# Phase 1 (G1) Pre-registration: M7, the L0 magnetic contact cube with rounded edges and NoSlip 10

**Status: DRAFT, revision 2, NOT APPROVED. Nothing here is in force.**
- **Revision 2 (P-89)** makes every required change of review 1 and adopts most of its optional ones
  ([`M7_PREREGISTRATION_REVIEW1_2026-11-25.md`](M7_PREREGISTRATION_REVIEW1_2026-11-25.md); two reviewer subagents,
  the user having widened P-86 Q8 to two for that round). The response, item by item, is in §9. It is the text sent to
  review 2.
- Revision 0 (`01938af`) was written by the main session on 2026-11-25, after P-83 (L0 chosen as the working
  candidate) and P-85 (R3, the E1-7 rehearsal).
- §8 was answered the same day (P-86): Q3 yes, Q4 criterion, Q8 one reviewer subagent per round, and the defaults for
  Q1, Q2, Q5, Q6, Q7 and Q9.
- **Revision 1 (P-88)** adds:
  - the fresh-seed rehearsal (R4, P-87);
  - the §6 code as built (`experiments/E7_scored_m7/`), with its self-check and smoke results;
  - the resolved TODOs (switched constraints, E1-1 radial pop, E1-5s function).

  It is the text sent to the first independent review.

The text is built from:
- `PHASE_1_M5_PREREGISTRATION.md`, revision 8, the last text in force (it governed M5's scored run);
- the ER9 skeleton `ER9_anchored_core_layouts/proposals/G1_SCORED_PREREG_DRAFT.md`. That skeleton was written for a
  Part G arm (PG8/PG20) and is superseded for that purpose by P-83. It is kept as a source.

No scored seed (17000–17999) has been touched. The simulations behind this revision are:
- the unscored R4 rehearsal (19000–19655);
- the self-check (rehearsal seeds 16000–16655);
- the smoke run (18000–18099).

**Path to force (as M5's, PROPOSAL):**
1. The user settles §8's questions.
2. The text is revised.
3. The §6 code is built and self-checked on rehearsal seeds (**done**, §6).
4. Independent review of text and code (§6.5) continues until a review requires no changes.
5. The user approves the text, and a Status-line commit is made.
6. The user gives an explicit go. Per P-63, the main session stops before any scored run.

**Freeze rule (as M5):**
- Once in force, the text changes only by a change an independent review requires, or by a dated amendment the user
  approves before the first scored trial.
- No threshold is loosened after any result (VALIDATION_PLAN threshold policy).

**Labels:**
- `FACT`: stated in the named file or record.
- `INFERENCE`: reasoning, not computed by project code.
- `PROPOSAL`: needs approval.
- `TODO`: still to be produced.
- `ASSUMPTION`: taken as given for the model, not established.
- `UNVERIFIED`: from a source that was not read, or that conflicts with another.

---

## 0. Disclosure (read first)
1. **Post-hoc chain (`FACT`, DECISION_LOG).**
   - M5 (L0's magnets, chamfer, default NoSlip) failed G1 at 203/204: one 10 s rest rotated 0.560° against ≤ 0.5°
     (P-51).
   - Diagnosis and redesign followed on the rehearsal seeds 16000–16999:
     - D10–D13 (rest-slip mechanism);
     - ER7–ER9, including Part G's PG8 and PG20;
     - D14: **NoSlip 10** adopted as the candidate solver setting after D13 (P-73), with a 60 s instrumented rest;
     - the 6° catch and one jam with the chamfer (P-76–P-78);
     - D15: **rounded edges at R 2.5 mm** replace the 45° 1.4 mm chamfer (P-79, P-80).
   - R2 rehearsed three arms (P-82), and **L0 was chosen from them** after the results were seen (P-83).
   - R3 then ran E1-7 on L0 (P-85).
   - Every one of these choices was made after seeing results on the rehearsal seeds. Only the scored seeds (§3) are
     independent of them.
2. **Independence (as M5 §0 item 2).**
   - Held out: the seeds, the setup draws and the E1-4 scrambles, which are drawn from the scored seeds.
   - Not held out: every other move string is fixed by M1 and has been seen many times.
3. **Clearance.** The 0.05 mm piece gap is an `ASSUMPTION` (M5 §0 item 3). Real cube clearances are unverified
   (P-77). The project's CAD figures conflict and are `UNVERIFIED`:
   - `ER9_anchored_core_layouts/side_checks/README.md:56` gives the CAD's "piece gap" as 0.25 mm;
   - `docs/research/CUBE_MECHANISM_FINDINGS.md:71` gives the same CAD's neighbour clearance as 0.033–0.038 mm.

   `docs/research/MAGNET_POCKET_WALL_FINDINGS.md:99-102` records this as unresolved; the two may measure different
   things.
   - R3 shows drift fragility at 0.1 mm: 1.005–1.095° against ≤ 1.0°.
   - M5 §4 already expected that flip from P-25.
4. **Turning torque is uncalibrated (P-83 (2)).**
   - The only verified real figure is 0.09 N·m. A snippet-only bracket suggests 0.10–0.20 N·m
     (`docs/research/TURNING_TORQUE_FINDINGS.md`, addendum 2026-11-25).
   - L0's R2 turner median is 0.103 N·m and its max 0.185 N·m.
   - Torque is reported, never judged (§4.3).
5. **Rounded edges are a modelling choice.**
   - R 2.5 mm was chosen because it removed the chamfer's catch (P-78–P-80), not from a measured profile.
   - Real-cube edge geometry is unverified (P-78; P-82 lists the physical credibility of the rounded edge as lacking).
     Whether real speedcube pieces have rounded edges of this size is `UNVERIFIED`. Corner cutting is a turning
     tolerance, not evidence of an edge profile.
   - R3 shows the outcome holds over R 1.8–3.6 mm.
   - Static checks: the magnets keep the 0.4 mm wall at those radii, and V4–V6 pass (`r3_static.json`).
6. **NoSlip 10 is a solver setting chosen post hoc** (P-73), and **E1-1 passes only with it** (review 1, R2).
   - **Sequences:** R3 shows the outcome holds over NoSlip 5–20, and with NoSlip off (the 0 reference arm).
   - **Rests: without NoSlip, the M7 geometry fails M1's E1-1 limit at a rate like M5's.** Each 60 s rest is preceded
     by a 10 s warm-up that is exactly M5's E1-1 trial with rounded edges and no NoSlip. It is recorded
     (`warmup_10s`), not judged. `FACT` from the committed D15 records:
     - R2 L0 (rehearsal seeds): 3 / 20 warm-ups above 0.5° (`rest_s16003` 0.709°, `rest_s16005` 0.549°,
       `rest_s16018` 0.694°);
     - R4 L0 (fresh seeds): 1 / 20 (`rest_s19008` 0.577°);
     - the judged 60 s rests of those seeds, with NoSlip 10: at most 0.0051° and 0.0055°.
   - `INFERENCE`: rounded edges removed the turning catch and jam; NoSlip removed the rest slips. The E1-1 result is a
     property of the model *with* this solver post-process.
   - The scored run reports the NoSlip-off warm-ups for E1-1, REST-X and the E1-7 rests (§4.3).
7. **Known fragilities (R3, P-85; E1-7 is reported, not judged):**
   - gap 0.1 mm: drift (both sequences);
   - μ 1.0: a jam at the clip (sexy6);
   - timestep 0.75 ms: penetration 0.504 mm (6-move).
8. **Margins on the rehearsal seeds** (`FACT`, R1 + R2 L0, 1376 moves, 20 rests of 60 s):

   | Quantity | Largest | Limit |
   |---|---|---|
   | non-target drift | 0.73° | 1.0° |
   | penetration | 0.29 mm | 0.5 mm |
   | 0–10 s rest rotation | 0.005° | 0.5° |
   | turner torque | 0.185 N·m | clip 1.0 N·m |

   For comparison: M5's rehearsal maximum rest was 0.290°, and its scored run then failed at 0.560° (P-51). Rehearsal
   maxima do not bound scored maxima.
   **Fresh-seed rehearsal R4 (§7 item 2; P-87; seeds 19000–19655, never used before; same configuration and list):**
   - 204 / 204, both signals met; 0 slip events in 20 rests of 60 s; no move at the clip.
   - Largest drift **0.781°** (up 0.05° from the rehearsal), penetration 0.292 mm, rest 0.0055°, turner torque
     max 0.193 N·m.
   - The drift tail grows with new seeds, as expected. 0.22° of margin remains, and drift is the most likely route to
     a scored failure.
9. **Provenance.** The author has seen M5's scored results and every rehearsal record. No change to this text may be
   made in light of this run's scored results.

## 1. Mechanism under test (frozen configuration, PROPOSAL)
| Group | Value | Basis |
|---|---|---|
| Cubies, rig, contacts | M5 §1 unchanged: B1 (`radial_preload = 0`), piece gap 0.05 mm, face gap 0.85 mm, implicitfast at 0.5 ms, M1's contact and solver settings | `FACT`, M5 §1 |
| **Edge profile** | `edge_profile = "rounded"`, `edge_radius = 0.0025` (`M1Params`, R0). The chamfer value is unused under the rounded profile | P-79, P-80; R0 shows a byte-identical chamfer default |
| **NoSlip** | `noslip_iterations = 10` on the trial model, applied by wrapping `scored.build_m1_xml` (D13 `with_noslip`). The magnet model has no NoSlip | P-73; D14 Stage 3 proof checks |
| Magnets | **M5's 48 × 4×2 mm N35** at M5's positions, with M5's table and V3 record (validated near-pair tilt 5°). Identical to M5 | `FACT`, M5 §1; L0 = M5 magnets (ER9 Part G's gate GS1, `er9g_layouts.py`) |
| Turner | M1's rig: turn_kp 5, kv 0.2, torque clip 1 N·m. Clip = peak ≥ 0.999 N·m | `FACT`, M5 §1, §4 |
| Execution path | M5's runner (`E5_scored_m5/run.py`) and M4's, loaded unchanged in M7's own module instances (as E6), with the edge and NoSlip installs applied per trial by a wrapper around `M4.run_trial` (§6.1). The self-check reproduces the D15 rehearsal records with 0 differences (§6.2) | `FACT`, `E7_scored_m7/results_selfcheck/selfcheck.json` |
| Software | MuJoCo 4.0.1, Python 3.12.3, NumPy 2.5.4, SciPy 1.18.1, in WSL (`~/.venvs/rubiknetic`; Ubuntu 24.04.5 per `/etc/os-release`) | `FACT`: the versions appear in all 357 R2, 74 R3 and 214 R4 records, whose platform string ends in `glibc2.39` |

**Abstractions (to be published with any verdict; VALIDATION_PLAN G1 "Pass"):**
- The cube is contact-emergent (B1). `m1_model.py`'s docstring (lines 11-13) states that no constraint is switched
  at runtime and nothing writes cubie state, and every trial's edit audit (M1 rule 2, `edit_audit_violations`) checks
  the second part. `INFERENCE`: the VALIDATION_PLAN "switch timing" item therefore does not apply.
- B1 has no radial freedom, so there is no magnetic preload.
- Magnets have no collision geometry.
- The ideal-magnet law may overstate force by up to 1.5× (M5 §7; D8 V2). E1-7's 0.67 scale covers this (passed, R3).
- NoSlip is a solver post-process that removes contact slip velocity. It is a numerical choice, not a physical law.
  For sequences, R3's NoSlip 5 / 20 / 0 arms bound its effect: all pass. For rests, the NoSlip-off evidence is the
  warm-ups of §0 item 6, which fail E1-1 in 3 / 20 rehearsal and 1 / 20 fresh seeds. The rest result depends on it.
- **Lateral-offset disclosure (carried from M5):** corner–edge magnet pairs that cross a turning boundary pass lateral
  offsets of 6–8 mm, while V3a validates 0–6 mm (D12 PROTOCOL; review G11).
- **Part G's "composite review" does not apply:** M7 has one magnet type, M5's.

## 2. Run integrity
M5 §2 unchanged, except as noted:
- record key; one first start with empty folders;
- immutable manifest (trial list, "not run" set, table SHA-256s, environment);
- append-only start log and ledger; atomic records written by the parent;
- the resume rule; INVALID and INCOMPLETE are final;
- harness exceptions become failing records;
- `MemoryError` / `OSError` / killed worker are interruptions.
- **Location check** as M5 revision 8: no path in a OneDrive folder.
- **Environment:** M5's check compares every record's environment (MuJoCo, NumPy, SciPy, Python, CPU) with the
  manifest. The run is started from WSL with `~/.venvs/rubiknetic`, the environment of every D15 record.
- **No other jobs in WSL** during the run (P-82 (b)). Each record stores the 1-minute load average at its start
  (`loadavg_start`); M5's start log does not record the load, and M5's runner is not changed for it.
- **Disk:** the runner refuses to start with less than 3 GB free. The 75 60 s rest records are about 11.4 MB each
  (about 0.85 GB in all).

## 3. Trials and seeds (PROPOSAL)
**Seed map: M5 scored seed + 7000** (17000–17655). Q2.
- `FACT` within §6.4's scope: no `.json`, `.json.gz` or `.jsonl` file under `experiments/` uses 17000–17999. The full
  search (tracked text, untracked files elsewhere) is `TODO`, repeated as the last step before fixing.
- D12's and Part G's runners refuse that block in code. The lapsed M6 draft and the never-run E6 runner named it
  (P-66).

| Sub-exp. | Content (M1/M4/M5) | Trials | Seeds | In Option A |
|---|---|---|---|---|
| E1-1 | Rest, **60 s instrumented** (D14 Stage 1's steps, as R2). M1's criterion is applied to 0–10 s; slip events over 0–60 s per Q4 | 20 | 17000–17019 | yes |
| E1-2 | Quarter turns, 6 faces × CW/CCW × 2 | 24 | 17100–17123 | yes |
| E1-3 | Half turns | 22 | M5 list + 7000 | yes |
| E1-4 | 20 × sexy6; 20 × scramble(20, s) + inverse (scrambles from 17400–17419) | 40 | M5 list + 7000 | yes |
| E1-5 | U offset 0…20°, both signs, then R | 42 | 17500–17541 | yes |
| E1-5s | Snap-back from ±1, 2, 3, 5, 8°, 2 repetitions (seed = base + 10·rep + \|δ\|) | 20 | 17551–17568 (10 seeds) | yes |
| E1-6a/b/c | Open pad (6), opposed torques (6), corner twist (8) | 20 | M5 list + 7000 | yes |
| E1-6t | Toy-standard torque 0.45 N·m | 16 | 17640–17655 | yes |
| E1-6m | Energy and impulse per move of E1-2 to E1-4 | (moves) | — | yes (⟨P⟩) |
| **Total Option A** | | **204** | | |
| E1-6n | No-magnet rerun of E1-2 to E1-6t on the same seeds (Q5) | 184 | as above | never |
| E1-7 | R3's list: M5's factors with edge radius 1.8 / 3.6 mm in place of the chamfer, NoSlip 5 / 20, and the reference NoSlip 0 (tag `noslip=0`, outside the band), both sequences; plus R3's 15 one-seed 60 s rests (Q6) | 58 (+2 not run, V3) + 15 | 17000 | never |
| REST-X | 40 extra 60 s rests (E1-1 configuration), reported (Q7) | 40 | 17700–17739 | never |
| E1-8 | Throughput on a quiet machine, after the verdict | — | — | sign-off only |

- The exact list is M5's runner list + 7000, checked by a unit test (`tests/test_scored_m7.py`,
  `test_m5_list_plus_7000`).
- **Totals (`run.py all --dry-run`, `FACT`):** 501 runnable trials, made up of:
  - 204 Option A;
  - 184 E1-6n;
  - 73 E1-7 (58 sequences + 15 rests);
  - 40 REST-X.

  There are also 2 registered "not run" trials (E1-7 4×1.5 N35, failed V3).
- **Smoke seeds:** 18000–18099.
- **Fresh-seed rehearsal (Q3):** 19000–19655.
- 10000–10999 (M5's scored range) and 16000–16999 (rehearsal) are never used in scored mode.

## 4. Criteria (stated before any data)
### 4.1 Inherited unchanged (`FACT`: M1 §4, M4 §4 with Amendment 1 A2, M5 §4)
- **E1-1:**
  - solved and valid;
  - rest rotation ≤ 0.5° over the first 10 s;
  - radial offset ≤ 0.5 mm;
  - penetration ≤ 0.5 mm;
  - pop ≤ 0.3 mm: **not evaluated on the 60 s record.** B1 has no radial joint, so pop is identically zero (D14
    `e11_pass`). `FACT`: the largest value in M5's 20 scored E1-1 records is 7.6e-14 mm. Omitting it loosens
    nothing.
- **E1-2 and E1-3:** oracle agreement; turn error ≤ 2°; non-target drift ≤ 1°; penetration ≤ 0.5 mm; pop ≤ 0.3 mm;
  causality.
- **E1-4:** E1-2's criteria per move, every state agreeing with the oracle, and a growth slope < 0.005°/move.
- **E1-5:** categorical: never an illegal or oracle-mismatched state.
- **E1-5s:** from ≥ 3°, |U error| ≤ 0.5° after 1 s, judged by M5's code unchanged: `d8_1b_stage1.run_snap`'s
  `U_err_after_1s_deg`, checked in `E4_scored_m4/run.py` `apply_m4_criteria`.
- **E1-6a:** rotation ≤ 0.5°; stays solved.
- **E1-6b:** categorical; radial change ≤ 0.5 mm.
- **E1-6c:** M1's categorical criterion.
- **E1-6t:** solved after release; penetration ≤ 0.5 mm.
- **E1-6m:** ⟨P⟩ per move.
- **Magnet validity (M4 rule 2, 5° tilt):** operational trials fail when out of range; abuse trials are labelled
  (rule 3).
- **Run-integrity rules:** M1 rules 1–5 and M4 rule 1.

### 4.2 Changed or new (PROPOSAL)
- **E1-1 procedure:** the 60 s instrumented rest replaces the 10 s rest. M1's criterion still reads 0–10 s, so this
  does not loosen M5.
  - Before it, each rest60 trial runs M5's 10 s E1-1 trial with rounded edges and **NoSlip 0** as a warm-up (R2–R4's
    steps). The warm-up is recorded as `warmup_10s`, **not judged**, and reported (§4.3; §0 item 6).
  - Penetration, integrity and final-solved are judged over the whole 60 s, which is stricter than M1's 10 s.
- **How E1-1 is judged (implementation):**
  - The worker computes the pass flag as D14's `e11_pass` and 0 events of D11's detector (`d13_analyze.events`).
  - `e11_pass` is copied into `run.py`, and a test checks it equals D14's on R4's records.
  - M4's criteria then add rule 2 (magnet validity), as for every trial.
  - The verdict script re-derives the flag from the stored record and makes any disagreement INVALID.
- **Slip rule (Q4):** E1-1 passes only with **0 D11 slip events over 0–60 s**. A slip event is a change of 0.2° or
  more in any cubie's signed rotation about any of its faces across 200 ms, merged as in D11.
  - This tightens M5.
  - Disclosed: the definition was descriptive and post hoc (D11 PROTOCOL).
  - Rehearsal: 0 events in L0's 20 R2 rests, R3's 15 and R4's 20.
  - A slip failure is listed in `fail_reasons` only as "M1 criteria" (M4 replaces the list). Its own reasons are kept
    in `e11_fail_reasons`, which the report prints.

### 4.3 Reported only (never in Option A); all written by `analyze.py`
- **Turner torque per move** (E1-2 to E1-4): median, p99 and max (M5's report), counts above 0.2, 0.45 and 0.5 N·m,
  and moves at the clip.
- **Margins** (largest drift, penetration, |turn error|, 0–10 s rest rotation and turner torque) beside the R1 + R2
  and R4 maxima of §0 item 8 and the limits.
- **NoSlip-off E1-1** (§0 item 6): for E1-1, REST-X and the E1-7 rests, the warm-ups above 0.5° and the largest.
- E1-6n (M5's report); REST-X and slips over E1-1 + REST-X; E1-7 against R3's flags (R3's `noslip_ref=0` is M7's
  `noslip=0`) and the E1-7 rests; failed 60 s rests with their `e11_fail_reasons`.

### 4.4 Pass logic
- **Option A:** every §4.1–§4.2 criterion holds in 100 % of the 204 trials (E1-6m per move).
- **No exclusions, no reruns.**
- Verdict order: INVALID, then INCOMPLETE, then NOT PASSED, then PASS (M5 §5).
- **A failure is final.** It is documented in full, and G1 stays not passed.

## 5. Analysis
- **Primary:** the verdict of `E7_scored_m7/analyze.py`.
  - It is **M5's `analyze.py` loaded unchanged** on M7's runner: manifest, ledger, record, seed, gap, wall, table and
    environment checks, E1-4 scrambles, and Option A.
  - M7 adds per-record checks, each a violation (INVALID):
    - the mechanism label is "M7";
    - rounded edges with the registered radius;
    - the registered NoSlip count in the compiled options;
    - for turn trials, exactly one trial model and one NoSlip-wrapper call (none at NoSlip 0);
    - every 60 s rest is 60 s long, by its label and by its 2,400 samples, and its stored verdict equals the one
      re-derived from the record.
  - **A harness-exception record** (M5 §2, U1 iii) is exempt from the M7 checks, because it carries neither edge nor
    M7 block. It must fail (`pass` False); it is then an ordinary failing trial, not a violation (review 1, R1).
  - Expected counts are as in §3. A missing record gives INCOMPLETE; an extra one gives INVALID.
- **Secondary (reported):**
  - the margins;
  - the torque report;
  - slips over 60 seeds (E1-1 + REST-X), with the two-sided 95 % Clopper–Pearson interval. 0 / 60 gives an upper
    bound of about 6 % (0.0596);
  - E1-6n;
  - the E1-7 flips against R3;
  - the NoSlip-off warm-ups;
  - the run procedure.
- **No hypothesis test** decides the verdict.

## 6. Freeze and integrity (code: `5e74b69`, `090fc8f`, and the revision-2 code commit)
### 6.1 Code (`FACT`)
**`experiments/E7_scored_m7/run.py`.** It loads M4's and M5's runners unchanged in fresh module instances (`*_for_m7`),
as E6 did, and changes only module globals:
- **Seeds:** +7000 (range 17000–17999); smoke base 18000.
- **Folders, label and manifest:** folders `E7_scored_m7/results*`; mechanism "M7"; the manifest adds the edge
  radius, NoSlip and rest length.
- **Per-trial installs** (`install`, and `run_trial` wrapping `M4.run_trial`, which M5's `run_job` calls):
  - a `scored.Trial` subclass setting `edge_profile = "rounded"` and the radius, as `r1_run.install_edge`;
  - `scored.build_m1_xml` wrapped with D13's `with_noslip` when NoSlip > 0, as `d14s3_run.worker`;
  - both are rebuilt from the originals for every trial;
  - E1-7's `edge_radius` and `noslip` overrides are consumed here.
- **Kind `rest60`** (E1-1, the E1-7 rests, REST-X), following R2–R4's steps:
  - a 10 s warm-up E1-1 through M4's rest trial, with the edge and without NoSlip;
  - a magnet-system reset;
  - `d13_rest` (variant V2's NoSlip, the setting's parameters);
  - the pass flag as in §4.2.
- **E1-7 factors:** `chamfer` is replaced by `edge_radius` [1.8, 2.5, 3.6] mm, and `noslip` [0, 5, 10, 20] is added;
  the 15 rests and REST-X are appended to the job list.
- **`selfcheck` mode** (§6.2), which records the HEAD, whether the M7 paths are clean, and the SHA-256 of `run.py` and
  `analyze.py` (`provenance`; also printed by `run.py provenance`).
- **Guards:** every appended seed (E1-7 rests, REST-X) must lie in the active range; `all` and `smoke` refuse to start
  with less than 3 GB free disk.

**`experiments/E7_scored_m7/analyze.py`:** §5 and §4.3.

**Tests:** `tests/test_scored_m7.py`, 31 tests. They cover:
- isolation from M5's module instances, including that a fresh M5 runner keeps its own seeds, factors and
  `run_trial`;
- the counts, the "not run" set, and `v3_not_run` on M7's list;
- seeds, scrambles, the M5 + 7000 map, and **M5's committed scored manifest mapped onto M7's list** (438 keys, seed
  + 7000, equal overrides);
- the E1-7 factors and the `rest60` kinds;
- `e11_pass` equal to D14's on all 20 R4 records, with each of its seven conditions broken in turn, and its limits
  equal to `scored.THRESHOLDS`;
- the per-trial installs: radius, profile handed to the base class, and `noslip_iterations` in the XML;
- **every one of the 501 runnable jobs** through `run_trial` with stand-ins: its registered edge and NoSlip, and for
  rests the `d13_rest` cfg, unwrapped XML and 60 s;
- the rest60 path: overrides consumed, warm-up and rest installs, cfg, length, the stored verdict, and a genuine slip
  failing the rest;
- the M7 record checks, including harness-exception records (failing, not violations) and NoSlip 0;
- **the full verdict on synthetic runs** through M5's run procedure:
  - a complete valid set gives PASS;
  - an E1-1 slip gives NOT PASSED;
  - a failing REST-X rest gives PASS;
  - a reported-only harness exception gives PASS;
  - an Option A harness exception gives NOT PASSED;
  - an inconsistent stored rest verdict gives INVALID;
  - a missing record gives INCOMPLETE;
  - an extra record gives INVALID;
- the report text (M7 title, restated lines, new sections);
- the frozen paths, the self-check list, and Clopper–Pearson.

M5's tests pass in the same session, and so does the full repository suite.

**Frozen paths** (`M7_FROZEN_PATHS`): M5's (with M4's), plus:
- `src/rubiknetic/cube_physics/m1_model.py`;
- `d10_rest.py`, `d13_run.py`, `d13_analyze.py`, `d11_analyze.py`;
- this text;
- `E7_scored_m7/run.py` and `analyze.py`.

`r1_run.py` and D14's code are not imported. Their two functions are copied: the edge install, and `e11_pass`, which
is test-checked against D14's.

### 6.2 Self-checks before the first start (rehearsal seeds only; committed)
**Provenance (review 1, B-R8).** The revision-1 results below ran on code that differed from any commit:
- the self-check ran at `5e74b69` with the 16-trial list added but not yet committed (committed in `090fc8f`);
- the smoke ran at `e795a2c`, before the E7 code was committed.

**Both are re-run at the revision-2 code commit**, with provenance recorded. Those results replace these before the
text is fixed (§6.7).
| ID | Check | Result (`FACT`) |
|---|---|---|
| SC1 / SC2 | `run.py selfcheck`, rehearsal map (+6000): the first trial of each of the 10 Option A sub-experiments reproduces R1's or R2's committed L0 R25 record. For E1-1 that is R2's 60 s `rest_s16000` | **0 differences each** |
| SC3 | E1-7 `nominal__sexy6`, `edge_radius=0.0018__6move`, `noslip=5__6move`, `nominal__rest60` and `magnet_scale=0.67__rest60` reproduce R3's records | **0 differences each** |
| SC5 | E1-7 `magnet=none__6move`, the no-magnet path that E1-6n also uses, reproduces R3's record | **0 differences** (16 / 16 in all) |
| SC4 | The seed list equals M5's + 7000, lies in 17000–17999, and the scrambles come from 17400–17419 | unit tests pass |

- Comparison: `er9g_run.gs_diff` with the rehearsal's logging blocks and M7's bookkeeping fields removed on both sides
  (`run.py selfcheck_compare`). For rests, every field of the rehearsal's record must equal M7's.
- The result is committed as `results_selfcheck/selfcheck.json`.

### 6.3 Smoke run (`FACT`; `smoke_2026-11-25/`, log `smoke_2026-11-25.log`)
- M5's smoke list on 18000+.
- **Start 1** was killed after 5 records (`--stop-after 5 --stop-point after_link`), between writing the record and
  its ledger line.
- **Start 2** resumed with the same command. It moved 1 orphan, reconciled 1 ledger line and wrote the remaining 14
  (332 s).
- `analyze.py --smoke-dir`: **19 records, 2 starts, 0 integrity violations, 0 missing.**

### 6.4 Seed search (to be repeated and recorded before fixing)
- `git grep` and `rg --no-ignore` for `17[0-9]{3}` seeds across all files, as in the ER9 skeleton §9.2.
- `FACT` (2026-11-25): a scan of all 5,590 `.json`, `.json.gz` and `.jsonl` files under `experiments/`
  (decompressed) for `"seed": 17xxx` or `_s17xxx` found **0 matches**. Review 1's rescan of the current 5,814 such
  files (5,740 tracked + 74 ignored) also found 0.
- Tracked text and untracked files outside `experiments/` are still to be searched as above. `git grep` will hit
  synthetic `_s17xxx` keys in `tests/test_scored_m6.py` and `tests/test_scored_m7.py`. These stub the trial before any
  step and simulate nothing.

### 6.5 Review (Q8)
- Independent review of the text and the code together, until a review requires no changes (M5 precedent: 8
  reviews).
- Reviewers get no scored data, because none exists.

### 6.6 Cost and stop rules (`INFERENCE` from R1–R3 L0 wall times)
| Part | Estimate |
|---|---|
| Option A (204) | about 9.6 CPU-h (E1-4 about 6.2). R4 ran this list in 1 h 38 min on 6 workers |
| E1-6n | about 4–7 CPU-h |
| E1-7 + rests | about 3.8 CPU-h (R3) |
| REST-X | about 3.4 CPU-h |
| **Total** | **about 21–24 CPU-h; about 4–5 h on 6 workers** |
| Fresh-seed rehearsal (Q3, Option A only) | about 10 CPU-h; about 2 h |

- Cap: 35 CPU-h.
- The cost is projected again after 25 % of the trials. Over the cap, the run pauses for the user; it is never
  abandoned (INCOMPLETE is final).

### 6.7 Revision-2 evidence (re-run at the revision-2 code commit `d5ba4cd`; B-R8; `FACT`)
These replace the revision-1 results of §6.2 and §6.3 as the evidence for fixing. They ran with 2 workers, because
memory was held by paused jobs of another project; worker count does not affect results.

- **Self-check** (`results_selfcheck/selfcheck.json`):
  - HEAD `d5ba4cd`, M7 paths clean (`tree_clean_for_m7_paths` true);
  - SHA-256 `run.py` `f1c8f4ce…74d9a3`, `analyze.py` `9a6df235…d0d269`;
  - **16 / 16 trials, 0 differences**.
- **Smoke** (`smoke_rev2_2026-11-25/`, log `smoke_rev2_2026-11-25.log`): commit `d5ba4cd+smoke`.
  - Start 1 was killed after 5 records (`after_link`).
  - Start 2 resumed: 1 orphan moved, 1 ledger line reconciled, 14 records written (323 s).
  - M7's revision-2 verdict script (`--smoke-dir`): **19 records, 2 starts, 0 integrity violations, 0 missing**.
- **Tests:** at `d5ba4cd`, the 31 M7 tests and M5's 83 pass together (114).

## 7. Prerequisites before this text can be fixed
1. The user's answers to §8.
2. **Fresh-seed rehearsal (if Q3)** on 19000–19655 under this exact configuration, reported and committed before the
   text is fixed. **Done** (D15 R4, P-87): 204 / 204, both signals met.
3. The §6.1 code, SC1–SC5 and the smoke run, committed (**done**). The seed search is repeated as the last step
   before fixing.
4. Review(s) per Q8.
5. The user's approval, the Status-line commit, an idle machine and an explicit go.

**After a PASS:** E1-8 on a quiet machine, the abstraction write-up (§1), and the VALIDATION_PLAN sign-off.

## 8. Questions for the user (recommended default first; **all answered 2026-11-25, P-86**: the recommended option each time; Q8 = one reviewer subagent per round)
| # | Question | Recommended | Why |
|---|---|---|---|
| Q1 | Label | **M7** (unused; the ER9 skeleton's proposal for its arm is superseded) | Next free mechanism label |
| Q2 | Scored seeds | **M5 + 7000 → 17000–17655**; REST-X 17700–17739; smoke 18000–18099 | Never simulated; reserved since P-66 |
| Q3 | Fresh-seed unscored rehearsal before fixing | **Yes, Option A on 19000–19655 (about 2 h)** | Every choice was made on 16000–16999. M5 rehearsed 204/204 and then failed scored. Fresh seeds show the tails before the one-shot run |
| Q4 | Slip rule | **A criterion (0 events over 60 s)**, disclosed post hoc | NoSlip was adopted to remove slips. A pass with slips would undercut the claim. It tightens M5 and never loosens it |
| Q5 | E1-6n no-magnet arm | **Keep, reported** (M5 precedent) | Shows what the magnets contribute. R3 found L0 sequences pass even without magnets, which is worth confirming on fresh seeds |
| Q6 | E1-7 | **R3's list and rests, at seed 17000** | Same design as the rehearsal, so flips are comparable |
| Q7 | REST-X | **Yes, 40 × 60 s rests** | 20 rests cannot bound the slip rate usefully. 60 give a two-sided 95 % upper bound of about 6 % if 0 |
| Q8 | Review | **Answered: one reviewer subagent per round** (P-86), text and code together, iterated until no changes are required | CLAUDE.md forbids subagents by default, and the user permitted this one. M5 needed 8 rounds |
| Q9 | Turner torque | **Reported only** | A threshold now would be post hoc. The torque is uncalibrated (P-83) |

## 9. Response to review 1 (revision 2)
Every required item was checked against the code or records by the main session before it was acted on. The review
is [`M7_PREREGISTRATION_REVIEW1_2026-11-25.md`](M7_PREREGISTRATION_REVIEW1_2026-11-25.md).

**Required**

| Item | Verified | Change |
|---|---|---|
| A-R1 / B-R3: a harness-exception record made the run INVALID | yes: the checks ran before the early return | `analyze.py`: the exemption is first, and such a record must fail. Tests: exception records (seq, rest60, `noslip=0`, REST-X, an E1-7 rest) give no violation; synthetic runs give PASS for a reported-only exception and NOT PASSED for an Option A one (§5) |
| A-R2: undisclosed NoSlip dependence of E1-1 | yes: R2 3/20 and R4 1/20 warm-ups above 0.5° | §0 item 6, §1 abstractions and §4.2 state it; §4.3 and `analyze.py` report the NoSlip-off warm-ups |
| A-R3: the seed FACT went beyond its search | yes | §3 limits it to §6.4's scope; the full search stays `TODO` before fixing |
| A-R4 / B-R2: the start-log load claim | yes: M5's start log has no load | §2 corrected (`loadavg_start` per record) |
| A-R5 / B-R1: "about 5 %" | yes: 0.0596 two-sided | §5 and Q7 say about 6 % (two-sided 95 %) |
| B-R4: CAD gap 0.25 mm miscited and contested | yes: `side_checks/README.md:56` against `CUBE_MECHANISM_FINDINGS.md:71` | §0 item 3 cites both, `UNVERIFIED` |
| B-R5: unlabelled speedcube-edge claim | yes: P-78 says edge geometry is unverified | §0 item 5 relabelled `UNVERIFIED` |
| B-R6: rest60 path untested | yes | Tests for the rest60 path (installs, cfg, 60 s, verdict) and a genuine slip failing the rest |
| B-R7: no full-verdict tests for M7 | yes | Synthetic-run tests: PASS, NOT PASSED, INCOMPLETE and INVALID cases (§6.1) |
| B-R8: evidence not tied to commits | yes | Disclosed in §6.2; self-check and smoke re-run at the revision-2 code commit with provenance (§6.7) |

**Optional (adopted unless stated)**
- **A-O1:** stub test over all 501 jobs.
- **A-O2:** provenance; see B-R8.
- **A-O3:** not adopted as a check. The equality of E1-7 `nominal__rest60` and E1-1 `rest_s17000` under worker reuse
  is reported in the scored write-up.
- **A-O4:** rest length is checked by sample count. Re-deriving the 0–10 s rotation is not adopted: the stored scalar
  comes from D13's own code, which is frozen.
- **A-O5:** `e11_pass` is tested on all 20 records with each condition broken, and its limits against
  `scored.THRESHOLDS`.
- **A-O6:** `e11_fail_reasons` are printed.
- **A-O7 / B-O8:** margins beside the rehearsals, E1-7 against R3, and torque counts are written by `analyze.py`.
- **A-O8:** a seed-range assert on the appended jobs.
- **A-O9:** a report-template guard and test.
- **A-O10:** the disk guard; the storage is noted in §2.
- **A-O11:** noted. B1's ball joints make pop zero for either edge; R4's largest per-move pop is 8.3e-14 mm.
- **A-O12:** test restores via a fixture.
- **B-O1:** file count and the synthetic test keys noted (§6.4).
- **B-O2:** the E1-5s seeds corrected.
- **B-O3:** GS1 attributed to ER9 Part G.
- **B-O4:** software provenance cited.
- **B-O5:** switch timing relabelled `INFERENCE`, citing lines 11-13 and the edit audit.
- **B-O6:** labels `ASSUMPTION` and `UNVERIFIED` added.
- **B-O7:** the tag mapping is stated.
- **B-O9:** tests strengthened (M5 manifest map, `v3_not_run`, isolation, record-check cases, profile and XML
  checks).
