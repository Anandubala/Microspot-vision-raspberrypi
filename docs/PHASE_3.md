# Phase 3 — Image Viewer (Zoom/Pan/ROI), Preprocessing, Stage Visualization

## Objective

Per master spec Section 16: image viewer with zoom/pan/ROI, preprocessing
stages, and intermediate-stage visualization in the GUI (Section 7:
"Every intermediate stage ... must be inspectable in the GUI — this is
essential for your reviewers to trust the result and for you to debug").

## Architecture / design decisions

- **Viewer rebuilt on `QGraphicsView`/`QGraphicsScene`**, replacing Phase
  1's `QLabel`. A `QLabel` can scale a pixmap but has no concept of an
  independent zoom level, pan offset, or overlay items — all three are
  needed for ROI drawing and are native to `QGraphicsView`.
- **ROI clamping logic (`clamp_roi`) and zoom clamping (`clamp_zoom_factor`)
  are plain functions with no Qt dependency**, separated from the mouse
  event handlers that call them. This is what makes them unit-testable
  without simulating pixel-accurate mouse drags through a view transform
  that changes with window size (fragile under the offscreen Qt platform
  this environment uses).
- **ROI selection is purely a selection tool in this phase** — it reports
  pixel coordinates in the status bar and via `ImageViewer.get_roi()`, but
  nothing yet reads it. Spec Section 10 ties ROI to calibration and
  physical measurement, which is Phase 9. Wiring ROI into anything
  analytical now would mean guessing at Phase 9's interface.
- **Preprocessing stage functions are pure** (`stages.py`): each takes an
  array (+ config values) and returns an array, no hidden state. The
  pipeline (`pipeline.py`) is just an ordered sequence of calls — this
  keeps each stage independently testable with synthetic images of known
  properties, and keeps the stage dict trivially extensible when Phase 4
  appends segmentation-related stages (mask, candidates, overlay) to the
  same inspectable list.
- **Background estimation uses a single large-kernel Gaussian blur**, not
  morphological opening. Both are standard choices for this; Gaussian blur
  was picked because its only parameter (kernel size) is simpler to reason
  about and expose in `PreprocessingConfig` than a structuring-element
  shape/size pair. This can be swapped later if your real lab images need
  rolling-ball-style morphological background subtraction instead —
  nothing else depends on which method produced "Background Estimate".
- **Stage selector in the GUI is a simple toolbar dropdown**, not the
  Section 12 multi-panel scientific layout yet. Switching stages replaces
  what the viewer shows; it doesn't yet show stages side-by-side. That's a
  layout decision for whichever later phase assembles the full Section 12
  UI, not something to guess at here.

## Bugs found and fixed (via actually running the tests, not inspection)

1. **`normalize()` returned the wrong dtype on a flat/zero-range input.**
   The early-return branch for `hi <= lo` returned `gray.copy()` —
   preserving the *input's* dtype. `correct_illumination()` calls
   `normalize()` with a `float64` ratio array, and a flat correction
   result (common for a uniform test image) hit that branch and silently
   returned `float64` instead of `uint8`, which would have broken display
   and every downstream stage. Fixed by always clipping+rounding+casting
   to `uint8` on that branch too.
2. **Off-by-one in the stretch formula.** `(150-50)*(255/(150-50))`
   computed as `254.99999...` in floating point, and truncating via
   `.astype(np.uint8)` dropped it to 254 instead of the mathematically
   correct 255. Fixed by rounding (`np.rint`) before casting.

Both were caught by `tests/unit/test_preprocessing_stages.py` failing on
the first run — documented here rather than silently fixed, per Section
16 ("never say everything works unless it was actually tested").

## Files created

```
app/image_engine/preprocessing/stages.py
app/image_engine/preprocessing/pipeline.py
tests/unit/test_preprocessing_stages.py
tests/unit/test_preprocessing_pipeline.py
docs/PHASE_3.md
```

## Files modified

```
app/gui/image_viewer.py     — rewritten: QGraphicsView zoom/pan/ROI (was QLabel)
app/gui/main_window.py      — stage selector toolbar, ROI toggle/clear, fit-to-window
app/config/schemas.py       — added PreprocessingConfig
tests/unit/test_image_viewer.py — rewritten for the new viewer's API
README.md                   — updated feature list to Phase 3
CHANGELOG.md                — new entry
docs/GLOSSARY.md            — added "Pipeline stage" and "ROI" entries
```

## Exact commands

**Install / run:** unchanged from Phase 1/2.

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
collecting ... collected 69 items

[... all 69 tests ...]

============================== 69 passed in 0.57s ===============================
```

(29 new this phase: 16 in `test_image_viewer.py` — including
`clamp_roi`/`clamp_zoom_factor` pure-function tests and a full ROI
select/clear lifecycle test driven through the viewer's real internal
handlers — plus 10 in `test_preprocessing_stages.py` and 3 in
`test_preprocessing_pipeline.py`.)

Additionally ran a full-app smoke test driving real widgets, not mocks:
loaded the fixture image, cycled the stage selector through all 7 entries
confirming the viewer updated each time, then toggled the real ROI button,
drew a region through the viewer's actual coordinate-handling path, and
confirmed the status bar and `get_roi()` reported the correct clamped
rectangle:

```
Stage selector items: ['Original', 'Grayscale', 'Normalized', 'Background Estimate', 'Corrected', 'Denoised', 'Enhanced']
  switched to stage: Original OK
  switched to stage: Grayscale OK
  switched to stage: Normalized OK
  switched to stage: Background Estimate OK
  switched to stage: Corrected OK
  switched to stage: Denoised OK
  switched to stage: Enhanced OK
ROI status: ROI selected: x=5, y=5, w=45, h=35 (pixels — not yet used by analysis)
Viewer get_roi(): (5, 5, 45, 35)
After clear: ROI cleared.
```

## Known limitations

- **Wheel-zoom and drag-to-pan are not unit-tested** — they call straight
  into Qt's own `scale()`/`ScrollHandDrag` machinery, which is standard
  framework behavior rather than logic this project owns. The clamping
  math around them (`clamp_zoom_factor`) is tested; the actual
  mouse-wheel-to-pixel-zoom wiring is not, and should be eyeballed once
  you have a real display (Windows or the Pi's own desktop session, not
  SSH).
- **ROI is single-rectangle only**, matching spec Section 10 ("rectangular
  first"). No polygon or multi-ROI support yet, and nothing currently
  consumes the selected ROI.
- **Background estimation (Gaussian-blur based) is unvalidated against
  real microscope illumination patterns.** It will smooth out genuine
  large features if `background_kernel_size` is set too small relative to
  real spot size — tune `PreprocessingConfig.background_kernel_size`
  once you have real lab images.
- **CLAHE defaults (`clip_limit=2.0`, `tile_grid_size=8`) are generic**,
  not tuned to your actual sample images — same caveat as Phase 2's
  quality thresholds.
- Preprocessing always runs on the full image — per-stage caching/lazy
  recomputation isn't implemented, so re-running the pipeline on a large
  batch (Phase 13) will recompute every stage every time. Fine for single
  images; worth revisiting if batch performance becomes a problem on the
  Pi (Phase 12's performance pass).
- Not tested on actual Raspberry Pi hardware or a real display — same
  caveat as Phases 1 and 2.

## Next phase

Phase 4 — Segmentation + connected-components candidate detection
(classical CV, tuned for small dark spots), per master spec Section 16.
