"""P-79 R0 check: with the edge_profile code in place and default (chamfer) params, one committed D14 Stage 2 record per
arm (E1-2 U_s16100, NoSlip 10) must reproduce exactly under the gates' comparison (er9g_run.gs_diff after strip).
Writes nothing under any results directory; prints and writes r0_repro.json next to this file."""
import json, sys, importlib.util
import multiprocessing as mp
from pathlib import Path
HERE = Path(__file__).resolve().parent
EXP = HERE.parent / "D14_noslip_rest_rehearsal"
sys.path.insert(0, str(EXP)); sys.path.insert(0, str(HERE.parents[1] / "src"))


def load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


def one(arm):
    S3 = load("d14s3_run", EXP / "d14s3_run.py")
    AN = load("d14s3_analyze", EXP / "d14s3_analyze.py")
    RUN2 = S3.RUN2
    env = S3.D13.environment()
    job = [j for j in S3.check_jobs(env, S3.NOSLIP) if j["er9g_arm"] == arm][0]
    rec = S3.worker(job)
    ref = RUN2.load_rec(RUN2.record_path(RUN2.S2, arm, "E1-2", "U_s16100"))
    ER9 = RUN2.er9()
    d = ER9.gs_diff(AN.strip(ref), AN.strip(rec))      # logging blocks (d14s2 / d14s3) excluded on both sides, as Stage 3a
    return {"arm": arm, "n_diffs": len(d), "diffs": d[:10], "proof_errors": S3.proof_errors(rec),
            "params_keys_equal": list(rec["params"]) == list(ref["params"]),
            "edge_fields_in_params": [k for k in ("edge_profile", "edge_radius") if k in rec["params"]]}


if __name__ == "__main__":
    with mp.get_context("fork").Pool(3, maxtasksperchild=1) as pool:
        res = pool.map(one, ["L0", "PG8", "PG20"])
    out = {"all_identical": all(r["n_diffs"] == 0 and not r["proof_errors"] for r in res), "trials": res}
    (HERE / "r0_repro.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
