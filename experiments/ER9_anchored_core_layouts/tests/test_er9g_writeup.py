"""Tests for the Part G write-up tables (er9g_writeup.py; PROTOCOL.md G.8, G.9; DECISION_LOG P-70).

Every probe report here is SYNTHETIC: built in the test with er9g_run's own helpers (probe_selection, sign_test,
slip_reading, turner_stats, aggregate_class_stats) so that its schema matches what `er9g_run.py report` writes, and
filled with obviously fake numbers (medians 0.111 / 0.222 N.m, rest values 0.0123 deg, ...). No real probe report or
probe record is read, and nothing is simulated. The only real files read are the committed static pre-checks
(results/hybrid_g/static/, selfcheck*.json), in test_static_only_on_committed_files.
Run (WSL, repo root):
  ~/.venvs/rubiknetic/bin/python -m pytest experiments/ER9_anchored_core_layouts/tests/test_er9g_writeup.py -q
"""
from __future__ import annotations

import gzip
import importlib.util
import inspect
import json
import re
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


W = _load("er9g_writeup")
G = _load("er9g_run")
ST = G.ST

D_VAL = 12.0     # FAKE D_val for both synthetic arms


# ---- synthetic inputs ----------------------------------------------------------------------------------------------
def cs(**over) -> dict:
    """A synthetic per-trial class_stats dict with every key er9g_stats.ClassStats.as_dict writes, all in regime."""
    d = {"calls": 10}
    for k in W.CLASSES:
        d.update({f"{k}_near_evals": 0, f"{k}_near_perpendicular": 0, f"{k}_max_near_tilt_deg": 0.0,
                  f"{k}_clamped_z": 0, f"{k}_min_centre_distance_mm": 9.9})
    d.update({"X_piece_piece_min_centre_distance_mm": 9.9, "PC_max_path_dev_deg": 0.0,
              "PC_max_path_dev_deg_clamped": 0.0, "D_val_deg": D_VAL, "cross_near": 0,
              "legacy": {"max_near_tilt_deg": 0.0, "near_perpendicular": 0, "clamped_z": 0, "calls": 10}})
    d.update(over)
    return d


def turner(values) -> dict:
    return G.turner_stats([{"per_move": [{"max_turner_torque_Nm": v}]} for v in values])


def arm_entry(n_mag: int, med: float, *, s1=True, s2=True, s3=True, s4=True, complete=True, clip=0,
              stats=None, slips_probe=(), slips60=(1, 60), l0_60=(5, 60)) -> dict:
    vals = [med] * (24 - clip) + [1.0] * clip          # 24 fake E1-2 moves, `clip` of them at the clip
    sig = {"complete": complete, "1_snap_scored_all_pass": s1 and complete, "2_rest_le_0.5_and_no_slips": s2 and complete,
           "3_e12_e15_all_pass": s3 and complete, "4_no_operational_trial_out_of_regime": s4 and complete}
    sig["all_met"] = all(sig.values())
    stats = stats or [cs()]
    return {"n": 106 if complete else 50, "signals": sig, "slip_seeds_0_60s": list(slips_probe),
            "out_of_regime_trials": [] if s4 else ["E1-2/U_s16100"], "failed": [] if sig["all_met"] else ["E1-2/U_s16100"],
            "n_magnets": n_mag, "turner_E1-2_Nm": turner(vals),
            "paired_rest_vs_L0": {**G.sign_test(17, 2), "n_seeds": 20, "n_ties": 1},
            "slip_seeds_60": G.slip_reading(slips60[0], slips60[1], l0_60[0], l0_60[1]),
            "slip_seeds_60_complete": True,
            "rest_on_L0_slip_seeds": {16003: {"rest_rotation_deg": 0.0123, "rest60_rotation_deg": 0.0124,
                                              "slip_events_60s": 0},
                                      16005: {"rest_rotation_deg": 0.0125, "rest60_rotation_deg": 0.0126,
                                              "slip_events_60s": 0}},
            "snap_back": sorted([["snap_+1_s16551", 1.0, 0.777, True], ["snap_+3_s16553", 3.0, 0.0333, True],
                                 ["snap_-8_s16558", -8.0, -0.0888, True]]),
            "class_stats_max": G.aggregate_class_stats(stats), "largest_d_deg": 1.11,
            "legacy_proxy_flag_20deg_trials": [], "steps_per_s_median": 1234.0, "wall_h": 1.5}


def synth_report(arms: dict, stopped: dict | None = None) -> dict:
    """arms: {name: arm_entry(...)}; selection through er9g_run.probe_selection; JSON round trip (int keys ->
    strings, as in the written report.json)."""
    stopped = stopped or {}
    sel_rows = {a: {"all_met": r["signals"]["all_met"], "median_e12_turner_Nm": r["turner_E1-2_Nm"]["median"],
                    "n_magnets": r["n_magnets"]} for a, r in arms.items()}
    done = {a: r["signals"]["complete"] for a, r in arms.items()}
    for a in stopped:
        done.setdefault(a, False)
    rep = {"arms": arms, "D_val": {a: D_VAL for a in arms},
           "turner_references_E1-2": {k: turner([m] * 24) for k, m in
                                      (("L0", 0.0144), ("C52", 0.07), ("W3", 0.0947), ("HB1", 0.0461),
                                       ("HB2", 0.037), ("HB3", 0.0388))},
           "turner_references_full_run": {"L0": turner([0.0203] * 10), "C52": turner([0.0645] * 10)},
           "gravity_sag_from_smoke": {"L0": 0.0229, "PG8": 0.0331, "PG20": 0.0442},
           "gates": {a: {"arm": a, "problems": [], "notes": []} for a in arms},
           "selection": G.probe_selection(done, sel_rows, stopped)}
    if rep["selection"]["complete"]:
        rep["cost"] = {"rest40_h": {"L0": 0.5, "PG8": 0.6, "PG20": 0.7}}
    return json.loads(json.dumps(rep, default=float))


def write_rest(root: Path, mode: str, arm: str, values: dict) -> None:
    d = root / mode / arm / "E1-1"
    d.mkdir(parents=True, exist_ok=True)
    for s, v in values.items():
        rec = {"seed": s, "spec": {"seed": s}, "rest_rotation_deg": v, "sub_experiment": "E1-1"}
        (d / f"rest_s{s}.json.gz").write_bytes(gzip.compress(json.dumps(rec).encode()))


def refs(tmp: Path) -> tuple[Path, Path, Path]:
    def row(rest, wall):
        return {"rest_max_deg": rest, "wall_s_total": wall,
                "snap_abs_err_by_delta": {"1": [0.9, 0.1], "3": [0.031, 0.0], "8": [0.032, 0.0]},
                "e12_turner_Nm": {"median": 0.5, "max": 0.6, "clip_moves": 0}}
    w3 = tmp / "w3.json"; w3.write_text(json.dumps({"L0": row(0.0568, 3600), "C52": row(0.0001, 7200),
                                                     "W3": row(0.0011, 10800)}))
    hb = tmp / "hb.json"; hb.write_text(json.dumps({h: row(0.04, 36000) for h in ("HB1", "HB2", "HB3")}))
    er7 = tmp / "er7.json"; er7.write_text(json.dumps({"arms": {"L0": {"slip_seeds_0_60s": 2},
                                                                "C52": {"slip_seeds_0_60s": 0}}}))
    return w3, hb, er7


def build(tmp: Path, rep: dict, rest=None) -> str:
    root = tmp / "hybrid_g"
    (root / "probe").mkdir(parents=True, exist_ok=True)
    p = root / "probe" / "report.json"
    p.write_text(json.dumps(rep))
    for (mode, arm), vals in (rest or {}).items():
        write_rest(root, mode, arm, vals)
    w3, hb, er7 = refs(tmp)
    return W.build(p, root=root, w3_path=w3, hb_path=hb, er7_path=er7)


_CELL = re.compile(r"(?<!\\)\|")


def md_tables(text: str) -> list[list[list[str]]]:
    """Markdown tables as lists of rows of cells (escaped pipes are not separators)."""
    out, cur = [], []
    for line in text.splitlines():
        if line.startswith("|"):
            cur.append([c.strip() for c in _CELL.split(line)[1:-1]])
        elif cur:
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out


# ---- G.4 conditions: the write-up's list against the runner's rule -------------------------------------------------
def test_conditions_match_er9g_stats_out_of_regime():
    assert not ST.out_of_regime(cs(), D_VAL) and W.exceeded_conditions(cs()) == []
    for cls, key, lim in W.G4_CONDITIONS:
        bad = cs(**{key: lim + (0.01 if isinstance(lim, float) else 1)})
        assert ST.out_of_regime(bad, D_VAL), key
        ex = W.exceeded_conditions(bad)
        assert [(c, k) for c, k, *_ in ex] == [(cls, key)], key
        assert G.oor_reasons(bad, D_VAL)[0].startswith(key)
        at = cs(**{key: lim})                                    # at the limit: in regime ("> limit")
        assert not ST.out_of_regime(at, D_VAL) and W.exceeded_conditions(at) == []
    assert len(W.G4_CONDITIONS) == 12


def test_reasons_by_class_text():
    s = cs(cross_near=7, PCoff_max_near_tilt_deg=9.5, CE_clamped_z=2)
    assert W.reasons_by_class(s) == ("CE: CE_clamped_z 2 > 0; PCoff: PCoff_max_near_tilt_deg 9.50 > 7.5; "
                                     "X: cross_near 7 > 0")
    assert W.reasons_by_class(cs()) == "none" and W.reasons_by_class(None) == "none"


def test_report_keys_read_here_are_written_by_er9g_run_report():
    """Schema guard: every report.json key this write-up reads is written by er9g_run.report / its helpers."""
    src = "".join(inspect.getsource(fn) for fn in (G.report, G.probe_signals, G.probe_selection, G.turner_stats,
                                                   G.sign_test, G.slip_reading, G.project_from_measured))
    for k in ("arms", "D_val", "signals", "slip_seeds_0_60s", "out_of_regime_trials", "failed", "n_magnets",
              "turner_E1-2_Nm", "paired_rest_vs_L0", "n_seeds", "n_ties", "n_lower", "p_one_sided_lower",
              "p_two_sided", "slip_seeds_60", "slip_seeds_60_complete", "arm_ci95", "L0_ci95", "fisher_one_sided_p",
              "reading", "rest_on_L0_slip_seeds", "rest_rotation_deg", "rest60_rotation_deg", "slip_events_60s",
              "snap_back", "class_stats_max", "largest_d_deg", "legacy_proxy_flag_20deg_trials",
              "steps_per_s_median", "wall_h", "turner_references_E1-2", "turner_references_full_run",
              "gravity_sag_from_smoke", "selection", "cost", "rest40_h", "complete", "arms_considered",
              "stopped_arms", "rows", "selected", "note", "all_met", "median_e12_turner_Nm", "median", "p99",
              "max", "above_0.45", "above_0.5", "at_clip", "n_moves",
              "1_snap_scored_all_pass", "2_rest_le_0.5_and_no_slips", "3_e12_e15_all_pass",
              "4_no_operational_trial_out_of_regime"):
        assert f'"{k}"' in src, k
    # snap_back rows are [trial_id, delta_deg, U_err_after_1s_deg, pass]
    assert '[r["trial_id"], r["delta_deg"], r["U_err_after_1s_deg"], pass_g(r, dv)]' in src


# ---- table structure -----------------------------------------------------------------------------------------------
def both_met():
    return {"PG8": arm_entry(64, 0.111), "PG20": arm_entry(88, 0.222)}


def test_tables_structure_and_fake_numbers(tmp_path):
    rest = {("probe", "PG8"): {16000: 0.0123, 16003: 0.0234}, ("probe", "PG20"): {16000: 0.0345},
            ("rest40", "L0"): {16700: 0.0456}, ("rest40", "PG8"): {16700: 0.0567}}
    text = build(tmp_path, synth_report(both_met()), rest)
    for h in ("### (a)", "### (b)", "### (c)", "### (d)", "### (e)"):
        assert h in text, h
    assert "### (f)" not in text                                   # no full rehearsal
    tabs = md_tables(text)
    assert len(tabs) >= 12
    for t in tabs:                                                 # header, separator, rows: same width
        assert len({len(r) for r in t}) == 1, t[0]
        assert set("".join(t[1])) <= {"-"}
    # (b): fake medians, rest max derived from the synthetic records, snap max over scored starts only
    sig = next(t for t in tabs if t[0][0] == "Arm" and "All four" in t[0])
    assert [r[0] for r in sig[2:]] == ["PG8", "PG20"]
    assert "rest max 0.023 deg" in sig[2][4] and "rest max 0.035 deg" in sig[3][4]
    assert "max \\|err\\| 0.089 deg" in sig[2][3]                   # 0.777 at +1 deg is not scored
    # (c): PG rows then the six references, in order; fake turner medians
    rep_t = next(t for t in tabs if "Rest max (deg)" in t[0] and "Summed trial wall time (h)" in t[0])
    assert [r[0] for r in rep_t[2:]] == ["**PG8**", "**PG20**", "L0", "C52", "W3", "HB1", "HB2", "HB3"]
    assert rep_t[2][4].startswith("0.111 / ") and rep_t[3][4].startswith("0.222 / ")
    assert rep_t[2][2] == "0.089" and rep_t[2][3] == "0.777"
    assert rep_t[4][1] == "0.057" and rep_t[4][2] == "0.032" and rep_t[4][3] == "0.900" and rep_t[4][8] == "1.0"
    assert rep_t[2][8] == "1.5 (+ rest40 0.6)"
    # (d): slip counts derived (probe / rest40) for arm and L0
    slip = next(t for t in tabs if "Fisher one-sided p" in t[0])
    assert slip[2][1] == "1 / 60" and slip[2][4] == "5 / 60" and slip[2][5] == "2 / 3"
    r40 = next(t for t in tabs if t[0] == ["Arm", "Records", "Rest max (deg)"])
    assert r40[2] == ["L0", "1", "0.046"] and r40[3] == ["PG8", "1", "0.057"] and r40[4] == ["PG20", "n/a", "n/a"]
    seeds = next(t for t in tabs if "D11 slip events (60 s)" in t[0])
    assert [r[1] for r in seeds[2:]] == ["16003", "16005", "16003", "16005"]
    assert "FACT — source:" in text and "INFERENCE" not in text


def test_missing_rest_records_print_na(tmp_path):
    text = build(tmp_path, synth_report(both_met()))
    sig = next(t for t in md_tables(text) if "All four" in t[0])
    assert "rest max n/a deg" in sig[2][4]


def test_missing_report_refuses(tmp_path):
    with pytest.raises(SystemExit):
        W.build(tmp_path / "none.json", root=tmp_path)


# ---- selection and P-70 branches -----------------------------------------------------------------------------------
def status(text: str) -> dict:
    t = next(t for t in md_tables(text) if t[0][0] == "Pre-commitment")
    return {int(r[0].split()[-1]): r[2] for r in t[2:]}


def test_both_met_lowest_median_selected_no_pause(tmp_path):
    rep = synth_report(both_met())
    b = W.p70_branch(rep)
    assert b["state"] == "selected" and b["selected"] == "PG8"
    assert [b["items"][i]["applies"] for i in (1, 2, 3)] == [False, False, False]
    assert status(build(tmp_path, rep)) == {1: "does not apply", 2: "does not apply", 3: "does not apply"}
    assert "**Selected: PG8.**" in build(tmp_path, rep)


def test_item3_pause_on_median(tmp_path):
    rep = synth_report({"PG8": arm_entry(64, 0.456, s2=False), "PG20": arm_entry(88, 0.456)})
    b = W.p70_branch(rep)
    assert b["selected"] == "PG20" and b["items"][3]["applies"] is True and b["items"][1]["applies"] is False
    assert status(build(tmp_path, rep))[3] == "**applies**"


def test_item3_median_exactly_045_pauses():
    rep = synth_report({"PG8": arm_entry(64, 0.45), "PG20": arm_entry(88, 0.46)})
    assert W.p70_branch(rep)["items"][3]["applies"] is True


def test_item3_pause_on_any_clip():
    rep = synth_report({"PG8": arm_entry(64, 0.111, clip=1), "PG20": arm_entry(88, 0.222)})
    b = W.p70_branch(rep)
    assert rep["arms"]["PG8"]["turner_E1-2_Nm"]["at_clip"] == 1 and rep["arms"]["PG8"]["turner_E1-2_Nm"]["median"] < 0.45
    assert b["selected"] == "PG8" and b["items"][3]["applies"] is True


def test_tie_goes_to_fewer_magnets():
    rep = synth_report({"PG8": arm_entry(64, 0.222), "PG20": arm_entry(88, 0.222)})
    assert W.p70_branch(rep)["selected"] == "PG8"


def test_none_met_item1_and_item2_only_cross_or_offpath(tmp_path):
    rep = synth_report({"PG8": arm_entry(64, 0.111, s4=False, stats=[cs(), cs(cross_near=3)]),
                        "PG20": arm_entry(88, 0.222, s4=False, stats=[cs(CE_max_near_tilt_deg=6.0)])})
    b = W.p70_branch(rep)
    assert b["state"] == "none_selected" and b["selected"] is None
    assert b["items"][1]["applies"] is True and b["items"][2]["applies"] is True and b["items"][3]["applies"] is False
    assert b["item2_per_arm"]["PG8"] == {"signal4_failed": True, "only_X_or_PCoff": True, "classes": ["X"],
                                         "signal4_only_failure": True}
    assert b["item2_per_arm"]["PG20"]["only_X_or_PCoff"] is False and b["item2_per_arm"]["PG20"]["classes"] == ["CE"]
    text = build(tmp_path, rep)
    assert status(text) == {1: "**applies**", 2: "**applies**", 3: "does not apply"}
    assert "no arm meets all four signals" in text and "**Selected: none.**" in text
    sig = next(t for t in md_tables(text) if "All four" in t[0])
    assert "X: cross_near 3 > 0" in sig[2][6] and "CE: CE_max_near_tilt_deg 6.00 > 5" in sig[3][6]


def test_item2_pcoff_with_other_signal_failing():
    rep = synth_report({"PG8": arm_entry(64, 0.111, s4=False, s1=False, stats=[cs(PCoff_clamped_z=4)]),
                        "PG20": arm_entry(88, 0.222, s2=False)})
    b = W.p70_branch(rep)
    assert b["items"][1]["applies"] is True and b["items"][2]["applies"] is True
    assert b["item2_per_arm"]["PG8"]["signal4_only_failure"] is False
    assert b["item2_per_arm"]["PG20"]["signal4_failed"] is False


def test_item2_not_when_ce_or_pcon_or_pp3_involved():
    for bad in ({"CE_near_perpendicular": 1}, {"PCon_max_near_tilt_deg": 20.5}, {"PP3_clamped_z": 1}):
        rep = synth_report({"PG8": arm_entry(64, 0.111, s4=False, stats=[cs(cross_near=2, **bad)]),
                            "PG20": arm_entry(88, 0.222, s4=False, stats=[cs(**bad)])})
        b = W.p70_branch(rep)
        assert b["items"][1]["applies"] is True and b["items"][2]["applies"] is False, bad


def test_none_met_without_signal4_failure():
    rep = synth_report({"PG8": arm_entry(64, 0.111, s2=False), "PG20": arm_entry(88, 0.222, s1=False)})
    b = W.p70_branch(rep)
    assert b["items"][1]["applies"] is True and b["items"][2]["applies"] is False


def test_incomplete_probe_reaches_no_branch(tmp_path):
    rep = synth_report({"PG8": arm_entry(64, 0.111), "PG20": arm_entry(88, 0.222, complete=False)})
    b = W.p70_branch(rep)
    assert b["state"] == "incomplete" and all(b["items"][i]["applies"] is None for i in (1, 2, 3))
    assert status(build(tmp_path, rep)) == {1: "not reached", 2: "not reached", 3: "not reached"}


def test_stopped_arm_excluded_and_all_stopped():
    rep = synth_report({"PG8": arm_entry(64, 0.111)}, stopped={"PG20": ["P4d_PG20.json missing"]})
    b = W.p70_branch(rep)
    assert b["selected"] == "PG8" and rep["selection"]["arms_considered"] == ["PG8"]
    rep2 = synth_report({}, stopped={"PG8": ["x"], "PG20": ["y"]})
    assert W.p70_branch(rep2)["state"] == "all_stopped"


# ---- G.9 reading branches ------------------------------------------------------------------------------------------
def full(s1=True, s2=True, s3=True, clip=0, e15s_failed=()):
    s = {"1_no_slips_and_rest_le_0.5": s1, "2_option_a_rule": s2, "3_no_operational_trial_out_of_regime": s3}
    s["all_met"] = all(s.values())
    return {"signals": s, "turner_Nm": {"at_clip": clip}, "rows": {"E1-5s": {"failed": list(e15s_failed)}}}


def test_g9_branches():
    assert W.g9_branches(full()) == ["all_no_clip"]
    assert W.g9_branches(full(clip=3)) == ["all_clip"]
    assert W.g9_branches(full(s1=False)) == ["1", "any"]
    assert W.g9_branches(full(s2=False, e15s_failed=["snap_+8_s16558"])) == ["2", "any"]
    assert W.g9_branches(full(s2=False)) == ["any"]
    assert W.g9_branches(full(s3=False, s1=False)) == ["1", "3", "any"]


# ---- static tables on the committed static files (allowed: results/hybrid_g/static, selfcheck*.json) -------------
def test_static_only_on_committed_files():
    text = W.build(static_only=True)
    assert "### (b)" not in text
    tabs = md_tables(text)
    for t in tabs:
        assert len({len(r) for r in t}) == 1, t[0]
    p2 = next(t for t in tabs if t[0][0] == "Row")
    assert [r[0] for r in p2[2:]] == [f"{a} {g}" for a, g in W.P2_ROWS]
    assert "P4.d PG8" in text and "P4.d PG20" in text and "**Arm stopped by P1** | no | no" in text
