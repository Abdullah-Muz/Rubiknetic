"""Fast geometry-only forgiveness analyser for D5 (UNSCORED; poses set for geometry queries only).

U is misaligned by delta (all U-layer pieces, including the U∩R ones, rotated about z), then the R
layer is swept 0..90 deg about x. Every penetrating contact between an R-layer body and a non-R body
is classified:
  * against a U-layer piece (it could be pushed back): CAM if the contact force on that piece gives a
    restoring torque about z (toward delta = 0) that is large relative to the torque it puts on the R
    layer, otherwise U-BLOCK;
  * against a piece that is in neither layer: HARD block (nothing can yield).
Report per delta: max penetration by class and the worst cam ratio. A forgiving design shows no HARD
penetration and cam ratios above ~tan(friction angle) for all deltas up to the target.
Usage: uv run python experiments/D5_follower_cube/cam_analyser.py [d5 k=v ...]
"""
from __future__ import annotations

import sys

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from cube_d5 import D5Params  # noqa: E402
from kin_check import Poser, layer, make  # noqa: E402

DELTAS = [-8, -5, -3, -2, -1, 1, 2, 3, 5, 8]
PHIS = list(range(0, 91, 3))


def analyse(p: D5Params) -> dict:
    m, d, info = make(p)
    P = Poser(m, d, p)
    U, R = set(layer("U")), set(layer("R"))
    zhat, xhat = np.array([0, 0, 1.0]), np.array([1.0, 0, 0])
    bname = lambda g: mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, m.geom_bodyid[g])  # noqa: E731
    out = {}
    for delta in DELTAS:
        res = {"hard": 0.0, "ublock": 0.0, "cam": 0.0, "worst_ratio": np.inf, "hard_where": None, "ublock_where": None}
        Ru = Rotation.from_rotvec(np.radians(delta) * zhat).as_matrix()
        for phi in PHIS:
            P.reset()
            Rr = Rotation.from_rotvec(-np.radians(phi) * xhat).as_matrix()
            P.rotate([n for n in U if n not in R], Ru)
            P.rotate([n for n in R if n not in U], Rr)
            P.rotate([n for n in R if n in U], Rr @ Ru)
            mujoco.mj_kinematics(m, d)
            mujoco.mj_collision(m, d)
            for i in range(d.ncon):
                c = d.contact[i]
                if c.dist >= 0:
                    continue
                b1, b2 = bname(c.geom1), bname(c.geom2)
                in1, in2 = b1 in R, b2 in R
                if in1 == in2:
                    continue
                other, F_other = (b2, c.frame[:3]) if in1 else (b1, -c.frame[:3])  # force on the non-R body
                mine = b1 if in1 else b2  # the R-layer body
                pen = -c.dist * 1000
                if mine in U and other not in U:
                    # the R-side piece is a misaligned U∩R piece: can the contact twist IT back about z
                    # (its misalignment axis, carried round by the R rotation)?
                    p_ = c.pos
                    zc = Rr @ zhat  # the U∩R piece's misalignment axis after the R rotation
                    restoring = -np.sign(delta) * (np.cross(p_, -F_other) @ zc)
                    if restoring / max(1e-9, abs(np.cross(p_, -F_other) @ xhat)) > 0.2:
                        res["cam"] = max(res["cam"], pen)
                        continue
                if other in U:
                    p_ = c.pos
                    tau_u = np.cross(p_, F_other) @ zhat           # torque on the U layer about z
                    tau_r = np.cross(p_, -F_other) @ xhat          # torque on the R layer about x
                    restoring = -np.sign(delta) * tau_u              # >0 pushes U back toward square
                    resist = max(1e-9, abs(tau_r))
                    ratio = restoring / resist
                    if ratio > 0.2:
                        res["cam"] = max(res["cam"], pen)
                        res["worst_ratio"] = min(res["worst_ratio"], ratio)
                    else:
                        if pen > res["ublock"]:
                            res["ublock"], res["ublock_where"] = pen, (b1[6:], b2[6:], np.round(c.pos * 1000, 1), np.round(c.frame[:3], 2), phi)
                else:
                    if pen > res["hard"]:
                        res["hard"], res["hard_where"] = pen, (b1[6:], b2[6:], np.round(c.pos * 1000, 1), np.round(c.frame[:3], 2), phi)
        out[delta] = res
    return out


def main():
    p = D5Params(bevel_body=1.0, bevel_foot=0.5, bevel_inner=1.0, gap=0.05, clearance=0.02,
                 pad_spacing_deg=14.0, sphere_spacing_mm=2.0)
    for kv in sys.argv[1:]:
        k, v = kv.split("=")
        cur = getattr(p, k)
        setattr(p, k, type(cur)(v) if not isinstance(cur, tuple) else tuple(float(x) for x in v.split(",")))
    res = analyse(p)
    print(f"bevels body/foot/inner {p.bevel_body}/{p.bevel_foot}/{p.bevel_inner}, taper {p.taper} from {p.taper_start} mm, split {p.inner_split_centre}/{p.inner_split_edge}")
    for dl, r in res.items():
        verdict = "OK (cam only)" if r["hard"] < 0.02 and r["ublock"] < 0.02 else "JAM-RISK"
        print(f"  U {dl:+3d} deg: HARD {r['hard']:5.2f} mm | U-block {r['ublock']:5.2f} mm | cam {r['cam']:5.2f} mm "
              f"(worst ratio {r['worst_ratio']:.2f}) | {verdict}")
        for key in ("hard_where", "ublock_where"):
            if r[key] is not None and r[key.split("_")[0] if key != "ublock_where" else "ublock"] >= 0.02:
                print(f"       {key}: {r[key]}")


if __name__ == "__main__":
    main()
