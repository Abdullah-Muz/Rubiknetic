"""Unit tests for the M6 runner and verdict script (PHASE_1_M6_PREREGISTRATION.md section 6.1 item 3).
No test steps the simulation on an M6 seed: trials are replaced by stand-ins, or stopped before the first step.
M6's runner is M5's runner with patched globals, so M5's own tests (test_scored_m5.py) cover the run procedure; the
tests here cover what M6 changes, and that the changes stay out of M5's module instances."""
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
from rubiknetic.cube_physics.magnets import MagnetParams, core_layout, near_field_tables

REPO = Path(__file__).resolve().parents[1]


def _load(name, rel):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


A = _load("e6_scored_m6_analyze", "experiments/E6_scored_m6/analyze.py")
E6 = A.E6
R, M4 = E6.R, E6.M4                                   # M6's own instances of M5's and M4's runner modules
R5 = _load("e5_scored_m5_run", "experiments/E5_scored_m5/run.py")     # M5's runner as its own code loads it
ENV = {"mujoco": "4.0.1", "numpy": "x", "scipy": "y", "python": "3.12", "cpu": "test", "platform": "p"}
GAP_TAGS = {"gap=2.5e-05": 2.5e-5, "gap=0.0001": 1e-4}
K_SEQ = ("magnets", "E1-2", "U_s17100")


def _jobs(commit="c"):
    return E6.build_m6_jobs(commit, ENV)


@pytest.fixture
def coarse():
    tabs = near_field_tables(E6.NOMINAL_MP, None, quad=(4, 12), n_rho=13, n_z=9)
    M4.TABLES_PROVIDER = lambda mp: tabs
    yield tabs
    M4.TABLES_PROVIDER = None
    M4.restore_process()


# ---- isolation from M5 ---------------------------------------------------------------------------------------------
def test_m6_patches_do_not_reach_m5s_modules():
    assert R is not R5 and M4 is not R5.M4
    assert sys.modules["e4_scored_m4_run_for_m5"] is R5.M4
    assert (R5.M4.SEED_SHIFT, R5.M4.SCORED_SEED_RANGE, R5.M4.SNAP_SEED_BASE, R5.M4.E16T_SEED_BASE) == \
        (9000, (10000, 10999), 10550, 10640)
    assert R5.OUT == REPO / "experiments/E5_scored_m5/results" and R5.M4.OUT == R5.OUT
    assert "4x2_N35" in R5.M4.MAGNET_SIZES and "4x3_N52" not in R5.M4.MAGNET_SIZES
    assert R5.magnet_params_for({}) == MagnetParams()
    job = R5.build_m5_jobs("c", ENV, 5.0)[0]
    assert R5._metadata({**job, "startup": None})["mechanism"] == "M5"
    assert "experiments/E6_scored_m6/run.py" not in R5.M5_FROZEN_PATHS
    assert R5.M4.use_magnets is not M4.use_magnets and R5.M4.apply_m4_criteria is not M4.apply_m4_criteria


# ---- seeds and trial list ------------------------------------------------------------------------------------------
def test_seed_list_is_m5_plus_7000_and_in_range():
    m5 = [j for j in R5.build_m5_jobs("c", ENV, 5.0) if j["exp"] != "E1-7"]
    m6 = [j for j in _jobs() if j["exp"] != "E1-7"]
    assert len(m5) == len(m6) == 204 + 184
    for a, b in zip(m5, m6):
        assert (a["exp"], a["sub"], a["magnets"], a["kind"]) == (b["exp"], b["sub"], b["magnets"], b["kind"])
        s = a["kw"]["seed"]
        assert b["kw"]["seed"] == s + 7000
        assert b["tid"] == a["tid"][: -len(f"_s{s}")] + f"_s{s + 7000}"
        ka = {k: v for k, v in a["kw"].items() if k not in ("seed", "moves")}
        kb = {k: v for k, v in b["kw"].items() if k not in ("seed", "moves")}
        assert ka == kb
        if not a["tid"].startswith("scr20inv_"):
            assert a["kw"].get("moves") == b["kw"].get("moves")
    seeds = [j["kw"]["seed"] for j in _jobs()]
    assert min(seeds) == 17000 and max(seeds) == 17655
    assert all(j["kw"]["seed"] == 17000 for j in _jobs() if j["exp"] == "E1-7")


def test_full_list_counts_and_unique_keys():
    jobs = _jobs()
    keys = [R.key_of(j) for j in jobs]
    assert len(keys) == len(set(keys)) == 436
    assert sum(j["magnets"] and j["exp"] != "E1-7" for j in jobs) == 204
    assert sum(not j["magnets"] for j in jobs) == 184
    assert sum(j["exp"] == "E1-7" for j in jobs) == 48
    assert all(j["validated_tilt"] == 20.0 for j in jobs)
    assert all(j["kw"]["overrides"].get("gap") in (2.5e-5, 5e-5, 1e-4) for j in jobs)


def test_e4_scrambles_drawn_from_the_m6_seed():
    scr = [j for j in _jobs() if j["tid"].startswith("scr20inv_") and j["magnets"]]
    assert [j["kw"]["seed"] for j in scr] == list(range(17400, 17420))
    for j in scr:
        sc = random_scramble(20, j["kw"]["seed"])
        assert j["kw"]["moves"] == " ".join(str(m) for m in sc + invert(sc))
    old = {j["kw"]["moves"] for j in R5.build_m5_jobs("c", ENV, 5.0) if j["tid"].startswith("scr20inv_")}
    assert not old & {j["kw"]["moves"] for j in scr}


def test_e17_magnet_factors():
    tags = {j["tid"].split("__")[0] for j in _jobs() if j["exp"] == "E1-7"}
    assert {"nominal", "magnet=none", "magnet=4x3_N35", "magnet=4x3_N42", "magnet_scale=0.67", "gap=2.5e-05",
            "gap=0.0001"} <= tags
    assert not any(t.startswith("face_gap_mm") or "4x2" in t or "3x1.5" in t or "4x1.5" in t for t in tags)
    assert "magnet=4x3_N52" not in tags and "magnet_scale=1.0" not in tags      # nominal values are not run twice
    m5_tags = {j["tid"].split("__")[0] for j in R5.build_m5_jobs("c", ENV, 5.0) if j["exp"] == "E1-7"}
    non_magnet = {t for t in m5_tags if not t.startswith(("magnet", "face_gap_mm"))}
    assert non_magnet <= tags                                # every non-magnet factor of M5's E1-7 is kept


def test_magnet_params_for():
    assert E6.NOMINAL_MP == MagnetParams(diameter=0.004, length=0.003, grade="N52")
    assert E6.magnet_params_for({"magnet": "none"}) is None
    assert E6.magnet_params_for({"magnet": "4x3_N42"}).grade == "N42"
    assert E6.magnet_params_for({"magnet_scale": 0.67}).scale == 0.67
    assert E6.magnet_params_for({}).wall == 0.4e-3
    with pytest.raises(ValueError, match="face-gap"):
        E6.magnet_params_for({"face_gap_mm": 0.85})
    with pytest.raises(KeyError):
        E6.magnet_params_for({"magnet": "4x2_N35"})
    assert M4.magnet_params_for is E6.magnet_params_for and R.magnet_params_for is E6.magnet_params_for


# ---- the core layout reaches every magnet job ----------------------------------------------------------------------
class _Stop(BaseException):
    pass


def test_core_layout_and_gap_in_every_job(coarse, monkeypatch):
    got = []

    def trial_stub(params, setup, **_kw):
        got.append(params.gap)
        raise _Stop

    monkeypatch.setattr(scored, "Trial", trial_stub)
    n_mag = 0
    for j in _jobs():
        got.clear()
        with pytest.raises(_Stop):
            M4.run_trial(j["kind"], copy.deepcopy(j["kw"]), j["magnets"])
        g = GAP_TAGS.get(j["tid"].split("__")[0], R.GAP) if j["exp"] == "E1-7" else R.GAP
        assert got[0] == g, j["tid"]
        mp = E6.magnet_params_for(dict(j["kw"].get("overrides", {}))) if j["magnets"] else None
        ms = M4._MS
        if mp is None:
            assert ms is None, j["tid"]
            continue
        n_mag += 1
        want = core_layout(mp, E6.CLEARANCE)
        assert ms.n == 40 and ms.mp == mp and M4._MS_KEY == (mp, g), j["tid"]
        assert np.allclose(ms.p_loc, [m["pos"] for m in want], atol=1e-15), j["tid"]
        assert [m["body"] for m in ms.mags] == [m["body"] for m in want]
        assert sum(m["body"] == "core" for m in ms.mags) == 20
    assert n_mag == 204 + 46                                  # every E1-7 arm except magnet=none (2 trials)


def test_startup_check_on_the_core_system(coarse):
    res = E6.startup_check()
    assert res["pass"] and res["gap"] == R.GAP and res["n_magnets"] == 40
    assert M4._MS.mp == E6.NOMINAL_MP
    assert R.startup_check is E6.startup_check


# ---- tables --------------------------------------------------------------------------------------------------------
def _fake_tables(tmp, monkeypatch):
    """A stand-in N52 table and N35 table with 'recorded' hashes, and an empty derived-tables folder."""
    mp, n35 = E6.NOMINAL_MP, MagnetParams(diameter=0.004, length=0.003, grade="N35")
    rng = np.random.default_rng(0)
    base = {"rho": np.linspace(0.0, mp.r2 + 0.001, 37), "z": np.linspace(mp.length + 0.0001, mp.r2 + 0.001, 31),
            "h_deg": np.array(1.5), "quad": np.array([16, 48])}
    data = {k: rng.normal(size=(37, 31)) for k in E6.TABLE_KEYS}
    paths = {}
    for m, fac in ((mp, 1.0), (n35, E6.strength_factor(n35))):
        p = tmp / "rec" / E6._table_name(m)
        p.parent.mkdir(exist_ok=True)
        np.savez(p, **base, **{k: v * fac for k, v in data.items()})
        paths[m] = p
    rec = {m: (p, M4._sha256(p), "test record") for m, p in paths.items()}
    monkeypatch.setattr(E6, "_recorded_tables", lambda: rec)
    monkeypatch.setattr(E6, "TABLES", tmp / "derived")
    monkeypatch.setattr(M4, "_rel", lambda path: str(path))
    return rec


def test_tables_recorded_and_derived(tmp_path, monkeypatch):
    rec = _fake_tables(tmp_path, monkeypatch)
    n42, s67 = E6.magnet_params_for({"magnet": "4x3_N42"}), E6.magnet_params_for({"magnet_scale": 0.67})
    assert E6.derived_magnets() == [n42, s67] or set(E6.derived_magnets()) == {n42, s67}
    info = E6.magnet_availability(E6.NOMINAL_MP)
    assert info["validated_tilt_deg"] == 20.0 and info["table_sha256"] == rec[E6.NOMINAL_MP][1]
    with pytest.raises(M4.Refused, match="does not exist"):
        E6.magnet_availability(n42)
    E6.make_tables(log=lambda s: None)
    for mp, fac in ((n42, (1.30 / 1.455) ** 2), (s67, 0.67)):
        info = E6.magnet_availability(mp)
        assert np.isclose(info["strength_factor_vs_N52"], fac, rtol=1e-15)
        assert info["derived_max_rel_diff"] <= 1e-12 and E6.table_path(mp).parent == tmp_path / "derived"
        assert E6.table_path(mp).name == E6._table_name(mp)
    before = E6.table_path(n42).read_bytes()
    E6.make_tables(log=lambda s: None)                        # a second call never rewrites a derived table
    assert E6.table_path(n42).read_bytes() == before


def test_tampered_or_wrong_tables_are_refused(tmp_path, monkeypatch):
    rec = _fake_tables(tmp_path, monkeypatch)
    n42 = E6.magnet_params_for({"magnet": "4x3_N42"})
    E6.make_tables(log=lambda s: None)
    p = E6.table_path(n42)
    with np.load(p) as f:
        d = {k: f[k] for k in f.files}
    np.savez(p, **{**d, "C0": d["C0"] * (1 + 1e-9)})
    with pytest.raises(M4.Refused, match="differs from the N52 table"):
        E6.magnet_availability(n42)
    np.savez(p, **{**d, "rho": d["rho"] * 2})
    with pytest.raises(M4.Refused, match="default grid"):
        E6.magnet_availability(n42)
    np.savez(p, **d)
    assert E6.magnet_availability(n42)["table_origin"].startswith("N52 table x")
    src = rec[E6.NOMINAL_MP][0]
    with np.load(src) as f:
        s = {k: f[k] for k in f.files}
    np.savez(src, **{**s, "Ct": s["Ct"] * 1.5})               # the recorded source table changed
    with pytest.raises(M4.Refused, match="not the recorded"):
        E6.magnet_availability(E6.NOMINAL_MP)
    with pytest.raises(M4.Refused, match="not the recorded"):
        E6.magnet_availability(n42)


# ---- V3 rule and classification ------------------------------------------------------------------------------------
def test_committed_validation_records_are_usable():
    assert E6.v3_basis() == []


def test_v3_rule(tmp_path, monkeypatch):
    jobs = _jobs()
    assert all(E6.v3_rule(j) == ("run", None) for j in jobs)
    assert R.v3_not_run(jobs) == {}
    monkeypatch.setitem(E6.MAGNET_SIZES, "5x2_N35", (0.005, 0.002, "N35"))
    j = next(x for x in jobs if x["tid"].startswith("nominal__"))
    bad = {**j, "kw": {**j["kw"], "overrides": {**j["kw"]["overrides"], "magnet": "5x2_N35"}}}
    status, msg = E6.v3_rule(bad)
    assert status == "refused" and "no V3 record" in msg
    er5 = json.loads(E6.ER5_JSON.read_text())
    for e in er5["V3_turn"]:
        if e["placement"] == "real" and e["kind"] == "corner":
            e["pass"] = False
    f = tmp_path / "er5.json"
    f.write_text(json.dumps(er5))
    monkeypatch.setattr(E6, "ER5_JSON", f)
    assert "real placement" in "; ".join(E6.v3_basis())
    assert E6.v3_rule(j)[0] == "refused"
    nomag = next(x for x in jobs if not x["magnets"])
    assert E6.v3_rule(nomag) == ("run", None)


def test_full_list_classifies_436_runnable(monkeypatch):
    monkeypatch.setattr(M4, "magnet_availability",
                        lambda mp: {"table_file": M4._rel(E6.table_path(mp)), "table_sha256": "x"})
    run, not_run, refused = R.prepare(_jobs())
    assert (len(run), len(not_run), len(refused)) == (436, 0, 0)
    files = {j["magnet_info"]["table_file"] for j in run if j.get("magnet_info")}
    assert len(files) == 4                                    # N52, N35, N42 and N52 at scale 0.67


# ---- validated regime (section 1) ----------------------------------------------------------------------------------
def _crit(sub, tilt, perp, clamped=0):
    rec = {"pass": True, "magnet_stats": {"max_near_tilt_deg": tilt, "near_perpendicular": perp, "clamped_z": clamped}}
    return M4.apply_m4_criteria(rec, sub, E6.VALIDATED_TILT_DEG, True)


def test_regime_rule_tilt_perpendicular_and_clamped_z():
    ok = _crit("E1-2", 19.99, 0, clamped=5000)                # clamped z is inside the regime (P-60)
    assert ok["pass"] and ok["ok_magnet_validity"] and not ok["magnet_outside_validated_range"]
    assert ok["validated_tilt_deg"] == 20.0 and ok["near_perpendicular_pairs"] == 0
    tilt = _crit("E1-2", 20.01, 0)
    assert not tilt["pass"] and tilt["magnet_outside_validated_range"] and "rule 2" in tilt["fail_reasons"][0]
    perp = _crit("E1-1", 3.0, 2)
    assert not perp["pass"] and perp["magnet_outside_validated_range"] and not perp["ok_magnet_validity"]
    assert any("perpendicular" in r for r in perp["fail_reasons"])
    both = _crit("E1-5", 25.0, 1)
    assert not both["pass"] and len(both["fail_reasons"]) == 2
    abuse = _crit("E1-6b", 3.0, 1)                            # rule 3: labelled, not failed
    assert abuse["pass"] and abuse["rule3_label"] == "magnet model outside validated range"
    assert _crit("E1-6c", 3.0, 0)["rule3_label"] is None
    e17 = _crit("E1-7", 30.0, 4)                              # E1-7 is under neither rule
    assert e17["pass"] and e17["magnet_outside_validated_range"]
    off = M4.apply_m4_criteria({"pass": True, "magnet_stats": None}, "E1-2", None, False)
    assert off["pass"] and "near_perpendicular_pairs" not in off


def test_run_job_uses_the_m6_criteria_and_label(monkeypatch):
    job = {**next(j for j in _jobs() if R.key_of(j) == K_SEQ), "startup": {"gap": R.GAP}}

    class _MS:
        pass

    def fake_trial(kind, kw, magnets):
        return ({"pass": True, "magnets": {"params": {}}, "magnet_stats": {"max_near_tilt_deg": 4.0,
                                                                           "near_perpendicular": 1}}, _MS(), None)

    monkeypatch.setattr(M4, "run_trial", fake_trial)
    monkeypatch.setattr(M4, "_MS_KEY", (E6.NOMINAL_MP, R.GAP))
    key, rec = R.run_job(job)
    assert key == K_SEQ and rec["mechanism"] == "M6" and rec["validated_tilt_deg"] == 20.0
    assert not rec["pass"] and any("perpendicular" in r for r in rec["fail_reasons"])
    assert rec["magnets"]["layout_gap"] == R.GAP


# ---- labels, folders, frozen paths ---------------------------------------------------------------------------------
def test_labels_folders_and_frozen_paths():
    here = REPO / "experiments/E6_scored_m6"
    assert (R.HERE, R.OUT, R.OUT_NOMAG) == (here, here / "results", here / "results_nomag")
    assert (M4.OUT, M4.OUT_NOMAG) == (R.OUT, R.OUT_NOMAG)
    body = R.manifest_body([], [], "c", ENV)
    assert body["mechanism"] == "M6"
    for p in ("experiments/PHASE_1_M6_PREREGISTRATION.md", "experiments/E6_scored_m6/run.py",
              "experiments/E6_scored_m6/analyze.py", "experiments/E5_scored_m5/run.py",
              "experiments/E4_scored_m4/run.py", "experiments/M6_core_magnets/results/m6_checks.json",
              "experiments/ER5_magnet_validation/results/er5_4x3_N35.json", "src"):
        assert p in body["frozen_paths"], p
    for p in body["frozen_paths"]:
        assert "*" in p or (REPO / p).exists(), p
    assert R.SMOKE_SEED_BASE == 18000 and M4.nominal_validated_tilt() == 20.0


def test_this_checkout_passes_the_location_check():
    R.require_local_location(None)


def _no_real_start(monkeypatch, tmp_path):
    def unreachable(*a, **k):
        raise AssertionError("the test reached a real start")
    monkeypatch.setattr(R, "execute", unreachable)
    monkeypatch.setattr(R, "startup_check", unreachable)
    monkeypatch.setattr(R, "OUT", tmp_path / "results")
    monkeypatch.setattr(R, "OUT_NOMAG", tmp_path / "results_nomag")


@pytest.mark.parametrize("where", ["here", "results", "results_nomag", "inside"])
def test_smoke_dir_may_not_be_the_m6_scored_folders(where, monkeypatch, tmp_path):
    _no_real_start(monkeypatch, tmp_path)
    d = {"here": R.HERE, "results": R.OUT, "results_nomag": R.OUT_NOMAG, "inside": R.OUT / "x"}[where]
    with pytest.raises(SystemExit, match="scored folders"):
        E6.main(["smoke", "--smoke-dir", str(d)])


def test_scored_start_refused_in_a_onedrive_folder(monkeypatch, tmp_path):
    _no_real_start(monkeypatch, tmp_path / "OneDrive" / "Rubiknetic")
    with pytest.raises(SystemExit, match="must not use a OneDrive folder"):
        E6.main(["all"])


# ---- run procedure and verdict through the patched modules ---------------------------------------------------------
def _fake_record(job, mutate=None):
    ov = job["kw"].get("overrides", {})
    gap = ov.get("gap", R.GAP)
    mp = E6.magnet_params_for(dict(ov)) if job["magnets"] else None
    rec = {"params": {"gap": gap}, "pass": True, "fail_reasons": [], "environment": job["env"],
           "magnets": None if mp is None else {
               "params": {"wall": mp.wall, "diameter": mp.diameter, "length": mp.length, "grade": mp.grade,
                          "scale": mp.scale}, "layout_gap": gap, "n_magnets": 40},
           "magnet_table": job.get("magnet_info"),
           "magnet_stats": None if mp is None else {"max_near_tilt_deg": 12.0, "near_perpendicular": 0,
                                                    "clamped_z": 7},
           "validated_tilt_deg": None if mp is None else 20.0,
           "magnet_outside_validated_range": False}
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


def _make(tmp, mutate=None, stop_after=None, jobs=None, not_run=()):
    jobs = _jobs("c0") if jobs is None else jobs
    for j in jobs:
        mp = E6.magnet_params_for(dict(j["kw"].get("overrides", {}))) if j["magnets"] else None
        if mp is not None:
            j["magnet_info"] = {"table_file": M4._rel(E6.table_path(mp)), "table_sha256": "abc"}
    n = R.execute(_dirs(tmp), jobs, list(not_run), "c0", ENV, "c0", {"gap": R.GAP}, 1,
                  runner=lambda j: (R.key_of(j), _fake_record(j, mutate)), stop_after=stop_after,
                  check_git=False, log=lambda s: None)
    return jobs, n


def _verdict(tmp):
    reg = _jobs("c0")
    return A.analyse(_dirs(tmp), reg, derived_not_run=R.v3_not_run(reg))


def _only(key, **fields):
    def m(k, rec):
        if k == key:
            for f, v in fields.items():
                if callable(v):
                    v(rec)
                else:
                    rec[f] = v
    return m


@pytest.fixture(scope="module")
def complete_set(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("complete_m6")
    _make(tmp)
    return tmp


def test_positive_control_complete_valid_set_passes(complete_set):
    st, vd = _verdict(complete_set)
    assert st["violations"] == [] and st["missing"] == []
    assert vd["verdict"] == "PASS"
    assert {e: r["n"] for e, r in vd["rows"].items()} == A.EXPECTED
    assert sum(1 for k in st["records"] if k[0] == "no_magnets") == 184
    man = json.loads((complete_set / "results" / R.MANIFEST).read_text())
    assert man["mechanism"] == "M6" and len(man["trials"]) == 436 and man["not_run"] == []
    text = A.report(st, vd)
    assert "M6" in text and "P-58" in text and "M5 seeds" not in text


def test_one_failing_rest_trial_is_not_passed(tmp_path):
    _make(tmp_path, _only(("magnets", "E1-1", "rest_s17001"), **{"pass": False, "fail_reasons": ["M1 criteria"]}))
    st, vd = _verdict(tmp_path)
    assert st["violations"] == [] and vd["verdict"] == "NOT PASSED"
    assert vd["rows"]["E1-1"]["passed"] == 19


def test_one_move_failing_e16m_is_not_passed(tmp_path):
    _make(tmp_path, _only(K_SEQ, per_move=lambda r: r["per_move"][0].update(e16m_P_ok=False)))
    assert _verdict(tmp_path)[1]["verdict"] == "NOT PASSED"


def test_missing_record_is_incomplete(tmp_path):
    _make(tmp_path)
    key = ("magnets", "E1-6t", "std_ppp_pos_s17654")
    R.record_path(_dirs(tmp_path), key).unlink()
    led = tmp_path / "results" / R.LEDGER
    lines = [x for x in led.read_text().splitlines()
             if (json.loads(x)["arm"], json.loads(x)["tid"]) != (key[0], key[2])]
    led.write_text("\n".join(lines) + "\n")
    st, vd = _verdict(tmp_path)
    assert st["violations"] == [] and vd["verdict"] == "INCOMPLETE" and st["missing"] == [key]


@pytest.mark.parametrize("needle, mutate", [
    ("mechanism 'M5'", _only(K_SEQ, mechanism="M5")),
    ("48 magnets", _only(K_SEQ, magnets=lambda r: r["magnets"].update(n_magnets=48))),
    ("magnet parameters differ", _only(K_SEQ, magnets=lambda r: r["magnets"]["params"].update(grade="N35"))),
    ("magnet parameters differ", _only(K_SEQ, magnets=lambda r: r["magnets"]["params"].update(length=0.002))),
    ("magnet parameters differ", _only(("magnets", "E1-7", "magnet_scale=0.67__6move"),
                                       magnets=lambda r: r["magnets"]["params"].update(scale=1.0))),
    ("validated tilt 5.0", _only(K_SEQ, validated_tilt_deg=5.0)),
    ("outside-regime flag", _only(K_SEQ, magnet_stats={"max_near_tilt_deg": 21.0, "near_perpendicular": 0})),
    ("outside-regime flag", _only(K_SEQ, magnet_stats={"max_near_tilt_deg": 2.0, "near_perpendicular": 3})),
    ("marked as passing", _only(K_SEQ, magnet_stats={"max_near_tilt_deg": 2.0, "near_perpendicular": 3},
                                magnet_outside_validated_range=True)),
    ("wall", _only(K_SEQ, magnets=lambda r: r["magnets"]["params"].update(wall=0.00015))),
    ("params.gap", _only(K_SEQ, params={"gap": 2e-4})),
    ("seed differs", _only(K_SEQ, spec=lambda r: r["spec"].update(seed=10100))),
    ("no-magnet record carries magnets", _only(("no_magnets", "E1-2", "U_s17100"), magnets={"params": {}})),
])
def test_m6_record_violations_are_invalid(tmp_path, needle, mutate):
    _make(tmp_path, mutate)
    st, vd = _verdict(tmp_path)
    assert vd["verdict"] == "INVALID", st["violations"]
    assert any(needle in v for v in st["violations"]), st["violations"]


def test_abuse_trial_outside_the_regime_may_pass_and_is_valid(tmp_path):
    key = ("magnets", "E1-6", "opposed_UR_s17603")
    keys = {R.key_of(j): j for j in _jobs()}
    key = next(k for k, j in keys.items() if j["sub"] == "E1-6b" and j["magnets"])
    _make(tmp_path, _only(key, magnet_stats={"max_near_tilt_deg": 26.0, "near_perpendicular": 0},
                          magnet_outside_validated_range=True,
                          rule3_label="magnet model outside validated range"))
    st, vd = _verdict(tmp_path)
    assert st["violations"] == [] and vd["verdict"] == "PASS"


def test_a_not_run_arm_is_invalid_for_m6(tmp_path):
    jobs = _jobs("c0")
    nr = [j for j in jobs if j["tid"].startswith("magnet=4x3_N42__")]
    run = [j for j in jobs if j not in nr]
    _make(tmp_path, jobs=run, not_run=[(j, "failed V3") for j in nr])
    st, vd = _verdict(tmp_path)
    assert vd["verdict"] == "INVALID"
    assert any("registers no 'not run' arm" in v for v in st["violations"])
    assert any("re-derived" in v for v in st["violations"])


def test_resume_runs_only_missing_keys_and_never_overwrites(tmp_path):
    jobs = [j for j in _jobs("c0") if j["tid"] in ("U_s17100", "Up_s17102")]
    assert len(jobs) == 4                                     # magnet and no-magnet arm of two trial IDs
    with pytest.raises(R.Interrupted):
        _make(tmp_path, jobs=copy.deepcopy(jobs), stop_after=1)
    first = sorted(p for p in tmp_path.rglob("*.json") if p.name != R.MANIFEST)
    assert len(first) == 1
    before = first[0].read_bytes()
    _, n = _make(tmp_path, jobs=copy.deepcopy(jobs))
    assert n == 3 and first[0].read_bytes() == before
    starts = [json.loads(x) for x in (tmp_path / "results" / R.STARTS).read_text().splitlines()]
    assert [s["k"] for s in starts] == [1, 2]


def test_first_start_refused_when_a_results_folder_is_not_empty(tmp_path):
    (tmp_path / "results_nomag").mkdir()
    (tmp_path / "results_nomag" / "x.txt").write_text("x")
    with pytest.raises(SystemExit, match="refusing first start"):
        _make(tmp_path)


def test_harness_exception_gives_a_failing_m6_record(monkeypatch):
    job = {**next(j for j in _jobs() if R.key_of(j) == K_SEQ), "startup": {"gap": R.GAP}}

    def boom(*a, **k):
        raise RuntimeError("stand-in failure")

    monkeypatch.setattr(M4, "run_trial", boom)
    key, rec = R.run_job(job)
    assert key == K_SEQ and rec["mechanism"] == "M6" and not rec["pass"]
    assert rec["magnets"]["params"]["grade"] == "N52" and rec["magnets"]["params"]["length"] == 0.003
    assert "harness exception" in rec["fail_reasons"][0]


def test_harness_exception_record_passes_integrity_and_fails_the_trial(tmp_path, monkeypatch):
    jobs = _jobs("c0")
    for j in jobs:
        j["startup"] = {"gap": R.GAP}
    monkeypatch.setattr(M4, "run_trial", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("stand-in")))
    exc = {K_SEQ: R.run_job({**next(j for j in jobs if R.key_of(j) == K_SEQ), "commit": "c0",
                             "magnet_info": {"table_file": M4._rel(E6.table_path(E6.NOMINAL_MP)),
                                             "table_sha256": "abc"}})[1]}

    def m(key, rec):
        if key in exc:
            rec.clear()
            rec.update(exc[key])

    _make(tmp_path, m, jobs=jobs)
    st, vd = _verdict(tmp_path)
    assert st["violations"] == [], st["violations"]
    assert vd["verdict"] == "NOT PASSED" and vd["rows"]["E1-2"]["passed"] == 23
