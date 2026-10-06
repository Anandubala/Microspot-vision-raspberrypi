"""Classical computer-vision spot detector: threshold -> touching-spot
separation -> contour-based candidate extraction. The only detector
implemented so far — ONNXDetector (onnx_detector.py) is a stub until
Phase 14.

Touching-spot separation (Phase 6) runs BEFORE candidate extraction, not
after — a deliberate ordering choice. The master spec's Section 7 pipeline
diagram lists "CANDIDATE FILTERING" before "TOUCHING-SPOT SEPARATION", but
filtering a still-merged blob first would risk rejecting it outright
(e.g. on LOW_SOLIDITY, since two touching circles are much less convex
than one) before ever getting the chance to split it into two legitimate
spots. Splitting first means each sub-spot gets its own accurate
circularity/solidity/area computed independently, and filtering then
judges each one on its own real merits. See docs/PHASE_6.md "design
decisions" for the full reasoning.
"""
from __future__ import annotations

import numpy as np

from app.config.schemas import Candidate, DetectionConfig
from app.image_engine.detection.candidate_extraction import extract_candidates
from app.image_engine.segmentation.thresholding import compute_mask, determine_polarity
from app.image_engine.separation.watershed import separate_touching_blobs


def segment_and_extract(
    gray: np.ndarray, config: DetectionConfig
) -> tuple[np.ndarray, list[Candidate], bool]:
    """Run segmentation -> touching-spot separation -> extraction and
    return the (possibly-separated) mask, the candidates, and whether
    watershed separation actually split anything this run (Section 7.5:
    "record whether it was used for that session").

    Used by the GUI (which needs the mask to display as its own
    inspectable stage) and by ClassicalCVDetector.detect() below (which
    only needs to return candidates, per the SpotDetector interface).
    """
    resolved_polarity = determine_polarity(gray, config.polarity)
    mask = compute_mask(gray, config, resolved_polarity)

    if config.enable_watershed_separation:
        mask, separation_applied = separate_touching_blobs(
            mask, config.watershed_min_peak_distance_px
        )
    else:
        separation_applied = False

    candidates = extract_candidates(mask, gray, config)
    return mask, candidates, separation_applied


class ClassicalCVDetector:
    """Threshold + contour-based candidate extraction. Implemented now,
    per spec Section 8.
    """

    def detect(self, image: np.ndarray, config: DetectionConfig) -> list[Candidate]:
        _, candidates, _ = segment_and_extract(image, config)
        return candidates
