"""D14 Stage 3a/3b unit tests (no simulation is stepped). Run (WSL, repo root):
~/.venvs/rubiknetic/bin/python -m pytest -q -p no:cacheprovider experiments/D14_noslip_rest_rehearsal/tests"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]


def _load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


RUN3 = _load("d14s3_run", HERE / "d14s3_run.py")
AN3 = _load("d14s3_analyze", HERE / "d14s3_analyze.py")


@pytest.fixture(scope="module")
def jobs3():
    return RUN3.stage3b_jobs({"commit": "test"})


def test_stage3b_jobs(jobs3):
    assert len(jobs3) == 3 * 98
    assert all(j["d14s3_n"] == 10 for j in jobs3)
    for j in jobs3:
        s = j["kw"]["seed"]
        assert 16000 <= s <= 16655


def test_gate3_is_l0_frozen_first_per_exp(jobs3):
    g = RUN3.gate3_jobs(jobs3)
    assert len(g) == 6 and all(j["er9g_arm"] == "L0" and j["d14s3_n"] == 0 for j in g)
    assert {j["sub"] for j in g} == set(RUN3.EXPS3)


def test_l0_frozen_records_exist(jobs3):
    for j in jobs3:
        if j["er9g_arm"] == "L0":
            assert RUN3.RUN2.frozen_path("L0", j["exp"], j["tid"]).exists()


def test_check_jobs():
    js = RUN3.check_jobs({"commit": "test"}, 20)
    assert len(js) == 3 and all(j["tid"] == "U_s16100" and j["d14s3_n"] == 20 for j in js)


def test_e11_pass_on_stage1_records():
    for arm in ("L0", "PG8", "PG20"):
        for s in (16000, 16013):
            rec = AN3.STAGE1.D13.load_json(AN3.STAGE1.result_path(arm, s))["record"]
            assert AN3.e11_pass(rec)


def test_assemble_counts_before_3b():
    for arm in ("L0", "PG8", "PG20"):
        t = AN3.assemble(arm)
        subs = {}
        for v in t.values():
            subs[v["sub"]] = subs.get(v["sub"], 0) + 1
        assert subs.get("E1-1") == 20 and subs.get("E1-2") == 24 and subs.get("E1-5") == 42 and subs.get("E1-5s") == 20
        assert all(v["pass"] for v in t.values())


def test_wall_ratios_positive():
    r = AN3.arm_wall_ratios()
    assert set(r) == {"L0", "PG8", "PG20"} and all(0.3 < x < 10 for x in r.values())


def test_proof_errors():
    ok = {"d14s3": {"noslip_n": 10, "wrapper_calls": 1, "n_trials_constructed": 1,
                    "trial_options": {"noslip_iterations": 10, "nv": 80}, "magnet_model_noslip_iterations": 0,
                    "magnet_model_nv": 80}}
    assert RUN3.proof_errors(ok) == []
    fz = {"d14s3": {**ok["d14s3"], "noslip_n": 0, "wrapper_calls": 0, "trial_options": {"noslip_iterations": 0, "nv": 80}}}
    assert RUN3.proof_errors(fz) == []
    bad = {"d14s3": {**ok["d14s3"], "wrapper_calls": 2}}
    assert RUN3.proof_errors(bad)
