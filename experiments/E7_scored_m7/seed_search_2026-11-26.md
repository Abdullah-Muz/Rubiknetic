# M7 final seed search (pre-registration §6.4 and §7 item 3; 2026-11-26, before the freeze)

**Method.** A read-only script was run with `python -I` from the session scratchpad, outside the repository:
- it walks every file under `C:\dev\Rubiknetic`, tracked, untracked or ignored, except `.git`, virtual
  environments, `__pycache__`, `node_modules` and `.pytest_cache`;
- it decompresses `.gz` files;
- it searches for a record use of a seed in 17000–17999, written either as `"seed": 17xxx` or as the trial-ID suffix
  `_s17xxx`.

**Result (`FACT`).** 6,803 files (3.71 GB) were scanned. 5 files match, and none is a simulation record:

| File | Matches | What it is |
|---|---|---|
| `experiments/PHASE_1_M7_PREREGISTRATION.md` | `_s17000` | Text naming an M7 trial ID |
| `experiments/M7_PREREGISTRATION_REVIEW1_2026-11-25.md` | `_s17000`, `_s17100`, `_s17700` | Review text naming M7 trial IDs |
| `experiments/ER9_anchored_core_layouts/tests/test_er9g_run.py` | `"seed": 17001` | ER9's seed-guard test, which asserts the seed is **refused** |
| `tests/test_scored_m6.py` | `_s17001`, `_s17100`, … | M6 tests: synthetic keys; the trial is stubbed before any step (P-66) |
| `tests/test_scored_m7.py` | `"seed": 17100`, `_s17000`, … | M7 tests: synthetic keys and stand-in trials, which never step the simulation. The synthetic full-verdict runs write stand-in records to pytest temporary folders outside the repository |

**Conclusion.** No simulation has been run on seeds 17000–17999. The scored seed block is unused.
