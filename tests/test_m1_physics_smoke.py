"""Fast physics smoke tests for the M1 model and the audit harness.

These check plumbing and categorical behaviour only; they are NOT the scored
G1 experiments (those need pre-registered thresholds; see
docs/research/PHASE_1_2_VALIDATION_EXPERIMENTS.md).
"""

from __future__ import annotations

import mujoco
import numpy as np
import pytest

from rubiknetic.cube_logic import SOLVED, Move
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml
from rubiknetic.cube_physics.readout import CubeReadout
from rubiknetic.cube_physics.rig import AuditedSim, EditAuditError, TurnRig


@pytest.fixture(scope="module")
def model():
    p = M1Params()
    return p, mujoco.MjModel.from_xml_string(build_m1_xml(p))


def _setup(model):
    p, m = model
    sim = AuditedSim(m)
    ro = CubeReadout(m, p.pitch)
    rig = TurnRig(sim, pad_close_target=-(p.pad_open_clearance + p.grip_overshoot))
    sim.step(400)
    return p, sim, ro, rig


def test_model_structure(model):
    _, m = model
    # 6 centre hinges + 20 ball joints (3 dof) + 20 radial slides + 6 turner hinges + 12 pad slides
    assert m.nv == 6 + 60 + 20 + 6 + 12
    assert m.nu == 18
    assert m.neq == 0  # M1 has no equality constraints at all: nothing to switch


def test_settled_cube_reads_solved(model):
    _, sim, ro, _ = _setup(model)
    o = ro.observe(sim.d)
    assert o.valid and o.state == SOLVED


def test_turner_without_contact_does_not_move_cube(model):
    """E1-6(a) categorical: an actuator command without contact causes no turn."""
    _, sim, ro, rig = _setup(model)
    _, r0 = ro.poses(sim.d)
    mem = ro.layer_members(sim.d, "U")
    rig.rotate({"U": -np.pi / 2}, grip=False)
    _, r1 = ro.poses(sim.d)
    assert np.max(np.abs(ro.rotation_about_deg(r0, r1, mem, "U"))) < 0.5
    assert ro.observe(sim.d).state == SOLVED


def test_contact_driven_quarter_turn_matches_oracle(model):
    _, sim, ro, rig = _setup(model)
    rig.turn(Move("U", 1))
    o = ro.observe(sim.d)
    assert o.valid, o.problems
    assert o.state == SOLVED.apply(Move("U", 1))
    assert sim.violations == [] and sim.numerical_failures == []


def test_edit_audit_detects_state_write(model):
    _, sim, _, _ = _setup(model)
    sim.d.qpos[0] += 1e-6  # a forbidden write between steps
    with pytest.raises(EditAuditError):
        sim.step()
