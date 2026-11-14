# D7 — Contact-driven alignment touch-ups for M2 (UNSCORED diagnostic, 2026-11-13/14)

**Approval:** option B (user: "B"), after smoke tests following Amendment 4. Seeds are diagnostic only (2231, 2300,
2401, 4302, 4401), never the scored range 3000–3999.

**Problem** (`FACT`, smoke tests): M2 cannot align itself. Each relock freezes the current small misalignment.
Turner residuals add up across axes until a piece passes the relock or unlock tolerance, and then long sequences
stall.

**Idea:** before every commanded move, the rig "squares" any face layer whose angular error is above 0.25°. It
grips the layer, rotates it by minus the error and releases it, using ordinary pad contact and M2's normal switch
rule. There are no state edits; this is the Phase 2 robot's job anyway (R2-05).
- The layer error is the median, over the layer's non-centre pieces, of the residual rotation about the face axis.
- At most 2 passes per move.

**Checks:**
- touch-ups never change the logical state;
- every commanded move matches the oracle;
- the switch log stays clean (|ΔKE| per switch is logged).

**Run:** `~/.venvs/rubiknetic/bin/python experiments/D7_touchup/run_touchup.py <a|b>`

Diagnostic environment overrides:
- `CUBIE_TOL`, `UNLOCK_TOL` and `HINGE_TOL` change the switch-rule tolerances (they are NOT the pre-registered
  rule);
- `NO_TOUCHUP=1` gives the baseline without touch-ups.

## Results (`FACT`, `results/*.json`)

Moves matching the oracle / moves commanded:

| Case | Approved 0.5° relock + touch-ups | 1.0° relock + touch-ups | Loose 3°/3°, no touch-ups | Loose 3°/3° + touch-ups | Loose 3°/3°, hinge 1.0°, no touch-ups |
|---|---|---|---|---|---|
| halves_s2231 (6 half turns) | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 |
| sexy6_s2300 (24) | 11/24 | 24/24 | 24/24 | 24/24 | 24/24 |
| sexy6_s4302 (24) | 4/24 | 15/24 | 24/24 | 15/24 | 24/24 |
| scr20inv_s2401 (40) | 4/40 | 4/40 | 14/40 | 4/40 | 11/40 |
| scr20inv_s4401 (40) | 8/40 | 34/40 | 16/40 | 34/40 | 17/40 |

- Every failure is a refused or incomplete turn, usually "layer X still unlocked". No illegal or oracle-mismatched
  state was reported.
- Touch-ups leave **0.14–0.63°** of residual layer error themselves. That is about the size of the 0.5° tolerance
  they are meant to restore.
- In the approved-tolerance failures, the worst misalignment logged at a switch is **0.498–0.4998°** in three of
  the four cases, just below the 0.5° limit. The fourth (scr20inv_s4401) is 0.457°.
- Max |ΔKE| per switch ≤ 1.3e-6 J.

## Interpretation

- `INFERENCE`: touch-ups through the same turner cannot hold the cube inside 0.5°, because they are no more precise
  than the turns they correct. Loosening the tolerances gets further, but the 20-move scramble plus inverse still
  fails in every configuration.
- D8-0 (`../D8_alignment/README.md`) then showed why: most of the accumulated error is piece-specific, so no
  layer-level correction, by touch-up or by magnets, can remove it.
