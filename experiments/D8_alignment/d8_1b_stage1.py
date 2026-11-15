"""D8-1b stage 1 (UNSCORED feasibility): contact cube with and without piece-to-piece magnets.

Design: D8_1b_DESIGN_PROPOSAL.md §6 (approved 2026-11-14). Pre-declared feasibility signals (§6), NOT G1 thresholds:
all T3 sequences match the oracle; max per-piece misalignment bounded (growth < 0.005 deg/move over 40 moves); T1
snaps back from >= 3 deg in both directions; V4/V5 passed (d8_1b_checks.json); throughput >= 300 steps/s
single-process (T7; must be re-measured on an idle machine).

Configurations (stage 1a):
  B1 = M1 geometry at rigid radius (radial_preload = 0, as frozen for M2), no welds.
  B2 = M1 as scored (1 N radial preload slide) + cubie solimp dmax 0.999 only. DEVIATION: this was meant to be the
       D1 config E overload fix, which also raises d0 to 0.99 and applies the same values to the radial stop
       (radial_solimplimit). Kept and labelled as run; the exact configuration is B2E.
  B2E = M1 as scored + D1 config E exactly.
  magnets: none | nom (4x2 mm N35, 1.0 mm face gap). Magnet mass (0.4-0.6 g per piece) is NOT added in either arm,
  so the comparison isolates the magnet force (disclosed).
The base-model overrides are applied to every reused harness trial by wrapping scored.params_for (in-process only;
the harness logic, rig, monitor, setup draw and oracle checks are the scored M1 ones, unchanged).

Tests per configuration (diagnostic seeds 5100-5299; never 1000-1999 or 3000-3999):
  T1 snap        U turned by delta in {+-1, +-2, +-3, +-5, +-8} deg by the rig, released; U's error to the
                 lattice after release and after 1 s more (pads open). DEVIATION from §6 (disclosed 2026-11-14):
                 §6 says "misalign U through the logged setup, +-1...+-10 deg"; the harness turns U with the rig
                 (a contact-driven offset) and stops at +-8 deg.
  T2 forgiveness scored.run_forgiveness_trial, U misaligned +-2...+-12 deg, then R.
  T3 sequences   6-move, half turns, sexy6 x2, 20-move scramble + inverse x2: oracle match per move, turn error,
                 penetration, peak turner torque (T4), per-piece misalignment after every move (D8-0 metric),
                 magnet energy before/after each move (T6).
  T5 abuse       scored.run_opposed_trial (U,R at 1 and 2 N m) and scored.run_corner_twist_trial (ppp, nnn).
  T7             steps/s for each trial (wall clock; machine load recorded).
Revision 2 (2026-11-14, after an independent code review): magnet stats are reset per trial and record the largest
near-pair tilt; each +-delta pair of T1/T2 shares one seed (5200 + |delta| for T1, 5220 + |delta| for T2); the
near-field fit has no spurious slope at exact alignment (magnets.py). Revision-2 results go to results/stage1_r2/
(set D8_STAGE1_OUT); revision-1 results in results/stage1/ are kept unchanged.
Usage (WSL): ~/.venvs/rubiknetic/bin/python experiments/D8_alignment/d8_1b_stage1.py <B1|B2|B2E> <none|nom> [test ...]
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).parent))
from magnets import MagnetParams, MagnetSystem  # noqa: E402

from rubiknetic.cube_logic import SOLVED, InconsistentTransition, Move, infer_move, invert, parse, random_scramble  # noqa: E402,E501
from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES  # noqa: E402
from rubiknetic.cube_logic.observe import nearest_lattice_rotation  # noqa: E402
from rubiknetic.cube_physics import scored as SC  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml  # noqa: E402
from rubiknetic.cube_physics.rig import EditAuditError, NumericalFailure  # noqa: E402

OUT = Path(__file__).parent / "results" / os.environ.get("D8_STAGE1_OUT", "stage1_r2")
CACHE = Path(__file__).parent / "results" / "tables"
BASES = {"B1": {"radial_preload": 0.0},
         # B2 as first run (2026-11-14): only cubie dmax raised. This is NOT D1 config E (deviation, disclosed).
         "B2": {"cubie_solimp": (0.95, 0.999, 0.0005)},
         # B2E: D1 config E exactly (D1_corner_twist_diagnostic/run.py "E_solimp_dmax0.999"), the intended B2.
         "B2E": {"cubie_solimp": (0.99, 0.999, 0.0005), "radial_solimplimit": (0.99, 0.999, 0.0005)}}
MAGNETS = {"none": None, "nom": MagnetParams()}
SETUP_MISALIGN = 1.0     # M1's scored setup draw (+-1 deg per face)
_NONCENTRE = [i for i, h in enumerate(HOME_POSITIONS) if np.count_nonzero(h) >= 2]
MS: MagnetSystem | None = None


def scramble_inv(seed: int) -> str:
    sc = random_scramble(20, seed)
    return " ".join(str(m) for m in sc + invert(sc))


def tests() -> dict:
    t = {}
    # Each +/- pair shares one setup seed (review finding, 2026-11-14: different seeds confounded the two directions
    # with different setup offsets, grips and speeds). Runs before this change used seed 5100 + i / 5120 + i.
    for deg in (1, 2, 3, 5, 8):
        for sgn in (1, -1):
            t[f"snap_{sgn * deg:+d}"] = ("snap", {"delta_deg": float(sgn * deg), "seed": 5200 + deg})
    for deg in (2, 4, 6, 8, 10, 12):
        for sgn in (1, -1):
            t[f"forgive_{sgn * deg:+d}"] = ("forgive", {"misalign_deg": float(sgn * deg), "seed": 5220 + deg})
    seqs = [("6move", "U U' R R' F F'", 5140), ("halves", "F2 B2 L2 R2 U2 D2", 5141),
            ("sexy6_a", ("R U R' U' " * 6).strip(), 5142), ("sexy6_b", ("R U R' U' " * 6).strip(), 5143),
            ("scr20inv_a", scramble_inv(5144), 5144), ("scr20inv_b", scramble_inv(5145), 5145)]
    for name, seq, s in seqs:
        t[f"seq_{name}"] = ("seq", {"moves": seq, "seed": s})
    for i, tau in enumerate((1.0, 2.0)):
        t[f"opposed_UR_{tau:g}Nm"] = ("opposed", {"faces": ("U", "R"), "torque_limit": tau, "seed": 5160 + i})
    for i, c in enumerate(((1, 1, 1), (-1, -1, -1))):
        t[f"twist_{''.join('p' if v > 0 else 'n' for v in c)}"] = ("twist", {"corner": c, "seed": 5170 + i})
    return t


# ------------------------------------------------------------------ helpers
def piece_errors(ro, d) -> tuple[np.ndarray, np.ndarray]:
    pos, rot = ro.poses(d)
    e = np.zeros((26, 3))
    member = np.zeros((26, 6), bool)
    for i in range(26):
        e[i] = np.degrees(Rotation.from_matrix(rot[i] @ nearest_lattice_rotation(rot[i]).T).as_rotvec())
        for k, f in enumerate(FACES):
            member[i, k] = pos[i] @ np.array(FACE_NORMAL[f], float) > 0.5
    return e, member


def misalignment(ro, d) -> dict:
    """D8-0 metric: max per-piece error, and the residual no combination of face-layer rotations can remove."""
    e, member = piece_errors(ro, d)
    normals = np.array([FACE_NORMAL[f] for f in FACES], float)
    A = np.zeros((78, 6))
    for i in range(26):
        for k in range(6):
            if member[i, k]:
                A[3 * i:3 * i + 3, k] = normals[k]
    s, *_ = np.linalg.lstsq(A, e.reshape(-1), rcond=None)
    r = (e.reshape(-1) - A @ s).reshape(26, 3)
    return {"max_err_deg": float(np.linalg.norm(e, axis=1)[_NONCENTRE].max()),
            "max_residual_deg": float(np.linalg.norm(r, axis=1)[_NONCENTRE].max())}


def layer_error(ro, d, face: str) -> float:
    """Signed error (deg) of a face layer to the lattice about its axis: median over the layer's non-centre pieces."""
    pos, rot = ro.poses(d)
    n = np.array(FACE_NORMAL[face], float)
    errs = [float(np.degrees(Rotation.from_matrix(rot[i] @ nearest_lattice_rotation(rot[i]).T).as_rotvec() @ n))
            for i in _NONCENTRE if pos[i] @ n > 0.5]
    return float(np.median(errs))


def magnet_energy(d) -> float | None:
    return MS.energy(d) if MS is not None else None


# ------------------------------------------------------------------ tests
def run_snap(delta_deg: float, seed: int) -> dict:
    setup = SC.draw_setup(seed, SETUP_MISALIGN)
    tr = SC.Trial(SC.params_for(setup), setup)
    ro, d = tr.ro, tr.sim.d
    rec = tr.base_record()
    rec.update({"seed": seed, "delta_deg": delta_deg, "U_err_t0_deg": layer_error(ro, d, "U")})
    try:
        tr.rig.rotate({"U": np.radians(delta_deg)}, grip=True, timing=tr.timing)
        rec["U_err_after_release_deg"] = layer_error(ro, d, "U")
        tr.sim.step(int(round(1.0 / tr.model.opt.timestep)))
        rec["U_err_after_1s_deg"] = layer_error(ro, d, "U")
        rec["misalignment_end"] = misalignment(ro, d)
        obs = ro.observe(d)
        rec["final_observed_valid"] = obs.valid
        rec["final_solved"] = bool(obs.valid and obs.state == SOLVED)
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    tr.finish(rec)
    return rec


def run_seq(moves: str, seed: int) -> dict:
    mv_list = parse(moves)
    setup = SC.draw_setup(seed, SETUP_MISALIGN)
    tr = SC.Trial(SC.params_for(setup), setup)
    ro, d, mon = tr.ro, tr.sim.d, tr.mon
    rec = tr.base_record()
    rec.update({"sequence": moves, "seed": seed, "per_move": [], "misalignment_t0": misalignment(ro, d)})
    expect, prev = SOLVED, tr.t0_obs
    try:
        for mv in mv_list:
            _, r0 = ro.poses(d)
            members = ro.layer_members(d, mv.face)
            u0 = magnet_energy(d)
            mon.new_window()
            log = tr.rig.turn(mv, tr.timing)
            _, r1 = ro.poses(d)
            obs = ro.observe(d)
            nominal = -90.0 * {1: 1, 2: 2, 3: -1}[mv.quarter_turns]
            err = (ro.rotation_about_deg(r0, r1, members, mv.face) - nominal + 180.0) % 360.0 - 180.0
            observed = None
            if prev.valid and obs.valid:
                try:
                    observed = infer_move(prev.cube, obs.cube)
                except InconsistentTransition:
                    observed = "inconsistent"
            if isinstance(observed, Move):
                expect = expect.apply(observed)
            ok = bool(obs.valid and observed == mv and obs.state == expect)
            u1 = magnet_energy(d)
            rec["per_move"].append({
                "move": str(mv), "observed": str(observed) if observed is not None else None, "ok": ok,
                "turn_error_deg": float(np.mean(err)), "penetration_mm": max(0.0, -mon.window_min_dist) * 1000,
                "max_turner_torque_Nm": float(np.max(np.abs(log.turner_torque))),
                "magnet_energy_before_J": u0, "magnet_energy_after_J": u1,
                "misalignment": misalignment(ro, d)})
            prev = obs
            if not ok:
                break
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    rec["n_moves"] = len(mv_list)
    rec["moves_ok"] = sum(r["ok"] for r in rec["per_move"])
    tr.finish(rec)
    return rec


def run(kind: str, kw: dict) -> dict:
    if kind == "snap":
        return run_snap(**kw)
    if kind == "seq":
        return run_seq(**kw)
    if kind == "forgive":
        return SC.run_forgiveness_trial(kw["misalign_deg"], kw["seed"])
    if kind == "opposed":
        return SC.run_opposed_trial(tuple(kw["faces"]), kw["torque_limit"], kw["seed"])
    if kind == "twist":
        return SC.run_corner_twist_trial(tuple(kw["corner"]), kw["seed"])
    raise ValueError(kind)


def main() -> None:
    global MS
    base, mag = sys.argv[1], sys.argv[2]
    over = BASES[base]
    orig = SC.params_for
    SC.params_for = lambda setup, **kw: orig(setup, **{**over, **kw})  # base model for every reused harness trial
    mp = MAGNETS[mag]
    if mp is not None:
        p = M1Params(**over)
        m = mujoco.MjModel.from_xml_string(build_m1_xml(p))
        MS = MagnetSystem(m, p.pitch, p.gap, mp, CACHE)
        # The passive callback is global and MuJoCo's compiler runs an internal forward pass that would invoke it on
        # a half-built model the Python bindings cannot wrap ("engine error: Python exception raised"). Pause it
        # while any model compiles; this changes no physics (no simulation step happens during compilation).
        compile_xml = mujoco.MjModel.from_xml_string

        def compile_paused(xml, *a, **k):
            MagnetSystem.uninstall()
            try:
                model = compile_xml(xml, *a, **k)
            finally:
                MS.install()
            body = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, g["body"]) for g in MS.mags]
            assert np.array_equal(body, MS.body), "trial model body ids differ from the magnet layout"
            return model

        mujoco.MjModel.from_xml_string = compile_paused
        MS.install()
    else:
        MagnetSystem.uninstall()
    cfg = f"{base}_{mag}"
    out = OUT / cfg
    out.mkdir(parents=True, exist_ok=True)
    todo = tests()
    names = sys.argv[3:] or list(todo)
    for name in names:
        if (out / f"{name}.json").exists():
            continue
        kind, kw = todo[name]
        load0 = os.getloadavg()[0]
        if MS is not None:
            MS.reset_stats()          # per-trial magnet stats (they were cumulative per process before 2026-11-14)
        t = time.perf_counter()
        rec = run(kind, kw)
        wall = time.perf_counter() - t
        steps = rec.get("sim_time_s", 0.0) / 0.0005
        rec.update({"config": cfg, "base_overrides": {k: list(v) if isinstance(v, tuple) else v for k, v in over.items()},
                    "magnets": None if mp is None else MS.describe(), "magnet_stats": None if MS is None else dict(MS.stats),
                    "test": name, "kind": kind, "kwargs": kw, "wall_s": wall, "steps_per_s": steps / wall if wall else None,
                    "loadavg_start": load0, "mujoco": mujoco.__version__})
        (out / f"{name}.json").write_text(json.dumps(rec, indent=1, default=str))
        summary = {k: rec.get(k) for k in ("pass", "moves_ok", "n_moves", "U_err_after_release_deg",
                                            "U_err_after_1s_deg", "outcome", "max_twist_deg", "aborted") if k in rec}
        print(f"[{cfg}] {name}: {summary} {rec['steps_per_s']:.0f} steps/s", flush=True)


if __name__ == "__main__":
    main()
