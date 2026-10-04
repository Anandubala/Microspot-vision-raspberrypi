import numpy as np

from app.image_engine.detection.candidate_extraction import extract_candidates
from app.image_engine.visualization.overlays import draw_candidate_outlines


def test_draw_candidate_outlines_returns_bgr_same_size():
    gray = np.full((100, 100), 200, dtype=np.uint8)
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[40:60, 40:60] = 255
    candidates = extract_candidates(mask)

    result = draw_candidate_outlines(gray, candidates)
    assert result.shape == (100, 100, 3)
    assert result.dtype == np.uint8


def test_draw_candidate_outlines_with_no_candidates_returns_plain_bgr():
    gray = np.full((50, 50), 128, dtype=np.uint8)
    result = draw_candidate_outlines(gray, [])
    assert result.shape == (50, 50, 3)
    # Should just be the grayscale image converted to BGR, unchanged.
    assert np.all(result[:, :, 0] == 128)
