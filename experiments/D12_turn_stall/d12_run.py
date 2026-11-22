"""D12 turning-stall diagnostic: driver (experiments/D12_turn_stall/PROTOCOL.md). Unscored, exploratory, diagnostic.

One simulation process at a time (section 12): the driver launches one fresh worker process per replay
(`d12_run.py _worker`, S3), waits for it, applies the stop rules, and only then starts the next. Records are one gzip
JSON per job, written by the worker to a temporary file and hard-linked to its final name (an existing record is never
overwritten; an existing record is skipped, so a rerun resumes). A crash is recorded with its traceback and is not
retried silently; a jam is a finding, not a crash.

Usage (WSL, repo root, idle machine, committed code):
    ~/.venvs/rubiknetic/bin/python experiments/D12_turn_stall/d12_run.py jobs [selfcheck|timing|stage1]   # print only
    ~/.venvs/rubiknetic/bin/python experiments/D12_turn_stall/d12_run.py selfcheck      # S1-S8; a failure stops D12
    ~/.venvs/rubiknetic/bin/python experiments/D12_turn_stall/d12_run.py --timing       # section 12 timing test
    ~/.venvs/rubiknetic/bin/python experiments/D12_turn_stall/d12_run.py set-floor --mb N   # record the memory floor
    ~/.venvs/rubiknetic/bin/python experiments/D12_turn_stall/d12_stage0.py       # then commit results/stage0/
    ~/.venvs/rubiknetic/bin/python experiments/D12_turn_stall/d12_run.py stage1   (then stage2, stage3, stage4)
    ~/.venvs/rubiknetic/bin/python experiments/D12_turn_stall/d12_analyze.py      # report (any time; read-only)
Stage gates: selfcheck passed, timing projection <= 6 h, memory floor recorded, Stage 0 output committed; each later
stage needs the previous stage complete (its job list depends on the previous stage's records).
Outputs only under experiments/D12_turn_stall/results/ (selfcheck/, timing/, stage1/ ... stage4/).
Exit codes: 0 done, 2 refused, 4 stopped by a stop rule (return to the user), 5 self-check failed.
"""
from __future__ import annotations

import time

_T_IMPORT = time.time()

import argparse  # noqa: E402
import gzip  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import d12_common as C  # noqa: E402

OUT = HERE / "results"
LOCK = OUT / ".d12_run.lock"
FLOOR = OUT / "timing" / "memory_floor.json"
ER9_DIAG = REPO / "experiments/ER9_anchored_core_layouts/results/probe/diag"
FROZEN_PATHS = C.FROZEN_PATHS     # code a D12 computation executes (all of src/, incl. the magnet force law), and the
#                                   records it reproduces or reads (S1 references, E1-7, V3 checks, M6 checks)


class Stop(Exception):
    """A stop rule fired: return to the user (exit 4)."""


class RefusedRun(Exception):
    """Preconditions not met (exit 2)."""


# ---- provenance and machine guards ----------------------------------------------------------------------------------
def git(*args: str) -> str:
    return C.git(*args).stdout.strip()


def require_unchanged_since(commit: str | None, what: str) -> None:
    """F1: refuse if frozen paths are dirty or differ between `commit` and HEAD (a commit outside them is allowed)."""
    probs = C.frozen_problems(commit)
    if probs:
        raise RefusedRun(f"refusing to run: {what} (commit {str(commit)[:12]}) may not match the code now:\n"
                         + "\n".join(probs))


def record_commit(rec: dict) -> str | None:
    return rec.get("commit") or (rec.get("job") or {}).get("commit")


def require_clean_commit() -> str:
    """Section 12: the runner refuses to run from uncommitted code."""
    dirty = git("status", "--porcelain", "--", *FROZEN_PATHS)
    if dirty:
        raise RefusedRun("refusing to run: uncommitted changes in paths a D12 computation uses:\n" + dirty)
    return git("rev-parse", "HEAD")


def require_repo_package() -> str:
    import rubiknetic
    p = Path(rubiknetic.__file__).resolve()
    src = REPO / "src"
    if not any(q.exists() and q.samefile(src) for q in p.parents):     # samefile: /mnt/c/dev == /mnt/c/Dev
        raise RefusedRun(f"refusing to run: rubiknetic is imported from {p}, not from this repository's src/")
    return str(p)


def other_simulations() -> list[str]:
    """Python processes running a script under experiments/ (section 12: never beside another simulation)."""
    me = {os.getpid(), os.getppid()}
    out = []
    for p in Path("/proc").glob("[0-9]*"):
        try:
            pid = int(p.name)
            if pid in me:
                continue
            argv = (p / "cmdline").read_bytes().split(b"\0")
        except (OSError, ValueError):
            continue
        argv = [a.decode(errors="replace") for a in argv if a]
        if argv and "python" in Path(argv[0]).name and any("experiments/" in a and a.endswith(".py") for a in argv[1:]):
            out.append(f"{pid}: {' '.join(argv)[:200]}")
    return out


class Lock:
    def __enter__(self):
        OUT.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise RefusedRun(f"refusing to run: {LOCK} exists (another D12 driver, or a stale lock: check, then "
                             f"remove it by hand)") from None
        os.write(fd, f"{os.getpid()}\n".encode())
        os.close(fd)
        return self

    def __exit__(self, *exc):
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass


def machine_state() -> dict:
    import d12_replay
    return d12_replay.machine_state()


def startup(mode: str) -> dict:
    commit = require_clean_commit()
    pkg = require_repo_package()
    others = other_simulations()
    if others:
        raise RefusedRun("refusing to run: other simulation processes are running (section 12):\n" + "\n".join(others))
    env = {"commit": commit, "rubiknetic": pkg, "machine": machine_state(), "mode": mode, "python": sys.executable}
    print(json.dumps(env, indent=1), flush=True)
    return env


# ---- records --------------------------------------------------------------------------------------------------------
def record_index() -> dict:
    """{job_id: path} over every result folder (a job is run once, wherever it first ran)."""
    out = {}
    for f in sorted(OUT.glob("*/*.json.gz")):
        out.setdefault(f.name[:-len(".json.gz")], f)
    return out


def read(path: Path) -> dict:
    return json.loads(gzip.decompress(Path(path).read_bytes()))


def write_json_once(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x") as f:
        json.dump(obj, f, indent=1, default=C.jsonable)


def store_job_list(folder: str, jobs: list[dict], extra: dict | None = None) -> None:
    """S5: print and store the full job list before the first replay; a stored list must not change."""
    path = OUT / folder / "jobs.json"
    ids = [j["job_id"] for j in jobs]
    for j in jobs:
        if j["kind"] in ("replay", "stage4"):
            C.check_seed(j["seed"], "replay" if j["kind"] == "replay" else j["trial_kind"],
                         j.get("move") if j["kind"] == "replay" else None)
    if path.exists():
        old = json.loads(path.read_text())
        if old["job_ids"] != ids:
            raise RefusedRun(f"refusing to run: {path} lists different jobs (the job list may not change)")
    else:
        write_json_once(path, {"job_ids": ids, "jobs": jobs, "thresholds_sha256": C.THRESHOLDS_SHA,
                               "seeds_allowed": sorted(C.ALLOWED_SEEDS), **(extra or {})})
    print(f"[{folder}] {len(jobs)} jobs:", flush=True)
    for j in jobs:
        print("  " + j["job_id"], flush=True)


def crash_record(job: dict, why: str, detail: dict) -> dict:
    return {"d12": "D12 crash record (driver)", "job_id": job["job_id"], "job": job, "crash": True, "error": why,
            **detail, "thresholds_sha256": C.THRESHOLDS_SHA}


def run_one(job: dict, folder: str, limit_s: float, env: dict) -> dict:
    """One job in a fresh process; returns its record (a crash record if the worker died or overran)."""
    import d12_replay
    job = {**job, "commit": env["commit"]}
    path = OUT / folder / f"{job['job_id']}.json.gz"
    cmd = [sys.executable, str(HERE / "d12_run.py"), "_worker", json.dumps(job, default=C.jsonable), str(path)]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=limit_s)
    except subprocess.TimeoutExpired as e:
        if not path.exists():
            d12_replay.write_record(path, crash_record(job, f"timeout after {limit_s:.0f} s (stop rule)",
                                                       {"stderr_tail": (e.stderr or "")[-4000:] if isinstance(e.stderr, str) else None}))
        raise Stop(f"{job['job_id']}: exceeded the per-replay limit of {limit_s:.0f} s (section 12)") from None
    wall = time.time() - t0
    if p.returncode == d12_replay.REFUSED_EXIT and not path.exists():
        raise RefusedRun(f"{job['job_id']}: the worker refused (nothing recorded):\n{p.stderr[-4000:]}")
    if not path.exists():
        d12_replay.write_record(path, crash_record(job, f"worker exited with {p.returncode} and no record",
                                                   {"stderr_tail": p.stderr[-4000:], "stdout_tail": p.stdout[-2000:]}))
    rec = read(path)
    rec["_driver_wall_s"] = wall
    return rec


def summary_line(rec: dict) -> str:
    if rec.get("crash"):
        return f"CRASH {rec['job_id']}: {rec.get('error')}"
    pr = rec.get("process") or {}
    res = f"wall {pr.get('wall_process_s') or 0:.0f} s, rss {pr.get('peak_rss_mb') or 0:.0f} MB"
    if rec["job"]["kind"] == "replay":
        f = rec["flags"]
        return (f"{rec['job_id']}: {rec['class']} impulse {rec['catch_impulse_Nms']:.5f} N m s, window peak "
                f"{rec['window_peak_Nm']:.3f}, peak {rec['peak_abs_torque_Nm']:.3f} N m"
                f"{' censored_R5' if f['censored_R5'] else ''}{' pad_limited' if f['pad_limited'] else ''}"
                f"{' FLAGGED' if rec['validity']['flagged'] else ''}, {res}")
    if rec["job"]["kind"] == "stage4":
        return f"{rec['job_id']}: {rec['guard_rail']}, {res}"
    return f"{rec['job_id']}: pass {rec.get('pass')}"


def load_timing() -> dict | None:
    p = OUT / "timing" / "timing.json"
    return json.loads(p.read_text()) if p.exists() else None


def load_floor() -> float | None:
    return json.loads(FLOOR.read_text())["floor_mb"] if FLOOR.exists() else None


def run_jobs(jobs: list[dict], folder: str, env: dict, timing: dict | None, floor: float | None,
             limit_fn=None) -> list[dict]:
    """limit_fn(job) -> seconds overrides the per-replay limit (Stage 4 trials, see C.stage4_trial_limit_s)."""
    idx = record_index()
    recs = []
    for k, job in enumerate(jobs, 1):
        if job["job_id"] in idx:
            old = read(idx[job["job_id"]])
            # F1: an existing record is reused only if the frozen paths did not change since its commit
            require_unchanged_since(record_commit(old), f"existing record {idx[job['job_id']].name}")
            print(f"[{folder} {k}/{len(jobs)}] skip (exists: {idx[job['job_id']].parent.name}) {job['job_id']}", flush=True)
            recs.append(old)
            continue
        # F1: the code must still be the code the driver started from (checked again inside the worker)
        require_unchanged_since(env["commit"], "the driver's start-up commit")
        ms = machine_state()
        if C.below_floor(ms.get("mem_available_mb"), floor):
            raise Stop(f"free memory {ms['mem_available_mb']:.0f} MB below the floor {floor:.0f} MB before "
                       f"{job['job_id']} (section 12)")
        cls_wall = cls_rss = None
        if timing is not None and job["kind"] == "replay":
            cls_wall = C.class_wall(timing["class_wall_s"], C.job_class(job))[0]
            cls_rss = C.class_wall(timing["class_rss_mb"], C.job_class(job))[0]
        # replays: 3 x the class's timing value, at most 15 min (section 12); Stage 4 trials: limit_fn
        if limit_fn is not None:
            limit = limit_fn(job)
        elif job["kind"] == "stage4":
            limit = C.STAGE4_FIRST_CAP_S
        else:
            limit = C.per_replay_limit_s(cls_wall)
        rec = run_one(job, folder, limit, env)
        print(f"[{folder} {k}/{len(jobs)}] {summary_line(rec)}", flush=True)
        recs.append(rec)
        rss = (rec.get("process") or {}).get("peak_rss_mb")
        if rss is not None and C.rss_exceeded(rss, cls_rss):
            raise Stop(f"{job['job_id']}: peak RSS {rss:.0f} MB > 2 x its class's timing value {cls_rss:.0f} MB")
    return recs


# ---- self-checks (section 10) ----------------------------------------------------------------------------------------
def _diff(a, b, path="") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{path}/{k}: missing on one side")
            else:
                out += _diff(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        return [x for i, (u, v) in enumerate(zip(a, b)) for x in _diff(u, v, f"{path}[{i}]")]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


def s1_compare(rec: dict, kind: str, ref_path: Path) -> dict:
    """Exact comparison of the rebuilt ER9 record with the committed one (every key of the committed record)."""
    ref = json.loads(ref_path.read_text())
    got = json.loads(json.dumps(rec["er9_compat"][kind], default=float))
    got = {k: got[k] for k in ref if k in got}
    d = _diff(ref, got)
    return {"reference": str(ref_path.relative_to(REPO)), "n_diffs": len(d), "diffs": d[:10], "pass": not d}


def s4_compare(r1: dict, r5: dict) -> dict:
    """R5 and R1 step digests identical up to (excluding) R1's first step with |actuator force| >= 0.999 N m."""
    k = r1["first_step_abs_tau_ge_0999"]
    n = len(r1["trace"]["steps"]) if k is None else k
    a, b = r1["trace"]["steps"][:n], r5["trace"]["steps"][:n]
    first = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
    ok = r1["trace"]["turn_start"] == r5["trace"]["turn_start"] and len(a) == len(b) == n and first is None
    return {"R1": r1["job_id"], "R5": r5["job_id"], "compared_steps": n, "R1_first_clip_step": k,
            "first_difference": first, "pass": bool(ok)}


def s3_check(recs: list[dict]) -> dict:
    """S3: every job ran alone in its own process. A record without process data (a driver-written crash record)
    fails the check instead of raising."""
    procs = [r.get("process") or {} for r in recs]
    missing = [r.get("job_id") for r, p in zip(recs, procs) if "pid" not in p]
    pids = [p["pid"] for p in procs if "pid" in p]
    ok = (not missing and all(p.get("jobs_in_process") == 1 for p in procs) and len(set(pids)) == len(recs))
    return {"pids": sorted(set(pids)), "missing_process_data": missing, "pass": bool(ok)}


def s5_check() -> dict:
    probes = {}
    for s in (10000, 10999, 17000, 17999, 16655, 16905, 16999, 1000, 16100, 16910, 16568):
        try:
            C.check_seed(s)
            probes[s] = "accepted"
        except C.Refused as e:
            probes[s] = f"refused: {e}"
    ok = all(probes[s].startswith("refused") for s in (10000, 10999, 17000, 17999, 16655, 16905, 16999, 1000)) and \
        all(probes[s] == "accepted" for s in (16100, 16910, 16568))
    lists = {"stage1": C.stage1_jobs(), "selfcheck": C.selfcheck_replays(), "timing": C.timing_replays()}
    used = sorted({j["seed"] for js in lists.values() for j in js})
    return {"guard_probes": probes, "seeds_in_fixed_lists": used, "n_stage1": len(lists["stage1"]),
            "pass": bool(ok and len(lists["stage1"]) == 102 and set(used) <= C.ALLOWED_SEEDS)}


def s6_s7_draws() -> dict:
    """S6 on the draw function and S7 on the step arithmetic, for every replay seed (no simulation)."""
    from dataclasses import asdict
    from rubiknetic.cube_physics import scored
    rows6, rows7 = [], []
    for seed in sorted(C.REPLAY_SEED_MOVE):
        nom = asdict(scored.draw_setup(seed))
        for chk, spec in C.CHECKS.items():
            got = asdict(C.draw_then_replace(scored.draw_setup, seed, spec["setup"]))
            ut = C.fields_under_test(C.setting(check=chk), "R5")["setup"]
            d = C.s6_diffs(nom, got, ut)
            replaced = True
            if spec["setup"].get("misalign_zero"):
                replaced = all(v == 0.0 for v in got["misalign_deg"].values())
            if "grip_force" in spec["setup"]:
                replaced = got["grip_force"] == spec["setup"]["grip_force"]
            rows6.append({"seed": seed, "check": chk, "diffs": d, "under_test": sorted(ut),
                          "replaced_as_specified": replaced, "pass": bool(not d and replaced)})
        rows7.append(C.s7_check(nom["turn_s_per_quarter"]))
    return {"S6": {"rows": rows6, "pass": all(r["pass"] for r in rows6)},
            "S7": {"rows": rows7, "pass": all(r["pass"] for r in rows7)}}


def selfcheck(env: dict) -> dict:
    res = {"env": env, "S5": s5_check()}
    res.update(s6_s7_draws())
    store_job_list("selfcheck", C.selfcheck_replays())
    store_job_list("stage1", C.stage1_jobs())
    special = [{"kind": k, "job_id": k.upper(), "stage": "selfcheck"} for k in ("s2_l0", "s2_w3", "s1b")]
    recs = {r["job_id"]: r for r in run_jobs(special + C.selfcheck_replays(), "selfcheck", env, None, None)}
    res["S2"] = {"L0": {k: recs["S2_L0"].get(k) for k in ("geometry", "l0_face_gap_ok", "l0_face_gaps_m",
                                                          "l0_face_gap_expected_m", "pass", "crash", "error")},
                 "W3": {k: recs["S2_W3"].get(k) for k in ("w3_magnet_positions_change_with_piece_gap",
                                                          "max_position_change_m", "note", "pass", "crash", "error")}}
    res["S2"]["pass"] = bool(recs["S2_L0"].get("pass") and recs["S2_W3"].get("pass"))
    res["S1b"] = {k: recs["S1B"].get(k) for k in ("callback_before_build", "callback_after_build",
                                                  "params_diffs_vs_E5_magnet_none", "pass", "crash", "error")}
    jid = lambda lay, rig: f"{lay}__{C.setting_tag(C.NOMINAL)}__{rig}__s16100"  # noqa: E731
    s1 = {}
    for arm in ("W3", "L0", "X0.003", "W1", "C52"):
        r = recs[jid(arm, "R1")]
        if r.get("crash"):
            s1[f"turn_{arm}"] = {"pass": False, "error": r.get("error")}
            continue
        s1[f"turn_{arm}"] = s1_compare(r, "turn", ER9_DIAG / f"turn_{arm}_s16100.json")
        if arm in ("W3", "L0"):
            s1[f"catch_{arm}"] = s1_compare(r, "catch", ER9_DIAG / f"catch_{arm}_s16100.json")
    res["S1"] = {"checks": s1, "pass": all(v["pass"] for v in s1.values())}
    s4 = {}
    for lay in C.STAGE_LAYOUTS:
        r1, r5 = recs[jid(lay, "R1")], recs[jid(lay, "R5")]
        s4[lay] = {"pass": False, "error": "crash"} if r1.get("crash") or r5.get("crash") else s4_compare(r1, r5)
    res["S4"] = {"layouts": s4, "pass": all(v["pass"] for v in s4.values())}
    reps = [r for r in recs.values() if r["job"]["kind"] == "replay"]
    res["S3"] = s3_check(list(recs.values()))
    res["S1b_replays"] = C.none_replays_clean(reps)       # the actual no-magnet replays ran without a callback
    import d12_analyze as A
    res["S6_records"] = A.s6_records(reps)
    res["S8"] = {"pass": bool(res["S1"]["pass"] and all(not r.get("crash") and not r["integrity"]["edit_audit_violations"]
                                                        for r in reps)),
                 "note": "hooks read mjData only; S1's bit-for-bit reproduction and AuditedSim's edit audit show it"}
    res["crashes"] = [r["job_id"] for r in recs.values() if r.get("crash")]
    keys = ("S1", "S1b", "S1b_replays", "S2", "S3", "S4", "S5", "S6", "S6_records", "S7", "S8")
    res["pass"] = bool(all(res[k]["pass"] for k in keys) and not res["crashes"])
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    write_json_once(OUT / "selfcheck" / f"selfcheck_{stamp}.json", res)
    (OUT / "selfcheck" / "selfcheck.json").write_text(json.dumps(res, indent=1, default=C.jsonable))
    return res


# ---- timing (section 12) ---------------------------------------------------------------------------------------------
def timing(env: dict) -> dict:
    jobs = C.timing_replays()
    store_job_list("timing", jobs)
    recs = run_jobs(jobs, "timing", env, None, None)
    idx = record_index()
    rows, wall, rss = [], {}, {}
    for j, r in zip(jobs, recs):
        if r.get("crash"):
            raise Stop(f"timing replay {r['job_id']} crashed: {r.get('error')}")
        cls = C.job_class(j)
        w, m = r["process"]["wall_process_s"], r["process"]["peak_rss_mb"]
        rows.append({"job_id": r["job_id"], "class": cls, "wall_process_s": w, "wall_replay_s": r["wall_replay_s"],
                     "peak_rss_mb": m, "machine_start": r["machine_start"],
                     "record": str(idx[r["job_id"]].relative_to(REPO))})
        wall[cls] = max(wall.get(cls, 0.0), w)
        rss[cls] = max(rss.get(cls, 0.0), m)
    proj = C.projection_s(wall)
    limits = {}
    for cls in sorted(set(C.projected_stage_counts()["stage1"]) | set(C.projected_stage_counts()["stage2"]) |
                      {C.class_key(lay, ts) for lay in C.CANDIDATE_LAYOUTS for ts in (0.0005, 0.00025)}):
        w, how = C.class_wall(wall, cls)
        limits[cls] = {"wall_s": w, "how": how, "per_replay_limit_s": C.per_replay_limit_s(w),
                       "rss_mb": C.class_wall(rss, cls)[0]}
    res = {"rows": rows, "class_wall_s": wall, "class_rss_mb": rss, "projection": proj, "limits": limits,
           "proposed_memory_floor_mb": 2.0 * max(rss.values()),
           "note": "every timing replay ran in its own process under its own job id (suffix '__timing'); no self-check "
                   "wall time is reused. wall = worker process wall (imports, model build, settle, replay, record); "
                   "load and free memory at each start are in the rows. Classes not timed at 0.25 ms are scaled by "
                   "L0's ratio (INFERENCE).",
           "env": env}
    p = OUT / "timing" / "timing.json"
    if p.exists():
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        p.rename(p.with_name(f"timing_superseded_{stamp}.json"))
    write_json_once(p, res)
    return res


# ---- stages ---------------------------------------------------------------------------------------------------------
def require_ready() -> tuple[dict, float]:
    s0 = OUT / "stage0" / "stage0.json"
    rel = str(s0.relative_to(REPO))
    if not s0.exists() or not git("ls-files", "--", rel) or git("status", "--porcelain", "--", rel):
        raise RefusedRun("refusing to run: Stage 0's output (results/stage0/stage0.json, d12_stage0.py) must be "
                         "committed before Stage 1 (section 7.0)")
    sc = OUT / "selfcheck" / "selfcheck.json"
    if not (sc.exists() and json.loads(sc.read_text())["pass"]):
        raise RefusedRun("refusing to run: the self-checks have not passed (run 'selfcheck')")
    require_unchanged_since(json.loads(sc.read_text())["env"]["commit"], "the passing self-check")
    t = load_timing()
    if t is not None:
        require_unchanged_since(t["env"]["commit"], "the timing test")
    if t is None:
        raise RefusedRun("refusing to run: no timing test (run '--timing')")
    if t["projection"]["stop"]:
        raise Stop(f"the timing test projects Stages 1-3 at {t['projection']['total'] / 3600:.2f} h (> 6 h) or could "
                   f"not project ({t['projection']['missing_classes']}): return to the user")
    fl = load_floor()
    if fl is None:
        raise RefusedRun("refusing to run: the memory floor is not recorded (run 'set-floor --mb N' after reviewing "
                         "results/timing/timing.json)")
    return t, fl


def require_complete(jobs: list[dict], what: str) -> list[dict]:
    idx = record_index()
    missing = [j["job_id"] for j in jobs if j["job_id"] not in idx]
    if missing:
        raise RefusedRun(f"refusing to run: {what} is incomplete ({len(missing)} records missing, e.g. {missing[:3]})")
    return [read(idx[j["job_id"]]) for j in jobs]


def stage_jobs(stage: str) -> tuple[list[dict], dict]:
    import d12_analyze as A
    if stage == "stage1":
        return C.stage1_jobs(), {}
    s1 = require_complete(C.stage1_jobs(), "Stage 1")
    idx = A.index(s1)
    p_none, table = A.worst_none_point(idx)
    if stage == "stage2":
        why = None if p_none is not None else "no no-magnet grid point is jam-free (and crash-free) on all 3 seeds"
        return C.stage2_jobs(p_none), {"P_none": p_none, "worst_point_table": table, "P_none_absent_reason": why}
    s2 = require_complete(C.stage2_jobs(p_none), "Stage 2")
    idx = A.index(s1 + s2)
    cand = A.candidates(idx, p_none)
    if stage == "stage3":
        return C.stage3_jobs(cand["selected"]), {"candidates": cand}
    s3 = require_complete(C.stage3_jobs(cand["selected"]), "Stage 3")
    idx = A.index(s1 + s2 + s3)
    cf = [A.catch_free(idx, lay, st) for lay, st in cand["selected"]]
    passing = [(x["layout"], x["setting"]) for x in cf if x["catch_free"]]
    sel = A.stage4_settings(idx, passing)
    if not sel["selected"]:
        return [], {"catch_free": cf, "stage4_settings": sel, "note": "no setting passed Stage 3: Stage 4 does not run"}
    return C.stage4_jobs(sel["selected"]), {"catch_free": cf, "stage4_settings": sel}


def run_stage(stage: str, env: dict) -> None:
    t, fl = require_ready()
    jobs, extra = stage_jobs(stage)
    print(json.dumps({k: v for k, v in extra.items()}, indent=1, default=C.jsonable)[:4000], flush=True)
    if not jobs:
        print(f"[{stage}] nothing to run", flush=True)
        return
    store_job_list(stage, jobs, extra)
    if stage != "stage4":
        run_jobs(jobs, stage, env, t, fl)
        return
    # Stage 4 trials are not replays: the first sequence trial is bounded at 30 min; every later trial at 3 x (the
    # first trial's wall per simulated second) x its estimated simulated time, within [5, 60] min
    # (C.stage4_trial_limit_s; the protocol's 3 x / 15 min rule is written for single-move replays).
    first = next(j for j in jobs if j["trial_kind"] == "seq")
    rec = run_jobs([first], stage, env, None, fl, limit_fn=lambda j: C.stage4_trial_limit_s(None, 0.0))[0]
    if rec.get("crash"):
        raise Stop(f"the first Stage 4 sequence trial crashed: {rec.get('error')}")
    est = {j["job_id"]: stage4_sim_estimate(j) for j in jobs}
    proj = C.stage4_projection_s(rec["process"]["wall_process_s"], est[first["job_id"]], list(est.values()))
    print(f"[stage4] projection {json.dumps(proj)}", flush=True)
    if proj["stop"]:
        raise Stop(f"Stage 4 projected at {proj['projected_s'] / 3600:.2f} h (> 4 h): return to the user")
    rate = proj["wall_per_sim_s"]
    run_jobs(jobs, stage, env, None, fl, limit_fn=lambda j: C.stage4_trial_limit_s(rate, est[j["job_id"]]))


def stage4_sim_estimate(job: dict) -> float:
    """Simulated seconds of a Stage 4 trial from its seed's turn-time draw (for the 4 h projection only)."""
    from rubiknetic.cube_logic import parse
    from rubiknetic.cube_physics import scored
    T = scored.draw_setup(job["seed"]).turn_s_per_quarter
    if job["trial_kind"] == "seq":
        return C.seq_sim_time_s([{1: 1, 2: 2, 3: 1}[m.quarter_turns] for m in parse(job["kw"]["moves"])], T)
    if job["trial_kind"] == "rest":
        return 0.5 + 10.0
    return 0.5 + 0.3 + T * abs(job["kw"]["delta_deg"]) / 90.0 + 0.9 + 1.0


def set_floor(mb: float | None, use_proposed: bool) -> dict:
    t = load_timing()
    if t is None:
        raise RefusedRun("refusing: no timing test yet")
    val = float(t["proposed_memory_floor_mb"]) if use_proposed else float(mb)
    obj = {"floor_mb": val, "proposed_mb": t["proposed_memory_floor_mb"], "set_utc":
           time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "basis": "section 12: recorded before Stage 1"}
    write_json_once(FLOOR, obj)
    return obj


# ---- main -----------------------------------------------------------------------------------------------------------
def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "_worker":
        import d12_replay
        d12_replay._STATE["t_import"] = _T_IMPORT
        return d12_replay.worker_main(json.loads(argv[1]), Path(argv[2]))
    ap = argparse.ArgumentParser(description="D12 turning-stall diagnostic driver")
    ap.add_argument("mode", nargs="?", choices=("jobs", "selfcheck", "timing", "set-floor", "stage1", "stage2",
                                                 "stage3", "stage4"))
    ap.add_argument("what", nargs="?", default="stage1")
    ap.add_argument("--timing", action="store_true", help="run the section 12 timing test")
    ap.add_argument("--mb", type=float)
    ap.add_argument("--use-proposed", action="store_true")
    a = ap.parse_args(argv)
    mode = "timing" if a.timing else a.mode
    if mode is None:
        ap.error("give a mode or --timing")
    try:
        if mode == "jobs":
            js = {"selfcheck": C.selfcheck_replays, "timing": C.timing_replays, "stage1": C.stage1_jobs}[a.what]()
            for j in js:
                print(j["job_id"])
            print(f"{len(js)} jobs")
            return 0
        if mode == "set-floor":
            if a.mb is None and not a.use_proposed:
                ap.error("set-floor needs --mb N or --use-proposed")
            print(json.dumps(set_floor(a.mb, a.use_proposed), indent=1))
            return 0
        with Lock():
            env = startup(mode)
            if mode == "selfcheck":
                res = selfcheck(env)
                print(json.dumps({k: (v.get("pass") if isinstance(v, dict) and "pass" in v else None)
                                  for k, v in res.items()}, indent=1), flush=True)
                return 0 if res["pass"] else 5
            if mode == "timing":
                res = timing(env)
                print(json.dumps({"class_wall_s": res["class_wall_s"], "class_rss_mb": res["class_rss_mb"],
                                  "projection": res["projection"],
                                  "proposed_memory_floor_mb": res["proposed_memory_floor_mb"]}, indent=1), flush=True)
                if res["projection"]["stop"]:
                    raise Stop("the timing test projects Stages 1-3 above 6 h (or could not project): return to the user")
                return 0
            run_stage(mode, env)
            return 0
    except RefusedRun as e:
        print(str(e), file=sys.stderr, flush=True)
        return 2
    except Stop as e:
        print(f"STOP: {e}", file=sys.stderr, flush=True)
        return 4


if __name__ == "__main__":
    sys.exit(main())
