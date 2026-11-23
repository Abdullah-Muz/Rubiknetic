"""Side check (2026-11-23): anatomy of the fast slip events in the committed 60 s rest records. Read-only, post hoc,
exploratory and unscored: no simulation is run and no record is changed. Written after the Part G probe report.

Reads the rest60 time series (25 ms samples) of
  PG8, PG20   experiments/ER9_anchored_core_layouts/results/hybrid_g/probe/<ARM>/E1-1/rest_s160NN.json.gz
  L0, C52     experiments/ER7_core_magnet_rehearsal/results/<ARM>/E1-1/rest_s160NN.json*
and prints, per arm:
  - per seed, the largest change of any piece about any of its face normals over 200 ms (D11's window; an event is a
    change >= 0.2 deg), with the piece and axis, and the largest net change from the first to the last sample;
  - for each seed with an event: the piece's angle and its net magnet torque at fixed fractions of the time before the
    event, the least-squares drift rate before the event, the pieces that moved >= 0.05 deg in the same 200 ms, the
    layer-mean changes, contact counts and magnet energy.
Usage (WSL, repo root): ~/.venvs/rubiknetic/bin/python experiments/ER9_anchored_core_layouts/side_checks/slip_anatomy/slip_anatomy.py
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
G = REPO / "experiments/ER9_anchored_core_layouts/results/hybrid_g/probe"
E7 = REPO / "experiments/ER7_core_magnet_rehearsal/results"
ARMS = {"PG8": G / "PG8/E1-1", "PG20": G / "PG20/E1-1", "L0": E7 / "L0/E1-1", "C52": E7 / "C52/E1-1"}
WIN, THR, DT = 8, 0.2, 0.025          # D11: 200 ms window at 25 ms samples, 0.2 deg


def load(p: Path) -> dict:
    return json.loads(gzip.decompress(p.read_bytes())) if p.suffix == ".gz" else json.loads(p.read_text())


def kind(name: str) -> str:
    return "corner" if "0" not in name.split("_")[1] else "edge"


def main() -> None:
    for arm, d in ARMS.items():
        files = sorted(d.glob("rest_s*.json*"))
        print(f"\n=== {arm}: {len(files)} records ({d.relative_to(REPO)})")
        rows, events = [], []
        for p in files:
            r = load(p)
            q = r["rest60"]
            ts = q["timeseries"]
            seed = q["seed"]
            t = np.array(ts["t"]) - ts["t"][0] + DT
            rot = {(f, n): np.array(rows_)[:, j] for f, rows_ in ts["rot_deg"].items()
                   for j, n in enumerate(q["members"][f])}
            win = {k: np.abs(a[WIN:] - a[:-WIN]) for k, a in rot.items()}
            kmax = max(win, key=lambda k: win[k].max())
            net = {k: abs(a[-1] - a[0]) for k, a in rot.items()}
            knet = max(net, key=net.get)
            rows.append((seed, float(win[kmax].max()), kmax, float(net[knet]), knet))
            if win[kmax].max() >= THR:
                events.append((seed, q, ts, t, rot, kmax, int(win[kmax].argmax())))
        print("  seed   max 200 ms change (deg)  piece/axis    net change first->last (deg)  piece/axis")
        for seed, m, (f, n), nm, (f2, n2) in rows:
            print(f"  {seed}  {m:8.3f}{' EVENT' if m >= THR else '      '}        {n[6:]}/{f}       {nm:8.3f}"
                  f"                   {n2[6:]}/{f2}")
        v = np.array([m for _, m, *_ in rows])
        print(f"  counts of seeds by max 200 ms change: >=0.2: {(v >= 0.2).sum()}, 0.1-0.2: {((v >= 0.1) & (v < 0.2)).sum()}"
              f", <0.1: {(v < 0.1).sum()}; median {np.median(v):.3f} deg")
        for seed, q, ts, t, rot, (f, name), k in events:
            a = rot[(f, name)]
            i = q["magnet_bodies"].index(name)
            T = np.array(ts["mag_torque_Nm"])[:, i] * 1e3
            U = np.array(ts["mag_energy_J"])
            nc = np.array(ts["ncon"])
            marks = [0, k // 4, k // 2, 3 * k // 4, k, k + WIN, min(k + 5 * WIN, len(a) - 1), len(a) - 1]
            print(f"\n  {arm} seed {seed}: {name[6:]} ({kind(name)}) about {f}; event {t[k]:.2f}-{t[k + WIN]:.2f} s, "
                  f"size {abs(a[k + WIN] - a[k]):.3f} deg, largest 25 ms step {np.abs(np.diff(a[k:k + WIN + 1])).max():.3f} deg")
            print("    t (s)                 " + " ".join(f"{t[m]:8.2f}" for m in marks))
            print("    angle (deg)           " + " ".join(f"{a[m]:+8.4f}" for m in marks))
            print("    magnet torque (mN m)  " + " ".join(f"{T[m]:8.2f}" for m in marks))
            print("    magnet energy-E0 (uJ) " + " ".join(f"{(U[m] - U[0]) * 1e6:8.2f}" for m in marks))
            print("    contacts              " + " ".join(f"{nc[m]:8d}" for m in marks))
            if k >= 8:
                rate = np.polyfit(t[:k + 1], a[:k + 1], 1)[0]
                print(f"    before the event: change {a[k] - a[0]:+.4f} deg in {t[k]:.2f} s, least-squares rate "
                      f"{rate * 1e3:+.2f} mdeg/s; magnet torque rank at the start {(np.array(ts['mag_torque_Nm'])[k] > T[k] / 1e3).sum() + 1}"
                      f" of {len(q['magnet_bodies'])}")
            comp = sorted(((abs(b[k + WIN] - b[k]), ff, nn) for (ff, nn), b in rot.items()
                           if (ff, nn) != (f, name) and abs(b[k + WIN] - b[k]) >= 0.05), reverse=True)
            print("    moved >= 0.05 deg in the same 200 ms: "
                  + ", ".join(f"{nn[6:]}/{ff} {m:.3f} ({kind(nn)})" for m, ff, nn in comp))
            lm = {ff: np.mean([b[k + WIN] - b[k] for (f2, _), b in rot.items() if f2 == ff]) for ff in ts["rot_deg"]}
            print("    layer-mean change (deg): " + ", ".join(f"{ff} {x:+.3f}" for ff, x in lm.items()))


if __name__ == "__main__":
    main()
