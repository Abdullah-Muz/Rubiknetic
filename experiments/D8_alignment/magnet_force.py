"""D8-1b design input (UNSCORED): forces between two axially magnetised cylindrical (disc) magnets.

Model (FACT, textbook magnetostatics): the Coulombian / magnetic-charge model of a uniformly magnetised cylinder.
The magnetisation M = Br / mu0 is replaced by surface charge +M on the north face and -M on the south face. The
force between two magnets is the sum over the four face pairs of
    F = mu0 / (4 pi) * sigma1 * sigma2 * integral integral (r2 - r1) / |r2 - r1|^3 dA1 dA2.
The model is exact for ideal rigid magnetisation (relative recoil permeability 1). Real NdFeB has
mu_r ~ 1.05, which is neglected (ASSUMPTION).

Checks:
  V1  the discretised charge model reproduces the closed-form on-axis field of a cylinder,
      Bz(z) = Br/2 * [ (z+L)/sqrt(a^2+(z+L)^2) - z/sqrt(a^2+z^2) ]   (z measured from the near face).
  V2  two identical magnets at (near) contact vs the supplier's adhesive force for a 4 x 2 mm N45 disc
      (supermagnete S-04-02-N: "approx. 4,12 N"; on steel, i.e. an image-magnet configuration, so it is
      only an order-of-magnitude check).

Geometry: magnet A occupies z in [-g/2 - L, -g/2]; magnet B occupies z in [g/2, g/2 + L] and is shifted
laterally by s along x. Both are magnetised +z, so A's north face faces B's south face (attraction).
Output: force ON B. Fz < 0 means attraction; Fx < 0 means a restoring shear toward s = 0.
Usage: python magnet_force.py   (writes results/magnet_force.json)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

MU0 = 4e-7 * np.pi
OUT = Path(__file__).parent / "results"


def disc_points(a: float, n_r: int = 24, n_phi: int = 64) -> tuple[np.ndarray, np.ndarray]:
    """Quadrature points (x, y) and weights (area) on a disc of radius a: Gauss-Legendre in r, uniform in phi."""
    xr, wr = np.polynomial.legendre.leggauss(n_r)
    r = 0.5 * a * (xr + 1)
    wr = 0.5 * a * wr * r
    phi = (np.arange(n_phi) + 0.5) * 2 * np.pi / n_phi
    R, P = np.meshgrid(r, phi, indexing="ij")
    W = np.repeat(wr[:, None], n_phi, axis=1) * (2 * np.pi / n_phi)
    return np.column_stack([(R * np.cos(P)).ravel(), (R * np.sin(P)).ravel()]), W.ravel()


def pair_force(a: float, L: float, br: float, g: float, s: float, n_r: int = 24, n_phi: int = 64) -> np.ndarray:
    """Force (N) on magnet B from magnet A, face-pair charge model."""
    sigma = br / MU0
    pts, w = disc_points(a, n_r, n_phi)
    faces_a = [(-g / 2, +1.0), (-g / 2 - L, -1.0)]          # A: north face on top (+), south face below (-)
    faces_b = [(g / 2, -1.0), (g / 2 + L, +1.0)]             # B: south face at bottom (-), north face on top (+)
    F = np.zeros(3)
    pb = np.column_stack([pts[:, 0] + s, pts[:, 1]])
    for za, qa in faces_a:
        for zb, qb in faces_b:
            d = np.empty((len(pts), len(pts), 3))
            d[..., 0] = pb[None, :, 0] - pts[:, None, 0]
            d[..., 1] = pb[None, :, 1] - pts[:, None, 1]
            d[..., 2] = zb - za
            r3 = np.linalg.norm(d, axis=2) ** 3
            F += qa * qb * np.einsum("i,j,ijk->k", w, w, d / r3[..., None])
    return MU0 / (4 * np.pi) * sigma ** 2 * F


def onaxis_field_closed(a: float, L: float, br: float, z: float) -> float:
    return br / 2 * ((z + L) / np.hypot(a, z + L) - z / np.hypot(a, z))


def onaxis_field_charges(a: float, L: float, br: float, z: float, n_r: int = 24, n_phi: int = 64) -> float:
    sigma = br / MU0
    pts, w = disc_points(a, n_r, n_phi)
    bz = 0.0
    for zf, q in [(0.0, +1.0), (-L, -1.0)]:                 # magnet below z = 0, north face at z = 0
        dz = z - zf
        r3 = (pts[:, 0] ** 2 + pts[:, 1] ** 2 + dz ** 2) ** 1.5
        bz += q * np.sum(w * dz / r3)
    return MU0 / (4 * np.pi) * sigma * bz


def main() -> None:
    out: dict = {"model": "Coulombian surface-charge model, ideal rigid magnetisation", "checks": {}, "tables": []}
    # V1: field check
    a, L, br = 0.002, 0.002, 1.35
    v1 = []
    for z in (0.0005, 0.001, 0.002, 0.004):
        bc, bq = onaxis_field_closed(a, L, br, z), onaxis_field_charges(a, L, br, z)
        v1.append({"z_mm": z * 1e3, "closed_T": bc, "charges_T": bq, "rel_err": abs(bq - bc) / bc})
    out["checks"]["V1_onaxis_field"] = v1
    # quadrature convergence at the smallest gap used
    f1 = pair_force(a, L, br, 0.0005, 0.0)[2]
    f2 = pair_force(a, L, br, 0.0005, 0.0, n_r=40, n_phi=96)[2]
    out["checks"]["quadrature_convergence_g0.5mm"] = {"Fz_24x64": f1, "Fz_40x96": f2, "rel_diff": abs(f1 - f2) / abs(f2)}
    # V2: near-contact force, 4 x 2 mm, N45 Br range 1.32-1.38 T (grade-table range; ASSUMPTION for this supplier)
    out["checks"]["V2_contact_4x2_N45"] = {
        f"Br_{b}": float(-pair_force(0.002, 0.002, b, 0.00005, 0.0, n_r=40, n_phi=96)[2]) for b in (1.32, 1.38)}
    out["checks"]["V2_supplier_adhesive_N"] = 4.12

    grades = {"N35": 1.19, "N52": 1.45}      # mid-range Br (T) from public grade tables (see README)
    sizes = {"4x2": (0.002, 0.002), "4x1.5": (0.002, 0.0015), "3x1.5": (0.0015, 0.0015)}
    for sz, (a, L) in sizes.items():
        for gname, br in grades.items():
            for g in (0.0005, 0.001, 0.0015, 0.002):
                offs = np.linspace(0, 0.006, 25)
                F = np.array([pair_force(a, L, br, g, s, n_r=16, n_phi=48) for s in offs])
                fx = -F[:, 0]                                     # restoring shear magnitude
                k = (fx[1] - fx[0]) / (offs[1] - offs[0])
                i = int(np.argmax(fx))
                out["tables"].append({"size": sz, "grade": gname, "Br_T": br, "gap_mm": g * 1e3,
                                      "Fn_aligned_N": float(-F[0, 2]), "shear_peak_N": float(fx[i]),
                                      "shear_peak_offset_mm": float(offs[i] * 1e3), "shear_stiffness_N_per_mm": k / 1e3,
                                      "offset_mm": (offs * 1e3).round(3).tolist(), "shear_N": fx.round(5).tolist(),
                                      "Fn_N": (-F[:, 2]).round(5).tolist()})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "magnet_force.json").write_text(json.dumps(out, indent=1))
    for c in v1:
        print(f"V1 z={c['z_mm']} mm closed={c['closed_T']:.4f} T charges={c['charges_T']:.4f} T err={c['rel_err']:.1e}")
    print("quadrature:", out["checks"]["quadrature_convergence_g0.5mm"])
    print("V2 contact force 4x2 N45:", out["checks"]["V2_contact_4x2_N45"], "supplier adhesive 4.12 N")
    print(f"{'size':6s} {'grade':5s} {'gap':>4s} {'Fn':>6s} {'shear_pk':>8s} {'@mm':>5s} {'k N/mm':>7s}")
    for t in out["tables"]:
        print(f"{t['size']:6s} {t['grade']:5s} {t['gap_mm']:4.1f} {t['Fn_aligned_N']:6.3f} {t['shear_peak_N']:8.3f} "
              f"{t['shear_peak_offset_mm']:5.2f} {t['shear_stiffness_N_per_mm']:7.3f}")


if __name__ == "__main__":
    main()
