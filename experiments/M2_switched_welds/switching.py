"""M2 switch manager and the audited simulator that permits ONLY its writes.

Audit exception (PHASE_1_2_VALIDATION_EXPERIMENTS rule 2: "approved, logged mechanism ... M2
switching rule"): `SwitchAuditedSim` extends `AuditedSim`. It also snapshots `mjModel.eq_data`
(weld relposes) between steps. The registered `SwitchManager` is the only caller allowed to
change `d.eq_active` or `m.eq_data` (through `apply_switch`), and every call is logged. Any
other change to those arrays, or to qpos/qvel/act/xfrc/qfrc/mocap, still raises EditAuditError.

Switch rule (uses ONLY physical state: poses, velocities, and contact forces from the rig's pads
on the cubies, read as a sensor; never the commanded move or the oracle state):
  UNLOCK face F when, with no layer unlocked:
    (a) the whole cube is aligned: every non-centre cubie within TOL_UNLOCK_DEG of a lattice
        rotation and within 0.15 pitch of a lattice position;
    (b) the pads of F grip (pad->cubie normal force > GRIP_MIN_N); and
    (c) the pad contact torque about F's axis on the cubies exceeds TAU_UNLOCK.
    If two faces satisfy (b) and (c) at once, both are refused (opposed-torque case).
  Unlock moves F's layer cubies from w_<cubie>_core to w_<cubie>_<centreF>, re-anchored at the
  current relative pose (zero violation), and releases w_<centreF>_core.
  RELOCK the unlocked face when its centre hinge is within TOL_LOCK_DEG of a multiple of 90 deg,
  every layer cubie is within TOL_LOCK_DEG of a lattice rotation, |pad torque| < TAU_RELOCK and
  |hinge speed| < OMEGA_RELOCK. Relock re-anchors to the core at the current pose (zero violation:
  no snap to the exact 90 deg).
  Requests while the cube is misaligned are REFUSED and logged (E1-6e). Nothing moves.
"""
from __future__ import annotations

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

from rubiknetic.cube_logic.geometric import HOME_POSITIONS
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES
from rubiknetic.cube_logic.observe import nearest_lattice_rotation
from rubiknetic.cube_physics.m1_model import cubie_name
from rubiknetic.cube_physics.readout import CubeReadout
from rubiknetic.cube_physics.rig import AuditedSim, EditAuditError

from m2_model import weld_name

TOL_UNLOCK_DEG = 1.0  # was 2.5: relocking up to 2 deg off froze misalignment into the shell -> later jams
TOL_LOCK_DEG = 0.5    # was 2.0
TAU_UNLOCK = 0.05     # N m
TAU_RELOCK = 0.02     # N m
GRIP_MIN_N = 2.0
OMEGA_RELOCK = 0.05   # rad/s (relock only near rest; 0.5 caused relock-while-moving + immediate re-unlock)
CHECK_EVERY = 4       # steps


def _rot_err_deg(R: np.ndarray) -> float:
    L = nearest_lattice_rotation(R)
    c = (np.trace(L.T @ R) - 1) / 2
    return float(np.degrees(np.arccos(np.clip(c, -1, 1))))


class SwitchAuditedSim(AuditedSim):
    def __init__(self, model, data=None, allow_test_wrench=False):
        super().__init__(model, data, allow_test_wrench)
        self._eqdata_snap = np.array(model.eq_data, copy=True)
        self.manager = None
        self.switch_log: list[dict] = []

    def step(self, n: int = 1) -> None:
        for _ in range(n):
            if not np.array_equal(self._eqdata_snap, self.m.eq_data):
                msg = f"mjModel.eq_data modified outside the switch manager before step {self.steps}"
                self.violations.append(msg)
                raise EditAuditError(msg)
            super().step(1)

    def apply_switch(self, caller, deactivate: list[int], activate: list[tuple[int, np.ndarray]], entry: dict) -> None:
        if caller is not self.manager or self.manager is None:
            msg = "eq switch requested by an unregistered caller"
            self.violations.append(msg)
            raise EditAuditError(msg)
        for eid in deactivate:
            self.d.eq_active[eid] = 0
        for eid, data in activate:
            self.m.eq_data[eid] = data
            self.d.eq_active[eid] = 1
        if self._snap is not None:
            self._snap["eq_active"] = np.array(self.d.eq_active, copy=True)
        self._eqdata_snap = np.array(self.m.eq_data, copy=True)
        self.switch_log.append(entry)


class SwitchManager:
    def __init__(self, sim: SwitchAuditedSim, pitch: float = 0.019):
        self.sim, self.m = sim, sim.m
        m = sim.m
        self.ro = CubeReadout(m, pitch)
        sim.manager = self
        sim.hooks.append(self)
        self.eq = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_EQUALITY, n)  # noqa: E731
        self.bid = {cubie_name(h): mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, cubie_name(h)) for h in HOME_POSITIONS}
        self.core = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "core")
        self.centre_of = {f: cubie_name(tuple(int(x) for x in FACE_NORMAL[f])) for f in FACES}
        self.hinge = {f: m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, self.centre_of[f] + "_j")] for f in FACES}
        self.hinge_v = {f: m.jnt_dofadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, self.centre_of[f] + "_j")] for f in FACES}
        self.pads = {f: {mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, f"pad_{f}{s}_g") for s in "ab"} for f in FACES}
        self.cubie_geom_body = {int(g): int(m.geom_bodyid[g]) for g in self.ro.geom_ids}
        self.movable = [cubie_name(h) for h in HOME_POSITIONS if sum(map(abs, h)) >= 2]
        self.unlocked: str | None = None
        self.members: list[str] = []
        self.refusing = False
        self.pending: dict | None = None
        self.k = 0
        self._f6 = np.zeros(6)

    # ----------------------------------------------------------------- physical measurements
    def pad_torque(self, d, face: str) -> tuple[float, float]:
        n = np.array(FACE_NORMAL[face], float)
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
            f = sign * (c.frame.reshape(3, 3).T @ self._f6[:3])  # force on the cubie
            tau += float(np.cross(c.pos, f) @ n)
            grip += abs(self._f6[0])
        return tau, grip

    def cube_ke(self, d) -> float:
        res = np.zeros(6)
        ke = 0.0
        for b in self.bid.values():
            mujoco.mj_objectVelocity(self.m, d, mujoco.mjtObj.mjOBJ_BODY, b, res, 0)
            w, v = res[:3], res[3:]
            vc = v + np.cross(w, d.xipos[b] - d.xpos[b])
            Ri = d.ximat[b].reshape(3, 3)
            Iw = Ri @ np.diag(self.m.body_inertia[b]) @ Ri.T
            ke += 0.5 * self.m.body_mass[b] * vc @ vc + 0.5 * w @ Iw @ w
        return float(ke)

    def _relpose(self, d, b1: int, b2: int) -> np.ndarray:
        R1, p1 = d.xmat[b1].reshape(3, 3), d.xpos[b1]
        R2, p2 = d.xmat[b2].reshape(3, 3), d.xpos[b2]
        x, y, z, w = Rotation.from_matrix(R1.T @ R2).as_quat()
        out = np.zeros(self.m.eq_data.shape[1])
        out[3:6] = R1.T @ (p2 - p1)
        out[6:10] = [w, x, y, z]
        out[10] = 1.0  # torquescale
        return out

    def _penetration(self, d) -> float:
        return max(0.0, -float(d.contact.dist[:d.ncon].min())) * 1000 if d.ncon else 0.0

    # ----------------------------------------------------------------- the rule
    def __call__(self, d) -> None:
        self.k += 1
        if self.pending is not None:  # finish logging the previous switch one check later
            e = self.pending
            e["ke_after"] = self.cube_ke(d)
            e["dke"] = e["ke_after"] - e["ke_before"]
            rows = [i for i in range(d.nefc) if d.efc_type[i] == mujoco.mjtConstraint.mjCNSTR_EQUALITY
                    and d.efc_id[i] in e["activated_ids"]]
            e["impulse_proxy_Ns"] = float(np.abs(d.efc_force[rows]).sum() * self.m.opt.timestep) if rows else 0.0
            e["pos_err_post_mm"] = float(np.abs(d.efc_pos[rows]).max() * 1000) if rows else 0.0
            self.pending = None
        if self.k % CHECK_EVERY:
            return
        pos, rot = self.ro.poses(d)
        if self.unlocked is None:
            req = {f: self.pad_torque(d, f) for f in FACES}
            active = [f for f, (tau, grip) in req.items() if grip > GRIP_MIN_N and abs(tau) > TAU_UNLOCK]
            if not active:
                self.refusing = False
                return
            aligned = all(_rot_err_deg(rot[i]) <= TOL_UNLOCK_DEG and np.abs(pos[i] - np.rint(pos[i])).max() < 0.15
                          for i in range(26) if sum(map(abs, HOME_POSITIONS[i])) >= 2)
            if len(active) > 1 or not aligned:
                if not self.refusing:
                    reason = "multiple faces" if len(active) > 1 else "cube misaligned"
                    self.sim.switch_log.append({"t": float(d.time), "kind": "refuse", "faces": active, "reason": reason})
                    self.refusing = True
                return
            self._unlock(d, active[0], req[active[0]][0], pos)
        else:
            f = self.unlocked
            # requests on OTHER faces while a layer is unlocked are refused (logged once per episode)
            others = [g for g in FACES if g != f]
            req = {g: self.pad_torque(d, g) for g in others}
            other_active = [g for g, (tau, grip) in req.items() if grip > GRIP_MIN_N and abs(tau) > TAU_UNLOCK]
            if other_active and not self.refusing:
                self.sim.switch_log.append({"t": float(d.time), "kind": "refuse", "faces": other_active,
                                            "reason": f"layer {f} still unlocked"})
                self.refusing = True
            elif not other_active:
                self.refusing = False
            ang = np.degrees(d.qpos[self.hinge[f]])
            off = abs(ang - 90 * round(ang / 90))
            moved = abs(ang - self.unlock_angle) > 45.0 or d.time - self.unlock_time > 1.0
            if not moved or off > TOL_LOCK_DEG or abs(d.qvel[self.hinge_v[f]]) > OMEGA_RELOCK:
                return
            if abs(self.pad_torque(d, f)[0]) >= TAU_RELOCK:
                return
            idx = {cubie_name(h): i for i, h in enumerate(HOME_POSITIONS)}
            if any(_rot_err_deg(rot[idx[b]]) > TOL_LOCK_DEG for b in self.members):
                return
            self._relock(d, f, off)

    def _unlock(self, d, f: str, tau: float, pos) -> None:
        n = np.array(FACE_NORMAL[f], float)
        idx = {cubie_name(h): i for i, h in enumerate(HOME_POSITIONS)}
        members = [b for b in self.movable if pos[idx[b]] @ n > 0.5]
        cen = self.centre_of[f]
        deact = [self.eq(weld_name(b, "core")) for b in members] + [self.eq(weld_name(cen, "core"))]
        act = [(self.eq(weld_name(b, cen)), self._relpose(d, self.bid[b], self.bid[cen])) for b in members]
        entry = {"t": float(d.time), "kind": "unlock", "face": f, "members": len(members), "pad_torque_Nm": tau,
                 "rel_speed_rad_s": float(d.qvel[self.hinge_v[f]]), "pos_err_pre_mm": 0.0,
                 "ke_before": self.cube_ke(d), "penetration_mm": self._penetration(d),
                 "activated_ids": [e for e, _ in act]}
        self.sim.apply_switch(self, deact, act, entry)
        self.unlocked, self.members, self.pending = f, members, entry
        self.unlock_angle = float(np.degrees(d.qpos[self.hinge[f]]))
        self.unlock_time = float(d.time)

    def _relock(self, d, f: str, off_deg: float) -> None:
        cen = self.centre_of[f]
        deact = [self.eq(weld_name(b, cen)) for b in self.members]
        act = [(self.eq(weld_name(b, "core")), self._relpose(d, self.bid[b], self.core)) for b in self.members]
        act.append((self.eq(weld_name(cen, "core")), self._relpose(d, self.bid[cen], self.core)))
        entry = {"t": float(d.time), "kind": "relock", "face": f, "members": len(self.members),
                 "hinge_off_square_deg": off_deg, "rel_speed_rad_s": float(d.qvel[self.hinge_v[f]]),
                 "pos_err_pre_mm": 0.0, "ke_before": self.cube_ke(d), "penetration_mm": self._penetration(d),
                 "activated_ids": [e for e, _ in act]}
        self.sim.apply_switch(self, deact, act, entry)
        self.unlocked, self.members, self.pending = None, [], entry
