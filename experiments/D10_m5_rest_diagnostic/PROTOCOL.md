# D10 — Unscored diagnostic of the M5 rest failure (PROTOCOL, fixed before any run)

**Status:** approved by the user 2026-11-17 (P-52, "all approved"). This file is committed **before** the first D10
run, so the commit date shows that the question, the arms and the decision rule were fixed in advance.

**Scope (`FACT`):** UNSCORED, reported only. M5's verdict (NOT PASSED, 203 / 204; P-51) stays as it is. No threshold
changes. Nothing is written under `experiments/E5_scored_m5/results*`, and `src/`, E4/E5 `run.py` and `analyze.py` are
not edited. Any simulation setting later chosen from D10 for a new pre-registration must be disclosed as chosen after
M5 failed, and must be tested on new seeds.

## 1. Background (`FACT` unless marked)
- E1-1 `rest_s10001` failed with rest rotation 0.5603° (limit ≤ 0.5°). `rest_s10000` passed with 0.4980°. The other 18
  trials are ≤ 0.344° (`experiments/E5_scored_m5/results/E1-1/`).
- **The metric** (`src/rubiknetic/cube_physics/scored.py:317`, `run_rest_trial`): after the setup misalignment and a
  0.5 s settle, the largest absolute rotation of **any single cubie** about the normal of **any face it belongs to**,
  relative to its pose at t0. It is sampled every 50 steps (25 ms at 0.5 ms) for 10 s. The record keeps only the
  maximum. It does not say which face, which cubie, when, or whether a whole layer moved.
- `INFERENCE`, background only: the E1-7 timestep flip at 0.75 ms was in the sequence trials, not the rest trials.
  At 0.75 ms MuJoCo probably also softens the contacts, because it raises the contact time constant to at least
  2 × timestep (1.5 ms > the 1 ms `solref`). No D10 arm uses a timestep above 0.5 ms, so in every arm the contact time
  constant stays at 1 ms and only the integration step changes.

## 2. Question (fixed)
> In `rest_s10001` (0.560°) and `rest_s10000` (0.498°), what is the peak: one cubie or a whole layer, which face, and
> when? Is it reproduced exactly? Does it shrink when the integration is refined, does it depend on the magnets, and
> is it a settling tail or a continuing creep?

## 3. Runs
Seeds 10001 and 10000 only (both are scored M5 seeds; re-simulating them is the purpose of D10). Setup
(misalignment, grip force) is drawn from the seed exactly as in M5. Each arm changes one setting from the frozen M5
magnet-arm configuration (B1, piece gap 0.05 mm, 48 × 4×2 mm N35, timestep 0.5 ms, Newton, 100 iterations, tolerance
1e-10, implicitfast).

| Arm | Change | Purpose |
|---|---|---|
| A0 | none; the frozen `run_rest_trial` through the M5 runner's `M4.run_trial("rest", …)` | Exact reproduction |
| A0i | none; D10's instrumented copy of the rest loop | Checks that the instrumentation is read-only |
| A1 | timestep 0.25 ms | Integration error |
| A2 | timestep 0.125 ms | Integration error (convergence trend) |
| A3 | solver iterations 400 | Solver convergence |
| A4 | no magnets | Role of the magnet force |
| A5 | rest 60 s instead of 10 s | Settling or creep |

**Logged in every instrumented arm**, every 25 ms of simulated time (the frozen sampling at 0.5 ms; the same simulated
times at the other timesteps):
- each cubie's rotation about each of its face normals;
- each face layer's mean rotation and the spread between its cubies;
- magnet force on each cubie (magnet arms);
- contact count, kinetic energy;
- the largest solver iteration count in the interval, and whether the iteration limit was reached.

**Peak** = the frozen metric: the largest absolute per-cubie rotation over the first 10 s after t0, at the 25 ms
sample times. For A5 the peak over 0–10 s is reported, plus the 60 s time series.

Code: `experiments/D10_m5_rest_diagnostic/d10_rest.py`. It imports the M5 runner read-only (same process patching,
magnet installation and tables as M5) and writes only to `experiments/D10_m5_rest_diagnostic/results/`.
Environment: WSL `~/.venvs/rubiknetic` (MuJoCo 4.0.1, NumPy 2.5.4, SciPy 1.18.1, Python 3.12.3), as M5.

## 4. Gates and decision rule (fixed)
**Reproduction gate:** A0 must equal the recorded values (10001: 0.5602934615568214°; 10000: 0.4979196969239446°) to 1e-6°,
and A0i must equal A0 to 1e-9°. If not, D10 stops and reports that alone (a determinism or instrumentation problem is a
finding in itself).

Let P(arm, seed) be the peak. The rule applies to both seeds together:

1. **Mostly numerical:** P(A2) ≤ 0.5 × P(A0) for both seeds, and P(A1) lies between P(A2) and P(A0) for both seeds.
   **Next step:** an M6 pre-registration with the finer setting and new seeds, stating that the setting was chosen
   after M5 failed.
2. **Model behaviour:** P(A1) and P(A2) are both within ±20 % of P(A0) for both seeds, **or** P(A4) ≤ 0.5 × P(A0) for
   both seeds. **Next step:** an engineering review of the mechanism or of the magnet model (the magnet model if A4
   removes it), not a retuned rerun.
3. **Creep:** in A5, the largest absolute per-cubie rotation in 50–60 s exceeds the 0–10 s peak by ≥ 0.05° in either
   seed. **Next step:** an engineering review, whatever rules 1 and 2 say; a cube that keeps turning at rest is not
   credible.
4. **Anything else is inconclusive:** reported, and the user decides. This includes the seeds disagreeing, and rules 1
   and 2 both holding (for example, rule 1 together with the A4 condition).

A3 is reported only; it is not part of the rule.

**Descriptive labels (fixed, not criteria):** at the peak sample, the peak is *layer-coherent* if the mean rotation
of the peak cubie's layer about that face is ≥ 80 % of the peak, *single-cubie* if it is ≤ 20 %, otherwise *mixed*.

## 5. Limits (fixed)
- Two seeds can explain where the rotation comes from in these two trials. They cannot show how often it happens
  across seeds.
- D10 is unscored. Its results are `FACT` about these simulations and `INFERENCE` about the mechanism; none is a
  `VALIDATED_RESULT` for G1.
- Changes to this protocol after the first run must be recorded as deviations, with the reason, in the D10 summary.
