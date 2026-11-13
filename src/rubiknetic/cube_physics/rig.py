"""Phase 1 test rig driver: commands *actuators only* and audits that nothing
else touches the simulation state.

``AuditedSim.step`` snapshots every state array a harness could abuse
(qpos, qvel, act, eq_active, xfrc_applied, qfrc_applied, mocap_pos/quat)
after each ``mj_step`` and verifies they are unchanged when the next step
begins. Any discrepancy is an **edit-audit violation** (VALIDATION_PLAN:
"No target-angle setter, teleportation ...").
"""

from __future__ import annotations

from dataclasses import dataclass, field

import mujoco
import numpy as np

from rubiknetic.cube_logic import Move

_AUDITED = ("qpos", "qvel", "act", "eq_active", "xfrc_applied", "qfrc_applied", "mocap_pos", "mocap_quat")
# MuJoCo warnings that invalidate a trial. mjWARN_BADQACC triggers an automatic
# mj_resetData inside mj_step, which would silently restore the solved cube.
_FATAL_WARNINGS = (mujoco.mjtWarning.mjWARN_BADQACC, mujoco.mjtWarning.mjWARN_BADQPOS,
                   mujoco.mjtWarning.mjWARN_BADQVEL, mujoco.mjtWarning.mjWARN_BADCTRL)


class EditAuditError(RuntimeError):
    pass


class NumericalFailure(RuntimeError):
    """Simulation diverged (and MuJoCo reset the state). The trial is void."""


class AuditedSim:
    """Steps MuJoCo and audits state integrity.

    ``setup_log`` records every *episode-setup* write made before the first step
    (allowed, logged). ``allow_test_wrench`` enables the single approved exception
    to the audit (P-12, E1-6c negative control only): ``set_test_wrench`` writes
    ``xfrc_applied`` and logs it. ``hooks`` are read-only monitors called after
    every step."""

    def __init__(self, model: mujoco.MjModel, data: mujoco.MjData | None = None,
                 allow_test_wrench: bool = False):
        self.m = model
        self.d = data if data is not None else mujoco.MjData(model)
        self._snap: dict[str, np.ndarray] | None = None
        self.steps = 0
        self.violations: list[str] = []
        self.numerical_failures: list[str] = []
        self.setup_log: list[dict] = []
        self.wrench_log: list[dict] = []
        self.allow_test_wrench = allow_test_wrench
        self.hooks: list = []

    def log_setup(self, entry: dict) -> None:
        if self.steps:
            raise EditAuditError("setup writes are only allowed before the first step")
        self.setup_log.append(entry)

    def set_test_wrench(self, body_id: int, wrench: np.ndarray) -> None:
        if not self.allow_test_wrench:
            msg = "test wrench requested but not permitted in this experiment"
            self.violations.append(msg)
            raise EditAuditError(msg)
        self.d.xfrc_applied[body_id] = wrench
        if self._snap is not None:
            self._snap["xfrc_applied"] = np.array(self.d.xfrc_applied, copy=True)
        self.wrench_log.append({"step": self.steps, "body": int(body_id), "wrench": [float(x) for x in wrench]})

    def _take(self) -> dict[str, np.ndarray]:
        return {k: np.array(getattr(self.d, k), copy=True) for k in _AUDITED}

    def step(self, n: int = 1) -> None:
        for _ in range(n):
            if self._snap is not None:
                for k, v in self._snap.items():
                    if not np.array_equal(v, getattr(self.d, k)):
                        msg = f"state array '{k}' modified outside mj_step before step {self.steps}"
                        self.violations.append(msg)
                        raise EditAuditError(msg)
            mujoco.mj_step(self.m, self.d)
            self.steps += 1
            for w in _FATAL_WARNINGS:
                if self.d.warning[w].number:
                    msg = (f"{w.name} at t~{self.steps * self.m.opt.timestep:.4f}s step {self.steps} "
                           f"(dof {self.d.warning[w].lastinfo}); state was auto-reset by MuJoCo")
                    self.numerical_failures.append(msg)
                    raise NumericalFailure(msg)
            self._snap = self._take()
            for h in self.hooks:
                h(self.d)


@dataclass
class TurnTiming:
    close_s: float = 0.3
    turn_s_per_quarter: float = 1.0
    hold_s: float = 0.3
    open_s: float = 0.3
    settle_s: float = 0.3


@dataclass
class TurnLog:
    move: str
    t: list[float] = field(default_factory=list)
    turner_angle_deg: list[float] = field(default_factory=list)
    turner_torque: list[float] = field(default_factory=list)
    ncon: list[int] = field(default_factory=list)
    min_contact_dist_mm: list[float] = field(default_factory=list)


class TurnRig:
    """Drives the six face turners of the M1 rig through their actuators."""

    def __init__(self, sim: AuditedSim, pad_close_target: float = -0.012):
        self.sim = sim
        m = sim.m
        aid = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, n)  # noqa: E731
        jid = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n)  # noqa: E731
        self.act = {f: (aid(f"grip_{f}a"), aid(f"grip_{f}b"), aid(f"turn_{f}")) for f in "URFDLB"}
        self.hinge_qadr = {f: m.jnt_qposadr[jid(f"turner_{f}_hinge")] for f in "URFDLB"}
        self.close_target = pad_close_target
        self.target = {f: 0.0 for f in "URFDLB"}  # commanded turner angle (rad)

    def _hold_others(self) -> None:
        d = self.sim.d
        for f, (_, _, t) in self.act.items():
            d.ctrl[t] = self.target[f]

    def _run(self, seconds: float, log: TurnLog | None, face: str) -> None:
        m, d = self.sim.m, self.sim.d
        n = max(1, int(round(seconds / m.opt.timestep)))
        for _ in range(n):
            self.sim.step()
            if log is not None:
                log.t.append(float(d.time))
                log.turner_angle_deg.append(float(np.degrees(d.qpos[self.hinge_qadr[face]])))
                log.turner_torque.append(float(d.actuator_force[self.act[face][2]]))
                log.ncon.append(int(d.ncon))
                log.min_contact_dist_mm.append(
                    float(d.contact.dist[: d.ncon].min() * 1000) if d.ncon else 0.0
                )

    def rotate(
        self,
        deltas: dict[str, float],
        grip: bool = True,
        timing: TurnTiming | None = None,
        record: bool = True,
        release: bool = True,
    ) -> TurnLog:
        """Rotate one or more turners by ``deltas`` (rad, right-hand about the face's
        outward normal), optionally gripping first. Several faces at once are used
        for jam negative controls. With ``grip=False`` the pads stay open, so the
        cube should not move (negative control E1-6a)."""
        tm = timing or TurnTiming()
        d = self.sim.d
        faces = list(deltas)
        log = TurnLog(",".join(f"{f}:{np.degrees(v):+.1f}" for f, v in deltas.items())) if record else None
        start = {f: self.target[f] for f in faces}
        self._hold_others()
        if grip:
            for f in faces:
                d.ctrl[self.act[f][0]] = d.ctrl[self.act[f][1]] = self.close_target
            self._run(tm.close_s, log, faces[0])
        quarters = max(abs(v) for v in deltas.values()) / (np.pi / 2)
        n = max(1, int(round(tm.turn_s_per_quarter * quarters / self.sim.m.opt.timestep)))
        for k in range(1, n + 1):
            s = 0.5 - 0.5 * np.cos(np.pi * k / n)  # smooth ramp 0 -> 1
            for f in faces:
                self.target[f] = start[f] + s * deltas[f]
                d.ctrl[self.act[f][2]] = self.target[f]
            self._run(self.sim.m.opt.timestep, log, faces[0])
        self._run(tm.hold_s, log, faces[0])
        if release:
            for f in faces:
                d.ctrl[self.act[f][0]] = d.ctrl[self.act[f][1]] = 0.0
            self._run(tm.open_s, log, faces[0])
        self._run(tm.settle_s, log, faces[0])
        return log

    def turn(self, move: Move, timing: TurnTiming | None = None, record: bool = True) -> TurnLog:
        """Physically perform ``move``: close pads, rotate turner, open pads.

        The clockwise sign convention matches cube_logic: clockwise = negative
        rotation about the outward normal (turner frame z = outward normal)."""
        delta = -np.pi / 2 * {1: 1, 2: 2, 3: -1}[move.quarter_turns]
        log = self.rotate({move.face: delta}, grip=True, timing=timing, record=record)
        if log is not None:
            log.move = str(move)
        return log
