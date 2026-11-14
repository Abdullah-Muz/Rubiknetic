"""D6 — UNSCORED free-core study (P-09 condition before Phase 2): the cube is NOT fixed to the world.
Its core is a free body (6 DOF), held only by one face's gripper pads ("holder") while the
opposite face is turned by the M1 rig, as two arms would do in Phase 2.

Question 1: does M2's switch rule still work? INFERENCE before testing: the holding pads feel an equal
and opposite torque, so the rule sees two requesting faces and refuses.
Question 2: does a refined, still physical-state-only request rule fix it? A face REQUESTS an unlock
only if its pads (a) grip, (b) exert torque about the cube's own axis (core frame), and (c) rotate
relative to the core faster than OMEGA_REQ. Holding pads do not rotate relative to the core, so they
no longer request. (PROPOSAL; it would change pre-registration section 1 and needs approval.)

Setup (before t = 0, documented, diagnostic only): gravity is off for 0.3 s while the first holder
closes, then restored. The core gets 1.7 g of mass (Paulus 2023 BOM; ASSUMPTION).
Usage: uv run python experiments/D6_free_core/run_free.py <orig|refined> [seq="U R ..."]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "experiments" / "M2_switched_welds"))
from m2_model import build_m2_xml  # noqa: E402
from switching import SwitchAuditedSim, SwitchManager  # noqa: E402

from rubiknetic.cube_logic import parse  # noqa: E402
from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_logic.notation import FACE_NORMAL, OPPOSITE  # noqa: E402
from rubiknetic.cube_logic.transitions import infer_move  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params  # noqa: E402
from rubiknetic.cube_physics.readout import CubeReadout  # noqa: E402
from rubiknetic.cube_physics.rig import EditAuditError, NumericalFailure, TurnRig  # noqa: E402

OMEGA_REQ = 0.02  # rad/s: pad rotation relative to the core needed to count as a turn request
OUT = Path(__file__).parent / "results"


class RefinedManager(SwitchManager):
    """Same rule as M2, except the request test (pad torque) is computed about the CORE's axis and is
    gated by pad rotation relative to the core."""

    def __init__(self, sim, pitch=0.019):
        super().__init__(sim, pitch)
        m = sim.m
        self.turner = {f: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, f"turner_{f}") for f in "URFDLB"}
        self._v = np.zeros(6)

    def _ang_vel(self, d, b):
        mujoco.mj_objectVelocity(self.m, d, mujoco.mjtObj.mjOBJ_BODY, b, self._v, 0)
        return self._v[:3].copy()

    def pad_torque(self, d, face):
        Rc, pc = d.xmat[self.core].reshape(3, 3), d.xpos[self.core]
        n = Rc @ np.array(FACE_NORMAL[face], float)  # the face axis in world, attached to the cube
        tau, grip = 0.0, 0.0
        for i in range(d.ncon):
            c = d.contact[i]
            g1, g2 = int(c.geom1), int(c.geom2)
            if g1 in self.pads[face] and g2 in self.cubie_geom_body:
                sign = 1.0
            elif g2 in self.pads[face] and g1 in self.cubie_geom_body:
                sign = -1.0
            else:
                continue
            mujoco.mj_contactForce(self.m, d, i, self._f6)
            f = sign * (c.frame.reshape(3, 3).T @ self._f6[:3])
            tau += float(np.cross(c.pos - pc, f) @ n)
            grip += abs(self._f6[0])
        rel = (self._ang_vel(d, self.turner[face]) - self._ang_vel(d, self.core)) @ n
        if abs(rel) < OMEGA_REQ:
            tau = 0.0  # pads not rotating relative to the cube: holding, not turning
        return tau, grip


def build(m1o: dict) -> mujoco.MjModel:
    mp = M1Params(**{"radial_preload": 0.0, **m1o})
    xml = build_m2_xml(mp)
    xml = xml.replace('<body name="core" pos="0 0 0">',
                      '<body name="core" pos="0 0 0">\n      <freejoint name="core_free"/>\n'
                      '      <inertial pos="0 0 0" mass="0.0017" diaginertia="2e-8 2e-8 2e-8"/>', 1)
    return mujoco.MjModel.from_xml_string(xml), mp


def run(mode: str, seq: str, m1o: dict) -> dict:
    m, mp = build(m1o)
    sim = SwitchAuditedSim(m)
    mujoco.mj_forward(m, sim.d)
    mgr = (RefinedManager if mode == "refined" else SwitchManager)(sim, mp.pitch)
    rig = TurnRig(sim, pad_close_target=-(mp.pad_open_clearance + mp.grip_overshoot))
    ro = CubeReadout(m, mp.pitch)
    d, dt = sim.d, m.opt.timestep
    close = -(mp.pad_open_clearance + mp.grip_overshoot)
    aid = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, n)  # noqa: E731
    pen = {"v": 0.0}
    sim.hooks.append(lambda dd: pen.__setitem__("v", max(pen["v"], -float(dd.contact.dist[:dd.ncon].min()) * 1000 if dd.ncon else 0.0)))

    def set_holder(face, closed):
        for s in "ab":
            d.ctrl[aid(f"grip_{face}{s}")] = close if closed else 0.0

    moves = parse(seq)
    holder = OPPOSITE[moves[0].face]
    g = m.opt.gravity.copy()
    m.opt.gravity[:] = 0.0  # setup only: hold the free cube while the first holder closes
    set_holder(holder, True)
    sim.step(int(0.3 / dt))
    m.opt.gravity[:] = g
    sim.step(int(0.3 / dt))
    core_p0, core_R0 = d.xpos[mgr.core].copy(), d.xmat[mgr.core].reshape(3, 3).copy()
    prev = ro.observe(d).cube
    rows = []
    t0 = time.perf_counter()
    for mv in moves:
        want = OPPOSITE[mv.face]
        if want != holder:  # regrasp: close the new holder, then release the old one
            set_holder(want, True)
            sim.step(int(0.3 / dt))
            set_holder(holder, False)
            sim.step(int(0.3 / dt))
            holder = want
        _, r0 = ro.poses(d)
        members = ro.layer_members(d, mv.face)
        others = [i for i in range(26) if sum(map(abs, HOME_POSITIONS[i])) >= 2 and i not in members]
        cp, cR = d.xpos[mgr.core].copy(), d.xmat[mgr.core].reshape(3, 3).copy()
        nlog = len(sim.switch_log)
        pen["v"] = 0.0
        try:
            log = rig.turn(mv)
        except (NumericalFailure, EditAuditError) as e:
            rows.append({"move": str(mv), "aborted": str(e)})
            break
        _, r = ro.poses(d)
        ang = CubeReadout.rotation_about_deg(r0, r, members, mv.face)
        drift = float(np.max(np.abs(CubeReadout.rotation_about_deg(r0, r, others, mv.face))))
        obs = ro.observe(d)
        try:
            om = infer_move(prev, obs.cube) if obs.valid else None
        except Exception as e:  # noqa: BLE001
            om = f"inconsistent: {e}"
        if obs.valid:
            prev = obs.cube
        core_slip_mm = float(np.linalg.norm(d.xpos[mgr.core] - cp) * 1000)
        core_rot = float(np.degrees(np.linalg.norm(Rotation.from_matrix(d.xmat[mgr.core].reshape(3, 3) @ cR.T).as_rotvec())))
        sw = sim.switch_log[nlog:]
        nominal = -90.0 * {1: 1, 2: 2, 3: -1}[mv.quarter_turns]
        rows.append({"move": str(mv), "holder": holder, "observed": str(om), "ok": str(om) == str(mv),
                     "layer_deg": float(np.mean(ang)), "error_deg": float(np.mean(ang) - nominal), "drift_deg": drift,
                     "core_slip_mm": core_slip_mm, "core_rot_deg": core_rot, "penetration_mm": pen["v"],
                     "peak_turner_torque_Nm": float(np.max(np.abs(log.turner_torque))),
                     "unlocks": sum(e["kind"] == "unlock" for e in sw), "refusals": [e.get("reason") for e in sw if e["kind"] == "refuse"],
                     "max_abs_dKE_J": max((abs(e.get("dke", 0)) for e in sw if e["kind"] in ("unlock", "relock")), default=0.0)})
        print(json.dumps(rows[-1])[:260], flush=True)
    el = time.perf_counter() - t0
    total_slip = float(np.linalg.norm(d.xpos[mgr.core] - core_p0) * 1000)
    total_rot = float(np.degrees(np.linalg.norm(Rotation.from_matrix(d.xmat[mgr.core].reshape(3, 3) @ core_R0.T).as_rotvec())))
    return {"study": "D6", "scored": False, "mode": mode, "seq": seq, "moves": rows, "all_ok": all(r.get("ok") for r in rows),
            "total_core_slip_mm": total_slip, "total_core_rot_deg": total_rot, "steps_per_s": sim.steps / el}


if __name__ == "__main__":
    mode = sys.argv[1]
    seq = "U R U' R' F F' D2 L B'"
    m1o = {}
    for kv in sys.argv[2:]:
        k, v = kv.split("=", 1)
        if k == "seq":
            seq = v
        else:
            m1o[k] = type(getattr(M1Params(), k))(v)
    res = run(mode, seq, m1o)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{mode}.json").write_text(json.dumps(res, indent=1))
    print(f"== {mode}: all_ok {res['all_ok']}, total core slip {res['total_core_slip_mm']:.2f} mm, "
          f"rotation {res['total_core_rot_deg']:.2f} deg, {res['steps_per_s']:.0f} steps/s")
