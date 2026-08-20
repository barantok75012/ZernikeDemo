"""Zernike polynomial computation.

Direct port of the Zernike-specific parts of PSFguiPrez.m: the (n, m) index
formulas (lines 43-44 / 189), Paul Fricker's radial-polynomial algorithm
(lines 190-200), and the weighted wavefront accumulation loop (lines 185-214).
"""
from __future__ import annotations

import math

import numpy as np


def zernike_nm(j: int) -> tuple[int, int]:
    """Radial degree n and azimuthal frequency m for the 0-based index j.

    Port of PSFguiPrez.m lines 43-44 (equivalently 189, same formula
    reindexed from 1-based kz to 0-based j = kz - 1).
    """
    n = math.ceil((-3 + math.sqrt(9 + 8 * j)) / 2)
    m = 2 * j - n * (n + 2)
    return n, m


def zernike_radial(n: int, m: int, r: np.ndarray) -> np.ndarray:
    """Radial part R_n^m(r) (PSFguiPrez.m lines 190-200, Paul Fricker's algorithm)."""
    am = abs(m)
    y = np.zeros_like(r)
    for s in range((n - am) // 2 + 1):
        coef = (
            (1 - 2 * (s % 2))
            * math.factorial(n - s)
            / (
                math.factorial(s)
                * math.factorial((n - am) // 2 - s)
                * math.factorial((n + am) // 2 - s)
            )
        )
        y = y + coef * r ** (n - 2 * s)
    return y


def zernike_value(n: int, m: int, r: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Normalized Zernike polynomial value at polar coordinates (r, t).

    Port of PSFguiPrez.m lines 201-207 (note the sin/cos assignment matches
    the original script exactly: sin for m>0, cos for m<0).
    """
    y = zernike_radial(n, m, r) * math.sqrt((1 + (m != 0)) * (n + 1))
    if m > 0:
        y = y * np.sin(t * m)
    elif m < 0:
        y = y * np.cos(t * m)
    return y


def build_wavefront(Xp: np.ndarray, Yp: np.ndarray, Rn: np.ndarray, zcoefs: np.ndarray) -> np.ndarray:
    """Wavefront W = sum_j zcoefs[j] * Z_j, restricted to the unit pupil (Rn <= 1).

    Port of PSFguiPrez.m lines 176-214. `zcoefs` holds one weight per
    0-based Zernike index j (already scaled to the same units as W, e.g. meters).
    """
    idr = Rn <= 1
    r = Rn[idr]
    t = np.arctan2(Yp[idr], Xp[idr])
    acc = np.zeros_like(r)
    for j, coef in enumerate(zcoefs):
        if coef == 0:
            continue
        n, m = zernike_nm(j)
        acc = acc + coef * zernike_value(n, m, r, t)
    W = np.zeros_like(Rn)
    W[idr] = acc
    return W
