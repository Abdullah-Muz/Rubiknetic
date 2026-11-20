# R1 — What published sources say about real-cube mechanics (2026-11-14/15)

Two searches were run by subagents under P-20, and their reports were checked by the main session:
1. English-language papers, manufacturers, retailers, forums and patents (2026-11-14).
2. Chinese-language sources, patents, toy safety standards, YouTube text, robotics papers and the WCA rules
   (2026-11-15).

Items verified by the main session on the primary page are marked **verified**. The rest are as the subagent
reported them, with the evidence types it gave.

## Bottom line
**No published source gives a measured corner-twist torque, twist angle or pop torque for a standard 55–57 mm cube.**
Turning torque for a 57 mm cube appears only in unverified forum snippets. A bench measurement (`PROTOCOL.md`) is the
only route to real-cube parity.

## Findings
| Topic | Finding | Evidence |
|---|---|---|
| Toy safety torque test | Parts a child can grip with thumb and forefinger must withstand **4 in·lb ±0.2 (0.45 N·m)**, applied within 5 s and held 10 s, or until 180° rotation, clockwise then counter-clockwise. Tension test: 15 lb (66.7 N). Scope: children over 36 and up to 96 months | **Verified**: 16 CFR §1500.53(a),(e),(f), https://www.law.cornell.edu/cfr/text/16/1500.53 (accessed 2026-11-15) |
| Other standards | EN 71-1 0.34 N·m; ISO 8124-1 / GB 6675.2 0.45 N·m | Test-lab summary (HK STC, 2020); the standards themselves are paywalled |
| Corner twist in practice | WCA Regulations list "pieces twisted in place" as a puzzle defect, and 5b3c lets a competitor "correct the corner piece by twisting it in place" | Subagent, from the WCA Regulations (version 1 Apr 2026); qualitative |
| Corner twist frequency | "occurs infrequently, only on certain 3x3 cubes" | Retailer blog (speedcube.com.au, 2015); anecdote |
| Turning torque | About 0.02–0.05 N·m for a speedcube; about 0.09 N·m for a standard Rubik's Cube | **Unverified**: forum snippets; the pages returned 403 |
| Corner cutting / auto-alignment | 45–60° forward, about 35° reverse, about 40° auto-alignment (Dayan Guhong MPro+, one reviewer, no method); 47° forward (GAN 11 M Pro); "reasonable corner-cutting … about 45 degrees" | Reviewer and retailer anecdotes; GAN claims "30° automatic alignment" (manufacturer) |
| Magnets | 48 magnets (3 per corner, 2 per edge), 4×2 mm discs, N35–N52 | Hobbyist builds and retailer pages; this matches the M4 layout |
| Mass and size | 94 g, 57 mm (YCB object set) | Calli et al., IEEE RAM 2015 |
| Giant cube | 6.0 N·m breakaway and 4.0 N·m running torque, on a 0.4 m, 4.6 kg cube | arXiv 2610.24610 (measured); not transferable |

## Use for the E1-6c corner-twist threshold (`INFERENCE`)
- **The standards give an engineering anchor, not real-cube parity.** A compliant toy's grippable parts survive
  0.45 N·m without detaching. That supports a criterion of the form "no pop and no invalid state at 0.45 N·m". It
  says nothing about how far a corner may twist.
- **Corners do twist in real use.** That argues against M2's "≤ 2° at 5 N·m" as a realism requirement.
- Any quantitative twist-angle threshold proposed without bench data would be set with knowledge of M4's unscored
  behaviour. It has to be disclosed as such.

## Piece clearance (added 2026-11-16, for the M5 pre-registration §0)
- **US 6,217,023 B1, "Spatial logic puzzle"** (Kremer; assignee Seven Towns Ltd), a **2×2×2** puzzle, not a 3×3
  (https://patents.google.com/patent/US6217023B1/en; accessed 2026-11-15 and 2026-11-16). `FACT`: it states "the
  clearance between pieces being of the order of 0.05 mm and being a matter for trial and error by the puzzle
  designer". It is the only numeric piece-clearance source found.
- **lulabs.net, stainless steel cube** (https://lulabs.net/machining/ss-cube/; accessed 2026-11-15). `FACT`: the
  builder held part tolerances to "within 0.002"" (0.05 mm), which is a dimensional tolerance, not a clearance. The
  page says moulded commercial cubes have looser tolerances, and that the steel pieces "fit snugly without significant
  play".
- No teardown, feeler-gauge or CT measurement of a commercial 3×3's piece clearance was found. A bench measurement
  (feeler gauge or CT, plus single-piece wobble under a small torque) would settle it.

## Addendum 2026-11-19: third search (O-09 re-check)
A subagent ran this search under P-20. The main session re-checked two items on their primary pages (marked
**verified**). One reported detail did not match the primary page and is noted below.

**Bottom line: unchanged.** No primary-page measurement was found of breakaway, running, corner-twist or pop torque, or
of magnet force in physical units, for a standard 55–57 mm cube. Nothing dated after 2026-11-15 adds one. The bench
protocol (`PROTOCOL.md`) remains the only route to real-cube values.

**Refinements to the "Turning torque" row above** (both still **unverified**; the primary pages return 403, and the
web archives could not be reached):
- **0.05 N·m vs 0.02 N·m.** speedsolving.com thread 76309 ("Torque on conventional cubes", opened 27 Jan 2020). In
  the snippets, **0.05 N·m** is the only reported, informal measurement, on a speedcube "set up to be sticky" for
  one-handed solving. **0.02 N·m** is a claim in the same reply that a speedcube can be set up to need that much; it
  is not a measurement.
- **Probable origin of 0.09 N·m.** The TwistyPuzzles museum entry for Oskar van Deventer's *Superclick Cube*
  (`puzzle.cgi?pkey=4697`) says, per the snippet: "Oskar even measured the torque needed to turn one face … ca. 2.7 Nm
  for the Superclick Cube compared with 0.09 Nm for a traditional Rubiks Cube". No method, date or cube model is
  given.

`INFERENCE`: both figures are single, undocumented hand measurements, good to an order of magnitude at best. They
are 4–14× below the sim's peak turning torque in `PROTOCOL.md` (0.32–0.72 N·m, gripper rig, an earlier model stage,
and a peak during a driven turn rather than a breakaway torque). They are too uncertain to calibrate the model.

| Source (accessed 2026-11-19) | What it establishes | Status |
|---|---|---|
| ruwix.com, "Corner cutting" | GAN 11 M Pro "47 degrees forward corner cutting"; RS3M 2020 "40-45-degree corner cutting forward and line to line reverse". The stated method is to "roughly measure the angle at which the cube automatically snaps to" | **verified**; retailer page, no author or date |
| arXiv 2609.33973, Liang et al., "FINGR: Learning Dexterous Hand Control for Real-World Rubik's Cube Solving" (v1 27 Sep 2026) | No torque or forgiveness data. **Discrepancy:** the subagent reported a 52 mm 3×3 with 15° / 18° turn thresholds, but the abstract refers to "ten scrambled 2×2×2 cubes". The body was not checked, so only "no torque data" is recorded | **verified** (abstract) |
| arXiv 1910.07113 (OpenAI, robot hand) | MuJoCo cube with bevelled cubelet edges (1.425 mm on a 1.9 cm cubelet) because a perfectly cubic model was "highly unforgiving"; "very rudimentary" dynamics calibration; no measured torque | Subagent, from the arXiv PDF; consistent with the earlier entry |
| GAN patent US11484780B1 ("Magnetic levitation magic cube") | Qualitative only: stronger positioning magnets give larger starting resistance | Subagent, primary page |
| speedcubeshop.com corner-cutting blog (2021); speedsolving.com thread 7655 (2007, a trigonometric method for measuring corner cutting) | Corner cutting over 45° claimed for modern cubes, without a method; a measuring method with one example (41.2°) | Subagent; the forum thread is snippet only |
| GAN, MoYu and QiYi product pages | Magnet strength is given only as levels (e.g. three strengths), never in physical units | Subagent; snippet only |
| Zieliński et al., *Industrial Robot* 34(5), 2007, DOI 10.1108/01439910710774377; UIUC ECE445 giant-cube reports | Force sensing used to avoid jamming (abstract); a giant cube with a ±5° design limit and no measured value | Subagent; no numbers for a standard cube |

**Not tried, by design.** The subagent's request to the Wayback availability API was refused by the session's
permission settings, and was not attempted another way. With the user's permission, a plain Wayback lookup might move
the two forum snippets to verified.

## Addendum 2026-11-19 (later the same day): archive lookups
The user approved a Web-archive lookup (P-62 item 6). The main session ran it and read the archived page itself.

- **0.09 N·m: now verified on an archived primary page.** TwistyPuzzles museum, "Superclick Cube"
  (https://web.archive.org/web/20220516192019/https://www.twistypuzzles.com/cgi-bin/puzzle.cgi?pkey=4697, snapshot
  2022-05-16, accessed 2026-11-19). The entry (inventor Oskar van Deventer, year 2014, 60 mm, 260 g) says: "Oskar even
  measured the torque needed to turn one face. ca. 2.7 Nm for the Superclick Cube compared with 0.09 Nm for a
  traditional Rubiks Cube."
  - It is still a single measurement with no method, and the Rubik's cube used is not identified.
  - **Also relevant to the core-magnet layout (ER4):** the Superclick Cube has "sixteen 12.7 mm diameter spherical
    magnets … placed in the corners and core", each pair holding 2.9 kg by the entry's account. This is a second
    documented corner-to-core magnet design, at hobby level, alongside the commercial ones ER4 found.
- **0.05 / 0.02 N·m: still unverified.** The Internet Archive has no copy of speedsolving.com thread 76309 (the
  availability API and a CDX search both returned nothing).
