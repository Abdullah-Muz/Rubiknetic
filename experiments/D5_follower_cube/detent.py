"""P-16 experiment (UNSCORED): passive core-centre detent, modelling a magnetic "core positioning"
pair between the fixed core and each centre piece.

Force law (fixed, documented, physical-state only): for each centre hinge angle q,
    tau(q) = -tau_max * sin(4 q)          (period 90 deg; zero torque at every square position)
with potential energy V(q) = (tau_max / 4) * (1 - cos(4 q)). It acts only between the core and that
centre piece. It knows nothing about the commanded move or any target; it is a fixed 4-fold
magnetic pattern, like real cubes with core magnets. It is added to qfrc_passive through
mjcb_passive, inside the physics step, so the edit audit (which checks qfrc_applied/xfrc_applied)
still catches any external force write.
"""
from __future__ import annotations

import mujoco
import numpy as np

from rubiknetic.cube_logic.geometric import HOME_POSITIONS
from rubiknetic.cube_physics.m1_model import cubie_name

_STATE: dict = {}


def install(m: mujoco.MjModel, tau_max: float) -> None:
    """Install the detent for model m (one model per process)."""
    dofs = []
    for h in HOME_POSITIONS:
        if np.count_nonzero(h) == 1:
            j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, cubie_name(h) + "_j")
            dofs.append((m.jnt_qposadr[j], m.jnt_dofadr[j]))
    _STATE.update(tau_max=float(tau_max), dofs=dofs, peak=0.0)

    def cb(model, data):
        tm = _STATE["tau_max"]
        for qa, da in _STATE["dofs"]:
            tau = -tm * np.sin(4.0 * data.qpos[qa])
            data.qfrc_passive[da] += tau
            _STATE["peak"] = max(_STATE["peak"], abs(tau))

    mujoco.set_mjcb_passive(cb if tau_max > 0 else None)


def energy(m: mujoco.MjModel, d: mujoco.MjData) -> float:
    tm = _STATE.get("tau_max", 0.0)
    return float(sum(tm / 4 * (1 - np.cos(4 * d.qpos[qa])) for qa, _ in _STATE.get("dofs", [])))


def peak_torque() -> float:
    return float(_STATE.get("peak", 0.0))
