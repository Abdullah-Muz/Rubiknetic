# D22: six-face reach and regrasp/handoff map at the G2 layout (UNSCORED, kinematics only, 2026-11-27)

**Status:** unscored feasibility study for Phase 4 (G4) planning. It is not pre-registered and not a validated plan.
**Static kinematics only:** IK and collision checks at static poses. There is no contact dynamics, no grasp
stability, no motion between poses, and no check that a grasp holds the cube. It reads the frozen G2 code
(`D18_two_arm_m7/layout.py`, `two_arm.py`, `D17_real_holder_m7/hold.py`, `turn.py`) and modifies none of it.

**Labels:** `FACT` means computed here or read from committed files. `INFERENCE` means reasoned from facts.
`ASSUMPTION` means taken without evidence.

## Question
At the G2 layout, which cube faces can be turned, by which arm, and from which cube orientation? Which faces can be
turned without a regrasp? What is the shortest regrasp/handoff sequence that gives access to all six faces?

## Method
**Layout (as G2).**
- Arm A's base is at the origin. Arm B's base is at (1.0, 0, 0) m, yawed 180°, with the modelled wrist F/T sensor
  (`two_arm.add_ft_sensor`). Arm A has no F/T sensor.
- The table is the plane z = 0. The cube is a 56.95 mm box centred at (0.5, 0, 0.30) m.
- At the G2 orientation: U = +x (toward B), D = −x (toward A), R = +y, L = −y, B = +z (up), F = −z (toward the table).

**Grasps.** Every axis-aligned gripper pose on the cube is used: 6 entry faces × 4 roll angles about the gripper axis.
The 4 roll angles are 2 pad axes × the ROLL180 flip; J1, J3, J5 and J7 are wrapped into ±180°.
- **COAX-c1:** C1 turner, 25 × 14 mm pad. Its distal end is 14 mm inside the entry face, so it grips that layer, and a
  J7 roll turns it (G2 arm B).
- **COAX-p97:** P-97 stabiliser, 30 × 30 mm pad, spanning 0–30 mm from the entry face. It holds the entry layer plus
  11 mm of the middle layer, so it stabilises a turn of the **opposite** face (G2 arm A).
- **SIDE-p97 / SIDE-c1:** the gripper enters a face perpendicular to the turn axis. The pad width runs along the turn
  axis, flush with one end face. SIDE-p97 stabilises a turn of the face opposite that end. SIDE-c1 holds 19 + 6 mm
  and is only used as arm B's holding grasp in the FIXED scenario. **SIDE grasps are new and not mechanically
  assessed** (`ASSUMPTION` that they hold).
- In total there are 144 world poses per arm.

**IK.** `layout.ik`, with the rotation-vector error, the 6 D18 seeds and 18 random seeds (`default_rng(22)`). A solution
is accepted at < 1e-4 m and < 0.01°. Up to 3 distinct postures are kept per pose. The approach pose, 40 mm out along
the axis with the gripper open, is solved from the grasp solution.

**Collision (`reach.Scene`).**
- Both arms in one MuJoCo model. The cube is represented by mocap boxes: the full cube, or the two held layers plus the
  turned layer.
- Detection uses `mj_kinematics` + `mj_collision` with a 10 mm contact margin. `clearance.py` re-checks the tours with
  60 mm.
- Collision geometry:
  - the model's collision meshes for the links, gripper base and knuckles;
  - the fingertip boxes;
  - **plus the G2 finger meshes as convex hulls.** These are visual-only in G2; they are added here as a conservative
    extra and are not blocking for a grasping arm.
- A configuration passes if there is no arm–arm, robot–table or self (non-adjacent links) pair, and no unexpected
  robot–cube pair, closer than 0 mm. A grasping arm's pads may touch the cube; their measured gap is 0.024–0.025 mm,
  which confirms that every grasp places its pads on the cube faces.

**Checks.**
- **solo:** one arm at the grasp, the other parked upright (q = 0).
- **turn:** holder (stabiliser) + turner, with the turner at its approach, at the grasp, and rolled −180…+180° in 30°
  steps. The turned layer rotates with the turner, and the holder is checked against it.
- **handoff:** the holder grasps; the receiver approaches open, then closes. Pad footprints must not overlap (1 mm
  clearance).

**Graph (`graph.py`).**
- A state is (holding arm, grasp in the cube frame, cube orientation, one of 24).
- **reorient:** the holder carries the cube to another orientation with the same grasp. Both end poses must pass the
  solo check. **The path between them is not checked.**
- **handoff:** passes the handoff check.
- A face is turnable in a state if the holder's grasp stabilises it and the other arm's turn check passes.
- Dijkstra, cost = (handoffs, then reorientations).
- Two tooling scenarios:
  - **FIXED** (G2 tooling): A has P-97 pads and can only hold or stabilise. B has C1 pads + F/T and turns; it holds the
    cube during handoffs by a C1 grip (`ASSUMPTION` that such a weak grip holds the cube).
  - **SYM:** either arm can take either role. This needs a tool change or a dual-purpose fingertip, which is not
    designed.
- Two grasp families: `coax` (G2-like grasps only) and `all` (with SIDE).

## Results (`FACT` for this model and these checks)
### 1. Reach map by the world direction of the face to be turned
Each cell gives collision-free variants / variants checked (solo), and the best joint-limit margin among them.
| Face points to | G2 face | A: turn (C1) | B: turn (C1) | A: stabilise COAX / SIDE | B: stabilise COAX / SIDE | Pair A holds, B turns | Pair B holds, A turns |
|---|---|---|---|---|---|---|---|
| +x (toward B) | **U** | 0/4 (no IK) | 4/4, 24.3° | 4/4, 31.5° / 6/8 | 0/4 (no IK) / 6/8 | **40/40 pass** (16 COAX holders) | not possible |
| −x (toward A) | **D** | 4/4, 28.4° | 0/4 (no IK) | 0/4 (no IK) / 6/8 | 4/4, 27.1° / 6/8 | not possible | **40/40 pass** (16 COAX) |
| +y | **R** | 4/4, 74.3° | 4/4, 70.9° | 4/4, 75.6° / 4/8 | 4/4, 72.5° / 4/8 | 32/32 pass | 32/32 pass |
| −y | **L** | 4/4, 74.3° | 4/4, 70.9° | 4/4, 75.6° / 4/8 | 4/4, 72.5° / 4/8 | 32/32 pass | 32/32 pass |
| +z (up) | **B** | 4/4, 81.8° | 4/4, 85.3° | 0/4 (table) / 6/8 | 0/4 (table) / 6/8 | 24/24 pass (**SIDE holders only**) | 24/24 (SIDE only) |
| −z (table) | **F** | 0/4 (table) | 0/4 (table) | 4/4, 80.7° / 6/8 | 4/4, 83.3° / 6/8 | not possible | not possible |

- **Reach limits:**
  - Neither arm reaches a pose entering the cube from the far side, toward its own base (A from +x, B from −x): no IK
    solution with any of 24 seeds.
  - No pose entering from below (−z) is collision-free with the table at H = 0.30 m.
- **Consequences:**
  - A face pointing at the table cannot be turned.
  - A face pointing up can only be stabilised by a SIDE grasp.
  - The face toward B can only be turned by B, and the face toward A only by A.
- **Turn checks:** every turn pair that passed both solo checks also passed the turn check, 256/256. This includes the
  ±90° and ±180° roll sweep (U2), and holds in both directions.
  - J7's range is ±360°, so the roll never reaches a joint limit (worst-case J7 margin after a half turn ≥ 0 by
    construction, since q7 is wrapped).
  - In the tours, arm–arm clearance over the whole sweep is ≥ 28 mm and robot–table clearance is ≥ 60 mm.
- **Handoff checks:** pairs whose pads do not overlap pass in 2144/3952 cases (FIXED) and 1232/3024 (SYM). The rest
  fail on approach or with both grippers closed.

### 2. Faces turnable without a regrasp from the G2 configuration: **U only**
- **Topology** (`FACT`, from the grasp geometry): arm A's P-97 pads lie on the R and L faces over D and 11 mm of E.
  - They clamp cubies of D, R and L directly.
  - They also clamp the D-layer corners, which are in F and B.
  - So only U is free to turn. Reorienting the cube does not change that.
- **Kinematics** confirms this independently, even if A's grasp is ignored:
  - D (−x) has no turner: B cannot reach it, and A is the holder.
  - F (−z) faces the table, which blocks any turner.
- `graph.py` agrees: with A's grasp fixed, only U is turnable in any of A's 16 reachable cube orientations.

### 3. Regrasp / handoff graph
**Fewest handoffs to make each face turnable, starting from G2** (h = handoffs, r = reorientations):
| Scenario | U | D | R | L | F | B | All six (tour) |
|---|---|---|---|---|---|---|---|
| FIXED, coax | 0 | 2h 1r | 2h | 2h | 2h 1r | 2h 1r | **10h 1r** |
| FIXED, all | 0 | 2h 1r | 2h | 2h | 2h 1r | 2h | **10h 1r** |
| SYM, coax | 0 | 1h | 1h | 1h | 1h 1r | 1h 1r | **5h 1r** |
| SYM, all | 0 | 1h | 1h | 1h | 1h 1r | 1h 1r | **5h 1r** |

**Face-to-face cost** (`matrix.py`, over every reachable state where the first face is turnable):
- FIXED: always exactly 2 handoffs.
- SYM coax: always exactly 1.
- SYM all: 1–2. Some SIDE-grasp states need 2.

**Interpretation** (`INFERENCE`):
- Each stabilising grasp enables exactly one face. In FIXED only A can stabilise, so A must release and regrasp: A→B,
  then B→A, which is 2 handoffs per face change. In SYM, one handoff swaps the roles.
- 10 and 5 are therefore the lower bounds set by the grasp topology. **At the G2 layout, kinematics and collisions do
  not raise them.**

**Best FIXED-coax tour (10 handoffs, 1 reorientation).** A always stabilises and B always turns. B holds the cube only
during handoffs, by a one-layer C1 grip.
1. G2 start: turn **U**.
2. →B holds the U layer. →A takes COAX from R (pads on B/F): turn **L**.
3. →B. →A takes COAX from L: turn **R**.
4. A reorients the cube 180° (U+x/B+z → U−x/B−y). →B holds the D layer. →A takes COAX from U: turn **D**.
5. →B. →A takes COAX from F: turn **B**.
6. →B. →A takes COAX from B: turn **F**.

**Best SYM-coax tour (5 handoffs, 1 reorientation).**
1. Turn **U**.
2. →B takes COAX from U: A turns **D**.
3. B reorients 120° (→ U+z/B−y). →A takes COAX from R: B turns **L**.
4. →B takes COAX from L: A turns **R**.
5. →A takes COAX from F: B turns **B**.
6. →B takes COAX from B: A turns **F**.

Full step lists, with grasp ids, margins and clearances, are in `results/graph.json` and `results/tour_clearance.json`.

### 4. Tight spots (`FACT`, values; `INFERENCE`, ranking)
1. **Arm B's joint-limit margin at the +x turn/hold pose is 19.7°** (J4 near its −11° limit). This pose is G2's own U
   turn, and it recurs in every FIXED handoff. It is the lowest margin in all the tours. Arm A at its −x poses has
   26–30°, and the ±y and +z poses have 55–85°.
   - **Side finding:** the committed D18/G2 record with the F/T sensor
     (`D18_two_arm_m7/results/two_arm_F20_L1_H0.3_U_Up_U2_Up_U_stand_ft0.6.json`) logs arm B's margin as
     **19.08°**.
   - The G2 pre-registration §5 table cites "≥ 25.8° joint margin", which is the layout figure before the F/T sensor.
   - This is not a collision or a gate issue, but the cited number is out of date. It is flagged here and not edited,
     because the file is frozen.
2. **Reorientations are unchecked.** The tours need one large carry by the holding arm: 180° in FIXED, 120° in SYM.
   Only the end poses were checked. A path through joint space, with the other arm parked, still has to be planned and
   collision-checked.
3. **Handoff arm–arm clearance with both grippers closed** is 18–23 mm for the COAX handoffs in the tours. With SIDE
   grasps it falls to **1.1 mm** (SYM-all, the handoff before F) and 12.9 mm. Of all handoffs that pass, 400 (FIXED)
   and 512 (SYM) are below 5 mm, many of them pad-to-pad at a cube edge. The `coax` tours avoid these.
4. **The face pointing up needs a SIDE stabiliser**, and the face pointing at the table cannot be turned at all. Every
   F/B access therefore depends on reorienting the cube, so that the face to turn points ±y or ±x.
5. **Mechanical, not kinematic:**
   - In FIXED, arm B must hold the whole cube by a 14 mm one-layer C1 grip during each handoff. The other two layers
     hang through the core mechanism; in G2 only one layer hangs.
   - SIDE grasps and the SYM tooling are undesigned.
   - None of this is assessed here.

## FACT / INFERENCE / ASSUMPTION summary
- **FACT:** all IK residuals, joint margins, collision distances and graph costs above, for the stated model, layout,
  grasp set and collision geometry. Also the reach limits (far side, from below), U-only without a regrasp, and the
  10 / 5 handoff tours.
- **INFERENCE:**
  - 10 / 5 are topological lower bounds, and the layout does not raise them.
  - The ranking of the tight spots.
  - The finger-hull and knuckle clearances (14.7 mm to the cube, constant) are not limiting.
- **ASSUMPTION:**
  - The cube centre stays at (0.5, 0, 0.30) m in every orientation.
  - The idle arm parks upright at q = 0.
  - Convex hulls stand in for the true mesh geometry: conservative for the links, unknown for the hand geometry not
    modelled for collision.
  - Pads at the calibrated 57 mm closure.
  - A has no F/T sensor in SYM.
  - SIDE grips and B's one-layer C1 grip would hold the cube.

## Limitations
- Static poses only. There is no trajectory between grasp, approach and reorientation poses, and no dynamics, contact
  forces, slip, grasp stability or cube-mechanism behaviour during handoffs.
- Collision is checked at discrete roll angles (30° steps), at grasp and approach poses only.
- One layout (L = 1.0 m, H = 0.30 m) and one cube position. Moving the cube between handoffs, or raising it so that a
  COAX stabiliser can enter from below, is not explored.
- At most 3 IK postures per pose. A different posture might change a failed handoff.
- Only axis-aligned grasps. Tilted grasps, regrasps on a fixture, and putting the cube down are not considered.

## Reproduce (WSL, single process, about 20 min in total on this machine)
```bash
cd /mnt/c/dev/Rubiknetic/experiments/D22_face_reach
~/.venvs/rubiknetic/bin/python reach.py        # ~10 min -> results/reach.json (IK + solo/turn/handoff checks)
~/.venvs/rubiknetic/bin/python graph.py        # ~8 min  -> results/graph.json (direction map, per-face, tours)
~/.venvs/rubiknetic/bin/python matrix.py       # ~1 min  -> results/matrix.json (face-to-face cost matrix)
~/.venvs/rubiknetic/bin/python clearance.py    # <1 min  -> results/tour_clearance.json (60 mm clearances on tours)
```
MuJoCo 4.0.1. The seeds are fixed (D18 seeds + `default_rng(22)`). Logs are in `logs/`. `reach.py --L/--H` changes the
layout.
