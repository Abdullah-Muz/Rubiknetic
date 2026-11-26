"""D16: UNSCORED free-core M7 rehearsal (P-97 item 3; carries out P-09's free-core condition for M7).

Question: does M7's G1 behaviour survive when the core is a free body and the cube is held only by a two-layer
stabiliser, as arm A will hold it in G2?

Model: M7 exactly as scored in G1 (experiments/E7_scored_m7/run.py: L0 magnets, rounded edges R 2.5 mm, NoSlip 10,
gap 0.05 mm, timestep 0.5 ms), plus
  * core_free: a free joint on the core, 1.7 g, diaginertia 2e-8 (as D6; ASSUMPTION) -- or the fixed core (baseline);
  * a stand-in stabiliser (arm A's fingertips, P-97 sizes): two flat pads 30 mm wide x 30 mm deep x 4 mm on the two
    opposite side faces, covering the two layers opposite the turned face from that face's far end face (insertion
    30 mm, so 8 mm short of the target-layer boundary), on world-fixed slides. Unlike the G1 rig pads, whose servo
    saturates at grip_kp x overshoot = 12 N (D16-0, grip_probe.py), the stabiliser target is 30 mm beyond contact
    (kp 2000 -> 60 N), so its squeeze is the requested force (forcerange).
The layer is turned by the unchanged G1 rig (pads ~10-11.6 N, torque limit 1 N.m).

Setup (before t = 0, logged, as D6): setup misalignment; gravity off for 0.3 s while the stabiliser closes; 0.3 s with
gravity; then the harness's 0.5 s settle. Trials run through E7's run_trial("seq", ...) so every G1 per-move check
(oracle on the observed move, turn error, drift, penetration, radial pop, causality, edit audit) is applied unchanged;
the layer angles are in the core frame (CubeReadout). Added: core slip and rotation in the world from t = 0, and the
measured stabiliser squeeze.
Usage (WSL): python experiments/D16_free_core_m7/run.py [--workers 2] [--only NAME]
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import sys
import time
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from grip_probe import load_e7  # noqa: E402

E7 = load_e7()
M4, scored = E7.M4, E7.scored
from rubiknetic.cube_logic.notation import FACE_NORMAL  # noqa: E402

OUT = HERE / "results"
STAB_W, STAB_DEPTH, STAB_T = 0.030, 0.030, 0.004      # P-97 stabiliser pad (m)
STAB_OPEN, STAB_OVERSHOOT, STAB_KP = 0.014, 0.030, 2000.0
SIDE_AXIS = {"U": 1, "D": 1, "R": 1, "L": 1, "F": 0, "B": 0}   # stabiliser pads on the +-y faces (U, R) or +-x (F)
CORE_MASS, CORE_I = 0.0017, 2e-8                      # D6 (Paulus 2023 BOM; ASSUMPTION)
import os  # noqa: E402
CORE_MASS = float(os.environ.get("D16_CORE_MASS", CORE_MASS))   # D16c diagnostic overrides only
CORE_I = float(os.environ.get("D16_CORE_I", CORE_I))
STAB_MASS = float(os.environ.get("D16_STAB_MASS", 0.01))       # D16d screen overrides only (defaults = D16 as run)
STAB_DAMP = float(os.environ.get("D16_STAB_DAMP", 100))
STAB_SOLREF = os.environ.get("D16_STAB_SOLREF")                 # e.g. "0.005 1"; default: the rig pad solref
SEEDS = (21000, 21001, 21002, 21003)
# D16b (user, 2026-11-26: "Settle-then-turn test"): before each move wait until the cube is at rest, then close the
# turning pads on a ramp instead of a step. A controller-side change; every G1 check is unchanged.
REST_W_DPS, REST_V_MMPS, MAX_WAIT_S, RAMP_S = 1.0, 1.0, 2.0, 0.3                  # unscored; outside every scored and rehearsal range used so far

_ORIG_TRIAL = E7._ORIG.get("trial", scored.Trial)
_ORIG_XML = E7._ORIG.get("xml", scored.build_m1_xml)
_ORIG_M4_XML = M4.build_m1_xml
CFG: dict = {}                                        # this worker's trial configuration


def stabiliser_xml(face: str, force: float, mu: float, p) -> tuple[str, str]:
    n = np.array(FACE_NORMAL[face], float)
    a = int(np.argmax(np.abs(n)))
    s = n[a]
    b = SIDE_AXIS[face]
    w = 3 - a - b
    H = 1.5 * p.pitch - p.gap / 2                     # outer face of the cube
    half = np.zeros(3)
    half[a], half[b], half[w] = STAB_DEPTH / 2, STAB_T / 2, STAB_W / 2
    f3 = lambda v: " ".join(f"{x:.6f}" for x in v)   # noqa: E731
    bodies, acts = [], []
    for sg, nm in ((-1, "a"), (1, "b")):
        pos = np.zeros(3)
        pos[a] = -s * (H - STAB_DEPTH / 2)
        pos[b] = sg * (H + STAB_OPEN + STAB_T / 2)
        ax = np.zeros(3)
        ax[b] = sg
        bodies.append(
            f'    <body name="stab_{nm}" pos="{f3(pos)}">\n'
            f'      <joint name="stab_{nm}_slide" type="slide" axis="{f3(ax)}" range="-0.06 0.001" damping="{STAB_DAMP:g}"/>\n'
            f'      <geom name="stab_{nm}_g" type="box" size="{f3(half)}" contype="2" conaffinity="0" '
            f'condim="{p.pad_condim}" friction="{mu} {p.pad_friction[1]} {p.pad_friction[2]}" '
            f'solref="{STAB_SOLREF or f"{p.pad_solref[0]} {p.pad_solref[1]}"}" solimp="{" ".join(map(str, p.pad_solimp))}" '
            f'mass="{STAB_MASS:g}" rgba="0.2 0.6 0.9 1"/>\n    </body>')
        acts.append(f'    <position name="stab_{nm}" joint="stab_{nm}_slide" kp="{STAB_KP}" '
                    f'forcerange="{-force} {force}" ctrlrange="-0.06 0.001"/>')
    return "\n".join(bodies), "\n".join(acts)


def g2_xml(xml: str, p) -> str:
    """Free core (if CFG['free']) and the stabiliser, appended after the cubies so body ids are unchanged."""
    if CFG["free"]:
        tag = '<body name="core" pos="0 0 0">'
        assert xml.count(tag) == 1
        xml = xml.replace(tag, tag + '\n      <freejoint name="core_free"/>\n'
                          f'      <inertial pos="0 0 0" mass="{CORE_MASS}" diaginertia="{CORE_I} {CORE_I} {CORE_I}"/>')
    bodies, acts = stabiliser_xml(CFG["face"], CFG["force"], CFG["mu"], p)
    assert xml.count("  </worldbody>") == 1 and xml.count("  <actuator>\n") == 1
    xml = xml.replace("  </worldbody>", bodies + "\n  </worldbody>")
    return xml.replace("  <actuator>\n", "  <actuator>\n" + acts + "\n")


class Tracker:
    """Step hook: core slip and rotation from t = 0 (world frame); stabiliser squeeze every 20 steps; and, per turn,
    the first time the turning layer's angular speed RELATIVE TO THE CORE exceeds the G1 causality speed (5 deg/s).
    G1's check uses the world-frame layer speed, which a free cube moving as a whole also trips."""

    def __init__(self, m, d, core, stab_geoms, stab_acts, mon):
        self.m, self.core, self.geoms, self.acts, self.mon = m, core, stab_geoms, stab_acts, mon
        self._turn = None
        self.rel_motion_t: list[float | None] = []    # one entry per turn, in move order
        names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, g) or "" for g in range(m.ngeom)]
        self.pad_ids = np.array([g for g, n in enumerate(names) if n.startswith(("pad_", "stab_"))])
        self.pen_cubie: list[float] = []              # per turn: deepest cubie-cubie contact (mm, >= 0)
        self.pen_pad: list[float] = []                # per turn: deepest pad-cubie contact (mm, >= 0)
        self.p0, self.R0 = d.xpos[core].copy(), d.xmat[core].reshape(3, 3).copy()
        self.slip = self.rot = 0.0
        self.k, self.f6 = 0, np.zeros(6)
        self.squeeze: list[float] = []
        self.act_force: list[float] = []
        self.series: list[list[float]] = []           # t, squeeze a, squeeze b, slip mm, dx dy dz mm, |w_core| deg/s

    def __call__(self, d) -> None:
        t = self.mon.turn
        if t is not None:
            if t is not self._turn:
                self._turn = t
                self.rel_motion_t.append(None)
                self.pen_cubie.append(0.0)
                self.pen_pad.append(0.0)
            n = d.ncon
            if n:
                dist = d.contact.dist[:n]
                pm = np.isin(d.contact.geom1[:n], self.pad_ids) | np.isin(d.contact.geom2[:n], self.pad_ids)
                if pm.any():
                    self.pen_pad[-1] = max(self.pen_pad[-1], float(-dist[pm].min()) * 1000)
                if (~pm).any():
                    self.pen_cubie[-1] = max(self.pen_cubie[-1], float(-dist[~pm].min()) * 1000)
            if self.rel_motion_t[-1] is None:
                ax = t["axis"]
                w = float(np.mean(d.cvel[t["bodies"], :3] @ ax) - d.cvel[self.core, :3] @ ax)
                if abs(np.degrees(w)) > scored.THRESHOLDS["causal_speed_dps"]:
                    self.rel_motion_t[-1] = float(d.time)
        self.slip = max(self.slip, float(np.linalg.norm(d.xpos[self.core] - self.p0)))
        self.rot = max(self.rot, float(np.linalg.norm(
            Rotation.from_matrix(d.xmat[self.core].reshape(3, 3) @ self.R0.T).as_rotvec())))
        self.k += 1
        if self.k % 20:
            return
        tot = {g: 0.0 for g in self.geoms}
        for i in range(d.ncon):
            c = d.contact[i]
            for g in self.geoms:
                if g in (c.geom1, c.geom2):
                    mujoco.mj_contactForce(self.m, d, i, self.f6)
                    tot[g] += self.f6[0]
        self.squeeze.append(float(min(tot.values())))
        self.act_force.append(float(np.mean(np.abs(d.actuator_force[self.acts]))))
        w = d.cvel[self.core, :3]                     # core angular velocity (world)
        self.series.append([float(d.time), *[float(v) for v in tot.values()],
                            float(np.linalg.norm(d.xpos[self.core] - self.p0) * 1000),
                            *[float(v) * 1000 for v in d.xpos[self.core] - self.p0],
                            float(np.degrees(np.linalg.norm(w)))])


class HoldTrial(_ORIG_TRIAL):
    """scored.Trial.__init__ with the stabiliser hold phase before the settle (setup, before t = 0)."""
    last = None

    def __init__(self, params, setup, allow_test_wrench: bool = False, settle_s: float = 0.5):
        self.params = params
        self.model = mujoco.MjModel.from_xml_string(scored.build_m1_xml(params))
        m = self.model
        self.sim = scored.AuditedSim(m, allow_test_wrench=allow_test_wrench)
        self.ro = scored.CubeReadout(m, params.pitch)
        self.rig = scored.TurnRig(self.sim, pad_close_target=-(params.pad_open_clearance + params.grip_overshoot))
        self.mon = scored.Monitor(m, self.ro)
        self.sim.hooks.append(self.mon)
        self.setup = setup
        if setup is not None:
            scored.apply_setup_misalignment(self.sim, setup.misalign_deg)
        self.sim.log_setup({"type": "d16_stabiliser_hold", "face": CFG["face"], "force_N": CFG["force"],
                            "free_core": CFG["free"], "gravity_off_s": 0.3, "gravity_on_s": 0.3})
        d, dt = self.sim.d, m.opt.timestep
        aid = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, n)  # noqa: E731
        gid = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, n)  # noqa: E731
        acts = [aid("stab_a"), aid("stab_b")]
        g = m.opt.gravity.copy()
        m.opt.gravity[:] = 0.0
        d.ctrl[acts] = -(STAB_OPEN + STAB_OVERSHOOT)
        # D16e fix: gravity stays off until both stabiliser pads squeeze at >= 90 % of the set force (at least 0.3 s,
        # at most 3 s). D16-D16c used a fixed 0.3 s, enough for their pads (damping 100: closing in ~0.07-0.14 s) but
        # not for the damped pads of D16e's first attempt (damping 1000: ~0.7 s), whose cube fell before it was caught.
        sg = [gid("stab_a_g"), gid("stab_b_g")]
        f6, t_hold = np.zeros(6), 0.0
        while True:
            self.sim.step(1)
            t_hold += dt
            tot = {x: 0.0 for x in sg}
            for i in range(d.ncon):
                c = d.contact[i]
                for x in sg:
                    if x in (c.geom1, c.geom2):
                        mujoco.mj_contactForce(m, d, i, f6)
                        tot[x] += f6[0]
            if (t_hold >= 0.3 and min(tot.values()) >= 0.9 * CFG["force"]) or t_hold >= 3.0:
                break
        self.hold_s = t_hold
        m.opt.gravity[:] = g
        self.sim.step(int(round(0.3 / dt)))
        self.sim.step(int(round(settle_s / dt)))
        self.mon.start_trial(d)
        self.mon.new_window()
        self.timing = scored.TurnTiming(turn_s_per_quarter=setup.turn_s_per_quarter) if setup else scored.TurnTiming()
        self.t0_obs = self.ro.observe(d)
        self.core_offset_t0_mm = [float(x) * 1000 for x in d.xpos[self.ro.core]]   # cube centre vs rig centre
        self.tracker = Tracker(m, d, self.ro.core, [gid("stab_a_g"), gid("stab_b_g")], acts, self.mon)
        self.sim.hooks.append(self.tracker)
        self.waits: list[dict] = []
        if CFG.get("settle"):
            self._orig_turn = self.rig.turn
            self.rig.turn = self._settled_turn
        HoldTrial.last = self

    def _settled_turn(self, move, timing=None, record: bool = True):
        """D16b: wait for rest (all cubies and core: |w| < 1 deg/s, core |v| < 1 mm/s; at most 2 s), then ramp the
        turning pads closed over 0.3 s; then the unchanged rig turn (its close step then holds the same target)."""
        sim, d, dt = self.sim, self.sim.d, self.model.opt.timestep
        ids = np.append(self.ro.body_ids, self.ro.core)
        t0, rested = float(d.time), False
        while d.time - t0 < MAX_WAIT_S:
            w = np.degrees(np.linalg.norm(d.cvel[ids, :3], axis=1)).max()
            v = np.linalg.norm(d.cvel[self.ro.core, 3:]) * 1000
            if w < REST_W_DPS and v < REST_V_MMPS:
                rested = True
                break
            self.rig._hold_others()
            sim.step()
        a, b, _ = self.rig.act[move.face]
        n = max(1, int(round(RAMP_S / dt)))
        for k in range(1, n + 1):
            d.ctrl[a] = d.ctrl[b] = self.rig.close_target * k / n
            sim.step()
        self.waits.append({"move": str(move), "wait_s": float(d.time) - t0 - n * dt, "rested": rested})
        return self._orig_turn(move, timing, record)


def configure(cfg: dict) -> None:
    CFG.clear()
    CFG.update(cfg)
    E7._ORIG.clear()
    E7._ORIG.update(trial=HoldTrial, xml=lambda p: g2_xml(_ORIG_XML(p), p))
    M4.build_m1_xml = lambda p: g2_xml(_ORIG_M4_XML(p), p)   # the magnet system's model must match (nv, body ids)
    M4.use_magnets(None, E7.R.GAP)                           # drop any cached magnet system


def run_one(cfg: dict) -> dict:
    configure(cfg)
    f = cfg["face"]
    seq = f"{f} {f}' {f}2 {f}' {f}"
    kw = {"moves": seq, "seed": cfg["seed"], "overrides": {}}
    t0 = time.perf_counter()
    HoldTrial.last = None
    rec, _, _ = E7.run_trial("seq", kw, True)
    rec = E7._plain(rec)
    tr = HoldTrial.last
    tk = tr.tracker if tr is not None else None
    rec["d16"] = {**cfg, "study": "D16", "scored": False, "sequence": seq,
                  "core_slip_mm": None if tk is None else tk.slip * 1000,
                  "core_rot_deg": None if tk is None else float(np.degrees(tk.rot)),
                  "stab_squeeze_N_min": None if not (tk and tk.squeeze) else min(tk.squeeze),
                  "stab_squeeze_N_median": None if not (tk and tk.squeeze) else float(np.median(tk.squeeze)),
                  "stab_actuator_N_median": None if not (tk and tk.act_force) else float(np.median(tk.act_force)),
                  "series_cols": ["t", "squeeze_a_N", "squeeze_b_N", "core_slip_mm", "dx_mm", "dy_mm", "dz_mm",
                                  "core_w_dps"],
                  "series": None if tk is None else tk.series,
                  "pen_cubie_mm_per_move": None if tk is None else tk.pen_cubie,
                  "pen_pad_mm_per_move": None if tk is None else tk.pen_pad,
                  "settle_waits": None if tr is None else tr.waits,
                  "hold_s": None if tr is None else tr.hold_s,
                  "core_offset_t0_mm": None if tr is None else tr.core_offset_t0_mm,
                  "nq": int(tr.model.nq) if tr else None, "wall_s": time.perf_counter() - t0}
    # supplementary check (not G1's): causality with the layer speed relative to the core
    rel = tk.rel_motion_t if tk is not None else []
    for i, pm in enumerate(rec.get("per_move", [])):
        rt = rel[i] if i < len(rel) else None
        tf = pm.get("t_pad_force_s")
        pm["d16_t_layer_motion_rel_core_s"] = rt
        pm["d16_ok_causal_rel_core"] = bool(rt is None or (tf is not None and tf <= rt))
        pm["d16_ok_all_rel_core"] = bool(all(v for k, v in pm.items() if k.startswith("ok_")
                                             and k not in ("ok_all", "ok_causal")) and pm["d16_ok_causal_rel_core"])
    pms = rec.get("per_move", [])
    rec["d16"]["pass_rel_core"] = bool(rec.get("integrity_ok") and "aborted" not in rec and rec.get("t0_solved")
                                       and len(pms) == len(seq.split()) and all(pm["d16_ok_all_rel_core"] for pm in pms)
                                       and rec.get("final_matches_oracle"))
    return rec


def plan() -> list[dict]:
    if STAB_DAMP != 100:                              # D16e: settle-then-turn with a damped stabiliser (D16d screen)
        tag = f"D{STAB_DAMP:g}_"
        jobs = [{"name": f"{tag}{f}_free_F20_s{s}", "face": f, "free": True, "force": 20.0, "mu": 0.8, "seed": s,
                 "settle": True, "stab_damp": STAB_DAMP} for f in ("U", "R", "F") for s in SEEDS]
        jobs += [{"name": f"{tag}U_{'free' if fr else 'fixed'}_F{F:g}_s{s}", "face": "U", "free": fr, "force": F,
                  "mu": 0.8, "seed": s, "settle": True, "stab_damp": STAB_DAMP}
                 for fr in (True, False) for F in (10.0, 30.0, 50.0) for s in SEEDS[:2]]
        return jobs
    jobs = []
    for face in ("U", "R", "F"):
        for free in (True, False):
            for s in SEEDS:
                jobs.append({"name": f"{face}_{'free' if free else 'fixed'}_F20_s{s}", "face": face, "free": free,
                             "force": 20.0, "mu": 0.8, "seed": s})
    for force in (10.0, 30.0, 50.0):
        for s in SEEDS[:2]:
            jobs.append({"name": f"U_free_F{force:g}_s{s}", "face": "U", "free": True, "force": force, "mu": 0.8,
                         "seed": s})
    for force in (10.0, 30.0, 50.0):                  # added after the first 30: fixed-core controls for the sweep
        for s in SEEDS[:2]:
            jobs.append({"name": f"U_fixed_F{force:g}_s{s}", "face": "U", "free": False, "force": force, "mu": 0.8,
                         "seed": s})
    for face in ("U", "R", "F"):                      # D16b: settle-then-turn
        for s in SEEDS:
            jobs.append({"name": f"S_{face}_free_F20_s{s}", "face": face, "free": True, "force": 20.0, "mu": 0.8,
                         "seed": s, "settle": True})
    for free in (True, False):
        for force in (20.0, 50.0):
            for s in SEEDS[:2]:
                if free and force == 20.0:
                    continue                          # already above
                jobs.append({"name": f"S_U_{'free' if free else 'fixed'}_F{force:g}_s{s}", "face": "U", "free": free,
                             "force": force, "mu": 0.8, "seed": s, "settle": True})
    return jobs


def worker(cfg: dict) -> str:
    try:
        rec = run_one(cfg)
    except Exception as e:  # noqa: BLE001  (harness error: recorded, never a pass)
        rec = {"d16": {**cfg, "study": "D16", "scored": False}, "pass": False, "harness_error": repr(e)}
    (OUT / f"{cfg['name']}.json").write_text(json.dumps(rec, indent=1))
    d = rec["d16"]
    return (f"{cfg['name']:22s} pass {rec.get('pass')!s:5s} pass_rel_core {d.get('pass_rel_core')!s:5s} moves_ok {rec.get('moves_completed_ok')} "
            f"core slip {d.get('core_slip_mm') or 0:6.2f} mm rot {d.get('core_rot_deg') or 0:6.2f} deg "
            f"squeeze {d.get('stab_squeeze_N_median') or 0:5.1f} N {rec.get('harness_error', '')}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    jobs = [j for j in plan() if a.only is None or j["name"] == a.only]
    jobs = [j for j in jobs if not (OUT / f"{j['name']}.json").exists()]
    print(f"D16: {len(jobs)} trials, {a.workers} workers", flush=True)
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(a.workers, maxtasksperchild=1) as pool:
        for line in pool.imap_unordered(worker, jobs):
            print(line, flush=True)


if __name__ == "__main__":
    main()
