import numpy as np

from app.config.schemas import DetectionConfig, FilterConfig
from app.image_engine.detection.candidate_extraction import extract_candidates
from app.image_engine.filtering.filters import (
    AREA_TOO_LARGE,
    AREA_TOO_SMALL,
    DIAMETER_TOO_LARGE,
    DIAMETER_TOO_SMALL,
    EDGE_EXCLUDED,
    HIGH_ASPECT_RATIO,
    LOW_CIRCULARITY,
    LOW_LOCAL_CONTRAST,
    LOW_SOLIDITY,
    filter_candidates,
    validated_count,
)


def _candidate_from_blob(mask_slice, shape=(100, 100), bg=200, fg=40):
    mask = np.zeros(shape, dtype=np.uint8)
    gray = np.full(shape, bg, dtype=np.uint8)
    y0, y1, x0, x1 = mask_slice
    mask[y0:y1, x0:x1] = 255
    gray[y0:y1, x0:x1] = fg
    return extract_candidates(mask, gray)[0]


def test_default_config_accepts_a_clean_round_high_contrast_spot():
    c = _candidate_from_blob((40, 60, 40, 60))  # 20x20 square, high contrast
    result = filter_candidates([c], FilterConfig())[0]
    assert result.is_validated
    assert result.rejection_reason is None


def test_area_too_small_rejection():
    c = _candidate_from_blob((10, 12, 10, 12))  # tiny speck
    result = filter_candidates([c], FilterConfig(min_area_px=50.0))[0]
    assert result.rejection_reason == AREA_TOO_SMALL


def test_area_too_large_rejection():
    c = _candidate_from_blob((10, 90, 10, 90))  # large 80x80 blob
    result = filter_candidates([c], FilterConfig(max_area_px=100.0))[0]
    assert result.rejection_reason == AREA_TOO_LARGE


def test_diameter_too_small_rejection():
    c = _candidate_from_blob((40, 44, 40, 44))  # tiny 4x4 blob, small diameter
    config = FilterConfig(min_area_px=0.0, min_diameter_px=10.0)
    result = filter_candidates([c], config)[0]
    assert result.rejection_reason == DIAMETER_TOO_SMALL


def test_diameter_too_large_rejection():
    c = _candidate_from_blob((10, 90, 10, 90))  # large 80x80 blob
    config = FilterConfig(max_diameter_px=20.0)
    result = filter_candidates([c], config)[0]
    assert result.rejection_reason == DIAMETER_TOO_LARGE


def test_diameter_filters_disabled_by_default():
    c = _candidate_from_blob((40, 44, 40, 44))  # tiny blob
    # Default FilterConfig has min_diameter_px=None — must not reject on
    # diameter even though this blob is small, since diameter checks are
    # opt-in. (It may still be rejected by area/other rules — that's fine,
    # this test only asserts diameter isn't the active gate.)
    result = filter_candidates([c], FilterConfig(min_area_px=0.0))[0]
    assert result.rejection_reason != DIAMETER_TOO_SMALL


def test_low_circularity_rejection_for_elongated_shape():
    c = _candidate_from_blob((45, 55, 10, 90))  # 80x10 bar — low circularity
    result = filter_candidates([c], FilterConfig(min_circularity=0.9))[0]
    assert result.rejection_reason in (LOW_CIRCULARITY, HIGH_ASPECT_RATIO)
    # Specifically, with a lenient aspect-ratio limit, circularity should
    # be the one that catches it:
    lenient_aspect = FilterConfig(min_circularity=0.9, max_aspect_ratio=100.0)
    result2 = filter_candidates([c], lenient_aspect)[0]
    assert result2.rejection_reason == LOW_CIRCULARITY


def test_high_aspect_ratio_rejection():
    c = _candidate_from_blob((45, 55, 10, 90))  # 80x10 bar, aspect ratio 8.0
    # Loosen circularity so aspect ratio is the deciding rule.
    config = FilterConfig(min_circularity=0.0, max_aspect_ratio=2.0)
    result = filter_candidates([c], config)[0]
    assert result.rejection_reason == HIGH_ASPECT_RATIO


def test_low_solidity_rejection_for_concave_shape():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[20:80, 20:80] = 255
    mask[35:65, 50:80] = 0  # bite taken out — concave
    gray = np.full((100, 100), 40, dtype=np.uint8)
    gray[mask == 0] = 200
    c = extract_candidates(mask, gray)[0]

    config = FilterConfig(min_circularity=0.0, min_solidity=0.95)
    result = filter_candidates([c], config)[0]
    assert result.rejection_reason == LOW_SOLIDITY


def test_low_local_contrast_rejection():
    c = _candidate_from_blob((40, 60, 40, 60), bg=150, fg=145)  # barely different
    config = FilterConfig(min_local_contrast=20.0)
    result = filter_candidates([c], config)[0]
    assert result.rejection_reason == LOW_LOCAL_CONTRAST


def test_edge_excluded_rejection_when_enabled():
    c = _candidate_from_blob((0, 20, 0, 20))  # touches top-left border
    config = FilterConfig(exclude_edge_candidates=True)
    result = filter_candidates([c], config)[0]
    assert result.rejection_reason == EDGE_EXCLUDED


def test_edge_candidate_not_rejected_when_disabled():
    c = _candidate_from_blob((0, 20, 0, 20))
    config = FilterConfig(exclude_edge_candidates=False)
    result = filter_candidates([c], config)[0]
    # Should pass through to the other rules rather than being auto-rejected.
    assert result.rejection_reason != EDGE_EXCLUDED


def test_filter_candidates_does_not_mutate_input():
    c = _candidate_from_blob((10, 12, 10, 12))
    original = c.model_copy()
    filter_candidates([c], FilterConfig(min_area_px=50.0))
    assert c.rejection_reason == original.rejection_reason  # unchanged (still None)


def test_validated_count_counts_only_passing_candidates():
    good = _candidate_from_blob((40, 60, 40, 60))
    bad = _candidate_from_blob((10, 12, 10, 12), shape=(100, 100))
    filtered = filter_candidates([good, bad], FilterConfig(min_area_px=50.0))
    assert validated_count(filtered) == 1


def test_validated_count_of_empty_list_is_zero():
    assert validated_count([]) == 0
