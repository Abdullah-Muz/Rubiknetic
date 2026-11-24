"""D15 R1 analysis (PROTOCOL_R1.md section 2): the screen per radius and arm, P-79's selection rule, and the reported
items. Reads results/r1/ and D14 Stage 2's chamfer records (for comparison only). Writes results/r1/r1_analysis.json."""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r1_run as RUN  # noqa: E402

RUN2, S3 = RUN.RUN2, RUN.S3
AN3 = RUN._load("d14s3_analyze", RUN.EXP14 / "d14s3_analyze.py")
D13A = RUN._load("d13_analyze", RUN.REPO / "experiments/D13_rest_slip_mechanism/d13_analyze.py")


def er9():
    return RUN2.er9()


def load(p: Path) -> dict:
    return json.loads(gzip.decompress(p.read_bytes()))


# ---- per trial ----------------------------------------------------------------------------------------------------------
def rest_eval(out: dict, arm: str) -> dict:
    rec = out["record"]
    ev = D13A.events(rec)
    oor = None
    if arm != "L0":
        oor = er9().verdict("E1-1", [], rec.get("class_stats"), out["d_val_deg"])["out_of_regime"]
    e11 = AN3.e11_pass(rec)
    ok = bool(e11 and not ev and (arm == "L0" or oor is False))
    return {"pass": ok, "e11_pass": e11, "n_events": len(ev), "out_of_regime": oor,
            "rest_deg": rec.get("rest_rotation_deg"), "penetration_mm": rec.get("penetration_mm")}


def seq_eval(rec: dict, arm: str) -> dict:
    E = er9()
    dv = RUN2.d_val(arm)
    ok = bool(rec["pass"]) if arm == "L0" else bool(E.pass_g(rec, dv))
    oor = None if arm == "L0" else E.oor_g(rec, dv)
    pm = rec.get("per_move") or []
    clip = [i for i, m in enumerate(pm) if (m.get("max_turner_torque_Nm") or 0.0) >= E.CLIP_NM]
    return {"pass": ok and (arm == "L0" or oor is False), "flag": ok, "out_of_regime": oor, "clip_moves": clip,
            "sub": rec["sub_experiment"], "outcome": rec.get("outcome"),
            "max_drift_deg": max((m.get("nontarget_drift_deg") or 0.0 for m in pm), default=None)}


# ---- per radius / arm ------------------------------------------------------------------------------------------------------
def arm_screen(tag: str, arm: str) -> dict:
    rests = {s: RUN.rest_path(tag, arm, s) for s in RUN.REST_SEEDS}
    rest_ev = {s: rest_eval(load(p), arm) for s, p in rests.items() if p.exists()}
    seq_files = sorted((RUN.OUT / tag / arm).glob("E1-*/*.json.gz"))
    seq_recs = {}
    for p in seq_files:
        if p.parent.name == "E1-1":
            continue
        r = load(p)
        seq_recs[(r["experiment"], r["trial_id"])] = r
    seq_ev = {k: seq_eval(r, arm) for k, r in seq_recs.items()}
    counts = {e: sum(v["sub"] == e for v in seq_ev.values()) for e in RUN.SEQ_EXPS}
    complete = len(rest_ev) == len(RUN.REST_SEEDS) and counts == RUN.SEQ_COUNTS
    e12 = [r for k, r in seq_recs.items() if r["sub_experiment"] == "E1-2"]
    clip_moves = sum(len(v["clip_moves"]) for v in seq_ev.values() if v["sub"] == "E1-2")
    rest_fail = sorted(s for s, v in rest_ev.items() if not v["pass"])
    seq_fail = sorted(f"{e}/{t}" for (e, t), v in seq_ev.items() if not v["pass"])
    meets = bool(complete and not rest_fail and not seq_fail and clip_moves == 0)
    outcomes = {}
    for v in seq_ev.values():
        if v["sub"] == "E1-5":
            outcomes[v["outcome"]] = outcomes.get(v["outcome"], 0) + 1
    rest_deg = [v["rest_deg"] for v in rest_ev.values() if v["rest_deg"] is not None]
    drift = [v["max_drift_deg"] for v in seq_ev.values() if v["max_drift_deg"] is not None]
    return {"complete": complete, "n_rest": len(rest_ev), "counts": counts, "rest_failures": rest_fail,
            "seq_failures": seq_fail, "e12_moves_at_clip": clip_moves, "meets_screen": meets,
            "reported": {"e12_turner": er9().turner_stats(e12), "e15_outcomes": outcomes,
                         "rest_max_deg": max(rest_deg) if rest_deg else None,
                         "rest_events": sum(v["n_events"] for v in rest_ev.values()),
                         "max_drift_deg": max(drift) if drift else None,
                         "max_solver_niter": max(((r.get("d14s3") or {}).get("solver") or {}).get("max_solver_niter", 0)
                                                 for r in seq_recs.values()) if seq_recs else None}}


def chamfer_reference(arm: str) -> dict:
    """D14 Stage 2 (chamfer, NoSlip 10) on the same trials: reported for comparison only."""
    recs = [RUN2.load_rec(p) for p in sorted((RUN2.S2 / arm).glob("*/*.json.gz"))]
    e12 = [r for r in recs if r["sub_experiment"] == "E1-2"]
    out = {}
    for r in recs:
        if r["sub_experiment"] == "E1-5":
            out[r.get("outcome")] = out.get(r.get("outcome"), 0) + 1
    return {"e12_turner": er9().turner_stats(e12), "e15_outcomes": out}


def select(meets: dict) -> str | None:
    """P-79's rule: R 2.5 mm if it meets the screen; otherwise R 1.4 mm if it does; otherwise none."""
    if meets.get("R25"):
        return "R25"
    if meets.get("R14"):
        return "R14"
    return None


def analyze() -> dict:
    res = {"radii": {}, "chamfer_reference_stage2": {a: chamfer_reference(a) for a in RUN.ARMS}}
    for tag in RUN.RADII:
        arms = {a: arm_screen(tag, a) for a in RUN.ARMS}
        res["radii"][tag] = {"edge_radius": RUN.RADII[tag], "arms": arms,
                             "meets_screen": all(v["meets_screen"] for v in arms.values()),
                             "complete": all(v["complete"] for v in arms.values())}
    res["selected"] = select({t: v["meets_screen"] for t, v in res["radii"].items()})
    res["all_complete"] = all(v["complete"] for v in res["radii"].values())
    return res


if __name__ == "__main__":
    out = analyze()
    (RUN.OUT / "r1_analysis.json").write_text(json.dumps(out, indent=1, default=float))
    for tag, v in out["radii"].items():
        print(tag, "complete", v["complete"], "meets", v["meets_screen"],
              {a: (x["meets_screen"], x["rest_failures"], x["seq_failures"][:3], x["e12_moves_at_clip"])
               for a, x in v["arms"].items()})
    print("selected:", out["selected"])
