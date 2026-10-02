"""Main application window.

Phase 1 added the file-open + display skeleton. Phase 2 routes that open
action through the full import pipeline (validate -> SHA-256 -> copy to
data/original/ -> quality analysis) and displays the real, computed
quality diagnostics. The full scientific-workstation layout (source panel,
analysis controls, pipeline-stage/results/warnings tabs, detection/
annotation/calibration/export tabs — spec Section 12) is still built up
incrementally in later phases; this is a working subset, not the final
layout.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QSplitter

from app.acquisition.image_import import ImageLoadError, UnsupportedImageFormatError
from app.acquisition.import_pipeline import import_image
from app.acquisition.validation import InvalidImageError
from app.config.settings import APP_NAME, APP_VERSION, SUPPORTED_IMAGE_EXTENSIONS
from app.gui.image_viewer import ImageViewer
from app.gui.quality_panel import QualityPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1100, 800)

        self._viewer = ImageViewer(self)
        self._quality_panel = QualityPanel(self)

        splitter = QSplitter(Qt.Orientation.Vertical, self)
        splitter.addWidget(self._viewer)
        splitter.addWidget(self._quality_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

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
            result = import_image(path)
        except (
            UnsupportedImageFormatError,
            ImageLoadError,
            FileNotFoundError,
            InvalidImageError,
        ) as exc:
            QMessageBox.critical(self, "Could not load image", str(exc))
            self.statusBar().showMessage(f"Failed to load {path.name}")
            return

        self._viewer.set_image(result.image)
        self._quality_panel.show_result(result.quality, result.record)

        status = (
            "clean" if result.quality.is_clean else f"{len(result.quality.warnings)} warning(s)"
        )
        self.statusBar().showMessage(
            f"Loaded {result.loaded.filename} — "
            f"{result.loaded.width}x{result.loaded.height}, "
            f"{result.loaded.channels} channel(s) — quality: {status}"
        )
