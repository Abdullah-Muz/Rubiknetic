"""Checks that er9_layout.anchored_core_layout (used by the dynamic probe) places every magnet exactly where
er9_screen.anchored_layout (used by the static screen) does, for C52 and for each probe arm.
Usage (WSL, repo root):  ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/er9_layout_check.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


S = _load("er9_screen", "experiments/ER9_anchored_core_layouts/er9_screen.py")
L = _load("er9_layout", "experiments/ER9_anchored_core_layouts/er9_layout.py")
from rubiknetic.cube_physics.magnets import MagnetParams, core_layout  # noqa: E402

sc = json.loads((HERE / "results" / "screen.json").read_text())
rows = {r["variant"]: r for r in sc["rows"]}
cases = {"C52": (("axis",), ("axis",))}
for key in ("selected", "runner_up"):
    if sc.get(key):
        cases[sc[key]] = (tuple(rows[sc[key]]["edge_opt"]), tuple(rows[sc[key]]["corner_opt"]))
out = {}
for name, (eo, co) in cases.items():
    mp = MagnetParams(diameter=0.004, length=0.003, grade="N52")
    a = S.anchored_layout(S.MP43, S.CLEAR, eo, co)
    b = L.anchored_core_layout(mp, S.CLEAR, eo, co)
    same = (len(a) == len(b) and all(x["body"] == y["body"] for x, y in zip(a, b))
            and np.allclose([x["pos"] for x in a], [y["pos"] for y in b], rtol=0, atol=1e-15)
            and np.allclose([x["dir"] for x in a], [y["dir"] for y in b], rtol=0, atol=1e-15))
    out[name] = {"n_magnets": len(b), "identical": bool(same)}
ref = core_layout(MagnetParams(diameter=0.004, length=0.003, grade="N52"), S.CLEAR)
c52 = L.anchored_core_layout(MagnetParams(diameter=0.004, length=0.003, grade="N52"), S.CLEAR, ("axis",), ("axis",))
out["C52_equals_magnets.core_layout"] = bool(
    len(ref) == len(c52) and all(x["body"] == y["body"] for x, y in zip(ref, c52))
    and np.array_equal([x["pos"] for x in ref], [y["pos"] for y in c52])
    and np.array_equal([x["dir"] for x in ref], [y["dir"] for y in c52]))
out["pass"] = bool(all(v["identical"] for k, v in out.items() if isinstance(v, dict)) and out["C52_equals_magnets.core_layout"])
(HERE / "results" / "layout_check.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
