from __future__ import annotations

import hashlib
from pathlib import Path

from .errors import VerificationError


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(path: Path, expected_size: int, expected_sha256: str) -> None:
    if not path.is_file():
        raise VerificationError(f"Required file is missing: {path.name}")
    size = path.stat().st_size
    if size != expected_size:
        raise VerificationError(f"File size check failed for {path.name} (expected {expected_size}, got {size}).")
    actual = sha256_file(path)
    if actual.lower() != expected_sha256.lower():
        raise VerificationError(f"SHA-256 check failed for {path.name}.")
