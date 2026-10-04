"""Classical computer-vision spot detector: threshold -> contour-based
candidate extraction. The only detector implemented so far — ONNXDetector
(onnx_detector.py) is a stub until Phase 14.
"""
from __future__ import annotations

import numpy as np

from app.config.schemas import Candidate, DetectionConfig
from app.image_engine.detection.candidate_extraction import extract_candidates
from app.image_engine.segmentation.thresholding import compute_mask, determine_polarity


def segment_and_extract(
    gray: np.ndarray, config: DetectionConfig
) -> tuple[np.ndarray, list[Candidate]]:
    """Run segmentation + extraction and return both the mask and the
    candidates — used by the GUI (which needs the mask to display as its
    own inspectable stage) and by ClassicalCVDetector.detect() below
    (which only needs to return candidates, per the SpotDetector
    interface).
    """
    resolved_polarity = determine_polarity(gray, config.polarity)
    mask = compute_mask(gray, config, resolved_polarity)
    candidates = extract_candidates(mask, config.min_area_px)
    return mask, candidates


class ClassicalCVDetector:
    """Threshold + contour-based candidate extraction. Implemented now,
    per spec Section 8.
    """

    def detect(self, image: np.ndarray, config: DetectionConfig) -> list[Candidate]:
        _, candidates = segment_and_extract(image, config)
        return candidates
