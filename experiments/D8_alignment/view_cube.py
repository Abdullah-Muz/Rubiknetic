"""Interactive viewer for the D8-1b stage-1 cube (visual inspection only; nothing is recorded or scored).

Usage (WSL, from the repo root):
    python experiments/D8_alignment/view_cube.py [B1|B2E] [nom|none] [--offset DEG] [--xray] [--rig] [--png FILE]

  B1 / B2E      base cube (as in d8_1b_stage1.py); default B1
  nom / none    with or without the 48 nominal magnets; default nom
  --offset DEG  start with the U layer turned DEG degrees off square (as in the T1 snap test); default 0
  --xray        draw pieces semi-transparent so the magnets (red = corner, blue = edge) are visible; in the
                window press 1 to toggle the stickers (geom group 1) and 2 to toggle the magnets (group 2)
  --rig         include the stage-1 gripper pads (idle, open)
  --png FILE    render one still image to FILE offscreen instead of opening the window

In the window: double-click a piece to select it, then Ctrl + right-drag to push it (turns a layer if it can);
Space pauses. The simulation runs slower than real time because the magnet force law is Python.

Viewer-only additions (stickers, magnet markers) are non-colliding, zero-mass geoms on the existing piece bodies, so
the physics is the same as the stage-1 model; the script asserts that body masses and body ids are unchanged.
"""
from __future__ import annotations

import sys
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from d8_1b_stage1 import BASES  # noqa: E402
from magnets import MagnetParams, MagnetSystem, layout  # noqa: E402

from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_logic.notation import FACE_NORMAL  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml, cubie_name  # noqa: E402

CACHE = Path(__file__).parent / "results" / "tables"
COLOURS = {"U": "1 1 1 1", "D": "1 0.85 0 1", "F": "0 0.6 0.2 1", "B": "0 0.3 0.9 1", "R": "0.85 0 0 1",
           "L": "1 0.45 0 1"}


def _f(v) -> str:
    return " ".join(f"{x:.6g}" for x in v)


def viewer_xml(p: M1Params, mp: MagnetParams | None, xray: bool) -> str:
    xml = build_m1_xml(p)
    h = (p.pitch - p.gap) / 2
    extra: dict[str, list[str]] = {}
    for home in HOME_POSITIONS:
        name = cubie_name(home)
        for face, n in FACE_NORMAL.items():
            k = int(np.flatnonzero(n)[0])
            if home[k] != n[k]:
                continue
            pos = np.array(home, float) * p.pitch
            pos[k] += n[k] * (h + 0.0002)
            size = [0.0078, 0.0078, 0.0078]
            size[k] = 0.0002
            extra.setdefault(name, []).append(
                f'<geom type="box" pos="{_f(pos)}" size="{_f(size)}" rgba="{COLOURS[face]}" contype="0" '
                f'conaffinity="0" density="0" group="1"/>')
    if mp is not None:
        for g in layout(p.pitch, p.gap, mp):
            a = g["pos"] - g["dir"] * mp.length / 2
            b = g["pos"] + g["dir"] * mp.length / 2
            rgba = "0.9 0.1 0.1 1" if g["kind"] == "corner" else "0.1 0.3 1 1"
            extra.setdefault(g["body"], []).append(
                f'<geom type="cylinder" fromto="{_f(a)} {_f(b)}" size="{mp.diameter / 2:.6g}" rgba="{rgba}" '
                f'contype="0" conaffinity="0" density="0" group="2"/>')
    for name, geoms in extra.items():
        tag = f'<geom name="{name}_g" class="cubie"'
        assert xml.count(tag) == 1, name
        xml = xml.replace(tag, "\n        ".join(geoms) + "\n        " + tag)
    if xray:
        xml = xml.replace('rgba="0.15 0.15 0.15 1"', 'rgba="0.15 0.15 0.15 0.25"')
    xml = xml.replace("<worldbody>", '<visual><global offwidth="1280" offheight="960"/></visual>\n  <worldbody>\n'
                      '    <light pos="0.3 -0.3 0.5" dir="-0.5 0.5 -0.8" directional="true"/>\n'
                      '    <light pos="-0.3 0.3 0.5" dir="0.5 -0.5 -0.8" directional="true" diffuse="0.4 0.4 0.4"/>')
    return xml


def offset_layer(m: mujoco.MjModel, d: mujoco.MjData, face: str, deg: float) -> None:
    """Initial condition only (the T1 snap-test start): rotate one layer's pieces about its axis before the run."""
    n = np.array(FACE_NORMAL[face], float)
    k = int(np.flatnonzero(n)[0])
    th = np.radians(deg)
    for home in HOME_POSITIONS:
        if home[k] != n[k]:
            continue
        j = m.joint(f"{cubie_name(home)}_j")
        adr = m.jnt_qposadr[j.id]
        if m.jnt_type[j.id] == mujoco.mjtJoint.mjJNT_HINGE:
            d.qpos[adr] = th * float(np.dot(m.jnt_axis[j.id], n))
        else:
            d.qpos[adr:adr + 4] = [np.cos(th / 2), *(np.sin(th / 2) * n)]
    mujoco.mj_forward(m, d)


def write_png(path: str, img: np.ndarray) -> None:
    """Minimal RGB PNG writer (standard library only; the project environment has no imaging package)."""
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    h, w, _ = img.shape
    raw = b"".join(b"\x00" + img[i].astype(np.uint8).tobytes() for i in range(h))
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def main() -> None:
    args = sys.argv[1:]
    base = next((a for a in args if a in BASES), "B1")
    mag = "none" if "none" in args else "nom"
    offset = float(args[args.index("--offset") + 1]) if "--offset" in args else 0.0
    png = args[args.index("--png") + 1] if "--png" in args else None
    p = M1Params(**BASES[base], rig="--rig" in args)
    mp = MagnetParams() if mag == "nom" else None

    plain = mujoco.MjModel.from_xml_string(build_m1_xml(p))
    m = mujoco.MjModel.from_xml_string(viewer_xml(p, mp, "--xray" in args))
    assert plain.nbody == m.nbody and np.allclose(plain.body_mass, m.body_mass), "viewer geoms changed the physics"
    d = mujoco.MjData(m)
    if mp is not None:
        ms = MagnetSystem(m, p.pitch, p.gap, mp, CACHE)
        ms.install()           # installed after compilation (see d8_1b_stage1.py on compile-time callbacks)
    offset_layer(m, d, "U", offset)
    print(f"{base} cube, magnets {mag}, U offset {offset:+.1f} deg, timestep {m.opt.timestep * 1e3:.1f} ms")

    if png:
        with mujoco.Renderer(m, 960, 1280) as r:
            cam = mujoco.MjvCamera()
            cam.lookat[:] = 0
            cam.distance, cam.azimuth, cam.elevation = 0.22, 135, -30
            r.update_scene(d, cam)
            write_png(png, r.render())
        print("wrote", png)
        return

    from mujoco import viewer
    viewer.launch(m, d)


if __name__ == "__main__":
    main()
