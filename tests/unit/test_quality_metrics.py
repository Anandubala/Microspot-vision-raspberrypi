import cv2
import numpy as np

from app.image_engine.quality.metrics import (
    blur_variance,
    clipping_fractions,
    contrast_std,
    illumination_cv,
    to_grayscale,
)


# ---- to_grayscale ----

def test_to_grayscale_passthrough_for_2d():
    gray = np.full((10, 10), 128, dtype=np.uint8)
    assert np.array_equal(to_grayscale(gray), gray)


def test_to_grayscale_converts_bgr():
    bgr = np.zeros((10, 10, 3), dtype=np.uint8)
    bgr[:, :, 2] = 255  # pure red in BGR
    gray = to_grayscale(bgr)
    assert gray.shape == (10, 10)
    assert gray.dtype == np.uint8


# ---- blur_variance ----

def test_sharp_checkerboard_has_higher_variance_than_blurred():
    checkerboard = np.zeros((100, 100), dtype=np.uint8)
    checkerboard[::2, ::2] = 255
    checkerboard[1::2, 1::2] = 255

    sharp_var = blur_variance(checkerboard)
    blurred = cv2.GaussianBlur(checkerboard, (15, 15), 0)
    blurred_var = blur_variance(blurred)

    assert sharp_var > blurred_var


def test_uniform_image_has_zero_blur_variance():
    flat = np.full((50, 50), 100, dtype=np.uint8)
    assert blur_variance(flat) == 0.0


# ---- contrast_std ----

def test_uniform_image_has_zero_contrast():
    flat = np.full((50, 50), 100, dtype=np.uint8)
    assert contrast_std(flat) == 0.0


def test_half_black_half_white_has_known_std():
    img = np.zeros((10, 10), dtype=np.uint8)
    img[:, 5:] = 255
    # Exact population std of 50 zeros and 50 255s:
    expected = float(np.std(np.array([0] * 50 + [255] * 50, dtype=np.float64)))
    assert abs(contrast_std(img) - expected) < 1e-6


def test_higher_contrast_scores_higher_than_lower_contrast():
    low_contrast = np.full((50, 50), 120, dtype=np.uint8)
    low_contrast[:, :25] = 130  # small difference
    high_contrast = np.zeros((50, 50), dtype=np.uint8)
    high_contrast[:, :25] = 255  # large difference

    assert contrast_std(high_contrast) > contrast_std(low_contrast)


# ---- illumination_cv ----

def test_flat_image_has_near_zero_illumination_cv():
    flat = np.full((100, 100), 150, dtype=np.uint8)
    assert illumination_cv(flat, grid_size=4) < 1e-6


def test_gradient_image_has_higher_cv_than_flat_image():
    flat = np.full((100, 100), 150, dtype=np.uint8)

    gradient = np.zeros((100, 100), dtype=np.uint8)
    for col in range(100):
        gradient[:, col] = int(50 + col * 2)  # left dark, right bright

    assert illumination_cv(gradient, grid_size=4) > illumination_cv(flat, grid_size=4)


def test_black_image_returns_zero_not_divide_by_zero_error():
    black = np.zeros((40, 40), dtype=np.uint8)
    assert illumination_cv(black, grid_size=4) == 0.0


# ---- clipping_fractions ----

def test_clipping_fractions_exact_known_counts():
    img = np.full((10, 10), 128, dtype=np.uint8)  # 100 pixels, none clipped
    img[0, :5] = 0  # 5 pixels at 0
    img[1, :3] = 255  # 3 pixels at 255

    dark_fraction, bright_fraction = clipping_fractions(img)
    assert abs(dark_fraction - 5 / 100) < 1e-9
    assert abs(bright_fraction - 3 / 100) < 1e-9


def test_no_clipping_returns_zero_zero():
    img = np.full((10, 10), 128, dtype=np.uint8)
    dark_fraction, bright_fraction = clipping_fractions(img)
    assert dark_fraction == 0.0
    assert bright_fraction == 0.0


def test_fully_saturated_image_returns_one_one_component():
    all_white = np.full((10, 10), 255, dtype=np.uint8)
    dark_fraction, bright_fraction = clipping_fractions(all_white)
    assert dark_fraction == 0.0
    assert bright_fraction == 1.0
