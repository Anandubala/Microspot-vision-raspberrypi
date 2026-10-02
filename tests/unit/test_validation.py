import numpy as np
import pytest

from app.acquisition.validation import InvalidImageError, validate_image_array


def test_valid_grayscale_passes():
    validate_image_array(np.zeros((50, 50), dtype=np.uint8))  # should not raise


def test_valid_bgr_passes():
    validate_image_array(np.zeros((50, 50, 3), dtype=np.uint8))


def test_valid_bgra_passes():
    validate_image_array(np.zeros((50, 50, 4), dtype=np.uint8))


def test_zero_dimension_raises():
    with pytest.raises(InvalidImageError):
        validate_image_array(np.zeros((0, 50), dtype=np.uint8))


def test_empty_array_raises():
    with pytest.raises(InvalidImageError):
        validate_image_array(np.array([], dtype=np.uint8))


def test_non_uint8_dtype_raises():
    with pytest.raises(InvalidImageError):
        validate_image_array(np.zeros((50, 50), dtype=np.float32))


def test_unsupported_channel_count_raises():
    with pytest.raises(InvalidImageError):
        validate_image_array(np.zeros((50, 50, 2), dtype=np.uint8))
