"""Unit tests for the M4 magnet force law (rubiknetic.cube_physics.magnets; P-16, P-23 section 6 item 1).

The near-field tables are built at a coarse quadrature and grid so the tests run in seconds. These tests check the
structure of the force law (conservation, pose-only dependence, gradient consistency, audit compatibility), which
does not depend on table accuracy. Accuracy against the fine charge model is V3 in
experiments/D8_alignment/d8_1b_checks.py.
"""
from __future__ import annotations

import mujoco
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from rubiknetic.cube_physics import magnets as M
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml
from rubiknetic.cube_physics.rig import AuditedSim, EditAuditError

MP = M.MagnetParams()


@pytest.fixture(scope="module")
def tables():
    return M.near_field_tables(MP, None, quad=(4, 12), n_rho=13, n_z=9)


@pytest.fixture
def cube(tables):
    p = M1Params(radial_preload=0.0, rig=True)
    m = mujoco.MjModel.from_xml_string(build_m1_xml(p))
    d = mujoco.MjData(m)
    ms = M.MagnetSystem(m, p.pitch, p.gap, MP, tables=tables)
    yield m, d, ms
    M.MagnetSystem.uninstall()


def _perturb(m, d, rng, sigma_deg=2.0):
    for k in range(m.njnt):
        a = m.jnt_qposadr[k]
        if m.jnt_type[k] == mujoco.mjtJoint.mjJNT_BALL:
            q = Rotation.from_rotvec(np.radians(rng.normal(0, sigma_deg, 3))).as_quat()
            d.qpos[a:a + 4] = [q[3], q[0], q[1], q[2]]
        elif m.jnt_type[k] == mujoco.mjtJoint.mjJNT_HINGE:
            d.qpos[a] = np.radians(rng.normal(0, sigma_deg))
    mujoco.mj_forward(m, d)


def test_layout_is_48_head_to_tail_corner_edge_magnets():
    mags = M.layout(0.019, 0.0002, MP)
    assert len(mags) == 48
    assert sum(g["kind"] == "corner" for g in mags) == 24
    assert sum(g["kind"] == "edge" for g in mags) == 24
    per_body = {}
    for g in mags:
        per_body[g["body"]] = per_body.get(g["body"], 0) + 1
    assert sorted(set(per_body.values())) == [2, 3]


def test_facing_pairs_attract_at_home(cube):
    m, d, ms = cube
    mujoco.mj_forward(m, d)
    p, n = ms.world(d.xpos, d.xmat)
    assert ms.forces(p, n)[2] < 0          # net magnet energy negative: the facing pairs attract


def test_net_force_and_angular_momentum_vanish(cube):
    m, d, ms = cube
    rng = np.random.default_rng(81)
    for _ in range(5):
        _perturb(m, d, rng)
        p, n = ms.world(d.xpos, d.xmat)
        F, T, _ = ms.forces(p, n)
        scale = np.abs(F).sum()
        assert np.linalg.norm(F.sum(axis=0)) / scale < 1e-9
        assert np.linalg.norm((T + np.cross(p, F)).sum(axis=0)) / (scale * 0.03) < 1e-9


def test_forces_and_torques_are_minus_the_energy_gradient(tables):
    rng = np.random.default_rng(3)
    ii, jj = np.array([0]), np.array([1])
    for _ in range(6):
        p = np.array([[0.0, 0.0, 0.0],
                      [rng.uniform(-2e-3, 2e-3), rng.uniform(-2e-3, 2e-3),
                       rng.choice([-1.0, 1.0]) * rng.uniform(2.6e-3, 4e-3)]])
        n = np.array([Rotation.from_rotvec(rng.normal(0, np.radians(3), 3)).apply([0, 0, 1]) for _ in range(2)])
        F, T, _ = M.pair_forces(MP, tables, ii, jj, p, n)
        h, a = 1e-8, 1e-6
        f_fd, t_fd = np.zeros(3), np.zeros(3)
        for k in range(3):
            e = np.zeros(3)
            e[k] = 1.0
            up = M.pair_forces(MP, tables, ii, jj, p + [np.zeros(3), h * e], n)[2]
            um = M.pair_forces(MP, tables, ii, jj, p - [np.zeros(3), h * e], n)[2]
            f_fd[k] = -(up - um) / (2 * h)
            rp, rm = Rotation.from_rotvec(a * e), Rotation.from_rotvec(-a * e)
            up = M.pair_forces(MP, tables, ii, jj, p, np.array([n[0], rp.apply(n[1])]))[2]
            um = M.pair_forces(MP, tables, ii, jj, p, np.array([n[0], rm.apply(n[1])]))[2]
            t_fd[k] = -(up - um) / (2 * a)
        assert np.linalg.norm(F[1] - f_fd) <= 1e-6 * np.linalg.norm(f_fd)
        assert np.linalg.norm(T[1] - t_fd) <= 1e-5 * max(np.linalg.norm(t_fd), 1e-9)


def test_callback_depends_only_on_poses(cube):
    m, d, ms = cube
    _perturb(m, d, np.random.default_rng(6))

    def contrib():
        d.qfrc_passive[:] = 0.0
        ms.apply(m, d)
        return d.qfrc_passive.copy()

    base = contrib()
    rng = np.random.default_rng(7)
    d.ctrl[:] = rng.uniform(-1, 1, m.nu)
    d.time = 123.4
    d.qvel[:] = rng.normal(0, 1, m.nv)
    assert np.abs(base).max() > 0
    assert np.array_equal(contrib(), base)


def test_installed_magnets_pass_the_audit_and_a_state_write_is_still_caught(cube):
    m, d, ms = cube
    sim = AuditedSim(m, d)
    ms.install()
    sim.step(200)                          # magnets act through qfrc_passive inside mj_step: no audit violation
    assert not sim.violations and np.all(np.isfinite(d.qpos))
    d.qpos[0] += 1e-3                      # an injected state edit must still be caught with magnets installed
    with pytest.raises(EditAuditError):
        sim.step()
