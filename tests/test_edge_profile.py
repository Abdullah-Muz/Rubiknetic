"""P-79 R0: rounded piece edges. The default (chamfer) geometry and record params must be unchanged; the rounded
geometry must keep the half-size, meet each face at 15 deg on its first fillet facet, and not overlap in the solved pose."""
import hashlib
from dataclasses import asdict

import mujoco
import numpy as np
import pytest
from scipy.spatial import ConvexHull

from rubiknetic.cube_physics import m1_model
from rubiknetic.cube_physics.m1_model import EDGE_DEFAULTS, M1Params, build_m1_xml, params_record, piece_vertices

# sha256 of build_m1_xml output recorded at commit 07054f1, before the edge_profile fields were added
XML_SHA256_BEFORE_P79 = {
    (): "dd9f542bb3ea79d390274ce9e2a67d4dea15eb4a857a645ea70b9d373c95af02",
    (("gap", 5e-05), ("radial_preload", 0.0)): "191add2380d0698d53a324fa3dc9ac19771ecd9185a007ba2a0370b02a067c64",
    (("gap", 5e-05), ("radial_preload", 0.0), ("rig", False)):
        "43c565162fa80d39e164c9cdd5210630fd6f10310af331d85cb97654c8390382",
}
PARAM_KEYS_BEFORE_P79 = [
    "pitch", "gap", "chamfer", "cubie_mass", "cubie_friction", "cubie_condim", "cubie_solref", "cubie_solimp",
    "joint_damping", "joint_frictionloss", "joint_armature", "radial_preload", "radial_stiffness", "radial_range",
    "radial_damping", "radial_solreflimit", "radial_solimplimit", "rig", "pad_thickness", "pad_width", "pad_height",
    "pad_open_clearance", "grip_overshoot", "pad_slide_damping", "pad_friction", "pad_condim", "pad_solref",
    "pad_solimp", "grip_force", "grip_kp", "turn_torque_limit", "turn_kp", "turn_kv", "rig_mass", "timestep",
    "gravity_z", "integrator", "cone", "impratio", "solver", "iterations", "tolerance"]
B1 = dict(gap=5e-05, radial_preload=0.0)


@pytest.mark.parametrize("kw", list(XML_SHA256_BEFORE_P79))
def test_default_xml_byte_identical(kw):
    xml = build_m1_xml(M1Params(**dict(kw)))
    assert hashlib.sha256(xml.encode()).hexdigest() == XML_SHA256_BEFORE_P79[kw]


def test_default_record_params_unchanged():
    p = M1Params(**B1)
    rec = params_record(p)
    assert list(rec) == PARAM_KEYS_BEFORE_P79
    assert rec == {k: v for k, v in asdict(p).items() if k != "extra" and k not in EDGE_DEFAULTS}


def test_rounded_record_params_state_the_edge():
    rec = params_record(M1Params(**B1, edge_profile="rounded", edge_radius=0.0025))
    assert rec["edge_profile"] == "rounded" and rec["edge_radius"] == 0.0025


@pytest.mark.parametrize("r", [0.0014, 0.0025])
def test_rounded_geometry(r):
    p = M1Params(**B1, edge_profile="rounded", edge_radius=r)
    h = (p.pitch - p.gap) / 2
    v = piece_vertices(p)
    assert len(v) == 104
    assert np.allclose(v.max(axis=0), h) and np.allclose(v.min(axis=0), -h)
    hull = ConvexHull(v)
    nz = [abs(e[2]) for e in hull.equations[:, :3] if 0.01 < e[2] < 0.9999]
    first = min(np.degrees(np.arccos(nz)))           # smallest tilt of a non-flat facet adjacent to the +z face
    assert first == pytest.approx(15.0, abs=0.6)
    flat = [e for e in hull.equations if e[2] > 0.9999]
    assert flat, "flat face missing"


@pytest.mark.parametrize("r", [0.0014, 0.0025])
def test_rounded_solved_pose_has_no_piece_overlap(r):
    m = mujoco.MjModel.from_xml_string(build_m1_xml(M1Params(**B1, edge_profile="rounded", edge_radius=r)))
    d = mujoco.MjData(m)
    mujoco.mj_fwdPosition(m, d)
    cub = [i for i in range(d.ncon) if m.geom(d.contact[i].geom1).name.startswith("cubie")
           and m.geom(d.contact[i].geom2).name.startswith("cubie")]
    assert not cub


def test_rounded_matches_diagnostic_geometry():
    """R0 must build exactly the geometry the P-78 diagnostic tested (diag_catch/edge_patch.py)."""
    import importlib.util
    from pathlib import Path
    f = Path(__file__).resolve().parents[1] / "experiments/D14_noslip_rest_rehearsal/diag_catch/edge_patch.py"
    spec = importlib.util.spec_from_file_location("edge_patch", f)
    ep = importlib.util.module_from_spec(spec); spec.loader.exec_module(ep)
    h = (0.019 - 5e-05) / 2
    for r in (0.0014, 0.0025):
        assert np.array_equal(m1_model._rounded_box_vertices(h, r), ep.rounded_box_vertices(h, r))


@pytest.mark.parametrize("kw", [dict(edge_profile="rounded", edge_radius=0.0),
                                dict(edge_profile="rounded", edge_radius=0.01),
                                dict(edge_profile="fillet")])
def test_bad_edge_settings_raise(kw):
    with pytest.raises(ValueError):
        build_m1_xml(M1Params(**B1, **kw))
