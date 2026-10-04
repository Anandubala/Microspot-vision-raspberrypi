"""Trained-model detection backend — deferred to Phase 14.

This exists now, per spec Section 8, as a real extension point: the
active backend is chosen via DetectionConfig.detector_backend, and
whatever calls SpotDetector.detect() doesn't change when this stops being
a stub. It raises NotImplementedError rather than silently returning
nothing or fabricating results.
"""
from __future__ import annotations

import numpy as np

from app.config.schemas import Candidate, DetectionConfig


class ONNXDetector:
    """Loads a YOLOv8n model exported to ONNX. NOT IMPLEMENTED — Phase 14,
    once Phases 7-8 produce real labeled data to train on.
    """

    def detect(self, image: np.ndarray, config: DetectionConfig) -> list[Candidate]:
        raise NotImplementedError(
            "ONNXDetector is not implemented yet (deferred to Phase 14, after "
            "Phases 7-8 produce labeled training data). Use ClassicalCVDetector "
            "(detector_backend='classical_cv') for detection in this build."
        )
