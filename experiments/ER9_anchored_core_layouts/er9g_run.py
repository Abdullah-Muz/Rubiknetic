"""ER9 Part G runner (PROTOCOL.md, Part G: G.4, G.5, G.7, G.8, G.9, G.11, G.12). Exploratory and unscored.

Every trial is ER7's trial (experiments/ER7_core_magnet_rehearsal/er7_run.py run_one, unchanged) in a fresh worker
process (fork pool, maxtasksperchild=1), with the arm's MagnetSystem installed by er9g_layouts.install_er7 (composite
system: same-type pairs with their own table, cross-type pairs dipole-only; no force-law code here) and the per-class
diagnostic er9g_stats (with_class_stats(M4.RecordingMagnetSystem); attach() once, at the start of the trial).

Arm registry (G.3 "Arm names"; any other name is refused):
  probe / full / smoke   PG8, PG20            (PG20r only with --u4-changed: U4 default is "no dynamics")
  rest40                 L0, PG8, PG20        (U5 extension, seeds 16700-16739)
  selfcheck (internal)   L0 (GS1, 48 only), C52 (GS2, 40 only), PG20 (GS4)
Every arm with M5's 4x2 magnets runs as ER7 arm "L0" (M5's tilt and 4x2 table record; no TABLES_PROVIDER); only GS2
runs as ER7 arm "C52". ER7's legacy rule 2 (aggregate tilt against M5's 5 deg) is replaced in Part G records by G.4's
per-class rule (verdict(); the legacy verdict is kept under rec["er9"]["m4_legacy"]).

Modes (WSL, repo root; ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9g_run.py MODE ...):
  selfcheck            GS1 (L0 via the composite, 48 only; first trial of each of ER7's ten sub-experiments against
                       ER7's committed L0 records), GS2 (the same for C52, 40 only), GS4 (PG20 E1-2 seed 16120 with
                       and without the diagnostic). Writes results/hybrid_g/selfcheck.json (exclusive create).
  smoke                G.7: per arm (and L0 as the speed reference) one single-turn replay (seed 16100, first U of
                       an E1-2 trial) and one snap-back replay (seed 16568, +8 deg, ER7's posthoc snap_diag method)
                       through er9g_replay.py, each in its own process under /usr/bin/time -v; the reported items
                       and the cost stop rule. Writes results/hybrid_g/smoke/ (exclusive create).
  probe [--arms ..]    G.8: ER7's E1-1 (with D10's instrumented 60 s rest), E1-2, E1-5s, E1-5 per arm (106 each).
                       Cost re-check after 25 % of the trials (G.7); pauses after the trials in flight if over.
  rest40 [--arms ..]   U5: E1-1 configuration (60 s instrumented rest) on seeds 16700-16739, arms L0, PG8, PG20.
  report               G.8 signals 1-4 (G.4 per-trial rule, D_val in force), the pre-declared reported items, the
                       selection rule; G.9 signals for any arm with full-rehearsal records.
  full --arm ARM       G.9: ER7's 204 trials for the selected arm.
  dev --root DIR       debugging only: one L0 (or C52) trial through the runner, compared with ER7's record; writes
                       only to DIR, which must be outside the repository. Part G arms are refused.
Records: results/hybrid_g/{probe,rest40,full}/<arm>/<exp>/<tid>.json.gz (exclusive create; existing records are
skipped, so a rerun resumes). Each carries rec["er9"]: commit, arm, grade, D_val, table files, per-class stats,
out_of_regime, the Part G verdict and the M4 legacy verdict.
Refusals: unregistered arm; seed outside 16000-16999 (and 10000-10999, 17000-17999 always); --jobs outside 1-6;
Part G code or its dependencies uncommitted or modified (FROZEN_PATHS); for probe/rest40/full/smoke: GS1, GS2, GS4
(selfcheck.json), GS3/GS5/GS6 (selfcheck_static.json), the arm's P1, P2 (N52), P4.0 (PG8) and P4.d files absent or not
passing, or no D_val; records from another commit in the target folder unless --resume (and then only if FROZEN_PATHS
are unchanged between that commit and HEAD).
"""
from __future__ import annotations

import argparse
import copy
import gzip
import importlib.util
import json
import math
import multiprocessing as mp_
import os
import queue
import resource
import subprocess
import sys
import time
from math import comb
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ROOT = HERE / "results" / "hybrid_g"
ER7_RES = REPO / "experiments/ER7_core_magnet_rehearsal/results"
ER9_RES = HERE / "results"


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


LY = _load("er9g_layouts", HERE / "er9g_layouts.py")
ST = _load("er9g_stats", HERE / "er9g_stats.py")


def mods():
    """(er9_probe, er7_run, M4 runner, M5 runner); loaded on first use (heavy: MuJoCo trial code)."""
    P = LY.probe_module()
    return P, P.E7, P.M4, P.R


# ---- fixed settings ----------------------------------------------------------------------------------------------
GRADE = "N52"                                           # U3: N52 core magnets in both arms
RUN_ARMS = ("PG8", "PG20")                              # probe / full / smoke registry
U4_ARM = "PG20r"                                        # only with --u4-changed
REST40_ARMS = ("L0", "PG8", "PG20")
REST40_SEEDS = tuple(range(16700, 16740))
SEED_RANGE = (16000, 16999)                             # ER7's rehearsal range
FORBIDDEN_SEEDS = ((10000, 10999), (17000, 17999))      # E5's scored range; held-out block (never used)
PROBE_EXPS = ("E1-1", "E1-2", "E1-5", "E1-5s")
PROBE_COUNTS = {"E1-1": 20, "E1-2": 24, "E1-5": 42, "E1-5s": 20}
FULL_COUNTS = {"E1-1": 20, "E1-2": 24, "E1-3": 22, "E1-4": 40, "E1-5": 42, "E1-5s": 20, "E1-6a": 6, "E1-6b": 6,
               "E1-6c": 8, "E1-6t": 16}
OPERATIONAL = frozenset({"E1-1", "E1-2", "E1-3", "E1-4", "E1-5", "E1-5s", "E1-6a"})     # G.4 (= M4 RULE2)
ABUSE = frozenset({"E1-6b", "E1-6c", "E1-6t"})                                        # G.4 (= M4 RULE3)
GS_SUBS = ("E1-1", "E1-2", "E1-3", "E1-4", "E1-5", "E1-5s", "E1-6a", "E1-6b", "E1-6c", "E1-6t")
GS4_KEY = ("E1-2", "B_s16120")
# G.5: fields outside the comparison = the listed arm/table-naming fields + run metadata (as ER9 Parts B/E).
GS_LISTED = ("er7_arm", "mechanism", "magnet_table", "er9_arm", "er9", "wall_s", "er7_wall_s", "loadavg_start")
GS_RUN_METADATA = ("environment", "source_commit", "wall_time_s")
GS_SKIP = frozenset(GS_LISTED + GS_RUN_METADATA)
DEFAULT_JOBS, MAX_JOBS = 4, 6
LIMIT_PROBE_H, LIMIT_FULL_H, LIMIT_FREE_GB = 24.0, 35.0, 2.0          # G.7 cost stop rule
COST_CHECK_FRACTION = 0.25
CLIP_NM = 0.999                                         # "at the 1 N m clip", as ER9 Parts B-E count it
TIMESTEP_S = 0.0005
SMOKE_TURN_SEED, SMOKE_SNAP_SEED, SMOKE_SNAP_DELTA = 16100, 16568, 8.0
L0_SLIP_SEEDS = (16003, 16005)
D_VAL_MIN = 0.5
# rec["er9"] as written by run_one; apply_verdict adds "m4_legacy" and "verdict" (probe, rest40, full records).
ER9_KEYS = ("part", "mode", "arm", "grade", "n_magnets", "commit", "D_val_deg", "D_val_source", "table_files",
            "class_stats", "class_stats_window", "class_stats_legacy_consistent", "diagnostic", "out_of_regime",
            "legacy_proxy_flag_20deg", "peak_rss_kb", "run_wall_s")
ER9_VERDICT_KEYS = ("m4_legacy", "verdict")

_E9 = "experiments/ER9_anchored_core_layouts/"
PART_G_CODE = [_E9 + f for f in (
    "PROTOCOL.md", "er9g_layouts.py", "er9g_stats.py", "er9g_scan.py", "er9g_static.py", "er9g_v3turn.py",
    "er9g_selfcheck_static.py", "er9g_p3.py", "er9g_run.py", "er9g_replay.py", "tests/test_er9g_static.py",
    "tests/test_er9g_v3turn.py", "tests/test_er9g_run.py")]
_SHARED = ["src", "pyproject.toml", "uv.lock"]
_STATIC_CORE = _SHARED + [_E9 + "er9g_layouts.py", _E9 + "er9g_stats.py"]
_TABLES = [_E9 + "er9_probe.py", _E9 + "er9_layout.py", "experiments/E4_scored_m4/run.py",
           "experiments/E5_scored_m5/run.py", "experiments/ER7_core_magnet_rehearsal/er7_run.py",
           "experiments/M6_core_magnets/results/m6_checks.json", "experiments/D8_alignment/results/d8_1b_checks*.json",
           "experiments/D8_alignment/d8_1b_stage1.py", "experiments/D8_alignment/magnets.py"]
_SCREEN = [_E9 + "er9_screen.py", "experiments/ER3_layout_design", "experiments/ER6_real_placement_screen",
           "experiments/ER2_layout_probe", "experiments/ER1_rest_slip_review",
           "experiments/ER5_magnet_validation/er5_checks.py"]
REFERENCE_DATA = [                                   # what GS1/GS2, the replay self-check and the slip comparison read
    "experiments/ER7_core_magnet_rehearsal/results/L0", "experiments/ER7_core_magnet_rehearsal/results/C52",
    "experiments/ER7_core_magnet_rehearsal/posthoc/snap_L0_s16568_+8.json",
    "experiments/ER7_core_magnet_rehearsal/posthoc/snap_C52_s16568_+8.json",
    _E9 + "results/probe/diag/turn_L0_s16100.json", _E9 + "results/probe/diag/turn_C52_s16100.json"]
_DYNAMIC = PART_G_CODE + _SHARED + _TABLES + REFERENCE_DATA + [
    _E9 + "er9_full_analyze.py", "experiments/ER7_core_magnet_rehearsal/er7_analyze.py",
    "experiments/ER7_core_magnet_rehearsal/posthoc/snap_diag.py", "experiments/E1_scored/run.py",
    "experiments/D10_m5_rest_diagnostic/d10_rest.py", "experiments/D11_rest_slip_count/d11_analyze.py"]
# Paths each gate file depends on (its result is void if one changed between the gate's commit and HEAD).
GATE_DEPS = {
    "selfcheck": _DYNAMIC, "replay_selfcheck": _DYNAMIC,
    "selfcheck_static": _STATIC_CORE + _TABLES + _SCREEN + [_E9 + f for f in ("er9g_scan.py", "er9g_static.py",
                                                                            "er9g_selfcheck_static.py")],
    "P1": _STATIC_CORE + [_E9 + "er9g_scan.py", "experiments/ER6_real_placement_screen"],
    "P2": _STATIC_CORE + _TABLES + _SCREEN + [_E9 + "er9g_scan.py", _E9 + "er9g_static.py"],
    "P3": _STATIC_CORE + [_E9 + "er9g_p3.py", _E9 + "side_checks/realfit"],
    "P4": _SHARED + [_E9 + "er9g_v3turn.py", "experiments/ER5_magnet_validation/er5_checks.py",
                     "experiments/D8_alignment"],
}
FROZEN_PATHS = sorted(set(_DYNAMIC).union(*GATE_DEPS.values()))
# Commits whose change to a gate dependency is accepted without rerunning the gate (the coordinator's decision; one
# entry each, with the reason). 65866d6 changed only install_er7's cache key, which no static path calls.
ACCEPTED_CHANGES = {
    ("65866d695f98ec10b1e977dc0360d0907fd05e40", _E9 + "er9g_layouts.py"):
        "install_er7 cache key only (gap at index 1); static gates (GS3/GS5/GS6, P1-P3) do not call install_er7",
}


class Refused(ValueError):
    """An arm, seed, setting or state the protocol does not allow. Nothing is simulated."""


# ---- registry, seeds, workers --------------------------------------------------------------------------------------
def allowed_arms(mode: str, u4_changed: bool = False) -> tuple:
    if mode == "rest40":
        base = REST40_ARMS
    elif mode in ("probe", "full", "smoke"):
        base = RUN_ARMS
    else:
        raise Refused(f"no arm registry for mode {mode!r}")
    return base + ((U4_ARM,) if u4_changed else ())


def check_arm(arm: str, mode: str, u4_changed: bool = False) -> str:
    ok = allowed_arms(mode, u4_changed)
    if arm not in ok:
        extra = "" if u4_changed or arm != U4_ARM else " (PG20r needs --u4-changed: U4's default is no dynamics)"
        raise Refused(f"arm {arm!r} is not in the Part G registry for {mode}: {ok}{extra}")
    return arm


def check_seed(seed) -> int:
    s = int(seed)
    if s != seed:
        raise Refused(f"seed {seed!r} is not an integer")
    for lo, hi in FORBIDDEN_SEEDS:
        if lo <= s <= hi:
            raise Refused(f"seed {s} is in the forbidden block {lo}-{hi}")
    if not SEED_RANGE[0] <= s <= SEED_RANGE[1]:
        raise Refused(f"seed {s} is outside ER7's rehearsal range {SEED_RANGE[0]}-{SEED_RANGE[1]}")
    return s


def check_jobs_seeds(jobs: list[dict]) -> None:
    for j in jobs:
        check_seed(j["kw"]["seed"])


def check_workers(n: int) -> int:
    if not 1 <= int(n) <= MAX_JOBS:
        raise Refused(f"--jobs {n}: allowed 1-{MAX_JOBS} (G.11)")
    return int(n)


def er7_arm_for(arm: str) -> str:
    """ER7 arm a Part G arm runs as: "C52" only for the 40-only GS2 system; every arm with 4x2 magnets as "L0"."""
    return "C52" if arm == "C52" else "L0"


# ---- git provenance ------------------------------------------------------------------------------------------------
def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "core.filemode=false", "-c", "safe.directory=*", "-C", str(REPO), *args],
                          capture_output=True, text=True, check=check)


def code_problems() -> tuple[str | None, list[str]]:
    """(HEAD, problems): uncommitted changes in FROZEN_PATHS, or a Part G code file not tracked."""
    try:
        head = git("rev-parse", "HEAD").stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return None, [f"git failed: {exc!r}"]
    out = []
    dirty = git("status", "--porcelain", "--", *FROZEN_PATHS).stdout.strip()
    if dirty:
        out.append("uncommitted changes in Part G frozen paths:\n" + dirty)
    for f in PART_G_CODE:
        if not git("ls-files", "--", f).stdout.strip():
            out.append(f"not committed: {f}")
    return head, out


def require_clean() -> str:
    head, probs = code_problems()
    if probs:
        raise Refused("refusing: Part G code is not committed and clean (G.12: commit first)\n" + "\n".join(probs))
    return head


def frozen_changed(old: str, new: str) -> list[str]:
    d = git("diff", "--quiet", old, new, "--", *FROZEN_PATHS, check=False)
    if d.returncode == 0:
        return []
    if d.returncode == 1:
        return [git("diff", "--name-only", old, new, "--", *FROZEN_PATHS, check=False).stdout.strip()]
    return [f"git diff {old[:12]} {new[:12]} failed: {d.stderr.strip()}"]


# ---- gates (G.0, G.8: GS1-GS6, P1-P4, D_val) -----------------------------------------------------------------------
def _read(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def d_val_for(arm: str, root: Path = ROOT) -> float:
    """The D_val in force (U2 default: P4.d's result for the arm). L0 has no 4x3 magnet: no PC pair, D_val unused
    (inf, so its records carry the 'proxy' value that cannot split any pair)."""
    if arm == "L0":
        return ST.PROXY_D_VAL
    rec = _read(root / "static" / f"P4d_{arm}.json")
    if rec is None or "verdict" not in rec or rec["verdict"].get("D_val_deg") is None:
        raise Refused(f"no D_val recorded for {arm} (results/hybrid_g/static/P4d_{arm}.json)")
    return float(rec["verdict"]["D_val_deg"])


def gate_commit(d: dict) -> str | None:
    """The commit a gate file was produced at: "commit" (this runner, the replay self-check, P3), env.commit
    (selfcheck_static, P1, P2; D10.environment()), git.commit (P4.0, P4.d; er9g_v3turn.git_info())."""
    return d.get("commit") or (d.get("env") or {}).get("commit") or (d.get("git") or {}).get("commit")


def changes_since(old: str, deps: list[str]) -> list[tuple[str, str]] | str:
    """[(commit, path)] for every commit in old..HEAD touching deps; a string on a git error."""
    r = git("log", "--format=%H", f"{old}..HEAD", "--", *deps, check=False)
    if r.returncode != 0:
        return f"git log {old[:12]}..HEAD failed: {r.stderr.strip()}"
    out = []
    for c in r.stdout.split():
        files = git("show", "--name-only", "--format=", c, "--", *deps, check=False).stdout.split()
        out += [(c, f) for f in files]
    return out


def judge_changes(changes: list[tuple[str, str]], accepted: dict = ACCEPTED_CHANGES) -> tuple[list[str], list[str]]:
    """(unaccepted changes, notes on accepted ones)."""
    bad, notes = [], []
    for c, f in changes:
        why = accepted.get((c, f))
        if why is None:
            bad.append(f"{c[:12]} {f}")
        else:
            notes.append(f"accepted change {c[:12]} {f}: {why}")
    return bad, notes


def provenance(name: str, kind: str, d: dict) -> tuple[list[str], list[str]]:
    """A gate file counts only if its commit is recorded and no path it depends on changed since (except
    ACCEPTED_CHANGES)."""
    old = gate_commit(d)
    if not old:
        return [f"{name}: no commit recorded"], []
    ch = changes_since(old, GATE_DEPS[kind])
    if isinstance(ch, str):
        return [f"{name}: {ch}"], []
    bad, notes = judge_changes(ch)
    probs = [f"{name}: produced at {old[:12]}; its dependencies changed since: " + ", ".join(bad)] if bad else []
    return probs, [f"{name}: {n}" for n in notes]


def gs5_deviation1(gs5: dict) -> tuple[bool, str]:
    """GS5 read per Part G deviation 1: the 40-only half; the 48-only half on the ER3-order comparison and ER1's
    probe 5, with the layout()-order miss reported."""
    h48 = gs5.get("48_only", {})
    ok = bool(gs5.get("40_only", {}).get("pass") is True and h48.get("with_er3_magnet_order", {}).get("pass") is True
              and h48.get("probe5_pass") is True)
    note = (f"GS5 read per Part G deviation 1: 40_only.pass={gs5.get('40_only', {}).get('pass')}, "
            f"48_only.with_er3_magnet_order.pass={h48.get('with_er3_magnet_order', {}).get('pass')}, "
            f"48_only.probe5_pass={h48.get('probe5_pass')}; layout()-order er3_row_pass={h48.get('er3_row_pass')} "
            f"(reported, not required)")
    return ok, note


def selfcheck_report(root: Path = ROOT, check_commits: bool = True) -> tuple[list[str], list[str]]:
    out, notes = [], []
    sc = _read(root / "selfcheck.json")
    for k in ("GS1", "GS2", "GS4"):
        if not (sc and sc.get(k, {}).get("pass") is True):
            out.append(f"{k} has not passed (results/hybrid_g/selfcheck.json; run 'selfcheck')")
    ss = _read(root / "selfcheck_static.json")
    for k in ("GS3", "GS3b", "GS6"):
        if not (ss and ss.get(k, {}).get("pass") is True):
            out.append(f"{k} has not passed (results/hybrid_g/selfcheck_static.json)")
    ok5, note5 = gs5_deviation1((ss or {}).get("GS5", {}))
    notes.append(note5)
    if not ok5:
        out.append("GS5 has not passed under Part G deviation 1 (results/hybrid_g/selfcheck_static.json)")
    if check_commits:
        for name, kind, d in (("selfcheck.json", "selfcheck", sc), ("selfcheck_static.json", "selfcheck_static", ss)):
            if d is not None:
                p, n = provenance(name, kind, d)
                out += p; notes += n
    return out, notes


def static_report(arm: str, root: Path = ROOT, check_commits: bool = True) -> tuple[list[str], list[str]]:
    """The arm's P1, P2 (N52), P3, P4.0 (PG8 only) and P4.d files exist, are protocol runs and pass (G.6)."""
    st, out, notes = root / "static", [], []
    files = []
    p1 = _read(st / f"P1_{arm}.json")
    if p1 is None or p1.get("stopped") is not False:
        out.append(f"P1_{arm}.json missing or stopped")
    files.append((f"P1_{arm}.json", "P1", p1))
    p2 = _read(st / f"P2_{arm}_{GRADE}.json")
    if p2 is None or p2.get("stopped") is not False:
        out.append(f"P2_{arm}_{GRADE}.json missing or stopped")
    files.append((f"P2_{arm}_{GRADE}.json", "P2", p2))
    p3 = _read(st / f"P3_{arm}.json")
    if p3 is None or p3.get("arm") != arm or p3.get("hard_stop") is not False:
        out.append(f"P3_{arm}.json missing, for another arm, or hard_stop not false (G.6 P3 hard stop)")
    files.append((f"P3_{arm}.json", "P3", p3))
    if arm == "PG8":
        p40 = _read(st / "P4_0.json")
        if not (p40 and p40.get("label") == "PROTOCOL SETTINGS" and p40.get("verdict", {}).get("pass") is True):
            out.append("P4_0.json missing, not protocol settings, or not passed (stops PG8)")
        files.append(("P4_0.json", "P4", p40))
    p4d = _read(st / f"P4d_{arm}.json")
    v = (p4d or {}).get("verdict", {})
    if not (p4d and p4d.get("label") == "PROTOCOL SETTINGS" and v.get("stop_arm") is False
            and v.get("status") in ("complete", "halted", "budget") and v.get("D_val_deg") is not None
            and float(v["D_val_deg"]) >= D_VAL_MIN):
        out.append(f"P4d_{arm}.json missing, not protocol settings, incomplete, or D_val < {D_VAL_MIN} deg")
    files.append((f"P4d_{arm}.json", "P4", p4d))
    if check_commits:
        for name, kind, d in files:
            if d is not None:
                p, n = provenance(name, kind, d)
                out += p; notes += n
    return out, notes


def gate_report(arm: str, root: Path = ROOT, check_commits: bool = True) -> dict:
    out, notes = selfcheck_report(root, check_commits)
    if arm != "L0":
        p, n = static_report(arm, root, check_commits)
        out += p; notes += n
    return {"arm": arm, "problems": out, "notes": notes}


def gate_problems(arm: str, root: Path = ROOT, check_commits: bool = True) -> list[str]:
    return gate_report(arm, root, check_commits)["problems"]


# ---- per-trial rule (G.4) and the Part G verdict ------------------------------------------------------------------
def oor_reasons(s: dict, d_val: float) -> list[str]:
    """G.4's per-trial rule, condition by condition (the same conditions as er9g_stats.out_of_regime, which is
    called as a cross-check). Raises if the stats were split at another D_val."""
    lim = [("CE_max_near_tilt_deg", 5.0), ("PCon_max_near_tilt_deg", 20.0), ("PCoff_max_near_tilt_deg", 7.5),
           ("PP3_max_near_tilt_deg", 7.5)]
    zero = ["CE_clamped_z", "CE_near_perpendicular", "PCon_near_perpendicular", "PCoff_clamped_z",
            "PCoff_near_perpendicular", "PP3_clamped_z", "PP3_near_perpendicular", "cross_near"]
    out = [f"{k} {s[k]:.3f} > {v:g}" for k, v in lim if s[k] > v] + [f"{k} {s[k]} > 0" for k in zero if s[k] > 0]
    assert bool(out) == ST.out_of_regime(s, d_val), (out, s)
    return out


def legacy_proxy_flag(ms_stats: dict | None) -> bool | None:
    """ER7's C52 flag (20 deg aggregate tilt or any near perpendicular pair), for comparison with ER7 / Part E."""
    if not ms_stats:
        return None
    return bool(ms_stats.get("near_perpendicular", 0) > 0 or ms_stats.get("max_near_tilt_deg", 0.0) > 20.0)


def verdict(sub: str, legacy_reasons: list[str], class_stats: dict | None, d_val: float) -> dict:
    """Part G verdict of one trial: M4's criteria with ER7/M4's aggregate-tilt rule 2 replaced by G.4's per-class rule
    (operational trials fail when out of regime; abuse trials are labelled)."""
    reasons = [r for r in legacy_reasons if not r.startswith("rule 2:")]
    if class_stats is None:
        oor, why = None, ["per-class stats missing"]
    else:
        why = oor_reasons(class_stats, d_val)
        oor = bool(why)
    if sub in OPERATIONAL and (oor is None or oor):
        reasons.append("G.4 per-class rule: " + "; ".join(why))
    label = None
    if sub in ABUSE and oor:
        label = "magnet model outside validated range"
    return {"pass": not reasons, "fail_reasons": reasons, "out_of_regime": oor, "out_of_regime_reasons": why,
            "operational": sub in OPERATIONAL, "rule3_label": label}


def apply_verdict(rec: dict) -> dict:
    """Overwrites the verdict fields of a Part G record with the Part G verdict (legacy kept in er9.m4_legacy).
    er7_flag_outside_regime = an operational trial out of regime (G.9 signal 3, as er9_full_analyze.py reads it)."""
    e = rec["er9"]
    keys = ("pass", "fail_reasons", "ok_magnet_validity", "magnet_outside_validated_range", "rule3_label",
            "er7_flag_outside_regime", "validated_tilt_deg")
    e["m4_legacy"] = {k: copy.deepcopy(rec.get(k)) for k in keys}
    v = verdict(rec["sub_experiment"], rec.get("fail_reasons", []), e.get("class_stats"), e["D_val_deg"])
    e["verdict"] = v
    rec["pass"], rec["fail_reasons"] = v["pass"], v["fail_reasons"]
    rec["magnet_outside_validated_range"] = v["out_of_regime"]
    if v["operational"]:
        rec["ok_magnet_validity"] = v["out_of_regime"] is False
    else:
        rec["rule3_label"] = v["rule3_label"]
    rec["er7_flag_outside_regime"] = bool(v["operational"] and v["out_of_regime"] is not False)
    return rec


# ---- jobs ----------------------------------------------------------------------------------------------------------
def make_job(j: dict, arm: str, mode: str, env: dict, d_val: float, diag: bool = True) -> dict:
    return {**copy.deepcopy(j), "er7_arm": er7_arm_for(arm), "env": env, "commit": env.get("commit"),
            "scored": False, "reported_only": True, "er9g_arm": arm, "er9g_grade": GRADE, "er9g_d_val": d_val,
            "er9g_diag": bool(diag), "er9g_mode": mode}


def probe_base(base: list[dict]) -> list[dict]:
    out = [j for j in base if j["exp"] in PROBE_EXPS]
    got = {e: sum(j["exp"] == e for j in out) for e in PROBE_EXPS}
    assert got == PROBE_COUNTS, got
    return out


def rest40_base(base: list[dict]) -> list[dict]:
    """E1-1 configuration (ER7's first E1-1 job, D10's 60 s rest included) on seeds 16700-16739."""
    tmpl = next(j for j in base if j["sub"] == "E1-1")
    out = []
    for s in REST40_SEEDS:
        j = copy.deepcopy(tmpl)
        j["kw"]["seed"], j["tid"] = s, f"rest_s{s}"
        out.append(j)
    return out


def gs_firsts(base: list[dict]) -> list[dict]:
    seen, out = set(), []
    for j in base:
        if j["sub"] not in seen:
            seen.add(j["sub"]); out.append(j)
    assert tuple(sorted(seen)) == tuple(sorted(GS_SUBS)), seen
    return out


def record_path(root: Path, mode: str, arm: str, exp: str, tid: str) -> Path:
    return root / mode / arm / exp / f"{tid}.json.gz"


# ---- worker --------------------------------------------------------------------------------------------------------
def dump(rec: dict) -> bytes:
    """Identical to er7_run._dump."""
    return gzip.compress(json.dumps(rec, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x)).encode(),
                         9, mtime=0)


def run_one(job: dict) -> dict:
    """One trial in this fresh worker: install the arm, build the (cached) MagnetSystem, attach the per-class
    accumulator, run ER7's trial; stats are read with ms.stats at the end of the trial (same window: for E1-1, the
    60 s instrumented rest, because ER7 resets the system's stats before it)."""
    P, E7, M4, R = mods()
    from rubiknetic.cube_physics.m1_model import M1Params
    arm, grade, d_val, diag = job["er9g_arm"], job["er9g_grade"], job["er9g_d_val"], job["er9g_diag"]
    check_seed(job["kw"]["seed"])
    cls = ST.with_class_stats(M4.RecordingMagnetSystem) if diag else M4.RecordingMagnetSystem
    LY.install_er7(arm, grade, cls=cls)
    E7.setup_arm(job["er7_arm"])                     # the wrapper refuses an er7_arm that does not match the arm
    if job["er7_arm"] == "C52":
        E7._c52_tables()                             # ER7 writes its C52 table record from this cache (GS2 only)
    ov = dict(job["kw"].get("overrides", {}))
    ms = M4.use_magnets(R.magnet_params_for(dict(ov)), ov.get("gap", M1Params().gap))   # built once; run_trial reuses
    acc = ST.attach(ms, d_val) if diag else None
    t0 = time.perf_counter()
    rec = E7.run_one({k: v for k, v in job.items() if not k.startswith("er9g_")})
    assert M4._MS is ms, "the trial did not reuse the attached MagnetSystem"
    window = "rest60" if rec.get("rest60") else "trial"
    ms_stats = dict(ms.stats)
    cs = acc.as_dict(ms_stats) if diag else None
    ref = (rec.get("rest60") or {}).get("magnet_stats") if window == "rest60" else rec.get("magnet_stats")
    consistent = None if (cs is None or not ref) else all(cs["legacy"][k] == ref.get(k) for k in cs["legacy"])
    n_want = len(LY.arm_mags(arm, grade))
    assert ms.n == n_want, (ms.n, n_want)
    if "harness_exception" not in rec:        # E5's exception record has magnets = {params, layout_gap} only; such a
        assert rec.get("magnets") is None or rec["magnets"]["n_magnets"] == n_want, (rec["magnets"], n_want)
        # trial is recorded and fails (G.4: not excluded, not rerun)
    rec["er9_arm"], rec["mechanism"] = arm, "ER9G-" + arm
    rec["er9"] = {
        "part": "G", "mode": job["er9g_mode"], "arm": arm, "grade": grade, "n_magnets": ms.n,
        "commit": job["env"].get("commit"), "D_val_deg": d_val,
        "D_val_source": ("none: L0/C52 reference (no PC split applies or GS run)" if arm in ("L0", "C52")
                         or job["er9g_mode"] == "selfcheck" else f"results/hybrid_g/static/P4d_{arm}.json"),
        "table_files": LY.table_files(arm, grade), "class_stats": cs, "class_stats_window": window,
        "class_stats_legacy_consistent": consistent, "diagnostic": bool(diag),
        "out_of_regime": None if cs is None else ST.out_of_regime(cs, d_val),
        "legacy_proxy_flag_20deg": legacy_proxy_flag(ms_stats),
        "peak_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, "run_wall_s": time.perf_counter() - t0}
    assert set(rec["er9"]) == set(ER9_KEYS), sorted(set(rec["er9"]) ^ set(ER9_KEYS))
    return rec


# ---- records -------------------------------------------------------------------------------------------------------
def write_record(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "xb") as f:                    # exclusive create: an existing record is never overwritten
        f.write(dump(rec))


def read_record(path: Path) -> dict:
    return json.loads(gzip.decompress(path.read_bytes()))


def load_records(folder: Path) -> dict:
    out = {}
    for f in sorted(folder.glob("*/*.json.gz")):
        r = read_record(f)
        out[(r["experiment"], r["trial_id"])] = r
    return out


def manifest_problems(folder: Path, head: str, resume: bool) -> list[str]:
    """Records from another commit are refused unless resuming with FROZEN_PATHS unchanged since that commit."""
    m = _read(folder / "environment.json")
    has_records = any(folder.glob("*/*.json.gz")) if folder.exists() else False
    if m is None:
        return [f"{folder} has records but no environment.json"] if has_records else []
    old = m.get("commit")
    if old == head:
        return []
    if not resume:
        return [f"{folder} holds a run from commit {old}, HEAD is {head}: pass --resume to continue it"]
    ch = frozen_changed(old, head)
    return [f"--resume refused: frozen paths changed since {old}:\n" + "\n".join(ch)] if ch else []


def write_manifest(folder: Path, payload: dict) -> None:
    p = folder / "environment.json"
    if p.exists():
        return
    folder.mkdir(parents=True, exist_ok=True)
    with open(p, "x") as f:
        f.write(json.dumps(payload, indent=1, default=float))


# ---- cost (G.7, G.11) ----------------------------------------------------------------------------------------------
def l0_reference(folder: Path = ER7_RES / "L0") -> dict:
    """{(exp, tid): {"wall_s": er7_wall_s, "steps": simulated steps (trial + 60 s rest)}} from ER7's L0 records."""
    out = {}
    for (e, t), r in load_records(folder).items():
        sim = float(r.get("sim_time_s") or 0.0) + float((r.get("rest60") or {}).get("sim_time_s") or 0.0)
        out[(e, t)] = {"wall_s": float(r.get("er7_wall_s") or 0.0), "steps": sim / TIMESTEP_S}
    return out


def _mean(xs):
    xs = list(xs)
    return float(sum(xs) / len(xs)) if xs else 0.0


def project_from_speed(ref: dict, sps: dict, probe_arms, rest40_arms, full_arms, probe_keys, l0_sps: float) -> dict:
    """Summed per-trial wall time (h) projected from steps/s: per trial the larger of (ER7 L0 steps / arm steps/s)
    and (ER7 L0 wall x L0 steps/s / arm steps/s)."""
    rest = [v for (e, _), v in ref.items() if e == "E1-1"]

    def h(keys_vals, s):
        return sum(max(v["steps"] / s, v["wall_s"] * l0_sps / s) for v in keys_vals) / 3600

    pr = {a: h([ref[k] for k in probe_keys], sps[a]) for a in probe_arms}
    r40 = {a: len(REST40_SEEDS) * h(rest, sps[a]) / max(len(rest), 1) for a in rest40_arms}
    fu = {a: h(list(ref.values()), sps[a]) for a in full_arms}
    return {"probe_h": pr, "rest40_h": r40, "probe_total_h": sum(pr.values()) + sum(r40.values()), "full_h": fu}


def project_from_measured(ref: dict, measured: dict, probe_arms, rest40_arms, full_arms, probe_keys,
                          rest40_measured: dict | None = None, fallback: dict | None = None) -> dict:
    """measured: {arm: {(exp, tid): wall_s}} of finished probe trials; rest40_measured the same for rest40 records.
    Per arm, ratio = measured / ER7 L0 wall on the same trials (probe records first, else rest40 records against
    ER7 L0's mean E1-1 wall); remaining trials = ratio x ER7 L0 wall. An arm with no measured trial takes the smoke
    projection (`fallback`, the smoke.json projection) when given, else ratio 1. Source per arm is reported."""
    rest_mean = _mean(v["wall_s"] for (e, _), v in ref.items() if e == "E1-1")
    rest40_measured = rest40_measured or {}
    fb = fallback or {}
    ratio, source = {}, {}
    for a in set(probe_arms) | set(full_arms) | set(rest40_arms):
        m = measured.get(a, {})
        r4 = rest40_measured.get(a, {})
        den = sum(ref[k]["wall_s"] for k in m if k in ref)
        if den > 0:
            ratio[a], source[a] = sum(m[k] for k in m if k in ref) / den, "probe records"
        elif r4 and rest_mean > 0:
            ratio[a], source[a] = sum(r4.values()) / (len(r4) * rest_mean), "rest40 records"
        else:
            ratio[a], source[a] = None, "smoke projection" if fb else "ratio 1 (no measurement)"

    def pick(kind, a, value):
        if ratio[a] is None and a in fb.get(kind, {}):
            return fb[kind][a]
        return value

    pr = {}
    for a in probe_arms:
        m = measured.get(a, {})
        r = ratio[a] if ratio[a] is not None else 1.0
        pr[a] = pick("probe_h", a, (sum(m.values()) + sum(r * ref[k]["wall_s"] for k in probe_keys if k not in m))
                     / 3600)
    r40 = {}
    for a in rest40_arms:
        got = rest40_measured.get(a, {})
        r = ratio[a] if ratio[a] is not None else 1.0
        r40[a] = pick("rest40_h", a, (sum(got.values()) + (len(REST40_SEEDS) - len(got)) * r * rest_mean) / 3600)
    fu = {a: pick("full_h", a, (ratio[a] if ratio[a] is not None else 1.0) * sum(v["wall_s"] for v in ref.values())
                  / 3600) for a in full_arms}
    return {"ratio_to_er7_L0": ratio, "ratio_source": source, "probe_h": pr, "rest40_h": r40,
            "probe_total_h": sum(pr.values()) + sum(r40.values()), "full_h": fu}


def mem_available_kb() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1])
    except OSError:
        pass
    return None


def memory_check(peak_rss_kb: float | None, workers: int, avail_kb: float | None) -> dict:
    """G.7: stop if peak memory x workers would leave less than 2 GB free."""
    if peak_rss_kb is None or avail_kb is None:
        return {"known": False, "stop": False, "note": "peak RSS or MemAvailable unknown"}
    free = avail_kb - peak_rss_kb * workers
    lim = LIMIT_FREE_GB * 1024 * 1024
    return {"known": True, "peak_rss_kb": peak_rss_kb, "workers": workers, "mem_available_kb": avail_kb,
            "free_after_kb": free, "limit_kb": lim, "max_workers": int(max(0, (avail_kb - lim) // peak_rss_kb)),
            "stop": bool(free < lim)}


def cost_stop(proj: dict, mem: dict) -> list[str]:
    out = []
    if proj["probe_total_h"] > LIMIT_PROBE_H:
        out.append(f"projected probe {proj['probe_total_h']:.2f} h > {LIMIT_PROBE_H:g} h")
    for a, h in proj["full_h"].items():
        if h > LIMIT_FULL_H:
            out.append(f"projected full rehearsal of {a} {h:.2f} h > {LIMIT_FULL_H:g} h")
    if mem.get("stop"):
        out.append(f"peak memory x workers leaves {mem['free_after_kb'] / 2**20:.2f} GB free < {LIMIT_FREE_GB:g} GB")
    return out


# ---- statistics (G.8 reported items) -------------------------------------------------------------------------------
def sign_test(n_lower: int, n_higher: int) -> dict:
    """Exact sign test (ties dropped): one-sided p for 'arm lower' (P[X >= n_lower], X ~ Bin(n, 1/2)) and two-sided."""
    n = n_lower + n_higher

    def ge(k):
        return sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n

    if n == 0:
        return {"n": 0, "n_lower": 0, "p_one_sided_lower": 1.0, "p_two_sided": 1.0}
    return {"n": n, "n_lower": n_lower, "p_one_sided_lower": ge(n_lower),
            "p_two_sided": min(1.0, 2 * min(ge(n_lower), ge(n_higher)))}


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact two-sided (1 - alpha) interval (as D11's cp())."""
    from scipy.stats import beta
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def fisher_one_sided_less(a: int, n1: int, b: int, n2: int) -> float:
    """One-sided Fisher exact p for 'arm (a of n1) has a lower proportion than the reference (b of n2)':
    P[X <= a], X hypergeometric with a + b successes among n1 + n2 (scipy's alternative='less' on [[a, n1-a],
    [b, n2-b]])."""
    k, n = a + b, n1 + n2
    return sum(comb(n1, x) * comb(n2, k - x) for x in range(max(0, k - n2), a + 1)) / comb(n, k)


def slip_reading(a: int, n1: int, b: int, n2: int) -> dict:
    p = fisher_one_sided_less(a, n1, b, n2)
    return {"arm": [a, n1], "L0": [b, n2], "arm_ci95": clopper_pearson(a, n1), "L0_ci95": clopper_pearson(b, n2),
            "fisher_one_sided_p": p,
            "reading": "fewer slips than L0 in rehearsal" if (p <= 0.05 and a / n1 < b / n2) else "not distinguishable"}


def select_arm(rows: dict) -> str | None:
    """G.8 selection: among arms meeting all four signals, the lowest median E1-2 turner torque; ties to fewer
    magnets (then by name, for determinism). None if no arm meets all four."""
    ok = [(r["median_e12_turner_Nm"], r["n_magnets"], a) for a, r in rows.items() if r["all_met"]]
    return min(ok)[2] if ok else None


def probe_selection(complete_by_arm: dict, sel_rows: dict, stopped: dict) -> dict:
    """G.6/G.8: an arm stopped by a static or self-check gate is out (listed with its failing check); the probe is
    complete when every remaining arm has all 106 records; selection among the remaining arms only."""
    active = [a for a in complete_by_arm if a not in stopped]
    complete = bool(active) and all(complete_by_arm[a] for a in active)
    sel = select_arm({a: sel_rows[a] for a in active if a in sel_rows}) if complete else None
    if not active:
        note = "every arm stopped before dynamics: Part G ends with each arm's failing check (G.6)"
    elif not complete:
        note = "probe incomplete: " + ", ".join(a for a in active if not complete_by_arm[a])
    elif sel is None:
        note = "no arm meets all four signals: Part G ends with the probe report; the next step goes to the user"
    else:
        note = None
    return {"complete": complete, "arms_considered": active, "stopped_arms": stopped,
            "rows": {a: sel_rows[a] for a in active if a in sel_rows}, "selected": sel, "note": note}


def turner_stats(recs: list[dict]) -> dict | None:
    tq = [m["max_turner_torque_Nm"] for r in recs for m in r.get("per_move", [])
          if m.get("max_turner_torque_Nm") is not None]
    if not tq:
        return None
    a = np.array(tq)
    return {"n_moves": len(tq), "median": float(np.median(a)), "p99": float(np.percentile(a, 99)),
            "max": float(a.max()), "above_0.45": int(np.sum(a > 0.45)), "above_0.5": int(np.sum(a > 0.5)),
            "at_clip": int(np.sum(a >= CLIP_NM))}


def aggregate_class_stats(stats: list[dict]) -> dict:
    out = {}
    for s in stats:
        for k, v in s.items():
            if k in ("legacy", "D_val_deg") or v is None:
                continue
            if k.endswith("_mm"):
                out[k] = v if k not in out else min(out[k], v)
            elif k.endswith("_deg") or k.startswith("PC_max"):
                out[k] = max(out.get(k, 0.0), v)
            else:
                out[k] = out.get(k, 0) + v
    return out


def pass_g(rec: dict, d_val: float) -> bool:
    """The Part G pass flag recomputed with the D_val in force (from the M4 legacy reasons and the per-class stats)."""
    e = rec["er9"]
    return verdict(rec["sub_experiment"], e["m4_legacy"]["fail_reasons"] or [], e["class_stats"], d_val)["pass"]


def oor_g(rec: dict, d_val: float) -> bool | None:
    cs = rec["er9"]["class_stats"]
    return None if cs is None else ST.out_of_regime(cs, d_val)


def probe_signals(recs: dict, d_val: float, slip_fn) -> dict:
    """G.8 signals 1-4 for one arm's probe records {(exp, tid): rec}."""
    by = {}
    for r in recs.values():
        by.setdefault(r["sub_experiment"], []).append(r)
    complete = {e: len(by.get(e, [])) for e in PROBE_COUNTS} == PROBE_COUNTS
    rest = by.get("E1-1", [])
    slip_seeds = sorted(r["seed"] if "seed" in r else r["spec"]["seed"] for r in rest if slip_fn(r))
    snap_scored = [r for r in by.get("E1-5s", []) if r.get("snap_is_criterion")]
    oor = sorted(f"{e}/{t}" for (e, t), r in recs.items() if oor_g(r, d_val) is not False)
    s = {"complete": complete,
         "1_snap_scored_all_pass": complete and all(pass_g(r, d_val) for r in snap_scored),
         "2_rest_le_0.5_and_no_slips": complete and all(r.get("rest_rotation_deg", math.inf) <= 0.5 for r in rest)
         and not slip_seeds,
         "3_e12_e15_all_pass": complete and all(pass_g(r, d_val) for e in ("E1-2", "E1-5") for r in by.get(e, [])),
         "4_no_operational_trial_out_of_regime": complete and not oor}
    s["all_met"] = all(s.values())
    return {"signals": s, "slip_seeds_0_60s": slip_seeds, "out_of_regime_trials": oor,
            "failed": sorted(f"{e}/{t}" for (e, t), r in recs.items() if not pass_g(r, d_val))}


# ---- pool ----------------------------------------------------------------------------------------------------------
_STARTQ = None            # set by run_pool before the pool forks; each worker reports (job key, pid) when it starts


def job_key(j: dict) -> tuple:
    return (j["er9g_arm"], j["exp"], j["tid"])


def _task(job: dict) -> dict:
    if _STARTQ is not None:
        _STARTQ.put((job_key(job), os.getpid()))
    return run_one(job)


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        return Path(f"/proc/{pid}/stat").read_text().split(")")[-1].split()[0] != "Z"
    except OSError:
        return True


def find_lost(inflight: dict, now: float, alive, grace_s: float, start_timeout_s: float) -> list:
    """In-flight trials whose worker is gone for >= grace_s with no result (a killed worker never reports), or that
    never started within start_timeout_s. inflight: {key: {"pid", "submitted", "gone_since"}}; updates gone_since."""
    lost = []
    for k, v in inflight.items():
        if v["pid"] is None:
            if now - v["submitted"] >= start_timeout_s:
                lost.append(k)
            continue
        if v["gone_since"] is None and not alive(v["pid"]):
            v["gone_since"] = now
        if v["gone_since"] is not None and now - v["gone_since"] >= grace_s:
            lost.append(k)
    return lost


def run_pool(todo: list[dict], root: Path, mode: str, workers: int, after_each=None, poll_s: float = 20.0,
             grace_s: float = 60.0, start_timeout_s: float = 900.0) -> dict:
    """Runs jobs in fresh workers with at most `workers` in flight; writes each record (exclusive create).
    after_each() returning True pauses: no new trial starts, the trials in flight finish and are written.
    A worker killed mid-trial (e.g. out of memory) never returns: such a trial is detected by its worker's pid, listed
    as not run in <mode>/not_run.jsonl, no new trial starts, and the run stops with an error after the others in
    flight finish; a resume reruns exactly the trials without a record."""
    global _STARTQ
    ctx = mp_.get_context("fork")
    _STARTQ = ctx.Queue()
    q: queue.Queue = queue.Queue()
    it = iter(todo)
    inflight: dict = {}
    done, paused, err, lost_all = 0, False, None, []
    t0 = time.perf_counter()
    last_check = time.monotonic()
    pool = ctx.Pool(workers, maxtasksperchild=1)
    try:
        def submit():
            j = next(it, None)
            if j is None:
                return False
            k = job_key(j)
            inflight[k] = {"pid": None, "submitted": time.monotonic(), "gone_since": None}
            pool.apply_async(_task, (j,), callback=lambda r: q.put(("ok", r)),
                             error_callback=lambda e, k=k: q.put(("err", k, e)))
            return True

        for _ in range(workers):
            if not submit():
                break
        while inflight:
            while True:
                try:
                    k, pid = _STARTQ.get_nowait()
                except queue.Empty:
                    break
                if k in inflight:
                    inflight[k]["pid"] = pid
            try:
                item = q.get(timeout=poll_s)
            except queue.Empty:
                item = None
            now = time.monotonic()
            if item is None or now - last_check >= poll_s:
                last_check = now
                lost = find_lost(inflight, now, pid_alive, grace_s, start_timeout_s)
                for k in lost:
                    inflight.pop(k)
                    lost_all.append(k)
                    print(f"LOST: {k[0]} {k[1]}/{k[2]} - its worker died without a result; recorded as not run, "
                          f"no new trials start", flush=True)
                    (root / mode).mkdir(parents=True, exist_ok=True)
                    with open(root / mode / "not_run.jsonl", "a") as f:
                        f.write(json.dumps({"arm": k[0], "exp": k[1], "tid": k[2], "reason": "worker died",
                                            "utc_s": time.time()}) + "\n")
            if item is None:
                continue
            if item[0] == "err":
                inflight.pop(item[1], None)
                err = err or item[2]
                print(f"worker error in {item[1]}: {item[2]!r} (no new trials start)", flush=True)
            else:
                rec = item[1]
                inflight.pop((rec["er9_arm"], rec["experiment"], rec["trial_id"]), None)
                if mode in ("probe", "rest40", "full"):
                    apply_verdict(rec)
                p = record_path(root, mode, rec["er9_arm"], rec["experiment"], rec["trial_id"])
                write_record(p, rec)
                done += 1
                extra = (f" rest {rec['rest_rotation_deg']:.3f}" if rec.get("kind") == "rest" else
                         f" err {rec.get('U_err_after_1s_deg'):+.3f}" if rec.get("kind") == "snap" else "")
                print(f"[{done}/{len(todo)} {time.perf_counter() - t0:.0f} s] {rec['er9_arm']} "
                      f"{'PASS' if rec['pass'] else 'FAIL'} {rec['experiment']}/{rec['trial_id']}{extra}"
                      f"{' OOR' if rec['er9']['out_of_regime'] else ''} {'; '.join(rec['fail_reasons'])}", flush=True)
                if after_each is not None and not paused and after_each():
                    paused = True
                    print("PAUSED by the cost check (G.7): waiting for the trials in flight", flush=True)
            if not paused and err is None and not lost_all:
                submit()
        if lost_all:
            pool.terminate()
        else:
            pool.close()
        pool.join()
    finally:
        pool.terminate()
        _STARTQ = None
    if err is not None:
        raise err
    if lost_all:
        raise RuntimeError(f"{len(lost_all)} trial(s) lost to a dead worker and recorded as not run in "
                           f"{root / mode / 'not_run.jsonl'}: {lost_all}. Rerun the same command (with --resume if "
                           "HEAD changed) to run only the trials without a record.")
    return {"done": done, "paused": paused, "remaining": len(todo) - done}


# ---- selfcheck (GS1, GS2, GS4) and dev -----------------------------------------------------------------------------
def gs_diff(ref: dict, rec: dict) -> list[str]:
    _, E7, _, _ = mods()
    keep, E7.SKIP_KEYS = E7.SKIP_KEYS, set(GS_SKIP)
    try:
        return E7.diff(ref, json.loads(gzip.decompress(dump(rec))))
    finally:
        E7.SKIP_KEYS = keep


def gs_jobs(env: dict) -> list[dict]:
    _, E7, _, _ = mods()
    base = E7.er7_jobs()
    firsts = gs_firsts(base)
    js = [make_job(j, "L0", "selfcheck", env, ST.PROXY_D_VAL) | {"er9g_gs": "GS1"} for j in firsts]
    js += [make_job(j, "C52", "selfcheck", env, ST.PROXY_D_VAL) | {"er9g_gs": "GS2"} for j in firsts]
    g4 = next(j for j in base if (j["exp"], j["tid"]) == GS4_KEY)
    js += [make_job(g4, "PG20", "selfcheck", env, ST.PROXY_D_VAL, diag=d) | {"er9g_gs": "GS4", "er9g_gs4_diag": d}
           for d in (True, False)]
    check_jobs_seeds(js)
    return js


def _pool_map(jobs: list[dict], workers: int) -> list[dict]:
    with mp_.get_context("fork").Pool(workers, maxtasksperchild=1) as pool:
        return pool.map(_run_stripped, jobs, chunksize=1)


def _run_stripped(job: dict) -> dict:
    return run_one({k: v for k, v in job.items() if k not in ("er9g_gs", "er9g_gs4_diag")})


def selfcheck(workers: int, out: Path) -> dict:
    head = require_clean()
    if out.exists():
        raise Refused(f"refusing to overwrite {out} (a failed self-check is explained and recorded as a deviation)")
    _, E7, _, _ = mods()
    env = E7.D10.environment()
    js = gs_jobs(env)
    recs = _pool_map(js, workers)
    res = {"commit": head, "env": env, "skip_fields": sorted(GS_SKIP), "GS1": {"trials": []}, "GS2": {"trials": []}}
    g4 = {}
    for j, r in zip(js, recs):
        if j["er9g_gs"] == "GS4":
            g4[j["er9g_gs4_diag"]] = r
            continue
        ref = read_record(ER7_RES / j["er9g_arm"] / j["exp"] / f"{j['tid']}.json.gz")
        d = gs_diff(ref, r)
        res[j["er9g_gs"]]["trials"].append({"sub": j["sub"], "exp": j["exp"], "tid": j["tid"], "n_diffs": len(d),
                                            "diffs": d[:20], "class_stats": r["er9"]["class_stats"]})
    for k in ("GS1", "GS2"):
        t = res[k]["trials"]
        res[k]["pass"] = bool(len(t) == len(GS_SUBS) and all(x["n_diffs"] == 0 for x in t))
    d = gs_diff(json.loads(gzip.decompress(dump(g4[False]))), g4[True])
    res["GS4"] = {"trial": "/".join(GS4_KEY), "arm": "PG20", "n_diffs": len(d), "diffs": d[:20],
                  "with_diag_class_stats": g4[True]["er9"]["class_stats"],
                  "pass": bool(len(d) == 0 and g4[True]["er9"]["class_stats"] is not None)}
    res["pass"] = bool(res["GS1"]["pass"] and res["GS2"]["pass"] and res["GS4"]["pass"])
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "x") as f:
        f.write(json.dumps(res, indent=1, default=float))
    return res


def outside_repo(p: Path) -> Path:
    p = p.resolve()
    if p == REPO or REPO in p.parents:
        raise Refused(f"dev output must be outside the repository: {p}")
    return p


def dev(root: Path, arm: str, exp: str, tid: str, workers: int) -> dict:
    """Debugging: one reference (L0 or C52) trial through run_one, compared with ER7's record (GS-style diff)."""
    if arm not in ("L0", "C52"):
        raise Refused("dev mode runs the reference arms L0 / C52 only")
    root = outside_repo(root)
    _, E7, _, _ = mods()
    env = E7.D10.environment()
    j = next(j for j in E7.er7_jobs() if (j["exp"], j["tid"]) == (exp, tid))
    job = make_job(j, arm, "dev", env, ST.PROXY_D_VAL)
    check_jobs_seeds([job])
    rec = _pool_map([job], 1)[0]
    d = gs_diff(read_record(ER7_RES / arm / exp / f"{tid}.json.gz"), rec)
    write_record(root / "dev" / arm / exp / f"{tid}.json.gz", rec)
    res = {"arm": arm, "trial": f"{exp}/{tid}", "n_diffs": len(d), "diffs": d[:20],
           "class_stats": rec["er9"]["class_stats"], "legacy_consistent": rec["er9"]["class_stats_legacy_consistent"],
           "wall_s": rec.get("er7_wall_s"), "label": "DEV (not a protocol run)"}
    with open(root / "dev" / f"diff_{arm}_{tid}.json", "x") as f:
        f.write(json.dumps(res, indent=1, default=float))
    return res


# ---- smoke (G.7) ---------------------------------------------------------------------------------------------------
def _replay(args: list[str], out: Path) -> dict:
    cmd = [sys.executable, str(HERE / "er9g_replay.py"), *args, "--out", str(out)]
    tv = Path("/usr/bin/time")
    if tv.exists():
        cmd = [str(tv), "-v", *cmd]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    if p.returncode != 0:
        raise RuntimeError(f"replay failed: {' '.join(args)}\n{p.stdout[-2000:]}\n{p.stderr[-4000:]}")
    rss = None
    for line in p.stderr.splitlines():
        if "Maximum resident set size" in line:
            rss = int(line.split(":")[-1])
    res = json.loads(out.read_text())
    res["time_v_max_rss_kb"] = rss
    res["process_wall_s"] = time.perf_counter() - t0
    return res


def smoke(arms: list[str], workers: int) -> dict:
    head = require_clean()
    sm = ROOT / "smoke"
    if (sm / "smoke.json").exists():
        raise Refused(f"refusing to overwrite {sm / 'smoke.json'}")
    probs = replay_selfcheck_problems()
    if probs:
        raise Refused("; ".join(probs))
    for a in arms:
        probs = gate_problems(a)
        if probs:
            raise Refused(f"{a}: " + "; ".join(probs))
    sm.mkdir(parents=True, exist_ok=True)
    rows = {}
    for a in ["L0", *arms]:
        tr = _replay(["turn", a, str(SMOKE_TURN_SEED)], sm / f"turn_{a}_s{SMOKE_TURN_SEED}.json")
        sn = _replay(["snap", a, str(SMOKE_SNAP_SEED), f"{SMOKE_SNAP_DELTA:+g}"],
                     sm / f"snap_{a}_s{SMOKE_SNAP_SEED}_{SMOKE_SNAP_DELTA:+g}.json")
        a1 = next(s for s in sn["states"] if s["tag"] == "after_1s")
        rows[a] = {
            "role": "speed reference" if a == "L0" else "arm",
            "turn": {"peak_torque_Nm": tr["peak_torque_Nm"], "fraction_of_steps_at_clip": tr["fraction_of_steps_at_clip"],
                     "final_layer_err_deg": tr["final_layer_err_deg"], "class_stats": tr["class_stats"],
                     "out_of_regime": tr["out_of_regime"], "steps_per_s": tr["steps_per_s"]},
            "snap": {"U_err_after_1s_deg": a1["U_err_deg"],
                     "leftover_spin_about_own_axis_deg": {k: v["spin_about_own_axis_deg"] for k, v in a1["pieces"].items()},
                     "largest_tangential_leftover_deg": max(v["tangential_deg"] for v in a1["pieces"].values()),
                     "class_stats": sn["class_stats"], "out_of_regime": sn["out_of_regime"],
                     "steps_per_s": sn["steps_per_s"]},
            "largest_d_deg": max(tr["class_stats"]["PC_max_path_dev_deg"], sn["class_stats"]["PC_max_path_dev_deg"]),
            "steps_per_s": (tr["steps"] + sn["steps"]) / (tr["step_wall_s"] + sn["step_wall_s"]),
            "peak_rss_kb": max(x for x in (tr["time_v_max_rss_kb"], sn["time_v_max_rss_kb"], tr["ru_maxrss_kb"],
                                           sn["ru_maxrss_kb"]) if x is not None)}
    ref = l0_reference()
    _, E7, _, _ = mods()
    probe_keys = [(j["exp"], j["tid"]) for j in probe_base(E7.er7_jobs())]
    proj = project_from_speed(ref, {a: r["steps_per_s"] for a, r in rows.items()}, arms, ["L0", *arms], arms,
                              probe_keys, rows["L0"]["steps_per_s"])
    mem = memory_check(max(r["peak_rss_kb"] for r in rows.values()), workers, mem_available_kb())
    stop = cost_stop(proj, mem)
    c52 = _read(ER9_RES / "probe" / "diag" / "turn_C52_s16100.json") or {}
    res = {"commit": head, "rows": rows, "projection": proj, "memory": mem, "cost_stop": bool(stop),
           "cost_stop_reasons": stop,
           "limits": {"probe_h": LIMIT_PROBE_H, "full_h": LIMIT_FULL_H, "free_gb": LIMIT_FREE_GB},
           "references": {"L0": {"peak_torque_Nm": 0.461, "at_clip_fraction": 0.0},
                          "C52": {"peak_torque_Nm": c52.get("peak_torque_Nm"),
                                  "at_clip_fraction": c52.get("fraction_of_steps_at_clip"),
                                  "source": "results/probe/diag/turn_C52_s16100.json"},
                          "W3": {"peak_torque_Nm": 1.000, "at_clip_fraction": 0.043},
                          "C52_leftover_spin_deg": "1.40-1.74 (FACT, G.7)"}}
    with open(sm / "smoke.json", "x") as f:
        f.write(json.dumps(res, indent=1, default=float))
    return res


def replay_selfcheck_problems(root: Path = ROOT, check_commits: bool = True) -> list[str]:
    sc = _read(root / "replay_selfcheck.json")
    if not (sc and sc.get("pass") is True and not sc.get("code_problems")):
        return ["the replay tool's self-check has not passed from committed, clean code (er9g_replay.py selfcheck)"]
    return provenance("replay_selfcheck.json", "replay_selfcheck", sc)[0] if check_commits else []


def smoke_ok(accept: bool) -> None:
    s = _read(ROOT / "smoke" / "smoke.json")
    if s is None:
        raise Refused("smoke replays and the cost check (G.7) have not run (mode 'smoke')")
    if s["cost_stop"] and not accept:
        raise Refused("the cost stop rule (G.7) triggered in smoke: " + "; ".join(s["cost_stop_reasons"])
                      + " - the user decides (--accept-cost-overrun records that decision)")


# ---- probe / rest40 / full -----------------------------------------------------------------------------------------
def _prepare(mode: str, arms: list[str], u4: bool, workers: int, resume: bool, accept: bool) -> tuple:
    for a in arms:
        check_arm(a, mode, u4)
    check_workers(workers)
    head = require_clean()
    for a in arms:
        probs = gate_problems(a)
        if probs:
            raise Refused(f"{mode} {a}: " + "; ".join(probs))
    smoke_ok(accept)
    stopped = cost_checks_stopped()
    if stopped and not accept:
        raise Refused("a 25 % cost check stopped the probe (G.7): " + "; ".join(stopped)
                      + " - the user decides (--accept-cost-overrun records that decision)")
    for a in arms:
        probs = manifest_problems(ROOT / mode / a, head, resume)
        if probs:
            raise Refused("; ".join(probs))
    s = _read(ROOT / "smoke" / "smoke.json") or {}
    m = memory_check(s.get("memory", {}).get("peak_rss_kb"), workers, mem_available_kb())
    if m["known"] and m["stop"]:
        new = max(1, min(workers, m["max_workers"]))
        print(f"memory (G.11): {workers} workers would leave < {LIMIT_FREE_GB:g} GB free; using {new}", flush=True)
        workers = new
    _, E7, _, _ = mods()
    env = E7.D10.environment()
    return head, env, workers, E7.er7_jobs()


def _start(mode: str, arm: str, env: dict, head: str, d_val: float, jobs: list[dict], accept: bool) -> None:
    write_manifest(ROOT / mode / arm, {**env, "commit": head, "mode": mode, "arm": arm, "grade": GRADE,
                                       "D_val_deg": d_val, "table_files": LY.table_files(arm, GRADE),
                                       "n_trials": len(jobs), "accept_cost_overrun": accept,
                                       "gates": gate_report(arm)})


def cost_check_files(root: Path = ROOT) -> list[Path]:
    return sorted(list((root / "probe").glob("cost_check_25_*.json")) + list((root / "rest40").glob("cost_check_25_*.json")))


def cost_checks_stopped(root: Path = ROOT) -> list[str]:
    out = []
    for f in cost_check_files(root):
        d = _read(f) or {}
        if d.get("stop"):
            out.append(f"{f.name}: " + "; ".join(d.get("reasons", [])))
    return out


def measured_walls(root: Path = ROOT) -> tuple[dict, dict]:
    """({arm: {(exp, tid): er7_wall_s}} of probe records, the same for rest40 records)."""
    pr = {a: {k: float(r.get("er7_wall_s") or 0.0) for k, r in load_records(root / "probe" / a).items()}
          for a in RUN_ARMS + (U4_ARM,)}
    r4 = {a: {k: float(r.get("er7_wall_s") or 0.0) for k, r in load_records(root / "rest40" / a).items()}
          for a in REST40_ARMS + (U4_ARM,)}
    return pr, r4


def write_cost_check(path: Path, n_done: int, n_total: int, workers: int, accept: bool, ref: dict,
                     probe_keys: list, root: Path = ROOT) -> bool:
    """G.7 during the probe: re-project the probe (with U5's extension) and each full rehearsal from measured wall_s
    (smoke projection for arms not yet measured); memory from the trials' peak RSS. Writes `path` (exclusive);
    returns True if the run must pause."""
    sm = _read(root / "smoke" / "smoke.json") or {}
    fb = sm.get("projection") or {}
    probe_arms = list(fb.get("probe_h") or RUN_ARMS)
    meas, r40 = measured_walls(root)
    proj = project_from_measured(ref, meas, probe_arms, list(REST40_ARMS), probe_arms, probe_keys, r40, fb)
    peaks = [r["er9"].get("peak_rss_kb") or 0 for mode in ("probe", "rest40") for a in REST40_ARMS + RUN_ARMS
             for r in load_records(root / mode / a).values()]
    peak = max(peaks + [resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss])
    mem = memory_check(peak, workers, mem_available_kb())
    why = cost_stop(proj, mem)
    with open(path, "x") as f:
        f.write(json.dumps({"n_done": n_done, "n_total": n_total, "projection": proj, "memory": mem,
                            "stop": bool(why), "reasons": why, "accepted_by_user_flag": accept}, indent=1,
                           default=float))
    print(f"cost check {path.name} at {n_done}/{n_total}: probe {proj['probe_total_h']:.2f} h, full "
          f"{proj['full_h']}; {'STOP: ' + '; '.join(why) if why else 'within limits'}", flush=True)
    return bool(why) and not accept


def _n_records(folder: Path) -> int:
    return len(list(folder.glob("*/*.json.gz"))) if folder.exists() else 0


def run_probe(arms: list[str], u4: bool, workers: int, resume: bool, accept: bool) -> dict:
    head, env, workers, base = _prepare("probe", arms, u4, workers, resume, accept)
    pb = probe_base(base)
    todo, total = [], 0
    for a in arms:
        dv = d_val_for(a)
        js = [make_job(j, a, "probe", env, dv) for j in pb]
        check_jobs_seeds(js)
        _start("probe", a, env, head, dv, js, accept)
        total += len(js)
        todo += [j for j in js if not record_path(ROOT, "probe", a, j["exp"], j["tid"]).exists()]
    todo.sort(key=lambda j: (j["exp"] != "E1-5s", j["exp"] != "E1-1", j["exp"], j["kw"]["seed"], j["er9g_arm"]))
    print(f"{len(todo)} probe trials to run ({total} in total), {workers} workers", flush=True)
    ref = l0_reference()
    probe_keys = [(j["exp"], j["tid"]) for j in pb]
    per_arm = len(pb)

    def after_each() -> bool:                        # one check per arm, when that arm has 25 % of its trials
        stop = False
        for a in arms:
            chk = ROOT / "probe" / f"cost_check_25_{a}.json"
            n = _n_records(ROOT / "probe" / a)
            if not chk.exists() and n >= math.ceil(COST_CHECK_FRACTION * per_arm):
                stop |= write_cost_check(chk, n, per_arm, workers, accept, ref, probe_keys)
        return stop

    return run_pool(todo, ROOT, "probe", workers, after_each)


def run_rest40(arms: list[str], u4: bool, workers: int, resume: bool, accept: bool) -> dict:
    head, env, workers, base = _prepare("rest40", arms, u4, workers, resume, accept)
    rb = rest40_base(base)
    todo = []
    for a in arms:
        dv = d_val_for(a)
        js = [make_job(j, a, "rest40", env, dv) for j in rb]
        check_jobs_seeds(js)
        _start("rest40", a, env, head, dv, js, accept)
        todo += [j for j in js if not record_path(ROOT, "rest40", a, j["exp"], j["tid"]).exists()]
    todo.sort(key=lambda j: (j["kw"]["seed"], j["er9g_arm"]))
    print(f"{len(todo)} rest40 trials to run, {workers} workers", flush=True)
    ref = l0_reference()
    probe_keys = [(j["exp"], j["tid"]) for j in probe_base(base)]
    total = len(rb) * len(arms)
    chk = ROOT / "rest40" / "cost_check_25_rest40.json"

    def after_each() -> bool:
        n = sum(_n_records(ROOT / "rest40" / a) for a in arms)
        if chk.exists() or n < math.ceil(COST_CHECK_FRACTION * total):
            return False
        return write_cost_check(chk, n, total, workers, accept, ref, probe_keys)

    return run_pool(todo, ROOT, "rest40", workers, after_each)


def run_full(arm: str, u4: bool, workers: int, resume: bool, accept: bool) -> dict:
    check_arm(arm, "full", u4)
    rep = _read(ROOT / "probe" / "report.json")
    if not rep or rep.get("selection", {}).get("selected") != arm:
        raise Refused(f"full: {arm} is not the probe's selected arm (G.9; run 'report' after a complete probe)")
    head, env, workers, base = _prepare("full", [arm], u4, workers, resume, accept)
    fh = rep.get("cost", {}).get("full_h", {}).get(arm)
    if fh is not None and fh > LIMIT_FULL_H and not accept:
        raise Refused(f"projected full rehearsal {fh:.2f} h > {LIMIT_FULL_H:g} h (G.7): the user decides")
    dv = d_val_for(arm)
    js = [make_job(j, arm, "full", env, dv) for j in base]
    assert len(js) == 204
    check_jobs_seeds(js)
    _start("full", arm, env, head, dv, js, accept)
    todo = [j for j in js if not record_path(ROOT, "full", arm, j["exp"], j["tid"]).exists()]
    todo.sort(key=lambda j: -len(j["kw"].get("moves", "").split()))        # longest sequences first
    print(f"{len(todo)} full-rehearsal trials to run (204 in total), arm {arm}, {workers} workers", flush=True)
    return run_pool(todo, ROOT, "full", workers)


# ---- report --------------------------------------------------------------------------------------------------------
def _a7():
    return _load("er7_analyze", REPO / "experiments/ER7_core_magnet_rehearsal/er7_analyze.py")


def report(u4: bool = False) -> dict:
    A7 = _a7()
    slip = lambda r: bool(A7.slips(r))  # noqa: E731
    l0 = load_records(ER7_RES / "L0")
    c52 = load_records(ER7_RES / "C52")
    arms = list(allowed_arms("probe", u4))
    res = {"arms": {}, "D_val": {}}
    sel_rows = {}
    l0_rest = {r["spec"]["seed"]: r for (e, _), r in l0.items() if e == "E1-1"}
    l0_r40 = {r["spec"]["seed"]: r for r in load_records(ROOT / "rest40" / "L0").values()}
    l0_slips60 = sum(slip(r) for r in l0_rest.values()) + sum(slip(r) for r in l0_r40.values())
    n_l0_60 = len(l0_rest) + len(l0_r40)
    for a in arms:
        recs = load_records(ROOT / "probe" / a)
        if not recs:
            continue
        dv = d_val_for(a)
        res["D_val"][a] = dv
        sig = probe_signals(recs, dv, slip)
        by = {}
        for r in recs.values():
            by.setdefault(r["sub_experiment"], []).append(r)
        e12 = turner_stats(by.get("E1-2", []))
        rest = {r["spec"]["seed"]: r for r in by.get("E1-1", [])}
        common = sorted(set(rest) & set(l0_rest))
        lower = sum(rest[s]["rest_rotation_deg"] < l0_rest[s]["rest_rotation_deg"] for s in common)
        higher = sum(rest[s]["rest_rotation_deg"] > l0_rest[s]["rest_rotation_deg"] for s in common)
        r40 = {r["spec"]["seed"]: r for r in load_records(ROOT / "rest40" / a).values()}
        a_slips60 = sum(slip(r) for r in rest.values()) + sum(slip(r) for r in r40.values())
        n_a_60 = len(rest) + len(r40)
        cs = [r["er9"]["class_stats"] for r in recs.values() if r["er9"]["class_stats"]]
        legacy = sorted(f"{e}/{t}" for (e, t), r in recs.items() if r["er9"].get("legacy_proxy_flag_20deg"))
        sps = [(float(r.get("sim_time_s") or 0) + float((r.get("rest60") or {}).get("sim_time_s") or 0))
               / TIMESTEP_S / r["er7_wall_s"] for r in recs.values() if r.get("er7_wall_s")]
        n_mag = next(iter(recs.values()))["er9"]["n_magnets"]
        res["arms"][a] = {
            "n": len(recs), **sig, "n_magnets": n_mag,
            "turner_E1-2_Nm": e12,
            "paired_rest_vs_L0": {**sign_test(lower, higher), "n_seeds": len(common), "n_ties": len(common) - lower - higher},
            "slip_seeds_60": (slip_reading(a_slips60, n_a_60, l0_slips60, n_l0_60) if n_a_60 and n_l0_60 else None),
            "slip_seeds_60_complete": n_a_60 == 60 and n_l0_60 == 60,
            "rest_on_L0_slip_seeds": {s: {"rest_rotation_deg": rest[s]["rest_rotation_deg"],
                                          "rest60_rotation_deg": (rest[s].get("rest60") or {}).get("rest_rotation_deg"),
                                          "slip_events_60s": len(A7.slips(rest[s]))} for s in L0_SLIP_SEEDS if s in rest},
            "snap_back": sorted([[r["trial_id"], r["delta_deg"], r["U_err_after_1s_deg"], pass_g(r, dv)]
                                 for r in by.get("E1-5s", [])]),
            "class_stats_max": aggregate_class_stats(cs), "largest_d_deg": max((c["PC_max_path_dev_deg"] for c in cs),
                                                                               default=None),
            "legacy_proxy_flag_20deg_trials": legacy, "steps_per_s_median": float(np.median(sps)) if sps else None,
            "wall_h": sum(float(r.get("er7_wall_s") or 0) for r in recs.values()) / 3600}
        if e12:
            sel_rows[a] = {"all_met": sig["signals"]["all_met"], "median_e12_turner_Nm": e12["median"],
                           "n_magnets": n_mag}
    # references beside the arms (same E1-2 seeds; L0 and C52 also full run)
    refs = {"L0": l0, "C52": c52, "W3": load_records(ER9_RES / "probe" / "W3")}
    for h in ("HB1", "HB2", "HB3"):
        refs[h] = load_records(ER9_RES / "hybrid" / "probe" / h)
    res["turner_references_E1-2"] = {k: turner_stats([r for (e, _), r in v.items() if e == "E1-2"])
                                     for k, v in refs.items() if v}
    res["turner_references_full_run"] = {k: turner_stats([r for (e, _), r in v.items() if e in ("E1-2", "E1-3", "E1-4")])
                                         for k, v in (("L0", l0), ("C52", c52))}
    sm = _read(ROOT / "smoke" / "smoke.json")
    res["gravity_sag_from_smoke"] = ({a: r["snap"]["largest_tangential_leftover_deg"] for a, r in sm["rows"].items()}
                                     if sm else None)
    stopped = {}
    for a in arms:
        g = gate_report(a)
        if g["problems"]:
            stopped[a] = g["problems"]
        res.setdefault("gates", {})[a] = g
    done = {a: bool(res["arms"].get(a, {}).get("signals", {}).get("complete")) for a in arms}
    res["selection"] = probe_selection(done, sel_rows, stopped)
    complete = res["selection"]["complete"]
    if complete:
        ref = l0_reference()
        meas = {a: {k: float(r.get("er7_wall_s") or 0.0) for k, r in load_records(ROOT / "probe" / a).items()}
                for a in res["arms"]}
        r40 = {a: {k: float(r.get("er7_wall_s") or 0.0) for k, r in load_records(ROOT / "rest40" / a).items()}
               for a in REST40_ARMS}
        pk = [k for k in ref if k[0] in PROBE_EXPS]
        res["cost"] = project_from_measured(ref, meas, list(res["arms"]), list(REST40_ARMS), list(res["arms"]), pk, r40)
    (ROOT / "probe").mkdir(parents=True, exist_ok=True)
    (ROOT / "probe" / "report.json").write_text(json.dumps(res, indent=1, default=float))
    for a in arms:
        if any((ROOT / "full" / a).glob("*/*.json.gz")):
            res.setdefault("full", {})[a] = full_report(a, A7)
    return res


def full_report(arm: str, A7=None) -> dict:
    """G.9 signals for a full rehearsal (Option A with E1-6m <P> on the Part G pass flags; slips; G.4 rule)."""
    A7 = A7 or _a7()
    dv = d_val_for(arm)
    recs = load_records(ROOT / "full" / arm)
    for r in recs.values():
        assert r["pass"] == pass_g(r, dv), (r["experiment"], r["trial_id"], "stored pass differs from G.4 at D_val")
    oa = A7.option_a(recs)
    rest = [r for r in recs.values() if r["sub_experiment"] == "E1-1"]
    slips = sorted(r["spec"]["seed"] for r in rest if A7.slips(r))
    oor_op = sorted(f"{e}/{t}" for (e, t), r in recs.items()
                    if r["sub_experiment"] in OPERATIONAL and oor_g(r, dv) is not False)
    oor_abuse = sorted(f"{e}/{t}" for (e, t), r in recs.items() if r["sub_experiment"] in ABUSE and oor_g(r, dv))
    probe = load_records(ROOT / "probe" / arm)
    same = [k for k in probe if k in recs]
    out = {"n": len(recs), "D_val_deg": dv, "option_a": oa["option_a"], "complete": oa["complete"],
           "rows": oa["rows"], "e16m": oa["e16m"], "slip_seeds_0_60s": slips,
           "rest_max_deg": max((r["rest_rotation_deg"] for r in rest), default=None),
           "operational_out_of_regime": oor_op, "abuse_labelled": oor_abuse,
           "out_of_regime_by_class": {f"{r['experiment']}/{r['trial_id']}": r["er9"]["verdict"]["out_of_regime_reasons"]
                                      for r in recs.values() if r["er9"]["verdict"]["out_of_regime"]},
           "turner_Nm": turner_stats([r for r in recs.values() if r["sub_experiment"] in ("E1-2", "E1-3", "E1-4")]),
           "probe_reproduced": {"n_common": len(same),
                                "pass_flags_equal": all(probe[k]["pass"] == recs[k]["pass"] for k in same),
                                "values_equal": all(probe[k].get(f) == recs[k].get(f) for k in same
                                                    for f in ("rest_rotation_deg", "U_err_after_1s_deg"))}}
    out["signals"] = {"1_no_slips_and_rest_le_0.5": bool(len(rest) == 20 and not slips and out["rest_max_deg"] is not None
                                                         and out["rest_max_deg"] <= 0.5),
                      "2_option_a_rule": bool(oa["option_a"]), "3_no_operational_trial_out_of_regime": not oor_op}
    out["signals"]["all_met"] = all(out["signals"].values())
    clip = (out["turner_Nm"] or {}).get("at_clip", 0)
    out["reading"] = ("meets the rehearsal signals (not a candidate)" if out["signals"]["all_met"] and clip == 0 else
                      "meets the rehearsal signals with moves at the clip: reported beside W3, the user decides"
                      if out["signals"]["all_met"] else "signal(s) missed: negative result kept and reported")
    (ROOT / "full" / arm / "report.json").write_text(json.dumps(out, indent=1, default=float))
    return out


# ---- CLI -----------------------------------------------------------------------------------------------------------
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=("selfcheck", "smoke", "probe", "rest40", "report", "full", "dev"))
    ap.add_argument("--jobs", type=int, default=DEFAULT_JOBS)
    ap.add_argument("--arms", nargs="*")
    ap.add_argument("--arm")
    ap.add_argument("--u4-changed", action="store_true", help="the user changed U4: PG20r may run")
    ap.add_argument("--resume", action="store_true", help="continue records from an earlier commit")
    ap.add_argument("--accept-cost-overrun", action="store_true", help="the user's decision after a G.7 cost stop")
    ap.add_argument("--root", help="dev mode only: output directory outside the repository")
    ap.add_argument("--trial", default="E1-2/B_s16120", help="dev mode only: EXP/TID")
    a = ap.parse_args(argv)
    try:
        jobs = check_workers(a.jobs)
        if a.mode == "selfcheck":
            r = selfcheck(jobs, ROOT / "selfcheck.json")
            print(json.dumps({k: r[k]["pass"] for k in ("GS1", "GS2", "GS4")} | {"pass": r["pass"]}, indent=1))
        elif a.mode == "dev":
            if not a.root:
                raise Refused("dev needs --root DIR (outside the repository)")
            exp, tid = a.trial.split("/")
            print(json.dumps(dev(Path(a.root), a.arm or "L0", exp, tid, jobs), indent=1, default=float))
        elif a.mode == "smoke":
            arms = a.arms or list(RUN_ARMS)
            for x in arms:
                check_arm(x, "smoke", a.u4_changed)
            r = smoke(arms, jobs)
            print(json.dumps({k: r[k] for k in ("projection", "memory", "cost_stop", "cost_stop_reasons")}, indent=1,
                             default=float))
        elif a.mode == "probe":
            print(run_probe(a.arms or list(RUN_ARMS), a.u4_changed, jobs, a.resume, a.accept_cost_overrun))
        elif a.mode == "rest40":
            print(run_rest40(a.arms or list(REST40_ARMS), a.u4_changed, jobs, a.resume, a.accept_cost_overrun))
        elif a.mode == "full":
            if not a.arm:
                raise Refused("full: name the arm with --arm")
            print(run_full(a.arm, a.u4_changed, jobs, a.resume, a.accept_cost_overrun))
        else:
            r = report(a.u4_changed)
            print(json.dumps({"selection": r["selection"],
                              "signals": {k: v["signals"] for k, v in r["arms"].items()},
                              "full": {k: v["signals"] for k, v in r.get("full", {}).items()}}, indent=1,
                             default=float))
    except Refused as e:
        raise SystemExit(f"REFUSED: {e}") from None


if __name__ == "__main__":
    main()
