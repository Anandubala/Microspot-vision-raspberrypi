import numpy as np

from app.config.schemas import FilterConfig
from app.image_engine.detection.candidate_extraction import extract_candidates
from app.image_engine.filtering.filters import filter_candidates
from app.image_engine.visualization.overlays import (
    draw_candidate_outlines,
    draw_validated_overlay,
)


def test_draw_candidate_outlines_returns_bgr_same_size():
    gray = np.full((100, 100), 200, dtype=np.uint8)
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[40:60, 40:60] = 255
    candidates = extract_candidates(mask, gray)

    result = draw_candidate_outlines(gray, candidates)
    assert result.shape == (100, 100, 3)
    assert result.dtype == np.uint8


def test_draw_candidate_outlines_with_no_candidates_returns_plain_bgr():
    gray = np.full((50, 50), 128, dtype=np.uint8)
    result = draw_candidate_outlines(gray, [])
    assert result.shape == (50, 50, 3)
    # Should just be the grayscale image converted to BGR, unchanged.
    assert np.all(result[:, :, 0] == 128)


# ---- draw_validated_overlay (Phase 5) ----

def test_validated_overlay_returns_bgr_same_size():
    gray = np.full((100, 100), 200, dtype=np.uint8)
    gray[40:60, 40:60] = 40
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[40:60, 40:60] = 255

    candidates = extract_candidates(mask, gray)
    filtered = filter_candidates(candidates, FilterConfig())

    result = draw_validated_overlay(gray, filtered)
    assert result.shape == (100, 100, 3)
    assert result.dtype == np.uint8


def test_validated_candidate_gets_green_outline_pixels():
    gray = np.full((100, 100), 200, dtype=np.uint8)
    gray[40:60, 40:60] = 40
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[40:60, 40:60] = 255

    candidates = extract_candidates(mask, gray)
    filtered = filter_candidates(candidates, FilterConfig(min_area_px=1.0))
    assert filtered[0].is_validated  # sanity check on the fixture

    result = draw_validated_overlay(gray, filtered)
    # BGR green = (0, 255, 0) should appear somewhere (the outline).
    green_pixels = np.all(result == (0, 255, 0), axis=-1)
    assert green_pixels.any()


def test_rejected_candidate_gets_orange_outline_not_green():
    gray = np.full((100, 100), 200, dtype=np.uint8)
    gray[10:12, 10:12] = 190  # tiny, low-contrast speck — should be rejected
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[10:12, 10:12] = 255

    candidates = extract_candidates(mask, gray)
    # Strict config guarantees this tiny speck is rejected on area alone.
    filtered = filter_candidates(candidates, FilterConfig(min_area_px=50.0))
    assert not filtered[0].is_validated

    result = draw_validated_overlay(gray, filtered)
    green_pixels = np.all(result == (0, 255, 0), axis=-1)
    orange_pixels = np.all(result == (0, 140, 255), axis=-1)
    assert not green_pixels.any()
    assert orange_pixels.any()


def test_validated_overlay_with_no_candidates_returns_plain_bgr():
    gray = np.full((50, 50), 128, dtype=np.uint8)
    result = draw_validated_overlay(gray, [])
    assert result.shape == (50, 50, 3)
    assert np.all(result[:, :, 0] == 128)
