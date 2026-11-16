"""Scored G1 runner for M5 (experiments/PHASE_1_M5_PREREGISTRATION.md, section 6.1 item 1).

M5 = M4 with the piece gap 0.2 -> 0.05 mm. The trial logic is M4's runner (experiments/E4_scored_m4/run.py), loaded
unchanged as a module; this file changes only the items the pre-registration lists in section 6.1 item 1:
  * gap 0.05 mm in BASE_OVERRIDES and in every trial's overrides (setdefault, so the E1-7 piece-gap arms keep theirs);
  * seeds = M4 scored seed + 4000 (SEED_SHIFT 9000, SNAP_SEED_BASE 10550, E16T_SEED_BASE 10640), range 10000-10999;
  * E1-4 scramble+inverse sequences drawn from the M5 seed (random_scramble(20, s));
  * the re-centred E1-7 factors (piece gap 0.025 / 0.05 / 0.1 mm, face gap 0.35 / 0.85 / 1.35 mm) with the wall
    computed from the 0.05 mm gap;
  * V3 records matched by size, grade and strength scale (exactly one match, wall ignored); the 0.35 mm pair check;
  * mechanism "M5", magnets.layout_gap in every magnet record, the start-up check at 0.05 mm with its gap recorded;
  * the run procedure of section 2: record key (arm, experiment, trial ID), first start, MANIFEST.json, STARTS.txt,
    resume with orphan handling (i) and ledger reconciliation (ii), atomic records written by the parent only,
    LEDGER.txt, harness exceptions as failing records (iii), MemoryError / OSError / a killed worker as interruptions.
  * revision 8: every start (not a dry run) refuses if a path the run uses lies in a OneDrive folder, or if the
    rubiknetic package is not imported from this repository.

Usage (WSL, from repo root):
    ~/.venvs/rubiknetic/bin/python experiments/E5_scored_m5/run.py all [--jobs N] [--dry-run]
    ~/.venvs/rubiknetic/bin/python experiments/E5_scored_m5/run.py smoke --smoke-dir DIR [--jobs N]
        [--stop-after N --stop-point {after_tmp,after_link,after_ledger}]       # UNSCORED; seeds 11000-11099
Exit codes: 0 complete, 2 refused, 3 interrupted (resume with the same command).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import multiprocessing
import os
import re
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_M4_NAME = "e4_scored_m4_run_for_m5"


def _load_m4():
    if _M4_NAME in sys.modules:
        return sys.modules[_M4_NAME]
    spec = importlib.util.spec_from_file_location(_M4_NAME, REPO / "experiments" / "E4_scored_m4" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_M4_NAME] = mod        # picklable exceptions (Refused) across worker processes
    spec.loader.exec_module(mod)
    return mod


M4 = _load_m4()

from rubiknetic.cube_logic import invert, random_scramble  # noqa: E402
from rubiknetic.cube_physics import scored  # noqa: E402
from rubiknetic.cube_physics.magnets import MagnetParams  # noqa: E402

# ---- M5 constants (pre-registration sections 1-4) -----------------------------------------------------------------
GAP = 5e-5                                   # piece gap 0.05 mm
E17_GAPS = [2.5e-5, 5e-5, 1e-4]              # piece-gap arm, A1 rule 0.5x / 1x / 2x
E17_FACE_GAPS_MM = [0.35, 0.85, 1.35]        # face-gap arm, M4's +/- 0.5 mm band around 0.85 mm
OUT = HERE / "results"                       # arm "magnets"
OUT_NOMAG = HERE / "results_nomag"           # arm "no_magnets" (E1-6n)
ARMS = ("magnets", "no_magnets")
MANIFEST, STARTS, LEDGER = "MANIFEST.json", "STARTS.txt", "LEDGER.txt"
INTERRUPTED = "_interrupted"
ENV_COMPARED = ("mujoco", "numpy", "scipy", "python", "cpu")   # SciPy added in revision 6 (review 5, O9)
PAIR_CHECK = M4.D8 / "results" / "d8_1b_checks_pair0.35mm_4x2_N35_s1.json"
M5_FROZEN_PATHS = M4.M4_FROZEN_PATHS + [
    "experiments/D8_alignment/results/d8_1b_checks*.json",
    "experiments/D8_alignment/v3_pair_extension.py",
    "experiments/PHASE_1_M5_PREREGISTRATION.md",
    "experiments/E5_scored_m5/run.py",
    "experiments/E5_scored_m5/analyze.py",
]
SMOKE_SEED_BASE = 11000                      # outside every registered range (P5)


class Interrupted(Exception):
    """The run stopped before completing; resume with the same command."""


# ---- patch M4's module globals (section 6.1 item 1) ---------------------------------------------------------------
M4.OUT, M4.OUT_NOMAG = OUT, OUT_NOMAG
M4.SEED_SHIFT = 9000                         # M1 offset + 9000 = M4 scored seed + 4000
M4.SCORED_SEED_RANGE = (10000, 10999)
M4.SNAP_SEED_BASE = 10550
M4.E16T_SEED_BASE = 10640
M4.BASE_OVERRIDES = {"radial_preload": 0.0, "gap": GAP}
M4.E17_FACTORS = [(n, E17_GAPS if n == "gap" else E17_FACE_GAPS_MM if n == "face_gap_mm" else v)
                  for n, v in M4.E17_FACTORS]
M4.NOMINAL = {("gap", GAP) if x[0] == "gap" else ("face_gap_mm", 0.85) if x[0] == "face_gap_mm" else x
              for x in M4.NOMINAL}
_m4_trials = M4.trials


def trials(exp: str) -> list:
    """M4's trial list for exp (seeds already shifted through the patched globals); E1-4 scrambles from the M5 seed."""
    out = []
    for tid, kind, kw in _m4_trials(exp):
        if exp == "E1-4" and tid.startswith("scr20inv_"):
            sc = random_scramble(20, kw["seed"])
            kw = {**kw, "moves": " ".join(str(m) for m in sc + invert(sc))}
        out.append((tid, kind, kw))
    return out


def magnet_params_for(ov: dict) -> MagnetParams | None:
    """As M4 (run.py:199-212), but a face-gap factor sets wall = (face gap - 0.05 mm) / 2 (run.py:211 used 0.2 mm)."""
    name = ov.pop("magnet", "4x2_N35")
    face_gap_mm = ov.pop("face_gap_mm", None)
    scale = ov.pop("magnet_scale", 1.0)
    if name == "none":
        return None
    dia, length, grade = M4.MAGNET_SIZES[name]
    kw = {"diameter": dia, "length": length, "grade": grade, "scale": scale}
    if face_gap_mm is not None:
        kw["wall"] = (face_gap_mm * 1e-3 - GAP) / 2
    return MagnetParams(**kw)


def v3_matches(mp: MagnetParams) -> list[tuple[Path, dict]]:
    """Section 4 matching rule: d8_1b_checks*.json files with a V3 block whose magnet_params diameter, length, grade
    and scale equal mp's; wall is ignored."""
    out = []
    for f in sorted((M4.D8 / "results").glob("d8_1b_checks*.json")):
        j = json.loads(f.read_text())
        if "V3" not in j:
            continue
        p = j.get("magnet_params", {})
        if (np.isclose(p.get("diameter", -1), mp.diameter) and np.isclose(p.get("length", -1), mp.length)
                and p.get("grade") == mp.grade and np.isclose(p.get("scale", -1), mp.scale)):
            out.append((f, j))
    return out


def v3_record_for(mp: MagnetParams) -> dict | None:
    """Replaces M4's size-only lookup (run.py:232-243): exactly one matching record, and it must pass."""
    m = v3_matches(mp)
    if len(m) != 1:
        return None
    f, j = m[0]
    v3 = j["V3"]
    if v3.get("pass") and "validated_tilt_deg" in v3:
        return {"validated_tilt_deg": float(v3["validated_tilt_deg"]), "v3_source": M4._rel(f),
                "v3_source_sha256": M4._sha256(f)}
    return None


M4.trials = trials
M4.magnet_params_for = magnet_params_for
M4.v3_record_for = v3_record_for


# ---- job list ------------------------------------------------------------------------------------------------------
def arm_of(job: dict) -> str:
    return "magnets" if job["magnets"] else "no_magnets"


def key_of(job: dict) -> tuple[str, str, str]:
    """Record key (U2): (arm, experiment, trial ID)."""
    return (arm_of(job), job["exp"], job["tid"])


def build_m5_jobs(commit: str, env: dict, validated_tilt: float) -> list[dict]:
    """The full scored M5 list (one 'all' call): E1-1..E1-6, E1-5s, E1-6t, E1-6n, E1-7."""
    jobs = M4.build_jobs("all", commit, env, validated_tilt, False)
    for j in jobs:
        j["kw"] = copy.deepcopy(j["kw"])
        j["kw"].setdefault("overrides", {}).setdefault("gap", GAP)   # N1: an E1-7 piece-gap value is kept
        j["arm"] = arm_of(j)
    keys = [key_of(j) for j in jobs]
    assert len(keys) == len(set(keys)), "duplicate record keys"
    return jobs


def smoke_jobs(commit: str, env: dict, validated_tilt: float) -> list[dict]:
    """UNSCORED smoke list (section 6.1 item 4): every trial kind, E1-6n jobs, and one E1-7 job per magnet
    configuration of the E1-7 list; seeds 11000-11099. Short moves; trial IDs are not scored IDs."""
    base = {"commit": commit, "env": env, "validated_tilt": validated_tilt, "smoke": True, "scored": False,
            "startup": None}
    s = SMOKE_SEED_BASE
    spec = [("E1-2", "seq", {"moves": "U", "seed": s + 0}),
            ("E1-1", "rest", {"seed": s + 1}),
            ("E1-5", "forgive", {"misalign_deg": 5.0, "seed": s + 2}),
            ("E1-6", "openpad", {"face": "U", "seed": s + 3}),
            ("E1-6", "opposed", {"faces": ["U", "R"], "torque_limit": 1.0, "seed": s + 4}),
            ("E1-6", "twist", {"corner": [1, 1, 1], "seed": s + 5}),
            ("E1-5s", "snap", {"delta_deg": 5.0, "seed": s + 6}),
            ("E1-6t", "twist_std", {"corner": [1, 1, 1], "seed": s + 7, "peak_Nm": M4.E16T_TORQUE_NM})]
    jobs = []
    for i, (exp, kind, kw) in enumerate(spec):
        tid = f"smoke_{kind}_s{kw['seed']}"
        for mag in (True, False) if kind in ("seq", "opposed") else (True,):
            jobs.append({**base, "exp": exp, "sub": M4.sub_experiment(exp, kind), "tid": tid, "kind": kind,
                         "kw": {**copy.deepcopy(kw), "overrides": {"gap": GAP}}, "magnets": mag,
                         "reported_only": True})
    seen = set()
    for tid, kind, kw in trials("E1-7"):
        ov = kw.get("overrides", {})
        cfg = json.dumps({k: ov[k] for k in ov if k in M4._MAGNET_KEYS or k == "gap"}, sort_keys=True)
        if cfg in seen or not tid.endswith("__6move"):
            continue
        seen.add(cfg)
        k = {**copy.deepcopy(kw), "moves": "U", "seed": s + 50 + len(seen)}
        k.setdefault("overrides", {}).setdefault("gap", GAP)
        jobs.append({**base, "exp": "E1-7", "sub": "E1-7", "tid": f"smoke_{tid}", "kind": "seq", "kw": k,
                     "magnets": True, "reported_only": True})
    for j in jobs:
        j["arm"] = arm_of(j)
    return jobs


# ---- availability: runnable / registered "not run" / refused (sections 2 and 4) ------------------------------------
def v3_rule(job: dict) -> tuple[str, str | None]:
    """Section 4 rule from committed files only (the V3 records and the 0.35 mm pair check): ('run', None) |
    ('not_run', reason) | ('refused', message). It never reads the git-ignored near-field tables, so the verdict
    script can re-derive the "not run" set on a fresh clone (revision 7, review 6 W1)."""
    if not job["magnets"]:
        return "run", None
    ov = dict(job["kw"].get("overrides", {}))
    face_gap = ov.get("face_gap_mm")
    mp = magnet_params_for(ov)
    if mp is None:
        return "run", None
    matches = v3_matches(mp)
    tag = f"{mp.diameter * 1e3:g}x{mp.length * 1e3:g} mm {mp.grade} scale {mp.scale:g}"
    if len(matches) != 1:
        return "refused", f"{len(matches)} V3 records match {tag} (exactly one required)"
    if not matches[0][1]["V3"].get("pass"):
        if job["exp"] == "E1-7":
            return "not_run", "failed V3"
        return "refused", f"V3 failed for {tag} outside E1-7"
    if face_gap is not None and np.isclose(face_gap, 0.35):
        if not PAIR_CHECK.exists():
            return "refused", f"0.35 mm pair check {M4._rel(PAIR_CHECK)} missing (section 6.1 item 5)"
        if not json.loads(PAIR_CHECK.read_text())["V3_pair_extension"]["pass"]:
            return "not_run", "outside V3"
    return "run", None


def v3_not_run(jobs: list[dict]) -> dict:
    """{key: reason} of the V3 rule's "not run" and refused outcomes (refusals as "refused: <message>"). Used by the
    verdict script; reads committed files only."""
    out = {}
    for j in jobs:
        status, msg = v3_rule(j)
        if status == "not_run":
            out[key_of(j)] = msg
        elif status == "refused":
            out[key_of(j)] = f"refused: {msg}"
    return out


def classify(job: dict) -> tuple[str, str | None, dict | None]:
    """('run', None, magnet_info) | ('not_run', reason, None) | ('refused', message, None): the V3 rule, then (runner
    only) the near-field tables must exist on the default grid."""
    status, msg = v3_rule(job)
    if status != "run":
        return status, msg, None
    mp = magnet_params_for(dict(job["kw"].get("overrides", {}))) if job["magnets"] else None
    if mp is None:
        return "run", None, None
    try:
        info = M4.magnet_availability(mp)
    except M4.Refused as e:
        return "refused", str(e), None
    return "run", None, info


# ---- trial execution (worker side) ---------------------------------------------------------------------------------
def _metadata(job: dict) -> dict:
    return {"experiment": job["exp"], "sub_experiment": job["sub"], "trial_id": job["tid"], "kind": job["kind"],
            "spec": job["kw"], "source_commit": job["commit"], "environment": job["env"], "scored": job["scored"],
            "smoke": job["smoke"], "reported_only": job["reported_only"], "arm": arm_of(job), "mechanism": "M5",
            "base_overrides": M4.BASE_OVERRIDES, "startup_checks": job["startup"]}


def exception_record(job: dict, exc: BaseException) -> dict:
    """U1 (iii): a failing record with the job metadata and the configured gap fields."""
    ov = dict(job["kw"].get("overrides", {}))
    gap = ov.get("gap", GAP)
    mp = magnet_params_for(dict(ov)) if job["magnets"] else None
    rec = {"params": {"gap": gap}, "seed": job["kw"].get("seed"),
           "magnets": None if mp is None else {"params": asdict(mp), "layout_gap": gap},
           "magnet_stats": None, "magnet_table": job.get("magnet_info"),
           "harness_exception": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
           "pass_m1_criteria": False, "pass": False,
           "fail_reasons": [f"harness exception: {type(exc).__name__}: {exc}"]}
    if job["kind"] == "seq":
        rec["sequence"] = job["kw"]["moves"]
    rec.update(_metadata(job))
    return rec


def run_job(job: dict) -> tuple[tuple, dict]:
    """Runs one trial; returns (key, record). MemoryError, OSError and Refused propagate (interruption)."""
    try:
        load0 = os.getloadavg()[0]
        rec, ms, info = M4.run_trial(job["kind"], job["kw"], job["magnets"])
        layout_gap = M4._MS_KEY[1] if ms is not None else None
        tilt = (info or {}).get("validated_tilt_deg", job["validated_tilt"]) if ms is not None else None
        rec.update(_metadata(job))
        rec["loadavg_start"] = load0
        if rec.get("magnets") is not None:
            rec["magnets"]["layout_gap"] = layout_gap
        M4.apply_m4_criteria(rec, job["sub"], tilt, ms is not None)
        json.dumps(rec, default=list)   # review 5, O4: a record that cannot be saved is a failed trial, not a crash
    except (MemoryError, OSError, M4.Refused):
        raise
    except Exception as e:  # noqa: BLE001  (U1 iii: any other harness exception is a failed trial)
        rec = exception_record(job, e)
    return key_of(job), rec


# ---- files (parent side only) --------------------------------------------------------------------------------------
def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _append_line(path: Path, obj: dict) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(obj, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record_path(dirs: dict, key: tuple) -> Path:
    arm, exp, tid = key
    return dirs[arm] / exp / f"{tid}.json"


def write_record(dirs: dict, key: tuple, rec: dict, start_k: int, stop_point: str | None = None) -> str:
    """Section 2: temporary file, flush, os.link to the final name (fails if it exists), remove the temporary name,
    then one ledger line. stop_point simulates a kill (smoke test only)."""
    final = record_path(dirs, key)
    final.parent.mkdir(parents=True, exist_ok=True)
    tmp = final.parent / f".{final.stem}.json.tmp"
    data = json.dumps(rec, indent=1, default=list).encode()
    with open(tmp, "xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    if stop_point == "after_tmp":
        os._exit(3)
    os.link(tmp, final)
    if stop_point == "after_link":
        os._exit(3)
    os.unlink(tmp)
    sha = _sha(data)
    _append_line(dirs["magnets"] / LEDGER, {"start": start_k, "arm": key[0], "exp": key[1], "tid": key[2],
                                            "sha256": sha, "reconciled": False})
    if stop_point == "after_ledger":
        os._exit(3)
    return sha


def read_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def folder_is_empty(p: Path) -> bool:
    return not p.exists() or not any(p.iterdir())


def manifest_body(jobs_run: list[dict], not_run: list[tuple[dict, str]], commit: str, env: dict) -> dict:
    tables = {}
    for j in jobs_run:
        info = j.get("magnet_info")
        if info:
            tables[info["table_file"]] = info["table_sha256"]
    return {
        "mechanism": "M5", "commit": commit,
        "trials": [{"arm": j["arm"], "exp": j["exp"], "sub": j["sub"], "tid": j["tid"], "kind": j["kind"],
                    "seed": j["kw"]["seed"], "overrides": j["kw"].get("overrides", {})} for j in jobs_run],
        "not_run": [{"arm": j["arm"], "exp": j["exp"], "sub": j["sub"], "tid": j["tid"], "reason": r,
                     "seed": j["kw"]["seed"], "overrides": j["kw"].get("overrides", {})} for j, r in not_run],
        "tables": tables,
        "environment": env, "environment_compared": list(ENV_COMPARED),
        "frozen_paths": M5_FROZEN_PATHS + scored.FROZEN_PATHS,
    }


def _norm(x):
    return json.loads(json.dumps(x, sort_keys=True, default=list))


def write_manifest(dirs: dict, body: dict) -> None:
    """Review 5, O2 (a): the temporary file lives next to the results folder, not in it, so a kill before the link
    leaves results/ empty (the first start can be repeated) and a kill after it leaves nothing inside results/.
    A leftover temporary file from a killed first start is overwritten: no trial can have run without a manifest."""
    out = dirs["magnets"]
    out.mkdir(parents=True, exist_ok=True)
    data = json.dumps({**body, "created": _now()}, indent=1, sort_keys=True, default=list).encode()
    tmp = out.parent / f".{out.name}.{MANIFEST}.tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.link(tmp, out / MANIFEST)                     # fails if a manifest exists: one first start only
    os.unlink(tmp)


def resume_problems(manifest: dict, body: dict, head: str, check_git: bool = True,
                    result_paths: tuple = ()) -> list[str]:
    """Section 2 resume conditions; an empty list means the resume may proceed. result_paths (the results folders,
    relative to the repository) are diffed like the frozen paths: commits during the run may touch neither
    (review 5, O7)."""
    probs = []
    for k in ("trials", "not_run", "tables"):
        if _norm(manifest.get(k)) != _norm(body[k]):
            probs.append(f"{k} differ from the manifest")
    for k in ENV_COMPARED:
        if manifest.get("environment", {}).get(k) != body["environment"].get(k):
            probs.append(f"environment field {k} differs from the manifest")
    base = manifest["commit"].split("+")[0]            # smoke manifests carry "<commit>+smoke"
    if check_git and base != head:
        # an empty pathspec would diff the whole tree, so each diff runs only with paths
        diff = (scored._git("diff", "--name-only", base, head, "--", *manifest["frozen_paths"])
                if manifest["frozen_paths"] else "")
        if diff:
            probs.append(f"frozen paths differ between the manifest commit and HEAD: {diff}")
        if result_paths:
            diff = scored._git("diff", "--name-only", base, head, "--", *result_paths)
            if diff:
                probs.append(f"commits since the manifest commit touch the results folders: {diff}")
    return probs


def foreign_files(dirs: dict, starts: list[dict], manifest: dict) -> list[str]:
    """Files the verdict script would count as INVALID (section 2), other than orphan temporary files, which a
    resume moves. A resume refuses if any exist (review 5, O1). A .json file counts only if it is the record path
    of a manifest trial (revision 7, review 6 X3)."""
    logged = {(o["arm"], o["moved_to"]) for s in starts for o in s.get("orphans", [])}
    records = {record_path(dirs, (t["arm"], t["exp"], t["tid"])) for t in manifest["trials"]}
    bad = []
    for arm in ARMS:
        root = dirs[arm]
        if not root.exists():
            continue
        for p in root.iterdir():
            if p.is_file():
                if not (arm == "magnets" and p.name in (MANIFEST, STARTS, LEDGER)):
                    bad.append(f"{arm}/{p.name}")
            elif p.name == INTERRUPTED:
                bad += [f"{arm}/{f.relative_to(root)}" for f in p.iterdir()
                        if (arm, str(f.relative_to(root))) not in logged]
            else:
                for f in p.iterdir():
                    if not (f in records or (f.name.startswith(".") and f.name.endswith(".json.tmp"))):
                        bad.append(f"{arm}/{p.name}/{f.name}")
    return bad


def plan_resume(dirs: dict, manifest: dict, start_k: int) -> dict:
    """U1 (i) orphan temporary files to move and (ii) records whose ledger line is missing. Nothing is changed here:
    the plan is written to the start log first, then carried out by apply_resume (review 5, O2 b). Each moved name
    carries the start index, so two orphans of one trial never collide (O2 c)."""
    orphans, reconciled = [], []
    for arm in ARMS:
        root = dirs[arm]
        if not root.exists():
            continue
        for tmp in sorted(root.glob("*/.*.json.tmp")):
            dest = root / INTERRUPTED / f"k{start_k}__{tmp.parent.name}__{tmp.name}"
            orphans.append({"arm": arm, "path": str(tmp.relative_to(root)), "moved_to": str(dest.relative_to(root)),
                            "sha256": _sha(tmp.read_bytes())})
    ledger_keys = {(x["arm"], x["exp"], x["tid"]) for x in read_lines(dirs["magnets"] / LEDGER)}
    for t in manifest["trials"]:
        key = (t["arm"], t["exp"], t["tid"])
        p = record_path(dirs, key)
        if p.exists() and key not in ledger_keys:
            data = p.read_bytes()
            json.loads(data)                       # a record that does not parse stops the resume (INVALID)
            reconciled.append({"key": list(key), "sha256": _sha(data)})
    return {"orphans": orphans, "reconciled": reconciled}


def apply_resume(dirs: dict, plan: dict, start_k: int) -> None:
    for o in plan["orphans"]:
        root = dirs[o["arm"]]
        src, dest = root / o["path"], root / o["moved_to"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.link(src, dest)                         # fails rather than overwrite
        os.unlink(src)
    for r in plan["reconciled"]:
        arm, exp, tid = r["key"]
        _append_line(dirs["magnets"] / LEDGER, {"start": start_k, "arm": arm, "exp": exp, "tid": tid,
                                                "sha256": r["sha256"], "reconciled": True})


# ---- the run procedure ---------------------------------------------------------------------------------------------
def execute(dirs: dict, jobs: list[dict], not_run: list[tuple[dict, str]], commit: str, env: dict, head: str,
            startup: dict | None, n_workers: int, runner=run_job, stop_after: int | None = None,
            stop_point: str | None = None, check_git: bool = True, log=print) -> int:
    """First start or resume, then run every key without a record. Returns the number of records written.
    Raises Interrupted when stopped early, SystemExit on a refusal."""
    out = dirs["magnets"]
    body = manifest_body(jobs, not_run, commit, env)
    man_path = out / MANIFEST
    if not man_path.exists():
        for arm in ARMS:
            if not folder_is_empty(dirs[arm]):
                raise SystemExit(f"refusing first start: {dirs[arm]} is not empty and has no manifest")
        write_manifest(dirs, body)
        start_k, done = 1, {"orphans": [], "reconciled": []}
    else:
        manifest = json.loads(man_path.read_text())
        starts = read_lines(out / STARTS)
        rel = tuple(str(d.resolve().relative_to(REPO)) for d in dirs.values() if d.resolve().is_relative_to(REPO))
        probs = resume_problems(manifest, body, head, check_git, rel)
        probs += [f"file that would make the run INVALID: {f}" for f in foreign_files(dirs, starts, manifest)]
        if probs:
            raise SystemExit("refusing resume:\n  " + "\n  ".join(probs))
        commit = manifest["commit"]
        start_k = len(starts) + 1
        done = plan_resume(dirs, manifest, start_k)
    _append_line(out / STARTS, {"k": start_k, "time": _now(), "head": head, **done})    # the plan is logged first
    if start_k > 1:
        apply_resume(dirs, done, start_k)
    for j in jobs:
        j["commit"], j["startup"] = commit, startup
    todo = [j for j in jobs if not record_path(dirs, key_of(j)).exists()]
    todo.sort(key=lambda j: -len(j["kw"].get("moves", "").split()))
    log(f"start {start_k}: commit {commit}; {len(todo)} of {len(jobs)} trials to run; "
        f"{len(not_run)} registered not run; orphans moved {len(done['orphans'])}; "
        f"ledger lines reconciled {len(done['reconciled'])}")
    written = 0

    def _write(key, rec):
        nonlocal written
        sp = stop_point if (stop_after is not None and written + 1 == stop_after) else None
        write_record(dirs, key, rec, start_k, sp)
        written += 1
        log(f"{'PASS' if rec['pass'] else 'FAIL'} {key[0]}/{key[1]}/{key[2]} {'; '.join(rec['fail_reasons'])}")
        if stop_after is not None and written >= stop_after:
            raise Interrupted(f"stopped after {written} records (--stop-after)")

    if n_workers <= 1:
        for j in todo:
            try:
                key, rec = runner(j)
            except (MemoryError, OSError, M4.Refused) as e:
                raise Interrupted(f"{type(e).__name__}: {e}") from e
            _write(key, rec)
        return written
    ex = ProcessPoolExecutor(max_workers=n_workers, mp_context=multiprocessing.get_context("fork"))
    try:
        futs = [ex.submit(runner, j) for j in todo]
        for fut in as_completed(futs):
            try:
                key, rec = fut.result()
            except Exception as e:  # noqa: BLE001  (BrokenProcessPool, MemoryError, OSError, Refused)
                raise Interrupted(f"{type(e).__name__}: {e}") from e
            _write(key, rec)
    finally:
        ex.shutdown(wait=True, cancel_futures=True)
    return written


ONEDRIVE_DIR = re.compile(r"(?i)^onedrive\b")    # "OneDrive", "OneDrive - <organisation>"


def location_problems(paths: dict, package_file: Path, package_repo: Path, repo: Path) -> list[str]:
    """Revision 8 (replaces the OneDrive-process check of review 5, O1): no path the run reads or writes may lie in a
    OneDrive-synced folder, and the rubiknetic package must be imported from this repository. OneDrive may run.
    paths: {label: path}; every path is checked after resolving links."""
    probs = []
    for label, path in paths.items():
        real = Path(path).resolve()
        hits = [c for c in real.parts if ONEDRIVE_DIR.match(c)]
        if hits:
            probs.append(f"{label} {real} is inside a OneDrive folder ({hits[0]!r})")
    src = (Path(repo) / "src").resolve()
    if not Path(package_file).resolve().is_relative_to(src) or Path(package_repo).resolve() != Path(repo).resolve():
        probs.append(f"the rubiknetic package is imported from {Path(package_file).resolve()}, not from {src}")
    return probs


def require_local_location(smoke_dir: Path | None) -> None:
    paths = {"repository": REPO, "results folder": OUT, "no-magnet results folder": OUT_NOMAG,
             "M4 runner": Path(M4.__file__), "rubiknetic package": Path(scored.__file__)}
    if smoke_dir is not None:
        paths["smoke folder"] = smoke_dir
    probs = location_problems(paths, Path(scored.__file__), scored.REPO, REPO)
    if probs:
        raise SystemExit("refusing: the run must not use a OneDrive folder (pre-registration section 2, revision "
                         "8):\n  " + "\n  ".join(probs))


def require_m5_clean_commit() -> str:
    commit = scored.require_clean_commit()                       # M1 frozen paths
    dirty = scored._git("status", "--porcelain", "--", *M5_FROZEN_PATHS)
    if dirty:
        raise SystemExit("refusing to run scored trials: uncommitted changes in M5 frozen paths:\n" + dirty)
    return commit


def environment() -> dict:
    return {**scored.environment(), "scipy": scipy.__version__}


def startup_check() -> dict:
    """M4 rule 1 at the 0.05 mm gap, with the gap recorded (O2; review 3, item 10)."""
    res = M4.startup_checks(MagnetParams(), gap=GAP)
    res["gap"] = GAP
    return res


def prepare(jobs: list[dict]) -> tuple[list[dict], list[tuple[dict, str]], list[tuple[dict, str]]]:
    run, not_run, refused = [], [], []
    for j in jobs:
        status, msg, info = classify(j)
        if status == "run":
            j["magnet_info"] = info
            run.append(j)
        elif status == "not_run":
            not_run.append((j, msg))
        else:
            refused.append((j, msg))
    return run, not_run, refused


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("experiment", choices=["all", "smoke"])
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke-dir", type=Path)
    ap.add_argument("--stop-after", type=int)
    ap.add_argument("--stop-point", choices=["after_tmp", "after_link", "after_ledger"], default="after_ledger")
    a = ap.parse_args(argv)
    smoke = a.experiment == "smoke"
    if smoke != (a.smoke_dir is not None):
        raise SystemExit("'smoke' requires --smoke-dir, and --smoke-dir is only for 'smoke'")
    if a.stop_after is not None and not smoke:
        raise SystemExit("--stop-after is for the smoke test only")
    if smoke:                                    # review 5, O11: never write a smoke run into the scored folders
        sd = a.smoke_dir.resolve()
        if sd == HERE.resolve() or any(sd == p.resolve() or sd.is_relative_to(p.resolve()) for p in (OUT, OUT_NOMAG)):
            raise SystemExit(f"refusing: --smoke-dir {a.smoke_dir} would write into the scored folders")
    if not a.dry_run:                            # revision 8: every scored or smoke start
        require_local_location(a.smoke_dir)
    head = scored._git("rev-parse", "HEAD")
    if smoke:
        commit = head + "+smoke"
    elif a.dry_run:
        commit = "dry-run"
    else:
        commit = require_m5_clean_commit()
        if M4.E16C_THRESHOLD is None:
            raise SystemExit("refusing: E1-6c threshold not set (M4 pre-registration)")
    env = environment()
    tilt = M4.nominal_validated_tilt()
    jobs = smoke_jobs(commit, env, tilt) if smoke else build_m5_jobs(commit, env, tilt)
    run, not_run, refused = prepare(jobs)
    for j, msg in refused:
        print(f"REFUSED {key_of(j)}: {msg}", flush=True)
    for j, msg in not_run:
        print(f"NOT RUN {key_of(j)}: {msg}", flush=True)
    if a.dry_run:
        by = {}
        for j in run:
            by.setdefault((j["arm"], j["exp"]), []).append(j["kw"]["seed"])
        for (arm, e), seeds in sorted(by.items()):
            print(f"{arm} {e}: {len(seeds)} trials, seeds {min(seeds)}-{max(seeds)}")
        print(f"{len(run)} runnable, {len(not_run)} registered not run, {len(refused)} refused")
        return
    if refused:
        raise SystemExit(2)
    dirs = ({"magnets": a.smoke_dir / "results", "no_magnets": a.smoke_dir / "results_nomag"} if smoke
            else {"magnets": OUT, "no_magnets": OUT_NOMAG})
    startup = startup_check()
    print(f"start-up checks: {startup}", flush=True)
    if not startup["pass"]:
        raise SystemExit("refusing to run: magnet start-up integrity check failed")
    M4.use_magnets(None, GAP)                    # workers install their own configuration per trial
    t0 = time.perf_counter()
    try:
        n = execute(dirs, run, not_run, commit, env, head, startup, a.jobs,
                    stop_after=a.stop_after, stop_point=a.stop_point if a.stop_after else None,
                    log=lambda s: print(s, flush=True))
    except Interrupted as e:
        print(f"INTERRUPTED after {time.perf_counter() - t0:.0f} s: {e}. Resume with the same command.", flush=True)
        sys.exit(3)
    print(f"complete: {n} records written this start in {time.perf_counter() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
