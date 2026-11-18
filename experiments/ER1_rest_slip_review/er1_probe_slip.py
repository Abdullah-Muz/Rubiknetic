"""ER1 (engineering review of the M5 rest slip), probe 1: re-simulate one rest seed at the frozen M5 settings
(the D10 A0i path, bit-identical to M5) and dump cubie positions, rotation vectors and cubie-cubie contacts at
chosen times. Analysis only; writes experiments/ER1_rest_slip_review/results/probe_slip_s<seed>.json."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

from rubiknetic.cube_logic import HOME_POSITIONS

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
spec = importlib.util.spec_from_file_location("d10_rest", REPO / "experiments/D10_m5_rest_diagnostic/d10_rest.py")
D10 = importlib.util.module_from_spec(spec); sys.modules["d10_rest"] = D10; spec.loader.exec_module(D10)


def snapshot(m, d, ro, r0, p0, names):
    pos, rots = ro.poses(d)
    out = {"t": float(d.time), "cubies": {}, "contacts": []}
    for i, n in enumerate(names):
        rv = Rotation.from_matrix(rots[i] @ r0[i].T).as_rotvec(degrees=True)
        out["cubies"][n] = {"disp_mm": ((pos[i] - p0[i]) * ro.pitch * 1e3).tolist(), "rotvec_deg": rv.tolist()}
    f6 = np.zeros(6)
    gid = {int(g): names[i] for i, g in enumerate(ro.geom_ids)}
    for k in range(d.ncon):
        c = d.contact[k]
        a, b = gid.get(int(c.geom1)), gid.get(int(c.geom2))
        mujoco.mj_contactForce(m, d, k, f6)
        out["contacts"].append({"a": a or mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, int(c.geom1)),
                                "b": b or mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, int(c.geom2)),
                                "dist_mm": float(c.dist * 1e3), "normal": c.frame[:3].tolist(),
                                "fn_N": float(f6[0]), "ft_N": float(np.hypot(f6[1], f6[2])), "pos_mm": (c.pos * 1e3).tolist()})
    # signed distances between all face-adjacent cubie pairs (mj_geomDistance, 2 mm cap)
    ft = np.zeros(6)
    homes = {n: np.array(h) for n, h in zip(names, HOME_POSITIONS)}
    out["pair_dist_mm"] = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if np.abs(homes[a] - homes[b]).sum() == 1:
                out["pair_dist_mm"][a + "|" + b] = float(mujoco.mj_geomDistance(
                    m, d, int(ro.geom_ids[names.index(a)]), int(ro.geom_ids[names.index(b)]), 0.002, ft) * 1e3)
    return out


def main(seed: int, times: list[float]) -> None:
    M5 = D10._load_m5(); M4 = M5.M4
    from rubiknetic.cube_physics import scored
    ms = M4.use_magnets(M5.magnet_params_for({}), M5.GAP)
    ms.reset_neighbour_list(); ms.reset_stats()
    setup = scored.draw_setup(seed)
    tr = scored.Trial(scored.params_for(setup), setup)
    m, d, ro = tr.model, tr.sim.d, tr.ro
    names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, int(b)) for b in ro.body_ids]
    p0, r0 = ro.poses(d)
    snaps = [snapshot(m, d, ro, r0, p0, names)]
    t_start = d.time
    for t in times:
        n = int(round((t_start + t - d.time) / m.opt.timestep))
        tr.sim.step(n)
        s = snapshot(m, d, ro, r0, p0, names)
        if ms.last is not None:
            p, F, T, U = ms.last
            Tb = ms.body_sum @ (T + np.cross(p - d.xpos[ms.body], F))
            bn = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, int(b)) for b in ms.bodies]
            s["magnet_torque_mNm"] = {bn[i]: (Tb[i] * 1e3).tolist() for i in range(len(bn))}
        snaps.append(s)
    out = HERE / "results"; out.mkdir(exist_ok=True)
    (out / f"probe_slip_s{seed}.json").write_text(json.dumps({"seed": seed, "env": D10.environment(), "snaps": snaps}))
    print("written", seed)


if __name__ == "__main__":
    main(int(sys.argv[1]), [float(x) for x in sys.argv[2:]])
