# Changelog

## Phase 7 — Performance, UI responsiveness, layout, oversized false positives (2026-10-06)

Prompted by real feedback after testing on an actual lab image (~9,800
candidates) — three distinct, real problems, not synthetic concerns:

- **Performance bug fixed**: `candidate_extraction.py`'s per-candidate
  intensity/local-contrast computation allocated a full-image-sized array
  for EVERY candidate. On an image with thousands of candidates this was
  the dominant cost behind a reported ~1-1.5 minute UI freeze. Rewrote to
  use a small local crop per candidate instead. Measured: a comparable
  ~8,700-candidate synthetic stress test now completes in ~0.55s (this
  function alone) / ~1.9s (full pipeline) on dev hardware, down from an
  estimated 13+ seconds for this function alone with the old code.
- **UI freeze fixed properly, not just made faster**: added
  `AnalysisWorker(QThread)` so preprocessing/detection/filtering run off
  the GUI thread, per spec Section 12's own (previously unfollowed)
  instruction. The original image and quality results now display
  immediately after import; an indeterminate progress bar runs during
  analysis instead of the window appearing frozen.
- **Splitter collapse bug fixed**: `setChildrenCollapsible(False)` on
  every splitter, explicit minimum heights on the quality/results panels,
  and the two panels moved into their own side-by-side horizontal
  splitter (was stacked vertically) — fixes a reported bug where dragging
  a splitter handle could make the results panel disappear with no way to
  resize it back.
- **Oversized false-positive gap fixed**: `FilterConfig.max_diameter_px`
  now defaults to 20.0px (was `None` — no upper bound at all). A real lab
  image showed large, roughly circular structures (tens to ~150px across)
  passing every filtering rule, since circularity/solidity alone favor
  round shapes regardless of size. Verified directly: 3 large synthetic
  blobs (diameter 119-169px) are correctly rejected as
  `DIAMETER_TOO_LARGE`. Also found, as a secondary finding: Phase 3's
  background-correction preprocessing already suppresses large,
  gradual-contrast blobs before detection even sees them in some cases —
  the new diameter cap is a deliberate, direct safety net for whatever
  doesn't get caught that way, not a replacement for it.
- Fixed 8 tests whose fixtures (20-80px blobs) were incidentally above the
  new 20px diameter default and started failing for the wrong reason
  (`DIAMETER_TOO_LARGE` pre-empting the rule each test actually meant to
  isolate) — either shrunk the fixture or explicitly set
  `max_diameter_px=None` to isolate the rule under test, per test.
- 4 new tests (146 total): real-thread load/busy-state verification,
  a guard against starting a second analysis while one is running, and
  splitter-non-collapsibility checks.

## Phase 6 — Multi-scale config, touching-spot separation, lab-assistant feedback (2026-10-05)

Prompted by real feedback from the lab assistant: count dark spots only,
report each spot's size in pixels, and separate spots that are stuck
together before counting them.

- `app/gui/results_panel.py` — added a per-spot pixel-size listing (area +
  equivalent diameter), matching the "Validated Spots" overlay's numbering.
- `app/config/schemas.py` — `FilterConfig.min_area_px` default lowered
  from 10.0 to 2.0 after learning real spots may be only 2-3px diameter
  (area ~3-7px²) — the old default would have silently rejected them.
  Added optional `min_diameter_px`/`max_diameter_px` (Section 7.3,
  disabled by default). Added `DetectionConfig.enable_watershed_separation`
  and `watershed_min_peak_distance_px`.
- `app/image_engine/separation/watershed.py` — new: distance-transform +
  watershed touching-spot separation, applied only to blobs with genuine
  evidence of multiple merged centers (never forces a split).
- `app/image_engine/detection/classical_cv.py` — `segment_and_extract()`
  now runs separation BEFORE extraction (not after filtering, despite the
  spec diagram's literal order — see docs/PHASE_6.md "design decisions"
  for why) and returns a 3-tuple including whether separation was applied.
- `app/image_engine/filtering/filters.py` — added `DIAMETER_TOO_SMALL`/
  `DIAMETER_TOO_LARGE` rejection reasons.
- `MainWindow` / `ResultsPanel` — show whether touching-spot separation
  ran this session (Section 7.5's "record whether it was used").
- 13 new tests (142 total), all passing. Verified on a real touching-spots
  scenario end to end through the actual GUI: two overlapping dark circles
  correctly separate into 2 validated spots (vs. 1 with separation
  disabled) — see `docs/PHASE_6.md`.

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
