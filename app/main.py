"""MicroSpot Vision entry point."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.config.settings import APP_NAME, ensure_data_dirs
from app.gui.main_window import MainWindow


def main() -> int:
    ensure_data_dirs()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
