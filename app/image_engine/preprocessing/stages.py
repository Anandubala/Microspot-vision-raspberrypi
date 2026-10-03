"""Individual preprocessing stage computations (spec Section 7).

Each function does exactly one transformation and returns a uint8 array
ready for display/the next stage — no stage here invents or destroys
features (Section 1): these are standard, explainable operations
(min-max stretch, large-kernel blur as a background estimate,
background division, denoising, CLAHE), each independently testable.
"""
from __future__ import annotations

import cv2
import numpy as np


def normalize(gray: np.ndarray) -> np.ndarray:
    """Min-max contrast stretch to the full 0-255 range.

    Accepts any numeric dtype (correct_illumination feeds it float64
    ratios) and always returns uint8. A flat/uniform input (min == max,
    nothing to stretch) is rescaled-as-is rather than dividing by zero,
    but still cast to uint8 — not returned in its original dtype.
    """
    gray_f = gray.astype(np.float64)
    lo, hi = gray_f.min(), gray_f.max()
    if hi <= lo:
        return np.clip(np.rint(gray_f), 0, 255).astype(np.uint8)
    stretched = (gray_f - lo) * (255.0 / (hi - lo))
    return np.clip(np.rint(stretched), 0, 255).astype(np.uint8)


def estimate_background(gray: np.ndarray, kernel_size: int) -> np.ndarray:
    """Estimate the illumination background via a large-kernel Gaussian
    blur — real spots are small relative to `kernel_size`, so they're
    averaged away, leaving the slow-varying illumination field.

    `kernel_size` is forced odd (Gaussian blur requires it) and capped to
    the smaller image dimension so it never errors on small images.
    """
    kernel_size = _odd(kernel_size)
    max_allowed = _odd(min(gray.shape[:2]) - 1) if min(gray.shape[:2]) > 1 else 1
    kernel_size = min(kernel_size, max_allowed) if max_allowed >= 1 else 1
    if kernel_size < 1:
        kernel_size = 1
    return cv2.GaussianBlur(gray, (kernel_size, kernel_size), 0)


def correct_illumination(gray: np.ndarray, background: np.ndarray) -> np.ndarray:
    """Divide the image by its estimated background and rescale back to
    0-255 — a standard flat-field-style correction that flattens uneven
    illumination without inventing new features.
    """
    gray_f = gray.astype(np.float64)
    bg_f = background.astype(np.float64)
    bg_f[bg_f == 0] = 1.0  # avoid divide-by-zero on pure-black background estimate
    corrected = gray_f / bg_f
    return normalize(corrected.astype(np.float64))


def denoise(gray: np.ndarray, method: str, kernel_size: int) -> np.ndarray:
    """Denoise with the configured method. `method` is validated here
    rather than silently falling back, so a typo'd config value fails
    loudly instead of quietly picking a default.
    """
    kernel_size = _odd(kernel_size)
    if method == "gaussian":
        return cv2.GaussianBlur(gray, (kernel_size, kernel_size), 0)
    if method == "median":
        return cv2.medianBlur(gray, kernel_size)
    raise ValueError(f"Unknown denoise method: {method!r} (expected 'gaussian' or 'median')")


def enhance_contrast(gray: np.ndarray, clip_limit: float, tile_grid_size: int) -> np.ndarray:
    """CLAHE (Contrast Limited Adaptive Histogram Equalization) — boosts
    local contrast so dim spots become easier to separate from background,
    without the global washout a plain histogram-equalize would cause.
    """
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size))
    return clahe.apply(gray)


def _odd(n: int) -> int:
    """Round up to the nearest odd integer >= 1 (required by several
    OpenCV kernel-size parameters).
    """
    n = max(1, int(n))
    return n if n % 2 == 1 else n + 1
