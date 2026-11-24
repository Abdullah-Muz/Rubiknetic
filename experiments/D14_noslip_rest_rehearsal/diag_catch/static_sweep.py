"""Static geometry sweep (diagnostic only). From a saved qpos at the turn's ramp start, rotate the turning layer rigidly
(each piece keeps its own tilt) about the face normal by theta and report cubie-cubie overlaps between the layer and the
rest. Variant 'ideal': the same, but every layer piece's tilt removed (piece orientation = pure rotation about the
face normal), to separate the pieces' tilt from the shapes themselves."""
import gzip, json, sys, glob
from pathlib import Path
import numpy as np
sys.path.insert(0, "/mnt/c/dev/Rubiknetic/src")
import mujoco
from scipy.spatial.transform import Rotation as Rot
from rubiknetic.cube_physics.m1_model import M1Params, build_m1_xml, cubie_name, HOME_POSITIONS
from rubiknetic.cube_logic.notation import FACE_NORMAL

HERE = Path(__file__).resolve().parent


def model_for(params):
    kw = {k: (tuple(v) if isinstance(v, list) else v) for k, v in params.items()}
    return mujoco.MjModel.from_xml_string(build_m1_xml(M1Params(**kw)))


def sweep(f, ideal=False, thetas=np.arange(0, 12.01, 0.25)):
    D = json.load(gzip.open(f)); s = D["s"]; face = D["face"]
    m = model_for(D["params"]); d = mujoco.MjData(m)
    q0 = np.array(s["qpos_ramp_start"])
    n = np.array(FACE_NORMAL[face], float)
    members = s["members"]
    jadr = [int(m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, cubie_name(HOME_POSITIONS[i]) + "_j")])
            for i in members]
    cen = cubie_name(tuple(int(x) for x in n)) + "_j"
    cadr = int(m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, cen)])
    gids = {int(mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, cubie_name(h) + "_g")): cubie_name(h) for h in HOME_POSITIONS}
    layer_g = set(int(mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, cubie_name(HOME_POSITIONS[i]) + "_g")) for i in members)
    base = q0.copy()
    if ideal:  # strip tilt: keep only the twist about n
        for a in jadr:
            w, x, y, z = base[a:a + 4]
            R = Rot.from_quat([x, y, z, w]).as_matrix()
            # nearest rotation that maps n to n: swing-twist decomposition, keep twist
            rv = Rot.from_matrix(R)
            qx, qy, qz, qw = rv.as_quat()
            proj = np.dot([qx, qy, qz], n) * n
            tw = np.array([*proj, qw]); tw /= np.linalg.norm(tw)
            base[a:a + 4] = [tw[3], tw[0], tw[1], tw[2]]
    out = []
    for th in thetas:
        q = base.copy()
        rq = Rot.from_rotvec(-np.radians(th) * n)          # clockwise turn = negative about the outward normal
        for a in jadr:
            w, x, y, z = q[a:a + 4]
            x2, y2, z2, w2 = (rq * Rot.from_quat([x, y, z, w])).as_quat()
            q[a:a + 4] = [w2, x2, y2, z2]
        q[cadr] -= np.radians(th)
        d.qpos[:] = q
        mujoco.mj_fwdPosition(m, d)
        worst, wpair, wn = 0.0, None, None
        for i in range(d.ncon):
            c = d.contact[i]
            g1, g2 = int(c.geom1), int(c.geom2)
            if g1 not in gids or g2 not in gids or ((g1 in layer_g) == (g2 in layer_g)):
                continue
            if c.dist < worst:
                fr = np.array(c.frame).reshape(3, 3)
                worst, wpair, wn = float(c.dist), (gids[g1], gids[g2]), float(abs(fr[0] @ n))
        out.append((float(th), worst * 1000, wpair, wn))
    return out


if __name__ == "__main__":
    files = sorted(glob.glob(str(HERE / "raw/diag3g/*.json.gz"))) + sorted(glob.glob(str(HERE / "raw/diag3nog/*.json.gz")))
    res = {}
    for f in files:
        key = Path(f).parent.name + "/" + Path(f).name.replace(".json.gz", "")
        for ideal in (False, True):
            r = sweep(f, ideal)
            res[key + (" ideal" if ideal else "")] = r
            pk = min(r, key=lambda x: x[1])
            sel = {t: round(v, 3) for t, v, _, _ in r if t in (0, 2, 4, 5, 5.5, 6, 6.25, 6.5, 7, 8, 10)}
            print(f"{key:28s} {'ideal' if ideal else 'as-is'}: worst overlap {pk[1]:.3f} mm at {pk[0]:.2f} deg {pk[2]} |n.axis| {pk[3]}")
            print("     overlap (mm) by angle:", sel)
    json.dump(res, open(HERE / "static_sweep.json", "w"), indent=0)
