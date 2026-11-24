"""D14 Stage 3a (model re-checks) and 3b (E1-3, E1-4, E1-6a/b/c/t) at noslip_iterations 10 (PROTOCOL_STAGE3.md,
committed before any computation). Reuses the Stage 2 harness (d14s2_run.install_logged_trial, er9g_run.run_one,
d13_run.with_noslip) with the NoSlip iteration count as a parameter.

Writes only under experiments/D14_noslip_rest_rehearsal/results/ (stage3a.json, stage3a/, stage3_gate/, stage3/, logs).
Usage (WSL, repo root): ~/.venvs/rubiknetic/bin/python experiments/D14_noslip_rest_rehearsal/d14s3_run.py [--jobs 4] [--resume]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import multiprocessing as mp_
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


RUN2 = _load("d14s2_run", HERE / "d14s2_run.py")
D13 = RUN2.D13
OUT = RUN2.OUT
S3A_FILE = OUT / "stage3a.json"
S3A_DIR = OUT / "stage3a"
GATE3 = OUT / "stage3_gate"
S3 = OUT / "stage3"
ARMS = RUN2.ARMS
EXPS3 = ("E1-3", "E1-4", "E1-6a", "E1-6b", "E1-6c", "E1-6t")
COUNTS3 = {"E1-3": 22, "E1-4": 40, "E1-6a": 6, "E1-6b": 6, "E1-6c": 8, "E1-6t": 16}
NOSLIP = 10
NOSLIP_CONV = 20
CHECK_TRIAL = ("E1-2", "U_s16100")
COST_STOP_S = 20 * 3600.0


# ---- worker ----------------------------------------------------------------------------------------------------------
def worker(job: dict) -> dict:
    """One trial (fresh process): NoSlip at job["d14s3_n"] iterations (0 = frozen), Stage 2's read-only logging."""
    ER9 = RUN2.er9()
    P, E7, M4, R = ER9.mods()
    from rubiknetic.cube_physics import scored
    n = int(job["d14s3_n"])
    calls = [0]
    if n:
        orig = scored.build_m1_xml

        def wrapped(p):
            calls[0] += 1
            return D13.with_noslip(orig(p), n)
        scored.build_m1_xml = wrapped
    log: dict = {}
    RUN2.install_logged_trial(scored, job["exp"] if job.get("d14s3_series") else "none", log)
    t0 = time.perf_counter()
    rec = ER9.run_one({k: v for k, v in job.items() if not k.startswith(("d14s2_", "d14s3_"))})
    if job["er9g_arm"] in ("PG8", "PG20"):
        ER9.apply_verdict(rec)
    ms = M4._MS
    rec["d14s3"] = {"noslip_n": n, "wrapper_calls": calls[0], "n_trials_constructed": log.get("n_trials", 0),
                    "trial_options": log.get("options"), "solver": log.get("solver"), "series": log.get("series"),
                    "magnet_model_noslip_iterations": int(ms.m.opt.noslip_iterations) if ms is not None else None,
                    "magnet_model_nv": int(ms.m.nv) if ms is not None else None,
                    "worker_wall_s": time.perf_counter() - t0}
    return rec


def proof_errors(rec: dict) -> list[str]:
    s = rec["d14s3"]
    n = s["noslip_n"]
    errs = []
    if s["wrapper_calls"] != (1 if n else 0):
        errs.append(f"wrapper_calls {s['wrapper_calls']}")
    if s["n_trials_constructed"] != 1:
        errs.append(f"trials constructed {s['n_trials_constructed']}")
    if (s["trial_options"] or {}).get("noslip_iterations") != n:
        errs.append(f"trial noslip_iterations {(s['trial_options'] or {}).get('noslip_iterations')} != {n}")
    if s["magnet_model_noslip_iterations"] not in (0, None):
        errs.append("magnet model has noslip")
    if s["magnet_model_nv"] is not None and s["magnet_model_nv"] != (s["trial_options"] or {}).get("nv"):
        errs.append("magnet model nv differs")
    return errs


def composite_worker(arm: str) -> dict:
    """er9g_composite_checks v4/v5/v6 for one arm with noslip_iterations 10 on every model they build."""
    CC = _load("er9g_composite_checks", RUN2.E9 / "er9g_composite_checks.py")
    D8 = CC.D8
    ob, orh = D8.build, D8.build_r_hinge_model

    def b(mp1):
        m, d = ob(mp1)
        m.opt.noslip_iterations = NOSLIP
        return m, d

    def brh(mp1):
        m, d = orh(mp1)
        m.opt.noslip_iterations = NOSLIP
        return m, d
    D8.build, D8.build_r_hinge_model = b, brh
    return {"arm": arm, "noslip_iterations": NOSLIP, "V4": CC.v4(arm), "V6": CC.v6(arm), "V5": CC.v5(arm)}


# ---- jobs ------------------------------------------------------------------------------------------------------------
def base_jobs(env: dict, subs, n: int) -> list[dict]:
    ER9 = RUN2.er9()
    _, E7, _, _ = ER9.mods()
    out = []
    base = [j for j in E7.er7_jobs() if j["sub"] in subs]       # ER7: exp "E1-6" holds subs E1-6a/b/c
    for arm in ARMS:
        dv = RUN2.d_val(arm)
        for j in base:
            ER9.check_seed(j["kw"]["seed"])
            job = ER9.make_job(j, arm, "d14s3", env, dv)
            job["d14s3_n"] = n
            out.append(job)
    return out


def stage3b_jobs(env: dict) -> list[dict]:
    js = base_jobs(env, EXPS3, NOSLIP)
    for arm in ARMS:
        got = {e: sum(j["er9g_arm"] == arm and j["sub"] == e for j in js) for e in EXPS3}
        assert got == COUNTS3, (arm, got)
    return js


def gate3_jobs(all3: list[dict]) -> list[dict]:
    firsts, seen = [], set()
    for j in all3:
        if j["er9g_arm"] == "L0" and j["sub"] not in seen:
            seen.add(j["sub"])
            firsts.append({**j, "d14s3_n": 0})
    assert len(firsts) == len(EXPS3)
    return firsts


def check_jobs(env: dict, n: int) -> list[dict]:
    js = [j for j in base_jobs(env, (CHECK_TRIAL[0],), n) if j["tid"] == CHECK_TRIAL[1]]
    assert len(js) == len(ARMS)
    return js


# ---- running -----------------------------------------------------------------------------------------------------------
def say(msg: str) -> None:
    print(msg, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "stage3_run_log.txt", "a") as fh:
        fh.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def run_jobs(todo: list[dict], root: Path, n_workers: int, pause_on_trouble: bool) -> dict:
    pending, i, done = [], 0, 0
    stop, pause = None, None
    with mp_.get_context("fork").Pool(n_workers, maxtasksperchild=1) as pool:
        while i < len(todo) or pending:
            while not stop and not pause and i < len(todo) and len(pending) < n_workers:
                pending.append((todo[i], pool.apply_async(worker, (todo[i],))))
                i += 1
            time.sleep(1.0)
            still = []
            for job, res in pending:
                if not res.ready():
                    still.append((job, res))
                    continue
                try:
                    rec = res.get()
                except Exception as e:                       # noqa: BLE001
                    stop = f"worker error in {job['er9g_arm']} {job['exp']}/{job['tid']}: {e!r}"
                    say(stop)
                    continue
                RUN2.write_rec(RUN2.record_path(root, rec["er9_arm"], rec["experiment"], rec["trial_id"]), rec)
                done += 1
                errs = proof_errors(rec)
                tr = RUN2.trouble(rec)
                say(f"[{done}] {rec['er9_arm']} {rec['experiment']}/{rec['trial_id']} n={rec['d14s3']['noslip_n']} "
                    f"{'PASS' if rec['pass'] else 'FAIL'}; wall {rec['d14s3']['worker_wall_s']:.0f} s"
                    + (f"; {'; '.join(rec['fail_reasons'])}" if rec.get("fail_reasons") else "")
                    + (f"; TROUBLE {tr}" if tr else "") + (f"; PROOF ERROR {errs}" if errs else ""))
                if errs:
                    stop = f"harness proof error: {errs}"
                if tr and pause_on_trouble and not pause:
                    pause = f"{rec['er9_arm']} {rec['experiment']}/{rec['trial_id']}: {tr}"
            pending = still
            if stop and not pending:
                break
    return {"done": done, "stop": stop, "pause": pause, "not_started": len(todo) - i}


def code_is_committed() -> bool:
    paths = [str(HERE / f) for f in ("PROTOCOL_STAGE3.md", "d14s3_run.py", "d14s3_analyze.py", "d14s2_run.py")]
    paths.append(str(REPO / "experiments/D13_rest_slip_mechanism/d13_run.py"))
    st = subprocess.run(["git", "status", "--porcelain", "--", *paths], cwd=REPO, capture_output=True, text=True)
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", *paths], cwd=REPO, capture_output=True)
    return st.stdout.strip() == "" and tracked.returncode == 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    if not code_is_committed():
        raise SystemExit("refusing: commit PROTOCOL_STAGE3.md, d14s3_run.py and d14s3_analyze.py first (clean)")
    AN = _load("d14s3_analyze", HERE / "d14s3_analyze.py")
    env = D13.environment()
    t_start = time.time()
    say(f"Stage 3 start: commit {env['commit']}, free {D13.free_gb():.1f} GB")
    n = D13.workers_for(a.jobs)
    # ---- 3a
    if not S3A_FILE.exists():
        with mp_.get_context("fork").Pool(min(n, len(ARMS)), maxtasksperchild=1) as pool:
            comp = pool.map(composite_worker, ARMS)
        todo = [j for j in check_jobs(env, NOSLIP) + check_jobs(env, NOSLIP_CONV)
                if not RUN2.record_path(S3A_DIR / f"n{j['d14s3_n']}", j["er9g_arm"], j["exp"], j["tid"]).exists()]
        for k in (NOSLIP, NOSLIP_CONV):
            sub = [j for j in todo if j["d14s3_n"] == k]
            if sub:
                r = run_jobs(sub, S3A_DIR / f"n{k}", n, pause_on_trouble=False)
                if r["stop"]:
                    say(f"Stage 3 stops in 3a: {r['stop']}")
                    return
        res = AN.stage3a(comp)
        res["environment"] = env
        with open(S3A_FILE, "x") as fh:
            json.dump(res, fh, indent=1, default=float)
    res = json.loads(S3A_FILE.read_text())
    say(f"3a: composite {res['composite_pass']}, Stage 2 reproduction {res['reproduction_pass']}; pass {res['pass']}")
    if not res["pass"]:
        say("Stage 3 stops: 3a failed (PROTOCOL_STAGE3 section 1); the user decides")
        return
    # ---- 3b gate
    all3 = stage3b_jobs(env)
    gj = [j for j in gate3_jobs(all3) if not RUN2.record_path(GATE3, j["er9g_arm"], j["exp"], j["tid"]).exists()]
    if gj:
        say(f"3b gate: {len(gj)} L0 frozen-setting trials")
        r = run_jobs(gj, GATE3, n, pause_on_trouble=False)
        if r["stop"]:
            say(f"Stage 3 stops: {r['stop']}")
            return
    g = AN.gate3()
    (OUT / "stage3_gate.json").write_text(json.dumps(g, indent=1))
    say(f"3b gate: {'PASS' if g['pass'] else 'FAIL'}")
    if not g["pass"]:
        say("Stage 3 stops: the 3b gate failed (PROTOCOL_STAGE3 section 2)")
        return
    # ---- 3b cost check
    rest = [j for j in all3 if not RUN2.record_path(S3, j["er9g_arm"], j["exp"], j["tid"]).exists()]
    if rest and len(rest) < len(all3) and not a.resume:
        raise SystemExit("refusing: Stage 3b records exist; use --resume")
    ratio = AN.arm_wall_ratios()
    n = D13.workers_for(a.jobs)
    work = sum(RUN2.load_rec(RUN2.frozen_path("L0", j["exp"], j["tid"]))["er7_wall_s"] * ratio[j["er9g_arm"]]
               for j in rest)
    projected = (time.time() - t_start) + work / n
    with open(OUT / "stage3_cost_checks.jsonl", "a") as fh:
        fh.write(json.dumps({"remaining": len(rest), "workers": n, "ratio_vs_L0_frozen": ratio,
                             "projected_total_s": projected, "limit_s": COST_STOP_S,
                             "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
    say(f"3b cost check: projected {projected / 3600:.2f} h (limit {COST_STOP_S / 3600:.0f} h), {len(rest)} trials on {n} workers")
    if projected > COST_STOP_S:
        say("Stage 3 stops: projected total exceeds the cost stop (PROTOCOL_STAGE3 section 2)")
        return
    # ---- 3b trials, longest first (E1-4, then by arm cost)
    order_e = {"E1-4": 0, "E1-3": 1, "E1-6t": 2, "E1-6c": 3, "E1-6b": 4, "E1-6a": 5}
    order_a = {"PG20": 0, "PG8": 1, "L0": 2}
    rest.sort(key=lambda j: (order_e[j["sub"]], order_a[j["er9g_arm"]]))
    r = run_jobs(rest, S3, n, pause_on_trouble=True)
    if r["stop"]:
        say(f"Stage 3 stops: {r['stop']}")
        return
    if r["pause"]:
        say(f"Stage 3 PAUSED for the user: {r['pause']}; {r['not_started']} trials not started")
        return
    have = sum(RUN2.record_path(S3, j["er9g_arm"], j["exp"], j["tid"]).exists() for j in all3)
    say(f"Stage 3b trials complete: {have} / {len(all3)}")


if __name__ == "__main__":
    main()
