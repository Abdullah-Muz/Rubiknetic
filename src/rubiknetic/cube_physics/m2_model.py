"""M2 — switched-weld cube model (experiments/PHASE_1_M2_PREREGISTRATION.md, section 1).

The geometry, cubie bodies, joints and pad rig are M1's (``build_m1_xml``, unchanged), built with
``radial_preload = 0`` (rigid radius, no radial slide). Equality WELDS are added:

* ``w_<cubie>_core``: each of the 20 non-centre cubies → core (initially active);
* ``w_<cubie>_<centre>``: 20 × 6 cubie → centre welds (initially inactive), because a cubie can end up in any face
  layer;
* ``w_<centre>_core``: each of the 6 centres → core (initially active).

That makes 146 welds. The switch manager (``switching.py``) moves one layer at a time between "welded to core" and
"welded to its centre", always re-anchoring at the CURRENT relative pose.
"""

from __future__ import annotations

from dataclasses import dataclass

from rubiknetic.cube_logic.geometric import HOME_POSITIONS

from .m1_model import M1Params, build_m1_xml, cubie_name

CENTRES = [h for h in HOME_POSITIONS if sum(map(abs, h)) == 1]
MOVABLE = [h for h in HOME_POSITIONS if sum(map(abs, h)) >= 2]


@dataclass(frozen=True)
class WeldParams:
    """Weld constraint parameters (pre-registration section 1)."""

    solref: tuple[float, float] = (0.001, 1.0)
    solimp: tuple[float, float, float] = (0.99, 0.999, 0.0001)


def weld_name(body: str, anchor: str) -> str:
    return f"w_{body}_{anchor}"


def m2_params(**overrides) -> M1Params:
    """M1 parameters with rigid radius (``radial_preload = 0``), as frozen for M2."""
    return M1Params(**{"radial_preload": 0.0, **overrides})


def build_m2_xml(p: M1Params | None = None, weld: WeldParams | None = None) -> str:
    p = p or m2_params()
    if p.radial_preload != 0.0:
        raise ValueError("M2 is frozen with radial_preload = 0 (rigid radius)")
    weld = weld or WeldParams()
    xml = build_m1_xml(p)
    sr = " ".join(f"{x:g}" for x in weld.solref)
    si = " ".join(f"{x:g}" for x in weld.solimp)
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
