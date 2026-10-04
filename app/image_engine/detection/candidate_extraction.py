"""Extracts raw candidates from a binary foreground mask.

Uses cv2.findContours rather than a separate connectedComponentsWithStats
call: contour tracing already identifies each connected foreground region
(the same regions connected-component labeling would find) and yields its
boundary polygon, bounding box, area, and centroid in a single pass — see
docs/PHASE_4.md "design decisions" for why this was chosen over calling
both APIs separately.

`min_area_px` here is a noise floor only (default 1.0 = effectively no
filtering) — NOT the explainable, rejection-reason-tracked size filtering
spec Section 7.4/Phase 5 describes. That's a deliberately separate,
later concern.
"""
from __future__ import annotations

import cv2
import numpy as np

from app.config.schemas import Candidate


def extract_candidates(mask: np.ndarray, min_area_px: float = 1.0) -> list[Candidate]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates: list[Candidate] = []
    next_id = 1
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area_px:
            continue

        x, y, w, h = cv2.boundingRect(contour)

        moments = cv2.moments(contour)
        if moments["m00"] != 0:
            cx = moments["m10"] / moments["m00"]
            cy = moments["m01"] / moments["m00"]
        else:
            # Degenerate contour (e.g. a single point/line) — fall back to
            # the bounding box center rather than dividing by zero.
            cx = x + w / 2.0
            cy = y + h / 2.0

        points = [(int(p[0][0]), int(p[0][1])) for p in contour]

        candidates.append(
            Candidate(
                id=next_id,
                centroid_x=float(cx),
                centroid_y=float(cy),
                bbox_x=x,
                bbox_y=y,
                bbox_w=w,
                bbox_h=h,
                area=float(area),
                contour=points,
            )
        )
        next_id += 1

    return candidates
