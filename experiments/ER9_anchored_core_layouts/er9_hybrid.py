"""ER9 hybrid layouts (exploratory, unscored): M5's 48 corner-edge magnets plus the anchored piece-to-core pairs.

One magnet type throughout, M5's own (4 x 2 mm N35, scale 1, M5's validated table), because a MagnetSystem has one
MagnetParams. The anchors' strength is set by a real dimension, the clearance between a piece and the core along the
pair's axis (face gap = clearance + 2 walls), not by a strength scale.

configure(cfg) applies a hybrid to this (fresh) process the way er9_probe.configure applies an anchored layout:
ER7's C52 arm then runs with it.   cfg = {"hybrid": True, "clear_mm": c, "edge_opt": [...], "corner_opt": [...]}
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
from rubiknetic.cube_physics.magnets import layout, near_field_tables  # noqa: E402

EDGE_OPT, CORNER_OPT = ("split", 20, "centre"), ("tri", 16, "centre")     # the screen's selected geometry (S1)


def cfg_for(clear_mm: float, edge_opt=EDGE_OPT, corner_opt=CORNER_OPT) -> dict:
    return {"hybrid": True, "variant": f"M5 48 + anchors 4x2 N35 c={clear_mm:g} mm", "clear_mm": float(clear_mm),
            "edge_opt": list(edge_opt), "corner_opt": list(corner_opt)}


def hybrid_mags(cfg: dict) -> tuple:
    """(magnet params, magnet list): M5's layout() first, then the anchor pairs."""
    mp = R.magnet_params_for({})                                           # M5's nominal magnet
    p = M1Params(**{**M4.BASE_OVERRIDES, "gap": R.GAP})
    base = layout(p.pitch, p.gap, mp)
    if not cfg.get("anchors", True):                                       # self-check: M5's 48 magnets only
        return mp, base
    anchors = LAY.anchored_core_layout(mp, cfg["clear_mm"] * 1e-3, tuple(cfg["edge_opt"]), tuple(cfg["corner_opt"]))
    return mp, base + anchors


def configure(cfg: dict) -> None:
    mp, mags = hybrid_mags(cfg)
    info = M4.magnet_availability(mp)                                      # M5's table and its V3 record, or Refused
    E7.MP52 = mp
    E7.C52_TILT_DEG = M4.nominal_validated_tilt()                          # M5's V3 limit for this table, not P-60's
    E7.core_layout = lambda _mp, _clear: hybrid_mags(cfg)[1]

    def tables(_mp=None):
        if "spline" not in E7._C52:
            E7._C52.update(spline=near_field_tables(mp, M4.TABLES), file=info["table_file"],
                           sha=info["table_sha256"])
        return E7._C52["spline"]

    E7._c52_tables = tables
