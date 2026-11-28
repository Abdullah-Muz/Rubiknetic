"""D25 part 3 (UNSCORED, pilot seed 29001; one simulation process): trajectories and timing, original vs prototype.

Usage: trajectory_bench.py g1|two_arm
* Trajectory equivalence. Each variant builds the scene from scratch with the variant's callback in place before the
  first step, then:
    g1:      Trial's 0.5 s settle (1,000 steps) + one U turn by the G1 rig (TurnRig.turn, the E1-2 path);
    two_arm: the TwoArm start sequence + 2,000 control steps.
  Recorded: SHA-256 of the final qpos / qvel, the step count, a SHA-256 of qpos every 100 steps (first divergence),
  the max |qpos - qpos_original| at the end, and the magnet stats.
  Variants: original, tuned (bit-identical candidate), original again (determinism control), perturbed (sums in
  sequential order: rounding-level differences of about 1e-13 relative, a stand-in for a compiled port).
* Timing. In the last scene, blocks of 300 steps alternate between: the original callback, the tuned callback and no
  callback (both callbacks share the same MagnetSystem state, so switching is seamless); 5 rounds; medians reported.
  Plus the callback alone on the live data.
Writes results/trajectory_bench_<scene>.json."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scenes  # noqa: E402
import fast_magnets as FM  # noqa: E402

from rubiknetic.cube_physics import magnets as MG  # noqa: E402

VARIANTS = {"original": None, "tuned": dict(spline="direct", scatter="blas", body="blas"),
            "original_repeat": None, "perturbed": dict(spline="direct", scatter="bincount", body="bincount")}
clock = time.perf_counter


def sha(a) -> str:
    return hashlib.sha256(np.ascontiguousarray(a, dtype=np.float64).tobytes()).hexdigest()


def run_variant(scene: str, kw):
    holder = {}

    def patch(ms):
        if kw is not None:
            holder["fa"] = FM.patch(ms, **kw)

    hashes = []
    t0 = clock()
    if scene == "g1":
        tr, ms = scenes.g1_scene(29001, patch)
        sim = tr.sim
        hook = lambda d: hashes.append(sha(d.qpos)) if sim.steps % 100 == 0 else None  # noqa: E731
        sim.hooks.append(hook)
        t1 = clock()
        tr.rig.turn(scenes.g1_move("U")[0], tr.timing)
        t_main = clock() - t1
        sim.hooks.remove(hook)
        obj, d, steps = tr, sim.d, int(sim.steps)
        extra = {"turn_wall_s": t_main}
    else:
        r, T = scenes.two_arm(29001, patch)
        ms, d, sim = r.ms, r.d, r.sim
        start_steps = int(sim.steps)
        hook = lambda dd: hashes.append(sha(dd.qpos)) if sim.steps % 100 == 0 else None  # noqa: E731
        sim.hooks.append(hook)
        t1 = clock()
        r.ctrl_step(2000)
        t_main = clock() - t1
        sim.hooks.remove(hook)
        obj, steps = r, int(sim.steps)
        extra = {"start_sequence_steps": start_steps, "wall_2000_steps_s": t_main,
                 "magnet_stats_two_arm": r.magnet_stats()}
    out = {"steps": steps, "wall_total_s": clock() - t0, "qpos_sha256": sha(d.qpos), "qvel_sha256": sha(d.qvel),
           "stats": dict(ms.stats), **extra}
    return out, obj, ms, d, np.array(d.qpos), hashes, holder.get("fa")


def timing(scene, obj, ms, d, fa):
    m = obj.model if scene == "g1" else obj.m
    step = obj.sim.step if scene == "g1" else obj.ctrl_step
    if fa is None:
        fa = FM.FastApply(ms)
    cbs = {"original": lambda mm, dd: MG.MagnetSystem.apply(ms, mm, dd), "tuned": fa.apply, "no_callback": None}
    res = {k: [] for k in cbs}
    for _ in range(5):
        for k, cb in cbs.items():
            mujoco.set_mjcb_passive(cb)
            t = clock()
            step(300)
            res[k].append((clock() - t) / 300 * 1e6)
    cb_only = {"original": [], "tuned": []}
    for _ in range(5):
        for k in cb_only:
            f = cbs[k]
            t = clock()
            for _ in range(200):
                f(m, d)
            cb_only[k].append((clock() - t) / 200 * 1e6)
    med = {k: float(np.median(v)) for k, v in res.items()}
    cmed = {k: float(np.median(v)) for k, v in cb_only.items()}
    return {"us_per_full_step_median": med, "us_per_full_step_all": res,
            "us_per_callback_median": cmed, "us_per_callback_all": cb_only,
            "callback_speedup": cmed["original"] / cmed["tuned"],
            "full_step_speedup": med["original"] / med["tuned"],
            "full_step_speedup_if_callback_free": med["original"] / med["no_callback"],
            "callback_share_original": 1 - med["no_callback"] / med["original"]}


def main(scene):
    res = {"scene": scene, "seed": 29001, "variants": {}}
    q_ref, h_ref = None, None
    last = None
    for name, kw in VARIANTS.items():
        out, obj, ms, d, q, hashes, fa = run_variant(scene, kw)
        if q_ref is None:
            q_ref, h_ref = q, hashes
        div = next((i for i, (a, b) in enumerate(zip(hashes, h_ref)) if a != b), None)
        out.update({"identical_final_qpos_to_original": bool(np.array_equal(q, q_ref)),
                    "max_abs_qpos_diff_vs_original": float(np.max(np.abs(q - q_ref))),
                    "first_differing_100step_checkpoint": None if div is None else div,
                    "n_checkpoints": len(hashes)})
        res["variants"][name] = out
        print(name, json.dumps({k: v for k, v in out.items() if k not in ("stats",)}), flush=True)
        last = (obj, ms, d, fa if name == "tuned" else None)
        if name == "tuned":
            tuned_scene = last
    res["timing"] = timing(scene, tuned_scene[0], tuned_scene[1], tuned_scene[2], tuned_scene[3])
    print(json.dumps(res["timing"], indent=1))
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / f"trajectory_bench_{scene}.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main(sys.argv[1])
