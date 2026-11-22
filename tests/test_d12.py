"""Unit tests for the D12 turning-stall diagnostic scripts (experiments/D12_turn_stall/PROTOCOL.md).

Pure logic only: the seed guard, override application and the setup draw (S6's logic), the jam / catch classification
on synthetic traces, the analysis rules on synthetic records, the stop-rule arithmetic, and Stage 0's parser on
synthetic records. The only MuJoCo work is building models (XML compile and mj_kinematics); no test takes a step.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
D12 = REPO / "experiments" / "D12_turn_stall"
sys.path.insert(0, str(D12))

import d12_analyze as A  # noqa: E402
import d12_common as C  # noqa: E402
import d12_replay as RP  # noqa: E402
import d12_run as RUN  # noqa: E402
import d12_stage0 as S0  # noqa: E402

from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES  # noqa: E402
from rubiknetic.cube_physics import scored  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml  # noqa: E402
from rubiknetic.cube_physics.readout import CubeReadout  # noqa: E402

B1 = {"radial_preload": 0.0, "gap": 5e-5}          # E5's M4.BASE_OVERRIDES (the frozen B1 / M5 base)


# ---- seed guard (S5) ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("seed", [10000, 10001, 10500, 10999, 17000, 17500, 17999])
def test_forbidden_ranges_always_refused(seed):
    with pytest.raises(C.Refused, match="forbidden"):
        C.check_seed(seed)
    with pytest.raises(C.Refused):
        C.replay_job("stage1", "L0", C.NOMINAL, "R1", seed)


@pytest.mark.parametrize("seed", [16655, 16899, 16905, 16909, 16912, 16999, 16001, 16103, 1000, 9999, 18000, -1])
def test_unlisted_seeds_refused(seed):
    with pytest.raises(C.Refused, match="not in PROTOCOL"):
        C.check_seed(seed)


def test_listed_seeds_accepted_and_uses_enforced():
    listed = {16100, 16101, 16900, 16901, 16902, 16102, 16104, 16108, 16903, 16904, 16910, 16911, 16000, 16003, 16568}
    assert C.ALLOWED_SEEDS == listed
    for s in listed:
        assert C.check_seed(s) == s
    assert all(C.RESERVED_BLOCK[0] <= s <= C.RESERVED_BLOCK[1] for s in (16900, 16901, 16902, 16903, 16904, 16910, 16911))
    with pytest.raises(C.Refused):
        C.check_seed(16910, "replay")              # a Stage 4 sequence seed is not a replay seed
    with pytest.raises(C.Refused):
        C.check_seed(16100, "seq")
    with pytest.raises(C.Refused):
        C.check_seed(16102, "replay", "U")         # 16102 is ER7's U' seed
    assert C.check_seed(16102, "replay", "U'") == 16102
    for bad in (True, "16100", 16100.0, None):
        with pytest.raises(C.Refused):
            C.check_seed(bad)
    with pytest.raises(C.Refused):
        C.stage4_job(C.NOMINAL, "6move", 10000)
    with pytest.raises(C.Refused):
        C.stage4_job(C.NOMINAL, "snap", 16568, 5.0)


def test_s5_check_and_job_lists():
    s5 = RUN.s5_check()
    assert s5["pass"], s5
    js = C.stage1_jobs()
    assert len(js) == 102 and len({j["job_id"] for j in js}) == 102
    assert sum(j["rig"] == "R5" for j in js) == 87 and sum(j["rig"] == "R1" for j in js) == 15
    assert {j["seed"] for j in js} == set(C.NOMINAL_SEEDS)
    assert all(j["move"] == "U" for j in js)
    counts = C.projected_stage_counts()
    assert counts["stage1"] == {"none@0.5ms": 34, "L0@0.5ms": 34, "W3@0.5ms": 34}
    s2 = C.stage2_jobs(C.setting(1e-4, 0.0020))
    assert len(s2) == 48 and sum(C.job_timestep(j) == 0.00025 for j in s2) == 12
    assert len(C.stage2_jobs(None)) == 24
    s3 = C.stage3_jobs([("L0", C.setting(2.5e-4, 0.002)), ("none", C.setting(check="f"))])
    assert len(s3) == 16
    assert [(j["seed"], j["move"]) for j in s3 if j["rig"] == "R5"][:5] == list(C.STAGE3_R5)
    with pytest.raises(C.Refused):
        C.stage3_jobs([("W3", C.NOMINAL)])
    s4 = C.stage4_jobs([C.setting(1e-4, 0.0014)])
    assert len(s4) == 16 and all(j["rig"] == "R1" and j["layout"] == "L0" for j in s4)
    assert len(C.selfcheck_replays()) == 9 and len(C.timing_replays()) == 6


def test_jobs_survive_the_json_hand_off_to_the_worker():
    """The worker recomputes the overrides from the job's setting and compares them with the job's JSON copy."""
    js = C.stage1_jobs() + C.stage2_jobs(C.setting(1e-4, 0.002)) + C.stage4_jobs([C.setting(check="b")])
    for j in js:
        jj = json.loads(json.dumps(j, default=C.jsonable))
        ov = C.overrides_for(jj["setting"], jj["rig"])
        assert C._norm(ov) == C._norm(jj["overrides"])
        assert ov == j["overrides"]


def test_registry_refuses_unknown_and_s1_only_arms():
    for bad in ("W2", "S1", "C52x", "H1", "G2", "X0.03", "PG0"):
        with pytest.raises(C.Refused):
            C.check_arm(bad)
    with pytest.raises(C.Refused):
        C.replay_job("stage1", "X0.003", C.NOMINAL, "R5", 16100)
    with pytest.raises(C.Refused):
        C.replay_job("stage1", "W1", C.setting(1e-4), "R1", 16100)
    assert C.replay_job("selfcheck", "C52", C.NOMINAL, "R1", 16100)["trace"]
    with pytest.raises(C.Refused):
        C.setting(gap=2e-4)
    with pytest.raises(C.Refused):
        C.setting(check="z")


# ---- overrides (section 8.1) ----------------------------------------------------------------------------------------
def test_nominal_overrides_change_nothing():
    ov = C.overrides_for(C.NOMINAL, "R1")
    assert ov["m1"] == {"gap": 5e-5} and ov["setup"] == {}
    assert M1Params(**{**B1, **ov["m1"]}) == M1Params(**B1)


def test_r5_differs_from_r1_only_in_turner_limit():
    for st in (C.NOMINAL, C.setting(2.5e-4, 0.001), C.setting(check="b"), C.setting(check="g")):
        r1, r5 = C.overrides_for(st, "R1"), C.overrides_for(st, "R5")
        assert {k: v for k, v in r5["m1"].items() if k != "turn_torque_limit"} == r1["m1"]
        assert r5["m1"]["turn_torque_limit"] == 5.0 and "turn_torque_limit" not in r1["m1"]
        assert r5["setup"] == r1["setup"]
    assert C.overrides_for(C.NOMINAL, "R5")["rig_label"] == "R5-diagnostic (turn_torque_limit 5.0 N·m; NOT the frozen rig)"


def test_check_overrides_are_exactly_the_protocol_settings():
    m1 = lambda c: C.overrides_for(C.setting(check=c), "R1")["m1"]  # noqa: E731
    assert m1("a") == {"gap": 5e-5, "timestep": 0.00025}
    assert m1("b") == {"gap": 5e-5, "timestep": 0.00025, "cubie_solref": (0.0005, 1.0)}
    assert m1("c") == {"gap": 5e-5, "cubie_solimp": (0.99, 0.99, 0.0005)}
    assert m1("d") == {"gap": 5e-5, "cubie_friction": (0.1, 0.0025, 0.0005)}
    assert m1("e") == {"gap": 5e-5, "cubie_friction": (0.5, 0.0025, 0.0005)}
    for c in "fgh":
        assert m1(c) == {"gap": 5e-5}
    assert C.overrides_for(C.setting(check="f"), "R5")["setup"] == {"misalign_zero": True}
    assert C.overrides_for(C.setting(check="h"), "R5")["setup"] == {"grip_force": 50.0}
    assert C.overrides_for(C.setting(2.5e-4, 0.002), "R1")["m1"] == {"gap": 2.5e-4, "chamfer": 0.002}
    # every M1 override is a real M1Params field (no global o_solref / o_solimp)
    fields = set(asdict(M1Params()))
    for c in C.CHECKS:
        assert set(m1(c)) <= fields


@pytest.mark.parametrize("seed", sorted(C.REPLAY_SEED_MOVE))
def test_draw_then_replace_keeps_other_draws(seed):
    """S6's logic on the setup draw: replacing a field never shifts another seeded draw."""
    nom = asdict(scored.draw_setup(seed))
    for chk, spec in C.CHECKS.items():
        got = asdict(C.draw_then_replace(scored.draw_setup, seed, spec["setup"]))
        ut = C.fields_under_test(C.setting(check=chk), "R5")["setup"]
        assert C.s6_diffs(nom, got, ut) == []
        if chk == "f":
            assert ut == {"misalign_deg"} and all(v == 0.0 for v in got["misalign_deg"].values())
            assert got["grip_force"] == nom["grip_force"] and got["turn_s_per_quarter"] == nom["turn_s_per_quarter"]
        elif chk in "gh":
            assert ut == {"grip_force"} and got["grip_force"] == spec["setup"]["grip_force"]
            assert got["misalign_deg"] == nom["misalign_deg"]
        else:
            assert got == nom
    # E1-7's misalignment arm drew with misalign_max_deg = 0; grip and turn time agree with draw-then-replace
    e17 = asdict(scored.draw_setup(seed, 0.0))
    assert e17["grip_force"] == nom["grip_force"] and e17["turn_s_per_quarter"] == nom["turn_s_per_quarter"]


def test_s6_diffs_detects_shifted_draw():
    nom = asdict(scored.draw_setup(16100))
    bad = {**nom, "turn_s_per_quarter": nom["turn_s_per_quarter"] + 1e-12}
    assert C.s6_diffs(nom, bad, {"grip_force"})
    assert C.params_diffs({"gap": 5e-5, "chamfer": 0.0014}, {"gap": 5e-5, "chamfer": 0.001}, set())
    assert not C.params_diffs({"gap": 5e-5, "chamfer": 0.0014}, {"gap": 5e-5, "chamfer": 0.001}, {"chamfer"})


def test_wrap_draw_setup_patches_and_records():
    class Mod:
        pass
    mod = Mod()
    mod.draw_setup = scored.draw_setup
    orig = RP.wrap_draw_setup(mod, {})
    assert mod.draw_setup is scored.draw_setup and orig is scored.draw_setup
    orig = RP.wrap_draw_setup(mod, {"grip_force": 10.0})
    s = mod.draw_setup(16101)
    assert s.grip_force == 10.0 and orig(16101).turn_s_per_quarter == s.turn_s_per_quarter


# ---- model builds: overrides reach the XML / compiled model; nothing else changes -----------------------------------
def _xml(st, rig, extra=None):
    ov = C.overrides_for(st, rig)
    return build_m1_xml(M1Params(**{**B1, **ov["m1"], **(extra or {})}))


def test_r5_xml_differs_only_in_turner_forcerange():
    a = _xml(C.NOMINAL, "R1").splitlines()
    b = _xml(C.NOMINAL, "R5").splitlines()
    diff = [(x, y) for x, y in zip(a, b) if x != y]
    assert len(a) == len(b) and len(diff) == 6
    for x, y in diff:
        assert 'name="turn_' in x and 'forcerange="-1.0 1.0"' in x and 'forcerange="-5.0 5.0"' in y
    assert _xml(C.NOMINAL, "R1") == build_m1_xml(M1Params(**B1))


def test_check_xml_settings():
    assert 'timestep="0.00025"' in _xml(C.setting(check="a"), "R5")
    xb = _xml(C.setting(check="b"), "R5")
    assert 'timestep="0.00025"' in xb and 'solref="0.0005 1"' in xb.split('class="pad"')[0]
    assert 'solimp="0.99 0.99 0.0005"' in _xml(C.setting(check="c"), "R5").split('class="pad"')[0]
    assert 'friction="0.1 0.0025 0.0005"' in _xml(C.setting(check="d"), "R5").split('class="pad"')[0]
    pad = _xml(C.setting(check="b"), "R5").split('class="pad"')[1]
    assert 'solref="0.001 1"' in pad and 'friction="0.8 0.005 0.0001"' in pad      # pad contacts untouched


def test_s2_geometry_on_a_built_model():
    import mujoco
    st = C.setting(2.5e-4, 0.0020)
    p = M1Params(**{**B1, **C.overrides_for(st, "R5")["m1"]})
    xml = build_m1_xml(p)
    m = mujoco.MjModel.from_xml_string(xml)
    g = RP.geometry_check(m, p, xml)
    assert g["half_size_ok"] and g["vertices_ok"] and g["xml_vertex_ok"], g
    assert abs(g["compiled_half_size_m"] - (0.019 - 2.5e-4) / 2) < 1e-8
    assert float(m.opt.timestep) == 0.0005
    tid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, "turn_U")
    assert list(m.actuator_forcerange[tid]) == [-5.0, 5.0]
    # a wrong chamfer is detected
    p2 = M1Params(**{**B1, "gap": 2.5e-4, "chamfer": 0.0014})
    g2 = RP.geometry_check(m, p2, xml)
    assert not g2["vertices_ok"] and not g2["xml_vertex_ok"]


@pytest.mark.parametrize("gap", C.GAPS)
def test_l0_face_gap_is_gap_plus_two_walls(gap):
    from rubiknetic.cube_physics.magnets import MagnetParams, layout
    mp = MagnetParams()
    fg = RP.l0_face_gaps(layout(0.019, gap, mp), mp.length)
    assert len(fg) == 24 and max(abs(x - (gap + 2 * mp.wall)) for x in fg) < 1e-12
    assert C.validity("L0", gap, {"max_near_tilt_deg": 1.0, "near_perpendicular": 0})["flagged"] is False


def test_vectorised_layer_angles_match_readout():
    from scipy.spatial.transform import Rotation
    rng = np.random.default_rng(0)
    for f in FACES:
        n = np.array(FACE_NORMAL[f], float)
        r0 = Rotation.from_rotvec(rng.normal(0, 0.02, (8, 3))).as_matrix()
        turn = Rotation.from_rotvec(np.radians(-37.0) * n)
        r1 = np.array([(turn * Rotation.from_matrix(r) * Rotation.from_rotvec(rng.normal(0, 0.01, 3))).as_matrix()
                       for r in r0])
        u, t = RP.layer_reference(r0, n)
        got = RP.layer_angles_deg(r1, u, t, n)
        want = CubeReadout.rotation_about_deg(r0, r1, list(range(8)), f)
        assert np.max(np.abs(got - want)) < 1e-9


def test_rotvec_matches_scipy():
    from scipy.spatial.transform import Rotation
    rng = np.random.default_rng(1)
    q = Rotation.from_rotvec(rng.normal(0, 0.05, (20, 3))).as_quat()          # xyzw, small rotations (as in a turn)
    a = np.array([0, 0, 1.0])
    th = 12.3
    qa = np.concatenate([[np.cos(np.radians(-th) / 2)], np.sin(np.radians(-th) / 2) * a])
    got = RP._rotvec_deg(RP._qmul(qa, q[:, [3, 0, 1, 2]]))
    want = np.degrees((Rotation.from_euler("z", -th, degrees=True) * Rotation.from_quat(q)).as_rotvec())
    assert np.max(np.abs(got - want)) < 1e-9


# ---- section 5: classification on synthetic traces ------------------------------------------------------------------
DT = 0.0005


def synthetic(n_turn=1780, catch=None, stall=None):
    """Turner follows a cosine ramp to -90 deg (U, clockwise); torque baseline 0.05 N m; optional catch (peak, steps)
    inside the window, optional stall (layer frozen for `stall` steps inside the window)."""
    k = np.arange(1, n_turn + 1)
    target = -90.0 * (0.5 - 0.5 * np.cos(np.pi * k / n_turn))
    turner = target.copy()
    tau = np.full(n_turn, 0.05)
    adv = -turner
    w = np.nonzero((adv >= 3) & (adv <= 15))[0]
    if catch is not None:
        peak, width = catch
        i0 = w[len(w) // 3]
        tau[i0:i0 + width] = peak
    layer = turner.copy()
    if stall is not None:
        i0 = w[5]
        layer[i0:i0 + stall] = layer[i0]
        layer[i0 + stall:] = layer[i0 + stall:] - (layer[i0 + stall] - layer[i0])
    return target, turner, layer, tau


def classify(target, turner, layer, tau, rig="R5"):
    sign = -1.0
    ta, la, tg = turner * sign, layer * sign, target * sign
    win = C.window_mask(ta)
    base = C.baseline_Nm(tau, ta)
    imp = C.catch_impulse(tau, win, base, DT)
    wp = float(np.abs(tau[win]).max()) if win.any() else 0.0
    st = C.stall_intervals(la, tg, win, DT)
    return C.catch_class(wp, base, bool(st), rig, False), imp, base, st, win


def test_baseline_window_and_impulse():
    target, turner, layer, tau = synthetic(catch=(1.2, 40))
    cls, imp, base, st, win = classify(target, turner, layer, tau)
    assert base == pytest.approx(0.05)
    assert imp == pytest.approx(40 * (1.2 - 0.05) * DT)
    assert cls["class"] == "present" and cls["high"] and cls["above_warning"]
    assert win.sum() > 0 and not st


def test_r1_clip_catch_and_sublimit_and_absent():
    target, turner, layer, tau = synthetic(catch=(1.0, 30))
    cls = classify(target, turner, layer, tau, rig="R1")[0]
    assert cls["class"] == "present" and cls["clip_catch"] and cls["high"] is None
    cls = classify(*synthetic(catch=(0.998, 30)), rig="R1")[0]
    assert cls["class"] == "attenuated" and not cls["clip_catch"]
    cls = classify(*synthetic(catch=(0.3, 30)))[0]
    assert cls["class"] == "attenuated" and cls["sub_limit"] and not cls["above_warning"]
    assert C.catch_class(0.3, 0.15, False, "R5", False)["class"] == "absent"        # 0.3 < 3 x 0.15
    assert C.catch_class(0.19, 0.01, False, "R5", False)["class"] == "absent"       # below 0.2 N m
    assert C.catch_class(0.999, 0.05, False, "R5", False)["class"] == "attenuated"  # R5 high needs 1.0
    cls = classify(*synthetic())[0]
    assert cls["class"] == "absent"
    assert C.catch_class(0.0, None, False, "R5", False)["class"] == "absent"        # empty window


def test_stall_detection_and_pad_slip():
    L = int(round(0.030 / DT))
    target, turner, layer, tau = synthetic(stall=L + 20)
    cls, imp, base, st, win = classify(target, turner, layer, tau)
    assert st and cls["class"] == "present" and cls["stall"]
    assert st[0][1] - st[0][0] >= L
    slip_adv = (turner - layer) * -1.0                       # the turner keeps going while the layer is held
    assert C.pad_slip_growth(slip_adv, st) > 0.0
    assert not classify(*synthetic(stall=L - 5))[3]          # held for less than 30 ms: no stall
    # a layer advancing 0.06 deg per 30 ms is not a stall; 0.04 deg per 30 ms is
    n = 400
    ta = np.linspace(3.0, 14.0, n)
    win = C.window_mask(ta)
    tg = ta + 1.0
    assert not C.stall_intervals(np.arange(n) * (0.06 / L), tg, win, DT)
    assert C.stall_intervals(np.arange(n) * (0.04 / L), tg, win, DT)
    # target not advancing -> no stall
    assert not C.stall_intervals(np.zeros(n), np.full(n, 5.0), win, DT)
    # pad slip growth inside a stall interval
    slip = np.zeros(n)
    slip[100:200] = np.linspace(0, 1.2, 100)
    assert C.pad_slip_growth(slip, [(100, 199)]) == pytest.approx(1.2)
    assert C.pad_slip_growth(slip, []) == 0.0


def test_jam_rules():
    t = np.arange(10) * DT
    pen = np.full(10, 0.1)
    base = dict(pen_cc_mm=pen, t=t, t_hold_end=0.004, j3_fired=False, j3_detail={}, t_settle_end=0.0045)
    assert not C.jam_check(-89.0, -90.0, **base)["jam"]
    j = C.jam_check(-60.0, -90.0, **base)
    assert j["jam"] and j["J1"]["fired"] and j["J1"]["shortfall_deg"] == pytest.approx(30.0)
    assert not C.jam_check(-70.5, -90.0, **base)["jam"]                       # 19.5 deg: not a jam
    assert C.jam_check(-69.0, -90.0, **base)["jam"]
    assert C.jam_check(-4.0, -90.0, **base)["jam"]                            # D8's "86 deg short"
    assert not C.jam_check(90.5, 90.0, **base)["jam"]                         # U' (counter-clockwise)
    pen2 = pen.copy()
    pen2[6] = 0.6
    j = C.jam_check(-90.0, -90.0, **{**base, "pen_cc_mm": pen2})
    assert j["jam"] and j["J2"]["fired"] and j["J2"]["t"] == pytest.approx(6 * DT)
    j = C.jam_check(-90.0, -90.0, **{**base, "j3_fired": True, "j3_detail": {"observed_valid": False}})
    assert j["jam"] and j["J3"]["fired"] and j["J3"]["observed_valid"] is False
    assert C.catch_class(3.0, 0.05, True, "R5", True)["class"] == "jam"


def test_signature_and_validity():
    u = (0, 0, 1)
    assert C.er9_signature("cubie_0n0", "cubie_pnp", (0.706, -0.081, 0.704), u)        # ER9 W3 contact
    assert C.er9_signature("cubie_nnp", "cubie_n00", (0.0, 0.7006, -0.7135), u)        # ER9 L0 contact
    assert not C.er9_signature("cubie_00p", "cubie_pnp", (0.706, 0, 0.704), u)          # U centre, not a side centre
    assert not C.er9_signature("cubie_p0p", "cubie_ppp", (0.128, 0.99, -0.003), u)      # edge-corner
    n30 = (np.sin(np.radians(30)), 0, np.cos(np.radians(30)))
    n36 = (np.sin(np.radians(36)), 0, np.cos(np.radians(36)))
    assert not C.er9_signature("cubie_0n0", "cubie_pnp", n30, u)
    assert C.er9_signature("cubie_0n0", "cubie_pnp", n36, u)
    assert C.validity("L0", 5e-5, {"max_near_tilt_deg": 5.1, "near_perpendicular": 0})["flagged"]
    assert C.validity("L0", 5e-5, {"max_near_tilt_deg": 1.0, "near_perpendicular": 1})["flagged"]
    assert C.validity("L0", 2.5e-4, {"max_near_tilt_deg": 1.0, "near_perpendicular": 0})["face_gap_mm"] == \
        pytest.approx(1.05)
    assert C.validity("W3", 5e-5, {})["flagged"] and C.validity("W3", 5e-5, {})["kind"] == "proxy"
    assert not C.validity("none", 2.5e-4, None)["flagged"]


def test_stored_steps_selection():
    n = 1000
    win = np.zeros(n, bool)
    win[300:400] = True
    keep = C.stored_steps(n, abs_step0=1000, win=win, events=[700], intervals=[(310, 330)], dt=DT)
    s = set(keep.tolist())
    assert set(range(300, 400)) <= s
    assert set(range(600, 801)) <= s                    # +-0.05 s = 100 steps around the event
    assert all((1000 + 1 + k) % 20 == 0 for k in keep if not (300 <= k < 400 or 600 <= k <= 800 or 210 <= k <= 430))


# ---- section 12: stop-rule arithmetic ---------------------------------------------------------------------------------
def test_stop_rule_arithmetic():
    assert C.per_replay_limit_s(100.0) == 300.0
    assert C.per_replay_limit_s(400.0) == 900.0
    assert C.per_replay_limit_s(None) == 900.0
    assert C.rss_exceeded(401.0, 200.0) and not C.rss_exceeded(400.0, 200.0) and not C.rss_exceeded(1e9, None)
    assert C.below_floor(999.0, 1000.0) and not C.below_floor(1000.0, 1000.0) and not C.below_floor(10.0, None)
    walls = {"none@0.5ms": 10.0, "L0@0.5ms": 20.0, "W3@0.5ms": 60.0, "L0@0.25ms": 40.0}
    assert C.class_wall(walls, "W3@0.25ms") == (120.0, "scaled by L0's 0.25/0.5 ms ratio")
    assert C.class_wall(walls, "none@0.25ms")[0] == 20.0
    p = C.projection_s(walls)
    assert p["stage1"] == pytest.approx(34 * 10 + 34 * 20 + 34 * 60)
    assert p["stage2"] == pytest.approx(18 * 10 + 6 * 20 + 18 * 60 + 6 * 120)
    assert p["stage3_max"] == pytest.approx(48 * 40)
    assert p["total"] == pytest.approx(3060 + 2100 + 1920) and not p["stop"]
    assert C.projection_s({**walls, "W3@0.5ms": 400.0})["stop"]
    assert C.projection_s({"none@0.5ms": 1.0})["stop"]                    # cannot project: stop
    s4 = C.stage4_projection_s(100.0, 20.0, [20.0] * 32)
    assert s4["projected_s"] == pytest.approx(3200.0) and not s4["stop"]
    assert C.stage4_projection_s(1000.0, 20.0, [20.0] * 32)["stop"]


def test_phase_steps_and_s7():
    for seed in sorted(C.REPLAY_SEED_MOVE):
        ts = scored.draw_setup(seed).turn_s_per_quarter
        r = C.s7_check(ts)
        assert r["pass"], r
        ph = C.phase_steps(ts, 0.0005)
        assert ph["turn"] == int(round(ts / 0.0005)) and ph["close"] == ph["hold"] == ph["open"] == ph["settle"] == 600
    assert C.phase_steps(0.8894671422274355, 0.0005)["turn"] == 1779
    assert C.seq_sim_time_s([1, 1], 1.0) == pytest.approx(0.5 + 2 * 2.2)


def test_thresholds_are_the_protocols():
    t = C.THRESHOLDS
    assert t["window_deg"] == (3.0, 15.0) and t["baseline_deg"] == (20.0, 70.0)
    assert (t["high_R5_Nm"], t["clip_R1_Nm"], t["sublimit_Nm"], t["sublimit_ratio"]) == (1.0, 0.999, 0.2, 3.0)
    assert (t["stall_deg"], t["stall_s"], t["jam_shortfall_deg"], t["jam_penetration_mm"]) == (0.05, 0.030, 20.0, 0.5)
    assert (t["censored_R5_Nm"], t["pad_slip_growth_deg"], t["warning_Nm"]) == (4.995, 1.0, 0.45)
    assert len(C.THRESHOLDS_SHA) == 64


# ---- section 11: analysis rules on synthetic records ----------------------------------------------------------------
def rec(layout, st, rig, seed, imp=0.0, cls="absent", peak=0.1, flagged=False, jam=False, crash=False, sig=False):
    j = C.replay_job("test", layout, st, rig, seed)
    if crash:
        return {"job_id": j["job_id"], "job": j, "crash": True, "error": "x"}
    snap = {"signature": sig}
    jd = {"jam": jam, "J1": {"fired": jam, "shortfall_deg": 30.0 if jam else 0.0}, "J2": {"fired": False,
          "max_penetration_mm": 0.1}, "J3": {"fired": False}}
    return {"job_id": j["job_id"], "job": j, "crash": False, "class": "jam" if jam else cls, "catch_impulse_Nms": imp,
            "window_peak_Nm": peak, "baseline_Nm": 0.05, "peak_abs_torque_Nm": peak,
            "flags": {"censored_R5": False, "pad_limited": False, "above_warning": peak >= 0.45},
            "validity": {"flagged": flagged}, "jam": jd, "snapshot_catch": snap, "snapshot_max_normal": snap,
            "setup_used": {}, "setup_drawn": {}, "params": {}}


def nominal_set(layout, values):
    return [rec(layout, C.NOMINAL, "R5", s, imp=v, cls="present") for s, v in zip(C.NOMINAL_SEEDS, values)]


def test_nominal_range_excludes_jams_and_crashes():
    rs = nominal_set("L0", [0.010, 0.012, 0.011, 0.015, 0.009])
    assert A.nominal_range(A.index(rs), "L0") == pytest.approx(0.006)
    rs[3] = rec("L0", C.NOMINAL, "R5", C.NOMINAL_SEEDS[3], imp=5.0, jam=True)
    rs[4] = rec("L0", C.NOMINAL, "R5", C.NOMINAL_SEEDS[4], crash=True)
    assert A.nominal_range(A.index(rs), "L0") == pytest.approx(0.002)


def _gap_slice(layout, vals_by_seed, chamfer=0.0014):
    return [rec(layout, C.setting(g, chamfer), "R5", s, imp=vals_by_seed[s][i], cls="present")
            for i, g in enumerate(C.GAPS) for s in C.GRID_SEEDS]


def test_trend_rule():
    base = nominal_set("none", [0.010, 0.012, 0.011, 0.013, 0.012])              # range 0.003
    vals = {16100: [0.010, 0.020, 0.030], 16101: [0.011, 0.018, 0.025], 16900: [0.012, 0.010, 0.026]}
    rs = [r for r in base if r["job"]["seed"] not in C.GRID_SEEDS] + _gap_slice("none", vals)
    t = A.trend(A.index(rs), "none", "gap", 0.0014)
    assert t["trend"] and t["n_monotone_in_direction"] == 2 and t["reading"] == "trend rising"
    vals2 = {16100: [0.010, 0.011, 0.012], 16101: [0.011, 0.012, 0.013], 16900: [0.012, 0.010, 0.013]}
    rs2 = [r for r in base if r["job"]["seed"] not in C.GRID_SEEDS] + _gap_slice("none", vals2)
    t2 = A.trend(A.index(rs2), "none", "gap", 0.0014)
    assert not t2["trend"] and t2["reading"] == "no trend distinguishable from seed spread"   # diff 0.002 < 0.003
    vals3 = {16100: [0.010, 0.020, 0.030], 16101: [0.030, 0.018, 0.012], 16900: [0.012, 0.025, 0.026]}
    rs3 = [r for r in base if r["job"]["seed"] not in C.GRID_SEEDS] + _gap_slice("none", vals3)
    rs3 = [r if not (r["job"]["seed"] == 16900 and r["job"]["setting"]["gap"] == 1e-4)
           else rec("none", C.setting(1e-4, 0.0014), "R5", 16900, imp=9.0, jam=True) for r in rs3]
    t3 = A.trend(A.index(rs3), "none", "gap", 0.0014)
    assert not t3["trend"] and t3["excluded_jam_or_crash"] == 1 and t3["n_monotone_in_direction"] == 1


def test_effect_rule():
    base = nominal_set("W3", [0.010, 0.012, 0.011, 0.013, 0.012])                # range 0.003
    ref = {16100: 0.011, 16101: 0.012, 16900: 0.013}
    rs = list(base)
    for s, v in ref.items():
        rs = [r for r in rs if not (r["job"]["seed"] == s and C.is_nominal(r["job"]["setting"]))]
        rs.append(rec("W3", C.NOMINAL, "R5", s, imp=v, cls="present"))
    chk = {16100: 0.020, 16101: 0.019, 16900: 0.010}
    rs += [rec("W3", C.setting(check="e"), "R5", s, imp=v, cls="present") for s, v in chk.items()]
    e = A.effect(A.index(rs), "W3", C.NOMINAL, "e")
    assert e["effect"] and e["n_same_direction"] == 2 and e["delta"] == pytest.approx(0.019 - 0.012)
    chk2 = {16100: 0.013, 16101: 0.014, 16900: 0.015}
    rs2 = [r for r in rs if r["job"]["setting"]["check"] != "e"] + \
        [rec("W3", C.setting(check="e"), "R5", s, imp=v, cls="present") for s, v in chk2.items()]
    assert not A.effect(A.index(rs2), "W3", C.NOMINAL, "e")["effect"]


def test_worst_point_candidates_catch_free_stage4_selection():
    rs = []
    for i, st in enumerate(A.grid_points()):
        for s in C.GRID_SEEDS:
            rs.append(rec("none", st, "R5", s, imp=0.01 * (i + 1), cls="present"))
    rs = [r for r in rs if not (C.setting_tag(r["job"]["setting"]) == "g0.25_c2" and r["job"]["seed"] == 16101)]
    rs.append(rec("none", C.setting(2.5e-4, 0.002), "R5", 16101, imp=99.0, jam=True))
    idx = A.index(rs)
    p, table = A.worst_none_point(idx)
    assert C.setting_tag(p) == "g0.25_c1.4"                       # largest jam-free median (the jam point excluded)
    assert any(r["tag"] == "g0.25_c2" and not r["qualifies"] for r in table)
    assert A.worst_none_point(A.index([rec("none", C.NOMINAL, "R5", 16100, jam=True)]))[0] is None
    # candidates: L0 grid points absent on all 3 seeds; one flagged; W3 never
    rs2 = []
    for i, st in enumerate(A.grid_points()):
        for s in C.GRID_SEEDS:
            rs2.append(rec("L0", st, "R5", s, imp=0.001 * (9 - i), cls="absent", flagged=(i == 0)))
            rs2.append(rec("W3", st, "R5", s, imp=0.0, cls="absent", flagged=True))
    cand = A.candidates(A.index(rs2), None)
    assert len(cand["selected"]) == 6 and len(cand["listed_beyond_cap"]) == 2
    assert all(lay == "L0" for lay, _ in cand["selected"])
    assert C.setting_tag(cand["selected"][0][1]) == "g0.25_c2"     # lowest median impulse first
    assert all(C.setting_tag(st) != "g0.05_c1" for lay, st in cand["selected"] + cand["listed_beyond_cap"])
    st = cand["selected"][0][1]
    rs3 = rs2 + [rec("L0", st, "R5", s, cls="absent") for s, _ in C.STAGE3_R5] + \
        [rec("L0", st, "R1", s, cls="absent") for s in C.GRID_SEEDS]
    cf = A.catch_free(A.index(rs3), "L0", st)
    assert cf["catch_free"]
    rs4 = rs3[:-1] + [rec("L0", st, "R1", C.GRID_SEEDS[-1], cls="attenuated")]
    assert not A.catch_free(A.index(rs4), "L0", st)["catch_free"]
    sel = A.stage4_settings(A.index(rs3), [("L0", s_) for _, s_ in cand["selected"]] + [("none", C.setting(check="a"))])
    assert len(sel["selected"]) == 3 and len(sel["returned_to_user"]) == 4
    assert any(r["ranked_by"].startswith("none") for r in sel["rows"])


def test_stage4_verdicts_and_jam_tables():
    def s4(st, trial, seed, extra=None, **g):
        j = C.stage4_job(st, trial, seed, extra)
        return {"job_id": j["job_id"], "job": j, "crash": False, "guard_rail": g, "validity": {"flagged": False}}
    st = C.setting(1e-4, 0.0014)
    rs = [s4(st, "6move", 16910, max_drift_deg=0.5, drift_fail=False, drift_flag=False),
          s4(st, "sexy6", 16910, max_drift_deg=1.2, drift_fail=True, drift_flag=True),
          s4(st, "6move", 16911, max_drift_deg=0.85, drift_fail=False, drift_flag=True),
          s4(st, "sexy6", 16911, max_drift_deg=0.7, drift_fail=False, drift_flag=False),
          s4(st, "rest", 16000, **{"pass": True}), s4(st, "rest", 16003, **{"pass": True}),
          s4(st, "snap", 16568, 8.0, **{"pass": True}), s4(st, "snap", 16568, -8.0, **{"pass": True})]
    v = A.stage4_verdicts(rs)["g0.1_c1.4"]["summary"]
    assert v["complete"] and v["drift_fail"] and not v["passes_guard_rails"]
    assert v["reading"].startswith("trades the stall for drift") and v["max_drift_deg"] == 1.2
    rs[1]["guard_rail"].update(max_drift_deg=0.9, drift_fail=False, drift_flag=True)
    v = A.stage4_verdicts(rs)["g0.1_c1.4"]["summary"]
    assert v["passes_guard_rails"] and "flag" in v["reading"]
    jams = [rec("none", C.NOMINAL, "R1", 16100, jam=True), rec("none", C.NOMINAL, "R5", 16100, cls="present", peak=2.5),
            rec("none", C.NOMINAL, "R1", 16101, cls="present")]
    idx = A.index(jams)
    assert A.jam_table(idx)[0]["k_jam"] == 1 and A.jam_table(idx)[0]["n"] == 2
    assert A.r1_jam_r5_completes(idx)[0]["R5_window_peak_Nm"] == 2.5


def test_prediction_pr1():
    rs = [rec("none", C.NOMINAL, "R5", 16100, peak=1.4, cls="present"),
          rec("none", C.NOMINAL, "R5", 16101, peak=1.1, cls="present"),
          rec("none", C.NOMINAL, "R5", 16900, peak=0.6, cls="attenuated")]
    assert A.predictions(A.index(rs), {}, None, [])["Pr1"]["result"] == "held"
    rs[1] = rec("none", C.NOMINAL, "R5", 16101, peak=0.7, cls="attenuated")
    assert A.predictions(A.index(rs), {}, None, [])["Pr1"]["result"] == "not held"
    rs[2] = rec("none", C.NOMINAL, "R5", 16900, jam=True)
    assert A.predictions(A.index(rs), {}, None, [])["Pr1"]["result"] == "held"
    assert A.predictions(A.index(rs[:2]), {}, None, [])["Pr1"]["result"] == "not testable"


def test_full_report_on_synthetic_records():
    rs = []
    for lay in C.STAGE_LAYOUTS:
        for i, st in enumerate(A.grid_points()):
            for s in C.GRID_SEEDS:
                rs.append(rec(lay, st, "R5", s, imp=0.001 * (i + 1) + 1e-4 * s % 3, cls="present", peak=1.2,
                              flagged=(lay == "W3")))
        for s in C.NOMINAL_EXTRA_SEEDS:
            rs.append(rec(lay, C.NOMINAL, "R5", s, imp=0.005, cls="present", flagged=(lay == "W3")))
        for s in C.NOMINAL_SEEDS:
            rs.append(rec(lay, C.NOMINAL, "R1", s, imp=0.004, cls="present", flagged=(lay == "W3")))
    rs.append(rec("L0", C.NOMINAL, "R1", 16100, crash=True))
    for r in rs:
        r["thresholds_sha256"] = C.THRESHOLDS_SHA
    rep = A.report(rs)
    md = A.markdown(rep)
    assert rep["worst_none_point"]["P_none"] is not None and rep["candidates"]["selected"] == []
    assert rep["thresholds_frozen"]["pass"] and "## Predictions" in md
    json.dumps(rep, default=C.jsonable)


def test_s6_records_rule():
    nom = rec("L0", C.NOMINAL, "R1", 16100)
    d = asdict(scored.draw_setup(16100))
    p = {"gap": 5e-5, "chamfer": 0.0014, "grip_force": d["grip_force"], "turn_torque_limit": 1.0}
    nom.update(setup_used=d, setup_drawn=d, params=p)
    ok = rec("L0", C.setting(check="g"), "R5", 16100)
    ok.update(setup_used={**d, "grip_force": 10.0}, setup_drawn=d,
              params={**p, "grip_force": 10.0, "turn_torque_limit": 5.0})
    assert A.s6_records([nom, ok])["pass"]
    bad = rec("L0", C.setting(check="a"), "R5", 16100)
    bad.update(setup_used={**d, "turn_s_per_quarter": 1.0}, setup_drawn=d,
               params={**p, "turn_torque_limit": 5.0, "timestep": 0.00025})
    r = A.s6_records([nom, bad])
    assert not r["pass"] and "turn_s_per_quarter" in r["problems"][0]["diffs"][0]
    bad2 = rec("none", C.setting(check="c"), "R5", 16100)
    bad2.update(setup_used=d, setup_drawn=d, params={**p, "turn_torque_limit": 5.0, "chamfer": 0.001,
                                                       "cubie_solimp": [0.99, 0.99, 0.0005]})
    r2 = A.s6_records([nom, bad2])
    assert not r2["pass"] and any("chamfer" in x for x in r2["problems"][0]["diffs"])


# ---- driver comparisons (S1, S4) on synthetic records -----------------------------------------------------------------
def test_s1_and_s4_comparisons(tmp_path):
    ref = {"arm": "L0", "seed": 16100, "peak_torque_Nm": 0.4610294451073229, "samples": [{"t": 0.51, "torque": 1e-21}]}
    f = tmp_path / "turn_L0_s16100.json"
    f.write_text(json.dumps(ref))
    RUN.REPO = tmp_path
    try:
        r = {"er9_compat": {"turn": {**ref, "n_magnets": 48}}}
        assert RUN.s1_compare(r, "turn", f)["pass"]
        r["er9_compat"]["turn"]["samples"] = [{"t": 0.51, "torque": 2e-21}]
        out = RUN.s1_compare(r, "turn", f)
        assert not out["pass"] and out["n_diffs"] == 1
    finally:
        RUN.REPO = REPO
    r1 = {"job_id": "a", "first_step_abs_tau_ge_0999": 3, "trace": {"turn_start": "x", "steps": list("abcdef")}}
    r5 = {"job_id": "b", "trace": {"turn_start": "x", "steps": list("abcXYZ")}}
    assert RUN.s4_compare(r1, r5)["pass"]
    r5["trace"]["steps"] = list("abXdef")
    s = RUN.s4_compare(r1, r5)
    assert not s["pass"] and s["first_difference"] == 2
    r1["first_step_abs_tau_ge_0999"] = None
    r5["trace"]["steps"] = list("abcdef")
    assert RUN.s4_compare(r1, r5)["pass"]


def test_jobs_mode_prints_without_simulating(capsys):
    assert RUN.main(["jobs", "stage1"]) == 0
    out = capsys.readouterr().out
    assert "102 jobs" in out and "L0__g0.05_c1.4__R1__s16100" in out


# ---- the read-only hook on a static, forward-computed state (no mj_step) ----------------------------------------------
def test_instrument_hook_on_static_state():
    """Drives Instrument by hand on one mj_forward state (a U layer rotated 2 deg so pieces touch): exercises the
    contact loop, the torque bookkeeping, the snapshots, the ER9-compatible blocks and finish(), and checks that the
    hook leaves every audited mjData array untouched. No simulation step is taken."""
    import types

    import mujoco
    sys.path.insert(0, str(REPO / "experiments" / "D8_alignment"))
    import d8_1b_stage1 as ST
    from rubiknetic.cube_logic import parse
    from rubiknetic.cube_logic.geometric import HOME_POSITIONS
    from rubiknetic.cube_physics.m1_model import cubie_name
    from rubiknetic.cube_physics.rig import AuditedSim, TurnLog, TurnRig, TurnTiming

    p = M1Params(**{**B1, "turn_torque_limit": 5.0})
    m = mujoco.MjModel.from_xml_string(build_m1_xml(p))
    d = mujoco.MjData(m)
    q = np.zeros(4)
    mujoco.mju_axisAngle2Quat(q, np.array([0, 0, 1.0]), np.radians(-2.0))
    for h in HOME_POSITIONS:
        if h[2] == 1 and np.count_nonzero(h) >= 2:
            a = m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, cubie_name(h) + "_j")]
            d.qpos[a:a + 4] = q
    mujoco.mj_forward(m, d)
    assert d.ncon > 0
    sim = AuditedSim(m, d)
    rig = TurnRig(sim, pad_close_target=-(p.pad_open_clearance + p.grip_overshoot))
    timing = TurnTiming(close_s=0.001, turn_s_per_quarter=0.004, hold_s=0.001, open_s=0.001, settle_s=0.001)
    tr = types.SimpleNamespace(model=m, sim=sim, ro=CubeReadout(m, p.pitch), rig=rig, timing=timing)
    snap = {k: np.array(getattr(d, k), copy=True) for k in ("qpos", "qvel", "act", "ctrl", "qfrc_applied",
                                                             "xfrc_applied")}
    inst = RP.Instrument(tr, parse("U")[0], None, ST, "none", 16100, trace=True)
    assert inst.N == 2 + 8 + 2 + 2 + 2
    log = TurnLog("U")
    for k in range(inst.N):
        sim.steps += 1                         # stand-in for mj_step: the state stays the forward-computed one
        inst(d)
        log.t.append(float(d.time))
        log.turner_angle_deg.append(0.0)
        log.turner_torque.append(float(d.actuator_force[rig.act["U"][2]]))
    for k, v in snap.items():
        assert np.array_equal(v, getattr(d, k)), k
    out = inst.finish(log, 0.0, scored.draw_setup(16100), {"fired": False, "detail": {}})
    assert out["n_steps"] == inst.N and len(out["trace"]["steps"]) == inst.N
    assert out["snapshot_max_normal"]["n_cc"] == int(inst.ai["n_cc"][0]) > 0
    assert len(out["snapshot_max_normal"]["top"]) <= 8
    assert out["hold_end"]["rotation_median_deg"] == pytest.approx(0.0, abs=1e-9)  # static: no rotation since start
    assert out["series"]["layer_rot_deg"][0] == pytest.approx(0.0, abs=1e-9)    # relative to the turn-start snapshot
    assert out["er9_compat"]["catch"]["normal"] == pytest.approx(out["snapshot_max_normal"]["summed_cc_normal_N"])
    assert len(out["er9_compat"]["catch"]["pieces"]) == 9 and out["er9_compat"]["turn"]["arm"] == "none"
    lag = out["snapshot_max_normal"]["pieces"]
    for nm, v in out["er9_compat"]["catch"]["pieces"].items():     # generalised lag/tilt = ER9's for U
        assert lag[nm]["lag_deg"] == pytest.approx(v["lag_about_z_deg"], abs=1e-9)
        assert lag[nm]["tilt_deg"] == pytest.approx(v["tilt_deg"], abs=1e-9)
    assert out["jam"]["J1"]["fired"]                                 # the layer "ended" 90 deg short in this stand-in
    json.dumps(out, default=C.jsonable)


# ---- review fixes F1-F6 ---------------------------------------------------------------------------------------------
class _CP:
    def __init__(self, rc=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def test_f1_frozen_paths_cover_d12_code_and_force_law():
    fp = C.FROZEN_PATHS
    assert "src" in fp                                        # m1_model, rig, scored, readout, magnets (force law)
    for f in ("d12_run.py", "d12_common.py", "d12_replay.py", "d12_analyze.py", "d12_stage0.py", "PROTOCOL.md"):
        assert f"experiments/D12_turn_stall/{f}" in fp
    for p in ("experiments/ER9_anchored_core_layouts/er9_probe.py", "experiments/ER7_core_magnet_rehearsal/er7_run.py",
              "experiments/E5_scored_m5/run.py", "experiments/E4_scored_m4/run.py", "experiments/D8_alignment/magnets.py",
              "experiments/D8_alignment/results/d8_1b_checks*.json", "experiments/E5_scored_m5/results/E1-7"):
        assert p in fp
    assert RUN.FROZEN_PATHS is C.FROZEN_PATHS


def test_f1_frozen_problems(monkeypatch):
    calls = []

    def fake(status="", diff_rc=0):
        def g(*args, check=True):
            calls.append(args)
            if args[0] == "status":
                return _CP(0, status)
            if args[0] == "diff" and "--quiet" in args:
                return _CP(diff_rc)
            return _CP(0, "src/rubiknetic/cube_physics/magnets.py")
        return g
    monkeypatch.setattr(C, "git", fake())
    assert C.frozen_problems("abc123") == []
    assert calls[1][:4] == ("diff", "--quiet", "abc123", "HEAD") and calls[1][4] == "--"
    assert tuple(calls[1][5:]) == tuple(C.FROZEN_PATHS)
    monkeypatch.setattr(C, "git", fake(diff_rc=1))
    p = C.frozen_problems("abc123")
    assert len(p) == 1 and "magnets.py" in p[0]
    monkeypatch.setattr(C, "git", fake(status=" M src/x.py"))
    assert "uncommitted" in C.frozen_problems("abc123")[0]
    assert C.frozen_problems(None) == ["no commit recorded"]


def test_f1_run_jobs_refuses_stale_reuse_and_moved_code(monkeypatch):
    job = C.replay_job("stage1", "L0", C.NOMINAL, "R5", 16101)
    monkeypatch.setattr(C, "frozen_problems", lambda c: [] if c == "new" else [f"frozen paths differ ({c})"])
    monkeypatch.setattr(RUN, "record_index", lambda: {job["job_id"]: Path("x.json.gz")})
    monkeypatch.setattr(RUN, "read", lambda p: {"job_id": job["job_id"], "job": {**job, "commit": "old"}})
    with pytest.raises(RUN.RefusedRun, match="existing record"):
        RUN.run_jobs([job], "stage1", {"commit": "new"}, None, None)
    monkeypatch.setattr(RUN, "read", lambda p: {"job_id": job["job_id"], "commit": "new", "job": job})
    assert RUN.run_jobs([job], "stage1", {"commit": "new"}, None, None)[0]["commit"] == "new"
    monkeypatch.setattr(RUN, "record_index", lambda: {})
    monkeypatch.setattr(RUN, "run_one", lambda *a: pytest.fail("must not launch a worker"))
    with pytest.raises(RUN.RefusedRun, match="start-up commit"):
        RUN.run_jobs([job], "stage1", {"commit": "moved"}, None, None)


def test_f2_incomplete_sequence_is_not_a_drift_failure():
    v = C.seq_guard_rail([0.3, 0.4], 6, aborted=False)
    assert v["incomplete"] and not v["drift_fail"] and not v["drift_flag"] and not v["pass"]
    v = C.seq_guard_rail([0.3] * 6, 6, aborted=True)
    assert v["incomplete"] and not v["drift_fail"] and not v["pass"]
    v = C.seq_guard_rail([0.3, 1.2, 0.2, 0.1, 0.1, 0.1], 6, aborted=False)
    assert v["drift_fail"] and v["drift_flag"] and not v["incomplete"] and not v["pass"]
    v = C.seq_guard_rail([0.85] * 6, 6, aborted=False)
    assert v["drift_flag"] and not v["drift_fail"] and v["pass"]
    assert C.seq_guard_rail([], 24, aborted=True)["incomplete"]

    def s4(st, trial, seed, extra=None, g=None):
        j = C.stage4_job(st, trial, seed, extra)
        return {"job_id": j["job_id"], "job": j, "crash": False, "guard_rail": g, "validity": {"flagged": False}}
    st = C.setting(1e-4, 0.0014)
    ok = {"pass": True}
    rs = [s4(st, "6move", 16910, g=C.seq_guard_rail([0.3, 0.4], 6, False)),           # incomplete
          s4(st, "sexy6", 16910, g=C.seq_guard_rail([0.5] * 24, 24, False)),
          s4(st, "6move", 16911, g=C.seq_guard_rail([0.5] * 6, 6, False)),
          s4(st, "sexy6", 16911, g=C.seq_guard_rail([0.5] * 24, 24, False)),
          s4(st, "rest", 16000, g=ok), s4(st, "rest", 16003, g=ok),
          s4(st, "snap", 16568, 8.0, g=ok), s4(st, "snap", 16568, -8.0, g=ok)]
    s = A.stage4_verdicts(rs)["g0.1_c1.4"]["summary"]
    assert not s["passes_guard_rails"] and not s["drift_fail"]
    assert s["reading"] == "fails a guard rail (sequence incomplete: oracle/abort)"
    assert s["n_sequences_complete"] == 3 and len(s["incomplete_sequences"]) == 1
    # Pr7: complete sequences of this gap >= 0.10 mm setting show no drift flag -> "not held"; incomplete ignored
    assert A.predictions({}, A.stage4_verdicts(rs), None, [("L0", st)])["Pr7"]["result"] == "not held"
    only_incomplete = [r for r in rs if r["job"]["trial_kind"] != "seq"] + \
        [s4(st, "6move", 16910, g=C.seq_guard_rail([1.5], 6, True))]
    s4v = A.stage4_verdicts(only_incomplete)
    assert not s4v["g0.1_c1.4"]["summary"]["drift_fail"]
    assert A.predictions({}, s4v, None, [("L0", st)])["Pr7"]["result"] == "not testable"


def test_f3_stage4_seed_consistency():
    j = C.stage4_job(C.NOMINAL, "sexy6", 16911)
    assert C.stage4_seed_check(j) == 16911
    with pytest.raises(C.Refused, match="kw seed"):
        C.stage4_seed_check({**j, "kw": {**j["kw"], "seed": 16910}})
    with pytest.raises(C.Refused, match="forbidden"):
        C.stage4_seed_check({**j, "seed": 10000, "kw": {**j["kw"], "seed": 10000}})
    with pytest.raises(C.Refused):
        C.stage4_seed_check({**j, "seed": 16000, "kw": {**j["kw"], "seed": 16000}})   # a rest seed, not a seq seed
    r = C.stage4_job(C.NOMINAL, "rest", 16003)
    assert C.stage4_seed_check(r) == 16003


def test_f4_stage4_trial_limits():
    assert C.stage4_trial_limit_s(None, 50.0) == 30 * 60.0                  # the first trial
    assert C.stage4_trial_limit_s(10.0, 60.0) == 1800.0                     # 3 x 10 x 60
    assert C.stage4_trial_limit_s(10.0, 200.0) == 3600.0                    # capped at 60 min
    assert C.stage4_trial_limit_s(1.0, 10.5) == 300.0                       # at least 5 min


def test_f5_timing_jobs_are_retimed_and_kept_out_of_the_analysis():
    t, s = C.timing_replays(), C.selfcheck_replays()
    assert all(j["job_id"].endswith("__timing") and j["purpose"] == "timing" for j in t)
    assert not {j["job_id"] for j in t} & {j["job_id"] for j in s}
    assert not {j["job_id"] for j in t} & {j["job_id"] for j in C.stage1_jobs()}
    a = rec("L0", C.NOMINAL, "R1", 16100, imp=0.1)
    b = rec("L0", C.NOMINAL, "R1", 16100, imp=0.9)
    b["job"] = {**b["job"], "purpose": "timing"}
    assert A.index([b, a])[("L0", "g0.05_c1.4", "R1", 16100)]["catch_impulse_Nms"] == 0.1
    assert A.index([b]) == {}


def test_f6a_s3_check_survives_crash_records_without_process():
    good = [{"job_id": f"j{i}", "process": {"pid": 100 + i, "jobs_in_process": 1}} for i in range(3)]
    assert RUN.s3_check(good)["pass"]
    bad = good + [{"job_id": "crashed", "crash": True}]
    r = RUN.s3_check(bad)
    assert not r["pass"] and r["missing_process_data"] == ["crashed"]
    assert not RUN.s3_check(good + [{"job_id": "dup", "process": {"pid": 100, "jobs_in_process": 1}}])["pass"]


def test_f6c_configure_layout_refuses_missing_derived_table(tmp_path):
    import types
    assert C.required_table_name({"grade": "N35", "scale": 0.3}) == "tilt_4x3_1.19T_s0.3_r8_h1.5_q16x48.npz"
    assert C.required_table_name({"grade": "N35", "scale": 0.003}) == "tilt_4x3_1.19T_s0.003_r8_h1.5_q16x48.npz"
    assert C.required_table_name({"grade": "N35", "scale": 1.0}) == "tilt_4x3_1.19T_s1_r8_h1.5_q16x48.npz"
    assert C.required_table_name({"grade": "N52", "edge_opt": ["axis"]}) is None      # C52: M6's table, no write
    configured = []
    E7 = types.SimpleNamespace(ER7_GLOBALS={}, set_seeds=lambda g: None, setup_arm=lambda a: None)
    P = types.SimpleNamespace(E7=E7, TABLES=tmp_path, C52_CFG={"grade": "N52"},
                              arms=lambda: {"W1": {"grade": "N35", "scale": 1.0}, "W3": {"grade": "N35", "scale": 0.3}},
                              configure=lambda cfg: configured.append(cfg))
    for lay in ("W3", "X0.003", "W1"):
        with pytest.raises(C.Refused, match="missing"):
            RP.configure_layout(P, lay)
    assert configured == []
    (tmp_path / "tilt_4x3_1.19T_s0.3_r8_h1.5_q16x48.npz").write_bytes(b"")
    assert RP.configure_layout(P, "W3")["scale"] == 0.3 and len(configured) == 1
    assert RP.configure_layout(P, "C52") == {"grade": "N52"}
    assert RP.configure_layout(P, "none") is None and len(configured) == 2


def test_f6d_none_replays_ran_without_callback():
    a = rec("none", C.NOMINAL, "R1", 16100)
    b = rec("none", C.NOMINAL, "R5", 16100)
    for r in (a, b):
        r.update(magnet_callback_installed=False, magnets=None)
    assert C.none_replays_clean([a, b])["pass"]
    b["magnet_callback_installed"] = True
    r = C.none_replays_clean([a, b])
    assert not r["pass"] and r["bad"] == [b["job_id"]]
    assert not C.none_replays_clean([])["pass"]                                    # nothing checked: not a pass


# ---- Stage 0 parser on synthetic records ----------------------------------------------------------------------------
def _seq(torques, drifts, ok=True, moves=None):
    moves = moves or ["U"] * len(torques)
    return {"sequence": " ".join(moves), "pass": ok,
            "per_move": [{"move": m, "max_turner_torque_Nm": t, "nontarget_drift_deg": d}
                         for m, t, d in zip(moves, torques, drifts)]}


def test_stage0_e17_table_and_comparison():
    recs = {"nominal__6move": _seq([0.4651, 0.2, 0.3, 0.1, 0.2, 0.3], [0.474, 0.1, 0.2, 0.1, 0.1, 0.1]),
            "nominal__sexy6": _seq([0.640] + [0.2] * 23, [0.517] + [0.1] * 23),
            "magnet=none__6move": _seq([1.0, 1.0], [0.578, 0.2], ok=False),
            "magnet=none__sexy6": _seq([1.0] * 5 + [0.5] * 19, [0.843] + [0.1] * 23)}
    tab = S0.e17_table(recs)
    assert tab["nominal"]["6move"]["first_move_peak_Nm"] == 0.4651 and tab["magnet=none"]["6move"]["clipped_moves"] == 2
    rows = {r["arm"]: r for r in S0.compare_e17(tab)}
    assert rows["nominal"]["match"] and rows["magnet=none"]["match"], rows
    assert not rows["gap=0.0001"]["match"] and rows["gap=0.0001"]["problems"] == ["records missing"]
    recs["nominal__sexy6"]["per_move"][0]["max_turner_torque_Nm"] = 0.700
    rows = {r["arm"]: r for r in S0.compare_e17(S0.e17_table(recs))}
    assert not rows["nominal"]["match"] and "sexy6 max" in rows["nominal"]["problems"][0]
