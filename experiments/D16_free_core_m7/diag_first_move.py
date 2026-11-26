"""D16c diagnostic (UNSCORED): step-by-step log of the first move of S_U_free_F20_s21001, whose turning layer moved
(> 5 deg/s, relative to the core) 3 ms after the move began, although the cube had passed the rest check.
Logs per step for the first 0.4 s of the move: the target layer's angular speed about the face axis (world and
relative to the core), the core's, the max |w| over all cubies, and the contacts touching target-layer cubies
(other geom name, normal force). Reads only. Usage (WSL): python diag_first_move.py [name]
"""
from __future__ import annotations

import json
import sys

import mujoco
import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import run as D16  # noqa: E402

from rubiknetic.cube_logic import parse  # noqa: E402
from rubiknetic.cube_logic.notation import FACE_NORMAL  # noqa: E402


def main(name: str = "S_U_free_F20_s21001") -> None:
    cfg = next(j for j in D16.plan() if j["name"] == name)
    D16.configure(cfg)
    E7, M4, scored = D16.E7, D16.M4, D16.scored
    import os
    E7.install(E7.EDGE_R, int(os.environ.get("D16_NOSLIP", E7.NOSLIP)))
    ov = {}
    mp = None if os.environ.get("D16_NOMAG") else E7.R.magnet_params_for(ov)
    ms = M4.use_magnets(mp, E7.R.GAP)
    if ms is not None:
        ms.reset_neighbour_list()
        ms.reset_stats()
    setup = scored.draw_setup(cfg["seed"])
    pkw = {"timestep": float(os.environ["D16_TIMESTEP"])} if os.environ.get("D16_TIMESTEP") else {}
    tr = scored.Trial(scored.params_for(setup, **pkw), setup)
    m, d, ro = tr.model, tr.sim.d, tr.ro
    if os.environ.get("D16_GRAVITY_OFF"):
        m.opt.gravity[:] = 0.0
    mv = parse(f"{cfg['face']}")[0]
    members = ro.layer_members(d, mv.face)
    bodies = ro.body_ids[members]
    ax = np.array(FACE_NORMAL[mv.face], float)
    names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, g) or "" for g in range(m.ngeom)]
    gbody = m.geom_bodyid
    f6 = np.zeros(6)
    rows = []

    def log():
        w_l = float(np.degrees(np.mean(d.cvel[bodies, :3] @ ax)))
        w_c = float(np.degrees(d.cvel[ro.core, :3] @ ax))
        cons = []
        for i in range(d.ncon):
            c = d.contact[i]
            b1, b2 = gbody[c.geom1], gbody[c.geom2]
            if (b1 in bodies) != (b2 in bodies):            # contact between the layer and anything else
                other = c.geom2 if b1 in bodies else c.geom1
                mujoco.mj_contactForce(m, d, i, f6)
                if f6[0] > 0.05:
                    cons.append((names[other] or f"geom{other}", round(float(f6[0]), 2)))
        agg = {}
        for n, f in cons:
            k = n.split("_")[0] + ("_" + n.split("_")[1][:2] if n.startswith(("pad", "stab")) else "")
            agg[k] = round(agg.get(k, 0) + f, 2)
        rows.append({"t": round(float(d.time), 4), "w_layer": round(w_l, 2), "w_core": round(w_c, 2),
                     "w_rel": round(w_l - w_c, 2),
                     "w_max_all": round(float(np.degrees(np.linalg.norm(d.cvel[ro.body_ids, :3], axis=1)).max()), 2),
                     "layer_contacts_N": agg})

    tr.mon.begin_turn(mv.face, members)
    a, b, _ = tr.rig.act[mv.face]
    n = int(round(D16.RAMP_S / m.opt.timestep))
    log()
    for k in range(1, n + 1):
        d.ctrl[a] = d.ctrl[b] = tr.rig.close_target * k / n
        tr.sim.step()
        log()
    tag = f"_m{D16.CORE_MASS:g}_I{D16.CORE_I:g}" if cfg["free"] else ""
    tag += "".join(f"_{k[4:].lower()}{v.replace(' ', '-')}" for k, v in sorted(os.environ.items())
                   if k.startswith("D16_") and k not in ("D16_CORE_MASS", "D16_CORE_I"))
    w = np.array([r["w_max_all"] for r in rows]); wr = np.abs([r["w_rel"] for r in rows])
    print(f"SUMMARY {name}{tag}: w_max_all median {np.median(w):.1f} max {w.max():.1f} deg/s; |w_rel| > 5 in "
          f"{int((wr > 5).sum())}/{len(wr)} steps before pad contact")
    out = D16.OUT / f"diag_first_move_{name}{tag}.json"
    out.write_text(json.dumps(rows, indent=0))


if __name__ == "__main__":
    main(*sys.argv[1:])
