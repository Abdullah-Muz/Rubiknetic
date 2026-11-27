# G2 pre-registration review 4 (2026-11-27)

VERDICT: REQUIRES CHANGES

*(Independent reviewer subagent, round 4 (P-121). It was given the pre-registration, the code, the evidence and
reviews 1–3, not the assistant's conclusions. The report is saved as returned.)*

## Scope and what I ran
I reviewed revision 4 at HEAD `80c8324`. I compared it with `E8_scored_g2/{run,trials,analyze,selfcheck,rerun_crashed}.py`, `D18/{two_arm,layout}.py`, `D17/{hold,turn}.py`, `tests/test_scored_g2.py`, the pilot records (P5, pilot 2, pilot 3 and its re-runs), `selfcheck_rev4_2026-11-27.log`, DECISION_LOG P-128/P-129 and reviews 1–3. Nothing in the repository was changed or committed. My scratch scripts are in the session scratchpad, with outputs in WSL `/tmp/rev4_*`. No scored seed was simulated.

What I ran:
- **Unit tests:** `pytest -q tests/test_scored_g2.py`, **62 passed** (62 dots, no F or E).
- **Magnet callback probe:** built `TwoArm` (seed 29001) and logged every `mujoco.set_mjcb_passive` call and every `MagnetSystem.apply` call.
- **Magnets off vs on, pilot seeds only:**
  - P2-Up `Up_s29300` as the code stands, and the same trial with the magnet callback put back after arm B's pre-grasp IK.
  - P3-ext `Up_m1.00_4_s29404` (U forced to −1.0°) with the callback put back.
  - A magnets-on `seq5_s29340` run was still going when I wrote this. It is not reported.
- **Pilot statistics:** recomputed from the committed records to check §0, §4.1 and §8 item 8.

## Review-3 items
| # | Status | Evidence |
|---|---|---|
| R1 load-error retry by message | **FIXED** | `run.py:203-234`: the rule depends on the phase; `LOAD_ERRORS` markers are gone. `two_arm.py:97,577-580`: the flag is set in `ctrl_step` before `sim.step`. `trials.py:64-72`. Before `ctrl_step`, the only steps are `mj_forward`, IK on separate models and setup writes; the start sequence itself uses `self.step` → `ctrl_step` (`two_arm.py:495-509`). Tests at `test:322-383` cover each empty-file message, an arbitrary message, the after-step case and the real flag. |
| R2 unfrozen E1 runner | **FIXED** | `run.py:59`. `test:100-148` audits `open` events in a fresh process and asserts that `E1_scored/run.py` is among the files seen. Scope: import, build and start sequence only (enough, because moves open no new files; `INFERENCE`). |
| S3 test gaps | **FIXED** | `test:650-662`: the construction-time `roll_sign` is kept and checked against `a_d`. `test:700-769`: model-audit positive controls for every element type, plus a robot-only negative. §2 wording at lines 98-100. |
| S4 stale evidence | **FIXED** | Recomputed (`FACT`): 156 non-offcentre records; t0 offset max 2.083 mm (`U2_m1.00_4_s29419`); drop shift max 0.119 mm; causality gap minimum 2 steps (twice), then 3 steps (13) and 4 steps (16); first-move turn error max 1.747° (`U2_m0.95_8_s29423`); end misalignment 2.83°; total rotation 1.24°; per-move core rotation 0.93°. Minor: I count 276 recorded moves, not "244". |
| S5 interruptions / verdict re-runs | **FIXED** | `run.py:67,434-436`; `analyze.py:195,205-206,317-319`; prereg lines 331-334 and 356-358; `test:185-202`. |
| S6 evidence at final code | **FIXED** (but see N1) | The self-check log shows 3/3 identical at `bb58342`; the pilot-3 README line 39 names re-run commit `6e4a0de`. |
| S7 no edits after freeze | **FIXED** | Prereg lines 20-22. |

## New findings

### N1. REQUIRED: the M7 magnets are switched off in every G2 trial. The text says otherwise, and every piece of pilot evidence was produced without them.
**What happens (`FACT`):**
- `TwoArm.__init__` installs the magnet callback at `two_arm.py:401` (`H.install_magnets` → `set_mjcb_passive`).
- At `two_arm.py:420` it calls `b_robot_spec()` → `hold.robot_spec`, which runs `MagnetSystem.uninstall()` first (`hold.py:65`).
- Nothing installs the callback again, so the global passive callback stays `None` for the whole trial.

**Probe results (`FACT`):**
- The logged `set_mjcb_passive` sequence ends with `SET` at `two_arm.py:401` followed by `CLEAR` at `two_arm.py:420`.
- `mujoco.get_mjcb_passive()` returns `None` after construction.
- `MagnetSystem.apply` ran once (the setup `mj_forward`) across all 7,200 start-sequence steps.
- The as-is `Up_s29300` run had 1 apply call and reproduced the committed pilot-2 record **bit-for-bit** (qpos SHA `7f7ec76b…`). The pilots, and the self-check that matches them, therefore ran without magnets.

**History (`FACT`, git):** the ordering dates from D18's first commit `b3b856a` (P-108): install at line 116, then `robot_spec` at line 133. All D18 work, P-115, P5, pilots 2 and 3 and both self-checks are affected. D17's `turn.py` builds its extra model before installing (`turn.py:158` before `:172`) and is not affected.

**Contradictions with the text:**
- §1 (line 77) says "M7 as G1-scored: B1, L0 magnets (unchanged `MagnetSystem`)". The D17 and D18 READMEs repeat it.
- §0.6 lists no magnet-free assumption.
- The magnet table is hashed and the magnet refusal rule is described, yet the magnets have no physical effect.

**It changes the outcome (`FACT`, pilot seeds, F/T stop disabled):**

| Trial | Magnets | Turn error | F/T peak | End misalignment | `MagnetSystem.apply` calls |
|---|---|---|---|---|---|
| `Up_s29300` | off (as is) | 0.80° | 0.193 N·m | 1.77° | 1 |
| `Up_s29300` | on | −0.05° | 0.215 N·m | 0.57° | 20,820 |
| `Up_m1.00_4_s29404` | off (committed record) | 1.56° | 0.41 N·m | – | – |
| `Up_m1.00_4_s29404` | on | −0.22° | 0.18 N·m | 0.76° | – |

Consequences:
- A PASS would be a result for a **magnet-free** cube, reported as M7. The magnets act through a fixed passive force law, so leaving them out is not a hidden actuation, but it is a different mechanism from the one in §1. In that sense the PASS would be false.
- Every limit and margin set from pilots is built on the wrong system:
  - the F/T stop (P-125) and its 1.49× margin;
  - the 20–50° jam window;
  - the two_layer detection at 1.05–1.11 N·m;
  - the end-misalignment bound and the "tightest margin" disclosure (§0.4, which looks like an artefact of the missing detent);
  - the hold and slip numbers;
  - the U′ torque regression.
- With magnets on, some of these could move toward a failure. The magnets add turning resistance, and their effect on the jam and two_layer stops is unknown. So the risk of a false NOT PASSED is not disclosed either.

**Fix:**
1. In `TwoArm.__init__`, build `m0` (`b_robot_spec().compile()`) before `install_magnets`, or call `self.ms.install()` again after it and before any step. Check every other `robot_spec` or `compile` call on the trial path.
2. Add a judged integrity field. For example, count `MagnetSystem.apply` calls in `AuditedSim.step` (or store `mujoco.get_mjcb_passive() is not None` at every move boundary) and require the count to equal the number of steps. The worker check and `analyze._integrity` must both enforce it, with a unit test.
3. Re-run the pilots (first-turn torque tail, jam, two_layer, 10-move sequences, holds) at the corrected code. Re-derive or reconfirm the F/T stop, the jam window and the stated margins, and re-run `selfcheck.py` against new reference records. The current P5 references are magnet-free.
4. Record this in the DECISION_LOG as a defect found after pilots. Disclose that D18 through pilot 3 were magnet-free and that every limit was revisited on new pilot seeds.

### N2. SUGGESTED: the verdict re-run rule covers only artifact hashes.
- §6 (lines 356-358) lets only an artifact-hash INVALID be re-checked. Other INVALID causes that a transient empty read on `/mnt/c` can also produce "stand as found": "record does not parse", "ledger SHA-256 differs" and "no ledger line" (an empty `LEDGER.txt` read).
- `analyze.integrity` reads every record and the ledger from disk (`analyze.py:257-296`).
- Fix: any INVALID that comes from reading a file must reproduce on a re-run, and every verdict run must be reported. Alternatively, run the verdict on a hash-verified copy on the native WSL filesystem. Either is safe because the verdict is deterministic on unchanged files.

### N3. SUGGESTED (minor): stale count in §4.1.
§4.1 and P-129 say "244 pilot moves"; I count 276. The claim it supports (minimum gap 2 steps) holds either way.

## Checked with no problem found
- **Load-error handling:**
  - A `Refused` after the first step is retried, then becomes an interruption.
  - `MemoryError` always interrupts.
  - A failure in `NumericalFailure`/`EditAuditError` during the start sequence or the approach becomes a failing record (`run()` does not catch it, the flag is set, and it is not an `OSError`; rig classes subclass `RuntimeError`).
  - A retry in the same worker re-runs `configure`. `install` replaces the callback, so there is no double counting, and the F/T RNG is recreated.
  - A deterministic error before the first step can only interrupt the run; it cannot produce a record.
- **Resume limits and verdict state:**
  - `MAX_STARTS` refusal fires before the STARTS line is written; the runner and analyze copies agree (6).
  - More than 6 starts gives INVALID; INCOMPLETE after 6 gives NOT PASSED.
  - `code_problems` checks the frozen paths and uncommitted changes.
- **Independence and agreement:**
  - The verdict's recomputation (`recompute_seq/hold/neg`) matches `trials._seq_reasons`/`neg_outcome`. The test checks that the limits agree.
  - The seq integrity check requires `tendons_on_cube` in the model audit.
- **Controller-input and audit tests:** the bit-identity test and the roll-command test with positive controls are sound; the model-audit tests pass.
- **Self-check:** 3/3 identical at `bb58342`, which is a valid identity check against magnet-free references (N1).
- **Pre-step path of the G2-6 conditions:** it differs from the piloted path only in grip (`set_grip` has no range assertion; 50 N was run in the D18 logs), `tip_solref`, `pad_mu` and the cube offset. None of these can raise deterministically before the first step (`INFERENCE`).

---
**Assistant's verification of N1 (2026-11-27, not part of the review):** reading `two_arm.py:401` and `:420` and `hold.py:65` confirms the order. A separate probe (seed 29001, `TwoArm` construction) gave `mujoco.get_mjcb_passive()` = None after construction, with `MagnetSystem.apply` called once over 3.6 s of simulated time (`FACT`).
