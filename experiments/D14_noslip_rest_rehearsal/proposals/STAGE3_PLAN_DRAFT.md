# DRAFT — not approved

# Stage 3 plan: from the D14 rehearsals to a scored G1 run at `noslip_iterations` 10

**Status:** PROPOSAL, 2026-11-23, written by the main session after D14 Stage 2 (`SUMMARY_STAGE2.md`, `1669da2`). Under
P-73, Stage 3 needs the user's go. Nothing here is decided, and nothing has been run.

Labels: `FACT` (file named), `INFERENCE`, `PROPOSAL`. CPU-h are summed trial wall times. Wall-clock assumes 4 workers.

## Where things stand (`FACT`)
- At `noslip_iterations` 10, on ER7's rehearsal seeds, L0, PG8 and PG20 each meet Part G's four probe signals
  (D14 Stage 1 and Stage 2).
- The full Option A list (204 trials) has six more sub-experiments, which have **not** run at this setting:
  - E1-3: 22 trials;
  - E1-4: 40 trials;
  - E1-6a, E1-6b, E1-6c and E1-6t: 6, 6, 8 and 16 trials.

  That is 98 trials per arm.
- G1 (`docs/VALIDATION_PLAN.md`) also asks for solver-tolerance sensitivity and a CPU benchmark. In M5's battery these
  are E1-7 and E1-8.
- A G1 pre-registration skeleton exists: `experiments/ER9_anchored_core_layouts/proposals/G1_SCORED_PREREG_DRAFT.md`,
  with Q1–Q12 and a prerequisite table. It was written for the frozen setting and an unnamed Part G arm.

## Steps (`PROPOSAL`)
| Step | What | Seeds | Cost (INFERENCE) | Gate to the next step |
|---|---|---|---|---|
| **3a** | **Model re-checks at NoSlip 10** (detail below) | none / one smoke seed | < 1 h | All pass, otherwise stop and report |
| **3b** | **Full rehearsal remainder at NoSlip 10**: E1-3, E1-4 and E1-6a/b/c/t (98 trials per arm), same harness as Stage 2 (frozen gate first, pause on the first abort), signals = ER7/M5 Option A rule plus G.4 validity | ER7 rehearsal list (16000–16655) | from ER7 L0's frozen wall times (E1-3 2,047 s; E1-4 23,930 s; E1-6 2,514 s; total 7.9 CPU-h) × Part G's arm ratios (about 2.0 for PG8, 2.4 for PG20) × NoSlip 1.0–1.26: **L0 8–10, PG8 16–20, PG20 19–24 CPU-h; all three about 11–14 h wall** | The user picks the G1 arm from the complete 204-trial picture |
| **3c** | **Fresh-seed unscored rehearsal** of the chosen arm (G1 draft Q3; the ER7 seeds were used for every choice so far): the full 204-trial battery plus 60 s rests | 19000–19655 (+ 19700–19739) | G1 draft §8 row 9 (frozen): PG8 15–23, PG20 25–45 CPU-h. L0 is lower (INFERENCE: about 10–15) | It must pass as the scored run would. Otherwise the user decides |
| **3d** | **G1 pre-registration**, updated (detail below) | text only | about a day of drafting and reviews | The user approves the text |
| **3e** | **Scored G1 run** | 17000–17999 (never used) | G1 draft: PG8 30–45, PG20 40–65 CPU-h. L0 is lower | The verdict, as written |

**Step 3a in detail:**
1. Rerun the composite checks V4 (momentum), V5 (energy) and V6 (pose-only) with NoSlip in the model.
   - INFERENCE: these test the magnet force law, not friction, so they should not change. They are rerun for the record.
   - For L0, the D8 V3–V6 records already exist at the frozen setting; V5 and V6 likewise.
2. A NoSlip determinism check: the same trial run twice gives identical results.
3. A solver check: the same trial at `noslip_iterations` 10 and 20 compared, reported only. This shows whether 10
   iterations is converged.

**Step 3d in detail.** Update `G1_SCORED_PREREG_DRAFT.md`:
- the arm, and the setting (`noslip_iterations` 10), with its post-hoc timing disclosed and P-72–P-74 cited;
- D14 results as background;
- answers to Q1–Q12, with Q4 (slip rule) and Q10 (fit) the substantive ones;
- E1-7 sensitivity extended with a NoSlip iteration factor, for example 10 and 20.

Then: runner, tests and a smoke run on 18000–18099; reviews until no changes are required; the user's explicit go.

## Decisions needed now (`PROPOSAL`, with recommendations)
1. **Arms for 3b.** Recommended: **all three** (about 11–14 h wall). Each has a different weak point that only the full
   list can test:
   - L0: snap-back margin 0.29° of 0.5°;
   - PG20: largest turn 0.97 N·m, near the 1 N·m clip;
   - PG8: median torque 0.42 N·m, near the warning level.

   The cheaper choice is PG8 alone, about 4–5 h.
2. **Fresh-seed rehearsal (3c).** Recommended: **yes**. Every choice so far, including the setting, used ER7's seeds.
3. **Order.** Recommended: 3a now (minutes), then 3b on an idle machine. The other training job on the machine
   reduces the safe worker count.

## Risks (`INFERENCE`)
- E1-4 (long move sequences) is the largest block. Its drift and stall behaviour at NoSlip are untested. Drift
  accumulated over many moves is where harder friction or extra coasting would show.
- E1-6 (abuse trials) may push magnets outside their validated range, as at the frozen setting (L0's 12.59° in ER7).
  G.4 labels these trials but does not fail them.
- If 3b or 3c fails for an arm, that arm stops at this setting. A new setting would be another post-hoc choice and
  would need a new decision.
