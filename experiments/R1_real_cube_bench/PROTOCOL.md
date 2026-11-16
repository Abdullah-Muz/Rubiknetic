# R1 — Real-cube bench measurements (protocol; no data yet)

**Why.** Our simulated cube has no real-cube data to be checked against. A literature search (2026-11-14, P-20
subagent, checked by the main session) found **no published turning-torque, corner-twist or friction measurement for
a standard 57 mm cube**. The only measured torque found is for a 0.4 m giant cube. So the G1 corner-twist criterion
has nothing to anchor it.

The current sim cube (B1 + magnets) gives, for comparison:

| Quantity | Sim (B1 + magnets, stage 1 revision 2) |
|---|---|
| Peak turning torque during a quarter turn (gripper rig) | 0.32–0.72 N·m |
| Corner-twist torque to reach 15° | 0.78–0.80 N·m |
| Corner twist at 5 N·m | 39–41°, without popping |
| Forgiveness: next turn still completes when the previous layer is off by | ±12° (the largest tested) |
| Snap-back from 3–8° off | to within 0.5° |

**Time:** about 30–45 minutes. **Cost:** nothing beyond household items.

## You need
- **The cube**, ideally the kind we'd like to model. A magnetic speedcube is best; an original Rubik's brand cube is
  also useful. Note the brand and model.
- **A scale:**
  - a luggage scale (hook type), or
  - a kitchen scale plus a small plastic bag and water or coins.
- **A lever:** a stiff 30 cm ruler or a flat stick, and strong tape.
- **Something to hold the cube still:** a vice with a cloth, a clamp, or a heavy book pressed down with your hand.
- **Your phone:** camera for photos straight down, and optionally a protractor or level app.
- **A paper protractor:** print one, or draw lines every 5° from a centre point. Use it under or behind the cube to
  read angles off photos.

## Measurements (5 repeats each; write down every reading)

### M1 — Cube basics
- Edge length in mm (ruler).
- Mass in g (kitchen scale).
- Magnetic or not.
- Tension setting, if adjustable.

### M2 — Layer turning torque (breakaway and running)
1. Hold the bottom two layers still: clamp them gently through a cloth, or press them down firmly on a table.
2. Tape the ruler across the top face so it passes over the centre and sticks out to one side. Mark a point **10 cm
   from the cube's centre axis**.
3. **With a luggage scale:** hook it at the 10 cm mark and pull slowly and horizontally, at right angles to the ruler.
   - Record the **peak reading just as the layer starts to move**. That is breakaway.
   - Record the **steady reading while it keeps turning slowly**. That is running.
4. **With a kitchen scale instead:** turn the cube so the top face points sideways, so the ruler is horizontal and
   can hang a load. Hang the bag from the 10 cm mark and add water or coins slowly until the layer starts to turn.
   Weigh the bag. That gives breakaway only.
5. Do both turning directions, 5 times each.
6. Torque (N·m) = reading (kg) × 9.81 × 0.10 m.

### M3 — Forgiveness / corner cutting
1. Draw a mark on the top layer and a matching mark on the layer below.
2. Turn the top layer **off square by θ** (5°, 10°, 15°, 20°, 30°, 40°), reading θ from the paper protractor in a
   photo taken straight down.
3. Without touching the top layer, gently try to turn the **right** face.
4. Record yes or no: does it turn fully without catching?
5. Repeat with the top layer offset the other way. One direction is "forward" and the other "reverse" corner
   cutting; they usually differ.
6. Record the largest θ that still works in each direction.

### M4 — Snap-back (magnetic cubes especially)
1. Turn the top layer by θ (2°, 5°, 10°, 15°, 20°, 30°) and let go cleanly.
2. Photo straight down. Record the angle it settles at: 0 means it snapped square.
3. Record the largest θ that still snaps back to square, if any.

### M5 — Corner-twist resistance (optional; can damage the cube)
This is the measurement the G1 corner-twist question needs most. A corner can pop out. Most speedcubes can be
reassembled, but don't do this on a cube you mind losing.
1. Hold the cube still with the chosen corner pointing up.
2. Grip **only that corner piece** with padded pliers (tape over the jaws). Tape the ruler to the pliers handle as a
   lever, at right angles to the corner's diagonal (the line from the corner through the cube's centre).
3. Pull with the luggage scale at 10 cm, or hang a weighted bag at 10 cm, increasing slowly.
4. Record:
   - (a) the torque when the corner has visibly rotated about **15°** (photo);
   - (b) the largest twist angle reached before it pops or you stop;
   - (c) the torque at which it **pops**, if it does.
5. 3 repeats if the cube survives.

## Recording sheet
| Measurement | Direction or condition | Repeat 1 | 2 | 3 | 4 | 5 | Units |
|---|---|---|---|---|---|---|---|
| M1 edge length / mass / magnetic | — | | | | | | mm / g / y-n |
| M2 breakaway | clockwise | | | | | | kg at 10 cm |
| M2 breakaway | counter-clockwise | | | | | | kg at 10 cm |
| M2 running | clockwise | | | | | | kg at 10 cm |
| M2 running | counter-clockwise | | | | | | kg at 10 cm |
| M3 largest θ that still turns | forward / reverse | | | | | | ° |
| M4 residual angle after release from θ | θ = 2, 5, 10, 15, 20, 30 | | | | | | ° |
| M5 torque at 15° twist / max twist / pop torque | — | | | | | | kg at 10 cm / ° / kg |

Photos are welcome. Any number with how it was measured is better than none.

## How the data will be used
- **M2:** calibration of turning resistance against the sim's 0.3–0.7 N·m.
- **M5:** decides the G1 corner-twist criterion. Two cases:
  - If a real cube twists 15° at well under 5 N·m or pops, then "≤ 2° at 5 N·m" is not a realistic requirement. The
    criterion would be rewritten around measured real behaviour, **before** any scored run.
  - If a real cube really is that stiff, B1 needs a structural fix.
- **M3 and M4:** realistic targets for forgiveness and snap-back.

Rules:
- Measured values are recorded as `FACT` with the method.
- Thresholds derived from them are `PROPOSAL`s for your approval, set before the scored run, never after.
- One cube is a single sample. It gives an anchor, not a population.
