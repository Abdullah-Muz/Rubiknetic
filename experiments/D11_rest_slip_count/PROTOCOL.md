# D11 — How often do rest slip events occur? (PROTOCOL, fixed before any run)

**Status:** approved in P-53 (user: "all approved", 2026-11-17; the interpretation is recorded there). The definitions
below were written by the main session and committed **before** the first D11 run. UNSCORED and descriptive only:
there is no decision rule, and nothing here can change M5's verdict (NOT PASSED, P-51) or any threshold.

## Question (fixed)
> At the frozen M5 settings, in how many of the 20 E1-1 rest seeds (10000–10019) does a fast single-cubie slip event,
> as seen in D10, occur within 10 s and within 60 s? How large are the events, when do they happen, which cubies slip,
> and how do they rank in net magnet torque at rest?

## Runs
- Seeds 10000–10019: the M5 E1-1 seeds. Setup is drawn from the seed, as in M5.
- One arm only: the frozen M5 magnet-arm settings, with the rest extended to 60 s. This is D10's arm A5, using D10's
  instrumented loop (`experiments/D10_m5_rest_diagnostic/d10_rest.py`, imported read-only). D10 showed that loop is
  bit-identical to the frozen trial.
- Logging as in D10: every 25 ms of simulated time.
- Output only to `experiments/D11_rest_slip_count/results/`.

## Reproduction check (fixed)
For each seed, the 0–10 s peak must equal that seed's recorded M5 `rest_rotation_deg` to within 1e-9°. A seed that
fails is reported as such, and its slip data are still shown but flagged.

## Definitions (fixed)
- **Signal:** for every non-centre cubie and every face layer it belongs to at t0, its signed rotation about that face
  normal (the M5 metric, before taking the absolute value).
- **Fast slip event:** a change of at least 0.2° in that signal across 8 consecutive samples (200 ms).
  - Windows that overlap or touch, for the same cubie, are merged into one event, whichever face they come from.
  - Separation, from D10: slip events changed by about 0.5° in 75–150 ms. Slow drift without magnets changed by
    ≤ 0.03° per 200 ms.
- **Event size:** the largest |change over 200 ms| inside the merged event (a lower bound on the jump), together with
  the cubie's largest |rotation| over the whole run.
- **Reported per seed:**
  - the 0–10 s peak (the M5 metric) and its cubie;
  - the number of events in 0–10 s and in 10–60 s;
  - each event's time, cubie, corner or edge, size, and the cubie's net magnet torque at t0 with its rank among the
    20 magnet bodies;
  - whether the seed's 0–10 s peak comes from an event cubie.
- **Summary:**
  - the number of seeds with at least one event in 0–10 s and in 0–60 s;
  - the event-size distribution;
  - the count of slipping cubies by type and by magnet-torque rank;
  - the 0–10 s peaks of seeds with and without events.

## Limits (fixed)
- One arm and 20 seeds. Frequencies are estimates with wide uncertainty. Clopper–Pearson 95 % intervals are reported.
- The 0.2° / 200 ms threshold is a descriptive choice made after D10. It is not a criterion.
