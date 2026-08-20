"""PyQt6/Matplotlib interface for the optical demo."""

from __future__ import annotations

import sys

import imageio.v2 as imageio
import matplotlib
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QSlider, QVBoxLayout, QWidget

from optics import OpticalParameters, calculate_optics


class PSFWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Wavefront, PSF & Ray tracing")
        self.parameters = OpticalParameters(zernike_coefficients_um=np.zeros(45))
        self.sliders: list[QSlider] = []
        self.bounds = [(450, 650), (2, 8), (0, 100), (-1, 1), (21, 24), (0.5, 1.5)]
        self.default_positions = [500, 500, 800, 500, 500, 500]
        self.parameter_rows: list[tuple[QSlider, QLineEdit, QLineEdit]] = []
        self.zernike_rows: list[tuple[QSlider, QLineEdit, QLineEdit]] = []
        self.recording = False
        self.frames: list[np.ndarray] = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        controls = QVBoxLayout()
        labels = ["Lambda (nm)", "Zer Ø (mm)", "Pup Ø (%)", "Defoc (mm)", "AL (mm)", "PSFpix (um)"]
        for index, (label, (low, high)) in enumerate(zip(labels, self.bounds)):
            row, slider, minimum, maximum = self._control_row(label, low, high, self.default_positions[index])
            self.parameter_rows.append((slider, minimum, maximum)); controls.addLayout(row)

        zernike_group = QVBoxLayout()
        for index in range(45):
            n, m = self._zernike_label(index)
            row, slider, minimum, maximum = self._control_row(f"Z({n},{m:+d})", -0.5, 0.5, 500)
            self.sliders.append(slider); self.zernike_rows.append((slider, minimum, maximum)); zernike_group.addLayout(row)
        controls.addLayout(zernike_group)
        buttons = QHBoxLayout()
        for text, slot in [("Refresh", self.refresh), ("Zero", self.zero), ("Random", self.randomize), ("Play", self.play), ("Record", self.toggle_recording)]:
            button = QPushButton(text); button.clicked.connect(slot); buttons.addWidget(button)
        controls.addLayout(buttons); controls.addStretch()
        control_widget = QWidget(); control_widget.setLayout(controls)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(control_widget); scroll.setMinimumWidth(365)
        self.figure = Figure(facecolor="black"); self.canvas = FigureCanvasQTAgg(self.figure)
        self.axes = [self.figure.add_subplot(221, projection="3d"), self.figure.add_subplot(222, projection="3d"), self.figure.add_subplot(223, projection="3d"), self.figure.add_subplot(224, projection="3d")]
        self._style_axes()
        layout = QHBoxLayout(self); layout.addWidget(scroll, 0); layout.addWidget(self.canvas, 1)

    def _style_axes(self) -> None:
        for axis in self.axes:
            axis.set_facecolor("none")
            axis.tick_params(axis="both", colors="white", labelcolor="white")
            axis.xaxis.label.set_color("white")
            axis.yaxis.label.set_color("white")
            axis.title.set_color("white")
            for spine in axis.spines.values():
                spine.set_color("white")
            if hasattr(axis, "zaxis"):
                axis.tick_params(axis="z", colors="white", labelcolor="white")
                axis.zaxis.label.set_color("white")
                axis.zaxis.pane.fill = False
                axis.xaxis.pane.fill = False
                axis.yaxis.pane.fill = False
                axis.zaxis.pane.set_edgecolor("white")
                axis.xaxis.pane.set_edgecolor("white")
                axis.yaxis.pane.set_edgecolor("white")
            axis.grid(True, color="white", alpha=0.25)

    def _control_row(self, name: str, minimum_value: float, maximum_value: float, default_position: int) -> tuple[QHBoxLayout, QSlider, QLineEdit, QLineEdit]:
        row = QHBoxLayout(); row.setSpacing(2)
        reset = QPushButton(name); reset.setFixedWidth(82); reset.setToolTip("Remettre la valeur par défaut")
        minimum = QLineEdit(str(minimum_value)); maximum = QLineEdit(str(maximum_value))
        minimum.setFixedWidth(42); maximum.setFixedWidth(42)
        slider = QSlider(Qt.Orientation.Horizontal); slider.setRange(0, 1000); slider.setValue(default_position); slider.setMinimumWidth(115)
        reset.clicked.connect(lambda: slider.setValue(default_position))
        slider.valueChanged.connect(self.refresh)
        minimum.editingFinished.connect(self.refresh); maximum.editingFinished.connect(self.refresh)
        row.addWidget(reset); row.addWidget(minimum); row.addWidget(slider, 1); row.addWidget(maximum)
        return row, slider, minimum, maximum

    @staticmethod
    def _zernike_label(index: int) -> tuple[int, int]:
        coefficient = index + 1
        n = int(np.ceil((-3 + np.sqrt(1 + 8 * coefficient)) / 2))
        m = 2 * index - n * (n + 2)
        return n, m

    def _parameter_values(self) -> OpticalParameters:
        values = [self._control_value(row) for row in self.parameter_rows]
        coefficients = np.array([self._control_value(row) for row in self.zernike_rows])
        return OpticalParameters(*values, coefficients)

    @staticmethod
    def _control_value(row: tuple[QSlider, QLineEdit, QLineEdit]) -> float:
        slider, minimum, maximum = row
        try:
            low = float(minimum.text()); high = float(maximum.text())
            if high <= low:
                raise ValueError
        except ValueError:
            return 0.0
        return low + (high - low) * slider.value() / 1000

    def refresh(self) -> None:
        view_angles = [(axis.elev, axis.azim) if axis.name == "3d" else None for axis in self.axes]
        parameters = self._parameter_values()
        self.result = calculate_optics(parameters); result = self.result
        for axis in self.axes: axis.clear()
        self._style_axes()
        effective_pupil = parameters.pupil_percent / 100.0
        zernike_surface = np.where(result.normalized_radius <= 1.0, result.wavefront * 1e6, np.nan)
        pupil_surface = np.where(result.normalized_radius <= effective_pupil, result.wavefront * 1e6, np.nan)
        diameter_mm = parameters.zernike_diameter_mm
        mesh_stride = 4
        self.axes[0].plot_wireframe(
            result.x_pupil * 1e3,
            result.y_pupil * 1e3,
            zernike_surface,
            rstride=mesh_stride,
            cstride=mesh_stride,
            color="#00bcd4",
            linewidth=0.35,
            alpha=0.8,
        )
        self.axes[0].plot_surface(
            result.x_pupil * 1e3,
            result.y_pupil * 1e3,
            pupil_surface,
            cmap="viridis",
            rstride=mesh_stride,
            cstride=mesh_stride,
            linewidth=0,
            antialiased=True,
            alpha=0.9,
        )
        self.axes[0].set_xlim(-diameter_mm / 2.0, diameter_mm / 2.0)
        self.axes[0].set_ylim(-diameter_mm / 2.0, diameter_mm / 2.0)
        self.axes[0].set_zlim(-1, 1)
        self.axes[0].set_xlabel("X (mm)"); self.axes[0].set_ylabel("Y (mm)"); self.axes[0].set_zlabel("Wavefront (um)")
        self.axes[0].set_title(f"Wavefront (peak PSF={result.peak_psf:.4g})", color="white")
        psf_axis_um = result.psf_axis * 1e6
        psf_height_um = result.psf * psf_axis_um[-1] / result.psf.max()
        psf_x, psf_y = np.meshgrid(psf_axis_um, psf_axis_um)
        self.axes[1].plot_surface(psf_x, psf_y, psf_height_um, cmap="magma", linewidth=0, antialiased=True)
        self.axes[1].set_xlabel("X (um)"); self.axes[1].set_ylabel("Y (um)"); self.axes[1].set_zlabel("PSF (um)")
        self.axes[1].set_title("PSF", color="white")
        for ray, color in zip(result.ray_points, result.ray_colors):
            self.axes[2].plot(ray[:, 2] * 1e3, ray[:, 1] * 1e3, ray[:, 0] * 1e3, color=(color, color * 0.7, 0.1))
            self.axes[3].plot(ray[:, 2] * 1e3, ray[:, 1] * 1e3, ray[:, 0] * 1e3, color=(color, color * 0.7, 0.1))
        self.axes[2].set_xlabel("Y (mm)"); self.axes[2].set_ylabel("Z (mm)"); self.axes[2].set_zlabel("X (mm)")
        self.axes[3].set_xlabel("Y (mm)"); self.axes[3].set_ylabel("Z (mm)"); self.axes[3].set_zlabel("X (mm)")
        self.axes[2].set_title("Ray tracing", color="white"); self.axes[3].set_title("Zoom", color="white")
        for axis, angles in zip(self.axes, view_angles):
            if angles is not None:
                axis.view_init(elev=angles[0], azim=angles[1])
        self.figure.tight_layout(); self.canvas.draw_idle()
        if self.recording: self.frames.append(self.canvas.buffer_rgba()[:, :, :3].copy())

    def zero(self) -> None:
        for slider in self.sliders: slider.setValue(0)

    def randomize(self) -> None:
        for slider in self.sliders: slider.setValue(np.random.randint(-50, 51))

    def play(self) -> None:
        self.timer.start(100)

    def animate(self) -> None:
        self.randomize()

    def toggle_recording(self) -> None:
        self.recording = not self.recording
        if not self.recording and self.frames:
            imageio.mimsave("psf_animation.gif", self.frames, duration=0.1, loop=0); self.frames.clear()


def run() -> int:
    matplotlib.use("qtagg")
    app = QApplication(sys.argv); window = PSFWindow(); window.resize(1500, 900); window.show()
    return app.exec()
