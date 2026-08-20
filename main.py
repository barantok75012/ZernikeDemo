"""Entry point: Wavefront, PSF & Co. demo (Python port of PSFguiPrez.m)."""
import sys

from PyQt6.QtWidgets import QApplication

from zernike_psf.gui import ControlWindow


def main() -> None:
    app = QApplication(sys.argv)
    control = ControlWindow()
    control.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
