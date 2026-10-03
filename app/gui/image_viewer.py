"""Image display widget with zoom, pan, and rectangular ROI selection
(spec Section 10: "ROI: rectangular first; architecture extensible to
polygon/multi-ROI later", Section 16 Phase 3: "Image viewer (zoom/pan/ROI)").

Built on QGraphicsView/QGraphicsScene rather than a plain QLabel (Phase 1)
so zoom and pan are real, interactive, and don't require re-scaling the
source pixmap by hand.
"""
from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QWidget,
)


def numpy_to_qpixmap(image: np.ndarray) -> QPixmap:
    """Convert a BGR/BGRA/grayscale OpenCV array into a QPixmap."""
    if image.ndim == 2:
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

    return QPixmap.fromImage(qimage.copy())


def clamp_roi(
    x0: float, y0: float, x1: float, y1: float, img_w: int, img_h: int
) -> tuple[int, int, int, int] | None:
    """Normalize two corner points into an (x, y, w, h) integer rect,
    clamped to [0, img_w] x [0, img_h]. Returns None if the clamped
    result has zero area (e.g. a click with no drag, or a drag that
    started/ended entirely outside the image).

    Pure function, no Qt dependency — independently testable.
    """
    left, right = sorted((x0, x1))
    top, bottom = sorted((y0, y1))

    left = max(0.0, min(left, img_w))
    right = max(0.0, min(right, img_w))
    top = max(0.0, min(top, img_h))
    bottom = max(0.0, min(bottom, img_h))

    x, y = int(round(left)), int(round(top))
    w, h = int(round(right - left)), int(round(bottom - top))

    if w <= 0 or h <= 0:
        return None
    return (x, y, w, h)


def clamp_zoom_factor(current: float, delta: float, min_zoom: float, max_zoom: float) -> float:
    """Compute the next cumulative zoom factor given a multiplicative
    `delta` (e.g. 1.15 to zoom in, 1/1.15 to zoom out), clamped to
    [min_zoom, max_zoom]. Pure function, independently testable.
    """
    proposed = current * delta
    return max(min_zoom, min(proposed, max_zoom))


class ImageViewer(QGraphicsView):
    """Displays one image with wheel-zoom, drag-to-pan, and an optional
    rectangular ROI selection tool.
    """

    roi_changed = Signal(object)  # emits (x, y, w, h) tuple, or None when cleared

    _ZOOM_STEP = 1.15
    _MIN_ZOOM = 0.1
    _MAX_ZOOM = 20.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._image_size: tuple[int, int] = (0, 0)  # (width, height)
        self._zoom_factor: float = 1.0

        self._roi_mode: bool = False
        self._roi_item: QGraphicsRectItem | None = None
        self._roi_start: QPointF | None = None
        self._roi: tuple[int, int, int, int] | None = None

    # ---- public API ----

    def set_image(self, image: np.ndarray) -> None:
        pixmap = numpy_to_qpixmap(image)
        self._image_size = (pixmap.width(), pixmap.height())

        if self._pixmap_item is None:
            self._pixmap_item = self._scene.addPixmap(pixmap)
        else:
            self._pixmap_item.setPixmap(pixmap)

        self._scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        self.fit_to_window()

    def clear(self) -> None:
        self._scene.clear()
        self._pixmap_item = None
        self._image_size = (0, 0)
        self._clear_roi_item()

    def fit_to_window(self) -> None:
        if self._pixmap_item is None:
            return
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom_factor = 1.0

    def set_roi_mode(self, enabled: bool) -> None:
        self._roi_mode = enabled
        self.setDragMode(
            QGraphicsView.DragMode.NoDrag if enabled else QGraphicsView.DragMode.ScrollHandDrag
        )

    def get_roi(self) -> tuple[int, int, int, int] | None:
        return self._roi

    def clear_roi(self) -> None:
        self._roi = None
        self._clear_roi_item()
        self.roi_changed.emit(None)

    # ---- zoom (wheel) ----

    def wheelEvent(self, event) -> None:  # noqa: N802
        if self._pixmap_item is None:
            return
        delta = self._ZOOM_STEP if event.angleDelta().y() > 0 else 1 / self._ZOOM_STEP
        new_zoom = clamp_zoom_factor(self._zoom_factor, delta, self._MIN_ZOOM, self._MAX_ZOOM)
        applied = new_zoom / self._zoom_factor
        self.scale(applied, applied)
        self._zoom_factor = new_zoom

    # ---- ROI (mouse drag, only while roi_mode is on) ----

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._roi_mode and self._pixmap_item is not None and event.button() == Qt.MouseButton.LeftButton:
            self._roi_start = self.mapToScene(event.pos())
            self._start_roi_item(self._roi_start)
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._roi_mode and self._roi_start is not None:
            current = self.mapToScene(event.pos())
            self._update_roi_item(self._roi_start, current)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._roi_mode and self._roi_start is not None:
            end = self.mapToScene(event.pos())
            self._finish_roi(self._roi_start, end)
            self._roi_start = None
            return
        super().mouseReleaseEvent(event)

    # ---- ROI helpers (scene-coordinate based, independently callable for tests) ----

    def _start_roi_item(self, scene_pos: QPointF) -> None:
        self._clear_roi_item()
        self._roi_item = QGraphicsRectItem(QRectF(scene_pos, scene_pos))
        pen = QPen(QColor(255, 60, 60), 1.5, Qt.PenStyle.DashLine)
        self._roi_item.setPen(pen)
        self._scene.addItem(self._roi_item)

    def _update_roi_item(self, start: QPointF, current: QPointF) -> None:
        if self._roi_item is not None:
            self._roi_item.setRect(QRectF(start, current).normalized())

    def _finish_roi(self, start: QPointF, end: QPointF) -> None:
        img_w, img_h = self._image_size
        result = clamp_roi(start.x(), start.y(), end.x(), end.y(), img_w, img_h)
        self._roi = result
        if result is None:
            self._clear_roi_item()
        else:
            x, y, w, h = result
            if self._roi_item is not None:
                self._roi_item.setRect(QRectF(x, y, w, h))
        self.roi_changed.emit(result)

    def _clear_roi_item(self) -> None:
        if self._roi_item is not None:
            self._scene.removeItem(self._roi_item)
            self._roi_item = None
