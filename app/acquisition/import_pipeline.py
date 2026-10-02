"""Ties acquisition, validation, provenance, and quality analysis into the
single flow every imported image goes through (spec Section 6):

    SOURCE -> VALIDATION -> SHA-256 -> COPY TO data/original/ -> QUALITY ANALYSIS

This is the module the GUI calls — it never talks to FileImportSource,
validation, hashing, or quality_analysis directly, so the sequence is
guaranteed consistent regardless of what calls it (GUI today; the Phase 13
batch importer later; tests).
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.acquisition.image_import import FileImportSource
from app.acquisition.validation import validate_image_array
from app.config.schemas import ImportRecord, LoadedImage, QualityConfig, QualityMetrics
from app.config.settings import ORIGINAL_DIR
from app.image_engine.quality.quality_analysis import analyze_quality
from app.utils.hashing import sha256_file


@dataclass
class ImportResult:
    """Everything produced by importing one image, for the GUI to display."""

    image: np.ndarray
    loaded: LoadedImage
    record: ImportRecord
    quality: QualityMetrics


def import_image(
    path: Path,
    *,
    quality_config: QualityConfig | None = None,
    original_dir: Path | None = None,
) -> ImportResult:
    """Run one image through the full Section 6 import flow.

    `original_dir` defaults to the real data/original/ (overridable for
    tests so they don't write into the real data directory).
    """
    path = Path(path)
    original_dir = original_dir or ORIGINAL_DIR
    original_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load (Phase 1's FileImportSource — extension check + OpenCV decode).
    image, loaded = FileImportSource().load(path)

    # 2. Validate the decoded array itself.
    validate_image_array(image)

    # 3. Hash the original file bytes (not the decoded array) and copy the
    #    untouched original into data/original/, named by hash so repeated
    #    imports of the same file never collide or duplicate storage.
    digest = sha256_file(path)
    stored_path = original_dir / f"{digest}{path.suffix.lower()}"
    already_existed = stored_path.exists()
    if not already_existed:
        shutil.copy2(path, stored_path)

    record = ImportRecord(
        sha256=digest,
        stored_path=stored_path,
        import_timestamp_utc=datetime.now(timezone.utc),
        already_existed=already_existed,
    )

    # 4. Quality analysis on the decoded array.
    quality = analyze_quality(image, quality_config)

    return ImportResult(image=image, loaded=loaded, record=record, quality=quality)
