"""UNSCORED diagnostic (2026-11-15/16): B1 + magnets at a 0.05 mm piece gap (user: "do both").

Question: does B1's drift and rest motion (angular piece play) fall within M1's limits when the clearance is halved
again, and does the tighter fit jam, deepen penetration or raise the turning torque?
Arms: gap 0.05 mm with 4x2 mm N35 magnets; gap 0.05 mm without magnets; gap 0.1 mm with magnets (paired seeds;
sequences, rest and snap only). The 0.2 mm arms are in ../size_gap0.2mm (same seeds and move strings).
Seeds: the 0.2 mm diagnostic's (9400-9402 sequences, 9000-9003 rest, 9500-9503 snap) plus 9800-9803 forgiveness and
9610/9611/9626/9627/9654/9655 abuse trials; all outside every registered range.
Magnet wall stays 0.4 mm (run.py magnet_params_for), so the face gap is piece gap + 0.8 mm (0.85 mm here).
Unmodified M4 runner logic (run_trial + apply_m4_criteria), including the P-26 neighbour-list reset.
Usage (WSL, repo root): diag_gap.py [--jobs N]
"""
import copy
import importlib.util
import json
import sys
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
spec = importlib.util.spec_from_file_location("reh", ROOT / "experiments/D8_alignment/rehearsal_gap.py")
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)
R = H.R

OUT = HERE.parent / "gap_study"
ARMS = [("g0.05_4x2", 0.00005, "4x2_N35", True), ("g0.05_none", 0.00005, None, True),
        ("g0.1_4x2", 0.0001, "4x2_N35", False)]
SUB = {"seq": "E1-4", "rest": "E1-1", "snap": "E1-5s", "forgive": "E1-5", "opposed": "E1-6b", "twist": "E1-6c",
       "twist_std": "E1-6t"}


def build_jobs():
    reh = {j["tid"]: j for j in H.jobs(0.0001, Path("/tmp"))}
    js = []
    for arm, gap, mag, full in ARMS:
        t = [(f"scr20inv_s{9400 + k}", "seq", {"moves": reh[f"scr20inv_s{7400 + k}"]["kw"]["moves"], "seed": 9400 + k})
             for k in range(3)]
        t += [(f"rest_s{9000 + k}", "rest", {"seed": 9000 + k}) for k in range(4)]
        if mag:
            t += [(f"snap_{d:+g}_s{9500 + k}", "snap", {"delta_deg": d, "seed": 9500 + k})
                  for k, d in enumerate((3.0, -3.0, 5.0, -5.0))]
        if full:
            t += [(f"forgive_{d:+g}_s{9800 + k}", "forgive", {"misalign_deg": d, "seed": 9800 + k})
                  for k, d in enumerate((10.0, -10.0, 20.0, -20.0))]
            t += [(f"opposed_UR_{n}Nm_s{s}", "opposed", {"faces": ("U", "R"), "torque_limit": float(n), "seed": s})
                  for n, s in ((1, 9610), (2, 9611))]
            t += [(f"twist_{c}_s{s}", "twist", {"corner": cc, "seed": s})
                  for c, cc, s in (("ppp", (1, 1, 1), 9626), ("nnn", (-1, -1, -1), 9627))]
            t += [(f"std_ppp_{p}_s{s}", "twist_std", {"corner": [1, 1, 1], "seed": s, "peak_Nm": v})
                  for p, v, s in (("pos", 0.45, 9654), ("neg", -0.45, 9655))]
        js += [(arm, gap, mag, tid, kind, kw) for tid, kind, kw in t]
    js.sort(key=lambda j: -len(j[5].get("moves", "").split()))
    return js


def run(job):
    arm, gap, mag, tid, kind, kw = job
    path = OUT / arm / f"{tid}.json"
    if path.exists():
        return f"skip {arm}/{tid}"
    R.BASE_OVERRIDES = {"radial_preload": 0.0, "gap": gap}
    kw = copy.deepcopy(kw)
    kw["overrides"] = {"gap": gap, "magnet": mag or "4x2_N35"}
    rec, _, _ = R.run_trial(kind, kw, mag is not None)
    rec.update({"arm": arm, "trial_id": tid, "kind": kind, "sub_experiment": SUB[kind], "spec": kw, "scored": False,
                "diagnostic": "2026-11-15 gap study"})
    R.apply_m4_criteria(rec, SUB[kind], R.nominal_validated_tilt() if mag else None, mag is not None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1, default=list))
    return f"{'PASS' if rec['pass'] else 'FAIL'} {arm}/{tid} {'; '.join(rec['fail_reasons'])}"


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 4
    js = build_jobs()
    print(len(js), "trials", flush=True)
    with Pool(n) as pool:
        for line in pool.imap_unordered(run, js):
            print(line, flush=True)
    print("done", flush=True)
