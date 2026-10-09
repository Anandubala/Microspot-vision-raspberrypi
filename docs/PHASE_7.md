# Phase 7 — Real-Lab-Image Feedback Round (Performance, Responsiveness, Layout, Oversized Blobs)

## Why this phase exists

This isn't a spec phase. It's the first time the app ran on a real lab
image (a phase-contrast microscope frame with ~9,800 raw candidates and
5,628 validated), and four real problems surfaced that synthetic test
images never could have:

1. Importing one image took ~1-1.5 minutes and the window showed nothing
   until it finished.
2. Dragging a splitter handle could make the results panel vanish with no
   way to drag it back.
3. Large, roughly circular structures (out-of-focus cells/debris) were
   not being excluded.
4. The user's annotated sketch: blue = tiny black spots to count, red =
   big white irregular patches / big blobs to ignore.

## Problem 1 — The freeze: two separate causes

**Cause A (a real bug): per-candidate full-image allocation.**
`extract_candidates` computed each candidate's intensity statistics and
local contrast by allocating a full-image-sized blank mask, drawing the
one candidate on it, and dilating the whole thing. With thousands of
candidates that is thousands of full-frame allocations, each almost
entirely empty. Fixed by cropping to a small padded box around each
candidate (`_local_intensity_features`). Behavior is identical — all
existing tests pass unchanged.

Measured here (dev container, not a Pi):

| Measurement | Result |
|---|---|
| Old per-candidate approach, 1,947 candidates, 1800x1200 | 2.69s (projected ~13.5s for ~9,800) |
| New extraction, 8,699 candidates, 1800x1200 | 0.55s |
| Full pipeline, ~8,000 candidates, 1800x1200 (preprocessing 0.44s + detection/extraction 1.29s + overlays/filter ~0.14s) | 1.86s total |

**Honest caveat:** your reported 1-1.5 minutes was on a Raspberry Pi 4,
which is several times slower than this container, so the old code's
~13s here is consistent with that. I cannot measure your Pi from here.
Expect the new version to be far faster but not as fast as 1.9s.

**Cause B (an architecture gap): everything ran on the GUI thread.**
Spec Section 12 said to use QThread/QThreadPool; it hadn't been done.
Now `AnalysisWorker(QThread)` runs preprocessing + detection + filtering
and emits one signal carrying plain data back; only `MainWindow`'s slot
touches widgets. After import, the original image, quality panel, and
SHA-256 appear immediately; an indeterminate progress bar and a "running
analysis, please wait..." status message show while the worker runs. The
Open action is disabled while busy, and a second Open is ignored.

## Problem 2 — Splitter collapse

Qt splitters let children collapse to zero size by default, and a
zero-height panel leaves almost nothing to grab to drag it back. Fixes:
`setChildrenCollapsible(False)` on both splitters, `setMinimumHeight(90)`
on the quality and results panels, and (per the user's suggestion) the
two panels now sit side by side in a horizontal splitter under the
viewer, so neither competes for vertical space.

## Problem 3 — Oversized blobs

`FilterConfig.max_diameter_px` was `None`, so nothing bounded the top end
of spot size, and round-and-solid shapes score well on circularity and
solidity regardless of size. Default is now `20.0`.

**Why 20.0:** the lab assistant's example spots were 2-3px; 20 leaves
roughly 7-10x headroom while still far below the ~60-170px structures
seen in the real image. It is a generic placeholder, NOT calibrated.

**Verified:** on a synthetic image with 3 large dark blobs (diameters
169, 139, 119px), `filter_candidates` marks all three
`DIAMETER_TOO_LARGE`.

**An honest surprise:** when I ran the full GUI pipeline on a similar
image, those blobs never became raw candidates at all, because Phase 3's
background correction (divide by a 51px Gaussian-blurred background)
flattens large, gradual features before detection sees them. So on my
synthetic blobs the cap wasn't the thing doing the work. I can't know
whether your real blobs behave the same way (real ones have dark rings
and sharp internal structure, which may survive). That's why the cap
exists as a direct safety net. **The real test is your image.**

## Problem 4 — The annotated sketch

I'm not treating the hand-drawn circles as exact regions (you said not
to). What I took from it:
- Blue: tiny, dark, dot-like specks scattered densely across the image
  are the target. The app already detects these.
- Red: big, irregular or round structures, including large light
  mottled areas, are not targets.

Large light/irregular areas should already be ignored (we only threshold
dark regions, and irregular shapes fail circularity/solidity). Large
round structures are now capped by diameter. What the app cannot yet do
is anything specific to your exact sketch, such as a dark ring around a
light centre.

## Test fixes caused by the new default

8 existing tests started failing because their fixtures (20-80px blobs)
were above the new 20px cap, so `DIAMETER_TOO_LARGE` pre-empted the rule
each test meant to isolate. The tests testing a different rule now set
`max_diameter_px=None` explicitly; happy-path tests shrank their blob to
10x10. No production behavior was weakened to make a test pass.

## Files modified

```
app/image_engine/detection/candidate_extraction.py  — local-crop feature computation
app/config/schemas.py                                — FilterConfig.max_diameter_px default 20.0
app/gui/main_window.py                               — AnalysisWorker, progress bar, side-by-side
                                                       non-collapsible splitters
app/image_engine/filtering/filters.py                — docstring corrected
tests/unit/test_filters.py, tests/unit/test_overlays.py — fixtures adjusted (see above)
README.md, CHANGELOG.md, docs/GLOSSARY.md
```

## Files created

```
tests/integration/test_main_window_threading.py (4 tests)
docs/PHASE_7.md
```

## Exact commands

```bash
QT_QPA_PLATFORM=offscreen pytest -v
```

Result: **146 passed**.

## Known limitations

- **20px cap is a placeholder.** If real spots can exceed ~20px, they'll
  be wrongly rejected as DIAMETER_TOO_LARGE; if big blobs are smaller
  than that, they'll slip through. Needs the lab assistant's real
  expected size range.
- **5,628 validated on your real image is not necessarily wrong** — the
  image genuinely shows thousands of tiny dark specks. But I cannot tell
  from a screenshot whether all of them are real spots versus debris,
  noise, or the dark edges of the big structures. This needs your eyes on
  the Validated Spots stage.
- **Per-spot listing for thousands of spots** makes the results text very
  long. It scrolls, but a summary (size histogram) would read better.
- **No GUI control for detection/filter thresholds yet.** Every
  adjustment so far is a code change; an analysis-controls panel is now
  clearly worth building.
- Not measured on a real Raspberry Pi.

## Next phase

Recommended before Phase 8: an analysis-controls panel (sliders for
max diameter, min area, circularity, polarity) with a Re-run button, so
you can tune against your real image live instead of waiting on code
changes. Then the original plan resumes: controlled validation dataset
(old numbering Phase 7) and manual ground-truth annotation.
