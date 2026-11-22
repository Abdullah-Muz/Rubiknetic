# Real cube turning torque and robot torque capacity (findings, 2026-11-21)

> **Status:** research report; unscored; no simulation. A subagent compiled it; all sources were accessed
> 2026-11-21. The main session re-read two sources and confirmed them:
> - the Gripper G2 specification page: "10-50N" gripping force, 0.22 / 0.5 N·m motor;
> - the xarm_ros2 `joint_limits.yaml` entry for joint 7: 30.6 N·m = 0.12 × 100 × 2.55, an overload limit.
>
> A second subagent fact-checked the remaining claims the same day. Applied corrections: the 0.37–0.46 N·m row (7–23×;
> 13–27 N), the Yang et al. and Ben Katz wording, and Zieliński 2005, which does not concern cubes. Three sources
> could not be reached for re-checking and rest on earlier verification or snippets: the TwistyPuzzles 0.09 N·m page
> (403; a snippet agrees), the Q-Bot page body, and UFACTORY forum thread 3531. Search summaries say that thread
> disputed "continuous" versus "maximum" and which joints 7 N·m applies to, before a reply attributed to staff
> confirmed "cont torque". Re-read it before relying on the 7 N·m figure.
>
> It also checked the arithmetic τ = μFa: for 1 N·m, 35 N at μ 0.5 and 58 N at μ 0.3. Downloaded PDFs stayed in the
> scratchpad and are not committed.
>
> **Headline (INFERENCE).** Against published evidence, a peak turner torque of 0.14 N·m is realistic, 0.4 N·m is
> high, and 1.0 N·m is far too high. The only verified figure for a standard cube is 0.09 N·m. A G2 grasp on opposite
> layer faces carries 1 N·m only at μ ≥ 0.35 with the G2's maximum 50 N grip. The arm's wrist (7 N·m continuous,
> reported on a forum) is not the limit. The 1 N·m turner limit is therefore a ceiling, not a realism yardstick. Any
> realism threshold (for example about 0.2 N·m, with 0.45–0.5 N·m as a warning level) is the user's decision.

---

# Turning torque: real cubes, magnets, xArm7 J7 and gripper grasp capacity (web and repo research, no simulation)

Access date for every web source: **2026-11-21** unless stated. Labels: **FACT** (named source, read by me today, or
on record in the repo as verified, marked "on record"), **INFERENCE** (mine), **UNVERIFIED** (search snippet only,
page not readable), **ASSUMPTION**. Nothing below was simulated. No repo file was changed.

## 0. Already on record in the repo (not redone)
- `experiments/R1_real_cube_bench/LITERATURE.md`: 0.09 N·m for "a traditional Rubiks Cube" (Oskar van Deventer,
  TwistyPuzzles museum *Superclick Cube* entry, archived 2022-05-16, verified 2026-11-19; Superclick itself 2.7 N·m;
  no method, cube model or date). 0.05 / 0.02 N·m speedcube figures from speedsolving thread 76309 are snippet-only.
  16 CFR §1500.53(e) toy torque test 0.45 N·m (a robustness load, not a turning torque), verified. Giant 0.4 m cube
  6.0 N·m breakaway / 4.0 N·m running (arXiv 2610.24610), not transferable.
- `docs/research/PHASE_2_ROBOT_MODEL_FINDINGS.md` §3, §7, §8: no torque table in any official spec page or manual;
  URDF max effort J7 30.6 N·m (overload-derived); UFACTORY forum thread 3531 (archived 2024-02-28): continuous
  J6/J7 7 N·m for xArm 5/6/7, "peak torque is 2-2.5 times". G2 10–50 N, original gripper 30 N.
- `docs/research/MECHANICAL_FEASIBILITY_ASSESSMENT.md` §3: grasp capacity μFa (friction only) to F(b + μa); 0.17–4.4
  N·m over 10–50 N, μ 0.3–1.0; τ_req bracket 0.03–0.6 N·m is an ASSUMPTION.
- ER9 `SUMMARY.md`: E1-2 turner median L0 0.144 N·m; full run medians L0 0.203, C52 0.645, W3 1.0 N·m; W3 at the
  1 N·m limit in 771 / 1,376 moves; stall at about 6.7° for about 0.1 s; L0 peak in the same replay 0.46 N·m.

## (a) Measured or stated real 3×3 turning torques

| # | Figure | What kind | Cube; magnets; tension | Method | Source | Label |
|---|---|---|---|---|---|---|
| 1 | **0.09 N·m** | "torque needed to turn one face" (breakaway or running not stated) | "traditional Rubiks Cube", model not named; presumably non-magnetic | not stated | TwistyPuzzles museum, Superclick Cube (archived) | FACT (on record, verified 2026-11-19; not re-read today, archive unreachable by my fetch tool) |
| 2 | 2.7 N·m | same, for the Superclick Cube | 60 mm novelty puzzle with sixteen 12.7 mm spherical magnets | not stated | same | FACT (on record). Not a speedcube |
| 3 | 0.05 N·m measured; 0.02 N·m claimed | informal | speedcube "set up to be sticky" | not stated | speedsolving.com thread 76309 (2020) | UNVERIFIED (403 again today) |
| 4 | **0.52 kg** hanging mass, highest of 3 trials | breakaway ("slowly increased the weight … until the cube turned") | not stated; cube clamped so one side turns | string tied to the cube, bag of weights (potatoes) | Q-Bot Instructables, published 2019-03-12 | UNVERIFIED for the numbers (snippet only; page body not readable). FACT that the page has a step "Picking the Right Motors" saying "no manufacturer of Rubik's cubes gives a torque rating" (read in the page's own metadata) |
| 5 | Steppers "able of applying up to 0.4 Nm, which is probably an overkill" | motor choice | as #4 | — | same | UNVERIFIED (snippet) |
| 6 | 0.05 N·m speedcubes; "worst case 0.5 N-M for original cubes" | **estimates**, no source given | — | none | Lathi, Choi, Uruchima, ECE 445 Design Document, UIUC, 29 Sep 2022 | FACT (text read): they are estimates, not measurements |
| 7 | test threshold 0.785 N at 127.3 mm (= 0.1 N·m) | a planned force-gauge test, **no result reported**; motors then failed to turn the face | **giant** cube | force gauge at face edge, adjacent face misaligned in steps | Winkelmann, Bui, Jiang, ECE 445 Final Report, UIUC, 6 May 2015 | FACT; not transferable to 57 mm |
| 8 | none (method only) | — | not stated; margin for "stronger magnets or stiffer" cubes | luggage scale on a string × lever | Twistopher-2 README (GitHub, Eldho-546), undated | FACT: no number given; designed for about 2× the estimate |
| 9 | none | — | "one of the cheapest available" speedcubes (a Yulong, per the product link) tightened "really tight" | — | Ben Katz, "The Rubik's Contraption", 2018-03-07 | FACT: no torque; ~10 ms per 90° move |
| 10 | none (motor only) | — | — | "torque required … is low", NEMA 17, 3.2 kg-cm holding | Marjerie Suresh, project page (SSNCE 2019) | FACT |

INFERENCE:
- **The only verified number for a standard-size cube is still 0.09 N·m**, one undocumented measurement.
- **#4, if the snippet is right:** 0.52 kg × 9.81 = 5.1 N. The lever is not stated. At 20–40 mm (string near the
  layer edge of a 57 mm cube) that is **about 0.10–0.20 N·m breakaway**. This agrees with #1 to within about 2×.
- **Hobby motor sizing** (0.3–0.4 N·m called "low need" or "overkill") is a weak upper bound. It agrees with
  breakaway torques well below about 0.3 N·m for the cubes those builders used.
- **What none of the sources give:** a breakaway/running split, a torque trace over the turn angle, the tension
  setting, or a magnetic/non-magnetic pairing. Magnetic or not is unstated in all of them.

## (b) Magnet effect
**No source quantifies it.** Nothing was found in English or Chinese web sources, patents, retailer pages or
reviews that compares the same cube with and without magnets, or gives detent torque in physical units.
- FACT (on record): GAN patent US11484780B1 says, qualitatively, that stronger positioning magnets give larger
  starting resistance.
- UNVERIFIED (snippet, Zhihu article p/469625564): magnets that are too strong raise the starting resistance,
  because a turn must first overcome the magnetic hold. Strength is adjustable by "gears" (levels).
- FACT (on record): manufacturers give magnet strength only as levels.
- INFERENCE: the direction is clear: magnets add breakaway torque and a detent profile. The size is unknown.
  The R1 bench protocol (magnets in vs removed) is still the only route.

## (c) Robot capacity

### xArm7 joint 7 (wrist roll)
| Quantity | Value | Source | Label |
|---|---|---|---|
| Joint torque on official spec page | **none listed** (payload 3.5 kg, 180°/s, J7 ±360°) | docs.xarm.ufactory.cc, *8. Technical Specifications* | FACT (re-read today) |
| J7 max effort, pre-1305 | 30.6 N·m = 0.12 (Kt) × 100 (gear ratio) × 2.55 (overload limit) | xarm_ros2 `config/xarm7/joint_limits.yaml` (humble) | FACT (re-read today); overload, not continuous |
| J7 max effort, ≥1305 | 30.6 N·m = 0.15 × 100 × 2.04 | xarm_ros2 `joint_limits_1305.yaml` | FACT (re-read today) |
| J7 continuous | 7 N·m; peak "2-2.5 times" (14–17.5 N·m) | UFACTORY forum thread 3531, archived 2024-02-28 | FACT (on record); forum poster, staff status not confirmed |
| Payload | 3.5 kg | spec page | FACT |

### Gripper grasp
| Gripper | Grip force | Other | Source | Label |
|---|---|---|---|---|
| **Gripper G2 (AG1200)** | **10–50 N** | stroke 84 ± 1 mm; payload 5 kg; 820 g; motor rated 0.22 / peak 0.5 N·m (gripper motor, not grasp torque); programmable speed, position, torque; position feedback only | docs.accessories.ufactory.cc, *xArm Gripper G2 – 6. Technical Specifications* (no date shown) | FACT (read today) |
| Original xArm Gripper | max 30 N | 84 mm | docs.xarm.ufactory.cc spec page; UFACTORY brochure (2022 file) | FACT (read today) |

ASSUMPTIONS: **F** is the normal force at each jaw (equal and opposite). Pad–cube friction **μ = 0.3–1.0, central 0.5**
(no measured value for silicone or rubber on ABS was found; a search found only generic tables). Cube edge
a = 57 mm.

**Case 1: coaxial layer grasp** (the repo's design). The jaws squeeze two opposite side faces of the layer, and the
turn axis is the face normal (J7). Friction-only capacity is τ = 2·μF·(a/2) = **μFa** (INFERENCE; same formula as
the feasibility report):

| F (N) | μ = 0.3 | μ = 0.5 | μ = 0.8 | μ = 1.0 |
|---|---|---|---|---|
| 10 (G2 min) | 0.17 | 0.29 | 0.46 | 0.57 |
| 30 (original max) | 0.51 | 0.86 | 1.37 | 1.71 |
| 50 (G2 max) | 0.86 | 1.43 | 2.28 | 2.85 |

Grip force needed for a given torque, F = τ/(μa):

| τ | μ = 0.3 | μ = 0.5 | μ = 1.0 |
|---|---|---|---|
| 0.14 N·m | 8 N | 5 N | 2.5 N |
| 0.40 N·m | 23 N | 14 N | 7 N |
| 1.0 N·m | **58 N (above G2 max)** | 35 N | 17.5 N |

A rigid-pad normal-force couple (F·b) can add up to F·b, but only if the jaws are not back-driven. That is unverified.
The stabilizer must react the same torque.

**Case 2: torque about the grasp axis itself** (the turn axis passes through both contact centres). Only
torsional friction of the contact patches acts. For a uniform circular patch of radius R it is about (2/3)μFR per
jaw, (4/3)μFR for both (INFERENCE). With R ≤ 8 mm (G2 finger width 16 mm) the capacity is ≤ 0.11 N·m at
10 N / μ 1.0 and **≤ 0.27 N·m at 50 N / μ 0.5**. That is too little for 0.4 or 1.0 N·m. Real soft-pad patches are
usually smaller than the full finger width, which lowers these figures further.

## (d) Robot-hand literature
- **OpenAI 2019 (arXiv 1910.07113), PDF text read today. FACT: no cube torque figure appears.** The hardware text
  says "torque limits were minimized such that the hand can reliably achieve a series of commanded positions",
  tuned by hand to avoid breakage. The cube model used bevels of 1.425 mm on 1.9 cm cubelets, "very rudimentary
  dynamics calibration", and randomized cube damping and friction loss under ADR. The modified cube was a Giiker
  cube with new encoders. Its face-turn resistance is not reported.
- **Li et al. 2019, arXiv 1907.11388** (Shadow hand, simulation only), PDF text read: no torque or friction value.
- **Sievers, Pitz, Bäuml 2022, arXiv 2204.03698:** whole-cube reorientation with a torque-controlled hand, not layer
  turning. The abstract has no torque value.
- **Yang et al., RA-L 2020 (arXiv 2202.07074)**, text read: a benchmark using a standard Hasbro Rubik's Cube
  (A9312, 5.7 cm), turned by the PR2's grippers. No torque or force values.
- **Zieliński et al. 2005 (RoMoCo'05; MRROC++)**, text read: the paper does not mention a Rubik's cube (its examples
  are milling, polishing, a crank, contour following, drawing and draughts), so it is the wrong source for the cube
  work. Force/torque sensing was used to
  avoid jamming (2007 paper, on record).
- Not read: Rigo/Higo et al., IROS 2018, DOI 10.1109/IROS.2018.8593538 (paywalled). FINGR, arXiv 2609.33973: the
  PDF is over the fetch size limit (abstract only, on record).
- INFERENCE: **no robot-hand paper found reports the torque it applied to turn a layer.**

## (e) INFERENCE: where the simulated peaks sit
Caveat: the real figures are quasi-static breakaway or "torque to turn" values. The simulated values are peaks
during a driven, position-controlled turn, so they include servo wind-up. A value of 1.0 is a clip and means "at
least 1.0".

| Simulated peak | vs real-cube evidence | vs J7 (7 N·m continuous; 30.6 N·m URDF) | vs G2 coaxial grasp (μFa) |
|---|---|---|---|
| **0.14 N·m** (L0 median) | **Within.** About 1.5× the 0.09 N·m figure; inside the Q-Bot-derived 0.10–0.20 N·m; 3–7× the unverified speedcube 0.02–0.05 N·m | 2 % of continuous | Easy: 5–8 N at μ 0.3–0.5, below the G2 minimum of 10 N |
| **0.37–0.46 N·m** (newer layouts) | **Above.** 4–5× the 0.09 N·m figure, 7–23× the speedcube claims; at the 0.45 N·m toy robustness load and the unsourced 0.5 N·m "worst case" estimate; near what hobby builders size motors for and call "overkill" | 5–7 % | Feasible: 13–27 N at μ 0.5–0.3. Not with a case-2 grasp |
| **1.0 N·m** (W3, at the limit) | **Far above.** 11× the 0.09 N·m figure, 20–50× the speedcube claims. Exceeded only by a deliberately clicky magnetic novelty puzzle (Superclick, 2.7 N·m) and giant cubes | 14 % of continuous; 3–7 % of peak or overload | **Marginal or slipping:** 35 N at μ 0.5 (70 % of G2 max; above the original gripper's 30 N); 58 N at μ 0.3 (above G2 max). The stabilizer must hold the same. Gripper squeeze at 35–50 N also loads the cube |

**What this means for the 1 N·m limit as a yardstick (INFERENCE):**
1. **The arm is not the constraint.** J7 has 7–30 N·m, so 1 N·m is a small fraction on either source.
2. **The binding constraints are the grasp and the cube.** 1 N·m sits at or past the G2 friction capacity for a
   plausible μ. It is also an order of magnitude above the only verified real-cube figure.
3. **So the 1 N·m limit is a generous rig ceiling, not a realism criterion.**
   - "Not reaching the limit" says little about realism.
   - "Reaching the limit" (W3: 771 moves) marks resistance that a real G2 grasp would likely not transmit without
     slip. No real 3×3 source supports it.
4. **A realism yardstick would sit much lower.**
   - Peaks of about 0.2 N·m or less: consistent with the evidence, within its large uncertainty.
   - About 0.45–0.5 N·m: an upper flag. It is the toy-standard load, the unsourced worst-case estimate, and the G2
     capacity at μ 0.3 with about 30 N.
   - This is a PROPOSAL only. Choosing a threshold is the user's decision.
5. **Every real figure is undocumented or snippet-only, so none can calibrate the model.** The R1 bench test
   (breakaway and running torque, magnets in and removed) remains the only way to pin these numbers down.

## (f) Unverified list (snippet only; not used as facts)
1. speedsolving.com thread 76309, "Torque on conventional cubes" (2020): 0.05 N·m measured on a sticky speedcube;
   0.02 N·m claim; a reply saying torque varies from face to face. 403 today.
2. Q-Bot Instructables (2019-03-12), step 2: "did the measurements three times and took the highest value, which
   gave 0.52 kg"; steppers "able of applying up to 0.4Nm, which is probably an overkill". Weights were potatoes in a
   bag, string tied to the cube. Step body not readable; a JSON API fetch was refused by the permission check and not
   attempted another way; hackster mirror 403.
3. Zhihu p/469625564 (MoYu tuning article): magnets too strong raise starting resistance; strength in levels.
4. eng-tips thread 450924, "Measure Rubik's Cube Torque" (2012-08-13): question only; replies not seen (403).
5. CSDN "GAN SG-1 review": "turning resistance reduced 30 %", no method (low credibility).
6. Rigo/Higo et al., IROS 2018 (paywalled): fingers positioned "to provide enough torque" (Gizmodo snippet); no
   value seen.

## Sources read today (2026-11-21)
| Source | URL | Author / publisher; date | Establishes |
|---|---|---|---|
| UIUC ECE 445 Final Report, "Robotic Rubik's Cube" | https://courses.grainger.illinois.edu/ece445/getfile.asp?id=6925 | Winkelmann, Bui, Jiang; 6 May 2015 | Giant cube; planned force-gauge test at 127.3 mm, 0.785 N threshold; motors failed; no measured value |
| UIUC ECE 445 Design Document, "Self Solving/Scrambling Rubik's Cube" | https://courses.grainger.illinois.edu/ece445/getfile.asp?id=20853 | Lathi, Choi, Uruchima; 29 Sep 2022 | Estimates 0.05 N·m (speedcubes) and 0.5 N·m worst case (original), unsourced |
| Twistopher-2 README | https://github.com/Eldho-546/Twistopher-2-Single-Motor-Cube-Solver | Eldho-546; undated | Luggage-scale method, no number; 2× margin; 3:1 gearing |
| Q-Bot Instructables (page metadata only) | https://www.instructables.com/Q-Bot-the-Open-Source-Rubiks-Cube-Solver/ | Instructables author; published 2019-03-12, modified 2020-07-21 | Step "Picking the Right Motors": no manufacturer torque rating; numbers unverified |
| "The Rubik's Contraption" | https://buildits-amk.pages.dev/posts/2018-03-07-the-rubik-s-contraption | Ben Katz (footer "© 2026 Ben Katz"; collaboration with "Jared"); 2018-03-07 | Cheap Yulong cube tightened "really tight"; ~10 ms per 90° move; no torque |
| Rubik's Cube Solver Bot | https://marjerie.github.io/projects/RCS | Marjerie Suresh; 2019 | "torque required … is low"; NEMA 17, 3.2 kg-cm |
| Solving Rubik's Cube with a Robot Hand | https://arxiv.org/pdf/1910.07113 | OpenAI (Akkaya et al.); 2019 | No torque figure; torque limits minimized by hand; model calibration rudimentary |
| Learning to Solve a Rubik's Cube with a Dexterous Hand | https://arxiv.org/abs/1907.11388 | Li, Xi, Fang, Xu, Meng; 26 Jul 2019 | No torque value |
| Learning Purely Tactile In-Hand Manipulation with a Torque-Controlled Hand | https://arxiv.org/abs/2204.03698 | Sievers, Pitz, Bäuml; Apr 2022 | Reorientation only; no torque value |
| Benchmarking Robot Manipulation with the Rubik's Cube | https://arxiv.org/pdf/2202.07074 | Yang, Lancaster, Srinivasa, Smith; RA-L 2020 | Hasbro A9312 cube, PR2 parallel grippers; no torque |
| Applications of MRROC++ Robot Programming Framework | https://www.ia.pw.edu.pl/~zielinsk/romoco05.pdf | Zieliński, Szynkiewicz, Winiarski; RoMoCo'05 | No cube torque values |
| Journal of Emerging Investigators, "Rubik's cube: What separates the fastest solvers from the rest?" | https://emerginginvestigators.org/articles/21-189 | Boyce, Storm; 24 Jul 2022 | No torque (negative check) |
| Mechanical Automation with Vision: A Design for Rubik's Cube Solver | https://arxiv.org/abs/2508.12469 | Chalise et al.; Aug 2025 | No torque (negative check) |
| Arduino forum, "Surrealistic Rubik's Cube robot" #16 | https://forum.arduino.cc/t/surrealistic-rubiks-cube-robot-auto-solver/185194/16 | Palliser; 28 Sep 2013 | Question only, no value |
| xArm Technical Specifications | https://docs.xarm.ufactory.cc/8.technical_specifications.html | UFACTORY | No joint torque; payload 3.5 kg; original gripper 30 N, 84 mm |
| xArm Gripper G2 Technical Specifications | https://docs.accessories.ufactory.cc/xArm_Gripper_G2/6.Technical_Specifications.html | UFACTORY; no date shown | G2 10–50 N, 84 ± 1 mm, 5 kg, 820 g, motor 0.22 / 0.5 N·m |
| xarm_ros2 joint limits (humble) | https://raw.githubusercontent.com/xArm-Developer/xarm_ros2/humble/xarm_description/config/xarm7/joint_limits.yaml and `.../joint_limits_1305.yaml` | UFACTORY (BSD-3) | J7 30.6 N·m with derivation |
| UFACTORY brochure (third-party host) | https://www.robotsepeti.com/Data/EditorFiles/urun%20resim/ufactory/UFACTORY-BROCHURE-EN.pdf | UFACTORY; file dated 2022-09-22 | Gripper 30 N, BIO 20 N; no joint torque |

Downloaded copies and extracted text were kept in the session scratchpad (`torque/dl/`) and are not in the repository.
