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

## Current feature set (Phase 2)

- PySide6 desktop app skeleton, runs identically on Windows (dev) and
  Raspberry Pi OS (deploy).
- File > Open Image — loads a single image (JPG/JPEG/PNG/BMP/TIFF) via a
  file picker and displays it, scaled to fit the window.
- `AcquisitionSource` interface in place (`app/acquisition/base.py`) so the
  analysis pipeline (from Phase 4 onward) is acquisition-agnostic; a guarded
  Picamera2 stub (`app/acquisition/camera.py`) exists for the Phase 15 live
  camera source but is not implemented yet.
- **Import pipeline** (`app/acquisition/import_pipeline.py`): every opened
  image is validated, SHA-256 hashed, copied untouched into
  `data/original/<hash>.<ext>` (re-imports of the same file are detected
  and not re-copied), and run through real quality diagnostics.
- **Quality diagnostics** (`app/image_engine/quality/`): blur (Laplacian
  variance), contrast (intensity std-dev), illumination uniformity
  (grid-based coefficient of variation), and clipping (dark/bright pixel
  fraction) — every value actually computed from the image, with named
  warnings (`BLURRY`, `LOW_CONTRAST`, `UNEVEN_ILLUMINATION`,
  `CLIPPED_DARK`, `CLIPPED_BRIGHT`) shown in a panel under the viewer.

Not yet implemented (later phases — see `docs/PHASE_2.md` "Next Phase" and
the master spec): preprocessing, segmentation/detection, filtering,
watershed separation, validation datasets, database persistence,
reporting, and everything past Phase 2 in the phase list.

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
