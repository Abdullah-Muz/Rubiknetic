"""D14 — Stage 1: 60 s rest rehearsal at noslip_iterations 10 (PROTOCOL.md, committed before this script ran).

Arms L0, PG8, PG20 x seeds 16000-16019 (60 runs). Each run is D13's variant V2 path, unchanged: the committed
experiments/D13_rest_slip_mechanism/d13_run.py provides the instrumented rest (d13_rest), the contact logging and the
event capture; this script only defines the runs, the gate batch (runs that repeat a D13 V2 case, compared exactly)
and the cost stop.

Writes only to experiments/D14_noslip_rest_rehearsal/results/ (exclusive create; --resume skips existing runs).
Usage (WSL, repo root): ~/.venvs/rubiknetic/bin/python experiments/D14_noslip_rest_rehearsal/d14_run.py [--jobs 4] [--resume]
"""
from __future__ import annotations

import argparse
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
OUT = HERE / "results"


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


D13 = _load("d13_run", REPO / "experiments/D13_rest_slip_mechanism/d13_run.py")
ARMS = ("L0", "PG8", "PG20")
SEEDS = tuple(range(16000, 16020))
VARIANT = "V2"                                   # D13's variant: noslip_iterations 10, applied to the 60 s rest only
CFG = D13.VARIANTS[VARIANT]
assert CFG == {"noslip_iterations": 10}
GATE = {("PG8", 16000): "Q1", ("PG8", 16003): "C1", ("PG8", 16011): "C2", ("PG8", 16016): "C3",
        ("PG20", 16000): "Q2", ("PG20", 16013): "C4", ("L0", 16003): "C5", ("L0", 16005): "C6"}
COST_STOP_S = 6 * 3600.0


def run_id(arm: str, seed: int) -> str:
    return f"{arm}_s{seed}"


def result_path(arm: str, seed: int) -> Path:
    return OUT / f"{run_id(arm, seed)}.json.gz"


def capture_path(arm: str, seed: int) -> Path:
    return OUT / f"capture_{run_id(arm, seed)}.npz"


def all_runs() -> list[tuple[str, int]]:
    return [(a, s) for a in ARMS for s in SEEDS]


def committed_frozen_path(arm: str, seed: int) -> Path:
    d = (REPO / "experiments/ER9_anchored_core_layouts/results/hybrid_g/probe" / arm / "E1-1" if arm != "L0"
         else REPO / "experiments/ER7_core_magnet_rehearsal/results/L0/E1-1")
    hits = sorted(d.glob(f"rest_s{seed}.json*"))
    assert len(hits) == 1, (arm, seed, hits)
    return hits[0]


# ---- worker: D13.run_job's steps for one (arm, seed), with D14's file names ---------------------------------------
def run_job(job: dict) -> dict:
    arm, seed, base_job = job["arm"], job["seed"], job["base_job"]
    assert arm in ARMS and seed in SEEDS and base_job["kw"]["seed"] == seed and base_job["sub"] == "E1-1"
    E9 = D13.E9
    LY = D13._load("er9g_layouts", E9 / "er9g_layouts.py")
    P = LY.probe_module()
    E7, M4, R = P.E7, P.M4, P.R
    D10 = sys.modules["d10_rest"]
    from rubiknetic.cube_physics import scored
    from rubiknetic.cube_physics.m1_model import M1Params
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
    rec, cap = D13.d13_rest(scored, D10, seed, ms, CFG)
    rec["magnet_stats"] = dict(ms.stats)
    if acc is not None:
        rec["class_stats"] = acc.as_dict(dict(ms.stats))
    out = {"arm": arm, "seed": seed, "variant": VARIANT, "cfg": CFG, "d_val_deg": job["d_val"],
           "warmup_10s": {k: warm.get(k) for k in ("rest_rotation_deg", "pass", "fail_reasons", "seed")},
           "record": rec, "wall_s": time.perf_counter() - t0, "environment": job["env"],
           "capture": None if cap is None else {**cap["info"], "file": capture_path(arm, seed).name,
                                                "n_pre": cap["n_pre"], "n_post": cap["n_post"]}}
    if cap is not None:
        with open(capture_path(arm, seed), "xb") as fh:
            fh.write(D13.capture_npz(cap))
    body = gzip.compress(json.dumps(out, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x)).encode(),
                         9, mtime=0)
    with open(result_path(arm, seed), "xb") as fh:
        fh.write(body)
    return {"arm": arm, "seed": seed, "wall_s": out["wall_s"], "rest10": rec["rest_rotation_deg"],
            "event": out["capture"], "aborted": rec.get("aborted")}


# ---- parent ----------------------------------------------------------------------------------------------------------
def code_is_committed() -> bool:
    paths = [str(HERE / f) for f in ("PROTOCOL.md", "d14_run.py", "d14_analyze.py")]
    paths.append(str(REPO / "experiments/D13_rest_slip_mechanism/d13_run.py"))
    st = subprocess.run(["git", "status", "--porcelain", "--", *paths], cwd=REPO, capture_output=True, text=True)
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", *paths], cwd=REPO, capture_output=True)
    return st.stdout.strip() == "" and tracked.returncode == 0


def base_jobs() -> dict:
    LY = D13._load("er9g_layouts", D13.E9 / "er9g_layouts.py")
    jobs = LY.probe_module().E7.er7_jobs()
    out = {}
    for s in SEEDS:
        hits = [j for j in jobs if j["sub"] == "E1-1" and j["kw"]["seed"] == s]
        assert len(hits) == 1, (s, len(hits))
        out[s] = hits[0]
    return out


def say(msg: str) -> None:
    print(msg, flush=True)
    with open(OUT / "run_log.txt", "a") as fh:
        fh.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def run_batch(runs: list, env: dict, bases: dict, d_vals: dict, n_workers: int) -> None:
    todo = [{"arm": a, "seed": s, "base_job": bases[s], "env": env, "d_val": d_vals.get(a)} for a, s in runs]
    todo.sort(key=lambda j: {"PG20": 0, "PG8": 1, "L0": 2}[j["arm"]])        # longest first
    with mp_.get_context("fork").Pool(n_workers, maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(run_job, todo):
            ev = r["event"]
            say(f"{r['arm']} s{r['seed']}: rest 0-10 s {r['rest10']:.6f} deg; "
                + (f"EVENT {ev['piece']}/{ev['axis']} {ev['size_deg']:.3f} deg (sim time {ev['window_start_s']:.2f} s)"
                   if ev else "no event") + f"; wall {r['wall_s']:.0f} s"
                + (f"; ABORTED {r['aborted']}" if r["aborted"] else ""))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    AN = _load("d14_analyze", HERE / "d14_analyze.py")
    if not code_is_committed():
        raise SystemExit("refusing: commit PROTOCOL.md, d14_run.py and d14_analyze.py first (clean)")
    OUT.mkdir(parents=True, exist_ok=True)
    env = D13.environment()
    if not (OUT / "environment.json").exists():
        (OUT / "environment.json").write_text(json.dumps(env, indent=1))
    d_vals = {arm: float(D13.load_json(committed_frozen_path(arm, 16000))["er9"]["D_val_deg"]) for arm in ("PG8", "PG20")}
    bases = base_jobs()
    done = {r for r in all_runs() if result_path(*r).exists()}
    if done and not a.resume:
        raise SystemExit(f"refusing: {len(done)} results exist; use --resume")
    say(f"D14 start: commit {env['commit']}, {len(done)} runs present, free {D13.free_gb():.1f} GB")
    gate_runs = [r for r in GATE if r not in done]
    t_gate = time.time()
    if gate_runs:
        n = D13.workers_for(a.jobs)
        say(f"gate batch: {len(gate_runs)} runs on {n} workers")
        run_batch(gate_runs, env, bases, d_vals, n)
    g = AN.gate()
    (OUT / "gate.json").write_text(json.dumps(g, indent=1))
    say(f"gate (D13 V2 reproduction): {'PASS' if g['pass'] else 'FAIL'}")
    if not g["pass"]:
        say("D14 stops: the gate failed (PROTOCOL section 4)")
        return
    walls = {}
    for (arm, seed) in GATE:
        walls.setdefault(arm, []).append(D13.load_json(result_path(arm, seed))["wall_s"])
    mean = {arm: sum(v) / len(v) for arm, v in walls.items()}
    rest = [r for r in all_runs() if r not in GATE and r not in done]
    n = D13.workers_for(a.jobs)
    gate_elapsed = (time.time() - t_gate) if gate_runs else 0.0
    projected = gate_elapsed + sum(mean[arm] for arm, _ in rest) / n
    cost = {"mean_wall_s": mean, "remaining_runs": len(rest), "workers": n, "gate_batch_elapsed_s": gate_elapsed,
            "projected_total_s": projected, "limit_s": COST_STOP_S, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(OUT / "cost_checks.jsonl", "a") as fh:
        fh.write(json.dumps(cost) + "\n")
    say(f"cost check: projected {projected / 3600:.2f} h (limit {COST_STOP_S / 3600:.0f} h), {len(rest)} runs left on {n} workers")
    if projected > COST_STOP_S:
        say("D14 stops: projected total exceeds the cost stop (PROTOCOL section 3)")
        return
    if rest:
        run_batch(rest, env, bases, d_vals, n)
    say(f"D14 runs complete: {sum(result_path(*r).exists() for r in all_runs())} / {len(all_runs())}")


if __name__ == "__main__":
    main()
