"""Tests for the scored G1 harness: frozen thresholds, setup logging, the
test-wrench exception, and injected-fault detection."""

from __future__ import annotations

import numpy as np
import pytest

from rubiknetic.cube_logic import Move
from rubiknetic.cube_physics import scored
from rubiknetic.cube_physics.rig import EditAuditError


def test_thresholds_match_preregistration():
    assert scored.THRESHOLDS == {
        "turn_error_deg": 2.0, "nontarget_drift_deg": 1.0, "penetration_mm": 0.5,
        "radial_offset_mm": 0.5, "radial_above_nominal_mm": 0.3, "rest_rotation_deg": 0.5,
        "open_pad_rotation_deg": 0.5, "opposed_radial_change_mm": 0.5, "causal_force_N": 0.5,
        "causal_speed_dps": 5.0, "observed_move_min_deg": 45.0,
    }


def test_setup_draw_is_seeded_and_in_range():
    a, b = scored.draw_setup(1000), scored.draw_setup(1000)
    assert a == b and a != scored.draw_setup(1001)
    assert all(abs(v) <= 1.0 for v in a.misalign_deg.values())
    assert 10.0 <= a.grip_force <= 20.0 and 0.8 <= a.turn_s_per_quarter <= 1.2


def test_setup_is_logged_and_forbidden_after_first_step():
    tr = scored.Trial(scored.params_for(None), scored.draw_setup(1000))
    assert len(tr.sim.setup_log) == 6
    with pytest.raises(EditAuditError):
        tr.sim.log_setup({"type": "late write"})


def test_test_wrench_refused_unless_enabled():
    tr = scored.Trial(scored.params_for(None), None)
    with pytest.raises(EditAuditError):
        tr.sim.set_test_wrench(int(tr.ro.body_ids[0]), np.ones(6))


def test_injected_state_write_is_caught_mid_trial():
    tr = scored.Trial(scored.params_for(None), None)
    tr.sim.d.qvel[3] += 0.1
    with pytest.raises(EditAuditError):
        tr.sim.step()


def test_scored_single_move_trial_passes_and_uses_observed_move():
    rec = scored.run_sequence_trial([Move("U", 1)], seed=999)  # seed outside the scored range
    m = rec["per_move"][0]
    assert m["observed_move"] == "U"
    assert rec["pass"], rec
