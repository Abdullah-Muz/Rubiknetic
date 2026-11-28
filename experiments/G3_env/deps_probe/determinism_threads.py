"""Does the torch intra-op thread count change SB3 SAC results on CPU? (G3 dependency probe)

    /tmp/g3sync/bin/python experiments/G3_env/deps_probe/determinism_threads.py

Same seed, DummyVecEnv(1) Pendulum-v1, 600 steps, net 256x256, batch 256; run with 1 thread and with 2 threads.
Prints whether the final parameters are bit-identical. One process; at most 2 threads.
"""

from __future__ import annotations

import json
import sys

import numpy as np
import torch as th
from stable_baselines3 import SAC
from stable_baselines3.common.env_util import make_vec_env


def run(threads: int) -> list[np.ndarray]:
    th.set_num_threads(threads)
    env = make_vec_env("Pendulum-v1", n_envs=1, seed=0)
    model = SAC("MlpPolicy", env, seed=0, learning_starts=100, batch_size=256, device="cpu")
    model.learn(600)
    return [p.detach().numpy().copy() for p in model.policy.parameters()]


if __name__ == "__main__":
    a = run(1)
    b = run(2)
    c = run(1)
    res = {
        "torch": th.__version__,
        "same_threads_bit_identical": all(np.array_equal(x, y) for x, y in zip(a, c)),
        "threads_1_vs_2_bit_identical": all(np.array_equal(x, y) for x, y in zip(a, b)),
        "max_abs_param_diff_1_vs_2": float(max(np.abs(x - y).max() for x, y in zip(a, b))),
    }
    print(json.dumps(res, indent=2))
    if len(sys.argv) > 1:
        from pathlib import Path

        (Path(__file__).resolve().parent / sys.argv[1]).write_text(json.dumps(res, indent=2) + "\n")
