"""Infer which face turn (if any) *physically happened* between two observed
cube configurations. Used so that the oracle is driven by observed moves,
never by commands (pre-registration rule 4).
"""

from __future__ import annotations

import numpy as np

from .geometric import HOME_POSITIONS, GeometricCube, move_rotation
from .notation import FACE_NORMAL, FACES, Move

_NONCENTRE = np.array([np.count_nonzero(h) >= 2 for h in HOME_POSITIONS])


class InconsistentTransition(ValueError):
    """The observed change is not a single legal outer-face turn."""


def infer_move(before: GeometricCube, after: GeometricCube) -> Move | None:
    """Return the single face turn mapping ``before`` to ``after``; ``None`` if no
    corner/edge cubie changed. Raises :class:`InconsistentTransition` otherwise.
    Centre cubie spin is ignored (invisible on a standard cube)."""
    rel = np.einsum("nij,nkj->nik", after.rotations, before.rotations)  # R_after @ R_before^T
    moved = np.array([not np.array_equal(rel[i], np.eye(3, dtype=int)) for i in range(26)]) & _NONCENTRE
    moved_pos = moved | (np.any(after.positions != before.positions, axis=1) & _NONCENTRE)
    if not moved_pos.any():
        return None
    for face in FACES:
        n = np.array(FACE_NORMAL[face], dtype=int)
        layer = (before.positions @ n == 1) & _NONCENTRE
        if not np.array_equal(layer, moved_pos):
            continue
        for q in (1, 2, 3):
            mv = Move(face, q)
            r = move_rotation(mv)
            if all(np.array_equal(rel[i], r) for i in np.nonzero(layer)[0]) and np.array_equal(
                after.positions[layer], before.positions[layer] @ r.T
            ):
                return mv
        raise InconsistentTransition(f"layer {face} changed but not by a rigid quarter/half turn")
    raise InconsistentTransition(
        f"{int(moved_pos.sum())} corner/edge cubies changed, not matching any single outer layer"
    )
