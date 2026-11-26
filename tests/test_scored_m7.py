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
    """On all 20 R4 rest records, and with each of e11_pass's seven conditions broken in turn (review 1, O5)."""
    an3 = _load("d14s3_analyze", REPO / "experiments/D14_noslip_rest_rehearsal/d14s3_analyze.py")
    from rubiknetic.cube_physics import scored
    th = scored.THRESHOLDS
    assert E7.E11_THRESH == {k: th[k] for k in E7.E11_THRESH}           # the same limits as M1's
    files = sorted(glob.glob(str(REPO / "experiments/D15_rounded_edges/results/r4/L0/E1-1/*.json.gz")))
    assert len(files) == 20
    breaks = [{"integrity_ok": False}, {"aborted": "x"}, {"t0_solved": False}, {"final_solved": False},
              {"rest_rotation_deg": 0.5001}, {"penetration_mm": 0.5001}, {"radial_offset_mm_t0": 0.5001}]
    for f in files:
        rec = json.loads(gzip.decompress(Path(f).read_bytes()))["record"]
        assert E7.e11_pass(rec) == an3.e11_pass(rec) is True
        for b in breaks:
            bad = {**rec, **b}
            assert E7.e11_pass(bad) is False and an3.e11_pass(bad) is False, b


@pytest.fixture
def restore_scored():
    """Whatever a test installs, scored.Trial and scored.build_m1_xml are restored afterwards (review 1, O12)."""
    from rubiknetic.cube_physics import scored
    E7.install(E7.EDGE_R, 0)                                             # make sure _ORIG holds the originals
    orig = (E7._ORIG["trial"], E7._ORIG["xml"])
    try:
        yield scored
    finally:
        scored.Trial, scored.build_m1_xml = orig


def test_run_trial_installs_and_consumes(monkeypatch, restore_scored):
    scored = restore_scored
    from rubiknetic.cube_physics.m1_model import M1Params
    seen = {}

    def fake(kind, kw, magnets_on):
        seen["kw"], seen["trial"], seen["xml"] = kw, scored.Trial, scored.build_m1_xml
        seen["xml_text"] = scored.build_m1_xml(M1Params())
        return {"pass": True}, None, None
    monkeypatch.setattr(E7, "_m4_run_trial", fake)
    rec, _, _ = E7.run_trial("seq", {"moves": "U", "seed": 1, "overrides": {"gap": 5e-5, "edge_radius": 0.0036,
                                                                            "noslip": 5}}, True)
    assert seen["kw"]["overrides"] == {"gap": 5e-5}
    assert issubclass(seen["trial"], E7._ORIG["trial"]) and seen["trial"].m7_edge_radius == 0.0036
    assert 'noslip_iterations="5"' in seen["xml_text"]
    assert rec["m7"]["edge_radius"] == 0.0036 and rec["m7"]["noslip"] == 5
    E7.run_trial("seq", {"moves": "U", "seed": 1, "overrides": {"noslip": 0}}, True)
    assert seen["xml"] is E7._ORIG["xml"] and "noslip_iterations" not in seen["xml_text"]   # NoSlip 0: unwrapped
    E7.run_trial("seq", {"moves": "U", "seed": 1}, True)
    assert 'noslip_iterations="10"' in seen["xml_text"] and seen["trial"].m7_edge_radius == 0.0025   # defaults


def test_m7trial_passes_rounded_edge_to_the_base(monkeypatch, restore_scored):
    """The subclass hands the base the rounded profile and the radius (as r1_run.install_edge)."""
    scored = restore_scored
    from rubiknetic.cube_physics.m1_model import M1Params
    got = {}

    class Stub:
        def __init__(self, params, *a, **k):
            got["p"] = params
            raise RuntimeError("stop before building a model")
    monkeypatch.setitem(E7._ORIG, "trial", Stub)
    E7.install(0.0018, 0)
    with pytest.raises(RuntimeError):
        scored.Trial(M1Params())
    assert got["p"].edge_profile == "rounded" and got["p"].edge_radius == 0.0018


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
    assert len(js) == 17 and all(16000 <= j["kw"]["seed"] <= 16999 for j in js)
    assert all(E7.selfcheck_ref(j).exists() for j in js)
    assert M4.SCORED_SEED_RANGE == (17000, 17999)                        # restored after the self-check build


def test_clopper_pearson():
    assert AN.clopper_pearson_upper(0, 60) == pytest.approx(0.0596, abs=5e-4)       # two-sided 95 % (about 6 %)
    assert AN.clopper_pearson_upper(60, 60) == 1.0


# ---- review 1 additions -----------------------------------------------------------------------------------------------
def _job(jobs, tid, exp=None, magnets=True):
    return next(j for j in jobs if j["tid"] == tid and j["magnets"] == magnets and (exp is None or j["exp"] == exp))


def test_harness_exception_records_are_failing_not_invalid(jobs):
    """Review 1, R1 / B-R3: M5's exception record (no edge, no m7 block) is a failing trial, never a violation."""
    for tid, exp in (("U_s17100", "E1-2"), ("rest_s17000", "E1-1"), ("noslip=0__6move", "E1-7"),
                     ("rest_s17700", "REST-X"), ("timestep=0.00075__rest60", "E1-7")):
        j = dict(_job(jobs, tid, exp), commit="c", startup=None, magnet_info=None)
        rec = R.exception_record(j, ValueError("boom"))
        assert rec["pass"] is False and rec.get("harness_exception")
        assert AN.m7_record_problems(R.key_of(j), rec) == [], tid
        assert AN.m7_record_problems(R.key_of(j), {**rec, "pass": True})  # an exception record may not pass


def test_m7_record_checks_more_cases():
    k = ("magnets", "E1-7", "noslip=0__6move")
    r = _good_seq()
    r["spec"]["overrides"]["noslip"] = 0
    r["m7"].update(noslip=0, noslip_wrapper_calls=1, options={"noslip_iterations": 0})
    assert AN.m7_record_problems(k, r)                                   # NoSlip 0 must not call the wrapper
    r["m7"]["noslip_wrapper_calls"] = 0
    assert AN.m7_record_problems(k, r) == []
    r = _good_seq()
    r["params"]["edge_profile"] = "chamfer"                              # right radius, wrong profile
    assert AN.m7_record_problems(("magnets", "E1-2", "U_s17100"), r)


@pytest.fixture(scope="module")
def r4_rest():
    f = REPO / "experiments/D15_rounded_edges/results/r4/L0/E1-1/rest_s19000.json.gz"
    return json.loads(gzip.decompress(f.read_bytes()))["record"]


def _with_slip(rec, size=0.3):
    rec = json.loads(json.dumps(rec))
    rows = rec["timeseries"]["rot_deg"]["U"]
    for i in range(1200, len(rows)):                                     # a 0.3 deg step at about 30 s
        rows[i][0] += size
    return rec


def _rest60_capture(monkeypatch, scored, rec):
    seen = {"warm": [], "rest": []}

    def warm(kind, kw, magnets_on):
        seen["warm"].append((kind, scored.Trial, scored.build_m1_xml))
        return {"rest_rotation_deg": 0.1, "pass": True, "fail_reasons": [], "seed": kw["seed"]}, None, None

    def d13_rest(sc, d10, seed, ms, cfg, duration_s=None):
        seen["rest"].append((sc.Trial, sc.build_m1_xml, cfg, duration_s, seed))
        return json.loads(json.dumps(rec)), None
    monkeypatch.setattr(E7, "_m4_run_trial", warm)
    monkeypatch.setattr(E7.D13, "d13_rest", d13_rest)
    monkeypatch.setattr(M4, "magnet_availability", lambda mp: {"table_file": "t"})
    monkeypatch.setattr(M4, "use_magnets", lambda mp, gap: None)
    return seen


def test_rest60_path(monkeypatch, restore_scored, r4_rest):
    """Review 1, B-R6: overrides consumed on the rest path; warm-up and rest with the edge and the unwrapped XML; the
    rest's NoSlip from cfg; 60 s; the stored verdict."""
    seen = _rest60_capture(monkeypatch, restore_scored, r4_rest)
    rec, _, _ = E7.run_trial("rest60", {"seed": 19000, "overrides": {"gap": 5e-5, "edge_radius": 0.0036, "noslip": 20,
                                                                     "magnet_scale": 0.67}}, True)
    (kind, wt, wx), = seen["warm"]
    (rt, rx, cfg, dur, seed), = seen["rest"]
    assert kind == "rest" and wt.m7_edge_radius == 0.0036 and rt.m7_edge_radius == 0.0036
    assert wx is E7._ORIG["xml"] and rx is E7._ORIG["xml"]               # d13_rest applies NoSlip itself
    assert cfg == {"noslip_iterations": 20, "params": {"gap": 5e-5}} and dur == 60.0 and seed == 19000
    assert rec["m7"] == {"edge_radius": 0.0036, "noslip": 20, "kind": "rest60"} and rec["rest_s"] == 60.0
    assert rec["pass"] is True and rec["n_slip_events"] == 0 and rec["ok_e11"] is True
    assert rec["warmup_10s"]["rest_rotation_deg"] == 0.1


def test_rest60_slip_fails(monkeypatch, restore_scored, r4_rest):
    _rest60_capture(monkeypatch, restore_scored, _with_slip(r4_rest))
    rec, _, _ = E7.run_trial("rest60", {"seed": 19000, "overrides": {"gap": 5e-5}}, True)
    assert rec["pass"] is False and rec["ok_no_slip"] is False and rec["n_slip_events"] >= 1
    assert rec["ok_e11"] is True and any("slip event" in x for x in rec["e11_fail_reasons"])


def test_every_job_installs_its_registered_edge_and_noslip(jobs, monkeypatch, restore_scored, r4_rest):
    """Review 1, O1: all 501 runnable jobs through run_trial with stand-ins (no simulation)."""
    scored = restore_scored
    seen = _rest60_capture(monkeypatch, scored, r4_rest)
    run, _, _ = R.prepare([dict(j) for j in jobs])
    assert len(run) == 501
    for j in run:
        ov = j["kw"].get("overrides", {})
        r_want, n_want = ov.get("edge_radius", E7.EDGE_R), ov.get("noslip", E7.NOSLIP)
        seen["warm"].clear()
        seen["rest"].clear()
        rec, _, _ = E7.run_trial(j["kind"], j["kw"], j["magnets"])
        assert rec["m7"]["edge_radius"] == r_want and rec["m7"]["noslip"] == n_want, j["tid"]
        if j["kind"] == "rest60":
            (rt, rx, cfg, dur, _s), = seen["rest"]
            assert rt.m7_edge_radius == r_want and rx is E7._ORIG["xml"] and dur == 60.0
            assert cfg.get("noslip_iterations", 0) == n_want
            assert not {"edge_radius", "noslip", "magnet", "magnet_scale", "face_gap_mm"} & set(cfg["params"])
        else:
            (_k, t, x), = seen["warm"]
            assert t.m7_edge_radius == r_want
            assert (x is E7._ORIG["xml"]) == (n_want == 0) and getattr(x, "m7_noslip", 0) == n_want


def test_v3_not_run_on_m7_list(jobs):
    assert R.v3_not_run(jobs) == {("magnets", "E1-7", "magnet=4x1.5_N35__6move"): "failed V3",
                                  ("magnets", "E1-7", "magnet=4x1.5_N35__sexy6"): "failed V3"}


def test_m5_scored_manifest_maps_to_m7(jobs):
    """Review 1, B-O9: every key of M5's committed scored manifest (except the 4 chamfer arms) is in M7's list with
    seed + 7000 and the same overrides."""
    man = json.loads((REPO / "experiments/E5_scored_m5/results/MANIFEST.json").read_text())
    m7 = {R.key_of(j): j for j in jobs}
    n = 0
    for t in man["trials"] + man["not_run"]:
        if t["tid"].startswith("chamfer="):
            continue
        tid = t["tid"]
        if tid.endswith(f"_s{t['seed']}"):
            tid = tid[: -len(f"_s{t['seed']}")] + f"_s{t['seed'] + 7000}"
        j = m7[(t["arm"], t["exp"], tid)]
        assert j["kw"]["seed"] == t["seed"] + 7000 and R._norm(j["kw"].get("overrides", {})) == R._norm(t["overrides"])
        n += 1
    assert n == 438


def test_m5_runner_untouched_by_m7():
    """M7's patches live in its own module instances; M5's registered M4 name is not M7's module."""
    assert sys.modules.get("e4_scored_m4_run_for_m5") is not M4
    m5 = _load("e5_scored_m5_run_isolation_check", REPO / "experiments/E5_scored_m5/run.py")
    assert m5.M4 is not M4 and m5.M4.SCORED_SEED_RANGE == (10000, 10999)
    assert m5.M4.run_trial is not E7.run_trial and any(n == "chamfer" for n, _ in m5.M4.E17_FACTORS)


# ---- full verdict on synthetic runs (review 1, B-R7): stand-in trials, M5's run procedure, M7's verdict ------------------
ENV = {"commit": "c0", "mujoco": "x", "numpy": "x", "scipy": "x", "python": "x", "cpu": "x"}


def _fake_rest_record(seed, n, slip=False, dt=0.0005):
    """A stand-in 60 s rest with d13_rest's sample count for its timestep (2,425 at 0.75 ms; review 2, R1)."""
    ns = AN.rest_samples(dt)
    rows = [[0.0] for _ in range(ns)]
    if slip:
        for i in range(ns // 2, ns):
            rows[i][0] = 0.3
    return {"timeseries": {"t": [0.5 + 0.025 * (i + 1) for i in range(ns)], "rot_deg": {"U": rows}},
            "members": {"U": ["c0"]}, "integrity_ok": True, "aborted": None, "t0_solved": True, "final_solved": True,
            "rest_rotation_deg": 0.001, "penetration_mm": 0.01, "radial_offset_mm_t0": 0.0, "seed": seed,
            "compiled_options": {"noslip_iterations": n, "timestep": dt}, "warmup_10s": {"rest_rotation_deg": 0.2}}


def _fake_m7_record(job, mutate=None):
    ov = job["kw"].get("overrides", {})
    gap = ov.get("gap", R.GAP)
    r, n = ov.get("edge_radius", E7.EDGE_R), ov.get("noslip", E7.NOSLIP)
    mp = R.magnet_params_for(dict(ov)) if job["magnets"] else None
    rec = {"params": {"gap": gap, "edge_profile": "rounded", "edge_radius": r}, "pass": True, "fail_reasons": [],
           "environment": job["env"], "magnet_table": job.get("magnet_info"),
           "magnets": None if mp is None else {"params": {"wall": mp.wall}, "layout_gap": gap},
           "magnet_stats": {"max_near_tilt_deg": 1.0}}
    if job["kind"] == "rest60":
        rec.update(_fake_rest_record(job["kw"]["seed"], n, dt=ov.get("timestep", 0.0005)), rest_s=60.0,
                   n_slip_events=0, ok_e11=True,
                   m7={"edge_radius": r, "noslip": n, "kind": "rest60"})
    else:
        rec["m7"] = {"edge_radius": r, "noslip": n, "kind": job["kind"], "n_trials": 1,
                     "noslip_wrapper_calls": 1 if n else 0, "options": {"noslip_iterations": n}}
    if job["kind"] == "seq":
        rec["sequence"] = job["kw"]["moves"]
        rec["per_move"] = [{"e16m_P_ok": True, "nontarget_drift_deg": 0.1, "max_turner_torque_Nm": 0.2,
                            "penetration_mm": 0.1, "turn_error_deg": 0.1} for _ in job["kw"]["moves"].split()]
    rec.update(R._metadata(job))
    rec["pass_m1_criteria"] = rec["pass"]
    if mutate:
        mutate(R.key_of(job), rec)
    return rec


def _m7_split(jobs):
    run, not_run = [], []
    for j in jobs:
        j = dict(j)
        if j["tid"].startswith("magnet=4x1.5_N35__"):
            not_run.append((j, "failed V3"))
            continue
        mp = R.magnet_params_for(dict(j["kw"].get("overrides", {}))) if j["magnets"] else None
        if mp is not None:
            j["magnet_info"] = {"table_file": M4._rel(M4.table_path(mp)), "table_sha256": "abc"}
        run.append(j)
    return run, not_run


def _m7_make(tmp, mutate=None, stop_after=None):
    jobs = R.build_m5_jobs("c0", ENV, 5.0)
    run, not_run = _m7_split(jobs)
    dirs = {"magnets": tmp / "results", "no_magnets": tmp / "results_nomag"}
    try:
        R.execute(dirs, run, not_run, "c0", ENV, "c0", {"gap": R.GAP}, 1,
                  runner=lambda j: (R.key_of(j), _fake_m7_record(j, mutate)), stop_after=stop_after,
                  check_git=False, log=lambda s: None)
    except R.Interrupted:
        pass
    reg = R.build_m5_jobs("c0", ENV, 5.0)
    return AN.A.analyse(dirs, reg, derived_not_run=R.v3_not_run(reg))


def _slip_e11(key, rec):
    if key == ("magnets", "E1-1", "rest_s17003"):
        rec.update(_fake_rest_record(17003, 10, slip=True))
        rec["n_slip_events"], rec["pass"], rec["pass_m1_criteria"] = 1, False, False


def _fail_rest_x(key, rec):
    if key == ("magnets", "REST-X", "rest_s17705"):
        rec.update(_fake_rest_record(17705, 10, slip=True))
        rec["n_slip_events"], rec["pass"], rec["pass_m1_criteria"] = 1, False, False


def _exception_e17(key, rec):
    if key == ("magnets", "E1-7", "timestep=0.00075__6move"):
        for k in ("m7", "per_move", "sequence"):
            rec.pop(k, None)
        rec.update(params={"gap": R.GAP}, harness_exception="boom", pass_m1_criteria=False)
        rec["pass"], rec["fail_reasons"] = False, ["harness exception"]


def _exception_e12(key, rec):
    if key == ("magnets", "E1-2", "U_s17100"):
        for k in ("m7", "per_move"):
            rec.pop(k, None)
        rec.update(params={"gap": R.GAP}, harness_exception="boom", pass_m1_criteria=False)
        rec["pass"], rec["fail_reasons"] = False, ["harness exception"]


def _inconsistent_rest(key, rec):
    if key == ("magnets", "E1-1", "rest_s17004"):
        rec.update(_fake_rest_record(17004, 10, slip=True))              # a slip the stored flag hides


@pytest.mark.parametrize("mutate,word", [
    (None, "PASS"),
    (_slip_e11, "NOT PASSED"),                    # the slip rule is a criterion (P-86 Q4)
    (_fail_rest_x, "PASS"),                       # REST-X is reported only
    (_exception_e17, "PASS"),                     # a reported-only harness exception is a failing record, not INVALID
    (_exception_e12, "NOT PASSED"),               # an Option A harness exception fails the trial
    (_inconsistent_rest, "INVALID"),              # a stored rest verdict that disagrees with the record
])
def test_full_verdict(tmp_path, mutate, word):
    st, vd = _m7_make(tmp_path, mutate)
    assert vd["verdict"] == word, (word, st["violations"][:5])
    if word != "INVALID":
        assert st["violations"] == [] and st["missing"] == []
    assert sum(1 for k in st["records"] if k[1] == "REST-X") == 40


def test_full_verdict_missing_and_extra(tmp_path):
    st, vd = _m7_make(tmp_path / "a", stop_after=500)                   # one record never written
    assert vd["verdict"].startswith("INCOMPLETE") and len(st["missing"]) == 1
    st, vd = _m7_make(tmp_path / "b")
    extra = tmp_path / "b" / "results" / "REST-X" / "rest_s17999.json"
    extra.write_text(json.dumps({"x": 1}))
    st, vd = AN.A.analyse({"magnets": tmp_path / "b" / "results", "no_magnets": tmp_path / "b" / "results_nomag"},
                          R.build_m5_jobs("c0", ENV, 5.0))
    assert vd["verdict"] == "INVALID"


# ---- review 2 additions -----------------------------------------------------------------------------------------------
def _dress_r3_rest(o, jobs):
    """An R3 rest output as the M7 record its job would give (R3's rest path is M7's: SC3)."""
    rec = json.loads(json.dumps(o["record"]))
    j = _job(jobs, f"{o['setting']}__rest60", "E1-7")
    ov = j["kw"]["overrides"]
    ev = E7.D13A.events(rec)
    rec.update(spec={"seed": j["kw"]["seed"], "overrides": ov}, rest_s=60.0, n_slip_events=len(ev),
               pass_m1_criteria=E7.e11_pass(rec) and not ev,
               m7={"edge_radius": ov.get("edge_radius", E7.EDGE_R), "noslip": ov.get("noslip", E7.NOSLIP),
                   "kind": "rest60"})
    return R.key_of(j), rec


def test_r3_rests_pass_the_m7_record_checks(jobs):
    """Review 2, R1: all 15 committed R3 rests, including timestep 0.75 ms (2,425 samples), give no problem."""
    files = sorted(glob.glob(str(REPO / "experiments/D15_rounded_edges/results/r3/rests/*.json.gz")))
    assert len(files) == 15
    n = {}
    for f in files:
        o = json.loads(gzip.decompress(Path(f).read_bytes()))
        k, rec = _dress_r3_rest(o, jobs)
        assert AN.m7_record_problems(k, rec) == [], k
        n[o["setting"]] = len(rec["timeseries"]["t"])
    assert n["timestep=0.00075"] == 2425 and AN.rest_samples(0.00075) == 2425
    assert {v for s, v in n.items() if s != "timestep=0.00075"} == {2400}
    assert AN.rest_samples(0.0005) == AN.rest_samples(0.00025) == 2400


def test_aborted_and_malformed_rests(r4_rest):
    k = ("magnets", "E1-1", "rest_s17000")
    base = dict(json.loads(json.dumps(r4_rest)), spec={"overrides": {"gap": 5e-5}}, rest_s=60.0,
                m7={"edge_radius": 0.0025, "noslip": 10, "kind": "rest60"})
    ab = dict(base, aborted="NumericalFailure at 20 s")
    ab["timeseries"] = {kk: (v[:800] if kk == "t" else {f: rows[:800] for f, rows in v.items()} if kk == "rot_deg" else v)
                        for kk, v in base["timeseries"].items()}
    ab.update(n_slip_events=len(E7.D13A.events(ab)), pass_m1_criteria=False)
    assert AN.m7_record_problems(k, ab) == []                            # an aborted rest is a failing trial
    assert AN.m7_record_problems(k, dict(ab, pass_m1_criteria=True))     # and may not be stored as passing
    full = dict(base, n_slip_events=0, pass_m1_criteria=True)
    assert AN.m7_record_problems(k, full) == []
    short = dict(full, timeseries={**full["timeseries"], "t": full["timeseries"]["t"][:2399]})
    assert AN.m7_record_problems(k, short)                               # not aborted: the count must be exact
    bad = {kk: v for kk, v in full.items() if kk != "penetration_mm"}
    probs = AN.m7_record_problems(k, bad)                                # malformed: a violation, not a crash
    assert probs and "lacks" in probs[-1]


def _aborted_e11(key, rec):
    if key == ("magnets", "E1-1", "rest_s17002"):
        rec["timeseries"] = {"t": rec["timeseries"]["t"][:800], "rot_deg": {"U": rec["timeseries"]["rot_deg"]["U"][:800]}}
        rec.update(aborted="NumericalFailure", n_slip_events=0, pass_m1_criteria=False)
        rec["pass"] = False


def _fail_e17_rest(key, rec):
    if key == ("magnets", "E1-7", "timestep=0.00075__rest60"):
        rec.update(_fake_rest_record(17000, 10, slip=True, dt=0.00075))
        rec["n_slip_events"], rec["pass"], rec["pass_m1_criteria"] = 1, False, False


def test_full_verdict_more_cases(tmp_path):
    st, vd = _m7_make(tmp_path / "abort", _aborted_e11)
    assert st["violations"] == [] and vd["verdict"] == "NOT PASSED"     # aborted E1-1: failing, not INVALID
    st, vd = _m7_make(tmp_path / "e17", _fail_e17_rest)
    assert st["violations"] == [] and vd["verdict"] == "PASS"           # a failing E1-7 rest is reported only
    # an explicitly missing REST-X record (file and ledger line removed): INCOMPLETE, not INVALID
    st, vd = _m7_make(tmp_path / "miss")
    res = tmp_path / "miss" / "results"
    (res / "REST-X" / "rest_s17705.json").unlink()
    led = res / R.LEDGER
    led.write_text("".join(x + "\n" for x in led.read_text().splitlines()
                           if not ('"REST-X"' in x and '"rest_s17705"' in x)))
    st, vd = AN.A.analyse({"magnets": res, "no_magnets": tmp_path / "miss" / "results_nomag"},
                          R.build_m5_jobs("c0", ENV, 5.0))
    assert st["violations"] == [] and st["missing"] == [("magnets", "REST-X", "rest_s17705")]
    assert vd["verdict"] == "INCOMPLETE"


def test_exception_record_through_run_job(jobs, monkeypatch):
    """Review 2, O5: the exception record M5's run_job writes, from a raising trial, passes M7's record checks."""
    def boom(kind, kw, magnets_on):
        raise ValueError("boom")
    monkeypatch.setattr(M4, "run_trial", boom)
    for tid, exp in (("U_s17100", "E1-2"), ("rest_s17000", "E1-1"), ("timestep=0.00075__rest60", "E1-7")):
        j = dict(_job(jobs, tid, exp), commit="c", startup=None, magnet_info=None)
        key, rec = R.run_job(j)
        assert rec["pass"] is False and rec.get("harness_exception") and AN.m7_record_problems(key, rec) == []


def test_report_text(tmp_path):
    st, vd = _m7_make(tmp_path)
    text = AN.report(st, vd)
    assert text.startswith("# G1 scored results — M7") and "M5 seeds" not in text
    assert all(x in text for x in AN.M7_RESTATED) and "Report template mismatch" not in text
    for heading in ("NoSlip-off E1-1", "Margins beside the rehearsals", "E1-7 against R3", "E1-7 rests"):
        assert heading in text
