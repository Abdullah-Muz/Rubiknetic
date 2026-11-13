"""Read-only measurements from a running MuJoCo cube (audit channel).

Nothing in this module writes to ``mjData``.
"""

from __future__ import annotations

import mujoco
import numpy as np

from rubiknetic.cube_logic import HOME_POSITIONS, Observation, observe
from rubiknetic.cube_logic.notation import FACE_NORMAL

from .m1_model import cubie_name


class CubeReadout:
    def __init__(self, model: mujoco.MjModel, pitch: float):
        self.m = model
        self.pitch = pitch
        self.core = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "core")
        self.body_ids = np.array(
            [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, cubie_name(h)) for h in HOME_POSITIONS]
        )
        self.geom_ids = np.array(
            [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, cubie_name(h) + "_g") for h in HOME_POSITIONS]
        )
        self.cubie_geom_set = set(int(g) for g in self.geom_ids)

    def poses(self, d: mujoco.MjData) -> tuple[np.ndarray, np.ndarray]:
        """Cubie positions (pitch units) and rotations, both in the core frame."""
        rc = d.xmat[self.core].reshape(3, 3)
        pc = d.xpos[self.core]
        pos = (d.geom_xpos[self.geom_ids] - pc) @ rc / self.pitch
        rots = np.einsum("ji,njk->nik", rc, d.xmat[self.body_ids].reshape(-1, 3, 3))
        return pos, rots

    def observe(self, d: mujoco.MjData, **kw) -> Observation:
        return observe(*self.poses(d), **kw)

    def layer_members(self, d: mujoco.MjData, face: str) -> list[int]:
        """Indices of non-centre cubies whose centre currently lies in the face layer."""
        pos, _ = self.poses(d)
        n = np.array(FACE_NORMAL[face], float)
        return [i for i in range(26) if np.count_nonzero(HOME_POSITIONS[i]) >= 2 and pos[i] @ n > 0.5]

    @staticmethod
    def rotation_about_deg(rots_start: np.ndarray, rots_now: np.ndarray, members: list[int], face: str) -> np.ndarray:
        """Per-cubie signed rotation (deg, right-hand about the face's outward normal)
        of ``members`` between two snapshots."""
        n = np.array(FACE_NORMAL[face], float)
        t = np.cross(n, [1.0, 0, 0]) if abs(n[0]) < 0.9 else np.cross(n, [0, 1.0, 0])
        t /= np.linalg.norm(t)
        out = []
        for i in members:
            v = rots_now[i] @ rots_start[i].T @ t
            v = v - (v @ n) * n
            out.append(np.degrees(np.arctan2(np.cross(t, v) @ n, t @ v)))
        return np.array(out)

    def max_penetration_mm(self, d: mujoco.MjData) -> float:
        dist = [d.contact[i].dist for i in range(d.ncon)]
        return float(max(0.0, -min(dist)) * 1000) if dist else 0.0
