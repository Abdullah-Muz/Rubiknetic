# ER1 — Engineering review of the M5 rest slip (2026-11-17)

**Status:** engineering review approved in P-53(b). Its probes are **exploratory and post hoc**: designed after
D10/D11, unscored, with no decision rule. Nothing here changes M5's verdict (NOT PASSED, P-51) or any threshold.
Labels follow CLAUDE.md: `FACT` (measured in these simulations), `INFERENCE`, `PROPOSAL`.

## Questions (from P-53)
- (a) What rotation do the 0.05 mm play and the chamfer permit, and is a 0.5° slip physically credible?
- (b) Why does a corner at rest carry about 10 mN m of net magnet torque?
- (c) What would remove the slip?

## Evidence
| Source | What it is | File |
|---|---|---|
| D10 | 7 arms × seeds 10000/10001; exact reproduction | `../D10_m5_rest_diagnostic/SUMMARY.md` |
| D11 | 20 seeds × 60 s; slip events counted | `../D11_rest_slip_count/SUMMARY.md` |
| Probe 1 | s10001 and s10000 re-simulated; positions, contacts, neighbour gaps | `er1_probe_slip.py`, `results/probe_slip_s*.json` |
| Probe 1v | Probe 1 with the setup misalignment set to zero, or to U only | `er1_probe_slip_variant.py`, `results/probe_slip_{zero,U_only}_s10000.json` |
| Probe 2 | Overlaps created by the setup misalignment, all 20 seeds, before any step | `er1_probe_setup.py`, `results/probe_setup.json` |
| Probe 3 | Rest with zero or U-only misalignment, seeds 10001/10000 | same |
| Probe 4 | Static: free rotation of pieces and groups from the aligned pose | `er1_probe_play.py`, `results/probe_play.json` |
| Probe 5 | Static: magnet torque and rotational stiffness, piece versus layer | `er1_probe_magnet_stiffness.py`, `results/probe_magnet_stiffness.json` |

All probes use the M5 code read-only, through D10's instrumented loop or a fresh M5 model, with the same software
versions as M5.

## Findings (`FACT`)

**F1. A slip is a cluster of pieces crossing a large consolidated gap.**
- Slips are rare: 2 of 20 seeds (D11). Those are the only two rest trials at or above 0.4°.
- In s10001 at t0 (after the 0.5 s settle), two neighbour gaps are already far above the 0.05 mm design gap:
  - `n0p|npp`: 0.225 mm;
  - `nnp|0np`: 0.268 mm.
- At 3.7–3.9 s after t0, the corner `nnp` and edge `n0p` slide together about the U axis (−0.55°; `n0p` moves
  0.218 mm). The `n0p|npp` gap closes (0.186 → −0.002 mm), and the opposite gap opens (`nnp|0np`: 0.31 → 0.41 mm).
- s10000 shows the same pattern: `n0p|npp` closes from 0.19 mm, and `npp|0pp` opens to 0.42 mm.
- The U layer's mean rotation stays at or below 0.11°. It is the cluster that moves, not the layer.

**F2. The large gaps are not created by the setup procedure.**
- Probe 2: the six independent layer misalignments create **no overlaps** in any of the 20 seeds. Layer rotations
  slide pieces parallel to their shared faces.
- Probe 1v: with **zero** misalignment, the 0.5 s settle still leaves gaps of 0.18–0.24 mm.
- Probe 3: with U-only misalignment of 0.033° (s10000), a 0.512° slip still occurs at 4.2 s. Afterwards the
  `0pp|ppp` gap is 0.42 mm.

**F3. The play budget sets the slip size.**
- Probe 4, starting from the aligned pose with every other piece fixed:
  - a single piece, a corner+edge pair, or a 3-piece row can rotate only **±0.106°** about the face axis (one
    0.05 mm gap);
  - a corner can twist only ±0.308° about its own diagonal;
  - the whole layer turns freely.
- Larger motion needs the gaps to be redistributed first. The ring of 8 pieces around a face has 8 interfaces ×
  0.05 mm = **0.40 mm** of total play, and the largest gap observed after a slip is 0.42 mm.
- A cluster crossing a gap g at radius r rotates by about g / r:

  | Gap crossed | Edge (r = 19 mm) | Corner (r = 26.9 mm) |
  |---|---|---|
  | 0.19 mm (as in s10001) | 0.57° | 0.40° |
  | 0.40 mm (whole ring budget) | 1.2° | 0.85° |

  The 0.5° limit corresponds to a gap of 0.17 mm at an edge, about 3.3 nominal gaps.
- The chamfer (1.4 mm) does not change the in-plane budget. The blocking contacts in probe 4 are flat faces.

**F4. The magnets centre layers but push individual pieces off centre.**
- Probe 5:
  - At the exactly aligned pose, the net magnet torque about the cube centre is **0** on every piece. The layout has
    no built-in asymmetry.
  - Rotating the **whole U layer** gives a restoring stiffness of **+2.03 N m/rad**. This is the self-alignment D8
    was designed for.
  - Rotating **one piece** inside its play gives a **destabilising** stiffness: −0.93 N m/rad for an edge, −0.42 for
    a corner, −0.42 for a corner+edge pair. The torque pushes the piece further the way it has already moved.
- The 48 magnets sit on the corner–edge faces (`magnets.py:92`, `layout`). A piece that moves toward one neighbour
  is pulled harder by that neighbour's magnet than by the one it moved away from.
- −0.42 to −0.93 N m/rad times a 0.5–0.7° offset gives 4–11 mN m. That is the size of the torque measured on the
  slipping pieces (8.8–13 mN m, D10/D11). So the ~10 mN m in question (b) is not a layout asymmetry. It is this
  negative stiffness acting on pieces that already sit off centre in their play.

**F5. Timing is sensitive; the solver is not involved.**
- Friction (cubie μ = 0.2) holds a cluster under a slowly growing magnet torque until it releases. The release time
  shifts with the timestep (D10), and slips happen in only 2 of 20 seeds.
- The solver never needed more than 15 of its 100 iterations (D10).

## Interpretation (`INFERENCE`)
1. **Mechanism of the M5 rest failure.**
   - Corner–edge magnets give each piece negative positional stiffness inside its play.
   - The pieces therefore bunch, and the ring's play collects into one or two large gaps (up to about 0.4 mm).
   - Friction then holds a cluster until it snaps across a gap: about 0.4–0.57°, in 75–150 ms.
   - This is a genuine behaviour of the M5 model, not integration error and not a setup artefact. A finer timestep
     cannot remove it (D10: s10000 gives 0.567° at 0.125 ms).
2. **Physical credibility (question a).**
   - The motion is geometrically legal: penetration stays at or below 0.02 mm (M5 s10001: 0.014 mm; probe 3: 0.005–0.020 mm), and the
     motion stays within the modelled play.
   - Whether a real cube does this depends on things the B1 abstraction leaves out. Each B1 piece is a free ball joint
     at the cube centre, with no radial preload. A real cube's pieces are also retained by interlocking feet and
     centre-cap spring tension, which may give per-piece positional stiffness.
   - So the slip is credible **for the model as specified**. Whether it is credible for a physical cube is
     unverified. No source on real-cube piece play has been reviewed for this.
3. **The rest criterion.**
   - The M1 text defines rest rotation per layer, but the code measures single pieces. This mismatch was already
     disclosed in `../PLAY_CRITERIA_PROPOSAL.md` §1.
   - D10/D11 show the failure is piece motion; the layer mean stays at or below 0.11°.
   - This must **not** be used to reinterpret M5. M5 was judged on the registered code. A criterion change made right
     after a failure is the post hoc move CLAUDE.md warns against. It would need an argument that stands on its own
     and a new pre-registration with new seeds.

## (c) Options (`PROPOSAL`; none applied, none validated)
| # | Option | Expected effect | Cheapest falsifiable test | Risks and trade-offs |
|---|---|---|---|---|
| O1 | Magnet layout with **non-negative piece stiffness** and positive layer stiffness. For example: keep only the pairs that act in shear across layer interfaces, or add piece-to-centre magnets. | Removes what drives the bunching. | Probe 5 on candidate layouts: static, minutes of CPU, no scored seeds. Then V1–V3 checks and an unscored rehearsal. | The in-layer pairs may be what suppresses drift during turns (E1-6n: without magnets, long sequences fail). Needs a new mechanism (M6) and a full pre-registration. |
| O2 | Smaller piece gap, 0.025 mm | Halves the ring budget to 0.2 mm, so a one-gap slip is about 0.2–0.3° at most. | Unscored rest rehearsal on new seeds at 0.025 mm; count slips as in D11. | Does not remove the mechanism, only scales it down. Whether a 0.025 mm fit is credible for a real cube is unverified. E1-7 at 0.025 mm passed the two sequences (reported only). |
| O3 | Model fidelity: per-piece retention, such as a radial preload or a feet-in-track constraint | May give the positive per-piece stiffness that real cubes might have. | Literature check on real-cube internal geometry, then probe 5 with the retention added. | M1's 1 N radial preload failed the radial pop and E1-6b checks. Larger modelling change; a spec-level decision for the user. |
| O4 | Longer settle before t0 | Would hide early slips. | — | **Not recommended.** It would tune the protocol so the trial passes, without changing the mechanism. |
| O5 | Rest criterion per layer, not per piece | Would pass M5-like behaviour. | — | **Not to be applied to M5.** Only inside a new pre-registration, justified independently, disclosed as proposed after M5 failed (see Interpretation 3). |

**Recommendation (`PROPOSAL`):** start with **O1's static probe**. It is cheap, and it directly tests the cause found
in F4. Its outcome decides between:
- a new magnet layout (M6 candidate);
- a model-fidelity change (O3), if no layout gives both positive piece stiffness and positive layer stiffness.

O2 can be evaluated alongside as a fallback. O4 and O5 are listed only so the record shows they were considered.

## Limits
- Probes 1–5 are exploratory and were designed after seeing D10/D11. They explain two seeds in detail and 20 by
  count. Slip frequency is 2 / 20, with a 95 % interval of 1–32 %.
- The static stiffness values (probe 5) are local, within ±0.1°, at the aligned pose. Off-centre poses may differ.
- The real-cube comparison in Interpretation 2 has no sources yet. It is a question, not a finding.
