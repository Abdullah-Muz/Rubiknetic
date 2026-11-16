"""Verdict script for M5 (experiments/PHASE_1_M5_PREREGISTRATION.md, section 5). Reads only; never re-runs a trial.

Verdict order: INVALID (any integrity violation, section 2 and 5) > INCOMPLETE (a manifest key without a record) >
NOT PASSED (Option A fails) > PASS. PASS here is the quantitative/categorical verdict only: G1 also needs E1-8
published and the user's sign-off.
Option A: every stored per-trial `pass` flag is true for the 204 magnet-arm trials of E1-1..E1-6, E1-5s and E1-6t
(E1-6t included, unlike M4's analyze.py:16-18), and E1-6m <P> (`e16m_P_ok`) holds for every move of E1-2..E1-4.
E1-6n (no magnets) and E1-7 are reported only.

Usage (WSL, repo root):
    ~/.venvs/rubiknetic/bin/python experiments/E5_scored_m5/analyze.py            # writes RESULTS.md
    ~/.venvs/rubiknetic/bin/python experiments/E5_scored_m5/analyze.py --print
    ~/.venvs/rubiknetic/bin/python experiments/E5_scored_m5/analyze.py --smoke-dir DIR   # integrity only
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_R_NAME = "e5_scored_m5_run"


def _load_runner():
    if _R_NAME in sys.modules:
        return sys.modules[_R_NAME]
    spec = importlib.util.spec_from_file_location(_R_NAME, HERE / "run.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_R_NAME] = mod
    spec.loader.exec_module(mod)
    return mod


R = _load_runner()
from rubiknetic.cube_logic import invert, random_scramble  # noqa: E402

EXPECTED = {"E1-1": 20, "E1-2": 24, "E1-3": 22, "E1-4": 40, "E1-5": 42, "E1-5s": 20, "E1-6a": 6, "E1-6b": 6,
            "E1-6c": 8, "E1-6t": 16}
ROWS = list(EXPECTED)
CLIP_NM = 0.999
TOP_FILES = {R.MANIFEST, R.STARTS, R.LEDGER}


def _tag(tid: str) -> str:
    return tid[len("smoke_"):] if tid.startswith("smoke_") else tid


def expected_gap(tid: str) -> float:
    tid = _tag(tid)
    if tid.startswith("gap=2.5e-05__"):
        return 2.5e-5
    if tid.startswith("gap=0.0001__"):
        return 1e-4
    return R.GAP


def expected_wall(tid: str) -> float:
    tid = _tag(tid)
    if tid.startswith("face_gap_mm=0.35__"):
        return 0.15e-3
    if tid.startswith("face_gap_mm=1.35__"):
        return 0.65e-3
    return 0.4e-3


def expects_magnets(key: tuple) -> bool:
    arm, _exp, tid = key
    return arm == "magnets" and not _tag(tid).startswith("magnet=none__")


def _close(a, b) -> bool:
    return a is not None and b is not None and bool(np.isclose(float(a), float(b), rtol=0.0, atol=1e-12))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _lines(path: Path) -> tuple[list[dict], list[str]]:
    out, bad = [], []
    if not path.exists():
        return out, bad
    for i, x in enumerate(path.read_text().splitlines()):
        if not x.strip():
            continue
        try:
            out.append(json.loads(x))
        except json.JSONDecodeError:
            bad.append(f"{path.name} line {i + 1} does not parse")
    return out, bad


# ---- load and check ------------------------------------------------------------------------------------------------
def load(dirs: dict) -> dict:
    """Everything on disk, with the integrity violations of sections 2 and 5 that do not need the registered list."""
    v: list[str] = []
    out = dirs["magnets"]
    man_path = out / R.MANIFEST
    if not man_path.exists():
        return {"manifest": None, "violations": [], "records": {}, "missing": [], "starts": [], "ledger": []}
    manifest = json.loads(man_path.read_text())
    starts, bad = _lines(out / R.STARTS)
    v += bad
    ledger, bad = _lines(out / R.LEDGER)
    v += bad
    logged_orphans = {(o["arm"], o["moved_to"]): o["sha256"] for s in starts for o in s.get("orphans", [])}
    records, shas = {}, {}
    for arm in R.ARMS:
        root = dirs[arm]
        if not root.exists():
            continue
        for p in sorted(root.iterdir()):
            if p.is_file():
                if not (arm == "magnets" and p.name in TOP_FILES):
                    v.append(f"unexpected file {arm}/{p.name}")
                continue
            if p.name == R.INTERRUPTED:
                for f in sorted(p.iterdir()):
                    rel = str(f.relative_to(root))
                    if logged_orphans.get((arm, rel)) != _sha(f.read_bytes()):
                        v.append(f"orphan {arm}/{rel} not logged in the start log (or SHA-256 differs)")
                continue
            for f in sorted(p.iterdir()):
                if f.name.startswith(".") and f.name.endswith(".json.tmp"):
                    v.append(f"unlogged temporary file {arm}/{p.name}/{f.name}")
                elif f.suffix == ".json" and f.is_file():
                    data = f.read_bytes()
                    key = (arm, p.name, f.stem)
                    try:
                        records[key] = json.loads(data)
                        shas[key] = _sha(data)
                    except json.JSONDecodeError:
                        v.append(f"record {arm}/{p.name}/{f.name} does not parse")
                else:
                    v.append(f"unexpected file {arm}/{p.name}/{f.name}")
    # ledger: one line per record, matching SHA-256, no duplicate key, no line without a record
    seen = Counter((x["arm"], x["exp"], x["tid"]) for x in ledger)
    for k, n in seen.items():
        if n > 1:
            v.append(f"key {k} appears {n} times in the ledger")
    by_key = {(x["arm"], x["exp"], x["tid"]): x for x in ledger}
    for k, x in by_key.items():
        if k not in shas:
            v.append(f"ledger line without a record: {k}")
        elif k in shas and x["sha256"] != shas[k]:
            v.append(f"ledger SHA-256 differs from the record: {k}")
    for k in shas:
        if k not in by_key:
            v.append(f"record without a ledger line: {k}")
    return {"manifest": manifest, "violations": v, "records": records, "starts": starts, "ledger": ledger}


def check_records(st: dict, registered: list[dict] | None, expect_scored: bool) -> None:
    """Per-record integrity (section 5) against the manifest and the registered list; adds to st['violations']."""
    v, man, recs = st["violations"], st["manifest"], st["records"]
    trials = {(t["arm"], t["exp"], t["tid"]): t for t in man["trials"]}
    not_run = {(t["arm"], t["exp"], t["tid"]): t for t in man["not_run"]}
    for k, t in not_run.items():
        if t["exp"] != "E1-7" or t["reason"] not in ("failed V3", "outside V3"):
            v.append(f"'not run' {k} with an unregistered reason {t['reason']!r}")
    if registered is not None:
        reg = {R.key_of(j): j for j in registered}
        if set(reg) != set(trials) | set(not_run):
            v.append(f"manifest keys differ from the registered list ({len(set(reg) ^ (set(trials) | set(not_run)))}"
                     " keys)")
        for k, t in {**trials, **not_run}.items():
            j = reg.get(k)
            if j and (j["kw"]["seed"] != t["seed"] or R._norm(j["kw"].get("overrides", {})) != R._norm(t["overrides"])):
                v.append(f"manifest seed/overrides differ from the registered list: {k}")
    env_man = man.get("environment", {})
    commits = set()
    for k, r in recs.items():
        if k not in trials:
            v.append(f"record not in the manifest: {k}")
            continue
        t = trials[k]
        commits.add(r.get("source_commit"))
        tag = "/".join(k)
        if (r.get("arm"), r.get("experiment"), r.get("trial_id")) != k:
            v.append(f"{tag}: record metadata does not match its key")
        if (r.get("spec") or {}).get("seed") != t["seed"]:
            v.append(f"{tag}: seed differs from the manifest")
        if registered is not None and k in reg and R._norm(r.get("spec")) != R._norm(reg[k]["kw"]):
            v.append(f"{tag}: spec differs from the registered trial")
        if r.get("source_commit") != man["commit"]:
            v.append(f"{tag}: source commit {r.get('source_commit')} differs from the manifest's")
        if r.get("scored") is not expect_scored:
            v.append(f"{tag}: scored = {r.get('scored')}")
        if r.get("mechanism") != "M5":
            v.append(f"{tag}: mechanism {r.get('mechanism')!r}")
        gap = expected_gap(k[2])
        if not _close((r.get("params") or {}).get("gap"), gap):
            v.append(f"{tag}: params.gap {(r.get('params') or {}).get('gap')} != {gap}")
        for f in R.ENV_COMPARED:
            if (r.get("environment") or {}).get(f) != env_man.get(f):
                v.append(f"{tag}: environment {f} differs from the manifest")
        mag = r.get("magnets")
        if expects_magnets(k):
            if not mag:
                v.append(f"{tag}: magnet record without magnets")
            else:
                if not _close(mag.get("layout_gap"), gap):
                    v.append(f"{tag}: magnets.layout_gap {mag.get('layout_gap')} != {gap}")
                if not _close((mag.get("params") or {}).get("wall"), expected_wall(k[2])):
                    v.append(f"{tag}: wall {(mag.get('params') or {}).get('wall')} != {expected_wall(k[2])}")
                if not _close((r.get("startup_checks") or {}).get("gap"), R.GAP):
                    v.append(f"{tag}: startup_checks.gap {(r.get('startup_checks') or {}).get('gap')}")
                tab = r.get("magnet_table") or {}
                if man["tables"].get(tab.get("table_file")) != tab.get("table_sha256"):
                    v.append(f"{tag}: table SHA-256 differs from the manifest")
        elif mag:
            v.append(f"{tag}: no-magnet record carries magnets")
        if k[1] == "E1-4" and k[2].startswith("scr20inv_"):
            sc = random_scramble(20, t["seed"])
            want = " ".join(str(m) for m in sc + invert(sc))
            if (r.get("spec") or {}).get("moves") != want or r.get("sequence", want) != want:
                v.append(f"{tag}: E1-4 sequence does not match random_scramble(20, {t['seed']}) + inverse")
    if len(commits) > 1:
        v.append(f"records carry {len(commits)} source commits")
    st["missing"] = sorted(k for k in trials if k not in recs)


def verdict(st: dict) -> dict:
    recs = st["records"]
    by = defaultdict(list)
    for (arm, _e, _t), r in recs.items():
        if arm == "magnets":
            by[r.get("sub_experiment")].append(r)
    rows = {}
    for e in ROWS:
        rs = by.get(e, [])
        rows[e] = {"n": len(rs), "expected": EXPECTED[e], "passed": sum(bool(r.get("pass")) for r in rs)}
    moves = [m for e in ("E1-2", "E1-3", "E1-4") for r in by.get(e, []) for m in r.get("per_move", [])]
    p_ok = [m.get("e16m_P_ok") for m in moves]
    seq_trials = sum(len(by.get(e, [])) for e in ("E1-2", "E1-3", "E1-4"))
    e16m_ok = bool(p_ok) and all(x is True for x in p_ok)        # as M4's analyze.py:66-70
    counts_ok = all(rows[e]["n"] == EXPECTED[e] for e in ROWS)
    option_a = counts_ok and all(rows[e]["passed"] == rows[e]["n"] for e in ROWS) and e16m_ok
    if st["violations"]:
        word = "INVALID"
    elif st["missing"] or not counts_ok:
        word = "INCOMPLETE"
    elif not option_a:
        word = "NOT PASSED"
    else:
        word = "PASS"
    return {"verdict": word, "rows": rows, "e16m": {"moves": len(p_ok), "ok": sum(x is True for x in p_ok),
                                                   "pass": e16m_ok, "seq_trials": seq_trials}, "by": by}


def analyse(dirs: dict, registered: list[dict] | None, expect_scored: bool = True) -> tuple[dict, dict]:
    st = load(dirs)
    if st["manifest"] is None:
        return st, {"verdict": "NO RUN", "rows": {}, "e16m": {}, "by": {}}
    check_records(st, registered, expect_scored)
    return st, verdict(st)


# ---- report --------------------------------------------------------------------------------------------------------
def _q(vals):
    v = np.asarray([x for x in vals if x is not None], float)
    if not len(v):
        return "–"
    return f"median {np.median(v):.3g} / p99 {np.percentile(v, 99):.3g} / max {v.max():.3g} (n = {len(v)})"


def report(st: dict, vd: dict) -> str:
    L = ["# G1 scored results — M5 (auto-generated by analyze.py)", ""]
    if st["manifest"] is None:
        return "\n".join(L + ["No manifest: the scored run has not started.", ""])
    man = st["manifest"]
    L += [f"**Verdict (Option A, quantitative/categorical): {vd['verdict']}.** G1 also needs E1-8 published and the "
          "user's sign-off.", "",
          f"Manifest commit `{man['commit']}`, created {man.get('created')}; {len(man['trials'])} trials to run, "
          f"{len(man['not_run'])} registered not run.", ""]
    if st["violations"]:
        L += ["## Integrity violations (INVALID)", ""] + [f"* {x}" for x in st["violations"]] + [""]
    if st["missing"]:
        L += [f"## Missing records (INCOMPLETE): {len(st['missing'])}", ""] + \
             [f"* {'/'.join(k)}" for k in st["missing"][:50]] + [""]
    per_start = Counter(x["start"] for x in st["ledger"])
    L += ["## Starts (section 2)", "", "| start | time | HEAD | records written | orphans moved | ledger lines reconciled |",
          "|---|---|---|---|---|---|"]
    for s in st["starts"]:
        L.append(f"| {s['k']} | {s['time']} | `{s['head'][:7]}` | {per_start.get(s['k'], 0)} | "
                 f"{len(s.get('orphans', []))} | {len(s.get('reconciled', []))} |")
    L += ["", "## Option A (magnet arm)", "", "| Experiment | Records / registered | Passed | Verdict |", "|---|---|---|---|"]
    for e, row in vd["rows"].items():
        ok = row["n"] == row["expected"] and row["passed"] == row["n"]
        L.append(f"| {e} | {row['n']} / {row['expected']} | {row['passed']} | "
                 f"{'PASS' if ok else ('INCOMPLETE' if row['n'] != row['expected'] else 'FAIL')} |")
    m = vd["e16m"]
    L.append(f"| E1-6m ⟨P⟩ (moves of E1-2…E1-4) | {m['moves']} moves | {m['ok']} | {'PASS' if m['pass'] else 'FAIL'} |")
    by = vd["by"]
    seq = by.get("E1-2", []) + by.get("E1-3", []) + by.get("E1-4", [])
    mv = [x for r in seq for x in r.get("per_move", [])]
    drift = [abs(x["nontarget_drift_deg"]) for x in mv if x.get("nontarget_drift_deg") is not None]
    torque = [x.get("max_turner_torque_Nm") for x in mv]
    clip = [r["trial_id"] + ":" + str(i) for r in seq for i, x in enumerate(r.get("per_move", []))
            if (x.get("max_turner_torque_Nm") or 0) >= CLIP_NM]
    L += ["", "## Restated with the verdict (section 5)", "",
          "* The 0.05 mm gap was chosen after unscored data at 0.2, 0.1 and 0.05 mm (P-24 to P-30).",
          "* Move strings other than the 20 E1-4 scrambles are the ones the rehearsals used; the E1-4 scrambles were "
          "drawn from the M5 seeds.",
          "* Whether a 0.05 mm clearance is realistic is an ASSUMPTION (one 2x2x2 patent; no 3x3 measurement).",
          f"* Non-target drift over E1-2…E1-4: {_q(drift)} deg; margin to the 1 deg criterion "
          f"{(1.0 - max(drift)) if drift else float('nan'):.3f} deg.",
          f"* Turner torque per move: {_q(torque)} N m; moves at the clip (>= {CLIP_NM} N m): {len(clip)}"
          + (f" ({', '.join(clip[:10])})" if clip else "") + "."]
    nomag = {(k[1], k[2]): r for k, r in st["records"].items() if k[0] == "no_magnets"}
    L += ["", "## Rule-3 trials with their no-magnet counterparts (E1-6b, E1-6c, E1-6t)", "",
          "| trial | pass | max tilt (deg) | rule-3 label | no-magnet pass | no-magnet final solved |", "|---|---|---|---|---|---|"]
    for e in ("E1-6b", "E1-6c", "E1-6t"):
        for r in sorted(by.get(e, []), key=lambda r: r["trial_id"]):
            n = nomag.get((r["experiment"], r["trial_id"]), {})
            tilt = (r.get("magnet_stats") or {}).get("max_near_tilt_deg")
            L.append(f"| {e}/{r['trial_id']} | {r['pass']} | {tilt if tilt is None else round(tilt, 2)} | "
                     f"{r.get('rule3_label') or ''} | {n.get('pass', '–')} | {n.get('final_solved', '–')} |")
    L += ["", "## Failed trials (magnet arm)", ""]
    for e in ROWS:
        for r in sorted(by.get(e, []), key=lambda r: r["trial_id"]):
            if not r.get("pass"):
                L.append(f"* {e}/{r['trial_id']}: {'; '.join(r.get('fail_reasons', []))}")
    L += ["", "## E1-6n no-magnet arm (reported only)", "", "| experiment | records | pass |", "|---|---|---|"]
    cn = defaultdict(lambda: [0, 0])
    for (exp, _t), r in nomag.items():
        cn[r.get("sub_experiment", exp)][0] += 1
        cn[r.get("sub_experiment", exp)][1] += bool(r.get("pass"))
    for e in sorted(cn):
        L.append(f"| {e} | {cn[e][0]} | {cn[e][1]} |")
    L += ["", "## E1-7 sensitivity (reported; flips are fragilities)", "", "| arm | 6move | sexy6 |", "|---|---|---|"]
    arms = defaultdict(dict)
    for k, r in st["records"].items():
        if k[1] == "E1-7":
            tag, sname = k[2].split("__")
            arms[tag][sname] = "pass" if r.get("pass") else "FAIL"
    for t in man["not_run"]:
        if t["exp"] == "E1-7":
            tag, sname = t["tid"].split("__")
            arms[tag][sname] = f"not run: {t['reason']}"
    for tag in sorted(arms):
        L.append(f"| {tag} | {arms[tag].get('6move', '–')} | {arms[tag].get('sexy6', '–')} |")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--smoke-dir", type=Path)
    a = ap.parse_args(argv)
    if a.smoke_dir:
        dirs = {"magnets": a.smoke_dir / "results", "no_magnets": a.smoke_dir / "results_nomag"}
        st, vd = analyse(dirs, None, expect_scored=False)
        print(f"smoke integrity: {len(st['violations'])} violations, {len(st['missing'])} missing, "
              f"{len(st['records'])} records, {len(st['starts'])} starts")
        for x in st["violations"]:
            print("  ", x)
        sys.exit(1 if st["violations"] or st["missing"] else 0)
    env = R.scored.environment()
    registered = R.build_m5_jobs("analyze", env, R.M4.nominal_validated_tilt())
    st, vd = analyse({"magnets": R.OUT, "no_magnets": R.OUT_NOMAG}, registered)
    text = report(st, vd)
    if not a.print and st["manifest"] is not None:
        (HERE / "RESULTS.md").write_text(text)           # outside results/: only registered files live there
    print(text)


if __name__ == "__main__":
    main()
