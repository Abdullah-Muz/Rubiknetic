"""D23 sweep driver: runs admittance.py configurations, at most --jobs processes at a time; skips finished runs.
Usage (WSL): python sweep.py [--jobs 2] [--set main|extra]
"""
from __future__ import annotations

import argparse
import itertools
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"

MAIN = [dict(K=K, M=M, delay=dl, zeta=0.8, sg=1.0, seed=29001)
        for M, dl, K in itertools.product((1.0, 0.1), (1, 3), (200, 500, 1000, 2000))]
# EXTRA (chosen after the first 8 main runs; README): damping sized against the contact stiffness instead of K/M,
# an F/T low-pass, 4x stiffer joint servos, and a second pilot seed.
EXTRA: list[dict] = (
    [dict(K=500, M=1.0, delay=dl, D=D, sg=1.0, seed=29001) for D in (150.0, 300.0) for dl in (1, 3)]
    + [dict(K=500, M=1.0, delay=1, zeta=0.8, lp=20.0, sg=1.0, seed=29001),
       dict(mode="stiff", sg=4.0, seed=29001),
       dict(K=500, M=1.0, delay=3, D=300.0, sg=4.0, seed=29001),
       dict(K=500, M=1.0, delay=3, D=300.0, sg=1.0, seed=29002),
       dict(K=500, M=1.0, delay=3, zeta=0.8, sg=1.0, seed=29002)])


def name(c: dict) -> str:
    if c.get("mode", "adm") != "adm":
        return f"{c['mode']}_sg{c['sg']:g}_s{c['seed']}"
    damp = f"D{c['D']:g}" if c.get("D") is not None else f"z{c['zeta']:g}"
    n = f"adm_K{c['K']:g}_M{c['M']:g}_d{c['delay']}_{damp}_sg{c['sg']:g}_s{c['seed']}"
    return n + (f"_lp{c['lp']:g}" if c.get("lp") else "")


def cmd(c: dict) -> list[str]:
    out = [sys.executable, str(HERE / "admittance.py"), "--mode", c.get("mode", "adm"), "--K", str(c.get("K", 500)),
           "--M", str(c.get("M", 1.0)), "--delay", str(c.get("delay", 1)), "--zeta", str(c.get("zeta", 0.8)),
           "--servo-gain", str(c["sg"]), "--seed", str(c["seed"]), "--out", str(RES)]
    if c.get("D") is not None:
        out += ["--D", str(c["D"])]
    if c.get("lp"):
        out += ["--ft-lp", str(c["lp"])]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--set", default="main", choices=("main", "extra"))
    a = ap.parse_args()
    assert a.jobs <= 2, "at most 2 simulation processes"
    todo = [c for c in (MAIN if a.set == "main" else EXTRA) if not (RES / f"{name(c)}.json").exists()]
    running: list = []
    (HERE / "logs").mkdir(exist_ok=True)
    while todo or running:
        while todo and len(running) < a.jobs:
            c = todo.pop(0)
            log = open(HERE / "logs" / f"{name(c)}.log", "w")
            running.append((subprocess.Popen(cmd(c), stdout=log, stderr=subprocess.STDOUT), c, log))
            print("start", name(c), flush=True)
        for p, c, log in list(running):
            if p.poll() is not None:
                log.close()
                running.remove((p, c, log))
                print("done", name(c), "exit", p.returncode, flush=True)
        time.sleep(2)


if __name__ == "__main__":
    main()
