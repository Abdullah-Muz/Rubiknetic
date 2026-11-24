"""Diagnostic: static sweep of saved catch poses with the 45 deg chamfer and rounded edges R 1.4 / 2.5 mm."""
import sys, os
from pathlib import Path
D = str(Path(__file__).resolve().parent); sys.path.insert(0, D); sys.path.insert(0, str(Path(D).parents[2] / "src"))
import edge_patch, static_sweep
from rubiknetic.cube_physics import m1_model
orig = m1_model._chamfered_box_vertices
for R in (None, "1.4", "2.5"):
    m1_model._chamfered_box_vertices = orig if R is None else (lambda h, c, R=R: edge_patch.rounded_box_vertices(h, float(R) / 1000))
    for name in ("diag3g/PG20_U_s16100", "diag3g/L0_R_s16100", "diag3g/PG20_U_s16101", "diag3nog/L0_R_s16100"):
        r = static_sweep.sweep(f"{D}/raw/{name}.json.gz")
        sel = {t: round(v, 3) for t, v, _, _ in r if t in (0, 4, 5, 5.5, 6, 6.5, 7, 8, 10, 12)}
        print(f"R={R or 'chamfer'} {name}: {sel}")
