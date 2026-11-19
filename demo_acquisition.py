import io
from pathlib import Path
from unittest.mock import patch

from data_acquisition.connectors.base_connector import BaseConnector
from data_acquisition.data_discovery.search_engine import DatasetDiscoveryEngine
from data_acquisition.ingestion.download_manager import DownloadManager
from data_acquisition.ingestion.raw_storage import RawStorageManager
from data_acquisition.metadata.source_registry import SourceRegistry
from data_acquisition.schemas.dataset_schema import DatasetSearchRequest
from data_acquisition.services.acquisition_service import AcquisitionService
from data_acquisition.services.discovery_service import DiscoveryService

REPO_ROOT = Path(__file__).resolve().parent


class _FakeResponse:
    def __init__(self, data: bytes):
        self._buf = io.BytesIO(data)
        self.headers = {}

    def read(self, size: int = -1) -> bytes:
        return self._buf.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._buf.close()
        return False


class _DemoConnector(BaseConnector):
    def authenticate(self) -> bool:
        return True

    def search(self, query: str, max_results: int = 10):
        return self.fetch_datasets(query=query, max_results=max_results)

    def fetch_datasets(self, query: str, max_results: int = 10):
        return [
            {
                "dataset_id": "demo-phish-01",
                "name": "Real-World Phishing URLs",
                "domain": "phishing",
                "platform": "DemoSource",
                "source_url": "https://example.org/phishing_urls.csv",
                "description": "Unpreprocessed phishing and benign URL records",
                "record_count": 75000,
                "format": "csv",
                "license": "MIT",
                "access_status": "eligible",
            }
        ]

    def download_data(self, dataset_id: str, filename=None):
        return None


def main() -> None:
    registry_path = REPO_ROOT / "data" / "demo_source_registry.json"
    staging_dir = REPO_ROOT / "data" / "demo_staging"
    storage_dir = REPO_ROOT / "storage"

    registry = SourceRegistry(registry_path=str(registry_path))
    raw_storage = RawStorageManager(base_storage_dir=str(storage_dir))
    dl_manager = DownloadManager(
        staging_dir=str(staging_dir),
        raw_storage=raw_storage,
        max_retries=1,
        backoff_seconds=0.0,
    )
    engine = DatasetDiscoveryEngine(connectors={"demo": _DemoConnector()})
    disc_svc = DiscoveryService(discovery_engine=engine, registry=registry)
    acq_svc = AcquisitionService(
        registry=registry,
        download_manager=dl_manager,
        raw_storage=raw_storage,
    )

    req = DatasetSearchRequest.from_dict(
        {
            "query": "phishing urls",
            "domain": "phishing",
            "min_records": 10000,
            "formats": ["csv"],
            "require_verified_license": True,
        }
    )
    print("Schema validation errors:", req.validate())

    found = disc_svc.search_datasets(req.to_requirements_dict())
    print(
        "Discovered & ranked:",
        found[0]["source_id"],
        found[0]["dataset_name"],
        "score=",
        found[0]["relevance_score"],
    )

    sample_csv = (
        b"url,label\nhttp://suspicious-login.test,1\nhttps://example.com,0\n"
    )
    with patch(
        "data_acquisition.ingestion.download_manager.urlopen",
        side_effect=lambda *args, **kwargs: _FakeResponse(sample_csv),
    ):
        job = acq_svc.acquire_dataset(found[0]["source_id"])

    print("Acquisition job:", job)
    print("Stored raw file exists:", Path(job["storage_uri"]).exists())


if __name__ == "__main__":
    main()