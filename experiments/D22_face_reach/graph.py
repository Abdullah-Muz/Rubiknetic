"""D22 step 2 (UNSCORED, kinematics only): face-access map and regrasp/handoff graph from reach.py's static checks.

The cube box is invariant under the 24 cube rotations, so reach.py checks WORLD-frame grasps once. Here a state is
(holding arm, grasp in the CUBE frame, cube orientation O); its world grasp follows from O. Transitions:
  reorient  the holding arm alone carries the cube from O to O' with the same grasp (both end poses reachable and
            collision-free with the other arm parked; the path between them is NOT checked);
  handoff   the other arm approaches and closes on a compatible grasp while the holder holds; the holder releases.
A face f is turnable in a state if the holding grasp is a P-97 stabiliser of f (COAX from the opposite face, or SIDE
flush with the opposite face) and the other arm's C1 turner on f passes reach.py's turn check (approach, grasp, and
J7 roll of +-90 deg; +-180 deg reported).
Scenarios (tooling):
  FIXED  G2 tooling kept: A carries P-97 pads (stabilise / hold), B carries C1 pads + the F/T sensor (turn; it can
         hold the cube only with C1 pads, a weak one-layer (COAX) or 25 mm (SIDE) grip; ASSUMPTION that it holds).
  SYM    both arms can take either role (needs a tool change or a dual-purpose fingertip; not designed): holds and
         stabilisers are P-97, turns are C1; A has no F/T sensor, B keeps its own.
Families: 'coax' (only coaxial holds and stabilisers, as G2) or 'all' (also SIDE grasps).
Search: Dijkstra, cost = (handoffs, reorients) lexicographic: (1) per face, the cheapest state where it is turnable;
(2) the cheapest sequence after which all six faces have been turnable (a tour; turns themselves do not change the
grasp state).
Usage (WSL): python graph.py [--reach results/reach.json] [--out results]
"""
from __future__ import annotations

import argparse
import heapq
import itertools
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
FACE_NORMAL = {"U": (0, 0, 1), "D": (0, 0, -1), "R": (1, 0, 0), "L": (-1, 0, 0), "F": (0, -1, 0), "B": (0, 1, 0)}
FACES = "UDRLFB"
AXES = {"+x": (1, 0, 0), "-x": (-1, 0, 0), "+y": (0, 1, 0), "-y": (0, -1, 0), "+z": (0, 0, 1), "-z": (0, 0, -1)}
DIRNAME = {"+x": "+x (to B)", "-x": "-x (to A)", "+y": "+y", "-y": "-y", "+z": "+z (up)", "-z": "-z (table)"}
RC_G2 = np.column_stack([[0, 1.0, 0], [0, 0, 1.0], [1.0, 0, 0]])   # cube -> world at G2 (U = +x, B = +z)
HCOST = 100                                                        # one handoff outweighs any number of reorients


def vec(k):
    return np.array(AXES[k], float)


def dname(v):
    for k, a in AXES.items():
        if np.allclose(v, a, atol=1e-6):
            return k
    raise ValueError(v)


def cube_rots():
    out = []
    for perm in itertools.permutations(range(3)):
        for s in itertools.product((-1.0, 1.0), repeat=3):
            M = np.zeros((3, 3))
            for i, (j, sg) in enumerate(zip(perm, s)):
                M[i, j] = sg
            if np.linalg.det(M) > 0:
                out.append(M)
    return out


def oname(R):
    """Orientation label: where the cube's U and B faces point in the world."""
    return f"U{dname(R @ FACE_NORMAL['U'])}/B{dname(R @ FACE_NORMAL['B'])}"


def face_at(R, d):
    for f in FACES:
        if dname(R @ np.array(FACE_NORMAL[f], float)) == d:
            return f


def load(path):
    r = json.loads(Path(path).read_text())
    G = {g["id"]: g for g in r["grasps"]}
    return r, G


def gkey(g, Rinv):
    """Cube-frame key of a world grasp (apply Rinv = Rc^T to its direction vectors)."""
    t = lambda k: dname(Rinv @ vec(k)) if k else None  # noqa: E731
    return (g["kind"], g["tip"], t(g["n"]), t(g["x"]), t(g["fe"]))


def build(r, G, scenario, families):
    rots = cube_rots()
    holds = {"A": "p97", "B": "c1" if scenario == "FIXED" else "p97"}
    fam_ok = lambda g: families == "all" or g["kind"] == "COAX"  # noqa: E731
    solo = {}
    for gid, g in G.items():
        for arm in "AB":
            res = [s for s in g[f"solo_{arm}"] if s["ok"]]
            if res:
                sols = g[f"ik_{arm}"]
                best = max(res, key=lambda s: (sols[s["sol"]]["margin_deg"]))
                solo[(arm, gid)] = {"margin_deg": sols[best["sol"]]["margin_deg"], "clear_mm": best["clear_mm"]}
    turn = {}
    for t in r["turns"]:
        if not t["ok"]:
            continue
        if scenario == "FIXED" and t["holder"] != "A":
            continue
        k = (t["holder"], t["hold_grasp"])
        if k not in turn or (t.get("half_ok"), t["quarter_clear_mm"]) > (turn[k].get("half_ok"), turn[k]["quarter_clear_mm"]):
            turn[k] = t
    hand = {}
    for h in r["handoffs"]:
        if h["ok"] and h["scenario"] == scenario:
            hand.setdefault((h["holder"], h["hold_grasp"]), []).append(h)
    # world grasp lookup by cube-frame key per orientation
    lut = []
    for R in rots:
        Rinv = R.T
        d = {}
        for gid, g in G.items():
            d[gkey(g, Rinv)] = gid
        lut.append(d)
    inv = [{v: k for k, v in d.items()} for d in lut]
    valid = {}                                                        # (arm, cube key) -> [orientation indices]
    for oi in range(len(rots)):
        for gid, g in G.items():
            for arm in "AB":
                if g["tip"] == holds[arm] and fam_ok(g) and (arm, gid) in solo:
                    valid.setdefault((arm, inv[oi][gid]), []).append(oi)
    return {"rots": rots, "lut": lut, "inv": inv, "solo": solo, "turn": turn, "hand": hand, "valid": valid,
            "holds": holds, "fam_ok": fam_ok}


def turnable(B, G, state):
    arm, ck, oi = state
    gid = B["lut"][oi][ck]
    t = B["turn"].get((arm, gid))
    if t is None or not B["fam_ok"](G[gid]):
        return None, None
    return face_at(B["rots"][oi], t["face_dir"]), t


def neighbours(B, G, state):
    arm, ck, oi = state
    for oj in B["valid"].get((arm, ck), []):
        if oj != oi:
            yield 1, ("reorient", None), (arm, ck, oj)
    gid = B["lut"][oi][ck]
    for h in B["hand"].get((arm, gid), []):
        g2 = G[h["recv_grasp"]]
        if g2["tip"] != B["holds"][h["receiver"]] or not B["fam_ok"](g2):
            continue
        yield HCOST, ("handoff", h), (h["receiver"], B["inv"][oi][h["recv_grasp"]], oi)


def start_states(B, G):
    oi = next(i for i, R in enumerate(B["rots"]) if np.allclose(R, RC_G2))
    gid = "COAX-p97:n-x:y+y"                    # G2 arm A (layout.solve: no roll180)
    return [("A", B["inv"][oi][gid], oi)], oi


def dijkstra(B, G, starts, tour: bool):
    full = (1 << 6) - 1
    dist, prev, pq = {}, {}, []

    def mask_of(s):
        f, _ = turnable(B, G, s)
        return 0 if f is None else 1 << FACES.index(f)
    for s in starts:
        node = (s, mask_of(s)) if tour else (s, 0)
        dist[node] = 0
        heapq.heappush(pq, (0, len(prev), node))
    per_face = {}
    while pq:
        c, _, node = heapq.heappop(pq)
        if c > dist.get(node, 1 << 60):
            continue
        s, mask = node
        f, _ = turnable(B, G, s)
        if f is not None and f not in per_face:
            per_face[f] = (c, node)
        if tour and mask == full:
            return {"cost": c, "end": node, "prev": prev, "per_face": per_face}
        for w, how, s2 in neighbours(B, G, s):
            m2 = mask | (mask_of(s2) if tour else 0)
            n2 = (s2, m2)
            c2 = c + w
            if c2 < dist.get(n2, 1 << 60):
                dist[n2] = c2
                prev[n2] = (node, how)
                heapq.heappush(pq, (c2, len(prev), n2))
    return {"cost": None, "end": None, "prev": prev, "per_face": per_face}


def path_to(res, node):
    out = []
    while node in res["prev"]:
        p, how = res["prev"][node]
        out.append((p, how, node))
        node = p
    return out[::-1]


def state_text(B, G, s):
    arm, ck, oi = s
    gid = B["lut"][oi][ck]
    g = G[gid]
    R = B["rots"][oi]
    side = f", flush with face {face_at(R, g['fe'])}" if g["fe"] else ""
    pads = "/".join(sorted({face_at(R, g["y"]), face_at(R, dname(-vec(g["y"])))}))
    sm = B["solo"][(arm, gid)]
    return (f"{arm} holds {g['kind']}-{g['tip']} entering face {face_at(R, g['n'])}{side}, pads on {pads}; cube "
            f"{oname(R)} [{gid}; holder margin {sm['margin_deg']:.1f} deg, clearance {sm['clear_mm']:.1f} mm]")


def run(r, G, scenario, families):
    B = build(r, G, scenario, families)
    starts, o0 = start_states(B, G)
    res1 = dijkstra(B, G, starts, tour=False)
    per_face = {}
    for f in FACES:
        if f in res1["per_face"]:
            c, node = res1["per_face"][f]
            per_face[f] = {"handoffs": c // HCOST, "reorients": c % HCOST}
        else:
            per_face[f] = None
    res2 = dijkstra(B, G, starts, tour=True)
    steps = []
    if res2["end"] is not None:
        s0 = starts[0]
        f0, t0 = turnable(B, G, s0)
        steps.append({"step": "start", "state": state_text(B, G, s0),
                      "turnable": f0, "turn": turn_text(t0)})
        for (p, how, node) in path_to(res2, res2["end"]):
            s = node[0]
            f, t = turnable(B, G, s)
            e = {"step": how[0], "state": state_text(B, G, s), "turnable": f, "turn": turn_text(t),
                 "faces_so_far": "".join(FACES[i] for i in range(6) if node[1] >> i & 1)}
            if how[0] == "handoff":
                h = how[1]
                e["handoff"] = {"approach_clear_mm": h.get("approach_clear_mm"), "grasp_clear_mm": h.get("grasp_clear_mm"),
                                "margin_holder_deg": h["margin_holder_deg"], "margin_recv_deg": h["margin_recv_deg"]}
            steps.append(e)
    # faces turnable from the start state with no regrasp (any reorientation by the holder)
    no_regrasp = sorted({turnable(B, G, (starts[0][0], starts[0][1], oi))[0]
                         for oi in B["valid"].get((starts[0][0], starts[0][1]), [])} - {None})
    return {"scenario": scenario, "families": families, "per_face_min": per_face,
            "tour_cost": None if res2["cost"] is None else {"handoffs": res2["cost"] // HCOST,
                                                             "reorients": res2["cost"] % HCOST},
            "tour": steps, "no_regrasp_faces": no_regrasp,
            "start_orientations_reachable": [oname(B["rots"][oi]) for oi in
                                             B["valid"].get((starts[0][0], starts[0][1]), [])]}


def turn_text(t):
    if t is None:
        return None
    return {"turner": t["turner"], "turn_grasp": t["turn_grasp"], "face_dir": t["face_dir"],
            "quarter_clear_mm": round(t["quarter_clear_mm"], 2), "half_ok": t["half_ok"],
            "approach_clear_mm": round(t["approach_clear_mm"], 2), "margin_holder_deg": round(t["margin_holder_deg"], 1),
            "margin_turner_deg": round(t["margin_turner_deg"], 1)}


def direction_map(r, G):
    """Per world direction d of the face to turn: can each arm reach a C1 turn grasp / a P-97 stabiliser for it (solo,
    collision-free with the other arm parked), and is the pair feasible (turn check)?"""
    rows = []
    for d in AXES:
        row = {"dir": d}
        for arm in "AB":
            tg = [g for g in G.values() if g["turn"] == d]
            st = [g for g in G.values() if g["stab"] == d]

            def summ(gs, arm=arm):
                ik_ok = [g for g in gs if g[f"ik_{arm}"]]
                ok = [g for g in gs if any(s["ok"] for s in g[f"solo_{arm}"])]
                mar = max((s["margin_deg"] for g in ok for s, so in zip(g[f"ik_{arm}"], g[f"solo_{arm}"]) if so["ok"]),
                          default=None)
                return {"variants": len(gs), "ik": len(ik_ok), "collision_free": len(ok),
                        "best_margin_deg": None if mar is None else round(mar, 1)}
            row[f"turn_{arm}"] = summ(tg)
            row[f"stab_coax_{arm}"] = summ([g for g in st if g["kind"] == "COAX"])
            row[f"stab_side_{arm}"] = summ([g for g in st if g["kind"] == "SIDE"])
        for holder, turner in (("A", "B"), ("B", "A")):
            ts = [t for t in r["turns"] if t["holder"] == holder and t["face_dir"] == d]
            ok = [t for t in ts if t["ok"]]
            okc = [t for t in ok if t["hold_grasp"].startswith("COAX")]
            best = max(ok, key=lambda t: (t["half_ok"], t["quarter_clear_mm"]), default=None)
            row[f"pair_{holder}hold_{turner}turn"] = {
                "checked": len(ts), "ok": len(ok), "ok_coax_holder": len(okc),
                "half_ok": sum(t["half_ok"] for t in ok),
                "best": None if best is None else {"hold": best["hold_grasp"], "turn": best["turn_grasp"],
                                                   "quarter_clear_mm": round(best["quarter_clear_mm"], 2),
                                                   "approach_clear_mm": round(best["approach_clear_mm"], 2),
                                                   "margins_deg": [round(best["margin_holder_deg"], 1),
                                                                   round(best["margin_turner_deg"], 1)]},
                "fails": sorted({t["fail"].split(" ")[0] for t in ts if t["fail"]})}
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reach", default=str(HERE / "results" / "reach.json"))
    ap.add_argument("--out", default=str(HERE / "results"))
    a = ap.parse_args()
    r, G = load(a.reach)
    out = {"meta": r["meta"], "direction_map": direction_map(r, G),
           "g2_face_directions": {f: dname(RC_G2 @ np.array(FACE_NORMAL[f], float)) for f in FACES}, "runs": []}
    for scen in ("FIXED", "SYM"):
        for fam in ("coax", "all"):
            res = run(r, G, scen, fam)
            out["runs"].append(res)
            pf = " ".join(f"{f}:{'-' if v is None else str(v['handoffs']) + 'h' + str(v['reorients']) + 'r'}"
                          for f, v in res["per_face_min"].items())
            print(f"{scen:5s} {fam:4s} per-face min {pf} | tour {res['tour_cost']} | no-regrasp {res['no_regrasp_faces']}")
    Path(a.out).mkdir(parents=True, exist_ok=True)
    tag = Path(a.reach).stem.replace("reach", "graph")
    (Path(a.out) / f"{tag}.json").write_text(json.dumps(out, indent=1))
    print("wrote", Path(a.out) / f"{tag}.json")


if __name__ == "__main__":
    main()
