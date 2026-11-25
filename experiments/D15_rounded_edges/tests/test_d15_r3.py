"""D15 R3 harness tests (fast; no simulation)."""
import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import r3_run as RUN  # noqa: E402
import r3_analyze as AN  # noqa: E402

ENV = {"commit": "test"}


def test_job_lists():
    run, not_run = RUN.all_jobs(ENV)
    seq = [j for j in run if j["d15_kind"] == "seq"]
    rests = [j for j in run if j["d15_kind"] == "rest"]
    assert len(seq) == 58 and len(rests) == 15 and not_run == AN.EXPECTED_NOT_RUN
    assert run[0]["tid"] == "nominal__rest60"                           # gate 2 first
    assert len({j["tid"] for j in run}) == len(run)
    assert {j["kw"]["seed"] for j in seq} == {16000} and {j["seed"] for j in rests} == {16000}
    settings = {j["d15_setting"] for j in seq}
    assert not any(s.startswith("chamfer=") for s in settings)          # replaced by the edge-radius factor
    assert {"edge_radius=0.0018", "edge_radius=0.0036", "noslip=5", "noslip=20", "noslip_ref=0", "nominal"} <= settings
    assert len(settings) + 1 == 30                                      # 29 run + 4x1.5 N35 (not run)
    assert all(sum(j["d15_setting"] == s for j in seq) == 2 for s in settings)
    assert {j["d15_r"] for j in seq} == {0.0018, 0.0025, 0.0036} and {j["d15_n"] for j in seq} == {0, 5, 10, 20}
    assert [j["d15_band"] for j in seq if j["d15_setting"] == "noslip_ref=0"] == [False, False]
    rs = {j["d15_setting"] for j in rests}
    assert rs == {s for s, *_ in RUN.REST_SETTINGS} and len(rs) == 15
    paths = [RUN.job_path(j) for j in run]
    assert len(set(paths)) == len(paths) and all(str(p).startswith(str(RUN.OUT)) for p in paths)


def test_smoke_seeds_outside_the_run():
    sm = RUN.smoke_jobs(ENV)
    seeds = [j["kw"]["seed"] if j["d15_kind"] == "seq" else j["seed"] for j in sm]
    assert all(RUN.SMOKE_SEEDS[0] < s < RUN.SMOKE_SEEDS[1] for s in seeds) and len(set(seeds)) == len(seeds)
    assert all(RUN.job_path(j, RUN.SMOKE_OUT) != RUN.job_path(j) for j in sm)


def _fake_seq(job):
    e = RUN.expected(job)
    params = {k: e[k] for k in ("timestep", "iterations", "joint_frictionloss", "gap", "cubie_friction")}
    params.update(edge_profile="rounded", edge_radius=e["edge_radius"], grip_force=e.get("grip_force", 12.0))
    return {"params": params, "seed": job["kw"]["seed"],
            "magnets": None if e["magnet"] is None else {"params": dict(e["magnet"]), "layout_gap": e["gap"]},
            "setup": {"misalign_deg": {f: 0.0 for f in "URFDLB"}},
            "d15": {"trial_options": {"noslip_iterations": e["noslip"], "timestep": e["timestep"],
                                      "iterations": e["iterations"]},
                    "wrapper_calls": 1 if e["noslip"] else 0, "n_trials_constructed": 1}}


def test_proof_checks():
    run, _ = RUN.all_jobs(ENV)
    by = {j["tid"]: j for j in run}
    for tid in ("nominal__sexy6", "magnet=none__6move", "face_gap_mm=0.35__sexy6", "edge_radius=0.0036__6move",
                "noslip_ref=0__sexy6", "grip_force=50.0__6move", "timestep=0.00025__sexy6"):
        assert RUN.proof_errors(by[tid], _fake_seq(by[tid])) == [], tid
    j = by["edge_radius=0.0036__6move"]
    bad = _fake_seq(j)
    bad["params"]["edge_radius"] = 0.0025                               # a factor that silently did nothing
    assert RUN.proof_errors(j, bad)
    j = by["magnet_scale=0.67__sexy6"]
    bad = _fake_seq(j)
    bad["magnets"]["params"]["scale"] = 1.0
    assert RUN.proof_errors(j, bad)
    j = by["noslip=20__6move"]
    bad = _fake_seq(j)
    bad["d15"]["trial_options"]["noslip_iterations"] = 10
    assert RUN.proof_errors(j, bad)
    j = by["misalign_max_deg=0.0__6move"]
    bad = _fake_seq(j)
    bad["setup"]["misalign_deg"]["U"] = 0.3
    assert RUN.proof_errors(j, bad)


def _rows(flip=None, nominal_fail=False, rest_flip=False):
    run, not_run = RUN.all_jobs(ENV)
    seq = {j["tid"]: {"setting": j["d15_setting"], "seq": j["d15_seq"], "band": j["d15_band"], "pass": True}
           for j in run if j["d15_kind"] == "seq"}
    if flip:
        seq[flip]["pass"] = False
    if nominal_fail:
        seq["nominal__sexy6"]["pass"] = False
    rest = {j["d15_setting"]: {"ok": True} for j in run if j["d15_kind"] == "rest"}
    if rest_flip:
        rest["timestep=0.00075"]["ok"] = False
    return seq, rest, dict(not_run)


def test_signals():
    s = AN.signals(*_rows())
    assert s["complete"] and s["signal_A_nominal"] and s["signal_B_no_flip"] and s["reading"] == "E1-7 rehearsal clean"
    s = AN.signals(*_rows(flip="timestep=0.00075__sexy6"))
    assert s["sequence_flips"] == ["timestep=0.00075__sexy6"] and s["reading"] == "fragilities reported: the user decides"
    s = AN.signals(*_rows(flip="noslip_ref=0__sexy6"))                  # the reference arm is not in the band
    assert s["signal_B_no_flip"] and s["noslip_ref_reported"]["noslip_ref=0__sexy6"] is False
    s = AN.signals(*_rows(rest_flip=True))
    assert s["rest_flips"] == ["timestep=0.00075"] and not s["signal_B_no_flip"]
    s = AN.signals(*_rows(nominal_fail=True))
    assert not s["signal_A_nominal"] and s["reading"] == "nominal failed: result to the user"
    seq, rest, nr = _rows()
    seq.pop("nominal__6move")
    assert AN.signals(seq, rest, nr)["reading"] == "incomplete: result to the user"
    seq, rest, nr = _rows()
    assert AN.signals(seq, rest, {})["complete"] is False              # the V3 "not run" set must match
