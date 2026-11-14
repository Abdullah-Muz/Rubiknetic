"""M2 switch manager, and the audited simulator that permits ONLY its writes
(experiments/PHASE_1_M2_PREREGISTRATION.md, sections 1–2).

**Audit exception** (validation protocol, rule 2: "approved, logged mechanism ... M2 switching rule"):

* ``SwitchAuditedSim`` extends ``AuditedSim`` and also snapshots ``mjModel.eq_data`` (weld relposes) between steps.
* The registered ``SwitchManager`` is the only caller allowed to change ``d.eq_active`` or ``m.eq_data``, through
  ``apply_switch``, and every call is logged.
* The only other permitted write is the logged episode setup (``setup_reanchor``) before the first step.
* Any other change to those arrays, or to qpos, qvel, act, xfrc, qfrc or mocap, raises ``EditAuditError``.

**Switch rule.** It uses ONLY physical state: poses, velocities, and the contact forces the grippers apply to the
cubies, read as a sensor. It never uses the commanded move or the oracle.

* **Unlock** face F when no layer is unlocked and all of these hold:
  * every non-centre cubie is within ``tol_unlock_deg`` of a lattice rotation and within ``pos_tol_pitch`` of a
    lattice position;
  * F's own pads grip with a pad-to-cubie normal force above ``grip_min_n`` (unchanged; stabilisers and other
    face-less gripper geoms add shear but never grant a face's grip);
  * **shear-dominance (Amendment 1, A2):** F's boundary shear exceeds ``tau_unlock`` and is at least
    ``dominance`` (1.5) times the next face's. The boundary shear is the torque about F's axis, in the CORE frame,
    that ALL gripper contacts (``pad_*`` and ``stab_*`` geoms, plus registered gripper geoms) apply to the cubies
    currently in F's layer.

  If no face dominates, every face above threshold requests, so the cube refuses: the loads are ambiguous, for
  example equal opposed torques (E1-6b) or a one-layer hold. Refusal episodes are logged once each. Requests while the cube is misaligned, or while another layer is
  unlocked, are refused and logged. Nothing moves.
* **Relock** when the centre hinge is within ``tol_lock_deg`` of a multiple of 90°, every layer cubie is within
  ``tol_lock_cubie_deg`` (Amendment 2, B1), the absolute boundary shear is below ``tau_relock`` and the absolute hinge speed is below
  ``omega_relock``. The layer must also have moved more than ``min_move_deg`` or ``min_unlocked_s`` must have passed.
* **Every activation** re-anchors the weld at the CURRENT relative pose. It never snaps to an exact lattice pose.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

from rubiknetic.cube_logic.geometric import HOME_POSITIONS
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES
from rubiknetic.cube_logic.observe import nearest_lattice_rotation

from .m1_model import cubie_name
from .m2_model import CENTRES, MOVABLE, weld_name
from .readout import CubeReadout
from .rig import AuditedSim, EditAuditError


@dataclass(frozen=True)
class SwitchRule:
    """Frozen switch-rule constants (pre-registration section 1)."""

    tol_unlock_deg: float = 1.0
    pos_tol_pitch: float = 0.15
    grip_min_n: float = 2.0
    tau_unlock: float = 0.05      # N m
    tol_lock_deg: float = 0.5          # centre-hinge relock tolerance (unchanged)
    tol_lock_cubie_deg: float = 0.5    # Amendment 2: B1 (1.0) failed its smoke condition -> fallback keeps 0.5
    tau_relock: float = 0.02      # N m
    omega_relock: float = 0.05    # rad/s
    min_move_deg: float = 45.0
    min_unlocked_s: float = 1.0
    check_every: int = 4          # steps between rule evaluations
    dominance: float = 1.5        # Amendment 1 (A2): a face requests only if |shear| >= dominance x next face


def rot_err_deg(R: np.ndarray) -> float:
    """Angle (deg) between rotation R and the nearest of the 24 lattice rotations."""
    L = nearest_lattice_rotation(R)
    c = (np.trace(L.T @ R) - 1) / 2
    return float(np.degrees(np.arccos(np.clip(c, -1, 1))))


class SwitchAuditedSim(AuditedSim):
    def __init__(self, model, data=None, allow_test_wrench: bool = False):
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
        if self.manager is None or caller is not self.manager:
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

    def setup_reanchor(self, caller, writes: list[tuple[int, np.ndarray]]) -> None:
        """Episode setup only (before the first step): re-anchor active welds at the setup pose."""
        if self.manager is None or caller is not self.manager:
            msg = "eq setup write by an unregistered caller"
            self.violations.append(msg)
            raise EditAuditError(msg)
        self.log_setup({"type": "weld_reanchor_at_setup_pose", "n_welds": len(writes)})  # raises after step 1
        for eid, data in writes:
            self.m.eq_data[eid] = data
        self._eqdata_snap = np.array(self.m.eq_data, copy=True)


class SwitchManager:
    def __init__(self, sim: SwitchAuditedSim, pitch: float = 0.019, rule: SwitchRule | None = None):
        self.sim, self.m = sim, sim.m
        self.rule = rule or SwitchRule()
        m = sim.m
        self.ro = CubeReadout(m, pitch)
        sim.manager = self
        sim.hooks.append(self)
        self.eq = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_EQUALITY, n)  # noqa: E731
        self.bid = {cubie_name(h): mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, cubie_name(h)) for h in HOME_POSITIONS}
        self.core = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "core")
        self.centre_of = {f: cubie_name(tuple(int(x) for x in FACE_NORMAL[f])) for f in FACES}
        jid = {f: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, self.centre_of[f] + "_j") for f in FACES}
        self.hinge = {f: m.jnt_qposadr[jid[f]] for f in FACES}
        self.hinge_v = {f: m.jnt_dofadr[jid[f]] for f in FACES}
        self.pads = {f: {mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, f"pad_{f}{s}_g") for s in "ab"} - {-1}
                     for f in FACES}
        self.cubie_geom_body = {int(g): int(m.geom_bodyid[g]) for g in self.ro.geom_ids}
        # Amendment 1 (A2): every gripper contact counts (rig pads, stabilisers, later robot fingertips).
        names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, g) or "" for g in range(m.ngeom)]
        self.gripper_geoms = {g for g, n in enumerate(names) if n.startswith(("pad_", "stab_"))}
        self.body_to_idx = {int(self.ro.body_ids[i]): i for i in range(26)}
        self._shear_cache: tuple = (None, None)
        self.movable = [cubie_name(h) for h in MOVABLE]
        self.idx = {cubie_name(h): i for i, h in enumerate(HOME_POSITIONS)}
        self.unlocked: str | None = None
        self.members: list[str] = []
        self.refusing = False
        self.pending: dict | None = None
        self.k = 0
        self.unlock_angle = 0.0
        self.unlock_time = 0.0
        self._f6 = np.zeros(6)

    # ----------------------------------------------------------------- physical measurements
    def pad_torque(self, d, face: str) -> tuple[float, float]:
        """DIAGNOSTIC ONLY since Amendment 1 (the rule uses ``request_torques``/``shears``): torque about the world
        face axis applied by that face's own rig pads, and their total normal force."""
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

    def register_gripper_geoms(self, geom_ids) -> None:
        """Add gripper geoms whose names do not start with ``pad_``/``stab_`` (e.g. robot fingertips)."""
        self.gripper_geoms |= {int(g) for g in geom_ids}
        self._shear_cache = (None, None)

    def shears(self, d) -> dict[str, tuple[float, float]]:
        """Amendment 1 (A2). For each face F: (boundary shear, grip). The shear is the torque about F's axis IN THE
        CORE FRAME (lever arm from the core position, axis = core rotation x face normal) that ALL gripper contacts
        apply to the cubies currently in F's layer (membership by measured position in the core frame). Grip is
        UNCHANGED from section 1 (A2 keeps every other condition): the normal force of F's OWN pads on the cubies.
        Gripper geoms without a face (stabilisers, later fingertips) add shear but never grant a face's grip.
        Physical state only."""
        key = (float(d.time), int(d.ncon))
        if self._shear_cache[0] == key:
            return self._shear_cache[1]
        Rc, pc = d.xmat[self.core].reshape(3, 3), d.xpos[self.core]
        pos, _ = self.ro.poses(d)
        contacts = []
        for i in range(d.ncon):
            c = d.contact[i]
            g1, g2 = int(c.geom1), int(c.geom2)
            if g1 in self.gripper_geoms and g2 in self.cubie_geom_body:
                sign, cg = 1.0, g2
            elif g2 in self.gripper_geoms and g1 in self.cubie_geom_body:
                sign, cg = -1.0, g1
            else:
                continue
            mujoco.mj_contactForce(self.m, d, i, self._f6)
            f = sign * (c.frame.reshape(3, 3).T @ self._f6[:3])  # force on the cubie
            pad = g1 if sign > 0 else g2
            contacts.append((self.body_to_idx[self.cubie_geom_body[cg]], c.pos - pc, f, abs(self._f6[0]), pad))
        out = {}
        for F in FACES:
            nF = np.array(FACE_NORMAL[F], float)
            n = Rc @ nF
            members = {i for i in range(26) if pos[i] @ nF > 0.5}
            tau = sum(float(np.cross(r, f) @ n) for i, r, f, _, _ in contacts if i in members)
            grip = sum(g for _, _, _, g, pad in contacts if pad in self.pads[F])
            out[F] = (tau, grip)
        self._shear_cache = (key, out)
        return out

    def request_torques(self, d) -> tuple[dict[str, tuple[float, float]], bool]:
        """Shear-dominance request (A2). Returns ({face: (torque, grip)}, ambiguous). If the largest |shear| is at
        least ``tau_unlock`` and at least ``dominance`` x the next, only that face keeps its torque (the others are
        zeroed). Otherwise every face keeps its shear, so several faces above threshold request at once and the
        rule refuses (ambiguous loads)."""
        sh = self.shears(d)
        mags = sorted(((abs(t), F) for F, (t, _) in sh.items()), reverse=True)
        (m1, f1), (m2, _) = mags[0], mags[1]
        if m1 >= self.rule.tau_unlock and m1 >= self.rule.dominance * m2:
            return {F: ((t, g) if F == f1 else (0.0, g)) for F, (t, g) in sh.items()}, False
        return dict(sh), m1 >= self.rule.tau_unlock

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

    def relpose(self, d, b1: int, b2: int) -> np.ndarray:
        """eq_data row placing body2 at its CURRENT pose relative to body1 (verified convention:
        eq_data[3:6] = body2 origin in body1 frame, [6:10] = quat of body2 relative to body1, [10] = torquescale)."""
        R1, p1 = d.xmat[b1].reshape(3, 3), d.xpos[b1]
        R2, p2 = d.xmat[b2].reshape(3, 3), d.xpos[b2]
        x, y, z, w = Rotation.from_matrix(R1.T @ R2).as_quat()
        out = np.zeros(self.m.eq_data.shape[1])
        out[3:6] = R1.T @ (p2 - p1)
        out[6:10] = [w, x, y, z]
        out[10] = 1.0
        return out

    def max_misalignment_deg(self, d) -> float:
        _, rot = self.ro.poses(d)
        return max(rot_err_deg(rot[self.idx[b]]) for b in self.movable)

    def _penetration(self, d) -> float:
        return max(0.0, -float(d.contact.dist[:d.ncon].min())) * 1000 if d.ncon else 0.0

    # ----------------------------------------------------------------- episode setup
    def setup_reanchor(self, d) -> None:
        """Logged episode-setup action before t = 0: re-anchor every ACTIVE weld at the current (setup) pose so the
        locked shell holds the pre-registered setup misalignment instead of pulling it back."""
        mujoco.mj_kinematics(self.m, d)
        writes = []
        for b in self.movable:
            writes.append((self.eq(weld_name(b, "core")), self.relpose(d, self.bid[b], self.core)))
        for c in CENTRES:
            cn = cubie_name(c)
            writes.append((self.eq(weld_name(cn, "core")), self.relpose(d, self.bid[cn], self.core)))
        self.sim.setup_reanchor(self, writes)

    # ----------------------------------------------------------------- the rule
    def __call__(self, d) -> None:
        r = self.rule
        self.k += 1
        if self.pending is not None:  # complete the previous switch's log on the next step
            e = self.pending
            e["ke_after"] = self.cube_ke(d)
            e["dke"] = e["ke_after"] - e["ke_before"]
            rows = [i for i in range(d.nefc) if d.efc_type[i] == mujoco.mjtConstraint.mjCNSTR_EQUALITY
                    and d.efc_id[i] in e["activated_ids"]]
            e["impulse_proxy_Ns"] = float(np.abs(d.efc_force[rows]).sum() * self.m.opt.timestep) if rows else 0.0
            # A weld contributes 6 consecutive rows: 3 translational residuals (m), then 3 rotational residuals (rad).
            pos_rows, rot_rows = [], []
            for eid in e["activated_ids"]:
                er = [i for i in rows if d.efc_id[i] == eid]
                pos_rows += er[:3]
                rot_rows += er[3:6]
            e["pos_err_post_mm"] = float(np.abs(d.efc_pos[pos_rows]).max() * 1000) if pos_rows else 0.0
            e["rot_err_post_deg"] = float(np.degrees(np.abs(d.efc_pos[rot_rows]).max())) if rot_rows else 0.0
            self.pending = None
        if self.k % r.check_every:
            return
        pos, rot = self.ro.poses(d)
        if self.unlocked is None:
            req, ambiguous = self.request_torques(d)
            active = [f for f, (tau, grip) in req.items() if grip > r.grip_min_n and abs(tau) > r.tau_unlock]
            if not active:
                self.refusing = False
                return
            mis = max(rot_err_deg(rot[self.idx[b]]) for b in self.movable)
            posdev = max(float(np.abs(pos[self.idx[b]] - np.rint(pos[self.idx[b]])).max()) for b in self.movable)
            aligned = mis <= r.tol_unlock_deg and posdev < r.pos_tol_pitch
            if len(active) > 1 or not aligned:
                if not self.refusing:  # rate limit: one log entry per refusal episode
                    reason = "multiple faces" if len(active) > 1 else "cube misaligned"
                    self.sim.switch_log.append({"t": float(d.time), "kind": "refuse", "faces": active, "reason": reason,
                                                "ambiguous_loads": bool(ambiguous and len(active) > 1),
                                                "shears_Nm": {F: float(t) for F, (t, _) in self.shears(d).items()},
                                                "max_misalignment_deg": mis, "max_pos_dev_pitch": posdev})
                    self.refusing = True
                return
            self._unlock(d, active[0], req[active[0]][0], pos, mis)
        else:
            f = self.unlocked
            others = [g for g in FACES if g != f]
            req_all, _ = self.request_torques(d)
            req = {g: req_all[g] for g in others}
            other_active = [g for g, (tau, grip) in req.items() if grip > r.grip_min_n and abs(tau) > r.tau_unlock]
            if other_active and not self.refusing:
                self.sim.switch_log.append({"t": float(d.time), "kind": "refuse", "faces": other_active,
                                            "reason": f"layer {f} still unlocked"})
                self.refusing = True
            elif not other_active:
                self.refusing = False
            ang = np.degrees(d.qpos[self.hinge[f]])
            off = abs(ang - 90 * round(ang / 90))
            moved = abs(ang - self.unlock_angle) > r.min_move_deg or d.time - self.unlock_time > r.min_unlocked_s
            if not moved or off > r.tol_lock_deg or abs(d.qvel[self.hinge_v[f]]) > r.omega_relock:
                return
            if abs(self.shears(d)[f][0]) >= r.tau_relock:  # A2: boundary shear of the unlocked face
                return
            member_err = max(rot_err_deg(rot[self.idx[b]]) for b in self.members)
            if member_err > r.tol_lock_cubie_deg:  # Amendment 2 (B1)
                return
            self._relock(d, f, off, member_err)

    def _unlock(self, d, f: str, tau: float, pos, mis: float) -> None:
        n = np.array(FACE_NORMAL[f], float)
        members = [b for b in self.movable if pos[self.idx[b]] @ n > 0.5]
        cen = self.centre_of[f]
        deact = [self.eq(weld_name(b, "core")) for b in members] + [self.eq(weld_name(cen, "core"))]
        act = [(self.eq(weld_name(b, cen)), self.relpose(d, self.bid[b], self.bid[cen])) for b in members]
        entry = {"t": float(d.time), "kind": "unlock", "face": f, "members": len(members), "pad_torque_Nm": tau,
                 "max_misalignment_deg": mis, "rel_speed_rad_s": float(d.qvel[self.hinge_v[f]]),
                 "pos_err_pre_mm": 0.0, "ke_before": self.cube_ke(d), "penetration_mm": self._penetration(d),
                 "activated_ids": [e for e, _ in act]}
        self.sim.apply_switch(self, deact, act, entry)
        self.unlocked, self.members, self.pending = f, members, entry
        self.unlock_angle = float(np.degrees(d.qpos[self.hinge[f]]))
        self.unlock_time = float(d.time)

    def _relock(self, d, f: str, off_deg: float, member_err: float) -> None:
        cen = self.centre_of[f]
        deact = [self.eq(weld_name(b, cen)) for b in self.members]
        act = [(self.eq(weld_name(b, "core")), self.relpose(d, self.bid[b], self.core)) for b in self.members]
        act.append((self.eq(weld_name(cen, "core")), self.relpose(d, self.bid[cen], self.core)))
        entry = {"t": float(d.time), "kind": "relock", "face": f, "members": len(self.members),
                 "hinge_off_square_deg": off_deg, "max_misalignment_deg": member_err,
                 "rel_speed_rad_s": float(d.qvel[self.hinge_v[f]]), "pos_err_pre_mm": 0.0,
                 "ke_before": self.cube_ke(d), "penetration_mm": self._penetration(d),
                 "activated_ids": [e for e, _ in act]}
        self.sim.apply_switch(self, deact, act, entry)
        self.unlocked, self.members, self.pending = None, [], entry

    # ----------------------------------------------------------------- E1-1 topology check
    def weld_topology_consistent(self, d) -> tuple[bool, list[str]]:
        """Active weld set vs the topology implied by measured poses: each non-centre cubie has exactly one active
        anchor weld. That anchor is the unlocked face's centre if the cubie lies in that layer, otherwise the core.
        Each centre is welded to the core unless it is the unlocked face."""
        pos, _ = self.ro.poses(d)
        problems = []
        anchors = ["core"] + [cubie_name(c) for c in CENTRES]
        for b in self.movable:
            act = [a for a in anchors if d.eq_active[self.eq(weld_name(b, a))]]
            if len(act) != 1:
                problems.append(f"{b}: {len(act)} active anchors {act}")
                continue
            in_unlocked = self.unlocked is not None and pos[self.idx[b]] @ np.array(FACE_NORMAL[self.unlocked]) > 0.5
            want = self.centre_of[self.unlocked] if in_unlocked else "core"
            if act[0] != want:
                problems.append(f"{b}: anchored to {act[0]}, poses imply {want}")
        for f in FACES:
            cen = self.centre_of[f]
            on = bool(d.eq_active[self.eq(weld_name(cen, "core"))])
            if on == (f == self.unlocked):
                problems.append(f"{cen}: core weld {'on' if on else 'off'} with unlocked={self.unlocked}")
        return (not problems), problems

    def rule_dict(self) -> dict:
        return asdict(self.rule)
