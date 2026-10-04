import numpy as np
import pytest

from app.config.schemas import DetectionConfig, DetectionPolarity, SegmentationMethod
from app.image_engine.segmentation.thresholding import compute_mask, determine_polarity


# ---- determine_polarity ----

def test_bright_image_resolves_to_dark_on_light():
    bright = np.full((50, 50), 200, dtype=np.uint8)
    assert determine_polarity(bright, DetectionPolarity.AUTO) == DetectionPolarity.DARK_ON_LIGHT


def test_dark_image_resolves_to_bright_on_dark():
    dark = np.full((50, 50), 40, dtype=np.uint8)
    assert determine_polarity(dark, DetectionPolarity.AUTO) == DetectionPolarity.BRIGHT_ON_DARK


def test_explicit_polarity_passes_through_unchanged():
    bright = np.full((50, 50), 200, dtype=np.uint8)
    # Even though the image is bright, an explicit BRIGHT_ON_DARK must not
    # be overridden by the AUTO heuristic.
    assert (
        determine_polarity(bright, DetectionPolarity.BRIGHT_ON_DARK)
        == DetectionPolarity.BRIGHT_ON_DARK
    )


# ---- compute_mask ----

def _dark_spot_on_light_background():
    img = np.full((100, 100), 200, dtype=np.uint8)
    img[40:60, 40:60] = 30  # a clear dark square
    return img


def _bright_spot_on_dark_background():
    img = np.full((100, 100), 30, dtype=np.uint8)
    img[40:60, 40:60] = 220
    return img


def test_otsu_dark_on_light_marks_spot_as_foreground():
    img = _dark_spot_on_light_background()
    config = DetectionConfig(segmentation_method=SegmentationMethod.OTSU)
    mask = compute_mask(img, config, DetectionPolarity.DARK_ON_LIGHT)

    assert mask[50, 50] == 255  # center of the dark spot is foreground
    assert mask[5, 5] == 0  # background corner is not


def test_otsu_bright_on_dark_marks_spot_as_foreground():
    img = _bright_spot_on_dark_background()
    config = DetectionConfig(segmentation_method=SegmentationMethod.OTSU)
    mask = compute_mask(img, config, DetectionPolarity.BRIGHT_ON_DARK)

    assert mask[50, 50] == 255
    assert mask[5, 5] == 0


def test_adaptive_mean_marks_spot_as_foreground():
    img = _dark_spot_on_light_background()
    config = DetectionConfig(
        segmentation_method=SegmentationMethod.ADAPTIVE_MEAN,
        adaptive_block_size=31,
        adaptive_c=5,
    )
    mask = compute_mask(img, config, DetectionPolarity.DARK_ON_LIGHT)
    assert mask[50, 50] == 255


def test_adaptive_gaussian_marks_spot_as_foreground():
    img = _dark_spot_on_light_background()
    config = DetectionConfig(
        segmentation_method=SegmentationMethod.ADAPTIVE_GAUSSIAN,
        adaptive_block_size=31,
        adaptive_c=5,
    )
    mask = compute_mask(img, config, DetectionPolarity.DARK_ON_LIGHT)
    assert mask[50, 50] == 255


def test_compute_mask_rejects_auto_polarity():
    img = _dark_spot_on_light_background()
    config = DetectionConfig()
    with pytest.raises(ValueError):
        compute_mask(img, config, DetectionPolarity.AUTO)


def test_mask_output_is_binary_0_or_255():
    img = _dark_spot_on_light_background()
    config = DetectionConfig()
    mask = compute_mask(img, config, DetectionPolarity.DARK_ON_LIGHT)
    unique_values = set(np.unique(mask).tolist())
    assert unique_values <= {0, 255}


# ---- flat-image regression (real bug found via integration testing) ----
#
# A perfectly flat BRIGHT_ON_DARK image used to come back as one giant
# false-positive candidate covering the whole frame: Otsu's threshold
# degenerates to 0 on a flat histogram, and non-inverted thresholding then
# marks every pixel > 0 as foreground. Fixed in compute_mask() by
# short-circuiting flat input to an empty mask. See docs/PHASE_4.md.

def test_flat_bright_on_dark_image_returns_empty_mask_not_full_frame():
    flat = np.full((300, 300), 30, dtype=np.uint8)
    config = DetectionConfig(segmentation_method=SegmentationMethod.OTSU)
    mask = compute_mask(flat, config, DetectionPolarity.BRIGHT_ON_DARK)
    assert np.count_nonzero(mask) == 0


def test_flat_dark_on_light_image_returns_empty_mask():
    flat = np.full((300, 300), 210, dtype=np.uint8)
    config = DetectionConfig(segmentation_method=SegmentationMethod.OTSU)
    mask = compute_mask(flat, config, DetectionPolarity.DARK_ON_LIGHT)
    assert np.count_nonzero(mask) == 0
