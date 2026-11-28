"""Renders the G2 two-arm scene doing one U quarter turn and encodes it as GIFs (UNSCORED; rendering only).

Two stages, run in two different Python environments so that nothing is installed into the pinned project venv:

  1. render  (project venv, MuJoCo, EGL): builds the G2 scene exactly as `experiments/E8_scored_g2/trials.py` does
     (`configure({}, start_draw(29001))`, pilot seed 29001), then switches on the visual-only stickers and room
     (`TA.STICKERS = TA.ENV = True`; physics-identical, P-110/P-112). It runs the start sequence (cube settles on the
     stand, arm A closes, the stand drops away), arm B's approach, and one `U` move (arm B closes, rolls J7 by a
     quarter turn, opens, rolls back). Magnets are on (P-131). Every SAMPLE steps the generalized positions are
     copied; after the run the magnets are uninstalled and the copies are rendered offscreen to PPM files in
     OUT (default /tmp/rubiknetic_gif). The physics is not touched by the capture: `step(n)` is replaced by n calls
     of the original `step(1)`, which is the same loop.
  2. encode  (any Python with Pillow only; no MuJoCo, no numpy): reads the PPM frames and labels, draws a caption,
     quantizes to an adaptive palette and writes the GIFs into docs/media/.

Usage (WSL, repo root):
  MUJOCO_GL=egl ~/.venvs/rubiknetic/bin/python docs/media/make_gif.py render   # simulate (~5 min) + render frames
  MUJOCO_GL=egl ~/.venvs/rubiknetic/bin/python docs/media/make_gif.py frames   # re-render saved poses only (cameras)
  /tmp/giftools/bin/python docs/media/make_gif.py encode        # a throwaway venv with Pillow (see README.md)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = Path(os.environ.get("RUBIKNETIC_GIF_TMP", "/tmp/rubiknetic_gif"))
SEED = 29001                    # pilot seed (never 30000-30999, the scored range)
W, H = 480, 360                 # wide view
WC, HC_ = 360, 270              # close-up
DT = 0.0005                     # M7 timestep (trials.SIM_DT)
WIDE_EVERY_S = 0.14             # wide: one frame per 0.14 s of simulated time, shown for 70 ms -> 2x real time
CLOSE_EVERY_S = 0.07            # close-up: one frame per 0.07 s of simulated time during the move, shown for 70 ms -> 1x
FRAME_MS = 70                   # ~14.3 fps
WIDE_CAM = {"lookat": (0.5, 0.0, 0.30), "distance": 0.85, "azimuth": 115.0, "elevation": -28.0}
CLOSE_CAM = {"lookat": (0.5, 0.0, 0.30), "distance": 0.24, "azimuth": 130.0, "elevation": -35.0}


def render() -> None:
    import importlib.util

    import mujoco
    import numpy as np
    os.environ.setdefault("MUJOCO_GL", "egl")
    spec = importlib.util.spec_from_file_location("trials", REPO / "experiments" / "E8_scored_g2" / "trials.py")
    T = importlib.util.module_from_spec(spec)
    sys.modules["trials"] = T
    spec.loader.exec_module(T)
    from rubiknetic.cube_logic import parse

    T.configure({}, T.start_draw(SEED))
    T.TA.STICKERS = True        # visual only (contype = conaffinity = 0, density 0), P-110
    T.TA.ENV = True             # visual only room, P-112
    wide_n, close_n = round(WIDE_EVERY_S / DT), round(CLOSE_EVERY_S / DT)
    wide, close = [], []        # (time, label, qpos)
    st = {"stage": "start", "k": 0, "rolled": False}

    class Recorder(T.TA.TwoArm):
        def label(self) -> str:
            d, m = self.d, self.m
            if st["stage"] == "start":
                if d.ctrl[m.actuator("stand_z").id] < 0.0:
                    return "Start: the stand drops away; arm A holds the cube"
                if d.ctrl[m.actuator("gripper").id] > float(m.actuator_ctrlrange[m.actuator("gripper").id, 0]):
                    return "Start: arm A closes on the cube (cube on the stand)"
                return "Start: the cube settles on the stand"
            if st["stage"] == "approach":
                return "Arm B approaches the U layer (open gripper)"
            if self.acc.get("rolling"):
                st["rolled"] = True
                return "Arm B rolls its wrist: U layer quarter turn"
            if st["rolled"]:
                return "Arm B releases and rolls back"
            if d.ctrl[self.gB] > self.th_open:
                return "Arm B closes on the U layer"
            return "Arm B settles at the grasp pose"

        def step(self, n: int) -> None:
            for _ in range(n):
                super().step(1)     # identical to step(n): TwoArm.step loops n times over the same body
                st["k"] += 1
                q = self.d.qpos.copy()
                if st["k"] % wide_n == 0:
                    wide.append((float(self.d.time), self.label(), q))
                if st["stage"] == "move" and st["k"] % close_n == 0:
                    close.append((float(self.d.time), self.label(), q))

    r = Recorder(T.L, T.HC, T.DEFAULTS["grip"])
    st["stage"] = "approach"
    r.approach()
    st["stage"] = "move"
    pm = r.move(parse("U")[0])
    obs = r.ro.observe(r.d)
    mags = r.magnet_stats()
    T.MagnetSystem.uninstall()          # render on a separate MjData with no passive callback
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fr in (("wide", wide), ("close", close)):
        np.save(OUT / f"qpos_{name}.npy", np.array([q for _, _, q in fr]))
        (OUT / f"labels_{name}.json").write_text(json.dumps([{"t": round(t, 3), "label": lab} for t, lab, _ in fr]))
    info = {"seed": SEED, "commit_note": "see README.md", "sim_time_s": float(r.d.time), "n_wide": len(wide),
            "n_close": len(close),
            "start": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.start.items() if k != "contacts"},
            "move_turn_error_deg": pm["turn_error_deg"], "move_jam_stop": pm["jam_stop"],
            "move_ft_tau_z_max_Nm": pm["ft_tau_z_max_Nm"], "final_observed_state_valid": bool(obs.valid),
            "final_state": str(obs.state) if obs.valid else None, "magnets": mags}
    (OUT / "render_info.json").write_text(json.dumps(info, indent=1, default=str))
    print(json.dumps({k: info[k] for k in ("sim_time_s", "n_wide", "n_close", "move_turn_error_deg",
                                           "move_jam_stop", "move_ft_tau_z_max_Nm")}, indent=1, default=str))
    frames(m=r.m)


def frames(m=None) -> None:
    """Renders the saved generalized positions (OUT/qpos_*.npy) to PPM files; rebuilds the visual model (no
    simulation) when called on its own, e.g. to try another camera."""
    import mujoco
    import numpy as np
    os.environ.setdefault("MUJOCO_GL", "egl")
    if m is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("trials", REPO / "experiments" / "E8_scored_g2" / "trials.py")
        T = importlib.util.module_from_spec(spec)
        sys.modules["trials"] = T
        spec.loader.exec_module(T)
        T.configure({}, T.start_draw(SEED))
        T.TA.STICKERS = T.TA.ENV = True
        m = T.TA.build(T.L, T.HC, T.DEFAULTS["pad_mu"])[0]
        T.MagnetSystem.uninstall()

    def save(sub, w, h, cam_cfg):
        qs = np.load(OUT / f"qpos_{sub}.npy")
        labels = json.loads((OUT / f"labels_{sub}.json").read_text())
        d = OUT / sub
        d.mkdir(parents=True, exist_ok=True)
        for f in d.glob("*.ppm"):
            f.unlink()
        ren = mujoco.Renderer(m, h, w)
        dd = mujoco.MjData(m)
        cam = mujoco.MjvCamera()
        cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        cam.lookat[:] = cam_cfg["lookat"]
        cam.distance, cam.azimuth, cam.elevation = cam_cfg["distance"], cam_cfg["azimuth"], cam_cfg["elevation"]
        for i, q in enumerate(qs):
            dd.qpos[:] = q
            mujoco.mj_forward(m, dd)
            ren.update_scene(dd, camera=cam)
            img = ren.render()
            with open(d / f"{i:04d}.ppm", "wb") as fh:
                fh.write(f"P6 {w} {h} 255\n".encode() + np.ascontiguousarray(img).tobytes())
        ren.close()
        (d / "labels.json").write_text(json.dumps(labels, indent=0))
        (d / "camera.json").write_text(json.dumps(cam_cfg))

    save("wide", W, H, WIDE_CAM)
    save("close", WC, HC_, CLOSE_CAM)
    print(f"frames written to {OUT}")


def encode() -> None:
    from PIL import Image, ImageDraw, ImageFont

    def font(size):
        try:
            return ImageFont.load_default(size=size)
        except TypeError:                       # Pillow < 10.1
            return ImageFont.load_default()

    def caption(img, top, bottom, size):
        im = img.convert("RGB")
        dr = ImageDraw.Draw(im)
        f = font(size)
        for text, y in ((top, 4), (bottom, im.height - size - 8)):
            x0, y0, x1, y1 = dr.textbbox((6, y), text, font=f)
            dr.rectangle((x0 - 3, y0 - 2, x1 + 3, y1 + 2), fill=(255, 255, 255))
            dr.text((6, y), text, fill=(20, 20, 20), font=f)
        return im

    def build(sub, out_name, top, size, hold_end=8, hold_start=3):
        d = OUT / sub
        labels = json.loads((d / "labels.json").read_text())
        frames = []
        for i, lab in enumerate(labels):
            img = Image.open(d / f"{i:04d}.ppm")
            frames.append(caption(img, top, f"t = {lab['t']:.2f} s   {lab['label']}", size))
        frames = [frames[0]] * hold_start + frames + [frames[-1]] * hold_end
        pal = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
        out = HERE / out_name
        pal[0].save(out, save_all=True, append_images=pal[1:], duration=FRAME_MS, loop=0, optimize=True,
                    disposal=1)
        n = len(pal)
        print(f"{out_name}: {n} frames, {n * FRAME_MS / 1000:.2f} s, {1000 / FRAME_MS:.1f} fps, "
              f"{out.stat().st_size / 1e6:.2f} MB, {frames[0].width}x{frames[0].height}")

    build("wide", "g2_two_arm_u_turn.gif", "Rubiknetic (MuJoCo simulation), magnets on, seed 29001, 2x speed", 13)
    build("close", "g2_u_turn_closeup.gif", "U turn close-up, real time", 12)


if __name__ == "__main__":
    {"render": render, "frames": frames, "encode": encode}[sys.argv[1]]()
