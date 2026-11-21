"""Check: charge-model coaxial pull of a 4x3 N35 x 0.756 pair at the hybrid arms' gaps, against scale.json (sim law)."""
import json, sys
from pathlib import Path
import numpy as np
R = Path("/mnt/c/dev/Rubiknetic")
sys.path.insert(0, str(R / "src"))
from rubiknetic.cube_physics.magnets import MagnetParams, _exact_energy_tilted, TABLE_QUAD
import inspect
print(inspect.signature(MagnetParams))
mp = MagnetParams(diameter=4e-3, length=3e-3, grade="N35", scale=0.756)
mp1 = MagnetParams(diameter=4e-3, length=3e-3, grade="N35", scale=1.0)
print("moment ratio", mp.moment / mp1.moment, "sqrt", 0.756 ** 0.5)
I = np.eye(3)
def U(z): return _exact_energy_tilted(mp.diameter / 2, mp.length, mp.moment, 0.0, z, I, *TABLE_QUAD)
h = 2e-5
for c in (0.2e-3, 1e-3, 2e-3, 3e-3):
    z = c + 2 * 0.4e-3 + mp.length
    F = (U(z + h) - U(z - h)) / (2 * h)
    print(f"c {c*1e3:.1f} mm  centre dist {z*1e3:.1f} mm  charge-model pull {abs(F):.4f} N")
print(json.loads((R / "experiments/ER9_anchored_core_layouts/results/hybrid/scale.json").read_text()))
