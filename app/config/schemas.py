"""Typed, serializable configuration models (Pydantic).

Schemas are added in the phase that first consumes them, not stubbed out
early with fields nothing reads yet. Phase 1 added LoadedImage (display
only). Phase 2 adds ImportRecord (validation/SHA-256/provenance) and the
quality-analysis models. Detection/segmentation/session-config schemas
follow in the phases that introduce those features.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
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


class PreprocessingConfig(BaseModel):
    """Thresholds/parameters for the Phase 3 preprocessing stages (Section 7:
    NORMALIZATION -> BACKGROUND/ILLUMINATION CORRECTION -> DENOISING ->
    CONTRAST ENHANCEMENT). Never hardcoded in the stage functions themselves.
    """

    background_kernel_size: int = 51  # odd; large-kernel blur used as the background estimate
    denoise_method: str = "gaussian"  # "gaussian" | "median"
    denoise_kernel_size: int = 5  # odd
    clahe_clip_limit: float = 2.0
    clahe_tile_grid_size: int = 8  # NxN tiles


class DetectionPolarity(str, Enum):
    """Spec Section 7.1. AUTO is resolved per-image by
    detection.classical_cv.determine_polarity — never a random guess, but a
    real (simple, documented) measurement of image statistics.
    """

    DARK_ON_LIGHT = "DARK_ON_LIGHT"
    BRIGHT_ON_DARK = "BRIGHT_ON_DARK"
    AUTO = "AUTO"


class SegmentationMethod(str, Enum):
    """Spec Section 7.2. Exactly one runs per image — never all three —
    and whichever ran is recorded (Section 10's provenance requirement,
    fully persisted once Phase 10's database exists).
    """

    OTSU = "OTSU"
    ADAPTIVE_MEAN = "ADAPTIVE_MEAN"
    ADAPTIVE_GAUSSIAN = "ADAPTIVE_GAUSSIAN"


class DetectionConfig(BaseModel):
    """Segmentation + candidate-extraction parameters (Sections 7.1-7.3).
    Nothing here is hardcoded into the detection functions themselves.

    `detector_backend` exists now (Section 8: "the active detector is
    chosen in configuration... stored per session") even though only
    "classical_cv" is implemented — ONNXDetector (Phase 14) will read the
    same field.
    """

    polarity: DetectionPolarity = DetectionPolarity.DARK_ON_LIGHT
    segmentation_method: SegmentationMethod = SegmentationMethod.OTSU
    adaptive_block_size: int = 35  # must be odd; used by both adaptive methods
    adaptive_c: int = 5  # constant subtracted from the adaptive threshold
    min_area_px: float = 1.0  # noise floor only — NOT the Phase 5 size-rejection rule
    detector_backend: str = "classical_cv"  # "classical_cv" | "onnx" (Phase 14)
    local_contrast_ring_px: int = 3  # width of the surrounding ring sampled for local_contrast
    enable_watershed_separation: bool = True  # Section 7.5 — off disables Phase 6 entirely
    watershed_min_peak_distance_px: int = 5  # min pixel gap between two spot "centers" to
    # treat them as separate during touching-spot separation (see separation/watershed.py).
    # Generic default — too small risks over-splitting noise, too large risks under-splitting
    # genuinely close spots. NOT calibrated against real images; tune once you have them.


class EdgeState(str, Enum):
    """Spec Section 7.4. An objective geometric fact about a candidate's
    bounding box relative to the frame — computed at extraction time and
    never changed by filtering policy. COMPLETE means the bounding box
    doesn't touch the image border; PARTIAL means it does (the candidate's
    true extent may be cut off by the frame edge, so its area/shape
    features may be unreliable).

    EDGE_EXCLUDED is NOT a value this enum ever takes. It is one of the
    possible `rejection_reason` strings a filtering rule can attach to a
    PARTIAL candidate — see FilterConfig.exclude_edge_candidates and
    docs/PHASE_5.md "design decisions" for why the exclusion decision is
    kept separate from the geometric fact.
    """

    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"


class FilterConfig(BaseModel):
    """Thresholds for candidate filtering (Section 7.4). Every value here
    is a configurable cutoff, never hardcoded in the filtering logic
    itself (Section 1). Defaults are generic starting points — see
    docs/PHASE_5.md "Known limitations" — not calibrated against your lab's
    real images.

    Filtering rules are applied in a fixed, documented order (see
    filtering/filters.py); a candidate failing more than one rule is
    reported with the FIRST rule it fails, not a list of all of them —
    matching the spec's "a candidate carries an explicit reason" (singular).
    """

    # Lowered from an initial guess of 10.0 after real-world input (lab
    # assistant, 2026-10-05): real spots may be as small as ~2-3px diameter
    # (area ~3-7 px²), which the old default would have silently rejected
    # as AREA_TOO_SMALL. 2.0 is a deliberately permissive placeholder, not
    # a calibrated value — it exists so tiny real spots aren't thrown away
    # by default while this gets properly tuned against real sample images
    # (see docs/PHASE_5.md "Addendum").
    min_area_px: float = 2.0
    max_area_px: float | None = None  # None = no upper bound
    # Section 7.3 "Multi-scale / size handling" explicitly calls out BOTH
    # area and diameter as configurable size bounds. Area-based filtering
    # (above) is the primary, always-active size gate; these diameter
    # bounds are an additional, OPTIONAL gate (None = disabled by default)
    # for when a reviewer finds it more natural to reason in "this spot is
    # N pixels across" terms — exactly how the lab assistant described
    # spot sizes (e.g. "2 pixels", "3 pixels" — diameter, not area).
    min_diameter_px: float | None = None
    max_diameter_px: float | None = None
    min_circularity: float = 0.3  # 0-1; 1.0 is a perfect circle
    min_solidity: float = 0.5  # 0-1; area / convex-hull area
    max_aspect_ratio: float = 3.0  # >=1.0; long/short bbox side ratio
    min_local_contrast: float = 10.0  # intensity units, 0-255 scale
    exclude_edge_candidates: bool = False  # reject PARTIAL (frame-touching) candidates


class Candidate(BaseModel):
    """One detected region, from raw extraction through filtering
    (Section 7.4) — a *candidate* until `rejection_reason` is confirmed
    None, never implicitly a validated spot or a biological claim
    (Section 1).

    Phase 4 had only centroid/bbox/area/contour. Phase 5 adds every other
    feature Section 7.4 lists (perimeter, circularity, aspect ratio,
    intensity statistics, local contrast, equivalent diameter, solidity,
    extent, edge state) plus `rejection_reason`, set by filtering — never
    at extraction time, since extraction doesn't know the filter config.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int
    centroid_x: float
    centroid_y: float
    bbox_x: int
    bbox_y: int
    bbox_w: int
    bbox_h: int
    area: float
    contour: list[tuple[int, int]]  # polygon points, plain ints for JSON export later

    perimeter: float
    circularity: float  # 4*pi*area / perimeter^2; 1.0 = perfect circle
    aspect_ratio: float  # >=1.0; longer bbox side / shorter bbox side
    mean_intensity: float
    min_intensity: float
    max_intensity: float
    local_contrast: float  # |mean inside the blob - mean in the ring just outside it|
    equivalent_diameter: float  # diameter of a circle with the same area
    solidity: float  # area / convex-hull area; 1.0 = fully convex
    extent: float  # area / bounding-box area
    edge_state: EdgeState

    rejection_reason: str | None = None  # None until filtering runs; see FilterConfig

    @property
    def is_validated(self) -> bool:
        return self.rejection_reason is None


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
