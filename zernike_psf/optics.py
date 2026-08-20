"""PSF, ray tracing and sampling-check computations.

Direct port of the non-Zernike numerical parts of PSFguiPrez.m's nested
CalcPSF function: eye focusing (line 216), PSF via FFT (lines 217-230),
corneal-surface/ray-tracing geometry (lines 232-270) and the FFT sampling
check (lines 382-396). Zernike-specific code lives in zernike.py.
"""
from __future__ import annotations

import numpy as np
from scipy.interpolate import RectBivariateSpline


def eye_focus(Xp: np.ndarray, Yp: np.ndarray, axial: float, defocus: float, no: float) -> np.ndarray:
    """Defocus term added to the wavefront (PSFguiPrez.m line 216)."""
    return no * (1 / axial - 1 / (axial + defocus)) * (Xp**2 + Yp**2)


def compute_psf(
    W: np.ndarray,
    foc: np.ndarray,
    Xp: np.ndarray,
    Yp: np.ndarray,
    Rn: np.ndarray,
    pupnorm: float,
    lambda_: float,
) -> np.ndarray:
    """Point-spread function from the pupil complex amplitude (lines 217-230)."""
    E = np.exp(2j * np.pi * (W + foc) / lambda_)
    # Stiles-Crawford effect (line 223)
    E = E * 10.0 ** (-0.05 * ((1e3 * Xp - 0.4) ** 2 + (1e3 * Yp - 0.2) ** 2) / 2)
    E = np.where(Rn > pupnorm, 0, E)  # aperture stop (line 224)
    psf = np.abs(np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(E)))) ** 2
    psf = psf / np.sum(psf)
    return psf


def cornea_surface(
    W: np.ndarray, Xp: np.ndarray, Yp: np.ndarray, axial: float, defocus: float, no: float
) -> np.ndarray:
    """Corneal surface used for the ray-tracing plot (PSFguiPrez.m line 234).

    MATLAB's `sqrt` of a negative value returns a complex number; `abs(sqrt(...))`
    then yields its magnitude rather than NaN, so the argument is cast to
    complex here to match that behavior exactly.
    """
    term = ((axial + defocus) * (no - 1) / no) ** 2 - Xp**2 - Yp**2
    return 2 * W / (no - 1) + np.abs(np.sqrt(term.astype(complex)))


def ray_grid(nr: int, pupnorm: float, zerdiam: float) -> tuple[np.ndarray, np.ndarray]:
    """Hexagonal grid of `nr` rays over the aperture (PSFguiPrez.m lines 240-251)."""
    npts = 2 * int(np.ceil(np.sqrt(nr / np.pi)))
    lin = np.linspace(-1, 1, npts)
    step = lin[1] - lin[0]
    y_grid, x_grid = np.meshgrid(lin, lin)  # matches MATLAB [y x] = meshgrid(lin)

    x_stack = np.vstack([x_grid, x_grid + 0.5 * step])
    y_stack = np.sqrt(3) * np.vstack([y_grid, y_grid + 0.5 * step])

    x = x_stack.flatten(order="F")
    y = y_stack.flatten(order="F")

    z = np.hypot(x, y)
    order = np.argsort(z, kind="stable")
    z_sorted = z[order]
    nr_actual = int(np.sum(z_sorted < 1))
    sel = order[:nr_actual]
    scale = 0.5 * pupnorm * zerdiam / z_sorted[nr_actual - 1]
    return x[sel] * scale, y[sel] * scale


def surfnorm(Xp: np.ndarray, Yp: np.ndarray, Z: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Unit surface normals of Z=f(Xp, Yp) on a regular grid.

    Approximates MATLAB's `surfnorm` (finite-difference / cross-product of
    tangents) with the equivalent analytic formula for an explicit surface:
    normal ∝ (-dZ/dX, -dZ/dY, 1).
    """
    dx = Xp[0, 1] - Xp[0, 0]
    dZdY, dZdX = np.gradient(Z, dx)
    Nx, Ny, Nz = -dZdX, -dZdY, np.ones_like(Z)
    norm = np.sqrt(Nx**2 + Ny**2 + Nz**2)
    return Nx / norm, Ny / norm, Nz / norm


def interp2_spline(Xp: np.ndarray, Yp: np.ndarray, V: np.ndarray, xi: np.ndarray, yi: np.ndarray) -> np.ndarray:
    """Spline interpolation of V(Xp, Yp) at scattered points (xi, yi).

    Equivalent of MATLAB's `interp2(...,'spline')` (PSFguiPrez.m line 268).
    """
    x1d = Xp[0, :]
    y1d = Yp[:, 0]
    spline = RectBivariateSpline(x1d, y1d, V.T)
    return spline.ev(xi, yi)


def trace_rays(
    Xp: np.ndarray,
    Yp: np.ndarray,
    W: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    axial: float,
    defocus: float,
    no: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Ray intersections with the wavefront and their propagation direction.

    Port of PSFguiPrez.m lines 264-270. Returns z (sag at each ray, meters)
    and p, an (nr, 3) array of unit direction vectors normal to the wavefront.
    """
    z = np.sqrt((axial + defocus) ** 2 - x**2 - y**2) - (axial + defocus)
    surf = 0.5 * W / no + np.sqrt((axial + defocus) ** 2 - Xp**2 - Yp**2)
    Nx, Ny, Nz = surfnorm(Xp, Yp, surf)
    nx = interp2_spline(Xp, Yp, Nx, x, y)
    ny = interp2_spline(Xp, Yp, Ny, x, y)
    nz = interp2_spline(Xp, Yp, Nz, x, y)
    p = np.column_stack([nx, ny, nz])
    return z, p


def ray_extension(z: np.ndarray, p: np.ndarray, axial: float, defocus: float) -> np.ndarray:
    """Ray parameter values at the 4 display planes (PSFguiPrez.m line 276)."""
    offsets = np.array([-1e-3, 0.0, -defocus, 1e-3])
    return ((-axial - z)[:, None] + offsets[None, :]) / p[:, 2:3]


def check_sampling(Rn: np.ndarray) -> bool:
    """True when FFT sampling is insufficient to reconstruct the wavefront (line 383)."""
    return bool(np.max(Rn) < np.sqrt(2))
