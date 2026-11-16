# D8-1b model-check history (kept, including failures)

| File | Model | Checks | Outcome |
|---|---|---|---|
| `r1_2026-11-14_before_review.json` | Revision 1: parallel-pair tables, one-sided spline at rho = 0 | Original V3 (reference at the table's own 16x48 quadrature, offsets on the table's rho nodes, no tilt) | All pass. The independent review later found this V3 too weak |
| `r2a_2026-11-14_strengthened_V3_tilt_FAIL.json` (+ `_log.txt`) | Revision 1 with the rho = 0 kink fixed | Strengthened V3 (32x96 reference, off-node offsets, tilts 2/5/10 deg) | **FAIL**: tilted pairs, force error 4.7 / 11 / 23 % at 2 / 5 / 10 deg, torque over tolerance from 2 deg. Survey, V4, V6 and V5 RK4 pass |
| (superseded) | Revision 2 | — | see the rows below |
| `r2b_2026-11-14_tilt_aware_ALL_PASS.json` (+ `_log.txt`) | Revision 2: tilt-aware expansion | Strengthened V3 with tilts 2/5/10° | All pass; validated tilt 5° (10° fails on torque) |
| `../d8_1b_checks.json` (2026-11-15) | Revision 2 (now `src/rubiknetic/cube_physics/magnets.py`) | As r2b plus a 7.5° tilt case (M4 pre-registration §6 item 2) | All pass; **7.5° fails on torque** (3.9e-5 N·m against a tolerance of 2.4e-5; force 0.30 %), so the validated tilt **stays 5°** |
| `../d8_1b_checks_3x1.5_N35_s1.json` (2026-11-15) | Revision 2, E1-7 size 3×1.5 mm N35 | As above | All pass; **validated tilt 7.5°** (10° fails on torque) |
| `../d8_1b_checks_4x1.5_N35_s1.json` (2026-11-15) | Revision 2, E1-7 size 4×1.5 mm N35 | As above | **FAIL: V3 pair force error 5.65 %** (tolerance 5 %; nominal 1.4 %, 3×1.5 3.2 %). Pair torque, tilt to 5°, cube, survey, V4, V6 and V5 RK4 pass; 7.5° fails on torque. The size is not validated, so the E1-7 runner refuses it. Tolerance unchanged. A first run on 2026-11-15 was stopped by memory pressure during V3; this record is the complete rerun |
