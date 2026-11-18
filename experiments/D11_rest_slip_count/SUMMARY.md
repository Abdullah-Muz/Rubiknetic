# D11 — Rest slip count over the 20 E1-1 seeds: summary (2026-11-17)

UNSCORED, descriptive (PROTOCOL.md; approved in P-53). M5 stays NOT PASSED (P-51).

## Provenance (`FACT`)
- The protocol and scripts were committed in `6262498`, before the run. The run used that commit with no tracked
  changes (`results/environment.json`). M5 software versions; 20 seeds, 60 s each, 10 in parallel. No aborts.
- **Deviation, storage only:** after the run, the 20 raw records were gzip-compressed (`results/*.json.gz`; each
  decompresses byte-identical to the original), and `d11_analyze.py` was changed to read `.json.gz`. The regenerated
  `report.md` is byte-identical to the report produced before compression.

## Reproduction (`FACT`)
All 20 seeds reproduce their recorded M5 E1-1 rest rotation exactly (to within 1e-9°; `report.md`).

## Results (`FACT`)
- **Seeds with a fast slip event:**
  - 0–10 s: 2 / 20 (95 % CI 0.01–0.32);
  - 0–60 s: the same 2. No slip occurs after 10 s in any seed.
- **They are exactly the two seeds at or above 0.4°:**
  - 10001 (0.560°, M5's failing trial);
  - 10000 (0.498°).
- **The other 18 seeds have no fast slip.** Their 0–10 s peaks are 0.046–0.344°, coming from slow motion.
- **Each slip moves a corner and its neighbouring edge on the U–L edge together:**

  | Seed | Time | Pieces | Size (largest change over 200 ms) |
  |---|---|---|---|
  | 10001 | 3.65 s | `nnp` + `n0p` | 0.435°, 0.425° |
  | 10000 | 0.07–0.10 s | `npp` + `n0p` | 0.493°, 0.269° |

- **Magnet torque:** every slipping piece ranks 2nd or 3rd of 20 in net magnet torque at t0 (8.8–11.7 mN m).

## Reading (`INFERENCE`)
In this battery, the M5 rest failure and its near-miss are entirely the fast slip events. Without a slip, rest
rotation stays below 0.35°. Twenty seeds cannot pin down how often slips happen; the 95 % interval is 1–32 % of
trials. The mechanism is analysed in `experiments/ER1_rest_slip_review/REVIEW.md`.
