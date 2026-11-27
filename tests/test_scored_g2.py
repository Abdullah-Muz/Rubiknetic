"""Tests for the G2 runner (experiments/E8_scored_g2; pre-registration DRAFT).

Fast tests: job list, seeds, ledger/resume/manifest procedure with a synthetic runner, harness exceptions, refusals,
negative-test acceptance, sequence checks. One slow test builds the two-arm scene and checks that the controllers'
outputs do not depend on the cube's state (they read robot state only).
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
E8 = REPO / "experiments" / "E8_scored_g2"


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


R = _load("e8_run", E8 / "run.py")


@pytest.fixture(scope="module")
def T():
    return _load("trials", E8 / "trials.py")


# ---- job list ---------------------------------------------------------------------------------------------------------
def test_job_counts_and_seeds(T):
    jobs = R.build_jobs()
    by = {}
    for j in jobs:
        by[j["exp"]] = by.get(j["exp"], 0) + 1
    assert by == {"G2-1": 20, "G2-2": 40, "G2-3": 20, "G2-4": 40, "G2-6": 8, "G2-7": 10}
    seeds = [j["kw"]["seed"] for j in jobs]
    assert len(set(seeds)) == len(seeds)
    assert all(R.SCORED_SEEDS[0] <= s <= R.SCORED_SEEDS[1] for s in seeds)
    assert len({R.key_of(j) for j in jobs}) == len(jobs)
    assert sum(j["reported_only"] for j in jobs) == 8                  # only the G2-6 screen
    scored = [j for j in jobs if not j["reported_only"]]
    assert len([j for j in scored if j["exp"] in ("G2-1", "G2-2", "G2-3", "G2-4")]) == 120


def test_smoke_seeds_are_pilot_seeds():
    assert all(29000 <= j["kw"]["seed"] <= 29999 for j in R.smoke_jobs())


def test_random_sequences_deterministic_and_u_only(T):
    a, b = T.random_u_sequence(30320), T.random_u_sequence(30320)
    assert a == b and len(a.split()) == 10 and set(a.split()) <= {"U", "U'", "U2"}
    assert T.random_u_sequence(30321) != a


def test_start_draw_bounds(T):
    for s in range(30000, 30050):
        d = T.start_draw(s)
        assert all(abs(x) <= T.CUBE_TOL for x in d["cube_offset_m"])
        assert all(abs(v) <= T.MISALIGN_DEG for v in d["misalign_deg"].values())
    assert T.start_draw(30001) == T.start_draw(30001)


# ---- run procedure with a synthetic runner ----------------------------------------------------------------------------
def _jobs(n=4):
    return [R.job("G2-2", f"U_s{30100 + i}", "seq", {"seed": 30100 + i, "moves": "U"}) for i in range(n)]


def _fake_runner(j):
    return R.key_of(j), {"pass": True, "fail_reasons": [], "seed": j["kw"]["seed"], **R.metadata(j)}


ENV = {"mujoco": "4.0.1", "numpy": "2", "scipy": "1", "python": "3.12", "cpu": "x"}


def test_first_start_writes_manifest_records_ledger(tmp_path):
    out = tmp_path / "results"
    n = R.execute(out, _jobs(), "abc", ENV, "abc", 1, runner=_fake_runner, check_git=False, log=lambda s: None)
    assert n == 4
    assert (out / R.MANIFEST).exists() and len(R.read_lines(out / R.LEDGER)) == 4
    assert len(R.read_lines(out / R.STARTS)) == 1
    for line in R.read_lines(out / R.LEDGER):
        data = R.record_path(out, (line["exp"], line["tid"])).read_bytes()
        assert R._sha(data) == line["sha256"]


def test_interrupt_then_resume_completes(tmp_path):
    out = tmp_path / "results"
    with pytest.raises(R.Interrupted):
        R.execute(out, _jobs(), "abc", ENV, "abc", 1, runner=_fake_runner, stop_after=2, check_git=False,
                  log=lambda s: None)
    assert len(R.read_lines(out / R.LEDGER)) == 2
    n = R.execute(out, _jobs(), "abc", ENV, "abc", 1, runner=_fake_runner, check_git=False, log=lambda s: None)
    assert n == 2 and len(R.read_lines(out / R.LEDGER)) == 4 and len(R.read_lines(out / R.STARTS)) == 2


def test_resume_moves_orphans_and_reconciles(tmp_path):
    out = tmp_path / "results"
    with pytest.raises(R.Interrupted):
        R.execute(out, _jobs(), "abc", ENV, "abc", 1, runner=_fake_runner, stop_after=1, check_git=False,
                  log=lambda s: None)
    (out / "G2-2" / ".U_s30103.json.tmp").write_text("{}")                     # a killed write
    key = ("G2-2", "U_s30102")                                                 # a record without its ledger line
    R.record_path(out, key).write_text(json.dumps({"pass": True, "fail_reasons": []}))
    R.execute(out, _jobs(), "abc", ENV, "abc", 1, runner=_fake_runner, check_git=False, log=lambda s: None)
    starts = R.read_lines(out / R.STARTS)
    assert len(starts[1]["orphans"]) == 1 and len(starts[1]["reconciled"]) == 1
    assert (out / starts[1]["orphans"][0]["moved_to"]).exists()
    assert sum(x["reconciled"] for x in R.read_lines(out / R.LEDGER)) == 1


def test_resume_refuses_changed_trials_foreign_files_and_environment(tmp_path):
    out = tmp_path / "results"
    R.execute(out, _jobs(), "abc", ENV, "abc", 1, runner=_fake_runner, check_git=False, log=lambda s: None)
    with pytest.raises(SystemExit, match="trials differ"):
        R.execute(out, _jobs(3), "abc", ENV, "abc", 1, runner=_fake_runner, check_git=False, log=lambda s: None)
    with pytest.raises(SystemExit, match="environment field mujoco"):
        R.execute(out, _jobs(), "abc", {**ENV, "mujoco": "9"}, "abc", 1, runner=_fake_runner, check_git=False,
                  log=lambda s: None)
    (out / "G2-2" / "stray.json").write_text("{}")
    with pytest.raises(SystemExit, match="INVALID"):
        R.execute(out, _jobs(), "abc", ENV, "abc", 1, runner=_fake_runner, check_git=False, log=lambda s: None)


def test_first_start_refuses_nonempty_folder(tmp_path):
    out = tmp_path / "results"
    out.mkdir()
    (out / "x.json").write_text("{}")
    with pytest.raises(SystemExit, match="not empty"):
        R.execute(out, _jobs(), "abc", ENV, "abc", 1, runner=_fake_runner, check_git=False, log=lambda s: None)


def test_record_never_overwritten(tmp_path):
    out = tmp_path / "results"
    R.write_record(out, ("G2-2", "U_s1"), {"pass": True}, 1)
    with pytest.raises(FileExistsError):
        R.write_record(out, ("G2-2", "U_s1"), {"pass": False}, 1)


# ---- harness exceptions and interruptions ----------------------------------------------------------------------------
def _fake_trials(exc: BaseException):
    m = types.ModuleType("trials")

    class Refused(Exception):
        pass

    def run_trial(kind, kw):
        raise exc
    m.Refused, m.run_trial = Refused, run_trial
    return m


def test_harness_exception_is_a_failing_record(monkeypatch):
    monkeypatch.setitem(sys.modules, "trials", _fake_trials(ValueError("boom")))
    key, rec = R.run_job(_jobs(1)[0])
    assert rec["pass"] is False and "harness exception: ValueError: boom" in rec["fail_reasons"][0]
    assert "Traceback" in rec["harness_exception"] and rec["trial_id"] == "U_s30100"


def test_interruptions_propagate(monkeypatch):
    for exc in (MemoryError(), OSError("disk")):
        monkeypatch.setitem(sys.modules, "trials", _fake_trials(exc))
        with pytest.raises(type(exc)):
            R.run_job(_jobs(1)[0])
    ft = _fake_trials(None)
    ft.run_trial = lambda kind, kw: (_ for _ in ()).throw(ft.Refused("no V3 record"))
    monkeypatch.setitem(sys.modules, "trials", ft)
    with pytest.raises(ft.Refused):
        R.run_job(_jobs(1)[0])


def test_execute_turns_runner_errors_into_interrupted(tmp_path):
    def bad(j):
        raise OSError("transient read")
    with pytest.raises(R.Interrupted, match="OSError"):
        R.execute(tmp_path / "r", _jobs(), "abc", ENV, "abc", 1, runner=bad, check_git=False, log=lambda s: None)


def test_scored_start_refused_until_frozen():
    assert R.FROZEN is False
    with pytest.raises(SystemExit, match="not frozen"):
        R.main(["all"])


def test_smoke_dir_may_not_be_the_scored_folder():
    with pytest.raises(SystemExit, match="scored folder"):
        R.main(["smoke", "--smoke-dir", str(R.OUT)])


# ---- trial-level logic ------------------------------------------------------------------------------------------------
def _pm(**kw):
    base = {"move": "U", "ok_oracle": True, "ok_turn_error": True, "ok_all": True, "jam_stop": None,
            "core_slip_mm": 0.1}
    return {**base, **kw}


def test_seq_reasons(T):
    good = {"t0_solved": True, "per_move": [_pm()], "final_matches_oracle": True, "audit_violations": [],
            "numerical_failures": []}
    assert T._seq_reasons(good, 1) == []
    assert T._seq_reasons({**good, "per_move": [_pm(ok_turn_error=False)]}, 1)
    assert T._seq_reasons({**good, "per_move": [_pm(jam_stop={"by": "ft"})]}, 1)
    assert T._seq_reasons({**good, "per_move": [_pm(core_slip_mm=T.MOVE_SLIP_MM + 0.01)]}, 1)
    assert T._seq_reasons({**good, "per_move": []}, 1)
    assert T._seq_reasons({**good, "aborted": "NumericalFailure: x"}, 1)
    assert T._seq_reasons({**good, "final_matches_oracle": False}, 1)


def test_neg_outcomes(T):
    clean = {"per_move": [_pm()], "fail_reasons": []}
    assert T.neg_outcome("two_layer", clean)[0] is False                    # a clean pass is not detection
    assert T.neg_outcome("two_layer", {**clean, "fail_reasons": ["x"]})[0] is True
    assert T.neg_outcome("open_midturn", {"per_move": [_pm(jam_stop={"by": "ft"})], "fail_reasons": ["x"]})[0]
    assert T.neg_outcome("jam", {"per_move": [_pm(jam_stop={"by": "ft"}, core_slip_mm=0.1)]})[0] is True
    assert T.neg_outcome("jam", {"per_move": [_pm(jam_stop={"by": "ft"}, core_slip_mm=2.0)]})[0] is False
    assert T.neg_outcome("jam", clean)[0] is False
    assert T.neg_outcome("collision", {"per_move": [_pm(arm_arm_max=3)]})[0] is True
    assert T.neg_outcome("collision", {"per_move": [_pm(arm_arm_max=0, robot_cube_nonpad_max=0)]})[0] is False
    assert T.neg_outcome("offcentre", clean)[0] is True


# ---- the controllers read robot state only (slow: builds the scene) ----------------------------------------------------
# slow (~1 min): builds the two-arm scene
def test_controllers_ignore_cube_state(T):
    import mujoco
    T.configure({}, T.start_draw(29001))
    r = T.TA.TwoArm(T.L, T.HC, T.GRIP)
    try:
        m, d = r.m, r.d
        r.integ = False                                  # no integrator update between the two evaluations
        r.j7 = [r.roll0 + 0.3, 0.5, 1.0]
        robot_q = set(np.concatenate([r.qA, r.qB]).tolist())

        def outputs():
            r.impedance()
            r.j7_control()
            return d.ctrl[r.aB].copy()
        mujoco.mj_forward(m, d)
        before = outputs()
        core = m.body("core").id                         # the cube: the core and every cubie (rooted at the core)
        cube_j = [j for j in range(m.njnt) if m.body_rootid[m.jnt_bodyid[j]] == core]
        assert len(cube_j) >= 21                         # free core + cubie joints
        cube_q = sorted({a for j in cube_j for a in range(m.jnt_qposadr[j], m.jnt_qposadr[j] + (
            7 if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_FREE else 4 if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_BALL
            else 1))})
        cube_v = sorted({a for j in cube_j for a in range(m.jnt_dofadr[j], m.jnt_dofadr[j] + (
            6 if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_FREE else 3 if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_BALL
            else 1))})
        q0, v0 = d.qpos.copy(), d.qvel.copy()
        rng = np.random.default_rng(0)
        d.qpos[cube_q] += rng.normal(0.0, 0.05, len(cube_q))   # scramble the cube's state (not the robots')
        d.qvel[cube_v] += rng.normal(0.0, 0.5, len(cube_v))
        mujoco.mj_forward(m, d)
        after = outputs()
        assert np.allclose(before, after, atol=1e-9, rtol=0)
        # sanity: the same comparison does see a change in arm B's own state
        d.qpos[:], d.qvel[:] = q0, v0
        d.qpos[r.qB[2]] += 0.01
        mujoco.mj_forward(m, d)
        assert not np.allclose(before, outputs(), atol=1e-6, rtol=0)
    finally:
        T.MagnetSystem.uninstall()
