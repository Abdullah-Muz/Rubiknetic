# Scored M2 run 1: archived as INVALID as a test of the pre-registration (2026-11-13)

**Status:** kept in full and reported. Not deleted, and none of its trials will be re-run under these seeds.

**What it is:** a complete, valid record of the code at commit `1b0a5e4`, seeds 2000–2999: 194 trials of E1-1 to
E1-6, plus E1-7. Auto-generated summary: `RESULTS.md`.

| Experiment | Result |
|---|---|
| E1-1 | 20/20 |
| E1-2 | 24/24 |
| E1-3 | 21/22 |
| E1-4 | **2/40** |
| E1-5 switches | 1,416/1,416 clean |
| E1-5b | 42/42 |
| E1-6 | 26/26 (all 8 corner twists pass) |

**Why it is not a valid test of the approved pre-registration** (FACT):

* Amendment 1 (A2) changed only the unlock **request** rule. It stated that "all other unlock, relock and refusal
  conditions in section 1 are unchanged". Section 1 relocks on the face's own **pad torque < 0.02 N·m**.
* The committed harness (`switching.py`, relock check) instead used the face's **boundary shear from ALL gripper
  contacts**.
* Combined with a spurious re-unlock when the pads release (a known transient), this produced a deadlock in 38 of the
  40 E1-4 trials:
  1. the layer re-unlocks;
  2. the next face's pads add shear to it, so it cannot relock;
  3. the next face is refused as "layer still unlocked".

  Example: `E1-4/scr20inv_s2401`, switch log at t = 4.87, 5.04 and 5.78 s.
* The deviation was reported by the sub-agent ("relock uses the unlocked face's shear"), but the main session's review
  missed its conflict with A2 before committing.

**What happened next:** option A, approved by the user ("go with A"):

1. Fix the harness to match the pre-registration.
2. Amendment 4: block the spurious re-unlock.
3. Unscored smoke tests.
4. A fresh scored run on **new seeds 3000–3999**.
