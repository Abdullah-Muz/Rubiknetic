"""Scored G1 runner for M4 (experiments/PHASE_1_M4_PREREGISTRATION.md, section 6 item 3).

M4 = M1's contact-only cube at rigid radius (B1, radial_preload = 0) plus the 48 passive D8-1b magnets
(rubiknetic.cube_physics.magnets, revision 2). The trial logic is M1's scored harness (scored.py), unchanged; this
runner adds, around it:
  * the B1 base model (scored.params_for wrapped in-process, as in D8_alignment/d8_1b_stage1.py);
  * magnet installation per process: the global passive callback is paused while any model compiles, trial body ids
    are asserted against the magnet layout, magnet stats are reset per trial;
  * a V6-style start-up check (rule 1) and a check that MagnetSystem._buf is the force used in the step (E1-6m);
  * rule 2 (magnet validity fails operational trials) and rule 3 (labels abuse trials);
  * E1-5s snap-back (d8_1b_stage1.run_snap, imported unchanged);
  * the D8-0 per-piece misalignment after every move and the E1-4 growth-slope criterion;
  * E1-6m magnet energy / work / impulse per move, through a read-only Monitor subclass (step hook);
  * E1-6n (no-magnet arm, reported only) and the M4 E1-7 factors.
E1-8 (throughput) is out of scope here: it is a separate bench script (pre-registration section 6 item 4).

Usage (WSL, from repo root):
    ~/.venvs/rubiknetic/bin/python experiments/E4_scored_m4/run.py \
        <E1-1|...|E1-6|E1-5s|E1-6n|E1-7|all> [--jobs N] [--dry-run]
    ~/.venvs/rubiknetic/bin/python experiments/E4_scored_m4/run.py smoke --smoke    # NOT scored (seeds 95-96)

Integrity: refuses to run from uncommitted code (M1 frozen paths plus M4_FROZEN_PATHS); never overwrites an existing
record; no exclusions (a failing trial is written with pass = False and its reasons). Scored runs are also refused
while the E1-6c threshold (pre-registration section 8 decision 1, option (c)) has not been set by an amendment.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
D8 = REPO / "experiments" / "D8_alignment"
sys.path.insert(0, str(D8))
import d8_1b_stage1 as ST  # noqa: E402  (D8-0 misalignment() and run_snap(); imported unchanged)

from rubiknetic.cube_logic import parse  # noqa: E402
from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_physics import scored  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml  # noqa: E402
from rubiknetic.cube_physics.magnets import (  # noqa: E402
    TABLE_QUAD,
    TILT_H_DEG,
    MagnetParams,
    MagnetSystem,
    near_field_tables,
)


def _load_e1_runner():
    spec = importlib.util.spec_from_file_location("e1_scored_run", REPO / "experiments" / "E1_scored" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


E1 = _load_e1_runner()          # M1's trial lists, reused exactly (seeds shifted below)

# ---- paths and frozen constants -----------------------------------------------------------------------------------
OUT = HERE / "results"                   # scored magnet arm
OUT_NOMAG = HERE / "results_nomag"       # E1-6n: no-magnet arm, reported only
SMOKE = HERE / "smoke"                   # unscored smoke runs
TABLES = D8 / "results" / "tables"
CHECKS = D8 / "results" / "d8_1b_checks.json"
M4_FROZEN_PATHS = ["experiments/PHASE_1_M4_PREREGISTRATION.md", "experiments/E4_scored_m4/run.py",
                   "experiments/E4_scored_m4/analyze.py", "experiments/D8_alignment/d8_1b_stage1.py",
                   "experiments/D8_alignment/magnets.py", "experiments/D8_alignment/results/d8_1b_checks.json"]

SEED_SHIFT = 5000                        # rule 4: M1 offsets + 5000
SCORED_SEED_RANGE = (6000, 6999)
BASE_OVERRIDES = {"radial_preload": 0.0}  # B1: rigid radius (section 1)
SLOPE_LIMIT_DEG_PER_MOVE = 0.005         # E1-4 growth slope (40-move runs)
SNAP_LIMIT_DEG = 0.5                     # E1-5s, |delta| >= SNAP_MIN_SCORED_DEG
SNAP_MIN_SCORED_DEG = 3.0
SNAP_DELTAS_DEG = (1, 2, 3, 5, 8)
SNAP_SEED_BASE = 6550                    # seed = 6550 + 10 * rep + |delta|; each +/- pair shares one seed
P_REL, P_ABS_J = 0.10, 0.05e-3           # E1-6m <P>: |W + dU| <= 10 % of (max - min U) + 0.05 mJ
RULE2 = {"E1-1", "E1-2", "E1-3", "E1-4", "E1-5", "E1-5s", "E1-6a"}
RULE3 = {"E1-6b", "E1-6c", "E1-6t"}
# E1-6c (Amendment 1, P-24, 2026-11-15): M1's approved categorical criterion only; twist, penetration and the torque at
# 15 deg are reported. "quantity": None means no quantitative E1-6c threshold. The standards-anchored check is E1-6t.
E16C_THRESHOLD: dict | None = {"rule": "M1 categorical only; twist, penetration, torque at 15 deg reported (P-24)",
                               "quantity": None}
# E1-6t (Amendment 1, P-24): toy-standard torque test in the form of 16 CFR 1500.53(e): 0.45 N m (4 in-lb) on each
# corner about its diagonal, applied over 5 s, held 10 s, released; both directions. Pass: after release the observed
# state is valid and solved, and penetration <= 0.5 mm throughout (M1's integrity limit). Rule 3 applies.
E16T_TORQUE_NM, E16T_RAMP_S, E16T_HOLD_S, E16T_PEN_LIMIT_MM = 0.45, 5.0, 10.0, 0.5
E16T_SEED_BASE = 6640                    # seed = 6640 + 2 * corner index + (0 for +, 1 for -)
OPERATIONAL = ["E1-1", "E1-2", "E1-3", "E1-4", "E1-5", "E1-5s", "E1-6", "E1-6t"]
NOMAG_EXPS = ["E1-2", "E1-3", "E1-4", "E1-5", "E1-5s", "E1-6", "E1-6t"]   # E1-6n (E1-5s included: see README)

MAGNET_SIZES = {"3x1.5_N35": (0.003, 0.0015, "N35"), "4x1.5_N35": (0.004, 0.0015, "N35"),
                "4x2_N35": (0.004, 0.002, "N35"), "4x2_N52": (0.004, 0.002, "N52")}
E17_FACTORS = [(n, v) for n, v in E1.E17_FACTORS if n != "radial_preload"] + [   # radial preload dropped (B1)
    ("magnet", ["none", "3x1.5_N35", "4x1.5_N35", "4x2_N35", "4x2_N52"]),
    ("face_gap_mm", [0.5, 1.0, 1.5]),
    ("magnet_scale", [0.67, 1.0]),
]
NOMINAL = ({x for x in E1.NOMINAL if x[0] != "radial_preload"}
           | {("magnet", "4x2_N35"), ("face_gap_mm", 1.0), ("magnet_scale", 1.0)})
_MAGNET_KEYS = ("magnet", "face_gap_mm", "magnet_scale")


class Refused(Exception):
    """A trial the runner must not run (missing or unvalidated magnet tables)."""


# ---- trial lists ----------------------------------------------------------------------------------------------------
def shift_seed(seed: int) -> int:
    return seed + SEED_SHIFT


def _shift(lst: list) -> list:
    out = []
    for tid, kind, kw in lst:
        s = kw["seed"]
        assert tid.endswith(f"_s{s}"), tid
        kw2 = copy.deepcopy(kw)
        kw2["seed"] = shift_seed(s)
        out.append((tid[: -len(f"_s{s}")] + f"_s{shift_seed(s)}", kind, kw2))
    return out


def snap_trials() -> list:
    t = []
    for rep in (0, 1):
        for deg in SNAP_DELTAS_DEG:
            seed = SNAP_SEED_BASE + 10 * rep + deg
            for sgn in (1, -1):
                t.append((f"snap_{sgn * deg:+d}_s{seed}", "snap", {"delta_deg": float(sgn * deg), "seed": seed}))
    return t


def e17_trials() -> list:
    t, seen = [], set()
    for name, values in E17_FACTORS:
        for v in values:
            ov = {} if (name, v) in NOMINAL else {name: v}
            key = json.dumps(ov, sort_keys=True, default=list)
            if key in seen:
                continue
            seen.add(key)
            tag = "nominal" if not ov else (f"{name}={v}".replace(" ", "").replace("(", "").replace(")", "")
                                            .replace(",", "-"))
            for sname, seq in (("6move", "U U' R R' F F'"), ("sexy6", E1.SEXY6.strip())):
                t.append((f"{tag}__{sname}", "seq", {"moves": seq, "seed": shift_seed(1000), "overrides": ov}))
    return t


def e16t_trials() -> list:
    corners = [h for h in HOME_POSITIONS if all(h)]
    t = []
    for i, c in enumerate(corners):
        for j, sgn in enumerate((1.0, -1.0)):
            seed = E16T_SEED_BASE + 2 * i + j
            tag = "".join("p" if v > 0 else "n" for v in c)
            t.append((f"std_{tag}_{'pos' if sgn > 0 else 'neg'}_s{seed}", "twist_std",
                      {"corner": list(c), "seed": seed, "peak_Nm": sgn * E16T_TORQUE_NM}))
    return t


def trials(exp: str) -> list:
    """(trial_id, kind, kwargs) for one M4 experiment, as pre-registered."""
    if exp in ("E1-1", "E1-2", "E1-3", "E1-4", "E1-5", "E1-6"):
        return _shift(E1.trials(exp))
    if exp == "E1-5s":
        return snap_trials()
    if exp == "E1-6t":
        return e16t_trials()
    if exp == "E1-7":
        return e17_trials()
    raise SystemExit(f"unknown experiment {exp}")


def smoke_trials() -> list:
    """Unscored smoke trials (seeds outside every registered range)."""
    return [("smoke_seq_s95", "seq", {"moves": "U R' F", "seed": 95}, "E1-4"),
            ("smoke_snap_+5_s96", "snap", {"delta_deg": 5.0, "seed": 96}, "E1-5s")]


def sub_experiment(exp: str, kind: str) -> str:
    if exp == "E1-6":
        return {"openpad": "E1-6a", "opposed": "E1-6b", "twist": "E1-6c"}[kind]
    return exp


# ---- magnet configuration, tables and validation ------------------------------------------------------------------
def magnet_params_for(ov: dict) -> MagnetParams | None:
    """Pops the M4 E1-7 factors from a trial's overrides and returns its MagnetParams (None = no magnets).
    Nominal = MagnetParams() exactly. A face-gap factor sets the wall: wall = (face gap - M1 nominal piece gap) / 2;
    otherwise the wall stays 0.4 mm (so M1's piece-gap factor changes the face gap by the same amount)."""
    name = ov.pop("magnet", "4x2_N35")
    face_gap_mm = ov.pop("face_gap_mm", None)
    scale = ov.pop("magnet_scale", 1.0)
    if name == "none":
        return None
    dia, length, grade = MAGNET_SIZES[name]
    kw = {"diameter": dia, "length": length, "grade": grade, "scale": scale}
    if face_gap_mm is not None:
        kw["wall"] = (face_gap_mm * 1e-3 - M1Params().gap) / 2
    return MagnetParams(**kw)


def table_path(mp: MagnetParams) -> Path:
    """Same file name as magnets.near_field_tables (default grid and quadrature)."""
    return TABLES / (f"tilt_{mp.diameter*1e3:g}x{mp.length*1e3:g}_{mp.br:g}T_s{mp.scale:g}_r{mp.r2*1e3:g}"
                     f"_h{TILT_H_DEG:g}_q{TABLE_QUAD[0]}x{TABLE_QUAD[1]}.npz")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def v3_record_for(mp: MagnetParams) -> dict | None:
    """V3 result for this magnet SIZE (pre-registration section 4: each new size must pass V3 at that size).
    Searched in experiments/D8_alignment/results/d8_1b_checks*.json by magnet_params diameter and length."""
    for f in sorted((D8 / "results").glob("d8_1b_checks*.json")):
        j = json.loads(f.read_text())
        p = j.get("magnet_params", {})
        if np.isclose(p.get("diameter", -1), mp.diameter) and np.isclose(p.get("length", -1), mp.length):
            v3 = j.get("V3", {})
            if v3.get("pass") and "validated_tilt_deg" in v3:
                return {"validated_tilt_deg": float(v3["validated_tilt_deg"]), "v3_source": _rel(f),
                        "v3_source_sha256": _sha256(f)}
    return None


def magnet_availability(mp: MagnetParams) -> dict:
    """Raises Refused unless the tables for mp exist on the expected grid and V3 passed at mp's size. Never builds
    tables (each takes about 20 minutes and must pass V3 first)."""
    path = table_path(mp)
    if not path.exists():
        raise Refused(f"near-field table {_rel(path)} does not exist; build it and run V3 at this size "
                      f"({mp.diameter*1e3:g}x{mp.length*1e3:g} mm {mp.grade}, scale {mp.scale:g}) before scoring")
    with np.load(path) as f:
        grid_ok = (np.array_equal(f["rho"], np.linspace(0.0, mp.r2 + 0.001, 37))
                   and np.array_equal(f["z"], np.linspace(mp.length + 0.0001, mp.r2 + 0.001, 31)))
    if not grid_ok:
        raise Refused(f"table {path.name} is not on the default grid (near_field_tables would rebuild it)")
    v3 = v3_record_for(mp)
    if v3 is None:
        raise Refused(f"no passing V3 record for magnet size {mp.diameter*1e3:g}x{mp.length*1e3:g} mm in "
                      f"{(D8 / 'results').relative_to(REPO)}/d8_1b_checks*.json")
    return {"table_file": _rel(path), "table_sha256": _sha256(path), **v3}


def nominal_validated_tilt() -> float:
    return float(json.loads(CHECKS.read_text())["V3"]["validated_tilt_deg"])


# ---- process-level magnet installation -----------------------------------------------------------------------------
class RecordingMagnetSystem(MagnetSystem):
    """MagnetSystem with the force law unchanged; it keeps the last callback evaluation (poses, per-magnet forces,
    torques, energy) for the read-only E1-6m accounting. Only evaluations from apply() (stats=True) are kept."""

    last: tuple | None = None

    def forces(self, p, n, stats: bool = False):
        F, T, U = super().forces(p, n, stats)
        if stats:
            self.last = (p.copy(), F.copy(), T.copy(), U)
        return F, T, U


_MS: RecordingMagnetSystem | None = None
_MS_KEY = None
_ORIG: dict = {}
TABLES_PROVIDER = None          # tests: callable(mp) -> splines (coarse tables); None = validated files only


def _compile_paused(xml, *a, **k):
    # The passive callback is global; MuJoCo's compiler runs an internal forward pass that would call it on a
    # half-built model. Pause it during compilation (no simulation step happens; no physics changes).
    MagnetSystem.uninstall()
    try:
        model = _ORIG["compile"](xml, *a, **k)
    finally:
        if _MS is not None:
            _MS.install()
    if _MS is not None:
        body = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, g["body"]) for g in _MS.mags]
        assert np.array_equal(body, _MS.body), "trial model body ids differ from the magnet layout"
    return model


def configure_process() -> None:
    """Idempotent: B1 base model for every harness trial, paused compilation, magnet-aware Monitor."""
    if _ORIG:
        return
    _ORIG.update(compile=mujoco.MjModel.from_xml_string, params_for=scored.params_for, monitor=scored.Monitor)
    orig_pf = _ORIG["params_for"]
    scored.params_for = lambda setup, **kw: orig_pf(setup, **{**BASE_OVERRIDES, **kw})
    mujoco.MjModel.from_xml_string = _compile_paused
    scored.Monitor = MagnetMonitor


def restore_process() -> None:
    """Undo configure_process (tests)."""
    global _MS, _MS_KEY
    MagnetSystem.uninstall()
    _MS, _MS_KEY = None, None
    if _ORIG:
        mujoco.MjModel.from_xml_string = _ORIG["compile"]
        scored.params_for = _ORIG["params_for"]
        scored.Monitor = _ORIG["monitor"]
        _ORIG.clear()


def _tables_for(mp: MagnetParams):
    if TABLES_PROVIDER is not None:
        return TABLES_PROVIDER(mp)
    magnet_availability(mp)                       # refuses before near_field_tables could start a build
    return near_field_tables(mp, TABLES)


def use_magnets(mp: MagnetParams | None, gap: float) -> RecordingMagnetSystem | None:
    """Install the magnet system for (mp, piece gap) in this process (reused if unchanged), or none."""
    global _MS, _MS_KEY
    configure_process()
    key = (mp, gap)
    if key == _MS_KEY and (_MS is not None or mp is None):
        if _MS is not None:
            _MS.install()
        return _MS
    MagnetSystem.uninstall()
    _MS, _MS_KEY = None, None
    if mp is None:
        _MS_KEY = key
        return None
    p = M1Params(**{**BASE_OVERRIDES, "gap": gap})
    m = _compile_paused(build_m1_xml(p))
    _MS = RecordingMagnetSystem(m, p.pitch, p.gap, mp, tables=_tables_for(mp))
    _MS_KEY = key
    _MS.install()
    return _MS


# ---- E1-6m and D8-0 accounting: a read-only monitor ----------------------------------------------------------------
class MagnetMonitor(scored.Monitor):
    """scored.Monitor plus, per move (begin_turn/end_turn of scored.run_sequence_trial):
    the D8-0 misalignment after the move; with magnets: dU_mag, W_mag, U range, peak force/torque and impulse of the
    magnets on the turning layer. W_mag is accumulated in the AuditedSim step hook from MagnetSystem._buf, the
    generalized force the callback added to qfrc_passive inside that mj_step (one callback call per step is checked).
    Reads only; returns end_turn's result unchanged, so the M1 per-move criteria are untouched."""

    last = None

    def __init__(self, m, ro):
        super().__init__(m, ro)
        MagnetMonitor.last = self
        self.moves: list[dict] = []
        self._acc = None
        self._d = None
        self._scratch = mujoco.MjData(m)
        self._dt = m.opt.timestep
        self.misalignment_t0 = None

    def energy_at(self, d) -> float | None:
        """U_mag at d's CURRENT qpos (after mj_step, d.xpos is still the pre-step kinematics)."""
        if _MS is None:
            return None
        s = self._scratch
        s.qpos[:] = d.qpos
        mujoco.mj_kinematics(self.m, s)
        return _MS.energy(s)

    def begin_turn(self, face, members) -> None:
        super().begin_turn(face, members)
        d = self._d
        if d is not None and self.misalignment_t0 is None and not self.moves:
            self.misalignment_t0 = ST.misalignment(self.ro, d)
        if _MS is None or d is None:
            self._acc = {"magnets": False}
            return
        u0 = self.energy_at(d)
        self._acc = {"magnets": True, "U0": u0, "Umin": u0, "Umax": u0, "v0": d.qvel.copy(), "W": 0.0,
                     "Wd": 0.0, "Fpk": 0.0, "Tpk": 0.0, "J": np.zeros(3), "Jax": 0.0, "steps": 0,
                     "calls0": _MS.stats["calls"], "U_first": None,
                     "mask": np.isin(_MS.body, self.turn["bodies"]), "axis": self.turn["axis"]}

    def __call__(self, d) -> None:
        super().__call__(d)
        self._d = d
        a = self._acc
        if not a or not a["magnets"]:
            return
        q, v1, dt = _MS._buf, d.qvel, self._dt
        a["W"] += float(q @ (a["v0"] + v1)) * 0.5 * dt      # pre-registered: trapezoid in qvel
        a["Wd"] += float(q @ v1) * dt                       # integrator displacement: dq = qvel_after * dt
        a["v0"] = v1.copy()
        p, F, T, U = _MS.last
        if a["U_first"] is None:
            a["U_first"] = U
        a["Umin"], a["Umax"] = min(a["Umin"], U), max(a["Umax"], U)
        mk = a["mask"]
        c = d.xpos[self.ro.core]
        Fl = F[mk].sum(axis=0)
        tau = float((T[mk] + np.cross(p[mk] - c, F[mk])).sum(axis=0) @ a["axis"])
        a["Fpk"] = max(a["Fpk"], float(np.linalg.norm(Fl)))
        a["Tpk"] = max(a["Tpk"], abs(tau))
        a["J"] += Fl * dt
        a["Jax"] += tau * dt
        a["steps"] += 1

    def end_turn(self) -> dict:
        res = super().end_turn()
        a, self._acc = self._acc, None
        d = self._d
        out = {"misalignment": ST.misalignment(self.ro, d)}
        if a and a["magnets"]:
            u1 = self.energy_at(d)
            umin, umax = min(a["Umin"], u1), max(a["Umax"], u1)
            du, rng = u1 - a["U0"], umax - umin
            calls = _MS.stats["calls"] - a["calls0"]
            out.update({
                "magnet_U_before_J": a["U0"], "magnet_U_after_J": u1, "magnet_dU_J": du,
                "magnet_W_J": a["W"], "magnet_W_displacement_J": a["Wd"], "magnet_U_range_J": rng,
                "e16m_residual_J": a["W"] + du, "e16m_bound_J": P_REL * rng + P_ABS_J,
                "e16m_P_ok": p_bound_ok(a["W"], du, rng),
                "e16m_residual_displacement_J": a["Wd"] + du,
                "layer_magnet_force_peak_N": a["Fpk"], "layer_magnet_axis_torque_peak_Nm": a["Tpk"],
                "layer_magnet_impulse_Ns": float(np.linalg.norm(a["J"])),
                "layer_magnet_axis_angular_impulse_Nms": a["Jax"],
                "magnet_steps": a["steps"], "magnet_callback_calls": calls,
                "magnet_buf_one_call_per_step": bool(calls == a["steps"]),
                "magnet_U0_vs_first_callback_J": None if a["U_first"] is None else abs(a["U_first"] - a["U0"]),
            })
        self.moves.append(out)
        return res


# ---- pass logic (pure functions) -----------------------------------------------------------------------------------
def p_bound_ok(W: float, dU: float, U_range: float) -> bool:
    """E1-6m <P>: |W_mag + dU_mag| <= 0.10 (max - min U_mag during the move) + 0.05 mJ (all J)."""
    return bool(abs(W + dU) <= P_REL * U_range + P_ABS_J)


def growth_slope(values) -> float | None:
    """Least-squares slope (deg/move) of the worst-piece error after each move (as analyze_stage1.py)."""
    v = np.asarray([x for x in values if x is not None], float)
    if len(v) < 2:
        return None
    return float(np.polyfit(np.arange(len(v)), v, 1)[0])


def apply_m4_criteria(rec: dict, sub: str, validated_tilt: float | None, magnets_on: bool) -> dict:
    """Adds the M4 criteria to a harness record. M1's verdict is kept as pass_m1_criteria; rec['pass'] is the M4
    verdict. Nothing is dropped: a failure only sets pass = False and appends a reason."""
    reasons = []
    if sub == "E1-5s":     # run_snap sets no verdict: M1 integrity + oracle (no move commanded: still solved)
        rec["ok_snap_state"] = bool(rec.get("final_observed_valid") and rec.get("final_solved"))
        rec["pass"] = bool(rec.get("integrity_ok") and "aborted" not in rec and rec.get("t0_solved")
                           and rec["ok_snap_state"])
    rec["pass_m1_criteria"] = bool(rec["pass"])
    if not rec["pass"]:
        reasons.append("M1 criteria")
    rec["validated_tilt_deg"] = validated_tilt
    if magnets_on:
        tilt = float(rec["magnet_stats"]["max_near_tilt_deg"])
        outside = tilt > validated_tilt
        rec["magnet_outside_validated_range"] = outside
        if sub in RULE2:
            rec["ok_magnet_validity"] = not outside
            if outside:
                reasons.append(f"rule 2: near-pair tilt {tilt:.3f} deg > validated {validated_tilt:g} deg")
        elif sub in RULE3:
            rec["rule3_label"] = "magnet model outside validated range" if outside else None
    if sub == "E1-4" and "per_move" in rec:
        mis = [m.get("misalignment", {}).get("max_err_deg") for m in rec["per_move"]]
        slope = growth_slope(mis)
        n = len(parse(rec["sequence"])) if "sequence" in rec else len(mis)
        rec["misalignment_growth_slope_deg_per_move"] = slope
        rec["growth_slope_is_criterion"] = n == 40
        if n == 40:
            rec["ok_growth_slope"] = slope is not None and slope < SLOPE_LIMIT_DEG_PER_MOVE
            if not rec["ok_growth_slope"]:
                reasons.append(f"E1-4 growth slope {slope} deg/move (limit < {SLOPE_LIMIT_DEG_PER_MOVE})")
    if sub == "E1-5s":
        err = rec.get("U_err_after_1s_deg")
        rec["snap_is_criterion"] = abs(rec["delta_deg"]) >= SNAP_MIN_SCORED_DEG
        if rec["snap_is_criterion"]:
            rec["ok_snap"] = err is not None and abs(err) <= SNAP_LIMIT_DEG
            if not rec["ok_snap"]:
                reasons.append(f"E1-5s |U error after 1 s| = {err} > {SNAP_LIMIT_DEG} deg")
    if sub == "E1-6t":
        pen = rec.get("penetration_mm_reported_only")
        rec["ok_e16t"] = bool(rec.get("final_solved") and pen is not None and pen <= E16T_PEN_LIMIT_MM)
        if not rec["ok_e16t"]:
            reasons.append(f"E1-6t: final_solved={rec.get('final_solved')}, penetration {pen} mm "
                           f"(limit {E16T_PEN_LIMIT_MM})")
    if sub == "E1-6c" and E16C_THRESHOLD is not None and E16C_THRESHOLD.get("quantity"):
        val = rec.get(E16C_THRESHOLD["quantity"])
        ok = val is not None and ("max" not in E16C_THRESHOLD or val <= E16C_THRESHOLD["max"]) and \
            ("min" not in E16C_THRESHOLD or val >= E16C_THRESHOLD["min"])
        rec["ok_e16c_threshold"] = bool(ok)
        if not ok:
            reasons.append(f"E1-6c threshold {E16C_THRESHOLD}: {val}")
    rec["fail_reasons"] = reasons
    rec["pass"] = not reasons
    return rec


# ---- integrity checks at runner start ------------------------------------------------------------------------------
def startup_checks(mp: MagnetParams, gap: float | None = None, seed: int = 6) -> dict:
    """Rule 1 (V6-style): the callback's qfrc contribution is unchanged by ctrl, time, qvel and act, and the installed
    callback adds exactly that contribution to qfrc_passive. E1-6m: after mj_step, MagnetSystem._buf equals the
    magnet force inside that step's qfrc_passive (with minus without the callback, same pre-step state), and the
    integrator's displacement is qvel_after * dt (so the trapezoid W differs from the displacement work)."""
    gap = M1Params().gap if gap is None else gap
    ms = use_magnets(mp, gap)
    MagnetSystem.uninstall()
    try:
        m = _compile_paused(build_m1_xml(M1Params(**{**BASE_OVERRIDES, "gap": gap})))
        MagnetSystem.uninstall()                # _compile_paused re-installs it
        d = mujoco.MjData(m)
        rng = np.random.default_rng(seed)
        for k in range(m.njnt):                 # small random pose (about 1 deg) so the magnets do work
            a = m.jnt_qposadr[k]
            if m.jnt_type[k] == mujoco.mjtJoint.mjJNT_BALL:
                q = np.zeros(4)
                ax = rng.normal(size=3)
                mujoco.mju_axisAngle2Quat(q, ax / np.linalg.norm(ax), np.radians(rng.normal(0, 1.0)))
                d.qpos[a:a + 4] = q
        mujoco.mj_forward(m, d)

        def contrib():
            d.qfrc_passive[:] = 0.0
            ms.apply(m, d)
            return d.qfrc_passive.copy()

        base = contrib()
        d.ctrl[:] = rng.uniform(-1, 1, m.nu)
        d.time = 123.4
        d.qvel[:] = rng.normal(0, 0.1, m.nv)
        if m.na:
            d.act[:] = rng.uniform(-1, 1, m.na)
        after = contrib()
        mujoco.mj_forward(m, d)
        without = d.qfrc_passive.copy()
        ms.install()
        mujoco.mj_forward(m, d)
        with_cb = d.qfrc_passive.copy()
        # _buf versus the step: same pre-step state stepped with the callback, and evaluated without it
        d_pre = mujoco.MjData(m)
        d_pre.qpos[:], d_pre.qvel[:], d_pre.ctrl[:], d_pre.time = d.qpos, d.qvel, d.ctrl, d.time
        if m.na:
            d_pre.act[:] = d.act
        qpos0, qvel0 = d.qpos.copy(), d.qvel.copy()
        calls0 = ms.stats["calls"]
        mujoco.mj_step(m, d)
        buf, qp_step, calls = ms._buf.copy(), d.qfrc_passive.copy(), ms.stats["calls"] - calls0
        MagnetSystem.uninstall()
        mujoco.mj_forward(m, d_pre)
        vel = np.zeros(m.nv)
        mujoco.mj_differentiatePos(m, vel, m.opt.timestep, qpos0, d.qpos)
        scale = float(np.abs(base).max())
        res = {
            "max_abs_magnet_qfrc": scale,
            "max_change_from_ctrl_time_qvel_act": float(np.abs(after - base).max()),
            "installed_matches_direct": float(np.abs((with_cb - without) - after).max()),
            "buf_matches_step_qfrc": float(np.abs((qp_step - d_pre.qfrc_passive) - buf).max()),
            "callback_calls_in_one_step": int(calls),
            "displacement_vs_qvel_after": float(np.abs(vel - d.qvel).max()),
            "displacement_vs_qvel_before": float(np.abs(vel - qvel0).max()),
            "integrator": ["euler", "rk4", "implicit", "implicitfast"][int(m.opt.integrator)],
        }
        res["pass"] = bool(scale > 0 and res["max_change_from_ctrl_time_qvel_act"] == 0.0
                           and res["installed_matches_direct"] <= 1e-12 * scale
                           and res["buf_matches_step_qfrc"] <= 1e-12 * scale and calls == 1)
        return res
    finally:
        if _MS is not None:
            _MS.install()


# ---- one trial ------------------------------------------------------------------------------------------------------
def run_trial(kind: str, kw: dict, magnets_on: bool) -> tuple[dict, RecordingMagnetSystem | None, dict | None]:
    """Runs one harness trial with this process's magnet configuration. Returns (record, ms, magnet_info)."""
    ov = dict(kw.get("overrides", {}))
    mp = magnet_params_for(ov)
    if not magnets_on:
        mp = None
    info = None if (mp is None or TABLES_PROVIDER is not None) else magnet_availability(mp)  # may raise Refused
    ms = use_magnets(mp, ov.get("gap", M1Params().gap))
    if ms is not None:
        ms.reset_stats()
    MagnetMonitor.last = None
    t0 = time.perf_counter()
    if kind == "seq":
        mis = ov.pop("misalign_max_deg", 1.0)
        rec = scored.run_sequence_trial(parse(kw["moves"]), kw["seed"], misalign_max_deg=mis, **ov)
        mon = MagnetMonitor.last
        for pm, extra in zip(rec["per_move"], mon.moves if mon else []):
            pm.update(extra)
        rec["misalignment_t0"] = mon.misalignment_t0 if mon else None
    elif kind == "rest":
        rec = scored.run_rest_trial(kw["seed"])
    elif kind == "forgive":
        rec = scored.run_forgiveness_trial(kw["misalign_deg"], kw["seed"])
    elif kind == "openpad":
        rec = scored.run_open_pad_trial(kw["face"], kw["seed"])
    elif kind == "opposed":
        rec = scored.run_opposed_trial(tuple(kw["faces"]), kw["torque_limit"], kw["seed"])
    elif kind == "twist":
        rec = scored.run_corner_twist_trial(tuple(kw["corner"]), kw["seed"])
    elif kind == "snap":
        rec = ST.run_snap(kw["delta_deg"], kw["seed"])
    elif kind == "twist_std":
        rec = scored.run_corner_twist_trial(tuple(kw["corner"]), kw["seed"], peak_Nm=kw["peak_Nm"],
                                            ramp_s=E16T_RAMP_S, hold_s=E16T_HOLD_S)
    else:
        raise ValueError(kind)
    rec["wall_s"] = time.perf_counter() - t0
    rec["magnets"] = None if ms is None else ms.describe()
    rec["magnet_stats"] = None if ms is None else dict(ms.stats)
    rec["magnet_table"] = info
    return rec, ms, info


def _write_new(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x") as f:                     # never overwrite an existing record
        f.write(json.dumps(rec, indent=1, default=list))


def _execute(job: dict) -> str:
    path = Path(job["out"]) / job["exp"] / f"{job['tid']}.json"
    if path.exists():
        return f"skip {job['exp']}/{job['tid']} (exists)"
    try:
        load0 = os.getloadavg()[0]
        rec, ms, info = run_trial(job["kind"], job["kw"], job["magnets"])
    except Refused as e:
        return f"REFUSED {job['exp']}/{job['tid']}: {e}"
    tilt = (info or {}).get("validated_tilt_deg", job["validated_tilt"]) if ms is not None else None
    rec.update({"experiment": job["exp"], "sub_experiment": job["sub"], "trial_id": job["tid"], "kind": job["kind"],
                "spec": job["kw"], "source_commit": job["commit"], "environment": job["env"],
                "scored": job["scored"], "smoke": job["smoke"], "reported_only": job["reported_only"],
                "arm": "magnets" if job["magnets"] else "no_magnets", "mechanism": "M4",
                "base_overrides": BASE_OVERRIDES, "startup_checks": job["startup"], "loadavg_start": load0})
    apply_m4_criteria(rec, job["sub"], tilt, ms is not None)
    _write_new(path, rec)
    return f"{'PASS' if rec['pass'] else 'FAIL'} {job['exp']}/{job['tid']} {'; '.join(rec['fail_reasons'])}"


# ---- main -----------------------------------------------------------------------------------------------------------
def require_m4_clean_commit() -> str:
    commit = scored.require_clean_commit()           # M1 frozen paths (src, lock files, E1 runner)
    dirty = scored._git("status", "--porcelain", "--", *M4_FROZEN_PATHS)
    if dirty:
        raise SystemExit("refusing to run scored trials: uncommitted changes in M4 frozen paths:\n" + dirty)
    return commit


def build_jobs(exp: str, commit: str, env: dict, validated_tilt: float, smoke: bool) -> list[dict]:
    base = {"commit": commit, "env": env, "validated_tilt": validated_tilt, "smoke": smoke, "scored": not smoke,
            "startup": None}
    jobs = []
    if smoke:
        for tid, kind, kw, sub in smoke_trials():
            jobs.append({**base, "exp": "smoke", "sub": sub, "tid": tid, "kind": kind, "kw": kw, "magnets": True,
                         "out": str(HERE), "reported_only": True})
        return jobs
    if exp == "all":
        exps = OPERATIONAL + ["E1-6n", "E1-7"]
    else:
        exps = [exp]
    for e in exps:
        if e == "E1-6n":
            for e2 in NOMAG_EXPS:
                for tid, kind, kw in trials(e2):
                    jobs.append({**base, "exp": e2, "sub": sub_experiment(e2, kind), "tid": tid, "kind": kind,
                                 "kw": kw, "magnets": False, "out": str(OUT_NOMAG), "reported_only": True})
            continue
        for tid, kind, kw in trials(e):
            jobs.append({**base, "exp": e, "sub": sub_experiment(e, kind), "tid": tid, "kind": kind, "kw": kw,
                         "magnets": True, "out": str(OUT), "reported_only": False})
    for j in jobs:
        s = j["kw"]["seed"]
        assert SCORED_SEED_RANGE[0] <= s <= SCORED_SEED_RANGE[1], (j["tid"], s)
    return jobs


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("experiment")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="UNSCORED smoke run: experiment must be 'smoke'")
    a = ap.parse_args(argv)
    if a.smoke != (a.experiment == "smoke"):
        raise SystemExit("--smoke runs only the 'smoke' trial list, and 'smoke' requires --smoke")
    if a.smoke:
        commit = scored._git("rev-parse", "HEAD") + "+uncommitted(smoke)"
    elif a.dry_run:
        commit = "dry-run"
    else:
        commit = require_m4_clean_commit()
        if E16C_THRESHOLD is None:
            raise SystemExit("refusing to run scored trials: the E1-6c threshold has not been set from R1 data by an "
                             "approved amendment (PHASE_1_M4_PREREGISTRATION.md, status and section 8 decision 1)")
    env = scored.environment()
    tilt = nominal_validated_tilt()
    jobs = build_jobs(a.experiment, commit, env, tilt, a.smoke)
    refused, ok_jobs = [], []
    for j in jobs:
        mp = magnet_params_for(dict(j["kw"].get("overrides", {}))) if j["magnets"] else None
        try:
            if mp is not None:
                magnet_availability(mp)
            ok_jobs.append(j)
        except Refused as e:
            refused.append((j, str(e)))
    for j, msg in refused:
        print(f"REFUSED {j['exp']}/{j['tid']}: {msg}", flush=True)
    if a.dry_run:
        by = {}
        for j in jobs:
            by.setdefault((j["exp"], j["magnets"]), []).append(j["kw"]["seed"])
        for (e, mag), seeds in by.items():
            print(f"{e} magnets={mag}: {len(seeds)} trials, seeds {min(seeds)}-{max(seeds)}")
        print(f"validated tilt {tilt} deg; {len(ok_jobs)} runnable, {len(refused)} refused; "
              f"E1-6c threshold {'NOT SET' if E16C_THRESHOLD is None else E16C_THRESHOLD}")
        return
    startup = None
    if any(j["magnets"] for j in ok_jobs):
        startup = startup_checks(MagnetParams())
        print(f"start-up checks: {startup}", flush=True)
        if not startup["pass"]:
            raise SystemExit("refusing to run: magnet start-up integrity check failed")
        use_magnets(None, M1Params().gap)          # workers install their own configuration per trial
    for j in ok_jobs:
        j["startup"] = startup
    ok_jobs.sort(key=lambda j: -len(j["kw"].get("moves", "").split()))
    print(f"commit {commit}: {len(ok_jobs)} trials ({len(refused)} refused)", flush=True)
    if a.jobs <= 1 or len(ok_jobs) <= 1:
        for j in ok_jobs:
            print(_execute(j), flush=True)
    else:
        with Pool(a.jobs) as pool:
            for line in pool.imap_unordered(_execute, ok_jobs):
                print(line, flush=True)
    if refused:
        sys.exit(2)


if __name__ == "__main__":
    main()
