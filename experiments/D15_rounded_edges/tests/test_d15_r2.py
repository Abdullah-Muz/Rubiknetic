"""D15 R2 harness tests (fast; no long simulation)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import r2_run as RUN  # noqa: E402
import r2_analyze as AN  # noqa: E402


def test_job_lists():
    env = RUN.D13.environment()
    g, m = RUN.gate_jobs(env), RUN.main_jobs(env)
    assert len(g) == 3 and all(j["d15_gate"] and j["tid"] == "U_s16100" and j["d15_r"] == RUN.R for j in g)
    assert len(m) == 3 * (20 + 98)
    for arm in RUN.ARMS:
        rests = [j for j in m if j["d15_kind"] == "rest" and j["arm"] == arm]
        assert sorted(j["seed"] for j in rests) == list(RUN.REST_SEEDS)
        seq = [j for j in m if j["d15_kind"] == "seq" and j["er9g_arm"] == arm]
        assert {e: sum(j["sub"] == e for j in seq) for e in RUN.EXPS3} == RUN.COUNTS3
    assert all(j["d15_r"] == 0.0025 and j["d15_tag"] == "R25" for j in m)
    assert m[0]["d15_kind"] == "seq" and m[0]["sub"] == "E1-4" and m[0]["er9g_arm"] == "PG20"   # longest first
    paths = [RUN.job_path(j) for j in g + m]
    assert len(set(paths)) == len(paths) and all(str(p).startswith(str(RUN.OUT)) for p in paths)
    seeds = {j["seed"] if j["d15_kind"] == "rest" else j["kw"]["seed"] for j in m}
    assert all(16000 <= s <= 16655 for s in seeds)


def test_reused_r1_records_complete():
    reuse = RUN.reused_files()
    assert all(len(v) == 86 for v in reuse.values())


def test_signal1_rule():
    good = {s: {"n_events": 0, "rest_deg": 0.01, "integrity_ok": True, "out_of_regime": False, "rest_s": 60.0}
            for s in RUN.REST_SEEDS}
    assert AN.signal1(good, "PG20")["signal_met"]
    bad = dict(good); bad[16003] = {**good[16003], "n_events": 1}
    assert not AN.signal1(bad, "PG20")["signal_met"]
    short = {s: {**v, "rest_s": 10.0} for s, v in good.items()}
    assert not AN.signal1(short, "L0")["signal_met"]
    oor = dict(good); oor[16000] = {**good[16000], "out_of_regime": None}
    assert not AN.signal1(oor, "PG8")["signal_met"] and AN.signal1(oor, "L0")["signal_met"]


def test_expected_counts():
    assert AN.A7.EXPECTED == {"E1-1": 20, "E1-2": 24, "E1-3": 22, "E1-4": 40, "E1-5": 42, "E1-5s": 20, "E1-6a": 6,
                              "E1-6b": 6, "E1-6c": 8, "E1-6t": 16}
