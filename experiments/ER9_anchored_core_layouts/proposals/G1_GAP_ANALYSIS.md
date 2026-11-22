> **DRAFT — not approved.** An analysis drafted by a subagent on 2026-11-21 from the repository's documents; nothing in
> it is a decision or a result. The main session checked the claims that changed ER9's summary:
> - P-60 covers clamped pairs only on V3-turn-validated on-axis trajectories (DECISION_LOG P-60);
> - the generic tilted-pair validation of the 4 × 3 table is 7.5° (ER5 SUMMARY, V3b);
> - the 4 × 2 table's extension to 7.5° failed (DECISION_LOG P-24);
> - E1-3 is "half turns";
> - the "CPU time" column is summed wall time (`er9_full_analyze.py`).
>
> The rest has not been re-verified item by item.

# What a scored G1 pre-registration for an ER9-derived mechanism still lacks

**Date:** 2026-11-21. **Status:** draft gap analysis, read-only. No simulation was run, no repository file was changed and
nothing was committed. Paths are relative to `C:\Dev\Rubiknetic`.

**Labels.** `FACT` = stated in the named file and section. `INFERENCE` = my reasoning from those facts. `PROPOSAL` = a
suggestion that needs the user's approval. "Not found" = I looked and found no evidence, which is different from
evidence that something is absent.

**Candidates assessed.**
- **(a) W3.** The ER9 anchored layout: edges with 2 pairs at 20° toward the centres, corners with 3 pairs at 16° toward
  the centres, 96 magnets of 4×3 mm N35 at strength scale 0.3, core clearance 0.2 mm, B1 cube at 0.05 mm piece gap
  (`experiments/ER9_anchored_core_layouts/PROTOCOL.md` Part C; `SUMMARY.md` Part D).
- **(b) A hybrid arm (HB1, HB2 or HB3).** M5's 48 corner–edge positions plus the same 96 anchors (144 magnets), all
  4×3 mm N35 at scale 0.756, anchors at 1, 2 or 3 mm clearance (`PROTOCOL.md` Part E and amendments 1–2).

---

## 0. Summary

**Where things stand (FACT).**
- No mechanism has passed G1. M1, M4 and M5 are NOT PASSED, and M2 has no valid scored run (`docs/DECISION_LOG.md`,
  Phase gate status, G1 row).
- W3 met all three of ER7's rehearsal signals on 204 of 204 trials. It did this on ER7's diagnostic seeds 16000–16655,
  the same seeds used to select it (`ER9 SUMMARY.md` Part D and Limits).
- **The decision log has no ER9 row yet.** It ends at P-66 (grep of `docs/` for P-67+ and "ER9": no match). The ER9
  summary says the row "will be proposed when Part E is complete" (`ER9 SUMMARY.md` Status).
- Seeds 17000–17999 have never been simulated (P-66; `ER9 SUMMARY.md` Status). A grep of `experiments/**/*.{py,md,txt}`
  finds them only in the lapsed M6 draft, the E6 runner and README, and the ER9 summary.

**Top five gaps** (detail in §2):
1. **Force-law validation for the off-axis anchor placement is missing, and P-60 does not cover it.**
   - W3: ER5's V3-turn validated on-axis piece-to-core pairs only. P-60 accepts clamped near pairs only on trajectories
     that ER5 validated.
   - Hybrid: it also has perpendicular piece-to-piece near pairs that no current rule accepts. Its 4×3 corner–edge
     pairs are flagged at 20°, but they were validated to only 7.5°. And there is a 7 % pull error in the 5–8 mm
     near/far blend at 2 mm clearance.
2. **The strength scale has no physical meaning yet** (D-06 and P-16 require "realistic strengths").
   - W3's 0.3 corresponds to Br ≈ 0.65 T (bonded NdFeB) or to a 3×3 mm N42/N45 at about 1.8–1.9 mm. Neither is
     chosen, and neither has a validated table.
   - The hybrid's 0.756 corresponds to Br ≈ 1.03 T, below sintered N35. Its suggested catalogue equivalent (4×2) has a
     table validated only to 5°, and the 7.5° extension of that table already failed.
3. **W3 does not fit the real-mechanism CAD.**
   - Corner anchors lie mostly in air, and edge anchors break out of the foot by 0.58 mm.
   - Either the user accepts the P-58 abstraction as a disclosed limitation, or a CAD-feasible redesign is needed. A
     redesign would need a new screen, a new probe and a new rehearsal.
4. **W3's turner saturates in 771 of 1,376 moves** (median peak torque = the 1 N·m limit).
   - No E1 criterion is triggered, and all moves were oracle-correct. But the real torque margin cannot be read from
     the records, because the clip censors it.
   - It sits at the top of Phase 0's capacity estimate and is above every real-cube figure on record.
   - A stall that does not break through on a new seed would fail turn error and the oracle check.
5. **None of the scored-run machinery exists for this mechanism yet.** That covers the pre-registration text, the
   adapted runner, verdict script and tests, a smoke run, the E1-7 V3 records, the independent reviews and the ER9
   decision-log row.
   - M5's procedure and E6's parameterised wrapper can be reused, so most of this is well-trodden work.
   - M5 needed eight reviews before its text was in force.

**User decisions:** see §3.1. **Recommended order:** see §4. **Contradictions found:** see §6.

---

## 1. The checklist a scored G1 pre-registration must satisfy here

Derived from `docs/VALIDATION_PLAN.md`, the M1, M4 and M5 pre-registrations, M5's eight reviews, the lapsed M6 draft and
the decision log. Each item cites where the requirement comes from.

### A. Mechanism and physics validity
| ID | Requirement | Source |
|---|---|---|
| A1 | A frozen, fully specified configuration: cube, gap, magnet layout code in a frozen path, tables pinned by SHA-256 | M5 prereg §1, §2 (manifest table SHA-256s); M6 draft §1; review 3 item 5; review 4 item 1 |
| A2 | Force law validated for **every pair type on every trajectory** the mechanism uses: V1, V3a, V3b, V3-turn and V4 | ER5 PROTOCOL "Verdict per size"; P-57; ER9 PROTOCOL Limits and Part D "Reading"; M4 prereg §4 ("must pass V3 at that size before use") |
| A3 | Checks of the MuJoCo implementation for the layout: V4, V5 (energy), V6 (callback reads poses only) and a near-pair survey | P-58 (4), P-59 (2); M6 PROTOCOL/SUMMARY; M4 prereg §2 rule 1 and §6 item 1 |
| A4 | A validated-regime definition and a flag rule: rule 2 fails an operational trial, rule 3 labels an abuse trial. `MagnetSystem.stats` logged per trial | M4 prereg §2 rules 2–3; P-60 ("Clamped pairs outside that set … still fail"; "must log `MagnetSystem.stats`"); M6 draft §1 |
| A5 | Realistic magnet strengths with a stated physical meaning | Master spec D-06; P-16 ("with realistic strengths"); ER9 PROTOCOL Part C ("What a scale below 1 stands for"); ER9 SUMMARY Limits |
| A6 | Robustness to the ideal-magnet overstatement of up to 1.5× (E1-7 strength-scale arm) | M4 prereg §7 and E1-7 factors; M5 prereg §7; M6 draft §0 item 4 |
| A7 | Real-mechanism fit, or the abstraction disclosed and accepted | P-58 (2); ER9 PROTOCOL Part D "Reading" (lists "a fit check in a real piece"); VALIDATION_PLAN G1 Pass ("mechanism abstraction and limitations published"); M6 draft §0 item 3, §7 |
| A8 | The piece-clearance assumption disclosed | M5 prereg §0 item 3 (0.05 mm is an `ASSUMPTION`) |
| A9 | P-16's required energy and impulse analysis and no-magnet comparison (E1-6m, E1-6n) | P-16; M4 prereg §4 (E1-6m, E1-6n) |
| A10 | Turner torque reported, with the clip defined; the rig limit is part of the frozen configuration | M1 prereg §1 (turner limit 1 N·m); M5 prereg §0 item 5 and §4 (reported only, clip ≥ 0.999 N·m); review 2 P3 |

### B. Evidence required before drafting
| ID | Requirement | Source |
|---|---|---|
| B1 | An unscored full 204-trial rehearsal of the exact frozen configuration meeting pre-declared signals | P-30 (M5's route); P-61 and ER7 PROTOCOL ("If C52 meets all three, I would propose a scored pre-registration"); ER9 PROTOCOL Part D |
| B2 | Rehearsal records committed and independently code-reviewed | ER9 SUMMARY "Independent code review"; P-20 |
| B3 | A decision-log row recording the rehearsal outcome, and the user's choice to draft | CLAUDE.md ("No phase advancement without … DECISION_LOG"); ER9 PROTOCOL Status; P-30/P-31 precedent |

### C. Pre-registration text
| ID | Requirement | Source |
|---|---|---|
| C1 | The basis, with an exhaustive list of what changes relative to M5 | M5 prereg "Basis"; review 3 item 6 |
| C2 | §0 disclosure of every post-hoc choice, in order | M5 prereg §0 item 1; M6 draft §0 item 1 |
| C3 | Independence statement: move strings shared with rehearsals; E1-4 scrambles drawn from the scored seeds | Review 1 R3 and O1; M5 prereg §0 item 2, §3 |
| C4 | M1/M4/M5 criteria inherited unchanged; Option A including E1-5s, E1-6t and E1-6m; E1-6n never in Option A | M5 prereg §4, §5; M1 prereg §5; review 1 O6 |
| C5 | Reported-only additions fixed before scoring, with no new threshold chosen after seeing data | M5 prereg §0 item 5, §4; review 2 P3 and "Post-hoc risk" |
| C6 | E1-7 factors, band rationale (with the precedent disclosed), and V3 coverage for every arm or a registered "not run" reason | Review 1 R4 and O5; review 2 N1 and P1; review 3 items 8 and 12; M5 prereg §4; M6 draft §4 (open) |
| C7 | Explicit seed map in an unused range, a recorded repository search, a unit test, and no simulation on scored seeds before the run | Review 1 R1; review 2 P5; M5 prereg §2; M6 draft §2 |
| C8 | A freeze rule and a provenance statement | Review 1 R5; review 2 P6; M5 prereg Status |
| C9 | A G1 verdict restatement (disclosures, margins, clip count, rule-3 labels, starts) | Review 1 O7; M5 prereg §5 |

### D. Code and run procedure
| ID | Requirement | Source |
|---|---|---|
| D1 | A scored runner: M5's logic and run procedure (manifest, start log, ledger, atomic records, resume, exception rule, location check) plus only the listed changes | M5 prereg §2, §6.1 item 1; reviews 3–6 (T1, U1, U2, V1, W1) |
| D2 | A frozen verdict script with E1-6t (16), E1-6m, every integrity check, the verdict order, and "not run" re-derived without the git-ignored tables | Review 1 R2; review 2 P4; review 5 O3 and O6; review 6 W1; M5 prereg §5 |
| D3 | Unit tests: seeds, layout, tables, regime rule, every INVALID case, a positive control, and a resume test with the git check on | M5 prereg §5 "Tests" and §6.1 item 3; review 5 V1; M6 draft §6.1 item 3 |
| D4 | A smoke test on non-scored seeds through the full run procedure, including an interruption and a resume | M5 prereg §6.1 item 4; review 4 item 11 |
| D5 | A clean frozen commit; the Status-line commit before the first start; no commits to frozen paths or results during the run | M1 prereg rule 1; M5 prereg §2 and §8; review 6 X6; review 4 item 5 |
| D6 | E1-7 V3 records committed before the first start | M5 prereg §6.1 item 5; M6 draft §6.1 item 5 |

### E. Review and approval
| ID | Requirement | Source |
|---|---|---|
| E1 | User approval of the text, plus independent reviews until one requires no changes (text and code reviewed together) | P-32, P-36, P-40, P-42 (option b), P-48, P-50 |
| E2 | Reviewers do not read results that could inform the text; provenance is disclosed | P-36; review 2 header; review 5 disclosure |
| E3 | A change request, using the DECISION_LOG template, if a locked decision or frozen rule changes | `docs/DECISION_LOG.md` "Change request template"; CLAUDE.md ("wait for user approval before changing locked decisions") |
| E4 | The user's explicit go for the scored run | P-63 ("stops before starting any scored run") |

### F. Needed for the G1 sign-off (not for starting the run)
| ID | Requirement | Source |
|---|---|---|
| F1 | E1-8 throughput on a quiet machine | M5 prereg §6.2; VALIDATION_PLAN G1 ("CPU benchmark"); M1 prereg E1-8 |
| F2 | The mechanism abstraction and its limitations published | VALIDATION_PLAN G1 Pass; DECISION_LOG G1 row ("Outstanding …") |
| F3 | User sign-off with the VALIDATION_PLAN fields | VALIDATION_PLAN "Sign-off protocol" |

**Note (FACT):** VALIDATION_PLAN defines the G1 tests and the threshold policy, but **not** the E1 experiments or
Option A. Those are in `experiments/PHASE_1_PREREGISTRATION.md` §4–§5 (M1).

---

## 2. Status per item: (a) W3 and (b) hybrid arm

Status words: **met**, **partly**, **not met**. Owner: **U** = user decision, **A** = work the assistant can do,
**B** = blocked on hardware or on the user's machine.

### Overview
| ID | Item | W3 | Hybrid | Owner |
|---|---|---|---|---|
| A1 | Frozen configuration | partly | not met | A (after U) |
| A2 | Force-law validation for every pair and trajectory | **not met** | **not met** | A, then U (amendment) |
| A3 | V4/V5/V6 and survey for the layout | partly | not met | A |
| A4 | Validated regime and flag rule | partly | **not met** | U (amendment), A |
| A5 | Physical meaning of the strength | **not met** | **not met** | U, A |
| A6 | Robustness to the 1.5× overstatement | not met (risk) | not met | A |
| A7 | Real-mechanism fit or accepted abstraction | **not met** | partly | U, A |
| A8 | Clearance assumption disclosed | partly | partly | A |
| A9 | E1-6m / E1-6n | partly | not met | A |
| A10 | Turner torque and rig limit | **open issue** | open (pending data) | U |
| B1 | Full rehearsal of the frozen configuration | met for W3 as is* | not met | A |
| B2 | Records committed and reviewed | met | not met | A |
| B3 | ER9 decision-log row | not met | not met | A drafts, U approves |
| C1–C9 | Pre-registration text | not met | not met | A drafts, U decides |
| D1–D3 | Runner, verdict script, tests | partly (E6 reusable) | partly | A |
| D4–D6 | Smoke run, frozen commit, E1-7 V3 records | not met | not met | A |
| E1–E4 | Reviews, approval, change request, go | not met | not met | U, A |
| F1–F3 | E1-8, abstraction write-up, sign-off | not met | not met | B, A, U |

\* Only if A5 and A7 are settled without changing the model. Any change of magnet, strength or placement needs a new
rehearsal.

### A1. Frozen configuration
- **W3: partly.**
  - FACT: the arm is defined in the ER9 wrapper and printed at the head of the run log: `{'grade': 'N35', 'scale': 0.3,
    'edge_opt': ['split', 20, 'centre'], 'corner_opt': ['tri', 16, 'centre']}` (`full_W3_log.txt` line 1).
  - FACT: the tables are "M6's N52 table times the exact strength factor, written once and checked on every use"
    (ER9 PROTOCOL Part C "Tables").
  - INFERENCE: the layout lives in `experiments/ER9_anchored_core_layouts/er9_layout.py`, not in
    `src/rubiknetic/cube_physics/magnets.py`.
  - **To close (A):** freeze the layout function in a frozen path (in `src/` or listed in the frozen paths), and pin
    the derived table's SHA-256 in the manifest, as M5 §2 does.
- **Hybrid: not met.** No arm has been selected; the probe is unfinished (see B1).

### A2. Force-law validation for every pair and trajectory
- **W3: not met.**
  - FACT: "The force law was validated for coaxial piece-to-core pairs up to 20° of tilt (P-60, ER5). Off-axis anchor
    pairs stay within that tilt range but their placement has not had its own V3-turn check" (ER9 SUMMARY Limits).
  - FACT: ER9 PROTOCOL Part D "Reading" lists "a force-law validation for the off-axis placement (an ER5-style
    V3-turn)" as still lacking.
  - FACT: in ER5, 4×3 N35 passed V3-turn in the real placement with a worst torque error of 4.1 % against 5 %, and
    failed it in the B1 placement (ER5 SUMMARY Results). The margin is modest, and off-axis pairs meet core magnets in
    new combinations (ER9 PROTOCOL Limits).
  - **To close (A):** an "ER10" V3-turn for the anchored placement, under a protocol committed before the run. Its
    content:
    - each distinct moving anchor magnet (one per edge pair and one per corner pair, by symmetry) rotated with its piece
      through 0–90°;
    - compared against all 96 core magnets, hybrid law against the fine model (32×96 within r2), with ER5's pass
      rules;
    - V1, V3a and V3b carry over by exact scaling, because the magnet is the ER5 4×3 table × scale (M6 S1 linearity);
    - V4 for the 96-magnet layout.
- **Hybrid: not met.** On top of the W3 gap:
  - **Perpendicular piece-to-piece near pairs** (FACT, ER9 PROTOCOL Part E amendment 2). Anchors of the turning layer
    pass corner–edge magnets of the layer below at 5.8–6.2 mm and about 64°, 12 pairs per quarter turn. The force law
    corrects near pairs only within 45° of parallel, so these pairs get the point-dipole formula alone.
    - The one comparison made gives torque about the turn axis within 3.5 % of the charge model (0.39 of 11.3 mN·m).
      It is "a measured size of the error, not a validation" (amendment 2; SUMMARY Part E).
    - That comparison covers one scalar, along a rigid quarter turn, at c = 2 mm only (`results/hybrid/perp_c2.json`).
  - **Corner–edge pairs of 4×3 magnets.**
    - FACT: ER5's V3b validated 4×3 tilted pairs to 7.5° (ER5 SUMMARY Results).
    - FACT: P-60's 20° covers piece-to-core pairs only (P-60).
    - FACT: Part E amendment 1 nevertheless uses 20° as the flag limit for all pairs, and states that corner–edge
      4×3 pairs and the cross-interaction "were not part of that validation".
  - **Blend-region error.** FACT (`side_checks/README.md`, catalogue, "Force-law note"): at 2 mm anchor clearance the
    simulated pull is 7.1 % below the charge model (0.386 vs 0.416 N). At 3 mm it is within 1 %, but the axial stiffness
    is reported 27 % low, and that figure was not rechecked.
    - INFERENCE: V3's tolerance is 5 % of the facing-pair force at 1.0 mm (1.92 N for 4×3 N35, × 0.756 ≈ 1.45 N;
      ER5 SUMMARY), so a 0.030 N error is about 2 % of that and would *pass* a V3-style test.
    - A V3-turn as defined therefore may not guard the weak anchors' own accuracy. A relative-error criterion for
      anchor pairs is worth considering (PROPOSAL; the user's choice).
  - **To close:**
    - (A) an ER10 that covers every pair type: anchor–core off-axis, corner–edge 4×3 tilted to the turn's maximum,
      perpendicular cross pairs (full force and torque vectors against the fine model), and blend-region accuracy at
      each candidate clearance;
    - (U) then an amendment of the P-60 kind if the perpendicular pairs are to be accepted. Alternatively, a force-law
      revision (M6 SUMMARY option (b) shows that is a separate approval).

### A3. Implementation checks for the layout
- **W3: partly.**
  - FACT: Part A's screen checked geometry and the near-pair survey for this geometry: no perpendicular pair, largest
    near tilt 18.2°, no piece-to-piece near pair, magnets of different pieces ≥ 10.36 mm apart (ER9 SUMMARY Part A;
    PROTOCOL Part A criteria 4–5).
  - FACT: E1-6m ⟨P⟩ passed 1,376 of 1,376 moves (ER9 SUMMARY Part D).
  - **V4, V5 (energy in MuJoCo with implicitfast and RK4) and V6 for the 96-magnet `MagnetSystem`: not found.**
  - FACT: the survey's "clamped |z|" count is not reported for W3 (ER9 SUMMARY Limits, last bullet).
  - **To close (A):** an M6-style check run for the final layout: V4, V5, V6, a survey with clamped-z counts, and a
    throughput figure. On M6's record this is under 1 CPU-h (752 s wall including a 637 s table build; M6 SUMMARY).
- **Hybrid: not met.** The survey fails by design (perpendicular pairs). V4, V5 and V6 were not found.

### A4. Validated regime and flag rule
- **W3: partly.**
  - FACT: signal 3 was met: 0 flagged trials, largest near tilt 18.42° against 20°, 0 perpendicular pairs
    (`results/full/W3/analysis.json`).
  - FACT: ER7's flag is "near_perpendicular > 0 or max near tilt > 20°" (ER7 PROTOCOL "Measured"). It does not look
    at clamped z.
  - FACT: P-60 accepts a clamped pair only if it is a piece-to-core pair "on a face-turn trajectory for which ER5's
    V3-turn passed". ER5's V3-turn covered on-axis magnets only (ER5 PROTOCOL V3-turn setup).
  - INFERENCE: W3's anchors pass through clamped z at 15.7–18.3° of relative rotation (ER9 SUMMARY Limits). Under
    P-60's wording these anchor pairs are outside the accepted set. So signal 3 does not show P-60 compliance (see
    §6, contradiction 2).
  - **To close:** (A) the ER10 V3-turn of A2 covering those trajectories; then (U) a P-60-style extension to the
    anchored trajectories, and a runner flag that counts clamped pairs outside the accepted set.
- **Hybrid: not met.**
  - FACT: "No hybrid arm can be named a candidate for a scored pre-registration under the rules as they stand"
    (PROTOCOL Part E amendment 2).
  - **To close (U):** an amendment for the perpendicular pairs, and per-configuration tilt limits (M5 §1 rule: "each
    other magnet configuration uses the validated tilt in its own V3 record"). The latter means 7.5° for 4×3 corner–edge
    pairs unless they are validated further.

### A5. Physical meaning of the strength scale
- **W3: not met.**
  - FACT: "A strength scale (0.3 for W3) is not a catalogue magnet … which one has not been chosen or checked for fit"
    (ER9 SUMMARY Limits).
  - FACT: the two readings on record:
    - (i) the same 4×3 mm size at lower remanence, "0.3 → 0.65 T, the range of bonded NdFeB" (PROTOCOL Part C);
    - (ii) a stocked 3×3 mm N45/N42 at about 1.8–1.9 mm face gap, which "has no validated force table" (SUMMARY
      Limits; side_checks catalogue).
  - FACT: vendor pull is 0.61–0.87 of the ideal model, so the matching gaps are uncertain by about 0.5 mm until pull is
    measured against gap (side_checks catalogue).
  - INFERENCE: what each reading needs.
    - **Reading (i)** keeps the model unchanged, which is cheapest. It needs a sourced availability check of 4×3 mm
      bonded NdFeB discs at Br ≈ 0.65 T (not found); and bonded magnets' μr and mechanical suitability are an
      unexamined assumption.
    - **Reading (ii)** changes magnet size and geometry. It needs a new table, V1/V3a/V3b/V3-turn, a new screen value,
      and a new probe and rehearsal.
  - **To close:** (U) choose the reading; (A) a sourcing check, and for (ii) the validation and rehearsal chain.
- **Hybrid: not met.**
  - FACT: scale 0.756 is the value at which a 4×3 corner–edge pair pulls like M5's 4×2 (1.644 N), and "it is not a
    catalogue magnet" (amendment 1).
  - INFERENCE: since the scale multiplies Br² (side_checks catalogue), 0.756 corresponds to Br ≈ 1.19 × √0.756 ≈ 1.03 T,
    below the N35 grade. Whether a sintered grade at that Br is stocked in 4×3 was not found.
  - FACT: the side check's shortlist names "4 × 2 N35/N45, which is M5's magnet type" for the hybrid at 1–2 mm, and
    notes that 4×2 would need its table validated beyond 5°.
  - FACT: that table's 7.5° extension **failed** on torque (M4 prereg §9 trigger "§6 item 2"; P-24). INFERENCE: the 4×2
    reading is blocked unless the force law is revised.

### A6. Robustness to the 1.5× overstatement
- **W3: not met, and a likely fragility** (INFERENCE).
  - FACT: W3 is "the weakest of the three that keeps ER3's layer stiffness of at least 1.0 N·m/rad" (1.32 N·m/rad;
    PROTOCOL Part C table).
  - INFERENCE: E1-7's 0.67 strength arm would give about 0.88 N·m/rad, below ER3's screen limit.
  - E1-7 flips do not fail G1 (M4 prereg §4 E1-7), but they limit the "outcome unchanged inside the band" claim.
  - **To close (A):** include the arm in E1-7 with its V3 coverage (by linearity) and disclose the expected fragility.
- **Hybrid:** the same requirement applies; there is no data yet.

### A7. Real-mechanism fit
- **W3: not met.**
  - FACT (side_checks `realfit/`; SUMMARY Limits): corner anchors at 16° are 83 % in air (material starts at 25.0 mm;
    the magnet spans 22.35–25.35 mm). Edge anchors at 20° break out of the foot by up to 0.58 mm.
  - FACT: in that CAD, three corner magnets fit only as 3×2 at 5.5–7° toward the centres, outside Part A's 10–16°.
    Edges take 4×3 up to 16.5°.
  - FACT: the core cover is 0.20–0.29 mm against the 0.4 mm assumed.
  - FACT: whether a feasible placement still anchors the pieces "has not been computed".
  - **To close, either:**
    - (U) accept the P-58 abstraction for G1 as a disclosed limitation (as the lapsed M6 draft §7 proposed: "a G1 pass
      would establish the simulated mechanism, not a buildable cube"); or
    - (A, after U) a CAD-feasible redesign: a static screen of 3×2 at 5.5–7° corners plus edges at ≤ 16.5°, then
      V-checks, a probe and a full rehearsal.
- **Hybrid: partly.**
  - FACT: M5's corner–edge magnets fit as 4×3 inside the CAD piece, at least 3.99 mm from the anchors (side_checks
    realfit).
  - The anchors use the same geometry as W3. Fit at 1–3 mm clearance was not determined (INFERENCE: the measured
    span was at 0.2 mm).

### A8. Clearance assumption
- **Both: partly.**
  - FACT: 0.05 mm is an `ASSUMPTION`; the only source is a 2×2×2 patent (M5 prereg §0 item 3).
  - FACT: the real-mechanism CAD's piece gap is 0.25 mm (side_checks realfit, Hybrid bullet).
  - **To close (A):** restate this in §0, adding the CAD's 0.25 mm. R1 would settle it (B), but it is not a G1 gate
    (P-24 A2).

### A9. E1-6m / E1-6n
- **W3: partly.**
  - FACT: E1-6m ⟨P⟩ passed 1,376 of 1,376 (SUMMARY Part D).
  - E1-6n was not run in ER9. INFERENCE: the M5 precedent says it will jam at 0.05 mm (M5 prereg §4 E1-6n; P-27). It
    is reported only.
- **Hybrid: not met** (no data).

### A10. Turner torque and the rig limit
- **W3: open issue.**
  - FACT: turner median, p99 and max are all 1.0 N·m. 771 of 1,376 moves (in 68 trials) are at the clip, against 0
    for L0 (`results/full/W3/analysis.json`).
  - FACT: the layer stalls at about 6.7° for about 0.1 s, then breaks through. The stall comes from U-corner lower
    chamfers against side-centre chamfers, and it is present with almost no magnets (SUMMARY Diagnostics; INFERENCE
    there from single-seed replays).
  - **Are the E1 criteria implicated?**
    - FACT: no. M1, M4 and M5 have no torque criterion; turner torque is reported only (M5 prereg §0 item 5, §4).
    - FACT: every W3 move matched the oracle, and all 204 trials passed.
    - INFERENCE: criteria are implicated *indirectly*. A stall that fails to break through within the commanded turn
      would show up as turn error > 2°, an oracle mismatch or a causality issue.
    - INFERENCE: because the clip censors the needed torque, the records cannot say how close to 1 N·m the breakaway
      torque really is.
  - **Is the rig limit implicated?**
    - FACT: the 1 N·m limit is part of M1's frozen rig (M1 prereg §1, "turner torque limit 1 N·m"), inherited by M4
      and M5.
    - INFERENCE: raising it would change the frozen configuration. It is allowed in a new pre-registration only if
      disclosed as chosen after seeing W3.
  - **Realism and Phase 2 (INFERENCE).**
    - Phase 0 found a coaxial grasp transmits 0.17–4.4 N·m and concluded torque is feasible "unless real resistance
      exceeds ~1 N·m" (`docs/research/MECHANICAL_FEASIBILITY_ASSESSMENT.md`). The required torque bracket is an
      `ASSUMPTION`, 0.03–0.6 N·m.
    - The only verified real-cube figure is 0.09 N·m, an undated hand measurement (P-63).
    - A mechanism whose median peak sits at the 1 N·m limit is at the edge of both. This is a credibility concern
      under D-06's "realistic", not a G1 criterion.
  - **To close (U):** choose one:
    - (a) keep turner torque reported only (M5 precedent), with the clip count restated in the verdict;
    - (b) add a criterion before scoring, disclosed as chosen after seeing W3 (M5 §0 item 5 notes that either direction
      is a post-hoc choice);
    - (c) amend the rig limit, which also shifts Phase 2 requirements.
  - PROPOSAL (A, unscored, before deciding): a turner diagnostic with the clip raised (for example 3 N·m) on rehearsal
    seeds only, to measure the uncensored breakaway-torque distribution. About 2–4 CPU-h for 24 to 40 replays.
- **Hybrid: open, pending data.**
  - FACT: the smoke replays G1/G2/G3 peaked at 0.525, 0.432 and 0.118 N·m, with no step at the limit (PROTOCOL Part E
    amendment 2). That is a single seed.

### B1. Full rehearsal of the frozen configuration
- **W3: met for W3 as defined.**
  - FACT: 204 of 204; signals 1–3 met; probe reproduced (`analysis.json`).
  - FACT: the seeds were already used for diagnostics and for selection, so "the 204 trials are not independent of the
    selection" (SUMMARY Limits).
  - If A5 or A7 changes the magnet, strength or placement, this no longer applies, and a new probe and rehearsal are
    needed.
  - PROPOSAL: even unchanged, a fresh-seed rehearsal (for example 19000–19999, which a grep of
    `experiments/**/*.py` found unused; a full search must be recorded) would give a selection-independent estimate.
- **Hybrid: not met.**
  - FACT: the ER9 SUMMARY records the probe stopped at 75 of 318 (Part E status).
  - FACT (working tree, uncommitted): `hybrid_probe_log.txt` shows two restarts ("243 trials to run", then "95 trials
    to run"). On 2026-11-21 there were 275 records (HB1 92, HB2 92, HB3 91).
  - FACT (same uncommitted log): one FAIL line, `HB2 FAIL E1-1/rest_s16005 rest 0.516 M1 criteria`. Seed 16005 is one
    of L0's two slip seeds (ER7 SUMMARY L0's failures).
  - Per the repository's own rule, the partial records are not interpreted here. If confirmed, HB2 would miss probe
    signal 2 and so be ineligible (PROTOCOL Part E amendment 2, "eligible").
  - **To close (A):** finish the probe, which is resumable. Commit, report, and run the full rehearsal of the eligible
    arm only if the user keeps the hybrid in contention.

### B2. Records committed and reviewed
- **W3: met.** FACT: ER9 SUMMARY "Independent code review (2026-11-20)", with no verdict change.
- **Hybrid: not met.** FACT: the records are untracked (git status at session start).

### B3. ER9 decision-log row
- **Both: not met.** FACT: no ER9 row exists; the SUMMARY defers it to the end of Part E.
- **To close:** (A) draft the row. It should record Parts A–D, the side checks, the code review and Part E's outcome.
  (U) approve it.

### C1–C9. Pre-registration text
- **Both: not met.** No draft exists (grep: no `PHASE_1_M7*`; the M6 draft lapsed, P-66).
- **Concrete content the text would need**, beyond M5's template:
  - **C2.** The full post-hoc chain:
    - M5 failed on rest (P-51), followed by D10, D11 and ER1 to ER6, M6 (with the P-60 amendment after a failure),
      ER7 and ER9 Parts A–D;
    - the Part A stiffness target set on a wrong rationale (SUMMARY "Corrections" 1);
    - W3 selected on ER7's seeds;
    - for a hybrid: arms chosen after single-seed replays, and amendments 1–2.
  - **C3.** The move strings fixed by M1 were seen by M5's scored run, ER7 and ER9. Only the E1-4 scrambles from the
    new seeds are held out (M6 draft §0 item 2).
  - **C5.** Turner torque and clip count (P3 definition). Also the clamped-pair counts per P-60, and, if kept from
    ER7 and ER9, the instrumented 60 s rest (the M6 draft and the E6 code differ on this; E6 README table).
  - **C6.** E1-7 factors.
    - The M6 draft left them open; the E6 code chose grades N35/N42/N52, strength 0.67 and no clearance factor,
      because only c = 0.2 mm has a V3-turn record (E6 README).
    - For W3, each clearance or strength arm needs its own V3-turn record, or a registered "not run" reason.
    - Disclose the expected 0.67 fragility (A6), and M5's timestep 0.75 ms flip (E5 SUMMARY E1-7).
  - **C7.** A new label (INFERENCE: "M6" names C52's configuration, M6 draft "Name"), so "M7" would be next.
    - The seed map: 17000–17999 never simulated (P-66), or a new range. Repeat the repository search and record it
      (M6 draft §2).
    - Smoke seeds 18000–18099 are already used by E6's code (E6 README).
  - **C8.** Provenance: the author has seen M5's scored results and all of the ER7 and ER9 rehearsal data.

### D1–D3. Runner, verdict script, tests
- **Both: partly.**
  - FACT: `experiments/E6_scored_m6/run.py` loads M5's runner unchanged and patches the seeds, magnet installation,
    tables, regime, V3 rule, E1-7 factors, label and folders. It has 45 tests and a dry run (436 trials, 0 refused)
    (E6 README; P-66).
  - FACT: "Any such use needs a new, approved pre-registration and a review of this code first" (E6 README).
  - **To close (A):**
    - install the anchored (or hybrid) layout;
    - change the V3 rule to the ER10 record;
    - add a regime rule that counts clamped pairs outside the accepted set (A4) and, for the hybrid, the amended
      perpendicular rule;
    - port the tests, adding new ones for the layout's magnet count (96 or 144) and the regime rule.

### D4–D6. Smoke run, frozen commit, E1-7 V3 records
- **Both: not met.**
  - FACT: E6 has never made a smoke run (E6 README).
  - INFERENCE: the working tree has untracked hybrid probe files. The clean-commit check covers the frozen paths
    (M5 review 5 "Frozen paths"), but the probe should be finished and committed first, so that no CPU or memory
    contention and no stray files overlap with the scored run.
  - The Status-line commit must precede the first start (review 6 X6; P-50 commit note).

### E1–E4. Reviews, approval, change request, go
- **Both: not met.**
  - FACT: M5 took eight reviews, with required changes in reviews 1–6, before its text was in force (P-33 to P-50).
  - FACT: the DECISION_LOG change-request template has never been used: a grep of `*.md` finds only the template
    itself.
  - INFERENCE: a change request (E3) is needed only if the user:
    - departs from D-06's "realistic strengths" (A5);
    - accepts a non-buildable layout beyond P-58's approved scope (A7);
    - raises the frozen rig limit (A10c); or
    - amends a regime rule (A4).
    The amendments themselves follow the P-60 pattern (a decision-log row).

### F1–F3. Sign-off items
- **F1: blocked (B).** FACT: E1-8 "needs the user's other workload paused" (M5 prereg §6.2). It was not run for M5
  (E5 SUMMARY).
  - INFERENCE: W3 used 22.8 h of summed trial time against L0's 10.4 h on the same 204 trials (`analysis.json`
    `wall_h`), so throughput is about 2.2× lower. That matters for Phase 3 budgets (P-64: about a million control steps
    at 606 steps/s).
- **F2: not met (A).** FACT: listed as outstanding in the G1 row.
- **F3: not met (U).**

---

## 3. Who decides, who does, what is blocked

### 3.1 User decisions (strategic or mechanical choices and amendments)
1. **Which candidate goes forward:**
   - W3 as is;
   - a CAD-feasible redesign of W3;
   - a hybrid arm (after its probe, and possibly its full rehearsal); or
   - none of these.
2. **The real-fit policy for G1:** accept the P-58 abstraction as a disclosed limitation, or require a placement that
   fits the real-mechanism CAD (A7).
3. **The physical meaning of the strength:** bonded NdFeB at Br ≈ 0.65 T in 4×3 (W3), a catalogue magnet at a larger
   gap (new table and validation), or the hybrid's 0.756 (Br ≈ 1.03 T) (A5). This also bears on D-06.
4. **The turner policy:** reported only (M5 precedent), a new criterion, or a rig-limit amendment. Optionally approve
   the clip-raised diagnostic first (A10).
5. **Force-law amendments:**
   - a P-60-style extension to the anchored trajectories once ER10 passes (both candidates);
   - for the hybrid, acceptance of the dipole formula for the perpendicular near pairs, and the tilt limit for 4×3
     corner–edge pairs (A2, A4);
   - or a force-law revision instead.
6. **Whether anchor accuracy needs a relative-error criterion** on top of V3's absolute normalisation (A2, hybrid).
7. **The ER9 decision-log row**, and approval of the follow-up protocols. ER9 ran under the P-63 delegation; the user
   may prefer to approve these explicitly.
8. **Pre-registration choices:**
   - the label (M7?);
   - the seed range (17000–17999 or new);
   - the E1-7 factors (clearance and strength arms);
   - whether to run a fresh-seed rehearsal first;
   - the number and scope of reviews;
   - whether the instrumented 60 s rest is in or out.
9. **Approval of the text** (conditional on the reviews), and **the explicit go** for the scored run (P-63).
10. **Unrelated but open in the G1 row:** formal closure of M2 (DECISION_LOG G1 row).

### 3.2 Work the assistant can do
- Finish the hybrid probe (it is resumable), commit, report, and draft the ER9 row.
- ER10 protocol and run: V3-turn for the off-axis anchors (and hybrid cross, perpendicular, corner–edge and blend
  checks), V4, V5, V6, and a survey with clamped-z accounting.
- Sourcing checks: bonded NdFeB 4×3 at about 0.65 T; a sintered grade at about 1.03 T. Web access may be needed; per
  P-62 and P-63 some fetches were refused by the permission check.
- If approved: a CAD-feasible anchor re-screen (static), and the clip-raised turner diagnostic.
- A fresh-seed probe and rehearsal of the final configuration.
- Drafting the pre-registration; adapting the E6 runner, verdict script and tests; the smoke run; the E1-7 V3 records.
- Organising the independent reviews (P-20 subagents) and answering them.
- The abstraction and limitations write-up (F2).

### 3.3 Blocked by hardware or by the user
- **E1-8 on a quiet machine:** the user must pause other workloads (M5 prereg §6.2). It gates the sign-off only.
- **Memory and CPU availability.** Runs have been killed or stopped by low memory: ER7 SUMMARY deviation 2, and ER9
  Part E status (another training job). Long rehearsals and the scored run need the machine mostly free.
- **R1 real-cube bench** (P-07, P-62: the user will run it; no data yet). Since M4 Amendment 1 A2 it is *not* a G1 gate
  (P-24). It would settle the 0.05 mm clearance, the real turning torque (O-09) and forgiveness.
- **A bench pull-vs-gap measurement of the chosen catalogue magnet** (side_checks catalogue: "A bench measurement would
  settle it"). Needed only if the user wants the strength meaning (A5) anchored to hardware.
- **Licensing:** the GrabCAD mesh licence is unconfirmed, so only numbers can be kept (side_checks realfit). Fit
  geometry cannot be published.

---

## 4. Recommended order of work to reach a scored run

Effort figures are `INFERENCE` from recorded runs:
- W3's full rehearsal: 22.8 h of summed trial time, 7,117 s wall (`full_W3_log.txt`, `analysis.json`).
- ER7: 408 records in 9,593 s with 8 workers.
- ER9 Part C probe: 318 trials in 2,756 s.
- M5's scored run: 440 records in 11,944 s.
- ER5: about 4,500 s wall per magnet size, including a 530 s table build.
- M6 checks: 752 s.

"CPU-h" is summed per-trial time. On this shared 16-core machine I assume 6–8 workers to stay clear of the memory kills
(ER7 was killed at 12 workers under other load).

| Step | What | Owner | CPU | Gate it closes |
|---|---|---|---|---|
| 0 | Decisions 1–4 of §3.1 (candidate, fit policy, strength meaning, turner policy) | U | 0 | Avoids redoing simulation |
| 1 | Let the hybrid probe finish (43 trials left), commit, report Part E, draft the ER9 decision-log row (P-67) | A, then U | ~1–2 h wall | B2, B3 |
| 1b | Only if the hybrid stays in contention: the full 204-trial rehearsal of the eligible arm | A | ~25–35 CPU-h (144 magnets, probably ≥ W3's cost; not measured); ~4–6 h wall | B1 (hybrid) |
| 2 | Optional, recommended: an unscored clip-raised turner diagnostic on rehearsal seeds | A (protocol), U approves | ~2–4 CPU-h | Informs A10 |
| 3 | If redesign or a new magnet: build the table (~10 min), V1/V3a/V3b (~1 h), then a static CAD-feasible re-screen (Part A style; under an hour on Part A's record, not timed) | A | ~2–3 CPU-h | A5, A7 |
| 4 | ER10 force-law validation of the final layout: V3-turn for every distinct anchor (and hybrid pair types), V4; then V5, V6 and the survey with clamped-z counts | A | ~3–8 CPU-h | A2, A3 |
| 5 | User amendment(s) of the P-60 kind, based on ER10 | U | 0 | A4 |
| 6 | Fresh-seed probe (106 trials, ~1 h wall) and full rehearsal (204 trials) of the final configuration | A | ~25–35 CPU-h; ~4–6 h wall | B1 (independent of selection) |
| 7 | Draft the pre-registration (label, seeds, disclosures, E1-7, reported items, freeze and provenance) | A, then U | 0 | C1–C9 |
| 8 | Adapt the E6 runner, verdict script and tests; build the E1-7 V3-turn records per arm; run the smoke test on non-scored seeds | A | V3 records ~1–2 CPU-h per arm; smoke ~1–2 CPU-h | D1–D4, D6 |
| 9 | Independent reviews of text and code together, iterated until one requires no changes; user approval | A, U | Tests only | E1, E2 |
| 10 | Status-line commit; clean tree; user's explicit go; scored run (~436–440 trials: 204 Option A, ~184 no-magnet, ~48–52 E1-7) | U, A | ~40–60 CPU-h; ~5–8 h wall at 8 workers, longer at 4–6 | D5, E4, the verdict |
| 11 | E1-8 on a quiet machine; abstraction write-up; sign-off | B, A, U | ~1 h | F1–F3 |

**Totals (rough):**
- Keep W3 unchanged (abstraction and reading (i) accepted): about 70–110 CPU-h from now.
- Redesign or a new magnet: add about 5 CPU-h for steps 3–4 (step 6 is needed either way).
- Plus the hybrid's rehearsal if pursued: about 25–35 CPU-h.

Calendar time is dominated by decisions and review rounds: M5's eight reviews took about a day.

**Why this order (INFERENCE).** Steps 0, 3, 4 and 5 can each invalidate the configuration, and so the rehearsal and any
drafted text. Doing the rehearsal (6) and the drafting (7–9) after them avoids repeating the M5 pattern of many
revision cycles.

---

## 5. Risks: ways the scored run could fail even with every item closed

Based on how M1, M4 and M5 failed:
1. **A tail event that the 204-trial rehearsal could not exclude.**
   - FACT: M5's 0.05 mm rehearsal passed 204 of 204 (P-30). The scored run then failed one rest trial at 0.560°,
     against a rehearsal maximum of 0.290° (P-51; E5 SUMMARY).
   - INFERENCE: under a simple exchangeable model with a uniform prior, P(204 of 204 | 204 of 204 rehearsal) =
     205/409 ≈ 0.5 (Laplace's rule of succession). Option A needs every trial to pass. W3's large margins on most
     metrics may make this pessimistic, but they do not remove it.
2. **Turn stalls that do not break through** (W3).
   - FACT: 56 % of moves clip, and the stall mechanism is contact geometry (SUMMARY Diagnostics).
   - INFERENCE: new setup draws and 20 new scrambles could produce a stall outside the turn window: turn error > 2° and
     an oracle mismatch.
   - This is the analogue of M4's failure, which was predicted from a known weakness (P-32 expected drift) and
     happened.
3. **Validity-regime exceedance on new seeds.**
   - FACT: M4 failed rule 2 in 2 trials, at 5.19° and 5.18° against 5° (P-37).
   - FACT: W3's largest near tilt is 18.42° against 20°, essentially the same value as C52's (`analysis.json`).
     INFERENCE: it is mostly set by geometry, so the risk is moderate.
   - Any new clamped-pair rule (A4) adds a new failure route that the rehearsal never measured.
4. **A criterion at the edge of a margin** (M1 failed by 0.004 and 0.031 mm on the pop check; G1 row).
   - FACT: W3's margins are wide: drift max 0.119° against 1°, rest 0.011° against 0.5°, snap 0.028° against 0.5°.
   - Turn error and penetration maxima for W3: **not found** in the ER9 summary or `analysis.json`. They need checking
     before drafting.
5. **The hybrid inherits L0's slip mode.** FACT (uncommitted, uninterpreted): HB2 had rest 0.516° on L0's slip seed
   16005. INFERENCE: weak anchors at 1–3 mm may not fully suppress the corner–edge slips that sank M5.
6. **Numerical and integrator sensitivity.**
   - FACT: implicitfast at 0.5 ms has a bounded energy oscillation of about 10 % with core magnets (M6 SUMMARY).
   - FACT: M5 flipped at timestep 0.75 ms in E1-7 (E5 SUMMARY), and M1 had numerical failures in E1-6c (G1 row).
   - The stall-and-jump dynamics may be timestep-sensitive. That would be an E1-7 fragility rather than a G1 failure,
     unless it reaches Option A trials.
7. **Run-procedure outcomes (INVALID or INCOMPLETE).**
   - FACT: memory kills have happened (ER7 deviation 2; ER9 Part E). M5's procedure makes them resumable interruptions
     (M5 prereg §2).
   - Commits to frozen paths during the run would block resumption.
   - The laptop sleeping is handled (E5 SUMMARY).
8. **Model credibility outside Option A.** A pass would still carry three disclosed abstractions:
   - the non-buildable placement (A7), unless redesigned;
   - a strength with no hardware anchor (A5);
   - turning torque near the 1 N·m limit, against a 0.09 N·m real-cube figure (A10).
   - INFERENCE: G1's "mechanism abstraction and limitations published" and the user's sign-off (F2, F3) could
     reasonably be withheld on these grounds even with Option A met.

---

## 6. Contradictions and inconsistencies found between documents
1. **ER9 approval record.**
   - ER9 PROTOCOL Status says the main session "records it in the DECISION_LOG".
   - No ER9 row exists (DECISION_LOG ends at P-66), and ER9 SUMMARY defers the row to the end of Part E. Parts A–D and
     the side checks are therefore unrecorded in the log.
2. **P-60 scope versus ER9's regime statement.**
   - ER9 SUMMARY Limits (last bullet) says W3's anchors pass through clamped z, and that C52 "is in the same regime …
     which P-60 covers".
   - P-60 covers only piece-to-core pairs on trajectories ER5's V3-turn validated. Those were on-axis pairs, and the
     same SUMMARY says the off-axis anchors have had no V3-turn.
   - Separately, ER7's and ER9's regime flag ignores clamped z, so "signal 3 met" does not show P-60 compliance.
3. **Tilt limit for hybrid corner–edge pairs.**
   - Part E amendment 1 flags all pairs at 20° (P-60).
   - The 4×3 table is validated to 7.5° for tilted pairs (ER5 V3b). M5 prereg §1 requires each configuration to use the
     tilt in its own V3 record.
   - Amendment 1 discloses that corner–edge 4×3 pairs were not in P-60's validation, but it keeps the 20° flag.
4. **Hybrid real-magnet equivalent.**
   - side_checks lists 4×2 N35/N45 for the hybrid and says its table would need validation beyond 5°.
   - It omits that the 7.5° extension of that table already failed (M4 prereg §9; P-24). This is an omission rather
     than a contradiction.
5. **The ER9 SUMMARY's probe status is stale and internally unreconciled.**
   - "Stopped at 75 of 318" and "All 112 hybrid probe records present on 2026-11-20" appear in the same document.
   - The working-tree log shows two restarts and 275 records by 2026-11-21.
6. **Labels in ER9 SUMMARY.**
   - "Outcome in brief" states as fact that M5's corner–edge magnets "are what prevent" the stall. The Diagnostics
     section and Part E label it `INFERENCE` from single-seed replays.
   - The Part D table calls E1-2 "single moves" and E1-3 "short sequences". M1 prereg §4 and ER7 call E1-3 "half
     turns".
   - The W3 "CPU time 22.8 h" is the `wall_h` field (summed per-trial wall time) in `analysis.json`.
7. **CLAUDE.md versus the decision log on subagents.**
   - CLAUDE.md says "Do not spawn subagents"; D-15 is still "Proposed".
   - P-19 and P-20 record a user-approved standing exception, used for reviews and the ER9 side checks. CLAUDE.md was
     not updated.
8. **VALIDATION_PLAN is stale relative to Phase 1 practice.**
   - Its Status says "All tests below start NOT RUN", and it does not point to the pre-registrations where Option A and
     the E1 experiments are defined (M1 prereg §4–§5).
   - Not a contradiction in substance, but a reader of VALIDATION_PLAN alone would not find the operative G1 criteria.
9. **The lapsed M6 draft versus the E6 code** (known, and listed in E6 README): instrumented rest included or not;
   clearance factor; 1/1.5 versus 0.67 scale. Any reuse must pick one explicitly.
10. **Minor:** DECISION_LOG row P-15 sits after P-66, out of order.

---

## 7. Sources read
`CLAUDE.md`; `RUBIKNETIC_MASTER_SPEC.md` §2 and §4–§5; `docs/VALIDATION_PLAN.md`; `docs/DECISION_LOG.md` (all rows, the
gate table and the template); `experiments/PHASE_1_PREREGISTRATION.md`; `PHASE_1_M4_PREREGISTRATION.md`;
`PHASE_1_M5_PREREGISTRATION.md`; `M5_PREREGISTRATION_REVIEW1–2` in full; `REVIEW5` in full; headings and required items
of `REVIEW3`, `4`, `6`, `7` and `8`; `PHASE_1_M6_PREREGISTRATION.md`; `E6_scored_m6/README.md`; `E5_scored_m5/SUMMARY.md`;
`ER5_magnet_validation/PROTOCOL.md` and `SUMMARY.md`; `M6_core_magnets/SUMMARY.md`;
`ER7_core_magnet_rehearsal/PROTOCOL.md` and `SUMMARY.md`; `ER9_anchored_core_layouts/PROTOCOL.md`, `SUMMARY.md` and
`side_checks/README.md`; `ER9…/results/full/W3/analysis.json`; the tails of `full_W3_log.txt`, `probe_partC_log.txt` and
`hybrid_probe_log.txt` (uncommitted); and grep hits in `docs/research/` on turning torque. No large result directory was
opened, and no record was read.
