# Phase 1 (G1) Pre-registration: M5, magnetic contact cube at a 0.05 mm piece gap

**Status: revision 8, NOT YET IN FORCE.** At the user's request, the working copy moves out of OneDrive to
`C:\dev\Rubiknetic`, and the OneDrive rule of §2 changes from "OneDrive exited" to "no path the run uses lies in a
OneDrive folder" (P-49). The user approved it on condition that a very narrow independent review of the revision-8
changes require no changes. Revision 7 stays in force until then; no scored trial has run. See §9.
- **Revision 7** (P-47) was approved on condition that a very narrow independent review of the revision-7 changes
  require no changes. That review returned ACCEPTABLE AS IS
  ([`M5_PREREGISTRATION_REVIEW7_2026-11-16.md`](M5_PREREGISTRATION_REVIEW7_2026-11-16.md)), and revision 7 came into
  force (P-48). Its optional items Y1–Y5 were not adopted. Revision 7 makes W1 and adopts X1–X6 from review 6.
- **Revision 6** (P-45) was approved on condition that a narrow independent review of the changes since revision 5
  require no changes. That review required one change, W1
  ([`M5_PREREGISTRATION_REVIEW6_2026-11-16.md`](M5_PREREGISTRATION_REVIEW6_2026-11-16.md); P-46), so revision 6 was
  never in force.
- **Revision 5** (P-42) was approved on condition that a fifth independent review of the text and the §6.1 code
  require no changes (P-43). That review required one change, V1, a missing registered test
  ([`M5_PREREGISTRATION_REVIEW5_2026-11-16.md`](M5_PREREGISTRATION_REVIEW5_2026-11-16.md); P-44), so revision 5 was
  never in force. Revision 6 (P-45) adds that test and adopts all twelve optional changes from review 5, as the user
  approved ("all have been approved"); see §9.
- **Revision 4** (P-39) was approved on condition that a fourth independent review require no changes (P-40). That
  review required two changes, U1 and U2 ([`M5_PREREGISTRATION_REVIEW4_2026-11-16.md`](M5_PREREGISTRATION_REVIEW4_2026-11-16.md);
  P-41), so revision 4 was never in force. Revision 5 (P-42) makes U1 and U2 and adopts all eleven optional changes
  from review 4, as the user approved ("approved"); see §9. By the user's choice (P-42, option (b)), the §6.1 code is
  built before the fifth review, which then checks the text and the code together.
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
  - **Revisions 4 to 8 were written after M4's scored battery finished** (G1 NOT PASSED, 123 / 204; P-37), and the
    author has seen its results.
    - Every revision-4 change answers an item in review 3, every revision-5 change an item in review 4, and every
      revision-6 change an item in review 5, and every revision-7 change an item in review 6. Revision 8 answers the
      user's request to stop depending on OneDrive. None of these reviews used M4's results (review 5 discloses that one
      grep printed the P-37 row and that nothing depends on it).
    - Some details are the author's own elaborations of the reviews' options (review 4, item 10): the ledger, the
      SHA-256 checks, the start log, the trial-list identity check and the harness-exception rule.
    - The changes concern run procedure, record integrity, tests and wording. **No criterion, threshold, factor value
      or seed is changed.** The one change to what can run is stricter: the 0.67 strength-scale arm of E1-7 now needs
      its own V3 record (review 3, item 8).
    - None of the changes was informed by M4's results.
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
  - the run procedure: first start, resume, manifest, start log, ledger and atomic records (§2, T1, U1, U2);
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
- **Run procedure** (T1 option (a), U1, U2). M4's `_execute` skips trial files that already exist
  (`run.py:645–648`), and its CLI runs one experiment, or `all`, per call. The M5 scored run is defined as follows.
  - **Record key (U2).** Every record is identified by **(arm, experiment, trial ID)**, where arm is `magnets`
    (folder `experiments/E5_scored_m5/results/`) or `no_magnets` (folder `results_nomag/`). E1-6n reuses the
    trial IDs of E1-2 to E1-6t (`run.py:101`, `689–692`), so the trial ID alone is not unique. The manifest, the ledger, the resume
    rule, the duplicate check and the "not in the manifest" check all use this key.
  - **Scored trial list.** The full M5 list, built by one `all` call: E1-1 to E1-6, E1-5s and E1-6t (204 trials), E1-6n
    and E1-7, from the rules in §2–§4.
  - **Before the first start**, every §6.1 item, including item 5 (the V3 checks for E1-7), is complete and
    committed. Each trial in the list is then either runnable or, for an E1-7 arm only, "not run" for a reason
    registered in §4. The runner refuses to start if any other trial would be refused.
  - **No path the run uses lies in a OneDrive folder** (revision 8; replaces "OneDrive is exited" of review 4,
    item 2 and review 5, O1), because any extra file in a results folder (for example a sync conflict copy) is
    INVALID. The working copy is `C:\dev\Rubiknetic`, a clone of the repository with the git-ignored near-field
    tables copied over (their SHA-256s are in the manifest). At every start other than a dry run, scored or smoke,
    the runner resolves links and refuses if the repository, either results folder, the smoke folder, M4's runner or
    the imported `rubiknetic` package has a path component named "OneDrive" or "OneDrive - …", or if the package is
    not imported from this repository's `src/`. OneDrive itself may run.
  - **First start.** M5 has exactly one first start. The runner refuses unless `results/` and `results_nomag/` are both
    empty or absent. Before any trial it writes `results/MANIFEST.json` atomically, from a temporary file kept next
    to `results/`, not in it (review 5, O2 (a)): a kill before the link leaves `results/` empty, so the first start
    can be repeated, and a kill after it leaves nothing extra in `results/`. The manifest holds:
    - the source commit and the start time;
    - the full trial list: key, kind, seed and overrides;
    - the E1-7 arms that are "not run", with their reasons;
    - the SHA-256 of the near-field table of every magnet configuration in the list (review 4, item 1). The tables
      are git-ignored (`.gitignore:74`), so the clean-commit check does not cover them;
    - the MuJoCo, NumPy, SciPy and Python versions and the CPU model (`scored.environment()` plus SciPy; review 5,
      O9). The platform string is reported but not compared, because a kernel update would change it.

    **The manifest is never changed or deleted** once written.
  - **Start log.** `results/STARTS.txt` is append-only. Each start appends one line before it runs any trial: its
    index k (1 for the first start), its time, HEAD, and what it did under (i) and (ii) below.
  - **Resume.** A later start is allowed only to complete the run. It requires:
    - that `MANIFEST.json` exists;
    - that the frozen paths (§6.1 item 1) are clean and identical between HEAD and the manifest's commit
      (`git diff <manifest commit> HEAD -- <frozen paths>` is empty). Commits made during the run may touch neither
      the frozen paths nor the results folders (review 4, item 5), and the resume diffs the results folders in the
      same way (review 5, O7). This file is a frozen path, so it is not edited between the first start and the end of
      the run. Records always carry the manifest's commit as `source_commit`, and each start's HEAD is in the start
      log;
    - that the trial list, the "not run" set, the table SHA-256s and the compared environment fields the runner
      builds now equal the manifest's;
    - that the results folders hold no file of a kind the verdict script rejects (§5), apart from orphan temporary
      files, which (i) handles (review 5, O1): only the manifest, start log and ledger at the top of `results/`,
      logged moved orphans in `_interrupted/`, and, in an experiment folder, temporary record files and the `.json`
      record of a manifest trial (revision 7, review 6 X3).

    Before running anything, a resume does two things (U1). It first writes its start-log line, listing both, and
    only then carries them out (review 5, O2 (b)); a kill in between leaves the files where they were, and the next
    resume plans them again:
    - **(i) Orphan temporary files.** Every temporary record file left by an interrupted start is moved to
      `<arm folder>/_interrupted/k<start index>__<experiment>__<name>` (review 5, O2 (c): two orphans of one trial
      never collide), without overwriting, and its name and SHA-256 are in the start log.
    - **(ii) Missing ledger lines.** For every complete, parseable record that is in the manifest but has no ledger
      line, the resume appends the line, marked "reconciled at start k".

    It then runs only keys that have no record. It never deletes, rewrites or reruns an existing record.
  - **Atomic records, one writer** (review 4, item 2). Worker processes run trials and return the records. Only the
    parent process writes files. For each record it:
    1. writes a temporary file `.<trial ID>.json.tmp` in the record's folder and flushes it to disk;
    2. links it to its final name with `os.link`, which fails if the name exists;
    3. removes the temporary name;
    4. appends one line to the append-only `results/LEDGER.txt`: the start index, the key and the record's SHA-256.

    A record is therefore either complete or absent. A kill between steps 1 and 3 leaves an orphan, handled by (i);
    a kill between steps 2 and 4 leaves a record without a ledger line, handled by (ii).
  - **A harness exception inside a trial** (U1 (iii); review 4, item 8).
    - **Any exception other than a refusal, `MemoryError` or `OSError`** is written as a failing record. It carries
      the job metadata (experiment, sub-experiment, trial ID, kind, seed, arm, `spec`, commit, `mechanism`,
      `scored`), the configured `params.gap`, and, for magnet jobs, `magnets.layout_gap`, both taken from the job's
      configuration, plus the exception text. Every §5 integrity check applies to it unchanged. It counts as a failed
      trial, not a missing one, and is never retried.
    - A record is also test-serialised inside the worker, so a record that cannot be saved is a failing record of
      this kind, not a crash (review 5, O4).
    - **`MemoryError`, `OSError`, a refusal raised during a trial, a killed worker, or a stopped parent** is an
      interruption (review 5, O5): no record is written, the runner stops, and the trial is run on resume.
  - **Interruption.** The run is resumed under the rule above. Trials that never wrote a record are run on resume;
    this is completion, not a rerun. A run that cannot be completed from its manifest stays **INCOMPLETE**, and G1 is
    not passed.
  - **Integrity** (checked by the verdict script, §5). Any of the following gives **INVALID**:
    - a temporary file not logged under (i);
    - a record that does not parse;
    - a record without a ledger line;
    - a ledger line without a matching record, or with a different SHA-256;
    - a key that appears twice in the ledger;
    - a record whose key is not in the manifest, or any other file in a results folder except `MANIFEST.json`,
      `STARTS.txt`, `LEDGER.txt` and `_interrupted/`.

    Reconciled ledger lines and logged orphans are accepted and reported.
  - **Finality** (review 4, item 4). INCOMPLETE and INVALID are final, like a failure (§5). Whatever the outcome, the
    manifest, start log, ledger and every record, complete or partial, are committed and reported.

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
| **E1-7 magnet configurations and V3 (O5, P1)** | **V3 records are matched by size, grade and strength scale.** The M4 runner's `v3_record_for` matches by size only (`run.py:232–243`), so it would reuse the 4×2 N35 record for 4×2 N52 and for the 0.67 strength scale. Grade and scale both change only the Br² strength, so they are treated alike: each needs its own V3 record (review 3, item 8). **4×1.5 N35 failed V3 (P-26).** It is not retested under altered V3 settings, and its arm is reported as "not run: failed V3". **4×2 N52 and the 0.67 strength scale** each need a V3 check at unchanged settings; if one fails, that arm is "not run: failed V3". **Matching rule** (review 4, item 6): only `experiments/D8_alignment/results/d8_1b_checks*.json` files that contain a `V3` block are considered; a record matches when its `magnet_params` diameter, length, grade and scale equal the arm's; `wall` is ignored, because the face-gap arms change only the wall. Exactly one record must match. No match, or more than one, is a refusal that stops the first start (§2), not a "not run" arm. **The 0.35 mm face gap is below the 0.5–1.5 mm face gaps at which V3 tested magnet pairs** (P1; `d8_1b_checks.py:133`). That arm (4×2 N35, scale 1, wall 0.15 mm) runs only if the **0.35 mm pair check** passes; otherwise it is "not run: outside V3". The pair check is V3 part (a) rerun with 0.35 mm added to its gap list and nothing else changed (`experiments/D8_alignment/v3_pair_extension.py`, record `d8_1b_checks_pair0.35mm_4x2_N35_s1.json`, which has no `V3` block): the same offsets, reference quadrature and force models; force error ≤ 5 % of the aligned facing-pair normal force at the nominal 1.0 mm gap; torque error ≤ max(5 % of the largest reference torque, 2e-5 N·m), with that maximum taken over the whole extended set (0.35 mm plus V3's five gaps). It passes if every row passes. **Disclosed** (review 5, O10): the pair check extends V3 part (a) only; parts (b) (tilted pairs) and (c) (whole cube) were not extended to 0.35 mm, so that arm uses the nominal record's validated tilt of 5°. This does not affect any verdict, because E1-7 is under neither rule 2 nor rule 3 (`run.py:89–90`). **E1-7 counts as complete** when every arm has either run or is "not run" for one of these registered reasons (review 3, item 12). The checks gate E1-7 only, and they must be complete and committed before the first scored trial (§2, §6.1 item 5) |

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
    - `startup_checks.gap` is 5e-5 in every magnet record (review 4, item 7);
    - `magnets.params.wall` is 0.15 / 0.65 mm in the E1-7 0.35 / 1.35 mm face-gap arms and 0.4 mm in every other
      magnet record (review 4, item 7; catches the `run.py:211` class of error after the run);
    - each magnet record has a `magnet_table` whose `table_file` is the table for its own configuration
      (`table_path`, `run.py:215–218`) and whose `table_sha256` equals the manifest's (review 5, O3), and its
      `environment` equals the manifest's in the compared fields (review 4, item 1);
    - the manifest's "not run" set equals the one re-derived from the committed V3 records (review 5, O3). The
      re-derivation applies the §4 rule to the committed V3 and pair-check records only; it never reads the
      git-ignored near-field tables, so a fresh clone gives the same verdict (revision 7, review 6 W1). Refusals of
      the §4 rule are part of the re-derived set as "refused: …", so a manifest made despite one is INVALID;
    - the run-procedure checks in §2 (record key, manifest, start log, ledger, atomic records).

    Any violation gives INVALID. Missing records give INCOMPLETE.
  - **Verdict order** (review 5, O6): INVALID, then INCOMPLETE, then NOT PASSED, then PASS. An INCOMPLETE run whose
    present records already fail Option A is reported as "INCOMPLETE (and NOT PASSED)". All but PASS are final, and
    none passes G1.
- **Tests (§6.1):**
  - **Positive control (U2):** a complete, valid synthetic record set, including E1-6n and E1-7 with its registered
    "not run" arms, must give PASS, not INVALID.
  - A synthetic set in which only one E1-6t trial fails must give NOT PASSED. The same must hold with only one move
    failing `e16m_P_ok`. One E1-6t record missing must give INCOMPLETE.
  - **Each of these must give INVALID** (review 3, item 3; review 4, item 7): a record labelled "M4"; a record with
    `params.gap` 2e-4; a record whose `magnets.layout_gap` differs from its `params.gap`; a piece-gap arm whose
    `layout_gap` equals its `params.gap` but not the registered value; two source commits; `scored` false; a trial ID
    outside the list; a record not in the manifest; an E1-4 sequence that does not match its seed; a record that does
    not parse; a record with no ledger line; a ledger line with no record; a ledger SHA-256 that does not match its
    record; a duplicate ledger key; an unlogged temporary file; a wrong `startup_checks.gap`; a wrong wall; a table
    SHA-256 that differs from the manifest's.
  - **Revision 6 (review 5, O3): each of these must also give INVALID**, so that no check can be removed without a
    test failing: a manifest key set that differs from the registered list; a record spec that differs from the
    registered trial; a seed that differs from the manifest; record metadata that does not match its key; an orphan in
    `_interrupted/` that is not logged; any other unexpected file; a magnet record without magnets; a no-magnet record
    with magnets; a "not run" reason that is not registered; a "not run" set that differs from the re-derived one; a
    magnet record without a table record; a table file that is not its configuration's.
  - Accepted, not INVALID: a reconciled ledger line and a logged orphan (U1).
- E1-7 and E1-8 must be completed and published. G1 also needs the user's sign-off.
- **The G1 verdict text must restate** (O7):
  - §0 items 1–3: the gap was chosen post hoc, the move strings are shared with the rehearsals, and the clearance is
    an assumption;
  - the observed drift margin;
  - the number of moves at the turner clip;
  - the rule-3 labels, with the no-magnet E1-6b, E1-6c and E1-6t outcomes (review 3, item 4);
  - the number of starts in the start log, and how many records each start wrote, counted from the start index in
    each ledger line (§2; review 4, item 3), with any orphans moved and ledger lines reconciled.
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
     `MagnetSystem` stores the magnet parameters but not the piece gap or the `M1Params` (`magnets.py:418–438`), and
     `describe()` does not record the gap;
   - `mechanism` = "M5" in every record (P4);
   - the V3 lookup matched by size, grade **and strength scale** (§4);
   - the start-up check at 0.05 mm, with the gap recorded in its result (O2; review 3, item 10);
   - seeds = M4 seed + 4000 (§2); `SCORED_SEED_RANGE` = 10000–10999 (`run.py:81`, asserted at `699`);
   - `OUT` and `OUT_NOMAG` under `experiments/E5_scored_m5/`;
   - E1-4 scrambles drawn from the M5 seed (§3);
   - the run procedure in §2: record key, first-start check of both result folders, manifest, start log, resume rule
     with (i) and (ii), atomic records written by the parent process only, ledger, and the exception rules;
   - the location check at every start (revision 8; it replaces the OneDrive-process check); a refusal to write a smoke run into the scored folders (review 5,
     O11);
   - the turner-torque report;
   - the re-centred E1-7 factors. M4's face-gap factor computes the wall from M1's nominal 0.2 mm gap (`run.py:211`),
     so M5 must compute it from 0.05 mm;
   - a clean-commit check covering M4's frozen paths, every V3 record (`experiments/D8_alignment/results/d8_1b_checks*.json`;
     review 3, item 5), `experiments/D8_alignment/v3_pair_extension.py`, this runner, `analyze.py` and this file.
     These are "the frozen paths" of §2, together with M1's (`scored.py:49–50`).
2. **Verdict script `experiments/E5_scored_m5/analyze.py`** (§5).
3. **Unit tests** (none steps the simulation on an M5 seed, P5):
   - the seed list (§2);
   - **the gap (N1, O3; review 3, item 1).** For every job of the full M5 list, with `scored.Trial` replaced by a
     stub that records the parameters it receives and stops before any step (review 5, O8): the cubie gap in the parameters the stub receives equals
     `expected_gap`, and, for every magnet
     job (review 4, item 9), the magnet positions `p_loc` of the magnet system built for the job equal those of
     `layout(pitch, expected_gap, mp)` (`magnets.py:92`), where `expected_gap` is 2.5e-5 in the 0.025 mm arm, 1e-4 in
     the 0.1 mm arm and 5e-5 in every other trial, E1-7 included. The recorded `magnets.layout_gap` equals
     `expected_gap`. The test must fail under the rehearsal-style overwrite;
   - the wall computation for each E1-7 face gap;
   - the E1-4 scrambles drawn from the M5 seeds;
   - the V3 matching rule (§4): exactly one match, `wall` ignored, the pair-check record skipped;
   - the run procedure, with trials replaced by stand-ins that do not simulate:
     - first-start refusal when either result folder is not empty;
     - resume refused on a different frozen-path commit, a different trial list, a different "not run" set or a
       different table SHA-256;
     - resume runs only the keys without records, including an E1-6n trial whose magnet twin has a record (U2);
     - a record is never overwritten; the ledger line is written;
     - (i) an orphan temporary file is moved and logged; (ii) a record without a ledger line is reconciled (U1);
     - (iii) a harness exception gives a failing record with the job metadata and gap fields, which passes every
       integrity check; a `MemoryError` or `OSError` writes no record and stops the run;
   - the start-up check records the 0.05 mm gap;
   - **revision 6 (review 5):** a resume refused when the manifest commit's frozen paths differ from HEAD's, with the
     git check on (V1), and allowed from the manifest commit; a resume refused when commits touch the results folders,
     or when a foreign file is present; a kill after the start-log line but before the moves is recoverable; two
     orphans of one trial do not collide; the manifest's temporary file never lands in `results/`; a record that cannot
     be serialised is a failed trial; the smoke folder may not be a scored folder; a scored start is refused while
     OneDrive runs; the committed V3 records classify the full list as 440 runnable, 2 "not run" (4×1.5 N35, "failed
     V3") and 0 refused (O12);
   - **revision 7 (review 6):** with the near-field tables absent, the re-derived "not run" set is unchanged and a
     complete, valid set is not INVALID, also through the verdict script's command line (W1); the two tests that
     call the runner's command line cannot reach a real start (X1); a resume from a HEAD that differs from the
     manifest commit with the frozen paths unchanged is allowed, with git run (X2); a resume refuses a `.json` that is
     not a manifest trial's record (X3); undecodable `tasklist` output does not crash the OneDrive check (X4);
   - **revision 8:** the OneDrive-process tests are replaced. A scored start is refused when a results folder is in a
     folder named "OneDrive", "OneDrive - …" or "onedrive", and a smoke start when the smoke folder is; the path
     check follows links and ignores names such as "OneDriveTemp"; a package imported from another repository is
     refused; this working copy passes the check;
   - the verdict-script cases in §5.
4. **A smoke test** on seeds outside every range, unscored, in a scratch folder (review 4, item 11). It runs the full
   run procedure: manifest, start log, atomic link, ledger, a forced interruption and a resume. It includes one
   trial of each kind, at least one E1-6n job, and one E1-7 job per magnet configuration that will run.
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
None open. Revision 8 was approved with its condition (P-49): it takes effect if a very narrow review of the
revision-8 changes requires no changes. The commit that records that outcome in the Status line comes before the first
start, because this file is a frozen path (review 6, X6).

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

**Revision 5 (review 4; user: "approved", P-42):**

| Review-4 item | Change |
|---|---|
| **U1 (required)** | §2: a resume first moves and logs orphan temporary files (i) and reconciles missing ledger lines (ii); exception records carry the job metadata and gap fields and face every integrity check (iii). Tests in §6.1 item 3; accepted cases in §5 |
| **U2 (required)** | §2: the record key is (arm, experiment, trial ID) everywhere. §5: a positive-control test (a complete, valid set gives PASS) |
| 1 | §2: table SHA-256s and environment versions in the manifest, compared on resume; §5 checks them per record |
| 2 | §2: only the parent process writes records and ledger lines; the OneDrive sync is paused for the run |
| 3 | §2: a separate append-only start log; the start index in each ledger line; the manifest is immutable |
| 4 | §2: finality; the manifest is never deleted; partial records are committed and reported |
| 5 | §2: resume compares the frozen paths with the manifest's commit; commits during the run may not touch them or the results |
| 6 | §4: the V3 matching rule (exactly one match, `wall` ignored) and the exact 0.35 mm pair check, with its script and record |
| 7 | §5: integrity checks for `startup_checks.gap` and the wall; more INVALID tests |
| 8 | §2: `MemoryError` and `OSError` are interruptions, not failed trials |
| 9 | §6.1 item 3: the `p_loc` comparison covers magnet jobs only |
| 10 | Status: provenance names the author's own elaborations and the stricter 0.67-scale gate; §2 says the CLI also accepts `all` |
| 11 | §6.1 item 4: the smoke test exercises the run procedure, an interruption and a resume, E1-6n and every E1-7 magnet configuration |

**Revision 6 (review 5; user: "all have been approved", P-45):**

| Review-5 item | Change |
|---|---|
| **V1 (required)** | §6.1 item 3: a test with the git check on: a resume from a HEAD whose frozen paths differ from the manifest commit's is refused, and one from the manifest commit is allowed |
| O1 | §2: OneDrive exited, not paused, for the whole run; the runner checks at every scored start; a resume refuses if a foreign file is present |
| O2 | §2: the manifest's temporary file sits outside `results/`; the start-log line is written before orphans are moved or ledger lines reconciled; moved names carry the start index |
| O3 | §5: a magnet record must have the table record of its own configuration; the "not run" set is re-derived; tests for every check that had none |
| O4 | §2: records are test-serialised inside the worker |
| O5 | §2: a refusal during a trial is an interruption |
| O6 | §5: the verdict order is registered; "INCOMPLETE (and NOT PASSED)" |
| O7 | §2: the resume diff covers the results folders; this file is not edited during the run |
| O8 | §2 and §6.1: wording (E1-6n's trial IDs; what `MagnetSystem` stores; how the gap test intercepts) |
| O9 | §2: SciPy in the manifest and the compared environment |
| O10 | §4: the pair check covers V3 part (a) only, disclosed |
| O11 | §6.1 item 1: the smoke folder may not be a scored folder |
| O12 | §6.1 item 3: a test pins the 440 / 2 / 0 classification |

**Revision 7 (review 6; user: "fully approved, proceed", P-47):**

| Review-6 item | Change |
|---|---|
| **W1 (required)** | §5: the "not run" set is re-derived from the committed V3 and pair-check records only, never the near-field tables; `run.py` splits the §4 rule (`v3_rule`, `v3_not_run`) from the table check; tests with the tables absent |
| X1 | §6.1 item 3: the two command-line tests stub the start and point the scored folders at a scratch folder |
| X2 | §6.1 item 3: a resume test with HEAD ≠ manifest commit and unchanged frozen paths (`ccc6330` → `769eab2`) |
| X3 | §2: the foreign-file wording is exact, and a `.json` must be a manifest trial's record |
| X4 | §2 (code): `tasklist` output decoded with replacement; operationally, the repository is kept on the device before OneDrive is exited |
| X5 | §6.1 item 3 and `analyze.py` wording; the start table's column is "orphans planned (moved)"; a lost line continuation in `run.py` |
| X6 | §8: the Status-line commit precedes the first start; no commit touches the results folders during the run |

**Revision 8 (user request, P-49; not from a review):**

| Item | Change |
|---|---|
| OneDrive | §2: the working copy moves to `C:\dev\Rubiknetic` (a clone at `d9933fe`, the git-ignored tables and licensed CAD copied with identical SHA-256s; the WSL environment's editable install of `rubiknetic` repointed to it). The rule "OneDrive exited" becomes "no path the run uses lies in a OneDrive folder, and the package comes from this repository"; `onedrive_running` is replaced by `location_problems` / `require_local_location`, applied at every start other than a dry run |
| Tests | §6.1 item 3: the OneDrive-process tests are replaced by the location tests |
| Provenance | Status: the revision-7 and revision-8 changes are named (review 7, Y2) |
