"""D14 Stage 2 — E1-2, E1-5 and E1-5s at noslip_iterations 10 (PROTOCOL_STAGE2.md, committed before any computation).

Order (PROTOCOL_STAGE2 section 2): free-decay check -> frozen-setting reproduction gate (9 trials, with Stage 2's
logging) -> cost check -> 258 NoSlip trials (L0, PG8, PG20 x 86), with the pause rule. Every trial is
er9g_run.run_one (the Part G harness, unchanged) in a fresh worker; Stage 2 adds only process-local wrappers:
scored.build_m1_xml -> d13_run.with_noslip(..., 10) in NoSlip workers, and scored.Trial -> a subclass that appends a
read-only step hook in every Stage 2 worker.

Writes only under experiments/D14_noslip_rest_rehearsal/results/ (stage2_decay.json, stage2_gate/, stage2/, logs).
Usage (WSL, repo root): ~/.venvs/rubiknetic/bin/python experiments/D14_noslip_rest_rehearsal/d14s2_run.py [--jobs 4] [--resume]
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

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "results"
S2 = OUT / "stage2"
GATE_DIR = OUT / "stage2_gate"
DECAY_FILE = OUT / "stage2_decay.json"
E9 = REPO / "experiments/ER9_anchored_core_layouts"
ER7_RESULTS = REPO / "experiments/ER7_core_magnet_rehearsal/results"


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
EXPS = ("E1-2", "E1-5", "E1-5s")
COUNTS = {"E1-2": 24, "E1-5": 42, "E1-5s": 20}
NOSLIP = 10
LOG_EVERY = 10                      # E1-2 series: every 10 steps (5 ms at 0.5 ms)
COST_STOP_S = 4 * 3600.0
WALL_FACTOR = 1.26                  # D13's largest measured NoSlip wall-time factor
DECAY_W0 = {"A_hinge": 20.0, "B_ball": 20.0, "C_U_layer": 5.0}
DECAY_CAP_S = 3.0
DECAY_RANGE = (0.8, 1.25)
FACES = ("U", "R", "F", "D", "L", "B")


def er9():
    return _load("er9g_run", E9 / "er9g_run.py")


# ---- paths -----------------------------------------------------------------------------------------------------------
def frozen_path(arm: str, exp: str, tid: str) -> Path:
    d = (E9 / "results/hybrid_g/probe" / arm / exp) if arm != "L0" else (ER7_RESULTS / "L0" / exp)
    hits = sorted(d.glob(f"{tid}.json*"))
    assert len(hits) == 1, (arm, exp, tid, hits)
    return hits[0]


def record_path(root: Path, arm: str, exp: str, tid: str) -> Path:
    return root / arm / exp / f"{tid}.json.gz"


def load_rec(p: Path) -> dict:
    return json.loads(gzip.decompress(p.read_bytes())) if p.suffix == ".gz" else json.loads(p.read_text())


def dump(rec: dict) -> bytes:
    return gzip.compress(json.dumps(rec, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x)).encode(),
                         9, mtime=0)


def write_rec(p: Path, rec: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "xb") as fh:
        fh.write(dump(rec))


# ---- free-decay check (PROTOCOL_STAGE2 section 3) -------------------------------------------------------------------
def _iso_xml(kind: str, noslip: int) -> str:
    from rubiknetic.cube_physics.m1_model import M1Params
    p = M1Params()
    h = (p.pitch - p.gap) / 2
    if kind == "A_hinge":
        joint, pos = '<joint name="j" type="hinge" axis="0 0 1"', f"0 0 {p.pitch}"
    else:
        joint, pos = '<joint name="j" type="ball"', f"{p.pitch} {p.pitch} {p.pitch}"
    joint += f' damping="{p.joint_damping}" frictionloss="{p.joint_frictionloss}" armature="{p.joint_armature}"/>'
    return (f'<mujoco><option timestep="{p.timestep}" integrator="{p.integrator}" cone="{p.cone}" '
            f'impratio="{p.impratio}" solver="{p.solver}" iterations="{p.iterations}" tolerance="{p.tolerance}" '
            f'gravity="0 0 0" noslip_iterations="{int(noslip)}"/><worldbody><body name="b">{joint}'
            f'<geom type="box" size="{h} {h} {h}" pos="{pos}" mass="{p.cubie_mass}" contype="0" conaffinity="0"/>'
            f'</body></worldbody></mujoco>')


def decay_case(kind: str, noslip: int) -> dict:
    import mujoco
    w0 = DECAY_W0[kind]
    if kind in ("A_hinge", "B_ball"):
        m = mujoco.MjModel.from_xml_string(_iso_xml(kind, noslip))
        d = mujoco.MjData(m)
        if kind == "A_hinge":
            d.qvel[0] = w0
        else:
            d.qvel[2] = w0                                  # ball: local frame = world at the identity pose
        rate = lambda: float(np.linalg.norm(d.qvel[:3] if kind == "B_ball" else d.qvel[:1]))  # noqa: E731
    else:
        from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml
        xml = build_m1_xml(M1Params(radial_preload=0.0, gap=5e-5, rig=True))
        if noslip:
            xml = D13.with_noslip(xml, noslip)
        m = mujoco.MjModel.from_xml_string(xml)
        d = mujoco.MjData(m)
        mujoco.mj_forward(m, d)
        for _ in range(int(round(0.5 / m.opt.timestep))):
            mujoco.mj_step(m, d)
        bodies = []
        for b in range(m.nbody):
            name = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b) or ""
            if name.startswith("cubie_") and name[-1] == "p":
                bodies.append(b)
        assert len(bodies) == 9, bodies
        wz = np.array([0.0, 0.0, w0])
        for b in bodies:
            j = m.body_jntadr[b]
            dof = m.jnt_dofadr[j]
            if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE:
                d.qvel[dof] = float(np.dot(m.jnt_axis[j], wz))
            else:
                R = d.xmat[b].reshape(3, 3)
                d.qvel[dof:dof + 3] = R.T @ wz
        mujoco.mj_forward(m, d)
        res = np.zeros(6)

        def rate():
            zs = []
            for b in bodies:
                mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_BODY, b, res, 0)
                zs.append(res[2])
            return float(abs(np.mean(zs)))
    assert int(m.opt.noslip_iterations) == int(noslip)
    dt = float(m.opt.timestep)
    t, angle, r = 0.0, 0.0, rate()
    decayed = False
    while t < DECAY_CAP_S:
        mujoco.mj_step(m, d)
        t += dt
        r = rate()
        angle += r * dt
        if r <= 0.01 * w0:
            decayed = True
            break
    return {"kind": kind, "noslip_iterations": int(noslip), "w0_rad_s": w0, "decayed": decayed,
            "decay_time_s": t if decayed else None, "angle_rad": angle, "final_rate_rad_s": r}


def decay_check() -> dict:
    out = {"cases": {}, "range": DECAY_RANGE, "cap_s": DECAY_CAP_S}
    ok = True
    for kind in DECAY_W0:
        a, b = decay_case(kind, 0), decay_case(kind, NOSLIP)
        good = a["decayed"] and b["decayed"]
        rt = (b["decay_time_s"] / a["decay_time_s"]) if good and a["decay_time_s"] else None
        ra = (b["angle_rad"] / a["angle_rad"]) if a["angle_rad"] else None
        passed = bool(good and rt is not None and ra is not None and DECAY_RANGE[0] <= rt <= DECAY_RANGE[1]
                      and DECAY_RANGE[0] <= ra <= DECAY_RANGE[1])
        out["cases"][kind] = {"noslip0": a, "noslip10": b, "time_ratio": rt, "angle_ratio": ra, "pass": passed}
        ok &= passed
    out["pass"] = bool(ok)
    return out


# ---- worker ----------------------------------------------------------------------------------------------------------
def install_logged_trial(scored, exp: str, log: dict) -> None:
    """scored.Trial -> a subclass whose __init__ runs the original unchanged, then appends a read-only step hook."""
    import mujoco
    Base = scored.Trial

    class LoggedTrial(Base):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            m, d = self.model, self.sim.d
            log["n_trials"] = log.get("n_trials", 0) + 1
            log["options"] = {"timestep": float(m.opt.timestep), "impratio": float(m.opt.impratio),
                              "noslip_iterations": int(m.opt.noslip_iterations), "cone": int(m.opt.cone),
                              "solver": int(m.opt.solver), "iterations": int(m.opt.iterations),
                              "tolerance": float(m.opt.tolerance), "nv": int(m.nv)}
            st = {"max_solver_niter": 0, "steps_at_iteration_limit": 0, "steps": 0}
            log["solver"] = st
            lim = int(m.opt.iterations)
            series = None
            if exp == "E1-2":
                ro = self.ro
                _, r0 = ro.poses(d)
                members = {f: ro.layer_members(d, f) for f in FACES}
                jadr = {f: int(m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, f"turner_{f}_hinge")])
                        for f in FACES}
                aid = {f: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, f"turn_{f}") for f in FACES}
                pads = np.array([mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, f"pad_{f}{s}_g")
                                 for f in FACES for s in "ab"])
                series = {"t": [], "turner_deg": [], "turner_Nm": [], "layer_deg": [], "pad_contacts": []}
                log["series"] = series

            def hook(dd):
                n = int(np.max(dd.solver_niter)) if np.size(dd.solver_niter) else 0
                st["max_solver_niter"] = max(st["max_solver_niter"], n)
                st["steps_at_iteration_limit"] += int(n >= lim)
                st["steps"] += 1
                if series is not None and st["steps"] % LOG_EVERY == 0:
                    _, r = ro.poses(dd)
                    series["t"].append(float(dd.time))
                    series["turner_deg"].append([float(np.degrees(dd.qpos[jadr[f]])) for f in FACES])
                    series["turner_Nm"].append([float(dd.actuator_force[aid[f]]) for f in FACES])
                    series["layer_deg"].append([float(np.mean(ro.rotation_about_deg(r0, r, members[f], f)))
                                                for f in FACES])
                    nc = int(dd.ncon)
                    g1, g2 = np.asarray(dd.contact.geom1[:nc]), np.asarray(dd.contact.geom2[:nc])
                    series["pad_contacts"].append(int(np.isin(g1, pads).sum() + np.isin(g2, pads).sum()))
            self.sim.hooks.append(hook)

    scored.Trial = LoggedTrial


def worker(job: dict) -> dict:
    ER9 = er9()
    P, E7, M4, R = ER9.mods()
    from rubiknetic.cube_physics import scored
    noslip = bool(job["d14s2_noslip"])
    calls = [0]
    if noslip:
        orig = scored.build_m1_xml

        def wrapped(p):
            calls[0] += 1
            return D13.with_noslip(orig(p), NOSLIP)
        scored.build_m1_xml = wrapped
    log: dict = {}
    install_logged_trial(scored, job["exp"], log)
    t0 = time.perf_counter()
    rec = ER9.run_one({k: v for k, v in job.items() if not k.startswith("d14s2_")})
    if job["er9g_arm"] in ("PG8", "PG20"):
        ER9.apply_verdict(rec)                                   # as the probe's pool did
    ms = M4._MS
    rec["d14s2"] = {"noslip": noslip, "wrapper_calls": calls[0], "n_trials_constructed": log.get("n_trials", 0),
                    "trial_options": log.get("options"), "solver": log.get("solver"), "series": log.get("series"),
                    "magnet_model_noslip_iterations": int(ms.m.opt.noslip_iterations) if ms is not None else None,
                    "magnet_model_nv": int(ms.m.nv) if ms is not None else None,
                    "worker_wall_s": time.perf_counter() - t0}
    return rec


def proof_errors(rec: dict) -> list[str]:
    s = rec["d14s2"]
    want_calls = 1 if s["noslip"] else 0
    want_ns = NOSLIP if s["noslip"] else 0
    errs = []
    if s["wrapper_calls"] != want_calls:
        errs.append(f"wrapper_calls {s['wrapper_calls']} != {want_calls}")
    if s["n_trials_constructed"] != 1:
        errs.append(f"trials constructed {s['n_trials_constructed']} != 1")
    if (s["trial_options"] or {}).get("noslip_iterations") != want_ns:
        errs.append(f"trial noslip_iterations {(s['trial_options'] or {}).get('noslip_iterations')} != {want_ns}")
    if s["magnet_model_noslip_iterations"] not in (0, None):
        errs.append("magnet model has noslip")
    if s["magnet_model_nv"] is not None and s["magnet_model_nv"] != (s["trial_options"] or {}).get("nv"):
        errs.append("magnet model nv differs from the trial model")
    return errs


def trouble(rec: dict) -> list[str]:
    out = []
    if rec.get("aborted"):
        out.append(f"aborted: {rec['aborted']}")
    if rec.get("numerical_failures"):
        out.append(f"numerical failures: {rec['numerical_failures']}")
    if "harness_exception" in rec:
        out.append(f"harness exception: {rec['harness_exception']}")
    return out


# ---- parent ----------------------------------------------------------------------------------------------------------
def code_is_committed() -> bool:
    paths = [str(HERE / f) for f in ("PROTOCOL_STAGE2.md", "d14s2_run.py", "d14s2_analyze.py")]
    paths.append(str(REPO / "experiments/D13_rest_slip_mechanism/d13_run.py"))
    st = subprocess.run(["git", "status", "--porcelain", "--", *paths], cwd=REPO, capture_output=True, text=True)
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", *paths], cwd=REPO, capture_output=True)
    return st.stdout.strip() == "" and tracked.returncode == 0


def d_val(arm: str) -> float:
    ER9 = er9()
    if arm == "L0":
        return ER9.ST.PROXY_D_VAL
    return float(json.loads((E9 / "results/hybrid_g/probe" / arm / "environment.json").read_text())["D_val_deg"])


def jobs(env: dict, noslip: bool) -> list[dict]:
    ER9 = er9()
    _, E7, _, _ = ER9.mods()
    base = [j for j in E7.er7_jobs() if j["exp"] in EXPS]
    got = {e: sum(j["exp"] == e for j in base) for e in EXPS}
    assert got == COUNTS, got
    out = []
    for arm in ARMS:
        dv = d_val(arm)
        for j in base:
            ER9.check_seed(j["kw"]["seed"])
            job = ER9.make_job(j, arm, "d14s2", env, dv)
            job["d14s2_noslip"] = noslip
            out.append(job)
    return out


def gate_jobs(all_jobs: list[dict]) -> list[dict]:
    firsts, seen = [], set()
    for j in all_jobs:
        k = (j["er9g_arm"], j["exp"])
        if k not in seen:
            seen.add(k)
            firsts.append({**j, "d14s2_noslip": False})
    assert len(firsts) == len(ARMS) * len(EXPS)
    return firsts


def say(msg: str) -> None:
    print(msg, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "stage2_run_log.txt", "a") as fh:
        fh.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def run_jobs(todo: list[dict], root: Path, n_workers: int, pause_on_trouble: bool) -> dict:
    """Runs todo in fresh workers (one trial each), at most n_workers at a time; writes each record as it arrives.
    On a harness-proof error: stop at once. On trouble (abort / numerical failure / harness exception) with
    pause_on_trouble: start nothing new, let trials in flight finish, then return."""
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
                write_rec(record_path(root, rec["er9_arm"], rec["experiment"], rec["trial_id"]), rec)
                done += 1
                errs = proof_errors(rec)
                tr = trouble(rec)
                tq = [mv.get("max_turner_torque_Nm") for mv in rec.get("per_move", [])]
                extra = (f" peak {max(t for t in tq if t is not None):.3f} N.m" if tq and any(t is not None for t in tq)
                         else f" err {rec.get('U_err_after_1s_deg'):+.3f}" if rec.get("kind") == "snap"
                         else f" {rec.get('outcome')}" if rec.get("kind") == "forgive" else "")
                say(f"[{done}] {rec['er9_arm']} {rec['experiment']}/{rec['trial_id']} "
                    f"{'PASS' if rec['pass'] else 'FAIL'}{extra}; wall {rec['d14s2']['worker_wall_s']:.0f} s"
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    if not code_is_committed():
        raise SystemExit("refusing: commit PROTOCOL_STAGE2.md, d14s2_run.py and d14s2_analyze.py first (clean)")
    AN = _load("d14s2_analyze", HERE / "d14s2_analyze.py")
    env = D13.environment()
    t_start = time.time()
    say(f"Stage 2 start: commit {env['commit']}, free {D13.free_gb():.1f} GB")
    # 1. free-decay check
    if DECAY_FILE.exists():
        dec = json.loads(DECAY_FILE.read_text())
    else:
        dec = decay_check()
        dec["environment"] = env
        with open(DECAY_FILE, "x") as fh:
            json.dump(dec, fh, indent=1)
    for k, c in dec["cases"].items():
        say(f"decay {k}: time ratio {c['time_ratio']}, angle ratio {c['angle_ratio']}, pass {c['pass']}")
    if not dec["pass"]:
        say("Stage 2 stops: the free-decay check failed (PROTOCOL_STAGE2 section 3); the user decides")
        return
    # 2. gate
    all_ns = jobs(env, noslip=True)
    gj = gate_jobs(all_ns)
    todo = [j for j in gj if not record_path(GATE_DIR, j["er9g_arm"], j["exp"], j["tid"]).exists()]
    if todo:
        n = D13.workers_for(a.jobs)
        say(f"gate: {len(todo)} frozen-setting trials on {n} workers")
        r = run_jobs(todo, GATE_DIR, n, pause_on_trouble=False)
        if r["stop"]:
            say(f"Stage 2 stops: {r['stop']}")
            return
    g = AN.gate()
    (OUT / "stage2_gate.json").write_text(json.dumps(g, indent=1))
    say(f"gate: {'PASS' if g['pass'] else 'FAIL'}")
    if not g["pass"]:
        say("Stage 2 stops: the reproduction gate failed (PROTOCOL_STAGE2 section 2)")
        return
    # 3. cost check
    rest = [j for j in all_ns if not record_path(S2, j["er9g_arm"], j["exp"], j["tid"]).exists()]
    n = D13.workers_for(a.jobs)
    ratio = g["wall_ratio_by_arm"]
    work = sum(load_rec(frozen_path(j["er9g_arm"], j["exp"], j["tid"]))["er7_wall_s"] * ratio[j["er9g_arm"]]
               * WALL_FACTOR for j in rest)
    projected = (time.time() - t_start) + work / n
    cost = {"remaining": len(rest), "workers": n, "gate_wall_ratio": ratio, "factor": WALL_FACTOR,
            "projected_total_s": projected, "limit_s": COST_STOP_S, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(OUT / "stage2_cost_checks.jsonl", "a") as fh:
        fh.write(json.dumps(cost) + "\n")
    say(f"cost check: projected {projected / 3600:.2f} h (limit 4 h), {len(rest)} trials on {n} workers")
    if projected > COST_STOP_S:
        say("Stage 2 stops: projected total exceeds the cost stop (PROTOCOL_STAGE2 section 2)")
        return
    if rest and not a.resume and any(record_path(S2, j["er9g_arm"], j["exp"], j["tid"]).exists() for j in all_ns):
        raise SystemExit("refusing: Stage 2 records exist; use --resume")
    # 4. NoSlip trials, longest experiments first within the list order
    rest.sort(key=lambda j: {"E1-5": 0, "E1-5s": 1, "E1-2": 2}[j["exp"]])
    r = run_jobs(rest, S2, n, pause_on_trouble=True)
    if r["stop"]:
        say(f"Stage 2 stops: {r['stop']}")
        return
    if r["pause"]:
        say(f"Stage 2 PAUSED for the user (OPEN-8): {r['pause']}; {r['not_started']} trials not started")
        return
    n_have = sum(record_path(S2, j["er9g_arm"], j["exp"], j["tid"]).exists() for j in all_ns)
    say(f"Stage 2 trials complete: {n_have} / {len(all_ns)}")


if __name__ == "__main__":
    main()
