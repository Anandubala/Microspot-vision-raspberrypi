# Phase 4 — Segmentation + Connected-Components Candidate Detection

## Objective

Per master spec Section 16: segmentation + connected-components candidate
detection, classical CV, tuned for small dark spots. Sections 7.1–7.4 and
Section 8 (ML-ready `SpotDetector` interface, built now, implemented
classically, stubbed for ONNX).

## Architecture / design decisions

- **`determine_polarity` resolves AUTO via a single, documented heuristic**:
  compare mean intensity to the 0–255 midpoint. This is explicitly a
  simple, honestly-limited measurement — stated in the code and here, not
  papered over — not a sophisticated multi-modal analysis. It will be
  wrong for images that are roughly balanced between foreground and
  background coverage; for this project's sample images (small spots on a
  large flat background), mean intensity tracks background polarity
  reliably.
- **Exactly one segmentation method runs per image** (`compute_mask`),
  matching Section 7.2 ("never run every method simultaneously"). Which
  one is recorded in `DetectionConfig.segmentation_method` — full
  persisted provenance is Phase 10, but the config object itself already
  carries this.
- **Candidate extraction uses `cv2.findContours` rather than
  `connectedComponentsWithStats`.** Both algorithms find the same
  connected foreground regions; `findContours` was chosen because it
  returns each region's boundary polygon directly (needed anyway for the
  outline overlay and for Phase 5's circularity/perimeter calculations),
  avoiding a second pass or a separate contour-finding call just for
  display.
- **`Candidate` is intentionally minimal this phase**: centroid, bounding
  box, area, raw contour polygon. Circularity, solidity, intensity
  statistics, edge-proximity state, and rejection reasons (Section 7.4)
  are added in Phase 5, once filtering exists to consume them — adding
  unused fields now would be exactly the kind of premature stub this
  project's own conventions reject.
- **`min_area_px` in `DetectionConfig` defaults to 1.0 — a noise floor,
  not Phase 5's size filter.** It exists only to drop literally
  zero/negative-area degenerate contours; the real, explainable,
  rejection-reason-tracked size filtering is a deliberately separate,
  later concern (Section 7.3/7.4).
- **GUI shows raw candidates, never implies they're validated.** The
  stage is labeled "Raw Candidates" (not "Spots" or "Count"), and the
  status bar says "raw candidates" explicitly — Section 1's requirement
  that a detected feature never be presented as more than that.

## Bugs found and fixed (via actually running the tests)

**1. Flat-image false positive (real bug, fixed).** A perfectly flat
`BRIGHT_ON_DARK` test image (zero dots — a legitimate "nothing here"
case) came back with ONE candidate covering the entire 300×300 frame
instead of zero. Root cause, confirmed by direct reproduction:

```python
>>> img = np.full((300,300), 30, dtype=np.uint8)
>>> ret, mask = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
>>> ret
0.0
>>> np.count_nonzero(mask)
90000   # the entire image
```

Otsu's algorithm has no bimodal histogram to split on a flat image, so its
computed threshold degenerates to 0. Combined with non-inverted
thresholding (`BRIGHT_ON_DARK`), every pixel with value > 0 then becomes
foreground — the whole frame. This isn't a hypothetical: it would have
shown up the first time anyone pointed the app at a blank field-of-view
image and gotten "1 candidate, the whole picture" instead of the correct
"0 candidates." Fixed by short-circuiting `compute_mask` to return an
empty mask whenever `gray.min() == gray.max()` — a flat image has no
local contrast, so zero detections is the only honest answer (Section 1:
"Zero detections is a valid result"). A flat image should also already
carry Phase 2's `LOW_CONTRAST` quality warning, which is the right place
for a reviewer to see *why* nothing was found.

**2. Wrong test assumption, not a code bug.** A test asserted that a
filled 20×20-pixel square should have `contourArea() == 400` (the literal
pixel count). The actual, correct OpenCV behavior:

```python
>>> cv2.contourArea(square_contour)
361.0   # (20-1) * (20-1), the shoelace-formula area of the boundary corners
```

`cv2.contourArea` computes the polygon area from the contour's corner
coordinates (the shoelace formula), which for an axis-aligned filled
rectangle is systematically `(w-1)*(h-1)`, not `w*h` — standard,
documented OpenCV behavior. The test's expectation was wrong, not the
code. Fixed the assertion (to 361, with an explanatory comment) rather
than changing the implementation, since `contourArea` paired with
`arcLength` on the same contour is the standard basis for Phase 5's
circularity calculation (`4π·area/perimeter²`) — switching to a raw pixel
count now would create an inconsistency to unwind later.

Both are documented here rather than silently patched, per Section 16:
"Never say everything works unless it was actually tested and the output
is shown."

## Files created

```
app/config/schemas.py additions: DetectionPolarity, SegmentationMethod, DetectionConfig, Candidate
app/image_engine/segmentation/thresholding.py
app/image_engine/detection/base.py
app/image_engine/detection/candidate_extraction.py
app/image_engine/detection/classical_cv.py
app/image_engine/detection/onnx_detector.py
app/image_engine/visualization/overlays.py
tests/unit/test_thresholding.py
tests/unit/test_candidate_extraction.py
tests/unit/test_overlays.py
tests/integration/test_classical_cv_detector.py
docs/PHASE_4.md
```

## Files modified

```
app/gui/main_window.py  — runs segment_and_extract() on the Enhanced stage
                           after every load; adds "Segmentation Mask" and
                           "Raw Candidates" to the stage selector; shows a
                           live raw-candidate count in the toolbar and
                           status bar
README.md               — updated feature list to Phase 4
CHANGELOG.md             — new entry
docs/GLOSSARY.md         — added "Raw candidate overlay" entry
```

## Exact commands

**Install / run:** unchanged from Phase 1.

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
collecting ... collected 101 items

[... all 101 tests ...]

============================== 101 passed in 0.44s ===============================
```

32 new this phase: 9 in `test_thresholding.py` (including the two flat-image
regression tests for Bug 1), 7 in `test_candidate_extraction.py`, 2 in
`test_overlays.py`, and 14 parametrized/integration cases in
`test_classical_cv_detector.py` — including synthetic images with a
**known exact dot count** (0, 1, 5, 12 dots, both polarities, both
segmentation methods, AUTO polarity resolution) verified end to end
through the real `ClassicalCVDetector`.

Additionally ran a full-app smoke test on the actual Phase 1 fixture image
(`tests/fixtures/sample_dots.png`), which was built with exactly 8
synthetic dots:

```
Status: Loaded sample_dots.png — 300x200, 1 channel(s) — quality: clean — raw candidates: 8
Candidate count label:  Raw candidates: 8
Stage selector items: ['Original', 'Grayscale', 'Normalized', 'Background Estimate', 'Corrected', 'Denoised', 'Enhanced', 'Segmentation Mask', 'Raw Candidates']
  stage 'Segmentation Mask': OK, image size (300, 200)
  stage 'Raw Candidates': OK, image size (300, 200)
```

The detector found exactly 8 candidates on an image with exactly 8 known
dots — real ground-truth agreement, not just a synthetic assertion.

## Known limitations

- **AUTO polarity is a single mean-intensity heuristic.** It will misjudge
  images that are roughly balanced between foreground and background
  coverage. Explicit `DARK_ON_LIGHT`/`BRIGHT_ON_DARK` configuration avoids
  this entirely; AUTO is a convenience, not a robust classifier.
- **No GUI control for `DetectionConfig` yet.** Polarity, segmentation
  method, and thresholds are all hardcoded to `DetectionConfig()` defaults
  in `MainWindow`. An analysis-controls panel (spec Section 12) to expose
  these is not yet built — would be a reasonable addition before or during
  Phase 5 when filtering parameters need the same kind of exposure.
- **Detection parameters are NOT tuned against your actual lab images.**
  `adaptive_block_size=35`, `adaptive_c=5` are generic defaults. The
  Otsu path (the current GUI default) is parameter-free and more robust
  for a first pass, but verify against your own samples once you have
  them.
- **No touching-spot separation.** Two overlapping dots are currently
  extracted as one candidate with a larger area — watershed separation is
  Phase 6.
- **No rejection reasons, no filtering.** Every raw candidate is shown,
  including anything that's clearly noise or an artifact. Phase 5 adds
  circularity/size/intensity-based filtering with an explicit reason
  attached to every rejection.
- Not tested on actual Raspberry Pi hardware — same caveat as every
  previous phase.

## Next phase

Phase 5 — Candidate feature extraction, filtering with explainable
rejection reasons, validated count + numbered overlay, per master spec
Section 16.
