"""Dump the exact ER9 magnet positions (anchored and hybrid) to JSON. Reads the repo, writes only next to this file.
Run (WSL): cd /mnt/c/dev/Rubiknetic && PYTHONDONTWRITEBYTECODE=1 ~/.venvs/rubiknetic/bin/python -B <this file>
No simulation is run: only the layout functions are called.
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = Path("/mnt/c/dev/Rubiknetic")
spec = importlib.util.spec_from_file_location("er9_hybrid", REPO / "experiments/ER9_anchored_core_layouts/er9_hybrid.py")
H = importlib.util.module_from_spec(spec); sys.modules["er9_hybrid"] = H; spec.loader.exec_module(H)

from rubiknetic.cube_physics.m1_model import M1Params  # noqa: E402
from rubiknetic.cube_physics.magnets import REAL_RADIUS, MagnetParams  # noqa: E402


def ser(mags):
    return [{"body": m["body"], "kind": m["kind"], "pos": [float(x) for x in m["pos"]],
             "dir": [float(x) for x in m["dir"]]} for m in mags]


out = {"REAL_RADIUS": REAL_RADIUS, "EDGE_OPT": list(H.EDGE_OPT), "CORNER_OPT": list(H.CORNER_OPT)}
p = M1Params(**{**H.M4.BASE_OVERRIDES, "gap": H.R.GAP})
out["m1"] = {"pitch": p.pitch, "gap": p.gap, "chamfer": p.chamfer, "base_overrides": H.M4.BASE_OVERRIDES}

# anchored layout as in Parts A-D: 4 x 3 mm magnet, clearance 0.2 mm
mp = MagnetParams(diameter=0.004, length=0.003, grade="N35")
out["mp"] = {"diameter": mp.diameter, "length": mp.length, "wall": mp.wall}
out["anchored_c0.2"] = ser(H.LAY.anchored_core_layout(mp, 2e-4, H.EDGE_OPT, H.CORNER_OPT))
for c in (1, 2, 3):
    cfg = H.cfg_for(c)
    mpc, mags = H.hybrid_mags(cfg)
    assert (mpc.diameter, mpc.length, mpc.wall) == (mp.diameter, mp.length, mp.wall)
    out[f"hybrid_c{c}"] = ser(mags)
for k in ("anchored_c0.2", "hybrid_c1", "hybrid_c2", "hybrid_c3"):
    print(k, len(out[k]), {kk: sum(1 for m in out[k] if m["kind"] == kk) for kk in sorted({m["kind"] for m in out[k]})})
(HERE / "positions.json").write_text(json.dumps(out, indent=1))
print("wrote", HERE / "positions.json")
