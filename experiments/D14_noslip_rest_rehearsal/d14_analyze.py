"""D14 analysis (PROTOCOL.md sections 4-5). Reads results/, the D13 V2 records and the committed frozen-setting
records; writes report.md and analysis.json. Exploratory and unscored.

Usage (WSL, repo root): ~/.venvs/rubiknetic/bin/python experiments/D14_noslip_rest_rehearsal/d14_analyze.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


RUN = _load("d14_run", HERE / "d14_run.py")
D13 = RUN.D13
D13A = _load("d13_analyze", REPO / "experiments/D13_rest_slip_mechanism/d13_analyze.py")
D11 = D13A.D11
REST_LIMIT_DEG = 0.5


def result(arm: str, seed: int) -> dict | None:
    p = RUN.result_path(arm, seed)
    return D13.load_json(p) if p.exists() else None


def frozen(arm: str, seed: int) -> dict:
    return D13.load_json(RUN.committed_frozen_path(arm, seed))["rest60"]


# ---- gate ----------------------------------------------------------------------------------------------------------
def gate() -> dict:
    out = {"cases": {}, "pass": True}
    for (arm, seed), case in RUN.GATE.items():
        r = result(arm, seed)
        key = f"{arm}_s{seed}"
        if r is None:
            out["cases"][key] = {"present": False}
            out["pass"] = False
            continue
        ref = D13.load_json(D13.result_path("V2", case))["record"]
        rec = r["record"]
        worst, shapes = 0.0, True
        for axis, rows in ref["timeseries"]["rot_deg"].items():
            a, b = np.array(rec["timeseries"]["rot_deg"][axis]), np.array(rows)
            if a.shape != b.shape:
                shapes = False
                continue
            worst = max(worst, float(np.abs(a - b).max()))
        same10 = rec["rest_rotation_deg"] == ref["rest_rotation_deg"]
        ok = bool(shapes and same10 and worst == 0.0 and "aborted" not in rec)
        out["cases"][key] = {"present": True, "d13_case": case, "rest10_deg": rec["rest_rotation_deg"],
                             "d13_rest10_deg": ref["rest_rotation_deg"], "rest10_equal": bool(same10),
                             "max_abs_rot_diff_deg": worst, "pass": ok}
        out["pass"] &= ok
    return out


# ---- per run ---------------------------------------------------------------------------------------------------------
def validity(arm: str, r: dict) -> dict:
    if arm == "L0":
        st = r["record"].get("magnet_stats") or {}
        return {"rule": "M4 legacy statistics (reported only)", "out_of_regime": None,
                "max_near_tilt_deg": st.get("max_near_tilt_deg"), "near_perpendicular": st.get("near_perpendicular"),
                "clamped_z": st.get("clamped_z")}
    ER9 = _load("er9g_run", REPO / "experiments/ER9_anchored_core_layouts/er9g_run.py")
    v = ER9.verdict("E1-1", [], r["record"].get("class_stats"), r["d_val_deg"])
    return {"rule": "Part G G.4 per-class", "out_of_regime": v["out_of_regime"], "reasons": v["out_of_regime_reasons"]}


def measures(arm: str, seed: int) -> dict | None:
    r = result(arm, seed)
    if r is None:
        return None
    rec = r["record"]
    ev = D13A.events(rec)
    ld = D13A.leading(rec)
    net = D13A.largest_net(rec)
    fz = frozen(arm, seed)
    fev = D13A.events(fz)
    ts = rec["timeseries"]
    return {"arm": arm, "seed": seed, "rest10_deg": rec["rest_rotation_deg"], "n_events": len(ev),
            "events": ev, "largest_200ms_deg": ld["size_deg"], "largest_200ms_piece": f"{ld['piece']}/{ld['axis']}",
            "largest_net_deg": net["net_deg"], "aborted": rec.get("aborted"),
            "numerical_failures": rec.get("numerical_failures") or [],
            "noslip_iterations": rec["compiled_options"]["noslip_iterations"],
            "solver_max_iter": int(max(ts["solver_max_iter"])), "solver_limit_hits": int(sum(ts["solver_limit_hits"])),
            "validity": validity(arm, r), "wall_s": r["wall_s"],
            "frozen": {"rest10_deg": fz["rest_rotation_deg"], "n_events": len(fev),
                       "largest_200ms_deg": D13A.leading(fz)["size_deg"], "largest_net_deg": D13A.largest_net(fz)["net_deg"]}}


def arm_signal(ms: list) -> dict:
    present = [m for m in ms if m is not None]
    complete = len(present) == len(RUN.SEEDS)
    rest_ok = all(m["rest10_deg"] <= REST_LIMIT_DEG for m in present)
    slip_seeds = [m["seed"] for m in present if m["n_events"]]
    integrity = [m["seed"] for m in present if m["aborted"] or m["numerical_failures"]]
    oor = [m["seed"] for m in present                                          # L0: legacy only (None)
           if m["arm"] != "L0" and m["validity"]["out_of_regime"] is not False]  # PG: missing stats count
    wrong_setting = [m["seed"] for m in present if m["noslip_iterations"] != 10]
    met = bool(complete and rest_ok and not slip_seeds and not integrity and not oor and not wrong_setting)
    return {"complete": complete, "n": len(present), "rest10_max_deg": max((m["rest10_deg"] for m in present), default=None),
            "all_rest_le_0.5": rest_ok, "slip_seeds": slip_seeds, "integrity_failures": integrity,
            "out_of_regime_seeds": oor, "wrong_setting_seeds": wrong_setting, "signal_met": met,
            "paired_rest10_lower_than_frozen": sum(m["rest10_deg"] < m["frozen"]["rest10_deg"] for m in present),
            "frozen_slip_seeds": [m["seed"] for m in present if m["frozen"]["n_events"]]}


def main() -> None:
    g = gate()
    per = {arm: [measures(arm, s) for s in RUN.SEEDS] for arm in RUN.ARMS}
    sig = {arm: arm_signal(v) for arm, v in per.items()}
    L = ["# D14 report (generated by d14_analyze.py)", "",
         f"Runs present: {sum(m is not None for v in per.values() for m in v)} / {len(RUN.all_runs())}. "
         f"Gate (D13 V2 reproduction): **{'PASS' if g['pass'] else 'FAIL'}**.", "",
         "## Gate", "", "| Run | D13 case | rest 0–10 s (°) | D13 V2 (°) | max abs rot diff (°) | pass |", "|---|---|---|---|---|---|"]
    for k, x in g["cases"].items():
        L.append(f"| {k} | missing | | | | False |" if not x["present"] else
                 f"| {k} | {x['d13_case']} | {x['rest10_deg']:.10f} | {x['d13_rest10_deg']:.10f} | "
                 f"{x['max_abs_rot_diff_deg']:.1e} | {x['pass']} |")
    L += ["", "## Stage 1 signal per arm (PROTOCOL section 5)", "",
          "| Arm | runs | max rest 0–10 s (°) | slip seeds | integrity failures | out of regime | signal met | "
          "rest lower than frozen (paired) | frozen slip seeds |", "|---|---|---|---|---|---|---|---|---|"]
    for arm, s in sig.items():
        L.append(f"| {arm} | {s['n']} / 20 | {D13A.fmt(s['rest10_max_deg'], 4)} | {s['slip_seeds'] or 'none'} | "
                 f"{s['integrity_failures'] or 'none'} | {s['out_of_regime_seeds'] or 'none'} | **{s['signal_met']}** | "
                 f"{s['paired_rest10_lower_than_frozen']} / {s['n']} | {s['frozen_slip_seeds'] or 'none'} |")
    L += ["", "## Runs", "",
          "| Arm | Seed | rest 0–10 s (°) | frozen (°) | events | largest 200 ms (°) | frozen largest 200 ms (°) | "
          "largest net (°) | frozen net (°) | solver max iter | validity | wall (s) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm, v in per.items():
        for m in v:
            if m is None:
                continue
            val = m["validity"]["out_of_regime"]
            L.append(f"| {arm} | {m['seed']} | {m['rest10_deg']:.4f} | {m['frozen']['rest10_deg']:.4f} | {m['n_events']} | "
                     f"{m['largest_200ms_deg']:.4f} | {m['frozen']['largest_200ms_deg']:.4f} | {m['largest_net_deg']:.4f} | "
                     f"{m['frozen']['largest_net_deg']:.4f} | {m['solver_max_iter']} | "
                     f"{'legacy' if val is None else ('OUT' if val else 'ok')} | {m['wall_s']:.0f} |")
    (HERE / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    json.dump({"gate": g, "signal": sig, "runs": {f"{a}_s{m['seed']}": m for a, v in per.items() for m in v if m}},
              open(HERE / "analysis.json", "w"), indent=1, default=float)
    print("\n".join(L[:30]))


if __name__ == "__main__":
    main()
