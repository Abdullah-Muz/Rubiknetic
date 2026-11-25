"""D15 R3 analysis (PROTOCOL_R3.md section 3): E1-7 sensitivity rehearsal of L0 at R 2.5 mm. Signal A (nominal passes
both sequences and its rest), signal B (no in-band setting flips a sequence or rest outcome against nominal), the
fragility list, the side-by-side with M5's E1-7, and the reported items. Reads results/r3/ and M5's committed E1-7
records. Writes results/r3/r3_analysis.json."""
from __future__ import annotations

import gzip
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r3_run as RUN  # noqa: E402

RUN1 = RUN.RUN1
M5_E17 = RUN.REPO / "experiments/E5_scored_m5/results/E1-7"
EXPECTED_NOT_RUN = {"magnet=4x1.5_N35__6move": "failed V3", "magnet=4x1.5_N35__sexy6": "failed V3"}
N_SEQ, N_REST = 58, 15


def load(p: Path) -> dict:
    return json.loads(gzip.decompress(p.read_bytes())) if p.suffix == ".gz" else json.loads(p.read_text())


def _max(xs):
    xs = [x for x in xs if x is not None]
    return max(xs) if xs else None


# ---- rows ------------------------------------------------------------------------------------------------------------------
def seq_row(r: dict, clip_Nm: float) -> dict:
    d, pm = r["d15"], r.get("per_move") or []
    tq = [m.get("max_turner_torque_Nm") for m in pm]
    first = next((i for i, m in enumerate(pm) if not m.get("ok_all")), None)
    return {"setting": d["setting"], "seq": d["seq"], "band": d["band"], "pass": bool(r.get("pass")),
            "fail_reasons": r.get("fail_reasons") or [], "moves_recorded": len(pm),
            "first_failing_move": None if first is None else {"index": first, "move": pm[first].get("move"),
                                                              "turn_error_deg": pm[first].get("turn_error_deg")},
            "max_abs_turn_error_deg": _max(abs(m["turn_error_deg"]) for m in pm if m.get("turn_error_deg") is not None),
            "max_nontarget_drift_deg": _max(abs(m["nontarget_drift_deg"]) for m in pm
                                            if m.get("nontarget_drift_deg") is not None),
            "max_penetration_mm": _max(m.get("penetration_mm") for m in pm),
            "max_turner_Nm": _max(tq), "median_turner_Nm": statistics.median([x for x in tq if x is not None]) if any(
                x is not None for x in tq) else None,
            "moves_at_clip": sum(1 for x in tq if x is not None and x >= clip_Nm - 1e-9),
            "numerical_failures": r.get("numerical_failures"), "harness_exception": bool(r.get("harness_exception")),
            "max_solver_niter": (d.get("solver") or {}).get("max_solver_niter"),
            "steps_at_iteration_limit": (d.get("solver") or {}).get("steps_at_iteration_limit"),
            "wall_s": d.get("worker_wall_s")}


def rest_row(o: dict) -> dict:
    AN3 = RUN1._load("d14s3_analyze", RUN1.EXP14 / "d14s3_analyze.py")
    D13A = RUN1._load("d13_analyze", RUN1.REPO / "experiments/D13_rest_slip_mechanism/d13_analyze.py")
    rec = o["record"]
    ev = D13A.events(rec)
    e11 = bool(AN3.e11_pass(rec))
    return {"setting": o["setting"], "e11_pass": e11, "n_slip_events": len(ev), "events": ev,
            "rest_deg_0_10s": rec.get("rest_rotation_deg"), "integrity_ok": rec.get("integrity_ok"),
            "ok": e11 and not ev, "rest_s": o.get("rest_s"), "wall_s": o.get("wall_s")}


# ---- signals (pure; tested) --------------------------------------------------------------------------------------------------
def signals(seq: dict, rest: dict, not_run: dict) -> dict:
    """seq: {tid: row with setting/seq/band/pass}; rest: {setting: row with ok}; not_run: {tid: reason}."""
    complete = (len(seq) == N_SEQ and len(rest) == N_REST and not_run == EXPECTED_NOT_RUN)
    nom = {r["seq"]: r["pass"] for r in seq.values() if r["setting"] == "nominal"}
    nom_rest = (rest.get("nominal") or {}).get("ok")
    a = bool(nom.get("6move") and nom.get("sexy6") and nom_rest)
    flips = sorted(t for t, r in seq.items() if r["band"] and r["setting"] != "nominal" and r["seq"] in nom
                   and r["pass"] != nom[r["seq"]])
    rest_flips = sorted(s for s, r in rest.items() if s != "nominal" and nom_rest is not None and r["ok"] != nom_rest)
    b = not flips and not rest_flips
    ref = {t: r["pass"] for t, r in seq.items() if not r["band"]}
    reading = ("incomplete: result to the user" if not complete else
               "E1-7 rehearsal clean" if a and b else
               "fragilities reported: the user decides" if a else
               "nominal failed: result to the user")
    return {"complete": complete, "signal_A_nominal": a, "nominal": {**nom, "rest": nom_rest},
            "signal_B_no_flip": b, "sequence_flips": flips, "rest_flips": rest_flips,
            "noslip_ref_reported": ref, "reading": reading}


# ---- M5 side-by-side (reported only) ----------------------------------------------------------------------------------------
def m5_table() -> dict:
    out = {}
    for p in sorted(M5_E17.glob("*.json")):
        r = load(p)
        out[r["trial_id"]] = {"pass": bool(r.get("pass")), "fail_reasons": r.get("fail_reasons") or []}
    return out


def analyze() -> dict:
    clip = 1.0
    seq = {}
    for p in sorted((RUN.OUT / "E1-7").glob("*.json.gz")):
        r = load(p)
        clip = (r.get("params") or {}).get("turn_torque_limit", clip)
        seq[r["trial_id"]] = seq_row(r, clip)
    rest = {}
    for p in sorted((RUN.OUT / "rests").glob("*.json.gz")):
        o = load(p)
        rest[o["setting"]] = rest_row(o)
    nr_file = RUN.OUT / "not_run.json"
    not_run = json.loads(nr_file.read_text()) if nr_file.exists() else {}
    sig = signals(seq, rest, not_run)
    m5 = m5_table()
    side = {t: {"M5": (m5.get(t) or {}).get("pass"), "R3": (seq.get(t) or {}).get("pass")}
            for t in sorted(set(m5) | set(seq))}
    fr = {t: seq[t] for t in sig["sequence_flips"]}
    tq = [r["max_turner_Nm"] for r in seq.values() if r["max_turner_Nm"] is not None]
    gates = {g: json.loads((RUN.OUT / f"r3_{g}.json").read_text()) if (RUN.OUT / f"r3_{g}.json").exists() else None
             for g in ("gate1", "gate2")}
    return {"gates": gates, "signals": sig, "not_run": not_run, "fragilities": fr,
            "rest_fragilities": {s: rest[s] for s in sig["rest_flips"]},
            "sequence_rows": seq, "rest_rows": rest, "m5_side_by_side": side,
            "reported": {"turner_max_Nm": max(tq) if tq else None,
                         "moves_at_clip": sum(r["moves_at_clip"] for r in seq.values()),
                         "max_drift_deg": _max(r["max_nontarget_drift_deg"] for r in seq.values()),
                         "max_penetration_mm": _max(r["max_penetration_mm"] for r in seq.values()),
                         "max_solver_niter": _max(r["max_solver_niter"] for r in seq.values()),
                         "steps_at_iteration_limit": sum(r["steps_at_iteration_limit"] or 0 for r in seq.values()),
                         "harness_exceptions": sorted(t for t, r in seq.items() if r["harness_exception"])}}


if __name__ == "__main__":
    out = analyze()
    (RUN.OUT / "r3_analysis.json").write_text(json.dumps(out, indent=1, default=float))
    s = out["signals"]
    print("gates", {g: (v or {}).get("pass") for g, v in out["gates"].items()})
    print("complete", s["complete"], "| A", s["signal_A_nominal"], s["nominal"], "| B", s["signal_B_no_flip"])
    print("sequence flips", s["sequence_flips"])
    print("rest flips", s["rest_flips"])
    print("noslip ref", s["noslip_ref_reported"])
    print("reading:", s["reading"])
    print("reported", out["reported"])
