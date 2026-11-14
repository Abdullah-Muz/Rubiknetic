"""Rest-throughput benchmark (wall clock; process_time over-counts MuJoCo helper threads) of D5 variants (cube + M1 rig, pads open). UNSCORED.
Usage: uv run python experiments/D5_follower_cube/speed/bench_rest.py [variant ...]"""
import sys
import time
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from variants import VARIANTS, xml_for  # noqa: E402

names = sys.argv[1:] or list(VARIANTS)
for name in names:
    m = mujoco.MjModel.from_xml_string(xml_for(name))
    d = mujoco.MjData(m)
    dt = m.opt.timestep
    for _ in range(int(0.3 / dt)):
        mujoco.mj_step(m, d)
    n = int(0.3 / dt)
    t = time.perf_counter()
    nc = []
    for _ in range(n):
        mujoco.mj_step(m, d)
        nc.append(d.ncon)
    el = time.perf_counter() - t
    print(f"{name:28s} ngeom {m.ngeom:4d} ncon {int(np.mean(nc)):5d} nefc {d.nefc:5d} | {n / el:6.0f} steps/s "
          f"RTF {n * dt / el:.3f} | warning {[int(w.number) for w in d.warning if w.number]}", flush=True)
