# DRAFT — not approved

**What this is.** A plan, written **before any Part G dynamic result exists**, for what to do after the Part G probe
(G.8) for each plausible outcome. The point is that every follow-up is chosen before the outcome is seen. Drafted
2026-11-22 by a subagent from the repository's documents. No simulation was run. Nothing here is a decision or a
result. The only results read are the committed static files `results/hybrid_g/static/P1_*.json`, `P2_*.json`,
`P3_*.json` and `P4_0.json` (commits `3935fd3`, `53e433f`, `fa1b6ae`). The uncommitted `P4d_*.partial.jsonl` files and
everything else under `results/hybrid_g/` were not opened.

**Labels.** `FACT` (file and section given), `INFERENCE` (reasoning or hand arithmetic, not computed by project code),
`PROPOSAL` (the user decides). "PROTOCOL" means `experiments/ER9_anchored_core_layouts/PROTOCOL.md` Part G. "Gap
analysis" means `proposals/G1_GAP_ANALYSIS.md` (itself a draft).

---

## 0. Static facts this plan relies on (verified in the committed files)

| Quantity | L0 | PG8 N35 | PG8 N42 | PG8 N52 | PG20 N35 | PG20 N42 | PG20 N52 | PG20r N52 | C52 |
|---|---|---|---|---|---|---|---|---|---|
| Static U-turn peak, N·m (`er3.turn_peak_Nm`) | 0.083 | 0.144 | 0.156 | 0.174 | 0.194 | 0.216 | 0.252 | 0.103 | 0.181 |
| Corner+edge cluster about face axis, mN·m/rad (`probe5`, pair nnp+n0p) | −421 | −177 | −130 | −56 | +17 | +102 | **+233** | −335 | +648 |
| Single edge / single corner (probe5), mN·m/rad | −929 / −420 | −937 / −177 | −938 / −130 | −939 / −56 | −742 / −173 | −705 / −125 | −648 / −50 | −1220 / −61 | +282 / +368 |
| Edge spin / corner twist (min), mN·m/rad | 118 / 118 | 121 / 118 | 121 / 118 | 121 / 118 | 121 / 116 | 121 / 116 | 121 / 116 | 121 / 118 | 0 / 0 |
| Layer stiffness, N·m/rad | 1.99 | 3.00 | 3.19 | 3.49 | 3.75 | 4.09 | 4.61 | 2.41 | 2.58 |
| Near-zero eigenvalues (\|λ\| < 1) | 9 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 26 |

FACT: `results/hybrid_g/static/P2_<arm>_<grade>.json` (commit `3935fd3`). The task brief's numbers (cluster +233 / +17
/ −56 / −421; peaks 0.083 / 0.174 / 0.144 / 0.252 / 0.194) all match these files.

Other static facts:
- **P1 passes both arms** (FACT, `P1_PG8.json`, `P1_PG20.json` `stops`). Margins: PC tilt 17.93° (PG8) and 18.37°
  (PG20) against 20°. Cross-type piece-to-piece minimum 9.335 mm against 9.0. Core-to-4×2 bound 8.207 mm (PG8) and
  8.117 mm (PG20) against 8.0. Smallest surface clearance 0.85 mm.
- **P1's rigid E1-5-like poses** (reported only, contacts ignored; FACT, `e15_like.per_alpha`) bound what E1-5 could
  reach:
  - CE tilt exceeds 5° from α = 4°;
  - CE clamped z appears from α = 2°;
  - cross-type near pairs (all perpendicular) appear from α = +3° / −5°, down to 4.25 mm;
  - PC path deviation d reaches 10.4° at α = 14°;
  - PG20 only: PP3 near pairs from α = +12°.
  - E1-5 sweeps α = 0–20°, completing at ≤ 11.6° (FACT, `experiments/PHASE_1_PREREGISTRATION.md` E1-5 row).
- **P3:** no hard stop for either arm. Smallest gap at home 0.85 mm. Both known fit misses stand: corner wall
  0.175 mm and core cover 0.202 / 0.292 mm, against 0.4 mm (FACT, `P3_*.json` items).
- **P4.0 passes at every θ** in both pair orders (FACT, `P4_0.json` verdict). Worst force error 1.18 % of Fn. Worst
  torque error 3.63e-5 N·m against a 5.34e-5 N·m tolerance (68 % of it). Summed run 201 s.
- **D_val is not yet recorded.** P4.d is still running (git status). The runner refuses an arm without it (PROTOCOL
  G.8).

---

## 1. Outcome table

The signals (FACT, PROTOCOL G.8) are: S1 snap-back; S2 rest ≤ 0.5° and 0/20 slips; S3 E1-2 and E1-5 pass; S4 no
operational trial out of regime (G.4, with the recorded D_val). **Turner torque is reported, not a signal** (G.1,
G.8): it is measured against the realism reference of about 0.2 N·m, with a warning level at 0.45–0.5 N·m.

Costs are FACT from G.11 (summed per-trial wall time) unless marked otherwise:
- full rehearsal: PG8 12–18 h; PG20 20–35 h;
- probe: PG8 2.5–5 h; PG20 4–10 h; U5 extension 2–5 h;
- ER10-type force-law check: 3–8 CPU-h (gap analysis §4, step 4).

| # | Outcome | Fixed next step (protocol) | Proposed follow-up (PROPOSAL) and rough cost | User decision needed | What would make it post hoc |
|---|---|---|---|---|---|
| **O0** | Before the probe: P4.d gives D_val < 0.5° for an arm, or the G.7 cost stop fires | The arm stops (G.6 P4.d). The cost stop returns to the user (G.7) | If D_val < 0.5°: report it and do not run that arm. U2 "proxy" is available only as a disclosed reversal of P-69. If the cost stop fires: the user decides (G.7), e.g. fewer workers or a later start | Whether to reverse U2 (strict / proxy) | Switching U2 after seeing which value lets more trials pass |
| **O1** | Both arms meet S1–S4 | Select the lower median E1-2 torque; ties go to fewer magnets (PG8). Then the G.9 full rehearsal of that arm only | Run G.9 as fixed (PG8 12–18 h or PG20 20–35 h). Report the other arm's probe in full. INFERENCE: PG8 is more likely to be selected (lower static peak), but statics have mispredicted dynamics twice (G.2) | Only the torque gate of pre-commitment P3 (§5), if the selected arm's median is ≥ 0.45 N·m | Rehearsing the unselected arm too, or switching arms because of its rest or torque margins |
| **O2** | Only PG20 meets S1–S4 (including PG20 meeting all four with a median ≥ 0.45 N·m while PG8 fails) | PG20 → G.9 (20–35 h). G.9's reading: with any move at the clip, "reported beside W3; the choice goes to the user" | INFERENCE (G.2): the median is likely above the warning. PROPOSAL: apply pre-commitment P3 (§5) before starting the 20–35 h. Also report the ER7-style per-move torque split (contacts vs magnets) on seed 16100 from the smoke replay already in G.7 (no new run) | Whether a torque above the warning blocks the rehearsal (decide **now**) | Deciding the torque threshold after the PG20 median is known |
| **O3** | Only PG8 meets S1–S4 | PG8 → G.9 (12–18 h) | As fixed. Watch E1-1 in the full run: PG8's cluster stays negative (−56, FACT §0), so its rest pass rests on contacts, as L0's does (INFERENCE). Report the 60-seed slip comparison | None before G.9 | Adding rest seeds or criteria after seeing PG8's rest margins |
| **O4a** | Neither: PG8 fails S2 (rest/slip), PG20 fails S1 (snap-back) | **Part G ends;** probe report; next step to the user (G.8) | (i) Before any new arm: one snap diagnostic replay of PG20 on seed 16568 (ER7's `snap_diag.py`, under 1 h), because a PG20 snap failure contradicts G.2's INFERENCE (L0's spin/twist should restore). (ii) Then, only if the user approves, the **pre-declared intermediate probe** of §2 (V1 PG20 at N42, V2 PG20 at N35): about 4–10 h each plus rest40 about 1–2 h each (INFERENCE from G.11) | Whether to run the §2 intermediate probe, and with which pre-declared arms | Choosing the grade after seeing how far each arm missed. Mitigation: fix §2's arms and selection rule now |
| **O4b** | Neither: PG8 fails S2; PG20 meets S2 but fails S3 (E1-2 or E1-5 turn failure, e.g. a stall past the window) | Part G ends; to the user | Report the failing trials. Then a clip-raised turner diagnostic on rehearsal seeds (gap analysis A10, 2–4 CPU-h), so the stall is measured uncensored. V1/V2 as in O4a only if the failure is torque-related | The turner policy (gap analysis §3.1 item 4) | Raising the 1 N·m clip for the probe trials themselves (the clip is frozen rig, M1 §1) |
| **O5** | Both (or the otherwise-passing arm) fail **only** S4, and every out-of-regime evaluation is X (`cross_near > 0`) or PC-off (d > D_val) | Part G ends (none meets all four). G.9's reading: accepting these is "an amendment of the P-60 kind, the user's decision" | (i) Report the counts by class, by d and by distance, per sub-experiment (E1-5 is expected; FACT §0, P1 E1-5-like envelope). (ii) **ER10-type check over an envelope fixed now from P1** (not from the probe's poses): X pairs 4.25–8 mm, all tilts to perpendicular; PC pairs at d up to 10.4°. Fine charge model, ER5's pass rule. 3–8 CPU-h plus code for mixed-size fine pairs (INFERENCE: `er5_checks` handles one size; TODO check). (iii) If it passes and the user amends: re-read S4 from the existing records (the stats are already logged), keeping "not met under the original rule" on record. If it fails: move the on-axis piece magnets (U8's alternative), which is a new Part | Approve (ii); later, the amendment itself | Fitting the check envelope or the tolerance to the poses the probe produced; dropping X near pairs from the rule after seeing them |
| **O5b** | S4 fails through **CE** (tilt > 5°, CE clamped or CE perpendicular) | As O5: Part G ends | First resolve G.10's TODO: L0's 12.59° by sub-experiment, from ER7's records. If L0's own operational trials exceed CE's 5°, the failure is inherited from M5's magnets, not caused by the core pairs. Report it so; no new check fixes it (the 4×2 table's 7.5° extension already failed, P-24) | Whether L0 is held to the same per-class rule in the report | Exempting CE pairs after seeing them |
| **O6** | Harness or numerical failure: trial exceptions, killed workers, NaN/instability, GS-type mismatch | Exceptions are recorded as failed trials; killed workers stop the run for resume (FACT, commit `ddda5eb`). Records are created exclusively, so the run resumes (G.8) | Diagnose with a single-trial replay. Record a deviation. Resume. A trial recorded as failed by an exception stays failed in the fixed reading; a rerun is reported beside it only after a code-review finding and a recorded deviation. A numerical trigger (energy growth, penetration) gets a diagnostic replay at 0.25 ms or with RK4, **reported only** (M6: 10 % energy oscillation at 0.5 ms) | Whether a confirmed harness bug justifies rerunning the affected trials (a deviation) | Rerunning only the failed trials of the arm you prefer |
| **O7** | Mixed partial: an arm meets S1–S3, misses S2 by < 0.05° (as HB2 did, 0.516°) | Not selected; Part G ends if no arm meets all four | None beyond O4a. Report the margin | — | Treating a near miss as a pass |

---

## 2. Candidate intermediate variants (defined now, for "PG8 too weak / PG20 too stiff")

INFERENCE for all rows: the probe would reuse G.8's 106 trials, signals and selection rule, plus U5's rest40. All rows
stay unscored rehearsal on 16000–16999. The ordering is a PROPOSAL.

| ID | Variant | What changes | Force-law coverage | Static rows | Rough cost | Fit | Assessment |
|---|---|---|---|---|---|---|---|
| **V1** | PG20 at **N42** | Core grade only | P-60 covers it ("grades by exact scaling"). P4.d's D_val transfers (relative pass is grade-invariant, G.6 P4). Needs a table self-check: the N42 table equals the N35 table × Br² exactly (M6 S1-style; seconds) | **Yes** (`P2_PG20_N42`): cluster +102, peak 0.216 | Probe 4–10 h + rest40 1–2 h | Same misses as PG20 | **First choice.** Cluster positive with margin; peak between PG8 N52 and PG20 N52 |
| **V2** | PG20 at **N35** | Core grade only | As V1; the 4×3 N35 table is ER5's own validated table | **Yes**: cluster +17, peak 0.194 | As V1 | Same | Second. Caution: +17 is a small difference of large terms, and pair order moves stiffnesses by up to about 4 % (deviation 1; 4 % of L0's −421 ≈ 17). Its sign is not robust (INFERENCE) |
| V3 | PG20 mixed: corner core pairs N52, edge core pairs N35 (or the reverse) | Per-class grade | Each pair is an exact scaling of a validated table, so P-60 should cover it (INFERENCE); no V3-turn has mixed grades in one core set (TODO: P4.0-type check, about 200 s) | **No** (P2 takes seconds per row, FACT `wall_s` 3.2 s) | P2 + P4.0-type: under 1 h; probe as V1 | Same | Only if V1 is excluded. Two parameters invite tuning |
| V4 | PG8 + a **subset** of edge core pairs | Breaks the cube symmetry of the core | **Not covered.** G.4's argument that every arc is equivalent to the validated one needs a symmetric core. Every slot then needs its own V3-turn, and P4.d must be redone | No | New wrapper, P1–P4 (hours), probe | Same | **Not recommended.** The 12 edges form one orbit, so any proper subset is asymmetric. Pieces would be held differently depending on which slot they occupy |
| V5 | PG8 or PG20 at a **larger core clearance c** (e.g. 0.3–0.4 mm) | Weaker core pairs; larger core cover | **Outside P-60** (c = 0.2 mm only). Needs an ER5-style V3-turn at the new c (about 4,500 s wall per configuration incl. a 530 s table build, gap analysis §4), P4.0/P4.d at the new c, and E1-7's clearance arm | ER6 has core-only rows at c = 0.1/0.2/0.3 (P-58 (3)); no composite rows | V3-turn about 1.3 h per configuration + P4.d (8 h cap, G.6) + P1–P3 minutes + probe | Moves toward the cover miss (0.20/0.29 vs 0.4 mm). Magnitude TODO from `realfit/stage2b` | Worth defining only together with U1 F-B, as one fit-and-strength step |
| V6 | PG20r (repelling edges, U4) | 12 edge piece moments reversed | GS6 shows exact oddness, so it is probably covered (INFERENCE); P-60 does not say so explicitly (G.3) | **Yes**: cluster −335, edge slide −2559, peak 0.103 | Probe 4–10 h | Same | **Not recommended.** Statically worse than PG8 N52 on the slip cluster (−335 vs −56), as G.3 predicted (B1 has no radial freedom) |

**Rule to fix now, if the user wants an intermediate probe (PROPOSAL).**
- Run V1 and V2 together, under G.8's signals and selection rule unchanged.
- No other variant without a new committed Part.
- V1 and V2 are chosen from static rows that exist today, not from the probe's margins.

---

## 3. Path from a successful G.9 rehearsal to a scored G1 run (ordered checklist)

The order follows gap analysis §4: items that can change the configuration come before the fresh-seed rehearsal and
the drafting. Costs are INFERENCE from the figures cited.

| Step | Item (G.9 reading list / gap ID) | What it needs | Rough cost | Owner |
|---|---|---|---|---|
| 1 | Record Part G (B2, B3) | Commit the records; an independent code review; an ER9/Part G decision-log row | Review: tests only | A drafts, U approves |
| 2 | **Fit, U1 → F-B or F-C** (A7; P-67 item 3) | F-C: sourced minimum wall and cover for moulded pockets (not in the repository; needs web access). If the sourced value is ≤ 0.175 mm, both misses pass unmoved. F-B: CAD-relative positions (mapping B), a new L0-fit control arm, a V3-turn at the new core gap (outside P-60), P1–P4 rerun, a new probe and rehearsal ("effectively a new Part", G.6 P3) | F-C: research only. F-B: 3–8 CPU-h validation + probe + rehearsal ≈ 25–45 h | U chooses; A executes |
| 3 | **Turner torque** (A10; P-67 item 4) | Policy: report only (M5 precedent), a criterion fixed before scoring (disclosed as post hoc), or a rig-limit amendment. Optionally a clip-raised diagnostic first | 0, or 2–4 CPU-h | U |
| 4 | Force-law coverage and amendments (A2, A4) | CE 5°, PC on-path (P-60 + P4.0), PC-off D_val, X dipole-only. Any accepted X or PC-off near pair needs an amendment (O5). **Lateral offsets 6–8 mm against V3a's 0–6 mm: disclosed** (G.10) | 0–8 CPU-h | A, then U |
| 5 | Composite system status (A3) | Its own review and V4/V5/V6 (G.0, done before GS1; cite them). An M6-style survey with clamped-z counts for the final layout | under 1 CPU-h | A |
| 6 | Strength meaning (A5) | INFERENCE: under magnet type (b) the magnets are catalogue grades at scale 1 (4×2 N35, 4×3 N35–N52), so A5 is largely met. Still needed: a sourcing check that the chosen 4×3 grade is stocked | research only | A |
| 7 | **Independence from selection: fresh seeds** (B1; G.10; C2) | A fresh-seed probe and full rehearsal of the exact frozen configuration on an unused, searched range (e.g. 19000–19999; repository search recorded; not 17000–17999, not 16700–16739, 16900–16999 or 18000–18099) | ≈ 1 probe + 1 rehearsal: PG8 15–23 h, PG20 25–45 h (G.11) | A, after U |
| 8 | **E1-7 coverage incl. the 1.5× ideal-magnet arm** (A6; C6) | Arms: grade factors and strength 0.67 (the E6 code's choice); V3 coverage by linearity. No clearance arm unless V5's V3-turn exists. Disclose the expected fragility: at 0.67, PG8's cluster moves toward L0's (INFERENCE) | V3 records 1–2 CPU-h per arm (gap analysis §4, step 8) | A |
| 9 | Pre-registration text (C1–C9) | Label (M7?); seed map; §0 post-hoc chain (P-51 → ER1–ER9, U1–U8, deviations 1–2, U6's waived ER3 criterion 1, the pair-order dependence of deviation 1); provenance (the author has seen all rehearsal data) | 0 CPU | A drafts, U |
| 10 | Runner, verdict, tests, smoke (D1–D4, D6) | Adapt E6's runner with G.4's per-class rule and the composite system; a smoke run on non-scored seeds with an interruption and resume | smoke 1–2 CPU-h | A |
| 11 | Reviews until one requires no changes (E1, E2) | Text and code together; reviewers do not read results | about a day (M5: eight reviews) | A, U |
| 12 | Status-line commit, clean tree, the user's explicit go (D5, E4) | — | 0 | U |
| 13 | Scored run | about 436–440 trials | 40–60 CPU-h for a W3-cost arm (gap analysis §4, step 10). INFERENCE: PG8 nearer the low end, PG20 nearer the high end | A |
| 14 | Sign-off (F1–F3) | E1-8 on a quiet machine; the abstraction write-up (P-58, no radial freedom, no collision geometry); the user's sign-off | about 1 h + writing | B, A, U |

**Rough total from a successful G.9 to a scored verdict** (INFERENCE): with F-C, about 70–110 CPU-h, matching the gap
analysis; add about 25–45 h with F-B. Calendar time is dominated by decisions and review rounds.

---

## 4. Risks that would invalidate a good-looking probe

| Risk | Basis | Consequence / mitigation |
|---|---|---|
| **Rehearsal seeds reused** | FACT: 16000–16655 were used for ER7 diagnostics, W3's selection and Part E (G.10). INFERENCE: the probe and G.9 rerun the same trials, so G.9's reproduction check is not independent of the probe | A pass is "meets the rehearsal signals", never a candidate. Step 7 (fresh seeds) is the remedy |
| **Weak power at rest** | FACT: 0/20 has a 95 % upper bound of 17 %; 0/20 against 2/20 gives p ≈ 0.49 (G.10, U5). INFERENCE (hand-computed hypergeometric): over 60 seeds, an arm with 0/60 is "fewer slips than L0" at p ≤ 0.05 only if L0 has ≥ 5/60 slip seeds (p = 0.029 at 5, 0.059 at 4). L0's ER7 rate (2/20) projects to about 6/60 | If L0 shows ≤ 4/60, even a perfect arm reads "not distinguishable". Do not add seeds after the fact |
| **Rehearsal-to-scored tail** | FACT (gap analysis §5.1): M5 passed 204/204 in rehearsal, then failed one scored rest at 0.560° (rehearsal max 0.290°) | A rest maximum near 0.5° (HB3 had 0.463°) is weak evidence. Report the margin, not just the flag |
| **Statics vs dynamics** | FACT: ER3 passed C52 statically, then it failed snap-back (ER7); Part A's static U-turn peak missed W3's stall (G.2). FACT §0: static U-turn peaks (L0 0.083, C52 0.181) sit far below the dynamic E1-2 medians (0.144, 0.700; SUMMARY Part E) | The static torque ranking (PG8 < PG20) and the cluster signs only guide. The probe decides (G.2) |
| **Stiffness sign sensitivity** | FACT (deviation 1): pair order moves stiffness by up to about 4 %. INFERENCE: PG20 N35's +17 and PG8 N52's −56 are within a few × that of zero | Do not choose a grade by the sign of a small cluster value |
| **Regime envelope in E1-5** | FACT §0: rigid E1-5-like poses produce CE tilt > 5°, X near pairs down to 4.25 mm and d up to 10.4°. FACT: L0 had no clamped pairs and a max tilt of 12.59° in ER7 (ER7 SUMMARY); where that 12.59° occurred is G.10's open TODO | S4 may fail for reasons shared with L0. Resolve G.10's TODO before reading (§5) |
| **Force-law margins** | FACT: P4.0's torque error is 68 % of tolerance; ER5's worst was 4.1 % against 5 % (P-58); U8: dipole error 3.4–7.4 % for X pairs at 7.3–8.2 mm | A pass inside these margins is still a proxy for real magnets, and the ideal-magnet caveat (up to 1.5×) stands |
| **Selection among two arms on the same seeds** | INFERENCE: picking the better of two arms on the same 106 trials favours the winner | Disclose in any later §0; fresh seeds (step 7) |
| **Numerics and run procedure** | FACT: implicitfast has a 10 % energy oscillation with core magnets (M6); M5 flipped at 0.75 ms in E1-7; low-memory stops recur (ER7 deviation 2, Part E) | Exceptions count as failures (`ddda5eb`). Report worker restarts. Timestep sensitivity belongs to E1-7, not to this probe |
| **Fit deferred** | FACT: under F-A an arm that passes is "fit not met"; F-B invalidates Part G's dynamics (G.6 P3) | A good probe does not settle buildability. U1 must be decided before step 7 |

---

## 5. Pre-commitments recommended for approval before the probe is read (PROPOSAL)

1. **"Neither arm" follow-up fixed now.** If no arm meets S1–S4 (O4a/O4b), the only follow-up probe is V1 + V2 (PG20
   at N42 and N35), run together under G.8's signals and selection, after one PG20 snap diagnostic replay. Nothing
   else (V3–V6, c changes, PG20r) without a new committed Part.
2. **Regime handling fixed now.**
   - Before the probe is read: resolve G.10's TODO (L0's 12.59° by sub-experiment, from ER7's own records). L0 is then
     reported under the same per-class rule.
   - If S4 fails only through X or PC-off evaluations (O5): the ER10-type check uses the envelope fixed above from P1
     (X 4.25–8 mm at any tilt; PC d ≤ 10.4°) with ER5's pass rule. S4 is re-read only after an approved amendment.
     "Not met under the original rule" stays on record.
3. **Torque gate before G.9 fixed now.** Choose one:
   - (a) the protocol default: the selected arm goes to G.9 whatever its median; or
   - (b) pause for the user if the selected arm's probe E1-2 median is ≥ 0.45 N·m, or any probe move reaches the
     1 N·m clip.
   In either case the unselected arm is not given a full rehearsal.

Also worth fixing now (lower priority): the fresh-seed range for step 7, with its repository search recorded.
