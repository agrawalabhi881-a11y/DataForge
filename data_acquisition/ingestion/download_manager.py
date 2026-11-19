import hashlib
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from data_acquisition.ingestion.archive_extractor import ArchiveExtractor
from data_acquisition.ingestion.file_validator import FileValidator
from data_acquisition.ingestion.raw_storage import RawStorageManager

logger = logging.getLogger(__name__)


class DownloadManager:
    """
    Downloads dataset files with retry handling, checksum verification,
    optional archive extraction, and raw storage ingestion.
    Tracks status across: pending, downloading, retrying, completed, failed.
    """

    def __init__(
        self,
        staging_dir: str = "data/downloads_staging",
        raw_storage: Optional[RawStorageManager] = None,
        extractor: Optional[ArchiveExtractor] = None,
        validator: Optional[FileValidator] = None,
        max_retries: int = 2,
        backoff_seconds: float = 1.0,
        chunk_size: int = 8192,
    ):
        self.staging_dir = Path(staging_dir)
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.raw_storage = raw_storage or RawStorageManager()
        self.extractor = extractor or ArchiveExtractor()
        self.validator = validator or FileValidator()
        self.max_retries = max(0, int(max_retries))
        self.backoff_seconds = max(0.0, float(backoff_seconds))
        self.chunk_size = max(1024, int(chunk_size))
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        digest = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        record = self._jobs.get(job_id)
        return dict(record) if record else None

    def _sanitize_filename(self, raw_name: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw_name.strip())
        return cleaned or "downloaded_dataset"

    def download_file(
        self,
        url: str,
        source_id: str,
        domain: Optional[str] = None,
        filename: Optional[str] = None,
        expected_sha256: Optional[str] = None,
        extract_archives: bool = False,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        Downloads a file from `url` into staging, verifies optional SHA-256 checksum,
        ingests the original file into `RawStorageManager`, and optionally extracts archives
        into a sibling subdirectory.
        """
        job_id = f"dl_{source_id}_{int(time.time() * 1000)}"
        inferred_name = filename or Path(url.split("?")[0]).name or f"{source_id}_data"
        safe_name = self._sanitize_filename(inferred_name)
        staged_path = self.staging_dir / f"{source_id}_{safe_name}"

        job_state: Dict[str, Any] = {
            "job_id": job_id,
            "source_id": source_id,
            "domain": domain,
            "url": url,
            "status": "pending",
            "attempts": 0,
            "storage_uri": None,
            "checksum": None,
            "file_size_bytes": None,
            "extracted_to": None,
            "error": None,
        }
        self._jobs[job_id] = job_state

        attempt = 0
        while attempt <= self.max_retries:
            attempt += 1
            job_state["attempts"] = attempt
            job_state["status"] = "downloading" if attempt == 1 else "retrying"

            try:
                if staged_path.exists():
                    staged_path.unlink(missing_ok=True)

                req = Request(
                    url,
                    headers={
                        "User-Agent": "DataForge-DownloadManager/1.0",
                        "Accept": "*/*",
                    },
                )
                with urlopen(req, timeout=60) as resp, open(staged_path, "wb") as out_f:
                    while True:
                        chunk = resp.read(self.chunk_size)
                        if not chunk:
                            break
                        out_f.write(chunk)

                if not staged_path.exists() or staged_path.stat().st_size == 0:
                    raise IOError("Downloaded file is empty or missing.")

                actual_sha256 = self.compute_sha256(staged_path)
                if expected_sha256 and actual_sha256.lower() != expected_sha256.strip().lower():
                    raise ValueError(
                        f"Checksum mismatch for '{url}': expected {expected_sha256}, got {actual_sha256}."
                    )

                raw_path = self.raw_storage.store_raw_file(
                    source_file=staged_path,
                    domain=domain,
                    source_id=source_id,
                    target_filename=safe_name,
                    overwrite=overwrite,
                )

                extracted_dir_str: Optional[str] = None
                if extract_archives and staged_path.suffix.lower() in {".zip", ".tar", ".gz", ".tgz"}:
                    extract_dest = raw_path.parent / "extracted"
                    extract_fn = getattr(self.extractor, "extract", None) or getattr(self.extractor, "extract_archive", None)
                    if callable(extract_fn):
                        extract_fn(str(raw_path), str(extract_dest))
                        extracted_dir_str = str(extract_dest)

                staged_path.unlink(missing_ok=True)

                job_state["status"] = "completed"
                job_state["storage_uri"] = str(raw_path)
                job_state["checksum"] = actual_sha256
                job_state["file_size_bytes"] = raw_path.stat().st_size
                job_state["extracted_to"] = extracted_dir_str
                job_state["error"] = None
                return dict(job_state)

            except (HTTPError, URLError, OSError, ValueError) as exc:
                if staged_path.exists():
                    staged_path.unlink(missing_ok=True)
                job_state["error"] = str(exc)
                self.logger.warning(
                    f"Download attempt {attempt}/{self.max_retries + 1} failed for '{url}': {exc}"
                )
                if attempt <= self.max_retries and self.backoff_seconds > 0:
                    time.sleep(self.backoff_seconds * attempt)

        job_state["status"] = "failed"
        return dict(job_state)