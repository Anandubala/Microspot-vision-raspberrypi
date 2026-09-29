"""File-based image import (Phase 1: single file only).

Batch/zip import of frame sequences (spec Section 6, Phase 13) is not
implemented here — this module handles exactly what Phase 1 needs: load
one user-picked image file into memory for display, through the same
AcquisitionSource interface every other acquisition backend will use.

Original files are never modified. Copying into data/original/ with a
SHA-256 hash and import timestamp is a Phase 2 responsibility (image
validation/metadata) and is not implemented here yet.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from app.config.schemas import LoadedImage
from app.config.settings import SUPPORTED_IMAGE_EXTENSIONS


class UnsupportedImageFormatError(ValueError):
    """Raised when a file extension isn't in SUPPORTED_IMAGE_EXTENSIONS."""


class ImageLoadError(RuntimeError):
    """Raised when a file has a supported extension but OpenCV can't decode it."""


class FileImportSource:
    """Loads a single image file from disk via a file-picker-style path."""

    def load(self, path: Path) -> tuple[np.ndarray, LoadedImage]:
        path = Path(path)

        if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
            raise UnsupportedImageFormatError(
                f"'{path.suffix}' is not supported. "
                f"Supported formats: {', '.join(SUPPORTED_IMAGE_EXTENSIONS)}"
            )

        if not path.is_file():
            raise FileNotFoundError(f"No such file: {path}")

        # IMREAD_UNCHANGED preserves the image's actual channel count
        # (grayscale, RGB, or RGBA) instead of forcing a conversion.
        image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise ImageLoadError(f"OpenCV could not decode: {path}")

        height, width = image.shape[:2]
        channels = 1 if image.ndim == 2 else image.shape[2]

        metadata = LoadedImage(
            source_path=path,
            filename=path.name,
            width=width,
            height=height,
            channels=channels,
        )
        return image, metadata
