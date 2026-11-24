"""D15 R1 runner (P-79; PROTOCOL_R1.md): rounded piece edges at R 2.5 / 1.4 mm, L0 / PG8 / PG20, NoSlip 10.
E1-1: 20 rests of 10 s (D14 Stage 1's worker steps); E1-2 / E1-5 / E1-5s: D14 Stage 2's 86 trials (d14s3_run.worker).
Writes only under results/r1/. Usage (WSL): python r1_run.py [--jobs 6] [--resume]"""
from __future__ import annotations

import argparse
import dataclasses
import gzip
import importlib.util
import json
import multiprocessing as mp_
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EXP14 = REPO / "experiments/D14_noslip_rest_rehearsal"
sys.path.insert(0, str(EXP14))
sys.path.insert(0, str(REPO / "src"))


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


S3 = _load("d14s3_run", EXP14 / "d14s3_run.py")
STAGE1 = _load("d14_run", EXP14 / "d14_run.py")
RUN2, D13 = S3.RUN2, S3.D13
OUT = HERE / "results" / "r1"
RADII = {"R25": 0.0025, "R14": 0.0014}          # run order: R25 first
ARMS = ("L0", "PG8", "PG20")
REST_SEEDS = tuple(range(16000, 16020))
REST_S = 10.0
NOSLIP = 10
SEQ_EXPS = ("E1-2", "E1-5", "E1-5s")
SEQ_COUNTS = {"E1-2": 24, "E1-5": 42, "E1-5s": 20}
COST_STOP_S = 6 * 3600.0
WORKERS = 6
assert STAGE1.CFG == {"noslip_iterations": NOSLIP} and S3.NOSLIP == NOSLIP


# ---- geometry ----------------------------------------------------------------------------------------------------------
def install_edge(scored, r: float) -> None:
    """scored.Trial -> a subclass that builds and records the trial with rounded edges of radius r."""
    Base = scored.Trial

    class EdgeTrial(Base):
        def __init__(self, params, *a, **k):
            super().__init__(dataclasses.replace(params, edge_profile="rounded", edge_radius=r), *a, **k)

    EdgeTrial.d15_edge_radius = r
    scored.Trial = EdgeTrial


def edge_errors(params: dict, r: float) -> list[str]:
    errs = []
    if params.get("edge_profile") != "rounded":
        errs.append(f"edge_profile {params.get('edge_profile')!r}")
    if params.get("edge_radius") != r:
        errs.append(f"edge_radius {params.get('edge_radius')!r} != {r}")
    return errs


# ---- paths -------------------------------------------------------------------------------------------------------------
def rest_path(tag: str, arm: str, seed: int) -> Path:
    return OUT / tag / arm / "E1-1" / f"rest_s{seed}.json.gz"


def seq_path(tag: str, arm: str, exp: str, tid: str) -> Path:
    return RUN2.record_path(OUT / tag, arm, exp, tid)


def job_path(job: dict) -> Path:
    if job["d15_kind"] == "rest":
        return rest_path(job["d15_tag"], job["arm"], job["seed"])
    return seq_path(job["d15_tag"], job["er9g_arm"], job["exp"], job["tid"])


def dump(obj: dict) -> bytes:
    return gzip.compress(json.dumps(obj, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x)).encode(),
                         9, mtime=0)


def write_new(p: Path, obj: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "xb") as fh:
        fh.write(dump(obj))


# ---- workers (fresh process each) ----------------------------------------------------------------------------------------
def rest_worker(job: dict) -> dict:
    """d14_run.run_job's steps for one (arm, seed) with rounded edges and a 10 s rest; returns the record (not written)."""
    arm, seed, base_job, r = job["arm"], job["seed"], job["base_job"], job["d15_r"]
    assert arm in ARMS and seed in REST_SEEDS and base_job["kw"]["seed"] == seed and base_job["sub"] == "E1-1"
    E9 = D13.E9
    LY = D13._load("er9g_layouts", E9 / "er9g_layouts.py")
    P = LY.probe_module()
    E7, M4, R = P.E7, P.M4, P.R
    D10 = sys.modules["d10_rest"]
    from rubiknetic.cube_physics import scored
    from rubiknetic.cube_physics.m1_model import M1Params
    install_edge(scored, r)
    t0 = time.perf_counter()
    ov = dict(base_job["kw"].get("overrides", {}))
    acc = ST = None
    if arm in ("PG8", "PG20"):
        ST = D13._load("er9g_stats", E9 / "er9g_stats.py")
        LY.install_er7(arm, D13.GRADE, cls=ST.with_class_stats(M4.RecordingMagnetSystem))
        E7.setup_arm("L0")
        ms = M4.use_magnets(R.magnet_params_for(dict(ov)), ov.get("gap", M1Params().gap))
        acc = ST.attach(ms, job["d_val"])
    warm = E7.run_one({**base_job, "er7_arm": "L0", "rest60": False})
    ms = M4.use_magnets(R.magnet_params_for(dict(ov)), R.GAP)
    ms.reset_neighbour_list()
    ms.reset_stats()
    M4.MagnetMonitor.last = None
    if acc is not None:
        acc = ST.attach(ms, job["d_val"])
    rec, cap = D13.d13_rest(scored, D10, seed, ms, STAGE1.CFG, duration_s=REST_S)
    rec["magnet_stats"] = dict(ms.stats)
    if acc is not None:
        rec["class_stats"] = acc.as_dict(dict(ms.stats))
    return {"arm": arm, "seed": seed, "tag": job["d15_tag"], "edge_radius": r, "rest_s": REST_S,
            "variant": STAGE1.VARIANT, "cfg": STAGE1.CFG, "d_val_deg": job["d_val"],
            "warmup_10s": {k: warm.get(k) for k in ("rest_rotation_deg", "pass", "fail_reasons", "seed")},
            "warmup_params_edge": edge_errors(warm.get("params") or {}, r),
            "record": rec, "wall_s": time.perf_counter() - t0, "environment": job["env"],
            "capture": None if cap is None else {**cap["info"], "n_pre": cap["n_pre"], "n_post": cap["n_post"]}}


def seq_worker(job: dict) -> dict:
    from rubiknetic.cube_physics import scored
    install_edge(scored, job["d15_r"])
    rec = S3.worker({k: v for k, v in job.items() if not k.startswith("d15_")})
    rec["d15"] = {"tag": job["d15_tag"], "edge_radius": job["d15_r"], "kind": "seq"}
    return rec


def worker(job: dict) -> dict:
    return rest_worker(job) if job["d15_kind"] == "rest" else seq_worker(job)


# ---- checks ---------------------------------------------------------------------------------------------------------------
def proof_errors(job: dict, out: dict) -> list[str]:
    r = job["d15_r"]
    if job["d15_kind"] == "rest":
        rec = out["record"]
        errs = edge_errors(rec.get("params") or {}, r)
        if (rec.get("compiled_options") or {}).get("noslip_iterations") != NOSLIP:
            errs.append(f"rest noslip_iterations {(rec.get('compiled_options') or {}).get('noslip_iterations')}")
        return errs
    return S3.proof_errors(out) + edge_errors(out.get("params") or {}, r)


def trouble(job: dict, out: dict) -> list[str]:
    return RUN2.trouble(out["record"] if job["d15_kind"] == "rest" else out)


# ---- jobs ------------------------------------------------------------------------------------------------------------------
def all_jobs(env: dict) -> list[dict]:
    rest_base = STAGE1.base_jobs()
    seq = S3.base_jobs(env, SEQ_EXPS, NOSLIP)
    for arm in ARMS:
        got = {e: sum(j["er9g_arm"] == arm and j["sub"] == e for j in seq) for e in SEQ_EXPS}
        assert got == SEQ_COUNTS, (arm, got)
    out = []
    for tag, r in RADII.items():
        for arm in ARMS:
            for s in REST_SEEDS:
                out.append({"d15_kind": "rest", "d15_tag": tag, "d15_r": r, "arm": arm, "seed": s,
                            "base_job": rest_base[s], "d_val": None if arm == "L0" else RUN2.d_val(arm), "env": env})
        out += [{**j, "d15_kind": "seq", "d15_tag": tag, "d15_r": r} for j in seq]
    assert len(out) == 636, len(out)
    return out


# ---- parent -----------------------------------------------------------------------------------------------------------------
def say(msg: str) -> None:
    print(msg, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "r1_run_log.txt", "a") as fh:
        fh.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def label(job: dict) -> str:
    if job["d15_kind"] == "rest":
        return f"{job['d15_tag']} {job['arm']} E1-1/rest_s{job['seed']}"
    return f"{job['d15_tag']} {job['er9g_arm']} {job['exp']}/{job['tid']}"


def summary(job: dict, out: dict) -> str:
    if job["d15_kind"] == "rest":
        rec = out["record"]
        return (f"rest 0-10 s {rec.get('rest_rotation_deg', float('nan')):.6f} deg; "
                f"{'event' if out['capture'] else 'no event'}; wall {out['wall_s']:.0f} s")
    pm = out.get("per_move") or []
    peak = max((m.get("max_turner_torque_Nm") or 0.0 for m in pm), default=None)
    return (f"{'PASS' if out['pass'] else 'FAIL'}" + (f" peak {peak:.3f} N.m" if peak else "")
            + f"; wall {out['d14s3']['worker_wall_s']:.0f} s"
            + (f"; {'; '.join(out['fail_reasons'])}" if out.get("fail_reasons") else ""))


def code_is_committed() -> bool:
    paths = [str(HERE / f) for f in ("PROTOCOL_R1.md", "r1_run.py", "r1_analyze.py")]
    paths += [str(EXP14 / f) for f in ("d14s3_run.py", "d14s2_run.py", "d14_run.py")]
    paths += [str(REPO / "src/rubiknetic/cube_physics/m1_model.py"),
              str(REPO / "experiments/D13_rest_slip_mechanism/d13_run.py")]
    st = subprocess.run(["git", "status", "--porcelain", "--", *paths], cwd=REPO, capture_output=True, text=True)
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", *paths], cwd=REPO, capture_output=True)
    return st.stdout.strip() == "" and tracked.returncode == 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=WORKERS)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    if not code_is_committed():
        raise SystemExit("refusing: commit PROTOCOL_R1.md, r1_run.py, r1_analyze.py (and unchanged dependencies) first")
    env = D13.environment()
    jobs = all_jobs(env)
    todo = [j for j in jobs if not job_path(j).exists()]
    if len(todo) < len(jobs) and not a.resume:
        raise SystemExit("refusing: R1 records exist; use --resume")
    n = min(a.jobs, D13.workers_for(a.jobs))
    say(f"R1 start: commit {env['commit']}, {len(jobs) - len(todo)} / {len(jobs)} present, {n} workers, "
        f"free {D13.free_gb():.1f} GB")
    t_start = time.time()
    walls = {"rest": [], "seq": []}
    checked = False
    pending, i, done = [], 0, 0
    stop = pause = None
    with mp_.get_context("fork").Pool(n, maxtasksperchild=1) as pool:
        while i < len(todo) or pending:
            while not stop and not pause and i < len(todo) and len(pending) < n:
                pending.append((todo[i], pool.apply_async(worker, (todo[i],))))
                i += 1
            time.sleep(1.0)
            still = []
            for job, res in pending:
                if not res.ready():
                    still.append((job, res))
                    continue
                try:
                    out = res.get()
                except Exception as e:                       # noqa: BLE001
                    stop = f"worker error in {label(job)}: {e!r}"
                    say(stop)
                    continue
                write_new(job_path(job), out)
                done += 1
                walls[job["d15_kind"]].append(out["wall_s"] if job["d15_kind"] == "rest"
                                              else out["d14s3"]["worker_wall_s"])
                errs, tr = proof_errors(job, out), trouble(job, out)
                say(f"[{done}] {label(job)} {summary(job, out)}" + (f"; TROUBLE {tr}" if tr else "")
                    + (f"; PROOF ERROR {errs}" if errs else ""))
                if errs:
                    stop = f"proof error: {errs}"
                if tr and not pause:
                    pause = f"{label(job)}: {tr}"
            pending = still
            if not checked and len(walls["rest"]) >= 6 and len(walls["seq"]) >= 6:
                checked = True
                left = {"rest": sum(j["d15_kind"] == "rest" for j in todo[i:]),
                        "seq": sum(j["d15_kind"] == "seq" for j in todo[i:])}
                mean = {k: sum(v) / len(v) for k, v in walls.items()}
                proj = (time.time() - t_start) + sum(mean[k] * left[k] for k in left) / n
                with open(OUT / "r1_cost_checks.jsonl", "a") as fh:
                    fh.write(json.dumps({"mean_wall_s": mean, "left": left, "workers": n, "projected_total_s": proj,
                                         "limit_s": COST_STOP_S}) + "\n")
                say(f"cost check: projected {proj / 3600:.2f} h (limit {COST_STOP_S / 3600:.0f} h); "
                    f"mean wall rest {mean['rest']:.0f} s, other {mean['seq']:.0f} s")
                if proj > COST_STOP_S and not stop:
                    stop = "projected total exceeds the cost stop (PROTOCOL_R1 section 1)"
                    say(stop)
            if stop and not pending:
                break
    have = sum(job_path(j).exists() for j in jobs)
    if stop:
        say(f"R1 STOPPED: {stop}; {have} / {len(jobs)} records")
    elif pause:
        say(f"R1 PAUSED for the user: {pause}; {have} / {len(jobs)} records, {len(todo) - i} not started")
    else:
        say(f"R1 trials complete: {have} / {len(jobs)}")


if __name__ == "__main__":
    main()
