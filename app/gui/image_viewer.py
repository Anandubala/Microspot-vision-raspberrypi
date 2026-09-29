"""Basic image display widget.

Phase 1 scope: show a loaded image, scaled to fit the viewport. Zoom, pan,
ROI selection, and multi-stage overlay switching (grayscale, normalized,
segmentation mask, etc.) are Phase 3 — not implemented here.
"""
from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget


def numpy_to_qpixmap(image: np.ndarray) -> QPixmap:
    """Convert a BGR/BGRA/grayscale OpenCV array (as returned by
    FileImportSource) into a QPixmap for display.
    """
    if image.ndim == 2:
        # Grayscale
        height, width = image.shape
        bytes_per_line = width
        qimage = QImage(
            image.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8
        )
    elif image.shape[2] == 3:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width, _ = rgb.shape
        bytes_per_line = 3 * width
        qimage = QImage(
            rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888
        )
    elif image.shape[2] == 4:
        rgba = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
        height, width, _ = rgba.shape
        bytes_per_line = 4 * width
        qimage = QImage(
            rgba.data, width, height, bytes_per_line, QImage.Format.Format_RGBA8888
        )
    else:
        raise ValueError(f"Unsupported channel count: {image.shape[2]}")

    # .copy() detaches from the numpy buffer so Qt owns its own memory.
    return QPixmap.fromImage(qimage.copy())


class ImageViewer(QWidget):
    """Displays a single image, scaled to fit the available space."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._label = QLabel("No image loaded")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._label.setMinimumSize(1, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

        self._source_pixmap: QPixmap | None = None

    def set_image(self, image: np.ndarray) -> None:
        self._source_pixmap = numpy_to_qpixmap(image)
        self._rescale()

    def clear(self) -> None:
        self._source_pixmap = None
        self._label.setText("No image loaded")
        self._label.setPixmap(QPixmap())

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override signature)
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self) -> None:
        if self._source_pixmap is None:
            return
        scaled = self._source_pixmap.scaled(
            self._label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._label.setPixmap(scaled)
