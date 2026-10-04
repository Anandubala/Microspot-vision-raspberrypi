"""Segmentation stage: resolves detection polarity and produces a binary
foreground mask (spec Sections 7.1, 7.2).

Exactly one thresholding method runs per image — never all of them — and
polarity AUTO is resolved by a real, simple, documented measurement of
image statistics, never a random guess.
"""
from __future__ import annotations

import cv2
import numpy as np

from app.config.schemas import DetectionConfig, DetectionPolarity, SegmentationMethod


def determine_polarity(gray: np.ndarray, configured: DetectionPolarity) -> DetectionPolarity:
    """Resolve AUTO to a concrete polarity by comparing the image's mean
    intensity to the mid-point of the 0-255 range: a majority-bright image
    is assumed to have a light background with dark spots (DARK_ON_LIGHT),
    and vice versa.

    This is a simple, real, and honestly limited heuristic — stated
    explicitly here and in docs/PHASE_4.md, not papered over. It can be
    wrong for images that are neither clearly bright- nor dark-dominant
    (e.g. roughly 50/50 coverage); it was chosen because it's transparent
    and auditable, not because it's the most sophisticated option
    available.

    If `configured` is not AUTO, it's returned unchanged — no measurement
    happens, since the user (or session config) already decided.
    """
    if configured != DetectionPolarity.AUTO:
        return configured

    mean_intensity = float(gray.mean())
    if mean_intensity >= 127.5:
        return DetectionPolarity.DARK_ON_LIGHT
    return DetectionPolarity.BRIGHT_ON_DARK


def compute_mask(
    gray: np.ndarray, config: DetectionConfig, resolved_polarity: DetectionPolarity
) -> np.ndarray:
    """Produce a binary foreground mask (0 or 255) where 255 marks
    candidate spot pixels, using exactly the one segmentation method
    named in `config.segmentation_method`.

    `resolved_polarity` must already be concrete (not AUTO) — callers get
    it from determine_polarity() first, so this function has no hidden
    AUTO-resolution logic of its own.
    """
    if resolved_polarity == DetectionPolarity.AUTO:
        raise ValueError(
            "compute_mask requires a resolved polarity, not AUTO. "
            "Call determine_polarity() first."
        )

    # A perfectly flat image (gray.min() == gray.max()) has zero local
    # contrast — there is no principled way to separate "foreground spots"
    # from "background" because there is no variation to separate. Otsu's
    # threshold degenerates to 0 on a flat histogram, which (combined with
    # non-inverted thresholding) would otherwise flag the ENTIRE image as
    # one spurious candidate — a real bug this project's own tests caught
    # (see docs/PHASE_4.md). The only honest answer here is zero detections
    # (spec Section 1: "Zero detections is a valid result"), not a guess in
    # either direction. A flat image should also already carry Phase 2's
    # LOW_CONTRAST quality warning, which is the right place for a reviewer
    # to see *why* nothing was detected.
    if gray.min() == gray.max():
        return np.zeros_like(gray)

    # THRESH_BINARY_INV makes pixels BELOW the threshold foreground (255) —
    # correct for small dark spots on light background. Plain THRESH_BINARY
    # makes pixels ABOVE the threshold foreground — correct for bright
    # spots on a dark background.
    invert = resolved_polarity == DetectionPolarity.DARK_ON_LIGHT

    method = config.segmentation_method
    if method == SegmentationMethod.OTSU:
        thresh_type = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
        _, mask = cv2.threshold(gray, 0, 255, thresh_type | cv2.THRESH_OTSU)
        return mask

    if method in (SegmentationMethod.ADAPTIVE_MEAN, SegmentationMethod.ADAPTIVE_GAUSSIAN):
        adaptive_method = (
            cv2.ADAPTIVE_THRESH_MEAN_C
            if method == SegmentationMethod.ADAPTIVE_MEAN
            else cv2.ADAPTIVE_THRESH_GAUSSIAN_C
        )
        thresh_type = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
        block_size = _odd(config.adaptive_block_size)
        mask = cv2.adaptiveThreshold(
            gray,
            255,
            adaptive_method,
            thresh_type,
            block_size,
            config.adaptive_c,
        )
        return mask

    raise ValueError(f"Unknown segmentation method: {method!r}")


def _odd(n: int) -> int:
    n = max(3, int(n))
    return n if n % 2 == 1 else n + 1
