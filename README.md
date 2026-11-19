# DataForge — Data Acquisition Module (`data_acquisition`)

The **Data Acquisition** module powers automated dataset discovery, bounded web scraping, staged download orchestration, license and provenance tracking, and unmodified raw data storage for **DataForge** across the **Phishing**, **Attack Logs**, **Vulnerable Code**, and **User Behavior** domains.

---

## Table of Contents

1. [Overview & Core Guarantees](#overview--core-guarantees)
2. [Directory Structure](#directory-structure)
3. [Module Breakdown](#module-breakdown)
   - [Connectors](#1-connectors-data_acquisitionconnectors)
   - [Data Discovery](#2-data-discovery-data_acquisitiondata_discovery)
   - [Metadata, Provenance & Source Registry](#3-metadata-provenance--source-registry-data_acquisitionmetadata)
   - [Ingestion & Raw Storage](#4-ingestion--raw-storage-data_acquisitioningestion)
   - [Web Scraping & Crawling](#5-web-scraping--crawling-data_acquisitionscraping)
   - [Schemas](#6-schemas-data_acquisitionschemas)
   - [Services](#7-services-data_acquisitionservices)
4. [Setup & Testing (Windows / PowerShell)](#setup--testing-windows--powershell)
5. [Usage Examples](#usage-examples)
   - [End-to-End Discovery & Acquisition](#end-to-end-discovery--acquisition)
   - [Bounded Web Crawling & Candidate Extraction](#bounded-web-crawling--candidate-extraction)
   - [Schema Validation & Serialization](#schema-validation--serialization)
6. [Integration Contracts (Backend & Data Engineering)](#integration-contracts-backend--data-engineering)
7. [Troubleshooting & Development Notes](#troubleshooting--development-notes)

---

## Overview & Core Guarantees

DataForge follows a **Real Data First** philosophy: rather than relying on synthetic or pre-cleaned sample sets when authentic data is available, the acquisition pipeline locates real-world datasets, verifies integrity, preserves original files untouched, and exposes clean programmatic interfaces to downstream components.

* **Unmodified Raw Storage:** Acquired files are copied into `storage/raw/<domain>/<source_id>/` without altering their contents or records, and accidental overwrites are blocked unless explicitly permitted.
* **Checksums & Provenance:** Every downloaded artifact can be verified against an expected **SHA-256** digest and recorded alongside computed checksums, source URLs, platforms, domains, licenses, and timestamps.
* **Explicit Missing-Value Handling:** Missing metadata fields (such as record counts, formats, or licenses) stay `None`/unverified rather than being guessed or fabricated.
* **Deterministic Job Lifecycle:** Download and acquisition jobs track explicit states (`pending`, `downloading`, `retrying`, `completed`, `failed`) with attempt counts and error messages.

---

## Directory Structure

```text
data_acquisition/
├── connectors/
│   ├── __init__.py
│   ├── base_connector.py
│   ├── github_connector.py
│   ├── huggingface_connector.py
│   ├── kaggle_connector.py
│   ├── open_data_connector.py
│   └── uci_connector.py
├── data_discovery/
│   ├── __init__.py
│   ├── deduplication.py
│   ├── metadata_extractor.py
│   ├── ranking.py
│   └── search_engine.py
├── ingestion/
│   ├── __init__.py
│   ├── archive_extractor.py
│   ├── download_manager.py
│   ├── file_validator.py
│   └── raw_storage.py
├── metadata/
│   ├── __init__.py
│   ├── license_checker.py
│   ├── provenance.py
│   └── source_registry.py
├── schemas/
│   ├── __init__.py
│   ├── acquisition_schema.py
│   └── dataset_schema.py
├── scraping/
│   ├── __init__.py
│   ├── crawler.py
│   ├── html_parser.py
│   ├── metadata_parser.py
│   ├── scraper.py
│   └── url_validator.py
├── services/
│   ├── __init__.py
│   ├── acquisition_service.py
│   └── discovery_service.py
└── tests/
    ├── test_blueprint_modules.py
    ├── test_connector.py
    ├── test_discovery_and_registry.py
    ├── test_ingestion_and_services.py
    ├── test_ingestion_service.py
    ├── test_modeling_service.py
    ├── test_new_connectors.py
    ├── test_preprocessing_service.py
    └── test_schemas.py

Everything from that previous response *was* in the README, and putting it inside a single `markdown` code block makes it easy to copy and paste the whole file at once.

```markdown
# DataForge — Data Acquisition Module (`data_acquisition`)

The **Data Acquisition** module powers automated dataset discovery, bounded web scraping, staged download orchestration, license and provenance tracking, and unmodified raw data storage for **DataForge** across the **Phishing**, **Attack Logs**, **Vulnerable Code**, and **User Behavior** domains.

---

## Table of Contents

1. [Overview & Core Guarantees](#overview--core-guarantees)
2. [Directory Structure](#directory-structure)
3. [Module Breakdown](#module-breakdown)
   - [Connectors](#1-connectors-data_acquisitionconnectors)
   - [Data Discovery](#2-data-discovery-data_acquisitiondata_discovery)
   - [Metadata, Provenance & Source Registry](#3-metadata-provenance--source-registry-data_acquisitionmetadata)
   - [Ingestion & Raw Storage](#4-ingestion--raw-storage-data_acquisitioningestion)
   - [Web Scraping & Crawling](#5-web-scraping--crawling-data_acquisitionscraping)
   - [Schemas](#6-schemas-data_acquisitionschemas)
   - [Services](#7-services-data_acquisitionservices)
4. [Setup & Testing (Windows / PowerShell)](#setup--testing-windows--powershell)
5. [Usage Examples](#usage-examples)
   - [End-to-End Discovery & Acquisition](#end-to-end-discovery--acquisition)
   - [Bounded Web Crawling & Candidate Extraction](#bounded-web-crawling--candidate-extraction)
   - [Schema Validation & Serialization](#schema-validation--serialization)
6. [Integration Contracts (Backend & Data Engineering)](#integration-contracts-backend--data-engineering)
7. [Troubleshooting & Development Notes](#troubleshooting--development-notes)

---

## Overview & Core Guarantees

DataForge follows a **Real Data First** philosophy: rather than relying on synthetic or pre-cleaned sample sets when authentic data is available, the acquisition pipeline locates real-world datasets, verifies integrity, preserves original files untouched, and exposes clean programmatic interfaces to downstream components.

* **Unmodified Raw Storage:** Acquired files are copied into `storage/raw/<domain>/<source_id>/` without altering their contents or records, and accidental overwrites are blocked unless explicitly permitted.
* **Checksums & Provenance:** Every downloaded artifact can be verified against an expected **SHA-256** digest and recorded alongside computed checksums, source URLs, platforms, domains, licenses, and timestamps.
* **Explicit Missing-Value Handling:** Missing metadata fields (such as record counts, formats, or licenses) stay `None`/unverified rather than being guessed or fabricated.
* **Deterministic Job Lifecycle:** Download and acquisition jobs track explicit states (`pending`, `downloading`, `retrying`, `completed`, `failed`) with attempt counts and error messages.

---

## Directory Structure

```text
data_acquisition/
├── connectors/
│   ├── __init__.py
│   ├── base_connector.py
│   ├── github_connector.py
│   ├── huggingface_connector.py
│   ├── kaggle_connector.py
│   ├── open_data_connector.py
│   └── uci_connector.py
├── data_discovery/
│   ├── __init__.py
│   ├── deduplication.py
│   ├── metadata_extractor.py
│   ├── ranking.py
│   └── search_engine.py
├── ingestion/
│   ├── __init__.py
│   ├── archive_extractor.py
│   ├── download_manager.py
│   ├── file_validator.py
│   └── raw_storage.py
├── metadata/
│   ├── __init__.py
│   ├── license_checker.py
│   ├── provenance.py
│   └── source_registry.py
├── schemas/
│   ├── __init__.py
│   ├── acquisition_schema.py
│   └── dataset_schema.py
├── scraping/
│   ├── __init__.py
│   ├── crawler.py
│   ├── html_parser.py
│   ├── metadata_parser.py
│   ├── scraper.py
│   └── url_validator.py
├── services/
│   ├── __init__.py
│   ├── acquisition_service.py
│   └── discovery_service.py
└── tests/
    ├── test_blueprint_modules.py
    ├── test_connector.py
    ├── test_discovery_and_registry.py
    ├── test_ingestion_and_services.py
    ├── test_ingestion_service.py
    ├── test_modeling_service.py
    ├── test_new_connectors.py
    ├── test_preprocessing_service.py
    └── test_schemas.py

```

---

## Module Breakdown

### 1. Connectors (`data_acquisition/connectors/`)

* **`BaseConnector`** (`base_connector.py`): Abstract base class defining the shared connector contract (`authenticate`, `fetch_datasets`, `download_data`, plus search/metadata/download helpers).
* **`KaggleConnector`** (`kaggle_connector.py`): Searches and retrieves dataset metadata and files from Kaggle.
* **`HuggingFaceConnector`** (`huggingface_connector.py`): Searches and retrieves datasets from the Hugging Face Hub.
* **`UCIConnector`** (`uci_connector.py`): Searches and fetches metadata and files from the UCI Machine Learning Repository.
* **`GitHubConnector`** (`github_connector.py`): Searches public repositories, inspects repository file trees for dataset artifacts, skips private repositories when restricted, and downloads target/candidate files.
* **`OpenDataConnector`** (`open_data_connector.py`): Queries open data portals (such as CKAN-style endpoints and direct resource URLs) for dataset packages, formats, metadata, and resource downloads.

### 2. Data Discovery (`data_acquisition/data_discovery/`)

* **`DatasetDiscoveryEngine`** (`search_engine.py`): Registers and queries connectors, normalizes candidate metadata fields without inventing missing values, deduplicates candidates, and delegates ranking to `DatasetRanker`.
* **`DatasetRanker`** (`ranking.py`): Computes weighted relevance scores in `[0.0, 1.0]` across domain match, query/keyword relevance, record count vs. `min_records`, requested features/labels, format match, and access/license eligibility.
* **`DatasetDeduplicator`** (`deduplication.py`): Removes duplicate dataset candidates across sources.
* **`MetadataExtractor`** (`metadata_extractor.py`): Extracts and structures dataset metadata attributes.

### 3. Metadata, Provenance & Source Registry (`data_acquisition/metadata/`)

* **`SourceRegistry`** (`source_registry.py`): Centralized source store (in-memory with optional JSON persistence via `registry_path`) that assigns sequential IDs (`SRC_001`, `SRC_002`, ...), deduplicates matching `dataset_id` + `platform` or `source_url` entries, updates download status/checksums/storage URIs, and filters by domain or status.
* **`LicenseChecker`** (`license_checker.py`): Evaluates license strings and usage eligibility.
* **`ProvenanceTracker`** (`provenance.py`): Tracks source lineage and acquisition provenance records.

### 4. Ingestion & Raw Storage (`data_acquisition/ingestion/`)

* **`RawStorageManager`** (`raw_storage.py`): Manages `storage/raw/<domain>/<source_id>/`, normalizes domain and `source_id` directory segments, copies original files without mutating them, prevents accidental overwrites (`overwrite=False` by default), and generates storage URIs.
* **`DownloadManager`** (`download_manager.py`): Downloads remote files into a staging directory with configurable retries and backoff, computes and verifies **SHA-256** checksums, optionally extracts archives (`.zip`, `.tar`, `.gz`, `.tgz`), hands off original files to `RawStorageManager`, cleans up staged files, and tracks job statuses (`pending`, `downloading`, `retrying`, `completed`, `failed`).
* **`ArchiveExtractor`** (`archive_extractor.py`): Extracts compressed dataset archives into target directories.
* **`FileValidator`** (`file_validator.py`): Validates downloaded file existence, integrity, and supported formats.

### 5. Web Scraping & Crawling (`data_acquisition/scraping/`)

* **`URLValidator`** (`url_validator.py`): Resolves relative URLs against a base URL, strips fragment identifiers for canonical deduplication, rejects unsafe schemes (`javascript:`, `data:`, `mailto:`, `tel:`, `file:`), and enforces optional `allowed_domains`.
* **`HTMLParser`** (`html_parser.py`): Parses HTML pages using BeautifulSoup to extract `<title>`, `<h1>`, `<meta name="description">`, normalized internal/allowed links, candidate dataset download links (by file extension or download/dataset keywords), and text excerpts.
* **`MetadataParser`** (`metadata_parser.py`): Extracts normalized metadata dictionaries (`dataset_name`, `domain`, `platform`, `source_url`, `description`, `record_count`, `features`, `format`, `download_links`, `license`, `access_status`), leaving unknown fields as `None` when not present.
* **`WebScraper`** (`scraper.py`): Enforces request pacing (`request_delay`) and timeouts, captures HTTP/URL/unexpected errors in `self.errors` without crashing, fetches HTML, and parses page metadata + links.
* **`WebCrawler`** (`crawler.py`): Performs bounded breadth-first traversal from seed URLs up to `max_pages` and `max_depth`, deduplicates visited URLs, collects extracted dataset records, and records crawl/scrape errors.

### 6. Schemas (`data_acquisition/schemas/`)

* **`dataset_schema.py`**:
* `DatasetSearchRequest`: Validates discovery parameters (`query`, `domain`, `description`, `keywords`, `min_records`, `required_features`, `labels`, `formats`, `require_verified_license`, `max_results_per_source`) and converts to requirement dicts.
* `DatasetRecord`: Standardizes dataset metadata, license/access state, download state, storage URI, checksum, and `relevance_score`.


* **`acquisition_schema.py`**:
* `AcquisitionRequest`: Validates acquisition inputs (`dataset_id`, `download_url`, `connector_name`, `domain`, `filename`, `expected_sha256` as 64-hex characters, `extract_archives`, `overwrite`).
* `AcquisitionJobStatus`: Represents job execution state (`job_id`, `source_id`, `status`, `storage_uri`, `checksum`, `file_size_bytes`, `attempts`, `error`).
* `ProvenanceRecord`: Captures source URL, platform, domain, storage URI, `sha256`, license, acquisition timestamp, and extra metadata.



### 7. Services (`data_acquisition/services/`)

* **`DiscoveryService`** (`discovery_service.py`):
* `search_datasets(requirements, max_results_per_source=10, register_results=True)`: Runs `DatasetDiscoveryEngine.discover(...)`, evaluates license/access status where known, optionally registers records in `SourceRegistry`, and returns normalized dataset dictionaries.
* `get_dataset_metadata(dataset_id)`: Looks up a record by `source_id` or `dataset_identifier` in `SourceRegistry`, falling back to connector `get_metadata` methods if needed.


* **`AcquisitionService`** (`acquisition_service.py`):
* `acquire_dataset(dataset_id, download_url=None, connector_name=None, domain=None, filename=None, expected_sha256=None, extract_archives=False)`: Resolves the source in `SourceRegistry`, downloads via HTTP/HTTPS (`DownloadManager`) or a registered connector, validates the file via `FileValidator`, stores raw data via `RawStorageManager`, updates `SourceRegistry` status/checksum/URI, and returns a job status dict.
* `get_acquisition_status(job_id)`: Returns the current job status dictionary for `job_id`.



---

## Setup & Testing (Windows / PowerShell)

Activate your Python environment and run `pytest` from the repository root (`C:\Users\hp\dataforge`):

```powershell
C:\Users\hp\dataforge\env\Scripts\Activate.ps1
pytest -v

```

For a concise pass/fail summary:

```powershell
pytest -q

```

---

## Usage Examples

### End-to-End Discovery & Acquisition

```python
from data_acquisition.data_discovery.search_engine import DatasetDiscoveryEngine
from data_acquisition.ingestion.download_manager import DownloadManager
from data_acquisition.ingestion.raw_storage import RawStorageManager
from data_acquisition.metadata.source_registry import SourceRegistry
from data_acquisition.services.acquisition_service import AcquisitionService
from data_acquisition.services.discovery_service import DiscoveryService

registry = SourceRegistry(registry_path="data/source_registry.json")
raw_storage = RawStorageManager(base_storage_dir="storage")
download_manager = DownloadManager(
    staging_dir="data/downloads_staging",
    raw_storage=raw_storage,
    max_retries=2,
    backoff_seconds=1.0,
)

engine = DatasetDiscoveryEngine()
discovery_service = DiscoveryService(discovery_engine=engine, registry=registry)
acquisition_service = AcquisitionService(
    registry=registry,
    download_manager=download_manager,
    raw_storage=raw_storage,
)

candidates = discovery_service.search_datasets(
    {
        "domain": "phishing",
        "query": "phishing url dataset",
        "min_records": 10000,
        "formats": ["csv"],
        "require_verified_license": True,
    },
    max_results_per_source=10,
    register_results=True,
)

if candidates:
    top_source_id = candidates[0]["source_id"]
    job = acquisition_service.acquire_dataset(top_source_id)
    print("Job status:", acquisition_service.get_acquisition_status(job["job_id"]))
    print("Registry entry:", discovery_service.get_dataset_metadata(top_source_id))

```

### Bounded Web Crawling & Candidate Extraction

```python
from data_acquisition.scraping.crawler import WebCrawler
from data_acquisition.scraping.scraper import WebScraper
from data_acquisition.scraping.url_validator import URLValidator

validator = URLValidator(allowed_domains=["datasets.example.org"])
scraper = WebScraper(validator=validator, timeout=15.0, request_delay=0.5)
crawler = WebCrawler(scraper=scraper, validator=validator, max_pages=15, max_depth=2)

discovered_pages = crawler.crawl(
    seed_urls=["[https://datasets.example.org/datasets](https://datasets.example.org/datasets)"],
    domain="attack_logs",
    platform="WebCrawler",
)

for entry in discovered_pages:
    print(entry["dataset_name"], entry["format"], entry["download_links"])

```

### Schema Validation & Serialization

```python
from data_acquisition.schemas.acquisition_schema import AcquisitionRequest
from data_acquisition.schemas.dataset_schema import DatasetSearchRequest

search_req = DatasetSearchRequest.from_dict(
    {
        "query": "vulnerable code snippets",
        "domain": "vulnerable_code",
        "min_records": 5000,
        "formats": ["json", "jsonl"],
    }
)
assert search_req.validate() == []

acq_req = AcquisitionRequest.from_dict(
    {
        "source_id": "SRC_001",
        "download_url": "[https://example.org/vuln_code.jsonl](https://example.org/vuln_code.jsonl)",
        "domain": "vulnerable_code",
        "extract_archives": False,
    }
)
assert acq_req.validate() == []

```

---

## Integration Contracts (Backend & Data Engineering)

* **Backend / API Layer:** Call `DiscoveryService.search_datasets(...)`, `DiscoveryService.get_dataset_metadata(...)`, `AcquisitionService.acquire_dataset(...)`, and `AcquisitionService.get_acquisition_status(...)`, optionally validating inputs/outputs with `DatasetSearchRequest`, `DatasetRecord`, `AcquisitionRequest`, and `AcquisitionJobStatus`.
* **Data Engineering / Preprocessing Layer:** Read registered sources and raw file locations from `SourceRegistry` (`storage_uri`, `checksum`, `domain`, `license`, `download_status`) and consume unmodified files under `storage/raw/<domain>/<source_id>/`.

---

## Troubleshooting & Development Notes

* **Abstract Connector Methods:** Any custom connector subclassing `BaseConnector` must implement its required abstract methods (`authenticate`, `fetch_datasets`, `download_data`) so it can be instantiated.
* **Offline Unit Testing:** Keep unit tests deterministic by mocking network calls (`urlopen` or scraper fetch methods) and using `pytest`'s `tmp_path` fixture so tests do not hit external rate limits or write test artifacts into production directories.
* **Unknown Metadata:** When a source or web page does not declare a record count, format, or license, keep those fields as `None` or `"unknown"` rather than substituting default guesses.

```

```