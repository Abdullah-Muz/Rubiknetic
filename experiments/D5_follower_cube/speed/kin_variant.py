"""Geometry-only checks (rest, 6 sweeps, corner/edge capture and twist) on a speed VARIANT's own
compiled geometry, reusing kin_check helpers. UNSCORED.
Usage: uv run python experiments/D5_follower_cube/speed/kin_variant.py <variant>"""
import sys
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kin_check as kc  # noqa: E402
from variants import params, xml_for  # noqa: E402

from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES  # noqa: E402

name = sys.argv[1]
m = mujoco.MjModel.from_xml_string(xml_for(name, rig=False, margin=kc.MARGIN))
d = mujoco.MjData(m)
P = kc.Poser(m, d, params(name))
P.reset()
rest, _ = kc.min_dist(m, d, set(n for n in P.bid if n.startswith("cubie_p")), None)
allmin = min(kc.min_dist(m, d, {n})[0] for n in P.bid)
sweeps = {}
for face in FACES:
    mv = kc.layer(face)
    n = np.array(FACE_NORMAL[face], float)
    w = np.inf
    for ang in range(0, 91, 2):
        P.reset()
        P.rotate(mv, Rotation.from_rotvec(-np.radians(ang) * n).as_matrix())
        w = min(w, kc.min_dist(m, d, set(mv))[0])
    sweeps[face] = round(w, 3)
cap = {}
for nm in ("cubie_ppp", "cubie_pp0"):
    u = P.home[nm] / np.linalg.norm(P.home[nm])
    P.reset()
    P.translate(nm, u * 0.1 / 1000)
    out = kc.min_dist(m, d, {nm})[0]
    P.reset()
    P.set_rot_about_own(nm, Rotation.from_rotvec(np.radians(1.0) * u).as_matrix())
    tw = kc.min_dist(m, d, {nm})[0]
    cap[nm] = (round(out, 3), round(tw, 3))
ok = allmin > 0 and min(sweeps.values()) > 0 and all(o < 0 for o, _ in cap.values())
print(f"{name}: rest min {allmin:+.3f} mm | sweep min per face {sweeps} | outward 0.1 mm / twist 1 deg dist "
      f"{cap} | GEOMETRY {'PASS' if ok else 'FAIL'}")
