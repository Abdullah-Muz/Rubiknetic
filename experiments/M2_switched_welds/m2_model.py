"""M2 — switched-weld cube (UNSCORED prototype, approved comparison model P-14).

Geometry, cubie bodies, joints and the pad rig are M1's (build_m1_xml, unchanged). Added: one
equality WELD per (cubie, anchor) pair, where the anchor is the fixed core or one of the 6 centres:
  w_<cubie>_core       : 20 non-centre cubies -> core
  w_<cubie>_<centre>   : 20 x 6 cubie -> centre welds (a cubie can end up in any face's layer)
  w_<centre>_core      : 6 centre hinges -> core
Initially every cubie and centre is welded to the core (shell rigid). The switch manager
(switching.py) moves exactly one layer at a time from "welded to core" to "welded to its centre",
and back, always re-anchoring at the CURRENT relative pose (zero violation). A switch never
targets an angle and never moves a body.
"""
from __future__ import annotations

from rubiknetic.cube_logic.geometric import HOME_POSITIONS
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml, cubie_name

CENTRES = [h for h in HOME_POSITIONS if sum(map(abs, h)) == 1]
MOVABLE = [h for h in HOME_POSITIONS if sum(map(abs, h)) >= 2]


def weld_name(body: str, anchor: str) -> str:
    return f"w_{body}_{anchor}"


def build_m2_xml(p: M1Params | None = None, weld_solref=(0.001, 1.0), weld_solimp=(0.99, 0.999, 0.0001)) -> str:
    p = p or M1Params(radial_preload=0.0)
    xml = build_m1_xml(p)
    sr = " ".join(f"{x:g}" for x in weld_solref)
    si = " ".join(f"{x:g}" for x in weld_solimp)
    lines = []
    for h in MOVABLE:
        b = cubie_name(h)
        lines.append(f'    <weld name="{weld_name(b, "core")}" body1="{b}" body2="core" relpose="0 0 0 1 0 0 0" '
                     f'active="true" solref="{sr}" solimp="{si}"/>')
        for c in CENTRES:
            cn = cubie_name(c)
            lines.append(f'    <weld name="{weld_name(b, cn)}" body1="{b}" body2="{cn}" relpose="0 0 0 1 0 0 0" '
                         f'active="false" solref="{sr}" solimp="{si}"/>')
    for c in CENTRES:
        cn = cubie_name(c)
        lines.append(f'    <weld name="{weld_name(cn, "core")}" body1="{cn}" body2="core" relpose="0 0 0 1 0 0 0" '
                     f'active="true" solref="{sr}" solimp="{si}"/>')
    eq = "  <equality>\n" + "\n".join(lines) + "\n  </equality>\n"
    return xml.replace("  <actuator>", eq + "  <actuator>", 1)
