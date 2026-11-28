"""Runtime check (UNSCORED, rehearsal seeds): did the magnet force act at every simulation step on G1's scored trial
path (experiments/E7_scored_m7/run.py)? Counts MagnetSystem.apply calls inside every AuditedSim.step, runs a few of
E7's own self-check jobs in this process, and compares each record with its committed rehearsal reference (so the
probed path is the G1 path: 0 differences required). Read-only; writes nothing in the repository."""
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path("/mnt/c/dev/Rubiknetic")
sys.path.insert(0, str(REPO / "src"))
spec = importlib.util.spec_from_file_location("e7_run", REPO / "experiments/E7_scored_m7/run.py")
E7 = importlib.util.module_from_spec(spec)
sys.modules["e7_run"] = E7
spec.loader.exec_module(E7)

from rubiknetic.cube_physics import magnets as MG  # noqa: E402
from rubiknetic.cube_physics import rig as RIG  # noqa: E402

cnt = {"apply": 0, "steps": 0, "missing": 0}
_apply = MG.MagnetSystem.apply


def apply(self, m, d):
    cnt["apply"] += 1
    return _apply(self, m, d)


MG.MagnetSystem.apply = apply
_step = RIG.AuditedSim.step


def step(self, n=1, *a, **k):
    for _ in range(n):
        c0 = cnt["apply"]
        _step(self, 1, *a, **k)
        cnt["steps"] += 1
        cnt["missing"] += cnt["apply"] == c0
    return None


RIG.AuditedSim.step = step

env = E7.R.environment()
jobs = E7.selfcheck_jobs(env)
want = sys.argv[1:] or ["E1-2", "E1-4", "E1-1"]
picked = []
for sub in want:
    picked += [j for j in jobs if j["sub"] == sub][:1]
out = []
for j in picked:
    j["commit"], j["startup"], j["magnet_info"] = "probe", None, None
    for k in cnt:
        cnt[k] = 0
    key, rec = E7.R.run_job(j)
    diffs = E7.selfcheck_compare(j, rec)
    row = {"sub": j["sub"], "tid": j["tid"], "kind": j["kind"], "magnets_flag": j.get("magnets"), **cnt,
           "pass": rec.get("pass"), "diffs_vs_rehearsal": len(diffs), "first_diffs": diffs[:3]}
    out.append(row)
    print(json.dumps(row), flush=True)
print("SUMMARY", json.dumps({"trials": len(out), "all_steps_with_magnet_force": all(r["missing"] == 0 and r["steps"] > 0
                                                                                   for r in out),
                             "all_identical_to_rehearsal": all(r["diffs_vs_rehearsal"] == 0 for r in out)}))
