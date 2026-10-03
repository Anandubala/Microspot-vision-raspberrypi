"""Main application window.

Phase 1: file-open + display skeleton.
Phase 2: routed Open through the import pipeline (validate/hash/copy/
quality) and added the quality panel.
Phase 3: upgraded the viewer to support zoom/pan/ROI, ran every loaded
image through the preprocessing pipeline, and added a stage selector so
every intermediate (grayscale, normalized, background estimate, corrected,
denoised, enhanced) is inspectable — per spec Section 7's requirement that
every stage be visible in the GUI.

The full scientific-workstation layout (spec Section 12) is still built up
incrementally; this is a working subset, not the final layout.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QToolBar,
    QWidget,
)

from app.acquisition.image_import import ImageLoadError, UnsupportedImageFormatError
from app.acquisition.import_pipeline import import_image
from app.acquisition.validation import InvalidImageError
from app.config.settings import APP_NAME, APP_VERSION, SUPPORTED_IMAGE_EXTENSIONS
from app.gui.image_viewer import ImageViewer
from app.gui.quality_panel import QualityPanel
from app.image_engine.preprocessing.pipeline import run_preprocessing_pipeline


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1150, 850)

        self._current_image = None  # the originally loaded array (color or gray)
        self._stages: dict[str, object] = {}

        self._viewer = ImageViewer(self)
        self._quality_panel = QualityPanel(self)

        splitter = QSplitter(Qt.Orientation.Vertical, self)
        splitter.addWidget(self._viewer)
        splitter.addWidget(self._quality_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        self._build_menu()
        self._build_toolbar()
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

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("View", self)
        self.addToolBar(toolbar)

        toolbar.addWidget(QLabel(" Stage: "))
        self._stage_selector = QComboBox(self)
        self._stage_selector.setMinimumWidth(160)
        self._stage_selector.currentTextChanged.connect(self._on_stage_changed)
        toolbar.addWidget(self._stage_selector)

        toolbar.addSeparator()

        fit_button = QPushButton("Fit to Window", self)
        fit_button.clicked.connect(self._viewer.fit_to_window)
        toolbar.addWidget(fit_button)

        toolbar.addSeparator()

        self._roi_button = QPushButton("ROI: Off", self)
        self._roi_button.setCheckable(True)
        self._roi_button.toggled.connect(self._on_roi_toggled)
        toolbar.addWidget(self._roi_button)

        clear_roi_button = QPushButton("Clear ROI", self)
        clear_roi_button.clicked.connect(self._viewer.clear_roi)
        toolbar.addWidget(clear_roi_button)

        self._viewer.roi_changed.connect(self._on_roi_changed)

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

        self._current_image = result.image
        self._stages = {"Original": result.image}
        self._stages.update(run_preprocessing_pipeline(result.image))

        self._stage_selector.blockSignals(True)
        self._stage_selector.clear()
        self._stage_selector.addItems(list(self._stages.keys()))
        self._stage_selector.blockSignals(False)
        self._stage_selector.setCurrentText("Original")

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

    def _on_stage_changed(self, stage_name: str) -> None:
        if stage_name and stage_name in self._stages:
            self._viewer.set_image(self._stages[stage_name])

    def _on_roi_toggled(self, enabled: bool) -> None:
        self._viewer.set_roi_mode(enabled)
        self._roi_button.setText("ROI: On" if enabled else "ROI: Off")

    def _on_roi_changed(self, roi) -> None:
        if roi is None:
            self.statusBar().showMessage("ROI cleared.")
        else:
            x, y, w, h = roi
            self.statusBar().showMessage(
                f"ROI selected: x={x}, y={y}, w={w}, h={h} (pixels — not yet used by analysis)"
            )
