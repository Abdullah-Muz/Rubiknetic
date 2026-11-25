"""D15 R2 analysis (PROTOCOL_R2.md section 2): Part G's G.9 signals over the 204 trials per arm at R 2.5 mm, with
G.9's reading, and the reported items. Reads results/r2/ and R1's reused R 2.5 records. Writes results/r2/r2_analysis.json."""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r2_run as RUN  # noqa: E402

RUN1, RUN2 = RUN.RUN1, RUN.RUN2
AN3 = RUN1._load("d14s3_analyze", RUN1.EXP14 / "d14s3_analyze.py")
D13A = RUN1._load("d13_analyze", RUN1.REPO / "experiments/D13_rest_slip_mechanism/d13_analyze.py")
A7 = RUN1._load("er7_analyze", RUN1.REPO / "experiments/ER7_core_magnet_rehearsal/er7_analyze.py")
assert sum(A7.EXPECTED.values()) == 204


def er9():
    return RUN2.er9()


def load(p: Path) -> dict:
    return json.loads(gzip.decompress(p.read_bytes()))


def rest_rows(arm: str) -> dict:
    out = {}
    for s in RUN.REST_SEEDS:
        p = RUN.rest_path(arm, s)
        if not p.exists():
            continue
        r = load(p)
        rec = r["record"]
        ev = D13A.events(rec)
        oor = None if arm == "L0" else er9().verdict("E1-1", [], rec.get("class_stats"), r["d_val_deg"])["out_of_regime"]
        out[s] = {"e11_pass": AN3.e11_pass(rec), "n_events": len(ev), "events": ev, "out_of_regime": oor,
                  "rest_deg": rec.get("rest_rotation_deg"), "integrity_ok": rec.get("integrity_ok"),
                  "rest_s": r.get("rest_s"), "wall_s": r.get("wall_s")}
    return out


def signal1(rows: dict, arm: str) -> dict:
    complete = len(rows) == len(RUN.REST_SEEDS)
    slip = sorted(s for s, v in rows.items() if v["n_events"])
    over = sorted(s for s, v in rows.items() if not (v["rest_deg"] is not None and v["rest_deg"] <= 0.5))
    integ = sorted(s for s, v in rows.items() if not v["integrity_ok"])
    oor = sorted(s for s, v in rows.items() if arm != "L0" and v["out_of_regime"] is not False)
    lengths = {v["rest_s"] for v in rows.values()}
    met = bool(complete and not slip and not over and not integ and not oor and lengths == {RUN.REST_S})
    return {"complete": complete, "slip_seeds": slip, "rest_over_0p5_seeds": over, "integrity_failures": integ,
            "out_of_regime_seeds": oor, "rest_lengths_s": sorted(lengths),
            "max_rest_deg": max((v["rest_deg"] for v in rows.values() if v["rest_deg"] is not None), default=None),
            "signal_met": met}


def assemble(arm: str) -> dict:
    """{(exp, tid): {"sub", "pass", "rec", "source"}} for the 204 trials."""
    E = er9()
    dv = RUN2.d_val(arm)
    out = {}
    for s, v in rest_rows(arm).items():
        out[("E1-1", f"rest_s{s}")] = {"sub": "E1-1", "pass": bool(v["e11_pass"]), "rec": None, "source": "r2"}
    roots = [(RUN1.OUT / RUN.TAG / arm, RUN.REUSED, "r1"), (RUN.OUT / RUN.TAG / arm, RUN.EXPS3, "r2")]
    for root, exps, src in roots:
        for exp in exps:
            for p in sorted((root / exp).glob("*.json.gz")):
                rec = RUN2.load_rec(p)
                ok = bool(rec["pass"]) if arm == "L0" else bool(E.pass_g(rec, dv))
                out[(rec["experiment"], rec["trial_id"])] = {"sub": rec["sub_experiment"], "pass": ok, "rec": rec,
                                                             "source": src}
    return out


def reuse_check() -> dict:
    """The reused R1 files must be byte-identical to those hashed at R2's start (results/r2/reused_r1_records.json)."""
    f = RUN.OUT / "reused_r1_records.json"
    if not f.exists():
        return {"pass": False, "reason": "missing reused_r1_records.json"}
    want = json.loads(f.read_text())
    bad = []
    for arm, files in want.items():
        for key, sha in files.items():
            exp, tid = key.split("/")
            p = RUN.r1_path(arm, exp, tid)
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != sha:
                bad.append(f"{arm} {key}")
    return {"pass": not bad and all(len(v) == 86 for v in want.values()), "changed_or_missing": bad[:20]}


def chamfer_flags(arm: str, t: dict) -> list[dict]:
    """E1-3 / E1-4 / E1-6 pass flags against chamfer records where they exist (reported only): D14 Stage 3b (PG20 E1-4)
    and, for L0, ER7's frozen records."""
    E = er9()
    out = []
    for (e, i), v in t.items():
        if v["sub"] not in RUN.EXPS3:
            continue
        ref = None
        p3 = RUN2.record_path(S3_DIR(), arm, e, i)
        if p3.exists():
            r = RUN2.load_rec(p3)
            ref = ("D14 Stage 3b chamfer", bool(r["pass"]) if arm == "L0" else bool(E.pass_g(r, RUN2.d_val(arm))))
        elif arm == "L0":
            fp = RUN2.frozen_path("L0", e, i)
            if fp.exists():
                ref = ("ER7 L0 frozen chamfer", bool(RUN2.load_rec(fp)["pass"]))
        if ref is not None:
            out.append({"trial": f"{e}/{i}", "reference": ref[0], "chamfer_pass": ref[1], "rounded_pass": v["pass"]})
    return out


def S3_DIR() -> Path:
    return RUN1.S3.S3


def arm_report(arm: str) -> dict:
    E = er9()
    dv = RUN2.d_val(arm)
    rows1 = rest_rows(arm)
    s1 = signal1(rows1, arm)
    t = assemble(arm)
    rows = {e: {"n": sum(v["sub"] == e for v in t.values()), "expected": n,
                "passed": sum(v["sub"] == e and v["pass"] for v in t.values()),
                "failed": sorted(k[1] for k, v in t.items() if v["sub"] == e and not v["pass"])}
            for e, n in A7.EXPECTED.items()}
    complete = all(r["n"] == r["expected"] for r in rows.values())
    p_ok = [m.get("e16m_P_ok") for v in t.values() if v["rec"] is not None and v["sub"] in ("E1-2", "E1-3", "E1-4")
            for m in v["rec"].get("per_move", [])]
    e16m = {"moves": len(p_ok), "ok": sum(x is True for x in p_ok)}
    e16m["pass"] = bool(p_ok) and e16m["ok"] == e16m["moves"]
    option_a = bool(complete and all(r["passed"] == r["n"] for r in rows.values()) and e16m["pass"])
    recs = {k: v["rec"] for k, v in t.items() if v["rec"] is not None}
    oor_op = sorted(f"{e}/{i}" for (e, i), r in recs.items()
                    if arm != "L0" and r["sub_experiment"] in E.OPERATIONAL and E.oor_g(r, dv) is not False)
    abuse = sorted(f"{e}/{i}" for (e, i), r in recs.items()
                   if arm != "L0" and r["sub_experiment"] in E.ABUSE and E.oor_g(r, dv))
    seqs = [r for r in recs.values() if r["sub_experiment"] in ("E1-2", "E1-3", "E1-4")]
    tq = E.turner_stats(seqs)
    tq34 = E.turner_stats([r for r in seqs if r["sub_experiment"] in ("E1-3", "E1-4")])
    sig = {"1_rest_60s_no_slips": s1["signal_met"], "2_option_a_rule": option_a,
           "3_no_operational_trial_out_of_regime": (not oor_op) if arm != "L0" else None}
    sig["all_met"] = all(v for v in sig.values() if v is not None)
    clip = (tq or {}).get("at_clip", 0)
    reading = ("meets the rehearsal signals (not a candidate)" if sig["all_met"] and clip == 0 else
               "meets the rehearsal signals with moves at the clip: the user decides" if sig["all_met"] else
               "signal(s) missed: negative result kept and reported")
    r2recs = [r for r in recs.values() if r["sub_experiment"] in RUN.EXPS3]
    drift = [abs(m["nontarget_drift_deg"]) for r in recs.values() for m in r.get("per_move", [])
             if m.get("nontarget_drift_deg") is not None]
    solver = [((r.get("d14s3") or {}).get("solver") or {}) for r in r2recs]
    return {"arm": arm, "n": len(t), "rows": rows, "e16m": e16m, "complete": complete, "signal1": s1,
            "signals": sig, "reading": reading, "operational_out_of_regime": oor_op,
            "abuse_labelled_out_of_regime": abuse, "turner_Nm_E12_E13_E14": tq, "turner_Nm_E13_E14": tq34,
            "chamfer_flags": chamfer_flags(arm, t),
            "r2_trouble": sorted(f"{r['experiment']}/{r['trial_id']}" for r in r2recs if RUN2.trouble(r)),
            "max_nontarget_drift_deg": max(drift) if drift else None,
            "max_solver_niter": max((s.get("max_solver_niter", 0) for s in solver), default=None),
            "steps_at_iteration_limit": sum(s.get("steps_at_iteration_limit", 0) for s in solver),
            "rest_wall_s": sorted(v["wall_s"] for v in rows1.values() if v["wall_s"] is not None)}


def analyze() -> dict:
    g = json.loads((RUN.OUT / "r2_gate.json").read_text()) if (RUN.OUT / "r2_gate.json").exists() else None
    return {"gate": g, "reuse": reuse_check(), "arms": {a: arm_report(a) for a in RUN.ARMS}}


if __name__ == "__main__":
    out = analyze()
    (RUN.OUT / "r2_analysis.json").write_text(json.dumps(out, indent=1, default=float))
    print("gate", (out["gate"] or {}).get("pass"), "reuse", out["reuse"]["pass"])
    for a, x in out["arms"].items():
        t = x["turner_Nm_E12_E13_E14"] or {}
        print(a, x["n"], "complete", x["complete"], x["signals"], "|", x["reading"], "| clip", t.get("at_clip"),
              "max %.3f" % t.get("max", float("nan")), "| failed", {e: r["failed"] for e, r in x["rows"].items() if r["failed"]})
