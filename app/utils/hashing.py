"""File hashing utilities."""
from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 1024 * 1024  # 1 MiB


def sha256_file(path: Path) -> str:
    """Compute the SHA-256 hex digest of a file's bytes on disk.

    Streams the file in chunks rather than reading it all into memory at
    once, since lab frame-sequence dumps (Section 6, Phase 13) may be large.
    """
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()
