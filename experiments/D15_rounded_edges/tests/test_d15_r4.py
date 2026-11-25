"""D15 R4 harness tests (fast; no simulation)."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import r4_run as RUN  # noqa: E402
import r4_analyze as AN  # noqa: E402

ENV = {"commit": "test"}


def _seed(j):
    return j["seed"] if j["d15_kind"] == "rest" else j["kw"]["seed"]


def test_main_list():
    m = RUN.main_jobs(ENV)
    assert len(m) == 204 and {j["sub"]: sum(x["sub"] == j["sub"] for x in m) for j in m} == RUN.EXPECTED
    assert all(19000 <= _seed(j) <= 19655 for j in m)
    assert sorted(_seed(j) for j in m if j["sub"] == "E1-1") == list(AN.REST_SEEDS)
    assert all(j["d15_r"] == 0.0025 and j["d15_n"] == 10 for j in m)
    assert all(j["d15_rest_s"] == 60.0 for j in m if j["d15_kind"] == "rest")
    assert len({RUN.job_path(j) for j in m}) == 204 and all(str(RUN.job_path(j)).startswith(str(RUN.OUT)) for j in m)
    assert m[0]["sub"] == "E1-4"                                         # longest first


def test_same_trials_as_rehearsal_shifted():
    """The R4 list is M5's list with every seed + 9000; the rehearsal list is the same with + 6000."""
    a, b = RUN.option_a(ENV, "r4"), RUN.option_a(ENV, "er7")
    assert [(x["exp"], x["sub"], x["kind"]) for x in a] == [(y["exp"], y["sub"], y["kind"]) for y in b]
    assert all(x["kw"]["seed"] - y["kw"]["seed"] == 3000 for x, y in zip(a, b))
    scr_a = [x["kw"]["moves"] for x in a if x["sub"] == "E1-4" and "scr" in x["tid"]]
    scr_b = [y["kw"]["moves"] for y in b if y["sub"] == "E1-4" and "scr" in y["tid"]]
    assert len(scr_a) == 20 and not set(scr_a) & set(scr_b)             # fresh scrambles


def test_gate_list():
    g = RUN.gate_jobs(ENV)
    assert len(g) == 10 and all(j["d15_gate"] for j in g) and all(16000 <= _seed(j) <= 16655 for j in g)
    assert all(RUN.ref_path(j).exists() for j in g)
    assert all(str(RUN.job_path(j)).startswith(str(RUN.OUT / "gate")) for j in g)


def test_seed_guard():
    for s in (10000, 10655, 17000, 17999):
        with pytest.raises(SystemExit):
            RUN.check_seed(s)
    with pytest.raises(SystemExit):
        RUN.check_seed(16000)                                            # outside R4's range in run mode
    assert RUN.check_seed(16950, smoke=True) == 16950 and RUN.check_seed(19000) == 19000


def _rows(slip=False, fail=None, missing=False):
    rows1 = {s: {"e11_pass": True, "n_events": 0, "rest_deg": 0.01, "integrity_ok": True, "out_of_regime": None,
                 "rest_s": 60.0, "wall_s": 1.0} for s in AN.REST_SEEDS}
    if slip:
        rows1[19003]["n_events"] = 1
    recs = {}
    for e, n in RUN.EXPECTED.items():
        if e == "E1-1":
            continue
        for i in range(n - (1 if missing and e == "E1-2" else 0)):
            pm = [{"e16m_P_ok": True}] if e in AN.SEQ_SUBS else []
            recs[(e, f"{e}_{i}")] = {"sub_experiment": e, "trial_id": f"{e}_{i}", "pass": True, "per_move": pm}
    if fail:
        recs[fail]["pass"] = False
        recs[fail]["fail_reasons"] = ["M1 criteria"]
    return rows1, recs


def test_verdict():
    v = AN.verdict(*_rows())
    assert v["complete"] and v["signals"]["all_met"] and v["reading"].startswith("meets")
    v = AN.verdict(*_rows(slip=True))                                    # the slip rule fails E1-1 (P-86 Q4)
    assert not v["signals"]["all_met"] and v["rows"]["E1-1"]["failed"] == ["rest_s19003"]
    v = AN.verdict(*_rows(fail=("E1-4", "E1-4_7")))
    assert not v["signals"]["2_option_a_with_slip_rule"] and v["reading"].startswith("signal(s) missed")
    v = AN.verdict(*_rows(missing=True))
    assert not v["complete"] and v["reading"].startswith("incomplete")
