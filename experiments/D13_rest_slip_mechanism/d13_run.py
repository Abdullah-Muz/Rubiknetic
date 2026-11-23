"""D13 — unscored diagnostic of the rest slip events (PROTOCOL.md, committed before this script ran).

Cases C1-C6 (the six committed slip events) and Q1-Q2 (quiet seeds); variants V0 (frozen), V1 (impratio 100),
V2 (noslip_iterations 10), V3 (timestep 0.25 ms), G1 (gravity 0), G2 (gravity flipped), S1 (setup misalignment in
reverse face order). Each run is a fresh worker process that repeats the committed trial's path (arm installation,
ER7's 10 s warm-up rest trial at frozen settings, ER7's 60 s rest set-up) and then runs D13's instrumented 60 s rest
with the variant applied. V0 runs first; the reproduction gate (d13_analyze.gate) and the cost stop are checked
before the other variants.

Writes only to experiments/D13_rest_slip_mechanism/results/ (exclusive create; --resume skips existing runs).
Usage (WSL, repo root):
  ~/.venvs/rubiknetic/bin/python experiments/D13_rest_slip_mechanism/d13_run.py [--jobs 6] [--resume]
  ~/.venvs/rubiknetic/bin/python experiments/D13_rest_slip_mechanism/d13_run.py smoke OUTDIR   (code smoke, 1 s)
"""
from __future__ import annotations

import argparse
import collections
import gzip
import importlib.util
import io
import json
import multiprocessing as mp_
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "results"
E9 = REPO / "experiments/ER9_anchored_core_layouts"
ER7_RESULTS = REPO / "experiments/ER7_core_magnet_rehearsal/results"

SAMPLE_S = 0.025                 # the committed sampling (every 50 steps at 0.5 ms)
CAPTURE_S = 0.0025               # event-capture and creep/sliding accumulation interval (divides 25 ms at 0.5 and 0.25 ms)
CAPTURE_PRE_S, CAPTURE_POST_S = 1.0, 0.5
WIN, THR = 8, 0.2                # D11: 200 ms window, 0.2 deg
CONE_SLIDING = 0.95              # cone use at or above which contact slip counts as sliding
DURATION_S = 60.0
COST_STOP_S = 4 * 3600.0
MIN_FREE_GB = 2.0
WORKER_GB = 0.5                  # assumed peak per worker (the probe's E1-1 workers peaked at about 0.17 GB)

CASES = {                        # case: (arm, seed, kind)
    "C1": ("PG8", 16003, "slip"), "C2": ("PG8", 16011, "slip"), "C3": ("PG8", 16016, "slip"),
    "C4": ("PG20", 16013, "slip"), "C5": ("L0", 16003, "slip"), "C6": ("L0", 16005, "slip"),
    "Q1": ("PG8", 16000, "quiet"), "Q2": ("PG20", 16000, "quiet"),
}
SLIP = tuple(c for c, v in CASES.items() if v[2] == "slip")
VARIANTS = {
    "V0": {},
    "V1": {"params": {"impratio": 100.0}},
    "V2": {"noslip_iterations": 10},
    "V3": {"params": {"timestep": 0.00025}},
    "G1": {"params": {"gravity_z": 0.0}},
    "G2": {"params": {"gravity_z": 9.81}},
    "S1": {"reverse_setup": True},
}
CASES_FOR = {"V0": tuple(CASES), "V1": tuple(CASES), "V2": tuple(CASES), "V3": tuple(CASES),
             "G1": SLIP, "G2": SLIP, "S1": SLIP}
COST_FACTOR = {"V2": 2.0, "V3": 2.0}          # PROTOCOL section 3 (assumption); others 1
ALLOWED_SEEDS = frozenset(v[1] for v in CASES.values())
GRADE = "N52"


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def committed_path(case: str) -> Path:
    arm, seed, _ = CASES[case]
    d = E9 / "results/hybrid_g/probe" / arm / "E1-1" if arm in ("PG8", "PG20") else ER7_RESULTS / "L0/E1-1"
    hits = sorted(d.glob(f"rest_s{seed}.json*"))
    assert len(hits) == 1, (case, hits)
    return hits[0]


def load_json(p: Path) -> dict:
    return json.loads(gzip.decompress(p.read_bytes())) if p.suffix == ".gz" else json.loads(p.read_text())


def result_path(variant: str, case: str) -> Path:
    return OUT / f"{variant}_{case}.json.gz"


def capture_path(variant: str, case: str) -> Path:
    return OUT / f"capture_{variant}_{case}.npz"


def all_runs() -> list[tuple[str, str]]:
    return [(v, c) for v in VARIANTS for c in CASES_FOR[v]]


def with_noslip(xml: str, n: int) -> str:
    """The trial XML with noslip_iterations set on its <option> element (exactly one)."""
    assert xml.count("<option ") == 1 and "noslip_iterations" not in xml
    return xml.replace("<option ", f'<option noslip_iterations="{int(n)}" ', 1)


# ---- contact reading (read-only) -------------------------------------------------------------------------------------
def contacts(m, d) -> dict:
    """Contact-frame force and velocity of every active contact, from efc_force / efc_vel (elliptic cones: rows are
    normal, tangent 1, tangent 2). Frictionless contacts (dim 1) get zero tangential entries."""
    n = int(d.ncon)
    c = d.contact
    g1 = np.array(c.geom1[:n], dtype=np.int32)
    g2 = np.array(c.geom2[:n], dtype=np.int32)
    dist = np.array(c.dist[:n], dtype=float)
    adr = np.array(c.efc_address[:n], dtype=int)
    dim = np.array(c.dim[:n], dtype=int)
    mu = np.array(c.friction[:n, 0], dtype=float)
    f = np.zeros((n, 3))
    v = np.zeros((n, 3))
    ok = adr >= 0
    one = ok & (dim == 1)
    many = ok & (dim >= 3)
    f[one, 0] = d.efc_force[adr[one]]
    v[one, 0] = d.efc_vel[adr[one]]
    if many.any():
        rows = adr[many][:, None] + np.arange(3)
        f[many] = d.efc_force[rows]
        v[many] = d.efc_vel[rows]
    return {"g1": g1, "g2": g2, "dist": dist, "f": f, "v": v, "mu": mu, "active": ok}


def check_contacts_against_mujoco(m, d, c: dict) -> float:
    """Largest difference between contacts()' forces and mj_contactForce (must be 0 for elliptic cones)."""
    import mujoco
    out = np.zeros(6)
    worst = 0.0
    for i in range(int(d.ncon)):
        if not c["active"][i]:
            continue
        mujoco.mj_contactForce(m, d, i, out)
        worst = max(worst, float(np.abs(out[:3] - c["f"][i]).max()))
    return worst


def cone_use(c: dict) -> np.ndarray:
    fn = c["f"][:, 0]
    ft = np.hypot(c["f"][:, 1], c["f"][:, 2])
    with np.errstate(divide="ignore", invalid="ignore"):
        u = np.where((fn > 0) & (c["mu"] > 0), ft / (c["mu"] * fn), 0.0)
    return u


# ---- the instrumented 60 s rest ----------------------------------------------------------------------------------------
def d13_rest(scored, D10, seed: int, ms, cfg: dict, duration_s: float | None = None) -> tuple[dict, dict | None]:
    """d10_rest.instrumented_rest (same trial, loop, metric and logging) with the variant cfg applied to this trial
    only, plus D13's per-piece contact logging and event capture. Returns (record, capture or None)."""
    import mujoco
    from rubiknetic.cube_logic import SOLVED
    from rubiknetic.cube_physics.rig import EditAuditError, NumericalFailure
    duration_s = DURATION_S if duration_s is None else duration_s
    FACES = scored.FACES
    setup = scored.draw_setup(seed)
    if cfg.get("reverse_setup"):
        setup = scored.TrialSetup(setup.seed, dict(reversed(list(setup.misalign_deg.items()))), setup.grip_force,
                                  setup.turn_s_per_quarter)
    orig_xml = scored.build_m1_xml
    if cfg.get("noslip_iterations"):
        scored.build_m1_xml = lambda p: with_noslip(orig_xml(p), cfg["noslip_iterations"])
    try:
        tr = scored.Trial(scored.params_for(setup, **cfg.get("params", {})), setup)
    finally:
        scored.build_m1_xml = orig_xml
    ro, d, mon, m = tr.ro, tr.sim.d, tr.mon, tr.model
    rec = tr.base_record()
    rec["seed"] = seed
    rec["compiled_options"] = {"timestep": float(m.opt.timestep), "impratio": float(m.opt.impratio),
                               "noslip_iterations": int(m.opt.noslip_iterations),
                               "gravity": [float(x) for x in m.opt.gravity], "cone": int(m.opt.cone),
                               "solver": int(m.opt.solver), "iterations": int(m.opt.iterations),
                               "tolerance": float(m.opt.tolerance)}
    _, r0 = ro.poses(d)
    members = {f: ro.layer_members(d, f) for f in FACES}
    names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, int(b)) for b in ro.body_ids]
    log = D10.StepLog(m)
    tr.sim.hooks.append(log)
    chunk = int(round(SAMPLE_S / m.opt.timestep))
    sub = int(round(CAPTURE_S / m.opt.timestep))
    assert chunk % sub == 0, (chunk, sub)
    steps = int(round(duration_s / m.opt.timestep))
    steps10 = int(round(10.0 / m.opt.timestep))
    npc = len(ro.body_ids)
    body_index = np.full(m.nbody, -1)
    body_index[np.array(ro.body_ids)] = np.arange(npc)
    geom_piece = body_index[m.geom_bodyid]
    creep = np.zeros(npc)
    slide = np.zeros(npc)
    pre = collections.deque(maxlen=int(round(CAPTURE_PRE_S / CAPTURE_S)))
    post: list = []
    post_left = None
    capture_info = None
    worst = 0.0
    contact_check = None
    ts = {"t": [], "ncon": [], "ke_J": [], "solver_max_iter": [], "solver_limit_hits": [],
          "rot_deg": {f: [] for f in FACES}, "mag_force_N": [], "mag_torque_Nm": [], "mag_energy_J": [],
          "piece_ncon": [], "piece_fn_N": [], "piece_cone_use_max": [], "piece_slip_speed_max_mm_s": [],
          "piece_creep_mm": [], "piece_slide_mm": []}
    tmp = np.zeros(m.nv)
    c = None
    try:
        for k in range(0, steps, chunk):
            n_chunk = min(chunk, steps - k)
            done = 0
            while done < n_chunk:
                s = min(sub, n_chunk - done)
                tr.sim.step(s)
                done += s
                c = contacts(m, d)
                if contact_check is None and int(d.ncon):
                    contact_check = check_contacts_against_mujoco(m, d, c)
                use = cone_use(c)
                slip_mm = np.hypot(c["v"][:, 1], c["v"][:, 2]) * 1000.0 * s * m.opt.timestep
                loaded = c["f"][:, 0] > 0
                for side in ("g1", "g2"):
                    p = geom_piece[c[side]]
                    sel = (p >= 0) & loaded
                    np.add.at(creep, p[sel & (use < CONE_SLIDING)], slip_mm[sel & (use < CONE_SLIDING)])
                    np.add.at(slide, p[sel & (use >= CONE_SLIDING)], slip_mm[sel & (use >= CONE_SLIDING)])
                snap = (float(d.time), d.qpos.astype(np.float32), c)
                if post_left is None:
                    pre.append(snap)
                elif post_left > 0:
                    post.append(snap)
                    post_left -= 1
            _, r = ro.poses(d)
            for f in FACES:
                rot = ro.rotation_about_deg(r0, r, members[f], f)
                ts["rot_deg"][f].append(rot.tolist())
                if k < steps10:
                    worst = max(worst, float(np.abs(rot).max()))
            mujoco.mj_mulM(m, d, tmp, d.qvel)
            ts["t"].append(float(d.time))
            ts["ncon"].append(int(d.ncon))
            ts["ke_J"].append(float(0.5 * d.qvel @ tmp))
            mi, hits = log.take()
            ts["solver_max_iter"].append(mi)
            ts["solver_limit_hits"].append(hits)
            if ms is not None and ms.last is not None:
                p_, F, T, U = ms.last
                Fb = ms.body_sum @ F
                Tb = ms.body_sum @ (T + np.cross(p_ - d.xpos[ms.body], F))
                ts["mag_force_N"].append(np.linalg.norm(Fb, axis=1).tolist())
                ts["mag_torque_Nm"].append(np.linalg.norm(Tb, axis=1).tolist())
                ts["mag_energy_J"].append(float(U))
            # per piece, at the sample instant
            use = cone_use(c)
            speed = np.hypot(c["v"][:, 1], c["v"][:, 2]) * 1000.0
            pn = np.zeros(npc, dtype=int)
            pf = np.zeros(npc)
            pu = np.zeros(npc)
            pv = np.zeros(npc)
            for side in ("g1", "g2"):
                p = geom_piece[c[side]]
                sel = p >= 0
                np.add.at(pn, p[sel], 1)
                np.add.at(pf, p[sel], c["f"][sel, 0])
                np.maximum.at(pu, p[sel], use[sel])
                np.maximum.at(pv, p[sel], speed[sel])
            ts["piece_ncon"].append(pn.tolist())
            ts["piece_fn_N"].append([float(f"{x:.6g}") for x in pf])
            ts["piece_cone_use_max"].append([float(f"{x:.6g}") for x in pu])
            ts["piece_slip_speed_max_mm_s"].append([float(f"{x:.6g}") for x in pv])
            ts["piece_creep_mm"].append([float(f"{x:.6g}") for x in creep])
            ts["piece_slide_mm"].append([float(f"{x:.6g}") for x in slide])
            # event detection (D11's definition, at this sample)
            i = len(ts["t"]) - 1
            if capture_info is None and i >= WIN:
                best = (0.0, None, None)
                for f in FACES:
                    dd = np.abs(np.array(ts["rot_deg"][f][i]) - np.array(ts["rot_deg"][f][i - WIN]))
                    j = int(dd.argmax())
                    if dd[j] > best[0]:
                        best = (float(dd[j]), f, j)
                if best[0] >= THR:
                    f, j = best[1], best[2]
                    capture_info = {"detected_at_s": float(d.time), "piece": names[members[f][j]], "axis": f,
                                    "size_deg": best[0], "window_start_s": ts["t"][i - WIN]}
                    post_left = int(round(CAPTURE_POST_S / CAPTURE_S))
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    obs = ro.observe(d)
    pen = max(0.0, -mon.window_min_dist) * 1000
    rec.update({
        "rest_rotation_deg": worst,
        "penetration_mm": pen,
        "radial_change_mm": mon.max_radial_change * 1000,
        "final_solved": bool(obs.valid and obs.state == SOLVED),
        "members": {f: [names[i] for i in members[f]] for f in FACES},
        "magnet_bodies": None if ms is None else [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, int(b))
                                                  for b in ms.bodies],
        "piece_bodies": names,
        "contact_force_check_max_abs_N": contact_check,
        "timeseries": ts,
    })
    tr.finish(rec)
    cap = None
    if capture_info is not None:
        snaps = list(pre) + post
        cap = {"info": capture_info, "snaps": snaps, "n_pre": len(pre), "n_post": len(post),
               "geom_body": [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, int(b)) or "" for b in m.geom_bodyid]}
    return rec, cap


def capture_npz(cap: dict) -> bytes:
    snaps = cap["snaps"]
    nc = np.array([len(s[2]["g1"]) for s in snaps], dtype=np.int32)
    cat = lambda key: (np.concatenate([s[2][key] for s in snaps]) if len(snaps) else np.zeros(0))  # noqa: E731
    buf = io.BytesIO()
    np.savez_compressed(
        buf, t=np.array([s[0] for s in snaps]), qpos=np.stack([s[1] for s in snaps]), ncon=nc,
        g1=cat("g1").astype(np.int32), g2=cat("g2").astype(np.int32), dist=cat("dist").astype(np.float32),
        force=cat("f").astype(np.float32), vel=cat("v").astype(np.float32), mu=cat("mu").astype(np.float32),
        n_pre=np.int32(cap["n_pre"]), n_post=np.int32(cap["n_post"]),
        geom_body=np.array(cap["geom_body"]), info=np.array(json.dumps(cap["info"])))
    return buf.getvalue()


# ---- worker ----------------------------------------------------------------------------------------------------------
def run_job(job: dict) -> dict:
    variant, case, base_job = job["variant"], job["case"], job["base_job"]
    arm, seed, _ = CASES[case]
    assert seed in ALLOWED_SEEDS and base_job["kw"]["seed"] == seed and base_job["sub"] == "E1-1"
    LY = _load("er9g_layouts", E9 / "er9g_layouts.py")
    P = LY.probe_module()
    E7, M4, R = P.E7, P.M4, P.R
    D10 = sys.modules["d10_rest"]                    # loaded by er7_run
    from rubiknetic.cube_physics import scored
    from rubiknetic.cube_physics.m1_model import M1Params
    t0 = time.perf_counter()
    ov = dict(base_job["kw"].get("overrides", {}))
    acc = None
    if arm in ("PG8", "PG20"):                       # as er9g_run.run_one
        ST = _load("er9g_stats", E9 / "er9g_stats.py")
        LY.install_er7(arm, GRADE, cls=ST.with_class_stats(M4.RecordingMagnetSystem))
        E7.setup_arm("L0")
        ms = M4.use_magnets(R.magnet_params_for(dict(ov)), ov.get("gap", M1Params().gap))
        acc = ST.attach(ms, job["d_val"])
    warm = E7.run_one({**base_job, "er7_arm": "L0", "rest60": False})    # ER7's trial at frozen settings
    # ER7's 60 s rest set-up (er7_run.run_one), then D13's instrumented rest with the variant
    ms = M4.use_magnets(R.magnet_params_for(dict(ov)), R.GAP)
    ms.reset_neighbour_list()
    ms.reset_stats()
    M4.MagnetMonitor.last = None
    if acc is not None:
        acc = ST.attach(ms, job["d_val"])
    rec, cap = d13_rest(scored, D10, seed, ms, VARIANTS[variant])
    rec["magnet_stats"] = dict(ms.stats)
    if acc is not None:
        rec["class_stats"] = acc.as_dict(dict(ms.stats))
    out = {"variant": variant, "case": case, "arm": arm, "seed": seed, "cfg": VARIANTS[variant],
           "warmup_10s": {k: warm.get(k) for k in ("rest_rotation_deg", "pass", "fail_reasons", "seed")},
           "record": rec, "wall_s": time.perf_counter() - t0, "environment": job["env"],
           "capture": None if cap is None else {**cap["info"], "file": capture_path(variant, case).name,
                                                "n_pre": cap["n_pre"], "n_post": cap["n_post"]}}
    target = Path(job["out_dir"])
    if cap is not None:
        with open(target / capture_path(variant, case).name, "xb") as fh:
            fh.write(capture_npz(cap))
    body = gzip.compress(json.dumps(out, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x)).encode(),
                         9, mtime=0)
    with open(target / result_path(variant, case).name, "xb") as fh:
        fh.write(body)
    return {"variant": variant, "case": case, "wall_s": out["wall_s"], "rest10": rec["rest_rotation_deg"],
            "event": out["capture"], "aborted": rec.get("aborted")}


# ---- parent ----------------------------------------------------------------------------------------------------------
def environment() -> dict:
    import mujoco
    import scipy
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True).stdout
    return {"commit": head, "tracked_changes": [ln for ln in dirty.splitlines() if not ln.startswith("??")],
            "mujoco": mujoco.__version__, "numpy": np.__version__, "scipy": scipy.__version__,
            "python": platform.python_version(), "platform": platform.platform(), "cpu": platform.processor()}


def code_is_committed() -> bool:
    paths = [str(HERE / f) for f in ("PROTOCOL.md", "d13_run.py", "d13_analyze.py")]
    st = subprocess.run(["git", "status", "--porcelain", "--", *paths], cwd=REPO, capture_output=True, text=True)
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", *paths], cwd=REPO, capture_output=True)
    return st.stdout.strip() == "" and tracked.returncode == 0


def free_gb() -> float:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 1024 ** 2
    return 0.0


def workers_for(jobs_wanted: int) -> int:
    return max(1, min(jobs_wanted, int((free_gb() - MIN_FREE_GB) // WORKER_GB)))


def base_jobs() -> dict:
    LY = _load("er9g_layouts", E9 / "er9g_layouts.py")
    E7 = LY.probe_module().E7
    jobs = E7.er7_jobs()
    out = {}
    for case, (arm, seed, _) in CASES.items():
        hits = [j for j in jobs if j["sub"] == "E1-1" and j["kw"]["seed"] == seed]
        assert len(hits) == 1, (case, len(hits))
        out[case] = hits[0]
    return out


def say(msg: str) -> None:
    print(msg, flush=True)
    with open(OUT / "run_log.txt", "a") as fh:
        fh.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def run_batch(runs: list, env: dict, bases: dict, d_vals: dict, n_workers: int, out_dir: Path) -> list:
    todo = [{"variant": v, "case": c, "base_job": bases[c], "env": env, "out_dir": str(out_dir),
             "d_val": d_vals.get(CASES[c][0])} for v, c in runs]
    todo.sort(key=lambda j: -COST_FACTOR.get(j["variant"], 1.0))
    res = []
    with mp_.get_context("fork").Pool(n_workers, maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(run_job, todo):
            ev = r["event"]
            say(f"{r['variant']} {r['case']}: rest 0-10 s {r['rest10']:.6f} deg; "
                + (f"event {ev['piece']}/{ev['axis']} {ev['size_deg']:.3f} deg at {ev['window_start_s']:.2f} s"
                   if ev else "no event") + f"; wall {r['wall_s']:.0f} s" + (f"; ABORTED {r['aborted']}" if r["aborted"] else ""))
            res.append(r)
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", nargs="?", default="run", choices=("run", "smoke"))
    ap.add_argument("outdir", nargs="?")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    AN = _load("d13_analyze", HERE / "d13_analyze.py")
    d_vals = {arm: float(load_json(committed_path(c))["er9"]["D_val_deg"])
              for c, (arm, _, _) in CASES.items() if arm in ("PG8", "PG20")}
    if a.mode == "smoke":                            # code smoke: 1 s, outside the repository, compared with nothing
        out = Path(a.outdir).resolve()
        assert REPO not in out.parents and out != REPO, "smoke output must be outside the repository"
        out.mkdir(parents=True, exist_ok=True)
        global DURATION_S
        DURATION_S = 1.0
        bases = base_jobs()
        env = environment()
        todo = [("V0", "C5"), ("V2", "C1")]
        with mp_.get_context("fork").Pool(2, maxtasksperchild=1) as pool:
            for r in pool.imap_unordered(run_job, [{"variant": v, "case": c, "base_job": bases[c], "env": env,
                                                     "out_dir": str(out), "d_val": d_vals.get(CASES[c][0])}
                                                    for v, c in todo]):
                print(r, flush=True)
        return
    if not code_is_committed():
        raise SystemExit("refusing: commit PROTOCOL.md, d13_run.py and d13_analyze.py first (clean)")
    OUT.mkdir(parents=True, exist_ok=True)
    env = environment()
    env_file = OUT / "environment.json"
    if not env_file.exists():
        env_file.write_text(json.dumps(env, indent=1))
    bases = base_jobs()
    t_start = time.time()
    done = {(v, c) for v, c in all_runs() if result_path(v, c).exists()}
    if done and not a.resume:
        raise SystemExit(f"refusing: {len(done)} results exist; use --resume")
    say(f"D13 start: commit {env['commit']}, {len(done)} runs already present, free {free_gb():.1f} GB")
    v0 = [(v, c) for v, c in all_runs() if v == "V0" and (v, c) not in done]
    t_v0 = time.time()
    if v0:
        n = workers_for(a.jobs)
        say(f"V0 batch: {len(v0)} runs on {n} workers")
        run_batch(v0, env, bases, d_vals, n, OUT)
    g = AN.gate()
    (OUT / "gate.json").write_text(json.dumps(g, indent=1))
    say(f"reproduction gate: {'PASS' if g['pass'] else 'FAIL'}")
    if not g["pass"]:
        say("D13 stops: the reproduction gate failed (PROTOCOL section 5)")
        return
    walls = {c: load_json(result_path("V0", c))["wall_s"] for c in CASES}
    rest = [(v, c) for v, c in all_runs() if v != "V0" and (v, c) not in done]
    n = workers_for(a.jobs)
    work = sum(COST_FACTOR.get(v, 1.0) * walls[c] for v, c in rest)
    v0_elapsed = (time.time() - t_v0) if v0 else sum(walls.values()) / max(1, min(a.jobs, len(CASES)))
    projected = v0_elapsed + work / n
    cost = {"v0_walls_s": walls, "v0_batch_elapsed_s": v0_elapsed, "remaining_runs": len(rest), "workers": n,
            "projected_total_s": projected, "limit_s": COST_STOP_S, "factors": COST_FACTOR,
            "elapsed_this_session_s": time.time() - t_start}
    (OUT / "cost_check.json").write_text(json.dumps(cost, indent=1))
    say(f"cost check: projected total {projected / 3600:.2f} h (limit {COST_STOP_S / 3600:.0f} h), "
        f"{len(rest)} runs left on {n} workers")
    if projected > COST_STOP_S:
        say("D13 stops: projected total exceeds the cost stop (PROTOCOL section 3)")
        return
    if rest:
        run_batch(rest, env, bases, d_vals, n, OUT)
    say(f"D13 runs complete: {sum(result_path(v, c).exists() for v, c in all_runs())} / {len(all_runs())}")


if __name__ == "__main__":
    main()
