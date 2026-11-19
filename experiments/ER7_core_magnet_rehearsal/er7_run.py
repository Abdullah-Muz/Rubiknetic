"""ER7: unscored dynamic rehearsal, core magnets (C52) against frozen M5 (L0), on new seeds (PROTOCOL.md).

The trial logic is M5's runner (experiments/E5_scored_m5/run.py), loaded unchanged; it loads M4's runner. ER7 changes
only module globals of that runner, in this process:
  * seeds: M5 scored seed + 6000 (M4.SEED_SHIFT 15000, SNAP_SEED_BASE 16550, E16T_SEED_BASE 16640, range 16000-16999);
    E1-4 scrambles drawn from the new seed by M5's trials();
  * arm C52 only: M4.use_magnets installs core_layout(4x3 mm N52, c = 0.2 mm) with M6's N52 table instead of M5's
    48-magnet layout; M4.TABLES_PROVIDER returns that table (so the 4x2 availability check is skipped); the validated
    tilt passed to M5's criteria is 20 deg (P-60: ER5's real-placement trajectories), and a trial with
    near_perpendicular > 0 is also flagged.
Each trial runs in a fresh worker process (maxtasksperchild=1), so the arms never share magnet state.
E1-1: M5's scored rest trial (10 s; frozen metric and pass flag), then D10's instrumented 60 s rest on the same seed
(time series for D11's slip events). Rest is deterministic, so its first-10 s peak must equal the scored one (S4).

Usage (WSL, repo root):
    ~/.venvs/rubiknetic/bin/python experiments/ER7_core_magnet_rehearsal/er7_run.py selfcheck
    ~/.venvs/rubiknetic/bin/python experiments/ER7_core_magnet_rehearsal/er7_run.py run [--jobs N]
Records: results/<arm>/<exp>/<tid>.json.gz (never overwritten; an existing record is skipped, so a rerun resumes).
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import multiprocessing as mp_
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "results"
ARMS = ("L0", "C52")
SHIFT = 6000
C52_TILT_DEG = 20.0
CLEAR = 2e-4
M6_TABLES = REPO / "experiments/M6_core_magnets/tables"
M6_JSON = REPO / "experiments/M6_core_magnets/results/m6_checks.json"
M5_RESULTS = REPO / "experiments/E5_scored_m5/results"
EXCLUDED_EXPS = ("E1-7",)          # and every no-magnet job (E1-6n)


def _load(name, rel):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


R = _load("e5_scored_m5_run", "experiments/E5_scored_m5/run.py")      # applies M5's patches to M4
M4 = R.M4
D10 = _load("d10_rest", "experiments/D10_m5_rest_diagnostic/d10_rest.py")   # instrumented_rest only (no _load_m5)

from rubiknetic.cube_physics import scored  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml  # noqa: E402
from rubiknetic.cube_physics.magnets import MagnetParams, MagnetSystem, core_layout, near_field_tables  # noqa: E402

MP52 = MagnetParams(diameter=0.004, length=0.003, grade="N52")
M5_GLOBALS = {k: getattr(M4, k) for k in ("SEED_SHIFT", "SCORED_SEED_RANGE", "SNAP_SEED_BASE", "E16T_SEED_BASE")}
ER7_GLOBALS = {"SEED_SHIFT": M5_GLOBALS["SEED_SHIFT"] + SHIFT, "SCORED_SEED_RANGE": (16000, 16999),
               "SNAP_SEED_BASE": M5_GLOBALS["SNAP_SEED_BASE"] + SHIFT,
               "E16T_SEED_BASE": M5_GLOBALS["E16T_SEED_BASE"] + SHIFT}


def set_seeds(which: dict) -> None:
    for k, v in which.items():
        setattr(M4, k, v)


def m6_table() -> tuple[Path, str]:
    rec = json.loads(M6_JSON.read_text())["S1"]
    f = M6_TABLES / rec["n52_file"]
    got = hashlib.sha256(f.read_bytes()).hexdigest()
    assert got == rec["n52_sha256"], f"M6 N52 table hash {got} != recorded {rec['n52_sha256']}"
    return f, got


# ---- arm C52: magnet installation ------------------------------------------------------------------------------------
_C52: dict = {}


def _c52_tables(_mp=None):
    if "spline" not in _C52:
        f, sha = m6_table()
        _C52.update(spline=near_field_tables(MP52, M6_TABLES), file=str(f.relative_to(REPO)), sha=sha)
    return _C52["spline"]


def use_core(mp: MagnetParams | None, gap: float):
    """Replaces M4.use_magnets in a C52 worker: the core layout for any magnet-on trial (mp is M5's default 4x2 N35,
    ignored); None stays None."""
    M4.configure_process()
    key = ("C52", gap)
    if mp is None:
        raise RuntimeError("ER7 runs magnet-arm jobs only")
    if M4._MS is not None and M4._MS_KEY == key:
        M4._MS.install()
        return M4._MS
    MagnetSystem.uninstall()
    M4._MS, M4._MS_KEY = None, None
    p = M1Params(**{**M4.BASE_OVERRIDES, "gap": gap})
    m = M4._compile_paused(build_m1_xml(p))
    ms = M4.RecordingMagnetSystem(m, p.pitch, p.gap, MP52, tables=_c52_tables(), mags=core_layout(MP52, CLEAR))
    M4._MS, M4._MS_KEY = ms, key
    ms.install()
    return ms


def setup_arm(arm: str) -> None:
    if arm == "C52":
        M4.use_magnets = use_core
        M4.TABLES_PROVIDER = _c52_tables


# ---- job list --------------------------------------------------------------------------------------------------------
def jobs_for(globals_: dict, validated_tilt: float) -> list[dict]:
    set_seeds(globals_)
    js = [j for j in R.build_m5_jobs("er7", {}, validated_tilt) if j["magnets"] and j["exp"] not in EXCLUDED_EXPS]
    return js


def er7_jobs() -> list[dict]:
    tilt = M4.nominal_validated_tilt()
    m5 = jobs_for(M5_GLOBALS, tilt)
    er7 = jobs_for(ER7_GLOBALS, tilt)
    set_seeds(ER7_GLOBALS)
    assert len(m5) == len(er7) == 204, (len(m5), len(er7))
    for a, b in zip(m5, er7):                         # same trial list, seeds shifted by exactly 6000
        assert (a["exp"], a["sub"], a["kind"]) == (b["exp"], b["sub"], b["kind"])
        assert b["kw"]["seed"] - a["kw"]["seed"] == SHIFT, (a["tid"], b["tid"])
        assert 16000 <= b["kw"]["seed"] <= 16999
    return er7


# ---- worker ----------------------------------------------------------------------------------------------------------
def run_one(job: dict) -> dict:
    """One trial in this (fresh) process. Returns the record."""
    arm = job["er7_arm"]
    set_seeds(ER7_GLOBALS if job.get("er7_seeds", True) else M5_GLOBALS)
    setup_arm(arm)
    if arm == "C52":
        job = {**job, "validated_tilt": C52_TILT_DEG}
    t0 = time.perf_counter()
    _, rec = R.run_job(job)
    rec["er7_arm"] = arm
    rec["mechanism"] = "ER7-" + arm
    if arm == "C52":
        rec["magnet_table"] = {"table_file": _C52["file"], "table_sha256": _C52["sha"], "validated_tilt_deg": C52_TILT_DEG,
                               "validated_tilt_source": "P-60 (ER5 V3-turn, real placement)"}
    st = rec.get("magnet_stats") or {}
    rec["er7_flag_outside_regime"] = bool(arm == "C52" and (st.get("near_perpendicular", 0) > 0
                                                            or st.get("max_near_tilt_deg", 0.0) > C52_TILT_DEG))
    if job["kind"] == "rest" and job.get("rest60", True):
        ms = M4.use_magnets(R.magnet_params_for(dict(job["kw"].get("overrides", {}))), R.GAP)
        ms.reset_neighbour_list(); ms.reset_stats()
        M4.MagnetMonitor.last = None
        r60 = D10.instrumented_rest(scored, M4, job["kw"]["seed"], 60.0, ms)
        r60["magnet_stats"] = dict(ms.stats)
        rec["rest60"] = r60
        rec["s4_rest60_matches_scored"] = bool(r60["rest_rotation_deg"] == rec["rest_rotation_deg"])
    rec["er7_wall_s"] = time.perf_counter() - t0
    return rec


def _dump(rec: dict) -> bytes:
    return gzip.compress(json.dumps(rec, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x)).encode(),
                         9, mtime=0)


def path_of(arm: str, job: dict) -> Path:
    return OUT / arm / job["exp"] / f"{job['tid']}.json.gz"


# ---- self-checks -----------------------------------------------------------------------------------------------------
SKIP_KEYS = {"wall_s", "wall_time_s", "er7_wall_s", "loadavg_start", "environment", "source_commit", "startup_checks", "scored",
             "smoke", "reported_only", "mechanism", "er7_arm", "magnet_table", "rest60", "s4_rest60_matches_scored",
             "er7_flag_outside_regime", "spec", "arm"}


def diff(a, b, path="") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in set(a) | set(b):
            if k in SKIP_KEYS:
                continue
            if k not in a or k not in b:
                out.append(f"{path}/{k}: missing on one side")
            else:
                out += diff(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        return [x for i, (u, v) in enumerate(zip(a, b)) for x in diff(u, v, f"{path}[{i}]")]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


def selfcheck(jobs_n: int) -> dict:
    """S1: one M5 scored trial per experiment (first of each sub-experiment), L0 arm with its M5 seed, equals the M5
    record (all fields except run metadata). S2: C52 MagnetSystem in the trial model: 40 magnets, M6 table hash, M6's
    S2 layer stiffness within 1e-9. S3: M4's body-id assertion runs inside every C52 trial-model compile (and in S2)."""
    tilt = M4.nominal_validated_tilt()
    m5 = jobs_for(M5_GLOBALS, tilt)
    set_seeds(ER7_GLOBALS)
    firsts, seen = [], set()
    for j in m5:
        if j["sub"] not in seen:
            seen.add(j["sub"])
            firsts.append({**copy.deepcopy(j), "er7_arm": "L0", "er7_seeds": False, "rest60": False})
    with mp_.get_context("fork").Pool(min(jobs_n, len(firsts)), maxtasksperchild=1) as pool:
        recs = pool.map(run_one, firsts)
    s1 = []
    for j, r in zip(firsts, recs):
        ref = json.loads((M5_RESULTS / j["exp"] / f"{j['tid']}.json").read_text())
        d = diff(ref, json.loads(json.dumps(r, default=list)))   # as stored: tuples become lists (deviation 1)
        s1.append({"exp": j["exp"], "sub": j["sub"], "tid": j["tid"], "n_diffs": len(d), "diffs": d[:10]})
    with mp_.get_context("fork").Pool(1, maxtasksperchild=1) as pool:
        s2 = pool.apply(_s2)
    res = {"S1": {"trials": s1, "pass": all(x["n_diffs"] == 0 for x in s1)}, "S2": s2}
    res["pass"] = bool(res["S1"]["pass"] and s2["pass"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "selfcheck.json").write_text(json.dumps(res, indent=1, default=str))
    return res


def _s2() -> dict:
    import mujoco
    from scipy.spatial.transform import Rotation
    from rubiknetic.cube_logic.geometric import HOME_POSITIONS
    from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES
    from rubiknetic.cube_physics.m1_model import cubie_name
    setup_arm("C52")
    ms = M4.use_magnets(R.magnet_params_for({}), R.GAP)
    m = M4._compile_paused(build_m1_xml(M1Params(**{**M4.BASE_OVERRIDES, "gap": R.GAP})))   # S3 assertion inside
    d = mujoco.MjData(m)
    m6 = json.loads(M6_JSON.read_text())
    dl = float(m6["S2"]["dlt_rad"])
    rel = {}
    for f in FACES:
        nrm = np.array(FACE_NORMAL[f], float)
        tq = []
        for s in (1, -1):
            mujoco.mj_resetData(m, d)
            q = Rotation.from_rotvec(s * dl * nrm).as_quat()
            for h in HOME_POSITIONS:
                if int(np.dot(h, nrm)) != 1:
                    continue
                j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, cubie_name(h) + "_j")
                a = m.jnt_qposadr[j]
                if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_BALL:
                    d.qpos[a:a + 4] = [q[3], q[0], q[1], q[2]]
                else:
                    d.qpos[a] = s * dl
            mujoco.mj_kinematics(m, d)
            p, n = ms.world(d.xpos, d.xmat)
            F, T, _ = ms.forces(p, n)
            tot = T + np.cross(p, F)
            mem = {cubie_name(h) for h in HOME_POSITIONS if int(np.dot(h, nrm)) == 1}
            tq.append(float(sum(tot[k] @ nrm for k, g in enumerate(ms.mags) if g["body"] in mem)))
        k = -(tq[0] - tq[1]) / (2 * dl)
        rel[f] = abs(k - m6["S2"]["layers"][f]) / abs(m6["S2"]["layers"][f])
    MagnetSystem.uninstall()
    return {"n_magnets": ms.n, "table_sha256": _C52["sha"], "layers_max_rel_diff": max(rel.values()),
            "pass": bool(ms.n == 40 and _C52["sha"] == m6["S1"]["n52_sha256"] and max(rel.values()) <= 1e-9)}


# ---- run -------------------------------------------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("selfcheck", "run"))
    ap.add_argument("--jobs", type=int, default=10)
    a = ap.parse_args()
    env = D10.environment()
    if a.mode == "selfcheck":
        res = selfcheck(a.jobs)
        print(json.dumps({"S1": [(x["sub"], x["tid"], x["n_diffs"]) for x in res["S1"]["trials"]],
                          "S2": res["S2"], "pass": res["pass"]}, indent=1, default=str), flush=True)
        return
    sc = json.loads((OUT / "selfcheck.json").read_text()) if (OUT / "selfcheck.json").exists() else None
    if not (sc and sc["pass"]):
        raise SystemExit("refusing to run: self-checks S1/S2 have not passed (run 'selfcheck' first)")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "environment.json").write_text(json.dumps(env, indent=1))
    base = er7_jobs()
    todo = []
    for j in base:                                    # interleave arms seed by seed
        for arm in ARMS:
            if not path_of(arm, j).exists():
                todo.append({**copy.deepcopy(j), "er7_arm": arm, "env": env, "commit": env["commit"],
                             "scored": False, "reported_only": True})
    print(f"{len(todo)} trials to run ({2 * len(base)} in total)", flush=True)
    t0 = time.perf_counter()
    with mp_.get_context("fork").Pool(a.jobs, maxtasksperchild=1) as pool:
        for k, rec in enumerate(pool.imap_unordered(run_one, todo), 1):
            j = {"exp": rec["experiment"], "tid": rec["trial_id"]}
            p = path_of(rec["er7_arm"], j)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "xb") as f:
                f.write(_dump(rec))
            extra = f" rest {rec['rest_rotation_deg']:.3f}" if rec.get("kind") == "rest" else ""
            print(f"[{k}/{len(todo)} {time.perf_counter() - t0:.0f} s] {rec['er7_arm']} "
                  f"{'PASS' if rec['pass'] else 'FAIL'} {rec['experiment']}/{rec['trial_id']}{extra}"
                  f"{' FLAG' if rec['er7_flag_outside_regime'] else ''} {'; '.join(rec['fail_reasons'])}", flush=True)


if __name__ == "__main__":
    main()
