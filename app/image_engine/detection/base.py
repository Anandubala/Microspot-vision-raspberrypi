"""Pluggable spot-detection interface (spec Section 8: "build this now,
train nothing yet").

ClassicalCVDetector (this phase) and ONNXDetector (stub, Phase 14) both
implement this same interface, so the rest of the application — whatever
calls detect() — never needs to change when a trained model becomes
available.
"""
from __future__ import annotations

from typing import Protocol

import numpy as np

from app.config.schemas import Candidate, DetectionConfig


class SpotDetector(Protocol):
    def detect(self, image: np.ndarray, config: DetectionConfig) -> list[Candidate]:
        """Detect candidate spots in a (grayscale) image under `config`."""
        ...
