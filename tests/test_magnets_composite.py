"""Tests for the composite (two-type) magnet system (P-67 item 2): M5's 4x2 mm N35 corner-edge magnets plus 4x3 mm core
pairs in one MagnetSystem.

1. Single-type equivalence: for M5's layout (L0) and C52's core layout, the current MagnetSystem gives forces, torques,
   energy, stats, neighbour lists and qfrc_passive bit-for-bit equal to the frozen pre-P-67 code
   (tests/legacy_magnets_911e45b.py), over a pose sequence that rebuilds the neighbour list.
2. Composite: same-type groups equal the single-type systems; cross-type pairs equal an independent point-dipole
   computation (and its finite-difference gradient); net force and torque about the origin vanish; near_cross_type is
   0 at home and counts a contrived near cross pair.
3. ER7's L0 and C52 installation paths (unchanged runner code) still build the same magnet list and parameters.

Near-field tables are coarse (fast); these tests check structure and bookkeeping, not table accuracy. No trial runs.
"""
from __future__ import annotations

import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

import mujoco
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from rubiknetic.cube_logic.geometric import HOME_POSITIONS
from rubiknetic.cube_physics import magnets as M
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml, cubie_name

REPO = Path(__file__).resolve().parents[1]
GAP = 5e-5                                                     # M5 / ER7 piece gap
CLEAR = 2e-4                                                   # C52 core clearance
MP42 = M.MagnetParams()                                        # M5: 4 x 2 mm N35
MP43 = M.MagnetParams(diameter=0.004, length=0.003, grade="N52")   # ER7 C52: 4 x 3 mm N52


def _load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


LEGACY = _load("legacy_magnets_911e45b", Path(__file__).resolve().parent / "legacy_magnets_911e45b.py")


def _coarse(mp):
    return M.near_field_tables(mp, None, quad=(4, 12), n_rho=13, n_z=9)


@pytest.fixture(scope="module")
def t42():
    return _coarse(MP42)


@pytest.fixture(scope="module")
def t43():
    return _coarse(MP43)


@pytest.fixture
def cube():
    p = M1Params(radial_preload=0.0, gap=GAP, rig=True)
    m = mujoco.MjModel.from_xml_string(build_m1_xml(p))
    d = mujoco.MjData(m)
    yield p, m, d
    M.MagnetSystem.uninstall()


def _set_pose(m, d, rng=None, sigma_deg=2.0, face=None, angle_deg=0.0):
    """Home, plus an optional rigid turn of the layer with outward normal `face` (a unit axis vector), plus optional
    random joint perturbations of sigma_deg."""
    mujoco.mj_resetData(m, d)
    if face is not None:
        nrm = np.asarray(face, float)
        q = Rotation.from_rotvec(np.radians(angle_deg) * nrm).as_quat()
        for h in HOME_POSITIONS:
            if int(np.dot(h, nrm)) != 1:
                continue
            j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, cubie_name(h) + "_j")
            a = m.jnt_qposadr[j]
            if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_BALL:
                d.qpos[a:a + 4] = [q[3], q[0], q[1], q[2]]
            else:
                d.qpos[a] = np.radians(angle_deg)
    if rng is not None:
        for k in range(m.njnt):
            a = m.jnt_qposadr[k]
            if m.jnt_type[k] == mujoco.mjtJoint.mjJNT_BALL:
                dq = Rotation.from_rotvec(np.radians(rng.normal(0, sigma_deg, 3)))
                cur = Rotation.from_quat([*d.qpos[a + 1:a + 4], d.qpos[a]])
                x = (cur * dq).as_quat()
                d.qpos[a:a + 4] = [x[3], x[0], x[1], x[2]]
            elif m.jnt_type[k] == mujoco.mjtJoint.mjJNT_HINGE:
                d.qpos[a] += np.radians(rng.normal(0, sigma_deg))
    mujoco.mj_forward(m, d)


def _poses():
    """Pose sequence: home, small perturbations, and turns large enough to force neighbour-list rebuilds."""
    rng = np.random.default_rng(6767)
    seq = [dict()]
    seq += [dict(rng=rng, sigma_deg=2.0) for _ in range(3)]
    seq += [dict(face=(0, 0, 1), angle_deg=a, rng=rng, sigma_deg=1.0) for a in (10.0, 30.0, 45.0, 60.0, 90.0)]
    seq += [dict(face=(1, 0, 0), angle_deg=a, rng=rng, sigma_deg=1.0) for a in (-20.0, -45.0)]
    seq += [dict(rng=rng, sigma_deg=2.0)]
    return seq


def _same_stats(a: dict, b: dict) -> bool:
    return a.keys() == b.keys() and all(a[k] == b[k] for k in a)


# ---- 1. single-type equivalence with the frozen pre-P-67 code ----------------------------------------------------
@pytest.mark.parametrize("which", ["L0", "C52"])
@pytest.mark.parametrize("tag", ["untyped", "typed", "typed_other_wall"])
def test_single_type_is_bit_identical_to_the_frozen_code(cube, t42, t43, which, tag):
    p, m, d = cube
    mp, tab = (MP42, t42) if which == "L0" else (MP43, t43)
    base = M.layout(p.pitch, p.gap, mp) if which == "L0" else M.core_layout(mp, CLEAR)
    old = LEGACY.MagnetSystem(m, p.pitch, p.gap, mp, tables=tab, mags=None if which == "L0" else base)
    if tag == "untyped":
        mags = None if which == "L0" else base
    else:                    # magnets tagged with their own type (wall is not a force-law field: still one type)
        mags = M.typed(base, mp if tag == "typed" else replace(mp, wall=mp.wall + 1e-4))
    new = M.MagnetSystem(m, p.pitch, p.gap, mp, tables=tab, mags=mags)
    assert not new.composite and new.type_labels == [M.type_label(mp)]
    assert new.n == old.n and np.array_equal(new.body, old.body)
    assert np.array_equal(new.p_loc, old.p_loc) and np.array_equal(new.d_loc, old.d_loc)
    assert np.array_equal(new.ii_all, old.ii_all) and np.array_equal(new.jj_all, old.jj_all)
    assert new.describe() == old.describe() and _same_stats(new.stats, old.stats)
    for kw in _poses():
        _set_pose(m, d, **kw)
        for stats in (False, True):
            pn = new.world(d.xpos, d.xmat)
            po = old.world(d.xpos, d.xmat)
            assert all(np.array_equal(a, b) for a, b in zip(pn, po))
            for a, b in zip(new.forces(*pn, stats=stats), old.forces(*po, stats=stats)):
                assert np.array_equal(a, b)
        d.qfrc_passive[:] = 0.0
        new.apply(m, d)
        qn = d.qfrc_passive.copy()
        d.qfrc_passive[:] = 0.0
        old.apply(m, d)
        assert np.array_equal(qn, d.qfrc_passive)
        assert np.array_equal(new.ii, old.ii) and np.array_equal(new.jj, old.jj)
        assert _same_stats(new.stats, old.stats), (new.stats, old.stats)
    assert old.stats["list_rebuilds"] > 1                      # the sequence exercised the neighbour list
    new.reset_neighbour_list(); old.reset_neighbour_list()
    new.reset_stats(); old.reset_stats()
    assert np.array_equal(new.ii, old.ii) and _same_stats(new.stats, old.stats)


# ---- 2. composite: M5's 48 (4x2 N35) + C52's 20 core pairs (4x3 N52) -----------------------------------------------
def _composite(p, m, t42, t43, grade="N52"):
    mp43 = replace(MP43, grade=grade)
    mags = M.typed(M.layout(p.pitch, p.gap, MP42), MP42) + M.typed(M.core_layout(mp43, CLEAR), mp43)
    tables = {mp43: t43 if grade == "N52" else _coarse(mp43)}
    return M.MagnetSystem(m, p.pitch, p.gap, MP42, tables=t42, mags=mags, type_tables=tables), mp43


def test_composite_construction(cube, t42, t43):
    p, m, d = cube
    ms, mp43 = _composite(p, m, t42, t43)
    assert ms.composite and ms.n == 88 and ms.type_labels == ["4x2_N35_s1", "4x3_N52_s1"]
    assert np.array_equal(ms.type_of, [0] * 48 + [1] * 40)
    assert np.allclose(ms.moments, [MP42.moment] * 48 + [mp43.moment] * 40, rtol=0, atol=0)
    assert ms.type_splines[0] is t42 and ms.type_splines[1] is t43
    desc = ms.describe()
    assert [t["n_magnets"] for t in desc["types"]] == [48, 40] and desc["n_magnets"] == 88
    for k in ("near_cross_type", "min_cross_type_r_m", "clamped_z[4x2_N35_s1]", "max_near_tilt_deg[4x3_N52_s1]"):
        assert k in ms.stats


def test_composite_rejects_mismatched_shared_fields_and_missing_system_type(cube, t42, t43):
    p, m, _ = cube
    bad = replace(MP43, r2=0.009)
    with pytest.raises(ValueError, match="r2"):
        M.MagnetSystem(m, p.pitch, p.gap, MP42, tables=t42, type_tables={bad: t43},
                       mags=M.typed(M.layout(p.pitch, p.gap, MP42), MP42) + M.typed(M.core_layout(bad, CLEAR), bad))
    with pytest.raises(ValueError, match="system MagnetParams"):
        M.MagnetSystem(m, p.pitch, p.gap, MP42, tables=t42, type_tables={MP43: t43},
                       mags=M.typed(M.core_layout(MP43, CLEAR), MP43))
    # review hardening (2026-11-22): every tagged magnet is checked, not only the first of each type
    split = M.typed(M.core_layout(MP43, CLEAR), MP43)
    split[-1] = {**split[-1], "mp": bad}
    with pytest.raises(ValueError, match="r2"):
        M.MagnetSystem(m, p.pitch, p.gap, MP42, tables=t42, type_tables={MP43: t43},
                       mags=M.typed(M.layout(p.pitch, p.gap, MP42), MP42) + split)
    with pytest.raises(ValueError, match="r1"):                 # a primary-type tag with another r1 is not ignored
        M.MagnetSystem(m, p.pitch, p.gap, MP42, tables=t42,
                       mags=M.typed(M.layout(p.pitch, p.gap, MP42), replace(MP42, r1=0.003)))
    with pytest.raises(ValueError, match="r2"):                 # a table keyed by a type with another r2
        M.MagnetSystem(m, p.pitch, p.gap, MP42, tables=t42, type_tables={replace(MP43, r2=0.004): t43},
                       mags=M.typed(M.layout(p.pitch, p.gap, MP42), MP42) + M.typed(M.core_layout(MP43, CLEAR), MP43))
    close = replace(MP43, scale=1.0000001)                     # a distinct type whose label would collide
    with pytest.raises(ValueError, match="share a label"):
        M.MagnetSystem(m, p.pitch, p.gap, MP42, tables=t42, type_tables={MP43: t43, close: t43},
                       mags=M.typed(M.layout(p.pitch, p.gap, MP42), MP42) + M.typed(M.core_layout(MP43, CLEAR), MP43)
                       + M.typed(M.core_layout(close, CLEAR), close))


def test_composite_after_ordinary_neighbour_list_rebuilds(cube, t42, t43):
    """Review gap (2026-11-22): run the pose sequence WITHOUT resetting the neighbour list, so groups are rebuilt by
    _update_list itself, and compare with fresh single-type systems plus the brute-force cross sum."""
    p, m, d = cube
    ms, mp43 = _composite(p, m, t42, t43)
    for kw in _poses():
        _set_pose(m, d, **kw)
        pp, n = ms.world(d.xpos, d.xmat)
        F, T, U = ms.forces(pp, n, stats=True)
        s42 = M.MagnetSystem(m, p.pitch, p.gap, MP42, tables=t42)
        s43 = M.MagnetSystem(m, p.pitch, p.gap, mp43, tables=t43, mags=M.core_layout(mp43, CLEAR))
        F42, T42, U42 = s42.forces(*s42.world(d.xpos, d.xmat))
        F43, T43, U43 = s43.forces(*s43.world(d.xpos, d.xmat))
        Fr, Tr, Ur, _, _ = _cross_reference(ms, pp, n)
        Fe, Te = Fr.copy(), Tr.copy()
        Fe[:48] += F42; Te[:48] += T42
        Fe[48:] += F43; Te[48:] += T43
        np.testing.assert_allclose(F, Fe, rtol=0, atol=1e-10 * np.abs(Fe).max())
        np.testing.assert_allclose(T, Te, rtol=0, atol=1e-10 * np.abs(Te).max())
        assert U == pytest.approx(U42 + U43 + Ur, rel=1e-10)
    assert ms.stats["list_rebuilds"] > 1                      # groups were rebuilt by ordinary list updates


def _cutoff_ref(r, r1, r2):
    """Independent C2 quintic taper w(r) and dw/dr."""
    if r <= r1:
        return 1.0, 0.0
    if r >= r2:
        return 0.0, 0.0
    t = (r - r1) / (r2 - r1)
    return 1 - t ** 3 * (10 - 15 * t + 6 * t * t), -30 * t * t * (1 - t) ** 2 / (r2 - r1)


def _dipole_ref(pa, ma, pb, mb, r1, r2):
    """Textbook point-dipole pair, times the taper: energy, force on b, torque on b and on a (about their centres)."""
    c = 1e-7
    rv = pb - pa
    r = np.linalg.norm(rv)
    e = rv / r
    U0 = c * (ma @ mb - 3 * (ma @ e) * (mb @ e)) / r ** 3
    Fb0 = 3 * c / r ** 4 * ((ma @ e) * mb + (mb @ e) * ma + (ma @ mb) * e - 5 * (ma @ e) * (mb @ e) * e)
    Ba = c * (3 * (ma @ e) * e - ma) / r ** 3            # field of a at b
    Bb = c * (3 * (mb @ e) * e - mb) / r ** 3            # field of b at a
    w, dw = _cutoff_ref(r, r1, r2)
    return w * U0, w * Fb0 - dw * U0 * e, w * np.cross(mb, Ba), w * np.cross(ma, Bb), r


def _cross_reference(ms, p, n):
    """Cross-type contribution from ALL cross-type pairs on different bodies (independent of the neighbour list)."""
    F, T, U, rmin, near = np.zeros((ms.n, 3)), np.zeros((ms.n, 3)), 0.0, np.inf, 0
    for a in range(ms.n):
        for b in range(a + 1, ms.n):
            if ms.body[a] == ms.body[b] or ms.type_of[a] == ms.type_of[b]:
                continue
            ma, mb = ms.types[ms.type_of[a]].moment * n[a], ms.types[ms.type_of[b]].moment * n[b]
            u, fb, tb, ta, r = _dipole_ref(p[a], ma, p[b], mb, ms.mp.far_r1, ms.mp.far_r2)
            U += u
            F[b] += fb
            F[a] -= fb
            T[b] += tb
            T[a] += ta
            rmin, near = min(rmin, r), near + int(r < ms.mp.r2)
    return F, T, U, rmin, near


def test_composite_groups_match_single_type_systems_and_an_independent_dipole_sum(cube, t42, t43):
    p, m, d = cube
    ms, mp43 = _composite(p, m, t42, t43)
    s42 = M.MagnetSystem(m, p.pitch, p.gap, MP42, tables=t42)
    s43 = M.MagnetSystem(m, p.pitch, p.gap, mp43, tables=t43, mags=M.core_layout(mp43, CLEAR))
    exact = {"4x2": True, "4x3": True}
    n_near = 0
    for kw in _poses():
        _set_pose(m, d, **kw)
        pp, n = ms.world(d.xpos, d.xmat)
        for s in (ms, s42, s43):           # same list state in every system: rebuilt fresh at this pose
            s.reset_neighbour_list()
        ms.reset_stats()
        F, T, U = ms.forces(pp, n, stats=True)
        parts = {name: (Fg, Tg, Ug) for name, Fg, Tg, Ug in ms.contributions(pp, n)}
        assert set(parts) == {"same:4x2_N35_s1", "same:4x3_N52_s1", "cross"}
        # forces() is exactly the sum of the contributions
        assert np.array_equal(F, sum(v[0] for v in parts.values()))
        # (a) same-type groups vs the single-type systems on the same magnets
        for key, s, sl, oth in (("4x2", s42, slice(0, 48), slice(48, 88)), ("4x3", s43, slice(48, 88), slice(0, 48))):
            Fg, Tg, Ug = parts[f"same:{'4x2_N35_s1' if key == '4x2' else '4x3_N52_s1'}"]
            Fs, Ts, Us = s.forces(*s.world(d.xpos, d.xmat))
            assert not Fg[oth].any() and not Tg[oth].any()
            exact[key] &= bool(np.array_equal(Fg[sl], Fs) and np.array_equal(Tg[sl], Ts) and Ug == Us)
            np.testing.assert_allclose(Fg[sl], Fs, rtol=0, atol=1e-14 * np.abs(Fs).max())
            np.testing.assert_allclose(Tg[sl], Ts, rtol=0, atol=1e-14 * np.abs(Ts).max())
            assert Ug == pytest.approx(Us, rel=1e-14)
        # (b) cross-type pairs vs the independent dipole sum over every cross pair
        Fc, Tc, Uc = parts["cross"]
        Fr, Tr, Ur, rmin, near = _cross_reference(ms, pp, n)
        np.testing.assert_allclose(Fc, Fr, rtol=0, atol=1e-10 * np.abs(Fr).max())
        np.testing.assert_allclose(Tc, Tr, rtol=0, atol=1e-10 * np.abs(Tr).max())
        assert Uc == pytest.approx(Ur, rel=1e-10)
        # the near-cross counter and closest distance agree with the brute-force count. The random perturbations
        # (independent piece tilts of 1-2 deg, larger than contact allows) do bring some cross pairs inside r2.
        assert ms.stats["near_cross_type"] == near and ms.stats["min_cross_type_r_m"] == pytest.approx(rmin, rel=1e-12)
        n_near += near
    print(f"poses with cross pairs inside r2 (counted, dipole only): {n_near} pairs in total")
    # The per-pair arithmetic of a same-type group is that of the single-type system; only the per-magnet sum
    # (scatter-matrix product with a different matrix shape) could differ in the last bit. Report which held.
    print(f"same-type groups bit-identical to single-type systems: {exact}")


def test_cross_pair_forces_are_minus_the_energy_gradient():
    """Finite-difference check of cross_pair_forces on one unlike pair (4x2 N35 with 4x3 N52) inside the far taper."""
    rng = np.random.default_rng(67)
    mom = np.array([MP42.moment, MP43.moment])
    ii, jj = np.array([0]), np.array([1])
    for _ in range(6):
        p = np.array([[0.0, 0.0, 0.0], rng.normal(0, 1, 3)])
        p[1] *= rng.uniform(0.009, 0.024) / np.linalg.norm(p[1])    # 9-24 mm: includes the 20-25 mm taper band
        n = np.array([Rotation.random(random_state=rng).apply([0, 0, 1]) for _ in range(2)])
        F, T, _, _ = M.cross_pair_forces(mom, MP42.far_r1, MP42.far_r2, ii, jj, p, n)
        h, a = 1e-8, 1e-6
        f_fd, t_fd = np.zeros(3), np.zeros(3)
        en = lambda pp, nn: M.cross_pair_forces(mom, MP42.far_r1, MP42.far_r2, ii, jj, pp, nn)[2]   # noqa: E731
        for k in range(3):
            e = np.zeros(3)
            e[k] = 1.0
            f_fd[k] = -(en(p + [np.zeros(3), h * e], n) - en(p - [np.zeros(3), h * e], n)) / (2 * h)
            rp, rm = Rotation.from_rotvec(a * e), Rotation.from_rotvec(-a * e)
            t_fd[k] = -(en(p, np.array([n[0], rp.apply(n[1])])) - en(p, np.array([n[0], rm.apply(n[1])]))) / (2 * a)
        assert np.linalg.norm(F[1] - f_fd) <= 1e-6 * np.linalg.norm(f_fd)
        assert np.linalg.norm(T[1] - t_fd) <= 1e-5 * max(np.linalg.norm(t_fd), 1e-12)
        assert np.allclose(F[0], -F[1], rtol=0, atol=1e-15)


@pytest.mark.parametrize("grade", ["N52", "N35"])
def test_composite_conserves_momentum(cube, t42, t43, grade):
    """(c) Newton's third law and angular-momentum balance of the whole composite (same-type + cross terms)."""
    p, m, d = cube
    ms, _ = _composite(p, m, t42, t43, grade)
    for kw in _poses():
        _set_pose(m, d, **kw)
        pp, n = ms.world(d.xpos, d.xmat)
        F, T, _ = ms.forces(pp, n, stats=True)
        scale = np.abs(F).sum()
        assert np.linalg.norm(F.sum(axis=0)) / scale < 1e-9
        assert np.linalg.norm((T + np.cross(pp, F)).sum(axis=0)) / (scale * 0.03) < 1e-9
    assert ms.stats["list_rebuilds"] > 1


def test_composite_near_cross_type_is_zero_at_home_and_stats_add_up(cube, t42, t43):
    """(d) at the home pose no cross pair is inside r2; per-type stats sum to the totals."""
    p, m, d = cube
    ms, _ = _composite(p, m, t42, t43)
    _set_pose(m, d)
    d.qfrc_passive[:] = 0.0
    ms.apply(m, d)
    st = ms.stats
    assert st["calls"] == 1 and st["near_cross_type"] == 0
    assert st["min_cross_type_r_m"] > ms.mp.r2
    print(f"home: closest cross-type pair {st['min_cross_type_r_m'] * 1e3:.3f} mm (r2 = {ms.mp.r2 * 1e3:g} mm)")
    for kw in _poses()[1:]:
        _set_pose(m, d, **kw)
        ms.apply(m, d)
    for k in ("clamped_z", "near_perpendicular"):
        assert st[k] == sum(st[f"{k}[{lab}]"] for lab in ms.type_labels)
    assert st["max_near_tilt_deg"] == max(st[f"max_near_tilt_deg[{lab}]"] for lab in ms.type_labels)
    print({k: v for k, v in st.items()})


def test_composite_near_cross_type_is_zero_in_rigid_single_face_turns(cube, t42, t43):
    """Rigid turns of each face, -90 to +90 deg in 7.5 deg steps: no cross pair inside r2. (Static geometry only;
    dynamics add piece tilts. At home the closest cross pair is a 4x2 edge magnet to the neighbouring corner's on-axis
    4x3 piece magnet, 9.34 mm; in rigid turns it is a 4x2 edge magnet to a core-body magnet, >= 8.12 mm by radius.)"""
    p, m, d = cube
    ms, _ = _composite(p, m, t42, t43)
    for face in [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]:
        for ang in np.arange(-90.0, 90.01, 7.5):
            _set_pose(m, d, face=face, angle_deg=float(ang))
            ms.forces(*ms.world(d.xpos, d.xmat), stats=True)
    assert ms.stats["near_cross_type"] == 0 and ms.stats["min_cross_type_r_m"] > ms.mp.r2
    print(f"rigid turns: closest cross-type pair {ms.stats['min_cross_type_r_m'] * 1e3:.3f} mm")


def test_near_cross_type_counts_a_cross_pair_inside_r2(cube, t42, t43):
    """A contrived 4x2 / 4x3 pair 5 mm apart on different bodies is counted (and given the dipole term only)."""
    p, m, d = cube
    corner = cubie_name((1, 1, 1))
    pos = np.array([0.0, 0.0, 0.0])
    mags = [{"body": corner, "pos": pos, "dir": np.array([0.0, 0.0, 1.0]), "kind": "test", "mp": MP42},
            {"body": "core", "pos": pos + [0.0, 0.0, 0.005], "dir": np.array([0.0, 0.0, 1.0]), "kind": "test",
             "mp": MP43}]
    ms = M.MagnetSystem(m, p.pitch, p.gap, MP42, tables=t42, mags=mags, type_tables={MP43: t43})
    _set_pose(m, d)
    pp, n = ms.world(d.xpos, d.xmat)
    F, T, U = ms.forces(pp, n, stats=True)
    assert ms.stats["near_cross_type"] == 1 and ms.stats["min_cross_type_r_m"] == pytest.approx(0.005)
    u, fb, tb, ta, _ = _dipole_ref(pp[0], MP42.moment * n[0], pp[1], MP43.moment * n[1], MP42.far_r1, MP42.far_r2)
    assert U == pytest.approx(u, rel=1e-12) and np.allclose(F[1], fb, rtol=1e-12, atol=0)


# ---- 3. ER7's installation paths (runner code unchanged) build the same systems as the frozen code ----------------
def test_er7_l0_and_c52_build_the_same_magnet_systems(t42, t43, monkeypatch):
    E7 = _load("er7_run_for_composite_test", REPO / "experiments/ER7_core_magnet_rehearsal/er7_run.py")
    M4 = E7.M4
    monkeypatch.setattr(M4, "TABLES_PROVIDER", lambda mp: t42)
    monkeypatch.setattr(E7, "_c52_tables", lambda _mp=None: t43)
    try:
        ms_l0 = M4.use_magnets(E7.R.magnet_params_for({}), E7.R.GAP)        # ER7 arm L0 (M5's installation)
        p = M1Params(**{**M4.BASE_OVERRIDES, "gap": E7.R.GAP})
        assert ms_l0.mp == MP42 and E7.R.GAP == GAP
        m = ms_l0.m
        refs = {"L0": LEGACY.MagnetSystem(m, p.pitch, p.gap, MP42, tables=t42)}
        got = {"L0": ms_l0}
        M4.restore_process()
        ms_c52 = E7.use_core(E7.R.magnet_params_for({}), E7.R.GAP)            # ER7 arm C52
        assert ms_c52.mp == MP43 == E7.MP52 and E7.CLEAR == CLEAR
        refs["C52"] = LEGACY.MagnetSystem(ms_c52.m, p.pitch, p.gap, MP43, tables=t43, mags=M.core_layout(MP43, CLEAR))
        got["C52"] = ms_c52
        M.MagnetSystem.uninstall()          # the passive callback is global: no evaluation from mj_forward below
        for arm in ("L0", "C52"):
            a, b = got[arm], refs[arm]
            assert not a.composite and a.n == b.n == (48 if arm == "L0" else 40)
            assert all("mp" not in g for g in a.mags)
            assert [(g["body"], g["kind"]) for g in a.mags] == [(g["body"], g["kind"]) for g in b.mags]
            assert np.array_equal(a.p_loc, b.p_loc) and np.array_equal(a.d_loc, b.d_loc)
            assert np.array_equal(a.body, b.body) and a.mp == b.mp and a.spline is b.spline
            assert np.array_equal(a.ii_all, b.ii_all) and np.array_equal(a.jj_all, b.jj_all)
            assert a.describe() == b.describe() and _same_stats(a.stats, b.stats)
            d = mujoco.MjData(a.m)
            _set_pose(a.m, d, rng=np.random.default_rng(7), sigma_deg=2.0)
            for x, y in zip(a.forces(*a.world(d.xpos, d.xmat), stats=True),
                            b.forces(*b.world(d.xpos, d.xmat), stats=True)):
                assert np.array_equal(x, y)
            assert _same_stats(a.stats, b.stats)
    finally:
        M4.restore_process()
