# G5 preparation: literature on camera-based Rubik's cube state estimation (2026-11-28)

**Status.** A research note for Phase 5 / gate G5 (camera-derived cube state). It is a first-pass literature search,
not a systematic review. No code was written and no simulation was run. No phase gate is affected. Every source was
accessed on 2026-11-28.

**Labels:**
- `FACT`: stated in a source opened in this session, at the verification level given for that source.
- `INFERENCE`: this note's reading of the sources or of the repository.
- `PROPOSAL`: a suggestion for G5. It needs user approval before it is used.
- `UNVERIFIED`: from a search-result summary or secondary report only. The primary page was not opened, or it would
  not load.

**Verification levels used in the source register (section 8):**
- **full text**: the paper body was read (HTML or PDF).
- **code**: the README and the named source files were read.
- **README**: only the repository front page was read.
- **abstract**: only the abstract page or the Crossref record with an abstract was read.
- **metadata**: only bibliographic metadata was confirmed.
- **news**: a secondary news page was read; there is no primary paper.

**Context read first:**
- `phases/PHASE_5_PERCEPTION.md`
- `docs/SYSTEM_ARCHITECTURE.md` (perception rows)
- `docs/REFERENCES_SEED.md` (items 14 and 15)
- `docs/VALIDATION_PLAN.md` (G5 checklist)
- `experiments/D21_camera_placement/README.md`

---

## 1. Summary

- `FACT`: **no published system found does what G5 needs.** G5 needs fixed cameras, robot grippers occluding the cube,
  all 54 facelets, and a cube that is being manipulated. The closest systems each cover part of this:
  - **OpenAI (2019):** cube pose and face angles during in-hand manipulation, but no sticker colours. The state was
    tracked from a known solved start.
  - **Amiet et al. (2026):** pose and full colour state from partial RGB-D views, but of a cube at rest.
  - **Kasprzak et al. (2007):** single-view facelet reading for a two-arm benchmark, but one view gives at most three
    faces.
- `FACT`: **classical colour pipelines are the norm.** Typical steps:
  - an intensity-normalised colour space (YUV, HSV or CIE-Lab);
  - per-facelet averaging, sometimes with erosion of the facelet edges;
  - a nearest-neighbour, MAP or threshold classifier.

  Learned classifiers are mostly used to *localise* the cube or the stickers, not to classify colour.
- `FACT`: **cube structure is the main tool against errors.** Constraints used in the sources:
  - nine facelets of each colour;
  - unique centres, with opposite colours on opposite faces;
  - only legal edge and corner colour combinations;
  - Kociemba's checks on twist, flip and parity.

  Ng (c. 2012) shows the cost: when the colour-count constraint is enforced, errors arrive in bunches.
- `FACT`: **face (layer) angle cannot be read from one frame of a standard cube.** The reason is the rotational
  symmetry of the stickers. OpenAI handled it in two ways:
  - an asymmetric (corner-cut) centre sticker, or temporal tracking;
  - an instrumented Giiker cube for face angles in most experiments.

  With vision face angles instead of the Giiker cube, full-scramble success fell from 20 % to 0 % (10 trials).
- `FACT`: **domain randomisation is decisive for sim-to-real.** OpenAI's real-image errors:
  - without domain randomisation: 128.83° orientation and 85.33° top-face angle;
  - with it: 7.81° and 15.92°.

  The real error was 1.2–2.5× the simulated error.
- `FACT`: **quantitative anchors for G5 are few and heterogeneous:**
  - Facelet accuracy: 94 % (Ng, 20 image pairs); 97.63 % (Liu et al., mixed lighting); 98.7–100 % (Amiet et al.).
  - Cube pose: about 6–8 mm and 7–9° (OpenAI, real); about 2 cm and under 3° (Amiet et al., 0.4 m cube at ≤ 2 m).
  - Face angle: 13.8–16.6° top face and 8.8° active faces (OpenAI, real).
  - Latency: 32–100 ms per frame (Kasprzak, 2007 hardware) up to 1.3 s per frame (Amiet et al.).
- `INFERENCE`: **G5 should not re-estimate all 54 facelets in every frame.** The literature supports a different
  split:
  1. establish the colour state when the view is good, with legality-constrained resolution;
  2. during a turn, track cube pose and layer angle;
  3. after each turn, check the visible facelets against the predicted state.

  Step 3 tests a hypothesis, so the gripped side faces (about 60 % visible, D21) need not be fully read.
- `INFERENCE`: **G5 must not use segmentation renders as a perception input.** D21 used MuJoCo segmentation renders,
  and segmentation IDs are simulator truth. G5 perception must work from RGB (and depth, if allowed) only.

## 2. Q1: how published systems estimate the 54-sticker state

### 2.1 Classical colour classification

**Kasprzak, Szynkiewicz & Czajka, "Rubik's Cube Reconstruction from Single View for Service Robots"** (Machine
Graphics & Vision; full text read).
- `FACT`: the setup is a two-arm benchmark: two modified IRp-6 arms with parallel-jaw grippers, wrist F/T sensors,
  eye-in-hand cameras and a fixed global camera.
- `FACT`: the pipeline:
  - RGB to YUV, then U and V normalised by intensity Y;
  - classification by per-colour intervals taken under "perfect white" lighting;
  - morphology, then filtering of cell contours by moment invariants and compactness;
  - grouping of cells into up to three surfaces;
  - pose from the corners of a face.
- `FACT`: the authors state that "this approach requires a previous color-based lighting calibration". The white-point
  compensation "works fine for restricted deterioration only of the lighting color".
- `FACT`: "It is possible to detect the full cell configuration from a single view only, when 3 Rubik's cube faces are
  visible. Otherwise fusion of information coming from 3 different views is needed. This is out of the scope of this
  paper."
- `FACT`: no accuracy is reported, only timing (section 6).
- `FACT` (metadata from search results and the PDF filename `MGV_16_2007_451`): vol. 16, 2007, pp. 451–459. The PDF
  itself has blank volume fields.

**Ng, "Automated Rubik's Cube Recognition"** (Stanford report; full text read).
- `FACT`: it uses the same YUV normalisation as Kasprzak (which it cites). A MAP detector over 9×9×9 bins was trained
  on 44 images under varied lighting.
- `FACT`: the state is chosen by maximising likelihood under piece constraints. Examples given: blue centre opposite
  green; one blue-yellow edge; no red-orange edge.
- `FACT`: test set: 20 image pairs, each pair showing all six faces.
  - Cube located in 80 % of pairs.
  - Colour accuracy 94 % on located cubes; 87 % under a desk lamp, 97 % with flash.
  - "we didn't have any errors in 69% of our test images", but erroneous cases fell "as low as 52%".
  - Errors "existed in bunches because of our assertion on the number of pieces". Confusions were blue/green and
    red/orange.
- `INFERENCE`: the year is about 2012, inferred from a reference access date of 06 June 2012. Neither the course nor
  the year is printed.

**Liu et al., "Color Recognition for Rubik's Cube Robot"** (arXiv 1901.03470; full text read via ar5iv).
- `FACT`: dataset: 348 images at 640×480, 18,792 colour blocks, five lighting/cube conditions. Faces were rectified
  from manually marked corners.
- `FACT`: methods compared:
  - offline: HSV histogram features with an extreme learning machine, 84.5–87.2 % in total;
  - online: centre-seeded label propagation (WLHP, DWLP). DWLP reached 97.63 % in total and 93.88–100 % per
    condition.
- `FACT`: the offline drop is attributed to "colour drift". No runtime is reported.

**dwalton76/rubiks-color-resolver** (GitHub, MIT licence; code read: `solver.py`, `color.py`).
- `FACT`: input is RGB per square, converted to CIE-Lab. Distance is Euclidean Lab distance; the CIEDE2000 function is
  present but disabled: "CIE2000 takes about 3x more CPU".
- `FACT`: labels are assigned under cube structure:
  - squares are split into six equal buckets, so the colour counts are forced;
  - corners are matched to the 8 legal corner colour triples, and edges to legal edge pairs;
  - assignment uses a greedy TSP ordering plus a swap-improvement loop.
- `INFERENCE`: this is the most explicit open implementation of "use cubie legality as a constraint" in classification.

**kkoomen/qbr** (GitHub, MIT; README read).
- `FACT`: a webcam and OpenCV scanner for 3×3, scanned one face at a time.
- `FACT`: it has a calibration mode that learns the user's cube colours and uses the centre colour to tell which side
  was scanned.
- `FACT`: the README does not name the colour classification method.

**hkociemba/RubiksCube-TwophaseSolver** (GitHub, GPL-3.0; code read: `vision2.py`, `cubie.py`).
- `FACT`: `vision2.py` handles one face per frame:
  - HSV colour space; white decided by saturation and value thresholds; other colours by median-hue bands;
  - grid found by contour and square filtering, with point reflection through the centre facelet to fill misses.
- `FACT`: `cubie.py` `verify()` checks that each edge and corner exists once, that the total edge flip is even, that
  the total corner twist is ≡ 0 (mod 3), and that edge parity equals corner parity.
- `INFERENCE`: this is a ready reference for the independent legality check that G5 requires. The licence is GPL-3.0,
  so read it as a reference; do not copy code into the repository without a licence decision.

### 2.2 Learned classifiers and detectors

**Hack & Shutzberg, "Rubiks Cube Localization, Face Detection, and Interactive Solving"** (Stanford CS231n 2015 report;
full text read).
- `FACT`: pipeline:
  - a 6-layer CNN regresses the cube's location and scale (7 ms per forward pass);
  - three CNNs locate the face centres, one for each opposite-colour pair;
  - SLIC superpixels with a random forest find pieces;
  - RANSAC homography, then an SVM classifies colour.
- `FACT`: the reported 92 % is the cross-validated accuracy of the **piece / non-piece superpixel classifier**. It is
  not colour accuracy.
- `FACT`: "our current implementation does not support structured extraction of face information in real time."
- `FACT`: code is at github.com/jayhack/ConvCube; no licence file was visible.

**Amiet et al., "Solving a Giant Rubik's Cube with a Quadruped Robot"** (arXiv 2610.24610, Oct 2026; full text read).
- `FACT`: hardware and segmentation: ZED X Mini RGB-D camera; SAM 3 segmentation from the text prompt "rubik's cube",
  without fine-tuning.
- `FACT`: colour classification:
  - faces are rectified to 3×3 grids;
  - each facelet is eroded by 10 % against colour bleed;
  - the mean CIE-Lab colour is classified by k-NN (k = 5);
  - training data: 5819 hand-labelled patches.
- `FACT`: full state comes from aggregating partial views while the robot walks and flips the cube (section 2.3).

**dualarm-cube (UIUC ECE 445, Spring 2026)** (project page and repository README read; MIT licence).
- `FACT`: a USB 1080p camera with exposure and white balance locked; YOLOv8-nano boxes every sticker as one class; a
  k-NN classifies colour.
- `FACT`: the cube is rolled through five poses, and the ten face views are fused into the 6×3×3 state.
- `FACT`: no accuracy figures are reported.

**CubeLabsNZ/CubeCV** (README read).
- `FACT`: DINO and LangSAM segment the cube, then classical CV reads the pieces.
- `FACT`: no accuracy figures; "some hand placements obscuring corners" make line detection fail.
- `FACT`: no licence is shown on the page.

### 2.3 Multi-view fusion and temporal tracking

- `FACT` (Amiet et al.):
  - colour votes accumulate until every facelet has been observed;
  - the fourfold ambiguity of a face's orientation is resolved by matching shared edges;
  - a published net must pass a **centre-colour gate**: at least two known centres, no repeated colour, no opposite
    colours together, and a right-handed frame when three faces are visible.
- `FACT` (OpenAI 2019, section 7 and Algorithm 5): the full state is *tracked*:
  - with the Giiker cube, from a solved start by integrating the rotations it senses;
  - with vision, a tracked angle per face is updated from the predicted active-axis angles (modulo π/2), and reset from
    the absolute top-face prediction when the cube is aligned.
- `FACT` (OpenAI footnote, section 7.1): a recurrent vision model was "very difficult to train" to the needed
  performance and was not pursued.
- `FACT` (FINGR, arXiv 2609.33973, full text read):
  - the system "observes the discrete cube state" after pickup and between sequences;
  - during turns it uses "multi-view tracking of coded surface markers" for cubie poses;
  - state mismatches in solves 8 and 9 "were resolved by reobservation";
  - how colour is perceived is not described.
- `FACT` (Rubikon, arXiv 2503.12619, full text read): ArUco markers on every facelet. Moves are inferred from state
  changes against rotation templates. No tracking accuracy is reported, and occlusion is not discussed.

### 2.4 Well-documented solver robots

- `FACT` (MIT News, 15 March 2018; news read): the Katz and Di Carlo robot used two webcams. Software identified each
  piece's colour to get the initial state. The 0.38 s record time is said to include image capture and computation.
- `UNVERIFIED` (search summaries of news coverage):
  - PlayStation Eye cameras;
  - orange faces painted black to avoid red/orange confusion;
  - Mitsubishi Electric TOKUFASTbot (0.305 s, Guinness 2024) uses a proprietary "AI" colour-recognition algorithm.
- `UNVERIFIED` (the Rethink Robotics wiki would not resolve): the Baxter demo scanned faces with a flatbed scanner and
  checked 6 colours × 9, unique centres, and valid edges and corners.

## 3. Q2: pose and layer-angle estimation during manipulation

**OpenAI, "Solving Rubik's Cube with a Robot Hand"** (arXiv 1910.07113; full text read via ar5iv).
- `FACT`: model and outputs:
  - three Basler RGB cameras (left, right, top), each through a shared ResNet50, then fully connected layers;
  - outputs: position; orientation; the active axis; the active-axis face angles modulo π/2; the absolute top-face
    angle in [−π, π] (its centre cubelet is "rarely occluded");
  - angles are classified into 90 bins per π, which beat regression;
  - training images were synthetic only (Unity / ORRB), at 200×200 input.
- `FACT` (Table 2 / Table 5; sim → real):
  - Full model: orientation 6.52° → 7.81°; position 2.63 → 6.47 mm; top-face angle 11.95° → 15.92°.
  - ADR (Large): 7.48°, 6.24 mm and 13.83° on real images.
  - Non-discrete angles: top-face angle 42.46° (sim), 35.27° (real).
- `FACT` (Table 22): active-face angle error on real images: 8.89° (baseline), 8.84° (ADR Large).
- `FACT` (Giiker cube, section 3.2.2): mean face-angle tracking error 5.90° (SD 7.61°) at 12.5 Hz.
- `FACT` (Table 6, 10 real trials): with Giiker face angles, half-scramble success was 60 % and full scramble 20 %.
  With vision face angles: 20 % and 0 %.
- `FACT`: per-camera resolution, frame rate and inference latency were not found in the text read.

**Amiet et al. (2026).**
- `FACT`: pose is estimated by sequential RANSAC on face planes plus ICP to a cube model of known size (L = 0.4 m).
  It is gated by silhouette IoU ≥ 0.90, and only faces with viewing angle < 82° and > 1 % of the image are used.
- `FACT`: median error ≈ 0.02 m and < 3° up to 2 m; ≈ 0.10 m and > 20° at 3.5 m.
- `FACT`: the cube is at rest when perceived; layer angles during turns are not estimated.

**Higo (listed as "Rigo" on researchr), Yamakawa, Senoo & Ishikawa, IROS 2018, pp. 6609–6614** (DOI
10.1109/IROS.2018.8593538; metadata from Crossref).
- `FACT` (Tech Briefs news page): the 500 fps vision system computes "the center of gravity position and angle of a
  Rubik's cube".
- `UNVERIFIED`: whether the layer angle is measured, and with what accuracy. The paper was not opened.

**Yang et al., "Benchmarking Robot Manipulation with the Rubik's Cube"** (RA-L 2020, arXiv 2202.07074; full text read).
- `FACT`: the protocol gives the robot the move sequence; colour sensing is not part of the benchmark.
- `FACT`: baselines get the cube's initial pose from a head camera. Pre-touch proximity sensors cut end-effector
  positioning error to "less than half of a centimeter".
- `FACT`: the paper cites pose error above half a cubie size (1.9 cm cubies) as a cause of failure.

**General methods** (abstracts read):
- `FACT`: ANCSH (Li et al., arXiv 1912.11913) estimates part poses and joint states of articulated objects from one
  depth image.
- `FACT`: FoundationPose (Wen et al., arXiv 2312.08344) does 6D pose estimation and tracking of novel objects from a
  CAD model or reference images. It was trained on large-scale synthetic data.
- `INFERENCE`: neither has been applied to a Rubik's cube in the sources found. A cube is an articulated object with
  one active revolute joint at a time, which fits the ANCSH framing. Within the project, MuJoCo provides the CAD model
  for model-based tracking.

## 4. Q3: occlusion, partial views and legality constraints

- `FACT`: **gripper and hand occlusion is rarely measured.**
  - OpenAI tests robustness with a blanket over the hand and cube, but reports no occlusion-specific vision metric.
  - CubeCV and Hack & Shutzberg note failures or data with hand occlusion.
  - Kasprzak's figures show a hand holding the cube, without a metric.
- `FACT`: **observability gates rather than inference.** Amiet et al. withhold oblique, truncated or poorly sampled
  faces (gate retention: visibility 92.4 %, validity 97.0 %). Unseen facelets are marked unknown, and missing facelets
  are filled by aggregating later views.
- `FACT`: **constraint-based completion.** Used by Ng (MAP under piece constraints) and by rubiks-color-resolver (legal
  cubie colour sets, forced counts). Kociemba's `verify()` supplies the group-level checks (twist, flip, parity).
- `FACT`: **temporal filtering.** OpenAI tracks angles with modulo-π/2 updates; a recurrent model was abandoned. FINGR
  reobserves when the state mismatches. No source found uses an explicit Bayesian or particle filter over legal cube
  states (section 9).
- `INFERENCE`: three facts together make partial visibility of the gripped faces less critical than it looks:
  1. a legal state is fully determined by its 20 movable cubies;
  2. each cubie shows 2–3 facelets on different faces;
  3. after a known single move, at most 20 facelets change, all on the turned layer and its ring.

  A post-turn check needs only enough visible facelets to tell the expected outcome from the plausible failures (no
  turn, ±90° error, wrong layer). This is a small hypothesis set and could be scored by likelihood.

## 5. Q4: sim-to-real for this perception

- `FACT` (OpenAI Table 2): without domain randomisation, real errors were 128.83° orientation, 69.40 mm position and
  85.33° top-face angle. The full model's were 7.81°, 6.47 mm and 15.92°. Higher ADR entropy *raised* simulation error
  but *lowered* real error (Table 5).
- `FACT` (OpenAI Appendix B.5, Table 11): the randomisations covered:
  - camera pose and field of view;
  - light count, intensity, position and spotlight angle;
  - material hue, saturation, value, glossiness and metallic;
  - post-processing (hue, contrast, bloom, grain and others);
  - image-level noise.
- `FACT` (Tobin et al., arXiv 1703.06907, abstract): a detector trained only on simulated RGB with random textures
  localised real objects to 1.5 cm and was robust to distractors and partial occlusion.
- `FACT` (Tremblay et al., DOPE, arXiv 1809.10790, abstract): combining domain-randomised and photorealistic synthetic
  data closed the reality gap for 6-DoF pose of known objects. Results were competitive with a network trained on real
  data.
- `FACT` (Garcia et al., arXiv 2307.15320, abstract): DR parameters were tuned on an offline *cube localisation* proxy
  task and transferred, with an average 93 % real success over manipulation tasks.
- `FACT` (Kasprzak; Liu et al.): classical colour pipelines degrade with lighting colour and drift unless they are
  calibrated or adapt online. Liu et al.'s online methods (97.6 %) beat their offline classifier (84–87 %).
- `UNVERIFIED` (search summary): DeXtreme (arXiv 2210.13702) uses three cameras and randomised lighting and camera
  pose for its pose estimator. The abstract confirms a vision pose estimator but gives no numbers.
- `INFERENCE`: G5 is simulation-only, so "sim-to-real" becomes **held-out rendering conditions** (lighting, sticker
  hue and gloss, camera pose jitter, noise). This matches task 6 of Phase 5. The OpenAI ratios (real / sim about
  1.2–2.5× for a domain-randomised model, about 30× without) mean that a perception result on one fixed render
  setting says little about robustness.

## 6. Q5: quantitative results usable for G5 acceptance

| Quantity | Value | Source, condition | Level |
|---|---|---|---|
| Facelet colour accuracy | 100 % indoor; 98.7 % outdoor (29 errors) | Amiet 2026; 2354 / 2264 labelled facelets; cube at rest | full text |
| Facelet colour accuracy | 97.63 % (DWLP); 84.5–87.2 % (offline ELM) | Liu 2019; 18,792 blocks; 5 lighting conditions | full text |
| Facelet colour accuracy | 94 % (87–97 % by lighting) | Ng c. 2012; 20 image pairs | full text |
| Error-free full-cube reads | 69 % of image pairs | Ng c. 2012 | full text |
| Complete, correct nets | 5/5 indoor; 3/5 outdoor (failures from locomotion); aggregated nets had no incorrect labels | Amiet 2026 | full text |
| Partial nets sound / exact | indoor 100 % / 77.6 %; outdoor 92.6 % / 69.7 % | Amiet 2026 | full text |
| Cube pose (real) | 6.24–7.61 mm; 7.48–8.93° | OpenAI 2019, Table 5 | full text |
| Cube pose (real) | median ≈ 2 cm, < 3° (≤ 2 m, 0.4 m cube) | Amiet 2026 | full text |
| Top-face angle (real) | 13.83–16.57° | OpenAI 2019, Table 5 | full text |
| Active-face angle (real) | 8.84–8.89° | OpenAI 2019, Table 22 | full text |
| Instrumented face angle | 5.90° mean (SD 7.61°), 12.5 Hz | OpenAI Giiker | full text |
| Latency | 90–100 ms full frame; 32–52 ms ROI (Pentium IV 2.4 GHz) | Kasprzak 2007 | full text |
| Latency | 1.3 s per frame; about 33 s per full scan | Amiet 2026, Jetson AGX Orin | full text |
| Latency | 7 ms CNN localisation forward pass | Hack & Shutzberg 2015 | full text |
| Pose rate | 500 fps | Higo et al. 2018 | news only |

`INFERENCE`: none of these numbers transfers directly:
- the cubes are different sizes;
- the scenes are real, while G5 is simulated;
- all except OpenAI's are static or hand-held cubes, not robot-occluded ones;
- the sample sizes are small (n = 10–20 trials or sequences).

They bracket what is achievable. They are not targets.

## 7. Implications for Rubiknetic G5

1. `PROPOSAL`: **a two-tier estimator.**
   - **(a) Colour-state acquisition** while the cube is held still. Per-facelet Lab mean with edge erosion. Then
     legality-constrained assignment: counts, centre consistency, legal cubie colour sets, then an independent
     twist/flip/parity check written in-house, not copied from GPL code.
   - **(b) Manipulation tracking.** Cube pose from geometry, and the turning layer's angle modulo 90° from the
     cubie-edge geometry. The logical state is updated only on a detected completed quarter turn.
   - **(c) A post-turn consistency check.** Score the visible facelets against a small set of hypotheses (expected
     move, no move, ±90° error, wrong layer). Output `UNKNOWN` or `REOBSERVE` below a confidence threshold. This
     follows the OpenAI tracking pattern and Amiet's gates.
2. `INFERENCE`: **centre-sticker symmetry matters only for the absolute face angle, not for colour state.** A
   quarter-turn count derived from the logical state replaces the absolute angle.

   `PROPOSAL`, for user decision: if absolute centre orientation is ever needed, OpenAI's corner-cut centre sticker is
   the documented route. In Rubiknetic it would be a visual-only change, since stickers are physics-invariant (P-110).
3. `INFERENCE`: **the D21 rig fits the literature.** Its three fixed cameras resemble OpenAI's (left, right, top). D21
   measured visibility, not recognisability. A recognisability test on RGB renders at the intended resolution is the
   natural next feasibility experiment.
4. `INFERENCE`: **no simulator truth leakage.** MuJoCo segmentation renders (used in D21), geom IDs and `qpos` must
   not feed the G5 estimator. They may be used only to make audit labels. This applies the `docs/SYSTEM_ARCHITECTURE.md`
   rule to rendering.
5. `PROPOSAL`: **candidate G5 metrics**, with thresholds to be pre-registered by the user, not taken from this note:
   - per-facelet accuracy on facelets the estimator *chose to report*, plus the abstention rate;
   - the **confident-wrong** rate for the full state after legality resolution. The literature suggests this must be
     zero for planning, because one wrong facelet makes the state illegal or wrong. Report it with an exact binomial
     upper bound;
   - missed-rotation, slip and ±90° detection rates on injected failures;
   - layer-angle error during a turn, compared with the controller's alignment tolerance;
   - cube pose error;
   - per-frame latency on the CPU-only headless setup.

   All of these on held-out lighting, materials and initial poses (Phase 5 task 6).
6. `INFERENCE`: **learned models are optional for G5.** No source showed a learned colour classifier clearly beating
   calibrated classical classification plus constraints. In simulation, colour is controlled, so classical methods
   plus randomised held-out lighting are a cheaper first falsifiable step. A learned pose or angle estimator would add
   a training-data and dependency cost, under the project's CPU-only constraint.

## 8. Source register

The URL / DOI column gives the exact addresses opened in this session (2026-11-28). Where a DOI is given, the column says
whether the DOI itself or only its Crossref record was opened.

| # | System / method | URL / DOI (as opened) | Approach | Sensors | Occlusion handling | Reported accuracy | Verification | Code / licence |
|---|---|---|---|---|---|---|---|---|
| 1 | OpenAI 2019, arXiv 1910.07113 | https://arxiv.org/abs/1910.07113 (abstract); https://ar5iv.labs.arxiv.org/html/1910.07113 (full text) | ResNet50 × 3 views; pose + face angles (binned); ADR; state tracked from known start | 3 RGB Basler; Giiker cube | Top face chosen as rarely occluded; blanket robustness test | Real: 6.2–7.6 mm, 7.5–8.9°, top face 13.8–16.6°, active 8.8° | full text | none found |
| 2 | Amiet et al. 2026, arXiv 2610.24610 | https://arxiv.org/abs/2610.24610 (abstract); https://arxiv.org/html/2610.24610 (full text); https://leggedrobotics.github.io/rubik-skills/ (project page) | SAM 3 + RANSAC/ICP pose; Lab k-NN facelets; multi-view aggregation; centre gate | ZED X Mini RGB-D | Visibility / validity gates; unknown facelets; aggregation | Facelets 98.7–100 %; pose ≈ 2 cm, < 3° | full text | project page links "Code"; licence not shown |
| 3 | Kasprzak et al. 2007, MGV 16 | https://www.ia.pw.edu.pl/~wkasprza/PAP/MGV_16_2007_451.pdf (author PDF, full text). No DOI found; none is printed in the PDF | YUV normalisation; interval colour classes; moment-based cells; single-view pose | Fixed + eye-in-hand CCD | None (≤ 3 faces per view) | None; 32–100 ms per frame | full text | none |
| 4 | Ng c. 2012 (Stanford report) | https://stacks.stanford.edu/file/druid:yj296hj2790/Ng_Rubiks%20Cube_Reconstruction_from_Images.pdf | YUV normalisation; MAP 9×9×9; piece-constraint maximisation; 2 views | Still camera | None | 94 % facelets; 69 % error-free | full text | none |
| 5 | Liu et al. 2019, arXiv 1901.03470 | https://ar5iv.labs.arxiv.org/html/1901.03470 (full text; the arXiv abstract page was not opened separately) | HSV histograms; ELM (offline); centre-seeded label propagation (online) | Robot camera, 640×480 | n/a | 97.63 % (DWLP) | full text | none found |
| 6 | Hack & Shutzberg 2015 (CS231n) | https://cs231n.stanford.edu/reports/2015/pdfs/jaykevin_final.pdf; code: https://github.com/jayhack/ConvCube | CNN localisation; SLIC + RF; homography; SVM colour | Laptop webcam | Hand-occluded training data | 92 % superpixel piece classification (not colour) | full text | no licence seen |
| 7 | FINGR 2026, arXiv 2609.33973 | https://arxiv.org/abs/2609.33973 (abstract); https://arxiv.org/html/2609.33973 (full text) | Flow policy; cubie poses from coded markers; reobservation on mismatch | Multi-view + markers; tactile | Not addressed | No perception metrics; 181/185 planned turns | full text | not checked |
| 8 | Rubikon 2025, arXiv 2503.12619 | https://arxiv.org/html/2503.12619v1 (full text, first ~100k of ~112k characters) | ArUco per facelet; move templates | Camera | Not addressed | None | full text | not checked |
| 9 | Yang et al. 2020/2022, arXiv 2202.07074 | https://arxiv.org/abs/2202.07074 (abstract); https://ar5iv.labs.arxiv.org/html/2202.07074 (full text) | Benchmark; head-camera pose; pre-touch sensing | PR2 head camera; ToF | n/a | < 0.5 cm EE error with pre-touch | full text | not checked |
| 10 | dwalton76/rubiks-color-resolver | https://github.com/dwalton76/rubiks-color-resolver; https://raw.githubusercontent.com/dwalton76/rubiks-color-resolver/master/rubikscolorresolver/solver.py; https://raw.githubusercontent.com/dwalton76/rubiks-color-resolver/master/rubikscolorresolver/color.py | Lab, Euclidean; legal corner/edge sets; TSP | RGB input | n/a | None | code | MIT |
| 11 | hkociemba/RubiksCube-TwophaseSolver | https://github.com/hkociemba/RubiksCube-TwophaseSolver; https://raw.githubusercontent.com/hkociemba/RubiksCube-TwophaseSolver/master/cubie.py; https://raw.githubusercontent.com/hkociemba/RubiksCube-TwophaseSolver/master/package_src/twophase/vision2.py | HSV thresholds per face; `verify()` twist/flip/parity | Webcam | n/a | None | code | GPL-3.0 |
| 12 | kkoomen/qbr | https://github.com/kkoomen/qbr | Webcam scanner, calibration mode | Webcam | n/a | None | README | MIT |
| 13 | dualarm-cube (UIUC 2026) | https://dualarm-cube.github.io/; https://github.com/dualarm-cube/cube-solver | YOLOv8-nano stickers + k-NN colour; 5 poses fused | USB 1080p | "Partly hidden stickers are still found" | None | README / page | MIT |
| 14 | CubeLabsNZ/CubeCV | https://github.com/CubeLabsNZ/CubeCV | DINO + LangSAM; classical reading | Video | Hand occlusion breaks lines | None | README | not shown |
| 15 | Higo et al. IROS 2018 | DOI 10.1109/IROS.2018.8593538 (Crossref record opened: https://api.crossref.org/works/10.1109%2FIROS.2018.8593538); news: https://www.techbriefs.com/component/content/article/33053-three-fingered-robot-hand-could-master-rubik-s-cube?m=1432 | High-speed vision, cube centroid and angle | 500 fps camera | unknown | unknown | metadata + news | n/a |
| 16 | Zieliński et al. 2007, Industrial Robot 34(5) | DOI 10.1108/01439910710774377 (Crossref record opened: https://api.crossref.org/works/10.1108%2F01439910710774377) | Two-arm MRROC++ benchmark; visual servoing | Cameras, F/T | n/a | Visual servoing only with slow hand-over | abstract | n/a |
| 17 | Chen et al. CCDC 2023 | DOI 10.1109/CCDC58219.2023.10326999 (https://doi.org/10.1109/CCDC58219.2023.10326999 redirected to IEEE Xplore, which was not opened; Crossref record opened: https://api.crossref.org/works/10.1109/CCDC58219.2023.10326999) | Dual-arm solver (seed item 14) | unknown | unknown | unknown | metadata only (pp. 4301–4305) | n/a |
| 18 | MIT Katz & Di Carlo 2018 | https://meche.mit.edu/node/1952 (MIT News article) | Two webcams; per-piece colour | Webcams | n/a | 0.38 s including vision | news | n/a |
| 19 | Tobin et al. 2017, arXiv 1703.06907 | https://arxiv.org/abs/1703.06907 | Domain randomisation | RGB | Robust to partial occlusion | 1.5 cm localisation | abstract | n/a |
| 20 | Tremblay et al. 2018, arXiv 1809.10790 | https://arxiv.org/abs/1809.10790 | DR + photorealistic synthetic data (DOPE) | RGB | n/a | Competitive with real-trained | abstract | n/a |
| 21 | Garcia et al. 2023, arXiv 2307.15320 | https://arxiv.org/abs/2307.15320 | DR tuned on cube-localisation proxy | RGB | n/a | 93 % average real task success | abstract | n/a |
| 22 | Li et al. 2020, arXiv 1912.11913 (ANCSH) | https://arxiv.org/abs/1912.11913 | Articulated part pose + joint state | Depth | n/a | not read | abstract | n/a |
| 23 | Wen et al. 2024, arXiv 2312.08344 (FoundationPose) | https://arxiv.org/abs/2312.08344 | Novel-object 6D pose estimation and tracking | (not stated in abstract) | n/a | not read | abstract | arXiv page CC BY 4.0 (paper); code licence not checked |
| 24 | OpenAI 2018, arXiv 1808.00177 | https://arxiv.org/abs/1808.00177 | Vision-based in-hand reorientation, DR | not stated in abstract | n/a | not read | abstract | n/a |
| 25 | Handa et al. 2022, arXiv 2210.13702 (DeXtreme) | https://arxiv.org/abs/2210.13702 | Vision pose estimator for in-hand reorientation | "affordable cameras" | n/a | no numbers in abstract | abstract | n/a |

**URLs of unverified items** (not counted as sources; these addresses appeared in search results, and the outcome of
any fetch attempt is noted):
- Rethink Robotics Baxter wiki: http://sdk.rethinkrobotics.com/wiki/Baxter_Solves_Rubiks_Cube (DNS failure; an
  archive.org copy could not be fetched).
- "Robust Rubik's Cube Detection Using Hough Transform and Advanced Clustering Functions":
  https://www.scientific.net/AMM.613.253 (HTTP 403).
- CubeBench: https://arxiv.org/pdf/2512.23328 (not opened).
- "Thinking with Patterns": https://arxiv.org/pdf/2605.16848 (not opened).
- TOKUFASTbot, for example
  https://www.livescience.com/technology/robotics/this-ai-powered-robot-has-worked-out-how-to-solve-a-rubiks-cube-in-just-0305-seconds
  (not opened).
- MIT robot camera model and painted faces (search summaries of news coverage, for example
  https://techcrunch.com/2018/03/07/this-robot-can-solve-a-rubiks-cube-in-38-seconds; not opened).
- DeXtreme "three cameras" (search summary of
  https://developer.nvidia.com/blog/reinforcing-the-value-of-simulation-by-teaching-dexterity-to-a-real-robot-hand;
  not opened).
- GitHub projects (not opened):
  - https://github.com/Hemant-Mulchandani/Rubiks-Cube-Face-Detection-Model
  - https://github.com/MihailTs/Rubic-s-cube-solver-with-computer-vision
  - https://github.com/akash77new-cmyk/Rubik-s-Cube-Solver/pull/2

**Count:**
- **Full text: 9.** Sources 1–9.
- **Code read: 2.** Sources 10–11.
- **README / project page: 3.** Sources 12–14.
- **Abstract only: 8.** Sources 16 and 19–25.
- **Metadata or news only: 3.** Sources 15, 17 and 18.
- **Unverified mentions (not counted): 5.** See section 9.

## 9. Empty or unproductive searches, and items not opened

- **No source found** for:
  - a Bayesian, HMM or particle filter over legal Rubik's cube states;
  - facelet recognition under robot-gripper (as opposed to human-hand) occlusion;
  - a learned sticker-colour classifier trained on synthetic or domain-randomised renders;
  - any MuJoCo-based Rubik's cube perception pipeline.
- **Seed item 14 (CCDC 2023):** no abstract was available through Crossref; IEEE Xplore was not opened. Its vision
  method is unknown.
- **Higo et al. IROS 2018:** the full text was not found; only Crossref metadata and news coverage were read.
- **`UNVERIFIED` and not opened:**
  - Rethink Robotics Baxter wiki (DNS failure; archive fetch blocked);
  - "Robust Rubik's Cube Detection Using Hough Transform and Advanced Clustering Functions", Applied Mechanics and
    Materials 613 (HTTP 403);
  - CubeBench (arXiv 2512.23328) and "Thinking with Patterns" (arXiv 2605.16848), which a search summary reported
    impute unknown stickers;
  - TOKUFASTbot coverage;
  - the Hemant-Mulchandani, MihailTs and akash77new-cmyk GitHub projects, which report learned-classifier accuracies
    in search snippets only.
- **Amiet et al.** cite Ďurovský and Chalise et al. as prior work; neither was found or opened.

## 10. Limits

- A first-pass search in one session using web search and page fetching. It is not a systematic review, and paywalled
  IEEE and Springer full texts were not read.
- Full-text reads went through an extraction tool for HTML (ar5iv / arXiv HTML) and through the PDF reader for PDFs.
  Numbers were taken from the extracted tables; they were not re-derived.
- Most results are on real images of real cubes, mostly at rest or hand-held. Only OpenAI reports vision during robot
  manipulation, and it does not estimate colour. The transfer to a simulated, robot-occluded, two-arm scene is
  `INFERENCE`.
- Licences were checked only for repositories that might be reused. The arXiv page licence for FoundationPose covers
  the paper, not its code.
- All `PROPOSAL` items need user approval. Thresholds for G5 belong in a pre-registration and are not set here.
