# Independent review: PHASE_1_M5_PREREGISTRATION.md (2026-11-16)

Reviewer: independent subagent (read-only; no simulations, no git writes).
Read: M5 draft; M4 pre-registration incl. Amendment 1; M1 pre-registration; `E4_scored_m4/run.py` (all);
`E4_scored_m4/analyze.py` (lines 1-75 + grep); `E1_scored/run.py` (trial lists, E1-7); `D8_alignment/rehearsal_gap.py`;
rehearsal 0.05 mm SUMMARY.md, CONDITION.md, report.txt (grep); diag SUMMARY (grep); DECISION_LOG P-23..P-32;
`src/rubiknetic/cube_physics/scored.py` (clean-commit, E1-6t penetration field).

## Verdict: ACCEPTABLE WITH CHANGES

The draft inherits M1/M4 thresholds faithfully, and its quoted numbers are accurate. Its disclosure of the post-hoc gap
choice is good. Five defects remain. Each one either leaves the verdict machinery or the seed map open to choice, or
overstates how independent the scored test is.

---

## Required changes

### R1. The seed map is undefined for E1-5s and E1-6t, and the draft's two descriptions conflict
- FACT (draft §2): "scored seeds 10000–10999. These are M1's experiment offsets shifted by +9000."
- FACT (draft §6.1): "It reuses M4's `run.py` logic unchanged, as `rehearsal_gap.py` does, with: ... seed shift +9000".
- FACT (`run.py:80,87,99`): `SEED_SHIFT = 5000` applies only to M1-derived lists; `SNAP_SEED_BASE = 6550` and
  `E16T_SEED_BASE = 6640` are hard-coded constants that are not derived from `SEED_SHIFT`.
- FACT (`rehearsal_gap.py` `jobs()`): `kw["seed"] = s + SHIFT` is added to M4's *scored* seeds (6000–6655).
  "+9000 as rehearsal_gap.py does" therefore gives 15000–15655, not 10000–10999.
- INFERENCE: the range assertion catches the 15000 reading. Inside 10000–10999, though, the E1-5s and E1-6t bases are
  left to the implementer. Changing only `SEED_SHIFT` leaves them at 6551–6568 and 6640–6655, which M4's scored run is
  using now, and the assertion would refuse them. The implementer then picks new bases after the draft is approved.
- **Change:** state the map explicitly: *every M5 seed = the corresponding M4 scored seed + 4000* (equivalently M1
  offset + 9000). That gives E1-1…E1-6 10000–10627, E1-5s 10551–10568, E1-6t 10640–10655, E1-7 10000, and E1-6n the
  same seeds. Add a unit test that asserts the M5 trial list equals M4's list with seeds +4000 and that it is disjoint
  from 7000–8999.

### R2. The verdict aggregator is unspecified, and M4's aggregator omits E1-6t
- FACT (draft §5): "every categorical and quantitative criterion holds in 100 % of scored trials of E1-1 to E1-6,
  including E1-5s and E1-6t."
- FACT (`E4_scored_m4/analyze.py:16-18`): `EXPECTED`/`ROWS` list E1-1, E1-2, E1-3, E1-4, E1-5, E1-5s, E1-6a, E1-6b
  and E1-6c, and **no E1-6t**. A grep for `6t|E16T|twist_std` in analyze.py finds nothing. The auto-generated
  "G1 ... verdict" line (l.73) therefore ignores E1-6t failures and E1-6t incompleteness.
- FACT: the E1-6m ⟨P⟩ criterion is enforced only in analyze.py (l.66-70), not in the per-trial `pass` from
  `apply_m4_criteria`. A verdict built from per-trial `pass` flags alone would drop E1-6m.
- FACT (draft §6): only `E5_scored_m5/run.py` is named. No analysis script is named or frozen.
- **Change:** §6 must name an M5 analyzer, for example `E5_scored_m5/analyze.py`. It must include E1-6t (16) in the
  expected counts and in the verdict, and keep the E1-6m ⟨P⟩ and completeness logic. It needs a test on fake records in
  which a failing E1-6t record turns the verdict to NOT PASSED. The analyzer must be in the clean-commit frozen paths
  together with `PHASE_1_M5_PREREGISTRATION.md` and `E5_scored_m5/run.py`.
- Side note for the main session, outside M5's scope: the same omission affects the M4 scored battery now running
  (P-32). Its auto-verdict will not reflect E1-6t.

### R3. The scored test is less independent than §0 implies: the move strings are the rehearsal's
- FACT (draft §0.1): "The scored seeds below have never been used, but the design choice itself is post hoc."
  FACT (draft §2): "The trial slots and move strings are M4's, with only the seeds shifted."
- FACT (`E1_scored/run.py:61-64`): scrambles are `random_scramble(20, s)` with s = M1 seeds 1400–1419. M4's `_shift`
  shifts the seed after the scramble is generated. The same 20 scrambles, and every other move string, were used in
  the 0.1 mm rehearsal (P-25), the 0.05 mm rehearsal (P-30; e.g. `scr20inv_s8416`) and the M4 scored run.
- INFERENCE: the gap was selected on exactly these move sequences. Only the setup draws (misalignment, grip, duration)
  are new. Under M1 §2, scrambles are drawn "from seed `s`" (the scored seed), so the reuse is a runner convention, not
  M1's wording.
- **Change:** add to §0 item 1, and to the G1 restatement in §5, that all move strings, including the E1-4 scrambles,
  are identical to those in the unscored rehearsals used to choose the gap, and that only the per-trial setup draws are
  new. (Fresh scrambles are listed as optional O1.)

### R4. The E1-7 piece-gap band rationale omits the project's own precedent, which would include the known failure
- FACT (draft §4): "This is M1's relative band ... applied to the new nominal ... The band was set by M1's rule, not to
  exclude it."
- FACT (M4 Amendment 1, A1, approved P-24): when the nominal moved to 0.1 mm, "the E1-7 gap factor becomes 0.05 /
  **0.1** / 0.2 mm", which is 0.5× / 1× / 2×, not 1.5×.
- INFERENCE: under the most recent approved re-centring rule, M5's band would be 0.025 / 0.05 / 0.1 mm and would
  contain 0.1 mm, which is known to fail drift (P-25). The draft picks the one available rule that excludes it and says
  so without mentioning the other rule. A sceptic would read it as band-shaping. E1-7 flips do not fail G1, but they
  decide whether "outcome unchanged inside the declared band" can be claimed.
- **Change:** disclose the A1 precedent. Also either adopt it (0.025 / 0.05 / 0.1) or keep 0.025 / 0.05 / 0.075 and
  add 0.1 mm as an extra reported E1-7 point (2 trials). The published sensitivity then contains the known fragility.

### R5. Stale statements, and no bar against changes informed by M4's scored data
- FACT (draft §2): "M4's unused scored range (6000–6999)". FACT (P-32; `E4_scored_m4/results/log.txt`, commit
  1dc578c): M4's scored battery on 6000–6655 is now running. FACT (draft §8 items 2 and 3) are still presented as open
  decisions, but P-32 already decided them.
- INFERENCE: if this review sends the draft back, M4's scored results at 0.2 mm will be available while the M5 text is
  being revised. That is a new opportunity for post-hoc adjustment.
- **Change:** correct §2 and §8 to reflect P-32. Add: "Revisions after this review are limited to the changes it
  requires. No M5 configuration, criterion or factor may be changed in light of M4's scored results."

---

## Optional changes
- O1. Draw E1-4 scrambles from the M5 seed (M1 §2's literal rule), so the sequences are also held out. This is a
  disclosed deviation from M4's runner.
- O2. `run.py:746` runs `startup_checks(MagnetParams())` with the default gap of 0.2 mm (l.527). The M5 runner should
  run it at 0.05 mm.
- O3. `run.py:602` builds the magnet layout from `ov.get("gap", M1Params().gap)`. The rehearsal set the gap in both
  `BASE_OVERRIDES` and `kw["overrides"]`. A runner that sets only `BASE_OVERRIDES` would build the magnets for a 0.2 mm
  pitch. The "gap override" unit test should assert the magnet system's `p.gap` = 5e-5.
- O4. Split §6 into the items that gate the scored run (1, 2, and 4 for E1-7 only) and the items that gate the G1
  sign-off (3, E1-8). This removes the ambiguity in "§6 work is committed" (compare the P-32 precedent for M4).
- O5. E1-7 magnet sizes: 4×1.5 N35 failed V3 (P-26). `v3_record_for` accepts any later passing
  `d8_1b_checks*.json`. State that a size that failed V3 is not retested under altered V3 settings, that its arm is
  reported as "not run: failed V3", and that E1-7 then counts as complete. State the same for 4×2 N52 if it fails.
- O6. State that E1-6n (no-magnet) failures never enter Option A. Rule 3 makes "the no-magnet arm ... the bound" for
  E1-6b/c. At 0.05 mm that bound may be uninformative, so the verdict should report the no-magnet E1-6b/c outcomes
  next to the rule-3-labelled magnet trials (8 of 8 E1-6c were labelled in the rehearsal).
- O7. Have the G1 verdict also restate the drift margin, the clip count and the rule-3 labels (§7). Require an empty
  `E5_scored_m5/results/` at start, because `_execute` skips existing files.
- O8. Record the patent source with its URL and access date in a references file. Reviewer check (FACT,
  https://patents.google.com/patent/US6217023B1/en, accessed 2026-11-16): "Spatial logic puzzle", a 2×2×2 puzzle. The
  quoted sentence is present verbatim.

## Checks that passed (FACT unless marked)
- Inheritance: M1 thresholds (2° / 1° / 0.5 mm / 0.5 mm / 0.3 mm / 0.5° / 0.5°, causality, Option A), M4 rules 1–3,
  growth slope < 0.005, E1-5s 0.5° from ≥ 3°, E1-6m, E1-6c categorical (A2), E1-6t 0.45 N·m, solved, ≤ 0.5 mm
  (`run.py:98,505`; the penetration window covers ramp, hold and settle, `scored.py`), and `RULE3 = {E1-6b, E1-6c,
  E1-6t}` (`run.py:90`). No threshold is loosened or dropped in the text. The defect is in the aggregator (R2).
- Seeds: a grep of .py/.md/.json/.txt/.toml for seeds ≥ 10000, `_s1xxxx` filenames and JSON `"seed": 1xxxx` found
  only the M5 draft and P-31. The range 10000–10999 is unused. M1-derived seeds +9000 reach 10627, so they fit.
- `run.py:211` wall bug: correctly identified. Wall = (face gap − 0.2 mm)/2 would give 0.075 / 0.325 / 0.575 mm
  instead of 0.15 / 0.4 / 0.65.
- Turner torque reported only: defensible and disclosed (§0.4). Not a gaming concern (INFERENCE).
- Numbers checked against the record: 16/204 failures (P-25); 21-trial study (P-27); 204/204 (P-30); median
  0.21 vs 0.10 N·m; 1 of 1,376 moves at the clip; drift max 0.74° (margin 0.26°); penetration 0.61 / 0.65 mm;
  "86° short" (diag SUMMARY l.96); face gap 0.85 mm; patent quote verified. No discrepancy found.
- Minor, outside the draft: CONDITION.md says it "was written before the run started", while SUMMARY.md says it was
  "committed ... while the run was in progress". These are consistent only if it was written before and committed
  later. Worth one clarifying line.
