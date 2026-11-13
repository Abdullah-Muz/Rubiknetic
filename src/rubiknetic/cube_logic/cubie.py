"""Model B: permutation/orientation ("cubie level") representation.

Uses the corner/edge ordering and move tables of H. Kociemba's two-phase
algorithm description (http://kociemba.org/cube.htm, "cubie level").
These tables are typed in by hand and are deliberately *not* derived from
``geometric.py``; the test suite cross-checks the two models against each
other on random sequences, so a typo in either is detected.
"""

from __future__ import annotations

from dataclasses import dataclass

from .notation import Move

CORNERS = ("URF", "UFL", "ULB", "UBR", "DFR", "DLF", "DBL", "DRB")
EDGES = ("UR", "UF", "UL", "UB", "DR", "DF", "DL", "DB", "FR", "FL", "BL", "BR")
URF, UFL, ULB, UBR, DFR, DLF, DBL, DRB = range(8)
UR, UF, UL, UB, DR, DF, DL, DB, FR, FL, BL, BR = range(12)


@dataclass(frozen=True)
class CubieCube:
    """cp[i] = corner occupying slot i; co[i] its twist (mod 3); same for edges (mod 2)."""

    cp: tuple[int, ...] = tuple(range(8))
    co: tuple[int, ...] = (0,) * 8
    ep: tuple[int, ...] = tuple(range(12))
    eo: tuple[int, ...] = (0,) * 12

    def multiply(self, b: "CubieCube") -> "CubieCube":
        """Composition self * b (apply self, then b) in "is replaced by" form."""
        cp = tuple(self.cp[b.cp[i]] for i in range(8))
        co = tuple((self.co[b.cp[i]] + b.co[i]) % 3 for i in range(8))
        ep = tuple(self.ep[b.ep[i]] for i in range(12))
        eo = tuple((self.eo[b.ep[i]] + b.eo[i]) % 2 for i in range(12))
        return CubieCube(cp, co, ep, eo)

    def apply(self, move: Move) -> "CubieCube":
        c = self
        for _ in range(move.quarter_turns):
            c = c.multiply(BASIC[move.face])
        return c

    def apply_all(self, moves: list[Move]) -> "CubieCube":
        c = self
        for m in moves:
            c = c.apply(m)
        return c

    def is_solved(self) -> bool:
        return self == SOLVED

    # ---- invariants of the legal (reachable) group -------------------------
    def corner_parity(self) -> int:
        return _parity(self.cp)

    def edge_parity(self) -> int:
        return _parity(self.ep)

    def invariant_violations(self) -> list[str]:
        """Empty list iff the state is in the reachable cube group."""
        v: list[str] = []
        if sorted(self.cp) != list(range(8)):
            v.append("cp is not a permutation")
        if sorted(self.ep) != list(range(12)):
            v.append("ep is not a permutation")
        if sum(self.co) % 3:
            v.append("corner twist sum not 0 mod 3")
        if sum(self.eo) % 2:
            v.append("edge flip sum not 0 mod 2")
        if not v and self.corner_parity() != self.edge_parity():
            v.append("corner and edge permutation parities differ")
        return v


def _parity(p: tuple[int, ...]) -> int:
    seen = [False] * len(p)
    swaps = 0
    for i in range(len(p)):
        j, length = i, 0
        while not seen[j]:
            seen[j] = True
            j = p[j]
            length += 1
        if length:
            swaps += length - 1
    return swaps % 2


SOLVED = CubieCube()

BASIC: dict[str, CubieCube] = {
    "U": CubieCube(
        (UBR, URF, UFL, ULB, DFR, DLF, DBL, DRB),
        (0, 0, 0, 0, 0, 0, 0, 0),
        (UB, UR, UF, UL, DR, DF, DL, DB, FR, FL, BL, BR),
        (0,) * 12,
    ),
    "R": CubieCube(
        (DFR, UFL, ULB, URF, DRB, DLF, DBL, UBR),
        (2, 0, 0, 1, 1, 0, 0, 2),
        (FR, UF, UL, UB, BR, DF, DL, DB, DR, FL, BL, UR),
        (0,) * 12,
    ),
    "F": CubieCube(
        (UFL, DLF, ULB, UBR, URF, DFR, DBL, DRB),
        (1, 2, 0, 0, 2, 1, 0, 0),
        (UR, FL, UL, UB, DR, FR, DL, DB, UF, DF, BL, BR),
        (0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0),
    ),
    "D": CubieCube(
        (URF, UFL, ULB, UBR, DLF, DBL, DRB, DFR),
        (0,) * 8,
        (UR, UF, UL, UB, DF, DL, DB, DR, FR, FL, BL, BR),
        (0,) * 12,
    ),
    "L": CubieCube(
        (URF, ULB, DBL, UBR, DFR, UFL, DLF, DRB),
        (0, 1, 2, 0, 0, 2, 1, 0),
        (UR, UF, BL, UB, DR, DF, FL, DB, FR, UL, DL, BR),
        (0,) * 12,
    ),
    "B": CubieCube(
        (URF, UFL, UBR, DRB, DFR, DLF, ULB, DBL),
        (0, 0, 1, 2, 0, 0, 2, 1),
        (UR, UF, UL, BR, DR, DF, DL, BL, FR, FL, UB, DB),
        (0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1),
    ),
}
