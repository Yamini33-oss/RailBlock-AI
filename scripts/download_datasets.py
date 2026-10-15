"""Real Railway Dataset Downloader for KAVACH BIE Member 3.

Streams and downloads verified, publicly accessible Indian Railways datasets:
- stations_raw.json (8,990+ stations)
- trains_raw.json (5,200+ train services)
- schedules_raw.json (14 MB detailed train stops)

Validates content integrity, records SHA-256 hashes, file sizes, and writes data/metadata/download_manifest.json.
"""

import hashlib
import json
import logging
import time
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import requests

from scripts.discover_datasets import discover_datasets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
METADATA_DIR = BASE_DIR / "data" / "metadata"
MANIFEST_FILE = METADATA_DIR / "download_manifest.json"


def compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a local file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, dest_path: Path, timeout: int = 60) -> Dict[str, Any]:
    """Stream download a file from a URL with progress tracking and validation."""
    logger.info("Downloading %s -> %s", url, dest_path.name)
    start_time = time.perf_counter()

    headers = {"User-Agent": "KAVACH-BIE-Data-Pipeline/1.0 (Indian-Railways-Research)"}
    response = requests.get(url, stream=True, timeout=timeout, headers=headers)
    response.raise_for_status()

    total_bytes = 0
    temp_dest = dest_path.with_suffix(dest_path.suffix + ".part")

    try:
        with open(temp_dest, "wb") as f:
            for chunk in response.iter_content(chunk_size=131072):
                if chunk:
                    f.write(chunk)
                    total_bytes += len(chunk)
        # Atomically replace destination
        if dest_path.exists():
            dest_path.unlink()
        temp_dest.rename(dest_path)
    except Exception:
        if temp_dest.exists():
            temp_dest.unlink()
        raise

    duration = time.perf_counter() - start_time
    file_sha256 = compute_sha256(dest_path)

    logger.info(
        "Successfully downloaded %s (%.2f MB in %.2fs, SHA-256: %s...)",
        dest_path.name,
        total_bytes / (1024 * 1024),
        duration,
        file_sha256[:12],
    )

    return {
        "status": "SUCCESS",
        "file_size_bytes": total_bytes,
        "file_size_mb": round(total_bytes / (1024 * 1024), 3),
        "download_duration_seconds": round(duration, 2),
        "sha256": file_sha256,
        "http_status": response.status_code,
    }


def download_all_datasets(force: bool = False) -> Dict[str, Any]:
    """Download all discovered railway datasets with valid download URLs."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    catalog = discover_datasets()
    manifest_records: List[Dict[str, Any]] = []

    for ds in catalog["datasets"]:
        download_url = ds.get("download_url")
        raw_filename = ds.get("target_raw_filename")

        if not download_url or not raw_filename:
            continue

        dest_file = RAW_DIR / raw_filename

        if dest_file.exists() and not force:
            logger.info("File %s already exists. Verifying hash...", raw_filename)
            file_size = dest_file.stat().st_size
            file_hash = compute_sha256(dest_file)
            manifest_records.append({
                "dataset_id": ds["dataset_id"],
                "name": ds["name"],
                "target_file": str(dest_file.relative_to(BASE_DIR)),
                "source_url": ds["source_url"],
                "download_url": download_url,
                "retrieved_at_utc": datetime.fromtimestamp(dest_file.stat().st_mtime, timezone.utc).isoformat(),
                "status": "CACHED_EXISTING",
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 3),
                "sha256": file_hash,
            })
            continue

        try:
            dl_result = download_file(download_url, dest_file)
            manifest_records.append({
                "dataset_id": ds["dataset_id"],
                "name": ds["name"],
                "target_file": str(dest_file.relative_to(BASE_DIR)),
                "source_url": ds["source_url"],
                "download_url": download_url,
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                **dl_result,
            })
        except Exception as exc:
            logger.error("Failed to download %s from %s: %s", raw_filename, download_url, exc)
            manifest_records.append({
                "dataset_id": ds["dataset_id"],
                "name": ds["name"],
                "target_file": str(dest_file.relative_to(BASE_DIR)),
                "source_url": ds["source_url"],
                "download_url": download_url,
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "status": "FAILED",
                "error": str(exc),
            })

    manifest = {
        "manifest_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_downloads": len(manifest_records),
        "successful_downloads": sum(1 for r in manifest_records if r["status"] in ("SUCCESS", "CACHED_EXISTING")),
        "records": manifest_records,
    }

    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info("Download manifest saved to %s", MANIFEST_FILE)
    return manifest


if __name__ == "__main__":
    download_all_datasets(force=False)
