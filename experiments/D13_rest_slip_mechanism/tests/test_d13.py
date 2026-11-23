"""D13 unit tests: XML patch, contact reading, labels, rule, Q3 labels, references from the committed records.
Run (WSL, repo root): ~/.venvs/rubiknetic/bin/python -m pytest -q experiments/D13_rest_slip_mechanism/tests"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import mujoco
import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[1]


def _load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


RUN = _load("d13_run", HERE / "d13_run.py")
AN = _load("d13_analyze", HERE / "d13_analyze.py")


def test_runs_and_seeds():
    runs = RUN.all_runs()
    assert len(runs) == 50
    assert sum(v == "V0" for v, _ in runs) == 8
    assert {s for _, s, _ in RUN.CASES.values()} == {16000, 16003, 16005, 16011, 16013, 16016}
    assert all(16000 <= s <= 16999 for s in RUN.ALLOWED_SEEDS)


def test_noslip_patch_compiles():
    from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml
    xml = RUN.with_noslip(build_m1_xml(M1Params(rig=True, gap=5e-5)), 10)
    m = mujoco.MjModel.from_xml_string(xml)
    assert m.opt.noslip_iterations == 10 and m.opt.impratio == 10.0
    with pytest.raises(AssertionError):
        RUN.with_noslip(xml, 10)                      # refuses a second insertion


def test_contacts_match_mj_contactForce():
    xml = ('<mujoco><option cone="elliptic" impratio="10"/><worldbody><geom type="plane" size="1 1 .1"/>'
           '<body pos="0 0 .06"><freejoint/><geom type="box" size=".05 .05 .05" mass=".1" friction=".2 .005 .0001"/>'
           '</body></worldbody></mujoco>')
    m = mujoco.MjModel.from_xml_string(xml)
    d = mujoco.MjData(m)
    d.qvel[0] = 0.2
    for _ in range(100):
        mujoco.mj_step(m, d)
    c = RUN.contacts(m, d)
    assert d.ncon > 0
    assert RUN.check_contacts_against_mujoco(m, d, c) == 0.0
    u = RUN.cone_use(c)
    assert np.all(u >= 0) and np.all(u <= 1.0 + 1e-6)


@pytest.mark.parametrize("rho,ev,want", [(0.1, False, "suppressed"), (0.25, False, "suppressed"),
                                         (0.3, False, "intermediate"), (0.5, False, "persists"),
                                         (0.1, True, "persists"), (None, True, "persists")])
def test_label(rho, ev, want):
    assert AN.label(rho, ev) == want


def _m(label=None, rho=None, ev=False, piece="cubie_nnp"):
    return {"label": label, "rho": rho, "has_event": ev, "leading": {"piece": piece}}


def _full(v1, v2, quiet_ev=False):
    m = {}
    for i, c in enumerate(AN.SLIP):
        m[("V1", c)] = v1[i]
        m[("V2", c)] = v2[i]
    for c in AN.QUIET:
        m[("V1", c)] = _m(ev=quiet_ev)
        m[("V2", c)] = _m()
    return m


def test_rule_outcomes():
    supp = [_m("suppressed", 0.05)] * 6
    v1_low = [_m("suppressed", 0.2)] * 5 + [_m("persists", None, True)]
    assert AN.rule(_full(v1_low, supp))["outcome"].startswith("1")
    assert AN.rule(_full(v1_low, supp, quiet_ev=True))["outcome"].startswith("3")
    pers = [_m("persists", 1.0, True)] * 6
    assert AN.rule(_full(pers, pers))["outcome"].startswith("2")
    assert AN.rule(_full(pers, supp))["outcome"].startswith("3")
    assert AN.rule({})["outcome"] is None


def test_q3_labels():
    m = {}
    for c in AN.SLIP:
        m[("G1", c)] = _m(ev=False)
        m[("G2", c)] = _m(ev=True, piece="cubie_nnn")
        m[("S1", c)] = _m(ev=True, piece="cubie_0np")
    assert AN.q3(m)["labels"] == ["gravity-linked"]
    for c in AN.SLIP:
        m[("G1", c)] = _m(ev=True)
        m[("G2", c)] = _m(ev=True, piece="cubie_0np")
        m[("S1", c)] = _m(ev=True, piece="cubie_ppp")
    assert AN.q3(m)["labels"] == ["setup-linked"]
    for c in AN.SLIP:
        m[("S1", c)] = _m(ev=True, piece="cubie_pnp")
    assert AN.q3(m)["labels"] == ["not explained"]
    assert AN.in_uf_row("cubie_0np") and not AN.in_uf_row("cubie_npp") and AN.in_d_layer("cubie_pnn")


EXPECTED = {"C1": ("cubie_nnp", "U", 15.30), "C2": ("cubie_0np", "U", 15.10), "C3": ("cubie_0np", "U", 1.02),
            "C4": ("cubie_pnp", "F", 13.88), "C5": ("cubie_nnp", "U", 5.27), "C6": ("cubie_pnp", "U", 7.30),
            "Q1": ("cubie_0np", "U", 60.0), "Q2": ("cubie_npn", "L", 60.0)}


@pytest.mark.parametrize("case", list(EXPECTED))
def test_references_match_protocol_table(case):
    r = AN.reference(case)
    piece, axis, t = EXPECTED[case]
    assert (r["piece"], r["axis"]) == (piece, axis)
    assert abs(r["t_ref_s"] - t) <= 0.0126            # the table rounds to 2 decimals (samples every 25 ms)
    if case.startswith("C"):
        assert r["event_size_deg"] >= 0.2
    else:
        assert AN.leading(AN.committed(case))["size_deg"] < 0.05
