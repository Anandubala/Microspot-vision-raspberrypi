"""Extracts every Section 7.4 candidate feature from a binary foreground
mask plus the original grayscale image.

Uses cv2.findContours rather than a separate connectedComponentsWithStats
call: contour tracing already identifies each connected foreground region
and yields its boundary polygon in one pass, which perimeter/circularity/
solidity below all need anyway — see docs/PHASE_4.md "design decisions"
for why this was chosen over calling both APIs separately.

`config.min_area_px` here is a noise floor only (default 1.0 = effectively
no filtering) — NOT the explainable, rejection-reason-tracked size
filtering Phase 5's filtering/filters.py implements. That's a deliberately
separate, later concern in the pipeline (Section 7: CANDIDATE EXTRACTION
happens before CANDIDATE FILTERING).
"""
from __future__ import annotations

import cv2
import numpy as np

from app.config.schemas import Candidate, DetectionConfig, EdgeState


def extract_candidates(
    mask: np.ndarray, gray: np.ndarray, config: DetectionConfig | None = None
) -> list[Candidate]:
    """Find every connected foreground region in `mask` and compute its
    full Section 7.4 feature set against the corresponding pixels of
    `gray` (the grayscale image the mask was computed from — intensity
    features are meaningless without it).
    """
    config = config or DetectionConfig()
    img_h, img_w = mask.shape[:2]
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates: list[Candidate] = []
    next_id = 1
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < config.min_area_px:
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

        perimeter = cv2.arcLength(contour, True)
        circularity = _circularity(area, perimeter)
        aspect_ratio = _aspect_ratio(w, h)
        equivalent_diameter = 2.0 * float(np.sqrt(area / np.pi)) if area > 0 else 0.0
        extent = area / (w * h) if (w * h) > 0 else 0.0
        solidity = _solidity(contour, area)
        edge_state = _edge_state(x, y, w, h, img_w, img_h)

        mean_i, min_i, max_i, local_contrast = _local_intensity_features(
            gray, contour, x, y, w, h, img_w, img_h, config.local_contrast_ring_px
        )

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
                perimeter=float(perimeter),
                circularity=circularity,
                aspect_ratio=aspect_ratio,
                mean_intensity=mean_i,
                min_intensity=min_i,
                max_intensity=max_i,
                local_contrast=local_contrast,
                equivalent_diameter=equivalent_diameter,
                solidity=solidity,
                extent=extent,
                edge_state=edge_state,
            )
        )
        next_id += 1

    return candidates


def _circularity(area: float, perimeter: float) -> float:
    """4*pi*area / perimeter^2. 1.0 for a perfect circle, lower for
    elongated or irregular shapes. 0.0 for a degenerate (zero-perimeter)
    contour rather than dividing by zero.
    """
    if perimeter <= 0:
        return 0.0
    return float(4.0 * np.pi * area / (perimeter**2))


def _aspect_ratio(w: int, h: int) -> float:
    """Longer bounding-box side / shorter side, always >= 1.0."""
    if w == 0 or h == 0:
        return 1.0
    long_side, short_side = (w, h) if w >= h else (h, w)
    return float(long_side / short_side)


def _solidity(contour: np.ndarray, area: float) -> float:
    """area / convex-hull area. 1.0 for a fully convex shape, lower for
    shapes with concavities (e.g. two touching spots merged into one
    blob — Phase 6's watershed separation targets exactly this case).
    0.0 for a degenerate (zero hull area) contour rather than dividing by
    zero.
    """
    hull = cv2.convexHull(contour)
    hull_area = cv2.contourArea(hull)
    if hull_area <= 0:
        return 0.0
    return float(min(area / hull_area, 1.0))  # clamp: pixelation can push this fractionally over 1.0


def _edge_state(x: int, y: int, w: int, h: int, img_w: int, img_h: int) -> EdgeState:
    """PARTIAL if the bounding box touches any image border, COMPLETE
    otherwise. A purely geometric fact — see EdgeState's docstring for why
    this never becomes EDGE_EXCLUDED here.
    """
    touches_edge = x <= 0 or y <= 0 or (x + w) >= img_w or (y + h) >= img_h
    return EdgeState.PARTIAL if touches_edge else EdgeState.COMPLETE


def _local_intensity_features(
    gray: np.ndarray,
    contour: np.ndarray,
    x: int,
    y: int,
    w: int,
    h: int,
    img_w: int,
    img_h: int,
    ring_px: int,
) -> tuple[float, float, float, float]:
    """Mean/min/max intensity inside the candidate, plus local_contrast
    against a `ring_px`-wide ring just outside it — computed on a small
    CROP around the candidate's bounding box, not the full image.

    This is the performance-critical part of extraction. The original
    Phase 5 implementation allocated a full-image-sized blank mask and ran
    drawContours/dilate on it for EVERY candidate — fine for a handful of
    candidates, but on a real microscope image with several thousand tiny
    spots (confirmed: ~9,800 on a real lab image, ~1-1.5 minutes to
    import) that's thousands of full-image-sized allocations, each one
    mostly empty space the candidate never touches. Cropping to a small
    padded region around just this candidate's bounding box turns an
    O(candidates x image_area) cost into O(candidates x local_area), which
    for small spots in a large image is a very large, measured speedup
    (see docs/PHASE_7.md's before/after benchmark) — not a hypothetical
    optimization.
    """
    pad = ring_px + 1
    cx0, cy0 = max(0, x - pad), max(0, y - pad)
    cx1, cy1 = min(img_w, x + w + pad), min(img_h, y + h + pad)

    gray_crop = gray[cy0:cy1, cx0:cx1]
    local_mask = np.zeros(gray_crop.shape, dtype=np.uint8)
    shifted_contour = contour - np.array([cx0, cy0])
    cv2.drawContours(local_mask, [shifted_contour], -1, 255, thickness=cv2.FILLED)

    inside_pixels = gray_crop[local_mask == 255]
    if inside_pixels.size == 0:
        return 0.0, 0.0, 0.0, 0.0
    mean_i = float(inside_pixels.mean())
    min_i = float(inside_pixels.min())
    max_i = float(inside_pixels.max())

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * ring_px + 1, 2 * ring_px + 1))
    dilated = cv2.dilate(local_mask, kernel)
    ring_mask = cv2.bitwise_and(dilated, cv2.bitwise_not(local_mask))
    ring_pixels = gray_crop[ring_mask == 255]

    local_contrast = float(abs(mean_i - float(ring_pixels.mean()))) if ring_pixels.size > 0 else 0.0

    return mean_i, min_i, max_i, local_contrast
