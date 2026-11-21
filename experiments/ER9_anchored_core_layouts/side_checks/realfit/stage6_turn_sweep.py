"""Stage 6: is the space the layout's anchor magnets occupy outside their own piece free, or do other CAD pieces pass
through it when a layer turns? Kinematic only (rigid rotation of a layer about its axis in 2 degree steps); no
dynamics. For the reference corner (1,1,1) and edge (1,1,0): the share of each 4 x 3 mm anchor cylinder's volume that
lies inside any other piece, at rest and over quarter turns of each layer that contains the piece. Numbers only."""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np  # noqa: E402

import fitlib as L  # noqa: E402

t0 = time.time()
pos = json.loads((HERE / "positions.json").read_text())
a, hl = pos["mp"]["diameter"] * 1e3 / 2, pos["mp"]["length"] * 1e3 / 2
name2home = lambda b: tuple({"n": -1, "0": 0, "p": 1}[ch] for ch in b.split("_")[1])  # noqa: E731
parts = [p for p in L.load_parts() if p["kind"] in ("edge", "corner", "centre")]
for p in parts:
    p["lo"], p["hi"] = p["V"].min(0), p["V"].max(0)


def rot(k, ang):
    c, s = np.cos(ang), np.sin(ang)
    i, j = [(1, 2), (2, 0), (0, 1)][k]
    R = np.eye(3)
    R[i, i], R[i, j], R[j, i], R[j, j] = c, -s, s, c
    return R


res = []
for home in ((1, 1, 1), (1, 1, 0)):
    own = [p for p in parts if p["home"] == home][0]
    mags = [m for m in pos["anchored_c0.2"] if m["body"] != "core" and name2home(m["body"]) == home]
    for im, m in enumerate(mags):
        c, v = np.array(m["pos"]) * 1e3, np.array(m["dir"])
        P = L.cyl_volume_points(c, v, a, hl, 0.25)
        own_in, _ = L.inside(own["V"], own["F"], P, ndir=5)
        row = {"home": home, "pair": im, "n_points": int(len(P)), "share_inside_own_piece": float(own_in.mean()), "turns": {}}
        for k in range(3):
            if home[k] == 0:
                continue
            static = [p for p in parts if p["home"][k] != home[k]]
            worst, worst_ang, kinds = 0.0, None, {}
            rest = None
            for deg in range(-90, 91, 2):
                Q = P @ rot(k, np.radians(deg)).T
                hit = np.zeros(len(Q), bool)
                for q in static:
                    if np.any(Q.max(0) < q["lo"]) or np.any(Q.min(0) > q["hi"]):
                        continue
                    ins, _ = L.inside(q["V"], q["F"], Q, ndir=3)
                    if ins.any():
                        hit |= ins
                        kinds[q["kind"]] = max(kinds.get(q["kind"], 0.0), float(ins.mean()))
                f = float(hit.mean())
                if deg == 0:
                    rest = f
                if f > worst:
                    worst, worst_ang = f, deg
            row["turns"]["xyz"[k]] = {"share_inside_other_pieces_at_rest": rest, "max_share_over_turn": worst,
                                      "at_deg": worst_ang, "max_share_by_piece_kind": kinds}
        res.append(row)
        print(json.dumps(row), flush=True)
(HERE / "stage6_results.json").write_text(json.dumps(res, indent=1))
print("done", round(time.time() - t0, 1), "s")
