"""Move notation shared by both independent cube models.

Conventions (declared once, tested in ``tests/test_cube_logic.py``):

* Cube frame: +x -> R face, +y -> B face, +z -> U face (right-handed;
  F is therefore -y).
* A face turn ``X`` is a 90-degree **clockwise** turn as seen looking at face
  X from outside the cube, i.e. a rotation of -90 degrees about X's outward
  normal under the right-hand rule. ``X'`` is +90 degrees, ``X2`` is 180.
"""

from __future__ import annotations

from dataclasses import dataclass

FACES = ("U", "R", "F", "D", "L", "B")

#: Outward unit normal of each face in the cube frame (integer vectors).
FACE_NORMAL: dict[str, tuple[int, int, int]] = {
    "U": (0, 0, 1),
    "D": (0, 0, -1),
    "R": (1, 0, 0),
    "L": (-1, 0, 0),
    "F": (0, -1, 0),
    "B": (0, 1, 0),
}

OPPOSITE = {"U": "D", "D": "U", "R": "L", "L": "R", "F": "B", "B": "F"}


@dataclass(frozen=True)
class Move:
    """One outer-layer face turn. ``quarter_turns`` is 1 (CW), 2, or 3 (CCW)."""

    face: str
    quarter_turns: int

    def __post_init__(self) -> None:
        if self.face not in FACES:
            raise ValueError(f"unknown face {self.face!r}")
        if self.quarter_turns not in (1, 2, 3):
            raise ValueError(f"quarter_turns must be 1, 2 or 3, got {self.quarter_turns}")

    def inverse(self) -> "Move":
        return Move(self.face, 4 - self.quarter_turns)

    def __str__(self) -> str:
        return self.face + {1: "", 2: "2", 3: "'"}[self.quarter_turns]


ALL_MOVES: tuple[Move, ...] = tuple(Move(f, q) for f in FACES for q in (1, 2, 3))


def parse(sequence: str) -> list[Move]:
    """Parse e.g. ``"R U R' U2"`` into moves. Raises on any unknown token."""
    moves: list[Move] = []
    for token in sequence.split():
        face, suffix = token[0], token[1:]
        if suffix not in ("", "'", "2", "2'"):
            raise ValueError(f"cannot parse move token {token!r}")
        q = 1 if suffix == "" else 3 if suffix == "'" else 2
        moves.append(Move(face, q))
    return moves


def invert(moves: list[Move]) -> list[Move]:
    """Inverse of a move sequence: reversed order, each move inverted."""
    return [m.inverse() for m in reversed(moves)]


def to_string(moves: list[Move]) -> str:
    return " ".join(str(m) for m in moves)
