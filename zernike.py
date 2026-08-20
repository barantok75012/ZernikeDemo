"""Zernike polynomials using the indexing convention of the MATLAB demo."""

from __future__ import annotations

import math

import numpy as np


def zernike_indices(count: int) -> list[tuple[int, int]]:
    """Return (n, m) pairs for MATLAB's one-based Zernike coefficient list."""
    indices: list[tuple[int, int]] = []
    for coefficient in range(count):
        one_based_coefficient = coefficient + 1
        n = math.ceil((-3.0 + math.sqrt(1.0 + 8.0 * one_based_coefficient)) / 2.0)
        m = 2 * coefficient - n * (n + 2)
        indices.append((n, m))
    return indices


def radial_polynomial(n: int, m: int, radius: np.ndarray) -> np.ndarray:
    """Evaluate the radial Zernike polynomial R_n^|m|(radius)."""
    if (n - abs(m)) % 2 or abs(m) > n:
        return np.zeros_like(radius, dtype=float)

    result = np.zeros_like(radius, dtype=float)
    for s in range((n - abs(m)) // 2 + 1):
        coefficient = (
            (-1) ** s
            * math.factorial(n - s)
            / (
                math.factorial(s)
                * math.factorial((n + abs(m)) // 2 - s)
                * math.factorial((n - abs(m)) // 2 - s)
            )
        )
        result += coefficient * radius ** (n - 2 * s)
    return result


def zernike_mode(n: int, m: int, radius: np.ndarray, theta: np.ndarray) -> np.ndarray:
    """Evaluate a normalized real Zernike mode on polar coordinates."""
    mode = radial_polynomial(n, m, radius)
    mode *= math.sqrt((1 + (m != 0)) * (n + 1))
    if m > 0:
        mode *= np.sin(m * theta)
    elif m < 0:
        mode *= np.cos(m * theta)
    return mode
