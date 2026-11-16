"""D8-1b model checks V3-V6 (UNSCORED; must pass before any D8-1b trial). See D8_1b_DESIGN_PROPOSAL.md §5.

V3  accuracy: the runtime hybrid force law vs the fine charge model (arbitrary orientation) at a finer, independent
    quadrature (32 x 96; the table uses 16 x 48), (a) for one facing pair over gap 0.5-1.5 mm and lateral offset
    0-6 mm in 0.37 mm steps (off the table's rho nodes), (b) for pairs tilted 2, 5, 7.5 and 10 deg (must pass up to 5 deg;
    the largest passing tilt is recorded as the validated range), and (c) for the whole 48-magnet cube at home, with
    the R layer turned 2 deg, and at 20 deg. (a)-(b) and the finer reference were added on 2026-11-14 after an
    independent review found the first V3 too weak. Criteria: force error <= 5 % of the aligned facing-pair
    normal force at the nominal gap; per-magnet torque error <= max(5 % of the largest fine torque in the set,
    2e-5 N m). The torque criterion was added on 2026-11-14 after the first full run showed per-magnet torque
    errors (~1e-3 N m) that the force-only criterion missed.
V4  Newton's third law and angular momentum: sum F = 0 and sum (T + p x F) = 0 over random perturbed cube states.
    For near pairs the partner torque is set from the balance, so V4 tests the far-field terms and the scatter
    bookkeeping; the split of a near pair's torque between its two magnets is tested by V3, not V4.
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
from magnets import MagnetParams, MagnetSystem, near_field_tables, pair_forces  # noqa: E402

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


REF_QUAD = (32, 96)        # V3 reference quadrature: independent of (finer than) the table's TABLE_QUAD
REF_QUAD_CUBE = (24, 72)   # whole-cube near pairs (many pairs); still finer than and different from the table's
TILTS_DEG = (2.0, 5.0, 7.5, 10.0)   # 7.5 added 2026-11-15 (M4 pre-registration draft, section 6 item 2)
TILT_REQUIRED_DEG = 5.0    # V3 must pass up to this tilt; the largest passing tilt is the validated range


def v3(spline) -> dict:
    """Revised 2026-11-14 after an independent review found the first V3 weak: its reference used the table's own
    quadrature, its offsets sat on the table's rho nodes, and no tilted pairs were tested. Criteria are unchanged
    (force error <= 5 % of the aligned nominal normal force; torque error <= max(5 % of the largest reference torque in
    the set, 2e-5 N m)); only the reference and the sample points are harder."""
    res = {"pair": [], "tilt": [], "cube": [], "ref_quad": REF_QUAD, "ref_quad_cube": REF_QUAD_CUBE}
    L = MP.length
    Fn_nom = abs(fine_pair(MP, [0, 0, 0], [0, 0, 1], [0, 0, L + 0.001], [0, 0, 1], *REF_QUAD)[0][2])
    res["Fn_nominal_N"] = Fn_nom

    def compare(rows, p2, n1, n2, **tag):
        ff, tf, _ = fine_pair(MP, [0, 0, 0], n1, p2, n2, *REF_QUAD)
        fh, th, _ = hybrid_pair(MP, spline, [0, 0, 0], n1, p2, n2)
        rows.append({**tag, "fine_N": ff.tolist(), "hybrid_N": fh.tolist(),
                     "err_rel_Fn": float(np.linalg.norm(fh - ff) / Fn_nom), "fine_T_Nm": tf.tolist(),
                     "hybrid_T_Nm": th.tolist(), "T_err_Nm": float(np.linalg.norm(th - tf))})

    # (a) parallel facing pair; offsets in 0.37 mm steps (off the 0.25 mm rho nodes, plus exactly 0 for the
    # alignment point) and gaps between the z nodes
    z_axis = [0.0, 0.0, 1.0]
    for g in (0.0005, 0.00075, 0.001, 0.00125, 0.0015):
        for s in np.arange(0.0, 0.0061, 0.00037):
            compare(res["pair"], [s, 0, L + g], z_axis, z_axis, gap_mm=g * 1e3, offset_mm=s * 1e3)
    t_scale = max(np.linalg.norm(c["fine_T_Nm"]) for c in res["pair"])
    res["pair_worst_err"] = max(c["err_rel_Fn"] for c in res["pair"])
    res["pair_worst_T_err_Nm"] = max(c["T_err_Nm"] for c in res["pair"])
    res["pair_T_tol_Nm"] = max(0.05 * t_scale, 2e-5)
    pair_ok = res["pair_worst_err"] <= 0.05 and res["pair_worst_T_err_Nm"] <= res["pair_T_tol_Nm"]
    # (b) tilted pairs at the nominal 1.0 mm gap, tilted about the offset direction and about the perpendicular
    # direction; offsets 0, 0.63, 1.37, 2.11 mm. Three cases (revision 2 added the last two): magnet 2 above and
    # tilted; magnet 1 (the frame magnet in the force law) tilted; magnet 2 below and tilted (z < 0 branch).
    # Force and torque are compared on magnet 2.
    for tilt in TILTS_DEG:
        for about in ("x", "y"):
            nt = Rotation.from_euler(about, tilt, degrees=True).apply(z_axis)
            for s in (0.0, 0.00063, 0.00137, 0.00211):
                tag = {"tilt_deg": tilt, "about": about, "offset_mm": s * 1e3}
                compare(res["tilt"], [s, 0, L + 0.001], z_axis, nt, case="upper_tilted", **tag)
                compare(res["tilt"], [s, 0, L + 0.001], nt, z_axis, case="frame_magnet_tilted", **tag)
                compare(res["tilt"], [s, 0, -(L + 0.001)], z_axis, nt, case="below_tilted", **tag)
    res["tilt_T_tol_Nm"] = max(0.05 * max(np.linalg.norm(c["fine_T_Nm"]) for c in res["tilt"]), 2e-5)
    res["tilt_by_angle"] = {}
    for tilt in TILTS_DEG:
        rows = [c for c in res["tilt"] if c["tilt_deg"] == tilt]
        wf = max(c["err_rel_Fn"] for c in rows)
        wt = max(c["T_err_Nm"] for c in rows)
        res["tilt_by_angle"][str(tilt)] = {"worst_err_rel_Fn": wf, "worst_T_err_Nm": wt,
                                          "pass": bool(wf <= 0.05 and wt <= res["tilt_T_tol_Nm"])}
    passing = [t for t in TILTS_DEG if all(res["tilt_by_angle"][str(u)]["pass"] for u in TILTS_DEG if u <= t)]
    res["validated_tilt_deg"] = max(passing) if passing else 0.0
    tilt_ok = res["validated_tilt_deg"] >= TILT_REQUIRED_DEG
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
            f, t, u = fine_pair(MP, p[i], n[i], p[j], n[j], *(REF_QUAD_CUBE if near else (6, 16)))
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
    res["pass"] = bool(pair_ok and tilt_ok and all(c["max_force_err_rel_Fn"] <= 0.05 for c in res["cube"])
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


def v5(integrator: str, duration: float = 0.5, timestep: float = 0.0005) -> dict:
    mp1 = M1Params(radial_preload=0.0, rig=False, gravity_z=0.0, joint_damping=0.0, joint_frictionloss=0.0,
                   integrator=integrator, timestep=timestep)
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
        half = len(E) // 2
        return {"integrator": integrator, "duration_s": duration, "timestep_s": timestep,
                "mean_drift_first_half_J": float(np.mean(E[:half] - E[0])),
                "mean_drift_second_half_J": float(np.mean(E[half:] - E[0])), "energy_exchanged_J": exch, "max_drift_J": drift,
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


SIZES = {"3x1.5_N35": (0.003, 0.0015, "N35"), "4x1.5_N35": (0.004, 0.0015, "N35"),
         "4x2_N35": (0.004, 0.002, "N35"), "4x2_N52": (0.004, 0.002, "N52")}


def main() -> None:
    """Usage: d8_1b_checks.py [--size TAG] [--scale S] [--tables-only]
    Default: nominal 4x2 mm N35, written to results/d8_1b_checks.json. With --size/--scale (M4 pre-registration E1-7,
    added 2026-11-15) the same checks run for that magnet and are written to results/d8_1b_checks_<tag>_s<scale>.json;
    --tables-only builds and caches the near-field tables and stops (used for grades/scales whose relative accuracy
    is covered by the V3 record at the same size)."""
    global MP
    tag, scale = None, 1.0
    if "--size" in sys.argv:
        tag = sys.argv[sys.argv.index("--size") + 1]
    if "--scale" in sys.argv:
        scale = float(sys.argv[sys.argv.index("--scale") + 1])
    if tag is not None or scale != 1.0:
        dia, length, grade = SIZES[tag or "4x2_N35"]
        MP = MagnetParams(diameter=dia, length=length, grade=grade, scale=scale)
    out_name = "d8_1b_checks.json" if (tag is None and scale == 1.0) else f"d8_1b_checks_{tag or '4x2_N35'}_s{scale:g}.json"
    t0 = time.perf_counter()
    spline = near_field_tables(MP, CACHE)
    if "--tables-only" in sys.argv:
        print(f"tables built for {asdict(MP)} in {time.perf_counter() - t0:.0f} s", flush=True)
        return
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
    # Diagnostic (review finding 7): a real energy gain keeps growing over time; a symplectic-Euler oscillation stays
    # bounded and shrinks with dt. Not a pass criterion.
    for dur, dt in ((5.0, 0.0005), (5.0, 0.00025)):
        key = f"V5_implicitfast_{dur:g}s_dt{dt * 1e3:g}ms"
        res[key] = v5("implicitfast", dur, dt)
        print(key, {k: v for k, v in res[key].items() if k != "stats"}, flush=True)
    res["throughput_idle_steps_per_s"] = throughput()
    print("throughput:", res["throughput_idle_steps_per_s"], flush=True)
    res["V3"] = v3(spline)
    v = res["V3"]
    print("V3: pair worst F", round(v["pair_worst_err"], 4), "T", f'{v["pair_worst_T_err_Nm"]:.2e}/{v["pair_T_tol_Nm"]:.2e}',
          "cube", [(c["R_turn_deg"], round(c["max_force_err_rel_Fn"], 4), f'{c["max_torque_err_Nm"]:.1e}')
                   for c in v["cube"]], f'T tol {v["cube_T_tol_Nm"]:.1e}', "tilt", v["tilt_by_angle"],
          "validated tilt", v["validated_tilt_deg"], "pass", v["pass"])
    res["all_pass"] = all(res[k]["pass"] for k in ("survey", "V3", "V4", "V5_rk4", "V6"))
    res["wall_s"] = round(time.perf_counter() - t0, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / out_name).write_text(json.dumps(res, indent=1, default=float))
    print("ALL PASS" if res["all_pass"] else "NOT ALL PASS", f"wall {res['wall_s']} s")


if __name__ == "__main__":
    main()
