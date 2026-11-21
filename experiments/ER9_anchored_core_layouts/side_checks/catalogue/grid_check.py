"""Check of the 12001-point integration grid in cyl_pair.py against the 120001-point values kept in targets_fine_grid.json."""
import json, sys
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cyl_pair as CP
ref = json.loads((HERE / "targets_fine_grid.json").read_text())
worst = 0.0
for arm, a in ref["arms"].items():
    p = CP.pair(0.004, 0.003, a["Br_eff_T"], a["face_gap_mm"] * 1e-3)
    for k in ("pull_N", "kz_N_per_m", "klat_N_per_m", "energy_mJ"):
        worst = max(worst, abs(p[k] / a["charge"][k] - 1))
# smallest d/a used anywhere in the scan: gap 0.5 mm, 4.1 mm diameter
print("max relative difference, 12001 vs 120001 points:", worst)
print("len grid:", len(CP._T), "pull 2x1 N48 gap 1.0:", CP.pull(0.002, 0.001, 1.395, 0.001))
