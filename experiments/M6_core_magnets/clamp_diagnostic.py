"""M6 post-run diagnostic (not a pass criterion): which near pairs fall below the table z range during a U turn.
Usage (WSL): ~/.venvs/rubiknetic/bin/python experiments/M6_core_magnets/clamp_diagnostic.py
"""
import sys, importlib.util, json
from pathlib import Path
import numpy as np, mujoco
REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("m6", REPO/"experiments/M6_core_magnets/m6_checks.py")
m6 = importlib.util.module_from_spec(spec); sys.modules["m6"]=m6; spec.loader.exec_module(m6)
M = m6.M
spline = M.near_field_tables(m6.MP, m6.TABLES)
m, d = m6.build(); ms = m6.system(m, spline)
core = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "core")
ii, jj = ms.ii_all, ms.jj_all
zmin = m6.MP.length + 1e-4
rows = {}
for f in ("U",):
    nrm = np.array(m6.FACE_NORMAL[f], float)
    for deg in range(-90, 91):
        m6.pose_layer(m, d, nrm, np.radians(deg))
        p, n = ms.world(d.xpos, d.xmat)
        rv = p[jj]-p[ii]; r = np.linalg.norm(rv, axis=1)
        near = r < m6.MP.r2
        cosn = np.einsum("ij,ij->i", n[ii], n[jj])
        for k in np.nonzero(near)[0]:
            z = rv[k] @ n[ii[k]]; rho = np.linalg.norm(rv[k] - z*n[ii[k]])
            if abs(z) < zmin:
                a, b = ms.mags[ii[k]], ms.mags[jj[k]]
                key = (a["kind"], b["kind"])
                rows.setdefault(key, []).append((deg, round(abs(z)*1e3,3), round(rho*1e3,3), round(r[k]*1e3,3), round(np.degrees(np.arccos(min(1,abs(cosn[k])))),1)))
for key, v in rows.items():
    degs = sorted({x[0] for x in v})
    print(key, "n", len(v), "deg range", degs[0], degs[-1], "count of degs", len(degs))
    print("  min|z|", min(x[1] for x in v), "rho range", min(x[2] for x in v), max(x[2] for x in v), "r range", min(x[3] for x in v), max(x[3] for x in v), "tilt", min(x[4] for x in v), max(x[4] for x in v))
    print("  sample", [x for x in v if x[0] in (degs[0], 45, degs[-1])][:6])
# weight of correction at those r: w(r)
print("r1,r2", m6.MP.r1, m6.MP.r2)
