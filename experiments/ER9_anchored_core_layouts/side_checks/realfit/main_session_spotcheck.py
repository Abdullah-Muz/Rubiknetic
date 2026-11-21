"""Independent spot-check of the fit agent's key claim: along an anchor pair's radial line, where does the piece's
material start and end in the real-mechanism CAD? (numbers only; geometry is not written anywhere)"""
import json
from pathlib import Path
import numpy as np
import trimesh
S = Path("/mnt/c/Users/abdul/AppData/Local/Temp/claude/ab701ba819fd63b8/8d1f9a13-9c26-453c-8133-d81f43b82083/scratchpad")
pos = json.loads((S / "fit/positions.json").read_text())["anchored_c0.2"]
sc = trimesh.load("/mnt/c/dev/Rubiknetic/third_party_cad/Assembled_Rubiks_Cube.glb")
pieces = [g for g in sc.dump(concatenate=False) if g.metadata.get("name", "").startswith(("Edge Square", "Corner Square"))]
def piece_for(body):
    s = np.array([{"p": 1, "n": -1, "0": 0}[c] for c in body.split("_")[1]], float)
    for g in pieces:
        if np.allclose(np.sign(np.round(g.bounds.mean(0) / 0.019)), s):
            return g
done = set()
for m in pos:
    if m["body"] == "core" or m["kind"] in done and len(done) > 1:
        continue
    g = piece_for(m["body"])
    u = np.array(m["dir"]); u /= np.linalg.norm(u)
    r_c = float(np.linalg.norm(m["pos"]))
    loc, _, _ = g.ray.intersects_location([np.zeros(3)], [u])
    hits = sorted(set(np.round(np.linalg.norm(loc, axis=1) * 1e3, 3)))
    axis = np.sign(np.round(g.bounds.mean(0) / 0.019)); axis /= np.linalg.norm(axis)
    ang = np.degrees(np.arccos(np.clip(u @ axis, -1, 1)))
    print(f"{m['body']} {m['kind']}: off-axis {ang:.1f} deg, magnet spans {r_c*1e3-1.5:.2f}-{r_c*1e3+1.5:.2f} mm, "
          f"piece material along line (mm): {hits[:4]}")
    done.add(m["kind"])
    if len(done) == 2 and m["kind"] in done:
        pass
