"""Bridge Model A (geometry) -> Model B (cubie coordinates).

Used (1) to cross-check the two independent models and (2) to turn a
physically observed cubie configuration into a canonical puzzle state.
Orientation definitions follow Kociemba's facelet->cubie rule: a corner's
twist is the index (in the slot's clockwise facelet list, U/D facelet first)
of the facelet now showing the cubie's U/D sticker; an edge's flip is 0 iff
the cubie's reference sticker sits on the slot's reference facelet.
"""

from __future__ import annotations

import numpy as np

from .cubie import CORNERS, EDGES, CubieCube
from .geometric import HOME_POSITIONS, GeometricCube
from .notation import FACE_NORMAL


def _slot_dirs(name: str) -> list[np.ndarray]:
    return [np.array(FACE_NORMAL[f], dtype=int) for f in name]


def _slot_pos(name: str) -> tuple[int, int, int]:
    return tuple(int(v) for v in sum(_slot_dirs(name)))


CORNER_POS = [_slot_pos(n) for n in CORNERS]
EDGE_POS = [_slot_pos(n) for n in EDGES]
_INDEX = {p: i for i, p in enumerate(HOME_POSITIONS)}


def geometric_to_cubie(g: GeometricCube) -> CubieCube:
    problems = g.check_legal_assembly()
    if problems:
        raise ValueError("not an assembled cube: " + "; ".join(problems))
    at_slot = {tuple(int(v) for v in g.positions[i]): i for i in range(26)}

    cp, co = [], []
    for slot_name, slot_pos in zip(CORNERS, CORNER_POS):
        cubie = at_slot[slot_pos]
        home = HOME_POSITIONS[cubie]
        cp.append(CORNER_POS.index(home))
        ud_home = np.array([0, 0, home[2]], dtype=int)
        ud_now = g.rotations[cubie] @ ud_home
        dirs = _slot_dirs(slot_name)
        co.append(next(k for k, d in enumerate(dirs) if np.array_equal(d, ud_now)))

    ep, eo = [], []
    for slot_name, slot_pos in zip(EDGES, EDGE_POS):
        cubie = at_slot[slot_pos]
        home = HOME_POSITIONS[cubie]
        e = EDGE_POS.index(home)
        ep.append(e)
        ref_now = g.rotations[cubie] @ _slot_dirs(EDGES[e])[0]
        eo.append(0 if np.array_equal(ref_now, _slot_dirs(slot_name)[0]) else 1)

    return CubieCube(tuple(cp), tuple(co), tuple(ep), tuple(eo))
