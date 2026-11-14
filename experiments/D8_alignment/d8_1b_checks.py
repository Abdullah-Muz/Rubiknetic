"""D8-1b model checks V3-V6 (UNSCORED; must pass before any D8-1b trial). See D8_1b_DESIGN_PROPOSAL.md §5.

V3  accuracy: the runtime hybrid force law vs the fine charge model (full quadrature, arbitrary orientation),
    (a) for one facing pair over gap 0.5-1.5 mm and lateral offset 0-6 mm, and (b) for the whole 48-magnet cube
    at home, with the R layer turned 2 deg, and at 20 deg. Criteria: force error <= 5 % of the aligned facing-pair
    normal force at the nominal gap; per-magnet torque error <= max(5 % of the largest fine torque in the set,
    2e-5 N m). The torque criterion was added on 2026-11-14 after the first full run showed per-magnet torque
    errors (~1e-3 N m) that the force-only criterion missed.
V4  Newton's third law and angular momentum: sum F = 0 and sum (T + p x F) = 0 over random perturbed cube states.
V5  energy conservation inside MuJoCo: the R layer turns as one rigid body on its centre hinge, every other piece
    fixed; contacts, gravity, damping and friction off; R layer released 3 deg off square; RK4 at 0.5 ms. Criterion: max |E(t) - E0| <= 1 % of the magnet energy exchanged. Also reported for
    the operational integrator (implicitfast).
V6  the callback depends only on body poses: changing ctrl, time, qvel and act leaves the magnet forces identical.
Also: a near-pair survey over a full R turn (must show no perpendicular pair within R2 and no clamped |z|), and
idle throughput with and without magnets.
Usage (WSL): ~/.venvs/rubiknetic/bin/python experiments/D8_alignment/d8_1b_checks.py
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).parent))
from magnet_force import MU0, disc_points  # noqa: E402
from magnets import MagnetParams, MagnetSystem, correction_spline, pair_forces  # noqa: E402

from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml, cubie_name  # noqa: E402

OUT = Path(__file__).parent / "results"
CACHE = OUT / "tables"
MP = MagnetParams()   # nominal: 4 x 2 mm N35, wall 0.4 mm


def fine_pair(mp: MagnetParams, p1, n1, p2, n2, n_r: int, n_phi: int):
    """Fine charge model: force and torque (about p2) on magnet 2, and the pair energy."""
    a, L = mp.diameter / 2, mp.length
    sigma = mp.moment / (np.pi * a * a * L)
    pts, w = disc_points(a, n_r, n_phi)

    def faces(p, n):
        u = np.cross(n, [1.0, 0, 0] if abs(n[0]) < 0.9 else [0, 1.0, 0])
        u /= np.linalg.norm(u)
        v = np.cross(n, u)
        out = []
        for sgn in (+1.0, -1.0):
            c = p + sgn * L / 2 * n
            out.append((c + pts[:, :1] * u + pts[:, 1:] * v, sgn))
        return out

    F, T, U = np.zeros(3), np.zeros(3), 0.0
    for x1, q1 in faces(np.asarray(p1, float), np.asarray(n1, float)):
        for x2, q2 in faces(np.asarray(p2, float), np.asarray(n2, float)):
            d = x2[None, :, :] - x1[:, None, :]
            r = np.linalg.norm(d, axis=2)
            ww = w[:, None] * w[None, :]
            f = (q1 * q2 * ww / r ** 3)[..., None] * d          # force on the charges of magnet 2
            F += f.sum(axis=(0, 1))
            T += np.cross(x2 - p2, f.sum(axis=0)).sum(axis=0)
            U += q1 * q2 * float(np.sum(ww / r))
    k = MU0 / (4 * np.pi) * sigma * sigma
    return k * F, k * T, k * U


def hybrid_pair(mp, spline, p1, n1, p2, n2):
    p = np.array([p1, p2], float)
    n = np.array([n1, n2], float)
    F, T, U = pair_forces(mp, spline, np.array([0]), np.array([1]), p, n)
    return F[1], T[1], U


def build(mp1: M1Params) -> tuple[mujoco.MjModel, mujoco.MjData]:
    m = mujoco.MjModel.from_xml_string(build_m1_xml(mp1))
    return m, mujoco.MjData(m)


def turn_layer(m, d, axis: int, sign: int, deg: float) -> None:
    """Kinematic setup only (checks, not trials): rotate the layer {home[axis] == sign} by deg about that axis."""
    ax = np.zeros(3)
    ax[axis] = 1.0
    q = Rotation.from_rotvec(np.radians(deg) * ax).as_quat()  # x y z w
    for h in HOME_POSITIONS:
        if h[axis] != sign:
            continue
        j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, cubie_name(h) + "_j")
        if j < 0:            # piece without its own joint (V5 rigid-layer model): it moves with its parent
            continue
        a = m.jnt_qposadr[j]
        if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_BALL:
            d.qpos[a:a + 4] = [q[3], q[0], q[1], q[2]]
        else:
            d.qpos[a] = np.radians(deg) * np.sign(np.dot(h, ax))


def v3(spline) -> dict:
    res = {"pair": [], "cube": []}
    L = MP.length
    Fn_nom = abs(fine_pair(MP, [0, 0, 0], [0, 0, 1], [0, 0, L + 0.001], [0, 0, 1], 16, 48)[0][2])
    res["Fn_nominal_N"] = Fn_nom
    worst = 0.0
    for g in (0.0005, 0.001, 0.0015):
        for s in np.linspace(0, 0.006, 13):
            p2, n = [s, 0, L + g], [0, 0, 1]
            ff, tf, _ = fine_pair(MP, [0, 0, 0], n, p2, n, 16, 48)
            fh, th, _ = hybrid_pair(MP, spline, [0, 0, 0], n, p2, n)
            err = float(np.linalg.norm(fh - ff) / Fn_nom)
            worst = max(worst, err)
            res["pair"].append({"gap_mm": g * 1e3, "offset_mm": s * 1e3, "fine_N": ff.tolist(), "hybrid_N": fh.tolist(),
                                "err_rel_Fn": err, "fine_T_Nm": tf.tolist(), "hybrid_T_Nm": th.tolist(),
                                "T_err_Nm": float(np.linalg.norm(th - tf))})
    res["pair_worst_err"] = worst
    t_scale = max(np.linalg.norm(c["fine_T_Nm"]) for c in res["pair"])
    res["pair_worst_T_err_Nm"] = max(c["T_err_Nm"] for c in res["pair"])
    res["pair_T_tol_Nm"] = max(0.05 * t_scale, 2e-5)
    # whole cube
    m, d = build(M1Params(radial_preload=0.0, rig=False))
    ms = MagnetSystem(m, 0.019, M1Params().gap, MP, CACHE)
    for deg in (0.0, 2.0, 20.0):
        mujoco.mj_resetData(m, d)
        turn_layer(m, d, 0, 1, deg)
        mujoco.mj_kinematics(m, d)
        p, n = ms.world(d.xpos, d.xmat)
        Fh, Th, Uh = ms.forces(p, n)
        Ff, Tf = np.zeros_like(Fh), np.zeros_like(Th)
        Uf = 0.0
        for i, j in zip(ms.ii, ms.jj):
            near = np.linalg.norm(p[j] - p[i]) < MP.r2
            f, t, u = fine_pair(MP, p[i], n[i], p[j], n[j], *((16, 48) if near else (6, 16)))
            # torque on i about p_i: total angular momentum balance gives T_i = -(T_j + (p_j - p_i) x f)
            Ff[j] += f
            Ff[i] -= f
            Tf[j] += t
            Tf[i] += -(t + np.cross(p[j] - p[i], f))
            Uf += u
        ferr = float(np.abs(Fh - Ff).max() / Fn_nom)
        res["cube"].append({"R_turn_deg": deg, "max_force_err_rel_Fn": ferr,
                            "max_torque_err_Nm": float(np.abs(Th - Tf).max()),
                            "max_torque_fine_Nm": float(np.abs(Tf).max()), "energy_hybrid_J": Uh, "energy_fine_J": Uf})
    t_cube = max(max(c["max_torque_fine_Nm"] for c in res["cube"]) * 0.05, 2e-5)
    res["cube_T_tol_Nm"] = t_cube
    res["pass"] = bool(worst <= 0.05 and all(c["max_force_err_rel_Fn"] <= 0.05 for c in res["cube"])
                       and res["pair_worst_T_err_Nm"] <= res["pair_T_tol_Nm"]
                       and all(c["max_torque_err_Nm"] <= t_cube for c in res["cube"]))
    return res


def v4(spline) -> dict:
    m, d = build(M1Params(radial_preload=0.0, rig=False))
    ms = MagnetSystem(m, 0.019, M1Params().gap, MP, CACHE)
    rng = np.random.default_rng(81)
    worst_f, worst_l = 0.0, 0.0
    for _ in range(20):
        mujoco.mj_resetData(m, d)
        for k in range(m.njnt):
            a = m.jnt_qposadr[k]
            if m.jnt_type[k] == mujoco.mjtJoint.mjJNT_BALL:
                q = Rotation.from_rotvec(np.radians(rng.normal(0, 2.0, 3))).as_quat()
                d.qpos[a:a + 4] = [q[3], q[0], q[1], q[2]]
            elif m.jnt_type[k] == mujoco.mjtJoint.mjJNT_HINGE:
                d.qpos[a] = np.radians(rng.normal(0, 2.0))
        turn_layer(m, d, rng.integers(3), int(rng.choice([-1, 1])), float(rng.uniform(0, 90)))
        mujoco.mj_kinematics(m, d)
        p, n = ms.world(d.xpos, d.xmat)
        F, T, _ = ms.forces(p, n)
        scale = np.abs(F).sum()
        worst_f = max(worst_f, float(np.linalg.norm(F.sum(axis=0)) / scale))
        worst_l = max(worst_l, float(np.linalg.norm((T + np.cross(p, F)).sum(axis=0)) / (scale * 0.03)))
    return {"max_rel_net_force": worst_f, "max_rel_net_angular": worst_l, "pass": bool(worst_f < 1e-9 and worst_l < 1e-9)}


def build_r_hinge_model(mp1: M1Params) -> tuple[mujoco.MjModel, mujoco.MjData]:
    """V5 test model: the R layer turns as ONE rigid body on the R centre's hinge (+x); every other piece is fixed to
    the core. Without contacts, pieces that are free to move independently and held only by attracting magnets have
    no stable equilibrium (Earnshaw's theorem): the first two V5 designs (free ball joints, then one hinge per piece)
    collapsed. A rigid layer turning about its axis keeps every across-boundary facing pair coplanar, which is the
    motion the detent must conserve energy for. All body frames sit at the cube centre, so nesting changes no geometry."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(build_m1_xml(mp1))
    core = root.find("./worldbody/body[@name='core']")
    centre = core.find(f"./body[@name='{cubie_name((1, 0, 0))}']")
    cj = centre.find("joint")
    cj.set("damping", "0")
    cj.set("frictionloss", "0")
    for h in HOME_POSITIONS:
        if h == (1, 0, 0):
            continue
        b = core.find(f"./body[@name='{cubie_name(h)}']")
        for j in b.findall("joint"):
            b.remove(j)
        if h[0] == 1:
            core.remove(b)
            centre.append(b)
    m = mujoco.MjModel.from_xml_string(ET.tostring(root, encoding="unicode"))
    assert m.nv == 1, m.nv
    return m, mujoco.MjData(m)


def v5(integrator: str, duration: float = 0.5) -> dict:
    mp1 = M1Params(radial_preload=0.0, rig=False, gravity_z=0.0, joint_damping=0.0, joint_frictionloss=0.0,
                   integrator=integrator)
    m, d = build_r_hinge_model(mp1)
    m.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_CONTACT
    m.opt.enableflags |= mujoco.mjtEnableBit.mjENBL_ENERGY
    ms = MagnetSystem(m, 0.019, mp1.gap, MP, CACHE)
    ms.install()
    try:
        turn_layer(m, d, 0, 1, 3.0)
        mujoco.mj_forward(m, d)
        E, U = [], []
        for _ in range(int(duration / m.opt.timestep)):
            mujoco.mj_step(m, d)
            u = ms.energy(d)
            U.append(u)
            E.append(d.energy[1] + d.energy[0] + u)
        E, U = np.array(E), np.array(U)
        exch = float(U.max() - U.min())
        drift = float(np.abs(E - E[0]).max())
        return {"integrator": integrator, "duration_s": duration, "energy_exchanged_J": exch, "max_drift_J": drift,
                "max_gain_J": float((E - E[0]).max()), "final_drift_J": float(E[-1] - E[0]),
                "drift_rel": drift / exch if exch > 0 else None, "stats": dict(ms.stats),
                "pass": bool(exch > 0 and drift <= 0.01 * exch)}
    finally:
        MagnetSystem.uninstall()


def v6() -> dict:
    m, d = build(M1Params(radial_preload=0.0, rig=True))
    ms = MagnetSystem(m, 0.019, M1Params().gap, MP, CACHE)
    turn_layer(m, d, 0, 1, 2.0)
    mujoco.mj_forward(m, d)   # mj_applyFT needs the com-based quantities of the position stage, not just kinematics

    def contrib():
        d.qfrc_passive[:] = 0.0
        ms.apply(m, d)
        return d.qfrc_passive.copy()

    base = contrib()
    rng = np.random.default_rng(6)
    d.ctrl[:] = rng.uniform(-1, 1, m.nu)
    d.time = 123.4
    d.qvel[:] = rng.normal(0, 1, m.nv)
    if m.na:
        d.act[:] = rng.uniform(-1, 1, m.na)
    after = contrib()
    # installed callback: qfrc_passive with minus without equals the magnet contribution
    mujoco.mj_forward(m, d)
    without = d.qfrc_passive.copy()
    ms.install()
    try:
        mujoco.mj_forward(m, d)
        with_cb = d.qfrc_passive.copy()
    finally:
        MagnetSystem.uninstall()
    return {"max_abs_magnet_qfrc": float(np.abs(base).max()),
            "max_change_from_ctrl_time_qvel_act": float(np.abs(after - base).max()),
            "installed_matches_direct": float(np.abs((with_cb - without) - base).max()),
            "pass": bool(np.abs(base).max() > 0 and np.array_equal(after, base)
                         and np.allclose(with_cb - without, base, rtol=0, atol=1e-12))}


def survey(spline) -> dict:
    m, d = build(M1Params(radial_preload=0.0, rig=False))
    ms = MagnetSystem(m, 0.019, M1Params().gap, MP, CACHE)
    near_counts, min_z, perp = [], np.inf, 0
    for deg in np.arange(0, 91, 2.5):
        mujoco.mj_resetData(m, d)
        turn_layer(m, d, 0, 1, float(deg))
        mujoco.mj_kinematics(m, d)
        p, n = ms.world(d.xpos, d.xmat)
        rv = p[ms.jj] - p[ms.ii]
        r = np.linalg.norm(rv, axis=1)
        near = r < MP.r2
        cosn = np.einsum("ij,ij->i", n[ms.ii], n[ms.jj])
        perp += int(np.sum(near & (np.abs(cosn) <= np.cos(np.radians(45)))))
        if near.any():
            z = np.abs(np.einsum("ij,ij->i", rv[near], n[ms.ii][near]))
            min_z = min(min_z, float(z.min()))
        near_counts.append(int(near.sum()))
    return {"near_pairs_per_angle": dict(zip([float(x) for x in np.arange(0, 91, 2.5)], near_counts)),
            "near_perpendicular_total": perp, "min_abs_z_mm": min_z * 1e3, "zmin_table_mm": (MP.length + 0.0001) * 1e3,
            "pass": bool(perp == 0 and min_z >= MP.length + 0.0001)}


def throughput() -> dict:
    out = {}
    for label, use in (("no_magnets", False), ("magnets", True)):
        m, d = build(M1Params(radial_preload=0.0, rig=True))
        ms = MagnetSystem(m, 0.019, M1Params().gap, MP, CACHE)
        if use:
            ms.install()
        try:
            mujoco.mj_step(m, d)
            t = time.perf_counter()
            for _ in range(2000):
                mujoco.mj_step(m, d)
            out[label] = 2000 / (time.perf_counter() - t)
        finally:
            MagnetSystem.uninstall()
    return out


def main() -> None:
    t0 = time.perf_counter()
    spline = correction_spline(MP, CACHE)
    print(f"table ready ({time.perf_counter() - t0:.0f} s)", flush=True)
    res = {"magnet_params": asdict(MP), "moment_Am2": MP.moment, "Br_T": MP.br, "mujoco": mujoco.__version__}
    res["survey"] = survey(spline)
    print("survey:", {k: v for k, v in res["survey"].items() if k != "near_pairs_per_angle"}, flush=True)
    res["V4"] = v4(spline)
    print("V4:", res["V4"], flush=True)
    res["V6"] = v6()
    print("V6:", res["V6"], flush=True)
    res["V5_rk4"] = v5("RK4")
    print("V5 RK4:", {k: v for k, v in res["V5_rk4"].items() if k != "stats"}, flush=True)
    res["V5_implicitfast"] = v5("implicitfast")
    print("V5 implicitfast:", {k: v for k, v in res["V5_implicitfast"].items() if k != "stats"}, flush=True)
    res["throughput_idle_steps_per_s"] = throughput()
    print("throughput:", res["throughput_idle_steps_per_s"], flush=True)
    res["V3"] = v3(spline)
    v = res["V3"]
    print("V3: pair worst F", round(v["pair_worst_err"], 4), "T", f'{v["pair_worst_T_err_Nm"]:.2e}/{v["pair_T_tol_Nm"]:.2e}',
          "cube", [(c["R_turn_deg"], round(c["max_force_err_rel_Fn"], 4), f'{c["max_torque_err_Nm"]:.1e}')
                   for c in v["cube"]], f'T tol {v["cube_T_tol_Nm"]:.1e}', "pass", v["pass"])
    res["all_pass"] = all(res[k]["pass"] for k in ("survey", "V3", "V4", "V5_rk4", "V6"))
    res["wall_s"] = round(time.perf_counter() - t0, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "d8_1b_checks.json").write_text(json.dumps(res, indent=1, default=float))
    print("ALL PASS" if res["all_pass"] else "NOT ALL PASS", f"wall {res['wall_s']} s")


if __name__ == "__main__":
    main()
