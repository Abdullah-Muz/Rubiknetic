# D8-1b model-check history (kept, including failures)

| File | Model | Checks | Outcome |
|---|---|---|---|
| `r1_2026-11-14_before_review.json` | Revision 1: parallel-pair tables, one-sided spline at rho = 0 | Original V3 (reference at the table's own 16x48 quadrature, offsets on the table's rho nodes, no tilt) | All pass. The independent review later found this V3 too weak |
| `r2a_2026-11-14_strengthened_V3_tilt_FAIL.json` (+ `_log.txt`) | Revision 1 with the rho = 0 kink fixed | Strengthened V3 (32x96 reference, off-node offsets, tilts 2/5/10 deg) | **FAIL**: tilted pairs, force error 4.7 / 11 / 23 % at 2 / 5 / 10 deg, torque over tolerance from 2 deg. Survey, V4, V6 and V5 RK4 pass |
| `../d8_1b_checks.json` | Revision 2: tilt-aware near-field expansion | Strengthened V3 plus frame-magnet-tilted and below-tilted cases | Current |
