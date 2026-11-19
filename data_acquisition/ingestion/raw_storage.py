import logging
import shutil
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


class RawStorageManager:
    """
    Manages the DataForge raw data layer (`storage/raw/<domain>/<source_id>/`),
    preserving original acquired files unmodified and returning storage references.
    """

    VALID_DOMAINS = (
        "phishing",
        "attack_logs",
        "vulnerable_code",
        "user_behavior",
    )

    def __init__(self, base_storage_dir: str = "storage"):
        self.base_storage_dir = Path(base_storage_dir)
        self.raw_root = self.base_storage_dir / "raw"
        self.raw_root.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _normalize_domain(self, domain: Optional[str]) -> str:
        clean = (domain or "general").strip().lower().replace("-", "_").replace(" ", "_")
        return clean or "general"

    def _normalize_source_id(self, source_id: str) -> str:
        clean = "".join(ch if (ch.isalnum() or ch in {"_", "-"}) else "_" for ch in str(source_id).strip())
        if not clean:
            raise ValueError("source_id must be a non-empty identifier.")
        return clean.lower()

    def get_source_dir(self, domain: Optional[str], source_id: str) -> Path:
        """Returns and ensures the raw directory for a specific domain and source ID."""
        dom_dir = self.raw_root / self._normalize_domain(domain)
        src_dir = dom_dir / self._normalize_source_id(source_id)
        src_dir.mkdir(parents=True, exist_ok=True)
        return src_dir

    def store_raw_file(
        self,
        source_file: Union[str, Path],
        domain: Optional[str],
        source_id: str,
        target_filename: Optional[str] = None,
        overwrite: bool = False,
    ) -> Path:
        """
        Copies an acquired file into `storage/raw/<domain>/<source_id>/` without
        modifying the original file or its records. Prevents accidental overwrite
        unless `overwrite=True` is explicitly passed.
        """
        src_path = Path(source_file)
        if not src_path.exists() or not src_path.is_file():
            raise FileNotFoundError(f"Source file does not exist for raw ingestion: '{src_path}'")

        dest_dir = self.get_source_dir(domain=domain, source_id=source_id)
        filename = target_filename or src_path.name
        dest_path = dest_dir / filename

        if dest_path.exists() and not overwrite:
            raise FileExistsError(
                f"Raw file already exists at '{dest_path}'. Set overwrite=True to replace it."
            )

        shutil.copy2(src_path, dest_path)
        self.logger.info(f"Stored raw dataset file at '{dest_path}' (source_id='{source_id}').")
        return dest_path

    def get_storage_uri(self, domain: Optional[str], source_id: str, filename: str) -> str:
        """Returns a normalized relative POSIX storage URI such as `storage/raw/phishing/src_001/data.csv`."""
        rel_path = Path(self.base_storage_dir.name or "storage") / "raw" / self._normalize_domain(domain) / self._normalize_source_id(source_id) / filename
        return rel_path.as_posix()