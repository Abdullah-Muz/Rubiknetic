"""ER9 part B: dynamic probe of the layout(s) the static screen selected (PROTOCOL.md). Unscored.

Every trial runs through ER7's runner (experiments/ER7_core_magnet_rehearsal/er7_run.py), loaded unchanged. Inside each
fresh worker this wrapper replaces only ER7's magnet parameters (grade), its layout function and its table provider.
Trials: ER7's E1-1 (scored 10 s rest only), E1-2, E1-5 and E1-5s, on ER7's seeds.

Usage (WSL, repo root):
    ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9_probe.py selfcheck
    ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9_probe.py run [--jobs N] [--arms A B]
    ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9_probe.py report
Records: results/probe/<arm>/<exp>/<tid>.json.gz (exclusive create; an existing record is skipped).
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
OUT = HERE / "results" / "probe"
TABLES = HERE / "tables"
SCREEN = HERE / "results" / "screen.json"
ER7_RESULTS = REPO / "experiments/ER7_core_magnet_rehearsal/results"
PROBE_EXPS = ("E1-1", "E1-2", "E1-5", "E1-5s")
S_SKIP = {"wall_s", "wall_time_s", "er7_wall_s", "loadavg_start", "environment", "source_commit"}
TABLE_KEYS = ("C0", "Cp", "Cm", "Ct")


def _load(name, rel):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


E7 = _load("er7_run", "experiments/ER7_core_magnet_rehearsal/er7_run.py")
LAY = _load("er9_layout", "experiments/ER9_anchored_core_layouts/er9_layout.py")
M4, R = E7.M4, E7.R

from rubiknetic.cube_physics.magnets import GRADES_BR, MagnetParams, near_field_tables  # noqa: E402

N52 = E7.MP52
C52_CFG = {"grade": "N52", "edge_opt": ["axis"], "corner_opt": ["axis"]}


def arms() -> dict:
    """{arm name: config} from the screen's selection: 'S1' = selected layout, 'S2' = runner-up if the protocol's
    condition for a second arm holds (it differs in grade or in which pieces are split)."""
    sc = json.loads(SCREEN.read_text())
    rows = {r["variant"]: r for r in sc["rows"]}
    out = {}
    if sc["selected"]:
        a = rows[sc["selected"]]
        out["S1"] = {"variant": a["variant"], "grade": a["grade"], "edge_opt": a["edge_opt"],
                     "corner_opt": a["corner_opt"]}
        b = rows.get(sc["runner_up"])
        if b and (b["grade"] != a["grade"] or (b["edge_opt"][0], b["corner_opt"][0]) !=
                  (a["edge_opt"][0], a["corner_opt"][0])):
            out["S2"] = {"variant": b["variant"], "grade": b["grade"], "edge_opt": b["edge_opt"],
                         "corner_opt": b["corner_opt"]}
    return out


def table_for(grade: str) -> tuple[MagnetParams, Path, str]:
    """(magnet params, table folder, table SHA-256). N52: M6's table. Other grades: that table times the exact
    strength factor, written once under tables/ and checked against it on every call."""
    mp = MagnetParams(diameter=0.004, length=0.003, grade=grade)
    src, src_sha = E7.m6_table()
    if grade == "N52":
        return mp, src.parent, src_sha
    fac = (GRADES_BR[grade] / GRADES_BR["N52"]) ** 2
    name = (f"tilt_{mp.diameter*1e3:g}x{mp.length*1e3:g}_{mp.br:g}T_s{mp.scale:g}_r{mp.r2*1e3:g}_h1.5_q16x48.npz")
    dst = TABLES / name
    with np.load(src) as f:
        data = {k: f[k] for k in f.files}
    if not dst.exists():
        TABLES.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(f".{time.time_ns()}.tmp.npz")
        np.savez(tmp, **{k: (v * fac if k in TABLE_KEYS else v) for k, v in data.items()})
        try:
            tmp.rename(dst)
        except FileExistsError:
            tmp.unlink()
    with np.load(dst) as f:
        got = {k: f[k] for k in f.files}
    for k, v in data.items():
        want = v * fac if k in TABLE_KEYS else v
        assert np.allclose(got[k], want, rtol=1e-12, atol=0.0), (grade, k)
    return mp, dst.parent, hashlib.sha256(dst.read_bytes()).hexdigest()


def configure(cfg: dict) -> None:
    """Applies a layout to this (fresh) process: ER7's C52 arm then runs with it."""
    mp, folder, sha = table_for(cfg["grade"])
    eo, co = tuple(cfg["edge_opt"]), tuple(cfg["corner_opt"])
    E7.MP52 = mp
    E7.core_layout = lambda _mp, clear: LAY.anchored_core_layout(mp, clear, eo, co)

    def tables(_mp=None):
        if "spline" not in E7._C52:
            E7._C52.update(spline=near_field_tables(mp, folder), file=str(folder.relative_to(REPO)), sha=sha)
        return E7._C52["spline"]

    E7._c52_tables = tables


def run_one(job: dict) -> dict:
    arm, cfg = job["er9_arm"], job["er9_cfg"]
    configure(cfg)
    rec = E7.run_one({k: v for k, v in job.items() if not k.startswith("er9_")})
    if arm == "C52x":
        return rec                                            # self-check: ER7's record, untouched
    want = LAY.anchored_core_layout(E7.MP52, E7.CLEAR, tuple(cfg["edge_opt"]), tuple(cfg["corner_opt"]))
    assert rec["magnets"]["n_magnets"] == len(want) and rec["magnets"]["params"]["grade"] == cfg["grade"]
    rec["er9_arm"], rec["mechanism"], rec["er9"] = arm, "ER9-" + arm, cfg
    return rec


def jobs_for(arm: str, cfg: dict, env: dict) -> list[dict]:
    base = [j for j in E7.er7_jobs() if j["exp"] in PROBE_EXPS]
    return [{**copy.deepcopy(j), "er7_arm": "C52", "rest60": False, "er9_arm": arm, "er9_cfg": cfg, "env": env,
             "commit": env["commit"], "scored": False, "reported_only": True} for j in base]


def path_of(arm, exp, tid) -> Path:
    return OUT / arm / exp / f"{tid}.json.gz"


def selfcheck(env: dict) -> dict:
    """The wrapper with C52's own layout reproduces ER7's C52 records (first E1-2 and first E1-5s trial)."""
    js = jobs_for("C52x", C52_CFG, env)
    firsts = [next(j for j in js if j["sub"] == s) for s in ("E1-2", "E1-5s")]
    with mp_.get_context("fork").Pool(2, maxtasksperchild=1) as pool:
        recs = pool.map(run_one, firsts)
    keep, E7.SKIP_KEYS = E7.SKIP_KEYS, S_SKIP
    try:
        out = []
        for j, r in zip(firsts, recs):
            ref = json.loads(gzip.decompress((ER7_RESULTS / "C52" / j["exp"] / f"{j['tid']}.json.gz").read_bytes()))
            d = E7.diff(ref, json.loads(gzip.decompress(E7._dump(r))))
            out.append({"sub": j["sub"], "tid": j["tid"], "n_diffs": len(d), "diffs": d[:10]})
    finally:
        E7.SKIP_KEYS = keep
    res = {"trials": out, "arms": arms(), "pass": all(x["n_diffs"] == 0 for x in out)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "selfcheck.json").write_text(json.dumps(res, indent=1, default=str))
    return res


def report() -> dict:
    def load(folder):
        out = {}
        for f in sorted(folder.glob("*/*.json.gz")):
            r = json.loads(gzip.decompress(f.read_bytes()))
            if r["experiment"] in PROBE_EXPS:
                out[(r["experiment"], r["trial_id"])] = r
        return out

    data = {"L0": load(ER7_RESULTS / "L0"), "C52": load(ER7_RESULTS / "C52")}
    for a in arms():
        data[a] = load(OUT / a)
    res = {}
    for a, recs in data.items():
        by = {}
        for r in recs.values():
            by.setdefault(r["sub_experiment"], []).append(r)
        snap = sorted(by.get("E1-5s", []), key=lambda r: (abs(r["delta_deg"]), r["trial_id"]))
        tq = [m["max_turner_torque_Nm"] for r in by.get("E1-2", []) for m in r["per_move"]]
        st = [r["magnet_stats"] for r in recs.values() if r.get("magnet_stats")]
        res[a] = {
            "n": len(recs), "passed": {s: f"{sum(bool(r['pass']) for r in v)} / {len(v)}" for s, v in sorted(by.items())},
            "snap_abs_err_by_delta": {str(d): [round(abs(r["U_err_after_1s_deg"]), 3) for r in snap
                                               if abs(r["delta_deg"]) == d] for d in (1, 2, 3, 5, 8)},
            "snap_scored_fail": [r["trial_id"] for r in snap if r.get("snap_is_criterion") and not r["pass"]],
            "rest_max_deg": max((r["rest_rotation_deg"] for r in by.get("E1-1", [])), default=None),
            "e12_turner_Nm": {"median": float(np.median(tq)), "max": float(max(tq)),
                              "clip_moves": int(sum(t >= 0.999 for t in tq))} if tq else None,
            "flagged": sorted(f"{e}/{t}" for (e, t), r in recs.items() if r.get("er7_flag_outside_regime")),
            "max_near_tilt_deg": max((s["max_near_tilt_deg"] for s in st), default=None),
            "near_perpendicular": sum(s.get("near_perpendicular", 0) for s in st),
            "wall_s_total": sum(r.get("er7_wall_s", 0.0) for r in recs.values()),
        }
        if a not in ("L0", "C52"):
            x = res[a]
            complete = x["n"] == 106
            x["signals"] = {
                "1_snap": complete and not x["snap_scored_fail"],
                "2_rest_le_0.5": complete and x["rest_max_deg"] is not None and x["rest_max_deg"] <= 0.5,
                "3_e12_e15_pass": complete and all(bool(r["pass"]) for s in ("E1-2", "E1-5") for r in by.get(s, [])),
                "4_inside_regime": complete and not x["flagged"], "complete": complete}
            x["signals"]["all_met"] = all(x["signals"].values())
            x["config"] = arms()[a]
    (OUT / "report.json").write_text(json.dumps(res, indent=1, default=float))
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("selfcheck", "run", "report"))
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--arms", nargs="*")
    a = ap.parse_args()
    if a.mode == "report":
        print(json.dumps(report(), indent=1, default=float))
        return
    env = E7.D10.environment()
    if a.mode == "selfcheck":
        print(json.dumps(selfcheck(env), indent=1, default=str), flush=True)
        return
    sc = json.loads((OUT / "selfcheck.json").read_text()) if (OUT / "selfcheck.json").exists() else None
    if not (sc and sc["pass"]):
        raise SystemExit("refusing to run: the self-check has not passed (run 'selfcheck' first)")
    todo, total = [], 0
    for arm, cfg in arms().items():
        if a.arms and arm not in a.arms:
            continue
        table_for(cfg["grade"])                               # derived table written by the parent, once
        js = jobs_for(arm, cfg, env)
        total += len(js)
        todo += [j for j in js if not path_of(arm, j["exp"], j["tid"]).exists()]
    todo.sort(key=lambda j: (j["exp"] != "E1-5s", j["exp"] != "E1-1", j["exp"], j["kw"]["seed"]))
    print(f"{len(todo)} trials to run ({total} in total)", flush=True)
    t0 = time.perf_counter()
    with mp_.get_context("fork").Pool(a.jobs, maxtasksperchild=1) as pool:
        for k, rec in enumerate(pool.imap_unordered(run_one, todo), 1):
            p = path_of(rec["er9_arm"], rec["experiment"], rec["trial_id"])
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "xb") as f:
                f.write(E7._dump(rec))
            extra = (f" rest {rec['rest_rotation_deg']:.3f}" if rec.get("kind") == "rest" else
                     f" err {rec.get('U_err_after_1s_deg'):+.3f}" if rec.get("kind") == "snap" else "")
            print(f"[{k}/{len(todo)} {time.perf_counter() - t0:.0f} s] {rec['er9_arm']} "
                  f"{'PASS' if rec['pass'] else 'FAIL'} {rec['experiment']}/{rec['trial_id']}{extra}"
                  f"{' FLAG' if rec['er7_flag_outside_regime'] else ''} {'; '.join(rec['fail_reasons'])}", flush=True)


if __name__ == "__main__":
    main()
