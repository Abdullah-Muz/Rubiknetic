"""D1 — UNSCORED diagnostic for the E1-6c corner-twist failure of M1.

Question: why does a corner twist in place at ~0.1 N.m and then diverge or
penetrate (E1-6c)? Hypotheses under test:
  H1  contact/limit constraints are too soft at the 3.4 g cubie scale
      (shorter solref time constant -> stiffer; needs a smaller timestep);
  H2  timestep too coarse (timestep only);
  H3  solimp impedance too low (dmax -> 0.999);
  H4  effective mass too low (MuJoCo constraint stiffness is specified as a
      reference acceleration, so force capacity scales with effective mass;
      tested via joint armature, which also distorts turning inertia).
Each config gets a static torque staircase on two corners, plus a turning
check (U U' R R' F F') so a "fix" that breaks turning is visible.

Not part of G1 scoring: no clean-commit requirement, no setup randomisation
for the twist (setup=None), turning check uses seed 5000 (outside 1000-1999).
Usage (WSL2, repo root):  uv run python experiments/D1_corner_twist_diagnostic/run.py [--jobs 8]
"""

from __future__ import annotations

import argparse
import json
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from rubiknetic.cube_logic import parse
from rubiknetic.cube_logic.geometric import HOME_POSITIONS
from rubiknetic.cube_physics import scored
from rubiknetic.cube_physics.rig import EditAuditError, NumericalFailure

OUT = Path(__file__).parent / "results"
LEVELS_NM = [0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
RAMP_S, HOLD_S = 0.05, 0.25
CORNERS = {"ppp": (1, 1, 1), "nnn": (-1, -1, -1)}

CONFIGS = {
    "A_nominal": {},
    "B_dt0.25ms": {"timestep": 0.00025},
    "C_solref0.5ms_dt0.25ms": {"timestep": 0.00025, "cubie_solref": (0.0005, 1.0), "radial_solreflimit": (0.0005, 1.0)},
    "D_solref0.25ms_dt0.125ms": {"timestep": 0.000125, "cubie_solref": (0.00025, 1.0),
                                 "radial_solreflimit": (0.00025, 1.0)},
    "E_solimp_dmax0.999": {"cubie_solimp": (0.99, 0.999, 0.0005), "radial_solimplimit": (0.99, 0.999, 0.0005)},
    "H_armature25x": {"joint_armature": 2.5e-5},
    "I_armature250x": {"joint_armature": 2.5e-4},
    # follow-up, added after A-I showed ~10 deg twist at 0.05 N.m with <0.13 mm penetration:
    # is the radial play (preload seating + lift to the +0.2 mm stop) what permits the twist?
    "J_rigid_radius_dmax0.999": {"radial_preload": 0.0, "cubie_solimp": (0.99, 0.999, 0.0005)},
    "K_preload3N_dmax0.999": {"radial_preload": 3.0, "cubie_solimp": (0.99, 0.999, 0.0005),
                              "radial_solimplimit": (0.99, 0.999, 0.0005)},
}


def twist_staircase(cfg: str, corner_name: str) -> dict:
    ov = CONFIGS[cfg]
    t_wall = time.perf_counter()
    rec: dict = {"diagnostic": "D1", "scored": False, "config": cfg, "overrides": ov, "corner": corner_name,
                 "levels": []}
    try:
        tr = scored.Trial(scored.params_for(None, **ov), None, allow_test_wrench=True)
    except NumericalFailure as e:
        rec["aborted"] = f"settle: {e}"
        return rec
    ro, d, mon, sim = tr.ro, tr.sim.d, tr.mon, tr.sim
    corner = CORNERS[corner_name]
    idx = HOME_POSITIONS.index(corner)
    body = int(ro.body_ids[idx])
    axis = np.array(corner, float) / np.sqrt(3)
    others = [i for i, h in enumerate(HOME_POSITIONS) if np.count_nonzero(h) >= 2 and i != idx]
    _, rot0 = ro.poses(d)
    dt = tr.model.opt.timestep

    def rotvec(i: int, rot) -> np.ndarray:
        return Rotation.from_matrix(rot[i] @ rot0[i].T).as_rotvec()

    prev = 0.0
    try:
        for lvl in LEVELS_NM:
            mon.new_window()
            n_r, n_h = int(RAMP_S / dt), int(HOLD_S / dt)
            for k in range(n_r + n_h):
                tau = prev + (lvl - prev) * min(1.0, (k + 1) / n_r)
                sim.set_test_wrench(body, np.concatenate([np.zeros(3), tau * axis]))
                sim.step()
            _, rot = ro.poses(d)
            rv = rotvec(idx, rot)
            rec["levels"].append({
                "torque_Nm": lvl,
                "twist_about_diagonal_deg": float(np.degrees(rv @ axis)),
                "total_rotation_deg": float(np.degrees(np.linalg.norm(rv))),
                "max_neighbour_rotation_deg": float(max(np.degrees(np.linalg.norm(rotvec(i, rot))) for i in others)),
                "penetration_mm": max(0.0, -mon.window_min_dist) * 1000,
                "radial_out_mm_so_far": mon.max_radial_out * 1000,
                "radial_in_mm_so_far": mon.max_radial_in * 1000,
                "ncon": int(d.ncon),
            })
            prev = lvl
        sim.set_test_wrench(body, np.zeros(6))
        sim.step(int(0.5 / dt))
        _, rot = ro.poses(d)
        obs = ro.observe(d)
        rec["after_release_twist_deg"] = float(np.degrees(rotvec(idx, rot) @ axis))
        rec["after_release_observed_valid"] = obs.valid
    except (NumericalFailure, EditAuditError) as e:
        rec["aborted"] = f"{type(e).__name__}: {e}"
    rec["wall_s"] = time.perf_counter() - t_wall
    rec["sim_s"] = float(d.time)
    return rec


def turning_check(cfg: str) -> dict:
    t_wall = time.perf_counter()
    r = scored.run_sequence_trial(parse("U U' R R' F F'"), 5000, **CONFIGS[cfg])
    keep = {k: r.get(k) for k in ("pass", "aborted", "numerical_failures", "final_solved")}
    keep["per_move"] = [{k: m.get(k) for k in ("move", "observed_move", "turn_error_deg", "nontarget_drift_deg",
                                                "penetration_mm", "radial_above_nominal_mm_so_far",
                                                "max_turner_torque_Nm", "ok_all")} for m in r.get("per_move", [])]
    return {"diagnostic": "D1", "scored": False, "config": cfg, "overrides": CONFIGS[cfg], "turning": keep,
            "wall_s": time.perf_counter() - t_wall}


def _job(j: tuple[str, str]) -> tuple[str, dict]:
    cfg, case = j
    rec = turning_check(cfg) if case == "turn" else twist_staircase(cfg, case)
    name = f"{cfg}__{case}"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(rec, indent=1, default=list))
    return name, rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--only", nargs="*", help="run only these config names")
    a = ap.parse_args()
    jobs = [(c, k) for c in (a.only or CONFIGS) for k in ("ppp", "nnn", "turn")]
    jobs.sort(key=lambda j: CONFIGS[j[0]].get("timestep", 0.0005))  # slowest first
    with Pool(a.jobs) as pool:
        for name, rec in pool.imap_unordered(_job, jobs):
            print(name, "ABORT " + rec["aborted"] if "aborted" in rec else "", f"{rec['wall_s']:.0f}s", flush=True)
    (OUT / "environment.json").write_text(json.dumps(scored.environment(), indent=1))


if __name__ == "__main__":
    main()
