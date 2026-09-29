import numpy as np

from app.gui.image_viewer import numpy_to_qpixmap


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
    assert pixmap.width() == 80
    assert pixmap.height() == 50


def test_bgra_array_converts_to_pixmap():
    image = np.zeros((50, 80, 4), dtype=np.uint8)
    pixmap = numpy_to_qpixmap(image)
    assert not pixmap.isNull()
    assert pixmap.width() == 80
    assert pixmap.height() == 50
