"""Drawing helpers for inspectable overlay stages.

Phase 4 only needs an unlabeled outline of every raw candidate, so a
reviewer can see what the segmentation + extraction stage found before any
filtering exists. Numbered, filtered, final-count overlays are Phase 5.
"""
from __future__ import annotations

import cv2
import numpy as np

from app.config.schemas import Candidate


def draw_candidate_outlines(gray: np.ndarray, candidates: list[Candidate]) -> np.ndarray:
    """Return a BGR copy of `gray` with every candidate's contour outlined
    in green. Unlabeled (no numbers, no count) — this is the Phase 4
    "raw candidates" inspection stage, not a final reviewer-facing result.
    """
    display = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    contours = [
        np.array(c.contour, dtype=np.int32).reshape(-1, 1, 2) for c in candidates
    ]
    cv2.drawContours(display, contours, -1, (0, 255, 0), 1)
    return display
