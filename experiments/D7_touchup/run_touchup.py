"""D7 — UNSCORED feasibility of contact-driven ALIGNMENT TOUCH-UPS for M2 (option B, user: "B").

Problem (smoke tests after Amendment 4, FACT): M2 has no self-alignment. Each relock freezes the current small
misalignment, and turner residuals accumulate across axes until a piece exceeds the relock or unlock tolerance.
Long sequences then stall.
Idea: before every commanded move, the rig squares any face layer whose angular error exceeds TOUCHUP_DEG. It
grips, rotates by minus the error and releases, through ordinary pad contact and M2's normal switching rule; no
state edits. This is the Phase 2 robot's job anyway (requirement R2-05).
Checks: touch-ups never change the logical state, every commanded move matches the oracle, and the switch log
stays clean.
Uses the committed scored-M2 trial setup (TrialM2, draw_setup), unchanged. Seeds here are diagnostic only.
Usage: uv run python experiments/D7_touchup/run_touchup.py <case-set a|b> [CUBIE_TOL env var for diagnostics]
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from rubiknetic.cube_logic import invert, parse, random_scramble
from rubiknetic.cube_logic.geometric import HOME_POSITIONS
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES
from rubiknetic.cube_logic.observe import nearest_lattice_rotation
from rubiknetic.cube_logic.transitions import infer_move
from rubiknetic.cube_physics import scored_m2 as S
from rubiknetic.cube_physics.rig import EditAuditError, NumericalFailure

TOUCHUP_DEG = 0.25
MAX_PASSES = 2
OUT = Path(__file__).parent / "results"
SEXY6 = ("R U R' U' " * 6).strip()
HALVES = "F2 B2 L2 R2 U2 D2"


def layer_errors(ro, d) -> dict[str, float]:
    """Signed angular error (deg) of each face layer about its axis: the median over the layer's non-centre
    pieces of (rotation relative to the nearest lattice rotation) projected on the face axis (core frame)."""
    pos, rot = ro.poses(d)
    out = {}
    for f in FACES:
        n = np.array(FACE_NORMAL[f], float)
        errs = []
        for i, h in enumerate(HOME_POSITIONS):
            if sum(map(abs, h)) < 2 or pos[i] @ n <= 0.5:
                continue
            res = rot[i] @ nearest_lattice_rotation(rot[i]).T
            errs.append(float(np.degrees(Rotation.from_matrix(res).as_rotvec() @ n)))
        out[f] = float(np.median(errs)) if errs else 0.0
    return out


def scramble_seq(seed):
    sc = random_scramble(20, seed)
    return " ".join(str(m) for m in sc + invert(sc))


def run_case(seq: str, seed: int, rule) -> dict:
    setup = S.draw_setup(seed)
    tr = S.TrialM2(S.params_for_m2(setup), setup, rule)
    ro, d = tr.ro, tr.sim.d
    prev = tr.t0_obs.cube
    rows, touchups, ok_all = [], [], True
    for mv in parse(seq):
        # ---- touch-up phase (contact-driven squaring), then a state check
        for _ in range(MAX_PASSES):
            errs = layer_errors(ro, d)
            worst = max(errs, key=lambda f: abs(errs[f]))
            if abs(errs[worst]) <= TOUCHUP_DEG:
                break
            n_sw = len(tr.sim.switch_log)
            try:
                tr.rig.rotate({worst: -np.radians(errs[worst])}, grip=True, timing=tr.timing, record=False)
            except (NumericalFailure, EditAuditError) as e:
                return {"seq": seq, "seed": seed, "aborted": str(e), "moves": rows, "touchups": touchups}
            after = layer_errors(ro, d)[worst]
            refused = [e.get("reason") for e in tr.sim.switch_log[n_sw:] if e["kind"] == "refuse"]
            touchups.append({"before_move": str(mv), "face": worst, "err_before": errs[worst], "err_after": after,
                             "refusals": refused})
        obs = ro.observe(d)
        try:
            tm = infer_move(prev, obs.cube) if obs.valid else "invalid"
        except Exception as e:  # noqa: BLE001
            tm = f"inconsistent: {e}"
        if tm is not None:  # a touch-up must never change the logical state
            rows.append({"move": "TOUCHUP-STATE-CHANGE", "observed": str(tm)})
            ok_all = False
            break
        # ---- the commanded move
        n_sw = len(tr.sim.switch_log)
        try:
            log = tr.rig.turn(mv, tr.timing)
        except (NumericalFailure, EditAuditError) as e:
            rows.append({"move": str(mv), "aborted": str(e)})
            ok_all = False
            break
        obs = ro.observe(d)
        try:
            om = infer_move(prev, obs.cube) if obs.valid else None
        except Exception as e:  # noqa: BLE001
            om = f"inconsistent: {e}"
        ok = str(om) == str(mv)
        rows.append({"move": str(mv), "observed": str(om), "ok": ok,
                     "peak_torque": float(np.max(np.abs(log.turner_torque))),
                     "refusals": [e.get("reason") for e in tr.sim.switch_log[n_sw:] if e["kind"] == "refuse"]})
        if not ok:
            ok_all = False
            break
        prev = obs.cube
    sw = [e for e in tr.sim.switch_log if e["kind"] in ("unlock", "relock")]
    return {"seq": seq, "seed": seed, "all_ok": ok_all, "moves_ok": sum(r.get("ok", False) for r in rows),
            "n_moves": len(parse(seq)), "n_touchups": len(touchups),
            "max_touchup_err_after": max((abs(t["err_after"]) for t in touchups), default=0.0),
            "max_abs_dKE_J": max((abs(e.get("dke", 0.0)) for e in sw), default=0.0),
            "max_misalignment_end": max((e.get("max_misalignment_deg", 0.0) for e in sw), default=0.0),
            "moves": rows, "touchups": touchups}


if __name__ == "__main__":
    which = sys.argv[1]
    rule = S.SwitchRule()
    if os.environ.get("CUBIE_TOL"):
        rule = replace(rule, tol_lock_cubie_deg=float(os.environ["CUBIE_TOL"]))  # diagnostic override only
    if os.environ.get("UNLOCK_TOL"):
        rule = replace(rule, tol_unlock_deg=float(os.environ["UNLOCK_TOL"]))     # diagnostic override only
    if os.environ.get("HINGE_TOL"):
        rule = replace(rule, tol_lock_deg=float(os.environ["HINGE_TOL"]))        # diagnostic override only
    if os.environ.get("NO_TOUCHUP"):
        globals()["MAX_PASSES"] = 0                                               # baseline: no touch-ups
    cases = {"a": [("scr20inv_s2401", scramble_seq(2401), 2401), ("halves_s2231", HALVES, 2231)],
             "b": [("sexy6_s2300", SEXY6, 2300), ("scr20inv_s4401", scramble_seq(4401), 4401),
                   ("sexy6_s4302", SEXY6, 4302)]}[which]
    OUT.mkdir(parents=True, exist_ok=True)
    for name, seq, seed in cases:
        t = time.perf_counter()
        res = run_case(seq, seed, rule)
        tag = f"tol{rule.tol_lock_cubie_deg}_unlock{rule.tol_unlock_deg}_hinge{rule.tol_lock_deg}_{'notouch' if MAX_PASSES == 0 else 'touch'}"
        (OUT / f"{name}_{tag}.json").write_text(json.dumps(res, indent=1, default=str))
        bad = [r for r in res.get("moves", []) if not r.get("ok", False)]
        print(f"{name} (cubie relock tol {rule.tol_lock_cubie_deg}): all_ok={res.get('all_ok')} moves_ok={res.get('moves_ok')}/"
              f"{res.get('n_moves')} touchups={res.get('n_touchups')} max_err_after={res.get('max_touchup_err_after', 0):.2f} "
              f"max_misalign={res.get('max_misalignment_end', 0):.2f} dKE={res.get('max_abs_dKE_J', 0):.1e} "
              f"first_bad={bad[:1]} aborted={res.get('aborted')} wall={time.perf_counter() - t:.0f}s", flush=True)
