"""Candidate filtering (spec Section 7.4: "Rejections must carry an
explicit reason, e.g. REJECTED: AREA_TOO_SMALL, REJECTED: LOW_CIRCULARITY").

Rules run in a fixed, documented order (AREA -> DIAMETER (optional,
Section 7.3) -> CIRCULARITY -> SOLIDITY -> ASPECT_RATIO -> LOCAL_CONTRAST
-> EDGE), and a candidate failing more than one is reported with the
FIRST one it fails — matching the spec's "a candidate carries an explicit
reason" (singular), not a list of every rule it happens to violate. The
chosen order runs the cheapest, most decisive checks first (a tiny noise
speck is almost always rejected on area alone, long before its
circularity would even matter).

Diameter: `min_diameter_px` is disabled by default (None) — area is the
primary lower-bound size gate, and min_diameter_px is an additional,
optional one for when a reviewer finds it more natural to reason in
"this spot is N pixels across" terms. `max_diameter_px` DOES default to
a real value (20.0px, since 2026-10-06) — a real lab image showed large
circular structures passing filtering because circularity/solidity alone
favor round shapes regardless of size; nothing was gating the upper
bound at all until then. See docs/PHASE_7.md.
"""
from __future__ import annotations

from app.config.schemas import Candidate, EdgeState, FilterConfig

AREA_TOO_SMALL = "AREA_TOO_SMALL"
AREA_TOO_LARGE = "AREA_TOO_LARGE"
DIAMETER_TOO_SMALL = "DIAMETER_TOO_SMALL"
DIAMETER_TOO_LARGE = "DIAMETER_TOO_LARGE"
LOW_CIRCULARITY = "LOW_CIRCULARITY"
LOW_SOLIDITY = "LOW_SOLIDITY"
HIGH_ASPECT_RATIO = "HIGH_ASPECT_RATIO"
LOW_LOCAL_CONTRAST = "LOW_LOCAL_CONTRAST"
EDGE_EXCLUDED = "EDGE_EXCLUDED"


def _first_failing_rule(candidate: Candidate, config: FilterConfig) -> str | None:
    """Return the first rejection reason this candidate fails, or None if
    it passes every configured rule. Order matters — see module docstring.
    """
    if candidate.area < config.min_area_px:
        return AREA_TOO_SMALL
    if config.max_area_px is not None and candidate.area > config.max_area_px:
        return AREA_TOO_LARGE
    if config.min_diameter_px is not None and candidate.equivalent_diameter < config.min_diameter_px:
        return DIAMETER_TOO_SMALL
    if config.max_diameter_px is not None and candidate.equivalent_diameter > config.max_diameter_px:
        return DIAMETER_TOO_LARGE
    if candidate.circularity < config.min_circularity:
        return LOW_CIRCULARITY
    if candidate.solidity < config.min_solidity:
        return LOW_SOLIDITY
    if candidate.aspect_ratio > config.max_aspect_ratio:
        return HIGH_ASPECT_RATIO
    if candidate.local_contrast < config.min_local_contrast:
        return LOW_LOCAL_CONTRAST
    if config.exclude_edge_candidates and candidate.edge_state == EdgeState.PARTIAL:
        return EDGE_EXCLUDED
    return None


def filter_candidates(
    candidates: list[Candidate], config: FilterConfig | None = None
) -> list[Candidate]:
    """Return a NEW list of candidates, each with `rejection_reason` set
    (or left None if it passed every rule). Does not mutate the input list
    in place, so callers that kept a reference to the raw Phase 4 output
    still see the original, unfiltered candidates.
    """
    config = config or FilterConfig()
    return [
        candidate.model_copy(update={"rejection_reason": _first_failing_rule(candidate, config)})
        for candidate in candidates
    ]


def validated_count(candidates: list[Candidate]) -> int:
    """Count of candidates with no rejection reason — the number spec
    Section 2 calls the "image-based count" for this image/config.
    """
    return sum(1 for c in candidates if c.is_validated)
