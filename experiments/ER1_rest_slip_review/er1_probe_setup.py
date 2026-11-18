"""ER1 probes 2 and 3 (exploratory, post hoc; analysis only).
Probe 2: for each E1-1 seed 10000-10019, cubie-cubie overlap created by the setup misalignment, measured right after
          apply_setup_misalignment and before any simulation step (MuJoCo contact distances, negative = overlap).
Probe 3: rest trials (frozen M5 magnet arm, D10 instrumented loop) for seeds 10001 and 10000 with the setup
          misalignment replaced by (a) zero on all faces, (b) only U at its drawn value (one legal layer turn).
Writes experiments/ER1_rest_slip_review/results/probe_setup.json."""
from __future__ import annotations

import dataclasses
import importlib.util
import json
import multiprocessing as mp_
import sys
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
spec = importlib.util.spec_from_file_location("d10_rest", REPO / "experiments/D10_m5_rest_diagnostic/d10_rest.py")
D10 = importlib.util.module_from_spec(spec); sys.modules["d10_rest"] = D10; spec.loader.exec_module(D10)


def setup_overlap(seed: int) -> dict:
    M5 = D10._load_m5(); M4 = M5.M4
    from rubiknetic.cube_physics import scored
    from rubiknetic.cube_physics.m1_model import build_m1_xml
    from rubiknetic.cube_physics.readout import CubeReadout
    from rubiknetic.cube_physics.rig import AuditedSim
    M4.use_magnets(M5.magnet_params_for({}), M5.GAP)
    setup = scored.draw_setup(seed)
    p = scored.params_for(setup)
    m = mujoco.MjModel.from_xml_string(build_m1_xml(p))
    sim = AuditedSim(m)
    mujoco.mj_forward(m, sim.d)
    base = [float(sim.d.contact[k].dist) for k in range(sim.d.ncon)]
    scored.apply_setup_misalignment(sim, setup.misalign_deg)
    ro = CubeReadout(m, p.pitch)
    cub = set(int(g) for g in ro.geom_ids)
    d = sim.d
    dists = [float(d.contact[k].dist) for k in range(d.ncon)
             if int(d.contact[k].geom1) in cub and int(d.contact[k].geom2) in cub]
    return {"seed": seed, "misalign_deg": setup.misalign_deg,
            "aligned_min_dist_mm": min(base) * 1e3 if base else None,
            "setup_min_dist_mm": min(dists) * 1e3 if dists else None,
            "setup_n_overlap_gt_0p02mm": int(sum(x < -2e-5 for x in dists)),
            "setup_n_overlap_gt_0p05mm": int(sum(x < -5e-5 for x in dists))}


def rest_variant(job) -> dict:
    seed, variant = job
    M5 = D10._load_m5(); M4 = M5.M4
    from rubiknetic.cube_physics import scored
    orig = scored.draw_setup

    def patched(s, *a, **k):
        st = orig(s, *a, **k)
        mis = {f: 0.0 for f in st.misalign_deg}
        if variant == "U_only":
            mis["U"] = st.misalign_deg["U"]
        return dataclasses.replace(st, misalign_deg=mis)
    scored.draw_setup = patched
    ms = M4.use_magnets(M5.magnet_params_for({}), M5.GAP)
    ms.reset_neighbour_list(); ms.reset_stats()
    rec = D10.instrumented_rest(scored, M4, seed, 10.0, ms)
    at = D10.attribute(rec)
    return {"seed": seed, "variant": variant, "peak_deg": rec["rest_rotation_deg"], "attribution": at,
            "penetration_mm": rec["penetration_mm"], "final_solved": rec["final_solved"],
            "aborted": rec.get("aborted")}


if __name__ == "__main__":
    ctx = mp_.get_context("fork")
    with ctx.Pool(6, maxtasksperchild=1) as pool:
        overlaps = pool.map(setup_overlap, range(10000, 10020))
        rests = pool.map(rest_variant, [(s, v) for s in (10001, 10000) for v in ("zero", "U_only")])
    out = HERE / "results"; out.mkdir(exist_ok=True)
    (out / "probe_setup.json").write_text(json.dumps({"env": D10.environment(), "overlaps": overlaps, "rests": rests},
                                                     indent=1))
    for o in overlaps:
        print(o["seed"], f"aligned min {o['aligned_min_dist_mm']}", f"setup min {o['setup_min_dist_mm']:.4f} mm",
              o["setup_n_overlap_gt_0p02mm"], o["setup_n_overlap_gt_0p05mm"])
    for r in rests:
        a = r["attribution"]
        print(r["seed"], r["variant"], f"peak {r['peak_deg']:.4f}", a["peak_cubie"], a["label"], r["aborted"])
