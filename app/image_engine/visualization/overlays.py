"""Drawing helpers for inspectable overlay stages.

Phase 4 added an unlabeled outline of every raw candidate (draw_candidate_
outlines), so a reviewer can see what segmentation + extraction found
before any filtering exists. Phase 5 adds the numbered, filtered,
final-count overlay (draw_validated_overlay) that Section 12 calls the
reviewer-facing result.
"""
from __future__ import annotations

import cv2
import numpy as np

from app.config.schemas import Candidate

_VALIDATED_COLOR = (0, 255, 0)  # green (BGR)
_REJECTED_COLOR = (0, 140, 255)  # orange (BGR)


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


def draw_validated_overlay(gray: np.ndarray, candidates: list[Candidate]) -> np.ndarray:
    """Return a BGR copy of `gray` with:

    - every VALIDATED candidate (rejection_reason is None) outlined in
      green and labeled with a sequential number, starting at 1
    - every REJECTED candidate outlined in orange, unlabeled

    Numbers are assigned in the order candidates appear in the input list
    (their original detection order) — this is NOT a spatial left-to-right
    or top-to-bottom ordering guarantee; it's whatever order
    extract_candidates produced them in. Stated here and in
    docs/PHASE_5.md so nobody reads meaning into the numbering that isn't
    there.

    This is the Section 12 "numbered overlay" — the reviewer-facing
    result — not an intermediate debug stage.
    """
    display = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    rejected_contours = [
        np.array(c.contour, dtype=np.int32).reshape(-1, 1, 2)
        for c in candidates
        if not c.is_validated
    ]
    cv2.drawContours(display, rejected_contours, -1, _REJECTED_COLOR, 1)

    label_number = 1
    for c in candidates:
        if not c.is_validated:
            continue
        contour = np.array(c.contour, dtype=np.int32).reshape(-1, 1, 2)
        cv2.drawContours(display, [contour], -1, _VALIDATED_COLOR, 1)
        label_pos = (int(c.centroid_x) + 4, int(c.centroid_y) - 4)
        cv2.putText(
            display,
            str(label_number),
            label_pos,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            _VALIDATED_COLOR,
            1,
            cv2.LINE_AA,
        )
        label_number += 1

    return display
