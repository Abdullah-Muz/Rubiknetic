# Independent review 2: PHASE_1_M5_PREREGISTRATION.md, revision 2 (2026-11-16)

Reviewer: independent subagent. Read-only: no simulations, no git writes, no repository files modified.
`experiments/E4_scored_m4/results/` was NOT read.

Read: M5 draft rev 2 (all); review 1 (all); M4 pre-registration incl. Amendment 1 (all); M1 pre-registration §2–§8;
`E4_scored_m4/run.py` (all); `E4_scored_m4/analyze.py` (all); `E1_scored/run.py` (all); `D8_alignment/rehearsal_gap.py`
(all); rehearsal 0.05 mm SUMMARY.md; DECISION_LOG P-23..P-34; `cube_logic/scramble.py`; `scored.py` `draw_setup`;
`m1_model.py` defaults; V3 fields of `d8_1b_checks*.json`.

## Verdict: ACCEPTABLE WITH CHANGES (one required change)

R1, R2, R3 and R5 are fixed correctly. R4 is fixed in the text, but §6.1 item 1 contradicts §4 in a way that, followed
literally, deletes the E1-7 piece-gap factor that R4 added (required change N1). Every quoted number and every code
reference I checked is correct.

---

## Required change

### N1. §6.1 item 1 overwrites the E1-7 piece-gap factor that §4 registers
- FACT (draft §6.1 item 1): "gap 0.05 mm set in **both** `BASE_OVERRIDES` and every trial's `kw["overrides"]` ... as
  `rehearsal_gap.py` does".
- FACT (`rehearsal_gap.py` `jobs()`): `kw.setdefault("overrides", {})["gap"] = gap` — an unconditional overwrite. The
  rehearsal never ran E1-7, so this never mattered there.
- FACT (`run.py:157`): E1-7 trials carry the factor in `kw["overrides"]`, e.g. `{"gap": ...}` for the piece-gap arm;
  `run.py:602` builds the magnets from `ov.get("gap", ...)`; `run.py:310` gives `kw` precedence over `BASE_OVERRIDES`.
- INFERENCE: implemented as written, the 0.025 mm and 0.1 mm E1-7 arms run at 0.05 mm, and the tags still read
  "gap=...". The 0.1 mm point that R4 required, and that is known to fail drift, silently becomes a nominal rerun, so
  "outcome unchanged inside the band" could be claimed. The §6.1 unit test ("the magnet system's `p.gap` = 5e-5")
  would pass under this bug and could be written to enforce it. Under "no rerun", the error could not be repaired
  after scoring.
- **Change:** state that the 0.05 mm per-trial override applies to every trial **except the E1-7 piece-gap arms,
  where the factor value takes precedence** for both the cubies and the magnet layout. Add a unit test asserting that
  the cubie `p.gap` and the magnet `p.gap` are 2.5e-5 and 1e-4 in those arms and 5e-5 in every other trial. Also
  state that the E1-7 `NOMINAL` set uses gap 0.05 mm and face gap 0.85 mm, so the nominal is not duplicated under
  another tag.

---

## R1–R5 checks

**R1 seeds — FIXED (FACT).** I recomputed the M4 lists from `E1_scored/run.py` `trials()` (+5000), `run.py:87`
(6550 + 10·rep + |δ|, δ ∈ {1,2,3,5,8}) and `run.py:99` (6640 + 2i + j):
E1-1 6000–6019 (20), E1-2 6100–6123 (24), E1-3 6200–6239 (22), E1-4 6300–6419 (40), E1-5 6500–6541 (42),
E1-6 6600–6627 (20), E1-5s 6551–6568 (20 trials, 10 seeds), E1-6t 6640–6655 (16), E1-7 6000. The total is 204. +4000
reproduces every row of the §2 table. A grep for `_s1NNNN`, `"seed": 1NNNN` and `random_scramble(20, 1NNNN)`
(excluding the M4 results) found no earlier use. Optional: the E1-3, E1-4 and E1-6 rows are envelopes, not contiguous
lists (for example, E1-3 is 22 seeds inside 10200–10239).

**R2 verdict script — FIXED (FACT).**
- `analyze.py:16–18` does omit E1-6t.
- `run.py:505` does set `ok_e16t`, and `run.py:516–517` folds it into `pass`.
- E1-6m is judged only in `analyze.py:66–70`.
- The spec covers counts (sum 204, verified), the INCOMPLETE state, E1-6t through `pass`, E1-6m through `e16m_P_ok`
  with completeness, and three failure tests.
- The script is frozen.

**R3 independence — FIXED (FACT).** The rehearsals used `R.trials()` → `_shift(E1.trials())`, so every move string,
including the scrambles from seeds 1400–1419, matches M4's, and only the setup draws were new. §0 item 2 says this. One
optional wording point: "Every E1-2, E1-3 and E1-5 sequence ... were generated from M1's seeds 1400–1419" reads as if
all of these strings were seed-generated. Only the scrambles are; the rest are fixed strings.

**R4 E1-7 band — FIXED in §4, undermined by §6.1 (see N1).** The derivation is correct (FACT): 0.5×/1×/2× of 0.05 gives
0.025/0.05/0.1 mm. The face gap is 0.05 + 2·wall, so walls 0.15/0.4/0.65 give 0.35/0.85/1.35 mm. The `run.py:211` fix
is specified and tested. The known 0.1 mm failure is disclosed. Choosing the rule that includes a known failure is the
conservative direction (INFERENCE).

**R5 stale text — FIXED (FACT).** 6000–6999 is now "in progress", §8 lists only open items, and the freeze rule appears
under Status.

## O1–O8
- **O1 (FACT, INFERENCE):** this is M1 §2's literal rule (`PHASE_1_PREREGISTRATION.md:52`, verified).
  - The seeds are fixed by +4000, so no one can pick scrambles.
  - The cost is that M4-vs-M5 E1-4 trials are no longer move-for-move paired. G1 is an absolute per-mechanism test, so
    this does not affect the verdict; it is disclosed.
  - `random_scramble` and `draw_setup` both use `default_rng(s)`, so the scramble and setup draws share a stream. This
    was already true of M1's own scored E1-4 and is harmless.
  - I found no gaming route.
- **O2, O3, O7 adopted.** O3's test is correct except as noted in N1.
- **O4:** §6.1/§6.2 split adopted.
- **O5 adopted, with one caveat (FACT):** `v3_record_for` (`run.py:232–243`) matches only by diameter and length. 4×2
  N52 would therefore inherit the passing 4×2 **N35** V3 record (`d8_1b_checks.json`), so a failed N52 V3 check (§6.1
  item 5) would not stop the runner. Optional: match on grade too, or state that the N52 arm is gated by its own
  recorded check.
- **O6 adopted for E1-6b/c only.** `RULE3` (`run.py:90`) also contains **E1-6t**, which is a G1 criterion. Optional: give
  any rule-3-labelled E1-6t trial the same side-by-side no-magnet report.
- **O8 partly adopted (FACT):** the URL and access date are in §0 item 3, but no references file contains the patent
  (grep). "Adopts all of the optional changes" slightly overstates this.

## Other optional changes
- **P1.** E1-7 face gap 0.35 mm lies below V3's tested pair gaps of 0.5–1.5 mm (`d8_1b_checks.json` V3 `pair.gap_mm`).
  M4's 0.5/1.0/1.5 band matched that range; the re-centred band leaves it. Disclose this, or add a V3 pair check at
  0.35 mm to §6.1 item 5.
- **P2.** §4 says A1's rule "for M4 gave 0.05/0.1/0.2 mm". A1 was conditional and **not adopted** (P-25), so M4's
  registered band remains M1's 0.1/0.2/0.3. Say so, and note the ±50 % alternative (0.025/0.05/0.075) that was declined.
- **P3.** Define "at the 1 N·m clip", for example as per-move `max_turner_torque_Nm` ≥ 0.999.
- **P4.** In the verdict script, also check:
  - that trial IDs equal the registered list;
  - a single `source_commit`;
  - `scored` = True;
  - `params.gap` = 5e-5;
  - `mechanism` = "M5" (`run.py:658` hard-codes "M4").
- **P5.** Forbid any simulation on M5 seeds 10000–10999 before the scored run, not only in the results folder.
- **P6.** Add to rev 2 a sentence stating that its changes are exactly review 1's items plus the user's band choice,
  and were not informed by M4's scored results. The freeze rule is otherwise enforceable only by self-certification;
  the §9 mapping makes it auditable.
- **P7.** Disclose that the E1-7 "magnet: none" arm is expected to jam (P-27), as E1-6n's is.

## Post-hoc risk
- The E1-7 band is correctly derived and disclosed (N1 aside).
- Reporting turner torque only is justified (FACT: M1 and M4 have no torque criterion). Clip effects that matter still
  surface as turn error, drift or oracle failures.
- The freeze rule is adequate once P6 is added.

## Factual accuracy (FACT, all match)
- Line references checked: `run.py:87, 99, 211, 505, 527, 602, 746` and `analyze.py:16–18`.
- Numbers checked: 16/204; 21 trials; 204/204; median turner torque 0.21 vs 0.10 N·m (≈2×); 1/1,376 moves at the
  clip; drift max 0.74° (margin 0.26°); penetration 0.61/0.65 mm; face gap 0.85 mm; clip 1.0 N·m (`m1_model.py:82`);
  the seed table.
