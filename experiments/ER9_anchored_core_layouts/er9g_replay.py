"""ER9 Part G replay tool (PROTOCOL.md G.7; review X3). Diagnostic only, exploratory and unscored.

Explicit arm registry (any other name is refused; the committed er9_turn_diag.py is not used for Part G arms):
  L0    the composite system with M5's 48 4x2 magnets only (ER7 arm "L0")      reference, self-check
  C52   the composite system with C52's 40 4x3 N52 magnets only (ER7 arm "C52") reference, self-check
  PG8, PG20                                                                    Part G arms (ER7 arm "L0")
  PG20r                                                                        only with --u4-changed
Installation: er9g_layouts.install_er7 with er9g_stats.with_class_stats(M4.RecordingMagnetSystem); the per-class
accumulator is attached once after the setup's reset_stats() and read with ms.stats at the end.

  turn ARM SEED     er9_turn_diag.py's method: setup, grip and the first quarter turn of U of an E1-2 trial (seed
                    16100 in G.7); turner torque, turner angle, layer error, contact sums every 20 steps.
  snap ARM SEED D   ER7's posthoc/snap_diag.py method (one replay of d8_1b_stage1.run_snap's steps, read-only
                    decomposition of the torque about U; states t0, after_release, after_1s, after_5s).
  selfcheck         before any use (G.7): `turn L0 16100` and `turn C52 16100` through the composite must reproduce the
                    committed results/probe/diag/turn_L0_s16100.json and turn_C52_s16100.json in every field those files
                    hold (exact). Reported in addition (not part of pass): `snap L0/C52 16568 +8` against ER7's committed
                    posthoc/snap_{L0,C52}_s16568_+8.json. Writes results/hybrid_g/replay_selfcheck.json (exclusive).
Added to every output: n_magnets, magnet_stats, class_stats (G.4 classes at the arm's D_val), out_of_regime, steps,
step_wall_s, steps_per_s (simulation steps over the stepping wall time), ru_maxrss_kb (peak RSS of this process).
Guards: seeds only 16000-16999; Part G arms need committed, clean code and the arm's gates (D_val from P4.d); any output
inside the repository needs committed, clean code; with uncommitted code only L0 / C52 may run, writing outside the
repository (debugging).
Usage (WSL, repo root): ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9g_replay.py
    turn ARM SEED [--out FILE] | snap ARM SEED DELTA [--out FILE] | selfcheck [--out FILE]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import multiprocessing as mp_
import resource
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("er9g_run", HERE / "er9g_run.py")
if "er9g_run" in sys.modules:
    G = sys.modules["er9g_run"]
else:
    G = importlib.util.module_from_spec(spec); sys.modules["er9g_run"] = G; spec.loader.exec_module(G)
LY, ST, REPO = G.LY, G.ST, G.REPO

REFERENCE_ARMS = ("L0", "C52")
REPLAY_ARMS = REFERENCE_ARMS + G.RUN_ARMS
TURN_REFS = {a: G.ER9_RES / "probe" / "diag" / f"turn_{a}_s16100.json" for a in REFERENCE_ARMS}
SNAP_REFS = {a: REPO / "experiments/ER7_core_magnet_rehearsal/posthoc" / f"snap_{a}_s16568_+8.json"
             for a in REFERENCE_ARMS}
OUT_SELFCHECK = G.ROOT / "replay_selfcheck.json"


def check_replay_arm(arm: str, u4_changed: bool = False) -> str:
    ok = REPLAY_ARMS + ((G.U4_ARM,) if u4_changed else ())
    if arm not in ok:
        raise G.Refused(f"arm {arm!r} is not in the replay registry {ok}")
    return arm


def d_val_for(arm: str) -> float:
    """References: no PC split is in force (inf); Part G arms: P4.d's D_val."""
    return ST.PROXY_D_VAL if arm in REFERENCE_ARMS else G.d_val_for(arm)


def _setup(arm: str, d_val: float):
    P, E7, M4, R = G.mods()
    E7.set_seeds(E7.ER7_GLOBALS)
    LY.install_er7(arm, G.GRADE, cls=ST.with_class_stats(M4.RecordingMagnetSystem))
    E7.setup_arm(G.er7_arm_for(arm))
    ms = M4.use_magnets(R.magnet_params_for({}), R.GAP)
    ms.reset_neighbour_list(); ms.reset_stats()
    acc = ST.attach(ms, d_val)
    return P, E7, M4, R, ms, acc


def _extras(out: dict, ms, acc, d_val: float, steps: int, wall: float) -> dict:
    cs = acc.as_dict(dict(ms.stats))
    out.update({"n_magnets": ms.n, "magnet_stats": dict(ms.stats), "class_stats": cs,
                "out_of_regime": ST.out_of_regime(cs, d_val), "D_val_deg": d_val, "steps": int(steps),
                "step_wall_s": wall, "steps_per_s": steps / wall if wall > 0 else None,
                "ru_maxrss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    return out


def turn(arm: str, seed: int, d_val: float) -> dict:
    """er9_turn_diag.py's replay (lines 45-81), with the arm installed through the composite system."""
    import mujoco
    P, E7, M4, R, ms, acc = _setup(arm, d_val)
    scored, ST8 = E7.scored, M4.ST
    from rubiknetic.cube_logic import parse
    from rubiknetic.cube_logic.geometric import HOME_POSITIONS
    from rubiknetic.cube_physics.m1_model import cubie_name
    setup = scored.draw_setup(seed)
    tr = scored.Trial(scored.params_for(setup), setup)
    m, d, ro = tr.model, tr.sim.d, tr.ro
    cubies = {mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, cubie_name(h)) for h in HOME_POSITIONS}
    samples = []

    def hook(dd):
        if tr.sim.steps % 20:
            return
        n_cc, n_pad, normal_cc, normal_pad, w = 0, 0, 0.0, 0.0, np.zeros(6)
        for i in range(dd.ncon):
            c = dd.contact[i]
            mujoco.mj_contactForce(m, dd, i, w)
            if m.geom_bodyid[c.geom1] in cubies and m.geom_bodyid[c.geom2] in cubies:
                n_cc += 1; normal_cc += float(w[0])
            else:
                n_pad += 1; normal_pad += float(w[0])
        samples.append({"t": float(dd.time), "torque": float(dd.actuator_force[tr.rig.act["U"][2]]),
                        "turner_deg": float(np.degrees(dd.qpos[tr.rig.hinge_qadr["U"]])),
                        "layer_err_deg": float(ST8.layer_error(ro, dd, "U")), "n_cc": n_cc, "normal_cc_N": normal_cc,
                        "n_pad": n_pad, "normal_pad_N": normal_pad})

    tr.sim.hooks.append(hook)
    t_start = d.time
    s0, w0 = tr.sim.steps, time.perf_counter()
    log = tr.rig.turn(parse("U")[0], tr.timing)
    wall, steps = time.perf_counter() - w0, tr.sim.steps - s0
    tq = np.abs(np.array(log.turner_torque))
    k = int(np.argmax(tq))
    out = {"arm": arm, "seed": seed, "grip_force_N": getattr(setup, "grip_force", None),
           "turn_s_per_quarter": tr.timing.turn_s_per_quarter, "peak_torque_Nm": float(tq.max()),
           "t_peak_from_start_s": float(log.t[k] - t_start), "turner_deg_at_peak": float(log.turner_angle_deg[k]),
           "fraction_of_steps_at_clip": float(np.mean(tq >= 0.999)),
           "final_layer_err_deg": float(ST8.layer_error(ro, d, "U")), "samples": samples}
    return _extras(out, ms, acc, d_val, steps, wall)


def snap(arm: str, seed: int, delta: float, d_val: float) -> dict:
    """ER7's posthoc/snap_diag.py (states and torque split about U), with the arm installed through the composite."""
    import mujoco
    from scipy.spatial.transform import Rotation
    P, E7, M4, R, ms, acc = _setup(arm, d_val)
    scored, ST8 = E7.scored, M4.ST
    from rubiknetic.cube_logic.geometric import HOME_POSITIONS
    from rubiknetic.cube_logic.notation import FACE_NORMAL
    from rubiknetic.cube_physics.m1_model import cubie_name
    setup = scored.draw_setup(seed, ST8.SETUP_MISALIGN)
    tr = scored.Trial(scored.params_for(setup), setup)
    m, d, ro = tr.model, tr.sim.d, tr.ro
    m.opt.jacobian = mujoco.mjtJacobian.mjJAC_DENSE
    cubie_bodies = {mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, cubie_name(h)) for h in HOME_POSITIONS}
    nrm = np.array(FACE_NORMAL["U"], float)

    def v_layer():
        v = np.zeros(m.nv)
        for h in HOME_POSITIONS:
            if int(np.dot(h, nrm)) != 1:
                continue
            j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, cubie_name(h) + "_j")
            a = m.jnt_dofadr[j]
            if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_BALL:
                v[a:a + 3] = d.xmat[m.jnt_bodyid[j]].reshape(3, 3).T @ nrm
            else:
                v[a] = float(np.dot(np.array(h, float) / np.linalg.norm(h), nrm))
        return v

    def pieces():
        out = {}
        for h in HOME_POSITIONS:
            b = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, cubie_name(h))
            w, x, y, z = d.xquat[b]
            rv = np.degrees(Rotation.from_quat([x, y, z, w]).as_rotvec())
            u = np.array(h, float) / np.linalg.norm(h)
            spin = float(rv @ u)
            out[cubie_name(h)] = {"kind": {1: "centre", 2: "edge", 3: "corner"}[int(np.count_nonzero(h))],
                                  "in_U_layer": bool(int(np.dot(h, nrm)) == 1), "about_U_deg": float(rv @ nrm),
                                  "spin_about_own_axis_deg": spin, "tangential_deg": float(np.linalg.norm(rv - spin * u))}
        return out

    def state(tag):
        mujoco.mj_forward(m, d)
        J = d.efc_J.reshape(d.nefc, m.nv) if d.nefc else np.zeros((0, m.nv))
        f, typ = d.efc_force[:d.nefc], d.efc_type[:d.nefc]
        v = v_layer()
        fric = typ == mujoco.mjtConstraint.mjCNSTR_FRICTION_DOF
        keep = d.qfrc_passive.copy()
        d.qfrc_passive[:] = 0.0
        ms.apply(m, d)
        q_mag = d.qfrc_passive.copy()
        d.qfrc_passive[:] = keep
        cc = {"n": 0, "normal_N": 0.0, "torque_Nm": 0.0}
        rig = {"n": 0, "normal_N": 0.0, "torque_Nm": 0.0}
        w = np.zeros(6)
        for i in range(d.ncon):
            c = d.contact[i]
            if c.efc_address < 0:
                continue
            b1, b2 = m.geom_bodyid[c.geom1], m.geom_bodyid[c.geom2]
            rows = slice(c.efc_address, c.efc_address + (c.dim if m.opt.cone == mujoco.mjtCone.mjCONE_ELLIPTIC
                                                          else 2 * (c.dim - 1)))
            mujoco.mj_contactForce(m, d, i, w)
            tgt = cc if (b1 in cubie_bodies and b2 in cubie_bodies) else rig
            tgt["n"] += 1
            tgt["normal_N"] += float(w[0])
            tgt["torque_Nm"] += float(v @ (J[rows].T @ f[rows]))
        con_all = np.isin(typ, [mujoco.mjtConstraint.mjCNSTR_CONTACT_FRICTIONLESS,
                                mujoco.mjtConstraint.mjCNSTR_CONTACT_PYRAMIDAL,
                                mujoco.mjtConstraint.mjCNSTR_CONTACT_ELLIPTIC])
        return {"tag": tag, "t": round(d.time, 3), "U_err_deg": ST8.layer_error(ro, d, "U"),
                "magnet_Nm": float(v @ q_mag), "joint_friction_Nm": float(v @ (J[fric].T @ f[fric])),
                "all_contacts_Nm": float(v @ (J[con_all].T @ f[con_all])), "cubie_cubie": cc, "rig_or_core": rig,
                "actuator_Nm": float(v @ d.qfrc_actuator), "max_abs_qvel": float(np.abs(d.qvel).max()),
                "misalignment": ST8.misalignment(ro, d), "pieces": pieces()}

    out = {"arm": arm, "seed": seed, "delta_deg": delta, "states": [state("t0")]}
    s0, w0 = tr.sim.steps, time.perf_counter()
    tr.rig.rotate({"U": np.radians(delta)}, grip=True, timing=tr.timing)
    wall = time.perf_counter() - w0
    out["states"].append(state("after_release"))
    w0 = time.perf_counter()
    tr.sim.step(int(round(1.0 / m.opt.timestep)))
    wall += time.perf_counter() - w0
    out["states"].append(state("after_1s"))
    w0 = time.perf_counter()
    tr.sim.step(int(round(4.0 / m.opt.timestep)))
    wall += time.perf_counter() - w0
    out["states"].append(state("after_5s"))
    return _extras(out, ms, acc, d_val, tr.sim.steps - s0, wall)


# ---- comparison and self-check -------------------------------------------------------------------------------------
def compare(ref, got, path: str = "") -> list[str]:
    """Every field of the reference, exactly (extra fields of the replay are ignored)."""
    if isinstance(ref, dict):
        if not isinstance(got, dict):
            return [f"{path}: type differs"]
        out = []
        for k, v in ref.items():
            out += [f"{path}/{k}: missing"] if k not in got else compare(v, got[k], f"{path}/{k}")
        return out
    if isinstance(ref, list):
        if not isinstance(got, list) or len(ref) != len(got):
            return [f"{path}: length differs"]
        return [x for i, (u, v) in enumerate(zip(ref, got)) for x in compare(u, v, f"{path}[{i}]")]
    return [] if ref == got else [f"{path}: {ref!r} != {got!r}"]


def _normal(x: dict) -> dict:
    return json.loads(json.dumps(x, default=float))


def _job(args: tuple) -> dict:
    kind, arm, seed, extra = args
    if kind == "turn":
        return turn(arm, seed, ST.PROXY_D_VAL)
    return snap(arm, seed, extra, ST.PROXY_D_VAL)


def _fresh(args: tuple) -> dict:
    with mp_.get_context("fork").Pool(1, maxtasksperchild=1) as pool:     # one fresh process per replay
        return _normal(pool.apply(_job, (args,)))


def selfcheck(out: Path, with_snap: bool = True) -> dict:
    res = {"turn": {}, "snap_reported": {}}
    for a in REFERENCE_ARMS:
        got = _fresh(("turn", a, 16100, None))
        ref = json.loads(TURN_REFS[a].read_text())
        d = compare(ref, got)
        res["turn"][a] = {"reference": str(TURN_REFS[a].relative_to(REPO)), "n_diffs": len(d), "diffs": d[:20],
                          "steps_per_s": got["steps_per_s"], "n_magnets": got["n_magnets"]}
    if with_snap:
        for a in REFERENCE_ARMS:
            got = _fresh(("snap", a, 16568, 8.0))
            ref = json.loads(SNAP_REFS[a].read_text())
            d = compare(ref, got)
            res["snap_reported"][a] = {"reference": str(SNAP_REFS[a].relative_to(REPO)), "n_diffs": len(d),
                                       "diffs": d[:20]}
    res["pass"] = all(v["n_diffs"] == 0 for v in res["turn"].values()) and len(res["turn"]) == 2
    res["snap_reported_pass"] = all(v["n_diffs"] == 0 for v in res["snap_reported"].values()) if with_snap else None
    head, probs = G.code_problems()
    res["commit"], res["code_problems"] = head, probs
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "x") as f:
        f.write(json.dumps(res, indent=1, default=float))
    return res


def _guard_out(out: Path | None, arm: str | None) -> None:
    """Part G arms: committed clean code and passing gates. Output inside the repository: committed clean code."""
    if arm is not None and arm not in REFERENCE_ARMS:
        G.require_clean()
        probs = G.gate_problems(arm)
        if probs:
            raise G.Refused(f"{arm}: " + "; ".join(probs))
    if out is not None:
        p = out.resolve()
        if p == REPO or REPO in p.parents:
            G.require_clean()
        if p.exists():
            raise G.Refused(f"refusing to overwrite {p}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("turn", "snap", "selfcheck"))
    ap.add_argument("arm", nargs="?")
    ap.add_argument("seed", nargs="?", type=int)
    ap.add_argument("delta", nargs="?", type=float)
    ap.add_argument("--out")
    ap.add_argument("--u4-changed", action="store_true")
    ap.add_argument("--no-snap", action="store_true", help="selfcheck: skip the reported snap comparison")
    a = ap.parse_args(argv)
    try:
        out = Path(a.out) if a.out else None
        if a.mode == "selfcheck":
            out = out or OUT_SELFCHECK
            _guard_out(out, None)
            r = selfcheck(out, not a.no_snap)
            print(json.dumps({"pass": r["pass"], "turn": {k: v["n_diffs"] for k, v in r["turn"].items()},
                              "snap_reported": {k: v["n_diffs"] for k, v in r["snap_reported"].items()}}, indent=1))
            return
        if a.arm is None or a.seed is None or (a.mode == "snap" and a.delta is None):
            raise G.Refused("usage: turn ARM SEED | snap ARM SEED DELTA")
        check_replay_arm(a.arm, a.u4_changed)
        G.check_seed(a.seed)
        _guard_out(out, a.arm)
        dv = d_val_for(a.arm)
        res = turn(a.arm, a.seed, dv) if a.mode == "turn" else snap(a.arm, a.seed, a.delta, dv)
        res["code"] = dict(zip(("commit", "problems"), G.code_problems()))
        text = json.dumps(res, indent=1, default=float)
        if out is None:
            print(text)
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "x") as f:
                f.write(text)
    except G.Refused as e:
        raise SystemExit(f"REFUSED: {e}") from None


if __name__ == "__main__":
    main()
