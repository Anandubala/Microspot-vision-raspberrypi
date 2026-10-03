import numpy as np

from app.config.schemas import PreprocessingConfig
from app.image_engine.preprocessing.pipeline import run_preprocessing_pipeline


def _sample_image():
    img = np.full((80, 80, 3), 150, dtype=np.uint8)
    img[30:34, 30:34] = 40  # small dark BGR spot
    return img


def test_pipeline_returns_stages_in_expected_order():
    stages = run_preprocessing_pipeline(_sample_image())
    assert list(stages.keys()) == [
        "Grayscale",
        "Normalized",
        "Background Estimate",
        "Corrected",
        "Denoised",
        "Enhanced",
    ]


def test_all_stages_are_uint8_and_correct_shape():
    image = _sample_image()
    stages = run_preprocessing_pipeline(image)
    expected_shape = image.shape[:2]
    for name, arr in stages.items():
        assert arr.dtype == np.uint8, f"{name} is not uint8"
        assert arr.shape == expected_shape, f"{name} has shape {arr.shape}"


def test_custom_config_is_applied():
    image = _sample_image()
    config = PreprocessingConfig(
        background_kernel_size=15,
        denoise_method="median",
        denoise_kernel_size=3,
        clahe_clip_limit=4.0,
        clahe_tile_grid_size=4,
    )
    # Should run without error and still produce every stage.
    stages = run_preprocessing_pipeline(image, config)
    assert len(stages) == 6
