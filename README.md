# MicroSpot Vision

Offline, Raspberry Pi–native desktop application for image-based microscopic
spot / feature detection and counting. Built as a final-year B.Tech
engineering prototype, demonstrated live to technical reviewers.

**What this is:** a deterministic computer-vision pipeline (with a real,
working extension point for a future trained ML detector) that detects
candidate spots in microscope images, lets the user filter/validate them,
and reports an image-derived count with full parameter provenance.

**What this is not:** a diagnostic tool. A detected spot is a
*candidate / detected feature*, never automatically a microorganism, colony,
or CFU. See [`docs/GLOSSARY.md`](docs/GLOSSARY.md).

## Current feature set (Phase 5)

- PySide6 desktop app skeleton, runs identically on Windows (dev) and
  Raspberry Pi OS (deploy).
- File > Open Image — loads a single image (JPG/JPEG/PNG/BMP/TIFF) via a
  file picker.
- `AcquisitionSource` interface in place (`app/acquisition/base.py`) so the
  analysis pipeline (from Phase 4 onward) is acquisition-agnostic; a guarded
  Picamera2 stub (`app/acquisition/camera.py`) exists for the Phase 15 live
  camera source but is not implemented yet.
- **Import pipeline** (`app/acquisition/import_pipeline.py`): every opened
  image is validated, SHA-256 hashed, copied untouched into
  `data/original/<hash>.<ext>` (re-imports of the same file are detected
  and not re-copied), and run through real quality diagnostics.
- **Quality diagnostics** (`app/image_engine/quality/`): blur, contrast,
  illumination uniformity, and clipping — every value actually computed,
  with named warnings shown in a panel under the viewer.
- **Zoom / pan / ROI viewer** (`app/gui/image_viewer.py`): mouse-wheel zoom,
  drag-to-pan, a toggleable rectangular ROI tool (coordinates shown in the
  status bar — not yet consumed by analysis, that's Phase 9's spatial
  calibration), and a "Fit to Window" button.
- **Preprocessing pipeline with inspectable stages**
  (`app/image_engine/preprocessing/`): every loaded image is run through
  Grayscale → Normalized → Background Estimate → Corrected → Denoised →
  Enhanced (CLAHE), and a toolbar dropdown lets you switch the viewer to
  any stage — per spec Section 7's requirement that every intermediate be
  inspectable.

- **Segmentation + candidate detection**
  (`app/image_engine/segmentation/`, `app/image_engine/detection/`):
  classical CV (Otsu or adaptive thresholding → contour-based extraction),
  with `AUTO`/`DARK_ON_LIGHT`/`BRIGHT_ON_DARK` polarity resolution. Runs on
  the Enhanced stage; "Segmentation Mask" and "Raw Candidates" (outlined,
  unfiltered, unnumbered) are added to the stage selector, with a live raw
  candidate count. The `SpotDetector` interface (Section 8) is in place
  with `ClassicalCVDetector` implemented and `ONNXDetector` stubbed for
  Phase 14.

- **Candidate filtering with explainable rejection reasons**
  (`app/image_engine/filtering/filters.py`): every raw candidate now
  carries a full Section 7.4 feature set (perimeter, circularity, aspect
  ratio, intensity stats, local contrast, equivalent diameter, solidity,
  extent, edge state) and is checked against a `FilterConfig`. A candidate
  that fails is tagged with one explicit reason (`AREA_TOO_SMALL`,
  `LOW_CIRCULARITY`, `LOW_SOLIDITY`, `HIGH_ASPECT_RATIO`,
  `LOW_LOCAL_CONTRAST`, `EDGE_EXCLUDED`) — never silently dropped.
- **"Validated Spots" numbered overlay** (`app/image_engine/visualization/
  overlays.py`): the Section 12 reviewer-facing result — validated
  candidates outlined in green and numbered; rejected ones outlined in
  orange, unlabeled. Added to the stage selector.
- **Results panel** (`app/gui/results_panel.py`): shows the validated
  count, raw count, and a breakdown of how many candidates were rejected
  and why — or a clear "NO VALID SPOTS DETECTED" when the count is zero
  (Section 1: zero is a valid result, never implied to mean "clean").

Not yet implemented (later phases — see `docs/PHASE_5.md` "Next Phase" and
the master spec): multi-scale config exposed in the GUI, touching-spot
separation, validation datasets, database persistence, reporting, and
everything past Phase 5 in the phase list.

## Install & run

See [`docs/SETUP_WINDOWS.md`](docs/SETUP_WINDOWS.md) or
[`docs/SETUP_RASPBERRY_PI.md`](docs/SETUP_RASPBERRY_PI.md) for exact,
platform-specific commands. Short version, both platforms:

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## Tests

```bash
pytest
```

## Documentation

- [`docs/PHASE_1.md`](docs/PHASE_1.md) — this phase's objective, files,
  commands, and actual test output.
- [`docs/GLOSSARY.md`](docs/GLOSSARY.md) — candidate / validated spot /
  image-based count, so no one misreads a result as a biological claim.
- [`CHANGELOG.md`](CHANGELOG.md) — one entry per phase/tag.

## Development workflow

Windows laptop (dev) → GitHub → Raspberry Pi 4B 8GB (deploy/demo), as
described in the master spec Section 4. Tag each completed phase
(`git tag phase-1-complete`) so there's always a working checkpoint to fall
back to or show a reviewer.
