"""Diagnostic 2 (UNSCORED, diagnostic only): what makes the ~6 deg catch at the start of a turn.

Single-turn trials through the committed d14s3_run.worker (NoSlip 10), one fresh process per trial, with a read-only hook:
per step (every 2 steps during the turn): turner/layer angle, turner torque, magnet torque about the turn axis and
magnet axial force on the layer, every contact on the layer (normal split into axial/radial/tangential in the layer
frame, height above the layer boundary plane, axis torque), each layer piece's axial offset and tilt, centre angles.
Output: <scratch>/diag2/<arm>_<face>_s<seed>.json.gz and a summary print.
"""
import gzip, json, sys, time
import multiprocessing as mp
from pathlib import Path
import numpy as np

REPO = Path("/mnt/c/dev/Rubiknetic")
EXP = REPO / "experiments/D14_noslip_rest_rehearsal"
OUT = None
sys.path.insert(0, str(EXP)); sys.path.insert(0, str(REPO / "src"))
EVERY = 2

import os
GRAV = os.environ.get("DIAG_GRAV")          # e.g. "0" -> gravity_z override
OVR = json.loads(os.environ.get("DIAG_OVR", "{}"))  # extra M1Params overrides, e.g. {"gap": 1e-4}
TAG = os.environ.get("DIAG_TAG", "diag2")
RUNS = json.loads(os.environ["DIAG_RUNS"]) if os.environ.get("DIAG_RUNS") else ([("PG20", f, 16100) for f in "URFDLB"]
        + [("PG20", f, s) for f in "UR" for s in (16101, 16102, 16103)]
        + [(a, f, 16100) for a in ("L0", "PG8") for f in "UR"])


def load_s3():
    import importlib.util
    spec = importlib.util.spec_from_file_location("d14s3_run", EXP / "d14s3_run.py")
    S3 = importlib.util.module_from_spec(spec); sys.modules["d14s3_run"] = S3; spec.loader.exec_module(S3)
    return S3


def one(run):
    arm, face, seed = run
    S3 = load_s3(); RUN2 = S3.RUN2
    import mujoco
    from rubiknetic.cube_logic.notation import FACE_NORMAL
    ER9 = RUN2.er9()
    _, _, M4, _ = ER9.mods()
    data = {"arm": arm, "face": face, "seed": seed, "s": None}

    def install_diag(scored):
        Base = scored.Trial

        class DiagTrial(Base):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                m, d, ro, rig = self.model, self.sim.d, self.ro, self.rig
                pitch = self.params.pitch
                jid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, f"turner_{face}_hinge")
                qadr = int(m.jnt_qposadr[jid])
                aid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, f"turn_{face}")
                gname = lambda g: m.geom(g).name  # noqa: E731
                cubie_bodies = set(int(b) for b in ro.body_ids)
                centres = {n: int(m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, f"cubie_{n}_j")])
                           for n in ("00p", "00n", "p00", "n00", "0p0", "0n0")}
                st = {"steps": 0, "on": False}
                orig_turn = rig.turn

                def turn(move, timing=None, record=True):
                    _, r0 = ro.poses(d)
                    members = ro.layer_members(d, face)
                    st.update(on=True, r0=r0, members=members, t0=float(d.time),
                              ub=set(int(ro.body_ids[i]) for i in members),
                              q0=float(d.qpos[qadr]), tg0=float(rig.target[face]))
                    s = {k: [] for k in ("t", "target_deg", "turner_deg", "layer_deg", "torque_Nm", "mag_tq_Nm",
                                         "mag_axial_N", "contacts", "axial_off_mm", "tilt_deg", "centres_deg")}
                    s["members"] = [int(x) for x in members]
                    s["qpos_turn_start"] = [float(x) for x in d.qpos]
                    s["qpos_ramp_start"] = None
                    data["s"] = s
                    out = orig_turn(move, timing, record)
                    st["on"] = False
                    return out
                rig.turn = turn

                def hook(dd):
                    st["steps"] += 1
                    if not st["on"] or st["steps"] % EVERY:
                        return
                    s = data["s"]
                    if s["qpos_ramp_start"] is None and float(dd.time) - st["t0"] >= 0.2995:
                        s["qpos_ramp_start"] = [float(x) for x in dd.qpos]
                    c = np.array(dd.xpos[ro.core]); rc = np.array(dd.xmat[ro.core]).reshape(3, 3)
                    n = rc @ np.array(FACE_NORMAL[face], float)          # outward normal, world
                    pos, r = ro.poses(dd)
                    ang = ro.rotation_about_deg(st["r0"], r, st["members"], face)
                    s["t"].append(float(dd.time) - st["t0"])
                    s["target_deg"].append(float(np.degrees(rig.target[face] - st["tg0"])))
                    s["turner_deg"].append(float(np.degrees(dd.qpos[qadr] - st["q0"])))
                    s["layer_deg"].append(float(np.mean(ang)))
                    s["torque_Nm"].append(float(dd.actuator_force[aid]))
                    ms = M4._MS
                    if ms is not None and ms.last is not None:
                        p, F, T, _U = ms.last
                        mk = np.isin(ms.body, list(st["ub"]))
                        s["mag_tq_Nm"].append(float((T[mk] + np.cross(p[mk] - c, F[mk])).sum(axis=0) @ n))
                        s["mag_axial_N"].append(float(F[mk].sum(axis=0) @ n))
                    else:
                        s["mag_tq_Nm"].append(0.0); s["mag_axial_N"].append(0.0)
                    # pieces: axial offset of geom centre from nominal layer centre plane, tilt since turn start
                    offs, tilts = [], []
                    for i in st["members"]:
                        offs.append(float((pos[i] @ np.array(FACE_NORMAL[face], float) - 1.0) * pitch * 1000))
                        R = r[i] @ st["r0"][i].T
                        w = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) / 2  # small-angle axis*sin
                        nl = np.array(FACE_NORMAL[face], float)
                        tilts.append(float(np.degrees(np.linalg.norm(w - (w @ nl) * nl))))
                    s["axial_off_mm"].append(offs); s["tilt_deg"].append(tilts)
                    s["centres_deg"].append({k: float(np.degrees(dd.qpos[a])) for k, a in centres.items()})
                    f6 = np.zeros(6); cl = []
                    for i in range(int(dd.ncon)):
                        cc = dd.contact[i]
                        b1, b2 = int(m.geom_bodyid[cc.geom1]), int(m.geom_bodyid[cc.geom2])
                        in1, in2 = b1 in st["ub"], b2 in st["ub"]
                        if in1 == in2:
                            continue
                        mujoco.mj_contactForce(m, dd, i, f6)
                        fr = np.array(cc.frame).reshape(3, 3)
                        sign = 1.0 if in2 else -1.0
                        F = sign * (fr.T @ f6[:3]); T = sign * (fr.T @ f6[3:])
                        nrm = sign * fr[0]                                  # normal pushing on the layer piece
                        P = np.array(cc.pos) - c
                        rad = P - (P @ n) * n
                        rr = float(np.linalg.norm(rad)); er = rad / max(rr, 1e-12); et = np.cross(n, er)
                        other = cc.geom1 if in2 else cc.geom2
                        ob = b1 if in2 else b2
                        cl.append({"other": gname(other), "me": gname(cc.geom2 if in2 else cc.geom1),
                                   "cls": "pad" if gname(other).startswith("pad_") else ("cubie" if ob in cubie_bodies else "x"),
                                   "tq": float((np.cross(P, F) + T) @ n), "fn": float(f6[0]),
                                   "n_ax": float(nrm @ n), "n_rad": float(nrm @ er), "n_tan": float(nrm @ et),
                                   "h_mm": float((P @ n - 0.5 * pitch) * 1000), "r_mm": rr * 1000,
                                   "dist_mm": float(cc.dist * 1000)})
                    s["contacts"].append(cl)
                self.sim.hooks.append(hook)

        scored.Trial = DiagTrial

    orig_install = RUN2.install_logged_trial

    def patched(scored, exp, log):
        orig_install(scored, exp, log)
        install_diag(scored)
    RUN2.install_logged_trial = patched
    env = S3.D13.environment()
    base = [j for j in S3.base_jobs(env, ("E1-2",), S3.NOSLIP) if j["er9g_arm"] == arm and j["tid"] == "U_s16100"][0]
    job = json.loads(json.dumps(base, default=str)) if False else dict(base)
    job["kw"] = {**base["kw"], "moves": face, "seed": seed}
    if OVR:
        job["kw"]["overrides"] = {**job["kw"]["overrides"], **OVR}
    if GRAV is not None:
        job["kw"]["overrides"] = {**base["kw"]["overrides"], "gravity_z": float(GRAV)}
    job["tid"] = f"{face}_s{seed}"
    t0 = time.perf_counter()
    rec = S3.worker(job)
    pm = rec["per_move"][0]
    data["params"] = rec["params"]
    data.update(wall_s=time.perf_counter() - t0, pass_=rec.get("pass"), turn_error_deg=pm["turn_error_deg"],
                max_turner_torque_Nm=pm["max_turner_torque_Nm"], penetration_mm=pm["penetration_mm"],
                nontarget_drift_deg=pm["nontarget_drift_deg"], overrides=job["kw"]["overrides"])
    out = Path(__file__).resolve().parent / "raw" / TAG
    out.mkdir(parents=True, exist_ok=True)
    with gzip.open(out / f"{arm}_{face}_s{seed}.json.gz", "wt") as fh:
        json.dump(data, fh)
    return {k: data[k] for k in ("arm", "face", "seed", "wall_s", "pass_", "max_turner_torque_Nm", "turn_error_deg", "nontarget_drift_deg")}


if __name__ == "__main__":
    with mp.get_context("fork").Pool(int(os.environ.get("DIAG_JOBS", "4")), maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(one, RUNS):
            print(r, flush=True)
