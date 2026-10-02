# Phase 1 — Project Foundation

## Objective

Per master spec Section 16: repo + venv on both machines, PySide6 skeleton
app, basic file-picker image load & display. First git push/pull
round-trip verified Windows → Pi (procedure documented below; actual
round-trip happens once this is pushed to your GitHub repo and pulled on
the Pi — not something this environment can execute for you).

## Architecture / design decisions

- **`AcquisitionSource` protocol built now, not deferred.** Even though
  Section 6 marks camera capture out of scope for this build, the
  interface itself (`app/acquisition/base.py`) is built in Phase 1 so
  `FileImportSource` is written against it from day one, rather than
  refactored into it later. `PiCameraSource` (`app/acquisition/camera.py`)
  is a guarded stub that raises `NotImplementedError`.
- **SHA-256 hashing and copying into `data/original/` deliberately NOT
  implemented yet.** That's Phase 2 (image validation/metadata). Phase 1's
  `FileImportSource.load()` reads the file and returns pixel data + basic
  dimensions only — it does not copy or hash anything.
- **`ImageViewer` has no zoom/pan/ROI.** Phase 3 scope. Phase 1's viewer
  only scales the pixmap to fit the widget on resize.
- **Config schema (`LoadedImage`) is intentionally minimal.** No detection
  or session-config schemas were added yet — those belong to the phases
  that actually consume them (avoids stub fields nothing reads).

## Files created

```
.gitignore
requirements.txt
pyproject.toml
README.md
CHANGELOG.md
run.py
app/__init__.py
app/main.py
app/config/__init__.py
app/config/settings.py
app/config/schemas.py
app/gui/__init__.py
app/gui/main_window.py
app/gui/image_viewer.py
app/acquisition/__init__.py
app/acquisition/base.py
app/acquisition/image_import.py
app/acquisition/camera.py
app/models/__init__.py
app/database/__init__.py
app/evaluation/__init__.py
app/reporting/__init__.py
app/workers/__init__.py
app/utils/__init__.py
app/image_engine/__init__.py
app/image_engine/quality/__init__.py
app/image_engine/preprocessing/__init__.py
app/image_engine/segmentation/__init__.py
app/image_engine/detection/__init__.py
app/image_engine/filtering/__init__.py
app/image_engine/separation/__init__.py
app/image_engine/calibration/__init__.py
app/image_engine/visualization/__init__.py
tests/__init__.py
tests/conftest.py
tests/unit/__init__.py
tests/unit/test_image_import.py
tests/unit/test_image_viewer.py
tests/integration/__init__.py
tests/evaluation/__init__.py
tests/fixtures/sample_dots.png
tests/fixtures/sample_dots.jpg
docs/SETUP_WINDOWS.md
docs/SETUP_RASPBERRY_PI.md
docs/GLOSSARY.md
docs/PHASE_1.md
```

`app/image_engine/*` and `app/models/`, `app/database/`, `app/evaluation/`,
`app/reporting/`, `app/workers/` are empty packages (just `__init__.py`) —
scaffolded per the Section 15 file structure but not yet populated; they
belong to Phase 4 onward.

## Files modified

None — this is the first phase, everything above is new.

## Exact commands

**Install:**
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Run:**
```bash
python run.py
```

**Test:**
```bash
pytest
# or, headless (no display attached):
QT_QPA_PLATFORM=offscreen pytest
```

## Tests executed

Ran in this environment (Linux container, Python 3.12.3, offscreen Qt
platform — same command works on Windows/Pi with a real display):

```
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```

## Actual results

```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-8.2.2, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
PySide6 6.7.2 -- Qt runtime 6.7.2 -- Qt compiled 6.7.2
rootdir: /home/claude/microspot_vision
configfile: pyproject.toml
plugins: qt-4.4.0
collecting ... collected 8 items

tests/unit/test_image_import.py::test_load_png_returns_array_and_metadata PASSED [ 12%]
tests/unit/test_image_import.py::test_load_jpg_returns_array_and_metadata PASSED [ 25%]
tests/unit/test_image_import.py::test_unsupported_extension_raises PASSED [ 37%]
tests/unit/test_image_import.py::test_missing_file_raises PASSED         [ 50%]
tests/unit/test_image_import.py::test_corrupt_file_raises_image_load_error PASSED [ 62%]
tests/unit/test_image_viewer.py::test_grayscale_array_converts_to_pixmap PASSED [ 75%]
tests/unit/test_image_viewer.py::test_bgr_array_converts_to_pixmap PASSED [ 87%]
tests/unit/test_image_viewer.py::test_bgra_array_converts_to_pixmap PASSED [100%]

============================== 8 passed in 0.35s ===============================
```

Additionally ran a headless smoke test constructing the real `MainWindow`
and driving its actual `_load_image()` path (not a mock) against the
synthetic fixture image:

```
MainWindow constructed and shown OK: MicroSpot Vision v1.0.0
Status bar after load: Loaded sample_dots.png — 300x200, 1 channel(s)
```

(One harmless stderr line from the offscreen Qt platform —
`This plugin does not support propagateSizeHints()` — is a known
offscreen-platform quirk, not an application error; expect it not to
appear when running with a real display on Windows or the Pi.)

## Known limitations

- No image validation, SHA-256 hashing, or quality diagnostics yet — raw
  `cv2.imread` only. A malformed-but-decodable image (e.g. truncated
  sensor data that OpenCV still parses) will load without warning.
- No zoom/pan/ROI in the viewer.
- No database, no session persistence — closing the app discards
  everything.
- Only single-file import; batch/zip import is Phase 13.
- The git push/pull round-trip between Windows and the Pi itself has not
  been executed from this environment — it requires your actual GitHub
  remote and physical Pi. Do this manually once you've reviewed the code:
  `git init && git add -A && git commit -m "Phase 1: project foundation" && git push`,
  then `git clone`/`git pull` on the Pi and re-run the test/run commands
  above there.
- Not tested on actual Raspberry Pi hardware or real Windows — verified in
  a Linux container with an offscreen Qt platform. Pi-specific apt
  dependencies (Section 1 of `docs/SETUP_RASPBERRY_PI.md`) are
  best-effort based on known PySide6/Pi OS requirements and may need
  adjustment on your actual Pi OS version — NOT TESTED on real hardware.

## Correction (2026-10-02)

The original Phase 1 pins (`PySide6==6.7.2` and matching numpy/opencv/etc.
versions) failed to install on the actual Raspberry Pi: its Python is
3.13, and `PySide6==6.7.2`'s metadata requires `<3.13`. Re-verified every
pin against live PyPI data and Raspberry Pi OS's actual Python version:

- Bumped `PySide6` to `6.8.2` (`Requires-Python <3.14,>=3.9` — confirmed
  via PyPI metadata) and every numpy/scipy/opencv/pandas/scikit-image/
  SQLAlchemy/pydantic/pytest pin to versions confirmed to ship official
  manylinux **aarch64** wheels for **cp313**, not just x86_64/cp312 —
  checked file-by-file against PyPI's JSON API, not assumed.
- Removed `picamera2` from `requirements.txt` entirely. Testing the
  install (not just reading about it) showed its `python-prctl` dependency
  has no prebuilt wheel and fails to *build* without the `libcap` system
  dev headers — this would have broken the Pi install a second time right
  after the PySide6 fix. It's unused in Phase 1 code anyway (guarded stub
  only); `docs/SETUP_RASPBERRY_PI.md` now documents installing it via
  `apt` in Phase 15 instead, which is also the only way to get the
  matching `libcamera` bindings.
- Re-ran the full test suite (same 8 tests) and the headless app smoke
  test against the new pins in a clean virtualenv — both passed identically
  to the original run; nothing in Phase 1's code depends on
  numpy/opencv/pydantic APIs that changed between the old and new pins.
- Still NOT verified: actual install and launch on your physical Pi. The
  new pins are checked against live PyPI metadata for Python 3.13 +
  aarch64 specifically (your reported environment), which is a much
  stronger check than before, but I don't have your hardware to confirm
  the apt packages in Section 1 are complete for your exact Pi OS image.

## Next phase

Phase 2 — Image validation, metadata, SHA-256, image-quality engine
(blur, contrast, illumination, clipping diagnostics), per master spec
Section 16.
