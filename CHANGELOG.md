# Changelog

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
