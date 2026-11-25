"""D15 R2 runner (P-81; PROTOCOL_R2.md): rounded edges at R 2.5 mm, L0 / PG8 / PG20, NoSlip 10.
Gate (E1-2 U_s16100 vs R1), E1-1 rests of 60 s, and D14 Stage 3b's E1-3 / E1-4 / E1-6 trials. E1-2 / E1-5 / E1-5s are
reused from R1 (not run here). Writes only under results/r2/. Usage (WSL): python r2_run.py [--jobs 6] [--resume]"""
from __future__ import annotations

import argparse
import gzip
import json
import multiprocessing as mp_
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r1_run as RUN1  # noqa: E402

S3, RUN2, D13 = RUN1.S3, RUN1.RUN2, RUN1.D13
REPO = RUN1.REPO
OUT = HERE / "results" / "r2"
TAG, R = "R25", 0.0025
ARMS = RUN1.ARMS
REST_SEEDS = RUN1.REST_SEEDS
REST_S = 60.0
EXPS3 = ("E1-3", "E1-4", "E1-6a", "E1-6b", "E1-6c", "E1-6t")
COUNTS3 = {"E1-3": 22, "E1-4": 40, "E1-6a": 6, "E1-6b": 6, "E1-6c": 8, "E1-6t": 16}
REUSED = ("E1-2", "E1-5", "E1-5s")
GATE_TRIAL = ("E1-2", "U_s16100")
WORKERS = 6
WALL_STOP_S = 12 * 3600.0
assert RUN1.RADII[TAG] == R and S3.EXPS3 == EXPS3 and S3.COUNTS3 == COUNTS3


# ---- paths ------------------------------------------------------------------------------------------------------------
def rest_path(arm: str, seed: int) -> Path:
    return OUT / TAG / arm / "E1-1" / f"rest_s{seed}.json.gz"


def seq_path(arm: str, exp: str, tid: str, gate: bool = False) -> Path:
    return RUN2.record_path(OUT / ("gate" if gate else TAG), arm, exp, tid)


def job_path(job: dict) -> Path:
    if job["d15_kind"] == "rest":
        return rest_path(job["arm"], job["seed"])
    return seq_path(job["er9g_arm"], job["exp"], job["tid"], gate=job.get("d15_gate", False))


def r1_path(arm: str, exp: str, tid: str) -> Path:
    return RUN1.seq_path(TAG, arm, exp, tid)


# ---- workers ------------------------------------------------------------------------------------------------------------
def worker(job: dict) -> dict:
    if job["d15_kind"] == "rest":
        RUN1.REST_S = REST_S                    # R1's rest worker reads its module constant: 60 s here (PROTOCOL_R2 §1)
        out = RUN1.rest_worker(job)
        assert out["rest_s"] == REST_S
        return out
    return RUN1.seq_worker({k: v for k, v in job.items() if k != "d15_gate"})


def proof_errors(job: dict, out: dict) -> list[str]:
    errs = RUN1.proof_errors(job, out)
    if job["d15_kind"] == "rest" and out.get("rest_s") != REST_S:
        errs.append(f"rest length {out.get('rest_s')}")
    return errs


# ---- jobs -----------------------------------------------------------------------------------------------------------------
def gate_jobs(env: dict) -> list[dict]:
    js = [j for j in S3.base_jobs(env, (GATE_TRIAL[0],), S3.NOSLIP) if j["tid"] == GATE_TRIAL[1]]
    assert len(js) == len(ARMS)
    return [{**j, "d15_kind": "seq", "d15_tag": TAG, "d15_r": R, "d15_gate": True} for j in js]


def main_jobs(env: dict) -> list[dict]:
    rest_base = RUN1.STAGE1.base_jobs()
    rests = [{"d15_kind": "rest", "d15_tag": TAG, "d15_r": R, "arm": a, "seed": s, "base_job": rest_base[s],
              "d_val": None if a == "L0" else RUN2.d_val(a), "env": env} for a in ARMS for s in REST_SEEDS]
    seq = [{**j, "d15_kind": "seq", "d15_tag": TAG, "d15_r": R} for j in S3.stage3b_jobs(env)]
    for arm in ARMS:
        got = {e: sum(j["er9g_arm"] == arm and j["sub"] == e for j in seq) for e in EXPS3}
        assert got == COUNTS3, (arm, got)
    order_e = {"E1-4": 0, "rest": 1, "E1-3": 2, "E1-6t": 3, "E1-6c": 4, "E1-6b": 5, "E1-6a": 6}
    order_a = {"PG20": 0, "PG8": 1, "L0": 2}
    allj = rests + seq
    allj.sort(key=lambda j: (order_e["rest" if j["d15_kind"] == "rest" else j["sub"]],
                             order_a[j["arm"] if j["d15_kind"] == "rest" else j["er9g_arm"]]))
    assert len(allj) == 3 * (20 + 98), len(allj)
    return allj


def reused_files() -> dict:
    """R1's R 2.5 records reused for E1-2 / E1-5 / E1-5s: {arm: {exp/tid: sha256}}; each arm must have 86."""
    import hashlib
    out = {}
    for arm in ARMS:
        files = {}
        for exp in REUSED:
            for p in sorted((RUN1.OUT / TAG / arm / exp).glob("*.json.gz")):
                files[f"{exp}/{p.name[:-8]}"] = hashlib.sha256(p.read_bytes()).hexdigest()
        out[arm] = files
    return out


# ---- parent ------------------------------------------------------------------------------------------------------------------
def say(msg: str) -> None:
    print(msg, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "r2_run_log.txt", "a") as fh:
        fh.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def run_batch(todo: list[dict], n: int, t_start: float, pause_on_trouble: bool) -> dict:
    pending, i, done = [], 0, 0
    stop = pause = None
    with mp_.get_context("fork").Pool(n, maxtasksperchild=1) as pool:
        while i < len(todo) or pending:
            while (not stop and not pause and i < len(todo) and len(pending) < n
                   and time.time() - t_start < WALL_STOP_S):
                pending.append((todo[i], pool.apply_async(worker, (todo[i],))))
                i += 1
            if i < len(todo) and not pending and time.time() - t_start >= WALL_STOP_S and not stop:
                stop = "wall-clock stop: 12 h since start (PROTOCOL_R2 section 1)"
                say(stop)
            time.sleep(1.0)
            still = []
            for job, res in pending:
                if not res.ready():
                    still.append((job, res))
                    continue
                try:
                    out = res.get()
                except Exception as e:                       # noqa: BLE001
                    stop = f"worker error in {RUN1.label(job)}: {e!r}"
                    say(stop)
                    continue
                RUN1.write_new(job_path(job), out)
                done += 1
                errs, tr = proof_errors(job, out), RUN1.trouble(job, out)
                say(f"[{done}] {'GATE ' if job.get('d15_gate') else ''}{RUN1.label(job)} {RUN1.summary(job, out)}"
                    + (f"; TROUBLE {tr}" if tr else "") + (f"; PROOF ERROR {errs}" if errs else ""))
                if errs:
                    stop = f"proof error: {errs}"
                if tr and pause_on_trouble and not pause:
                    pause = f"{RUN1.label(job)}: {tr}"
            pending = still
            if stop and not pending:
                break
    return {"done": done, "stop": stop, "pause": pause, "not_started": len(todo) - i}


def gate_check() -> dict:
    """Each gate record must equal R1's committed R 2.5 record exactly (logging blocks stripped on both sides)."""
    AN3 = RUN1._load("d14s3_analyze", RUN1.EXP14 / "d14s3_analyze.py")
    ER9 = RUN2.er9()
    rows = []
    for arm in ARMS:
        g = RUN2.load_rec(seq_path(arm, *GATE_TRIAL, gate=True))
        ref = RUN2.load_rec(r1_path(arm, *GATE_TRIAL))
        strip = lambda r: {k: v for k, v in AN3.strip(r).items() if k != "d15"}  # noqa: E731
        d = ER9.gs_diff(strip(ref), strip(g))
        rows.append({"arm": arm, "n_diffs": len(d), "diffs": d[:10], "pass": not d})
    return {"pass": all(r["pass"] for r in rows), "trials": rows}


def code_is_committed() -> bool:
    paths = [str(HERE / f) for f in ("PROTOCOL_R2.md", "r2_run.py", "r2_analyze.py", "r1_run.py", "PROTOCOL_R1.md")]
    paths += [str(RUN1.EXP14 / f) for f in ("d14s3_run.py", "d14s2_run.py", "d14_run.py", "d14s3_analyze.py")]
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
        raise SystemExit("refusing: commit PROTOCOL_R2.md, r2_run.py, r2_analyze.py (and unchanged dependencies) first")
    env = D13.environment()
    n = min(a.jobs, D13.workers_for(a.jobs))
    reuse = reused_files()
    if any(len(v) != 86 for v in reuse.values()):
        raise SystemExit(f"refusing: R1 R 2.5 records incomplete {[len(v) for v in reuse.values()]}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reused_r1_records.json").write_text(json.dumps(reuse, indent=1))
    gates, mains = gate_jobs(env), main_jobs(env)
    present = sum(job_path(j).exists() for j in gates + mains)
    if present and not a.resume:
        raise SystemExit("refusing: R2 records exist; use --resume")
    say(f"R2 start: commit {env['commit']}, {present} / {len(gates) + len(mains)} present, {n} workers, "
        f"free {D13.free_gb():.1f} GB")
    if n < a.jobs:
        say(f"R2 not started: only {n} workers possible (PROTOCOL_R2 section 1); free memory first")
        return
    t_start = time.time()
    gtodo = [j for j in gates if not job_path(j).exists()]
    if gtodo:
        r = run_batch(gtodo, min(n, len(gtodo)), t_start, pause_on_trouble=False)
        if r["stop"]:
            say(f"R2 STOPPED in the gate: {r['stop']}")
            return
    g = gate_check()
    (OUT / "r2_gate.json").write_text(json.dumps(g, indent=1))
    say(f"R2 gate: {'PASS' if g['pass'] else 'FAIL'} {[(t['arm'], t['n_diffs']) for t in g['trials']]}")
    if not g["pass"]:
        say("R2 stops: the gate failed (PROTOCOL_R2 section 1)")
        return
    todo = [j for j in mains if not job_path(j).exists()]
    r = run_batch(todo, n, t_start, pause_on_trouble=True)
    have = sum(job_path(j).exists() for j in mains)
    if r["stop"]:
        say(f"R2 STOPPED: {r['stop']}; {have} / {len(mains)} records")
    elif r["pause"]:
        say(f"R2 PAUSED for the user: {r['pause']}; {have} / {len(mains)} records, {r['not_started']} not started")
    else:
        say(f"R2 trials complete: {have} / {len(mains)}")


if __name__ == "__main__":
    main()
