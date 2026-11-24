"""D15 R1 harness tests (fast; no long simulation)."""
import dataclasses
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import r1_run as RUN  # noqa: E402
import r1_analyze as AN  # noqa: E402


def test_job_list():
    env = RUN.D13.environment()
    js = RUN.all_jobs(env)
    assert len(js) == 636
    for tag, r in RUN.RADII.items():
        for arm in RUN.ARMS:
            rest = [j for j in js if j["d15_tag"] == tag and j["d15_kind"] == "rest" and j["arm"] == arm]
            seq = [j for j in js if j["d15_tag"] == tag and j["d15_kind"] == "seq" and j["er9g_arm"] == arm]
            assert sorted(j["seed"] for j in rest) == list(RUN.REST_SEEDS)
            assert {e: sum(j["sub"] == e for j in seq) for e in RUN.SEQ_EXPS} == RUN.SEQ_COUNTS
            assert all(j["d15_r"] == r for j in rest + seq)
            assert all(j["d14s3_n"] == RUN.NOSLIP for j in seq)
    assert [j["d15_tag"] for j in js][0] == "R25"                      # R25 first
    paths = [RUN.job_path(j) for j in js]
    assert len(set(paths)) == len(paths)
    assert all(str(p).startswith(str(RUN.OUT)) for p in paths)
    seeds = {j["seed"] if j["d15_kind"] == "rest" else j["kw"]["seed"] for j in js}
    assert all(16000 <= s <= 16655 for s in seeds)


def test_edge_trial_sets_params():
    from rubiknetic.cube_physics import scored
    from rubiknetic.cube_physics.m1_model import M1Params
    orig = scored.Trial
    captured = {}

    class Fake:
        def __init__(self, params, *a, **k):
            captured["p"] = params
    scored.Trial = Fake
    try:
        RUN.install_edge(scored, 0.0025)
        scored.Trial(M1Params(gap=5e-05, radial_preload=0.0), None)
    finally:
        scored.Trial = orig
    p = captured["p"]
    assert p.edge_profile == "rounded" and p.edge_radius == 0.0025 and p.gap == 5e-05


def test_edge_errors():
    assert RUN.edge_errors({"edge_profile": "rounded", "edge_radius": 0.0014}, 0.0014) == []
    assert RUN.edge_errors({}, 0.0014)
    assert RUN.edge_errors({"edge_profile": "rounded", "edge_radius": 0.0025}, 0.0014)


@pytest.mark.parametrize("meets,want", [({"R25": True, "R14": True}, "R25"), ({"R25": True, "R14": False}, "R25"),
                                        ({"R25": False, "R14": True}, "R14"), ({"R25": False, "R14": False}, None)])
def test_selection_rule(meets, want):
    assert AN.select(meets) == want


def test_code_check_lists_protocol_files():
    import inspect
    src = inspect.getsource(RUN.code_is_committed)
    for f in ("PROTOCOL_R1.md", "r1_run.py", "r1_analyze.py", "m1_model.py"):
        assert f in src
