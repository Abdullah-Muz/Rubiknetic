# Gripper and Fingertip Design — Research Brief (not findings)

**Platform:** 2 × UFACTORY xArm7, MuJoCo.  
**Status:** No fingertip CAD selected, generated or validated.

## Research objective

Perform a literature-backed mechanical study to identify the simplest credible parallel-gripper and custom-fingertip arrangement supporting repeated, legal, **contact-driven** 3×3 Rubik's Cube face turns, stable cube holding, reorientation, and handoffs. Do **not** design geometry first and search for citations afterward.

## Functional requirements

- Both arms can potentially stabilize, reorient, turn, release and hand off the cube; evaluate role-swapping feasibility.
- One gripper holds a nonrotating portion while the other engages only the intended face layer, without touching or jamming adjacent layers.
- Transfer sufficient torque through contacts for 90°/180° turns under realistic friction, grip force and cube torque.
- Maintain controlled contact and avoid unintended twists, slipping, tearing apart or ejecting cubies.
- Retain wrist reachability, arm clearance, mount compatibility and stable tool frames.
- Permit practical approximation using MuJoCo primitive/convex contact geometries and CPU-first simulation.
- Support later camera visibility of cube faces; tooling should not render perception impossible.

## Literature and source review requirements

Inspect published robotic cube solvers, bimanual grasp planning, custom fingertip optimization, parallel-jaw gripper design, torsional friction, precision assembly, passive mechanical compliance, contact-force sensing and residual-RL-assisted manipulation. Compare at least **six distinct candidate end-effector/fingertip concepts**, and the best **two or three** in depth. Include both positive and negative evidence.

**Primary sources to examine:** peer-reviewed manipulation papers; official UFACTORY gripper manuals and 3D models; MuJoCo Menagerie xArm7 and available gripper model metadata; peer-reviewed grasp-wrench and stability methods; actual open CAD releases and license terms. Source leads appear in `REFERENCES_SEED.md`.

## Concepts to compare

1. Simple narrow flat jaws with a tunable high-friction compliant pad.
2. Offset or stepped jaws for non-target layer clearance.
3. Shallow grooved, edge-conforming or corner-contact jaws, avoiding physical jamming.
4. Asymmetric tool geometry for stabilizing vs turning.
5. Identical dual-role jaws with role switching and handoffs.
6. Alternative compact 3-point/adaptive mechanisms if mechanical evidence shows two-finger limits.
7. Published puzzle manipulators or assembly end-effectors if adaptable without a proprietary hidden actuator.

## Quantitative feasibility analysis

Derive preliminary **contact/friction wrench** requirements for face-turning torque and stabilizing counter-torque. Use sources or conservative ranges for cube dimension, layer height, total and cubie masses, grip force, gripper aperture, fingertip width, friction, compliance and turning resistance. Show units, lever arms and sensitivity. Evaluate pinch normal forces, torsional resistance, contact patch pressure, tool clearance and expected collision geometries. Do not invent friction/torque measurements.

For each concept examine:

| Criterion | What to verify |
| --- | --- |
| Layer selectivity | Can the jaw fit and contact the intended layer without adjacent-layer interference? |
| Stabilization | Is counter-torque maintained without twist or slip? |
| Turning feasibility | Can the opposite tool deliver torque around the layer's correct axis? |
| Tool reach | Are poses reachable without wrist and arm collisions? |
| Swappable roles | Can both arms perform both tasks or a credible handoff plan? |
| Camera visibility | Can all sticker faces eventually be observed? |
| Sensitivity | Does it still work when pose/friction/size varies? |
| Computational cost | Can collision/contact geometry be simulated at practical headless throughput? |
| Integration | Mounting geometry, actuator force, model accuracy and CAD license |
| Manufacturability | Parametric, physically plausible dimensions; simulation is still primary |

## Required report format

Write the findings under `docs/research/` **after** research (written as `GRIPPER_LITERATURE_REVIEW.md` and `GRIPPER_DESIGN_TRADEOFFS.md`; P-05):

- Verified bibliography with titles, authors, dates, DOI/URL, accessible content level and licensing.
- Official xArm7/gripper models, source links, attachment interfaces, jaw stroke/force (if verified), CAD formats.
- At least six concepts with figures/links or reasoned geometric sketches, each with trade-offs and failure modes.
- Contact-force/torque model, sensitivity tables and unknown physical parameters.
- A weighted decision matrix (weights declared, sensitivity reported).
- Preferred **two or three** concepts for physical simulation pilot, not premature detailed CAD.
- Recommendation as `SELECT`, `CONDITIONAL`, or `BLOCKED`, plus the minimum falsifiable simulation experiment.

## Mandatory approval gate

Do not CAD-model custom fingertips, edit gripper meshes, start contact RL training or declare a final design until the user approves the research-backed geometry direction. First validate with simple geometry and conventional control; only then invest in detailed fingertip models or optimization.

## Source starting points

- UFACTORY manuals and gripper CAD: https://www.ufactory.cc/en-us/downloads
- MuJoCo Menagerie xArm7 MJCF and licensing: https://github.com/google-deepmind/mujoco_menagerie/tree/main/ufactory_xarm7
- MuJoCo Menagerie overview: https://github.com/google-deepmind/mujoco_menagerie
- Bimanual Rubik's Cube system (2023, DOI): https://doi.org/10.1109/CCDC58219.2023.10326999
