"""D25 part 1 (UNSCORED, pilot seed 29001; read-only): where does MagnetSystem.apply spend its time?

For each scene (G1 cube rig during a U turn; two-arm scene after its start sequence) it
  1. times the full step with the original callback, with no callback, and with an empty Python callback
     (= the cost of MuJoCo calling into Python at all);
  2. records 300 body-pose snapshots from the run and times every stage of apply() on them, using a verbatim copy of
     pair_forces with timers (stage_pair_forces; checked equal to the original on every snapshot);
  3. runs cProfile over 500 callback calls.
Writes results/profile_<scene>.json in this folder only."""
from __future__ import annotations

import cProfile
import io
import json
import pstats
import sys
import time
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scenes  # noqa: E402

from rubiknetic.cube_physics import magnets as MG  # noqa: E402

clock = time.perf_counter


def stage_pair_forces(mp, spline, ii, jj, p, n, stats, scatter, T):
    """magnets.pair_forces copied verbatim, with clock checkpoints accumulated into dict T."""
    t0 = clock()
    mabs, c = mp.moment, MG.MU0 / (4 * np.pi)
    i, j = ii, jj
    zmin = mp.length + 0.0001
    rv = p[j] - p[i]
    r = np.linalg.norm(rv, axis=1)
    rh = rv / r[:, None]
    m1, m2 = mabs * n[i], mabs * n[j]
    a1 = np.einsum("ij,ij->i", m1, rh)
    a2 = np.einsum("ij,ij->i", m2, rh)
    mm = np.einsum("ij,ij->i", m1, m2)
    wf, dwf = MG._cutoff(r, mp.far_r1, mp.far_r2)
    Ud = c / r ** 3 * (mm - 3 * a1 * a2)
    U = float(np.sum(wf * Ud))
    F2 = (3 * c / r ** 4)[:, None] * (a1[:, None] * m2 + a2[:, None] * m1 + mm[:, None] * rh
                                     - 5 * (a1 * a2)[:, None] * rh)
    F2 = wf[:, None] * F2 - (dwf * Ud)[:, None] * rh
    B1 = (c / r ** 3)[:, None] * (3 * a1[:, None] * rh - m1)
    B2 = (c / r ** 3)[:, None] * (3 * a2[:, None] * rh - m2)
    T2 = wf[:, None] * MG._cross(m2, B1)
    T1 = wf[:, None] * MG._cross(m1, B2)
    cosn = np.einsum("ij,ij->i", n[i], n[j])
    near = r < mp.r2
    par = near & (np.abs(cosn) > np.cos(np.radians(45)))
    if stats is not None:
        stats["near_perpendicular"] += int(np.sum(near & ~par))
    t1 = clock()
    T["dipole_all_pairs"] += t1 - t0
    if par.any():
        k = np.nonzero(par)[0]
        ax = n[i[k]]
        s = np.sign(cosn[k])
        u = s[:, None] * n[j[k]]
        rk = rv[k]
        z = np.einsum("ij,ij->i", rk, ax)
        lat = rk - z[:, None] * ax
        rho = np.linalg.norm(lat, axis=1)
        az = np.abs(z)
        if stats is not None:
            stats["clamped_z"] += int(np.sum(az < zmin))
            tilt = float(np.degrees(np.arccos(min(1.0, float(np.abs(cosn[k]).min())))))
            stats["max_near_tilt_deg"] = max(stats["max_near_tilt_deg"], tilt)
        azc = np.maximum(az, zmin)
        zon = (az >= zmin).astype(float)
        sig = np.where(z >= 0, 1.0, -1.0)
        mu = np.einsum("ij,ij->i", u, ax)
        v = np.einsum("ij,ij->i", u, lat)
        t2 = clock()
        T["near_geometry"] += t2 - t1
        S0, SA, SB, SD = spline
        C0, C0r, C0z = S0.ev(rho, azc), S0.ev(rho, azc, dx=1), S0.ev(rho, azc, dy=1)
        A, Ar, Az = SA.ev(rho, azc), SA.ev(rho, azc, dx=1), SA.ev(rho, azc, dy=1)
        B, Br, Bz = SB.ev(rho, azc), SB.ev(rho, azc, dx=1), SB.ev(rho, azc, dy=1)
        D, Dr, Dz = SD.ev(rho, azc), SD.ev(rho, azc, dx=1), SD.ev(rho, azc, dy=1)
        t3 = clock()
        T["spline_ev_12_calls"] += t3 - t2
        q = 1.0 - mu * mu
        C = C0 + sig * A * v + 0.5 * B * q + 0.5 * D * v * v
        C_r = C0r + sig * v * Ar + 0.5 * q * Br + 0.5 * v * v * Dr
        C_z = (C0z + sig * v * Az + 0.5 * q * Bz + 0.5 * v * v * Dz) * zon
        C_v = sig * A + D * v
        C_mu = -B * mu
        w, dw = MG._cutoff(r[k], mp.r1, mp.r2)
        U += float(np.sum(s * w * C))
        lat_hat = np.where(rho[:, None] > 1e-12, lat / np.maximum(rho, 1e-12)[:, None], 0.0)
        grad = s[:, None] * ((dw * C)[:, None] * rh[k]
                             + w[:, None] * (C_r[:, None] * lat_hat + (C_z * sig)[:, None] * ax
                                             + C_v[:, None] * (u - mu[:, None] * ax)))
        F2[k] -= grad
        g_u = (s * w)[:, None] * (C_v[:, None] * lat + C_mu[:, None] * ax)
        T2[k] = T2[k] - MG._cross(u, g_u)
        T1[k] = -MG._cross(rk, F2[k]) - T2[k]
        t4 = clock()
        T["near_force_torque"] += t4 - t3
        T["n_near"] += len(k)
    t4 = clock()
    Si, Sj = scatter if scatter is not None else MG.scatter_matrices(len(p), i, j)
    F = Sj @ F2 - Si @ F2
    Tq = Sj @ T2 + Si @ T1
    if stats is not None:
        stats["max_force_N"] = max(stats["max_force_N"], float(np.abs(F).max()))
    T["scatter_matmul"] += clock() - t4
    T["n_pairs"] += len(ii)
    return F, Tq, U


def stage_profile(ms, d, snaps, model):
    """Times each stage of apply() over the recorded pose snapshots (list state frozen at the last one)."""
    keys = ("world", "neighbour_list_check", "dipole_all_pairs", "near_geometry", "spline_ev_12_calls",
            "near_force_torque", "scatter_matmul", "body_sum_cross", "applyFT_loop", "n_near", "n_pairs")
    T = dict.fromkeys(keys, 0.0)
    st = MG._pair_stats()
    equal = True
    for xpos, xmat in snaps:
        t0 = clock()
        p, n = ms.world(xpos, xmat)
        t1 = clock()
        ms._update_list(p)
        t2 = clock()
        T["world"] += t1 - t0
        T["neighbour_list_check"] += t2 - t1
        F, Tq, U = stage_pair_forces(ms.mp, ms.spline, ms.ii, ms.jj, p, n, st, ms.scatter, T)
        F0, T0, U0 = MG.pair_forces(ms.mp, ms.spline, ms.ii, ms.jj, p, n, None, ms.scatter)
        equal &= bool(np.array_equal(F, F0) and np.array_equal(Tq, T0) and U == U0)
        t3 = clock()
        Fb = ms.body_sum @ F
        Tb = ms.body_sum @ (Tq + MG._cross(p - xpos[ms.body], F))
        t4 = clock()
        buf = np.zeros(model.nv)
        for k, b in enumerate(ms.bodies):       # on the live data (the Jacobian cost does not depend on the pose)
            mujoco.mj_applyFT(model, d, Fb[k], Tb[k], d.xpos[b], int(b), buf)
        t5 = clock()
        T["body_sum_cross"] += t4 - t3
        T["applyFT_loop"] += t5 - t4
    N = len(snaps)
    out = {k: (T[k] / N * 1e6 if not k.startswith("n_") else T[k] / N) for k in keys}
    out = {("us_" + k if not k.startswith("n_") else "mean_" + k): v for k, v in out.items()}
    out["us_total_stages"] = sum(v for k, v in out.items() if k.startswith("us_"))
    out["stage_copy_equal_to_original"] = equal
    out["n_bodies"] = int(len(ms.bodies))
    return out


def cprofile(ms, model, snaps, d, n=500):
    pr = cProfile.Profile()
    pr.enable()
    for k in range(n):
        xpos, xmat = snaps[k % len(snaps)]
        p, nn = ms.world(xpos, xmat)
        F, Tq, U = ms.forces(p, nn, stats=True)
        Fb = ms.body_sum @ F
        Tb = ms.body_sum @ (Tq + MG._cross(p - xpos[ms.body], F))
        buf = np.zeros(model.nv)
        for kk, b in enumerate(ms.bodies):
            mujoco.mj_applyFT(model, d, Fb[kk], Tb[kk], d.xpos[b], int(b), buf)
    pr.disable()
    s = io.StringIO()
    pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(25)
    return s.getvalue()


def timed_steps(step, n):
    t = clock()
    step(n)
    return (clock() - t) / n * 1e6


def main(which: str):
    out = {"scene": which}
    snaps = []
    if which == "g1":
        tr, ms = scenes.g1_scene(29001)
        sim, m, d = tr.sim, tr.model, tr.sim.d
        rec = lambda dd: snaps.append((dd.xpos.copy(), dd.xmat.copy())) if len(snaps) < 300 and sim.steps % 7 == 0 else None  # noqa: E731
        sim.hooks.append(rec)
        t = clock()
        tr.rig.turn(scenes.g1_move("U")[0], tr.timing)
        out["turn_steps"] = int(sim.steps)
        out["turn_wall_s"] = clock() - t
        sim.hooks.remove(rec)
        step = sim.step
    else:
        r, T = scenes.two_arm(29001)
        ms, m, d = r.ms, r.m, r.d
        rec = lambda dd: snaps.append((dd.xpos.copy(), dd.xmat.copy())) if len(snaps) < 300 else None  # noqa: E731
        r.sim.hooks.append(rec)
        r.ctrl_step(300)
        r.sim.hooks.remove(rec)
        step = r.ctrl_step
    out["nv"], out["nbody"] = int(m.nv), int(m.nbody)
    out["list_pairs"], out["n_magnets"] = int(len(ms.ii)), int(ms.n)
    out["magnet_stats"] = {k: v for k, v in ms.stats.items()}
    # full step with / without / with an empty Python callback (median of 3 blocks of 400 steps, interleaved)
    reps = {"original": [], "no_callback": [], "empty_python_callback": []}
    for _ in range(3):
        ms.install()
        reps["original"].append(timed_steps(step, 400))
        MG.MagnetSystem.uninstall()
        reps["no_callback"].append(timed_steps(step, 400))
        mujoco.set_mjcb_passive(lambda mm, dd: None)
        reps["empty_python_callback"].append(timed_steps(step, 400))
    ms.install()
    out["us_per_step_median"] = {k: float(np.median(v)) for k, v in reps.items()}
    out["us_per_step_all"] = reps
    out["callback_share_of_step"] = 1 - out["us_per_step_median"]["no_callback"] / out["us_per_step_median"]["original"]
    # the callback alone, on the live data, as MuJoCo calls it
    mujoco.mj_forward(m, d)
    ts = []
    for _ in range(5):
        t = clock()
        for _ in range(200):
            d.qfrc_passive[:] = 0.0
            ms.apply(m, d)
        ts.append((clock() - t) / 200 * 1e6)
    out["us_apply_call_median"] = float(np.median(ts))
    out["stages"] = stage_profile(ms, d, snaps, m)
    out["cprofile_top25_tottime"] = cprofile(ms, m, snaps, d)
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / f"profile_{which}.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: v for k, v in out.items() if k != "cprofile_top25_tottime"}, indent=1, default=float))
    print(out["cprofile_top25_tottime"])


if __name__ == "__main__":
    main(sys.argv[1])
