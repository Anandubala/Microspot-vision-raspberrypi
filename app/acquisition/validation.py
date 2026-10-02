"""Image validation (spec Section 6: validation happens before hashing and
quality analysis, as its own explicit stage).

FileImportSource (Phase 1) already rejects files that are the wrong
extension or that OpenCV can't decode at all. This module validates the
*decoded array* itself — catching degenerate results that decode
successfully but aren't usable (zero-sized, wrong dtype, unsupported
channel count) before SHA-256/copy/quality-analysis run on them.
"""
from __future__ import annotations

import numpy as np


class InvalidImageError(ValueError):
    """Raised when a decoded image array fails validation."""


def validate_image_array(image: np.ndarray) -> None:
    """Raise InvalidImageError if the array isn't a usable image.

    Checks, in order: non-empty, non-zero width/height, 8-bit unsigned
    data (what the rest of the pipeline assumes), and a supported channel
    count (grayscale, BGR, or BGRA — matching what FileImportSource and
    ImageViewer already handle).
    """
    if image is None or image.size == 0:
        raise InvalidImageError("Decoded image is empty.")

    if image.ndim not in (2, 3):
        raise InvalidImageError(f"Unexpected array shape: {image.shape}")

    height, width = image.shape[:2]
    if height == 0 or width == 0:
        raise InvalidImageError(f"Image has a zero dimension: {width}x{height}")

    if image.dtype != np.uint8:
        raise InvalidImageError(
            f"Expected 8-bit unsigned image data, got dtype={image.dtype}. "
            "16-bit/float microscope exports need a conversion step not yet "
            "implemented."
        )

    if image.ndim == 3 and image.shape[2] not in (3, 4):
        raise InvalidImageError(f"Unsupported channel count: {image.shape[2]}")
