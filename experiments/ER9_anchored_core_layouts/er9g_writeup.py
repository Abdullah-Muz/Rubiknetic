"""ER9 Part G write-up tables (PROTOCOL.md Part G: G.6, G.8, G.9; DECISION_LOG P-70). Reporting only.

Reads, never writes:
  results/hybrid_g/probe/report.json          written by `er9g_run.py report` (G.8 signals, reported items, selection)
  results/hybrid_g/static/*.json              P1-P4 (committed static pre-checks)
  results/hybrid_g/selfcheck*.json, replay_selfcheck.json
  results/hybrid_g/{probe,rest40}/<arm>/E1-1/*.json.gz   only the field rest_rotation_deg (the report has no rest
                                              maximum per arm; see the note printed under table (b))
  results/hybrid_g/full/<arm>/report.json     only if a full rehearsal was run (G.9)
  results/probe/report.json                   Parts B-D rows (L0, C52, W3 on the 106 probe seeds)
  results/hybrid/probe/report.json            Part E rows (HB1-HB3 on the same seeds)
  ../ER7_core_magnet_rehearsal/results/analysis.json   ER7 L0 / C52 slip counts over 20 rest seeds
and prints Markdown tables to paste into SUMMARY.md. Every number is a field of one of these files (named above each
table) or plain arithmetic on such fields (labelled "derived"). No interpretation beyond the wording that G.8, G.9 and
P-70 fix.

Run (WSL, repo root), after `er9g_run.py report`:
  ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9g_writeup.py            # all tables
  ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9g_writeup.py --static-only
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ROOT = HERE / "results" / "hybrid_g"
W3_REPORT = HERE / "results" / "probe" / "report.json"
HB_REPORT = HERE / "results" / "hybrid" / "probe" / "report.json"
ER7_ANALYSIS = REPO / "experiments" / "ER7_core_magnet_rehearsal" / "results" / "analysis.json"

ARMS = ("PG8", "PG20", "PG20r")             # report order; PG20r only if the report has it (U4)
REF_ROWS = ("L0", "C52", "W3", "HB1", "HB2", "HB3")
P2_ROWS = (("PG8", "N35"), ("PG8", "N42"), ("PG8", "N52"), ("PG20", "N35"), ("PG20", "N42"), ("PG20", "N52"),
           ("PG20r", "N52"), ("L0", "N35"), ("C52", "N52"))
L0_SLIP_SEEDS = ("16003", "16005")
SCORED_SNAP_DEG = 3.0                       # G.8 signal 1: release offsets of 3 deg or more
P70_MEDIAN_NM = 0.45                        # P-70 item 3
P70_ITEM2_CLASSES = frozenset({"X", "PCoff"})   # "cross-type or off-path pairs"
P1_ENVELOPE_TEXT = "cross-type pairs 4.25-8 mm, path deviation up to 10.4 deg"

# G.4's per-trial rule, condition by condition (the same list as er9g_run.oor_reasons; tested against
# er9g_stats.out_of_regime). (class, field, limit): exceeded if value > limit.
G4_CONDITIONS = (
    ("CE", "CE_max_near_tilt_deg", 5.0), ("CE", "CE_clamped_z", 0), ("CE", "CE_near_perpendicular", 0),
    ("PCon", "PCon_max_near_tilt_deg", 20.0), ("PCon", "PCon_near_perpendicular", 0),
    ("PCoff", "PCoff_max_near_tilt_deg", 7.5), ("PCoff", "PCoff_clamped_z", 0),
    ("PCoff", "PCoff_near_perpendicular", 0),
    ("PP3", "PP3_max_near_tilt_deg", 7.5), ("PP3", "PP3_clamped_z", 0), ("PP3", "PP3_near_perpendicular", 0),
    ("X", "cross_near", 0))
CLASSES = ("CE", "PCon", "PCoff", "PP3", "X")
CLASS_FIELDS = ("near_evals", "near_perpendicular", "max_near_tilt_deg", "clamped_z", "min_centre_distance_mm")

P70_TEXT = {
    1: "if neither arm meets all four probe signals, the only follow-up probe is PG20 at N42 and N35 under the same "
       "signals and selection rule, after one PG20 snap-back diagnostic",
    2: "if signal 4 fails only through cross-type or off-path pairs, any further force-law check uses the envelope "
       f"fixed from P1 ({P1_ENVELOPE_TEXT}), not one fitted to the probe's poses, and L0's 12.59 deg in ER7 is first "
       "located by sub-experiment",
    3: "before G.9's full rehearsal, pause for the user if the selected arm's median E1-2 turner torque is >= 0.45 "
       "N.m or any move reaches the 1 N.m clip; the arm not selected gets no full rehearsal",
}
G9_READING = {   # PROTOCOL.md G.9 "Reading (fixed now)", verbatim in substance
    "all_no_clip": "All three met, no move at the clip: reported as \"meets the rehearsal signals\", not as a "
                   "candidate; put to the user with what it still lacks for a gate G1 path (fit under U1; turner "
                   "torque against the realism reference; independence from selection; E1-7 coverage incl. the 1.5x "
                   "ideal-magnet arm; the composite system's review status; the lateral-offset disclosure)",
    "all_clip": "All three met, with moves at the clip: reported beside W3; the choice goes to the user",
    "1": "Signal 1 missed: INFERENCE, the static warning of G.2 holds. Reported against L0 trial by trial, with the "
         "60-seed slip comparison",
    "2": "Signal 2 missed in E1-5s: reported with each piece's leftover spin, against L0 and C52",
    "3": "Signal 3 missed: reported by class and by d. If only PC-off or X evaluations caused it, accepting them "
         "would be an amendment of the P-60 kind, which is the user's decision; it is not made here",
    "any": "Any miss: the negative result is kept and reported (CLAUDE.md)",
}


# ---- helpers -------------------------------------------------------------------------------------------------------
def read_json(p: Path):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def rel(p: Path) -> str:
    """Paths as SUMMARY.md writes them: relative to this experiment's folder, else to the repository."""
    p = Path(p).resolve()
    for base in (HERE, REPO):
        try:
            return p.relative_to(base).as_posix()
        except ValueError:
            continue
    return p.as_posix()


def f(x, nd: int = 3, unit: str = "") -> str:
    """Number formatting; None -> 'n/a'. Very small magnitudes in scientific notation."""
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, int):
        return f"{x:,}{unit}"
    if isinstance(x, float) and (math.isinf(x) or math.isnan(x)):
        return str(x)
    if x != 0 and abs(x) < 10 ** (-nd):
        return f"{x:.1e}{unit}"
    return f"{x:,.{nd}f}{unit}"


def yn(b) -> str:
    return "n/a" if b is None else ("met" if b else "**not met**")


def table(header: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def fact(*sources: str) -> str:
    return "FACT — source: " + "; ".join(sources) + "."


def report_arms(rep: dict) -> list[str]:
    return [a for a in ARMS if a in (rep.get("arms") or {})]


# ---- G.4 reasons from the aggregated class stats -------------------------------------------------------------------
def exceeded_conditions(stats: dict | None) -> list[tuple[str, str, float, float]]:
    """[(class, field, value, limit)] of G.4 conditions exceeded in `stats` (a trial's class_stats, or the report's
    class_stats_max: maxima of tilts, sums of counts, so a condition exceeded there was exceeded in at least one
    trial, and no condition is exceeded there that no trial exceeded)."""
    if not stats:
        return []
    out = []
    for cls, key, lim in G4_CONDITIONS:
        v = stats.get(key)
        if v is not None and v > lim:
            out.append((cls, key, v, lim))
    return out


def reasons_by_class(stats: dict | None) -> str:
    ex = exceeded_conditions(stats)
    if not ex:
        return "none"
    by: dict[str, list[str]] = {}
    for cls, key, v, lim in ex:
        by.setdefault(cls, []).append(f"{key} {f(v, 2) if isinstance(v, float) else v} > {lim:g}")
    return "; ".join(f"{c}: " + ", ".join(by[c]) for c in CLASSES if c in by)


# ---- rest values from records (the report has no per-arm rest maximum) ---------------------------------------------
def rest_values(root: Path, mode: str, arm: str) -> dict[int, float] | None:
    """{seed: rest_rotation_deg} from <root>/<mode>/<arm>/E1-1/*.json.gz; None if the folder does not exist."""
    d = Path(root) / mode / arm / "E1-1"
    if not d.is_dir():
        return None
    out = {}
    for p in sorted(d.glob("*.json.gz")):
        r = json.loads(gzip.decompress(p.read_bytes()))
        seed = r.get("seed", (r.get("spec") or {}).get("seed"))
        out[int(seed)] = float(r["rest_rotation_deg"])
    return out


# ---- (a) static pre-checks -----------------------------------------------------------------------------------------
def static_tables(root: Path = ROOT) -> str:
    st = Path(root) / "static"
    out = ["### (a) Self-checks and static pre-checks (G.5, G.6)", ""]
    sc, ss, rp = (read_json(root / "selfcheck.json") or {}, read_json(root / "selfcheck_static.json") or {},
                  read_json(root / "replay_selfcheck.json") or {})
    gs5 = ss.get("GS5", {})
    h48 = gs5.get("48_only", {})
    out.append(fact(f"`{rel(root / 'selfcheck.json')}` (GS1, GS2, GS4 `.pass`)",
                    f"`{rel(root / 'selfcheck_static.json')}` (GS3, GS3b, GS6 `.pass`; GS5 fields named)",
                    f"`{rel(root / 'replay_selfcheck.json')}` (`pass`, `snap_reported_pass`)"))
    out.append("")
    rows = [[k, f(sc.get(k, {}).get("pass"))] for k in ("GS1", "GS2", "GS4")]
    rows += [[k, f(ss.get(k, {}).get("pass"))] for k in ("GS3", "GS3b", "GS6")]
    rows.append(["GS5 (read per Part G deviation 1)",
                 f"40_only.pass {f(gs5.get('40_only', {}).get('pass'))}; 48_only.with_er3_magnet_order.pass "
                 f"{f(h48.get('with_er3_magnet_order', {}).get('pass'))} (rel. diff "
                 f"{f(h48.get('with_er3_magnet_order', {}).get('rel_diff_vs_er3'), 2)}); 48_only.probe5_pass "
                 f"{f(h48.get('probe5_pass'))}; layout()-order er3_row_pass {f(h48.get('er3_row_pass'))} (rel. diff "
                 f"{f(h48.get('rel_diff_vs_er3'), 4)}; reported, not required)"])
    rows.append(["Replay tool self-check (G.7)", f"pass {f(rp.get('pass'))}; snap replays {f(rp.get('snap_reported_pass'))}"])
    out += [table(["Check", "Result"], rows), ""]

    # P1
    p1 = {a: read_json(st / f"P1_{a}.json") for a in ("PG8", "PG20")}
    out.append("**P1, kinematic scan** — " + fact(*(f"`{rel(st / f'P1_{a}.json')}` (`stops`, `stopped`, "
                                                  f"`e15_like.combined.stats`)" for a in p1)))
    out.append("")
    rules = []
    for a in p1:
        for s in (p1[a] or {}).get("stops", []):
            if s["rule"] not in rules:
                rules.append(s["rule"])
    rows = []
    for rule in rules:
        row = [rule]
        for a in p1:
            s = next((x for x in (p1[a] or {}).get("stops", []) if x["rule"] == rule), None)
            if s is None:
                row.append("n/a")
                continue
            v = f(s["value"], 3) if isinstance(s["value"], float) else str(s["value"])
            extra = f", margin {f(s['margin'], 3)}" if "margin" in s else ""
            extra += f", min centre {f(s['min_centre_distance_mm'], 3)} mm" if "min_centre_distance_mm" in s else ""
            row.append(f"{v} (limit {s['limit']}{extra}){' **STOP**' if s.get('stop') else ''}")
        rows.append(row)
    rows.append(["**Arm stopped by P1**"] + [f((p1[a] or {}).get("stopped")) for a in p1])
    out += [table(["Stop rule (rigid face turns)"] + list(p1), rows), ""]
    keys = [("cross_near (X near evaluations)", "cross_near"), ("X min centre distance (mm)", "X_min_centre_distance_mm"),
            ("PC largest path deviation d (deg)", "PC_max_path_dev_deg"),
            ("PCon largest near tilt (deg)", "PCon_max_near_tilt_deg"),
            ("CE largest near tilt (deg)", "CE_max_near_tilt_deg"), ("CE near perpendicular", "CE_near_perpendicular"),
            ("CE clamped z", "CE_clamped_z"), ("PP3 near evaluations", "PP3_near_evals")]
    rows = [[lab] + [f(((p1[a] or {}).get("e15_like", {}).get("combined", {}).get("stats", {})).get(k), 3)
                     for a in p1] for lab, k in keys]
    out += ["E1-5-like rigid poses (U offset ±1..20 deg, then R 0..90 deg; reported only, contacts ignored, G.6):", "",
            table(["Quantity"] + list(p1), rows), ""]

    # P2
    out.append("**P2, stiffness** — " + fact("`results/hybrid_g/static/P2_<arm>_<grade>.json` (`stopped`, "
                                            "`full.n_zero`, `full.collective_twist_mNm_per_rad`, `full.n_negative`, "
                                            "`er3.mode_min`, `er3.min_layer`, `er3.turn_peak_Nm`, "
                                            "`probe5.*.restoring_stiffness_mNm_per_rad`)") +
               " Stiffness in mN·m/rad, layer in N·m/rad. The stop rule applies to arms only; L0 and C52 are "
               "reference rows (GS5).")
    out.append("")
    rows = []
    for arm, g in P2_ROWS:
        d = read_json(st / f"P2_{arm}_{g}.json")
        if d is None:
            rows.append([f"{arm} {g}"] + ["not recorded"] + [""] * 9)
            continue
        mm, p5 = d["er3"]["mode_min"], d["probe5"]
        k = lambda n: p5[n]["restoring_stiffness_mNm_per_rad"]  # noqa: E731
        rows.append([f"{arm} {g}", f(d["stopped"]), d["full"]["n_zero"], f(d["full"]["collective_twist_mNm_per_rad"], 0),
                     d["full"]["n_negative"],
                     f"{f(mm['edge_spin'], 0)} / {f(mm['edge_slide'], 0)} / {f(mm['edge_cross'], 0)}",
                     f"{f(mm['corner_twist'], 0)} / {f(mm['corner_tangential'], 0)}", f(d["er3"]["min_layer"], 2),
                     f(d["er3"]["turn_peak_Nm"], 3),
                     f"{f(k('edge n0p'), 0)} / {f(k('corner nnp'), 0)} / **{f(k('pair nnp + n0p'), 0)}**",
                     f(k("whole U layer"), 0)])
    out += [table(["Row", "Stopped (field)", "Zero modes", "Collective twist", "Negative eigenvalues",
                   "Edge spin / slide / cross (min)", "Corner twist / tangential (min)", "Layer", "U-turn peak (N·m)",
                   "Probe 5: edge / corner / corner+edge cluster", "Probe 5: U layer"], rows), ""]

    # P3
    out.append("**P3, fit (hard stop per Part G deviation 2)** — " +
               fact(*(f"`{rel(st / f'P3_{a}.json')}` (`hard_stop`, `protrusion`, `surface_gaps`, `items`)"
                      for a in ("PG8", "PG20"))))
    out.append("")
    rows = []
    for a in ("PG8", "PG20"):
        d = read_json(st / f"P3_{a}.json")
        if d is None:
            rows.append([a, "not recorded", "", "", ""])
            continue
        sg = d["surface_gaps"]
        rows.append([a, f(d["hard_stop"]), f(d["protrusion"]),
                     f"{f(sg['min_surface_gap_mm'], 3)} ({' / '.join(sg['min_pair']['bodies'])}; "
                     f"{sg['pairs_sampled']} of {sg['pairs_total']} pairs sampled, rest bounded by spheres)",
                     "; ".join(f"{it['item']}: {it['value']}" for it in d["items"])])
    out += [table(["Arm", "Hard stop", "Protrusion", "Min surface gap at home (mm)", "Items (committed side checks)"],
                  rows), ""]

    # P4
    p40 = read_json(st / "P4_0.json")
    out.append("**P4, force-law checks (ER5 V3-turn pass rule)** — " +
               fact(f"`{rel(st / 'P4_0.json')}` (`label`, `verdict`)",
                    "`results/hybrid_g/static/P4d_<arm>.json` (`label`, `verdict`)"))
    out.append("")
    rows = []
    if p40:
        v = p40["verdict"]
        rows.append(["P4.0 (PG8, 8 corner core magnets)", p40.get("label"), f(v["pass"]),
                     f"worst F err {f(100 * v['worst_F_err_rel_Fn'], 2)} % of Fn (limit 5 %); worst T err "
                     f"{f(v['worst_T_err_Nm'], 7)} N·m (tol {f(v['T_tol_Nm'], 7)}); max near tilt "
                     f"{f(v['max_near_tilt_deg'], 2)} deg; pairs beyond 45 deg {v['pairs_beyond_45deg_total']}",
                     f(v["summed_run_s"] / 3600, 2)])
    else:
        rows.append(["P4.0 (PG8)", "not recorded", "", "", ""])
    for a in ("PG8", "PG20"):
        d = read_json(st / f"P4d_{a}.json")
        if d is None:
            rows.append([f"P4.d {a}", f"not recorded (`P4d_{a}.json` absent)", "", "D_val not fixed", ""])
            continue
        v = d["verdict"]
        rows.append([f"P4.d {a}", d.get("label"), f"stop_arm {f(v['stop_arm'])}",
                     f"**D_val = {f(v['D_val_deg'], 1)} deg**; status {v['status']}; halted at "
                     f"{f(v.get('halted_at_d_deg'), 1)}; budget reached {f(v.get('budget_reached'))}",
                     f(v["summed_run_s"] / 3600, 2)])
    out += [table(["Check", "Label", "Result", "Detail", "Summed run (h)"], rows), ""]
    return "\n".join(out)


# ---- (b) probe signals ---------------------------------------------------------------------------------------------
def snap_max(snap_back: list, scored_only: bool) -> float | None:
    v = [abs(e) for _, d, e, _ in snap_back if e is not None and (not scored_only or abs(d) >= SCORED_SNAP_DEG)]
    return max(v) if v else None


def signals_table(rep: dict, rest: dict) -> str:
    out = ["### (b) Probe signals (G.8; ER7's criteria, G.4 per-class rule at the D_val in force)", "",
           fact("`results/hybrid_g/probe/report.json` → `arms.<arm>.signals`, `.slip_seeds_0_60s`, `.snap_back`, "
                "`.out_of_regime_trials`, `.class_stats_max`, `.failed`; `D_val.<arm>`",
                "rest max: derived, max of `rest_rotation_deg` over `results/hybrid_g/probe/<arm>/E1-1/*.json.gz` "
                "(report.json carries no per-arm rest maximum)"), ""]
    rows = []
    for a in report_arms(rep):
        r = rep["arms"][a]
        s = r["signals"]
        rv = rest.get(a)
        rmax = max(rv.values()) if rv else None
        oor = r.get("out_of_regime_trials", [])
        rows.append([a, r["n"], f(rep.get("D_val", {}).get(a), 1),
                     f"{yn(s['1_snap_scored_all_pass'])} (max \\|err\\| {f(snap_max(r['snap_back'], True), 3)} deg)",
                     f"{yn(s['2_rest_le_0.5_and_no_slips'])} (rest max {f(rmax, 3)} deg; slip seeds "
                     f"{r['slip_seeds_0_60s'] or 'none'})",
                     f"{yn(s['3_e12_e15_all_pass'])}",
                     f"{yn(s['4_no_operational_trial_out_of_regime'])} ({len(oor)} of {r['n']} trials out of regime; "
                     f"{reasons_by_class(r.get('class_stats_max'))})",
                     "**yes**" if s["all_met"] else "no", f(s["complete"])])
    out.append(table(["Arm", "Records", "D_val (deg)", "1 snap-back (scored, \\|Δ\\| ≥ 3°)",
                      "2 rest ≤ 0.5° and 0/20 D11 slips over 60 s", "3 E1-2 and E1-5 all pass",
                      "4 no operational trial out of regime (reasons by class)", "All four", "Complete (106)"], rows))
    out.append("")
    out.append("Reasons by class are the G.4 conditions exceeded in `class_stats_max` (tilts are maxima and counts are "
               "sums over the arm's probe trials, so each listed condition was exceeded in at least one trial). "
               "Per-trial reasons are not in report.json.")
    fails = {a: rep["arms"][a].get("failed", []) for a in report_arms(rep)}
    for a, fl in fails.items():
        out.append(f"- {a} failed trials (Part G verdict at D_val): {', '.join(fl) if fl else 'none'}")
    for a in report_arms(rep):
        oor = rep["arms"][a].get("out_of_regime_trials", [])
        if oor:
            out.append(f"- {a} out-of-regime trials: {', '.join(oor)}")
    out.append("")
    return "\n".join(out)


# ---- (c) reported items beside the references ----------------------------------------------------------------------
def reference_rows(w3: dict | None, hb: dict | None) -> dict:
    """Parts B-E rows on the 106 probe seeds: rest max, snap-back max |err| (rounded to 3 dp in those reports),
    summed wall time."""
    out = {}
    for src, names in ((w3, ("L0", "C52", "W3")), (hb, ("HB1", "HB2", "HB3"))):
        for n in names:
            r = (src or {}).get(n)
            if not r:
                continue
            by = r["snap_abs_err_by_delta"]
            out[n] = {"rest_max_deg": r["rest_max_deg"],
                      "snap_max_scored": max(v for d, vs in by.items() if float(d) >= SCORED_SNAP_DEG for v in vs),
                      "snap_max_all": max(v for vs in by.values() for v in vs),
                      "wall_h": r["wall_s_total"] / 3600, "e12": r.get("e12_turner_Nm")}
    return out


def turner_cells(t: dict | None) -> list[str]:
    if not t:
        return ["n/a"] * 4
    return [f"{f(t['median'], 3)} / {f(t['p99'], 3)} / {f(t['max'], 3)}", str(t["above_0.45"]), str(t["above_0.5"]),
            f"{t['at_clip']} (of {t['n_moves']})"]


def reported_table(rep: dict, rest: dict, refs: dict) -> str:
    out = ["### (c) Reported items beside L0, C52, W3 and HB1–HB3 on the same 106 seeds (G.8; not signals)", "",
           fact("PG arms: `results/hybrid_g/probe/report.json` → `arms.<arm>.turner_E1-2_Nm`, `.snap_back`, `.wall_h`; "
                "rest max derived from the arm's E1-1 records (`rest_rotation_deg`); rest40 wall `cost.rest40_h`",
                "references' turner columns: the same report → `turner_references_E1-2.<ref>` (computed from those "
                "arms' records)",
                f"references' rest max, snap-back and wall time: `{rel(W3_REPORT)}` (L0, C52, W3) and "
                f"`{rel(HB_REPORT)}` (HB1–HB3) → `rest_max_deg`, `snap_abs_err_by_delta` (rounded to 3 dp there), "
                "`wall_s_total`"), ""]
    rows = []
    cost = rep.get("cost") or {}
    for a in report_arms(rep):
        r = rep["arms"][a]
        rv = rest.get(a)
        t = r.get("turner_E1-2_Nm")
        r40h = (cost.get("rest40_h") or {}).get(a)
        wall = f(r["wall_h"], 1) + (f" (+ rest40 {f(r40h, 1)})" if r40h is not None else "")
        rows.append([f"**{a}**", f(max(rv.values()) if rv else None, 3), f(snap_max(r["snap_back"], True), 3),
                     f(snap_max(r["snap_back"], False), 3)] + turner_cells(t)[:4] + [wall])
    tr = rep.get("turner_references_E1-2") or {}
    for n in REF_ROWS:
        x = refs.get(n, {})
        t = tr.get(n)
        if not x and not t:
            continue
        rows.append([n, f(x.get("rest_max_deg"), 3), f(x.get("snap_max_scored"), 3), f(x.get("snap_max_all"), 3)]
                    + turner_cells(t)[:4] + [f(x.get("wall_h"), 1)])
    out.append(table(["Arm", "Rest max (deg)", "Snap-back max \\|err\\|, scored (deg)", "… all 20 starts (deg)",
                      "E1-2 turner median / p99 / max (N·m)", "Moves > 0.45 N·m", "Moves > 0.5 N·m",
                      "Moves at the 1 N·m clip (≥ 0.999)", "Summed trial wall time (h)"], rows))
    out.append("")
    fr = rep.get("turner_references_full_run") or {}
    if fr:
        out.append("Full-run references (ER7, 204 trials, moves of E1-2, E1-3, E1-4) — "
                   + fact("report.json → `turner_references_full_run`") + "")
        out.append("")
        out.append(table(["Reference", "Turner median / p99 / max (N·m)", "> 0.45", "> 0.5", "At clip"],
                         [[n] + turner_cells(fr[n])[:4] for n in ("L0", "C52") if fr.get(n)]))
        out.append("")
    out.append("Realism reference about 0.2 N·m; warning level about 0.45–0.5 N·m (P-67 item 4; G.1). HB1–HB3 wall "
               "times were measured with other jobs on the machine and are not comparable (SUMMARY.md, Part E).")
    out.append("")
    # other reported items
    rows = []
    sag = rep.get("gravity_sag_from_smoke") or {}
    for a in report_arms(rep):
        r = rep["arms"][a]
        rows.append([a, f(r.get("largest_d_deg"), 2), len(r.get("legacy_proxy_flag_20deg_trials", [])),
                     f(r.get("steps_per_s_median"), 0), f(sag.get(a), 3)])
    out.append("Other reported items — " + fact("report.json → `arms.<arm>.largest_d_deg`, "
                                                "`.legacy_proxy_flag_20deg_trials`, `.steps_per_s_median`; "
                                                "`gravity_sag_from_smoke` (smoke replay seed 16568, largest "
                                                "tangential leftover; one replay, not the probe trials)"))
    out.append("")
    out.append(table(["Arm", "Largest d (deg)", "Trials with ER7's 20° proxy flag", "Steps/s (median)",
                      "Gravity sag, smoke (deg)"], rows))
    out.append("")
    rows = []
    arms = report_arms(rep)
    for c in CLASSES:
        for fld in CLASS_FIELDS:
            k = f"{c}_{fld}"
            rows.append([k] + [f((rep["arms"][a].get("class_stats_max") or {}).get(k), 3) for a in arms])
    rows.append(["cross_near"] + [f((rep["arms"][a].get("class_stats_max") or {}).get("cross_near"), 0) for a in arms])
    out.append("Per-class stats over the probe (max of tilts, min of distances, sum of counts) — "
               + fact("report.json → `arms.<arm>.class_stats_max`"))
    out.append("")
    out.append(table(["Field"] + arms, rows))
    out.append("")
    return "\n".join(out)


# ---- (d) rest comparison and slips ---------------------------------------------------------------------------------
def rest_slip_tables(rep: dict, er7: dict | None, rest40: dict) -> str:
    out = ["### (d) Paired rest rotation against L0, and slip seeds over 60 seeds (G.8; reported, not signals)", "",
           fact("report.json → `arms.<arm>.paired_rest_vs_L0`, `.slip_seeds_60`, `.slip_seeds_60_complete`, "
                "`.slip_seeds_0_60s`, `.rest_on_L0_slip_seeds`",
                f"L0's 20 probe seeds: `{rel(ER7_ANALYSIS)}` → `arms.L0.slip_seeds_0_60s`",
                "rest40 rest max: derived from `results/hybrid_g/rest40/<arm>/E1-1/*.json.gz` (`rest_rotation_deg`)"),
           ""]
    rows = []
    for a in report_arms(rep):
        p = rep["arms"][a]["paired_rest_vs_L0"]
        rows.append([a, p["n_seeds"], p["n_lower"], p["n"] - p["n_lower"], p["n_ties"], f(p["p_one_sided_lower"], 4),
                     f(p["p_two_sided"], 4)])
    out += ["Paired rest rotation (10 s scored metric) on the 20 E1-1 seeds; exact sign test, ties dropped:", "",
            table(["Arm", "Seeds", "Arm lower", "Arm higher", "Ties", "One-sided p (arm lower)", "Two-sided p"], rows),
            ""]
    l0_20 = ((er7 or {}).get("arms", {}).get("L0", {}) or {}).get("slip_seeds_0_60s")
    rows = []
    for a in report_arms(rep):
        r = rep["arms"][a]
        s = r.get("slip_seeds_60")
        if not s:
            rows.append([a] + ["n/a"] * 8)
            continue
        n_probe = len(r.get("slip_seeds_0_60s", []))
        a_r40 = s["arm"][0] - n_probe
        l0_r40 = (s["L0"][0] - l0_20) if l0_20 is not None else None
        rows.append([a, f"{s['arm'][0]} / {s['arm'][1]}", f"{n_probe} / {a_r40}",
                     f"[{f(s['arm_ci95'][0], 3)}, {f(s['arm_ci95'][1], 3)}]",
                     f"{s['L0'][0]} / {s['L0'][1]}", f"{f(l0_20)} / {f(l0_r40)}",
                     f"[{f(s['L0_ci95'][0], 3)}, {f(s['L0_ci95'][1], 3)}]", f(s["fisher_one_sided_p"], 4),
                     f"{s['reading']}{'' if r.get('slip_seeds_60_complete') else ' (**incomplete: not 60 / 60**)'}"])
    out += ["Slip seeds (D11 events over the 60 s rest), 20 probe + 40 rest40 seeds (16700–16739):", "",
            table(["Arm", "Arm slip seeds / n", "… probe / rest40 (derived)", "Arm 95 % CP", "L0 slip seeds / n",
                   "… ER7 20 / rest40 (derived)", "L0 95 % CP", "Fisher one-sided p", "Pre-declared reading"], rows),
            "", "Pre-declared reading (G.8): p ≤ 0.05 and fewer slip seeds than L0 = \"fewer slips than L0 in "
            "rehearsal\"; otherwise \"not distinguishable\".", ""]
    rows = []
    for a in ("L0",) + tuple(report_arms(rep)):
        rv = rest40.get(a)
        rows.append([a, f(len(rv)) if rv is not None else "n/a", f(max(rv.values()) if rv else None, 3)])
    out += ["Rest40 (U5) rest rotation, 10 s metric:", "", table(["Arm", "Records", "Rest max (deg)"], rows), ""]
    rows = []
    for a in report_arms(rep):
        d = rep["arms"][a].get("rest_on_L0_slip_seeds") or {}
        for s in L0_SLIP_SEEDS:
            x = d.get(s) or d.get(int(s)) if isinstance(d, dict) else None
            if x:
                rows.append([a, s, f(x["rest_rotation_deg"], 3), f(x.get("rest60_rotation_deg"), 3),
                             x["slip_events_60s"]])
    out += ["Rest on L0's slip seeds (L0 in ER7: 16003 at 0.568°, 16005 at 0.559°):", "",
            table(["Arm", "Seed", "Rest, 10 s (deg)", "Rest, 60 s (deg)", "D11 slip events (60 s)"], rows), ""]
    return "\n".join(out)


# ---- (e) selection and P-70 ----------------------------------------------------------------------------------------
def p70_branch(rep: dict) -> dict:
    """Which P-70 pre-commitment applies, from report.json alone. Returns {"state", "selected", "items": {1,2,3:
    {"applies", "why"}}, "item2_per_arm"}."""
    sel = rep.get("selection") or {}
    arms = rep.get("arms") or {}
    out = {"state": None, "selected": sel.get("selected"), "items": {}, "item2_per_arm": {}}
    if not sel.get("arms_considered"):
        out["state"] = "all_stopped"
    elif not sel.get("complete"):
        out["state"] = "incomplete"
    elif sel.get("selected") is None:
        out["state"] = "none_selected"
    else:
        out["state"] = "selected"
    if out["state"] in ("all_stopped", "incomplete"):
        for i in (1, 2, 3):
            out["items"][i] = {"applies": None, "why": f"not reached ({out['state']})"}
        return out
    considered = sel["arms_considered"]
    none = out["state"] == "none_selected"
    out["items"][1] = {"applies": none, "why": "selection.selected is null: no arm meets all four signals" if none
                       else f"selection.selected = {sel['selected']}"}
    any2 = False
    for a in considered:
        r = arms.get(a) or {}
        s = r.get("signals") or {}
        if s.get("4_no_operational_trial_out_of_regime", True):
            out["item2_per_arm"][a] = {"signal4_failed": False, "only_X_or_PCoff": None, "classes": [],
                                       "signal4_only_failure": False}
            continue
        cls = sorted({c for c, *_ in exceeded_conditions(r.get("class_stats_max"))})
        only = bool(cls) and set(cls) <= P70_ITEM2_CLASSES
        others = all(s.get(k) for k in ("1_snap_scored_all_pass", "2_rest_le_0.5_and_no_slips", "3_e12_e15_all_pass"))
        out["item2_per_arm"][a] = {"signal4_failed": True, "only_X_or_PCoff": only, "classes": cls,
                                   "signal4_only_failure": others}
        any2 |= only
    out["items"][2] = {"applies": any2, "why": "; ".join(
        f"{a}: signal 4 {'not met, exceeded classes ' + ','.join(v['classes']) if v['signal4_failed'] else 'met'}"
        for a, v in out["item2_per_arm"].items()) + " (envelope: P1 `e15_like.combined.stats` "
        "`X_min_centre_distance_mm` and `PC_max_path_dev_deg`, table (a))"}
    if none:
        out["items"][3] = {"applies": False, "why": "no arm selected"}
    else:
        a = sel["selected"]
        t = (arms.get(a) or {}).get("turner_E1-2_Nm") or {}
        med, clip = t.get("median"), t.get("at_clip")
        pause = bool(med is None or med >= P70_MEDIAN_NM or (clip or 0) > 0)
        out["items"][3] = {"applies": pause, "median": med, "at_clip": clip,
                           "why": f"{a}: E1-2 median {f(med, 3)} N·m (≥ {P70_MEDIAN_NM} → pause), moves at the clip "
                                  f"{clip} (> 0 → pause)"}
    return out


def selection_tables(rep: dict) -> str:
    sel = rep.get("selection") or {}
    out = ["### (e) Selection rule (G.8) and the P-70 pre-commitment that applies", "",
           fact("report.json → `selection` (`complete`, `arms_considered`, `stopped_arms`, `rows`, `selected`, "
                "`note`), `arms.<arm>.signals`, `.class_stats_max`, `.turner_E1-2_Nm`",
                "branch logic: `er9g_writeup.p70_branch` applying DECISION_LOG P-70 to those fields"), ""]
    rows = [[a, "**yes**" if r["all_met"] else "no", f(r["median_e12_turner_Nm"], 3), r["n_magnets"]]
            for a, r in (sel.get("rows") or {}).items()]
    out += [table(["Arm", "Meets all four", "Median E1-2 turner (N·m)", "Magnets"], rows), ""]
    for a, why in (sel.get("stopped_arms") or {}).items():
        out.append(f"- Stopped by a gate (G.6): {a}: {'; '.join(why)}")
    out.append(f"- Probe complete: {f(sel.get('complete'))}. **Selected: {sel.get('selected') or 'none'}.**"
               + (f" Note (report): {sel['note']}." if sel.get("note") else ""))
    out.append("- Rule (G.8): among PG8 and PG20, the arm that meets all four signals with the lowest median E1-2 "
               "turner torque; ties to fewer magnets. If none meets all four, Part G ends with the probe report and "
               "the next step goes to the user. Fit does not enter selection.")
    out.append("")
    b = p70_branch(rep)
    rows = [[f"P-70 item {i}", P70_TEXT[i], {True: "**applies**", False: "does not apply", None: "not reached"}[
        b["items"][i]["applies"]], b["items"][i]["why"]] for i in (1, 2, 3)]
    out += [table(["Pre-commitment", "Text (DECISION_LOG P-70)", "Status", "From fields"], rows), ""]
    for a, v in b["item2_per_arm"].items():
        if v["signal4_failed"]:
            out.append(f"- {a}: signal 4 failed through classes {', '.join(v['classes']) or '(none found in '
                       'class_stats_max)'}; only cross-type / off-path: {f(v['only_X_or_PCoff'])}; signals 1–3 "
                       f"met (signal 4 the only failure): {f(v['signal4_only_failure'])}")
    out.append("")
    return "\n".join(out)


# ---- (f) full rehearsal (G.9), only if run -------------------------------------------------------------------------
def g9_branches(full: dict) -> list[str]:
    s = full["signals"]
    clip = (full.get("turner_Nm") or {}).get("at_clip", 0)
    if s["all_met"]:
        return ["all_no_clip" if clip == 0 else "all_clip"]
    out = []
    if not s["1_no_slips_and_rest_le_0.5"]:
        out.append("1")
    e15s = (full.get("rows") or {}).get("E1-5s") or {}
    if not s["2_option_a_rule"] and e15s.get("failed"):
        out.append("2")
    if not s["3_no_operational_trial_out_of_regime"]:
        out.append("3")
    return out + ["any"]


def full_tables(root: Path = ROOT) -> str:
    out = []
    for a in ARMS:
        p = Path(root) / "full" / a / "report.json"
        d = read_json(p)
        if d is None:
            continue
        s, t = d["signals"], d.get("turner_Nm") or {}
        out += [f"### (f) Full rehearsal of {a} (G.9)", "",
                fact(f"`{rel(p)}` (`signals`, `rows`, `slip_seeds_0_60s`, `rest_max_deg`, "
                     "`operational_out_of_regime`, `abuse_labelled`, `turner_Nm`, `probe_reproduced`, `reading`)"), "",
                table(["Signal (G.9)", "Result"], [
                    ["1. 0/20 slip seeds and every rest ≤ 0.5°", f"{yn(s['1_no_slips_and_rest_le_0.5'])} (rest max "
                     f"{f(d.get('rest_max_deg'), 3)} deg; slip seeds {d.get('slip_seeds_0_60s') or 'none'})"],
                    ["2. M5's Option A rule (E1-6m ⟨P⟩)", yn(s["2_option_a_rule"])],
                    ["3. No operational trial out of regime", f"{yn(s['3_no_operational_trial_out_of_regime'])} "
                     f"({len(d.get('operational_out_of_regime', []))} operational; abuse labelled "
                     f"{len(d.get('abuse_labelled', []))})"]]), "",
                table(["Experiment", "Passed"], [[e, f"{r['passed']} / {r['expected']}"]
                                                 for e, r in (d.get("rows") or {}).items()]), "",
                f"Turner (E1-2, E1-3, E1-4 moves): median / p99 / max {turner_cells(t)[0]} N·m; > 0.45: "
                f"{t.get('above_0.45')}; > 0.5: {t.get('above_0.5')}; at clip {t.get('at_clip')} of "
                f"{t.get('n_moves')}. Probe reproduced: pass flags {f(d['probe_reproduced']['pass_flags_equal'])}, "
                f"values {f(d['probe_reproduced']['values_equal'])} ({d['probe_reproduced']['n_common']} trials).", "",
                f"Runner's reading field: \"{d.get('reading')}\". Protocol reading (G.9) that applies:", ""]
        out += [f"- {G9_READING[k]}" for k in g9_branches(d)] + [""]
    return "\n".join(out)


# ---- assembly ------------------------------------------------------------------------------------------------------
def build(report_path: Path | None = None, root: Path = ROOT, w3_path: Path = W3_REPORT, hb_path: Path = HB_REPORT,
          er7_path: Path = ER7_ANALYSIS, static_only: bool = False) -> str:
    parts = ["<!-- generated by experiments/ER9_anchored_core_layouts/er9g_writeup.py; every number is a field of the "
             "files named above its table -->", "", static_tables(root)]
    if static_only:
        return "\n".join(parts)
    report_path = Path(report_path or Path(root) / "probe" / "report.json")
    rep = read_json(report_path)
    if rep is None:
        raise SystemExit(f"no probe report at {report_path}: run `er9g_run.py report` first (or use --static-only)")
    rest = {a: rest_values(root, "probe", a) for a in report_arms(rep)}
    rest40 = {a: rest_values(root, "rest40", a) for a in ("L0",) + tuple(report_arms(rep))}
    refs = reference_rows(read_json(w3_path), read_json(hb_path))
    parts += [signals_table(rep, rest), reported_table(rep, rest, refs),
              rest_slip_tables(rep, read_json(er7_path), rest40), selection_tables(rep), full_tables(root)]
    return "\n".join(parts)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--static-only", action="store_true", help="table (a) only; no probe report needed")
    ap.add_argument("--report", help="probe report (default results/hybrid_g/probe/report.json)")
    a = ap.parse_args(argv)
    print(build(Path(a.report) if a.report else None, static_only=a.static_only))


if __name__ == "__main__":
    main()
