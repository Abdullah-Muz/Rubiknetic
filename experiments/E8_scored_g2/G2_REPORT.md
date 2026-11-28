# G2 report: two xArm7 arms turn a layer of the free-core M7 cube by contact

**Status: G2 PASSED for M7, signed off by the user on 2026-11-28 (§8; DECISION_LOG P-144)**, with the §6 limitations as its stated scope. Scored run PASS (P-143). §1–§4 were drafted before the
scored run (the skeleton committed at `ad08a50`); §5 and the result fields were filled in after it. This file is not a
frozen path: under the pre-registration (status block), results and discussion go here, and frozen files are never
edited after the freeze.

**Labels:**
- `FACT`: from a committed record or file.
- `INFERENCE`: the main session's reading.
- `ASSUMPTION`: as in the pre-registration §0.6.

## 1. What was tested
- **Gate:** `docs/VALIDATION_PLAN.md` G2: repeatable, contact-driven layer turns by two robot arms with prescribed
  classical controllers; no learning.
- **Plan:** [`../PHASE_2_G2_PREREGISTRATION.md`](../PHASE_2_G2_PREREGISTRATION.md), revision 7, frozen at `5aab69d`
  (user approval, P-141).
- **Battery:** 138 trials on seeds 30000–30999, never used before the run. 128 are scored with zero tolerance:
  - G2-1: 20 × 60 s holds;
  - G2-2/3: 20 U, 20 U′, 20 U2;
  - G2-4: 20 × U U′ U2 U′ U and 20 × 10 random U-family moves;
  - G2-7: 8 negative cases (two_layer, collision, open_midturn, jam).

  Reported only: G2-6 (8 sensitivity conditions), 2 × offcentre, and G2-8 (throughput).
- **Verdict: PASS, 128/128 scored trials** (`analyze.py`, independent recomputation; one verdict run,
  `verdict_runs/`; §5).

## 2. System under test (summary of pre-registration §1–§2)
- **Cube:** M7 as G1-passed: B1 contact cube, 48 L0 corner–edge magnets, rounded edges R 2.5 mm, gap 0.05 mm, NoSlip
  10, dt 0.5 ms. The core is a free body (1.7 g); nothing holds it but the cubies.
- **Arms:** two xArm7 1305+ from UFACTORY's BSD-3 model. Arm A at the origin; arm B 1.0 m away, yawed 180°. The cube's
  U face points at arm B.
- **Grippers and fingertips:** two Gripper G2 models at 20 N.
  - Arm A holds the D and E layers with one flat 30 × 30 × 4 mm pad per finger (P-97).
  - Arm B turns the U layer with the C1 fingertip, 25 × 14 × 4 mm per finger (P-107).
- **Controllers (classical; they never read cube state):**
  - arm A holds a joint-servo pose;
  - arm B uses a Cartesian impedance with an integral term (only while open);
  - J7 rolls by torque control with a feedforward and a torque budget.
- **Wrist guard:** a modelled 6-axis F/T sensor stops the roll above 1.0 N·m (P-114, P-125).
- **Start:** the cube rests on a drop-away stand, arm A grasps it with gravity on, and the stand lowers clear.

## 3. How the plan was reviewed (`FACT`)
| Round | Verdict | Main findings | Response |
|---|---|---|---|
| 1 | REQUIRES CHANGES (7 required) | roll sign derived from cube state; unjudged start and roll-back phases; integrity gaps | revision 2 (P-122, P-123) |
| 2 | REQUIRES CHANGES (4 required) | U′ torque at untested misalignment; limits unexercised; weak roll test; stray temporary files | pilot 3, revision 3 (P-126, P-127) |
| 3 | REQUIRES CHANGES (2 required) | load-error retry by message; an unfrozen module | revision 4 (P-128, P-129) |
| 4 | REQUIRES CHANGES (1 required) | **the M7 magnets were off in every two-arm trial** | magnets restored and checked per step; pilot 4; revision 5 (P-130, P-131) |
| 5 | ACCEPTABLE AS IS (6 suggested) | G1's magnet-validity rule not judged; jam headroom; step-count hardening; provenance | revision 6, all applied (P-135, P-136) |
| 6 | ACCEPTABLE AS IS (7 suggested) | stale joint margin; "0 skipped" not enforced; verdict file naming | revision 7, all applied (P-137, P-138) |
| 7 | ACCEPTABLE AS IS (3 suggested) | a false statement about `run.py` written by the main session | text corrected; new kill-and-resume smoke PASS (P-139, P-140) |

**The magnet defect (`FACT`, P-130):**
- From D18's first commit to pilot 3, building arm B's IK model uninstalled the magnet callback that had just been
  installed. Every earlier D18/G2 pilot, the gain tuning and two self-checks ran on a magnet-free cube.
- The independent reviewer found it; the main session confirmed it with its own probe.
- Since P-131 every record counts the steps without a magnet-force evaluation, and a trial fails unless the count is 0.
- Pilot 4 repeated every pilot with the magnets on: 144/144 pass.
- G1 is not affected (`FACT`, D20, P-133): G1's scored runner evaluated the magnet force at every step of three probed
  trial kinds and reproduced the committed rehearsal records exactly.

## 4. Pilot evidence before the freeze (`FACT`, pilot 4, magnets on; [`pilot4_magnets/`](pilot4_magnets/README.md))
| Quantity | Pilot max | Limit |
|---|---|---|
| Turn error (244 moves) | 0.31° | 2° |
| First-turn F/T (120 first turns, stop disabled) | 0.373 N·m | 1.0 N·m stop |
| Per-move core rotation | 1.21° | 2° |
| t0 offset | 2.25 mm | 3 mm |
| End misalignment (16 sequences) | 1.05° | 4° |
| Jam stop (6) | 37.3–44.3° | 20–50° |
| two_layer (6) | all detected at 1.10–1.15 N·m | detected |

## 5. Scored results
**Run (`FACT`):**
- `run.py all --jobs 8` at manifest commit `a3e4c98` (frozen code of `5aab69d`).
- One uninterrupted start: 138 records in 11,519 s (3.2 h), no load retries, no interruption.
- Another project's processes were paused by the user for the whole run.
- Freeze-commit checks before the run: 63 tests passed, 0 skipped; self-check 3/3 physics-identical (P-142).

**Verdict (`analyze.py`; `VERDICT.md`, `verdict.json`, `verdict_runs/`): PASS.**
- Integrity: clean (manifest, ledger SHA-256s, start log, frozen code against the manifest commit, artifact SHA-256s,
  record metadata, and the independent recomputation agrees with every stored pass/fail).
- **128 / 128 scored trials pass** (zero tolerance, P-105).
- **Turn trials (G2-2, G2-3, G2-4): 100 / 100, 360 moves, 0 guard stops.** The exact 95 % upper bound on the per-trial
  failure rate is **3.0 %** (Clopper–Pearson, 0/100).
- **Holds (G2-1): 20 / 20**; core slip ≤ 0.16 mm and rotation ≤ 0.34° over 60 s (limits 1 mm, 1°).
- **Negative cases (G2-7), scored: 8 / 8.** two_layer 2/2 detected, collision 2/2 (robot contact), open_midturn 2/2
  detected, jam 2/2 stopped at 43.6° and 40.8° (window 20–50°).

| Quantity (scored turn trials) | Maximum | Limit |
|---|---|---|
| Turn error | 0.414° | 2° |
| Drift (other layers) | 0.307° | 1° |
| Cubie penetration | 0.144 mm | 0.5 mm |
| F/T τ_z, any move | 0.503 N·m | 1.0 N·m stop |
| F/T τ_z, first turn (100) | 0.371 N·m (U′) | 1.0 N·m stop |
| Core slip per move / total | 0.260 / 0.656 mm | 1 / 2 mm |
| Core rotation per move / total | 1.237° / 1.188° | 2° / 2° |
| Roll-back rotation | 0.092° | 1° |
| End misalignment | 1.064° | 4° |
| t0 offset / stand-drop shift | 2.09 / 0.14 mm | 3 / 1 mm |
| Causality gap (force before motion) | min 2 steps (1.0 ms), median 24 | > 0 |
| Drive impulse | min 0.0090 N·m·s | > 0 |
| Magnets | 0 steps without force; steps = sim time / dt in every record; near-pair tilt ≤ 2.32°; 0 perpendicular pairs | 0; equal; ≤ 5°; 0 |

**Reported only:**
- **G2-6 screen (n = 1 each):**
  - turn checks pass for K_P ×0.5 and ×1.5, μ 0.5, grip 10, 30 and 50 N (stress), and rigid pads;
  - **`offset2mm_s30607` fails the pre-t0 offset check (3.23 mm > 3 mm).** Its extra (0, 2, 2) mm offset pushes the
    start past the 3 mm limit, so the check fired as designed; its moves pass.
- **offcentre (5 mm):** 2/2 clean.
- **G2-8:** median real-time factor 0.043 per trial process (8 workers).

**Reading (`INFERENCE`):**
- Every judged quantity stayed at or below 75 % of its limit. The closest were the t0 offset (2.09 of 3 mm) and the
  per-move core rotation (1.24 of 2°), as the pilots predicted (pre-registration §0.4).
- The jam stops (40.8°, 43.6°) stayed inside the window with 6.4° of headroom.
- The causality gap's minimum of 2 steps matches the magnet-free pilots, not pilot 4's 3. It is a judged > 0 check,
  and it passed.

## 6. Limitations (pre-registration §8; to be stated wherever the G2 result is cited)
1. Simulation only; every assumption of §0.6 applies (clearance, turning torque, pad friction and compliance, the F/T
   sensor model, Menagerie joint friction).
2. U-family turns from one grasp only: no regrasp, no other faces, no camera state (G4, G5).
3. The controllers were tuned without the magnets (P-115, P-130) and not re-tuned; pilot 4 shows they work with them.
4. The F/T noise is one seeded stream shared by every trial.
5. Starts within ±1 mm / ±1°. Larger errors were tested only in G2-6 (n = 1 each) and offcentre (reported only).
6. One seed per scored trial; negative cases n = 2 each (detection shown, not a rate).
7. The limits are task tolerances, not tight stabilisation bounds (§8 item 8).
8. The scored run adds no new limitation. Its 3.0 % bound is a per-trial failure rate under the tested start
   distribution only; it says nothing about larger placement errors, other faces or hardware.

## 7. Evidence map: VALIDATION_PLAN G2
| G2 checklist item | Evidence |
|---|---|
| Distinct xArm7 instances with validated tool frames, limits, collision geometry | layout IK (joint-limit margin arm B ≥ 19.1°, arm A 28.9° with the F/T sensor); contact checks in every phase (no judged contact in any scored trial); G2-7 collision 2/2 |
| Approved passive fingertip candidate accurately mounted | P-97, P-107; no non-fingertip robot–cube contact in any scored trial |
| Stable classical stabilisation against a physical rotating layer | G2-1 20/20; core slip ≤ 0.26 mm and rotation ≤ 1.24° per move, totals ≤ 0.66 mm / 1.19° |
| Contact-driven 90° and 180° turns, no unintentional adjacent-layer rotation | G2-2 … G2-4: 100/100 trials, 360 moves; turn error ≤ 0.41°, drift ≤ 0.31°; causality and drive checks pass |
| Collision/force/clearance logs; sensitivity to alignment and friction | per-move logs in every record; G2-6 (7/8 turn-pass, 1 start-offset trip by design); G2-7 8/8 |

## 8. Sign-off (VALIDATION_PLAN sign-off protocol)
**Signed off 2026-11-28 (P-144):**
- `gate_id`: G2 (two-arm manipulation, M7 free core).
- `test_evidence_paths`:
  - `experiments/E8_scored_g2/results/`, `VERDICT.md`, `verdict.json`, `verdict_runs/`, `scored_run_log.txt`;
  - `freeze_check_2026-11-28.log`, `pilot4_magnets/`, `smoke_3_kill_resume/`, `tests/test_scored_g2.py`;
  - reviews 1–7.
- `tolerances_and_trial_counts_pre_registered`: `PHASE_2_G2_PREREGISTRATION.md` revision 7, frozen `5aab69d`.
  138 trials, 128 scored with zero tolerance; the limits are in §4.
- Result: **PASS**, with the §6 limitations as its stated scope.
- `unresolved_risks`:
  - the §6 limitations;
  - open items O-09 (real turning torque), O-10 (squeeze legality, here screened to 50 N), O-12 (G2 CAD licence);
  - the arm B joint-limit margin (19.1°) is the tightest kinematic margin (D22).
- `date`: 2026-11-28. `approver`: the user ("Sign off: PASS").
- `next_authorized_phase`: to be chosen by the user after sign-off.
