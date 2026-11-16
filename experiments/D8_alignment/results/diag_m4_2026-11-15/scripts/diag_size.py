"""UNSCORED diagnostic (2026-11-15): drift / rest / snap at the REGISTERED 0.2 mm piece gap, by magnet size.

Configs: 4x2_N35 (M4 nominal), 3x1.5_N35 (weaker; V3-validated to 7.5 deg), none (B1 without magnets).
Seeds 9000-9999 (outside every registered range). Move strings are reused from the rehearsal's scramble+inverse
specs; only seeds change. Unmodified M4 runner logic (run_trial + apply_m4_criteria).
History control: the magnet neighbour list is reset before every trial, so a trial's result does not depend on
which trial ran before it in the same worker (diagnostic only; the runner itself is unchanged).
Usage (WSL, repo root): diag_size.py [--jobs N]
"""
import copy
import importlib.util
import json
import sys
from multiprocessing import Pool
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "reh", "/mnt/c/Users/abdul/OneDrive/Desktop/Rubiknetic/experiments/D8_alignment/rehearsal_gap.py")
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)
R = H.R
from rubiknetic.cube_physics.magnets import scatter_matrices  # noqa: E402

OUT = Path("/mnt/c/Users/abdul/AppData/Local/Temp/claude/b6672f8dce1e00f4/3140f1d7-6e9e-4f5a-9e6c-c7e61a5f6350/scratchpad/diag_size")
GAP = 0.0002
CONFIGS = ["4x2_N35", "3x1.5_N35", "none"]


def build_jobs():
    reh = {j["tid"]: j for j in H.jobs(0.0001, Path("/tmp"))}
    js = []
    for cfg in CONFIGS:
        for k in range(3):
            mv = reh[f"scr20inv_s{7400 + k}"]["kw"]["moves"]
            js.append((cfg, f"scr20inv_s{9400 + k}", "seq", "E1-4", {"moves": mv, "seed": 9400 + k}))
        for k in range(4):
            js.append((cfg, f"rest_s{9000 + k}", "rest", "E1-1", {"seed": 9000 + k}))
        if cfg != "none":
            for k, deg in enumerate((3.0, -3.0, 5.0, -5.0)):
                js.append((cfg, f"snap_{deg:+g}_s{9500 + k}", "snap", "E1-5s", {"delta_deg": deg, "seed": 9500 + k}))
    js.sort(key=lambda j: -len(j[4].get("moves", "").split()))
    return js


def run(job):
    cfg, tid, kind, sub, kw = job
    path = OUT / cfg / f"{tid}.json"
    if path.exists():
        return f"skip {cfg}/{tid}"
    R.BASE_OVERRIDES = {"radial_preload": 0.0, "gap": GAP}
    kw = copy.deepcopy(kw)
    kw["overrides"] = {"gap": GAP, "magnet": cfg if cfg != "none" else "4x2_N35"}
    if R._MS is not None:                                   # history control (see docstring)
        ms = R._MS
        ms.ii, ms.jj, ms.p_ref = ms.ii_all, ms.jj_all, None
        ms.scatter = scatter_matrices(48, ms.ii, ms.jj)
    on = cfg != "none"
    rec, ms, _ = R.run_trial(kind, kw, on)
    rec.update({"config": cfg, "trial_id": tid, "kind": kind, "sub_experiment": sub, "spec": kw, "scored": False,
                "diagnostic": "2026-11-15 size/gap diagnostic"})
    R.apply_m4_criteria(rec, sub, R.nominal_validated_tilt() if on else None, on)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1, default=list))
    return f"{'PASS' if rec['pass'] else 'FAIL'} {cfg}/{tid} {'; '.join(rec['fail_reasons'])}"


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 4
    js = build_jobs()
    print(len(js), "trials", flush=True)
    with Pool(n, maxtasksperchild=None) as pool:
        for line in pool.imap_unordered(run, js):
            print(line, flush=True)
    print("done", flush=True)
