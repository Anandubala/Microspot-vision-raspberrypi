"""Image-quality diagnostics (spec Section 2: "Runs image-quality
diagnostics (blur, contrast, illumination, clipping) before analysis").

Ties the individual metric computations (metrics.py) to a QualityConfig's
thresholds and produces a QualityMetrics result with explicit, named
warnings — never a bare score with no stated basis (Section 1).
"""
from __future__ import annotations

import numpy as np

from app.config.schemas import QualityConfig, QualityMetrics
from app.image_engine.quality.metrics import (
    blur_variance,
    clipping_fractions,
    contrast_std,
    illumination_cv,
    to_grayscale,
)


def analyze_quality(
    image: np.ndarray, config: QualityConfig | None = None
) -> QualityMetrics:
    """Run every quality diagnostic on `image` and return the result,
    including which configured thresholds (if any) it failed.
    """
    config = config or QualityConfig()
    gray = to_grayscale(image)

    blur = blur_variance(gray)
    contrast = contrast_std(gray)
    illum_cv = illumination_cv(gray, grid_size=config.illumination_grid_size)
    dark_fraction, bright_fraction = clipping_fractions(gray)

    warnings: list[str] = []
    if blur < config.blur_variance_min:
        warnings.append("BLURRY")
    if contrast < config.contrast_std_min:
        warnings.append("LOW_CONTRAST")
    if illum_cv > config.illumination_cv_max:
        warnings.append("UNEVEN_ILLUMINATION")
    if dark_fraction > config.clipping_fraction_max:
        warnings.append("CLIPPED_DARK")
    if bright_fraction > config.clipping_fraction_max:
        warnings.append("CLIPPED_BRIGHT")

    return QualityMetrics(
        blur_variance=blur,
        contrast_std=contrast,
        illumination_cv=illum_cv,
        clipped_dark_fraction=dark_fraction,
        clipped_bright_fraction=bright_fraction,
        warnings=warnings,
    )
