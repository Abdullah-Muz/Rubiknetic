# Novelty check for an M7 / G1 publication: literature search (2026-11-26)

**Status.** A research note, done by the main session at the user's request ("can you confirm with a literature
search"). It is a first-pass search for a possible paper, not a systematic review. Access date for every source:
2026-11-26.

**Labels:**
- `FACT`: read directly (arXiv abstract page, GitHub README) or already on record in the repository as read.
- `UNVERIFIED`: search-result summary only, page not read.
- `INFERENCE`: the main session's reading.

## Question
Is the project's work novel? In particular:
- the contact-driven simulated Rubik's cube (M7);
- the pre-registered, frozen, zero-tolerance, held-out validation method with independent reviews.

## Findings

### 1. Contact-driven simulated Rubik's cubes already exist
- **OpenAI, "Solving Rubik's Cube with a Robot Hand" (arXiv 1910.07113, 2019).**
  - `FACT` (on record: `docs/research/TURNING_TORQUE_FINDINGS.md`, PDF read 2026-11-21): the cube model used bevels of
    1.425 mm on 1.9 cm cubelets, with "very rudimentary dynamics calibration".
  - `UNVERIFIED` (search summary): the model has 26 convex cubelets, and face rotation is driven by contact and
    friction rather than explicit joints.
- **vctr-dng/manip-rubiks** (GitHub). `UNVERIFIED` (search summary): a 2×2×2 cube in MuJoCo, built as a core plus
  eight box cubies on ball joints at the cube centre, used for tactile manipulation with a dexterous hand.
- **Li et al., arXiv 1907.11388 (2019).** MuJoCo cube solving with a dexterous hand (`FACT` on record: no torque or
  friction values).
- `INFERENCE`: **a contact-driven cube in MuJoCo is not novel.** OpenAI's bevelled cubelets are close in kind to M7's
  geometry. M7's distinguishing features are what has been validated about it, not its construction.

### 2. Pre-registration in robotics exists, mostly for human-subject studies and small projects
- **Human-robot interaction studies routinely pre-register on OSF.** `UNVERIFIED` (search summaries): an arXiv
  human-robot teaming study (2311.00785), and two studies of how people interpret an RL robot's learning.
- **henrikhalasz/robot-learning** (GitHub, created 2026-10-22). `FACT` (README read): experiments on two SO-101 arms,
  where "each README holds the prediction, written before the run". A personal learning project ("The first builds
  are on their way"), 0 stars.
- **Alt et al., "Open, Reproducible and Trustworthy Robot-Based Experiments with Virtual Labs and Digital-Twin-Based
  Execution Tracing"** (arXiv 2508.11406, 2025-08-15). `FACT` (abstract read):
  - semantic execution tracing and a cloud platform for replicating robot task executions;
  - "deterministic execution";
  - aimed at reproducible robot-driven science.

  `UNVERIFIED` (search summary): the paper argues that robot protocols can be pre-registered.
- **Luminous-Dynamics GitHub issues.** `UNVERIFIED` (search summary): proposals for "preregistered" thresholds on
  contact benchmarks (for example ≥ 95 % decision agreement). These are proposals, not completed studies.

### 3. Validating simulators and auditing contact artefacts is an active topic
- **Zhou et al., "When the Simulator Fails, Not the Policy: Auditing Contact Artifacts in Simulated Robot
  Benchmarks"** (arXiv 2610.41857; v1 2026-10-30, v2 2026-11-22). `FACT` (abstract read):
  - SimuGuard records state at every physics step and flags contact artefacts;
  - it replays episodes "bit for bit" and reruns them with one solver parameter changed;
  - it traces failures to a false PhysX contact, and with the repaired engine the model ranking follows the
    real-robot ranking.

  `INFERENCE`: this is close in spirit to M7's self-check (bit-exact reproduction) and E1-7 (one-factor sensitivity),
  and to D14's diagnosis of the chamfer catch as a contact artefact. It is an audit of benchmarks, not a
  pre-registered validation of an object model.
- **Real-to-sim validation.** `UNVERIFIED` (search summaries): SIMPLER (real–sim policy correlation), a 2019 CSIRO
  physics-engine benchmark against real ground truth (arXiv 1911.01557), Genie Sim (frozen configurations), and
  held-out designs in CALVIN and RoboDyna.

### 4. Formal credibility frameworks for computational models are established in engineering
- **ASME V&V 40** (medical devices) and **NASA-STD-7009 / NASA-HDBK-7009** (aerospace). Both build on Sandia's PCMM.
- `UNVERIFIED` (search summaries of the standards and NAFEMS):
  - risk-informed credibility assessment, where "the level of evidence should be commensurate with the risk";
  - credibility is "the trust, obtained through the collection of evidence, in the predictive capability of a
    computational model";
  - ASME V&V 40 is not a step-by-step or quantitative method.
- `INFERENCE`: **rigorous validation of a computational model is an established discipline.** Its central ideas
  predate this project: context of use, evidence matched to risk, and verification, validation and uncertainty
  quantification.

### 5. Reproducibility gaps in robotics are widely recognised
- `UNVERIFIED` (search summaries):
  - a 2025 Nature Machine Intelligence piece, "Towards reproducible robotics research";
  - a CoRL 2020 workshop paper on deep RL irreproducibility (variance, unreported hyperparameters);
  - a Frontiers review noting reproducibility "is not a mainstream practice" in AI and robotics.

## Conclusion (`INFERENCE`)
1. **The simulated cube is not novel in kind.** OpenAI's contact-driven, bevelled cubelet cube predates it. M7's
   contribution is a validated configuration (rounded edges, magnetic detents, NoSlip) and its documented failure
   modes, not a new kind of model.
2. **The validation method is not an invention, and each part has precedent:**
   - pre-registration (human-subject robotics and HRI, small robot-learning projects, proposals);
   - simulation V&V and credibility frameworks (ASME V&V 40, NASA-STD-7009);
   - bit-exact replay and one-parameter sensitivity audits of contact artefacts (SimuGuard, 2026);
   - held-out evaluation (ML benchmarks).
3. **No source found applies all of these together to a simulated manipulable object.** That means pre-registered,
   frozen criteria, one-shot zero-tolerance scoring on held-out seeds, bit-exact self-checks against earlier records,
   independent review until no changes are required, and negative results kept. This combination appears to be
   **uncommon**, and is a fair methodological contribution, framed as *applying* established clinical-trial,
   V&V and ML evaluation practice to robotics simulation models.
4. **A paper should not claim "first"** without a systematic search (Google Scholar, IEEE Xplore, the ACM DL, and
   recent ICRA, IROS, RSS and CoRL proceedings) and a reading of the full texts above, especially OpenAI's cube model
   and SimuGuard. It should cite the V&V standards and SimuGuard as the nearest related work.

## Sources
| Source | URL | Read |
|---|---|---|
| OpenAI, Solving Rubik's Cube with a Robot Hand (2019) | https://arxiv.org/abs/1910.07113 | `FACT` on record (2026-11-21) for the bevel; modelling detail `UNVERIFIED` |
| Li et al., Learning to Solve a Rubik's Cube with a Dexterous Hand (2019) | https://arxiv.org/abs/1907.11388 | on record |
| vctr-dng/manip-rubiks | https://github.com/vctr-dng/manip-rubiks | `UNVERIFIED` |
| henrikhalasz/robot-learning | https://github.com/henrikhalasz/robot-learning | `FACT` (README) |
| Alt et al., arXiv 2508.11406 | https://arxiv.org/abs/2508.11406 | `FACT` (abstract) |
| Zhou et al., arXiv 2610.41857 (SimuGuard) | https://arxiv.org/abs/2610.41857 | `FACT` (abstract) |
| Human-robot teaming, preregistered | https://arxiv.org/pdf/2311.00785 | `UNVERIFIED` |
| ASME V&V 40 summary (NIH IMAG wiki) | https://www.imagwiki.nibib.nih.gov/sites/default/files/asme_vv_40_model_simulation_standard.pdf | `UNVERIFIED` |
| NASA-HDBK-7009 | https://standards.nasa.gov/sites/default/files/standards/NASA/A/0/Historical/nasa-hdbk-7009.pdf | `UNVERIFIED` |
| NAFEMS on V&V credibility | https://nafems.org/blog/posts/credibility-is-everything-or-how-to-get-the-most-from-verification-and-validation | `UNVERIFIED` |
| SIMPLER | https://simpler-env.github.io/simpler.pdf | `UNVERIFIED` |
| CSIRO physics-engine validation (RA-L 2019) | https://arxiv.org/abs/1911.01557 | `UNVERIFIED` |
| Towards reproducible robotics research (Nat. Mach. Intell. 2025) | https://www.nature.com/articles/s42256-025-01114-7 | `UNVERIFIED` |
| Reproducibility of deep RL in robotics (CoRL 2020 workshop) | http://proceedings.mlr.press/v100/lynnerup20a/lynnerup20a.pdf | `UNVERIFIED` |
