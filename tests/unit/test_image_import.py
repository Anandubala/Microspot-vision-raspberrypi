from pathlib import Path

import numpy as np
import pytest

from app.acquisition.image_import import (
    FileImportSource,
    ImageLoadError,
    UnsupportedImageFormatError,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_load_png_returns_array_and_metadata():
    source = FileImportSource()
    image, metadata = source.load(FIXTURES / "sample_dots.png")

    assert isinstance(image, np.ndarray)
    assert metadata.filename == "sample_dots.png"
    assert metadata.width == 300
    assert metadata.height == 200
    assert metadata.channels == 1  # grayscale fixture


def test_load_jpg_returns_array_and_metadata():
    source = FileImportSource()
    image, metadata = source.load(FIXTURES / "sample_dots.jpg")

    assert isinstance(image, np.ndarray)
    assert metadata.filename == "sample_dots.jpg"
    assert metadata.width == 300
    assert metadata.height == 200


def test_unsupported_extension_raises():
    source = FileImportSource()
    with pytest.raises(UnsupportedImageFormatError):
        source.load(FIXTURES / "sample_dots.gif")


def test_missing_file_raises():
    source = FileImportSource()
    with pytest.raises(FileNotFoundError):
        source.load(FIXTURES / "does_not_exist.png")


def test_corrupt_file_raises_image_load_error(tmp_path):
    bad_file = tmp_path / "corrupt.png"
    bad_file.write_bytes(b"not a real png")

    source = FileImportSource()
    with pytest.raises(ImageLoadError):
        source.load(bad_file)
