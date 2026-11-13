"""Read a discrete puzzle state from *measured* continuous cubie poses.

This is a measurement, never a write-back: it returns the nearest lattice
configuration together with the residual error, and refuses (``valid=False``)
when any cubie is farther than the tolerance from a lattice pose or the
result is not a legal assembly. Callers must treat an invalid reading as
"state UNKNOWN", not snap the simulator to the nearest state.

Inputs are expressed in the cube (core) frame, positions in units of the
cubie pitch, so the module has no MuJoCo dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .convert import geometric_to_cubie
from .cubie import CubieCube
from .geometric import GeometricCube


@dataclass
class Observation:
    valid: bool
    cube: GeometricCube | None
    state: CubieCube | None
    max_position_error: float  # in cubie pitches
    max_angle_error_deg: float
    problems: list[str] = field(default_factory=list)


def _rotation_angle_deg(r: np.ndarray) -> float:
    c = (np.trace(r) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def nearest_lattice_rotation(r: np.ndarray) -> np.ndarray:
    """Nearest signed-permutation matrix with det +1 (one of 24 cube rotations)."""
    out = np.zeros((3, 3), dtype=int)
    used: set[int] = set()
    # Greedy on largest |entries| is exact whenever the angle error is < 45 deg.
    order = np.dstack(np.unravel_index(np.argsort(-np.abs(r), axis=None), r.shape))[0]
    rows: set[int] = set()
    for i, j in order:
        if i in rows or j in used:
            continue
        out[i, j] = 1 if r[i, j] >= 0 else -1
        rows.add(i)
        used.add(j)
    return out


def observe(
    positions: np.ndarray,
    rotations: np.ndarray,
    pos_tol: float = 0.15,
    angle_tol_deg: float = 15.0,
) -> Observation:
    """positions (26,3) in cubie pitches, rotations (26,3,3), cube-frame, HOME order."""
    positions = np.asarray(positions, dtype=float)
    rotations = np.asarray(rotations, dtype=float)
    pos_int = np.rint(positions).astype(int)
    pos_err = np.linalg.norm(positions - pos_int, axis=1)
    rot_int = np.array([nearest_lattice_rotation(r) for r in rotations])
    ang_err = np.array([_rotation_angle_deg(rot_int[i].T @ rotations[i]) for i in range(26)])

    problems: list[str] = []
    if pos_err.max() > pos_tol:
        problems.append(f"position error {pos_err.max():.3f} pitch > tol {pos_tol}")
    if ang_err.max() > angle_tol_deg:
        problems.append(f"angle error {ang_err.max():.2f} deg > tol {angle_tol_deg}")
    for i in range(26):
        if round(np.linalg.det(rot_int[i])) != 1:
            problems.append(f"cubie {i}: nearest lattice rotation improper")

    cube = GeometricCube(pos_int, rot_int)
    state = None
    if not problems:
        problems.extend(cube.check_legal_assembly())
    if not problems:
        state = geometric_to_cubie(cube)
        problems.extend(state.invariant_violations())
    valid = not problems
    return Observation(
        valid=valid,
        cube=cube if valid else None,
        state=state if valid else None,
        max_position_error=float(pos_err.max()),
        max_angle_error_deg=float(ang_err.max()),
        problems=problems,
    )
