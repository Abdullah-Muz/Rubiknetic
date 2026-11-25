# Turning torque: second search round (addendum, 2026-11-25)

> **Status:** research addendum; no simulation; negative result. Done by the main session on 2026-11-25 at the
> user's request ("can't we just do a round of research to find some sort of torque profile?"), because no physical
> cube is available for the O-09 bench measurement. It extends `TURNING_TORQUE_FINDINGS.md` (2026-11-21) and does
> not change it. Access date for every source: **2026-11-25**.

**Headline (`FACT` about the search; `INFERENCE` about what it means).** This round found **no new measured turning
torque and no torque-versus-angle profile** for any 3×3 cube. The 2026-11-21 conclusions stand:
- The only verified figure is 0.09 N·m (TwistyPuzzles, method not stated).
- A snippet-only bench report implies about 0.10–0.20 N·m breakaway.
- Nothing quantifies what magnets add.

INFERENCE: a public torque profile for a real cube very likely does not exist. Pinning one down needs a measurement
(O-09).

## What was searched (gaps left by the first round)
| Angle | Query or source | Outcome | Label |
|---|---|---|---|
| Chinese standards for cube turning force | 魔方 转动力矩 测试 N·m 标准; 魔方 行业标准 QB/T 转动 力矩 手感 检测 | No QB/T, GB or group standard with a cube turning-torque requirement found. The QB/T hits concern other products. | FACT (negative) |
| Chinese competition-equipment requirements | 中国魔方运动竞赛训练器具技术要求 征求意见稿 | A draft of that name (March 2026) is mentioned only by a third-party report (mffb.com.cn). The report quotes fault-tolerance angles (≥ 45° forward, ≥ 25° reverse) and adjustable tension, **not torque**. No official text was found. | UNVERIFIED (third party, no source cited) |
| Official sports-administration notice | https://www.sport.gov.cn/stzx/n5434/c29481290/content.html (社体字〔2026〕107号, 2026-03-16) | Read in full: a call for a competition-equipment sponsor (150 sets of timers, cubes, mats). No technical specification. | FACT (read) |
| Group standard T/ACCEM 144—2024 智力竞技产品 | https://www.ttbz.org.cn/Home/PdfFileStreamGet/c3QsMTIwNDA3 | The download failed (HTTP 504). A search summary says it covers smart-cube assembly gaps and weight tolerance, not torque. | UNVERIFIED |
| Magnetic vs non-magnetic, gauge measurements | speedcube turning torque measured torque gauge … | Only qualitative retailer text (magnets add stability and lock the layer). | FACT (negative) |
| Robot builds, motor current | Rubik's cube robot measured torque … mNm; GAN robot motor torque | Only sources already on record: speedsolving 76309, Twistopher-2, the UIUC reports and Marjerie Suresh. No GAN Robot motor specification was found. | FACT (negative) |
| Turning-force testers, patents | magic cube turning force tester patent … | Cube mechanism and smart-cube sensor patents with no turning-torque values: US20150076766A1, WO2021000580A1, CN111939552A. | FACT (negative; search summaries) |
| Theses and papers on cube friction | speedcube mechanism design thesis torque …; Rubik's cube layer friction torque … | None found. | FACT (negative) |
| Magnet pull force | speedcube magnet pull force newtons … | Only a community estimate formula (speedsolving thread 64019), no measurement. | UNVERIFIED |
| Re-reads of first-round snippet sources | speedsolving 76309 (403 again); Q-Bot Instructables and eng-tips 450924 (HTTP 200 but bot-check pages with no text); Medium/Yandex record robot (403); web.archive.org copy of 76309 (404) | Still unreadable. A search summary adds that the eng-tips thread mentions a dial torque wrench (in-lb) and that **detents add to the required force**. No value was seen. | UNVERIFIED |

## Side facts (not torque; context only)
- Retailer setup guides (cubenationshop.com, aicubetrainer.com): a well-set speedcube corner-cuts at about 45°, ideally
  55–60°. Factory tension is often too tight if corner cutting is below 35°. This is hobbyist guidance, not
  measurement. It bears on E1-5 (forgiveness), not on turning torque. `UNVERIFIED`.

## Consequence for the project (`INFERENCE`; decisions are the user's)
- Literature cannot calibrate the model's turning torque or its profile over the turn angle. Any G1 claim about
  turning-torque realism rests on the 0.09 N·m figure and the 0.10–0.20 N·m bracket, and must be disclosed as
  uncalibrated.
- The simulated profile (magnet detent plus contact) is a model prediction, not a fit to data.
- O-09 stays open. A physical measurement remains the only route: any 3×3 cube, a luggage scale or kitchen scale,
  and string, following `REAL_CUBE_MEASUREMENT_GUIDE.md`.
