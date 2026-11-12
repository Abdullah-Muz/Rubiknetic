# Seed References and Source Verification Queue

**This is not a completed literature review.** Links below are starting points verified as publicly identifiable on 2026-11-12; source applicability, exact mechanical findings, experimental setups, full-text access, source/CAD licenses and comparative validity must be reviewed during Phase 0. Bibliography may grow substantially.

## Core simulation and robot assets

1. **MuJoCo — Simulation documentation.** Runtime equality constraint activation (`mjData.eq_active`), actuator/control interfaces. https://mujoco.readthedocs.io/en/stable/programming/simulation.html
2. **MuJoCo — XML Reference.** Equality constraints, modeling, contact parameters. https://mujoco.readthedocs.io/en/latest/XMLreference.html
3. **MuJoCo — Python bindings.** Simulation and rendering APIs; inspect current version. https://mujoco.readthedocs.io/en/stable/python.html
4. **Google DeepMind — MuJoCo Menagerie.** Curated robot models, xArm7 and grippers, license inventory. https://github.com/google-deepmind/mujoco_menagerie
5. **Google DeepMind — xArm7 MJCF model README.** Model derivation and stated BSD-3-Clause licensing. https://github.com/google-deepmind/mujoco_menagerie/blob/main/ufactory_xarm7/README.md
6. **UFACTORY — Downloads.** xArm7 3D models and gripper G2 CAD/manuals; inspect exact variant compatibility. https://www.ufactory.cc/en-us/downloads

## Learning and control

7. **Johannink et al. (2019), “Residual Reinforcement Learning for Robot Control.”** ICRA. DOI: `10.1109/ICRA.2019.8794127`. https://doi.org/10.1109/ICRA.2019.8794127
8. **Residual RL project page** by the paper's authors (includes abstract/research links). https://residualrl.github.io/
9. **Stable-Baselines3 documentation.** SAC, PPO and implementation considerations (verify current API). https://stable-baselines3.readthedocs.io/en/master/
10. **Gymnasium documentation.** Custom environment API and reset/step interfaces. https://gymnasium.farama.org/
11. **Pinocchio robotics dynamics docs.** Kinematics, dynamics, Jacobians. https://gepetto.github.io/doc/pinocchio/doxygen-html/
12. **Open Motion Planning Library.** Planners and state-validity model. https://ompl.kavrakilab.org/

## Cube solving and related manipulation

13. **Herbert Kociemba — Two-Phase Algorithm.** Independent symbolic solver fundamentals; does not optimize robot grasp cost. https://www.kociemba.org/math/twophase.htm
14. **“Design and Implementation of Dual-Arm Robot Rubik's Cube Solving System” (2023), CCDC / IEEE.** DOI: `10.1109/CCDC58219.2023.10326999`. https://doi.org/10.1109/CCDC58219.2023.10326999
15. **OpenAI (2019), “Solving Rubik's Cube with a Robot Hand.”** Dexterous RL reference; different hardware/compute requirements. https://openai.com/index/solving-rubiks-cube/

## Research backlog: source discovery required

Find additional verified primary papers on dynamic topological constraints, robotic Rubik's Cube mechanisms, grasp wrench and torsional contact, compliant fingertips, bimanual coordination, facelet recognition under occlusion, manipulation-aware planning, physically meaningful constraint switching and its numerical artifacts. Aim for **15–20 relevant sources across the Phase 0 research**, not merely 15 links on this seed page.

## Citation hygiene

For each item moved to a findings report record source ID, authors, date, venue, DOI/URL, access date, abstract/full-paper/official-document access status, direct supported claim, limitations, numerical data and license. Never imply that a listing, abstract or landing page means the full paper was critically read.
