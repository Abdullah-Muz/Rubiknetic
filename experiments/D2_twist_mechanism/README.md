# D2 — Mechanism of M1's corner-twist play (UNSCORED, 2026-11-12)

This follows D1 ([`../D1_corner_twist_diagnostic/README.md`](../D1_corner_twist_diagnostic/README.md)). It is not
part of G1 and changes no scored result.

**Setup:** corner `ppp`, the D1 torque staircase, and stable contact settings (solimp dmax 0.999). The code is in
`run.py`, and the raw records are in `results/`. The work ran in three steps, each added after the previous result:

* the main run (geometry probe and dynamic decomposition);
* `--followup` (centre locking);
* `--followup2` (parameter levers).

## 1. Geometry alone allows only ~2° (FACT)

This is a kinematic probe: no dynamics, with every other cubie held still, using MuJoCo signed-distance queries.

* With all cubies at nominal radius, the corner shape twists **1.25°** before it touches a neighbour.
* Lifted to its outward stop (+0.2 mm), it twists **2.25°**.
* In the settled rest pose, it is already in contact at 0°: the preload wedges it into its neighbours.

## 2. The play comes from many cubies moving together (FACT)

Twist at 0.05 N·m and 2 N·m, with different sets of cubies welded to the core:

| Free to move | Twist at 0.05 N·m | Twist at 2 N·m |
|---|---|---|
| corner only | 2.2° | 4.9° |
| + its 3 edges | 3.5° | 7.6° |
| + all cubies on its 3 faces (19) | 14.4° | 29.7° |
| everything except the 6 centres | 8.9° (14.3° at 0.1 N·m) | 28.5° |
| everything (M1 as is) | 15.9° | 31.7° |

The centre hinges rotate about 3° when free, but locking them changes little. The slack is spread over about 20
corner and edge cubies, each contributing a fraction of a degree to a few degrees.

## 3. Two stages: breakaway, then slack (FACT)

* **Below breakaway:** the corner sits at its seat, about 0.35 mm inside nominal, and twist stays ≈ 0°.
* **At breakaway:** the corner jumps to its outward stop (slide −0.35 → +0.21 mm) and the twist jumps to ~10–16°.
* **Above it:** the twist grows slowly with load, through contact compliance.

## 4. Which parameter controls what (FACT; all cubies free; turning check `U U' R R' F F'`, seed 5000)

| Lever | Breakaway torque | Twist at 0.05 / 0.5 / 2 N·m | Turning check | Peak turner torque |
|---|---|---|---|---|
| reference (1 N preload, stop +0.2 mm) | < 0.05 N·m | 15.9 / 21.3 / 31.7° | pass 6/6 | 0.81 N·m |
| preload 3 N | 0.1–0.2 N·m | 0.1 / 22.0 / 31.9° | fail 3/6 | 1.0 (at limit) |
| preload 10 N | 0.2–0.5 N·m | 0.0 / 24.5 / 31.1° | fail (jam) | 1.0 (at limit) |
| outward stop 0.0 mm | < 0.05 N·m | 11.8 / 15.4 / 23.7° | fail 4/6 | 1.0 (at limit) |
| outward stop −0.15 mm | < 0.05 N·m | 6.7 / 9.7 / 17.7° | **pass 6/6** | **1.0 (at limit)** |
| outward stop −0.25 mm | < 0.05 N·m | 2.4 / 5.9 / 13.0° | fail (jam) | 1.0 (at limit) |
| gap 0.1 mm | < 0.05 N·m | 10.8 / 16.5 / 25.0° | fail 3/4 | 1.0 (at limit) |
| gap 0.05 mm | < 0.05 N·m | 6.7 / 13.8 / 21.8° | fail 1/6 | 1.0 (at limit) |

* **Preload sets the breakaway torque** but not the slack. Above 1 N it breaks turning: the turner saturates at its
  1 N·m limit.
* **The outward stop sets the slack**, at roughly 30° per mm of available lift. A lower stop reduces the slack, but
  turning needs about 0.2 mm or more of lift: −0.15 mm still turns, −0.25 mm jams.
* **Gap** has a weaker effect on slack and also breaks turning.

## Root cause (INFERENCE, supported by sections 1–4)

* M1 gets its rigidity at rest from **preload wedging**. Each corner and edge cubie is pulled inward by its own
  1 N spring until the 0.2 mm design gaps close.
* A small torque, about 0.02–0.05 N·m, cams a cubie out of that wedge. That reopens up to 0.55 mm of radial play
  and lets about 15° of slack build up through the shell.
* **Turning needs exactly the same radial play.** M1's turning surfaces are flat, bevelled block faces, which can
  slide past each other only once the gaps reopen.
* So in M1, twist resistance and turnability are **coupled through one mechanism**. None of the tested settings
  gives both:
  * the only setting that halves the slack (stop −0.15 mm) uses the turner's full torque margin;
  * it still twists 18° at 2 N·m.
* **Contrast with a real cube** (general design knowledge, not measured here): pieces are held by interlocking
  inner feet that slide on concentric surfaces. Clearance for turning does not depend on letting pieces lift
  outward, so retention and turnability are decoupled.

**Plausibly the same mechanism (INFERENCE, untested):**

* the E1-4 pop-check overshoot;
* the E1-6b radial change (0.8–0.9 mm);
* part of the 12–15° forgiveness or corner-cutting angle.

## What could fix it (PROPOSAL; nothing has been changed)

1. **M1 tuning (outward stop −0.15 mm):** a partial mitigation only. It halves the slack, but leaves no turner
   torque margin and still allows 18° at 2 N·m. Not recommended as the fix.
2. **M1 structural change (interlocking interior geometry):** add inner "feet" or concentric-shell geoms so
   cubies are captured radially *with* running clearance, and drop the per-cubie preload. This is the most
   physical option, but it is a substantial geometry and calibration project with its own open questions (convex
   decomposition, contact count, throughput).
3. **M2 (switched welds, already approved as the comparison):** welding idle cubies removes the slack by
   construction, and releasing the welds for the turning layer avoids the conflict with turning. It is the
   cheapest test of whether a decoupled model passes E1-6c. Its welds are soft constraints, so carry over
   dmax 0.999.

**Limits:**

* One corner (`ppp`; D1 showed `nnn` behaves the same), one seed, and one turning sequence per setting.
* The turning check is not the scored protocol.
* There is no real-cube twist data (O-09), so the *target* breakaway torque and slack are unknown.
