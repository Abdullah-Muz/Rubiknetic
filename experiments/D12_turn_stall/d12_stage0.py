"""D12 Stage 0 (PROTOCOL.md section 7.0): existing records only, read-only JSON parsing, no simulation.

Tabulates per-move turner peak, clipped-move count (|tau| >= 0.999 N m) and non-target drift for
  * E5's E1-7 (all arms)                         experiments/E5_scored_m5/results/E1-7/*.json
  * E5's no-magnet battery, E1-2 single moves    experiments/E5_scored_m5/results_nomag/E1-2/*.json
  * D8's gap study                               experiments/D8_alignment/results/diag_m4_2026-11-15/gap_study/*/*.json
  * ER9's 13 turn diagnostics                    experiments/ER9_anchored_core_layouts/results/probe/diag/turn_*.json
and compares the E1-7 rows with the tallies quoted in PROTOCOL.md section 7.0 (grep/awk, 2026-11-21). Where they
disagree, this script's value governs and the mismatch is reported.

Usage (WSL, repo root):  ~/.venvs/rubiknetic/bin/python experiments/D12_turn_stall/d12_stage0.py
Writes results/stage0/stage0.json and stage0.md (exclusive create: an existing output is never overwritten).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "results" / "stage0"
E17 = REPO / "experiments/E5_scored_m5/results/E1-7"
NOMAG = REPO / "experiments/E5_scored_m5/results_nomag/E1-2"
GAPSTUDY = REPO / "experiments/D8_alignment/results/diag_m4_2026-11-15/gap_study"
ER9 = REPO / "experiments/ER9_anchored_core_layouts/results/probe/diag"
CLIP = 0.999

# PROTOCOL.md section 7.0 table: (6move U peak, 6move max, 6move clipped, 6move max drift, 6move moves recorded or
# None for all 6, sexy6 max, sexy6 clipped, sexy6 max drift, pass 6move, pass sexy6)
PROTOCOL_E17 = {
    "nominal": (0.465, 0.465, 0, 0.474, None, 0.640, 0, 0.517, True, True),
    "gap=2.5e-05": (0.373, 0.373, 0, 0.331, None, 0.491, 0, 0.381, True, True),
    "gap=0.0001": (0.456, 0.456, 0, 0.805, None, 0.464, 0, 0.894, True, True),
    "chamfer=0.001": (0.813, 0.813, 0, 0.280, 5, 0.568, 0, 0.510, False, True),
    "chamfer=0.002": (0.447, 0.447, 0, 0.467, None, 0.502, 0, 0.593, True, True),
    "cubie_friction=0.1-0.0025-0.0005": (0.309, 0.400, 0, 0.350, None, 0.388, 0, 0.376, True, True),
    "cubie_friction=0.5-0.0025-0.0005": (0.504, 0.504, 0, 0.466, None, 1.000, 5, 0.586, True, True),
    "cubie_friction=1.0-0.0025-0.0005": (0.743, 0.743, 0, 0.473, None, 1.000, 3, 0.586, True, True),
    "grip_force=10.0": (0.557, 0.557, 0, 0.477, None, 0.570, 0, 0.379, True, True),
    "grip_force=30.0": (0.460, 0.460, 0, 0.493, None, 0.471, 0, 0.355, True, True),
    "grip_force=50.0": (0.445, 0.925, 0, 0.496, None, 0.489, 0, 0.505, True, True),
    "misalign_max_deg=0.0": (0.095, 0.110, 0, 0.476, None, 0.477, 0, 0.381, True, True),
    "misalign_max_deg=2.0": (0.252, 0.252, 0, 0.528, None, 0.492, 0, 0.583, True, True),
    "misalign_max_deg=5.0": (0.463, 0.463, 0, 0.496, None, 0.474, 0, 0.468, True, True),
    "timestep=0.00025": (0.632, 0.632, 0, 0.512, None, 0.597, 0, 0.566, True, True),
    "timestep=0.00075": (0.106, 0.129, 0, 0.536, None, 0.389, 0, 0.571, False, False),
    "magnet=none": (1.000, 1.000, 2, 0.578, 2, 1.000, 5, 0.843, False, True),
}


def seq_summary(rec: dict) -> dict:
    pm = rec.get("per_move", [])
    tq = [float(m["max_turner_torque_Nm"]) for m in pm]
    dr = [float(m["nontarget_drift_deg"]) for m in pm]
    return {"sequence": rec.get("sequence"), "n_moves_recorded": len(pm),
            "first_move": pm[0]["move"] if pm else None, "first_move_peak_Nm": tq[0] if tq else None,
            "peak_max_Nm": max(tq) if tq else None, "peak_median_Nm": float(np.median(tq)) if tq else None,
            "clipped_moves": int(sum(t >= CLIP for t in tq)), "max_drift_deg": max(dr) if dr else None,
            "pass": rec.get("pass"), "per_move_peak_Nm": tq, "per_move_drift_deg": dr}


def e17_table(recs: dict) -> dict:
    """recs: {trial id 'arm__6move' / 'arm__sexy6': record} -> {arm: {'6move': summary, 'sexy6': summary}}."""
    out: dict = {}
    for tid, r in recs.items():
        arm, seq = tid.rsplit("__", 1)
        out.setdefault(arm, {})[seq] = seq_summary(r)
    return out


def _close(a, b, tol=0.0005 + 1e-9) -> bool:
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


def compare_e17(table: dict) -> list[dict]:
    """Rows of the protocol's E1-7 table against the recomputed values (3-decimal quotes; tolerance 0.0005)."""
    rows = []
    for arm, exp in PROTOCOL_E17.items():
        u, mx, clip, dr, nrec, smx, sclip, sdr, p6, ps = exp
        got = table.get(arm)
        if got is None or "6move" not in got or "sexy6" not in got:
            rows.append({"arm": arm, "match": False, "problems": ["records missing"]})
            continue
        a, b = got["6move"], got["sexy6"]
        probs = []
        checks = [("6move U peak", a["first_move_peak_Nm"], u), ("6move max", a["peak_max_Nm"], mx),
                  ("6move max drift", a["max_drift_deg"], dr), ("sexy6 max", b["peak_max_Nm"], smx),
                  ("sexy6 max drift", b["max_drift_deg"], sdr)]
        for name, g, e in checks:
            if not _close(g, e):
                probs.append(f"{name}: recomputed {g} vs quoted {e}")
        if a["clipped_moves"] != clip:
            probs.append(f"6move clipped: recomputed {a['clipped_moves']} vs quoted {clip}")
        if b["clipped_moves"] != sclip:
            probs.append(f"sexy6 clipped: recomputed {b['clipped_moves']} vs quoted {sclip}")
        if nrec is not None and a["n_moves_recorded"] != nrec:
            probs.append(f"6move moves recorded: {a['n_moves_recorded']} vs quoted {nrec}")
        if nrec is None and a["n_moves_recorded"] != 6:
            probs.append(f"6move moves recorded: {a['n_moves_recorded']} vs 6 implied")
        if bool(a["pass"]) != p6 or bool(b["pass"]) != ps:
            probs.append(f"pass: recomputed ({a['pass']}, {b['pass']}) vs quoted ({p6}, {ps})")
        rows.append({"arm": arm, "match": not probs, "problems": probs})
    return rows


def er9_turn_row(rec: dict) -> dict:
    return {k: rec.get(k) for k in ("arm", "seed", "peak_torque_Nm", "turner_deg_at_peak", "t_peak_from_start_s",
                                    "fraction_of_steps_at_clip", "final_layer_err_deg", "grip_force_N",
                                    "turn_s_per_quarter")}


def _load_dir(d: Path, pattern: str = "*.json") -> dict:
    return {f.stem: json.loads(f.read_text()) for f in sorted(d.glob(pattern))}


def build() -> dict:
    e17 = e17_table(_load_dir(E17))
    nomag = {tid: seq_summary(r) for tid, r in _load_dir(NOMAG).items()}
    nm_tq = [x["first_move_peak_Nm"] for x in nomag.values() if x["first_move_peak_Nm"] is not None]
    gap = {}
    for sub in sorted(p for p in GAPSTUDY.iterdir() if p.is_dir()):
        for tid, r in _load_dir(sub).items():
            if r.get("per_move"):
                gap[f"{sub.name}/{tid}"] = seq_summary(r)
    er9 = {f.stem: er9_turn_row(json.loads(f.read_text())) for f in sorted(ER9.glob("turn_*.json"))}
    return {
        "status": "D12 Stage 0: committed records only; read-only; no simulation",
        "E1-7": {"source": str(E17.relative_to(REPO)), "arms": e17, "protocol_comparison": compare_e17(e17)},
        "E5_nomag_E1-2": {"source": str(NOMAG.relative_to(REPO)), "trials": nomag,
                          "summary": {"n": len(nm_tq), "median_peak_Nm": float(np.median(nm_tq)) if nm_tq else None,
                                      "max_peak_Nm": max(nm_tq) if nm_tq else None,
                                      "clipped_moves": int(sum(t >= CLIP for t in nm_tq))}},
        "D8_gap_study": {"source": str(GAPSTUDY.relative_to(REPO)), "sequences": gap},
        "ER9_turn": {"source": str(ER9.relative_to(REPO)), "n_files": len(er9), "rows": er9},
    }


def markdown(res: dict) -> str:
    L = ["# D12 Stage 0 (generated by d12_stage0.py; read-only, no simulation)", "",
         "## E5 E1-7 (seed 10000, R1, L0 unless named)", "",
         "| arm | 6move U peak | 6move max | clipped | max drift | moves | sexy6 max | clipped | max drift | pass |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    f = lambda x: "-" if x is None else f"{x:.3f}"  # noqa: E731
    for arm, v in sorted(res["E1-7"]["arms"].items()):
        a, b = v.get("6move", {}), v.get("sexy6", {})
        L.append(f"| {arm} | {f(a.get('first_move_peak_Nm'))} | {f(a.get('peak_max_Nm'))} | {a.get('clipped_moves')} | "
                 f"{f(a.get('max_drift_deg'))} | {a.get('n_moves_recorded')} | {f(b.get('peak_max_Nm'))} | "
                 f"{b.get('clipped_moves')} | {f(b.get('max_drift_deg'))} | {a.get('pass')}, {b.get('pass')} |")
    L += ["", "### Against the protocol's quoted tallies", ""]
    for r in res["E1-7"]["protocol_comparison"]:
        L.append(f"- {r['arm']}: {'match' if r['match'] else 'MISMATCH: ' + '; '.join(r['problems'])}")
    s = res["E5_nomag_E1-2"]["summary"]
    L += ["", f"## E5 no-magnet E1-2: n {s['n']}, median peak {f(s['median_peak_Nm'])}, max {f(s['max_peak_Nm'])}, "
              f"clipped {s['clipped_moves']}", "", "## D8 gap study (sequences)", ""]
    for k, v in res["D8_gap_study"]["sequences"].items():
        L.append(f"- {k}: moves {v['n_moves_recorded']}, peak median {f(v['peak_median_Nm'])}, max {f(v['peak_max_Nm'])}, "
                 f"clipped {v['clipped_moves']}, max drift {f(v['max_drift_deg'])}, pass {v['pass']}")
    L += ["", "## ER9 turn diagnostics (seed 16100, R1)", ""]
    for k, v in res["ER9_turn"]["rows"].items():
        L.append(f"- {k}: peak {f(v['peak_torque_Nm'])} N m at {f(v['turner_deg_at_peak'])} deg, clip fraction "
                 f"{f(v['fraction_of_steps_at_clip'])}, final error {f(v['final_layer_err_deg'])} deg")
    return "\n".join(L) + "\n"


def main() -> int:
    res = build()
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in (("stage0.json", json.dumps(res, indent=1)), ("stage0.md", markdown(res))):
        p = OUT / name
        if p.exists():
            print(f"{p} exists; Stage 0's output is never overwritten", file=sys.stderr)
            return 2
        with open(p, "x") as fh:
            fh.write(text)
    print(markdown(res))
    bad = [r for r in res["E1-7"]["protocol_comparison"] if not r["match"]]
    if bad:
        print(f"{len(bad)} E1-7 rows differ from the protocol's quoted tallies (this script's values govern)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
