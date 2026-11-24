"""P-79 R0 check: er9g_composite_checks V4 / V5 / V6 for L0, PG8 and PG20 on the rounded geometry (R 1.4 and 2.5 mm),
with noslip_iterations 10 on every model they build, exactly as D14 Stage 3a ran them on the chamfer geometry
(d14s3_run.composite_worker), plus edge_profile / edge_radius substituted into every M1Params the checks build from.
Pass criteria are each check's own committed ones. Writes r0_composite.json next to this file."""
import dataclasses, json, sys, importlib.util
import multiprocessing as mp
from pathlib import Path
HERE = Path(__file__).resolve().parent
EXP = HERE.parent / "D14_noslip_rest_rehearsal"
sys.path.insert(0, str(EXP)); sys.path.insert(0, str(HERE.parents[1] / "src"))
NOSLIP = 10


def load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


def one(job):
    arm, r = job
    S3 = load("d14s3_run", EXP / "d14s3_run.py")
    CC = load("er9g_composite_checks", S3.RUN2.E9 / "er9g_composite_checks.py")
    D8 = CC.D8
    ob, orh = D8.build, D8.build_r_hinge_model
    seen = []

    def edge(mp1):
        seen.append(1)
        return dataclasses.replace(mp1, edge_profile="rounded", edge_radius=r)

    def b(mp1):
        m, d = ob(edge(mp1)); m.opt.noslip_iterations = NOSLIP
        return m, d

    def brh(mp1):
        m, d = orh(edge(mp1)); m.opt.noslip_iterations = NOSLIP
        return m, d
    D8.build, D8.build_r_hinge_model = b, brh
    out = {"arm": arm, "edge_radius": r, "noslip_iterations": NOSLIP, "V4": CC.v4(arm), "V6": CC.v6(arm), "V5": CC.v5(arm)}
    out["models_built_rounded"] = len(seen)
    out["pass"] = all(out[k]["pass"] for k in ("V4", "V5", "V6")) and len(seen) > 0
    return out


if __name__ == "__main__":
    jobs = [(a, r) for r in (0.0014, 0.0025) for a in ("L0", "PG8", "PG20")]
    with mp.get_context("fork").Pool(6, maxtasksperchild=1) as pool:
        res = pool.map(one, jobs)
    out = {"all_pass": all(x["pass"] for x in res), "results": res}
    (HERE / "r0_composite.json").write_text(json.dumps(out, indent=1, default=float))
    for x in res:
        print(x["arm"], x["edge_radius"], "pass", x["pass"], "models", x["models_built_rounded"],
              {k: x[k]["pass"] for k in ("V4", "V5", "V6")},
              "V4 rel", x["V4"].get("max_rel_net_force"), "V5 drift", x["V5"].get("drift_rel"))
