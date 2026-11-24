"""Compact numbers from raw/ (diagnostic only) -> catch_summary.json. Plain Python + numpy; reads only raw/."""
import glob, gzip, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"


def turn_summary(f):
    D = json.load(gzip.open(f)); s = D["s"]
    tq = np.array(s["torque_Nm"]); i = int(np.argmax(np.abs(tq)))
    by = {}
    for c in s["contacts"][i]:
        by[c["cls"]] = by.get(c["cls"], 0.0) + c["tq"]
    cub = sorted([c for c in s["contacts"][i] if c["cls"] == "cubie"], key=lambda c: -abs(c["tq"]))
    L = -np.array(s["layer_deg"]); M = np.array(s["mag_tq_Nm"]); t = np.array(s["t"]); k = t < 1.6
    return {"set": Path(f).parent.name, "arm": D["arm"], "face": D["face"], "seed": D["seed"],
            # the first batch (raw/diag2) saved no params; it ran the unmodified E1-2 job (gap override 5e-5, default gravity)
            "gravity_z": D["params"]["gravity_z"] if "params" in D else -9.81,
            "gap": D["params"]["gap"] if "params" in D else 5e-05,
            "params_source": "record" if "params" in D else "unmodified job (diag2 batch saved no params)",
            "record_max_turner_torque_Nm": D["max_turner_torque_Nm"], "record_turn_error_deg": D["turn_error_deg"],
            "peak_turner_torque_Nm": float(tq[i]), "layer_deg_at_peak": float(s["layer_deg"][i]),
            "magnet_axis_torque_at_peak_Nm": float(s["mag_tq_Nm"][i]), "magnet_axial_force_at_peak_N": float(s["mag_axial_N"][i]),
            "contact_axis_torque_by_class_at_peak_Nm": by,
            "top_cubie_contact_at_peak": cub[0] if cub else None,
            "magnet_torque_max_first_1p6s_Nm": float(M[k].max()), "layer_deg_at_magnet_max": float(L[k][np.argmax(M[k])])}


def series(mv, every=5):
    s = mv["s"]
    keys = ["t", "target_deg", "turner_deg", "layer_deg", "torque_Nm"]
    out = {k: [round(x, 4) for x in s[k][::every]] for k in keys}
    out["contact_axis_torque_by_class_Nm"] = [{a: round(b, 4) for a, b in c.items()} for c in s["tq_by_class"][::every]]
    return out


res = {"note": "UNSCORED diagnostic of D14 Stage 3b PG20 E1-4/scr20inv_s16400; see README.md", "single_turns": []}
for d in ("diag2", "diag3g", "diag3nog"):
    for f in sorted(glob.glob(str(RAW / d / "*.json.gz"))):
        res["single_turns"].append(turn_summary(f))
S = json.load(gzip.open(RAW / "diag_scr20inv_s16400.json.gz"))
res["s16400_rerun"] = {"per_move_identical_to_committed": S["per_move_identical_to_committed"],
                       "fields_identical": S["fields_identical"], "solver": S["solver"],
                       "moves": {str(m["k"]): {"move": m["move"], "series_10ms": series(m)} for m in S["diag"]["moves"] if m["detail"]}}
U = json.load(gzip.open(RAW / "diag_U_s16100.json.gz"))
res["smoke_E1-2_U_s16100"] = {"per_move_identical_to_committed": U["per_move_identical_to_committed"]}
(HERE / "catch_summary.json").write_text(json.dumps(res, indent=1))
print(len(res["single_turns"]), "single turns;", (HERE / "catch_summary.json").stat().st_size // 1024, "KB")
