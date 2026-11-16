# Pass condition, fixed before any result (2026-11-16)

**UNSCORED dress rehearsal of the full M4 battery at a 0.05 mm piece gap.** Approved by the user: "both approved. Commit
and push 1, start 2". This file was written before the run started. Every trial result in this folder comes after it.

- **Configuration:**
  - B1 (radial_preload = 0) with 48 magnets, 4×2 mm N35;
  - piece gap 0.05 mm;
  - the magnet wall stays 0.4 mm, so the face gap is 0.85 mm;
  - everything else as frozen in M4 §1, including the P-26 runner fix.
- **Battery:** every pre-registered M4 experiment, E1-1 to E1-6 plus E1-5s and E1-6t (204 trials), through the
  unmodified M4 runner logic (`rehearsal_gap.py 0.00005 --jobs 4 --shift 2000`).
- **Seeds:** the scored list shifted by +2000 (8000–8999). This range has not been used before.
- **Criteria:** M1's and M4's, unchanged: Option A, every criterion in every trial, with magnet-validity rules 2 and 3.
  The play-criteria proposal is **not** used.
- **Condition:** if every one of the 204 trials passes, a pre-registration for "M5 = B1 + magnets at 0.05 mm" under M1's
  original criteria may be drafted for the user's approval. If any trial fails, the failure is reported in full and
  the options go back to the user. No threshold changes, and no trial is rerun or excluded.
- **Disclosed:**
  - the 0.05 mm gap was chosen after the unscored 0.2 mm, 0.1 mm and 0.05 mm diagnostics (P-25 to P-27);
  - whether a 0.05 mm clearance is realistic for a real cube is unknown.
