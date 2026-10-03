"""Runs the Section 7 preprocessing stages in order and returns every
intermediate result, named, so the GUI can let the user inspect any of
them — "essential for your reviewers to trust the result."

Stage order matches Section 7 exactly: grayscale -> normalized ->
background estimate -> corrected -> denoised -> enhanced. Segmentation
onward is Phase 4+.
"""
from __future__ import annotations

from collections import OrderedDict

import numpy as np

from app.config.schemas import PreprocessingConfig
from app.image_engine.preprocessing.stages import (
    correct_illumination,
    denoise,
    enhance_contrast,
    estimate_background,
    normalize,
)
from app.image_engine.quality.metrics import to_grayscale


def run_preprocessing_pipeline(
    image: np.ndarray, config: PreprocessingConfig | None = None
) -> "OrderedDict[str, np.ndarray]":
    """Run every stage and return an OrderedDict of stage name -> uint8
    array, in pipeline order. Keys match the Section 7 stage names exactly
    so GUI labels and this dict never drift apart.
    """
    config = config or PreprocessingConfig()
    stages: "OrderedDict[str, np.ndarray]" = OrderedDict()

    gray = to_grayscale(image)
    stages["Grayscale"] = gray

    normalized = normalize(gray)
    stages["Normalized"] = normalized

    background = estimate_background(normalized, config.background_kernel_size)
    stages["Background Estimate"] = background

    corrected = correct_illumination(normalized, background)
    stages["Corrected"] = corrected

    denoised = denoise(corrected, config.denoise_method, config.denoise_kernel_size)
    stages["Denoised"] = denoised

    enhanced = enhance_contrast(
        denoised, config.clahe_clip_limit, config.clahe_tile_grid_size
    )
    stages["Enhanced"] = enhanced

    return stages
