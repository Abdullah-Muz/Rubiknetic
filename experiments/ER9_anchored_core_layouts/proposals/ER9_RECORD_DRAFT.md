# DRAFT — not approved

**Status: PROPOSAL, 2026-11-22.** Drafted under P-67 items 6 and 7. Nothing here is recorded, approved or in force.
`docs/DECISION_LOG.md`, `../PROTOCOL.md` and `../SUMMARY.md` are unchanged. Each part goes in only on the user's
approval, and only after Part E's probe is reported.
- **Part E data were not read for this draft.** Nothing under `../results/hybrid/` or `../hybrid_probe_log.txt` was
  opened. Every Part E number below is either already in `../SUMMARY.md` or `../PROTOCOL.md` (amendments 1–2), or is a
  placeholder.
- Labels: `FACT` (file or commit named), `INFERENCE`, `ASSUMPTION`, `PROPOSAL`. Nothing in ER9 is a `VALIDATED_RESULT`.

---

## 1. Draft decision-log row (proposed id P-71)

Format follows P-55 to P-67: one table row, kept on one line so the table renders (see item 12 in section 4).
Placeholders in square brackets are filled once the probe is reported and the user has decided U7.

```markdown
| P-71 | **ER9 recorded: anchored core-magnet layouts (Parts A–D), side checks and corrections; Part E [PART E PROBE RESULT — pending report]** (proposed under P-67 item 6; exploratory and unscored). [`../experiments/ER9_anchored_core_layouts/SUMMARY.md`](../experiments/ER9_anchored_core_layouts/SUMMARY.md); protocol `5edce62`, fixed 2026-11-19 before any ER9 computation. Each later part and amendment was committed before its runs: Part C addendum `1b1b6f0`, Part D addendum `a4959e5`, runner `0918147`, Part E addendum `1cce081`, amendments `d637ab8` and `7290bd1`. Only ER7's rehearsal seeds were used (16000–16655); no scored seed was touched. **Approval of ER9 itself (FACT, not recorded until now):** the main session treated the user's "please find a solution to these problems, be creative" (2026-11-19) as approval under P-63's delegation (PROTOCOL.md, Status). No row recorded it; this row does. **Part A** (`1912a7f`, static screen): self-checks S1–S3 pass. 3 of 243 layouts pass. The one selected is N42, edges with 2 pairs at 20° and corners with 3 pairs at 16°, set toward the centres, 96 magnets. FACT: it leaves 6 zero modes, the centres, against C52's 26. **Parts B and C** (`1b1b6f0`, `a101ad8`; deviation 1 `e65775c`, a bookkeeping field): S1, S2, W1, W2 and W3 each meet the four probe signals, 106 / 106. The turner reached its 1 N·m limit in 20, 20, 20, 16 and 9 of 24 E1-2 moves. The fixed rule (lowest median E1-2 turner torque, 0.947 N·m) selected W3 (N35 × 0.3). **Part D** (`5a85a05`): W3 passed 204 / 204 and met ER7's three signals. L0 passed 201 / 204 and C52 194 / 204 on the same seeds. The probe records were reproduced. W3's turner was at the 1 N·m limit in 771 of 1,376 moves (68 trials), against 0 for L0. Its median was 1.0 N·m, against L0's 0.203 N·m. **Diagnostics** (single seeds, exploratory): the layer stalls at about 7° even with almost no magnets. INFERENCE: the stall belongs to B1 without in-layer magnets, not to the anchors, and M5's corner–edge magnets attenuate it (L0 peak 0.461 N·m). An independent code review (`abca460`) found no verdict change. **Side checks** (`d20fde5`, corrected `3f6219e`). No simulation was run. The CAD licence is unconfirmed, so only numbers were kept. FACT about the GrabCAD real-mechanism CAD: W3's anchor geometry does not fit. Each corner anchor has material only from 25.0 mm along its line, against a magnet span of 22.35–25.35 mm, so 83 % of it is in air. The edge anchors at 20° break out of the foot by up to 0.58 mm. The placements that fit lie outside Part A's screened range. Whether any of them holds the pieces was not computed. Catalogue: a strength scale multiplies Br². W3 corresponds to about a 3 × 3 N45/N42 at a 1.8–1.9 mm face gap, which has no validated table. The gap is uncertain by about 0.5 mm until pull is measured on real magnets. **Negative results kept:** (1) W3 does not fit the real CAD. (2) W3's turner torque is unrealistic. It is about 11× the only verified real-cube figure of 0.09 N·m ([`research/TURNING_TORQUE_FINDINGS.md`](research/TURNING_TORQUE_FINDINGS.md), `7655e5a`, `edd624a`) and above P-67 item 4's 0.45–0.5 N·m warning level. The 1 N·m clip also hides the true demand. (3) Signal 3 is the protocol's 20° proxy, not a validation; ER5's generic tilt check (V3b) covers the 4 × 3 table to 7.5° only. (4) P-60 does not cover W3's off-axis anchor paths: it covers on-axis paths at c = 0.2 mm only, and there is no V3-turn check of the off-axis placement. (5) The rehearsal seeds also chose the arm, so they are not independent. (6) The 0.3 scale is not a catalogue magnet. **Corrections after review, kept on record:** the stiffness target's rationale was wrong: the leftovers are gravity sag, not joint friction (Part C addendum). The stall is independent of the anchors, not merely of strength. Part E's first specification used the 4 × 2 table past its validated 5° (amendment 1). "Suppress" became "attenuate" (`102fe11`). A Limits line said P-60 covers W3's clamped pairs, which it does not, and signal 3 is now called a proxy (`3f13173`, from the G1 gap analysis, along with the E1-3, wall-time and stop-history labels). The two snap-back error definitions are labelled (L0 0.269° and 0.118°; `abca460`). The side-check notes were corrected: 3 × 3 also fits at 5.5–6.5°, the core-side small-angle bounds are unchecked, the hybrid's corner walls are 0.175 mm, and 20° holds only on the paths ER5 checked (`3f6219e`). **Part E** (hybrid HB1–HB3: M5's 48 positions plus W3's anchor geometry at c = 1, 2 and 3 mm; 144 magnets, 4 × 3 N35 × 0.756). The self-check passed. Smoke replays peaked at 0.525, 0.432 and 0.118 N·m. FACT, known before the probe: signal 4 cannot be met, because of 12 perpendicular near pairs per quarter turn. For them the dipole formula is within 3.5 % of the charge model in torque about the turn axis; that is a measured error size, not a validation. Probe (318 trials): [PART E PROBE RESULT — pending report]. Records committed at [commit — pending]. Full rehearsal: [run under Part E's selection rule / not run: Part E recorded as probe-only by amendment 3, under P-67 item 7 and decision U7 — pending the user's decision]. **What this row does not do:** nothing in ER9 is scored or validated. **G1 is NOT PASSED** and M5 stays NOT PASSED. W3 is not taken forward (P-67 item 1). No mechanism is selected | **DRAFT 2026-11-22 — awaiting the user's approval** (proposed under P-67 item 6; not recorded until approved and until Part E's probe is reported) |
```

Before submission, check:
- every placeholder is filled from the reported probe;
- the Part E clause uses only numbers from the committed probe report;
- if U7 keeps the hybrid in contention, the full-rehearsal clause reads "pending the full rehearsal".

---

## 2. Draft Part E section for SUMMARY.md

This replaces the current "Part E — hybrid … (in progress; no result)" section once the probe is reported. Every
non-placeholder fact is reused from the current SUMMARY.md, or from PROTOCOL.md Part E and its amendments.

> ## Part E — hybrid: M5's 48 positions plus weak anchors [status: probe complete / probe-only — pending]
>
> **Question (Part E addendum, `1cce081`).** Can M5's corner–edge magnets, which tie the pieces of a turning layer to
> each other, keep the turning torque near L0's while weak anchors hold the pieces at rest, where L0 fails on E1-1
> slips? PROPOSAL tested here, chosen after single-seed replays on an ER7 seed.
>
> **Arms (amendment 1, `d637ab8`).** Every arm uses M5's `layout()` (48 corner–edge magnets) plus W3's anchor geometry
> (edges with 2 pairs at 20° and corners with 3 pairs at 16°, toward the centres; 96 magnets), 144 magnets in all. The
> magnet type is 4 × 3 mm N35 at scale 0.756. At that scale the corner–edge pull matches M5's 4 × 2 pair (1.644 N).
> It is not a catalogue magnet.
>
> | Arm | Anchor clearance c | Anchor pair pull | Tilt limit used |
> |---|---|---|---|
> | HB1 | 1 mm | 0.80 N | 20° (proxy) |
> | HB2 | 2 mm | 0.39 N | 20° (proxy) |
> | HB3 | 3 mm | 0.23 N | 20° (proxy) |
>
> **Trials (probe, as Part B).** Each arm runs 106 trials on ER7's seeds 16000–16655, 318 in all:
> - E1-1 rest: 20 trials, scored 10 s rest only;
> - E1-2 quarter turns: 24;
> - E1-5 forgiveness: 42;
> - E1-5s snap-back: 20.
>
> **Before the probe.** The self-check passed: W3's probe records were reproduced with 0 differences. Smoke replays
> (seed 16100) peaked at 0.525, 0.432 and 0.118 N·m, with no step at the limit. Signal 4 cannot be met: 12
> perpendicular near pairs per quarter turn, dipole within 3.5 % of the charge model (amendment 2, `7290bd1`).
>
> **Probe run.** The run was stopped by low-memory stops at 75, 223 and 275 of 318 trials. The runner skips existing
> records. Final completion: [date — pending]. Records committed at [commit — pending]. Integrity check:
> [N records, all decompress, configuration per arm — pending].
>
> **Probe signals per arm** (signals 1–4 as in Part B; eligibility as in amendment 2)
>
> | Arm | Trials passed (of 106) | S1 E1-5s | S2 E1-1 rest ≤ 0.5° | S3 E1-2 and E1-5 | S4 regime | Max near tilt | Eligible |
> |---|---|---|---|---|---|---|---|
> | HB1 | [pending] | [pending] | [pending] | [pending] | not met (amendment 2) | [pending] | [pending] |
> | HB2 | [pending] | [pending] | [pending] | [pending] | not met (amendment 2) | [pending] | [pending] |
> | HB3 | [pending] | [pending] | [pending] | [pending] | not met (amendment 2) | [pending] | [pending] |
>
> **Reported beside the Parts B and C arms (same 106 seeds)**
>
> | Arm | Rest max | Snap-back max error | E1-2 turner median | Moves at the 1 N·m limit (of 24) |
> |---|---|---|---|---|
> | L0 | 0.568° | 0.27° | 0.144 N·m | 0 |
> | C52 | 3.4e-6° | 1.01° | 0.70 | 4 |
> | W3 | 0.011° | 0.028° | 0.947 | 9 |
> | HB1 | [pending] | [pending] | [pending] | [pending] |
> | HB2 | [pending] | [pending] | [pending] | [pending] |
> | HB3 | [pending] | [pending] | [pending] | [pending] |
>
> Also reported: the turner median against P-67 item 4's realism reference (about 0.2 N·m) and warning level
> (0.45–0.5 N·m) [pending], and steps per second [pending].
>
> **What the probe can show.**
> - Whether each arm meets signals 1–3 on these 106 rehearsal trials.
> - How its E1-2 turner torque compares with L0, C52 and W3 on the same seeds.
> - Which arm is eligible, and which one the fixed rule would select (lowest median E1-2 turner torque; ties go to
>   the larger clearance).
>
> **What it cannot show.**
> - Long sequences, drift, half turns or abuse (E1-3, E1-4, E1-6, E1-6t). These are not in the probe.
> - Slip events over D10's 60 s rest. The probe scores a 10 s rest only.
> - A rest result statistically distinct from L0's: 0 / 20 against 2 / 20 cannot be told apart (INFERENCE,
>   PART_G_FINAL U5, p ≈ 0.49).
> - Validity. Signal 4 is not met by construction, and the 20° limit is a proxy. Three things lie outside it:
>   - the 4 × 3 corner–edge pairs, for which only V3b's 7.5° applies;
>   - the anchors, which are off-axis at c = 1–3 mm, while P-60's acceptance covers on-axis paths at c = 0.2 mm only;
>   - the cross-interaction of the two groups.
> - Fit. W3's anchor geometry does not fit the real-mechanism CAD (side checks), and the hybrid's corner walls are
>   0.175 mm against 0.4 mm.
> - Independence. The arms were chosen after replays on an ER7 seed.
>
> **Rule for the next step (P-67 item 7).** If the hybrid stays in contention, the full 204-trial rehearsal runs on
> the eligible arm with the lowest median E1-2 turner torque. Its reading is amendment 2's: "meets or misses signals 1
> and 2; signal 3 not met". If the hybrid is not in contention, Part E is recorded as probe-only by amendment, and no
> full rehearsal runs. **Applied:** [full rehearsal / probe-only, amendment 3 — pending the user's decision U7].
>
> **Reading.** [pending; it states only which signals each arm met or missed]. No hybrid arm can be named a candidate
> for a scored pre-registration under the rules as they stand (amendment 2). Nothing here is scored or validated, and
> G1 is NOT PASSED.

Matching edits to the rest of SUMMARY.md (proposed, not made):
- Status, lines 5–6: "Part E is in progress" becomes "Part E [probe complete / recorded as probe-only]". The row
  wording follows P-67 item 6: "proposed once Part E's probe is reported".
- Outcome in brief, line 23: replace "probe interrupted and incomplete" with a one-line pointer to the section above.

---

## 3. Draft protocol amendment: "Part E recorded as probe-only"

Use this only if the user's decisions (P-67 item 1, decision U7) keep the hybrid out of contention. Append it to
`../PROTOCOL.md` after amendment 2, with the user's approval, before any Part E full-rehearsal trial.

> ### Part E amendment 3 (fixed [date — pending], after the probe, before any Part E full-rehearsal trial): Part E recorded as probe-only
> **Decision (user, [date and quoted wording — pending]; P-67 item 7, U7 in `proposals/PART_G_FINAL.md`).** The
> hybrid is not in contention. Part E ends with its 318-trial probe. The full 204-trial rehearsal in Part E's
> selection rule is not run.
>
> **Reason (independent of the probe's outcome).** The reason rests only on evidence that existed before the probe
> finished:
> - P-67 item 1 chose Part G (M5's 48 plus on-axis core pairs) as the direction, and W3 is not taken forward.
> - P-67 item 3 made real-mechanism fit a criterion for any new candidate.
> - Part E's anchors use W3's geometry, which does not fit the real-mechanism CAD (`side_checks/realfit/`).
> - Amendment 2 already rules out naming a hybrid arm a candidate under the rules as they stand.
>
> **Order of events, disclosed.** The user's decision was taken [before / after] the probe results were reported
> [pending]. If it was after, this is stated as such. The decision does not depend on any probe signal.
>
> **What stays as fixed.** The probe's trials, signals 1–4, the eligibility rule, the self-check and the records are
> all unchanged. The probe is reported in full, per arm, beside L0, C52 and W3 (SUMMARY.md, Part E), including:
> - which arm would have been selected: [pending], reported only;
> - its turner torque against L0.
>
> **What is not claimed.** There is no result on Part D's three signals for any hybrid arm. Sequences, drift, abuse
> trials and the 60 s rest slip count are unmeasured. Part E's addendum "Reading" (the hybrid replaces W3, or the
> choice goes to the user) does not apply, because no full rehearsal exists.
>
> **Records.** The probe records are under `results/hybrid/probe/`, committed at [commit — pending]. The folder
> `results/hybrid/full/` stays empty. If the user later reopens Part E, the full rehearsal runs under Part E's
> selection rule as fixed. That is reported as run after this amendment, and the arm it uses is the one named above.
>
> Nothing here is scored or validated; G1 is NOT PASSED; no mechanism is selected.

---

## 4. Inconsistent, stale or unsupported text found (reported, not fixed)

1. **`SUMMARY.md` l.5–6, stale.** It says the row "will be proposed when Part E is complete". P-67 item 6 says "once
   Part E's probe is reported", and item 7 allows probe-only.
2. **`SUMMARY.md` l.101–103, stale.** It says "the anchored layout is a candidate for a scored pre-registration". The
   side checks (no fit), the proxy correction (l.176–181) and P-67 item 1 (W3 not taken forward) supersede this, and
   no note points to them.
3. **`SUMMARY.md` l.152–153, overstated.** "The force law was validated for coaxial piece-to-core pairs up to 20° of
   tilt (P-60, ER5)" contradicts l.176–181 of the same file and side_checks l.27–28. Those limit 20° to ER5's on-axis
   face-turn paths at c = 0.2 mm, and give 7.5° for the generic case.
4. **`SUMMARY.md` l.107–108, overstated.** "the table used is the one validated to 20° of tilt" (Part E) conflicts with
   l.180–181 ("only V3b's 7.5° applies"). PROTOCOL.md l.245–246 and l.263 say the same; that file is frozen, so this is
   reported only.
5. **Missing limit.** Part E's anchors sit at c = 1–3 mm and off-axis. P-60 accepts c = 0.2 mm only (DECISION_LOG
   l.139: "other clearances or sizes … still fail"). SUMMARY.md l.176–181 qualifies only the corner–edge pairs.
6. **`PROTOCOL.md` l.197–198** says M5's magnets "suppress" the stall. SUMMARY.md l.21 was corrected to "attenuate"
   (`102fe11`); the protocol has no note.
7. **`PROTOCOL.md` l.7–8** says the delegated ER9 approval is recorded in the DECISION_LOG. No row records it; the only
   ER9 mention is P-67.
8. **`proposals/DECISIONS_2026-11-21.md` l.41, stale.** "record … as P-67": P-67 went to the decisions themselves, and
   P-69 and P-70 to Part G decisions, so the row is now P-71.
9. **`proposals/PART_G_FINAL.md` l.491** quotes Part E HB1–HB3 per-trial wall times ("547–675 s"). These come from
   uncommitted records of the probe that is still running. That conflicts with "partial records are not interpreted"
   (SUMMARY.md l.120; PART_G_FINAL l.123, l.628).
10. **`side_checks/README.md` l.25–26, unsupported.** "the 3 mm arm's axial stiffness is 27 % low" is a subagent claim
    marked "not rechecked".
11. **`SUMMARY.md` l.20, mislabelled.** "Result 2 (diagnostics, Part E)": these diagnostics are the Part C/D replays
    that motivated Part E, not Part E results.
12. **`DECISION_LOG.md` l.147–152:** P-68 contains line breaks and bullets inside a table row, which break the table's
    rendering. Separately, P-15 (l.153) sits after P-68.
