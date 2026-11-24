"""Diagnostic rerun of D14 Stage 3b PG20 E1-4/scr20inv_s16400 (UNSCORED, diagnostic only, not part of any protocol).

Runs the committed d14s3_run.worker unchanged, with one extra read-only step hook stacked on the Stage 2 LoggedTrial:
- every U move: turner angle / target / torque and U-layer mean angle, every 20 steps (10 ms);
- moves DETAIL (10: U2 that passed, 29: U2 that jammed): every 4 steps (2 ms), plus contact torques on the U layer
  about the U turner axis, grouped by partner class, and the top contacts.
Then checks that the record's per_move equals the committed record exactly (the hook must not change the trajectory).
Output: <scratch>/diag_s16400.json.gz
"""
import gzip, json, sys, time
from pathlib import Path
import numpy as np

REPO = Path("/mnt/c/dev/Rubiknetic")
EXP = REPO / "experiments/D14_noslip_rest_rehearsal"
sys.path.insert(0, str(EXP))
sys.path.insert(0, str(REPO / "src"))

import importlib.util
spec = importlib.util.spec_from_file_location("d14s3_run", EXP / "d14s3_run.py")
S3 = importlib.util.module_from_spec(spec); sys.modules["d14s3_run"] = S3; spec.loader.exec_module(S3)
RUN2 = S3.RUN2
import mujoco

SUB = sys.argv[1] if len(sys.argv) > 1 else "E1-4"
TID = sys.argv[2] if len(sys.argv) > 2 else "scr20inv_s16400"
DETAIL = set(int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else "10,29").split(","))
COARSE_EVERY, DETAIL_EVERY = 20, 4
diag = {"moves": []}


def install_diag(scored):
    Base = scored.Trial

    class DiagTrial(Base):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            m, d, ro, rig = self.model, self.sim.d, self.ro, self.rig
            jid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "turner_U_hinge")
            qadr = int(m.jnt_qposadr[jid])
            aid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, "turn_U")
            gname = lambda g: m.geom(g).name or f"geom{g}"  # noqa: E731
            bname = lambda b: m.body(b).name or f"body{b}"  # noqa: E731
            body_of = m.geom_bodyid
            cubie_bodies = set(int(b) for b in ro.body_ids)
            st = {"k": -1, "cur": None, "steps": 0}
            orig_turn = rig.turn

            def turn(move, timing=None, record=True):
                st["k"] += 1
                k = st["k"]
                cur = None
                if move.face == "U":
                    _, r0 = ro.poses(d)
                    members = ro.layer_members(d, "U")
                    cur = {"k": k, "move": str(move), "detail": k in DETAIL, "t0": float(d.time),
                           "turner0_deg": float(np.degrees(d.qpos[qadr])), "target0_deg": float(np.degrees(rig.target["U"])),
                           "members": members, "r0": r0,
                           "ubodies": set(int(ro.body_ids[i]) for i in members),
                           "s": {"t": [], "target_deg": [], "turner_deg": [], "torque_Nm": [], "layer_deg": [],
                                 "layer_spread_deg": [], "ncon": [], "min_dist_mm": []}}
                    if cur["detail"]:
                        cur["s"].update({"member_deg": [], "tq_by_class": [], "top": []})
                    diag["moves"].append(cur)
                st["cur"] = cur
                out = orig_turn(move, timing, record)
                st["cur"] = None
                return out
            rig.turn = turn

            def hook(dd):
                st["steps"] += 1
                cur = st["cur"]
                if cur is None:
                    return
                every = DETAIL_EVERY if cur["detail"] else COARSE_EVERY
                if st["steps"] % every:
                    return
                s = cur["s"]
                _, r = ro.poses(dd)
                ang = ro.rotation_about_deg(cur["r0"], r, cur["members"], "U")
                s["t"].append(float(dd.time) - cur["t0"])
                s["target_deg"].append(float(np.degrees(rig.target["U"])) - cur["target0_deg"])
                s["turner_deg"].append(float(np.degrees(dd.qpos[qadr])) - cur["turner0_deg"])
                s["torque_Nm"].append(float(dd.actuator_force[aid]))
                s["layer_deg"].append(float(np.mean(ang)))
                s["layer_spread_deg"].append(float(np.ptp(ang)))
                nc = int(dd.ncon)
                s["ncon"].append(nc)
                s["min_dist_mm"].append(float(dd.contact.dist[:nc].min() * 1000) if nc else 0.0)
                if not cur["detail"]:
                    return
                s["member_deg"].append([float(x) for x in ang])
                axis = np.array(dd.xaxis[jid]); anchor = np.array(dd.xanchor[jid])
                cls_tq = {}
                tops = []
                f6 = np.zeros(6)
                for i in range(nc):
                    c = dd.contact[i]
                    b1, b2 = int(body_of[c.geom1]), int(body_of[c.geom2])
                    in1, in2 = b1 in cur["ubodies"], b2 in cur["ubodies"]
                    if in1 == in2:
                        continue
                    mujoco.mj_contactForce(m, dd, i, f6)
                    fr = np.array(c.frame).reshape(3, 3)
                    F = fr.T @ f6[:3]            # force on geom2 (normal points geom1 -> geom2)
                    T = fr.T @ f6[3:]            # torsional/rolling torque on geom2
                    sign = 1.0 if in2 else -1.0  # force on the U-layer side
                    pos = np.array(c.pos)
                    tq = sign * (np.cross(pos - anchor, F) + T) @ axis
                    other_b, other_g = (b1, c.geom1) if in2 else (b2, c.geom2)
                    on = gname(other_g)
                    cls = ("pad" if on.startswith("pad_") else "cubie" if other_b in cubie_bodies
                           else "core" if bname(other_b) == "core" else "other:" + bname(other_b))
                    cls_tq[cls] = cls_tq.get(cls, 0.0) + float(tq)
                    tops.append((float(tq), gname(c.geom1), gname(c.geom2), float(c.dist * 1000), float(f6[0])))
                tops.sort(key=lambda x: -abs(x[0]))
                s["tq_by_class"].append(cls_tq)
                s["top"].append(tops[:6])
            self.sim.hooks.append(hook)

    scored.Trial = DiagTrial


orig_install = RUN2.install_logged_trial


def patched(scored, exp, log):
    orig_install(scored, exp, log)
    install_diag(scored)


RUN2.install_logged_trial = patched

OUTF = Path(__file__).resolve().parent / "raw" / f"diag_{TID}.json.gz"; OUTF.parent.mkdir(exist_ok=True)
import os
OVR = json.loads(os.environ.get("DIAG_OVR", "{}"))
TAG = os.environ.get("DIAG_TAG", "")
if TAG:
    OUTF = OUTF.parent / f"diag_{TID}_{TAG}.json.gz"
env = S3.D13.environment()
jobs = [j for j in S3.base_jobs(env, (SUB,), S3.NOSLIP) if j["er9g_arm"] == "PG20" and j["tid"] == TID]
assert len(jobs) == 1, len(jobs)
if OVR:
    jobs[0] = {**jobs[0], "kw": {**jobs[0]["kw"], "overrides": {**jobs[0]["kw"]["overrides"], **OVR}}}
t0 = time.perf_counter()
rec = S3.worker(jobs[0])
wall = time.perf_counter() - t0

committed = json.load(gzip.open(EXP / f"results/{'stage2' if SUB in ('E1-2','E1-5','E1-5s') else 'stage3'}/PG20/{SUB}/{TID}.json.gz"))
mine = json.loads(json.dumps(rec, default=float))
same_pm = mine["per_move"] == committed["per_move"]
same_keys = {k: mine.get(k) == committed.get(k) for k in ("pass", "fail_reasons", "moves_completed_ok", "sim_time_s",
                                                          "final_matches_oracle", "misalignment_growth_slope_deg_per_move")}
for mv in diag["moves"]:
    mv.pop("r0"); mv["ubodies"] = sorted(mv["ubodies"])
out = {"note": "diagnostic only; unscored", "job_tid": jobs[0]["tid"], "env": env, "wall_s": wall,
       "per_move_identical_to_committed": same_pm, "fields_identical": same_keys,
       "solver": rec["d14s3"]["solver"], "overrides": jobs[0]["kw"]["overrides"], "pass": rec.get("pass"),
       "fail_reasons": rec.get("fail_reasons"),
       "per_move_summary": [{k: m[k] for k in ("move", "turn_error_deg", "nontarget_drift_deg", "max_turner_torque_Nm",
                                               "penetration_mm", "ok_all")} for m in rec["per_move"]], "diag": diag}
with gzip.open(OUTF, "wt") as fh:
    json.dump(out, fh, default=float)
print("wall %.0f s; per_move identical: %s; %s" % (wall, same_pm, same_keys))
print("wrote", OUTF)
