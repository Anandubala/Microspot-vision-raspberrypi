# Phase 6 — Multi-Scale Config, Touching-Spot Separation, Real-World Feedback

## Objective

Per master spec Section 16: multi-scale config, touching-spot separation
(watershed), edge handling. This phase also incorporates the first real
feedback from the lab assistant (2026-10-05), relayed through Anandu, which
mapped directly onto this phase's own planned scope.

## What the lab assistant asked for, and how it maps to this phase

Her feedback, as relayed:
1. Count the black (dark) spots in the image.
2. Report spot size in pixels — e.g. "this one is 2 pixels, that one is 3
   pixels."
3. Remove white-patch artifacts from the count.
4. Spots that are stuck together need to be separated and counted
   individually.

Mapping each to the codebase:

1. **Already correct.** `DetectionConfig.polarity` already defaults to
   `DARK_ON_LIGHT` (Section 7.1's own stated default, chosen for exactly
   this kind of image). No change needed.
2. **A real gap — fixed this phase.** `Candidate.area` and
   `Candidate.equivalent_diameter` have existed since Phase 5, but nothing
   displayed them. Added a per-spot listing to `ResultsPanel` (see below).
3. **Already handled by the existing polarity-based segmentation** — with
   `DARK_ON_LIGHT` thresholding, bright/white regions are classified as
   background and never become candidates in the first place. No code
   change was needed for this specifically, but see "Open questions for
   the lab assistant" below — there's a scenario this doesn't cover.
4. **This phase's main deliverable.** Exactly spec Section 7.5's
   touching-spot separation, now validated against a real-world-shaped
   scenario (see "Actual results" below), not just a hypothetical spec
   requirement.

## A calibration risk caught before it became a problem

Doing the pixel-size math on what she described: a 2px-diameter spot has
an area of `π×(1)² ≈ 3.1 px²`; a 3px spot is `π×(1.5)² ≈ 7.1 px²`. The
`FilterConfig.min_area_px` default at the start of this phase was 10.0 —
an arbitrary placeholder from before any real sizing information existed.
Both of her example spot sizes would have been silently rejected as
`AREA_TOO_SMALL` under that default. Lowered to 2.0 now — still a
placeholder, not a calibrated value, but one that won't throw away
genuinely small real spots while this gets properly tuned against actual
lab images. Flagged prominently rather than quietly changed, since a
threshold change like this can silently alter results for anyone who
already ran the app against real images before this fix.

## Architecture / design decisions

- **Separation runs BEFORE candidate extraction, not after filtering** —
  a deliberate deviation from the literal order in the spec's Section 7
  pipeline diagram (`...CANDIDATE FILTERING -> TOUCHING-SPOT SEPARATION
  -> VALIDATION...`). Reasoning: if a merged blob were filtered first,
  it could easily be rejected outright — two touching circles have much
  lower solidity and circularity than either circle alone — before ever
  getting the chance to be split into two legitimate candidates. Splitting
  first means each resulting sub-spot gets its own accurate feature set
  (its own circularity, solidity, area — not the merged blob's), and
  filtering then judges each one honestly on its own merits. The
  practical outcome (correct final count) is what the spec is actually
  after; the exact micro-ordering of internal pipeline stages in a
  diagram is reasonably interpreted as a conceptual overview rather than
  a literal call-order mandate — especially since getting this ordering
  "wrong" the spec's way would actively break the stated goal (separate
  AND count them separately).
- **Separation is selective, driven by evidence, never forced.**
  `separate_touching_blobs` only ever modifies a region if the distance
  transform shows more than one local maximum within it. A single
  (possibly irregular or elongated) spot has one dominant peak and passes
  through completely unchanged. This was verified directly, not assumed:
  `test_single_isolated_circle_is_not_split` and
  `test_well_separated_dots_are_not_falsely_split_by_watershed` confirm
  zero change in output for non-merged input, including re-running the
  full existing Phase 4/5 known-dot-count tests (0/1/5/12 well-separated
  dots) unaffected by this change.
- **Implementation uses `scipy.ndimage` + `skimage.feature`/`skimage.
  segmentation`**, not a hand-rolled watershed — these are exactly the
  libraries spec Section 5's stack table names for this purpose
  ("Scientific CV: scikit-image — Watershed, morphology, region props").
- **The boundary-detection helper explicitly avoids `np.roll`**, which
  wraps around array edges — comparing pixels on the left edge of the
  image to pixels on the right edge as if they were neighbors. This is a
  real correctness bug class, not a hypothetical one; the implementation
  uses explicit zero-padding instead, which cannot produce false
  cross-image-edge "boundaries."
- **`min_distance_px` is configurable, not hardcoded**, as a single
  example test in `test_watershed.py` demonstrates directly: the exact
  same two-overlapping-circles image is NOT split with
  `min_distance_px=100` (peaks within 100px of each other are treated as
  one spot center) but IS split with `min_distance_px=5` — proving the
  parameter genuinely controls behavior, not just existing as an unused
  config field.
- **`FilterConfig.min_diameter_px`/`max_diameter_px` are opt-in (default
  `None`), not replacing area-based filtering.** Area remains the primary
  size gate (it was already there and already tested); diameter is an
  additional, independent way to express a size cutoff for cases where
  thinking in "N pixels across" is more natural — directly mirroring how
  the lab assistant herself described spot sizes.

## Files created

```
app/image_engine/separation/watershed.py
tests/unit/test_watershed.py
docs/PHASE_6.md
```

## Files modified

```
app/config/schemas.py                          — FilterConfig.min_area_px default
                                                   2.0 (was 10.0); added min/max_diameter_px;
                                                   added DetectionConfig.enable_watershed_separation,
                                                   watershed_min_peak_distance_px
app/image_engine/detection/classical_cv.py     — wired in separate_touching_blobs();
                                                   segment_and_extract() now returns a 3-tuple
app/image_engine/filtering/filters.py          — added DIAMETER_TOO_SMALL/DIAMETER_TOO_LARGE
app/gui/results_panel.py                       — per-spot pixel-size listing; shows whether
                                                   separation was applied
app/gui/main_window.py                         — updated call site for the new 3-tuple return
tests/integration/test_classical_cv_detector.py — updated call site; added 3 new tests
tests/unit/test_filters.py                      — added diameter rejection-reason tests
README.md, CHANGELOG.md, docs/GLOSSARY.md       — updated for Phase 6
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
collecting ... collected 142 items

[... all 142 tests ...]

============================== 142 passed in 1.07s ===============================
```

13 new this phase: 8 in `test_watershed.py` (empty mask, single isolated
circle untouched, two separate circles correctly left as two, two
overlapping circles split into two, three-in-a-row split into three, area
preserved within 10%, `min_distance_px` sensitivity proven both ways,
output stays binary), 3 new integration tests (watershed doesn't alter
well-separated-dot results with or without the feature enabled; a real
two-overlapping-circles scenario is split and counted as 2, versus 1 with
separation explicitly disabled — proving the feature is what made the
difference), and 3 diameter-filter tests.

Additionally ran two full-GUI end-to-end checks, not just unit tests:

**1. The Phase 1 fixture (8 well-separated dots) — confirming zero
regression:**
```
Fixture (well-separated dots): Loaded sample_dots.png — 300x200, 1 channel(s) — quality: clean — validated: 8 (raw: 8)
Touching-spot separation applied: no — no merged blobs were found this run
```

**2. A real touching-spots image** (two overlapping dark circles, built
specifically to match what the lab assistant described) loaded through
the actual `MainWindow._load_image()`:
```
Touching-spots image: Loaded touching_spots.png — 300x150, 1 channel(s) — quality: clean — validated: 2 (raw: 2)

Validated count: 2  (image-based count — see docs/GLOSSARY.md)
Raw candidates: 2  |  Rejected: 0
Touching-spot separation applied: yes — at least one merged blob was split into separate spots

Per-spot pixel size (matches overlay numbering):
  #1: area=1754.0 px²  diameter≈47.3 px  (pixels, not microns — no spatial calibration yet)
  #2: area=1755.0 px²  diameter≈47.3 px  (pixels, not microns — no spatial calibration yet)
```

Two visually merged spots → 2 validated candidates, each with its own
pixel-size measurement — the exact real-world scenario reported.

## Open questions for the lab assistant

These would sharpen the defaults and confirm interpretations rather than
block progress — Anandu, feel free to forward these:

1. **Expected spot size range**: roughly what diameter (in pixels, at
   whatever magnification/resolution you're imaging at) do real spots
   tend to be? This directly calibrates `FilterConfig.min_area_px` /
   `min_diameter_px` — right now they're deliberately permissive
   placeholders, not tuned values.
2. **"White patches" — which scenario?** (a) Bright artifacts physically
   separate from the dark spots (dust, reflections elsewhere in the
   frame) — already excluded automatically by `DARK_ON_LIGHT`
   segmentation, no further work needed. (b) Bright glare/reflection
   *inside or overlapping* a dark spot itself, which could interfere with
   detecting that spot correctly — this would need a different fix
   (preprocessing, not just polarity). Which is it, or is it both?
3. **How many spots are typically stuck together** — just pairs, or
   sometimes clusters of 3 or more? This affects how aggressively
   `watershed_min_peak_distance_px` should be tuned, and whether the
   current approach (which already handles 3-in-a-row, tested above)
   needs anything further.
4. **Always dark-on-light?** Confirming the real lab images are always
   dark spots on a lighter background (never the reverse) — this is
   already the default, just worth confirming it's never wrong for her
   actual dataset.

## Known limitations

- **`watershed_min_peak_distance_px` default (5px) is untuned** against
  real images — same caveat as every threshold introduced so far. Two
  genuinely distinct but very close spots could still be merged into one
  if they're closer than this; conversely a single oddly-shaped spot with
  two faint "bumps" far enough apart could in principle be over-split.
  Neither was observed in any test here, but both are the kind of thing
  only real sample images can properly validate.
- **No GUI control for any of these parameters yet** — `DetectionConfig`
  and `FilterConfig` (including the new watershed/diameter fields) are
  still hardcoded to defaults in `MainWindow`. This is now the single
  most useful next addition for actually tuning against real images
  interactively, independent of the phase numbering.
- **The "white patches" question above is genuinely unresolved** — the
  code handles the straightforward interpretation (bright = background,
  automatically excluded), but if the real issue is glare overlapping
  dark spots, that needs a different, not-yet-built fix.
- **Boundary carved during separation is exactly 1px wide** — for very
  small spots (the 2-3px ones the lab assistant mentioned!), a 1px
  boundary cut could meaningfully shrink or even eliminate a tiny spot's
  remaining area after separation. This is a real interaction between two
  pieces of feedback from the same conversation worth testing once real
  small, touching spots are available — not something synthetic test
  images happened to exercise here (the touching-spot test case above
  used 25px-radius circles, not 2-3px ones).
- Not tested on actual Raspberry Pi hardware — same caveat as every
  previous phase.

## Next phase

Phase 7 — Controlled validation dataset workflow + Precision/Recall/F1
against it (spec Section 9.1), per master spec Section 16. Given the
lab-assistant conversation this phase, it may also be worth pausing before
Phase 7 to add a lightweight GUI panel for adjusting `FilterConfig`/
`DetectionConfig` interactively — purely a suggestion, not a decision made
here, since it's not strictly next in the phase list but would make
answering several of the open questions above much faster once real
images are available.
