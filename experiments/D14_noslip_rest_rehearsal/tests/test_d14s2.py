"""D14 Stage 2 unit tests (no simulation is stepped). Run (WSL, repo root):
~/.venvs/rubiknetic/bin/python -m pytest -q -p no:cacheprovider experiments/D14_noslip_rest_rehearsal/tests"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import mujoco
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


RUN = _load("d14s2_run", HERE / "d14s2_run.py")
AN = _load("d14s2_analyze", HERE / "d14s2_analyze.py")


@pytest.fixture(scope="module")
def all_jobs():
    return RUN.jobs({"commit": "test"}, noslip=True)


def test_job_list(all_jobs):
    assert len(all_jobs) == 3 * 86
    for arm in RUN.ARMS:
        got = {e: sum(j["er9g_arm"] == arm and j["exp"] == e for j in all_jobs) for e in RUN.EXPS}
        assert got == RUN.COUNTS
    assert {j["er9g_d_val"] for j in all_jobs if j["er9g_arm"] != "L0"} == {12.0}
    for j in all_jobs:
        s = j["kw"]["seed"]
        assert 16000 <= s <= 16999 and not 16700 <= s <= 16739 and not 16900 <= s <= 16999
        assert j["d14s2_noslip"] is True


def test_gate_jobs_are_first_per_arm_and_exp(all_jobs):
    g = RUN.gate_jobs(all_jobs)
    assert len(g) == 9 and all(j["d14s2_noslip"] is False for j in g)
    assert {(j["er9g_arm"], j["exp"]) for j in g} == {(a, e) for a in RUN.ARMS for e in RUN.EXPS}


def test_frozen_records_exist_and_pair(all_jobs):
    for j in all_jobs:
        p = RUN.frozen_path(j["er9g_arm"], j["exp"], j["tid"])
        assert p.exists()


def test_frozen_turner_stats_reproduce_probe_report():
    rep = json.loads((RUN.E9 / "results/hybrid_g/probe/report.json").read_text())
    ER9 = RUN.er9()
    for arm in ("PG8", "PG20"):
        recs = [RUN.load_rec(p) for p in sorted((RUN.E9 / "results/hybrid_g/probe" / arm / "E1-2").glob("*.json.gz"))]
        mine = ER9.turner_stats(recs)
        ref = rep["arms"][arm]["turner_E1-2_Nm"]
        assert mine["median"] == ref["median"] and mine["max"] == ref["max"]


def test_decay_models_compile_with_and_without_noslip():
    for kind in ("A_hinge", "B_ball"):
        for ns in (0, 10):
            m = mujoco.MjModel.from_xml_string(RUN._iso_xml(kind, ns))
            assert m.opt.noslip_iterations == ns and m.nv in (1, 3)
            assert m.dof_frictionloss[0] > 0 and m.dof_damping[0] > 0


def test_proof_errors():
    ok = {"d14s2": {"noslip": True, "wrapper_calls": 1, "n_trials_constructed": 1,
                    "trial_options": {"noslip_iterations": 10, "nv": 80}, "magnet_model_noslip_iterations": 0,
                    "magnet_model_nv": 80}}
    assert RUN.proof_errors(ok) == []
    bad = json.loads(json.dumps(ok))
    bad["d14s2"]["trial_options"]["noslip_iterations"] = 0
    assert RUN.proof_errors(bad)
    gate = json.loads(json.dumps(ok))
    gate["d14s2"].update({"noslip": False, "wrapper_calls": 0})
    gate["d14s2"]["trial_options"]["noslip_iterations"] = 0
    assert RUN.proof_errors(gate) == []


def test_stall_descriptors_synthetic():
    t = [i * 0.005 for i in range(200)]
    turner = [min(90.0, i * 1.0) for i in range(200)]
    layer = [min(90.0, max(0.0, i * 1.0 - 2.0)) if not 20 <= i < 40 else 18.0 for i in range(200)]
    rec = {"trial_id": "U_s16100", "d14s2": {"series": {
        "t": t, "turner_deg": [[x, 0, 0, 0, 0, 0] for x in turner], "turner_Nm": [[0] * 6] * 200,
        "layer_deg": [[x, 0, 0, 0, 0, 0] for x in layer], "pad_contacts": [4] * 200}}}
    s = AN.stall_descriptors(rec)
    assert s["move_found"] and s["reached_85"] and s["n_stall_episodes"] == 1
    assert abs(s["longest_stall_s"] - 0.1) < 0.03
    assert s["max_pad_slip_deg"] > 20
