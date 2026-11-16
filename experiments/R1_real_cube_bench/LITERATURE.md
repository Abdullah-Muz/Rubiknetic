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
