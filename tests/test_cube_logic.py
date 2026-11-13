"""G1 'Logic' row: identity, inverse, invariants, reachable scrambles and
cross-agreement of two independently written cube models."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from rubiknetic.cube_logic import (
    ALL_MOVES,
    SOLVED,
    CubieCube,
    GeometricCube,
    HOME_POSITIONS,
    Move,
    geometric_to_cubie,
    invert,
    observe,
    parse,
    random_scramble,
    to_string,
)
from rubiknetic.cube_logic.cubie import BASIC
from rubiknetic.cube_logic.geometric import move_rotation

# ---------------------------------------------------------------- notation


def test_parse_roundtrip_and_errors():
    seq = parse("R U R' U' F2 B D' L")
    assert to_string(seq) == "R U R' U' F2 B D' L"
    with pytest.raises(ValueError):
        parse("X")
    with pytest.raises(ValueError):
        parse("R3")


def test_invert_sequence():
    assert to_string(invert(parse("R U' F2"))) == "F2 U R'"


def test_declared_sign_convention():
    """U (clockwise seen from above) carries the UB cubie to UR (x=R, y=B, z=U)."""
    r = move_rotation(Move("U", 1))
    assert tuple(r @ np.array([0, 1, 1])) == (1, 0, 1)
    # R clockwise seen from the right carries UR (top) to BR (back): F->U->B->D->F.
    r = move_rotation(Move("R", 1))
    assert tuple(r @ np.array([1, 0, 1])) == (1, 1, 0)


# ------------------------------------------------- identities, both models


@pytest.mark.parametrize("move", ALL_MOVES, ids=str)
def test_move_then_inverse_is_identity(move):
    assert GeometricCube().apply(move).apply(move.inverse()).is_solved(ignore_centers=False)
    assert SOLVED.apply(move).apply(move.inverse()).is_solved()


@pytest.mark.parametrize("face", "URFDLB")
def test_four_quarter_turns_is_identity(face):
    m = Move(face, 1)
    g, c = GeometricCube(), SOLVED
    for k in range(4):
        assert g.is_solved(ignore_centers=False) == (k == 0)
        assert c.is_solved() == (k == 0)
        g, c = g.apply(m), c.apply(m)
    assert g.is_solved(ignore_centers=False) and c.is_solved()


def _order(seq):
    c, n = SOLVED.apply_all(seq), 1
    while not c.is_solved():
        c, n = c.apply_all(seq), n + 1
    return n


def test_known_sequence_orders():
    assert _order(parse("R U R' U'")) == 6  # also the E1-4 physics sequence
    assert _order(parse("R U")) == 105
    assert _order(parse("R2 U2")) == 6


# ------------------------------------------------- cross-model agreement


@pytest.mark.parametrize("move", ALL_MOVES, ids=str)
def test_models_agree_on_every_single_move(move):
    assert geometric_to_cubie(GeometricCube().apply(move)) == SOLVED.apply(move)


def test_models_agree_on_random_sequences():
    for seed in range(300):
        seq = random_scramble(25, seed)
        g = GeometricCube().apply_all(seq)
        assert not g.check_legal_assembly()
        assert geometric_to_cubie(g) == SOLVED.apply_all(seq), to_string(seq)


# ------------------------------------------------- invariants


def test_basic_moves_are_legal():
    for m in BASIC.values():
        assert m.invariant_violations() == []


def test_scrambles_satisfy_invariants_and_invert_to_solved():
    for seed in range(200):
        seq = random_scramble(20, seed)
        c = SOLVED.apply_all(seq)
        assert c.invariant_violations() == []
        assert c.apply_all(invert(seq)).is_solved()
        assert GeometricCube().apply_all(seq).apply_all(invert(seq)).is_solved(ignore_centers=False)


@pytest.mark.parametrize(
    "bad, reason",
    [
        (CubieCube(co=(1, 0, 0, 0, 0, 0, 0, 0)), "twist"),
        (CubieCube(eo=(1,) + (0,) * 11), "flip"),
        (CubieCube(ep=(1, 0) + tuple(range(2, 12))), "parit"),
        (CubieCube(cp=(1, 0) + tuple(range(2, 8))), "parit"),
    ],
)
def test_illegal_states_are_detected(bad, reason):
    v = bad.invariant_violations()
    assert v and any(reason in s for s in v)


def test_scramble_generator_is_seeded_and_well_formed():
    a, b = random_scramble(30, 7), random_scramble(30, 7)
    assert a == b and a != random_scramble(30, 8)
    assert len(a) == 30
    assert all(x.face != y.face for x, y in zip(a, a[1:]))


# ------------------------------------------------- observation from poses


def _poses(g: GeometricCube, noise_pos=0.0, noise_deg=0.0, seed=0):
    rng = np.random.default_rng(seed)
    pos = g.positions.astype(float) + rng.normal(0, noise_pos, (26, 3))
    rots = []
    for r in g.rotations:
        d = Rotation.from_rotvec(np.radians(noise_deg) * rng.normal(0, 1, 3) / np.sqrt(3))
        rots.append(d.as_matrix() @ r)
    return pos, np.array(rots)


def test_observe_recovers_scrambled_state_under_small_noise():
    seq = random_scramble(20, 3)
    g = GeometricCube().apply_all(seq)
    obs = observe(*_poses(g, noise_pos=0.01, noise_deg=1.0))
    assert obs.valid, obs.problems
    assert obs.state == SOLVED.apply_all(seq)


def test_observe_refuses_mid_turn_pose():
    """A layer stopped at 45 deg must read as UNKNOWN, not snap to a neighbour."""
    g = GeometricCube()
    pos, rots = _poses(g)
    half = Rotation.from_rotvec([0, 0, -np.pi / 4]).as_matrix()
    layer = np.array(HOME_POSITIONS)[:, 2] == 1
    pos[layer] = pos[layer] @ half.T
    rots[layer] = half[None] @ rots[layer]
    obs = observe(pos, rots)
    assert not obs.valid and obs.state is None


def test_observe_rejects_twisted_corner():
    """Negative control: a corner rotated 120 deg in place is a legal-looking
    assembly but violates the twist invariant."""
    g = GeometricCube()
    i = HOME_POSITIONS.index((1, -1, 1))
    twist = Rotation.from_rotvec(2 * np.pi / 3 * np.array([1, -1, 1]) / np.sqrt(3)).as_matrix()
    g.rotations[i] = np.rint(twist).astype(int)
    obs = observe(*_poses(g))
    assert not obs.valid
    assert any("twist" in p for p in obs.problems)
