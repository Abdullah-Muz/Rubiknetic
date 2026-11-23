# Magnet pocket walls and covers in real pieces (findings, 2026-11-22)

**Status:** research report; unscored; no simulation; no decision. Labels: `FACT` (stated by the named source),
`INFERENCE`, `ASSUMPTION`, `UNVERIFIED` (search snippet only, page not read). All sources accessed 2026-11-22. A
subagent compiled this report. Pages were read through a fetch tool that returns a model-written extract, so quoted
wording should be spot-checked against the page before it is relied on. Many cube-community pages (SpeedSolving,
MakerWorld, Printables, Thingiverse, MyMiniFactory) returned HTTP 403 or 429 and could not be read.

**Why.** Part G (`experiments/ER9_anchored_core_layouts/PROTOCOL.md`, P3 table, decision U1) reuses magnet positions
that, measured in the real-mechanism CAD, leave **0.175 mm** of wall over the corner magnets and **0.20–0.29 mm** of
core over the core magnets. The simulation's **0.4 mm** is its own `MagnetParams.wall` default, not a manufacturing
figure. Option F-C needs a sourced wall and cover for moulded magnet pockets. **The protocol already notes that a
threshold chosen after these misses were seen is post hoc and must be disclosed.** This report only presents evidence.

## Summary
- **No source gives a wall, cover, pocket depth or protrusion for any commercial speedcube magnet.** That covers
  piece magnets and core magnets. Nothing was found that either supports or rules out 0.175 mm.
- **Commercial retention is mechanical capture or glue (`FACT`).**
  - GAN's maglev patent [C1] says the edge magnets sit in mounting grooves. Each magnet is "pressed by the color
    sheet" and "not attached to an inner wall of the block by glue".
  - GAN's "visible magnetic cabins" patent [C2] puts magnets in "transparent" cabins held by pressing seats. The edge
    cabins have an "openable" transparent end cover.
  - GAN's own page lists "adhesive magnetization", "see-through capsules" and "magnetic positioning slots" [C7].
  - A retailer installs extra 4 × 1 mm magnets "behind the magnets already attached to the piece", without glue [C6].
  - The WR M 2021 core kit snaps together, and its corner magnets are superglued into "a small hole in the stem" [C5].
  - No patent read states whether plastic lies between a magnet's face and the neighbouring piece.
- **Ball-core magnets are enclosed in plastic (`FACT`), thickness unknown.** They are "enclosed inside a spherical
  plastic structure" [C4]. MoYu's patent [C3] puts each core magnet in its own "housing shell" inside a spherical
  shell. That is two plastic layers between magnet and core surface (`INFERENCE`).
- **Moulding guides put ordinary walls well above our numbers (`FACT`).**
  - Recommended walls: ABS 1.14–3.56 mm, PC 1.02–3.81 mm, nylon 0.76–2.92 mm [M1, M5].
  - Protolabs flags walls "under 0.015-0.020 in. (0.381-0.508mm)" as too thin, depending on material [M3].
  - Micro-moulding guidance goes down to "0.004 in. (0.1 mm) or thicker" for thin sections, and specialists say such
    rules "break down" at the limit [M7].
  - No guide gives a skin thickness over an insert or a magnet pocket.
- **Magnet-specific guidance (`FACT`).**
  - Overmoulding heat "will partially demagnetize most magnets" [M9].
  - 1 mm is the stated minimum plastic wall for a "durable hermetic seal" [M9].
  - One magnet supplier advises against pressing bare magnets into an interference fit. It advises recessing the
    magnet "slightly below the housing face" rather than leaving it proud [M10].
- **Standard magnet tolerance is ±0.1 mm (`FACT`, [M11]).** That is about 57 % of 0.175 mm.

## Q1. Piece magnets in commercial cubes
| Cube or source | How the magnet is held | Wall, cover, depth or protrusion stated? | Label, source |
|---|---|---|---|
| GAN maglev (US11484780B1, filed 2021-07-02) | Edge magnets in "magnet mounting grooves" near the edge body's opening. The groove "abuts against one end"; "pressing blocks" on the colour sheet abut the other. "Not attached … by glue" | No dimensions. Not stated whether the groove has a wall toward the neighbour. Corner magnets not described | `FACT` [C1] |
| GAN "visible magnetic cabins" (EP4257213B1, priority 2022-04-07) | Corner: three "transparent visible" cabins; "magnet pressing seat … directly press the magnet". Edge: cabins at each end of a strut, with a "transparent end cover … openable" | No thickness, no material beyond "transparent", no statement on a wall facing the neighbour | `FACT` [C2] |
| GAN (company page, undated) | "Adhesive magnetization"; "See-through capsules"; "Magnetic positioning slots" | None | `FACT` [C7] |
| GAN356 X | "interchangeable magnet capsules" | None; the sentence is uncited in Wikipedia | `FACT` [C8] |
| MoYu RS3M 2020 (retailer Cuboss) | Factory magnets in the edges. The extra 4 × 1 mm N50 magnets go "behind the magnets already attached" and stay without glue | None. `INFERENCE`: the edge pocket opens toward the piece interior and has at least 1 mm of spare depth | `FACT` [C6] |
| MoYu WR M 2021 corner (retailer guide) | Small magnet glued into "a small hole in the stem" of the corner | None | `FACT` [C5] |
| DIY 3x3 (WeiLong GTS, 2017) | 48 magnets of 2 × 4 mm N52, glued with Gorilla Glue after removing the piece caps | None | `FACT` [C9] |
| Magnetic dice cube (not a speedcube mechanism, 2008) | 5 × 2 mm magnet "countersunk" into a hole drilled in each contact surface, then superglued | Flush or recessed not stated | `FACT` [C11] |
| Speed cubes generally | Pieces "typically" injection moulded, ABS "commonly used" | None | `FACT` [C10] |

No teardown with measurements, and no modding guide giving drill depth or flush mounting for a speedcube, was found.

## Q2. Core and ball-core magnets
| Source | How held | Cover thickness stated? | Label |
|---|---|---|---|
| Ball cores generally | Corner–core magnets "enclosed inside a spherical plastic structure surrounding the central core" | No | `FACT` [C4] |
| GAN rod cores | Magnets "at the ends of exposed rods" from the core | No; fixing not stated | `FACT` [C4] |
| MoYu ball core (CN116850572B, granted 2023-11-28) | "The magnet 23 is disposed in the housing shell 22". "The spherical shell 14 encloses … the first magnetic component 2". The components slide in radial guide grooves | No dimensions. `INFERENCE`: two plastic layers lie between magnet and core surface | `FACT` [C3] |
| MoYu WR M 2021 core kit | Two halves pressed together until they snap | No | `FACT` [C5] |
| GAN 17 | 17.5 mm ball core (earlier report) | No | `FACT`, CORE_MAGNET_PRACTICE_FINDINGS [S6] |

## Q3. Moulding design guidance
| Item | Value | Label, source |
|---|---|---|
| Recommended wall, ABS | 0.045–0.140 in (1.143–3.556 mm) | `FACT` [M1, M5]; Protolabs says its table is "adapted from manufacturingcenter.com" |
| Recommended wall, PC | 0.040–0.150 in (1.016–3.81 mm) | `FACT` [M1, M5] |
| Recommended wall, nylon / acetal | 0.030–0.115 in (0.762–2.921 mm) / 0.030–0.120 in | `FACT` [M1, M5] |
| A second vendor's ranges | ABS 1.2–3.5, PC 1.0–4.0, nylon 0.8–3.0 mm; nominal "2-3mm" | `FACT` [M4] |
| "Too thin" flag | "under 0.015-0.020 in. (0.381-0.508mm) depending on material"; PC described as hard to fill in thin walls | `FACT` [M3] |
| Relative rule | Walls "no less than 40 to 60 percent that of adjacent walls" | `FACT` [M2] |
| No universal minimum | "no single, universal minimum wall thickness" | `FACT` [M5] |
| Flow length ratio | ABS 30–50, PC 30–100, PA 140–340, POM 100–200 | `FACT` [M5] |
| Thin wall (packaging) | < 0.025 in (0.62 mm) with flow length / thickness > 200 | `FACT` [M6], citing a 2006 resin datasheet |
| Micro-moulding guideline | Thin sections "0.004 in. (0.1 mm) or thicker". Accumold: such rules "break down when you start to push the limits" | `FACT` [M7] |
| Micro-moulding test (2013) | A 0.003 in (76 µm) section, 42:1 length: 4 of 11 resins filled full length. Experts suggested ≥ 0.015 in (0.38 mm) | `FACT` [M8] |
| Walls over inserts | Protolabs' insert-moulding page gives no thickness over or around inserts | `FACT` [M12] (absence) |
| Overmoulding magnets | Heat "will partially demagnetize most magnets" (re-magnetised after moulding). "The minimum plastic wall thickness to form a durable hermetic seal is 1mm" | `FACT` [M9] |
| Press-fit pockets | Do not press bare magnets in an interference fit. Use a lip, cover or snap; recess "slightly below the housing face". Bond line "tens of microns to a few tenths of a millimetre" | `FACT` [M10]; no wall or recess number |
| Magnet tolerance | Standard ±0.1 mm on diameter and height below 50 mm; custom ±0.05 mm below 20 mm. Another supplier: ±0.003 in for a 1/4 in cylinder | `FACT` [M11, M13] |

## Q4. Open 3D-printed magnetic cubes
No page could be read; all returned 403. The snippets are in the Unverified list. General printing guidance, not
cube-specific:
- add 0.2–0.4 mm to the magnet's diameter and thickness, and keep "at least 1–2mm of wall thickness around the slot"
  (`FACT` [P1]);
- Tom Parker's magnetic cube embeds magnets by pausing the print; no dimensions or licence stated (`FACT` [P3]).

No cube design with a stated skin thickness or flush mounting, and its licence, was verified.

## Q5. Piece gaps and tolerances
- **Injection-moulded speedcubes: no figure found.**
- **3D-printed puzzles:** Sculpteo advises a "large" clearance "reduced to 0,4mm", with a different clearance for
  competition cubes "to anticipate the wear of plastic" (`FACT` [P2]; process not named).
- **Internal check, not resolved:** `CUBE_MECHANISM_FINDINGS.md` §3 reports the GrabCAD CAD's neighbour clearance as
  0.033–0.038 mm. `side_checks/README.md` gives that CAD's "piece gap" as 0.25 mm. These may measure different
  things: smallest clearance anywhere against the face gap at the magnet. This should be confirmed before 0.25 mm is
  used in a wall argument.

## `INFERENCE`: how the evidence relates to our three numbers
No decision is recommended here. A threshold chosen from this evidence after the misses were seen is post hoc
(PROTOCOL, F-C).
1. **0.4 mm (simulation default).** This is near the lower end of Protolabs' "too thin" flag (0.381–0.508 mm). It is
   below every general recommended wall range (ABS lower bound 1.14 mm). It is above the micro-moulding guideline
   (0.1 mm). No source ties a number to a magnet pocket, so 0.4 mm is neither confirmed nor refuted as a cube figure.
2. **0.175 mm (corner wall) and 0.20–0.29 mm (core cover).**
   - These are below Protolabs' "too thin" flag and well below the general ranges. They are inside what
     micro-moulding specialists report achieving (≥ 0.1 mm guideline).
   - The 2013 test shows that much thinner sections (76 µm) filled in some resins over a 42:1 length.
   - A skin over a 4 mm pocket fills across about 2–4 mm. That is an L/T of about 11–23 at 0.175 mm, under Fictiv's
     ABS flow ratio of 30–50. This is a rough local comparison: flow ratio is defined from the gate, so it does not
     show that such a skin moulds well.
   - If the adjacent piece wall is about 1 mm (`ASSUMPTION`; real pieces are hollow and unmeasured), 0.175 mm is 18 %
     of it, against the 40–60 % rule.
3. **Exposed or flush magnets** would make the wall 0 by construction.
   - GAN's open, transparent and capped cabins and MoYu's open-from-inside edge pockets [C1, C2, C6] are consistent
     with magnets whose wall toward the neighbour is a separate part, thin, or absent. No source says which.
   - Supplier guidance [M10] prefers slightly recessed to proud magnets.
4. **Tolerance scale.**
   - Standard magnet tolerance (±0.1 mm) is about 57 % of 0.175 mm and 25 % of 0.4 mm. If a magnet is seated against
     a moulded skin, the mould sets the skin and the magnet tolerance moves the magnet's far end.
   - The gap between 0.175 and 0.4 mm (0.225 mm) is about two standard magnet tolerances.
5. **Core cover in ball cores.** MoYu's double enclosure [C3] suggests the real cover is the sum of two shells. No
   thickness is stated, so the evidence does not show whether that sum is above or below 0.20–0.29 mm.
6. **What would settle it.** Calipers or a CT scan on a real piece and core (`REAL_CUBE_MEASUREMENT_GUIDE.md`), or a
   manufacturer drawing. No web source substitutes for that.

## Sources (all accessed 2026-11-22)
- [C1] https://patents.google.com/patent/US11484780B1/en, "Magnetic levitation magic cube", Guangzhou Ganyuan
  Intelligent Technology; inventor Ganyuan Jiang; filed 2021-07-02, granted 2022-11-01 (machine text).
- [C2] https://patents.google.com/patent/EP4257213B1/en, "Magic cube with visible magnetic cabins", Gan Cube;
  inventor Ganyuan Jiang; priority 2022-04-07 (CN202220802196.6U), B1 2024-11-20. The last 13.5 k characters were not
  read.
- [C3] https://patents.google.com/patent/CN116850572B/en, Moyu, granted 2023-11-28 (machine translation).
- [C4] https://speedcubing.org/blogs/news/the-evolution-of-magnets-in-speedcubes (no author or date shown).
- [C5] https://speedcubeshop.com/a/blog/how-to-install-core-magnets-for-moyu-weilong-wr-m-2021-maglev-lite, Ari,
  2022-07-13.
- [C6] https://cuboss.com/shop/moyu-rs3m-2020/ (retailer, undated).
- [C7] https://www.gancube.com/pages/advanced-cubers (undated; the last 3 k characters were not read).
- [C8] https://en.wikipedia.org/wiki/Gancube (CC BY-SA); the GMS sentence carries no inline citation.
- [C9] https://msrose.github.io/blog/Making-my-own-magnetic-Rubiks-cube, Michael Rose, 2017-05-23.
- [C10] https://speedcubeshop.com/a/blog/how-are-speed-cubes-made, "Rafael", 2023-12-28.
- [C11] https://www.supermagnete.de/eng/Magnet-applications/Magnetic-Version-of-the-speed-cube, "Joe, Dublin",
  2008-09-05 (customer application).
- [M1] https://protolabs.com/services/injection-molding/plastic-injection-molding/design-guidelines (no date; table
  "adapted from manufacturingcenter.com").
- [M2] https://www.protolabs.com/resources/design-tips/improving-part-design-with-uniform-wall-thickness/ (no date).
- [M3] https://www.protolabs.com/resources/blog/thin-wall-injection-molding/, Protolabs, 2022-06-08.
- [M4] https://www.fictiv.com/specifications/injection-molding (no date).
- [M5] https://www.fictiv.com/articles/wall-thickness-recommendations-for-injection-molding, Steve Melito, 2023-01-13.
- [M6] https://en.wikipedia.org/wiki/Thin-wall_injection_molding (CC BY-SA), citing an Evalene PHJ4501 datasheet
  (JG Summit, 2006).
- [M7] https://www.machinedesign.com/medical-design/article/21150387/small-parts-design-for-micromolding-fuels-miniature-component-applications,
  Rehana Begg, 2020-12-15.
- [M8] https://medtechintelligence.com/column/ask-the-engineer-micro-molding-material-selection/amp, Accumold white
  paper, 2013-09-30.
- [M9] https://amazingmagnets.com/magnetology/overmolding-magnets-in-plastic/, Luke Bilisoly, 2026-04-23.
- [M10] https://radialmagnet.com/magnet-assembly-retention-design/, Radial Magnets ("last reviewed july 2026").
- [M11] https://www.magfine.it/en/user_data/size.php (no date).
- [M12] https://www.protolabs.com/services/injection-molding/insert-molding/design-guidelines/ (no date).
- [M13] https://www.apexmagnets.com/news-how-tos/magnet-dimensional-tolerances, 2018-07-27.
- [P1] https://kingroon.com/blogs/3d-printing-guides/how-to-embed-magnets-into-3d-prints, MadisonJames, 2025-03-31.
- [P2] https://3dprint.com/129649/sculpteo-rubiks-cube/, Michelle Matisons, 2016-04-17 (reporting Sculpteo's advice).
- [P3] https://hackaday.com/2019/02/16/the-magnetic-rubiks-cube, 2019-02-16, linking tomparker.co/magnetic-rubix
  (that site did not resolve).

## Unverified (snippets only, or pages not readable)
- **Commercial cubes:**
  - GAN, from a search snippet of its magnetic-system history: glued magnets' "glue would get weaker over time, and
    the magnets would fall off"; GAN460 M used "clear capsules … outside the core".
  - GAN356 M: "48 visable magnet capsules", held by "positioning slots and pillars"; GMC "precisely capped into the
    notches". The GAN pages redirected to the homepage.
  - GAN 356 ME: magnets covered by "tinted plastic" (customer comment).
  - RS3 M upgrade kit: magnets shifting after drops, with a buyer advising glue (SpeedCubeShop, HTTP 429).
- **SpeedSolving posts (HTTP 403):**
  - "Plastics of modern cubes are made to be a lot thinner to make magnets feel strong enough";
  - a reply that flush-mounting is not done because of the cost of drilling and aligning holes;
  - "Corner-to-core magnets pop out" and "YS3M BC loose magnet" threads (contents unknown).
- **Open designs (HTTP 403):**
  - MakerWorld 1065200: a "very small drop of superglue" tip, and 16 × Ø4 × 1.5 core magnets glued;
  - MakerWorld 1202147: the "magnet must sit completely in the socket";
  - MakerWorld community post 968465: about 0.2 mm cavity clearance, raised versus recessed magnets, and a 0.4 mm top
    layer, watching until two layers cover the magnet;
  - MakerWorld 680441: hidden 4 × 2 magnets;
  - MakerWorld 2703836: 3 × 1.5 mm magnets;
  - Printables 354201: 4 × 1 magnets;
  - Printables 731463;
  - Thingiverse 1952776: 10 × 2 and 5 × 2 magnets.
  - Licences are unknown for all of these.
- **Moulding:**
  - Micro-moulding walls of 25 µm (ASME) and 36 µm (Knowles);
  - crush-rib interference of about 0.25 mm (RapidDirect);
  - SolidWorks DFMXpress minimum wall 2.0 mm.
- **Gaps:**
  - Sculpteo's 0.2 / 0.5 mm small / large clearances (blog, HTTP 403);
  - a MyMiniFactory cube with 0.1 mm at the pivots and 0.5 mm elsewhere;
  - a keyboard-case guide giving 0.5–0.8 mm moulded gaps (not cubes);
  - a B2B guide giving mould precision ≤ 0.05 mm for cube makers.
