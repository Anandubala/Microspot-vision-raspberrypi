# Phase 2 — Image Validation, Metadata, SHA-256, Image-Quality Engine

## Objective

Per master spec Section 16: image validation, metadata, SHA-256, and a
real image-quality engine (blur, contrast, illumination, clipping),
wired into the import flow Section 6 describes:
`SOURCE -> VALIDATION -> SHA-256 -> COPY TO data/original/ -> QUALITY ANALYSIS`.

## Architecture / design decisions

- **New `import_pipeline.py` orchestrates the whole flow**, rather than
  stuffing validation/hashing/quality calls into the GUI or into
  `FileImportSource`. The GUI (`MainWindow._load_image`) now calls
  `import_image()` once and gets back one `ImportResult` bundling the
  pixel array, display metadata, provenance record, and quality metrics.
  This is also what the Phase 13 batch importer will call per file.
- **Validation is its own module** (`app/acquisition/validation.py`),
  separate from `FileImportSource`'s existing extension/decode checks,
  because it validates the *decoded array* (dtype, dimensions, channel
  count) rather than the file itself — a different failure class.
- **Quality metrics vs. quality analysis are split into two modules.**
  `image_engine/quality/metrics.py` has pure, independently-testable
  functions that return raw numbers (blur variance, contrast std-dev,
  illumination CV, clipping fractions) with no opinion about what's
  "good." `image_engine/quality/quality_analysis.py` applies
  `QualityConfig`'s thresholds to produce named warnings. This keeps the
  measurements reusable (e.g. for per-ROI quality checks later) separately
  from the configurable pass/fail logic.
- **Thresholds live in `QualityConfig`, not in the metric functions**,
  per spec Section 1 ("never hardcode"). Defaults are generic starting
  points — NOT calibrated against real lab images (see Known Limitations).
- **Original-file copies are named by hash, not by original filename**
  (`data/original/<sha256>.<ext>`), so re-importing the same file is
  idempotent (detected via `ImportRecord.already_existed`, not re-copied)
  and two different files can never collide on name.
- **Persisted provenance is explicitly NOT built yet.** `ImportRecord`
  exists only in memory for the current run. The `sessions`/`images`/
  `image_metadata` SQLite tables are Phase 10 — Phase 2 only needed the
  validate/hash/copy/analyze behavior to exist and be correct, not to
  survive an app restart.
- **16-bit/float image support is explicitly out of scope.**
  `validate_image_array` rejects anything that isn't 8-bit unsigned,
  with a clear error message, rather than silently mishandling it.

## Files created

```
app/acquisition/validation.py
app/acquisition/import_pipeline.py
app/image_engine/quality/metrics.py
app/image_engine/quality/quality_analysis.py
app/gui/quality_panel.py
app/utils/hashing.py
tests/unit/test_hashing.py
tests/unit/test_validation.py
tests/unit/test_quality_metrics.py
tests/unit/test_quality_analysis.py
tests/integration/test_import_pipeline.py
docs/PHASE_2.md
```

## Files modified

```
app/config/schemas.py     — added ImportRecord, QualityConfig, QualityMetrics
app/gui/main_window.py    — now calls import_image() instead of FileImportSource
                             directly; added the QualityPanel to the layout
README.md                 — updated feature list to Phase 2
CHANGELOG.md              — new entry
docs/GLOSSARY.md          — added "Quality warning" entry
```

`app/config/settings.py` and `app/acquisition/image_import.py` are
unchanged from Phase 1 — `FileImportSource` is still exactly what
`import_pipeline.py` calls for the load step.

## Exact commands

**Install / run:** unchanged from Phase 1 (`docs/SETUP_WINDOWS.md` /
`docs/SETUP_RASPBERRY_PI.md`).

**Test:**
```bash
QT_QPA_PLATFORM=offscreen pytest -v
```

## Tests executed

```
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```

## Actual results

```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-8.3.4, pluggy-1.6.0
PySide6 6.8.2 -- Qt runtime 6.8.2 -- Qt compiled 6.8.2
rootdir: /home/claude/microspot_vision
configfile: pyproject.toml
plugins: qt-4.4.0
collecting ... collected 40 items

tests/integration/test_import_pipeline.py::test_import_image_full_flow PASSED
tests/integration/test_import_pipeline.py::test_reimporting_same_file_does_not_duplicate_copy PASSED
tests/integration/test_import_pipeline.py::test_import_rejects_corrupt_file PASSED
tests/unit/test_hashing.py::test_sha256_matches_hashlib_reference PASSED
tests/unit/test_hashing.py::test_sha256_differs_for_different_content PASSED
tests/unit/test_hashing.py::test_sha256_identical_for_identical_content PASSED
tests/unit/test_image_import.py::test_load_png_returns_array_and_metadata PASSED
tests/unit/test_image_import.py::test_load_jpg_returns_array_and_metadata PASSED
tests/unit/test_image_import.py::test_unsupported_extension_raises PASSED
tests/unit/test_image_import.py::test_missing_file_raises PASSED
tests/unit/test_image_import.py::test_corrupt_file_raises_image_load_error PASSED
tests/unit/test_image_viewer.py::test_grayscale_array_converts_to_pixmap PASSED
tests/unit/test_image_viewer.py::test_bgr_array_converts_to_pixmap PASSED
tests/unit/test_image_viewer.py::test_bgra_array_converts_to_pixmap PASSED
tests/unit/test_quality_analysis.py::test_clean_sharp_high_contrast_image_has_no_warnings PASSED
tests/unit/test_quality_analysis.py::test_uniform_flat_image_triggers_blur_and_low_contrast_warnings PASSED
tests/unit/test_quality_analysis.py::test_fully_white_image_triggers_clipped_bright PASSED
tests/unit/test_quality_analysis.py::test_fully_black_image_triggers_clipped_dark PASSED
tests/unit/test_quality_analysis.py::test_strong_gradient_triggers_uneven_illumination PASSED
tests/unit/test_quality_analysis.py::test_custom_config_thresholds_are_respected PASSED
tests/unit/test_quality_metrics.py::test_to_grayscale_passthrough_for_2d PASSED
tests/unit/test_quality_metrics.py::test_to_grayscale_converts_bgr PASSED
tests/unit/test_quality_metrics.py::test_sharp_checkerboard_has_higher_variance_than_blurred PASSED
tests/unit/test_quality_metrics.py::test_uniform_image_has_zero_blur_variance PASSED
tests/unit/test_quality_metrics.py::test_uniform_image_has_zero_contrast PASSED
tests/unit/test_quality_metrics.py::test_half_black_half_white_has_known_std PASSED
tests/unit/test_quality_metrics.py::test_higher_contrast_scores_higher_than_lower_contrast PASSED
tests/unit/test_quality_metrics.py::test_flat_image_has_near_zero_illumination_cv PASSED
tests/unit/test_quality_metrics.py::test_gradient_image_has_higher_cv_than_flat_image PASSED
tests/unit/test_quality_metrics.py::test_black_image_returns_zero_not_divide_by_zero_error PASSED
tests/unit/test_quality_metrics.py::test_clipping_fractions_exact_known_counts PASSED
tests/unit/test_quality_metrics.py::test_no_clipping_returns_zero_zero PASSED
tests/unit/test_quality_metrics.py::test_fully_saturated_image_returns_one_one_component PASSED
tests/unit/test_validation.py::test_valid_grayscale_passes PASSED
tests/unit/test_validation.py::test_valid_bgr_passes PASSED
tests/unit/test_validation.py::test_valid_bgra_passes PASSED
tests/unit/test_validation.py::test_zero_dimension_raises PASSED
tests/unit/test_validation.py::test_empty_array_raises PASSED
tests/unit/test_validation.py::test_non_uint8_dtype_raises PASSED
tests/unit/test_validation.py::test_unsupported_channel_count_raises PASSED

============================== 40 passed in 7.38s ===============================
```

Additionally ran a full-app smoke test (not a mock) loading the real
fixture image through the real `MainWindow`:

```
Status bar: Loaded sample_dots.png — 300x200, 1 channel(s) — quality: clean
Quality panel text:
Quality: CLEAN
  blur variance (higher=sharper): 518.8
  contrast std-dev:                16.4
  illumination CV (lower=flatter): 0.014
  clipped dark / bright fraction:  0.0000 / 0.0000
SHA-256: cabdcc6faff34ff9c622c7518fb77d9f8aec98af992d6f7b5c01a6d50de4c83c

--- data/original contents ---
cabdcc6faff34ff9c622c7518fb77d9f8aec98af992d6f7b5c01a6d50de4c83c.png
```

The SHA-256 matches independently recomputing `hashlib.sha256()` over the
fixture file's bytes (also asserted in
`tests/integration/test_import_pipeline.py`).

## Known limitations

- **Quality thresholds are uncalibrated defaults.** `blur_variance_min=100`,
  `contrast_std_min=15`, `illumination_cv_max=0.25`,
  `clipping_fraction_max=0.02` are reasonable generic starting points, but
  NOT TESTED against your actual lab microscope images. Once you have real
  sample images, run them through and check whether a human-judged "good"
  image gets flagged, or a human-judged "bad" one doesn't — then adjust
  `QualityConfig` defaults in `app/config/schemas.py` accordingly.
- **16-bit or float image data is rejected, not converted.** If your lab's
  camera/scope exports anything other than 8-bit unsigned images,
  `validate_image_array` will raise `InvalidImageError` rather than
  silently rescaling it — a conversion step would need to be added
  deliberately (and documented) rather than guessed at here.
- **No database — ImportRecord doesn't survive an app restart.** You won't
  see "this was already imported on 2026-10-01" after closing and
  reopening the app; only within one run, and only because the file
  already exists on disk under its hash (re-copy is skipped, but the
  original import *time* isn't recalled). That's explicitly Phase 10.
- **Quality panel is a single text block**, not the tabbed
  Quality/Pipeline-stages/Results/Warnings layout from spec Section 12.
  That full layout is assembled incrementally; Phase 3 adds pipeline-stage
  visualization next to it.
- **Illumination-uniformity grid (default 4×4) is a simple, real but
  coarse measure.** It won't catch illumination problems smaller than one
  grid cell. Good enough to flag gross vignetting/gradient issues; not a
  substitute for a proper flat-field correction (which belongs in Phase 3
  preprocessing if your images need it).
- Not tested on actual Raspberry Pi hardware — verified in a Linux
  container with the Phase-1-corrected dependency pins. Same caveat as
  Phase 1: confirm it installs and the quality panel behaves the same way
  on your real Pi.

## Next phase

Phase 3 — Image viewer (zoom/pan/ROI), preprocessing stages, and
intermediate-stage visualization (grayscale, normalized, background
estimate, etc. — each inspectable in the GUI), per master spec Section 16.
