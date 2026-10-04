"""End-to-end detection tests against synthetic images with a KNOWN dot
count — the same idea as spec Section 9.1's controlled validation dataset,
scaled down to a fast, deterministic unit-test fixture. This is engineering
validation only, never biological validation (Section 9.1/9.3).
"""
import cv2
import numpy as np
import pytest

from app.config.schemas import DetectionConfig, DetectionPolarity, SegmentationMethod
from app.image_engine.detection.classical_cv import ClassicalCVDetector, segment_and_extract
from app.image_engine.detection.onnx_detector import ONNXDetector


def _known_dot_image(n_dots: int, polarity: DetectionPolarity) -> np.ndarray:
    """Build an image with exactly `n_dots` well-separated circular dots,
    for either polarity, on a 300x300 canvas.
    """
    background_value = 210 if polarity == DetectionPolarity.DARK_ON_LIGHT else 30
    dot_value = 30 if polarity == DetectionPolarity.DARK_ON_LIGHT else 220

    img = np.full((300, 300), background_value, dtype=np.uint8)
    rng = np.random.default_rng(7)
    placed = 0
    attempts = 0
    centers: list[tuple[int, int]] = []
    while placed < n_dots and attempts < 1000:
        attempts += 1
        cx, cy = rng.integers(25, 275), rng.integers(25, 275)
        if all((cx - ex) ** 2 + (cy - ey) ** 2 > 35**2 for ex, ey in centers):
            cv2.circle(img, (int(cx), int(cy)), 10, int(dot_value), -1)
            centers.append((cx, cy))
            placed += 1
    assert placed == n_dots, "test fixture failed to place all dots — increase canvas/spacing"
    return img


@pytest.mark.parametrize("n_dots", [0, 1, 5, 12])
def test_classical_cv_detector_finds_exact_known_dot_count_dark_on_light(n_dots):
    img = _known_dot_image(n_dots, DetectionPolarity.DARK_ON_LIGHT)
    config = DetectionConfig(polarity=DetectionPolarity.DARK_ON_LIGHT)

    detector = ClassicalCVDetector()
    candidates = detector.detect(img, config)

    assert len(candidates) == n_dots


@pytest.mark.parametrize("n_dots", [0, 1, 5, 12])
def test_classical_cv_detector_finds_exact_known_dot_count_bright_on_dark(n_dots):
    img = _known_dot_image(n_dots, DetectionPolarity.BRIGHT_ON_DARK)
    config = DetectionConfig(polarity=DetectionPolarity.BRIGHT_ON_DARK)

    detector = ClassicalCVDetector()
    candidates = detector.detect(img, config)

    assert len(candidates) == n_dots


def test_auto_polarity_also_finds_correct_count():
    img = _known_dot_image(8, DetectionPolarity.DARK_ON_LIGHT)
    config = DetectionConfig(polarity=DetectionPolarity.AUTO)

    candidates = ClassicalCVDetector().detect(img, config)
    assert len(candidates) == 8


def test_segment_and_extract_returns_mask_matching_candidates():
    img = _known_dot_image(4, DetectionPolarity.DARK_ON_LIGHT)
    config = DetectionConfig(polarity=DetectionPolarity.DARK_ON_LIGHT)

    mask, candidates = segment_and_extract(img, config)
    assert mask.shape == img.shape
    assert len(candidates) == 4
    # Every candidate's centroid should actually land on foreground mask pixels.
    for c in candidates:
        assert mask[int(c.centroid_y), int(c.centroid_x)] == 255


def test_adaptive_method_also_finds_known_dots():
    img = _known_dot_image(6, DetectionPolarity.DARK_ON_LIGHT)
    config = DetectionConfig(
        polarity=DetectionPolarity.DARK_ON_LIGHT,
        segmentation_method=SegmentationMethod.ADAPTIVE_GAUSSIAN,
        adaptive_block_size=51,
        adaptive_c=10,
    )
    candidates = ClassicalCVDetector().detect(img, config)
    assert len(candidates) == 6


def test_onnx_detector_raises_not_implemented():
    img = np.zeros((50, 50), dtype=np.uint8)
    with pytest.raises(NotImplementedError):
        ONNXDetector().detect(img, DetectionConfig())
