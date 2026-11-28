# G2 report (DRAFT): two xArm7 arms turn a layer of the free-core M7 cube by contact

**Status: DRAFT skeleton, written before the scored run (2026-11-28).** No scored G2 trial has been run. Every
"RESULT" field below is empty until the scored run and its verdict exist. This file is not a frozen path: under the
pre-registration (status block), results and discussion go in a separate report and frozen files are never edited
after the freeze.

**Labels:**
- `FACT`: from a committed record or file.
- `INFERENCE`: the main session's reading.
- `ASSUMPTION`: as in the pre-registration §0.6.

## 1. What was tested
- **Gate:** `docs/VALIDATION_PLAN.md` G2: repeatable, contact-driven layer turns by two robot arms with prescribed
  classical controllers; no learning.
- **Plan:** [`../PHASE_2_G2_PREREGISTRATION.md`](../PHASE_2_G2_PREREGISTRATION.md), revision RESULT_REVISION, in force at
  RESULT_FREEZE_COMMIT (P-RESULT).
- **Battery:** 138 trials on seeds 30000–30999, never used before the run. 128 are scored with zero tolerance:
  - G2-1: 20 × 60 s holds;
  - G2-2/3: 20 U, 20 U′, 20 U2;
  - G2-4: 20 × U U′ U2 U′ U and 20 × 10 random U-family moves;
  - G2-7: 8 negative cases (two_layer, collision, open_midturn, jam).

  Reported only: G2-6 (8 sensitivity conditions), 2 × offcentre, and G2-8 (throughput).
- **Verdict:** RESULT_VERDICT (`analyze.py`, independent recomputation; every verdict run reported, §6).

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
| RESULT_ROUNDS | | | |

**The magnet defect (`FACT`, P-130):**
- From D18's first commit to pilot 3, building arm B's IK model uninstalled the magnet callback that had just been
  installed. Every earlier D18/G2 pilot, the gain tuning and two self-checks ran on a magnet-free cube.
- The independent reviewer found it; the main session confirmed it with its own probe.
- Since P-131 every record counts the steps without a magnet-force evaluation, and a trial fails unless the count is 0.
- Pilot 4 repeated every pilot with the magnets on: 144/144 pass.
- G1 is not affected: RESULT_G1_PROBE.

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
RESULT_SCORED: verdict, per-move and trial maxima, the hold and negative tables, the Clopper–Pearson bound on the
turn-trial failure rate, G2-6 and G2-8, every verdict run, interruptions and resumes.

## 6. Limitations (pre-registration §8; to be stated wherever the G2 result is cited)
1. Simulation only; every assumption of §0.6 applies (clearance, turning torque, pad friction and compliance, the F/T
   sensor model, Menagerie joint friction).
2. U-family turns from one grasp only: no regrasp, no other faces, no camera state (G4, G5).
3. The controllers were tuned without the magnets (P-115, P-130) and not re-tuned; pilot 4 shows they work with them.
4. The F/T noise is one seeded stream shared by every trial.
5. Starts within ±1 mm / ±1°. Larger errors were tested only in G2-6 (n = 1 each) and offcentre (reported only).
6. One seed per scored trial; negative cases n = 2 each (detection shown, not a rate).
7. The limits are task tolerances, not tight stabilisation bounds (§8 item 8).
RESULT_LIMITATIONS: anything the scored run adds.

## 7. Evidence map: VALIDATION_PLAN G2
| G2 checklist item | Evidence |
|---|---|
| Distinct xArm7 instances with validated tool frames, limits, collision geometry | layout IK (P-108); contact checks in every phase; G2-7 collision |
| Approved passive fingertip candidate accurately mounted | P-97, P-107; non-fingertip contact checks |
| Stable classical stabilisation against a physical rotating layer | G2-1 holds; core slip and rotation per move and per trial |
| Contact-driven 90° and 180° turns, no unintentional adjacent-layer rotation | G2-2 … G2-4 |
| Collision/force/clearance logs; sensitivity to alignment and friction | per-move logs; G2-6; G2-7 |

## 8. Sign-off (VALIDATION_PLAN sign-off protocol)
RESULT_SIGNOFF: `gate_id` G2; `date`; `approver`; `test_evidence_paths`; `tolerances_and_trial_counts_pre_registered`;
PASS / NOT PASSED; `unresolved_risks`; `next_authorized_phase`.
