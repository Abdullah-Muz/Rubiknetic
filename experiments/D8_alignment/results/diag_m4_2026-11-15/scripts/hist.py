"""UNSCORED: run rehearsal jobs <tid...> sequentially in ONE process; print move-level results (history test)."""
import copy, importlib.util, sys, json
from pathlib import Path
tids = sys.argv[1:]; sys.argv = sys.argv[:1]
spec = importlib.util.spec_from_file_location("reh", "/mnt/c/Users/abdul/OneDrive/Desktop/Rubiknetic/experiments/D8_alignment/rehearsal_gap.py")
H = importlib.util.module_from_spec(spec); spec.loader.exec_module(H); R = H.R
jobs = {j["tid"]: j for j in H.jobs(0.0001, Path("/tmp"))}
for tid in tids:
    j = jobs[tid]; R.BASE_OVERRIDES = {"radial_preload": 0.0, "gap": 0.0001}
    p_ref_before = None if R._MS is None or R._MS.p_ref is None else "kept"
    rec, ms, _ = R.run_trial(j["kind"], copy.deepcopy(j["kw"]), True)
    out = {"tid": tid, "list_state_at_start": p_ref_before, "rebuilds": rec["magnet_stats"]["list_rebuilds"], "pass": rec["pass"]}
    if "per_move" in rec and len(rec["per_move"]) > 12:
        m = rec["per_move"][12]; out.update(drift12=m["nontarget_drift_deg"], t_motion12=m["t_layer_motion_s"], causal12=m["causal"],
                                            max_drift=max(x["nontarget_drift_deg"] for x in rec["per_move"]))
    print(json.dumps(out), flush=True)
