"""D15 R4 analysis (PROTOCOL_R4.md section 2): M7's Option A battery on fresh seeds 19000-19655. Signal 1 (rests: 20 / 20,
0 D11 slip events over 60 s, 0-10 s rotation <= 0.5 deg, integrity), signal 2 (M5's Option A rule over 204 trials with
L0's M4 flag and E1-6m <P> on every move of E1-2 to E1-4), the reading, the margins against R1 + R2's L0 rehearsal maxima,
and the turner-torque report. Writes results/r4/r4_analysis.json."""
from __future__ import annotations

import glob
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r4_run as RUN  # noqa: E402
import r2_analyze as AN2  # noqa: E402

RUN1, RUN2 = RUN.RUN1, RUN.RUN2
AN3, D13A = AN2.AN3, AN2.D13A
REST_SEEDS = tuple(range(19000, 19020))
SEQ_SUBS = ("E1-2", "E1-3", "E1-4")


def load(p) -> dict:
    return json.loads(gzip.decompress(Path(p).read_bytes()))


def rest_rows(root: Path) -> dict:
    out = {}
    for p in sorted((root / RUN.ARM / "E1-1").glob("rest_s*.json.gz")):
        o = load(p)
        rec = o["record"]
        ev = D13A.events(rec)
        out[o["seed"]] = {"e11_pass": bool(AN3.e11_pass(rec)), "n_events": len(ev), "events": ev, "out_of_regime": None,
                          "rest_deg": rec.get("rest_rotation_deg"), "integrity_ok": rec.get("integrity_ok"),
                          "rest_s": o.get("rest_s"), "wall_s": o.get("wall_s")}
    return out


def trial_records(root: Path) -> dict:
    out = {}
    for p in sorted((root / RUN.ARM).glob("*/*.json.gz")):
        if p.parent.name == "E1-1":
            continue
        r = load(p)
        out[(r["experiment"], r["trial_id"])] = r
    return out


def margins(recs: list[dict], rests: list[dict]) -> dict:
    pm = [m for r in recs if r.get("sub_experiment") in SEQ_SUBS for m in r.get("per_move") or []]
    mx = lambda xs: max((x for x in xs if x is not None), default=None)  # noqa: E731
    return {"max_rest_deg_0_10s": mx(v.get("rest_deg") for v in rests),
            "max_nontarget_drift_deg": mx(abs(m["nontarget_drift_deg"]) for m in pm if m.get("nontarget_drift_deg") is not None),
            "max_penetration_mm": mx(m.get("penetration_mm") for m in pm),
            "max_abs_turn_error_deg": mx(abs(m["turn_error_deg"]) for m in pm if m.get("turn_error_deg") is not None),
            "moves": len(pm)}


def rehearsal_margins() -> dict:
    """R1 + R2's L0 R25 records on the rehearsal seeds (the §0 item 8 maxima of the M7 draft)."""
    recs = [load(p) for p in glob.glob(str(HERE / "results/r1/R25/L0/*/*.json.gz")) + glob.glob(str(HERE / "results/r2/R25/L0/*/*.json.gz"))
            if Path(p).parent.name != "E1-1"]
    rests = [{"rest_deg": load(p)["record"].get("rest_rotation_deg")}
             for p in glob.glob(str(HERE / "results/r2/R25/L0/E1-1/*.json.gz"))]
    return margins(recs, rests)


def verdict(rows1: dict, recs: dict) -> dict:
    """Pure: signals and reading from rest rows and trial records (keys (experiment, trial_id))."""
    s1 = AN2.signal1(rows1, "L0") if rows1 else {"signal_met": False}
    s1_complete = sorted(rows1) == list(REST_SEEDS)
    s1_met = bool(s1.get("signal_met")) and s1_complete
    rows = {}
    for e, n in RUN.EXPECTED.items():
        if e == "E1-1":
            rows[e] = {"n": len(rows1), "expected": n, "passed": sum(bool(v["e11_pass"]) and not v["n_events"]
                                                                    for v in rows1.values()),
                       "failed": sorted(f"rest_s{s}" for s, v in rows1.items() if not (v["e11_pass"] and not v["n_events"]))}
            continue
        sub = [r for r in recs.values() if r.get("sub_experiment") == e]
        rows[e] = {"n": len(sub), "expected": n, "passed": sum(bool(r.get("pass")) for r in sub),
                   "failed": sorted(f"{r['trial_id']}: {'; '.join(r.get('fail_reasons') or [])}"
                                    for r in sub if not r.get("pass"))}
    complete = all(r["n"] == r["expected"] for r in rows.values()) and s1_complete
    p_ok = [m.get("e16m_P_ok") for r in recs.values() if r.get("sub_experiment") in SEQ_SUBS
            for m in r.get("per_move") or []]
    e16m = {"moves": len(p_ok), "ok": sum(x is True for x in p_ok)}
    e16m["pass"] = bool(p_ok) and e16m["ok"] == e16m["moves"]
    option_a = bool(complete and all(r["passed"] == r["n"] for r in rows.values()) and e16m["pass"])
    met = s1_met and option_a
    return {"complete": complete, "rows": rows, "e16m": e16m, "signal1": {**s1, "complete": s1_complete},
            "signals": {"1_rest_60s_no_slips": s1_met, "2_option_a_with_slip_rule": option_a, "all_met": met},
            "reading": ("meets the rehearsal signals on fresh seeds (not a candidate)" if met else
                        "incomplete: result to the user" if not complete else
                        "signal(s) missed: negative result kept; the user decides")}


def analyze(root: Path = RUN.OUT) -> dict:
    rows1, recs = rest_rows(root), trial_records(root)
    v = verdict(rows1, recs)
    E = RUN2.er9()
    seqs = [r for r in recs.values() if r.get("sub_experiment") in SEQ_SUBS]
    gate = json.loads((root / "r4_gate.json").read_text()) if (root / "r4_gate.json").exists() else None
    return {"gate": gate, **v, "turner_Nm_E12_E13_E14": E.turner_stats(seqs),
            "margins_fresh": margins(list(recs.values()), list(rows1.values())),
            "margins_rehearsal_R1_R2": rehearsal_margins(),
            "trouble": sorted(f"{e}/{t}" for (e, t), r in recs.items() if RUN2.trouble(r)),
            "rest_wall_s": sorted(v["wall_s"] for v in rows1.values() if v["wall_s"] is not None)}


if __name__ == "__main__":
    out = analyze()
    (RUN.OUT / "r4_analysis.json").write_text(json.dumps(out, indent=1, default=float))
    print("gate", (out["gate"] or {}).get("pass"), "| complete", out["complete"], "| signals", out["signals"])
    print("reading:", out["reading"])
    print("failed", {e: r["failed"] for e, r in out["rows"].items() if r["failed"]})
    print("e16m", out["e16m"], "| torque", {k: out["turner_Nm_E12_E13_E14"].get(k) for k in ("median", "max", "at_clip")})
    print("margins fresh", out["margins_fresh"])
    print("margins rehearsal", out["margins_rehearsal_R1_R2"])
