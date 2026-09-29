"""Main application window.

Phase 1 scope: a menu action to open an image via a file picker, and
display it. The full scientific-workstation layout (source panel, analysis
controls, quality/pipeline/results/warnings tabs, detection/annotation/
calibration/export tabs — spec Section 12) is built incrementally starting
Phase 2; this is the minimal skeleton those panels will be added to.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from app.acquisition.image_import import (
    FileImportSource,
    ImageLoadError,
    UnsupportedImageFormatError,
)
from app.config.settings import APP_NAME, APP_VERSION, SUPPORTED_IMAGE_EXTENSIONS
from app.gui.image_viewer import ImageViewer


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1100, 750)

        self._import_source = FileImportSource()

        self._viewer = ImageViewer(self)
        self.setCentralWidget(self._viewer)

        self._build_menu()
        self.statusBar().showMessage("Ready — File > Open Image to load a lab image.")

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        open_action = file_menu.addAction("&Open Image...")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_image)

        file_menu.addSeparator()
        exit_action = file_menu.addAction("E&xit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

    def _on_open_image(self) -> None:
        extensions = " ".join(f"*{ext}" for ext in SUPPORTED_IMAGE_EXTENSIONS)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            f"Images ({extensions})",
        )
        if not file_path:
            return  # User cancelled.

        self._load_image(Path(file_path))

    def _load_image(self, path: Path) -> None:
        try:
            image, metadata = self._import_source.load(path)
        except (UnsupportedImageFormatError, ImageLoadError, FileNotFoundError) as exc:
            QMessageBox.critical(self, "Could not load image", str(exc))
            self.statusBar().showMessage(f"Failed to load {path.name}")
            return

        self._viewer.set_image(image)
        self.statusBar().showMessage(
            f"Loaded {metadata.filename} — {metadata.width}x{metadata.height}, "
            f"{metadata.channels} channel(s)"
        )
