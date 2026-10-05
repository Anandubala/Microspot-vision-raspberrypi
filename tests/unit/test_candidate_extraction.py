import cv2
import numpy as np
import pytest

from app.config.schemas import DetectionConfig, EdgeState
from app.image_engine.detection.candidate_extraction import extract_candidates


def _gray_with_value(shape, value=150):
    return np.full(shape, value, dtype=np.uint8)


def test_single_square_blob_detected_with_correct_geometry():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[30:50, 40:60] = 255  # a 20x20 square at (40, 30)
    gray = _gray_with_value((100, 100))

    candidates = extract_candidates(mask, gray)
    assert len(candidates) == 1

    c = candidates[0]
    assert c.bbox_x == 40
    assert c.bbox_y == 30
    assert c.bbox_w == 20
    assert c.bbox_h == 20
    # cv2.contourArea computes the shoelace-formula area of the boundary
    # polygon's corner coordinates, not a pixel count — for a filled NxN
    # block this is exactly (N-1)*(N-1) = 19*19 = 361, not 400. This is
    # standard, documented OpenCV behavior (confirmed by running it, not
    # assumed), kept here as the project's convention because circularity
    # pairs this same contourArea with cv2.arcLength on the same contour.
    assert abs(c.area - 361) < 1e-6
    assert abs(c.centroid_x - 49.5) < 1.0  # center of [40,60) is 49.5
    assert abs(c.centroid_y - 39.5) < 1.0


def test_multiple_separate_blobs_all_detected():
    mask = np.zeros((200, 200), dtype=np.uint8)
    mask[10:20, 10:20] = 255
    mask[50:60, 50:60] = 255
    mask[100:115, 100:115] = 255
    gray = _gray_with_value((200, 200))

    candidates = extract_candidates(mask, gray)
    assert len(candidates) == 3


def test_no_foreground_returns_empty_list():
    mask = np.zeros((50, 50), dtype=np.uint8)
    gray = _gray_with_value((50, 50))
    assert extract_candidates(mask, gray) == []


def test_min_area_filters_out_small_noise():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[10:12, 10:12] = 255  # tiny 2x2 noise speck, area ~1 (contourArea convention)
    mask[50:70, 50:70] = 255  # real 20x20 blob
    gray = _gray_with_value((100, 100))

    config = DetectionConfig(min_area_px=50.0)
    candidates = extract_candidates(mask, gray, config)
    assert len(candidates) == 1
    assert candidates[0].bbox_x == 50


def test_min_area_default_keeps_small_regions():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[10:12, 10:12] = 255  # tiny but non-zero area
    gray = _gray_with_value((100, 100))

    candidates = extract_candidates(mask, gray)  # default min_area_px=1.0
    assert len(candidates) == 1


def test_circular_blob_has_plausible_area_and_high_circularity():
    mask = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(mask, (50, 50), 10, 255, -1)
    gray = _gray_with_value((100, 100))

    candidates = extract_candidates(mask, gray)
    assert len(candidates) == 1
    expected_area = np.pi * 10**2
    assert abs(candidates[0].area - expected_area) / expected_area < 0.15
    # A real (pixelated) circle should score close to, but not exactly,
    # a perfect circle's circularity of 1.0.
    assert candidates[0].circularity > 0.8


def test_candidate_ids_are_sequential_starting_at_one():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[10:20, 10:20] = 255
    mask[50:60, 50:60] = 255
    gray = _gray_with_value((100, 100))

    candidates = extract_candidates(mask, gray)
    ids = sorted(c.id for c in candidates)
    assert ids == [1, 2]


# ---- Phase 5 feature tests ----

def test_elongated_blob_has_high_aspect_ratio():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[45:55, 10:90] = 255  # a 80x10 bar — clearly elongated
    gray = _gray_with_value((100, 100))

    candidates = extract_candidates(mask, gray)
    assert len(candidates) == 1
    assert candidates[0].aspect_ratio > 5.0


def test_square_blob_has_aspect_ratio_near_one():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[40:60, 40:60] = 255
    gray = _gray_with_value((100, 100))

    candidates = extract_candidates(mask, gray)
    assert abs(candidates[0].aspect_ratio - 1.0) < 0.01


def test_intensity_stats_reflect_actual_pixel_values_inside_blob():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[40:60, 40:60] = 255
    gray = np.full((100, 100), 200, dtype=np.uint8)
    gray[40:60, 40:60] = 50  # the blob region is darker than the background

    candidates = extract_candidates(mask, gray)
    c = candidates[0]
    assert abs(c.mean_intensity - 50) < 1.0
    assert c.min_intensity == 50
    assert c.max_intensity == 50


def test_local_contrast_is_nonzero_for_a_dark_spot_on_light_background():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[40:60, 40:60] = 255
    gray = np.full((100, 100), 200, dtype=np.uint8)
    gray[40:60, 40:60] = 50

    candidates = extract_candidates(mask, gray)
    assert candidates[0].local_contrast > 50  # background (200) vs blob (50)


def test_local_contrast_is_near_zero_when_blob_matches_background():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[40:60, 40:60] = 255
    gray = np.full((100, 100), 150, dtype=np.uint8)  # uniform — blob == surroundings

    candidates = extract_candidates(mask, gray)
    assert candidates[0].local_contrast < 1.0


def test_solid_square_has_high_solidity():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[40:60, 40:60] = 255
    gray = _gray_with_value((100, 100))

    candidates = extract_candidates(mask, gray)
    assert candidates[0].solidity > 0.95


def test_concave_shape_has_lower_solidity_than_solid_shape():
    # A "C" shape (a square with a bite taken out) has real concavity.
    concave_mask = np.zeros((100, 100), dtype=np.uint8)
    concave_mask[20:80, 20:80] = 255
    concave_mask[35:65, 50:80] = 0  # bite out of the right side

    solid_mask = np.zeros((100, 100), dtype=np.uint8)
    solid_mask[20:80, 20:80] = 255

    gray = _gray_with_value((100, 100))

    concave_candidates = extract_candidates(concave_mask, gray)
    solid_candidates = extract_candidates(solid_mask, gray)

    assert concave_candidates[0].solidity < solid_candidates[0].solidity


def test_extent_near_one_for_blob_filling_its_bbox():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[40:60, 40:60] = 255  # fills its own bounding box exactly
    gray = _gray_with_value((100, 100))

    candidates = extract_candidates(mask, gray)
    # extent = contourArea / bbox_area. Per the same contourArea convention
    # documented above (shoelace area on corner coordinates), a filled NxN
    # block gives (N-1)^2 / N^2 = 361/400 = 0.9025 here, not ~1.0 — a real,
    # correctly-computed value, not a bug. 0.85 leaves headroom above that.
    assert candidates[0].extent > 0.85


def test_equivalent_diameter_matches_area_formula():
    mask = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(mask, (50, 50), 15, 255, -1)
    gray = _gray_with_value((100, 100))

    c = extract_candidates(mask, gray)[0]
    expected = 2.0 * np.sqrt(c.area / np.pi)
    assert abs(c.equivalent_diameter - expected) < 1e-6


def test_centered_blob_has_complete_edge_state():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[40:60, 40:60] = 255
    gray = _gray_with_value((100, 100))

    candidates = extract_candidates(mask, gray)
    assert candidates[0].edge_state == EdgeState.COMPLETE


def test_blob_touching_border_has_partial_edge_state():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[0:20, 0:20] = 255  # touches the top-left corner of the frame
    gray = _gray_with_value((100, 100))

    candidates = extract_candidates(mask, gray)
    assert candidates[0].edge_state == EdgeState.PARTIAL


def test_rejection_reason_is_none_right_after_extraction():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[40:60, 40:60] = 255
    gray = _gray_with_value((100, 100))

    candidates = extract_candidates(mask, gray)
    assert candidates[0].rejection_reason is None
    assert candidates[0].is_validated is True
