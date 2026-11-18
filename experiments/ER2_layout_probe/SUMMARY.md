# ER2 — Magnet-layout stiffness screen and 0.025 mm rest rehearsal: summary (2026-11-17)

Exploratory and unscored (PROTOCOL.md; approved in P-54). M5 stays NOT PASSED (P-51). No mechanism is selected.

## Provenance (`FACT`)
- The protocol and scripts were committed in `0495421`, before any run, using the M5 software versions.
  - O2 ran on that commit with no tracked changes (`results/rest_environment.json`).
  - O1 ran after deviation 1 below.
- **Deviation 1 (O1 static script, fixed after a failed self-check):** the script's built-in check found that its
  rebuilt L0 did not equal M5's `magnets.layout`. For some corner–edge pairs it had both moments reversed. Such a pair
  still attracts, but its cross-interactions with other magnets differ. The polarity rule was corrected to M5's
  convention (moments point corner → edge, and edge → centre for the new pairs). The check then passed, and all O1
  numbers come from the corrected script. The protocol itself was not changed.
- **Deviation 2 (post hoc supplement):** `er2_static_modes.py` breaks each piece's stiffness matrix into its natural
  motions. It reads only `results/static_screen.json` and was not in the protocol.

## O1 — static screen (`FACT`; `static_report.md`, `static_modes_report.md`)
**No candidate layout passes the fixed screen.** Every layout leaves at least one piece unstable in at least one
direction.

| Layout | Magnets | Edge slide (the D10/D11 slip mode) | Edge cross | Edge spin | Corner tangential | Corner twist | Layer N m/rad | Screen |
|---|---|---|---|---|---|---|---|---|
| L0 corner–edge attract (M5) | 48 | **−1971** | +994 | +121 | **−703** | +118 | +1.99 | fail |
| L1 edge–centre attract | 48 | **+559** | **−926** | +58 | 0 | 0 | +0.99 | fail |
| L2 = L0 + L1 | 96 | −1410 | +69 | +179 | −703 | +119 | +2.98 | fail |
| L3 corner–edge repel | 48 | +1976 | −994 | −122 | +702 | −118 | **−1.99** | fail |
| L4 = L1 + L3 | 96 | +2529 | −1918 | −64 | +702 | −117 | −1.00 | fail |
| L0 at 0.025 mm | 48 | −2087 | +1024 | +124 | −767 | +121 | +2.05 | fail |

- Piece stiffnesses are in mN m/rad: the minimum over pieces of that type, along the given motion. Positive means
  restoring.
- The net magnet torque at the aligned pose is zero (≤ 1.4e-14 mN m) in every layout.
- For one pair type, the slide and cross stiffnesses have opposite signs. Attracting corner–edge pairs (L0) restore
  the layer but destabilise slides. Repelling them (L3) restores slides but destabilises the layer.
- L1 is restoring in the slip mode and leaves corners neutral. It fails on the edge cross mode (−926) and on the
  layer threshold: 0.989 against 1.0. The threshold is not adjusted.
- `ASSUMPTION` flag: L1–L4 use the near-field correction outside its V3-validated configuration (attracting
  corner–edge pairs).

## O2 — rest rehearsal on the new seeds 14000–14019 (`FACT`; `rest_report.md`)
| Arm | Slips 0–60 s | 0–10 s peak, median / max | Seeds > 0.5° | Max penetration | Max magnet tilt |
|---|---|---|---|---|---|
| G050 (M5 settings) | 0 / 20 (95 % CI 0–0.17) | 0.111° / 0.264° | 0 | 0.008 mm | 1.38° |
| G025 (0.025 mm gap) | 0 / 20 (95 % CI 0–0.17) | 0.089° / 0.255° | 0 | 0.005 mm | 0.75° |

- Paired G025 − G050 peak difference: median −0.021°; G025 is lower in 13 of 20 seeds.
- No aborts.

## Interpretation (`INFERENCE`)
1. **No tested passive layout removes the destabilising piece stiffness without losing layer restoring.** This
   screen does not prove that no layout exists. It tested five candidates built from one placement rule, statically
   and locally. But the sign trade-off is the same in all five.
2. **O2 cannot tell the two gaps apart for slips.** M5's own settings did not slip on these 20 new seeds.
   - Pooled with D11, M5 settings slip in 2 / 40 seeds (95 % CI 0.006–0.169).
   - At 0.025 mm, 0 / 20 (95 % CI 0–0.168).
   - A gap effect on slip frequency would need far more seeds.
   - What O2 shows is that a 0.025 mm gap does not make rest worse, and that peaks are slightly lower.
3. **M5 settings pass rest on all 20 new seeds.** The M5 failure looks like a rare-event outcome (about 1–17 % of
   trials). It is not a typical one. Under its pre-registration M5 remains NOT PASSED, and that does not change.

## What this leaves (`PROPOSAL`; for the user's decision, nothing applied)
- **(A) Engineering acceptance route.** Treat the corner–edge negative stiffness as a known property of M5's magnet
  design and keep it. Then, in a new pre-registration (M6) with new seeds, address the rare slip:
  - by a larger, pre-registered E1-1 sample with a stated tolerated slip rate, if the user judges a rare 0.5° piece
    slip acceptable; this is a criterion change, so it needs independent justification and must be disclosed as
    proposed after M5 failed;
  - or by the 0.025 mm gap, which shrinks the play budget, although O2 shows no measurable slip benefit.
- **(B) Mechanism route.** Explore L1-like edge–centre layouts further (shaped or offset magnets, mixed strengths)
  for both slide and cross restoring. This is static design work first, then V-checks, then a rehearsal.
- **(C) Model-fidelity route (O3 from ER1).** Add per-piece retention representing real-cube interlocks or
  spring tension. This is a spec-level modelling decision and needs a literature check first.
