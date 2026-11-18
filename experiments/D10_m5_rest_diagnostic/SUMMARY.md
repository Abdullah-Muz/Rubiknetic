# D10 — Unscored diagnostic of the M5 rest failure: summary (2026-11-17)

**Outcome under the fixed rule (PROTOCOL.md §4): INCONCLUSIVE (rule 4). The user decides the next step.**
UNSCORED, reported only. M5 stays NOT PASSED, 203 / 204 (P-51). No threshold was changed.

## Provenance (`FACT`)
- The protocol was committed in `2e7377a` and the script in `76e69cf`, both before the first run. The run used
  commit `76e69cf` with no tracked changes (`results/environment.json`).
- WSL `~/.venvs/rubiknetic`: MuJoCo 4.0.1, NumPy 2.5.4, SciPy 1.18.1, Python 3.12.3. These are the M5 versions.
- 14 jobs (7 arms × seeds 10001 and 10000), 7 in parallel. No aborts, no numerical failures, and no deviations from
  the protocol.
- Files:
  - `run_log.txt`;
  - `report.md`: the rule, applied mechanically by `d10_analyze.py`;
  - `describe.txt`: the descriptive numbers below, from `d10_describe.py`;
  - `results/*.json`: full time series.

## Reproduction gate: passed (`FACT`)
A0 (the frozen trial through the M5 runner) reproduces both recorded values exactly: 0.5602934615568214° and
0.4979196969239446°. The difference is 0. A0i (the instrumented copy) equals A0 exactly, so the logging did not
change the physics.

## Results (`FACT`)

| Arm | s10001 peak ° (× A0) | s10000 peak ° (× A0) |
|---|---|---|
| A0 frozen | 0.560 (1.00) | 0.498 (1.00) |
| A1 timestep 0.25 ms | 0.508 (0.91) | 0.550 (1.11) |
| A2 timestep 0.125 ms | 0.125 (0.22) | **0.567 (1.14)** |
| A3 iterations 400 | 0.560 (1.00, identical) | 0.498 (1.00, identical) |
| A4 no magnets | 0.324 (0.58) | 0.229 (0.46) |
| A5 60 s (peak in 0–10 s) | 0.560 | 0.498 |

**Rules:**
- **Rule 1 (mostly numerical): not met.** A2 fell to 0.22 × A0 for s10001 but rose to 1.14 × A0 for s10000.
- **Rule 2 (model behaviour): not met.**
  - Timestep: A1 and A2 are not both within ±20 % (s10001 A2 is 0.22 × A0).
  - Magnets: A4 is not ≤ 0.5 × A0 for both seeds (s10001 is 0.58 × A0).
- **Rule 3 (creep): not met.** In A5 the largest rotation in 50–60 s is about 0.10° below the 0–10 s peak for both
  seeds.

The seeds disagree, so under the fixed rule the outcome is inconclusive.

## What the time series show (`FACT`, descriptive; not part of the rule)
1. **The peak is one corner cubie, not a layer.** In every magnet-arm run with an event, the peak is a single U-layer
   corner: `cubie_nnp` for s10001 and `cubie_npp` for s10000. The U layer's mean rotation at the peak is only
   −0.08° to +0.11°, with a spread of 0.53–0.66° between its cubies. The fixed labels give "single-cubie" in every
   such case except A1 s10001, which is "mixed".
2. **The rotation arrives as one fast event.**
   - The corner turns about 0.5° within 75–150 ms (4–6 samples).
   - Kinetic energy jumps from about 1e-12 J to 1e-7–2e-6 J during the event.
   - Afterwards the corner relaxes slowly back. For s10001: 0.560° at 4 s, 0.523° at 10 s, 0.460° at 60 s.
3. **The event's timing varies a lot; its size does not.**
   - Events occur at:

     | Run | Event time |
     |---|---|
     | A0 s10000 | 0.2 s |
     | A1 s10000 | 1.5 s |
     | A1 s10001 | 2.3 s |
     | A2 s10000 | 3.6 s |
     | A0 s10001 | 3.8 s |

   - A2 s10001 has no event within 10 s. Its largest rotation, a different U corner (`cubie_n0p`), is still rising at
     10 s (0.049° at 8 s, 0.125° at 10 s).
   - When an event occurs, its size is 0.50–0.57°.
4. **Solver convergence is not involved.** The Newton solver needed at most 15 iterations in any step of any arm,
   against a limit of 100. A3 (limit 400) is bit-identical to A0.
5. **Magnets:**
   - At rest, every corner carries a net magnet force of 2.3–2.9 N; the median over all magnet bodies is about 0.3 N.
   - The corner that slips has one of the three largest net magnet torques: 8.8–13 mN m, against a median of
     1.5–2.1 mN m.
   - Without magnets (A4) there is no fast event. Instead, an edge or corner on a different face (R or F) drifts
     slowly: 0.23–0.32° by 10 s, still rising in s10000, and the cube comes to rest (KE about 1e-16 J).

## Interpretation (`INFERENCE`; not validated)
- The M5 rest failure looks like a **stick-slip event**: a single corner, under a sustained magnet torque, is held by
  friction and then slips about 0.5° in its slot. The whole layer does not move. When the event happens depends
  sensitively on numerical details: timestep and seed change it, the iteration count does not. Its size depends
  much less on them.
- So refining the timestep does not remove the failure. At 0.125 ms, s10000 gives 0.567°, which is worse than in
  M5. A new pre-registration that only uses a finer timestep would be expected to fail rest trials again.
- Without magnets, the rotation at rest is smaller in 10 s but slow and still rising. So "no magnets" is not a clean
  fix either; E1-6n already showed that long sequences fail without magnets.
- Two seeds can explain the mechanism in these trials. They cannot show how often slip events occur across seeds,
  or whether a slip can exceed 0.57°.

## Proposal for the user's decision (`PROPOSAL`; nothing applied)
D10 does not support M6 with a finer timestep. Recommended: an **engineering review** of the corner-slip mechanism.
Its questions:
- (a) What corner rotation does the 0.05 mm play and the chamfer geometry permit, and is a 0.5° slip physically
  credible for the intended cube?
- (b) Why does a corner at rest carry about 10 mN m of net magnet torque? Is it a real property of the magnet
  layout, or an artefact of the magnet force model?
- (c) What would remove the slip mechanically, for example a magnet layout with no net corner torque at the aligned
  pose?

A cheap follow-up, also unscored and fixed in advance, could count slip events across all 20 rest seeds at the frozen
settings. Any new criterion or setting goes through a new pre-registration with new seeds, disclosed as chosen after
M5 failed.
