"""D15 R3 runner (P-84; PROTOCOL_R3.md): E1-7 sensitivity rehearsal of L0 at rounded edges R 2.5 mm, NoSlip 10.

Sequences: M5's E1-7 list (6move and sexy6 per setting) built by M5's own builder under ER7's seed mapping (seed 16000),
with M5's chamfer settings replaced by edge radius 1.8 / 3.6 mm and NoSlip 5 / 20 added (plus NoSlip 0 as a reference
arm). They run through ER7's L0 path (er7_run.run_one -> M5 run_job), the path M5's own E1-7 used: ER9 Part G's L0
installer ignores the magnet settings, so it cannot be used for E1-7 (PROTOCOL_R3 section 2).
Rests: 15 one-seed 60 s rests (D14 Stage 1's steps, as R1/R2's rest worker) under the settings of P-84 D3.
Writes only under results/r3/. Usage (WSL, repo root): python experiments/D15_rounded_edges/r3_run.py [--resume]
Smoke (unscored, seeds 16900-16999, results/r3_smoke/): python ... r3_run.py --smoke"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import multiprocessing as mp_
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r1_run as RUN1  # noqa: E402

S3, RUN2, D13, STAGE1 = RUN1.S3, RUN1.RUN2, RUN1.D13, RUN1.STAGE1
REPO = RUN1.REPO
OUT = HERE / "results" / "r3"
SMOKE_OUT = HERE / "results" / "r3_smoke"
ARM = "L0"
R_NOM, N_NOM = 0.0025, 10
EDGE_BAND = (0.0018, 0.0036)                     # P-84 D1
NOSLIP_BAND = (5, 20)                            # P-84 D2
NOSLIP_REF = 0                                   # P-84 D2: reference arm, reported separately
SEED = 16000                                     # M5's E1-7 seed 10000 + ER7's 6000
SMOKE_SEEDS = (16900, 16999)                     # unused block of ER7's rehearsal range (ER9 refuses seeds outside it)
REST_S = 60.0
SMOKE_REST_S = 2.0
WORKERS = 6
WALL_STOP_S = 3 * 3600.0
GATE_SEQ = ("E1-2", "U_s16100")                  # R1's committed R 2.5 L0 record (ER9 path) vs this runner's path
NOM_SEQ = {"timestep": 0.0005, "iterations": 100, "cubie_friction": (0.2, 0.0025, 0.0005),
           "joint_frictionloss": 0.0005, "gap": 5e-05}
CF = {"0.1": (0.1, 0.0025, 0.0005), "0.5": (0.5, 0.0025, 0.0005), "1.0": (1.0, 0.0025, 0.0005)}
# P-84 D3: one 60 s rest per non-nominal setting of these factors, plus nominal (15)
REST_SETTINGS = ([("nominal", {}, R_NOM, N_NOM)]
                 + [(f"timestep={v}", {"timestep": v}, R_NOM, N_NOM) for v in (0.00025, 0.00075)]
                 + [(f"iterations={v}", {"iterations": v}, R_NOM, N_NOM) for v in (50, 200)]
                 + [(f"cubie_friction={k}-0.0025-0.0005", {"cubie_friction": v}, R_NOM, N_NOM) for k, v in CF.items()]
                 + [(f"edge_radius={r}", {}, r, N_NOM) for r in EDGE_BAND]
                 + [(f"gap={v}", {"gap": v}, R_NOM, N_NOM) for v in (2.5e-05, 0.0001)]
                 + [("magnet_scale=0.67", {"magnet_scale": 0.67}, R_NOM, N_NOM)]
                 + [(f"noslip={n}", {}, R_NOM, n) for n in NOSLIP_BAND])
assert len(REST_SETTINGS) == 15


def mods():
    return RUN2.er9().mods()                     # (er9_probe, er7_run, M4 runner, M5 runner)


# ---- jobs ---------------------------------------------------------------------------------------------------------------
def _seq_job(base: dict, setting: str, seqname: str, r: float, n: int, band: bool) -> dict:
    j = copy.deepcopy(base)
    j.update({"tid": f"{setting}__{seqname}", "er7_arm": "L0", "er7_seeds": True, "reported_only": True,
              "scored": False, "d15_kind": "seq", "d15_setting": setting, "d15_seq": seqname, "d15_r": r,
              "d15_n": n, "d15_band": band})
    return j


def seq_jobs(env: dict) -> list[dict]:
    """60 jobs: M5's 54 E1-7 jobs minus the 4 chamfer jobs, plus edge radius 1.8 / 3.6 mm and NoSlip 5 / 20 / 0 (ref)."""
    _, E7, M4, R = mods()
    E7.set_seeds(E7.ER7_GLOBALS)
    base = [j for j in R.build_m5_jobs(env.get("commit"), env, M4.nominal_validated_tilt()) if j["exp"] == "E1-7"]
    assert len(base) == 54 and {j["kw"]["seed"] for j in base} == {SEED}, (len(base), {j["kw"]["seed"] for j in base})
    out, nominal = [], {}
    for j in base:
        setting, seqname = j["tid"].split("__")
        if setting == "nominal":
            nominal[seqname] = j
        if setting.startswith("chamfer="):
            continue                              # replaced by the edge-radius factor (P-84 D1)
        out.append(_seq_job(j, setting, seqname, R_NOM, N_NOM, True))
    assert set(nominal) == {"6move", "sexy6"}
    for seqname, j in nominal.items():
        for r in EDGE_BAND:
            out.append(_seq_job(j, f"edge_radius={r}", seqname, r, N_NOM, True))
        for n in NOSLIP_BAND:
            out.append(_seq_job(j, f"noslip={n}", seqname, R_NOM, n, True))
        out.append(_seq_job(j, f"noslip_ref={NOSLIP_REF}", seqname, R_NOM, NOSLIP_REF, False))
    assert len(out) == 60 and len({j["tid"] for j in out}) == 60
    return out


def rest_jobs(env: dict) -> list[dict]:
    base = STAGE1.base_jobs()[SEED]
    assert base["sub"] == "E1-1" and base["kw"]["seed"] == SEED
    return [{"d15_kind": "rest", "d15_setting": s, "d15_ov": ov, "d15_r": r, "d15_n": n, "seed": SEED,
             "base_job": base, "env": env, "tid": f"{s}__rest60", "d15_rest_s": REST_S} for s, ov, r, n in REST_SETTINGS]


def split_not_run(jobs: list[dict]) -> tuple[list[dict], dict]:
    """M5's V3 rule (R.classify): 'not run' sequence jobs are recorded with their reason, never run."""
    _, _, _, R = mods()
    run, not_run = [], {}
    for j in jobs:
        if j["d15_kind"] == "seq":
            status, msg, _ = R.classify(j)
            if status == "refused":
                raise SystemExit(f"refused: {j['tid']}: {msg}")
            if status == "not_run":
                not_run[j["tid"]] = msg
                continue
        run.append(j)
    return run, not_run


def all_jobs(env: dict) -> tuple[list[dict], dict]:
    """Nominal rest first (it is the rest gate), then sequences longest first (sexy6), then the other rests."""
    seq, rests = seq_jobs(env), rest_jobs(env)
    run, not_run = split_not_run(seq + rests)
    order = {"rest_nominal": 0, "sexy6": 1, "6move": 2, "rest": 3}
    run.sort(key=lambda j: order["rest_nominal" if j["tid"] == "nominal__rest60" else
                                 j["d15_seq"] if j["d15_kind"] == "seq" else "rest"])
    return run, not_run


def gate_job(env: dict) -> dict:
    """E1-2 U_s16100 for L0 at R 2.5 mm through this runner's sequence path (compared with R1's ER9-path record)."""
    j = [x for x in S3.base_jobs(env, (GATE_SEQ[0],), N_NOM) if x["tid"] == GATE_SEQ[1] and x["er9g_arm"] == ARM][0]
    j = {k: v for k, v in j.items() if not k.startswith(("er9g_", "d14s3_"))}
    return {**j, "er7_arm": "L0", "er7_seeds": True, "d15_kind": "seq", "d15_setting": "gate", "d15_seq": "U",
            "d15_r": R_NOM, "d15_n": N_NOM, "d15_band": False, "d15_gate": True}


# ---- expected values (parent side) and proof checks --------------------------------------------------------------------
def expected(job: dict) -> dict:
    """What the record must show for this job's setting."""
    _, _, _, R = mods()
    if job["d15_kind"] == "seq":
        ov = dict(job["kw"].get("overrides", {}))
    else:
        ov = {**NOM_SEQ, **job["d15_ov"]}
    mp = R.magnet_params_for(dict(ov))
    e = {k: ov.get(k, NOM_SEQ[k]) for k in NOM_SEQ}
    e["cubie_friction"] = list(e["cubie_friction"])
    e.update({"edge_radius": job["d15_r"], "noslip": job["d15_n"],
              "magnet": None if mp is None else {k: getattr(mp, k) for k in ("diameter", "length", "grade", "scale",
                                                                                "wall")}})
    if "grip_force" in ov:
        e["grip_force"] = ov["grip_force"]
    if job["d15_kind"] == "seq":
        e["misalign_max_deg"] = ov.get("misalign_max_deg", 1.0)
    return e


def proof_errors(job: dict, out: dict) -> list[str]:
    e = expected(job)
    errs = []
    rec = out["record"] if job["d15_kind"] == "rest" else out
    p = rec.get("params") or {}
    if p.get("edge_profile") != "rounded" or p.get("edge_radius") != e["edge_radius"]:
        errs.append(f"edge {p.get('edge_profile')!r} {p.get('edge_radius')!r} != {e['edge_radius']}")
    for k in ("timestep", "iterations", "joint_frictionloss", "gap"):
        if p.get(k) != e[k]:
            errs.append(f"params.{k} {p.get(k)!r} != {e[k]!r}")
    if list(p.get("cubie_friction") or []) != e["cubie_friction"]:
        errs.append(f"params.cubie_friction {p.get('cubie_friction')!r} != {e['cubie_friction']!r}")
    if "grip_force" in e and p.get("grip_force") != e["grip_force"]:
        errs.append(f"params.grip_force {p.get('grip_force')!r} != {e['grip_force']!r}")
    opts = (rec.get("compiled_options") if job["d15_kind"] == "rest" else (out.get("d15") or {}).get("trial_options")) or {}
    for k, want in (("noslip_iterations", e["noslip"]), ("timestep", e["timestep"]), ("iterations", e["iterations"])):
        if opts.get(k) != want:
            errs.append(f"compiled {k} {opts.get(k)!r} != {want!r}")
    mag = out.get("magnet_params") if job["d15_kind"] == "rest" else ((rec.get("magnets") or {}).get("params"))
    if e["magnet"] is None:
        if mag is not None:
            errs.append("magnets present in a no-magnet setting")
    else:
        got = None if mag is None else {k: mag.get(k) for k in e["magnet"]}
        if got != e["magnet"]:
            errs.append(f"magnet params {got!r} != {e['magnet']!r}")
        lg = out.get("layout_gap") if job["d15_kind"] == "rest" else (rec.get("magnets") or {}).get("layout_gap")
        if lg != e["gap"]:
            errs.append(f"magnet layout gap {lg!r} != {e['gap']!r}")
    if job["d15_kind"] == "seq":
        d = out.get("d15") or {}
        if d.get("wrapper_calls") != (1 if e["noslip"] else 0):
            errs.append(f"noslip wrapper calls {d.get('wrapper_calls')}")
        if d.get("n_trials_constructed") != 1:
            errs.append(f"trials constructed {d.get('n_trials_constructed')}")
        if rec.get("seed") != job["kw"]["seed"]:
            errs.append(f"seed {rec.get('seed')} != {job['kw']['seed']}")
        mis = ((rec.get("setup") or {}).get("misalign_deg") or {}).values()
        if any(abs(x) > e["misalign_max_deg"] + 1e-12 for x in mis) or (e["misalign_max_deg"] == 0 and any(mis)):
            errs.append(f"misalignment outside max {e['misalign_max_deg']}")
    else:
        if out.get("rest_s") != job["d15_rest_s"]:
            errs.append(f"rest length {out.get('rest_s')}")
        if rec.get("seed") != job["seed"]:
            errs.append(f"rest seed {rec.get('seed')}")
    return errs


def harness_trouble(job: dict, out: dict) -> str | None:
    """Pause rule (PROTOCOL_R3 section 1): only a harness exception pauses; an abort or numerical failure under a
    setting is an E1-7 outcome (a possible fragility), not a pause."""
    rec = out["record"] if job["d15_kind"] == "rest" else out
    return "harness exception" if rec.get("harness_exception") else None


# ---- workers (fresh process each) ----------------------------------------------------------------------------------------
def seq_worker(job: dict) -> dict:
    from rubiknetic.cube_physics import scored
    _, E7, M4, _ = mods()
    RUN1.install_edge(scored, job["d15_r"])
    n = int(job["d15_n"])
    calls = [0]
    if n:
        orig = scored.build_m1_xml

        def wrapped(p):
            calls[0] += 1
            return D13.with_noslip(orig(p), n)
        scored.build_m1_xml = wrapped
    log: dict = {}
    RUN2.install_logged_trial(scored, "none", log)
    t0 = time.perf_counter()
    rec = E7.run_one({k: v for k, v in job.items() if not k.startswith("d15_")})
    ms = M4._MS
    rec["d15"] = {"run": "R3", "setting": job["d15_setting"], "seq": job["d15_seq"], "edge_radius": job["d15_r"],
                  "noslip_n": n, "band": job["d15_band"], "wrapper_calls": calls[0],
                  "n_trials_constructed": log.get("n_trials", 0), "trial_options": log.get("options"),
                  "solver": log.get("solver"),
                  "magnet_model_noslip_iterations": int(ms.m.opt.noslip_iterations) if ms is not None else None,
                  "worker_wall_s": time.perf_counter() - t0}
    return rec


def rest_worker(job: dict) -> dict:
    """R1/R2's rest steps (warm-up E1-1 through ER7's L0 path, magnet-system reset, d13_rest with D13 variant V2) with
    this setting's overrides, edge radius and NoSlip count."""
    from dataclasses import asdict
    _, E7, M4, R = mods()
    D10 = sys.modules["d10_rest"]
    from rubiknetic.cube_physics import scored
    seed, r, n = job["seed"], job["d15_r"], int(job["d15_n"])
    RUN1.install_edge(scored, r)
    t0 = time.perf_counter()
    base = copy.deepcopy(job["base_job"])
    base["kw"]["seed"] = seed
    base["kw"]["overrides"] = {**base["kw"].get("overrides", {}), **job["d15_ov"]}
    ov = dict(base["kw"]["overrides"])
    warm = E7.run_one({**base, "er7_arm": "L0", "rest60": False})
    ov2 = dict(ov)
    mp = R.magnet_params_for(ov2)                 # pops the magnet keys; ov2 keeps M1Params overrides
    gap = ov.get("gap", R.GAP)
    ms = M4.use_magnets(mp, gap)
    ms.reset_neighbour_list()
    ms.reset_stats()
    M4.MagnetMonitor.last = None
    cfg = {"noslip_iterations": n, "params": ov2} if n else {"params": ov2}
    rec, cap = D13.d13_rest(scored, D10, seed, ms, cfg, duration_s=job["d15_rest_s"])
    rec["magnet_stats"] = dict(ms.stats)
    return {"run": "R3", "arm": ARM, "seed": seed, "setting": job["d15_setting"], "edge_radius": r, "noslip_n": n,
            "rest_s": job["d15_rest_s"], "variant": STAGE1.VARIANT, "cfg": cfg,
            "magnet_params": None if mp is None else asdict(mp), "layout_gap": M4._MS_KEY[1] if mp is not None else None,
            "warmup_10s": {k: warm.get(k) for k in ("rest_rotation_deg", "pass", "fail_reasons", "seed")},
            "record": rec, "wall_s": time.perf_counter() - t0, "environment": job["env"],
            "capture": None if cap is None else {**cap["info"], "n_pre": cap["n_pre"], "n_post": cap["n_post"]}}


def worker(job: dict) -> dict:
    return rest_worker(job) if job["d15_kind"] == "rest" else seq_worker(job)


# ---- paths, logging -------------------------------------------------------------------------------------------------------
def job_path(job: dict, root: Path = OUT) -> Path:
    if job.get("d15_gate"):
        return root / "gate" / ARM / GATE_SEQ[0] / f"{GATE_SEQ[1]}.json.gz"
    return root / ("rests" if job["d15_kind"] == "rest" else "E1-7") / f"{job['tid']}.json.gz"


def say(msg: str, root: Path = OUT) -> None:
    print(msg, flush=True)
    root.mkdir(parents=True, exist_ok=True)
    with open(root / "r3_run_log.txt", "a") as fh:
        fh.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def summary(job: dict, out: dict) -> str:
    if job["d15_kind"] == "rest":
        rec = out["record"]
        return (f"rest 0-10 s {rec.get('rest_rotation_deg', float('nan')):.6f} deg; "
                f"{'EVENT' if out['capture'] else 'no event'}; wall {out['wall_s']:.0f} s")
    pm = out.get("per_move") or []
    peak = max((m.get("max_turner_torque_Nm") or 0.0 for m in pm), default=0.0)
    return (f"{'PASS' if out.get('pass') else 'FAIL'} peak {peak:.3f} N.m; wall {out['d15']['worker_wall_s']:.0f} s"
            + (f"; {'; '.join(out['fail_reasons'])}" if out.get("fail_reasons") else ""))


def run_batch(todo: list[dict], n: int, t_start: float, root: Path) -> dict:
    pending, i, done = [], 0, 0
    stop = pause = None
    with mp_.get_context("fork").Pool(n, maxtasksperchild=1) as pool:
        while i < len(todo) or pending:
            while (not stop and not pause and i < len(todo) and len(pending) < n
                   and time.time() - t_start < WALL_STOP_S):
                pending.append((todo[i], pool.apply_async(worker, (todo[i],))))
                i += 1
            if i < len(todo) and not pending and time.time() - t_start >= WALL_STOP_S and not stop:
                stop = "wall-clock stop: 3 h since start (PROTOCOL_R3 section 1)"
                say(stop, root)
            time.sleep(1.0)
            still = []
            for job, res in pending:
                if not res.ready():
                    still.append((job, res))
                    continue
                try:
                    out = res.get()
                except Exception as e:                       # noqa: BLE001
                    stop = f"worker error in {job['tid']}: {e!r}"
                    say(stop, root)
                    continue
                RUN1.write_new(job_path(job, root), out)
                done += 1
                errs, tr = proof_errors(job, out), harness_trouble(job, out)
                say(f"[{done}] {'GATE ' if job.get('d15_gate') else ''}{job['tid']} {summary(job, out)}"
                    + (f"; TROUBLE {tr}" if tr else "") + (f"; PROOF ERROR {errs}" if errs else ""), root)
                if errs:
                    stop = f"proof error in {job['tid']}: {errs}"
                if tr and not pause:
                    pause = f"{job['tid']}: {tr}"
            pending = still
            if stop and not pending:
                break
    return {"done": done, "stop": stop, "pause": pause, "not_started": len(todo) - i}


# ---- gates ---------------------------------------------------------------------------------------------------------------
def _strip(r: dict) -> dict:
    AN3 = RUN1._load("d14s3_analyze", RUN1.EXP14 / "d14s3_analyze.py")
    return {k: v for k, v in AN3.strip(r).items() if k not in ("d15", "d14s3")}


def gate_seq_check(root: Path = OUT) -> dict:
    """Gate 1: this runner's E1-2 U_s16100 record equals R1's committed R 2.5 L0 record (ER9 path)."""
    ER9 = RUN2.er9()
    g = RUN2.load_rec(job_path({"d15_gate": True}, root))
    ref = RUN2.load_rec(RUN1.seq_path("R25", ARM, *GATE_SEQ))
    d = ER9.gs_diff(_strip(ref), _strip(g))
    return {"n_diffs": len(d), "diffs": d[:20], "pass": not d}


def gate_rest_check(root: Path = OUT) -> dict:
    """Gate 2: the nominal 60 s rest equals R2's committed L0 rest_s16000 (record block; timing fields excluded)."""
    import gzip
    mine = json.loads(gzip.decompress(job_path({"d15_kind": "rest", "tid": "nominal__rest60"}, root).read_bytes()))
    ref = json.loads(gzip.decompress((HERE / "results/r2/R25/L0/E1-1/rest_s16000.json.gz").read_bytes()))
    ER9 = RUN2.er9()
    d = ER9.gs_diff(ref["record"], mine["record"])
    same = {k: mine.get(k) == ref.get(k) for k in ("seed", "rest_s", "variant", "capture")}
    return {"n_diffs": len(d), "diffs": d[:20], "fields_equal": same, "pass": not d and all(same.values())}


# ---- smoke (unscored; seeds 16900-16999; results/r3_smoke/) -----------------------------------------------------------
def smoke_jobs(env: dict) -> list[dict]:
    """One short trial (move 'U') per sequence setting, one 2 s rest per rest setting, and the path-equivalence pair."""
    out, s = [], SMOKE_SEEDS[0]
    seen = set()
    for j in seq_jobs(env):
        if j["d15_setting"] in seen:
            continue
        seen.add(j["d15_setting"])
        s += 1
        k = copy.deepcopy(j)
        k["kw"]["moves"], k["kw"]["seed"] = "U", s
        k["tid"], k["d15_seq"] = f"{j['d15_setting']}__U_s{s}", "U"
        out.append(k)
    for r in rest_jobs(env):
        s += 1
        out.append({**r, "seed": s, "tid": f"{r['d15_setting']}__rest2_s{s}", "d15_rest_s": SMOKE_REST_S})
    assert s <= SMOKE_SEEDS[1]
    return out


def equivalence_pair(env: dict) -> tuple[dict, dict]:
    """The same short trial (E1-2 'U' at seed 16999) through R1's ER9 path and through this runner's ER7 path."""
    j = [x for x in S3.base_jobs(env, ("E1-2",), N_NOM) if x["tid"] == GATE_SEQ[1] and x["er9g_arm"] == ARM][0]
    j = copy.deepcopy(j)
    j["kw"]["seed"], j["tid"] = SMOKE_SEEDS[1], f"U_s{SMOKE_SEEDS[1]}"
    er9 = {**j, "d15_kind": "seq", "d15_tag": "R25", "d15_r": R_NOM}
    mine = {**{k: v for k, v in j.items() if not k.startswith(("er9g_", "d14s3_"))}, "er7_arm": "L0", "er7_seeds": True,
            "d15_kind": "seq", "d15_setting": "equiv", "d15_seq": "U", "d15_r": R_NOM, "d15_n": N_NOM, "d15_band": False}
    return er9, mine


def _equiv_er9(job: dict) -> dict:
    return RUN1.seq_worker(job)


def _as_saved(rec: dict) -> dict:
    """The record as it is on disk (RUN1.dump, then load): tuples become lists, as in every committed record."""
    import gzip
    return json.loads(gzip.decompress(RUN1.dump(rec)))


def run_equivalence(env: dict) -> dict:
    er9, mine = equivalence_pair(env)
    with mp_.get_context("fork").Pool(2, maxtasksperchild=1) as pool:
        a, b = pool.apply_async(_equiv_er9, (er9,)), pool.apply_async(seq_worker, (mine,))
        ra, rb = a.get(), b.get()
    d = RUN2.er9().gs_diff(_strip(_as_saved(ra)), _strip(_as_saved(rb)))
    out = {"seed": SMOKE_SEEDS[1], "n_diffs": len(d), "diffs": d[:40], "pass": not d}
    (SMOKE_OUT / "equivalence.json").write_text(json.dumps(out, indent=1, default=str))
    say(f"R3 SMOKE path equivalence (seed {SMOKE_SEEDS[1]}): {'PASS' if not d else 'FAIL'} {len(d)} diffs {d[:5]}",
        SMOKE_OUT)
    return out


def run_smoke(env: dict) -> None:
    SMOKE_OUT.mkdir(parents=True, exist_ok=True)
    jobs = smoke_jobs(env)
    run, not_run = split_not_run(jobs)
    say(f"R3 SMOKE start: {len(run)} jobs, {len(not_run)} not run {not_run}", SMOKE_OUT)
    r = run_batch(run, WORKERS, time.time(), SMOKE_OUT)
    say(f"R3 SMOKE trials: {r}", SMOKE_OUT)
    run_equivalence(env)


# ---- parent -------------------------------------------------------------------------------------------------------------------
def code_is_committed() -> bool:
    paths = [str(HERE / f) for f in ("PROTOCOL_R3.md", "r3_run.py", "r3_analyze.py", "r1_run.py", "r3_static.json")]
    paths += [str(RUN1.EXP14 / f) for f in ("d14s3_run.py", "d14s2_run.py", "d14_run.py", "d14s3_analyze.py")]
    paths += [str(REPO / "src/rubiknetic/cube_physics/m1_model.py"),
              str(REPO / "experiments/D13_rest_slip_mechanism/d13_run.py"),
              str(REPO / "experiments/E5_scored_m5/run.py"), str(REPO / "experiments/E4_scored_m4/run.py"),
              str(REPO / "experiments/ER7_core_magnet_rehearsal/er7_run.py")]
    st = subprocess.run(["git", "status", "--porcelain", "--", *paths], cwd=REPO, capture_output=True, text=True)
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", *paths], cwd=REPO, capture_output=True)
    return st.stdout.strip() == "" and tracked.returncode == 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=WORKERS)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--smoke-equivalence", action="store_true", help="rerun only the smoke path-equivalence pair")
    a = ap.parse_args()
    env = D13.environment()
    if a.smoke:
        run_smoke(env)
        return
    if a.smoke_equivalence:
        run_equivalence(env)
        return
    if not code_is_committed():
        raise SystemExit("refusing: commit PROTOCOL_R3.md, r3_run.py, r3_analyze.py (and unchanged dependencies) first")
    n = min(a.jobs, D13.workers_for(a.jobs))
    gate = gate_job(env)
    run, not_run = all_jobs(env)
    present = sum(job_path(j).exists() for j in [gate] + run)
    if present and not a.resume:
        raise SystemExit("refusing: R3 records exist; use --resume")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "not_run.json").write_text(json.dumps(not_run, indent=1))
    say(f"R3 start: commit {env['commit']}, {present} / {1 + len(run)} present, {len(not_run)} not run (V3), "
        f"{n} workers, free {D13.free_gb():.1f} GB")
    if n < a.jobs:
        say(f"R3 not started: only {n} workers possible (PROTOCOL_R3 section 1); free memory first")
        return
    t_start = time.time()
    if not job_path(gate).exists():
        r = run_batch([gate], 1, t_start, OUT)
        if r["stop"] or r["pause"]:
            say(f"R3 STOPPED in gate 1: {r['stop'] or r['pause']}")
            return
    g1 = gate_seq_check()
    (OUT / "r3_gate1.json").write_text(json.dumps(g1, indent=1, default=str))
    say(f"R3 gate 1 (sequence path vs R1): {'PASS' if g1['pass'] else 'FAIL'} {g1['n_diffs']} diffs")
    if not g1["pass"]:
        say("R3 stops: gate 1 failed (PROTOCOL_R3 section 1)")
        return
    nom = [j for j in run if j["tid"] == "nominal__rest60"]
    if not job_path(nom[0]).exists():
        r = run_batch(nom, 1, t_start, OUT)
        if r["stop"] or r["pause"]:
            say(f"R3 STOPPED in gate 2: {r['stop'] or r['pause']}")
            return
    g2 = gate_rest_check()
    (OUT / "r3_gate2.json").write_text(json.dumps(g2, indent=1, default=str))
    say(f"R3 gate 2 (nominal rest vs R2 rest_s16000): {'PASS' if g2['pass'] else 'FAIL'} {g2['n_diffs']} diffs")
    if not g2["pass"]:
        say("R3 stops: gate 2 failed (PROTOCOL_R3 section 1)")
        return
    todo = [j for j in run if not job_path(j).exists()]
    r = run_batch(todo, n, t_start, OUT)
    have = sum(job_path(j).exists() for j in run)
    if r["stop"]:
        say(f"R3 STOPPED: {r['stop']}; {have} / {len(run)} records")
    elif r["pause"]:
        say(f"R3 PAUSED for the user: {r['pause']}; {have} / {len(run)} records, {r['not_started']} not started")
    else:
        say(f"R3 trials complete: {have} / {len(run)} (+ {len(not_run)} not run, V3)")


if __name__ == "__main__":
    main()
