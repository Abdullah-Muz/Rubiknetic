"""M6: checks of the MuJoCo implementation of the real-radius core layout, 4x3 mm N52 at c = 0.2 mm (PROTOCOL.md).
Unscored. Usage (WSL):  ~/.venvs/rubiknetic/bin/python experiments/M6_core_magnets/m6_checks.py
Writes results/m6_checks.json and prints a summary.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import mujoco
import numpy as np
import scipy
from scipy.spatial.transform import Rotation

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TABLES = HERE / "tables"
OUT = HERE / "results"


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


D8 = _load("d8_1b_checks", "experiments/D8_alignment/d8_1b_checks.py")   # only turn_layer and build_r_hinge_model
E3 = _load("er3_screen", "experiments/ER3_layout_design/er3_screen.py")   # only DLT (ER3's finite-difference step)

from rubiknetic.cube_logic.geometric import HOME_POSITIONS  # noqa: E402
from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES  # noqa: E402
from rubiknetic.cube_physics import magnets as M  # noqa: E402
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml, cubie_name  # noqa: E402

MP = M.MagnetParams(diameter=0.004, length=0.003, grade="N52")
MP35 = M.MagnetParams(diameter=0.004, length=0.003, grade="N35")
CLEAR = 2e-4
GAP = 5e-5                     # M5's piece gap
ER5_TABLES = REPO / "experiments/ER5_magnet_validation/tables"
ER5_JSON = REPO / "experiments/ER5_magnet_validation/results/er5_4x3_N35.json"
ER6_JSON = REPO / "experiments/ER6_real_placement_screen/results/screen.json"
ER6_VARIANT = "N52 c=0.2mm"


def m1(**kw) -> M1Params:
    return M1Params(radial_preload=0.0, gap=GAP, **kw)


def build(rig: bool = False):
    m = mujoco.MjModel.from_xml_string(build_m1_xml(m1(rig=rig)))
    return m, mujoco.MjData(m)


def system(m, spline) -> M.MagnetSystem:
    return M.MagnetSystem(m, m1().pitch, GAP, MP, tables=spline, mags=M.core_layout(MP, CLEAR))


def pose_layer(m, d, nrm: np.ndarray, theta: float) -> None:
    """Kinematic setup only: from home, rotate every body of the layer {h . nrm = 1} by theta about nrm."""
    mujoco.mj_resetData(m, d)
    q = Rotation.from_rotvec(theta * nrm).as_quat()           # x y z w
    for h in HOME_POSITIONS:
        if int(np.dot(h, nrm)) != 1:
            continue
        j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, cubie_name(h) + "_j")
        a = m.jnt_qposadr[j]
        if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_BALL:
            d.qpos[a:a + 4] = [q[3], q[0], q[1], q[2]]
        else:                                                  # centre: hinge about its own outward normal h = nrm
            d.qpos[a] = theta
    mujoco.mj_kinematics(m, d)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------------- self-checks
def s1() -> dict:
    rec = json.loads(ER5_JSON.read_text())["tables_sha256"]
    (fname, recorded), = rec.items()
    f35 = ER5_TABLES / fname
    got = sha(f35)
    f52 = TABLES / f"tilt_4x3_{MP.br:g}T_s1_r8_h1.5_q16x48.npz"
    assert f52.exists(), f52
    k = (MP.br / MP35.br) ** 2
    diffs = {}
    with np.load(f35) as a, np.load(f52) as b:
        assert np.array_equal(a["rho"], b["rho"]) and np.array_equal(a["z"], b["z"])
        for key in ("C0", "Cp", "Cm", "Ct"):
            diffs[key] = float(np.abs(b[key] - k * a[key]).max() / np.abs(b[key]).max())
    return {"er5_file": fname, "er5_sha256": got, "er5_recorded": recorded, "n52_file": f52.name,
            "n52_sha256": sha(f52), "scale": k, "max_rel_diff": diffs,
            "pass": bool(got == recorded and max(diffs.values()) <= 1e-9)}


def layer_torque(ms, d, nrm) -> float:
    p, n = ms.world(d.xpos, d.xmat)
    F, T, _ = ms.forces(p, n)
    tot = T + np.cross(p, F)                                   # about the cube centre (body frames sit there)
    names = [g["body"] for g in ms.mags]
    mem = {cubie_name(h) for h in HOME_POSITIONS if int(np.dot(h, nrm)) == 1}
    return float(sum(tot[k] @ nrm for k, b in enumerate(names) if b in mem))


def s2(spline) -> dict:
    ref = next(r for r in json.loads(ER6_JSON.read_text())["rows"] if r["variant"] == ER6_VARIANT)
    m, d = build()
    ms = system(m, spline)
    dl = float(E3.DLT)
    layers, rel = {}, {}
    for f in FACES:
        nrm = np.array(FACE_NORMAL[f], float)
        tq = []
        for s in (1, -1):
            pose_layer(m, d, nrm, s * dl)
            tq.append(layer_torque(ms, d, nrm))
        layers[f] = -(tq[0] - tq[1]) / (2 * dl)
        rel[f] = abs(layers[f] - ref["layers"][f]) / abs(ref["layers"][f])
    nrm = np.array(FACE_NORMAL["U"], float)
    prof = []
    for deg in range(0, 91):
        pose_layer(m, d, nrm, np.radians(deg))
        prof.append(layer_torque(ms, d, nrm))
    prof_ref = np.array(ref["turn_profile_Nm"])
    prof_err = float(np.abs(np.array(prof) - prof_ref).max() / np.abs(prof_ref).max())
    return {"dlt_rad": dl, "layers": layers, "layers_er6": ref["layers"], "layers_max_rel_diff": max(rel.values()),
            "turn_peak_Nm": float(np.abs(prof).max()), "turn_peak_er6_Nm": ref["turn_peak_Nm"],
            "profile_max_diff_rel_peak": prof_err,
            "pass": bool(max(rel.values()) <= 1e-6 and prof_err <= 1e-6)}


# ---------------------------------------------------------------------------------------------------- checks
def v4(spline) -> dict:
    m, d = build()
    ms = system(m, spline)
    rng = np.random.default_rng(81)
    worst_f = worst_l = 0.0
    faces = []
    for _ in range(20):
        mujoco.mj_resetData(m, d)
        for k in range(m.njnt):
            a = m.jnt_qposadr[k]
            if m.jnt_type[k] == mujoco.mjtJoint.mjJNT_BALL:
                q = Rotation.from_rotvec(np.radians(rng.normal(0, 2.0, 3))).as_quat()
                d.qpos[a:a + 4] = [q[3], q[0], q[1], q[2]]
            elif m.jnt_type[k] == mujoco.mjtJoint.mjJNT_HINGE:   # centres (rig=False: no turner hinges)
                d.qpos[a] = np.radians(rng.normal(0, 2.0))
        axis, sign, deg = int(rng.integers(3)), int(rng.choice([-1, 1])), float(rng.uniform(0, 90))
        faces.append([axis, sign, deg])
        D8.turn_layer(m, d, axis, sign, deg)
        mujoco.mj_kinematics(m, d)
        p, n = ms.world(d.xpos, d.xmat)
        F, T, _ = ms.forces(p, n)
        scale = np.abs(F).sum()
        worst_f = max(worst_f, float(np.linalg.norm(F.sum(axis=0)) / scale))
        worst_l = max(worst_l, float(np.linalg.norm((T + np.cross(p, F)).sum(axis=0)) / (scale * 0.03)))
    return {"max_rel_net_force": worst_f, "max_rel_net_angular": worst_l, "turns": faces,
            "pass": bool(worst_f < 1e-9 and worst_l < 1e-9)}


def v5(spline, integrator: str, duration: float = 0.5, timestep: float = 0.0005) -> dict:
    mp1 = m1(rig=False, gravity_z=0.0, joint_damping=0.0, joint_frictionloss=0.0, integrator=integrator,
             timestep=timestep)
    m, d = D8.build_r_hinge_model(mp1)
    m.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_CONTACT
    m.opt.enableflags |= mujoco.mjtEnableBit.mjENBL_ENERGY
    ms = system(m, spline)
    ms.install()
    try:
        D8.turn_layer(m, d, 0, 1, 3.0)
        mujoco.mj_forward(m, d)
        ang0 = float(np.degrees(d.qpos[0]))
        E, U, ang = [], [], []
        for _ in range(int(round(duration / m.opt.timestep))):
            mujoco.mj_step(m, d)
            u = ms.energy(d)
            U.append(u)
            E.append(d.energy[1] + d.energy[0] + u)
            ang.append(float(np.degrees(d.qpos[0])))
        E, U = np.array(E), np.array(U)
        exch = float(U.max() - U.min())
        drift = float(np.abs(E - E[0]).max())
        half = len(E) // 2
        return {"integrator": integrator, "duration_s": duration, "timestep_s": timestep, "release_deg": ang0,
                "angle_range_deg": [min(ang), max(ang)], "energy_exchanged_J": exch, "max_drift_J": drift,
                "drift_rel": drift / exch if exch > 0 else None, "final_drift_J": float(E[-1] - E[0]),
                "mean_drift_first_half_J": float(np.mean(E[:half] - E[0])),
                "mean_drift_second_half_J": float(np.mean(E[half:] - E[0])), "stats": dict(ms.stats),
                "pass": bool(exch > 0 and drift <= 0.01 * exch)}
    finally:
        M.MagnetSystem.uninstall()


def v6(spline) -> dict:
    m, d = build(rig=True)
    ms = system(m, spline)
    D8.turn_layer(m, d, 2, 1, 2.0)                            # U layer at 2 deg
    mujoco.mj_forward(m, d)

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
    mujoco.mj_forward(m, d)
    without = d.qfrc_passive.copy()
    ms.install()
    try:
        mujoco.mj_forward(m, d)
        with_cb = d.qfrc_passive.copy()
    finally:
        M.MagnetSystem.uninstall()
    return {"max_abs_magnet_qfrc": float(np.abs(base).max()),
            "max_change_from_ctrl_time_qvel_act": float(np.abs(after - base).max()),
            "installed_matches_direct": float(np.abs((with_cb - without) - base).max()),
            "pass": bool(np.abs(base).max() > 0 and np.array_equal(after, base)
                         and np.allclose(with_cb - without, base, rtol=0, atol=1e-12))}


def survey(spline) -> dict:
    m, d = build()
    ms = system(m, spline)
    core_id = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "core")
    ii, jj = ms.ii_all, ms.jj_all
    piece_piece = (ms.body[ii] != core_id) & (ms.body[jj] != core_id)
    zmin = MP.length + 0.0001
    perp = clamped = pp_near = 0
    min_z, max_tilt = np.inf, 0.0
    counts = {}
    for f in FACES:
        nrm = np.array(FACE_NORMAL[f], float)
        counts[f] = []
        for deg in range(-90, 91):
            pose_layer(m, d, nrm, np.radians(deg))
            p, n = ms.world(d.xpos, d.xmat)
            rv = p[jj] - p[ii]
            near = np.linalg.norm(rv, axis=1) < MP.r2
            cosn = np.einsum("ij,ij->i", n[ii], n[jj])
            par = near & (np.abs(cosn) > np.cos(np.radians(45)))
            perp += int(np.sum(near & ~par))
            pp_near += int(np.sum(near & piece_piece))
            if par.any():
                z = np.abs(np.einsum("ij,ij->i", rv[par], n[ii][par]))
                clamped += int(np.sum(z < zmin))
                min_z = min(min_z, float(z.min()))
                max_tilt = max(max_tilt, float(np.degrees(np.arccos(min(1.0, float(np.abs(cosn[par]).min()))))))
            counts[f].append(int(near.sum()))
    return {"near_pairs_per_deg": counts, "near_perpendicular_total": perp, "clamped_z_total": clamped,
            "near_piece_piece_total": pp_near, "min_abs_z_mm": min_z * 1e3, "zmin_table_mm": zmin * 1e3,
            "max_near_tilt_deg": max_tilt, "near_pairs_range": [min(min(v) for v in counts.values()),
                                                                max(max(v) for v in counts.values())],
            "pass": bool(perp == 0 and clamped == 0 and pp_near == 0)}


def throughput(spline) -> dict:
    out = {}
    for label, use in (("no_magnets", False), ("core_layout", True)):
        m, d = build(rig=True)
        ms = system(m, spline)
        if use:
            ms.install()
        try:
            mujoco.mj_step(m, d)
            t = time.perf_counter()
            for _ in range(2000):
                mujoco.mj_step(m, d)
            out[label] = 2000 / (time.perf_counter() - t)
        finally:
            M.MagnetSystem.uninstall()
    return out


def env() -> dict:
    git = lambda *a: subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()  # noqa: E731
    return {"commit": git("rev-parse", "HEAD"), "tracked_changes": git("status", "--porcelain", "-uno").splitlines(),
            "mujoco": mujoco.__version__, "numpy": np.__version__, "scipy": scipy.__version__,
            "python": platform.python_version(), "platform": platform.platform(), "cpu": platform.machine()}


def main() -> None:
    t0 = time.perf_counter()
    res = {"env": env(), "magnet_params": M.asdict(MP), "moment_Am2": MP.moment, "clearance_m": CLEAR, "gap_m": GAP}
    spline = M.near_field_tables(MP, TABLES)
    res["table_build_s"] = round(time.perf_counter() - t0, 1)
    print(f"N52 table ready ({res['table_build_s']} s)", flush=True)
    res["S1"] = s1()
    print("S1:", {k: v for k, v in res["S1"].items() if "sha" not in k}, flush=True)
    res["S2"] = s2(spline)
    print("S2:", {k: res["S2"][k] for k in ("layers_max_rel_diff", "turn_peak_Nm", "profile_max_diff_rel_peak",
                                            "pass")}, flush=True)
    res["V4"] = v4(spline)
    print("V4:", {k: v for k, v in res["V4"].items() if k != "turns"}, flush=True)
    res["V6"] = v6(spline)
    print("V6:", res["V6"], flush=True)
    res["survey"] = survey(spline)
    print("survey:", {k: v for k, v in res["survey"].items() if k != "near_pairs_per_deg"}, flush=True)
    res["V5_rk4"] = v5(spline, "RK4")
    print("V5 RK4:", {k: v for k, v in res["V5_rk4"].items() if k != "stats"}, flush=True)
    res["V5_implicitfast"] = v5(spline, "implicitfast")
    print("V5 implicitfast:", {k: v for k, v in res["V5_implicitfast"].items() if k != "stats"}, flush=True)
    for dur, dt in ((5.0, 0.0005), (5.0, 0.00025)):
        key = f"V5_implicitfast_{dur:g}s_dt{dt * 1e3:g}ms"
        res[key] = v5(spline, "implicitfast", dur, dt)
        print(key, {k: v for k, v in res[key].items() if k != "stats"}, flush=True)
    res["throughput_idle_steps_per_s"] = throughput(spline)
    print("throughput:", res["throughput_idle_steps_per_s"], flush=True)
    res["all_pass"] = all(res[k]["pass"] for k in ("S1", "S2", "V4", "V5_rk4", "V6", "survey"))
    res["wall_s"] = round(time.perf_counter() - t0, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "m6_checks.json").write_text(json.dumps(res, indent=1, default=float))
    print("M6 IMPLEMENTATION CHECKS PASS" if res["all_pass"] else "M6 CHECKS: NOT ALL PASS", f"wall {res['wall_s']} s")


if __name__ == "__main__":
    main()
