# Decisions for the user after the 2026-11-21 subagent waves

**Status:** PROPOSAL. Nothing here is decided or run. These are the decisions that block the next step toward G1,
with the evidence for each and a recommended default. The decisions are listed in the order they block work.

## What is now known (each item links to its committed file)
- **W3 does not fit a real cube, and its turner torque is unrealistic.**
  - It does not fit the real-mechanism CAD: corner anchors lie mostly in air (`../side_checks/README.md`).
  - Its turns reach 1 N·m, about 11× the only verified real-cube figure, 0.09 N·m
    (`../../../docs/research/TURNING_TORQUE_FINDINGS.md`).
  - Its "validity" signal was a 20° proxy: P-60 does not cover its off-axis paths (`../SUMMARY.md`, Limits).
- **Commercial cubes use on-axis corner–core pairs added to the usual piece-to-piece magnets**
  (`../../../docs/research/CORE_MAGNET_PRACTICE_FINDINGS.md`). No source shows off-axis core magnets.
- **The commercial pattern fits our model's real-mechanism geometry.** "M5's 48 plus on-axis core pairs" uses the only
  placement inside P-60, and both magnet groups fit the CAD. It failed ER3's static screen in the earlier,
  unbuildable placement; M5's layout alone fails that screen too and still passes most dynamic trials.
- **Nothing is scored or validated, and G1 is still NOT PASSED.** `G1_GAP_ANALYSIS.md` lists what a scored run lacks:
  about 70–110 CPU-hours of work plus the decisions below.

## Decisions
1. **Which direction goes forward.** Recommended: **Part G**, the commercial pattern (M5's 48 plus 8 or 20 on-axis
   core pairs), starting with its static pre-checks, which take minutes. Alternatives:
   - Part F, re-screening anchored layouts that fit; the review says rework it, and its outcome is largely
     predetermined;
   - continuing W3 with fit disclosed as an abstraction.
   The review recommends Part G first.
2. **Part G's magnet type (review G4).** Recommended: **(b)**, M5's real 4 × 2 mm magnets for the 48 plus
   4 × 3 mm core magnets. It needs a composite magnet system in the force-law code, plus a review. In return it
   reproduces L0 exactly, uses catalogue magnets, removes the stand-in and the 0.756 strength-meaning question, and
   keeps every core magnet out of near-field range of the M5 magnets. Alternative: (a), all 4 × 3 at scale 0.756,
   which needs no new code but probably fails HC20 on geometry (review G3).
3. **Is real-mechanism fit required for G1?** Recommended: yes, as a criterion for any new candidate, using the
   measured CAD numbers. Alternative: disclose fit as an abstraction (P-58 style).
4. **Turner-torque policy.** Recommended: keep reporting it, add a stated realism reference (about 0.2 N·m, warning
   at about 0.45–0.5 N·m), and make no change to the frozen rig. Alternatives:
   - a criterion, which would be chosen after seeing data and must be disclosed;
   - an unscored clip-raised diagnostic to measure true torque demand.
5. **ER10 (stall diagnostic).** Recommended: approve with the review's blocking fixes T1–T3 (a jam rule, a clip-raised
   or uncensored measure, rehearsal seeds for the sequences), run one process on an idle machine, and rename it
   (review T9). It stays off the G1 critical path.
6. **The ER9 decision-log row.** Recommended: record ER9 Parts A–D, the side checks and the corrections as P-67 once
   Part E's probe is reported.
7. **Part E.** Recommended: finish the probe (43 trials left) when memory allows. Run the full rehearsal of its
   eligible arm only if decision 1 keeps the hybrid in contention; otherwise record Part E as probe-only, by
   amendment.
8. **A force-law validation (V3-turn) for whichever placement goes forward,** before its dynamics are read as more
   than a proxy. For Part G at c = 0.2 mm, ER5's check already covers the 20-pair core (review: optionally re-check
   the 8-pair subset).

## Review findings already applied to the drafts' status
- Part F is marked for rework (F1–F3: P-60 scope overstated, 20° proxy, blend-region error).
- Part G and ER10 need the listed changes before approval (`REVIEW_F_G_ER10_2026-11-21.md`).
