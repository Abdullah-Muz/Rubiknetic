"""D5 stage-2: face turns with the UNCHANGED M1 pad rig (two gripper pads per face plus a
turner, grip 10 N, turner torque limit 1 N.m, 1 s per quarter turn). UNSCORED.

Per move: layer rotation and error, non-target drift (non-centre pieces only), penetration, peak
turner torque, and whether the observed state matches the oracle applied to the OBSERVED move.
Usage: uv run python experiments/D5_follower_cube/rig_turn.py [seq="U R U' R'"] [d5 k=v ...] [m1.k=v ...]
"""
from __future__ import annotations

import sys
import time

import mujoco
import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from cube_d5 import D5Params, build_xml_with_rig  # noqa: E402

from rubiknetic.cube_logic import parse  # noqa: E402
from rubiknetic.cube_logic.cubie import SOLVED  # noqa: E402
from rubiknetic.cube_logic.transitions import infer_move  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params  # noqa: E402
from rubiknetic.cube_physics.readout import CubeReadout  # noqa: E402
from rubiknetic.cube_physics.rig import AuditedSim, EditAuditError, NumericalFailure, TurnRig  # noqa: E402

PITCH = 0.019
_NONCENTRE = [i for i in range(26)]


def main():
    seq = "U R U' R' F F' D2 L B'"
    p = D5Params(bevel_body=1.0, bevel_foot=0.5, gap=0.05, clearance=0.02, spring_preload=10.0, spring_k=2000.0,
                 slide_range=(-0.001, 0.0003))
    m1o = {}
    for kv in sys.argv[1:]:
        k, v = kv.split("=", 1)
        if k == "seq":
            seq = v
        elif k.startswith("m1."):
            cur = getattr(M1Params(), k[3:])
            m1o[k[3:]] = type(cur)(v)
        else:
            cur = getattr(p, k)
            setattr(p, k, type(cur)(v) if not isinstance(cur, tuple) else tuple(float(x) for x in v.split(",")))
    xml, _ = build_xml_with_rig(p, m1o)
    m = mujoco.MjModel.from_xml_string(xml)
    import os
    import detent  # P-16 core-centre detent (0 = off)
    detent.install(m, float(os.environ.get("D5_DETENT", "0")))
    sim = AuditedSim(m)
    mujoco.mj_forward(m, sim.d)
    ro = CubeReadout(m, PITCH)
    mp = M1Params(**m1o)
    rig = TurnRig(sim, pad_close_target=-(mp.pad_open_clearance + mp.grip_overshoot))
    d = sim.d
    pad_geoms = {g for g in range(m.ngeom) if (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, g) or "").startswith("pad_")}
    pen = {"pad": 0.0, "piece": 0.0}

    def hook(dd):  # read-only: classify the deepest contact of each kind
        n = dd.ncon
        if not n:
            return
        g1, g2, dist = dd.contact.geom1[:n], dd.contact.geom2[:n], dd.contact.dist[:n]
        is_pad = np.array([a in pad_geoms or b in pad_geoms for a, b in zip(g1, g2)])
        if is_pad.any():
            pen["pad"] = max(pen["pad"], -dist[is_pad].min() * 1000)
        if (~is_pad).any():
            pen["piece"] = max(pen["piece"], -dist[~is_pad].min() * 1000)

    sim.hooks.append(hook)
    sim.step(int(0.3 / m.opt.timestep))
    obs0 = ro.observe(d)
    print(f"D5 + M1 rig: ngeom {m.ngeom}, friction {p.friction}, spring {p.spring_preload} N, grip {mp.grip_force} N, "
          f"turner limit {mp.turn_torque_limit} N.m | start observed valid {obs0.valid}, solved {obs0.valid and obs0.state == SOLVED}")
    prev = obs0.cube
    t0 = time.perf_counter()
    steps0 = 0
    for mv in parse(seq):
        _, rot0 = ro.poses(d)
        members = ro.layer_members(d, mv.face)
        others = [i for i in range(26) if np.count_nonzero(np.array(ro.poses(d)[0][i]).round()) >= 2 and i not in members]
        n0 = sim.d.time
        pen["pad"] = pen["piece"] = 0.0
        try:
            log = rig.turn(mv)
        except (NumericalFailure, EditAuditError) as e:
            print(f"  {mv}: ABORT {e}")
            return
        steps0 += int((sim.d.time - n0) / m.opt.timestep)
        _, rot = ro.poses(d)
        ang = CubeReadout.rotation_about_deg(rot0, rot, members, mv.face)
        drift = np.max(np.abs(CubeReadout.rotation_about_deg(rot0, rot, others, mv.face))) if others else 0.0
        nominal = -90.0 * {1: 1, 2: 2, 3: -1}[mv.quarter_turns]
        obs = ro.observe(d)
        try:
            observed = infer_move(prev, obs.cube) if obs.valid else None
        except Exception:
            observed = "inconsistent"
        ok = obs.valid and observed is not None and str(observed) == str(mv)
        if obs.valid:
            prev = obs.cube

        print(f"  {str(mv):3s}: layer {np.mean(ang):+8.2f} deg (error {np.mean(ang) - nominal:+6.2f}, spread {np.ptp(ang):5.2f}) | "
              f"drift {drift:5.2f} | pen pad {pen['pad']:.3f} piece {pen['piece']:.3f} mm | peak turner torque {np.max(np.abs(log.turner_torque)):.3f} N.m | "
              f"observed move {observed} {'OK' if ok else 'MISMATCH'}")
    el = time.perf_counter() - t0
    print(f"  wall {el:.0f} s for {sim.d.time:.1f} s simulated ({steps0 / el:.0f} steps/s); detent tau_max {os.environ.get('D5_DETENT', '0')} N.m, peak detent torque {detent.peak_torque():.3f}")


if __name__ == "__main__":
    main()
