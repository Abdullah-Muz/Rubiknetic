"""Stages 2/3 of the D5 geometry search (UNSCORED).

geometry gate (in-process, kin_check functions): rest interference, 6 face sweeps 0..90 (1 deg) >= 0.015 mm,
corner ppp outward capture blocked by 0.05 mm, corner twist blocked by 2 deg. Then dynamic tests as
subprocesses (one at a time per driver): rig_turn.py (soft/default turner), optionally forgive_rig.py and
dyn_check.py twist.
Usage: python stage2.py <configs.json> <out.jsonl> <stage: 2|3>
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

HERE = Path(__file__).resolve().parent
D5 = HERE.parent
sys.path.insert(0, str(D5))
sys.path.insert(0, str(HERE))
from kin_check import Poser, layer, make, min_dist  # noqa: E402
from screen import params  # noqa: E402

from rubiknetic.cube_logic.notation import FACE_NORMAL, FACES  # noqa: E402

PY = sys.executable
REPO = D5.parents[1]


def geometry_gate(p) -> dict:
    m, d, _ = make(p)
    P = Poser(m, d, p)
    P.reset()
    rest, _ = min_dist(m, d, set(P.bid))
    sweeps = {}
    for face in FACES:
        mv = layer(face)
        n = np.array(FACE_NORMAL[face], float)
        worst = np.inf
        for ang in range(0, 91):
            P.reset()
            P.rotate(mv, Rotation.from_rotvec(-np.radians(ang) * n).as_matrix())
            worst = min(worst, min_dist(m, d, set(mv))[0])
        sweeps[face] = float(worst)
    u = np.ones(3) / np.sqrt(3)
    P.reset()
    P.translate("cubie_ppp", u * 0.05 / 1000)
    out_cap = float(min_dist(m, d, {"cubie_ppp"})[0])
    P.reset()
    P.set_rot_about_own("cubie_ppp", Rotation.from_rotvec(np.radians(2.0) * u).as_matrix())
    twist = float(min_dist(m, d, {"cubie_ppp"})[0])
    green = rest >= 0.0 and min(sweeps.values()) >= 0.015 and out_cap < 0 and twist < 0
    return {"rest_min_mm": float(rest), "sweep_min_mm": sweeps, "outward_0.05mm": out_cap, "twist_2deg": twist,
            "green": bool(green), "ngeom": int(m.ngeom)}


def cli_args(cfg: dict) -> list[str]:
    kw = {k: v for k, v in cfg.items() if k != "is_baseline"}
    if kw.get("taper", 0) > 0:
        kw.update(inner_split_centre=26.0, inner_split_edge=24.0)
    kw.setdefault("sphere_spacing_mm", 2.0)
    return [f"{k}={float(v)}" for k, v in kw.items()]


MOVE_RE = re.compile(r"^\s+(\S+)\s*: layer\s+([-+\d.]+) deg \(error\s+([-+\d.]+), spread\s+([-+\d.]+)\) \| drift\s+([-+\d.]+) \| "
                     r"pen pad ([\d.]+) piece ([\d.]+) mm \| peak turner torque ([\d.]+) N.m \| observed move (\S+) (OK|MISMATCH)")


def run(script: str, args: list[str], timeout: int = 7200) -> tuple[str, float]:
    t0 = time.perf_counter()
    r = subprocess.run([PY, str(D5 / script), *args], cwd=REPO, capture_output=True, text=True, timeout=timeout)
    return r.stdout + r.stderr, time.perf_counter() - t0


def rig(cfg: dict, seq: str) -> dict:
    out, wall = run("rig_turn.py", [f"seq={seq}", *cli_args(cfg)])
    moves = []
    for line in out.splitlines():
        mm = MOVE_RE.match(line)
        if mm:
            mv, lay, err, spr, dr, pp, ppc, tq, obs, ok = mm.groups()
            moves.append(dict(move=mv, layer=float(lay), error=float(err), spread=float(spr), drift=float(dr),
                              pen_pad=float(pp), pen_piece=float(ppc), torque=float(tq), observed=obs, ok=ok == "OK"))
    sps = re.search(r"\((\d+) steps/s\)", out)
    return {"seq": seq, "moves": moves, "n_ok": sum(m["ok"] for m in moves), "n": len(moves),
            "disintegrated": any(m["spread"] > 2 or m["drift"] > 2 for m in moves),
            "steps_per_s": int(sps.group(1)) if sps else None, "wall_s": wall,
            "aborted": "ABORT" in out, "tail": out.strip().splitlines()[-3:] if not moves else []}


FG_RE = re.compile(r"d=\s*([-+\d.]+): U misaligned\s+([-+\d.]+) deg -> R turned\s+([-+\d.]+) deg \| U moved\s+([-+\d.]+) deg "
                   r"during R \| peak R torque ([\d.]+) N.m \| observed valid (\w+)")


def forgive(cfg: dict) -> dict:
    args = [a for a in cli_args(cfg)]
    out, wall = run("forgive_rig.py", ["degs=-6,-3,3,6", *args])
    pts = [dict(cmd=float(a), mis=float(b), R=float(c), U_moved=float(dd), torque=float(e), valid=f == "True")
           for a, b, c, dd, e, f in FG_RE.findall(out)]
    for q in pts:
        q["completed"] = q["R"] < -85.0 and q["valid"]
    return {"points": pts, "wall_s": wall}


TW_RE = re.compile(r"^\s+([\d.]+) N.m: twist\s+([-+\d.]+) deg \| corner moved\s+([\d.]+) mm \| max neighbour rot\s+([\d.]+) deg \| pen ([\d.]+) mm")


def twist(cfg: dict) -> dict:
    args = cli_args(cfg) + ["gap=0.05", "clearance=0.02", "spring_preload=10.0", "spring_k=2000.0", "slide_range=-0.001,0.0003"]
    out, wall = run("dyn_check.py", ["twist", *args])
    lv = [dict(torque=float(a), twist=float(b), moved=float(c), nbr=float(dd), pen=float(e))
          for a, b, c, dd, e in (TW_RE.match(l).groups() for l in out.splitlines() if TW_RE.match(l))]
    rel = re.search(r"released: twist\s+([-+\d.]+) deg; observed valid (\w+), solved (\w+)", out)
    return {"levels": lv, "released_twist": float(rel.group(1)) if rel else None,
            "recovered_solved": bool(rel and rel.group(3) == "True"), "aborted": "ABORT" in out, "wall_s": wall}


def main():
    cfgs = json.loads(Path(sys.argv[1]).read_text())
    out_path = Path(sys.argv[2])
    stage = int(sys.argv[3])
    done = set()
    if out_path.exists():
        done = {json.dumps(json.loads(l)["cfg"], sort_keys=True) for l in out_path.read_text().splitlines() if l.strip()}
    for cfg in cfgs:
        if json.dumps(cfg, sort_keys=True) in done:
            continue
        rec = {"cfg": cfg, "stage": stage}
        p = params(cfg, sphere=cfg.get("sphere_spacing_mm"))
        rec["geometry"] = geometry_gate(p)
        print(f"geometry {cfg}: {rec['geometry']}", flush=True)
        if rec["geometry"]["green"] or cfg.get("is_baseline"):
            if stage == 2:
                rec["rig"] = rig(cfg, "U R U' R'")
            else:
                rec["rig"] = rig(cfg, "U R U' R' F F' D2 L B'")
                rec["forgive"] = forgive(cfg)
                rec["twist"] = twist(cfg)
            print(f"  rig {rec['rig']['n_ok']}/{rec['rig']['n']} disintegrated={rec['rig']['disintegrated']}", flush=True)
        with out_path.open("a") as f:
            f.write(json.dumps(rec) + "\n")


if __name__ == "__main__":
    main()
