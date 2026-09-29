"""Application-wide settings.

Cross-platform on purpose: every path is built with pathlib relative to the
project root, so this file behaves identically on the Windows dev machine
and the Raspberry Pi deployment target. Nothing here hardcodes a drive
letter, a POSIX-only path, or a platform-specific separator.
"""
from __future__ import annotations

from pathlib import Path

# Project root = two levels up from this file (app/config/settings.py -> project root)
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

DATA_DIR: Path = PROJECT_ROOT / "data"
ORIGINAL_DIR: Path = DATA_DIR / "original"
PROCESSED_DIR: Path = DATA_DIR / "processed"
SESSIONS_DIR: Path = DATA_DIR / "sessions"
EXPORTS_DIR: Path = DATA_DIR / "exports"
REPORTS_DIR: Path = DATA_DIR / "reports"

DATABASE_PATH: Path = DATA_DIR / "microspot_vision.db"

APP_NAME: str = "MicroSpot Vision"
APP_VERSION: str = "1.0.0"
PIPELINE_VERSION: str = "SpotCV-0.3"

# Image formats accepted by the file picker / batch import (Section 6).
SUPPORTED_IMAGE_EXTENSIONS: tuple[str, ...] = (
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tif",
    ".tiff",
)


def ensure_data_dirs() -> None:
    """Create the gitignored data/* subdirectories if they don't exist yet.

    Safe to call on every startup; a fresh `git clone` on either machine
    will not have these directories present since they are gitignored
    (spec Section 4.1).
    """
    for directory in (
        ORIGINAL_DIR,
        PROCESSED_DIR,
        SESSIONS_DIR,
        EXPORTS_DIR,
        REPORTS_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)
