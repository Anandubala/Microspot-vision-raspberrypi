import numpy as np
from PySide6.QtCore import QPointF

from app.gui.image_viewer import ImageViewer, clamp_roi, clamp_zoom_factor, numpy_to_qpixmap


# ---- numpy_to_qpixmap (unchanged from Phase 1) ----

def test_grayscale_array_converts_to_pixmap():
    image = np.zeros((50, 80), dtype=np.uint8)
    pixmap = numpy_to_qpixmap(image)
    assert not pixmap.isNull()
    assert pixmap.width() == 80
    assert pixmap.height() == 50


def test_bgr_array_converts_to_pixmap():
    image = np.zeros((50, 80, 3), dtype=np.uint8)
    pixmap = numpy_to_qpixmap(image)
    assert not pixmap.isNull()


def test_bgra_array_converts_to_pixmap():
    image = np.zeros((50, 80, 4), dtype=np.uint8)
    pixmap = numpy_to_qpixmap(image)
    assert not pixmap.isNull()


# ---- clamp_roi (pure function) ----

def test_clamp_roi_normal_drag_inside_image():
    result = clamp_roi(10, 10, 50, 40, img_w=100, img_h=100)
    assert result == (10, 10, 40, 30)


def test_clamp_roi_reversed_drag_direction_still_normalizes():
    result = clamp_roi(50, 40, 10, 10, img_w=100, img_h=100)
    assert result == (10, 10, 40, 30)


def test_clamp_roi_clips_to_image_bounds():
    result = clamp_roi(-20, -20, 50, 50, img_w=100, img_h=100)
    assert result == (0, 0, 50, 50)


def test_clamp_roi_clips_overshoot_past_image_edge():
    result = clamp_roi(80, 80, 150, 150, img_w=100, img_h=100)
    assert result == (80, 80, 20, 20)


def test_clamp_roi_zero_area_click_returns_none():
    result = clamp_roi(30, 30, 30, 30, img_w=100, img_h=100)
    assert result is None


def test_clamp_roi_entirely_outside_image_returns_none():
    result = clamp_roi(-50, -50, -10, -10, img_w=100, img_h=100)
    assert result is None


# ---- clamp_zoom_factor (pure function) ----

def test_clamp_zoom_factor_zooms_in():
    assert clamp_zoom_factor(1.0, 1.15, min_zoom=0.1, max_zoom=20.0) == 1.15


def test_clamp_zoom_factor_respects_max():
    result = clamp_zoom_factor(19.0, 1.15, min_zoom=0.1, max_zoom=20.0)
    assert result == 20.0


def test_clamp_zoom_factor_respects_min():
    result = clamp_zoom_factor(0.11, 1 / 1.15, min_zoom=0.1, max_zoom=20.0)
    assert result == 0.1


# ---- ImageViewer widget behavior ----

def test_set_image_populates_pixmap_item(qapp_session):
    viewer = ImageViewer()
    viewer.resize(400, 300)
    image = np.zeros((50, 80), dtype=np.uint8)
    viewer.set_image(image)

    assert viewer._pixmap_item is not None
    assert viewer._image_size == (80, 50)


def test_clear_removes_pixmap_item(qapp_session):
    viewer = ImageViewer()
    viewer.set_image(np.zeros((50, 80), dtype=np.uint8))
    viewer.clear()
    assert viewer._pixmap_item is None
    assert viewer.get_roi() is None


def test_roi_lifecycle_via_internal_handlers(qapp_session):
    """Drives the same scene-coordinate ROI handlers that mouse events
    call, without depending on the view's pixel->scene transform (which
    varies with window size under the offscreen platform). This still
    exercises the real clamping/signal/state logic end to end.
    """
    viewer = ImageViewer()
    viewer.resize(400, 300)
    viewer.set_image(np.zeros((100, 100), dtype=np.uint8))
    viewer.set_roi_mode(True)

    received = []
    viewer.roi_changed.connect(lambda roi: received.append(roi))

    start = QPointF(10, 10)
    viewer._start_roi_item(start)
    viewer._update_roi_item(start, QPointF(60, 50))
    viewer._finish_roi(start, QPointF(60, 50))

    assert viewer.get_roi() == (10, 10, 50, 40)
    assert received == [(10, 10, 50, 40)]

    viewer.clear_roi()
    assert viewer.get_roi() is None
    assert received[-1] is None


def test_roi_mode_toggle_changes_drag_mode(qapp_session):
    from PySide6.QtWidgets import QGraphicsView

    viewer = ImageViewer()
    assert viewer.dragMode() == QGraphicsView.DragMode.ScrollHandDrag

    viewer.set_roi_mode(True)
    assert viewer.dragMode() == QGraphicsView.DragMode.NoDrag

    viewer.set_roi_mode(False)
    assert viewer.dragMode() == QGraphicsView.DragMode.ScrollHandDrag
