# How commercial cubes place core-to-piece magnets (findings, 2026-11-21)

**Status:** research report; unscored; no simulation. Labels: `FACT` (stated by the named source), `INFERENCE`,
`UNVERIFIED` (search snippet only). All sources accessed 2026-11-21. A subagent compiled this report. The main session
re-read [P1] and [S3] and confirmed the claims attributed to them. A second subagent then fact-checked the other
claims against their sources the same day. Its corrections are applied here: one misquote, one overstated patent
claim relabelled as `INFERENCE`, and the GAN 12 M, GAN 13 and WR M V9 rows narrowed to what the sources state.

**Why.** ER9's anchored layout (2 off-axis pairs per edge, 3 per corner) does not fit the real-mechanism CAD
(`experiments/ER9_anchored_core_layouts/side_checks/README.md`). This report asks how real cubes place core magnets,
so that the next layout copies a buildable arrangement.

## Summary
- **On-axis corner pairs are the norm (`FACT`, several sources).** Every arrangement verified uses one magnet per
  corner on the corner's own body diagonal. It sits in the corner's foot (stalk) and faces one core magnet on the same
  axis. The core magnet is either at the end of a rod (GAN 11–15) or inside a plastic ball (ball cores). No source
  shows off-axis core-to-piece magnets.
- **Edges are optional and often repel.** In GAN 13 Maglev, edge magnets repel "the 8 core magnets" ([S5]). In MoYu
  WR M V9, edge magnets repel "the core magnets"; the count is not stated ([S7]). "20-magnet" cores add 12 edge-axis
  core magnets, which "in many designs" have the opposite polarity ([S3]).
- **Core magnets are added to the usual piece-to-piece magnets, not used instead of them** ([S4]: "Corner core
  magnetization, otherwise called a magnetic core, is usually used in conjunction with standard magnetization").
- **Magnets probably do not hold pieces on (`INFERENCE`).** Two patents describe how pieces are retained. In both,
  corner feet engage under the centres and the centres are sprung: [P6] "corner block feet and engaging feet",
  pressure spring; [P7] "rotating clamping leg". [P3] and [P8] describe maglev centres but not how corners and edges
  are held. [P2], [P4] and [P5] say nothing about retention. No source says magnets do not retain pieces.
- **Strength is tuned by radial gap.** MoYu's patent [P1] moves each core magnet radially; GAN 13 has a 6-level
  adjustment at the corners.
- **No source gives a core magnet's size, grade, gap or force.** The one dimension found is GAN 17's 17.5 mm ball core.

## (a) Cubes and their arrangements
| Cube | Core magnets | Acts on | Attract or repel | Placement; core type | Source |
|---|---|---|---|---|---|
| GAN 11 M Pro (2020) | 8 | corners | attract | Core end and "on the foot of the corner pieces"; rods | `FACT` [S1–S4] |
| GAN 11–15 | – | corners | – | Rod design "appeared in the GAN 11, GAN 12, GAN 13, GAN 14 and GAN 15" | `FACT` [S3] |
| GAN 12 M (2021) | "even more magnets"; count not stated | corners | repulsion claim `UNVERIFIED` (S2's article body no longer served; snippet only) | Longer corner-stalk magnets; "30 degree auto-alignment" | `FACT` [S4] for placement and alignment |
| GAN 13 Maglev (2022) | 8 | corners (polarity not stated); edges repel "the 8 core magnets" | edges repel | Corner strength adjustable in 6 levels; edge repulsion not adjustable; rods | `FACT` [S1, S5] |
| GAN 17 MagDrive | 20 in a 17.5 mm "micro ball core", plus 20 in the feet | corners and edges | core polarity not stated | Feet; ball | `FACT` [S6]; `INFERENCE`: 8 corners + 12 edges |
| MoYu WR M V9 Ball-Core | not stated | edges (corners not mentioned) | edges repel "the core magnets" | ball | `FACT` [S7] |
| Generic 8-magnet ball core | 8 | corners | attract | One core magnet per corner, attracting "a magnet positioned inside the foot of the corresponding corner"; ball | `FACT` [S3] |
| Generic 20-magnet ball core | 8 + 12 | corners, edges | extra 12 "do not always attract"; often opposite polarity | ball | `FACT` [S3] |

## (b) Dimensions
- GAN 17 ball core: 17.5 mm ([S6]).
- Centre-block magnets of D4 × 1 or D4 × 1.5 mm in CN209696259U ([P5]). These are not core magnets.
- No measured teardown giving gap, foot geometry or core magnet size was found.

## (c) Patents
- **[P1] CN116850572B**, "Center component of magic cube and magic cube".
  - Moyu Culture Co.; inventor Chen Yonghuang; priority and filing 2023-09-05, granted 2023-11-28.
  - `FACT` (re-read by the main session): the hub comprises a spherical shell holding eight first magnetic
    components. They move in guide grooves "extending in the radial direction", driven toward or away from the
    centre.
  - `FACT`: each corner's second magnetic component is opposite one of them in the reset state, and is "magnetically
    attracted" to it (claim 8).
  - Figures not read (scanned PDF).
- **[P2] CN220968048U**, Guangdong Yongjun Technology, filed 2024-04-17.
  - `FACT`: 3 corner-foot magnets repel 4 centre-block magnets, nearest at a 45° layer rotation.
  - `FACT`: a further corner-foot magnet attracts a magnet on the central body in the solved state.
- **Read, but with no core-to-piece magnets:**
  - [P3] US11484780B1 (Gan, 2021);
  - [P4] US12350597B2 (Gan, 2022; its ball shaft carries no magnets);
  - [P6] EP4257213B1 (Gan, 2022);
  - [P7] CN215585434U (2021);
  - [P8] CN220989608U (2023);
  - [P5] CN209696259U (2019).

## (d) Open designs
None could be verified (pages returned 403 or 429). See the unverified list.

## (e) `INFERENCE`: what is buildable and worth simulating
1. **On-axis corner pairs** run along the line the real corner foot follows. ER4 measured room on that axis for
   magnets of at least 9.8 mm diameter, so this placement fits.
2. **ER7's C52 (single on-axis core pairs) failed** because one on-axis pair gives no stiffness against the piece
   spinning about that axis. In commercial cubes, the piece-to-piece magnets that are always present supply it. The
   commercial pattern is therefore "M5-style piece-to-piece magnets plus on-axis corner–core pairs". ER9's
   measurements show both groups fit the real CAD (`side_checks/realfit/`).
3. **Edge-foot magnets repelling the 8 corner-axis core magnets** peak near a 45° turn. There, an edge's radial axis is
   about 9.7° from a body diagonal, against 35.3° at rest. This pushes the layer toward 0° or 90°, which matches the
   "auto-alignment" claims.
4. **Candidates to screen:**
   - (i) M5's layout plus 8 on-axis corner–core pairs, sweeping the gap;
   - (ii) (i) plus 12 on-axis edge-foot magnets repelling the 8 core magnets;
   - (iii) a 20-magnet core with the 12 edge-axis pairs attracting or repelling.
5. **Abstraction to record.** Commercial cubes do not hold pieces on with magnets. If the model relies on magnets for
   radial retention, that departs from real practice.

## Sources
- [S1] https://en.wikipedia.org/wiki/Gancube (CC BY-SA), citing GANCUBE "Magnetic System Evolution", 2024-10-22.
- [S2] https://www.gancube.com/blogs/blogs/gancube-s-magnetic-system-evolution, "GANCUBE Core Technology Evolution"
  (no author or date shown).
- [S3] https://speedcubing.org/blogs/news/the-evolution-of-magnets-in-speedcubes, "The Evolution of Magnets in
  Speedcubes" (no author or date shown). Re-read by the main session.
- [S4] https://speedcubeshop.com/a/blog/what-is-a-magnetic-core, Ari, 2021-10-11.
- [S5] https://speedcubeshop.com/a/blog/gan-13-maglev-overview, Jeremy Sheng, 2022-11-02.
- [S6] https://www.gancube.com/blogs/gan_news/gan-16-vs-gan-17-comparison-which-flagship-should-you-buy (dated
  "August 10th").
- [S7] https://speedcubeshop.com/a/blog/finding-the-best-wr-m-v9-moyu-weilong-wr-m-v9-3x3-review, Jeremy Sheng,
  2023-04-24.
- [P1]–[P8]: https://patents.google.com/patent/<number>/en, machine-translated text only.

## Unverified (snippets only)
- **Magnet counts:**
  - ES3: 8 or 20 core magnets.
  - MoYu YS3 M: 48–100 magnets in total.
  - MoYu Maple: "10-magnet ball-core".
  - WR M V9 20-magnet version (Jan 2024): "12 more core-magnets to repel magnets in the edge's foot".
  - X-Man Tornado V5 Pioneer: 8 corner-base and 12 repelling edge-base magnets.
- **Adjustment and alignment claims:**
  - GAN 11 M Pro: 3 strength levels.
  - GAN 14: "core positioning 4.0 … 40 degrees".
  - HuaMeng TG V2: 9 edge-tuning levels.
- **Open designs:**
  - MakerWorld 1065200: "16x Ø4x1.5" core magnets (one snippet attributes this to model 1202147 instead).
  - MakerWorld 2703836: 3 × 1.5 mm magnets.
  - MakerWorld MeiLong 3M V2 ball-core kit: 3 × 1.5 N38 core, 3 × 3 N38 corners.
  - Printables 354201: 4 × 1 magnets.
  - Printables 731463: 8 × 3 magnets.
  - Licences unknown.
- **Snippet-only patents:** CN221846022U, CN112894310A.
