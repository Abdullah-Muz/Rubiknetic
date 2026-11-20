# Phase 0 — Literature & Engineering Research Plan

**Status:** Instructions prepared; literature review not yet executed.  
**Owner:** Project engineer, using Claude Code in one interactive session.  
**Prerequisites:** Read the master specification, the gripper research brief, and the cubie mechanics research brief.

## Goals

1. Determine whether dynamic cubie connectivity can support **repeatable, physically driven** turns in MuJoCo without nonphysical constraint impulses or forced state updates.
2. Evaluate xArm7-compatible parallel-gripper and fingertip mechanisms for stabilization, target-layer access, torque transfer, regrasping, role swapping and eventual full solves.
3. Establish a realistic baseline for Cartesian/impedance control and residual RL on a CPU-only development machine.
4. Recommend a mechanical concept, simulation abstraction, measurable validation criteria and falsifiable pilot experiment.

## Research protocol

**Search in layers:** primary peer-reviewed research (IEEE ICRA/IROS/RA-L/T-RO, PMLR, journals); published robotics laboratories' technical reports and reproducible code; official MuJoCo/UFACTORY/robot libraries; open CAD and source releases; credible technical blogs only as supplementary context.

**Required searches:** bimanual Rubik's Cube manipulation; robotic cube-turning mechanisms; custom parallel-jaw fingertip design; quasi-static grasp wrench and torsional friction; adaptive fingers vs narrow stepped fingers; dynamic equality/loop constraints and articulated-object reconfiguration; constraint activation impulses; contact-rich manipulation residual RL; cube-state vision and sticker color reconstruction; CPU-based MuJoCo training and control.

**Search coverage:** target **15–20 distinct credible sources minimum** across the *combined* Phase 0 study. This is a research target, not permission to pad a bibliography. Include sources with contradictory findings, clearly mark unavailable or paywalled material, and avoid citation laundering. A relevant experimental paper is more valuable than ten repetitive summaries.

**For every source**, record: source ID; full title, author(s), publication year, venue; exact URL and DOI if applicable; access date; public abstract or full text actually inspected; methodological relevance; limitations; what is experimentally supported vs inferred; usable code/CAD and license; how it affects a Rubiknetic design decision. For source records, use precise quotations sparingly and cite original locations.

**For every numerical assumption**, document units, uncertainty, source, and plausible range. No invented gripping forces, friction coefficients, cube mass, gap widths or accuracy percentages.

## Required research reports (produce after researching)

Create reports under `docs/research/` rather than overwriting the briefs in `docs/` (P-05, approved 2026-11-19; the Phase 0 reports were written under these names, mapped below):

- `docs/research/CUBE_MECHANICS_LITERATURE_REVIEW.md` (with `docs/research/CUBE_MECHANISM_FINDINGS.md`): physical cube topology, candidate MuJoCo representation, constraint-update algorithm, failure modes, alternatives, fidelity limits, pilot experiment.
- `docs/research/GRIPPER_LITERATURE_REVIEW.md` + `docs/research/GRIPPER_DESIGN_TRADEOFFS.md`: commercial grippers and CAD, contact geometry, custom fingertip concepts, force/torque budget, compatibility, interference, recommendations.
- `docs/research/CONTACT_AND_RL_FINDINGS.md` (written 2026-11-19, P-64; to be re-checked for newer work when Phase 3 starts): modeling of friction/compliance, controller baseline, residual-RL publications and CPU performance concerns.
- decision matrix, in `docs/research/GRIPPER_DESIGN_TRADEOFFS.md` §4 and the cube comparison in `docs/research/CUBE_MECHANICS_LITERATURE_REVIEW.md` §6: weighted comparison of mechanisms and grippers (with weights justified), uncertainty sensitivity, selected leading candidate(s) and negative findings.
- `docs/research/PHASE_0_SOURCE_REGISTER.md`: full bibliography with verification and licensing metadata.

These are **deliverable names**, not pre-filled reports: they must not be marked completed or populated with invented findings.

## Required mechanical thought experiments

1. One robot stabilizes two layers while the other engages precisely one layer; estimate force/torque and gripper clearance.
2. Repeat 90° and 180° turns, change axes, release/re-attach constraints and demonstrate inverse moves without overlaps or missing cubies.
3. Reorient a partially scrambled cube without violating grasp geometry; test whether arm roles can be swapped with identical fingertips.
4. Analyze whether a gripper can both stabilize and turn with the same jaw geometry; compare asymmetric tooling and explicit tool changes.
5. Design a fail-fast pilot where implausible constraint switching, hidden face actuation or contact-force mismatch is obvious.

## Research outputs and review gate

- Evidence-backed **top 2–3 cube mechanism concepts**, not merely one favored approach.
- Evidence-backed **top 2–3 fingertip configurations**, with design tradeoffs and quantitative feasibility bounds where data exists.
- A prioritized list of unknown measurements, tests and sourced manufacturer specifications.
- CPU benchmark plan and a first classical-controller validation plan.
- Written decision request to the user naming the proposed mechanism/gripper and alternatives; **no CAD development before approval**.
- Explicit `PASS`, `CONDITIONAL`, or `BLOCKED` Phase 0 status in `docs/DECISION_LOG.md` with supporting files. If fundamentally infeasible, explain the blocker and seek revised scope.

## Research quality checklist

- [ ] Claims are traceable to primary materials where possible.
- [ ] Peer-reviewed paper metadata, year and DOI verified.
- [ ] Model/mesh/CAD licenses identified and compatible with planned distribution.
- [ ] Data and source access limitations recorded.
- [ ] Mechanical geometry constraints and quantitative ranges distinguished from assumptions.
- [ ] MuJoCo `eq_active` API is not treated as proof of valid topology switching.
- [ ] No simulations, training outcomes, or design verification invented.
- [ ] Mechanical alternatives and negative evidence represented fairly.
- [ ] User has reviewed candidate designs before moving to Phase 1 CAD/simulator build.
