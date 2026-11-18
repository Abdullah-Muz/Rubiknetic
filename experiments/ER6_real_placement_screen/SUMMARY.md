# ER6 — Static screen of real-radius core magnets, with a no-intersection sweep: summary (2026-11-17)

Static and unscored (PROTOCOL.md; approved in P-58). It changes no record and selects no mechanism. M5 stays NOT
PASSED. Labels: `FACT`, `INFERENCE`, `PROPOSAL`.

## Provenance (`FACT`)
- The protocol and script were committed in `c5db3e7`, before the run, which recorded a clean tree at that commit.
  Same software as M5 (MuJoCo 4.0.1, NumPy 2.5.4, SciPy 1.18.1, Python 3.12.3, WSL).
- One run, a few minutes long. Output: `results/screen.json`, `results/sweep.json` and `run_log.txt`.
- No deviations from the protocol.
- **Self-checks, all passed:**
  - S1: ER3's "core σ=2 alone" reproduced, relative difference 0.
  - S2: ER5's 4×3 N35 table hash matches.
  - S3: the positive control (ER5's B1 placement) shows an intersection of −1.50 mm on the U turn at −45°, between
    edge `cubie_n0p` and a core magnet.
  - S4: sampled clearance 1.000 mm (coaxial, exact 1.000) and 0.500 mm (side by side, exact 0.500).

## Results (`FACT`)
**Static screen: 9 / 9 variants pass ER3's criteria.**

| Variant (4×3 mm) | Edge spin / slide / cross (mN m/rad) | Corner twist / tangential | Layer (N m/rad) | U-turn peak (N m) | Screen | Derated ÷1.5: layer |
|---|---|---|---|---|---|---|
| N35, c = 0.1 mm | 0 / +420 / +413 | 0 / +411 | +1.92 | 0.131 | PASS | 1.28 |
| N35, c = 0.2 mm | 0 / +377 / +370 | 0 / +369 | +1.72 | 0.121 | PASS | 1.15 |
| N35, c = 0.3 mm | 0 / +339 / +333 | 0 / +331 | +1.55 | 0.112 | PASS | 1.03 |
| N42, c = 0.1 mm | 0 / +501 / +493 | 0 / +490 | +2.29 | 0.157 | PASS | 1.53 |
| N42, c = 0.2 mm | 0 / +450 / +442 | 0 / +440 | +2.06 | 0.145 | PASS | 1.37 |
| N42, c = 0.3 mm | 0 / +404 / +397 | 0 / +395 | +1.85 | 0.134 | PASS | 1.23 |
| N52, c = 0.1 mm | 0 / +627 / +617 | 0 / +614 | +2.87 | 0.197 | PASS | 1.91 |
| N52, c = 0.2 mm | 0 / +563 / +554 | 0 / +551 | +2.58 | 0.181 | PASS | 1.72 |
| N52, c = 0.3 mm | 0 / +507 / +497 | 0 / +495 | +2.31 | 0.168 | PASS | 1.54 |
| *ER3 B1 σ=2 (reference; not buildable)* | *0 / +522 / +490* | *0 / +743* | *+3.01* | *0.285* | | |

- **Every variant passes at margin +0.010.** As in ER3, the limit is the −1 mN m/rad tolerance applied to edge spin
  and corner twist. Those are exactly 0, because coaxial pairs are axisymmetric (displayed values are about −1e-6).
- With every stiffness and torque divided by 1.5 (D8's overstatement caveat), the layer stiffness stays ≥ 1.0 in all
  9 variants. The smallest is N35 at c = 0.3 mm, with 1.03.

**No-intersection sweep: pass at all three clearances.** Six faces, −90° to +90° in 1° steps.

| Clearance c | Minimum magnet clearance | Where | Pairs checked |
|---|---|---|---|
| 0.1 mm | 0.782 mm | corner `cubie_nnp` against a core magnet, U at −45° | 16 344 |
| 0.2 mm | 0.881 mm | same | 16 008 |
| 0.3 mm | 0.979 mm | same | 15 720 |

The minimum is identical on all six faces, as symmetry requires. It is smaller than the gap at home (c + 2 × wall),
because at 45° a corner magnet passes over the edge's core magnet with its axis about 10° off.

## Interpretation (`INFERENCE`)
1. **The real-radius core layout with 4×3 mm magnets passes the static screen and is geometrically buildable** in
   every variant tested. Every tangential piece mode is restoring, and the layer stiffness is ≥ 1.0 N m/rad even when
   derated. This removes the negative single-piece stiffness behind M5's rest slip (ER1), in statics.
2. **It is weaker than ER3's B1 numbers suggested.**
   - Corner tangential stiffness is 369–614 mN m/rad, against 743 in B1. Layer stiffness is 1.5–2.9 N m/rad,
     against 3.0. The detent is lower: 0.11–0.20 N m, against 0.285.
   - ER4's moment-scaling estimate was optimistic. For 4×3 N35 at c = 0.2 mm the edge slide is 377 mN m/rad, 1.35×
     ER4's 4×2 single-pair value (280), not the 2.25× that the moment ratio implies. A longer magnet places its centre
     further from its partner.
3. **Validation coverage:** ER5 validated 4×3 N35 at c = 0.2 mm along the turn. The grades are exact rescalings in
   the ideal model. The 0.1 and 0.3 mm turn trajectories were not separately validated, so c = 0.2 mm is the
   best-covered clearance.
4. **Not shown by a static screen:** whether the stiffness suffices dynamically (rest slip and sequence drift), and
   how the lower detent affects turn completion. That is step (c), the dynamic rehearsal.

## Proposed next step (`PROPOSAL`; the variant choice is the user's, per P-58)
- **M6 implementation of one variant**: core magnets in MagnetSystem, with V5 (energy in MuJoCo), V6 (pose-only
  callback) and the near-pair survey.
- **Recommended variant: N52 at c = 0.2 mm.** It is the stiffest at the clearance ER5 validated along the turn:
  layer 2.58 N m/rad (1.72 derated) and detent 0.18 N m, well under the 0.5 N m limit.
- **Alternative: N35 at c = 0.2 mm**, the exact ER5-validated case, with less stiffness: layer 1.72 N m/rad (1.15
  derated).
