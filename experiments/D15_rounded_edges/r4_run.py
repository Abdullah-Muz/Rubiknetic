"""D15 R4 runner (P-86 Q3; PROTOCOL_R4.md): fresh-seed unscored rehearsal of M7's Option A battery (L0, rounded edges
R 2.5 mm, NoSlip 10) on seeds 19000-19655 (M5's scored seeds + 9000), before the M7 pre-registration is fixed.

Trials: M5's 204-trial Option A list built by M5's own builder under a +9000 seed mapping (as ER7 used +6000). Turn
trials run through R3's sequence worker (ER7's L0 path: er7_run.run_one -> M5 run_job, with the edge and NoSlip
installs); E1-1 runs as R2/R3's 60 s instrumented rest (R3's rest worker). Gate: the first trial of every sub-experiment,
built under ER7's rehearsal mapping, must reproduce R1/R2's committed L0 R25 record exactly. Writes only under
results/r4/. Usage (WSL, repo root): python experiments/D15_rounded_edges/r4_run.py [--resume]
Smoke (unscored, seeds 16950-16959, results/r4_smoke/, proof checks only): ... r4_run.py --smoke"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r3_run as R3  # noqa: E402

RUN1, RUN2, D13 = R3.RUN1, R3.RUN2, R3.D13
REPO = R3.REPO
OUT = HERE / "results" / "r4"
SMOKE_OUT = HERE / "results" / "r4_smoke"
ARM = "L0"
SHIFT = 9000                                   # M5 scored seed + 9000 (ER7 used + 6000)
SEED_RANGE = (19000, 19999)
FORBIDDEN = ((10000, 10999), (17000, 17999))   # M5's scored range; M7's reserved scored block
SMOKE_SEEDS = tuple(range(16950, 16960))       # unused part of 16900-16999 (R3 smoke used 16901-16945, 16999)
REST_S = 60.0
WORKERS = 6
WALL_STOP_S = 6 * 3600.0
EXPECTED = {"E1-1": 20, "E1-2": 24, "E1-3": 22, "E1-4": 40, "E1-5": 42, "E1-5s": 20, "E1-6a": 6, "E1-6b": 6,
            "E1-6c": 8, "E1-6t": 16}
# R1 holds E1-2 / E1-5 / E1-5s at R25, R2 holds E1-3 / E1-4 / E1-6 / E1-6t (and the 60 s rests)
GATE_SOURCE = {"E1-2": "r1", "E1-5": "r1", "E1-5s": "r1", "E1-3": "r2", "E1-4": "r2", "E1-6a": "r2", "E1-6b": "r2",
               "E1-6c": "r2", "E1-6t": "r2"}


def mods():
    return R3.mods()


def r4_globals(E7) -> dict:
    m5 = E7.M5_GLOBALS
    return {"SEED_SHIFT": m5["SEED_SHIFT"] + SHIFT, "SCORED_SEED_RANGE": SEED_RANGE,
            "SNAP_SEED_BASE": m5["SNAP_SEED_BASE"] + SHIFT, "E16T_SEED_BASE": m5["E16T_SEED_BASE"] + SHIFT}


def option_a(env: dict, globals_: str) -> list[dict]:
    """M5's 204 Option A magnet jobs (no E1-7, no E1-6n) under the named seed mapping ('r4' or 'er7')."""
    _, E7, M4, R = mods()
    E7.set_seeds(r4_globals(E7) if globals_ == "r4" else E7.ER7_GLOBALS)
    js = [j for j in R.build_m5_jobs(env.get("commit"), env, M4.nominal_validated_tilt())
          if j["magnets"] and j["exp"] != "E1-7"]
    E7.set_seeds(E7.ER7_GLOBALS)
    got = {e: sum(j["sub"] == e for j in js) for e in EXPECTED}
    assert got == EXPECTED and len(js) == 204, got
    return js


def check_seed(s: int, smoke: bool = False) -> int:
    for lo, hi in FORBIDDEN:
        if lo <= s <= hi:
            raise SystemExit(f"refusing: seed {s} is in the forbidden block {lo}-{hi}")
    if not smoke and not SEED_RANGE[0] <= s <= SEED_RANGE[1]:
        raise SystemExit(f"refusing: seed {s} outside R4's range {SEED_RANGE}")
    return s


def _seq(j: dict) -> dict:
    return {**copy.deepcopy(j), "er7_arm": "L0", "er7_seeds": True, "reported_only": True, "scored": False,
            "d15_kind": "seq", "d15_setting": j["sub"], "d15_seq": j["kind"], "d15_r": R3.R_NOM, "d15_n": R3.N_NOM,
            "d15_band": False}


def _rest(j: dict, env: dict, rest_s: float = REST_S) -> dict:
    s = j["kw"]["seed"]
    return {"d15_kind": "rest", "d15_setting": "nominal", "d15_ov": {}, "d15_r": R3.R_NOM, "d15_n": R3.N_NOM,
            "seed": s, "base_job": copy.deepcopy(j), "env": env, "tid": j["tid"], "exp": "E1-1", "sub": "E1-1",
            "d15_rest_s": rest_s}


def to_job(j: dict, env: dict) -> dict:
    return _rest(j, env) if j["sub"] == "E1-1" else _seq(j)


def main_jobs(env: dict) -> list[dict]:
    js = [to_job(j, env) for j in option_a(env, "r4")]
    for j in js:
        check_seed(j["seed"] if j["d15_kind"] == "rest" else j["kw"]["seed"])
    order = {"E1-4": 0, "E1-1": 1, "E1-3": 2, "E1-5": 3, "E1-2": 4, "E1-5s": 5, "E1-6t": 6, "E1-6c": 7, "E1-6b": 8,
             "E1-6a": 9}
    js.sort(key=lambda j: order[j["sub"]])
    return js


def gate_jobs(env: dict) -> list[dict]:
    """First trial of each sub-experiment, rehearsal mapping (ER7 +6000), compared with R1/R2's committed records."""
    seen, out = set(), []
    for j in option_a(env, "er7"):
        if j["sub"] in seen:
            continue
        seen.add(j["sub"])
        g = to_job(j, env)
        g["d15_gate"] = True
        out.append(g)
    assert len(out) == len(EXPECTED)
    return out


# ---- proof checks ----------------------------------------------------------------------------------------------------
_R3_PROOF = R3.proof_errors                      # R3's own function (run_batch patches R3.proof_errors with ours)


def proof_errors(job: dict, out: dict) -> list[str]:
    """R3's checks: edge, solver settings, NoSlip, M5's nominal magnets and layout gap, seed (and misalignment for
    sequence trials, rest length for rests)."""
    if job["d15_kind"] == "rest":
        return _R3_PROOF(job, out)
    errs = _R3_PROOF(job, out)
    if job["kind"] != "seq":                     # misalignment of offset/abuse trials is set by the trial itself
        errs = [e for e in errs if not e.startswith("misalignment")]
    return errs


# ---- paths, gate ------------------------------------------------------------------------------------------------------
def job_path(job: dict, root: Path = OUT) -> Path:
    base = root / ("gate" if job.get("d15_gate") else "") / ARM
    if job["d15_kind"] == "rest":
        return base / "E1-1" / f"rest_s{job['seed']}.json.gz"
    return base / job["exp"] / f"{job['tid']}.json.gz"


def ref_path(job: dict) -> Path:
    if job["d15_kind"] == "rest":
        return HERE / "results/r2/R25" / ARM / "E1-1" / f"rest_s{job['seed']}.json.gz"
    src = GATE_SOURCE[job["sub"]]
    return HERE / "results" / src / "R25" / ARM / job["exp"] / f"{job['tid']}.json.gz"


def gate_check(root: Path = OUT) -> dict:
    import gzip
    ER9 = RUN2.er9()
    rows = []
    for g in gate_jobs({"commit": None}):
        mine = json.loads(gzip.decompress(job_path(g, root).read_bytes()))
        ref = json.loads(gzip.decompress(ref_path(g).read_bytes()))
        if g["d15_kind"] == "rest":
            d = ER9.gs_diff(ref["record"], mine["record"])
            d += [f"/{k}" for k in ("seed", "rest_s", "variant", "capture") if mine.get(k) != ref.get(k)]
        else:
            d = ER9.gs_diff(R3._strip(ref), R3._strip(mine))
        rows.append({"sub": g["sub"], "tid": g["tid"], "ref": str(ref_path(g).relative_to(HERE)), "n_diffs": len(d),
                     "diffs": d[:10], "pass": not d})
    return {"pass": all(r["pass"] for r in rows), "trials": rows}


# ---- parent ----------------------------------------------------------------------------------------------------------
def say(msg: str, root: Path = OUT) -> None:
    print(msg, flush=True)
    root.mkdir(parents=True, exist_ok=True)
    with open(root / "r4_run_log.txt", "a") as fh:
        fh.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def run_batch(todo: list[dict], n: int, t_start: float, root: Path) -> dict:
    """R3's batch loop with R4's paths, proof checks and log."""
    keep = (R3.job_path, R3.proof_errors, R3.say, R3.WALL_STOP_S)
    R3.job_path = lambda job, r=root: job_path(job, r)
    R3.proof_errors = proof_errors
    R3.say = lambda msg, r=root: say(msg.replace("PROTOCOL_R3", "PROTOCOL_R4").replace("3 h", "6 h"), r)
    R3.WALL_STOP_S = WALL_STOP_S
    try:
        return R3.run_batch(todo, n, t_start, root)
    finally:
        R3.job_path, R3.proof_errors, R3.say, R3.WALL_STOP_S = keep


def smoke(env: dict) -> None:
    """One short trial per sub-experiment on 16950-16959 (rest 2 s; sequences one move), proof checks only."""
    seen, js = set(), []
    for j in option_a(env, "er7"):
        if j["sub"] in seen:
            continue
        seen.add(j["sub"])
        s = check_seed(SMOKE_SEEDS[len(js)], smoke=True)
        k = copy.deepcopy(j)
        k["kw"]["seed"] = s
        if k["kind"] == "seq":
            k["kw"]["moves"] = "U"
        k["tid"] = f"smoke_{k['sub']}_s{s}"
        job = _rest(k, env, rest_s=R3.SMOKE_REST_S) if k["sub"] == "E1-1" else _seq(k)
        js.append(job)
    r = run_batch(js, WORKERS, time.time(), SMOKE_OUT)
    say(f"R4 SMOKE: {r}", SMOKE_OUT)


def code_is_committed() -> bool:
    paths = [str(HERE / f) for f in ("PROTOCOL_R4.md", "r4_run.py", "r4_analyze.py", "r3_run.py", "r1_run.py")]
    paths += [str(RUN1.EXP14 / f) for f in ("d14s3_run.py", "d14s2_run.py", "d14_run.py", "d14s3_analyze.py")]
    paths += [str(REPO / p) for p in ("src/rubiknetic/cube_physics/m1_model.py", "experiments/D13_rest_slip_mechanism/d13_run.py",
                                      "experiments/E5_scored_m5/run.py", "experiments/E4_scored_m4/run.py",
                                      "experiments/ER7_core_magnet_rehearsal/er7_run.py")]
    st = subprocess.run(["git", "status", "--porcelain", "--", *paths], cwd=REPO, capture_output=True, text=True)
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", *paths], cwd=REPO, capture_output=True)
    return st.stdout.strip() == "" and tracked.returncode == 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=WORKERS)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    env = D13.environment()
    if a.smoke:
        smoke(env)
        return
    if not code_is_committed():
        raise SystemExit("refusing: commit PROTOCOL_R4.md, r4_run.py, r4_analyze.py (and unchanged dependencies) first")
    n = min(a.jobs, D13.workers_for(a.jobs))
    gates, mains = gate_jobs(env), main_jobs(env)
    present = sum(job_path(j).exists() for j in gates + mains)
    if present and not a.resume:
        raise SystemExit("refusing: R4 records exist; use --resume")
    say(f"R4 start: commit {env['commit']}, {present} / {len(gates) + len(mains)} present, {n} workers, "
        f"free {D13.free_gb():.1f} GB")
    if n < a.jobs:
        say(f"R4 not started: only {n} workers possible (PROTOCOL_R4 section 1); free memory first")
        return
    t_start = time.time()
    gtodo = [j for j in gates if not job_path(j).exists()]
    if gtodo:
        r = run_batch(gtodo, min(n, len(gtodo)), t_start, OUT)
        if r["stop"] or r["pause"]:
            say(f"R4 STOPPED in the gate: {r['stop'] or r['pause']}")
            return
    g = gate_check()
    (OUT / "r4_gate.json").write_text(json.dumps(g, indent=1, default=str))
    say(f"R4 gate: {'PASS' if g['pass'] else 'FAIL'} {[(t['sub'], t['n_diffs']) for t in g['trials']]}")
    if not g["pass"]:
        say("R4 stops: the gate failed (PROTOCOL_R4 section 1)")
        return
    todo = [j for j in mains if not job_path(j).exists()]
    r = run_batch(todo, n, t_start, OUT)
    have = sum(job_path(j).exists() for j in mains)
    if r["stop"]:
        say(f"R4 STOPPED: {r['stop']}; {have} / {len(mains)} records")
    elif r["pause"]:
        say(f"R4 PAUSED for the user: {r['pause']}; {have} / {len(mains)} records, {r['not_started']} not started")
    else:
        say(f"R4 trials complete: {have} / {len(mains)}")


if __name__ == "__main__":
    main()
