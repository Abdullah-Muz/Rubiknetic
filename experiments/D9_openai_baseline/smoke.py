"""D9 smoke test of the OpenAI-cube adapter (NOT the stage-1 battery).

Usage (WSL): ~/.venvs/rubiknetic/bin/python experiments/D9_openai_baseline/smoke.py <A|B> <step ...>
steps: load | rest | U | sexy | gimbal     (results appended to results/smoke_<variant>.jsonl)
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "D8_alignment"))
import openai_cube as OC  # noqa: E402
import d8_1b_stage1 as S1  # noqa: E402  (harness functions reused unmodified; MS stays None = no magnets)

from rubiknetic.cube_logic import SOLVED, Move  # noqa: E402
from rubiknetic.cube_physics import scored as SC  # noqa: E402

SEED = 5140   # stage-1 seq seed (6move); diagnostic range
LAST: list = []


class _KeepTrial(SC.Trial):  # read-only capture of the trial object for post-hoc diagnostics
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        LAST.append(self)


def check_physics_unchanged(m) -> dict:
    """Compare every OpenAI joint/geom/body parameter in the trial model with the stripped source model."""
    src = OC.SRC_XML.read_text()
    for pat in (r"\s*<texture[^>]*/>", r"\s*<material[^>]*/>", r'\s*material="[^"]*"'):
        src = re.sub(pat, "", src)
    m0 = mujoco.MjModel.from_xml_string(src, {"roundcube.msh": OC.SRC_MSH.read_bytes()})
    bad = []
    for j in range(m0.njnt):
        name = m0.joint(j).name
        if name.startswith("cube:"):
            continue  # the 4 removed core joints (fixed core, disclosed)
        k = m.joint(name).id
        da, db = m0.jnt_dofadr[j], m.jnt_dofadr[k]
        for f in ("type", "axis", "pos", "range", "limited", "stiffness", "solref", "solimp", "margin"):
            if not np.allclose(np.atleast_1d(getattr(m0, "jnt_" + f)[j]), np.atleast_1d(getattr(m, "jnt_" + f)[k])):
                bad.append(f"joint {name}.{f}")
        for f in ("damping", "armature", "frictionloss"):
            if not np.isclose(getattr(m0, "dof_" + f)[da], getattr(m, "dof_" + f)[db]):
                bad.append(f"joint {name}.{f}")
        if not np.isclose(m0.qpos_spring[m0.jnt_qposadr[j]], m.qpos_spring[m.jnt_qposadr[k]]):
            bad.append(f"joint {name}.springref")
    for g in range(m0.ngeom):
        a = m0.geom(g)
        bname = m0.body(int(m0.geom_bodyid[g])).name   # map by body (some source geoms may be unnamed)
        if bname.startswith("cubelet:"):
            bname = OC.cubie_name(OC._home_from_name(bname.split(":", 1)[1]))
        elif bname == "middle":
            bname = "core"
        bid = m.body(bname).id
        b = m.geom(int(m.body_geomadr[bid] + (g - m0.body_geomadr[int(m0.geom_bodyid[g])])))
        name = f"{bname}/{a.name or g}"
        for f in ("type", "size", "friction", "condim", "solref", "solimp", "solmix", "margin", "gap", "contype",
                  "conaffinity", "priority", "pos", "quat"):
            if not np.allclose(np.atleast_1d(getattr(a, f)), np.atleast_1d(getattr(b, f))):
                bad.append(f"geom {name}.{f}")
        if not np.isclose(m0.body_mass[a.bodyid], m.body_mass[b.bodyid]):
            bad.append(f"mass {name}")
        if not np.allclose(m0.body_inertia[a.bodyid], m.body_inertia[b.bodyid]):
            bad.append(f"inertia {name}")
    mid = m.geom(OC.cubie_name((1, 0, 0)) + "_g").dataid[0]
    v = m.mesh_vert[m.mesh_vertadr[mid]:m.mesh_vertadr[mid] + m.mesh_vertnum[mid]]
    return {"mismatches": bad, "n_checked_joints": m0.njnt - 4, "n_checked_geoms": m0.ngeom,
            "mesh_extent_mm": ((v.max(0) - v.min(0)) * 1e3).round(4).tolist()}


def main() -> None:
    variant, steps = sys.argv[1], sys.argv[2:]
    OC.install(variant)
    SC.Trial = _KeepTrial
    out = HERE / "results" / f"smoke_{variant}.jsonl"
    out.parent.mkdir(exist_ok=True)

    def emit(rec):
        rec = {"variant": variant, "mujoco": mujoco.__version__, **rec}
        with out.open("a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        print(json.dumps(rec, default=str)[:1500], flush=True)

    for step in steps:
        t = time.perf_counter()
        if step == "load":
            setup = SC.draw_setup(SEED, S1.SETUP_MISALIGN)
            p = SC.params_for(setup)
            m = mujoco.MjModel.from_xml_string(SC.build_m1_xml(p))
            emit({"step": "load", "nbody": m.nbody, "njnt": m.njnt, "nq": m.nq, "nv": m.nv, "ngeom": m.ngeom,
                  "nu": m.nu, "timestep": m.opt.timestep, "integrator": int(m.opt.integrator),
                  "iterations": m.opt.iterations, "physics_check": check_physics_unchanged(m)})
        elif step == "rest":
            setup = SC.draw_setup(SEED, S1.SETUP_MISALIGN)
            tr = SC.Trial(SC.params_for(setup), setup)       # setup misalignment + 0.5 s settle (harness default)
            ro, d, m = tr.ro, tr.sim.d, tr.model
            _, r0 = ro.poses(d)
            q0 = d.qpos.copy()
            mis0 = S1.misalignment(ro, d)
            tr.sim.step(int(round(0.5 / m.opt.timestep)))     # 0.5 s at rest, pads open, no commands
            _, r1 = ro.poses(d)
            rot = max(float(np.degrees(np.arccos(np.clip((np.trace(r1[i] @ r0[i].T) - 1) / 2, -1, 1))))
                      for i in range(26))
            obs = ro.observe(d)
            emit({"step": "rest", "seed": SEED, "setup_misalign_deg": setup.misalign_deg,
                  "t0_solved": bool(tr.t0_obs.valid and tr.t0_obs.state == SOLVED),
                  "misalignment_after_settle": mis0, "misalignment_after_rest": S1.misalignment(ro, d),
                  "max_piece_rotation_during_0p5s_rest_deg": rot, "max_abs_qvel_end": float(np.abs(d.qvel).max()),
                  "max_abs_dqpos": float(np.abs(d.qpos - q0).max()), "nan": bool(np.isnan(d.qpos).any()),
                  "radial_offset_mm": tr.radial_offset_mm(), "solved_end": bool(obs.valid and obs.state == SOLVED),
                  "ncon": int(d.ncon), "hinge_min_singular": min(OC.hinge_conditioning(m, d).values()),
                  "integrity_ok": not tr.sim.violations and not tr.sim.numerical_failures,
                  "wall_s": time.perf_counter() - t, "sim_s": float(d.time)})
        elif step in ("U", "sexy"):
            moves = "U" if step == "U" else "R U R' U'"
            rec = S1.run_seq(moves, SEED)                     # unmodified stage-1 harness function
            tr = LAST[-1]
            cond = OC.hinge_conditioning(tr.model, tr.sim.d)
            rec.pop("params", None)
            rec.update({"step": step, "wall_s": time.perf_counter() - t,
                        "steps_per_s": rec["sim_time_s"] / tr.model.opt.timestep / (time.perf_counter() - t),
                        "hinge_min_singular_end": min(cond.values()),
                        "hinge_worst_pieces_end": sorted(cond.items(), key=lambda kv: kv[1])[:4]})
            emit(rec)
        elif step == "gimbal":
            # One F turn (axis -y) by the rig, then hinge-chain conditioning of the F-layer pieces.
            setup = SC.draw_setup(SEED, S1.SETUP_MISALIGN)
            tr = SC.Trial(SC.params_for(setup), setup)
            ro, d = tr.ro, tr.sim.d
            before = OC.hinge_conditioning(tr.model, d)
            log = tr.rig.turn(Move("F", 1), tr.timing)
            after = OC.hinge_conditioning(tr.model, d)
            obs = ro.observe(d)
            emit({"step": "gimbal", "move": "F", "min_singular_before": min(before.values()),
                  "min_singular_after": min(after.values()),
                  "pieces_singular_after": {k: v for k, v in after.items() if v < 0.05},
                  "observed_valid": obs.valid, "state_is_F": bool(obs.valid and obs.state == SOLVED.apply(Move("F", 1))),
                  "max_turner_torque_Nm": float(np.max(np.abs(log.turner_torque))),
                  "integrity_ok": not tr.sim.violations and not tr.sim.numerical_failures,
                  "wall_s": time.perf_counter() - t})


if __name__ == "__main__":
    main()
