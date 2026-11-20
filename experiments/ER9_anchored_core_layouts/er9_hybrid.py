"""ER9 hybrid layouts (exploratory, unscored): M5's 48 corner-edge magnet positions plus the anchored piece-to-core
pairs. A MagnetSystem has one magnet type, so every magnet of a hybrid is the same.

cfg["magnet"]:
  "4x3_N35"  (Part E arms)  4 x 3 mm N35 at cfg["scale"], with the tilt-aware table of Parts B-D (M6's N52 table
             times the exact strength factor; validated to 20 deg near-pair tilt, P-60). SCALE_M5 is the scale at
             which a corner-edge pair pulls as hard as M5's 4 x 2 mm N35 pair (er9_hybrid_scale.py).
  "4x2_M5"   (the first single-turn replays only) M5's own magnet and table. That table is validated to 5 deg of
             near-pair tilt, which anchor pairs exceed in every turn, so no Part E arm uses it.
The anchors' strength is set by a real dimension, the clearance between a piece and the core along the pair's axis
(face gap = clearance + 2 walls). cfg["base"] = False leaves M5's 48 positions out (self-check against W3);
cfg["anchors"] = False leaves the anchors out (self-check against L0, 4x2_M5 only).

configure(cfg) applies a hybrid to this (fresh) process the way er9_probe.configure applies an anchored layout:
ER7's C52 arm then runs with it.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if "er9_probe" not in sys.modules:
    spec = importlib.util.spec_from_file_location("er9_probe", HERE / "er9_probe.py")
    _P = importlib.util.module_from_spec(spec); sys.modules["er9_probe"] = _P; spec.loader.exec_module(_P)
P = sys.modules["er9_probe"]
E7, M4, R, LAY, REPO = P.E7, P.M4, P.R, P.LAY, P.REPO

from rubiknetic.cube_physics.m1_model import M1Params  # noqa: E402
from rubiknetic.cube_physics.magnets import MagnetParams, layout, near_field_tables  # noqa: E402

EDGE_OPT, CORNER_OPT = ("split", 20, "centre"), ("tri", 16, "centre")     # the screen's selected geometry (S1)
SCALE_M5 = 0.756                                                           # results/hybrid/scale.json: 0.75615
P60_TILT_DEG = 20.0


def cfg_for(clear_mm: float, magnet: str = "4x3_N35", scale: float = SCALE_M5, base: bool = True,
            anchors: bool = True, edge_opt=EDGE_OPT, corner_opt=CORNER_OPT) -> dict:
    if magnet == "4x2_M5":
        scale = 1.0
    return {"hybrid": True, "magnet": magnet, "scale": float(scale), "base": bool(base), "anchors": bool(anchors),
            "variant": f"{'M5 positions' if base else 'no corner-edge magnets'} + "
                       f"{f'anchors c={clear_mm:g} mm' if anchors else 'no anchors'}, {magnet} x {scale:g}",
            "clear_mm": float(clear_mm), "edge_opt": list(edge_opt), "corner_opt": list(corner_opt)}


def params_for(cfg: dict) -> MagnetParams:
    if cfg["magnet"] == "4x2_M5":
        return R.magnet_params_for({})                                     # M5's nominal magnet
    assert cfg["magnet"] == "4x3_N35", cfg["magnet"]
    return MagnetParams(diameter=0.004, length=0.003, grade="N35", scale=cfg["scale"])


def hybrid_mags(cfg: dict) -> tuple:
    """(magnet params, magnet list): M5's layout() positions first, then the anchor pairs."""
    mp = params_for(cfg)
    p = M1Params(**{**M4.BASE_OVERRIDES, "gap": R.GAP})
    mags = layout(p.pitch, p.gap, mp) if cfg["base"] else []
    if cfg["anchors"]:
        mags = mags + LAY.anchored_core_layout(mp, cfg["clear_mm"] * 1e-3, tuple(cfg["edge_opt"]),
                                               tuple(cfg["corner_opt"]))
    return mp, mags


def configure(cfg: dict) -> None:
    mp, _ = hybrid_mags(cfg)
    if cfg["magnet"] == "4x2_M5":
        info = M4.magnet_availability(mp)                                  # M5's table and its V3 record, or Refused
        folder, file, sha, tilt = M4.TABLES, info["table_file"], info["table_sha256"], M4.nominal_validated_tilt()
    else:
        mp2, table, sha = P.table_for("N35", cfg["scale"])
        assert mp2 == mp
        folder, file, tilt = table.parent, str(table.relative_to(REPO)), P60_TILT_DEG
    E7.MP52 = mp
    E7.C52_TILT_DEG = tilt
    E7.core_layout = lambda _mp, _clear: hybrid_mags(cfg)[1]

    def tables(_mp=None):
        if "spline" not in E7._C52:
            E7._C52.update(spline=near_field_tables(mp, folder), file=file, sha=sha)
        return E7._C52["spline"]

    E7._c52_tables = tables
