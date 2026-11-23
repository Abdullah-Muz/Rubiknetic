"""Tests for ER9 Part G's static code (PROTOCOL.md G.3-G.6, G.12): er9g_layouts, er9g_stats, er9g_scan, er9g_static.

Structure and invariants only (counts, list equality, d = 0 in rigid turns, polarity oddness, the stats-only property,
agreement of the per-class counters with MagnetSystem's own stats). No stiffness or scan value of a Part G arm is
asserted or printed. Near-field tables are coarse (fast) except where a test says otherwise; no trial runs.
Run (WSL, repo root):
  ~/.venvs/rubiknetic/bin/python -m pytest experiments/ER9_anchored_core_layouts/tests/test_er9g_static.py -q
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import mujoco
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from rubiknetic.cube_logic.notation import FACE_NORMAL
from rubiknetic.cube_physics import magnets as M

HERE = Path(__file__).resolve().parents[1]


def _load(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


LY = _load("er9g_layouts")
ST = _load("er9g_stats")
SC = _load("er9g_scan")


def _coarse(mp):
    return M.near_field_tables(mp, None, quad=(4, 12), n_rho=13, n_z=9)


@pytest.fixture(scope="module")
def tables():
    out = {LY.MP42: _coarse(LY.MP42)}
    for g in LY.GRADES:
        out[LY.mp43(g)] = _coarse(LY.mp43(g))
    return out


@pytest.fixture(scope="module")
def kin():
    return SC.Kin()


def _random_pose(kin, rng, sigma_deg=1.5, face=None, deg=0.0):
    """A face turn plus random small rotations of every piece (rotation vectors about the cube centre)."""
    moves = SC.face_turn_moves(face, deg) if face else {}
    out = {}
    for x in SC.NAMES:
        base = Rotation.from_rotvec(moves.get(x, np.zeros(3)))
        out[x] = (Rotation.from_rotvec(np.radians(rng.normal(0, sigma_deg, 3))) * base).as_rotvec()
    kin.pose(out)


# ---- registry and lists (GS3) ----------------------------------------------------------------------------------------
def test_registry_refuses_unknown_arms_and_grades():
    for bad in ("H1", "G1", "HB3", "PG", "pg20", "PG20R", "S1"):
        with pytest.raises(ValueError):
            LY.arm_mags(bad)
    with pytest.raises(ValueError):
        LY.arm_mags("PG20", "N45")


@pytest.mark.parametrize("grade", LY.GRADES)
def test_gs3_passes(grade):
    r = LY.gs3(grade)
    assert r["pass"], r
    for arm, row in r["arms"].items():
        assert row["n_magnets"] == LY.G3_MAGNET_COUNTS[arm]
        assert row["pair_counts"] == LY.G11_PAIR_COUNTS[arm]


def test_pg8_is_l0_plus_the_corner_pairs_and_pg20r_flips_only_edge_piece_magnets():
    pg8, pg20, pg20r = LY.arm_mags("PG8"), LY.arm_mags("PG20"), LY.arm_mags("PG20r")
    core8 = pg8[48:]
    assert len(core8) == 16 and {g["kind"] for g in core8} == {"corner", "core_corner"}
    assert sum(g["body"] == "core" for g in core8) == 8
    assert all(LY.is_43(g) for g in core8) and not any(LY.is_43(g) for g in pg8[:48])
    flipped = [k for k in range(88) if not np.array_equal(pg20[k]["dir"], pg20r[k]["dir"])]
    assert len(flipped) == 12 and all(k >= 48 for k in flipped)
    for k in flipped:
        g = pg20r[k]
        assert g["kind"] == "edge" and g["body"] != "core" and np.array_equal(g["dir"], -pg20[k]["dir"])
        u = g["pos"] / np.linalg.norm(g["pos"])
        assert np.allclose(g["dir"], -u)                 # points at its own core magnet: head to head, repelling
    a, b = LY.arm_mags("L0", "N52"), LY.arm_mags("L0", "N35")      # the core grade does not touch L0
    assert all(x["mp"] == y["mp"] == LY.MP42 and np.array_equal(x["pos"], y["pos"]) for x, y in zip(a, b))
    assert LY.system_mp("C52", "N42") == LY.mp43("N42") and LY.system_mp("PG8", "N42") == LY.MP42


def test_build_system_types_and_kinematic_world_agree(kin, tables):
    for arm in LY.ARMS:
        ms = LY.build_system(kin.m, arm, "N52", tables)
        assert ms.n == LY.G3_MAGNET_COUNTS[arm]
        assert ms.composite == (arm in LY.PART_G_ARMS)
        assert len(ms.ii_all) == LY.G11_PAIR_COUNTS[arm]["total"]
        _random_pose(kin, np.random.default_rng(3), face="U", deg=17.0)
        p, n = ms.world(kin.d.xpos, kin.d.xmat)
        p2, n2, _ = kin.world(ms.mags)
        assert np.array_equal(p, p2) and np.array_equal(n, n2)


def test_install_er7_builds_the_arm_and_refuses_other_er7_arms(tables, monkeypatch):
    P = LY.probe_module()
    E7, M4 = P.E7, P.M4
    monkeypatch.setattr(E7, "setup_arm", E7.setup_arm)
    monkeypatch.setattr(M4, "use_magnets", M4.use_magnets)
    monkeypatch.setattr(M4, "TABLES_PROVIDER", M4.TABLES_PROVIDER)
    monkeypatch.setattr(E7, "_c52_tables", lambda _mp=None: tables[LY.mp43("N52")])
    try:
        LY.install_er7("PG20", "N52", tables=tables)
        with pytest.raises(ValueError):
            E7.setup_arm("C52")                          # an arm with 4x2 magnets runs as ER7's L0 only
        E7.setup_arm("L0")                               # ER7's own arm setup must not undo the installation
        assert M4.TABLES_PROVIDER is None
        ms = M4.use_magnets(E7.R.magnet_params_for({}), E7.R.GAP)
        assert isinstance(ms, M4.RecordingMagnetSystem) and ms.composite and ms.n == 88
        assert ms.type_labels == ["4x2_N35_s1", "4x3_N52_s1"]
        assert M4.use_magnets(E7.R.magnet_params_for({}), E7.R.GAP) is ms     # reused by key
        with pytest.raises(RuntimeError):
            M4.use_magnets(None, E7.R.GAP)
        LY.install_er7("C52", "N52", tables=tables)
        with pytest.raises(ValueError):
            E7.setup_arm("L0")                           # C52-only runs as ER7's C52 only
    finally:
        M4.restore_process()


def test_4x2_table_ignores_er7_tables_provider(monkeypatch):
    """After ER7's C52 setup sets M4.TABLES_PROVIDER (to the 4x3 N52 table), load_tables still gives the 4x2 magnets
    M5's table, the same object ER7's L0 path (no provider) gets."""
    P = LY.probe_module()
    E7, M4 = P.E7, P.M4
    monkeypatch.setattr(M4, "use_magnets", M4.use_magnets)
    monkeypatch.setattr(M4, "TABLES_PROVIDER", None)
    l0 = M4._tables_for(LY.MP42)                         # ER7's L0 path: no provider
    E7.setup_arm("C52")                                  # ER7's own (unwrapped) C52 setup sets the provider
    assert M4.TABLES_PROVIDER is not None and M4._tables_for(LY.MP42) is not l0
    got = LY.load_tables("PG20", "N52")
    assert got[LY.MP42] is l0
    assert got[LY.mp43("N52")] is E7._c52_tables()       # M6's N52 table for the 4x3 type


def test_reset_stats_resets_the_class_accumulator(kin, tables):
    diag = LY.build_system(kin.m, "PG8", "N52", tables, cls=ST.with_class_stats(M.MagnetSystem))
    acc = ST.attach(diag, ST.STRICT_D_VAL)
    d = mujoco.MjData(kin.m)
    try:
        _random_pose(kin, np.random.default_rng(5), face="U", deg=10.0)
        d.qpos[:] = kin.d.qpos
        mujoco.mj_kinematics(kin.m, d)
        diag.apply(kin.m, d)
        assert acc.calls == 1 and diag.stats["calls"] == 1 and acc.as_dict()["CE_near_evals"] > 0
        diag.reset_stats()
        assert acc.calls == 0 and diag.stats["calls"] == 0
        assert acc.as_dict() == ST.ClassStats(diag.mags, diag.mp, ST.STRICT_D_VAL).as_dict()
    finally:
        M.MagnetSystem.uninstall()


@pytest.mark.parametrize("arm", ["PG20", "PG20r", "PG8"])
def test_gs3b_composite_equals_parts(arm, tables):
    SCK = _load("er9g_selfcheck_static")
    r = SCK.gs3b(arm, "N52", tables, n_poses=8)
    assert r["pass"], r["max_rel_diff"]


# ---- path deviation (GS6, d part) -------------------------------------------------------------------------------------
def test_path_deviation_values():
    b = math.radians(45.0)
    for delta in (0.0, 0.5, 3.0, 12.0):
        a = b + math.radians(delta)
        n = np.array([[math.sin(a), 0.0, math.cos(a)]])
        assert ST.path_deviation_deg(n, "edge")[0] == pytest.approx(delta, abs=1e-9)
    corners = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]) / math.sqrt(3)
    assert ST.path_deviation_deg(corners, "corner").max() < 1e-9
    assert ST.path_deviation_deg(np.array([[0, 0, 1.0]]), "edge")[0] == pytest.approx(45.0)


@pytest.mark.parametrize("arm", ["PG20", "PG8"])
def test_d_is_zero_in_rigid_face_turns(arm):
    r = ST.gs6_path_deviation(arm, "N52", step_deg=1.0)
    assert r["poses"] == 6 * 181 and r["n_piece_magnets"] == (20 if arm == "PG20" else 8)
    assert r["max_d_deg"] < 1e-9 and r["pass"]


# ---- polarity (GS6) ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("arm", ["PG20", "PG20r", "PG8"])
def test_pair_energy_is_odd_in_each_moment(arm, tables):
    SS = _load("er9g_static")
    r = SS.gs6_polarity(arm, "N52", tables)
    assert set(r["classes"]) == {"CE", "PC", "PP3", "X"}
    assert all(w["pairs"] > 0 and w["max_rel"] <= 1e-12 for w in r["classes"].values()) and r["pass"]


# ---- the diagnostic is stats-only (GS4's static part) --------------------------------------------------------------
def _poses():
    rng = np.random.default_rng(1729)
    return [dict(), dict(face="U", deg=20.0), dict(face="R", deg=-60.0), dict(face="F", deg=90.0),
            dict(face="D", deg=5.0)], rng


@pytest.mark.parametrize("arm", ["PG20", "PG20r", "L0", "C52"])
def test_class_stats_leave_forces_and_qfrc_bit_identical(kin, tables, arm):
    plain = LY.build_system(kin.m, arm, "N52", tables)
    diag = LY.build_system(kin.m, arm, "N52", tables, cls=ST.with_class_stats(M.MagnetSystem))
    acc = ST.attach(diag, ST.STRICT_D_VAL)
    poses, rng = _poses()
    d1, d2 = mujoco.MjData(kin.m), mujoco.MjData(kin.m)
    try:
        for kw in poses:
            _random_pose(kin, rng, face=kw.get("face"), deg=kw.get("deg", 0.0))
            for d in (d1, d2):
                d.qpos[:] = kin.d.qpos
                mujoco.mj_kinematics(kin.m, d)
                d.qfrc_passive[:] = 0.0
            plain.apply(kin.m, d1)
            diag.apply(kin.m, d2)
            assert np.array_equal(d1.qfrc_passive, d2.qfrc_passive)
            p, n = plain.world(d1.xpos, d1.xmat)
            p0, n0 = p.copy(), n.copy()
            a = plain.forces(p, n)
            acc.update(p, n)                              # direct call: reads only
            assert np.array_equal(p, p0) and np.array_equal(n, n0)
            b = diag.forces(p, n)
            for x, y in zip(a, b):
                assert np.array_equal(x, y)
            assert plain.stats == diag.stats
            assert np.array_equal(plain.ii, diag.ii)
        assert acc.calls == 2 * len(poses)                # apply() feeds it; energy-style calls (stats=False) do not
    finally:
        M.MagnetSystem.uninstall()


@pytest.mark.parametrize("arm", ["L0", "C52", "PG20", "PG20r", "PG8"])
def test_class_counters_agree_with_magnet_system_stats(kin, tables, arm):
    """Same definitions as magnets.py: per type, the class counters add up to MagnetSystem's own stats."""
    ms = LY.build_system(kin.m, arm, "N52", tables)
    acc = ST.ClassStats(ms.mags, ms.mp, ST.STRICT_D_VAL)
    rng = np.random.default_rng(99)
    for face, deg in ((None, 0.0), ("U", 30.0), ("L", -45.0), ("B", 88.0), (None, 0.0)):
        _random_pose(kin, rng, sigma_deg=4.0, face=face, deg=deg)
        p, n = ms.world(kin.d.xpos, kin.d.xmat)
        ms.forces(p, n, stats=True)
        acc.update(p, n)
    s = acc.as_dict(ms.stats)
    c43 = ("PCon", "PCoff", "PP3")
    if not ms.composite:
        ks = ("CE",) if arm == "L0" else c43
        assert ms.stats["clamped_z"] == sum(s[f"{k}_clamped_z"] for k in ks)
        assert ms.stats["near_perpendicular"] == sum(s[f"{k}_near_perpendicular"] for k in ks)
        assert ms.stats["max_near_tilt_deg"] == max(s[f"{k}_max_near_tilt_deg"] for k in ks)
        assert s["cross_near"] == 0 and s["X_near_evals"] == 0
    else:
        l42, l43 = ms.type_labels
        assert ms.stats[f"clamped_z[{l42}]"] == s["CE_clamped_z"]
        assert ms.stats[f"near_perpendicular[{l42}]"] == s["CE_near_perpendicular"]
        assert ms.stats[f"max_near_tilt_deg[{l42}]"] == s["CE_max_near_tilt_deg"]
        assert ms.stats[f"clamped_z[{l43}]"] == sum(s[f"{k}_clamped_z"] for k in c43)
        assert ms.stats[f"near_perpendicular[{l43}]"] == sum(s[f"{k}_near_perpendicular"] for k in c43)
        assert ms.stats[f"max_near_tilt_deg[{l43}]"] == max(s[f"{k}_max_near_tilt_deg"] for k in c43)
        assert s["cross_near"] == ms.stats["near_cross_type"] == s["X_near_evals"]
        assert s["X_min_centre_distance_mm"] == pytest.approx(ms.stats["min_cross_type_r_m"] * 1e3, rel=0, abs=1e-12)
    assert s["legacy"]["clamped_z"] == ms.stats["clamped_z"]
    assert s["D_val_deg"] == ST.STRICT_D_VAL and s["calls"] == 5


def test_out_of_regime_rule():
    base = {f"{k}_{f}": 0 for k in ST.CLASSES for f in ("near_evals", "near_perpendicular", "max_near_tilt_deg",
                                                       "clamped_z")}
    base.update(cross_near=0, D_val_deg=2.0)
    assert not ST.out_of_regime(base, 2.0)
    for key, val in (("CE_max_near_tilt_deg", 5.01), ("CE_clamped_z", 1), ("CE_near_perpendicular", 1),
                     ("PCon_max_near_tilt_deg", 20.01), ("PCon_near_perpendicular", 1),
                     ("PCoff_max_near_tilt_deg", 7.51), ("PCoff_clamped_z", 1), ("PCoff_near_perpendicular", 1),
                     ("PP3_max_near_tilt_deg", 7.51), ("PP3_clamped_z", 1), ("PP3_near_perpendicular", 1),
                     ("cross_near", 1)):
        assert ST.out_of_regime({**base, key: val}, 2.0), key
    for key, val in (("CE_max_near_tilt_deg", 5.0), ("PCon_max_near_tilt_deg", 20.0), ("PCon_clamped_z", 7),
                     ("PCoff_max_near_tilt_deg", 7.5), ("PP3_max_near_tilt_deg", 7.5), ("X_max_near_tilt_deg", 40.0)):
        assert not ST.out_of_regime({**base, key: val}, 2.0), key
    with pytest.raises(ValueError):
        ST.out_of_regime(base, 0.5)


def test_pc_split_follows_d_val(kin, tables):
    """Offset U, then turn R (E1-5-like): PC evaluations move from PCon to PCoff as D_val shrinks; totals agree."""
    ms = LY.build_system(kin.m, "PG20", "N52", tables)
    kin.pose(SC.e15_moves(10.0, 45.0))
    p, n = ms.world(kin.d.xpos, kin.d.xmat)
    out = {}
    for dv in (0.0, ST.PROXY_D_VAL):
        acc = ST.ClassStats(ms.mags, ms.mp, dv)
        acc.update(p, n)
        out[dv] = acc.as_dict()
    a, b = out[0.0], out[ST.PROXY_D_VAL]
    assert b["PCoff_near_evals"] == 0
    assert a["PCon_near_evals"] + a["PCoff_near_evals"] == b["PCon_near_evals"]
    assert a["PCoff_near_evals"] > 0 and a["PC_max_path_dev_deg"] == b["PC_max_path_dev_deg"] > 0


# ---- P1 / P2 code paths (reference arms only; structure) -------------------------------------------------------------
@pytest.mark.parametrize("arm", ["L0", "C52"])
def test_scan_code_path_structure(arm):
    r = SC.scan(arm, step_deg=45.0, alphas=(1,), faces=("U", "R"))
    assert r["face_turns"]["per_face"]["U"]["poses"] == 5
    assert set(r["e15_like"]["per_alpha"]) == {"+1", "-1"}
    assert r["e15_like"]["per_alpha"]["+1"]["poses"] == 3
    assert len(r["stops"]) == 9 and all(isinstance(s["stop"], bool) for s in r["stops"])
    st = r["face_turns"]["combined"]["stats"]
    assert st["PC_max_path_dev_deg"] < 1e-9                 # rigid face turns stay on the validated circle
    assert st["X_near_evals"] == 0 and st["cross_near"] == 0


def test_p2_rows_and_p3_stub():
    SS = _load("er9g_static")
    for row in (("PG20r", "N35"), ("L0", "N52"), ("PG8", "N45"), ("H1", "N52")):
        with pytest.raises(ValueError):
            SS.p2(*row)
    p3 = SS.p3_inputs()
    assert p3["computed"] is False and any(x["status"] == "TODO" for x in p3["inputs"])


def test_full_matrix_copy_matches_part_a(tables):
    """full_matrix66 (mixed-type path) equals er9_screen.full_matrix on the same single-type torques (C52 layout)."""
    SS = _load("er9g_static")
    r = SS.rig()
    ms = LY.build_system(r.m, "C52", "N52", tables, pitch=r.p.pitch, gap=r.p.gap)
    T = SS.composite_torques(ms)
    a = SS.full_matrix66(r, T)
    with SS.er3_through(T):
        b = SS.S9.full_matrix(r, ms.mags, None)
    r.pose({})
    for k, v in b.items():
        assert a[k] == v, k
