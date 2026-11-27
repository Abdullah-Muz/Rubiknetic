# G2 pilot 2 (revision 2; UNSCORED; seeds 29300–29353; 2026-11-27)

**Scope:**
- Run with `run.py pilot2 --smoke-dir /home/fwdev/g2pilot2 --jobs 7` at commit `eded7ef` (the revision-2 code). The records
  are copied here (`results/`, `run_log.txt`). 54 trials. Results: DECISION_LOG P-124.
- **The stored pass/fail used the rules then in force:** an F/T stop of 0.8 N·m, and the misalignment-growth rule
  (≤ +1° from t0).
- Both were amended afterwards (P-125): F/T stop 1.0 N·m, absolute end misalignment ≤ 4°.
- So `analyze.py --mode pilot2` reports INVALID with 11 "stored pass False != recomputed True" lines. Those are the 11
  trials that failed only the old growth rule; the current rules pass them. This is expected and kept as recorded.

**Key data (`FACT`):**
- **First-turn F/T, stop disabled:** U′ max 0.674 N·m (p95 0.52), U2 max 0.488.
- **Every check except the growth rule passed in every trial.** Roll-back rotation ≤ 0.043°; total slip ≤ 0.27 mm;
  total rotation ≤ 0.87°.
- **Negatives:** 8/8 handled.
