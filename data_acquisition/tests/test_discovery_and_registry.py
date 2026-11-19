from data_acquisition.connectors.base_connector import BaseConnector
from data_acquisition.data_discovery.ranking import DatasetRanker
from data_acquisition.data_discovery.search_engine import DatasetDiscoveryEngine
from data_acquisition.metadata.source_registry import SourceRegistry


class _StubConnector(BaseConnector):
    def __init__(self, items):
        self._items = items

    def authenticate(self) -> bool:
        return True

    def fetch_datasets(self, query, max_results=10):
        return self.search(query=query, max_results=max_results)

    def download_data(self, dataset_id, filename=None):
        return self.download(dataset_id=dataset_id, filename=filename)

    def search(self, query, max_results=10):
        return self._items[:max_results]

    def get_metadata(self, dataset_id):
        for item in self._items:
            if item.get("dataset_id") == dataset_id:
                return item
        return None

    def download(self, dataset_id, filename=None):
        return None

    
def test_ranker_prioritizes_matching_domain_records_and_license():
    ranker = DatasetRanker()
    requirements = {
        "domain": "phishing",
        "query": "phishing url dataset",
        "min_records": 50000,
        "labels": ["benign", "phishing"],
        "formats": ["csv"],
        "require_verified_license": True,
    }

    strong_match = {
        "name": "Phishing URL Dataset",
        "description": "Contains benign and phishing URLs",
        "domain": "phishing",
        "record_count": 80000,
        "features": ["url", "domain", "label"],
        "format": "csv",
        "license": "MIT",
        "access_status": "eligible",
    }
    weak_match = {
        "name": "Unrelated Notes",
        "description": "General text",
        "domain": "user_behavior",
        "record_count": None,
        "features": [],
        "format": "txt",
        "license": None,
        "access_status": "unknown",
    }

    ranked = ranker.rank_datasets([weak_match, strong_match], requirements=requirements)
    assert ranked[0]["name"] == "Phishing URL Dataset"
    assert ranked[0]["relevance_score"] > ranked[1]["relevance_score"]


def test_discovery_engine_deduplicates_and_ranks():
    dup_a = {
        "dataset_id": "ds-1",
        "name": "Phishing URLs",
        "source_url": "https://example.org/ds-1",
        "domain": "phishing",
        "record_count": 60000,
        "format": "csv",
        "license": "CC-BY-4.0",
        "access_status": "eligible",
    }
    dup_b = {
        "dataset_id": "ds-1",
        "name": "Phishing URLs",
        "source_url": "https://example.org/ds-1",
        "domain": "phishing",
        "record_count": 60000,
        "format": "csv",
        "license": "CC-BY-4.0",
        "access_status": "eligible",
    }

    engine = DatasetDiscoveryEngine(
        connectors={
            "conn_a": _StubConnector([dup_a]),
            "conn_b": _StubConnector([dup_b]),
        }
    )

    results = engine.discover({"domain": "phishing", "query": "phishing", "min_records": 50000})
    assert len(results) == 1
    assert "relevance_score" in results[0]


def test_source_registry_deduplication_status_and_persistence(tmp_path):
    reg_file = tmp_path / "registry.json"
    registry = SourceRegistry(registry_path=str(reg_file))

    sid_1 = registry.register_source(
        {
            "dataset_name": "CICIDS Sample",
            "dataset_identifier": "cicids-sample",
            "platform": "Kaggle",
            "source_url": "https://www.kaggle.com/datasets/test/cicids-sample",
            "domain": "attack_logs",
            "license": "MIT",
        }
    )
    assert sid_1 == "SRC_001"

    # Re-registering the same source_url or dataset_identifier+platform updates instead of duplicating
    sid_dup = registry.register_source(
        {
            "dataset_name": "CICIDS Sample",
            "dataset_identifier": "cicids-sample",
            "platform": "Kaggle",
            "source_url": "https://www.kaggle.com/datasets/test/cicids-sample",
            "domain": "attack_logs",
            "record_count": 12000,
        }
    )
    assert sid_dup == "SRC_001"
    assert len(registry.list_sources()) == 1
    assert registry.get_source("SRC_001")["record_count"] == 12000

    registry.update_download_status(
        "SRC_001",
        status="completed",
        storage_uri="storage/raw/attack_logs/src_001/data.csv",
        checksum="abc123",
    )
    assert registry.get_storage_uri("SRC_001") == "storage/raw/attack_logs/src_001/data.csv"

    # Reload from disk
    reloaded = SourceRegistry(registry_path=str(reg_file))
    assert reloaded.get_source("SRC_001")["download_status"] == "completed"