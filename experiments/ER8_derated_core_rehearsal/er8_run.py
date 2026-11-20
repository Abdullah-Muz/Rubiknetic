"""ER8: unscored robustness arms for ER7's C52 core layout (PROTOCOL.md).

Every trial runs through ER7's runner (experiments/ER7_core_magnet_rehearsal/er7_run.py), loaded unchanged, on ER7's
trial list and seeds (16000-16655). ER8 changes, inside each fresh worker process only:
  * arm C52d: MagnetParams.scale = 1/1.5 (every pair energy x 1/1.5) and the near-field table = M6's N52 table x 1/1.5;
  * arm C52h: nominal C52, timestep 0.25 ms (scored.params_for wrapped, as D10's A1 arm did); E1-1 only;
  * arm C52x (self-check S4 only): nothing changed; must reproduce ER7's C52 records exactly.

Usage (WSL, repo root):
    ~/.venvs/rubiknetic/bin/python experiments/ER8_derated_core_rehearsal/er8_run.py selfcheck [--jobs N]
    ~/.venvs/rubiknetic/bin/python experiments/ER8_derated_core_rehearsal/er8_run.py run [--jobs N]
Records: results/<arm>/<exp>/<tid>.json.gz (exclusive create; an existing record is skipped, so a rerun resumes).
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import multiprocessing as mp_
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "results"
TABLES = HERE / "tables"
ER7_RESULTS = REPO / "experiments/ER7_core_magnet_rehearsal/results"
ER7_COMMIT = "0cc9ff683c9608968e5ffb1ec8e0b534f9330833"       # the commit every ER7 record carries
FROZEN = ("experiments/ER7_core_magnet_rehearsal/er7_run.py", "experiments/E5_scored_m5/run.py",
          "experiments/E4_scored_m4/run.py", "experiments/D10_m5_rest_diagnostic/d10_rest.py",
          "src/rubiknetic/cube_physics")
SCALE = 1.0 / 1.5
HALF_DT = 0.00025
ARMS = {
    "C52d": {"scale": SCALE, "timestep": None, "exps": None},          # all 204 trials
    "C52h": {"scale": 1.0, "timestep": HALF_DT, "exps": ("E1-1",)},    # 20 rest trials
}
S4_ARM = {"scale": 1.0, "timestep": None, "exps": None}
S4_SKIP = {"wall_s", "wall_time_s", "er7_wall_s", "loadavg_start", "environment", "source_commit"}


def _load(name, rel):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


E7 = _load("er7_run", "experiments/ER7_core_magnet_rehearsal/er7_run.py")
M4, R = E7.M4, E7.R

from rubiknetic.cube_physics import scored  # noqa: E402
from rubiknetic.cube_physics.magnets import MagnetSystem, near_field_tables  # noqa: E402

MP52D = replace(E7.MP52, scale=SCALE)
TABLE_KEYS = ("C0", "Cp", "Cm", "Ct")


def scaled_table_path() -> Path:
    mp = MP52D     # the name near_field_tables() looks for (magnets.py), so the table is loaded and never rebuilt
    return TABLES / (f"tilt_{mp.diameter*1e3:g}x{mp.length*1e3:g}_{mp.br:g}T_s{mp.scale:g}_r{mp.r2*1e3:g}"
                     f"_h1.5_q16x48.npz")


def make_scaled_table() -> dict:
    """Writes (once) M6's N52 table x SCALE; returns its description. The source hash is checked by E7.m6_table()."""
    src, src_sha = E7.m6_table()
    dst = scaled_table_path()
    with np.load(src) as f:
        data = {k: f[k] for k in f.files}
    if not dst.exists():
        TABLES.mkdir(parents=True, exist_ok=True)
        out = {k: (v * SCALE if k in TABLE_KEYS else v) for k, v in data.items()}
        np.savez(dst, **out)
    with np.load(dst) as f:
        got = {k: f[k] for k in f.files}
    assert set(got) == set(data), (sorted(got), sorted(data))
    rel = 0.0
    for k in data:
        if k in TABLE_KEYS:
            want = data[k] * SCALE
            rel = max(rel, float(np.max(np.abs(got[k] - want)) / np.max(np.abs(want))))
        else:
            assert np.array_equal(got[k], data[k]), k
    return {"file": str(dst.relative_to(REPO)), "sha256": hashlib.sha256(dst.read_bytes()).hexdigest(),
            "source_file": str(src.relative_to(REPO)), "source_sha256": src_sha, "scale": SCALE,
            "max_rel_diff_vs_source_times_scale": rel}


def _scaled_tables(_mp=None):
    """Replaces E7._c52_tables in a C52d worker."""
    if "spline" not in E7._C52:
        sc = json.loads((OUT / "selfcheck.json").read_text())["table"]
        f = REPO / sc["file"]
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        assert f == scaled_table_path() and sha == sc["sha256"], f"derated table hash {sha} != recorded {sc['sha256']}"
        E7.m6_table()                                         # the source table still has its recorded hash
        E7._C52.update(spline=near_field_tables(MP52D, TABLES), file=sc["file"], sha=sha)
    return E7._C52["spline"]


def configure(cfg: dict) -> None:
    """Applies an arm's changes to this process (workers are fresh, so nothing is ever undone)."""
    if cfg["scale"] != 1.0:
        assert cfg["scale"] == SCALE
        E7.MP52 = MP52D
        E7._c52_tables = _scaled_tables
    if cfg["timestep"] is not None:
        pf = scored.params_for
        scored.params_for = lambda setup, **kw: pf(setup, **{"timestep": cfg["timestep"], **kw})


def run_one(job: dict) -> dict:
    arm, cfg = job["er8_arm"], job["er8_cfg"]
    configure(cfg)
    rec = E7.run_one({k: v for k, v in job.items() if not k.startswith("er8_")})
    if arm == "C52x":
        return rec                                            # S4: ER7's record, untouched
    rec["er8_arm"] = arm
    rec["mechanism"] = "ER8-" + arm
    rec["er8"] = {"scale": cfg["scale"], "timestep": cfg["timestep"]}
    want_dt = cfg["timestep"] if cfg["timestep"] is not None else 0.0005
    got = [rec["params"]["timestep"]] + ([rec["rest60"]["params"]["timestep"]] if "rest60" in rec else [])
    assert all(x == want_dt for x in got), (got, want_dt)
    assert rec["magnets"]["params"]["scale"] == cfg["scale"], rec["magnets"]["params"]
    return rec


def path_of(arm: str, exp: str, tid: str) -> Path:
    return OUT / arm / exp / f"{tid}.json.gz"


def jobs_for(arm: str, cfg: dict, env: dict) -> list[dict]:
    base = [j for j in E7.er7_jobs() if cfg["exps"] is None or j["exp"] in cfg["exps"]]
    return [{**copy.deepcopy(j), "er7_arm": "C52", "er8_arm": arm, "er8_cfg": cfg, "env": env, "commit": env["commit"],
             "scored": False, "reported_only": True} for j in base]


# ---- self-checks -----------------------------------------------------------------------------------------------------
def s1_frozen() -> dict:
    out = subprocess.run(["git", "-C", str(REPO), "diff", "--stat", ER7_COMMIT, "HEAD", "--", *FROZEN],
                         capture_output=True, text=True, check=True).stdout
    dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", *FROZEN],
                           capture_output=True, text=True, check=True).stdout
    return {"er7_commit": ER7_COMMIT, "paths": list(FROZEN), "diff": out, "uncommitted": dirty,
            "pass": out.strip() == "" and dirty.strip() == ""}


def layer_stiffness(ms) -> dict:
    """Layer stiffness (N m/rad) per face in the trial model: the calculation of ER7's _s2 / M6's S2."""
    import mujoco
    from scipy.spatial.transform import Rotation
    from rubiknetic.cube_logic.geometric import HOME_POSITIONS
    from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES
    from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml, cubie_name
    m = M4._compile_paused(build_m1_xml(M1Params(**{**M4.BASE_OVERRIDES, "gap": R.GAP})))   # S3 assertion inside
    d = mujoco.MjData(m)
    dl = float(json.loads(E7.M6_JSON.read_text())["S2"]["dlt_rad"])
    k = {}
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
            tq.append(float(sum(tot[i] @ nrm for i, g in enumerate(ms.mags) if g["body"] in mem)))
        k[f] = -(tq[0] - tq[1]) / (2 * dl)
    return k


def _s2() -> dict:
    configure(ARMS["C52d"])
    E7.setup_arm("C52")
    ms = M4.use_magnets(R.magnet_params_for({}), R.GAP)
    k = layer_stiffness(ms)
    MagnetSystem.uninstall()
    m6 = json.loads(E7.M6_JSON.read_text())["S2"]["layers"]
    rel = {f: abs(k[f] - m6[f] * SCALE) / abs(m6[f] * SCALE) for f in k}
    return {"n_magnets": ms.n, "magnet_scale": ms.mp.scale, "layers_N_m_per_rad": k,
            "layers_max_rel_diff_vs_m6_times_scale": max(rel.values()),
            "pass": bool(ms.n == 40 and ms.mp.scale == SCALE and max(rel.values()) <= 1e-9)}


def selfcheck(jobs_n: int, env: dict) -> dict:
    res = {"S1": s1_frozen(), "table": make_scaled_table()}
    res["table"]["pass"] = res["table"]["max_rel_diff_vs_source_times_scale"] <= 1e-12
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "selfcheck.json").write_text(json.dumps({**res, "pass": False}, indent=1, default=str))  # table for workers
    with mp_.get_context("fork").Pool(1, maxtasksperchild=1) as pool:
        res["S2"] = pool.apply(_s2)
    firsts, seen = [], set()
    for j in jobs_for("C52x", S4_ARM, env):
        if j["sub"] not in seen:
            seen.add(j["sub"])
            firsts.append(j)
    with mp_.get_context("fork").Pool(min(jobs_n, len(firsts)), maxtasksperchild=1) as pool:
        recs = pool.map(run_one, firsts)
    keep, E7.SKIP_KEYS = E7.SKIP_KEYS, S4_SKIP
    try:
        s4 = []
        for j, r in zip(firsts, recs):
            ref = json.loads(gzip.decompress((ER7_RESULTS / "C52" / j["exp"] / f"{j['tid']}.json.gz").read_bytes()))
            d = E7.diff(ref, json.loads(gzip.decompress(E7._dump(r))))
            s4.append({"exp": j["exp"], "sub": j["sub"], "tid": j["tid"], "n_diffs": len(d), "diffs": d[:10]})
    finally:
        E7.SKIP_KEYS = keep
    res["S4"] = {"trials": s4, "skipped_keys": sorted(S4_SKIP), "pass": all(x["n_diffs"] == 0 for x in s4)}
    res["pass"] = bool(res["S1"]["pass"] and res["table"]["pass"] and res["S2"]["pass"] and res["S4"]["pass"])
    (OUT / "selfcheck.json").write_text(json.dumps(res, indent=1, default=str))
    return res


# ---- run -------------------------------------------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("selfcheck", "run"))
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    env = E7.D10.environment()
    if a.mode == "selfcheck":
        res = selfcheck(a.jobs, env)
        print(json.dumps({"S1": res["S1"]["pass"], "table": res["table"], "S2": res["S2"],
                          "S4": [(x["sub"], x["tid"], x["n_diffs"], x["diffs"][:3]) for x in res["S4"]["trials"]],
                          "pass": res["pass"]}, indent=1, default=str), flush=True)
        return
    sc = json.loads((OUT / "selfcheck.json").read_text()) if (OUT / "selfcheck.json").exists() else None
    if not (sc and sc["pass"]):
        raise SystemExit("refusing to run: self-checks have not passed (run 'selfcheck' first)")
    if not s1_frozen()["pass"]:
        raise SystemExit("refusing to run: a frozen path differs from ER7's commit")
    a7 = ER7_RESULTS / "analysis.json"                        # PROTOCOL "Condition": C52 met all three ER7 signals
    if not (a7.exists() and json.loads(a7.read_text())["signals"]["all_met"] is True):
        raise SystemExit("refusing to run: ER7's analysis.json does not show all three C52 signals met")
    (OUT / "environment.json").write_text(json.dumps(env, indent=1))
    todo, total = [], 0
    for arm, cfg in ARMS.items():
        js = jobs_for(arm, cfg, env)
        total += len(js)
        todo += [j for j in js if not path_of(arm, j["exp"], j["tid"]).exists()]
    todo.sort(key=lambda j: (j["exp"] != "E1-1", j["exp"], j["kw"]["seed"], j["er8_arm"]))   # rest trials first
    print(f"{len(todo)} trials to run ({total} in total)", flush=True)
    t0 = time.perf_counter()
    with mp_.get_context("fork").Pool(a.jobs, maxtasksperchild=1) as pool:
        for k, rec in enumerate(pool.imap_unordered(run_one, todo), 1):
            p = path_of(rec["er8_arm"], rec["experiment"], rec["trial_id"])
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "xb") as f:
                f.write(E7._dump(rec))
            extra = f" rest {rec['rest_rotation_deg']:.3f}" if rec.get("kind") == "rest" else ""
            print(f"[{k}/{len(todo)} {time.perf_counter() - t0:.0f} s] {rec['er8_arm']} "
                  f"{'PASS' if rec['pass'] else 'FAIL'} {rec['experiment']}/{rec['trial_id']}{extra}"
                  f"{' FLAG' if rec['er7_flag_outside_regime'] else ''} {'; '.join(rec['fail_reasons'])}", flush=True)


if __name__ == "__main__":
    main()
