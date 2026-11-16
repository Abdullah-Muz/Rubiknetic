"""Task 2: recompute numbers quoted in the written records. Read-only."""
import json, glob, os, re, ast
from collections import defaultdict, Counter
import numpy as np

E = "experiments"
DG = E + "/D8_alignment/results/diag_m4_2026-11-15/"


def L(pat):
    out = []
    for f in sorted(glob.glob(pat)):
        try:
            r = json.load(open(f))
        except Exception:
            continue
        if isinstance(r, dict):
            r["_f"] = f
            out.append(r)
    return out


def P(*a):
    print(*a)


# ---------- RULE2/RULE3 from run.py ----------
tree = ast.parse(open(E + "/E4_scored_m4/run.py").read())
consts = {}
for n in tree.body:
    if isinstance(n, ast.Assign):
        for t in n.targets:
            if isinstance(t, ast.Name) and t.id in ("RULE2", "RULE3"):
                consts[t.id] = ast.literal_eval(n.value)
P("run.py", consts)

# ---------- 0.1 mm rehearsal ----------
R = L(E + "/D8_alignment/results/rehearsal_gap0.1mm/E1-*/*.json")
seeds = [r.get("seed") or (r.get("setup") or {}).get("seed") for r in R]
seeds = [s for s in seeds if s is not None]
P("\n## 0.1 rehearsal: trials", len(R), "seed min/max", min(seeds), max(seeds))
P("params gap", Counter(r["params"]["gap"] for r in R), "radial_preload", Counter(r["params"]["radial_preload"] for r in R))
P("magnets params", Counter(json.dumps((r.get("magnets") or {}).get("params"), sort_keys=True) for r in R).most_common(2))
P("magnets other keys", sorted((R[0].get("magnets") or {}).keys()))
mg = R[0].get("magnets") or {}
for k, v in mg.items():
    if k != "params":
        P("   magnets.", k, repr(v)[:200])
P("magnet_stats.list_pairs", Counter((r.get("magnet_stats") or {}).get("list_pairs") for r in R))
mv = [(r, i, m) for r in R for i, m in enumerate(r.get("per_move", []))]
P("moves", len(mv), "oracle ok", sum(m["ok_oracle"] for _, _, m in mv), "e16m", sum(m.get("e16m_P_ok") is True for _, _, m in mv))
dm = [(r["trial_id"], r["experiment"], i + 1, m["nontarget_drift_deg"]) for r, i, m in mv if m["nontarget_drift_deg"] > 1.0]
P("drift>1 moves", len(dm), "trials", len({d[0] for d in dm}), "pct", round(100 * len(dm) / len(mv), 3))
P("  E1-4 drift moves", [(a, round(d, 4)) for a, e, i, d in dm if e == "E1-4"], "count", sum(e == "E1-4" for _, e, _, _ in dm))
P("  E1-4 drift trials", sorted({a for a, e, _, _ in dm if e == "E1-4"}))
cf = [(r["trial_id"], i + 1, m["t_pad_force_s"], m["t_layer_motion_s"], (m["t_pad_force_s"] - m["t_layer_motion_s"]) * 1000) for r, i, m in mv if m.get("ok_causal") is False]
P("causal fails", [(a, b, round(e, 2)) for a, b, c, d, e in cf])
P("turn err max", max(abs(m["turn_error_deg"]) for _, _, m in mv), "pen max", max(m["penetration_mm"] for _, _, m in mv))
fails = [r for r in R if not r["pass"]]
P("pass", sum(r["pass"] for r in R), "fail list", sorted((r["experiment"], r["trial_id"]) for r in fails))
by = defaultdict(lambda: [0, 0])
for r in R:
    by[r["experiment"]][0] += 1; by[r["experiment"]][1] += bool(r["pass"])
P("per experiment (n, pass)", dict(by))
rest = sorted((r["trial_id"], round(r["rest_rotation_deg"], 4), (r.get("magnet_stats") or {}).get("list_rebuilds"), r["pass"]) for r in R if r["experiment"] == "E1-1")
P("rest trials (id, rot, list_rebuilds, pass):", rest)
P("rest rotation range", min(x[1] for x in rest), max(x[1] for x in rest))
tilt = defaultdict(list)
for r in R:
    tilt[r["sub_experiment"]].append((r.get("magnet_stats") or {}).get("max_near_tilt_deg"))
P("max tilt per sub", {k: round(max(v), 3) for k, v in tilt.items()})
P("rule2 max", round(max(max(v) for k, v in tilt.items() if k in consts["RULE2"]), 3),
  "rule3 trials", sum(len(v) for k, v in tilt.items() if k in consts["RULE3"]))
P("outside validated (stored flag)", Counter((r["sub_experiment"], r.get("magnet_outside_validated_range")) for r in R if r.get("magnet_outside_validated_range")))
P("rule3_label count", sum(bool(r.get("rule3_label")) for r in R), "E1-6t min tilt", round(min(tilt["E1-6t"]), 3), "E1-6c min tilt", round(min(tilt["E1-6c"]), 3))
s7312 = [r for r in R if r["trial_id"] == "sexy6_s7312"][0]
m12 = s7312["per_move"][12]
P("sexy6_s7312 per_move[12]", m12["move"], "drift", m12["nontarget_drift_deg"], "t_motion", m12["t_layer_motion_s"], "t_pad", m12["t_pad_force_s"], "causal", m12["ok_causal"])
P("sexy6_s7312 list_rebuilds", s7312["magnet_stats"].get("list_rebuilds"))
r7004 = [r for r in R if r["trial_id"] == "rest_s7004"][0]
P("rehearsal rest_s7004 rot", r7004["rest_rotation_deg"], "rebuilds", r7004["magnet_stats"].get("list_rebuilds"))
r7000 = [r for r in R if r["trial_id"] == "rest_s7000"][0]
P("rehearsal rest_s7000 rot repr", repr(r7000["rest_rotation_deg"]))

# ---------- M1 scored ----------
M1 = L(E + "/E1_scored/results/E1-[234]/*.json")
m1mv = [m for r in M1 for m in r.get("per_move", [])]
d = np.array([m["nontarget_drift_deg"] for m in m1mv])
P("\n## M1 scored E1-2..4 moves", len(d), "median", round(np.median(d), 4), "p90", round(np.percentile(d, 90), 4), "max", round(d.max(), 4), ">1", (d > 1).sum())
M1r = L(E + "/E1_scored/results/E1-1/*.json")
rr = [(r.get("seed"), r.get("rest_rotation_deg")) for r in M1r if r.get("rest_rotation_deg") is not None]
P("M1 rest n", len(rr), "seeds", min(s for s, _ in rr), max(s for s, _ in rr), "min", round(min(v for _, v in rr), 4), "max", round(max(v for _, v in rr), 4))
reh = np.array([m["nontarget_drift_deg"] for _, _, m in mv])
P("0.1 rehearsal drift median", round(np.median(reh), 4), "p90", round(np.percentile(reh, 90), 4), "max", round(reh.max(), 4), "ratio median reh/M1", round(np.median(reh) / np.median(d), 2))


# ---------- diag arms ----------
def arm(name, path):
    A = L(path + "/*.json")
    seq = [r for r in A if r.get("kind") == "seq"]
    mvs = [m for r in seq for m in r["per_move"]]
    dd = np.array([m["nontarget_drift_deg"] for m in mvs])
    te = np.array([abs(m["turn_error_deg"]) for m in mvs])
    tq = np.array([abs(m["max_turner_torque_Nm"]) for m in mvs])
    post = [m["misalignment"]["max_err_deg"] for m in mvs if m.get("misalignment")]
    rests = sorted(round(r["rest_rotation_deg"], 3) for r in A if r.get("kind") == "rest")
    restp = [r["pass"] for r in A if r.get("kind") == "rest"]
    tilt = [(r.get("magnet_stats") or {}).get("max_near_tilt_deg") for r in A if (r.get("magnet_stats") or {}).get("max_near_tilt_deg") is not None]
    seqtilt = [(r.get("magnet_stats") or {}).get("max_near_tilt_deg") for r in seq if (r.get("magnet_stats") or {}).get("max_near_tilt_deg") is not None]
    P(f"\n## {name}: files {len(A)} pass {sum(r['pass'] for r in A)} seeds {sorted(r.get('seed') or r['setup']['seed'] for r in A)}")
    P(f"  seq pass {sum(r['pass'] for r in seq)}/{len(seq)} moves {len(mvs)} oracle {sum(m['ok_oracle'] for m in mvs)} causal_fail {sum(m.get('ok_causal') is False for m in mvs)}")
    if len(dd):
        P(f"  drift median {np.median(dd):.4f} p90 {np.percentile(dd,90):.4f} p99 {np.percentile(dd,99):.4f} max {dd.max():.4f} >1 {(dd>1).sum()}")
        P(f"  turn err max {te.max():.4f}  torque median {np.median(tq):.4f} max {tq.max():.4f}  pen max {max(m['penetration_mm'] for m in mvs):.4f}")
        if post:
            P(f"  post-move worst err median {np.median(post):.4f} max {max(post):.4f}")
    P(f"  rest {rests} pass {restp}")
    if tilt:
        P(f"  tilt max all {max(tilt):.4f}  seq-only {max(seqtilt) if seqtilt else None}")
    for r in A:
        k = r.get("kind")
        if k in ("seq", "rest"):
            continue
        flat = {kk: (round(v, 4) if isinstance(v, float) else v) for kk, v in r.items()
                if not isinstance(v, (dict, list)) and kk not in ("_f", "t0_observed_valid", "t0_solved", "radial_offset_mm_t0", "wrench_log_entries",
                                                                   "sim_time_s", "integrity_ok", "wall_s", "scored", "diagnostic", "arm", "spec", "seed",
                                                                   "growth_slope_is_criterion", "validated_tilt_deg", "magnets", "magnet_table")}
        extra = {kk: v for kk, v in r.items() if isinstance(v, dict) and kk in ("layer_rotations_deg",)}
        P(f"  {r['trial_id']}: {json.dumps(flat)[:600]} {json.dumps(extra)}")
    return A


for nm, p in [("0.2 4x2", DG + "size_gap0.2mm/4x2_N35"), ("0.2 3x1.5", DG + "size_gap0.2mm/3x1.5_N35"),
              ("0.2 none", DG + "size_gap0.2mm/none"), ("0.1 4x2 (gap study)", DG + "gap_study/g0.1_4x2"),
              ("0.05 4x2", DG + "gap_study/g0.05_4x2"), ("0.05 none", DG + "gap_study/g0.05_none")]:
    A = arm(nm, p)
    if nm == "0.05 4x2":
        P("  magnets.params.wall", (A[0].get("magnets") or {}).get("params", {}).get("wall"), "gap", A[0]["params"]["gap"])
# all three 0.2 arms together: oracle and causal
tot = [m for p in ("4x2_N35", "3x1.5_N35", "none") for r in L(DG + "size_gap0.2mm/" + p + "/scr*.json") for m in r["per_move"]]
P("\n0.2 arms combined: moves", len(tot), "oracle", sum(m["ok_oracle"] for m in tot), "causal_fail", sum(m.get("ok_causal") is False for m in tot))
mag = [abs(m["turn_error_deg"]) for p in ("4x2_N35", "3x1.5_N35") for r in L(DG + "size_gap0.2mm/" + p + "/scr*.json") for m in r["per_move"]]
P("0.2 turn error max with magnets", max(mag))
