"""Main application window.

Phase 1: file-open + display skeleton.
Phase 2: routed Open through the import pipeline (validate/hash/copy/
quality) and added the quality panel.
Phase 3: upgraded the viewer to support zoom/pan/ROI, ran every loaded
image through the preprocessing pipeline, and added a stage selector so
every intermediate (grayscale, normalized, background estimate, corrected,
denoised, enhanced) is inspectable — per spec Section 7's requirement that
every stage be visible in the GUI.
Phase 4: runs classical-CV segmentation + candidate extraction on the
Enhanced stage, adding "Segmentation Mask" and "Raw Candidates" to the
same inspectable stage list, with a live candidate count. These are raw,
unfiltered candidates (Section 1: never implicitly a validated spot).
Phase 5: runs every raw candidate through filter_candidates() (explicit,
named rejection reasons), adds "Validated Spots" (the numbered, reviewer-
facing final overlay) to the stage list, and shows a results panel with
the validated count and a rejection-reason breakdown.
Phase 6: touching-spot separation (watershed) wired in via
segment_and_extract()'s third return value; per-spot pixel sizes shown in
the results panel.

Phase 7 (2026-10-06, real-lab-image feedback round): three real problems
surfaced by an actual lab image with ~9,800 candidates, not synthetic
test data:
  1. PERFORMANCE: the entire analysis pipeline ran synchronously on the
     GUI thread, so the window appeared frozen for however long detection
     took (~1-1.5 minutes on the reported hardware, dominated by a
     candidate-extraction bug fixed the same session — see
     candidate_extraction.py and docs/PHASE_7.md). Fixed here by moving
     preprocessing/detection/filtering onto a QThread (AnalysisWorker),
     per spec Section 12's own instruction ("Use QThread/QThreadPool for
     processing so the GUI never freezes; never touch widgets from a
     worker thread directly" — not followed until now). The original
     image now displays immediately after import; an indeterminate
     progress bar runs during analysis.
  2. SPLITTER COLLAPSE: dragging the splitter handle below the quality/
     results panels could shrink one to zero height with no way to drag
     it back. Fixed with setChildrenCollapsible(False) and explicit
     minimum heights, and restructured quality+results side by side
     (a nested horizontal splitter) per direct user request.
  3. OVERSIZED FALSE POSITIVES: large, roughly circular structures in a
     real image (out-of-focus cells/debris, tens to ~150px across) were
     passing filtering because circularity/solidity alone favor round
     shapes regardless of size. FilterConfig.max_diameter_px, previously
     unset (None), now defaults to a (still-generic, not yet lab-
     calibrated) 20.0px cap — see docs/PHASE_7.md for the reasoning and
     its limitations.

The full scientific-workstation layout (spec Section 12) is still built up
incrementally; this is a working subset, not the final layout.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QToolBar,
)

from app.acquisition.image_import import ImageLoadError, UnsupportedImageFormatError
from app.acquisition.import_pipeline import ImportResult, import_image
from app.acquisition.validation import InvalidImageError
from app.config.schemas import DetectionConfig, FilterConfig
from app.config.settings import APP_NAME, APP_VERSION, SUPPORTED_IMAGE_EXTENSIONS
from app.gui.image_viewer import ImageViewer
from app.gui.quality_panel import QualityPanel
from app.gui.results_panel import ResultsPanel
from app.image_engine.detection.classical_cv import segment_and_extract
from app.image_engine.filtering.filters import filter_candidates, validated_count
from app.image_engine.preprocessing.pipeline import run_preprocessing_pipeline
from app.image_engine.visualization.overlays import draw_candidate_outlines, draw_validated_overlay


class AnalysisWorker(QThread):
    """Runs preprocessing + detection + filtering off the GUI thread.

    Takes plain data in (a numpy array, two config objects) and emits
    plain data out (a dict) via a Qt signal — it never touches a QWidget
    directly, which is the part of Section 12's threading instruction
    that actually matters: Qt delivers the signal back on the main
    thread automatically, so MainWindow's slot is the only place that
    touches widgets.
    """

    finished_analysis = Signal(dict)

    def __init__(
        self,
        image,
        detection_config: DetectionConfig,
        filter_config: FilterConfig,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._image = image
        self._detection_config = detection_config
        self._filter_config = filter_config

    def run(self) -> None:
        stages = run_preprocessing_pipeline(self._image)

        mask, raw_candidates, separation_applied = segment_and_extract(
            stages["Enhanced"], self._detection_config
        )
        stages["Segmentation Mask"] = mask
        stages["Raw Candidates"] = draw_candidate_outlines(stages["Enhanced"], raw_candidates)

        filtered_candidates = filter_candidates(raw_candidates, self._filter_config)
        stages["Validated Spots"] = draw_validated_overlay(stages["Enhanced"], filtered_candidates)

        self.finished_analysis.emit(
            {
                "stages": stages,
                "raw_candidates": raw_candidates,
                "filtered_candidates": filtered_candidates,
                "separation_applied": separation_applied,
            }
        )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1150, 850)

        self._current_image = None  # the originally loaded array (color or gray)
        self._stages: dict[str, object] = {}
        self._worker: AnalysisWorker | None = None
        self._pending_result: ImportResult | None = None

        self._viewer = ImageViewer(self)
        self._quality_panel = QualityPanel(self)
        self._results_panel = ResultsPanel(self)

        # Quality + results side by side (not stacked) per direct user
        # request, in their own splitter so each can still be resized —
        # but never collapsed to invisible (setChildrenCollapsible(False)
        # on both splitters, see below).
        self._quality_panel.setMinimumHeight(90)
        self._results_panel.setMinimumHeight(90)
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        bottom_splitter.addWidget(self._quality_panel)
        bottom_splitter.addWidget(self._results_panel)
        bottom_splitter.setChildrenCollapsible(False)
        bottom_splitter.setStretchFactor(0, 1)
        bottom_splitter.setStretchFactor(1, 1)

        main_splitter = QSplitter(Qt.Orientation.Vertical, self)
        main_splitter.addWidget(self._viewer)
        main_splitter.addWidget(bottom_splitter)
        main_splitter.setChildrenCollapsible(False)
        main_splitter.setStretchFactor(0, 5)
        main_splitter.setStretchFactor(1, 2)
        self.setCentralWidget(main_splitter)

        self._build_menu()
        self._build_toolbar()

        self._progress_bar = QProgressBar(self)
        self._progress_bar.setRange(0, 0)  # indeterminate ("busy") animation
        self._progress_bar.setMaximumWidth(160)
        self._progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self._progress_bar)

        self.statusBar().showMessage("Ready — File > Open Image to load a lab image.")

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        self._open_action = file_menu.addAction("&Open Image...")
        self._open_action.setShortcut("Ctrl+O")
        self._open_action.triggered.connect(self._on_open_image)

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

        self._fit_button = QPushButton("Fit to Window", self)
        self._fit_button.clicked.connect(self._viewer.fit_to_window)
        toolbar.addWidget(self._fit_button)

        toolbar.addSeparator()

        self._roi_button = QPushButton("ROI: Off", self)
        self._roi_button.setCheckable(True)
        self._roi_button.toggled.connect(self._on_roi_toggled)
        toolbar.addWidget(self._roi_button)

        self._clear_roi_button = QPushButton("Clear ROI", self)
        self._clear_roi_button.clicked.connect(self._viewer.clear_roi)
        toolbar.addWidget(self._clear_roi_button)

        toolbar.addSeparator()
        self._candidate_count_label = QLabel(" Raw candidates: —", self)
        toolbar.addWidget(self._candidate_count_label)

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
        if self._worker is not None and self._worker.isRunning():
            return  # Ignore Open while an analysis is already in flight.

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

        # Show the original image and quality results IMMEDIATELY — these
        # are fast (single-pass pixel statistics on one image). Only the
        # detection pipeline below is slow enough to need a worker thread.
        self._current_image = result.image
        self._pending_result = result
        self._stages = {"Original": result.image}

        self._stage_selector.blockSignals(True)
        self._stage_selector.clear()
        self._stage_selector.addItem("Original")
        self._stage_selector.blockSignals(False)

        self._viewer.set_image(result.image)
        self._quality_panel.show_result(result.quality, result.record)
        self._results_panel.clear()
        self._candidate_count_label.setText(" Raw candidates: —  |  Validated: —")

        self._set_busy(True)
        self.statusBar().showMessage(
            f"Loaded {result.loaded.filename} — running analysis, please wait..."
        )

        self._worker = AnalysisWorker(result.image, DetectionConfig(), FilterConfig(), self)
        self._worker.finished_analysis.connect(self._on_analysis_finished)
        self._worker.start()

    def _on_analysis_finished(self, data: dict) -> None:
        self._stages.update(data["stages"])

        current_stage = self._stage_selector.currentText() or "Original"
        self._stage_selector.blockSignals(True)
        self._stage_selector.clear()
        self._stage_selector.addItems(list(self._stages.keys()))
        self._stage_selector.blockSignals(False)
        self._stage_selector.setCurrentText(current_stage)
        self._on_stage_changed(self._stage_selector.currentText())

        n_validated = validated_count(data["filtered_candidates"])
        n_raw = len(data["raw_candidates"])
        self._candidate_count_label.setText(
            f" Raw candidates: {n_raw}  |  Validated: {n_validated}"
        )
        self._results_panel.show_result(data["filtered_candidates"], data["separation_applied"])

        self._set_busy(False)

        result = self._pending_result
        if result is not None:
            status = (
                "clean" if result.quality.is_clean else f"{len(result.quality.warnings)} warning(s)"
            )
            self.statusBar().showMessage(
                f"Loaded {result.loaded.filename} — "
                f"{result.loaded.width}x{result.loaded.height}, "
                f"{result.loaded.channels} channel(s) — quality: {status} — "
                f"validated: {n_validated} (raw: {n_raw})"
            )

    def _set_busy(self, busy: bool) -> None:
        self._progress_bar.setVisible(busy)
        self._open_action.setEnabled(not busy)

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
