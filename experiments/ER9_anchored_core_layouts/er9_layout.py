"""ER9 layouts for dynamic runs: the same geometry as er9_screen.anchored_layout, with no dependency on the static
screen's modules (which load other runners). er9_layout_check.py compares the two.

A layout option is ('axis',), ('split', gamma_deg, 'centre' | 'corner') for edges, or
('tri', gamma_deg, 'edge' | 'centre') for corners; see PROTOCOL.md.
"""
from __future__ import annotations

import numpy as np

from rubiknetic.cube_logic.geometric import HOME_POSITIONS
from rubiknetic.cube_physics.m1_model import cubie_name
from rubiknetic.cube_physics.magnets import REAL_RADIUS, MagnetParams


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _toward(u: np.ndarray, target: np.ndarray) -> np.ndarray:
    return _unit(target - (target @ u) * u)


def pair_directions(home, opt: tuple) -> list[np.ndarray]:
    h = np.asarray(home, float)
    u = _unit(h)
    if opt[0] == "axis":
        return [u]
    g = np.radians(opt[1])
    nz = np.nonzero(h)[0]
    if opt[0] == "split":
        assert len(nz) == 2
        if opt[2] == "centre":
            targets = [np.eye(3)[k] * h[k] for k in nz]
        else:
            z = [k for k in range(3) if h[k] == 0][0]
            targets = [_unit(h + s * np.eye(3)[z]) for s in (1.0, -1.0)]
    elif opt[0] == "tri":
        assert len(nz) == 3
        if opt[2] == "edge":
            targets = [_unit(h * (1 - np.eye(3)[k])) for k in range(3)]
        else:
            targets = [np.eye(3)[k] * h[k] for k in range(3)]
    else:
        raise ValueError(opt)
    return [_unit(np.cos(g) * u + np.sin(g) * _toward(u, t)) for t in targets]


def anchored_core_layout(mp: MagnetParams, clearance: float, edge_opt: tuple, corner_opt: tuple) -> list[dict]:
    """Magnet list for MagnetSystem: per pair, a piece magnet at v (R + wall + L/2) and a core magnet on the `core`
    body at v (R - clearance - wall - L/2), both moments along +v. ('axis',) for both options is magnets.core_layout."""
    mags = []
    for home in HOME_POSITIONS:
        nz = int(np.count_nonzero(home))
        if nz == 1:
            continue
        kind = "edge" if nz == 2 else "corner"
        R = REAL_RADIUS[kind]
        for v in pair_directions(home, edge_opt if kind == "edge" else corner_opt):
            mags.append({"body": cubie_name(home), "pos": v * (R + mp.wall + mp.length / 2), "dir": v.copy(),
                         "kind": kind})
            mags.append({"body": "core", "pos": v * (R - clearance - mp.wall - mp.length / 2), "dir": v.copy(),
                         "kind": "core_" + kind})
    return mags
