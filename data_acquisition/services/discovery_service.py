import logging
from typing import Any, Dict, List, Optional

from data_acquisition.data_discovery.search_engine import DatasetDiscoveryEngine
from data_acquisition.metadata.license_checker import LicenseChecker
from data_acquisition.metadata.source_registry import SourceRegistry

logger = logging.getLogger(__name__)


class DiscoveryService:
    """
    Service interface exposed to the backend (Person 2) for discovering candidate
    datasets, evaluating basic license/access eligibility, registering sources,
    and retrieving metadata.
    """

    def __init__(
        self,
        discovery_engine: Optional[DatasetDiscoveryEngine] = None,
        registry: Optional[SourceRegistry] = None,
        license_checker: Optional[LicenseChecker] = None,
    ):
        self.discovery_engine = discovery_engine or DatasetDiscoveryEngine()
        self.registry = registry or SourceRegistry()
        self.license_checker = license_checker or LicenseChecker()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _evaluate_access_status(self, candidate: Dict[str, Any]) -> str:
        """Evaluates license eligibility when a license string is present; otherwise keeps 'unknown'."""
        existing_status = (candidate.get("access_status") or "").strip().lower()
        if existing_status in {"eligible", "ineligible", "restricted"}:
            return existing_status

        license_val = candidate.get("license")
        if not license_val:
            return "unknown"

        check_fn = getattr(self.license_checker, "is_eligible", None) or getattr(
            self.license_checker, "check_license", None
        )
        if callable(check_fn):
            result = check_fn(license_val)
            if isinstance(result, bool):
                return "eligible" if result else "restricted"
            if isinstance(result, dict) and "eligible" in result:
                return "eligible" if result["eligible"] else "restricted"
            if isinstance(result, str) and result.strip():
                return result.strip().lower()

        return "unknown"

    def search_datasets(
        self,
        requirements: Dict[str, Any],
        max_results_per_source: int = 10,
        register_results: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Discovers datasets matching `requirements`, evaluates license/access status
        where known, optionally records them in `SourceRegistry`, and returns
        structured records aligned with Person 4's integration contract.
        """
        self.logger.info("Running DiscoveryService.search_datasets...")
        ranked = self.discovery_engine.discover(
            requirements=requirements,
            max_results_per_source=max_results_per_source,
        )

        output: List[Dict[str, Any]] = []
        for item in ranked:
            access_status = self._evaluate_access_status(item)
            record: Dict[str, Any] = {
                "source_id": item.get("source_id"),
                "dataset_name": item.get("name") or item.get("dataset_name") or item.get("dataset_id") or "",
                "dataset_id": item.get("dataset_id"),
                "domain": item.get("domain"),
                "platform": item.get("platform"),
                "record_count": item.get("record_count"),
                "features": item.get("features") if item.get("features") is not None else [],
                "format": item.get("format"),
                "source_url": item.get("source_url"),
                "license": item.get("license"),
                "access_status": access_status,
                "download_status": item.get("download_status") or "pending",
                "storage_uri": item.get("storage_uri"),
                "relevance_score": item.get("relevance_score"),
            }

            if register_results:
                source_id = self.registry.register_source(record)
                reg_entry = self.registry.get_source(source_id) or {}
                record["source_id"] = source_id
                record["download_status"] = reg_entry.get("download_status", record["download_status"])
                record["storage_uri"] = reg_entry.get("storage_uri", record["storage_uri"])

            output.append(record)

        return output

    def get_dataset_metadata(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves dataset metadata from `SourceRegistry` (by `source_id` or `dataset_identifier`),
        or queries a matching connector's `get_metadata` method if not yet registered.
        """
        if not dataset_id:
            return None

        registered = self.registry.get_source(dataset_id)
        if registered:
            return registered

        for src in self.registry.list_sources():
            if src.get("dataset_identifier") == dataset_id:
                return src

        for conn_name, connector in self.discovery_engine.connectors.items():
            meta_fn = getattr(connector, "get_metadata", None)
            if callable(meta_fn):
                try:
                    meta = meta_fn(dataset_id)
                    if isinstance(meta, dict):
                        return meta
                except Exception as exc:
                    self.logger.warning(f"Connector '{conn_name}' get_metadata failed for '{dataset_id}': {exc}")

        return None