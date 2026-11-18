"""ER2 O1 supplement (descriptive, post hoc; reads results/static_screen.json only): each piece's stiffness matrix
expressed along its natural motions. Edge (home c, two non-zero axes): 'spin' = rotation about its radial axis,
'slide' = rotation that moves it along its own edge direction (the D10/D11 slip mode), 'cross' = rotation that moves
it from one face toward the other. Corner: 'twist' = about its radial diagonal, plus the two tangential modes
(the stiffness range over tangential directions)."""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
D = json.loads((HERE / "results" / "static_screen.json").read_text())
HOME = {}
for c in [(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1)]:
    HOME["cubie_" + "".join({-1: "n", 0: "0", 1: "p"}[v] for v in c)] = np.array(c, float)
print("| layout | edge spin | edge slide (slip mode) | edge cross | corner twist | corner tangential min..max |  (mN m/rad, min over pieces; positive = restoring)")
print("|---|---|---|---|---|---|")
for r in D["rows"]:
    es, esl, ecr, ct, ctan_lo, ctan_hi = [], [], [], [], [], []
    for n, v in r["pieces"].items():
        K = np.array(v["K"]); c = HOME[n]
        rad = c / np.linalg.norm(c)
        q = lambda u: float(u @ K @ u)  # noqa: E731
        if v["kind"] == "edge":
            zero = np.nonzero(c == 0)[0][0]
            along = np.eye(3)[zero]                       # edge direction
            slide = np.cross(rad, along); slide /= np.linalg.norm(slide)   # rotation axis that moves it along 'along'
            es.append(q(rad)); esl.append(q(slide)); ecr.append(q(along))  # rotating about 'along' moves it across
        else:
            ct.append(q(rad))
            t1 = np.cross(rad, [1.0, 0, 0]); t1 /= np.linalg.norm(t1); t2 = np.cross(rad, t1)
            B = np.column_stack([t1, t2])
            tang = list(np.linalg.eigvalsh(B.T @ K @ B))
            ctan_lo.append(min(tang)); ctan_hi.append(max(tang))
    f = lambda a: f"{min(a):+.0f}" if a else "â€“"  # noqa: E731
    print(f"| {r['layout']} | {f(es)} | {f(esl)} | {f(ecr)} | {f(ct)} | {min(ctan_lo):+.0f}..{max(ctan_hi):+.0f} |")
