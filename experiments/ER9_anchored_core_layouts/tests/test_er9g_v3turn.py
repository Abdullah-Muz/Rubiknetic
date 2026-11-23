"""Tests for er9g_v3turn.py (ER9 Part G, P4). They never run P4.0 or P4.d at protocol settings and never write into the
repository: geometry, the pass rule, the driver logic (with a fake evaluator), and bit-exact reproduction of committed
ER5 V3-turn points. Run (WSL, repo root):
    OMP_NUM_THREADS=1 ~/.venvs/rubiknetic/bin/python -m pytest experiments/ER9_anchored_core_layouts/tests/test_er9g_v3turn.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("er9g_v3turn", HERE.parent / "er9g_v3turn.py")
V = importlib.util.module_from_spec(_spec)
sys.modules["er9g_v3turn"] = V
_spec.loader.exec_module(V)

MP = V.magnet_params()


# ------------------------------------------------------------------ geometry
@pytest.mark.parametrize("kind", ["edge", "corner"])
def test_on_path_d_is_zero(kind):
    p0, n0 = V.trajectory_start(MP, kind, 0.0, None)
    for deg in V.THETAS:
        n = V.ER5.rz(deg) @ n0
        assert V.path_dev_deg(n, V.BETA0_DEG[kind]) < 1e-9


@pytest.mark.parametrize("kind", ["edge", "corner"])
@pytest.mark.parametrize("direction", V.DIRECTIONS)
@pytest.mark.parametrize("d", V.D_GRID)
def test_displaced_direction_keeps_d_through_sweep(kind, direction, d):
    p0, n0 = V.piece_magnet(MP, kind)
    b0 = V.BETA0_DEG[kind]
    p, n = V.trajectory_start(MP, kind, d, direction)
    assert abs(np.linalg.norm(n) - 1) < 1e-15
    assert abs(np.linalg.norm(p) - np.linalg.norm(p0)) < 1e-16          # same radius (to a few ulp)
    assert np.allclose(p / np.linalg.norm(p), n, atol=1e-15)               # on its radial line
    beta = np.degrees(np.arccos(n @ V.TURN_AXIS))
    assert abs(beta - (b0 - d if direction == "toward" else b0 + d)) < 1e-9
    # azimuth about the turn axis kept
    az = lambda v: np.arctan2(v[1], v[0])                                   # noqa: E731
    assert abs(az(n) - az(n0)) < 1e-12
    for deg in V.THETAS:
        R = V.ER5.rz(deg)
        nm = R @ n
        # deviation from the validated circle of the turn axis equals the intended d at every theta
        assert abs(V.axis_dev_deg(nm, V.TURN_AXIS, b0) - d) < 1e-9
        # G.4's min over k never exceeds it
        assert V.path_dev_deg(nm, b0) <= d + 1e-9


@pytest.mark.parametrize("d", V.D_GRID)
def test_edge_toward_g4_equals_d(d):
    """Edge, toward the axis: G.4's min-over-k d(n) equals d at every theta (the x and y circles are farther)."""
    p, n = V.trajectory_start(MP, "edge", d, "toward")
    for deg in V.THETAS:
        assert abs(V.path_dev_deg(V.ER5.rz(deg) @ n, 45.0) - d) < 1e-9


def test_g4_min_can_be_below_d():
    """Documents a property of G.4's definition: for corners at theta = 0, and for 'away' sweeps that cross another
    axis' circle, min-over-k d(n) is below the construction displacement d (both are recorded per row)."""
    _, n = V.trajectory_start(MP, "corner", 4.0, "toward")
    assert V.path_dev_deg(n, V.BETA0_DEG["corner"]) < 4.0 - 1e-3
    _, n = V.trajectory_start(MP, "edge", 4.0, "away")
    assert min(V.path_dev_deg(V.ER5.rz(t) @ n, 45.0) for t in V.THETAS) < 0.5


def test_core_sets_match_er5():
    a_p, a_n, a_l = V.core_set(MP, "all")
    b_p, b_n, b_l = V.er5_core_set(MP)
    assert a_l == b_l and np.array_equal(a_p, b_p) and np.array_equal(a_n, b_n)
    c_p, c_n, c_l = V.core_set(MP, "corner")
    assert len(c_l) == 8 and all(all(abs(x) == 1 for x in h) for h in c_l)
    idx = [b_l.index(h) for h in c_l]
    assert idx == sorted(idx)                                              # ER5's order kept
    assert np.array_equal(c_p, b_p[idx]) and np.array_equal(c_n, b_n[idx])
    assert V.HOMES["corner"] in c_l


# ------------------------------------------------------------------ pass rule
def test_pass_rule_reproduces_er5_flags():
    com = V.er5_committed()
    for t in com["V3_turn"]:
        rows = [{k: v for k, v in r.items() if k != "pass"} for r in t["rows"]]
        assert V.apply_pass_rule(rows) == t["T_tol_Nm"]
        assert [r["pass"] for r in rows] == [r["pass"] for r in t["rows"]]
    assert sum(t["pass"] for t in com["V3_turn"]) == 2                     # real passes, B1 fails (ER5 run_log)


def test_pass_rule_arithmetic():
    rows = [{"F_err_rel_Fn": 0.05, "T_err_Nm": 2e-5, "fine_T_Nm": 1e-4},   # T_tol = floor 2e-5; both at limit
            {"F_err_rel_Fn": 0.0500001, "T_err_Nm": 0.0, "fine_T_Nm": 0.0},
            {"F_err_rel_Fn": 0.0, "T_err_Nm": 2.0001e-5, "fine_T_Nm": 0.0}]
    assert V.apply_pass_rule(rows) == 2e-5
    assert [r["pass"] for r in rows] == [True, False, False]
    rows = [{"F_err_rel_Fn": 0.0, "T_err_Nm": 4.9e-5, "fine_T_Nm": 1e-3},  # T_tol = 5 % of 1e-3
            {"F_err_rel_Fn": 0.0, "T_err_Nm": 5.1e-5, "fine_T_Nm": 0.0}]
    assert V.apply_pass_rule(rows) == pytest.approx(5e-5, rel=1e-15)
    assert [r["pass"] for r in rows] == [True, False]


def _row(deg, f=0.01, t=0.0, ft=0.01, tt=0.0, fine_t=1e-4):
    return {"deg": deg, "F_err_rel_Fn": f, "T_err_Nm": t, "F_err_rel_Fn_trial": ft, "T_err_Nm_trial": tt,
            "fine_T_Nm": fine_t, "fine_F_N": 1.0, "max_near_tilt_deg": 10.0, "n_near": 1, "near_perpendicular": 0,
            "near_pairs": [], "d_turn_axis_deg": 0.0, "d_G4_deg": 0.0}


def test_pass_rule_both_orders():
    """Each order gets ER5's rule separately (same T_tol); a point passes only if both orders pass."""
    rows = [_row(0), _row(1, ft=0.051), _row(2, tt=2.1e-5), _row(3, f=0.051), _row(4, t=1e-3, fine_t=1e-2)]
    tr = V.summarize_trajectory({"kind": "corner", "direction": "on-path", "d_deg": 0.0}, rows)
    assert tr["T_tol_Nm"] == max(0.05 * 1e-2, 2e-5)
    assert [r["pass_er5"] for r in tr["rows"]] == [True, True, True, False, False]
    assert [r["pass_trial"] for r in tr["rows"]] == [True, False, True, True, True]   # 2.1e-5 <= 5e-4 passes
    assert [r["pass"] for r in tr["rows"]] == [True, False, True, False, False]
    assert not tr["pass"] and not tr["order_er5"]["pass"] and not tr["order_trial"]["pass"]
    assert tr["order_er5"]["first_failing_deg"] == 3 and tr["order_trial"]["first_failing_deg"] == 1
    ok = V.summarize_trajectory({"kind": "edge", "direction": "toward", "d_deg": 1.0}, [_row(0), _row(1)])
    assert ok["pass"] and ok["order_er5"]["pass"] and ok["order_trial"]["pass"]


@pytest.mark.parametrize("arm", ["PG8", "PG20"])
def test_trial_order_matches_magnetsystem_pair_list(arm):
    """trial_piece_first agrees with which magnet is index i in a built (composite) MagnetSystem's 4x3 pair group,
    for the arm's magnet list (M5's 48 4x2 first, then core_layout's 4x3 entries, PG8 filtered to corners)."""
    import mujoco
    from rubiknetic.cube_physics import magnets as M
    from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml, cubie_name
    p = M1Params(radial_preload=0.0, rig=True)
    m = mujoco.MjModel.from_xml_string(build_m1_xml(p))
    mp42, mp43 = M.MagnetParams(), M.MagnetParams(diameter=0.004, length=0.003, grade="N52")
    core = M.core_layout(mp43, 2e-4)
    which = V.ARMS[arm]["core"]
    if which == "corner":
        core = [g for g in core if g["kind"] in ("corner", "core_corner")]
    mags = M.typed(M.layout(p.pitch, p.gap, mp42), mp42) + M.typed(core, mp43)
    ms = M.MagnetSystem(m, p.pitch, p.gap, mp42, tables=object(), mags=mags, type_tables={mp43: object()})
    assert ms.composite
    t43 = ms.types.index(next(t for t in ms.types if M.type_key(t) == M.type_key(mp43)))
    _, gi, gj, _ = next(g for g in ms._groups if g[0] == t43)
    assert np.all(gi < gj)
    lab = lambda g: tuple(int(v) for v in np.round(g["dir"] / np.abs(g["dir"]).max()))   # noqa: E731
    for kind in V.ARMS[arm]["kinds"]:
        piece = next(k for k, g in enumerate(mags) if g["body"] == cubie_name(V.HOMES[kind]) and g["mp"] is mp43)
        first = {}
        for a, b in zip(gi, gj):
            if piece in (a, b):
                other = b if a == piece else a
                if mags[other]["body"] == "core":                    # piece-to-core pairs only (PP3 pairs skipped)
                    first[lab(mags[other])] = bool(a == piece)
        _, _, labels = V.core_set(V.magnet_params(), which)
        assert sorted(first) == sorted(labels)                       # every core magnet pairs with the piece
        pf = V.trial_piece_first(V.magnet_params(), which, kind)
        assert [first[c] for c in labels] == list(pf)
        assert first[V.HOMES[kind]] is True                          # own core magnet: the piece is first
        assert pf.any() and not pf.all()                             # both orders occur in the trial list


def test_d_val():
    L = lambda d, c, p: {"d_deg": d, "complete": c, "pass": p}            # noqa: E731
    assert V.d_val([L(0.5, True, True), L(1, True, True), L(2, True, False)]) == 1
    assert V.d_val([L(0.5, True, False)]) == 0.0
    assert V.d_val([L(0.5, True, True), L(1, False, None)]) == 0.5        # budget hit during d = 1
    assert V.d_val([L(d, True, True) for d in V.D_GRID]) == 12.0


# ------------------------------------------------------------------ driver logic (fake evaluator; no physics)
def _fake(fail_at_d=None, fail_kind="corner", fail_dir="away", fail_order="er5"):
    calls = []

    def evaluate(spec, deg):
        calls.append((spec["kind"], spec["direction"], spec["d_deg"], deg))
        bad = (spec["d_deg"] == fail_at_d and spec["kind"] == fail_kind and spec["direction"] == fail_dir
               and deg == 45)
        r = _row(deg)
        r[V.ORDERS[fail_order][0]] = 0.06 if bad else 0.01
        r["d_turn_axis_deg"] = r["d_G4_deg"] = spec["d_deg"]
        return r
    return evaluate, calls


def test_driver_trial_order_failure_fails_level(tmp_path):
    ev, _ = _fake(fail_at_d=1.0, fail_order="trial")
    res = V.run_p4d_levels(("corner",), V.D_GRID, (0, 45), ev, V.Checkpoint(tmp_path / "t.jsonl", {}), 1e9)
    assert res["D_val_deg"] == 0.5 and res["halted_at_d_deg"] == 1.0
    tr = res["levels"][-1]["trajectories"][-1]
    assert tr["order_er5"]["pass"] and not tr["order_trial"]["pass"] and not tr["pass"]


def test_driver_halts_at_first_failing_d(tmp_path):
    ev, calls = _fake(fail_at_d=2.0, fail_kind="edge", fail_dir="away")
    ck = V.Checkpoint(tmp_path / "x.partial.jsonl", {"s": 1})
    res = V.run_p4d_levels(("edge", "corner"), V.D_GRID, (0, 45, 90), ev, ck, 1e9)
    assert res["D_val_deg"] == 1.0 and res["halted_at_d_deg"] == 2.0 and not res["stop_arm"]
    lv = res["levels"][-1]
    assert lv["d_deg"] == 2.0 and lv["pass"] is False
    assert [s["kind"] + s["direction"] for s in lv["skipped"]] == ["cornertoward", "corneraway"]
    assert not any(c[2] > 2.0 for c in calls)


def test_driver_stop_arm_and_all_pass(tmp_path):
    ev, _ = _fake(fail_at_d=0.5)
    res = V.run_p4d_levels(("corner",), V.D_GRID, (0, 45), ev, V.Checkpoint(tmp_path / "a.jsonl", {}), 1e9)
    assert res["D_val_deg"] == 0.0 and res["stop_arm"]
    ev, _ = _fake()
    res = V.run_p4d_levels(("corner",), V.D_GRID, (0, 45), ev, V.Checkpoint(tmp_path / "b.jsonl", {}), 1e9)
    assert res["D_val_deg"] == 12.0 and res["status"] == "complete" and res["halted_at_d_deg"] is None


def test_driver_budget_and_resume(tmp_path):
    path = tmp_path / "c.partial.jsonl"
    ev, calls = _fake()
    ck = V.Checkpoint(path, {"s": 2})
    ck.spent_s = 0.0
    # budget smaller than any work: stops before the first row, D_val 0 -> stop
    res = V.run_p4d_levels(("corner",), (0.5, 1.0), (0, 90), ev, ck, 0.0)
    assert res["budget_reached"] and res["D_val_deg"] == 0.0 and not calls
    # a session deadline in the past stops without rows; then a full run resumes from the checkpoint
    res = V.run_p4d_levels(("corner",), (0.5, 1.0), (0, 90), ev, V.Checkpoint(path, {"s": 2}), 1e9, deadline=0.0)
    assert res["status"] == "session"
    res1 = V.run_p4d_levels(("corner",), (0.5,), (0, 90), ev, V.Checkpoint(path, {"s": 2}), 1e9)
    n_first = len(calls)
    assert res1["D_val_deg"] == 0.5 and n_first == 4
    ck2 = V.Checkpoint(path, {"s": 2})
    assert ck2.resumed and len(ck2.rows) == 4
    res2 = V.run_p4d_levels(("corner",), (0.5, 1.0), (0, 90), ev, ck2, 1e9)
    assert res2["D_val_deg"] == 1.0 and len(calls) == n_first + 4         # d = 0.5 rows not recomputed
    with pytest.raises(SystemExit):
        V.Checkpoint(path, {"s": 3})                                       # settings differ: refuse to resume


def test_refusals(tmp_path, monkeypatch):
    f = tmp_path / "P.json"
    V._write_final(f, {"a": 1})
    with pytest.raises(FileExistsError):
        V._write_final(f, {"a": 2})
    assert json.loads(f.read_text()) == {"a": 1}

    class A:  # protocol settings
        thetas = d_grid = quad_near = quad_far = None
        out_dir = None
        arm = "PG20"
        budget_h = 8.0
    s, proto = V.settings_from_args(A, "P4.d")
    assert proto
    monkeypatch.setattr(V, "git_info", lambda: {"code_dirty": True})
    with pytest.raises(SystemExit):
        V.resolve_out(A, True)                                             # uncommitted code: refuse
    A.out_dir = str(tmp_path)
    with pytest.raises(SystemExit):
        V.resolve_out(A, True)                                             # protocol run cannot redirect output
    A.budget_h, A.out_dir = 1.0, str(V.REPO / "tmp_x")
    s, proto = V.settings_from_args(A, "P4.d")
    assert not proto
    with pytest.raises(SystemExit):
        V.resolve_out(A, False)                                            # test output inside the repo: refuse
    A.out_dir = None
    with pytest.raises(SystemExit):
        V.resolve_out(A, False)


# ------------------------------------------------------------------ physics: bit-exact ER5 reproduction (~15 s)
@pytest.fixture(scope="module")
def physics():
    tab = V.load_table(MP)
    assert tab["sha_matches_er5"] and tab["source"] == "ER5 cache"
    fn = V.fn_reference(MP)
    V.check_fn(fn)                                     # asserts 1.92 N and equality with ER5's committed Fn
    return tab["spline"], fn


@pytest.mark.parametrize("kind,deg", [("edge", 17), ("corner", 30)])
def test_reproduces_er5_v3turn_point(physics, kind, deg):
    spline, fn = physics
    cp, cn, labels = V.er5_core_set(MP)
    p0, n0 = V.piece_magnet(MP, kind)
    pf = V.trial_piece_first(MP, "all", kind)
    row = V.eval_row(MP, spline, fn, cp, cn, labels, V.HOMES[kind], p0, n0, deg, V.BETA0_DEG[kind], piece_first=pf)
    plain = V.eval_row(MP, spline, fn, cp, cn, labels, V.HOMES[kind], p0, n0, deg, V.BETA0_DEG[kind])
    assert "F_err_rel_Fn_trial" in row and "F_err_rel_Fn_trial" not in plain
    # the trial-order pair list in eval_row, with an all-False piece_first, is ER5's order: identical numbers
    same = V.eval_row(MP, spline, fn, cp, cn, labels, V.HOMES[kind], p0, n0, deg, V.BETA0_DEG[kind],
                      piece_first=np.zeros(len(cp), bool))
    assert same["F_err_rel_Fn_trial"] == same["F_err_rel_Fn"] and same["T_err_Nm_trial"] == same["T_err_Nm"]
    ref = next(t for t in V.er5_committed()["V3_turn"] if t["placement"] == "real" and t["kind"] == kind)["rows"][deg]
    for k in ("deg", "F_err_rel_Fn", "T_err_Nm", "fine_T_Nm", "fine_F_N", "max_near_tilt_deg", "n_near",
              "near_perpendicular"):
        assert row[k] == ref[k], k                                         # bit-identical
    assert row["d_G4_deg"] < 1e-9 and len(row["near_pairs"]) == row["n_near"]
    # own/other labelling: at 17 deg the near pair is the piece's own core magnet; at 30 deg (corner) it is another
    assert [q["own"] for q in row["near_pairs"]] == ([True] if deg == 17 else [False])
