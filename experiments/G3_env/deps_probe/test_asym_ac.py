"""Tests for the asymmetric actor-critic probe (asym_ac.py). Throwaway venv only:

    PYTHONDONTWRITEBYTECODE=1 /tmp/g3deps/bin/python -m pytest -p no:cacheprovider \
        experiments/G3_env/deps_probe/test_asym_ac.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import torch as th
from torch import nn

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
th.set_num_threads(1)

from stable_baselines3 import PPO, SAC  # noqa: E402
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv  # noqa: E402

from asym_ac import (  # noqa: E402
    AsymmetricActorCriticPolicy,
    AsymmetricSACPolicy,
    KeySubsetExtractor,
    LayerNormContinuousCritic,
    prefill_replay_buffer,
)
from toy_envs import make_priv_pendulum  # noqa: E402

N = 64


def _batch(rng: np.random.Generator, priv: np.ndarray | None = None) -> dict[str, th.Tensor]:
    ang = rng.uniform(-np.pi, np.pi, N)
    obs = np.stack([np.cos(ang), np.sin(ang)], axis=1).astype(np.float32)
    if priv is None:
        priv = rng.uniform(-8, 8, (N, 1)).astype(np.float32)
    return {"obs": th.as_tensor(obs), "priv": th.as_tensor(priv)}


def _sac(env, **kw) -> SAC:
    pk = dict(net_arch=[64, 64], critic_layer_norm=True, zero_init_actor_mean=True)
    pk.update(kw.pop("policy_kwargs", {}))
    return SAC(AsymmetricSACPolicy, env, policy_kwargs=pk, buffer_size=5_000, batch_size=64,
               learning_starts=0, seed=0, device="cpu", **kw)


def _ppo(env, **kw) -> PPO:
    pk = dict(net_arch=dict(pi=[64, 64], vf=[64, 64]), vf_layer_norm=True)
    pk.update(kw.pop("policy_kwargs", {}))
    return PPO(AsymmetricActorCriticPolicy, env, policy_kwargs=pk, n_steps=128, batch_size=64, n_epochs=2,
               seed=0, device="cpu", **kw)


def _assert_actor_ignores_priv_sac(model: SAC) -> None:
    rng = np.random.default_rng(1)
    base = _batch(rng)
    actor = model.policy.actor
    with th.no_grad():
        a0 = actor(base, deterministic=True)
        for priv in (th.zeros(N, 1), th.full((N, 1), 1e6), th.full((N, 1), float("nan"))):
            a1 = actor({"obs": base["obs"], "priv": priv}, deterministic=True)
            assert th.equal(a0, a1)
        # stochastic path: same torch RNG state, different priv -> identical samples
        th.manual_seed(7); s0 = actor({"obs": base["obs"], "priv": th.zeros(N, 1)}, deterministic=False)
        th.manual_seed(7); s1 = actor({"obs": base["obs"], "priv": th.full((N, 1), float("nan"))}, deterministic=False)
        assert th.equal(s0, s1)
    # gradient path: priv never enters the actor's graph
    priv = base["priv"].clone().requires_grad_(True)
    out = actor({"obs": base["obs"], "priv": priv}, deterministic=True).sum()
    (g,) = th.autograd.grad(out, priv, allow_unused=True)
    assert g is None
    # the public predict() path (numpy, unscaled) with a NaN privileged input
    obs_np = {"obs": base["obs"].numpy(), "priv": np.full((N, 1), np.nan, np.float32)}
    act_nan, _ = model.predict(obs_np, deterministic=True)
    act_ref, _ = model.predict({"obs": base["obs"].numpy(), "priv": base["priv"].numpy()}, deterministic=True)
    assert np.all(np.isfinite(act_nan)) and np.array_equal(act_nan, act_ref)


def _assert_critic_uses_priv_sac(model: SAC) -> None:
    rng = np.random.default_rng(2)
    base = _batch(rng)
    act = th.zeros(N, 1)
    with th.no_grad():
        q0 = model.policy.critic(base, act)[0]
        q1 = model.policy.critic({"obs": base["obs"], "priv": base["priv"] + 3.0}, act)[0]
    assert not th.allclose(q0, q1)


def test_extractor_selects_keys() -> None:
    env = make_priv_pendulum()()
    assert KeySubsetExtractor(env.observation_space, ("obs",)).features_dim == 2
    assert KeySubsetExtractor(env.observation_space, ("obs", "priv")).features_dim == 3
    with pytest.raises(KeyError):
        KeySubsetExtractor(env.observation_space, ("nope",))


def test_sac_structure_and_init() -> None:
    model = _sac(DummyVecEnv([make_priv_pendulum()]))
    pol = model.policy
    assert pol.actor.features_extractor.keys == ("obs",)
    assert pol.critic.features_extractor.keys == ("obs", "priv")
    assert pol.critic_target.features_extractor.keys == ("obs", "priv")
    assert pol.actor.features_extractor is not pol.critic.features_extractor
    for c in (pol.critic, pol.critic_target):
        assert isinstance(c, LayerNormContinuousCritic)
        for q in c.q_networks:
            assert sum(isinstance(m, nn.LayerNorm) for m in q) == 2  # one per hidden layer
            assert isinstance(q[-1], nn.Linear)  # no LayerNorm on the output
    # actor's first layer only has 2 inputs (no privileged column)
    assert pol.actor.latent_pi[0].in_features == 2
    # zero-initialised mean: deterministic action exactly 0 (scaled and unscaled)
    rng = np.random.default_rng(0)
    with th.no_grad():
        a = pol.actor(_batch(rng), deterministic=True)
    assert th.count_nonzero(a) == 0
    act, _ = model.predict({"obs": np.array([[1.0, 0.0]], np.float32), "priv": np.array([[3.0]], np.float32)},
                           deterministic=True)
    assert np.array_equal(act, np.zeros((1, 1), np.float32))
    # critic optimizer covers the critic's own parameters, actor optimizer only the actor's
    crit_ids = {id(p) for g in pol.critic.optimizer.param_groups for p in g["params"]}
    act_ids = {id(p) for g in pol.actor.optimizer.param_groups for p in g["params"]}
    assert crit_ids == {id(p) for p in pol.critic.parameters()} and not crit_ids & act_ids


def test_sac_log_std_bias_option() -> None:
    model = _sac(DummyVecEnv([make_priv_pendulum()]), policy_kwargs=dict(actor_log_std_bias=-2.0))
    with th.no_grad():
        _, log_std, _ = model.policy.actor.get_action_dist_params(_batch(np.random.default_rng(0)))
    assert th.allclose(log_std, th.full_like(log_std, -2.0))


def test_sac_prefill_train_subproc_and_independence(tmp_path: Path) -> None:
    env = SubprocVecEnv([make_priv_pendulum() for _ in range(2)])
    try:
        model = _sac(env)
        n = prefill_replay_buffer(model, 450)  # 225 vec-steps x 2 envs, crosses the 200-step time limit
        rb = model.replay_buffer
        assert n == 450 and rb.pos == 225 and not rb.full
        assert np.all(rb.actions[:225] == 0.0)
        # time-limit truncation: dones set and flagged as timeouts (so not treated as terminal by SAC)
        assert rb.dones[:225].sum() == 2 and rb.timeouts[:225].sum() == 2
        # next_obs at the truncation step is the terminal obs, not the reset obs
        i = int(np.argmax(rb.dones[:225, 0]))
        assert not np.array_equal(rb.next_observations["obs"][i, 0], rb.observations["obs"][i + 1, 0])
        _assert_actor_ignores_priv_sac(model)
        model.learn(total_timesteps=400)
        assert model.num_timesteps == 400
        _assert_actor_ignores_priv_sac(model)  # still structural after training
        _assert_critic_uses_priv_sac(model)
        # save / load round trip keeps the asymmetric policy
        path = tmp_path / "sac_asym.zip"
        model.save(path)
        loaded = SAC.load(path, device="cpu")
        assert isinstance(loaded.policy, AsymmetricSACPolicy)
        assert loaded.policy.actor.features_extractor.keys == ("obs",)
        assert isinstance(loaded.policy.critic, LayerNormContinuousCritic)
        x = {"obs": np.array([[0.3, 0.95]], np.float32), "priv": np.array([[1.0]], np.float32)}
        assert np.array_equal(model.predict(x, deterministic=True)[0], loaded.predict(x, deterministic=True)[0])
    finally:
        env.close()


def test_ppo_asymmetric_subproc(tmp_path: Path) -> None:
    env = SubprocVecEnv([make_priv_pendulum() for _ in range(2)])
    try:
        model = _ppo(env)
        pol = model.policy
        assert not pol.share_features_extractor
        assert pol.pi_features_extractor.keys == ("obs",)
        assert pol.vf_features_extractor.keys == ("obs", "priv")
        assert pol.mlp_extractor.policy_net[0].in_features == 2
        assert pol.mlp_extractor.value_net[0].in_features == 3
        assert sum(isinstance(m, nn.LayerNorm) for m in pol.mlp_extractor.value_net) == 2
        assert th.count_nonzero(pol.action_net.weight) == 0 and th.count_nonzero(pol.action_net.bias) == 0
        # optimizer covers every parameter, including the replaced value extractor/MLP
        opt_ids = {id(p) for g in pol.optimizer.param_groups for p in g["params"]}
        assert opt_ids == {id(p) for p in pol.parameters()}
        model.learn(total_timesteps=512)
        rng = np.random.default_rng(3)
        base = _batch(rng)
        with th.no_grad():
            d0 = pol.get_distribution(base).distribution
            d1 = pol.get_distribution({"obs": base["obs"], "priv": th.full((N, 1), float("nan"))}).distribution
            assert th.equal(d0.mean, d1.mean) and th.equal(d0.stddev, d1.stddev)
            v0 = pol.predict_values(base)
            v1 = pol.predict_values({"obs": base["obs"], "priv": base["priv"] + 3.0})
            assert not th.allclose(v0, v1)
        priv = base["priv"].clone().requires_grad_(True)
        mean = pol.get_distribution({"obs": base["obs"], "priv": priv}).distribution.mean.sum()
        (g,) = th.autograd.grad(mean, priv, allow_unused=True)
        assert g is None
        path = tmp_path / "ppo_asym.zip"
        model.save(path)
        loaded = PPO.load(path, device="cpu")
        assert isinstance(loaded.policy, AsymmetricActorCriticPolicy)
        assert loaded.policy.vf_features_extractor.keys == ("obs", "priv")
        x = {"obs": np.array([[0.3, 0.95]], np.float32), "priv": np.array([[1.0]], np.float32)}
        assert np.array_equal(model.predict(x, deterministic=True)[0], loaded.predict(x, deterministic=True)[0])
    finally:
        env.close()
