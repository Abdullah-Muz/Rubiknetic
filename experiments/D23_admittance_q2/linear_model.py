"""D23 linear cross-check (no simulation): the sampled admittance loop closed through a contact spring k_e.

Per axis, tick period T = 4 ms, semi-implicit Euler as in admittance.py:
    v[k+1] = v[k] + T * (F[k-d] - D v[k] - K delta[k]) / M,   delta[k+1] = delta[k] + T v[k+1]
    F[k]   = -k_e * delta[k-1]     (the arm reaches the commanded offset one tick later: stiff servo, ZOH)
k_e lumps arm B's servo compliance, the pads and arm A's grip (INFERENCE from the observed limit-cycle frequency,
f ~ sqrt((K + k_e)/M) / 2 pi: 12 Hz at M = 1 and 33-39 Hz at M = 0.1 both give k_e ~ 5-6 kN/m).
Prints the spectral radius (> 1 = linearly unstable) and the frequency of the dominant mode.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np

T = 0.004
HERE = Path(__file__).resolve().parent


def rho(K, M, D, d, ke):
    n = d + 3                                  # state: delta[k], v[k], delta[k-1] ... delta[k-d-1]
    A = np.zeros((n, n))
    # F[k-d] = -ke * delta[k-d-1] -> index of delta[k-d-1] in the state is d + 2 (delta[k-j] at j + 1 for j >= 1)
    jF = d + 2
    # v' = v + T/M (-ke delta[k-d-1] - D v - K delta)
    A[1, 0] = -T * K / M
    A[1, 1] = 1 - T * D / M
    A[1, jF] += -T * ke / M
    # delta' = delta + T v'
    A[0] = T * A[1]
    A[0, 0] += 1.0
    # shift register: delta[k] -> slot 2, slot j -> j+1
    A[2, 0] = 1.0
    for j in range(3, n):
        A[j, j - 1] = 1.0
    ev = np.linalg.eigvals(A)
    i = int(np.argmax(np.abs(ev)))
    return float(np.abs(ev[i])), float(abs(np.angle(ev[i])) / (2 * np.pi * T))


def main() -> None:
    rows = []
    for ke, M, d, K in itertools.product((3000.0, 5500.0, 10000.0), (1.0, 0.1), (1, 3), (200, 500, 1000, 2000)):
        D = 2 * 0.8 * np.sqrt(K * M)
        r, f = rho(K, M, D, d, ke)
        rows.append({"k_e": ke, "M": M, "delay": d, "K": K, "D": round(D, 1), "rho": round(r, 4), "f_hz": round(f, 1)})
    for ke, d, D in itertools.product((3000.0, 5500.0, 10000.0), (1, 3), (150.0, 300.0)):
        r, f = rho(500, 1.0, D, d, ke)
        rows.append({"k_e": ke, "M": 1.0, "delay": d, "K": 500, "D": D, "rho": round(r, 4), "f_hz": round(f, 1)})
    (HERE / "results" / "linear_model.json").write_text(json.dumps(rows, indent=1))
    print("| k_e | M | delay | K | D | rho | f Hz |\n|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['k_e']:g} | {r['M']:g} | {r['delay']} | {r['K']} | {r['D']:g} | {r['rho']:.3f} | {r['f_hz']:g} |")


if __name__ == "__main__":
    main()
