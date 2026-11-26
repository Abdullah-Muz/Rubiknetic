"""Scored G1 runner for M7 (experiments/PHASE_1_M7_PREREGISTRATION.md, section 6.1).

M7 = M5 (L0: M5's 48 x 4x2 mm N35 magnets, B1, 0.05 mm piece gap) with rounded piece edges (R 2.5 mm) and NoSlip 10.
The trial logic and the whole run procedure are M5's runner (experiments/E5_scored_m5/run.py), loaded unchanged in
fresh module instances of its own, as E6 did, so M5's tests and ER7 never see these patches. Changes:
  * seeds = M5 scored seed + 7000 (17000-17999); smoke seeds 18000-18099; REST-X 17700-17739;
  * every trial: rounded edges and NoSlip are installed exactly as the D15 rehearsals did (a scored.Trial subclass that
    sets edge_profile / edge_radius; scored.build_m1_xml wrapped with D13's with_noslip), through a wrapper around
    M4.run_trial, which M5's run_job calls. E1-7's `edge_radius` and `noslip` overrides are consumed there;
  * kind "rest60": E1-1 as the D14 Stage 1 / D15 R2-R4 instrumented 60 s rest (10 s warm-up E1-1 with the edge and no
    NoSlip, magnet-system reset, D13's d13_rest with variant V2's NoSlip). Its pass flag is D14's e11_pass and 0 D11
    slip events over 60 s (P-86 Q4), computed in the worker; M4's criteria then add rule 2 as for every trial;
  * E1-7: M5's factors with the chamfer factor replaced by edge radius 1.8 / 2.5 / 3.6 mm and a NoSlip factor
    0 / 5 / 10 / 20 (0 is the reference arm), plus R3's 15 one-seed 60 s rests (P-86 Q6);
  * REST-X: 40 extra 60 s rests (P-86 Q7), reported only;
  * mechanism "M7", folders under experiments/E7_scored_m7/, the frozen paths;
  * "selfcheck": the first trial of every Option A sub-experiment and four E1-7 trials on the rehearsal mapping (+6000),
    compared with the committed D15 rehearsal records (section 6.2; unscored, results_selfcheck/).
Nothing else is redefined: jobs, records, manifest, start log, ledger, resume, exceptions and the location check are
M5's code.

Usage (WSL, from repo root):
    ~/.venvs/rubiknetic/bin/python experiments/E7_scored_m7/run.py all [--jobs N] [--dry-run]
    ~/.venvs/rubiknetic/bin/python experiments/E7_scored_m7/run.py smoke --smoke-dir DIR [--jobs N]
        [--stop-after N --stop-point {after_tmp,after_link,after_ledger}]       # UNSCORED; seeds 18000-18099
    ~/.venvs/rubiknetic/bin/python experiments/E7_scored_m7/run.py selfcheck [--jobs N]   # UNSCORED; rehearsal seeds
Exit codes: 0 complete, 2 refused, 3 interrupted (resume with the same command).
"""
from __future__ import annotations

import copy
import dataclasses
import importlib.util
import json
import multiprocessing
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_M4_NAME_M5 = "e4_scored_m4_run_for_m5"      # the name M5's runner looks its M4 module up under
_M4_NAME = "e4_scored_m4_run_for_m7"
_R_NAME = "e5_scored_m5_run_for_m7"


def _exec(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod                  # picklable exceptions and worker functions
    spec.loader.exec_module(mod)
    return mod


def _load_isolated():
    """Fresh instances of M4's and M5's runner modules for M7 (as E6's run.py)."""
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

D10 = _exec("d10_rest", REPO / "experiments/D10_m5_rest_diagnostic/d10_rest.py")          # D13 reads sys.modules
D13 = _exec("d13_run", REPO / "experiments/D13_rest_slip_mechanism/d13_run.py")
D13A = _exec("d13_analyze", REPO / "experiments/D13_rest_slip_mechanism/d13_analyze.py")  # D11's slip-event detector

# ---- M7 constants (pre-registration sections 1-4) ------------------------------------------------------------------
MECHANISM = "M7"
SEED_PLUS = 7000                             # M7 seed = M5 scored seed + 7000
REHEARSAL_PLUS = 6000                        # ER7 / D15 rehearsal mapping (self-check only)
EDGE_R = 0.0025                              # rounded edges, R 2.5 mm (P-80)
NOSLIP = 10                                  # noslip_iterations (P-73)
REST_S = 60.0                                # E1-1 instrumented rest (section 4.2)
E11_THRESH = {"rest_rotation_deg": 0.5, "penetration_mm": 0.5, "radial_offset_mm": 0.5}   # D14 d14s3_analyze.THRESH
E17_EDGE = [0.0018, 0.0025, 0.0036]          # P-84 D1
E17_NOSLIP = [0, 5, 10, 20]                  # P-84 D2 (0 = reference arm, outside the band)
REST_X_SEEDS = tuple(range(17700, 17740))    # P-86 Q7
OUT = HERE / "results"
OUT_NOMAG = HERE / "results_nomag"
SELFCHECK_OUT = HERE / "results_selfcheck"
D15 = REPO / "experiments/D15_rounded_edges/results"
M7_FROZEN_PATHS = R.M5_FROZEN_PATHS + [
    "src/rubiknetic/cube_physics/m1_model.py",
    "experiments/D10_m5_rest_diagnostic/d10_rest.py",
    "experiments/D13_rest_slip_mechanism/d13_run.py",
    "experiments/D13_rest_slip_mechanism/d13_analyze.py",
    "experiments/D11_rest_slip_count/d11_analyze.py",
    "experiments/PHASE_1_M7_PREREGISTRATION.md",
    "experiments/E7_scored_m7/run.py",
    "experiments/E7_scored_m7/analyze.py",
]
_M5 = {"SEED_SHIFT": M4.SEED_SHIFT, "SCORED_SEED_RANGE": M4.SCORED_SEED_RANGE, "SNAP_SEED_BASE": M4.SNAP_SEED_BASE,
       "E16T_SEED_BASE": M4.E16T_SEED_BASE}          # M5's values, kept for the seed test


def set_seed_map(plus: int, rng: tuple[int, int]) -> None:
    M4.SEED_SHIFT = _M5["SEED_SHIFT"] + plus
    M4.SCORED_SEED_RANGE = rng
    M4.SNAP_SEED_BASE = _M5["SNAP_SEED_BASE"] + plus
    M4.E16T_SEED_BASE = _M5["E16T_SEED_BASE"] + plus


# ---- seeds, folders, labels ----------------------------------------------------------------------------------------
set_seed_map(SEED_PLUS, (17000, 17999))
R.SMOKE_SEED_BASE = 18000
R.HERE, R.OUT, R.OUT_NOMAG = HERE, OUT, OUT_NOMAG
M4.OUT, M4.OUT_NOMAG = OUT, OUT_NOMAG
R.M5_FROZEN_PATHS = M7_FROZEN_PATHS

_m5_metadata, _m5_manifest_body = R._metadata, R.manifest_body


def _metadata(job: dict) -> dict:
    return {**_m5_metadata(job), "mechanism": MECHANISM}


def manifest_body(jobs_run, not_run, commit, env) -> dict:
    return {**_m5_manifest_body(jobs_run, not_run, commit, env), "mechanism": MECHANISM,
            "edge_radius": EDGE_R, "noslip_iterations": NOSLIP, "rest_s": REST_S}


R._metadata, R.manifest_body = _metadata, manifest_body

# ---- E1-7 factors ----------------------------------------------------------------------------------------------------
M4.E17_FACTORS = ([("edge_radius", E17_EDGE) if n == "chamfer" else (n, v) for n, v in M4.E17_FACTORS]
                  + [("noslip", E17_NOSLIP)])
M4.NOMINAL = ({x for x in M4.NOMINAL if x[0] != "chamfer"} | {("edge_radius", EDGE_R), ("noslip", NOSLIP)})
assert not any(n == "chamfer" for n, _ in M4.E17_FACTORS)

# ---- per-trial installs (edge, NoSlip), as the D15 rehearsals ----------------------------------------------------------
_ORIG: dict = {}


def install(r: float, n: int) -> dict:
    """scored.Trial -> a subclass with rounded edges of radius r (r1_run.install_edge); scored.build_m1_xml wrapped with
    D13's with_noslip(n) when n > 0 (d14s3_run.worker). Idempotent: always built on the original class and function.
    Returns a log the subclass fills with the compiled options of each trial model built."""
    if not _ORIG:
        _ORIG.update(trial=scored.Trial, xml=scored.build_m1_xml)
    Base, xml = _ORIG["trial"], _ORIG["xml"]
    log: dict = {"n_trials": 0, "noslip_wrapper_calls": 0}

    class M7Trial(Base):
        def __init__(self, params, *a, **k):
            super().__init__(dataclasses.replace(params, edge_profile="rounded", edge_radius=r), *a, **k)
            m = self.model
            log["n_trials"] += 1
            log["options"] = {"timestep": float(m.opt.timestep), "iterations": int(m.opt.iterations),
                              "noslip_iterations": int(m.opt.noslip_iterations), "tolerance": float(m.opt.tolerance)}

    def wrapped(p):
        log["noslip_wrapper_calls"] += 1
        return D13.with_noslip(xml(p), n)

    scored.Trial = M7Trial
    scored.build_m1_xml = wrapped if n else xml
    return log


def e11_pass(rec: dict) -> bool:
    """D14's e11_pass (d14s3_analyze.py:105-110), copied so workers need not import D14; equality is tested on R4's
    committed rest records. B1 has no radial joint, so M1's radial pop does not apply (D14)."""
    return bool(rec.get("integrity_ok") and not rec.get("aborted") and rec.get("t0_solved") and rec.get("final_solved")
                and rec["rest_rotation_deg"] <= E11_THRESH["rest_rotation_deg"]
                and rec["penetration_mm"] <= E11_THRESH["penetration_mm"]
                and rec["radial_offset_mm_t0"] <= E11_THRESH["radial_offset_mm"])


def _plain(x):
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if isinstance(x, np.ndarray):
        return _plain(x.tolist())
    if isinstance(x, np.generic):
        return x.item()
    return x


def rest60(kw: dict, magnets_on: bool, r: float, n: int, duration: float = REST_S):
    """The D15 R2-R4 rest steps (r3_run.rest_worker) inside M5's run_job. Returns (record, ms, info) as run_trial."""
    ov = dict(kw.get("overrides", {}))
    install(r, 0)                                   # warm-up: edge, no NoSlip (as R2-R4)
    warm, _, _ = _m4_run_trial("rest", kw, magnets_on)
    ov2 = dict(ov)
    mp = R.magnet_params_for(ov2)                   # pops the magnet keys; ov2 keeps M1Params overrides
    if not magnets_on:
        mp = None
    gap = ov.get("gap", R.GAP)
    info = None if mp is None else M4.magnet_availability(mp)
    ms = M4.use_magnets(mp, gap)
    if ms is not None:
        ms.reset_neighbour_list()
        ms.reset_stats()
    M4.MagnetMonitor.last = None
    cfg = {"noslip_iterations": n, "params": ov2} if n else {"params": ov2}
    install(r, 0)                                   # d13_rest applies NoSlip itself, from cfg
    t0 = time.perf_counter()
    rec, cap = D13.d13_rest(scored, D10, kw["seed"], ms, cfg, duration_s=duration)
    rec = _plain(rec)
    ev = _plain(D13A.events(rec))
    ok11 = e11_pass(rec)
    reasons = ([] if ok11 else ["E1-1 criteria (e11_pass)"]) + ([f"{len(ev)} slip event(s) over {duration:g} s"]
                                                                 if ev else [])
    rec.update({"rest_s": duration, "variant": "V2", "cfg": _plain(cfg), "ok_e11": ok11, "slip_events": ev,
                "n_slip_events": len(ev), "ok_no_slip": not ev, "e11_fail_reasons": reasons,
                "pass": ok11 and not ev, "fail_reasons": reasons,
                "warmup_10s": _plain({k: warm.get(k) for k in ("rest_rotation_deg", "pass", "fail_reasons", "seed")}),
                "capture": None if cap is None else _plain({**cap["info"], "n_pre": cap["n_pre"],
                                                            "n_post": cap["n_post"]}),
                "wall_s": time.perf_counter() - t0,
                "magnets": None if ms is None else _plain(ms.describe()),
                "magnet_stats": None if ms is None else _plain(dict(ms.stats)), "magnet_table": info,
                "m7": {"edge_radius": r, "noslip": n, "kind": "rest60"}})
    return rec, ms, info


_m4_run_trial = M4.run_trial


def run_trial(kind: str, kw: dict, magnets_on: bool):
    """M4.run_trial with M7's per-trial installs. Consumes the E1-7 overrides `edge_radius` and `noslip`."""
    kw = copy.deepcopy(kw)
    ov = kw.setdefault("overrides", {})
    r = float(ov.pop("edge_radius", EDGE_R))
    n = int(ov.pop("noslip", NOSLIP))
    if kind == "rest60":
        return rest60(kw, magnets_on, r, n)
    log = install(r, n)
    rec, ms, info = _m4_run_trial(kind, kw, magnets_on)
    rec["m7"] = {"edge_radius": r, "noslip": n, "kind": kind, **log}
    return rec, ms, info


M4.run_trial = run_trial


# ---- job list ----------------------------------------------------------------------------------------------------------
def _e17_rest_settings() -> list[tuple[str, dict]]:
    """R3's 15 rest settings (P-84 D3) as E1-7 overrides, tagged as e17_trials tags them."""
    out = [("nominal", {})]
    for name, vals in (("timestep", [0.00025, 0.00075]), ("iterations", [50, 200]),
                       ("cubie_friction", [(0.1, 0.0025, 0.0005), (0.5, 0.0025, 0.0005), (1.0, 0.0025, 0.0005)]),
                       ("edge_radius", [0.0018, 0.0036]), ("gap", [2.5e-05, 0.0001]), ("magnet_scale", [0.67]),
                       ("noslip", [5, 20])):
        for v in vals:
            tag = f"{name}={v}".replace(" ", "").replace("(", "").replace(")", "").replace(",", "-")
            out.append((tag, {name: v}))
    assert len(out) == 15
    return out


def _rest_job(base: dict, exp: str, tid: str, seed: int, ov: dict) -> dict:
    j = copy.deepcopy(base)
    j.update({"exp": exp, "sub": exp, "tid": tid, "kind": "rest60", "magnets": True, "reported_only": True})
    j["kw"] = {"seed": seed, "overrides": {"gap": R.GAP, **ov}}
    j["arm"] = R.arm_of(j)
    return j


_m5_build = R.build_m5_jobs
_m5_smoke = R.smoke_jobs


def build_m7_jobs(commit: str, env: dict, validated_tilt: float) -> list[dict]:
    """M5's list on the patched globals, with E1-1 as kind rest60, plus E1-7's 15 rests and REST-X's 40."""
    jobs = _m5_build(commit, env, validated_tilt)
    e11 = [j for j in jobs if j["exp"] == "E1-1"]
    for j in e11:
        j["kind"] = "rest60"
    base = e11[0]
    e17_seed = M4.shift_seed(1000)
    jobs += [_rest_job(base, "E1-7", f"{tag}__rest60", e17_seed, ov) for tag, ov in _e17_rest_settings()]
    plus = M4.SEED_SHIFT - _M5["SEED_SHIFT"]
    rx = [s - SEED_PLUS + plus for s in REST_X_SEEDS]          # REST-X follows the active seed map
    jobs += [_rest_job(base, "REST-X", f"rest_s{s}", s, {}) for s in rx]
    keys = [R.key_of(j) for j in jobs]
    assert len(keys) == len(set(keys)), "duplicate record keys"
    return jobs


def smoke_m7_jobs(commit: str, env: dict, validated_tilt: float) -> list[dict]:
    jobs = _m5_smoke(commit, env, validated_tilt)
    for j in jobs:
        if j["kind"] == "rest":
            j["kind"] = "rest60"
    return jobs


R.build_m5_jobs = build_m7_jobs
R.smoke_jobs = smoke_m7_jobs


# ---- self-check (section 6.2; unscored; rehearsal seeds) -------------------------------------------------------------
SC_E17 = ("nominal__sexy6", "edge_radius=0.0018__6move", "noslip=5__6move", "magnet=none__6move",
          "nominal__rest60", "magnet_scale=0.67__rest60")        # magnet=none: the no-magnet path (E1-6n's)


def selfcheck_jobs(env: dict) -> list[dict]:
    """The first magnet-arm trial of every Option A sub-experiment and SC_E17, on the rehearsal mapping (+6000)."""
    set_seed_map(REHEARSAL_PLUS, (16000, 16999))
    try:
        jobs = build_m7_jobs("selfcheck", env, M4.nominal_validated_tilt())
    finally:
        set_seed_map(SEED_PLUS, (17000, 17999))
    out, seen = [], set()
    for j in jobs:
        if not j["magnets"]:
            continue
        if j["exp"] == "E1-7" and j["tid"] in SC_E17:
            out.append(j)
        elif j["exp"] not in ("E1-7", "REST-X") and j["sub"] not in seen:
            seen.add(j["sub"])
            out.append(j)
    for j in out:
        j["scored"], j["smoke"] = False, True
    assert len(out) == 10 + len(SC_E17), len(out)
    return out


def selfcheck_ref(job: dict) -> Path:
    """The committed D15 rehearsal record the self-check trial must reproduce."""
    if job["exp"] == "E1-7":
        if job["kind"] == "rest60":
            return D15 / "r3" / "rests" / f"{job['tid']}.json.gz"
        return D15 / "r3" / "E1-7" / f"{job['tid']}.json.gz"
    if job["sub"] == "E1-1":
        return D15 / "r2/R25/L0/E1-1" / f"rest_s{job['kw']['seed']}.json.gz"
    src = "r1" if job["sub"] in ("E1-2", "E1-5", "E1-5s") else "r2"
    return D15 / src / "R25/L0" / job["exp"] / f"{job['tid']}.json.gz"


def _load_gz(p: Path) -> dict:
    import gzip
    return json.loads(gzip.decompress(p.read_bytes()))


def selfcheck_compare(job: dict, rec: dict) -> list[str]:
    """0 differences required. Rests: every field of the rehearsal's d13 record equals M7's. Turn trials:
    er9g_run.gs_diff with the rehearsal's logging blocks and M7's bookkeeping removed on both sides."""
    ER9 = _exec("er9g_run", REPO / "experiments/ER9_anchored_core_layouts/er9g_run.py")
    ref = _load_gz(selfcheck_ref(job))
    mine = json.loads(json.dumps(rec, default=list))
    if job["kind"] == "rest60":
        ref_rec = ref["record"]
        return ER9.gs_diff(ref_rec, {k: mine.get(k) for k in ref_rec})
    drop = ("d15", "d14s3", "m7", "er9", "er9_arm", "er7_arm", "er7_flag_outside_regime", "er7_wall_s", "mechanism",
            "arm", "scored", "smoke", "reported_only", "source_commit", "startup_checks", "base_overrides",
            "environment", "loadavg_start", "wall_s", "wall_time_s")
    strip = lambda r: {k: v for k, v in r.items() if k not in drop}  # noqa: E731
    spec = copy.deepcopy(mine.get("spec") or {})                 # R3 set the edge and NoSlip per job, not in spec
    for k in ("edge_radius", "noslip"):
        (spec.get("overrides") or {}).pop(k, None)
    mine["spec"] = spec
    return ER9.gs_diff(strip(ref), strip(mine))


def _sc_worker(job: dict) -> dict:
    key, rec = R.run_job(job)
    return {"tid": job["tid"], "sub": job["sub"], "kind": job["kind"], "ref": str(selfcheck_ref(job).relative_to(REPO)),
            "diffs": selfcheck_compare(job, rec), "pass": rec.get("pass")}


def selfcheck(n_workers: int) -> int:
    env = R.environment()
    jobs = selfcheck_jobs(env)
    for j in jobs:
        j["commit"], j["startup"], j["magnet_info"] = "selfcheck", None, None
    with multiprocessing.get_context("fork").Pool(n_workers, maxtasksperchild=1) as pool:
        rows = pool.map(_sc_worker, jobs, chunksize=1)
    ok = all(not r["diffs"] for r in rows)
    SELFCHECK_OUT.mkdir(parents=True, exist_ok=True)
    out = {"note": "UNSCORED M7 self-check (pre-registration section 6.2); rehearsal seeds only", "pass": ok,
           "environment": env, "head": scored._git("rev-parse", "HEAD"),
           "trials": [{**r, "n_diffs": len(r["diffs"]), "diffs": r["diffs"][:20]} for r in rows]}
    (SELFCHECK_OUT / "selfcheck.json").write_text(json.dumps(out, indent=1, default=str))
    for r in rows:
        print(f"{'OK  ' if not r['diffs'] else 'DIFF'} {r['sub']:6} {r['tid']:32} {len(r['diffs'])} diffs "
              f"{r['diffs'][:3]}", flush=True)
    print(f"self-check: {'PASS' if ok else 'FAIL'}", flush=True)
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["selfcheck"]:
        n = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 6
        sys.exit(selfcheck(n))
    R.main(argv)


if __name__ == "__main__":
    main()
