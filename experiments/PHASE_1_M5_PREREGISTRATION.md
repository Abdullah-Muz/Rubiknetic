# Phase 1 (G1) Pre-registration: M5, magnetic contact cube at a 0.05 mm piece gap

**Status: revision 4, `DRAFT PROPOSAL`, awaiting a fourth independent review and the user's approval.**
- **Revision 3** (P-35) was approved on condition that a third independent review require no changes (P-36). That
  review required one change, T1 ([`M5_PREREGISTRATION_REVIEW3_2026-11-16.md`](M5_PREREGISTRATION_REVIEW3_2026-11-16.md);
  P-38), so revision 3 was never in force. Revision 4 (P-39) makes T1 with option (a), a resumable run, and adopts all
  twelve optional changes from review 3, as the user approved ("all approved"); see §9.
- **Revision 2** (P-34) was reviewed, and the review required one change, N1
  ([`M5_PREREGISTRATION_REVIEW2_2026-11-16.md`](M5_PREREGISTRATION_REVIEW2_2026-11-16.md)). Revision 3 (P-35) makes N1
  and adopts every optional change from that review.
- **Provenance (P6).**
  - Revision 2 was committed (`5e7bbbb`) before any M4 scored result had been viewed.
  - Before writing revision 3, the author had seen that M4's first scored E1-4 trials failed M1's criteria, which was
    expected.
  - Every revision-3 change comes from review 2's text; none concerns or depends on M4's results.
  - **Revision 4 was written after M4's scored battery finished** (G1 NOT PASSED, 123 / 204; P-37), and the author
    has seen its results. Every revision-4 change comes from review 3's text, which was written without reading M4's
    results. The changes concern run procedure, record integrity, tests and wording. **No configuration, criterion,
    threshold, factor or seed is changed**, and none of the changes was informed by M4's results.
- **Revision 1** (2026-11-15, P-31) was approved on condition that an independent review require no changes (P-32).
  The review required five changes, so revision 1 was never in force (P-33). Review:
  [`M5_PREREGISTRATION_REVIEW1_2026-11-16.md`](M5_PREREGISTRATION_REVIEW1_2026-11-16.md).
- **Revision 2** (2026-11-16, P-34) makes every required change, R1–R5, adopts all of the optional changes O1–O8, and
  uses the E1-7 band the user chose (Amendment A1's rule). The changes are listed in §9.
- **No scored M5 trial exists.** Scored runs may start only after:
  - this text is approved;
  - the items in §6.1 that gate the scored run are committed;
  - the runner checks for a clean commit.
- Thresholds may never be loosened after a failure.
- **Freeze rule (R5).** From now on this text may change only:
  - to make changes that an independent review of this text requires; or
  - by a dated amendment that the user approves before any scored M5 trial.

  **No change may be made in light of M4's scored results** (P-32; that run finished on 2026-11-16, P-37). Any
  amendment must state that it was not informed by them.

**Name.** "M5" is the next free mechanism label. It is not the "M5" measurement in
`R1_real_cube_bench/PROTOCOL.md`, which is a corner-twist bench test.

**Basis:**
- The approved M4 pre-registration ([`PHASE_1_M4_PREREGISTRATION.md`](PHASE_1_M4_PREREGISTRATION.md)) including
  Amendment 1 item A2, and through it the M1 pre-registration. **M5 is M4 with one design change: the piece gap.**
- Every rule, criterion and threshold is M4's unless this file says otherwise. This file's changes are confined to:
  - the piece gap (§1) and the magnet layout built for it;
  - the start-up check run at the 0.05 mm gap (§2);
  - the seeds (§2);
  - the run procedure: first start, resume, manifest, ledger and atomic records (§2, T1);
  - the E1-4 scramble draw (§3);
  - the reported-only additions (§4);
  - the E1-7 band, and V3 records matched by size, grade and strength scale, including the 0.35 mm face-gap pair
    check (§4);
  - the `mechanism` label "M5" and the record-integrity checks (§5);
  - the verdict script (§5).

  None of these loosens an M1 or M4 criterion.
- **The play-criteria proposal is not used.** That proposal's revision 3 is not in force (P-28). M5 is judged on M1's and M4's
  per-piece criteria exactly as registered.

## 0. Disclosure (read first)
1. **The gap was chosen after seeing unscored data** (`FACT`):
   - at the registered 0.2 mm, an unscored probe showed drift over 1° (P-24);
   - a 0.1 mm rehearsal failed 16 / 204 trials (P-25);
   - the diagnostic attributed the drift to B1's per-piece play (P-26);
   - a 21-trial study at 0.05 mm passed (P-27);
   - a full 204-trial rehearsal at 0.05 mm passed every M1 and M4 criterion (P-30).
2. **How independent the scored test is (R3).**
   - The rehearsals reused the scored trial slots and **the same move strings** as M4's scored list.
     - The E1-2, E1-3 and E1-5 sequences and the E1-4 `R U R' U'` × 6 trials are fixed by M1's registration.
     - The 20 E1-4 scramble+inverse sequences were generated from M1's seeds 1400–1419.
     - Only the random setup draws were new in each rehearsal.
   - **For M5, the 20 E1-4 scrambles are drawn from the M5 seed (§3, O1).** Those 20 sequences are therefore held out.
   - The other move strings are fixed by M1's registration (single face turns, half turns, `R U R' U'` × 6,
     forgiveness and snap offsets). They stay identical to what the rehearsals saw, and only their setup draws are new.
3. **Whether a 0.05 mm clearance is realistic is an `ASSUMPTION`.**
   - The only numeric source found is US 6,217,023 B1, "Spatial logic puzzle" (Kremer, Seven Towns), a 2×2×2 puzzle.
     It states: "the clearance between pieces being of the order of 0.05 mm and being a matter for trial and error by
     the puzzle designer" (https://patents.google.com/patent/US6217023B1/en; accessed 2026-11-15 and 2026-11-16).
   - No measurement of a real 3×3 was found.
   - Generic ABS moulding tolerances place 0.05 mm at the tight end of what is achievable. That figure comes from a
     manufacturer's guide the main session has not checked.
   - R1 bench data would settle it, after G1, as for E1-6t.
4. **Without magnets, 0.05 mm jams** (P-27: turner torque at its 1 N·m clip, a layer 86° short, forgiveness blocked).
   M5's turning depends on the magnets keeping the layers square (`INFERENCE`).
5. **Turner torque headroom is smaller** (`FACT`, rehearsal):
   - median turning torque 0.21 N·m, about 2× the 0.1 mm run;
   - 1 of 1,376 moves touched the 1 N·m clip, and that move still turned correctly.

   It is reported (§4), not a criterion: M1 and M4 have none, and adding one after seeing this value would be a
   post-hoc choice in either direction.
6. **Drift margin.** M1's 1° criterion is kept. The rehearsal maximum was 0.74°, a margin of 0.26°.

## 1. Frozen configuration (proposed)
| Group | Value |
|---|---|
| Cubies, rig, solver | M4 §1 unchanged: M1 as frozen, with `radial_preload = 0` (B1, rigid radius), **except piece gap 0.2 → 0.05 mm** (`M1Params.gap = 0.00005`; box size = pitch − gap) |
| Magnets | M4 §1 unchanged: 48 axial discs, 4 × 2 mm N35, 0.4 mm wall, classic layout. Because the wall is unchanged, **the face gap is 0.85 mm** (M4: 1.0 mm). The magnet layout is built for the 0.05 mm gap (§6.1 item 1, O3) |
| Force law, validated range | M4 §1 unchanged: `src/rubiknetic/cube_physics/magnets.py`; validated near-pair tilt 5° for the nominal 4 × 2 mm N35 magnets (the V3 extension to 7.5° failed, Amendment 1). **Each other magnet configuration uses the validated tilt in its own V3 record** (`run.py:654`); in E1-7 the 3 × 1.5 mm N35 arm uses 7.5° (`d8_1b_checks_3x1.5_N35_s1.json`). This affects E1-7 only |
| Turner | Default M1 rig (turn_kp 5, kv 0.2, torque clip 1 N·m), unchanged |
| Runner | M4 logic (`experiments/E4_scored_m4/run.py`), including the P-26 neighbour-list reset, through the new M5 runner (§6.1) |
| Software | MuJoCo 4.0.1, Python 3.12, NumPy and SciPy from `uv.lock` |

## 2. Run-integrity rules
- M1 rules 1–5 and M4 rules 1–3 apply unchanged:
  - clean commit;
  - edit audit;
  - numerical failure;
  - observed-move oracle;
  - no exclusions;
  - magnet callback check;
  - rule 2: magnet validity fails operational trials;
  - rule 3: magnet validity labels abuse trials.
- **The magnet start-up check (M4 rule 1) runs at the 0.05 mm gap** (O2). M4's runner runs it at the default 0.2 mm
  (`run.py:527`, `746`). The check's result records the gap it used (review 3, item 10), so this can be audited from
  the records.
- **Rule 4 (M5), seeds (R1): M5 seed = the M4 scored seed + 4000 for every trial.** This covers the hard-coded E1-5s
  and E1-6t bases (`run.py:87`, `99`) as well as `SEED_SHIFT`.

  | Experiment | M4 scored seeds | M5 seeds |
  |---|---|---|
  | E1-1 | 6000–6019 | 10000–10019 |
  | E1-2 | 6100–6123 | 10100–10123 |
  | E1-3 | 6200–6239 | 10200–10239 |
  | E1-4 | 6300–6419 | 10300–10419 |
  | E1-5 | 6500–6541 | 10500–10541 |
  | E1-5s | 6551–6568 | 10551–10568 |
  | E1-6 | 6600–6627 | 10600–10627 |
  | E1-6t | 6640–6655 | 10640–10655 |
  | E1-7 | 6000 | 10000 |

  Ranges are first–last. Not every seed between them is used: the exact list is the M4 runner's list + 4000. All M5
  seeds lie in 10000–10999.
- **No simulation on M5 seeds before the scored run** (P5). Smoke tests and unit tests use seeds outside every
  registered range, or do not simulate. That range is disjoint from:
  - M1 (1000–1999) and M2 (2000–3999);
  - the diagnostics (4302, 4401) and stage 1 (5100–5299);
  - **M4's scored battery (6000–6999, used by the run recorded in P-37)**;
  - the rehearsals (7000–8999) and the M4 diagnostics (9000–9999).

  A repository search found no use of seeds of 10000 or more. A unit test (§6.1) checks that the runner's full M5
  seed list equals the M4 list + 4000 and lies in 10000–10999.
- **Run procedure: first start, resume, manifest and ledger** (T1, option (a)). M4's `_execute` skips trial files
  that already exist (`run.py:645–648`), and its CLI runs one experiment per call. The M5 scored run is defined as
  follows.
  - **Scored trial list.** The full M5 list: E1-1 to E1-6, E1-5s and E1-6t (204 trials), E1-6n and E1-7, built by the
    runner from the rules in §2–§4.
  - **Before the first start**, every §6.1 item, including item 5 (the V3 checks for E1-7), is complete and
    committed. Each trial in the list is then either runnable or, for an E1-7 arm only, "not run" for a reason
    registered in §4. The runner refuses to start if any other trial would be refused.
  - **First start.** The runner refuses unless `experiments/E5_scored_m5/results/` and `results_nomag/` are both
    empty or absent. It then writes `experiments/E5_scored_m5/results/MANIFEST.json`, before any trial: the source
    commit, the start time, the full trial list (experiment, trial ID, seed, arm, overrides) and the E1-7 arms that
    are "not run" with their reasons.
  - **Resume.** A later start is allowed only to complete the run. It requires that `MANIFEST.json` exists, that HEAD
    equals the manifest's commit and passes the clean-commit check, and that the trial list the runner builds now is
    identical to the manifest's. It runs only trial IDs that have no record. It never deletes, rewrites or reruns an
    existing record. Each start, with its time and the number of trials it ran, is appended to the manifest's start
    log.
  - **Atomic records.** Each record is written to a temporary file in the same folder and then linked to its final
    name, which fails if the name exists, so a record is either complete or absent. After each record is written, the
    runner appends its trial ID and the record's SHA-256 to `experiments/E5_scored_m5/results/LEDGER.txt`, which is
    only ever appended to.
  - **A harness exception inside a trial** (any exception other than a refusal) is written as a failing record with
    the exception text. It counts as a failed trial, not a missing one, and is never retried.
  - **Interruption.** If the process stops (crash, restart, out of memory), the run is resumed under the rule above.
    Trials that never wrote a record are run on resume; this is completion, not a rerun. A run that cannot be
    completed from its manifest's commit stays INCOMPLETE, and G1 is not passed.
  - **Integrity** (checked by the verdict script, §5): a leftover temporary file, a record that does not parse, a
    record without a ledger line, a ledger line without a matching record or with a different SHA-256, a trial ID
    that appears twice in the ledger, or a record not in the manifest gives INVALID.
  - The scored results are committed only after the run is complete.

## 3. What varies between trials
- As M4: misalignment ±1° per face applied before t = 0 and logged, grip 10–20 N, 0.8–1.2 s per quarter turn.
- **E1-4 scrambles (O1):** the 20 scramble+inverse sequences are drawn with `random_scramble(20, s)`, where s is the
  **M5 seed** of that trial (10400–10419), not M1's seed (1400–1419). This follows M1 §2, which draws each scramble as
  `random_scramble(20, s)` from the trial's seed s (`PHASE_1_PREREGISTRATION.md:52`).
  - This is a disclosed deviation from M4's runner, which reuses M1's scramble strings.
  - It makes the 20 sequences new to every unscored run (§0 item 2).
  - The scrambles are logged per trial, as in M4.

## 4. Experiments and thresholds
**All of M4 §4 and Amendment 1 item A2 apply unchanged:**
- E1-1 to E1-6, with M1's thresholds;
- Option A;
- magnet validity;
- the E1-4 growth slope < 0.005°/move;
- E1-5s;
- E1-6c, M1's categorical criterion, with twist, penetration and the torque at 15° reported;
- E1-6t: 0.45 N·m; solved after release; penetration ≤ 0.5 mm;
- E1-6m;
- E1-6n;
- E1-8.

The changes in this section are the reported-only additions, the E1-7 band and the E1-7 V3 requirements. The other
changes (gap, start-up check, seeds, run procedure, scramble draw, label, integrity checks, verdict script) are in §1–§3
and §5:

| ID | Change |
|---|---|
| **E1-6n** | Unchanged in form: a no-magnet rerun on the same seeds, reported only. **E1-6n results never enter Option A** (O6). **Disclosed:** at 0.05 mm the no-magnet arm is expected to jam (P-27), so it shows that the magnets are necessary rather than giving a like-for-like comparison. Rule 3 names the no-magnet arm "the bound" for E1-6b and E1-6c, and at 0.05 mm that bound may say little. The verdict therefore reports the no-magnet E1-6b, E1-6c **and E1-6t** outcomes next to the corresponding magnet trials (E1-6t is subject to rule 3 and is a G1 criterion) |
| **Turner torque (NEW, reported)** | For every move of E1-2 to E1-4, the per-move peak turner torque, its median / p99 / max, and the number of moves **at the clip, defined as a peak of ≥ 0.999 N·m** (P3). No threshold (§0 item 5) |
| **E1-7 sensitivity, M5 factors** | M4's factors, with the two gap factors re-centred. **Piece gap 0.025 / 0.05 / 0.1 mm** uses the 0.5× / 1× / 2× rule of M4's Amendment 1 item A1, which for M4 gave 0.05 / 0.1 / 0.2 mm; the user chose it (P-34). A1 itself was never adopted (P-25); only its band rule is reused here. The declined alternative was M1's ±50 % rule (0.025 / 0.05 / 0.075 mm). **Face gap 0.35 / 0.85 / 1.35 mm** (wall 0.15 / 0.4 / 0.65 mm) keeps M4's ±0.5 mm band. **E1-7 nominal values: piece gap 0.05 mm, face gap 0.85 mm (N1)**, so the nominal trial is not run twice under another tag. The magnet size, grade and strength-scale factors are as M4. **Disclosed:** 0.1 mm is known from the P-25 rehearsal to fail M1's drift criterion, so a flip at the upper gap is expected. As for every E1-7 factor, a flip is reported as a fragility, not a G1 failure (M4 §4). 0.025 mm has never been run. **The E1-7 no-magnet arm is expected to jam at 0.05 mm** (P7; P-27) |
| **E1-7 magnet configurations and V3 (O5, P1)** | **V3 records are matched by size, grade and strength scale.** The M4 runner's `v3_record_for` matches by size only (`run.py:232–243`), so it would reuse the 4×2 N35 record for 4×2 N52 and for the 0.67 strength scale. Grade and scale both change only the Br² strength, so they are treated alike: each needs its own V3 record (review 3, item 8). **4×1.5 N35 failed V3 (P-26).** It is not retested under altered V3 settings, and its arm is reported as "not run: failed V3". **4×2 N52 and the 0.67 strength scale** each need a V3 check at unchanged settings; if one fails, that arm is "not run: failed V3". **The 0.35 mm face gap is below the 0.5–1.5 mm face gaps at which V3 tested magnet pairs** (P1). That arm runs only if a V3 pair check at 0.35 mm passes at unchanged settings; otherwise it is "not run: outside V3". **E1-7 counts as complete** when every arm has either run or is "not run" for one of these registered reasons (review 3, item 12). The checks gate E1-7 only, and they must be complete and committed before the first scored trial (§2, §6.1 item 5) |

## 5. Pass logic and verdict script (R2)
- **Option A,** as for M1 and M4: every categorical and quantitative criterion holds in 100 % of scored trials of
  E1-1 to E1-6, **including E1-5s, E1-6t and E1-6m**. E1-6n never enters (§4).
- **Verdict script:** `experiments/E5_scored_m5/analyze.py`, frozen with the runner (§6.1). M4's `analyze.py` omits
  E1-6t from its expected counts and its verdict (`analyze.py:16–18`, P-33), so the M5 script must:
  - expect E1-1 20, E1-2 24, E1-3 22, E1-4 40, E1-5 42, E1-5s 20, E1-6a 6, E1-6b 6, E1-6c 8 and **E1-6t 16** trials,
    204 in all, and report NOT PASSED / INCOMPLETE if any count differs;
  - take each trial's verdict from its stored `pass` flag, which includes E1-6t (`run.py:505`);
  - judge **E1-6m** from the per-move `e16m_P_ok` flags of E1-2 to E1-4, as M4's `analyze.py` does (E1-6m is not in
    the per-trial `pass` flag);
  - report the reported-only items in §4;
  - **check every record's integrity (P4):**
    - the trial ID and seed are in the registered list and in the manifest (§2);
    - all records carry a single source commit, equal to the manifest's;
    - `scored` is true;
    - `params.gap` (cubies) and `magnets.layout_gap` (the gap the magnet layout was built for; review 3, item 1) are
      both 2.5e-5 in the E1-7 0.025 mm piece-gap arm, both 1e-4 in the E1-7 0.1 mm piece-gap arm, and both 5e-5 in
      every other record, including the E1-7 face-gap arms (review 3, item 2). Records without magnets (E1-6n and the
      E1-7 "none" arm) carry no layout gap, and only `params.gap` is checked for them;
    - the `mechanism` label is "M5". The M4 runner writes "M4" (`run.py:658`), so the M5 runner must set it;
    - every E1-4 scramble+inverse sequence equals the one re-derived from the trial's seed with
      `random_scramble(20, s)` and its inverse (review 3, item 11; §3);
    - the run-procedure checks in §2 (manifest, ledger, atomic records).

    Any violation gives NOT PASSED / INVALID.
- **Tests (§6.1):** a synthetic record set in which only one E1-6t trial fails must give NOT PASSED. The same must hold
  with only one move failing `e16m_P_ok`, and with one E1-6t record missing. **Each of these must give INVALID**
  (review 3, item 3): a record labelled "M4"; a record with `params.gap` 2e-4; a record whose `magnets.layout_gap`
  differs from its `params.gap`; two source commits; `scored` false; a trial ID outside the list; an E1-4 sequence
  that does not match its seed; a record that does not parse; a record with no ledger line; a ledger SHA-256 that does
  not match its record.
- E1-7 and E1-8 must be completed and published. G1 also needs the user's sign-off.
- **The G1 verdict text must restate** (O7):
  - §0 items 1–3: the gap was chosen post hoc, the move strings are shared with the rehearsals, and the clearance is
    an assumption;
  - the observed drift margin;
  - the number of moves at the turner clip;
  - the rule-3 labels, with the no-magnet E1-6b, E1-6c and E1-6t outcomes (review 3, item 4);
  - the number of starts in the manifest's start log, and how many trials each start ran (§2).
- If M5 fails, the failure is documented in full and G1 stays not passed. No rerun, no exclusion, and a scripted
  rotation is never a fallback.

## 6. Work required
### 6.1 Gates the scored run (O4)
1. **Scored runner `experiments/E5_scored_m5/run.py`.** It reuses M4's `run.py` logic unchanged **except for the items
   listed here** (review 3, item 7):
   - gap 0.05 mm set in **both** `BASE_OVERRIDES` and every trial's `kw["overrides"]`, so the magnet layout is built for
     0.05 mm (`run.py:602`, O3);
   - **except that in the E1-7 piece-gap arms the factor's value takes precedence for both the cubies and the magnet
     layout (N1).** `rehearsal_gap.py:42` overwrites the gap unconditionally, so it must **not** be copied for E1-7;
   - each record stores `magnets.layout_gap`, the gap passed to `use_magnets` for that trial (review 3, item 1).
     `MagnetSystem` stores neither the parameters nor the gap (`magnets.py:418–438`), and `describe()` does not
     record it;
   - `mechanism` = "M5" in every record (P4);
   - the V3 lookup matched by size, grade **and strength scale** (§4);
   - the start-up check at 0.05 mm, with the gap recorded in its result (O2; review 3, item 10);
   - seeds = M4 seed + 4000 (§2); `SCORED_SEED_RANGE` = 10000–10999 (`run.py:81`, asserted at `699`);
   - `OUT` and `OUT_NOMAG` under `experiments/E5_scored_m5/`;
   - E1-4 scrambles drawn from the M5 seed (§3);
   - the run procedure in §2: first-start check of both result folders, manifest, resume rule, atomic records, ledger,
     and harness exceptions written as failing records;
   - the turner-torque report;
   - the re-centred E1-7 factors. M4's face-gap factor computes the wall from M1's nominal 0.2 mm gap (`run.py:211`),
     so M5 must compute it from 0.05 mm;
   - a clean-commit check covering M4's frozen paths, every V3 record (`experiments/D8_alignment/results/d8_1b_checks*.json`;
     review 3, item 5), this runner, `analyze.py` and this file.
2. **Verdict script `experiments/E5_scored_m5/analyze.py`** (§5).
3. **Unit tests** (none steps the simulation on an M5 seed, P5):
   - the seed list (§2);
   - **the gap (N1, O3; review 3, item 1).** For every job of the full M5 list, with `params_for` and `use_magnets`
     intercepted and no stepping: the cubie gap passed to `params_for` equals `expected_gap`, and the magnet positions
     `p_loc` of the magnet system built for the job equal those of `layout(pitch, expected_gap, mp)`
     (`magnets.py:92`), where `expected_gap` is
     2.5e-5 in the 0.025 mm arm, 1e-4 in the 0.1 mm arm and 5e-5 in every other trial, E1-7 included. The recorded
     `magnets.layout_gap` equals `expected_gap`. The test must fail under the rehearsal-style overwrite;
   - the wall computation for each E1-7 face gap;
   - the E1-4 scrambles drawn from the M5 seeds;
   - the run procedure: first-start refusal when either result folder is not empty; resume refused on a different
     commit or a different trial list; resume runs only the trials without records; a record is never overwritten;
     the ledger line is written; a harness exception gives a failing record;
   - the start-up check records the 0.05 mm gap;
   - the verdict-script cases in §5.
4. **A smoke test**, one trial per experiment, on seeds outside every range. It is unscored and only checks the
   plumbing.
5. **For E1-7, before the first scored trial (§2):** V3 checks for 4×2 N52 and for the 0.67 strength scale, and a V3
   pair check at a 0.35 mm face gap, all at unchanged settings (§4). Their records are committed and covered by the
   clean-commit check.

### 6.2 Gates the G1 sign-off only (O4)
6. **E1-8 on a quiet machine**, with load average and CPU model recorded. This needs the user's other workload paused.

## 7. Known issues carried into scoring (`INFERENCE`)
- **Drift margin:** 0.26° below the 1° criterion in the rehearsal. Across 1,376 moves, with new setup draws and 20
  new scrambles, a move above 1° is possible.
- **Torque headroom:** §0 item 5. A seed with higher friction or misalignment could clip the turner for longer.
  Whether that would show as a turn error is not known.
- **Magnet force may be overstated by about 1.5×** (V2). E1-7's 0.67 strength scale tests this. Because the magnets
  prevent jamming at 0.05 mm, weaker magnets may jam: a likely fragility.
- **Abuse penetration** reached 0.61 mm (E1-6b) and 0.65 mm (E1-6c) in the rehearsal. Both are categorical
  experiments, so these values are reported and not judged against 0.5 mm, as for M4.

## 8. Decisions requested
1. Approve revision 4, or modify it. A fourth independent review was approved with the drafting (P-39) and runs
   before the user's decision.

## 9. Changes from revision 1
| Review item | Change |
|---|---|
| R1 seeds | §2: M5 seed = M4 scored seed + 4000 for every trial, with a table and a unit test |
| R2 verdict script | §5: a named, frozen `analyze.py` that includes E1-6t (16) and E1-6m, with failure tests |
| R3 independence | §0 item 2 and the G1 restatement (§5); E1-4 scrambles held out (O1) |
| R4 E1-7 band | §4: Amendment A1's 0.5× / 1× / 2× rule (0.025 / 0.05 / 0.1 mm), chosen by the user (P-34); the known 0.1 mm failure is disclosed |
| R5 stale text | §2: 6000–6999 is in use by M4's scored run; §8 lists only open decisions; the freeze rule is under Status |
| O1–O8 | O1 §3; O2 §2; O3 §6.1 item 1; O4 §6; O5 §4; O6 §4; O7 §2 and §5; O8 §0 item 3 |

**Revision 3 (review 2):**

| Review-2 item | Change |
|---|---|
| **N1 (required)** | §6.1 item 1: the E1-7 gap factor takes precedence for the cubies and the magnets, with a test. §4: E1-7 nominal = 0.05 mm gap and 0.85 mm face gap |
| O5 gap | §4 and §6.1: V3 matched by size and grade; N52 needs its own record |
| O6 | §4: E1-6t is added to the no-magnet side-by-side |
| O8 | Patent and sources recorded in `R1_real_cube_bench/LITERATURE.md` ("Piece clearance") |
| P1 | §4: the 0.35 mm face-gap arm needs a V3 pair check, or is "not run: outside V3" |
| P2 | §4: A1 was never adopted, and the declined ±50 % alternative is named |
| P3 | §4: the clip is defined as a peak of ≥ 0.999 N·m |
| P4 | §5: integrity checks in the verdict script; mechanism label "M5" |
| P5 | §2: no simulation on M5 seeds before the scored run |
| P6 | Status: a provenance statement |
| P7 | §4: the E1-7 no-magnet arm is expected to jam |
| Wording | §0 item 2 (which strings come from which seeds); §2 (seed ranges have gaps) |

**Revision 4 (review 3; user: "all approved", P-39):**

| Review-3 item | Change |
|---|---|
| **T1 (required), option (a)** | §2: a resumable run. First start requires both result folders empty and writes a manifest; a resume needs the same commit and trial list and runs only trials without records; atomic records; an append-only ledger; harness exceptions become failing records; integrity violations give INVALID. §6.1 item 5 must be committed before the first scored trial. The empty-folder check covers `results_nomag/` |
| 1 | §6.1 items 1 and 3: the gap test compares `p_loc` with `layout(pitch, expected_gap, mp)`; each record stores `magnets.layout_gap`, checked in §5 |
| 2 | §5: the gap integrity check names the two piece-gap arms and their values |
| 3 | §5: tests that each integrity violation gives INVALID |
| 4 | §5: the G1 restatement adds the no-magnet E1-6t outcomes |
| 5 | §6.1 item 1: every V3 record is under the clean-commit check |
| 6 | Basis and §4: complete lists of what changes |
| 7 | §6.1 item 1: `SCORED_SEED_RANGE`, `OUT`, `OUT_NOMAG`; "unchanged except for the items listed" |
| 8 | §4: V3 matched by strength scale as well; the 0.67 scale needs its own V3 check (§6.1 item 5) |
| 9 | §1: per-configuration validated tilts (3 × 1.5 mm N35: 7.5°) |
| 10 | §2 and §6.1: the start-up check records its gap |
| 11 | §5: the verdict script re-derives each E1-4 scramble from its seed |
| 12 | §4: E1-7 counts as complete when an arm is "not run" for a registered reason |
| Status | Provenance for revision 4; §2 and the freeze rule updated now that M4's run has finished (P-37) |
