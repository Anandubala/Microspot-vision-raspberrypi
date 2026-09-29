"""Acquisition source interface.

The analysis pipeline (built from Phase 4 onward) must never know or care
whether an image came from a file picker or, later, a live Raspberry Pi
camera capture. Every acquisition backend implements this same interface
and returns the same data shape.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

import numpy as np

from app.config.schemas import LoadedImage


class AcquisitionSource(Protocol):
    """Something that can produce a validated image + its metadata.

    Implementations: FileImportSource (Phase 1, this phase) and, later,
    PiCameraSource (Phase 15, deferred). Both must return the exact same
    (np.ndarray, LoadedImage) shape so nothing downstream branches on
    acquisition type.
    """

    def load(self, path: Path) -> tuple[np.ndarray, LoadedImage]:
        """Load a single image and return (pixel_array, metadata)."""
        ...
