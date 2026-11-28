"""Tests for the G2 runner (experiments/E8_scored_g2; pre-registration revision 6, DRAFT).

Fast tests: job list, seeds, run procedure with a synthetic runner (manifest, ledger, resume, tampering), harness
exceptions, refusals, criteria, negative-case acceptance, the independent verdict recomputation, frozen-path coverage.
Slow tests (~1-2 min each) build the two-arm scene: the controllers' outputs and the roll command sequence do not
depend on the cube's state.
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
# The scene-building tests need the generated robot model, which is git-ignored (third_party_cad/, GrabCAD terms), so
# they are skipped on a clean clone such as CI. The freeze evidence requires them to RUN locally (0 skipped, §7).
ROBOT_XML = REPO / "third_party_cad" / "robot" / "generated" / "xarm7_g2_1305+.xml"
NEEDS_SCENE = pytest.mark.skipif(not ROBOT_XML.exists(), reason="git-ignored robot model absent (clean clone, e.g. CI)")
A = _load("e8_analyze", E8 / "analyze.py")


@pytest.fixture(scope="module")
def T():
    return _load("trials", E8 / "trials.py")


# ---- job list ---------------------------------------------------------------------------------------------------------
def test_job_counts_and_seeds(T):
    jobs = R.build_jobs()
    by = {}
    for j in jobs:
        by[j["exp"]] = by.get(j["exp"], 0) + 1
    assert by == {"G2-1": 20, "G2-2": 40, "G2-3": 20, "G2-4": 40, "G2-6": 8, "G2-7": 10} and len(jobs) == 138
    seeds = [j["kw"]["seed"] for j in jobs]
    assert len(set(seeds)) == len(seeds) and all(R.SCORED_SEEDS[0] <= s <= R.SCORED_SEEDS[1] for s in seeds)
    assert len({R.key_of(j) for j in jobs}) == len(jobs)
    ro = [j for j in jobs if j["reported_only"]]
    assert {j["exp"] for j in ro} == {"G2-6", "G2-7"} and len(ro) == 10          # 8 screen + 2 offcentre
    assert all(j["kw"]["case"] == "offcentre" for j in ro if j["exp"] == "G2-7")
    assert len(jobs) - len(ro) == 128


def test_smoke_and_pilot_seeds_are_pilot_seeds():
    jobs = R.smoke_jobs() + R.pilot_jobs() + R.pilot2_jobs() + R.pilot3_jobs() + R.pilot4_jobs()
    assert all(29000 <= j["kw"]["seed"] <= 29999 for j in jobs)
    p4 = [j["kw"]["seed"] for j in R.pilot4_jobs()]                  # P-131: new seeds, unique, none reused
    old = {j["kw"]["seed"] for j in R.pilot_jobs() + R.pilot2_jobs() + R.pilot3_jobs()}
    assert len(p4) == len(set(p4)) == 144 and not set(p4) & old and min(p4) >= 29500


def test_random_sequences_and_start_draw(T):
    a = T.random_u_sequence(30320)
    assert a == T.random_u_sequence(30320) and len(a.split()) == 10 and set(a.split()) <= {"U", "U'", "U2"}
    for s in range(30000, 30050):
        d = T.start_draw(s)
        assert all(abs(x) <= T.CUBE_TOL for x in d["cube_offset_m"])
        assert all(abs(v) <= T.MISALIGN_DEG for v in d["misalign_deg"].values())


def test_limits_agree_between_trials_and_analyze(T):
    L = A.LIMITS
    assert L["move_slip_mm"] == T.MOVE_SLIP_MM and L["pen_mm"] == T.PEN_MM
    assert (L["hold_slip_mm"], L["hold_rot_deg"]) == (T.HOLD_SLIP_MM, T.HOLD_ROT_DEG)
    assert (L["total_slip_mm"], L["total_rot_deg"]) == (T.TOTAL_SLIP_MM, T.TOTAL_ROT_DEG)
    assert L["residual_end_deg"] == T.RESIDUAL_END_MAX_DEG and L["jam_slip_mm"] == T.JAM_SLIP_MM
    assert T.FT_STOP == 1.0                                       # P-125
    assert L["magnet_tilt_deg"] == T.MAGNET_TILT_MAX_DEG == T.TA.H.M4.nominal_validated_tilt()   # review 5 S1
    assert A.DT == T.SIM_DT == 0.0005                            # review 5 S4 (the scene's timestep: real-scene test)
    assert L["pen_mm"] == T.TA.T["penetration_mm"]                # review 2 S10
    assert (L["drop_shift_mm"], L["t0_offset_mm"]) == (T.DROP_SHIFT_MM, T.T0_OFFSET_MM)
    assert tuple(L["jam_roll_deg"]) == T.JAM_ROLL_DEG and L["move_rot_deg"] == T.TA.CORE_ROT_MOVE_DEG
    th = T.TA.T
    assert (L["turn_error_deg"], L["drift_deg"], L["rollback_deg"]) == (th["turn_error_deg"], th["nontarget_drift_deg"],
                                                                         th["nontarget_drift_deg"])


def _frozen(f: str) -> bool:
    import fnmatch
    return any(f == p or f.startswith(p.rstrip("/") + "/") or fnmatch.fnmatch(f, p) for p in R.FROZEN_PATHS)


def test_frozen_paths_cover_every_loaded_module(tmp_path):
    """Review 1 item 5: every repository module in sys.modules after a fresh process loads `trials` is frozen. A fresh
    process, not pytest's (which imports every test file, and on CI keeps its virtualenv inside the checkout)."""
    import subprocess
    probe = tmp_path / "mods.py"
    probe.write_text("import importlib.util, json, sys\n"
                     "s = importlib.util.spec_from_file_location('trials', sys.argv[1])\n"
                     "T = importlib.util.module_from_spec(s); sys.modules['trials'] = T; s.loader.exec_module(T)\n"
                     "print('MODS' + json.dumps(sorted({m.__file__ for m in list(sys.modules.values())"
                     " if getattr(m, '__file__', None)})))\n")
    out = subprocess.run([sys.executable, str(probe), str(E8 / "trials.py")], capture_output=True, text=True,
                         timeout=600, cwd=str(tmp_path))
    assert out.returncode == 0, out.stderr[-3000:]
    files = {Path(f).resolve() for f in json.loads(out.stdout.split("MODS", 1)[1])}
    repo_files = sorted(str(f.relative_to(REPO)).replace("\\", "/") for f in files if f.is_relative_to(REPO)
                        and not ({".venv", "venv", "site-packages"} & set(f.relative_to(REPO).parts)))
    assert "experiments/D18_two_arm_m7/two_arm.py" in repo_files
    missing = [f for f in repo_files if not _frozen(f)]
    assert not missing, missing


_OPEN_PROBE = r"""
import importlib.util, json, sys
from pathlib import Path
opened = set()
def hook(event, args):
    if event == "open" and isinstance(args[0], (str, bytes)) or event == "open" and hasattr(args[0], "__fspath__"):
        p = args[0].decode() if isinstance(args[0], bytes) else str(args[0])
        opened.add(p)
sys.addaudithook(hook)
spec = importlib.util.spec_from_file_location("trials", sys.argv[1])
T = importlib.util.module_from_spec(spec); sys.modules["trials"] = T; spec.loader.exec_module(T)
T.reset_phase()
T.configure({}, T.start_draw(29001))
r = T.TA.TwoArm(T.L, T.HC, T.DEFAULTS["grip"])          # builds the model and runs the start sequence
assert T.simulation_started()
T.MagnetSystem.uninstall()
print("OPENED" + json.dumps(sorted(opened)))
"""


@NEEDS_SCENE
def test_every_repository_file_a_trial_opens_is_frozen_or_an_artifact(T, tmp_path):
    """Review 3 item 2: records every file opened (Python `open` audit events, which include imports through
    spec_from_file_location) while a fresh process imports `trials`, builds the scene and runs the start sequence.
    Every repository .py file must be frozen; every other repository file must be frozen or a hashed artifact."""
    import subprocess
    probe = tmp_path / "probe.py"
    probe.write_text(_OPEN_PROBE)
    out = subprocess.run([sys.executable, str(probe), str(E8 / "trials.py")], capture_output=True, text=True,
                         timeout=900, cwd=str(tmp_path))
    assert out.returncode == 0, out.stderr[-3000:]
    opened = json.loads(out.stdout.split("OPENED", 1)[1])
    arts = {k.replace("\\", "/") for k in R.artifacts()}
    seen, missing = set(), []
    for p in opened:
        f = Path(p)
        if not f.is_absolute():
            f = tmp_path / f
        f = f.resolve()
        if f.parent.name == "__pycache__" and f.suffix == ".pyc":
            f = f.parent.parent / (f.name.split(".")[0] + ".py")
        if not f.is_relative_to(REPO):
            continue
        rel = str(f.relative_to(REPO)).replace("\\", "/")
        seen.add(rel)
        if not (_frozen(rel) or rel in arts):
            missing.append(rel)
    assert "experiments/E1_scored/run.py" in seen                     # the review-3 case is visible to this test
    assert "experiments/D18_two_arm_m7/two_arm.py" in seen
    assert not missing, missing


# ---- run procedure with a synthetic runner ----------------------------------------------------------------------------
def _jobs(n=4):
    return [R.job("G2-2", f"U_s{30100 + i}", "seq", {"seed": 30100 + i, "moves": "U"}) for i in range(n)]


def _fake_runner(j):
    return R.key_of(j), {"pass": True, "fail_reasons": [], **R.metadata(j)}


ENV = {"mujoco": "4.0.1", "numpy": "2", "scipy": "1", "python": "3.12", "cpu": "x"}
ARTS = {"a.xml": "00"}


def _ex(out, jobs=None, runner=_fake_runner, **kw):
    return R.execute(out, jobs or _jobs(), "abc", ENV, "abc", 1, runner=runner, check_git=False, log=lambda s: None,
                     arts=ARTS, **kw)


def test_first_start_writes_manifest_records_ledger(tmp_path):
    out = tmp_path / "results"
    assert _ex(out) == 4
    man = json.loads((out / R.MANIFEST).read_text())
    assert man["artifacts"] == ARTS and len(R.read_lines(out / R.LEDGER)) == 4
    for line in R.read_lines(out / R.LEDGER):
        assert R._sha(R.record_path(out, (line["exp"], line["tid"])).read_bytes()) == line["sha256"]


def test_interrupt_then_resume_completes(tmp_path):
    out = tmp_path / "results"
    with pytest.raises(R.Interrupted):
        _ex(out, stop_after=2)
    assert _ex(out) == 2 and len(R.read_lines(out / R.LEDGER)) == 4 and len(R.read_lines(out / R.STARTS)) == 2


def test_resumes_are_limited_then_not_passed(tmp_path):
    """Review 3 S5: the first start and at most 5 resumes; an incomplete run after them is NOT PASSED."""
    assert R.MAX_STARTS == A.MAX_STARTS == 6
    out = tmp_path / "results"
    jobs = _jobs()
    for j in jobs:
        j["scored"], j["smoke"] = True, False

    def bad(j):
        raise OSError("persistent load error")
    for _ in range(R.MAX_STARTS):
        with pytest.raises(R.Interrupted):
            _ex(out, jobs, runner=bad)
    with pytest.raises(SystemExit, match="5 resumes"):
        _ex(out, jobs)
    assert len(R.read_lines(out / R.STARTS)) == 6
    res = _verdict(out)
    assert res["status"] == "NOT PASSED" and "not passed" in res["problems"][-1]


def test_resume_moves_orphans_and_reconciles(tmp_path):
    out = tmp_path / "results"
    with pytest.raises(R.Interrupted):
        _ex(out, stop_after=1)
    (out / "G2-2" / ".U_s30103.json.tmp").write_text("{}")
    R.record_path(out, ("G2-2", "U_s30102")).write_text(json.dumps({"pass": True, "fail_reasons": []}))
    _ex(out)
    starts = R.read_lines(out / R.STARTS)
    assert len(starts[1]["orphans"]) == 1 and len(starts[1]["reconciled"]) == 1
    assert (out / starts[1]["orphans"][0]["moved_to"]).exists()


def test_resume_refusals(tmp_path):
    out = tmp_path / "results"
    _ex(out)
    with pytest.raises(SystemExit, match="trials differ"):
        _ex(out, _jobs(3))
    with pytest.raises(SystemExit, match="environment field mujoco"):
        R.execute(out, _jobs(), "abc", {**ENV, "mujoco": "9"}, "abc", 1, runner=_fake_runner, check_git=False,
                  log=lambda s: None, arts=ARTS)
    with pytest.raises(SystemExit, match="artifact SHA-256s differ"):
        R.execute(out, _jobs(), "abc", ENV, "abc", 1, runner=_fake_runner, check_git=False, log=lambda s: None,
                  arts={"a.xml": "11"})
    R.record_path(out, ("G2-2", "U_s30101")).unlink()            # a deleted record (review 1 item 4 b)
    with pytest.raises(SystemExit, match="has no record"):
        _ex(out)


def test_resume_refuses_stray_temporary_files(tmp_path):
    """Review 2 item 4: only <exp>/.<tid>.json.tmp of a manifest trial is an in-flight file."""
    for name in (".x.json.tmp", "foo.json.tmp"):
        out = tmp_path / name / "results"
        _ex(out)
        (out / name).write_text("{}")
        with pytest.raises(SystemExit, match="INVALID"):
            _ex(out)
    out = tmp_path / "unknown_tid" / "results"
    _ex(out)
    (out / "G2-2" / ".U_s99999.json.tmp").write_text("{}")
    with pytest.raises(SystemExit, match="INVALID"):
        _ex(out)


def test_verdict_checks_frozen_code_against_the_manifest(monkeypatch):
    """Review 2 S5: the verdict refuses to pass unless the frozen paths at HEAD equal the manifest commit's."""
    calls = []

    def fake_git(*args):
        calls.append(args)
        return "experiments/E8_scored_g2/analyze.py" if args[0] == "diff" else ""
    monkeypatch.setattr(A.R, "_git", fake_git)                    # analyze's own copy of the run module
    probs = A.code_problems({"commit": "abc", "frozen_paths": ["x"]})
    assert probs and "differ" in probs[0] and calls[0][:2] == ("diff", "--name-only")


def test_resume_refuses_unknown_directory(tmp_path):
    out = tmp_path / "results"
    _ex(out)
    (out / "G2-9").mkdir()                                       # even empty (review 1 item 4 d)
    with pytest.raises(SystemExit, match="directory not in the manifest"):
        _ex(out)


def test_first_start_refuses_nonempty_folder(tmp_path):
    out = tmp_path / "results"
    out.mkdir()
    (out / "x.json").write_text("{}")
    with pytest.raises(SystemExit, match="not empty"):
        _ex(out)


def test_record_never_overwritten(tmp_path):
    out = tmp_path / "results"
    R.write_record(out, ("G2-2", "U_s1"), {"pass": True}, 1)
    with pytest.raises(FileExistsError):
        R.write_record(out, ("G2-2", "U_s1"), {"pass": False}, 1)


# ---- harness exceptions and interruptions ----------------------------------------------------------------------------
def _fake_trials(exc: BaseException, started: bool = True):
    """A stand-in `trials` module. `started`: whether run_trial takes its first control step before raising."""
    m = types.ModuleType("trials")

    class Refused(Exception):
        pass

    def run_trial(kind, kw):
        m.started = started
        raise exc

    def reset_phase():
        m.started = False
    m.Refused, m.run_trial, m.reset_phase, m.simulation_started = Refused, run_trial, reset_phase, lambda: m.started
    m.started = False
    return m


def test_harness_exception_is_a_failing_record(monkeypatch):
    monkeypatch.setitem(sys.modules, "trials", _fake_trials(ValueError("boom")))
    key, rec = R.run_job(_jobs(1)[0])
    assert rec["pass"] is False and "harness exception: ValueError: boom" in rec["fail_reasons"][0]
    assert "Traceback" in rec["harness_exception"]


def test_interruptions_propagate(monkeypatch):
    for exc in (MemoryError(), OSError("disk")):                       # after the first step: an interruption
        monkeypatch.setitem(sys.modules, "trials", _fake_trials(exc))
        with pytest.raises(type(exc)):
            R.run_job(_jobs(1)[0])
    ft = _fake_trials(None)
    ft.run_trial = lambda kind, kw: (_ for _ in ()).throw(ft.Refused("no V3 record"))
    monkeypatch.setitem(sys.modules, "trials", ft)
    monkeypatch.setattr(R.time, "sleep", lambda s: None)
    with pytest.raises(OSError, match="model load failed"):            # retried, then an interruption (P-127)
        R.run_job(_jobs(1)[0])


LOAD_ERRORS = [                                    # review 3 item 1: what an empty file gives in each loader
    ValueError("Error: stl_decoder: STL file 'x.stl' is empty"),
    ValueError("ParseXML: empty file '/mnt/c/dev/Rubiknetic/third_party_cad/robot/generated/xarm7_g2_1305+.xml'"),
    json.JSONDecodeError("Expecting value", "", 0),
    EOFError("No data left in file"),
    FileNotFoundError("[Errno 2] No such file or directory: 'x.npz'"),
    RuntimeError("an unexpected message"),
]


@pytest.mark.parametrize("err", LOAD_ERRORS, ids=lambda e: type(e).__name__)
def test_errors_before_the_first_step_are_retried_then_interrupt(monkeypatch, err):
    """P-127, review 3 item 1: any exception before the first control step is a load error, whatever its message:
    retried, and a persistent one interrupts the run (never a failed record)."""
    calls = {"n": 0}
    ft = _fake_trials(None)

    def flaky(kind, kw):
        calls["n"] += 1
        if calls["n"] < 3:
            raise err                                   # before the first step (the flag is never set)
        ft.started = True
        return {"pass": True, "fail_reasons": []}
    ft.run_trial = flaky
    monkeypatch.setitem(sys.modules, "trials", ft)
    monkeypatch.setattr(R.time, "sleep", lambda s: None)
    key, rec = R.run_job(_jobs(1)[0])
    assert rec["pass"] is True and len(rec["load_retries"]) == 2 and calls["n"] == 3
    ft2 = _fake_trials(err, started=False)
    monkeypatch.setitem(sys.modules, "trials", ft2)
    with pytest.raises(OSError, match="model load failed 3 times"):
        R.run_job(_jobs(1)[0])


def test_errors_after_the_first_step_are_failing_records(monkeypatch):
    """Review 3 item 1: after the first step, even a load-like message is a failing record, and is not retried."""
    for err in (ValueError("STL file 'x.stl' is empty"), EOFError("No data left in file"), ValueError("a genuine bug")):
        ft = _fake_trials(err, started=True)
        calls = {"n": 0}
        inner = ft.run_trial

        def counted(kind, kw, inner=inner, calls=calls):
            calls["n"] += 1
            return inner(kind, kw)
        ft.run_trial = counted
        monkeypatch.setitem(sys.modules, "trials", ft)
        key, rec = R.run_job(_jobs(1)[0])
        assert rec["pass"] is False and str(err) in rec["fail_reasons"][0] and calls["n"] == 1
        assert rec["load_retries"] == []


@NEEDS_SCENE
def test_phase_flag_and_magnets_in_the_real_scene(T):
    """The real phase flag: reset_phase clears it; constructing the scene (start sequence) sets it.
    P-130 (review 4 N1): the L0 magnets act at every step of the start sequence; positive control: with the passive
    callback removed, the counter reports the steps without magnet force."""
    import mujoco
    T.reset_phase()
    assert not T.simulation_started()
    T.configure({}, T.start_draw(29001))
    r = T.TA.TwoArm(T.L, T.HC, T.DEFAULTS["grip"])
    try:
        assert T.simulation_started() and r.d.time > 0
        assert mujoco.get_mjcb_passive() is not None
        st = r.magnet_stats()
        assert st["steps"] >= 7000 and st["steps_without_magnet_force"] == 0 and st["force_evaluations"] >= st["steps"]
        assert st["sim_steps"] == st["steps"] == round(r.d.time / r.m.opt.timestep)               # review 5 S4
        assert r.m.opt.timestep == T.SIM_DT
        assert 0.0 < st["max_near_tilt_deg"] < T.MAGNET_TILT_MAX_DEG and st["near_perpendicular"] == 0  # review 5 S1
        T.MagnetSystem.uninstall()
        r.ctrl_step(5)
        assert r.magnet_stats()["steps_without_magnet_force"] == 5
    finally:
        T.MagnetSystem.uninstall()


def test_execute_turns_runner_errors_into_interrupted(tmp_path):
    def bad(j):
        raise OSError("transient read")
    with pytest.raises(R.Interrupted, match="OSError"):
        _ex(tmp_path / "r", runner=bad)


def test_scored_start_refused_until_frozen(monkeypatch):
    monkeypatch.setattr(R, "FROZEN", False)                       # independent of the committed flag (review 1 item 7)
    with pytest.raises(SystemExit, match="not frozen"):
        R.main(["all"])


def test_smoke_dir_may_not_be_the_scored_folder():
    with pytest.raises(SystemExit, match="scored folder"):
        R.main(["smoke", "--smoke-dir", str(R.OUT)])


# ---- synthetic records for the criteria -----------------------------------------------------------------------------
AUDIT = {"actuators_on_cube": [], "equalities_on_cube": [], "tendons_on_cube": [], "gravcomp_on_cube": [],
         "n_cube_bodies": 27}
START = {"contacts": {}, "stand_drop_shift_mm": 0.1, "core_offset_from_nominal_mm": 1.0}
MAGNETS = {"steps": 100000, "steps_without_magnet_force": 0, "force_evaluations": 100003,       # P-130
           "sim_steps": 100000, "max_near_tilt_deg": 1.5, "near_perpendicular": 0, "clamped_z": 0}  # review 5


def _pm(**kw):
    base = {"move": "U", "observed_move": "U", "turn_error_deg": 0.3, "nontarget_drift_deg": 0.2,
            "pen_cubie_mm": 0.1, "t_tip_force_s": 1.0, "t_layer_motion_rel_core_s": 1.01, "robot_cube_nonpad_max": 0,
            "arm_arm_max": 0, "robot_table_max": 0, "robot_stand_max": 0, "robot_block_max": 0, "cube_stand_max": 0,
            "drive_impulse_Nms": 0.05, "rollback_rot_deg": 0.1, "rollback_state_unchanged": True,
            "core_rot_deg": 0.3, "core_slip_mm": 0.1, "jam_stop": None,
            "ok_oracle": True, "ok_turn_error": True, "ok_drift": True, "ok_penetration_cubie": True, "ok_causal": True,
            "ok_no_nonpad_cube_contact": True, "ok_no_arm_arm": True, "ok_no_table": True, "ok_no_stand_block": True,
            "ok_drive": True, "ok_rollback": True, "ok_core_rot": True, "ok_all": True}
    return {**base, **kw}


def _rec(pms=None, **kw):
    base = {"t0_solved": True, "per_move": pms if pms is not None else [_pm()], "final_matches_oracle": True,
            "sim_time_s": 50.0,
            "audit_violations": [], "numerical_failures": [], "start": dict(START),
            "approach": {"pen_cubie": 0.02}, "trial": {"core_slip_total_mm": 0.2, "core_rot_total_deg": 0.3,
                                                     "residual_t0_deg": [0.5] * 26, "residual_end_deg": [0.6] * 26,
                                                     "model_audit": AUDIT, "magnets": dict(MAGNETS)}}
    return {**base, **kw}


def test_seq_reasons_and_recompute_agree(T):
    cases = [
        (_rec(), True),
        (_rec([_pm(ok_turn_error=False, turn_error_deg=2.5)]), False),
        (_rec([_pm(jam_stop={"by": "ft"})]), False),
        (_rec([_pm(core_slip_mm=1.01)]), False),
        (_rec([_pm(ok_core_rot=False, core_rot_deg=2.1)]), False),
        (_rec([_pm(ok_rollback=False, rollback_rot_deg=1.5)]), False),
        (_rec([_pm(ok_drive=False, drive_impulse_Nms=-0.01)]), False),
        (_rec([]), False),
        (_rec(aborted="NumericalFailure: x"), False),
        (_rec(final_matches_oracle=False), False),
        (_rec(approach={"arm_arm": 2}), False),
        (_rec(approach={"cube_stand": 1}), False),
        (_rec(start={**START, "contacts": {"robot_cube_nonpad": 1}}), False),
        (_rec(start={**START, "stand_drop_shift_mm": 1.1}), False),           # review 2 S6
        (_rec(start={**START, "core_offset_from_nominal_mm": 3.1}), False),
        (_rec(trial={**_rec()["trial"], "model_audit": {**AUDIT, "gravcomp_on_cube": [5]}}), False),
        (_rec(trial={**_rec()["trial"], "core_slip_total_mm": 2.1}), False),
        (_rec(trial={**_rec()["trial"], "residual_end_deg": [0.5] * 25 + [1.6]}), True),     # growth alone is fine
        (_rec(trial={**_rec()["trial"], "residual_end_deg": [0.5] * 25 + [4.1]}), False),    # P-125: absolute 4 deg
        (_rec(trial={**_rec()["trial"], "model_audit": {**AUDIT, "actuators_on_cube": ["x"]}}), False),
        (_rec(trial={**_rec()["trial"], "magnets": {**MAGNETS, "steps_without_magnet_force": 1}}), False),  # P-130
        (_rec(trial={**_rec()["trial"], "magnets": {**MAGNETS, "steps": 0}}), False),
        (_rec(trial={k: v for k, v in _rec()["trial"].items() if k != "magnets"}), False),
        (_rec(trial={**_rec()["trial"], "magnets": {**MAGNETS, "sim_steps": 99999}}), False),          # review 5 S4
        (_rec(sim_time_s=50.001), False),
        (_rec(trial={**_rec()["trial"], "magnets": {**MAGNETS, "max_near_tilt_deg": 5.01}}), False),  # review 5 S1
        (_rec(trial={**_rec()["trial"], "magnets": {**MAGNETS, "max_near_tilt_deg": 4.99}}), True),
        (_rec(trial={**_rec()["trial"], "magnets": {**MAGNETS, "near_perpendicular": 1}}), False),
    ]
    for rec, ok in cases:
        assert (not T._seq_reasons(rec, 1)) is ok
        assert (not A.recompute_seq(rec, "U")) is ok


def test_neg_outcomes_revision2(T):
    clean = _rec()
    for case in ("two_layer", "open_midturn", "jam"):
        assert T.neg_outcome(case, clean)[0] is False and A.recompute_neg(clean, case) is False
    aborted = _rec([_pm(ok_oracle=False, observed_move=None)], aborted="NumericalFailure: x")
    for case in ("two_layer", "open_midturn", "offcentre", "collision", "jam"):
        assert T.neg_outcome(case, aborted)[0] is False and A.recompute_neg(aborted, case) is False   # review 1 item 3
    det = _rec([_pm(ok_oracle=False, observed_move=None, ok_turn_error=False, turn_error_deg=80.0)])
    assert T.neg_outcome("two_layer", det)[0] and A.recompute_neg(det, "two_layer")
    assert T.neg_outcome("open_midturn", det)[0] and A.recompute_neg(det, "open_midturn")
    jam_ok = _rec([_pm(jam_stop={"by": "ft", "roll_done_deg": -33.0}, ok_turn_error=False, turn_error_deg=57.0)])
    assert T.neg_outcome("jam", jam_ok)[0] and A.recompute_neg(jam_ok, "jam")
    jam_early = _rec([_pm(jam_stop={"by": "ft", "roll_done_deg": -5.0})])
    assert not T.neg_outcome("jam", jam_early)[0] and not A.recompute_neg(jam_early, "jam")
    jam_shift = _rec([_pm(jam_stop={"by": "ft", "roll_done_deg": -33.0}, core_slip_mm=0.6)])
    assert not T.neg_outcome("jam", jam_shift)[0] and not A.recompute_neg(jam_shift, "jam")
    hit = _rec([_pm(arm_arm_max=3)])
    assert T.neg_outcome("collision", hit)[0] and A.recompute_neg(hit, "collision")
    assert not T.neg_outcome("collision", clean)[0] and not A.recompute_neg(clean, "collision")
    assert T.neg_outcome("offcentre", clean) == (True, "clean")
    tilted = _rec([_pm(jam_stop={"by": "ft", "roll_done_deg": -33.0}, ok_turn_error=False, turn_error_deg=57.0)],
                  trial={**_rec()["trial"], "magnets": {**MAGNETS, "max_near_tilt_deg": 7.0}})
    assert T.neg_outcome("jam", tilted)[0] and A.recompute_neg(tilted, "jam")    # review 5 S1: negatives label only


# ---- verdict script --------------------------------------------------------------------------------------------------
def _run(tmp, runner=_fake_runner, jobs=None):
    out = tmp / "results"
    jobs = jobs or _jobs()
    for j in jobs:
        j["scored"], j["smoke"] = True, False
    _ex(out, jobs, runner)
    return out


def _verdict(out, jobs=None):
    return A.verdict(out, "scored", check_artifacts=False, expected=jobs or _jobs(),
                     recompute_fn=lambda rec, t: bool(rec.get("pass")), check_code=False)


def test_verdict_pass_fail_incomplete(tmp_path):
    assert _verdict(_run(tmp_path / "a"))["status"] == "PASS"

    def one_fails(j):
        k, r = _fake_runner(j)
        if j["kw"]["seed"] == 30101:
            r.update({"pass": False, "fail_reasons": ["move 1 U: ok_drift"]})
        return k, r
    res = _verdict(_run(tmp_path / "b", one_fails))
    assert res["status"] == "NOT PASSED" and list(res["failed"]) == ["G2-2/U_s30101"]
    out = tmp_path / "c" / "results"
    jobs = _jobs()
    for j in jobs:
        j["scored"], j["smoke"] = True, False
    with pytest.raises(R.Interrupted):
        _ex(out, jobs, stop_after=2)
    assert _verdict(out)["status"] == "INCOMPLETE"


@pytest.mark.parametrize("tamper", ["edit", "extra_file", "orphan_tmp_subfolder", "duplicate_ledger", "deleted_rerun",
                                    "extra_dir", "metadata", "list", "root_tmp", "root_tmp_plain",
                                    "interrupted_unlogged", "starts_emptied", "deleted_with_ledger_line"])
def test_verdict_invalid_cases(tmp_path, tamper):
    out = _run(tmp_path)
    jobs = None
    if tamper == "edit":
        p = R.record_path(out, ("G2-2", "U_s30100"))
        p.write_text(p.read_text().replace('"pass": true', '"pass": false'))
    elif tamper == "extra_file":
        (out / "G2-2" / "extra.json").write_text("{}")
    elif tamper == "orphan_tmp_subfolder":
        (out / "G2-2" / ".U_s30100.json.tmp").write_text("{}")        # review 1 item 4 a
    elif tamper == "duplicate_ledger":
        line = R.read_lines(out / R.LEDGER)[0]
        R._append_line(out / R.LEDGER, line)
    elif tamper == "deleted_rerun":                                    # review 1 item 4 b
        R.record_path(out, ("G2-2", "U_s30101")).unlink()
        rec = {"pass": True, "fail_reasons": [], **R.metadata({**_jobs()[1], "scored": True, "commit": "abc"})}
        R.write_record(out, ("G2-2", "U_s30101"), rec, 2)
    elif tamper == "extra_dir":
        (out / "G2-9").mkdir()
    elif tamper == "metadata":
        p = R.record_path(out, ("G2-2", "U_s30102"))
        r = json.loads(p.read_text())
        r["spec"]["seed"] = 1
        data = json.dumps(r, indent=1).encode()
        p.unlink()
        p.write_bytes(data)
        lines = R.read_lines(out / R.LEDGER)
        for x in lines:
            if x["tid"] == "U_s30102":
                x["sha256"] = R._sha(data)
        (out / R.LEDGER).write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in lines))
    elif tamper == "list":
        jobs = _jobs(3)                                               # the registered list differs (item 4 c)
    elif tamper == "root_tmp":                                        # review 2 item 4
        (out / ".x.json.tmp").write_text("{}")
    elif tamper == "root_tmp_plain":
        (out / "foo.json.tmp").write_text("{}")
    elif tamper == "interrupted_unlogged":
        (out / R.INTERRUPTED).mkdir()
        (out / R.INTERRUPTED / "k9__G2-2__.U_s30100.json.tmp").write_text("{}")
    elif tamper == "starts_emptied":                                  # review 2 S5
        (out / R.STARTS).write_text("")
    elif tamper == "deleted_with_ledger_line":
        _ex(out)                                                      # a second start logs the records present
        R.record_path(out, ("G2-2", "U_s30101")).unlink()
        lines = [x for x in R.read_lines(out / R.LEDGER) if x["tid"] != "U_s30101"]
        (out / R.LEDGER).write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in lines))
    assert _verdict(out, jobs)["status"] == "INVALID", tamper


def test_verdict_flags_recomputation_disagreement(tmp_path):
    out = _run(tmp_path)
    res = A.verdict(out, "scored", check_artifacts=False, expected=_jobs(), recompute_fn=lambda rec, t: False,
                    check_code=False)
    assert res["status"] == "INVALID" and any("recomputed" in p for p in res["problems"])


def test_reported_only_failures_do_not_fail_the_gate(tmp_path):
    jobs = _jobs(2) + [R.job("G2-6", "grip50_stress_s30605", "sens", {"seed": 30605, "moves": "U"},
                             reported_only=True)]

    def screen_fails(j):
        k, r = _fake_runner(j)
        if j["exp"] == "G2-6":
            r.update({"pass": False, "fail_reasons": ["move 1 U: ok_penetration_cubie"]})
        return k, r
    res = _verdict(_run(tmp_path, screen_fails, jobs), jobs)
    assert res["status"] == "PASS" and res["screen"]["grip50_stress_s30605"]["pass_as_turns"] is False


def test_cp_upper():
    assert A.cp_upper(0, 100) == pytest.approx(1 - 0.05 ** (1 / 100), abs=5e-4)
    assert A.cp_upper(5, 5) == 1.0


# ---- the controllers read robot state only (slow: builds the scene) ----------------------------------------------------
def _cube_dofs(m, mujoco):
    core = m.body("core").id
    cube_j = [j for j in range(m.njnt) if m.body_rootid[m.jnt_bodyid[j]] == core]
    nq = {mujoco.mjtJoint.mjJNT_FREE: 7, mujoco.mjtJoint.mjJNT_BALL: 4}
    nv = {mujoco.mjtJoint.mjJNT_FREE: 6, mujoco.mjtJoint.mjJNT_BALL: 3}
    q = sorted({a for j in cube_j for a in range(m.jnt_qposadr[j], m.jnt_qposadr[j] + nq.get(m.jnt_type[j], 1))})
    v = sorted({a for j in cube_j for a in range(m.jnt_dofadr[j], m.jnt_dofadr[j] + nv.get(m.jnt_type[j], 1))})
    return cube_j, q, v


@NEEDS_SCENE
def test_controllers_ignore_cube_state(T):
    import mujoco
    T.configure({}, T.start_draw(29001))
    r = T.TA.TwoArm(T.L, T.HC, T.DEFAULTS["grip"])
    try:
        m, d = r.m, r.d
        r.integ = False
        r.j7 = [r.roll0 + 0.3, 0.5, 1.0]

        def outputs():
            r.impedance()
            r.j7_control()
            return d.ctrl[r.aB].copy()
        mujoco.mj_forward(m, d)
        before = outputs()
        cube_j, q, v = _cube_dofs(m, mujoco)
        assert len(cube_j) >= 21
        q0, v0 = d.qpos.copy(), d.qvel.copy()
        rng = np.random.default_rng(0)
        d.qpos[q] += rng.normal(0.0, 0.05, len(q))
        d.qvel[v] += rng.normal(0.0, 0.5, len(v))
        mujoco.mj_forward(m, d)
        assert np.array_equal(before, outputs())                 # bit-identical
        d.qpos[:], d.qvel[:] = q0, v0
        d.qpos[r.qB[2]] += 0.01                                   # positive control: arm B's own state matters
        mujoco.mj_forward(m, d)
        assert not np.allclose(before, outputs(), atol=1e-6, rtol=0)
    finally:
        T.MagnetSystem.uninstall()


@NEEDS_SCENE
def test_roll_commands_ignore_cube_state(T):
    """Review 1 item 1 / review 2 item 3: the J7 and gripper command sequence of a whole move (settle, grasp, roll, open,
    roll-back) is identical when the cube is turned 180 deg about world z (which flips every cube-derived axis). The
    stubbed step makes J7 follow its command, so the full roll runs (no stall stop). Positive control: a controller
    that takes the roll sign from the cube's orientation (the review-1 bug) must give different commands."""
    import types

    import mujoco
    from rubiknetic.cube_logic import parse
    from rubiknetic.cube_logic.notation import FACE_NORMAL
    T.configure({}, T.start_draw(29001))
    r = T.TA.TwoArm(T.L, T.HC, T.DEFAULTS["grip"])
    try:
        m, d = r.m, r.d
        q7 = r.qB[6]
        state = (d.qpos.copy(), d.qvel.copy(), r.roll0)
        sign0 = r.roll_sign                                           # review 3 S3: the value set at construction
        assert sign0 == float(np.sign(np.array([1.0, 0, 0]) @ r.a_d)) and sign0 in (-1.0, 1.0)
        core_q = m.jnt_qposadr[[j for j in range(m.njnt) if m.jnt_bodyid[j] == r.core][0]]

        def reset(turn_cube: bool):
            d.qpos[:], d.qvel[:] = state[0], state[1]
            if turn_cube:
                qz = np.array([0.0, 0.0, 0.0, 1.0])                   # 180 deg about world z (w, x, y, z)
                out = np.zeros(4)
                mujoco.mju_mulQuat(out, qz, d.qpos[core_q + 3:core_q + 7].copy())
                d.qpos[core_q + 3:core_q + 7] = out
            mujoco.mj_forward(m, d)
            r.j7, r.integ, r.roll_sign = [state[2], 0.0, 0.0], True, sign0
            d.ctrl[r.gB] = r.th_open

        def commands():
            seq = []

            def step(n):
                for _ in range(n):
                    d.qpos[q7] = r.j7[0]                               # J7 follows its command
                    seq.append((tuple(np.round(r.j7, 12)), float(d.ctrl[r.gB])))
            r.step, r.ctrl_step = step, (lambda n=1: None)
            r.move(parse("U")[0])
            return seq

        reset(False)
        first = commands()
        reset(True)
        second = commands()
        assert len(first) > 3000 and first == second                  # the whole move, identical
        assert max(abs(c[0][0] - state[2]) for c in first) > 1.5      # the roll really ran (about 90 deg)

        orig_move = type(r).move

        def buggy_move(self, mv):                                     # the review-1 bug, re-introduced on purpose
            Rc = self.d.xmat[self.core].reshape(3, 3)
            zB = self.d.xmat[self.bodyB].reshape(3, 3)[:, 2]
            self.roll_sign = float(np.sign((Rc @ np.array(FACE_NORMAL[mv.face], float)) @ zB))
            return orig_move(self, mv)
        r.move = types.MethodType(buggy_move, r)
        reset(False)
        b1 = commands()
        reset(True)
        b2 = commands()
        assert b1 != b2                                               # the test can see the bug
    finally:
        T.MagnetSystem.uninstall()


# ---- model audit positive controls (review 3 S3) ------------------------------------------------------------------------
_AUDIT_BASE = """
<mujoco>
  <worldbody>
    <body name="core" pos="0 0 1">
      <freejoint/>
      <geom type="sphere" size="0.01"/>
      <site name="core_site"/>
      <body name="cubie" pos="0.02 0 0">
        <joint name="cubie_j" type="hinge"/>
        <geom name="cubie_g" type="box" size="0.01 0.01 0.01"/>
        <site name="cubie_site"/>
      </body>
    </body>
    <body name="arm" pos="1 0 1">
      <joint name="arm_j" type="hinge"/>
      <geom type="capsule" size="0.01 0.05"/>
      <site name="arm_site"/>
      <body name="arm2" pos="0 0 0.1">
        <joint name="arm2_j" type="hinge"/>
        <geom type="sphere" size="0.01"/>
      </body>
    </body>
  </worldbody>
  {extra}
</mujoco>
"""
_FORBIDDEN = {
    "joint actuator": ("actuators_on_cube", '<actuator><motor joint="cubie_j"/></actuator>'),
    "site actuator": ("actuators_on_cube", '<actuator><motor site="cubie_site" gear="0 0 0 0 0 1"/></actuator>'),
    "body actuator": ("actuators_on_cube", '<actuator><adhesion body="cubie" ctrlrange="0 1"/></actuator>'),
    "tendon (joint)": ("tendons_on_cube", '<tendon><fixed name="t"><joint joint="cubie_j" coef="1"/></fixed></tendon>'),
    "tendon (site)": ("tendons_on_cube", '<tendon><spatial name="t"><site site="arm_site"/><site site="cubie_site"/>'
                      '</spatial></tendon>'),
    "tendon actuator": ("actuators_on_cube", '<tendon><fixed name="t"><joint joint="cubie_j" coef="1"/></fixed></tendon>'
                        '<actuator><motor tendon="t"/></actuator>'),
    "connect": ("equalities_on_cube", '<equality><connect body1="cubie" body2="arm" anchor="0 0 0"/></equality>'),
    "weld": ("equalities_on_cube", '<equality><weld body1="arm" body2="core"/></equality>'),
    "joint equality": ("equalities_on_cube", '<equality><joint joint1="arm_j" joint2="cubie_j"/></equality>'),
    "tendon equality": ("equalities_on_cube", '<tendon><fixed name="t"><joint joint="cubie_j" coef="1"/></fixed>'
                        '<fixed name="u"><joint joint="arm_j" coef="1"/></fixed></tendon>'
                        '<equality><tendon tendon1="u" tendon2="t"/></equality>'),
}


def _audit(T, extra: str, gravcomp: bool = False):
    import mujoco
    xml = _AUDIT_BASE.replace("{extra}", extra)
    if gravcomp:
        xml = xml.replace('<body name="cubie" pos="0.02 0 0">', '<body name="cubie" pos="0.02 0 0" gravcomp="1">')
    return T.TA.model_audit(mujoco.MjModel.from_xml_string(xml))


def test_model_audit_clean_and_robot_only_elements(T):
    """Elements that act only on robot bodies are not findings."""
    clean = _audit(T, '<actuator><motor joint="arm_j"/></actuator>'
                      '<tendon><fixed name="u"><joint joint="arm_j" coef="1"/></fixed></tendon>'
                      '<equality><weld body1="arm" body2="arm2"/><joint joint1="arm_j" joint2="arm2_j"/></equality>')
    assert clean["n_cube_bodies"] == 2
    assert not any(clean[k] for k in ("actuators_on_cube", "equalities_on_cube", "tendons_on_cube", "gravcomp_on_cube"))


@pytest.mark.parametrize("case", list(_FORBIDDEN))
def test_model_audit_flags_each_forbidden_element(T, case):
    key, extra = _FORBIDDEN[case]
    assert _audit(T, extra)[key], case


def test_model_audit_flags_gravcomp(T):
    assert _audit(T, "", gravcomp=True)["gravcomp_on_cube"]
