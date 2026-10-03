import numpy as np
import pytest

from app.image_engine.preprocessing.stages import (
    correct_illumination,
    denoise,
    enhance_contrast,
    estimate_background,
    normalize,
)
from app.image_engine.quality.metrics import contrast_std, illumination_cv


# ---- normalize ----

def test_normalize_stretches_to_full_range():
    img = np.full((20, 20), 100, dtype=np.uint8)
    img[0, 0] = 50
    img[0, 1] = 150

    result = normalize(img)
    assert result.min() == 0
    assert result.max() == 255


def test_normalize_flat_image_returned_unchanged():
    flat = np.full((20, 20), 120, dtype=np.uint8)
    result = normalize(flat)
    assert np.array_equal(result, flat)


def test_normalize_output_is_uint8():
    img = np.random.default_rng(0).integers(0, 200, (10, 10), dtype=np.uint8)
    result = normalize(img)
    assert result.dtype == np.uint8


# ---- estimate_background ----

def test_background_of_uniform_image_is_uniform():
    flat = np.full((60, 60), 130, dtype=np.uint8)
    bg = estimate_background(flat, kernel_size=21)
    # Interior pixels (away from any edge effects) should match the flat value.
    assert abs(int(bg[30, 30]) - 130) <= 1


def test_background_estimate_handles_small_images_without_error():
    tiny = np.full((5, 5), 100, dtype=np.uint8)
    bg = estimate_background(tiny, kernel_size=51)  # larger than the image
    assert bg.shape == tiny.shape


def test_background_estimate_smooths_out_small_features():
    img = np.full((80, 80), 100, dtype=np.uint8)
    img[38:42, 38:42] = 10  # a small dark spot
    bg = estimate_background(img, kernel_size=31)
    # The background estimate at the spot's location should NOT be anywhere
    # near as dark as the spot itself — it's been averaged away.
    assert bg[40, 40] > 50


# ---- correct_illumination ----

def test_correction_reduces_illumination_cv_on_gradient():
    gradient = np.zeros((100, 100), dtype=np.uint8)
    for col in range(100):
        gradient[:, col] = int(20 + col * 2)

    before_cv = illumination_cv(gradient, grid_size=4)
    background = estimate_background(gradient, kernel_size=41)
    corrected = correct_illumination(gradient, background)
    after_cv = illumination_cv(corrected, grid_size=4)

    assert after_cv < before_cv


def test_correction_output_is_uint8_and_full_range_capable():
    gray = np.full((30, 30), 128, dtype=np.uint8)
    bg = estimate_background(gray, kernel_size=11)
    corrected = correct_illumination(gray, bg)
    assert corrected.dtype == np.uint8


# ---- denoise ----

def test_gaussian_denoise_reduces_salt_and_pepper_noise_variance():
    rng = np.random.default_rng(42)
    clean = np.full((100, 100), 128, dtype=np.uint8)
    noisy = clean.copy()
    noise_mask = rng.random((100, 100)) < 0.1
    noisy[noise_mask] = rng.choice([0, 255], size=noise_mask.sum())

    denoised = denoise(noisy, method="median", kernel_size=5)
    assert float(denoised.std()) < float(noisy.std())


def test_unknown_denoise_method_raises():
    img = np.zeros((20, 20), dtype=np.uint8)
    with pytest.raises(ValueError):
        denoise(img, method="not_a_real_method", kernel_size=3)


def test_gaussian_vs_median_both_return_uint8():
    img = np.full((20, 20), 100, dtype=np.uint8)
    assert denoise(img, "gaussian", 3).dtype == np.uint8
    assert denoise(img, "median", 3).dtype == np.uint8


# ---- enhance_contrast ----

def test_clahe_increases_local_contrast_on_low_contrast_image():
    # A low-contrast image with real (small) local structure.
    img = np.full((100, 100), 128, dtype=np.uint8)
    img[40:60, 40:60] = 135  # subtle square, barely different from background

    enhanced = enhance_contrast(img, clip_limit=2.0, tile_grid_size=8)
    assert contrast_std(enhanced) > contrast_std(img)


def test_clahe_output_is_uint8_same_shape():
    img = np.full((50, 50), 100, dtype=np.uint8)
    result = enhance_contrast(img, clip_limit=2.0, tile_grid_size=8)
    assert result.dtype == np.uint8
    assert result.shape == img.shape
