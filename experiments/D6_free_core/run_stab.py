"""D6b — UNSCORED free-core study with a two-layer STABILISER grip.

The free cube is held by a stabiliser: two tall pads on slide joints spanning the D and E layers,
as a robot or human would hold it. The U face is turned by the M1 rig.

Rules compared:
  orig  — M2's rule unchanged;
  shear — PROPOSAL: for every face F, the boundary shear is the torque about F's axis (core frame)
          that all pad and stabiliser contacts apply to the cubies currently in F's layer. The face
          with the clearly largest |shear| (at least 1.5x the next, and above TAU_UNLOCK) requests;
          otherwise every face above threshold "requests", which makes M2 refuse (ambiguous loads).
Physical state only: contact forces, poses, no commanded move.
Setup (before t = 0, diagnostic): gravity is off for 0.3 s while the stabiliser closes.
Usage: uv run python experiments/D6_free_core/run_stab.py <orig|shear> [seq="U U' U2 U' U"] [stab_hold=D|DE]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from run_free import build as _build_free  # noqa: E402,F401
from run_free import REPO  # noqa: E402

sys.path.insert(0, str(REPO / "experiments" / "M2_switched_welds"))
from m2_model import build_m2_xml  # noqa: E402
from switching import TAU_UNLOCK, SwitchAuditedSim, SwitchManager  # noqa: E402

from rubiknetic.cube_logic import parse  # noqa: E402
from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES  # noqa: E402
from rubiknetic.cube_logic.transitions import infer_move  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params  # noqa: E402
from rubiknetic.cube_physics.readout import CubeReadout  # noqa: E402
from rubiknetic.cube_physics.rig import EditAuditError, NumericalFailure, TurnRig  # noqa: E402

OUT = Path(__file__).parent / "results"
DOMINANCE = 1.5
STAB_FORCE = 30.0  # N per stabiliser pad


def build(stab_hold: str):
    mp = M1Params(radial_preload=0.0)
    xml = build_m2_xml(mp)
    xml = xml.replace('<body name="core" pos="0 0 0">',
                      '<body name="core" pos="0 0 0">\n      <freejoint name="core_free"/>\n'
                      '      <inertial pos="0 0 0" mass="0.0017" diaginertia="2e-8 2e-8 2e-8"/>', 1)
    H = 0.0284
    if stab_hold == "DE":
        zc, hz = (-H + 0.0090) / 2, (H + 0.0090) / 2 - 0.0005   # covers the D and E layers (z from -28.4 to +9.0 mm)
    else:
        zc, hz = -0.019, 0.0045                                 # covers the D layer only
    t = 0.0025
    y0 = H + 0.014 + t
    stab = []
    acts = []
    for s, name in ((-1, "a"), (1, "b")):
        stab.append(f'    <body name="stab_{name}" pos="0 {s * y0:.6f} {zc:.6f}">\n'
                    f'      <joint name="stab_{name}_slide" type="slide" axis="0 {s} 0" range="-0.05 0.001" damping="100"/>\n'
                    f'      <geom name="stab_{name}_g" type="box" size="0.020 {t:.4f} {hz:.5f}" contype="2" conaffinity="0" '
                    f'condim="4" friction="0.8 0.005 0.0001" solref="0.001 1" solimp="0.95 0.99 0.0005" mass="0.01" rgba="0.2 0.6 0.9 1"/>\n'
                    f'    </body>')
        acts.append(f'    <position name="stab_{name}" joint="stab_{name}_slide" kp="2000" forcerange="{-STAB_FORCE} {STAB_FORCE}" ctrlrange="-0.05 0.001"/>')
    xml = xml.replace("  </worldbody>", "\n".join(stab) + "\n  </worldbody>", 1)
    xml = xml.replace("  <actuator>\n", "  <actuator>\n" + "\n".join(acts) + "\n", 1)
    return mujoco.MjModel.from_xml_string(xml), mp


class ShearManager(SwitchManager):
    def __init__(self, sim, pitch=0.019):
        super().__init__(sim, pitch)
        m = sim.m
        names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, g) or "" for g in range(m.ngeom)]
        self.all_pads = {g for g, n in enumerate(names) if n.startswith(("pad_", "stab_"))}
        self._cache = (None, None)

    def _shears(self, d):
        if self._cache[0] == d.time:
            return self._cache[1]
        Rc, pc = d.xmat[self.core].reshape(3, 3), d.xpos[self.core]
        pos, _ = self.ro.poses(d)
        body_to_idx = {int(self.ro.body_ids[i]): i for i in range(26)}
        out = {}
        contacts = []
        for i in range(d.ncon):
            c = d.contact[i]
            g1, g2 = int(c.geom1), int(c.geom2)
            if g1 in self.all_pads and g2 in self.cubie_geom_body:
                sign, cg = 1.0, g2
            elif g2 in self.all_pads and g1 in self.cubie_geom_body:
                sign, cg = -1.0, g1
            else:
                continue
            mujoco.mj_contactForce(self.m, d, i, self._f6)
            f = sign * (c.frame.reshape(3, 3).T @ self._f6[:3])
            contacts.append((body_to_idx[self.cubie_geom_body[cg]], c.pos - pc, f, abs(self._f6[0])))
        for F in FACES:
            nF = np.array(FACE_NORMAL[F], float)
            n = Rc @ nF
            members = {i for i in range(26) if pos[i] @ nF > 0.5}
            tau = sum(float(np.cross(r, f) @ n) for i, r, f, _ in contacts if i in members)
            grip = sum(g for i, _, _, g in contacts if i in members)
            out[F] = (tau, grip)
        self._cache = (d.time, out)
        return out

    def pad_torque(self, d, face):
        sh = self._shears(d)
        mags = sorted(((abs(t), F) for F, (t, _) in sh.items()), reverse=True)
        (m1, f1), (m2, _) = mags[0], mags[1]
        tau, grip = sh[face]
        if m1 >= TAU_UNLOCK and m1 >= DOMINANCE * m2:
            return (tau, grip) if face == f1 else (0.0, grip)
        return tau, grip  # ambiguous: every face above threshold requests, so M2 refuses


def run(mode, seq, stab_hold):
    m, mp = build(stab_hold)
    sim = SwitchAuditedSim(m)
    mujoco.mj_forward(m, sim.d)
    mgr = (ShearManager if mode == "shear" else SwitchManager)(sim, mp.pitch)
    rig = TurnRig(sim, pad_close_target=-(mp.pad_open_clearance + mp.grip_overshoot))
    ro = CubeReadout(m, mp.pitch)
    d, dt = sim.d, m.opt.timestep
    aid = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, n)  # noqa: E731
    g = m.opt.gravity.copy()
    m.opt.gravity[:] = 0.0
    for s in "ab":
        d.ctrl[aid(f"stab_{s}")] = -0.016
    sim.step(int(0.3 / dt))
    m.opt.gravity[:] = g
    sim.step(int(0.3 / dt))
    prev = ro.observe(d).cube
    rows, t0 = [], time.perf_counter()
    for mv in parse(seq):
        _, r0 = ro.poses(d)
        members = ro.layer_members(d, mv.face)
        others = [i for i in range(26) if sum(map(abs, HOME_POSITIONS[i])) >= 2 and i not in members]
        cp, cR = d.xpos[mgr.core].copy(), d.xmat[mgr.core].reshape(3, 3).copy()
        nlog = len(sim.switch_log)
        try:
            log = rig.turn(mv)
        except (NumericalFailure, EditAuditError) as e:
            rows.append({"move": str(mv), "aborted": str(e)})
            break
        _, r = ro.poses(d)
        ang = CubeReadout.rotation_about_deg(r0, r, members, mv.face)
        obs = ro.observe(d)
        try:
            om = infer_move(prev, obs.cube) if obs.valid else None
        except Exception as e:  # noqa: BLE001
            om = f"inconsistent: {e}"
        if obs.valid:
            prev = obs.cube
        sw = sim.switch_log[nlog:]
        nominal = -90.0 * {1: 1, 2: 2, 3: -1}[mv.quarter_turns]
        rows.append({"move": str(mv), "observed": str(om), "ok": str(om) == str(mv), "layer_deg": float(np.mean(ang)),
                     "error_deg": float(np.mean(ang) - nominal),
                     "drift_deg": float(np.max(np.abs(CubeReadout.rotation_about_deg(r0, r, others, mv.face)))),
                     "core_slip_mm": float(np.linalg.norm(d.xpos[mgr.core] - cp) * 1000),
                     "core_rot_deg": float(np.degrees(np.linalg.norm(Rotation.from_matrix(d.xmat[mgr.core].reshape(3, 3) @ cR.T).as_rotvec()))),
                     "peak_turner_torque_Nm": float(np.max(np.abs(log.turner_torque))),
                     "unlocked": [e.get("face") for e in sw if e["kind"] == "unlock"],
                     "refusals": [e.get("reason") for e in sw if e["kind"] == "refuse"],
                     "max_abs_dKE_J": max((abs(e.get("dke", 0)) for e in sw if e["kind"] in ("unlock", "relock")), default=0.0)})
        r_ = rows[-1]
        print(f"  {r_['move']:3s} obs {r_['observed']:5s} ok {r_['ok']!s:5s} err {r_['error_deg']:+7.2f} drift {r_['drift_deg']:5.2f} "
              f"core slip {r_['core_slip_mm']:5.2f} mm rot {r_['core_rot_deg']:5.2f} deg tq {r_['peak_turner_torque_Nm']:.2f} "
              f"unlocked {r_['unlocked']} refusals {r_['refusals']} dKE {r_['max_abs_dKE_J']:.1e}", flush=True)
    return {"study": "D6b", "scored": False, "mode": mode, "seq": seq, "stab_hold": stab_hold, "moves": rows,
            "all_ok": all(r.get("ok") for r in rows), "steps_per_s": sim.steps / (time.perf_counter() - t0)}


if __name__ == "__main__":
    mode = sys.argv[1]
    seq, hold = "U U' U2 U' U", "DE"
    for kv in sys.argv[2:]:
        k, v = kv.split("=", 1)
        if k == "seq":
            seq = v
        elif k == "stab_hold":
            hold = v
    print(f"== mode {mode}, stabiliser on {hold}, seq {seq}")
    res = run(mode, seq, hold)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"stab_{mode}_{hold}.json").write_text(json.dumps(res, indent=1))
    print(f"== all_ok {res['all_ok']}, {res['steps_per_s']:.0f} steps/s")
