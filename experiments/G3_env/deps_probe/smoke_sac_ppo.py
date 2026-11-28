"""G3 dependency smoke test: SB3 SAC + PPO on Pendulum-v1 with SubprocVecEnv(2), next to MuJoCo 4.0.1.

Run (WSL, throwaway venv only; never the project venv):
    /tmp/g3deps/bin/python experiments/G3_env/deps_probe/smoke_sac_ppo.py

Writes smoke_results.json (or the file name given as argv[1]) next to this file. Also checks:
- MuJoCo imports and steps inside each SubprocVecEnv worker, and each worker owns its passive callback;
- same-seed reruns give bit-identical parameters (CPU, 1 torch thread), for SAC and PPO.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import platform
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import torch as th  # noqa: E402

th.set_num_threads(1)  # small MLPs; avoid oversubscription with env worker processes

import gymnasium  # noqa: E402
import mujoco  # noqa: E402
import numpy as np  # noqa: E402
import scipy  # noqa: E402
import stable_baselines3 as sb3  # noqa: E402
from stable_baselines3 import PPO, SAC  # noqa: E402
from stable_baselines3.common.vec_env import SubprocVecEnv  # noqa: E402

from toy_envs import make_pendulum, make_priv_pendulum  # noqa: E402


def params_digest(model) -> tuple[float, list[np.ndarray]]:
    arrs = [p.detach().cpu().numpy().copy() for p in model.policy.parameters()]
    return float(sum(a.sum() for a in arrs)), arrs


def same(a: list[np.ndarray], b: list[np.ndarray]) -> bool:
    return len(a) == len(b) and all(np.array_equal(x, y) for x, y in zip(a, b))


def run_sac(seed: int, steps: int) -> tuple[float, list[np.ndarray], float, float]:
    env = SubprocVecEnv([make_pendulum() for _ in range(2)])
    t0 = time.perf_counter()
    model = SAC("MlpPolicy", env, seed=seed, learning_starts=200, buffer_size=10_000, batch_size=64, device="cpu", verbose=0)
    model.learn(total_timesteps=steps)
    dt = time.perf_counter() - t0
    ep = [e["r"] for e in model.ep_info_buffer]
    env.close()
    s, arrs = params_digest(model)
    return s, arrs, dt, float(np.mean(ep)) if ep else float("nan")


def run_ppo(seed: int, steps: int) -> tuple[float, list[np.ndarray], float, float]:
    env = SubprocVecEnv([make_pendulum() for _ in range(2)])
    t0 = time.perf_counter()
    model = PPO("MlpPolicy", env, seed=seed, n_steps=256, batch_size=64, n_epochs=4, device="cpu", verbose=0)
    model.learn(total_timesteps=steps)
    dt = time.perf_counter() - t0
    ep = [e["r"] for e in model.ep_info_buffer]
    env.close()
    s, arrs = params_digest(model)
    return s, arrs, dt, float(np.mean(ep)) if ep else float("nan")


def main() -> None:
    out: dict = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "versions": {
            "stable_baselines3": sb3.__version__,
            "gymnasium": gymnasium.__version__,
            "torch": th.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "mujoco": mujoco.__version__,
        },
        "torch_cuda_available": th.cuda.is_available(),
        "torch_num_threads": th.get_num_threads(),
        "torch_num_interop_threads": th.get_num_interop_threads(),
        "os_cpu_count": os.cpu_count(),
        "mp_default_start_method_sb3": "forkserver" if "forkserver" in mp.get_all_start_methods() else "spawn",
        "main_process_passive_callback": repr(mujoco.get_mjcb_passive()),
    }

    # 1. MuJoCo inside SubprocVecEnv workers; per-process passive callback.
    env = SubprocVecEnv([make_priv_pendulum(touch_mujoco=True, passive_torque=t) for t in (+0.01, -0.01)])
    reports = env.env_method("get_mj_report")
    env.close()
    out["worker_mujoco_reports"] = reports
    out["worker_pids_distinct"] = len({r["pid"] for r in reports}) == 2 and all(r["pid"] != os.getpid() for r in reports)
    out["worker_callback_isolated"] = (
        reports[0]["callback_before_install"] is None
        and reports[1]["callback_before_install"] is None
        and reports[0]["qvel_after_100_steps"] > 0 > reports[1]["qvel_after_100_steps"]
    )
    out["main_process_passive_callback_after"] = repr(mujoco.get_mjcb_passive())

    # 2. SAC + PPO smoke, each twice with the same seed (determinism), once with another seed.
    sac_steps, ppo_steps = 1_000, 1_024
    s1, a1, t1, r1 = run_sac(0, sac_steps)
    s2, a2, t2, _ = run_sac(0, sac_steps)
    s3, a3, _, _ = run_sac(1, sac_steps)
    out["sac"] = {
        "total_timesteps": sac_steps,
        "n_envs": 2,
        "wall_s": [round(t1, 2), round(t2, 2)],
        "mean_ep_return": r1,
        "param_sum_seed0_run1": s1,
        "param_sum_seed0_run2": s2,
        "bit_identical_same_seed": same(a1, a2),
        "differs_other_seed": not same(a1, a3),
    }
    p1, b1, u1, q1 = run_ppo(0, ppo_steps)
    p2, b2, u2, _ = run_ppo(0, ppo_steps)
    p3, b3, _, _ = run_ppo(1, ppo_steps)
    out["ppo"] = {
        "total_timesteps": ppo_steps,
        "n_envs": 2,
        "wall_s": [round(u1, 2), round(u2, 2)],
        "mean_ep_return": q1,
        "param_sum_seed0_run1": p1,
        "param_sum_seed0_run2": p2,
        "bit_identical_same_seed": same(b1, b2),
        "differs_other_seed": not same(b1, b3),
    }
    name = sys.argv[1] if len(sys.argv) > 1 else "smoke_results.json"
    (HERE / name).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
