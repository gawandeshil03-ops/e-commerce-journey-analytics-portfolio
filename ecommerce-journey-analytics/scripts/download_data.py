from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ecommerce_journey.config import (  # noqa: E402
    RAW_EVENTS_PATH,
    SOURCE_ARCHIVE_SHA256,
    SOURCE_ARCHIVE_URL,
    ensure_directories,
)
from ecommerce_journey.data import sha256_file, validate_events_file  # noqa: E402


def download_archive(destination: Path) -> None:
    request = urllib.request.Request(
        SOURCE_ARCHIVE_URL,
        headers={"User-Agent": "ecommerce-journey-analytics/1.0"},
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        total_bytes = int(response.headers.get("Content-Length", "0"))
        downloaded = 0
        next_report = 25 * 1024 * 1024

        with destination.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                downloaded += len(chunk)
                if downloaded >= next_report:
                    if total_bytes:
                        print(
                            f"Downloaded {downloaded / 1024**2:.0f} / "
                            f"{total_bytes / 1024**2:.0f} MiB"
                        )
                    else:
                        print(f"Downloaded {downloaded / 1024**2:.0f} MiB")
                    next_report += 25 * 1024 * 1024


def extract_events(archive_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        if "events.csv" not in archive.namelist():
            raise ValueError("Archive does not contain events.csv.")

        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = destination.with_suffix(".csv.part")
        with archive.open("events.csv") as source, temporary_path.open("wb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)
        temporary_path.replace(destination)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and verify RetailRocket dataset version 4."
    )
    parser.add_argument(
        "--archive",
        type=Path,
        help="Use an existing Kaggle ZIP archive instead of downloading it.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing events.csv.",
    )
    parser.add_argument(
        "--keep-archive",
        action="store_true",
        help="Keep a downloaded archive under data/raw/.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_directories()

    if RAW_EVENTS_PATH.exists() and not args.force:
        metadata = validate_events_file(RAW_EVENTS_PATH)
        print(
            "events.csv is already present and verified: "
            f"{metadata['size_bytes'] / 1024**2:.1f} MiB"
        )
        return

    if args.archive:
        archive_path = args.archive.resolve()
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")
        cleanup_archive = False
    else:
        temporary_directory = Path(tempfile.mkdtemp(prefix="retailrocket_"))
        archive_path = temporary_directory / "retailrocket_v4.zip"
        cleanup_archive = True
        print("Downloading RetailRocket dataset version 4...")
        download_archive(archive_path)

    archive_checksum = sha256_file(archive_path)
    if archive_checksum != SOURCE_ARCHIVE_SHA256:
        raise ValueError(
            "Archive checksum mismatch. "
            f"Expected {SOURCE_ARCHIVE_SHA256}, got {archive_checksum}."
        )

    extract_events(archive_path, RAW_EVENTS_PATH)
    metadata = validate_events_file(RAW_EVENTS_PATH)
    print(
        "Extracted and verified events.csv: "
        f"{metadata['size_bytes'] / 1024**2:.1f} MiB"
    )

    if args.keep_archive and not args.archive:
        kept_archive = RAW_EVENTS_PATH.parent / "retailrocket_v4.zip"
        shutil.move(str(archive_path), kept_archive)
        print(f"Archive kept at: {kept_archive}")
    elif cleanup_archive:
        shutil.rmtree(archive_path.parent, ignore_errors=True)


if __name__ == "__main__":
    main()
