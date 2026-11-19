import logging
import time
from typing import Any, Dict, Optional

from data_acquisition.connectors.base_connector import BaseConnector
from data_acquisition.ingestion.download_manager import DownloadManager
from data_acquisition.ingestion.file_validator import FileValidator
from data_acquisition.ingestion.raw_storage import RawStorageManager
from data_acquisition.metadata.provenance import ProvenanceTracker
from data_acquisition.metadata.source_registry import SourceRegistry

logger = logging.getLogger(__name__)


class AcquisitionService:
    """
    Service interface exposed to the backend (Person 2) for acquiring datasets
    either via a direct download URL or through a registered connector, validating
    files, preserving raw storage and provenance, and tracking job status.
    """

    def __init__(
        self,
        registry: Optional[SourceRegistry] = None,
        download_manager: Optional[DownloadManager] = None,
        raw_storage: Optional[RawStorageManager] = None,
        validator: Optional[FileValidator] = None,
        provenance: Optional[ProvenanceTracker] = None,
        connectors: Optional[Dict[str, BaseConnector]] = None,
    ):
        self.registry = registry or SourceRegistry()
        self.raw_storage = raw_storage or RawStorageManager()
        self.download_manager = download_manager or DownloadManager(raw_storage=self.raw_storage)
        self.validator = validator or FileValidator()
        self.provenance = provenance or ProvenanceTracker()
        self.connectors: Dict[str, BaseConnector] = dict(connectors or {})
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def register_connector(self, name: str, connector: BaseConnector) -> None:
        self.connectors[name] = connector

    def acquire_dataset(
        self,
        dataset_id: str,
        download_url: Optional[str] = None,
        connector_name: Optional[str] = None,
        domain: Optional[str] = None,
        filename: Optional[str] = None,
        expected_sha256: Optional[str] = None,
        extract_archives: bool = False,
    ) -> Dict[str, Any]:
        """
        Triggers dataset acquisition for a registered `source_id` or `dataset_identifier`.
        Returns a job status dictionary containing `job_id`, `source_id`, `status`,
        `storage_uri`, and `error` (if failed).
        """
        source_record = self.registry.get_source(dataset_id)
        if not source_record:
            for item in self.registry.list_sources():
                if item.get("dataset_identifier") == dataset_id:
                    source_record = item
                    break

        source_id = source_record["source_id"] if source_record else self.registry.register_source(
            {
                "dataset_name": dataset_id,
                "dataset_identifier": dataset_id,
                "domain": domain,
                "source_url": download_url,
            }
        )
        resolved_domain = domain or (source_record or {}).get("domain")
        resolved_url = download_url or (source_record or {}).get("source_url")
        resolved_platform = (connector_name or (source_record or {}).get("platform") or "").lower()

        job_id = f"acq_{source_id}_{int(time.time() * 1000)}"
        job_info: Dict[str, Any] = {
            "job_id": job_id,
            "source_id": source_id,
            "status": "pending",
            "storage_uri": None,
            "checksum": None,
            "error": None,
        }
        self._jobs[job_id] = job_info

        self.registry.update_download_status(source_id, status="downloading")
        job_info["status"] = "downloading"

        try:
            stored_path_str: Optional[str] = None
            checksum: Optional[str] = None

            if resolved_url and resolved_url.startswith(("http://", "https://")):
                dl_result = self.download_manager.download_file(
                    url=resolved_url,
                    source_id=source_id,
                    domain=resolved_domain,
                    filename=filename,
                    expected_sha256=expected_sha256,
                    extract_archives=extract_archives,
                )
                if dl_result.get("status") != "completed" or not dl_result.get("storage_uri"):
                    raise RuntimeError(dl_result.get("error") or "Download did not complete.")
                stored_path_str = dl_result["storage_uri"]
                checksum = dl_result.get("checksum")
            else:
                connector = self._resolve_connector(resolved_platform)
                if not connector:
                    raise ValueError(
                        f"No direct HTTP download_url or matching connector available for '{dataset_id}'."
                    )
                dl_fn = getattr(connector, "download", None) or getattr(connector, "download_dataset", None)
                if not callable(dl_fn):
                    raise RuntimeError(f"Connector '{connector}' does not support download.")

                target_ref = (source_record or {}).get("dataset_identifier") or dataset_id
                downloaded_file = dl_fn(target_ref, filename=filename) if filename else dl_fn(target_ref)
                if not downloaded_file:
                    raise RuntimeError(f"Connector download returned no file for '{target_ref}'.")

                raw_stored = self.raw_storage.store_raw_file(
                    source_file=downloaded_file,
                    domain=resolved_domain,
                    source_id=source_id,
                    target_filename=filename,
                )
                stored_path_str = str(raw_stored)
                checksum = self.download_manager.compute_sha256(raw_stored)

            validate_fn = getattr(self.validator, "validate_file", None) or getattr(self.validator, "validate", None)
            if callable(validate_fn):
                is_valid = validate_fn(stored_path_str)
                if is_valid is False:
                    raise ValueError(f"Downloaded file failed validation: '{stored_path_str}'.")

            self.registry.update_download_status(
                source_id=source_id,
                status="completed",
                storage_uri=stored_path_str,
                checksum=checksum,
            )
            job_info["status"] = "completed"
            job_info["storage_uri"] = stored_path_str
            job_info["checksum"] = checksum
            job_info["error"] = None
            return dict(job_info)

        except Exception as exc:
            err_msg = str(exc)
            self.logger.error(f"Acquisition failed for source_id='{source_id}': {err_msg}")
            self.registry.update_download_status(
                source_id=source_id,
                status="failed",
                error=err_msg,
            )
            job_info["status"] = "failed"
            job_info["error"] = err_msg
            return dict(job_info)

    def _resolve_connector(self, platform_key: str) -> Optional[BaseConnector]:
        if not platform_key:
            return next(iter(self.connectors.values()), None)
        for name, conn in self.connectors.items():
            if platform_key in name.lower():
                return conn
        return None

    def get_acquisition_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Returns the current status record for an acquisition job."""
        job = self._jobs.get(job_id)
        return dict(job) if job else None