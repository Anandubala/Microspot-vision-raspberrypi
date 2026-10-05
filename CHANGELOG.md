# Changelog

## Phase 5 — Candidate filtering, rejection reasons, validated overlay (2026-10-04)

- `app/config/schemas.py` — extended `Candidate` with the full Section 7.4
  feature set (perimeter, circularity, aspect_ratio, mean/min/max
  intensity, local_contrast, equivalent_diameter, solidity, extent,
  edge_state, rejection_reason); added `EdgeState` and `FilterConfig`.
- `app/image_engine/detection/candidate_extraction.py` — rewritten to
  compute every new feature from the mask + original grayscale image
  (signature changed: now takes `gray` and a `DetectionConfig`).
- `app/image_engine/filtering/filters.py` — `filter_candidates()` applies
  6 rules in a fixed, documented order, each a named rejection reason;
  `validated_count()`.
- `app/image_engine/visualization/overlays.py` — added
  `draw_validated_overlay()`: green numbered outlines for validated
  candidates, orange unlabeled outlines for rejected ones.
- `app/gui/results_panel.py` — new panel: validated count, raw/rejected
  counts, rejection-reason breakdown, "NO VALID SPOTS DETECTED" when zero.
- `MainWindow` — runs filtering after detection; adds "Validated Spots" to
  the stage selector; status bar and toolbar now show validated (not just
  raw) count.
- 28 new tests (129 total), all passing. Verified on the Phase 1 fixture
  (8/8 candidates validated, zero false rejections) and a new mixed-quality
  synthetic image (3 round dots validated, 1 elongated bar correctly
  rejected as `LOW_CIRCULARITY`, 1 sub-pixel noise speck never even
  extracted as a candidate) — see `docs/PHASE_5.md`.

## Phase 4 — Segmentation + connected-components candidate detection (2026-10-03)

- `app/config/schemas.py` — added `DetectionPolarity`, `SegmentationMethod`,
  `DetectionConfig`, `Candidate`.
- `app/image_engine/segmentation/thresholding.py` — `determine_polarity`
  (AUTO resolved via mean-intensity heuristic, documented as a real but
  limited measurement) and `compute_mask` (Otsu or adaptive thresholding,
  exactly one method per image, per config).
- `app/image_engine/detection/` — `SpotDetector` protocol (Section 8),
  `candidate_extraction.py` (contour-based, with centroid/bbox/area),
  `classical_cv.py` (`ClassicalCVDetector`, implemented), `onnx_detector.py`
  (stub, raises `NotImplementedError`, Phase 14).
- `app/image_engine/visualization/overlays.py` — `draw_candidate_outlines`
  for the unfiltered "Raw Candidates" inspection stage.
- `MainWindow` — runs detection on the Enhanced stage after every load;
  adds "Segmentation Mask" and "Raw Candidates" to the stage selector, plus
  a live raw-candidate count.
- **Found and fixed a real bug via testing**: a perfectly flat
  `BRIGHT_ON_DARK` image made Otsu's threshold degenerate to 0, which
  (combined with non-inverted thresholding) flagged the *entire frame* as
  one false-positive candidate — violating the spec's "zero detections is
  a valid result" principle. Fixed by short-circuiting flat input
  (`gray.min() == gray.max()`) to an empty mask. See `docs/PHASE_4.md`.
- Corrected a wrong test assumption (not a code bug):
  `cv2.contourArea` on a filled 20×20-pixel block returns 361 (19×19, the
  shoelace-formula convention on corner coordinates), not 400 — documented
  and fixed in the test rather than changing the (correct) implementation.
- 32 new tests (101 total), all passing. Full-app smoke test on the Phase
  1 fixture image (built with exactly 8 synthetic dots) found exactly 8
  raw candidates — a real ground-truth check, not just a synthetic one.

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
