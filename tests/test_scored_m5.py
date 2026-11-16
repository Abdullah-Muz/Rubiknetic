"""Unit tests for the M5 runner and verdict script (PHASE_1_M5_PREREGISTRATION.md section 6.1 item 3).
No test steps the simulation on an M5 seed (P5): trials are replaced by stand-ins, or stopped before the first step."""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from rubiknetic.cube_logic import invert, random_scramble
from rubiknetic.cube_physics import scored
from rubiknetic.cube_physics.m1_model import M1Params
from rubiknetic.cube_physics.magnets import MagnetParams, layout, near_field_tables

REPO = Path(__file__).resolve().parents[1]


def _load(name, rel):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


A = _load("e5_scored_m5_analyze", "experiments/E5_scored_m5/analyze.py")
R = A.R                                               # the runner module the analyzer uses
M4_FRESH = _load("e4_unpatched_for_m5_tests", "experiments/E4_scored_m4/run.py")   # M4 as registered, unpatched
ENV = {"mujoco": "4.0.1", "numpy": "x", "scipy": "y", "python": "3.12", "cpu": "test", "platform": "p"}
GAP_TAGS = {"gap=2.5e-05": 2.5e-5, "gap=0.0001": 1e-4}


@pytest.fixture
def coarse():
    tabs = near_field_tables(MagnetParams(), None, quad=(4, 12), n_rho=13, n_z=9)
    R.M4.TABLES_PROVIDER = lambda mp: tabs
    yield tabs
    R.M4.TABLES_PROVIDER = None
    R.M4.restore_process()


# ---- seeds and trial list ------------------------------------------------------------------------------------------
def test_seed_list_is_m4_plus_4000_and_in_range():
    m4 = M4_FRESH.build_jobs("all", "c", {}, 5.0, False)
    m5 = R.build_m5_jobs("c", {}, 5.0)
    assert len(m4) == len(m5) == 442
    for a, b in zip(m4, m5):
        assert (a["exp"], a["magnets"], a["kind"]) == (b["exp"], b["magnets"], b["kind"])
        assert b["kw"]["seed"] == a["kw"]["seed"] + 4000
        s = a["kw"]["seed"]
        if a["exp"] != "E1-7":                     # E1-7 tags change with the re-centred gap factors (section 4)
            assert b["tid"] == a["tid"][: -len(f"_s{s}")] + f"_s{s + 4000}"
    seeds = [j["kw"]["seed"] for j in m5]
    assert min(seeds) >= 10000 and max(seeds) <= 10999
    assert not any(7000 <= s <= 8999 for s in seeds)


def test_record_keys_unique_although_e16n_reuses_trial_ids():
    m5 = R.build_m5_jobs("c", {}, 5.0)
    keys = [R.key_of(j) for j in m5]
    assert len(set(keys)) == len(keys) == 442
    assert len({j["tid"] for j in m5}) < len(m5)          # trial IDs alone repeat (U2)


def test_e4_scrambles_drawn_from_the_m5_seed():
    scr = [j for j in R.build_m5_jobs("c", {}, 5.0) if j["tid"].startswith("scr20inv_") and j["magnets"]]
    assert [j["kw"]["seed"] for j in scr] == list(range(10400, 10420))
    for j in scr:
        sc = random_scramble(20, j["kw"]["seed"])
        assert j["kw"]["moves"] == " ".join(str(m) for m in sc + invert(sc))
    old = {j["kw"]["moves"] for j in M4_FRESH.build_jobs("E1-4", "c", {}, 5.0, False)}
    assert not old & {j["kw"]["moves"] for j in scr if True}


def test_e17_factors_recentred():
    tags = {j["tid"].split("__")[0] for j in R.build_m5_jobs("c", {}, 5.0) if j["exp"] == "E1-7"}
    assert {"gap=2.5e-05", "gap=0.0001", "face_gap_mm=0.35", "face_gap_mm=1.35", "nominal"} <= tags
    assert not {"gap=0.0002", "gap=5e-05", "face_gap_mm=0.85", "face_gap_mm=1.0"} & tags


# ---- gap: cubies and magnet layout (N1, O3) ------------------------------------------------------------------------
class _Stop(BaseException):
    pass


def _capture(job_list, monkeypatch):
    """For each job: the cubie gap reaching scored.Trial and the magnet system installed, with no stepping."""
    got = []

    def trial_stub(params, setup, **_kw):
        got.append(params.gap)
        raise _Stop

    monkeypatch.setattr(scored, "Trial", trial_stub)
    out = []
    for j in job_list:
        got.clear()
        with pytest.raises(_Stop):
            R.M4.run_trial(j["kind"], copy.deepcopy(j["kw"]), j["magnets"])
        ms = R.M4._MS
        out.append((j, got[0], None if ms is None else ms.p_loc.copy(), None if ms is None else R.M4._MS_KEY[1]))
    return out


def _expected_gap(j):
    return GAP_TAGS.get(j["tid"].split("__")[0], R.GAP) if j["exp"] == "E1-7" else R.GAP


def test_gap_reaches_cubies_and_magnet_layout_in_every_job(coarse, monkeypatch):
    pitch = M1Params().pitch
    jobs = R.build_m5_jobs("c", {}, 5.0)
    n_mag = 0
    for j, cubie_gap, p_loc, layout_gap in _capture(jobs, monkeypatch):
        g = _expected_gap(j)
        assert cubie_gap == g, j["tid"]
        mp = R.magnet_params_for(dict(j["kw"].get("overrides", {}))) if j["magnets"] else None
        if mp is None:
            assert p_loc is None
            continue
        n_mag += 1
        assert layout_gap == g, j["tid"]
        assert np.allclose(p_loc, [m["pos"] for m in layout(pitch, g, mp)], atol=1e-15), j["tid"]
    assert n_mag > 250


def test_gap_test_fails_under_the_rehearsal_style_overwrite(coarse, monkeypatch):
    jobs = [j for j in R.build_m5_jobs("c", {}, 5.0) if j["tid"].split("__")[0] in GAP_TAGS]
    assert len(jobs) == 4
    for j in jobs:
        j["kw"]["overrides"]["gap"] = R.GAP                 # rehearsal_gap.py:42 overwrites unconditionally
    wrong = [j for j, cubie_gap, _p, lg in _capture(jobs, monkeypatch) if cubie_gap != _expected_gap(j)]
    assert len(wrong) == 4


def test_wall_from_the_m5_gap():
    for fg, wall in ((0.35, 0.15e-3), (0.85, 0.4e-3), (1.35, 0.65e-3)):
        assert np.isclose(R.magnet_params_for({"face_gap_mm": fg}).wall, wall, rtol=0, atol=1e-15)
    assert R.magnet_params_for({}).wall == 0.4e-3


def test_startup_check_runs_and_records_the_m5_gap(coarse):
    res = R.startup_check()
    assert res["pass"] and res["gap"] == R.GAP
    assert R.M4._MS_KEY[1] == R.GAP


# ---- V3 matching (section 4) ---------------------------------------------------------------------------------------
def _v3_file(d, name, dia, length, grade, scale, ok, wall=0.0004, v3=True):
    j = {"magnet_params": {"diameter": dia, "length": length, "grade": grade, "scale": scale, "wall": wall}}
    if v3:
        j["V3"] = {"pass": ok, "validated_tilt_deg": 5.0}
    else:
        j["V3_pair_extension"] = {"pass": ok}
    (d / name).write_text(json.dumps(j))


def test_v3_match_by_size_grade_and_scale_ignoring_wall(tmp_path, monkeypatch):
    res = tmp_path / "results"
    res.mkdir()
    monkeypatch.setattr(R.M4, "D8", tmp_path)
    _v3_file(res, "d8_1b_checks.json", 0.004, 0.002, "N35", 1.0, True, wall=0.0001)
    _v3_file(res, "d8_1b_checks_pair0.35mm_4x2_N35_s1.json", 0.004, 0.002, "N35", 1.0, True, v3=False)
    assert len(R.v3_matches(MagnetParams())) == 1                       # pair record skipped, wall ignored
    assert R.v3_record_for(MagnetParams(wall=0.00015))["validated_tilt_deg"] == 5.0
    assert R.v3_matches(MagnetParams(grade="N52")) == []                # grade must match (M4 matched size only)
    assert R.v3_matches(MagnetParams(scale=0.67)) == []                 # scale must match
    _v3_file(res, "d8_1b_checks_dup.json", 0.004, 0.002, "N35", 1.0, True)
    assert R.v3_record_for(MagnetParams()) is None                      # two matches: no record


def test_classify_registered_not_run_and_refusals(tmp_path, monkeypatch):
    res = tmp_path / "results"
    res.mkdir()
    monkeypatch.setattr(R.M4, "D8", tmp_path)
    monkeypatch.setattr(R, "PAIR_CHECK", res / "pair.json")
    monkeypatch.setattr(R.M4, "magnet_availability", lambda mp: {"table_file": "t", "table_sha256": "s"})
    _v3_file(res, "d8_1b_checks.json", 0.004, 0.002, "N35", 1.0, True)
    _v3_file(res, "d8_1b_checks_4x1.5.json", 0.004, 0.0015, "N35", 1.0, False)
    jobs = {j["tid"]: j for j in R.build_m5_jobs("c", {}, 5.0) if j["exp"] == "E1-7"}
    assert R.classify(jobs["magnet=4x1.5_N35__6move"])[:2] == ("not_run", "failed V3")
    assert R.classify(jobs["magnet=4x2_N52__6move"])[0] == "refused"        # no record: not a registered reason
    assert R.classify(jobs["face_gap_mm=0.35__6move"])[0] == "refused"      # pair check missing
    _v3_file(res, "pair.json", 0.004, 0.002, "N35", 1.0, False, v3=False)
    assert R.classify(jobs["face_gap_mm=0.35__6move"])[:2] == ("not_run", "outside V3")
    _v3_file(res, "pair.json", 0.004, 0.002, "N35", 1.0, True, v3=False)
    assert R.classify(jobs["face_gap_mm=0.35__6move"])[0] == "run"
    assert R.classify(jobs["magnet=none__6move"])[0] == "run"


# ---- synthetic runs: stand-in trials, real run procedure, real verdict script ---------------------------------------
def _fake_record(job, mutate=None):
    ov = job["kw"].get("overrides", {})
    gap = ov.get("gap", R.GAP)
    mp = R.magnet_params_for(dict(ov)) if job["magnets"] else None
    rec = {"params": {"gap": gap}, "pass": True, "fail_reasons": [], "environment": job["env"],
           "magnets": None if mp is None else {"params": {"wall": mp.wall}, "layout_gap": gap},
           "magnet_table": job.get("magnet_info"), "magnet_stats": {"max_near_tilt_deg": 1.0}}
    if job["kind"] == "seq":
        rec["sequence"] = job["kw"]["moves"]
        rec["per_move"] = [{"e16m_P_ok": True, "nontarget_drift_deg": 0.1, "max_turner_torque_Nm": 0.2}
                           for _ in job["kw"]["moves"].split()]
    rec.update(R._metadata(job))
    if mutate:
        mutate(R.key_of(job), rec)
    return rec


def _dirs(tmp):
    return {"magnets": tmp / "results", "no_magnets": tmp / "results_nomag"}


def _split(jobs):
    run, not_run = [], []
    for j in jobs:
        if j["tid"].startswith("magnet=4x1.5_N35__"):
            not_run.append((j, "failed V3"))
        else:
            mp = R.magnet_params_for(dict(j["kw"].get("overrides", {}))) if j["magnets"] else None
            if mp is not None:
                j["magnet_info"] = {"table_file": R.M4._rel(R.M4.table_path(mp)), "table_sha256": "abc"}
            run.append(j)
    return run, not_run


def _make(tmp, mutate=None, stop_after=None, jobs=None):
    jobs = R.build_m5_jobs("c0", ENV, 5.0) if jobs is None else jobs
    run, not_run = _split(jobs)
    n = R.execute(_dirs(tmp), run, not_run, "c0", ENV, "c0", {"gap": R.GAP}, 1,
                  runner=lambda j: (R.key_of(j), _fake_record(j, mutate)), stop_after=stop_after,
                  check_git=False, log=lambda s: None)
    return jobs, n


def _verdict(tmp, registered=None):
    reg = R.build_m5_jobs("c0", ENV, 5.0) if registered is None else registered
    return A.analyse(_dirs(tmp), reg)


@pytest.fixture(scope="module")
def complete_set(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("complete")
    _make(tmp)
    return tmp


def test_positive_control_complete_valid_set_passes(complete_set):
    st, vd = _verdict(complete_set)
    assert st["violations"] == [] and st["missing"] == []
    assert vd["verdict"] == "PASS"
    assert vd["rows"]["E1-6t"] == {"n": 16, "expected": 16, "passed": 16}
    assert sum(1 for k in st["records"] if k[0] == "no_magnets") == 184


def _ledger_lines(tmp):
    return (tmp / "results" / R.LEDGER).read_text().splitlines()


def test_one_failing_e16t_trial_is_not_passed(tmp_path):
    def m(key, rec):
        if key == ("magnets", "E1-6t", "std_ppp_pos_s10654"):
            rec["pass"], rec["fail_reasons"] = False, ["E1-6t"]
    _make(tmp_path, m)
    st, vd = _verdict(tmp_path)
    assert st["violations"] == [] and vd["verdict"] == "NOT PASSED"


def test_one_move_failing_e16m_is_not_passed(tmp_path):
    def m(key, rec):
        if key == ("magnets", "E1-2", "U_s10100"):
            rec["per_move"][0]["e16m_P_ok"] = False
    _make(tmp_path, m)
    assert _verdict(tmp_path)[1]["verdict"] == "NOT PASSED"


def test_missing_e16t_record_is_incomplete(tmp_path):
    _make(tmp_path)
    key = ("magnets", "E1-6t", "std_ppp_pos_s10654")
    R.record_path(_dirs(tmp_path), key).unlink()
    lines = [x for x in _ledger_lines(tmp_path) if json.loads(x)["tid"] != key[2] or json.loads(x)["arm"] != key[0]]
    (tmp_path / "results" / R.LEDGER).write_text("\n".join(lines) + "\n")
    st, vd = _verdict(tmp_path)
    assert st["violations"] == [] and vd["verdict"] == "INCOMPLETE" and st["missing"] == [key]


def _invalid(tmp, needle, mutate=None, after=None):
    _make(tmp, mutate)
    if after:
        after(tmp)
    st, vd = _verdict(tmp)
    assert vd["verdict"] == "INVALID", st["violations"]
    assert any(needle in v for v in st["violations"]), st["violations"]


K_SEQ = ("magnets", "E1-2", "U_s10100")


def _only(key, **fields):
    def m(k, rec):
        if k == key:
            for f, v in fields.items():
                if callable(v):
                    v(rec)
                else:
                    rec[f] = v
    return m


@pytest.mark.parametrize("needle, mutate", [
    ("mechanism 'M4'", _only(K_SEQ, mechanism="M4")),
    ("params.gap", _only(K_SEQ, params={"gap": 2e-4})),
    ("layout_gap", _only(K_SEQ, magnets={"params": {"wall": 0.4e-3}, "layout_gap": 1e-4})),
    ("layout_gap", _only(("magnets", "E1-7", "gap=2.5e-05__6move"), params={"gap": 5e-5},
                         magnets={"params": {"wall": 0.4e-3}, "layout_gap": 5e-5})),
    ("source commit", _only(K_SEQ, source_commit="other")),
    ("scored = False", _only(K_SEQ, scored=False)),
    ("E1-4 sequence", _only(("magnets", "E1-4", "scr20inv_s10400"), sequence="U R")),
    ("startup_checks.gap", _only(K_SEQ, startup_checks={"gap": 2e-4})),
    ("wall", _only(("magnets", "E1-7", "face_gap_mm=0.35__6move"),
                   magnets={"params": {"wall": 0.4e-3}, "layout_gap": 5e-5})),
    ("table SHA-256", _only(K_SEQ, magnet_table={"table_file": R.M4._rel(R.M4.table_path(MagnetParams())),
                                                  "table_sha256": "zzz"})),
    ("environment", _only(K_SEQ, environment={**ENV, "mujoco": "9"})),
])
def test_record_integrity_violations_are_invalid(tmp_path, needle, mutate):
    _invalid(tmp_path, needle, mutate)


def _extra_record(tmp):
    R.write_record(_dirs(tmp), ("magnets", "E1-2", "U_s99999"), {"x": 1}, 1)


def _garbage(tmp):
    (tmp / "results" / "E1-2" / "bad.json").write_text("{not json")


def _drop_ledger_line(tmp):
    lines = _ledger_lines(tmp)
    (tmp / "results" / R.LEDGER).write_text("\n".join(lines[1:]) + "\n")


def _extra_ledger_line(tmp):
    R._append_line(tmp / "results" / R.LEDGER, {"start": 1, "arm": "magnets", "exp": "E1-2", "tid": "nope",
                                                 "sha256": "0", "reconciled": False})


def _bad_sha(tmp):
    lines = _ledger_lines(tmp)
    x = json.loads(lines[0])
    x["sha256"] = "0" * 64
    (tmp / "results" / R.LEDGER).write_text("\n".join([json.dumps(x)] + lines[1:]) + "\n")


def _dup_line(tmp):
    lines = _ledger_lines(tmp)
    (tmp / "results" / R.LEDGER).write_text("\n".join(lines + [lines[0]]) + "\n")


def _tmp_file(tmp):
    (tmp / "results" / "E1-2" / ".U_s10100.json.tmp").write_text("{}")


@pytest.mark.parametrize("needle, after", [
    ("record not in the manifest", _extra_record),
    ("does not parse", _garbage),
    ("record without a ledger line", _drop_ledger_line),
    ("ledger line without a record", _extra_ledger_line),
    ("ledger SHA-256 differs", _bad_sha),
    ("times in the ledger", _dup_line),
    ("unlogged temporary file", _tmp_file),
])
def test_file_level_violations_are_invalid(tmp_path, needle, after):
    _invalid(tmp_path, needle, after=after)


# ---- run procedure (section 2) -------------------------------------------------------------------------------------
def test_first_start_refused_when_a_results_folder_is_not_empty(tmp_path):
    (tmp_path / "results_nomag").mkdir()
    (tmp_path / "results_nomag" / "x.txt").write_text("x")
    with pytest.raises(SystemExit, match="refusing first start"):
        _make(tmp_path)


def test_resume_runs_only_missing_keys_including_e16n_twins_and_never_overwrites(tmp_path):
    jobs = [j for j in R.build_m5_jobs("c0", ENV, 5.0) if j["tid"] in ("U_s10100", "Up_s10102")]
    assert len(jobs) == 4                                  # magnet and no-magnet arm of two trial IDs
    jobs.sort(key=lambda j: (j["tid"], j["arm"]))
    with pytest.raises(R.Interrupted):
        _make(tmp_path, jobs=copy.deepcopy(jobs), stop_after=1)
    first = sorted(p for p in (tmp_path).rglob("*.json") if p.name != R.MANIFEST)
    assert len(first) == 1
    before = {p: p.read_bytes() for p in first}
    _, n = _make(tmp_path, jobs=copy.deepcopy(jobs))
    assert n == 3
    for p, b in before.items():
        assert p.read_bytes() == b
    lines = [json.loads(x) for x in _ledger_lines(tmp_path)]
    assert sorted((x["arm"], x["tid"]) for x in lines) == sorted((j["arm"], j["tid"]) for j in jobs)
    assert [x["start"] for x in lines].count(2) == 3
    st, _vd = A.analyse(_dirs(tmp_path), jobs)
    assert st["violations"] == []


def test_write_record_never_overwrites(tmp_path):
    key = ("magnets", "E1-2", "U_s1")
    R.write_record(_dirs(tmp_path), key, {"a": 1}, 1)
    with pytest.raises(FileExistsError):
        R.write_record(_dirs(tmp_path), key, {"a": 2}, 1)


@pytest.mark.parametrize("change", ["trials", "not_run", "tables", "env"])
def test_resume_refused_when_the_configuration_changed(tmp_path, change):
    jobs = [j for j in R.build_m5_jobs("c0", ENV, 5.0) if j["exp"] in ("E1-1", "E1-7")]
    _make(tmp_path, jobs=copy.deepcopy(jobs), stop_after=None)
    jobs2 = copy.deepcopy(jobs)
    run, not_run = _split(jobs2)
    env = dict(ENV)
    if change == "trials":
        run = run[1:]
    elif change == "not_run":
        run, not_run = run + [j for j, _ in not_run], []
    elif change == "tables":
        for j in run:
            if j.get("magnet_info"):
                j["magnet_info"] = {**j["magnet_info"], "table_sha256": "changed"}
    else:
        env["cpu"] = "other"
    with pytest.raises(SystemExit, match="refusing resume"):
        R.execute(_dirs(tmp_path), run, not_run, "c0", env, "c0", {"gap": R.GAP}, 1,
                  runner=lambda j: (R.key_of(j), _fake_record(j)), check_git=False, log=lambda s: None)


def test_resume_moves_orphans_and_reconciles_ledger_lines(tmp_path):
    jobs = [j for j in R.build_m5_jobs("c0", ENV, 5.0) if j["exp"] == "E1-1"]
    with pytest.raises(R.Interrupted):
        _make(tmp_path, jobs=copy.deepcopy(jobs), stop_after=2)
    d = _dirs(tmp_path)
    # (ii) a record linked but killed before its ledger line
    lines = _ledger_lines(tmp_path)
    (tmp_path / "results" / R.LEDGER).write_text("\n".join(lines[:1]) + "\n")
    # (i) an orphan temporary file of a trial that has no record
    orphan = d["magnets"] / "E1-1" / ".rest_s10019.json.tmp"
    orphan.write_text('{"partial": ')
    _, n = _make(tmp_path, jobs=copy.deepcopy(jobs))
    assert n == 18
    starts = [json.loads(x) for x in (tmp_path / "results" / R.STARTS).read_text().splitlines()]
    assert len(starts) == 2 and len(starts[1]["orphans"]) == 1 and len(starts[1]["reconciled"]) == 1
    assert not orphan.exists() and (d["magnets"] / R.INTERRUPTED / "k2__E1-1__.rest_s10019.json.tmp").exists()
    st, _vd = A.analyse(d, jobs)
    assert st["violations"] == [] and st["missing"] == []
    assert sum(1 for x in st["ledger"] if x["reconciled"]) == 1


def _job(tid="U_s10100", exp="E1-2", magnets=True):
    return next(copy.deepcopy(j) for j in R.build_m5_jobs("c0", ENV, 5.0)
                if j["tid"] == tid and j["exp"] == exp and j["magnets"] == magnets)


def test_harness_exception_gives_a_failing_record_that_passes_integrity(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise ValueError("boom")

    monkeypatch.setattr(R.M4, "run_trial", boom)
    jobs = [j for j in R.build_m5_jobs("c0", ENV, 5.0) if j["exp"] in ("E1-2", "E1-7")]
    run, not_run = _split(jobs)
    R.execute(_dirs(tmp_path), run, not_run, "c0", ENV, "c0", {"gap": R.GAP}, 1, check_git=False,
              log=lambda s: None)
    st, vd = A.analyse(_dirs(tmp_path), jobs)
    assert st["violations"] == [], st["violations"][:5]
    rec = st["records"][("magnets", "E1-7", "gap=2.5e-05__6move")]
    assert rec["pass"] is False and "ValueError: boom" in rec["fail_reasons"][0]
    assert rec["params"]["gap"] == 2.5e-5 and rec["magnets"]["layout_gap"] == 2.5e-5
    assert rec["mechanism"] == "M5" and rec["trial_id"] == "gap=2.5e-05__6move"


@pytest.mark.parametrize("exc", [MemoryError, OSError])
def test_memory_and_os_errors_are_interruptions_without_a_record(tmp_path, monkeypatch, exc):
    def boom(*a, **k):
        raise exc("x")

    monkeypatch.setattr(R.M4, "run_trial", boom)
    jobs = [_job()]
    run, not_run = _split(jobs)
    with pytest.raises(R.Interrupted):
        R.execute(_dirs(tmp_path), run, not_run, "c0", ENV, "c0", {"gap": R.GAP}, 1, check_git=False,
                  log=lambda s: None)
    assert not R.record_path(_dirs(tmp_path), R.key_of(jobs[0])).exists()
    assert not (tmp_path / "results" / R.LEDGER).exists()


def test_manifest_is_written_once(tmp_path):
    R.write_manifest(_dirs(tmp_path), {"a": 1})
    with pytest.raises(FileExistsError):
        R.write_manifest(_dirs(tmp_path), {"a": 2})
    assert json.loads((tmp_path / "results" / R.MANIFEST).read_text())["a"] == 1


# ---- revision 6 (review 5) -----------------------------------------------------------------------------------------
def _fake(j):
    return R.key_of(j), _fake_record(j)


def test_resume_refused_on_a_different_frozen_path_commit(tmp_path):
    """V1: the git branch of the resume check, with check_git on (cdfc76e predates the runner)."""
    head, old = scored._git("rev-parse", "HEAD"), scored._git("rev-parse", "cdfc76e")
    jobs = [j for j in R.build_m5_jobs("c0", ENV, 5.0) if j["exp"] == "E1-1"][:3]
    run, nr = _split(copy.deepcopy(jobs))
    with pytest.raises(R.Interrupted):
        R.execute(_dirs(tmp_path), run, nr, old, ENV, old, {"gap": R.GAP}, 1, runner=_fake, stop_after=1,
                  log=lambda s: None)
    run, nr = _split(copy.deepcopy(jobs))
    with pytest.raises(SystemExit, match="frozen paths differ"):
        R.execute(_dirs(tmp_path), run, nr, head, ENV, head, {"gap": R.GAP}, 1, runner=_fake, log=lambda s: None)


def test_resume_allowed_from_the_manifest_commit(tmp_path):
    head = scored._git("rev-parse", "HEAD")
    jobs = [j for j in R.build_m5_jobs("c0", ENV, 5.0) if j["exp"] == "E1-1"][:3]
    run, nr = _split(copy.deepcopy(jobs))
    with pytest.raises(R.Interrupted):
        R.execute(_dirs(tmp_path), run, nr, head, ENV, head, {"gap": R.GAP}, 1, runner=_fake, stop_after=1,
                  log=lambda s: None)
    run, nr = _split(copy.deepcopy(jobs))
    assert R.execute(_dirs(tmp_path), run, nr, head, ENV, head, {"gap": R.GAP}, 1, runner=_fake,
                     log=lambda s: None) == 2


def test_resume_refused_when_commits_touch_the_results_folders():
    """Review 5, O7: the results folders are diffed like the frozen paths."""
    head, old = scored._git("rev-parse", "HEAD"), scored._git("rev-parse", "cdfc76e")
    m = {"trials": [], "not_run": [], "tables": {}, "environment": ENV, "commit": old, "frozen_paths": []}
    probs = R.resume_problems(m, m, head, True, ("experiments/E5_scored_m5",))
    assert any("touch the results folders" in p for p in probs)
    assert R.resume_problems(m, m, head, True, ("experiments/E1_scored",)) == []


def _interrupted_run(tmp, stop_after=2):
    jobs = [j for j in R.build_m5_jobs("c0", ENV, 5.0) if j["exp"] == "E1-1"]
    with pytest.raises(R.Interrupted):
        _make(tmp, jobs=copy.deepcopy(jobs), stop_after=stop_after)
    return jobs


def test_resume_refused_when_a_foreign_file_is_present(tmp_path):
    jobs = _interrupted_run(tmp_path)
    (tmp_path / "results" / "E1-1" / "rest_s10000-conflict.txt").write_text("x")
    with pytest.raises(SystemExit, match="would make the run INVALID"):
        _make(tmp_path, jobs=copy.deepcopy(jobs))


def test_kill_after_logging_the_plan_but_before_moving_is_recoverable(tmp_path, monkeypatch):
    """Review 5, O2 (b): the plan is logged before any orphan is moved, so a kill in between loses nothing."""
    jobs = _interrupted_run(tmp_path)
    orphan = tmp_path / "results" / "E1-1" / ".rest_s10019.json.tmp"
    orphan.write_text("partial")

    def killed(*a, **k):
        raise SystemExit("killed")

    monkeypatch.setattr(R, "apply_resume", killed)
    with pytest.raises(SystemExit, match="killed"):
        _make(tmp_path, jobs=copy.deepcopy(jobs))
    monkeypatch.undo()
    _make(tmp_path, jobs=copy.deepcopy(jobs))
    assert not orphan.exists()
    st, _vd = A.analyse(_dirs(tmp_path), jobs)
    assert st["violations"] == [] and st["missing"] == []


def test_two_orphans_of_one_trial_do_not_collide(tmp_path):
    """Review 5, O2 (c): the moved name carries the start index."""
    jobs = _interrupted_run(tmp_path, stop_after=1)
    orphan = tmp_path / "results" / "E1-1" / ".rest_s10019.json.tmp"
    orphan.write_text("first")
    with pytest.raises(R.Interrupted):
        _make(tmp_path, jobs=copy.deepcopy(jobs), stop_after=1)
    orphan.write_text("second")
    _make(tmp_path, jobs=copy.deepcopy(jobs))
    moved = sorted(p.read_text() for p in (tmp_path / "results" / R.INTERRUPTED).iterdir())
    assert moved == ["first", "second"]
    assert A.analyse(_dirs(tmp_path), jobs)[0]["violations"] == []


def test_manifest_temporary_file_never_lands_in_results(tmp_path):
    """Review 5, O2 (a): a leftover temporary manifest from a killed first start sits outside results/ and is
    overwritten by the next first start."""
    (tmp_path / ".results.MANIFEST.json.tmp").write_text("partial")
    jobs = [j for j in R.build_m5_jobs("c0", ENV, 5.0) if j["exp"] == "E1-1"][:2]
    _make(tmp_path, jobs=copy.deepcopy(jobs))
    assert sorted(p.name for p in (tmp_path / "results").iterdir()) == ["E1-1", R.LEDGER, R.MANIFEST, R.STARTS]
    assert A.analyse(_dirs(tmp_path), jobs)[0]["violations"] == []


def _spec(**ch):
    def f(rec):
        rec["spec"] = {**rec["spec"], **ch}
    return f


K_NOMAG = ("no_magnets", "E1-2", "U_s10100")


@pytest.mark.parametrize("needle, mutate", [
    ("spec differs from the registered trial", _only(K_SEQ, spec=_spec(moves="U2"))),
    ("seed differs from the manifest", _only(K_SEQ, spec=_spec(seed=1))),
    ("metadata does not match its key", _only(K_SEQ, trial_id="U_s1")),
    ("magnet record without magnets", _only(K_SEQ, magnets=None)),
    ("no-magnet record carries magnets", _only(K_NOMAG, magnets={"params": {"wall": 0.4e-3}, "layout_gap": 5e-5})),
    ("table file None", _only(K_SEQ, magnet_table=None)),
    ("is not", _only(K_SEQ, magnet_table={"table_file": "experiments/other.npz", "table_sha256": "abc"})),
])
def test_more_record_violations_are_invalid(tmp_path, needle, mutate):
    _invalid(tmp_path, needle, mutate)


def _unlogged_orphan(tmp):
    d = tmp / "results" / R.INTERRUPTED
    d.mkdir()
    (d / "k9__E1-2__.U_s10100.json.tmp").write_text("x")


def _stray(tmp):
    (tmp / "results" / "notes.txt").write_text("x")


@pytest.mark.parametrize("needle, after", [
    ("not logged in the start log", _unlogged_orphan),
    ("unexpected file", _stray),
])
def test_more_file_violations_are_invalid(tmp_path, needle, after):
    _invalid(tmp_path, needle, after=after)


def test_manifest_keys_must_equal_the_registered_list(complete_set):
    reg = R.build_m5_jobs("c0", ENV, 5.0)[1:]
    st, vd = A.analyse(_dirs(complete_set), reg)
    assert vd["verdict"] == "INVALID" and any("differ from the registered list" in v for v in st["violations"])


def test_not_run_set_must_equal_the_rederived_one(complete_set):
    st, vd = A.analyse(_dirs(complete_set), R.build_m5_jobs("c0", ENV, 5.0), derived_not_run={})
    assert vd["verdict"] == "INVALID" and any("re-derived" in v for v in st["violations"])
    nr = {("magnets", "E1-7", f"magnet=4x1.5_N35__{s}"): "failed V3" for s in ("6move", "sexy6")}
    assert A.analyse(_dirs(complete_set), R.build_m5_jobs("c0", ENV, 5.0), derived_not_run=nr)[1]["verdict"] == "PASS"


def test_unregistered_not_run_reason_is_invalid(tmp_path):
    jobs = [j for j in R.build_m5_jobs("c0", ENV, 5.0) if j["exp"] in ("E1-1", "E1-7")]
    run, nr = _split(copy.deepcopy(jobs))
    nr = [(j, "other") for j, _r in nr]
    R.execute(_dirs(tmp_path), run, nr, "c0", ENV, "c0", {"gap": R.GAP}, 1, runner=_fake, check_git=False,
              log=lambda s: None)
    st, vd = A.analyse(_dirs(tmp_path), jobs)
    assert vd["verdict"] == "INVALID" and any("unregistered reason" in v for v in st["violations"])


def test_incomplete_with_a_failure_reports_both_words(tmp_path):
    def m(key, rec):
        if key == ("magnets", "E1-6t", "std_ppp_pos_s10654"):
            rec["pass"], rec["fail_reasons"] = False, ["E1-6t"]
    _make(tmp_path, m)
    key = ("no_magnets", "E1-2", "U_s10100")
    R.record_path(_dirs(tmp_path), key).unlink()
    lines = [x for x in _ledger_lines(tmp_path) if (json.loads(x)["arm"], json.loads(x)["tid"]) != (key[0], key[2])]
    (tmp_path / "results" / R.LEDGER).write_text("\n".join(lines) + "\n")
    assert _verdict(tmp_path)[1]["verdict"] == "INCOMPLETE (and NOT PASSED)"


def test_unserialisable_record_is_a_failed_trial(monkeypatch):
    """Review 5, O4."""
    monkeypatch.setattr(R.M4, "run_trial",
                        lambda kind, kw, mag: ({"pass": True, "bad": object(), "magnets": None}, None, None))
    key, rec = R.run_job(_job())
    assert rec["pass"] is False and "TypeError" in rec["fail_reasons"][0]


def _no_real_start(monkeypatch, tmp_path):
    """Review 6, X1: if the check under test ever regresses, the test fails here instead of starting a run."""
    def unreachable(*a, **k):
        raise AssertionError("the test reached a real start")
    monkeypatch.setattr(R, "execute", unreachable)
    monkeypatch.setattr(R, "startup_check", unreachable)
    monkeypatch.setattr(R, "OUT", tmp_path / "results")
    monkeypatch.setattr(R, "OUT_NOMAG", tmp_path / "results_nomag")


@pytest.mark.parametrize("where", ["here", "results", "results_nomag", "inside"])
def test_smoke_dir_may_not_be_the_scored_folders(where, monkeypatch, tmp_path):
    _no_real_start(monkeypatch, tmp_path)
    d = {"here": R.HERE, "results": R.OUT, "results_nomag": R.OUT_NOMAG, "inside": R.OUT / "x"}[where]
    with pytest.raises(SystemExit, match="scored folders"):
        R.main(["smoke", "--smoke-dir", str(d)])


@pytest.mark.parametrize("folder", ["OneDrive", "OneDrive - Example Org", "onedrive"])
def test_scored_start_refused_when_a_results_folder_is_in_onedrive(monkeypatch, tmp_path, folder):
    """Revision 8 (replaces the OneDrive-process test of review 5, O1)."""
    _no_real_start(monkeypatch, tmp_path / folder / "Rubiknetic")
    with pytest.raises(SystemExit, match="must not use a OneDrive folder"):
        R.main(["all"])


def test_committed_v3_records_classify_440_runnable_2_not_run_0_refused():
    """Review 5, O12: the committed V3 and pair-check records give the registered E1-7 outcome."""
    run, nr, refused = R.prepare(R.build_m5_jobs("c", ENV, 5.0))
    assert (len(run), len(nr), len(refused)) == (440, 2, 0)
    assert sorted((j["tid"], r) for j, r in nr) == [("magnet=4x1.5_N35__6move", "failed V3"),
                                                     ("magnet=4x1.5_N35__sexy6", "failed V3")]


# ---- revision 7 (review 6) -----------------------------------------------------------------------------------------
@pytest.fixture
def no_tables(monkeypatch, tmp_path):
    """The git-ignored near-field tables are absent (a fresh clone): every .npz in the tables folder reads as
    missing; the expected table paths are unchanged."""
    real_exists, tables = Path.exists, R.M4.TABLES

    def exists(self, *a, **k):
        return False if self.suffix == ".npz" and self.parent == tables else real_exists(self, *a, **k)
    monkeypatch.setattr(Path, "exists", exists)
    return tmp_path


def test_rederived_not_run_set_reads_no_tables(no_tables):
    """Review 6, W1: without the tables the runner refuses, but the verdict script's re-derivation is unchanged."""
    reg = R.build_m5_jobs("c0", ENV, 5.0)
    _run, _nr, refused = R.prepare([dict(j) for j in reg])
    assert len(refused) > 0                                   # the tables really are absent
    nr = {("magnets", "E1-7", f"magnet=4x1.5_N35__{s}"): "failed V3" for s in ("6move", "sexy6")}
    assert R.v3_not_run(reg) == nr


def test_complete_valid_set_without_tables_is_not_invalid(complete_set, no_tables):
    """Review 6, W1: a complete, valid set analysed with the tables absent gives PASS, not INVALID."""
    reg = R.build_m5_jobs("c0", ENV, 5.0)
    st, vd = A.analyse(_dirs(complete_set), reg, derived_not_run=R.v3_not_run(reg))
    assert st["violations"] == [] and vd["verdict"] == "PASS"


def test_verdict_script_main_never_reads_tables(complete_set, no_tables, monkeypatch, capsys):
    """Review 6, W1: analyze.main end to end on the complete set, tables absent, the runner's prepare unusable."""
    def unreachable(*a, **k):
        raise AssertionError("the verdict script called the runner's availability check")
    monkeypatch.setattr(R, "prepare", unreachable)
    monkeypatch.setattr(R.M4, "magnet_availability", unreachable)
    monkeypatch.setattr(R, "OUT", complete_set / "results")
    monkeypatch.setattr(R, "OUT_NOMAG", complete_set / "results_nomag")
    monkeypatch.setattr(R, "environment", lambda: ENV)
    monkeypatch.setattr(R.M4, "nominal_validated_tilt", lambda: 5.0)
    A.main(["--print"])
    out = capsys.readouterr().out
    assert "INVALID" not in out and "PASS" in out


def test_resume_allowed_when_head_moved_but_frozen_paths_did_not():
    """Review 6, X2: the realistic resume (HEAD != manifest commit, frozen paths and results folders unchanged)
    runs git and is allowed. ccc6330 -> 769eab2 only added the revision 6 smoke-test folder."""
    old, new = scored._git("rev-parse", "ccc6330"), scored._git("rev-parse", "769eab2")
    m = {"trials": [], "not_run": [], "tables": {}, "environment": ENV, "commit": old,
         "frozen_paths": R.M5_FROZEN_PATHS + scored.FROZEN_PATHS}
    rel = tuple(str(d.relative_to(REPO)).replace("\\", "/") for d in (R.OUT, R.OUT_NOMAG))
    assert R.resume_problems(m, m, new, True, rel) == []
    # the same pair with a frozen path that did change between them is refused (the diff really ran)
    m2 = {**m, "frozen_paths": ["experiments/E5_scored_m5/smoke_rev6_2026-11-16"]}
    assert any("frozen paths differ" in x for x in R.resume_problems(m2, m2, new, True, rel))


@pytest.mark.parametrize("name", ["rest_s99999.json", "rest_s10000-PC.json"])
def test_resume_refused_for_a_json_that_is_not_a_manifest_record(tmp_path, name):
    """Review 6, X3: a .json in an experiment folder must be a manifest trial's record."""
    jobs = _interrupted_run(tmp_path)
    (tmp_path / "results" / "E1-1" / name).write_text("{}")
    with pytest.raises(SystemExit, match="would make the run INVALID"):
        _make(tmp_path, jobs=copy.deepcopy(jobs))


def test_location_problems_flags_onedrive_folders_and_a_foreign_package(tmp_path):
    """Revision 8: the path check and the package check, on synthetic paths."""
    repo = tmp_path / "dev" / "Rubiknetic"
    pkg = repo / "src" / "rubiknetic" / "cube_physics" / "scored.py"
    assert R.location_problems({"repository": repo, "results": repo / "x" / "results"}, pkg, repo, repo) == []
    assert R.location_problems({"OneDriveTemp": tmp_path / "OneDriveTemp"}, pkg, repo, repo) == []
    for name in ("OneDrive", "OneDrive - Org", "ONEDRIVE"):
        probs = R.location_problems({"results": tmp_path / name / "Desktop" / "r"}, pkg, repo, repo)
        assert len(probs) == 1 and "inside a OneDrive folder" in probs[0]
    other = tmp_path / "OneDrive" / "Desktop" / "Rubiknetic"
    probs = R.location_problems({}, other / "src" / "rubiknetic" / "cube_physics" / "scored.py", other, repo)
    assert len(probs) == 1 and "not from" in probs[0]
    assert len(R.location_problems({}, pkg, other, repo)) == 1         # package's own REPO differs


def test_location_problems_follow_links(tmp_path):
    """Revision 8: a link to a OneDrive folder is caught after resolving it."""
    target = tmp_path / "OneDrive" / "results"
    target.mkdir(parents=True)
    link = tmp_path / "dev" / "results"
    link.parent.mkdir()
    link.symlink_to(target, target_is_directory=True)
    repo = tmp_path / "dev"
    pkg = repo / "src" / "rubiknetic" / "x.py"
    assert any("OneDrive" in x for x in R.location_problems({"results": link}, pkg, repo, repo))


def test_this_checkout_passes_the_location_check():
    """Revision 8: the real paths of this working copy (outside OneDrive, package from its own src/)."""
    R.require_local_location(None)


def test_smoke_start_refused_when_the_smoke_folder_is_in_onedrive(monkeypatch, tmp_path):
    _no_real_start(monkeypatch, tmp_path)
    with pytest.raises(SystemExit, match="must not use a OneDrive folder"):
        R.main(["smoke", "--smoke-dir", str(tmp_path / "OneDrive" / "smoke")])
