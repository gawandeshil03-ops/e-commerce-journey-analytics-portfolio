from __future__ import annotations

import hashlib
from pathlib import Path

from .config import RAW_EVENTS_SHA256


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def validate_events_file(path: Path, verify_checksum: bool = True) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(
            f"Raw events file not found: {path}. "
            "Run `python scripts/download_data.py` first."
        )

    with path.open("r", encoding="utf-8") as file:
        header = file.readline().strip()

    expected_header = "timestamp,visitorid,event,itemid,transactionid"
    if header != expected_header:
        raise ValueError(
            f"Unexpected events.csv header: {header!r}. "
            f"Expected {expected_header!r}."
        )

    checksum = sha256_file(path)
    if verify_checksum and checksum != RAW_EVENTS_SHA256:
        raise ValueError(
            "events.csv checksum does not match the fixed RetailRocket v4 file. "
            f"Expected {RAW_EVENTS_SHA256}, got {checksum}."
        )

    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": checksum,
        "checksum_verified": checksum == RAW_EVENTS_SHA256,
    }
