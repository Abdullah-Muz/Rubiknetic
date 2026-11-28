"""D25 equivalence part 1 (UNSCORED; seeds 29xxx; no simulation steps): is FastApply bit-identical to the original?

A. Splines: FusedSplines.ev vs RectBivariateSpline.ev (value, d/drho, d/dz) for the four M7 near-field tables at
   random points across the table domain, at rho = 0, at the knots and at the domain edges.
B. Random poses: the G1 M7 cube model (built by G1's runner chain, no step taken) is posed by random layer turns and
   per-cubie tilts (mj_kinematics only, so no callback runs); two fresh MagnetSystems on the same tables, one with
   the original apply and one routed to FastApply, are called on the same pose sequence. Compared bit for bit: the
   generalized force added to qfrc_passive, the per-magnet forces / torques / energy (RecordingMagnetSystem.last),
   and the stats. Two pose sequences: large random poses (neighbour list rebuilt at almost every call) and small
   steps (list kept between calls).
Every FastApply variant (spline scipy / direct / fused; scatter and body blas / bincount) is tested.
Writes results/equivalence_poses.json."""
from __future__ import annotations


import json
import sys
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scenes  # noqa: E402
import fast_magnets as FM  # noqa: E402

from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml, cubie_name  # noqa: E402


def ulp_diff(a, b):
    a, b = np.asarray(a, float).ravel(), np.asarray(b, float).ravel()
    same = (a == b)
    rel = np.abs(a - b) / np.maximum(np.maximum(np.abs(a), np.abs(b)), 1e-300)
    return {"n": int(a.size), "n_bit_equal": int(np.sum(same)), "max_abs": float(np.max(np.abs(a - b), initial=0.0)),
            "max_rel": float(np.max(rel, initial=0.0))}


def spline_test(splines, rng):
    fs = FM.FusedSplines(list(splines))
    tx0, ty = splines[0].tck[0], splines[0].tck[1]
    rmax, zlo, zhi = tx0[-1], ty[0], ty[-1]
    pts = [(rng.uniform(0, rmax, 20000), rng.uniform(zlo, zhi, 20000)),
           (np.zeros(200), rng.uniform(zlo, zhi, 200)),
           (rng.uniform(0, rmax, 200), np.full(200, zlo))]
    knots = np.unique(np.concatenate([s.tck[0] for s in splines]))
    knots = knots[knots >= 0]
    pts.append((np.repeat(knots, 5), rng.uniform(zlo, zhi, 5 * len(knots))))
    pts.append((rng.uniform(0, rmax, len(ty) * 5), np.repeat(ty, 5)))
    x = np.concatenate([p[0] for p in pts])
    y = np.concatenate([p[1] for p in pts])
    v, dx, dy = fs.ev(x, y)
    out = {}
    for q, s in enumerate(splines):
        for name, mine, ref in (("value", v[q], s.ev(x, y)), ("d_drho", dx[q], s.ev(x, y, dx=1)),
                                ("d_dz", dy[q], s.ev(x, y, dy=1))):
            out[f"spline{q}_{name}"] = ulp_diff(mine, ref)
    return out


def c_port_checks(rng):
    """Could a C port reproduce numpy's arithmetic bit for bit? (i) numpy's float64 power (r**3, r**4, t**3..t**5;
    numpy may dispatch to SIMD code) vs the C library pow (math.pow), elementwise, on the value ranges the force law
    sees. (ii) numpy's sqrt and division are IEEE correctly rounded, so they are not tested."""
    import math
    out = {}
    for name, lo, hi, e in (("r**3", 0.002, 0.03, 3), ("r**4", 0.002, 0.03, 4), ("t**3", 0, 1, 3), ("t**4", 0, 1, 4),
                            ("t**5", 0, 1, 5)):
        x = rng.uniform(lo, hi, 200000)
        a = x ** e
        b = np.array([math.pow(v, e) for v in x])
        out[name] = ulp_diff(a, b)
    return out


def random_layer_pose(m, d, rng, big: bool, base_q=None):
    """Random layer rotations (big) or a small random step from base_q; per-cubie tilts; kinematics only."""
    if base_q is not None:
        d.qpos[:] = base_q
    else:
        mujoco.mj_resetData(m, d)
    if big:
        for axis in range(3):
            for layer in (-1, 1):
                ang = rng.uniform(-np.pi / 4, np.pi / 4) if rng.random() < 0.5 else rng.choice([0, np.pi / 2])
                rot_layer(m, d, axis, layer, ang)
    for h in HOME_POSITIONS:
        jid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, cubie_name(h) + "_j")
        if jid < 0 or m.jnt_type[jid] != mujoco.mjtJoint.mjJNT_BALL:
            continue
        a = m.jnt_qposadr[jid]
        qa = np.zeros(4)
        tilt = np.radians(rng.uniform(0, 3.0 if big else 0.05))
        mujoco.mju_axisAngle2Quat(qa, _unit(rng.normal(size=3)), tilt)
        qn = np.zeros(4)
        mujoco.mju_mulQuat(qn, qa, d.qpos[a:a + 4].copy())
        d.qpos[a:a + 4] = qn / np.linalg.norm(qn)
    mujoco.mj_kinematics(m, d)
    mujoco.mj_comPos(m, d)                      # mj_applyFT needs the com-based quantities (subtree_com, cdof)


def _unit(v):
    return v / np.linalg.norm(v)


def rot_layer(m, d, axis, layer, ang):
    n = np.zeros(3)
    n[axis] = 1.0
    qa = np.zeros(4)
    mujoco.mju_axisAngle2Quat(qa, n, ang)
    for h in HOME_POSITIONS:
        if h[axis] != layer:
            continue
        jid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, cubie_name(h) + "_j")
        if jid < 0:
            continue
        a = m.jnt_qposadr[jid]
        if m.jnt_type[jid] == mujoco.mjtJoint.mjJNT_BALL:
            qn = np.zeros(4)
            mujoco.mju_mulQuat(qn, qa, d.qpos[a:a + 4].copy())
            d.qpos[a:a + 4] = qn
        elif m.jnt_type[jid] == mujoco.mjtJoint.mjJNT_HINGE and abs(m.jnt_axis[jid] @ n) > 0.5:
            d.qpos[a] += ang * float(np.sign(m.jnt_axis[jid] @ n))


def pose_test(m, mp, p, tables, variants, rng_seed, n_poses, big):
    E7, _ = scenes.g1_modules()
    RMS = E7.M4.RecordingMagnetSystem
    rng = np.random.default_rng(rng_seed)
    dA, dB = mujoco.MjData(m), mujoco.MjData(m)
    msA = RMS(m, p.pitch, p.gap, mp, tables=tables)
    systems = []
    for kw in variants:
        msB = RMS(m, p.pitch, p.gap, mp, tables=tables)
        systems.append((kw, msB, FM.FastApply(msB, **kw)))
    res = {json.dumps(kw): {"qfrc": [], "F": [], "T": [], "U_equal": 0, "stats_equal": True} for kw in variants}
    base = None
    worst = {}
    for t in range(n_poses):
        random_layer_pose(m, dA, rng, big, base)
        if not big:
            base = dA.qpos.copy()
        dA.qfrc_passive[:] = 0.0
        msA.apply(m, dA)
        for kw, msB, fa in systems:
            dB.qpos[:] = dA.qpos
            mujoco.mj_kinematics(m, dB)
            mujoco.mj_comPos(m, dB)
            dB.qfrc_passive[:] = 0.0
            fa.apply(m, dB)
            key = json.dumps(kw)
            r = res[key]
            r["qfrc"].append(ulp_diff(dB.qfrc_passive, dA.qfrc_passive))
            r["F"].append(ulp_diff(msB.last[1], msA.last[1]))
            r["T"].append(ulp_diff(msB.last[2], msA.last[2]))
            r["U_equal"] += int(msB.last[3] == msA.last[3])
            r["stats_equal"] &= (msB.stats == msA.stats)
    out = {}
    for key, r in res.items():
        agg = {}
        for name in ("qfrc", "F", "T"):
            L = r[name]
            agg[name] = {"n_values": sum(x["n"] for x in L), "n_bit_equal": sum(x["n_bit_equal"] for x in L),
                         "max_abs": max(x["max_abs"] for x in L), "max_rel": max(x["max_rel"] for x in L)}
        agg["U_bit_equal_calls"] = r["U_equal"]
        agg["stats_equal"] = bool(r["stats_equal"])
        agg["all_bit_identical"] = all(agg[nm]["n_values"] == agg[nm]["n_bit_equal"] for nm in ("qfrc", "F", "T")) \
            and r["U_equal"] == n_poses and agg["stats_equal"]
        out[key] = agg
    out["_orig_stats"] = msA.stats
    return out


def main():
    E7, scored = scenes.g1_modules()
    M4, R = E7.M4, E7.R
    E7.install(E7.EDGE_R, E7.NOSLIP)
    M4.configure_process()
    mp = R.magnet_params_for({})
    tables = M4._tables_for(mp)
    rng = np.random.default_rng(29501)
    res = {"splines": spline_test(tables, rng)}
    res["splines_all_bit_identical"] = all(v["n"] == v["n_bit_equal"] for v in res["splines"].values())
    p = M1Params(**{**M4.BASE_OVERRIDES})
    m = M4._compile_paused(scored.build_m1_xml(scored.params_for(scored.draw_setup(29502))))
    mujoco.set_mjcb_passive(None)
    variants = [dict(spline="direct", scatter="blas", body="blas"),        # "tuned" (the candidate)
                dict(spline="scipy", scatter="blas", body="blas"),
                dict(spline="fused", scatter="blas", body="blas"),
                dict(spline="direct", scatter="bincount", body="blas"),
                dict(spline="direct", scatter="bincount", body="bincount")]  # "perturbed"
    res["c_port_checks"] = c_port_checks(np.random.default_rng(29506))
    res["poses_big"] = pose_test(m, mp, p, tables, variants, 29503, 300, True)
    res["poses_small_steps"] = pose_test(m, mp, p, tables, variants, 29504, 300, False)
    res["model"] = {"nv": int(m.nv), "nbody": int(m.nbody), "gap": p.gap, "pitch": p.pitch,
                    "noslip": int(m.opt.noslip_iterations)}
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "equivalence_poses.json").write_text(json.dumps(res, indent=1, default=float))
    print("c port checks (numpy power vs C pow):", json.dumps(res["c_port_checks"]))
    print("splines all bit-identical:", res["splines_all_bit_identical"])
    for k, v in res["splines"].items():
        if v["n"] != v["n_bit_equal"]:
            print("  spline mismatch", k, v)
    for part in ("poses_big", "poses_small_steps"):
        print(part, "orig stats", res[part]["_orig_stats"])
        for key, agg in res[part].items():
            if key.startswith("_"):
                continue
            print(f"  {key}: bit-identical={agg['all_bit_identical']} qfrc {agg['qfrc']} F max_rel "
                  f"{agg['F']['max_rel']:.3g} T max_rel {agg['T']['max_rel']:.3g} U eq {agg['U_bit_equal_calls']} "
                  f"stats {agg['stats_equal']}")


if __name__ == "__main__":
    main()
