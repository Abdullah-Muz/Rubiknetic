"""D2 — UNSCORED deep dive: where does M1's ~12 deg free corner-twist play come from?

Part 1 (kinematic probe, no dynamics): with every other cubie held at a fixed
pose, rotate the target corner about its diagonal by theta and query signed
distances (mj_geomDistance). Gives the purely geometric free twist of ONE
corner inside rigid neighbours, versus chamfer, gap and radial lift. These are
direct qpos writes for a geometry query, never a simulation step, so no
integrity rule applies (this is not an evaluation).

Part 2 (dynamic decomposition): repeat the D1 torque staircase while welding
subsets of cubies to the fixed core (equality welds added to the model, a
diagnostic-only modification):
  corner_only   every cubie except the target is welded;
  plus_edges    the target and its 3 adjacent edges are free;
  plus_ring     the target, its 3 edges, and the 3 adjacent centres and the
                other cubies of the 3 faces it touches are free;
  all_free      unmodified M1 (equivalent to D1).
Contact settings use D1 config E (solimp dmax 0.999) so the solver is stable.

Usage (WSL2, repo root): uv run python experiments/D2_twist_mechanism/run.py
"""

from __future__ import annotations

import json
from multiprocessing import Pool
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

from rubiknetic.cube_logic.geometric import HOME_POSITIONS
from rubiknetic.cube_physics import scored
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml, cubie_name
from rubiknetic.cube_physics.readout import CubeReadout
from rubiknetic.cube_physics.rig import AuditedSim, NumericalFailure

OUT = Path(__file__).parent / "results"
CORNER = (1, 1, 1)
AXIS = np.array(CORNER, float) / np.sqrt(3)
STABLE = {"cubie_solimp": (0.99, 0.999, 0.0005), "radial_solimplimit": (0.99, 0.999, 0.0005)}
LEVELS_NM = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]


# ------------------------------------------------------------------ part 1
def _settled_qpos(p: M1Params) -> np.ndarray:
    m = mujoco.MjModel.from_xml_string(build_m1_xml(p))
    d = mujoco.MjData(m)
    for _ in range(int(0.5 / m.opt.timestep)):
        mujoco.mj_step(m, d)
    return d.qpos.copy()


def kinematic_probe(chamfer: float, gap: float, base: str, lift_mm: float | None) -> dict:
    """base: 'nominal' (qpos0, every cubie at home, gaps open) or 'settled'
    (rest pose after 0.5 s under the 1 N preload). lift_mm: target corner's
    radial slide position in mm (None = keep the base value)."""
    p = M1Params(rig=False, chamfer=chamfer, gap=gap)
    m = mujoco.MjModel.from_xml_string(build_m1_xml(p))
    d = mujoco.MjData(m)
    q0 = m.qpos0.copy() if base == "nominal" else _settled_qpos(p)
    name = cubie_name(CORNER)
    jb = m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, f"{name}_j")]
    js = m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, f"{name}_r")]
    g_t = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, f"{name}_g")
    others = {cubie_name(h): mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, f"{cubie_name(h)}_g")
              for h in HOME_POSITIONS if h != CORNER}
    quat_base = q0[jb:jb + 4].copy()
    fromto = np.zeros(6)
    curve = []
    first_contact = None
    for theta in np.arange(0.0, 30.01, 0.25):
        d.qpos[:] = q0
        rq = Rotation.from_rotvec(np.radians(theta) * AXIS)
        rb = Rotation.from_quat(quat_base[[1, 2, 3, 0]])
        x, y, z, w = (rq * rb).as_quat()
        d.qpos[jb:jb + 4] = [w, x, y, z]
        if lift_mm is not None:
            d.qpos[js] = lift_mm / 1000
        mujoco.mj_kinematics(m, d)
        dists = {n: mujoco.mj_geomDistance(m, d, g_t, g, 0.01, fromto) for n, g in others.items()}
        nmin = min(dists, key=dists.get)
        curve.append({"theta_deg": float(theta), "min_dist_mm": dists[nmin] * 1000, "closest": nmin})
        if first_contact is None and dists[nmin] < 0:
            first_contact = {"theta_deg": float(theta), "with": nmin}
    return {"part": 1, "chamfer_mm": chamfer * 1000, "gap_mm": gap * 1000, "base": base,
            "lift_mm": lift_mm, "corner_slide_mm_used": float(d.qpos[js] * 1000),
            "dist_at_0_mm": curve[0]["min_dist_mm"], "free_twist_deg": first_contact and first_contact["theta_deg"],
            "first_contact_with": first_contact and first_contact["with"], "curve": curve[::4]}


# ------------------------------------------------------------------ part 2
def _free_set(mode: str) -> set[tuple[int, int, int]]:
    if mode == "all_free":
        return set(HOME_POSITIONS)
    if mode == "corner_only":
        return {CORNER}
    edges = {h for h in HOME_POSITIONS if np.count_nonzero(h) == 2
             and sum(int(a == b) for a, b in zip(h, CORNER)) == 2}
    if mode == "plus_edges":
        return {CORNER} | edges
    if mode == "plus_ring":  # every cubie on the three faces that contain the corner
        return {h for h in HOME_POSITIONS if any(h[i] == CORNER[i] for i in range(3))}
    # follow-up (added after the first D2 run): is the play the adjacent face layers turning?
    centres = {h for h in HOME_POSITIONS if np.count_nonzero(h) == 1}
    if mode == "no_centres":  # everything free except the 6 centre hinges (welded)
        return set(HOME_POSITIONS) - centres
    if mode == "no_adj_centres":  # everything free except the 3 centres touching the corner
        return set(HOME_POSITIONS) - {h for h in centres if any(h[i] == CORNER[i] != 0 for i in range(3))}
    raise ValueError(mode)


def _welded_xml(p: M1Params, free: set) -> str:
    xml = build_m1_xml(p)
    welds = "\n".join(f'    <weld body1="{cubie_name(h)}" body2="core" solref="0.0005 1" '
                      f'solimp="0.99 0.999 0.0005"/>' for h in HOME_POSITIONS if h not in free)
    if not welds:
        return xml
    return xml.replace("  <actuator>", f"  <equality>\n{welds}\n  </equality>\n  <actuator>", 1)


def decomposition(mode: str, overrides: dict | None = None) -> dict:
    p = M1Params(**{**STABLE, **(overrides or {})})
    free = _free_set(mode)
    m = mujoco.MjModel.from_xml_string(_welded_xml(p, free))
    sim = AuditedSim(m, allow_test_wrench=True)
    ro = CubeReadout(m, p.pitch)
    d = sim.d
    idx = HOME_POSITIONS.index(CORNER)
    body = int(ro.body_ids[idx])
    sim.step(int(0.5 / m.opt.timestep))
    _, rot0 = ro.poses(d)
    dt = m.opt.timestep
    nbr = [i for i, h in enumerate(HOME_POSITIONS) if np.count_nonzero(h) >= 2 and i != idx]
    rec = {"part": 2, "mode": mode, "n_free_cubies": len(free), "levels": []}
    prev = 0.0
    try:
        for lvl in LEVELS_NM:
            n_r, n_h = int(0.05 / dt), int(0.25 / dt)
            for k in range(n_r + n_h):
                tau = prev + (lvl - prev) * min(1.0, (k + 1) / n_r)
                sim.set_test_wrench(body, np.concatenate([np.zeros(3), tau * AXIS]))
                sim.step()
            _, rot = ro.poses(d)
            rv = Rotation.from_matrix(rot[idx] @ rot0[idx].T).as_rotvec()
            per_nbr = {cubie_name(HOME_POSITIONS[i]):
                       float(np.degrees(np.linalg.norm(Rotation.from_matrix(rot[i] @ rot0[i].T).as_rotvec())))
                       for i in nbr}
            top = sorted(per_nbr.items(), key=lambda kv: -kv[1])[:5]
            centre_deg = {cubie_name(h)[6:]: float(np.degrees(d.qpos[m.jnt_qposadr[mujoco.mj_name2id(
                m, mujoco.mjtObj.mjOBJ_JOINT, f"{cubie_name(h)}_j")]]))
                for h in HOME_POSITIONS if np.count_nonzero(h) == 1}
            rec["levels"].append({"torque_Nm": lvl, "twist_deg": float(np.degrees(rv @ AXIS)),
                                  "top_neighbour_rotations_deg": top, "centre_hinge_deg": centre_deg,
                                  "corner_slide_mm": float(d.qpos[m.jnt_qposadr[mujoco.mj_name2id(
                                      m, mujoco.mjtObj.mjOBJ_JOINT, f"{cubie_name(CORNER)}_r")]] * 1000)})
            prev = lvl
    except NumericalFailure as e:
        rec["aborted"] = str(e)
    return rec


def _job(j):
    return kinematic_probe(*j[1:]) if j[0] == "k" else decomposition(j[1])


def followup() -> None:
    """Second D2 run: centre-locking modes, plus all_free again for the centre hinge angles."""
    with Pool(3) as pool:
        res = pool.map(decomposition, ["all_free", "no_centres", "no_adj_centres"])
    (OUT / "d2_followup_centres.json").write_text(json.dumps({"diagnostic": "D2-followup", "scored": False,
                                                              "results": res}, indent=1, default=list))
    for r in res:
        print(f"D {r['mode']:15s} free={r['n_free_cubies']:2d} {r.get('aborted', '')}")
        for L in r["levels"]:
            c = {k: round(v, 2) for k, v in L["centre_hinge_deg"].items() if abs(v) > 0.05}
            print(f"    {L['torque_Nm']:6.3f} Nm twist={L['twist_deg']:7.2f} slide={L['corner_slide_mm']:+.2f}mm "
                  f"edges={[round(v, 1) for _, v in L['top_neighbour_rotations_deg'][:3]]} centres={c}")


# follow-up 2 (added after follow-up 1): which parameters set breakaway torque and post-breakaway slack,
# and does any of them keep turning working? All runs: all cubies free, stable contact settings.
LEVERS = {
    "ref_preload1N_stop+0.2": {},
    "preload3N": {"radial_preload": 3.0},
    "preload10N": {"radial_preload": 10.0},
    "stop0.0mm": {"radial_range": (-0.001, 0.0)},
    "stop-0.15mm": {"radial_range": (-0.001, -0.00015)},
    "stop-0.25mm": {"radial_range": (-0.001, -0.00025)},
    "gap0.1mm": {"gap": 0.0001},
    "gap0.05mm": {"gap": 0.00005},
}


def _lever_job(j: tuple[str, str]) -> dict:
    name, kind = j
    ov = LEVERS[name]
    if kind == "twist":
        r = decomposition("all_free", ov)
        r["lever"] = name
        return r
    from rubiknetic.cube_logic import parse
    t = scored.run_sequence_trial(parse("U U' R R' F F'"), 5000, **{**STABLE, **ov})
    pm = t.get("per_move", [])
    return {"lever": name, "kind": "turn", "pass": t["pass"], "aborted": t.get("aborted"),
            "moves_ok": sum(bool(m["ok_all"]) for m in pm), "n_moves": len(pm),
            "max_turn_error_deg": max((abs(m["turn_error_deg"]) for m in pm), default=None),
            "max_penetration_mm": max((m["penetration_mm"] for m in pm), default=None),
            "max_turner_torque_Nm": max((m["max_turner_torque_Nm"] for m in pm), default=None),
            "observed": [m["observed_move"] for m in pm]}


def followup2() -> None:
    jobs = [(n, k) for n in LEVERS for k in ("turn", "twist")]
    with Pool(8) as pool:
        res = pool.map(_lever_job, jobs)
    (OUT / "d2_followup_levers.json").write_text(json.dumps({"diagnostic": "D2-followup2", "scored": False,
                                                             "results": res}, indent=1, default=list))
    for n in LEVERS:
        tw = next(r for r in res if r["lever"] == n and r.get("part") == 2)
        tu = next(r for r in res if r["lever"] == n and r.get("kind") == "turn")
        curve = " ".join(f"{L['torque_Nm']:g}:{L['twist_deg']:.1f}" for L in tw["levels"])
        print(f"{n:24s} TURN {'pass' if tu['pass'] else 'FAIL'} {tu['moves_ok']}/{tu['n_moves']} "
              f"err={tu['max_turn_error_deg'] and round(tu['max_turn_error_deg'], 2)} "
              f"tq={tu['max_turner_torque_Nm'] and round(tu['max_turner_torque_Nm'], 2)} obs={tu['observed']}"
              f"\n{'':24s} TWIST {curve} {tw.get('aborted', '')}")


def main() -> None:
    import sys
    if "--followup" in sys.argv:
        followup()
        return
    if "--followup2" in sys.argv:
        followup2()
        return
    jobs = []
    for base, lift in (("nominal", None), ("settled", None), ("settled", 0.2)):
        jobs.append(("k", 0.0014, 0.0002, base, lift))
    for c in (0.0, 0.0005, 0.001, 0.002):
        jobs.append(("k", c, 0.0002, "settled", None))
    for g in (0.0001, 0.0003):
        jobs.append(("k", 0.0014, g, "settled", None))
    jobs += [("d", mode) for mode in ("corner_only", "plus_edges", "plus_ring", "all_free")]
    OUT.mkdir(parents=True, exist_ok=True)
    with Pool(8) as pool:
        res = pool.map(_job, jobs)
    (OUT / "d2_results.json").write_text(json.dumps({"diagnostic": "D2", "scored": False,
                                                     "environment": scored.environment(), "results": res},
                                                    indent=1, default=list))
    for r in res:
        if r["part"] == 1:
            print(f"K chamfer={r['chamfer_mm']:.1f} gap={r['gap_mm']:.1f} base={r['base']:8s} lift={r['lift_mm']} "
                  f"slide={r['corner_slide_mm_used']:+.3f}mm d0={r['dist_at_0_mm']:+.3f}mm "
                  f"FREE TWIST={r['free_twist_deg']} deg first contact {r['first_contact_with']}")
        else:
            print(f"D {r['mode']:12s} free={r['n_free_cubies']:2d} {r.get('aborted', '')}")
            for L in r["levels"]:
                print(f"    {L['torque_Nm']:6.3f} Nm twist={L['twist_deg']:7.2f} slide={L['corner_slide_mm']:+.2f}mm "
                      f"nbrs={[(n[6:], round(v, 2)) for n, v in L['top_neighbour_rotations_deg'][:3]]}")


if __name__ == "__main__":
    main()
