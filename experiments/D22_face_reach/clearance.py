"""D22 step 4 (UNSCORED, kinematics only): actual clearances (up to 60 mm) and joint margins along graph.py's tours.

reach.py caps clearance at its 10 mm contact margin. Clearances are reported per class (arm-arm, robot-table,
self, robot-cube); 60.0 means nothing within 60 mm. Here every turn and handoff of the tours in results/graph.json is
re-checked with a 60 mm margin, using the IK postures reach.py selected, and the cube rotation of each reorientation is
reported (its path is not checked).
Usage (WSL): python clearance.py [--reach results/reach.json] [--graph results/graph.json]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import mujoco
import numpy as np

import graph as GR
import reach as RC

HERE = Path(__file__).resolve().parent
RC.MARGIN = 0.060


def gid_of(text):
    return re.search(r"\[([^;]+);", text).group(1)


def arm_of(text):
    return text.split(" ")[0]


CLASSES = ("arm_arm", "robot_table", "self_A", "self_B", "robot_cube")


def per_class(res):
    return {k: round(res[k] * 1e3, 1) for k in CLASSES}


def worst_of(rs):
    return {k: min(r[k] for r in rs) for k in CLASSES}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reach", default=str(HERE / "results" / "reach.json"))
    ap.add_argument("--graph", default=str(HERE / "results" / "graph.json"))
    a = ap.parse_args()
    r = json.loads(Path(a.reach).read_text())
    g = json.loads(Path(a.graph).read_text())
    G = {x["id"]: x for x in r["grasps"]}
    meta = r["meta"]
    geo = RC.geometry(meta["L"], meta["H"])
    turns = {(t["holder"], t["hold_grasp"], t["turn_grasp"]): t for t in r["turns"]}
    hands = {(h["scenario"], h["holder"], h["hold_grasp"], h["recv_grasp"]): h for h in r["handoffs"]}
    scenes = {}

    def scene(tA, tB):
        if (tA, tB) not in scenes:
            scenes[(tA, tB)] = RC.Scene(geo, tA, tB)
        return scenes[(tA, tB)]
    q = lambda arm, gid, k: np.array(G[gid][f"ik_{arm}"][k]["q"])  # noqa: E731
    app = lambda arm, gid, k: np.array(G[gid][f"ik_{arm}"][k]["approach"]["q"])  # noqa: E731
    out = []
    for run in g["runs"]:
        rows = []
        prev = None
        for st in run["tour"]:
            arm, gid = arm_of(st["state"]), gid_of(st["state"])
            row = {"step": st["step"], "holder": arm, "grasp": gid, "turnable": st["turnable"]}
            if st["step"] == "reorient" and prev is not None:
                o1 = re.search(r"cube (U\S+/B\S+)", prev["state"]).group(1)
                o2 = re.search(r"cube (U\S+/B\S+)", st["state"]).group(1)
                R = {GR.oname(R): R for R in GR.cube_rots()}
                dR = R[o2] @ R[o1].T
                row["reorient"] = f"{o1} -> {o2}"
                row["rotation_deg"] = round(float(np.degrees(np.arccos(np.clip((np.trace(dR) - 1) / 2, -1, 1)))), 1)
            if st["step"] == "handoff":
                h = hands[(run["scenario"], arm_of(prev["state"]), gid_of(prev["state"]), gid)]
                tA = G[h["hold_grasp"] if h["holder"] == "A" else gid]["tip"]
                tB = G[h["hold_grasp"] if h["holder"] == "B" else gid]["tip"]
                S = scene(tA, tB)
                S.set_cube("full")
                S.set_arm(h["holder"], q(h["holder"], h["hold_grasp"], h["holder_sol"]), "closed")
                S.set_arm(h["receiver"], app(h["receiver"], gid, h["recv_sol"]), "open")
                ra = S.check({h["holder"]: "grasp"})
                S.set_arm(h["receiver"], q(h["receiver"], gid, h["recv_sol"]), "closed")
                rg = S.check({h["holder"]: "grasp", h["receiver"]: "grasp"})
                row["handoff_clear_mm"] = {"approach": per_class(ra), "both_closed": per_class(rg)}
                row["margins_deg"] = [round(h["margin_holder_deg"], 1), round(h["margin_recv_deg"], 1)]
            if st["turn"]:
                t = turns[(arm, gid, st["turn"]["turn_grasp"])]
                S = scene(*(("p97", "c1") if arm == "A" else ("c1", "p97")))
                S.set_arm(arm, q(arm, gid, t["holder_sol"]), "closed")
                tq = q(t["turner"], t["turn_grasp"], t["turner_sol"])
                nf = RC.AXES[t["face_dir"]]
                S.set_arm(t["turner"], tq, "closed")
                mujoco.mj_kinematics(S.m, S.d)
                R0 = S.d.xmat[S.gb[t["turner"]]].reshape(3, 3).copy()
                rs = []
                for ang in [0] + RC.SWEEP_DEG:
                    qq = tq.copy()
                    qq[6] += np.radians(ang)
                    S.set_arm(t["turner"], qq, "closed")
                    mujoco.mj_kinematics(S.m, S.d)
                    S.set_cube("split", nf, S.d.xmat[S.gb[t["turner"]]].reshape(3, 3) @ R0.T)
                    rr = S.check({arm: "grasp", t["turner"]: "grasp"}, corotating=t["turner"])
                    rs.append(rr)
                row["turn"] = {"face": st["turnable"], "turner": t["turner"], "turn_grasp": t["turn_grasp"],
                               "clear_mm_worst_over_sweep": per_class(worst_of(rs)),
                               "margins_deg": [round(t["margin_holder_deg"], 1), round(t["margin_turner_deg"], 1)]}
            rows.append(row)
            prev = st
        out.append({"scenario": run["scenario"], "families": run["families"], "steps": rows})
        print(f"== {run['scenario']} {run['families']}")
        for row in rows:
            print("  ", json.dumps({k: v for k, v in row.items() if k not in ("holder",)}))
    (HERE / "results" / "tour_clearance.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
