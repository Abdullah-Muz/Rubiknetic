# Findings: how a real Rubik's Cube works, and what the simulated cube should copy (2026-11-12)

This report answers why M1 fails E1-6c (see [`../../experiments/D2_twist_mechanism/README.md`](../../experiments/D2_twist_mechanism/README.md))
and what a physically faithful cube model needs. It also assesses the user-supplied GrabCAD model.

Tags: FACT = stated by a source or measured here; INFERENCE; PROPOSAL. All sources were accessed 2026-11-12.

## 1. Real cube mechanism (FACT unless tagged)

**Parts** (bill of materials from a student reverse-engineering report of a stickerless clone, so these are
indicative values only [Paulus 2023]):

| Part | Count | Material | Mass each |
|---|---|---|---|
| Core | 1 | ABS (nylon in official cubes [madehow]) | 1.7 g |
| Centre pieces | 6 | ABS | 1.0 g |
| Centre caps | 6 | ABS | 0.8 g |
| Corner thirds | 24 (8 corners) | ABS | 1.3 g |
| Edge halves | 24 (12 edges) | ABS | 1.3 g |
| Screws | 6 | metal | 1.0 g |
| Springs | 6 | metal | 0.5 g |

INFERENCE: summing the table gives about 84 g, consistent with the model's 88 g assumption.

**Size:** 5.6–5.7 cm per side [Wikipedia; madehow].

**Manufacturing:** injection-moulded ABS from virgin material, hand-assembled. Each centre is riveted to the core
over a spring, with a depth stop setting the spring compression [madehow].

**Retention and tension**, which is the key point for simulation:

* The core is "three intersecting axes". "Each of the six centre pieces pivots on a fastener", and "a spring
  between each fastener and its corresponding piece tensions the piece inward" [Wikipedia].
* Edge and corner pieces have **no fastener**. Each has "a concealed inward extension that interlocks with the
  other cubes" [Wikipedia]: "internal tabs ride on curved tracks formed by the backs of neighboring pieces"
  [madehow]. In practice, edge feet sit under the centres, and corner feet sit under the edges.
* **All tension comes from the 6 centre springs.** Looser springs mean easier corner cutting but more pops; tighter
  springs mean more control and fewer pops [zhaojeffrey; SpeedSolving thread].
* **Popping is the natural failure mode.** Disassembly works by turning a layer 45° and prying an edge out
  [Wikipedia].

**Performance figures:**

* **Corner cutting:** for speedcubes, guides and vendors claim about 45° forward and "over half a cubie" in
  reverse [speedcube.com.au; vendor listing]. These are marketing or guide claims, not measurements.
* **Turning torque and spring force:** **no published measurement was found.** One student robotics report says it
  had no reliable way to measure the required torque [UIUC ECE445]. Open item O-09 remains open.

## 2. Why M1 differs (INFERENCE, supported by D1 and D2)

| | Real cube | M1 (and OpenAI robogym, which M1 follows) |
|---|---|---|
| Edge and corner retention | Interlocking feet that slide on curved tracks; captured geometrically | Ball joint at the core plus a 1 N spring per cubie; flat bevelled blocks; no feet |
| Where tension acts | 6 centre springs | 20 individual cubie springs |
| Rigidity at rest | Geometric capture | Preload wedging; breaks loose at ~0.02–0.05 N·m |
| Corner twist | Blocked by feet and neighbours | ~15° of slack once a corner lifts 0.55 mm |

## 3. The user-supplied CAD: GrabCAD "Rotatable Rubik's Cube 3 x 3 x 3"

Source: <https://grabcad.com/library/rotatable-rubik-s-cube-3-x-3-x-3-1>. The page returned HTTP 403 to automated
access, so the author and licence were not read.

**Contents** (FACT, from the files): SolidWorks 2022 / STEP AP214 export dated 2024-10-03, in millimetres. It has
a core, 6 centre caps, 12 edges, 8 corners and 54 stickers, all as separate solids. The cube is 57.5 mm across
with a 19 mm pitch. Edges and corners have inner feet on a sphere of radius ~22 mm. **There are no
springs or screws**: the caps sit rigidly on the core arms.

**Geometry check** (FACT; exact triangle meshes with FCL collision queries; script in the scratchpad, not in
the repo):

* **At rest:** no interference between pieces. Neighbour clearance is **0.033–0.038 mm**.
* **Layer sweeps:** the U layer (horizontal) and the R and +y layers (vertical) sweep 0–90° with at least
  0.033 mm clearance. Checked at 5° steps on 3 of the 6 faces.
* **Corner twist** with neighbours fixed: ≤ 1° of free play, and blocked by 2°.
* **Radial capture:** a corner or edge pulled outward collides within **0.1 mm**, so the pieces are captured. In
  M1 they could lift 0.55 mm, which is the root cause found in D2.

**Licence (FACT):** GrabCAD's general terms default to personal or internal, non-commercial use, with creator
permission required for commercial use [GrabCAD help; terms]. **Do not commit the CAD, or meshes derived from it,
to the public repo** until the author's terms are confirmed.

## 4. Implications for a faithful model (PROPOSAL: "M3", for user decision)

* **Edges and corners as free bodies**, held only by contact with feet geometry. This removes the ball-joint
  abstraction entirely. It gives 120 DOF for these pieces, against 86 in M1.
* **Centres as hinge plus spring-loaded radial slide**, which is the real screw and spring. Tension, corner
  cutting and popping then emerge from where they do in a real cube.
* **Geometry, two options:**
  * (a) the GrabCAD model, if its licence allows: used locally and kept out of the repo;
  * (b) our own parametric feet geometry based on the publicly known mechanism, which is clean for a public repo
    and lets us tune clearances. The GrabCAD model would then be a reference only.
* **Known risks:**
  * Clearances are only 33 µm, against 0.1–0.3 mm of MuJoCo soft-contact penetration, so the pieces may bind
    unless shrunk slightly.
  * MuJoCo needs convex pieces, and the core and caps are highly non-convex, so each needs convex decomposition.
  * Free bodies held only by contact demand much more from the solver.
  * Contact count and throughput are unknown.
* **Validation targets need real data from the specific cube the robot will use:** turning torque, spring
  preload, forgiveness angle and pop threshold (O-09). A simple measurement with a force gauge or luggage scale on
  a string wound round a layer would give starting values.

## Sources

* Wikipedia, "Rubik's Cube": <https://en.wikipedia.org/wiki/Rubik%27s_Cube>
* madehow, "How Rubik's Cube is made": <https://www.madehow.com/Volume-7/Rubik-s-Cube.html>
* A. Paulus, "Rubik's Cube Manual" (student reverse-engineering report, 2023-12-12): <https://abbypaulus.github.io/Resources\Paulus_ReverseEngineering.pdf>
* J. Zhao, "The Rubik's Cube" mechanism page: <https://zhaojeffrey.github.io/home/mechanism.html>
* SpeedSolving forum, spring constants thread: <https://www.speedsolving.com/threads/replacement-screw-lengths-and-spring-constants.37417/latest>
* speedcube.com.au, speedcube characteristics: <https://speedcube.com.au/blogs/speedcubing_news_and_advice/64469763-september-2015-speedcube-characteristics>
* UIUC ECE445 robotic cube report: <https://courses.grainger.illinois.edu/ece445/getfile.asp?id=6925>
* GrabCAD use terms: <https://help.grabcad.com/article/246-how-can-models-be-used-and-shared>, <https://grabcad.com/terms>
* OpenAI et al. 2019, arXiv 1910.07113, and openai/robogym (MIT licence): cube XML inspected directly
