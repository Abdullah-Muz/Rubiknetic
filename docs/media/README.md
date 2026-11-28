# Media: the G2 two-arm U turn (rendering of the simulation)

These GIFs are **renderings of the MuJoCo simulation**. They are not video of real hardware. They show one unscored run
on pilot seed **29001** (never a scored seed; scored G2 seeds are 30000–30999). They are illustrations, not evidence:
the G2 result is in [`../../experiments/E8_scored_g2/G2_REPORT.md`](../../experiments/E8_scored_g2/G2_REPORT.md).

| File | What it shows | Size | Frames / duration | Speed |
|---|---|---|---|---|
| `g2_two_arm_u_turn.gif` | Whole sequence. The cube settles on the stand, arm A closes on D+E, and the stand drops away. Arm B approaches, closes on the U layer, rolls its wrist through a U quarter turn, releases and rolls back | 480 × 360, 1.02 MB | 74 rendered frames (+ first/last held), 5.95 s, looping | **2× real time**: one frame per 0.14 s of simulated time, shown for 70 ms (~14.3 fps) |
| `g2_u_turn_closeup.gif` | Close-up of the cube during the move only: arm B settles, closes, turns U, releases and rolls back | 360 × 270, 0.92 MB | 68 rendered frames (+ held), 5.53 s, looping | **1× real time**: one frame per 0.07 s of simulated time, shown for 70 ms |

Each frame is captioned with the simulated time and the current phase. The phase label is derived from the
controller's own commands (stand and gripper set-points, and the move's `rolling` flag), not from the cube state.

## Scene and physics
- The scene is built exactly as a G2 trial builds it: `experiments/E8_scored_g2/trials.py`
  `configure({}, start_draw(29001))`, the frozen G2 defaults (grip 20 N, K_P 4000, pad μ 0.8, F/T guard on, stand
  on), then `TA.TwoArm(L, HC, 20 N)`, `approach()`, and `move(parse("U")[0])`.
- **The magnets are on** (P-131). In this run the magnet force was evaluated at all 20,817 simulation steps (0 steps
  without it), with near-pair tilt ≤ 1.62°.
- **Visual-only differences from the scored configuration:** `TA.STICKERS = True` and `TA.ENV = True` (coloured
  stickers; sky, wood table, floor and lights). Both are visual only, with no mass and no collision. The project
  showed them to be physics-identical by an identical final qpos SHA-256 with and without them (P-110, P-112). Scored
  runs have them off.
- **Outcome of this run** (from the render script's own summary; unscored):
  - simulated time 10.41 s;
  - U turn error −0.13°, no guard stop, F/T peak |τ_z| 0.167 N·m;
  - the final cube state, observed by the independent readout, is the U move;
  - stand drop shift 0.11 mm.
- **Capture method.** The scene's `step(n)` is replaced by n calls of the original `step(1)`. This is the same loop, so
  physics is unchanged. Every 0.07 or 0.14 s of simulated time a copy of `qpos` is kept. After the run, the magnet
  callback is uninstalled and the copies are rendered on a separate `MjData` with `mj_forward`.

## Cameras (MuJoCo free cameras)
| GIF | lookat (m) | distance | azimuth | elevation |
|---|---|---|---|---|
| wide | (0.5, 0, 0.30) | 0.85 m | 115° | −28° |
| close-up | (0.5, 0, 0.30) | 0.24 m | 130° | −35° |

Arm A (holder) is on the left and arm B (turner) on the right. The cube's U face points at arm B.

## How it was made
- **Code:** the repository at commit `fbca90c`. The commits after it at render time (`f4f5e0b`, `b5deb88`) touch only
  documents and new D24 scripts, not the scene. No frozen path was modified.
- **Environment:**
  - WSL Ubuntu-24.04;
  - project venv `~/.venvs/rubiknetic` (MuJoCo 4.0.1), offscreen rendering with `MUJOCO_GL=egl` and
    `mujoco.Renderer`. Nothing was installed into the project venv.
- **Encoder:**
  - Pillow 13.0.0 in a throwaway venv **outside the repository**, `/tmp/giftools`, created with
    `uv venv /tmp/giftools && uv pip install --python /tmp/giftools/bin/python pillow`. ffmpeg is not installed in WSL.
  - GIFs use a 128-colour median-cut palette per frame, no dithering, and `optimize=True`.
  - The encoder reads only the PPM frames and JSON labels that the project venv wrote to `/tmp/rubiknetic_gif`.

```bash
# WSL, repository root
MUJOCO_GL=egl ~/.venvs/rubiknetic/bin/python docs/media/make_gif.py render   # simulate (~5-8 min) and render frames
MUJOCO_GL=egl ~/.venvs/rubiknetic/bin/python docs/media/make_gif.py frames   # re-render saved poses (to change cameras)
/tmp/giftools/bin/python docs/media/make_gif.py encode                       # write the two GIFs here
```

The intermediate files in `/tmp/rubiknetic_gif` (poses, labels, frames, `render_info.json`) are not part of the
repository.
