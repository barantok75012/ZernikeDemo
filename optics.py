"""Optical calculations translated from PSFguiPrez.m."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from zernike import zernike_indices, zernike_mode


@dataclass
class OpticalParameters:
    wavelength_nm: float = 550.0
    zernike_diameter_mm: float = 5.0
    pupil_percent: float = 50.0
    defocus_mm: float = 0.0
    axial_length_mm: float = 22.5
    psf_pixel_um: float = 1.0
    zernike_coefficients_um: np.ndarray | None = None
    grid_size: int = 128
    eye_index: float = 1.336


@dataclass
class OpticalResult:
    x_pupil: np.ndarray
    y_pupil: np.ndarray
    normalized_radius: np.ndarray
    wavefront: np.ndarray
    psf: np.ndarray
    psf_axis: np.ndarray
    corneal_surface: np.ndarray
    ray_origins: np.ndarray
    ray_points: np.ndarray
    ray_colors: np.ndarray
    sampling_warning: bool
    peak_psf: float


def _ray_grid(ray_count: int, pupil_radius: float, diameter: float) -> tuple[np.ndarray, np.ndarray]:
    side = 2 * int(np.ceil(np.sqrt(ray_count / np.pi)))
    base = np.linspace(-1.0, 1.0, side)
    y, x = np.meshgrid(base, base)
    x = np.vstack((x, x + np.diff(x[0, :2])[0] / 2.0)).ravel()
    y = np.sqrt(3.0) * np.vstack((y, y + np.diff(y[0, :2])[0] / 2.0)).ravel()
    radius = np.hypot(x, y)
    keep = np.argsort(radius)[radius[np.argsort(radius)] < 1.0]
    keep = keep[: len(keep)]
    scale = 0.5 * pupil_radius * diameter / radius[keep[-1]]
    return x[keep] * scale, y[keep] * scale


def calculate_optics(parameters: OpticalParameters) -> OpticalResult:
    """Calculate wavefront, FFT PSF, and the ray-tracing display data."""
    p = parameters
    wavelength = p.wavelength_nm * 1e-9
    diameter = p.zernike_diameter_mm * 1e-3
    pupil_fraction = p.pupil_percent * 1e-2
    defocus = p.defocus_mm * 1e-3
    axial = p.axial_length_mm * 1e-3
    psf_pixel = p.psf_pixel_um * 1e-6
    size = 2 ** int(np.ceil(np.log2(p.grid_size)))
    axis = np.linspace(-0.5, 0.5, size) * wavelength * axial / (p.eye_index * psf_pixel)
    x_pupil, y_pupil = np.meshgrid(axis, axis)
    radius = np.hypot(x_pupil, y_pupil) / (diameter / 2.0)
    inside = radius <= 1.0
    theta = np.arctan2(y_pupil, x_pupil)
    wavefront = np.zeros_like(radius)
    coefficients = p.zernike_coefficients_um
    if coefficients is None:
        coefficients = np.zeros(45)
    for coefficient, (n, m) in zip(coefficients, zernike_indices(len(coefficients))):
        mode = zernike_mode(n, m, radius, theta)
        wavefront[inside] += coefficient * 1e-6 * mode[inside]

    focus = p.eye_index * (1.0 / axial - 1.0 / (axial + defocus)) * (x_pupil**2 + y_pupil**2)
    amplitude = np.exp(2j * np.pi * (wavefront + focus) / wavelength)
    amplitude *= 10 ** (-0.05 * ((1e3 * x_pupil - 0.4) ** 2 + (1e3 * y_pupil - 0.2) ** 2) / 2.0)
    amplitude[~(radius <= pupil_fraction)] = 0.0
    psf = np.abs(np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(amplitude)))) ** 2
    psf /= psf.sum()

    surface = 0.5 * wavefront / p.eye_index + np.sqrt(np.maximum(0.0, axial**2 - x_pupil**2 - y_pupil**2))
    k_surface = 2.0 * wavefront / (p.eye_index - 1.0) + np.abs(
        np.sqrt(
            np.maximum(
                0.0,
                ((axial + defocus) * (p.eye_index - 1.0) / p.eye_index) ** 2 - x_pupil**2 - y_pupil**2,
            )
        )
    )
    ray_x, ray_y = _ray_grid(60, pupil_fraction, diameter)
    ray_z = np.sqrt(np.maximum(0.0, (axial + defocus) ** 2 - ray_x**2 - ray_y**2)) - (axial + defocus)
    grad_y, grad_x = np.gradient(surface, axis, axis)
    interpolator_x = RegularGridInterpolator((axis, axis), grad_x, bounds_error=False, fill_value=0.0)
    interpolator_y = RegularGridInterpolator((axis, axis), grad_y, bounds_error=False, fill_value=0.0)
    points = np.column_stack((ray_y, ray_x))
    normal_x = interpolator_x(points)
    normal_y = interpolator_y(points)
    normal_z = np.ones_like(normal_x)
    normals = np.column_stack((normal_x, normal_y, normal_z))
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    target_planes = np.column_stack(
        (-1e-3 * np.ones(len(ray_x)), np.zeros(len(ray_x)), -defocus * np.ones(len(ray_x)), 1e-3 * np.ones(len(ray_x)))
    )
    distances = ((-axial - ray_z)[:, None] + target_planes) / normals[:, 2, None]
    ray_origins = np.column_stack((ray_x, ray_z, ray_y))
    ray_points = ray_origins[:, None, :] + distances[:, :, None] * normals[:, None, :]
    ray_colors = np.clip(1.0 - 1.5 * np.hypot(ray_x, ray_y) / (0.5 * pupil_fraction * diameter), 0.0, 1.0)
    return OpticalResult(
        x_pupil=x_pupil, y_pupil=y_pupil, normalized_radius=radius, wavefront=wavefront,
        psf=psf, psf_axis=np.linspace(-0.5, 0.5, size) * size * psf_pixel,
        corneal_surface=k_surface, ray_origins=ray_origins, ray_points=ray_points,
        ray_colors=ray_colors, sampling_warning=np.max(radius) < np.sqrt(2), peak_psf=float(psf.max()),
    )
