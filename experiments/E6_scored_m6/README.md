# E6 — Scored runner for the M6 core-magnet cube (UNUSED; the pre-registration lapsed)

**Status: never used for a scored run, and not approved for one.** This folder was built on 2026-11-19, while ER7 was
still running, to prepare for a scored M6 run in case ER7's C52 arm met its feasibility signals. It did not (P-65:
E1-5s snap-back 10 / 20), so [`../PHASE_1_M6_PREREGISTRATION.md`](../PHASE_1_M6_PREREGISTRATION.md) lapsed.
- **No trial has been simulated on an M6 seed** (17000–17999), and no smoke run was made. Only `run.py tables` and
  `run.py all --dry-run` have been executed.
- **Nothing here is a result.** There is no `results/` folder.
- It is kept because the wrapper takes the magnet configuration as a parameter, so a revised core-layout candidate
  could reuse it. Any such use needs a new, approved pre-registration and a review of this code first.

## What it is
- `run.py` loads M5's runner (`../E5_scored_m5/run.py`) unchanged, in module instances of its own, and patches only:
  - the seeds (M5 scored seed + 7000) and the smoke seeds (18000–18099);
  - the magnet installation (`core_layout`, 4×3 mm N52, clearance 0.2 mm, 40 magnets);
  - the tables (M6's N52 table and ER5's N35 table by recorded hash; other strengths derived by exact scaling);
  - the validated regime (tilt 20°, and no near pair perpendicular; P-60);
  - the V3 rule (4×3 mm only, on ER5's real-placement record and M6's linearity record);
  - the E1-7 magnet factors;
  - the mechanism label, folders, start-up check and frozen paths.

  The run procedure (manifest, start log, ledger, atomic records, resume, exceptions, location check) is M5's code.
- `analyze.py` is M5's verdict script with a fixed list of replacements: the runner it loads, the label, the magnet
  checks and the restated disclosures.
- `../../tests/test_scored_m6.py`: 45 tests, none stepping the simulation on an M6 seed. They include a check that
  M6's patches never reach the module instances M5's own code uses.
- Dry run of the full list: 436 trials (204 Option A, 48 E1-7, 184 no-magnet), seeds 17000–17655, 0 refused.

## Where it differs from the lapsed draft (revision 0)
The draft left these open or stated them differently; the code took one choice so that it could be built and tested.
None of these was approved.
| Draft | Code |
|---|---|
| E1-1 also runs D10's instrumented 60 s rest | Not included. A D11-style diagnostic after the run would do the same job without adding to the scored runner |
| E1-7 factors open; a core-clearance factor of 0.1 / 0.2 / 0.3 mm proposed | No clearance factor: only c = 0.2 mm has a V3-turn record |
| E1-7 strength scale 1/1.5 | 0.67, as in M4 and M5 |
| E1-7 grades N35 / N42 / N52 | As drafted, as the `magnet` factor (with `none`) |
| Frozen-path list names the draft file | It names `experiments/PHASE_1_M6_PREREGISTRATION.md` (the draft was renamed) |
