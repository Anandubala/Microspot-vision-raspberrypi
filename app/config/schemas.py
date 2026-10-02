"""Typed, serializable configuration models (Pydantic).

Schemas are added in the phase that first consumes them, not stubbed out
early with fields nothing reads yet. Phase 1 added LoadedImage (display
only). Phase 2 adds ImportRecord (validation/SHA-256/provenance) and the
quality-analysis models. Detection/segmentation/session-config schemas
follow in the phases that introduce those features.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class LoadedImage(BaseModel):
    """Describes one image that has been loaded through an AcquisitionSource.

    Display-only metadata (Phase 1). Provenance (hash, copy location,
    import time) lives in ImportRecord below, not here, since a LoadedImage
    can exist in memory without ever having been validated or copied yet.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_path: Path
    filename: str
    width: int
    height: int
    channels: int


class ImportRecord(BaseModel):
    """Provenance for one successfully imported image (Phase 2, Section 6).

    Original files are never modified — this records where the untouched
    copy was placed under data/original/, under what hash, and when.
    Persisting this across app restarts (the sessions/images/image_metadata
    tables) is Phase 10; for now it exists only in memory for the current
    run and whatever the GUI displays from it.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    sha256: str
    stored_path: Path
    import_timestamp_utc: datetime
    already_existed: bool  # True if this exact hash was already in data/original/


class QualityConfig(BaseModel):
    """Thresholds for the image-quality diagnostics (Section 1: never
    hardcode a cutoff in the algorithm itself — it lives here instead).

    Defaults are generic starting points, NOT calibrated against your lab's
    actual microscope images — see docs/PHASE_2.md "Known limitations".
    Tune them once you have real sample images with known-good/known-bad
    examples to check against.
    """

    blur_variance_min: float = 100.0  # Laplacian variance below this = blurry
    contrast_std_min: float = 15.0  # intensity std-dev below this = low contrast
    illumination_cv_max: float = 0.25  # grid-mean coefficient of variation above this = uneven
    clipping_fraction_max: float = 0.02  # fraction of pixels at 0 or 255 above this = clipped
    illumination_grid_size: int = 4  # NxN grid for the illumination-uniformity check


class QualityMetrics(BaseModel):
    """Computed, real image-quality diagnostics for one image (Section 1:
    every value here comes from actual computation — nothing fabricated).

    `warnings` lists every threshold this image failed, by name, so a
    reviewer can see exactly why (or whether) an image was flagged —
    never a bare pass/fail with no basis shown.
    """

    blur_variance: float
    contrast_std: float
    illumination_cv: float
    clipped_dark_fraction: float
    clipped_bright_fraction: float
    warnings: list[str]

    @property
    def is_clean(self) -> bool:
        return len(self.warnings) == 0
