"""D22 step 3 (UNSCORED, kinematics only): face-to-face regrasp cost matrix.

For every pair of faces (f, g): starting from any state reachable from the G2 start in which f is turnable, the
cheapest number of (handoffs, reorients) to a state in which g is turnable. Reported as the best case (min over those
states) and the worst case (max over them), so a planner that is "in some f-turning state" knows its bound.
Computed with one multi-source Dijkstra per target face on the reversed transition graph of graph.py.
Usage (WSL): python matrix.py [--reach results/reach.json] [--out results]
"""
from __future__ import annotations

import argparse
import heapq
import json
from pathlib import Path

import graph as GR

HERE = Path(__file__).resolve().parent


def all_states(B):
    for (arm, ck), ois in B["valid"].items():
        for oi in ois:
            yield (arm, ck, oi)


def run(r, G, scenario, families):
    B = GR.build(r, G, scenario, families)
    states = list(all_states(B))
    rev = {s: [] for s in states}
    fwd = {s: [] for s in states}
    for s in states:
        for w, how, s2 in GR.neighbours(B, G, s):
            fwd[s].append((w, s2))
            rev.setdefault(s2, []).append((w, s))
    starts, _ = GR.start_states(B, G)
    seen, stack = set(starts), list(starts)               # states reachable from the G2 start
    while stack:
        s = stack.pop()
        for _, s2 in fwd.get(s, []):
            if s2 not in seen:
                seen.add(s2)
                stack.append(s2)
    turn_face = {s: GR.turnable(B, G, s)[0] for s in seen}
    out = {}
    for g in GR.FACES:
        dist, pq = {}, []
        for s in seen:
            if turn_face[s] == g:
                dist[s] = 0
                heapq.heappush(pq, (0, len(dist), s))
        k = len(dist)
        while pq:
            c, _, s = heapq.heappop(pq)
            if c > dist.get(s, 1 << 60):
                continue
            for w, sp in rev.get(s, []):
                if c + w < dist.get(sp, 1 << 60):
                    dist[sp] = c + w
                    k += 1
                    heapq.heappush(pq, (c + w, k, sp))
        for f in GR.FACES:
            src = [dist.get(s) for s in seen if turn_face[s] == f]
            if not src:
                out[f"{f}->{g}"] = None
                continue
            fin = [c for c in src if c is not None]
            enc = lambda c: {"handoffs": c // GR.HCOST, "reorients": c % GR.HCOST}  # noqa: E731
            out[f"{f}->{g}"] = {"best": enc(min(fin)) if fin else None, "worst": enc(max(fin)) if fin else None,
                                "unreachable_from": len(src) - len(fin), "n_states": len(src)}
    return {"scenario": scenario, "families": families, "n_states": len(states), "n_reachable": len(seen),
            "matrix": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reach", default=str(HERE / "results" / "reach.json"))
    ap.add_argument("--out", default=str(HERE / "results"))
    a = ap.parse_args()
    r, G = GR.load(a.reach)
    res = []
    for scen in ("FIXED", "SYM"):
        for fam in ("coax", "all"):
            m = run(r, G, scen, fam)
            res.append(m)
            print(f"{scen} {fam}: {m['n_reachable']}/{m['n_states']} states reachable from the G2 start")
            print("   from\\to " + " ".join(f"{g:>9s}" for g in GR.FACES) + "   (handoffs best-worst)")
            for f in GR.FACES:
                cells = []
                for g in GR.FACES:
                    v = m["matrix"][f"{f}->{g}"]
                    cells.append("        -" if v is None or v["best"] is None else
                                 f"{v['best']['handoffs']}-{v['worst']['handoffs']}".rjust(9))
                print(f"   {f:>7s} " + " ".join(cells))
    tag = Path(a.reach).stem.replace("reach", "matrix")
    (Path(a.out) / f"{tag}.json").write_text(json.dumps(res, indent=1))
    print("wrote", Path(a.out) / f"{tag}.json")


if __name__ == "__main__":
    main()
