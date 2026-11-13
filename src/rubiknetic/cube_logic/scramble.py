"""Seeded generator of *reachable* scrambles built only from legal face turns.

No arbitrary sticker or cubie permutations are ever generated, so every
scramble is in the cube group by construction. Consecutive moves never turn
the same face, and an opposite-face pair (e.g. U D) is never followed by a
third turn of either face, which avoids trivially cancelling sequences.
"""

from __future__ import annotations

import numpy as np

from .notation import FACES, OPPOSITE, Move


def random_scramble(length: int, seed: int) -> list[Move]:
    rng = np.random.default_rng(seed)
    moves: list[Move] = []
    while len(moves) < length:
        face = FACES[int(rng.integers(6))]
        if moves and moves[-1].face == face:
            continue
        if (
            len(moves) >= 2
            and moves[-1].face == OPPOSITE[face]
            and moves[-2].face == face
        ):
            continue
        moves.append(Move(face, int(rng.integers(1, 4))))
    return moves
