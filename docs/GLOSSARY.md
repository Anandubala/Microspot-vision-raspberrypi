# Glossary

Terms used throughout MicroSpot Vision's UI, reports, and code. Read this
before interpreting any number the app produces — the wording is chosen
deliberately so a result is never misread as a biological claim.

**Candidate / detected feature**
A region the image-processing pipeline flagged as matching the configured
spot criteria (size, shape, contrast, etc.), before any filtering. Not yet
confirmed as anything.

**Validated spot**
A candidate that survived the configured rejection rules (Section 7.4 of
the master spec). Still an image-based detection, not a biological
identification.

**Image-based count**
The number of validated spots in one image, under one specific
configuration. Always reported alongside that configuration (thresholds,
polarity, size range, detector backend) so it's reproducible.

**Spot density**
Validated-spot count normalized by image or ROI area — only meaningful in
physical units (per mm²) once spatial calibration has been performed for
that session; otherwise it's per-pixel-area and labeled as such.

**Rejection reason**
The specific rule a candidate failed (e.g. `AREA_TOO_SMALL`,
`LOW_CIRCULARITY`, `EDGE_EXCLUDED`) — always attached to a rejected
candidate so a reviewer can audit why it didn't count.

**Quality warning** (e.g. `BLURRY`, `LOW_CONTRAST`, `UNEVEN_ILLUMINATION`,
`CLIPPED_DARK`, `CLIPPED_BRIGHT`)
A named flag raised when a computed quality metric crosses its configured
threshold (`QualityConfig`) — e.g. `BLURRY` means the image's Laplacian
variance was below `blur_variance_min`. Not a judgment on the image's
biological content; purely a signal that the detection pipeline (Phase 4
onward) may be less reliable on this particular image.

**Pipeline stage**
One named, inspectable step of preprocessing (`Grayscale`, `Normalized`,
`Background Estimate`, `Corrected`, `Denoised`, `Enhanced`) or later,
segmentation/detection. Viewing a stage in the GUI shows exactly what that
step of the pipeline produced — not a final result, and not yet a count.

**ROI (Region of Interest)**
A rectangular area the user has selected in the viewer. In Phase 3 this is
purely a selection tool (coordinates shown in pixels); it is not yet used
to restrict analysis or compute physical measurements — that requires
spatial calibration (Section 10), added in Phase 9.

**Raw candidate overlay**
The "Raw Candidates" pipeline stage: every detected region outlined on the
image, unfiltered and unnumbered. Shows what segmentation + extraction
found before Phase 5's filtering exists — not a reviewer-facing final
count, and candidates here can include noise, debris, or artifacts that
filtering will later reject.

**Rejected candidate**
A candidate whose `rejection_reason` is not `None` — it failed one of the
configured filtering rules (Section 7.4). Shown in orange, unlabeled, in
the "Validated Spots" overlay, and counted (by reason) in the results
panel. Not discarded silently — every rejection is visible and explained.

**NO VALID SPOTS DETECTED**
The exact result when zero candidates pass filtering (or zero were
detected at all). Per spec Section 1, this is always shown as a clearly
labeled, valid result — never implied to mean "sterile" or "clean."

**Touching-spot separation**
A distance-transform + watershed step that splits a single detected blob
into two or more spots when the blob's shape shows clear evidence of more
than one spot merged together (two distinct "centers" close together).
Applied selectively — a normal single spot is never split. Whether it ran
for a given image is shown in the results panel (Section 7.5).

**Diameter cap**
A configured upper bound (`FilterConfig.max_diameter_px`) on how large a
validated spot can be, measured as equivalent diameter in pixels. Added
after a real lab image showed large, roughly circular structures
(out-of-focus cells, debris, or similar — not the target spots) passing
every other filtering rule, since circularity and solidity alone favor
round shapes regardless of actual size.

**What none of the above mean:** "microorganism," "colony," "CFU," or any
biological diagnosis. The system performs image-based feature detection
and quantification — nothing more is claimed unless a controlled
validation (Section 9.1) or annotation-based accuracy figure (Section 9.2)
backs it up, and even then only against the stated basis and sample size.
