"""ER9 Part G, static pre-check P4 (PROTOCOL.md, Part G, G.6 "P4" and G.4 "Path deviation d"). Unscored; no MuJoCo.

Force-law checks modelled on ER5's V3-turn (`experiments/ER5_magnet_validation/er5_checks.py`, `v3_turn`):
the runtime hybrid law (`magnets.pair_forces`, 4x3 mm N35 tilt table) against the fine charge model
(`D8.fine_pair`, 32 x 96 for pairs within r2, 6 x 16 beyond) for ONE piece magnet against a set of core magnets,
the piece magnet turned about U (+z) at theta = 0, 1, ..., 90 deg. ER5's pass rule, unchanged, at every theta:
force error <= 5 % of Fn (the 4x3 N35 facing-pair normal force at a 1.0 mm face gap, 1.923 N) and torque error
<= max(5 % of the largest fine torque along that trajectory, 2e-5 N m).

Pair order (coordinator review, 2026-11-22): pair_forces expands the near-field term about the FIRST magnet's axis,
so the hybrid depends on the order. ER5 put the core magnet first; in the trials MagnetSystem's pair list
(np.triu_indices over the arm list, M5's 48 then core_layout's entries) puts first whichever comes first in
core_layout (the piece before its own core magnet). Every theta point is evaluated in BOTH orders against the same
fine reference; ER5's rule is applied to each order separately, and a point (hence a trajectory, P4.0, a d level)
passes only if both orders pass. The ER5-order numbers are ER5's computation unchanged (selftest: bit-identical).

  p40     P4.0: real placement, c = 0.2 mm, core = the 8 corner core magnets of `magnets.core_layout`, piece = ER5's
          U-layer corner (-1,-1,1). Stop PG8 if any theta fails.
  p4d     P4.d (--arm PG8|PG20): the piece magnet direction displaced from its validated circle
          {n . e_z = cos beta0} by d in {0.5, 1, 2, 4, 8, 12} deg toward / away from the turn axis (polar angle
          beta0 -/+ d, azimuth kept; the magnet stays on its radial line at its own radius), then swept about U.
          Increasing d; halt at the first failing d; D_val = largest d such that every grid point with displacement
          <= d passes; stop the arm if D_val < 0.5 deg; 8 h budget of summed run time (D_val = largest completed and
          passed d if it is reached). PG20: edge (-1,0,1) and corner (-1,-1,1) with all 20 core magnets; PG8: corner
          with the 8 corner core magnets. PG8 refuses to start unless P4_0.json exists and passed.
  selftest  reproduces committed points of ER5's own 20-magnet real-placement V3-turn
          (experiments/ER5_magnet_validation/results/er5_4x3_N35.json, "V3_turn" entries with placement "real"),
          recomputes Fn and asserts 1.92 N, checks the table's sha256 and ER5's pass flags under this file's pass rule.

Usage (WSL, repo root; OMP_NUM_THREADS=1 recommended):
    ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9g_v3turn.py selftest
    ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9g_v3turn.py p40
    ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9g_v3turn.py p4d --arm PG20 [--budget-h 8]
Protocol runs write results/hybrid_g/static/P4_0.json or P4d_<arm>.json (exclusive create: an existing file is never
overwritten), checkpointing every theta row to <name>.partial.jsonl so an interrupted run resumes; they refuse to start
unless this file and er5_checks.py are committed and unmodified. Any non-protocol setting (--thetas, --d-grid,
--quad-near, --quad-far, --budget-h other than 8) is a TEST run: it must name --out-dir outside the repository and
its output is labelled "NOT PROTOCOL SETTINGS".

Path deviation (G.4): d(n) = min_k |arccos(|n . e_k|) - beta0|. The displaced trajectories keep the deviation from the
turn-axis circle, |arccos(|n . e_z|) - beta0|, equal to d at every theta (rotation about z leaves n_z bit-identical).
G.4's min over k can be smaller (the displaced point can approach another axis' circle); every row records both.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ER5DIR = REPO / "experiments" / "ER5_magnet_validation"
sys.path.insert(0, str(ER5DIR))
import er5_checks as ER5  # noqa: E402  (also puts D8_alignment on sys.path and imports d8_1b_checks)

D8 = ER5.D8
from rubiknetic.cube_physics.magnets import (  # noqa: E402
    MagnetParams, core_layout, near_field_tables, pair_forces)

# ------------------------------------------------------------------ fixed protocol settings (G.6, P4)
ER5_RESULT = ER5DIR / "results" / "er5_4x3_N35.json"
SIZE_TAG = "4x3_N35"
TABLE_NAME = "tilt_4x3_1.19T_s1_r8_h1.5_q16x48.npz"
QUAD_NEAR = tuple(D8.REF_QUAD)          # (32, 96), ER5/D8's reference quadrature within r2
QUAD_FAR = tuple(ER5.FAR_QUAD)          # (6, 16) beyond r2
THETAS = tuple(range(0, 91))            # deg, 1 deg steps (P4.0 text; P4.d uses the same grid)
D_GRID = (0.5, 1.0, 2.0, 4.0, 8.0, 12.0)
DIRECTIONS = ("toward", "away")
BUDGET_H = 8.0
D_VAL_MIN = 0.5
HOMES = {"edge": (-1, 0, 1), "corner": (-1, -1, 1)}   # ER5's V3-turn pieces (U layer, z = +1)
TURN_AXIS = np.array([0.0, 0.0, 1.0])                 # U; ER5.rz turns about +z
BETA0_DEG = {"edge": 45.0, "corner": float(np.degrees(np.arccos(1.0 / np.sqrt(3.0))))}
FN_REF_N = 1.92                         # protocol's rounded reference; recomputed and asserted
F_TOL_REL, T_FRAC, T_FLOOR_NM = 0.05, 0.05, 2e-5
ARMS = {"PG8": {"core": "corner", "kinds": ("corner",)},
        "PG20": {"core": "all", "kinds": ("edge", "corner")}}
OUT_DEFAULT = HERE / "results" / "hybrid_g" / "static"


def magnet_params() -> MagnetParams:
    dia, length, grade = ER5.SIZES[SIZE_TAG]
    return MagnetParams(diameter=dia, length=length, grade=grade)


# ------------------------------------------------------------------ geometry
def axis_dev_deg(n, axis, beta0_deg: float) -> float:
    """|arccos(|n . axis|) - beta0| in degrees (deviation from one validated circle)."""
    c = min(1.0, abs(float(np.dot(n, axis))))
    return abs(float(np.degrees(np.arccos(c))) - beta0_deg)


def path_dev_deg(n, beta0_deg: float) -> float:
    """G.4: d(n) = min over k in {x, y, z} of |arccos(|n . e_k|) - beta0|, degrees."""
    return min(axis_dev_deg(n, e, beta0_deg) for e in np.eye(3))


def displaced_direction(n0, axis, beta0_deg: float, d_deg: float, direction: str) -> np.ndarray:
    """n0's direction moved off the circle {n . axis = cos beta0} by d along the meridian through n0 (azimuth about
    `axis` kept): polar angle beta0 - d ('toward' the axis) or beta0 + d ('away')."""
    n0 = np.asarray(n0, float)
    a = np.asarray(axis, float)
    assert abs(float(np.degrees(np.arccos(np.clip(n0 @ a, -1, 1)))) - beta0_deg) < 1e-9, "n0 is not on its circle"
    e = n0 - (n0 @ a) * a
    e /= np.linalg.norm(e)
    sgn = {"toward": -1.0, "away": +1.0}[direction]
    beta = np.radians(beta0_deg + sgn * d_deg)
    return np.cos(beta) * a + np.sin(beta) * e


def core_set(mp: MagnetParams, which: str):
    """Core magnets (pos, dir, home label) from `magnets.core_layout` (real radii, clearance 2e-4), in its order."""
    mags = [g for g in core_layout(mp) if g["body"] == "core"]
    if which == "corner":
        mags = [g for g in mags if g["kind"] == "core_corner"]
    elif which != "all":
        raise ValueError(which)
    labels = [tuple(int(v) for v in np.round(g["dir"] / np.abs(g["dir"]).max())) for g in mags]
    return np.array([g["pos"] for g in mags]), np.array([g["dir"] for g in mags]), labels


def trial_piece_first(mp: MagnetParams, which: str, kind: str) -> np.ndarray:
    """Pair order in the trials, per core magnet of core_set(mp, which): True where the piece magnet is the FIRST
    magnet (index i) of the pair. MagnetSystem's pair list is np.triu_indices over the arm's magnet list (i < j), and
    the arm lists are M5's 48 (if any) followed by core_layout's entries in core_layout's order (PG20: all 40; PG8: the
    16 corner entries), so i is whichever of the two comes first in core_layout's list. pair_forces expands the
    near-field term about magnet i's axis, so the order changes the hybrid result. Checked against a built
    MagnetSystem's pair list in tests/test_er9g_v3turn.py."""
    mags = core_layout(mp)
    if which == "corner":
        mags = [g for g in mags if g["kind"] in ("corner", "core_corner")]
    lab = lambda g: tuple(int(v) for v in np.round(g["dir"] / np.abs(g["dir"]).max()))   # noqa: E731
    home = HOMES[kind]
    i_piece = next(i for i, g in enumerate(mags) if g["body"] != "core" and lab(g) == home)
    _, _, labels = core_set(mp, which)
    i_core = {lab(g): i for i, g in enumerate(mags) if g["body"] == "core"}
    return np.array([i_piece < i_core[c] for c in labels])


def er5_core_set(mp: MagnetParams):
    """ER5's own 20-magnet real-placement core (er5_checks.core_layout), for the reproduction."""
    core, _ = ER5.core_layout(mp, "real")
    return (np.array([v[0] for v in core.values()]), np.array([v[1] for v in core.values()]),
            [tuple(int(x) for x in h) for h in core])


def piece_magnet(mp: MagnetParams, kind: str):
    """(p0, n0) of ER5's real-placement piece magnet for that kind (er5_checks.core_layout)."""
    _, piece = ER5.core_layout(mp, "real")
    p0, n0, k = piece[HOMES[kind]]
    assert k == kind
    return np.asarray(p0, float), np.asarray(n0, float)


def trajectory_start(mp: MagnetParams, kind: str, d_deg: float, direction: str | None):
    """Start pose (p, n) of the swept piece magnet. d = 0: ER5's exact (p0, n0). d > 0: displaced direction, same radius
    (the magnet stays on its piece's radial line; B1 pieces rotate about the centre, so the radius is invariant)."""
    p0, n0 = piece_magnet(mp, kind)
    if d_deg == 0:
        return p0, n0
    n = displaced_direction(n0, TURN_AXIS, BETA0_DEG[kind], d_deg, direction)
    return np.linalg.norm(p0) * n, n


# ------------------------------------------------------------------ one theta row (ER5's loop body + extras)
def eval_row(mp, spline, fn_nom, cp, cn, labels, own, p0, n0, deg, beta0_deg,
             quad_near=QUAD_NEAR, quad_far=QUAD_FAR, piece_first=None) -> dict:
    """ER5 v3_turn's per-theta computation, unchanged (same calls, same order, same accumulation), for an arbitrary
    core set and start pose: the hybrid with the core magnet FIRST in every pair (ER5 order; fields F_err_rel_Fn,
    T_err_Nm). Also the hybrid in the TRIAL order (piece_first[i]: the piece magnet is pair index i; fields
    F_err_rel_Fn_trial, T_err_Nm_trial), against the same fine reference (force on, and torque about, the piece
    magnet). Plus reported-only extras: per near pair (own core magnet / others) errors in both orders, tilt, clamped
    z and the path deviations of the piece direction. piece_first=None: trial fields are omitted."""
    R = ER5.rz(deg)
    pm, nm = R @ p0, R @ n0
    p = np.vstack([cp, pm]); n = np.vstack([cn, nm])
    k = len(cp)
    ii = np.arange(k); jj = np.full(k, k)
    F, T, _ = pair_forces(mp, spline, ii, jj, p, n)
    fh, th = F[k], T[k]
    if piece_first is not None:
        pf = np.asarray(piece_first, bool)
        assert pf.shape == (k,)
        it = np.where(pf, k, np.arange(k)); jt = np.where(pf, np.arange(k), k)
        Ft, Tt, _ = pair_forces(mp, spline, it, jt, p, n)
        fh_t, th_t = Ft[k], Tt[k]
    ff, tf = np.zeros(3), np.zeros(3)
    near_tilts, near_perp = [], 0
    pairs = []
    for i in range(k):
        dist = np.linalg.norm(pm - cp[i])
        near = dist < mp.r2
        f, t, _ = D8.fine_pair(mp, cp[i], cn[i], pm, nm, *(quad_near if near else quad_far))
        ff += f; tf += t
        if near:
            c = float(abs(cn[i] @ nm))
            near_tilts.append(float(np.degrees(np.arccos(min(1.0, c)))))
            near_perp += int(c <= ER5.COS45)
            # ---- extras (reported only; not part of ER5's rule)
            Fp, Tp, _ = pair_forces(mp, spline, np.array([0]), np.array([1]),
                                    np.vstack([cp[i], pm]), np.vstack([cn[i], nm]))
            z = float((pm - cp[i]) @ cn[i])
            extra = {}
            if piece_first is not None:
                a, b = (1, 0) if pf[i] else (0, 1)          # (i, j) in the 2-magnet list [core, piece]
                Fq, Tq, _ = pair_forces(mp, spline, np.array([a]), np.array([b]),
                                        np.vstack([cp[i], pm]), np.vstack([cn[i], nm]))
                extra = {"piece_first_trial": bool(pf[i]),
                         "F_err_rel_Fn_trial": float(np.linalg.norm(Fq[1] - f) / fn_nom),
                         "T_err_Nm_trial": float(np.linalg.norm(Tq[1] - t))}
            pairs.append({"core": list(labels[i]), "own": labels[i] == own, "r_mm": float(dist * 1e3),
                          "tilt_deg": near_tilts[-1], "perpendicular": bool(c <= ER5.COS45),
                          "z_mm": z * 1e3, "clamped_z": bool(c > ER5.COS45 and abs(z) < mp.length + 1e-4),
                          "F_err_rel_Fn": float(np.linalg.norm(Fp[1] - f) / fn_nom),
                          "T_err_Nm": float(np.linalg.norm(Tp[1] - t)),
                          "fine_F_N": float(np.linalg.norm(f)), "fine_T_Nm": float(np.linalg.norm(t)), **extra})
    row = {"deg": deg, "F_err_rel_Fn": float(np.linalg.norm(fh - ff) / fn_nom),
           "T_err_Nm": float(np.linalg.norm(th - tf)), "fine_T_Nm": float(np.linalg.norm(tf)),
           "fine_F_N": float(np.linalg.norm(ff)), "max_near_tilt_deg": max(near_tilts, default=None),
           "n_near": len(near_tilts), "near_perpendicular": near_perp}
    if piece_first is not None:
        row["F_err_rel_Fn_trial"] = float(np.linalg.norm(fh_t - ff) / fn_nom)
        row["T_err_Nm_trial"] = float(np.linalg.norm(th_t - tf))
    row["near_pairs"] = pairs
    row["d_turn_axis_deg"] = axis_dev_deg(nm, TURN_AXIS, beta0_deg)
    row["d_G4_deg"] = path_dev_deg(nm, beta0_deg)
    return row


# ------------------------------------------------------------------ pass rule (ER5's, unchanged)
ORDERS = {"er5": ("F_err_rel_Fn", "T_err_Nm"), "trial": ("F_err_rel_Fn_trial", "T_err_Nm_trial")}


def apply_pass_rule(rows: list[dict], order: str = "er5", out_key: str = "pass") -> float:
    """ER5 v3_turn's rule over one trajectory, for one pair order: returns T_tol and sets r[out_key] on every row.
    T_tol depends only on the fine torques, so it is the same for both orders."""
    fk, tk = ORDERS[order]
    t_tol = max(T_FRAC * max(r["fine_T_Nm"] for r in rows), T_FLOOR_NM)
    for r in rows:
        r[out_key] = bool(r[fk] <= F_TOL_REL and r[tk] <= t_tol)
    return t_tol


def summarize_trajectory(spec: dict, rows: list[dict]) -> dict:
    rows = sorted(rows, key=lambda r: r["deg"])
    t_tol = apply_pass_rule(rows, "er5", "pass_er5")
    assert apply_pass_rule(rows, "trial", "pass_trial") == t_tol
    for r in rows:
        r["pass"] = bool(r["pass_er5"] and r["pass_trial"])       # a theta passes only if both orders pass
    passing = [r["deg"] for r in rows if r["pass"]]

    def order_summary(order):
        fk, tk = ORDERS[order]
        key = "pass_" + order
        return {"worst_F_err_rel_Fn": max(r[fk] for r in rows), "worst_T_err_Nm": max(r[tk] for r in rows),
                "first_failing_deg": next((r["deg"] for r in rows if not r[key]), None),
                "n_passing": sum(r[key] for r in rows), "pass": all(r[key] for r in rows)}

    def pmax(sel, key):
        v = [q[key] for r in rows for q in r.get("near_pairs", []) if sel(q) and key in q]
        return max(v, default=None)

    own, other = (lambda q: q["own"]), (lambda q: not q["own"])
    return {**spec, "T_tol_Nm": t_tol, "rows": rows, "n_rows": len(rows),
            "order_er5": order_summary("er5"), "order_trial": order_summary("trial"),
            "worst_F_err_rel_Fn": max(max(r[f] for r in rows) for f, _ in ORDERS.values()),
            "worst_T_err_Nm": max(max(r[t] for r in rows) for _, t in ORDERS.values()),
            "first_failing_deg": next((r["deg"] for r in rows if not r["pass"]), None),
            "n_passing": len(passing),
            "near_perpendicular_total": sum(r["near_perpendicular"] for r in rows),
            "max_near_tilt_deg": max((r["max_near_tilt_deg"] or 0) for r in rows),
            "pairs_beyond_45deg_total": sum(r["near_perpendicular"] for r in rows),
            "own_pair": {"max_F_err_rel_Fn": pmax(own, "F_err_rel_Fn"), "max_T_err_Nm": pmax(own, "T_err_Nm"),
                         "max_F_err_rel_Fn_trial": pmax(own, "F_err_rel_Fn_trial"),
                         "max_T_err_Nm_trial": pmax(own, "T_err_Nm_trial"),
                         "max_tilt_deg": pmax(own, "tilt_deg"),
                         "n_clamped_rows": sum(any(q["clamped_z"] for q in r.get("near_pairs", []) if q["own"])
                                               for r in rows)},
            "other_pairs": {"max_F_err_rel_Fn": pmax(other, "F_err_rel_Fn"), "max_T_err_Nm": pmax(other, "T_err_Nm"),
                            "max_F_err_rel_Fn_trial": pmax(other, "F_err_rel_Fn_trial"),
                            "max_T_err_Nm_trial": pmax(other, "T_err_Nm_trial"),
                            "max_tilt_deg": pmax(other, "tilt_deg"),
                            "n_near_evals": sum(1 for r in rows for q in r.get("near_pairs", []) if not q["own"]),
                            "n_clamped": sum(1 for r in rows for q in r.get("near_pairs", [])
                                             if not q["own"] and q["clamped_z"])},
            "d_turn_axis_deg_range": [min(r["d_turn_axis_deg"] for r in rows), max(r["d_turn_axis_deg"] for r in rows)],
            "d_G4_deg_range": [min(r["d_G4_deg"] for r in rows), max(r["d_G4_deg"] for r in rows)],
            "pass": bool(len(passing) == len(rows))}           # both orders pass at every theta


def d_val(levels: list[dict]) -> float:
    """Largest d such that every grid point with displacement <= d passes (levels in increasing d; a level counts only
    if it is complete and passed). 0.0 if the first level did not pass."""
    best = 0.0
    for lv in sorted(levels, key=lambda lv: lv["d_deg"]):
        if lv["complete"] and lv["pass"]:
            best = lv["d_deg"]
        else:
            break
    return best


# ------------------------------------------------------------------ provenance
def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True).stdout


def git_info() -> dict:
    files = [Path(__file__).resolve(), ER5DIR / "er5_checks.py"]
    try:
        head = _git("rev-parse", "HEAD").strip()
        rel = [str(f.relative_to(REPO)) for f in files]
        dirty = _git("status", "--porcelain", "--", *rel).strip()
        tracked = _git("ls-files", "--", *rel).split()
        return {"commit": head, "code_files": rel, "code_dirty": bool(dirty) or len(tracked) < len(rel),
                "git_status": dirty, "tracked": tracked}
    except Exception as exc:          # noqa: BLE001
        return {"commit": None, "code_dirty": True, "error": repr(exc)}


def host_info() -> dict:
    return {"platform": platform.platform(), "python": sys.version.split()[0], "numpy": np.__version__,
            "cpu_count": os.cpu_count(), "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"),
            "loadavg_start": list(os.getloadavg()) if hasattr(os, "getloadavg") else None}


def er5_committed() -> dict:
    return json.loads(ER5_RESULT.read_text())


def load_table(mp: MagnetParams, own_dir: Path | None = None) -> dict:
    """The 4x3 N35 tilt table. ER5's cached file is used only if its sha256 equals the one ER5 committed (so
    near_field_tables cannot rebuild over it); otherwise it is built (about 530 s, ER5 run_log) into own_dir."""
    expected = er5_committed()["tables_sha256"][TABLE_NAME]
    er5_file = ER5.TABLES / TABLE_NAME
    if er5_file.exists() and sha256(er5_file) == expected:
        cache, source = ER5.TABLES, "ER5 cache"
    else:
        cache, source = (own_dir or HERE / "tables" / "p4_4x3_N35"), "built here (ER5 cache absent or different)"
    t0 = time.perf_counter()
    spline = near_field_tables(mp, cache)
    f = cache / TABLE_NAME
    return {"spline": spline, "path": str(f), "source": source, "sha256": sha256(f), "sha256_er5": expected,
            "sha_matches_er5": sha256(f) == expected, "load_s": time.perf_counter() - t0}


def fn_reference(mp: MagnetParams) -> float:
    """D8 v3's Fn_nominal_N with D8.MP = mp, as ER5 computed it: fine model, 32 x 96, facing pair, 1.0 mm face gap."""
    L = mp.length
    return abs(D8.fine_pair(mp, [0, 0, 0], [0, 0, 1], [0, 0, L + 0.001], [0, 0, 1], *D8.REF_QUAD)[0][2])


def check_fn(fn: float) -> dict:
    committed = er5_committed()["V3_D8"]["Fn_nominal_N"]
    fn = float(fn)
    out = {"Fn_N": fn, "Fn_er5_committed_N": committed, "abs_diff": abs(fn - committed),
           "rounds_to_1.92": bool(round(fn, 2) == FN_REF_N)}
    assert out["rounds_to_1.92"], out
    assert out["abs_diff"] <= 1e-12 * committed, out
    return out


# ------------------------------------------------------------------ checkpointed driver
class Checkpoint:
    """Append-only JSONL: one header line, then 'session' and 'row' lines. Resumes only with identical settings."""

    def __init__(self, path: Path, settings: dict):
        self.path = path
        self.rows: dict[str, dict] = {}
        self.spent_s = 0.0
        if path.exists():
            lines = [json.loads(s) for s in path.read_text().splitlines() if s.strip()]
            if not lines or lines[0].get("type") != "header" or lines[0]["settings"] != settings:
                raise SystemExit(f"refusing to resume {path}: header missing or settings differ")
            for ln in lines[1:]:
                if ln["type"] == "row":
                    self.rows[ln["key"]] = ln["row"]
                    self.spent_s += ln["wall_s"]
                elif ln["type"] == "session":
                    self.spent_s += ln["setup_s"]
            self.resumed = True
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._append({"type": "header", "settings": settings})
            self.resumed = False

    def _append(self, obj: dict) -> None:
        with open(self.path, "a") as fh:
            fh.write(json.dumps(obj, default=float) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def session(self, setup_s: float, info: dict) -> None:
        self.spent_s += setup_s
        self._append({"type": "session", "setup_s": setup_s, **info})

    def row(self, key: str, row: dict, wall_s: float) -> None:
        row = {**row, "wall_s": wall_s}
        self.rows[key] = row
        self.spent_s += wall_s
        self._append({"type": "row", "key": key, "row": row, "wall_s": wall_s})


def traj_key(kind, direction, d_deg, deg) -> str:
    return f"{kind}|{direction}|{d_deg:g}|{deg:g}"


def run_trajectory(spec, thetas, evaluate, ckpt: Checkpoint, budget_s: float | None, deadline: float | None):
    """Rows of one trajectory (from the checkpoint where present). Returns (rows, status) with status in
    {'complete', 'budget', 'session'}."""
    rows = []
    for deg in thetas:
        key = traj_key(spec["kind"], spec["direction"], spec["d_deg"], deg)
        if key in ckpt.rows:
            rows.append(ckpt.rows[key]); continue
        if budget_s is not None and ckpt.spent_s >= budget_s:
            return rows, "budget"
        if deadline is not None and time.time() >= deadline:
            return rows, "session"
        t0 = time.perf_counter()
        row = evaluate(spec, deg)
        w = time.perf_counter() - t0
        ckpt.row(key, row, w)
        rows.append(ckpt.rows[key])
        print(f"  {key}: F {row['F_err_rel_Fn']:.4f}/{row['F_err_rel_Fn_trial']:.4f} "
              f"T {row['T_err_Nm']:.2e}/{row['T_err_Nm_trial']:.2e} (er5/trial order) near {row['n_near']} "
              f"({w:.1f} s; summed {ckpt.spent_s / 3600:.3f} h)", flush=True)
    return rows, "complete"


def run_p4d_levels(kinds, d_grid, thetas, evaluate, ckpt, budget_s, deadline=None) -> dict:
    """P4.d's order and stop rules: increasing d; within d, kinds x {toward, away}; halt after the first failing
    trajectory (the remaining trajectories of that d are skipped); budget on summed run time."""
    levels, status = [], "complete"
    for d in d_grid:
        lv = {"d_deg": d, "trajectories": [], "complete": False, "pass": None, "skipped": []}
        levels.append(lv)
        specs = [{"kind": k, "direction": s, "d_deg": d} for k in kinds for s in DIRECTIONS]
        for i, spec in enumerate(specs):
            rows, st = run_trajectory(spec, thetas, evaluate, ckpt, budget_s, deadline)
            if st != "complete":
                lv["partial"] = {**spec, "n_rows": len(rows),
                                 "rows_failing_F": [r["deg"] for r in rows
                                                    if max(r[f] for f, _ in ORDERS.values()) > F_TOL_REL]}
                status = st
                break
            tr = summarize_trajectory(spec, rows)
            lv["trajectories"].append(tr)
            if not tr["pass"]:
                lv["pass"] = False
                lv["skipped"] = specs[i + 1:]
                status = "halted"
                break
        else:
            lv["complete"], lv["pass"] = True, True
        if status != "complete":
            break
    dv = d_val(levels)
    return {"levels": levels, "status": status, "D_val_deg": dv,
            "halted_at_d_deg": next((lv["d_deg"] for lv in levels if lv["pass"] is False), None),
            "budget_reached": status == "budget", "stop_arm": dv < D_VAL_MIN,
            "summed_run_s": ckpt.spent_s}


# ------------------------------------------------------------------ CLI
def _parse_list(s: str | None, cast=float):
    return None if s is None else tuple(cast(x) for x in s.split(",") if x.strip())


def _parse_quad(s: str | None):
    return None if s is None else tuple(int(x) for x in s.lower().split("x"))


def settings_from_args(a, check: str) -> tuple[dict, bool]:
    thetas = _parse_list(a.thetas, int) or THETAS
    s = {"check": check, "size": SIZE_TAG, "table": TABLE_NAME, "quad_near": list(_parse_quad(a.quad_near) or QUAD_NEAR),
         "quad_far": list(_parse_quad(a.quad_far) or QUAD_FAR), "thetas_deg": list(thetas),
         "pass_rule": {"F_tol_rel_Fn": F_TOL_REL, "T_frac": T_FRAC, "T_floor_Nm": T_FLOOR_NM}}
    proto = (tuple(s["quad_near"]) == QUAD_NEAR and tuple(s["quad_far"]) == QUAD_FAR and tuple(thetas) == THETAS)
    if check == "P4.0":
        s.update({"arm": "PG8", "core": "corner", "kind": "corner", "piece_home": list(HOMES["corner"])})
    else:
        arm = ARMS[a.arm]
        dg = _parse_list(a.d_grid) or D_GRID
        s.update({"arm": a.arm, "core": arm["core"], "kinds": list(arm["kinds"]),
                  "piece_homes": {k: list(HOMES[k]) for k in arm["kinds"]}, "d_grid_deg": list(dg),
                  "directions": list(DIRECTIONS), "budget_h": a.budget_h, "D_val_min_deg": D_VAL_MIN})
        proto = proto and tuple(dg) == D_GRID and a.budget_h == BUDGET_H
    s["protocol_settings"] = proto
    return s, proto


def resolve_out(a, proto: bool) -> Path:
    if proto:
        if a.out_dir is not None:
            raise SystemExit("protocol settings write only to results/hybrid_g/static (do not pass --out-dir)")
        gi = git_info()
        if gi.get("code_dirty", True):
            raise SystemExit(f"refusing a protocol run: code not committed/clean ({gi}). G.12: commit first.")
        return OUT_DEFAULT
    if a.out_dir is None:
        raise SystemExit("non-protocol (test) settings need --out-dir outside the repository")
    out = Path(a.out_dir).resolve()
    if out == REPO or REPO in out.parents:
        raise SystemExit(f"test output must be outside the repository: {out}")
    return out


def _start(a, check: str, name: str):
    settings, proto = settings_from_args(a, check)
    out_dir = resolve_out(a, proto)
    final = out_dir / name
    if final.exists():
        raise SystemExit(f"refusing to overwrite {final}")
    ckpt = Checkpoint(out_dir / (name + ".partial.jsonl"), settings)
    mp = magnet_params()
    t0 = time.perf_counter()
    tab = load_table(mp)
    fn = fn_reference(mp)
    fn_check = check_fn(fn)
    setup_s = time.perf_counter() - t0
    ckpt.session(setup_s, {"git": git_info(), "host": host_info(), "utc": _dt.datetime.now(_dt.timezone.utc).isoformat()})
    deadline = None if a.stop_after_min is None else time.time() + 60 * a.stop_after_min
    return settings, proto, final, ckpt, mp, tab, fn, fn_check, deadline


def _write_final(final: Path, payload: dict) -> None:
    with open(final, "x") as fh:          # exclusive create: never overwrite
        json.dump(payload, fh, indent=1, default=float)
    print(f"wrote {final}")


def _header(settings, proto, tab, fn_check) -> dict:
    return {"protocol": "ER9 PROTOCOL.md Part G, G.6 P4 (unscored; static force-law check)",
            "label": "PROTOCOL SETTINGS" if proto else "NOT PROTOCOL SETTINGS (test run; not a result)",
            "settings": settings, "git": git_info(), "host": host_info(),
            "table": {k: v for k, v in tab.items() if k != "spline"}, "Fn_reference": fn_check,
            "utc_written": _dt.datetime.now(_dt.timezone.utc).isoformat()}


def cmd_p40(a) -> None:
    settings, proto, final, ckpt, mp, tab, fn, fn_check, deadline = _start(a, "P4.0", "P4_0.json")
    cp, cn, labels = core_set(mp, "corner")
    assert len(cp) == 8
    q_near, q_far = tuple(settings["quad_near"]), tuple(settings["quad_far"])
    spec = {"kind": "corner", "direction": "on-path", "d_deg": 0.0}
    p0, n0 = trajectory_start(mp, "corner", 0.0, None)
    pf = trial_piece_first(mp, "corner", "corner")

    def evaluate(sp, deg):
        return eval_row(mp, tab["spline"], fn, cp, cn, labels, HOMES["corner"], p0, n0, deg, BETA0_DEG["corner"],
                        q_near, q_far, pf)

    rows, st = run_trajectory(spec, settings["thetas_deg"], evaluate, ckpt, None, deadline)
    if st != "complete":
        print(f"stopped ({st}) after {len(rows)} rows; rerun to resume from {ckpt.path}")
        return
    tr = summarize_trajectory(spec, rows)
    verdict = {"pass": tr["pass"], "stop_PG8": not tr["pass"], "first_failing_deg": tr["first_failing_deg"],
               "pass_er5_order": tr["order_er5"]["pass"], "pass_trial_order": tr["order_trial"]["pass"],
               "first_failing_deg_er5_order": tr["order_er5"]["first_failing_deg"],
               "first_failing_deg_trial_order": tr["order_trial"]["first_failing_deg"],
               "worst_F_err_rel_Fn": tr["worst_F_err_rel_Fn"], "worst_T_err_Nm": tr["worst_T_err_Nm"],
               "T_tol_Nm": tr["T_tol_Nm"], "max_near_tilt_deg": tr["max_near_tilt_deg"],
               "pairs_beyond_45deg_total": tr["pairs_beyond_45deg_total"],
               "summed_run_s": ckpt.spent_s}
    _write_final(final, {**_header(settings, proto, tab, fn_check), "core_labels": [list(x) for x in labels],
                         "trajectory": tr, "verdict": verdict})


def cmd_p4d(a) -> None:
    arm = ARMS[a.arm]
    settings0, proto0 = settings_from_args(a, "P4.d")
    if a.arm == "PG8" and proto0:
        p40 = OUT_DEFAULT / "P4_0.json"
        if not p40.exists() or not json.loads(p40.read_text())["verdict"]["pass"]:
            raise SystemExit("PG8: P4.0 has not passed (G.6: stop PG8 if P4.0 fails at any theta); P4.d not run")
    settings, proto, final, ckpt, mp, tab, fn, fn_check, deadline = _start(a, "P4.d", f"P4d_{a.arm}.json")
    cp, cn, labels = core_set(mp, arm["core"])
    q_near, q_far = tuple(settings["quad_near"]), tuple(settings["quad_far"])
    starts = {}
    pfs = {k: trial_piece_first(mp, arm["core"], k) for k in arm["kinds"]}

    def evaluate(sp, deg):
        key = (sp["kind"], sp["direction"], sp["d_deg"])
        if key not in starts:
            starts[key] = trajectory_start(mp, sp["kind"], sp["d_deg"], sp["direction"])
        p0, n0 = starts[key]
        return eval_row(mp, tab["spline"], fn, cp, cn, labels, HOMES[sp["kind"]], p0, n0, deg,
                        BETA0_DEG[sp["kind"]], q_near, q_far, pfs[sp["kind"]])

    res = run_p4d_levels(arm["kinds"], settings["d_grid_deg"], settings["thetas_deg"], evaluate, ckpt,
                         3600 * a.budget_h, deadline)
    if res["status"] == "session":
        print(f"session limit reached; rerun to resume from {ckpt.path} (summed {ckpt.spent_s / 3600:.3f} h)")
        return
    verdict = {k: res[k] for k in ("D_val_deg", "halted_at_d_deg", "budget_reached", "stop_arm", "status",
                                   "summed_run_s")}
    verdict["D_val_rule"] = "a grid point passes only if both pair orders (ER5: core first; trial: as in MagnetSystem) pass"
    verdict["first_failure_by_order"] = {
        order: next(({"d_deg": lv["d_deg"], "kind": t["kind"], "direction": t["direction"],
                      "deg": t["order_" + order]["first_failing_deg"]}
                     for lv in res["levels"] for t in lv["trajectories"] if not t["order_" + order]["pass"]), None)
        for order in ORDERS}
    _write_final(final, {**_header(settings, proto, tab, fn_check), "core_labels": [list(x) for x in labels],
                         "levels": res["levels"], "verdict": verdict})


def selftest(thetas=(0, 17, 45), quiet=False) -> dict:
    """Reproduce committed ER5 V3-turn points (real placement, all 20 core magnets, edge and corner)."""
    mp = magnet_params()
    out = {}
    tab = load_table(mp)
    out["table"] = {k: v for k, v in tab.items() if k != "spline"}
    assert tab["sha_matches_er5"], out["table"]
    t0 = time.perf_counter()
    out["Fn"] = check_fn(fn_reference(mp))
    out["Fn"]["wall_s"] = time.perf_counter() - t0
    fn = out["Fn"]["Fn_N"]
    # magnets.core_layout's core equals ER5's real core (order and values)
    a_p, a_n, a_l = core_set(mp, "all"); b_p, b_n, b_l = er5_core_set(mp)
    out["core_layout_vs_er5"] = {"same_labels": a_l == b_l, "max_abs_pos_m": float(np.abs(a_p - b_p).max()),
                                 "max_abs_dir": float(np.abs(a_n - b_n).max())}
    com = er5_committed()
    # pass-rule arithmetic on every committed trajectory
    out["pass_rule_on_committed"] = []
    for t in com["V3_turn"]:
        rows = [{k: v for k, v in r.items() if k != "pass"} for r in t["rows"]]
        tol = apply_pass_rule(rows)
        out["pass_rule_on_committed"].append({
            "placement": t["placement"], "kind": t["kind"], "T_tol_equal": tol == t["T_tol_Nm"],
            "pass_flags_equal": [r["pass"] for r in rows] == [r["pass"] for r in t["rows"]]})
    fields = ("F_err_rel_Fn", "T_err_Nm", "fine_T_Nm", "fine_F_N", "max_near_tilt_deg", "n_near", "near_perpendicular")
    out["points"] = []
    for t in com["V3_turn"]:
        if t["placement"] != "real":
            continue
        kind = t["kind"]
        p0, n0 = piece_magnet(mp, kind)
        for deg in thetas:
            ref = t["rows"][deg]
            assert ref["deg"] == deg
            t1 = time.perf_counter()
            # with the trial order also evaluated (as in P4 runs): the ER5-order fields must still be bit-identical
            row = eval_row(mp, tab["spline"], fn, b_p, b_n, b_l, HOMES[kind], p0, n0, deg, BETA0_DEG[kind],
                           piece_first=trial_piece_first(mp, "all", kind))
            w = time.perf_counter() - t1
            diffs = {f: (0.0 if row[f] == ref[f] else
                         abs(row[f] - ref[f]) / max(abs(ref[f]), 1e-300)) for f in fields}
            out["points"].append({"kind": kind, "deg": deg, "bit_identical": all(v == 0.0 for v in diffs.values()),
                                  "max_rel_diff": max(diffs.values()), "n_near": row["n_near"], "wall_s": w})
            if not quiet:
                print(f"  ER5 real {kind} deg {deg}: bit-identical {out['points'][-1]['bit_identical']} "
                      f"(max rel diff {max(diffs.values()):.1e}); n_near {row['n_near']}; {w:.1f} s", flush=True)
    out["pass"] = bool(out["core_layout_vs_er5"]["same_labels"]
                       and out["core_layout_vs_er5"]["max_abs_pos_m"] == 0.0
                       and all(x["T_tol_equal"] and x["pass_flags_equal"] for x in out["pass_rule_on_committed"])
                       and all(p["max_rel_diff"] <= 1e-12 for p in out["points"]))
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("check", choices=("p40", "p4d", "selftest"))
    ap.add_argument("--arm", choices=tuple(ARMS))
    ap.add_argument("--budget-h", type=float, default=BUDGET_H)
    ap.add_argument("--stop-after-min", type=float, default=None,
                    help="end this session after N minutes (checkpoint kept; rerun resumes; not a budget)")
    ap.add_argument("--selftest-thetas", default="0,17,45")
    # test-only knobs (any of them makes the run non-protocol)
    ap.add_argument("--thetas"); ap.add_argument("--d-grid"); ap.add_argument("--quad-near"); ap.add_argument("--quad-far")
    ap.add_argument("--out-dir")
    a = ap.parse_args(argv)
    if a.check == "selftest":
        r = selftest(_parse_list(a.selftest_thetas, int))
        print(json.dumps({k: v for k, v in r.items()}, indent=1, default=float))
        print("SELFTEST PASS" if r["pass"] else "SELFTEST FAIL")
        sys.exit(0 if r["pass"] else 1)
    if a.check == "p4d" and a.arm is None:
        ap.error("p4d needs --arm PG8|PG20")
    (cmd_p40 if a.check == "p40" else cmd_p4d)(a)


if __name__ == "__main__":
    main()
