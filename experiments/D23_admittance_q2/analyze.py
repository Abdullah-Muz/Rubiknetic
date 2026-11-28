"""D23 analysis: chatter, internal force, slip and turn outcome per run -> results/summary.json and a Markdown table.

Signals (metrics only; computed offline from the logged simulator state):
  F_ext   true external force on arm B's gripper subtree = -(F/T force (world) - its mean over the tare window),
          noise-free; it is the net force arm B's fingertips exert on the cube, i.e. the force arm A has to resist
          (the inter-arm 'internal squeeze' force). Arm B's own grip (fingertip normal force) is reported separately.
  chatter high-pass (2nd-order Butterworth, 5 Hz, zero-phase) of the gripper-base position and of F_ext, at 2 kHz;
          RMS of the 3-vector, peak-to-peak (largest axis), dominant frequency (Welch PSD of the high-passed force).
Windows: hold = the last 1.0 s of the task-1 hold; roll = the task-2 roll.
Classification thresholds (CHATTER_F_N, CHATTER_X_MM) were set AFTER seeing the G2 reference and stiff-servo runs
(post hoc; stated in the README).
Usage: python analyze.py [results_dir]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt, welch

HERE = Path(__file__).resolve().parent
FS = 2000.0
CHATTER_F_N = 1.0       # high-passed |F_ext| RMS above this = chatter (post hoc)
CHATTER_X_MM = 0.05     # high-passed gripper-base position RMS above this = chatter (post hoc)
SOS = butter(2, 5.0, "highpass", fs=FS, output="sos")


def window(t, a, b):
    return (t >= a) & (t <= b)


def chatter(t, x, f, sel) -> dict:
    if sel.sum() < 200:
        return {}
    xh = sosfiltfilt(SOS, x[sel], axis=0) * 1e3
    fh = sosfiltfilt(SOS, f[sel], axis=0)
    fr, P = welch(fh, fs=FS, nperseg=min(1024, sel.sum()), axis=0)
    P = P.sum(axis=1)
    k = fr > 5.0
    return {"x_hp_rms_mm": float(np.sqrt((xh ** 2).sum(1).mean())), "x_hp_p2p_mm": float(np.ptp(xh, axis=0).max()),
            "f_hp_rms_N": float(np.sqrt((fh ** 2).sum(1).mean())), "f_hp_p2p_N": float(np.ptp(fh, axis=0).max()),
            "f_dom_hz": float(fr[k][np.argmax(P[k])])}


def analyse(rec: dict, tr) -> dict:
    out = {"name": rec["name"], "mode": rec["cfg"]["mode"], "K": rec["cfg"]["K"], "M": rec["cfg"]["M"],
           "D": rec["cfg"]["D"], "delay": rec["cfg"]["delay"], "servo_gain": rec["cfg"]["servo_gain"],
           "seed": rec["cfg"]["seed"], "aborted": rec.get("aborted"), "turn": rec.get("turn"),
           "contacts": rec.get("contacts"), "wall_s": rec.get("wall_s"), "sim_time_s": rec.get("sim_time_s"),
           "magnets_every_step": bool(rec.get("magnets", {}).get("steps_without_magnet_force", 1) == 0),
           "audit_violations": len(rec.get("audit_violations") or []),
           "numerical_failures": len(rec.get("numerical_failures") or [])}
    s, k = tr["step"], tr["tick"]
    if s.size == 0:
        return out
    t, x, fr = s[:, 0], s[:, 1:4], s[:, 4:7]
    ph = rec.get("phases", {})
    if "tare" not in ph:
        return out
    tare = fr[window(t, *ph["tare"])].mean(0)
    f = -(fr - tare)
    fn = np.linalg.norm(f, axis=1)
    kt = k[:, 0]
    W = {}
    if "hold" in ph:
        W["hold"] = (ph["hold"][1] - 1.0, ph["hold"][1])
    if "roll" in ph:
        W["roll"] = tuple(ph["roll"])
    last = float(t[-1])
    if "hold" not in ph:                         # aborted early: analyse the last 0.5 s before the stop
        W["last"] = (max(float(t[0]), last - 0.5), last)
    for w, (a, b) in W.items():
        sel = window(t, a, b)
        ks = window(kt, a, b)
        out[w] = {**chatter(t, x, f, sel),
                  "F_ext_mean_N": float(fn[sel].mean()), "F_ext_peak_N": float(fn[sel].max()),
                  "grip_mean_N": float(k[ks, 3].mean()) if ks.any() else None,
                  "grip_peak_N": float(k[ks, 3].max()) if ks.any() else None,
                  "delta_max_mm": float(np.linalg.norm(k[ks, 7:10], axis=1).max() * 1e3) if ks.any() else None}
    out["F_ext_peak_whole_N"] = float(fn[t >= ph["tare"][1]].max())
    out["core_slip_max_mm"] = float(k[:, 1].max())
    out["core_slip_end_mm"] = float(k[-1, 1])
    out["core_rot_max_deg"] = float(k[:, 2].max())
    if "hold" in ph:
        e = window(kt, ph["hold"][0], ph["hold"][1])
        out["core_slip_end_hold_mm"] = float(k[e, 1][-1])
    out["delta_max_whole_mm"] = float(np.linalg.norm(k[:, 7:10], axis=1).max() * 1e3)
    cls = "UNSTABLE (diverged)" if out["aborted"] and "diverged" in out["aborted"] else None
    if cls is None:
        chat = [w for w in ("hold", "roll", "last") if w in out and out[w].get("f_hp_rms_N", 0) > CHATTER_F_N
                or w in out and out[w].get("x_hp_rms_mm", 0) > CHATTER_X_MM]
        cls = ("CHATTER (" + ",".join(chat) + ")") if chat else ("ABORTED" if out["aborted"] else "STABLE")
    out["class"] = cls
    return out


def main() -> None:
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "results"
    rows = []
    for j in sorted(d.glob("*.json")):
        if j.name == "summary.json":
            continue
        rec = json.loads(j.read_text())
        if not isinstance(rec, dict) or "cfg" not in rec:     # e.g. linear_model.json
            continue
        tr = np.load(d / f"{rec['name']}_trace.npz")
        rows.append(analyse(rec, tr))
    (d / "summary.json").write_text(json.dumps({"chatter_thresholds": {"f_hp_rms_N": CHATTER_F_N,
                                                                        "x_hp_rms_mm": CHATTER_X_MM},
                                                "runs": rows}, indent=1, default=float))
    hdr = ("| run | class | hold F_hp rms N (f_dom Hz) | hold x_hp rms mm | hold F_ext mean/peak N | grip mean N | "
           "roll F_hp rms N (f_dom Hz) | roll F_ext mean/peak N | max delta mm | core slip max/end mm | turn | contacts |")
    print(hdr)
    print("|" + "---|" * hdr.count("|")[:-1] if False else "|" + "---|" * (hdr.count("|") - 1))

    def g(w, r, key, fmt="{:.2f}"):
        v = r.get(w, {}).get(key)
        return "-" if v is None else fmt.format(v)
    for r in rows:
        tn = r.get("turn") or {}
        c = r.get("contacts") or {}
        bad = {kk: v for kk, v in c.items() if v and kk != "pen_cubie"}
        print(f"| {r['name']} | {r.get('class', '-')} | {g('hold', r, 'f_hp_rms_N')} ({g('hold', r, 'f_dom_hz', '{:.0f}')}) | "
              f"{g('hold', r, 'x_hp_rms_mm', '{:.3f}')} | {g('hold', r, 'F_ext_mean_N')}/{g('hold', r, 'F_ext_peak_N')} | "
              f"{g('hold', r, 'grip_mean_N', '{:.1f}')} | {g('roll', r, 'f_hp_rms_N')} ({g('roll', r, 'f_dom_hz', '{:.0f}')}) | "
              f"{g('roll', r, 'F_ext_mean_N')}/{g('roll', r, 'F_ext_peak_N')} | "
              f"{r.get('delta_max_whole_mm', float('nan')):.2f} | "
              f"{r.get('core_slip_max_mm', float('nan')):.2f}/{r.get('core_slip_end_mm', float('nan')):.2f} | "
              f"{tn.get('observed_move')} ({tn.get('layer_rot_mean_deg', float('nan')):.1f} deg) | "
              f"pen {c.get('pen_cubie', 0):.3f} mm{'; ' + str(bad) if bad else ''} |")


if __name__ == "__main__":
    main()
