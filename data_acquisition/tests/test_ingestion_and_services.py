import hashlib
import io
from unittest.mock import patch
from urllib.error import URLError
import pytest

from data_acquisition.data_discovery.search_engine import DatasetDiscoveryEngine
from data_acquisition.ingestion.download_manager import DownloadManager
from data_acquisition.ingestion.raw_storage import RawStorageManager
from data_acquisition.metadata.source_registry import SourceRegistry
from data_acquisition.scraping.crawler import WebCrawler
from data_acquisition.scraping.scraper import WebScraper
from data_acquisition.scraping.url_validator import URLValidator
from data_acquisition.services.acquisition_service import AcquisitionService
from data_acquisition.services.discovery_service import DiscoveryService


class _ByteStreamResponse:
    def __init__(self, data: bytes):
        self._buf = io.BytesIO(data)
        self.headers = {}

    def read(self, size: int = -1) -> bytes:
        return self._buf.read(size)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._buf.close()
        return False


def test_raw_storage_preserves_original_and_prevents_overwrite(tmp_path):
    storage = RawStorageManager(base_storage_dir=str(tmp_path / "storage"))
    src_file = tmp_path / "original.csv"
    src_file.write_bytes(b"col1,col2\nval1,val2\n")

    stored = storage.store_raw_file(src_file, domain="phishing", source_id="SRC_001")
    assert stored.exists()
    assert stored.read_bytes() == b"col1,col2\nval1,val2\n"
    assert src_file.read_bytes() == b"col1,col2\nval1,val2\n"

    with pytest.raises(FileExistsError):
        storage.store_raw_file(src_file, domain="phishing", source_id="SRC_001", overwrite=False)


def test_download_manager_checksum_and_retries(tmp_path):
    raw_mgr = RawStorageManager(base_storage_dir=str(tmp_path / "storage"))
    dl_mgr = DownloadManager(
        staging_dir=str(tmp_path / "staging"),
        raw_storage=raw_mgr,
        max_retries=1,
        backoff_seconds=0.0,
    )

    payload = b"url,label\nhttps://safe.example,benign\n"
    good_hash = hashlib.sha256(payload).hexdigest()

    # Valid checksum succeeds
    with patch(
        "data_acquisition.ingestion.download_manager.urlopen",
        side_effect=lambda *args, **kwargs: _ByteStreamResponse(payload),
    ):
        res = dl_mgr.download_file(
            url="https://data.example.org/urls.csv",
            source_id="SRC_010",
            domain="phishing",
            expected_sha256=good_hash,
        )
    assert res["status"] == "completed"
    assert res["checksum"] == good_hash
    assert res["storage_uri"] is not None

    # Checksum mismatch retries once with fresh stream and marks job failed
    with patch(
        "data_acquisition.ingestion.download_manager.urlopen",
        side_effect=lambda *args, **kwargs: _ByteStreamResponse(payload),
    ):
        bad_res = dl_mgr.download_file(
            url="https://data.example.org/urls.csv",
            source_id="SRC_011",
            domain="phishing",
            expected_sha256="0" * 64,
        )
    assert bad_res["status"] == "failed"
    assert bad_res["attempts"] == 2
    assert "Checksum mismatch" in (bad_res["error"] or "")

    # Network failure retries once and then fails cleanly
    with patch(
        "data_acquisition.ingestion.download_manager.urlopen",
        side_effect=URLError("connection refused"),
    ):
        net_fail = dl_mgr.download_file(
            url="https://data.example.org/missing.csv",
            source_id="SRC_012",
            domain="phishing",
        )
    assert net_fail["status"] == "failed"
    assert net_fail["attempts"] == 2


def test_scraping_validator_parser_scraper_and_crawler():
    validator = URLValidator(allowed_domains=["datasets.example.org"])
    assert validator.normalize_url("javascript:alert(1)") is None
    assert (
        validator.normalize_url("/files/log.csv#top", base_url="https://datasets.example.org/index")
        == "https://datasets.example.org/files/log.csv"
    )
    assert validator.is_valid_url("https://other.example.org/file.csv") is False

    html_page_1 = """
    <html>
      <head><title>Attack Log Archive</title><meta name="description" content="50,000 network events"></head>
      <body>
        <h1>Attack Log Archive</h1>
        <a href="/page2">Next Page</a>
        <a href="/files/logs.csv">Download CSV Dataset</a>
      </body>
    </html>
    """
    html_page_2 = """
    <html>
      <head><title>Page 2 Logs</title></head>
      <body><a href="/files/more.json">JSON Dump</a></body>
    </html>
    """

    pages = {
        "https://datasets.example.org/start": html_page_1,
        "https://datasets.example.org/page2": html_page_2,
    }

    def fake_fetch(url):
        return pages.get(url)

    scraper = WebScraper(validator=validator, request_delay=0.0)
    with patch.object(scraper, "fetch_html", side_effect=fake_fetch):
        crawler = WebCrawler(scraper=scraper, validator=validator, max_pages=5, max_depth=1)
        items = crawler.crawl(["https://datasets.example.org/start"], domain="attack_logs")

    assert len(items) == 2
    assert items[0]["dataset_name"] == "Attack Log Archive"
    assert items[0]["record_count"] == 50000
    assert "https://datasets.example.org/files/logs.csv" in items[0]["download_links"]


def test_discovery_and_acquisition_services_integration(tmp_path):
    registry = SourceRegistry(registry_path=str(tmp_path / "reg.json"))
    raw_storage = RawStorageManager(base_storage_dir=str(tmp_path / "storage"))
    dl_manager = DownloadManager(
        staging_dir=str(tmp_path / "staging"),
        raw_storage=raw_storage,
        max_retries=0,
        backoff_seconds=0.0,
    )

    class _MockConnector:
        def search(self, query, max_results=10):
            return [
                {
                    "dataset_id": "phish-001",
                    "name": "Phishing Dataset",
                    "domain": "phishing",
                    "platform": "MockSource",
                    "source_url": "https://mock.example.org/phishing.csv",
                    "record_count": 25000,
                    "format": "csv",
                    "license": "MIT",
                }
            ]

    engine = DatasetDiscoveryEngine(connectors={"mock": _MockConnector()})
    disc_service = DiscoveryService(discovery_engine=engine, registry=registry)
    found = disc_service.search_datasets({"domain": "phishing", "query": "phishing"})
    assert len(found) == 1
    source_id = found[0]["source_id"]
    assert source_id.startswith("SRC_")

    acq_service = AcquisitionService(
        registry=registry,
        download_manager=dl_manager,
        raw_storage=raw_storage,
    )
    with patch(
        "data_acquisition.ingestion.download_manager.urlopen",
        side_effect=lambda *args, **kwargs: _ByteStreamResponse(b"url,label\nhttp://phish.test,1\n"),
    ):
        job = acq_service.acquire_dataset(source_id)

    assert job["status"] == "completed"
    assert job["storage_uri"] is not None
    status_lookup = acq_service.get_acquisition_status(job["job_id"])
    assert status_lookup is not None
    assert status_lookup["status"] == "completed"