"""Individual image-quality metric computations.

Each function does exactly one measurement and returns a raw number —
thresholding/warning-generation happens one layer up in quality_analysis.py,
so these stay independently testable and reusable (e.g. for per-ROI quality
checks later).
"""
from __future__ import annotations

import cv2
import numpy as np


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert a loaded image (grayscale, BGR, or BGRA) to grayscale."""
    if image.ndim == 2:
        return image
    if image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    raise ValueError(f"Unsupported channel count: {image.shape[2]}")


def blur_variance(gray: np.ndarray) -> float:
    """Variance of the Laplacian — a standard, well-established focus
    measure. Lower variance means fewer sharp edges, i.e. more blur.

    This is a relative measure: what counts as "too low" depends on image
    content and must be calibrated (QualityConfig.blur_variance_min), not
    treated as an absolute, universal cutoff.
    """
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return float(laplacian.var())


def contrast_std(gray: np.ndarray) -> float:
    """Standard deviation of pixel intensities — a simple, real RMS-contrast
    measure. A near-uniform image (little to distinguish spots from
    background) has a low value here.
    """
    return float(gray.std())


def illumination_cv(gray: np.ndarray, grid_size: int = 4) -> float:
    """Coefficient of variation (std / mean) of per-cell mean intensity
    across an NxN grid — a real measure of uneven illumination across the
    frame. A perfectly flat-lit image scores near 0; strong vignetting or a
    lighting gradient scores higher.

    Grid cells that would be empty (grid_size larger than the image) are
    skipped rather than fabricated.
    """
    height, width = gray.shape[:2]
    grid_size = max(1, min(grid_size, height, width))

    cell_h = height // grid_size
    cell_w = width // grid_size

    cell_means = []
    for row in range(grid_size):
        for col in range(grid_size):
            y0, y1 = row * cell_h, (row + 1) * cell_h if row < grid_size - 1 else height
            x0, x1 = col * cell_w, (col + 1) * cell_w if col < grid_size - 1 else width
            cell = gray[y0:y1, x0:x1]
            if cell.size > 0:
                cell_means.append(float(cell.mean()))

    if len(cell_means) < 2:
        return 0.0  # Not enough cells to measure non-uniformity.

    mean_of_means = float(np.mean(cell_means))
    if mean_of_means == 0.0:
        return 0.0  # Fully black image — avoid division by zero.

    return float(np.std(cell_means) / mean_of_means)


def clipping_fractions(gray: np.ndarray) -> tuple[float, float]:
    """Fraction of pixels pinned at 0 (underexposed/clipped dark) and at
    255 (overexposed/clipped bright). Both are real histogram counts, not
    estimates.

    Returns (dark_fraction, bright_fraction), each in [0.0, 1.0].
    """
    total = gray.size
    dark_fraction = float(np.count_nonzero(gray == 0)) / total
    bright_fraction = float(np.count_nonzero(gray == 255)) / total
    return dark_fraction, bright_fraction
