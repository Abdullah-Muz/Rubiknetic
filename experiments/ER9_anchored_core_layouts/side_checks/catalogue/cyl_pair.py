"""Coaxial pair of identical, axially magnetised cylinder magnets: ideal charge model, independent implementation.

Uniform magnetisation M = Br / mu0 gives two uniformly charged end discs (surface density +-M) per magnet. The energy
of two coaxial-oriented discs of radius a, lateral offset rho, axial separation d is
    U_dd(rho, d) = mu0 pi M^2 a^2  Int_0^inf  J1(q a)^2 J0(q rho) exp(-q d) q^-2 dq
(from 1/r = Int J0(q rho) exp(-q |z|) dq). A magnet pair with centre distance D and length L (moments parallel):
    U(rho, D) = 2 U_dd(rho, D) - U_dd(rho, D - L) - U_dd(rho, D + L).
Force on the upper magnet: Fz = -dU/dD (negative = attraction), Fx = -dU/drho.
Quantities returned (SI): pull = -Fz at rho = 0 (N, positive = attraction);
  kz = dFz/dD at rho = 0 (N/m, positive: the attraction falls as the gap opens, i.e. axially unstable);
  klat = -dFx/dx at rho = 0 (N/m, positive = restoring).  Laplace's equation gives klat = kz / 2 exactly.
No repo import; numpy and scipy only.
"""
from __future__ import annotations

import numpy as np
from scipy.special import j0, j1

MU0 = 4e-7 * np.pi
_T = np.linspace(0.0, 120.0, 12001)           # t = q a, step 0.01 (120001 and 30001 points: same to 1e-9)
_J1SQ = j1(_T) ** 2
with np.errstate(divide="ignore", invalid="ignore"):
    _J1SQ_T1 = np.where(_T > 0, _J1SQ / _T, 0.0)            # J1^2 / t   (-> 0)
    _J1SQ_T2 = np.where(_T > 0, _J1SQ / _T ** 2, 0.25)      # J1^2 / t^2 (-> 1/4)
_W = np.full(_T.shape, 2.0); _W[1::2] = 4.0; _W[0] = _W[-1] = 1.0; _W *= (_T[1] - _T[0]) / 3.0   # Simpson


def _g(n: int, d: float, a: float, rho: float = 0.0, lat: bool = False) -> float:
    """a^(n-1) Int J1(t)^2 K(t rho / a) exp(-t d / a) t^-n dt, K = J0 (default) or J1 (lat=True)."""
    if d == 0.0 and n == 1 and not lat:
        return 0.5                                          # Int_0^inf J1(t)^2 / t dt = 1/2 (discs in contact)
    assert d > 0 and d / a >= 0.2, (d, a)                   # exp(-120 * 0.2) = 4e-11: tail negligible
    base = {0: _J1SQ, 1: _J1SQ_T1, 2: _J1SQ_T2}[n]
    k = (j1 if lat else j0)(_T * rho / a) if (rho != 0.0 or lat) else 1.0
    return float(np.sum(_W * base * k * np.exp(-_T * d / a))) * a ** (n - 1)


def _comb(f, D: float, L: float) -> float:
    return 2 * f(D) - f(D - L) - f(D + L)


def pair(diameter: float, length: float, br: float, face_gap: float) -> dict:
    """Ideal charge-model quantities of a coaxial attracting pair (SI in, SI out)."""
    a, L, D = diameter / 2, length, face_gap + length
    c = MU0 * np.pi * (br / MU0) ** 2 * a * a
    energy = c * _comb(lambda d: _g(2, d, a), D, L)                     # J (negative)
    fz = c * _comb(lambda d: _g(1, d, a), D, L)                         # N (negative)
    kz = -c * _comb(lambda d: _g(0, d, a), D, L)                        # dFz/dD, N/m (positive)
    moment = (br / MU0) * np.pi * a * a * L
    return {"pull_N": -fz, "kz_N_per_m": kz, "klat_N_per_m": kz / 2, "energy_mJ": energy * 1e3,
            "moment_Am2": moment, "centre_distance_mm": D * 1e3}


def pull(diameter: float, length: float, br: float, face_gap: float) -> float:
    """Pull only (N, positive = attraction). face_gap = 0 is allowed: it is the ideal pull of one magnet on a thick
    steel plate of infinite permeability (mirror image), the quantity a vendor's "adhesive force" approximates."""
    a, L, D = diameter / 2, length, face_gap + length
    c = MU0 * np.pi * (br / MU0) ** 2 * a * a
    return -c * _comb(lambda d: _g(1, d, a), D, L)


def lateral_force(diameter: float, length: float, br: float, face_gap: float, rho: np.ndarray) -> np.ndarray:
    """Restoring lateral force (N, positive = toward the axis) at lateral offsets rho (m)."""
    a, L, D = diameter / 2, length, face_gap + length
    c = MU0 * np.pi * (br / MU0) ** 2 * a * a
    return np.array([-c * _comb(lambda d: _g(1, d, a, r, lat=True), D, L) for r in np.atleast_1d(rho)])


def dipole_pull(diameter: float, length: float, br: float, face_gap: float) -> float:
    m = (br / MU0) * np.pi * (diameter / 2) ** 2 * length
    D = face_gap + length
    return 3 * MU0 * m * m / (2 * np.pi * D ** 4)
