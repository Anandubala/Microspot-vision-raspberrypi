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

**What none of the above mean:** "microorganism," "colony," "CFU," or any
biological diagnosis. The system performs image-based feature detection
and quantification — nothing more is claimed unless a controlled
validation (Section 9.1) or annotation-based accuracy figure (Section 9.2)
backs it up, and even then only against the stated basis and sample size.
