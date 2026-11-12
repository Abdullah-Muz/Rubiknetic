# Start Here — Rubiknetic Documentation Handoff

This directory is the **documentation package** for a proposed Rubiknetic repository. It contains no completed research report, physics simulation or RL policy. Every phase gate starts **NOT STARTED**.

## Quick start

1. Place the folder contents in your new local `Rubiknetic` project folder. The docs can live in a GitHub repository later; this package does not create or push any remote repository.
2. Open that folder in VS Code. Start Claude Code in the folder's root.
3. Read the `README.md` for the public overview, `RUBIKNETIC_MASTER_SPEC.md` for technical authority and `CLAUDE.md` for operating constraints.
4. Begin with **Phase 0**, the cube mechanics and gripper/fingertip literature reviews. Do not let Claude start CAD, full simulator implementation or RL training without approval.
5. Review Phase 0 reports and design matrices before authorizing implementation.

## Initial Claude Code prompt — copy and paste

> We are starting a new robotics project called Rubiknetic. This folder contains its approved planning documentation. Read `CLAUDE.md`, `RUBIKNETIC_MASTER_SPEC.md`, `docs/DECISION_LOG.md`, `docs/RESEARCH_PLAN.md`, `docs/CUBE_MECHANICS_RESEARCH.md`, `docs/GRIPPER_DESIGN_RESEARCH.md`, `docs/REFERENCES_SEED.md`, and `phases/PHASE_0_RESEARCH.md` before acting. Work in **one Claude Code session only; no subagents or teams**. First audit the documentation for contradictions and unresolved assumptions, then prepare an executable **Phase 0 literature research plan** and conduct the research using verified sources available to you. The two top priorities are (a) the mechanical feasibility of dynamically changing Rubik's Cube cubie constraints in MuJoCo, and (b) evidence-based xArm7-compatible gripper and custom fingertip concepts for genuinely contact-driven bimanual face turns. Distinguish verified evidence from assumptions, record exact citations/DOIs/asset licenses, include alternatives and failure modes, and produce the report filenames required by the research plan. Do **not** invent papers, results, CAD, simulation passes or benchmarks; if browsing is unavailable, report the limitation. Do not begin detailed CAD, gripper modifications, physics implementation or RL training before my approval of Phase 0 findings. Don't commit, push or create a remote repository without my explicit authorization. Summarize your sources, risks, design decision matrix and proposed next step for my review.

## Package map

- `README.md` — public profile/landing page for the project.
- `RUBIKNETIC_MASTER_SPEC.md` — approved architecture, assumptions, invariants and phased acceptance.
- `CLAUDE.md` — how Claude should operate in the repository.
- `docs/` — research instructions, interfaces, experiment and validation protocols, source leads and decision log.
- `phases/` — eight development plans from research (0) to evaluation (7).

## What is still deliberately unknown?

Exact gripper variant, fingertip shape/compliance, trustworthy cube connectivity mechanism, measured cube mechanical parameters, numerical physical-validity tolerances, feasible CPU training budget and final camera arrangement. **The research and pilot phases are supposed to determine these.**
