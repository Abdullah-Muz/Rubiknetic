# D8 — Self-alignment for the cube model (UNSCORED diagnostics)

**Status (2026-11-14):**
- D8-0 is done.
- P-18 approved D8-1b. Its design ([`D8_1b_DESIGN_PROPOSAL.md`](D8_1b_DESIGN_PROPOSAL.md)) was approved and the
  magnet model has been built and checked (below).
- Stage-1 feasibility trials ran (revision 1). An independent code review then found a modelling artefact and weak
  checks, so the magnet model was fixed, the checks were strengthened, and stage 1 is being re-run as revision 2.
Nothing here is a scored G1 result. No model, switch rule, turner, setup, threshold or pre-registration was changed.

**Context.** M2 stalls on long sequences because each relock freezes the current misalignment, and the frozen
errors add up until a piece exceeds the 0.5° per-piece relock tolerance (D7). Real cubes, and OpenAI's contact
cube (S01: 1.425 mm bevels, turns attempted within ±0.1 rad ≈ 5.7°), self-align through geometry or magnets.
P-16 allows passive forces between specific pieces (such as magnet pairs). D8 asks where such forces would have to act.

## D8-0 — Can forces that act on whole layers remove M2's misalignment?

**Why it matters.** In M2 every piece is welded to the core or to its face centre. A force between pieces can only
rotate a whole unlocked layer about its axis; it cannot move one piece relative to the rest of its layer. Magnets on
M2 can only help if the error is mostly shared by all the pieces of a layer.

**Method** (`d8_0_decompose.py`):
1. Run the five D7 diagnostic sequences on unchanged M2: the scored `TrialM2` setup, the frozen turner, and no
   touch-ups. Seeds 2231, 2300, 2401, 4302 and 4401, never the scored range 3000–3999.
2. After setup and after every move, read each piece's 3-D residual rotation relative to its nearest lattice
   rotation.
3. Fit the six face-layer rotations that best remove it (small-angle least squares: 78 equations, 6 unknowns). The
   **residual** is the error that no combination of layer rotations can remove.

This is an **upper bound** on what layer-level forces can do, because it assumes all six layers are corrected
perfectly and at once. The run modes are:
- `approved`: the frozen SwitchRule.
- `loose`: diagnostic only. Per-piece relock and unlock tolerances are 3.0°, so sequences run longer and the error
  growth can be observed.

Snapshots taken after a stalled move are excluded, because a half-turned layer is not a resting error.

**Positive control** (`FACT`): the setup misalignment is applied per face, so it should be fully removable. At setup
the residual is ≤ 0.001° and 100 % of the error is removable in all five cases. The method recovers layer-level
error correctly.

### Results (`FACT`, `results/*.json`; source commit `1b0a5e4` plus the uncommitted Amendment 4 `src` changes, recorded as `src_dirty`)

| Case | Mode | Moves OK | Max error (last good) | Max residual (last good) | Removable share | First move with residual > 0.5° |
|---|---|---|---|---|---|---|
| halves_s2231 | approved | 3/6 | 0.55° | 0.28° | 84 % | – |
| halves_s2231 | loose | 6/6 | 0.76° | 0.24° | 91 % | – |
| scr20inv_s2401 | approved | 4/40 | 0.75° | 0.38° | 62 % | – |
| scr20inv_s2401 | loose | 14/40 | 1.78° | 0.72° | 81 % | move 6 |
| scr20inv_s4401 | approved | 23/40 | 0.59° | 0.47° | 46 % | – (peak 0.50°) |
| scr20inv_s4401 | loose | 16/40 | 1.31° | 0.61° | 78 % | move 16 |
| sexy6_s2300 | approved | 11/24 | 0.56° | 0.45° | 39 % | – |
| sexy6_s2300 | loose | 24/24 | 1.07° | 1.04° | 24 % | move 7 |
| sexy6_s4302 | approved | 6/24 | 0.59° | 0.47° | 38 % | move 4 |
| sexy6_s4302 | loose | 24/24 | 1.27° | 1.09° | 15 % | move 4 |

Other facts:
- Every run has zero edit-audit violations.
- In every `approved` run, the stall is a refused turn: "layer X still unlocked". The previous layer could not
  relock because a member piece exceeded 0.5°.
- The non-removable residual appears with the **first move** (0.08–0.42°) and keeps growing. In the 24-move `loose`
  runs it reaches about 1.0–1.2°, roughly 0.04° per move. By then only 15–24 % of the error could be removed by
  rotating layers.

### Interpretation

- `INFERENCE`: **layer-level forces cannot keep M2 inside its own tolerance on long sequences.** Even an ideal
  correction of all six layers leaves a piece-specific residual that passes 0.5° within 4–16 moves in four of the
  five `loose` runs. In the `approved` runs it is already 0.45–0.54° when the cube stalls. Magnets on M2 (option
  D8-1a) would delay the stall by a few moves at most.
- `INFERENCE` (mechanism, consistent with the positive control): each piece carries its error with it when its layer
  turns. A tilt picked up about one axis ends up about a different axis after the piece moves. Pieces that share a
  layer arrive with different histories, so their errors differ, and the welds keep each piece's own error. Weld
  compliance under pad load may add to this; D8-0 did not separate the two sources.
- `INFERENCE`: a real cube avoids the problem because each piece is held only by contact and can settle on its own.
  Correcting piece-specific error therefore needs forces that act **on each piece individually**, such as P-16
  magnet pairs or detents, in a model where pieces are not rigidly welded while they settle. That is option D8-1b: a
  bevelled contact cube in the style of S01/M1, with piece-to-piece magnets.
- Limits:
  - small-angle linear model (errors ≤ 2° here);
  - five sequences, one seed each;
  - an upper-bound argument, which rules out D8-1a rather than proving D8-1b will work;
  - the `loose` rule is not the pre-registered rule.

### Reproduce

```bash
# WSL, from the repo root; one case per process
~/.venvs/rubiknetic/bin/python experiments/D8_alignment/d8_0_decompose.py approved sexy6_s2300
~/.venvs/rubiknetic/bin/python experiments/D8_alignment/d8_0_decompose.py loose sexy6_s2300
```

Wall time is 44–343 s per case on 16 threads, with the ten runs in parallel.

## D8-1b — Magnet model built and checked (2026-11-14; no cube trials yet)

**Files:**
- `magnets.py`: the 48-magnet layout and the force law;
- `d8_1b_checks.py`: checks V3–V6, a near-pair survey and an idle speed comparison;
- `results/d8_1b_checks.json`: the results.

The near-field tables are generated caches (`results/tables/*.npz`). They are rebuilt on demand in about 8 minutes
and are not committed.

**Nominal magnets:** 4×2 mm N35, Br 1.19 T, moment 0.0238 A·m², 1.0 mm face gap.

**Results** (`FACT`):

| Check | Result | Criterion |
|---|---|---|
| Near-pair survey, R layer swept 0–90° | no perpendicular pair inside 8 mm; min axial separation 3.0 mm (table starts at 2.1 mm) | pass |
| V3 force, single facing pair (gap 0.5–1.5 mm, offset 0–6 mm) | worst 1.1 % of the aligned normal force | ≤ 5 % |
| V3 force, whole cube (R layer at 0°, 2°, 20°) | worst 0.24 % | ≤ 5 % |
| V3 torque per magnet | pair 3.8e-5 N·m (tolerance 4.8e-5); cube ≤ 1.2e-5 N·m (tolerance 2e-5) | pass |
| V4 net force and net angular momentum (20 random states) | ≤ 9e-17 relative | ≈ 0 |
| V5 energy, rigid R layer released 3° off square, RK4 | drift 0.56 % of the 2.07 mJ exchanged | ≤ 1 % |
| V6 depends only on poses (ctrl, time, qvel and act changed) | identical forces; installed callback matches the direct call to 2e-18 | pass |

**Corrections made while building**, all before any trial; nothing was loosened to make a check pass:
1. **V6 initially failed because of a test bug.** `mj_applyFT` needs the position-stage centre-of-mass quantities, and
   the test had run only `mj_kinematics`.
2. **V5 was redesigned twice.** With contacts off, pieces that move independently and are held only by attracting
   magnets have no stable equilibrium (Earnshaw's theorem), so the free-ball and per-piece-hinge versions collapsed.
   The final test turns the R layer as one rigid body. That is the motion the detent is for, and it is a well-posed
   conservation test.
3. **Per-magnet torques were wrong.** The first full run showed errors of about 1e-3 N·m: the total was right, but it
   was split wrongly between the two magnets of a facing pair. The force-only V3 criterion missed this. Exact
   charge-model torques for facing pairs are now tabulated, the error is about 6e-6 N·m, and a torque criterion was
   added to V3.
4. **A far-field taper and neighbour list were added** for speed. Pair forces fall smoothly to zero between 20 and
   25 mm, where they are about 0.06 % of the facing force. A Verlet list is used, so the force law stays exact and
   conservative.

**Open points, disclosed** (revision 1; see revision 2 below for what changed):
- **The operational integrator adds energy.** With `implicitfast` at 0.5 ms (the magnet force is explicit) the same
  undamped release gains up to +0.16 mJ in 0.5 s. That is 7.6 % of the exchanged energy, and the gain is
  **positive**.
  - `INFERENCE`: in trials this is dwarfed by joint damping alone. The layer's natural frequency is about 280 rad/s,
    so at a 3° amplitude the damping dissipates of the order of 0.05 W, against an injected ~2e-4 W.
  - T6 will measure magnet work per turn during real trials.
  - **Superseded (revision 2):** this is a bounded oscillation, not a steady gain (below).
- **Speed was not measured fairly.** It was 168 steps/s with magnets and 1,476 without, while unrelated jobs held the
  load average at about 13 on 16 threads. It must be re-measured on an idle machine. The pre-declared signal is
  ≥ 300 steps/s single-process; if it is missed, the force law would need to move into a C plugin.
- **Tilted pairs:** the parallel-pair tables stand in for slightly tilted pairs, so energy is conserved only to first
  order in tilt. **Superseded (revision 2):** this approximation failed the strengthened V3 and was replaced.

## D8-1b revision 2 — Independent review, model fix and stronger checks (2026-11-14)

**Why.** After stage 1 (revision 1), an independent code review (a subagent under P-20, given the code and not the
conclusions) checked the magnet model and the harness. The main session verified each finding against the code
before acting. The review found no sign or unit error and no P-16 violation. It did find the following, all
`FACT` (checked):

| # | Finding | Consequence | Action |
|---|---|---|---|
| 1 | The near-field spline was fitted on rho ≥ 0 only, leaving a nonzero slope at exact alignment: a spurious pull of about 15 mN per pair toward alignment (measured) | Revision-1 snap and alignment results are slightly flattered by an artefact | Fit on the grid mirrored to negative rho: slope at alignment now exactly 0; values elsewhere change < 1 % |
| 2 | Corner-twist trials tilt magnet pairs about 30°, far outside any validated range | Revision-1 T5 magnet results are not magnet physics | Largest near-pair tilt is now logged per trial; trials beyond the validated tilt are flagged |
| 3 | V3 was weak: its reference used the table's own quadrature, its offsets fell on the table's nodes, and no tilted pair was tested | V3's 1.1 % was not independent evidence | V3 strengthened (below) |
| 4 | Magnet stats accumulated over the whole process, not per trial | Revision-1 stats can't be traced to trials | Reset per trial |
| 5 | Each ±δ pair of T1/T2 used a different seed (different setup offset, grip and speed) | Direction comparisons confounded | One seed per ± pair |
| 6 | T1 turns U with the rig and stops at ±8°, while §6 says "through the logged setup, ±1…±10°" | Undisclosed deviation | Disclosed in the harness; kept (the rig offset is contact-driven) |
| 7 | S3 ignores ±1/±2°, and its 0.5° line was chosen when the analysis was written, not pre-declared | A near-square dead-band was invisible | S3 kept as pre-declared; the dead-band and the threshold choice are reported |
| 8 | S4 gated only V4 and V5 | Weak gate | S4 now requires every check (`all_pass`) |
| 9 | V4 passes by construction for near pairs (the partner torque is set by balance) | V4 cannot catch a wrong torque split | Documented: V3 tests the split |

**The strengthened V3 failed** on the revision-1 force law (kept in `results/checks_history/`):
- tilted pairs: force error 4.7 / 11 / 23 % at 2 / 5 / 10° tilt (criterion 5 %);
- torque over tolerance from 2° on;
- parallel pairs and the whole-cube checks still passed.

Pieces in B1 sit 1–2° off square, so the magnet pairs in real trials are tilted that much. No criterion was loosened.

**Fix: tilt-aware near-field correction** (`near_field_tables`, `pair_forces`).
- The correction is now a second-order expansion in the tilt between the two magnets:
  `C = C0(ρ,|z|) + sign(z)·A·v + B·(1−μ²)/2 + D·v²/2`, where `v = u·lat` and `μ = u·a`.
- The coefficients come from central differences (±1.5°) of the exact charge-model energy, at the table's quadrature,
  with magnet 2's quadrature pattern rotated by the tilt.
- Every force and torque is the gradient of this single rotation-invariant energy, so energy and angular momentum
  are conserved at any tilt.

Internal consistency (`FACT`):
- C0 equals the revision-1 parallel table exactly.
- The in-plane slope matches the independent revision-1 exact-torque table to 0.05 %.
- Forces and torques equal minus the energy's gradient to 2e-10 and 1e-8 (relative; finite-difference check on 12
  random tilted pairs).

**Revised checks** (`results/d8_1b_checks.json`, `FACT`):

| Check | Result | Criterion |
|---|---|---|
| V3 parallel pair: 32×96 reference (table 16×48), gaps 0.5–1.5 mm in 5 steps, offsets 0–6 mm in 0.37 mm steps | force 1.4 %; torque 3.6e-5 N·m (tolerance 4.8e-5) | ≤ 5 %; torque tolerance |
| V3 tilted pairs, 1.0 mm gap, three cases (upper magnet tilted, frame magnet tilted, tilted magnet below) | force 0.15 % / 0.20 % / 0.59 % and torque 2.3e-6 / 1.7e-5 / **7.0e-5** N·m at 2 / 5 / 10° (tolerance 2.4e-5) | must pass to 5° |
| **Validated tilt range** | **5°** (10° fails on torque) | trials beyond it are flagged |
| V3 whole cube (R at 0°, 2°, 20°; near pairs at 24×72) | ≤ 0.24 %; torque ≤ 1.2e-5 N·m | ≤ 5 %; 2e-5 N·m |
| V4, V5 RK4, V6, survey | pass (V5 drift 0.045 %) | as before |
| V5 implicitfast, 5 s at 0.5 ms and 0.25 ms (diagnostic) | peak error 0.157 mJ, unchanged from 0.5 s to 5 s; mean error 8.8 µJ in the first half, 9.1 µJ in the second; halving dt halves it (7.6 % → 3.7 %) | — |
| Throughput (rig model; load average about 5 on 16 threads, not idle) | 710 steps/s with magnets, 4,759 without | ≥ 300 |

`INFERENCE`: the implicitfast energy error is the bounded first-order oscillation of a symplectic-Euler step (review
finding 7), not a steady gain. The revision-1 "positive gain" description is withdrawn.

**Stage 1 revision 2:**
- Results go to `results/stage1_r2/`; the revision-1 results in `results/stage1/` are kept unchanged and annotated
  (`analyze_stage1.py stage1`).
- B2/B2E were not re-run. Revision 1 already rules them out on non-magnet grounds: opposed-torque radial change
  0.67–0.90 mm against 0.5 mm, and numerical failure in corner twist in both arms, which also hit B2E without magnets.

### Stage 1 revision 2 results: B1 (`FACT`, `results/stage1_r2/SUMMARY.md`)
Run 2026-11-14: magnet model revision 2, all checks passing, paired seeds, per-trial stats. Both arms ran on the same
harness and seeds; the load average was about 5–6 on 16 threads, which is not idle.

| Signal (pre-declared, §6) | B1 + magnets | B1, no magnets |
|---|---|---|
| S1: every sequence matches the oracle | **yes**, 140/140 moves | no: scr20inv_b jams at move 4 (60°) |
| S2: no error build-up (slope < 0.005°/move over 40 moves) | **yes** (−0.0023 and −0.0031) | no (one run failed; the other +0.0028) |
| S3: snaps back from ≥ 3° in both directions (≤ 0.5° after 1 s) | **yes**: 0.05–0.48° from ±3, ±5 and ±8° | no: stays where left |
| S4: all model checks pass | yes | yes |
| S5: ≥ 300 steps/s single process (not idle; 3 processes in parallel) | yes, median 328 | yes, 981 |

Further results:
- **Near-square dead-band** (reported, not a signal): up to 0.59° left after release from ±1/±2°, against up to 2.0°
  without magnets.
- **Forgiveness:** completes at every offset from ±2 to ±12°, never illegal. Without magnets, +12° is blocked.
- **Turn error:** 0.23–0.43° with magnets, against 1.05–2.27° without.
- **Worst-piece misalignment:** 1.1–2.3° throughout, with no build-up. This is B1's per-piece play.
- **Penetration:** 0.28–0.29 mm.
- **Peak turner torque:** 0.32–0.72 N·m, against 1.00 N·m (the limit) without magnets.
- **Opposed torque:** passes at 1 and 2 N·m. At 2 N·m neither layer moves.
- **Corner twist:** categorical pass, 39–41° at 5 N·m, about 1.0 mm penetration. Unchanged from revision 1.
- **Magnet validity:**
  - In every operational trial (snap, forgiveness, sequences) the largest near-pair tilt was **4.80°**
    (scr20inv_b). That is inside the validated 5° range, with little margin.
  - The peak magnet force was 1.89 N, with 0 near-perpendicular and 0 clamped pairs.
  - Three abuse trials go beyond 5° and are flagged as outside the validated range: opposed at 2 N·m (7.3°) and both
    corner twists (23°).
- **Integrity:** 0 edit-audit violations and 0 numerical failures in either arm.

`INFERENCE`:
- The revision-1 conclusion survives the artefact fix and the stronger checks. B1 + magnets is the first configuration
  to meet every behavioural feasibility signal.
- This is still **not G1**. It would need a pre-registration, and corner twist (about 40° at 5 N·m, with no
  real-cube data to calibrate against; see the literature search) remains the open question for that.
- The 4.80° operational tilt is close to the validated limit, so a scored run should either extend V3 to cover a
  margin (for example 7.5°) or treat the limit as a run-time abort condition.

### Throughput, single process (`FACT`, 2026-11-15, `results/throughput_2026-11-15/`)
- Machine: AMD Ryzen 7 250, 16 threads. Load average 4.2 at the start and 10.0 at the end, from unrelated jobs, so not
  idle.
- **B1 + magnets: 381 steps/s in a real 24-move trial** (seq_sexy6_a, full harness), against 1,082 without magnets.
  The stage-1 S5 signal (≥ 300) is met single-process.
- The bare cube plus rig benchmark, 3 repeats: 495–594 steps/s with magnets, 2,678–5,143 without.
- The Python force law costs about 1.4 ms per step. A C plugin isn't needed for S5, but would recover roughly 2.8× for
  Phase 2 training throughput.
