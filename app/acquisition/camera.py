"""Raspberry Pi Camera acquisition — deferred to Phase 15.

Picamera2 is Linux-only and is not installed on the Windows dev machine
(see requirements.txt's sys_platform marker). The import is guarded here
so simply importing this module never crashes the app on Windows; it only
fails if someone actually tries to *use* PiCameraSource before Phase 15
implements it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from app.config.schemas import LoadedImage

try:
    if sys.platform.startswith("linux"):
        from picamera2 import Picamera2  # type: ignore[import-not-found]
    else:
        Picamera2 = None  # type: ignore[assignment]
except ImportError:
    Picamera2 = None  # type: ignore[assignment]


class PiCameraSource:
    """Live Raspberry Pi Camera capture. NOT IMPLEMENTED — Phase 15.

    Will implement the same AcquisitionSource interface as
    FileImportSource (app/acquisition/image_import.py) once built, so the
    analysis pipeline requires no changes to accept live camera frames.
    """

    def load(self, path: Path) -> tuple[np.ndarray, LoadedImage]:
        raise NotImplementedError(
            "PiCameraSource is not implemented yet (deferred to Phase 15). "
            "Use FileImportSource for image acquisition in this build."
        )
