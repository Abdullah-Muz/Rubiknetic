# Phase 1 (G1) Pre-registration: M7, the L0 magnetic contact cube with rounded edges and NoSlip 10

**Status: DRAFT, revision 0, NOT APPROVED. Nothing here is in force.** §8 was answered on 2026-11-25 (P-86):
Q3 yes, Q4 criterion, Q8 one reviewer subagent per round, and the defaults for Q1, Q2, Q5, Q6, Q7 and Q9. The text
is revised after the fresh-seed rehearsal (§7 item 2). Written by the main session on 2026-11-25,
after P-83 (L0 chosen as the working candidate) and P-85 (R3, the E1-7 rehearsal). It is built from:
- `PHASE_1_M5_PREREGISTRATION.md`, revision 8, the last text in force (it governed M5's scored run);
- the ER9 skeleton `ER9_anchored_core_layouts/proposals/G1_SCORED_PREREG_DRAFT.md`. That skeleton was written for a
  Part G arm (PG8/PG20) and is superseded for that purpose by P-83. It is kept as a source.

No simulation was run for this draft, and no scored seed was touched.

**Path to force (as M5's, PROPOSAL):**
1. The user settles §8's questions.
2. The text is revised.
3. The §6 code is built and self-checked on rehearsal seeds.
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
3. **Clearance.** The 0.05 mm piece gap is an `ASSUMPTION` (M5 §0 item 3). The CAD's piece gap is 0.25 mm, and real
   cube clearances are unverified (P-77).
   - R3 shows drift fragility at 0.1 mm: 1.005–1.095° against ≤ 1.0°.
   - M5 §4 already expected that flip from P-25.
4. **Turning torque is uncalibrated (P-83 (2)).**
   - The only verified real figure is 0.09 N·m. A snippet-only bracket suggests 0.10–0.20 N·m
     (`docs/research/TURNING_TORQUE_FINDINGS.md`, addendum 2026-11-25).
   - L0's R2 turner median is 0.103 N·m and its max 0.185 N·m.
   - Torque is reported, never judged (§4.3).
5. **Rounded edges are a modelling choice.**
   - Real speedcube pieces are rounded or bevelled at their edges (corner cutting), but R 2.5 mm was chosen because
     it removed the chamfer's catch (P-78–P-80), not from a measured profile.
   - R3 shows the outcome holds over R 1.8–3.6 mm.
   - Static checks: the magnets keep the 0.4 mm wall at those radii, and V4–V6 pass (`r3_static.json`).
6. **NoSlip 10 is a solver setting chosen post hoc** (P-73). R3 shows the outcome holds over NoSlip 5–20 and, for
   sequences, with NoSlip off.
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
| Magnets | **M5's 48 × 4×2 mm N35** at M5's positions, with M5's table and V3 record (validated near-pair tilt 5°). Identical to M5 | `FACT`, M5 §1; L0 = M5 magnets (ER7 GS1) |
| Turner | M1's rig: turn_kp 5, kv 0.2, torque clip 1 N·m. Clip = peak ≥ 0.999 N·m | `FACT`, M5 §1, §4 |
| Execution path | M5's runner (`E5_scored_m5/run.py`) loaded unchanged, as ER7 did, plus the two installs above. R3's gate 1 and smoke equivalence show this path reproduces the ER9-path records exactly (0 differences) | `FACT`, R3 (P-85) |
| Software | MuJoCo 4.0.1, Python 3.12.3, NumPy 2.5.4, SciPy 1.18.1, in WSL Ubuntu 24.04 (`~/.venvs/rubiknetic`) | `FACT`, every R2/R3 record |

**Abstractions (to be published with any verdict; VALIDATION_PLAN G1 "Pass"):**
- The cube is contact-emergent (B1). There are no switched constraints, so the "switch timing" item does not apply.
  TODO: confirm in `M1Params`.
- B1 has no radial freedom, so there is no magnetic preload.
- Magnets have no collision geometry.
- The ideal-magnet law may overstate force by up to 1.5× (M5 §7; D8 V2). E1-7's 0.67 scale covers this (passed, R3).
- NoSlip is a solver post-process that removes contact slip velocity. It is a numerical choice, not a physical law,
  and its effect is bounded by R3's NoSlip 5 / 20 / 0 arms.
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
- **Location check** as M5 revision 8: no path in a OneDrive folder. Additionally (PROPOSAL), the run must execute in
  the recorded WSL environment, and every record's environment block is compared with the manifest.
- **No other jobs in WSL** during the run (P-82 (b)). The start log records the load at start.

## 3. Trials and seeds (PROPOSAL)
**Seed map: M5 scored seed + 7000** (17000–17655). Q2.
- `FACT`: no record anywhere uses 17000–17999 (seed search in §6.4 below, to be repeated before fixing).
- D12's and Part G's runners refuse that block in code. The lapsed M6 draft and the never-run E6 runner named it
  (P-66).

| Sub-exp. | Content (M1/M4/M5) | Trials | Seeds | In Option A |
|---|---|---|---|---|
| E1-1 | Rest, **60 s instrumented** (D14 Stage 1's steps, as R2). M1's criterion is applied to 0–10 s; slip events over 0–60 s per Q4 | 20 | 17000–17019 | yes |
| E1-2 | Quarter turns, 6 faces × CW/CCW × 2 | 24 | 17100–17123 | yes |
| E1-3 | Half turns | 22 | M5 list + 7000 | yes |
| E1-4 | 20 × sexy6; 20 × scramble(20, s) + inverse (scrambles from 17400–17419) | 40 | M5 list + 7000 | yes |
| E1-5 | U offset 0…20°, both signs, then R | 42 | 17500–17541 | yes |
| E1-5s | Snap-back from ±1, 2, 3, 5, 8°, 2 seeds | 20 | M5 list + 7000 | yes |
| E1-6a/b/c | Open pad (6), opposed torques (6), corner twist (8) | 20 | M5 list + 7000 | yes |
| E1-6t | Toy-standard torque 0.45 N·m | 16 | 17640–17655 | yes |
| E1-6m | Energy and impulse per move of E1-2 to E1-4 | (moves) | — | yes (⟨P⟩) |
| **Total Option A** | | **204** | | |
| E1-6n | No-magnet rerun of E1-2 to E1-6t on the same seeds (Q5) | 184 | as above | never |
| E1-7 | R3's list: M5's factors with edge radius 1.8 / 3.6 mm in place of the chamfer, NoSlip 5 / 20 (+ 0 reference), both sequences; plus R3's 15 one-seed 60 s rests (Q6) | 58 (+2 not run, V3) + 15 | 17000 | never |
| REST-X | 40 extra 60 s rests (E1-1 configuration), reported (Q7) | 40 | 17700–17739 | never |
| E1-8 | Throughput on a quiet machine, after the verdict | — | — | sign-off only |

- The exact list is M5's runner list + 7000, checked by a unit test (as M5 §2).
- **Smoke seeds:** 18000–18099.
- **Fresh-seed rehearsal (Q3):** 19000–19655.
- 10000–10999 (M5's scored range) and 16000–16999 (rehearsal) are never used in scored mode.

## 4. Criteria (stated before any data)
### 4.1 Inherited unchanged (`FACT`: M1 §4, M4 §4 with Amendment 1 A2, M5 §4)
- **E1-1:**
  - solved and valid;
  - rest rotation ≤ 0.5° over the first 10 s;
  - radial offset ≤ 0.5 mm;
  - pop ≤ 0.3 mm;
  - penetration ≤ 0.5 mm.
- **E1-2 and E1-3:** oracle agreement; turn error ≤ 2°; non-target drift ≤ 1°; penetration ≤ 0.5 mm; pop ≤ 0.3 mm;
  causality.
- **E1-4:** E1-2's criteria per move, every state agreeing with the oracle, and a growth slope < 0.005°/move.
- **E1-5:** categorical: never an illegal or oracle-mismatched state.
- **E1-5s:** from ≥ 3°, |U error| ≤ 0.5° after 1 s. TODO: name M5's frozen function, since two definitions exist
  (ER9 SUMMARY).
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
- **Slip rule (Q4):** E1-1 passes only with **0 D11 slip events over 0–60 s**. A slip event is a change of 0.2° or
  more in any cubie's signed rotation about any of its faces across 200 ms, merged as in D11.
  - This tightens M5.
  - Disclosed: the definition was descriptive and post hoc (D11 PROTOCOL).
  - Rehearsal: 0 events in L0's 20 R2 rests and in R3's 15.

### 4.3 Reported only (never in Option A)
- **Turner torque per move** (E1-2 to E1-4): median, p99 and max, and counts above 0.2, 0.45 and 0.5 N·m and at the
  clip. Shown beside R2's L0 values.
- E1-6n, E1-7 (flips are fragilities), REST-X.
- Margins against every threshold, beside the §0 item 8 rehearsal maxima.

### 4.4 Pass logic
- **Option A:** every §4.1–§4.2 criterion holds in 100 % of the 204 trials (E1-6m per move).
- **No exclusions, no reruns.**
- Verdict order: INVALID, then INCOMPLETE, then NOT PASSED, then PASS (M5 §5).
- **A failure is final.** It is documented in full, and G1 stays not passed.

## 5. Analysis
- **Primary:** the verdict of the frozen `analyze.py`, M5's with M7's folders, seeds, the slip rule and E1-1's
  60 s record format. Expected counts are as in §3. A missing record gives INCOMPLETE; an extra one gives INVALID.
- **Secondary (reported):**
  - the margins;
  - the torque report;
  - slips over 60 seeds (E1-1 + REST-X), with a 95 % Clopper–Pearson interval. 0/60 gives an upper bound of about
    5 %;
  - E1-6n;
  - the E1-7 flips against R3;
  - the run procedure.
- **No hypothesis test** decides the verdict.

## 6. Freeze and integrity (TODO)
### 6.1 Code
A new `experiments/E7_scored_m7/run.py`:
- It loads M5's runner unchanged in its own module instance and patches only:
  - the seeds and the smoke seeds;
  - the edge install (`r1_run.install_edge`);
  - the NoSlip wrapper;
  - E1-1's 60 s rest steps (R2's);
  - the R3 E1-7 list and rests;
  - REST-X;
  - the label, folders and frozen paths.
- `analyze.py` is M5's with the §5 changes.
- Tests are ported from `test_scored_m5.py`, plus R3's proof checks on every record (edge, NoSlip, magnet parameters,
  seed).
- Frozen paths: M5's, plus `m1_model.py`, D13's `with_noslip` and `d13_rest`, D14 Stage 1, `r1_run.py`
  (`install_edge`), the new runner, `analyze.py`, the tests and this text.

### 6.2 Self-checks before the first start (rehearsal seeds only; committed)
| ID | Check | Pass |
|---|---|---|
| SC1 | In self-check mode with the rehearsal seed map (+6000), the runner reproduces R1/R2's L0 R25 record for the first trial of each sub-experiment | 0 differences (`gs_diff`, logging stripped) |
| SC2 | It reproduces R2's L0 `rest_s16000` (60 s) | 0 differences |
| SC3 | It reproduces R3's `nominal__sexy6` and one non-nominal E1-7 record | 0 differences |
| SC4 | The seed list equals M5's + 7000, lies in 17000–17999, and the scrambles come from 17400–17419 | unit test |
| SC5 | The E1-6n model equals M5's no-magnet model plus edge and NoSlip (static comparison) | identical |

### 6.3 Smoke run
- Seeds 18000–18099, every trial kind, with one forced interruption and a resume (M5 precedent).
- It measures steps/s and memory.

### 6.4 Seed search (to be repeated and recorded before fixing)
- `git grep` and `rg --no-ignore` for `17[0-9]{3}` seeds across all files, as in the ER9 skeleton §9.2.
- `FACT` (2026-11-25, this draft): a scan of all 5,590 `.json`, `.json.gz` and `.jsonl` files under `experiments/`
  (decompressed) for `"seed": 17xxx` or `_s17xxx` found **0 matches**. Tracked text and untracked files outside
  `experiments/` are still to be searched as above.

### 6.5 Review (Q8)
- Independent review of the text and the code together, until a review requires no changes (M5 precedent: 8
  reviews).
- Reviewers get no scored data, because none exists.

### 6.6 Cost and stop rules (`INFERENCE` from R1–R3 L0 wall times)
| Part | Estimate |
|---|---|
| Option A | about 9.6 CPU-h (E1-4 about 6.2) |
| E1-6n | about 4–7 CPU-h |
| E1-7 + rests | about 3.8 CPU-h (R3) |
| REST-X | about 3.4 CPU-h |
| **Total** | **about 21–24 CPU-h; about 4–5 h on 6 workers** |
| Fresh-seed rehearsal (Q3, Option A only) | about 10 CPU-h; about 2 h |

- Cap: 35 CPU-h.
- The cost is projected again after 25 % of the trials. Over the cap, the run pauses for the user; it is never
  abandoned (INCOMPLETE is final).

## 7. Prerequisites before this text can be fixed
1. The user's answers to §8.
2. **Fresh-seed rehearsal (if Q3)** on 19000–19655 under this exact configuration, reported and committed before the
   text is fixed. **Done** (D15 R4, P-87): 204 / 204, both signals met.
3. The §6.1 code, SC1–SC5, the smoke run, and the seed search, all committed.
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
| Q7 | REST-X | **Yes, 40 × 60 s rests** | 20 rests cannot bound the slip rate usefully. 60 gives a bound of about 5 % if 0 |
| Q8 | Review | **Independent review by a fresh session**, text and code together, iterated until no changes are required. Options: a separate Claude Code session you start, or up to 2 subagents if you allow them (as P-73) | CLAUDE.md forbids subagents by default. M5 needed 8 rounds |
| Q9 | Turner torque | **Reported only** | A threshold now would be post hoc. The torque is uncalibrated (P-83) |
