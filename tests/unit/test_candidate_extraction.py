import cv2
import numpy as np

from app.image_engine.detection.candidate_extraction import extract_candidates


def test_single_square_blob_detected_with_correct_geometry():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[30:50, 40:60] = 255  # a 20x20 square at (40, 30)

    candidates = extract_candidates(mask)
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
    # assumed), kept here as the project's convention because Phase 5's
    # circularity calculation will pair this same contourArea with
    # cv2.arcLength on the same contour.
    assert abs(c.area - 361) < 1e-6
    assert abs(c.centroid_x - 49.5) < 1.0  # center of [40,60) is 49.5
    assert abs(c.centroid_y - 39.5) < 1.0


def test_multiple_separate_blobs_all_detected():
    mask = np.zeros((200, 200), dtype=np.uint8)
    mask[10:20, 10:20] = 255
    mask[50:60, 50:60] = 255
    mask[100:115, 100:115] = 255

    candidates = extract_candidates(mask)
    assert len(candidates) == 3


def test_no_foreground_returns_empty_list():
    mask = np.zeros((50, 50), dtype=np.uint8)
    assert extract_candidates(mask) == []


def test_min_area_filters_out_small_noise():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[10:12, 10:12] = 255  # tiny 2x2 noise speck, area ~4
    mask[50:70, 50:70] = 255  # real 20x20 blob, area 400

    # With a high min_area, only the real blob should survive.
    candidates = extract_candidates(mask, min_area_px=50.0)
    assert len(candidates) == 1
    assert candidates[0].bbox_x == 50


def test_min_area_default_keeps_small_regions():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[10:12, 10:12] = 255  # tiny but non-zero area

    candidates = extract_candidates(mask)  # default min_area_px=1.0
    assert len(candidates) == 1


def test_circular_blob_has_plausible_area():
    mask = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(mask, (50, 50), 10, 255, -1)

    candidates = extract_candidates(mask)
    assert len(candidates) == 1
    expected_area = np.pi * 10**2
    # Pixelated circle area should be within ~15% of the ideal geometric area.
    assert abs(candidates[0].area - expected_area) / expected_area < 0.15


def test_candidate_ids_are_sequential_starting_at_one():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[10:20, 10:20] = 255
    mask[50:60, 50:60] = 255

    candidates = extract_candidates(mask)
    ids = sorted(c.id for c in candidates)
    assert ids == [1, 2]
