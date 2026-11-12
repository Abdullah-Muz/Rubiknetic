# Cube Mechanics — Research Brief (not findings)

**Goal:** Find a physically credible and computationally feasible MuJoCo model of a 3×3 Rubik's Cube with **dynamically changing cubie constraints**, allowing legal face turns driven by robot-applied torque.

## Locked requirements

- Realistic enough for contact-driven manipulation, not kinematic face-turn scripts.
- Repeated quarter-, half-, inverse turns and changes of rotation axis.
- Relative cube topology always valid: 8 corners, 12 edges, 6 centers, central support structure as appropriate; no arbitrary cubie detachment, interpenetration or illegal orientation/permutation.
- Constraint change may maintain legal assembly at correct alignment, but cannot generate the rotation or force the target state.
- An independent discrete cube representation verifies every move without copying the simulated model's intended target state.
- CPU-only tractability matters; do not pursue microscopic internal geometry without engineering justification.

## Mandatory research questions

1. **Physical mechanism:** What core / center / edge / corner arrangements retain conventional cubes through turns? What external sources or models document the mechanical constraints? How does contact torque propagate?
2. **State representation:** Which bodies and generalized coordinates are needed? What remains locked during a face turn, and what constraints are switched only at legal alignments?
3. **Topology transition:** Can constraint activation/deactivation among **predefined** MuJoCo equalities encode all necessary transitions without overconstraints? How many constraints would be required; what are alternatives (custom mechanism, sliding contacts, hybrid equivalent joints)?
4. **Transition validity:** How are angular tolerance, face alignment, velocity, penetration, opposing torque, potential energy and momentum consistency checked at each switch? Could the operation cause spurious acceleration or energy injection?
5. **Friction and torque:** What quantities influence turn resistance, face torque, solver stiffness, contact patch, damping and cube-body stability? Which values are physically sourced versus uncertain?
6. **Collision fidelity:** Which collision meshes can be simplified while retaining legal contact and preventing passage through other cubies?
7. **Computational cost:** Number of constraints/contact pairs and observed steps/s on CPU; sensitivity to timestep/iterations and solver selection.
8. **Generalization:** What happens with successive `R`, `U`, `R'`, `U'` moves? Can inverse/repeated turns restore exact combinatorial cube states within tolerance?

## Candidate mechanisms (to compare, not to presume viable)

- **Predefined switching equalities:** Fixed multibody bodies + select predeclared equality relationships; evaluate topology coverage and switching artifacts.
- **Mechanically constrained cubies with a simulated core:** More direct physical assembly, possibly harder to make numerically stable or CPU-efficient.
- **Minimal equivalent mechanical surrogate:** Lower-dimensional rotation mechanism that still transmits force through contacts and preserves discrete legal state; must disclose reduced fidelity and prove it does not provide unearned actuation.

If none is adequate, return a `BLOCKED` finding and propose user-reviewed changes; do not implement an invisible scripted rotation workaround.

## Independent test oracle

Use a standalone symbolic cube model to validate:

- All six face directions, primes and 180° turns; each inverse cancels a move.
- Four quarter turns return identity; correct cubie identities/orientations persist.
- Reachable scrambles generated exclusively by legal moves.
- No duplication/loss of cubies; parity and orientation constraints remain satisfiable.
- Physical transform-to-state extraction agrees with symbolic expected moves, not with the controller's requested move alone.

## Experimental pilot design

1. Minimal core / layer surrogate and a physically applied **external contact wrench**, no robot initially.
2. Execute one 90° turn; log torque, forces, angle, separation, penetration, constraint mode and body velocities.
3. Execute reverse and half turns; test 4×90° identity and reverse paths.
4. Execute **two non-parallel face moves** and a 4-move commutator; verify logical consistency.
5. Perturb friction, timestep, solver iterations and initial alignment; report failures and artifacts.
6. Repeat with cube held by a physical fixture as intermediate validation; eventually replace fixture with robot contact.

## Decision gate

Recommend one modeled mechanism (with documented fidelity level), alternatives, parameter uncertainties and mechanical risks. Produce `research/CUBE_MECHANICS_FINDINGS.md`; user approves before implementation. Passing this **research** gate is distinct from the Phase 1 **working-physics** gate.

## Primary reference starting points

- MuJoCo simulation API (`mjData.eq_active`): https://mujoco.readthedocs.io/en/stable/programming/simulation.html
- MuJoCo XML reference: https://mujoco.readthedocs.io/en/latest/XMLreference.html
- MuJoCo computation: https://mujoco.readthedocs.io/en/stable/computation/
- Two-phase logical solving (independent oracle): https://www.kociemba.org/math/twophase.htm
