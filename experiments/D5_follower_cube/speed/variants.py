"""D5 speed study (UNSCORED): model variants built from cube_d5 without editing it.

A variant = D5Params overrides + MJCF option edits (applied to the generated XML string).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cube_d5 import D5Params, build_xml, build_xml_with_rig  # noqa: E402

BASE = dict(bevel_body=1.0, bevel_foot=0.5, bevel_inner=1.0, gap=0.05, clearance=0.02, spring_preload=10.0,
            spring_k=2000.0, slide_range=(-0.001, 0.0003))

# name: (D5Params overrides, option edits)
VARIANTS = {
    "base_pad10": ({}, {}),
    "pad14": ({"pad_spacing_deg": 14.0}, {}),
    "pad20": ({"pad_spacing_deg": 20.0}, {}),
    "sph2": ({"sphere_spacing_mm": 2.0}, {}),
    "sph3": ({"sphere_spacing_mm": 3.0}, {}),
    "nomulticcd": ({}, {"flags": {"multiccd": "disable"}}),
    "pyramidal": ({}, {"cone": "pyramidal"}),
    "iter30_tol1e-6_ls10": ({}, {"iterations": 30, "tolerance": "1e-6", "ls_iterations": 10}),
    "dt1ms": ({"timestep": 0.001}, {}),
    "sph2_nomulticcd": ({"sphere_spacing_mm": 2.0}, {"flags": {"multiccd": "disable"}}),
    "pad14_sph2_nomulticcd": ({"pad_spacing_deg": 14.0, "sphere_spacing_mm": 2.0}, {"flags": {"multiccd": "disable"}}),
    "pad10_sph2_nomulticcd_it30": ({"sphere_spacing_mm": 2.0},
                                   {"flags": {"multiccd": "disable"}, "iterations": 30, "tolerance": "1e-6", "ls_iterations": 10}),
    "pad14_sph2": ({"pad_spacing_deg": 14.0, "sphere_spacing_mm": 2.0}, {}),
    "sph2_footmhv48": ({"sphere_spacing_mm": 2.0}, {"foot_maxhullvert": 48}),
    "sph2_allmhv32": ({"sphere_spacing_mm": 2.0}, {"all_maxhullvert": 32}),
    "pad14_sph2_footmhv48": ({"pad_spacing_deg": 14.0, "sphere_spacing_mm": 2.0}, {"foot_maxhullvert": 48}),
    "pad12_sph2_footmhv48": ({"pad_spacing_deg": 12.0, "sphere_spacing_mm": 2.0}, {"foot_maxhullvert": 48}),
    "sph2_footmhv48_nomulticcd": ({"sphere_spacing_mm": 2.0}, {"foot_maxhullvert": 48, "flags": {"multiccd": "disable"}}),
}


def apply_options(xml: str, opt: dict) -> str:
    if "cone" in opt:
        xml = xml.replace('cone="elliptic"', f'cone="{opt["cone"]}"', 1)
    if "iterations" in opt:
        xml = xml.replace('iterations="100"', f'iterations="{opt["iterations"]}"', 1)
    if "tolerance" in opt:
        xml = xml.replace('tolerance="1e-10"', f'tolerance="{opt["tolerance"]}"', 1)
    if "ls_iterations" in opt:
        xml = xml.replace('solver="Newton"', f'solver="Newton" ls_iterations="{opt["ls_iterations"]}"', 1)
    if "foot_maxhullvert" in opt:  # inner approximation (subset hull): feet can only shrink
        import re
        xml = re.sub(r'<mesh name="(cubie_\w+_m0)" vertex=', rf'<mesh name="\1" maxhullvert="{opt["foot_maxhullvert"]}" vertex=', xml)
    if "all_maxhullvert" in opt:
        xml = xml.replace('<mesh name="cubie_', f'<mesh maxhullvert="{opt["all_maxhullvert"]}" name="cubie_')
    if "flags" in opt:
        fl = " ".join(f'{k}="{v}"' for k, v in opt["flags"].items())
        xml = xml.replace('gravity="0 0 -9.81"/>', f'gravity="0 0 -9.81">\n    <flag {fl}/>\n  </option>', 1)
    return xml


def params(name: str) -> D5Params:
    ov, _ = VARIANTS[name]
    return D5Params(**{**BASE, **ov})


def xml_for(name: str, rig: bool = True, **extra) -> str:
    ov, opt = VARIANTS[name]
    p = params(name)
    for k, v in extra.items():
        setattr(p, k, v)
    xml = build_xml_with_rig(p)[0] if rig else build_xml(p, actuated_centres=False)[0]
    return apply_options(xml, opt)
