"""ER1 probe 5 (static, no dynamics): magnet torque about the cube centre at the aligned M5 pose, and its rotational
stiffness when (i) one piece, (ii) a corner+edge pair, (iii) a whole layer is rotated about the face axis by small
angles inside the free play (probe 4: +/-0.106 deg for a single piece). Positive stiffness = restoring.
Writes results/probe_magnet_stiffness.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import er1_probe_play as P  # noqa: E402  (aligned M5 model, set_group, names)
from rubiknetic.cube_physics.magnets import MagnetSystem  # noqa: E402

M4 = P.M5.M4
mp = P.M5.magnet_params_for({})
ms = MagnetSystem(P.m, P.p.pitch, P.p.gap, mp, tables=M4._tables_for(mp))
BN = {int(b): mujoco.mj_id2name(P.m, mujoco.mjtObj.mjOBJ_BODY, int(b)) for b in ms.bodies}


def torques():
    """Per-body magnet torque about the cube centre (world origin; core fixed at origin), N m."""
    ms.reset_neighbour_list()
    p, n = ms.world(P.d.xpos, P.d.xmat)
    F, T, U = ms.forces(p, n)
    Tc = ms.body_sum @ (T + np.cross(p, F))
    return {BN[int(b)]: Tc[k] for k, b in enumerate(ms.bodies)}, U


CASES = [
    ("edge n0p", ["cubie_n0p"]),
    ("corner nnp", ["cubie_nnp"]),
    ("pair nnp + n0p", ["cubie_nnp", "cubie_n0p"]),
    ("whole U layer", [n for n in P.NAMES if P.HOME[n][2] == 1]),
]
if __name__ == "__main__":
    P.set_group([], (0, 0, 1), 0.0)
    print("cubie body origin |xpos| max (m):", float(np.abs(P.d.xpos[ms.bodies]).max()))
    T0, U0 = torques()
    mag = {k: float(np.linalg.norm(v) * 1e3) for k, v in T0.items()}
    print(f"aligned pose: |torque about centre| per body (mN m): max {max(mag.values()):.4f}, median {np.median(list(mag.values())):.4f}")
    out = {"aligned_torque_mNm": {k: (v * 1e3).tolist() for k, v in T0.items()}, "cases": []}
    for label, grp in CASES:
        rows = []
        for deg in (-0.1, -0.05, -0.02, 0.0, 0.02, 0.05, 0.1):
            P.set_group(grp, (0, 0, 1), deg)
            T, U = torques()
            tz = float(sum(T[n][2] for n in grp if n in T))
            rows.append({"deg": deg, "group_torque_z_mNm": tz * 1e3, "energy_J": U - U0, "min_dist_mm": float(P.min_dist(grp)[0] * 1e3) if len(grp) < 8 else None})
        k = np.polyfit([r["deg"] for r in rows], [r["group_torque_z_mNm"] for r in rows], 1)[0]
        stiff = -k * 180 / np.pi    # restoring stiffness, mN m / rad (positive = restoring)
        out["cases"].append({"case": label, "group": grp, "rows": rows, "restoring_stiffness_mNm_per_rad": stiff})
        print(f"{label:18s} torque_z at -0.1/-0.05/0/+0.05/+0.1 deg: "
              + " ".join(f"{r['group_torque_z_mNm']:+.3f}" for r in rows if r['deg'] in (-0.1, -0.05, 0.0, 0.05, 0.1))
              + f"  mN m; restoring stiffness {stiff:+.1f} mN m/rad ({'RESTORING' if stiff > 0 else 'DESTABILISING'})")
    (HERE / "results" / "probe_magnet_stiffness.json").write_text(json.dumps({"env": P.D10.environment(), **out}, indent=1))
