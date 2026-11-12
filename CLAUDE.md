# Claude Code operating instructions — Rubiknetic

**Read `RUBIKNETIC_MASTER_SPEC.md` first.** This file governs the assistant's workflow; the master specification governs technical scope. Consult `docs/DECISION_LOG.md`, the relevant phase plan, the research briefs, and `docs/VALIDATION_PLAN.md` before proposing changes.

## Operating mode

- Work in **one interactive Claude Code session**. Do not spawn subagents, agent teams, or independent assistants.
- Treat these files as a prepared **documentation package**, not proof of implemented code. Never imply a simulator, gripper, trained policy, benchmark, or test already exists.
- **Begin with Phase 0 research**, not robot geometry generation, training, repo scaffolding beyond what the user explicitly authorizes, or GitHub publication.
- Work in bounded, reviewable increments. Before each change: state objective, affected files, evidence required, and which phase gate it addresses. After each: summarize verified work, tests, limits, and blockers.
- User makes strategic mechanical choices. Do not silently change xArm7, MuJoCo, dynamic cubie constraints, Level C physical manipulation, or E+C+D RL/controller architecture.
- You may propose alternatives, trade-offs, or a scope correction with evidence, but wait for user approval before changing locked decisions.

## Research integrity

- Verify sources using available web/browsing tools; if access is unavailable, mark research **blocked/unverified**, do not fabricate DOI, author, date, benchmark numbers, or claim full-text review.
- Prefer primary papers, official docs, manufacturer CAD, reputable source code. Record access date, exact URL/DOI, license, and what each source *actually* establishes.
- Separate `FACT`, `INFERENCE`, `ASSUMPTION`, `PROPOSAL`, and `VALIDATED_RESULT` in technical reports. Never promote a proposal to validated without recorded experiments.
- The starter links in `docs/REFERENCES_SEED.md` are a **seed bibliography**, not a complete literature review.

## Physics and scientific constraints

- Real cube rotations must be induced by modeled contact forces/torques. No free state edits, hidden face motor, kinematic snapping, target-angle assignment, or high-level solver state injection during evaluation.
- Constraint activation may represent mechanical connectivity when geometrically permitted, **not impose the desired rotation**. Analyze constraint activation impulses, penetration, angular momentum / energy effects, illegal topology, and numerical sensitivity.
- Maintain an independent combinatorial Rubik's Cube state verifier; verify legal face turns, puzzle group invariants, reversibility, and physical-to-logical agreement. Do not validate a model only against itself.
- Document abstractions such as equivalent joints or constraint switches; if constraints fail to reproduce credible mechanics, recommend an engineering review, not a fake success.

## Learning and testing

- Start with an independently validated conventional controller. RL remains a core planned contribution but follows physics and classical-controller feasibility.
- Prefer bounded residual Cartesian actions with a stable lower-level impedance controller; isolate privileged state used in training from camera-derived state used at final evaluation.
- Pin dependencies **when introduced**, log random seeds/configuration/hardware/runtime, use held-out evaluation, compare identical task distributions, and preserve negative results.
- Keep CPU-only headless throughput measurable. Do not require CUDA or install all future-phase dependencies at once.
- No phase advancement without a signed-off gate in `docs/VALIDATION_PLAN.md` and an update to `docs/DECISION_LOG.md`.

## Repository, credit and change hygiene

- Never commit/push, publish, create remote repositories, or overwrite user work without explicit instruction and confirmation of target GitHub account/repository.
- Do not add Claude/Anthropic as contributor/coauthor/committer, nor insert model attribution into project branding or source headers. Preserve legitimate attribution and licenses for borrowed material.
- Do not modify `RUBIKNETIC_MASTER_SPEC.md` silently. Propose specification changes and record approvals in `docs/DECISION_LOG.md`.
- When a question is uncertain, prefer a small falsifiable feasibility experiment to a large implementation.

## First authorized work sequence

1. Inspect the package for contradictions and missing citations; create an issue list rather than asserting completion.
2. Execute Phase 0 literature research on cubie constraint mechanics and gripper design. Produce findings as distinct reports (do not overwrite the research *briefs* with findings).
3. Compare feasible mechanical alternatives and provide a decision matrix, quantified assumptions and license check.
4. Ask the user to select/approve the mechanism and fingertip geometry before detailed CAD, MuJoCo integration, or training.
