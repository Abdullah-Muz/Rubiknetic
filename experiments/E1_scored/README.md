# G1 scored runs — M1 results memo (2026-11-12)

**Verdict (Option A, frozen pre-registration): M1 does NOT pass G1.** E1-4 and E1-6 fail. G1 also requires user
sign-off, which has not been given.

* Source commit for every E1-1…E1-7 record: `cfbc5c6`. E1-8 was run from `bf42dc5`, which only adds `bench.py`;
  the frozen paths are unchanged.
* 214 trials ran. None were rerun, excluded or filtered.
* Raw records are in `results/<experiment>/`. The auto-generated table is in [`results/RESULTS.md`](results/RESULTS.md).
* Claim tags: FACT = read from the records; INFERENCE = my interpretation, not tested.

## Summary

| Exp | Passed | Verdict | What failed |
|---|---|---|---|
| E1-1 rest | 20/20 | PASS | — |
| E1-2 quarter turns | 24/24 | PASS | — |
| E1-3 half turns | 22/22 | PASS | — |
| E1-4 sequences | 38/40 | **FAIL** | Radial pop check only (0.304 and 0.331 mm against 0.3 mm) |
| E1-5 forgiveness | 42/42 | PASS | — (categorical) |
| E1-6 negative controls | 7/20 | **FAIL** | E1-6b 6/6 radial change; E1-6c 7/8 numerical failure, 1/8 passed but physically not credible |
| E1-7 sensitivity | — | 3 flips | μ = 1.0 (both sequences); 0.75 ms timestep (sexy6) |
| E1-8 throughput | — | measured | See below; the measurement has a design flaw |

## Findings

1. **FACT: Oracle agreement held in every E1-2…E1-4 trial (86 trials), including both E1-4 failures.**
   * Worst values: turn error 1.45° (limit 2), non-target drift 0.70° (limit 1), penetration 0.43 mm (limit 0.5).
   * Causality held in every trial.

2. **FACT: The E1-4 failures are narrow exceedances of the pop check.** Both happened in the first move of the
   trial:
   * `scr20inv_s1405`: 0.331 mm on the first U2.
   * `sexy6_s1318`: 0.304 mm on the first R.

   The metric is cumulative ("so far"), so every later move in those trials is also flagged. The next-highest trial
   was 0.298 mm.
   * INFERENCE: this is softness of the +0.2 mm outward retention limit (0.10–0.13 mm past the stop), not a
     cubie pop. A pop would be millimetre-scale.
   * The threshold is frozen and is not loosened (VALIDATION_PLAN threshold policy).

3. **FACT: In E1-6b, all 6 opposed-torque trials failed the approved "radial change ≤ 0.5 mm" criterion.**
   * Measured radial change was 0.82–0.89 mm.
   * The categorical criteria held in all 6: never both layers ≥ 45°, and the state was UNKNOWN (observed invalid)
     at the end.
   * Penetration (reported only) was 0.39–0.69 mm.
   * This failure was flagged as likely when Amendment 1 was approved, and the criterion was deliberately not
     amended.
   * The records do not store the direction of radial motion for this trial type, so whether this is outward
     separation or inward seating cannot be read from the data.

4. **FACT: E1-6c corner twist is the substantive failure.**
   * 7 of 8 corners hit `mjWARN_BADQACC` at t ≈ 1.17–1.56 s. The wrench ramp starts at t = 0.5 s and rises at
     2.5 N·m/s, so failure happened at ≈ 1.7–2.7 N·m, well below the 5 N·m peak.
   * The 8th corner (`ppp`) passes the categorical rule (the observer never reported a false valid state), but the
     physics in that trial is not credible:
     * twist 175°;
     * penetration 12.9 mm;
     * radial travel 5.97 mm, against a slide limited to −1…+0.2 mm;
     * the corner passed 15° of twist at only **0.10 N·m**.
   * INFERENCE: M1's contacts were tuned to scale with the 3.4 g cubie mass (E1-0). Under loads far above operating
     loads they are too soft to block a geometrically locked motion: the solver lets the corner penetrate its
     neighbours instead of resisting. M1 therefore cannot represent a twisted-corner fault or a robust cube under
     abusive loads.

5. **FACT: E1-5 forgiveness is asymmetric in sign.** In measured U misalignment:
   * Positive side: R completes up to +6.2°, and R is blocked from +9.0°.
   * Negative side: R completes up to −10.4°; from −11.8° the R turn is mid-turn or stuck (UNKNOWN, never
     illegal).
   * Measured misalignment differs from commanded by up to ≈5° (for example, −11 commanded gives −6.2 measured),
     so the forgiveness angle should be quoted in measured terms.
   * INFERENCE: only one turning direction benefits from chamfer-guided corner cutting.

6. **FACT: E1-7 fragilities.**
   * μ = 1.0, 6-move: U′ and R′ turn errors of −3.3° and −5.7°, then F stalled mid-turn (observed invalid, so the
     oracle check failed). No *illegal* valid state was reported.
   * μ = 1.0, sexy6: `mjWARN_BADQVEL` at 3.71 s.
   * 0.75 ms timestep, sexy6: penetration above 0.5 mm on 11 moves.
   * Every other setting passed, including grip 10/30/50 N, preload 0.5–3 N, chamfer 1.0–2.0 mm, gap 0.1–0.3 mm,
     iterations 50–200 and misalignment up to 5°.

7. **FACT: E1-8 throughput** (16 logical CPUs, WSL2, measured with no other simulation jobs running):

   | Measure | Result |
   |---|---|
   | Single process during a turn at 0.5 ms | ≈ 620 steps/s (real-time factor 0.31) |
   | Parallel turning, 1 / 4 / 8 / 16 processes (aggregate) | 618 / 1917 / 2147 / 2566 steps/s (real-time factor 0.31 / 0.96 / 1.07 / 1.28) |
   | Contacts at rest | ≈ 192 |

   INFERENCE: scaling saturates after about 4–8 processes.

   **Measurement limitations:**
   * Single-process numbers are noisy. For example, rig_idle raw throughput was 981, 958 and 2159 steps/s at
     0.25, 0.5 and 1 ms.
   * The "audited" figure is taken on the state *after* the timed segment, so it is not like-for-like with "raw".
     It sometimes exceeds raw, so it is not a valid estimate of audit overhead.

## Consequences under the pre-registered rules

* The mechanism decision rule says: "If M1 fails E1-4 or E1-6, M2 becomes the candidate." M1 fails both, so
  **M2 (switched welds) becomes the candidate.** It still has to be built and scored under its own frozen
  pre-registration. A scripted rotation is never a fallback.
* M1's results stay as the comparison and are not discarded.
