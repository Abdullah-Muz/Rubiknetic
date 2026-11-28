# G3 dependencies: Stable-Baselines3, Gymnasium and CPU PyTorch (research and compatibility probe)

- **Date:** 2026-11-28 (all URLs accessed on this date).
- **Scope:** Phase 3 (G3) dependency selection for P-146 D3/D4: SB3 SAC (B2), SB3 PPO (B3), Gymnasium, CPU-only
  PyTorch; asymmetric actor-critic; critic LayerNorm; zero-initialised residual; replay pre-fill.
- **Status:** `PROPOSAL` with `FACT`s from primary sources and a small probe. **Nothing was added to the project.**
  `pyproject.toml`, `uv.lock` and the project venv `~/.venvs/rubiknetic` are unchanged. Adding the pins needs the
  user's approval and a DECISION_LOG entry (CLAUDE.md: "pinned when introduced").
- **Probe files:** [`../../experiments/G3_env/deps_probe/`](../../experiments/G3_env/deps_probe/) (toy environments only;
  no Rubik's cube scene was used).
- **Environment of the probe:** WSL2 Ubuntu 24.04, Python 3.12.3, 16 logical CPUs (shared with a running simulation
  job; load average about 11 during the probe, so wall times are indicative only). Throwaway venvs `/tmp/g3deps`
  (`uv pip install`) and `/tmp/g3sync` (`uv sync --locked` from a trial lock in `/tmp/g3lock`).

## 1. Proposed pins (`FACT` = verified on PyPI / the index; `PROPOSAL` = the choice)

| Package | Pin | Why / evidence | Licence (verified) |
| --- | --- | --- | --- |
| stable-baselines3 | **2.9.2** | Latest on PyPI (uploaded 2026-10-26). Requires `gymnasium>=0.29.1,<2.0`, `numpy>=1.20,<3.0`, `torch>=2.8,<3.0`, `cloudpickle`. pandas/matplotlib are only in the `extra` extra | MIT (repo `LICENSE`, "Copyright (c) 2019 Antonin Raffin"; wheel ships `LICENSE` + `NOTICE` crediting OpenAI Baselines / Stable-Baselines, both MIT) |
| gymnasium | **1.4.0** | Latest on PyPI (2026-10-05). Requires `numpy>=1.22.0`, `cloudpickle>=1.2.0`, `typing-extensions>=4.12.0`, `farama-notifications>=0.0.1` | MIT (repo `LICENSE`: "Copyright (c) 2016 OpenAI, (c) 2022 Farama Foundation") |
| torch | **2.15.0** (`2.15.0+cpu` from `https://download.pytorch.org/whl/cpu`) | Latest on PyPI (2026-10-28); `requires_python >=3.11`. The PyPI Linux wheel pulls CUDA 13 packages (`cuda-toolkit==13.2.2`, `nvidia-cudnn-cu13`, `triton`...), so the CPU index is needed for a CPU-only install | PyTorch's own code: BSD-3-Clause-style (repo `LICENSE`, "From PyTorch: Copyright (c) 2016- Facebook, Inc ..."; 3-clause "Redistribution and use..." text). The wheel's metadata `License-Expression` is the compound `Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND ISC AND MIT AND Zlib`, covering bundled third-party code. All permissive |

Transitive packages added (from the trial `uv lock`, PyPI unless noted): cloudpickle 3.1.3 (BSD-3-Clause),
farama-notifications 0.0.6 (MIT), filelock 4.3.2 (MIT), fsspec 2026.9.0 (BSD-3-Clause), jinja2 3.1.6 (BSD),
markupsafe 3.0.4 (BSD-3-Clause), mpmath 1.3.0 (BSD), networkx 3.7 (BSD-3-Clause), setuptools 84.2.1 (MIT),
sympy 1.14.0 (BSD), typing-extensions 4.16.0 (PSF-2.0). Licences read from each installed wheel's metadata.

**Conflicts with the locked stack: none found.**
- numpy 2.5.4, scipy 1.18.1, mujoco 4.0.1 and pytest 9.2.0 are inside every range above (`uv pip check`:
  "All installed packages are compatible").
- The trial `uv lock` (below) only **added** packages; every package already in `uv.lock` kept its version
  (including `packaging 26.3`). No downgrade/upgrade of numpy, scipy or mujoco.
- Nothing pulls in pandas, matplotlib, CUDA or tensorboard.

Pip freezes: [`pip_freeze_uv_lock.txt`](../../experiments/G3_env/deps_probe/pip_freeze_uv_lock.txt) (the lock-resolved
set; this is the one to adopt) and [`pip_freeze_pip_venv.txt`](../../experiments/G3_env/deps_probe/pip_freeze_pip_venv.txt)
(first ad-hoc install; its torch dependencies came from the PyTorch index, hence filelock 4.2.4, markupsafe 3.0.3,
setuptools 78.1.0 and packaging 26.4). Both sets gave bit-identical smoke results (§2).

### How to add them to the project (`PROPOSAL`; not done)

A separate dependency group keeps G1/G2 installs unchanged (CLAUDE.md: do not install all future-phase dependencies
at once). Tested in a copy of `pyproject.toml` + `uv.lock` under `/tmp/g3lock`
([`pyproject_trial.toml`](../../experiments/G3_env/deps_probe/pyproject_trial.toml),
[`uv_lock_trial.lock`](../../experiments/G3_env/deps_probe/uv_lock_trial.lock)):

```toml
[dependency-groups]
dev = ["pytest==9.2.0"]
rl = [
    "stable-baselines3==2.9.2",
    "gymnasium==1.4.0",
    "torch==2.15.0",
]

[tool.uv.sources]
torch = [{ index = "pytorch-cpu" }]

[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true
```

then `uv lock` and, in WSL, `UV_PROJECT_ENVIRONMENT=~/.venvs/rubiknetic uv sync --locked --group rl --group dev`
(or the project's equivalent). Notes:
- `explicit = true` restricts the PyTorch index to `torch`; everything else still resolves from PyPI (uv docs).
- `torch==2.15.0` matches `2.15.0+cpu` (PEP 440 local version). The universal lock resolved **`2.15.0+cpu`** for
  `sys_platform != 'darwin'` (wheels locked for linux x86_64/aarch64/s390x and win_amd64/win_arm64) and plain
  `2.15.0` for macOS, so Windows `uv` would also get the CPU build.
- `uv lock` was not run in the repository.

## 2. Smoke test (`VALIDATED_RESULT` for the probe only)

Script: [`smoke_sac_ppo.py`](../../experiments/G3_env/deps_probe/smoke_sac_ppo.py). Results:
[`smoke_results_uv_lock.json`](../../experiments/G3_env/deps_probe/smoke_results_uv_lock.json) (lock set) and
[`smoke_results_pip_venv.json`](../../experiments/G3_env/deps_probe/smoke_results_pip_venv.json).

| Check | Result (both venvs) |
| --- | --- |
| Versions in process | SB3 2.9.2, Gymnasium 1.4.0, torch 2.15.0+cpu, NumPy 2.5.4, SciPy 1.18.1, MuJoCo 4.0.1; `torch.cuda.is_available() == False` |
| MuJoCo in `SubprocVecEnv(2)` workers (start method `forkserver`, SB3's default on Linux) | Each worker builds a tiny model, installs its own `mujoco.set_mjcb_passive` callback (+0.01 / -0.01 N·m) and steps 100 times: qvel +120.0 / -120.0. Each worker saw **no inherited callback**; the main process's callback stayed `None`. Distinct PIDs. So one-environment-per-process isolates the process-global passive callback, as G3 needs |
| SAC `MlpPolicy`, Pendulum-v1, `SubprocVecEnv(2)`, 1000 steps, `learning_starts=200` | Runs; same seed twice: **bit-identical parameters**; other seed: different. Wall 24-29 s first run (includes worker start-up), 11-14 s second |
| PPO `MlpPolicy`, Pendulum-v1, `SubprocVecEnv(2)`, 1024 steps | Runs; same seed twice: **bit-identical**; other seed: different. Wall 2-3 s |
| Across the two venvs | Same parameter sums (SAC 1444.83154296875, PPO 3.0196661949157715): the transitive-version differences do not change results |

These are smoke runs only (returns are untrained, about -1200 to -1300); they say nothing about learning
performance.

## 3. Asymmetric actor-critic in SB3 2.9.2

### 3.1 What SB3 offers (`FACT`, from the installed source and the docs)
- Dict observations are supported (`MultiInputPolicy` / `CombinedExtractor`); off-policy algorithms switch to
  `DictReplayBuffer` automatically, PPO to `DictRolloutBuffer`.
- `SACPolicy` defaults to `share_features_extractor=False` and builds the actor and each critic through
  `make_actor()` / `make_critic()`, but **both use the same `features_extractor_class` and kwargs**. SB3 has no
  built-in "privileged critic" option. `ContinuousCritic` has **no LayerNorm option** (it calls `create_mlp` without
  `post_linear_modules`), although `create_mlp` itself accepts `post_linear_modules=[nn.LayerNorm]` (applied after each
  hidden Linear, before the activation, not after the output layer).
- `ActorCriticPolicy` (PPO) with `share_features_extractor=False` builds `pi_features_extractor` and
  `vf_features_extractor` from the same class, and one `MlpExtractor(features_dim, ...)` with a single input width.
  Its `forward`, `evaluate_actions`, `get_distribution` and `predict_values` call
  `mlp_extractor.forward_actor(pi_features)` / `forward_critic(vf_features)` separately; the docs' "Advanced Example"
  overrides `_build_mlp_extractor`.

### 3.2 Approach (`PROPOSAL`; works in the probe)
Code: [`asym_ac.py`](../../experiments/G3_env/deps_probe/asym_ac.py) (about 290 lines including docstrings).

- Observation = `spaces.Dict({"obs": Box, "priv": Box})`. In G3, `obs` would hold the real-robot signals of D3 and
  `priv` the simulator layer angle (and anything else privileged).
- `KeySubsetExtractor(observation_space, keys)`: flattens and concatenates only `keys`. The actor gets
  `("obs",)`, the critic(s) `("obs", "priv")`. The actor's graph never contains the privileged tensor.
- **SAC:** `AsymmetricSACPolicy(SACPolicy)` overrides `make_actor` and `make_critic` to pass different extractors
  (critic and critic target both get the privileged one). `LayerNormContinuousCritic(ContinuousCritic)` rebuilds
  the Q-MLPs with `create_mlp(..., post_linear_modules=[nn.LayerNorm])`. `actor.mu` (the mean Linear) is
  zero-initialised, so the deterministic action is exactly 0 (tanh(0) = 0; unscaling a symmetric box gives 0.0
  exactly). Option `actor_log_std_bias` sets the initial log-std to a constant.
- **PPO:** `AsymmetricActorCriticPolicy(ActorCriticPolicy)` swaps `vf_features_extractor` in `_build` (before the
  MLPs, orthogonal init and optimizer are created) and overrides `_build_mlp_extractor` with an
  `AsymmetricMlpExtractor` whose policy and value branches have different input widths (optional LayerNorm on the
  value branch). `action_net` is zero-initialised.
- Extra policy kwargs are returned by `_get_constructor_parameters`, and `model.save` / `SAC.load` / `PPO.load`
  round-trip (tested).

Minimal usage:

```python
from stable_baselines3 import SAC, PPO
from asym_ac import AsymmetricSACPolicy, AsymmetricActorCriticPolicy, prefill_replay_buffer

sac = SAC(AsymmetricSACPolicy, venv, learning_starts=0, seed=seed, device="cpu",
          policy_kwargs=dict(net_arch=[256, 256], actor_keys=("obs",), critic_keys=("obs", "priv"),
                             critic_layer_norm=True, zero_init_actor_mean=True))
prefill_replay_buffer(sac, 20_000)          # B0 transitions, residual = 0
sac.learn(total_timesteps=...)

ppo = PPO(AsymmetricActorCriticPolicy, venv, seed=seed, device="cpu",
          policy_kwargs=dict(net_arch=dict(pi=[256, 256], vf=[256, 256]), vf_layer_norm=True))
```

### 3.3 Tests (`VALIDATED_RESULT` for the toy env)
[`test_asym_ac.py`](../../experiments/G3_env/deps_probe/test_asym_ac.py), toy env `PrivPendulum`
([`toy_envs.py`](../../experiments/G3_env/deps_probe/toy_envs.py)): Pendulum-v1 whose actor key holds (cos θ, sin θ)
and whose privileged key holds θ̇. **5 / 5 pass** in both venvs (96 s in `/tmp/g3deps`, 56 s in `/tmp/g3sync`, on the loaded machine).

- **Actor independence (SAC and PPO), before and after training:** replacing `priv` by 0, 1e6 or NaN leaves the
  deterministic action bit-identical; the stochastic SAC sample is identical under the same torch RNG state; PPO's
  distribution mean and std are identical; `torch.autograd.grad(action, priv)` returns `None` (priv is not in the
  graph); `model.predict()` with a NaN `priv` returns finite actions equal to the reference. The actor's first Linear
  has 2 inputs (no privileged column).
- **The critic really uses `priv`:** changing it changes Q (SAC) and V (PPO).
- **Structure:** critic and critic target have one LayerNorm per hidden layer and none on the output; the critic
  optimizer holds exactly the critic's parameters, disjoint from the actor's; PPO's optimizer holds every parameter,
  including the replaced value extractor/MLP.
- **Zero residual at init:** SAC deterministic action is exactly 0 (scaled and through `predict`); PPO `action_net`
  weight and bias are 0.
- **Pre-fill:** 450 zero-action transitions with `SubprocVecEnv(2)` across the 200-step time limit: buffer position
  225 per env, all stored actions 0, both truncations stored with `dones=1` and `timeouts=1` (so SAC does not treat
  them as terminal), and `next_obs` at truncation is the terminal observation, not the reset one. Then 400 SAC steps
  train from the pre-filled buffer.
- **Save/load:** both algorithms reload as the asymmetric policy classes with identical predictions.

### 3.4 Caveats (`INFERENCE` unless stated)
- **Evaluation without privileged input.** The policy's observation space still contains `priv`, so `predict()` needs
  the key. At final evaluation, fill it with NaN: the NaN test shows the actor does not read it, and any accidental
  use would show as NaN actions. Alternatively export `model.policy.actor` and feed `obs` only.
- **This relies on SB3 internals** (`make_actor`, `make_critic`, `_build`, `_build_mlp_extractor`,
  `_update_features_extractor`, `ContinuousCritic.q_networks`). They are stable across 2.x but not a public API:
  keep SB3 pinned and keep these tests in the G3 suite.
- **SAC initial exploration is not zero.** Zero mean makes the *deterministic* residual 0, but SAC samples from
  tanh(N(0, σ)); with the default `log_std` Linear, σ ≈ 1 at start, i.e. sampled residuals spread over most of the
  bound. Options: `actor_log_std_bias` (e.g. -1 to -2), or rely on the pre-filled buffer and auto-entropy
  (`target_entropy = -dim(A)` by default). This is a design choice for the residual-bound pilot.
- **PPO is not squashed.** SB3 PPO samples an unbounded Gaussian and clips to the action box (`log_std_init=0` gives
  σ = 1 in normalised units). For a matched B3 a smaller `log_std_init` is needed; the clip also makes the stored
  action differ from the executed one.
- **LayerNorm on PPO's value function** is an option here (`vf_layer_norm`), not a P-146 decision; whether B3 gets it
  should be decided for the matched comparison.
- Zero-initialising the last layer means the hidden layers get no gradient through the actor until the mean weights
  move away from 0; this is standard for residual RL but a small-scale init (e.g. 1e-3) is an alternative.

## 4. Pitfalls

1. **Learning-starts warm-up injects random residuals.** `OffPolicyAlgorithm._sample_action` uses
   `action_space.sample()` (uniform over the whole bound) while `num_timesteps < learning_starts` (default 100). With
   a pre-filled buffer set **`learning_starts=0`**, otherwise B0 data is mixed with uniform random residuals.
2. **Replay pre-fill API.** There is no public "pre-fill" call. Use `model.replay_buffer.add(obs, next_obs, action,
   reward, done, infos)` after constructing the model and before `learn()`:
   - shapes carry the `n_envs` axis; with a Dict space, obs/next_obs are dicts of `(n_envs, ...)` arrays;
   - store the **scaled** action (`model.policy.scale_action`); for a [-1, 1] box this is the identity;
   - on episode end use `infos[i]["terminal_observation"]` as next_obs (the VecEnv has already reset);
   - pass `infos` so `handle_timeout_termination` reads `TimeLimit.truncated`;
   - `buffer_size` is divided by `n_envs` internally (`buffer_size // n_envs` rows);
   - with `VecNormalize`, store **un-normalised** obs (SB3 does); the probe helper refuses VecNormalize;
   - `learn(reset_num_timesteps=True)` resets the env but does **not** clear the buffer;
   - alternatively, `save_replay_buffer` / `load_replay_buffer` persist a pre-filled buffer for reuse across seeds
     (the 20k B0 transitions could be generated once per seed and logged).
3. **SAC with `n_envs > 1`** (`FACT`, source and docs): each `env.step()` counts `n_envs` timesteps; `train_freq` (in
   steps) counts vector steps, so an update happens every `train_freq * n_envs` transitions; `gradient_steps=1`
   then gives one gradient step per `n_envs` transitions (with 8 envs, a replay ratio of 1/8). `gradient_steps=-1`
   does as many gradient steps as transitions collected. `train_freq` in episodes requires a single env (assert).
   The G3 budget (2e5 steps) and update-to-data ratio should be stated in these terms, and B3 PPO matched on
   environment transitions.
4. **Seeding / determinism on CPU.** `seed=` seeds Python, NumPy, torch, the action space and the VecEnv (env `i` gets
   `seed + i`, applied at the next reset only). Same seed reruns were bit-identical (SAC and PPO, `SubprocVecEnv`,
   one torch thread). SB3 docs: reproducibility is not guaranteed across PyTorch releases or platforms.
   Thread count ([`determinism_threads.py`](../../experiments/G3_env/deps_probe/determinism_threads.py),
   [`determinism_threads_results.json`](../../experiments/G3_env/deps_probe/determinism_threads_results.json)): SAC
   256x256, batch 256, 600 steps, was bit-identical with 1 and 2 torch threads (max parameter difference 0.0). Only
   1 vs 2 threads was tested (CPU budget); higher counts or other batch sizes may change reduction order, so **fix
   the thread count** for all scored runs rather than rely on this. Record `torch.get_num_threads()`, torch build and SB3 version in each run log.
5. **Torch threads with SubprocVecEnv.** Default torch intra-op threads = number of cores (16 here). With N MuJoCo
   worker processes plus the learner, set `torch.set_num_threads(1)` (or a small k) in the learner; small MLPs
   gain little from more threads and oversubscription slows the MuJoCo workers. `th.set_num_threads` does not
   propagate to workers, but `OMP_NUM_THREADS` does.
6. **Workers import torch.** With `forkserver`/`spawn`, each worker imports `stable_baselines3` (hence torch) to run
   `_worker`. This costs start-up time (part of the 24-29 s first SAC run) and memory per worker; measure it in the
   throughput step (G3 design step 4) with 1/4/8 envs.
7. **Process-global MuJoCo callback.** Use `SubprocVecEnv` (never `DummyVecEnv` with more than one env) and install
   the passive callback inside the env constructor in the worker. `forkserver` workers did not inherit the main
   process's callback state (§2). Do not create a MuJoCo cube env in the learner process unless it is the only one.
8. **Monitor and truncation.** Use Gymnasium `TimeLimit`/`truncated=True` for time limits, not `terminated`, so SAC
   bootstraps through time-outs (the buffer's `timeouts` array).
9. **Float types.** SB3 actions are float32; adding a float32 0.0 residual to a float64 setpoint is exact, so
   "residual = 0 reproduces G2 bit-identically" (design step 3) is achievable, but the G3 env should test it.

## 5. Sources (accessed 2026-11-28)

- PyPI JSON: https://pypi.org/pypi/stable-baselines3/json, https://pypi.org/pypi/gymnasium/json,
  https://pypi.org/pypi/torch/json, https://pypi.org/pypi/cloudpickle/json (versions, upload dates, requires_dist,
  licence metadata).
- PyTorch CPU index: https://download.pytorch.org/whl/cpu/torch/ (`torch-2.15.0+cpu-cp312-cp312-manylinux_2_28_x86_64.whl`
  and Windows wheels present).
- Licences: https://raw.githubusercontent.com/DLR-RM/stable-baselines3/master/LICENSE,
  https://raw.githubusercontent.com/Farama-Foundation/Gymnasium/main/LICENSE,
  https://raw.githubusercontent.com/pytorch/pytorch/main/LICENSE; plus the `LICENSE`/`NOTICE` files and `METADATA`
  in each installed wheel.
- uv + PyTorch: https://docs.astral.sh/uv/guides/integration/pytorch/ (explicit CPU index, `[tool.uv.sources]`).
- SB3 docs: https://stable-baselines3.readthedocs.io/en/master/guide/algos.html (reproducibility; off-policy with
  multiple envs collects `train_freq * n_envs` steps per update),
  https://stable-baselines3.readthedocs.io/en/master/guide/custom_policy.html (separate extractors for off-policy;
  `share_features_extractor`; `_build_mlp_extractor` example).
- SB3 2.9.2 source as installed: `common/torch_layers.py` (`create_mlp`), `common/policies.py`
  (`ContinuousCritic`, `ActorCriticPolicy`), `sac/policies.py`, `common/off_policy_algorithm.py`
  (`_sample_action`, `_store_transition`, `collect_rollouts`), `common/buffers.py`, `common/vec_env/subproc_vec_env.py`.

## 6. Files created

All under `experiments/G3_env/deps_probe/` (plus this report): `asym_ac.py`, `toy_envs.py`, `test_asym_ac.py`,
`smoke_sac_ppo.py`, `determinism_threads.py`, `smoke_results_uv_lock.json`, `smoke_results_pip_venv.json`,
`determinism_threads_results.json`, `pip_freeze_uv_lock.txt`, `pip_freeze_pip_venv.txt`, `pyproject_trial.toml`, `uv_lock_trial.lock`.
Throwaway venvs `/tmp/g3deps`, `/tmp/g3sync` and `/tmp/g3lock` are outside the repository and can be deleted.
