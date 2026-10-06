"""Touching-spot separation via distance-transform + watershed
(spec Section 7.5: "Support distance-transform + watershed for genuinely
touching spots, applied only when the segmentation indicates merged
blobs — record whether it was used for that session").

Applied selectively, not globally: a connected region in the mask is only
split if its distance transform shows more than one distinct local
maximum (more than one spot "center" merged into one blob). A normal
single spot — even one that's a bit irregular or elongated — has exactly
one dominant peak and is left completely untouched. This is what "applied
only when the segmentation indicates merged blobs" means in practice: the
function never forces a split, it only acts where the evidence (multiple
peaks within one connected region) says there's more than one spot there.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from skimage.feature import peak_local_max
from skimage.segmentation import watershed


def separate_touching_blobs(
    mask: np.ndarray, min_distance_px: int = 5
) -> tuple[np.ndarray, bool]:
    """Split genuinely merged blobs in a binary foreground mask.

    Returns (new_mask, was_separation_applied):
    - `new_mask` is `mask` with a thin (1px) boundary carved between any
      two sub-regions the analysis found merged together — so a
      subsequent contour-based extraction sees them as separate regions.
    - `was_separation_applied` is True only if at least one genuine split
      was made; False (with new_mask identical to the input) if every
      connected region in the mask had only one peak, i.e. nothing needed
      separating. Section 7.5 asks this be recorded per session.

    `min_distance_px` is the minimum pixel distance two local maxima must
    be apart to be treated as two different spot centers rather than
    noise in the distance transform — a configurable parameter
    (DetectionConfig.watershed_min_peak_distance_px), never hardcoded.
    """
    if np.count_nonzero(mask) == 0:
        return mask.copy(), False

    # Distance transform: for each foreground pixel, distance to the
    # nearest background pixel. Peaks of this surface are natural
    # candidates for spot centers — the middle of a blob is always
    # farther from the edge than points near its boundary.
    distance = ndi.distance_transform_edt(mask)

    coords = peak_local_max(distance, min_distance=min_distance_px, labels=mask)
    if len(coords) == 0:
        return mask.copy(), False

    markers = np.zeros(mask.shape, dtype=np.int32)
    for marker_id, (y, x) in enumerate(coords, start=1):
        markers[y, x] = marker_id

    # Watershed "floods" from each marker outward across the inverted
    # distance surface (so it floods from each peak toward the edges),
    # constrained to stay within the original mask. Two markers in the
    # same original blob produce two different labels meeting at a ridge
    # line — that ridge is exactly where we want to cut.
    labels = watershed(-distance, markers, mask=mask)

    ridge = _ridge_between_different_labels(labels)
    separation_applied = bool(ridge.any())

    new_mask = mask.copy()
    new_mask[ridge] = 0
    return new_mask, separation_applied


def _ridge_between_different_labels(labels: np.ndarray) -> np.ndarray:
    """Pixels that have a 4-connected neighbor with a different, nonzero
    label — i.e. the boundary between two distinct watershed regions.

    Note this can only ever be nonempty where two DIFFERENT peaks ended up
    adjacent, which only happens when two markers were placed inside what
    was originally one connected blob (a single-peak blob can never
    border a different nonzero label, since there's only one label to
    begin with). That's what makes "ridge.any()" a correct, honest test
    for "was anything actually merged" rather than a guess.

    Implemented with explicit zero-padding (not np.roll) specifically to
    avoid wraparound comparing opposite image edges as if they were
    adjacent — a real correctness bug that would otherwise falsely flag
    edge-touching blobs as merged with something on the far side of the
    image.
    """
    padded = np.pad(labels, 1, mode="constant", constant_values=0)
    height, width = labels.shape
    center = padded[1 : 1 + height, 1 : 1 + width]

    ridge = np.zeros(labels.shape, dtype=bool)
    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        neighbor = padded[1 + dy : 1 + dy + height, 1 + dx : 1 + dx + width]
        differing = (center != 0) & (neighbor != 0) & (center != neighbor)
        ridge |= differing
    return ridge
