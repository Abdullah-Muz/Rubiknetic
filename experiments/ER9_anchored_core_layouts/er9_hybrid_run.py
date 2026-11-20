"""ER9 part E runner (PROTOCOL.md, Part E): hybrid arms (M5's 48 magnets + anchors). Unscored.

Usage (WSL, repo root):
    ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9_hybrid_run.py selfcheck
    ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9_hybrid_run.py probe [--jobs N] [--arms ..]
    ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9_hybrid_run.py report
    ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9_hybrid_run.py full --arms ARM [--jobs N]
Records: results/hybrid/{probe,full}/<arm>/<exp>/<tid>.json.gz (exclusive create; an existing record is skipped).
"""
from __future__ import annotations

import argparse
import copy
import gzip
import importlib.util
import json
import multiprocessing as mp_
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("er9_hybrid", HERE / "er9_hybrid.py")
HY = importlib.util.module_from_spec(spec); sys.modules["er9_hybrid"] = HY; spec.loader.exec_module(HY)
P, E7, M4 = HY.P, HY.E7, HY.M4
ROOT = HERE / "results" / "hybrid"
ARMS = {"HB1": HY.cfg_for(1.0), "HB2": HY.cfg_for(2.0), "HB3": HY.cfg_for(3.0)}
OFF = {**HY.cfg_for(0.0), "anchors": False, "variant": "M5 48 only (self-check)"}
SC_SKIP = set(P.S_SKIP) | {"er7_arm", "mechanism", "magnet_table", "er9_arm", "er9"}
TILT_SOURCE = "M5 V3 (4x2 mm N35 table)"


def run_one(job: dict) -> dict:
    arm, cfg = job["er9_arm"], job["er9_cfg"]
    HY.configure(cfg)
    rec = E7.run_one({k: v for k, v in job.items() if not k.startswith("er9_")})
    assert rec["magnets"]["n_magnets"] == len(HY.hybrid_mags(cfg)[1]), rec["magnets"]["n_magnets"]
    rec["magnet_table"]["validated_tilt_source"] = TILT_SOURCE
    assert rec["magnet_table"]["validated_tilt_deg"] == M4.nominal_validated_tilt()
    rec["er9_arm"], rec["mechanism"], rec["er9"] = arm, "ER9-" + arm, cfg
    return rec


def selfcheck(env: dict) -> dict:
    js = P.jobs_for("L0x", OFF, env)
    firsts = [next(j for j in js if j["sub"] == s) for s in ("E1-2", "E1-5s")]
    with mp_.get_context("fork").Pool(2, maxtasksperchild=1) as pool:
        recs = pool.map(run_one, firsts)
    keep, E7.SKIP_KEYS = E7.SKIP_KEYS, SC_SKIP
    try:
        out = []
        for j, r in zip(firsts, recs):
            ref = json.loads(gzip.decompress((P.ER7_RESULTS / "L0" / j["exp"] / f"{j['tid']}.json.gz").read_bytes()))
            d = E7.diff(ref, json.loads(gzip.decompress(E7._dump(r))))
            out.append({"sub": j["sub"], "tid": j["tid"], "n_diffs": len(d), "diffs": d[:20]})
    finally:
        E7.SKIP_KEYS = keep
    res = {"trials": out, "arms": ARMS, "validated_tilt_deg": M4.nominal_validated_tilt(),
           "pass": all(x["n_diffs"] == 0 for x in out)}
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "selfcheck.json").write_text(json.dumps(res, indent=1, default=str))
    return res


def report() -> dict:
    """er9_probe.report() applied to the hybrid arms (its signals, unchanged)."""
    keep = P.arms, P.OUT
    P.arms, P.OUT = (lambda: ARMS), ROOT / "probe"
    try:
        return P.report()
    finally:
        P.arms, P.OUT = keep


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("selfcheck", "probe", "report", "full"))
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
    sc = json.loads((ROOT / "selfcheck.json").read_text()) if (ROOT / "selfcheck.json").exists() else None
    if not (sc and sc["pass"]):
        raise SystemExit("refusing to run: the hybrid self-check has not passed (run 'selfcheck' first)")
    out = ROOT / a.mode
    todo, total = [], 0
    if a.mode == "probe":
        for arm, cfg in ARMS.items():
            if a.arms and arm not in a.arms:
                continue
            js = P.jobs_for(arm, cfg, env)
            total += len(js)
            todo += js
        todo.sort(key=lambda j: (j["exp"] != "E1-5s", j["exp"] != "E1-1", j["exp"], j["kw"]["seed"]))
    else:
        if not a.arms or len(a.arms) != 1:
            raise SystemExit("full: name exactly one arm with --arms")
        arm = a.arms[0]
        rep = json.loads((ROOT / "probe" / "report.json").read_text())
        if not rep[arm]["signals"]["all_met"]:
            raise SystemExit(f"refusing to run: arm {arm} did not meet the probe signals")
        todo = [{**copy.deepcopy(j), "er7_arm": "C52", "er9_arm": arm, "er9_cfg": ARMS[arm], "env": env,
                 "commit": env["commit"], "scored": False, "reported_only": True} for j in E7.er7_jobs()]
        total = len(todo)
        todo.sort(key=lambda j: -len(j["kw"].get("moves", "").split()))        # longest sequences first
        (out / arm).mkdir(parents=True, exist_ok=True)
        (out / arm / "environment.json").write_text(json.dumps({**env, "config": ARMS[arm]}, indent=1))

    def path(j):
        return out / j["er9_arm"] / j["exp"] / f"{j['tid']}.json.gz"

    todo = [j for j in todo if not path(j).exists()]
    print(f"{len(todo)} trials to run ({total} in total); mode {a.mode}", flush=True)
    t0 = time.perf_counter()
    with mp_.get_context("fork").Pool(a.jobs, maxtasksperchild=1) as pool:
        for k, rec in enumerate(pool.imap_unordered(run_one, todo), 1):
            p = out / rec["er9_arm"] / rec["experiment"] / f"{rec['trial_id']}.json.gz"
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
