"""Scored G1 runner for M6 (experiments/PHASE_1_M6_PREREGISTRATION.md, section 6.1 item 1).

M6 = M5 with the 48 corner-edge magnets replaced by the core layout (20 piece magnets + 20 core magnets, 4x3 mm N52,
clearance 0.2 mm). The trial logic and the whole run procedure are M5's runner (experiments/E5_scored_m5/run.py),
loaded unchanged as a module, which loads M4's runner. This file changes only module globals of those two, in fresh
module instances of its own (so M5's tests and ER7 never see M6's patches):
  * seeds = M5 scored seed + 7000 (SEED_SHIFT 16000, SNAP_SEED_BASE 17550, E16T_SEED_BASE 17640), range 17000-17999;
    smoke seeds 18000-18099;
  * magnets: use_magnets installs core_layout(mp, 0.2 mm) for the trial's MagnetParams; default 4x3 mm N52;
  * tables: N52 = M6's table, N35 = ER5's table (both with recorded SHA-256); the other E1-7 strengths are that N52
    table times an exact factor, written by `run.py tables` and checked against it at every start;
  * validated regime: tilt 20 deg (P-60) and no near pair perpendicular; M4's rules 2 and 3 use both;
  * V3 rule: only 4x3 mm magnets (ER5's real-placement V3-turn record) with M6's S1 linearity record;
  * E1-7 magnet factors: none / 4x3 N35 / N42 / N52 and strength scale 0.67 / 1; no face-gap factor;
  * mechanism "M6", folders under experiments/E6_scored_m6/, the start-up check on the nominal core system, and
    the frozen paths.
Nothing else is redefined: jobs, records, manifest, start log, ledger, resume, exceptions and the location check are
M5's code.

Usage (WSL, from repo root):
    ~/.venvs/rubiknetic/bin/python experiments/E6_scored_m6/run.py tables            # derived tables (unscored prep)
    ~/.venvs/rubiknetic/bin/python experiments/E6_scored_m6/run.py all [--jobs N] [--dry-run]
    ~/.venvs/rubiknetic/bin/python experiments/E6_scored_m6/run.py smoke --smoke-dir DIR [--jobs N]
        [--stop-after N --stop-point {after_tmp,after_link,after_ledger}]       # UNSCORED; seeds 18000-18099
Exit codes: 0 complete, 2 refused, 3 interrupted (resume with the same command).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_M4_NAME_M5 = "e4_scored_m4_run_for_m5"      # the name M5's runner looks its M4 module up under
_M4_NAME = "e4_scored_m4_run_for_m6"
_R_NAME = "e5_scored_m5_run_for_m6"


def _exec(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod                  # picklable exceptions and worker functions
    spec.loader.exec_module(mod)
    return mod


def _load_isolated():
    """Fresh instances of M4's and M5's runner modules for M6. M5's runner takes its M4 module from
    sys.modules[_M4_NAME_M5] if present, so M6's instance is placed there while M5's runner loads, then the previous
    entry is restored."""
    if _R_NAME in sys.modules:
        return sys.modules[_R_NAME]
    m4 = _exec(_M4_NAME, REPO / "experiments" / "E4_scored_m4" / "run.py")
    missing = object()
    prev = sys.modules.get(_M4_NAME_M5, missing)
    sys.modules[_M4_NAME_M5] = m4
    try:
        r = _exec(_R_NAME, REPO / "experiments" / "E5_scored_m5" / "run.py")
    finally:
        if prev is missing:
            del sys.modules[_M4_NAME_M5]
        else:
            sys.modules[_M4_NAME_M5] = prev
    assert r.M4 is m4
    return r


R = _load_isolated()
M4 = R.M4

from rubiknetic.cube_physics import scored  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml  # noqa: E402
from rubiknetic.cube_physics.magnets import (GRADES_BR, MagnetParams, MagnetSystem, core_layout,  # noqa: E402
                                             near_field_tables)

# ---- M6 constants (pre-registration sections 1-4) ------------------------------------------------------------------
MECHANISM = "M6"
SEED_PLUS = 7000                             # M6 seed = M5 scored seed + 7000
CLEARANCE = 2e-4                             # core clearance c = 0.2 mm
VALIDATED_TILT_DEG = 20.0                    # P-60: ER5's real-placement V3-turn trajectories
MAGNET_SIZES = {"4x3_N35": (0.004, 0.003, "N35"), "4x3_N42": (0.004, 0.003, "N42"),
                "4x3_N52": (0.004, 0.003, "N52")}
NOMINAL_MAGNET = "4x3_N52"
E17_MAGNETS = ["none", "4x3_N35", "4x3_N42", "4x3_N52"]
E17_SCALES = [0.67, 1.0]
OUT = HERE / "results"
OUT_NOMAG = HERE / "results_nomag"
TABLES = HERE / "tables"                     # derived tables (git-ignored; SHA-256 in the manifest)
ER5_JSON = REPO / "experiments/ER5_magnet_validation/results/er5_4x3_N35.json"
ER5_TABLES = REPO / "experiments/ER5_magnet_validation/tables"
M6_JSON = REPO / "experiments/M6_core_magnets/results/m6_checks.json"
M6_TABLES = REPO / "experiments/M6_core_magnets/tables"
TABLE_KEYS = ("C0", "Cp", "Cm", "Ct")
M6_FROZEN_PATHS = R.M5_FROZEN_PATHS + [
    "experiments/ER5_magnet_validation/results/er5_4x3_N35.json",
    "experiments/M6_core_magnets/results/m6_checks.json",
    "experiments/PHASE_1_M6_PREREGISTRATION.md",
    "experiments/E6_scored_m6/run.py",
    "experiments/E6_scored_m6/analyze.py",
]
_M5 = {"SEED_SHIFT": M4.SEED_SHIFT, "SCORED_SEED_RANGE": M4.SCORED_SEED_RANGE, "SNAP_SEED_BASE": M4.SNAP_SEED_BASE,
       "E16T_SEED_BASE": M4.E16T_SEED_BASE}          # M5's values, kept for the seed test

# ---- seeds, folders, labels ----------------------------------------------------------------------------------------
M4.SEED_SHIFT = _M5["SEED_SHIFT"] + SEED_PLUS
M4.SCORED_SEED_RANGE = (17000, 17999)
M4.SNAP_SEED_BASE = _M5["SNAP_SEED_BASE"] + SEED_PLUS
M4.E16T_SEED_BASE = _M5["E16T_SEED_BASE"] + SEED_PLUS
R.SMOKE_SEED_BASE = 18000
R.HERE, R.OUT, R.OUT_NOMAG = HERE, OUT, OUT_NOMAG
M4.OUT, M4.OUT_NOMAG = OUT, OUT_NOMAG
R.M5_FROZEN_PATHS = M6_FROZEN_PATHS

_m5_metadata, _m5_manifest_body = R._metadata, R.manifest_body


def _metadata(job: dict) -> dict:
    return {**_m5_metadata(job), "mechanism": MECHANISM}


def manifest_body(jobs_run, not_run, commit, env) -> dict:
    return {**_m5_manifest_body(jobs_run, not_run, commit, env), "mechanism": MECHANISM}


R._metadata, R.manifest_body = _metadata, manifest_body


# ---- magnets -------------------------------------------------------------------------------------------------------
def magnet_params_for(ov: dict) -> MagnetParams | None:
    """The trial's magnets from its overrides (which it consumes, as M4's and M5's do). Default 4x3 mm N52."""
    name = ov.pop("magnet", NOMINAL_MAGNET)
    scale = ov.pop("magnet_scale", 1.0)
    if "face_gap_mm" in ov:
        raise ValueError("M6 has no face-gap factor (the core layout is set by its clearance)")
    if name == "none":
        return None
    dia, length, grade = MAGNET_SIZES[name]
    return MagnetParams(diameter=dia, length=length, grade=grade, scale=scale)


NOMINAL_MP = magnet_params_for({})


def _table_name(mp: MagnetParams) -> str:
    """The file name near_field_tables() looks for (magnets.py)."""
    return (f"tilt_{mp.diameter*1e3:g}x{mp.length*1e3:g}_{mp.br:g}T_s{mp.scale:g}_r{mp.r2*1e3:g}"
            f"_h1.5_q16x48.npz")


def _recorded_tables() -> dict:
    """{magnet params: (path, recorded SHA-256, record)} for the two tables built and recorded earlier."""
    m6 = json.loads(M6_JSON.read_text())["S1"]
    er5 = json.loads(ER5_JSON.read_text())["tables_sha256"]
    n35 = MagnetParams(diameter=0.004, length=0.003, grade="N35")
    return {NOMINAL_MP: (M6_TABLES / m6["n52_file"], m6["n52_sha256"], M4._rel(M6_JSON)),
            n35: (ER5_TABLES / _table_name(n35), er5[_table_name(n35)], M4._rel(ER5_JSON))}


def table_path(mp: MagnetParams) -> Path:
    rec = _recorded_tables()
    return rec[mp][0] if mp in rec else TABLES / _table_name(mp)


def strength_factor(mp: MagnetParams) -> float:
    """Pair-energy ratio of mp to the nominal 4x3 mm N52 magnet (same size: Br^2 times the strength scale)."""
    return (GRADES_BR[mp.grade] / GRADES_BR[NOMINAL_MP.grade]) ** 2 * mp.scale


def _load_npz(path: Path) -> dict:
    with np.load(path) as f:
        return {k: f[k] for k in f.files}


def derived_rel_diff(mp: MagnetParams) -> float:
    """Largest relative difference between mp's derived table and the N52 table times strength_factor(mp); the grid
    and the other arrays must be identical."""
    src, got, fac = _load_npz(table_path(NOMINAL_MP)), _load_npz(table_path(mp)), strength_factor(mp)
    if set(src) != set(got):
        return float("inf")
    rel = 0.0
    for k, v in src.items():
        if k in TABLE_KEYS:
            rel = max(rel, float(np.max(np.abs(got[k] - v * fac)) / np.max(np.abs(v * fac))))
        elif not np.array_equal(got[k], v):
            return float("inf")
    return rel


def v3_basis() -> list[str]:
    """Problems with the validation records the core layout rests on (empty = usable). Committed files only."""
    probs = []
    er5 = json.loads(ER5_JSON.read_text())
    if er5.get("size") != "4x3_N35":
        probs.append("ER5 record is not for 4x3 mm N35")
    for k in ("V1", "V4"):
        if not er5.get(k, {}).get("pass"):
            probs.append(f"ER5 {k} did not pass")
    for k in ("V3a_pass", "V3b_pass"):
        if not er5.get(k):
            probs.append(f"ER5 {k} is not true")
    real = [e for e in er5.get("V3_turn", []) if e.get("placement") == "real"]
    if sorted(e.get("kind") for e in real) != ["corner", "edge"] or not all(e.get("pass") for e in real):
        probs.append("ER5 V3-turn in the real placement did not pass for edge and corner")
    m6 = json.loads(M6_JSON.read_text())
    if not m6.get("S1", {}).get("pass"):
        probs.append("M6 S1 (table linearity in strength) did not pass")
    for k in ("S2", "V4", "V6", "V5_rk4"):
        if not m6.get(k, {}).get("pass"):
            probs.append(f"M6 {k} did not pass")
    return probs


def v3_rule(job: dict) -> tuple[str, str | None]:
    """('run', None) | ('refused', message). Section 4: a magnet arm runs only with 4x3 mm magnets, on ER5's
    real-placement V3-turn record and M6's linearity record. M6 registers no "not run" arm."""
    if not job["magnets"]:
        return "run", None
    mp = magnet_params_for(dict(job["kw"].get("overrides", {})))
    if mp is None:
        return "run", None
    if (mp.diameter, mp.length) != (0.004, 0.003):
        return "refused", f"no V3 record for {mp.diameter*1e3:g}x{mp.length*1e3:g} mm in the core layout (ER5: 4x3 mm)"
    probs = v3_basis()
    if probs:
        return "refused", "; ".join(probs)
    return "run", None


def magnet_availability(mp: MagnetParams) -> dict:
    """Raises Refused unless mp's table exists on the default grid with its recorded hash (N52, N35) or equals the
    N52 table times the exact strength factor (derived tables). Never builds a table."""
    path, rec = table_path(mp), _recorded_tables()
    if not path.exists():
        raise M4.Refused(f"near-field table {M4._rel(path)} does not exist (run 'run.py tables' for derived tables)")
    with np.load(path) as f:
        grid_ok = (np.array_equal(f["rho"], np.linspace(0.0, mp.r2 + 0.001, 37))
                   and np.array_equal(f["z"], np.linspace(mp.length + 0.0001, mp.r2 + 0.001, 31)))
    if not grid_ok:
        raise M4.Refused(f"table {path.name} is not on the default grid (near_field_tables would rebuild it)")
    sha = M4._sha256(path)
    info = {"table_file": M4._rel(path), "table_sha256": sha, "validated_tilt_deg": VALIDATED_TILT_DEG,
            "v3_source": M4._rel(ER5_JSON), "v3_source_sha256": M4._sha256(ER5_JSON),
            "linearity_source": M4._rel(M6_JSON), "linearity_source_sha256": M4._sha256(M6_JSON),
            "strength_factor_vs_N52": strength_factor(mp)}
    if mp in rec:
        if sha != rec[mp][1]:
            raise M4.Refused(f"table {path.name} has SHA-256 {sha}, not the recorded {rec[mp][1]} ({rec[mp][2]})")
        info["table_origin"] = f"built; hash recorded in {rec[mp][2]}"
    else:
        magnet_availability(NOMINAL_MP)                       # the source table has its recorded hash
        rel = derived_rel_diff(mp)
        if not rel <= 1e-12:
            raise M4.Refused(f"derived table {path.name} differs from the N52 table x {strength_factor(mp):.6g} "
                             f"by {rel:.3g} (limit 1e-12)")
        info["table_origin"] = f"N52 table x {strength_factor(mp):.12g}"
        info["derived_max_rel_diff"] = rel
    return info


def _tables_for(mp: MagnetParams):
    if M4.TABLES_PROVIDER is not None:                        # tests only (coarse tables), as in M4
        return M4.TABLES_PROVIDER(mp)
    magnet_availability(mp)                                   # refuses before near_field_tables could start a build
    path = table_path(mp)
    assert path.name == _table_name(mp)
    return near_field_tables(mp, path.parent)


def use_magnets(mp: MagnetParams | None, gap: float):
    """M4's use_magnets (run.py:334-354) with the core layout: the same process cache, key and installation."""
    M4.configure_process()
    key = (mp, gap)
    if key == M4._MS_KEY and (M4._MS is not None or mp is None):
        if M4._MS is not None:
            M4._MS.install()
        return M4._MS
    MagnetSystem.uninstall()
    M4._MS, M4._MS_KEY = None, None
    if mp is None:
        M4._MS_KEY = key
        return None
    p = M1Params(**{**M4.BASE_OVERRIDES, "gap": gap})
    m = M4._compile_paused(build_m1_xml(p))
    ms = M4.RecordingMagnetSystem(m, p.pitch, p.gap, mp, tables=_tables_for(mp), mags=core_layout(mp, CLEARANCE))
    M4._MS, M4._MS_KEY = ms, key
    ms.install()
    return ms


_m4_apply = M4.apply_m4_criteria


def apply_m6_criteria(rec: dict, sub: str, validated_tilt: float | None, magnets_on: bool) -> dict:
    """M4's criteria, then the second half of M6's validated regime (section 1): a near pair that is perpendicular is
    outside it. Rule 2 then fails an operational trial and rule 3 labels an abuse trial, exactly as for the tilt."""
    rec = _m4_apply(rec, sub, validated_tilt, magnets_on)
    if magnets_on:
        n_perp = int(rec["magnet_stats"].get("near_perpendicular", 0))
        rec["near_perpendicular_pairs"] = n_perp
        if n_perp > 0:
            rec["magnet_outside_validated_range"] = True
            if sub in M4.RULE2:
                rec["ok_magnet_validity"] = False
                rec["fail_reasons"].append(f"rule 2: {n_perp} near-pair evaluations perpendicular (outside the "
                                           "validated regime)")
                rec["pass"] = False
            elif sub in M4.RULE3:
                rec["rule3_label"] = "magnet model outside validated range"
    return rec


def startup_check() -> dict:
    """M4 rule 1 on the nominal core system at the 0.05 mm gap, with the gap and the magnet count recorded."""
    res = M4.startup_checks(NOMINAL_MP, gap=R.GAP)
    res["gap"] = R.GAP
    res["n_magnets"] = int(M4._MS.n) if M4._MS is not None else None
    res["pass"] = bool(res["pass"] and res["n_magnets"] == 40)
    return res


M4.MAGNET_SIZES = MAGNET_SIZES
M4.E17_FACTORS = ([(n, v) for n, v in M4.E17_FACTORS if n not in M4._MAGNET_KEYS]
                  + [("magnet", E17_MAGNETS), ("magnet_scale", E17_SCALES)])
M4.NOMINAL = ({x for x in M4.NOMINAL if x[0] not in M4._MAGNET_KEYS}
              | {("magnet", NOMINAL_MAGNET), ("magnet_scale", 1.0)})
M4.magnet_params_for = R.magnet_params_for = magnet_params_for
M4.table_path = table_path
M4.magnet_availability = magnet_availability
M4._tables_for = _tables_for
M4.use_magnets = use_magnets
M4.apply_m4_criteria = apply_m6_criteria
M4.nominal_validated_tilt = lambda: VALIDATED_TILT_DEG
M4.TABLES_PROVIDER = None
R.v3_rule = v3_rule
R.startup_check = startup_check


# ---- job list and derived tables -----------------------------------------------------------------------------------
def build_m6_jobs(commit: str, env: dict) -> list[dict]:
    """The full scored M6 list: M5's builder on the patched globals."""
    return R.build_m5_jobs(commit, env, VALIDATED_TILT_DEG)


def derived_magnets() -> list[MagnetParams]:
    """Every magnet configuration of the full list that has no recorded table of its own."""
    rec, out = _recorded_tables(), []
    for j in build_m6_jobs("tables", {}):
        mp = magnet_params_for(dict(j["kw"].get("overrides", {}))) if j["magnets"] else None
        if mp is not None and mp not in rec and mp not in out:
            out.append(mp)
    return out


def make_tables(log=print) -> None:
    """Writes each missing derived table (the N52 table times the exact strength factor) and checks all of them."""
    magnet_availability(NOMINAL_MP)
    src = _load_npz(table_path(NOMINAL_MP))
    for mp in derived_magnets():
        path = table_path(mp)
        if not path.exists():
            TABLES.mkdir(parents=True, exist_ok=True)
            np.savez(path, **{k: (v * strength_factor(mp) if k in TABLE_KEYS else v) for k, v in src.items()})
        info = magnet_availability(mp)
        log(f"{info['table_file']}  sha256 {info['table_sha256']}  {info['table_origin']}  "
            f"max rel diff {info['derived_max_rel_diff']:.3g}")


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["tables"]:
        make_tables()
        return
    R.main(argv)


if __name__ == "__main__":
    main()
