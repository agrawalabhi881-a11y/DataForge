import logging
from typing import Any, Dict, List, Optional

from data_acquisition.connectors.base_connector import BaseConnector
from data_acquisition.data_discovery.deduplication import DatasetDeduplicator
from data_acquisition.data_discovery.ranking import DatasetRanker

logger = logging.getLogger(__name__)


class DatasetDiscoveryEngine:
    """
    Coordinates dataset discovery across registered platform connectors,
    normalizes candidate metadata, removes duplicates, and ranks results
    against requested dataset requirements.
    """

    def __init__(
        self,
        connectors: Optional[Dict[str, BaseConnector]] = None,
        deduplicator: Optional[DatasetDeduplicator] = None,
        ranker: Optional[DatasetRanker] = None,
    ):
        self.connectors: Dict[str, BaseConnector] = dict(connectors or {})
        self.deduplicator = deduplicator or DatasetDeduplicator()
        self.ranker = ranker or DatasetRanker()
        self.logger = logging.getLogger(self.__class__.__name__)

    def register_connector(self, name: str, connector: BaseConnector) -> None:
        """Registers or replaces a named connector instance."""
        self.connectors[name] = connector
        self.logger.info(f"Registered discovery connector: '{name}'")

    def _normalize_candidate(
        self,
        raw: Dict[str, Any],
        connector_name: str,
        default_domain: Optional[str],
    ) -> Dict[str, Any]:
        """Normalizes connector output fields without inventing missing values."""
        name = raw.get("name") or raw.get("title") or raw.get("dataset_id") or ""
        record_count = raw.get("record_count")
        if record_count is None:
            record_count = raw.get("num_instances")

        return {
            "name": name,
            "dataset_id": raw.get("dataset_id") or raw.get("id"),
            "domain": raw.get("domain") or default_domain,
            "platform": raw.get("platform") or connector_name,
            "source_url": raw.get("source_url") or raw.get("url"),
            "description": raw.get("description") or "",
            "record_count": record_count,
            "features": raw.get("features") if raw.get("features") is not None else [],
            "format": raw.get("format"),
            "formats": raw.get("formats") if raw.get("formats") is not None else [],
            "license": raw.get("license"),
            "access_status": raw.get("access_status") or "unknown",
        }

    def discover(
        self,
        requirements: Dict[str, Any],
        max_results_per_source: int = 10,
        sources: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes a discovery pass across active connectors, deduplicates candidates,
        and returns ranked dataset records.
        """
        query = (
            requirements.get("query")
            or requirements.get("description")
            or requirements.get("domain")
            or ""
        ).strip()
        domain = requirements.get("domain")

        if not query:
            self.logger.warning("Discovery called with an empty query/description/domain.")
            return []

        selected_names = (
            [s for s in sources if s in self.connectors]
            if sources is not None
            else list(self.connectors.keys())
        )

        candidates: List[Dict[str, Any]] = []
        for conn_name in selected_names:
            connector = self.connectors[conn_name]
            search_fn = getattr(connector, "search", None)
            if not callable(search_fn):
                self.logger.warning(f"Connector '{conn_name}' does not implement search(); skipping.")
                continue

            try:
                raw_results = search_fn(query, max_results=max_results_per_source)
            except TypeError:
                raw_results = search_fn(query)
            except Exception as exc:
                self.logger.error(f"Error searching connector '{conn_name}': {exc}")
                continue

            for item in raw_results or []:
                if isinstance(item, dict):
                    candidates.append(self._normalize_candidate(item, conn_name, domain))

        unique_candidates = self.deduplicator.deduplicate_sources(candidates)
        ranked_results = self.ranker.rank_datasets(unique_candidates, requirements=requirements)
        self.logger.info(f"Discovery complete. Returning {len(ranked_results)} ranked candidates.")
        return ranked_results