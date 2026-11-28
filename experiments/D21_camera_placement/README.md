# D21: camera placement study (UNSCORED; G5 preparation; pilot seed 29001; 2026-11-28)

**Why:** Phase 5 (G5) needs camera-derived cube state. The Phase 3 plan lists a camera placement study as work that can
run in parallel. The user asked for it while G2 is in review. This is rendering only: no camera feeds any controller,
and no frozen file changes.

**Method (`camera_study.py`):**
- The G2 scene runs with the magnets on and stickers on (stickers are physics-invariant, P-110). It goes through the
  start sequence, arm B's approach and one U move. Snapshots: t0; after the approach; the move at 30, 45 and 60 %;
  the move end.
- Candidate cameras: 85 free cameras looking at the cube centre (0.5, 0, 0.30) m from 0.6 m. Azimuth every 30°;
  elevation from −90° (straight down) to +30° (from below the cube's height). MuJoCo convention: negative elevation
  looks down.
- For each snapshot and camera there are two segmentation renders at 160 × 120: as is, and with every robot geom
  hidden. Per cube face (its current outward direction in the core frame), **visible fraction** = sticker pixels with
  the robots ÷ sticker pixels without them.
- A camera "sees" a face if the fraction is ≥ 0.5 in **every** snapshot (the worst case over the grasp and turn). A
  greedy search picks the smallest camera sets that see all six faces.

**Faces at t0** (P-108 layout):
- U (core +z) faces arm B and D faces arm A.
- The two gripped sides (core ±x = world ±y) carry both arms' fingertips.
- The top faces up, and the **bottom faces the table and the stand**.

## Results (`FACT`; `results.json`)
Best single camera per face (worst-case visible fraction over the six snapshots):

| Face | Best worst-case fraction | Camera (azimuth, elevation) |
|---|---|---|
| U (toward arm B) | 0.85 | (240, −60) |
| D (toward arm A) | 1.00 | (0, −60) |
| side +y (gripped) | 0.60 | (270, −15) |
| side −y (gripped) | 0.61 | (90, −15) |
| top | 1.00 | (330, −30) |
| bottom | 1.00 | (120, +30), only from below the cube's height |

**Smallest covering sets (3 cameras each):**

| Constraint | Cameras: (az, el) → position (m) → faces added |
|---|---|
| none | (60, +30) → (0.24, −0.45, 0.00) → side −y, bottom, D; (240, −60) → (0.65, 0.26, 0.82) → top, U; (300, +30) → (0.24, 0.45, 0.00) → side +y |
| **cameras ≥ 0.14 m above the table** | (60, −30) → (0.24, −0.45, 0.60) → top, side −y, D; **(270, +15) → (0.50, 0.58, 0.145) → side +y, bottom**; (240, −60) → (0.65, 0.26, 0.82) → U |
| cameras at or above the cube centre | no full cover: **the bottom face is never seen** |

## Reading
- `INFERENCE`: three cameras can see every face through a grasp and a U turn. The bottom face needs one camera below the
  cube's height (about 0.15 m above the table in the second set). The gripped side faces are the worst: about 60 %
  visible at best, because both arms' fingertips cover them.
- `INFERENCE`: a fixed three-camera rig is a reasonable G5 starting point. The second set (no camera at table level)
  is the practical one.

## Limitations
- One seed, one U move, the G2 grasp only. Other faces' turns and regrasps (G4) will change the occlusion.
- Occlusion is by robot geoms only. Lighting, specular highlights, sticker colour separation, motion blur, lens models
  and resolution effects are not modelled. Visibility is not the same as recognisability.
- 160 × 120 renders; a face counts as absent below 20 sticker pixels without robots (edge-on).
- Fixed 0.6 m camera distance; mounts and cables are not checked.

**Reproduce (WSL, repo root):** `MUJOCO_GL=egl ~/.venvs/rubiknetic/bin/python experiments/D21_camera_placement/camera_study.py`
(about 10 min).
