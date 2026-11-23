"""Tests for the ER9 Part G runner and replay tool (er9g_run.py, er9g_replay.py; PROTOCOL.md G.4, G.7, G.8, G.9).

Fast unit tests only: registry, seed and worker refusals, gates on temporary result folders, the G.4 per-trial rule
and the Part G verdict, the record schema, the statistics functions against known values, the selection rule, the
cost projection and memory rule, job lists. No trial, replay or MuJoCo simulation runs.
Run (WSL, repo root):
  ~/.venvs/rubiknetic/bin/python -m pytest experiments/ER9_anchored_core_layouts/tests/test_er9g_run.py -q
"""
from __future__ import annotations

import copy
import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]


def _load(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


G = _load("er9g_run")
RP = _load("er9g_replay")
ST = G.ST


# ---- registry, seeds, workers ----------------------------------------------------------------------------------
@pytest.mark.parametrize("mode", ["probe", "full", "smoke"])
def test_run_registry_is_pg8_pg20_only(mode):
    for a in ("PG8", "PG20"):
        assert G.check_arm(a, mode) == a
    for a in ("L0", "C52", "PG20r", "HB1", "G1", "H1", "W3", "S1", "pg8", ""):
        with pytest.raises(G.Refused):
            G.check_arm(a, mode)
    assert G.check_arm("PG20r", mode, u4_changed=True) == "PG20r"


def test_rest40_registry_adds_l0():
    for a in ("L0", "PG8", "PG20"):
        G.check_arm(a, "rest40")
    for a in ("C52", "PG20r", "HB3"):
        with pytest.raises(G.Refused):
            G.check_arm(a, "rest40")
    with pytest.raises(G.Refused):
        G.check_arm("L0", "probe")
    with pytest.raises(G.Refused):
        G.allowed_arms("selfcheck")


def test_replay_registry():
    for a in ("L0", "C52", "PG8", "PG20"):
        assert RP.check_replay_arm(a) == a
    for a in ("PG20r", "H1", "G2", "X0.1", "S1", "W3"):
        with pytest.raises(G.Refused):
            RP.check_replay_arm(a)
    assert RP.check_replay_arm("PG20r", u4_changed=True) == "PG20r"


def test_every_part_g_arm_runs_as_er7_l0_and_only_gs2_as_c52():
    for a in ("L0", "PG8", "PG20", "PG20r"):
        assert G.er7_arm_for(a) == "L0"
    assert G.er7_arm_for("C52") == "C52"


@pytest.mark.parametrize("seed", [16000, 16100, 16568, 16700, 16739, 16999])
def test_seeds_accepted(seed):
    assert G.check_seed(seed) == seed


@pytest.mark.parametrize("seed", [15999, 17000, 17500, 17999, 10000, 10999, 10500, 18000, 0, -1, 16000.5])
def test_seeds_refused(seed):
    with pytest.raises(G.Refused):
        G.check_seed(seed)


def test_job_list_seed_refusal():
    G.check_jobs_seeds([{"kw": {"seed": 16001}}, {"kw": {"seed": 16739}}])
    with pytest.raises(G.Refused):
        G.check_jobs_seeds([{"kw": {"seed": 16001}}, {"kw": {"seed": 17001}}])


def test_workers():
    assert G.DEFAULT_JOBS == 4 and G.MAX_JOBS == 6
    for n in (1, 4, 6):
        assert G.check_workers(n) == n
    for n in (0, 7, 8, -1):
        with pytest.raises(G.Refused):
            G.check_workers(n)


def test_rest40_seed_block():
    assert G.REST40_SEEDS == tuple(range(16700, 16740)) and len(G.REST40_SEEDS) == 40
    for s in G.REST40_SEEDS:
        G.check_seed(s)


# ---- job lists ---------------------------------------------------------------------------------------------------
def _base():
    out = []
    spec = [("E1-1", "E1-1", "rest", 20, 16000), ("E1-2", "E1-2", "seq", 24, 16100), ("E1-3", "E1-3", "seq", 22, 16200),
            ("E1-4", "E1-4", "seq", 40, 16300), ("E1-5", "E1-5", "forgive", 42, 16500),
            ("E1-5s", "E1-5s", "snap", 20, 16551), ("E1-6", "E1-6a", "openpad", 6, 16600),
            ("E1-6", "E1-6b", "opposed", 6, 16610), ("E1-6", "E1-6c", "twist", 8, 16620),
            ("E1-6t", "E1-6t", "twist_std", 16, 16640)]
    for exp, sub, kind, n, s0 in spec:
        for i in range(n):
            out.append({"exp": exp, "sub": sub, "kind": kind, "tid": f"{kind}_s{s0 + i}",
                        "kw": {"seed": s0 + i, "overrides": {"gap": 5e-5}}, "magnets": True})
    return out


def test_probe_rest40_and_gs_lists():
    base = _base()
    assert len(base) == 204
    pb = G.probe_base(base)
    assert len(pb) == 106 and {j["exp"] for j in pb} == set(G.PROBE_EXPS)
    rb = G.rest40_base(base)
    assert [j["kw"]["seed"] for j in rb] == list(range(16700, 16740))
    assert all(j["sub"] == "E1-1" and j["kind"] == "rest" and j["tid"] == f"rest_s{j['kw']['seed']}" for j in rb)
    assert base[0]["kw"]["seed"] == 16000                         # template not mutated
    firsts = G.gs_firsts(base)
    assert [j["sub"] for j in firsts] == list(G.GS_SUBS) and len(firsts) == 10


def test_make_job_fields():
    j = G.make_job(_base()[0], "PG20", "probe", {"commit": "abc"}, 2.0)
    assert j["er7_arm"] == "L0" and j["er9g_arm"] == "PG20" and j["er9g_grade"] == "N52" and j["er9g_d_val"] == 2.0
    assert j["commit"] == "abc" and j["scored"] is False and j["reported_only"] is True and j["er9g_diag"] is True
    assert "rest60" not in j                                      # ER7's default: the 60 s instrumented rest runs
    assert [k for k in j if k.startswith("er9g_")] and all(not k.startswith("er9_") for k in j)


def test_record_paths():
    p = G.record_path(Path("/r"), "probe", "PG8", "E1-2", "U_s16100")
    assert p.as_posix() == "/r/probe/PG8/E1-2/U_s16100.json.gz"


# ---- G.4 per-trial rule and Part G verdict -----------------------------------------------------------------------
def _stats(d_val=2.0, **kw):
    s = {f"{k}_{f}": 0 for k in ST.CLASSES for f in ("near_evals", "near_perpendicular", "clamped_z")}
    s.update({f"{k}_max_near_tilt_deg": 0.0 for k in ST.CLASSES})
    s.update({"cross_near": 0, "D_val_deg": d_val, "PC_max_path_dev_deg": 0.0, "PC_max_path_dev_deg_clamped": 0.0,
              "legacy": {"max_near_tilt_deg": 0.0, "near_perpendicular": 0, "clamped_z": 0, "calls": 1}})
    s.update(kw)
    return s


@pytest.mark.parametrize("field,value,oor", [
    ("CE_max_near_tilt_deg", 5.0, False), ("CE_max_near_tilt_deg", 5.01, True), ("CE_clamped_z", 1, True),
    ("CE_near_perpendicular", 1, True), ("PCon_max_near_tilt_deg", 20.0, False),
    ("PCon_max_near_tilt_deg", 20.01, True), ("PCon_clamped_z", 5, False), ("PCon_near_perpendicular", 1, True),
    ("PCoff_max_near_tilt_deg", 7.5, False), ("PCoff_max_near_tilt_deg", 7.6, True), ("PCoff_clamped_z", 1, True),
    ("PCoff_near_perpendicular", 1, True), ("PP3_max_near_tilt_deg", 7.6, True), ("PP3_clamped_z", 1, True),
    ("PP3_near_perpendicular", 1, True), ("cross_near", 1, True), ("X_max_near_tilt_deg", 30.0, False)])
def test_oor_reasons_match_er9g_stats(field, value, oor):
    s = _stats(**{field: value})
    r = G.oor_reasons(s, 2.0)
    assert bool(r) is oor and ST.out_of_regime(s, 2.0) is oor


def test_oor_refuses_other_d_val():
    with pytest.raises(ValueError):
        G.oor_reasons(_stats(d_val=2.0), 4.0)


def test_verdict_replaces_legacy_rule2_with_g4():
    legacy = ["rule 2: near-pair tilt 18.400 deg > validated 5 deg"]
    v = G.verdict("E1-2", legacy, _stats(PCon_max_near_tilt_deg=18.4, PCon_clamped_z=30), 2.0)
    assert v["pass"] and v["out_of_regime"] is False and v["fail_reasons"] == []
    v = G.verdict("E1-2", legacy, _stats(CE_max_near_tilt_deg=6.0), 2.0)
    assert not v["pass"] and v["out_of_regime"] and v["fail_reasons"][0].startswith("G.4 per-class rule")
    v = G.verdict("E1-2", ["M1 criteria", legacy[0]], _stats(), 2.0)
    assert v["fail_reasons"] == ["M1 criteria"] and not v["pass"]


@pytest.mark.parametrize("sub", sorted(G.OPERATIONAL))
def test_operational_trials_fail_when_out_of_regime(sub):
    v = G.verdict(sub, [], _stats(cross_near=1), 2.0)
    assert not v["pass"] and v["operational"] and v["rule3_label"] is None
    v = G.verdict(sub, [], None, 2.0)                             # stats missing: not silently passed
    assert not v["pass"]


@pytest.mark.parametrize("sub", sorted(G.ABUSE))
def test_abuse_trials_are_labelled_not_failed(sub):
    v = G.verdict(sub, [], _stats(cross_near=1), 2.0)
    assert v["pass"] and not v["operational"] and v["rule3_label"] == "magnet model outside validated range"
    v = G.verdict(sub, [], _stats(), 2.0)
    assert v["pass"] and v["rule3_label"] is None


def test_operational_and_abuse_sets_match_g4_and_m4():
    assert G.OPERATIONAL == {"E1-1", "E1-2", "E1-3", "E1-4", "E1-5", "E1-5s", "E1-6a"}
    assert G.ABUSE == {"E1-6b", "E1-6c", "E1-6t"}
    assert set(G.FULL_COUNTS) == G.OPERATIONAL | G.ABUSE and sum(G.FULL_COUNTS.values()) == 204
    assert sum(G.PROBE_COUNTS.values()) == 106


def _record(sub="E1-2", stats=None, legacy=None, d_val=2.0, exp=None, tid="U_s16100"):
    return {"experiment": exp or sub, "sub_experiment": sub, "trial_id": tid, "pass": not legacy,
            "fail_reasons": list(legacy or []), "ok_magnet_validity": not legacy, "magnet_outside_validated_range":
            bool(legacy), "validated_tilt_deg": 5.0, "er7_flag_outside_regime": False, "seed": 16100,
            "spec": {"seed": 16100},
            "er9": {k: None for k in G.ER9_KEYS} | {"D_val_deg": d_val, "class_stats": stats or _stats(d_val)}}


def test_apply_verdict_record_schema_and_legacy_kept():
    rec = _record(legacy=["rule 2: near-pair tilt 18.4 deg > validated 5 deg"], stats=_stats(PCon_max_near_tilt_deg=18.4))
    G.apply_verdict(rec)
    assert set(rec["er9"]) == set(G.ER9_KEYS) | set(G.ER9_VERDICT_KEYS)
    assert rec["pass"] is True and rec["fail_reasons"] == [] and rec["ok_magnet_validity"] is True
    assert rec["er7_flag_outside_regime"] is False and rec["magnet_outside_validated_range"] is False
    assert rec["er9"]["m4_legacy"]["pass"] is False and rec["er9"]["m4_legacy"]["fail_reasons"][0].startswith("rule 2")
    assert G.pass_g(rec, 2.0) is True
    rec2 = G.apply_verdict(_record(stats=_stats(CE_clamped_z=2)))
    assert rec2["pass"] is False and rec2["er7_flag_outside_regime"] is True and G.oor_g(rec2, 2.0) is True
    rec3 = G.apply_verdict(_record(sub="E1-6c", exp="E1-6", stats=_stats(cross_near=3)))
    assert rec3["pass"] is True and rec3["er7_flag_outside_regime"] is False
    assert rec3["rule3_label"] == "magnet model outside validated range"


def test_er9_keys_cover_the_required_fields():
    for k in ("commit", "arm", "grade", "D_val_deg", "table_files", "class_stats", "out_of_regime"):
        assert k in G.ER9_KEYS


def test_dump_roundtrip_and_exclusive_create(tmp_path):
    rec = G.apply_verdict(_record())
    p = tmp_path / "probe" / "PG8" / "E1-2" / "U_s16100.json.gz"
    G.write_record(p, rec)
    assert G.read_record(p)["er9"]["verdict"]["pass"] is True
    with pytest.raises(FileExistsError):
        G.write_record(p, rec)
    assert list(G.load_records(tmp_path / "probe" / "PG8")) == [("E1-2", "U_s16100")]


def test_dump_is_er7_format():
    import gzip
    rec = {"a": 1.5, "b": [1, 2]}
    assert json.loads(gzip.decompress(G.dump(rec))) == rec
    assert G.dump(rec) == G.dump(rec)                             # mtime=0: deterministic bytes


def test_legacy_proxy_flag():
    assert G.legacy_proxy_flag({"max_near_tilt_deg": 18.4, "near_perpendicular": 0}) is False
    assert G.legacy_proxy_flag({"max_near_tilt_deg": 20.1, "near_perpendicular": 0}) is True
    assert G.legacy_proxy_flag({"max_near_tilt_deg": 1.0, "near_perpendicular": 1}) is True
    assert G.legacy_proxy_flag(None) is None


def test_gs_skip_fields_are_exactly_g5s_list_plus_run_metadata():
    assert set(G.GS_LISTED) == {"er7_arm", "mechanism", "magnet_table", "er9_arm", "er9", "wall_s", "er7_wall_s",
                                "loadavg_start"}
    assert G.GS_SKIP == set(G.GS_LISTED) | {"environment", "source_commit", "wall_time_s"}
    for physics in ("rest60", "magnets", "magnet_stats", "pass", "fail_reasons", "per_move", "rest_rotation_deg"):
        assert physics not in G.GS_SKIP


# ---- probe signals -----------------------------------------------------------------------------------------------
def _probe_recs(d_val=2.0, rest=0.1, snap_err=0.1, fail_e12=False, oor_e15=False):
    recs = {}
    for e, n in G.PROBE_COUNTS.items():
        for i in range(n):
            tid = f"{e}_{i}"
            st = _stats(d_val, cross_near=1) if (oor_e15 and e == "E1-5" and i == 0) else _stats(d_val)
            leg = ["M1 criteria"] if (fail_e12 and e == "E1-2" and i == 3) else []
            r = _record(sub=e, stats=st, legacy=leg, d_val=d_val, tid=tid)
            if e == "E1-1":
                r["rest_rotation_deg"] = rest
                r["spec"]["seed"] = r["seed"] = 16000 + i
            if e == "E1-5s":
                r["snap_is_criterion"] = i % 2 == 0
                r["delta_deg"], r["U_err_after_1s_deg"] = 3.0, snap_err
            recs[(e, tid)] = G.apply_verdict(r)
    return recs


def test_probe_signals_all_met():
    s = G.probe_signals(_probe_recs(), 2.0, lambda r: False)
    assert s["signals"]["all_met"] and s["slip_seeds_0_60s"] == [] and s["out_of_regime_trials"] == []


def test_probe_signal_2_rest_and_slips():
    s = G.probe_signals(_probe_recs(rest=0.51), 2.0, lambda r: False)
    assert not s["signals"]["2_rest_le_0.5_and_no_slips"] and s["signals"]["1_snap_scored_all_pass"]
    s = G.probe_signals(_probe_recs(), 2.0, lambda r: r["seed"] == 16003)
    assert not s["signals"]["2_rest_le_0.5_and_no_slips"] and s["slip_seeds_0_60s"] == [16003]


def test_probe_signals_3_and_4():
    s = G.probe_signals(_probe_recs(fail_e12=True), 2.0, lambda r: False)
    assert not s["signals"]["3_e12_e15_all_pass"] and s["signals"]["4_no_operational_trial_out_of_regime"]
    s = G.probe_signals(_probe_recs(oor_e15=True), 2.0, lambda r: False)
    assert not s["signals"]["4_no_operational_trial_out_of_regime"] and not s["signals"]["3_e12_e15_all_pass"]
    assert s["out_of_regime_trials"] == ["E1-5/E1-5_0"]


def test_probe_signals_incomplete_and_d_val_in_force():
    recs = _probe_recs()
    recs.pop(next(iter(recs)))
    assert not G.probe_signals(recs, 2.0, lambda r: False)["signals"]["all_met"]
    with pytest.raises(ValueError):                                # stats split at 2.0 cannot be read at 4.0
        G.probe_signals(_probe_recs(), 4.0, lambda r: False)


# ---- statistics --------------------------------------------------------------------------------------------------
def test_sign_test_known_values():
    s = G.sign_test(10, 0)
    assert s["p_one_sided_lower"] == pytest.approx(1 / 1024) and s["p_two_sided"] == pytest.approx(2 / 1024)
    s = G.sign_test(15, 5)                                         # P[X >= 15], n = 20: 21700 / 2^20
    assert s["p_one_sided_lower"] == pytest.approx(21700 / 2 ** 20) and s["p_two_sided"] == pytest.approx(43400 / 2 ** 20)
    assert G.sign_test(5, 5)["p_two_sided"] == 1.0
    assert G.sign_test(0, 0)["n"] == 0
    assert G.sign_test(0, 3)["p_one_sided_lower"] == 1.0


def test_sign_test_against_scipy():
    from scipy.stats import binomtest
    for k, n in ((14, 20), (3, 17), (12, 12), (7, 15)):
        s = G.sign_test(k, n - k)
        assert s["p_one_sided_lower"] == pytest.approx(binomtest(k, n, 0.5, alternative="greater").pvalue, rel=1e-12)
        assert s["p_two_sided"] == pytest.approx(binomtest(k, n, 0.5).pvalue, rel=1e-12)


def test_clopper_pearson_known_values():
    lo, hi = G.clopper_pearson(0, 20)
    assert lo == 0.0 and hi == pytest.approx(1 - 0.025 ** (1 / 20), rel=1e-10)   # 0.1684: G.10's "17 %"
    assert round(hi, 2) == 0.17
    lo, hi = G.clopper_pearson(20, 20)
    assert hi == 1.0 and lo == pytest.approx(0.025 ** (1 / 20), rel=1e-10)
    lo, hi = G.clopper_pearson(2, 20)
    assert lo == pytest.approx(0.01234, abs=1e-5) and hi == pytest.approx(0.31698, abs=1e-5)


def test_clopper_pearson_matches_d11():
    D11 = _load_d11()
    for k, n in ((0, 60), (2, 60), (5, 20), (60, 60)):
        assert G.clopper_pearson(k, n) == pytest.approx(D11.cp(k, n), rel=1e-12)


def _load_d11():
    p = HERE.parents[1] / "experiments/D11_rest_slip_count/d11_analyze.py"
    spec = importlib.util.spec_from_file_location("d11_analyze_t", p)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def test_fisher_known_values():
    # 0/20 vs 2/20: one-sided C(20,2)/C(40,2) = 190/780; two-sided ~0.49 is the figure U5 quotes
    assert G.fisher_one_sided_less(0, 20, 2, 20) == pytest.approx(190 / 780, rel=1e-12)
    assert 2 * G.fisher_one_sided_less(0, 20, 2, 20) == pytest.approx(0.487, abs=1e-3)
    assert G.fisher_one_sided_less(0, 60, 6, 60) == pytest.approx(math.comb(60, 6) / math.comb(120, 6), rel=1e-12)
    assert G.fisher_one_sided_less(3, 20, 3, 20) > 0.5
    assert G.fisher_one_sided_less(0, 10, 0, 10) == 1.0


def test_fisher_against_scipy():
    from scipy.stats import fisher_exact
    for a, n1, b, n2 in ((0, 60, 2, 60), (0, 60, 6, 60), (1, 60, 8, 60), (5, 60, 2, 60), (0, 20, 2, 20)):
        _, p = fisher_exact([[a, n1 - a], [b, n2 - b]], alternative="less")
        assert G.fisher_one_sided_less(a, n1, b, n2) == pytest.approx(p, rel=1e-10)


def test_slip_reading():
    r = G.slip_reading(0, 60, 6, 60)
    assert r["fisher_one_sided_p"] <= 0.05 and r["reading"] == "fewer slips than L0 in rehearsal"
    assert G.slip_reading(0, 60, 2, 60)["reading"] == "not distinguishable"
    assert G.slip_reading(6, 60, 6, 60)["reading"] == "not distinguishable"


# ---- selection ---------------------------------------------------------------------------------------------------
def test_selection_rule():
    row = lambda ok, med, n: {"all_met": ok, "median_e12_turner_Nm": med, "n_magnets": n}  # noqa: E731
    assert G.select_arm({"PG8": row(True, 0.30, 64), "PG20": row(True, 0.25, 88)}) == "PG20"
    assert G.select_arm({"PG8": row(True, 0.30, 64), "PG20": row(False, 0.25, 88)}) == "PG8"
    assert G.select_arm({"PG8": row(True, 0.30, 64), "PG20": row(True, 0.30, 88)}) == "PG8"   # tie: fewer magnets
    assert G.select_arm({"PG8": row(False, 0.30, 64), "PG20": row(False, 0.25, 88)}) is None
    assert G.select_arm({}) is None


def test_probe_selection_excludes_stopped_arms():
    row = lambda ok, med, n: {"all_met": ok, "median_e12_turner_Nm": med, "n_magnets": n}  # noqa: E731
    rows = {"PG8": row(True, 0.30, 64), "PG20": row(True, 0.25, 88)}
    s = G.probe_selection({"PG8": True, "PG20": False}, rows, {"PG20": ["P4d_PG20.json: D_val < 0.5 deg"]})
    assert s["complete"] and s["selected"] == "PG8" and s["arms_considered"] == ["PG8"]
    assert s["stopped_arms"] == {"PG20": ["P4d_PG20.json: D_val < 0.5 deg"]}
    s = G.probe_selection({"PG8": True, "PG20": False}, rows, {})
    assert not s["complete"] and s["selected"] is None and "PG20" in s["note"]
    s = G.probe_selection({"PG8": False, "PG20": False}, {}, {"PG8": ["x"], "PG20": ["y"]})
    assert not s["complete"] and "every arm stopped" in s["note"]
    s = G.probe_selection({"PG8": True, "PG20": True}, {"PG8": row(False, 0.3, 64), "PG20": row(False, 0.2, 88)}, {})
    assert s["complete"] and s["selected"] is None and "no arm meets" in s["note"]


def test_harness_exception_trial_fails():
    v = G.verdict("E1-2", ["harness exception: RuntimeError: x"], _stats(), 2.0)
    assert not v["pass"] and v["fail_reasons"] == ["harness exception: RuntimeError: x"]


def test_turner_stats():
    recs = [{"per_move": [{"max_turner_torque_Nm": x} for x in (0.2, 0.46, 0.51, 1.0)]}]
    t = G.turner_stats(recs)
    assert t["n_moves"] == 4 and t["median"] == pytest.approx(0.485) and t["max"] == 1.0
    assert t["above_0.45"] == 3 and t["above_0.5"] == 2 and t["at_clip"] == 1
    assert G.turner_stats([]) is None


def test_aggregate_class_stats():
    a = G.aggregate_class_stats([_stats(CE_near_evals=3, CE_max_near_tilt_deg=1.0, CE_min_centre_distance_mm=9.0),
                                 _stats(CE_near_evals=4, CE_max_near_tilt_deg=2.0, CE_min_centre_distance_mm=8.5)])
    assert a["CE_near_evals"] == 7 and a["CE_max_near_tilt_deg"] == 2.0 and a["CE_min_centre_distance_mm"] == 8.5


# ---- cost and memory (G.7) ---------------------------------------------------------------------------------------
def _ref():
    ref = {}
    for e, n in G.FULL_COUNTS.items():
        for i in range(n):
            ref[(e, f"{e}_{i}")] = {"wall_s": 300.0 if e == "E1-1" else 30.0, "steps": 1000.0}
    return ref


def test_projection_from_speed_scales_with_steps_per_s():
    ref = _ref()
    pk = [k for k in ref if k[0] in G.PROBE_EXPS]
    p = G.project_from_speed(ref, {"L0": 100.0, "PG8": 100.0, "PG20": 50.0}, ["PG8", "PG20"], ["L0", "PG8", "PG20"],
                             ["PG8", "PG20"], pk, 100.0)
    assert p["probe_h"]["PG20"] == pytest.approx(2 * p["probe_h"]["PG8"])
    want_pg8 = sum(max(ref[k]["steps"] / 100, ref[k]["wall_s"]) for k in pk) / 3600
    assert p["probe_h"]["PG8"] == pytest.approx(want_pg8)
    assert p["rest40_h"]["L0"] == pytest.approx(40 * 300 / 3600)
    assert p["probe_total_h"] == pytest.approx(sum(p["probe_h"].values()) + sum(p["rest40_h"].values()))


def test_projection_from_measured():
    ref = _ref()
    pk = [k for k in ref if k[0] in G.PROBE_EXPS]
    meas = {"PG20": {k: 2 * ref[k]["wall_s"] for k in pk[:30]}}
    p = G.project_from_measured(ref, meas, ["PG20"], ["L0", "PG20"], ["PG20"], pk)
    assert p["ratio_to_er7_L0"]["PG20"] == pytest.approx(2.0)
    assert p["probe_h"]["PG20"] == pytest.approx(2 * sum(ref[k]["wall_s"] for k in pk) / 3600)
    assert p["full_h"]["PG20"] == pytest.approx(2 * sum(v["wall_s"] for v in ref.values()) / 3600)
    assert p["rest40_h"]["L0"] == pytest.approx(40 * 300 / 3600)


def test_projection_fallbacks():
    ref = _ref()
    pk = [k for k in ref if k[0] in G.PROBE_EXPS]
    fb = {"probe_h": {"PG8": 5.0, "PG20": 9.0}, "rest40_h": {"L0": 3.0, "PG8": 4.0, "PG20": 6.0},
          "full_h": {"PG8": 11.0, "PG20": 21.0}}
    meas = {"PG8": {k: 3 * ref[k]["wall_s"] for k in pk[:10]}}
    p = G.project_from_measured(ref, meas, ["PG8", "PG20"], ["L0", "PG8", "PG20"], ["PG8", "PG20"], pk, {}, fb)
    assert p["ratio_source"]["PG8"] == "probe records" and p["ratio_source"]["PG20"] == "smoke projection"
    assert p["probe_h"]["PG20"] == 9.0 and p["full_h"]["PG20"] == 21.0 and p["rest40_h"]["L0"] == 3.0
    assert p["full_h"]["PG8"] == pytest.approx(3 * sum(v["wall_s"] for v in ref.values()) / 3600)
    r40 = {"PG20": {("E1-1", f"rest_s{s}"): 600.0 for s in range(16700, 16710)}}
    p = G.project_from_measured(ref, {}, ["PG20"], ["PG20"], ["PG20"], pk, r40, fb)
    assert p["ratio_source"]["PG20"] == "rest40 records" and p["ratio_to_er7_L0"]["PG20"] == pytest.approx(2.0)
    assert p["rest40_h"]["PG20"] == pytest.approx(40 * 600 / 3600)


def test_cost_check_files_and_stop(tmp_path):
    assert G.cost_checks_stopped(tmp_path) == []
    _write(tmp_path / "probe" / "cost_check_25_PG8.json", {"stop": False, "reasons": []})
    _write(tmp_path / "rest40" / "cost_check_25_rest40.json", {"stop": True, "reasons": ["probe 30 h > 24 h"]})
    assert len(G.cost_check_files(tmp_path)) == 2
    assert G.cost_checks_stopped(tmp_path) == ["cost_check_25_rest40.json: probe 30 h > 24 h"]


def test_cost_stop_rule():
    ok = {"probe_total_h": 23.9, "full_h": {"PG8": 34.9}}
    assert G.cost_stop(ok, {"stop": False}) == []
    assert len(G.cost_stop({"probe_total_h": 24.1, "full_h": {"PG8": 1}}, {"stop": False})) == 1
    assert len(G.cost_stop({"probe_total_h": 1, "full_h": {"PG8": 35.1, "PG20": 40}}, {"stop": False})) == 2
    two_gb = 2 * 1024 * 1024                                       # kB
    mem = G.memory_check(1_000_000, 4, 4_000_000 + two_gb)         # exactly 2 GB left: not below the limit
    assert not mem["stop"] and mem["max_workers"] == 4
    mem = G.memory_check(1_000_000, 4, 4_000_000 + two_gb - 1)
    assert mem["stop"] and mem["max_workers"] == 3
    mem = G.memory_check(1_100_000, 4, 6_000_000)
    assert mem["stop"] and len(G.cost_stop(ok, mem)) == 1
    assert G.memory_check(None, 4, 1)["stop"] is False


# ---- gates (temporary result folders) ----------------------------------------------------------------------------
def _write(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))


COMMITTED_STATIC = G.ROOT / "selfcheck_static.json"


def _committed_static() -> dict:
    """The committed selfcheck_static.json (read only); its GS5.pass is False and deviation 1 applies."""
    if not COMMITTED_STATIC.exists():
        pytest.skip("committed selfcheck_static.json not present")
    return json.loads(COMMITTED_STATIC.read_text())


def _passing_root(tmp: Path, d_val=2.0):
    _write(tmp / "selfcheck.json", {k: {"pass": True} for k in ("GS1", "GS2", "GS4")})
    ss = _committed_static()
    _write(tmp / "selfcheck_static.json", {k: ss[k] for k in ("GS3", "GS3b", "GS5", "GS6", "pass", "env")})
    st = tmp / "static"
    for a in ("PG8", "PG20"):
        _write(st / f"P1_{a}.json", {"stopped": False})
        _write(st / f"P2_{a}_N52.json", {"stopped": False})
        _write(st / f"P3_{a}.json", {"arm": a, "hard_stop": False, "items": []})
        _write(st / f"P4d_{a}.json", {"label": "PROTOCOL SETTINGS",
                                      "verdict": {"stop_arm": False, "status": "halted", "D_val_deg": d_val}})
    _write(st / "P4_0.json", {"label": "PROTOCOL SETTINGS", "verdict": {"pass": True}})
    return tmp


def test_gates_pass_and_d_val(tmp_path):
    root = _passing_root(tmp_path)
    for a in ("PG8", "PG20", "L0"):
        assert G.gate_problems(a, root, check_commits=False) == []
    rep = G.gate_report("PG8", root, check_commits=False)
    assert any("deviation 1" in n for n in rep["notes"])
    assert G.d_val_for("PG20", root) == 2.0 and G.d_val_for("L0", root) == math.inf


def test_gs5_read_per_deviation_1_on_the_committed_file():
    gs5 = _committed_static()["GS5"]
    assert gs5["pass"] is False                                     # the plain GS5 flag would refuse
    ok, note = G.gs5_deviation1(gs5)
    assert ok and "deviation 1" in note and "er3_row_pass=False" in note
    for path in (("40_only", "pass"), ("48_only", "with_er3_magnet_order", "pass"), ("48_only", "probe5_pass")):
        g = copy.deepcopy(gs5)
        d = g
        for k in path[:-1]:
            d = d[k]
        d[path[-1]] = False
        assert G.gs5_deviation1(g)[0] is False, path


def _set(path, key, value):
    d = json.loads(path.read_text())
    d[key] = value
    _write(path, d)


def _set_gs5(r, *keys):
    d = json.loads((r / "selfcheck_static.json").read_text())
    x = d["GS5"]
    for k in keys[:-1]:
        x = x[k]
    x[keys[-1]] = False
    _write(r / "selfcheck_static.json", d)


@pytest.mark.parametrize("breaker", [
    lambda r: (r / "selfcheck.json").unlink(),
    lambda r: _write(r / "selfcheck.json", {"GS1": {"pass": True}, "GS2": {"pass": False}, "GS4": {"pass": True}}),
    lambda r: _set(r / "selfcheck_static.json", "GS3b", {"pass": False}),
    lambda r: _set(r / "selfcheck_static.json", "GS6", {"pass": False}),
    lambda r: _set_gs5(r, "48_only", "with_er3_magnet_order", "pass"),
    lambda r: _set_gs5(r, "40_only", "pass"),
    lambda r: (r / "static" / "P3_PG8.json").unlink(),
    lambda r: _write(r / "static" / "P3_PG8.json", {"arm": "PG8", "hard_stop": True, "items": []}),
    lambda r: _write(r / "static" / "P3_PG8.json", {"arm": "PG20", "hard_stop": False, "items": []}),
    lambda r: (r / "static" / "P1_PG8.json").unlink(),
    lambda r: _write(r / "static" / "P1_PG8.json", {"stopped": True}),
    lambda r: _write(r / "static" / "P2_PG8_N52.json", {"stopped": True}),
    lambda r: _write(r / "static" / "P4_0.json", {"label": "PROTOCOL SETTINGS", "verdict": {"pass": False}}),
    lambda r: _write(r / "static" / "P4_0.json", {"label": "NOT PROTOCOL SETTINGS (test run; not a result)",
                                                  "verdict": {"pass": True}}),
    lambda r: _write(r / "static" / "P4d_PG8.json", {"label": "PROTOCOL SETTINGS",
                                                     "verdict": {"stop_arm": True, "status": "halted",
                                                                 "D_val_deg": 0.0}}),
    lambda r: _write(r / "static" / "P4d_PG8.json", {"label": "PROTOCOL SETTINGS",
                                                     "verdict": {"stop_arm": False, "status": "session",
                                                                 "D_val_deg": 2.0}}),
    lambda r: (r / "static" / "P4d_PG8.json").unlink()])
def test_gates_refuse(tmp_path, breaker):
    root = _passing_root(tmp_path)
    breaker(root)
    assert G.gate_problems("PG8", root, check_commits=False)


def test_p40_needed_for_pg8_only(tmp_path):
    root = _passing_root(tmp_path)
    (root / "static" / "P4_0.json").unlink()
    assert G.gate_problems("PG8", root, check_commits=False)
    assert G.gate_problems("PG20", root, check_commits=False) == []


def test_gate_commit_fields():
    assert G.gate_commit({"commit": "a"}) == "a"
    assert G.gate_commit({"env": {"commit": "b"}}) == "b"
    assert G.gate_commit({"git": {"commit": "c"}}) == "c"
    assert G.gate_commit({}) is None
    assert G.provenance("x.json", "P1", {})[0] == ["x.json: no commit recorded"]


def test_judge_changes_accepts_only_listed_commit_and_path():
    c = "65866d695f98ec10b1e977dc0360d0907fd05e40"
    lay = "experiments/ER9_anchored_core_layouts/er9g_layouts.py"
    bad, notes = G.judge_changes([(c, lay)])
    assert bad == [] and len(notes) == 1
    bad, _ = G.judge_changes([(c, "experiments/ER9_anchored_core_layouts/er9g_stats.py"), ("deadbeef" * 5, lay)])
    assert len(bad) == 2


def test_gate_deps_and_frozen_paths():
    assert set(G.GATE_DEPS) == {"selfcheck", "replay_selfcheck", "selfcheck_static", "P1", "P2", "P3", "P4"}
    for deps in G.GATE_DEPS.values():
        assert set(deps) <= set(G.FROZEN_PATHS)
    for p in ("experiments/D8_alignment/magnets.py", "experiments/ER7_core_magnet_rehearsal/results/L0",
              "experiments/ER7_core_magnet_rehearsal/results/C52",
              "experiments/ER7_core_magnet_rehearsal/posthoc/snap_L0_s16568_+8.json",
              "experiments/ER7_core_magnet_rehearsal/posthoc/snap_C52_s16568_+8.json"):
        assert p in G.FROZEN_PATHS
    assert "experiments/ER9_anchored_core_layouts/er9g_v3turn.py" not in G.GATE_DEPS["selfcheck_static"]


def test_committed_static_selfcheck_provenance_is_current():
    """Repository state: the committed selfcheck_static.json (77ba5b2) is still valid at HEAD, with 65866d6's
    install_er7 key change accepted."""
    probs, notes = G.provenance("selfcheck_static.json", "selfcheck_static", _committed_static())
    assert probs == [], probs


def test_no_d_val_refused(tmp_path):
    with pytest.raises(G.Refused):
        G.d_val_for("PG8", tmp_path)


def test_manifest(tmp_path):
    f = tmp_path / "probe" / "PG8"
    assert G.manifest_problems(f, "abc", False) == []
    G.write_record(f / "E1-2" / "U_s16100.json.gz", {"x": 1})
    assert G.manifest_problems(f, "abc", False)                    # records without a manifest
    G.write_manifest(f, {"commit": "abc"})
    assert G.manifest_problems(f, "abc", False) == []
    assert G.manifest_problems(f, "def", False)                    # another commit, not resuming
    G.write_manifest(f, {"commit": "zzz"})                         # never overwritten
    assert json.loads((f / "environment.json").read_text())["commit"] == "abc"


def test_outside_repo_guard(tmp_path):
    assert G.outside_repo(tmp_path) == tmp_path.resolve()
    with pytest.raises(G.Refused):
        G.outside_repo(G.ROOT / "dev")


def test_frozen_paths_cover_part_g_code():
    for f in ("er9g_layouts.py", "er9g_stats.py", "er9g_scan.py", "er9g_static.py", "er9g_v3turn.py", "er9g_run.py",
              "er9g_replay.py", "PROTOCOL.md"):
        assert f"experiments/ER9_anchored_core_layouts/{f}" in G.PART_G_CODE
    assert "src" in G.FROZEN_PATHS and "experiments/ER7_core_magnet_rehearsal/er7_run.py" in G.FROZEN_PATHS


# ---- replay comparison -------------------------------------------------------------------------------------------
def test_replay_compare_exact_on_reference_fields():
    ref = {"a": 1.0, "s": [{"t": 0.5, "x": 2}], "n": None}
    assert RP.compare(ref, copy.deepcopy(ref) | {"extra": 3}) == []
    got = copy.deepcopy(ref); got["s"][0]["t"] = 0.5000000001
    assert RP.compare(ref, got) == ["/s[0]/t: 0.5 != 0.5000000001"]
    assert RP.compare(ref, {"a": 1.0, "s": []}) and RP.compare(ref, {"s": [{"t": 0.5, "x": 2}], "n": None})


# ---- pool: a killed worker does not hang the run -----------------------------------------------------------------
def _fake_run_one(job):
    import os as _os
    if job["tid"] == "die":
        _os._exit(9)                                               # as an out-of-memory kill: no result, no error
    return {"er9_arm": job["er9g_arm"], "experiment": job["exp"], "trial_id": job["tid"], "kind": "seq",
            "pass": True, "fail_reasons": [], "er9": {"out_of_regime": False}}


def test_run_pool_records_lost_trial_and_stops(tmp_path, monkeypatch):
    monkeypatch.setattr(G, "run_one", _fake_run_one)
    jobs = [{"er9g_arm": "L0", "exp": "E1-2", "tid": t, "kw": {"seed": 16100}} for t in ("ok1", "die", "ok2", "ok3")]
    with pytest.raises(RuntimeError, match="lost to a dead worker"):
        G.run_pool(jobs, tmp_path, "dev", 1, poll_s=0.2, grace_s=0.5, start_timeout_s=30)
    lines = [json.loads(x) for x in (tmp_path / "dev" / "not_run.jsonl").read_text().splitlines()]
    assert [(x["arm"], x["exp"], x["tid"]) for x in lines] == [("L0", "E1-2", "die")]
    written = sorted(p.name for p in (tmp_path / "dev").rglob("*.json.gz"))
    assert written == ["ok1.json.gz"]                              # no new trial started after the loss


def test_run_pool_normal(tmp_path, monkeypatch):
    monkeypatch.setattr(G, "run_one", _fake_run_one)
    jobs = [{"er9g_arm": "L0", "exp": "E1-2", "tid": t, "kw": {"seed": 16100}} for t in ("a", "b", "c")]
    r = G.run_pool(jobs, tmp_path, "dev", 2, poll_s=0.2, grace_s=0.5)
    assert r == {"done": 3, "paused": False, "remaining": 0}
    assert not (tmp_path / "dev" / "not_run.jsonl").exists()


def test_find_lost():
    now = 100.0
    inflight = {"a": {"pid": 1, "submitted": 0.0, "gone_since": None},
                "b": {"pid": 2, "submitted": 0.0, "gone_since": 50.0},
                "c": {"pid": None, "submitted": 0.0, "gone_since": None},
                "d": {"pid": None, "submitted": 95.0, "gone_since": None}}
    lost = G.find_lost(inflight, now, lambda pid: pid == 1, grace_s=30, start_timeout_s=60)
    assert sorted(lost) == ["b", "c"]
    assert inflight["a"]["gone_since"] is None
