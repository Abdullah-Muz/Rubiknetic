# D1 — Corner-twist diagnostic for M1 (UNSCORED, 2026-11-12)

**Purpose:** explain the E1-6c failure. This is not part of G1 and changes no scored result.

**Method** (`run.py`; raw records in `results/`):

* Torque is applied about a corner's diagonal (logged test wrench) in a staircase: 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2
  and 5 N·m. Each step is a 0.05 s ramp followed by a 0.25 s hold. The torque is then released for 0.5 s.
* Corners `ppp` and `nnn` are tested.
* No setup randomisation.
* Each configuration also gets a turning check: `U U' R R' F F'` with seed 5000, outside the scored range.
* Configurations A–I were planned before running. J and K were added after A–I as a follow-up.

## Results (both corners agree to within about 1°)

| Config | Twist at 0.05 N·m | Twist at 0.5 N·m | Behaviour above that | Turning check | Wall time |
|---|---|---|---|---|---|
| A nominal | 11° | 35° | 1 N·m: 7 mm penetration, then diverges | pass 6/6 | 1× |
| B timestep 0.25 ms | 11° | 35° | 1–2 N·m: 3–8 mm penetration, then diverges | pass | 1.9× |
| C solref 0.5 ms, dt 0.25 ms | 10° | 22° | holds 2 N·m (0.3 mm), diverges before 5 N·m | pass | 1.8× |
| D solref 0.25 ms, dt 0.125 ms | 10° | 18° | **5 N·m: 32°, 0.25 mm, stable** | **fail** 5/6 (turn error 2.47°) | 3.2× |
| E solimp dmax 0.999 | 13° | 21° | **5 N·m: 46°, 0.36 mm, stable** | **pass** 6/6 (turn error 1.47°, penetration 0.43 mm) | 1.2× |
| H armature ×25 | 11° | 29° | 2 N·m: 7 mm penetration (corner tears through) | fail 0/6 | 1× |
| I armature ×250 | 12° | 28° | 2 N·m: tears through | fail 0/6 | 1× |
| J rigid radius + dmax 0.999 | **12° already at 0.02 N·m** | 13° | 5 N·m: 20°, 0.27 mm, stable | fail (jams, 57° error) | — |
| K preload 3 N + dmax 0.999 | **0.07°** | 20° | breaks loose at 0.1–0.2 N·m, then like E | fail 3/6 (turn error 2.93°, penetration 0.69 mm) | — |

In every configuration, the residual twist 0.5 s after release was 3–6° when the solver stayed stable.

## Findings

1. **FACT: soft contacts are *not* the main cause of the low twist resistance.**
   * In every configuration with the 1 N preload, the corner twists 10–13° at only 0.05 N·m while penetration
     stays ≤ 0.15 mm.
   * Stiffer contacts (C, D, E), a smaller timestep (B) and more effective mass (H, I) leave that first ~10°
     unchanged.

2. **FACT: the twist is a collective motion of the corner and its neighbours.**
   * Neighbouring cubies rotate 3–6°.
   * With the slide present, the twisting corner moves out about 0.55 mm, from its seated position to the outward
     stop.
   * With the radial slide removed (J), the corner still has about 12° of twist at almost zero torque.
   * INFERENCE: M1's structure leaves roughly 12–17° of free twist play. Each cubie sits on its own 3-degree-of-
     freedom ball joint and is held only by bevelled neighbours with 0.2 mm gaps. There is no interlock like the
     feet of a real cube. The radial preload is the only thing resisting this play: it holds to about 0.05 N·m at
     1 N, and to about 0.1 N·m at 3 N (K).

3. **FACT: the divergence and tear-through at 0.5–2 N·m is a separate problem: contact-solver overload.**
   * Setting solimp dmax to 0.999 (E) removes it up to 5 N·m at about 1.2× cost, and the turning check still
     passes.
   * solref 0.25 ms (D) also removes it, but costs 3.2× and fails the turning check.
   * A smaller timestep alone (B) does not help. Adding armature (H, I) makes both twisting and turning worse.

4. **INFERENCE: the play overlaps the forgiveness and observer scales.**
   * About 12° of free twist play is close to the observer's 15° tolerance and to the 12–15° forgiveness angle.
   * Some of the emergent "corner cutting" in E1-0 and E1-5 may come from this same play. Not yet tested.

5. **Limits of this diagnostic:**
   * One seed, two corners, and one turning sequence per configuration.
   * The turning check is not the scored protocol.
   * No real-cube twist data is available yet (open item O-09), so the *correct* twist resistance is unknown.

## Implications (PROPOSAL; nothing has been changed)

* **The cheap solver fix (dmax 0.999) addresses only the divergence, not the twist play.** It can be carried into
  any future model's pre-registration.
* **M1 cannot become twist-resistant through tuning.**
  * A stronger preload trades twist resistance for turning failures (K).
  * Removing the radial slide jams turning (J; consistent with E1-0).
  * A real fix needs structural change, such as interlocking interior geometry ("feet").
* **M2 (switched welds) targets exactly this weakness.** Welding idle cubies would remove the free twist play
  directly. Its weld constraints use the same soft-constraint model, so finding 3 applies to it. E1-6c, with an
  added penetration/credibility criterion, should be the first test M2 faces.
