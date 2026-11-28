"""Toy environments for the G3 dependency probe (not project code).

PrivPendulum: Gymnasium's Pendulum-v1 with a Dict observation. The actor key "obs" holds (cos th, sin th);
the privileged key "priv" holds the angular velocity, which only the critic may read. Actions are a
normalised "residual" in [-1, 1], scaled x2 to Pendulum's torque.

Optionally each instance builds a tiny MuJoCo model and installs a process-global passive-force callback,
to check that MuJoCo 4.0.1 runs inside SubprocVecEnv workers and that each worker owns its callback.
"""

from __future__ import annotations

import os

import gymnasium as gym
import numpy as np
from gymnasium import spaces

_TINY_XML = """
<mujoco>
  <worldbody>
    <body name="b"><joint name="hinge" type="hinge" axis="0 0 1"/><geom type="box" size=".01 .02 .03" mass="0.1"/></body>
  </worldbody>
</mujoco>
"""


class PrivPendulum(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, touch_mujoco: bool = False, passive_torque: float = 0.0):
        self._env = gym.make("Pendulum-v1")  # TimeLimit 200 steps -> truncation
        self.observation_space = spaces.Dict(
            {
                "obs": spaces.Box(-1.0, 1.0, (2,), np.float32),
                "priv": spaces.Box(-8.0, 8.0, (1,), np.float32),
            }
        )
        self.action_space = spaces.Box(-1.0, 1.0, (1,), np.float32)
        self.mj_report: dict | None = None
        if touch_mujoco:
            self.mj_report = self._touch_mujoco(passive_torque)

    @staticmethod
    def _touch_mujoco(passive_torque: float) -> dict:
        import mujoco

        model = mujoco.MjModel.from_xml_string(_TINY_XML)
        data = mujoco.MjData(model)
        before = mujoco.get_mjcb_passive()

        def cb(m, d):  # constant torque on the hinge, applied through qfrc_passive
            d.qfrc_passive[0] += passive_torque

        mujoco.set_mjcb_passive(cb)
        for _ in range(100):
            mujoco.mj_step(model, data)
        report = {
            "pid": os.getpid(),
            "mujoco": mujoco.__version__,
            "callback_before_install": None if before is None else repr(before),
            "qvel_after_100_steps": float(data.qvel[0]),
            "passive_torque": passive_torque,
        }
        return report

    @staticmethod
    def _split(o: np.ndarray) -> dict[str, np.ndarray]:
        return {"obs": o[:2].astype(np.float32), "priv": o[2:3].astype(np.float32)}

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        o, info = self._env.reset(seed=seed, options=options)
        return self._split(o), info

    def step(self, action):
        o, r, terminated, truncated, info = self._env.step(2.0 * np.asarray(action, dtype=np.float32))
        return self._split(o), float(r), terminated, truncated, info

    def get_mj_report(self) -> dict | None:
        return self.mj_report


def make_priv_pendulum(touch_mujoco: bool = False, passive_torque: float = 0.0):
    def _init():
        from stable_baselines3.common.monitor import Monitor

        return Monitor(PrivPendulum(touch_mujoco=touch_mujoco, passive_torque=passive_torque))

    return _init


def make_pendulum():
    def _init():
        from stable_baselines3.common.monitor import Monitor

        return Monitor(gym.make("Pendulum-v1"))

    return _init
