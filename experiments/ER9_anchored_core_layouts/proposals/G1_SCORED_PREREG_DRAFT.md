# DRAFT — not approved

# Phase 1 (G1) scored pre-registration, skeleton: [LABEL — "M7" proposed], Part G commercial-pattern cube

**What this is.** A skeleton for the scored pre-registration that would follow a successful ER9 Part G full rehearsal
(PROTOCOL G.9). A subagent drafted it on 2026-11-22, **before any Part G probe result existed**. It is modelled on
`experiments/PHASE_1_M5_PREREGISTRATION.md` (revision 8, the last text in force) and updated for what ER7–ER9 learned.
No simulation was run, no other file was changed, and nothing was committed. Nothing here is a decision, a criterion
in force, or a result. It cannot take effect: see §7 for what must happen first.

**What was read.** Only the files listed in §9. Under `experiments/ER9_anchored_core_layouts/results/hybrid_g/`, only
the committed static results summarised in `PART_G_NEXT_STEPS_DRAFT.md` §0 and commit messages were used. No probe,
rest40, full or smoke record was opened. The one exception is disclosed in §9.2: a seed-pattern search touched three
committed self-check files there, with no match. Every arm-specific choice is a placeholder in square brackets:
`[ARM — from G.9 / user]`, `[GRADE]`, `[D_VAL]`, `[FIT — F-B / F-C, user]`, `[COMMIT …]`.

**Labels.**
- `FACT`: stated in the named file and section.
- `INFERENCE`: reasoning or hand arithmetic, not computed by project code.
- `PROPOSAL`: needs the user's approval.
- `TODO`: work or a number still to be produced.

---

## 1. Status, scope, and what a pass would and would not establish

### 1.1 Status
- FACT (DECISION_LOG, G1 gate row): G1 is **IN PROGRESS — NOT PASSED** for M1, M4 and M5, and M2 has no valid scored
  run. No mechanism has passed G1. What any G1 pass still needs:
  - a mechanism that passes a pre-registered scored battery;
  - E1-8 for that mechanism;
  - the mechanism abstraction and its limitations published;
  - the user's sign-off with the VALIDATION_PLAN fields.
- FACT (P-69, P-70; PROTOCOL Part G Status): Part G is exploratory and unscored. Its seeds are 16000–16999 only. A
  G.9 rehearsal that meets every signal is reported as "meets the rehearsal signals", **not as a candidate** (G.9
  "Reading").
- PROPOSAL: this text becomes a candidate pre-registration only after every §7 item is closed. Its path to force is
  M5's:
  - the user approves the text;
  - independent reviews of the text and the code together continue until one requires no changes;
  - the §6 items are committed;
  - the runner checks for a clean commit;
  - the user gives an explicit go (P-63: the main session "stops before starting any scored run").
- **Freeze rule** (as M5 Status, R5). Once approved, this text changes only:
  - to make changes that an independent review requires; or
  - by a dated amendment the user approves before any scored trial.

  Thresholds are never loosened after a failure (VALIDATION_PLAN, threshold policy).

### 1.2 Scope
- **Mechanism.** One configuration: `[ARM — from G.9 / user]` (PG8 or PG20, or a §2 variant of
  `PART_G_NEXT_STEPS_DRAFT.md` only if one was rehearsed under P-70 item 1), at core grade `[GRADE]`. It is fixed by
  the G.9 rehearsal that precedes this text, and by the fresh-seed rehearsal if the user approves Q3.
- **Basis.** M5 revision 8, and through it M4 (with Amendment 1 item A2) and M1. Every rule, criterion, threshold and
  run-procedure item is M5's unless §2–§6 say otherwise.
- **What this text changes relative to M5** (exhaustive, C1 of the gap analysis):
  1. the magnets (composite system, §2);
  2. the validated-regime rule, from one tilt limit to the per-class rule of G.4;
  3. the seeds (§3.3);
  4. the E1-1 instrumented 60 s rest, and the slip rule (§4.2, Q4);
  5. the reported-only control arms, rest extension and derated block (§3.2, Q5–Q7);
  6. the E1-7 factors (§3.4);
  7. the torque report's reference levels (§3.5);
  8. the label, folders and frozen paths (§6).

  None of these loosens an M1, M4 or M5 criterion. Changes 2 and 4 tighten M5 (INFERENCE, §4.3).

### 1.3 What a PASS would and would not establish
| Would establish (if PASS, plus E1-7, E1-8 and sign-off) | Would **not** establish |
|---|---|
| The simulated B1 contact cube with `[ARM]`'s magnets meets M1/M4/M5's Option A battery on held-out seeds, with every magnet pair inside its class's validated regime (G.4, `[D_VAL]`) | A buildable cube. Under F-A the geometry is L0's and C52's, not the CAD's. Fit holds only under `[FIT]`, and under F-C only against a threshold chosen after the misses were seen (§2.4) |
| Turns driven only by the rig turner's contact torque, with the edit audit, the observed-move oracle, causality and the energy/impulse accounting (E1-6m) holding | Realistic turning torque. The turner is reported against about 0.2 N·m, not judged (P-67 item 4) |
| Rest without D11 slip events (if Q4 makes it a criterion) and snap-back ≤ 0.5° from ≥ 3° | Real magnet strength (ideal-magnet law; up to 1.5× overstated, D8 V2). The 0.67 arm and the derated block (§3.4, Q7) measure sensitivity only |
| A G1 **candidate** for the user's sign-off (VALIDATION_PLAN G1 "Pass") | Radial play, magnetic preload, or the commercial use of repelling magnets: B1 has no radial freedom (G.10) |
| | Real piece clearance: 0.05 mm is an `ASSUMPTION`, against 0.25 mm in the CAD (M5 §0 item 3; gap analysis A8) |
| | Anything about Phase 2: the rig turner is not an xArm7 grasp. Nothing about RL |

---

## 2. Mechanism under test

### 2.1 Frozen configuration (placeholders)
| Group | Value | Basis |
|---|---|---|
| Cubies, rig, solver | M5 §1 unchanged: B1 (`radial_preload = 0`), piece gap 0.05 mm, implicitfast at 0.5 ms, M1's contact and solver settings | FACT, M5 prereg §1; PROTOCOL G.3 |
| Turner | M1's rig unchanged: turn_kp 5, kv 0.2, torque clip 1 N·m. Clip = peak ≥ 0.999 N·m (M5 review 2, P3) | FACT, M5 §1, §4 |
| Magnet system | Composite (`src/rubiknetic/cube_physics/magnets.py` at `[COMMIT — ≥ 6d00cda]`):<br>- **48 × 4×2 mm N35** at M5's positions, `layout(19 mm, 0.05 mm)` in `layout()`'s order (deviation 1), with M5's table;<br>- **[8 corner / 20] on-axis 4×3 mm core pairs**, `core_layout(MagnetParams(4 mm, 3 mm, [GRADE]), clearance = 2e-4)`, with M6's N52 table or its exact Br² rescaling;<br>- cross-type pairs as a point dipole with the far taper | FACT, PROTOCOL G.0 item 1, G.3; commit `6d00cda` |
| Arm wrapper | `er9g_layouts.py` (registry and lists), `er9g_stats.py` (per-class stats) | FACT, PROTOCOL G.12 |
| Tables | 4×2 N35 (M5), 4×3 N52 (M6), and derived grade or scale tables. SHA-256 of each in the manifest (M5 §2) | FACT, M5 §2; E6 README |
| Magnet count | PG8 64, PG20 88 | FACT, G.3 |
| Software | MuJoCo 4.0.1, Python 3.12, NumPy 2.5.4, SciPy 1.18.1, pytest 9.2.0 (PH1-01) | FACT, P-62 item 1 |

### 2.2 Force-law coverage by pair class (G.4), with the D_val in force
| Class | Members | Validated basis (FACT, G.4) | In regime if |
|---|---|---|---|
| CE | 4×2–4×2 on different pieces | M5's V3 record, 5° (the 7.5° extension failed, P-24); V3a covers face gaps 0.5–1.5 mm and lateral offsets 0–6 mm | tilt ≤ 5°; no clamped z (\|z\| < 2.1 mm); no perpendicular near pair |
| PC-on | 4×3 piece magnet with a 4×3 core magnet, d ≤ `[D_VAL]` | P-60 (real placement, c = 0.2 mm, grades by exact scaling); ER5 V3-turn; **P4.0 for PG8** (passes, `P4_0.json`) | tilt ≤ 20°; clamped z allowed; no perpendicular |
| PC-off | as PC-on, d > `[D_VAL]` | ER5 V3b, 7.5° | tilt ≤ 7.5°; no clamped z (\|z\| < 3.1 mm); no perpendicular |
| PP3 | 4×3–4×3 on two pieces | ER5 V3b, 7.5° | tilt ≤ 7.5°; no clamped z; no perpendicular |
| X | 4×2 with 4×3 | none (dipole only) | `cross_near` = 0 |

- **`[D_VAL]`** is the value P4.d gives for the selected arm under U2.
  - FACT: PG8's committed P4.d gives D_val = 12°, the largest displacement tested (commit `446f989` message).
  - PG20's P4.d was still running when this was written and was not read.
  - If an O5-type amendment (`PART_G_NEXT_STEPS_DRAFT.md` §1) is approved, that amendment is cited here. Otherwise
    none applies.
- **Path deviation** d(n) is as defined in G.4.
- **Disclosed limits that carry over** (G.10):
  - CE lateral offsets of 6–8 mm against V3a's 0–6 mm (as in M5);
  - X pairs beyond r2 use the dipole term only, as every pair does there;
  - U8's dipole error for X pairs at 7.3–8.2 mm is 3.4–7.4 % (FACT, P-69 U8).

### 2.3 Abstractions (P-58 and others), to be published with any verdict (VALIDATION_PLAN G1 "Pass")
- The magnets have no collision geometry. They sit at real-mechanism radii (22.04 / 21.95 mm) inside B1 piece volumes
  (FACT, P-58 (2); G.3).
- B1 has no radial freedom, so there is no magnetic preload (FACT, P-65 correction; G.10).
- The ideal-magnet law may overstate force by up to 1.5× (FACT, M5 §7; D8 V2).
- The integrator shows a bounded energy oscillation of about 10 % with core magnets at 0.5 ms (FACT, M6 SUMMARY; P-60).
- The magnet force law depends on pair order: stiffness changes by up to about 4 % with the order of a pair (FACT,
  Part G deviation 1). The trials use `layout()`'s order, as M5 and ER7 did.
- There are no switched constraints: the cube is contact-emergent (M1/B1). VALIDATION_PLAN's "switch timing" item is
  therefore not applicable, and the text must say why (INFERENCE; TODO: confirm in `M1Params`).

### 2.4 Fit status (U1) and disclosure
- FACT (P-69 U1; G.6 P3): under F-A the configuration is reported "fit not met". The misses are:
  - corner wall 0.175 mm against 0.4 mm;
  - core cover 0.202 / 0.292 mm against 0.4 mm.

  U1 requires fit "of the configuration taken to a scored pre-registration".
- `[FIT — F-B / F-C, user]`:
  - **F-B:** CAD-relative positions. That is a new configuration: new controls, a V3-turn at the new core gap
    (outside P-60), P1–P4 again, and a new probe and rehearsal (G.6 P3). Every number in this skeleton that comes
    from Part G would then be replaced.
  - **F-C:** a sourced minimum wall and cover.
    - FACT (commit `79572c6`, `docs/research/MAGNET_POCKET_WALL_FINDINGS.md`, compiled by a subagent and not yet
      spot-checked): no source gives a commercial speedcube magnet wall or cover. General moulding guides give
      1.0–3.8 mm, and micro-moulding reaches about 0.1 mm.
    - INFERENCE: a threshold fixed now would be post hoc (G.6 P3 F-C). It must be disclosed in §0.

### 2.5 Disclosure (to become §0 of the final text), in order
1. **Post-hoc chain** (FACT, from the decision log; gap analysis C2):
   - M5 failed on one rest trial (P-51);
   - D10, D11 and ER1–ER6;
   - M6, with the P-60 amendment made after its survey failed;
   - ER7: C52 failed snap-back, and L0 had 2 rest slips (P-65);
   - ER8 lapsed (P-66);
   - ER9 Parts A–D (W3), the side checks, and Part E (probe-only by amendment 3, decided after the probe report);
   - Part G: U1–U8 (P-69), with U6's waiver of ER3 criterion 1, deviations 1–2, and P-70's pre-commitments;
   - `[ARM]` selected from two arms on ER7's seeds (G.8);
   - `[P-70 item 3 outcome: paused / not triggered]`;
   - `[any O5 amendment]`;
   - `[FIT]`.
2. **Independence** (M5 §0 item 2; gap analysis C3).
   - Held out: the E1-4 scrambles, drawn from the new seeds.
   - Not held out: every other move string is fixed by M1 and was seen by M5's scored run, ER7, ER9 and Part G. Only
     their setup draws are new.
   - Seeds 16000–16655 were used for diagnostics and for selection several times over (G.10).
3. **The slip rule** (if Q4 adopts it) uses D11's 0.2° / 200 ms definition. That definition was "a descriptive choice
   made after D10" (FACT, D11 PROTOCOL Definitions).
4. **Clearance** 0.05 mm is an `ASSUMPTION` (M5 §0 item 3); the CAD's piece gap is 0.25 mm.
5. **Turner torque** `[G.9 median, p99, clip count]` against about 0.2 N·m (P-67 item 4). FACT: L0's median was 0.203 N·m
   and C52's 0.645 N·m over ER7's full runs (G.1, G.2); on the probe's E1-2 trials, 0.144 and 0.700 N·m
   (`PART_G_NEXT_STEPS_DRAFT.md` §4).
6. **Provenance.** The author has seen M5's scored results and all rehearsal data from ER7, ER9 and Part G. No change
   to this text may be made in light of scored results of this run.

---

## 3. Trial list

### 3.1 Scored battery (Option A) and reported arms
**Seed map (PROPOSAL, Q2): seed = M5 scored seed + 7000**, the map of the lapsed M6 draft, which was never simulated
(§9). The exact list is M5's runner list + 7000, checked by a unit test, as in M5 §2.

| Sub-exp. | Content (M1/M4/M5) | Trials | M5 seeds | Proposed seeds | Validity rule | In Option A |
|---|---|---|---|---|---|---|
| E1-1 | Rest. Frozen 10 s metric, plus D10's instrumented 60 s and D11 slip events | 20 | 10000–10019 | 17000–17019 | rule 2 (fails) | yes |
| E1-2 | Quarter turns, 6 faces × CW/CCW × 2 | 24 | 10100–10123 | 17100–17123 | rule 2 | yes |
| E1-3 | Half turns, 12 + 10 × `F2 B2 L2 R2 U2 D2` | 22 | 10200–10239* | 17200–17239* | rule 2 | yes |
| E1-4 | 20 × `R U R' U'`×6; 20 × scramble(20, s) + inverse | 40 | 10300–10419* | 17300–17419* (scrambles from 17400–17419) | rule 2 | yes |
| E1-5 | U offset 0…20°, both signs, then R | 42 | 10500–10541 | 17500–17541 | rule 2 | yes |
| E1-5s | Snap-back from ±1, 2, 3, 5, 8°, 2 seeds | 20 | 10551–10568* | 17551–17568* | rule 2 | yes |
| E1-6a/b/c | Open-pad command (6), opposed torques (6), corner twist (8) | 20 | 10600–10627* | 17600–17627* | a: rule 2; b, c: rule 3 (label) | yes |
| E1-6t | Toy-standard torque, 0.45 N·m | 16 | 10640–10655 | 17640–17655 | rule 3 | yes |
| E1-6m | Energy and impulse per move of E1-2 to E1-4 | (moves) | — | — | — | yes (⟨P⟩) |
| **Total Option A** | | **204** | | | | |
| E1-6n | No-magnet rerun of E1-2 to E1-6t on the same seeds; expected to jam at 0.05 mm (P-27) | 184 | as above | as above | — | **never** |
| E1-7 | Sensitivity (§3.4); every factor value × (U U' R R' F F' and `R U R' U'`×6) | `[N_E17 ≈ 50–60]` | 10000 | 17000 | none (E1-7 is under neither rule) | never |
| E1-8 | Throughput on a quiet machine | — | — | — | — | gates sign-off only |

\* Not every seed in the range is used; the exact list is the runner's, as in M5 §2.

### 3.2 Controls and reported-only additions (PROPOSAL; Q5–Q7)
**Argument.**
- L0 (frozen M5) and C52 are exact subsets of the composite under magnet type (b) (FACT, G.1; GS1 and GS2).
- The question Part G asks is whether core pairs remove L0's rest slips without C52's snap-back failure (G.1). On
  held-out seeds, only paired controls can attribute a difference to the core pairs. Rehearsal pairs are not
  independent of selection.
- Running the full 204 trials for both controls would add 20 h or more (L0 10.5 h, C52 9.5 h; G.11). That buys no
  Option A role, because L0's and C52's G1 status is already fixed (M5 NOT PASSED; C52 lapsed, P-66).
- **Default:** controls only where the question is.
- **Every control record:**
  - goes in its own arm folder;
  - carries `mechanism` = "L0-control" or "C52-control";
  - never enters Option A;
  - never changes M5's verdict, M6's lapsed status, or any threshold.

| Arm | Content | Trials | Seeds | Purpose |
|---|---|---|---|---|
| CTRL-L0 | E1-1 (with 60 s instrumented rest) | 20 | 17000–17019 | Paired rest and slip comparison |
| CTRL-C52 | E1-5s | 20 | 17551–17568 | Paired snap-back comparison |
| REST-X | Rest-only (E1-1 configuration, 60 s), for `[ARM]` **and** L0 | 40 + 40 | 17700–17739 | Power for slips over 60 seeds (U5's design; G.10: 0/20 has a 95 % upper bound of 17 %) |
| DERATE | `[ARM]` with every magnet force × 0.67 (both types): E1-1 and E1-5s | 20 + 20 | 17000–17019, 17551–17568 | Gap analysis A6, beyond E1-7's two sequences; ER8's C52d precedent |

INFERENCE (gap analysis A6; next steps §3 step 8): the 0.67 arm is a likely fragility. At 0.67, PG8's corner+edge
cluster moves toward L0's. It is reported as a fragility, never as a G1 failure.

### 3.3 Seeds: summary (PROPOSAL; verification in §9)
| Block | Use | Status (FACT, §9) |
|---|---|---|
| 17000–17655 (map), 17700–17739 (REST-X) | Scored run and its reported arms | Never simulated. The only earlier claim is the lapsed M6 draft and the unused E6 runner (P-66: "Seeds 17000–17999 remain unused"). D12 and the Part G runner refuse 17000–17999 in code |
| 18000–18099 | Smoke run | Named only by E6's unused runner (`SMOKE_SEED_BASE`), which never ran a smoke test (E6 README) |
| 19000–19655, 19700–19739 | Fresh-seed unscored rehearsal before fixing (Q3) | Named only in two drafts (gap analysis B1; next steps §3 step 7) |
| 16000–16655 | Self-checks (§6.3) reproducing G.9's records | Rehearsal range (ER7, ER9, Part G) |
| **10000–10999** | **Never** | M5's scored range: 440 records on 10000–10655, including E1-7 at seed 10000 (P-51). D10 reran 10000–10001 (P-52) and D11 reran 10000–10019. D12 (`d12_common.py:85`) and Part G (`er9g_run.py:93`) refuse the range always |
| 16700–16739, 16900–16999 | Never | Part G's U5 extension (P-69) and D12's reservation (P-68) |

### 3.4 E1-7 factors (PROPOSAL; Q8)
- **M1/M5 factors unchanged:** timestep, iterations, μ, frictionloss, chamfer, grip and misalignment as M1; piece gap
  0.025 / 0.05 / 0.1 mm as M5.
- **Magnet factors, adapted to the composite:**
  - **4×2 set as M5:** sizes 3×1.5 N35, 4×1.5 N35 ("not run: failed V3", as M5), 4×2 N35 nominal, and 4×2 N52; face
    gap 0.35 / 0.85 / 1.35 mm. Uses M5's committed V3 and pair-check records and M5's matching rule.
  - **Core grade** N35 / N42 / N52, covered by exact Br² scaling (M6 S1).
  - **Global strength scale** 0.67 / 1 on both magnet types. 4×2 at 0.67 uses M5's own 0.67 V3 record; 4×3 is
    covered by linearity.
  - **Magnet set** (optional, an ablation): none / 48 only / core only / both.
  - **No core-clearance factor:** only c = 0.2 mm has a V3-turn record (E6 README).
- **New gate.** Every arm that moves or resizes a magnet (piece gap, face gap, 4×2 size) gets a **P1-type static
  scan** before the first start (G.6 P1 stop rules, including the core-to-4×2 bound ≥ r2 and the cross piece-pair
  minimum ≥ r2 + 1.0 mm). If the scan fails, the arm is "not run: outside P1", a registered reason (M5 §4 pattern).
  - INFERENCE (hand arithmetic): at face gap 1.35 mm the wall grows by 0.25 mm, so the 4×2 magnets move inward by
    about 0.25 mm. For PG20 the hard bound would fall from 8.117 mm to about 7.87 mm, below r2. That arm is therefore
    likely "not run: outside P1" for PG20.
- E1-7 is complete when every arm has run or is "not run" for a registered reason (M5 §4).

### 3.5 Turner rig (frozen) and the torque report
- The rig is M1's, unchanged (FACT, P-67 item 4: "the frozen rig is unchanged").
- **Reported per move of E1-2 to E1-4:**
  - the peak turner torque, with its median, p99 and max;
  - the count of moves above 0.2 N·m (the P-67 realism reference), above 0.45 N·m and above 0.5 N·m (the warning
    level), and at the clip (≥ 0.999 N·m).

  These are shown beside M5's scored run, ER7's L0 and C52, and G.9's rehearsal of `[ARM]`. **No threshold.**
- E1-6t's 0.45 N·m test torque is a criterion. It is a separate quantity, and the coincidence with the warning level is
  disclosed.

### 3.6 Mapping to VALIDATION_PLAN G1 tests (FACT unless labelled)
| G1 test | Covered by |
|---|---|
| Logic: inverse identity, 4×, scrambles, invariants | PH1-02: two independent oracle models, 57 tests (DECISION_LOG; not yet signed off) |
| Quarter turns, both signs | E1-2 |
| Half and reverse turns | E1-3, E1-2 (CCW) |
| Nonparallel sequences incl. `R U R' U'` | E1-4 |
| No setter, teleportation or hidden actuator | M1 rule 2 (edit audit), rule 4 (observed-move oracle), causality; E1-6a |
| Switch timing, force/torque, angular velocity, penetration, continuity, solver sensitivity | No switches (INFERENCE, §2.3); torque report; penetration criteria; E1-6m; E1-7 timestep and iterations |
| CPU benchmark | E1-8 (sign-off only) |

---

## 4. Criteria (stated before any data)

### 4.1 Inherited unchanged (FACT: M1 §4, M4 §4, M5 §4)
- **E1-1:**
  - solved and valid;
  - rest rotation ≤ 0.5° over the first 10 s;
  - radial offset ≤ 0.5 mm;
  - pop check ≤ 0.3 mm;
  - penetration ≤ 0.5 mm.
- **E1-2, E1-3:** oracle agreement; turn error ≤ 2°; non-target drift ≤ 1°; penetration ≤ 0.5 mm; pop check ≤ 0.3 mm;
  causality.
- **E1-4:**
  - every intermediate state agrees with the oracle, and the final state is solved;
  - the per-move criteria of E1-2;
  - growth slope < 0.005°/move.
- **E1-5:** categorical: never an illegal or oracle-mismatched state.
- **E1-5s:** from ≥ 3°, \|U error\| ≤ 0.5° after 1 s.
  - TODO: name M5's frozen function. Two snap-back definitions exist; L0 gives 0.269° under one and 0.118° under the
    other (FACT, ER9 SUMMARY Part C notes).
- **E1-6a:** rotation ≤ 0.5°; the state stays solved.
- **E1-6b:** categorical; radial change ≤ 0.5 mm.
- **E1-6c:** M1's categorical criterion (M4 A2).
- **E1-6t:** solved after release; penetration ≤ 0.5 mm.
- **E1-6m:** ⟨P⟩ \|W_mag + ΔU_mag\| ≤ 10 % of the magnet energy exchanged + 0.05 mJ, per move.
- **Run-integrity rules:** M1 rules 1–5 (clean commit, edit audit, numerical failure, observed-move oracle, no
  exclusions) and M4 rule 1 (magnet callback check).

### 4.2 New or changed (PROPOSAL)
- **Magnet validity, per class (replaces M5's single tilt).**
  - G.4's `out_of_regime` function, with `[D_VAL]`.
  - **Rule 2:** an operational trial (E1-1 to E1-5, E1-5s, E1-6a) with any out-of-regime evaluation **fails**.
  - **Rule 3:** an abuse trial (E1-6b, E1-6c, E1-6t) is labelled "magnet model outside validated range". The label
    does not fail the trial by itself, and the E1-6n twin is the bound.
  - Every record stores the per-class stats and the legacy `MagnetSystem.stats` (G.4).
- **Slip rule (Q4; default: a criterion).** E1-1 passes only with **0 D11 fast slip events over 0–60 s**: no change
  of 0.2° or more in any cubie's signed rotation about any of its faces across 8 consecutive samples (200 ms), using
  D11's merge rule (FACT, D11 PROTOCOL Definitions).
  - This tightens M5.
  - Disclosed: the definition was descriptive and post hoc (§2.5 item 3).
  - Alternative: report only, as in the lapsed M6 draft §4.

### 4.3 Pass logic
- **Option A.** Every criterion in §4.1–§4.2 holds in 100 % of the 204 trials (E1-6m per move).
- The following never enter Option A: E1-6n, E1-7, the CTRL-L0, CTRL-C52, REST-X and DERATE arms, and the torque
  report.
- INFERENCE: the per-class rule is stricter than M5's for CE pairs, because it adds the clamped-z and perpendicular
  clauses (G.4 against M4 rule 2). Disclosed as a tightening.

### 4.4 What counts as a failure or an exclusion
- **No exclusions, no reruns** (M1 rule 5; M5 §5).
- **Harness exceptions** other than a refusal, `MemoryError` or `OSError` become **failing records** with the full
  job metadata, and are never retried (M5 §2, U1 (iii)).
- `MemoryError`, `OSError`, a refusal raised during a trial, a killed worker or a stopped parent is an
  **interruption**: no record is written, and the trial runs on resume.
- Verdict order: **INVALID**, then **INCOMPLETE**, then **NOT PASSED**, then **PASS** (M5 §5). Only PASS can lead
  to G1, and only with §1.1's remaining items.
- **A failure is final.** It is documented in full, and G1 stays not passed. A scripted rotation is never a
  fallback.

---

## 5. Analysis plan

### 5.1 Primary
- The verdict of the frozen `analyze.py` (§6.1), with every M5 §5 integrity check, adapted to the new arms and folders.
- Expected counts:
  - E1-1 20, E1-2 24, E1-3 22, E1-4 40, E1-5 42, E1-5s 20, E1-6a 6, E1-6b 6, E1-6c 8, E1-6t 16;
  - plus the reported arms' registered counts.

  A missing record gives INCOMPLETE; an extra one gives INVALID.

### 5.2 Secondary, reported (pre-declared; none can change the verdict)
1. Margins against each threshold:
   - largest rest rotation, drift, turn error, penetration, pop and snap-back error;
   - growth slope;
   - E1-6m ratio.

   Each is shown beside G.9's rehearsal maxima. M5's rest failure came at 0.560° against a rehearsal maximum of
   0.290° (FACT, P-51).
2. The turner-torque report (§3.5).
3. **Slips:** slip seeds out of 60 (E1-1 plus REST-X) for `[ARM]` and for L0:
   - counts with 95 % Clopper–Pearson intervals;
   - a one-sided Fisher exact test.

   Pre-declared reading, as in G.8: "fewer slips than L0" if p ≤ 0.05 and the count is lower; otherwise "not
   distinguishable".
   - INFERENCE (next steps §4): if `[ARM]` has 0/60, the test can show a difference only if L0 has ≥ 5/60.
4. **Paired rest rotation** against CTRL-L0 on 17000–17019: an exact sign test, one-sided (arm lower), ties dropped.
5. **Paired snap-back error** against CTRL-C52 on E1-5s: an exact sign test, one-sided.
6. **Per-class regime stats:**
   - the largest d;
   - the legacy 20° proxy flag;
   - rule-3 labels, with the E1-6n E1-6b, E1-6c and E1-6t outcomes beside them (M5 §5).
7. DERATE and the E1-7 flips, reported as fragilities.
8. E1-6n: what the magnets change.
9. Run procedure: starts, records per start, orphans moved and ledger lines reconciled (M5 §5).

### 5.3 Statistics and multiplicity
- **The primary verdict is a deterministic all-pass rule, with no hypothesis test**, so no multiplicity correction
  applies to it.
- **Secondary tests** form one family of three: items 3, 4 and 5. Raw p and Holm-adjusted p (family α = 0.05) are
  both reported. All three are descriptive.
- **The forking paths are disclosed:**
  - INFERENCE: at least 12 arms have been run on ER7's seeds (L0, C52, the five anchored arms of Parts B–C, HB1–HB3,
    PG8, PG20).
  - Fresh scored seeds, and the Q3 fresh-seed rehearsal, are the remedy. No statistical adjustment is claimed.
- **Prior chance of a full pass** (INFERENCE, gap analysis §5.1): about 0.5 even after a 204/204 rehearsal (Laplace),
  because Option A has no tolerance for a single failure.

---

## 6. Freeze and integrity

### 6.1 Code and frozen paths (TODO; `[COMMIT …]` placeholders)
- **Runner:** a new `experiments/[E7_scored_m7]/run.py`. It loads M5's runner unchanged in module instances of its own,
  as E6 does (FACT, E6 README). It patches only:
  - the seeds and smoke seeds;
  - the composite installation via `er9g_layouts`;
  - the tables with their SHA-256 checks;
  - the G.4 per-class rule via `er9g_stats`;
  - the V3 and P1 arm rule (§3.4);
  - the E1-7 factors;
  - the E1-1 instrumented rest and D11 counting;
  - the reported arms;
  - the label, folders and frozen paths.
- **Also:** `analyze.py` and tests ported from `tests/test_scored_m6.py` (45 tests) and `test_scored_m5.py`.
- **Frozen paths:**
  - M5's;
  - `src/rubiknetic/cube_physics/magnets.py` at `[COMMIT]`;
  - `er9g_layouts.py` and `er9g_stats.py`;
  - D11's slip-count code `[path]`;
  - the new runner, `analyze.py` and tests;
  - this text;
  - every V3, pair-check, P1/P3/P4.0/P4.d record of `[ARM]`, the E1-7 P1-type scans, M6's `m6_checks.json`, and the
    composite V5/V6 record (§7).
- PROPOSAL: freeze the two `er9g_*` modules by path rather than move them into `src/`, so that GS1–GS4's evidence
  stays valid for the code that runs.
- **Commits:**
  - `[COMMIT — text]`, `[COMMIT — code]`;
  - the Status-line commit before the first start (M5 review 6, X6);
  - no commit touches the frozen paths or the results folders during the run (M5 §2).

### 6.2 Run procedure
M5 §2 unchanged (FACT):
- record key (arm, experiment, trial ID);
- one first start, with empty folders;
- an immutable manifest holding the trial list, the "not run" set, the table SHA-256s and the environment;
- an append-only start log and ledger;
- atomic records written by the parent process only;
- the resume rule with steps (i) and (ii);
- the location check (no OneDrive path; package from this repository);
- INVALID and INCOMPLETE are final.

### 6.3 Self-checks before the first start (on rehearsal seeds only; committed)
| ID | Check | Pass |
|---|---|---|
| SC1 | The scored runner in self-check mode, with the rehearsal seed map, reproduces G.9's `[ARM]` records: the first trial of each of the ten sub-experiments | 0 differences outside G.5's metadata list |
| SC2 | The CTRL-L0 path reproduces ER7's L0 records (as GS1) | as SC1 |
| SC3 | The CTRL-C52 path reproduces ER7's C52 records (as GS2) | as SC1 |
| SC4 | The stats diagnostic changes no physics field (GS4-like, one E1-2 trial) | identical |
| SC5 | Every derived table equals its base × the exact factor (M6 S1) | ≤ 1e-12 relative |
| SC6 | The E1-6n model equals M5's no-magnet model, by a static comparison of the model and its parameters | identical; no simulation on 10000–10999 |
| SC7 | The seed list equals M5's list + 7000, lies in 17000–17999, and the E1-4 scrambles come from 17400–17419 | unit test |

### 6.4 Seed guards
- **Scored mode** accepts exactly the registered list and refuses every other seed.
- **Self-check and smoke modes** refuse 17000–17999 and 10000–10999.
- FACT: D12's and Part G's runners already refuse 17000–17999 (`d12_common.py:85`; `er9g_run.py:93`).
- **No simulation on scored seeds before the run** (M5 P5).

### 6.5 Reviews required before running
Independent reviews (P-20 subagents) look at the text and the code together. They are iterated until one requires no
changes (P-32 … P-50 precedent).

| Scope | Covers |
|---|---|
| R-a | The text against the repository: every FACT cited, the seed search re-run |
| R-b | Runner, verdict script and tests: every INVALID case, the positive control, resume with the git check on (M5 V1) |
| R-c | The composite system, the per-class rule, the d computation, and the E1-7 P1-type scans |

Reviewers are not given scored data (none exists) and do not need probe data.

### 6.6 Stop rules
- **Before the first start.**
  - The smoke run gives steps/s and peak memory per process.
  - Return to the user if:
    - the projected summed trial time exceeds `[CAP — PROPOSAL: 70 CPU-h for PG20, 45 CPU-h for PG8]`; or
    - peak memory × workers would leave less than 2 GB free (G.7).
- **During the run.**
  - A memory stop is an interruption. Resume with fewer workers, logged in the start log.
  - After 25 % of the trials, the cost is projected again. If it exceeds the cap, the run **pauses** and the user
    decides when to resume.
  - It is never abandoned by choice, because an abandoned run is INCOMPLETE, which is final.
  - Workers: 4 by default, at most 6 (G.11).
  - Nothing else heavy runs alongside it (D12, other jobs).

### 6.7 Deviations
- **Before the first start:** only by a dated amendment the user approves. It states that it was informed by no scored
  result, and it is reviewed again.
- **After the first start:**
  - the text is frozen;
  - anything unforeseen is recorded as a deviation in the summary and in the decision log;
  - no criterion, threshold, seed or trial list changes;
  - a harness bug found later is disclosed beside the unchanged verdict, with no rerun (M5 §5; next steps O6).

---

## 7. Prerequisites before this text can be fixed

Each item is consistent with the gap analysis §4 and with `PART_G_NEXT_STEPS_DRAFT.md` §3. Costs are INFERENCE from
G.11 and the gap analysis.

| # | Item | Gap ID | Owner | Rough cost |
|---|---|---|---|---|
| 1 | Part G probe reported. P-70 item 3's torque pause applied if triggered. G.9 rehearsal of `[ARM]` meets all three signals; with any move at the clip the choice is the user's (G.9 "Reading") | B1 | A, U | PG8 12–18 h, PG20 20–35 h (rehearsal) |
| 2 | Part G records committed and code-reviewed. ER9 decision-log row (draft P-71) and a Part G outcome row approved | B2, B3 | A drafts, U | review only |
| 3 | G.10 TODO resolved: L0's 12.59° located by sub-experiment, so CE's rule is read the same way for L0 | A4 | A | minutes |
| 4 | **Fit decision `[FIT]`** (U1). F-C: the main session spot-checks `MAGNET_POCKET_WALL_FINDINGS.md`, then the user fixes a threshold, disclosed post hoc. F-B: a new Part | A7 | U | F-C: research only. F-B: about 25–45 h |
| 5 | **Torque decision** confirmed: reported only (P-67 item 4), or a disclosed post-hoc criterion. The rig is unchanged | A10 | U | 0 (optional clip-raised diagnostic 2–4 CPU-h; D12 covers part of this) |
| 6 | `[D_VAL]` recorded for `[ARM]`; any O5-type amendment decided before the text is fixed | A2, A4 | A, U | 0–8 CPU-h |
| 7 | Composite V5 (energy) and V6 (pose-only) records for `[ARM]`, and a survey with clamped-z counts. V4 (momentum) is in `tests/test_magnets_composite.py`. **TODO: V5 and V6 not found by grep**; G.0 requires them before GS1 | A3 | A | under 1 CPU-h |
| 8 | Strength meaning: a sourcing check that 4×3 mm `[GRADE]` and 4×2 mm N35 discs are stocked | A5 | A | research only |
| 9 | Fresh-seed unscored rehearsal on 19000–19655 (+ 19700–19739), if Q3 is approved | B1 | A, after U | PG8 15–23 h, PG20 25–45 h |
| 10 | E1-7: P1-type scans per position-changing arm; V3 coverage confirmed | C6, D6 | A | 1–2 CPU-h |
| 11 | Runner, `analyze.py`, tests, SC1–SC7, and a smoke run on 18000–18099 with an interruption and a resume | D1–D4 | A | smoke 1–2 CPU-h |
| 12 | Reviews R-a, R-b and R-c until one requires no changes; the user approves the text | E1, E2 | A, U | about a day (M5: eight reviews) |
| 13 | Status-line commit, clean tree, idle machine, and the user's explicit go | D5, E4 | U | 0 |
| — | **Scored run** (not a prerequisite; for scale): 204 + 184 + `[N_E17]` + 200 reported | — | A | INFERENCE: PG8 about 30–45 CPU-h, PG20 about 40–65 CPU-h (TODO from the smoke run and E5's `wall_s`) |
| — | Sign-off items: E1-8 on a quiet machine, the abstraction write-up, the VALIDATION_PLAN sign-off | F1–F3 | B, A, U | about 1 h + writing |

**Rough total from a G.9 pass to a scored verdict** (INFERENCE): about 70–110 CPU-h with F-C (as gap analysis §4), plus
25–45 h with F-B. Calendar time is set by decisions and review rounds.

---

## 8. Open questions for the user (each with a recommended default)

| # | Question | Recommended default | Why |
|---|---|---|---|
| Q1 | Label | **"M7"** (git grep: no mechanism uses it) | "M6" names C52's lapsed configuration (M6 draft "Name") |
| Q2 | Scored seed map | **M5 seed + 7000 → 17000–17655; REST-X 17700–17739; `SCORED_SEED_RANGE` 17000–17999** | Never simulated (§9). M6's lapsed reservation was never used (P-66). A disjoint translate of M5's 656-seed span cannot fit beside it inside 17000–17999 |
| Q3 | Fresh-seed unscored rehearsal before fixing | **Yes, on 19000–19655 (+ 19700–19739)** | ER7's seeds were used for selection (G.10). M5's 204/204 rehearsal was followed by a scored failure |
| Q4 | Slip rule | **A criterion: 0 D11 events over 0–60 s in E1-1**, disclosed post hoc | Rest slips are the failure Part G exists to remove. A pass with slips would contradict the mechanism claim. It tightens, never loosens |
| Q5 | Controls on scored seeds | **CTRL-L0 on E1-1 and CTRL-C52 on E1-5s** (40 trials), reported only | Paired, held-out attribution at low cost. Full 204-trial controls add 20 h or more without an Option A role |
| Q6 | Rest extension | **Yes:** 40 × 60 s rests for `[ARM]` and L0 | 20 seeds cannot tell 0/20 from 2/20 (p ≈ 0.49, U5) |
| Q7 | 1.5× ideal-magnet coverage | **E1-7 0.67 arm plus DERATE** (E1-1 and E1-5s at 0.67; 40 trials), reported | Gap analysis A6. Rest and snap-back are the strength-sensitive behaviours |
| Q8 | E1-7 factors | **§3.4 as written**, including the P1-type gate; magnet-set ablation optional | Keeps M5's factors; adds only factors with V3 coverage |
| Q9 | Turner torque | **Reported only** (P-67 item 4), with counts at 0.2 / 0.45 / 0.5 N·m and at the clip | A criterion now is post hoc in either direction (M5 §0 item 5) |
| Q10 | Fit | **F-C**, after the main session spot-checks the pocket-wall sources, disclosed post hoc; F-B only if the sources do not support ≤ 0.175 mm | F-B voids all Part G dynamics (G.6 P3). This is the user's strategic call (U1) |
| Q11 | Reviews | **R-a, R-b and R-c, iterated until none requires changes** | M5 precedent (eight reviews) |
| Q12 | Stop-rule cost cap | **70 CPU-h (PG20) / 45 CPU-h (PG8)**, with pause and resume | About 1.2–1.5× this draft's estimate; never abandon (INCOMPLETE is final) |

---

## 9. Sources and the seed search record

### 9.1 Read
- `CLAUDE.md`; `RUBIKNETIC_MASTER_SPEC.md` §1–§5 (top).
- `docs/VALIDATION_PLAN.md`.
- `docs/DECISION_LOG.md`: P-24, P-51, P-52, P-58, P-60–P-70, and the G1 row.
- `experiments/PHASE_1_PREREGISTRATION.md` §1–§8.
- `PHASE_1_M4_PREREGISTRATION.md` §2–§4.
- `PHASE_1_M5_PREREGISTRATION.md` (in full).
- `PHASE_1_M6_PREREGISTRATION.md` (lapsed).
- `E6_scored_m6/README.md`; E4, E5 and E6 `run.py` seed constants.
- ER7 PROTOCOL; D11 PROTOCOL Definitions.
- ER9 PROTOCOL Part G (G.0–G.13, deviations 1–2).
- `proposals/G1_GAP_ANALYSIS.md`; `proposals/PART_G_NEXT_STEPS_DRAFT.md`.
- ER9 SUMMARY (snap-back note); `docs/research/TURNING_TORQUE_FINDINGS.md` (headline).
- `git log` messages (`6d00cda`, `446f989`, `9753518`, `79572c6`); `tests/test_magnets_composite.py` (test names).

### 9.2 Seed search (2026-11-22; to be repeated and recorded before the text is fixed, as M5 §2 and the M6 draft §2 require)
1. **Tracked text files.**

   ```
   git grep -nE "(^|[^0-9.e])17[0-9]{3}([^0-9]|$)" -- ':!*.json' ':!*.jsonl' ':!*.npz' ':!*.lock'
   ```

   Hits:
   - statements that the block is held out (DECISION_LOG P-66 and P-69, ER9 PROTOCOL and SUMMARY, drafts);
   - the lapsed M6 draft (17000–17655);
   - E6's unused runner, README and `tests/test_scored_m6.py` (stub tests, no simulation; P-66);
   - D12's and Part G's seed guards and their refusal tests;
   - false positives inside hashes in E4 and E5 result files.

   No simulation use.
2. **All files, including untracked and git-ignored records.**

   ```
   rg -l --no-ignore -e '"seed": ?17[0-9]{3}[,}]' -e '_s17[0-9]{3}' -g '!.git/**' -g '!.venv/**' (+ hybrid_g sub-folder excludes)
   ```

   Only `tests/test_scored_m6.py` and `experiments/ER9_anchored_core_layouts/tests/test_er9g_run.py` match.
   - **Disclosure:** the exclude globs named hybrid_g's sub-folders. The three committed self-check files directly
     under `results/hybrid_g/` (`selfcheck.json`, `selfcheck_static.json`, `replay_selfcheck.json`) were therefore
     pattern-scanned, with no match. Their content was not displayed or read.
   - The re-run should exclude `results/hybrid_g/**` except `static/`.
3. **18xxx and 19xxx** (same two forms, `1[89][0-9]{3}`, excluding `third_party_cad/` and hashes).
   - 18000–18099: E6's `SMOKE_SEED_BASE` and tests only (never run).
   - 19000–19999: only the two drafts that propose it.
4. **Status of 10000–10999** (FACT):
   - M5's scored range (P-34, P-51: 440 records, 10000–10655, E1-7 at 10000);
   - D10 reran 10000–10001 (P-52), and D11 reran 10000–10019 (`experiments/D11_rest_slip_count/results/rest60_s100xx`);
   - D12 and the Part G runner refuse the whole range (`d12_common.py:85`, `er9g_run.py:93`; D12 PROTOCOL l.19: "E5's
     E1-7 ran at seed 10000").

   Consumed; never to be used again.
