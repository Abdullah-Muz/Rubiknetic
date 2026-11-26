"""M7 scored runner and verdict script (experiments/E7_scored_m7; PHASE_1_M7_PREREGISTRATION.md section 6.1).
Fast: no simulation. The runner's module globals are M7's own (isolated from M5's instance)."""
import glob
import gzip
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


E7 = _load("e7_scored_m7_run", REPO / "experiments/E7_scored_m7/run.py")
AN = _load("e7_scored_m7_analyze", REPO / "experiments/E7_scored_m7/analyze.py")
R, M4 = E7.R, E7.M4
EXPECTED = {"E1-1": 20, "E1-2": 24, "E1-3": 22, "E1-4": 40, "E1-5": 42, "E1-5s": 20, "E1-6a": 6, "E1-6b": 6,
            "E1-6c": 8, "E1-6t": 16}


@pytest.fixture(scope="module")
def jobs():
    return R.build_m5_jobs("test", {}, M4.nominal_validated_tilt())


def test_isolated_from_m5():
    assert R.__name__ == "e5_scored_m5_run_for_m7" and M4.__name__ == "e4_scored_m4_run_for_m7"
    assert M4.SCORED_SEED_RANGE == (17000, 17999) and R.SMOKE_SEED_BASE == 18000
    assert E7._M5["SCORED_SEED_RANGE"] == (10000, 10999)
    assert R.OUT == E7.HERE / "results" and R.M5_FROZEN_PATHS is E7.M7_FROZEN_PATHS


def test_counts(jobs):
    mag = [j for j in jobs if j["magnets"]]
    got = {e: sum(j["sub"] == e for j in mag) for e in EXPECTED}
    assert got == EXPECTED
    assert sum(not j["magnets"] for j in jobs) == 184
    e17 = [j for j in jobs if j["exp"] == "E1-7"]
    assert len(e17) == 60 + 15 and sum(j["kind"] == "rest60" for j in e17) == 15
    assert sum(j["exp"] == "REST-X" for j in jobs) == 40
    assert len(jobs) == 204 + 184 + 75 + 40
    run, not_run, refused = R.prepare([dict(j) for j in jobs])
    assert len(run) == 501 and not refused
    assert sorted(j["tid"] for j, _ in not_run) == ["magnet=4x1.5_N35__6move", "magnet=4x1.5_N35__sexy6"]


def test_seeds(jobs):
    from rubiknetic.cube_logic import invert, random_scramble
    for j in jobs:
        s = j["kw"]["seed"]
        if j["exp"] == "REST-X":
            assert 17700 <= s <= 17739
        else:
            assert 17000 <= s <= 17655, (j["tid"], s)
    assert sorted(j["kw"]["seed"] for j in jobs if j["exp"] == "REST-X") == list(range(17700, 17740))
    assert {j["kw"]["seed"] for j in jobs if j["exp"] == "E1-7"} == {17000}
    assert sorted(j["kw"]["seed"] for j in jobs if j["sub"] == "E1-1" and j["magnets"]) == list(range(17000, 17020))
    scr = [j for j in jobs if j["sub"] == "E1-4" and j["tid"].startswith("scr20inv_") and j["magnets"]]
    assert len(scr) == 20 and all(17400 <= j["kw"]["seed"] <= 17419 for j in scr)
    for j in scr:
        sc = random_scramble(20, j["kw"]["seed"])
        assert j["kw"]["moves"] == " ".join(str(m) for m in sc + invert(sc))


def test_m5_list_plus_7000(jobs):
    """Every M5-derived job is M5's job with the seed + 7000 (rest kinds renamed rest60)."""
    E7.set_seed_map(0, (10000, 10999))
    try:
        m5 = E7._m5_build("test", {}, M4.nominal_validated_tilt())
    finally:
        E7.set_seed_map(E7.SEED_PLUS, (17000, 17999))
    m7 = {R.key_of(j): j for j in jobs}
    assert len(m5) == 204 + 184 + 60                                     # E1-7 already carries M7's factors
    for j in m5:
        arm, exp, tid = R.key_of(j)
        s = j["kw"]["seed"]
        if tid.endswith(f"_s{s}"):                                       # trial IDs carry their seed
            tid = tid[: -len(f"_s{s}")] + f"_s{s + 7000}"
        k = (arm, exp, tid)
        assert k in m7, k
        assert m7[k]["kw"]["seed"] == j["kw"]["seed"] + 7000
        assert m7[k]["kind"] == ("rest60" if j["kind"] == "rest" else j["kind"])


def test_e17_factors(jobs):
    f = dict(M4.E17_FACTORS)
    assert "chamfer" not in f and f["edge_radius"] == [0.0018, 0.0025, 0.0036] and f["noslip"] == [0, 5, 10, 20]
    assert ("edge_radius", 0.0025) in M4.NOMINAL and ("noslip", 10) in M4.NOMINAL
    tags = {j["tid"].split("__")[0] for j in jobs if j["exp"] == "E1-7"}
    assert {"edge_radius=0.0018", "edge_radius=0.0036", "noslip=0", "noslip=5", "noslip=20", "nominal"} <= tags
    assert not any(t.startswith("chamfer") for t in tags)
    rests = {j["tid"] for j in jobs if j["exp"] == "E1-7" and j["kind"] == "rest60"}
    assert "nominal__rest60" in rests and "magnet_scale=0.67__rest60" in rests and len(rests) == 15


def test_e11_kind(jobs):
    assert all(j["kind"] == "rest60" for j in jobs if j["sub"] in ("E1-1", "REST-X"))
    assert not any(j["kind"] == "rest" for j in jobs)


def test_e11_pass_equals_d14():
    an3 = _load("d14s3_analyze", REPO / "experiments/D14_noslip_rest_rehearsal/d14s3_analyze.py")
    files = sorted(glob.glob(str(REPO / "experiments/D15_rounded_edges/results/r4/L0/E1-1/*.json.gz")))[:5]
    assert files
    for f in files:
        rec = json.loads(gzip.decompress(Path(f).read_bytes()))["record"]
        assert E7.e11_pass(rec) == an3.e11_pass(rec)
        bad = dict(rec, rest_rotation_deg=0.51)
        assert E7.e11_pass(bad) is False and an3.e11_pass(bad) is False


def test_run_trial_installs_and_consumes(monkeypatch):
    from rubiknetic.cube_physics import scored
    seen = {}

    def fake(kind, kw, magnets_on):
        seen["kw"], seen["trial"], seen["xml"] = kw, scored.Trial, scored.build_m1_xml
        return {"pass": True}, None, None
    monkeypatch.setattr(E7, "_m4_run_trial", fake)
    rec, _, _ = E7.run_trial("seq", {"moves": "U", "seed": 1, "overrides": {"gap": 5e-5, "edge_radius": 0.0036,
                                                                            "noslip": 5}}, True)
    assert seen["kw"]["overrides"] == {"gap": 5e-5}
    assert seen["trial"] is not E7._ORIG["trial"] and issubclass(seen["trial"], E7._ORIG["trial"])
    assert seen["xml"] is not E7._ORIG["xml"]
    assert rec["m7"]["edge_radius"] == 0.0036 and rec["m7"]["noslip"] == 5
    E7.run_trial("seq", {"moves": "U", "seed": 1, "overrides": {"noslip": 0}}, True)
    assert seen["xml"] is E7._ORIG["xml"]                                # NoSlip 0: unwrapped
    E7.run_trial("seq", {"moves": "U", "seed": 1}, True)
    assert seen["xml"] is not E7._ORIG["xml"]                            # default NoSlip 10
    scored.Trial, scored.build_m1_xml = E7._ORIG["trial"], E7._ORIG["xml"]


def _good_seq():
    return {"spec": {"overrides": {"gap": 5e-5}}, "params": {"edge_profile": "rounded", "edge_radius": 0.0025},
            "m7": {"edge_radius": 0.0025, "noslip": 10, "kind": "seq", "n_trials": 1, "noslip_wrapper_calls": 1,
                   "options": {"noslip_iterations": 10}}}


def test_m7_record_checks():
    k = ("magnets", "E1-2", "U_s17100")
    assert AN.m7_record_problems(k, _good_seq()) == []
    r = _good_seq()
    r["params"]["edge_radius"] = 0.0014
    assert AN.m7_record_problems(k, r)
    r = _good_seq()
    r["m7"]["options"]["noslip_iterations"] = 0
    assert AN.m7_record_problems(k, r)
    r = _good_seq()
    r["m7"]["n_trials"] = 2
    assert AN.m7_record_problems(k, r)
    r = _good_seq()
    r["spec"]["overrides"]["edge_radius"] = 0.0018                      # an E1-7 edge setting the trial ignored
    assert AN.m7_record_problems(("magnets", "E1-7", "edge_radius=0.0018__6move"), r)


def test_rest_verdict_rederived():
    f = sorted(glob.glob(str(REPO / "experiments/D15_rounded_edges/results/r4/L0/E1-1/*.json.gz")))[0]
    rec = json.loads(gzip.decompress(Path(f).read_bytes()))["record"]
    ok = E7.e11_pass(rec) and not E7.D13A.events(rec)
    r = dict(rec, spec={"overrides": {"gap": 5e-5}}, params={**rec["params"]}, rest_s=60.0, pass_m1_criteria=ok,
             n_slip_events=0, m7={"edge_radius": 0.0025, "noslip": 10, "kind": "rest60"})
    k = ("magnets", "E1-1", "rest_s17000")
    assert AN.m7_record_problems(k, r) == []
    assert AN.m7_record_problems(k, dict(r, pass_m1_criteria=not ok))  # a stored flag that disagrees
    assert AN.m7_record_problems(k, dict(r, rest_s=10.0))


def test_mechanism_check_replaces_m5s():
    """M5's script flags any label but "M5"; M7's wrapper removes that message for "M7" and flags anything else."""
    assert AN.A.check_records is AN.check_records
    man = {"trials": [{"arm": "magnets", "exp": "E1-2", "tid": t, "seed": 17100, "overrides": {"gap": 5e-5}}
                      for t in ("a", "b")], "not_run": [], "environment": {}, "commit": "c", "tables": {}}
    recs = {("magnets", "E1-2", "a"): {**_good_seq(), "mechanism": "M7"},
            ("magnets", "E1-2", "b"): {**_good_seq(), "mechanism": "M5"}}
    st = {"violations": [], "records": recs, "manifest": man}
    AN.check_records(st, None, True)
    mech = [x for x in st["violations"] if "mechanism" in x]
    assert mech == ["magnets/E1-2/b: mechanism 'M5' (M7 expected)"]


def test_frozen_paths():
    fp = set(E7.M7_FROZEN_PATHS)
    for p in ("experiments/E5_scored_m5/run.py", "experiments/E5_scored_m5/analyze.py", "experiments/E4_scored_m4/run.py",
              "src/rubiknetic/cube_physics/m1_model.py", "experiments/D13_rest_slip_mechanism/d13_run.py",
              "experiments/D10_m5_rest_diagnostic/d10_rest.py", "experiments/D11_rest_slip_count/d11_analyze.py",
              "experiments/PHASE_1_M7_PREREGISTRATION.md", "experiments/E7_scored_m7/run.py",
              "experiments/E7_scored_m7/analyze.py"):
        assert p in fp, p


def test_selfcheck_list():
    js = E7.selfcheck_jobs({})
    assert len(js) == 15 and all(16000 <= j["kw"]["seed"] <= 16999 for j in js)
    assert all(E7.selfcheck_ref(j).exists() for j in js)
    assert M4.SCORED_SEED_RANGE == (17000, 17999)                        # restored after the self-check build


def test_clopper_pearson():
    assert AN.clopper_pearson_upper(0, 60) == pytest.approx(0.0596, abs=5e-4)
    assert AN.clopper_pearson_upper(60, 60) == 1.0
