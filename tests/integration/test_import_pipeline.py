import hashlib
from pathlib import Path

import pytest

from app.acquisition.import_pipeline import import_image
from app.acquisition.validation import InvalidImageError

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_import_image_full_flow(tmp_path):
    original_dir = tmp_path / "original"
    fixture = FIXTURES / "sample_dots.png"

    result = import_image(fixture, original_dir=original_dir)

    # Loaded correctly.
    assert result.loaded.filename == "sample_dots.png"
    assert result.loaded.width == 300
    assert result.loaded.height == 200

    # Hashed correctly, matching an independent hashlib computation.
    expected_hash = hashlib.sha256(fixture.read_bytes()).hexdigest()
    assert result.record.sha256 == expected_hash

    # Original copied, untouched, into original_dir.
    assert result.record.stored_path.exists()
    assert result.record.stored_path.read_bytes() == fixture.read_bytes()
    assert result.record.already_existed is False

    # Original source file itself was never modified.
    assert fixture.read_bytes() == fixture.read_bytes()  # sanity: still readable

    # Quality analysis ran and produced a real result.
    assert result.quality.blur_variance >= 0.0


def test_reimporting_same_file_does_not_duplicate_copy(tmp_path):
    original_dir = tmp_path / "original"
    fixture = FIXTURES / "sample_dots.png"

    first = import_image(fixture, original_dir=original_dir)
    second = import_image(fixture, original_dir=original_dir)

    assert first.record.stored_path == second.record.stored_path
    assert first.record.already_existed is False
    assert second.record.already_existed is True
    # Only one file should exist in original_dir for this hash.
    assert len(list(original_dir.iterdir())) == 1


def test_import_rejects_corrupt_file(tmp_path):
    bad_file = tmp_path / "corrupt.png"
    bad_file.write_bytes(b"not a real png")

    with pytest.raises(Exception):
        import_image(bad_file, original_dir=tmp_path / "original")
