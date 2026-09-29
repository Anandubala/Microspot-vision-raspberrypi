"""Typed, serializable configuration models (Pydantic).

Phase 1 only defines what Phase 1 actually uses: a record describing an
image once it has been loaded through an AcquisitionSource. Detection,
segmentation, and session config schemas are added in the phases that
introduce those features (Phase 2 onward) rather than stubbed out early
with fields nothing reads yet.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class LoadedImage(BaseModel):
    """Describes one image that has been loaded through an AcquisitionSource.

    This is intentionally minimal for Phase 1 (display only). SHA-256
    hashing, import timestamp, and persisted metadata are added in Phase 2
    when the validation/quality-analysis stage is built.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_path: Path
    filename: str
    width: int
    height: int
    channels: int
