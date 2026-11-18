"""D10 — unscored diagnostic of the M5 E1-1 rest failure (PROTOCOL.md, fixed before this script ran).

Arms (PROTOCOL.md section 3), each on seeds 10001 and 10000:
  A0   frozen rest trial through the M5 runner's M4.run_trial("rest", ...)   (exact reproduction)
  A0i  instrumented copy of scored.run_rest_trial, frozen settings            (instrumentation is read-only)
  A1   timestep 0.25 ms        A2  timestep 0.125 ms     A3  solver iterations 400
  A4   no magnets              A5  60 s rest

Read-only use of the M5 runner (experiments/E5_scored_m5/run.py is imported, which applies its documented patches to
the M4 runner in this process). Writes only to experiments/D10_m5_rest_diagnostic/results/.

Usage (WSL, as M5):  ~/.venvs/rubiknetic/bin/python experiments/D10_m5_rest_diagnostic/d10_rest.py [--jobs N]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import multiprocessing as mp_
import platform
import subprocess
import sys
import time
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "results"
SEEDS = (10001, 10000)
RECORDED = {10001: 0.5602934615568214, 10000: 0.4979196969239446}   # E5_scored_m5/results/E1-1/rest_s*.json
SAMPLE_S = 0.025          # frozen sampling: every 50 steps at 0.5 ms
ARMS = {
    "A0": {},
    "A0i": {},
    "A1": {"timestep": 0.00025},
    "A2": {"timestep": 0.000125},
    "A3": {"iterations": 400},
    "A4": {"magnets": False},
    "A5": {"duration_s": 60.0},
}


def _load_m5():
    spec = importlib.util.spec_from_file_location("e5_scored_m5_run_for_d10", REPO / "experiments/E5_scored_m5/run.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class StepLog:
    """Read-only AuditedSim hook: largest solver iteration count since the last sample."""

    def __init__(self, m):
        self.limit = int(m.opt.iterations)
        self.max_iter = 0
        self.hits = 0

    def __call__(self, d) -> None:
        n = int(np.max(d.solver_niter)) if np.size(d.solver_niter) else 0
        self.max_iter = max(self.max_iter, n)
        self.hits += int(n >= self.limit)

    def take(self):
        out = (self.max_iter, self.hits)
        self.max_iter, self.hits = 0, 0
        return out


def instrumented_rest(scored, M4, seed: int, duration_s: float, ms) -> dict:
    """scored.run_rest_trial (scored.py:317), unchanged in its physics and its metric, plus read-only logging."""
    from rubiknetic.cube_logic import SOLVED
    from rubiknetic.cube_physics.rig import EditAuditError, NumericalFailure
    FACES = scored.FACES
    setup = scored.draw_setup(seed)
    tr = scored.Trial(scored.params_for(setup), setup)
    ro, d, mon, m = tr.ro, tr.sim.d, tr.mon, tr.model
    rec = tr.base_record()
    rec["seed"] = seed
    _, r0 = ro.poses(d)
    members = {f: ro.layer_members(d, f) for f in FACES}
    names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, int(b)) for b in ro.body_ids]
    log = StepLog(m)
    tr.sim.hooks.append(log)
    chunk = int(round(SAMPLE_S / m.opt.timestep))
    steps = int(round(duration_s / m.opt.timestep))
    steps10 = int(round(10.0 / m.opt.timestep))
    worst = 0.0
    ts = {"t": [], "ncon": [], "ke_J": [], "solver_max_iter": [], "solver_limit_hits": [],
          "rot_deg": {f: [] for f in FACES}, "mag_force_N": [], "mag_torque_Nm": [], "mag_energy_J": []}
    tmp = np.zeros(m.nv)
    try:
        for k in range(0, steps, chunk):
            tr.sim.step(min(chunk, steps - k))
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
                p, F, T, U = ms.last
                Fb = ms.body_sum @ F
                Tb = ms.body_sum @ (T + np.cross(p - d.xpos[ms.body], F))
                ts["mag_force_N"].append(np.linalg.norm(Fb, axis=1).tolist())
                ts["mag_torque_Nm"].append(np.linalg.norm(Tb, axis=1).tolist())
                ts["mag_energy_J"].append(float(U))
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
        "timeseries": ts,
    })
    tr.finish(rec)
    return rec


def attribute(rec: dict, window_s: float = 10.0) -> dict:
    """Peak (frozen metric, first 10 s), where and when it occurs, and the fixed descriptive label."""
    ts = rec["timeseries"]
    t = np.array(ts["t"]) - ts["t"][0] + SAMPLE_S        # time since t0 (first sample at 25 ms)
    best = (0.0, None)
    for f, rows in ts["rot_deg"].items():
        a = np.abs(np.array(rows))                         # samples x members
        sel = t <= window_s + 1e-9
        if not a[sel].size:
            continue
        i, j = np.unravel_index(np.argmax(a[sel]), a[sel].shape)
        if a[sel][i, j] > best[0]:
            best = (float(a[sel][i, j]), (f, int(i), int(j)))
    peak, (f, i, j) = best
    row = np.array(ts["rot_deg"][f][i])
    signed = float(row[j])
    layer_mean = float(row.mean())
    frac = abs(layer_mean) / peak if peak else 0.0
    same_sign = np.sign(layer_mean) == np.sign(signed)
    label = "layer-coherent" if (frac >= 0.8 and same_sign) else "single-cubie" if frac <= 0.2 else "mixed"
    out = {"peak_deg": peak, "peak_face": f, "peak_cubie": rec["members"][f][j], "peak_time_s": float(t[i]),
           "peak_signed_deg": signed, "layer_mean_deg_at_peak": layer_mean, "layer_spread_deg_at_peak":
           float(row.max() - row.min()), "layer_mean_fraction": frac, "label": label}
    if t[-1] > 10.5:   # A5 creep check (rule 3)
        late = t >= 50.0 - 1e-9
        out["max_abs_50_60s_deg"] = float(max(np.abs(np.array(rows))[late].max()
                                               for rows in ts["rot_deg"].values()))
        out["creep_excess_deg"] = out["max_abs_50_60s_deg"] - peak
    return out


def run_job(job: tuple) -> dict:
    arm, seed = job
    M5 = _load_m5()
    M4 = M5.M4
    from rubiknetic.cube_physics import scored
    cfg = dict(ARMS[arm])
    t0 = time.perf_counter()
    if arm == "A0":
        rec, ms, info = M4.run_trial("rest", {"seed": seed, "overrides": {"gap": M5.GAP}}, True)
        rec.pop("magnets", None)
        out = {"arm": arm, "seed": seed, "frozen_record": rec, "rest_rotation_deg": rec["rest_rotation_deg"]}
    else:
        magnets = cfg.pop("magnets", True)
        duration = cfg.pop("duration_s", 10.0)
        mp = M5.magnet_params_for({}) if magnets else None
        ms = M4.use_magnets(mp, M5.GAP)
        if ms is not None:
            ms.reset_neighbour_list()
            ms.reset_stats()
        M4.MagnetMonitor.last = None
        pf = scored.params_for
        scored.params_for = lambda setup, **kw: pf(setup, **{**cfg, **kw})
        try:
            rec = instrumented_rest(scored, M4, seed, duration, ms)
        finally:
            scored.params_for = pf
        rec["magnet_stats"] = None if ms is None else dict(ms.stats)
        out = {"arm": arm, "seed": seed, "overrides": ARMS[arm], "rest_rotation_deg": rec["rest_rotation_deg"],
               "attribution": attribute(rec), "record": rec}
    out["wall_s"] = time.perf_counter() - t0
    return out


def environment() -> dict:
    import numpy, scipy
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True).stdout
    return {"commit": head, "tracked_changes": [l for l in dirty.splitlines() if not l.startswith("??")],
            "mujoco": mujoco.__version__, "numpy": numpy.__version__, "scipy": scipy.__version__,
            "python": platform.python_version(), "platform": platform.platform(), "cpu": platform.processor()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=7)
    ap.add_argument("--arms", nargs="*", default=list(ARMS))
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    env = environment()
    (OUT / "environment.json").write_text(json.dumps(env, indent=1))
    jobs = [(arm, s) for arm in a.arms for s in SEEDS]
    jobs.sort(key=lambda j: {"A5": 0, "A2": 1, "A1": 2}.get(j[0], 3))     # longest first
    with mp_.get_context("fork").Pool(a.jobs, maxtasksperchild=1) as pool:
        for res in pool.imap_unordered(run_job, jobs):
            res["environment"] = env
            p = OUT / f"{res['arm']}_s{res['seed']}.json"
            p.write_text(json.dumps(res, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x)))
            print(f"{res['arm']:4s} s{res['seed']}  peak {res['rest_rotation_deg']:.6f} deg  "
                  f"{res.get('attribution', {}).get('label', '')}  wall {res['wall_s']:.0f} s", flush=True)


if __name__ == "__main__":
    main()
