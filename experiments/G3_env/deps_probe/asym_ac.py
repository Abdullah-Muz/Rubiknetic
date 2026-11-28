"""Asymmetric actor-critic policies for Stable-Baselines3 SAC and PPO (G3 dependency probe).

Status: PROPOSAL. This is a probe written to check that SB3 2.9.2 supports the G3 design (P-146 D3/D4).
It is not project code and is not imported by `src/rubiknetic`.

Design
------
Observations are a `gymnasium.spaces.Dict`. The actor reads only `actor_keys` (default ("obs",)); the critic
(SAC Q-networks, PPO value function) reads `critic_keys` (default ("obs", "priv")). Each network gets its own
`KeySubsetExtractor`, which flattens and concatenates only the keys it is given, so the actor's computation
graph never touches the privileged tensor. `share_features_extractor` is forced to False.

Extras used by G3:
- `LayerNormContinuousCritic`: SAC critic with LayerNorm after each hidden Linear (before the activation).
- the SAC actor mean layer (`actor.mu`) is zero-initialised, so the deterministic action is exactly 0 at
  initialisation; optionally the log-std layer is set to a constant (`actor_log_std_bias`).
- the PPO `action_net` is zero-initialised (mean residual exactly 0); PPO's own `log_std_init` sets the spread.
- `prefill_replay_buffer`: stores baseline (zero-residual) transitions exactly as SB3's own `_store_transition`.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from copy import deepcopy
from typing import Any

import numpy as np
import torch as th
from gymnasium import spaces
from torch import nn

from stable_baselines3.common.policies import ActorCriticPolicy, ContinuousCritic
from stable_baselines3.common.preprocessing import get_action_dim
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor, create_mlp
from stable_baselines3.sac.policies import Actor, SACPolicy

ACTOR_KEYS: tuple[str, ...] = ("obs",)
CRITIC_KEYS: tuple[str, ...] = ("obs", "priv")


class KeySubsetExtractor(BaseFeaturesExtractor):
    """Flatten and concatenate only `keys` of a Dict observation. Other keys are never read."""

    def __init__(self, observation_space: spaces.Dict, keys: Sequence[str] = ACTOR_KEYS):
        if not isinstance(observation_space, spaces.Dict):
            raise TypeError("KeySubsetExtractor needs a Dict observation space")
        keys = tuple(keys)
        missing = [k for k in keys if k not in observation_space.spaces]
        if missing:
            raise KeyError(f"keys {missing} not in observation space {list(observation_space.spaces)}")
        for k in keys:
            if not isinstance(observation_space[k], spaces.Box):
                raise TypeError(f"key {k!r}: only Box subspaces are supported in this probe")
        dim = sum(spaces.flatdim(observation_space[k]) for k in keys)
        super().__init__(observation_space, features_dim=dim)
        self.keys = keys

    def forward(self, observations: dict[str, th.Tensor]) -> th.Tensor:
        return th.cat([th.flatten(observations[k], start_dim=1) for k in self.keys], dim=1)


# --------------------------------------------------------------------------------------------- SAC


class LayerNormContinuousCritic(ContinuousCritic):
    """ContinuousCritic whose Q-MLPs have LayerNorm after every hidden Linear (Linear -> LN -> activation)."""

    def __init__(
        self,
        observation_space: spaces.Space,
        action_space: spaces.Box,
        net_arch: list[int],
        features_extractor: BaseFeaturesExtractor,
        features_dim: int,
        activation_fn: type[nn.Module] = nn.ReLU,
        normalize_images: bool = True,
        n_critics: int = 2,
        share_features_extractor: bool = True,
    ):
        super().__init__(
            observation_space,
            action_space,
            net_arch,
            features_extractor,
            features_dim,
            activation_fn,
            normalize_images,
            n_critics,
            share_features_extractor,
        )
        action_dim = get_action_dim(self.action_space)
        self.q_networks = []
        for idx in range(n_critics):
            layers = create_mlp(features_dim + action_dim, 1, net_arch, activation_fn, post_linear_modules=[nn.LayerNorm])
            q_net = nn.Sequential(*layers)
            self.add_module(f"qf{idx}", q_net)  # replaces the plain MLP registered by the parent
            self.q_networks.append(q_net)


class AsymmetricSACPolicy(SACPolicy):
    """SACPolicy whose actor reads `actor_keys` and whose critics (and targets) read `critic_keys`."""

    def __init__(
        self,
        observation_space: spaces.Dict,
        action_space: spaces.Box,
        lr_schedule: Callable[[float], float],
        *args: Any,
        actor_keys: Sequence[str] = ACTOR_KEYS,
        critic_keys: Sequence[str] = CRITIC_KEYS,
        critic_layer_norm: bool = True,
        zero_init_actor_mean: bool = True,
        actor_log_std_bias: float | None = None,
        **kwargs: Any,
    ):
        # Set before super().__init__, because SACPolicy.__init__ calls _build -> make_actor/make_critic.
        self.actor_keys = tuple(actor_keys)
        self.critic_keys = tuple(critic_keys)
        self.critic_layer_norm = critic_layer_norm
        self.zero_init_actor_mean = zero_init_actor_mean
        self.actor_log_std_bias = actor_log_std_bias
        if kwargs.get("share_features_extractor", False):
            raise ValueError("asymmetric actor-critic needs share_features_extractor=False")
        if kwargs.get("use_sde", False):
            raise ValueError("this probe supports use_sde=False only")
        kwargs["share_features_extractor"] = False
        super().__init__(observation_space, action_space, lr_schedule, *args, **kwargs)

    def make_actor(self, features_extractor: BaseFeaturesExtractor | None = None) -> Actor:
        extractor = KeySubsetExtractor(self.observation_space, self.actor_keys)
        actor_kwargs = self._update_features_extractor(self.actor_kwargs, extractor)
        actor = Actor(**actor_kwargs).to(self.device)
        if self.zero_init_actor_mean:
            nn.init.zeros_(actor.mu.weight)
            nn.init.zeros_(actor.mu.bias)
        if self.actor_log_std_bias is not None:
            nn.init.zeros_(actor.log_std.weight)
            nn.init.constant_(actor.log_std.bias, self.actor_log_std_bias)
        return actor

    def make_critic(self, features_extractor: BaseFeaturesExtractor | None = None) -> ContinuousCritic:
        extractor = KeySubsetExtractor(self.observation_space, self.critic_keys)
        critic_kwargs = self._update_features_extractor(self.critic_kwargs, extractor)
        critic_cls = LayerNormContinuousCritic if self.critic_layer_norm else ContinuousCritic
        return critic_cls(**critic_kwargs).to(self.device)

    def _get_constructor_parameters(self) -> dict[str, Any]:
        data = super()._get_constructor_parameters()
        data.update(
            actor_keys=self.actor_keys,
            critic_keys=self.critic_keys,
            critic_layer_norm=self.critic_layer_norm,
            zero_init_actor_mean=self.zero_init_actor_mean,
            actor_log_std_bias=self.actor_log_std_bias,
        )
        return data


# --------------------------------------------------------------------------------------------- PPO


class AsymmetricMlpExtractor(nn.Module):
    """MlpExtractor with different input sizes for the policy and value branches (never shared)."""

    def __init__(
        self,
        pi_dim: int,
        vf_dim: int,
        net_arch: list[int] | dict[str, list[int]],
        activation_fn: type[nn.Module],
        vf_layer_norm: bool = False,
    ):
        super().__init__()
        if isinstance(net_arch, dict):
            pi_arch, vf_arch = list(net_arch.get("pi", [])), list(net_arch.get("vf", []))
        else:
            pi_arch = vf_arch = list(net_arch)
        post = [nn.LayerNorm] if vf_layer_norm else None
        self.policy_net = nn.Sequential(*create_mlp(pi_dim, -1, pi_arch, activation_fn))
        self.value_net = nn.Sequential(*create_mlp(vf_dim, -1, vf_arch, activation_fn, post_linear_modules=post))
        self.latent_dim_pi = pi_arch[-1] if pi_arch else pi_dim
        self.latent_dim_vf = vf_arch[-1] if vf_arch else vf_dim

    def forward(self, features: tuple[th.Tensor, th.Tensor]) -> tuple[th.Tensor, th.Tensor]:
        pi_features, vf_features = features
        return self.forward_actor(pi_features), self.forward_critic(vf_features)

    def forward_actor(self, features: th.Tensor) -> th.Tensor:
        return self.policy_net(features)

    def forward_critic(self, features: th.Tensor) -> th.Tensor:
        return self.value_net(features)


class AsymmetricActorCriticPolicy(ActorCriticPolicy):
    """PPO/A2C policy: pi reads `actor_keys`, the value function reads `critic_keys`."""

    def __init__(
        self,
        observation_space: spaces.Dict,
        action_space: spaces.Space,
        lr_schedule: Callable[[float], float],
        *args: Any,
        actor_keys: Sequence[str] = ACTOR_KEYS,
        critic_keys: Sequence[str] = CRITIC_KEYS,
        vf_layer_norm: bool = False,
        zero_init_action_net: bool = True,
        **kwargs: Any,
    ):
        self.actor_keys = tuple(actor_keys)
        self.critic_keys = tuple(critic_keys)
        self.vf_layer_norm = vf_layer_norm
        self.zero_init_action_net = zero_init_action_net
        if kwargs.get("share_features_extractor", False):
            raise ValueError("asymmetric actor-critic needs share_features_extractor=False")
        kwargs["share_features_extractor"] = False
        kwargs["features_extractor_class"] = KeySubsetExtractor
        kwargs["features_extractor_kwargs"] = {"keys": self.actor_keys}
        super().__init__(observation_space, action_space, lr_schedule, *args, **kwargs)

    def _build(self, lr_schedule: Callable[[float], float]) -> None:
        # ActorCriticPolicy.__init__ made pi and vf extractors from the same class/kwargs (actor keys);
        # replace the value extractor before the MLPs, init gains and optimizer are built.
        self.vf_features_extractor = KeySubsetExtractor(self.observation_space, self.critic_keys)
        super()._build(lr_schedule)
        if self.zero_init_action_net:
            with th.no_grad():
                nn.init.zeros_(self.action_net.weight)
                nn.init.zeros_(self.action_net.bias)

    def _build_mlp_extractor(self) -> None:
        self.mlp_extractor = AsymmetricMlpExtractor(
            self.pi_features_extractor.features_dim,
            self.vf_features_extractor.features_dim,
            self.net_arch,
            self.activation_fn,
            self.vf_layer_norm,
        )

    def _get_constructor_parameters(self) -> dict[str, Any]:
        data = super()._get_constructor_parameters()
        data.pop("features_extractor_class", None)
        data.pop("features_extractor_kwargs", None)
        data.update(
            actor_keys=self.actor_keys,
            critic_keys=self.critic_keys,
            vf_layer_norm=self.vf_layer_norm,
            zero_init_action_net=self.zero_init_action_net,
        )
        return data


# ------------------------------------------------------------------------------- replay pre-fill


def prefill_replay_buffer(
    model: Any,
    n_transitions: int,
    action_fn: Callable[[Any], np.ndarray] | None = None,
) -> int:
    """Fill `model.replay_buffer` with baseline transitions before `model.learn`.

    `action_fn(obs) -> unscaled action of shape (n_envs, *action_shape)`; default is the zero residual.
    Mirrors OffPolicyAlgorithm._store_transition: the stored action is policy.scale_action(action),
    `next_obs` uses infos[i]["terminal_observation"] on episode end, and the buffer's own
    handle_timeout_termination reads infos[i]["TimeLimit.truncated"]. VecNormalize is not supported here.
    Returns the number of transitions stored (rounded up to a multiple of n_envs).
    """
    if model.get_vec_normalize_env() is not None:
        raise NotImplementedError("pre-fill with VecNormalize must store un-normalised obs; not covered here")
    env = model.get_env()
    n_envs = env.num_envs
    act_shape = model.action_space.shape
    obs = env.reset()
    steps = math.ceil(n_transitions / n_envs)
    for _ in range(steps):
        action = np.zeros((n_envs, *act_shape), dtype=np.float32) if action_fn is None else action_fn(obs)
        buffer_action = model.policy.scale_action(action)
        new_obs, rewards, dones, infos = env.step(action)
        next_obs = deepcopy(new_obs)
        for i, done in enumerate(dones):
            term = infos[i].get("terminal_observation")
            if done and term is not None:
                if isinstance(next_obs, dict):
                    for key in next_obs:
                        next_obs[key][i] = term[key]
                else:
                    next_obs[i] = term
        model.replay_buffer.add(obs, next_obs, buffer_action, rewards, dones, infos)
        obs = new_obs
    return steps * n_envs
