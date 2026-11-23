"""ER9 Part G (PROTOCOL.md G.4, G.12): per-class validity diagnostic and path deviation d. Diagnostic only.

It reads the magnet centres p and unit moment directions n that MagnetSystem.world computed for the force call, AFTER
that unchanged force call, and only writes its own counters. It changes no force, torque, energy, stat of the
MagnetSystem, neighbour list or MuJoCo field (GS4; tests: test_er9g_static.py).

Pair classes (G.4; fixed by static labels: magnet type, and whether a magnet sits on `core` or on a piece; pairs on
the same body are skipped, as MagnetSystem skips them):
  CE    4x2-4x2 on different pieces            PCon / PCoff  4x3 piece magnet with a 4x3 core magnet, d <= / > D_val
  PP3   4x3-4x3 on two different pieces         X             4x2 with 4x3 (cross-type; dipole term only)
Definitions copied from rubiknetic/cube_physics/magnets.py so the numbers are comparable with MagnetSystem.stats:
  * evaluation: a pair on different bodies (MagnetSystem.__init__ l.527-529: triu pairs, same-body skipped). Every
    pair, not only the current Verlet list: pairs off the list are beyond far_r2 + skin, so near counts are the same.
  * near: centre distance r = |p_j - p_i| < r2 (pair_forces l.400-401, l.419; composite cross pairs l.676).
  * perpendicular: near and |n_i . n_j| <= cos 45 deg (pair_forces l.418-422: par = near & |cosn| > cos 45).
  * tilt: arccos(min(1, |n_i . n_j|)) in degrees over near non-perpendicular pairs (pair_forces l.439).
  * clamped z: near, non-perpendicular, |z| < z_min with z = (p_j - p_i) . n_i (pair i < j, the first magnet's axis)
    and z_min = L + 0.1 mm of the class's magnet type (pair_forces l.399, l.428-437). For X, which has two types and
    no near-field branch, z_min uses the larger length (4x3: 3.1 mm) - a reading of "the class's magnet type".
  * d(n) = min over k of |arccos(|n . e_k|) - beta0| (degrees) for the piece magnet of a PC pair; beta0 = 45 deg for an
    edge's magnet, arccos(1/sqrt 3) for a corner's (G.4 "Path deviation d").
Cost per callback (timing(), 2026-11-22, WSL, one thread, shared machine; operational, not a result): about 0.20 ms
for L0's 1,092 pairs, 0.26 ms for C52's 590 (PC path deviation per pair), 0.55 ms at 3,554 pairs (PG20's size). One
vectorised pass over all different-body pairs per call; no Python loop over pairs.
"""
from __future__ import annotations

import math

import numpy as np

from rubiknetic.cube_physics.magnets import MagnetSystem

CLASSES = ("CE", "PCon", "PCoff", "PP3", "X")
_CODE = {"CE": 0, "PC": 1, "PP3": 3, "X": 4}            # PC splits into PCon (1) / PCoff (2) per evaluation
COS45 = np.cos(np.radians(45))                           # the same expression as pair_forces l.420
BETA0_DEG = {"edge": 45.0, "corner": math.degrees(math.acos(1 / math.sqrt(3)))}
STRICT_D_VAL, PROXY_D_VAL = 0.5, math.inf                # U2 alternatives; the default is P4.d's result


def path_deviation_deg(n: np.ndarray, kind) -> np.ndarray:
    """d(n) of G.4, vectorised: n (k, 3) unit directions; kind 'edge' / 'corner' or an array of beta0 in degrees."""
    n = np.atleast_2d(np.asarray(n, float))
    beta = np.full(len(n), BETA0_DEG[kind]) if isinstance(kind, str) else np.asarray(kind, float)
    ang = np.degrees(np.arccos(np.minimum(1.0, np.abs(n))))          # angle to each axis e_x, e_y, e_z
    return np.min(np.abs(ang - beta[:, None]), axis=1)


def magnet_class_info(mags: list[dict], system_mp) -> dict:
    """Static labels per magnet: is 4x3, on core, length (m), beta0 (piece 4x3 only)."""
    t43, core, length, beta = [], [], [], []
    for g in mags:
        mp = g.get("mp", system_mp)
        dims = (round(mp.diameter, 9), round(mp.length, 9))
        if dims not in ((0.004, 0.002), (0.004, 0.003)):
            raise ValueError(f"Part G classes know 4x2 and 4x3 magnets only, got {dims}")
        is43 = dims[1] == 0.003
        on_core = g["body"] == "core"
        if on_core and not is43:
            raise ValueError("a 4x2 magnet on the core is not a Part G configuration")
        t43.append(is43); core.append(on_core); length.append(mp.length)
        kind = g["kind"].replace("core_", "")
        beta.append(BETA0_DEG[kind] if (is43 and not on_core) else np.nan)
    return {"t43": np.array(t43), "core": np.array(core), "length": np.array(length), "beta": np.array(beta)}


class ClassStats:
    """Per-trial accumulator of the G.4 per-class stats. update(p, n) once per magnet callback (after the force call);
    as_dict(ms_stats) at the end of the trial."""

    def __init__(self, mags: list[dict], system_mp, d_val_deg: float):
        if not (d_val_deg >= 0):
            raise ValueError(f"D_val must be >= 0 (or inf for 'proxy'), got {d_val_deg}")
        self.d_val = float(d_val_deg)
        info = magnet_class_info(mags, system_mp)
        n = len(mags)
        ii, jj = np.triu_indices(n, 1)
        body = np.array([g["body"] for g in mags])
        keep = body[ii] != body[jj]                       # = MagnetSystem.ii_all / jj_all (same order)
        self.ii, self.jj = ii[keep], jj[keep]
        a43, b43 = info["t43"][self.ii], info["t43"][self.jj]
        ac, bc = info["core"][self.ii], info["core"][self.jj]
        code = np.full(len(self.ii), -1)
        code[~a43 & ~b43] = _CODE["CE"]
        code[a43 & b43 & (ac != bc)] = _CODE["PC"]
        code[a43 & b43 & ~ac & ~bc] = _CODE["PP3"]
        code[a43 != b43] = _CODE["X"]
        assert (code >= 0).all(), "unclassified pair"
        self.code = code
        self.zmin = np.where(code == _CODE["X"], np.maximum(info["length"][self.ii], info["length"][self.jj]),
                             info["length"][self.ii]) + 0.0001
        self.piece = np.where(ac, self.jj, self.ii)       # the piece magnet of a PC pair (meaningful where code == 1)
        self.beta = info["beta"][self.piece]
        self.x_pp = (code == _CODE["X"]) & ~ac & ~bc      # cross-type pairs with no magnet on the core
        self.masks = {k: code == c for k, c in (("CE", 0), ("PC", 1), ("PP3", 3), ("X", 4))}
        self.r2 = float(system_mp.r2)
        self.reset()

    def reset(self) -> None:
        self.calls = 0
        self.acc = {k: {"near_evals": 0, "near_perpendicular": 0, "max_near_tilt_deg": 0.0, "clamped_z": 0,
                        "min_centre_distance_mm": None} for k in CLASSES}
        self.pc_max_d = 0.0
        self.pc_max_d_clamped = 0.0
        self.x_pp_min_mm = None

    @staticmethod
    def _min(old, new):
        return new if old is None else min(old, new)

    def update(self, p: np.ndarray, n: np.ndarray) -> None:
        """One evaluation of every pair at magnet centres p (m) and unit directions n. Reads p and n only."""
        self.calls += 1
        rv = p[self.jj] - p[self.ii]
        r = np.linalg.norm(rv, axis=1)
        code = self.code.copy()
        d = np.zeros(len(code))
        pc = self.masks["PC"]
        if pc.any():                                      # d per PC evaluation, from its piece magnet's direction
            d[pc] = path_deviation_deg(n[self.piece[pc]], self.beta[pc])
            code[pc & (d > self.d_val)] = 2               # PCoff
        for name, c in (("CE", 0), ("PCon", 1), ("PCoff", 2), ("PP3", 3), ("X", 4)):
            sel = code == c                               # smallest centre distance over every evaluation
            if sel.any():
                a = self.acc[name]
                a["min_centre_distance_mm"] = self._min(a["min_centre_distance_mm"], float(r[sel].min()) * 1e3)
        if self.x_pp.any():
            self.x_pp_min_mm = self._min(self.x_pp_min_mm, float(r[self.x_pp].min()) * 1e3)
        k = np.nonzero(r < self.r2)[0]
        if len(k) == 0:
            return
        i, j, ck, dk = self.ii[k], self.jj[k], code[k], d[k]
        cosn = np.einsum("ij,ij->i", n[i], n[j])
        acos = np.abs(cosn)
        par = acos > COS45
        z = np.einsum("ij,ij->i", rv[k], n[i])
        clamped = par & (np.abs(z) < self.zmin[k])
        tilt = np.degrees(np.arccos(np.minimum(1.0, acos)))
        pck = (ck == 1) | (ck == 2)
        if pck.any():
            self.pc_max_d = max(self.pc_max_d, float(dk[pck].max()))
            if (pck & clamped).any():
                self.pc_max_d_clamped = max(self.pc_max_d_clamped, float(dk[pck & clamped].max()))
        for name, c in (("CE", 0), ("PCon", 1), ("PCoff", 2), ("PP3", 3), ("X", 4)):
            sel = ck == c
            if not sel.any():
                continue
            a = self.acc[name]
            a["near_evals"] += int(sel.sum())
            a["near_perpendicular"] += int(np.sum(sel & ~par))
            a["clamped_z"] += int(np.sum(sel & clamped))
            sp = sel & par
            if sp.any():
                a["max_near_tilt_deg"] = max(a["max_near_tilt_deg"], float(tilt[sp].max()))

    def as_dict(self, ms_stats: dict | None = None) -> dict:
        """The per-trial record of G.4: K_near_evals, K_near_perpendicular, K_max_near_tilt_deg, K_clamped_z,
        K_min_centre_distance_mm for K in CE, PCon, PCoff, PP3, X; PC_max_path_dev_deg, PC_max_path_dev_deg_clamped,
        D_val_deg, cross_near (the composite's own near_cross_type if given, else X_near_evals), and the legacy
        aggregate MagnetSystem.stats keys. K_min_centre_distance_mm is over every evaluation of class K (near or
        not; None if the class has no pair); the PCon / PCoff split uses each evaluation's d, near or not.
        Extra (not in G.4's list): X_piece_piece_min_centre_distance_mm (cross pairs with no magnet on the core),
        used by P1's stop rule."""
        out = {"calls": self.calls}
        for k in CLASSES:
            for f, v in self.acc[k].items():
                out[f"{k}_{f}"] = v
        out["X_piece_piece_min_centre_distance_mm"] = self.x_pp_min_mm
        out["PC_max_path_dev_deg"] = self.pc_max_d
        out["PC_max_path_dev_deg_clamped"] = self.pc_max_d_clamped
        out["D_val_deg"] = self.d_val
        out["cross_near"] = self.acc["X"]["near_evals"]
        if ms_stats is not None:
            if "near_cross_type" in ms_stats:
                out["cross_near"] = int(ms_stats["near_cross_type"])
            out["legacy"] = {k: ms_stats.get(k) for k in ("max_near_tilt_deg", "near_perpendicular", "clamped_z",
                                                          "calls")}
        return out


def out_of_regime(stats: dict, D_val: float) -> bool:
    """G.4's per-trial rule, exactly. `stats` is ClassStats.as_dict(); its PCon / PCoff split was made with its own
    D_val_deg, so a different D_val is refused (the split cannot be redone from the aggregates)."""
    if float(stats["D_val_deg"]) != float(D_val):
        raise ValueError(f"stats were split at D_val = {stats['D_val_deg']} deg, not {D_val} deg")
    s = stats
    return bool(s["CE_max_near_tilt_deg"] > 5 or s["CE_clamped_z"] > 0 or s["CE_near_perpendicular"] > 0
                or s["PCon_max_near_tilt_deg"] > 20 or s["PCon_near_perpendicular"] > 0
                or s["PCoff_max_near_tilt_deg"] > 7.5 or s["PCoff_clamped_z"] > 0 or s["PCoff_near_perpendicular"] > 0
                or s["PP3_max_near_tilt_deg"] > 7.5 or s["PP3_clamped_z"] > 0 or s["PP3_near_perpendicular"] > 0
                or s["cross_near"] > 0)


def with_class_stats(base_cls=MagnetSystem):
    """A subclass of base_cls (MagnetSystem or M4.RecordingMagnetSystem) whose forces() calls base_cls.forces
    unchanged and then, only for callback evaluations (stats=True, i.e. from apply()), feeds (p, n) to self.g_stats
    if one is attached. Nothing returned by forces() and nothing in self.stats is touched."""

    class ClassStatsSystem(base_cls):
        g_stats: ClassStats | None = None

        def forces(self, p, n, stats: bool = False):
            out = super().forces(p, n, stats)
            if stats and self.g_stats is not None:
                self.g_stats.update(p, n)
            return out

        def reset_stats(self) -> None:
            # The class accumulator always covers the same window as MagnetSystem.stats (ER7's run_one resets the
            # system's stats before the 60 s rest, for example).
            super().reset_stats()
            if self.g_stats is not None:
                self.g_stats.reset()

    ClassStatsSystem.__name__ = f"ClassStats{base_cls.__name__}"
    return ClassStatsSystem


def attach(ms, d_val_deg: float) -> ClassStats:
    """A fresh per-trial accumulator for ms (a with_class_stats system), attached to it. Call at the start of every
    trial, next to ms.reset_stats()."""
    acc = ClassStats(ms.mags, ms.mp, d_val_deg)
    ms.g_stats = acc
    return acc


def timing(mags: list[dict], system_mp, repeats: int = 2000) -> float:
    """Seconds per update() on poses near home (for the cost statement; not a physics quantity)."""
    import time
    acc = ClassStats(mags, system_mp, PROXY_D_VAL)
    p = np.array([g["pos"] for g in mags], float)
    n = np.array([g["dir"] for g in mags], float)
    t0 = time.perf_counter()
    for _ in range(repeats):
        acc.update(p, n)
    return (time.perf_counter() - t0) / repeats


def gs6_path_deviation(arm: str = "PG20", grade: str = "N52", step_deg: float = 1.0) -> dict:
    """GS6, d part (G.5): d(n) of every 4x3 piece magnet stays below 1e-9 deg in rigid turns of all six faces,
    -90..+90 deg at step_deg (kinematic poses of the B1 model, er9g_scan.Kin)."""
    import importlib.util
    import sys
    from pathlib import Path
    here = Path(__file__).resolve().parent

    def load(name):
        if name not in sys.modules:
            spec = importlib.util.spec_from_file_location(name, here / f"{name}.py")
            mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
        return sys.modules[name]

    LY, SC = load("er9g_layouts"), load("er9g_scan")
    from rubiknetic.cube_logic.notation import FACES
    kin = SC.Kin()
    mags = LY.arm_mags(arm, grade, kin.p.pitch, kin.p.gap)
    idx = [k for k, g in enumerate(mags) if LY.is_43(g) and g["body"] != "core"]
    beta = np.array([BETA0_DEG[mags[k]["kind"]] for k in idx])
    worst, poses = 0.0, 0
    for f in FACES:
        for a in SC.degs(-90.0, 90.0, step_deg):
            kin.pose(SC.face_turn_moves(f, a))
            _, n, _ = kin.world(mags)
            if idx:
                worst = max(worst, float(path_deviation_deg(n[idx], beta).max()))
            poses += 1
    return {"arm": arm, "n_piece_magnets": len(idx), "poses": poses, "step_deg": step_deg, "max_d_deg": worst,
            "pass": bool(len(idx) > 0 and worst < 1e-9)}
