# Changelog

## Phase 3 — Zoom/pan/ROI viewer, preprocessing pipeline (2026-10-02)

- `app/gui/image_viewer.py` — rewritten on `QGraphicsView`/`QGraphicsScene`:
  mouse-wheel zoom (clamped), drag-to-pan, toggleable rectangular ROI
  selection (`clamp_roi`, pure/tested), `fit_to_window()`. Replaces the
  Phase 1 QLabel-based viewer.
- `app/image_engine/preprocessing/stages.py` — real, independently-tested
  `normalize`, `estimate_background`, `correct_illumination`, `denoise`
  (gaussian/median), `enhance_contrast` (CLAHE).
- `app/image_engine/preprocessing/pipeline.py` — `run_preprocessing_pipeline()`
  runs all stages in Section-7 order and returns every named intermediate.
- `app/config/schemas.py` — added `PreprocessingConfig`.
- `MainWindow` — added a stage-selector toolbar (switches the viewer
  between Original/Grayscale/Normalized/Background Estimate/Corrected/
  Denoised/Enhanced), ROI toggle + clear buttons, Fit to Window button.
- Found and fixed two real bugs via testing: `normalize()` returned the
  wrong dtype on a flat/zero-range input (broke `correct_illumination`),
  and a float-precision off-by-one left `normalize()`'s max value at 254
  instead of 255 — see `docs/PHASE_3.md`.
- 29 new tests (69 total), all passing, plus a full-app smoke test driving
  every stage switch and a real ROI select/clear cycle through the actual
  widgets.

## Phase 2 — Image validation, metadata, SHA-256, quality engine (2026-10-02)

- `app/acquisition/validation.py` — validates the decoded image array
  (dtype, dimensions, channel count) before anything downstream touches it.
- `app/utils/hashing.py` — streamed SHA-256 file hashing.
- `app/acquisition/import_pipeline.py` — ties load -> validate -> hash ->
  copy to `data/original/<hash>.<ext>` -> quality analysis into one
  `import_image()` call; idempotent on re-import of the same file.
- `app/image_engine/quality/metrics.py` — real, independently-tested
  blur (Laplacian variance), contrast (std-dev), illumination uniformity
  (grid coefficient of variation), and clipping-fraction computations.
- `app/image_engine/quality/quality_analysis.py` — applies `QualityConfig`
  thresholds to produce named warnings (`BLURRY`, `LOW_CONTRAST`,
  `UNEVEN_ILLUMINATION`, `CLIPPED_DARK`, `CLIPPED_BRIGHT`).
- `app/config/schemas.py` — added `ImportRecord`, `QualityConfig`,
  `QualityMetrics`.
- `app/gui/quality_panel.py` + `MainWindow` — displays the real computed
  metrics and warnings under the image viewer after each load.
- 32 new tests (40 total), all passing — see `docs/PHASE_2.md`.

## Phase 1 — dependency fix (2026-10-02)

- `requirements.txt` pins were built on this container's Python 3.12 and
  broke on the Pi's actual Python 3.13 (`PySide6==6.7.2` requires `<3.13`).
  Re-pinned every dependency to versions confirmed via live PyPI data to
  ship aarch64 wheels for cp313.
- Removed `picamera2` from `requirements.txt` — its `python-prctl`
  dependency fails to build without `libcap` system headers. Moved to an
  apt-install instruction for Phase 15 in `docs/SETUP_RASPBERRY_PI.md`.
- See `docs/PHASE_1.md` "Correction" section for the full account.

## Phase 1 — Project foundation (2026-09-29)

- Repository structure created per master spec Section 15.
- `requirements.txt` / `pyproject.toml` — pinned, cross-platform
  (Picamera2 guarded to Linux via `sys_platform` marker).
- `AcquisitionSource` protocol (`app/acquisition/base.py`) and
  `FileImportSource` (`app/acquisition/image_import.py`) — single-image
  load via file picker, no SHA-256/validation yet (Phase 2).
- Guarded `PiCameraSource` stub (`app/acquisition/camera.py`) —
  `NotImplementedError`, deferred to Phase 15.
- PySide6 skeleton: `MainWindow` (File > Open Image, status bar) and
  `ImageViewer` (scaled display, no zoom/pan/ROI yet — Phase 3).
- `app/config/settings.py` and `app/config/schemas.py` — project paths,
  supported formats, `LoadedImage` model.
- Unit tests for image import and the numpy→QPixmap conversion path
  (8 tests, all passing — see `docs/PHASE_1.md`).
- Docs: README, SETUP_WINDOWS, SETUP_RASPBERRY_PI, GLOSSARY, this file.
