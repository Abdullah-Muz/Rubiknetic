"""Model A: exact integer geometry of the 26 visible cubies.

Each cubie is identified by its *home* lattice position p in {-1,0,1}^3 \\ {0}.
State = current integer position and integer 3x3 rotation of every cubie,
both relative to the cube frame. A face turn rotates every cubie whose
current position lies in that layer. Nothing here is hard-coded per move,
which makes this model independent of the table-based model in ``cubie.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .notation import FACE_NORMAL, Move

HOME_POSITIONS: tuple[tuple[int, int, int], ...] = tuple(
    (x, y, z)
    for x in (-1, 0, 1)
    for y in (-1, 0, 1)
    for z in (-1, 0, 1)
    if (x, y, z) != (0, 0, 0)
)
assert len(HOME_POSITIONS) == 26


def axis_rotation(axis: tuple[int, int, int], quarter_turns_ccw: int) -> np.ndarray:
    """Exact integer rotation of ``quarter_turns_ccw`` * 90 deg about a unit axis."""
    a = np.array(axis, dtype=int)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]], dtype=int)
    # Rodrigues at 90 deg: R = I + sin(90)K + (1 - cos(90))K^2 = I + K + K^2
    one = np.eye(3, dtype=int) + k + k @ k
    r = np.eye(3, dtype=int)
    for _ in range(quarter_turns_ccw % 4):
        r = one @ r
    return r


def move_rotation(move: Move) -> np.ndarray:
    """Rotation applied to the turning layer. Clockwise (seen from outside) = -90 deg."""
    return axis_rotation(FACE_NORMAL[move.face], (-move.quarter_turns) % 4)


@dataclass
class GeometricCube:
    """Positions (26,3) int and rotations (26,3,3) int, indexed like HOME_POSITIONS."""

    positions: np.ndarray = field(
        default_factory=lambda: np.array(HOME_POSITIONS, dtype=int)
    )
    rotations: np.ndarray = field(
        default_factory=lambda: np.repeat(np.eye(3, dtype=int)[None], 26, axis=0)
    )

    def copy(self) -> "GeometricCube":
        return GeometricCube(self.positions.copy(), self.rotations.copy())

    def apply(self, move: Move) -> "GeometricCube":
        n = np.array(FACE_NORMAL[move.face], dtype=int)
        r = move_rotation(move)
        out = self.copy()
        in_layer = self.positions @ n == 1
        out.positions[in_layer] = self.positions[in_layer] @ r.T
        out.rotations[in_layer] = r[None] @ self.rotations[in_layer]
        return out

    def apply_all(self, moves: list[Move]) -> "GeometricCube":
        c = self
        for m in moves:
            c = c.apply(m)
        return c

    def is_solved(self, ignore_centers: bool = True) -> bool:
        """Solved = every cubie home with identity rotation.

        Center orientation is invisible on a standard sticker cube, so it is
        ignored by default (``ignore_centers``)."""
        home = np.array(HOME_POSITIONS, dtype=int)
        ok_pos = np.all(self.positions == home)
        nonzero = np.count_nonzero(home, axis=1)
        mask = nonzero >= 2 if ignore_centers else np.ones(26, bool)
        ok_rot = np.all(self.rotations[mask] == np.eye(3, dtype=int))
        return bool(ok_pos and ok_rot)

    def check_legal_assembly(self) -> list[str]:
        """Structural checks that hold for any assembled cube (legal or not)."""
        problems: list[str] = []
        home = np.array(HOME_POSITIONS, dtype=int)
        seen = {tuple(p) for p in self.positions}
        if len(seen) != 26 or seen != set(map(tuple, home)):
            problems.append("positions are not a permutation of the 26 slots")
        for i in range(26):
            r = self.rotations[i]
            if not (np.array_equal(r.T @ r, np.eye(3, dtype=int)) and round(np.linalg.det(r)) == 1):
                problems.append(f"cubie {HOME_POSITIONS[i]} rotation is not proper")
            if np.count_nonzero(self.positions[i]) != np.count_nonzero(home[i]):
                problems.append(f"cubie {HOME_POSITIONS[i]} in a slot of the wrong type")
            # A cubie's stickers must face outward: R maps home position to current.
            if not np.array_equal(r @ home[i], self.positions[i]):
                problems.append(f"cubie {HOME_POSITIONS[i]} stickers not facing outward")
        return problems
