"""D14 unit tests. Run (WSL, repo root):
~/.venvs/rubiknetic/bin/python -m pytest -q -p no:cacheprovider experiments/D14_noslip_rest_rehearsal/tests"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def _load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


RUN = _load("d14_run", HERE / "d14_run.py")
AN = _load("d14_analyze", HERE / "d14_analyze.py")


def test_runs_seeds_setting():
    assert len(RUN.all_runs()) == 60
    assert set(RUN.GATE) <= set(RUN.all_runs())
    assert RUN.CFG == {"noslip_iterations": 10}
    assert all(16000 <= s <= 16019 for _, s in RUN.all_runs())


def test_gate_cases_are_d13_v2_records():
    for (arm, seed), case in RUN.GATE.items():
        assert RUN.D13.CASES[case][:2] == (arm, seed)
        assert RUN.D13.result_path("V2", case).exists()


def test_frozen_records_exist():
    for arm, seed in RUN.all_runs():
        assert RUN.committed_frozen_path(arm, seed).exists()


def test_validity_on_d13_v2_record():
    r = RUN.D13.load_json(RUN.D13.result_path("V2", "C1"))      # PG8, noslip, class stats recorded
    v = AN.validity("PG8", {**r, "d_val_deg": 12.0})
    assert v["out_of_regime"] is False


def _m(arm="PG8", seed=16000, rest=0.01, ev=0, oor=False, ab=None, ns=10):
    return {"arm": arm, "seed": seed, "rest10_deg": rest, "n_events": ev, "aborted": ab, "numerical_failures": [],
            "validity": {"out_of_regime": oor}, "noslip_iterations": ns, "frozen": {"rest10_deg": 0.1, "n_events": 0}}


def test_arm_signal():
    good = [_m(seed=s) for s in RUN.SEEDS]
    assert AN.arm_signal(good)["signal_met"]
    assert not AN.arm_signal(good[:-1] + [None])["signal_met"]                      # incomplete
    assert not AN.arm_signal(good[:-1] + [_m(seed=16019, ev=1)])["signal_met"]      # slip
    assert not AN.arm_signal(good[:-1] + [_m(seed=16019, rest=0.51)])["signal_met"]
    assert not AN.arm_signal(good[:-1] + [_m(seed=16019, oor=None)])["signal_met"]  # PG stats missing
    assert not AN.arm_signal(good[:-1] + [_m(seed=16019, ab="x")])["signal_met"]
    assert not AN.arm_signal(good[:-1] + [_m(seed=16019, ns=0)])["signal_met"]
    l0 = [_m(arm="L0", seed=s, oor=None) for s in RUN.SEEDS]
    assert AN.arm_signal(l0)["signal_met"]                                          # L0: legacy stats only
