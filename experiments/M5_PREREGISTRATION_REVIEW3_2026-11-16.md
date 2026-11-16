# Independent review 3: PHASE_1_M5_PREREGISTRATION.md revision 3 (2026-11-16)

Reviewer: independent subagent, read-only. I ran no simulations, ran no git command that writes, and modified no repository file. The only commands I ran were read-only: `git log`/`git diff 5e7bbbb HEAD`, and Python that reads stored rehearsal JSON and V3 JSON.

**`experiments/E4_scored_m4/results/` was NOT read, listed or grepped.** Seed searches were run on explicit paths that leave it out. No session transcripts were read.

Read:
- M5 pre-registration rev 3 (all);
- `git diff 5e7bbbb HEAD` for that file (rev 2 → rev 3);
- review 1 (required and optional sections) and review 2 (all);
- M4 pre-registration including Amendment 1 (all);
- M1 pre-registration §2 to §4;
- `E4_scored_m4/run.py` (all) and `E4_scored_m4/analyze.py` (all);
- `E1_scored/run.py` (all) and `D8_alignment/rehearsal_gap.py` (all);
- `d8_1b_stage1.py` `run_snap`;
- `scored.py` (`base_record`, `params_for`, trial functions);
- `m1_model.py` (gap, clip, geometry);
- `magnets.py` (`MagnetParams`, `layout`, `MagnetSystem`);
- the V3 blocks of all three `d8_1b_checks*.json`, and a listing of `D8_alignment/results/tables/`;
- rehearsal 0.05 mm `SUMMARY.md`, `report.txt`, `CONDITION.md`, plus a recount of its per-move turner torque;
- diagnostic SUMMARY §5 (gap study);
- `DECISION_LOG.md` P-21 to P-36;
- `R1_real_cube_bench/LITERATURE.md` "Piece clearance".

## Verdict: ACCEPTABLE WITH CHANGES

N1 is fixed correctly in the text, and its test can catch the regression. R1 to R5 still hold. Every number and line reference I checked matches its source. One required change remains, T1. It is procedural: the O7 empty-folder rule, together with the freeze rule, leaves no defined way to complete the scored run if it is interrupted. It also forces a single run, which the text never says. Any recovery would therefore be decided after partial scored results had been seen.

## Required changes

### T1. The empty-folder rule makes the scored run non-resumable, and nothing says how the run is invoked or what happens if it stops

**What the text and code say (FACT):**
- §2 (lines 125–126): the runner "refuses to start unless `experiments/E5_scored_m5/results/` is empty or absent".
- M4's runner can resume: `_execute` skips trials whose files already exist (`run.py:646–648`). Its CLI runs one experiment per call (`run.py:17–19`, `684–686`).
- The freeze rule (lines 22–27) allows amendments only "before any scored M5 trial". §5 (line 187) says "No rerun".
- §6.1 item 5 (lines 221–222) and §4 (line 157) say the N52 V3 check and the 0.35 mm pair check "gate E1-7 only".
- §5 (line 180) says "E1-7 and E1-8 must be completed and published" for G1.
- §5 (line 172) requires "a single source commit" across all records.

**Why it matters (INFERENCE):**
- After the first scored trial is written, the runner can never be started again. Concretely:
  - every experiment, including E1-6n and E1-7, must run in one `all` call. Running `run.py E1-1` and then `run.py E1-2` would refuse the second call;
  - both §6.1 item 5 checks must be finished and committed before that call. If they are not, the N52 and 0.35 mm arms are refused (`run.py:258–261`, `733–734`). They then cannot be run later, so E1-7, and with it G1 sign-off, can never be completed;
  - if the run stops (crash, WSL restart, out of memory), the 204-trial verdict is permanently INCOMPLETE, and no amendment is allowed.
- This is not hypothetical:
  - P-25 records a V3 run "stopped by memory pressure" (FACT).
  - The 0.05 mm rehearsal alone took 7,812 s for 204 trials (SUMMARY, FACT).
  - The M5 run is about twice that size: 204 + 184 E1-6n + about 54 E1-7 trials, counted from `run.py:101`, `105–111` and `E1_scored/run.py:25–35`.
  - §6.2 notes that the user has other workload on the machine.
- After an interruption, the author would have three choices, none of them registered:
  - accept a NOT PASSED for an infrastructure reason;
  - delete the results and restart, which is a rerun after seeing partial results;
  - bypass the check.

  That is a post-hoc choice.
- A secondary risk (FACT): `_write_new` (`run.py:639–642`) writes the JSON after opening the file. A crash during the write leaves a truncated file that a resumed run would skip and that the analyzer cannot parse.

**Change.** Pick one option and state it.
- **(a) Resumable.** The empty-folder check applies only at first start, which writes a manifest (commit, trial list, start time). A restart is allowed only:
  - from the same commit, checked against the manifest;
  - for trial IDs that have no record. That is completion, not a rerun: existing records are never touched.

  Records should be written atomically (temporary file, then rename). A record that cannot be parsed counts as an integrity violation (INVALID), not a missing trial.
- **(b) Not resumable.** State that the scored run is one `all` call, that §6.1 item 5 is finished and committed before it, and that an interruption gives INCOMPLETE, so G1 is not passed, with no recovery.

Either way, also:
- state that §6.1 item 5 must be complete and committed before the first scored trial;
- extend the empty-folder (or manifest) check to `results_nomag/` (`run.py:72`), which `_execute` also skips into.

## Optional changes

1. **"The magnet system's `p.gap`" does not exist** (FACT, `magnets.py:418–438`). `MagnetSystem` keeps neither `p` nor the gap. The gap appears only in `_MS_KEY` (`run.py:338`) and, implicitly, in the magnet positions `p_loc`. `describe()` (`magnets.py:502–504`) does not record it, so no trial record shows the magnet-layout gap.
   - The N1 and O3 tests (lines 199–200 and 214) should say what they compare. The strongest choice is `_MS.p_loc == layout(pitch, expected_gap, mp)` for every job of the full M5 list, with `params_for` and `use_magnets` intercepted and no stepping, as P5 requires.
   - Also record the layout gap in each record (for example `magnets.layout_gap`), and add it to the §5 integrity check. That covers the O3/N1 failure class after the run, not only before it.
2. **The integrity exemption "except the E1-7 gap arms" (line 174) is loose.** Only the two piece-gap arms differ. The face-gap arms keep 5e-5 (FACT, `run.py:597–602` with the specified override). Say instead that the two piece-gap arms must show 2.5e-5 and 1e-4, and every other record 5e-5.
3. **Add tests for the integrity checks** to §5 (lines 178–179). Each should give INVALID:
   - a record labelled "M4";
   - a record with `params.gap` 2e-4;
   - two source commits;
   - `scored` false;
   - a trial ID outside the list.

   Today only the E1-6t and E1-6m cases are tested.
4. **The G1 restatement (line 186) lists "the no-magnet E1-6b and E1-6c outcomes".** §4 (line 154) now adds E1-6t (O6). Add E1-6t at line 186 as well, for consistency.
5. **New V3 record files are not under the clean-commit check.** Line 210 covers M4's frozen paths, which name only `d8_1b_checks.json` (`run.py:76–78`). Add the new N52 and 0.35 mm V3 records, or the `d8_1b_checks*.json` glob. Partial mitigation already exists (FACT): `v3_source_sha256` is stored per record (`run.py:242`).
6. **The scope statements understate what changes.** Lines 35–40 ("changes are confined to …") and line 150 ("The only changes are …") leave out:
   - the start-up check gap;
   - V3 matching by grade;
   - the 0.35 mm V3 gate;
   - the mechanism label;
   - the empty-folder rule;
   - the integrity checks.

   None of these weakens anything, but the lists should be complete.
7. **Name the other runner constants that must change**, beyond what is stated:
   - `SCORED_SEED_RANGE` (`run.py:81`, asserted at `699`) becomes 10000–10999;
   - `OUT` and `OUT_NOMAG` point to `E5_scored_m5`;
   - "reuses M4's `run.py` logic unchanged" (line 192) means unchanged except for the listed items.

   The seed unit test would catch a missed range constant, so this is wording only.
8. **Strength scale vs grade.** The 0.67 strength-scale arm reuses the 4×2 N35 V3 record, because `table_path` and `v3_record_for` ignore scale (`run.py:217`, `238`). Scale and grade both change only the Br² strength, so either state why scale is exempt or require its own record. This affects E1-7 only.
9. **Disclose per-size validated tilts.** The 3×1.5 N35 arm uses its own validated tilt of 7.5° (FACT: `d8_1b_checks_3x1.5_N35_s1.json` V3 `validated_tilt_deg` = 7.5; `run.py:654`), not the 5° in §1 line 82. This affects E1-7 only.
10. **Record the start-up check's gap** in its result dict (`run.py:575–584` has no gap field), so that O2 can be audited from the records.
11. **Let `analyze.py` re-derive each E1-4 scramble** from the trial's seed (`random_scramble(20, s)` + inverse) and compare it with the stored `sequence` (`scored.py:246`). That makes O1 auditable after the run.
12. **Say that E1-7 counts as complete** when the N52 or 0.35 mm arm is "not run" (line 157). The text says so explicitly only for 4×1.5 N35.

## Checks that passed

**N1 is fixed (FACT unless marked).**
- §6.1 item 1 (lines 196–200) gives the E1-7 piece-gap factor precedence for both the cubies and the magnets, and forbids copying `rehearsal_gap.py:42` (verified: an unconditional `kw.setdefault("overrides", {})["gap"] = gap`).
- With a non-overwriting per-trial default, the factor reaches both paths:
  - the magnets through `ov.get("gap", …)` (`run.py:597–602`);
  - the cubies through `run_sequence_trial(**ov)` → `params_for` with `{**BASE_OVERRIDES, **kw}`, where `kw` takes precedence (`run.py:310`, `610`; `scored.py:233–243`).
- Every E1-7 trial is of kind `seq` (`run.py:156–157`), so no E1-7 trial bypasses this.
- Trials of other kinds take the cubie gap from `BASE_OVERRIDES`: `scored.py:319`, `360`, `404`, `428`, `467` and `d8_1b_stage1.py:142` all call `params_for`.
- The test (lines 199–200) covers both values in both arms and 5e-5 everywhere else, E1-7 included. It would fail under the rehearsal-style overwrite (INFERENCE; see optional item 1 on what it compares).
- The nominal values (line 156) are piece gap 0.05 mm and face gap 0.85 mm. Without this, `e17_trials` would emit a duplicate "gap=5e-05" arm while M1's `("gap", 0.0002)` stayed in NOMINAL (`run.py:110–111`, `149`; `E1_scored/run.py:101–103`).
- The face-gap walls (0.35 − 0.05)/2 = 0.15 mm, 0.4 mm and 0.65 mm are correct (`magnets.py:70`, `105`, `112`). The `run.py:211` fix is specified and tested (line 215).
- 0.5 × 5e-5 and 2 × 5e-5 are exact in binary floating point, so the asserted values are reachable (INFERENCE).

**R1 holds (FACT).**
- The table (lines 102–113) is M4's list + 4000. I recomputed it from `E1_scored/run.py:41–83`, `run.py:87`, `99` and `157`:
  - E1-1 to E1-6 are M1 offsets + 9000;
  - E1-5s is 10550 + 10·rep + |δ|, which gives 10551–10568;
  - E1-6t is 10640–10655;
  - E1-7 is 10000.
- A search of `src/`, `tests/`, every `experiments/*/` folder except `E4_scored_m4/`, and `E4_scored_m4/{run.py, analyze.py, bench.py, smoke}` found no use of seeds of 10000 or more.
- The range is disjoint from 1000–9999. The unit test is specified (lines 123–124).

**R2 holds (FACT).**
- Expected counts are given, 20+24+22+40+42+20+6+6+8+16 = 204, with INCOMPLETE on any mismatch.
- E1-6t is judged through `pass` (`run.py:503–508`, `516–517`); E1-6m through `e16m_P_ok` with completeness (as in `analyze.py:66–70`).
- The integrity checks are listed, `analyze.py` is in the frozen paths (line 210), and three failure tests are specified. `analyze.py:16–18` does omit E1-6t.

**R3 holds (FACT).**
- §0 item 2 now separates the fixed strings from the seed-generated scrambles.
- The scrambles come from M5 seeds 10400–10419 (§3), following M1 §2 (`PHASE_1_PREREGISTRATION.md:52`, verified).
- The G1 restatement keeps the disclosure (lines 182–183).

**R4 holds (FACT).**
- The 0.025 / 0.05 / 0.1 mm band is disclosed, and the known 0.1 mm failure is disclosed (P-25: 188/204).
- A1 is shown as never adopted (P-25), and the declined ±50 % alternative is named.

**R5 and the freeze rule hold (FACT).**
- The freeze rule appears at lines 22–27.
- Every rev-3 change traces to a review-2 item (`git diff 5e7bbbb HEAD`); none touches a threshold.
- The provenance statement (lines 7–11) discloses that the author saw M4's early E1-4 failures. Its claim about timing relative to M4's results cannot be checked without reading the excluded folder (not checked).

**Adopted optional items.**
- **V3 by grade:** correctly motivated. `run.py:238` matches diameter and length only. An N52 table exists (`tilt_4x2_1.455T_…npz`) but has no V3 record, so M4's lookup would have used the N35 record.
- **0.35 mm pair check:** correctly motivated. V3 pair gaps are 0.5, 0.75, 1.0, 1.25 and 1.5 mm (`d8_1b_checks.json`).
- **4×1.5 N35:** V3 failed (record `pass: false`; P-26: 5.65 % > 5 %).
- **Clip definition:** at ≥ 0.999 N·m, a recount of the rehearsal gives exactly 1 of 1,376 moves (`scr20inv_s8416` U2, 1.000). The next highest is 0.985.
- **Mechanism label:** `run.py:658` does write "M4".
- **P5:** no simulation on M5 seeds before the scored run.
- **Provenance statement:** present at lines 7–11.
- **§6.1/§6.2 split:** coherent apart from the item 5 sequencing in T1.
- **Patent:** recorded in `LITERATURE.md:37–47`.

**No weakening (FACT).**
- Every M1 and M4 threshold, Option A, rules 1–3, the growth slope, E1-5s, E1-6t (0.45 N·m, solved after release, ≤ 0.5 mm) and E1-6m are kept.
- Rule-3 labels cannot change the verdict, because the verdict comes from the stored `pass` flags.
- E1-6n is excluded from Option A.

**Numbers and references, all matching (FACT).**
- Numbers checked against their sources:
  - 16/204 (P-25); 21 trials (P-27); 204/204 (P-30, `report.txt`);
  - median turner torque 0.214 vs 0.104 N·m;
  - drift maximum 0.742°, a margin of 0.26°;
  - abuse penetration 0.61 mm (E1-6b) and 0.65 mm (E1-6c);
  - "86° short" and "forgiveness blocked" (diagnostic SUMMARY lines 96 and 110);
  - face gap 0.85 mm; clip 1 N·m (`m1_model.py:82`, `188`); box size = pitch − gap (`m1_model.py:131`);
  - validated tilt 5° (`d8_1b_checks.json`).
- Line references checked:
  - `run.py:87`, `99`, `211`, `232–243`, `505`, `527`, `602`, `658`, `746`;
  - `analyze.py:16–18`;
  - `rehearsal_gap.py:42`;
  - `PHASE_1_PREREGISTRATION.md:52`.
