# M6 — Core-magnet implementation checks (SUMMARY)

**Status:** unscored model checks under [`PROTOCOL.md`](PROTOCOL.md) (P-59; protocol and script committed in `911e45b`
before the run). One run, 2026-11-18, WSL2, MuJoCo 4.0.1; wall time 752 s, of which 637 s was the N52 table build.
Raw record: `results/m6_checks.json` and `run_log.txt`. Nothing here selects a mechanism or changes M5, which stays
NOT PASSED.

## Fixed verdict
**M6 CHECKS: NOT ALL PASS.** (Amended by P-60, 2026-11-18: under the amended survey criterion, M6 passes; this fixed verdict stays on record.) S1, S2, V4, V5 (RK4) and V6 pass. **The near-pair survey fails** on its "no clamped |z|"
criterion. Per the protocol, nothing is used dynamically.

## Results (`VALIDATED_RESULT` for the checks as defined; `FACT` for the numbers)

| Check | Result | Criterion | Pass |
|---|---|---|---|
| S1, table scaling | ER5 4×3 N35 SHA-256 matches the record. N52 table = N35 × 1.4950 (= (1.455/1.19)²), max rel. difference 8.3e-16 | ≤ 1e-9 | yes |
| S2, ER6 reproduction | Layer stiffness on all six faces: max rel. difference 4.0e-13. U-turn profile: 2.9e-13 of the peak. Peak 0.181 N m | ≤ 1e-6 | yes |
| V4, Newton / angular momentum | 1.5e-17 / 1.0e-17 | < 1e-9 | yes |
| V5, RK4, 0.5 ms, 0.5 s | Drift 2.6 µJ against 3.33 mJ exchanged: **0.079 %** | ≤ 1 % | yes |
| V6, pose-only callback | Change from ctrl/time/qvel/act: exactly 0. Installed vs direct: 1.7e-18. Magnet qfrc up to 0.012 | identical; ≤ 1e-12; non-zero | yes |
| Near-pair survey, 6 faces × −90…+90° | 0 perpendicular pairs; 0 piece–piece pairs; **576 clamped-z pair-poses**, min \|z\| 2.74 mm against the table's 3.1 mm | 0 / 0 / 0 | **no** |

**Reported only:**
- **Survey:** 16–24 near pairs per pose. The largest near tilt was 18.05°, the same as ER5's real-placement
  trajectories (18–20°).
- **V5 with implicitfast**, the operational integrator: drift 10.0 % of the exchanged energy at 0.5 ms (0.5 s and 5 s
  identical) and 4.8 % at 0.25 ms. The mean drift is constant over 5 s (2.6e-5 J in both halves), so the drift is
  bounded and roughly halves with dt. That is an integrator oscillation, not a growing energy gain. D8's 48-magnet
  layout showed the same pattern: 7.6 % and 3.7 %.
- **Throughput,** rig model, idle, single process: 3854 steps/s without magnets and 606 steps/s with the core
  layout.
- **V5 stats:** see the JSON.

## Diagnostic of the survey failure (post-run, `FACT`; `clamp_diagnostic.py`, `results/clamp_diagnostic.txt`)
- **Where it happens.** U turn: 96 clamped pair-poses; × 6 symmetric faces = 576.
  - Every one is a turning piece magnet passing the core magnet of a neighbouring piece,
    at turn angles up to ±70°.
  - Centre distance r is 6.9–7.97 mm, lateral offset ρ is 6.2–7.4 mm, tilt is 15–18°, and |z| is 2.74–3.10 mm.
- **How much it matters.** These pairs lie in the near-field cutoff taper (r1 = 5 mm to r2 = 8 mm). There the
  correction's weight w(r) is at most 0.26, and it falls to 0 at 8 mm.
- **What clamping does.** The force law evaluates the correction at |z| = 3.1 mm and zeroes its z-derivative. The
  energy therefore stays a single consistent function: V4 and V5 are unaffected. But in that region the correction is
  extrapolated flat, not tabulated.
- **ER5 already compared this regime with the fine model.** ER5's V3-turn moved one U-layer edge magnet and one corner
  magnet through 0–90° against all 20 core magnets, in this same placement and clearance. It reported near pairs at
  the same angles and the same tilts (18.051° at 65°, edge and corner). Its force errors there were 0.5–0.8 % of the
  facing-pair force and its torque errors were within tolerance; for example, at 65° the edge torque error was 6e-6 N m
  against a tolerance of 5.0e-5 N m. N52 is an exact rescaling (S1).
  - **`INFERENCE`:** the clamped pairs are inside the accuracy ER5 validated. The survey's "no clamped |z|" criterion,
    carried over from D8 as a proxy for "inside the validated regime", is stricter than the accuracy evidence.
  - This does not change the fixed verdict.

## Interpretation (`INFERENCE`)
1. The implementation is correct as code. It reproduces ER6 to 1e-13, conserves momentum and energy (RK4), and reads
   only poses.
2. The only failure is a proxy criterion. The quantity it guards, force-law accuracy, was measured directly by ER5
   for the same pairs and passed.
3. implicitfast at 0.5 ms has a bounded 10 % energy oscillation on a 3° rigid-layer release, as D8's layout did.
   This matters for the dynamic rehearsal: the operational integrator or timestep may need to be chosen with it in
   mind.

## Proposed next step (`PROPOSAL`; needs user approval)
- **(a) Recommended.** Record a criterion amendment, P-60. A clamped near pair is acceptable when its pose lies on a
  trajectory where ER5's V3-turn passed against the fine model. Here that is every piece-to-core pair during a face
  turn in this placement, at this clearance and at this size; grades follow by exact scaling.
  - With that amendment, M6 would count as passing. The original verdict stays on record as NOT ALL PASS.
  - Then the dynamic rehearsal (step (c)) gets its own protocol, for your approval.
- **(b)** Change the force law so that these pairs are tabulated. For example, give the table a non-rectangular grid
  that reaches |z| ≈ 2.7 mm at ρ ≥ 6 mm; the overlap region at small ρ must stay excluded. Then rerun ER5's V3 and
  M6. This is more work, and it is a force-law revision, which ER5 and P-58 set aside.
- **(c)** Treat M6 as failed and return to layout design.
