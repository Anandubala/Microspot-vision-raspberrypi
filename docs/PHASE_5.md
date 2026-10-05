# Phase 5 — Candidate Feature Extraction, Filtering, Validated Overlay

## Objective

Per master spec Section 16: candidate feature extraction, filtering with
explainable rejection reasons, validated count + numbered overlay.
Section 7.4 in full: every candidate carries centroid, bbox, area,
perimeter, circularity, aspect ratio, mean/min/max intensity, local
contrast, equivalent diameter, solidity, extent, and edge-proximity state;
rejections carry an explicit reason.

## Architecture / design decisions

- **`extract_candidates()`'s signature changed**: it now takes `gray` (the
  original grayscale image) alongside `mask`, because intensity
  statistics and local contrast are meaningless without the actual pixel
  values — a mask alone only tells you shape. This is a breaking change to
  an internal Phase 4 function; every call site (`classical_cv.py`, all
  tests) was updated. Phase 4's own "Known limitations" section already
  flagged this as coming in Phase 5, so it isn't a surprise reversal.
- **`rejection_reason` lives on `Candidate` but is only ever set by
  filtering, never by extraction.** Extraction doesn't know about
  `FilterConfig` and shouldn't need to — keeping the two concerns
  separate means you can re-run filtering with different thresholds
  against the same extracted candidates without re-running detection.
- **Filtering rules run in a fixed order and report only the FIRST
  failing rule**, not every rule a candidate happens to violate. The
  spec's own example (Section 7.4) shows a single reason per candidate
  ("REJECTED: AREA_TOO_SMALL"), not a list — matched here. The order
  (AREA → CIRCULARITY → SOLIDITY → ASPECT_RATIO → LOCAL_CONTRAST → EDGE)
  runs the cheapest, most decisive check first: a tiny noise speck is
  almost always caught on area alone, long before circularity would even
  be numerically meaningful for it.
- **`EdgeState` is a pure geometric fact (COMPLETE/PARTIAL), never
  computed as `EDGE_EXCLUDED`.** The spec lists `EDGE_EXCLUDED` as one
  possible value of the edge-proximity feature, but making a "feature"
  depend on `FilterConfig.exclude_edge_candidates` would blur the line
  between an objective measurement and a policy decision. Here,
  `edge_state` always just says whether the bounding box touches the
  frame; `EDGE_EXCLUDED` only ever appears as a `rejection_reason` string,
  assigned by filtering when that config flag is on. The practical result
  is identical to the spec's description; the implementation keeps
  measurement and policy separable.
- **`local_contrast` is a new, real metric**: `|mean intensity inside the
  candidate - mean intensity in a configurable-width ring immediately
  outside it|`. This is distinct from Phase 2's `QualityMetrics.
  contrast_std` (a whole-image statistic) — `local_contrast` asks "does
  THIS candidate actually stand out from ITS immediate surroundings,"
  which is what should gate whether a detection is real versus background
  noise that happened to cross the segmentation threshold.
- **The numbered overlay's numbering is detection-order, not spatial
  order.** Candidates are numbered 1..N in the order `extract_candidates`
  produced them (OpenCV's contour-finding order), not sorted
  left-to-right or top-to-bottom. Stated explicitly in the overlay
  function's docstring and here, so nobody reads a spatial pattern into
  numbers that don't have one. Sorting by position would be a reasonable
  future improvement but wasn't necessary for this phase's PHASE_5
  objective.
- **`filter_candidates()` returns a new list rather than mutating in
  place** (`Candidate.model_copy(update=...)`), so a caller holding a
  reference to the raw Phase 4 candidates isn't surprised by their
  `rejection_reason` changing out from under them.

## Files created

```
app/image_engine/filtering/filters.py
app/gui/results_panel.py
tests/unit/test_filters.py
docs/PHASE_5.md
```

## Files modified

```
app/config/schemas.py                        — extended Candidate; added EdgeState, FilterConfig;
                                                 added DetectionConfig.local_contrast_ring_px
app/image_engine/detection/candidate_extraction.py — rewritten: full feature set, new signature
app/image_engine/detection/classical_cv.py    — updated call site for the new extract_candidates() signature
app/image_engine/visualization/overlays.py    — added draw_validated_overlay()
app/gui/main_window.py                        — runs filtering; adds "Validated Spots" stage;
                                                 adds ResultsPanel to the layout
tests/unit/test_candidate_extraction.py       — rewritten for new signature + 13 new feature tests
tests/unit/test_overlays.py                   — updated call site + 4 new draw_validated_overlay tests
README.md, CHANGELOG.md, docs/GLOSSARY.md     — updated for Phase 5
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
collecting ... collected 129 items

[... all 129 tests ...]

============================== 129 passed in 0.51s ===============================
```

28 new this phase: 13 feature tests added to `test_candidate_extraction.py`
(aspect ratio, intensity stats, local contrast — both a real dark-on-light
case and a "blob matches background" near-zero case, solidity including a
concave-vs-solid comparison, extent, equivalent diameter, edge state both
ways), 11 in the new `test_filters.py` (one test per rejection reason, rule
non-mutation, validated_count), and 4 new overlay tests (green pixels
present for validated, orange-not-green for rejected, empty-candidate
cases for both overlay functions).

One test assertion was corrected during this phase (not a code bug): a
new `extent` test initially asserted `> 0.95` for a filled square, but
`extent = contourArea / bbox_area`, and `contourArea`'s shoelace-formula
convention (documented in Phase 4) gives `361/400 = 0.9025` for a 20×20
block — a real, correctly-computed value. Adjusted the assertion to
`> 0.85` with an explanatory comment rather than changing the
(correct) implementation.

Additionally ran two real end-to-end checks, not just unit assertions:

**1. The Phase 1 fixture image** (`tests/fixtures/sample_dots.png`, 8 known
synthetic dots) through the full GUI load path:

```
Status: Loaded sample_dots.png — 300x200, 1 channel(s) — quality: clean — validated: 8 (raw: 8)
Candidate count label:  Raw candidates: 8  |  Validated: 8

Results panel:
Validated count: 8  (image-based count — see docs/GLOSSARY.md)
Raw candidates: 8  |  Rejected: 0

Stage selector items: ['Original', 'Grayscale', 'Normalized', 'Background Estimate', 'Corrected', 'Denoised', 'Enhanced', 'Segmentation Mask', 'Raw Candidates', 'Validated Spots']
Switched to Validated Spots stage: OK
```

All 8 known dots pass filtering cleanly with the default `FilterConfig` —
zero false rejections on a clean synthetic image.

**2. A new mixed-quality synthetic image** (3 round dots + 1 elongated bar
+ 1 sub-pixel noise speck), run through the real `segment_and_extract()` +
`filter_candidates()` call path:

```
raw: 4 validated: 3
  id=1 area=1500.0 circularity=0.18 aspect=13.73 -> LOW_CIRCULARITY
  id=2 area=174.0 circularity=0.80 aspect=1.00 -> None
  id=3 area=174.0 circularity=0.80 aspect=1.00 -> None
  id=4 area=174.0 circularity=0.80 aspect=1.00 -> None
```

The 3 round dots validated correctly; the elongated bar was correctly
rejected (circularity 0.18, well below the default 0.3 — and would also
have failed aspect ratio at 13.73, but circularity runs first per the
documented rule order, so that's the reason shown); the single-pixel
noise speck never even became a candidate — Otsu's threshold didn't pick
it up as foreground at all, which is itself a reasonable outcome for
something that faint.

## Known limitations

- **Filter thresholds are generic defaults**, same caveat as Phase 2's
  quality thresholds and Phase 4's detection parameters:
  `min_area_px=10`, `min_circularity=0.3`, `min_solidity=0.5`,
  `max_aspect_ratio=3.0`, `min_local_contrast=10.0` are reasonable
  starting points, NOT calibrated against your actual lab images. Once
  you have real samples, check whether a human-judged "real spot" gets
  rejected or an obvious artifact passes, and tune `FilterConfig`
  accordingly.
- **No GUI control for `FilterConfig` (or `DetectionConfig`) yet** — same
  limitation carried from Phase 4. Both are hardcoded to defaults in
  `MainWindow`. An analysis-controls panel exposing these (spec Section
  12) is a reasonable next addition, independent of the phase numbering.
- **Overlay numbering is detection order, not spatial order** (see design
  decisions above) — if you need numbers that read left-to-right or
  top-to-bottom for a reviewer, that's a small, deliberately-deferred
  enhancement to `draw_validated_overlay`, not implemented here.
- **No touching-spot separation still** — two overlapping dots remain one
  low-solidity candidate, likely rejected by `LOW_SOLIDITY` or
  `LOW_CIRCULARITY` rather than counted as two. That's exactly what Phase
  6 (watershed separation) exists to fix.
- **No persistence** — `FilterConfig`, rejection reasons, and the
  validated count all live only in the current run, same as every
  previous phase's config. Phase 10's database is still where this
  becomes durable, auditable history.
- Not tested on actual Raspberry Pi hardware — same caveat as every
  previous phase.

## Next phase

Phase 6 — Multi-scale config, touching-spot separation (watershed), edge
handling, per master spec Section 16. This is also the natural point to
reconsider whether `EdgeState`/`exclude_edge_candidates` need any
refinement once touching-spot separation changes what a "candidate at the
edge" can look like.
