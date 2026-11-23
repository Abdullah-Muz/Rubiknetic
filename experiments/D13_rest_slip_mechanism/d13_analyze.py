"""D13 analysis (PROTOCOL.md sections 4-5). Reads results/ and the committed records; writes report.md and
analysis.json. Exploratory and unscored.

Usage (WSL, repo root): ~/.venvs/rubiknetic/bin/python experiments/D13_rest_slip_mechanism/d13_analyze.py
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


RUN = _load("d13_run", HERE / "d13_run.py")           # definitions only (nothing runs on import)
D11 = _load("d11_analyze", REPO / "experiments/D11_rest_slip_count/d11_analyze.py")
CASES, SLIP, WIN, THR = RUN.CASES, RUN.SLIP, RUN.WIN, RUN.THR
QUIET = tuple(c for c in CASES if c not in SLIP)
DEFAULT_OPTIONS = {"timestep": 0.0005, "impratio": 10.0, "noslip_iterations": 0, "gravity_z": -9.81}
FACE_ORDER = ("U", "R", "F", "D", "L", "B")


# ---- reading -----------------------------------------------------------------------------------------------------------
def committed(case: str) -> dict:
    return RUN.load_json(RUN.committed_path(case))["rest60"]


def result(variant: str, case: str) -> dict | None:
    p = RUN.result_path(variant, case)
    return RUN.load_json(p) if p.exists() else None


def times(rec: dict) -> np.ndarray:
    t = np.array(rec["timeseries"]["t"])
    return t - t[0] + RUN.SAMPLE_S


def angle(rec: dict, piece: str, axis: str) -> np.ndarray:
    j = rec["members"][axis].index(piece)
    return np.array(rec["timeseries"]["rot_deg"][axis])[:, j]


def events(rec: dict) -> list[dict]:
    return D11.events(rec, times(rec))


def leading(rec: dict) -> dict:
    """The piece and axis with the largest 200 ms change (PROTOCOL section 4), with the change and its window start."""
    t = times(rec)
    best = {"size_deg": -1.0}
    for axis, rows in rec["timeseries"]["rot_deg"].items():
        a = np.array(rows)
        if len(a) <= WIN:
            continue
        dd = np.abs(a[WIN:] - a[:-WIN])
        k, j = np.unravel_index(int(dd.argmax()), dd.shape)
        if dd[k, j] > best["size_deg"]:
            best = {"piece": rec["members"][axis][j], "axis": axis, "size_deg": float(dd[k, j]), "t_start_s": float(t[k])}
    return best


def largest_net(rec: dict) -> dict:
    best = {"net_deg": -1.0}
    for axis, rows in rec["timeseries"]["rot_deg"].items():
        a = np.array(rows)
        net = np.abs(a[-1] - a[0])
        j = int(net.argmax())
        if net[j] > best["net_deg"]:
            best = {"piece": rec["members"][axis][j], "axis": axis, "net_deg": float(net[j])}
    return best


def reference(case: str) -> dict:
    """Reference piece, axis and T_ref from the committed record (PROTOCOL section 3)."""
    rec = committed(case)
    if CASES[case][2] == "slip":
        ld = leading(rec)
        return {"piece": ld["piece"], "axis": ld["axis"], "t_ref_s": ld["t_start_s"], "event_size_deg": ld["size_deg"]}
    ln = largest_net(rec)
    return {"piece": ln["piece"], "axis": ln["axis"], "t_ref_s": float(times(rec)[-1]), "event_size_deg": None}


def change_at(rec: dict, piece: str, axis: str, t_ref: float) -> float:
    t = times(rec)
    i = int(np.abs(t - t_ref).argmin())
    a = angle(rec, piece, axis)
    return float(abs(a[i] - a[0]))


# ---- gate --------------------------------------------------------------------------------------------------------------
def gate() -> dict:
    out = {"cases": {}, "pass": True}
    for case in CASES:
        r = result("V0", case)
        if r is None:
            out["cases"][case] = {"present": False}
            out["pass"] = False
            continue
        rec, ref = r["record"], committed(case)
        same10 = rec["rest_rotation_deg"] == ref["rest_rotation_deg"]
        worst, shapes_ok = 0.0, True
        for axis in ref["timeseries"]["rot_deg"]:
            a, b = np.array(rec["timeseries"]["rot_deg"][axis]), np.array(ref["timeseries"]["rot_deg"][axis])
            if a.shape != b.shape:
                shapes_ok = False
                continue
            worst = max(worst, float(np.abs(a - b).max()))
        ok = bool(same10 and shapes_ok and worst <= 1e-9 and "aborted" not in rec)
        out["cases"][case] = {"present": True, "rest10_deg": rec["rest_rotation_deg"],
                              "committed_rest10_deg": ref["rest_rotation_deg"], "rest10_equal": bool(same10),
                              "shapes_equal": shapes_ok, "max_abs_rot_diff_deg": worst, "pass": ok}
        out["pass"] &= ok
    return out


# ---- measures and rules ------------------------------------------------------------------------------------------------
def options_applied(variant: str, rec: dict) -> bool:
    o = rec["compiled_options"]
    want = dict(DEFAULT_OPTIONS)
    cfg = RUN.VARIANTS[variant]
    want.update({k: v for k, v in cfg.get("params", {}).items()})
    if cfg.get("noslip_iterations"):
        want["noslip_iterations"] = cfg["noslip_iterations"]
    ok = (abs(o["timestep"] - want["timestep"]) < 1e-15 and o["impratio"] == want["impratio"]
          and o["noslip_iterations"] == want["noslip_iterations"] and o["gravity"][2] == want["gravity_z"]
          and o["gravity"][0] == 0.0 and o["gravity"][1] == 0.0)
    order = tuple(rec["setup"]["misalign_deg"])
    ok &= order == (tuple(reversed(FACE_ORDER)) if cfg.get("reverse_setup") else FACE_ORDER)
    return bool(ok)


def run_measures(variant: str, case: str) -> dict | None:
    r = result(variant, case)
    if r is None:
        return None
    rec = r["record"]
    ref = reference(case)
    ev = events(rec)
    ld = leading(rec)
    first = min(ev, key=lambda e: e["t_start_s"]) if ev else None
    out = {"variant": variant, "case": case, "arm": CASES[case][0], "seed": CASES[case][1],
           "options_applied": options_applied(variant, rec), "aborted": rec.get("aborted"),
           "rest10_deg": rec["rest_rotation_deg"], "n_events": len(ev), "has_event": bool(ev),
           "first_event": first, "leading": ld, "wall_s": r["wall_s"],
           "net_ref_change_end_deg": change_at(rec, ref["piece"], ref["axis"], float(times(rec)[-1])),
           "ref_change_at_t_ref_deg": change_at(rec, ref["piece"], ref["axis"], ref["t_ref_s"])}
    if variant in ("V1", "V2", "V3"):
        r0 = result("V0", case)
        earlier = bool(ev and min(e["t_start_s"] for e in ev) < ref["t_ref_s"] - 1e-9)
        rho = None
        if not earlier and r0 is not None:
            base = change_at(r0["record"], ref["piece"], ref["axis"], ref["t_ref_s"])
            rho = out["ref_change_at_t_ref_deg"] / base if base > 0 else None
        out["earlier_event"] = earlier
        out["rho"] = rho
        if CASES[case][2] == "slip" and variant in ("V1", "V2"):
            out["label"] = label(rho, bool(ev))
    return out


def label(rho: float | None, has_event: bool) -> str:
    if has_event:
        return "persists"
    if rho is None:
        return "intermediate"
    if rho >= 0.5:
        return "persists"
    if rho <= 0.25:
        return "suppressed"
    return "intermediate"


def rule(m: dict) -> dict:
    """PROTOCOL section 5 rule for Q1/Q2. m[(variant, case)] = run_measures(...)."""
    v1 = [m.get(("V1", c)) for c in SLIP]
    v2 = [m.get(("V2", c)) for c in SLIP]
    complete = all(x is not None for x in v1 + v2) and all(m.get((v, c)) is not None for v in ("V1", "V2") for c in QUIET)
    n_v2_supp = sum(x is not None and x.get("label") == "suppressed" for x in v2)
    n_v1_rho = sum(x is not None and x.get("rho") is not None and x["rho"] <= 0.5 for x in v1)
    quiet_ev = [f"{v} {c}" for v in ("V1", "V2") for c in QUIET if m.get((v, c)) and m[(v, c)]["has_event"]]
    n_v1_pers = sum(x is not None and x.get("label") == "persists" for x in v1)
    n_v2_pers = sum(x is not None and x.get("label") == "persists" for x in v2)
    r1 = n_v2_supp >= 5 and n_v1_rho >= 5 and not quiet_ev
    r2 = n_v1_pers >= 5 and n_v2_pers >= 5
    outcome = None if not complete else ("1: drift mostly numerical, events depend on it" if r1 and not r2 else
                                         "2: model behaviour" if r2 and not r1 else "3: inconclusive")
    return {"complete": complete, "V2_suppressed": n_v2_supp, "V1_rho_le_0.5": n_v1_rho, "V1_persists": n_v1_pers,
            "V2_persists": n_v2_pers, "quiet_case_events_V1_V2": quiet_ev, "outcome": outcome}


def in_uf_row(piece: str) -> bool:
    code = piece.split("_")[1]
    return code[1] == "n" and code[2] == "p"


def in_d_layer(piece: str) -> bool:
    return piece.split("_")[1][2] == "n"


def q3(m: dict) -> dict:
    g1 = [m.get(("G1", c)) for c in SLIP]
    g2 = [m.get(("G2", c)) for c in SLIP]
    s1 = [m.get(("S1", c)) for c in SLIP]
    complete = all(x is not None for x in g1 + g2 + s1)
    g1_none = sum(x is not None and not x["has_event"] for x in g1)
    g2_ev = [x for x in g2 if x is not None and x["has_event"]]
    g2_d = sum(in_d_layer(x["leading"]["piece"]) for x in g2_ev)
    s1_ev = [x for x in s1 if x is not None and x["has_event"]]
    s1_out = sum(not in_uf_row(x["leading"]["piece"]) for x in s1_ev)
    gl = g1_none >= 5 or g2_d >= 4
    sl = s1_out >= 4
    labels = [n for n, f in (("gravity-linked", gl), ("setup-linked", sl)) if f] or ["not explained"]
    return {"complete": complete, "G1_runs_without_event": g1_none, "G2_runs_with_event": len(g2_ev),
            "G2_leading_in_D_layer": g2_d, "S1_runs_with_event": len(s1_ev), "S1_leading_outside_UF_row": s1_out,
            "labels": labels if complete else None}


def creep_share(case: str) -> dict | None:
    r = result("V0", case)
    if r is None:
        return None
    rec = r["record"]
    ref = reference(case)
    i = int(np.abs(times(rec) - ref["t_ref_s"]).argmin())
    k = rec["piece_bodies"].index(ref["piece"])
    cr = rec["timeseries"]["piece_creep_mm"][i][k]
    sl = rec["timeseries"]["piece_slide_mm"][i][k]
    use = np.array(rec["timeseries"]["piece_cone_use_max"])[: i + 1, k]
    return {"creep_mm": cr, "slide_mm": sl, "share": cr / (cr + sl) if cr + sl > 0 else None,
            "cone_use_max_before_t_ref_median": float(np.median(use)), "cone_use_max_before_t_ref_max": float(use.max())}


# ---- report ------------------------------------------------------------------------------------------------------------
def fmt(x, nd=3):
    return "–" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def main() -> None:
    g = gate()
    m = {(v, c): run_measures(v, c) for v, c in RUN.all_runs()}
    refs = {c: reference(c) for c in CASES}
    rl = rule(m)
    q = q3(m)
    cs = {c: creep_share(c) for c in CASES}
    n_done = sum(x is not None for x in m.values())
    lines = ["# D13 report (generated by d13_analyze.py)", "",
             f"Runs present: {n_done} / {len(m)}. Reproduction gate: **{'PASS' if g['pass'] else 'FAIL'}**.", "",
             "## Cases (reference from the committed records)", "",
             "| Case | Arm | Seed | Piece / axis | T_ref (s) | Committed event (°) |", "|---|---|---|---|---|---|"]
    for c, r in refs.items():
        lines.append(f"| {c} | {CASES[c][0]} | {CASES[c][1]} | `{r['piece'][6:]}` / {r['axis']} | {r['t_ref_s']:.3f} | "
                     f"{fmt(r['event_size_deg'])} |")
    lines += ["", "## Gate (V0 against the committed records)", "",
              "| Case | rest 0–10 s (°) | committed (°) | equal | max abs rot diff (°) | pass |", "|---|---|---|---|---|---|"]
    for c, x in g["cases"].items():
        if not x["present"]:
            lines.append(f"| {c} | missing | | | | False |")
            continue
        lines.append(f"| {c} | {x['rest10_deg']:.10f} | {x['committed_rest10_deg']:.10f} | {x['rest10_equal']} | "
                     f"{x['max_abs_rot_diff_deg']:.2e} | {x['pass']} |")
    lines += ["", "## Runs", "",
              "| Variant | Case | options applied | rest 0–10 s (°) | events | first event (t s, piece/axis, °) | "
              "ref change at T_ref (°) | ρ | label | wall (s) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for (v, c), x in m.items():
        if x is None:
            lines.append(f"| {v} | {c} | not run | | | | | | | |")
            continue
        fe = x["first_event"]
        fes = f"{fe['t_start_s']:.2f}, `{fe['cubie'][6:]}`, {fe['size_deg']:.3f}" if fe else "–"
        rho = "earlier event" if x.get("earlier_event") else fmt(x.get("rho"))
        lines.append(f"| {v} | {c} | {x['options_applied']} | {x['rest10_deg']:.4f} | {x['n_events']} | {fes} | "
                     f"{x['ref_change_at_t_ref_deg']:.4f} | {rho} | {x.get('label', '')} | {x['wall_s']:.0f} |")
    lines += ["", "## Rule for Q1 and Q2 (PROTOCOL section 5)", "",
              f"- V2 *suppressed*: {rl['V2_suppressed']} / 6; V1 ρ ≤ 0.5: {rl['V1_rho_le_0.5']} / 6; "
              f"events in quiet cases under V1/V2: {rl['quiet_case_events_V1_V2'] or 'none'}",
              f"- V1 *persists*: {rl['V1_persists']} / 6; V2 *persists*: {rl['V2_persists']} / 6",
              f"- **Outcome: {rl['outcome'] or 'incomplete'}**", "",
              "## Q3 labels (descriptive)", "",
              f"- G1 runs without an event: {q['G1_runs_without_event']} / 6; G2 runs with an event: "
              f"{q['G2_runs_with_event']}, leading piece in D layer: {q['G2_leading_in_D_layer']}",
              f"- S1 runs with an event: {q['S1_runs_with_event']}, leading piece outside the U∩F row: "
              f"{q['S1_leading_outside_UF_row']}",
              f"- **Labels: {', '.join(q['labels']) if q['labels'] else 'incomplete'}**", "",
              "## Q4 creep share (V0, reported only)", "",
              "| Case | creep (mm) | sliding (mm) | creep share | cone use, median of per-sample max | cone use, max |",
              "|---|---|---|---|---|---|"]
    for c, x in cs.items():
        if x is None:
            lines.append(f"| {c} | not run | | | | |")
            continue
        lines.append(f"| {c} | {x['creep_mm']:.4g} | {x['slide_mm']:.4g} | {fmt(x['share'])} | "
                     f"{x['cone_use_max_before_t_ref_median']:.3f} | {x['cone_use_max_before_t_ref_max']:.3f} |")
    (HERE / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    json.dump({"gate": g, "references": refs, "runs": {f"{v}_{c}": x for (v, c), x in m.items()}, "rule": rl,
               "q3": q, "creep_share": cs}, open(HERE / "analysis.json", "w"), indent=1, default=float)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
