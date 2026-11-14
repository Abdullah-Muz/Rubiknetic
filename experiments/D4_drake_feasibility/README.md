# D4 — Drake hydroelastic feasibility for a real-mechanism bearing (UNSCORED, 2026-11-13)

**Approval:** P-15 (user: "okay lets try Drake"). This is an exploration only. **MuJoCo remains the locked
simulator (D-02).**

**Question:** D3 showed that MuJoCo's convex collision cannot represent a real cube's concave spherical bearings at
a usable size or speed. Can Drake's hydroelastic contact do it?

**Test** (`t1_bearing.py`, run in a separate Drake 1.58.0 virtual environment, not the project environment):
- A compliant sphere (R = 24.95 mm, 3 g) sits in a rigid **non-convex** spherical cap cup (inner R = 25.0 mm), so
  the radial clearance is 0.05 mm.
- The sphere is pressed in with 3 N and spun by a torque ramped from 0 to 0.05 N·m.
- Defaults: time step 1 ms; cup mesh from a 64-point profile × 256 sections; compliant resolution hint 2 mm;
  hydroelastic modulus 5e7; friction 0.2.

**Result** (as recorded in commit `2df4e66`; the raw output was not saved to the repo):
- Drake represented the concave bearing.
- It ran at **about 25 steps/s for this single bearing pair**, which is too slow. A full cube has dozens of such
  contacts, compared with about 1,400 steps/s for M2.

**Limits:**
- one configuration (one mesh resolution and one time step); not a tuning study;
- this README was written on 2026-11-14 from the script and the commit message, because the original run did not
  write a report.

**Status:** not pursued. Revisit only if real-mechanism fidelity becomes worth roughly two orders of magnitude in
throughput, for example as an offline reference.
