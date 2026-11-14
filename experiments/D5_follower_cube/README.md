# D5 — Convex-only real-mechanism cube ("two-grid + tangent pads"), UNSCORED design study

> **FROZEN 2026-11-13 as the high-fidelity REFERENCE model (design "B").** It is not the primary cube model
> (user: "I approve your recommendation", decision P-17).
>
> **Frozen parameters:**
>
> | Group | Values |
> |---|---|
> | `D5Params` geometry | `bevel_body=2.0, bevel_foot=0.5, bevel_inner=1.0, taper=0.1, taper_start=20.0, inner_split_centre=26.0, inner_split_edge=24.0, pad_spacing_deg=14.0, sphere_spacing_mm=2.0` |
> | Gaps and centres | `gap=0.05, clearance=0.02, spring_preload=10.0, spring_k=2000.0, slide_range=(-0.001, 0.0003)` |
> | Contact and solver | friction 0.2; solref (1 ms, 1); solimp (0.99, 0.999, 0.5 mm); timestep 0.5 ms |
> | Other | Detent off; unchanged M1 pad rig |
>
> **Performance with the soft turner** (staged search, `search/`; FACT):
>
> | Measure | Result |
> |---|---|
> | 9-move sequence | 9/9 match the oracle |
> | Worst turn error | 4.0° |
> | Penetration | ≤ 1.51 mm |
> | Speed | 62 steps/s |
> | Twist | 1.1° at 0.2 N·m; 20.9° at 0.5 N·m; recovers to solved after 5 N·m |
> | Forgiveness | completes +3.2°; jams at −2.5° (R stops at −81°) |
>
> **Known limits** (why it isn't primary):
> * one-sided forgiveness of about 3–4°;
> * penetration of 1–1.5 mm under grip;
> * turn error above 2° with the soft turner;
> * about 20× slower than M2.
>
> **Alternative reference:** the original baseline (`bevel_body=1.0, bevel_foot=0.5`, 10° pads, 1 mm sphere
> sampling) also passes 9/9 reproducibly, with lower twist rigidity.
>
> **Revisit only with new inputs:** real-cube measurements (O-09), or a genuine cam-surface redesign.

**Status:** design iteration in progress (2026-11-13). Nothing here is a scored result, and nothing has been
adopted as the project's cube model.

* Approvals:
  * User approved redesigning the internals for MuJoCo, with stage 1 and stage 2 testing ("Approved, lets begin").
  * User approved iterating on the fixes ("you have my approval ... apply those fixes, reiterate, and try again").
* This is our own geometry. No CAD geometry is used. Only layout dimensions were measured from the reference CAD
  (`tools/cad_layout.py`).

## Design principle

The reference CAD's layout shows the real mechanism is effectively **two nested 3×3×3 grids**:

| Region | Bounded by | Contents |
|---|---|---|
| Outside the bearing sphere (r ≥ RS = 25 mm) | Outer cut planes \|x\|, \|y\|, \|z\| = A = 9.5 mm | Each piece's outer body |
| Inside the sphere | Inner planes ±S = 4.8 mm | Each piece's foot |

* Each piece = its outer cell + its inner cell.
* Where the two grids disagree, one piece's foot lies under another piece's body, across the sphere. **That is the
  capture.**
* Every interface is a plane except the sphere.
  * Feet are box ∩ ball, which is convex and exact.
  * The concave undersides of bodies are replaced by **flat pads tangent to the sphere**. Each pad touches a foot at
    one point, and that point stays fixed as the foot slides around the sphere during a turn.
* Centres sit on a hinge plus a spring-loaded radial slide, like the real screw and spring. Edges and corners are
  free bodies.

**Files:**

| File | Purpose |
|---|---|
| `cube_d5.py` | Generator |
| `kin_check.py` | Geometry-only checks |
| `dyn_check.py` | Rest and twist dynamics |
| `rig_turn.py` | Turns with the unchanged M1 pad rig |
| `forgive_rig.py` | Dynamic forgiveness |
| `diag_block.py` | Identifies the contacts that block a turn |

## Results so far (FACT unless tagged)

| Test | Result |
|---|---|
| Geometry: rest, all 6 face sweeps 0–90° in 1° steps | No interference; ≥ 0.018–0.05 mm clearance throughout |
| Geometry: capture with others fixed | Corner outward blocked ≤ 0.05 mm (M1: 0.55 mm); twist blocked by 0.5–2° (M1: ~15° of slack); tilt blocked by 0.25–0.5° |
| Rest, 3 s | Valid and solved; max piece rotation 0.18°; penetration ≤ 0.008 mm |
| Corner twist staircase | Best configs reach 1.8–3.7° at 0.2 N·m (M1: 23°). Survive 5 N·m and recover to solved, with a snap to ~12° above 0.2–0.5 N·m. With soft contacts at 0.5 ms the corner can tunnel out above ~0.5 N·m. Stiffer contacts (0.25 ms) prevent it, at the cost of speed |
| Turning by the centre cap only | Jams at ~30° with μ 0.2: the cap tips the edges, which wedge. This was a test-method artefact |
| **Turning with the M1 pad rig** (10° pads), U R U′ R′ F F′ D2 L B′ | **9/9 observed moves match the oracle.** Error 0.94–2.47°, drift ≤ 0.23°, turner torque ≤ 0.95 N·m. Piece penetration 0.6–1.1 mm and pad penetration 0.3–0.6 mm (above the 0.5 mm limit) |
| Same sequence, 20° pads (fast variant, 2.3× faster) | Only 3/9 moves. Jams follow small misalignments |
| Dynamic forgiveness (10° pads) | Completes R and **pushes U back into line** for U misaligned −0.9° to −7.8°. Weak side: +1.5° completes at the torque limit; jams by +4.3° |
| Weak-side blocker (diag_block) | The misaligned U∩R corner's foot crosses the inner plane and meets a centre's inner block **face-on** (pure-z normal, no cam). Cause: those inner-plane faces were left unbevelled |
| Speed | 23–89 steps/s depending on pad count, against ~600–2000 for M1 |

## Iterations 1–5 (2026-11-13)

All results FACT unless tagged.

**1. Inner-plane bevels inside the sphere (`bevel_inner`).** Did not fix the weak side.

**2. Gaps 0.10 / 0.15 mm.** Did not fix the weak side. U was pushed back into line, but R then jammed at about −20°.

**3. Stiffer turner (`m1.turn_kp` 20).**
* Turn error fell from 1.5–2.5° to ≤ 1.1°.
* 4/4 on the 10° pads; 7/9 on the 14° pads, where R′ jammed after U′ ended 1.68° off.

**4. Centre-diagnostic hypothesis (centres drifting off-square): refuted.** All non-turning centres were within 0.02°. The blocker is the misaligned U∩R corner's own foot.

**5. Long ramps sized by the rule (bevels 2.5 / 2.2 / 2.2).** Mixed: the weak side improved (+2.4° completes), the strong side got worse (R stuck at −81° after U was pushed past square).

**6. Spring 3 N, and spring 3 N + core detent (P-16, 0.1 N·m).**

| Setting | 9-move sequence |
|---|---|
| Spring 3 N | 7/9; lower friction; penetration ≈ 0.5 mm |
| + detent | 5/9 |

INFERENCE: near square the detent is far weaker than the layer friction, while it still adds resistance to the turns.

**7. Fast cam analyser (`cam_analyser.py`, ~20 s per design).**
* Its HARD-block metric matches the dynamic forgiveness asymmetry; its "U-block" class does not.
* Lateral tapers plus 5 mm body bevels made it clean to ±3° kinematically. **Dynamically that design collapsed:** the U turn stalled at −76° and the cube came apart, though it held at rest.
* Each change alone makes R stop 4–7° short. Large bevels or tapers remove too much support.

**8. Next.** An automated staged search: analyser screen, then short dynamic tests, then the full tests, with a support penalty. It runs in `search/` (sub-agent).

## Fixes under test (iteration 1)

1. **Bevel inner-plane faces inside the sphere** (`bevel_inner`). Geometry stays green.
2. **Stiffer turner control** (`m1.turn_kp` 20). Residual turn error is friction torque divided by kp, about 1.7°
   at kp = 5.

Still to do:

* Remove the start-up spring transient (2 mm at t ≈ 2 ms).
* Tilt stops to stop edges wedging under grip.
* A pad layout that keeps robustness at lower cost.
