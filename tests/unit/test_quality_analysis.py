import numpy as np

from app.config.schemas import QualityConfig
from app.image_engine.quality.quality_analysis import analyze_quality


def test_clean_sharp_high_contrast_image_has_no_warnings():
    # A checkerboard is sharp (high blur variance) and high-contrast,
    # flat-lit (uniform pattern -> low illumination CV), and not clipped
    # at the extremes in a way that exceeds the default 2% threshold.
    img = np.zeros((100, 100), dtype=np.uint8)
    img[::2, ::2] = 200
    img[1::2, 1::2] = 200
    # Mix in mid-tones so it isn't pure 0/255 (which would itself be "clipped").
    img[img == 0] = 60

    result = analyze_quality(img)
    assert result.warnings == []
    assert result.is_clean


def test_uniform_flat_image_triggers_blur_and_low_contrast_warnings():
    flat = np.full((80, 80), 120, dtype=np.uint8)
    result = analyze_quality(flat)

    assert "BLURRY" in result.warnings
    assert "LOW_CONTRAST" in result.warnings
    assert not result.is_clean


def test_fully_white_image_triggers_clipped_bright():
    white = np.full((50, 50), 255, dtype=np.uint8)
    result = analyze_quality(white)
    assert "CLIPPED_BRIGHT" in result.warnings


def test_fully_black_image_triggers_clipped_dark():
    black = np.zeros((50, 50), dtype=np.uint8)
    result = analyze_quality(black)
    assert "CLIPPED_DARK" in result.warnings


def test_strong_gradient_triggers_uneven_illumination():
    gradient = np.zeros((100, 100), dtype=np.uint8)
    for col in range(100):
        gradient[:, col] = int(20 + col * 2)  # 20 -> ~218 left to right

    result = analyze_quality(gradient)
    assert "UNEVEN_ILLUMINATION" in result.warnings


def test_custom_config_thresholds_are_respected():
    flat = np.full((80, 80), 120, dtype=np.uint8)

    # Loosen every threshold so the same flat image passes clean.
    lenient_config = QualityConfig(
        blur_variance_min=0.0,
        contrast_std_min=0.0,
        illumination_cv_max=1.0,
        clipping_fraction_max=1.0,
    )
    result = analyze_quality(flat, lenient_config)
    assert result.warnings == []
