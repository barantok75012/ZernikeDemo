"""PyQt6 interface: control panel + live wavefront/PSF/ray-tracing plots.

Port of the UI and CalcPSF orchestration in PSFguiPrez.m (uicontrol panel:
lines 5-107; nested CalcPSF callback: lines 110-398). Numerics are delegated
to zernike_psf.zernike and zernike_psf.optics.
"""
from __future__ import annotations

import datetime as dt
import math
import random
from pathlib import Path

import matplotlib
from PIL import Image

matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers 3d projection)
import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSlider,
    QWidget,
)

from .zernike import build_wavefront, zernike_nm
from . import optics

N = 128  # image size, PSFguiPrez.m line 11 (U.N)
N_ZERNIKE = 45  # PSFguiPrez.m line 12 (U.Z)
NO = 1.336  # eye refractive index, PSFguiPrez.m line 166

# [label, left value, right value] for the fn=6 parameter rows (lines 16-30)
PARAM_ROWS = [
    ("Lambda (nm)", 450.0, 650.0),
    ("Zer diam (mm)", 2.0, 8.0),
    ("Pup diam (%)", 0.0, 100.0),
    ("Defoc (mm)", -1.0, 1.0),
    ("AL (mm)", 21.0, 24.0),
    ("PSFpix (um)", 0.5, 1.5),
]
IDX_ZERDIAM = 1
IDX_PUPNORM = 2
IDX_DEFOCUS = 3
IDX_AXIAL = 4
IDX_PSFPIX = 5

SLIDER_MAX = 1000
_Z2 = zernike_nm(N_ZERNIKE)[0]  # PSFguiPrez.m line 13, U.Z(2)
_JET = matplotlib.colormaps["jet"]
_COOL = matplotlib.colormaps["cool"].resampled(20)(np.arange(20))
_COOL[:, 2] = 0  # PSFguiPrez.m line 315: cool(20)*diag([1 1 0])
_COOL = _COOL[::-1]  # flipud


def _order_color(n: int) -> np.ndarray:
    if n < _Z2:
        return np.array(_JET(n / max(_Z2 - 1, 1))[:3])
    return np.array([0.5, 0.5, 0.5])


def _button_color(n: int, m: int) -> np.ndarray:
    factor = 1 - 0.4 * (abs(m) + 3) / (n + 3)
    return factor * _order_color(n)


def _transparent_panes(ax) -> None:
    """Make the 3D axis box (x/y/z panes) transparent, keep faint grid lines."""
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_facecolor((0, 0, 0, 0))
        axis.pane.set_edgecolor((1, 1, 1, 0.3))
        axis._axinfo["grid"]["color"] = (1, 1, 1, 0.2)


def _qcolor(rgb: np.ndarray) -> str:
    r, g, b = (np.clip(rgb, 0, 1) * 255).astype(int)
    return f"rgb({r},{g},{b})"


class ClickButton(QPushButton):
    """QPushButton that remembers the vertical click position as a 0-1 ratio.

    Mirrors PSFguiPrez.m's use of `CurrentPoint` to derive an intensity
    factor `c` from where inside a button the user clicked (lines 122-123).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.click_ratio = 1.0

    def mousePressEvent(self, event):
        self.click_ratio = 1 - event.position().y() / max(self.height(), 1)
        super().mousePressEvent(event)


ROW_H = 19  # PSFguiPrez.m: fh-19*kp row pitch
CTRL_H = 16  # uicontrol height


def row_rects(kp: int, is_zernike: bool) -> tuple[tuple, tuple, tuple, tuple]:
    """Pixel geometry (x, y, w, h) for push/edit_left/slider/edit_right of row `kp` (1-based).

    Direct port of the Position formulas in PSFguiPrez.m lines 47-72.
    """
    y = ROW_H * (kp - 1)
    push = (52, y, 38, CTRL_H) if is_zernike else (2, y, 88, CTRL_H)
    edit_left = (push[0] + push[2] + 2, y, 40, CTRL_H)
    slider = (edit_left[0] + edit_left[2] + 2, y, 150, CTRL_H)
    edit_right = (slider[0] + slider[2] + 2, y, 40, CTRL_H)
    return push, edit_left, slider, edit_right


class Row:
    def __init__(self, parent, label: str, left: float, right: float, n: int, m: int, is_zernike: bool):
        self.label = label
        self.n = n
        self.m = m
        self.is_zernike = is_zernike
        self.push = ClickButton(label, parent)
        self.edit_left = QLineEdit(_fmt(left), parent)
        self.edit_right = QLineEdit(_fmt(right), parent)
        self.slider = QSlider(Qt.Orientation.Horizontal, parent)
        self.slider.setRange(0, SLIDER_MAX)
        self.slider.setValue(SLIDER_MAX // 2)
        for edit in (self.edit_left, self.edit_right):
            edit.setValidator(QDoubleValidator())
        color = _qcolor(_button_color(n, m))
        style = f"background-color:{color}; color:white;"
        self.push.setStyleSheet(style)
        self.edit_left.setStyleSheet(style)
        self.edit_right.setStyleSheet(style)
        self.slider.setStyleSheet(style)

    def place(self, kp: int) -> None:
        push_r, el_r, sl_r, er_r = row_rects(kp, self.is_zernike)
        self.push.setGeometry(*push_r)
        self.edit_left.setGeometry(*el_r)
        self.slider.setGeometry(*sl_r)
        self.edit_right.setGeometry(*er_r)

    def ratio(self) -> float:
        return self.slider.value() / SLIDER_MAX

    def value(self) -> float:
        left = float(self.edit_left.text() or 0.0)
        right = float(self.edit_right.text() or 0.0)
        ratio = self.ratio()
        return right * ratio + left * (1 - ratio)

    def set_ratio(self, ratio: float) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(int(round(np.clip(ratio, 0, 1) * SLIDER_MAX)))
        self.slider.blockSignals(False)


def _fmt(v: float) -> str:
    return f"{v:g}"


class GraphWindow(QMainWindow):
    """Second window: wavefront / PSF / ray-tracing / zoom (PSFguiPrez.m lines 281-325)."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wavefront, PSF & Ray tracing")
        self.resize(1200, 800)
        fig = Figure(facecolor="black")
        self.canvas = FigureCanvasQTAgg(fig)
        self.setCentralWidget(self.canvas)
        self.ax_wavefront = fig.add_subplot(2, 2, 1, projection="3d", facecolor="black")
        self.ax_psf = fig.add_subplot(2, 2, 2, projection="3d", facecolor="black")
        self.ax_rays = fig.add_subplot(2, 2, 3, projection="3d", facecolor="black")
        self.ax_zoom = fig.add_subplot(2, 2, 4, projection="3d", facecolor="black")
        for ax in (self.ax_wavefront, self.ax_psf, self.ax_rays, self.ax_zoom):
            ax.tick_params(colors="white")
            ax.title.set_color("white")
            _transparent_panes(ax)

    def grab_frame(self) -> np.ndarray:
        self.canvas.draw()
        buf = np.asarray(self.canvas.buffer_rgba())
        return buf[:, :, :3].copy()

    def refresh(
        self,
        Xp,
        Yp,
        W,
        Rn,
        xr,
        psf,
        K,
        c_const,
        x,
        y,
        z,
        p,
        v,
        lambda_,
        pupdiam_mm,
        defocus_mm,
        axial_mm,
        undersampled: bool,
    ):
        Wd = np.where(Rn > 1, np.nan, W)

        ax = self.ax_wavefront
        ax.cla()
        ax.set_facecolor("black")
        ax.plot_surface(
            1e3 * Xp, 1e3 * Yp, 1e6 * Wd, cmap="viridis",
            edgecolor="black", linewidth=0.1, rstride=2, cstride=2, antialiased=True,
        )
        ax.set_xlabel("mm", color="white")  # PSFguiPrez.m line 286
        ax.set_zlabel("µm", color="white")
        ax.set_zlim(-1, 1)  # PSFguiPrez.m line 287: zlim([-1 1])
        rms = np.nanstd(1e6 * Wd)
        title = f"Wavefront (rms={rms:05.3f} lambda={1e9*lambda_:5.1f} Pd={pupdiam_mm:04.2f})"
        color = "red" if undersampled else "white"
        ax.set_title(title, color=color)
        ax.tick_params(colors="white")
        _transparent_panes(ax)

        ax = self.ax_psf
        ax.cla()
        ax.set_facecolor("black")
        Xr, Yr = np.meshgrid(xr, xr)
        ax.plot_surface(
            1e6 * Xr, 1e6 * Yr, psf, cmap="viridis",
            edgecolor="black", linewidth=0.1, rstride=2, cstride=2, antialiased=True,
        )
        ax.view_init(elev=90, azim=-90)  # PSFguiPrez.m line 296: view(0,90)
        ax.set_xlabel("µm", color="white")  # PSFguiPrez.m line 295
        ax.set_zticks([])
        ax.set_title(f"PSF (defoc={defocus_mm:05.2f} AL={axial_mm:05.2f})", color="white")
        ax.tick_params(colors="white")
        _transparent_panes(ax)

        ray_colors = _COOL[np.clip((19 * np.hypot(x, y) / max(np.max(np.hypot(x, y)), 1e-12)).astype(int), 0, 19)]

        ax = self.ax_rays
        ax.cla()
        ax.set_facecolor("black")
        ax.plot_surface(
            1e3 * Yp, 1e3 * (K - c_const), 1e3 * Xp, cmap="viridis",
            edgecolor="black", linewidth=0.1, rstride=4, cstride=4, alpha=0.6,
        )
        for k in range(len(x)):
            xs = 1e3 * np.array([y[k], y[k], y[k] + v[k, 0] * p[k, 1]])
            ys = 1e3 * np.array([1e-3, z[k], z[k] + v[k, 0] * p[k, 2]])
            zs = 1e3 * np.array([x[k], x[k], x[k] + v[k, 0] * p[k, 0]])
            ax.plot(xs, ys, zs, "-", color=ray_colors[k])
        ax.set_title("Ray tracing", color="white")
        ax.view_init(elev=10, azim=-125)
        ax.tick_params(colors="white")
        _transparent_panes(ax)

        ax = self.ax_zoom
        ax.cla()
        ax.set_facecolor("black")
        g = 10
        for k in range(len(x)):
            xs = 1e3 * (y[k] + v[k, :] * p[k, 1]) * g
            ys = 1e3 * (z[k] + v[k, :] * p[k, 2])
            zs = 1e3 * (x[k] + v[k, :] * p[k, 0]) * g
            ax.plot(xs, ys, zs, ".-", color=ray_colors[k])
        ax.set_title("Zoom", color="white")
        ax.view_init(elev=10, azim=-125)
        ax.tick_params(colors="white")
        _transparent_panes(ax)

        self.canvas.draw_idle()


class ControlWindow(QMainWindow):
    """Control panel (PSFguiPrez.m lines 34-107)."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wavefront, PSF & Co. - Controls")
        self.setStyleSheet("background-color:black;")
        self.graph = GraphWindow()

        fh = ROW_H * (len(PARAM_ROWS) + N_ZERNIKE) + 10  # PSFguiPrez.m line 34
        central = QWidget()
        central.setFixedSize(330, fh)
        central.setStyleSheet("background-color:black;")

        self.rows: list[Row] = []
        for label, left, right in PARAM_ROWS:
            self.rows.append(Row(central, label, left, right, _Z2, _Z2 - 1, is_zernike=False))
        for j in range(N_ZERNIKE):
            n, m = zernike_nm(j)
            label = f"Z({n},{m:+d})"
            self.rows.append(Row(central, label, -0.5, 0.5, n, m, is_zernike=True))

        for kp, row in enumerate(self.rows, start=1):
            row.place(kp)
            row.push.clicked.connect(lambda _checked, r=row: self._on_row_push(r))
            row.slider.valueChanged.connect(lambda _v: self.recalc())
            row.edit_left.editingFinished.connect(self.recalc)
            row.edit_right.editingFinished.connect(self.recalc)
        self.setCentralWidget(central)

        self.rows[IDX_PUPNORM].set_ratio(0.8)  # PSFguiPrez.m line 75

        # Command buttons (PSFguiPrez.m lines 79-102): Refresh/Rec/"0" overlay the push-button
        # column of the first 3 Zernike rows; "?" and ">" are narrow strips spanning the
        # full height of the Zernike section, to the left of the row push-buttons.
        cmd_color = _qcolor(_button_color(_Z2, _Z2 + 1))
        fn = len(PARAM_ROWS)
        narrow_y = ROW_H * fn + 2 * N_ZERNIKE + 2
        narrow_h = 17 * N_ZERNIKE - 2
        self.btn_refresh = ClickButton("Refresh", central)
        self.btn_refresh.setGeometry(2, ROW_H * fn, 50, CTRL_H)
        self.btn_rec = ClickButton("Rec", central)
        self.btn_rec.setGeometry(2, ROW_H * (fn + 1), 50, CTRL_H)
        self.btn_zero = ClickButton("0", central)
        self.btn_zero.setGeometry(2, ROW_H * (fn + 2), 50, CTRL_H)
        self.btn_random = ClickButton("?", central)
        self.btn_random.setGeometry(18, narrow_y, 16, narrow_h)
        self.btn_play = ClickButton(">", central)
        self.btn_play.setGeometry(34, narrow_y, 16, narrow_h)
        for btn in (self.btn_refresh, self.btn_rec, self.btn_zero, self.btn_random, self.btn_play):
            btn.setStyleSheet(f"background-color:{cmd_color}; color:white;")
            btn.raise_()

        self.btn_refresh.clicked.connect(self.recalc)
        self.btn_rec.clicked.connect(self._toggle_record)
        self.btn_zero.clicked.connect(self._zero_zernikes)
        self.btn_random.clicked.connect(self._randomize)
        self.btn_play.clicked.connect(self._play)

        self._recording = False
        self._gif_frames: list[np.ndarray] = []
        self._gif_path: Path | None = None

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate_tick)
        self._anim_frame = 0
        self._anim_frames_total = 10
        self._anim_start: list[float] = []
        self._anim_target: list[float] = []

        self.graph.show()
        self.recalc()

    def _zernike_rows(self) -> list[Row]:
        return [r for r in self.rows if r.is_zernike]

    def _on_row_push(self, row: Row) -> None:
        row.set_ratio(0.5)
        self.recalc()

    def _zero_zernikes(self) -> None:
        for row in self._zernike_rows():
            row.set_ratio(0.5)
        self.recalc()

    def _randomize(self) -> None:
        c = self.btn_random.click_ratio
        for row in self._zernike_rows():
            ratio = c * (random.random() - 0.5) / (0.5 * row.n + 1) + 0.5
            row.set_ratio(ratio)
        self.recalc()

    def _play(self) -> None:
        c = self.btn_play.click_ratio
        rows = self._zernike_rows()
        self._anim_start = [row.ratio() for row in rows]
        self._anim_target = [
            c * (random.random() - 0.5) / (0.5 * row.n + 1) + 0.5 for row in rows
        ]
        self._anim_frame = 0
        self._anim_timer.start(60)

    def _animate_tick(self) -> None:
        self._anim_frame += 1
        nf = self._anim_frames_total
        kf = self._anim_frame
        rows = self._zernike_rows()
        for row, start, target in zip(rows, self._anim_start, self._anim_target):
            ratio = (start * (nf - kf) + target * kf) / nf
            row.set_ratio(ratio)
        self.recalc()
        if kf >= nf:
            self._anim_timer.stop()

    def _toggle_record(self) -> None:
        if not self._recording:
            out_dir = Path(__file__).resolve().parent.parent / "output"
            out_dir.mkdir(exist_ok=True)
            stamp = dt.datetime.now().strftime("%Y-%m-%d_%Hh%Mm%S.%f")[:-3]
            self._gif_path = out_dir / f"fig {stamp}.gif"
            self._gif_frames = []
            self._recording = True
            self.btn_rec.setStyleSheet("background-color:red; color:white;")
            print(self._gif_path)
        else:
            self._recording = False
            cmd_color = _qcolor(_button_color(_Z2, _Z2 + 1))
            self.btn_rec.setStyleSheet(f"background-color:{cmd_color}; color:white;")
            self._save_gif()

    def _save_gif(self) -> None:
        """Write the buffered frames as a GIF with a transparent background.

        The on-screen windows stay black; only the exported GIF gets its
        black background made transparent, mirroring PSFguiPrez.m's
        border-color-based TransparentColor logic (lines 371-378).
        """
        if not self._gif_frames or self._gif_path is None:
            return
        pil_frames = []
        for rgb in self._gif_frames:
            img = Image.fromarray(rgb, "RGB").quantize(colors=255, method=Image.MEDIANCUT)
            palette = np.array(img.getpalette()[: 256 * 3]).reshape(-1, 3)
            transparent_idx = int(np.argmin(np.sum(palette.astype(int) ** 2, axis=1)))
            img.info["transparency"] = transparent_idx
            pil_frames.append(img)
        pil_frames[0].save(
            self._gif_path,
            save_all=True,
            append_images=pil_frames[1:],
            duration=100,
            loop=0,
            disposal=2,
            transparency=pil_frames[0].info["transparency"],
        )
        self._gif_frames = []

    def recalc(self) -> None:
        lambda_ = 1e-9 * self.rows[0].value()
        zerdiam = 1e-3 * self.rows[IDX_ZERDIAM].value()
        pupnorm = 1e-2 * self.rows[IDX_PUPNORM].value()
        defocus = 1e-3 * self.rows[IDX_DEFOCUS].value()
        axial = 1e-3 * self.rows[IDX_AXIAL].value()
        psfpix = 1e-6 * self.rows[IDX_PSFPIX].value()

        N2 = 2 ** math.ceil(math.log2(N))
        Xp1d = np.linspace(-0.5, 0.5, N2) * lambda_ * axial / (NO * psfpix)
        Xp, Yp = np.meshgrid(Xp1d, Xp1d)
        Rp = np.sqrt(Xp**2 + Yp**2)
        Rn = Rp / (zerdiam / 2)

        zcoefs = np.array([1e-6 * row.value() for row in self._zernike_rows()])
        W = build_wavefront(Xp, Yp, Rn, zcoefs)
        foc = optics.eye_focus(Xp, Yp, axial, defocus, NO)
        psf = optics.compute_psf(W, foc, Xp, Yp, Rn, pupnorm, lambda_)
        xr = np.linspace(-0.5, 0.5, N2) * N2 * psfpix

        K = optics.cornea_surface(W, Xp, Yp, axial, defocus, NO)
        c_const = (axial + defocus) * (NO - 1) / NO

        x, y = optics.ray_grid(60, pupnorm, zerdiam)
        z, p = optics.trace_rays(Xp, Yp, W, x, y, axial, defocus, NO)
        v = optics.ray_extension(z, p, axial, defocus)

        undersampled = optics.check_sampling(Rn)
        self._apply_sampling_warning(undersampled)

        self.graph.refresh(
            Xp, Yp, W, Rn, xr, psf, K, c_const, x, y, z, p, v,
            lambda_=lambda_,
            pupdiam_mm=1e3 * pupnorm * zerdiam,
            defocus_mm=1e3 * defocus, axial_mm=1e3 * axial,
            undersampled=undersampled,
        )

        if self._recording:
            self._gif_frames.append(self.graph.grab_frame())

    def _apply_sampling_warning(self, undersampled: bool) -> None:
        rows = (self.rows[IDX_ZERDIAM], self.rows[IDX_PSFPIX])
        if undersampled:
            for row in rows:
                row.push.setStyleSheet("background-color:red; color:white;")
                row.slider.setStyleSheet("background-color:red; color:white;")
        else:
            for row in rows:
                color = _qcolor(_button_color(row.n, row.m))
                style = f"background-color:{color}; color:white;"
                row.push.setStyleSheet(style)
                row.slider.setStyleSheet(style)

