# Rubiknetic so far, in plain language (G1 and G2)

> **DRAFT summary generated from project records. Not for publication without the project owner's approval.** It
> summarises `docs/writeup/G1_G2_DRAFT.md`, which cites the source file for every number.

**What is Rubiknetic?** It is a computer simulation project. The long-term aim is for two simulated robot arms to solve
a Rubik's cube by actually gripping and twisting it, the way real arms would have to. This summary covers the first
two steps. Everything here happened in simulation, using the MuJoCo physics engine. No real robot or real cube was
used, and nothing here shows that the results would carry over to real hardware.

**Why is this hard to do honestly?** In a simulation it is easy to cheat. A program can simply rotate a layer of the
cube by setting its angle, or hide a motor inside the cube. A robot would then appear to turn the cube without really
doing it. The project's rules forbid this. Layers may only move because something pushes on them, with the forces
computed by the physics engine. The small magnets modelled inside the cube are allowed, because they are passive
parts that act between specific pieces through a fixed physical force law (the project's rule P-16).

**Step 1 (gate G1): a believable simulated cube.**
- The team built a model cube from 26 separate pieces that touch and slide against each other, with 48 tiny magnets.
- It took several designs. Three earlier versions (M1, M4, M5) failed their tests, and one (M2) was never properly
  scored. A later version, **M7**, passed.
- In its test, a simple clamp-and-twist fixture turned the cube's layers in 204 planned trials: single turns, long
  sequences, resting still, and deliberate abuse. **All 204 passed** on every planned check (turn accuracy, no pieces
  pushed into each other, no unwanted movement). Source: `experiments/E7_scored_m7/G1_REPORT_M7.md`.
- A separate cube program, written independently, checked that the cube's colours ended up where a real cube's would.

**Step 2 (gate G2): two robot arms turn a layer.**
- Two models of a real industrial arm (the UFACTORY xArm7) face each other across a table.
- Arm A holds two layers of the cube. Arm B grips the top layer and twists its wrist a quarter or half turn, then lets
  go and turns back.
- Neither arm is told where the cube's pieces are. They act only on their own joint sensors and a simulated
  force/torque sensor in arm B's wrist. If arm B feels too much resistance, it stops instead of forcing the cube.
- **Result: 128 of 128 planned trials passed** (`experiments/E8_scored_g2/G2_REPORT.md`):
  - 100 turning trials with 360 turns in total, and no failures;
  - 20 one-minute holds;
  - 8 deliberately faulty setups, such as gripping two layers, blocking the layer, or letting go mid-turn. Each fault
    was caught as intended.
- The largest turning error was 0.414°, against an allowed 2°.

**How the testing was kept fair.**
- **The rules were written first.** The pass criteria, the number of trials and the code were fixed and frozen before
  the real test.
- **The test cases were new.** The test used random cases ("seeds") that had never been run before.
- **No failures were allowed.** One failure in the scored trials would have meant "not passed".
- **The plans were reviewed independently.** A separate reviewer, given the code but not the authors' conclusions,
  checked each plan. Reviews continued until the reviewer had no required changes: 4 rounds for G1 and 7 for G2.

**A mistake that the process caught.** During the arm work, a software bug silently switched off the cube's magnets
in every two-arm test run before the fourth review. The turns still worked, so nothing looked wrong. The fourth
independent review found the bug. The team then:
- fixed it;
- added a check that the magnets act at every simulation step, with a trial failing if they ever do not;
- re-ran all the preliminary tests with the magnets on (144 of 144 passed);
- confirmed with a separate check that the earlier cube test (G1) had not been affected.

The lesson is that a helpful force can quietly disappear without any failure showing it, so it has to be checked
directly.

**What these results do not show.**
- Only one face (the top layer) was turned, from one grip. There was no regrip, no other faces and no cameras.
- Several properties of the cube are assumptions, not measurements: how tight the pieces fit, how hard a real cube is
  to turn, and how grippy the fingertips are.
- The simulation is slow: about 0.04× real time per trial.
- Nothing here is a full solve, and nothing is tested on real hardware.

**What comes next.**
- **G3:** test whether a learning controller can improve on the hand-designed one. The design work has been
  authorised; training has not started.
- **G4:** regrip the cube and turn other faces.
- **G5:** read the cube's state from cameras.
- **G6:** full solves.
- **G7:** a reproducible public release.
