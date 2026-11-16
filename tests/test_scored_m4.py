"""Fast tests for the M4 scored runner (experiments/E4_scored_m4/run.py; PHASE_1_M4_PREREGISTRATION.md section 6
item 3). No scored trial is run. Physics tests use coarse near-field tables (structure, not accuracy)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import mujoco
import numpy as np
import pytest

from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml
from rubiknetic.cube_physics.magnets import MagnetParams, near_field_tables
from rubiknetic.cube_physics.readout import CubeReadout
from rubiknetic.cube_physics.rig import AuditedSim

REPO = Path(__file__).resolve().parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R = _load("e4_scored_m4_run", "experiments/E4_scored_m4/run.py")
EXPECTED = {"E1-1": 20, "E1-2": 24, "E1-3": 22, "E1-4": 40, "E1-5": 42, "E1-5s": 20, "E1-6": 20, "E1-6t": 16}


@pytest.fixture
def coarse():
    tabs = near_field_tables(MagnetParams(), None, quad=(4, 12), n_rho=13, n_z=9)
    R.TABLES_PROVIDER = lambda mp: tabs
    yield tabs
    R.TABLES_PROVIDER = None
    R.restore_process()


# ---- seeds ---------------------------------------------------------------------------------------------------------
def test_seeds_are_m1_plus_5000_and_disjoint_from_earlier_ranges():
    all_seeds, ids = [], set()
    for exp in ("E1-1", "E1-2", "E1-3", "E1-4", "E1-5", "E1-6"):
        m1, m4 = R.E1.trials(exp), R.trials(exp)
        assert len(m4) == len(m1) == EXPECTED[exp]
        for (t1, k1, kw1), (t4, k4, kw4) in zip(m1, m4):
            assert k1 == k4 and kw4["seed"] == kw1["seed"] + 5000
            assert {k: v for k, v in kw4.items() if k != "seed"} == {k: v for k, v in kw1.items() if k != "seed"}
            assert t4.endswith(f"_s{kw4['seed']}")
    for exp in ("E1-1", "E1-2", "E1-3", "E1-4", "E1-5", "E1-5s", "E1-6", "E1-7"):
        for tid, _, kw in R.trials(exp):
            all_seeds.append(kw["seed"])
            assert (exp, tid) not in ids
            ids.add((exp, tid))
    assert all(6000 <= s <= 6999 for s in all_seeds)
    assert not set(all_seeds) & set(range(1000, 5300))
    # E1-5: 0...20 deg both signs
    e15 = sorted(kw["misalign_deg"] for _, _, kw in R.trials("E1-5"))
    assert e15 == sorted([float(d) for d in range(21)] + [float(-d) for d in range(21)])
    # E1-5s: +-1, 2, 3, 5, 8 deg x 2 seeds, each +/- pair sharing a seed, seeds not used by any other experiment
    snap = R.trials("E1-5s")
    assert len(snap) == 20
    pairs = {}
    for _, _, kw in snap:
        pairs.setdefault(kw["seed"], []).append(kw["delta_deg"])
    assert len(pairs) == 10 and all(sorted(v) == [-abs(v[0]), abs(v[0])] for v in pairs.values())
    others = {kw["seed"] for e in ("E1-1", "E1-2", "E1-3", "E1-4", "E1-5", "E1-6") for _, _, kw in R.trials(e)}
    assert not set(pairs) & others


def test_e17_drops_radial_preload_and_adds_m4_factors():
    tids = [t for t, _, _ in R.trials("E1-7")]
    assert not any("radial_preload" in t for t in tids)
    for tag in ("magnet=none", "magnet=3x1.5_N35", "magnet=4x2_N52", "face_gap_mm=0.5", "magnet_scale=0.67"):
        assert f"{tag}__6move" in tids
    assert "magnet=4x2_N35__6move" not in tids and "nominal__6move" in tids


# ---- rule 2 / rule 3 -----------------------------------------------------------------------------------------------
def _fake(tilt, ok=True):
    return {"pass": ok, "magnet_stats": {"max_near_tilt_deg": tilt}}


def test_rule2_fails_operational_trial_outside_validated_tilt():
    r = R.apply_m4_criteria(_fake(5.3), "E1-2", 5.0, True)
    assert r["pass"] is False and r["pass_m1_criteria"] is True and r["ok_magnet_validity"] is False
    assert "rule 2" in r["fail_reasons"][0] and r["validated_tilt_deg"] == 5.0
    for sub in ("E1-1", "E1-5", "E1-6a"):
        assert R.apply_m4_criteria(_fake(5.01), sub, 5.0, True)["pass"] is False
    assert R.apply_m4_criteria(_fake(4.99), "E1-2", 5.0, True)["pass"] is True
    assert R.apply_m4_criteria(_fake(4.99, ok=False), "E1-2", 5.0, True)["pass"] is False


def test_rule3_labels_abuse_trials_without_failing_them():
    for sub in ("E1-6b", "E1-6c"):
        r = R.apply_m4_criteria(_fake(9.0), sub, 5.0, True)
        assert r["pass"] is True and r["rule3_label"] == "magnet model outside validated range"
        assert "ok_magnet_validity" not in r
    r = R.apply_m4_criteria({"pass": True, "magnet_stats": None}, "E1-2", None, False)   # E1-6n arm
    assert r["pass"] is True and "ok_magnet_validity" not in r


# ---- E1-4 growth slope and E1-5s -----------------------------------------------------------------------------------
def _seq_rec(n, slope, rng):
    vals = 1.5 + slope * np.arange(n) + rng.normal(0, 0.02, n)
    return {"pass": True, "magnet_stats": {"max_near_tilt_deg": 1.0}, "sequence": " ".join(["U"] * n),
            "per_move": [{"misalignment": {"max_err_deg": float(v)}} for v in vals]}


def test_growth_slope_criterion_on_synthetic_data():
    rng = np.random.default_rng(0)
    assert R.growth_slope([1.0, 1.1, 1.2, 1.3]) == pytest.approx(0.1)
    assert R.growth_slope([1.0]) is None
    ok = R.apply_m4_criteria(_seq_rec(40, 0.0, rng), "E1-4", 5.0, True)
    assert ok["pass"] and ok["ok_growth_slope"] and ok["growth_slope_is_criterion"]
    bad = R.apply_m4_criteria(_seq_rec(40, 0.02, rng), "E1-4", 5.0, True)
    assert bad["pass"] is False and bad["ok_growth_slope"] is False
    assert bad["misalignment_growth_slope_deg_per_move"] == pytest.approx(0.02, abs=0.003)
    short = R.apply_m4_criteria(_seq_rec(24, 0.02, rng), "E1-4", 5.0, True)    # 24-move runs: reported only
    assert short["pass"] is True and "ok_growth_slope" not in short


def test_snap_criterion():
    base = {"integrity_ok": True, "t0_solved": True, "final_observed_valid": True, "final_solved": True,
            "magnet_stats": {"max_near_tilt_deg": 2.0}}
    assert R.apply_m4_criteria({**base, "delta_deg": 5.0, "U_err_after_1s_deg": 0.49}, "E1-5s", 5.0, True)["pass"]
    assert not R.apply_m4_criteria({**base, "delta_deg": -3.0, "U_err_after_1s_deg": -0.51}, "E1-5s", 5.0,
                                   True)["pass"]
    r = R.apply_m4_criteria({**base, "delta_deg": 2.0, "U_err_after_1s_deg": 0.9}, "E1-5s", 5.0, True)
    assert r["pass"] and r["snap_is_criterion"] is False                       # |delta| < 3: reported only
    assert not R.apply_m4_criteria({**base, "final_solved": False, "delta_deg": 2.0, "U_err_after_1s_deg": 0.1},
                                   "E1-5s", 5.0, True)["pass"]


# ---- E1-6m bound ---------------------------------------------------------------------------------------------------
def test_e16m_bound():
    assert R.p_bound_ok(-1.0e-3, 1.0e-3, 2.0e-3)                    # exact balance
    assert R.p_bound_ok(-1.0e-3, 1.2e-3, 1.5e-3)                    # 0.2 mJ <= 0.15 + 0.05 mJ
    assert not R.p_bound_ok(-1.0e-3, 1.21e-3, 1.5e-3)
    assert R.p_bound_ok(0.0, 0.049e-3, 0.0) and not R.p_bound_ok(0.0, 0.051e-3, 0.0)


# ---- integrity -----------------------------------------------------------------------------------------------------
def test_runner_refuses_a_dirty_tree(monkeypatch, tmp_path):
    monkeypatch.setattr(R, "OUT", tmp_path / "results")

    def dirty_git(*args):
        if args[0] == "status":
            return " M src/rubiknetic/cube_physics/magnets.py"
        return "deadbeef"

    monkeypatch.setattr(R.scored, "_git", dirty_git)
    with pytest.raises(SystemExit, match="uncommitted"):
        R.main(["E1-1"])
    # an M4-only path (the runner itself) dirty is refused too
    monkeypatch.setattr(R.scored, "require_clean_commit", lambda: "deadbeef")
    with pytest.raises(SystemExit, match="M4 frozen paths"):
        R.main(["E1-1"])
    assert not (tmp_path / "results").exists()


def test_smoke_flag_only_runs_the_smoke_list():
    with pytest.raises(SystemExit, match="smoke"):
        R.main(["E1-1", "--smoke"])


def test_missing_tables_are_refused_not_built(monkeypatch, tmp_path):
    monkeypatch.setattr(R, "TABLES", tmp_path)
    mp = R.magnet_params_for({"magnet": "3x1.5_N35"})
    assert mp.diameter == 0.003 and mp.length == 0.0015 and mp.wall == MagnetParams().wall
    with pytest.raises(R.Refused, match="does not exist"):
        R.magnet_availability(mp)
    assert not list(tmp_path.iterdir())
    assert R.magnet_params_for({}) == MagnetParams()                          # nominal is MagnetParams() exactly
    assert R.magnet_params_for({"magnet": "none"}) is None
    assert R.magnet_params_for({"face_gap_mm": 1.5}).wall == pytest.approx(0.00065)


def test_nominal_validated_tilt_is_read_from_v3():
    assert R.nominal_validated_tilt() >= 5.0


# ---- physics hooks (coarse tables) ---------------------------------------------------------------------------------
def test_startup_checks_pass_with_installed_magnets(coarse):
    res = R.startup_checks(MagnetParams())
    assert res["pass"], res
    assert res["callback_calls_in_one_step"] == 1
    assert res["displacement_vs_qvel_after"] < 1e-9 < res["displacement_vs_qvel_before"]   # semi-implicit position


def test_monitor_work_balances_energy_over_a_free_window(coarse):
    """W_mag from the step hook plus dU_mag stays inside the <P> bound while misaligned pieces are pulled back."""
    ms = R.use_magnets(MagnetParams(), M1Params().gap)
    p = M1Params(radial_preload=0.0)
    m = mujoco.MjModel.from_xml_string(build_m1_xml(p))        # patched: callback paused, body ids asserted
    sim = AuditedSim(m)
    ro = CubeReadout(m, p.pitch)
    mon = R.MagnetMonitor(m, ro)
    sim.hooks.append(mon)
    d = sim.d
    rng = np.random.default_rng(2)
    for k in range(m.njnt):
        a = m.jnt_qposadr[k]
        if m.jnt_type[k] == mujoco.mjtJoint.mjJNT_BALL:
            q = np.zeros(4)
            ax = rng.normal(size=3)
            mujoco.mju_axisAngle2Quat(q, ax / np.linalg.norm(ax), np.radians(0.3))
            d.qpos[a:a + 4] = q
    mujoco.mj_forward(m, d)
    sim.step(1)
    mon.begin_turn("U", ro.layer_members(d, "U"))
    sim.step(150)
    mon.end_turn()
    mv = mon.moves[-1]
    assert mv["magnet_buf_one_call_per_step"] and mv["magnet_steps"] == 150
    assert mv["magnet_U_range_J"] > 0 and mv["layer_magnet_force_peak_N"] > 0
    assert mv["e16m_P_ok"], mv
    assert abs(mv["e16m_residual_J"]) < 0.1 * abs(mv["magnet_W_J"])
    assert abs(mv["magnet_U0_vs_first_callback_J"]) < 1e-12
    assert "max_err_deg" in mv["misalignment"]
    assert ms.stats["calls"] >= 150


def test_analyzer_counts_and_flags_on_fake_records(tmp_path):
    A = _load("e4_scored_m4_analyze", "experiments/E4_scored_m4/analyze.py")
    import json
    rec = {"experiment": "E1-2", "sub_experiment": "E1-2", "trial_id": "U_s6100", "source_commit": "x",
           "validated_tilt_deg": 5.0, "magnet_stats": {"max_near_tilt_deg": 5.2}, "pass": False,
           "fail_reasons": ["rule 2"], "ok_magnet_validity": False,
           "per_move": [{"move": "U", "ok_all": True, "e16m_P_ok": True, "e16m_residual_J": 1e-5, "e16m_bound_J": 1e-4,
                         "magnet_dU_J": 1e-3, "misalignment": {"max_err_deg": 1.2}}]}
    (tmp_path / "r" / "E1-2").mkdir(parents=True)
    (tmp_path / "r" / "E1-2" / "U_s6100.json").write_text(json.dumps(rec))
    text = A.report(tmp_path / "r", tmp_path / "n")
    assert "| E1-2 | 1 / 24 | 0 | 5.20 | INCOMPLETE |" in text
    assert "NOT PASSED" in text and "E1-2/U_s6100: rule 2" in text


# ---- Amendment 1 / P-24: E1-6c categorical only, E1-6t toy-standard torque test -------------------------------------
def test_e16c_has_no_quantitative_threshold_and_runner_does_not_refuse():
    assert R.E16C_THRESHOLD is not None and R.E16C_THRESHOLD["quantity"] is None
    r = R.apply_m4_criteria({"pass": True, "magnet_stats": {"max_near_tilt_deg": 30.0}, "max_twist_deg": 40.0},
                            "E1-6c", 5.0, True)
    assert r["pass"] is True and r["rule3_label"] == "magnet model outside validated range"


def test_e16t_trials_are_16_corner_direction_pairs_with_unique_scored_seeds():
    t = R.trials("E1-6t")
    assert len(t) == 16
    assert {kw["peak_Nm"] for _, _, kw in t} == {0.45, -0.45}
    seeds = [kw["seed"] for _, _, kw in t]
    assert len(set(seeds)) == 16 and min(seeds) == 6640 and max(seeds) == 6655
    other = {kw["seed"] for e in ("E1-1", "E1-2", "E1-3", "E1-4", "E1-5", "E1-5s", "E1-6") for _, _, kw in R.trials(e)}
    assert not set(seeds) & other


def test_e16t_criterion_needs_solved_state_and_penetration_within_limit():
    base = {"pass": True, "magnet_stats": {"max_near_tilt_deg": 2.0}}
    ok = R.apply_m4_criteria({**base, "final_solved": True, "penetration_mm_reported_only": 0.4}, "E1-6t", 5.0, True)
    assert ok["pass"] is True and ok["ok_e16t"] is True
    deep = R.apply_m4_criteria({**base, "final_solved": True, "penetration_mm_reported_only": 0.6}, "E1-6t", 5.0, True)
    assert deep["pass"] is False and "E1-6t" in deep["fail_reasons"][0]
    moved = R.apply_m4_criteria({**base, "final_solved": False, "penetration_mm_reported_only": 0.1}, "E1-6t", 5.0,
                                True)
    assert moved["pass"] is False
