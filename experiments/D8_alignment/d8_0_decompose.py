"""D8-0 — UNSCORED diagnostic: is M2's accumulated misalignment removable by LAYER-LEVEL rotations at all?

Question (decides D8-1a "magnets on M2" vs D8-1b "magnets on a contact cube"):
    In M2 every piece is welded to the core or to its face centre, with the weld anchored at the pose it had when
    the weld switched on. A force between pieces (e.g. a magnet pair) can therefore only move a whole unlocked layer
    about its axis. It cannot move one piece relative to the others in its layer. If the error that stalls M2 is
    mostly "the same for all pieces of a layer", layer-level forces can in principle remove it. If it differs from
    piece to piece, no layer-level force can.

Method (no change to the model, rule, turner, setup or harness):
    * Run the D7 diagnostic sequences on unchanged scored M2 (TrialM2, draw_setup, SwitchRule), without touch-ups.
    * After setup and after every commanded move (all layers locked), read each of the 26 pieces' residual
      rotation e_i relative to its nearest lattice rotation, as a small rotation vector in the core frame (deg).
    * Small-angle linear model: rotating face layer F by s_F about its normal n_F adds s_F * n_F to e_i of every
      piece in that layer. Solve min_s sum_i |e_i - sum_F s_F n_F [i in F]|^2 (6 unknowns, 78 equations).
      The residual r_i is the part of the error that NO combination of the six face-layer rotations can remove.
    * This is an UPPER BOUND on what layer-level forces could achieve: it assumes ideal, simultaneous correction of
      all six layers, which forces acting only while one layer is unlocked cannot exceed.
    Reported per snapshot: max |e_i|, max |r_i| (deg), fraction of squared error removable, and the blocking piece.
    Compare max |r_i| with the 0.5 deg per-piece relock tolerance (Amendment 2 fallback, in force).

Seeds: D7's diagnostic seeds (2231, 2300, 2401, 4302, 4401). Never the scored range 3000-3999.
Usage (WSL): ~/.venvs/rubiknetic/bin/python experiments/D8_alignment/d8_0_decompose.py <approved|loose> [case ...]
    approved = SwitchRule() as frozen for scoring; loose = diagnostic override (per-piece relock 3.0 deg, unlock
    3.0 deg) so sequences run longer before stalling and the error growth can be observed. "loose" is NOT the
    pre-registered rule.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

from rubiknetic.cube_logic import invert, parse, random_scramble
from rubiknetic.cube_logic.geometric import HOME_POSITIONS
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES
from rubiknetic.cube_logic.observe import nearest_lattice_rotation
from rubiknetic.cube_logic.transitions import infer_move
from rubiknetic.cube_physics import scored_m2 as S
from rubiknetic.cube_physics.rig import EditAuditError, NumericalFailure

OUT = Path(__file__).parent / "results"
SEXY6 = ("R U R' U' " * 6).strip()
HALVES = "F2 B2 L2 R2 U2 D2"


def scramble_seq(seed: int) -> str:
    sc = random_scramble(20, seed)
    return " ".join(str(m) for m in sc + invert(sc))


CASES = {
    "halves_s2231": (HALVES, 2231),
    "sexy6_s2300": (SEXY6, 2300),
    "sexy6_s4302": (SEXY6, 4302),
    "scr20inv_s2401": (scramble_seq(2401), 2401),
    "scr20inv_s4401": (scramble_seq(4401), 4401),
}
KIND = ["centre" if np.count_nonzero(h) == 1 else "edge" if np.count_nonzero(h) == 2 else "corner"
        for h in HOME_POSITIONS]


def piece_errors(ro, d) -> tuple[np.ndarray, np.ndarray]:
    """(26, 3) residual rotation vectors in deg (core frame, left residual) and (26, 6) layer membership."""
    pos, rot = ro.poses(d)
    e = np.zeros((26, 3))
    member = np.zeros((26, 6), bool)
    for i in range(26):
        res = rot[i] @ nearest_lattice_rotation(rot[i]).T
        e[i] = np.degrees(Rotation.from_matrix(res).as_rotvec())
        for k, f in enumerate(FACES):
            member[i, k] = pos[i] @ np.array(FACE_NORMAL[f], float) > 0.5
    return e, member


def decompose(e: np.ndarray, member: np.ndarray) -> dict:
    """Least-squares split of the error into the part six face-layer rotations can remove and the residual."""
    normals = np.array([FACE_NORMAL[f] for f in FACES], float)
    A = np.zeros((26 * 3, 6))
    for i in range(26):
        for k in range(6):
            if member[i, k]:
                A[3 * i:3 * i + 3, k] = normals[k]
    s, *_ = np.linalg.lstsq(A, e.reshape(-1), rcond=None)
    r = (e.reshape(-1) - A @ s).reshape(26, 3)
    mag_e, mag_r = np.linalg.norm(e, axis=1), np.linalg.norm(r, axis=1)
    tot = float((e ** 2).sum())
    worst = int(np.argmax(mag_e))
    return {
        "max_err_deg": float(mag_e.max()),
        "max_residual_deg": float(mag_r.max()),
        "rms_err_deg": float(np.sqrt((mag_e ** 2).mean())),
        "rms_residual_deg": float(np.sqrt((mag_r ** 2).mean())),
        "removable_fraction": float(1 - (r ** 2).sum() / tot) if tot > 0 else 1.0,
        "n_pieces_err_gt_0p5": int((mag_e > 0.5).sum()),
        "n_pieces_residual_gt_0p5": int((mag_r > 0.5).sum()),
        "worst_piece": {"index": worst, "kind": KIND[worst], "home": HOME_POSITIONS[worst],
                        "err_deg": mag_e[worst].round(4).item(), "residual_deg": mag_r[worst].round(4).item()},
        "layer_shift_deg": dict(zip(FACES, np.round(s, 4).tolist())),
    }


def run_case(name: str, seq: str, seed: int, rule) -> dict:
    setup = S.draw_setup(seed)
    tr = S.TrialM2(S.params_for_m2(setup), setup, rule)
    ro, d = tr.ro, tr.sim.d
    prev = tr.t0_obs.cube
    snaps = [{"after": "setup", **decompose(*piece_errors(ro, d))}]
    rows, stop = [], None
    for mv in parse(seq):
        n_sw = len(tr.sim.switch_log)
        try:
            tr.rig.turn(mv, tr.timing)
        except (NumericalFailure, EditAuditError) as ex:
            stop = f"{type(ex).__name__}: {ex}"
            break
        obs = ro.observe(d)
        try:
            om = infer_move(prev, obs.cube) if obs.valid else None
        except Exception as ex:  # noqa: BLE001
            om = f"inconsistent: {ex}"
        ok = str(om) == str(mv)
        sw = tr.sim.switch_log[n_sw:]
        rows.append({"move": str(mv), "observed": str(om), "ok": ok,
                     "refusals": [x.get("reason") for x in sw if x["kind"] == "refuse"],
                     "relock_member_err_deg": [x.get("max_misalignment_deg") for x in sw if x["kind"] == "relock"]})
        snaps.append({"after": f"{len(rows)}:{mv}", "ok": ok, **decompose(*piece_errors(ro, d))})
        if not ok:
            stop = f"move {len(rows)} ({mv}) observed {om}; refusals {rows[-1]['refusals'][:2]}; unlocked={tr.mgr.unlocked}"
            break
        prev = obs.cube
    return {"case": name, "seq": seq, "seed": seed, "rule": asdict(rule), "n_moves": len(parse(seq)),
            "moves_ok": sum(r["ok"] for r in rows), "stop": stop, "edit_audit_violations": tr.sim.violations,
            "moves": rows, "snapshots": snaps}


def main() -> None:
    mode = sys.argv[1]
    rule = S.SwitchRule()
    if mode == "loose":
        rule = replace(rule, tol_lock_cubie_deg=3.0, tol_unlock_deg=3.0)  # diagnostic override only
    elif mode != "approved":
        raise SystemExit("mode must be 'approved' or 'loose'")
    names = sys.argv[2:] or list(CASES)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "src"], capture_output=True, text=True).stdout)
    OUT.mkdir(parents=True, exist_ok=True)
    for name in names:
        seq, seed = CASES[name]
        t = time.perf_counter()
        res = run_case(name, seq, seed, rule)
        res.update({"mode": mode, "source_commit": commit, "src_dirty": dirty, "mujoco": mujoco.__version__,
                    "wall_s": round(time.perf_counter() - t, 1)})
        (OUT / f"{name}_{mode}.json").write_text(json.dumps(res, indent=1, default=str))
        last = res["snapshots"][-1]
        peak_r = max(s["max_residual_deg"] for s in res["snapshots"])
        print(f"{name} [{mode}] moves_ok={res['moves_ok']}/{res['n_moves']} final max_err={last['max_err_deg']:.3f} "
              f"max_resid={last['max_residual_deg']:.3f} removable={last['removable_fraction']:.2f} "
              f"peak_resid={peak_r:.3f} stop={res['stop']} wall={res['wall_s']}s", flush=True)


if __name__ == "__main__":
    main()
