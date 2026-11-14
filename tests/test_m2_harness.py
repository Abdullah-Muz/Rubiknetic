"""Tests for the M2 scored harness (experiments/PHASE_1_M2_PREREGISTRATION.md section 6): frozen thresholds,
weld re-anchoring, the switch audit exception, refusal of misaligned switches, injected-fault detection, and an
unscored smoke trial (seed outside the scored range)."""

from __future__ import annotations

import mujoco
import numpy as np
import pytest

from rubiknetic.cube_logic import Move
from rubiknetic.cube_logic.notation import FACES
from rubiknetic.cube_physics import scored, scored_m2
from rubiknetic.cube_physics.m2_model import build_m2_xml, m2_params
from rubiknetic.cube_physics.rig import EditAuditError
from rubiknetic.cube_physics.switching import SwitchAuditedSim, SwitchManager, SwitchRule


def _env():
    p = m2_params()
    m = mujoco.MjModel.from_xml_string(build_m2_xml(p))
    sim = SwitchAuditedSim(m)
    mujoco.mj_forward(m, sim.d)
    mgr = SwitchManager(sim, p.pitch)
    return p, m, sim, mgr


def test_thresholds_match_preregistration():
    assert scored_m2.THRESHOLDS_M2 == {
        **scored.THRESHOLDS,
        "switch_dke_rel": 0.01, "switch_dke_abs_J": 1e-3, "switch_post_pos_err_mm": 0.01,
        "twist_max_deg": 2.0, "twist_penetration_mm": 0.5, "e16e_misalignment_deg": 5.0,
    }
    assert scored_m2.SCORED_SEED_RANGE == (3000, 3999)  # Amendment 4 (D2)


def test_switch_rule_matches_preregistration():
    r = SwitchRule()
    assert (r.tol_unlock_deg, r.pos_tol_pitch, r.grip_min_n, r.tau_unlock) == (1.0, 0.15, 2.0, 0.05)
    assert (r.tol_lock_deg, r.tau_relock, r.omega_relock, r.min_move_deg, r.min_unlocked_s) == (0.5, 0.02, 0.05, 45.0, 1.0)
    assert r.tol_lock_cubie_deg == 0.5  # Amendment 2: B1 conditional failed, fallback keeps per-cubie relock 0.5
    assert r.dominance == 1.5  # Amendment 1, A2


def test_setup_misalignment_amendment_a1():
    """A1: +/-0.5 deg per face, and the compound worst piece stays inside the 1.0 deg unlock tolerance for every
    scored seed (2000-2999)."""
    from scipy.spatial.transform import Rotation

    from rubiknetic.cube_logic import HOME_POSITIONS
    from rubiknetic.cube_logic.notation import FACE_NORMAL

    assert scored_m2.SETUP_MISALIGN_MAX_DEG == 0.25  # Amendment 2 fallback
    worst_all = 0.0
    lo, hi = scored_m2.SCORED_SEED_RANGE
    for seed in range(lo, hi + 1):
        s = scored_m2.draw_setup(seed)
        assert all(abs(v) <= scored_m2.SETUP_MISALIGN_MAX_DEG for v in s.misalign_deg.values())
        for h in HOME_POSITIONS:
            if sum(map(abs, h)) < 2:
                continue
            R = Rotation.identity()
            for f, deg in s.misalign_deg.items():
                n = np.array(FACE_NORMAL[f], float)
                if np.dot(h, n) == 1:
                    R = Rotation.from_rotvec(np.radians(deg) * n) * R
            worst_all = max(worst_all, float(np.degrees(R.magnitude())))
    assert worst_all <= SwitchRule().tol_unlock_deg, worst_all


def test_shear_dominance_request_logic():
    """A2 logic on synthetic shears: a dominant face requests alone; equal opposed shears are ambiguous."""
    p, m, sim, mgr = _env()
    base = {f: (0.0, 5.0) for f in FACES}

    mgr.shears = lambda d: {**base, "U": (0.30, 5.0), "D": (-0.10, 5.0)}
    req, amb = mgr.request_torques(sim.d)
    assert req["U"][0] == 0.30 and req["D"][0] == 0.0 and not amb

    mgr.shears = lambda d: {**base, "U": (0.30, 5.0), "D": (-0.30, 5.0)}
    req, amb = mgr.request_torques(sim.d)
    assert req["U"][0] == 0.30 and req["D"][0] == -0.30 and amb  # both request -> rule refuses

    mgr.shears = lambda d: {**base, "U": (0.04, 5.0)}
    req, amb = mgr.request_torques(sim.d)
    assert not amb and abs(req["U"][0]) < SwitchRule().tau_unlock


def _with_two_layer_stabiliser(p) -> str:
    """M2 model plus a D+E stabiliser (two tall pads named stab_*), as in study D6."""
    xml = build_m2_xml(p)
    H, t = 0.0284, 0.0025
    zc, hz = (-H + 0.0090) / 2, (H + 0.0090) / 2 - 0.0005
    y0 = H + 0.014 + t
    bodies, acts = [], []
    for s, nm in ((-1, "a"), (1, "b")):
        bodies.append(f'    <body name="stab_{nm}" pos="0 {s * y0:.6f} {zc:.6f}">\n'
                      f'      <joint name="stab_{nm}_slide" type="slide" axis="0 {s} 0" range="-0.05 0.001" damping="100"/>\n'
                      f'      <geom name="stab_{nm}_g" type="box" size="0.020 {t} {hz:.5f}" contype="2" conaffinity="0" '
                      f'condim="4" friction="0.8 0.005 0.0001" solref="0.001 1" solimp="0.95 0.99 0.0005" mass="0.01"/>\n'
                      f'    </body>')
        acts.append(f'    <position name="stab_{nm}" joint="stab_{nm}_slide" kp="2000" forcerange="-30 30" ctrlrange="-0.05 0.001"/>')
    xml = xml.replace("  </worldbody>", "\n".join(bodies) + "\n  </worldbody>", 1)
    return xml.replace("  <actuator>\n", "  <actuator>\n" + "\n".join(acts) + "\n", 1)


def test_shear_rule_unlocks_U_with_two_layer_stabiliser():
    """A2 in simulation: with the D and E layers held by a stabiliser, turning U unlocks U (not D)."""
    from rubiknetic.cube_physics.readout import CubeReadout
    from rubiknetic.cube_physics.rig import TurnRig

    p = m2_params()
    m = mujoco.MjModel.from_xml_string(_with_two_layer_stabiliser(p))
    sim = SwitchAuditedSim(m)
    mujoco.mj_forward(m, sim.d)
    mgr = SwitchManager(sim, p.pitch)
    assert {mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, g) for g in mgr.gripper_geoms} >= {"stab_a_g", "stab_b_g"}
    ro = CubeReadout(m, p.pitch)
    for s in "ab":
        sim.d.ctrl[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, f"stab_{s}")] = -0.016
    sim.step(int(0.3 / m.opt.timestep))
    prev = ro.observe(sim.d).cube
    TurnRig(sim, pad_close_target=-(p.pad_open_clearance + p.grip_overshoot)).turn(Move("U", 1))
    unlocks = [e["face"] for e in sim.switch_log if e["kind"] == "unlock"]
    assert unlocks and unlocks[0] == "U", sim.switch_log
    obs = ro.observe(sim.d)
    from rubiknetic.cube_logic import infer_move
    assert obs.valid and str(infer_move(prev, obs.cube)) == "U"


def test_weld_count_and_initial_topology():
    p, m, sim, mgr = _env()
    assert m.neq == 146
    ok, problems = mgr.weld_topology_consistent(sim.d)
    assert ok, problems


def test_weld_reanchor_residual_is_zero_at_setup_pose():
    p, m, sim, mgr = _env()
    scored.apply_setup_misalignment(sim, {"U": 0.8, "R": -0.6})  # logged setup writes before t=0
    mgr.setup_reanchor(sim.d)
    mujoco.mj_forward(m, sim.d)
    rows = [i for i in range(sim.d.nefc) if sim.d.efc_type[i] == mujoco.mjtConstraint.mjCNSTR_EQUALITY]
    assert rows and float(np.abs(sim.d.efc_pos[rows]).max()) < 1e-9
    assert any(e["type"] == "weld_reanchor_at_setup_pose" for e in sim.setup_log)


def test_setup_reanchor_forbidden_after_first_step():
    p, m, sim, mgr = _env()
    sim.step()
    with pytest.raises(EditAuditError):
        mgr.setup_reanchor(sim.d)


def test_injected_eq_active_write_is_caught():
    p, m, sim, mgr = _env()
    sim.step()
    sim.d.eq_active[0] = 0
    with pytest.raises(EditAuditError):
        sim.step()


def test_injected_eq_data_write_is_caught():
    p, m, sim, mgr = _env()
    sim.step()
    m.eq_data[0, 3] += 1e-4
    with pytest.raises(EditAuditError):
        sim.step()


def test_injected_qpos_write_is_still_caught():
    p, m, sim, mgr = _env()
    sim.step()
    sim.d.qpos[0] += 0.01
    with pytest.raises(EditAuditError):
        sim.step()


def test_unregistered_switch_caller_is_refused():
    p, m, sim, mgr = _env()
    with pytest.raises(EditAuditError):
        sim.apply_switch(object(), [0], [], {"kind": "fake"})


def test_misaligned_switch_request_is_refused_and_logged():
    mis = {f: 0.0 for f in FACES}
    mis["U"] = 5.0
    tr = scored_m2.TrialM2(scored_m2.params_for_m2(None), None, misalign_override=mis)
    _, r0 = tr.ro.poses(tr.sim.d)
    mem = tr.ro.layer_members(tr.sim.d, "R")
    tr.rig.turn(Move("R", 1), tr.timing)
    _, r1 = tr.ro.poses(tr.sim.d)
    kinds = [e["kind"] for e in tr.sim.switch_log]
    assert "unlock" not in kinds
    assert any(e["kind"] == "refuse" and e["reason"] == "cube misaligned" for e in tr.sim.switch_log)
    assert float(np.abs(tr.ro.rotation_about_deg(r0, r1, mem, "R")).max()) < 0.5


def test_unscored_smoke_sequence_trial_passes():
    rec = scored_m2.run_sequence_trial_m2([Move("U", 1), Move("R", 1)], seed=99, misalign_max_deg=0.0)
    assert [m["observed_move"] for m in rec["per_move"]] == ["U", "R"]
    assert rec["e1_5"]["n"] >= 2 and rec["e1_5"]["n_fail"] == 0, rec["e1_5"]
    assert rec["pass"], {k: v for k, v in rec.items() if k not in ("params", "switch_log", "e1_5")}


def test_never_two_unlocked_reconstruction_b2():
    """Amendment 2 (B2): concurrent-unlock count reconstructed from the switch log."""
    f = scored_m2._max_concurrent_unlocked
    assert f([]) == 0
    assert f([{"kind": "unlock", "face": "U"}, {"kind": "refuse"}, {"kind": "relock", "face": "U"},
              {"kind": "unlock", "face": "R"}]) == 1
    assert f([{"kind": "unlock", "face": "U"}, {"kind": "unlock", "face": "R"}]) == 2


def test_scored_turner_and_e17_factor_amendment_c1():
    """Amendment 3 (C1): every scored M2 trial uses turn_kp 20 / turn_kv 0.8; E1-7 turner factor {5, 20} with
    kv = 0.04*kp and kp 20 as nominal. The B1 fallback stays in force (setup +/-0.25, relock 0.5 / 0.5)."""
    import importlib.util
    from pathlib import Path

    assert scored_m2.SCORED_TURNER == {"turn_kp": 20.0, "turn_kv": 0.8}
    p = scored_m2.params_for_m2(scored_m2.draw_setup(94))
    assert (p.turn_kp, p.turn_kv) == (20.0, 0.8)
    assert scored_m2.SETUP_MISALIGN_MAX_DEG == 0.25
    assert (SwitchRule().tol_lock_deg, SwitchRule().tol_lock_cubie_deg) == (0.5, 0.5)
    spec = importlib.util.spec_from_file_location(
        "e2_run", Path(__file__).resolve().parents[1] / "experiments" / "E2_scored_m2" / "run.py")
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)
    assert dict(run.E17_FACTORS)["turn_kp"] == [5.0, 20.0]
    assert ("turn_kp", 20.0) in run.NOMINAL and ("turn_kp", 5.0) not in run.NOMINAL
    m1, _, _ = run._split_overrides({"turn_kp": 5.0})
    assert m1 == {"turn_kp": 5.0, "turn_kv": 0.2}
    labels = " ".join(scored_m2.AMENDMENTS)
    for tag in ("A1", "A2", "A3", "A4", "A5", "B1 FALLBACK", "B2", "C1"):
        assert tag in labels


def _check_now(mgr, d):
    """Run one rule evaluation on the next call (the manager checks every ``check_every`` steps)."""
    mgr.k = mgr.rule.check_every - 1
    mgr(d)


def test_fresh_grip_blocks_reunlock_amendment_d1():
    """D1: after a relock, the face may not request again until its own pads' grip has dropped below grip_min_n."""
    p, m, sim, mgr = _env()
    d = sim.d
    mujoco.mj_forward(m, d)
    strong = {f: (0.0, 5.0) for f in FACES}
    strong["U"] = (0.30, 5.0)
    released = {f: (0.0, 0.0) for f in FACES}
    mgr.needs_release["U"] = True  # as if U had just relocked
    mgr.request_torques = lambda dd: (strong, False)
    _check_now(mgr, d)
    assert mgr.unlocked is None, "a pad-release transient must not re-unlock the face"
    mgr.request_torques = lambda dd: (released, False)  # pads let go
    _check_now(mgr, d)
    assert mgr.needs_release["U"] is False
    mgr.request_torques = lambda dd: (strong, False)  # a fresh grip with torque: a genuine new request
    _check_now(mgr, d)
    assert mgr.unlocked == "U"


def test_relock_uses_own_pad_torque_amendment_d0():
    """D0 (conformity with section 1): relock checks the unlocked face's OWN pad torque, so other faces' pads
    pressing on the layer (all-contact shear) cannot block the relock (the scored run 1 deadlock)."""
    p, m, sim, mgr = _env()
    d = sim.d
    mujoco.mj_forward(m, d)
    strong = {f: (0.0, 5.0) for f in FACES}
    strong["U"] = (0.30, 5.0)
    mgr.request_torques = lambda dd: (strong, False)
    _check_now(mgr, d)
    assert mgr.unlocked == "U"
    mgr.unlock_time = d.time - 10.0  # "moved" condition satisfied by elapsed time
    quiet = {f: (0.0, 0.0) for f in FACES}
    mgr.request_torques = lambda dd: (quiet, False)
    mgr.shears = lambda dd: {**quiet, "U": (0.50, 0.0)}   # large all-contact shear on U from OTHER pads
    mgr.pad_torque = lambda dd, face: (0.0, 0.0)          # U's own pads exert nothing
    _check_now(mgr, d)
    assert mgr.unlocked is None, "relock must not be blocked by other faces' contacts"
