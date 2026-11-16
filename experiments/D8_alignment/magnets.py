"""Shim: the magnet model now lives in rubiknetic.cube_physics.magnets (moved 2026-11-15, M4 pre-registration section 6).

Kept so the D8 scripts and their recorded commands still run. The force law is identical to D8-1b revision 2.
"""
from rubiknetic.cube_physics import magnets as _m
from rubiknetic.cube_physics.magnets import *  # noqa: F401,F403

# private helpers used by the D8 diagnostic scripts
_exact_parallel_energy = _m._exact_parallel_energy
_exact_parallel_torque = _m._exact_parallel_torque
_dipole_parallel_energy = _m._dipole_parallel_energy
_exact_energy_tilted = _m._exact_energy_tilted
_dipole_energy = _m._dipole_energy
