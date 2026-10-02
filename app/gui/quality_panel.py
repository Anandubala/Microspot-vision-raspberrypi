"""Quality diagnostics display panel.

Phase 2 scope: show the real computed metrics and any warnings for the
current image. This is not the full Section 12 "Quality | Pipeline stages |
Results | Warnings" tabbed layout — that's assembled incrementally as later
phases add the data to put in each tab. For now it's a single read-only
text panel under the image viewer.
"""
from __future__ import annotations

from app.config.schemas import ImportRecord, QualityMetrics
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class QualityPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._label = QLabel("No image loaded.")
        self._label.setWordWrap(True)
        self._label.setStyleSheet("font-family: monospace; padding: 6px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

    def show_result(self, quality: QualityMetrics, record: ImportRecord) -> None:
        status = "CLEAN" if quality.is_clean else "WARNINGS: " + ", ".join(quality.warnings)
        dup_note = " (already in data/original/)" if record.already_existed else ""

        text = (
            f"Quality: {status}\n"
            f"  blur variance (higher=sharper): {quality.blur_variance:.1f}\n"
            f"  contrast std-dev:                {quality.contrast_std:.1f}\n"
            f"  illumination CV (lower=flatter): {quality.illumination_cv:.3f}\n"
            f"  clipped dark / bright fraction:  {quality.clipped_dark_fraction:.4f} / "
            f"{quality.clipped_bright_fraction:.4f}\n"
            f"SHA-256: {record.sha256}{dup_note}"
        )
        self._label.setText(text)

    def clear(self) -> None:
        self._label.setText("No image loaded.")
