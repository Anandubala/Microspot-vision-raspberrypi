import cv2
import numpy as np

from app.image_engine.separation.watershed import separate_touching_blobs


def _components(mask: np.ndarray) -> int:
    n, _ = cv2.connectedComponents(mask)
    return n - 1  # subtract the background label


def test_empty_mask_returns_unchanged_and_not_applied():
    mask = np.zeros((50, 50), dtype=np.uint8)
    new_mask, applied = separate_touching_blobs(mask)
    assert applied is False
    assert np.array_equal(mask, new_mask)


def test_single_isolated_circle_is_not_split():
    mask = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(mask, (50, 50), 20, 255, -1)

    new_mask, applied = separate_touching_blobs(mask, min_distance_px=15)
    assert applied is False
    assert np.array_equal(mask, new_mask)
    assert _components(new_mask) == 1


def test_two_separate_non_touching_circles_are_not_falsely_split():
    mask = np.zeros((100, 200), dtype=np.uint8)
    cv2.circle(mask, (40, 50), 15, 255, -1)
    cv2.circle(mask, (160, 50), 15, 255, -1)

    new_mask, applied = separate_touching_blobs(mask, min_distance_px=15)
    assert applied is False
    assert np.array_equal(mask, new_mask)
    assert _components(new_mask) == 2  # already two — correctly left as two


def test_two_overlapping_circles_are_split_into_two_components():
    mask = np.zeros((100, 150), dtype=np.uint8)
    cv2.circle(mask, (50, 50), 25, 255, -1)
    cv2.circle(mask, (85, 50), 25, 255, -1)  # overlaps — one connected blob

    assert _components(mask) == 1  # sanity check on the fixture

    new_mask, applied = separate_touching_blobs(mask, min_distance_px=15)
    assert applied is True
    assert _components(new_mask) == 2


def test_three_overlapping_circles_in_a_row_split_into_three():
    mask = np.zeros((100, 220), dtype=np.uint8)
    cv2.circle(mask, (50, 50), 25, 255, -1)
    cv2.circle(mask, (85, 50), 25, 255, -1)
    cv2.circle(mask, (120, 50), 25, 255, -1)

    assert _components(mask) == 1

    new_mask, applied = separate_touching_blobs(mask, min_distance_px=15)
    assert applied is True
    assert _components(new_mask) == 3


def test_separated_regions_total_area_is_close_to_original():
    """Splitting carves a thin 1px boundary — total foreground area should
    shrink only slightly, not collapse.
    """
    mask = np.zeros((100, 150), dtype=np.uint8)
    cv2.circle(mask, (50, 50), 25, 255, -1)
    cv2.circle(mask, (85, 50), 25, 255, -1)

    original_area = int(np.count_nonzero(mask))
    new_mask, applied = separate_touching_blobs(mask, min_distance_px=15)
    new_area = int(np.count_nonzero(new_mask))

    assert applied is True
    assert new_area < original_area  # some pixels removed for the boundary
    assert new_area > original_area * 0.9  # but only a thin boundary's worth


def test_min_distance_controls_sensitivity():
    """A very large min_distance_px should treat two close-together peaks
    as one (no split); a small one should find both.
    """
    mask = np.zeros((100, 150), dtype=np.uint8)
    cv2.circle(mask, (50, 50), 25, 255, -1)
    cv2.circle(mask, (85, 50), 25, 255, -1)

    _, applied_strict = separate_touching_blobs(mask, min_distance_px=100)
    _, applied_loose = separate_touching_blobs(mask, min_distance_px=5)

    assert applied_strict is False  # peaks less than 100px apart -> merged into one
    assert applied_loose is True


def test_output_mask_is_binary_0_or_255():
    mask = np.zeros((100, 150), dtype=np.uint8)
    cv2.circle(mask, (50, 50), 25, 255, -1)
    cv2.circle(mask, (85, 50), 25, 255, -1)

    new_mask, _ = separate_touching_blobs(mask, min_distance_px=15)
    assert set(np.unique(new_mask).tolist()) <= {0, 255}
